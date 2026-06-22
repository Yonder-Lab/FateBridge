"""
Liu Yao (六爻) divination for the FateBridge local-techniques package.

Pure relocation from the package facade: hexagram-palace lookup, 六神/六亲
enrichment, pattern detection, and public ``build_sixyao_result``. Chart
substrate primitives are imported from ``.chart``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ...utils.helpers import DEFAULT_BIRTH_TIMEZONE
from ..almanac import build_calendar_context
from ..calendar import BaZiCalendar
from ..divination import lookup_hexagram_by_code
from .chart import (
    _join_lines,
    _normalize_date_text,
    _normalize_time_text,
    _render_snapshot_text,
    parse_local_datetime,
)

SIX_YAO_GODS = ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]


SIX_YAO_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]


_TRIGRAM_LOWER_BRANCHES = {
    "乾": ("子", "寅", "辰"),
    "坎": ("寅", "辰", "午"),
    "艮": ("辰", "午", "申"),
    "震": ("子", "寅", "辰"),
    "巽": ("丑", "亥", "酉"),
    "离": ("卯", "丑", "亥"),
    "坤": ("未", "巳", "卯"),
    "兑": ("巳", "卯", "丑"),
}


_TRIGRAM_UPPER_BRANCHES = {
    "乾": ("午", "申", "戌"),
    "坎": ("申", "戌", "子"),
    "艮": ("戌", "子", "寅"),
    "震": ("午", "申", "戌"),
    "巽": ("未", "巳", "卯"),
    "离": ("酉", "未", "巳"),
    "坤": ("丑", "亥", "酉"),
    "兑": ("亥", "酉", "未"),
}


_BAGONG_BASES = [
    ("乾", "111111", "金"),
    ("坎", "010010", "水"),
    ("艮", "001001", "土"),
    ("震", "100100", "木"),
    ("巽", "011011", "木"),
    ("离", "101101", "火"),
    ("坤", "000000", "土"),
    ("兑", "110110", "金"),
]


_BAGONG_POSITION_INFO = [
    ("本宫", "000000", 6),
    ("一世", "100000", 1),
    ("二世", "110000", 2),
    ("三世", "111000", 3),
    ("四世", "111100", 4),
    ("五世", "111110", 5),
    ("游魂", "111010", 4),
    ("归魂", "000010", 3),
]


_BRANCH_TO_ELEMENT = {
    "寅": "木",
    "卯": "木",
    "巳": "火",
    "午": "火",
    "申": "金",
    "酉": "金",
    "亥": "水",
    "子": "水",
    "辰": "土",
    "戌": "土",
    "丑": "土",
    "未": "土",
}


_LIUSHEN_CYCLE = ("青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武")


_LIUSHEN_OFFSET_BY_STEM = {
    "甲": 0,
    "乙": 0,
    "丙": 1,
    "丁": 1,
    "戊": 2,
    "己": 3,
    "庚": 4,
    "辛": 4,
    "壬": 5,
    "癸": 5,
}


def _xor_binary(code: str, mask: str) -> str:
    return "".join("1" if a != b else "0" for a, b in zip(code, mask))


def _build_hexagram_palace_lookup() -> Dict[str, Dict[str, Any]]:
    """根据 8 本宫 × 8 卦位 × XOR 掩码生成 64 卦 → 宫 / 世爻 / 宫五行 查表。"""
    lookup: Dict[str, Dict[str, Any]] = {}
    for palace_name, base_code, palace_element in _BAGONG_BASES:
        for position_name, mask, shi_line in _BAGONG_POSITION_INFO:
            code = _xor_binary(base_code, mask)
            # 应爻 = (世爻 + 3 - 1) % 6 + 1 (1-indexed)
            ying_line = ((shi_line + 2) % 6) + 1
            lookup[code] = {
                "palace": palace_name,
                "palace_element": palace_element,
                "position": position_name,
                "shi_line": shi_line,
                "ying_line": ying_line,
            }
    return lookup


_HEXAGRAM_PALACE_LOOKUP: Dict[str, Dict[str, Any]] = _build_hexagram_palace_lookup()


def _decode_trigrams(code: str) -> Tuple[str, str]:
    """拆分六位二进制到 (下卦, 上卦) 三画卦名。"""
    inv = {
        v: k
        for k, v in {
            "乾": "111",
            "坎": "010",
            "艮": "001",
            "震": "100",
            "巽": "011",
            "离": "101",
            "坤": "000",
            "兑": "110",
        }.items()
    }
    lower = inv.get(code[0:3])
    upper = inv.get(code[3:6])
    return lower or "?", upper or "?"


_LIUCHONG_HEXAGRAM_CODES = frozenset(
    {
        "111111",  # 乾为天
        "000000",  # 坤为地
        "100100",  # 震为雷
        "011011",  # 巽为风
        "010010",  # 坎为水
        "101101",  # 离为火
        "001001",  # 艮为山
        "110110",  # 兑为泽
    }
)


_LIUHE_HEXAGRAM_CODES = frozenset(
    {
        "111000",  # 地天泰
        "000111",  # 天地否
        "000100",  # 雷地豫
        "100000",  # 地雷复
        "010110",  # 泽水困
        "110010",  # 水泽节
        "001101",  # 火山旅
        "101001",  # 山火贲
    }
)


_BRANCH_CLASH = {
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


def _detect_sixyao_patterns(
    current_code: str,
    changed_code: str,
    current_branches: List[str],
    changed_branches: List[str],
    moving_indices: List[int],
) -> Dict[str, Any]:
    """识别六爻常见格局：六冲/六合/反吟/伏吟。"""
    patterns: List[Dict[str, str]] = []
    # 本卦六冲 / 六合
    if current_code in _LIUCHONG_HEXAGRAM_CODES:
        patterns.append({"name": "本卦六冲", "basis": "本卦为八纯冲卦。"})
    if current_code in _LIUHE_HEXAGRAM_CODES:
        patterns.append({"name": "本卦六合", "basis": "本卦为六合卦。"})
    # 之卦六冲 / 六合
    if current_code != changed_code:
        if changed_code in _LIUCHONG_HEXAGRAM_CODES:
            patterns.append({"name": "变卦六冲", "basis": "之卦转为六冲。"})
        if changed_code in _LIUHE_HEXAGRAM_CODES:
            patterns.append({"name": "变卦六合", "basis": "之卦归六合。"})

    # 伏吟 / 反吟 (只在动爻上判断, 避开 changed_branch 为空的静爻)
    fu_count = 0
    fan_count = 0
    for idx in moving_indices:
        if idx < 0 or idx >= 6:
            continue
        orig_branch = current_branches[idx]
        new_branch = changed_branches[idx]
        if not orig_branch or not new_branch:
            continue
        if orig_branch == new_branch:
            fu_count += 1
        elif _BRANCH_CLASH.get(orig_branch) == new_branch:
            fan_count += 1
    if fu_count and fu_count == len(moving_indices):
        patterns.append(
            {
                "name": "伏吟",
                "basis": "动爻所变支全与本支同 (伏而不动)。",
            }
        )
    elif fu_count:
        patterns.append(
            {
                "name": "局部伏吟",
                "basis": f"{fu_count}个动爻之支与原支相同。",
            }
        )
    if fan_count and fan_count == len(moving_indices):
        patterns.append({"name": "反吟", "basis": "动爻所变支全与本支相冲。"})
    elif fan_count:
        patterns.append(
            {
                "name": "局部反吟",
                "basis": f"{fan_count}个动爻之支与原支相冲。",
            }
        )

    return {
        "patterns": patterns,
        "is_liuchong_base": current_code in _LIUCHONG_HEXAGRAM_CODES,
        "is_liuhe_base": current_code in _LIUHE_HEXAGRAM_CODES,
        "is_liuchong_changed": changed_code in _LIUCHONG_HEXAGRAM_CODES,
        "is_liuhe_changed": changed_code in _LIUHE_HEXAGRAM_CODES,
    }


def _liuqin_against_palace(palace_element: str, line_element: str) -> str:
    if palace_element == line_element:
        return "兄弟"
    generates = {"金": "水", "水": "木", "木": "火", "火": "土", "土": "金"}
    controls = {"金": "木", "木": "土", "土": "水", "水": "火", "火": "金"}
    if generates.get(line_element) == palace_element:
        return "父母"  # 生宫者
    if generates.get(palace_element) == line_element:
        return "子孙"  # 宫所生
    if controls.get(line_element) == palace_element:
        return "官鬼"  # 克宫者
    if controls.get(palace_element) == line_element:
        return "妻财"  # 宫所克
    return "平"


def _build_sixyao_enrichment(
    current_code: str,
    changed_code: str,
    day_gan: Optional[str],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """生成本卦信息 + 六爻纳甲/世应/六亲/六神。lines 下标 0=初爻，5=上爻。"""

    current_info = _HEXAGRAM_PALACE_LOOKUP.get(current_code, {})
    changed_info = _HEXAGRAM_PALACE_LOOKUP.get(changed_code, {})

    lower_trigram, upper_trigram = _decode_trigrams(current_code)
    lower_branches = _TRIGRAM_LOWER_BRANCHES.get(lower_trigram, ("", "", ""))
    upper_branches = _TRIGRAM_UPPER_BRANCHES.get(upper_trigram, ("", "", ""))
    branches = list(lower_branches) + list(upper_branches)

    # 之卦地支 (仅作参考, 用于动爻变后的六亲比对)
    changed_lower_trigram, changed_upper_trigram = _decode_trigrams(changed_code)
    changed_branches = list(
        _TRIGRAM_LOWER_BRANCHES.get(changed_lower_trigram, ("", "", ""))
    ) + list(_TRIGRAM_UPPER_BRANCHES.get(changed_upper_trigram, ("", "", "")))

    palace_element = current_info.get("palace_element", "")
    shi_line = current_info.get("shi_line", 0)
    ying_line = current_info.get("ying_line", 0)

    offset = _LIUSHEN_OFFSET_BY_STEM.get(day_gan or "", 0)

    enriched_lines: List[Dict[str, Any]] = []
    for i in range(6):
        branch = branches[i]
        element = _BRANCH_TO_ELEMENT.get(branch, "")
        liuqin = _liuqin_against_palace(palace_element, element) if element else "平"
        # 动爻后的变爻地支 + 之卦六亲 (用本宫五行)
        changed_branch = changed_branches[i] if changed_branches[i] else branch
        changed_element = _BRANCH_TO_ELEMENT.get(changed_branch, "")
        changed_liuqin = (
            _liuqin_against_palace(palace_element, changed_element)
            if changed_element
            else "平"
        )
        position_label = SIX_YAO_NAMES[i]
        position_num = i + 1
        shi_ying = ""
        if position_num == shi_line:
            shi_ying = "世"
        elif position_num == ying_line:
            shi_ying = "应"
        liushen = _LIUSHEN_CYCLE[(offset + i) % 6]
        enriched_lines.append(
            {
                "branch": branch,
                "element": element,
                "liuqin": liuqin,
                "shi_ying": shi_ying,
                "liushen": liushen,
                "position_label": position_label,
                "position": position_num,
                "changed_branch": changed_branch if changed_branch != branch else None,
                "changed_liuqin": changed_liuqin if changed_branch != branch else None,
            }
        )

    hexagram_info = {
        "current_palace": current_info.get("palace"),
        "current_position": current_info.get("position"),
        "current_palace_element": palace_element,
        "shi_line": shi_line,
        "ying_line": ying_line,
        "changed_palace": changed_info.get("palace"),
        "changed_position": changed_info.get("position"),
        "changed_palace_element": changed_info.get("palace_element"),
    }
    return hexagram_info, enriched_lines


def _build_context(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str],
) -> Dict[str, Any]:
    moment = parse_local_datetime(date_text, time_text, timezone_name)
    timezone_value = timezone_name or DEFAULT_BIRTH_TIMEZONE
    pillars = BaZiCalendar.get_four_pillars(moment, timezone_name=timezone_value)
    calendar_context = build_calendar_context(
        moment, timezone_name=timezone_value, pillars=pillars
    )
    lunar = calendar_context.get("lunar_calendar") or {}
    nongli = {
        "birth": calendar_context["solar_datetime"],
        "nongli": lunar.get("display"),
        "yearJieqi": f"{pillars['year'][0]}{pillars['year'][1]}",
        "year": f"{pillars['year'][0]}{pillars['year'][1]}",
        "yearGanZi": f"{pillars['year'][0]}{pillars['year'][1]}",
        "monthGanZi": f"{pillars['month'][0]}{pillars['month'][1]}",
        "dayGanZi": f"{pillars['day'][0]}{pillars['day'][1]}",
        "time": f"{pillars['hour'][0]}{pillars['hour'][1]}",
        "jieqi": calendar_context["current_solar_term"]["name"],
        "jiedelta": calendar_context["solar_term_delta"]["description"],
        "monthInt": lunar.get("month"),
        "dayInt": lunar.get("day"),
        "month": lunar.get("month_cn"),
        "day": lunar.get("day_cn"),
        "leap": lunar.get("is_leap_month"),
    }
    return {
        "moment": moment,
        "timezone_name": timezone_value,
        "pillars": pillars,
        "calendar_context": calendar_context,
        "lunar": lunar,
        "nongli": nongli,
    }


def _normalize_gua_lines(lines: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in lines or []:
        if not isinstance(item, dict):
            continue
        # Keep legacy truthiness semantics here for request compatibility.
        value = 1 if bool(item.get("value")) else 0
        normalized.append(
            {
                "value": value,
                "change": bool(item.get("change")),
                "god": item.get("god"),
                "name": item.get("name"),
            }
        )
    return normalized[:6]


def _clean_code(code: Optional[str]) -> str:
    return "".join(ch for ch in str(code or "") if ch in {"0", "1"})


def _derive_gua_code(lines: List[Dict[str, Any]]) -> str:
    return "".join(str(int(line.get("value", 0))) for line in lines) or "000000"


def _derive_changed_code(lines: List[Dict[str, Any]]) -> str:
    chars: List[str] = []
    for line in lines:
        value = int(line.get("value", 0))
        if line.get("change"):
            value = 1 - value
        chars.append(str(value))
    return "".join(chars) or "000000"


def _lines_from_codes(
    current_code: str, changed_code: Optional[str] = None
) -> List[Dict[str, Any]]:
    current = _clean_code(current_code)
    changed = _clean_code(changed_code or current_code)
    if len(current) != 6 or len(changed) != 6:
        raise ValueError("六爻卦码必须是 6 位 0/1 字符串。")

    normalized: List[Dict[str, Any]] = []
    for index, (current_bit, changed_bit) in enumerate(zip(current, changed)):
        normalized.append(
            {
                "value": int(current_bit),
                "change": current_bit != changed_bit,
                "god": SIX_YAO_GODS[index],
                "name": SIX_YAO_NAMES[index],
            }
        )
    return normalized


def _default_sixyao_lines() -> List[Dict[str, Any]]:
    return [
        {"value": 1, "change": False, "god": "青龙", "name": "初爻"},
        {"value": 0, "change": False, "god": "朱雀", "name": "二爻"},
        {"value": 1, "change": True, "god": "勾陈", "name": "三爻"},
        {"value": 0, "change": False, "god": "腾蛇", "name": "四爻"},
        {"value": 1, "change": False, "god": "白虎", "name": "五爻"},
        {"value": 0, "change": True, "god": "玄武", "name": "上爻"},
    ]


def _hexagram_desc_payload(code: str) -> Dict[str, Any]:
    detail = lookup_hexagram_by_code(code)
    return {
        "code": code,
        "name": detail.get("name"),
        "theme": detail.get("theme"),
        "卦辞": detail.get("judgement"),
        "象曰": detail.get("image"),
        "guidance": detail.get("guidance"),
        "favorable": detail.get("favorable"),
        "caution": detail.get("caution"),
        "summary": detail.get("summary"),
        "raw": detail,
    }


def _build_sixyao_snapshot_text(
    *,
    input_normalized: Dict[str, Any],
    nongli: Dict[str, Any],
    current_payload: Dict[str, Any],
    changed_payload: Dict[str, Any],
    lines: List[Dict[str, Any]],
) -> str:
    line_texts = []
    for index, line in enumerate(lines, start=1):
        yao_type = "阳爻" if int(line.get("value", 0)) == 1 else "阴爻"
        moving = "（动）" if line.get("change") else "（静）"
        extras = []
        if line.get("god"):
            extras.append(f"六神:{line['god']}")
        if line.get("name"):
            extras.append(f"爻名:{line['name']}")
        suffix = f"，{'，'.join(extras)}" if extras else ""
        line_texts.append(f"第{index}爻：{yao_type}{moving}{suffix}")

    judge_lines = []
    if input_normalized.get("question"):
        judge_lines.append(f"问题：{input_normalized['question']}")
    judge_lines.append(
        f"本卦：{current_payload.get('name', input_normalized['gua_code'])}"
    )
    if current_payload.get("卦辞"):
        judge_lines.append(f"卦辞：{current_payload['卦辞']}")
    judge_lines.append(
        f"之卦：{changed_payload.get('name', input_normalized['changed_code'])}"
    )
    if changed_payload.get("卦辞"):
        judge_lines.append(f"之卦卦辞：{changed_payload['卦辞']}")

    return _render_snapshot_text(
        [
            (
                "起盘信息",
                _join_lines(
                    [
                        f"日期：{input_normalized['date']} {input_normalized['time']}",
                        f"时区：{input_normalized['zone']}",
                        f"经纬度：{input_normalized.get('lon') or '无'} {input_normalized.get('lat') or '无'}",
                        f"起卦时间：{nongli.get('birth', '无')}",
                        f"干支：年{nongli.get('yearJieqi', '无')} 月{nongli.get('monthGanZi', '无')} 日{nongli.get('dayGanZi', '无')} 时{nongli.get('time', '无')}",
                    ]
                ),
            ),
            (
                "卦象",
                _join_lines(
                    [
                        f"本卦：{current_payload.get('name', input_normalized['gua_code'])}",
                        f"之卦：{changed_payload.get('name', input_normalized['changed_code'])}",
                    ]
                ),
            ),
            ("六爻与动爻", _join_lines(line_texts) or "暂无爻线数据"),
            ("卦辞与断语", _join_lines(judge_lines) or "无"),
        ]
    )


def build_sixyao_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    question: Optional[str] = None,
    gua_code: Optional[str] = None,
    changed_code: Optional[str] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    context = _build_context(date_text=date, time_text=time, timezone_name=zone)
    normalized_lines = _normalize_gua_lines(lines)
    explicit_lines_provided = bool(normalized_lines)
    if not normalized_lines:
        normalized_lines = _default_sixyao_lines()

    current_code = _clean_code(gua_code) or _derive_gua_code(normalized_lines)
    next_code = _clean_code(changed_code) or _derive_changed_code(normalized_lines)

    if len(current_code) != 6 or len(next_code) != 6:
        raise ValueError("六爻卦码必须是 6 位 0/1 字符串。")

    # When the caller supplied explicit gua_code/changed_code but no lines, the
    # placeholder lines still carry demo-only ``change`` flags (hard-coded on
    # lines 3 and 6). Recompute the canonical line set from the authoritative
    # codes so moving-line detection reflects the real request instead of the
    # default seed.
    if (gua_code or changed_code) and not explicit_lines_provided:
        normalized_lines = _lines_from_codes(current_code, next_code)

    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "question": question,
        "gua_code": current_code,
        "changed_code": next_code,
    }
    current_payload = _hexagram_desc_payload(current_code)
    changed_payload = _hexagram_desc_payload(next_code)
    descriptions = {
        current_code: current_payload,
        next_code: changed_payload,
    }

    # 按起卦日干 + 卦码排纳甲、世应、六亲、六神，并写回每爻。
    day_ganzhi = context.get("nongli", {}).get("dayGanZi") or ""
    day_gan = day_ganzhi[0] if day_ganzhi else None
    hexagram_info, enrichment = _build_sixyao_enrichment(
        current_code=current_code, changed_code=next_code, day_gan=day_gan
    )
    for line_dict, extra in zip(normalized_lines, enrichment):
        # 六神与 SIX_YAO_GODS 的固定位置不同——按日干重算 god。
        line_dict["god"] = extra["liushen"]
        line_dict["name"] = extra["position_label"]
        line_dict["position"] = extra["position"]
        line_dict["branch"] = extra["branch"]
        line_dict["element"] = extra["element"]
        line_dict["liuqin"] = extra["liuqin"]
        line_dict["liushen"] = extra["liushen"]
        line_dict["shi_ying"] = extra["shi_ying"]
        if extra["changed_branch"]:
            line_dict["changed_branch"] = extra["changed_branch"]
            line_dict["changed_liuqin"] = extra["changed_liuqin"]
        elif line_dict.get("change"):
            # 动爻但变后地支与原支相同——标记为伏吟位的提示
            line_dict["changed_branch"] = extra["branch"]
            line_dict["changed_liuqin"] = extra["liuqin"]
            line_dict["is_fuyin_line"] = True

    snapshot_text = _build_sixyao_snapshot_text(
        input_normalized=input_normalized,
        nongli=context["nongli"],
        current_payload=current_payload,
        changed_payload=changed_payload,
        lines=normalized_lines,
    )

    moving_lines = [
        index + 1 for index, line in enumerate(normalized_lines) if line.get("change")
    ]
    moving_indices = [
        i for i, line in enumerate(normalized_lines) if line.get("change")
    ]
    current_branches = [line.get("branch", "") for line in normalized_lines]
    changed_branches = [
        line.get("changed_branch") or line.get("branch", "")
        for line in normalized_lines
    ]
    pattern_info = _detect_sixyao_patterns(
        current_code=current_code,
        changed_code=next_code,
        current_branches=current_branches,
        changed_branches=changed_branches,
        moving_indices=moving_indices,
    )
    return {
        "analysis_type": "六爻 / 易卦",
        "input_normalized": input_normalized,
        "nongli": context["nongli"],
        "current_code": current_code,
        "changed_code": next_code,
        "lines": normalized_lines,
        "moving_lines": moving_lines,
        "hexagram_info": hexagram_info,
        "patterns": pattern_info["patterns"],
        "pattern_flags": {
            "liuchong_base": pattern_info["is_liuchong_base"],
            "liuhe_base": pattern_info["is_liuhe_base"],
            "liuchong_changed": pattern_info["is_liuchong_changed"],
            "liuhe_changed": pattern_info["is_liuhe_changed"],
        },
        "question": question,
        "descriptions": descriptions,
        "current_hexagram": current_payload["raw"],
        "changed_hexagram": changed_payload["raw"],
        "snapshot_text": snapshot_text,
        "summary": f"已生成易卦 / 六爻输出。本卦编码：{current_code}。之卦编码：{next_code}。",
    }
