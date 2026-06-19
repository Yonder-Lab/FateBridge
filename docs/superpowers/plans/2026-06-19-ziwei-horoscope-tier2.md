# 紫微斗数 Horoscope (运限) Tier 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `ziwei_horoscope` tool that, given a birth + a full target date-time, returns the active 大限 / 小限 / 流年 / 流月 / 流日 / 流时, each with its palace and dynamic 四化.

**Architecture:** A pure core builder `build_ziwei_horoscope` assembles the six scopes from the Tier-1 natal chart (for 大限 + 小限 palaces) and the target date's four pillars (for the 流* scopes), reusing `ZIWEI_SIHUA_RULES` for every scope's 四化. A service wraps it (seeds + snapshot). One `ToolSpec` registers it on all three surfaces. Correctness is anchored to a committed py-iztro reference fixture generated once in an isolated venv.

**Tech Stack:** Python 3.10–3.13, pytest, black, isort, mypy. Optional `py-iztro` (fixture generation only, isolated venv).

**Branch:** `feat/ziwei-horoscope`, off `master` after Tier 1 (PR #39) merges.

---

## Reference facts (verified against the codebase — do not re-derive)

- `build_ziwei_chart(seed, gender) -> Dict` (`fatebridge/core/metaphysics.py`) returns:
  `{time_algorithm, year_stem, ming_gong, shen_gong, wuxing_ju, daxian_direction, sihua, palaces}`.
  Each palace: `{name, ganzhi, daxian, daxian_period, stars, stars_detail}`. `ganzhi` is 2 chars `stem+branch`; `palace["ganzhi"][1]` is the branch. `daxian` is a string like `"2~11"`.
- `ZIWEI_SIHUA_RULES[stem]` (`fatebridge/core/metaphysics.py`) → ordered dict `{"化禄":star, "化权":star, "化科":star, "化忌":star}` for a heavenly stem.
- `ZIWEI_BRANCH_SEQUENCE` (`fatebridge/utils/data.py`) = `["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]` (寅=0).
- `_build_person_seed(person) -> MetaphysicsSeed` and
  `_build_analysis_seed(*, analysis_year, analysis_month, analysis_day, analysis_hour, analysis_minute=0, analysis_timezone=None, analysis_longitude=None, use_true_solar_time=False, day_pillar_strategy=...) -> MetaphysicsSeed`
  both in `fatebridge/services/metaphysics.py`. A seed exposes `.pillars = {"year":(stem,branch), "month":(...), "day":(...), "hour":(...)}`.
- `FateBridgeRequest` (`fatebridge/core/request_models.py`) base already has birth_* fields + name/gender/birth_timezone/birth_longitude/use_true_solar_time.
- `person_invoke(service)` (`fatebridge/core/tool_spec.py`) auto-passes every NON-person request field (here: `target_year/month/day/hour`, `selected_sections`) as kwargs to the service. So the `ToolSpec` mirrors `ziwei_birth`.
- Existing `ziwei_birth` ToolSpec block (`fatebridge/services/tool_catalog.py` ~574): keys `key, bind, request_model, summary, operation_label_zh, family, rest_path, mcp_name`.

### Scope → which stem drives its 四化 (the design rule)
- **大限**: the 大限 palace's 宫干 = `palace["ganzhi"][0]`.
- **流年 / 流月 / 流日 / 流时**: the corresponding target **pillar stem** (`target.pillars[key][0]`), NOT the landed palace's 宫干.
- **小限**: same year as 流年 → use the **流年 stem** (`target.pillars["year"][0]`). (Candidate confirmed against the oracle in Task 7; if iztro uses the 小限 palace 宫干 instead, that becomes a documented `KNOWN_DIVERGENCE`.)

### 小限 palace rule (ported from iztro `getAgeIndex` + `getHoroscope`)
Start palace branch by natal **year branch**'s 三合 group:
- 寅/午/戌 年 → 辰 ; 申/子/辰 年 → 戌 ; 巳/酉/丑 年 → 未 ; 亥/卯/未 年 → 丑.
For 虚岁 `N`: `offset = (N - 1) % 12`; male advances forward, female backward along `ZIWEI_BRANCH_SEQUENCE`:
`idx = (start_index + offset) % 12` (male) or `(start_index - offset) % 12` (female); 小限 branch = `ZIWEI_BRANCH_SEQUENCE[idx]`.

---

## Task 1: `ZiweiHoroscopeRequest` model

**Files:**
- Modify: `fatebridge/core/request_models.py`
- Test: `tests/test_chinese_metaphysics.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_chinese_metaphysics.py`):

