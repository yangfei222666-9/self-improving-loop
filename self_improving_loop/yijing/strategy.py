"""Yijing evolution strategy for SelfImprovingLoop."""

from __future__ import annotations

from typing import Dict, Mapping, Sequence

from .hexagram import identify_hexagram
from .lines import lines_to_patch_metadata, score_lines
from .policies import policy_for_hexagram


class YijingEvolutionStrategy:
    """Convert traces into a bounded policy patch.

    This is not fortune telling and not a high-trust decision maker. It is a
    deterministic state router for agent reliability:

    traces -> six engineering lines -> hexagram state -> policy patch.
    """

    def __init__(self, *, latency_target_sec: float = 5.0):
        self.latency_target_sec = latency_target_sec

    def analyze(
        self,
        agent_id: str,
        traces: Sequence[Mapping],
        before_metrics: Mapping | None = None,
    ) -> Dict:
        lines = score_lines(
            traces,
            before_metrics,
            latency_target_sec=self.latency_target_sec,
        )
        hexagram = identify_hexagram(lines)
        policy = policy_for_hexagram(hexagram)
        return {
            "strategy_source": "yijing_hexagram_state_machine",
            "agent_id": agent_id,
            **policy,
            **lines_to_patch_metadata(lines),
        }
