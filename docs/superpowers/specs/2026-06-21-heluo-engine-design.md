# Design: 河洛理数 (heluo) — horosa parity

- **Date:** 2026-06-21
- **Status:** Draft (design); pending review before implementation
- **Source capability:** horosa-skill `heluo` —
  `horosa-core-js/src/tools/heluo.js` (shell + `solarTerm`) +
  `src/vendor/heluo/heluoLocal.js` (555-line算法) +
  `src/vendor/heluo/data/heluoTiaowen.json` (388 KB, 64 卦条文 + 爻辞)
- **Verification corpus:** ships in source — `heluoLocal.js:3-4` records算例:
  甲子丁卯庚申庚辰(阳男·辰时)→先天天风姤·元堂上九；丁巳丙午壬寅辛丑(阴男)→
  水风井；壬子年命例 澤地萃(元堂4)→地水師(元堂1).
- **Sibling of:** [[canping]] ([FateBridge#70](https://github.com/thomas-yanxin/FateBridge/pull/70)) — same数算 class & playbook. See `horosa-merge-roadmap`.

## 1. Goal

Add a `heluo` tool that, from a birth (date/time/性别/经度/真太阳时), returns the
河洛理数 chart and reading:

- **起命** — 天数/地数 → 天/地卦 → 先天卦(上下相盪) + 元堂动爻 → 后天卦;
- **先天/后天 元堂爻辞** (摘要 + 诗歌, from the条文表);
- **命运篇** — 天元气/地元气、化工/反化、得势/得时/得体、葉/不葉、阴阳二数、元堂当位/有应/顺气;
- **大限·岁运** — 先天卦元堂起、绕行六爻(阳9阴6年)、接后天卦, 虚岁;
- `snapshot_text` byte-aligned to horosa's `heluoLocal.buildSnapshotText`
  (sections `[起命]/[先天·… 元堂爻辞]/[后天·… 元堂爻辞]/[命运篇]/[大限·岁运]`).

Pure Python / offline. Central `tool_catalog.py` → REST/MCP/CLI auto-synced.

## 2. Scope decision — port only what the skill output needs

`heluoLocal.js` exports ~30 functions, but horosa's own `runHeluo` (the skill
surface) calls only: `calculate` → `daYun` → `solarTerm` → `judge` →
`buildSnapshotText` (+ `yaoText`/`yaoName`). The rest (`liuYue`, `liuRi`,
`periodEnergies`, `periodLiShu`, `chartExtras`, `duiGua`, `guaRelations`,
`monthXiaoxi`, `bianYiYi`, `jianDuan`, najia helpers …) feed horosa's **interactive
UI component** (`HeLuoMain`), NOT its export/snapshot contract.

**Decision:** port exactly the `runHeluo` chain (matches the aiExport contract
`先天卦/后天卦/大限` + 命运篇). Defer UI-only流月/流日/逐段卦气/对体 helpers — they
are not part of horosa's machine output and add large surface for no parity gain.
(Recorded as a follow-up if ever needed.)

## 3. The one genuinely new wrinkle — 命运篇 is 节气-coupled

Everything except 命运篇's 化工 is **pure ganzhi arithmetic** (天地数纳甲/卦变/
大限/爻辞查表) → byte-verifiable against horosa exactly like canping.

**命运篇 化工/反化** depends on the **real solar term at birth**. horosa's
`solarTerm()` uses lunar-javascript (`getPrevJieQi(true)` over all 24 terms +
四立前18日土用 → `solarTermHuagong`). FateBridge has its **own** 24-term engine
(`core/almanac.get_solar_terms_for_year`, swisseph/Moshier). Two consequences:

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | 节气 source | **FB's own 24-term engine** (not lunar-javascript) | DRY; FB jieqi already golden-locked. heluo consumes only the term *name* → 化工象限 (震/離/兌/坎) + 土用 flag. |
| 2 | 化工 verification | byte-diff vs horosa only on a **节气-safe** birth date (mid-quarter, NOT within 18d of 四立, NOT on a term boundary), where FB jieqi name == lunar-javascript's | At boundaries the two ephemerides may disagree by minutes; off-boundary they agree on the *name*, which is all 化工 needs. |
| 3 | term granularity | use FB's most-recent-of-24 term (`prevJieQi` equivalent), confirm `calendar_context` exposes it; else derive from `get_solar_terms_for_year` | `JIEQI_QUARTER` keys include both 节 and 气, so we need the most recent of all 24, not the month 节. |
| 4 | 土用 | within 18 days *before* a 四立 (立春/夏/秋/冬), from FB jieqi moments | mirrors `heluo.js` `LI_TERMS`/`diff>=0 && <=18`. |

