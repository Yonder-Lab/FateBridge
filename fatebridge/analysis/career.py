"""
事业分析模块

基于八字命理的事业分析功能，综合以下经典技法：
- 十神看事业类型与方向
- 五行看行业选择
- 格局看事业高度
- 大运流年看事业时机

核心分析维度：
1. 事业类型与适合行业
2. 事业格局与高度
3. 事业时机（大运/流年）
4. 创业 vs 打工倾向
5. 贵人与小人
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils.data import (
    BRANCH_ELEMENTS,
    BRANCH_HIDDEN_STEMS,
    STEM_ELEMENTS,
    Element,
    TenGod,
    get_ten_god,
)

# 五行对应行业
ELEMENT_INDUSTRIES = {
    Element.WOOD: {
        "label": "木",
        "industries": [
            "教育培训",
            "文化出版",
            "园林绿化",
            "家具木材",
            "纺织服装",
            "医药健康",
            "农业种植",
            "环保生态",
            "设计创意",
            "宗教哲学",
        ],
        "direction": "东方",
        "season": "春季",
    },
    Element.FIRE: {
        "label": "火",
        "industries": [
            "互联网科技",
            "电子电器",
            "能源电力",
            "餐饮娱乐",
            "传媒广告",
            "美容化妆",
            "照明光学",
            "冶炼铸造",
            "心理咨询",
            "演艺娱乐",
        ],
        "direction": "南方",
        "season": "夏季",
    },
    Element.EARTH: {
        "label": "土",
        "industries": [
            "房地产建筑",
            "农业畜牧",
            "矿业资源",
            "仓储物流",
            "陶瓷建材",
            "殡葬服务",
            "宗教场所",
            "人力资源",
            "会计审计",
            "仓储管理",
        ],
        "direction": "中央",
        "season": "四季月（辰戌丑未月）",
    },
    Element.METAL: {
        "label": "金",
        "industries": [
            "金融银行",
            "法律司法",
            "机械制造",
            "汽车交通",
            "珠宝首饰",
            "医疗器械",
            "军事国防",
            "体育竞技",
            "IT硬件",
            "精密仪器",
        ],
        "direction": "西方",
        "season": "秋季",
    },
    Element.WATER: {
        "label": "水",
        "industries": [
            "贸易流通",
            "物流运输",
            "旅游酒店",
            "水产渔业",
            "饮料酒业",
            "水利水务",
            "航海航空",
            "媒体传播",
            "咨询顾问",
            "外交公关",
        ],
        "direction": "北方",
        "season": "冬季",
    },
}

# 十神对应事业特征
TEN_GOD_CAREER = {
    TenGod.COMPARE: {
        "label": "比肩",
        "career_type": "独立经营",
        "traits": "自主性强、竞争意识强、适合独立创业或合伙经营",
        "suitable": ["创业", "合伙经营", "自由职业", "体育竞技"],
    },
    TenGod.ROB_WEALTH: {
        "label": "劫财",
        "career_type": "竞争型",
        "traits": "行动力强、敢于冒险、适合高竞争行业",
        "suitable": ["销售", "市场营销", "投机行业", "体育"],
    },
    TenGod.FOOD_GOD: {
        "label": "食神",
        "career_type": "才华型",
        "traits": "才华横溢、创意丰富、适合文化产业",
        "suitable": ["艺术创作", "餐饮美食", "教育培训", "文化出版"],
    },
    TenGod.HURT_OFFICER: {
        "label": "伤官",
        "career_type": "创新型",
        "traits": "思维独特、不拘常规、适合创新领域",
        "suitable": ["技术研发", "设计创意", "自媒体", "律师"],
    },
    TenGod.POSITIVE_WEALTH: {
        "label": "正财",
        "career_type": "稳健型",
        "traits": "踏实稳健、理财能力强、适合传统行业",
        "suitable": ["财务管理", "银行金融", "会计审计", "实业经营"],
    },
    TenGod.PARTIAL_WEALTH: {
        "label": "偏财",
        "career_type": "投资型",
        "traits": "眼光独到、善于把握机会、适合投资领域",
        "suitable": ["投资理财", "股票期货", "贸易经商", "地产"],
    },
    TenGod.POSITIVE_OFFICER: {
        "label": "正官",
        "career_type": "管理型",
        "traits": "有领导力、守规矩、适合体制内或大企业管理",
        "suitable": ["公务员", "企业管理", "行政管理", "法律"],
    },
    TenGod.SEVEN_KILLER: {
        "label": "七杀",
        "career_type": "权威型",
        "traits": "果断有魄力、适合高压环境",
        "suitable": ["军警", "外科医生", "高管", "创业"],
    },
    TenGod.POSITIVE_SEAL: {
        "label": "正印",
        "career_type": "学术型",
        "traits": "好学上进、有文化底蕴、适合学术教育",
        "suitable": ["教师", "研究员", "公务员", "文化行业"],
    },
    TenGod.PARTIAL_SEAL: {
        "label": "偏印",
        "career_type": "技术型",
        "traits": "思维敏捷、专业技能强、适合技术领域",
        "suitable": ["技术研发", "医疗", "玄学", "IT"],
    },
}


class CareerAnalysis:
    """事业分析工具类"""

    @staticmethod
    def analyze_career(
        pillars: Dict[str, Tuple[str, str]],
        gender: Optional[str] = None,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        综合事业分析。

        Args:
            pillars: 四柱
            gender: 性别
            dayun_pillar: 当前大运柱 (可选)
            liunian_pillar: 当前流年柱 (可选)

        Returns:
            事业分析结果字典
        """
        day_stem = pillars["day"][0]
        day_element = STEM_ELEMENTS[day_stem][0]

        # 1. 主导十神分析
        dominant_god_analysis = CareerAnalysis._analyze_dominant_ten_gods(
            pillars, day_stem
        )

        # 2. 适合行业分析
        industry_analysis = CareerAnalysis._analyze_industries(
            pillars, day_stem, day_element
        )

        # 3. 事业格局
        career_structure = CareerAnalysis._analyze_career_structure(pillars, day_stem)

        # 4. 创业 vs 打工倾向
        entrepreneurship = CareerAnalysis._analyze_entrepreneurship(pillars, day_stem)

        # 5. 事业时机
        career_timing = CareerAnalysis._analyze_career_timing(
            pillars, day_stem, dayun_pillar, liunian_pillar
        )

        # 6. 贵人方位
        noble_direction = CareerAnalysis._analyze_noble_direction(pillars, day_element)

        # 7. 综合建议
        suggestions = CareerAnalysis._generate_suggestions(
            dominant_god_analysis, industry_analysis, career_structure, entrepreneurship
        )

        return {
            "dominant_ten_gods": dominant_god_analysis,
            "industry_analysis": industry_analysis,
            "career_structure": career_structure,
            "entrepreneurship": entrepreneurship,
            "career_timing": career_timing,
            "noble_direction": noble_direction,
            "suggestions": suggestions,
        }

    @staticmethod
    def _analyze_dominant_ten_gods(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
    ) -> Dict[str, Any]:
        """分析命局中主导的十神，确定事业类型。"""
        god_counts: Dict[TenGod, float] = {tg: 0.0 for tg in TenGod}

        for p_name, (stem, branch) in pillars.items():
            if p_name == "day" and stem == day_stem:
                continue
            god = get_ten_god(day_stem, stem)
            god_counts[god] += 1.0
            for hidden in BRANCH_HIDDEN_STEMS.get(branch, []):
                h_god = get_ten_god(day_stem, hidden)
                god_counts[h_god] += 0.5

        # 排序取前三
        sorted_gods = sorted(god_counts.items(), key=lambda x: x[1], reverse=True)
        top_gods = [(god, count) for god, count in sorted_gods if count > 0][:3]

        career_profiles = []
        for god, count in top_gods:
            profile = TEN_GOD_CAREER.get(god, {})
            career_profiles.append(
                {
                    "ten_god": god.value,
                    "weight": round(count, 1),
                    "career_type": profile.get("career_type", "综合型"),
                    "traits": profile.get("traits", ""),
                    "suitable_roles": profile.get("suitable", []),
                }
            )

        return {
            "top_gods": career_profiles,
            "primary_career_type": (
                career_profiles[0]["career_type"] if career_profiles else "综合型"
            ),
        }

    @staticmethod
    def _analyze_industries(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
        day_element: Element,
    ) -> Dict[str, Any]:
        """分析适合的行业方向。"""
        # 统计命局五行分布
        element_counts: Dict[Element, float] = {e: 0.0 for e in Element}
        for stem, branch in pillars.values():
            s_elem = STEM_ELEMENTS[stem][0]
            element_counts[s_elem] += 1.0
            b_elem = BRANCH_ELEMENTS[branch][0]
            element_counts[b_elem] += 0.5
            for hidden in BRANCH_HIDDEN_STEMS.get(branch, []):
                h_elem = STEM_ELEMENTS[hidden][0]
                element_counts[h_elem] += 0.3

        # 喜用神五行
        from ..core.elements import ElementAnalysis

        day_master_analysis = ElementAnalysis.analyze_day_master_strength(pillars)
        favorable = ElementAnalysis.get_favorable_elements(day_master_analysis)

        # 推荐行业基于喜用神
        recommended_industries: List[Dict[str, Any]] = []
        for elem in favorable:
            info = ELEMENT_INDUSTRIES.get(elem)
            if info:
                recommended_industries.append(
                    {
                        "element": info["label"],
                        "industries": info["industries"],
                        "direction": info["direction"],
                        "reason": f"喜用神为{info['label']}，适合{info['label']}相关行业",
                    }
                )

        # 忌神行业
        avoid_elements = [e for e in Element if e not in favorable]
        avoid_industries: List[Dict[str, Any]] = []
        for elem in avoid_elements:
            info = ELEMENT_INDUSTRIES.get(elem)
            if info:
                avoid_industries.append(
                    {
                        "element": info["label"],
                        "industries": info["industries"][:3],
                        "reason": f"忌神为{info['label']}，{info['label']}行业需谨慎",
                    }
                )

        return {
            "favorable_elements": [e.value for e in favorable],
            "recommended_industries": recommended_industries,
            "avoid_industries": avoid_industries,
            "element_distribution": {
                e.value: round(c, 1) for e, c in element_counts.items()
            },
        }

    @staticmethod
    def _analyze_career_structure(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
    ) -> Dict[str, Any]:
        """分析事业格局高低。"""
        score = 60  # 基准分
        notes: List[str] = []

        # 1. 官印相生 → 事业格局高
        has_officer = False
        has_seal = False
        for p_name, (stem, branch) in pillars.items():
            if p_name == "day":
                continue
            god = get_ten_god(day_stem, stem)
            if god in (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER):
                has_officer = True
            if god in (TenGod.POSITIVE_SEAL, TenGod.PARTIAL_SEAL):
                has_seal = True
            for hidden in BRANCH_HIDDEN_STEMS.get(branch, []):
                h_god = get_ten_god(day_stem, hidden)
                if h_god in (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER):
                    has_officer = True
                if h_god in (TenGod.POSITIVE_SEAL, TenGod.PARTIAL_SEAL):
                    has_seal = True

        if has_officer and has_seal:
            score += 15
            notes.append("官印相生，事业格局高，易得权力与地位")

        # 2. 食伤生财 → 经商格局
        has_food_hurt = False
        has_wealth = False
        for p_name, (stem, branch) in pillars.items():
            if p_name == "day":
                continue
            god = get_ten_god(day_stem, stem)
            if god in (TenGod.FOOD_GOD, TenGod.HURT_OFFICER):
                has_food_hurt = True
            if god in (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH):
                has_wealth = True

        if has_food_hurt and has_wealth:
            score += 10
            notes.append("食伤生财，适合经商或技术致富")

        # 3. 财官双美
        if has_officer and has_wealth:
            score += 8
            notes.append("财官双美，名利双收之象")

        # 4. 日主强弱影响
        from ..core.elements import ElementAnalysis

        dm_analysis = ElementAnalysis.analyze_day_master_strength(pillars)
        strength = dm_analysis["strength_level"]
        if strength == "强":
            score += 5
            notes.append("日主强旺，有能力承担事业压力")
        elif strength == "弱":
            score -= 5
            notes.append("日主偏弱，事业中需借力他人")

        score = max(30, min(95, score))

        if score >= 85:
            level = "上等格局"
        elif score >= 70:
            level = "中等格局"
        elif score >= 55:
            level = "普通格局"
        else:
            level = "需努力突破"

        return {
            "score": score,
            "level": level,
            "notes": notes,
        }

    @staticmethod
    def _analyze_entrepreneurship(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
    ) -> Dict[str, Any]:
        """分析创业 vs 打工倾向。"""
        entrepreneur_score = 50
        notes: List[str] = []

        # 统计十神
        god_counts: Dict[str, float] = {}
        for p_name, (stem, branch) in pillars.items():
            if p_name == "day" and stem == day_stem:
                continue
            god = get_ten_god(day_stem, stem).value
            god_counts[god] = god_counts.get(god, 0) + 1
            for hidden in BRANCH_HIDDEN_STEMS.get(branch, []):
                h_god = get_ten_god(day_stem, hidden).value
                god_counts[h_god] = god_counts.get(h_god, 0) + 0.5

        # 偏星多 → 创业倾向
        partial_stars = sum(
            god_counts.get(g, 0)
            for g in [
                TenGod.ROB_WEALTH.value,
                TenGod.HURT_OFFICER.value,
                TenGod.PARTIAL_WEALTH.value,
                TenGod.SEVEN_KILLER.value,
                TenGod.PARTIAL_SEAL.value,
            ]
        )
        normal_stars = sum(
            god_counts.get(g, 0)
            for g in [
                TenGod.COMPARE.value,
                TenGod.FOOD_GOD.value,
                TenGod.POSITIVE_WEALTH.value,
                TenGod.POSITIVE_OFFICER.value,
                TenGod.POSITIVE_SEAL.value,
            ]
        )

        if partial_stars > normal_stars:
            entrepreneur_score += 15
            notes.append("偏星为主，性格独立，适合创业")
        elif normal_stars > partial_stars:
            entrepreneur_score -= 10
            notes.append("正星为主，性格稳重，适合稳定工作")

        # 七杀有制 → 领导型创业者
        if god_counts.get(TenGod.SEVEN_KILLER.value, 0) > 0:
            if god_counts.get(TenGod.FOOD_GOD.value, 0) > 0:
                entrepreneur_score += 10
                notes.append("食神制杀，有魄力有谋略，创业成功率高")
            elif god_counts.get(TenGod.POSITIVE_SEAL.value, 0) > 0:
                entrepreneur_score += 8
                notes.append("杀印相生，有领导力，适合管理型创业")

        entrepreneur_score = max(20, min(90, entrepreneur_score))

        if entrepreneur_score >= 70:
            tendency = "强烈创业倾向"
        elif entrepreneur_score >= 55:
            tendency = "可创业可打工"
        else:
            tendency = "更适合稳定工作"

        return {
            "score": entrepreneur_score,
            "tendency": tendency,
            "notes": notes,
        }

    @staticmethod
    def _analyze_career_timing(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        """分析事业时机。"""
        signals: List[str] = []

        if dayun_pillar:
            d_stem, d_branch = dayun_pillar
            d_god = get_ten_god(day_stem, d_stem)
            if d_god in (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER):
                signals.append(
                    f"大运{d_stem}{d_branch}见官杀，事业运旺盛，有升职或权力增长机会"
                )
            elif d_god in (TenGod.POSITIVE_SEAL, TenGod.PARTIAL_SEAL):
                signals.append(f"大运{d_stem}{d_branch}见印星，贵人运佳，利于学习晋升")
            elif d_god in (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH):
                signals.append(f"大运{d_stem}{d_branch}见财星，财运亨通，利于投资经营")
            elif d_god in (TenGod.FOOD_GOD, TenGod.HURT_OFFICER):
                signals.append(f"大运{d_stem}{d_branch}见食伤，创意表达力强，利于创新")

        if liunian_pillar:
            l_stem, l_branch = liunian_pillar
            l_god = get_ten_god(day_stem, l_stem)
            if l_god in (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER):
                signals.append(f"流年{l_stem}{l_branch}见官杀，当年事业有变动或机遇")
            elif l_god in (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH):
                signals.append(f"流年{l_stem}{l_branch}见财星，当年财运佳")

        return {
            "timing_signals": signals,
        }

    @staticmethod
    def _analyze_noble_direction(
        pillars: Dict[str, Tuple[str, str]],
        day_element: Element,
    ) -> Dict[str, Any]:
        """分析贵人方位。"""
        # 喜用神方位
        from ..core.elements import ElementAnalysis

        dm_analysis = ElementAnalysis.analyze_day_master_strength(pillars)
        favorable = ElementAnalysis.get_favorable_elements(dm_analysis)

        directions: List[Dict[str, Any]] = []
        for elem in favorable:
            info = ELEMENT_INDUSTRIES.get(elem)
            if info:
                directions.append(
                    {
                        "element": info["label"],
                        "direction": info["direction"],
                        "reason": f"喜用神{info['label']}对应{info['direction']}方",
                    }
                )

        return {
            "favorable_directions": directions,
        }

    @staticmethod
    def _generate_suggestions(
        dominant_god: Dict[str, Any],
        industry: Dict[str, Any],
        structure: Dict[str, Any],
        entrepreneurship: Dict[str, Any],
    ) -> List[str]:
        """生成事业建议。"""
        suggestions: List[str] = []

        # 基于主导十神
        primary_type = dominant_god.get("primary_career_type", "综合型")
        suggestions.append(f"主导事业类型为{primary_type}，建议发挥自身优势")

        # 基于格局
        level = structure.get("level", "普通格局")
        if "上等" in level:
            suggestions.append("事业格局高，宜志存高远，把握大机遇")
        elif "中等" in level:
            suggestions.append("事业格局中等，稳扎稳打，步步为营")
        else:
            suggestions.append("事业格局需突破，建议持续学习提升，积累人脉资源")

        # 基于创业倾向
        tendency = entrepreneurship.get("tendency", "")
        if "创业" in tendency:
            suggestions.append("命局适合创业，但需做好充分准备，不宜盲目冒进")
        elif "稳定" in tendency:
            suggestions.append("更适合在稳定环境中发展，可考虑体制内或大企业")

        # 基于行业
        rec = industry.get("recommended_industries", [])
        if rec:
            first_industries = rec[0].get("industries", [])[:3]
            suggestions.append(f"推荐行业：{'、'.join(first_industries)}等")

        return suggestions