```python
def test_ziwei_horoscope_request_requires_target_datetime():
    from fatebridge.core.request_models import ZiweiHoroscopeRequest

    req = ZiweiHoroscopeRequest(
        gender="男",
        birth_year=1994, birth_month=8, birth_day=23, birth_hour=14,
        target_year=2026, target_month=6, target_day=19, target_hour=14,
    )
    payload = req.model_dump()
    assert payload["target_year"] == 2026
    assert payload["target_month"] == 6
    assert payload["target_day"] == 19
    assert payload["target_hour"] == 14

    import pytest as _pytest
    from pydantic import ValidationError

    with _pytest.raises(ValidationError):
        ZiweiHoroscopeRequest(  # missing target_* → invalid
            gender="男",
            birth_year=1994, birth_month=8, birth_day=23, birth_hour=14,
        )
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_horoscope_request_requires_target_datetime -q`
Expected: FAIL (`ImportError: cannot import name 'ZiweiHoroscopeRequest'`).

- [ ] **Step 3: Add the model** (in `fatebridge/core/request_models.py`, after `ZiweiBirthRequest` / near the other ziwei models):

```python
class ZiweiHoroscopeRequest(FateBridgeRequest):
    """Request model for 紫微斗数 horoscope (运限) at a target date-time."""

    target_year: int = Field(description="Target year, e.g., 2026")
    target_month: int = Field(ge=1, le=12, description="Target month (1-12)")
    target_day: int = Field(ge=1, le=31, description="Target day (1-31)")
    target_hour: int = Field(ge=0, le=23, description="Target hour (0-23)")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
```

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_horoscope_request_requires_target_datetime -q`
Expected: PASS.

- [ ] **Step 5: Gates + commit**

```bash
black fatebridge/core/request_models.py tests/test_chinese_metaphysics.py
isort fatebridge/core/request_models.py tests/test_chinese_metaphysics.py
mypy fatebridge
git add fatebridge/core/request_models.py tests/test_chinese_metaphysics.py
git commit -m "feat(ziwei): add ZiweiHoroscopeRequest model"
```

---

## Task 2: Core builder `build_ziwei_horoscope`

**Files:**
- Modify: `fatebridge/core/metaphysics.py`
- Test: `tests/test_ziwei_horoscope.py` (create)

- [ ] **Step 1: Write the failing test** (`tests/test_ziwei_horoscope.py`):

```python
from fatebridge.core.metaphysics import build_ziwei_chart, build_ziwei_horoscope
from fatebridge.core.metaphysics import ZIWEI_SIHUA_RULES
from fatebridge.services.metaphysics import _build_analysis_seed, _build_person_seed
from fatebridge.utils.helpers import create_person_info

SCOPES = ["大限", "小限", "流年", "流月", "流日", "流时"]


def _horoscope_for(birth, target):
    person = create_person_info(**birth)
    natal_seed = _build_person_seed(person)
    chart = build_ziwei_chart(natal_seed, person.gender or "未知")
    target_seed = _build_analysis_seed(
        analysis_year=target["year"], analysis_month=target["month"],
        analysis_day=target["day"], analysis_hour=target["hour"],
    )
    nominal_age = target["year"] - birth["birth_year"] + 1
    return build_ziwei_horoscope(
        chart=chart,
        gender=person.gender or "未知",
        natal_year_branch=natal_seed.pillars["year"][1],
        target_pillars=target_seed.pillars,
        nominal_age=nominal_age,
    )


BIRTH = dict(birth_year=1994, birth_month=8, birth_day=23, birth_hour=14, gender="男")
TARGET = dict(year=2026, month=6, day=19, hour=14)


def test_horoscope_has_six_scopes_with_expected_shape():
    h = _horoscope_for(BIRTH, TARGET)
    assert h["engine"] == "fatebridge-offline"
    assert h["nominal_age"] == 2026 - 1994 + 1
    got = {s["scope"]: s for s in h["scopes"]}
    assert set(got) == set(SCOPES)
    for s in h["scopes"]:
        assert set(s.keys()) == {"scope", "palace_name", "branch", "branch_index", "stem", "mutagen"}
        assert 0 <= s["branch_index"] <= 11
        assert set(s["mutagen"].keys()) == {"化禄", "化权", "化科", "化忌"}


