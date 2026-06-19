# Design: 紫微斗数 Horoscope (运限) — iztro parity Tier 2

- **Date:** 2026-06-19
- **Status:** Approved (design); pending implementation plan
- **Depends on:** Tier 1 (star brightness) — [FateBridge#39](https://github.com/thomas-yanxin/FateBridge/pull/39)
- **Parent spec:** `docs/superpowers/specs/2026-06-19-iztro-ziwei-parity-design.md`
- **Source capability:** iztro `FunctionalHoroscope` / `getHoroscope`

## 1. Goal

Add a new `ziwei_horoscope` tool that, given a birth and a target date-time,
returns the **active 运限 (horoscope) for all six iztro scopes** — 大限 / 小限 /
流年 / 流月 / 流日 / 流时 — each with the palace it lands on and its **dynamic
四化** (the period's stem re-triggering 禄/权/科/忌 onto natal stars). Pure
Python / offline; flows through the central `tool_catalog.py` so REST / MCP /
CLI + `describe` stay auto-synced.

**Out of scope (deferred):** 流耀 (dynamic stars 流昌/流曲/流魁/流钺/流禄/流羊/
流陀/流马). This Tier delivers cycle *palaces + 四化* only — matching the parent
spec's Tier-2 description. 流耀 is a candidate for a later phase.

## 2. What already exists (reuse, do not rebuild)

- `build_ziwei_chart` (Tier 1) returns palaces with static **大限 age ranges**
  (`palace["daxian"] = "2~11"`, `daxian_period`) + top-level
  `daxian_direction` (顺行/逆行). 紫微大限 is palace-based; this is NOT BaZi 大运.
- `BaZiCalendar.calculate_year_pillar / calculate_month_pillar /
  calculate_day_pillar / calculate_hour_pillar` → 干支 for any target date
  (流年/流月/流日/流时 stems & branches).
- `ZIWEI_SIHUA_RULES[stem]` → the 禄/权/科/忌 → star mapping for any stem
  (reused verbatim for every scope's dynamic 四化).
- `fatebridge/utils/data.ZIWEI_BRANCH_SEQUENCE` (寅-indexed palace branch order).
- Leap-month handling already implemented in `build_ziwei_chart` (十五日为界).

**The only genuinely new algorithm is 小限 (minor limit)**, ported from iztro.

## 3. Locked decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scope | All 6 cycle palaces + dynamic 四化; **no 流耀** | Matches parent Tier-2 spec; mostly assembly of existing parts; smallest valuable CI gate. |
| Input shape | **All of `target_year/month/day/hour` required** | Simpler contract; always compute all 6 cycles. |
| Convention conflicts | **Keep FateBridge's natal 大限; document iztro diffs** | Tier-1 大限 ranges/direction already shipped + tested; Tier 2 only *selects* among them. Don't reopen shipped behavior; surface divergence in spec + fixture notes. |
| Verification | **py-iztro in a throwaway venv → committed fixtures** | Genuinely independent oracle (closes the Tier-1 same-source caveat). No py-iztro at test time; no pydantic pollution of the main env. |
| Delivery | One PR (`feat/ziwei-horoscope`), after Tier 1 merges | One responsibility; small gate. |

## 4. Architecture

```
fatebridge/core/request_models.py     # + ZiweiHoroscopeRequest
fatebridge/core/metaphysics.py        # + build_ziwei_horoscope (+ small 小限 helper)
fatebridge/services/metaphysics.py    # + calculate_ziwei_horoscope, + _build_ziwei_horoscope_snapshot_text
fatebridge/services/tool_catalog.py   # + one ToolSpec (key=ziwei_horoscope)
scripts/gen_ziwei_horoscope_fixture.py  # one-shot py-iztro fixture generator (isolated venv)
tests/fixtures/ziwei_horoscope_reference.json  # committed reference
tests/test_ziwei_horoscope*.py        # unit + cross-check + describe/contract
skills/onda-mingge/SKILL.md           # 运限 subsection (real CLI + output)
```

### 4.1 Request — `ZiweiHoroscopeRequest(FateBridgeRequest)`
Inherits birth fields (name/gender/birth_year/month/day/hour/minute/place/
timezone/longitude). Adds, all **required**:
`target_year: int`, `target_month: int (1-12)`, `target_day: int (1-31)`,
`target_hour: int (0-23)`. Plus the standard optional
`selected_sections: List[str]`.

### 4.2 Core — `build_ziwei_horoscope(seed, gender, target_dt) -> Dict`
1. `chart = build_ziwei_chart(seed, gender)` → palaces, 大限 ranges, direction.
2. `nominal_age = target_year - birth_year + 1` (虚岁).
3. **大限**: select the palace whose `daxian` range contains `nominal_age`.
4. **小限**: ported iztro minor-limit rule (start palace by birth-year branch's
   三合 group; advance 1 palace/year; direction by gender×yin/yang).
5. **流年**: `calculate_year_pillar(target_year)` → palace whose branch == the
   year branch.
6. **流月 / 流日 / 流时**: `calculate_month/day/hour_pillar(...)` → palace whose
   branch == that pillar's branch.
7. For every scope build:
   ```
   {
     "scope": "大限"|"小限"|"流年"|"流月"|"流日"|"流时",
     "palace_name": str, "palace_index": int,
     "stem": str, "branch": str, "ganzhi": str,
     "mutagen": {"化禄": star, "化权": star, "化科": star, "化忌": star}  # ZIWEI_SIHUA_RULES[stem]
   }
   ```
8. Return `{"nominal_age": int, "target": {...}, "scopes": [ ...6 entries... ],
   "engine": "fatebridge-offline"}`.

### 4.3 Service — `calculate_ziwei_horoscope(person, target_*, selected_sections=None)`
Builds the seed (reusing `_build_person_seed`), calls `build_ziwei_horoscope`,
attaches `_build_ziwei_horoscope_snapshot_text` (起盘信息 + one section per
scope), and wraps with the standard `snapshot_export`. Output keys mirror the
other CN metaphysics tools (`analysis_type`, `ziwei_horoscope`, `snapshot_text`,
`snapshot_export`); transport layer adds `run_metadata`.

### 4.4 Tool registration
Append ONE `ToolSpec` to `tool_catalog.py`:
`key="ziwei_horoscope"`, `bind=person_invoke(calculate_ziwei_horoscope)` (or a
person+target bind mirroring the closest existing pattern),
`rest_path="/api/cn/ziwei/horoscope"`, `mcp_name="ziwei_horoscope"`,
CLI auto-derived, `describe` auto. No transport file edited by hand.

## 5. Verification (independent oracle)

`scripts/gen_ziwei_horoscope_fixture.py` — documented one-shot, run in an
**isolated throwaway venv** so py-iztro never touches the project env:
```
python -m venv /tmp/iztro_oracle && /tmp/iztro_oracle/bin/pip install py-iztro
/tmp/iztro_oracle/bin/python scripts/gen_ziwei_horoscope_fixture.py
```
It emits `tests/fixtures/ziwei_horoscope_reference.json` for ~3 (birth, target)
pairs covering all 6 scopes, recording for each scope: palace index/branch and
the four 四化 target stars. **Committed.**

`tests/test_ziwei_horoscope_crosscheck.py` compares
`build_ziwei_horoscope` output to the committed fixture (no py-iztro import).
Where iztro and FateBridge legitimately differ (e.g. 小限 direction start, leap
month), the diff is recorded in a `KNOWN_DIVERGENCES` block in the fixture/test
with a one-line rationale, and asserted as an *expected* difference rather than
silently passed.

`tests/test_ziwei_horoscope.py` adds cheap internal invariants regardless:
- the 大限 scope's palace range contains `nominal_age`;
- the 流年 scope branch == `calculate_year_pillar(target_year)[1]`;
- every scope's `mutagen` equals `ZIWEI_SIHUA_RULES[scope.stem]`;
- all 6 scopes present; palace_index in 0..11.

## 6. Skill doc
`skills/onda-mingge/SKILL.md` gains a 运限 subsection: what `ziwei_horoscope`
returns, a real runnable CLI command, and a trimmed real `snapshot_text`
excerpt. 人味儿 self-check on any prose.

## 7. Non-goals (YAGNI)
- No 流耀 (dynamic stars).
- No reopening Tier-1 natal 大限 direction/range logic.
- No new interpretive narrative beyond the skill-doc note.
- No partial-input handling (all target fields required).

## 8. Risks & mitigations
| Risk | Mitigation |
|---|---|
| 小限 convention differs from iztro | Port iztro's rule directly; cross-check fixture surfaces any diff; document in KNOWN_DIVERGENCES. |
| 流月 leap-month edge | Reuse `build_ziwei_chart`'s existing 十五日为界 handling. |
| py-iztro fixture friction (pydantic conflict) | Generate in an isolated venv; commit JSON; tests never import py-iztro. |
| Natal 大限 vs iztro mismatch | Decision: keep FateBridge's; document — does not block. |

## 9. Delivery checklist
- [ ] `ZiweiHoroscopeRequest` + `build_ziwei_horoscope` + 小限 helper
- [ ] `calculate_ziwei_horoscope` + snapshot text
- [ ] one `ToolSpec` (REST/MCP/CLI/describe verified)
- [ ] isolated-venv fixture generator + committed reference + cross-check test
- [ ] internal-invariant unit tests + e2e CLI + describe/contract test
- [ ] `onda-mingge` 运限 doc with real command/output
- [ ] all four gates green (pytest 3.10–3.13, black, isort, mypy)
