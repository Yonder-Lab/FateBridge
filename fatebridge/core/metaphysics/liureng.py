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
    GUI_REN_REVERSED_STARTS,
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


DAY_STEM_HOUSE = {
    "甲": "寅",
    "乙": "辰",
    "丙": "巳",
    "丁": "未",
    "戊": "巳",
    "己": "未",
    "庚": "申",
    "辛": "戌",
    "壬": "亥",
    "癸": "丑",
}


LIURENG_STYLE_PRIORITY = {
    "伏吟": 60,
    "返吟": 50,
    "涉害": 40,
    "官鬼": 30,
    "六合": 20,
    "比用": 10,
}


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


def _liureng_follow_sky(
    start_branch: str,
    sky_to_earth: Dict[str, str],
    steps: int,
) -> List[str]:
    path = [start_branch]
    current = start_branch
    for _ in range(steps):
        current = sky_to_earth.get(current, current)
        path.append(current)
    return path


def _liureng_build_transmissions(
    *,
    style: str,
    initial_lesson: Dict[str, Any],
    sky_to_earth: Dict[str, str],
    day_stem_house: Optional[str] = None,
    day_branch: Optional[str] = None,
    four_lessons: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, List[str]]:
    initial_branch = initial_lesson["upper_branch"]
    lower_branch = initial_lesson["lower_branch"]

    if style == "伏吟":
        # 伏吟守一：月将加占时同位，四课上下伏吟。发用已按阳/阴日选在干上/支上，
        # 取 初 = 课1/3 上神 (即 日干寄宫/日支)。中 = 初的自刑为支上神；末 = 中的刑。
        initial = initial_branch
        if day_stem_house is not None and day_branch is not None and four_lessons:
            # 阳日：初=日干寄宫, 中=日支, 末=中的刑；阴日反之
            if initial_lesson.get("anchor_branch") == day_stem_house:
                middle = day_branch
            else:
                middle = day_stem_house
        else:
            middle = initial
        final = _branch_self_punish(middle)
        return "伏吟守一", [initial, middle, final]
    if style == "返吟":
        # 返吟取冲：月将加占时相冲，四课上下皆冲。
        # 取 初 = 发用之上 (阳日干上/阴日支上)，中 = 初之冲，末 = 中的上神 (=sky[中])。
        middle = SIX_CLASH_BRANCHES.get(initial_branch, initial_branch)
        final = sky_to_earth.get(middle, middle)
        return "返吟取冲", [initial_branch, middle, final]
    if style == "六合":
        middle = SIX_HARMONY_BRANCHES.get(initial_branch, lower_branch)
        final = sky_to_earth.get(middle, middle)
        return "六合取合", [initial_branch, middle, final]
    if style == "涉害":
        middle = lower_branch
        final = sky_to_earth.get(middle, middle)
        return "涉害循下", [initial_branch, middle, final]
    if style == "官鬼":
        return "官鬼循盘", _liureng_follow_sky(initial_branch, sky_to_earth, 2)
    return "比用循盘", _liureng_follow_sky(initial_branch, sky_to_earth, 2)


_BRANCH_SELF_PUNISHMENT = {"辰", "午", "酉", "亥"}


_BRANCH_THREE_PUNISHMENTS = {
    "子": "卯",
    "卯": "子",
    "丑": "戌",
    "戌": "未",
    "未": "丑",
    "寅": "巳",
    "巳": "申",
    "申": "寅",
}


def _branch_self_punish(branch: str) -> str:
    if branch in _BRANCH_SELF_PUNISHMENT:
        return branch
    return _BRANCH_THREE_PUNISHMENTS.get(branch, branch)


def _liureng_upper_lower_relation(upper_branch: str, lower_branch: str) -> str:
    upper_element = branch_element_text(upper_branch)
    lower_element = branch_element_text(lower_branch)
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


