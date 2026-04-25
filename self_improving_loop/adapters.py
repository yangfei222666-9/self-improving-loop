"""Adapter contracts for connecting the loop to real agent configuration."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class ConfigAdapter(Protocol):
    """Minimal contract for rollback-first agent config control.

    The loop owns tracking, thresholds, regression detection, and rollback
    decisions. Your application owns how config is read and restored.
    """

    def get_config(self, agent_id: str) -> Dict[str, Any]:
        """Return the current full config before a patch is applied."""
        ...

    def apply_config(self, agent_id: str, config_patch: Dict[str, Any]) -> bool:
        """Apply a proposed patch. Return False to reject it explicitly."""
        ...

    def rollback_config(self, agent_id: str, backup_config: Dict[str, Any]) -> None:
        """Restore a previously backed-up full config."""
        ...
