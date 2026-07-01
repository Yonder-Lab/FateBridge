"""邵子参评数 / 金锁银匙 (canping) — 原生离线计算。

This is a native Python port of horosa's ``canpingLocal.js`` (邵子参评数 /
金锁银匙). canping is a "原生·非 kentang" technique: unlike qimen/taiyi/jinkou
(computed by a backend and only formatted), canping is computed entirely
in-process. The four pillars come from FateBridge's own calendar engine; this
module does only the 金锁银匙 起数 + 条文查表 — value-aligned with horosa
(itself字逐验证 against the文档算例: 本命 2242/3242, 大运寅 3038/2438,
流年戌 2543/2943).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fatebridge.utils.data import get_nayin

BRANCHES: Tuple[str, ...] = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
)
BRANCH_NUM: Dict[str, int] = {
    branch: index + 1 for index, branch in enumerate(BRANCHES)
}

# 明法（胖胖熊）：月支(月建/八字月支)反向取日宫支。
MONTH_TO_DAY_PALACE: Dict[str, str] = {
    "寅": "亥",
    "卯": "戌",
    "辰": "酉",
    "巳": "申",
    "午": "未",
    "未": "午",
    "申": "巳",
    "酉": "辰",
    "戌": "卯",
    "亥": "寅",
    "子": "丑",
    "丑": "子",
}

# 水火 +27、土 +50、木金 +0。
ELEMENT_ADD: Dict[str, int] = {"水": 27, "火": 27, "土": 50, "木": 0, "金": 0}
# 水1 火2 木3 金4 土5。
ELEMENT_PEI: Dict[str, int] = {"水": 1, "火": 2, "木": 3, "金": 4, "土": 5}

PART_NAMES: Dict[str, str] = {
    "水": "水部",
    "火": "火部",
    "木": "木部",
    "金": "金部",
    "土": "土部",
}

_GANS: Tuple[str, ...] = (
    "甲",
    "乙",
    "丙",
    "丁",
    "戊",
    "己",
    "庚",
    "辛",
    "壬",
    "癸",
)

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "canping" / "canpingTiaowen.json"
)


@lru_cache(maxsize=1)
def _tiaowen() -> Dict[str, Any]:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        data: Dict[str, Any] = json.load(handle)
    return data


def nayin_element(year_gz: str) -> str:
    """年干支 → 纳音五行（金/木/水/火/土）。

    Reuses FateBridge's ``get_nayin`` (verified to match horosa's
    ``NAYIN_ELEMENT`` over all 60 ganzhi) and takes its last char.
    """
    if len(year_gz) < 2:
        return ""
    nayin = get_nayin(year_gz[0], year_gz[1])
    if not nayin or nayin == "未知纳音":
        return ""
    return nayin[-1]


def _branch_from_num(number: int) -> str:
    return BRANCHES[((number - 1) % 12 + 12) % 12]


def _branch_of(ganzhi_or_branch: str) -> str:
    text = ganzhi_or_branch or ""
    if len(text) >= 2 and text[1] in BRANCH_NUM:
        return text[1]
    if len(text) == 1 and text in BRANCH_NUM:
        return text
    return ""


def day_palace(month_branch: str, day_branch: str, method: str = "ming") -> str:
    """日宫支：明法用月支反向，古法直接用八字日支。"""
    if method == "gu":
        return day_branch
    return MONTH_TO_DAY_PALACE.get(month_branch, day_branch)


def ming_gong(day_palace_branch: str, hour_branch: str) -> str:
    """命宫：日宫支配卯时起，逆数至生时。"""
    mao = BRANCH_NUM["卯"]
    dp = BRANCH_NUM[day_palace_branch]
    hb = BRANCH_NUM[hour_branch]
    idx = ((dp - (hb - mao) - 1) % 12 + 12) % 12 + 1
    return _branch_from_num(idx)


def compute_number(day_branch: str, hour_branch: str, element: str) -> Dict[str, int]:
    """金锁银匙起数：顺/逆两数。"""
    dp = BRANCH_NUM[day_branch]
    hb = BRANCH_NUM[hour_branch]
    shun = ((12 + (hb - dp)) % 12) + 1  # 日支顺数至时支
    ni = 14 - shun  # 时日顺冲（逆）
    zi_round = dp + hb  # 时日皆从子上轮
    add = ELEMENT_ADD.get(element, 0)
    pei = ELEMENT_PEI.get(element, 0)
    base = 2000 + zi_round + add + pei
    return {
        "shun": shun,
        "ni": ni,
        "ziRound": zi_round,
        "numShun": base + shun * 100,
        "numNi": base + ni * 100,
    }


def _lookup(element: str, number: int, kind: str) -> str:
    data = _tiaowen()
    part = (data.get("parts") or {}).get(element) or {}
    entry = part.get(str(number))
    if entry:
        return entry.get(kind) or ""
    special = (data.get("special") or {}).get(str(number))
    if special:
        return special.get("text") or ""
    return ""


def _verses(element: str, info: Dict[str, int], kind: str) -> Dict[str, Any]:
    return {
        "numShun": info["numShun"],
        "numNi": info["numNi"],
        "textShun": _lookup(element, info["numShun"], kind),
        "textNi": _lookup(element, info["numNi"], kind),
    }


def _kind_for_gender(gender: str) -> str:
    if gender in {"女", "F", "female", "Female", 0}:
        return "female"
    return "male"


def dayun_sequence(
    day_palace_branch: str,
    hour_branch: str,
    qiyun_age: int = 1,
    count: int = 9,
) -> Tuple[List[Dict[str, Any]], str]:
    """大运序列：命宫顺行 ``count`` 步，每步 10 年。"""
    mg = ming_gong(day_palace_branch, hour_branch)
    start_idx = BRANCH_NUM[mg]
    seq: List[Dict[str, Any]] = []
    for k in range(count):
        branch = _branch_from_num(start_idx + k)
        age_start = qiyun_age + 10 * k
        seq.append(
            {
                "index": k,
                "branch": branch,
                "ageStart": age_start,
                "ageEnd": age_start + 9,
            }
        )
    return seq, mg


def _year_ganzhi(year: int) -> str:
    return _GANS[((year - 4) % 10 + 10) % 10] + BRANCHES[((year - 4) % 12 + 12) % 12]


def calculate(
    *,
    year_gz: str,
    month_branch: str,
    day_branch: str,
    hour_branch: str,
    gender: str = "男",
    method: str = "ming",
    qiyun_age: int = 1,
    liunian_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """本命 + 大运 (+ 可选单点流年) 起数与条文。"""
    element = nayin_element(year_gz)
    dp_branch = day_palace(month_branch, day_branch, method)
    kind_main = _kind_for_gender(gender)

    benming = compute_number(dp_branch, hour_branch, element)
    benming_verses = _verses(element, benming, kind_main)

    seq, mg = dayun_sequence(dp_branch, hour_branch, qiyun_age)
    dayun: List[Dict[str, Any]] = []
    for step in seq:
        info = compute_number(dp_branch, step["branch"], element)
        dayun.append({**step, **info, "verses": _verses(element, info, "luck")})

    liunian: Optional[Dict[str, Any]] = None
    if liunian_branch:
        cur_dayun = dayun[0]["branch"] if dayun else mg
        info = compute_number(_branch_of(liunian_branch), cur_dayun, element)
        liunian = {
            "taisuiBranch": _branch_of(liunian_branch),
            "dayunBranch": cur_dayun,
            **info,
            "verses": _verses(element, info, "luck"),
        }

    return {
        "method": method,
        "gender": gender,
        "element": element,
        "partName": PART_NAMES.get(element, f"{element}部"),
        "fourPillars": {
            "yearGz": year_gz,
            "monthBranch": month_branch,
            "dayBranch": day_branch,
            "hourBranch": hour_branch,
        },
        "dayPalaceBranch": dp_branch,
        "mingGong": mg,
        "kindMain": kind_main,
        "benming": {**benming, "verses": benming_verses},
        "dayun": dayun,
        "liunian": liunian,
        "qiyunAge": qiyun_age,
    }


def liunian_series(
    *,
    year_gz: str,
    month_branch: str,
    day_branch: str,
    hour_branch: str,
    gender: str = "男",
    method: str = "ming",
    qiyun_age: int = 1,
    birth_year: int = 0,
    start_age: int = 1,
    end_age: int = 120,
) -> Dict[str, Any]:
    """全表流年：自 ``start_age`` 至 ``end_age`` 虚岁逐岁起数。

    太岁(当年年支)替日宫支、当时大运支替时支起数；每岁按虚岁定位所属大运。
    """
    result = calculate(
        year_gz=year_gz,
        month_branch=month_branch,
        day_branch=day_branch,
        hour_branch=hour_branch,
        gender=gender,
        method=method,
        qiyun_age=qiyun_age,
    )
    element = result["element"]
    dayun: List[Dict[str, Any]] = result["dayun"]

    def dayun_at(age: int) -> Dict[str, Any]:
        if not dayun:
            return {"branch": result["mingGong"], "ageStart": 1, "ageEnd": 10}
        k = (age - qiyun_age) // 10
        if k < 0:
            k = 0
        if k > len(dayun) - 1:
            k = len(dayun) - 1
        return dayun[k]

    rows: List[Dict[str, Any]] = []
    for age in range(start_age, end_age + 1):
        year = birth_year + age - 1 if birth_year else 0
        taisui = BRANCHES[((year - 4) % 12 + 12) % 12] if year else ""
        dy = dayun_at(age)
        info = compute_number(taisui or day_branch, dy["branch"], element)
        rows.append(
            {
                "age": age,
                "year": year,
                "ganzhi": _year_ganzhi(year) if year else "",
                "taisuiBranch": taisui,
                "dayunBranch": dy["branch"],
                "dayunRange": f"{dy['ageStart']}-{dy['ageEnd']}",
                **info,
                "verses": _verses(element, info, "luck"),
            }
        )
    return {
        "element": element,
        "partName": result["partName"],
        "dayun": dayun,
        "rows": rows,
        "qiyunAge": qiyun_age,
    }


def build_snapshot_text(result: Dict[str, Any]) -> str:
    """渲染 [起盘]/[本命]/[大运·歲運]/[流年·歲運] 四段中文快照。"""
    if not result:
        return ""
    lines: List[str] = []
    benming = result.get("benming") or {}
    verses = benming.get("verses") or {}
    method_label = "古法(八字日支)" if result["method"] == "gu" else "明法(月支反向)"

    lines.append("[起盘]")
    lines.append(
        f"年纳音：{result['element']}（{result['partName']}）  取法：{method_label}"
    )
    lines.append(f"日宫支：{result['dayPalaceBranch']}  命宫：{result['mingGong']}")
    lines.append("")
    lines.append("[本命]")
    lines.append(f"顺 {verses.get('numShun')}：{verses.get('textShun')}")
    lines.append(f"逆 {verses.get('numNi')}：{verses.get('textNi')}")
    lines.append("")
    lines.append("[大运·歲運]")
    for step in result.get("dayun") or []:
        step_verses = step.get("verses") or {}
        lines.append(
            f"{step['ageStart']}-{step['ageEnd']}岁 {step['branch']}："
            f"顺{step_verses.get('numShun')} {step_verses.get('textShun')} ／ "
            f"逆{step_verses.get('numNi')} {step_verses.get('textNi')}"
        )
    liunian = result.get("liunian")
    if liunian:
        lv = liunian.get("verses") or {}
        lines.append("")
        lines.append("[流年·歲運]")
        lines.append(
            f"太岁{liunian['taisuiBranch']}/大运{liunian['dayunBranch']}："
            f"顺{lv.get('numShun')} {lv.get('textShun')} ／ "
            f"逆{lv.get('numNi')} {lv.get('textNi')}"
        )
    return "\n".join(lines)
