"""
Agent Auto Evolution - 使用文档

## Phase 2：自动进化

让 Agent 自动应用低风险改进，无需人工审核。

## 核心功能

### 1. 进化策略库
预定义的进化策略，包含触发条件、执行动作、风险等级。

### 2. 自动触发
系统自动检测失败模式，匹配策略，生成进化计划。

### 3. 风险分级
- **low** - 自动应用（如提升 thinking level）
- **medium** - 需要人工审核（如调整工具权限）
- **high** - 必须人工审核（如修改 system prompt）

### 4. 自动回滚
如果进化后表现变差（成功率下降 > 10%），自动回滚。

## 使用方法

### CLI 命令

```bash
# 自动进化 Agent
python -m aios.agent_system.auto_evolution evolve <agent_id>

# 查看策略库
python -m aios.agent_system.auto_evolution strategies
```

### Python API

```python
from aios.agent_system.auto_evolution import AutoEvolution
from aios.agent_system.core.agent_manager import AgentManager

auto_evolution = AutoEvolution()
agent_manager = AgentManager()

# 自动进化
result = auto_evolution.auto_evolve("coder-123456", agent_manager)

if result["status"] == "applied":
    print(f"✅ {result['message']}")
    for plan in result["plans"]:
        print(f"  - {plan['description']}")
        print(f"    变更: {plan['changes']}")
elif result["status"] == "pending_review":
    print("⏳ 需要人工审核")
else:
    print(f"⏭️ {result['reason']}")
```

## 进化策略

### 1. high_failure_rate
- **触发条件**：失败率 > 30%
- **执行动作**：提升 thinking level
- **风险等级**：low
- **自动应用**：是

### 2. timeout_errors
- **触发条件**：超时错误 ≥ 3 次
- **执行动作**：增加超时时间
- **风险等级**：low
- **自动应用**：是

### 3. permission_errors
- **触发条件**：权限错误 ≥ 3 次
- **执行动作**：调整工具权限
- **风险等级**：medium
- **自动应用**：否（需审核）

### 4. rate_limit_errors
- **触发条件**：API 限流错误 ≥ 3 次
- **执行动作**：添加重试机制
- **风险等级**：low
- **自动应用**：是

### 5. task_type_failure
- **触发条件**：特定任务类型失败 ≥ 3 次
- **执行动作**：安装相关技能
- **风险等级**：medium
- **自动应用**：否（需审核）

## 进化流程

```
1. 分析失败模式
   ↓
2. 评估触发条件
   ↓
3. 匹配进化策略
   ↓
4. 生成进化计划
   ↓
5. 风险评估
   ↓
6a. 低风险 → 自动应用
6b. 中高风险 → 人工审核
   ↓
7. 记录进化历史
   ↓
8. 监控进化效果
   ↓
9a. 效果好 → 保留
9b. 效果差 → 自动回滚
```

## 示例场景

### 场景 1：Coder Agent 频繁超时

```bash
$ python -m aios.agent_system.auto_evolution evolve coder-123456

{
  "status": "applied",
  "plans": [
    {
      "action": "increase_thinking",
      "description": "失败率过高，提升思考深度",
      "changes": {"thinking": "medium"},
      "rollback": {"thinking": "low"}
    },
    {
      "action": "increase_timeout",
      "description": "频繁超时，增加超时时间",
      "changes": {"timeout_sec": 60},
      "rollback": {"timeout_sec": 30}
    }
  ],
  "message": "已自动应用 2 个进化改进"
}
```

### 场景 2：需要人工审核

```bash
$ python -m aios.agent_system.auto_evolution evolve analyst-688334

{
  "status": "pending_review",
  "strategies": [
    {
      "name": "permission_errors",
      "strategy": {
        "action": "adjust_tools",
        "risk": "medium",
        "auto_apply": false
      },
      "reason": "检测到 3 次 'permission' 错误"
    }
  ],
  "reason": "所有匹配策略需要人工审核"
}
```

## 自动回滚

系统会在进化后持续监控 Agent 表现：

```python
# 进化前成功率：60%
# 进化后成功率：45%（下降 15%）

result = auto_evolution.check_evolution_result(
    agent_id="coder-123456",
    before_score=0.6,
    after_score=0.45
)

# result = {
#     "improved": False,
#     "delta": -0.15,
#     "action": "rollback",
#     "message": "进化失败！成功率下降 15.0%，建议回滚"
# }
```

## 定时任务

建议每天自动运行一次：

```bash
# 添加到 HEARTBEAT.md
python -m aios.agent_system.auto_evolution evolve <agent_id>
```

或者在 Agent 失败率超过阈值时立即触发。

## 下一步（Phase 3）

- 多 Agent 协同学习（共享经验）
- 元学习（学习如何学习）
- 自主探索（主动尝试新方法）
- Prompt 自动优化（基于成功案例）
