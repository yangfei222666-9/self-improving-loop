#!/usr/bin/env python3
"""Wrap an existing agent callable with self-improving-loop.

This is the smallest useful integration shape:

existing agent -> execute_with_improvement -> traces + guarded strategy +
rollback if the strategy makes things worse.

No framework dependency is required. Replace ``agent.run`` with your real
LangGraph / CrewAI / AutoGen / MCP tool call.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop


class ExistingAgent:
    def __init__(self) -> None:
        self.config = {"mode": "normal", "max_retries": 1}

    def run(self, prompt: str) -> dict:
        if self.config["mode"] == "broken":
            raise RuntimeError("agent regression after config change")
        return {
            "answer": f"handled: {prompt}",
            "config": dict(self.config),
        }


class GuardedStrategy:
    """A strategy hook that knows how to patch and restore this agent."""

    def __init__(self, agent: ExistingAgent) -> None:
        self.agent = agent
        self._proposed_once = False

    def current_config(self, agent_id: str) -> dict:
        return dict(self.agent.config)

    def analyze(
        self,
        agent_id: str,
        traces: list[dict],
        before_metrics: dict,
    ) -> dict | None:
        if self._proposed_once:
            return None
        self._proposed_once = True
        return {"max_retries": 2}

    def apply(self, agent_id: str, config_patch: dict) -> bool:
        self.agent.config.update(config_patch)
        return True

    def rollback(self, agent_id: str, backup_config: dict) -> None:
        self.agent.config = dict(backup_config)


def main() -> int:
    agent = ExistingAgent()
    strategy = GuardedStrategy(agent)
    data_dir = Path(tempfile.mkdtemp(prefix="sil_existing_agent_"))
    loop = SelfImprovingLoop(data_dir=str(data_dir), improvement_strategy=strategy)
    loop.adaptive_threshold.set_manual_threshold(
        "existing-agent",
        failure_threshold=1,
        analysis_window_hours=24,
        cooldown_hours=0,
    )

    ok = loop.execute_with_improvement(
        agent_id="existing-agent",
        task="normal request",
        execute_fn=lambda: agent.run("hello"),
    )
    assert ok["success"] is True

    failure = loop.execute_with_improvement(
        agent_id="existing-agent",
        task="upstream timeout",
        execute_fn=lambda: (_ for _ in ()).throw(RuntimeError("upstream timeout")),
    )
    assert failure["improvement_triggered"] is True
    assert failure["improvement_applied"] == 1
    assert agent.config["max_retries"] == 2

    print("existing agent wrapped")
    print("failure detected")
    print("strategy patch applied")
    print(f"trace file: {data_dir / 'traces.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