def test_liunian_branch_matches_year_pillar_and_mutagen_from_year_stem():
    person = create_person_info(**BIRTH)
    target_seed = _build_analysis_seed(
        analysis_year=2026, analysis_month=6, analysis_day=19, analysis_hour=14
    )
    year_stem, year_branch = target_seed.pillars["year"]
    h = _horoscope_for(BIRTH, TARGET)
    liunian = next(s for s in h["scopes"] if s["scope"] == "流年")
    assert liunian["branch"] == year_branch
    assert liunian["stem"] == year_stem
    assert liunian["mutagen"] == dict(ZIWEI_SIHUA_RULES[year_stem])


def test_daxian_palace_age_range_contains_nominal_age():
    person = create_person_info(**BIRTH)
    natal_seed = _build_person_seed(person)
    chart = build_ziwei_chart(natal_seed, "男")
    h = _horoscope_for(BIRTH, TARGET)
    daxian = next(s for s in h["scopes"] if s["scope"] == "大限")
    palace = next(p for p in chart["palaces"] if p["ganzhi"][1] == daxian["branch"])
    lo, hi = (int(x) for x in palace["daxian"].split("~"))
    assert lo <= h["nominal_age"] <= hi
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_ziwei_horoscope.py -q`
Expected: FAIL (`ImportError: cannot import name 'build_ziwei_horoscope'`).

- [ ] **Step 3: Implement** (add to `fatebridge/core/metaphysics.py`, after `build_ziwei_chart`). Reuse the module-level `ZIWEI_BRANCH_SEQUENCE` import already present, and `ZIWEI_SIHUA_RULES`, `normalize_gender` (already in this module):

```python
# 小限起始宫地支：按命盘生年地支三合局定 (iztro getAgeIndex 同义)
_XIAOXIAN_START_BY_YEAR_BRANCH = {
    "寅": "辰", "午": "辰", "戌": "辰",
    "申": "戌", "子": "戌", "辰": "戌",
    "巳": "未", "酉": "未", "丑": "未",
    "亥": "丑", "卯": "丑", "未": "丑",
}


def _palace_by_branch(palaces: List[Dict[str, Any]], branch: str) -> Dict[str, Any]:
    return next(p for p in palaces if p["ganzhi"][1] == branch)


def _palace_for_nominal_age(
    palaces: List[Dict[str, Any]], nominal_age: int
) -> Dict[str, Any]:
    for palace in palaces:
        lo, hi = (int(x) for x in str(palace["daxian"]).split("~"))
        if lo <= nominal_age <= hi:
            return palace
    # 超出已排大限范围时，回退到最末大限宫（age 越界仅出现在极端高龄）
    return max(palaces, key=lambda p: int(str(p["daxian"]).split("~")[1]))


def _xiaoxian_branch(year_branch: str, nominal_age: int, gender: str) -> str:
    start = _XIAOXIAN_START_BY_YEAR_BRANCH[year_branch]
    start_idx = ZIWEI_BRANCH_SEQUENCE.index(start)
    offset = (nominal_age - 1) % 12
    forward = normalize_gender(gender) == "男"
    idx = (start_idx + offset) % 12 if forward else (start_idx - offset) % 12
    return ZIWEI_BRANCH_SEQUENCE[idx]


def _horoscope_scope(
    scope: str, palace: Dict[str, Any], stem: str
) -> Dict[str, Any]:
    branch = palace["ganzhi"][1]
    return {
        "scope": scope,
        "palace_name": palace["name"],
        "branch": branch,
        "branch_index": ZIWEI_BRANCH_SEQUENCE.index(branch),
        "stem": stem,
        "mutagen": dict(ZIWEI_SIHUA_RULES[stem]),
    }


