"""
Agent Evolution System - 使用文档

## 功能概述

Agent 进化系统让 Agent 通过实际使用不断优化自己的能力。

## 核心功能

### 1. 任务执行追踪
自动记录每次任务的成功/失败、耗时、错误信息。

### 2. 失败分析
分析失败模式，识别高频错误类型。

### 3. 改进建议生成
基于失败模式自动生成改进建议：
- Prompt 优化
- 工具权限调整
- 技能安装建议
- 参数调优

### 4. 进化历史
记录所有进化改进，支持回滚。

## 使用方法

### CLI 命令

```bash
# 分析 Agent 失败模式
python -m aios.agent_system.evolution analyze <agent_id>

# 生成进化报告
python -m aios.agent_system.evolution report <agent_id>

# 查看待审核建议
python -m aios.agent_system.evolution suggestions [agent_id]

# 查看进化历史
python -m aios.agent_system.evolution history <agent_id>
```

### Python API

```python
from aios.agent_system.evolution import AgentEvolution

evolution = AgentEvolution()

# 记录任务执行
evolution.log_task_execution(
    agent_id="coder-123456",
    task_type="code",
    success=False,
    duration_sec=45.2,
    error_msg="Timeout after 30s",
    context={"tools_used": ["exec", "write"]}
)

# 分析失败模式
analysis = evolution.analyze_failures("coder-123456", lookback_hours=24)
print(f"失败率: {analysis['failure_rate']:.1%}")
print(f"建议: {analysis['suggestions']}")

# 生成进化报告
report = evolution.generate_evolution_report("coder-123456")
print(report)

# 应用进化改进
evolution.apply_evolution(
    agent_id="coder-123456",
    evolution={
        "type": "prompt_update",
        "changes": {"thinking": "high"},
        "reason": "失败率过高，提升思考深度"
    }
)
```

## 数据文件

所有数据存储在 `aios/agent_system/data/evolution/`：

- `task_executions.jsonl` - 任务执行日志
- `improvement_suggestions.jsonl` - 改进建议
- `evolution_history.jsonl` - 进化历史

## 进化触发条件

系统会在以下情况自动生成建议：

1. **失败率 > 30%** → 建议提升 thinking level
2. **同类任务失败 ≥ 3 次** → 建议添加技能或调整工具
3. **检测到超时错误** → 建议增加超时时间
4. **检测到权限错误** → 建议检查工具权限
5. **检测到 API 限流** → 建议添加重试机制

## 进化类型

- `prompt_update` - System prompt 优化
- `tool_permission` - 工具权限调整
- `skill_install` - 技能安装
- `parameter_tune` - 参数调优（thinking/model/timeout）

## 审核流程

1. 系统生成建议 → `status: pending`
2. 人工审核 → `status: approved` 或 `rejected`
3. 应用改进 → `status: applied`
4. 记录到进化历史

## 示例场景

### 场景 1：Coder Agent 频繁超时

```bash
# 分析失败
$ python -m aios.agent_system.evolution analyze coder-123456

{
  "total_tasks": 10,
  "failed_tasks": 4,
  "failure_rate": 0.4,
  "failure_patterns": {
    "code": {
      "count": 4,
      "errors": ["Timeout after 30s", "Timeout after 30s", ...]
    }
  },
  "suggestions": [
    "失败率过高（>30%），建议提升 thinking level 到 'medium' 或 'high'",
    "检测到超时错误，建议增加任务超时时间"
  ]
}
```

### 场景 2：Analyst Agent 缺少工具权限

```bash
# 生成报告
$ python -m aios.agent_system.evolution report analyst-688334

# Agent analyst-688334 进化报告

**生成时间：** 2026-02-24 01:40:00

## 📊 性能分析（最近24小时）

- 总任务数：8
- 失败任务数：3
- 失败率：37.5%

## ⚠️ 失败模式

- **analysis**：失败 3 次

## 💡 改进建议

1. 失败率过高（>30%），建议提升 thinking level 到 'medium' 或 'high'
2. analysis 任务失败 3 次，建议：
3.   - 添加数据分析相关技能
4.   - 确保 'web_search', 'web_fetch' 工具权限
```

## 下一步

Phase 2 将实现：
- 自动应用低风险改进（无需人工审核）
- A/B 测试（新旧版本对比）
- 多 Agent 协同学习（共享经验）
