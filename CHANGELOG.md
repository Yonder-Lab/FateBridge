# Changelog

All notable changes to FateBridge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version is single-sourced from `src/fatebridge/__init__.py::__version__`.
A version bump updates package metadata; PyPI publication is triggered separately
by a published GitHub Release through `.github/workflows/publish.yml`.

## [Unreleased]

### Added

- 补齐九类八字专题、宿曜双向关系、知识目录/来源/查询及导出模板/动态设置/分段的嵌套输出合同，并复用到各工具 snapshot_export；严格校验保持可空事实、扩展字段、部分投影及既有整数/浮点数原样输出。

- 专业输出补齐主限坐标与命中、递归时主、寿限、古典/关系盘及中国术数的嵌套合同；三端共用校验和发现 schema，保留动态键、扩展字段、可空事实、部分投影及既有数值。嵌套类型违规在投影前按内部失败处理。
- 场景 manifest 从既有 8 个技能 YAML 与住宅路由生成，REST `/api/scenarios`、CLI `scenarios`、MCP resources 共用；工具发现支持 scenario 筛选，可选 MCP scenario profile 与 family 取交集。
- 共享调用上下文支持 as_of / trace_id / parent_run_id；固定默认时间，保留显式日期、时区和手动起卦优先级，随机六爻记录本次 seed。
- 成功元数据增加格式/包版本、输入/合同/业务输出摘要、环境及数据指纹、耗时、口径和 replay 参数。新增字段可选，旧基础字段和 CLI --no-metadata 保留；有效标识传播到领域与校验失败，CLI profile 建立根/子关联。

- 玄空宅盘 `fengshui_xuankong_natal`（中州派 v1）：历史事件定运、24山／三元龙、五黄同元龙借运、下卦与兼向替星，分界和测量误差返回候选；REST/MCP/CLI 共用合同，合参与年度飞星分层。登记规则出处、网页版本和笔误范围，新增独立公开盘例及固定第三方比对差异记录。
- Six residential Feng Shui tools across REST, MCP and CLI: fixed directions,
  personal Ming Gua, sitting-trigram Eight Mansions, basic Jin Suo sand/water,
  annual Zi Bai stars and layered assessment. Versioned source registry,
  per-person results, explicit partial coverage and scoped differences are
  preserved; Xuan Kong natal charts are recorded in the separate entry above.
- Opt-in JSON `--request-file` and nested JSON flags for residential tools,
  shared layered output schemas, factual snapshots, offline independent
  reference fixtures and three-transport contract tests.

### API compatibility notes
- Native MCP result construction now validates the protocol dictionary across
  SDK 1.x and 2.x constructor naming conventions. Linux x86_64 / Python 3.12
  reference validation completes all golden comparisons without skips.
- Feng Shui `Ruleset` output fields now permit omission in dotted projections;
  native MCP clients can validate single-rule-field results. Full results and
  rule versions are preserved; catalog-wide projection regression checks cover
  nested objects, arrays and the REST/MCP/CLI schemas.
- Invalid projection paths now return additive `projection_warnings` while
  retaining the existing selected data and success status by default. Opt in to
  `strict_fields=true` (CLI `--strict-fields`) for shared 422 validation failures.
- Progressive discovery adds summary/filter/single-tool views to `/api/tools`,
  JSON `discover` / `list --json` CLI commands, and MCP catalog resources. REST
  defaults to full records; existing CLI text listings and `describe` remain.
  `FATEBRIDGE_MCP_FAMILIES` optionally narrows the registered MCP tools.
- MCP execution annotations derive from the same catalog hints exposed by REST
  and CLI. These describe environmental effects, not deterministic output.
- Requests now reject unknown fields and invalid civil dates with safe field-level
  `issues`. Explicit invalid election topics and horary categories are rejected;
  omitted selectors retain their defaults. Remove previously ignored fields from
  ordinary tool requests; CLI subject profiles still select fields for each tool.
- MCP errors now set native `isError=true`. FastMCP Client callers that inspect
  error payloads must use `raise_on_error=False`; successful text JSON remains
  available alongside structuredContent.
- All catalog tools publish projection-compatible output schemas. REST documents
  API Key authentication and error statuses, and uses stable catalog operationIds.
  Successful JSON shapes are preserved; schema-validation errors use 422 across
  REST/MCP/CLI. CLI command syntax errors retain exit 2 / usage_error.

### Changed
- Cache default model schemas and contract fingerprints with bounded, model-identity
  and rebuild-aware entries; public schemas remain independent copies and business
  executions are never cached. Remove the redundant third REST output validation.
- Build native MCP structured results directly from response dictionaries and
  initialize legacy Python adapters synchronously. Keep existing Python aliases,
  REST/MCP/CLI contracts and numerical behavior; move internal imports and transport
  tests to canonical modules and native registration paths.
- Remove the obsolete `iztro-verify` extra, unused imports and private parameters,
  unreachable compatibility error forwarding and repeated export-section mapping.
  Bind documented CLI example tests to their test interpreter and refresh document
  navigation and maintenance guidance.
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