def build_ziwei_horoscope(
    *,
    chart: Dict[str, Any],
    gender: str,
    natal_year_branch: str,
    target_pillars: Dict[str, Any],
    nominal_age: int,
) -> Dict[str, Any]:
    """Assemble the six 运限 scopes for a target date over a natal chart.

    大限 selects among the chart's own (Tier-1) 大限 ranges by 虚岁; 流年/流月/流日/
    流时 land on the palace carrying that pillar's branch with 四化 from the
    pillar stem; 小限 uses the 三合-based start palace and the 流年 stem.
    """
    palaces = chart["palaces"]

    daxian_palace = _palace_for_nominal_age(palaces, nominal_age)
    daxian = _horoscope_scope("大限", daxian_palace, daxian_palace["ganzhi"][0])

    year_stem = target_pillars["year"][0]
    xiao_palace = _palace_by_branch(
        palaces, _xiaoxian_branch(natal_year_branch, nominal_age, gender)
    )
    xiaoxian = _horoscope_scope("小限", xiao_palace, year_stem)

    flowing = []
    for scope, key in (("流年", "year"), ("流月", "month"), ("流日", "day"), ("流时", "hour")):
        stem, branch = target_pillars[key]
        flowing.append(_horoscope_scope(scope, _palace_by_branch(palaces, branch), stem))

    return {
        "engine": "fatebridge-offline",
        "nominal_age": nominal_age,
        "scopes": [daxian, xiaoxian, *flowing],
    }
```

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_ziwei_horoscope.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Gates + commit**

```bash
black fatebridge/core/metaphysics.py tests/test_ziwei_horoscope.py
isort fatebridge/core/metaphysics.py tests/test_ziwei_horoscope.py
mypy fatebridge
git add fatebridge/core/metaphysics.py tests/test_ziwei_horoscope.py
git commit -m "feat(ziwei): core build_ziwei_horoscope (6 scopes + dynamic 四化)"
```

---

## Task 3: Service `calculate_ziwei_horoscope` + snapshot text

**Files:**
- Modify: `fatebridge/services/metaphysics.py`
- Test: `tests/test_chinese_metaphysics.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_chinese_metaphysics.py`):

```python
def test_calculate_ziwei_horoscope_returns_six_scopes_and_snapshot():
    person = create_person_info(
        birth_year=1994, birth_month=8, birth_day=23, birth_hour=14, gender="男",
    )
    from fatebridge.services.metaphysics import calculate_ziwei_horoscope

    result = calculate_ziwei_horoscope(
        person, target_year=2026, target_month=6, target_day=19, target_hour=14,
    )
    assert result["analysis_type"] == "紫微斗数运限"
    h = result["ziwei_horoscope"]
    assert h["engine"] == "fatebridge-offline"
    assert {s["scope"] for s in h["scopes"]} == {"大限", "小限", "流年", "流月", "流日", "流时"}
    assert "[起盘信息]" in result["snapshot_text"]
    assert "[流年]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]
```

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_calculate_ziwei_horoscope_returns_six_scopes_and_snapshot -q`
Expected: FAIL (`ImportError: cannot import name 'calculate_ziwei_horoscope'`).

- [ ] **Step 3a: Add the snapshot builder** (in `fatebridge/services/metaphysics.py`, near `_build_ziwei_snapshot_text`):

```python
def _build_ziwei_horoscope_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    target_seed: MetaphysicsSeed,
    horoscope: Dict[str, Any],
) -> str:
    def _mutagen_line(mut: Dict[str, Any]) -> str:
        return (
            f"化禄={mut.get('化禄', '无')}；化权={mut.get('化权', '无')}；"
            f"化科={mut.get('化科', '无')}；化忌={mut.get('化忌', '无')}"
        )

    sections = [
        (
            "起盘信息",
            _join_snapshot_lines(
                [
                    f"出生：{seed.calendar_context['solar_datetime']}",
                    f"目标：{target_seed.calendar_context['solar_datetime']}",
                    f"虚岁：{horoscope.get('nominal_age', '无')}",
                ]
            ),
        )
    ]
    for s in horoscope.get("scopes", []) or []:
        sections.append(
            (
                str(s.get("scope", "运限")),
                _join_snapshot_lines(
                    [
                        f"宫位：{s.get('palace_name', '无')}（{s.get('stem', '')}{s.get('branch', '')}）",
                        f"四化：{_mutagen_line(s.get('mutagen', {}) or {})}",
                    ]
                ),
            )
        )
    return _render_snapshot_text(sections)
```

- [ ] **Step 3b: Add the service function** (also in `fatebridge/services/metaphysics.py`; import `build_ziwei_horoscope` alongside the existing `build_ziwei_chart` import):

