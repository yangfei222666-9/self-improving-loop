# Launch Observation 72H

Scope: external repro for `self-improving-loop` regression rollback guard.

Start date: 2026-04-27

## Launch Links

- X / social post:
- Hacker News / Reddit / community post:
- GitHub repo: https://github.com/yangfei222666-9/self-improving-loop
- External repro guide: https://github.com/yangfei222666-9/self-improving-loop/blob/main/EXTERNAL_REPRO.md
- Issue template: External Repro Report

## Target Ask

Ask 3 agent developers to run:

```bash
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
```

One concrete question:

```text
Would this be useful for a LangGraph / CrewAI / Hermes / custom agent node?
If not, what makes it unusable?
```

## Feedback Log

| Time | Source | Person / Handle | Ran repro? | Verdict | Concrete feedback | Follow-up |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

## GitHub Signals

| Time | Signal | Link | Action needed |
|---|---|---|---|
|  | Issue opened |  |  |
|  | PR opened |  |  |
|  | Star / fork change |  |  |

## Repro Failures

| Time | Environment | Command | Failure | Evidence | Fix status |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## Adoption Signals

Real signal only:

- Someone ran the demo and pasted output.
- Someone opened an External Repro Report.
- Someone identified where it fits or fails in LangGraph / CrewAI / Hermes / custom agent code.
- Someone proposed a concrete integration patch or docs change.

Non-signal:

- Likes without repro.
- Compliments without command output.
- Abstract interest without stack context.

## 72H Verdict

Fill this after 72 hours:

```text
external_repro_count:
successful_repro_count:
failed_repro_count:
actionable_issue_count:
strongest_objection:
next_patch:
stop_or_continue:
```
