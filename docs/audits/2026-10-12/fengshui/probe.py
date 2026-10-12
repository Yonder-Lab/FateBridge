"""Research arithmetic only; this does not install a Feng Shui service.

Run with the project's installed Python, from the repository root:
  .venv/bin/python docs/audits/2026-10-12/fengshui/probe.py

Sources and limits are recorded in the accompanying research report. Source
spot checks, algebraic invariants, and existing calendar behavior are distinct
checks; none validate the real-world predictive claims of these traditions.
"""

import json
from collections import Counter
from datetime import timedelta, timezone
from pathlib import Path

from fatebridge.core.almanac import get_bazi_year, get_solar_terms_for_year
from fatebridge.core.divination import BAGUA_BY_NAME
from fatebridge.services.tool_catalog import CATALOG


def wrap9(value):
    return (value - 1) % 9 + 1


def digital_root(value):
    return wrap9(value)


def raw_gua(year, convention):
    # Modern 1864-upper-yuan anchor; raw 5 must remain 5 until final mapping.
    elapsed = year - 1864
    return wrap9(1 - elapsed if convention == "male" else 5 + elapsed)


MASK_TO_STAR = {
    0: "伏位",
    1: "祸害",
    2: "绝命",
    3: "天医",
    4: "生气",
    5: "六煞",
    6: "五鬼",
    7: "延年",
}
GOOD = {"生气", "天医", "延年", "伏位"}
ORDER = ["乾", "坎", "艮", "震", "巽", "离", "坤", "兑"]
EAST = {"坎", "震", "巽", "离"}
BITS = {
    name: sum(bit << i for i, bit in enumerate(BAGUA_BY_NAME[name]["lines"]))
    for name in ORDER
}
TABLE = {
    base: {target: MASK_TO_STAR[BITS[base] ^ BITS[target]] for target in ORDER}
    for base in ORDER
}

# Literal pairs recorded in 八宅明镜卷下: 宅舍大门 / 各命之宅 / 各宅开门.
# A transcription mirror is a provisional oracle, not a checked critical edition.
SOURCE_PAIRS = {
    "乾": dict(
        zip(
            ["兑", "艮", "坤", "坎", "震", "巽", "离"],
            ["生气", "天医", "延年", "六煞", "五鬼", "祸害", "绝命"],
        )
    ),
    "坎": dict(
        zip(
            ["巽", "震", "离", "乾", "坤", "艮", "兑"],
            ["生气", "天医", "延年", "六煞", "绝命", "五鬼", "祸害"],
        )
    ),
    "艮": dict(
        zip(
            ["坤", "乾", "兑", "坎", "离", "震", "巽"],
            ["生气", "天医", "延年", "五鬼", "祸害", "六煞", "绝命"],
        )
    ),
    "兑": {"乾": "生气", "坤": "天医", "艮": "延年"},
    "离": {"震": "生气", "坎": "延年", "巽": "天医", "乾": "绝命"},
    "坤": {"艮": "生气", "乾": "延年", "兑": "天医", "坎": "绝命"},
}
for base, row in SOURCE_PAIRS.items():
    for target, expected in row.items():
        assert TABLE[base][target] == expected, (base, target, expected)
for base in ORDER:
    assert Counter(TABLE[base].values()) == Counter(MASK_TO_STAR.values())
    for target in ORDER:
        assert TABLE[base][target] == TABLE[target][base]
        assert (TABLE[base][target] in GOOD) == ((base in EAST) == (target in EAST))

# Original three-yuan starts: male 1/4/7, female raw 5/2/8.
YUAN_ANCHORS = {
    1864: {"male": 1, "female": 5},
    1924: {"male": 4, "female": 2},
    1984: {"male": 7, "female": 8},
    2044: {"male": 1, "female": 5},
}
for year, genders in YUAN_ANCHORS.items():
    for convention, expected in genders.items():
        assert raw_gua(year, convention) == expected
for year in range(1800, 2200):
    assert raw_gua(year, "male") == wrap9(11 - digital_root(year))
    assert raw_gua(year, "female") == wrap9(4 + digital_root(year))

FLIGHT = ["C", "NW", "W", "NE", "S", "N", "SW", "E", "SE"]
center_2026 = wrap9(1 - (2026 - 1864))
annual = {direction: wrap9(center_2026 + i) for i, direction in enumerate(FLIGHT)}
# Independently published chart: Joey Yap TG26 Booklet, printed p.67 / PDF p.66.
JOEY_2026 = {"SE": 9, "S": 5, "SW": 7, "E": 8, "C": 1, "W": 3, "NE": 4, "N": 6, "NW": 2}
assert annual == JOEY_2026

lichun = next(t for t in get_solar_terms_for_year(2026) if t.name == "立春")
boundary = {
    label: get_bazi_year(moment, "Asia/Shanghai")
    for label, moment in {
        "one_second_before": lichun.moment - timedelta(seconds=1),
        "at_boundary": lichun.moment,
        "one_second_after": lichun.moment + timedelta(seconds=1),
        "same_instant_utc": lichun.moment.astimezone(timezone.utc),
    }.items()
}
assert boundary == {
    "one_second_before": 2025,
    "at_boundary": 2026,
    "one_second_after": 2026,
    "same_instant_utc": 2026,
}

result = {
    "scope": "research_probe_not_production_engine",
    "source_spot_checks": {
        "bazhai_original_text_pairs": sum(len(row) for row in SOURCE_PAIRS.values()),
        "minggua_yuan_anchor_pairs": 8,
        "published_2026_palaces": 9,
        "all_passed": True,
        "limits": "Text mirror spot checks and one published annual chart; no independent full engine comparison.",
    },
    "internal_consistency": {
        "bazhai_pairs": 64,
        "distinct_stars_per_row": 8,
        "symmetric_and_east_west_partition": True,
        "minggua_years": [1800, 2199],
        "anchor_vs_full_year_formula_cases": 800,
        "limits": "Algebraic equivalence, not an independently published 400-year yearbook.",
    },
    "bazhai_table_order": ORDER,
    "bazhai_table": TABLE,
    "annual_2026": annual,
    "calendar_reuse_probe": {
        "local_lichun": lichun.moment.isoformat(),
        "year_boundary_results": boundary,
        "limits": "Existing runtime calculated this instant; HKO date was checked, not seconds-level accuracy.",
    },
    "current_catalog": {
        "records": len(CATALOG),
        "fengshui_tools": [
            spec.key
            for spec in CATALOG
            if spec.family == "fengshui" or "fengshui" in spec.key
        ],
    },
}
destination = Path(__file__).with_name("probe-results.json")
destination.write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "result_file": str(destination.resolve()),
            "spot_checks": result["source_spot_checks"],
            "calendar": result["calendar_reuse_probe"],
            "catalog": result["current_catalog"],
        },
        ensure_ascii=False,
        indent=2,
    )
)
