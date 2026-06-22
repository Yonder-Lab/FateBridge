"""
Qi Men Dun Jia (奇门遁甲) board construction for the FateBridge metaphysics package.

Pure relocation from the package facade: every QIMEN_* table and _qimen_* helper
plus the public ``build_qimen_board`` / ``qimen_futou_for_ganzhi``. Imports its
shared primitives from ``.common``; no other technique depends on these symbols.
"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils.data import EARTHLY_BRANCHES, HEAVENLY_STEMS
from ..almanac import (
    DAY_GANZHI_STRATEGY_STANDARD,
    get_jieqi_year_grid,
    localize_datetime,
)
from ..calendar import BaZiCalendar, resolve_bazi_effective_date
from ..divination import build_hexagram
from .common import (
    XUN_HEADS,
    MetaphysicsSeed,
    ganzhi_text,
    kongwang_for_ganzhi,
    sexagenary_index_for,
    sexagenary_text,
    xun_head_for_ganzhi,
)

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


QIMEN_PALACES: List[Dict[str, Any]] = [
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


QIMEN_STAR_CODE_BY_DISPLAY: Dict[Any, str] = {
    value: key for key, value in QIMEN_STAR_DISPLAY.items()
}


QIMEN_DOOR_CODE_BY_DISPLAY: Dict[Any, str] = {
    value: key for key, value in QIMEN_DOOR_DISPLAY.items()
}


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


QIMEN_GODS = tuple(
    QIMEN_GOD_DISPLAY[key]
    for key in ("符", "蛇", "阴", "合", "虎", "玄", "地", "天", "符")
)


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


QIMEN_DOOR_TO_TRIGRAM: Dict[Any, str] = {
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


def qimen_futou_for_ganzhi(text: str) -> str:
    cycle_index = sexagenary_index_for(text)
    for offset in range(60):
        candidate = sexagenary_text(cycle_index - offset)
        if candidate in QIMEN_SAN_YUAN_FU_TOU_SET:
            return candidate
    return xun_head_for_ganzhi(text)


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
    return QIMEN_ZHIRUN_TERM_SEQUENCE[(index + 1) % len(QIMEN_ZHIRUN_TERM_SEQUENCE)]


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
    current_term = (
        "芒种"
        if (
            mangzhong_day_number is not None
            and mangzhong_start_day > mangzhong_day_number + 9
        )
        else "夏至"
    )
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
    current_term = (
        "大雪"
        if (
            daxue_day_number is not None
            and current_daxue_start_day > daxue_day_number + 9
        )
        else "冬至"
    )
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
    hgan_index = (
        HEAVENLY_STEMS.index(heavenly_stem) if heavenly_stem in HEAVENLY_STEMS else 0
    )
    time_xun_head = xun_head_for_ganzhi(time_ganzhi)

    zhishi_pai = _qimen_zhishi_pai(ju_text)
    zhifu_pai = _qimen_zhifu_pai(ju_text)
    zhishi_keys = list(zhishi_pai.keys())
    zhishi_values = list(zhishi_pai.values())
    zhifu_keys = list(zhifu_pai.keys())
    zhifu_values = list(zhifu_pai.values())

    door_codes = [
        QIMEN_DOOR_ROUTE_BY_NUMERAL.get(value[0], "死") for value in zhishi_values
    ]
    star_codes = [
        QIMEN_JIU_XING_BY_NUMERAL.get(value[0], "芮") for value in zhifu_values
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
        door = _qimen_resolve_special_zhishi(
            dun_type=dun_type, current_term=current_term
        )
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
    gong_reorder = _qimen_new_list(
        rotate, "坤" if starting_gong == "中" else starting_gong
    )
    god_values = QIMEN_GOD_RING_YIN if meta["yy"] == "阴" else QIMEN_GOD_RING_YANG
    board = _qimen_zip_map(gong_reorder, god_values)
    return {
        key: value.replace("勾", "虎").replace("雀", "玄")
        for key, value in board.items()
    }


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
    gong_reorder = _qimen_new_list(
        rotate, "坤" if starting_gong == "中" else starting_gong
    )
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
    gong_reorder = _qimen_new_list(
        rotate, "坤" if starting_gong == "中" else starting_gong
    )
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
        start_stem = (
            zhifu_stem
            if zhifu_stem in earth_ring
            else earth_plate.get(start_gong, start_stem)
        )
    if (
        zhifu_gong != "中"
        and zfzs["star"].replace("芮", "禽") != "禽"
        and fu_head_gong == "中"
    ):
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
            "content_trigram": zhifu_palace.get(
                "content_trigram", zhifu_palace["trigram"]
            ),
            "code": zhifu_star_code,
        },
        "zhishi": {
            "door": zhishi_door,
            "palace": zhishi_palace["name"],
            "trigram": zhishi_palace["trigram"],
            "content_palace": zhishi_palace.get(
                "content_palace", zhishi_palace["name"]
            ),
            "content_trigram": zhishi_palace.get(
                "content_trigram", zhishi_palace["trigram"]
            ),
            "code": zhishi_door_code,
        },
        "fushi_hexagram": {
            "name": fushi_hexagram["name"],
            "binary_code": fushi_hexagram["binary_code"],
        },
        "palaces": palaces,
    }
