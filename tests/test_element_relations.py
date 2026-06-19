"""锁定地支刑冲克害 / 合化对五行计数的调整（element_relations 计分层）。

静态计数（天干 1 / 本气 1 / 藏干 0.5）不反映地支关系。本测试覆盖：
六冲（含受克方加损）、三会、三合（化成 / 不化）、半合、六合（化成 / 合绊）、
三刑 / 自刑、六害，以及"合处逢冲则冲开"的优先级，并锁定命主样例命盘。
"""

from fatebridge.core.element_relations import (
    HALF_BONUS,
    SEASONAL_BONUS,
    SIXCOMB_BONUS,
    TRIPLE_BONUS_TRANSFORMED,
    TRIPLE_BONUS_UNTRANSFORMED,
    adjust_element_counts,
)
from fatebridge.core.elements import ElementAnalysis
from fatebridge.utils.data import Element


def _run(pillars):
    base = ElementAnalysis.count_elements(pillars)
    adjusted, relations = adjust_element_counts(base, pillars)
    types = [r["type"] for r in relations]
    return base, adjusted, relations, types


def test_inert_chart_leaves_counts_unchanged():
    # 寅 / 子 / 酉 两两无合冲刑害会
    pillars = {"year": ("甲", "寅"), "month": ("壬", "子"), "day": ("辛", "酉")}
    base, adjusted, relations, _ = _run(pillars)
    assert relations == []
    assert adjusted == {e: round(v, 4) for e, v in base.items()}


def test_half_combination_adds_bonus_to_bureau_element():
    # 子辰半合水局（子为旺神，辰为库）
    pillars = {"month": ("甲", "子"), "day": ("甲", "辰")}
    base, adjusted, _, types = _run(pillars)
    assert "半合水局" in types
    assert adjusted[Element.WATER] == round(base[Element.WATER] + HALF_BONUS, 4)


def test_full_triple_transformed_when_god_in_command():
    # 申子辰三合水局，月支子（水当令）→ 化成
    pillars = {
        "year": ("甲", "申"),
        "month": ("甲", "子"),
        "day": ("甲", "辰"),
        "hour": ("甲", "申"),
    }
    base, adjusted, _, types = _run(pillars)
    assert "三合水局(化成)" in types
    # 化成：局神得 +1.5，三支本气各 ×0.6
    assert adjusted[Element.WATER] > base[Element.WATER]


def test_full_triple_untransformed_without_god():
    # 申子辰俱全但月支辰（土当令）、四干无水 → 不化，仅 +0.8、本气不降
    pillars = {
        "year": ("丙", "申"),
        "month": ("丙", "辰"),
        "day": ("丙", "子"),
        "hour": ("丙", "申"),
    }
    base, adjusted, _, types = _run(pillars)
    assert "三合水局(不化)" in types
    assert adjusted[Element.WATER] == round(
        base[Element.WATER] + TRIPLE_BONUS_UNTRANSFORMED, 4
    )
    assert TRIPLE_BONUS_TRANSFORMED != TRIPLE_BONUS_UNTRANSFORMED  # 区分两档


def test_six_combination_transformed_vs_bound():
    # 寅亥合木：木透干（甲）→ 化成，化神 +1.0
    transformed = {"year": ("甲", "寅"), "month": ("乙", "亥"), "day": ("乙", "酉")}
    base_t, adj_t, _, types_t = _run(transformed)
    assert any("化成" in t for t in types_t)
    # 木净效应：寅本气木 ×0.5（-0.5）+ 化神 +1.0 = +0.5（亥本气为水，不计木）
    assert adj_t[Element.WOOD] == round(base_t[Element.WOOD] - 0.5 + SIXCOMB_BONUS, 4)

    # 寅亥合木：四干无木、亥月非木令 → 合绊（不转化、双方略降）
    bound = {"year": ("戊", "寅"), "month": ("庚", "亥"), "day": ("庚", "酉")}
    _, _, _, types_b = _run(bound)
    assert any("合绊" in t for t in types_b)
    assert not any("化成" in t for t in types_b)


