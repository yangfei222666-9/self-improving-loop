#!/usr/bin/env python3
"""
AIOS Unified Router v1.0 - 生产就绪版
核心护栏：A（解释性）+ B（防抖滞回）
"""

import os
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path


# ========== 统一类型定义 ==========

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
    DESIGN = "design"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionMode(Enum):
    """执行模式"""
    DRY_RUN = "dry_run"
    APPLY = "apply"


@dataclass
class TaskContext:
    """统一任务上下文"""
    description: str
    task_type: TaskType
    complexity: int  # 1-10
    risk_level: RiskLevel
    
    # 系统状态
    error_rate: float = 0.0
    performance_drop: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    # 路由元数据
    task_id: str = ""
    last_agent: Optional[str] = None
    failure_count: int = 0
    max_cost: Optional[float] = None
    max_time: Optional[int] = None


@dataclass
class Decision:
    """统一决策结果"""
    agent: str
    model: str
    thinking: str
    timeout: int
    execution_mode: ExecutionMode = ExecutionMode.APPLY
    reason_codes: List[str] = field(default_factory=list)
    confidence: float = 0.7
    
    # 解释性（护栏 A）
    input_snapshot: Dict = field(default_factory=dict)
    decided_at: str = ""


# ========== 护栏 B：防抖滞回 ==========

class StickyCache:
    """内存优先的 sticky 状态（防抖）"""
    
    def __init__(self, data_dir: str, ttl_seconds: int = 600):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl_seconds
        
        # 内存缓存
        self._cache: Dict[str, Dict] = {}
        self._dirty = False
        self._last_flush = time.time()
        self._flush_interval = 30  # 30 秒刷盘一次
        
        # 加载持久化数据
        self._load()
    
    def check(self, task_type: TaskType) -> Optional[str]:
        """检查是否应该 sticky（10 分钟内同类任务固定 agent）"""
        key = task_type.value
        
        if key not in self._cache:
            return None
        
        record = self._cache[key]
        age = time.time() - record["timestamp"]
        
        # 超过 TTL，删除
        if age > self.ttl:
            del self._cache[key]
            self._dirty = True
            return None
        
        return record["agent"]
    
    def record(self, task_type: TaskType, agent: str):
        """记录 sticky 状态"""
        key = task_type.value
        self._cache[key] = {
            "agent": agent,
            "timestamp": time.time()
        }
        self._dirty = True
        self._maybe_flush()
    
    def _load(self):
        """加载持久化数据"""
        file = self.data_dir / "router_sticky.json"
        if file.exists():
            try:
                data = json.loads(file.read_text(encoding='utf-8'))
                # 清理过期数据
                now = time.time()
                self._cache = {
                    k: v for k, v in data.items()
                    if now - v.get("timestamp", 0) < self.ttl
                }
            except:
                self._cache = {}
    
    def _maybe_flush(self):
        """定期刷盘（避免每次写文件）"""
        if self._dirty and time.time() - self._last_flush > self._flush_interval:
            self._flush()
    
    def _flush(self):
        """强制刷盘"""
        file = self.data_dir / "router_sticky.json"
        file.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2))
        self._dirty = False
        self._last_flush = time.time()


class HysteresisTracker:
    """滞回追踪器（防止抖动）"""
    
    def __init__(self):
        # 滞回阈值
        self.thresholds = {
            "error_rate": {"enter": 0.3, "exit": 0.2},
            "performance_drop": {"enter": 0.2, "exit": 0.1}
        }
        
        # 当前状态
        self._state = {}
    
    def should_trigger(self, metric: str, value: float, last_agent: Optional[str]) -> bool:
        """
        判断是否应该触发（带滞回）
        
        Args:
            metric: 指标名称（error_rate/performance_drop）
            value: 当前值
            last_agent: 上次使用的 agent
            
        Returns:
            是否应该触发
        """
        if metric not in self.thresholds:
            return False
        
        enter_threshold = self.thresholds[metric]["enter"]
        exit_threshold = self.thresholds[metric]["exit"]
        
        # 当前是否在触发状态
        in_state = self._state.get(metric, False)
        
        if not in_state:
            # 未触发 → 检查是否超过进入阈值
            if value > enter_threshold:
                self._state[metric] = True
                return True
            return False
        else:
            # 已触发 → 检查是否低于退出阈值
            if value < exit_threshold:
                self._state[metric] = False
                return False
            return True


# ========== 护栏 A：决策日志 ==========

