# Stage Authorization Packet

Status: `authorized_local_branch_stage_commit_no_push`

Created: `2026-05-17T16:28:07+08:00`

Repo: `/Users/weiwei/Desktop/self-improving-loop`

## Boundary

This packet does not authorize staging by itself. It exists so the human can
confirm the exact staging scope.

Authorization received at `2026-05-17T16:37:22+08:00` for local branch
creation, `git add`, and commit only. Push, tag, release, PyPI upload, and
Hugging Face Space creation remain blocked.

## Recommended Branch

```bash
git switch -c product/distribution-demo-pypi
```

This changes local git branch state, so it still requires explicit user
confirmation before execution.

## Recommended Stage Command

Use explicit paths instead of `git add .`:

```bash
git add \
  .github/workflows/ci.yml \
  .github/workflows/publish.yml \
  .gitignore \
  MANIFEST.in \
  README.md \
  benchmarks/overhead.py \
  benchmarks/startup_recovery.py \
  demo/huggingface_space/README.md \
  demo/huggingface_space/app.py \
  demo/huggingface_space/requirements.txt \
  docs/RELEASE_PROCESS.md \
  examples/06_hermes_skill_regression_guard.py \
  examples/regression_rollback_demo.py \
  examples/verify_agent_eval_cases.py \
  examples/verify_regression_rollback_event_trail.py \
  runs/ops_check/product_distribution_pr4_pr7_20260517/PRODUCT_DISTRIBUTION_CLOSEOUT.md \
  runs/ops_check/product_distribution_pr4_pr7_20260517/STAGE_AUTHORIZATION_PACKET.md \
  runs/ops_check/product_distribution_pr4_pr7_20260517/event_flow.jsonl \
  runs/ops_check/product_distribution_pr4_pr7_20260517/summary.json \
  tests/test_agent_eval_cases.py \
  tests/test_benchmarks.py \
  tests/test_examples.py \
  tests/test_huggingface_space_demo.py
```

## Recommended Commit

```bash
git commit -m "build: productize distribution and demo packaging"
```

Commit also requires explicit user confirmation.

## Verified Gates

- `pre-commit run --all-files`: pass
- `python3 -m pytest -q`: `69 passed`
- `python3 -m compileall -q self_improving_loop examples benchmarks demo tests`: pass
- build + `twine check`: pass
- `git diff --check`: pass
- `summary.json` + `event_flow.jsonl`: parseable
- current `staged_count`: `0`

## External Publish Blockers

- PyPI publish is blocked until user confirms release/tag publishing and PyPI
  Trusted Publishing readiness.
- Hugging Face Space public URL is blocked until user confirms creating or
  uploading to a public external Space.
