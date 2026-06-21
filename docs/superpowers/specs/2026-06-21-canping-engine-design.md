# Design: 邵子参评数 / 金锁银匙 (canping) — horosa parity

- **Date:** 2026-06-21
- **Status:** Implemented on `feat/canping-engine`. Resolutions: decision #2 →
  **reuse FB `get_nayin`** (0 mismatches over 60 ganzhi); §5 →
  **ming & gu have identical 74% verse coverage** (gu is NOT sparse; the 26%
  holes are inherent to horosa's table and faithfully preserved), so both取法
  ship as first-class. Full chain verified byte-identical to horosa's
  `canpingLocal.js` (720/720 numeric inputs + snapshot golden).
- **Source capability:** horosa-skill `canping` —
  `horosa-core-js/src/tools/canping.js` (thin shell) +
  `src/vendor/canping/canpingLocal.js` (193-line算法) +
  `src/vendor/canping/data/canpingTiaowen.json` (61 KB 条文表)
- **Verification corpus:** ships inside the source —
  `canpingLocal.js:3` records the文档算例 that the JS was字逐验证 against:
  本命 `2242/3242`, 大运寅 `3038/2438`, 流年戌 `2543/2943`.
- **Family:** Chinese metaphysics · 数算 (number-divination). Same class as
  `tongshefa` — a horosa "headless JS" technique re-implemented as a
  **native offline Python** tool, NOT a backend/ken passthrough.

## 1. Goal

Add a new `canping` tool that, given a birth (date / time / 性别 / 经度 /
真太阳时 flag) plus a取法 (`ming` 明法 / `gu` 古法), returns the 金锁银匙
起数 + 条文 for:

- **本命** (natal) — 顺/逆 two numbers + their gender-keyed verses,
- **大运** — 9 steps from 命宫顺行, each step's 顺/逆 number + 流年-class verse,
- **流年全表** — age 1→120 虚岁, each year's 太岁/大运 起数 + verse,
- a `snapshot_text` byte-aligned to horosa's `buildSnapshotText`
  (sections `[起盘]/[本命]/[大运·歲運]/[流年·歲運]`).

Pure Python / offline. Flows through the central `tool_catalog.py` so
REST / MCP / CLI + `describe` stay auto-synced (the BaZi-dimension pattern).

**Out of scope (deferred):**
- `gu` 古法 condition-text completeness IF the shipped table lacks gu-specific
  entries — see §5. We expose both取法 but verify `ming` first.
- `heluo` (河洛理数) — the larger数算 sibling (388 KB table, 555-line算法).
  Separate branch / PR after canping lands. This spec is canping-only.

## 2. What already exists (reuse, do not rebuild)

- **Four pillars.** horosa builds pillars via its own `baziLunarLocal.js`
  (lunar-javascript). FateBridge has its own four-pillar engine
  (`BaZiCalendar` / the bazi service). We **substitute FB's pillars** for
  horosa's — canping only consumes 年干支 + 月支 + 日支 + 时支, so any engine
  that yields the same四柱 yields the same numbers. The真太阳时 flag
  (`timeAlg` 0 = 真太阳, default = 钟表时) maps onto FB's existing真太阳时 path.
- **年纳音 → 五行.** `fatebridge/core/...get_nayin(stem, branch)` already
  returns the 纳音 name; the element is its last char (金/木/水/火/土).
  Cross-check against horosa's `NAYIN_ELEMENT` map (60-ganzhi → element,
  `canpingLocal.js:18-31`) — must agree value-for-value or we port the map
  verbatim instead.
- **snapshot rendering.** `_render_snapshot_text(sections)` (already in
  `services` + `core/local_techniques.py`) is the standard section renderer.
- **真太阳时 / 经度解析, datetime parsing.** existing helpers in
  `core/local_techniques.py` (`parse_local_datetime`, `parse_geo_coordinate`).

**The genuinely new code is the 金锁银匙 起数 + 条文查表**, ported verbatim
from `canpingLocal.js`.

## 3. Locked decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | Pillar source | FB's own four-pillar engine | DRY; FB pillars are already golden-tested. canping is pillar-agnostic. |
| 2 | 纳音 source | reuse FB `get_nayin` + element-extract; fall back to porting `NAYIN_ELEMENT` | DRY first, but a value-mismatch forces the verbatim map. Decided by a one-shot 60-ganzhi diff test. |
| 3 | 条文 data | copy `canpingTiaowen.json` verbatim into `fatebridge/data/` | Lookup table, not algorithm. Byte-copy guarantees parity; no re-typing 5-char verses. |
| 4 | 取法 default | `ming` (明法) | mirrors horosa `normalizeMethod` default. |
| 5 | 流年 range | 1→120 虚岁 | matches horosa `liunianSeries` default (`startAge:1,endAge:120`). |
| 6 | snapshot sections | `[起盘]/[本命]/[大运·歲運]/[流年·歲運]` | byte-aligned to horosa `buildSnapshotText`; export layer legacy-maps 大运·歲運→大运, 流年·歲運→流年 per horosa's aiExport contract `['起盘','本命','大运','流年']`. |
| 7 | CLI home | a `数算`/术数 skill entry (likely `onda-*`); confirm at wiring time | consistent with how election went to `onda-shiyun`. |

## 4. Algorithm (ported verbatim from `canpingLocal.js`)

All constants copied exactly:

- `BRANCH_NUM`: 子=1…亥=12.
- `MONTH_TO_DAY_PALACE` (明法 reverse map): 寅→亥, 卯→戌, …, 子→丑, 丑→子.
- `ELEMENT_ADD`: 水/火 +27, 土 +50, 木/金 +0.
- `ELEMENT_PEI`: 水1 火2 木3 金4 土5.

