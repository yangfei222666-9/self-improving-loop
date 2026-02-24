#!/usr/bin/env python3
"""
AIOS Task Router - 简洁版决策系统
核心理念：if-elif 决策树，清晰可读，易于调试
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class TaskType(Enum):
    """任务类型"""
    CODING = "coding"
    REFACTOR = "refactor"
    DEBUG = "debug"
    TEST = "test"
    MONITOR = "monitor"
    DEPLOY = "deploy"
    OPTIMIZE = "optimize"
    ANALYZE = "analyze"
    RESEARCH = "research"
    REVIEW = "review"
    DOCUMENT = "document"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskContext:
    """任务上下文"""
    description: str
    task_type: TaskType
    complexity: int  # 1-10
    risk_level: RiskLevel
    
    # 系统状态
    error_rate: float
    performance_drop: float
    cpu_usage: float
    memory_usage: float
    
    # 约束
    max_cost: Optional[float] = None
    max_time: Optional[int] = None


@dataclass
class Decision:
    """路由决策"""
    agent: str
    model: str
    thinking: str
    timeout: int
    reason: str


class SimpleRouter:
    """简洁版路由器 - if-elif 决策树"""
    
    def route(self, ctx: TaskContext) -> Decision:
        """
        核心决策逻辑 - 清晰的 if-elif 树
        
        优先级（优化后）：
        1. 系统状态（错误/性能）
        2. 风险等级（CRITICAL 提前）
        3. 资源约束（降级模型，不换 agent）
        4. 任务类型
        """
        
        # ========== 第一优先级：系统状态 ==========
        
        # 高错误率 → debugger
        if ctx.error_rate > 0.3:
            return Decision(
                agent="debugger",
                model=self._select_model(ctx),
                thinking="high",
                timeout=180,
                reason=f"高错误率 {ctx.error_rate:.1%}"
            )
        
        # 性能下降 → optimizer
        elif ctx.performance_drop > 0.2:
            return Decision(
                agent="optimizer",
                model=self._select_model(ctx),
                thinking="high",
                timeout=300,
                reason=f"性能下降 {ctx.performance_drop:.1%}"
            )
        
        # ========== 第二优先级：风险等级（提前到资源约束之前）==========
        
        # 高风险 → reviewer（审查优先）
        elif ctx.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return Decision(
                agent="reviewer",
                model="claude-opus-4-6",
                thinking="high",
                timeout=300,
                reason=f"高风险任务 {ctx.risk_level.value}"
            )
        
        # ========== 第三优先级：资源约束（降级模型，不换 agent）==========
        
        # 资源紧张 → 降级模型 + thinking
        elif ctx.cpu_usage > 0.8 or ctx.memory_usage > 0.8:
            # 根据任务类型选择 agent，但强制降级模型
            agent = self._select_agent_by_task_type(ctx.task_type)
            return Decision(
                agent=agent,
                model="claude-sonnet-4-5",  # 强制 Sonnet
                thinking="off",  # 降 thinking
                timeout=180,
                reason=f"资源紧张 CPU:{ctx.cpu_usage:.1%} MEM:{ctx.memory_usage:.1%}"
            )
        
        # ========== 第四优先级：任务类型 ==========
        
        # 重构 → coding + analysis
        elif ctx.task_type == TaskType.REFACTOR:
            return Decision(
                agent="coder",  # 能力：coding + refactoring + architecture
                model=self._select_model(ctx),
                thinking="medium",
                timeout=300,
                reason="重构任务"
            )
        
        # 调试 → debugger
        elif ctx.task_type == TaskType.DEBUG:
            return Decision(
                agent="debugger",
                model="claude-opus-4-6",
                thinking="high",
                timeout=300,
                reason="调试任务"
            )
        
        # 优化 → optimizer
        elif ctx.task_type == TaskType.OPTIMIZE:
            return Decision(
                agent="optimizer",
                model="claude-opus-4-6",
                thinking="high",
                timeout=300,
                reason="优化任务"
            )
        
        # 测试 → tester
        elif ctx.task_type == TaskType.TEST:
            return Decision(
                agent="tester",
                model="claude-sonnet-4-5",
                thinking="medium",
                timeout=300,
                reason="测试任务"
            )
        
        # 监控 → monitor
        elif ctx.task_type == TaskType.MONITOR:
            return Decision(
                agent="monitor",
                model="claude-sonnet-4-5",
                thinking="off",
                timeout=60,
                reason="监控任务"
            )
        
        # 部署 → deployer
        elif ctx.task_type == TaskType.DEPLOY:
            return Decision(
                agent="deployer",
                model="claude-sonnet-4-5",
                thinking="medium",
                timeout=600,
                reason="部署任务"
            )
        
        # 分析 → analyst
        elif ctx.task_type == TaskType.ANALYZE:
            return Decision(
                agent="analyst",
                model="claude-sonnet-4-5",
                thinking="low",
                timeout=300,
                reason="分析任务"
            )
        
        # 研究 → researcher
        elif ctx.task_type == TaskType.RESEARCH:
            return Decision(
                agent="researcher",
                model="claude-sonnet-4-5",
                thinking="low",
                timeout=300,
                reason="研究任务"
            )
        
        # 审查 → reviewer
        elif ctx.task_type == TaskType.REVIEW:
            return Decision(
                agent="reviewer",
                model="claude-opus-4-6",
                thinking="high",
                timeout=300,
                reason="审查任务"
            )
        
        # 文档 → documenter
        elif ctx.task_type == TaskType.DOCUMENT:
            return Decision(
                agent="documenter",
                model="claude-sonnet-4-5",
                thinking="low",
                timeout=300,
                reason="文档任务"
            )
        
        # ========== 默认：编码任务 ==========
        else:
            return Decision(
                agent="coder",
                model=self._select_model(ctx),
                thinking="medium",
                timeout=300,
                reason="默认编码任务"
            )
    
    def _select_model(self, ctx: TaskContext) -> str:
        """
        模型选择 - 简单规则
        
        规则：
        1. 成本约束 < $0.1 → Sonnet
        2. 资源紧张（CPU/内存 > 80%）→ Sonnet
        3. 复杂度 ≤ 5 → Sonnet
        4. 其他 → Opus
        """
        
        # 成本约束
        if ctx.max_cost and ctx.max_cost < 0.1:
            return "claude-sonnet-4-5"
        
        # 资源约束
        if ctx.cpu_usage > 0.8 or ctx.memory_usage > 0.8:
            return "claude-sonnet-4-5"
        
        # 复杂度
        if ctx.complexity <= 5:
            return "claude-sonnet-4-5"
        
        return "claude-opus-4-6"
    
    def _select_agent_by_task_type(self, task_type: TaskType) -> str:
        """根据任务类型选择 agent（用于资源约束时）"""
        task_agent_map = {
            TaskType.REFACTOR: "coder",
            TaskType.DEBUG: "debugger",
            TaskType.OPTIMIZE: "optimizer",
            TaskType.TEST: "tester",
            TaskType.MONITOR: "monitor",
            TaskType.DEPLOY: "deployer",
            TaskType.ANALYZE: "analyst",
            TaskType.RESEARCH: "researcher",
            TaskType.REVIEW: "reviewer",
            TaskType.DOCUMENT: "documenter",
            TaskType.CODING: "coder"
        }
        return task_agent_map.get(task_type, "coder")


def demo():
    """演示简洁版路由"""
    router = SimpleRouter()
    
    print("=" * 80)
    print("AIOS Simple Router - if-elif 决策树")
    print("=" * 80)
    
    # 场景 1：高错误率
    print("\n【场景 1】高错误率 → debugger")
    ctx1 = TaskContext(
        description="修复支付接口超时",
        task_type=TaskType.CODING,
        complexity=5,
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.45,  # 45% 错误率
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6
    )
    decision1 = router.route(ctx1)
    print(f"if error_rate > 0.3:")
    print(f"    assign({decision1.agent})")
    print(f"    # {decision1.reason}")
    print(f"    # 模型: {decision1.model}, thinking: {decision1.thinking}")
    
    # 场景 2：性能下降
    print("\n" + "=" * 80)
    print("【场景 2】性能下降 → optimizer")
    ctx2 = TaskContext(
        description="优化数据库查询",
        task_type=TaskType.CODING,
        complexity=7,
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.05,
        performance_drop=0.35,  # 35% 性能下降
        cpu_usage=0.6,
        memory_usage=0.7
    )
    decision2 = router.route(ctx2)
    print(f"elif performance_drop > 0.2:")
    print(f"    assign({decision2.agent})")
    print(f"    # {decision2.reason}")
    print(f"    # 模型: {decision2.model}, thinking: {decision2.thinking}")
    
    # 场景 3：重构任务
    print("\n" + "=" * 80)
    print("【场景 3】重构任务 → coder (coding + analysis)")
    ctx3 = TaskContext(
        description="重构用户模块，提取公共逻辑",
        task_type=TaskType.REFACTOR,
        complexity=6,
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5
    )
    decision3 = router.route(ctx3)
    print(f"elif task.type == 'refactor':")
    print(f"    assign({decision3.agent})  # coding + refactoring + architecture")
    print(f"    # {decision3.reason}")
    print(f"    # 模型: {decision3.model}, thinking: {decision3.thinking}")
    
    # 场景 4：高风险部署
    print("\n" + "=" * 80)
    print("【场景 4】高风险部署 → reviewer")
    ctx4 = TaskContext(
        description="部署到生产环境",
        task_type=TaskType.DEPLOY,
        complexity=8,
        risk_level=RiskLevel.CRITICAL,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5
    )
    decision4 = router.route(ctx4)
    print(f"elif risk_level == CRITICAL:")
    print(f"    assign({decision4.agent})")
    print(f"    # {decision4.reason}")
    print(f"    # 模型: {decision4.model}, thinking: {decision4.thinking}")
    
    # 场景 5：资源紧张
    print("\n" + "=" * 80)
    print("【场景 5】资源紧张 → monitor + Sonnet")
    ctx5 = TaskContext(
        description="实现新功能",
        task_type=TaskType.CODING,
        complexity=8,
        risk_level=RiskLevel.LOW,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.85,  # CPU 紧张
        memory_usage=0.9  # 内存紧张
    )
    decision5 = router.route(ctx5)
    print(f"elif cpu_usage > 0.8 or memory_usage > 0.8:")
    print(f"    assign({decision5.agent})")
    print(f"    # {decision5.reason}")
    print(f"    # 模型: {decision5.model} (降级), thinking: {decision5.thinking}")
    
    # 场景 6：简单任务 + 成本约束
    print("\n" + "=" * 80)
    print("【场景 6】简单任务 + 成本约束 → coder + Sonnet")
    ctx6 = TaskContext(
        description="添加日志输出",
        task_type=TaskType.CODING,
        complexity=3,
        risk_level=RiskLevel.LOW,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5,
        max_cost=0.05  # 成本约束
    )
    decision6 = router.route(ctx6)
    print(f"else:  # 默认编码任务")
    print(f"    assign({decision6.agent})")
    print(f"    # {decision6.reason}")
    print(f"    # 模型: {decision6.model} (成本约束), thinking: {decision6.thinking}")
    
    print("\n" + "=" * 80)
    print("✅ 简洁版路由演示完成")
    print("=" * 80)
    print("\n核心优势：")
    print("1. 清晰的 if-elif 决策树，一眼看懂")
    print("2. 优先级明确：系统状态 > 风险 > 任务类型")
    print("3. 易于调试和扩展")
    print("4. 代码即文档")


if __name__ == "__main__":
    demo()
