# Hermes-style Skill Regression Guard

`self-improving-loop` is not a Hermes replacement.

It is a regression guard that can sit under Hermes-style skills, OpenClaw
plugins, LangGraph nodes, CrewAI tasks, or any custom agent callable.

## Contract

```text
Hermes-style skill call
-> bad skill config patch
-> skill repeated failures
-> trace recorded
-> rollback restores previous config
-> event trail written
```

The runnable proof is:

```bash
python examples/06_hermes_skill_regression_guard.py
```

## What It Proves

- A skill call can be wrapped without adopting a new agent framework.
- A bad skill config patch is backed up before it is applied.
- Repeated skill failures are recorded as traces.
- Regression checks can trigger rollback.
- `ConfigAdapter.rollback_config()` restores the previous skill config.
- A JSONL event trail survives for audit and review.

## Integration Shape

```python
result = loop.track(
    agent_id="hermes-research-skill",
    task="run research skill",
    execute_fn=lambda: research_skill(args),
    context={
        "framework_style": "hermes_skill",
        "skill": "research",
    },
)
```

For real config restore, pass a `ConfigAdapter`:

```python
loop = SelfImprovingLoop(
    strategy=my_strategy,
    config_adapter=my_skill_config_adapter,
    storage="sqlite",
)
```

The loop owns trace, threshold, regression detection, and rollback decision.
Your runtime owns how skill config is read, patched, and restored.

## Boundary

This does not provide Hermes memory, message routing, MCP servers, sub-agents,
or a skill marketplace.

It provides the narrow safety layer that answers:

```text
If this skill gets worse after a config/prompt/model/tool change,
can we prove what happened and roll back?
```

## Launch Copy

```text
Not competing with Hermes.

self-improving-loop is a regression guard that can sit under Hermes-style
skills, LangGraph nodes, or custom agent calls:
trace failures, detect regression, roll back bad config, preserve evidence.
```
