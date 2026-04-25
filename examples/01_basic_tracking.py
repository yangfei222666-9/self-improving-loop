#!/usr/bin/env python3
"""Basic tracking example.

Use this first. It proves the smallest contract:

agent call -> execute_with_improvement -> trace persisted -> stats readable.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_basic_tracking_"))
    loop = SelfImprovingLoop(data_dir=str(data_dir), storage="sqlite")

    result = loop.execute_with_improvement(
        agent_id="basic-agent",
        task="answer one request",
        execute_fn=lambda: {"answer": "ok"},
        context={"example": "01_basic_tracking"},
    )

    stats = loop.get_improvement_stats("basic-agent")
    assert result["success"] is True
    assert stats["total_tasks"] == 1

    print("basic tracking ok")
    print(f"data dir: {data_dir}")
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