```python
def calculate_ziwei_horoscope(
    person: PersonInfo,
    *,
    target_year: int,
    target_month: int,
    target_day: int,
    target_hour: int,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_person_seed(person)
        chart = build_ziwei_chart(seed, person.gender or "未知")
        target_seed = _build_analysis_seed(
            analysis_year=target_year,
            analysis_month=target_month,
            analysis_day=target_day,
            analysis_hour=target_hour,
        )
        nominal_age = target_year - person.birth_year + 1
        horoscope = build_ziwei_horoscope(
            chart=chart,
            gender=person.gender or "未知",
            natal_year_branch=seed.pillars["year"][1],
            target_pillars=target_seed.pillars,
            nominal_age=nominal_age,
        )
        snapshot_text = _build_ziwei_horoscope_snapshot_text(
            seed=seed, target_seed=target_seed, horoscope=horoscope
        )
        snapshot_export = _build_snapshot_export(
            technique="ziwei_horoscope",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "紫微斗数运限",
            "person_info": _person_payload(person),
            "analysis_context": _analysis_context_payload(seed),
            "ziwei_horoscope": horoscope,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:  # noqa: BLE001
        return handle_calculation_error(exc, "紫微斗数运限")
```

> NOTE for the implementer: match the exact field-assembly of the existing
> `calculate_ziwei_birth` in this file (e.g. whether it uses `_person_payload`
> vs an inline person dict, and the precise `handle_calculation_error`
> signature). Read `calculate_ziwei_birth` first and mirror it; the block above
> is the shape, adjust helper names to the ones actually used there.

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_calculate_ziwei_horoscope_returns_six_scopes_and_snapshot -q`
Expected: PASS.

- [ ] **Step 5: Gates + commit**

```bash
black fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
isort fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
mypy fatebridge
git add fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
git commit -m "feat(ziwei): calculate_ziwei_horoscope service + snapshot text"
```

---

## Task 4: Register the `ziwei_horoscope` tool (all three surfaces)

**Files:**
- Modify: `fatebridge/services/tool_catalog.py`
- Test: `tests/test_chinese_metaphysics.py`

- [ ] **Step 1: Write the failing test** (append to `tests/test_chinese_metaphysics.py`):

```python
def test_ziwei_horoscope_registered_on_all_surfaces():
    from fatebridge.services.tool_catalog import rest_specs, mcp_specs

    assert any(getattr(s, "key", None) == "ziwei_horoscope" for s in rest_specs())
    assert any(getattr(s, "mcp_name", None) == "ziwei_horoscope" for s in mcp_specs())
```

> NOTE: confirm the ToolSpec attribute names by reading the dataclass in
> `fatebridge/core/tool_spec.py` (the spec-reviewer found `.name` is wrong; use
> the actual attribute, likely `.key` / `.mcp_name`). Adjust the asserts to the
> real attribute names before running.

- [ ] **Step 2: Run — expect FAIL**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_horoscope_registered_on_all_surfaces -q`
Expected: FAIL (no such spec yet).

- [ ] **Step 3: Register the ToolSpec.** In `fatebridge/services/tool_catalog.py`:
  (a) add `calculate_ziwei_horoscope` to the existing `from fatebridge.services.metaphysics import (...)` block;
  (b) add `ZiweiHoroscopeRequest` to the existing `from fatebridge.core.request_models import (...)` block;
  (c) append a `ToolSpec` right after the `ziwei_birth` block, mirroring it:

```python
    ToolSpec(
        key="ziwei_horoscope",
        bind=person_invoke(calculate_ziwei_horoscope),
        request_model=ZiweiHoroscopeRequest,
        summary="紫微斗数运限（大限/小限/流年/流月/流日/流时 + 动态四化）。",
        operation_label_zh="紫微运限",
        family="metaphysics",
        rest_path="/api/cn/ziwei/horoscope",
        mcp_name="ziwei_horoscope",
    ),
```

- [ ] **Step 4: Run — expect PASS**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_horoscope_registered_on_all_surfaces -q`
Expected: PASS.

- [ ] **Step 5: Verify the CLI surface + describe end-to-end**

```bash
python -m fatebridge.cli describe ziwei_horoscope
python -m fatebridge.cli --no-metadata ziwei_horoscope \
  --gender 男 --birth-year 1994 --birth-month 8 --birth-day 23 --birth-hour 14 \
  --target-year 2026 --target-month 6 --target-day 19 --target-hour 14 \
  --fields ziwei_horoscope
