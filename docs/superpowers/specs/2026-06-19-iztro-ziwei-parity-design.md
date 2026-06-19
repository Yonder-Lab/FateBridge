# Design: iztro-grade 紫微斗数 (Zi Wei Dou Shu) for FateBridge

- **Date:** 2026-06-19
- **Status:** Approved (design); pending implementation plan
- **Author:** thomas-yanxin (with Claude)
- **Source capability:** [SylarLong/iztro](https://github.com/SylarLong/iztro) (TypeScript, 紫微斗数)

## 1. Background & Goal

FateBridge already ships a native-Python 紫微斗数 engine: `build_ziwei_chart()`
in `fatebridge/core/metaphysics.py` (≈1598–2115), surfaced as the
`ziwei_birth` and `ziwei_rules` tools via the central `tool_catalog.py`. Its
code comments already cite iztro as the reference for palace ordering and 四化.

The existing engine is **more complete than a skeleton**. It already:

- places the 14 主星 (紫微/天府 groups),
- places 辅星 (左辅 右弼 文昌 文曲),
- places 煞星 (擎羊 陀罗 火星 铃星 地空 地劫 禄存 天魁 天钺 天马),
- places a broad 杂星 set (红鸾 天喜 孤辰 寡宿 破碎 蜚廉 天官 天福 天厨 天月
  天刑 天姚 天巫 解神 阴煞 华盖 咸池 …),
- computes 四化 (`sihua`) from the birth-year stem,
- computes 五行局 and static 大限 age ranges,
- returns `{ ming_gong, shen_gong, wuxing_ju, sihua, palaces, year_stem, engine }`.

**The genuine gaps versus iztro are three additive layers** — none of which
require changing the existing star-placement math:

1. **Star brightness** (庙 / 旺 / 得 / 利 / 平 / 不 / 陷) per placed star.
2. **Horoscope cycles** — an *active* time-travel view: which palace is the
   current 大限 / 小限 / 流年 / 流月 / 流日 / 流时 for a target date, plus the
   **dynamic 四化** each period's stem triggers.
3. **Palace relationships** — 对宫 (opposite) and 三方四正 (trine + opposition)
   as structured data, plus an agent-facing query helper (iztro's chained
   `star('紫微').surroundedPalaces().haveMutagen('忌')` expressed as data + a
   convenience tool, rather than a fluent JS API).

**Goal:** bring the native engine to iztro feature-parity, delivered in three
phased PRs, all **pure-Python / offline**, all flowing through `tool_catalog.py`
so CLI / REST / MCP stay auto-synced and `describe`-introspectable.

## 2. Design Decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Integration approach | **Native Python port** | Stays offline, single-engine, auditable against iztro's source tables; matches pure-Python/accuracy stance. No JS runtime at runtime. |
| Scope & delivery | **Full parity, phased** (3 PRs, Tier 1→2→3) | One responsibility per PR; small CI gates; matches the established PR workflow. |
| Accuracy anchor | **py-iztro as dev/test-only dependency** | Generate ground-truth fixtures once, commit JSON, assert pure-Python output matches. Runtime stays pure-Python; cross-checks are automated and regenerable. |
| Tier 3 surface | **Embed relationship data + `ziwei_palace_query` tool** | Most agent-friendly: relationships as data in the payload, plus a convenience query tool mirroring iztro's query power. |
| Payload evolution | **Additive, backward-compatible** | `palaces[].stars: [str]` and all current keys are preserved; new info lands in parallel fields so existing snapshot_text + contract tests stay green. |

## 3. Architecture

New/changed files:

```
fatebridge/core/ziwei_tables.py        # NEW — iztro-sourced lookup tables (brightness, etc.)
fatebridge/core/metaphysics.py         # extend build_ziwei_chart (Tier 1 + Tier 3 data)
                                        # add build_ziwei_horoscope (Tier 2)
                                        # add ziwei palace-relationship + query helpers (Tier 3)
fatebridge/core/request_models.py      # add ZiweiHoroscopeRequest, ZiweiPalaceQueryRequest
fatebridge/services/metaphysics.py     # add calculate_ziwei_horoscope, calculate_ziwei_palace_query
                                        # + snapshot_text builders
fatebridge/services/tool_catalog.py    # register new ToolSpecs (1 entry each)
tests/...                              # unit + contract + e2e CLI tests; committed fixtures
skills/onda-mingge/, skills/onda-xingpan/  # doc updates per tier
```

`ziwei_tables.py` exists so the large, transcribed iztro lookup tables live in
one auditable place, separate from the placement logic. Every table carries a
comment pointing at the corresponding iztro source location.

## 4. Tier 1 — Static chart completeness (PR #1)

**What ships**

- `fatebridge/core/ziwei_tables.py` with the brightness table keyed by
  `(star, branch)`, transcribed from iztro's `data/` brightness definitions,
  each block commented with its iztro source reference.
- `build_ziwei_chart` annotates each placed star with its brightness.
- **Payload (additive):**
  - keep `palaces[].stars: [str]` unchanged;
  - add `palaces[].stars_detail: [{ "name": str, "brightness": str, "mutagen": str | null }]`
    where `mutagen` is derived from the existing `sihua` (化禄/化权/化科/化忌 or null).
- `_build_ziwei_snapshot_text` gains brightness annotations (e.g. `紫微(庙)`).

**Out of scope for Tier 1:** new tools, horoscopes, relationships.

**Tests:** brightness lookup unit tests; one canonical chart fixture asserted
field-by-field against py-iztro; contract test confirms old keys still present;
snapshot_text regression.

## 5. Tier 2 — Horoscope cycles (PR #2)

**What ships**

- `ZiweiHoroscopeRequest` (birth info + `target_date`, ISO solar date; optional
  target time for 流时).
- `build_ziwei_horoscope(seed, gender, target_date)` returns, for the target:
  - **大限** (active decadal palace + its stem-driven 四化),
  - **小限** (annual minor limit palace),
  - **流年** (year palace + 流年四化),
  - **流月 / 流日 / 流时** (month / day / hour palaces + their 四化),
  - each entry: `{ palace_name, palace_index, branch, stem, mutagen: {禄,权,科,忌→star} }`.
- `calculate_ziwei_horoscope` service fn + `_build_ziwei_horoscope_snapshot_text`.
- One `ToolSpec` entry → tool name `ziwei_horoscope`, available on CLI/REST/MCP,
  introspectable via `describe`.

**Reuse:** the static 大限 ranges already computed in `build_ziwei_chart` define
the decadal boundaries; Tier 2 selects the active one for the date and layers
the dynamic 四化 on top (the year/month/day/hour stems come from the existing
calendar/ganzhi machinery).

**Tests:** horoscope fixtures for ≥2 dates against py-iztro; e2e CLI test;
contract + `describe` test.

## 6. Tier 3 — Palace relationships + query (PR #3)

**What ships**

- **Chart enrichment (additive):** each palace gains
  `opposite_index` (对宫) and `san_fang_si_zheng: [int, int, int]` (the palace's
  trine + opposition indices).
- **`ziwei_palace_query` tool** (`ZiweiPalaceQueryRequest`): given a computed
  chart (or birth info) + a query, answer agent-style lookups:
  - find the palace(s) containing a given star,
  - find which mutagen (if any) a given star carries,
  - check whether a palace's 三方四正 / surrounding palaces contain a given
    mutagen or star (the data equivalent of iztro's
    `surroundedPalaces().haveMutagen('忌')`).
- Returns structured results (indices, palace names, booleans) — no fluent API.

**Tests:** relationship-index unit tests vs py-iztro; query-tool behaviour
tests (by-star, by-mutagen, surrounding checks); e2e CLI + contract + describe.

## 7. Cross-cutting requirements

- **Single source of truth:** every new tool is one `ToolSpec` append; no
  transport file is hand-edited. CLI/REST/MCP + `describe` come for free.
- **Output contract:** new tool outputs include the standard `run_metadata` and
  `snapshot_text`; payloads support `--fields` dot-path projection.
- **Pure-Python/offline at runtime:** py-iztro is **dev/test-only**, never
  imported by runtime code. CI's runtime install must not require it.
- **Skills layer:** `onda-mingge` (命格) and `onda-xingpan` (星盘) docs updated
  per tier with real, runnable CLI commands whose output an agent can reason
  over; "人味儿" self-check applied to any interpretive copy.
- **Verification anchor:** a committed canonical-birth fixture (iztro's README
  example birth) cross-checked field-by-field; a small script regenerates
  fixtures from py-iztro so they're reproducible.

## 8. Non-goals (YAGNI)

- No JS runtime in production; no py-iztro at runtime.
- No fluent/chained query API (data + helper tool instead).
- No rewrite of existing star-placement logic; only additive layers.
- No new interpretive/AI-narrative content beyond skill-doc updates.
- No GUI/visualization of the astrolabe.

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Brightness/relationship tables transcribed wrong | py-iztro fixture diff catches mismatches automatically; tables commented with source refs. |
| Existing engine's placement differs subtly from iztro (e.g. leap-month, 文昌/文曲 direction) | Field-by-field fixture diff surfaces it; discrepancies fixed within the relevant tier with a documented note. |
| Payload growth bloats agent token budgets | Additive fields + `--fields` projection let callers trim; `stars` (compact) preserved alongside `stars_detail`. |
| py-iztro (JS-via-interpreter) hard to install in CI | It's an *optional* dev/test extra; fixtures are committed, so the main test run passes without regenerating. A separate, non-blocking job regenerates/verifies. |

## 10. Delivery checklist

- [ ] PR #1 — Tier 1 (brightness + `stars_detail`) — branch `feat/ziwei-brightness`
- [ ] PR #2 — Tier 2 (`ziwei_horoscope`) — branch `feat/ziwei-horoscope`
- [ ] PR #3 — Tier 3 (relationships + `ziwei_palace_query`) — branch `feat/ziwei-palace-query`

Each PR: unit + contract + e2e CLI tests green across Python 3.10–3.13, black,
isort, mypy; skill docs updated; merged before the next begins.