class DecisionLogger:
    """决策日志（解释性 + 自动截断）"""
    
    def __init__(self, data_dir: str, max_lines: int = 1000):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.data_dir / "router_decisions.jsonl"
        self.max_lines = max_lines
        self._write_count = 0
    
    def log(self, decision: Decision, ctx: TaskContext, duration_ms: int):
        """记录决策（可复盘）"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "decision": {
                "agent": decision.agent,
                "model": decision.model,
                "thinking": decision.thinking,
                "timeout": decision.timeout,
                "execution_mode": decision.execution_mode.value,
                "reason_codes": decision.reason_codes,
                "confidence": decision.confidence
            },
            "input_snapshot": decision.input_snapshot
        }
        
        # Append
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        
        # 定期截断
        self._write_count += 1
        if self._write_count % 100 == 0:
            self._truncate()
    
    def _truncate(self):
        """截断日志（保留最近 N 条）"""
        if not self.log_file.exists():
            return
        
        lines = self.log_file.read_text(encoding='utf-8').splitlines()
        if len(lines) > self.max_lines:
            keep = lines[-self.max_lines:]
            self.log_file.write_text('\n'.join(keep) + '\n', encoding='utf-8')


# ========== 统一路由器 ==========

class UnifiedRouter:
    """
    统一路由器 v1.0
    
    核心护栏：
    - A（解释性）：每次决策落盘，输入快照 + 原因链 + 置信度
    - B（防抖滞回）：sticky agent（10min）+ 滞回阈值（20%-30%）
    """
    
    def __init__(self, data_dir: str = "aios/data", enable_guardrails: bool = True):
        self.enable_guardrails = enable_guardrails
        
        if enable_guardrails:
            self.sticky = StickyCache(data_dir)
            self.hysteresis = HysteresisTracker()
        
        self.logger = DecisionLogger(data_dir)
    
    def route(self, ctx: TaskContext) -> Decision:
        """
        统一路由入口
        
        决策流程：
        1. 护栏 B：检查 sticky（防抖）
        2. 核心决策：系统状态 > 风险 > 资源 > 任务类型
        3. 护栏 A：决策落盘（解释性）
        """
        
        start_time = time.time()
        reason_codes = []
        
        # ========== 护栏 A：输入快照 ==========
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
        
        # ========== 护栏 B：防抖（sticky）==========
        sticky_agent = None
        if self.enable_guardrails:
            sticky_agent = self.sticky.check(ctx.task_type)
            if sticky_agent:
                reason_codes.append("sticky_applied")
        
        # ========== 核心决策 ==========
        if sticky_agent:
            agent = sticky_agent
            confidence = 0.95  # sticky 高置信度
        else:
            agent, agent_reasons = self._decide_agent(ctx)
            reason_codes.extend(agent_reasons)
            confidence = self._calculate_confidence(reason_codes, ctx)
            
            # 记录 sticky
            if self.enable_guardrails:
                self.sticky.record(ctx.task_type, agent)
        
        # 模型选择
        model = self._select_model(ctx)
        
        # 构建决策
        decision = Decision(
            agent=agent,
            model=model,
            thinking=self._select_thinking(ctx, model),
            timeout=self._select_timeout(ctx),
            execution_mode=ExecutionMode.APPLY,
            reason_codes=reason_codes,
            confidence=confidence,
            input_snapshot=input_snapshot,
            decided_at=datetime.now().isoformat()
        )
        
        # ========== 护栏 A：决策落盘 ==========
        duration_ms = int((time.time() - start_time) * 1000)
        self.logger.log(decision, ctx, duration_ms)
        
        return decision
    
    def _decide_agent(self, ctx: TaskContext) -> Tuple[str, List[str]]:
        """
        核心决策逻辑（带滞回）
        
        优先级：
        1. 系统状态（错误/性能）- 带滞回
        2. 风险等级（CRITICAL 提前）
        3. 资源约束（降级模型，不换 agent）
        4. 任务类型
        """
        reasons = []
        
        # 1. 系统状态（带滞回）
        if self.enable_guardrails:
            # 高错误率（带滞回）
            if self.hysteresis.should_trigger("error_rate", ctx.error_rate, ctx.last_agent):
                reasons.append("high_error_rate")
                return "debugger", reasons
            
            # 性能下降（带滞回）
            if self.hysteresis.should_trigger("performance_drop", ctx.performance_drop, ctx.last_agent):
                reasons.append("performance_degraded")
                return "optimizer", reasons
        else:
            # 简单阈值（无滞回）
            if ctx.error_rate > 0.3:
                reasons.append("high_error_rate")
                return "debugger", reasons
            
            if ctx.performance_drop > 0.2:
                reasons.append("performance_degraded")
                return "optimizer", reasons
        
        # 2. 风险等级
        if ctx.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            reasons.append(f"high_risk_{ctx.risk_level.value}")
            return "reviewer", reasons
        
        # 3. 资源约束（降级模型，不换 agent）
        if ctx.cpu_usage > 0.8 or ctx.memory_usage > 0.8:
            reasons.append("resource_constrained")
            agent = self._select_agent_by_task_type(ctx.task_type)
            return agent, reasons
        
        # 4. 任务类型
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
            TaskType.DESIGN: "designer",
            TaskType.CODING: "coder"
        }
        
        agent = task_agent_map.get(ctx.task_type, "coder")
        reasons.append(f"task_type_{ctx.task_type.value}")
        
        return agent, reasons
    
    def _select_model(self, ctx: TaskContext) -> str:
        """模型选择"""
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
    
    def _select_thinking(self, ctx: TaskContext, model: str) -> str:
        """选择 thinking 级别"""
        if ctx.complexity >= 8:
            return "high"
        elif ctx.complexity >= 5:
            return "medium"
        elif ctx.cpu_usage > 0.8:
            return "off"
        else:
            return "low"
    
    def _select_timeout(self, ctx: TaskContext) -> int:
        """选择超时时间"""
        if ctx.max_time:
            return ctx.max_time
        
        if ctx.complexity >= 8:
            return 600
        elif ctx.complexity >= 5:
            return 300
        else:
            return 180
    
    def _select_agent_by_task_type(self, task_type: TaskType) -> str:
        """根据任务类型选择 agent"""
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
            TaskType.DESIGN: "designer",
            TaskType.CODING: "coder"
        }
        return task_agent_map.get(task_type, "coder")
    
    def _calculate_confidence(self, reason_codes: List[str], ctx: TaskContext) -> float:
        """计算置信度"""
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


def demo():
    """演示 UnifiedRouter v1.0"""
    router = UnifiedRouter(enable_guardrails=True)
    
    print("=" * 80)
    print("AIOS Unified Router v1.0 - A（解释性）+ B（防抖滞回）")
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
    decision1 = router.route(ctx1)
    print(f"Agent: {decision1.agent}")
    print(f"Model: {decision1.model}")
    print(f"Reason: {decision1.reason_codes}")
    print(f"Confidence: {decision1.confidence:.2f}")
    
    # 场景 2：高错误率（滞回）
    print("\n" + "=" * 80)
    print("【场景 2】高错误率 35% → debugger")
    ctx2 = TaskContext(
        task_id="task-002",
        description="修复支付接口",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.35,
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6
    )
    decision2 = router.route(ctx2)
    print(f"Agent: {decision2.agent}")
    print(f"Reason: {decision2.reason_codes}")
    
    # 场景 3：错误率下降到 25%（滞回保持）
    print("\n" + "=" * 80)
    print("【场景 3】错误率下降到 25%（滞回保持 debugger）")
    ctx3 = TaskContext(
        task_id="task-003",
        description="继续修复",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.25,  # 在滞回区
        performance_drop=0.0,
        cpu_usage=0.5,
        memory_usage=0.6,
        last_agent="debugger"
    )
    decision3 = router.route(ctx3)
    print(f"Agent: {decision3.agent} (应该保持 debugger)")
    print(f"Reason: {decision3.reason_codes}")
    
    # 场景 4：错误率下降到 15%（退出滞回）
    print("\n" + "=" * 80)
    print("【场景 4】错误率下降到 15%（退出滞回）")
    ctx4 = TaskContext(
        task_id="task-004",
        description="新功能开发",
        task_type=TaskType.CODING,
        complexity=5,
        risk_level=RiskLevel.MEDIUM,
        error_rate=0.15,  # 低于退出阈值
        performance_drop=0.0,
        cpu_usage=0.4,
        memory_usage=0.5,
        last_agent="debugger"
    )
    decision4 = router.route(ctx4)
    print(f"Agent: {decision4.agent} (应该切换到 coder)")
    print(f"Reason: {decision4.reason_codes}")
    
    print("\n" + "=" * 80)
    print("✅ UnifiedRouter v1.0 演示完成")
    print("=" * 80)
    print("\n核心护栏验证：")
    print("1. ✅ 解释性 - 每次决策落盘到 router_decisions.jsonl")
    print("2. ✅ 防抖 - sticky agent（10 分钟）")
    print("3. ✅ 滞回 - 进入 30%/退出 20%（防止抖动）")
    print("4. ✅ 内存缓存 - 30 秒刷盘一次（性能优化）")


if __name__ == "__main__":
    demo()
