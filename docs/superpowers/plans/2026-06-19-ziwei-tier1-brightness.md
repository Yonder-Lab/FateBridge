# 紫微斗数 Tier 1 — Star Brightness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add iztro-grade star **brightness** (庙/旺/得/利/平/不/陷) to FateBridge's native 紫微斗数 chart, exposed as an additive `stars_detail` field per palace, with the brightness table verifiable against iztro's authoritative source and (optionally) py-iztro.

**Architecture:** A new pure-data module `fatebridge/core/ziwei_tables.py` holds the brightness lookup table (transcribed from iztro's `src/data/stars.ts`, which is 寅-indexed — identical to FateBridge's `ZIWEI_BRANCH_SEQUENCE`, so no index translation) plus two small helpers. `build_ziwei_chart` consumes them to attach `stars_detail` to each palace without mutating the existing `stars` list. The snapshot text gains brightness annotations. Everything stays pure-Python/offline; py-iztro is an *optional* test-only extra used for a skip-gated cross-check.

**Tech Stack:** Python 3.10–3.13, pytest, black, isort, mypy. Optional `py-iztro` (test-only).

---

## Reference facts (verified against the codebase, do not re-derive)

- `fatebridge/core/metaphysics.py`:
  - `ZIWEI_BRANCH_SEQUENCE = ["寅","卯","辰","巳","午","未","申","酉","戌","亥","子","丑"]` (寅=index 0).
  - `build_ziwei_chart(seed, gender)` ends ≈ line 2087–2113. After `_apply_sihua_to_palaces`, each `palace["stars"]` is `sorted(dict.fromkeys(...))` and **mutated to contain mutagen-suffixed names** like `"紫微化科"`. The returned dict has keys: `time_algorithm, year_stem, ming_gong, shen_gong, wuxing_ju, daxian_direction, sihua, palaces`.
  - Each `palace` dict has keys: `name, ganzhi, daxian, daxian_period, stars`. `palace["ganzhi"][1]` is the palace's earthly branch.
- `fatebridge/services/metaphysics.py`:
  - `_build_ziwei_snapshot_text(*, seed, ziwei_birth)` (≈ line 493) builds palace lines from `palace.get("stars", [])`.
  - `calculate_ziwei_birth` sets `ziwei_birth["engine"] = "fatebridge-offline"`.
- `tests/test_chinese_metaphysics.py` already imports `create_person_info` (line 36) and has `test_calculate_ziwei_birth_returns_twelve_palaces` (line 151). Add new tests in this file.
- Mutagen suffixes that can be appended to a star name: `化禄`, `化权`, `化科`, `化忌`.

### Authoritative brightness data (transcribed from iztro `src/data/stars.ts`, 寅-indexed)

Romanization map: `miao→庙, wang→旺, de→得, li→利, ping→平, bu→不, xian→陷`, empty `''→None`.
This exact table is embedded in Task 1's code block — it is the single source of the values.

---

## Task 1: Brightness table + helpers (`ziwei_tables.py`)

**Files:**
- Create: `fatebridge/core/ziwei_tables.py`
- Test: `tests/test_ziwei_tables.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ziwei_tables.py`:

```python
import pytest

from fatebridge.core.ziwei_tables import (
    ZIWEI_STAR_BRIGHTNESS,
    lookup_star_brightness,
    split_star_mutagen,
)


def test_table_shape_is_twelve_per_star():
    for star, row in ZIWEI_STAR_BRIGHTNESS.items():
        assert len(row) == 12, f"{star} must have 12 branch entries"


def test_lookup_known_authoritative_cells():
    # 寅-indexed: 寅=0, 午=4, 丑=11 (ZIWEI_BRANCH_SEQUENCE order)
    assert lookup_star_brightness("紫微", "午") == "庙"   # ziweiMaj[4]=miao
    assert lookup_star_brightness("紫微", "寅") == "旺"   # ziweiMaj[0]=wang
    assert lookup_star_brightness("太阳", "戌") == "不"   # taiyangMaj[8]=bu
    assert lookup_star_brightness("天机", "未") == "陷"   # tianjiMaj[5]=xian


def test_lookup_unknown_or_empty_returns_none():
    assert lookup_star_brightness("天魁", "子") is None      # not in table
    assert lookup_star_brightness("擎羊", "寅") is None      # qingyangMin[0]=''
    assert lookup_star_brightness("陀罗", "卯") is None      # tuoluoMin[1]=''
    assert lookup_star_brightness("紫微", "辰X") is None     # bad branch


def test_split_star_mutagen():
    assert split_star_mutagen("紫微化科") == ("紫微", "化科")
    assert split_star_mutagen("太阴化忌") == ("太阴", "化忌")
    assert split_star_mutagen("天府") == ("天府", None)
    assert split_star_mutagen("") == ("", None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ziwei_tables.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'fatebridge.core.ziwei_tables'`

