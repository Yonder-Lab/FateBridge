"""
Offline Chinese metaphysics helpers for FateBridge.

These routines intentionally stay lightweight and deterministic so the
project can expose structured Zi Wei, Liu Ren, Qi Men, Tai Yi, and
Jin Kou outputs without depending on a separate runtime.
"""

from __future__ import annotations

from functools import lru_cache
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .almanac import (
    DAY_GANZHI_STRATEGY_STANDARD,
    get_jieqi_year_grid,
    localize_datetime,
)
from .calendar import BaZiCalendar, resolve_bazi_effective_date
from .divination import build_hexagram
from ..utils.data import (
    BRANCH_ELEMENTS,
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    STEM_ELEMENTS,
    get_nayin,
)
from ..utils.helpers import normalize_gender


# 五行局数字与标签 (紫微斗数): 水二局 / 木三局 / 金四局 / 土五局 / 火六局
_WUXING_JU_NUMBER_BY_ELEMENT: Dict[str, int] = {
    "水": 2, "木": 3, "金": 4, "土": 5, "火": 6,
}
_WUXING_JU_LABEL_BY_NUMBER: Dict[int, str] = {
    2: "水二局", 3: "木三局", 4: "金四局", 5: "土五局", 6: "火六局",
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

QIMEN_SAN_YUAN_FU_TOU = (
    "甲子",
    "甲午",
    "甲寅",
    "甲申",
    "甲辰",
    "甲戌",
    "己卯",
    "己酉",
    "己巳",
    "己亥",
    "己丑",
    "己未",
)
QIMEN_SAN_YUAN_FU_TOU_SET = set(QIMEN_SAN_YUAN_FU_TOU)

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

SIX_CLASH_BRANCHES = {
    "子": "午",
    "午": "子",
    "丑": "未",
    "未": "丑",
    "寅": "申",
    "申": "寅",
    "卯": "酉",
    "酉": "卯",
    "辰": "戌",
    "戌": "辰",
    "巳": "亥",
    "亥": "巳",
}

SIX_HARM_BRANCHES = {
    "子": "未",
    "未": "子",
    "丑": "午",
    "午": "丑",
    "寅": "巳",
    "巳": "寅",
    "卯": "辰",
    "辰": "卯",
    "申": "亥",
    "亥": "申",
    "酉": "戌",
    "戌": "酉",
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

ZIWEI_BRANCH_SEQUENCE = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
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

QIMEN_HEAVEN_STEMS = ["壬", "癸", "丁", "丙", "戊", "己", "庚", "辛", "乙"]
QIMEN_EARTH_STEMS = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]
QIMEN_CN_NUMBERS = tuple("一二三四五六七八九")
QIMEN_GUA_SEQUENCE = ("坎", "坤", "震", "巽", "中", "乾", "兑", "艮", "离")
QIMEN_CLOCKWISE_GUA_SEQUENCE = ("坎", "艮", "震", "巽", "离", "坤", "兑", "乾")
QIMEN_DOOR_RING = ("休", "生", "伤", "杜", "景", "死", "惊", "开")
QIMEN_STAR_RING = ("蓬", "任", "冲", "辅", "英", "禽", "柱", "心")
QIMEN_JIU_XING_RING = ("蓬", "芮", "冲", "辅", "禽", "心", "柱", "任", "英")
QIMEN_DOOR_ROUTE = ("休", "死", "伤", "杜", "中", "开", "惊", "生", "景")
QIMEN_STAR_DISPLAY = {
    "蓬": "天蓬",
    "任": "天任",
    "冲": "天冲",
    "辅": "天辅",
    "英": "天英",
    "芮": "天芮",
    "禽": "天禽",
    "柱": "天柱",
    "心": "天心",
}
QIMEN_DOOR_DISPLAY = {
    "休": "休门",
    "生": "生门",
    "伤": "伤门",
    "杜": "杜门",
    "景": "景门",
    "死": "死门",
    "惊": "惊门",
    "开": "开门",
}
QIMEN_STAR_CODE_BY_DISPLAY = {value: key for key, value in QIMEN_STAR_DISPLAY.items()}
QIMEN_DOOR_CODE_BY_DISPLAY = {value: key for key, value in QIMEN_DOOR_DISPLAY.items()}
QIMEN_GOD_DISPLAY = {
    "符": "值符",
    "蛇": "螣蛇",
    "阴": "太阴",
    "合": "六合",
    "虎": "白虎",
    "玄": "玄武",
    "地": "九地",
    "天": "九天",
}
QIMEN_STARS = tuple(
    QIMEN_STAR_DISPLAY[key]
    for key in ("蓬", "任", "冲", "辅", "英", "芮", "柱", "心", "禽")
)
QIMEN_DOORS = tuple(QIMEN_DOOR_DISPLAY.get(key, "中门") for key in QIMEN_DOOR_ROUTE)
QIMEN_GODS = tuple(QIMEN_GOD_DISPLAY[key] for key in ("符", "蛇", "阴", "合", "虎", "玄", "地", "天", "符"))
QIMEN_FUHEAD_HEAVEN_STEM = {
    "甲子": "戊",
    "甲戌": "己",
    "甲申": "庚",
    "甲午": "辛",
    "甲辰": "壬",
    "甲寅": "癸",
}
QIMEN_ZHIFU_TABLE_YANG = {
    "一": "九八七一二三四五六",
    "二": "一九八二三四五六七",
    "三": "二一九三四五六七八",
    "四": "三二一四五六七八九",
    "五": "四三二五六七八九一",
    "六": "五四三六七八九一二",
    "七": "六五四七八九一二三",
    "八": "七六五八九一二三四",
    "九": "八七六九一二三四五",
}
QIMEN_ZHIFU_TABLE_YIN = {
    "九": "一二三九八七六五四",
    "八": "九一二八七六五四三",
    "七": "八九一七六五四三二",
    "六": "七八九六五四三二一",
    "五": "六七八五四三二一九",
    "四": "五六七四三二一九八",
    "三": "四五六三二一九八七",
    "二": "三四五二一九八七六",
    "一": "二三四一九八七六五",
}
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

# 按传统时家奇门常用节气定局表，局数随上中下元变化。
QIMEN_JU_BY_TERM = {
    "冬至": (1, 7, 4),
    "小寒": (2, 8, 5),
    "大寒": (3, 9, 6),
    "立春": (8, 5, 2),
    "雨水": (9, 6, 3),
    "惊蛰": (1, 7, 4),
    "春分": (3, 9, 6),
    "清明": (4, 1, 7),
    "谷雨": (5, 2, 8),
    "立夏": (4, 1, 7),
    "小满": (5, 2, 8),
    "芒种": (6, 3, 9),
    "夏至": (9, 3, 6),
    "小暑": (8, 2, 5),
    "大暑": (7, 1, 4),
    "立秋": (2, 5, 8),
    "处暑": (1, 4, 7),
    "白露": (9, 3, 6),
    "秋分": (7, 1, 4),
    "寒露": (6, 9, 3),
    "霜降": (5, 8, 2),
    "立冬": (6, 9, 3),
    "小雪": (5, 8, 2),
    "大雪": (4, 7, 1),
}
QIMEN_ZHIRUN_TERM_SEQUENCE = (
    "春分",
    "清明",
    "谷雨",
    "立夏",
    "小满",
    "芒种",
    "夏至",
    "小暑",
    "大暑",
    "立秋",
    "处暑",
    "白露",
    "秋分",
    "寒露",
    "霜降",
    "立冬",
    "小雪",
    "大雪",
    "冬至",
    "小寒",
    "大寒",
    "立春",
    "雨水",
    "惊蛰",
)
QIMEN_PALACE_BY_TRIGRAM = {item["trigram"]: item for item in QIMEN_PALACES}
QIMEN_GUA_BY_NUMERAL = dict(zip(QIMEN_CN_NUMBERS, QIMEN_GUA_SEQUENCE))
QIMEN_JIU_XING_BY_NUMERAL = dict(zip(QIMEN_CN_NUMBERS, QIMEN_JIU_XING_RING))
QIMEN_DOOR_ROUTE_BY_NUMERAL = dict(zip(QIMEN_CN_NUMBERS, QIMEN_DOOR_ROUTE))
QIMEN_EARTH_PLATE_YANG = tuple("戊己庚辛壬癸丁丙乙")
QIMEN_EARTH_PLATE_YIN = tuple("戊乙丙丁癸壬辛庚己")
QIMEN_GOD_RING_YANG = tuple("符蛇阴合勾雀地天")
QIMEN_GOD_RING_YIN = tuple("符蛇阴合虎玄地天")

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


def qimen_futou_for_ganzhi(text: str) -> str:
    cycle_index = sexagenary_index_for(text)
    for offset in range(60):
        candidate = sexagenary_text(cycle_index - offset)
        if candidate in QIMEN_SAN_YUAN_FU_TOU_SET:
            return candidate
    return xun_head_for_ganzhi(text)


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
        earth_branch: sky_order[index]
        for index, earth_branch in enumerate(earth_order)
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


def _qimen_new_list(values: Iterable[str], start_value: str) -> List[str]:
    ordered = list(values)
    if start_value not in ordered:
        return ordered
    start_index = ordered.index(start_value)
    return ordered[start_index:] + ordered[:start_index]


def _qimen_new_list_r(values: Iterable[str], start_value: str) -> List[str]:
    ordered = list(values)
    if start_value not in ordered:
        return ordered
    start_index = ordered.index(start_value)
    result: List[str] = []
    for offset in range(len(ordered)):
        result.append(ordered[(start_index - offset) % len(ordered)])
    return result


def _qimen_zip_map(keys: Iterable[str], values: Iterable[str]) -> Dict[str, str]:
    return {key: value for key, value in zip(keys, values)}


def _qimen_rotate_gua_sequence(yinyang: str) -> Tuple[str, ...]:
    if yinyang == "阴":
        return tuple(reversed(QIMEN_CLOCKWISE_GUA_SEQUENCE))
    return QIMEN_CLOCKWISE_GUA_SEQUENCE


def _qimen_key_to_day_number(key: str) -> int:
    if len(key or "") != 8:
        raise ValueError(f"Invalid qimen day key: {key!r}")
    year = int(key[0:4])
    month = int(key[4:6])
    day = int(key[6:8])
    return datetime(year, month, day).date().toordinal()


def _qimen_day_number_to_key(day_number: int) -> str:
    return datetime.fromordinal(day_number).strftime("%Y%m%d")


def _qimen_next_term(name: str) -> str:
    if name not in QIMEN_ZHIRUN_TERM_SEQUENCE:
        return "冬至"
    index = QIMEN_ZHIRUN_TERM_SEQUENCE.index(name)
    return QIMEN_ZHIRUN_TERM_SEQUENCE[
        (index + 1) % len(QIMEN_ZHIRUN_TERM_SEQUENCE)
    ]


@lru_cache(maxsize=16)
def _qimen_build_year_term_seed(
    year: int,
    timezone_name: str,
) -> Dict[str, Dict[str, str]]:
    return {
        item["name"]: {
            "term": item["name"],
            "date_key": item["date_key"],
            "day_ganzhi": item["day_ganzhi"],
        }
        for item in get_jieqi_year_grid(year, timezone_name)
        if item.get("name")
    }


@lru_cache(maxsize=16)
def _qimen_build_yinyangdun_map(
    year: int,
    timezone_name: str,
) -> Dict[str, Tuple[str, str]]:
    previous_year = _qimen_build_year_term_seed(year - 1, timezone_name)
    current_year = _qimen_build_year_term_seed(year, timezone_name)
    if (
        not previous_year
        or not current_year
        or "大雪" not in previous_year
        or "芒种" not in current_year
        or "大雪" not in current_year
    ):
        return {}

    result: Dict[str, Tuple[str, str]] = {}

    previous_daxue = previous_year["大雪"]
    daxue_start_key = previous_daxue.get("date_key") or ""
    daxue_day_ganzhi = previous_daxue.get("day_ganzhi") or "甲子"
    daxue_index = sexagenary_index_for(daxue_day_ganzhi)
    futou_index = (daxue_index // 15) * 15
    current_day_number = _qimen_key_to_day_number(daxue_start_key)
    rizhu_index = daxue_index

    for _ in range(daxue_index, futou_index + 15):
        result[_qimen_day_number_to_key(current_day_number)] = (
            "大雪",
            sexagenary_text(rizhu_index),
        )
        current_day_number += 1
        rizhu_index = (rizhu_index + 1) % 60

    current_term = "大雪" if daxue_index - futou_index >= 9 else "冬至"
    term_days = 0
    mangzhong_day_number: Optional[int] = None

    for _ in range(300):
        result[_qimen_day_number_to_key(current_day_number)] = (
            current_term,
            sexagenary_text(rizhu_index),
        )
        current_day_number += 1
        rizhu_index = (rizhu_index + 1) % 60
        term_days += 1
        if term_days == 15:
            term_days = 0
            current_term = _qimen_next_term(current_term)
            if current_term == "芒种":
                mangzhong_day_number = current_day_number
                for _ in range(15):
                    result[_qimen_day_number_to_key(current_day_number)] = (
                        current_term,
                        sexagenary_text(rizhu_index),
                    )
                    current_day_number += 1
                    rizhu_index = (rizhu_index + 1) % 60
                break

    mangzhong_start_day = _qimen_key_to_day_number(
        current_year["芒种"].get("date_key") or ""
    )
    current_term = "芒种" if (
        mangzhong_day_number is not None
        and mangzhong_start_day > mangzhong_day_number + 9
    ) else "夏至"
    term_days = 0
    daxue_day_number: Optional[int] = None

    for _ in range(300):
        result[_qimen_day_number_to_key(current_day_number)] = (
            current_term,
            sexagenary_text(rizhu_index),
        )
        current_day_number += 1
        rizhu_index = (rizhu_index + 1) % 60
        term_days += 1
        if term_days == 15:
            term_days = 0
            current_term = _qimen_next_term(current_term)
            if current_term == "大雪":
                daxue_day_number = current_day_number
                for _ in range(15):
                    result[_qimen_day_number_to_key(current_day_number)] = (
                        current_term,
                        sexagenary_text(rizhu_index),
                    )
                    current_day_number += 1
                    rizhu_index = (rizhu_index + 1) % 60
                break

    current_daxue_start_day = _qimen_key_to_day_number(
        current_year["大雪"].get("date_key") or ""
    )
    current_term = "大雪" if (
        daxue_day_number is not None
        and current_daxue_start_day > daxue_day_number + 9
    ) else "冬至"
    term_days = 0

    for _ in range(300):
        result[_qimen_day_number_to_key(current_day_number)] = (
            current_term,
            sexagenary_text(rizhu_index),
        )
        current_day_number += 1
        rizhu_index = (rizhu_index + 1) % 60
        term_days += 1
        if term_days == 15:
            term_days = 0
            current_term = _qimen_next_term(current_term)
            if current_term == "立春":
                result[_qimen_day_number_to_key(current_day_number)] = (
                    current_term,
                    sexagenary_text(rizhu_index),
                )
                break

    return result


def _qimen_effective_ganzhi(seed: MetaphysicsSeed) -> Tuple[str, str]:
    # 晚子时 (23:00-23:59) 翻日规则现已由 BaZiCalendar 统一处理：
    # - calculate_hour_pillar 会把 23 时的 day stem 对齐到次日
    # - get_four_pillars 的 day pillar 同样已翻日
    # 所以只要 seed.pillars 是走 get_four_pillars 得到的，就与 Qimen 预期一致，
    # 这里不再需要手动 +1 天。
    local_datetime = localize_datetime(seed.corrected_datetime, seed.timezone)
    if local_datetime.hour != 23:
        return ganzhi_text(seed.pillars["day"]), ganzhi_text(seed.pillars["hour"])

    day_pillar = BaZiCalendar.calculate_day_pillar(
        *resolve_bazi_effective_date(
            local_datetime.year,
            local_datetime.month,
            local_datetime.day,
            local_datetime.hour,
        ),
        strategy=DAY_GANZHI_STRATEGY_STANDARD,
    )
    hour_pillar = BaZiCalendar.calculate_hour_pillar(
        local_datetime.year,
        local_datetime.month,
        local_datetime.day,
        local_datetime.hour,
        day_pillar_strategy=DAY_GANZHI_STRATEGY_STANDARD,
    )
    return ganzhi_text(day_pillar), ganzhi_text(hour_pillar)


def _qimen_resolve_zhirun_meta(
    *,
    seed: MetaphysicsSeed,
    fallback_term: str,
    fallback_ju: int,
) -> Dict[str, Any]:
    local_datetime = localize_datetime(seed.corrected_datetime, seed.timezone)
    target_day_number = _qimen_key_to_day_number(local_datetime.strftime("%Y%m%d"))
    if local_datetime.hour == 23:
        target_day_number += 1
    target_key = _qimen_day_number_to_key(target_day_number)
    target_year = int(target_key[:4])
    yinyangdun_map = _qimen_build_yinyangdun_map(target_year, seed.timezone)
    resolved_term, resolved_day_ganzhi = yinyangdun_map.get(
        target_key,
        (fallback_term, None),
    )
    effective_day_ganzhi, _ = _qimen_effective_ganzhi(seed)
    ju_day_ganzhi = resolved_day_ganzhi or effective_day_ganzhi
    yuan = _qimen_find_yuan(ju_day_ganzhi)
    ju_number = _qimen_ju_number_for_term(
        current_term=resolved_term,
        yuan=yuan,
        fallback_ju=fallback_ju,
    )
    dun_type = "阳遁" if resolved_term in QIMEN_YANG_TERMS else "阴遁"
    return {
        "current_term": resolved_term,
        "day_ganzhi": ju_day_ganzhi,
        "yuan": yuan,
        "ju_number": ju_number,
        "dun_type": dun_type,
    }


def _qimen_find_yuan(day_ganzhi: str) -> str:
    cycle_index = sexagenary_index_for(day_ganzhi) % 15
    if cycle_index < 5:
        return "上元"
    if cycle_index < 10:
        return "中元"
    return "下元"


def _qimen_find_yuan_from_delta(days_since_current: float) -> str:
    if days_since_current < 5:
        return "上元"
    if days_since_current < 10:
        return "中元"
    return "下元"


def _qimen_ju_number_for_term(
    *,
    current_term: str,
    yuan: str,
    fallback_ju: int,
) -> int:
    table = QIMEN_JU_BY_TERM.get(current_term)
    if not table:
        return fallback_ju
    yuan_index = {"上元": 0, "中元": 1, "下元": 2}[yuan]
    return table[yuan_index]


def _qimen_build_ju_text(dun_type: str, ju_number: int, yuan: str) -> str:
    index = max(1, min(9, int(ju_number))) - 1
    return f"{dun_type}{QIMEN_CN_NUMBERS[index]}局{yuan}"


def _qimen_parse_meta(ju_text: str) -> Dict[str, str]:
    text = ju_text or "阳遁一局上元"
    return {
        "text": text,
        "yy": "阴" if "阴遁" in text else "阳",
        "kook": next((char for char in text if char in QIMEN_CN_NUMBERS), "一"),
        "yuan": "上元" if "上元" in text else ("中元" if "中元" in text else "下元"),
    }


def _qimen_zhifu_pai(ju_text: str) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    table = QIMEN_ZHIFU_TABLE_YIN if meta["yy"] == "阴" else QIMEN_ZHIFU_TABLE_YANG
    pai = table[meta["kook"]]
    if meta["yy"] == "阴":
        numerals = _qimen_new_list_r(QIMEN_CN_NUMBERS, meta["kook"])[:6]
    else:
        numerals = _qimen_new_list(QIMEN_CN_NUMBERS, meta["kook"])[:6]
    values = [f"{numeral}{pai}" for numeral in numerals]
    return _qimen_zip_map(XUN_HEADS, values)


def _qimen_zhishi_pai(ju_text: str) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    new_kook = _qimen_new_list(QIMEN_CN_NUMBERS, meta["kook"])
    new_kook_r = _qimen_new_list_r(QIMEN_CN_NUMBERS, meta["kook"])
    yang_text = "".join(new_kook) * 3
    yin_text = "".join(new_kook_r) * 3
    yang_values = [
        f"{numeral}{yang_text[yang_text.index(numeral) + 1 : yang_text.index(numeral) + 12]}"
        for numeral in new_kook[:6]
    ]
    yin_values = [
        f"{numeral}{yin_text[yin_text.index(numeral) + 1 : yin_text.index(numeral) + 12]}"
        for numeral in new_kook_r[:6]
    ]
    values = yin_values if meta["yy"] == "阴" else yang_values
    return _qimen_zip_map(XUN_HEADS, values)


def _qimen_resolve_special_zhishi(
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> str:
    _ = (dun_type, current_term)
    return "死"


def _qimen_zhifu_zhishi(
    time_ganzhi: str,
    ju_text: str,
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    heavenly_stem = time_ganzhi[:1]
    hgan_index = HEAVENLY_STEMS.index(heavenly_stem) if heavenly_stem in HEAVENLY_STEMS else 0
    time_xun_head = xun_head_for_ganzhi(time_ganzhi)

    zhishi_pai = _qimen_zhishi_pai(ju_text)
    zhifu_pai = _qimen_zhifu_pai(ju_text)
    zhishi_keys = list(zhishi_pai.keys())
    zhishi_values = list(zhishi_pai.values())
    zhifu_keys = list(zhifu_pai.keys())
    zhifu_values = list(zhifu_pai.values())

    door_codes = [
        QIMEN_DOOR_ROUTE_BY_NUMERAL.get(value[0], "死")
        for value in zhishi_values
    ]
    star_codes = [
        QIMEN_JIU_XING_BY_NUMERAL.get(value[0], "芮")
        for value in zhifu_values
    ]
    star_gongs = [
        QIMEN_GUA_BY_NUMERAL.get(value[hgan_index], "中")
        for value in zhifu_values
        if hgan_index < len(value)
    ]
    door_gongs = [
        QIMEN_GUA_BY_NUMERAL.get(value[hgan_index], "中")
        for value in zhishi_values
        if hgan_index < len(value)
    ]

    star = _qimen_zip_map(zhifu_keys, star_codes).get(time_xun_head, "芮")
    star_gong = _qimen_zip_map(zhifu_keys, star_gongs).get(time_xun_head, "中")
    door = _qimen_zip_map(zhishi_keys, door_codes).get(time_xun_head, "死")
    if star == "禽":
        door = _qimen_resolve_special_zhishi(dun_type=dun_type, current_term=current_term)
    elif door == "中":
        door = "死"
    door_gong = _qimen_zip_map(zhishi_keys, door_gongs).get(time_xun_head, "中")

    return {
        "xun_head": time_xun_head,
        "zhifu_heaven_stem": QIMEN_FUHEAD_HEAVEN_STEM.get(time_xun_head, "戊"),
        "star": star,
        "star_gong": star_gong,
        "door": door,
        "door_gong": door_gong,
        "dun_type": meta["yy"],
    }


def _qimen_pan_earth(ju_text: str) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    palace_order = [
        QIMEN_GUA_BY_NUMERAL[numeral]
        for numeral in _qimen_new_list(QIMEN_CN_NUMBERS, meta["kook"])
    ]
    values = QIMEN_EARTH_PLATE_YIN if meta["yy"] == "阴" else QIMEN_EARTH_PLATE_YANG
    return _qimen_zip_map(palace_order, values)


def _qimen_pan_god(
    time_ganzhi: str,
    ju_text: str,
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    zfzs = _qimen_zhifu_zhishi(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    rotate = _qimen_rotate_gua_sequence(meta["yy"])
    starting_gong = zfzs["star_gong"]
    gong_reorder = _qimen_new_list(rotate, "坤" if starting_gong == "中" else starting_gong)
    god_values = QIMEN_GOD_RING_YIN if meta["yy"] == "阴" else QIMEN_GOD_RING_YANG
    board = _qimen_zip_map(gong_reorder, god_values)
    return {key: value.replace("勾", "虎").replace("雀", "玄") for key, value in board.items()}


def _qimen_pan_door(
    time_ganzhi: str,
    ju_text: str,
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    zfzs = _qimen_zhifu_zhishi(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    rotate = _qimen_rotate_gua_sequence(meta["yy"])
    starting_gong = zfzs["door_gong"]
    starting_door = zfzs["door"]
    gong_reorder = _qimen_new_list(rotate, "坤" if starting_gong == "中" else starting_gong)
    if meta["yy"] == "阴":
        door_order = _qimen_new_list(tuple(reversed(QIMEN_DOOR_RING)), starting_door)
    else:
        door_order = _qimen_new_list(QIMEN_DOOR_RING, starting_door)
    return _qimen_zip_map(gong_reorder, door_order)


def _qimen_pan_star(
    time_ganzhi: str,
    ju_text: str,
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    zfzs = _qimen_zhifu_zhishi(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    rotate = _qimen_rotate_gua_sequence(meta["yy"])
    starting_gong = zfzs["star_gong"]
    starting_star = zfzs["star"].replace("芮", "禽")
    gong_reorder = _qimen_new_list(rotate, "坤" if starting_gong == "中" else starting_gong)
    if meta["yy"] == "阴":
        star_order = _qimen_new_list(tuple(reversed(QIMEN_STAR_RING)), starting_star)
    else:
        star_order = _qimen_new_list(QIMEN_STAR_RING, starting_star)
    board = _qimen_zip_map(gong_reorder, star_order)
    return {key: value.replace("禽", "芮") for key, value in board.items()}


def _qimen_pan_sky(
    time_ganzhi: str,
    ju_text: str,
    *,
    dun_type: str,
    current_term: Optional[str] = None,
) -> Dict[str, str]:
    meta = _qimen_parse_meta(ju_text)
    rotate = _qimen_rotate_gua_sequence(meta["yy"])
    earth_plate = _qimen_pan_earth(ju_text)
    earth_reverse = {value: key for key, value in earth_plate.items()}
    zfzs = _qimen_zhifu_zhishi(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )

    time_stem = time_ganzhi[:1]
    fu_head = QIMEN_FUHEAD_HEAVEN_STEM.get(xun_head_for_ganzhi(time_ganzhi), "戊")
    time_stem_gong = earth_reverse.get(time_stem)
    zhifu_gong = zfzs["star_gong"]
    fu_head_gong = earth_reverse.get(fu_head)
    start_gong = "坤" if time_stem_gong == "中" else (time_stem_gong or "坤")
    if start_gong != "坤" and start_gong not in rotate:
        start_gong = "坤"

    earth_ring = [earth_plate[gua] for gua in rotate]
    start_stem = fu_head
    if start_stem not in earth_ring:
        zhifu_stem = zfzs["zhifu_heaven_stem"]
        start_stem = zhifu_stem if zhifu_stem in earth_ring else earth_plate.get(start_gong, start_stem)
    if zhifu_gong != "中" and zfzs["star"].replace("芮", "禽") != "禽" and fu_head_gong == "中":
        start_stem = earth_plate.get(start_gong, start_stem)
    if time_stem_gong is None:
        start_stem = earth_plate.get(start_gong, start_stem)

    stem_reorder = _qimen_new_list(earth_ring, start_stem)
    gong_reorder = _qimen_new_list(rotate, start_gong)
    board = _qimen_zip_map(gong_reorder, stem_reorder)
    board["中"] = earth_plate["中"]
    return board


def _qimen_build_palaces(
    *,
    time_ganzhi: str,
    ju_text: str,
    dun_type: str,
    current_term: str,
) -> List[Dict[str, Any]]:
    earth_plate = _qimen_pan_earth(ju_text)
    sky_plate = _qimen_pan_sky(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    star_plate = _qimen_pan_star(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    door_plate = _qimen_pan_door(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    god_plate = _qimen_pan_god(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )

    palaces: List[Dict[str, Any]] = []
    for palace in QIMEN_PALACES:
        trigram = palace["trigram"]
        board_key = trigram
        if trigram == "中":
            door = "中门"
            star = "天禽"
            god = "值符"
        else:
            door = QIMEN_DOOR_DISPLAY.get(door_plate.get(board_key, "死"), "中门")
            star = QIMEN_STAR_DISPLAY.get(star_plate.get(board_key, "芮"), "天芮")
            god = QIMEN_GOD_DISPLAY.get(god_plate.get(board_key, "符"), "值符")
        palace_trigram = trigram if trigram != "中" else "坤"
        door_hexagram = build_hexagram(
            upper_name=palace_trigram,
            lower_name=QIMEN_DOOR_TO_TRIGRAM[door],
        )
        palaces.append(
            {
                "name": palace["label"],
                "trigram": trigram,
                "content_palace": palace["label"],
                "content_trigram": trigram,
                "heaven_stem": sky_plate.get(board_key, earth_plate.get(board_key, "")),
                "earth_stem": earth_plate.get(board_key, ""),
                "god": god,
                "door": door,
                "star": star,
                "door_hexagram": {
                    "name": door_hexagram["name"],
                    "binary_code": door_hexagram["binary_code"],
                },
            }
        )
    return palaces


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
        HEAVENLY_STEMS[(yin_stem_base + (ming_index + offset) % 12) % len(HEAVENLY_STEMS)]
        for offset in range(12)
    ]
    palace_branches = ZIWEI_BRANCH_SEQUENCE[ming_index:] + ZIWEI_BRANCH_SEQUENCE[:ming_index]
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
        "紫微": 0, "天机": -1, "太阳": -3, "武曲": -4, "天同": -5, "廉贞": -8
    }
    # Tian Fu group (Clockwise relative to Tian Fu)
    tianfu_group = {
        "天府": 0, "太阴": 1, "贪狼": 2, "巨门": 3, "天相": 4, "天梁": 5, "七杀": 6, "破军": 10
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
        palace = {
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
    aux_locators = {
        "左辅": (2 + lunar_month - 1) % 12,           # Starts from 辰 (2)
        "右弼": (8 - (lunar_month - 1)) % 12,        # Starts from 戌 (8)
        "文昌": (9 - (hour_index - 1)) % 12,         # Starts from 戌 (9) - Wait, let me check
        "文曲": (3 + (hour_index - 1)) % 12,         # Starts from 辰 (3) - Wait, check
    }
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
        "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
        "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
    }
    tiankui_by_year_stem = {
        "甲": "丑", "戊": "丑", "庚": "丑",
        "乙": "子", "己": "子",
        "丙": "亥", "丁": "亥",
        "辛": "午",
        "壬": "卯", "癸": "卯",
    }
    tianyue_by_year_stem = {
        "甲": "未", "戊": "未", "庚": "未",
        "乙": "申", "己": "申",
        "丙": "酉", "丁": "酉",
        "辛": "寅",
        "壬": "巳", "癸": "巳",
    }
    # 年支三合局定马 / 火铃起点
    tianma_by_year_branch = {
        "寅": "申", "午": "申", "戌": "申",
        "申": "寅", "子": "寅", "辰": "寅",
        "巳": "亥", "酉": "亥", "丑": "亥",
        "亥": "巳", "卯": "巳", "未": "巳",
    }
    huoxing_start_by_year_branch = {
        "寅": "丑", "午": "丑", "戌": "丑",
        "申": "寅", "子": "寅", "辰": "寅",
        "巳": "卯", "酉": "卯", "丑": "卯",
        "亥": "酉", "卯": "酉", "未": "酉",
    }
    lingxing_start_by_year_branch = {
        "寅": "卯", "午": "卯", "戌": "卯",
        "申": "戌", "子": "戌", "辰": "戌",
        "巳": "戌", "酉": "戌", "丑": "戌",
        "亥": "戌", "卯": "戌", "未": "戌",
    }

    def _branch_by_offset(start_branch: str, offset: int) -> str:
        return EARTHLY_BRANCHES[
            (EARTHLY_BRANCHES.index(start_branch) + offset) % 12
        ]

    lucun_branch = lucun_by_year_stem[year_stem]
    minor_star_branches: Dict[str, str] = {
        "禄存": lucun_branch,
        "擎羊": _branch_by_offset(lucun_branch, 1),   # 禄存前一位
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
        "寅": "戌", "午": "戌", "戌": "戌",
        "申": "辰", "子": "辰", "辰": "辰",
        "巳": "丑", "酉": "丑", "丑": "丑",
        "亥": "未", "卯": "未", "未": "未",
    }
    xianchi_by_triad = {
        "寅": "卯", "午": "卯", "戌": "卯",
        "申": "酉", "子": "酉", "辰": "酉",
        "巳": "午", "酉": "午", "丑": "午",
        "亥": "子", "卯": "子", "未": "子",
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
        "子": "巳", "午": "巳", "卯": "巳", "酉": "巳",
        "寅": "酉", "申": "酉", "巳": "酉", "亥": "酉",
        "辰": "丑", "戌": "丑", "丑": "丑", "未": "丑",
    }
    # 蜚廉 按年支（固定表）
    feilian_by_year_branch = {
        "子": "申", "丑": "酉", "寅": "戌", "卯": "巳",
        "辰": "午", "巳": "未", "午": "寅", "未": "卯",
        "申": "辰", "酉": "亥", "戌": "子", "亥": "丑",
    }

    # 年干系 查表
    tianguan_by_year_stem = {
        "甲": "未", "乙": "辰", "丙": "巳", "丁": "寅", "戊": "卯",
        "己": "酉", "庚": "亥", "辛": "酉", "壬": "戌", "癸": "午",
    }
    tianfu_by_year_stem = {
        "甲": "酉", "乙": "申", "丙": "子", "丁": "亥", "戊": "卯",
        "己": "寅", "庚": "午", "辛": "巳", "壬": "午", "癸": "巳",
    }
    tianchu_by_year_stem = {
        "甲": "巳", "乙": "午", "丙": "子", "丁": "巳", "戊": "午",
        "己": "申", "庚": "寅", "辛": "午", "壬": "酉", "癸": "亥",
    }

    # 月系（按生月, 1-12）: 天月 / 天刑 / 天姚 / 天巫 / 解神 / 阴煞
    tianyue_month_table = ["戌","巳","辰","寅","未","卯","亥","未","寅","午","戌","寅"]
    tianxing_start_idx = 9  # 酉起正月顺
    tianyao_start_idx = 1   # 丑起正月顺
    tianwu_cycle = ["巳","申","寅","亥"]  # 4-day cycle
    jieshen_pair_table = ["申","申","戌","戌","子","子","寅","寅","辰","辰","午","午"]
    yinsha_six_cycle = ["寅","子","戌","申","午","辰"]

    # 时系: 封诰 / 台辅
    fenggao_start_idx = 2   # 寅起子时顺
    taifu_start_idx = 6     # 午起子时顺

    # 命宫/身宫 + 年支: 天才 / 天寿
    ming_branch_idx = EARTHLY_BRANCHES.index(ming_branch)
    shen_branch_idx = EARTHLY_BRANCHES.index(shen_branch)

    # 文昌/文曲地支位置（复用前面 aux_locators 公式，转成地支索引）
    wenchang_earth_idx = (10 - hour_earth_index) % 12
    wenqu_earth_idx = (4 + hour_earth_index) % 12
    # 左辅/右弼地支位置（月系）
    zuofu_earth_idx = (4 + lunar_month - 1) % 12   # 辰(4)起正月顺
    youbi_earth_idx = (10 - (lunar_month - 1)) % 12  # 戌(10)起正月逆

    # 旬空: 年支所在旬空亡，阳干取阳支、阴干取阴支
    #   甲子旬 → 戌亥, 甲戌旬 → 申酉, 甲申旬 → 午未,
    #   甲午旬 → 辰巳, 甲辰旬 → 寅卯, 甲寅旬 → 子丑。
    #   第一支为阳(戌/申/午/辰/寅/子)，第二支为阴(亥/酉/未/巳/卯/丑)。
    year_pillar_text = f"{year_stem}{year_branch}"
    year_cycle_index = sexagenary_index_for(year_pillar_text)
    xunkong_pairs = [("戌","亥"),("申","酉"),("午","未"),("辰","巳"),("寅","卯"),("子","丑")]
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
    guiren_start = LIURENG_GUIREN_DAY[day_stem] if is_day else LIURENG_GUIREN_NIGHT[day_stem]
    guiren_reverse = guiren_start in GUI_REN_REVERSED_STARTS
    if month_general_override is not None and month_general_override not in YUE_JIANG_NAMES:
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

    guiren_branches = rotate_sequence(EARTHLY_BRANCHES, guiren_start, reverse=guiren_reverse)
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
    four_lessons = []
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
            les for les in four_lessons
            if les.get("upper_lower_relation") == "上克下"
        ]
        zei_lessons = [
            les for les in four_lessons
            if les.get("upper_lower_relation") == "下贼上"
        ]

        def _pick_zhiyi(lessons: List[Dict[str, Any]]) -> Dict[str, Any]:
            """知一法简化：阳日取 阳支 发用，阴日取 阴支 发用；若无匹配，取课号最小者。"""
            yang_branches = {"子", "寅", "辰", "午", "申", "戌"}
            preferred = [
                les for les in lessons
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
    transmission_payload = {"method": transmission_method}
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


def build_liureng_runyear(seed: MetaphysicsSeed, gender: str, birth_year: int) -> Dict[str, Any]:
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


def build_qimen_board(seed: MetaphysicsSeed) -> Dict[str, Any]:
    current_term_info = seed.calendar_context["current_solar_term"]
    current_term = current_term_info["name"]
    day_ganzhi, time_ganzhi = _qimen_effective_ganzhi(seed)
    # 时家奇门的符头与三元都应从当前日干支回推，不应直接借用节气元数据里的日柱。
    fu_tou = qimen_futou_for_ganzhi(day_ganzhi)
    month_index = EARTHLY_BRANCHES.index(seed.pillars["month"][1])
    day_index = EARTHLY_BRANCHES.index(day_ganzhi[1])
    hour_index = EARTHLY_BRANCHES.index(time_ganzhi[1])
    fallback_ju = ((month_index + day_index + hour_index) % 9) + 1
    ju_meta = _qimen_resolve_zhirun_meta(
        seed=seed,
        fallback_term=current_term,
        fallback_ju=fallback_ju,
    )
    current_term = ju_meta["current_term"]
    dun_type = ju_meta["dun_type"]
    yuan = ju_meta["yuan"]
    ju_number = ju_meta["ju_number"]
    ju_text = _qimen_build_ju_text(dun_type, ju_number, yuan)
    zfzs = _qimen_zhifu_zhishi(
        time_ganzhi,
        ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )
    xun_head = xun_head_for_ganzhi(day_ganzhi)
    kongwang = kongwang_for_ganzhi(day_ganzhi)
    palaces = _qimen_build_palaces(
        time_ganzhi=time_ganzhi,
        ju_text=ju_text,
        dun_type=dun_type,
        current_term=current_term,
    )

    zhifu_palace = next(
        (palace for palace in palaces if palace["trigram"] == zfzs["star_gong"]),
        None,
    )
    if zhifu_palace is None:
        zhifu_star = QIMEN_STAR_DISPLAY.get(zfzs["star"], "天芮")
        zhifu_palace = next(
            (palace for palace in palaces if palace["star"] == zhifu_star),
            palaces[0],
        )
    zhifu_star = zhifu_palace["star"]
    zhifu_star_code = QIMEN_STAR_CODE_BY_DISPLAY.get(zhifu_star, zfzs["star"])

    zhishi_palace = next(
        (palace for palace in palaces if palace["trigram"] == zfzs["door_gong"]),
        None,
    )
    if zhishi_palace is None:
        zhishi_door = QIMEN_DOOR_DISPLAY.get(zfzs["door"], "死门")
        zhishi_palace = next(
            (palace for palace in palaces if palace["door"] == zhishi_door),
            palaces[0],
        )
    zhishi_door = zhishi_palace["door"]
    zhishi_door_code = QIMEN_DOOR_CODE_BY_DISPLAY.get(zhishi_door, zfzs["door"])

    fushi_hexagram = build_hexagram(
        upper_name=zhifu_palace["trigram"] if zhifu_palace["trigram"] != "中" else "坤",
        lower_name=QIMEN_DOOR_TO_TRIGRAM.get(zhishi_door, "坤"),
    )

    return {
        "dun_type": dun_type,
        "ju_number": ju_number,
        "ju_text": ju_text,
        "yuan": yuan,
        "yuan_order": yuan,
        "fu_tou": fu_tou,
        "xun_head": xun_head,
        "kongwang": kongwang,
        "zhifu": {
            "star": zhifu_star,
            "palace": zhifu_palace["name"],
            "trigram": zhifu_palace["trigram"],
            "content_palace": zhifu_palace.get("content_palace", zhifu_palace["name"]),
            "content_trigram": zhifu_palace.get("content_trigram", zhifu_palace["trigram"]),
            "code": zhifu_star_code,
        },
        "zhishi": {
            "door": zhishi_door,
            "palace": zhishi_palace["name"],
            "trigram": zhishi_palace["trigram"],
            "content_palace": zhishi_palace.get("content_palace", zhishi_palace["name"]),
            "content_trigram": zhishi_palace.get("content_trigram", zhishi_palace["trigram"]),
            "code": zhishi_door_code,
        },
        "fushi_hexagram": {
            "name": fushi_hexagram["name"],
            "binary_code": fushi_hexagram["binary_code"],
        },
        "palaces": palaces,
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
        (
            EARTHLY_BRANCHES.index(year_branch)
            + lunar_month
            + lunar_day
            - 1
        )
        % 72
    ) + 1
    main_calculation = (
        f"{'阳' if seed.pillars['year'][0] in '甲丙戊庚壬' else '阴'}遁"
        f"{chinese_numeral(main_calculation_number)}局"
    )

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
    strongest_rows = [
        row for row in rows if POWER_RANK[row["power"]] == strongest_rank
    ]

    preferred_label = JINKOU_USE_POSITION_PREFERENCE.get(board_style_detail)
    if preferred_label and any(row["label"] == preferred_label for row in strongest_rows):
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
    if preferred_label and any(row["label"] == preferred_label for row in strongest_rows):
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
    jiangshen_branch = twelve_board.get(di_fen_branch, {}).get("sky_branch", di_fen_branch)
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
        ("将神", jiangshen_branch, branch_element_text(jiangshen_branch), jiangshen_name),
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
    transmission_method = (
        liureng_board.get("three_transmissions", {}) or {}
    ).get("method", "")
    selected_lesson_relation = (
        (liureng_board.get("meta") or {}).get("selected_lesson_relation") or ""
    )
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
