# AIOS 系统优化方案

> 分析日期：2025-07-17
> 分析范围：agent_system 路由层 + core 模型路由层

---

## 一、现状诊断

### 1.1 路由器清单（共 5 个，严重冗余）

| 文件 | 职责 | 实际使用 | 状态 |
|------|------|----------|------|
| `agent_system/simple_router.py` | if-elif 决策树，选 agent | ✅ `__init__.py` 引用 | 主力 |
| `agent_system/production_router.py` | 4 护栏（防抖/预算/回退/日志） | ❌ 未被引用 | 闲置 |
| `agent_system/task_router.py` | 能力匹配 + 多维决策 | ❌ 未被引用 | 闲置 |
| `agent_system/core/task_router.py` | JSON 规则 + 关键词匹配 | ❌ 仅 test.py 引用 | 遗留 |
| `core/model_router_v2.py` | Ollama/Claude 选择 | ❌ 未被引用 | 遗留 |
| `core/model_router.py` | 同上（v1） | ❌ 未被引用 | 遗留 |

**问题**：5 个路由器，只有 `simple_router` 在用。`production_router` 的 4 个护栏（防抖、预算、失败回退、决策日志）是有价值的功能，但完全没接入。

### 1.2 重复代码

- `TaskType` 枚举定义了 3 次（simple_router / production_router / task_router）
- `RiskLevel` 枚举定义了 3 次
- `TaskContext` dataclass 定义了 3 次，字段各不相同
- 模型选择逻辑（复杂度→模型）在 3 个文件中各写了一遍
- 关键词→任务类型推断在 `capabilities.py` 和 `__init__.py` 中各写了一遍

### 1.3 性能问题

- `production_router` 每次 `route()` 都做 3 次文件 I/O（load sticky / load budget / load failures）
- 决策日志是 append-only JSONL，无清理机制，会无限增长
- `_update_system_state()` 每次读取整个 `events.jsonl` 的最后 100 行

### 1.4 功能缺口

- `__init__.py` 用的是 `SimpleRouter`，没有防抖/预算/失败回退
- `CircuitBreaker` 存在但未接入路由层
- CPU/内存使用率是硬编码占位值（0.4/0.5）
- 没有真正的系统指标采集

---

## 二、优化方案（按优先级）

### P0 - 统一路由器（消除冗余）

**目标**：合并为 1 个路由器，保留所有有价值的功能。

**方案**：创建 `unified_router.py`，分层设计：

```
┌─────────────────────────────────┐
│         UnifiedRouter           │
│  ┌───────────────────────────┐  │
│  │  Layer 1: 护栏（可选）     │  │
│  │  - 防抖 (sticky)          │  │
│  │  - 预算 (budget)          │  │
│  │  - 熔断 (circuit_breaker) │  │
│  │  - 失败回退 (fallback)    │  │
│  ├───────────────────────────┤  │
│  │  Layer 2: 核心决策         │  │
│  │  - 系统状态 > 风险 > 任务  │  │
│  │  (来自 simple_router)     │  │
│  ├───────────────────────────┤  │
│  │  Layer 3: 模型选择         │  │
│  │  - 复杂度 + 预算 + 资源   │  │
│  ├───────────────────────────┤  │
│  │  Layer 4: 决策日志         │  │
│  │  - JSONL 落盘             │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

**共享类型**：提取到 `types.py`

```python
# aios/agent_system/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

