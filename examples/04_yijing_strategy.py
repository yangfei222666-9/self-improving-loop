#!/usr/bin/env python3
"""Yijing strategy example.

This proves the engineering interpretation:

runtime traces -> six line scores -> hexagram state -> bounded policy patch.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop, YijingEvolutionStrategy


class RuntimeConfig:
    def __init__(self) -> None:
        self.config = {"mode": "normal", "max_tool_fanout": 4}
        self.applied_patch = None

    def get_config(self, agent_id: str) -> dict:
        return dict(self.config)

    def apply_config(self, agent_id: str, config_patch: dict) -> bool:
        self.applied_patch = dict(config_patch)
        self.config.update({
            key: value
            for key, value in config_patch.items()
            if key in {"max_tool_fanout", "retry_limit", "timeout_multiplier"}
        })
        return True

    def rollback_config(self, agent_id: str, backup_config: dict) -> None:
        self.config = dict(backup_config)


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_yijing_strategy_"))
    adapter = RuntimeConfig()
    loop = SelfImprovingLoop(
        data_dir=str(data_dir),
        storage="sqlite",
        strategy=YijingEvolutionStrategy(latency_target_sec=0.000001),
        config_adapter=adapter,
    )
    loop.adaptive_threshold.set_manual_threshold(
        "yijing-agent",
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
    )

    def failing_call():
        time.sleep(0.01)
        raise RuntimeError("provider route schema handoff sync quota error")

    result = loop.execute_with_improvement(
        agent_id="yijing-agent",
        task="provider route and governance failed",
        execute_fn=failing_call,
        context={"provider": "demo", "route_ok": False, "handoff_ok": False, "budget": "quota"},
    )

    assert result["improvement_triggered"] is True
    assert result["improvement_applied"] == 1
    assert adapter.applied_patch is not None
    assert adapter.applied_patch["strategy_source"] == "yijing_hexagram_state_machine"
    assert "hexagram" in adapter.applied_patch
    assert "dimensions" in adapter.applied_patch
    assert adapter.applied_patch["hexagram"]["name"] == "kun"

    print("yijing strategy ok")
    print(f"hexagram: {adapter.applied_patch['hexagram']['display_name']}")
    print(f"policy_action: {adapter.applied_patch['policy_action']}")
    print(f"data dir: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
