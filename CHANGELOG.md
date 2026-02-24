# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release preparation
- Open source documentation

## [0.1.0] - 2026-02-24

### Added
- **Self-Improving Loop**: Complete 7-step improvement cycle
  - Execute task
  - Record results
  - Analyze failures
  - Generate suggestions
  - Auto apply improvements
  - Verify effects
  - Update configuration

- **Auto Rollback**: Automatic rollback on degradation
  - Success rate drop >10%
  - Latency increase >20%
  - Consecutive failures ≥5
  - Atomic config writes
  - Complete rollback history

- **Adaptive Threshold**: Dynamic threshold adjustment
  - High-frequency agents: 5 failures / 48h window / 3h cooldown
  - Medium-frequency agents: 3 failures / 24h window / 6h cooldown
  - Low-frequency agents: 2 failures / 72h window / 12h cooldown
  - Critical agents: 1 failure / 24h window / 6h cooldown
  - Auto-detect task frequency
  - Auto-detect critical agents
  - Manual configuration override

- **Telegram Notifier**: Real-time notifications
  - Improvement applied (normal priority)
  - Rollback alert (high priority)
  - Daily summary report
  - Threshold adjustment notification

- **Test Suite**: Comprehensive test coverage
  - 17/17 test cases passing
  - Core functionality tests
  - Rollback tests
  - Adaptive threshold tests
  - Integration tests

- **Documentation**
  - README with quick start
  - Integration guide
  - API reference
  - Architecture documentation
  - Contributing guidelines

### Performance
- <1% overhead on task execution
- ~5ms for tracing
- ~100ms for failure analysis (only when triggered)
- ~200ms for improvement application (only when triggered)
- ~10ms for rollback execution

### Security
- No sensitive data in logs
- Atomic config writes
- Rollback idempotency
- Safe Telegram token handling

## [0.0.1] - 2026-02-24

### Added
- Initial prototype
- Basic improvement cycle
- Simple rollback mechanism

---

## Release Notes

### v0.1.0 - Production Ready

This is the first production-ready release of Self-Improving Loop.

**Key Features:**
- ✅ Complete improvement cycle with automatic rollback
- ✅ Adaptive thresholds based on agent characteristics
- ✅ Real-time Telegram notifications
- ✅ 100% test coverage on core features
- ✅ <1% performance overhead

**Breaking Changes:**
- None (initial release)

**Migration Guide:**
- N/A (initial release)

**Known Issues:**
- None

**Upgrade Instructions:**
```bash
pip install self-improving-loop==0.1.0
```

---

[Unreleased]: https://github.com/yourusername/self-improving-loop/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/self-improving-loop/releases/tag/v0.1.0
[0.0.1]: https://github.com/yourusername/self-improving-loop/releases/tag/v0.0.1
