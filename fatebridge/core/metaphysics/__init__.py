"""
Offline Chinese metaphysics helpers for FateBridge.

These routines intentionally stay lightweight and deterministic so the
project can expose structured Zi Wei, Liu Ren, Qi Men, Tai Yi, and
Jin Kou outputs without depending on a separate runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...utils.data import EARTHLY_BRANCHES, HEAVENLY_STEMS
from .common import (
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    GUI_REN_REVERSED_STARTS,
    GUI_REN_SEQUENCE,
    KONGWANG_BY_XUN_HEAD,
    LIURENG_GUIREN_DAY,
    LIURENG_GUIREN_NIGHT,
    SEXAGENARY_CYCLE,
    SEXAGENARY_INDEX,
    SIX_CLASH_BRANCHES,
    SIX_HARM_BRANCHES,
    SIX_HARMONY_BRANCHES,
    XUN_HEADS,
    YUE_JIANG_NAMES,
    MetaphysicsSeed,
    branch_element_text,
    chinese_numeral,
    cyclic_get,
    element_relation,
    ganzhi_text,
    kongwang_for_ganzhi,
    liuqin_against_day,
    rotate_sequence,
    sexagenary_index_for,
    sexagenary_text,
    status_against_anchor,
    stem_element_text,
    xun_head_for_ganzhi,
)
from .liureng import build_liureng_board, build_liureng_runyear
from .qimen import (
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    build_qimen_board,
    qimen_futou_for_ganzhi,
)
from .ziwei import (
    ZIWEI_SIHUA_RULES,
    build_ziwei_chart,
    build_ziwei_horoscope,
    build_ziwei_rules,
)

GUI_REN_BRANCH_BY_NAME = {
    "贵人": "丑",
    "螣蛇": "巳",
    "朱雀": "午",
    "六合": "卯",
    "勾陈": "辰",
    "青龙": "寅",
    "天空": "戌",
    "白虎": "申",
    "太常": "未",
    "玄武": "子",
    "太阴": "酉",
    "天后": "亥",
}

# 大六壬 "日干寄宫" 表：十天干各自所寄的地支宫位。
# 四课中，一课/二课 以 "日干寄宫" 为下神起点；三课/四课 以 "日支" 为下神起点。

WUZI_DUN_START = {
    "甲": "甲",
    "己": "甲",
    "乙": "丙",
    "庚": "丙",
    "丙": "戊",
    "辛": "戊",
    "丁": "庚",
    "壬": "庚",
    "戊": "壬",
    "癸": "壬",
}

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

POWER_RANK = {"旺": 5, "相": 4, "休": 3, "囚": 2, "死": 1}
JINKOU_USE_POSITION_PREFERENCE = {
    "元首": "贵神",
    "遥克": "贵神",
    "官鬼": "贵神",
    "重审": "地分",
    "别责": "地分",
    "八专": "地分",
    "伏吟": "地分",
    "返吟": "地分",
    "六合": "将神",
    "昴星": "将神",
    "涉害": "将神",
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


def _build_guishen_mapping(
    day_stem: str, hour_branch: str
) -> Tuple[str, Dict[str, str]]:
    is_day = hour_branch in {"卯", "辰", "巳", "午", "未", "申"}
    start_branch = (
        LIURENG_GUIREN_DAY[day_stem] if is_day else LIURENG_GUIREN_NIGHT[day_stem]
    )
    reverse = start_branch in GUI_REN_REVERSED_STARTS
    branches = rotate_sequence(EARTHLY_BRANCHES, start_branch, reverse=reverse)
    return start_branch, {
        branches[index]: GUI_REN_SEQUENCE[index]
        for index in range(len(EARTHLY_BRANCHES))
    }


def _wuzidun_stem(day_stem: str, branch: str) -> str:
    start_stem = WUZI_DUN_START[day_stem]
    start_index = HEAVENLY_STEMS.index(start_stem)
    branch_index = EARTHLY_BRANCHES.index(branch)
    return HEAVENLY_STEMS[(start_index + branch_index) % len(HEAVENLY_STEMS)]


def _jinkou_pick_use_position(
    *,
    rows: List[Dict[str, Any]],
    board_style_detail: str,
    selected_lesson_relation: str,
) -> Tuple[str, str]:
    if not rows:
        return "人元", "四位未齐，暂以人元为用。"

    strongest_rank = max(POWER_RANK[row["power"]] for row in rows)
    strongest_rows = [row for row in rows if POWER_RANK[row["power"]] == strongest_rank]

    preferred_label = JINKOU_USE_POSITION_PREFERENCE.get(board_style_detail)
    if preferred_label and any(
        row["label"] == preferred_label for row in strongest_rows
    ):
        return (
            preferred_label,
            f"{board_style_detail}课并见同旺，以{preferred_label}为用。",
        )

    relation_preference = {
        "上克下": "贵神",
        "下贼上": "地分",
        "上生下": "将神",
        "下生上": "地分",
        "比和": "将神",
    }
    preferred_label = relation_preference.get(selected_lesson_relation)
    if preferred_label and any(
        row["label"] == preferred_label for row in strongest_rows
    ):
        return (
            preferred_label,
            f"发用见{selected_lesson_relation}，并旺时偏取{preferred_label}。",
        )

    return strongest_rows[0]["label"], "按四位旺衰取最旺者为用。"


def build_jinkou_board(
    seed: MetaphysicsSeed,
    liureng_board: Dict[str, Any],
    gender: str = "未知",
    di_fen: Optional[str] = None,
    runyear: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day_stem = seed.pillars["day"][0]
    hour_branch = seed.pillars["hour"][1]
    di_fen_branch = di_fen or hour_branch
    guiren_start, guishen_map = _build_guishen_mapping(day_stem, hour_branch)
    renyuan_stem = _wuzidun_stem(day_stem, di_fen_branch)
    twelve_board = {
        row["earth_branch"]: row
        for row in liureng_board.get("twelve_board", [])
        if isinstance(row, dict) and row.get("earth_branch")
    }
    jiangshen_branch = twelve_board.get(di_fen_branch, {}).get(
        "sky_branch", di_fen_branch
    )
    jiangshen_name = YUE_JIANG_NAMES.get(jiangshen_branch, "未知")
    guishen_branch = hour_branch
    guishen_name = (
        twelve_board.get(hour_branch, {}).get("god")
        or guishen_map.get(hour_branch)
        or "贵人"
    )
    anchor_element = branch_element_text(di_fen_branch)

    row_defs = [
        ("人元", renyuan_stem, stem_element_text(renyuan_stem), "—"),
        ("贵神", guishen_branch, branch_element_text(guishen_branch), guishen_name),
        (
            "将神",
            jiangshen_branch,
            branch_element_text(jiangshen_branch),
            jiangshen_name,
        ),
        ("地分", di_fen_branch, branch_element_text(di_fen_branch), "—"),
    ]

    rows = []
    for label, content, element, shenjiang in row_defs:
        power = status_against_anchor(anchor_element, element)
        rows.append(
            {
                "label": label,
                "content": content,
                "shenjiang": shenjiang,
                "element": element,
                "power": power,
            }
        )

    board_style_detail = liureng_board.get("board_style_detail", "")
    transmission_method = (liureng_board.get("three_transmissions", {}) or {}).get(
        "method", ""
    )
    selected_lesson_relation = (liureng_board.get("meta") or {}).get(
        "selected_lesson_relation"
    ) or ""
    use_position, use_position_basis = _jinkou_pick_use_position(
        rows=rows,
        board_style_detail=board_style_detail,
        selected_lesson_relation=selected_lesson_relation,
    )

    shensha = [
        {"label": "人元", "value": "纳音引气"},
        {"label": "贵神", "value": f"{guishen_name}守时"},
        {"label": "将神", "value": f"{jiangshen_name}临地分"},
        {"label": "地分", "value": f"{di_fen_branch}守位"},
    ]
    if board_style_detail:
        shensha.append({"label": "课体", "value": f"{board_style_detail}课"})
    if transmission_method:
        shensha.append({"label": "取传", "value": transmission_method})

    overview = {
        "di_fen": di_fen_branch,
        "kongwang": liureng_board["kongwang"],
        "si_da_kong": f"{branch_element_text(di_fen_branch)}空",
        "board_style": liureng_board.get("board_style", ""),
        "board_style_detail": board_style_detail,
        "transmission_method": transmission_method,
        "use_position": use_position,
        "use_position_basis": use_position_basis,
        "yuejiang": {
            "branch": jiangshen_branch,
            "name": jiangshen_name,
        },
        "guishen": {
            "start_branch": guiren_start,
            "branch": guishen_branch,
            "name": guishen_name,
        },
        "month_general": liureng_board.get("month_general"),
        "gender": gender,
    }
    if runyear:
        overview["runyear"] = runyear

    return {
        "overview": overview,
        "rows": rows,
        "shensha": shensha,
    }
