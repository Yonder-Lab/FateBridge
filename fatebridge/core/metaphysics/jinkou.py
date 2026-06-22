"""
Jin Kou Jue (金口诀) board construction for the FateBridge metaphysics package.

Pure relocation from the package facade: 用神 preference tables, 贵神/五子遁
helpers, and the public ``build_jinkou_board``. Shared 贵人/月将 tables and
sexagenary/element primitives come from ``.common``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...utils.data import EARTHLY_BRANCHES, HEAVENLY_STEMS
from .common import (
    GUI_REN_REVERSED_STARTS,
    GUI_REN_SEQUENCE,
    LIURENG_GUIREN_DAY,
    LIURENG_GUIREN_NIGHT,
    YUE_JIANG_NAMES,
    MetaphysicsSeed,
    branch_element_text,
    rotate_sequence,
    status_against_anchor,
    stem_element_text,
)

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
