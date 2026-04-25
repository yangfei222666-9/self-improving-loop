#!/usr/bin/env python3
"""Wrap a LangGraph-style node without importing LangGraph.

LangGraph nodes are usually plain callables that accept state and return state.
This example keeps the dependency out of the package while showing the exact
integration seam:

    graph node(state) -> execute_with_improvement(...)

If you already use LangGraph, wrap the node body the same way.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from self_improving_loop import SelfImprovingLoop


def summarizer_node(state: dict) -> dict:
    text = state.get("text", "")
    if not text:
        raise ValueError("missing text")
    return {
        **state,
        "summary": text[:40],
    }


def main() -> int:
    data_dir = Path(tempfile.mkdtemp(prefix="sil_langgraph_style_"))
    loop = SelfImprovingLoop(data_dir=str(data_dir))

    result = loop.execute_with_improvement(
        agent_id="langgraph-style-summarizer",
        task="summarize graph state",
        execute_fn=lambda: summarizer_node({"text": "Agent reliability needs evidence."}),
        context={"framework_style": "langgraph", "node": "summarizer_node"},
    )

    assert result["success"] is True
    assert result["result"]["summary"] == "Agent reliability needs evidence."

    print("langgraph-style node wrapped")
    print("trace written")
    print(f"trace file: {data_dir / 'traces.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