class TaskType(Enum):
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
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ExecutionMode(Enum):
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
```

**统一路由器核心**：

```python
# aios/agent_system/unified_router.py
class UnifiedRouter:
    def __init__(self, data_dir="aios/data", enable_guardrails=True):
        self.enable_guardrails = enable_guardrails
        if enable_guardrails:
            self._sticky = StickyCache(data_dir)
            self._budget = BudgetTracker(data_dir)
            self._breaker = CircuitBreaker()
        self._logger = DecisionLogger(data_dir)

    def route(self, ctx: TaskContext) -> Decision:
        reasons = []

        # 护栏 1: 熔断检查
        if self.enable_guardrails and not self._breaker.should_execute(ctx.task_type.value):
            reasons.append("circuit_open")
            return Decision(agent="reviewer", model="claude-sonnet-4-5",
                          thinking="off", timeout=60,
                          execution_mode=ExecutionMode.DRY_RUN,
                          reason_codes=reasons, confidence=0.3)

        # 护栏 2: 防抖
        if self.enable_guardrails:
            sticky = self._sticky.check(ctx.task_type)
            if sticky:
                reasons.append("sticky_applied")
                # 用 sticky agent 但继续走模型选择

        # 核心决策（simple_router 的逻辑，不变）
        agent, agent_reasons = self._decide_agent(ctx)
        reasons.extend(agent_reasons)

        # 护栏 3: 失败回退
        if ctx.failure_count >= 2:
            agent = "reviewer"
            reasons.append("max_retries_exceeded")
            mode = ExecutionMode.DRY_RUN
        else:
            mode = ExecutionMode.APPLY

        # 模型选择（带预算）
        model, model_reasons = self._select_model(ctx)
        reasons.extend(model_reasons)

        decision = Decision(
            agent=agent, model=model,
            thinking=self._select_thinking(ctx, model),
            timeout=self._select_timeout(ctx),
            execution_mode=mode,
            reason_codes=reasons,
            confidence=self._calc_confidence(reasons, ctx)
        )

        # 落盘
        self._logger.log(decision, ctx)
        return decision
```

**清理计划**：

| 操作 | 文件 |
|------|------|
| 新建 | `types.py`, `unified_router.py` |
| 归档到 `_deprecated/` | `simple_router.py`, `production_router.py`, `task_router.py` |
| 归档到 `_deprecated/` | `core/task_router.py`, `core/model_router.py`, `core/model_router_v2.py` |
| 修改 | `__init__.py` → 引用 `UnifiedRouter` |

---

### P0 - 接入真实系统指标

**问题**：`cpu_usage` 和 `memory_usage` 是硬编码的 0.4/0.5。

**方案**：

```python
# aios/agent_system/system_metrics.py
import psutil

class SystemMetrics:
    """轻量系统指标采集（缓存 5 秒）"""

    def __init__(self, cache_ttl=5):
        self._cache = {}
        self._cache_time = 0
        self._ttl = cache_ttl

    def get(self) -> dict:
        now = time.time()
        if now - self._cache_time < self._ttl:
            return self._cache

        self._cache = {
            "cpu_usage": psutil.cpu_percent(interval=0.1) / 100,
            "memory_usage": psutil.virtual_memory().percent / 100,
        }
        self._cache_time = now
        return self._cache
```

在 `__init__.py` 的 `_update_system_state()` 中替换硬编码值。

---

### P1 - 文件 I/O 优化

**问题**：`production_router` 每次路由都读写 3 个 JSON 文件。

**方案**：内存缓存 + 定期刷盘

```python
class StickyCache:
    """内存优先的 sticky 状态"""

    def __init__(self, data_dir, flush_interval=30):
        self._state = self._load(data_dir)
        self._dirty = False
        self._last_flush = time.time()
        self._flush_interval = flush_interval
        self._path = Path(data_dir) / "router_sticky.json"

    def check(self, task_type: TaskType) -> Optional[str]:
        key = task_type.value
        record = self._state.get(key)
        if not record:
            return None
        if time.time() - record["ts"] > 600:  # 10 分钟过期
            del self._state[key]
            self._dirty = True
            return None
        return record["agent"]

    def record(self, task_type: TaskType, agent: str):
        self._state[task_type.value] = {"agent": agent, "ts": time.time()}
        self._dirty = True
        self._maybe_flush()

    def _maybe_flush(self):
        if self._dirty and time.time() - self._last_flush > self._flush_interval:
            self._path.write_text(json.dumps(self._state, ensure_ascii=False))
            self._dirty = False
            self._last_flush = time.time()
