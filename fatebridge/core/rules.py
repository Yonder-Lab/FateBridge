"""
BaZi rules and pattern analysis.
"""

from typing import Dict, List, Tuple, Any
from ..utils.data import HEAVENLY_STEMS, EARTHLY_BRANCHES


class BaZiRules:
    """Analyzes special patterns and rules in BaZi charts."""

    # 地支三合 (Triple Harmony)
    TRIPLE_HARMONY = [
        ("申", "子", "辰"),  # 水局
        ("亥", "卯", "未"),  # 木局
        ("寅", "午", "戌"),  # 火局
        ("巳", "酉", "丑"),  # 金局
    ]

    # 地支六合 (Six Harmony)
    SIX_HARMONY = [
        ("子", "丑"),
        ("寅", "亥"),
        ("卯", "戌"),
        ("辰", "酉"),
        ("巳", "申"),
        ("午", "未"),
    ]

    # 地支六冲 (Six Clash)
    SIX_CLASH = [
        ("子", "午"),
        ("丑", "未"),
        ("寅", "申"),
        ("卯", "酉"),
        ("辰", "戌"),
        ("巳", "亥"),
    ]

    # 地支三刑 (Triple Punishment)
    TRIPLE_PUNISHMENT = [
        ("寅", "巳", "申"),  # 无恩之刑
        ("丑", "戌", "未"),  # 恃势之刑
        ("子", "卯"),  # 无礼之刑
        ("辰",),
        ("午",),
        ("酉",),
        ("亥",),  # 自刑
    ]

    @staticmethod
    def check_harmony_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[str]]:
        """Check for harmony patterns in the chart."""
        all_branches = [pillar_branch for _, pillar_branch in pillars.values()]
        harmony_patterns = {
            "triple_harmony": [],
            "six_harmony": [],
        }

        # Check triple harmony
        for triple_harmony_set in BaZiRules.TRIPLE_HARMONY:
            found_branches_in_set = [
                branch for branch in triple_harmony_set if branch in all_branches
            ]
            if len(found_branches_in_set) >= 2:
                element_mapping = {
                    ("申", "子", "辰"): "水局",
                    ("亥", "卯", "未"): "木局",
                    ("寅", "午", "戌"): "火局",
                    ("巳", "酉", "丑"): "金局",
                }
                harmony_patterns["triple_harmony"].append(
                    {
                        "type": element_mapping[triple_harmony_set],
                        "branches": found_branches_in_set,
                        "complete": len(found_branches_in_set) == 3,
                    }
                )

        # Check six harmony
        for six_harmony_pair in BaZiRules.SIX_HARMONY:
            if all(branch in all_branches for branch in six_harmony_pair):
                harmony_patterns["six_harmony"].append(list(six_harmony_pair))

        return harmony_patterns

    @staticmethod
    def check_clash_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[str]]:
        """Check for clash patterns in the chart."""
        all_branches = [pillar_branch for _, pillar_branch in pillars.values()]
        clash_patterns = {
            "six_clash": [],
            "triple_punishment": [],
        }

        # Check six clash
        for six_clash_pair in BaZiRules.SIX_CLASH:
            if all(branch in all_branches for branch in six_clash_pair):
                clash_patterns["six_clash"].append(list(six_clash_pair))

        # Check triple punishment
        for punishment_set in BaZiRules.TRIPLE_PUNISHMENT:
            if len(punishment_set) == 3:  # Triple punishment (寅巳申、丑戌未)
                # 传统理论：任意两个地支出现就构成相刑
                found_branches_in_punishment = [
                    branch for branch in punishment_set if branch in all_branches
                ]
                if len(found_branches_in_punishment) >= 2:
                    clash_patterns["triple_punishment"].append(
                        found_branches_in_punishment
                    )
            elif len(punishment_set) == 2:  # Pair punishment (子卯)
                if all(branch in all_branches for branch in punishment_set):
                    clash_patterns["triple_punishment"].append(list(punishment_set))
            elif len(punishment_set) == 1:  # Self punishment (辰、午、酉、亥)
                punishment_branch = punishment_set[0]
                branch_count = all_branches.count(punishment_branch)
                if branch_count >= 2:
                    clash_patterns["triple_punishment"].append(
                        [punishment_branch] * branch_count
                    )

        return clash_patterns

    @staticmethod
    def analyze_special_patterns(
        pillars: Dict[str, Tuple[str, str]], birth_hour: int = None
    ) -> Dict[str, Any]:
        """Analyze special patterns in the BaZi chart."""
        stems = [stem for stem, _ in pillars.values()]
        branches = [branch for _, branch in pillars.values()]

        patterns = {}

        # Check for special day pillar patterns
        day_stem, day_branch = pillars["day"]

        # 日贵格 (Noble Day Pattern)
        # 正确的日贵格只有四日：丁酉、丁亥、癸巳、癸卯
        day_pillar = f"{day_stem}{day_branch}"
        noble_days = ["丁酉", "丁亥", "癸巳", "癸卯"]

        if day_pillar in noble_days:
            patterns["noble_day"] = True

            # 添加昼夜区分
            if birth_hour is not None:
                # 昼贵：癸卯、丁亥（白天6-18时）
                # 夜贵：癸巳、丁酉（夜晚18-6时）
                is_daytime = 6 <= birth_hour < 18

                if day_pillar in ["癸卯", "丁亥"] and is_daytime:
                    patterns["noble_day_type"] = "昼贵"
                elif day_pillar in ["癸巳", "丁酉"] and not is_daytime:
                    patterns["noble_day_type"] = "夜贵"
                else:
                    patterns["noble_day_type"] = "不合时"

        # 魁罡格 (Kui Gang Pattern)
        kui_gang_days = ["庚戌", "庚辰", "戊戌", "壬辰"]
        if f"{day_stem}{day_branch}" in kui_gang_days:
            patterns["kui_gang"] = True

        # Check stem patterns
        # 四同 (Four Same)
        for stem in HEAVENLY_STEMS:
            if stems.count(stem) == 4:
                patterns["four_same_stems"] = stem

        for branch in EARTHLY_BRANCHES:
            if branches.count(branch) == 4:
                patterns["four_same_branches"] = branch

        # 天干一气 (Heavenly Stems Unity)
        if len(set(stems)) == 1:
            patterns["stem_unity"] = stems[0]

        # 地支一气 (Earthly Branches Unity)
        if len(set(branches)) == 1:
            patterns["branch_unity"] = branches[0]

        return patterns

    @staticmethod
    def calculate_compatibility_score(
        pillars1: Dict[str, Tuple[str, str]], pillars2: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Calculate basic compatibility score between two BaZi charts."""
        compatibility = {
            "harmony_score": 0,
            "clash_score": 0,
            "overall_score": 0,
            "details": [],
        }

        # Extract all branches from both charts
        branches1 = [branch for _, branch in pillars1.values()]
        branches2 = [branch for _, branch in pillars2.values()]

        # Check harmony between charts
        for b1 in branches1:
            for b2 in branches2:
                # Check six harmony
                for harmony_pair in BaZiRules.SIX_HARMONY:
                    if (b1, b2) in [harmony_pair, harmony_pair[::-1]]:
                        compatibility["harmony_score"] += 2
                        compatibility["details"].append(f"{b1}与{b2}六合")

                # Check six clash
                for clash_pair in BaZiRules.SIX_CLASH:
                    if (b1, b2) in [clash_pair, clash_pair[::-1]]:
                        compatibility["clash_score"] += 2
                        compatibility["details"].append(f"{b1}与{b2}六冲")

        # Check day pillar compatibility (most important)
        day_stem1, day_branch1 = pillars1["day"]
        day_stem2, day_branch2 = pillars2["day"]

        # Day branch harmony/clash has higher weight
        for harmony_pair in BaZiRules.SIX_HARMONY:
            if (day_branch1, day_branch2) in [harmony_pair, harmony_pair[::-1]]:
                compatibility["harmony_score"] += 5
                compatibility["details"].append(
                    f"日支{day_branch1}与{day_branch2}六合(重要)"
                )

        for clash_pair in BaZiRules.SIX_CLASH:
            if (day_branch1, day_branch2) in [clash_pair, clash_pair[::-1]]:
                compatibility["clash_score"] += 5
                compatibility["details"].append(
                    f"日支{day_branch1}与{day_branch2}六冲(重要)"
                )

        # Calculate overall score
        compatibility["overall_score"] = (
            compatibility["harmony_score"] - compatibility["clash_score"]
        )

        # Determine compatibility level
        if compatibility["overall_score"] >= 8:
            compatibility["level"] = "非常匹配"
        elif compatibility["overall_score"] >= 4:
            compatibility["level"] = "比较匹配"
        elif compatibility["overall_score"] >= 0:
            compatibility["level"] = "一般匹配"
        elif compatibility["overall_score"] >= -4:
            compatibility["level"] = "需要磨合"
        else:
            compatibility["level"] = "不太匹配"

        return compatibility

    @staticmethod
    def get_life_analysis(
        pillars: Dict[str, Tuple[str, str]], element_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide life analysis based on BaZi patterns."""
        analysis = {
            "personality": [],
            "career": [],
            "health": [],
            "relationships": [],
            "fortune": [],
        }

        day_stem = pillars["day"][0]
        day_branch = pillars["day"][1]
        strength_level = element_analysis["day_master"]["strength_level"]

        # Basic personality analysis based on day stem
        personality_map = {
            "甲": "积极主动，有领导能力，但有时过于刚强",
            "乙": "温和柔韧，适应力强，但有时优柔寡断",
            "丙": "热情开朗，有感染力，但有时过于冲动",
            "丁": "细致敏感，有创造力，但有时过于敏感",
            "戊": "稳重踏实，有责任心，但有时过于固执",
            "己": "温和谦逊，有包容心，但有时缺乏主见",
            "庚": "果断坚定，有执行力，但有时过于严厉",
            "辛": "精致细腻，有品味，但有时过于挑剔",
            "壬": "灵活变通，有智慧，但有时过于多变",
            "癸": "温柔体贴，有直觉力，但有时过于被动",
        }

        if day_stem in personality_map:
            analysis["personality"].append(personality_map[day_stem])

        # Add strength analysis
        if strength_level == "强":
            analysis["personality"].append("个性较强，自信心足，但需要注意不要过于自我")
            analysis["career"].append("适合领导管理类工作，创业运佳")
        elif strength_level == "弱":
            analysis["personality"].append("性格较为温和，需要他人扶持")
            analysis["career"].append("适合团队合作，技术专业类工作")
        else:
            analysis["personality"].append("性格较为平衡，能够适应各种环境")

        # Fortune analysis based on favorable elements
        favorable_elements = element_analysis.get("favorable_elements", [])
        if favorable_elements:
            analysis["fortune"].append(f"有利五行: {', '.join(favorable_elements)}")

        return analysis
