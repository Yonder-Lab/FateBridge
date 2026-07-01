# Changelog

All notable changes to FateBridge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Because the version is single-sourced from `fatebridge/__init__.py::__version__`,
bumping that constant is the release action.

## [Unreleased]

### Added
- `[project.urls]` (Homepage / Repository / Issues / Changelog) so the PyPI
  project page links back to the repository.
- `Typing :: Typed` and `Topic ::` classifiers.

### Removed
- `requirements.txt`, which duplicated `[project.dependencies]` with no check
  against drift. Docs now point at `pip install -e .` / `pip install fatebridge`.

### Fixed
- README status badge and "项目状态" section said Alpha `0.1.0`; corrected to
  Beta `0.2.0` to match the `Development Status` classifier.

## [0.2.0] - 2026-07-01

First packaging-hardening release: the distribution is now installable and
usable from a wheel (previously the reference-data JSON was omitted, so several
engines crashed at runtime after `pip install`).

### Fixed
- **Ship reference data in the wheel/sdist.** Declared
  `[tool.setuptools.package-data]` so `fatebridge/data/**/*.json`
  (canping / heluo / knowledge stores) is packaged. Without it an installed
  wheel raised `FileNotFoundError` because the engines load these files via
  `Path(__file__).parents[1] / "data" / ...` at runtime.

### Added
- **PEP 561 typed marker** (`fatebridge/py.typed`) so downstream mypy / IDEs
  consume the package's inline type hints.
- `SECURITY.md` disclosure policy and a `publish.yml` GitHub Actions workflow
  that publishes to PyPI via Trusted Publishing (OIDC, no API tokens).
- `__all__` and a "Public API" note in the top-level package docstring.

### Changed
- Version `0.1.0` → `0.2.0`; `Development Status` classifier `3 - Alpha`
  → `4 - Beta` to reflect the stabilized, CI-locked API.
- Migrated license metadata to the PEP 639 form: SPDX `license = "Apache-2.0"`
  + `license-files = ["LICENSE", "NOTICE"]`, dropping the deprecated
  `License :: OSI Approved ::` classifier. `build-system` now requires
  `setuptools>=77.0.0` (first version to support the SPDX expression).

## [0.1.0] - initial

- Initial FateBridge engine: 80 tools across 13 families exposed over three
  transports (FastAPI REST, FastMCP, `fatebridge` CLI) from a single central
  tool catalog. Golden-master numeric locks and a 4-version CI matrix.

[Unreleased]: https://github.com/Yonder-Lab/FateBridge/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Yonder-Lab/FateBridge/releases/tag/v0.2.0
[0.1.0]: https://github.com/Yonder-Lab/FateBridge/releases/tag/v0.1.0
