# Self-Improving Agent 3 天验证计划

## 目标
证明系统在真实环境里不会误修、不会振荡、不会把系统带偏。

## 验证流程

### Day 1: 只读观察（dry-run）
**目的**: 确认分析器靠谱、建议不胡来

**运行命令**:
```bash
python safe_self_improving.py --dry-run --days 1 --min 3
python safe_self_improving.py --report 1
```

**检查项**:
- ✅ 识别的失败模式是否合理（timeout/502/权限/路径）
- ✅ 建议是否可执行且不激进
- ✅ 是否出现"同一问题反复给不同建议"（不稳定）
- ✅ 轨迹记录是否完整（每次都有 trace_id）

**通过标准**:
- 建议命中率高（主观判断：80% 看起来合理）
- 没有高风险建议混进来（删文件/重启服务等）

---

### Day 2: 仅允许 low 风险自动应用（带冷却）
**目的**: 验证"自动改一点"不会出事

**运行命令**:
```bash
python safe_self_improving.py --days 2 --min 3 --risk low
python safe_self_improving.py --report 2
```

**检查项**:
- ✅ 自动修复后失败率下降或超时减少（至少一个指标改善）
- ✅ 同一修复 24h 内不会重复应用（避免振荡）
- ✅ 没有引入新错误类型

**通过标准**:
- 失败率下降 或 超时减少
- 冷却期生效（24h 内不重复应用）
- 无新增错误类型

---

### Day 3: 回归验证（对比窗口）
**目的**: 确认不是"碰巧变好了"

**运行命令**:
```bash
python safe_self_improving.py --days 3 --min 3 --risk low
python safe_self_improving.py --report 3
```

**检查项**:
- 统计 Before/After 两个窗口（例如各 20 次任务）：
  - success_rate
  - timeout_count
  - avg_latency（可选）
- 结果写进 daily_summary.json

**通过标准（硬一点）**:
- success_rate 相对提升 ≥ 10% 或
- timeout_count 下降 ≥ 30%
- 并且无新增高危事件

---

## 安全阀（必须）

### 1. 风险门
默认只允许 low 风险自动 apply

**Low 风险白名单**:
- increase_timeout（增加超时时间）
- add_retry（添加重试机制）
- rate_limiting（限流）
- agent_degradation（降低 Agent 优先级）
- thinking_level_adjust（调整 thinking level）

**High 风险黑名单**（一律需要人工确认）:
- delete_file（删除文件）
- restart_service（重启服务）
- kill_process（杀进程）
- modify_permissions（修改权限）
- install_dependency（安装依赖）

### 2. 冷却期
同一修复 24h 只能应用一次，避免振荡

### 3. 熔断器
连续回滚/变差 ≥2 次 → 停止自动改进 24h，只发提醒

---

## 文件结构

```
aios/agent_system/
├── safe_self_improving.py       # 带安全阀的改进脚本
├── safety_valve.py               # 安全阀（风险门+冷却期+熔断器）
├── validation_report.py          # 验证报告生成器
└── data/
    ├── safety/
    │   ├── cooldown_state.json       # 冷却状态
    │   └── circuit_breaker_state.json # 熔断器状态
    └── validation/
        └── day*_report_*.json        # 每日验证报告
```

---

## 使用示例

### Day 1: Dry-run
```bash
# 只分析不应用
python safe_self_improving.py --dry-run --days 1 --min 3

# 生成报告
python safe_self_improving.py --report 1
```

输出示例:
```
=== Safe Self-Improving Agent ===
模式: DRY-RUN（只分析不应用）
风险等级: low

发现 3 条改进建议

[DRY-RUN] 将应用: 检测到频繁超时，建议增加超时时间
   操作: increase by 50%

🚫 阻止应用: 工具 exec 频繁失败，建议添加备用方案
   原因: 非低风险操作 tool_fallback，当前只允许 low 风险

=== 摘要 ===
总改进建议: 3
已应用: 2
被阻止: 1
```

### Day 2: 低风险自动应用
```bash
# 自动应用低风险改进
python safe_self_improving.py --days 2 --min 3 --risk low

# 生成报告
python safe_self_improving.py --report 2
```

### Day 3: 回归验证
```bash
# 继续自动应用
python safe_self_improving.py --days 3 --min 3 --risk low

# 生成最终报告
python safe_self_improving.py --report 3
```

---

## 验证报告示例

```
============================================================
Day 1 验证报告 - 2026-02-24
============================================================

📊 今日统计
  总任务数: 7
  失败数: 5
  成功率: 28.6%
  超时数: 4
  失败类型 Top3: {'timeout': 4, 'network': 1}

🔍 识别到的模式 Top3
  - Timeout after Ns (出现 4 次)

🔧 改进情况
  建议数: 3
  应用数: 2
  成功: 2
  失败: 0

🛡️ 安全状态
  熔断器: 正常
  连续失败: 0
  冷却中: 0 个改进

✅ 验证结论
  阶段: 只读观察（dry-run）
  通过: ✓
```

---

## 通过后的下一步

1. **集成到心跳** - 每天自动运行一次，只允许 low 风险
2. **Phase 3** - A/B 测试 + 自动回滚机制
3. **扩展策略库** - 添加更多改进规则
4. **可视化 Dashboard** - 展示改进历史和效果

---

## 注意事项

1. **数据积累** - 至少需要 7 天的追踪数据才能有效分析
2. **风险控制** - 默认只允许 low 风险，中高风险需要人工审核
3. **熔断保护** - 连续失败 ≥2 次自动停止，避免系统带偏
4. **冷却期** - 24h 内不重复应用同一修复，避免振荡

---

## 故障排查

### 熔断器触发
```bash
# 检查熔断器状态
cat data/safety/circuit_breaker_state.json

# 手动重置（谨慎）
rm data/safety/circuit_breaker_state.json
```

### 冷却期查询
```bash
# 查看哪些改进在冷却中
cat data/safety/cooldown_state.json
```

### 查看完整日志
```bash
# 追踪数据
cat data/traces/agent_traces.jsonl

# 修复历史
cat data/fixes/fix_history.jsonl

# 验证报告
cat data/validation/day1_report_*.json
```
