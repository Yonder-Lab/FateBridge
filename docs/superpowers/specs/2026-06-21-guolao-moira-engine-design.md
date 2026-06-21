# 七政四余政余格局 (guolaoMoira) — Engine Design Spec

**Status:** Draft for validation · **Branch:** `feat/guolao-moira` · **Date:** 2026-06-21

Port horosa-skill's `guolaoMoira.js` (七政四余 政余格局 / Moira DSL) into FateBridge as a
native-Python engine, **full scope including the 七政四余 神煞 god system** (user decision
2026-06-21, made with full knowledge that the god system has no byte-oracle).

---

## 1. Why this is not a leaf port (the dependency discovery)

`canping`/`heluo` were self-contained 数算 (pillars → numbers → 条文). `guolaoMoira` is the
opposite: a 613-line **pattern-matching DSL that reads a fully-computed 七政四余 chart**. The
DSL itself is trivial to port; the work is building the chart inputs it reads, which FB's
current `astro_guolao` does **not** produce:

| Input the DSL reads | Source in horosa | Present in FB today? | Verifiable? |
|---|---|---|---|
| 七政 longitudes (日月水金火木土) | closed `/chart` backend | ✅ (kerykeion Sun..Saturn) | ✅ swisseph |
| 孛 (Black Moon Lilith / 月亮平均远地点) | closed backend, `DARKMOON` | ❌ | ✅ swisseph `SE_MEAN_APOG` |
| 罗 / 计 (North/South Node) | closed backend | ◑ North only | ✅ (South = North+180°) |
| 紫炁 (木余) | closed backend, `PURPLE_CLOUDS` | ❌ | ❌ **no oracle** (classical 步紫炁 formula) |
| 命度 (LIFEMASTERDEG74) | closed backend | ◑ falls back to ASC | ✅ |
| 28宿 boundary degrees (`fixedStarSu28[].ra`) | closed backend | likely reusable (FB labels su28) | ✅ classical 宿度表 |
| **七政四余 神煞 by 地支 (`guolaoGods.ziGods`)** | **closed backend only** | ❌ | ❌ **no oracle — text reconstruction** |

