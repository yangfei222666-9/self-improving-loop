# AIOS Agent System 使用指南

## 快速开始

### 1. 命令行使用

```bash
# 查看系统状态
python -m aios.agent_system status

# 列出所有 Agent
python -m aios.agent_system list

# 列出特定类型的 Agent
python -m aios.agent_system list coder

# 手动创建 Agent
python -m aios.agent_system create coder

# 测试任务路由（不自动创建）
python -m aios.agent_system route "帮我写一个 Python 爬虫"

# 清理闲置 Agent（默认 24 小时）
python -m aios.agent_system cleanup
python -m aios.agent_system cleanup 48
```

### 2. Python API 使用

```python
from aios.agent_system import AgentSystem

# 初始化系统
system = AgentSystem()

# 处理任务（自动创建或分配 Agent）
result = system.handle_task("帮我写一个 Python 爬虫", auto_create=True)
print(result)
# {
#   'status': 'success',
#   'action': 'created',  # 或 'assigned'
#   'agent_id': 'coder-001',
#   'agent_name': '代码开发专员',
#   'task_analysis': {...},
#   'message': '已创建新 Agent: 代码开发专员 (coder-001)'
# }

# 报告任务结果（更新统计）
system.report_task_result(
    agent_id='coder-001',
    success=True,
    duration_sec=45.2
)

# 获取系统状态
status = system.get_status()
print(status)

# 列出 Agent
agents = system.list_agents(template='coder', status='active')

# 获取 Agent 详情
agent = system.get_agent_detail('coder-001')

# 清理闲置 Agent
archived = system.cleanup_idle_agents(idle_hours=24)
```

## Agent 模板

系统内置 4 种 Agent 模板：

### 1. coder - 代码开发专员
- **触发关键词**: 写代码、编写、实现、开发、调试、bug、重构、函数、类、模块、API、测试、爬虫、脚本
- **模型**: claude-opus-4-6
- **技能**: coding-agent, github
- **适用场景**: 编写代码、调试、重构、优化

### 2. analyst - 数据分析专员
- **触发关键词**: 分析、统计、数据、趋势、模式、报告、总结、对比、评估
- **模型**: claude-sonnet-4-5
- **适用场景**: 数据分析、统计报告、趋势预测

### 3. monitor - 系统监控专员
- **触发关键词**: 监控、检查、状态、健康、性能、资源、CPU、内存、磁盘、进程、服务
- **模型**: claude-sonnet-4-5
- **技能**: system-resource-monitor
- **适用场景**: 系统健康检查、性能监控、异常告警

### 4. researcher - 信息研究专员
- **触发关键词**: 搜索、查找、研究、资料、信息、文档、什么是、如何、为什么
- **模型**: claude-sonnet-4-5
- **适用场景**: 信息搜索、资料整理、知识总结

## 任务路由逻辑

1. **任务分析**: 根据关键词匹配任务类型和复杂度
2. **Agent 匹配**: 查找相同模板的活跃 Agent
3. **自动创建**: 如果没有合适的 Agent，自动创建新的
4. **负载均衡**: 优先分配给最近最少使用的 Agent

## 配置

### 任务分类规则
位置: `aios/agent_system/config/task_rules.json`

可以自定义：
- 任务类型和关键词
- 复杂度指标
- 自动创建规则

### Agent 模板
位置: `aios/agent_system/templates/templates.json`

可以自定义：
- Agent 名称和描述
- 技能和工具权限
- 系统提示词
- 默认模型

## 数据存储

- **Agent 配置**: `~/.openclaw/workspace/aios/agent_system/data/agents.jsonl`
- **系统日志**: `~/.openclaw/workspace/aios/agent_system/data/system.log`

## 示例场景

### 场景 1: 代码开发
```python
system = AgentSystem()

# 第一次：创建 coder Agent
result1 = system.handle_task("写一个 Python 爬虫")
# action: 'created', agent_id: 'coder-001'

# 第二次：复用现有 coder Agent
result2 = system.handle_task("调试这段代码")
# action: 'assigned', agent_id: 'coder-001'

# 报告结果
system.report_task_result('coder-001', success=True, duration_sec=120)
```

### 场景 2: 多类型任务
```python
system = AgentSystem()

# 代码任务 → coder Agent
system.handle_task("实现一个 REST API")

# 分析任务 → analyst Agent
system.handle_task("分析最近的用户数据")

# 监控任务 → monitor Agent
system.handle_task("检查服务器状态")

# 查看所有 Agent
status = system.get_status()
# {
#   'total_active': 3,
#   'active_agents_by_template': {
#     'coder': [...],
#     'analyst': [...],
#     'monitor': [...]
#   }
# }
```

### 场景 3: 定期清理
```python
system = AgentSystem()

# 清理 24 小时未使用的 Agent
archived = system.cleanup_idle_agents(idle_hours=24)
print(f"Archived {len(archived)} agents")
```

## 集成到 OpenClaw

在 OpenClaw 主会话中使用：

```python
# 在 HEARTBEAT.md 或其他地方调用
from aios.agent_system import AgentSystem

system = AgentSystem()

# 收到用户消息时
user_message = "帮我写一个爬虫"
result = system.handle_task(user_message)

if result['status'] == 'success':
    agent_id = result['agent_id']
    # 使用 sessions_spawn 创建子 Agent 会话
    # 或者直接在当前会话处理
```

## 未来扩展

- [ ] 与 OpenClaw sessions_spawn 集成
- [ ] Agent 性能自动优化
- [ ] 任务队列和并行执行
- [ ] Dashboard 可视化
- [ ] 更智能的任务拆解和协作