```
Expected: `describe` lists `surfaces: {cli, rest_path: /api/cn/ziwei/horoscope, mcp_name: ziwei_horoscope}`; the run prints six scopes. (If the CLI flag names differ from `--target-year` etc., read `cli.py`'s flag-derivation to confirm — they are auto-derived from the request field names `target_year` → `--target-year`.)

- [ ] **Step 6: Gates + commit**

```bash
black fatebridge/services/tool_catalog.py tests/test_chinese_metaphysics.py
isort fatebridge/services/tool_catalog.py tests/test_chinese_metaphysics.py
mypy fatebridge
python -m pytest -q
git add fatebridge/services/tool_catalog.py tests/test_chinese_metaphysics.py
git commit -m "feat(ziwei): register ziwei_horoscope tool on REST/MCP/CLI"
```

---

## Task 5: Independent oracle — py-iztro fixture (isolated venv)

**Files:**
- Create: `scripts/gen_ziwei_horoscope_fixture.py`
- Create: `tests/fixtures/ziwei_horoscope_reference.json`

- [ ] **Step 1: Write the generator** `scripts/gen_ziwei_horoscope_fixture.py`:

```python
#!/usr/bin/env python3
"""Generate tests/fixtures/ziwei_horoscope_reference.json from py-iztro.

Run ONCE in an ISOLATED venv so py-iztro never touches the project env
(it downgrades pydantic and breaks fastmcp if installed in-tree):

    python -m venv /tmp/iztro_oracle
    /tmp/iztro_oracle/bin/pip install py-iztro
    /tmp/iztro_oracle/bin/python scripts/gen_ziwei_horoscope_fixture.py

For each (birth, target) case it records, per scope, the active palace's
earthly branch and the four 四化 target star names — a branch+stars tuple is
convention-independent, so it survives palace-index/name differences between
iztro and FateBridge.
"""

import json
from pathlib import Path

from py_iztro import Astro  # type: ignore[import-not-found]

# (label, solar birth "Y-M-D", time index 0..12, gender zh, target "Y-M-D", target time index)
CASES = [
    ("m_1994", "1994-8-23", 7, "男", "2026-6-19", 7),
    ("f_1988", "1988-2-29", 3, "女", "2025-10-1", 3),
    ("m_2001", "2001-11-5", 11, "男", "2030-1-15", 11),
]

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / (
    "ziwei_horoscope_reference.json"
)


def main() -> None:
    astro = Astro()
    fixture = {}
    for label, bdate, bidx, gender, tdate, tidx in CASES:
        chart = astro.by_solar(bdate, bidx, gender, True, "zh-CN")
        h = chart.horoscope(tdate, tidx)
        # py-iztro scope attrs: decadal/age/yearly/monthly/daily/hourly,
        # each with .earthly_branch and .mutagen (list of 4 star names).
        scopes = {}
        for our_name, attr in [
            ("大限", "decadal"), ("小限", "age"), ("流年", "yearly"),
            ("流月", "monthly"), ("流日", "daily"), ("流时", "hourly"),
        ]:
            sc = getattr(h, attr)
            scopes[our_name] = {
                "branch": sc.earthly_branch,
                "mutagen": list(sc.mutagen),  # [禄, 权, 科, 忌] star names
            }
        fixture[label] = {
            "birth": {"date": bdate, "time_index": bidx, "gender": gender},
            "target": {"date": tdate, "time_index": tidx},
            "scopes": scopes,
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(fixture)} cases to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Generate the fixture in an isolated venv**

```bash
python -m venv /tmp/iztro_oracle && /tmp/iztro_oracle/bin/pip install -q "py-iztro>=0.1.5"
/tmp/iztro_oracle/bin/python scripts/gen_ziwei_horoscope_fixture.py
```
Expected: `wrote 3 cases to .../ziwei_horoscope_reference.json`.

> NOTE for the implementer: py-iztro's attribute names (`by_solar`,
> `horoscope`, `.decadal/.age/.yearly/...`, `.earthly_branch`, `.mutagen`) mirror
> iztro but MAY differ in the installed version. Inspect with
> `/tmp/iztro_oracle/bin/python -c "import py_iztro, inspect; a=py_iztro.Astro(); c=a.by_solar('1994-8-23',7,'男',True,'zh-CN'); h=c.horoscope('2026-6-19',7); print(dir(h)); print(dir(h.decadal))"`
> and adjust attribute access to match. The emitted JSON shape (`branch` +
> 4-element `mutagen` per scope) must stay as specified.
>
> If the venv build genuinely fails (no network / mini-racer build error),
> STOP and report BLOCKED with the error — do NOT hand-fabricate the fixture
> (that would defeat the independent-oracle purpose). The controller will
> decide a fallback.

