"""
Da Liu Ren (大六壬) board construction for the FateBridge metaphysics package.

Pure relocation from the package facade: the liu-ren-exclusive tables and
``_liureng_*`` helpers plus public ``build_liureng_board`` /
``build_liureng_runyear``. Shared 贵人/月将 tables and sexagenary/element
primitives are imported from ``.common``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...utils.data import EARTHLY_BRANCHES, HEAVENLY_STEMS
from ...utils.helpers import normalize_gender
from .common import (
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    GUI_REN_SEQUENCE,
    LIURENG_GUIREN_DAY,
    LIURENG_GUIREN_NIGHT,
    SIX_CLASH_BRANCHES,
    SIX_HARM_BRANCHES,
    SIX_HARMONY_BRANCHES,
    YUE_JIANG_NAMES,
    MetaphysicsSeed,
    branch_element_text,
    ganzhi_text,
    kongwang_for_ganzhi,
    liuqin_against_day,
    rotate_sequence,
    sexagenary_index_for,
    sexagenary_text,
    stem_element_text,
    xun_head_for_ganzhi,
)
from .liureng_transmissions import STEM_HOUSES as DAY_STEM_HOUSE
from .liureng_transmissions import select_transmissions

LIURENG_MONTH_GENERAL_BY_TERM = {
    "大寒": "子",
    "立春": "子",
    "雨水": "亥",
    "惊蛰": "亥",
    "春分": "戌",
    "清明": "戌",
    "谷雨": "酉",
    "立夏": "酉",
    "小满": "申",
    "芒种": "申",
    "夏至": "未",
    "小暑": "未",
    "大暑": "午",
    "立秋": "午",
    "处暑": "巳",
    "白露": "巳",
    "秋分": "辰",
    "寒露": "辰",
    "霜降": "卯",
    "立冬": "卯",
    "小雪": "寅",
    "大雪": "寅",
    "冬至": "丑",
    "小寒": "丑",
}


LIURENG_GUIREN_REVERSED_EARTH = frozenset("巳午未申酉戌")


def _liureng_month_general_for_term(current_term: str, fallback_branch: str) -> str:
    return LIURENG_MONTH_GENERAL_BY_TERM.get(current_term, fallback_branch)


def _liureng_month_general_on_hour(
    *,
    hour_branch: str,
    month_general_branch: str,
) -> Dict[str, str]:
    earth_order = rotate_sequence(EARTHLY_BRANCHES, hour_branch)
    sky_order = rotate_sequence(EARTHLY_BRANCHES, month_general_branch)
    return {
        earth_branch: sky_order[index] for index, earth_branch in enumerate(earth_order)
    }


def _branch_relation(
    left_branch: str,
    right_branch: str,
    *,
    same_label: str = "同支",
) -> str:
    if left_branch == right_branch:
        return same_label
    if SIX_HARMONY_BRANCHES.get(left_branch) == right_branch:
        return "六合"
    if SIX_CLASH_BRANCHES.get(left_branch) == right_branch:
        return "六冲"
    if SIX_HARM_BRANCHES.get(left_branch) == right_branch:
        return "六害"
    return "平"


def _liureng_judge_lesson(
    *,
    upper_branch: str,
    lower_branch: str,
    day_branch: str,
    relation: str,
) -> Tuple[str, str, str, str]:
    with_day = _branch_relation(upper_branch, day_branch, same_label="比和")
    with_lower = _branch_relation(upper_branch, lower_branch, same_label="伏吟")

    # 大六壬课体判断以"上下"关系为主：伏吟=上下同位，返吟=上下相冲，六合=上下合。
    # 上神与日支的关系只作辅参，不应单独触发 返吟/六合 类型，否则会把
    # "上下六合、上神冲日" 这种组合误判为返吟。
    if with_lower == "伏吟":
        return "伏吟", "上神与下神同位，伏吟取象。", with_day, with_lower
    if with_lower == "六冲":
        return "返吟", "上神与下神相冲，取返吟往复之象。", with_day, with_lower
    if with_lower == "六害":
        return "涉害", "上神与下神相害，课传重看牵连阻滞。", with_day, with_lower
    if relation == "官鬼":
        return "官鬼", "上神为官鬼，先取克身之应。", with_day, with_lower
    if with_lower == "六合":
        return "六合", "上神与下神相合，以和合成局为先。", with_day, with_lower
    return "比用", "同类比用，以首课取发用。", with_day, with_lower


def _liureng_upper_lower_relation(upper_branch: str, lower_branch: str) -> str:
    upper_element = branch_element_text(upper_branch)
    lower_element = (
        stem_element_text(lower_branch)
        if lower_branch in HEAVENLY_STEMS
        else branch_element_text(lower_branch)
    )
    if upper_element == lower_element:
        return "比和"
    if ELEMENT_CONTROLS[upper_element] == lower_element:
        return "上克下"
    if ELEMENT_CONTROLS[lower_element] == upper_element:
        return "下贼上"
    if ELEMENT_GENERATES[upper_element] == lower_element:
        return "上生下"
    if ELEMENT_GENERATES[lower_element] == upper_element:
        return "下生上"
    return "平"


def build_liureng_board(
    seed: MetaphysicsSeed,
    gender: str = "未知",
    month_general_override: Optional[str] = None,
    is_diurnal_override: Optional[bool] = None,
) -> Dict[str, Any]:
    lunar = seed.calendar_context.get("lunar_calendar") or {}
    current_term_name = seed.calendar_context["current_solar_term"]["name"]
    month_branch = seed.pillars["month"][1]
    day_stem = seed.pillars["day"][0]
    day_branch = seed.pillars["day"][1]
    hour_branch = seed.pillars["hour"][1]
    day_element = stem_element_text(day_stem)
    day_ganzhi = ganzhi_text(seed.pillars["day"])
    xun_head = xun_head_for_ganzhi(day_ganzhi)
    kongwang = kongwang_for_ganzhi(day_ganzhi)

    is_day = (
        is_diurnal_override
        if is_diurnal_override is not None
        else hour_branch in {"卯", "辰", "巳", "午", "未", "申"}
    )
    guiren_start = (
        LIURENG_GUIREN_DAY[day_stem] if is_day else LIURENG_GUIREN_NIGHT[day_stem]
    )
    if (
        month_general_override is not None
        and month_general_override not in YUE_JIANG_NAMES
    ):
        raise ValueError("month_general_override 必须是十二地支之一")
    yuejiang_branch = month_general_override or _liureng_month_general_for_term(
        current_term_name,
        month_branch,
    )
    yuejiang_name = YUE_JIANG_NAMES[yuejiang_branch]

    sky_to_earth = _liureng_month_general_on_hour(
        hour_branch=hour_branch,
        month_general_branch=yuejiang_branch,
    )

    guiren_earth = next(
        earth for earth, sky in sky_to_earth.items() if sky == guiren_start
    )
    guiren_reverse = guiren_earth in LIURENG_GUIREN_REVERSED_EARTH
    guiren_branches = rotate_sequence(
        EARTHLY_BRANCHES, guiren_start, reverse=guiren_reverse
    )
    guiren_map = {
        guiren_branches[index]: GUI_REN_SEQUENCE[index]
        for index in range(len(EARTHLY_BRANCHES))
    }

    # 大六壬 classical 四课 construction:
    # 一课 下=日干寄宫, 上=sky[日干寄宫]
    # 二课 下=一课上神, 上=sky[一课上神]
    # 三课 下=日支, 上=sky[日支]
    # 四课 下=三课上神, 上=sky[三课上神]
    day_stem_house = DAY_STEM_HOUSE[day_stem]
    lesson_1_lower = day_stem_house
    lesson_1_upper = sky_to_earth[lesson_1_lower]
    lesson_2_lower = lesson_1_upper
    lesson_2_upper = sky_to_earth[lesson_2_lower]
    lesson_3_lower = day_branch
    lesson_3_upper = sky_to_earth[lesson_3_lower]
    lesson_4_lower = lesson_3_upper
    lesson_4_upper = sky_to_earth[lesson_4_lower]
    lesson_specs = [
        # (lower, upper, anchor_branch)：一/二课 以日干寄宫为 anchor；三/四课 以日支为 anchor。
        (lesson_1_lower, lesson_1_upper, day_stem_house),
        (lesson_2_lower, lesson_2_upper, day_stem_house),
        (lesson_3_lower, lesson_3_upper, day_branch),
        (lesson_4_lower, lesson_4_upper, day_branch),
    ]
    four_lessons: List[Dict[str, Any]] = []
    for lesson_index, (lower_branch, upper_branch, anchor_branch) in enumerate(
        lesson_specs, start=1
    ):
        relation = liuqin_against_day(day_element, branch_element_text(upper_branch))
        style_hint, style_basis, with_day, with_lower = _liureng_judge_lesson(
            upper_branch=upper_branch,
            lower_branch=lower_branch,
            day_branch=anchor_branch,
            relation=relation,
        )
        four_lessons.append(
            {
                "index": lesson_index,
                "upper_branch": upper_branch,
                "lower_branch": lower_branch,
                "anchor_branch": anchor_branch,
                "text": f"{upper_branch}加{day_stem if lesson_index == 1 else lower_branch}",
                "relation": relation,
                "upper_lower_relation": _liureng_upper_lower_relation(
                    upper_branch,
                    day_stem if lesson_index == 1 else lower_branch,
                ),
                "relations": {
                    "with_day_branch": with_day,
                    "with_lower_branch": with_lower,
                },
                "style_hint": style_hint,
                "style_basis": style_basis,
                "use_candidate": False,
            }
        )

    (
        style,
        style_detail,
        transmission_method,
        transmission_branches,
        selected_lesson_index,
    ) = select_transmissions(day_stem, day_branch, sky_to_earth, four_lessons)
    initial_lesson = next(
        (l for l in four_lessons if l["index"] == selected_lesson_index), None
    )
    if initial_lesson is not None:
        initial_lesson["use_candidate"] = True
    style_basis = f"依九宗门取{style}，发用为{transmission_branches[0]}。"
    style_detail_basis = f"细课体{style_detail}，取传法为{transmission_method}。"

    initial_branch = transmission_branches[0]
    transmission_labels = ["initial", "middle", "final"]
    transmission_payload: Dict[str, Any] = {"method": transmission_method}
    for offset, label in enumerate(transmission_labels):
        branch = transmission_branches[offset]
        relation = liuqin_against_day(day_element, branch_element_text(branch))
        transmission_payload[label] = {
            "branch": branch,
            "relation": relation,
            "god": guiren_map[branch],
            "ganzhi": f"{branch}{sky_to_earth[branch]}",
        }

    overview = [
        f"月将{yuejiang_branch}({yuejiang_name})加{hour_branch}时，当前以{current_term_name}节气入局。",
        f"贵人起于{guiren_start}，{'逆' if guiren_reverse else '顺'}行布十二神将。",
        f"{style}课主导，首传落{initial_branch}，{style_basis}",
        f"细课体：{style_detail}。{style_detail_basis}",
        f"取传法：{transmission_method}。首传见{transmission_payload['initial']['relation']}，末传归{transmission_payload['final']['branch']}。",
    ]

    patterns = [
        {
            "name": f"贵人{'逆' if guiren_reverse else '顺'}行格",
            "basis": f"贵人起{guiren_start}，{'逆' if guiren_reverse else '顺'}布神将。",
        },
        {
            "name": f"{style}课",
            "basis": style_basis,
        },
    ]
    if style_detail != style:
        patterns.append(
            {
                "name": f"{style_detail}课",
                "basis": style_detail_basis,
            }
        )

    return {
        "month_general": {
            "branch": yuejiang_branch,
            "name": yuejiang_name,
        },
        "board_style": style,
        "board_style_detail": style_detail,
        "board_order": "天盘逆布" if guiren_reverse else "天盘顺布",
        "kongwang": kongwang,
        "xun_head": xun_head,
        "twelve_life_element": branch_element_text(month_branch),
        "guiren_system": "六壬法贵人",
        "four_lessons": four_lessons,
        "three_transmissions": transmission_payload,
        "patterns": patterns,
        "overview": overview,
        "twelve_board": [
            {
                "earth_branch": branch,
                "sky_branch": sky_to_earth[branch],
                "god": guiren_map[sky_to_earth[branch]],
            }
            for branch in EARTHLY_BRANCHES
        ],
        "meta": {
            "current_term": current_term_name,
            "lunar_display": lunar.get("display"),
            "questioner_gender": gender,
            "is_diurnal": is_day,
            "selected_lesson_index": (
                initial_lesson["index"] if initial_lesson else None
            ),
            "selected_lesson_relation": (
                initial_lesson.get("upper_lower_relation") if initial_lesson else None
            ),
            "guiren_earth_branch": guiren_earth,
        },
    }


def build_liureng_runyear(
    seed: MetaphysicsSeed, gender: str, birth_year: int
) -> Dict[str, Any]:
    age = max(1, seed.corrected_datetime.year - birth_year + 1)
    if normalize_gender(gender) == "女":
        start_index = sexagenary_index_for("己卯")
        direction = -1
    else:
        start_index = sexagenary_index_for("癸酉")
        direction = 1
    runyear_ganzhi = sexagenary_text(start_index + direction * (age - 1))
    return {
        "age": age,
        "ganzhi": runyear_ganzhi,
        "gender": gender,
    }
