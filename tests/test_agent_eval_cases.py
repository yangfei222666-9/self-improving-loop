"""The bundled eval cases should stay parseable and non-authorizing."""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_agent_eval_cases_verify():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples" / "verify_agent_eval_cases.py"),
            str(ROOT / "examples" / "agent_eval_cases.jsonl"),
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "verdict=ok" in result.stdout
    assert "case_count=30" in result.stdout
    assert "judgment_allowed=false" in result.stdout
    assert "paper_buy_allowed=false" in result.stdout
    assert "trade_allowed=false" in result.stdout
    assert "promote_allowed=false" in result.stdout

