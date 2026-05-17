import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_startup_recovery_benchmark_runs_from_checkout():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "benchmarks" / "startup_recovery.py"),
            "--traces",
            "10",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout.strip())
    assert record["trace_count"] == 10
    assert record["total_tasks"] == 10
    assert record["success_rate"] == 0.9
    assert "calculate_metrics_ms" in record
