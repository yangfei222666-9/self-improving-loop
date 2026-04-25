"""Timestamp parsing helpers shared by trace consumers."""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Optional


def parse_trace_timestamp(trace: Mapping) -> Optional[datetime]:
    """Return a timestamp from either canonical ``timestamp`` or legacy start_time."""

    raw = trace.get("timestamp") or trace.get("start_time")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
