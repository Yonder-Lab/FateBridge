"""地支刑冲克害 / 合化 对五行计数的调整（计分层）。

``ElementAnalysis.count_elements`` 给出的是**静态结构计数**（天干 1 / 本气 1 /
藏干 0.5、四柱等权），它不反映地支之间的刑、冲、克、害与合、会、合化。本模块在
该静态计数之上，依据四柱地支的相互关系做一层增减，得到“关系调整后”的五行计数。

设计要点（规则方案 v0，已与命主确认）：

* **只作用于本命四柱**，不混入大运 / 流年（后者归 timing 模块）。
* 调整作用在每支的**本气**（即静态计数里那 +1 的主气）上；天干 +1 与藏干 +0.5
  作为底分保持不变。
* **合化（增益）优先于刑冲处理**；合处逢冲则冲开（冲解合，合局不成）。
* “化成”判定：化神五行**透干**（四天干见之）**或**当令（与月支本气同类）。
  否则六合只“合绊”（双方略降、不转化），三合只成局加少分而不转化。

本模块不改动 ``count_elements`` 本身，调用方以新增字段承载结果，零破坏现有契约。
"""

import itertools
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Tuple

from ..utils.data import (
    BRANCH_COMBINATION_ELEMENT,
    BRANCH_COMBINATIONS,
    BRANCH_CONFLICTS,
    BRANCH_ELEMENTS,
    BRANCH_HARMS,
    BRANCH_SEASONAL_COMBINATIONS,
    BRANCH_SELF_PUNISHMENTS,
    BRANCH_THREE_PUNISHMENTS,
    BRANCH_TRIPLE_COMBINATIONS,
    BUREAU_ELEMENT,
    DESTRUCTION_CYCLE,
    STEM_ELEMENTS,
    TRIPLE_COMBINATION_PEAK,
    Element,
)

# --- 计分参数 -------------------------------------------------------------
# 减损（作用于本气乘子）
CLASH_MAIN_MULT = 0.7  # 六冲：双方本气
CLASH_LOSER_EXTRA_MULT = 0.85  # 六冲中受克一方额外
PUNISH_MAIN_MULT = 0.85  # 三刑 / 自刑：相关支本气
HARM_MAIN_MULT = 0.95  # 六害：双方本气（轻）

# 增益（合 / 会）
SEASONAL_MEMBER_MULT = 0.5  # 三会方：三支本气
SEASONAL_BONUS = 2.0  # 三会方：会神元素

TRIPLE_MEMBER_MULT = 0.6  # 三合化成：三支本气
TRIPLE_BONUS_TRANSFORMED = 1.5  # 三合化成：局神元素
TRIPLE_BONUS_UNTRANSFORMED = 0.8  # 三合不化：局神元素

HALF_BONUS = 0.7  # 半合：局神元素

SIXCOMB_MEMBER_MULT_TRANSFORMED = 0.5  # 六合化成：双方本气
SIXCOMB_BONUS = 1.0  # 六合化成：化神元素
SIXCOMB_MEMBER_MULT_BOUND = 0.8  # 六合合绊：双方本气


def _is_transformed(target: Element, stems: List[str], month_element: Element) -> bool:
    """化成判定：化神透干（四天干见之）或当令（与月支本气同类）。"""
    revealed_in_stems = any(STEM_ELEMENTS[s][0] == target for s in stems)
    in_command = month_element == target
    return revealed_in_stems or in_command


def _pairs(items: Any) -> List[frozenset]:
    return [frozenset(p) for p in itertools.combinations(items, 2)]


