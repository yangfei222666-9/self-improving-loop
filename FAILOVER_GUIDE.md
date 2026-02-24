# Agent Spawner with Failover - 集成指南

## 概述

Agent Spawner with Failover 为 OpenClaw 的 `sessions_spawn` 提供容灾机制：
- **Provider Failover** - 自动切换到备用模型
- **重试机制** - 指数退避重试（1s, 2s, 4s）
- **熔断器** - 连续失败 3 次自动熔断 5 分钟
- **DLQ** - 失败任务进入死信队列

## 快速开始

### 1. 在主 Agent 中使用

```python
from agent_system.spawner_with_failover import create_spawner_with_failover

# 创建带 Failover 的 Spawner
spawner = create_spawner_with_failover(sessions_spawn)

# 使用（会自动 Failover）
result = spawner.spawn_with_failover(
    task="帮我写一个 Python 爬虫",
    label="coder-task-123",
    model="claude-sonnet-4-6"  # 如果失败会自动切换到 Opus 或 Haiku
)

# 检查结果
if result['status'] == 'spawned':
    print(f"✅ Agent 创建成功: {result['sessionKey']}")
    print(f"使用的模型: {result['provider']}")
else:
    print(f"❌ 创建失败: {result['error']}")
    if result.get('dlq'):
        print(f"任务已进入 DLQ: {result['task_id']}")
```

### 2. 在 auto_dispatcher.py 中集成

修改 `auto_dispatcher.py` 的 Agent 创建部分：

```python
# 旧代码（无容灾）
result = sessions_spawn(
    task=task_desc,
    label=label,
    model=model
)

# 新代码（有容灾）
from agent_system.spawner_with_failover import create_spawner_with_failover

spawner = create_spawner_with_failover(sessions_spawn)
result = spawner.spawn_with_failover(
    task=task_desc,
    label=label,
    model=model
)
```

## Failover 流程

```
1. 尝试 claude-sonnet-4-6 (3 次重试)
   ↓ 失败
2. 尝试 claude-opus-4-6 (3 次重试)
   ↓ 失败
3. 尝试 claude-haiku-4-5 (3 次重试)
   ↓ 失败
4. 进入 DLQ（可手动重试）
```

## 熔断器

- **触发条件：** 连续失败 3 次
- **熔断时间：** 5 分钟
- **恢复机制：** 5 分钟后进入半开状态，成功一次即关闭

## DLQ（死信队列）

失败任务会自动进入 DLQ：

```python
from core.provider_manager import get_provider_manager

manager = get_provider_manager()

# 查看 DLQ
tasks = manager.get_dlq_tasks()
for task in tasks:
    print(f"任务 {task.id}: {task.error}")

# 手动重试
result = manager.retry_dlq_task(task_id, execute_fn)
```

## 配置

Provider 配置文件：`aios/data/provider_config.json`

```json
[
  {
    "name": "claude-sonnet-4-6",
    "priority": 1,
    "max_retries": 3,
    "timeout_sec": 30,
    "enabled": true
  },
  {
    "name": "claude-opus-4-6",
    "priority": 2,
    "max_retries": 3,
    "timeout_sec": 30,
    "enabled": true
  },
  {
    "name": "claude-haiku-4-5",
    "priority": 3,
    "max_retries": 3,
    "timeout_sec": 30,
    "enabled": true
  }
]
```

## 监控

查看容灾状态：

```python
from core.provider_manager import get_provider_manager

manager = get_provider_manager()

# 熔断器状态
for provider, cb in manager.circuit_breakers.items():
    print(f"{provider}: {cb['state']} (失败次数: {cb['failure_count']})")

# DLQ 大小
dlq_size = len(manager.get_dlq_tasks())
print(f"DLQ 中的任务数: {dlq_size}")
```

## 注意事项

1. **模型名称必须匹配** - Provider 配置中的 `name` 必须是 OpenClaw 支持的模型名
2. **优先级顺序** - 数字越小优先级越高（1 > 2 > 3）
3. **熔断器全局共享** - 所有 Agent 创建共享同一个熔断器状态
4. **DLQ 需要定期清理** - 建议在心跳任务中自动重试 DLQ

## 测试

运行测试脚本：

```bash
python aios/agent_system/spawner_with_failover.py
```

## 故障排查

### 问题：所有 Provider 都熔断了

**原因：** 上游服务持续不可用

**解决：**
1. 等待 5 分钟自动恢复
2. 或手动重置熔断器：
   ```python
   manager.circuit_breakers.clear()
   ```

### 问题：DLQ 堆积过多

**原因：** 失败任务没有自动重试

**解决：**
1. 在心跳任务中添加 DLQ 自动重试
2. 或手动批量重试：
   ```python
   for task in manager.get_dlq_tasks():
       manager.retry_dlq_task(task.id, execute_fn)
   ```

## 下一步

- [ ] 集成到 auto_dispatcher.py
- [ ] 添加 DLQ 自动重试到心跳任务
- [ ] 添加熔断器告警（Telegram 通知）
- [ ] Dashboard 展示容灾状态