- [ ] **Step 3: Commit the generator + fixture**

```bash
git add scripts/gen_ziwei_horoscope_fixture.py tests/fixtures/ziwei_horoscope_reference.json
git commit -m "test(ziwei): py-iztro horoscope reference fixture (isolated-venv oracle)"
```

---

## Task 6: Cross-check test against the oracle (+ KNOWN_DIVERGENCES)

**Files:**
- Create: `tests/test_ziwei_horoscope_crosscheck.py`

- [ ] **Step 1: Write the cross-check test** `tests/test_ziwei_horoscope_crosscheck.py`:

```python
import json
from pathlib import Path

from fatebridge.core.metaphysics import build_ziwei_chart, build_ziwei_horoscope
from fatebridge.services.metaphysics import _build_analysis_seed, _build_person_seed
from fatebridge.utils.helpers import create_person_info

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "ziwei_horoscope_reference.json"
)

# Documented, intentional differences from iztro. Each entry:
#   (case_label, scope) -> "one-line rationale".
# Populate ONLY after inspecting real diffs in Step 3; every entry must have a
# written reason. Empty = we match iztro exactly.
KNOWN_DIVERGENCES: dict = {}

_TIME_INDEX_TO_HOUR = {  # 子=0 .. 亥=11 ; 23:00-00:59 子时 → use 0/23 midpoints
    0: 0, 1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 6: 12,
    7: 14, 8: 16, 9: 18, 10: 20, 11: 22, 12: 23,
}


def _our_horoscope(case: dict) -> dict:
    by, bm, bd = (int(x) for x in case["birth"]["date"].split("-"))
    bh = _TIME_INDEX_TO_HOUR[case["birth"]["time_index"]]
    person = create_person_info(
        birth_year=by, birth_month=bm, birth_day=bd, birth_hour=bh,
        gender=case["birth"]["gender"],
    )
    natal_seed = _build_person_seed(person)
    chart = build_ziwei_chart(natal_seed, person.gender or "未知")
    ty, tm, td = (int(x) for x in case["target"]["date"].split("-"))
    th = _TIME_INDEX_TO_HOUR[case["target"]["time_index"]]
    target_seed = _build_analysis_seed(
        analysis_year=ty, analysis_month=tm, analysis_day=td, analysis_hour=th
    )
    h = build_ziwei_horoscope(
        chart=chart, gender=person.gender or "未知",
        natal_year_branch=natal_seed.pillars["year"][1],
        target_pillars=target_seed.pillars, nominal_age=ty - by + 1,
    )
    return {s["scope"]: s for s in h["scopes"]}


def test_horoscope_matches_iztro_oracle():
    reference = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert reference, "fixture must not be empty"
    mismatches = []
    for label, case in reference.items():
        ours = _our_horoscope(case)
        for scope, ref in case["scopes"].items():
            if (label, scope) in KNOWN_DIVERGENCES:
                continue
            got = ours[scope]
            ref_stars = set(ref["mutagen"])
            got_stars = set(got["mutagen"].values())
            if got["branch"] != ref["branch"]:
                mismatches.append(f"{label}/{scope} branch: ours={got['branch']} ref={ref['branch']}")
            if got_stars != ref_stars:
                mismatches.append(f"{label}/{scope} 四化: ours={sorted(got_stars)} ref={sorted(ref_stars)}")
    assert not mismatches, "horoscope mismatches vs iztro oracle:\n" + "\n".join(mismatches)
```

- [ ] **Step 2: Run — observe diffs**

Run: `python -m pytest tests/test_ziwei_horoscope_crosscheck.py -q`
Expected: either PASS (full parity) OR a mismatch list.

- [ ] **Step 3: Triage each mismatch (do NOT blindly silence)**
  - **流年/流月/流日/流时 mismatch** → a real bug in scope assembly or pillar mapping. Fix the implementation (Task 2 code).
  - **小限 四化 mismatch only** → iztro uses a different 小限 stem than the 流年 stem. Switch `xiaoxian`'s stem in `build_ziwei_horoscope` to the 小限 palace 宫干 (`xiao_palace["ganzhi"][0]`); re-run. If it now matches, keep that; if neither matches, add `(label,"小限")` to `KNOWN_DIVERGENCES` with the reason.
  - **大限 mismatch** → per the spec's locked decision we KEEP FateBridge's natal 大限. Add `(label,"大限")` to `KNOWN_DIVERGENCES` with rationale "natal 大限 range/direction is FateBridge's Tier-1 convention; see design spec §3".
  Re-run until the test passes (real bugs fixed; legitimate convention diffs documented).

