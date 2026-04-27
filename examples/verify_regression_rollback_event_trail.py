#!/usr/bin/env python3
"""Verify the regression rollback demo event trail.

This is intentionally small and dependency-free so external repro users can run
one machine-checkable command instead of eyeballing JSONL output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_EVENTS = {
    "baseline_pass",
    "failure_detected",
    "backup_created",
    "rollback_executed",
    "final_status_recovered",
}

ORDERED_EVENTS = [
    "baseline_pass",
    "failure_detected",
    "backup_created",
    "rollback_executed",
    "final_status_recovered",
]


def load_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid_jsonl line={line_no}: {exc}") from exc
    return records


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: verify_regression_rollback_event_trail.py <event_trail.jsonl>")
        return 2

    path = Path(argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"missing_event_trail: {path}")
        return 1

    records = load_jsonl(path)
    events = {record.get("event") for record in records}
    sources = {record.get("source") for record in records}
    run_ids = {record.get("run_id") for record in records}

    missing_events = sorted(REQUIRED_EVENTS - events)
    has_trace = "trace" in sources
    has_rollback = "rollback" in sources
    has_strategy_restore = any(record.get("event") == "rollback_restored_config" for record in records)
    final_recovered_ok = any(
        record.get("event") == "final_status_recovered"
        and ((record.get("result") or {}).get("success") is True)
        for record in records
    )
    event_positions: dict[str, int] = {}
    for index, record in enumerate(records):
        event = record.get("event")
        if event in ORDERED_EVENTS and event not in event_positions:
            event_positions[event] = index

    ordered_events_present = all(event in event_positions for event in ORDERED_EVENTS)
    ordered = ordered_events_present and all(
        event_positions[left] < event_positions[right]
        for left, right in zip(ORDERED_EVENTS, ORDERED_EVENTS[1:])
    )

    backup_records = [record for record in records if record.get("event") == "backup_created"]
    restore_records = [record for record in records if record.get("event") == "rollback_restored_config"]
    expected_backup_config = backup_records[-1].get("expected_backup_config") if backup_records else None
    restored_config = restore_records[-1].get("config") if restore_records else None
    rollback_matches_backup = bool(expected_backup_config and restored_config == expected_backup_config)

    rollback_events = [record for record in records if record.get("event") == "rollback_executed"]
    rollback_backup_id = ((rollback_events[-1].get("result") or {}).get("backup_id") if rollback_events else None)
    rollback_source_matches = any(
        record.get("source") == "rollback"
        and record.get("backup_id") == rollback_backup_id
        for record in records
    )

    failures: list[str] = []
    if len(run_ids) != 1 or None in run_ids:
        failures.append(f"invalid_run_ids={sorted(str(item) for item in run_ids)}")
    if missing_events:
        failures.append(f"missing_events={missing_events}")
    if not ordered_events_present:
        failures.append("missing_ordered_events")
    if not ordered:
        failures.append("invalid_event_order")
    if not has_trace:
        failures.append("missing_trace_records")
    if not has_rollback:
        failures.append("missing_rollback_records")
    if not has_strategy_restore:
        failures.append("missing_strategy_restore_event")
    if not rollback_matches_backup:
        failures.append("rollback_restore_config_mismatch")
    if not rollback_source_matches:
        failures.append("rollback_source_backup_id_mismatch")
    if not final_recovered_ok:
        failures.append("final_recovered_not_successful")

    if failures:
        print("verdict=failed")
        for failure in failures:
            print(failure)
        print(f"record_count={len(records)}")
        return 1

    print("verdict=ok")
    print(f"record_count={len(records)}")
    print("has_trace=true")
    print("has_rollback=true")
    print("has_strategy_restore=true")
    print("final_recovered_ok=true")
    print("event_order=valid")
    print("rollback_restore_config=matches_backup")
    print(f"run_id={next(iter(run_ids))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
