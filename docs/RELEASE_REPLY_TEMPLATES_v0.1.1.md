# Reply Templates · self-improving-loop v0.1.1

Use these for X, GitHub issues, or short community replies. Keep replies factual; do not overclaim.

## What is this?

`self-improving-loop` is a small reliability layer for AI agents. It wraps an agent call, records success/failure/latency, maps runtime signals into a six-line state, applies bounded config policies, and rolls back if the agent regresses.

## How is this different from LangGraph / CrewAI / AutoGen?

It is not a replacement for those frameworks. It is a guard layer around an agent you already have. LangGraph/CrewAI/AutoGen help you build and orchestrate agents; this focuses on regression detection, guarded config changes, and rollback evidence.

## Why hexagrams?

The hexagram layer is implemented as a deterministic state machine: six runtime dimensions become six lines, the six-line state selects a bounded policy, and the policy still goes through verification and rollback. It is a policy router, not fortune telling.

## Is it production-ready?

Not yet. `v0.1.1` has 43 tests, cross-platform CI, a rollback path, JSONL/SQLite trace storage, and a first Yijing strategy. It is early and should be tested around your own agent before production use.

## Is this just retry logic?

No. Retry handles transient failures. This watches rolling success rate, latency, and repeated failures to detect regressions after behavior or config changes. It can keep or roll back changes based on measured regression.

## Why not use an LLM to fix itself?

The base loop is LLM-free by design. If you want LLM-authored patches, pass an `improvement_strategy` that calls your own model. The rollback guard remains deterministic.

## Where should I start?

Start with the release and examples:

https://github.com/yangfei222666-9/self-improving-loop/releases/tag/v0.1.1

Run:

```bash
python examples/01_basic_tracking.py
python examples/02_config_rollback.py
python examples/04_yijing_strategy.py
```