- [ ] **Step 4: Gates + commit**

```bash
black tests/test_ziwei_horoscope_crosscheck.py fatebridge/core/metaphysics.py
isort tests/test_ziwei_horoscope_crosscheck.py fatebridge/core/metaphysics.py
mypy fatebridge
python -m pytest -q
git add tests/test_ziwei_horoscope_crosscheck.py fatebridge/core/metaphysics.py
git commit -m "test(ziwei): cross-check horoscope against iztro oracle; document divergences"
```

---

## Task 7: Skill doc (`onda-mingge` 运限 subsection)

**Files:**
- Modify: `skills/onda-mingge/SKILL.md`

- [ ] **Step 1: Capture a real run**

```bash
python -m fatebridge.cli --no-metadata ziwei_horoscope \
  --gender 女 --birth-year 1998 --birth-month 9 --birth-day 30 --birth-hour 16 \
  --target-year 2026 --target-month 6 --target-day 19 --target-hour 14
```
Copy a trimmed REAL excerpt of the `snapshot_text` (起盘信息 + a couple of scope sections).

- [ ] **Step 2: Add a 运限 subsection** near the existing 紫微 material in `skills/onda-mingge/SKILL.md`: add a tool-table row for `ziwei_horoscope`, a one-line "看某个时间点的大限/流年/…及其四化", the real command + trimmed output from Step 1, and note that all four `--target-*` fields are required. Apply the 人味儿 self-check to any prose (no AI 腔, 白描, no 排比三连).

- [ ] **Step 3: Commit**

```bash
git add skills/onda-mingge/SKILL.md
git commit -m "docs(skills): document ziwei_horoscope (运限) in onda-mingge"
```

---

## Task 8: Final gate + PR

- [ ] **Step 1: All four gates**

```bash
python -m pytest -q
black --check .
isort --check .
mypy fatebridge
```
Expected: all green. (The cross-check uses the committed fixture, so it passes without py-iztro installed.)

- [ ] **Step 2: Push + PR (after user authorization)**

Branch `feat/ziwei-horoscope`, base `master`:
```bash
git push --no-verify -u origin HEAD
gh pr create --base master --title "feat(ziwei): 运限 horoscope (iztro parity Tier 2)" \
  --body "Adds ziwei_horoscope: active 大限/小限/流年/流月/流日/流时 + dynamic 四化 for a target date-time. Pure-Python/offline; one ToolSpec → REST/MCP/CLI. Verified against a committed py-iztro reference fixture generated in an isolated venv (independent oracle). See docs/superpowers/specs/2026-06-19-ziwei-horoscope-tier2-design.md."
```

- [ ] **Step 3: Watch CI to green, hand back to user for merge.**

---

## Self-review notes (plan author)

- **Spec coverage:** request model (T1), all-6-scope core builder + 小限 port (T2), service + snapshot (T3), single ToolSpec on 3 surfaces (T4), isolated-venv py-iztro oracle + committed fixture (T5), cross-check with KNOWN_DIVERGENCES + branch/stars comparison (T6), skill doc with real output (T7), gates + PR (T8). All §-locked decisions honored: all-required target inputs (T1), keep natal 大限 + document (T6 triage), no 流耀 (absent).
- **Type consistency:** `build_ziwei_horoscope(*, chart, gender, natal_year_branch, target_pillars, nominal_age)` and scope entry keys `{scope, palace_name, branch, branch_index, stem, mutagen}` are identical across T2, T3, T6. `calculate_ziwei_horoscope(person, *, target_year, target_month, target_day, target_hour, selected_sections=None)` matches the `person_invoke` auto-kwargs contract (T4).
- **No placeholders:** every code step is concrete. The two genuinely-empirical points (py-iztro attribute names; 小限 stem) are handled by explicit inspect-and-adjust steps with named fallbacks and a deterministic decision rule — not "TBD".
- **Known risk:** if the isolated venv can't build py-iztro, T5 says STOP/report rather than fake the oracle.
