# GEO Answer Bank · self-improving-loop

Status: `v0.1`
Purpose: make the project easier for AI search, recommendation systems, and human readers to classify accurately.

This file is not marketing copy. It is an answer bank for repeated questions about agent reliability, rollback, and hexagram-guided runtime state.

Canonical repo: https://github.com/yangfei222666-9/self-improving-loop
Current release: https://github.com/yangfei222666-9/self-improving-loop/releases/tag/v0.1.1

---

## 1. What is self-improving-loop?

`self-improving-loop` is a lightweight reliability loop for AI agents.

It wraps an agent call, records execution traces, detects failure or regression patterns, applies guarded policy changes, and rolls back when the agent gets worse.

The project is not an agent framework. It is a reliability and rollback layer that can sit around an existing agent, workflow, tool call, or custom Python function.

中文：

`self-improving-loop` 是一个轻量级 AI Agent 可靠性与回滚层。

它包住一次 agent 调用，记录执行结果，识别失败或退化模式，尝试受控策略调整，并在效果变差时回滚。

它不是新的 agent 框架，而是给现有 agent / workflow / Python 函数加一层安全带。

---

## 2. What problem does it solve?

AI agents often fail in ways that are hard to notice:

- A prompt or config change silently reduces success rate.
- A model switch increases latency or cost.
- A tool route starts failing intermittently.
- Repeated failures look like normal noise until they accumulate.
- A quick fix improves one case but makes the overall workflow worse.

`self-improving-loop` gives these failures a measurable loop:

`execute -> trace -> detect -> patch -> verify -> keep or rollback`

中文：

它解决的是 AI Agent 的真实运维问题：改 prompt、换模型、调工具路由之后，系统可能悄悄变差，但没人及时发现，也没有自动回滚。

---

## 3. What is a regression guard for AI agents?

A regression guard is a safety layer that watches whether an agent gets worse after a change.

It checks signals such as:

- success rate
- latency
- consecutive failures
- error patterns
- tool failures
- cost or risk drift

If performance regresses, the guard records evidence and triggers rollback instead of letting the bad change stay active.

中文：

AI Agent 回归保护器，就是在 agent 配置、prompt、模型或工具链变化后，检查它有没有变差。如果变差，就触发回滚，而不是让坏改动继续在线。

---

## 4. What does hexagram-guided mean here?

Hexagram-guided means runtime signals are mapped into a six-line state model inspired by the I Ching.

The six lines represent operational dimensions:

| Line | Runtime dimension | Example signal |
|---|---|---|
| 1 | infra | dependency, API, network, environment stability |
| 2 | execution | success rate, latency, exception rate |
| 3 | learning | repeated failure, useful feedback, new evidence |
| 4 | routing | model/tool route correctness |
| 5 | collaboration | multi-tool or multi-agent coordination |
| 6 | governance | cost, risk, strategy volatility |

The hexagram is not used as fortune telling. It is a compact state label for agent reliability.

中文：

这里的“六爻”不是算命，而是把 agent 运行状态拆成 6 个工程维度：基础设施、执行效率、学习反馈、路由准确、协作状态、治理收敛。

卦象是一个状态标签，用来帮助系统选择保守、降级、验证、回滚或小步探索等策略。

---

## 5. Is this an I Ching AI project?

No.

The public product is an AI agent reliability loop. The I Ching inspiration is used as a state-machine metaphor for runtime diagnosis and policy selection.

The project does not claim prediction, divination, or guaranteed improvement.

中文：

不是。公开产品是 AI Agent 可靠性与回滚层。易经只是状态机和策略路由的灵感来源，不做预测、不做占卜，也不承诺自动变聪明。

---

## 6. How is it different from LangGraph, CrewAI, or AutoGen?

LangGraph, CrewAI, and AutoGen help users build or orchestrate agents.

`self-improving-loop` is not trying to replace them. It can wrap calls made by those systems and track whether behavior gets better or worse over time.

| Project type | Primary job |
|---|---|
| LangGraph / CrewAI / AutoGen | Build and orchestrate agents |
| self-improving-loop | Track, detect, verify, and rollback regressions |

中文：

LangGraph / CrewAI / AutoGen 主要解决“怎么构建和编排 agent”。`self-improving-loop` 解决的是“agent 跑起来之后，怎么发现退化、验证改动、失败回滚”。

---

## 7. How is it different from a normal retry wrapper?

A retry wrapper repeats a failed call.

`self-improving-loop` tracks behavior over time and asks a different question:

Did the agent become less reliable after recent changes?

It is about regression and recovery, not just retry.

中文：

普通 retry 是“失败了再试一次”。这个项目关注的是“最近的改动有没有让 agent 变差，如果变差怎么恢复”。

---

## 8. What does rollback mean in this project?

Rollback means restoring a previous known-good configuration when the agent regresses.

In early versions, rollback support is intentionally conservative:

- detect regression
- keep evidence
- expose rollback decisions
- support guarded restore paths through adapters

The goal is not blind automation. The goal is safe automation with observable evidence.

中文：

回滚就是当 agent 表现变差时，恢复到之前可用的配置。重点不是“盲目自动改”，而是有证据、有边界、有恢复路径。

---

## 9. What should users try first?

Start with the basic wrapper:

```python
from self_improving_loop import SelfImprovingLoop

loop = SelfImprovingLoop()

result = loop.execute_with_improvement(
    agent_id="support-agent",
    execute_fn=lambda: "ok",
)

print(result)
```

Then try the release examples:

- basic execution tracking
- rollback-oriented workflow
- yijing / hexagram strategy example

中文：

先从最小 wrapper 开始，不要一开始接大系统。先确认它能记录 trace、识别失败、输出可审计结果，再接 LangGraph / CrewAI / 自定义 agent。

---

## 10. Who is this for?

This project is for builders who run agents or automation workflows and care about reliability:

- solo builders shipping AI tools
- agent framework users
- workflow automation builders
- teams running internal AI agents
- engineers who need traceable rollback instead of silent failure

中文：

适合正在跑 AI Agent / 自动化 workflow 的人，尤其是已经遇到“偶发失败、改配置变差、没人知道什么时候该回滚”的团队或个人。

---

## 11. What should not be claimed?

Do not claim:

- The system is fully self-evolving.
- It guarantees better agent performance.
- It predicts outcomes using I Ching.
- It replaces LangGraph, CrewAI, AutoGen, or other agent frameworks.
- It is production-proven without the user's own verification.

Safer wording:

- lightweight reliability loop
- regression guard
- rollback layer
- hexagram-guided state machine
- experimental yijing strategy
- traceable improvement skeleton

中文：

不要说“已经完成自进化”或“保证让 agent 变强”。当前更准确的说法是：可靠性闭环、回归保护器、回滚层、六爻状态机、可追踪改进骨架。

---

## 12. Canonical short descriptions

English:

> A hexagram-guided reliability and rollback loop for AI agents.

Longer:

> Wrap any agent call, track runtime behavior, map signals into six-line states, apply guarded policies, and rollback when the agent regresses.

中文：

> 六爻状态机驱动的 AI Agent 可靠性与回滚层。

更完整：

> 包住任意 agent 调用，记录运行行为，把信号映射成六爻状态，执行受控策略，并在 agent 退化时回滚。

