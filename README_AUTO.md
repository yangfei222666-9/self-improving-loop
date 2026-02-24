# AIOS Agent System - 自动化部署

## 三种自动化方式

### 1. 心跳集成（Heartbeat）
**触发频率**: 每次心跳（约 30 分钟）

**功能**:
- 处理任务队列（最多 5 个任务/次）
- 自动路由到合适的 Agent
- 监控 Agent 健康状态

**实现**:
```bash
# HEARTBEAT.md 已添加
& "C:\Program Files\Python312\python.exe" C:\Users\A\.openclaw\workspace\aios\agent_system\auto_dispatcher.py heartbeat
```

**适用场景**:
- 响应式任务（文件变化、告警触发）
- 需要快速处理的任务
- 队列积压清理

---

### 2. 事件驱动（Event-Driven）
**触发频率**: 实时（事件发生时）

**功能**:
- 文件变化 → 自动触发 coder Agent
- 系统告警 → 自动触发 monitor Agent  
- 新数据到达 → 自动触发 analyst Agent

**实现**:
```python
# auto_dispatcher.py 已订阅 EventBus
dispatcher = AutoDispatcher(workspace)
# 自动订阅：sensor.file.*, alert.*, sensor.data.*
```

**适用场景**:
- 代码文件修改后自动测试
- 系统告警自动诊断
- 数据到达自动分析

---

### 3. 定时任务（Cron）
**触发频率**: 每天 9:00 AM

**功能**:
- 每日代码审查
- 每周性能报告
- 每小时待办检查

**实现**:
```bash
# Cron job 已创建（ID: 3e6ae359-c131-468f-af72-2ec9bdf20136）
# 每天 9:00 触发
& "C:\Program Files\Python312\python.exe" C:\Users\A\.openclaw\workspace\aios\agent_system\auto_dispatcher.py cron
```

**适用场景**:
- 周期性报告生成
- 定期健康检查
- 计划性任务

---

## 任务流程

```
事件发生 → 入队 (task_queue.jsonl)
    ↓
心跳处理 → 路由到 Agent
    ↓
Agent 执行 → 结果记录
    ↓
失败重试 / 成功归档
```

---

## 监控命令

### 查看队列状态
```bash
& "C:\Program Files\Python312\python.exe" C:\Users\A\.openclaw\workspace\aios\agent_system\auto_dispatcher.py status
```

### 手动触发心跳处理
```bash
& "C:\Program Files\Python312\python.exe" C:\Users\A\.openclaw\workspace\aios\agent_system\auto_dispatcher.py heartbeat
```

### 手动触发定时任务
```bash
& "C:\Program Files\Python312\python.exe" C:\Users\A\.openclaw\workspace\aios\agent_system\auto_dispatcher.py cron
```

---

## 配置文件

- **任务队列**: `aios/agent_system/task_queue.jsonl`
- **调度状态**: `memory/agent_dispatch_state.json`
- **Agent 注册**: `aios/agent_system/agents.jsonl`

---

## 任务优先级

- **high**: 立即处理（告警、测试失败）
- **normal**: 正常处理（代码审查、数据分析）
- **low**: 低优先级（待办检查、日常巡检）

---

## 扩展方式

### 添加新的事件订阅
编辑 `auto_dispatcher.py` 的 `_subscribe_events()` 方法：

```python
self.event_bus.subscribe("your.event.*", self._on_your_event)
```

### 添加新的定时任务
编辑 `auto_dispatcher.py` 的 `check_scheduled_tasks()` 方法：

```python
if self._should_run(state, "your_task", hours=24):
    self.enqueue_task({
        "type": "code",
        "message": "你的任务描述",
        "priority": "normal",
        "source": "cron_daily"
    })
```

---

## 部署状态

✅ **心跳集成**: 已添加到 HEARTBEAT.md  
✅ **事件驱动**: EventBus 订阅已配置  
✅ **定时任务**: Cron job 已创建（每天 9:00）

**下次心跳时自动生效**
