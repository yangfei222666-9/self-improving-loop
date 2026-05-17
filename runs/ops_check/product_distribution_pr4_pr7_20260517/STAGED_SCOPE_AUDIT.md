# Staged Scope Audit

Status: `pass`

Recorded: `2026-05-17T16:38:30+08:00`

Branch: `product/distribution-demo-pypi`

## Authorized Scope

Authorized by user:

```text
允许创建本地分支、git add、commit，不 push
```

Allowed actions performed:

- local branch creation
- `git add`

Still forbidden:

- push
- tag
- release
- PR creation
- PyPI upload
- Hugging Face Space creation
- secret read/export

## Staged Files

Staged before this audit artifact: `25`

```text
.github/workflows/ci.yml
.github/workflows/publish.yml
.gitignore
MANIFEST.in
README.md
benchmarks/overhead.py
benchmarks/startup_recovery.py
demo/huggingface_space/README.md
demo/huggingface_space/app.py
demo/huggingface_space/requirements.txt
docs/RELEASE_PROCESS.md
examples/06_hermes_skill_regression_guard.py
examples/regression_rollback_demo.py
examples/verify_agent_eval_cases.py
examples/verify_regression_rollback_event_trail.py
runs/ops_check/product_distribution_pr4_pr7_20260517/BLOCKED_GIT_STAGE_20260517.md
runs/ops_check/product_distribution_pr4_pr7_20260517/PRODUCT_DISTRIBUTION_CLOSEOUT.md
runs/ops_check/product_distribution_pr4_pr7_20260517/PR_SCOPE_SPLIT_REVIEW.md
runs/ops_check/product_distribution_pr4_pr7_20260517/STAGE_AUTHORIZATION_PACKET.md
runs/ops_check/product_distribution_pr4_pr7_20260517/event_flow.jsonl
runs/ops_check/product_distribution_pr4_pr7_20260517/summary.json
tests/test_agent_eval_cases.py
tests/test_benchmarks.py
tests/test_examples.py
tests/test_huggingface_space_demo.py
```

This audit file is added after that count, so the final staged count for the
commit is expected to be `26`.

## Verification

- `git diff --cached --check`: pass
- `git diff --name-only`: empty after restaging fixed imports
- `.venv/bin/pre-commit run --all-files`: pass
- `python3 -m compileall -q self_improving_loop examples benchmarks demo tests`: pass
- `python3 -m pytest -q`: `69 passed`
- `summary.json` / `event_flow.jsonl`: parseable

## Notes

The first staged pre-commit run found import-order fixes in new demo/test
files. `ruff check --fix` repaired them, and those files were restaged before
this audit.
