"""Classical 子平 charting algorithms previously missing from the engine.

These three lookups are the computable core of the advanced 格局 / 调候 books in
the ``八字/`` corpus (崔进祥《子平八字王·子平格局》, 晋文《八字命理内部网授班》, and the
《穷通宝鉴》/《造化元钥》 调候 tables). They are deterministic table lookups — they
emit *structured facts*, never interpretation or teaching prose — so they fit
FateBridge's agentic split: the engine computes, the LLM reads and interprets.

Each function takes the already-computed four pillars and returns plain data,
mirroring :func:`fatebridge.services.bazi._build_shensha_entries`. Nothing here
does I/O, raises on bad data, or formats user-facing explanations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fatebridge.utils.data import (
    BRANCH_HIDDEN_STEMS,
    EARTHLY_BRANCHES,
    get_shishen,
)

PillarMap = Dict[str, Tuple[str, str]]

# --------------------------------------------------------------------------- #
# 十二长生 (Twelve Life Stages)
# --------------------------------------------------------------------------- #
# Day-master energy state at each branch. 阳干顺行、阴干逆行 from the 长生 branch.
# Classical and fully deterministic; quantifies 通根/旺衰 per pillar.

TWELVE_STAGES: Tuple[str, ...] = (
    "长生",
    "沐浴",
    "冠带",
    "临官",
    "帝旺",
    "衰",
    "病",
    "死",
    "墓",
    "绝",
    "胎",
    "养",
)

# day stem -> (长生 branch, direction). +1 = 顺行 (阳干), -1 = 逆行 (阴干).
_CHANGSHENG_START: Dict[str, Tuple[str, int]] = {
    "甲": ("亥", +1),
    "丙": ("寅", +1),
    "戊": ("寅", +1),
    "庚": ("巳", +1),
    "壬": ("申", +1),
    "乙": ("午", -1),
    "丁": ("酉", -1),
    "己": ("酉", -1),
    "辛": ("子", -1),
    "癸": ("卯", -1),
}

# 临官/帝旺 = the day-master's own 禄/刃 seats — the strongest roots.
_STRONG_STAGES = frozenset({"临官", "帝旺", "长生"})


def twelve_life_stage(day_stem: str, branch: str) -> str:
    """Return the 十二长生 stage of ``day_stem`` sitting on ``branch``."""
    start_branch, direction = _CHANGSHENG_START[day_stem]
    start_idx = EARTHLY_BRANCHES.index(start_branch)
    branch_idx = EARTHLY_BRANCHES.index(branch)
    steps = ((branch_idx - start_idx) * direction) % 12
    return TWELVE_STAGES[steps]


def life_stages_for_pillars(pillars: PillarMap) -> Dict[str, Any]:
    """Map the day master's 十二长生 state across all four branches."""
    day_stem = pillars["day"][0]
    labels = {"year": "年支", "month": "月支", "day": "日支", "hour": "时支"}
    per_pillar = {
        labels[key]: twelve_life_stage(day_stem, pillars[key][1])
        for key in ("year", "month", "day", "hour")
    }
    rooted = [pos for pos, stage in per_pillar.items() if stage in _STRONG_STAGES]
    return {
        "day_stem": day_stem,
        "per_pillar": per_pillar,
        "strong_roots": rooted,
    }


# --------------------------------------------------------------------------- #
# 月令取格 (Canonical structure from the month branch)
# --------------------------------------------------------------------------- #
# The foundational 子平 pattern: read the month branch's hidden stems
# (本气/中气/余气), see which is 透出 on the other stems, and the ten-god of the
# chosen stem names the 正格. 禄(比肩)/刃(劫财) are handled as the 建禄/月刃 specials.

_TEN_GOD_TO_STRUCTURE: Dict[str, str] = {
    "正官": "正官格",
    "七杀": "七杀格",
    "正财": "正财格",
    "偏财": "偏财格",
    "正印": "正印格",
    "偏印": "偏印格",
    "食神": "食神格",
    "伤官": "伤官格",
    "比肩": "建禄格",
    "劫财": "月刃格",
}