def _liureng_refine_style_detail(
    *,
    style: str,
    selected_lesson: Dict[str, Any],
    four_lessons: List[Dict[str, Any]],
    day_stem_house: Optional[str] = None,
    day_branch: Optional[str] = None,
) -> Tuple[str, str]:
    upper_branches = [lesson["upper_branch"] for lesson in four_lessons]
    unique_upper = len(set(upper_branches))
    upper_lower_relation = selected_lesson.get("upper_lower_relation", "平")
    selected_index = int(selected_lesson.get("index") or 1)
    # 八专课：日干寄宫 == 日支（干支共位），四课自然只出现两套上下，课1/3 下神相同。
    bazhuan = (
        day_stem_house is not None
        and day_branch is not None
        and day_stem_house == day_branch
    )

    if style == "伏吟":
        return "伏吟", "上下同临，细课体仍从伏吟。"
    if style == "返吟":
        return "返吟", "冲返往复，细课体仍从返吟。"
    if bazhuan:
        return "八专", "日干寄宫与日支同位，四课两两重见，取偏专之象。"
    if selected_index != 1 and style == "官鬼":
        return "遥克", "发用不居首课，以远神克应论遥克。"
    if upper_lower_relation == "上克下":
        return "元首", "上神克下神，取元首先发之象。"
    if upper_lower_relation == "下贼上":
        return "重审", "下神贼上神，回身重审其因。"
    if upper_lower_relation == "下生上":
        return "别责", "四课之间无克贼可取，以下生上之义为发用，课体为别责。"
    if style == "涉害":
        return "涉害", "课中见害，细课体仍从涉害。"
    if unique_upper == 4 and style == "比用":
        return "昴星", "四课分张散列，取昴星之象。"
    if unique_upper == 3:
        return "别责", "四课上神不足四种，以偏专责一端观之。"
    return style, selected_lesson.get("style_basis", "依主课体取象。")


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
    guiren_reverse = guiren_start in GUI_REN_REVERSED_STARTS
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
                "text": f"{upper_branch}加{lower_branch}",
                "relation": relation,
                "upper_lower_relation": _liureng_upper_lower_relation(
                    upper_branch,
                    lower_branch,
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

    # Board-level 伏吟/返吟 detection (classical 大六壬):
    # 月将 加 占时 == 占时 (offset=0) → 四课上下同位 → 伏吟.
    # 月将 加 占时 == 占时的冲 (offset=6) → 四课上下皆冲 → 返吟.
    board_fuyin = yuejiang_branch == hour_branch
    board_fanyin = SIX_CLASH_BRANCHES.get(yuejiang_branch) == hour_branch

    style = "比用"
    style_basis = "同类比用，以首课取发用。"
    initial_lesson = four_lessons[0]
    day_stem_polarity_idx = HEAVENLY_STEMS.index(day_stem)
    yang_day = day_stem_polarity_idx % 2 == 0

    if board_fuyin:
        initial_lesson = four_lessons[0] if yang_day else four_lessons[2]
        style = "伏吟"
        style_basis = "月将加占时同位，四课上下伏吟，按阳日取干上、阴日取支上发用。"
    elif board_fanyin:
        initial_lesson = four_lessons[0] if yang_day else four_lessons[2]
        style = "返吟"
        style_basis = "月将加占时相冲，四课上下返吟，按阳日取干上、阴日取支上发用。"
    else:
        # 正统贼克发用：下贼上 优于 上克下。若多于一个，按 知一/涉害 规则选一。
        ke_lessons = [
            les for les in four_lessons if les.get("upper_lower_relation") == "上克下"
        ]
        zei_lessons = [
            les for les in four_lessons if les.get("upper_lower_relation") == "下贼上"
        ]

        def _pick_zhiyi(lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
            """知一法简化：阳日取 阳支 发用，阴日取 阴支 发用；若无匹配，取课号最小者。"""
            yang_branches = {"子", "寅", "辰", "午", "申", "戌"}
            preferred = [
                les
                for les in lessons
                if (les["upper_branch"] in yang_branches) == yang_day
            ]
            candidates = preferred or lessons
            return min(candidates, key=lambda les: les["index"])

        if zei_lessons:
            initial_lesson = (
                zei_lessons[0] if len(zei_lessons) == 1 else _pick_zhiyi(zei_lessons)
            )
            style = "重审"
            style_basis = "下神贼上神，以贼课取发用，课体为重审。"
        elif ke_lessons:
            initial_lesson = (
                ke_lessons[0] if len(ke_lessons) == 1 else _pick_zhiyi(ke_lessons)
            )
            style = "元首"
            style_basis = "上神克下神，以克课取发用，课体为元首。"
        else:
            # 无正克贼：看是否有 六合、遥克 或 比用 可推。
            liuhe_lessons = [
                les for les in four_lessons if les.get("style_hint") == "六合"
            ]
            yaoke_lessons = [
                les for les in four_lessons if les.get("style_hint") == "官鬼"
            ]
            if liuhe_lessons:
                initial_lesson = min(liuhe_lessons, key=lambda les: les["index"])
                style = "六合"
                style_basis = "上下相合，取合课发用。"
            elif yaoke_lessons:
                # 无正克贼，有 官鬼 (上神克日)：为遥克课。发用取 最后一个 克 lesson (index 4 优先)。
                initial_lesson = max(yaoke_lessons, key=lambda les: les["index"])
                style = "官鬼"
                style_basis = "四课无正克贼，上神克日干，远神克应论遥克。"
            else:
                # 默认：按 style priority 次序取。
                judged_lessons = sorted(
                    four_lessons,
                    key=lambda lesson: (
                        LIURENG_STYLE_PRIORITY.get(lesson["style_hint"], 0),
                        -lesson["index"],
                    ),
                    reverse=True,
                )
                initial_lesson = judged_lessons[0]
                style = initial_lesson["style_hint"]
                style_basis = initial_lesson["style_basis"]
    initial_lesson["use_candidate"] = True
    style_detail, style_detail_basis = _liureng_refine_style_detail(
        style=style,
        selected_lesson=initial_lesson,
        four_lessons=four_lessons,
        day_stem_house=day_stem_house,
        day_branch=day_branch,
    )

    transmission_method, transmission_branches = _liureng_build_transmissions(
        style=style,
        initial_lesson=initial_lesson,
        sky_to_earth=sky_to_earth,
        day_stem_house=day_stem_house,
        day_branch=day_branch,
        four_lessons=four_lessons,
    )
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
                "god": guiren_map[branch],
            }
            for branch in EARTHLY_BRANCHES
        ],
        "meta": {
            "current_term": current_term_name,
            "lunar_display": lunar.get("display"),
            "questioner_gender": gender,
            "is_diurnal": is_day,
            "selected_lesson_index": initial_lesson["index"],
            "selected_lesson_relation": initial_lesson.get("upper_lower_relation"),
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
