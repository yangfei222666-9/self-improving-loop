# Self-Improving Agent System

自我学习和自动改进的 Agent 系统。

## 核心功能

1. **任务追踪** - 记录 Agent 执行的每个细节
2. **失败分析** - 识别重复失败模式
3. **自动修复** - 根据失败模式自动应用改进
4. **效果验证** - A/B 测试验证改进效果（Phase 3）

## 工作流程

```
Agent 执行任务 → AgentTracer 记录轨迹 → FailureAnalyzer 分析失败模式 
→ AgentAutoFixer 应用修复 → 验证效果 → 更新配置
```

## 快速开始

### 1. 在 Agent 代码中集成追踪器

```python
from agent_tracer import AgentTracer

# 创建追踪器
tracer = AgentTracer("agent_coder_001")

# 开始任务
tracer.start_task("修复登录 bug", context={"file": "auth.py"})

# 记录步骤
tracer.log_step("读取文件")
tracer.log_tool_call("read", {"path": "auth.py"}, result="...")

# 结束任务
tracer.end_task(success=True, metadata={"lines_changed": 3})
```

### 2. 运行失败分析

```bash
# 分析最近 7 天的失败模式（最少出现 3 次）
python analyze_failures.py 7 3
```

输出示例：
```
总追踪数: 100
总失败数: 25
识别模式: 3
改进建议: 3

改进建议：
1. 检测到频繁超时，建议增加超时时间
   类型: increase_timeout
   优先级: high
   操作: increase by 50%
```

### 3. 应用自动修复

```bash
# 手动确认模式（默认）
python agent_auto_fixer.py --days 7 --min 3

# 自动应用低风险改进
python agent_auto_fixer.py --auto --days 7 --min 3
```

### 4. 运行完整改进循环

```bash
# 一键运行：分析 → 修复 → 报告
python self_improving_agent.py --auto --days 7 --min 3
```

## 文件结构

```
aios/agent_system/
├── agent_tracer.py              # 任务追踪器
├── analyze_failures.py          # 失败分析器
├── agent_auto_fixer.py          # 自动修复器
├── self_improving_agent.py      # 完整闭环
├── test_tracer.py               # 测试脚本
└── data/
    ├── traces/
    │   └── agent_traces.jsonl       # 追踪数据
    ├── analysis/
    │   └── failure_patterns.json    # 分析报告
    ├── fixes/
    │   ├── fix_history.jsonl        # 修复历史
    │   └── fix_report_*.json        # 修复报告
    ├── reports/
    │   └── cycle_*.json             # 改进循环报告
    └── agent_configs.json           # Agent 配置
```

## 改进策略库

当前支持的自动修复：

### 1. 超时问题
- **检测**: 同类超时错误 ≥3 次
- **修复**: 增加 timeout 50%
- **风险**: 低

### 2. 网络错误
- **检测**: 502/503/network 错误 ≥3 次
- **修复**: 添加重试机制（3次，指数退避）
- **风险**: 低

### 3. 限流错误
- **检测**: 429/rate limit 错误 ≥3 次
- **修复**: 增加请求延迟（1-2秒）
- **风险**: 低

### 4. Agent 失败率过高
- **检测**: 失败率 >50%
- **修复**: 降低优先级 50% 或触发重启
- **风险**: 低

### 5. 工具频繁失败
- **检测**: 同一工具失败 ≥3 次
- **修复**: 建议添加备用方案（需人工实现）
- **风险**: 低

### 6. 内存问题
- **检测**: 内存相关错误 ≥3 次
- **修复**: 建议优化内存使用或减少批量大小
- **风险**: 中

## 配置文件

`agent_configs.json` 示例：

```json
{
  "timeout": 45,
  "request_delay": 1.5,
  "agents": {
    "agent_coder_001": {
      "priority": 0.5
    }
  }
}
```

## 集成到心跳任务

在 `HEARTBEAT.md` 中添加：

```markdown
### 每天：Agent 自我改进
- 运行 `python self_improving_agent.py --auto --days 7 --min 3`
- 自动分析失败模式并应用低风险改进
- 如果有中高风险改进，提醒珊瑚海人工审核
```

## 下一步（Phase 3）

- [ ] A/B 测试框架（验证改进效果）
- [ ] 自动回滚机制（改进失败时恢复旧配置）
- [ ] 扩展改进策略库（更多错误类型）
- [ ] 可视化 Dashboard（展示改进历史和效果）
- [ ] 跨 Agent 学习（一个 Agent 的教训应用到其他 Agent）

## 测试

```bash
# 运行测试
python test_tracer.py
```

## 注意事项

1. **风险分级**
   - 低风险：自动应用（配置调整、优先级调整）
   - 中风险：需要确认（代码变更建议）
   - 高风险：需要人工审核（架构变更）

2. **数据隐私**
   - 追踪数据包含任务输入输出，注意敏感信息
   - 可以在 `AgentTracer` 中添加过滤规则

3. **性能影响**
   - 追踪器开销很小（每个任务 <1ms）
   - 分析器只在心跳时运行（每天一次）

## 贡献

欢迎提交新的改进策略！在 `agent_auto_fixer.py` 中添加新的规则即可。
