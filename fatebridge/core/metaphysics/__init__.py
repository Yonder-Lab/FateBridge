"""
Offline Chinese metaphysics helpers for FateBridge.

These routines intentionally stay lightweight and deterministic so the
project can expose structured Zi Wei, Liu Ren, Qi Men, Tai Yi, and
Jin Kou outputs without depending on a separate runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

from ...utils.data import (
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    ZIWEI_BRANCH_SEQUENCE,
    get_nayin,
)
from ...utils.helpers import normalize_gender
from ..almanac import (
    DAY_GANZHI_STRATEGY_STANDARD,
    get_jieqi_year_grid,
    localize_datetime,
)
from ..calendar import BaZiCalendar, resolve_bazi_effective_date
from ..divination import build_hexagram
from ..ziwei_tables import (
    lookup_star_brightness,
    split_star_mutagen,
)
from .common import (
    ELEMENT_CONTROLS,
    ELEMENT_GENERATES,
    KONGWANG_BY_XUN_HEAD,
    SEXAGENARY_CYCLE,
    SEXAGENARY_INDEX,
    SIX_CLASH_BRANCHES,
    SIX_HARM_BRANCHES,
    SIX_HARMONY_BRANCHES,
    XUN_HEADS,
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
from .qimen import (
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    build_qimen_board,
    qimen_futou_for_ganzhi,
)

# 五行局数字与标签 (紫微斗数): 水二局 / 木三局 / 金四局 / 土五局 / 火六局
_WUXING_JU_NUMBER_BY_ELEMENT: Dict[str, int] = {
    "水": 2,
    "木": 3,
    "金": 4,
    "土": 5,
    "火": 6,
}
_WUXING_JU_LABEL_BY_NUMBER: Dict[int, str] = {
    2: "水二局",
    3: "木三局",
    4: "金四局",
    5: "土五局",
    6: "火六局",
}


def _resolve_wuxing_ju(ming_stem: str, ming_branch: str) -> Dict[str, Any]:
    """由命宫干支的纳音推出五行局 (起大限岁数)。"""
    nayin = get_nayin(ming_stem, ming_branch)
    element = nayin[-1] if nayin and nayin != "未知纳音" else "木"
    if element not in _WUXING_JU_NUMBER_BY_ELEMENT:
        element = "木"  # 无法识别时退回 木三局 保守默认
    number = _WUXING_JU_NUMBER_BY_ELEMENT[element]
    return {
        "number": number,
        "element": element,
        "label": _WUXING_JU_LABEL_BY_NUMBER[number],
        "nayin": nayin,
    }


YUE_JIANG_NAMES = {
    "子": "神后",
    "丑": "大吉",
    "寅": "功曹",
    "卯": "太冲",
    "辰": "天罡",
    "巳": "太乙",
    "午": "胜光",
    "未": "小吉",
    "申": "传送",
    "酉": "从魁",
    "戌": "河魁",
    "亥": "登明",
}

# 六壬月将按中气为纲，节气期间沿用上一中气的月将。
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

LIURENG_GUIREN_DAY = {
    "甲": "丑",
    "乙": "子",
    "丙": "亥",
    "丁": "亥",
    "戊": "丑",
    "己": "子",
    "庚": "丑",
    "辛": "午",
    "壬": "巳",
    "癸": "巳",
}

LIURENG_GUIREN_NIGHT = {
    "甲": "未",
    "乙": "申",
    "丙": "酉",
    "丁": "酉",
    "戊": "未",
    "己": "申",
    "庚": "未",
    "辛": "寅",
    "壬": "卯",
    "癸": "卯",
}

GUI_REN_REVERSED_STARTS = {"巳", "午", "未", "申", "酉"}
GUI_REN_SEQUENCE = [
    "贵人",
    "螣蛇",
    "朱雀",
    "六合",
    "勾陈",
    "青龙",
    "天空",
    "白虎",
    "太常",
    "玄武",
    "太阴",
    "天后",
]
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

# 紫微十二宫顺序：命宫定位后，沿地支递增方向（子→丑→寅→...→亥）依次为
# 命、父母、福德、田宅、官禄、仆役、迁移、疾厄、财帛、子女、夫妻、兄弟。
# 这一排列等价于「从命宫逆时针起兄弟、夫妻...父母」的传统顺序
# （iztro / 紫微斗数全书一致做法）。
ZIWEI_PALACE_SEQUENCE = [
    "命宫",
    "父母宫",
    "福德宫",
    "田宅宫",
    "官禄宫",
    "仆役宫",
    "迁移宫",
    "疾厄宫",
    "财帛宫",
    "子女宫",
    "夫妻宫",
    "兄弟宫",
]

ZIWEI_SIHUA_RULES = {
    "甲": {"化禄": "廉贞", "化权": "破军", "化科": "武曲", "化忌": "太阳"},
    "乙": {"化禄": "天机", "化权": "天梁", "化科": "紫微", "化忌": "太阴"},
    "丙": {"化禄": "天同", "化权": "天机", "化科": "文昌", "化忌": "廉贞"},
    "丁": {"化禄": "太阴", "化权": "天同", "化科": "天机", "化忌": "巨门"},
    "戊": {"化禄": "贪狼", "化权": "太阴", "化科": "右弼", "化忌": "天机"},
    "己": {"化禄": "武曲", "化权": "贪狼", "化科": "天梁", "化忌": "文曲"},
    "庚": {"化禄": "太阳", "化权": "武曲", "化科": "太阴", "化忌": "天同"},
    "辛": {"化禄": "巨门", "化权": "太阳", "化科": "文曲", "化忌": "文昌"},
    "壬": {"化禄": "天梁", "化权": "紫微", "化科": "左辅", "化忌": "武曲"},
    "癸": {"化禄": "破军", "化权": "巨门", "化科": "太阴", "化忌": "贪狼"},
}

ZIWEI_STAR_OFFSETS = {
    "紫微": 0,
    "天机": 1,
    "太阳": 3,
    "武曲": 4,
    "天同": 5,
    "廉贞": 8,
    "天府": 6,
    "太阴": 7,
    "贪狼": 9,
    "巨门": 10,
    "天相": 11,
    "天梁": 2,
    "七杀": 4,
    "破军": 6,
}


# 按传统时家奇门常用节气定局表，局数随上中下元变化。

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
LIURENG_STYLE_PRIORITY = {
    "伏吟": 60,
    "返吟": 50,
    "涉害": 40,
    "官鬼": 30,
    "六合": 20,
    "比用": 10,
}
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
SIHUA_DISPLAY_ORDER = {
    "化忌": 0,
    "化权": 1,
    "化科": 2,
    "化禄": 3,
}


class OrderedSihuaKey(str):
    """String subclass that keeps Zi Wei sihua labels in traditional order."""

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, str):
            return NotImplemented
        return (
            SIHUA_DISPLAY_ORDER.get(str(self), 99),
            str(self),
        ) < (
            SIHUA_DISPLAY_ORDER.get(str(other), 99),
            str(other),
        )


def ordered_sihua_mapping(mapping: Dict[str, str]) -> Dict[OrderedSihuaKey, str]:
    return {OrderedSihuaKey(label): star for label, star in mapping.items()}


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


# 自刑地支对：大六壬 三刑 中的"自刑"四位：辰午酉亥。
_BRANCH_SELF_PUNISHMENT = {"辰", "午", "酉", "亥"}
# 非自刑地支的 刑 对（用于伏吟末传推演）。
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


def _branch_from_hour(hour_branch: str) -> int:
    return EARTHLY_BRANCHES.index(hour_branch) + 1


def _apply_sihua_to_palaces(
    palaces: List[Dict[str, Any]],
    year_stem: str,
) -> Dict[str, str]:
    sihua = ZIWEI_SIHUA_RULES[year_stem]
    transformed = {}
    for change_name, star_name in sihua.items():
        for palace in palaces:
            if star_name in palace["stars"]:
                palace["stars"] = [
                    f"{star}{change_name}" if star == star_name else star
                    for star in palace["stars"]
                ]
                transformed[change_name] = f"{star_name}入{palace['name']}"
                break
        else:
            transformed[change_name] = star_name
    # ordered_sihua_mapping keeps OrderedSihuaKey (a str subclass) keys for their
    # custom ordering; at runtime they are plain str keys, satisfying Dict[str, str].
    return cast(Dict[str, str], ordered_sihua_mapping(sihua))


def build_ziwei_chart(seed: MetaphysicsSeed, gender: str) -> Dict[str, Any]:
    lunar = seed.calendar_context.get("lunar_calendar") or {}
    lunar_month = int(lunar.get("month") or 1)
    lunar_day = int(lunar.get("day") or 1)

    # 紫微斗数闰月处理：以十五日为界，十五日及以前作当月算，十六日及以后作下月算
    if lunar.get("is_leap_month"):
        if lunar_day >= 16:
            lunar_month = (lunar_month % 12) + 1
    hour_branch = seed.pillars["hour"][1]
    hour_index = _branch_from_hour(hour_branch)
    year_stem = seed.pillars["year"][0]

    ming_index = (lunar_month - hour_index) % 12
    shen_index = (lunar_month + hour_index - 2) % 12
    ming_branch = ZIWEI_BRANCH_SEQUENCE[ming_index]
    shen_branch = ZIWEI_BRANCH_SEQUENCE[shen_index]

    # 宫干按「五虎遁」规则从年干推出：
    #   甲己之年 → 寅宫起丙寅，乙庚 → 戊寅，丙辛 → 庚寅，丁壬 → 壬寅，戊癸 → 甲寅。
    # ZIWEI_BRANCH_SEQUENCE 以 寅=0 为起点顺数到丑=11，因此某宫位在序列中的位置
    # 就是它相对于寅的偏移量，可直接叠加到寅宫干基。
    year_stem_index = HEAVENLY_STEMS.index(year_stem)
    yin_stem_base = (year_stem_index * 2 + 2) % len(HEAVENLY_STEMS)
    palace_stems = [
        HEAVENLY_STEMS[
            (yin_stem_base + (ming_index + offset) % 12) % len(HEAVENLY_STEMS)
        ]
        for offset in range(12)
    ]
    palace_branches = (
        ZIWEI_BRANCH_SEQUENCE[ming_index:] + ZIWEI_BRANCH_SEQUENCE[:ming_index]
    )
    palace_names = ZIWEI_PALACE_SEQUENCE[:]
    # 五行局 (起大限岁数) — 由命宫 (palaces[0]) 干支的纳音决定
    # Note: palace_stems[0] and palace_branches[0] are Ming Gong stems/branches
    wuxing_ju = _resolve_wuxing_ju(palace_stems[0], palace_branches[0])
    start_age = wuxing_ju["number"]

    # 大限方向: 阳男阴女顺行 / 阴男阳女逆行
    is_yang_year = HEAVENLY_STEMS.index(year_stem) % 2 == 0
    canonical_gender = normalize_gender(gender)
    daxian_forward = (canonical_gender == "男" and is_yang_year) or (
        canonical_gender == "女" and not is_yang_year
    )

    daxian_direction_label = "顺行" if daxian_forward else "逆行"

    # --- Standard Zi Wei Star Placement ---
    # 1. Resolve Zi Wei star position based on Wu Xing Ju and Lunar Day
    ju_num = wuxing_ju["number"]
    # Formula: find X such that ju_num * X >= lunar_day, Y = ju_num * X - lunar_day
    x = (lunar_day + ju_num - 1) // ju_num
    y = ju_num * x - lunar_day
    if y % 2 == 0:
        ziwei_index = (x + y - 1) % 12  # Relative to 寅 (0)
    else:
        ziwei_index = (x - y - 1) % 12

    # 2. Derive Tian Fu star position (mirrored from Zi Wei)
    tianfu_index = (12 - ziwei_index) % 12

    # 3. Place stars
    # Zi Wei group (Counter-clockwise relative to Zi Wei)
    ziwei_group = {
        "紫微": 0,
        "天机": -1,
        "太阳": -3,
        "武曲": -4,
        "天同": -5,
        "廉贞": -8,
    }
    # Tian Fu group (Clockwise relative to Tian Fu)
    tianfu_group = {
        "天府": 0,
        "太阴": 1,
        "贪狼": 2,
        "巨门": 3,
        "天相": 4,
        "天梁": 5,
        "七杀": 6,
        "破军": 10,
    }

    palaces: List[Dict[str, Any]] = []
    for index, palace_name in enumerate(palace_names):
        # 命宫永远是第一个大限，其余按顺/逆方向沿宫位排列；
        # 宫名序列已按地支递增方向排布（命→父母→福德→...→兄弟）。
        if daxian_forward:
            period_index = index  # 阳男/阴女：命→父母→福德→...
        else:
            period_index = (-index) % 12  # 阴男/阳女：命→兄弟→夫妻→...
        period_start = start_age + period_index * 10
        palace: Dict[str, Any] = {
            "name": palace_name,
            "ganzhi": f"{palace_stems[index]}{palace_branches[index]}",
            "daxian": f"{period_start}~{period_start + 9}",
            "daxian_period": period_index + 1,
            "stars": [],
        }
        palaces.append(palace)

    # Place Zi Wei group
    for star, offset in ziwei_group.items():
        idx = (ziwei_index + offset) % 12
        # Current palaces list is ordered by ZIWEI_PALACE_SEQUENCE starting from Ming Gong
        # But we need to find the palace that matches the earthly branch index (idx)
        for p in palaces:
            if p["ganzhi"][1] == ZIWEI_BRANCH_SEQUENCE[idx]:
                p["stars"].append(star)
                break

    # Place Tian Fu group
    for star, offset in tianfu_group.items():
        idx = (tianfu_index + offset) % 12
        for p in palaces:
            if p["ganzhi"][1] == ZIWEI_BRANCH_SEQUENCE[idx]:
                p["stars"].append(star)
                break

    # 4. Place Auxiliary Stars (Fixed Rules)
    # ZIWEI_BRANCH_SEQUENCE indexing: 寅(0), 卯(1), 辰(2), 巳(3), 午(4), 未(5),
    # 申(6), 酉(7), 戌(8), 亥(9), 子(10), 丑(11)。
    # 月系（生月起）：左辅从辰顺、右弼从戌逆。
    # 时系（生时起）：文昌从戌逆、文曲从辰顺。
    aux_locators = {
        "左辅": (2 + lunar_month - 1) % 12,
        "右弼": (8 - (lunar_month - 1)) % 12,
        "文昌": (8 - (hour_index - 1)) % 12,
        "文曲": (2 + (hour_index - 1)) % 12,
    }

    for star, idx in aux_locators.items():
        for p in palaces:
            if p["ganzhi"][1] == ZIWEI_BRANCH_SEQUENCE[idx]:
                p["stars"].append(star)
                break

    # --- 年干 / 年支 / 生时 派生的辅煞星 ---
    year_branch = seed.pillars["year"][1]
    year_branch_earth_index = EARTHLY_BRANCHES.index(year_branch)
    hour_earth_index = EARTHLY_BRANCHES.index(hour_branch)

    lucun_by_year_stem = {
        "甲": "寅",
        "乙": "卯",
        "丙": "巳",
        "丁": "午",
        "戊": "巳",
        "己": "午",
        "庚": "申",
        "辛": "酉",
        "壬": "亥",
        "癸": "子",
    }
    tiankui_by_year_stem = {
        "甲": "丑",
        "戊": "丑",
        "庚": "丑",
        "乙": "子",
        "己": "子",
        "丙": "亥",
        "丁": "亥",
        "辛": "午",
        "壬": "卯",
        "癸": "卯",
    }
    tianyue_by_year_stem = {
        "甲": "未",
        "戊": "未",
        "庚": "未",
        "乙": "申",
        "己": "申",
        "丙": "酉",
        "丁": "酉",
        "辛": "寅",
        "壬": "巳",
        "癸": "巳",
    }
    # 年支三合局定马 / 火铃起点
    tianma_by_year_branch = {
        "寅": "申",
        "午": "申",
        "戌": "申",
        "申": "寅",
        "子": "寅",
        "辰": "寅",
        "巳": "亥",
        "酉": "亥",
        "丑": "亥",
        "亥": "巳",
        "卯": "巳",
        "未": "巳",
    }
    huoxing_start_by_year_branch = {
        "寅": "丑",
        "午": "丑",
        "戌": "丑",
        "申": "寅",
        "子": "寅",
        "辰": "寅",
        "巳": "卯",
        "酉": "卯",
        "丑": "卯",
        "亥": "酉",
        "卯": "酉",
        "未": "酉",
    }
    lingxing_start_by_year_branch = {
        "寅": "卯",
        "午": "卯",
        "戌": "卯",
        "申": "戌",
        "子": "戌",
        "辰": "戌",
        "巳": "戌",
        "酉": "戌",
        "丑": "戌",
        "亥": "戌",
        "卯": "戌",
        "未": "戌",
    }

    def _branch_by_offset(start_branch: str, offset: int) -> str:
        return EARTHLY_BRANCHES[(EARTHLY_BRANCHES.index(start_branch) + offset) % 12]

    lucun_branch = lucun_by_year_stem[year_stem]
    minor_star_branches: Dict[str, str] = {
        "禄存": lucun_branch,
        "擎羊": _branch_by_offset(lucun_branch, 1),  # 禄存前一位
        "陀罗": _branch_by_offset(lucun_branch, -1),  # 禄存后一位
        "天魁": tiankui_by_year_stem[year_stem],
        "天钺": tianyue_by_year_stem[year_stem],
        "天马": tianma_by_year_branch[year_branch],
        "火星": _branch_by_offset(
            huoxing_start_by_year_branch[year_branch], hour_earth_index
        ),
        "铃星": _branch_by_offset(
            lingxing_start_by_year_branch[year_branch], hour_earth_index
        ),
        # 地空 / 地劫：生时起亥逆 / 顺
        "地空": EARTHLY_BRANCHES[(11 - hour_earth_index) % 12],
        "地劫": EARTHLY_BRANCHES[(11 + hour_earth_index) % 12],
        # 红鸾 / 天喜：年支起卯逆 / 对冲
        "红鸾": EARTHLY_BRANCHES[(3 - year_branch_earth_index) % 12],
        "天喜": EARTHLY_BRANCHES[(9 - year_branch_earth_index) % 12],
    }
    for star, target_branch in minor_star_branches.items():
        for p in palaces:
            if p["ganzhi"][1] == target_branch:
                p["stars"].append(star)
                break

    # --- 杂星 (adjective stars) ---
    # 年支三合派
    huagai_by_triad = {
        "寅": "戌",
        "午": "戌",
        "戌": "戌",
        "申": "辰",
        "子": "辰",
        "辰": "辰",
        "巳": "丑",
        "酉": "丑",
        "丑": "丑",
        "亥": "未",
        "卯": "未",
        "未": "未",
    }
    xianchi_by_triad = {
        "寅": "卯",
        "午": "卯",
        "戌": "卯",
        "申": "酉",
        "子": "酉",
        "辰": "酉",
        "巳": "午",
        "酉": "午",
        "丑": "午",
        "亥": "子",
        "卯": "子",
        "未": "子",
    }
    # 孤辰/寡宿 按年支"方局"
    guchen_gushu_table = {
        frozenset({"寅", "卯", "辰"}): ("巳", "丑"),
        frozenset({"巳", "午", "未"}): ("申", "辰"),
        frozenset({"申", "酉", "戌"}): ("亥", "未"),
        frozenset({"亥", "子", "丑"}): ("寅", "戌"),
    }
    guchen_branch = None
    guashu_branch = None
    for members, (gu, gua) in guchen_gushu_table.items():
        if year_branch in members:
            guchen_branch, guashu_branch = gu, gua
            break

    # 破碎 按年支
    posui_by_year_branch = {
        "子": "巳",
        "午": "巳",
        "卯": "巳",
        "酉": "巳",
        "寅": "酉",
        "申": "酉",
        "巳": "酉",
        "亥": "酉",
        "辰": "丑",
        "戌": "丑",
        "丑": "丑",
        "未": "丑",
    }
    # 蜚廉 按年支（固定表）
    feilian_by_year_branch = {
        "子": "申",
        "丑": "酉",
        "寅": "戌",
        "卯": "巳",
        "辰": "午",
        "巳": "未",
        "午": "寅",
        "未": "卯",
        "申": "辰",
        "酉": "亥",
        "戌": "子",
        "亥": "丑",
    }

    # 年干系 查表
    tianguan_by_year_stem = {
        "甲": "未",
        "乙": "辰",
        "丙": "巳",
        "丁": "寅",
        "戊": "卯",
        "己": "酉",
        "庚": "亥",
        "辛": "酉",
        "壬": "戌",
        "癸": "午",
    }
    tianfu_by_year_stem = {
        "甲": "酉",
        "乙": "申",
        "丙": "子",
        "丁": "亥",
        "戊": "卯",
        "己": "寅",
        "庚": "午",
        "辛": "巳",
        "壬": "午",
        "癸": "巳",
    }
    tianchu_by_year_stem = {
        "甲": "巳",
        "乙": "午",
        "丙": "子",
        "丁": "巳",
        "戊": "午",
        "己": "申",
        "庚": "寅",
        "辛": "午",
        "壬": "酉",
        "癸": "亥",
    }

    # 月系（按生月, 1-12）: 天月 / 天刑 / 天姚 / 天巫 / 解神 / 阴煞
    tianyue_month_table = [
        "戌",
        "巳",
        "辰",
        "寅",
        "未",
        "卯",
        "亥",
        "未",
        "寅",
        "午",
        "戌",
        "寅",
    ]
    tianxing_start_idx = 9  # 酉起正月顺
    tianyao_start_idx = 1  # 丑起正月顺
    tianwu_cycle = ["巳", "申", "寅", "亥"]  # 4-day cycle
    jieshen_pair_table = [
        "申",
        "申",
        "戌",
        "戌",
        "子",
        "子",
        "寅",
        "寅",
        "辰",
        "辰",
        "午",
        "午",
    ]
    yinsha_six_cycle = ["寅", "子", "戌", "申", "午", "辰"]

    # 时系: 封诰 / 台辅
    fenggao_start_idx = 2  # 寅起子时顺
    taifu_start_idx = 6  # 午起子时顺

    # 命宫/身宫 + 年支: 天才 / 天寿
    ming_branch_idx = EARTHLY_BRANCHES.index(ming_branch)
    shen_branch_idx = EARTHLY_BRANCHES.index(shen_branch)

    # 文昌/文曲地支位置（复用前面 aux_locators 公式，转成地支索引）
    wenchang_earth_idx = (10 - hour_earth_index) % 12
    wenqu_earth_idx = (4 + hour_earth_index) % 12
    # 左辅/右弼地支位置（月系）
    zuofu_earth_idx = (4 + lunar_month - 1) % 12  # 辰(4)起正月顺
    youbi_earth_idx = (10 - (lunar_month - 1)) % 12  # 戌(10)起正月逆

    # 旬空: 年支所在旬空亡，阳干取阳支、阴干取阴支
    #   甲子旬 → 戌亥, 甲戌旬 → 申酉, 甲申旬 → 午未,
    #   甲午旬 → 辰巳, 甲辰旬 → 寅卯, 甲寅旬 → 子丑。
    #   第一支为阳(戌/申/午/辰/寅/子)，第二支为阴(亥/酉/未/巳/卯/丑)。
    year_pillar_text = f"{year_stem}{year_branch}"
    year_cycle_index = sexagenary_index_for(year_pillar_text)
    xunkong_pairs = [
        ("戌", "亥"),
        ("申", "酉"),
        ("午", "未"),
        ("辰", "巳"),
        ("寅", "卯"),
        ("子", "丑"),
    ]
    xun_group = year_cycle_index // 10  # 0..5
    xunkong_yang, xunkong_yin = xunkong_pairs[xun_group]
    is_yang_stem = HEAVENLY_STEMS.index(year_stem) % 2 == 0
    xunkong_branch = xunkong_yang if is_yang_stem else xunkong_yin

    adjective_star_branches: Dict[str, str] = {
        # 命身派
        "天伤": EARTHLY_BRANCHES[(ming_branch_idx + 5) % 12],
        "天使": EARTHLY_BRANCHES[(ming_branch_idx + 7) % 12],
        "天才": EARTHLY_BRANCHES[(ming_branch_idx + year_branch_earth_index) % 12],
        "天寿": EARTHLY_BRANCHES[(shen_branch_idx + year_branch_earth_index) % 12],
        # 年支三合派
        "华盖": huagai_by_triad[year_branch],
        "咸池": xianchi_by_triad[year_branch],
        "孤辰": guchen_branch or year_branch,
        "寡宿": guashu_branch or year_branch,
        "破碎": posui_by_year_branch[year_branch],
        "蜚廉": feilian_by_year_branch[year_branch],
        # 年支派
        "龙池": EARTHLY_BRANCHES[(4 + year_branch_earth_index) % 12],
        "凤阁": EARTHLY_BRANCHES[(10 - year_branch_earth_index) % 12],
        "年解": EARTHLY_BRANCHES[(10 - year_branch_earth_index) % 12],  # 与凤阁同位
        "天哭": EARTHLY_BRANCHES[(6 - year_branch_earth_index) % 12],
        "天虚": EARTHLY_BRANCHES[(6 + year_branch_earth_index) % 12],
        "天德": EARTHLY_BRANCHES[(9 + year_branch_earth_index) % 12],
        "月德": EARTHLY_BRANCHES[(5 + year_branch_earth_index) % 12],
        # 年干查表派
        "天官": tianguan_by_year_stem[year_stem],
        "天福": tianfu_by_year_stem[year_stem],
        "天厨": tianchu_by_year_stem[year_stem],
        # 月系
        "天月": tianyue_month_table[(lunar_month - 1) % 12],
        "天刑": EARTHLY_BRANCHES[(tianxing_start_idx + lunar_month - 1) % 12],
        "天姚": EARTHLY_BRANCHES[(tianyao_start_idx + lunar_month - 1) % 12],
        "天巫": tianwu_cycle[(lunar_month - 1) % 4],
        "解神": jieshen_pair_table[(lunar_month - 1) % 12],
        "阴煞": yinsha_six_cycle[(lunar_month - 1) % 6],
        # 时系
        "封诰": EARTHLY_BRANCHES[(fenggao_start_idx + hour_earth_index) % 12],
        "台辅": EARTHLY_BRANCHES[(taifu_start_idx + hour_earth_index) % 12],
        # 月日复合派 (三台/八座 沿左辅/右弼; 恩光/天贵 沿文昌/文曲)
        "三台": EARTHLY_BRANCHES[(zuofu_earth_idx + lunar_day - 1) % 12],
        "八座": EARTHLY_BRANCHES[(youbi_earth_idx - (lunar_day - 1)) % 12],
        "恩光": EARTHLY_BRANCHES[(wenchang_earth_idx + lunar_day - 2) % 12],
        "天贵": EARTHLY_BRANCHES[(wenqu_earth_idx + lunar_day - 2) % 12],
        # 旬空
        "旬空": xunkong_branch,
    }
    for star, target_branch in adjective_star_branches.items():
        for p in palaces:
            if p["ganzhi"][1] == target_branch:
                p["stars"].append(star)
                break

    sihua = _apply_sihua_to_palaces(palaces, year_stem)
    for palace in palaces:
        palace["stars"] = sorted(dict.fromkeys(palace["stars"]))

    # --- Tier 1: attach brightness + parsed mutagen as an additive field ---
    # `palace["stars"]` (legacy) stays a list[str] of mutagen-suffixed labels;
    # `stars_detail` mirrors it 1:1 with structured data.
    for palace in palaces:
        palace_branch = palace["ganzhi"][1]
        detail: List[Dict[str, Any]] = []
        for label in palace["stars"]:
            base_name, mutagen = split_star_mutagen(label)
            detail.append(
                {
                    "name": base_name,
                    "label": label,
                    "brightness": lookup_star_brightness(base_name, palace_branch),
                    "mutagen": mutagen,
                }
            )
        palace["stars_detail"] = detail

    ming_palace = next(palace for palace in palaces if palace["name"] == "命宫")
    shen_palace = next(
        (palace for palace in palaces if palace["ganzhi"][1] == shen_branch),
        ming_palace,
    )
    return {
        "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
        "year_stem": year_stem,
        "ming_gong": {
            "name": "命宫",
            "branch": ming_branch,
            "ganzhi": ming_palace["ganzhi"],
        },
        "shen_gong": {
            "name": "身宫",
            "branch": shen_branch,
            "ganzhi": shen_palace["ganzhi"],
        },
        "wuxing_ju": wuxing_ju,
        "daxian_direction": daxian_direction_label,
        "sihua": sihua,
        "palaces": palaces,
    }


# 小限起始宫地支：按命盘生年地支三合局定 (iztro getAgeIndex 同义)
_XIAOXIAN_START_BY_YEAR_BRANCH = {
    "寅": "辰",
    "午": "辰",
    "戌": "辰",
    "申": "戌",
    "子": "戌",
    "辰": "戌",
    "巳": "未",
    "酉": "未",
    "丑": "未",
    "亥": "丑",
    "卯": "丑",
    "未": "丑",
}


def _palace_by_branch(palaces: List[Dict[str, Any]], branch: str) -> Dict[str, Any]:
    palace = next((p for p in palaces if p["ganzhi"][1] == branch), None)
    if palace is None:
        raise ValueError(f"未找到地支为 {branch!r} 的宫位")
    return palace


def _palace_for_nominal_age(
    palaces: List[Dict[str, Any]], nominal_age: int
) -> Dict[str, Any]:
    for palace in palaces:
        lo, hi = (int(x) for x in palace["daxian"].split("~"))
        if lo <= nominal_age <= hi:
            return palace
    # 超出已排大限范围时，回退到最末大限宫（仅极端高龄出现）
    return max(palaces, key=lambda p: int(p["daxian"].split("~")[1]))


def _xiaoxian_branch(year_branch: str, nominal_age: int, gender: str) -> str:
    start = _XIAOXIAN_START_BY_YEAR_BRANCH[year_branch]
    start_idx = ZIWEI_BRANCH_SEQUENCE.index(start)
    offset = (nominal_age - 1) % 12
    forward = normalize_gender(gender) == "男"
    idx = (start_idx + offset) % 12 if forward else (start_idx - offset) % 12
    return ZIWEI_BRANCH_SEQUENCE[idx]


def _horoscope_scope(scope: str, palace: Dict[str, Any], stem: str) -> Dict[str, Any]:
    branch = palace["ganzhi"][1]
    return {
        "scope": scope,
        "palace_name": palace["name"],
        "branch": branch,
        "branch_index": ZIWEI_BRANCH_SEQUENCE.index(branch),
        "stem": stem,
        "mutagen": dict(ZIWEI_SIHUA_RULES[stem]),
    }


def _bazi_year_for(target_year: int, target_year_branch: str) -> int:
    """Return the BaZi (节气) year for a calendar date.

    A date before 立春 carries the previous solar year's 年柱, so the BaZi year
    is target_year - 1 in that case. Detected by comparing the actual 年柱 branch
    to the branch expected for target_year.
    """
    expected_idx = (target_year - 4) % 12
    if EARTHLY_BRANCHES.index(target_year_branch) == expected_idx:
        return target_year
    return target_year - 1


def build_ziwei_horoscope(
    *,
    chart: Dict[str, Any],
    gender: str,
    natal_year_branch: str,
    target_pillars: Dict[str, Any],
    birth_year: int,
    target_year: int,
) -> Dict[str, Any]:
    """Assemble the six 运限 scopes for a target date over a natal chart.

    大限 selects among the chart's own (Tier-1) 大限 ranges by 虚岁; 流年/流月/流日/
    流时 land on the palace carrying that pillar's branch with 四化 from the
    pillar stem; 小限 uses the 三合-based start palace and the 小限 palace's 宫干
    (iztro convention).

    ``birth_year`` and ``target_year`` are calendar years; the returned
    ``nominal_age`` (虚岁) is derived from the BaZi (节气) year, so a target
    before 立春 maps to ``target_year - 1`` internally.
    """
    palaces = chart["palaces"]
    bazi_year = _bazi_year_for(target_year, target_pillars["year"][1])
    nominal_age = bazi_year - birth_year + 1

    daxian_palace = _palace_for_nominal_age(palaces, nominal_age)
    daxian = _horoscope_scope("大限", daxian_palace, daxian_palace["ganzhi"][0])

    xiao_palace = _palace_by_branch(
        palaces, _xiaoxian_branch(natal_year_branch, nominal_age, gender)
    )
    # 小限 四化 follows the 宫干 of the 小限 palace (iztro convention), not the 流年 stem.
    xiaoxian = _horoscope_scope("小限", xiao_palace, xiao_palace["ganzhi"][0])

    flowing = []
    for scope, key in (
        ("流年", "year"),
        ("流月", "month"),
        ("流日", "day"),
        ("流时", "hour"),
    ):
        stem, branch = target_pillars[key]
        flowing.append(
            _horoscope_scope(scope, _palace_by_branch(palaces, branch), stem)
        )

    return {
        "engine": "fatebridge-offline",
        "nominal_age": nominal_age,
        "scopes": [daxian, xiaoxian, *flowing],
    }


def build_ziwei_rules(year_stem: Optional[str] = None) -> Dict[str, Any]:
    catalogue = {
        "palace_sequence": ZIWEI_PALACE_SEQUENCE,
        "ming_gong_method": "寅宫起正月，顺数生月，逆数生时。",
        "shen_gong_method": "寅宫起正月，顺数生月，再顺数生时。",
        "sihua_by_year_stem": ZIWEI_SIHUA_RULES,
    }
    focused = None
    if year_stem:
        focused = {
            "year_stem": year_stem,
            "sihua": ordered_sihua_mapping(ZIWEI_SIHUA_RULES[year_stem]),
        }
    return {
        "requested_year_stem": year_stem,
        "rule_catalogue": catalogue,
        "focused_rules": focused,
    }


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
