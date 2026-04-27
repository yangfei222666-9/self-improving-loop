"""Executable examples should stay honest and runnable."""

import json
import subprocess
import sys
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def test_regression_rollback_demo_runs_end_to_end():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "regression_rollback_demo.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    for phrase in [
        "baseline pass",
        "failure detected",
        "improvement proposed",
        "backup created",
        "patch applied",
        "quality worse",
        "rollback executed",
        "final status recovered",
        "event trail written:",
    ]:
        assert phrase in output

    trail_path = None
    for line in output.splitlines():
        if line.startswith("event trail written: "):
            trail_path = Path(line.split(": ", 1)[1])
            break

    assert trail_path is not None
    assert trail_path.exists()

    records = [
        json.loads(line)
        for line in trail_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    events = {record.get("event") for record in records}
    sources = {record.get("source") for record in records}

    assert "trace" in sources
    assert "rollback" in sources
    assert "rollback_restored_config" in events
    run_ids = {record.get("run_id") for record in records}
    assert len(run_ids) == 1
    assert any(
        record.get("event") == "final_status_recovered"
        and (record.get("result") or {}).get("success") is True
        for record in records
    )

    verify = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "verify_regression_rollback_event_trail.py"),
            str(trail_path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "verdict=ok" in verify.stdout


def test_wrap_existing_agent_example_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "wrap_existing_agent.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    for phrase in [
        "existing agent wrapped",
        "failure detected",
        "strategy patch applied",
        "trace file:",
    ]:
        assert phrase in output


def test_langgraph_style_node_example_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "langgraph_style_node.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    for phrase in [
        "langgraph-style node wrapped",
        "trace written",
        "trace file:",
    ]:
        assert phrase in output


def test_langgraph_regression_guard_example_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "05_langgraph_regression_guard.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    for phrase in [
        "langgraph node baseline pass",
        "trace recorded",
        "success_rate / latency regression checked",
        "regression detected",
        "rollback executed",
        "final node recovered",
        "event trail written:",
    ]:
        assert phrase in output


def test_hermes_skill_regression_guard_example_runs():
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "06_hermes_skill_regression_guard.py")],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    output = result.stdout
    for phrase in [
        "hermes-style skill baseline pass",
        "bad skill config patch",
        "skill repeated failures",
        "trace recorded",
        "rollback restores previous config",
        "event trail written",
        "event trail path:",
    ]:
        assert phrase in output


def _write_trail(records):
    path = Path(tempfile.mkdtemp(prefix="sil_bad_trail_")) / "trail.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _valid_records():
    run_id = "test-run"
    backup = {"mode": "baseline", "timeout_sec": 30, "prompt_variant": "safe-v1"}
    return [
        {"source": "demo", "run_id": run_id, "event": "baseline_pass", "result": {"success": True}},
        {"source": "demo", "run_id": run_id, "event": "failure_detected", "result": {"success": False}},
        {"source": "demo", "run_id": run_id, "event": "backup_created", "expected_backup_config": backup},
        {"source": "strategy", "run_id": run_id, "event": "rollback_restored_config", "config": backup},
        {"source": "demo", "run_id": run_id, "event": "rollback_executed", "result": {"backup_id": "b1"}},
        {"source": "rollback", "run_id": run_id, "backup_id": "b1", "config_restored": backup},
        {"source": "demo", "run_id": run_id, "event": "final_status_recovered", "result": {"success": True}},
        {"source": "trace", "run_id": run_id, "agent_id": "support-agent-demo", "success": False},
    ]


def _run_verifier(path: Path):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "verify_regression_rollback_event_trail.py"),
            str(path),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )


def test_event_trail_verifier_rejects_out_of_order_events():
    records = _valid_records()
    records[0], records[4] = records[4], records[0]
    result = _run_verifier(_write_trail(records))
    assert result.returncode == 1
    assert "invalid_event_order" in result.stdout


def test_event_trail_verifier_rejects_mixed_run_ids():
    records = _valid_records()
    records[-1]["run_id"] = "other-run"
    result = _run_verifier(_write_trail(records))
    assert result.returncode == 1
    assert "invalid_run_ids" in result.stdout


def test_event_trail_verifier_rejects_fake_restore_config():
    records = _valid_records()
    for record in records:
        if record.get("event") == "rollback_restored_config":
            record["config"] = {"mode": "broken"}
    result = _run_verifier(_write_trail(records))
    assert result.returncode == 1
    assert "rollback_restore_config_mismatch" in result.stdout


def test_event_trail_verifier_rejects_missing_ordered_event():
    records = [record for record in _valid_records() if record.get("event") != "failure_detected"]
    result = _run_verifier(_write_trail(records))
    assert result.returncode == 1
    assert "missing_ordered_events" in result.stdout
    assert "invalid_event_order" in result.stdout
