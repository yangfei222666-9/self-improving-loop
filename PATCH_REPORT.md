# Patch Report · HN readiness surgery

Date: 2026-04-25

Scope: `self-improving-loop` only. No changes were made to `zhuge-skill`, `taiji`, or `taijios-bundle`.

## A · Self-contradictions

| Item | Before | After | Evidence |
|---|---|---|---|
| Overhead badge | Badge said generic `<1%` while README table says ~10 ms calls can be `+3.0%`. | Badge now says `LLM overhead <1%`, and README explicitly says to measure sub-10ms calls before wrapping. | README Performance section still preserves measured fixed-cost caveat. |
| Test count | Show HN draft had stale counts after adding CLI, alias, and Yijing entrypoint tests. | Draft says `40/40`. | `python3 -m pytest --collect-only -q` reports `40 tests collected`; `python3 -m pytest -q` reports `40 passed`. |
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
| Unit tests | `40 passed in 2.55s` |
| Test collection | `40 tests collected in 0.20s` |
| Compile | `python3 -m compileall -q self_improving_loop examples` passed |
| Editable install | `python3 -m pip install -e ".[dev]"` passed |
| CLI | `self-improving-loop --version` prints `self-improving-loop 0.1.0` |
| Clean venv install | `pip install -e .` passed; `pip freeze` showed only `self-improving-loop` |
| Wheel install | Built wheel installed in a clean venv and imported `SelfImprovingLoop` + `YijingEvolutionStrategy` |
| Build | `python -m build` produced both sdist and wheel |
| Twine | `twine check dist/*` passed |

## Follow-up · local release verification

| Check | Result |
|---|---|
| Isolated build tooling | Created a temporary venv and installed `build` + `twine`, because the host `python3` did not include `build`. |
| Build artifacts | `self_improving_loop-0.1.0-py3-none-any.whl` and `self_improving_loop-0.1.0.tar.gz` generated under `/tmp/self_improving_loop_release_verify_20260425_192345/dist`. |
| Metadata validation | `twine check` passed for both wheel and sdist. |
| Clean wheel install | Installed the wheel into `/tmp/self_improving_loop_install_verify_20260425_192424/venv`. |
| Installed CLI | `self-improving-loop --version` printed `self-improving-loop 0.1.0`. |
| Installed import/API | `SelfImprovingLoop(strategy=YijingEvolutionStrategy())` imported and executed successfully; installed object stores the hook as `improvement_strategy`. |
| TestPyPI credentials | `TWINE_USERNAME`, `TWINE_PASSWORD`, `TWINE_REPOSITORY_URL`, `TEST_PYPI_API_TOKEN`, and `PYPI_TOKEN` were all missing, so remote TestPyPI upload remains blocked. |

## Blocked / not executed

| Item | Status |
|---|---|
| TestPyPI upload | Blocked: no `PYPI` / `TWINE` credentials are present in the environment, and no token was used from chat history. |
| Demo GIF/asciinema | Done as local demo artifacts: SVG terminal card, asciinema-compatible `.cast`, and transcript under `assets/demo/`. |
| `LoopResult` dataclass | Not done. The current dict contract remains stable; changing result type before HN would be higher API risk than adding the safe `track()` alias. |

## Follow-up · Yijing positioning/API alignment

| Item | Before | After | Evidence |
|---|---|---|---|
| Public positioning | Generic rollback-first reliability loop. | Hexagram-guided reliability loop with the rollback guard still central. | README top line and `pyproject.toml` description updated. |
| Constructor API | Only `improvement_strategy=` was documented as the strategy hook. | Added preferred `strategy=` alias while keeping `improvement_strategy=` compatible. | `tests/test_smoke.py::test_strategy_alias_is_preferred_entrypoint`. |
| Duplicate strategy args | Passing both names was ambiguous. | Raises `ValueError`. | `tests/test_smoke.py::test_strategy_alias_rejects_duplicate_strategy_args`. |
| Yijing example | Used legacy `improvement_strategy=`. | Uses `strategy=YijingEvolutionStrategy(...)`. | `examples/04_yijing_strategy.py`. |

## Follow-up · bilingual launch material

| Item | Before | After | Evidence |
|---|---|---|---|
| Chinese launch copy | No dedicated Chinese or bilingual material. | Added `LAUNCH_COPY_BILINGUAL.md` with English and Chinese positioning, demo script, short posts, HN boundary, safe claims, and claims to avoid. | README links to `LAUNCH_COPY_BILINGUAL.md`. |
| Overclaim guard | Launch wording could drift between English and Chinese channels. | Both languages explicitly say the Yijing layer is experimental, deterministic, and not full 64-hexagram coverage yet. | `LAUNCH_COPY_BILINGUAL.md` sections 6 and 7. |

## Follow-up · persistence evidence

| Item | Before | After | Evidence |
|---|---|---|---|
| Test framing | `tests/test_smoke.py` still described the suite as minimal and partially unported. | Updated the header to match current safety-path coverage. | `tests/test_smoke.py`. |
| Restart persistence | SQLite trace and loop state persistence were implied but not explicitly asserted in restart-style tests. | Added assertions that SQLite traces and improvement backup state survive a new `SelfImprovingLoop` instance. | `tests/test_smoke.py`; test count remains `40`. |

## Follow-up · demo recording

| Item | Before | After | Evidence |
|---|---|---|---|
| README visual proof | README checklist asked for screenshot/asciinema, but no recording artifact existed. | Added a terminal SVG demo plus transcript and asciinema-compatible cast. | `assets/demo/self_improving_loop_demo.svg`, `.txt`, `.cast`; README embeds the SVG. |
| Local path leakage | Raw command output included temp directories. | Demo artifacts use sanitized `/tmp/sil_demo_*` paths. | Sensitive-path grep is clean. |