def adjust_element_counts(
    base_counts: Dict[Element, float],
    pillars: Dict[str, Tuple[str, str]],
) -> Tuple[Dict[Element, float], List[Dict[str, Any]]]:
    """在静态五行计数上叠加刑冲克害 / 合化调整。

    Args:
        base_counts: ``ElementAnalysis.count_elements`` 的原始计数。
        pillars: ``{position: (stem, branch)}``，含 ``"month"`` 键以判当令。

    Returns:
        ``(adjusted_counts, relations)``：调整后的五行计数（>= 0），以及命中的
        关系明细列表（含类型、涉及地支、效果说明），供溯源与解读。
    """
    positions = list(pillars.keys())
    branch_of = {p: pillars[p][1] for p in positions}
    present = set(branch_of.values())
    positions_of_branch: DefaultDict[str, List[str]] = defaultdict(list)
    for position, branch in branch_of.items():
        positions_of_branch[branch].append(position)

    stems = [pillars[p][0] for p in positions]
    month_branch = pillars["month"][1]
    month_element = BRANCH_ELEMENTS[month_branch][0]

    main_mult: Dict[str, float] = {p: 1.0 for p in positions}
    delta: DefaultDict[Element, float] = defaultdict(float)
    relations: List[Dict[str, Any]] = []
    clashed: set = set()
    consumed_pairs: set = set()

    def _scale(branch: str, factor: float) -> None:
        for position in positions_of_branch[branch]:
            main_mult[position] *= factor

    # --- A. 六冲（先行，决定后续合局是否被冲解）-----------------------
    seen: set = set()
    for branch in sorted(present):
        opp = BRANCH_CONFLICTS.get(branch)
        if not opp or opp not in present:
            continue
        pair = frozenset({branch, opp})
        if pair in seen:
            continue
        seen.add(pair)
        clashed.update({branch, opp})
        for member in (branch, opp):
            _scale(member, CLASH_MAIN_MULT)
        e1, e2 = BRANCH_ELEMENTS[branch][0], BRANCH_ELEMENTS[opp][0]
        loser = None
        if DESTRUCTION_CYCLE.get(e2) == e1:
            loser = branch
        elif DESTRUCTION_CYCLE.get(e1) == e2:
            loser = opp
        if loser is not None:
            _scale(loser, CLASH_LOSER_EXTRA_MULT)
        note = "".join(sorted(pair)) + "冲"
        if loser is not None:
            note += f"，{loser}受克更损"
        relations.append({"type": "六冲", "branches": sorted(pair), "note": note})

    # --- B. 合 / 会（化神 → 增益；逢冲则冲解）--------------------------
    # B1. 三会方（最强）
    for key, bureau in BRANCH_SEASONAL_COMBINATIONS.items():
        trio = set(key)
        if not trio <= present:
            continue
        if trio & clashed:
            relations.append(
                {
                    "type": "三会(被冲解)",
                    "branches": sorted(trio),
                    "note": "逢冲，会局不成",
                }
            )
            consumed_pairs.update(_pairs(trio))
            continue
        element = BUREAU_ELEMENT[bureau]
        for member in trio:
            _scale(member, SEASONAL_MEMBER_MULT)
        delta[element] += SEASONAL_BONUS
        consumed_pairs.update(_pairs(trio))
        relations.append(
            {
                "type": f"三会{bureau}",
                "branches": sorted(trio),
                "effect": f"{element.value} +{SEASONAL_BONUS}",
            }
        )

    # B2. 三合局（全）
    for key, bureau in BRANCH_TRIPLE_COMBINATIONS.items():
        trio = set(key)
        if not trio <= present:
            continue
        consumed_pairs.update(_pairs(trio))
        if trio & clashed:
            relations.append(
                {
                    "type": "三合(被冲解)",
                    "branches": sorted(trio),
                    "note": "逢冲，合局不成",
                }
            )
            continue
        element = BUREAU_ELEMENT[bureau]
        transformed = _is_transformed(element, stems, month_element)
        if transformed:
            for member in trio:
                _scale(member, TRIPLE_MEMBER_MULT)
            delta[element] += TRIPLE_BONUS_TRANSFORMED
        else:
            delta[element] += TRIPLE_BONUS_UNTRANSFORMED
        bonus = TRIPLE_BONUS_TRANSFORMED if transformed else TRIPLE_BONUS_UNTRANSFORMED
        relations.append(
            {
                "type": f"三合{bureau}{'(化成)' if transformed else '(不化)'}",
                "branches": sorted(trio),
                "effect": f"{element.value} +{bonus}",
            }
        )

    # B3. 半合（须含旺神：旺+生 或 旺+库；未被三合 / 三会消费）
    for key, bureau in BRANCH_TRIPLE_COMBINATIONS.items():
        peak = TRIPLE_COMBINATION_PEAK[key]
        if peak not in present:
            continue
        for other in (b for b in key if b != peak):
            pair = frozenset({peak, other})
            if pair in consumed_pairs or other not in present:
                continue
            consumed_pairs.add(pair)
            if pair & clashed:
                relations.append(
                    {
                        "type": "半合(被冲解)",
                        "branches": sorted(pair),
                        "note": "逢冲，半合不成",
                    }
                )
                continue
            element = BUREAU_ELEMENT[bureau]
            delta[element] += HALF_BONUS
            relations.append(
                {
                    "type": f"半合{bureau}",
                    "branches": sorted(pair),
                    "effect": f"{element.value} +{HALF_BONUS}",
                }
            )

    # B4. 六合（化成 / 合绊；未被上面消费）
    seen = set()
    for branch in sorted(present):
        partner = BRANCH_COMBINATIONS.get(branch)
        if not partner or partner not in present:
            continue
        pair = frozenset({branch, partner})
        if pair in seen or pair in consumed_pairs:
            continue
        seen.add(pair)
        if pair & clashed:
            relations.append(
                {
                    "type": "六合(被冲解)",
                    "branches": sorted(pair),
                    "note": "逢冲，合而不合",
                }
            )
            continue
        element = BRANCH_COMBINATION_ELEMENT[pair]
        if _is_transformed(element, stems, month_element):
            for member in pair:
                _scale(member, SIXCOMB_MEMBER_MULT_TRANSFORMED)
            delta[element] += SIXCOMB_BONUS
            relations.append(
                {
                    "type": f"六合化{element.value}(化成)",
                    "branches": sorted(pair),
                    "effect": f"{element.value} +{SIXCOMB_BONUS}",
                }
            )
        else:
            for member in pair:
                _scale(member, SIXCOMB_MEMBER_MULT_BOUND)
            relations.append(
                {
                    "type": f"六合{element.value}(合绊)",
                    "branches": sorted(pair),
                    "note": "合而不化，双方略降",
                }
            )

    # --- C. 三刑 / 自刑（组内出现 >= 2 支即论；同支重见为自刑）----------
    for group in BRANCH_THREE_PUNISHMENTS:
        members = [b for b in group if b in present]
        if len(members) < 2:
            continue
        for member in members:
            _scale(member, PUNISH_MAIN_MULT)
        full = len(members) == len(group) >= 3
        relations.append(
            {
                "type": "三刑" if full else "相刑",
                "branches": sorted(members),
                "note": "".join(members) + ("三刑" if full else "刑"),
            }
        )
    for branch in BRANCH_SELF_PUNISHMENTS:
        if len(positions_of_branch[branch]) >= 2:
            _scale(branch, PUNISH_MAIN_MULT)
            relations.append(
                {"type": "自刑", "branches": [branch], "note": f"{branch}{branch}自刑"}
            )

    # --- D. 六害（轻减）-----------------------------------------------
    seen = set()
    for branch in sorted(present):
        partner = BRANCH_HARMS.get(branch)
        if not partner or partner not in present:
            continue
        pair = frozenset({branch, partner})
        if pair in seen:
            continue
        seen.add(pair)
        for member in pair:
            _scale(member, HARM_MAIN_MULT)
        relations.append(
            {
                "type": "六害",
                "branches": sorted(pair),
                "note": "".join(sorted(pair)) + "害",
            }
        )

    # --- 汇总：本气乘子作用于底分，叠加合化增益，钳制 >= 0 --------------
    adjusted: Dict[Element, float] = dict(base_counts)
    for position in positions:
        main_element = BRANCH_ELEMENTS[branch_of[position]][0]
        adjusted[main_element] = adjusted.get(main_element, 0.0) + (
            main_mult[position] - 1.0
        )
    for element, value in delta.items():
        adjusted[element] = adjusted.get(element, 0.0) + value
    for element in list(adjusted):
        adjusted[element] = round(max(0.0, adjusted[element]), 4)

    return adjusted, relations
