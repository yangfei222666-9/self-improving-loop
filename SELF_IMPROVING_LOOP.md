# Self-Improving Loop - 集成指南

## 概述

Self-Improving Loop 是一个统一的 Agent 自我改进闭环，自动嵌入到每个任务执行流程中。

## 完整闭环

```
执行任务 → 记录结果 → 分析失败模式 → 生成改进建议 → 自动应用 → 验证效果 → 更新配置
   ↑                                                                              ↓
   └──────────────────────────────────────────────────────────────────────────────┘
```

## 核心特性

1. **透明代理** - 不侵入现有代码，通过包装函数自动嵌入
2. **自动触发** - 失败达到阈值自动触发改进循环
3. **风险控制** - 只自动应用低风险改进，中高风险需人工审核
4. **冷却期** - 每个 Agent 6 小时内最多改进 1 次
5. **A/B 测试** - 自动验证改进效果，效果不佳自动回滚
6. **统一管理** - 所有 Agent 共享同一套改进逻辑

## 快速开始

### 1. 基础使用

```python
from aios.agent_system.self_improving_loop import SelfImprovingLoop

loop = SelfImprovingLoop()

# 包装任务执行
result = loop.execute_with_improvement(
    agent_id="coder-001",
    task="修复登录 bug",
    execute_fn=lambda: agent.run_task(task),
    context={"file": "auth.py", "line": 42}
)

print(f"成功: {result['success']}")
print(f"改进触发: {result['improvement_triggered']}")
print(f"改进应用: {result['improvement_applied']}")
```

### 2. 集成到现有 Agent

**方式 1：包装执行函数**

```python
class MyAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.loop = SelfImprovingLoop()
    
    def run_task(self, task):
        return self.loop.execute_with_improvement(
            agent_id=self.agent_id,
            task=task,
            execute_fn=lambda: self._do_task(task)
        )
    
    def _do_task(self, task):
        # 实际任务逻辑
        pass
```

**方式 2：装饰器模式**

```python
from functools import wraps

def with_self_improvement(agent_id):
    loop = SelfImprovingLoop()
    
    def decorator(func):
        @wraps(func)
        def wrapper(task, *args, **kwargs):
            return loop.execute_with_improvement(
                agent_id=agent_id,
                task=task,
                execute_fn=lambda: func(task, *args, **kwargs)
            )
        return wrapper
    return decorator

@with_self_improvement("coder-001")
def run_coding_task(task):
    # 任务逻辑
    pass
```

### 3. 集成到 Auto Dispatcher

```python
# auto_dispatcher.py

from self_improving_loop import SelfImprovingLoop

class AutoDispatcher:
    def __init__(self):
        self.loop = SelfImprovingLoop()
    
    def dispatch_task(self, agent_id, task):
        # 原有的任务分发逻辑
        def execute():
            return self._spawn_agent_and_run(agent_id, task)
        
        # 包装为自我改进循环
        return self.loop.execute_with_improvement(
            agent_id=agent_id,
            task=task,
            execute_fn=execute
        )
```

## 配置参数

在 `self_improving_loop.py` 中可调整：

```python
class SelfImprovingLoop:
    MIN_FAILURES_FOR_ANALYSIS = 3      # 最少失败次数才触发分析
    ANALYSIS_WINDOW_HOURS = 24         # 分析窗口（小时）
    IMPROVEMENT_COOLDOWN_HOURS = 6     # 改进冷却期（小时）
    AUTO_APPLY_RISK_LEVEL = "low"      # 自动应用的风险等级
```

## 改进类型

### 自动应用（低风险）

- 增加超时时间
- 添加重试机制
- 降低请求频率
- 调整 Agent 优先级

### 需要审核（中高风险）

- 内存优化
- 代码变更
- Agent 重启
- Prompt 大幅修改

## 监控和统计

### 查看单个 Agent 统计

```python
stats = loop.get_improvement_stats("coder-001")
print(stats)
# {
#   "agent_id": "coder-001",
#   "stats": {
#     "tasks_completed": 10,
#     "tasks_failed": 3,
#     "success_rate": 0.77
#   },
#   "last_improvement": "2026-02-24T16:30:00",
#   "cooldown_remaining_hours": 2.5
# }
```

### 查看全局统计

