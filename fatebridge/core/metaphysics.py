"""
Offline Chinese metaphysics helpers for FateBridge.

These routines intentionally stay lightweight and deterministic so the
project can expose structured Zi Wei, Liu Ren, Qi Men, Tai Yi, and
Jin Kou outputs without depending on a separate runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .divination import build_hexagram
from ..utils.data import (
    BRANCH_ELEMENTS,
    DESTRUCTION_CYCLE,
    EARTHLY_BRANCHES,
    GENERATION_CYCLE,
    HEAVENLY_STEMS,
    STEM_ELEMENTS,
)


SEXAGENARY_CYCLE = [
    f"{HEAVENLY_STEMS[index % 10]}{EARTHLY_BRANCHES[index % 12]}"
    for index in range(60)
]
SEXAGENARY_INDEX = {value: index for index, value in enumerate(SEXAGENARY_CYCLE)}

ELEMENT_GENERATES = {
    "木": "火",
    "火": "土",
    "土": "金",
    "金": "水",
    "水": "木",
}

ELEMENT_CONTROLS = {
    "木": "土",
    "火": "金",
    "土": "水",
    "金": "木",
    "水": "火",
}

XUN_HEADS = ("甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅")
KONGWANG_BY_XUN_HEAD = {
    "甲子": "戌亥空",
    "甲戌": "申酉空",
    "甲申": "午未空",
    "甲午": "辰巳空",
    "甲辰": "寅卯空",
    "甲寅": "子丑空",
}

SIX_HARMONY_BRANCHES = {
    "子": "丑",
    "丑": "子",
    "寅": "亥",
    "亥": "寅",
    "卯": "戌",
    "戌": "卯",
    "辰": "酉",
    "酉": "辰",
    "巳": "申",
    "申": "巳",
    "午": "未",
    "未": "午",
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

ZIWEI_BRANCH_SEQUENCE = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
ZIWEI_PALACE_SEQUENCE = [
    "命宫",
    "兄弟宫",
    "夫妻宫",
    "子女宫",
    "财帛宫",
    "疾厄宫",
    "迁移宫",
    "仆役宫",
    "官禄宫",
    "田宅宫",
    "福德宫",
    "父母宫",
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

AUXILIARY_STAR_RULES = {
    "左辅": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (lunar_month - 1) % 12,
    "右弼": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (12 - lunar_month) % 12,
    "文昌": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (day_stem_index + 2) % 12,
    "文曲": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (day_branch_index + 4) % 12,
    "左辅化科引": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (hour_index + 1) % 12,
    "右弼唱和": lambda lunar_month, lunar_day, hour_index, day_stem_index, day_branch_index: (hour_index + 7) % 12,
}

QIMEN_PALACES = [
    {"index": 1, "label": "坎一宫", "trigram": "坎"},
    {"index": 2, "label": "坤二宫", "trigram": "坤"},
    {"index": 3, "label": "震三宫", "trigram": "震"},
    {"index": 4, "label": "巽四宫", "trigram": "巽"},
    {"index": 5, "label": "中五宫", "trigram": "中"},
    {"index": 6, "label": "乾六宫", "trigram": "乾"},
    {"index": 7, "label": "兑七宫", "trigram": "兑"},
    {"index": 8, "label": "艮八宫", "trigram": "艮"},
    {"index": 9, "label": "离九宫", "trigram": "离"},
]

QIMEN_STARS = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心", "天禽"]
QIMEN_DOORS = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门", "中门"]
QIMEN_GODS = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天", "值符"]
QIMEN_HEAVEN_STEMS = ["壬", "癸", "丁", "丙", "戊", "己", "庚", "辛", "乙"]
QIMEN_EARTH_STEMS = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]
QIMEN_DOOR_TO_TRIGRAM = {
    "休门": "坎",
    "生门": "艮",
    "伤门": "震",
    "杜门": "巽",
    "景门": "离",
    "死门": "坤",
    "惊门": "兑",
    "开门": "乾",
    "中门": "坤",
}
QIMEN_YANG_TERMS = {
    "冬至",
    "小寒",
    "大寒",
    "立春",
    "雨水",
    "惊蛰",
    "春分",
    "清明",
    "谷雨",
    "立夏",
    "小满",
    "芒种",
}

TAIYI_PALACE16_ORDER = ["巽", "巳", "午", "未", "坤", "申", "酉", "戌", "乾", "亥", "子", "丑", "艮", "寅", "卯", "辰"]
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
SIHUA_DISPLAY_ORDER = {
    "化忌": 0,
    "化权": 1,
    "化科": 2,
    "化禄": 3,
}


@dataclass(frozen=True)
class MetaphysicsSeed:
    input_datetime: datetime
    corrected_datetime: datetime
    timezone: str
    longitude: Optional[float]
    applied_true_solar: bool
    total_correction_minutes: float
    pillars: Dict[str, Tuple[str, str]]
    calendar_context: Dict[str, Any]


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


def rotate_sequence(values: Iterable[str], start_value: str, reverse: bool = False) -> List[str]:
    ordered = list(values)
    if not ordered:
        return []
    if reverse:
        ordered = list(reversed(ordered))
    if start_value not in ordered:
        return ordered
    start_index = ordered.index(start_value)
    return ordered[start_index:] + ordered[:start_index]


def cyclic_get(values: List[str], index: int) -> str:
    if not values:
        return ""
    return values[index % len(values)]


def stem_element_text(stem: str) -> str:
    return STEM_ELEMENTS[stem][0].value


def branch_element_text(branch: str) -> str:
    return BRANCH_ELEMENTS[branch][0].value


def ganzhi_text(pillar: Tuple[str, str]) -> str:
    return f"{pillar[0]}{pillar[1]}"


def sexagenary_index_for(text: str) -> int:
    return SEXAGENARY_INDEX[text]


def sexagenary_text(index: int) -> str:
    return SEXAGENARY_CYCLE[index % 60]


def xun_head_for_ganzhi(text: str) -> str:
    cycle_index = sexagenary_index_for(text)
    return XUN_HEADS[cycle_index // 10]


def kongwang_for_ganzhi(text: str) -> str:
    return KONGWANG_BY_XUN_HEAD[xun_head_for_ganzhi(text)]


def element_relation(anchor: str, other: str) -> str:
    if anchor == other:
        return "同气"
    if ELEMENT_GENERATES[anchor] == other:
        return "生出"
    if ELEMENT_CONTROLS[anchor] == other:
        return "制约"
    if ELEMENT_GENERATES[other] == anchor:
        return "受生"
    if ELEMENT_CONTROLS[other] == anchor:
        return "受克"
    return "平衡"


def liuqin_against_day(day_element: str, target_element: str) -> str:
    if day_element == target_element:
        return "兄弟"
    if ELEMENT_GENERATES[day_element] == target_element:
        return "子孙"
    if ELEMENT_GENERATES[target_element] == day_element:
        return "父母"
    if ELEMENT_CONTROLS[day_element] == target_element:
        return "妻财"
    if ELEMENT_CONTROLS[target_element] == day_element:
        return "官鬼"
    return "比和"


def status_against_anchor(anchor: str, target: str) -> str:
    if anchor == target:
        return "旺"
    if ELEMENT_GENERATES[anchor] == target:
        return "相"
    if ELEMENT_GENERATES[target] == anchor:
        return "休"
    if ELEMENT_CONTROLS[anchor] == target:
        return "囚"
    return "死"


def chinese_numeral(value: int) -> str:
    mapping = "零一二三四五六七八九"
    if value < 10:
        return mapping[value]
    if value < 20:
        suffix = "" if value == 10 else mapping[value % 10]
        return f"十{suffix}"
    tens = value // 10
    ones = value % 10
    if ones == 0:
        return f"{mapping[tens]}十"
    return f"{mapping[tens]}十{mapping[ones]}"


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
    return ordered_sihua_mapping(sihua)


def build_ziwei_chart(seed: MetaphysicsSeed, gender: str) -> Dict[str, Any]:
    lunar = seed.calendar_context.get("lunar_calendar") or {}
    lunar_month = int(lunar.get("month") or 1)
    lunar_day = int(lunar.get("day") or 1)
    hour_branch = seed.pillars["hour"][1]
    hour_index = _branch_from_hour(hour_branch)
    year_stem = seed.pillars["year"][0]
    day_stem = seed.pillars["day"][0]
    day_branch = seed.pillars["day"][1]
    day_stem_index = HEAVENLY_STEMS.index(day_stem)
    day_branch_index = EARTHLY_BRANCHES.index(day_branch)
    gender_offset = 0 if gender == "男" else 1

    ming_index = (lunar_month - hour_index) % 12
    shen_index = (lunar_month + hour_index - 2) % 12
    ming_branch = ZIWEI_BRANCH_SEQUENCE[ming_index]
    shen_branch = ZIWEI_BRANCH_SEQUENCE[shen_index]

    ming_stem = HEAVENLY_STEMS[
        (HEAVENLY_STEMS.index(year_stem) * 2 + ming_index) % len(HEAVENLY_STEMS)
    ]
    palace_stems = [
        HEAVENLY_STEMS[(HEAVENLY_STEMS.index(ming_stem) + offset) % len(HEAVENLY_STEMS)]
        for offset in range(12)
    ]
    palace_branches = ZIWEI_BRANCH_SEQUENCE[ming_index:] + ZIWEI_BRANCH_SEQUENCE[:ming_index]
    palace_names = ZIWEI_PALACE_SEQUENCE[:]
    ziwei_anchor = (lunar_day + lunar_month + gender_offset - 1) % 12

    palaces: List[Dict[str, Any]] = []
    for index, palace_name in enumerate(palace_names):
        palace = {
            "name": palace_name,
            "ganzhi": f"{palace_stems[index]}{palace_branches[index]}",
            "daxian": f"{3 + index * 10}~{12 + index * 10}",
            "stars": [],
        }
        palaces.append(palace)

    for star_name, offset in ZIWEI_STAR_OFFSETS.items():
        palace_index = (ziwei_anchor + offset) % 12
        palaces[palace_index]["stars"].append(star_name)

    for star_name, locator in AUXILIARY_STAR_RULES.items():
        palace_index = locator(
            lunar_month,
            lunar_day,
            hour_index - 1,
            day_stem_index,
            day_branch_index,
        )
        palaces[palace_index]["stars"].append(star_name)

    sihua = _apply_sihua_to_palaces(palaces, year_stem)
    for palace in palaces:
        palace["stars"] = sorted(dict.fromkeys(palace["stars"]))

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
        "sihua": sihua,
        "palaces": palaces,
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


def build_liureng_board(seed: MetaphysicsSeed, gender: str = "未知") -> Dict[str, Any]:
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

    is_day = hour_branch in {"卯", "辰", "巳", "午", "未", "申"}
    guiren_start = LIURENG_GUIREN_DAY[day_stem] if is_day else LIURENG_GUIREN_NIGHT[day_stem]
    guiren_reverse = guiren_start in GUI_REN_REVERSED_STARTS
    yuejiang_branch = month_branch
    yuejiang_name = YUE_JIANG_NAMES[yuejiang_branch]

    earth_plate = EARTHLY_BRANCHES[:]
    sky_plate = rotate_sequence(earth_plate, yuejiang_branch)
    sky_to_earth = {
        branch: sky_plate[index]
        for index, branch in enumerate(earth_plate)
    }

    guiren_branches = rotate_sequence(EARTHLY_BRANCHES, guiren_start, reverse=guiren_reverse)
    guiren_map = {
        guiren_branches[index]: GUI_REN_SEQUENCE[index]
        for index in range(len(EARTHLY_BRANCHES))
    }

    lesson_bases = [day_branch, hour_branch, yuejiang_branch, seed.pillars["year"][1]]
    four_lessons = []
    for lesson_index, lower_branch in enumerate(lesson_bases, start=1):
        upper_branch = sky_to_earth[lower_branch]
        relation = liuqin_against_day(day_element, branch_element_text(upper_branch))
        four_lessons.append(
            {
                "index": lesson_index,
                "upper_branch": upper_branch,
                "lower_branch": lower_branch,
                "text": f"{upper_branch}加{lower_branch}",
                "relation": relation,
                "use_candidate": lesson_index == 1,
            }
        )

    style = "比用"
    initial_lesson = four_lessons[0]
    for lesson in four_lessons:
        upper_branch = lesson["upper_branch"]
        if SIX_HARMONY_BRANCHES.get(upper_branch) == day_branch:
            style = "涉害"
            initial_lesson = lesson
            break
        if liuqin_against_day(day_element, branch_element_text(upper_branch)) == "官鬼":
            style = "官鬼"
            initial_lesson = lesson
            break

    step = 1 if not guiren_reverse else -1
    initial_branch = initial_lesson["upper_branch"]
    initial_index = EARTHLY_BRANCHES.index(initial_branch)
    transmission_branches = [
        EARTHLY_BRANCHES[(initial_index + step * offset) % 12]
        for offset in range(3)
    ]
    transmission_labels = ["initial", "middle", "final"]
    transmission_payload = {}
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
        f"月将{yuejiang_branch}({yuejiang_name})主盘，当前以{current_term_name}节气入局。",
        f"贵人起于{guiren_start}，{'逆' if guiren_reverse else '顺'}行布十二神将。",
        f"{style}课主导，首传落{initial_branch}，重看{transmission_payload['initial']['relation']}之象。",
    ]

    patterns = [
        {
            "name": f"贵人{'逆' if guiren_reverse else '顺'}行格",
            "basis": f"贵人起{guiren_start}，{'逆' if guiren_reverse else '顺'}布神将。",
        }
    ]

    return {
        "month_general": {
            "branch": yuejiang_branch,
            "name": yuejiang_name,
        },
        "board_style": style,
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
        },
    }


def build_liureng_runyear(seed: MetaphysicsSeed, gender: str, birth_year: int) -> Dict[str, Any]:
    age = max(1, seed.corrected_datetime.year - birth_year + 1)
    if gender == "女":
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


def build_qimen_board(seed: MetaphysicsSeed) -> Dict[str, Any]:
    current_term = seed.calendar_context["current_solar_term"]["name"]
    day_ganzhi = ganzhi_text(seed.pillars["day"])
    xun_head = xun_head_for_ganzhi(day_ganzhi)
    kongwang = kongwang_for_ganzhi(day_ganzhi)
    dun_type = "阳遁" if current_term in QIMEN_YANG_TERMS else "阴遁"
    month_index = EARTHLY_BRANCHES.index(seed.pillars["month"][1])
    day_index = EARTHLY_BRANCHES.index(seed.pillars["day"][1])
    hour_index = EARTHLY_BRANCHES.index(seed.pillars["hour"][1])
    day_stem_index = HEAVENLY_STEMS.index(seed.pillars["day"][0])
    ju_number = ((month_index + day_index + hour_index) % 9) + 1
    palace_start = (hour_index + ju_number - 1) % 9
    god_start = (day_stem_index + hour_index) % 9

    palaces: List[Dict[str, Any]] = []
    for offset, palace in enumerate(QIMEN_PALACES):
        door = QIMEN_DOORS[(palace_start + offset) % len(QIMEN_DOORS)]
        star = QIMEN_STARS[(ju_number - 1 + offset) % len(QIMEN_STARS)]
        god = QIMEN_GODS[(god_start + offset) % len(QIMEN_GODS)]
        heaven_stem = QIMEN_HEAVEN_STEMS[(day_stem_index + offset) % len(QIMEN_HEAVEN_STEMS)]
        earth_stem = QIMEN_EARTH_STEMS[(ju_number - 1 + offset) % len(QIMEN_EARTH_STEMS)]
        palace_trigram = palace["trigram"] if palace["trigram"] != "中" else "坤"
        door_hexagram = build_hexagram(
            upper_name=palace_trigram,
            lower_name=QIMEN_DOOR_TO_TRIGRAM[door],
        )
        palaces.append(
            {
                "name": palace["label"],
                "trigram": palace["trigram"],
                "heaven_stem": heaven_stem,
                "earth_stem": earth_stem,
                "god": god,
                "door": door,
                "star": star,
                "door_hexagram": {
                    "name": door_hexagram["name"],
                    "binary_code": door_hexagram["binary_code"],
                },
            }
        )

    zhifu_palace = next(palace for palace in palaces if palace["god"] == "值符")
    zhishi_palace = next(palace for palace in palaces if palace["door"] == QIMEN_DOORS[palace_start])
    fushi_hexagram = build_hexagram(
        upper_name=zhifu_palace["trigram"] if zhifu_palace["trigram"] != "中" else "坤",
        lower_name=QIMEN_DOOR_TO_TRIGRAM[zhishi_palace["door"]],
    )

    return {
        "dun_type": dun_type,
        "ju_number": ju_number,
        "xun_head": xun_head,
        "kongwang": kongwang,
        "zhifu": {
            "star": zhifu_palace["star"],
            "palace": zhifu_palace["name"],
        },
        "zhishi": {
            "door": zhishi_palace["door"],
            "palace": zhishi_palace["name"],
        },
        "fushi_hexagram": {
            "name": fushi_hexagram["name"],
            "binary_code": fushi_hexagram["binary_code"],
        },
        "palaces": palaces,
    }


def build_taiyi_board(seed: MetaphysicsSeed, gender: str) -> Dict[str, Any]:
    year_branch = seed.pillars["year"][1]
    month_branch = seed.pillars["month"][1]
    day_branch = seed.pillars["day"][1]
    hour_branch = seed.pillars["hour"][1]
    palace_index = (
        EARTHLY_BRANCHES.index(year_branch)
        + EARTHLY_BRANCHES.index(month_branch)
        + EARTHLY_BRANCHES.index(day_branch)
        + EARTHLY_BRANCHES.index(hour_branch)
    ) % len(TAIYI_PALACE16_ORDER)
    taiyi_palace = TAIYI_PALACE16_ORDER[palace_index]
    wanchang_palace = TAIYI_PALACE16_ORDER[(palace_index + 5) % len(TAIYI_PALACE16_ORDER)]
    main_calculation = f"{'阳' if seed.pillars['year'][0] in '甲丙戊庚壬' else '阴'}遁{chinese_numeral((palace_index % 72) + 1)}局"

    marks = {palace: [] for palace in TAIYI_PALACE16_ORDER}
    for marker, offset in TAIYI_MARKER_OFFSETS.items():
        marks[TAIYI_PALACE16_ORDER[(palace_index + offset) % len(TAIYI_PALACE16_ORDER)]].append(marker)
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


def _build_guishen_mapping(day_stem: str, hour_branch: str) -> Tuple[str, Dict[str, str]]:
    is_day = hour_branch in {"卯", "辰", "巳", "午", "未", "申"}
    start_branch = LIURENG_GUIREN_DAY[day_stem] if is_day else LIURENG_GUIREN_NIGHT[day_stem]
    reverse = start_branch in GUI_REN_REVERSED_STARTS
    branches = rotate_sequence(EARTHLY_BRANCHES, start_branch, reverse=reverse)
    return start_branch, {
        EARTHLY_BRANCHES[index]: GUI_REN_SEQUENCE[branches.index(EARTHLY_BRANCHES[index])]
        if EARTHLY_BRANCHES[index] in branches
        else GUI_REN_SEQUENCE[index]
        for index in range(len(EARTHLY_BRANCHES))
    }


def _wuzidun_stem(day_stem: str, branch: str) -> str:
    start_stem = WUZI_DUN_START[day_stem]
    start_index = HEAVENLY_STEMS.index(start_stem)
    branch_index = EARTHLY_BRANCHES.index(branch)
    return HEAVENLY_STEMS[(start_index + branch_index) % len(HEAVENLY_STEMS)]


def build_jinkou_board(
    seed: MetaphysicsSeed,
    liureng_board: Dict[str, Any],
    gender: str = "未知",
    di_fen: Optional[str] = None,
    runyear: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    day_stem = seed.pillars["day"][0]
    hour_branch = seed.pillars["hour"][1]
    month_branch = seed.pillars["month"][1]
    di_fen_branch = di_fen or hour_branch
    yuejiang_branch = liureng_board["month_general"]["branch"]
    yuejiang_name = YUE_JIANG_NAMES[yuejiang_branch]
    guiren_start, guishen_map = _build_guishen_mapping(day_stem, hour_branch)
    guishen_name = guishen_map[di_fen_branch]
    renyuan_stem = _wuzidun_stem(day_stem, di_fen_branch)
    month_element = branch_element_text(month_branch)

    row_defs = [
        ("人元", renyuan_stem, stem_element_text(renyuan_stem), "—"),
        ("贵神", guiren_start, branch_element_text(guiren_start), guishen_name),
        ("将神", yuejiang_branch, branch_element_text(yuejiang_branch), yuejiang_name),
        ("地分", di_fen_branch, branch_element_text(di_fen_branch), "—"),
    ]

    rows = []
    strongest_label = "人元"
    strongest_rank = -1
    for label, content, element, shenjiang in row_defs:
        power = status_against_anchor(month_element, element)
        rank = POWER_RANK[power]
        if rank > strongest_rank:
            strongest_rank = rank
            strongest_label = label
        rows.append(
            {
                "label": label,
                "content": content,
                "shenjiang": shenjiang,
                "element": element,
                "power": power,
            }
        )

    shensha = [
        {"label": "人元", "value": "纳音引气"},
        {"label": "贵神", "value": f"{guishen_name}入课"},
        {"label": "将神", "value": f"{yuejiang_name}临门"},
        {"label": "地分", "value": f"{di_fen_branch}守位"},
    ]

    overview = {
        "di_fen": di_fen_branch,
        "kongwang": liureng_board["kongwang"],
        "si_da_kong": f"{branch_element_text(di_fen_branch)}空",
        "use_position": strongest_label,
        "yuejiang": {
            "branch": yuejiang_branch,
            "name": yuejiang_name,
        },
        "guishen": {
            "start_branch": guiren_start,
            "name": guishen_name,
        },
        "gender": gender,
    }
    if runyear:
        overview["runyear"] = runyear

    return {
        "overview": overview,
        "rows": rows,
        "shensha": shensha,
    }
