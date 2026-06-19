import json
from pathlib import Path

from fatebridge.core.metaphysics import (
    EARTHLY_BRANCHES,
    build_ziwei_chart,
    build_ziwei_horoscope,
)
from fatebridge.services.metaphysics import _build_analysis_seed, _build_person_seed
from fatebridge.utils.helpers import create_person_info

FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "ziwei_horoscope_reference.json"
)

# Documented, intentional differences from iztro. (case_label, scope) -> rationale.
# Populate ONLY after triage in Step 3; each entry needs a written reason.
KNOWN_DIVERGENCES: dict = {}

# py-iztro time index (子=0 .. 亥=11; 12=晚子) -> representative hour
_TIME_INDEX_TO_HOUR = {
    0: 0,
    1: 2,
    2: 4,
    3: 6,
    4: 8,
    5: 10,
    6: 12,
    7: 14,
    8: 16,
    9: 18,
    10: 20,
    11: 22,
    12: 23,
}


def _bazi_year(calendar_year: int, year_pillar_branch: str) -> int:
    """Return the BaZi year corresponding to a target date.

    If the target date falls before 立春 (Spring Equinox solar term boundary),
    its BaZi year pillar will still carry the *previous* year's branch.  In that
    case we return calendar_year - 1 so that 虚岁 is computed correctly.
    """
    expected_branch_idx = (calendar_year - 4) % 12
    actual_branch_idx = EARTHLY_BRANCHES.index(year_pillar_branch)
    return (
        calendar_year if actual_branch_idx == expected_branch_idx else calendar_year - 1
    )


def _our_scopes(case: dict) -> dict:
    by, bm, bd = (int(x) for x in case["birth"]["date"].split("-"))
    bh = _TIME_INDEX_TO_HOUR[case["birth"]["time_index"]]
    person = create_person_info(
        birth_year=by,
        birth_month=bm,
        birth_day=bd,
        birth_hour=bh,
        gender=case["birth"]["gender"],
    )
    natal_seed = _build_person_seed(person)
    chart = build_ziwei_chart(natal_seed, person.gender or "未知")
    ty, tm, td = (int(x) for x in case["target"]["date"].split("-"))
    th = _TIME_INDEX_TO_HOUR[case["target"]["time_index"]]
    target_seed = _build_analysis_seed(
        analysis_year=ty, analysis_month=tm, analysis_day=td, analysis_hour=th
    )
    # Use the BaZi year (from the year pillar branch) to compute 虚岁 correctly.
    # Dates before 立春 carry the previous year's branch, so we must use that year.
    bazi_yr = _bazi_year(ty, target_seed.pillars["year"][1])
    h = build_ziwei_horoscope(
        chart=chart,
        gender=person.gender or "未知",
        natal_year_branch=natal_seed.pillars["year"][1],
        target_pillars=target_seed.pillars,
        nominal_age=bazi_yr - by + 1,
    )
    return {s["scope"]: s for s in h["scopes"]}


def test_horoscope_matches_iztro_oracle():
    reference = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert reference, "fixture must not be empty"
    mismatches = []
    for label, case in reference.items():
        ours = _our_scopes(case)
        for scope, ref in case["scopes"].items():
            if (label, scope) in KNOWN_DIVERGENCES:
                continue
            got = ours[scope]
            if got["branch"] != ref["branch"]:
                mismatches.append(
                    f"{label}/{scope} branch: ours={got['branch']} ref={ref['branch']}"
                )
            if set(got["mutagen"].values()) != set(ref["mutagen"]):
                mismatches.append(
                    f"{label}/{scope} 四化: ours={sorted(got['mutagen'].values())} ref={sorted(ref['mutagen'])}"
                )
    assert not mismatches, "horoscope mismatches vs iztro oracle:\n" + "\n".join(
        mismatches
    )