```python
stats = loop.get_improvement_stats()
print(stats)
# {
#   "total_agents": 5,
#   "total_improvements": 12,
#   "agents_improved": ["coder-001", "analyst-002", ...]
# }
```

## 日志和追踪

### 日志文件

- `aios/agent_system/data/loop.log` - 改进循环日志
- `aios/agent_system/data/traces/agent_traces.jsonl` - 任务追踪
- `aios/agent_system/data/fixes/fix_history.jsonl` - 修复历史

### 查看日志

```bash
# 查看最近的改进日志
tail -f aios/agent_system/data/loop.log

# 查看特定 Agent 的追踪
cat aios/agent_system/data/traces/agent_traces.jsonl | grep "coder-001"
```

## A/B 测试验证

改进应用后会自动启动 A/B 测试：

1. 记录改进前的基线（最近 10 次任务）
2. 应用改进
3. 记录改进后的表现（接下来 10 次任务）
4. 对比成功率、平均耗时
5. 如果效果变差，自动回滚

## 故障排查

### 改进未触发

检查：
1. 失败次数是否达到阈值（默认 3 次）
2. 是否在冷却期内（默认 6 小时）
3. 查看 `loop.log` 确认原因

### 改进应用失败

检查：
1. `fix_history.jsonl` 查看失败原因
2. 确认 Agent 配置文件权限
3. 确认改进类型是否支持

### 性能影响

- 追踪记录：~5ms 开销
- 失败分析：仅在触发时执行（~100ms）
- 改进应用：仅在触发时执行（~200ms）
- 总体影响：<1% 性能开销

## 最佳实践

1. **渐进式集成** - 先在 1-2 个 Agent 上测试，验证后再推广
2. **监控指标** - 定期查看改进统计，确认效果
3. **调整阈值** - 根据实际情况调整失败次数阈值和冷却期
4. **人工审核** - 定期查看中高风险改进建议，手动应用有价值的
5. **备份配置** - 改进前自动备份 Agent 配置，支持回滚

## 与现有模块的关系

```
SelfImprovingLoop (统一入口)
    ├── AgentTracer (追踪记录)
    ├── FailureAnalyzer (失败分析)
    ├── AgentAutoFixer (自动修复)
    ├── AutoEvolution (Prompt 进化)
    ├── EvolutionABTest (A/B 测试)
    └── AgentManager (配置管理)
```

所有现有模块保持独立可用，`SelfImprovingLoop` 作为统一编排层。

## 下一步

1. 在 `auto_dispatcher.py` 中集成 Self-Improving Loop
2. 在 `HEARTBEAT.md` 中添加定期检查改进统计
3. 创建 Dashboard 可视化改进历史
4. 添加 Telegram 通知（改进应用时推送）

## 示例：完整集成

```python
# 在 auto_dispatcher.py 中

from self_improving_loop import SelfImprovingLoop

class AutoDispatcher:
    def __init__(self):
        self.loop = SelfImprovingLoop()
        self.agent_manager = AgentManager()
    
    def process_heartbeat(self):
        """心跳处理（每次心跳调用）"""
        # 1. 处理任务队列
        tasks = self._load_task_queue()
        for task in tasks[:5]:  # 每次最多处理 5 个
            agent_id = self._route_task(task)
            
            # 2. 执行任务（自动嵌入改进循环）
            result = self.loop.execute_with_improvement(
                agent_id=agent_id,
                task=task["description"],
                execute_fn=lambda: self._spawn_and_run(agent_id, task)
            )
            
            # 3. 记录结果
            self._log_result(task, result)
            
            # 4. 如果触发了改进，通知用户
            if result["improvement_triggered"]:
                self._notify_improvement(agent_id, result["improvement_applied"])
    
    def _notify_improvement(self, agent_id, count):
        """通知改进应用"""
        message = f"🔧 Agent {agent_id} 自动应用了 {count} 项改进"
        # 发送 Telegram 通知
        print(message)
```

## 参考

- [agent_tracer.py](./agent_tracer.py) - 任务追踪
- [analyze_failures.py](./analyze_failures.py) - 失败分析
- [agent_auto_fixer.py](./agent_auto_fixer.py) - 自动修复
- [evolution_engine.py](./evolution_engine.py) - 进化引擎
