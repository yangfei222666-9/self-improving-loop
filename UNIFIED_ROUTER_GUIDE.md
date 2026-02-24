# UnifiedRouter 使用指南

## 目录
- [核心概念](#核心概念)
- [三档模式](#三档模式)
- [使用方法](#使用方法)
- [配置选项](#配置选项)
- [护栏机制](#护栏机制)
- [最佳实践](#最佳实践)
- [代码示例](#代码示例)

---

## 核心概念

### 什么是 UnifiedRouter？

UnifiedRouter 是 AIOS 的智能任务路由器，负责根据任务特征选择最合适的 Agent、模型和执行策略。

**核心特性：**
- 🎯 **三档模式**：simple（快速）/ full（完整护栏）/ auto（自适应）
- 🛡️ **2 个核心护栏**：解释性 + 防抖滞回（所有模式）
- 📊 **能力矩阵**：18 个原子能力 + 17 个专业模板
- 🔍 **可复盘**：每次决策落盘，包含输入快照、理由、置信度

### 为什么需要 UnifiedRouter？

**问题：** 传统 Agent 系统要么过于简单（if-else），要么过于复杂（ML 模型），难以平衡性能和可靠性。

**解决方案：** UnifiedRouter 提供三档模式，让你根据场景选择：
- 日常任务 → simple 模式（快速决策）
- 生产环境 → full 模式（完整护栏）
- 不确定 → auto 模式（自动切换）

---

## 三档模式

### 1. Simple Mode（默认）

**适用场景：** 日常开发、快速迭代、低风险任务

**特点：**
- ✅ 快速决策（if-elif 树）
- ✅ 2 个核心护栏（解释性 + 防抖）
- ✅ 低延迟（< 10ms）
- ❌ 无预算控制
- ❌ 无失败回退

**决策逻辑：**
```
1. 系统状态（错误率/性能）
2. 风险等级（CRITICAL 优先）
3. 资源约束（降级模型，不换 agent）
4. 任务类型（coding/debug/optimize...）
```

**示例：**
```python
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

router = UnifiedRouter(mode="simple")
ctx = UnifiedContext(
    task_id="task-001",
    description="修复支付接口超时",
    task_type=TaskType.DEBUG,
    complexity=7,
    risk_level=RiskLevel.HIGH,
    error_rate=0.35
)
plan = router.route(ctx)
# → agent: debugger, model: opus-4-6, thinking: high
```

### 2. Full Mode（生产级）

**适用场景：** 生产环境、高风险任务、需要审计

**特点：**
- ✅ 2 个核心护栏（解释性 + 防抖）
- ✅ 预算控制（Opus 配额 + 自动降级）
- ✅ 失败回退（最多 2 次切换 → needs_human）
- ✅ 完整审计日志（JSONL）
- ⚠️ 稍高延迟（20-50ms）

**4 个护栏：**
1. **解释性** - 每次决策落盘可复盘理由
2. **防抖** - sticky agent + 滞回阈值
3. **预算** - Opus 配额 + 自动降级
4. **失败回退** - 最多 2 次切换 + needs_human

**示例：**
```python
router = UnifiedRouter(mode="full", data_dir="aios/data")
plan = router.route(ctx)

# 决策日志自动写入 aios/data/router_decisions.jsonl
# {
#   "task_id": "task-001",
#   "agent": "debugger",
#   "model": "opus-4-6",
#   "reason_codes": ["high_error_rate", "sticky_applied"],
#   "confidence": 0.95,
#   "input_snapshot": {...},
#   "decided_at": "2025-02-22T14:30:00Z"
# }
```

### 3. Auto Mode（自适应）

**适用场景：** 不确定系统状态、希望自动优化

**特点：**
- ✅ 自动判断使用 simple 还是 full
- ✅ 根据系统健康度切换
- ✅ 平衡性能和可靠性

**切换条件（满足任一则用 full）：**
1. 最近 1 小时事件量 > 200
2. 502/timeout 错误率 > 5%
3. evolution_score 下降 > 10%

**示例：**
```python
router = UnifiedRouter(mode="auto")
plan = router.route(ctx)
print(f"Mode used: {plan.mode_used}")  # simple 或 full
```

---

## 使用方法

### 基本使用

```python
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

# 1. 创建路由器
router = UnifiedRouter(mode="simple")  # 或 "full" / "auto"

# 2. 构建任务上下文
ctx = UnifiedContext(
    task_id="task-001",
    description="优化数据库查询性能",
    task_type=TaskType.OPTIMIZE,
    complexity=8,
    risk_level=RiskLevel.MEDIUM,
    error_rate=0.05,
    performance_drop=0.25,
    cpu_usage=0.7,
    memory_usage=0.6
)

# 3. 路由决策
plan = router.route(ctx)

# 4. 使用决策结果
print(f"Agent: {plan.agent_type}")
print(f"Model: {plan.model}")
print(f"Thinking: {plan.thinking_level}")
print(f"Timeout: {plan.timeout}s")
print(f"Reason: {plan.reason}")
print(f"Confidence: {plan.confidence:.2f}")
```

### 环境变量配置

```bash
# 设置默认模式
export AIOS_ROUTER_MODE=simple  # 或 full / auto

# 设置数据目录
export AIOS_DATA_DIR=aios/data
```

### 集成到 AIOS

```python
from aios import AIOS
from aios.agent_system import UnifiedRouter

system = AIOS()
router = UnifiedRouter(mode="auto")

# 处理任务时使用路由器
def handle_task(task_description):
    ctx = system.analyze_task(task_description)
    plan = router.route(ctx)
    agent = system.spawn_agent(plan.agent_type, plan.model, plan.thinking_level)
    result = agent.execute(task_description, timeout=plan.timeout)
    return result
```

---

## 配置选项

### UnifiedRouter 参数

```python
UnifiedRouter(
    mode: str = "simple",           # simple / full / auto
    data_dir: str = "aios/data"     # 数据目录（full 模式需要）
)
```

### UnifiedContext 参数

```python
UnifiedContext(
    # 必需
    task_id: str,                   # 任务 ID
    description: str,               # 任务描述
    task_type: TaskType,            # 任务类型
    complexity: int,                # 复杂度 1-10
    risk_level: RiskLevel,          # 风险等级
    
    # 系统状态
    error_rate: float = 0.0,        # 错误率 0-1
    performance_drop: float = 0.0,  # 性能下降 0-1
    cpu_usage: float = 0.0,         # CPU 使用率 0-1
    memory_usage: float = 0.0,      # 内存使用率 0-1
    
    # 约束（可选）
    max_cost: Optional[float] = None,   # 最大成本
    max_time: Optional[int] = None,     # 最大时间（秒）
    
    # 历史（可选）
    last_agent: Optional[str] = None,   # 上次使用的 agent
    failure_count: int = 0              # 失败次数
)
```

### TaskType 枚举

```python
class TaskType(Enum):
    CODING = "coding"           # 编写代码
    REFACTOR = "refactor"       # 重构代码
    DEBUG = "debug"             # 调试 bug
    TEST = "test"               # 编写测试
    MONITOR = "monitor"         # 系统监控
    DEPLOY = "deploy"           # 部署发布
    OPTIMIZE = "optimize"       # 性能优化
    ANALYZE = "analyze"         # 数据分析
    RESEARCH = "research"       # 信息研究
    REVIEW = "review"           # 代码审查
    DOCUMENT = "document"       # 编写文档
```

### RiskLevel 枚举

```python
class RiskLevel(Enum):
    LOW = "low"                 # 低风险（只读操作）
    MEDIUM = "medium"           # 中风险（修改代码）
    HIGH = "high"               # 高风险（部署/删除）
    CRITICAL = "critical"       # 极高风险（生产环境）
```

---

## 护栏机制

### 护栏 1：解释性（Explainability）

**目标：** 每次决策可复盘，包含输入快照、理由、置信度

**实现：**
```python
# 决策日志格式（JSONL）
{
    "task_id": "task-001",
    "agent": "debugger",
    "model": "opus-4-6",
    "thinking": "high",
    "reason_codes": ["high_error_rate", "sticky_applied"],
    "confidence": 0.95,
    "input_snapshot": {
        "task_type": "debug",
        "complexity": 7,
        "error_rate": 0.35,
        ...
    },
    "decided_at": "2025-02-22T14:30:00Z",
    "decision_time_ms": 15
}
```

**查看决策日志：**
```bash
# 查看最近 10 条决策
tail -n 10 aios/data/router_decisions.jsonl | jq

# 统计 agent 分布
cat aios/data/router_decisions.jsonl | jq -r '.agent' | sort | uniq -c

# 查找高置信度决策
cat aios/data/router_decisions.jsonl | jq 'select(.confidence > 0.9)'
```

### 护栏 2：防抖滞回（Anti-Flapping）

**目标：** 防止频繁切换 agent，保持决策稳定性

**机制：**
1. **Sticky Agent** - 同一任务类型优先使用上次的 agent
2. **滞回阈值** - 只有显著变化才切换（error_rate ±0.1）

**示例：**
```python
# 第一次决策
ctx1 = UnifiedContext(
    task_id="task-001",
    task_type=TaskType.DEBUG,
    error_rate=0.35,
    last_agent=None
)
plan1 = router.route(ctx1)
# → agent: debugger

# 第二次决策（error_rate 小幅下降）
ctx2 = UnifiedContext(
    task_id="task-002",
    task_type=TaskType.DEBUG,
    error_rate=0.30,  # 下降 0.05，未达到滞回阈值
    last_agent="debugger"
)
plan2 = router.route(ctx2)
# → agent: debugger（sticky 生效，不切换）

# 第三次决策（error_rate 大幅下降）
ctx3 = UnifiedContext(
    task_id="task-003",
    task_type=TaskType.DEBUG,
    error_rate=0.10,  # 下降 0.25，超过滞回阈值
    last_agent="debugger"
)
plan3 = router.route(ctx3)
# → agent: coder（切换到正常开发）
```

**配置滞回阈值：**
```python
# simple_router.py
HYSTERESIS_THRESHOLD = 0.1  # 错误率变化阈值

# production_router.py
STICKY_DURATION_SEC = 300   # sticky 持续时间（5 分钟）
```

### 护栏 3：预算控制（Full Mode）

**目标：** 控制 Opus 使用量，避免成本失控

**机制：**
1. 追踪 Opus 使用次数（每小时）
2. 超过配额自动降级到 Sonnet
3. 重置周期（每小时）

**示例：**
```python
# aios/data/router_budget.json
{
    "opus_quota_per_hour": 10,
    "current_hour": "2025-02-22T14:00:00Z",
    "opus_used": 7,
    "sonnet_used": 23
}

# 决策逻辑
if opus_used >= opus_quota_per_hour:
    model = "sonnet-4-5"  # 降级
    reason_codes.append("budget_exceeded")
else:
    model = "opus-4-6"
    opus_used += 1
```

### 护栏 4：失败回退（Full Mode）

**目标：** 防止无限重试，及时人工介入

**机制：**
1. 追踪失败次数（同一任务）
2. 第 1 次失败 → 切换 agent
3. 第 2 次失败 → 切换 agent + 降级模型
4. 第 3 次失败 → needs_human = True

**示例：**
```python
# 第 1 次失败
ctx1 = UnifiedContext(
    task_id="task-001",
    failure_count=1,
    last_agent="coder"
)
plan1 = router.route(ctx1)
# → agent: debugger（切换）

# 第 2 次失败
ctx2 = UnifiedContext(
    task_id="task-001",
    failure_count=2,
    last_agent="debugger"
)
plan2 = router.route(ctx2)
# → agent: optimizer, model: sonnet-4-5（切换 + 降级）

# 第 3 次失败
ctx3 = UnifiedContext(
    task_id="task-001",
    failure_count=3,
    last_agent="optimizer"
)
plan3 = router.route(ctx3)
# → needs_human: True（人工介入）
```

---

## 最佳实践

### 1. 选择合适的模式

| 场景 | 推荐模式 | 理由 |
|------|---------|------|
| 日常开发 | simple | 快速决策，低延迟 |
| 生产环境 | full | 完整护栏，可审计 |
| 不确定 | auto | 自动切换，平衡性能和可靠性 |
| 高风险任务 | full | 失败回退，预算控制 |
| 低风险任务 | simple | 无需额外开销 |

### 2. 合理设置复杂度和风险等级

```python
# 复杂度（1-10）
complexity = 1-3   # 简单任务（修改配置、查询数据）
complexity = 4-6   # 中等任务（实现功能、修复 bug）
complexity = 7-9   # 复杂任务（重构、优化、架构设计）
complexity = 10    # 极复杂任务（多模块协作、系统级改动）

# 风险等级
risk_level = LOW       # 只读操作（查询、分析）
risk_level = MEDIUM    # 修改代码（开发、测试）
risk_level = HIGH      # 部署/删除（发布、清理）
risk_level = CRITICAL  # 生产环境（线上修复、数据迁移）
```

### 3. 利用历史信息

```python
# 传递上次 agent 和失败次数
ctx = UnifiedContext(
    task_id="task-001",
    description="继续优化性能",
    task_type=TaskType.OPTIMIZE,
    complexity=7,
    risk_level=RiskLevel.MEDIUM,
    last_agent="optimizer",  # 上次使用的 agent
    failure_count=0          # 失败次数
)
```

### 4. 监控决策质量

```bash
# 统计 agent 分布
cat aios/data/router_decisions.jsonl | jq -r '.agent' | sort | uniq -c

# 统计模型使用
cat aios/data/router_decisions.jsonl | jq -r '.model' | sort | uniq -c

# 统计置信度分布
cat aios/data/router_decisions.jsonl | jq '.confidence' | \
  awk '{sum+=$1; count++} END {print "Avg:", sum/count}'

# 查找低置信度决策
cat aios/data/router_decisions.jsonl | jq 'select(.confidence < 0.7)'
```

### 5. 自定义护栏阈值

```python
# simple_router.py
class SimpleRouter:
    def __init__(self):
        self.error_threshold = 0.3      # 错误率阈值
        self.perf_threshold = 0.2       # 性能下降阈值
        self.hysteresis = 0.1           # 滞回阈值

# production_router.py
class ProductionRouter:
    def __init__(self, data_dir: str = "aios/data"):
        self.sticky_duration_sec = 300  # sticky 持续时间
        self.opus_quota_per_hour = 10   # Opus 配额
        self.max_failures = 3           # 最大失败次数
```

---

## 代码示例

### 示例 1：基本使用

```python
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

# 创建路由器
router = UnifiedRouter(mode="simple")

# 任务 1：编写代码
ctx1 = UnifiedContext(
    task_id="task-001",
    description="实现用户登录功能",
    task_type=TaskType.CODING,
    complexity=5,
    risk_level=RiskLevel.MEDIUM
)
plan1 = router.route(ctx1)
print(f"Task 1: {plan1.agent_type} / {plan1.model} / {plan1.reason}")
# → coder / opus-4-6 / 编码任务

# 任务 2：调试 bug
ctx2 = UnifiedContext(
    task_id="task-002",
    description="修复支付接口超时",
    task_type=TaskType.DEBUG,
    complexity=7,
    risk_level=RiskLevel.HIGH,
    error_rate=0.35
)
plan2 = router.route(ctx2)
print(f"Task 2: {plan2.agent_type} / {plan2.model} / {plan2.reason}")
# → debugger / opus-4-6 / 高错误率 35.0%
```

### 示例 2：高级配置

```python
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

# 使用 full 模式
router = UnifiedRouter(mode="full", data_dir="aios/data")

# 复杂任务：性能优化
ctx = UnifiedContext(
    task_id="task-003",
    description="优化数据库查询性能",
    task_type=TaskType.OPTIMIZE,
    complexity=8,
    risk_level=RiskLevel.HIGH,
    error_rate=0.05,
    performance_drop=0.30,
    cpu_usage=0.85,
    memory_usage=0.70,
    max_cost=10.0,      # 最大成本 $10
    max_time=600,       # 最大时间 10 分钟
    last_agent="coder",
    failure_count=0
)

plan = router.route(ctx)

print(f"Agent: {plan.agent_type}")
print(f"Model: {plan.model}")
print(f"Thinking: {plan.thinking_level}")
print(f"Timeout: {plan.timeout}s")
print(f"Reason: {plan.reason}")
print(f"Confidence: {plan.confidence:.2f}")
print(f"Mode: {plan.mode_used}")

# 输出：
# Agent: optimizer
# Model: opus-4-6
# Thinking: high
# Timeout: 300
# Reason: 性能下降 30.0% / sticky_applied
# Confidence: 0.95
# Mode: full
```

### 示例 3：自定义护栏

```python
from aios.agent_system.production_router import ProductionRouter
from aios.agent_system import UnifiedContext, TaskType, RiskLevel

# 自定义护栏阈值
class CustomRouter(ProductionRouter):
    def __init__(self, data_dir: str = "aios/data"):
        super().__init__(data_dir)
        # 自定义配置
        self.sticky_duration_sec = 600      # 10 分钟 sticky
        self.opus_quota_per_hour = 20       # 提高 Opus 配额
        self.max_failures = 2               # 降低失败容忍度

router = CustomRouter()

ctx = UnifiedContext(
    task_id="task-004",
    description="重构支付模块",
    task_type=TaskType.REFACTOR,
    complexity=9,
    risk_level=RiskLevel.HIGH
)

plan = router.route(ctx)
print(f"Custom router: {plan.agent_type} / {plan.model}")
```

### 示例 4：批量路由

```python
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

router = UnifiedRouter(mode="auto")

# 批量任务
tasks = [
    ("实现用户注册", TaskType.CODING, 5, RiskLevel.MEDIUM),
    ("修复登录 bug", TaskType.DEBUG, 6, RiskLevel.HIGH),
    ("优化查询性能", TaskType.OPTIMIZE, 8, RiskLevel.HIGH),
    ("编写 API 文档", TaskType.DOCUMENT, 4, RiskLevel.LOW),
]

for i, (desc, task_type, complexity, risk) in enumerate(tasks):
    ctx = UnifiedContext(
        task_id=f"task-{i+1:03d}",
        description=desc,
        task_type=task_type,
        complexity=complexity,
        risk_level=risk
    )
    plan = router.route(ctx)
    print(f"{desc:20s} → {plan.agent_type:12s} / {plan.model:12s} / {plan.mode_used}")

# 输出：
# 实现用户注册           → coder        / opus-4-6     / simple
# 修复登录 bug          → debugger     / opus-4-6     / simple
# 优化查询性能           → optimizer    / opus-4-6     / simple
# 编写 API 文档         → documenter   / sonnet-4-5   / simple
```

### 示例 5：与能力矩阵集成

```python
from aios.agent_system import UnifiedRouter, CapabilityMatcher, UnifiedContext, TaskType, RiskLevel

router = UnifiedRouter(mode="simple")
matcher = CapabilityMatcher()

# 从任务描述推断能力
task_desc = "优化这段代码的性能，找出瓶颈并重构"
capabilities = matcher.infer_capabilities_from_task(task_desc)
print(f"Inferred capabilities: {capabilities}")
# → ["coding", "debugging", "profiling", "optimization"]

# 匹配最佳模板
match = matcher.match_template(capabilities)
print(f"Best match: {match['template_name']} (score: {match['match_score']:.2f})")
# → optimizer (score: 0.85)

# 合并能力配置
config = matcher.merge_capabilities(capabilities)
print(f"Merged config: {config}")
# → {tools: [...], model: "opus-4-6", thinking: "high"}

# 使用路由器决策
ctx = UnifiedContext(
    task_id="task-001",
    description=task_desc,
    task_type=TaskType.OPTIMIZE,
    complexity=8,
    risk_level=RiskLevel.MEDIUM
)
plan = router.route(ctx)
print(f"Router decision: {plan.agent_type} / {plan.model}")
# → optimizer / opus-4-6
```

---

## 故障排查

### 问题 1：决策日志未生成

**症状：** `aios/data/router_decisions.jsonl` 不存在

**原因：** 使用 simple 模式（不写日志）

**解决：** 切换到 full 模式
```python
router = UnifiedRouter(mode="full", data_dir="aios/data")
```

### 问题 2：频繁切换 agent

**症状：** 同一任务类型频繁切换 agent

**原因：** 未传递 `last_agent` 参数

**解决：** 传递历史信息
```python
ctx = UnifiedContext(
    task_id="task-001",
    task_type=TaskType.DEBUG,
    last_agent="debugger",  # 传递上次 agent
    ...
)
```

### 问题 3：Opus 配额耗尽

**症状：** 所有任务都使用 Sonnet

**原因：** Opus 配额用完

**解决：** 等待下一小时重置，或提高配额
```python
# production_router.py
self.opus_quota_per_hour = 20  # 提高配额
```

### 问题 4：低置信度决策

**症状：** `confidence < 0.7`

**原因：** 任务特征不明确

**解决：** 提供更多上下文信息
```python
ctx = UnifiedContext(
    task_id="task-001",
    description="详细的任务描述",  # 更详细
    task_type=TaskType.DEBUG,
    complexity=7,                  # 明确复杂度
    risk_level=RiskLevel.HIGH,     # 明确风险
    error_rate=0.35,               # 提供系统状态
    performance_drop=0.0,
    ...
)
```

---

## 总结

UnifiedRouter 提供了灵活的三档模式，满足不同场景需求：

- **Simple** - 快速决策，适合日常开发
- **Full** - 完整护栏，适合生产环境
- **Auto** - 自动切换，平衡性能和可靠性

**2 个核心护栏**（所有模式）：
1. 解释性 - 每次决策可复盘
2. 防抖滞回 - 保持决策稳定性

**额外护栏**（Full 模式）：
3. 预算控制 - 避免成本失控
4. 失败回退 - 及时人工介入

**最佳实践：**
- 根据场景选择模式
- 合理设置复杂度和风险等级
- 传递历史信息（last_agent, failure_count）
- 监控决策质量（日志分析）
- 自定义护栏阈值（根据需求）

更多信息请参考：
- [Dashboard Guide](../dashboard/DASHBOARD_GUIDE.md) - 实时监控决策
- [Developer Guide](DEVELOPER_GUIDE.md) - 扩展和自定义
- [Capability Matrix](capabilities.py) - 能力矩阵详解
