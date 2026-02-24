#!/usr/bin/env python3
"""
AIOS Task Router - 智能任务路由与决策系统
三大核心能力：
1. 自动化运维（监控 → 决策 → 修复）
2. 多 Agent 协作（任务分解 → 并行执行 → 结果聚合）
3. 系统自动进化（学习 → 优化 → 升级）
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

# 导入能力匹配器
from capabilities import CapabilityMatcher, CAPABILITIES


class TaskType(Enum):
    """任务类型"""
    # 开发类
    CODING = "coding"
    REFACTOR = "refactor"
    DEBUG = "debug"
    TEST = "test"
    
    # 运维类
    MONITOR = "monitor"
    DEPLOY = "deploy"
    OPTIMIZE = "optimize"
    AUTOMATE = "automate"
    
    # 分析类
    ANALYZE = "analyze"
    RESEARCH = "research"
    
    # 设计类
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    
    # 审查类
    REVIEW = "review"
    AUDIT = "audit"
    
    # 文档类
    DOCUMENT = "document"
    TRANSLATE = "translate"


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"          # 只读操作
    MEDIUM = "medium"    # 写文件、执行安全命令
    HIGH = "high"        # 修改代码、部署
    CRITICAL = "critical"  # 删除、系统级操作


class Priority(Enum):
    """优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class TaskContext:
    """任务上下文"""
    # 基本信息
    task_id: str
    description: str
    task_type: TaskType
    
    # 决策因素
    complexity: int  # 1-10
    risk_level: RiskLevel
    priority: Priority
    
    # 系统状态
    error_rate: float  # 最近错误率
    performance_drop: float  # 性能下降百分比
    resource_usage: Dict[str, float]  # CPU/内存/GPU 使用率
    
    # 历史数据
    similar_tasks_success_rate: float  # 类似任务成功率
    last_agent_used: Optional[str]  # 上次使用的 Agent
    
    # 约束条件
    max_cost: Optional[float]  # 最大成本（美元）
    max_time: Optional[int]  # 最大时间（秒）
    required_capabilities: List[str]  # 必需能力


@dataclass
class RoutingDecision:
    """路由决策"""
    # Agent 选择
    agent_template: str
    agent_name: str
    capabilities: List[str]
    
    # 模型选择
    model: str
    thinking: str
    
    # 执行策略
    execution_mode: str  # single/parallel/sequential
    fallback_agents: List[str]  # 备用 Agent
    
    # 资源控制
    max_retries: int
    timeout: int
    
    # 决策依据
    decision_reason: str
    confidence: float  # 0-1


