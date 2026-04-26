# Bilingual Launch Copy / 中英双语发布材料

This file is for launch posts, demo captions, short videos, and replies.
Keep `README.md` technical and compact; use this file when publishing outside
GitHub.

本文用于发布帖、demo 配音、短视频字幕和评论回复。`README.md` 继续保持技术向、短而硬；
中文渠道和双语渠道用本文。

---

## 1. One-line Positioning / 一句话定位

**EN**

`self-improving-loop` is a regression guard for AI agents:
wrap LangGraph / Hermes / custom agent nodes, record traces, detect success-rate
or latency regression, roll back bad config changes, and preserve event
evidence.

**中文**

`self-improving-loop` 是 AI Agent 的回归保护层：
包住 LangGraph / Hermes / 自定义 agent 节点，记录 trace，检测成功率或延迟退化，
回滚坏配置，并保留可复查事件证据。

---

## 2. 30-second Demo Script / 30 秒 demo 口播

**EN**

Most agent frameworks focus on how to make an agent act. This project focuses
on what happens after it acts badly.

`self-improving-loop` wraps an existing LangGraph node, Hermes-style skill, or
custom agent call. It tracks success rate and latency, applies guarded config
changes through your adapter, and rolls back if the change makes the agent
worse.

The optional Yijing layer is not fortune telling. It is an internal state
router: six runtime dimensions become a hexagram state, and that state can
choose a bounded policy patch. The patch still goes through rollback.

**中文**

大多数 Agent 框架关心“怎么让 Agent 执行任务”。这个项目关心的是：
Agent 执行坏了以后，系统怎么发现、怎么修、怎么回滚。

`self-improving-loop` 可以包住 LangGraph 节点、Hermes-style skill 或自定义
Agent 调用，记录成功率和延迟，通过你的 adapter 应用受控配置变化；
如果变化让系统变差，就自动回滚。

这里的易经不是算命，而是一个可选的内部状态路由器：
六个运行维度形成卦象状态，卦象可以选择有边界的策略补丁；
补丁仍然必须经过 rollback。

---

## 3. X / LinkedIn Post / 英文短帖

**EN**

I built `self-improving-loop`, a small Python runtime for AI agent reliability.

It wraps LangGraph nodes, Hermes-style skills, or custom agent calls.
It records traces, detects success-rate or latency regression, rolls back bad
config changes, and preserves event evidence.

The unusual part: it includes an optional hexagram-guided strategy. Runtime
signals become six engineering lines, then a bounded policy decision. Not
fortune telling; just a deterministic state router behind the rollback guard.

Zero runtime dependencies. Python 3.9+. MIT.

Repo: https://github.com/yangfei222666-9/self-improving-loop

---

## 4. 即刻 / 小红书 / 中文短帖

**中文**

我把 TaijiOS 里最通用的一块拆成了独立库：`self-improving-loop`。

它不是另一个 Agent 框架，而是给现有 Agent 加一层回归保护：
包住 LangGraph 节点、Hermes-style skill 或自定义 Agent 调用，
记录执行结果、监控成功率和延迟、回滚坏配置，并保留事件证据。

最特别的地方是：内部可以用“六爻状态机”做策略路由。
基础稳定性、执行效率、学习活跃度、路由准确度、协作顺畅度、治理收敛度，
这 6 个运行维度组合成状态，再决定当前是该探索、保守、降级还是回滚。

这不是把易经当包装，而是把它变成 Agent 运行状态的工程协议。

GitHub: https://github.com/yangfei222666-9/self-improving-loop

---

## 5. Hacker News Boundary / HN 边界

**EN**

Use the English `SHOW_HN_DRAFT.md` for Hacker News. Do not post bilingual body
text there. HN readers want a tight technical pitch.

If someone challenges the Yijing part, answer:

> It is not used as mystical authority. It is a compact six-dimensional state
> machine. Runtime metrics map into six lines; the resulting state selects a
> bounded policy patch. The patch still goes through canary and rollback.

**中文**

HN 主帖只用英文，不要中英混排。HN 读者要的是短、硬、可验证的技术描述。

如果有人质疑易经部分，可以这样回：

> 这里的易经不是神秘权威，而是一个六维状态机。运行指标映射成六个爻位，
> 得到状态后选择一个有边界的策略补丁；补丁仍然必须经过 canary 和 rollback。

---

## 6. Claims We Can Safely Make / 可以安全说的事实

**EN**

- Pure Python stdlib at runtime.
- Python 3.9+.
- 61 tests currently pass.
- Supports JSONL trace storage and SQLite/WAL trace storage.
- Supports config backup / patch / restore through `ConfigAdapter`.
- Includes optional Yijing strategy with eight core states in the first version.
- The Yijing layer is experimental and deterministic.
- Includes runnable LangGraph-style and Hermes-style regression guard examples.

**中文**

- 运行时纯 Python 标准库。
- 支持 Python 3.9+。
- 当前 61 个测试通过。
- 支持 JSONL trace storage 和 SQLite/WAL trace storage。
- 通过 `ConfigAdapter` 支持配置备份、补丁应用和恢复。
- 第一版 Yijing strategy 支持 8 个核心状态。
- 易经层是实验性的、确定性的状态路由，不是玄学裁决。
- 已包含 LangGraph-style 与 Hermes-style regression guard 可运行示例。

---

## 7. Claims To Avoid / 不要说的话

**EN**

- Do not say it is a complete self-evolving system.
- Do not say the Yijing strategy covers all 64 hexagrams yet.
- Do not say it improves every agent automatically.
- Do not say it is production-proven.
- Do not frame it as a replacement for LangGraph, Hermes, CrewAI, AutoGen, or Agno.

**中文**

- 不要说它已经是完整自进化系统。
- 不要说易经策略已经覆盖完整 64 卦。
- 不要说它能自动让所有 Agent 变好。
- 不要说它已经生产验证。
- 不要说它替代 LangGraph、Hermes、CrewAI、AutoGen、Agno。

---

## 8. Practical CTA / 行动入口

**EN**

Try it when you have an agent or workflow that can get worse after prompt,
model, timeout, tool, or retry changes.

Start with:

```bash
pip install https://github.com/yangfei222666-9/self-improving-loop/releases/download/v0.1.1/self_improving_loop-0.1.1-py3-none-any.whl
git clone https://github.com/yangfei222666-9/self-improving-loop.git
cd self-improving-loop
python examples/06_hermes_skill_regression_guard.py
```

**中文**

如果你的 Agent 会因为 prompt、模型、timeout、工具选择或 retry 策略变化而变差，
这个库就是给这类场景加回归保护和自动回滚。

先从这里开始：

```bash
pip install https://github.com/yangfei222666-9/self-improving-loop/releases/download/v0.1.1/self_improving_loop-0.1.1-py3-none-any.whl
git clone https://github.com/yangfei222666-9/self-improving-loop.git
cd self-improving-loop
python examples/06_hermes_skill_regression_guard.py
```
