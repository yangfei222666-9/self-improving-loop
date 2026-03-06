"""
Phase 3 异常处理测试 - 零改动可跑版
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from debate_policy_engine import DebatePolicyEngine, TaskMeta, HexagramState
from phase3_types import GenerateResponse, TokenUsage


# ============================================================
# Mock Providers
# ============================================================

class TimeoutProvider:
    def generate(self, req):
        raise TimeoutError("simulated timeout")


class EmptyProvider:
    def generate(self, req):
        return GenerateResponse(
            ok=True,
            text="",
            model_id="empty-provider",
            latency_ms=1,
            token_usage=TokenUsage(),
        )


class ConflictProvider:
    def generate(self, req):
        text = "approve immediately, low risk" if req.role == "bull" else "reject immediately, high risk"
        return GenerateResponse(
            ok=True,
            text=text,
            model_id="conflict-provider",
            latency_ms=2,
            token_usage=TokenUsage(prompt_tokens=5, completion_tokens=8, total_tokens=13),
        )


# ============================================================
# 辅助函数
# ============================================================

def _build_engine(provider):
    return DebatePolicyEngine(llm_client=provider)


def _run(engine, *, task_id="t-1", risk="medium", hexagram="乾卦", score=80.0, text="deploy change"):
    task = TaskMeta(task_id=task_id, risk_level=risk, content=text)
    state = HexagramState(hexagram=hexagram, evolution_score=score)
    return engine.evaluate(task_meta=task, state=state)


# ============================================================
# 测试用例
# ============================================================

def test_timeout_fallback():
    engine = _build_engine(TimeoutProvider())
    result = _run(engine, risk="low", hexagram="乾卦", score=88.0, text="release config")
    assert result.verdict == "defer"
    assert result.requires_human_gate is True


def test_empty_response_fallback():
    engine = _build_engine(EmptyProvider())
    result = _run(engine, risk="medium", hexagram="坤卦", score=76.0, text="preflight check")
    assert result.verdict == "defer"
    assert result.requires_human_gate is True


def test_daguo_hard_gate_unskippable():
    engine = _build_engine(ConflictProvider())
    result = _run(
        engine,
        risk="high",
        hexagram="大过卦 (#28)",
        score=98.0,
        text="drop production table",
    )
    assert result.verdict == "defer"
    assert result.requires_human_gate is True
    assert result.rounds_used == 0


def test_conflict_escalates_conservative():
    engine = _build_engine(ConflictProvider())
    result = _run(engine, risk="medium", hexagram="离卦", score=85.0, text="auth middleware hot update")
    assert result.verdict in ("defer", "reject")
