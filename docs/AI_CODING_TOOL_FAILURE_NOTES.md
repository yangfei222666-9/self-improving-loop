# AI Coding Tool Failure Notes

This note maps common Claude Code, Cursor, OpenClaw, Hermes, and custom coding
agent failures into trace fields, failure labels, and guard actions.

The package should be positioned as a reliability layer around these tools, not
as a replacement for them.

## Core Pattern

```text
agent action -> trace -> failure label -> verifier -> rollback or block
```

The important question is not whether the tool produced code. The important
question is whether the task is complete, tested, and recoverable.

## Common Failure Modes

| Failure mode | Label | Guard action |
| --- | --- | --- |
| Patch generated but no matching test ran. | `patch_without_test` | Block promote; require verifier. |
| Tool call says ok but file/state is unchanged. | `tool_call_noop` | Re-read target state; retry or block. |
| Multi-turn repair drifts away from the original issue. | `context_drift` | Re-anchor to original task and stop current branch. |
| Provider changes from intended model to fallback without disclosure. | `provider_route_drift` | Mark blocked until route is verified. |
| Agent output is truncated or invalid JSON. | `partial_output_truncation` | Retry with bounded prompt or mark degraded. |
| HTTP 200 response contains empty content. | `http_200_empty_output` | Treat as failure, not ok. |
| Generated artifact is older than the current run. | `stale_artifact` | Block success claim; require fresh run id/hash. |
| Review packet points to a different source artifact. | `artifact_hash_mismatch` | Block review; regenerate packet. |
| Agent repeats the same request hash. | `duplicate_request` | Stop replay and record duplicate evidence. |
| Regression detected but no rollback event exists. | `rollback_missing` | Block; require restore evidence. |
| Learning output tries to authorize trade/promote/deploy. | `unsafe_action_escalation` | Hard block. |

## Mapping to self-improving-loop

`self-improving-loop` already provides the runtime seam:

- Trace each callable execution.
- Track success rate and latency.
- Trigger a strategy hook when failure patterns cross a threshold.
- Apply a guarded config patch.
- Roll back when the patch regresses quality.
- Preserve an event trail for audit.

The eval packet layer adds the missing data strategy layer:

- Convert traces into failure labels.
- Separate hard signals from soft reviewer observations.
- Decide whether the case is `learning_only`, `blocked`, or `manual_review_required`.
- Prevent eval data from becoming execution authority.

## Tool-Specific Notes

### Claude Code / Cursor

Typical risk: patch quality appears high, but the actual task may be unverified.

Minimum guard:

- Record changed files.
- Record tests/verifiers run.
- Record stdout/stderr.
- Recalculate artifact hashes after patch.
- Block if no test or verifier maps to the change.

### OpenClaw

Typical risk: a tool route is available in configuration but not actually
healthy at runtime.

Minimum guard:

- Probe gateway health before trusting tool availability.
- Record actual route, version, and failure reason.
- Treat configured-but-unreachable tools as blocked, not degraded.

### Hermes / Skill Runtimes

Typical risk: skill config changes can degrade output while still returning a
formally successful result.

Minimum guard:

- Store previous skill config.
- Run a baseline task.
- Apply the candidate patch.
- Compare quality and latency.
- Roll back if worse.
- Verify event trail contains restore evidence.

## Non-Goals

This note does not claim model training, RL, or autonomous self-improvement.
Before those claims are valid, the system needs sustained runs, accumulated
cases, real promote/demote/archive behavior, and at least one learned rule that
changes future behavior under audit.

