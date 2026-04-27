# Launch Post Draft

## Short version

I am looking for external repro feedback on a small regression guard for AI agents:

https://github.com/yangfei222666-9/self-improving-loop

It wraps an agent call, records traces, detects regression, applies a guarded change, rolls back when quality gets worse, and writes an event trail.

Run:

```bash
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
```

I am not asking for a star. I am looking for one concrete answer:

Would this be useful for a LangGraph / CrewAI / Hermes / custom agent node? If not, what makes it unusable?

## Longer version

Most agent demos focus on "it worked once."

I am trying to make the failure path observable instead:

```text
agent call
-> trace failure
-> detect regression
-> apply guarded config change
-> quality gets worse
-> rollback
-> event trail survives
```

The current repro is intentionally small:

```bash
git clone https://github.com/yangfei222666-9/self-improving-loop.git
cd self-improving-loop
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
python -m pip install pytest
python -m pytest tests/test_examples.py -q
```

If it fails, or if the rollback evidence is not convincing, please open an External Repro Report:

https://github.com/yangfei222666-9/self-improving-loop/issues/new/choose

The feedback I need most:

- Can a stranger run it in 5 minutes?
- Is the event trail enough to debug what changed?
- Where would this connect in LangGraph / CrewAI / Hermes / custom agent nodes?
- What makes it not useful?

## Chinese version

我在找外部复现反馈，不是要 star。

项目是一个很小的 AI Agent regression guard：

https://github.com/yangfei222666-9/self-improving-loop

目标只做一件事：

```text
记录 agent 调用
-> 发现失败 / 质量退化
-> 应用受控改动
-> 如果变差就回滚
-> 留下可审计事件流
```

最小复现：

```bash
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
```

我想知道的是：这东西能不能接到你的 LangGraph / CrewAI / Hermes / custom agent node？如果不能，卡在哪里？
