#!/usr/bin/env python3
"""Regression rollback demo for self-improving-loop.

This demo intentionally applies a bad strategy patch so the runtime can prove
the safety path:

baseline pass -> failure detected -> improvement proposed -> backup created ->
patch applied -> quality worse -> rollback executed -> final recovered ->
event trail written.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop

AGENT_ID = "support-agent-demo"


class BadPatchStrategy:
    """A minimal strategy that proposes one deliberately bad patch."""

    def __init__(self) -> None:
        self.config = {
            "mode": "baseline",
            "timeout_sec": 30,
            "prompt_variant": "safe-v1",
        }
        self.events: list[dict] = []
        self._already_proposed = False

    def current_config(self, agent_id: str) -> dict:
        self.events.append(
            {
                "event": "current_config",
                "agent_id": agent_id,
                "config": dict(self.config),
            }
        )
        return dict(self.config)

    def analyze(self, agent_id: str, traces: list[dict], before_metrics: dict) -> dict | None:
        if self._already_proposed:
            self.events.append(
                {
                    "event": "improvement_skipped",
                    "agent_id": agent_id,
                    "reason": "one_patch_demo_only",
                }
            )
            return None

        self._already_proposed = True
        patch = {
            "mode": "broken",
            "prompt_variant": "unsafe-v2",
            "reason": "demo_bad_patch_to_exercise_rollback",
        }
        self.events.append(
            {
                "event": "improvement_proposed",
                "agent_id": agent_id,
                "trace_count": len(traces),
                "before_metrics": before_metrics,
                "patch": patch,
            }
        )
        return patch

    def apply(self, agent_id: str, config_patch: dict) -> bool:
        self.config.update(config_patch)
        self.events.append(
            {
                "event": "patch_applied",
                "agent_id": agent_id,
                "config": dict(self.config),
            }
        )
        return True

    def rollback(self, agent_id: str, backup_config: dict) -> None:
        self.config = dict(backup_config)
        self.events.append(
            {
                "event": "rollback_restored_config",
                "agent_id": agent_id,
                "config": dict(self.config),
            }
        )


def make_task(strategy: BadPatchStrategy, *, forced_failure: bool = False):
    def task() -> dict:
        if forced_failure:
            raise RuntimeError("seed failure: initial regression signal")
        if strategy.config["mode"] == "broken":
            raise RuntimeError("regression: bad patch made the agent worse")
        return {"status": "ok", "mode": strategy.config["mode"]}

    return task


def write_event_trail(data_dir: Path, strategy: BadPatchStrategy, steps: list[dict]) -> Path:
    trail_path = data_dir / "regression_rollback_event_trail.jsonl"
    trace_path = data_dir / "traces.jsonl"
    rollback_path = data_dir / "rollback_history.jsonl"

    records: list[dict] = []
    records.extend({"source": "demo", **step} for step in steps)
    records.extend({"source": "strategy", **event} for event in strategy.events)

    if trace_path.exists():
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append({"source": "trace", **json.loads(line)})

    if rollback_path.exists():
        for line in rollback_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append({"source": "rollback", **json.loads(line)})

    with trail_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return trail_path


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_rollback_demo_"))
    strategy = BadPatchStrategy()
    loop = SelfImprovingLoop(
        data_dir=str(data_dir),
        improvement_strategy=strategy,
    )
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    steps: list[dict] = []

    try:
        # 1. Establish a real baseline.
        baseline = loop.execute_with_improvement(
            agent_id=AGENT_ID,
            task="baseline pass",
            execute_fn=make_task(strategy),
        )
        steps.append({"event": "baseline_pass", "result": baseline})

        # 2. Seed one real failure so the loop triggers the strategy.
        failure = loop.execute_with_improvement(
            agent_id=AGENT_ID,
            task="seed failure",
            execute_fn=make_task(strategy, forced_failure=True),
        )
        steps.append({"event": "failure_detected", "result": failure})

        backup_info = loop.state.get("backups", {}).get(AGENT_ID)
        if not backup_info:
            raise AssertionError("expected backup after improvement apply")
        steps.append({"event": "backup_created", "backup_info": backup_info})

        # Prevent repeated demo patches while rollback verification collects
        # post-change evidence. Rollback still runs after every task.
        loop.adaptive_threshold.set_manual_threshold(
            AGENT_ID,
            failure_threshold=999,
            analysis_window_hours=24,
            cooldown_hours=0,
            is_critical=True,
        )

        # 3. Prove the patch made quality worse. AutoRollback verifies after
        # 10 total recent tasks.
        rollback_result = None
        for i in range(10):
            result = loop.execute_with_improvement(
                agent_id=AGENT_ID,
                task=f"post-patch verification {i + 1}",
                execute_fn=make_task(strategy),
            )
            steps.append({"event": "post_patch_check", "index": i + 1, "result": result})
            if result["rollback_executed"]:
                rollback_result = result["rollback_executed"]
                steps.append({"event": "rollback_executed", "result": rollback_result})
                break

        if not rollback_result:
            raise AssertionError("expected rollback after quality regression")

        # 4. Confirm the restored config actually works.
        recovered = loop.execute_with_improvement(
            agent_id=AGENT_ID,
            task="final recovered pass",
            execute_fn=make_task(strategy),
        )
        steps.append({"event": "final_status_recovered", "result": recovered})
        if not recovered["success"]:
            raise AssertionError("final recovered task should pass after rollback")

        trail_path = write_event_trail(data_dir, strategy, steps)
        steps.append({"event": "event_trail_written", "path": str(trail_path)})

        print("baseline pass")
        print("failure detected")
        print("improvement proposed")
        print("backup created")
        print("patch applied")
        print("quality worse")
        print("rollback executed")
        print("final status recovered")
        print(f"event trail written: {trail_path}")
        print(f"demo data dir: {data_dir}")
        return 0
    except Exception:
        # Keep failed artifacts for debugging.
        raise


if __name__ == "__main__":
    raise SystemExit(main())