Functions (1:1 Python ports, names kept readable):

1. **`day_palace(month_branch, day_branch, method)`** — `gu`→日支;
   `ming`→`MONTH_TO_DAY_PALACE[month_branch]`.
2. **`ming_gong(day_palace_branch, hour_branch)`** — 日宫支配卯时起逆数至生时:
   `idx = ((dp - (hb - 卯) - 1) mod 12) + 1`.
3. **`compute_number(day_branch, hour_branch, element)`** — the起数 core:
   ```
   shun = ((12 + (hb - dp)) mod 12) + 1     # 日支顺数至时支
   ni   = 14 - shun                          # 时日顺冲(逆)
   ziRound = dp + hb                          # 皆从子上轮
   base = 2000 + ziRound + ELEMENT_ADD + ELEMENT_PEI
   numShun = base + shun*100 ; numNi = base + ni*100
   ```
4. **`lookup(element, number, kind)`** — `TIAOWEN.parts[element][str(number)][kind]`
   with `kind ∈ {male, female, luck}`; fall back to `TIAOWEN.special[str(number)].text`.
5. **`dayun_sequence(day_palace_branch, hour_branch, qiyun_age=1, count=9)`** —
   9 steps from 命宫顺行, each `ageStart = qiyun + 10k`.
6. **`calculate(...)`** — assembles 本命 (kind = 性别) + 大运 (kind = luck) +
   optional单点流年.
7. **`liunian_series(...)`** — age 1→120: 太岁(当年年支)替日支、当时大运支替时支
   起数, kind = luck.
8. **`build_snapshot_text(result)`** — the 4 sections above.

> **Gender keying:** 本命 verse uses `male`/`female` by 性别; 大运 & 流年 use
> `luck`. (`canpingLocal.js:109,117,160`.)

## 5. Data table (`canpingTiaowen.json`)

Top-level shape (verified): `{"parts": {"<element>": {"<number>": {"male","female","luck"}}}, "special": {"<number>": {"text"}}}`.
- Byte-copy into `fatebridge/data/knowledge/` (or a new `fatebridge/data/canping/`).
- **Open question for review:** does the shipped table contain `gu`-法 numbers?
  The起数 ranges differ between 明/古法 because日宫支 differs. We will run a
  coverage probe (every (element, number) the algorithm can emit for both法 vs
  table keys) and report holes. If `gu` is sparsely covered, decision #4 + a
  doc note stands; we do not fabricate verses.

## 6. Tool surface (the BaZi-dimension recipe)

| Layer | Change |
|---|---|
| `core/` | new `core/canping.py` (or fold into `local_techniques.py`): constants + the 8 functions above. |
| `data/` | `canpingTiaowen.json` verbatim. |
| `services/` | `calculate_canping(request)` in `services/divination.py` (canping is术数/占断, sits with sixyao/suzhan/tongshefa). Builds pillars → calls core → assembles response + `snapshot_text`. |
| `core/request_models.py` | `CanpingRequest` (date/time/性别/经度/真太阳时/method). |
| `services/tool_catalog.py` | one `ToolSpec(key="canping", mcp_name="canping", rest_path="/api/divination/canping", ...)`. |
| `core/export_contracts.py` | `canping` → `['起盘','本命','大运','流年']`. |
| `fatebridge/mcp_server.py` | register (auto if it iterates `mcp_specs()`; verify). |
| CLI | auto via catalog `describe`/dispatch; add a real runnable example to the chosen skill doc (per doc-accuracy practice). |

## 7. Verification

1. **Golden algorithm test** — assert `compute_number` reproduces the source's
   documented算例: 本命 `2242/3242`, 大运寅 `3038/2438`, 流年戌 `2543/2943`
   (`canpingLocal.js:3`). These are the corpus the JS itself was验证 against.
2. **纳音 diff test** — FB `get_nayin`-derived element vs horosa `NAYIN_ELEMENT`
   over all 60 ganzhi (decides locked-decision #2).
3. **snapshot golden** — one full命例 → `snapshot_text` byte-compared to a
   captured horosa `buildSnapshotText` output (run the Node tool once on the
   same input to mint the golden), under the reference-env golden convention
   (PR #61) so 3.10–3.13 stay deterministic.
4. **Tri-surface smoke** — REST + MCP + CLI return the same payload
   (the standard `test_tool_spec` / `test_divination_tools` additions).
5. **Coverage probe** — §5 table-hole report (informational, not a gate).

## 8. File-by-file change list (implementation plan preview)

- `fatebridge/core/canping.py` — new (algorithm).
- `fatebridge/data/canping/canpingTiaowen.json` — new (verbatim copy).
- `fatebridge/core/request_models.py` — `CanpingRequest`.
- `fatebridge/services/divination.py` — `calculate_canping`.
- `fatebridge/services/tool_catalog.py` — one `ToolSpec`.
- `fatebridge/core/export_contracts.py` — canping contract.
- `tests/test_divination_tools.py` (+ `test_tool_spec.py`) — the 5 checks.
- chosen `skills/onda-*/SKILL.md` — runnable CLI example.

## 9. Risks / notes

- **No backend dependency** — canping is fully in-process (the whole reason it
  is cleanly portable, unlike `agepoint`/`persiandirected` which are computed
  by horosa's closed Python/Java chart-extra backend with no readable source).
- **真太阳时 parity** — if FB's真太阳时 correction differs from horosa's
  (longitude + equation-of-time), pillars near a时辰 boundary could diverge.
  Mitigation: golden命例 uses a mid-时辰 birth; document the dependency.
- **License / provenance** — verses are classical (金锁银匙) public-domain text;
  the JSON is a data table. Copyright署名 stays `thomas-yanxin` per project norm.
