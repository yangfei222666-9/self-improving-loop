# Examples

Run these in order. They are intentionally small and dependency-free.

```bash
python examples/01_basic_tracking.py
python examples/02_config_rollback.py
python examples/03_langgraph_adapter.py
python examples/04_yijing_strategy.py
python examples/05_langgraph_regression_guard.py
```

## 01_basic_tracking.py

Proves the minimum contract:

`agent call -> execute_with_improvement -> trace persisted -> stats readable`

Uses SQLite trace storage so the example matches a multi-worker production
shape while keeping the public API unchanged.

## 02_config_rollback.py

Proves the core product claim:

`bad patch -> regression detected -> ConfigAdapter.rollback_config() -> recovered agent`

This is the example to show when someone asks whether rollback is real or just
a log entry.

## 03_langgraph_adapter.py

Shows the integration seam for LangGraph-style callables without depending on
LangGraph. The same pattern applies to CrewAI, AutoGen, MCP tools, or an
internal agent runner: wrap the callable you already trust.

## 04_yijing_strategy.py

Proves the Yijing layer is an engineering state machine, not decoration:

`runtime traces -> six line scores -> hexagram state -> bounded policy patch`

The first version intentionally supports only eight core policy states. It does
not claim full 64-hexagram coverage.

## 05_langgraph_regression_guard.py

Proves the LangGraph-style reliability claim end to end without a LangGraph
dependency:

`node call -> trace -> success_rate / latency regression check -> rollback -> event trail`

Use this when someone asks whether the package is another agent framework or a
regression guard that can wrap an agent node you already run.