_HIDDEN_ROLES: Tuple[str, ...] = ("本气", "中气", "余气")


def _select_structure_god(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Pick which month-branch hidden stem defines the 格 (the tunable rule).

    This is the one genuinely school-dependent decision in 取格. The mainstream
    子平 rule used here:

    1. 禄/刃 special case — if 本气 is 比肩(建禄) or 劫财(月刃), the month branch is
       the day master's own 禄/刃 seat; it takes no 用神 from the 格, so 本气 wins
       outright and the result is flagged ``is_special``.
    2. Otherwise prefer a hidden stem that is **透出** on the other stems, by
       role priority 本气 > 中气 > 余气 (透干者优先取格). 比劫 transparent in 中气/
       余气 are skipped — 比劫 only defines a 格 as the 本气 禄/刃 of case 1.
    3. If no eligible 透出 stem, fall back to 本气 (本气为格).

    Adjust the ordering / eligibility here to match a specific lineage's 取格 convention.
    """
    primary = candidates[0]
    if primary["ten_god"] in ("比肩", "劫财"):
        return {**primary, "is_special": True}

    transparent = [
        c
        for c in candidates
        if c["transparent"] and c["ten_god"] not in ("比肩", "劫财")
    ]
    chosen = transparent[0] if transparent else primary
    return {**chosen, "is_special": False}


def determine_monthly_structure(pillars: PillarMap, day_stem: str) -> Dict[str, Any]:
    """Determine the canonical 月令正格 from the month branch.

    Returns the recognised 格 plus the factual derivation basis. Pure data —
    the agent interprets what the structure means.
    """
    month_branch = pillars["month"][1]
    hidden = BRANCH_HIDDEN_STEMS[month_branch]

    # 透干 = a month hidden stem appearing on year/month/hour stems
    # (the day stem itself is 我, never the 格神).
    transparent_stems = {pillars[p][0] for p in ("year", "month", "hour")}

    candidates: List[Dict[str, Any]] = []
    for rank, hidden_stem in enumerate(hidden):
        candidates.append(
            {
                "stem": hidden_stem,
                "ten_god": get_shishen(day_stem, hidden_stem),
                "role": _HIDDEN_ROLES[rank] if rank < len(_HIDDEN_ROLES) else "余气",
                "transparent": hidden_stem in transparent_stems,
            }
        )

    god = _select_structure_god(candidates)
    label = _TEN_GOD_TO_STRUCTURE.get(god["ten_god"], f"{god['ten_god']}格")

    transparency = "透干" if god["transparent"] else "未透（本气取格）"
    if god["is_special"]:
        basis = f"月令{month_branch}为日主{day_stem}之禄刃，本气取{label}。"
    else:
        basis = (
            f"月令{month_branch}藏{god['stem']}（{god['role']}），"
            f"对日主{day_stem}为{god['ten_god']}，{transparency}，取{label}。"
        )

    return {
        "month_branch": month_branch,
        "label": label,
        "structure_god": god,
        "is_special": god["is_special"],
        "hidden_stems": candidates,
        "basis": basis,
    }


# --------------------------------------------------------------------------- #
# 调候用神 (Seasonal adjustment, after 《穷通宝鉴》/《造化元钥》)
# --------------------------------------------------------------------------- #
# month branch -> (primary, [secondary...]) per day stem. This is the widely
# circulated 调候用神简表. It is school-variant at the margins — treat as the
# mainstream baseline and validate against a preferred lineage source if needed.

_DIAOHOU_TABLE: Dict[str, Dict[str, Tuple[str, Tuple[str, ...]]]] = {
    "甲": {
        "寅": ("丙", ("癸",)),
        "卯": ("庚", ("丙", "丁", "戊", "己")),
        "辰": ("庚", ("丁", "壬")),
        "巳": ("癸", ("丁", "庚")),
        "午": ("癸", ("丁", "庚")),
        "未": ("癸", ("丁", "庚")),
        "申": ("庚", ("丁", "壬")),
        "酉": ("庚", ("丁", "丙")),
        "戌": ("庚", ("甲", "丁", "壬", "癸")),
        "亥": ("庚", ("丁", "丙", "戊")),
        "子": ("丁", ("庚", "丙")),
        "丑": ("丁", ("庚", "丙")),
    },
    "乙": {
        "寅": ("丙", ("癸",)),
        "卯": ("丙", ("癸",)),
        "辰": ("癸", ("丙", "戊")),
        "巳": ("癸", ()),
        "午": ("癸", ("丙",)),
        "未": ("癸", ("丙",)),
        "申": ("丙", ("癸", "己")),
        "酉": ("癸", ("丙", "丁")),
        "戌": ("癸", ("辛",)),
        "亥": ("丙", ("戊",)),
        "子": ("丙", ()),
        "丑": ("丙", ()),
    },
    "丙": {
        "寅": ("壬", ("庚",)),
        "卯": ("壬", ("己",)),
        "辰": ("壬", ("甲",)),
        "巳": ("壬", ("庚", "癸")),
        "午": ("壬", ("庚",)),
        "未": ("壬", ("庚",)),
        "申": ("壬", ("戊",)),
        "酉": ("壬", ("癸",)),
        "戌": ("甲", ("壬",)),
        "亥": ("甲", ("戊", "庚", "壬")),
        "子": ("壬", ("戊", "己")),
        "丑": ("壬", ("甲",)),
    },
    "丁": {
        "寅": ("甲", ("庚",)),
        "卯": ("庚", ("甲",)),
        "辰": ("甲", ("庚",)),
        "巳": ("甲", ("庚",)),
        "午": ("壬", ("庚", "癸")),
        "未": ("甲", ("壬", "庚")),
        "申": ("甲", ("庚", "丙", "戊")),
        "酉": ("甲", ("庚", "丙", "戊")),
        "戌": ("甲", ("庚", "戊")),
        "亥": ("甲", ("庚",)),
        "子": ("甲", ("庚",)),
        "丑": ("甲", ("庚",)),
    },
    "戊": {
        "寅": ("丙", ("甲", "癸")),
        "卯": ("丙", ("甲", "癸")),
        "辰": ("甲", ("丙", "癸")),
        "巳": ("甲", ("丙", "癸")),
        "午": ("壬", ("甲", "丙")),
        "未": ("癸", ("丙", "甲")),
        "申": ("丙", ("癸", "甲")),
        "酉": ("丙", ("癸",)),
        "戌": ("甲", ("丙", "癸")),
        "亥": ("甲", ("丙",)),
        "子": ("丙", ("甲",)),
        "丑": ("丙", ("甲",)),
    },
    "己": {
        "寅": ("丙", ("庚", "甲")),
        "卯": ("甲", ("癸", "丙")),
        "辰": ("丙", ("癸", "甲")),
        "巳": ("癸", ("丙",)),
        "午": ("癸", ("丙",)),
        "未": ("癸", ("丙",)),
        "申": ("丙", ("癸",)),
        "酉": ("丙", ("癸",)),
        "戌": ("甲", ("丙", "癸")),
        "亥": ("丙", ("甲", "戊")),
        "子": ("丙", ("甲", "戊")),
        "丑": ("丙", ("甲", "戊")),
    },
    "庚": {
        "寅": ("戊", ("甲", "丙", "丁", "壬")),
        "卯": ("丁", ("甲", "庚", "丙")),
        "辰": ("甲", ("丁", "壬", "癸")),
        "巳": ("壬", ("戊", "丙", "丁")),
        "午": ("壬", ("癸",)),
        "未": ("丁", ("甲",)),
        "申": ("丁", ("甲",)),
        "酉": ("丁", ("甲", "丙")),
        "戌": ("甲", ("壬",)),
        "亥": ("丁", ("丙",)),
        "子": ("丁", ("丙", "甲")),
        "丑": ("丙", ("丁", "甲")),
    },
    "辛": {
        "寅": ("己", ("壬", "庚")),
        "卯": ("壬", ("甲",)),
        "辰": ("壬", ("甲",)),
        "巳": ("壬", ("甲", "癸")),
        "午": ("壬", ("己", "癸")),
        "未": ("壬", ("庚", "甲")),
        "申": ("壬", ("甲", "戊")),
        "酉": ("壬", ("甲",)),
        "戌": ("壬", ("甲",)),
        "亥": ("壬", ("丙",)),
        "子": ("丙", ("戊", "壬", "甲")),
        "丑": ("丙", ("壬", "戊", "己")),
    },
    "壬": {
        "寅": ("庚", ("丙", "戊")),
        "卯": ("戊", ("辛", "庚")),
        "辰": ("甲", ("庚",)),
        "巳": ("壬", ("辛", "庚", "癸")),
        "午": ("癸", ("庚", "辛")),
        "未": ("辛", ("甲",)),
        "申": ("戊", ("丁",)),
        "酉": ("甲", ("庚",)),
        "戌": ("甲", ("丙",)),
        "亥": ("戊", ("庚", "丙")),
        "子": ("戊", ("丙",)),
        "丑": ("丙", ("丁", "甲")),
    },
    "癸": {
        "寅": ("辛", ("丙",)),
        "卯": ("庚", ("辛",)),
        "辰": ("丙", ("辛", "甲")),
        "巳": ("辛", ()),
        "午": ("庚", ("壬", "辛", "癸")),
        "未": ("庚", ("辛", "壬", "癸")),
        "申": ("丁", ()),
        "酉": ("辛", ("丙",)),
        "戌": ("辛", ("甲", "壬", "癸")),
        "亥": ("庚", ("辛", "戊", "丁")),
        "子": ("丙", ("辛",)),
        "丑": ("丙", ("丁",)),
    },
}


def seasonal_climate_god(day_stem: str, month_branch: str) -> Dict[str, Any]:
    """Return the 调候用神 (primary + secondary stems) for ``day_stem`` in ``month_branch``."""
    entry: Optional[Tuple[str, Tuple[str, ...]]] = _DIAOHOU_TABLE.get(day_stem, {}).get(
        month_branch
    )
    if entry is None:
        return {"primary": None, "secondary": [], "available": False}
    primary, secondary = entry
    return {"primary": primary, "secondary": list(secondary), "available": True}


# --------------------------------------------------------------------------- #
# Snapshot adapter
# --------------------------------------------------------------------------- #


def build_classical_overview(pillars: PillarMap) -> Dict[str, Any]:
    """Bundle the three classical facts for the chart payload + snapshot."""
    day_stem = pillars["day"][0]
    month_branch = pillars["month"][1]
    return {
        "monthly_structure": determine_monthly_structure(pillars, day_stem),
        "seasonal_climate": seasonal_climate_god(day_stem, month_branch),
        "life_stages": life_stages_for_pillars(pillars),
    }


def classical_snapshot_lines(overview: Dict[str, Any]) -> List[str]:
    """Render the classical overview into factual snapshot lines."""
    structure = overview["monthly_structure"]
    climate = overview["seasonal_climate"]
    stages = overview["life_stages"]

    lines = [f"月令格局：{structure['label']}（{structure['basis']}）"]

    if climate["available"]:
        secondary = "、".join(climate["secondary"]) if climate["secondary"] else "无"
        lines.append(f"调候用神：主用{climate['primary']}，辅用{secondary}")
    else:
        lines.append("调候用神：暂无对应表项")

    stage_text = " / ".join(
        f"{pos}{stage}" for pos, stage in stages["per_pillar"].items()
    )
    roots = (
        "、".join(stages["strong_roots"]) if stages["strong_roots"] else "无显著强根"
    )
    lines.append(f"日主十二长生：{stage_text}（强根：{roots}）")

    return lines
