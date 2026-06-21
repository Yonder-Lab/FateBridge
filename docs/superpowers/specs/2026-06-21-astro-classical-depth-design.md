# Design: 西占古典深度段 [古典]/[古典格局] — horosa parity (multi-phase)

- **Date:** 2026-06-21
- **Status:** **Phase 1 (#72) + Phase 2 (#73) merged; Phase 3 implemented**
  (`feat/astro-classical-phase3`). Overarching project spec — ~5 phased PRs.
  - **Phase 3 shipped:** **Arabic lots** (福/精神/婚姻/子女/死亡 5 lots) with
    day/night reversal, each lot's domicile dispositor + weighted almuten; chart
    gains `classical.lots`, snapshot adds `[阿拉伯点]`. `lots.fortune` shares the
    EXACT-ascendant formula with the pre-existing `_fortune_lot` (single source,
    verified equal). Fixed stars + planetary hours **deferred to Phase 3b** (need
    star catalog/precession + sunrise → ephemeris, like Phase 2b).
  - **Phase 2 shipped:** dispositor chains (主宰星链, with mutual-reception / loop
    detection + final dispositors) and per-house **topic almutens** (weighted
    essential-dignity winner of each cusp), via new `almuten_of` /
    `dignity_lords_at` / `dispositor_chain` in `classical_western.py` (almuten
    weights = horosa `lifespanEngine.js` `DIG_W`). Chart gains
    `classical.dispositors` + `classical.topic_almutens`; snapshot adds
    `[主宰]` + `[宫主星]`.
  - **Deferred to Phase 2b** (all need ephemeris plumbing the offline chart
    lacks): **Almuten figuris** (needs the prenatal **syzygy** point),
    **retrograde** (per-planet speed), **out-of-bounds** (declination). Bundle
    these once the chart exposes speed + declination + syzygy.
- **Source capability:** horosa-skill chart family `[古典] (Classical)` +
  `[古典格局] (Classical patterns)` sections (README_EN "Classical astrology
  completion v2.6.7"), on natal / 13-house / Hellenistic / India / mundane charts.
- **Sibling specs:** [[canping]]/[[heluo]] (数算 lane, now complete). This is the
  remaining first-priority item per `horosa-merge-roadmap`.

## 1. Goal

Give FateBridge's `astro_chart` (and variants) a classical-astrology layer so an
agent can reason in Hellenistic/medieval terms: per-planet **essential +
accidental condition** (`[古典]`) and chart-level **patterns/格局** (`[古典格局]`).
Pure Python on the existing pyswisseph engine; attaches as new structured keys
on the chart payload (`classical`, `classical_patterns`) + snapshot section.

## 2. Critical framing — NOT a byte-oracle port

Unlike canping/heluo, horosa's classical layer is **backend-computed**
(`chartFacts.js:3-4`: the Java/Python chart service supplies dignities,
selfDignity, isPeregrining, isVOC, receptions, `surround`/besiegement,
antiscia). The readable vendored JS only does trivial frontend derivations.
**Consequence for verification:**

- **Reference data tables** horosa ships (`data/dignities.js` Egyptian terms +
  Dorothean triplicity, faces/decans, `data/lots.js`, `data/bodyParts.js`
  melothesia, `data/fixedStars.js`, `data/planetaryHours.js`) → **port verbatim,
  table-parity tested.**
- **Derivation logic** (almuten, besiegement, doryphory, temperament…) → **build
  from authoritative classical definitions** (Ptolemy / Lilly / Bonatti /
  Dorotheus; horosa's data files cite their sources), **structurally tested**
  (invariants, known-chart spot-checks), not byte-diffed against a closed oracle.
- Where a derivation IS in readable JS (combustion, angularity, moon phase,
  lots formula, melothesia degree-position), diff against that JS as a bonus.

## 3. Reuse — FateBridge already has a classical foundation

| Already in FB | Where | Reuse plan |
|---|---|---|
| Essential dignity (rulership/exaltation/detriment/fall/peregrine) | `astrology.py:_essential_dignity` + dignity tables | promote to the shared classical module; add triplicity/term/face. |
| Bound(term) lord, Dorothean triplicity lords, face | `astrology_horary.py:_bound_lord/_triplicity_element_lords/_dignities` | **extract** from horary into `core/classical_western.py`; horary imports back. |
| Mutual reception | `astrology_horary.py:_mutual_reception` | generalize to all planets/points. |
| Moon void-of-course, via combusta | `astrology_horary.py` | reuse for accidental layer. |
| Sect (day/night), aspects, houses, sidereal/nakshatra | `astrology.py` chart build | feed the classical layer. |

**Key refactor (Phase 1):** the dignity/reception logic is currently private to
horary. Phase 1 extracts it into a shared `core/classical_western.py` that both
horary and the chart layer consume — single source, no duplication (the dedup
principle). This is the riskiest structural step, so it leads.

## 4. Phase decomposition (≈5 PRs, each independently shippable)

Each phase adds a coherent slice of `chart["classical"]` / `["classical_patterns"]`
+ tests + snapshot lines + golden re-freeze (every phase changes `astro_chart`
output → its golden snapshot must be regenerated; the canping/heluo CI lesson).

**Phase 1 — per-planet essential + accidental status (foundation).** Detailed §5.
Extract shared dignity module; emit `classical.planets[key]` = 5-fold essential
dignity + score, bound/triplicity/face lords, sect placement (hayyiz/halb,
rejoicing), oriental/occidental, combustion (cazimi/combust/under-beams),
peregrine, retrograde, angularity (angular/succedent/cadent), out-of-bounds
(|declination| > 23.4367°), aboveHorizon, joy (planetary joys by house).

**Phase 2 — almutens & dispositor chains.** Almuten of any degree (weighted
essential dignity), **Almuten figuris** (whole-chart almuten), house/topic
almutens, **主宰星链** dispositor chains + final dispositor.

**Phase 3 — lots, fixed stars, planetary hours, calendars.** Extended Arabic
**lots** (LOTS formulas, day/night reversal), **fixed-star** conjunctions
(fixedStars.js), **planetary hours**, Egyptian calendar / Babylonian reference
stars (if data present).

**Phase 4 — `[古典格局]` aspect-pattern layer.** besiegement (sign + degree),
encirclement, **doryphory** (spear-bearing), translation / collection of light,
overcoming, aversion, nodal bending, bonification / maltreatment.

**Phase 5 — degree-level + body.** **Dodekatemoria (12分度)**,
monomoiria / ninth-part / face / Darijan, **lunar mansions (28)** (FB already has
nakshatra; mansions are the classical 28), **melothesia** body parts
(bodyParts.js), **temperament** (qualities tally).

> Ordering rationale: 1 builds the shared substrate everything else needs; 2
> depends on 1's dignity scores; 3 is independent data-driven; 4 needs aspects +
> dignities; 5 is degree tables (most data, least logic). Stop-after-any-phase
> safe — each leaves a coherent, tested `classical` subtree.

## 5. Phase 1 detail (this PR)

### 5.1 New module `core/classical_western.py`
Shared classical primitives, extracted from `astrology_horary.py` (which then
imports them — net dedup):
- `EGYPTIAN_TERMS`, `DOROTHEAN_TRIPLICITY`, `CHALDEAN_FACES` reference tables
  (ported verbatim from horosa `data/dignities.js`/`signs.js`; table-parity tested).
- `essential_dignity(planet, sign, degree, is_day)` → all dignities held + score
  (Lilly's +5/+4/+3/+2/+1 / −5 / −4 / peregrine).
- `bound_lord` / `triplicity_lords` / `face_lord` (move from horary).
- `sect_status(planet, is_day, above_horizon, sign)` → hayyiz / halb / contrary.
- `combustion_state(planet_lon, sun_lon)` (cazimi 17′ / combust 8.5° / under-beams
  17° — from chartFacts.js, diffable).
- `orientality(planet_lon, sun_lon)`, `out_of_bounds(declination)`,
  `angularity(house)`, `planetary_joy(planet, house)`.

### 5.2 Chart integration
`build_core_chart_payload` (or the service layer) gains, behind the existing
七曜/point loop, a `classical` block:
```
chart["classical"] = {
  "sect": "day"|"night",
  "planets": { "sun": {essential, dignity_score, bound_lord, triplicity_lords,
                       face_lord, sect_status, orientality, combustion,
                       peregrine, retrograde, angularity, out_of_bounds,
                       above_horizon, joy}, ... },
}
```
Only classical 七曜 (☉☽☿♀♂♃♄) get full essential dignity; outers/nodes get the
accidental subset (retro/angularity/combustion/OOB) with `essential: null` — same
convention as FB's existing `_essential_dignity` (None for non-classical).

### 5.3 Snapshot + surfaces
- New `[古典]` snapshot section (per-planet one-liner: `太阳 巳宫 庙 昼 角宫 …`).
- Flows through `tool_catalog` → REST/MCP/CLI automatically (no new tool; enriches
  `astro_chart`). `--fields classical.planets.sun.essential` works.

### 5.4 Verification (Phase 1)
1. **Table parity** — `EGYPTIAN_TERMS`/`TRIPLICITY`/`FACES` byte-equal to horosa
   `data/dignities.js` (port + a test that re-derives the JS structure).
2. **Dignity invariants** — every degree of all 12 signs has exactly one bound
   lord and one face lord; a planet in its own sign scores rulership; sun in Aries
   = exaltation; etc. (classical ground truth).
3. **combustion/orientality diff** — port matches `chartFacts.js` formulas
   (cazimi/combust/under-beams thresholds) on sampled separations.
4. **Refactor safety** — horary tests still pass after dignity extraction (the
   extraction must be behavior-preserving — horary golden unchanged).
5. **golden re-freeze** — `api_astro_chart.json` + variants regenerated (chart
   output now has `classical`); registry untouched (no new technique/tool).
6. Four gates + CI 3.10–3.13.

## 6. Risks / notes

- **No byte-oracle** (§2) — mitigated by table-parity + classical-invariant tests
  + the fact FB's foundation is already horary-validated. Each derivation cites
  its authoritative source in code comments.
- **Refactor blast radius** — extracting dignities out of horary touches a
  shipped, golden-locked tool. Phase 1 keeps horary's output byte-identical
  (extraction only); the horary golden is the guardrail.
- **Scope discipline** — resist doing >1 phase per PR. Each phase is reviewable,
  testable, and leaves master green. Outers/Uranian points stay out of essential
  dignity (classical correctness).
- **Naming** — `core/classical.py` is already taken (BaZi 格局). Use
  `core/classical_western.py` to avoid the clash.
