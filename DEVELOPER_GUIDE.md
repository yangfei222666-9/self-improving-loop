# AIOS 开发者指南

## 目录
- [架构设计](#架构设计)
- [核心组件](#核心组件)
- [扩展指南](#扩展指南)
- [贡献指南](#贡献指南)
- [测试指南](#测试指南)
- [性能优化](#性能优化)

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      AIOS 架构层次                           │
├─────────────────────────────────────────────────────────────┤
│  应用层 (Application Layer)                                 │
│  • 用户交互、任务提交、结果展示                              │
├─────────────────────────────────────────────────────────────┤
│  路由层 (Routing Layer)                                     │
│  • UnifiedRouter (simple/full/auto)                         │
│  • CapabilityMatcher (能力匹配)                             │
│  • 护栏机制 (解释性、防抖、预算、失败回退)                   │
├─────────────────────────────────────────────────────────────┤
│  Agent 层 (Agent Layer)                                     │
│  • Agent 模板 (17 种专业模板)                               │
│  • Agent 管理器 (创建、监控、优化)                          │
│  • 协作编排器 (任务拆解、并行执行)                          │
├─────────────────────────────────────────────────────────────┤
│  学习层 (Learning Layer)                                    │
│  • Autolearn v1.1 (错误签名 → 课程 → 规则)                 │
│  • 模糊匹配 (strict/loose/fuzzy)                            │
│  • 自动重试 (指数退避)                                       │
├─────────────────────────────────────────────────────────────┤
│  自愈层 (Self-Healing Layer)                                │
│  • 传感器 (文件/进程/系统/网络)                             │
│  • 告警器 (阈值检测)                                         │
│  • 反应器 (Playbook 自动修复)                               │
│  • 验证器 (smoke/regression/full)                           │
├─────────────────────────────────────────────────────────────┤
│  数据层 (Data Layer)                                        │
│  • 事件总线 (Event Bus)                                     │
│  • 持久化存储 (JSONL 日志)                                  │
│  • 指标追踪 (SLA、Evolution Score)                          │
├─────────────────────────────────────────────────────────────┤
│  工具层 (Tools Layer)                                       │
│  • Dashboard (实时监控)                                     │
│  • CLI (命令行工具)                                         │
│  • API (RESTful + WebSocket)                                │
└─────────────────────────────────────────────────────────────┘
```

### 设计原则

1. **模块化** - 每个组件独立，低耦合高内聚
2. **可扩展** - 易于添加新的 Agent、护栏、传感器
3. **可观测** - 完整的日志、指标、审计追踪
4. **容错性** - 熔断器、回退机制、失败隔离
5. **性能优先** - 异步执行、批量处理、缓存优化

### 数据流

```
用户请求
    ↓
任务分析 (analyze_task)
    ↓
能力推断 (infer_capabilities)
    ↓
路由决策 (UnifiedRouter.route)
    ↓
Agent 创建/选择 (spawn_agent)
    ↓
任务执行 (agent.execute)
    ↓
结果验证 (verify_result)
    ↓
学习反馈 (learn_from_result)
    ↓
返回用户
```

---

## 核心组件

### 1. UnifiedRouter

**职责：** 根据任务特征选择最合适的 Agent、模型和执行策略

**核心文件：**
- `agent_system/unified_router.py` - 统一路由器
- `agent_system/simple_router.py` - 简洁版路由器
- `agent_system/production_router.py` - 生产级路由器

**关键方法：**
```python
class UnifiedRouter:
    def route(self, ctx: UnifiedContext) -> UnifiedPlan:
        """路由决策入口"""
        if self.mode == RouterMode.SIMPLE:
            return self._route_simple(ctx)
        elif self.mode == RouterMode.FULL:
            return self._route_full(ctx)
        elif self.mode == RouterMode.AUTO:
            if self._should_use_full(ctx):
                return self._route_full(ctx)
            else:
                return self._route_simple(ctx)
```

**扩展点：**
- 添加新的路由模式
- 自定义护栏逻辑
- 调整决策权重

### 2. CapabilityMatcher

**职责：** 从任务描述推断所需能力，匹配最佳 Agent 模板

**核心文件：**
- `agent_system/capabilities.py` - 能力矩阵

**关键方法：**
```python
class CapabilityMatcher:
    def infer_capabilities_from_task(self, task_description: str) -> List[str]:
        """从任务描述推断所需能力"""
        
    def match_template(self, required_capabilities: List[str]) -> Optional[Dict]:
        """根据所需能力匹配最佳模板"""
        
    def merge_capabilities(self, capabilities: List[str]) -> Dict:
        """合并多个能力的配置"""
```

**扩展点：**
- 添加新的原子能力
- 添加新的 Agent 模板
- 优化能力推断算法

### 3. Agent Manager

**职责：** 管理 Agent 生命周期（创建、监控、优化、归档）

**核心文件：**
- `agent_system/agent_manager.py` - Agent 管理器（待实现）

**关键方法：**
```python
class AgentManager:
    def create_agent(self, template: str, task: Dict) -> Agent:
        """根据模板创建 Agent"""
        
    def list_agents(self) -> List[Agent]:
        """列出所有活跃 Agent"""
        
    def get_agent_status(self, agent_id: str) -> Dict:
        """查询 Agent 状态"""
        
    def archive_agent(self, agent_id: str):
        """归档闲置 Agent"""
        
    def optimize_agent(self, agent_id: str):
        """根据表现优化配置"""
```

**扩展点：**
- 自定义 Agent 模板
- 添加新的优化策略
- 实现 Agent 池管理

### 4. Learning Layer

**职责：** 从错误中学习，自动生成修复规则

**核心文件：**
- `agent_system/agent_learning.py` - 学习引擎

**关键方法：**
```python
class LearningEngine:
    def learn_from_error(self, error: Dict) -> Lesson:
        """从错误中学习"""
        
    def match_lesson(self, error: Dict) -> Optional[Lesson]:
        """匹配已有课程"""
        
    def apply_fix(self, lesson: Lesson) -> bool:
        """应用修复方案"""
```

**扩展点：**
- 添加新的错误签名
- 优化匹配算法
- 实现增量学习

### 5. Self-Healing Pipeline

**职责：** 自动检测和修复系统问题

**核心文件：**
- `reactor_auto_trigger.py` - 自动触发器
- `agent_system/agent_fallback.py` - 失败回退

**关键方法：**
```python
class SelfHealingPipeline:
    def run(self):
        """运行自愈流程"""
        sensors = self.collect_metrics()
        alerts = self.detect_anomalies(sensors)
        for alert in alerts:
            playbook = self.match_playbook(alert)
            result = self.execute_playbook(playbook)
            self.verify_result(result)
```

**扩展点：**
- 添加新的传感器
- 添加新的 Playbook
- 优化告警阈值

---

## 扩展指南

### 添加新的原子能力

**步骤：**

1. 在 `capabilities.py` 中定义能力：

```python
CAPABILITIES = {
    # 现有能力...
    
    # 新能力
    "api-design": Capability(
        name="api-design",
        description="API 设计、接口规范",
        tools=["read", "write", "web_search"],
        model="claude-opus-4-6",
        thinking="high",
        skills=[]
    ),
}
```

2. 在 `CapabilityMatcher.infer_capabilities_from_task` 中添加关键词映射：

```python
keyword_map = {
    # 现有映射...
    
    # 新映射
    "api-design": ["API 设计", "接口设计", "RESTful", "GraphQL", "api design"],
}
```

3. 测试能力推断：

```python
matcher = CapabilityMatcher()
task = "设计一个 RESTful API"
caps = matcher.infer_capabilities_from_task(task)
print(caps)  # 应包含 "api-design"
```

### 添加新的 Agent 模板

**步骤：**

1. 在 `capabilities.py` 中定义模板：

```python
TEMPLATES_V2 = {
    # 现有模板...
    
    # 新模板
    "api-designer": {
        "name": "API 设计师",
        "capabilities": ["api-design", "documentation", "code-review"],
        "description": "负责 API 设计、文档编写、接口审查"
    },
}
```

2. 测试模板匹配：

```python
matcher = CapabilityMatcher()
caps = ["api-design", "documentation"]
match = matcher.match_template(caps)
print(match['template_name'])  # 应为 "API 设计师"
```

3. 在 Dashboard 中添加图标（可选）：

```javascript
// dashboard/router_dashboard.py
const agentIcons = {
    // 现有图标...
    'api-designer': '🔌',
};
```

### 添加新的护栏

**步骤：**

1. 在 `production_router.py` 中添加护栏逻辑：

```python
class ProductionRouter:
    def route(self, ctx: TaskContext) -> Plan:
        # 现有护栏...
        
        # 新护栏：时间窗口限制
        if self._is_off_hours():
            reason_codes.append("off_hours_restriction")
            execution_mode = ExecutionMode.DRY_RUN  # 非工作时间只读
        
        # ...
    
    def _is_off_hours(self) -> bool:
        """判断是否非工作时间"""
        now = datetime.now()
        return now.hour < 9 or now.hour > 18
```

2. 添加配置选项：

```python
class ProductionRouter:
    def __init__(self, data_dir: str = "aios/data"):
        # 现有配置...
        
        # 新配置
        self.off_hours_enabled = True
        self.off_hours_start = 18
        self.off_hours_end = 9
```

3. 测试护栏：

```python
router = ProductionRouter()
ctx = TaskContext(
    task_id="task-001",
    description="删除生产数据",
    task_type=TaskType.DEPLOY,
    complexity=9,
    risk_level=RiskLevel.CRITICAL
)
plan = router.route(ctx)
print(plan.execution_mode)  # 非工作时间应为 DRY_RUN
```

### 自定义决策逻辑

**步骤：**

1. 继承 `SimpleRouter` 或 `ProductionRouter`：

```python
from aios.agent_system.simple_router import SimpleRouter

class CustomRouter(SimpleRouter):
    def route(self, ctx: TaskContext) -> Decision:
        # 自定义逻辑：优先使用本地模型
        if ctx.max_cost and ctx.max_cost < 1.0:
            return Decision(
                agent=self._select_agent(ctx),
                model="local-llama-3",  # 本地模型
                thinking="low",
                timeout=120,
                reason="成本限制，使用本地模型"
            )
        
        # 回退到默认逻辑
        return super().route(ctx)
```

2. 使用自定义路由器：

```python
router = CustomRouter()
ctx = UnifiedContext(
    task_id="task-001",
    description="简单查询",
    task_type=TaskType.ANALYZE,
    complexity=3,
    risk_level=RiskLevel.LOW,
    max_cost=0.5  # 低成本限制
)
plan = router.route(ctx)
print(plan.model)  # 应为 "local-llama-3"
```

---

## 贡献指南

### 代码规范

**Python 风格：**
- 遵循 PEP 8
- 使用 type hints
- 文档字符串（docstring）

**示例：**
```python
def route(self, ctx: UnifiedContext) -> UnifiedPlan:
    """
    统一路由入口
    
    Args:
        ctx: 任务上下文
        
    Returns:
        执行计划
        
    Raises:
        ValueError: 如果上下文无效
    """
    if not ctx.task_id:
        raise ValueError("task_id is required")
    
    # ...
```

**命名约定：**
- 类名：PascalCase（如 `UnifiedRouter`）
- 函数名：snake_case（如 `route_task`）
- 常量：UPPER_CASE（如 `MAX_RETRIES`）
- 私有方法：`_method_name`

### 提交流程

1. **Fork 仓库**

```bash
git clone https://github.com/your-username/aios.git
cd aios
```

2. **创建分支**

```bash
git checkout -b feature/add-new-capability
```

3. **编写代码**

```bash
# 添加新功能
vim aios/agent_system/capabilities.py

# 添加测试
vim aios/tests/test_capabilities.py
```

4. **运行测试**

```bash
# 运行所有测试
python -m pytest aios/tests/

# 运行特定测试
python -m pytest aios/tests/test_capabilities.py

# 检查代码风格
flake8 aios/
black aios/
```

5. **提交代码**

```bash
git add .
git commit -m "feat: add api-design capability"
```

**提交信息格式：**
- `feat:` - 新功能
- `fix:` - Bug 修复
- `docs:` - 文档更新
- `refactor:` - 代码重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

6. **推送分支**

```bash
git push origin feature/add-new-capability
```

7. **创建 Pull Request**

在 GitHub 上创建 PR，描述你的改动。

### 代码审查

**审查清单：**
- [ ] 代码符合 PEP 8 规范
- [ ] 添加了必要的测试
- [ ] 更新了相关文档
- [ ] 通过所有测试
- [ ] 无明显性能问题
- [ ] 无安全漏洞

---

## 测试指南

### 单元测试

**示例：测试 CapabilityMatcher**

```python
# aios/tests/test_capabilities.py

import pytest
from aios.agent_system.capabilities import CapabilityMatcher

def test_infer_capabilities():
    matcher = CapabilityMatcher()
    
    # 测试编码任务
    task = "实现用户登录功能"
    caps = matcher.infer_capabilities_from_task(task)
    assert "coding" in caps
    
    # 测试调试任务
    task = "修复支付接口 bug"
    caps = matcher.infer_capabilities_from_task(task)
    assert "debugging" in caps

def test_match_template():
    matcher = CapabilityMatcher()
    
    # 测试优化任务
    caps = ["coding", "debugging", "profiling", "optimization"]
    match = matcher.match_template(caps)
    assert match['template_id'] == "optimizer"
    assert match['match_score'] > 0.8

def test_merge_capabilities():
    matcher = CapabilityMatcher()
    
    # 测试能力合并
    caps = ["coding", "debugging"]
    config = matcher.merge_capabilities(caps)
    assert "exec" in config['tools']['allow']
    assert config['model'] == "claude-opus-4-6"
```

### 集成测试

**示例：测试 UnifiedRouter**

```python
# aios/tests/test_unified_router.py

import pytest
from aios.agent_system import UnifiedRouter, UnifiedContext, TaskType, RiskLevel

def test_simple_mode():
    router = UnifiedRouter(mode="simple")
    
    ctx = UnifiedContext(
        task_id="test-001",
        description="实现登录功能",
        task_type=TaskType.CODING,
        complexity=5,
        risk_level=RiskLevel.MEDIUM
    )
    
    plan = router.route(ctx)
    assert plan.agent_type == "coder"
    assert plan.model == "claude-opus-4-6"
    assert plan.mode_used == "simple"

def test_full_mode():
    router = UnifiedRouter(mode="full", data_dir="aios/data/test")
    
    ctx = UnifiedContext(
        task_id="test-002",
        description="修复支付 bug",
        task_type=TaskType.DEBUG,
        complexity=7,
        risk_level=RiskLevel.HIGH,
        error_rate=0.35
    )
    
    plan = router.route(ctx)
    assert plan.agent_type == "debugger"
    assert plan.confidence > 0.8
    assert plan.mode_used == "full"

def test_auto_mode():
    router = UnifiedRouter(mode="auto")
    
    ctx = UnifiedContext(
        task_id="test-003",
        description="优化性能",
        task_type=TaskType.OPTIMIZE,
        complexity=8,
        risk_level=RiskLevel.MEDIUM
    )
    
    plan = router.route(ctx)
    assert plan.agent_type in ["optimizer", "coder"]
    assert plan.mode_used in ["simple", "full"]
```

### 端到端测试

**示例：测试完整流程**

```python
# aios/tests/test_e2e.py

import pytest
from aios import AIOS
from aios.agent_system import UnifiedRouter

def test_full_workflow():
    # 初始化系统
    system = AIOS()
    router = UnifiedRouter(mode="auto")
    
    # 提交任务
    task = "优化数据库查询性能"
    ctx = system.analyze_task(task)
    
    # 路由决策
    plan = router.route(ctx)
    assert plan.agent_type == "optimizer"
    
    # 创建 Agent
    agent = system.spawn_agent(
        plan.agent_type,
        plan.model,
        plan.thinking_level
    )
    
    # 执行任务
    result = agent.execute(task, timeout=plan.timeout)
    assert result.success
    
    # 验证结果
    verified = system.verify_result(result)
    assert verified
    
    # 学习反馈
    system.learn_from_result(result)
```

### 运行测试

```bash
# 运行所有测试
python -m pytest aios/tests/

# 运行特定测试文件
python -m pytest aios/tests/test_capabilities.py

# 运行特定测试函数
python -m pytest aios/tests/test_capabilities.py::test_infer_capabilities

# 显示详细输出
python -m pytest aios/tests/ -v

# 显示覆盖率
python -m pytest aios/tests/ --cov=aios --cov-report=html
```

---

## 性能优化

### 1. 路由决策优化

**问题：** 决策延迟过高（> 100ms）

**优化方案：**

```python
# 使用缓存
from functools import lru_cache

class UnifiedRouter:
    @lru_cache(maxsize=128)
    def _get_capability_config(self, capability: str) -> Dict:
        """缓存能力配置"""
        return self.matcher.get_capability_info(capability)
    
    def route(self, ctx: UnifiedContext) -> UnifiedPlan:
        # 使用缓存的配置
        config = self._get_capability_config(ctx.task_type.value)
        # ...
```

### 2. 日志写入优化

**问题：** 频繁写入日志导致 I/O 瓶颈

**优化方案：**

```python
# 批量写入
class ProductionRouter:
    def __init__(self, data_dir: str = "aios/data"):
        self.decision_buffer = []
        self.buffer_size = 10
    
    def _log_decision(self, plan: Plan):
        self.decision_buffer.append(plan)
        if len(self.decision_buffer) >= self.buffer_size:
            self._flush_buffer()
    
    def _flush_buffer(self):
        with open(self.decision_log_file, 'a') as f:
            for plan in self.decision_buffer:
                f.write(json.dumps(asdict(plan)) + '\n')
        self.decision_buffer.clear()
```

### 3. Agent 池管理

**问题：** 频繁创建/销毁 Agent 导致开销大

**优化方案：**

```python
# Agent 池
class AgentPool:
    def __init__(self, max_size: int = 10):
        self.pool = {}
        self.max_size = max_size
    
    def get_agent(self, agent_type: str) -> Agent:
        if agent_type in self.pool:
            return self.pool[agent_type]
        
        if len(self.pool) >= self.max_size:
            # 移除最久未使用的 Agent
            oldest = min(self.pool.items(), key=lambda x: x[1].last_used)
            del self.pool[oldest[0]]
        
        agent = self._create_agent(agent_type)
        self.pool[agent_type] = agent
        return agent
```

### 4. 并行执行

**问题：** 多任务串行执行效率低

**优化方案：**

```python
import asyncio

class Orchestrator:
    async def parallel_execute(self, tasks: List[Task]) -> List[Result]:
        """并行执行多个任务"""
        coroutines = [self._execute_task(task) for task in tasks]
        results = await asyncio.gather(*coroutines)
        return results
    
    async def _execute_task(self, task: Task) -> Result:
        agent = self.get_agent(task.agent_type)
        result = await agent.execute_async(task)
        return result
```

### 5. 指标追踪优化

**问题：** 实时计算指标导致性能下降

**优化方案：**

```python
# 增量更新
class MetricsTracker:
    def __init__(self):
        self.total_decisions = 0
        self.total_confidence = 0.0
        self.opus_count = 0
        self.sonnet_count = 0
    
    def update(self, decision: Dict):
        """增量更新指标"""
        self.total_decisions += 1
        self.total_confidence += decision['confidence']
        
        if decision['model'] == 'opus-4-6':
            self.opus_count += 1
        else:
            self.sonnet_count += 1
    
    def get_stats(self) -> Dict:
        """O(1) 获取统计"""
        return {
            'total_decisions': self.total_decisions,
            'avg_confidence': self.total_confidence / self.total_decisions,
            'opus_usage': self.opus_count / self.total_decisions,
        }
```

---

## 总结

AIOS 是一个模块化、可扩展的 AI Agent 系统：

**核心组件：**
- UnifiedRouter - 智能路由决策
- CapabilityMatcher - 能力匹配
- Agent Manager - Agent 生命周期管理
- Learning Layer - 自动学习
- Self-Healing Pipeline - 自动修复

**扩展点：**
- 添加新的原子能力
- 添加新的 Agent 模板
- 添加新的护栏
- 自定义决策逻辑

**贡献流程：**
1. Fork 仓库
2. 创建分支
3. 编写代码和测试
4. 提交 PR
5. 代码审查

**性能优化：**
- 缓存配置
- 批量写入日志
- Agent 池管理
- 并行执行
- 增量更新指标

更多信息请参考：
- [UnifiedRouter Guide](UNIFIED_ROUTER_GUIDE.md) - 路由器使用指南
- [Dashboard Guide](../dashboard/DASHBOARD_GUIDE.md) - Dashboard 使用指南
- [README](../README.md) - 项目概览