class TaskRouter:
    """智能任务路由器"""
    
    def __init__(self, data_dir: str = "aios/data"):
        self.data_dir = Path(data_dir)
        self.matcher = CapabilityMatcher()
        
        # 加载历史数据
        self.agent_stats = self._load_agent_stats()
        self.system_state = self._load_system_state()
    
    def route(self, context: TaskContext) -> RoutingDecision:
        """
        智能路由决策
        
        决策流程：
        1. 分析任务类型和复杂度
        2. 评估系统状态（错误率、性能、资源）
        3. 选择最佳 Agent（能力匹配 + 历史成功率）
        4. 选择模型（复杂度 + 成本约束）
        5. 制定执行策略（单一/并行/顺序）
        6. 设置降级方案（备用 Agent + 重试）
        """
        
        # 1. 任务类型分析
        task_caps = self._infer_capabilities(context)
        
        # 2. 系统状态评估
        system_health = self._evaluate_system_health(context)
        
        # 3. Agent 选择（核心决策）
        agent_decision = self._select_agent(context, task_caps, system_health)
        
        # 4. 模型选择
        model_decision = self._select_model(context, agent_decision)
        
        # 5. 执行策略
        execution_strategy = self._plan_execution(context, agent_decision)
        
        # 6. 降级方案
        fallback_plan = self._plan_fallback(context, agent_decision)
        
        return RoutingDecision(
            agent_template=agent_decision["template"],
            agent_name=agent_decision["name"],
            capabilities=agent_decision["capabilities"],
            model=model_decision["model"],
            thinking=model_decision["thinking"],
            execution_mode=execution_strategy["mode"],
            fallback_agents=fallback_plan["agents"],
            max_retries=fallback_plan["max_retries"],
            timeout=execution_strategy["timeout"],
            decision_reason=agent_decision["reason"],
            confidence=agent_decision["confidence"]
        )
    
    def _infer_capabilities(self, context: TaskContext) -> List[str]:
        """推断任务所需能力"""
        # 从任务描述推断
        inferred = self.matcher.infer_capabilities_from_task(context.description)
        
        # 从任务类型推断
        type_map = {
            TaskType.CODING: ["coding"],
            TaskType.REFACTOR: ["coding", "refactoring", "architecture"],
            TaskType.DEBUG: ["debugging", "profiling"],
            TaskType.TEST: ["testing", "automation"],
            TaskType.MONITOR: ["monitoring", "data-analysis"],
            TaskType.DEPLOY: ["deployment", "automation"],
            TaskType.OPTIMIZE: ["optimization", "profiling", "coding"],
            TaskType.ANALYZE: ["data-analysis", "research"],
            TaskType.RESEARCH: ["research", "documentation"],
            TaskType.DESIGN: ["design", "architecture"],
            TaskType.ARCHITECTURE: ["architecture", "design"],
            TaskType.REVIEW: ["code-review", "security-audit"],
            TaskType.AUDIT: ["security-audit", "code-review"],
            TaskType.DOCUMENT: ["documentation", "research"],
            TaskType.TRANSLATE: ["translation", "documentation"],
        }
        
        type_caps = type_map.get(context.task_type, [])
        
        # 合并去重
        all_caps = list(set(inferred + type_caps + context.required_capabilities))
        
        return all_caps
    
    def _evaluate_system_health(self, context: TaskContext) -> Dict:
        """评估系统健康状态"""
        health = {
            "status": "healthy",
            "issues": [],
            "recommendations": []
        }
        
        # 错误率检查
        if context.error_rate > 0.3:
            health["status"] = "degraded"
            health["issues"].append(f"高错误率: {context.error_rate:.1%}")
            health["recommendations"].append("使用 debugger 优先")
        
        # 性能检查
        if context.performance_drop > 0.2:
            health["status"] = "degraded"
            health["issues"].append(f"性能下降: {context.performance_drop:.1%}")
            health["recommendations"].append("使用 optimizer 优先")
        
        # 资源检查
        cpu = context.resource_usage.get("cpu", 0)
        memory = context.resource_usage.get("memory", 0)
        
        if cpu > 0.8 or memory > 0.8:
            health["status"] = "overloaded"
            health["issues"].append(f"资源紧张: CPU {cpu:.1%}, 内存 {memory:.1%}")
            health["recommendations"].append("降级到 Sonnet 模型")
        
        return health
    
    def _select_agent(self, context: TaskContext, 
                     capabilities: List[str], 
                     system_health: Dict) -> Dict:
        """
        选择最佳 Agent（核心决策逻辑）
        
        决策因素：
        1. 能力匹配度（必需）
        2. 历史成功率（重要）
        3. 系统状态（重要）
        4. 风险等级（约束）
        5. 成本约束（约束）
        """
        
        # 1. 能力匹配
        match = self.matcher.match_template(capabilities)
        
        if not match:
            # 没有匹配的模板，使用通用 Agent
            return {
                "template": "coder",
                "name": "通用开发专员",
                "capabilities": ["coding", "debugging"],
                "reason": "无匹配模板，使用通用 Agent",
                "confidence": 0.5
            }
        
        # 2. 系统状态调整
        if system_health["status"] == "degraded":
            # 系统降级，优先使用专门的修复 Agent
            if context.error_rate > 0.3:
                return {
                    "template": "debugger",
                    "name": "调试专家",
                    "capabilities": ["debugging", "profiling", "code-review"],
                    "reason": f"高错误率 ({context.error_rate:.1%})，优先调试",
                    "confidence": 0.9
                }
            
            if context.performance_drop > 0.2:
                return {
                    "template": "optimizer",
                    "name": "性能优化专员",
                    "capabilities": ["optimization", "profiling", "coding"],
                    "reason": f"性能下降 ({context.performance_drop:.1%})，优先优化",
                    "confidence": 0.9
                }
        
        # 3. 历史成功率调整
        if context.similar_tasks_success_rate < 0.5 and context.last_agent_used:
            # 上次失败率高，换一个 Agent
            fallback_map = {
                "coder": "debugger",
                "debugger": "optimizer",
                "optimizer": "architect"
            }
            fallback = fallback_map.get(context.last_agent_used, match["template_id"])
            
            return {
                "template": fallback,
                "name": self.matcher.templates[fallback]["name"],
                "capabilities": self.matcher.templates[fallback]["capabilities"],
                "reason": f"上次 {context.last_agent_used} 成功率低 ({context.similar_tasks_success_rate:.1%})，切换到 {fallback}",
                "confidence": 0.7
            }
        
        # 4. 风险等级约束
        if context.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            # 高风险任务，使用审查 Agent
            if "code-review" not in capabilities:
                return {
                    "template": "reviewer",
                    "name": "代码审查专员",
                    "capabilities": ["code-review", "security-audit", "testing"],
                    "reason": f"高风险任务 ({context.risk_level.value})，需要审查",
                    "confidence": 0.8
                }
        
        # 5. 默认使用能力匹配结果
        return {
            "template": match["template_id"],
            "name": match["template_name"],
            "capabilities": match["capabilities"],
            "reason": f"能力匹配 (匹配度: {match['match_score']:.2f})",
            "confidence": match["match_score"]
        }
    
    def _select_model(self, context: TaskContext, agent_decision: Dict) -> Dict:
        """
        选择模型（成本优化）
        
        决策因素：
        1. 任务复杂度（主要）
        2. 成本约束（约束）
        3. 资源使用率（约束）
        """
        
        # 默认模型（从能力合并）
        caps = agent_decision["capabilities"]
        default_config = self.matcher.merge_capabilities(caps)
        default_model = default_config["model"]
        default_thinking = default_config["thinking"]
        
        # 1. 复杂度调整
        if context.complexity <= 3:
            # 简单任务，降级到 Sonnet
            model = "claude-sonnet-4-5"
            thinking = "low"
        elif context.complexity <= 7:
            # 中等任务，使用默认
            model = default_model
            thinking = default_thinking
        else:
            # 复杂任务，升级到 Opus + high thinking
            model = "claude-opus-4-6"
            thinking = "high"
        
        # 2. 成本约束
        if context.max_cost and context.max_cost < 0.1:
            # 低成本约束，强制 Sonnet
            model = "claude-sonnet-4-5"
            thinking = "low"
        
        # 3. 资源约束
        cpu = context.resource_usage.get("cpu", 0)
        if cpu > 0.8:
            # CPU 紧张，降级
            model = "claude-sonnet-4-5"
            thinking = "off"
        
        return {
            "model": model,
            "thinking": thinking
        }
    
    def _plan_execution(self, context: TaskContext, agent_decision: Dict) -> Dict:
        """
        制定执行策略
        
        策略：
        1. single - 单一 Agent 执行
        2. parallel - 多 Agent 并行执行
        3. sequential - 多 Agent 顺序执行
        """
        
        # 默认单一执行
        mode = "single"
        timeout = context.max_time or 300  # 默认 5 分钟
        
        # 复杂任务考虑并行
        if context.complexity >= 8:
            mode = "parallel"
            timeout = context.max_time or 600  # 10 分钟
        
        # 高优先级任务缩短超时
        if context.priority == Priority.CRITICAL:
            timeout = min(timeout, 180)  # 最多 3 分钟
        
        return {
            "mode": mode,
            "timeout": timeout
        }
    
    def _plan_fallback(self, context: TaskContext, agent_decision: Dict) -> Dict:
        """
        制定降级方案
        
        降级策略：
        1. 同类型 Agent 备选
        2. 重试次数根据优先级
        """
        
        # 备用 Agent（同类型）
        template = agent_decision["template"]
        fallback_map = {
            "coder": ["debugger", "optimizer"],
            "debugger": ["coder", "reviewer"],
            "optimizer": ["coder", "architect"],
            "analyst": ["researcher", "monitor"],
            "monitor": ["analyst"],
            "researcher": ["analyst", "documenter"],
        }
        
        fallback_agents = fallback_map.get(template, ["coder"])
        
        # 重试次数
        if context.priority == Priority.CRITICAL:
            max_retries = 1  # 紧急任务快速失败
        elif context.priority == Priority.HIGH:
            max_retries = 2
        else:
            max_retries = 3
        
        return {
            "agents": fallback_agents,
            "max_retries": max_retries
        }
    
    def _load_agent_stats(self) -> Dict:
        """加载 Agent 统计数据"""
        stats_file = self.data_dir / "agent_stats.json"
        if stats_file.exists():
            with open(stats_file) as f:
                return json.load(f)
        return {}
    
    def _load_system_state(self) -> Dict:
        """加载系统状态"""
        state_file = self.data_dir / "system_state.json"
        if state_file.exists():
            with open(state_file) as f:
                return json.load(f)
        return {
            "error_rate": 0.0,
            "performance_drop": 0.0,
            "resource_usage": {"cpu": 0.0, "memory": 0.0}
        }


