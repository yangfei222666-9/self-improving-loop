# PR Scope Split Review

Status: `read_only_review_complete`

Recorded: `2026-05-17T16:29:14+08:00`

Repo: `/Users/weiwei/Desktop/self-improving-loop`

## Current Git State

- Branch: `main...origin/main`
- Staged files: `0`
- Tracked modified files: `14`
- Untracked candidate files: `9`
- Dry-run stage candidates after this review: `24`

## Recommendation

Use one local PR/commit for this batch:

```text
build: productize distribution and demo packaging
```

Reason: the files are coupled by verification gates:

- `README.md` points to `demo/huggingface_space/`.
- `MANIFEST.in` is needed so the demo source appears in the source distribution.
- CI/publish compile gates were extended to include `demo`.
- Benchmark fixes are covered by the new benchmark test and README benchmark command.
- Formatter-only changes were required by the repo's own pre-commit gate.
- `runs/ops_check/...` is the audit package for the same local PR scope.

## If Split Into Smaller PRs

Split only if the goal is contribution graph granularity, not engineering
simplicity.

### PR A: Release / Publish Workflow

Files:

- `.github/workflows/publish.yml`
- `.github/workflows/ci.yml`
- `docs/RELEASE_PROCESS.md`

Risk: README and demo claims would still be incomplete until PR B lands.

### PR B: README + Demo Distribution

Files:

- `README.md`
- `.gitignore`
- `MANIFEST.in`
- `demo/huggingface_space/README.md`
- `demo/huggingface_space/app.py`
- `demo/huggingface_space/requirements.txt`
- `tests/test_huggingface_space_demo.py`

Risk: depends on PR A if CI/publish should compile the demo in automation.

### PR C: Benchmark / Example Gate Hardening

Files:

- `benchmarks/overhead.py`
- `benchmarks/startup_recovery.py`
- `tests/test_benchmarks.py`
- `examples/06_hermes_skill_regression_guard.py`
- `examples/regression_rollback_demo.py`
- `examples/verify_agent_eval_cases.py`
- `examples/verify_regression_rollback_event_trail.py`
- `tests/test_agent_eval_cases.py`
- `tests/test_examples.py`

Risk: formatter-only changes are noisy if separated from the pre-commit gate
that required them.

### PR D: Audit Artifacts

Files:

- `runs/ops_check/product_distribution_pr4_pr7_20260517/PRODUCT_DISTRIBUTION_CLOSEOUT.md`
- `runs/ops_check/product_distribution_pr4_pr7_20260517/PR_SCOPE_SPLIT_REVIEW.md`
- `runs/ops_check/product_distribution_pr4_pr7_20260517/STAGE_AUTHORIZATION_PACKET.md`
- `runs/ops_check/product_distribution_pr4_pr7_20260517/event_flow.jsonl`
- `runs/ops_check/product_distribution_pr4_pr7_20260517/summary.json`

Risk: keeping audit artifacts outside the PR weakens the TaijiOS evidence
contract. Keeping them inside the same PR is preferable for this project.

## Boundary

No git mutation was performed while creating this review. Real staging still
requires explicit user authorization.
