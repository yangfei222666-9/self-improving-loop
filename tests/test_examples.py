"""Executable examples should stay honest and runnable."""

import subprocess
import sys
from pathlib import Path

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