```

**预期收益**：路由延迟从 ~10ms 降到 <1ms（消除同步文件 I/O）。

---

### P1 - 决策日志清理

**问题**：`router_decisions.jsonl` 无限增长。

**方案**：

```python
class DecisionLogger:
    MAX_LINES = 1000  # 保留最近 1000 条

    def log(self, decision, ctx):
        # append
        with open(self._path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # 定期截断（每 100 次写入检查一次）
        self._write_count += 1
        if self._write_count % 100 == 0:
            self._truncate()

    def _truncate(self):
        lines = self._path.read_text().splitlines()
        if len(lines) > self.MAX_LINES:
            keep = lines[-self.MAX_LINES:]
            self._path.write_text('\n'.join(keep) + '\n')
```

---

### P1 - 接入 CircuitBreaker

**问题**：`circuit_breaker.py` 已实现但未接入路由。

**方案**：在 `UnifiedRouter` 中作为第一个护栏检查（见 P0 代码示例）。

---

### P2 - 决策回放/模拟

**目标**：支持离线回放历史决策，验证路由逻辑变更的影响。

```python
class DecisionReplayer:
    """从 JSONL 回放历史决策"""

    def replay(self, router, decisions_file):
        results = []
        for entry in self._read_jsonl(decisions_file):
            ctx = TaskContext(**entry["input_snapshot"])
            old_decision = entry["plan"]
            new_decision = router.route(ctx)

            results.append({
                "task_id": ctx.task_id,
                "old_agent": old_decision["agent_type"],
                "new_agent": new_decision.agent,
                "changed": old_decision["agent_type"] != new_decision.agent,
            })

        changed = sum(1 for r in results if r["changed"])
        print(f"回放 {len(results)} 条决策，{changed} 条发生变化 ({changed/len(results)*100:.1f}%)")
        return results
```

**用途**：修改路由逻辑前，先回放历史数据看影响面。

---

### P2 - 用户偏好 & 历史成功率

**目标**：路由决策考虑历史数据。

```python
# 在 UnifiedRouter._decide_agent 中增加：

def _adjust_by_history(self, agent, ctx):
    """根据历史成功率微调"""
    stats = self._load_agent_stats(agent)
    if stats and stats.get("success_rate", 1.0) < 0.5:
        # 该 agent 对此类任务成功率低，尝试备选
        fallback = FALLBACK_MAP.get(agent)
        if fallback:
            return fallback, ["low_success_rate_fallback"]
    return agent, []
```

这个功能依赖 `evolution.py` 的数据积累，当前数据量不足以有效工作，标记为 P2。

---

### P2 - Dashboard 增强

**当前问题**：
- Dashboard 只读取 `production_router` 的日志格式
- 没有 WebSocket 实时推送（用 5 秒轮询）

**方案**：
- 统一日志格式后 Dashboard 自动兼容
- 暂不加 WebSocket（轮询对当前规模足够）

---

## 三、实施路线图

```
Week 1 (P0):
  ├── 创建 types.py（统一类型定义）
  ├── 创建 unified_router.py（合并 3 个路由器）
  ├── 修改 __init__.py 引用 UnifiedRouter
  ├── 创建 system_metrics.py（真实 CPU/内存）
  ├── 归档旧路由器到 _deprecated/
  └── 更新测试

Week 2 (P1):
  ├── 实现 StickyCache（内存缓存 + 定期刷盘）
  ├── 实现 DecisionLogger（带截断）
  ├── 接入 CircuitBreaker
  └── 性能基准测试

Week 3+ (P2):
  ├── DecisionReplayer
  ├── 历史成功率调整
  └── Dashboard 适配
```

---

## 四、预期收益

| 维度 | 当前 | 优化后 |
|------|------|--------|
| 路由器数量 | 5 个（3 个闲置） | 1 个 |
| 重复类型定义 | 3 份 | 1 份 |
| 路由延迟 | ~10ms（含文件 I/O） | <1ms（内存缓存） |
| 护栏功能 | 0/4 接入 | 4/4 接入 |
| 系统指标 | 硬编码占位 | 真实采集 |
| 熔断器 | 已实现未接入 | 已接入 |
| 决策日志 | 无限增长 | 自动截断 |
| 代码行数 | ~1800 行（5 文件） | ~400 行（2 文件） |

---

## 五、风险与注意事项

1. `core/task_router.py` 被 `test.py` 的 `test_task_routing()` 引用，归档前需更新测试
2. `core/model_router_v2.py` 的 Ollama 路由逻辑目前不在 agent_system 路由范围内，属于不同层级（模型调用层 vs 任务路由层），保持独立但标记为低优先级清理
3. `production_router` 的滞回阈值（hysteresis）是好设计，合并时保留
4. 统一后需要跑一遍所有现有测试确保无回归
