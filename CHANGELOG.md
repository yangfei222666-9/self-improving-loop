# Changelog

## 0.1.1

- Make the Yijing / hexagram-guided strategy the primary public entrypoint.
- Add terminal demo recording artifacts and README embed.
- Add bilingual launch copy for English and Chinese channels.
- Add restart-persistence assertions for SQLite traces and loop state.
- Add local release verification notes for wheel, sdist, CLI, and clean wheel install.
- Report rollback lookup/logging failures explicitly instead of returning silent `None`.
- Allow `YijingEvolutionStrategy.analyze(..., before_metrics=None)` for fresh agents.
- Keep `0.1.0` immutable on PyPI; publish the current release-ready package as `0.1.1`.

## 0.1.0

- Add `SelfImprovingLoop` runtime wrapper for execution tracking, adaptive thresholds, strategy-triggered patches, and rollback checks.
- Add `ConfigAdapter` for real config backup, patch, and rollback integration.
- Add JSONL trace storage with cross-process locking and optional SQLite/WAL trace storage.
- Add `YijingEvolutionStrategy` as a deterministic six-line / hexagram policy router.
- Add `self-improving-loop --version` CLI entrypoint for installation verification.
- Add smoke, rollback, example, SQLite, CLI, and Yijing strategy tests.
