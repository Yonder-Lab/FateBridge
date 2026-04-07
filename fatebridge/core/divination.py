"""
I Ching and Mei Hua Yi Shu helper utilities.

This module adds lightweight divination support around trigram/hexagram
composition so FateBridge can expose contextual gua information without
depending on an external runtime.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..utils.data import EARTHLY_BRANCHES


BAGUA_BY_NAME: Dict[str, Dict[str, object]] = {
    "乾": {"name": "乾", "nature": "天", "element": "金", "lines": [1, 1, 1], "symbol": "☰", "keywords": "刚健、开创、天道"},
    "兑": {"name": "兑", "nature": "泽", "element": "金", "lines": [1, 1, 0], "symbol": "☱", "keywords": "喜悦、交流、润泽"},
    "离": {"name": "离", "nature": "火", "element": "火", "lines": [1, 0, 1], "symbol": "☲", "keywords": "光明、表达、洞察"},
    "震": {"name": "震", "nature": "雷", "element": "木", "lines": [1, 0, 0], "symbol": "☳", "keywords": "发动、突破、惊醒"},
    "巽": {"name": "巽", "nature": "风", "element": "木", "lines": [0, 1, 1], "symbol": "☴", "keywords": "渗透、谋划、柔入"},
    "坎": {"name": "坎", "nature": "水", "element": "水", "lines": [0, 1, 0], "symbol": "☵", "keywords": "流动、隐忧、险中求通"},
    "艮": {"name": "艮", "nature": "山", "element": "土", "lines": [0, 0, 1], "symbol": "☶", "keywords": "止守、边界、收束"},
    "坤": {"name": "坤", "nature": "地", "element": "土", "lines": [0, 0, 0], "symbol": "☷", "keywords": "承载、包容、顺势"},
}

BAGUA_BY_NUMBER = {
    1: "乾",
    2: "兑",
    3: "离",
    4: "震",
    5: "巽",
    6: "坎",
    7: "艮",
    8: "坤",
}

HEXAGRAM_NAMES: Dict[Tuple[str, str], str] = {
    ("乾", "乾"): "乾为天",
    ("乾", "兑"): "天泽履",
    ("乾", "离"): "天火同人",
    ("乾", "震"): "天雷无妄",
    ("乾", "巽"): "天风姤",
    ("乾", "坎"): "天水讼",
    ("乾", "艮"): "天山遁",
    ("乾", "坤"): "天地否",
    ("兑", "乾"): "泽天夬",
    ("兑", "兑"): "兑为泽",
    ("兑", "离"): "泽火革",
    ("兑", "震"): "泽雷随",
    ("兑", "巽"): "泽风大过",
    ("兑", "坎"): "泽水困",
    ("兑", "艮"): "泽山咸",
    ("兑", "坤"): "泽地萃",
    ("离", "乾"): "火天大有",
    ("离", "兑"): "火泽睽",
    ("离", "离"): "离为火",
    ("离", "震"): "火雷噬嗑",
    ("离", "巽"): "火风鼎",
    ("离", "坎"): "火水未济",
    ("离", "艮"): "火山旅",
    ("离", "坤"): "火地晋",
    ("震", "乾"): "雷天大壮",
    ("震", "兑"): "雷泽归妹",
    ("震", "离"): "雷火丰",
    ("震", "震"): "震为雷",
    ("震", "巽"): "雷风恒",
    ("震", "坎"): "雷水解",
    ("震", "艮"): "雷山小过",
    ("震", "坤"): "雷地豫",
    ("巽", "乾"): "风天小畜",
    ("巽", "兑"): "风泽中孚",
    ("巽", "离"): "风火家人",
    ("巽", "震"): "风雷益",
    ("巽", "巽"): "巽为风",
    ("巽", "坎"): "风水涣",
    ("巽", "艮"): "风山渐",
    ("巽", "坤"): "风地观",
    ("坎", "乾"): "水天需",
    ("坎", "兑"): "水泽节",
    ("坎", "离"): "水火既济",
    ("坎", "震"): "水雷屯",
    ("坎", "巽"): "水风井",
    ("坎", "坎"): "坎为水",
    ("坎", "艮"): "水山蹇",
    ("坎", "坤"): "水地比",
    ("艮", "乾"): "山天大畜",
    ("艮", "兑"): "山泽损",
    ("艮", "离"): "山火贲",
    ("艮", "震"): "山雷颐",
    ("艮", "巽"): "山风蛊",
    ("艮", "坎"): "山水蒙",
    ("艮", "艮"): "艮为山",
    ("艮", "坤"): "山地剥",
    ("坤", "乾"): "地天泰",
    ("坤", "兑"): "地泽临",
    ("坤", "离"): "地火明夷",
    ("坤", "震"): "地雷复",
    ("坤", "巽"): "地风升",
    ("坤", "坎"): "地水师",
    ("坤", "艮"): "地山谦",
    ("坤", "坤"): "坤为地",
}

ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def _bagua_from_lines(lines: List[int]) -> Dict[str, object]:
    target = ",".join(str(bit) for bit in lines)
    for item in BAGUA_BY_NAME.values():
        if ",".join(str(bit) for bit in item["lines"]) == target:
            return item
    return BAGUA_BY_NAME["乾"]


def _bagua_from_number(number: int) -> Dict[str, object]:
    normalized = ((number - 1) % 8) + 1
    return BAGUA_BY_NAME[BAGUA_BY_NUMBER[normalized]]


def build_hexagram(upper_name: str, lower_name: str) -> Dict[str, object]:
    upper = BAGUA_BY_NAME[upper_name]
    lower = BAGUA_BY_NAME[lower_name]
    lines = [*lower["lines"], *upper["lines"]]
    return {
        "name": HEXAGRAM_NAMES.get((upper_name, lower_name), f"{upper['nature']}{lower['nature']}"),
        "upper": upper,
        "lower": lower,
        "lines": lines,
        "binary_code": "".join(str(bit) for bit in lines),
        "symbol": f"{upper['symbol']}{lower['symbol']}",
    }


def build_mutual_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    lines = hexagram["lines"]
    mutual_lines = [lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]]
    lower = _bagua_from_lines(mutual_lines[:3])
    upper = _bagua_from_lines(mutual_lines[3:])
    return build_hexagram(upper["name"], lower["name"])


def build_opposite_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    opposite_lines = [0 if bit == 1 else 1 for bit in hexagram["lines"]]
    lower = _bagua_from_lines(opposite_lines[:3])
    upper = _bagua_from_lines(opposite_lines[3:])
    return build_hexagram(upper["name"], lower["name"])


def build_changed_hexagram(hexagram: Dict[str, object], moving_line: int) -> Dict[str, object]:
    normalized_line = 6 if moving_line % 6 == 0 else moving_line % 6
    changed_lines = list(hexagram["lines"])
    changed_lines[normalized_line - 1] = 0 if changed_lines[normalized_line - 1] == 1 else 1
    lower = _bagua_from_lines(changed_lines[:3])
    upper = _bagua_from_lines(changed_lines[3:])
    changed = build_hexagram(upper["name"], lower["name"])
    changed["moving_line"] = normalized_line
    return changed


def relationship_by_element(left_element: str, right_element: str) -> str:
    if left_element == right_element:
        return "同气相应"
    if ELEMENT_GENERATES[left_element] == right_element:
        return "上生下"
    if ELEMENT_CONTROLS[left_element] == right_element:
        return "上制下"
    if ELEMENT_GENERATES[right_element] == left_element:
        return "下生上"
    if ELEMENT_CONTROLS[right_element] == left_element:
        return "下制上"
    return "关系未明"


def relationship_by_role(body_element: str, use_element: str) -> str:
    if body_element == use_element:
        return "体用比和"
    if ELEMENT_GENERATES[body_element] == use_element:
        return "体生用"
    if ELEMENT_CONTROLS[body_element] == use_element:
        return "体克用"
    if ELEMENT_GENERATES[use_element] == body_element:
        return "用生体"
    if ELEMENT_CONTROLS[use_element] == body_element:
        return "用克体"
    return "体用关系未明"


def resolve_body_use(
    hexagram: Dict[str, object], moving_line: int
) -> Dict[str, object]:
    normalized_line = 6 if moving_line % 6 == 0 else moving_line % 6
    moving_palace = "下卦" if normalized_line <= 3 else "上卦"
    if moving_palace == "下卦":
        body = hexagram["upper"]
        use = hexagram["lower"]
    else:
        body = hexagram["lower"]
        use = hexagram["upper"]

    relation = relationship_by_role(body["element"], use["element"])
    return {
        "moving_palace": moving_palace,
        "body_trigram": body,
        "use_trigram": use,
        "body_use_relation": relation,
        "body_use_summary": (
            f"动爻落{moving_palace}，体卦{body['name']}、用卦{use['name']}，"
            f"五行关系为{relation}。"
        ),
    }


def lookup_hexagram_by_code(code: str) -> Dict[str, object]:
    normalized = "".join(ch for ch in (code or "") if ch in {"0", "1"})
    if len(normalized) != 6:
        raise ValueError("卦码必须是 6 位 0/1 字符串，例如 111111。")
    lower = _bagua_from_lines([int(bit) for bit in normalized[:3]])
    upper = _bagua_from_lines([int(bit) for bit in normalized[3:]])
    hexagram = build_hexagram(upper["name"], lower["name"])
    hexagram["code"] = normalized
    hexagram["summary"] = (
        f"上卦{upper['name']}({upper['keywords']})，下卦{lower['name']}({lower['keywords']})。"
    )
    return hexagram


def derive_meihua_hexagram(
    *,
    year_branch: str,
    lunar_month: int,
    lunar_day: int,
    hour_branch: str,
) -> Dict[str, object]:
    year_number = EARTHLY_BRANCHES.index(year_branch) + 1
    hour_number = EARTHLY_BRANCHES.index(hour_branch) + 1
    upper_number = (year_number + lunar_month + lunar_day) % 8 or 8
    lower_number = (year_number + lunar_month + lunar_day + hour_number) % 8 or 8
    moving_line = (year_number + lunar_month + lunar_day + hour_number) % 6 or 6

    upper = _bagua_from_number(upper_number)
    lower = _bagua_from_number(lower_number)
    base = build_hexagram(upper["name"], lower["name"])
    changed = build_changed_hexagram(base, moving_line)
    mutual = build_mutual_hexagram(base)
    opposite = build_opposite_hexagram(base)
    relation = relationship_by_element(upper["element"], lower["element"])
    body_use = resolve_body_use(base, moving_line)

    return {
        "method": "meihua_time_seed",
        "seed": {
            "year_branch": year_branch,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
            "hour_branch": hour_branch,
            "upper_number": upper_number,
            "lower_number": lower_number,
            "moving_line": moving_line,
        },
        "base_hexagram": base,
        "changed_hexagram": changed,
        "mutual_hexagram": mutual,
        "opposite_hexagram": opposite,
        "element_relation": relation,
        "moving_palace": body_use["moving_palace"],
        "body_trigram": body_use["body_trigram"],
        "use_trigram": body_use["use_trigram"],
        "body_use_relation": body_use["body_use_relation"],
        "body_use_summary": body_use["body_use_summary"],
        "summary": (
            f"梅花时卦得{base['name']}，动{moving_line}爻，之{changed['name']}；"
            f"上卦{upper['name']}、下卦{lower['name']}，五行关系为{relation}。"
        ),
    }
