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
