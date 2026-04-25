# Release Process

This project uses GitHub Releases as the primary public distribution path.
PyPI publishing is automated only after PyPI Trusted Publishing is configured.

## Pre-release checks

```bash
python -m pytest -q
python -m compileall -q self_improving_loop examples benchmarks
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

The `Publish` workflow builds on every manual run and tag push. It publishes to
PyPI only on `v*` tag pushes.

Required PyPI setup before tag publishing:

- Configure PyPI Trusted Publishing for this repository.
- Environment name: `pypi`.
- Workflow file: `.github/workflows/publish.yml`.
- Project name: `self-improving-loop`.

Do not store PyPI API tokens in the repository or GitHub Actions logs.
