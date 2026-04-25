#!/usr/bin/env python3
"""Measure restart/startup cost with a pre-seeded JSONL trace file.

This benchmark intentionally seeds the trace file directly so the reported
startup cost does not include trace generation or fsync cost.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from self_improving_loop import SelfImprovingLoop


def _seed_traces(data_dir: Path, count: int, agent_id: str) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    traces_file = data_dir / "traces.jsonl"
    with open(traces_file, "w", encoding="utf-8") as f:
        for index in range(count):
            f.write(
                json.dumps(
                    {
                        "agent_id": agent_id,
                        "task": f"benchmark-task-{index}",
                        "success": index % 10 != 0,
                        "duration_sec": 0.01 + (index % 5) * 0.001,
                        "timestamp": "2026-04-26T00:00:00",
                    }
                )
                + "\n"
            )


def _measure(count: int, agent_id: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="sil-startup-") as tmp:
        data_dir = Path(tmp)
        _seed_traces(data_dir, count=count, agent_id=agent_id)

        start = time.perf_counter()
        loop = SelfImprovingLoop(data_dir=str(data_dir))
        init_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        stats = loop.get_improvement_stats(agent_id)
        stats_ms = (time.perf_counter() - start) * 1000

        start = time.perf_counter()
        metrics = loop._calculate_metrics(agent_id)
        metrics_ms = (time.perf_counter() - start) * 1000

    return {
        "trace_count": count,
        "init_ms": round(init_ms, 3),
        "get_stats_ms": round(stats_ms, 3),
        "calculate_metrics_ms": round(metrics_ms, 3),
        "total_tasks": stats["total_tasks"],
        "success_rate": round(metrics["success_rate"], 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--traces",
        type=int,
        nargs="+",
        default=[1000, 10000, 100000],
        help="Trace counts to seed before restart measurement.",
    )
    parser.add_argument("--agent-id", default="benchmark-agent")
    args = parser.parse_args()

    for count in args.traces:
        print(json.dumps(_measure(count, args.agent_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
