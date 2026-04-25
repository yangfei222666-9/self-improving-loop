"""Policy patches for core hexagram states.

The patches are intentionally small. They are meant to be consumed by a
ConfigAdapter or strategy wrapper, validated in a canary window, and rolled back
if metrics regress.
"""

from __future__ import annotations

from typing import Dict

from .hexagram import HexagramState


CORE_POLICIES: Dict[str, Dict] = {
    "qian": {
        "policy_action": "canary_explore",
        "canary_ratio": 0.10,
        "reason": "all six dimensions are strong; prefer small exploration, not broad mutation",
    },
    "kun": {
        "policy_action": "conserve_and_rollback_bias",
        "canary_ratio": 0.0,
        "max_tool_fanout": 1,
        "auto_apply_enabled": False,
        "reason": "all six dimensions are weak; stop expansion and prefer rollback/recovery",
    },
    "zhen": {
        "policy_action": "fast_recover",
        "fallback_enabled": True,
        "max_tool_fanout": 1,
        "timeout_multiplier": 1.25,
        "reason": "sudden disturbance; isolate, reduce fanout, and switch fallback paths",
    },
    "kan": {
        "policy_action": "reduce_complexity",
        "max_tool_fanout": 1,
        "context_budget_multiplier": 0.75,
        "retry_limit": 1,
        "reason": "repeated risk state; simplify execution before retrying",
    },
    "bo": {
        "policy_action": "rollback_recent_change",
        "rollback_bias": True,
        "auto_apply_enabled": False,
        "reason": "degradation state; prefer reverting the latest risky change",
    },
    "fu": {
        "policy_action": "gradual_restore",
        "canary_ratio": 0.10,
        "restore_step": "small",
        "reason": "recovery signal; restore capability gradually",
    },
    "jiji": {
        "policy_action": "solidify",
        "promote_candidate": True,
        "canary_ratio": 0.0,
        "reason": "stable resolved state; preserve and document the working config",
    },
    "weiji": {
        "policy_action": "continue_canary",
        "canary_ratio": 0.05,
        "auto_apply_enabled": False,
        "reason": "not yet settled; continue canary and avoid full rollout",
    },
    "mixed": {
        "policy_action": "observe_and_bound",
        "canary_ratio": 0.05,
        "auto_apply_enabled": False,
        "reason": "mixed state outside the initial eight core policies; keep changes bounded",
    },
}


def policy_for_hexagram(state: HexagramState) -> Dict:
    """Return a bounded config patch for a hexagram state."""

    policy = dict(CORE_POLICIES.get(state.name, CORE_POLICIES["mixed"]))
    policy["hexagram"] = {
        "binary": state.binary,
        "name": state.name,
        "display_name": state.display_name,
        "moving_lines": list(state.moving_lines),
        "changed_binary": state.changed_binary,
        "changed_name": state.changed_name,
        "changed_display_name": state.changed_display_name,
    }
    return policy