def test_seasonal_meeting_is_strongest():
    # 亥子丑三会水方
    pillars = {
        "year": ("甲", "亥"),
        "month": ("甲", "子"),
        "day": ("甲", "丑"),
        "hour": ("甲", "亥"),
    }
    base, adjusted, _, types = _run(pillars)
    assert "三会水局" in types
    assert adjusted[Element.WATER] > base[Element.WATER]


def test_clash_loser_takes_extra_penalty():
    # 子午冲：水克火，午为受克方
    pillars = {"month": ("甲", "子"), "day": ("甲", "午")}
    base, adjusted, relations, types = _run(pillars)
    assert "六冲" in types
    note = next(r for r in relations if r["type"] == "六冲")["note"]
    assert "午受克更损" in note
    assert adjusted[Element.FIRE] < base[Element.FIRE]
    assert adjusted[Element.WATER] < base[Element.WATER]


def test_clash_without_destruction_has_no_loser():
    # 辰戌冲：双土，无克 → 不标受克方
    pillars = {"month": ("甲", "辰"), "day": ("甲", "戌")}
    _, _, relations, types = _run(pillars)
    assert "六冲" in types
    note = next(r for r in relations if r["type"] == "六冲")["note"]
    assert "受克" not in note


def test_clash_breaks_combination():
    # 子辰半合 + 子午冲 → 子被冲，半合不成
    pillars = {"year": ("甲", "辰"), "month": ("甲", "子"), "day": ("甲", "午")}
    _, _, _, types = _run(pillars)
    assert "六冲" in types
    assert "半合(被冲解)" in types
    assert "半合水局" not in types


def test_mutual_punishment_and_self_punishment():
    # 子卯相刑（无礼之刑）
    _, _, _, types = _run({"month": ("甲", "子"), "day": ("甲", "卯")})
    assert "相刑" in types
    # 辰辰自刑
    _, _, _, types_self = _run({"month": ("甲", "辰"), "day": ("甲", "辰")})
    assert "自刑" in types_self


def test_six_harm_penalty():
    # 卯辰害（不与刑冲重叠）
    pillars = {"month": ("甲", "卯"), "day": ("甲", "辰")}
    base, adjusted, _, types = _run(pillars)
    assert "六害" in types
    assert adjusted[Element.WOOD] <= base[Element.WOOD]
    assert adjusted[Element.EARTH] <= base[Element.EARTH]


def test_counts_never_negative():
    for pillars in (
        {"year": ("甲", "辰"), "month": ("甲", "子"), "day": ("甲", "午")},
        {"month": ("甲", "卯"), "day": ("甲", "辰")},
        {"year": ("丙", "申"), "month": ("丙", "辰"), "day": ("丙", "子")},
    ):
        _, adjusted, _, _ = _run(pillars)
        assert all(v >= 0.0 for v in adjusted.values())


def test_subject_chart_water_up_fire_down():
    """命主 庚辰 / 戊子 / 壬寅 / 乙巳：子辰半合水、寅巳刑、寅巳害。"""
    pillars = {
        "year": ("庚", "辰"),
        "month": ("戊", "子"),
        "day": ("壬", "寅"),
        "hour": ("乙", "巳"),
    }
    base, adjusted, _, types = _run(pillars)
    assert "半合水局" in types
    assert "相刑" in types
    assert "六害" in types
    assert adjusted[Element.WATER] > base[Element.WATER]  # 半合水
    assert adjusted[Element.FIRE] < base[Element.FIRE]  # 巳被刑+害


def test_analyze_day_master_exposes_adjusted_fields():
    pillars = {
        "year": ("庚", "辰"),
        "month": ("戊", "子"),
        "day": ("壬", "寅"),
        "hour": ("乙", "巳"),
    }
    result = ElementAnalysis.analyze_day_master_strength(pillars)
    assert "element_distribution_adjusted" in result
    assert "element_distribution_adjusted_raw" in result
    assert "element_relations" in result
    assert abs(sum(result["element_distribution_adjusted"].values()) - 100.0) <= 0.1
