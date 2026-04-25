# self-improving-loop

> A safety-first self-improvement loop for AI agents:
> **execute → track → analyze → strategy-apply → rollback on regression.**

[![PyPI](https://img.shields.io/badge/pypi-0.1.0-blue.svg)](https://pypi.org/project/self-improving-loop/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Overhead](https://img.shields.io/badge/overhead-%3C1%25-brightgreen)](#performance)

Most "self-improving agent" projects stop at *"log the failures, let the next run read the log"*. That's a methodology, not a loop. **This package is the loop, as 1,170 lines of pure-stdlib Python** — no framework lock-in, no LLM dependency, no cloud.

Wrap any function, get:

- 📊 **Automatic execution tracking** (success rate, latency, rolling window)
- 🧠 **Adaptive thresholds** per agent profile (high-freq / mid-freq / low-freq / critical)
- 🛠 **Strategy hook** for applying improvement configs when failure patterns are detected
- 🛡 **Rollback trigger** when the new config regresses (>10% success drop, >20% latency gain, or 5 consecutive failures)
- 📬 **Pluggable notifier** (stub by default — swap in Telegram / Slack / whatever)

Extracted from [**TaijiOS**](https://github.com/yangfei222666-9/TaijiOS), where it survived a 346-heartbeat Ising physics experiment and production-scale agent workloads.

---

## Install

```bash
pip install self-improving-loop
```

Zero required dependencies. Everything is `datetime`, `json`, `pathlib`, `typing`.

---

## 30-second example

```python
from self_improving_loop import SelfImprovingLoop

loop = SelfImprovingLoop()

def my_agent_work():
    # Your actual agent call / LLM chain / tool invocation
    return {"status": "ok", "data": ...}

result = loop.execute_with_improvement(
    agent_id="my-agent",
    task="handle user query",
    execute_fn=my_agent_work,
)

if result["improvement_triggered"]:
    print(f"Strategy applied {result['improvement_applied']} config tweaks")

if result["rollback_executed"]:
    print(f"Rolled back because: {result['rollback_executed']['reason']}")
```

That's it. The loop watches every execution, decides when to trigger tuning, and can undo tunings that made things worse when you provide a strategy hook.

---

## Prove rollback in one command

Run the end-to-end safety demo:

```bash
python examples/regression_rollback_demo.py
```

Expected evidence:

```text
baseline pass
failure detected
improvement proposed
backup created
patch applied
quality worse
rollback executed
final status recovered
event trail written: /tmp/.../regression_rollback_event_trail.jsonl
```

The demo intentionally applies a bad patch via an `improvement_strategy`, then
proves the runtime can restore the prior config and write an auditable event
trail. It is not a mocked success path.

---

## Use it as a safety layer for your current agent

This package is not trying to replace LangGraph, CrewAI, AutoGen, OpenAI
Agents, or your own internal runner. It wraps the callable you already trust:

```python
result = loop.execute_with_improvement(
    agent_id="support-agent",
    task="answer ticket",
    execute_fn=lambda: existing_agent.run(ticket),
    context={"framework": "your-current-stack"},
)
```

Two dependency-free examples show the integration seam:

```bash
python examples/wrap_existing_agent.py
python examples/langgraph_style_node.py
```

The goal is narrow: traces, thresholds, guarded strategy application, and
rollback evidence around an agent you already have.

---

## Why this exists

Most agents have this failure mode:

1. You ship an agent.
2. It works for a week.
3. Something upstream changes (rate limits, schema drift, a new edge case).
4. Your agent starts failing.
5. You find out three days later from angry users.
6. You tweak a config, hope for the best, ship it.
7. The tweak makes another scenario worse.
8. You roll it back manually, losing the original learning.

`self-improving-loop` turns steps 3–8 into a tight feedback loop that runs inside your process, without needing observability infra, Kubernetes, or a dedicated ML team.

---

## Adaptive thresholds (no magic numbers)

Different agents have different "pulse rates". A critical alerting agent should reconsider after 1 failure; a batch classifier can tolerate 5 before triggering analysis. The library classifies agents by execution frequency and adjusts:

| Agent profile | Failure trigger | Analysis window | Cooldown |
|---|---|---|---|
| High-frequency (>10/day) | 5 failures | 48h | 3h |
| Medium-frequency (3-10/day) | 3 failures | 24h | 6h |
| Low-frequency (<3/day) | 2 failures | 72h | 12h |
| Critical (user-marked) | 1 failure | 24h | 6h |

Or bypass the classifier and set manually:

```python
from self_improving_loop import AdaptiveThreshold

adaptive = AdaptiveThreshold()
adaptive.set_manual_threshold(
    "critical-agent",
    failure_threshold=1,
    analysis_window_hours=12,
    cooldown_hours=1,
    is_critical=True,
)
```

---

## Auto-rollback (the safety net)

When a config change ships, the loop keeps watching. It rolls back if **any** of these become true:

- Success rate drops >10%
- Average latency increases >20%
- ≥5 consecutive failures after the change

```python
# See recent rollbacks
rollback_history = loop.auto_rollback.get_rollback_history("my-agent")
for event in rollback_history:
    print(event["reason"], event["timestamp"])
```

---

## Pluggable notifier

The built-in `TelegramNotifier` is a stub — it logs to stdout. Override `_send_message()` to hook any channel:

```python
from self_improving_loop import TelegramNotifier

class MySlackNotifier(TelegramNotifier):
    def __init__(self, webhook_url, **kw):
        super().__init__(**kw)
        self.webhook_url = webhook_url

    def _send_message(self, message, priority="normal"):
        import requests
        requests.post(self.webhook_url, json={"text": f"[{priority}] {message}"})

loop = SelfImprovingLoop(notifier=MySlackNotifier(webhook_url="https://hooks..."))
```

---

## Performance

Measured locally with `benchmarks/overhead.py` (200 iterations per workload, Python 3.12, Windows):

| Workload profile | Absolute overhead | Relative overhead |
|---|---|---|
| ~100 ms agent call (typical LLM) | +0.27 ms | **+0.3%** |
| ~10 ms agent call (tool call) | +0.31 ms | **+3.0%** |
| sub-millisecond call | +0.08 ms | >>% (don't wrap these) |

The wrapper adds a stable **~300 μs of fixed cost per call** (trace append + threshold check). Whether that's negligible depends on your workload:

- LLM calls (>500 ms): overhead is ≤0.06% — invisible
- HTTP / DB calls (~30-100 ms): ≤1%
- Fast in-memory work (<10 ms): 3%+ — reconsider whether you need this for those

Rerun the benchmark on your own machine with `python benchmarks/overhead.py`.

Separate operation costs (triggered occasionally, not per-call):

| Operation | Cost |
|---|---|
| Failure analysis (only when threshold crossed) | ~100 ms |
| Applying improvement config | ~200 ms |
| Rollback execution | ~10 ms |

---

## Not a...

- **...methodology doc.** Many "self-improving agent" repos are markdown templates that ask *you* to log learnings to `CLAUDE.md`. This is the runtime loop that does it for you.
- **...heavyweight framework.** 1,170 LoC of stdlib. Drop it next to your existing code. No decorators forced on you. No background process.
- **...LLM-dependent.** The analysis is statistical, not LLM-based. If you want LLM-authored config tweaks, pass an `improvement_strategy` object and ask your favorite LLM inside its `analyze()` method.

---

## Background

Extracted from [**TaijiOS**](https://github.com/yangfei222666-9/TaijiOS) — a self-learning AI operating system with 5 *I Ching*–bound engines and a 346-heartbeat Ising physics experiment. The parent project has 14 modules; this one is the most generally reusable, so it lives as a standalone package.

TaijiOS was built through multi-AI collaboration starting on **Chinese New Year 2026-02-17** (60 days before this release).

---

## License

MIT. Ship it wherever.

## Contact / Feedback

This is a very early release. Every bug report, every "didn't work for me", every "I wish it did X" is read:

- GitHub Issue: [open one](https://github.com/yangfei222666-9/self-improving-loop/issues/new)
- Parent project: [TaijiOS](https://github.com/yangfei222666-9/TaijiOS)

---

*"Safety first, then automation."*
