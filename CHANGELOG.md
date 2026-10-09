# Changelog

All notable changes to FateBridge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version is single-sourced from `src/fatebridge/__init__.py::__version__`.
A version bump updates package metadata; PyPI publication is triggered separately
by a published GitHub Release through `.github/workflows/publish.yml`.

## [Unreleased]

### Changed
- Align integration, architecture, security, and Onda documentation with the
  current catalog and request models: distinguish transport bindings, document
  REST projections and 422 errors, and clarify installation, solar-time defaults
  and actual ephemeris precision. Simplify contribution steps and add a
  documentation maintenance and verification workflow.

- **Adopt the PyPA-recommended `src/` layout** (`fatebridge/` → `src/fatebridge/`).
  The package is no longer importable from the repo root without installing it,
  so a bare `pytest`/`import` runs against the *installed* package — packaging
  gaps (like the missing data files fixed in 0.2.0) now fail locally instead of
  only after `pip install`. Import name, wheel contents, and the three console
  scripts are unchanged. Repo-root-relative lookups (`.env`, `ephe/`) had their
  parent-index depth bumped so they still resolve to the repo root.

### Added
- `[project.urls]` (Homepage / Repository / Issues / Changelog) so the PyPI
  project page links back to the repository.
- `Typing :: Typed` and `Topic ::` classifiers.

### Removed
- `requirements.txt`, which duplicated `[project.dependencies]` with no check
  against drift. Docs now point at `pip install -e .` / `pip install fatebridge`.

### Fixed
- Preserve the actual selected Liu Ren lesson through transmission selection,
  so duplicate upper gods cannot mislabel 发用 or change Jin Kou 用神.
- Correct lunar month lengths in 1933, 1954 and 1978 without mutating the
  dependency's global tables; all 73,058 supported solar dates now agree with
  sxtwl. Cache immutable lunar-date values for repeated calendar requests.
- Resolve Zi Wei ages and flowing palaces using lunar boundaries and natal
  month/hour rotation, including childhood and leap-month handling. Expose
  calendar conventions and distinguish palace stems from transformation stems.
- Replace simplified Liu Ren transmission selection with the nine-method
  rules, use the day stem's element in the first lesson, and place generals
  using the nobleman's earthly position (including the 戌 reverse boundary).
- Include the equation of time in shared apparent-solar analysis inputs,
  bringing Qi Men / Liu Ren / Tai Yi / Jin Kou into agreement with birth inputs.
- Replace the Zi Wei oracle's calendar-branch comparison with actual active
  palaces; add pinned independent calendar and Liu Ren regression fixtures.
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
