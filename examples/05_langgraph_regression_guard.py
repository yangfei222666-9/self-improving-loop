#!/usr/bin/env python3
"""LangGraph-style regression guard demo.

This example has no LangGraph dependency. It models the exact production seam:

LangGraph / any agent node
-> node call fails or quality regresses
-> self-improving-loop records traces
-> success_rate / latency regression is checked
-> ConfigAdapter rollback restores the previous config
-> an event trail survives for review
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop

AGENT_ID = "langgraph-support-node"


class OneBadNodePatchStrategy:
    """Propose one bad patch so the rollback path is provable."""

    def __init__(self) -> None:
        self.proposed = False
        self.events: List[Dict[str, Any]] = []

    def analyze(
        self,
        agent_id: str,
        traces: List[Dict[str, Any]],
        before_metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.proposed:
            self.events.append(
                {
                    "event": "strategy_noop",
                    "agent_id": agent_id,
                    "reason": "one_bad_patch_demo_only",
                }
            )
            return {}

        self.proposed = True
        patch = {
            "mode": "broken",
            "model": "risky-v2",
            "tool_fanout": 8,
            "reason": "demo_bad_patch_to_prove_rollback",
        }
        self.events.append(
            {
                "event": "strategy_patch_proposed",
                "agent_id": agent_id,
                "before_metrics": before_metrics,
                "trace_count": len(traces),
                "patch": patch,
            }
        )
        return patch


class NodeConfigAdapter:
    """In-memory config owner for a LangGraph-style node."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {
            "mode": "stable",
            "model": "safe-v1",
            "tool_fanout": 2,
            "timeout_sec": 30,
        }
        self.rollback_count = 0
        self.events: List[Dict[str, Any]] = []

    def get_config(self, agent_id: str) -> Dict[str, Any]:
        self.events.append(
            {"event": "config_backed_up", "agent_id": agent_id, "config": dict(self.config)}
        )
        return dict(self.config)

    def apply_config(self, agent_id: str, config_patch: Dict[str, Any]) -> bool:
        self.config.update(config_patch)
        self.events.append(
            {"event": "config_patch_applied", "agent_id": agent_id, "config": dict(self.config)}
        )
        return True

    def rollback_config(self, agent_id: str, backup_config: Dict[str, Any]) -> None:
        self.config = dict(backup_config)
        self.rollback_count += 1
        self.events.append(
            {
                "event": "config_rollback_applied",
                "agent_id": agent_id,
                "config": dict(self.config),
                "rollback_count": self.rollback_count,
            }
        )


def support_reply_node(state: Dict[str, Any], adapter: NodeConfigAdapter) -> Dict[str, Any]:
    """A plain callable shaped like a LangGraph node."""
    ticket = state.get("ticket", "")
    if not ticket:
        raise ValueError("missing ticket")
    if adapter.config["mode"] == "broken":
        raise RuntimeError("regression: patched node routes to an unstable model")

    return {
        **state,
        "reply": "We found the failure evidence and kept the safe route.",
        "model": adapter.config["model"],
        "tool_fanout": adapter.config["tool_fanout"],
    }


def run_guarded_node(
    loop: SelfImprovingLoop,
    adapter: NodeConfigAdapter,
    state: Dict[str, Any],
    task: str,
) -> Dict[str, Any]:
    """Wrap the node exactly where a graph runner would call it."""
    return loop.track(
        agent_id=AGENT_ID,
        task=task,
        execute_fn=lambda: support_reply_node(state, adapter),
        context={
            "framework_style": "langgraph",
            "node": "support_reply_node",
            "input_keys": sorted(state.keys()),
            "current_model": adapter.config["model"],
            "current_mode": adapter.config["mode"],
        },
    )


def write_event_trail(
    data_dir: Path,
    loop: SelfImprovingLoop,
    strategy: OneBadNodePatchStrategy,
    adapter: NodeConfigAdapter,
    steps: List[Dict[str, Any]],
) -> Path:
    trail_path = data_dir / "langgraph_regression_guard_event_trail.jsonl"
    records: List[Dict[str, Any]] = []
    records.extend({"source": "demo", **step} for step in steps)
    records.extend({"source": "strategy", **event} for event in strategy.events)
    records.extend({"source": "config_adapter", **event} for event in adapter.events)
    records.extend({"source": "trace", **trace} for trace in loop.trace_store.load(AGENT_ID))
    records.extend(
        {"source": "rollback", **entry}
        for entry in loop.auto_rollback.get_rollback_history(AGENT_ID)
    )

    with trail_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    return trail_path


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_langgraph_regression_guard_"))
    strategy = OneBadNodePatchStrategy()
    adapter = NodeConfigAdapter()
    loop = SelfImprovingLoop(
        data_dir=str(data_dir),
        storage="sqlite",
        strategy=strategy,
        config_adapter=adapter,
    )
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    steps: List[Dict[str, Any]] = []
    state = {"ticket": "customer reports repeated agent routing failures"}

    baseline = run_guarded_node(loop, adapter, state, "baseline langgraph node call")
    assert baseline["success"] is True
    steps.append({"event": "langgraph_node_baseline_pass", "result": baseline})

    seed_failure = loop.track(
        agent_id=AGENT_ID,
        task="seed node failure",
        execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("node quality dropped")),
        context={"framework_style": "langgraph", "node": "support_reply_node"},
    )
    assert seed_failure["improvement_triggered"] is True
    assert seed_failure["improvement_applied"] == 1
    assert adapter.config["mode"] == "broken"
    steps.append({"event": "node_failure_triggered_patch", "result": seed_failure})

    # Keep the bad patch in place while the verification window fills. This
    # proves rollback comes from regression evidence, not from another patch.
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=999,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    rollback_result = None
    for i in range(10):
        result = run_guarded_node(
            loop,
            adapter,
            state,
            f"post-patch regression check {i + 1}",
        )
        steps.append({"event": "post_patch_regression_check", "index": i + 1, "result": result})
        if result["rollback_executed"]:
            rollback_result = result["rollback_executed"]
            steps.append({"event": "rollback_executed", "result": rollback_result})
            break

    assert rollback_result is not None
    assert rollback_result["success"] is True
    assert rollback_result["restore_applied"] is True
    assert rollback_result["restore_source"] == "config_adapter"
    assert adapter.rollback_count == 1
    assert adapter.config["mode"] == "stable"

    recovered = run_guarded_node(loop, adapter, state, "recovered langgraph node call")
    assert recovered["success"] is True
    steps.append({"event": "final_node_recovered", "result": recovered})

    trail_path = write_event_trail(data_dir, loop, strategy, adapter, steps)

    print("langgraph node baseline pass")
    print("trace recorded")
    print("success_rate / latency regression checked")
    print("regression detected")
    print("rollback executed")
    print("final node recovered")
    print(f"event trail written: {trail_path}")
    print(f"demo data dir: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
