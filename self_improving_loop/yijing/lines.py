"""Map agent traces to six engineering lines.

Line order is bottom -> top:

1. stability
2. efficiency
3. learning_activity
4. routing_accuracy
5. collaboration
6. governance

Each line receives a 0..1 score.  ``state`` is yin/yang. ``moving`` marks the
dimension most likely to need policy attention.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

DIMENSIONS: Sequence[str] = (
    "stability",
    "efficiency",
    "learning_activity",
    "routing_accuracy",
    "collaboration",
    "governance",
)


@dataclass(frozen=True)
class LineSignal:
    """A scored runtime dimension mapped to a Yijing line."""

    position: int
    dimension: str
    score: float
    state: str
    moving: bool
    evidence: str

    @property
    def bit(self) -> int:
        return 1 if self.state == "yang" else 0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _success_rate(traces: Sequence[Mapping]) -> float:
    if not traces:
        return 1.0
    return sum(1 for trace in traces if trace.get("success")) / len(traces)


def _avg_duration(traces: Sequence[Mapping], before_metrics: Mapping | None) -> float:
    if before_metrics and "avg_duration_sec" in before_metrics:
        return float(before_metrics.get("avg_duration_sec") or 0.0)
    if not traces:
        return 0.0
    return sum(float(trace.get("duration_sec") or 0.0) for trace in traces) / len(traces)


def _failure_count(traces: Sequence[Mapping], keywords: Iterable[str]) -> int:
    lowered_keywords = tuple(keyword.lower() for keyword in keywords)
    count = 0
    for trace in traces:
        if trace.get("success"):
            continue
        context = trace.get("context") or {}
        haystack = " ".join(
            [
                str(trace.get("error") or ""),
                str(trace.get("task") or ""),
                " ".join(f"{key}={value}" for key, value in context.items()),
            ]
        ).lower()
        if any(keyword in haystack for keyword in lowered_keywords):
            count += 1
    return count


def _line(position: int, dimension: str, score: float, evidence: str) -> LineSignal:
    score = _clamp(score)
    return LineSignal(
        position=position,
        dimension=dimension,
        score=score,
        state="yang" if score >= 0.60 else "yin",
        moving=score < 0.45,
        evidence=evidence,
    )


def score_lines(
    traces: Sequence[Mapping],
    before_metrics: Mapping | None = None,
    *,
    latency_target_sec: float = 5.0,
) -> List[LineSignal]:
    """Score six runtime dimensions from traces.

    The scoring is intentionally conservative and transparent.  It is good
    enough to route a bounded policy patch, not to make high-trust decisions.
    """

    traces = list(traces)
    total = len(traces)
    failures = sum(1 for trace in traces if not trace.get("success"))
    success_rate = (
        float(before_metrics.get("success_rate"))
        if before_metrics and "success_rate" in before_metrics
        else _success_rate(traces)
    )
    avg_duration = _avg_duration(traces, before_metrics)
    consecutive_failures = (
        int(before_metrics.get("consecutive_failures") or 0) if before_metrics else 0
    )

    route_failures = _failure_count(
        traces,
        ("route", "model", "provider", "tool", "schema", "json"),
    )
    collaboration_failures = _failure_count(
        traces,
        ("handoff", "sync", "context", "collab", "coordination"),
    )
    governance_failures = _failure_count(
        traces,
        ("quota", "rate", "429", "auth", "permission", "budget", "cost"),
    )

    denominator = max(1, total)
    efficiency = 1.0 if avg_duration <= 0 else 1.0 - (avg_duration / max(latency_target_sec, 0.001))
    learning_activity = 0.5
    if total >= 3:
        learning_activity = 0.75
    if failures and total >= 3:
        learning_activity = 0.85
    if consecutive_failures >= 3:
        learning_activity = 0.35

    return [
        _line(1, "stability", success_rate, f"success_rate={success_rate:.2f}"),
        _line(2, "efficiency", efficiency, f"avg_duration_sec={avg_duration:.2f}"),
        _line(3, "learning_activity", learning_activity, f"traces={total}, failures={failures}"),
        _line(
            4,
            "routing_accuracy",
            1.0 - route_failures / denominator,
            f"route_failures={route_failures}/{denominator}",
        ),
        _line(
            5,
            "collaboration",
            1.0 - collaboration_failures / denominator,
            f"collaboration_failures={collaboration_failures}/{denominator}",
        ),
        _line(
            6,
            "governance",
            1.0 - governance_failures / denominator,
            f"governance_failures={governance_failures}/{denominator}",
        ),
    ]


def lines_to_patch_metadata(lines: Sequence[LineSignal]) -> Dict:
    """Serialize line signals into a config-patch friendly shape."""

    return {
        "dimensions": [
            {
                "position": line.position,
                "dimension": line.dimension,
                "score": round(line.score, 3),
                "state": line.state,
                "moving": line.moving,
                "evidence": line.evidence,
            }
            for line in lines
        ]
    }