Fallback parity: `judge` already has a month-branch 化工 fallback (`MONTH_HG`)
when no solarTerm — we keep that path for robustness, but default to the precise
FB-jieqi path.

## 4. Reuse (do not rebuild)

- **Four pillars** — FB's four-pillar engine (heluo needs all four full 干支).
  Substitute for horosa's `baziLunarLocal`, same as canping.
- **24 solar terms** — `core/almanac` (`get_solar_terms_for_year`,
  `SOLAR_TERM_LONGITUDES`). Port `solarTerm`/`solarTermHuagong` on top.
- **真太阳时 / datetime / 经度** — `_build_metaphysics_seed` in
  `core/local_techniques.py` (same entry canping used).
- **snapshot rendering** — `_render_snapshot_text` convention.

The genuinely new code: 天地数→卦 (纳甲/河图洛书), 元堂(含乾坤纯卦+三至尊卦
特例), 后天卦变换, 大限, judge(元气/化工/得势得时得体/二数/元堂), 爻辞查表,
snapshot — all ported verbatim from `heluoLocal.js`.

## 5. Data table (`heluoTiaowen.json`, 388 KB)

Keyed by **卦名** (64). Each: `index`(王弗序)/`verdict`/`gist`/`meaning`/`guaci`/
`zongjue`/`mingtiao`/`yao{1..6}{yaoci,shige,detail,verdict}`. Byte-copy verbatim
into `fatebridge/data/heluo/`. `buildSnapshotText` uses `yao[pos].detail` +
`.shige`; the gua-name↔trigram tables are rebuilt from the 64 keys at import
(`buildGuaTables`), so the JSON is the single source.

## 6. Tool surface (BaZi-dimension recipe — identical to canping)

| Layer | Change |
|---|---|
| `core/heluo.py` | new — constants + calculate / transformHoutian / daYun / solarTermHuagong / judge / yaoText / yaoName / buildSnapshotText. |
| `core/heluo_solar_term.py` *(or fold into heluo.py)* | `solar_term(date)` over FB's 24-term engine → `{hg,fh,term,tuyong}`. |
| `data/heluo/heluoTiaowen.json` | verbatim. |
| `core/local_techniques.py` | `build_heluo_result(...)` (seed → pillars → calc/daYun/judge → snapshot), mirroring `build_canping_result`. |
| `core/request_models.py` | `HeluoRequest` (date/time/性别/经度/真太阳时). |
| `services/divination.py` | `calculate_heluo_analysis` thin wrapper. |
| `services/tool_catalog.py` | one `ToolSpec(key="heluo", rest_path="/api/divination/heluo", mcp_name="heluo")`. |
| `core/export_contracts.py` | `heluo` technique + preset sections (actual snapshot titles). |
| tests + golden | see §7. |
| `skills/onda-zhanbu` | runnable CLI example + interface.yaml engine_tools. |

## 7. Verification

1. **节气-independent byte parity** — run horosa `heluoLocal.js` (calc/daYun/
   buildSnapshotText) on the documented算例 pillars; assert FB reproduces
   [起命] + [先天/后天爻辞] + [大限·岁运] byte-for-byte. (These are pure ganzhi.)
2. **命运篇 parity on a 节气-safe date** — pick a birth mid-quarter & outside 土用;
   diff the full snapshot (incl. [命运篇]) against horosa. Document the chosen date.
3. **算例 anchors** — assert the three `heluoLocal.js:3-4` cases (先天卦/元堂/后天卦).
4. **golden-master** — new REST route ⇒ commit `api_divination_heluo.json`
   (节气-safe payload, away from term boundaries → cross-platform stable).
   **Also re-freeze `api_export_registry.json`** (new technique entry) — the
   canping lesson: aggregator goldens drift on any tool add.
5. **surface case-map** — add heluo to REST + MCP representative payloads
   (`tests/fixtures/surface_payloads.py`) — the other canping CI lesson.
6. Four gates locally (pytest/black/isort/mypy); CI 3.10–3.13 + floor green.

## 8. Risks / notes

- **节气 source parity** is the only real risk; mitigated by §3 + a安全 golden date.
  If FB jieqi and lunar-javascript ever disagree on a term *name* off-boundary,
  that is a separate FB-vs-horosa ephemeris question, surfaced not hidden.
- **乾/坤 纯卦 元堂** + **三至尊卦(坎為水/水雷屯/水山蹇)「变而不易」** are the
  delicate special cases (`yuanTangPure`, `transformHoutian`) — covered by the
  documented算例 (天风姤 etc.) and the byte golden.
- **Provenance**: 《河洛理数》(陈抟·邵康节) classical public-domain text; JSON is a
  data table. 署名 `thomas-yanxin` per project norm.
- **Size**: 388 KB JSON + ~400 lines Python. Larger than canping but same shape.
