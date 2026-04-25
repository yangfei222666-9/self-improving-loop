# Changelog

## 0.1.0

- Add `SelfImprovingLoop` runtime wrapper for execution tracking, adaptive thresholds, strategy-triggered patches, and rollback checks.
- Add `ConfigAdapter` for real config backup, patch, and rollback integration.
- Add JSONL trace storage with cross-process locking and optional SQLite/WAL trace storage.
- Add `YijingEvolutionStrategy` as a deterministic six-line / hexagram policy router.
- Add `self-improving-loop --version` CLI entrypoint for installation verification.
- Add smoke, rollback, example, SQLite, CLI, and Yijing strategy tests.
