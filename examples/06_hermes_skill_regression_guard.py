#!/usr/bin/env python3
"""Hermes-style skill regression guard demo.

This example has no Hermes dependency. It models the seam where Hermes Agent,
or any skill-based agent runtime, calls a skill implementation:

Hermes-style skill call
-> bad skill config patch
-> skill repeated failures
-> trace recorded
-> ConfigAdapter rollback restores the previous config
-> event trail written
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

AGENT_ID = "hermes-research-skill"


class OneBadSkillPatchStrategy:
    """Propose one bad skill patch so rollback evidence is generated."""

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
                    "reason": "one_bad_skill_patch_demo_only",
                }
            )
            return {}

        self.proposed = True
        patch = {
            "skill_mode": "broken",
            "retrieval_depth": 0,
            "allow_unverified_sources": True,
            "reason": "demo_bad_skill_patch_to_prove_rollback",
        }
        self.events.append(
            {
                "event": "skill_patch_proposed",
                "agent_id": agent_id,
                "before_metrics": before_metrics,
                "trace_count": len(traces),
                "patch": patch,
            }
        )
        return patch


class SkillConfigAdapter:
    """In-memory owner for a Hermes-style skill config."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {
            "skill_mode": "stable",
            "retrieval_depth": 3,
            "allow_unverified_sources": False,
            "model": "safe-router",
        }
        self.rollback_count = 0
        self.events: List[Dict[str, Any]] = []

    def get_config(self, agent_id: str) -> Dict[str, Any]:
        self.events.append(
            {"event": "skill_config_backed_up", "agent_id": agent_id, "config": dict(self.config)}
        )
        return dict(self.config)

    def apply_config(self, agent_id: str, config_patch: Dict[str, Any]) -> bool:
        self.config.update(config_patch)
        self.events.append(
            {"event": "skill_config_patch_applied", "agent_id": agent_id, "config": dict(self.config)}
        )
        return True

    def rollback_config(self, agent_id: str, backup_config: Dict[str, Any]) -> None:
        self.config = dict(backup_config)
        self.rollback_count += 1
        self.events.append(
            {
                "event": "skill_config_rollback_applied",
                "agent_id": agent_id,
                "config": dict(self.config),
                "rollback_count": self.rollback_count,
            }
        )


def research_skill(args: Dict[str, Any], adapter: SkillConfigAdapter) -> Dict[str, Any]:
    """A plain callable shaped like a Hermes skill handler."""
    query = args.get("query", "")
    if not query:
        raise ValueError("missing query")
    if adapter.config["skill_mode"] == "broken":
        raise RuntimeError("skill regression: retrieval config returned no verified evidence")

    return {
        "skill": "research",
        "query": query,
        "answer": "verified evidence returned",
        "retrieval_depth": adapter.config["retrieval_depth"],
        "model": adapter.config["model"],
    }


def run_guarded_skill(
    loop: SelfImprovingLoop,
    adapter: SkillConfigAdapter,
    args: Dict[str, Any],
    task: str,
) -> Dict[str, Any]:
    """Wrap a skill call where Hermes or another skill runtime would invoke it."""
    return loop.track(
        agent_id=AGENT_ID,
        task=task,
        execute_fn=lambda: research_skill(args, adapter),
        context={
            "framework_style": "hermes_skill",
            "skill": "research",
            "input_keys": sorted(args.keys()),
            "skill_mode": adapter.config["skill_mode"],
            "model": adapter.config["model"],
        },
    )


def write_event_trail(
    data_dir: Path,
    loop: SelfImprovingLoop,
    strategy: OneBadSkillPatchStrategy,
    adapter: SkillConfigAdapter,
    steps: List[Dict[str, Any]],
) -> Path:
    trail_path = data_dir / "hermes_skill_regression_guard_event_trail.jsonl"
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
    data_dir = Path(tempfile.mkdtemp(prefix="sil_hermes_skill_regression_guard_"))
    strategy = OneBadSkillPatchStrategy()
    adapter = SkillConfigAdapter()
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
    args = {"query": "find evidence that rollback preserved agent behavior"}

    baseline = run_guarded_skill(loop, adapter, args, "baseline hermes-style skill call")
    assert baseline["success"] is True
    steps.append({"event": "hermes_skill_baseline_pass", "result": baseline})

    seed_failure = loop.track(
        agent_id=AGENT_ID,
        task="seed skill failure",
        execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("skill output quality dropped")),
        context={"framework_style": "hermes_skill", "skill": "research"},
    )
    assert seed_failure["improvement_triggered"] is True
    assert seed_failure["improvement_applied"] == 1
    assert adapter.config["skill_mode"] == "broken"
    steps.append({"event": "bad_skill_config_patch", "result": seed_failure})

    # Keep the bad skill config active until rollback evidence is sufficient.
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=999,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    rollback_result = None
    for i in range(10):
        result = run_guarded_skill(
            loop,
            adapter,
            args,
            f"post-patch skill failure check {i + 1}",
        )
        steps.append({"event": "skill_repeated_failure", "index": i + 1, "result": result})
        if result["rollback_executed"]:
            rollback_result = result["rollback_executed"]
            steps.append({"event": "skill_rollback_executed", "result": rollback_result})
            break

    assert rollback_result is not None
    assert rollback_result["success"] is True
    assert rollback_result["restore_applied"] is True
    assert rollback_result["restore_source"] == "config_adapter"
    assert adapter.rollback_count == 1
    assert adapter.config["skill_mode"] == "stable"

    recovered = run_guarded_skill(loop, adapter, args, "recovered hermes-style skill call")
    assert recovered["success"] is True
    steps.append({"event": "final_skill_recovered", "result": recovered})

    trail_path = write_event_trail(data_dir, loop, strategy, adapter, steps)

    print("hermes-style skill baseline pass")
    print("bad skill config patch")
    print("skill repeated failures")
    print("trace recorded")
    print("rollback restores previous config")
    print("event trail written")
    print(f"event trail path: {trail_path}")
    print(f"demo data dir: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
