# Patch Report · HN readiness surgery

Date: 2026-04-25

Scope: `self-improving-loop` only. No changes were made to `zhuge-skill`, `taiji`, or `taijios-bundle`.

## A · Self-contradictions

| Item | Before | After | Evidence |
|---|---|---|---|
| Overhead badge | Badge said generic `<1%` while README table says ~10 ms calls can be `+3.0%`. | Badge now says `LLM overhead <1%`, and README explicitly says to measure sub-10ms calls before wrapping. | README Performance section still preserves measured fixed-cost caveat. |
| Test count | Show HN draft had stale `36/36` after adding CLI and alias tests. | Draft says `38/38`. | `python3 -m pytest --collect-only -q` reports `38 tests collected`; `python3 -m pytest -q` reports `38 passed`. |
| Ising hook | README wording implied this package itself survived the Ising experiment. | Wording now says it is extracted from TaijiOS, which includes the Ising experiment and production-scale workloads. | README top section changed. |
| Hard-coded day count | Show HN draft and README had date deltas that age badly. | Copy now anchors on `Chinese New Year 2026-02-17` without hard-coded `60 days` deltas. | README Background and SHOW_HN_DRAFT body changed. |

## B · Packaging metadata

| Item | Before | After | Evidence |
|---|---|---|---|
| Author metadata | `authors = [{ name = "TaijiOS" }]`. | `TaijiOS maintainers` plus GitHub noreply-style email. | `pyproject.toml`. |
| Development status | `4 - Beta`. | `3 - Alpha`. | `pyproject.toml`. |
| License metadata | `license = { file = "LICENSE" }` plus old license classifier. | `license = "MIT"` and removed superseded classifier. | Editable install initially failed until classifier was removed; now build passes. |
| Package discovery | Hard-coded package list. | `tool.setuptools.packages.find` with `include = ["self_improving_loop*"]`. | Build includes `self_improving_loop.yijing` and CLI. |
| CLI | No console script. | `self-improving-loop --version`. | Clean venv and wheel install both print `self-improving-loop 0.1.0`. |
| Keywords/topics | PyPI keywords and GitHub topics could drift. | PyPI keywords expanded to include `ai-agents`, `rollback`, `autonomous-agents`. | `pyproject.toml`; existing GitHub topics already include the same core terms. |

## Extra high-ROI fixes

| Item | Change |
|---|---|
| CI badge | Added dynamic GitHub Actions badge to README. |
| PyPI badge | Replaced hard-coded `0.1.0` badge with dynamic PyPI version badge. |
| Framework-war prevention | Moved `Not a...` section to the second screen, immediately after install. |
| Threshold clarity | Added `exec_count_24h` explanation and manual override pointer. |
| Short API alias | Added `loop.track(...)` as an alias for `execute_with_improvement(...)`. |
| HN operating checklist | Added first-24h comment-response checklist. |
| Changelog | Added `CHANGELOG.md` with 0.1.0 entry. |
| Source package materials | Added `MANIFEST.in` so sdist includes `CHANGELOG.md` and repo examples. |

## Validation

| Check | Result |
|---|---|
| Unit tests | `38 passed in 1.81s` |
| Test collection | `38 tests collected in 0.06s` |
| Compile | `python3 -m compileall -q self_improving_loop examples` passed |
| Editable install | `python3 -m pip install -e ".[dev]"` passed |
| CLI | `self-improving-loop --version` prints `self-improving-loop 0.1.0` |
| Clean venv install | `pip install -e .` passed; `pip freeze` showed only `self-improving-loop` |
| Wheel install | Built wheel installed in a clean venv and imported `SelfImprovingLoop` + `YijingEvolutionStrategy` |
| Build | `python -m build` produced both sdist and wheel |
| Twine | `twine check dist/*` passed |

## Blocked / not executed

| Item | Status |
|---|---|
| TestPyPI upload | Blocked: no `PYPI` / `TWINE` credentials are present in the environment, and no token was used from chat history. |
| Demo GIF/asciinema | Not done in this patch; README now has stronger executable examples, but no recording artifact yet. |
| `LoopResult` dataclass | Not done. The current dict contract remains stable; changing result type before HN would be higher API risk than adding the safe `track()` alias. |
