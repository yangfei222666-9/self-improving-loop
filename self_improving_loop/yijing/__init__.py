"""Yijing-inspired policy strategy.

This module treats I Ching concepts as an engineering state machine:
six runtime dimensions -> six lines -> a hexagram state -> a bounded policy
patch. It is a strategy layer, not a judgment engine.
"""

from .hexagram import CORE_HEXAGRAMS, HexagramState, identify_hexagram
from .lines import DIMENSIONS, LineSignal, score_lines
from .policies import policy_for_hexagram
from .strategy import YijingEvolutionStrategy

__all__ = [
    "CORE_HEXAGRAMS",
    "DIMENSIONS",
    "HexagramState",
    "LineSignal",
    "YijingEvolutionStrategy",
    "identify_hexagram",
    "policy_for_hexagram",
    "score_lines",
]
