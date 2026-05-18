# Release Readiness · self-improving-loop v0.1.2

Status: `local_prep`
Recorded: `2026-05-18`

## Scope

- Package: `self-improving-loop`
- Target version: `0.1.2`
- Release path: GitHub tag / release followed by the `Publish` workflow
- PyPI project: `self-improving-loop`

## Why 0.1.2

`v0.1.1` already exists as a GitHub Release and points to commit
`11676025c8087e5fa2b79060bb9f2b6868db0720`. PyPI currently exposes only
`0.1.0`, and PyPI version files are immutable once uploaded. The next publish
attempt should therefore use a new version, `0.1.2`, instead of trying to
reuse `0.1.1` from a different commit.

## Local Prep

- `pyproject.toml` version is `0.1.2`.
- `self_improving_loop.__version__` is `0.1.2`.
- `CHANGELOG.md` includes a `0.1.2` entry.
- `docs/RELEASE_PROCESS.md` covers the demo compile gate.

## Required Before Publishing

- Configure PyPI Trusted Publishing for this GitHub repository.
- Ensure the PyPI environment name is `pypi`.
- Create a fresh `v0.1.2` tag or GitHub Release only after the version bump is
  merged to `main`.
- Let `.github/workflows/publish.yml` publish from the tag or published release.

## Hard Stops

- Do not upload distributions manually from this local checkout.
- Do not create a `v0.1.2` tag before the version bump is committed and merged.
- Do not treat the existing `v0.1.1` release as proof that PyPI `0.1.1` is live.
