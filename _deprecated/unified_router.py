#!/usr/bin/env python3
"""
AIOS Unified Router - 统一路由器（支持三档模式）
"""

import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from pathlib import Path

# 导入两个实现（已归档，从 _deprecated 导入）
from _deprecated.simple_router import SimpleRouter, TaskContext as SimpleContext, TaskType, RiskLevel, Decision as SimpleDecision
from _deprecated.production_router import ProductionRouter, TaskContext as ProdContext, Plan


class RouterMode(Enum):
    """路由器模式"""
    SIMPLE = "simple"  # 简洁版（默认）
    FULL = "full"      # 生产级（4 个护栏）
    AUTO = "auto"      # 自动切换


@dataclass
class UnifiedContext:
    """统一的任务上下文"""
    task_id: str
    description: str
    task_type: TaskType
    complexity: int
    risk_level: RiskLevel
    
    # 系统状态
    error_rate: float = 0.0
    performance_drop: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    # 约束
    max_cost: Optional[float] = None
    max_time: Optional[int] = None
    
    # 历史
    last_agent: Optional[str] = None
    failure_count: int = 0


@dataclass
class UnifiedPlan:
    """统一的执行计划"""
    agent_type: str
    model: str
    thinking_level: str
    timeout: int
    reason: str
    confidence: float
    mode_used: str  # simple/full


class UnifiedRouter:
    """统一路由器 - 支持三档模式"""
    
    def __init__(self, mode: str = None, data_dir: str = "aios/data"):
        # 从环境变量或参数获取模式
        self.mode = RouterMode(mode or os.getenv("AIOS_ROUTER_MODE", "simple"))
        
        # 初始化两个路由器
        self.simple_router = SimpleRouter()
        self.production_router = ProductionRouter(data_dir)
        
        # auto 模式的阈值
        self.auto_thresholds = {
            "min_events": 200,  # 最近 1 小时事件量
            "min_502_rate": 0.05,  # 502 错误率
            "min_score_drop": 0.1  # evolution_score 下降
        }
    
    def route(self, ctx: UnifiedContext) -> UnifiedPlan:
        """
        统一路由入口
        
        根据模式选择路由器：
        - simple: 快速决策，适合正常情况
        - full: 完整护栏，适合生产环境
        - auto: 自动判断，满足条件才用 full
        """
        
        # 决定使用哪个路由器
        if self.mode == RouterMode.SIMPLE:
            return self._route_simple(ctx)
        
        elif self.mode == RouterMode.FULL:
            return self._route_full(ctx)
        
        elif self.mode == RouterMode.AUTO:
            # 自动判断
            if self._should_use_full(ctx):
                return self._route_full(ctx)
            else:
                return self._route_simple(ctx)
        
        else:
            return self._route_simple(ctx)
    
    def _route_simple(self, ctx: UnifiedContext) -> UnifiedPlan:
        """使用简洁版路由"""
        # 转换上下文
        simple_ctx = SimpleContext(
            description=ctx.description,
            task_type=ctx.task_type,
            complexity=ctx.complexity,
            risk_level=ctx.risk_level,
            error_rate=ctx.error_rate,
            performance_drop=ctx.performance_drop,
            cpu_usage=ctx.cpu_usage,
            memory_usage=ctx.memory_usage,
            max_cost=ctx.max_cost,
            max_time=ctx.max_time
        )
        
        decision = self.simple_router.route(simple_ctx)
        
        return UnifiedPlan(
            agent_type=decision.agent,
            model=decision.model,
            thinking_level=decision.thinking,
            timeout=decision.timeout,
            reason=decision.reason,
            confidence=0.8,  # simple 模式固定置信度
            mode_used="simple"
        )
    
    def _route_full(self, ctx: UnifiedContext) -> UnifiedPlan:
        """使用生产级路由"""
        # 转换上下文
        prod_ctx = ProdContext(
            task_id=ctx.task_id,
            description=ctx.description,
            task_type=ctx.task_type,
            complexity=ctx.complexity,
            risk_level=ctx.risk_level,
            error_rate=ctx.error_rate,
            performance_drop=ctx.performance_drop,
            cpu_usage=ctx.cpu_usage,
            memory_usage=ctx.memory_usage,
            max_cost=ctx.max_cost,
            max_time=ctx.max_time,
            last_agent=ctx.last_agent,
            failure_count=ctx.failure_count
        )
        
        plan = self.production_router.route(prod_ctx)
        
        return UnifiedPlan(
            agent_type=plan.agent_type,
            model=plan.model,
            thinking_level=plan.thinking_level,
            timeout=plan.timeout,
            reason=" / ".join(plan.reason_codes),
            confidence=plan.confidence,
            mode_used="full"
        )
    
    def _should_use_full(self, ctx: UnifiedContext) -> bool:
        """
        判断是否应该使用 full 模式（auto 模式的核心逻辑）
        
        满足以下任一条件则使用 full：
        1. 最近 1 小时事件量 > N（比如 200）
        2. 且 502/timeout 低于阈值
        3. 且 score 稳定（波动 < 0.1）
        
        否则回退 simple。
        """
        
        # 1. 检查事件量
        events_count = self._get_recent_events_count()
        if events_count < self.auto_thresholds["min_events"]:
            return False
        
        # 2. 检查 502 错误率
        error_502_rate = self._get_502_rate()
        if error_502_rate > self.auto_thresholds["min_502_rate"]:
            return False
        
        # 3. 检查 evolution_score
        score_drop = self._get_score_drop()
        if score_drop > self.auto_thresholds["min_score_drop"]:
            return False
        
        # 满足条件，使用 full
        return True
    
    def _get_recent_events_count(self) -> int:
        """获取最近 1 小时事件量"""
        # 简化实现，实际应该读取 events.jsonl
        return 0
    
    def _get_502_rate(self) -> float:
        """获取 502 错误率"""
        # 简化实现
        return 0.0
    
    def _get_score_drop(self) -> float:
        """获取 evolution_score 下降幅度"""
        # 简化实现
        return 0.0


def demo():
    """演示三档模式"""
    print("=" * 80)
    print("AIOS Unified Router - 三档模式演示")
    print("=" * 80)
    
    ctx = UnifiedContext(
        task_id="task-001",
        description="修复支付接口超时",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.35,
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6
    )
    
    # 测试三种模式
    for mode in ["simple", "full", "auto"]:
        print(f"\n【模式：{mode}】")
        router = UnifiedRouter(mode=mode)
        plan = router.route(ctx)
        
        print(f"Agent: {plan.agent_type}")
        print(f"Model: {plan.model}")
        print(f"Thinking: {plan.thinking_level}")
        print(f"Reason: {plan.reason}")
        print(f"Confidence: {plan.confidence:.2f}")
        print(f"Mode Used: {plan.mode_used}")
    
    print("\n" + "=" * 80)
    print("✅ 三档模式演示完成")
    print("=" * 80)
    print("\n使用方法：")
    print("1. 环境变量：export AIOS_ROUTER_MODE=simple")
    print("2. 代码指定：UnifiedRouter(mode='full')")
    print("3. 默认：simple（快速决策）")


if __name__ == "__main__":
    demo()
