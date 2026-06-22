"""
Shared primitives for the FateBridge metaphysics package.

Sexagenary-cycle / five-element / xun-kongwang tables and the leaf helpers that
every technique module (zi wei, liu ren, qi men, tai yi, jin kou) builds on,
plus the ``MetaphysicsSeed`` input record. Kept free of any single technique's
logic so domain modules can import from here without cycling back through the
package facade (``metaphysics/__init__.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ...utils.data import (
    BRANCH_ELEMENTS,
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    STEM_ELEMENTS,
)

SEXAGENARY_CYCLE = [
    f"{HEAVENLY_STEMS[index % 10]}{EARTHLY_BRANCHES[index % 12]}" for index in range(60)
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


def rotate_sequence(
    values: Iterable[str], start_value: str, reverse: bool = False
) -> List[str]:
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