- [ ] **Step 3: Write the implementation**

Create `fatebridge/core/ziwei_tables.py`:

```python
"""
Static lookup tables ported from iztro (紫微斗数), kept separate from the
placement logic in ``metaphysics.py`` so the transcribed data is auditable.

Source of truth: iztro ``src/data/stars.ts`` -> ``STARS_INFO[*].brightness``.
Each brightness row is ordered "从寅开始" (starting at 寅), which is exactly
FateBridge's ``ZIWEI_BRANCH_SEQUENCE`` order, so no index translation is needed.
Romanization map applied: miao=庙, wang=旺, de=得, li=利, ping=平, bu=不,
xian=陷; iztro's empty string '' (brightness not applicable at that branch)
becomes ``None`` here.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# Branch order shared with metaphysics.ZIWEI_BRANCH_SEQUENCE (寅=0 ... 丑=11).
_BRANCH_ORDER: List[str] = [
    "寅", "卯", "辰", "巳", "午", "未",
    "申", "酉", "戌", "亥", "子", "丑",
]

_MUTAGEN_SUFFIXES: Tuple[str, ...] = ("化禄", "化权", "化科", "化忌")

# star name -> 12 brightness values (寅-indexed); None = not applicable.
ZIWEI_STAR_BRIGHTNESS: Dict[str, List[Optional[str]]] = {
    # --- 14 主星 ---
    "紫微": ["旺", "旺", "得", "旺", "庙", "庙", "旺", "旺", "得", "旺", "平", "庙"],
    "天机": ["得", "旺", "利", "平", "庙", "陷", "得", "旺", "利", "平", "庙", "陷"],
    "太阳": ["旺", "庙", "旺", "旺", "旺", "得", "得", "陷", "不", "陷", "陷", "不"],
    "武曲": ["得", "利", "庙", "平", "旺", "庙", "得", "利", "庙", "平", "旺", "庙"],
    "天同": ["利", "平", "平", "庙", "陷", "不", "旺", "平", "平", "庙", "旺", "不"],
    "廉贞": ["庙", "平", "利", "陷", "平", "利", "庙", "平", "利", "陷", "平", "利"],
    "天府": ["庙", "得", "庙", "得", "旺", "庙", "得", "旺", "庙", "得", "庙", "庙"],
    "太阴": ["旺", "陷", "陷", "陷", "不", "不", "利", "不", "旺", "庙", "庙", "庙"],
    "贪狼": ["平", "利", "庙", "陷", "旺", "庙", "平", "利", "庙", "陷", "旺", "庙"],
    "巨门": ["庙", "庙", "陷", "旺", "旺", "不", "庙", "庙", "陷", "旺", "旺", "不"],
    "天相": ["庙", "陷", "得", "得", "庙", "得", "庙", "陷", "得", "得", "庙", "庙"],
    "天梁": ["庙", "庙", "庙", "陷", "庙", "旺", "陷", "得", "庙", "陷", "庙", "旺"],
    "七杀": ["庙", "旺", "庙", "平", "旺", "庙", "庙", "庙", "庙", "平", "旺", "庙"],
    "破军": ["得", "陷", "旺", "平", "庙", "旺", "得", "陷", "旺", "平", "庙", "旺"],
    # --- 辅煞星 with brightness ---
    "文昌": ["陷", "利", "得", "庙", "陷", "利", "得", "庙", "陷", "利", "得", "庙"],
    "文曲": ["平", "旺", "得", "庙", "陷", "旺", "得", "庙", "陷", "旺", "得", "庙"],
    "火星": ["庙", "利", "陷", "得", "庙", "利", "陷", "得", "庙", "利", "陷", "得"],
    "铃星": ["庙", "利", "陷", "得", "庙", "利", "陷", "得", "庙", "利", "陷", "得"],
    "擎羊": [None, "陷", "庙", None, "陷", "庙", None, "陷", "庙", None, "陷", "庙"],
    "陀罗": ["陷", None, "庙", "陷", None, "庙", "陷", None, "庙", "陷", None, "庙"],
}


def lookup_star_brightness(star: str, branch: str) -> Optional[str]:
    """Return the brightness char for ``star`` at earthly ``branch``.

    Returns ``None`` when the star has no brightness, the branch is unknown,
    or the branch is one where the star's brightness is not applicable.
    """
    row = ZIWEI_STAR_BRIGHTNESS.get(star)
    if row is None or branch not in _BRANCH_ORDER:
        return None
    return row[_BRANCH_ORDER.index(branch)]


def split_star_mutagen(star_label: str) -> Tuple[str, Optional[str]]:
    """Split a possibly mutagen-suffixed star label.

    ``"紫微化科"`` -> ``("紫微", "化科")``; ``"天府"`` -> ``("天府", None)``.
    """
    for suffix in _MUTAGEN_SUFFIXES:
        if star_label.endswith(suffix):
            return star_label[: -len(suffix)], suffix
    return star_label, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ziwei_tables.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Format, type-check, commit**

```bash
black fatebridge/core/ziwei_tables.py tests/test_ziwei_tables.py
isort fatebridge/core/ziwei_tables.py tests/test_ziwei_tables.py
mypy fatebridge/core/ziwei_tables.py
git add fatebridge/core/ziwei_tables.py tests/test_ziwei_tables.py
git commit -m "feat(ziwei): add star brightness table + helpers (Tier 1)"
```
Expected: black/isort report files unchanged or reformatted; mypy "Success: no issues"; commit created.

---

## Task 2: Attach `stars_detail` in `build_ziwei_chart`

**Files:**
- Modify: `fatebridge/core/metaphysics.py` (in `build_ziwei_chart`, just before the final `return {...}` ≈ line 2096)
- Test: `tests/test_chinese_metaphysics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chinese_metaphysics.py`:

```python
def test_ziwei_birth_palaces_have_stars_detail():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_ziwei_birth(person)
    palaces = result["ziwei_birth"]["palaces"]

    for palace in palaces:
        # additive: legacy `stars` list is preserved unchanged
        assert "stars" in palace
        assert "stars_detail" in palace
        assert len(palace["stars_detail"]) == len(palace["stars"])
        for legacy, detail in zip(palace["stars"], palace["stars_detail"]):
            assert legacy == detail["label"]
            assert set(detail.keys()) == {"name", "label", "brightness", "mutagen"}

    # at least one major star must carry a non-null brightness
    all_details = [d for p in palaces for d in p["stars_detail"]]
    assert any(d["brightness"] is not None for d in all_details)

    # mutagen parsing: any 化X suffix in legacy stars surfaces in detail.mutagen
    for palace in palaces:
        for detail in palace["stars_detail"]:
            if detail["mutagen"] is not None:
                assert detail["label"] == f"{detail['name']}{detail['mutagen']}"
                assert detail["mutagen"] in {"化禄", "化权", "化科", "化忌"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_birth_palaces_have_stars_detail -q`
Expected: FAIL with `KeyError: 'stars_detail'`

- [ ] **Step 3: Add the import**

At the top of `fatebridge/core/metaphysics.py`, add to the existing imports block:

```python
from fatebridge.core.ziwei_tables import (
    lookup_star_brightness,
    split_star_mutagen,
)
```

- [ ] **Step 4: Build `stars_detail` before the return**

In `build_ziwei_chart`, immediately after the line
`palace["stars"] = sorted(dict.fromkeys(palace["stars"]))` block (the `for palace in palaces:` loop ≈ line 2088-2089) and before `ming_palace = next(...)`, insert:

```python
    # --- Tier 1: attach brightness + parsed mutagen as an additive field ---
    # `palace["stars"]` (legacy) stays a list[str] of mutagen-suffixed labels;
    # `stars_detail` mirrors it 1:1 with structured data.
    for palace in palaces:
        branch = palace["ganzhi"][1]
        detail = []
        for label in palace["stars"]:
            base_name, mutagen = split_star_mutagen(label)
            detail.append(
                {
                    "name": base_name,
                    "label": label,
                    "brightness": lookup_star_brightness(base_name, branch),
                    "mutagen": mutagen,
                }
            )
        palace["stars_detail"] = detail
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_birth_palaces_have_stars_detail -q`
Expected: PASS

- [ ] **Step 6: Run the full ziwei test group to confirm no regression**

Run: `python -m pytest tests/test_chinese_metaphysics.py -q -k ziwei`
Expected: PASS (existing `test_calculate_ziwei_birth_returns_twelve_palaces` still green — `stars` is untouched)

- [ ] **Step 7: Format, type-check, commit**

```bash
black fatebridge/core/metaphysics.py tests/test_chinese_metaphysics.py
isort fatebridge/core/metaphysics.py tests/test_chinese_metaphysics.py
mypy fatebridge/core/metaphysics.py
git add fatebridge/core/metaphysics.py tests/test_chinese_metaphysics.py
git commit -m "feat(ziwei): attach additive stars_detail with brightness to chart"
```
Expected: mypy "Success"; commit created.

---

## Task 3: Brightness annotations in snapshot text

**Files:**
- Modify: `fatebridge/services/metaphysics.py` (`_build_ziwei_snapshot_text` ≈ line 506-516)
- Test: `tests/test_chinese_metaphysics.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_chinese_metaphysics.py`:

```python
def test_ziwei_snapshot_text_annotates_brightness():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_ziwei_birth(person)
    snapshot = result["snapshot_text"]

    # brightness should be rendered in parentheses next to at least one star,
    # e.g. "紫微(庙)" — assert at least one bracketed brightness char appears.
    assert any(f"({b})" in snapshot for b in ("庙", "旺", "得", "利", "平", "不", "陷"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_snapshot_text_annotates_brightness -q`
Expected: FAIL (no bracketed brightness rendered yet)

- [ ] **Step 3: Render brightness from `stars_detail`**

In `_build_ziwei_snapshot_text`, replace the palace-line construction loop (the
`for palace in ziwei_birth.get("palaces", []) or []:` block, ≈ lines 507-516) with:

```python
    for palace in ziwei_birth.get("palaces", []) or []:
        if not isinstance(palace, dict):
            continue
        details = palace.get("stars_detail") or []
        if details:
            star_text = (
                "、".join(
                    f"{d['label']}({d['brightness']})"
                    if d.get("brightness")
                    else d["label"]
                    for d in details
                )
                or "无"
            )
        else:
            # fallback for any caller that didn't populate stars_detail
            star_text = "、".join(palace.get("stars", []) or []) or "无"
        palace_lines.append(
            (
                f"{palace.get('name', '宫位')}：{palace.get('ganzhi', '无')}；"
                f"大限：{palace.get('daxian', '无')}；"
                f"星曜：{star_text}"
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_chinese_metaphysics.py::test_ziwei_snapshot_text_annotates_brightness -q`
Expected: PASS

- [ ] **Step 5: Format, type-check, commit**

```bash
black fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
isort fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
mypy fatebridge/services/metaphysics.py
git add fatebridge/services/metaphysics.py tests/test_chinese_metaphysics.py
git commit -m "feat(ziwei): annotate star brightness in snapshot text"
```
Expected: mypy "Success"; commit created.

---

## Task 4: py-iztro cross-check (optional, skip-gated) + committed fixture

**Files:**
- Modify: `pyproject.toml` (add an `iztro-verify` optional extra)
- Create: `tests/fixtures/ziwei_brightness_reference.json`
- Create: `scripts/gen_ziwei_brightness_fixture.py`
- Test: `tests/test_ziwei_brightness_crosscheck.py`

- [ ] **Step 1: Add the optional extra to `pyproject.toml`**

In `[project.optional-dependencies]`, after the `dev = [...]` list, add:

```toml
iztro-verify = [
    "py-iztro>=0.1.5",
]
```

- [ ] **Step 2: Create the fixture generator script**

Create `scripts/gen_ziwei_brightness_fixture.py`:

```python
"""Regenerate the brightness reference fixture from py-iztro.

Run manually (requires the optional extra):
    pip install -e ".[iztro-verify]"
    python scripts/gen_ziwei_brightness_fixture.py

Emits tests/fixtures/ziwei_brightness_reference.json mapping
"<star>@<branch>" -> "<brightness>" for every major/minor star that py-iztro
reports with a non-empty brightness, for one canonical birth.
"""

import json
from pathlib import Path

from py_iztro import Astro  # type: ignore[import-not-found]

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / (
    "ziwei_brightness_reference.json"
)


def main() -> None:
    astro = Astro()
    # canonical birth: 1994-08-23 14:30 (hour index 7 = 未时), male, zh-CN
    astrolabe = astro.by_solar("1994-8-23", 7, "男", True, "zh-CN")
    ref = {}
    for palace in astrolabe.palaces:
        branch = palace.earthly_branch
        for star in list(palace.major_stars) + list(palace.minor_stars):
            if star.brightness:
                ref[f"{star.name}@{branch}"] = star.brightness
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(ref, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(ref)} entries to {OUT}")


if __name__ == "__main__":
    main()
```

> NOTE for the implementer: py-iztro's attribute names mirror iztro. If
> `by_solar`/`earthly_branch`/`major_stars` differ in the installed version,
> adjust to the actual API (inspect with `dir()`), regenerate, and keep the
> emitted JSON shape `"<star>@<branch>": "<brightness>"`.

- [ ] **Step 3: Generate and commit the fixture**

Run:
```bash
pip install -e ".[iztro-verify]"
python scripts/gen_ziwei_brightness_fixture.py
```
Expected: prints `wrote N entries ...` and creates
`tests/fixtures/ziwei_brightness_reference.json`.

If py-iztro cannot be installed in this environment, create the fixture by hand
from the authoritative table in Task 1 for the canonical birth's actual star
placements (run `calculate_ziwei_birth` for 1994-08-23 14:30 男 and read each
palace's `stars_detail`), writing the same `"<star>@<branch>": "<brightness>"`
shape. The cross-check test below then becomes a regression guard either way.

- [ ] **Step 4: Write the cross-check test**

Create `tests/test_ziwei_brightness_crosscheck.py`:

```python
import json
from pathlib import Path

from fatebridge.core.ziwei_tables import lookup_star_brightness

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "ziwei_brightness_reference.json"
)


def test_our_table_matches_reference_fixture():
    reference = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert reference, "fixture must not be empty"
    mismatches = []
    for key, expected in reference.items():
        star, branch = key.split("@")
        actual = lookup_star_brightness(star, branch)
        if actual != expected:
            mismatches.append(f"{key}: ours={actual} ref={expected}")
    assert not mismatches, "brightness mismatches:\n" + "\n".join(mismatches)
```

- [ ] **Step 5: Run the cross-check test**

Run: `python -m pytest tests/test_ziwei_brightness_crosscheck.py -q`
Expected: PASS (our literal table agrees with the reference for every entry)

- [ ] **Step 6: Format, type-check, commit**

```bash
black scripts/gen_ziwei_brightness_fixture.py tests/test_ziwei_brightness_crosscheck.py
isort scripts/gen_ziwei_brightness_fixture.py tests/test_ziwei_brightness_crosscheck.py
mypy fatebridge/core/ziwei_tables.py
git add pyproject.toml scripts/gen_ziwei_brightness_fixture.py \
        tests/fixtures/ziwei_brightness_reference.json \
        tests/test_ziwei_brightness_crosscheck.py
git commit -m "test(ziwei): cross-check brightness table against iztro reference fixture"
```
Expected: commit created.

---

## Task 5: Skill docs (`onda-mingge`, `onda-xingpan`)

**Files:**
- Modify: `skills/onda-mingge/SKILL.md`
- Modify: `skills/onda-xingpan/SKILL.md`

- [ ] **Step 1: Inspect current skill docs and a real CLI invocation**

Run:
```bash
ls skills/onda-mingge skills/onda-xingpan
python -m fatebridge.cli ziwei_birth --help 2>/dev/null | head -30 || \
  python -m fatebridge.cli --help | head -40
```
Expected: confirm the exact CLI subcommand + flags for the ziwei birth tool.

- [ ] **Step 2: Capture a real, runnable example with brightness**

Run the ziwei birth tool via CLI for the canonical birth and project the new
field to show it works (use the real subcommand/flags discovered in Step 1):

```bash
python -m fatebridge.cli ziwei_birth \
  --birth-year 1994 --birth-month 8 --birth-day 23 --birth-hour 14 \
  --gender 男 --fields ziwei_birth.palaces.0.stars_detail
```
Expected: prints the first palace's `stars_detail` with `brightness` values.
Copy the actual command + a trimmed real output for the docs (do not invent output).

- [ ] **Step 3: Add a "星曜亮度 (brightness)" subsection to both skill docs**

In each `SKILL.md`, add a short section documenting:
- that each palace now carries `stars_detail` with `name`/`label`/`brightness`/`mutagen`,
- the brightness scale 庙>旺>得>利>平>不>陷,
- the real CLI command and trimmed output from Step 2,
- that `stars` (legacy list) is unchanged.
Apply the "人味儿" self-check to any interpretive prose (no AI 腔, no 排比三连,
白描优先).

- [ ] **Step 4: Commit**

```bash
git add skills/onda-mingge/SKILL.md skills/onda-xingpan/SKILL.md
git commit -m "docs(skills): document ziwei star brightness (stars_detail)"
```
Expected: commit created.

---

## Task 6: Full gate + open PR

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass (the optional cross-check uses the committed fixture, so
it passes without py-iztro installed).

- [ ] **Step 2: Run all four CI gates locally**

Run:
```bash
python -m pytest -q
black --check .
isort --check .
mypy fatebridge
```
Expected: all four succeed.

- [ ] **Step 3: Push branch and open PR (after user authorization)**

Per the established PR workflow, branch name `feat/ziwei-brightness`, base `master`:
```bash
git push -u origin HEAD
gh pr create --base master --title "feat(ziwei): star brightness (iztro parity Tier 1)" \
  --body "Adds iztro-grade star brightness as an additive \`stars_detail\` field per palace. Pure-Python/offline; table transcribed from iztro src/data/stars.ts and cross-checked via a committed reference fixture. Backward-compatible: legacy \`stars\` list unchanged. First of three phased PRs toward iztro parity (see docs/superpowers/specs/2026-06-19-iztro-ziwei-parity-design.md)."
```
Expected: PR created; CI runs across Python 3.10–3.13 + GitGuardian.

- [ ] **Step 4: Watch CI to green, then hand back to user for merge decision.**

---

## Self-review notes (completed by plan author)

- **Spec coverage (Tier 1 only):** brightness table ✓ (Task 1), additive
  `stars_detail` preserving `stars` ✓ (Task 2), snapshot annotation ✓ (Task 3),
  py-iztro dev/test-only anchor + committed fixture ✓ (Task 4), skill-doc updates
  with runnable commands ✓ (Task 5), single-PR CI gate ✓ (Task 6). Tiers 2–3 are
  intentionally out of scope for this plan (separate PRs).
- **Type consistency:** `lookup_star_brightness(star, branch) -> Optional[str]`
  and `split_star_mutagen(label) -> Tuple[str, Optional[str]]` are used with the
  same signatures in Tasks 2 and 4. `stars_detail` entry keys
  `{name, label, brightness, mutagen}` are identical across Tasks 2, 3, and the
  tests.
- **No placeholders:** the full brightness table is embedded literal data (Task 1),
  transcribed from the authoritative iztro source; no value is left "TBD".
- **Tool catalog:** Tier 1 adds **no new tool** — it enriches the existing
  `ziwei_birth` output — so `tool_catalog.py` needs no change. (New tools arrive
  in Tier 2/3.)
```
