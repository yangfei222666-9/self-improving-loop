# Agent Data Strategy

Status: `portfolio_evidence`

This document describes `self-improving-loop` as an Agent execution data strategy project.

It does not claim to be a model training system, a complete agent framework, or an autonomous AI OS. The narrow claim is:

```text
wrap an agent call
-> record execution traces
-> detect quality or latency regression
-> apply guarded config changes
-> rollback bad changes
-> preserve event evidence
```

## 1. Problem

Agent workflows often fail in ways that a final response cannot reveal:

- false success: the agent says "done" but the artifact is missing or stale,
- provider drift: the model/tool route silently changes,
- latency regression: the call still succeeds but becomes too slow,
- success-rate regression: a prompt/config patch lowers quality,
- missing event trail: there is no replayable evidence,
- rollback gap: a bad config cannot be restored safely.

The project treats those as data problems, not just prompt problems.

## 2. Data Captured

Each execution can be turned into a trace record.

Minimum useful fields:

```json
{
  "trace_id": "trace_001",
  "agent_id": "support-agent",
  "task": "answer_ticket",
  "timestamp": "2026-04-29T00:00:00Z",
  "success": true,
  "latency_ms": 1240,
  "provider_route": "custom_agent_node",
  "config_version": "cfg_12",
  "artifact_ref": "sha256:...",
  "failure_label": null,
  "rollback_result": null
}
```

The concrete runtime supports readable JSONL traces by default and SQLite/WAL for multi-worker deployments.

## 3. Failure Labels

The most important labels for Agent evaluation:

| label | meaning | routing |
| --- | --- | --- |
| `success_rate_regression` | A new config/prompt/model route reduces success rate beyond threshold. | rollback |
| `latency_regression` | A new config/prompt/model route increases latency beyond threshold. | rollback or review |
| `consecutive_failures` | The same agent fails repeatedly inside the analysis window. | guarded strategy |
| `config_patch_regressed` | A proposed config was applied but made the run worse. | rollback |
| `missing_event_trail` | No replayable event evidence exists. | block trust |
| `provider_route_drift` | Expected tool/model route changed unexpectedly. | block or review |
| `stale_artifact` | Existing output belongs to an older run. | block trust |

These labels are deliberately operational. They are designed to become eval cases.

## 4. Regression Guard Logic

The library watches rolling execution metrics and can trigger rollback when:

```text
success rate drops more than 10%
latency increases more than 20%
five consecutive failures occur
```

The rollback path is intentionally separated from the strategy path:

```text
Strategy proposes a config patch.
ConfigAdapter backs up current config.
Patch is applied.
Canary/evaluation detects regression.
ConfigAdapter restores previous config.
Trace and rollback evidence remain.
```

This separation is the core reliability idea: learning is allowed, but bad learning cannot silently become the new baseline.

## 5. Eval Packet Schema

A reusable eval packet should contain:

```json
{
  "case_id": "REG-001",
  "agent_id": "support-agent",
  "baseline_window": {
    "success_rate": 0.92,
    "p95_latency_ms": 1800
  },
  "candidate_window": {
    "success_rate": 0.78,
    "p95_latency_ms": 2600
  },
  "failure_labels": [
    "success_rate_regression",
    "latency_regression"
  ],
  "rollback_expected": true,
  "rollback_observed": true,
  "evidence": {
    "trace_file": ".repro-demo/traces.jsonl",
    "event_trail": ".repro-demo/regression_rollback_event_trail.jsonl"
  },
  "verdict": "regression_blocked"
}
```

## 6. Demo Commands

Run the minimal rollback event-trail demo:

```bash
python examples/regression_rollback_demo.py --data-dir .repro-demo
python examples/verify_regression_rollback_event_trail.py .repro-demo/regression_rollback_event_trail.jsonl
```

Expected behavior:

```text
bad skill/config patch is applied
regression is detected
rollback restores previous config
event trail is written
verifier confirms rollback evidence
```

## 7. Why This Fits Agent Data / Eval Work

This project is not trying to make a model smarter directly.

It creates the data layer needed to evaluate whether an Agent got safer or worse after a change:

```text
trace data
failure labels
metric windows
rollback result
event evidence
```

That is the part most agent demos skip.

## 8. Boundary

Current evidence is a small, reproducible open-source package with tests and examples.

It is not yet:

- a large production trace dataset,
- a benchmark accepted by external teams,
- a hosted observability platform,
- a replacement for LangSmith / Langfuse / Phoenix.

The intended next step is external repro feedback from real LangGraph, CrewAI, Hermes-style, or custom agent-node users.
