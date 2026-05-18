# Release Process

This project uses GitHub Releases as the primary public distribution path.
PyPI publishing is automated only after PyPI Trusted Publishing is configured.

## Pre-release checks

```bash
python -m pytest -q
python -m compileall -q self_improving_loop examples benchmarks demo tests
python -m build
python -m twine check dist/*
pre-commit run --all-files
```

## GitHub release path

1. Update version metadata and changelog.
2. Build wheel and sdist locally.
3. Create a GitHub release and attach both artifacts.
4. Verify a clean install from the release artifact.

## PyPI publish path

The `Publish` workflow builds on every manual run, `v*` tag push, and published
GitHub Release. It publishes to PyPI only for release/tag events.

Required PyPI setup before tag publishing:

- Configure PyPI Trusted Publishing for this repository.
- Environment name: `pypi`.
- Workflow file: `.github/workflows/publish.yml`.
- Project name: `self-improving-loop`.

Do not store PyPI API tokens in the repository or GitHub Actions logs. The
workflow uses PyPI Trusted Publishing instead of a `PYPI_API_TOKEN` secret.

## Version selection notes

- `v0.1.1` is an existing GitHub Release tag that points to commit
  `11676025c8087e5fa2b79060bb9f2b6868db0720`.
- PyPI still has only `0.1.0`, so do not try to republish `0.1.1` from a
  different commit.
- Use `0.1.2` for the next PyPI publish attempt after Trusted Publishing is
  configured.
