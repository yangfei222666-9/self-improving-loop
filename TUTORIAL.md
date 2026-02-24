# Tutorial - Self-Improving Loop 完整教程

欢迎使用 Self-Improving Loop！这个教程会带你从零开始，5 分钟上手，然后深入了解核心概念和高级用法。

## 📚 目录

- [快速开始（5分钟）](#快速开始5分钟)
- [核心概念](#核心概念)
- [基础用法](#基础用法)
- [高级用法](#高级用法)
- [最佳实践](#最佳实践)
- [常见问题 FAQ](#常见问题-faq)

---

## 快速开始（5分钟）

### 1. 安装

```bash
git clone https://github.com/yangfei222666-9/self-improving-loop.git
cd self-improving-loop
pip install -e .
```

### 2. 第一个例子

创建 `hello.py`：

```python
from self_improving_loop import SelfImprovingLoop

# 创建循环
loop = SelfImprovingLoop()

# 包装你的任务
def my_task():
    print("Hello, Self-Improving Loop!")
    return {"status": "success"}

# 执行任务（自动追踪 + 改进）
result = loop.execute_with_improvement(
    agent_id="hello-agent",
    task="打招呼",
    execute_fn=my_task
)

print(f"成功: {result['success']}")
print(f"耗时: {result['duration_sec']:.2f}s")
```

运行：
```bash
python hello.py
```

输出：
```
Hello, Self-Improving Loop!
成功: True
耗时: 0.00s
```

**恭喜！** 你已经完成了第一个 Self-Improving Loop 程序。

---

## 核心概念

### 什么是 Self-Improving Loop？

Self-Improving Loop 是一个让 AI Agent 自动进化的系统。它会：

1. **追踪**每个任务的执行过程
2. **分析**失败模式
3. **生成**改进建议
4. **自动应用**低风险改进
5. **验证**改进效果
6. **回滚**效果变差的改进

### 7 步闭环

```
┌─────────────────────────────────────────────────────────┐
│                  Self-Improving Loop                     │
│                                                          │
│  1. Execute Task    → 执行任务（透明代理）               │
│  2. Record Result   → 记录结果（Tracer）                 │
│  3. Analyze Failure → 分析失败模式                       │
│  4. Generate Fix    → 生成改进建议                       │
│  5. Auto Apply      → 自动应用低风险改进                 │
│  6. Verify Effect   → 验证效果                           │
│  7. Update Config   → 更新配置 + 自动回滚                │
└─────────────────────────────────────────────────────────┘
```

### 核心组件

- **SelfImprovingLoop**: 主引擎，协调所有组件
- **AgentTracer**: 任务追踪器，记录执行细节
- **AutoRollback**: 自动回滚，效果变差时恢复
- **AdaptiveThreshold**: 自适应阈值，根据 Agent 特性调整
- **Notifier**: 通知系统，可插拔的通知接口

---

## 基础用法

### 1. 追踪任务执行

```python
from self_improving_loop import SelfImprovingLoop

loop = SelfImprovingLoop(data_dir="./my_data")

def process_data(data):
    # 你的业务逻辑
    result = data * 2
    return result

result = loop.execute_with_improvement(
    agent_id="data-processor",
    task="处理数据",
    execute_fn=lambda: process_data(42),
    context={"input": 42}  # 可选：任务上下文
)

print(result)
# {
#     "success": True,
#     "result": 84,
#     "error": None,
#     "duration_sec": 0.001,
#     "improvement_triggered": False,
#     "improvement_applied": 0,
#     "rollback_executed": None
# }
```

### 2. 处理失败

```python
def risky_task():
    import random
    if random.random() < 0.3:  # 30% 失败率
        raise Exception("网络超时")
    return {"status": "ok"}

# 执行多次，观察改进触发
for i in range(10):
    result = loop.execute_with_improvement(
        agent_id="risky-agent",
        task=f"任务 {i+1}",
        execute_fn=risky_task
    )
    
    if result["improvement_triggered"]:
        print(f"第 {i+1} 次失败后触发改进！")
        print(f"应用了 {result['improvement_applied']} 项改进")
```

### 3. 查看统计

```python
# 单个 Agent 统计
stats = loop.get_improvement_stats("risky-agent")
print(stats)
# {
#     "agent_id": "risky-agent",
#     "agent_stats": {
#         "tasks_completed": 7,
#         "tasks_failed": 3,
#         "success_rate": 0.7
#     },
#     "last_improvement": "2026-02-24T18:00:00",
#     "cooldown_remaining_hours": 3.5
# }

# 全局统计
global_stats = loop.get_improvement_stats()
print(global_stats)
# {
#     "total_agents": 2,
#     "total_improvements": 1,
#     "agents_improved": ["risky-agent"]
# }
```

---

## 高级用法

### 1. 集成到 Agent 类

```python
from self_improving_loop import SelfImprovingLoop

class MyAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.loop = SelfImprovingLoop()
    
    def run(self, task, **kwargs):
        """执行任务（自动改进）"""
        return self.loop.execute_with_improvement(
            agent_id=self.agent_id,
            task=task,
            execute_fn=lambda: self._execute(task, **kwargs),
            context=kwargs
        )
    
    def _execute(self, task, **kwargs):
        """实际执行逻辑"""
        # 你的 Agent 逻辑
        if "error" in task:
            raise RuntimeError(f"执行失败: {task}")
        return {"done": True, "task": task}

# 使用
agent = MyAgent("my-agent-001")

result = agent.run("正常任务")
print(result["success"])  # True

result = agent.run("error 任务")
print(result["success"])  # False
print(result["error"])    # "执行失败: error 任务"
```

### 2. 自定义通知器

```python
from self_improving_loop import SelfImprovingLoop
from self_improving_loop.notifier import Notifier

class SlackNotifier(Notifier):
    def __init__(self, webhook_url):
        super().__init__(enabled=True)
        self.webhook_url = webhook_url
    
    def notify_improvement(self, agent_id, improvements_applied, details=None):
        # 发送到 Slack
        message = f"🔧 Agent {agent_id} 应用了 {improvements_applied} 项改进"
        self._send_to_slack(message)
    
    def notify_rollback(self, agent_id, reason, metrics=None):
        # 发送告警到 Slack
        message = f"⚠️ Agent {agent_id} 回滚: {reason}"
        self._send_to_slack(message)
    
    def _send_to_slack(self, message):
        import requests
        requests.post(self.webhook_url, json={"text": message})

# 使用自定义通知器
notifier = SlackNotifier("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
loop = SelfImprovingLoop(notifier=notifier)
```

### 3. 自适应阈值配置

```python
from self_improving_loop import AdaptiveThreshold

at = AdaptiveThreshold()

# 查看默认阈值
threshold, window, cooldown = at.get_threshold("normal-agent", [])
print(f"阈值: {threshold}, 窗口: {window}h, 冷却: {cooldown}h")
# 阈值: 3, 窗口: 24h, 冷却: 6h

# 关键 Agent（名称包含 critical/monitor/prod）
threshold, window, cooldown = at.get_threshold("prod-monitor", [])
print(f"关键 Agent 阈值: {threshold}")
# 关键 Agent 阈值: 1

# 手动配置
at.set_manual_threshold(
    "special-agent",
    failure_threshold=10,
    analysis_window_hours=48,
    cooldown_hours=1,
    is_critical=False
)

# 查看完整配置
profile = at.get_agent_profile("special-agent", [])
print(profile)
# {
#     "agent_id": "special-agent",
#     "frequency": "medium",
#     "is_critical": False,
#     "failure_threshold": 10,
#     "analysis_window_hours": 48,
#     "cooldown_hours": 1,
#     "tasks_per_day": 0,
#     "source": "manual"
# }
```

### 4. 手动分析追踪数据

```python
from self_improving_loop import TraceAnalyzer

analyzer = TraceAnalyzer(trace_dir="./my_data/traces")

# 获取失败模式
patterns = analyzer.get_failure_patterns(min_occurrences=3)
for pattern in patterns:
    print(f"错误签名: {pattern['error_signature']}")
    print(f"出现次数: {pattern['occurrences']}")
    print(f"影响 Agent: {pattern['affected_agents']}")
    print()

# 获取 Agent 统计
stats = analyzer.get_agent_stats("my-agent")
print(f"总任务: {stats['total_tasks']}")
print(f"成功率: {stats['success_rate']:.1%}")
print(f"平均耗时: {stats['avg_duration_sec']:.2f}s")

# 获取最近的追踪
recent = analyzer.get_recent_traces(agent_id="my-agent", hours=24)
print(f"最近 24h 执行了 {len(recent)} 个任务")
```

### 5. 手动回滚

```python
from self_improving_loop import AutoRollback

rollback = AutoRollback(data_dir="./my_data/rollback")

# 备份配置
config = {"timeout": 30, "retry": 3}
backup_id = rollback.backup_config("my-agent", config, "improvement_001")
print(f"备份 ID: {backup_id}")

# 判断是否需要回滚
before = {"success_rate": 0.80, "avg_duration_sec": 10.0}
after = {"success_rate": 0.65, "avg_duration_sec": 12.0}

should, reason = rollback.should_rollback("my-agent", "improvement_001", before, after)
if should:
    print(f"需要回滚: {reason}")
    result = rollback.rollback("my-agent", backup_id)
    if result["success"]:
        print("回滚成功")

# 查看回滚历史
history = rollback.get_rollback_history("my-agent")
print(f"回滚次数: {len(history)}")
```

---

## 最佳实践

### 1. 数据目录管理

```python
# 推荐：为每个项目使用独立的数据目录
loop = SelfImprovingLoop(data_dir="./project_data")

# 数据目录结构：
# project_data/
# ├── traces/              # 任务追踪
# │   └── agent_traces.jsonl
# ├── rollback/            # 回滚备份
# │   ├── config_backups.jsonl
# │   └── rollback_history.jsonl
# ├── agent_configs.json   # Agent 配置
# ├── adaptive_thresholds.json  # 阈值配置
# ├── loop_state.json      # 循环状态
# └── loop.log             # 日志
```

### 2. Agent ID 命名规范

```python
# 推荐：使用有意义的 ID
loop.execute_with_improvement(
    agent_id="coder-backend-api",  # ✅ 清晰
    # agent_id="agent-001",        # ❌ 不清晰
    task="修复登录 bug",
    execute_fn=fix_login_bug
)

# 关键 Agent 使用特殊前缀
loop.execute_with_improvement(
    agent_id="prod-monitor-database",  # 自动识别为关键 Agent
    task="监控数据库",
    execute_fn=monitor_db
)
```

### 3. 错误处理

```python
def safe_execute(task_fn):
    """安全执行，捕获所有异常"""
    try:
        return task_fn()
    except Exception as e:
        # 记录详细错误信息
        import traceback
        error_detail = traceback.format_exc()
        raise Exception(f"{str(e)}\n\n{error_detail}")

result = loop.execute_with_improvement(
    agent_id="my-agent",
    task="执行任务",
    execute_fn=lambda: safe_execute(my_task)
)
```

### 4. 性能优化

```python
# 对于高频任务，使用更高的失败阈值
from self_improving_loop import AdaptiveThreshold

at = AdaptiveThreshold()
at.set_manual_threshold(
    "high-freq-agent",
    failure_threshold=10,  # 更高的阈值
    cooldown_hours=1       # 更短的冷却期
)

# 在 SelfImprovingLoop 中使用
loop = SelfImprovingLoop()
loop.adaptive_threshold = at
```

### 5. 测试环境隔离

```python
import tempfile
import shutil

# 测试时使用临时目录
test_dir = tempfile.mkdtemp(prefix="test_loop_")
try:
    loop = SelfImprovingLoop(data_dir=test_dir)
    # 运行测试...
finally:
    shutil.rmtree(test_dir)  # 清理
```

---

## 常见问题 FAQ

### Q1: 什么时候会触发改进？

**A:** 当 Agent 在指定时间窗口内失败次数达到阈值时触发。默认：
- 失败阈值：3 次
- 时间窗口：24 小时
- 冷却期：6 小时

可以通过 `AdaptiveThreshold` 自定义。

### Q2: 改进会自动应用吗？

**A:** 只有**低风险**改进会自动应用。中高风险改进需要人工审核。

低风险改进包括：
- 增加超时时间
- 添加重试机制
- 降低请求频率

### Q3: 如何防止改进后效果变差？

**A:** 内置自动回滚机制。如果改进后：
- 成功率下降 >10%
- 平均耗时增加 >20%
- 连续失败 ≥5 次

会自动回滚到改进前的配置。

### Q4: 数据会占用多少空间？

**A:** 取决于任务量。典型场景：
- 1000 个任务 ≈ 1-2 MB
- 10000 个任务 ≈ 10-20 MB

建议定期清理旧数据（>30天）。

### Q5: 支持多进程/多线程吗？

**A:** 支持。每个进程/线程使用独立的 `SelfImprovingLoop` 实例即可。数据文件使用追加模式写入，支持并发。

### Q6: 如何集成到现有系统？

**A:** 最小侵入式集成：

```python
# 原代码
def my_function():
    # 业务逻辑
    return result

# 集成后
from self_improving_loop import SelfImprovingLoop
loop = SelfImprovingLoop()

def my_function():
    return loop.execute_with_improvement(
        agent_id="my-function",
        task="执行任务",
        execute_fn=lambda: original_logic()
    )["result"]

def original_logic():
    # 原业务逻辑不变
    return result
```

### Q7: 如何禁用自动改进？

**A:** 设置一个极高的失败阈值：

```python
from self_improving_loop import AdaptiveThreshold

at = AdaptiveThreshold()
at.set_manual_threshold("my-agent", failure_threshold=999999)

loop = SelfImprovingLoop()
loop.adaptive_threshold = at
```

### Q8: 支持分布式部署吗？

**A:** 当前版本使用本地文件存储，不支持分布式。如果需要分布式，可以：
1. 使用共享文件系统（NFS/S3）
2. 自己实现分布式存储后端（继承 `AgentConfig` 等类）

### Q9: 如何查看日志？

**A:** 日志文件位于 `{data_dir}/loop.log`：

```python
import json

with open("./my_data/loop.log", "r") as f:
    for line in f:
        log = json.loads(line)
        print(f"[{log['level']}] {log['message']}")
```

### Q10: 遇到问题怎么办？

**A:** 
1. 查看 [GitHub Issues](https://github.com/yangfei222666-9/self-improving-loop/issues)
2. 提交新 Issue（附上日志和复现步骤）
3. 查看源码（代码很简洁，易于理解）

---

## 下一步

- 查看 [examples/](../examples/) 了解更多示例
- 阅读 [API 文档](API.md)（如果有）
- 贡献代码：[CONTRIBUTING.md](../CONTRIBUTING.md)

祝你使用愉快！🎉
