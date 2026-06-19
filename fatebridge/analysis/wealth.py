"""
财运分析模块

基于八字命理的财运分析功能，综合以下经典技法：
- 子平正格：身财两停、财多身弱、身旺财旺等财富格局判断
- 墓库财法：辰戌丑未财库、冲库发财（参《八字中墓库对发财和破财》系列）
- 盲派求财技法：正财偏财辨财源、食伤生财、比劫夺财
- 德盛《八字中财富格局祸福的五大核心法门》《八字中看是否有钱和财富高低四大命脉》

核心分析维度：
1. 财星定位（正财/偏财所在与强弱）
2. 财富格局评估（身财平衡、富贵层次）
3. 墓库财分析（财库与冲开时机）
4. 求财方式与方位（正业/投资、喜用神方位）
5. 破财风险（比劫夺财、财星受冲）
6. 财运时机（大运/流年发财与破财信号）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils.data import (
    BRANCH_ELEMENTS,
    BRANCH_HIDDEN_STEMS,
    DESTRUCTION_CYCLE,
    STEM_ELEMENTS,
    Element,
    TenGod,
    check_branch_conflict,
    count_element_distribution,
    get_ten_god,
    iter_pillar_gods,
)

# 财库：辰戌丑未对应所藏之财（墓库）
# 每个土支为某一五行的墓库
STORAGE_BRANCHES = {
    "辰": Element.WATER,  # 水库
    "戌": Element.FIRE,  # 火库
    "丑": Element.METAL,  # 金库
    "未": Element.WOOD,  # 木库
}

# 正财/偏财求财方式说明
WEALTH_STAR_STYLE = {
    TenGod.POSITIVE_WEALTH: {
        "label": "正财",
        "source": "正业、固定收入、薪资、稳健经营",
        "traits": "踏实积累、量入为出、财来有道",
    },
    TenGod.PARTIAL_WEALTH: {
        "label": "偏财",
        "source": "投资、投机、副业、经商、意外之财",
        "traits": "眼光独到、敢于把握机会、财来财去波动大",
    },
}

# 五行求财方位
ELEMENT_DIRECTION = {
    Element.WOOD: "东方",
    Element.FIRE: "南方",
    Element.EARTH: "中央/本地",
    Element.METAL: "西方",
    Element.WATER: "北方",
}


class WealthAnalysis:
    """财运分析工具类"""

    @staticmethod
    def analyze_wealth(
        pillars: Dict[str, Tuple[str, str]],
        gender: Optional[str] = None,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        综合财运分析。

        Args:
            pillars: 四柱 {"year"/"month"/"day"/"hour": (stem, branch)}
            gender: 性别（财运分析中影响较小，保留以统一接口）
            dayun_pillar: 当前大运柱 (可选)
            liunian_pillar: 当前流年柱 (可选)

        Returns:
            财运分析结果字典
        """
        day_stem = pillars["day"][0]
        day_element = STEM_ELEMENTS[day_stem][0]
        wealth_element = DESTRUCTION_CYCLE[day_element]  # 日主所克即为财

        wealth_stars = WealthAnalysis._locate_wealth_stars(pillars, day_stem)
        structure = WealthAnalysis._analyze_wealth_structure(
            pillars, day_stem, wealth_element
        )
        storage = WealthAnalysis._analyze_wealth_storage(pillars, wealth_element)
        style = WealthAnalysis._analyze_wealth_style(wealth_stars)
        direction = WealthAnalysis._analyze_wealth_direction(wealth_element)
        risk = WealthAnalysis._analyze_wealth_risk(pillars, day_stem, wealth_element)
        timing = WealthAnalysis._analyze_wealth_timing(
            day_stem, wealth_element, dayun_pillar, liunian_pillar
        )
        suggestions = WealthAnalysis._generate_suggestions(structure, style, risk)

        return {
            "wealth_element": wealth_element.value,
            "wealth_stars": wealth_stars,
            "wealth_structure": structure,
            "wealth_storage": storage,
            "wealth_style": style,
            "wealth_direction": direction,
            "wealth_risk": risk,
            "wealth_timing": timing,
            "suggestions": suggestions,
        }

    @staticmethod
    def _locate_wealth_stars(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
    ) -> Dict[str, Any]:
        """定位命局中的正财、偏财（含地支藏干）。"""
        positions: List[Dict[str, Any]] = []
        zheng_count = 0.0
        pian_count = 0.0

        for e in iter_pillar_gods(pillars, day_stem):
            if e.ten_god not in (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH):
                continue
            positions.append(
                {
                    "pillar": e.pillar,
                    "location": e.location,
                    "char": e.char,
                    "ten_god": e.ten_god.value,
                }
            )
            if e.ten_god == TenGod.POSITIVE_WEALTH:
                zheng_count += e.weight
            else:
                pian_count += e.weight

        total = round(zheng_count + pian_count, 1)
        if total == 0:
            visibility = "命局无明财，财星藏而不露或须从大运流年引动"
        elif zheng_count >= pian_count:
            visibility = "以正财为主，财源稳定正当"
        else:
            visibility = "以偏财为主，财源灵活、利于投资经商"

        return {
            "positions": positions,
            "zheng_wealth_weight": round(zheng_count, 1),
            "pian_wealth_weight": round(pian_count, 1),
            "total_weight": total,
            "visibility": visibility,
        }

    @staticmethod
    def _analyze_wealth_structure(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
        wealth_element: Element,
    ) -> Dict[str, Any]:
        """评估财富格局：身财平衡决定守财与得财能力。"""
        from ..core.elements import ElementAnalysis

        dm_analysis = ElementAnalysis.analyze_day_master_strength(pillars)
        strength = dm_analysis["strength_level"]

        # 统计财星五行力量
        element_counts = count_element_distribution(pillars)
        wealth_strength = round(element_counts[wealth_element], 1)

        score = 60
        notes: List[str] = []
        pattern = ""

        has_wealth = wealth_strength >= 1.5

        if strength == "强" and has_wealth:
            score += 18
            pattern = "身旺财旺"
            notes.append("身旺能任财，财星亦旺，财富层次高，得财守财俱佳")
        elif strength == "中和" and has_wealth:
            score += 12
            pattern = "身财两停"
            notes.append("身财平衡，得财顺遂，理财有度，富格之象")
        elif strength == "弱" and wealth_strength >= 2.5:
            score -= 12
            pattern = "财多身弱"
            notes.append("财多身弱，富屋贫人，见财而难守，宜先扶身（比劫、印星）再求财")
        elif strength == "强" and not has_wealth:
            score -= 5
            pattern = "身旺财轻"
            notes.append("身旺财轻，须行食伤运通关生财，或靠才华技术致富")
        else:
            pattern = "财星平常"
            notes.append("财星力量一般，财运平稳，宜稳健积累")

        # 食伤生财：财源活水
        has_food_hurt = False
        for p_name, (stem, branch) in pillars.items():
            if p_name == "day":
                continue
            if get_ten_god(day_stem, stem) in (TenGod.FOOD_GOD, TenGod.HURT_OFFICER):
                has_food_hurt = True
        if has_food_hurt and has_wealth:
            score += 8
            notes.append("食伤生财，财源有根，越做越旺，利于经营与才华变现")

        score = max(30, min(95, score))
        if score >= 82:
            level = "财富层次高"
        elif score >= 68:
            level = "财运良好"
        elif score >= 55:
            level = "财运平稳"
        else:
            level = "求财较辛苦，重在守成"

        return {
            "day_master_strength": strength,
            "wealth_strength": wealth_strength,
            "pattern": pattern,
            "score": score,
            "level": level,
            "notes": notes,
        }

    @staticmethod
    def _analyze_wealth_storage(
        pillars: Dict[str, Tuple[str, str]],
        wealth_element: Element,
    ) -> Dict[str, Any]:
        """墓库财分析：财库见冲方能开库进财。"""
        storage_hits: List[Dict[str, Any]] = []
        branches = [branch for _, branch in pillars.values()]

        for p_name, (_, branch) in pillars.items():
            stored = STORAGE_BRANCHES.get(branch)
            if stored == wealth_element:
                # 检查是否被其他地支冲开
                opened = any(
                    other != branch and check_branch_conflict(branch, other)
                    for other in branches
                )
                storage_hits.append(
                    {
                        "pillar": p_name,
                        "branch": branch,
                        "stores": f"{wealth_element.value}（财库）",
                        "opened": opened,
                        "note": (
                            "财库逢冲，开库进财，主大财或不动产"
                            if opened
                            else "财库未冲，财气封藏，逢冲库之运流年易得大财"
                        ),
                    }
                )

        if storage_hits:
            summary = "命带财库，财富有积聚之象，关键看冲开时机"
        else:
            summary = "命无财库，财以流通见用，不主大额积聚"

        return {
            "has_storage": bool(storage_hits),
            "storage_hits": storage_hits,
            "summary": summary,
        }

    @staticmethod
    def _analyze_wealth_style(wealth_stars: Dict[str, Any]) -> Dict[str, Any]:
        """根据正偏财比重判断求财方式。"""
        zheng = wealth_stars["zheng_wealth_weight"]
        pian = wealth_stars["pian_wealth_weight"]

        recommendations: List[str] = []
        if zheng > 0:
            info = WEALTH_STAR_STYLE[TenGod.POSITIVE_WEALTH]
            recommendations.append(f"正财：{info['source']}（{info['traits']}）")
        if pian > 0:
            info = WEALTH_STAR_STYLE[TenGod.PARTIAL_WEALTH]
            recommendations.append(f"偏财：{info['source']}（{info['traits']}）")
        if not recommendations:
            recommendations.append("命局财星不显，宜靠印绶（专业、技能）或官贵间接得财")

        if pian > zheng:
            primary = "偏财为主，适合投资、经商、副业拓展"
        elif zheng > pian:
            primary = "正财为主，适合稳定职业、固定收入与稳健理财"
        else:
            primary = "正偏财均衡，可正业为本、兼以投资增益"

        return {
            "primary_style": primary,
            "recommendations": recommendations,
        }

    @staticmethod
    def _analyze_wealth_direction(wealth_element: Element) -> Dict[str, Any]:
        """求财方位（以财星五行所主方位为参考）。"""
        return {
            "wealth_element": wealth_element.value,
            "direction": ELEMENT_DIRECTION.get(wealth_element, "本地"),
            "note": f"财星五行为{wealth_element.value}，求财、置业可参考{ELEMENT_DIRECTION.get(wealth_element, '本地')}",
        }

    @staticmethod
    def _analyze_wealth_risk(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
        wealth_element: Element,
    ) -> Dict[str, Any]:
        """破财风险：比劫夺财、财星受冲。"""
        risks: List[str] = []

        # 比劫数量
        bijie = sum(
            e.weight
            for e in iter_pillar_gods(pillars, day_stem)
            if e.ten_god in (TenGod.COMPARE, TenGod.ROB_WEALTH)
        )

        if bijie >= 2.5:
            risks.append("比劫旺而夺财，易因合伙、借贷、兄弟朋友耗财，忌合伙与担保")
        elif bijie >= 1.5:
            risks.append("比劫稍重，理财需防被借被分，宜账目清晰")

        # 财星受冲
        branches = [branch for _, branch in pillars.values()]
        for p_name, (_, branch) in pillars.items():
            b_elem = BRANCH_ELEMENTS[branch][0]
            if b_elem == wealth_element:
                if any(
                    o != branch and check_branch_conflict(branch, o) for o in branches
                ):
                    risks.append(
                        f"{p_name}支财星受冲，财来财去、收入不稳，宜留现金储备"
                    )
                    break

        if not risks:
            risks.append("命局无明显破财结构，财务相对安稳")

        return {
            "bijie_weight": round(bijie, 1),
            "risks": risks,
        }

    @staticmethod
    def _analyze_wealth_timing(
        day_stem: str,
        wealth_element: Element,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """大运/流年财运信号。"""
        signals: List[str] = []

        def _assess(label: str, pillar: Tuple[str, str]) -> None:
            stem, branch = pillar
            god = get_ten_god(day_stem, stem)
            if god in (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH):
                signals.append(
                    f"{label}{stem}{branch}见财星，财运转旺，利于求财、投资与正业增收"
                )
            elif god in (TenGod.FOOD_GOD, TenGod.HURT_OFFICER):
                signals.append(
                    f"{label}{stem}{branch}见食伤，食伤生财，利于以才华、项目、副业生财"
                )
            elif god in (TenGod.COMPARE, TenGod.ROB_WEALTH):
                signals.append(f"{label}{stem}{branch}见比劫，防破财、被借贷与合伙纠纷")
            # 地支引动财库/财星
            if STORAGE_BRANCHES.get(branch) == wealth_element:
                signals.append(
                    f"{label}支为{wealth_element.value}财库，逢冲开库主进大财或不动产变现"
                )

        if dayun_pillar:
            _assess("大运", dayun_pillar)
        if liunian_pillar:
            _assess("流年", liunian_pillar)

        return {"timing_signals": signals}

    @staticmethod
    def _generate_suggestions(
        structure: Dict[str, Any],
        style: Dict[str, Any],
        risk: Dict[str, Any],
    ) -> List[str]:
        """生成财运建议。"""
        suggestions: List[str] = []
        suggestions.append(f"财富格局：{structure['pattern']}（{structure['level']}）")

        pattern = structure["pattern"]
        if pattern == "财多身弱":
            suggestions.append(
                "宜先强身（结交贵人、提升专业、稳固根基）再图大财，切忌贪多冒进"
            )
        elif pattern in ("身旺财旺", "身财两停"):
            suggestions.append("身能任财，可积极进取，把握行财运、食伤运的发财窗口")
        elif pattern == "身旺财轻":
            suggestions.append("宜走食伤生财之路，以技术、才华、内容变现，胜于死守正财")

        suggestions.append(style["primary_style"])
        if risk["risks"] and "无明显破财" not in risk["risks"][0]:
            suggestions.append("防破财：" + risk["risks"][0])
        return suggestions
