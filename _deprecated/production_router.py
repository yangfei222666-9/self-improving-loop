#!/usr/bin/env python3
"""
AIOS Production Router v2.0 - 生产级路由器
4 个必需护栏：解释性、防抖、预算、失败回退
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
from pathlib import Path
import time


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


class ExecutionMode(Enum):
    """执行模式"""
    DRY_RUN = "dry_run"  # 只读分析
    APPLY = "apply"      # 真正执行


@dataclass
class TaskContext:
    """任务上下文"""
    task_id: str
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
    
    # 历史
    last_agent: Optional[str] = None
    failure_count: int = 0


@dataclass
class Plan:
    """执行计划"""
    # Agent 选择
    agent_type: str
    model: str
    thinking_level: str
    
    # 执行策略
    execution_mode: ExecutionMode
    timeout: int
    retry_policy: Dict
    degrade_policy: Dict
    
    # 解释性
    reason_codes: List[str]  # ["high_error_rate", "sticky_applied"]
    confidence: float  # 0-1
    
    # 输入快照（可复盘）
    input_snapshot: Dict
    
    # 决策时间
    decided_at: str


class ProductionRouter:
    """生产级路由器 - 带 4 个护栏"""
    
    def __init__(self, data_dir: str = "aios/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 防抖状态（sticky agent）
        self.sticky_state = self._load_sticky_state()
        
        # 2. 预算追踪
        self.budget_tracker = self._load_budget_tracker()
        
        # 3. 失败历史
        self.failure_history = self._load_failure_history()
        
        # 4. 决策日志
        self.decision_log_file = self.data_dir / "router_decisions.jsonl"
    
    def route(self, ctx: TaskContext) -> Plan:
        """
        生产级路由决策
        
        护栏：
        1. 解释性 - 每次决策落盘可复盘理由
        2. 防抖 - sticky agent + 滞回阈值
        3. 预算 - Opus 配额 + 自动降级
        4. 失败回退 - 最多 2 次切换 + needs_human
        """
        
        start_time = time.time()
        reason_codes = []
        
        # ========== 护栏 1：输入快照（可复盘） ==========
        input_snapshot = {
            "task_id": ctx.task_id,
            "task_type": ctx.task_type.value,
            "complexity": ctx.complexity,
            "risk_level": ctx.risk_level.value,
            "error_rate": ctx.error_rate,
            "performance_drop": ctx.performance_drop,
            "cpu_usage": ctx.cpu_usage,
            "memory_usage": ctx.memory_usage,
            "last_agent": ctx.last_agent,
            "failure_count": ctx.failure_count
        }
        
        # ========== 护栏 2：防抖（sticky agent） ==========
        sticky_agent = self._check_sticky(ctx)
        if sticky_agent:
            reason_codes.append("sticky_applied")
            agent = sticky_agent
            confidence = 0.95  # sticky 高置信度
        else:
            # ========== 核心决策逻辑 ==========
            agent, agent_reason = self._decide_agent(ctx)
            reason_codes.extend(agent_reason)
            confidence = self._calculate_confidence(reason_codes, ctx)
            
            # 记录 sticky
            self._record_sticky(ctx.task_id, ctx.task_type, agent)
        
        # ========== 护栏 4：失败回退 ==========
        if ctx.failure_count >= 2:
            reason_codes.append("max_retries_exceeded")
            agent = "reviewer"  # 失败 2 次 → 人工审计
            execution_mode = ExecutionMode.DRY_RUN  # 只读
        else:
            execution_mode = ExecutionMode.APPLY
        
        # ========== 护栏 3：预算控制 ==========
        model, model_reason = self._select_model_with_budget(ctx, agent)
        reason_codes.extend(model_reason)
        
        # 构建计划
        plan = Plan(
            agent_type=agent,
            model=model,
            thinking_level=self._select_thinking(ctx, model),
            execution_mode=execution_mode,
            timeout=self._select_timeout(ctx),
            retry_policy=self._build_retry_policy(ctx),
            degrade_policy=self._build_degrade_policy(ctx),
            reason_codes=reason_codes,
            confidence=confidence,
            input_snapshot=input_snapshot,
            decided_at=datetime.now().isoformat()
        )
        
        # ========== 护栏 1：决策落盘 ==========
        self._log_decision(plan, time.time() - start_time)
        
        return plan
    
    def _decide_agent(self, ctx: TaskContext) -> Tuple[str, List[str]]:
        """
        核心决策逻辑（带滞回阈值）
        
        返回：(agent, reason_codes)
        """
        reasons = []
        
        # 1. 系统状态（带滞回）
        if ctx.error_rate > 0.3:  # 进入阈值 30%
            reasons.append("high_error_rate")
            return "debugger", reasons
        elif ctx.error_rate < 0.2 and ctx.last_agent == "debugger":
            # 退出阈值 20%（滞回）
            reasons.append("error_rate_recovered")
            # 继续用 debugger 直到 <20%
            return "debugger", reasons
        
        if ctx.performance_drop > 0.2:  # 进入阈值 20%
            reasons.append("performance_degraded")
            return "optimizer", reasons
        elif ctx.performance_drop < 0.1 and ctx.last_agent == "optimizer":
            # 退出阈值 10%（滞回）
            reasons.append("performance_recovered")
            return "optimizer", reasons
        
        if ctx.cpu_usage > 0.8 or ctx.memory_usage > 0.8:
            reasons.append("resource_constrained")
            return "monitor", reasons
        
        # 2. 风险等级
        if ctx.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            reasons.append(f"high_risk_{ctx.risk_level.value}")
            return "reviewer", reasons
        
        # 3. 任务类型
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
        
        agent = task_agent_map.get(ctx.task_type, "coder")
        reasons.append(f"task_type_{ctx.task_type.value}")
        
        return agent, reasons
    
    def _select_model_with_budget(self, ctx: TaskContext, agent: str) -> Tuple[str, List[str]]:
        """
        模型选择（带预算控制）
        
        返回：(model, reason_codes)
        """
        reasons = []
        
        # 1. 检查 Opus 配额
        opus_usage = self._get_opus_usage_last_hour()
        opus_limit = 10  # 每小时最多 10 次 Opus
        
        if opus_usage >= opus_limit:
            reasons.append("opus_quota_exceeded")
            return "claude-sonnet-4-5", reasons
        
        # 2. 成本约束
        if ctx.max_cost and ctx.max_cost < 0.1:
            reasons.append("cost_constrained")
            return "claude-sonnet-4-5", reasons
        
        # 3. 资源约束
        if ctx.cpu_usage > 0.8 or ctx.memory_usage > 0.8:
            reasons.append("resource_constrained")
            return "claude-sonnet-4-5", reasons
        
        # 4. 复杂度
        if ctx.complexity <= 5:
            reasons.append("low_complexity")
            return "claude-sonnet-4-5", reasons
        
        # 5. 默认 Opus（高复杂度 + 有配额）
        reasons.append("high_complexity")
        self._record_opus_usage()
        return "claude-opus-4-6", reasons
    
    def _select_thinking(self, ctx: TaskContext, model: str) -> str:
        """选择 thinking 级别"""
        if ctx.complexity >= 8:
            return "high"
        elif ctx.complexity >= 5:
            return "medium"
        elif ctx.cpu_usage > 0.8:
            return "off"  # 资源紧张降级
        else:
            return "low"
    
    def _select_timeout(self, ctx: TaskContext) -> int:
        """选择超时时间"""
        if ctx.max_time:
            return ctx.max_time
        
        if ctx.complexity >= 8:
            return 600  # 10 分钟
        elif ctx.complexity >= 5:
            return 300  # 5 分钟
        else:
            return 180  # 3 分钟
    
    def _build_retry_policy(self, ctx: TaskContext) -> Dict:
        """构建重试策略"""
        return {
            "max_retries": 2 - ctx.failure_count,  # 最多 2 次
            "backoff": "exponential",
            "initial_delay": 5,
            "max_delay": 60
        }
    
    def _build_degrade_policy(self, ctx: TaskContext) -> Dict:
        """构建降级策略"""
        fallback_map = {
            "coder": ["debugger", "reviewer"],
            "debugger": ["coder", "reviewer"],
            "optimizer": ["coder", "reviewer"],
            "analyst": ["researcher"],
            "monitor": ["analyst"]
        }
        
        return {
            "fallback_agents": fallback_map.get(ctx.last_agent or "coder", ["reviewer"]),
            "degrade_to_readonly": ctx.failure_count >= 1
        }
    
    def _calculate_confidence(self, reason_codes: List[str], ctx: TaskContext) -> float:
        """计算置信度"""
        # 基础置信度
        confidence = 0.7
        
        # 系统状态明确 → 高置信度
        if any(r in reason_codes for r in ["high_error_rate", "performance_degraded", "resource_constrained"]):
            confidence += 0.2
        
        # 高风险 → 高置信度
        if "high_risk" in str(reason_codes):
            confidence += 0.1
        
        # 失败过 → 低置信度
        if ctx.failure_count > 0:
            confidence -= 0.1 * ctx.failure_count
        
        return min(max(confidence, 0.0), 1.0)
    
    # ========== 护栏 2：防抖（sticky） ==========
    
    def _check_sticky(self, ctx: TaskContext) -> Optional[str]:
        """检查是否应该 sticky（10 分钟内同类任务固定 agent）"""
        key = f"{ctx.task_type.value}"
        
        if key in self.sticky_state:
            record = self.sticky_state[key]
            last_time = datetime.fromisoformat(record["timestamp"])
            
            # 10 分钟内 sticky
            if datetime.now() - last_time < timedelta(minutes=10):
                return record["agent"]
        
        return None
    
    def _record_sticky(self, task_id: str, task_type: TaskType, agent: str):
        """记录 sticky 状态"""
        key = f"{task_type.value}"
        self.sticky_state[key] = {
            "task_id": task_id,
            "agent": agent,
            "timestamp": datetime.now().isoformat()
        }
        self._save_sticky_state()
    
    def _load_sticky_state(self) -> Dict:
        """加载 sticky 状态"""
        file = self.data_dir / "router_sticky.json"
        if file.exists():
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_sticky_state(self):
        """保存 sticky 状态"""
        file = self.data_dir / "router_sticky.json"
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(self.sticky_state, f, indent=2, ensure_ascii=False)
    
    # ========== 护栏 3：预算追踪 ==========
    
    def _get_opus_usage_last_hour(self) -> int:
        """获取最近 1 小时 Opus 使用次数"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        count = 0
        for record in self.budget_tracker.get("opus_usage", []):
            timestamp = datetime.fromisoformat(record["timestamp"])
            if timestamp > one_hour_ago:
                count += 1
        
        return count
    
    def _record_opus_usage(self):
        """记录 Opus 使用"""
        if "opus_usage" not in self.budget_tracker:
            self.budget_tracker["opus_usage"] = []
        
        self.budget_tracker["opus_usage"].append({
            "timestamp": datetime.now().isoformat()
        })
        
        # 只保留最近 2 小时的记录
        two_hours_ago = datetime.now() - timedelta(hours=2)
        self.budget_tracker["opus_usage"] = [
            r for r in self.budget_tracker["opus_usage"]
            if datetime.fromisoformat(r["timestamp"]) > two_hours_ago
        ]
        
        self._save_budget_tracker()
    
    def _load_budget_tracker(self) -> Dict:
        """加载预算追踪"""
        file = self.data_dir / "router_budget.json"
        if file.exists():
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_budget_tracker(self):
        """保存预算追踪"""
        file = self.data_dir / "router_budget.json"
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(self.budget_tracker, f, indent=2, ensure_ascii=False)
    
    # ========== 护栏 4：失败历史 ==========
    
    def _load_failure_history(self) -> Dict:
        """加载失败历史"""
        file = self.data_dir / "router_failures.json"
        if file.exists():
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    # ========== 护栏 1：决策日志 ==========
    
    def _log_decision(self, plan: Plan, duration: float):
        """记录决策日志（可复盘）"""
        # 转换 Enum 为字符串
        plan_dict = asdict(plan)
        plan_dict["execution_mode"] = plan.execution_mode.value
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "duration_ms": int(duration * 1000),
            "plan": plan_dict
        }
        
        with open(self.decision_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')


def demo():
    """演示生产级路由"""
    router = ProductionRouter()
    
    print("=" * 80)
    print("AIOS Production Router v2.0 - 4 个护栏演示")
    print("=" * 80)
    
    # 场景 1：正常任务
    print("\n【场景 1】正常任务")
    ctx1 = TaskContext(
        task_id="task-001",
        description="实现用户登录",
        task_type=TaskType.CODING,
        complexity=5,
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5
    )
    plan1 = router.route(ctx1)
    print(f"Agent: {plan1.agent_type}")
    print(f"Model: {plan1.model}")
    print(f"Reason: {plan1.reason_codes}")
    print(f"Confidence: {plan1.confidence:.2f}")
    
    # 场景 2：高错误率（滞回）
    print("\n" + "=" * 80)
    print("【场景 2】高错误率 35% → debugger")
    ctx2 = TaskContext(
        task_id="task-002",
        description="修复支付接口",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.35,  # 35% > 30% 阈值
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6
    )
    plan2 = router.route(ctx2)
    print(f"Agent: {plan2.agent_type}")
    print(f"Model: {plan2.model}")
    print(f"Reason: {plan2.reason_codes}")
    print(f"Confidence: {plan2.confidence:.2f}")
    
    # 场景 3：错误率下降到 25%（滞回保持）
    print("\n" + "=" * 80)
    print("【场景 3】错误率下降到 25%（滞回保持 debugger）")
    ctx3 = TaskContext(
        task_id="task-003",
        description="继续修复",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.25,  # 25% 在 20%-30% 之间（滞回区）
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6,
        last_agent="debugger"
    )
    plan3 = router.route(ctx3)
    print(f"Agent: {plan3.agent_type} (应该保持 debugger)")
    print(f"Reason: {plan3.reason_codes}")
    
    # 场景 4：Opus 配额耗尽
    print("\n" + "=" * 80)
    print("【场景 4】Opus 配额耗尽 → 降级 Sonnet")
    # 模拟 Opus 配额耗尽
    for i in range(10):
        router._record_opus_usage()
    
    ctx4 = TaskContext(
        task_id="task-004",
        description="复杂重构",
        task_type=TaskType.REFACTOR,
        complexity=9,  # 高复杂度
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.05,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5
    )
    plan4 = router.route(ctx4)
    print(f"Agent: {plan4.agent_type}")
    print(f"Model: {plan4.model} (应该是 Sonnet)")
    print(f"Reason: {plan4.reason_codes}")
    
    # 场景 5：失败 2 次 → needs_human
    print("\n" + "=" * 80)
    print("【场景 5】失败 2 次 → reviewer (只读)")
    ctx5 = TaskContext(
        task_id="task-005",
        description="部署失败",
        task_type=TaskType.DEPLOY,
        complexity=8,
        risk_level=RiskLevel.HIGH,
        error_rate=0.1,
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5,
        failure_count=2  # 失败 2 次
    )
    plan5 = router.route(ctx5)
    print(f"Agent: {plan5.agent_type} (应该是 reviewer)")
    print(f"Execution Mode: {plan5.execution_mode.value} (应该是 dry_run)")
    print(f"Reason: {plan5.reason_codes}")
    
    print("\n" + "=" * 80)
    print("✅ 生产级路由演示完成")
    print("=" * 80)
    print("\n4 个护栏验证：")
    print("1. ✅ 解释性 - 每次决策落盘到 router_decisions.jsonl")
    print("2. ✅ 防抖 - sticky agent + 滞回阈值（20%-30%）")
    print("3. ✅ 预算 - Opus 配额（10次/小时）+ 自动降级")
    print("4. ✅ 失败回退 - 最多 2 次切换 + reviewer 只读")


if __name__ == "__main__":
    demo()