def demo():
    """演示智能路由"""
    router = TaskRouter()
    
    print("=" * 80)
    print("AIOS Task Router - 智能决策演示")
    print("=" * 80)
    
    # 场景 1：正常开发任务
    print("\n【场景 1】正常开发任务")
    context1 = TaskContext(
        task_id="task-001",
        description="实现用户登录功能，包括密码加密和 JWT token",
        task_type=TaskType.CODING,
        complexity=5,
        risk_level=RiskLevel.MEDIUM,
        priority=Priority.MEDIUM,
        error_rate=0.05,
        performance_drop=0.0,
        resource_usage={"cpu": 0.3, "memory": 0.4},
        similar_tasks_success_rate=0.85,
        last_agent_used=None,
        max_cost=None,
        max_time=None,
        required_capabilities=[]
    )
    
    decision1 = router.route(context1)
    print(f"任务: {context1.description}")
    print(f"决策: {decision1.agent_name} ({decision1.agent_template})")
    print(f"模型: {decision1.model} (thinking: {decision1.thinking})")
    print(f"执行: {decision1.execution_mode} (超时: {decision1.timeout}s)")
    print(f"依据: {decision1.decision_reason}")
    print(f"信心: {decision1.confidence:.2f}")
    
    # 场景 2：高错误率，系统降级
    print("\n" + "=" * 80)
    print("【场景 2】高错误率，系统降级")
    context2 = TaskContext(
        task_id="task-002",
        description="修复支付接口频繁超时的问题",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        priority=Priority.CRITICAL,
        error_rate=0.45,  # 45% 错误率
        performance_drop=0.0,
        resource_usage={"cpu": 0.5, "memory": 0.6},
        similar_tasks_success_rate=0.6,
        last_agent_used="coder",
        max_cost=None,
        max_time=180,
        required_capabilities=[]
    )
    
    decision2 = router.route(context2)
    print(f"任务: {context2.description}")
    print(f"系统状态: 错误率 {context2.error_rate:.1%} (降级)")
    print(f"决策: {decision2.agent_name} ({decision2.agent_template})")
    print(f"模型: {decision2.model} (thinking: {decision2.thinking})")
    print(f"执行: {decision2.execution_mode} (超时: {decision2.timeout}s, 重试: {decision2.max_retries})")
    print(f"备用: {decision2.fallback_agents}")
    print(f"依据: {decision2.decision_reason}")
    print(f"信心: {decision2.confidence:.2f}")
    
    # 场景 3：性能下降，资源紧张
    print("\n" + "=" * 80)
    print("【场景 3】性能下降，资源紧张")
    context3 = TaskContext(
        task_id="task-003",
        description="优化数据库查询，响应时间从 2s 降到 200ms",
        task_type=TaskType.OPTIMIZE,
        complexity=8,
        risk_level=RiskLevel.MEDIUM,
        priority=Priority.HIGH,
        error_rate=0.1,
        performance_drop=0.35,  # 35% 性能下降
        resource_usage={"cpu": 0.85, "memory": 0.9},  # 资源紧张
        similar_tasks_success_rate=0.7,
        last_agent_used=None,
        max_cost=0.05,  # 低成本约束
        max_time=None,
        required_capabilities=[]
    )
    
    decision3 = router.route(context3)
    print(f"任务: {context3.description}")
    print(f"系统状态: 性能下降 {context3.performance_drop:.1%}, CPU {context3.resource_usage['cpu']:.1%}, 内存 {context3.resource_usage['memory']:.1%}")
    print(f"决策: {decision3.agent_name} ({decision3.agent_template})")
    print(f"模型: {decision3.model} (thinking: {decision3.thinking}) [成本约束]")
    print(f"执行: {decision3.execution_mode} (超时: {decision3.timeout}s)")
    print(f"依据: {decision3.decision_reason}")
    print(f"信心: {decision3.confidence:.2f}")
    
    # 场景 4：高风险任务
    print("\n" + "=" * 80)
    print("【场景 4】高风险任务，需要审查")
    context4 = TaskContext(
        task_id="task-004",
        description="部署新版本到生产环境，包含数据库迁移",
        task_type=TaskType.DEPLOY,
        complexity=9,
        risk_level=RiskLevel.CRITICAL,  # 高风险
        priority=Priority.CRITICAL,
        error_rate=0.05,
        performance_drop=0.0,
        resource_usage={"cpu": 0.4, "memory": 0.5},
        similar_tasks_success_rate=0.9,
        last_agent_used=None,
        max_cost=None,
        max_time=None,
        required_capabilities=[]
    )
    
    decision4 = router.route(context4)
    print(f"任务: {context4.description}")
    print(f"风险等级: {context4.risk_level.value}")
    print(f"决策: {decision4.agent_name} ({decision4.agent_template})")
    print(f"模型: {decision4.model} (thinking: {decision4.thinking})")
    print(f"执行: {decision4.execution_mode} (超时: {decision4.timeout}s, 重试: {decision4.max_retries})")
    print(f"依据: {decision4.decision_reason}")
    print(f"信心: {decision4.confidence:.2f}")
    
    print("\n" + "=" * 80)
    print("✅ Task Router 演示完成")
    print("=" * 80)


if __name__ == "__main__":
    demo()
