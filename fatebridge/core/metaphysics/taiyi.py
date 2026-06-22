"""
Tai Yi (太乙统宗) board construction for the FateBridge metaphysics package.

Pure relocation from the package facade: the 16-palace order, marker offsets,
and public ``build_taiyi_board``. Shared primitives come from ``.common``.
"""

from __future__ import annotations

from typing import Any, Dict, List

from ...utils.data import EARTHLY_BRANCHES
from .common import SIX_HARMONY_BRANCHES, MetaphysicsSeed, chinese_numeral

TAIYI_PALACE16_ORDER = [
    "巽",
    "巳",
    "午",
    "未",
    "坤",
    "申",
    "酉",
    "戌",
    "乾",
    "亥",
    "子",
    "丑",
    "艮",
    "寅",
    "卯",
    "辰",
]


TAIYI_MARKER_OFFSETS = {
    "君基": 0,
    "臣基": 1,
    "民基": 4,
    "文昌": 6,
    "始击": 9,
    "定目": 11,
    "主算": 13,
}


def build_taiyi_board(seed: MetaphysicsSeed, gender: str) -> Dict[str, Any]:
    lunar = seed.calendar_context.get("lunar_calendar") or {}
    lunar_month = int(lunar.get("month") or 1)
    lunar_day = int(lunar.get("day") or 1)
    year_branch = seed.pillars["year"][1]
    month_branch = seed.pillars["month"][1]
    day_branch = seed.pillars["day"][1]
    hour_branch = seed.pillars["hour"][1]
    palace_index = (
        EARTHLY_BRANCHES.index(year_branch)
        + EARTHLY_BRANCHES.index(month_branch)
        + EARTHLY_BRANCHES.index(day_branch)
        + EARTHLY_BRANCHES.index(hour_branch)
        + lunar_day
    ) % len(TAIYI_PALACE16_ORDER)
    taiyi_palace = TAIYI_PALACE16_ORDER[palace_index]
    wanchang_palace = TAIYI_PALACE16_ORDER[
        (palace_index + TAIYI_MARKER_OFFSETS["文昌"]) % len(TAIYI_PALACE16_ORDER)
    ]
    main_calculation_number = (
        (EARTHLY_BRANCHES.index(year_branch) + lunar_month + lunar_day - 1) % 72
    ) + 1
    main_calculation = (
        f"{'阳' if seed.pillars['year'][0] in '甲丙戊庚壬' else '阴'}遁"
        f"{chinese_numeral(main_calculation_number)}局"
    )

    marks: Dict[str, List[str]] = {palace: [] for palace in TAIYI_PALACE16_ORDER}
    for marker, offset in TAIYI_MARKER_OFFSETS.items():
        marks[
            TAIYI_PALACE16_ORDER[(palace_index + offset) % len(TAIYI_PALACE16_ORDER)]
        ].append(marker)
    marks[taiyi_palace].append("太乙")
    marks[wanchang_palace].append("文昌")

    return {
        "style_label": "太乙统宗",
        "accumulation_label": "太乙积年",
        "rotation": "顺布" if seed.pillars["year"][0] in "甲丙戊庚壬" else "逆布",
        "life_method": f"{gender}命",
        "taiyi_palace": taiyi_palace,
        "wenchang_palace": wanchang_palace,
        "core_board": {
            "main_calculation": main_calculation,
            "taiyi_position": f"太乙在{taiyi_palace}宫",
            "wenchang_position": f"文昌在{wanchang_palace}宫",
            "suijun": year_branch,
            "heshen": SIX_HARMONY_BRANCHES.get(year_branch, ""),
        },
        "palace_marks": [
            {
                "palace": palace,
                "markers": sorted(dict.fromkeys(marks[palace])),
            }
            for palace in TAIYI_PALACE16_ORDER
        ],
    }
