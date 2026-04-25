#!/usr/bin/env python3
"""LangGraph-style adapter example.

No LangGraph dependency is required here. LangGraph nodes are callables that
receive state and return state; wrap that callable with execute_with_improvement.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop


def summarize_node(state: dict) -> dict:
    text = state.get("text", "")
    if not text:
        raise ValueError("missing text")
    return {
        **state,
        "summary": text[:48],
    }


def guarded_node(loop: SelfImprovingLoop, state: dict) -> dict:
    result = loop.execute_with_improvement(
        agent_id="langgraph-summary-node",
        task="summarize state",
        execute_fn=lambda: summarize_node(state),
        context={"framework": "langgraph-style", "node": "summarize_node"},
    )
    if not result["success"]:
        raise RuntimeError(result["error"])
    return result["result"]


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_langgraph_adapter_"))
    loop = SelfImprovingLoop(data_dir=str(data_dir), storage="sqlite")
    output = guarded_node(loop, {"text": "Agent reliability needs regression evidence."})

    assert output["summary"] == "Agent reliability needs regression evidence."
    assert loop.get_improvement_stats("langgraph-summary-node")["total_tasks"] == 1

    print("langgraph adapter ok")
    print(f"data dir: {data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
