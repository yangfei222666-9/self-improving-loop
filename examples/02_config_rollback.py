#!/usr/bin/env python3
"""Config rollback example.

This is the core product demo:

1. A strategy proposes a bad config patch after a seed failure.
2. ConfigAdapter applies the patch and owns the real runtime config.
3. The loop detects regression and calls rollback_config().
4. The agent recovers on the restored config.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop


AGENT_ID = "rollback-demo-agent"


class OneBadPatchStrategy:
    def __init__(self) -> None:
        self.proposed = False

    def analyze(self, agent_id: str, traces: list[dict], before_metrics: dict):
        if self.proposed:
            return None
        self.proposed = True
        return {"mode": "broken", "prompt_variant": "bad-v2"}


class InMemoryConfigAdapter:
    def __init__(self) -> None:
        self.config = {"mode": "stable", "prompt_variant": "safe-v1"}
        self.rollback_count = 0

    def get_config(self, agent_id: str) -> dict:
        return dict(self.config)

    def apply_config(self, agent_id: str, config_patch: dict) -> bool:
        self.config.update(config_patch)
        return True

    def rollback_config(self, agent_id: str, backup_config: dict) -> None:
        self.config = dict(backup_config)
        self.rollback_count += 1


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_config_rollback_"))
    adapter = InMemoryConfigAdapter()
    loop = SelfImprovingLoop(
        data_dir=str(data_dir),
        storage="sqlite",
        improvement_strategy=OneBadPatchStrategy(),
        config_adapter=adapter,
    )
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    def agent_call() -> dict:
        if adapter.config["mode"] == "broken":
            raise RuntimeError("bad patch regressed the agent")
        return {"status": "ok", "config": dict(adapter.config)}

    # Establish baseline.
    assert loop.execute_with_improvement(
        agent_id=AGENT_ID,
        task="baseline",
        execute_fn=agent_call,
    )["success"] is True

    # Seed one failure. This triggers the bad patch and creates a backup.
    seed = loop.execute_with_improvement(
        agent_id=AGENT_ID,
        task="seed failure",
        execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("upstream failure")),
    )
    assert seed["improvement_triggered"] is True
    assert seed["improvement_applied"] == 1
    assert adapter.config["mode"] == "broken"

    # Stop additional patches; collect regression evidence until rollback fires.
    loop.adaptive_threshold.set_manual_threshold(
        AGENT_ID,
        failure_threshold=999,
        analysis_window_hours=24,
        cooldown_hours=0,
        is_critical=True,
    )

    rollback_result = None
    for i in range(10):
        result = loop.execute_with_improvement(
            agent_id=AGENT_ID,
            task=f"post-patch verification {i + 1}",
            execute_fn=agent_call,
        )
        if result["rollback_executed"]:
            rollback_result = result["rollback_executed"]
            break

    assert rollback_result is not None
    assert rollback_result["success"] is True
    assert rollback_result["restore_applied"] is True
    assert rollback_result["restore_source"] == "config_adapter"
    assert adapter.rollback_count == 1
    assert adapter.config["mode"] == "stable"

    recovered = loop.execute_with_improvement(
        agent_id=AGENT_ID,
        task="recovered request",
        execute_fn=agent_call,
    )
    assert recovered["success"] is True

    print("config rollback ok")
    print(f"restore source: {rollback_result['restore_source']}")
    print(f"data dir: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