**Key fact (horosa's own `service.py:730-732`):** in horosa's *offline* skill the god-dependent
patterns also do not fire, because `guolaoGods` is never returned by its offline `/chart`. So FB
building the god system is **going beyond horosa**, by design, at the user's request.

---

## 2. Which bodies / data each pattern actually needs

The DSL has 12 patterns. Mapping each to its true data dependency (so we can phase delivery):

| Pattern | Level | Needs | Phase |
|---|---|---|---|
| 八杀朝天 | good | 疾厄宫主(planet by sign-ruler) + 命临戌亥 | 1 |
| 孤月独明 | good | 月 + 七政 same-sign count + 昼夜 | 1 |
| 日月拱官 | good | 日/月/官禄宫 | 1 |
| 金水相涵 | good | 金/水 + 非冬令 | 1 |
| 日月失所 | bad | 日/月 地支 | 1 |
| 官福失垣 | bad | 官/福宫主 失垣(overcoming) | 1 |
| 孛犯太阳 | bad | **孛** + 日 | 1 |
| 罗犯太阳 | bad | 罗 + 日 | 1 |
| 孛罗交战 | bad | **孛** + 罗 | 1 |
| 命坐两歧 | bad | 命度 + **28宿界** | 3 |
| 日月拱贵人 | good | 日/月 + **天贵/玉贵** (神煞) | 2a |
| 命登岁驾 | good | 命度 + **岁驾** (神煞) | 2a |

**紫炁 and 计(degreed) are referenced by ZERO live patterns.** They are only needed for the
per-宫 神煞 *display* table (`buildGodRowsFromChart`), not the 格局 logic. This lets us isolate
the unverifiable 紫炁 into a clearly-flagged, display-only phase.

Only **3 of 100 gods** (天贵/玉贵/岁驾) feed the 格局 patterns. The full 64-birth + 36-transit god
table is for the per-宫 神煞 display section only.

---

## 3. Phasing (one PR each, single responsibility)

### Phase 1 — node/孛 bodies + 物象格局 (verifiable, ~250 LoC) — **highest value, do first**
- **FB's guolao body set is `TRADITIONAL_PLANETS` = 7 classical only (no nodes).** So Phase 1 adds
  **THREE** bodies: 孛 (`swe.MEAN_APOG`=12), 罗 (North Node, mean — `swe.MEAN_NODE`), 计 (=罗+180°).
  Inject in `core/astrology.py`: extend `PLANET_SWISSEPH_IDS` (L331-347) + a guolao-specific body
  list feeding `_planet_set("guolao_chart")` (L1029-1032); the `_swisseph_planet_state` loop
  (L1049-1064) already handles any id, so no per-body branching.
- 命度 = **ASC** (horosa default `GUOLAO_LIFE_MODE_ASC`); ASC longitude already in
  `result["angles"]["ascendant"]`. **No 命度 computation needed** → resolves §4.2.
- House signs = guolao's **whole_sign** ring from ASC sign — exactly matches the DSL's
  `localMoiraHouseSign(lifeSignIndex, offset)`. ✅
- Phase 1 needs **no 四柱干支** (時支 only matters for the Phase 2b display-table house numbering
  via `computeAscSignIndex`; the 10 patterns derive houses from ASC sign alone).
- Port the 10 pattern checks that need only planets/houses/孛/罗. 命坐两歧's god-free 近宫界 half
  (`lifeLon % 30` near boundary, from ASC longitude) ships here; 近宿界 waits for Phase 3.
- New `fatebridge/core/guolao_moira.py` (DSL, mirrors `canping.py` conventions).
- Verification: byte-parity test vs `guolaoMoira.js` on a synthetic chart whose 孛/罗/planet
  longitudes we feed identically to both implementations (Node oracle, like decennials/canping).

### Phase 2a — 天贵/玉贵/岁驾 起例 (3 gods, for 格局) (~80 LoC)
- Encode just the 3 god placements the patterns need → enables 日月拱贵人 + 命登岁驾.
- Verification: **domain validation by user** (no JS oracle) + golden-lock once accepted.

### Phase 2b — full 七政四余 神煞 table (64 birth + 36 transit) + per-宫 display section (~400 LoC + data)
- Port `buildGodRowsFromChart` + the full god 起例 table → "[政余神煞]" snapshot section.
- This is the bulk of the text-reconstruction work. See §5 for the god list + 起例 status.
- Verification: **domain validation by user**, then golden-lock.

### Phase 3 — 28宿界 (命坐两歧 近宿界 half) (~40 LoC) — **has a fidelity fork (see §4.5)**
- **FB has NO real 宿度 boundary table.** `core/astrology.py:910 _su28()` uses *equal* 360/28
  spacing; horosa's 近宿界 uses real unequal `fixedStarSu28[].ra` from its backend. The two cannot
  both be matched. Affects only 命坐两歧's 近宿界 sub-check. Decision in §4.5.

### Phase 4 — 紫炁 (display-only, flagged) + tool wiring + catalog + 3-surface conformance
- 紫炁 via classical 步紫炁 formula, **explicitly labelled "近似/无 horosa 对照"** in output.
- Register `guolao_moira` (or fold into the `astro_guolao` snapshot as a `[政余格局]` section —
  decision in §4). REST+MCP+CLI conformance test + export-registry golden re-freeze.

---

## 4. Open design decisions (need a call before/within implementation)

1. **Surface shape:** new standalone tool `guolao_moira`, OR enrich the existing `astro_guolao`
   chart snapshot with `[政余格局]` + `[政余神煞]` sections (like the 西占古典深度段 enriched
   `astro_chart`)? — *Recommendation: enrich `astro_guolao`*, since the patterns are meaningless
   without the chart they read; matches the classical-depth precedent. The 命度/昼夜/季节 inputs
   are already in the chart request.
2. **命主 mode:** horsa default = ASC (`GUOLAO_LIFE_MODE_ASC`). Keep ASC-only (羽士/同度 modes are
   localStorage UI prefs, irrelevant headless). ✅ no decision needed — match horosa default.
3. **House-start mode:** horosa headless default = `SZHouseStart_Bazi` (時支-based), see
   `computeAscSignIndex`. Must replicate (needs 時支 from FB pillars). ✅ match default.
4. **紫炁 inclusion:** ship it (flagged approximate) or omit entirely? It feeds no 格局 pattern.
   *Recommendation: omit from格局; include in display only if Phase 2b's神煞 table ships, else drop.*
5. **命坐两歧 近宿界 (Phase 3 fork):** (a) add a real classical 宿度 table for the boundary check —
   but FB's planet `su28` labels stay equal-spaced, so the chart would be internally inconsistent;
   (b) reuse FB's equal-spacing boundaries — internally consistent but diverges from horosa's 近宿界;
   (c) ship 命坐两歧's 近宫界 half only, drop 近宿界. *Recommendation: (c) for Phase 1, revisit (a)
   as a broader "real 宿度" upgrade that also fixes `_su28` labels — out of scope for this engine.*

---

## 5. 七政四余 神煞 起例 — the reconstruction crux (USER VALIDATION NEEDED)

These placements come **only** from horosa's closed backend; there is no source to port. They must
be reconstructed from classical 七政四余 / 《张果星宗》 起例 and validated by domain knowledge.

**Birth gods (64), in `MOIRA_BIRTH_GOD_ORDER`:**
劫杀 文昌 禄勋 大耗 月杀 咸池 唐符 天厨 伏尸 三刑 勾神 蓦越 黄幡 的杀 孤辰 天喜 注受 剑锋 飞廉
病符 紫微 华盖 天贵 六害 孤虚 游奕 年符 死符 地雌 卷舌 绞杀 天德 贯索 亡神 国印 岁殿 卦气 空亡
豹尾 擎天 天空 大杀 天厄 月廉 天雄 天哭 天狗 地耗 月符 披头 红鸾 岁驾 小耗 寡宿 飞刃 天耗 斗杓
驿马 阳刃 阑干 玉贵 血刃 浮沉 解神

**Transit gods (36), in `MOIRA_TRANSIT_GOD_ORDER`:**
岁驾 天空 地雌 贯索 五鬼 死符 大耗 天厄 天雄 大杀 卷舌 天德 天狗 蓦越 亡神 天喜 披头 血刃 解神
天哭 地解 劫杀 的杀 红鸾 驿马 游奕 擎天 黄幡 豹尾 天厨 三刑 六害 咸池 阳刃 禄勋 天贵

**起例 confidence tiers (to be filled in collaboratively):**
- **Tier 1 — standard 三合/年支-based, high confidence I can encode:** 劫杀、咸池、华盖、驿马、
  亡神、月杀、的杀、孤辰、寡宿、天喜、红鸾、六害、三刑、黄幡、豹尾 (these follow well-known
  年/日支 三合局 起例).
- **Tier 2 — needs the 3 for 格局 first (Phase 2a):** 天贵、玉贵、岁驾.
- **Tier 3 — guolao-specific / obscure, NEED USER SOURCE:** 禄勋、唐符、蓦越、注受、勾神、伏尸、
  天厨、岁殿、卦气、月廉、天雄、地雌、斗杓、阑干、浮沉、年符、国印… (起例 varies by 流派; user to
  supply the authoritative 口诀/table FateBridge should follow).

> **ACTION:** Before Phase 2b, user reviews this list and either (a) confirms the 流派/源书 FB
> should follow (so I encode one consistent system), or (b) supplies the 起例 for Tier 3.

---

## 6. Verification strategy (honest about the oracle gaps)

| Component | Oracle | Method |
|---|---|---|
| 孛 longitude | swisseph `SE_MEAN_APOG` | numeric assert vs pyswisseph |
| 计 longitude | 罗+180° | identity |
| 物象格局 DSL (Phase 1) | `guolaoMoira.js` via Node | byte-parity on synthetic chart with fed-in longitudes (canping/decennials pattern) |
| 28宿界 | classical 宿度表 | numeric assert |
| 神煞 placements (Phase 2) | **none** | user domain validation → golden-lock regression |
| 紫炁 | **none** | classical formula, output flagged 近似 |
| 3-surface parity | existing conformance harness | REST==MCP==CLI + export-registry golden |

**CI note (from canping/heluo PRs):** any new REST route needs its own
`tests/golden/snapshots/api_*.json` AND a re-frozen `api_export_registry.json`; add the tool to both
surface case-maps in `tests/fixtures/surface_payloads.py`.

---

## 7. Module layout (mirrors canping/heluo)

- `fatebridge/core/guolao_moira.py` — pure DSL + 神煞 起例 tables + 命度/宿界 helpers.
- (if standalone tool) `fatebridge/core/request_models.py` += `GuolaoMoiraRequest`; one
  `_*_spec` in `fatebridge/services/tool_catalog.py`.
- (if enrichment) extend `_build_guolao_snapshot_sections` in `fatebridge/services/astrology.py`
  with `[政余格局]` (+ later `[政余神煞]`) sections; no new tool.
- `tests/test_guolao_moira_tool.py` + `tests/fixtures/guolao_moira_*_snapshot.txt`.
