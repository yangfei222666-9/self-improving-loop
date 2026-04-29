#!/usr/bin/env python3
"""Verify the bundled agent eval case JSONL packet.

The packet is intentionally conservative: it may describe failures that require
review, but it must never authorize judgment, paper-buy, trade, or promote.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_LABELS = {
    "artifact_hash_mismatch",
    "config_patch_regression",
    "context_drift",
    "duplicate_request",
    "false_success",
    "http_200_empty_output",
    "human_review_missing",
    "latency_regression",
    "missing_event_trail",
    "partial_output_truncation",
    "patch_without_test",
    "provider_route_drift",
    "rollback_missing",
    "silent_failure",
    "stale_artifact",
    "success_rate_regression",
    "tool_call_noop",
    "unsafe_action_escalation",
}

ALLOWED_VERDICTS = {"blocked", "learning_only", "manual_review_required"}
REQUIRED_TOP_LEVEL = {
    "agent_stack",
    "case_id",
    "domain",
    "evidence_required",
    "expected_routing",
    "failure_labels",
    "observed_failure",
    "prompt_summary",
    "regression_guard_action",
    "signals",
    "task_type",
    "trace",
}
FORBIDDEN_TRUE_FLAGS = {
    "judgment_allowed",
    "paper_buy_allowed",
    "promote_allowed",
    "trade_allowed",
}


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            failures.append(f"line_{line_no}:invalid_json:{exc.msg}")
            continue
        if not isinstance(record, dict):
            failures.append(f"line_{line_no}:not_object")
            continue
        records.append(record)
    return records, failures


def verify_record(record: dict[str, Any], index: int) -> list[str]:
    case_id = str(record.get("case_id") or f"line_{index}")
    failures: list[str] = []

    missing = sorted(REQUIRED_TOP_LEVEL - set(record))
    if missing:
        failures.append(f"{case_id}:missing_fields={missing}")

    labels = record.get("failure_labels")
    if not isinstance(labels, list) or not labels:
        failures.append(f"{case_id}:failure_labels_missing_or_empty")
    else:
        unknown = sorted(label for label in labels if label not in ALLOWED_LABELS)
        if unknown:
            failures.append(f"{case_id}:unknown_labels={unknown}")

    signals = record.get("signals")
    if not isinstance(signals, dict):
        failures.append(f"{case_id}:signals_not_object")
    else:
        if not isinstance(signals.get("hard"), list):
            failures.append(f"{case_id}:signals_hard_not_list")
        if not isinstance(signals.get("soft"), list):
            failures.append(f"{case_id}:signals_soft_not_list")

    trace = record.get("trace")
    if not isinstance(trace, dict):
        failures.append(f"{case_id}:trace_not_object")
    else:
        if not isinstance(trace.get("event_flow_present"), bool):
            failures.append(f"{case_id}:trace_event_flow_present_not_bool")
        if not isinstance(trace.get("artifact_present"), bool):
            failures.append(f"{case_id}:trace_artifact_present_not_bool")

    routing = record.get("expected_routing")
    if not isinstance(routing, dict):
        failures.append(f"{case_id}:expected_routing_not_object")
    else:
        verdict = routing.get("verdict")
        if verdict not in ALLOWED_VERDICTS:
            failures.append(f"{case_id}:unsupported_verdict={verdict}")
        for flag in FORBIDDEN_TRUE_FLAGS:
            if routing.get(flag) is not False:
                failures.append(f"{case_id}:{flag}_not_false")
        if not isinstance(routing.get("human_review_required"), bool):
            failures.append(f"{case_id}:human_review_required_not_bool")

    for field in ("evidence_required", "regression_guard_action"):
        value = record.get(field)
        if not isinstance(value, list) or not value:
            failures.append(f"{case_id}:{field}_missing_or_empty")

    return failures


def main(argv: list[str]) -> int:
    if len(argv) > 2:
        print("usage: verify_agent_eval_cases.py [agent_eval_cases.jsonl]")
        return 2

    path = (
        Path(argv[1]).expanduser()
        if len(argv) == 2
        else Path(__file__).with_name("agent_eval_cases.jsonl")
    )
    path = path.resolve()
    if not path.exists():
        print(f"verdict=blocked")
        print(f"missing_eval_cases={path}")
        return 1

    records, failures = load_jsonl(path)
    if len(records) < 30:
        failures.append(f"case_count_lt_30:{len(records)}")

    case_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for index, record in enumerate(records, 1):
        case_id = str(record.get("case_id") or f"line_{index}")
        if case_id in case_ids:
            duplicate_ids.add(case_id)
        case_ids.add(case_id)
        failures.extend(verify_record(record, index))

    if duplicate_ids:
        failures.append(f"duplicate_case_ids={sorted(duplicate_ids)}")

    if failures:
        print("verdict=failed")
        print(f"case_count={len(records)}")
        for failure in failures:
            print(failure)
        return 1

    print("verdict=ok")
    print(f"case_count={len(records)}")
    print("judgment_allowed=false")
    print("paper_buy_allowed=false")
    print("trade_allowed=false")
    print("promote_allowed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

