# Agent Eval Annotation Guideline

This guideline defines how to label agent workflow failures for regression
guards, eval packets, and human review queues.

It is not a benchmark claim. It is a conservative labeling policy for turning
agent execution evidence into auditable data.

## Goal

Convert an agent run into a structured eval case:

```text
task -> trace -> artifact -> failure label -> routing verdict -> evidence
```

The labeler must not infer success from a final text answer alone. A run is only
trusted when the required trace, artifact, and verifier evidence exist.

## Required Fields

Each eval case should capture:

- `case_id`: stable unique identifier.
- `domain`: workflow family, such as coding_agent, tool_calling, or provider_route.
- `task_type`: what the agent was trying to do.
- `agent_stack`: framework or runner shape, such as LangGraph, Hermes, OpenClaw, Cursor, Claude Code, or custom.
- `prompt_summary`: short non-sensitive task summary.
- `observed_failure`: what actually went wrong.
- `failure_labels`: one or more controlled labels.
- `signals.hard`: machine-checkable signals.
- `signals.soft`: reviewer observations that are useful but not sufficient alone.
- `trace`: provider, model, latency, success signal, artifact status, and event-flow status.
- `expected_routing`: conservative routing decision.
- `evidence_required`: artifacts needed before the case can be trusted.
- `regression_guard_action`: guard action such as block, rollback, retry, or human review.

## Label Set

Use the narrowest labels that are supported by evidence.

| Label | Meaning | Minimum evidence |
| --- | --- | --- |
| `silent_failure` | The workflow looks finished, but a required step did not actually complete. | Missing event, missing artifact, or verifier contradiction. |
| `false_success` | The run reports success while evidence proves the target was not completed. | Success status plus failed verifier or stale/missing artifact. |
| `stale_artifact` | Output was reused from an older run. | Timestamp, run id, source hash, or archive mismatch. |
| `missing_event_trail` | The result lacks a parseable event trail. | Missing JSONL/trace or unreadable trace. |
| `provider_route_drift` | The actual model/provider differs from the intended route. | Expected route and actual route disagree. |
| `latency_regression` | Latency worsened beyond threshold. | Before/after latency metrics. |
| `success_rate_regression` | Success rate dropped beyond threshold. | Before/after success metrics. |
| `tool_call_noop` | A tool call returned ok but did not change the target state. | Tool result plus unchanged artifact/state. |
| `patch_without_test` | Code was changed without a verifier or test proving behavior. | Diff exists, no matching test/verifier evidence. |
| `context_drift` | Multi-turn repair no longer addresses the original task. | Original task and later action diverge. |
| `http_200_empty_output` | Provider returned HTTP 200 but the usable output was empty or unparsable. | HTTP status plus parse failure or empty content. |
| `rollback_missing` | Regression was detected but no rollback evidence exists. | Regression event without rollback event. |
| `config_patch_regression` | A config/prompt/tool patch made quality worse. | Before/after quality or rollback trigger. |
| `duplicate_request` | Same request hash/session was submitted twice and should be blocked. | Duplicate hash count or replay evidence. |
| `partial_output_truncation` | Output is cut off and cannot support a complete verdict. | Truncation marker, invalid JSON, or missing required section. |
| `artifact_hash_mismatch` | Review packet does not match the source artifact it claims to review. | Stored hash differs from recalculated hash. |
| `unsafe_action_escalation` | Learning/review output tries to authorize a risky action. | `trade_allowed`, `paper_buy_allowed`, `promote_allowed`, or equivalent set true. |
| `human_review_missing` | Human review was required but absent. | Review-required gate plus missing review artifact. |

## Routing Policy

Eval cases are not execution permission.

Allowed routing values:

- `learning_only`: safe to store as training/eval evidence only.
- `blocked`: cannot be used until missing evidence or hard failure is fixed.
- `manual_review_required`: human review can inspect it, but execution remains blocked.

Forbidden in eval packets:

- `judgment_allowed=true`
- `paper_buy_allowed=true`
- `trade_allowed=true`
- `promote_allowed=true`

If any forbidden flag appears in an eval packet, the packet verifier must return
`blocked`.

## Hard vs Soft Signals

Hard signals are machine-checkable and can block automatically:

- Missing artifact.
- Hash mismatch.
- Duplicate request hash.
- Provider/model mismatch.
- HTTP 200 with empty or invalid JSON.
- Event trail missing or unparsable.
- Test/verifier failure.

Soft signals require review and cannot promote alone:

- The answer feels off-topic.
- The patch looks risky.
- The wording is ambiguous.
- The model gave a plausible but unverified explanation.

## Training vs Eval vs Review

Use cases this way:

- Training candidate: stable label, safe content, no secrets, no execution authority.
- Eval case: deterministic expected route and required evidence are known.
- Human review: ambiguous, high-impact, or soft-signal-heavy cases.
- Blocked: missing evidence, unsafe action escalation, or corrupted event flow.

## Stop Rules

Stop and mark `blocked` when:

- The event trail is missing or unparsable.
- The source artifact is missing.
- A learning packet contains any execution authorization.
- The provider route cannot be verified.
- The case contains secrets or personal data.
- The case relies on a stale output as fresh evidence.

