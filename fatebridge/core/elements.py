"""
Five Elements analysis for BaZi calculations.
"""

from typing import Dict, List, Tuple, Any
from collections import Counter
from ..utils.data import (
    Element,
    Polarity,
    STEM_ELEMENTS,
    BRANCH_ELEMENTS,
    GENERATION_CYCLE,
    DESTRUCTION_CYCLE,
    BRANCH_HIDDEN_STEMS,
    get_ten_god,
)


class ElementAnalysis:
    """
    五行分析工具类，负责分析八字中五行的分布、关系和强弱

    该类提供了完整的五行分析功能，包括：
    - 五行统计：计算各五行在四柱中的出现次数和百分比
    - 日主强弱：分析日干的旺衰程度
    - 十神分析：根据日干与其他干支的关系确定十神
    - 喜用神：根据日主强弱确定有利的五行
    - 综合分析：整合所有五行相关的分析结果

    分析考虑因素：
    - 天干五行：直接对应的五行属性
    - 地支五行：地支本气和藏干的五行
    - 生克关系：五行相生相克的影响
    - 季节因素：月令对五行旺衰的影响
    """

    @staticmethod
    def get_pillar_elements(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Tuple[Element, Polarity]]]:
        """Extract all elements from the four pillars."""
        pillar_elements = {}

        for pillar_name, (stem, branch) in pillars.items():
            elements = []

            # Add stem element
            stem_element, stem_polarity = STEM_ELEMENTS[stem]
            elements.append((stem_element, stem_polarity))

            # Add branch element (main)
            branch_element, branch_polarity = BRANCH_ELEMENTS[branch]
            elements.append((branch_element, branch_polarity))

            # Add hidden stems in branch
            hidden_stems = BRANCH_HIDDEN_STEMS[branch]
            for hidden_stem in hidden_stems:
                hidden_element, hidden_polarity = STEM_ELEMENTS[hidden_stem]
                elements.append((hidden_element, hidden_polarity))

            pillar_elements[pillar_name] = elements

        return pillar_elements

    @staticmethod
    def count_elements(pillars: Dict[str, Tuple[str, str]]) -> Dict[Element, float]:
        """Count the occurrence of each element in the chart."""
        element_count = Counter()

        # Count stem elements
        for stem, branch in pillars.values():
            stem_element, _ = STEM_ELEMENTS[stem]
            element_count[stem_element] += 1

            # Count main branch element
            branch_element, _ = BRANCH_ELEMENTS[branch]
            element_count[branch_element] += 1

            # Count hidden stems (with reduced weight)
            hidden_stems = BRANCH_HIDDEN_STEMS[branch]
            for hidden_stem in hidden_stems:
                hidden_element, _ = STEM_ELEMENTS[hidden_stem]
                element_count[hidden_element] += 0.5  # Hidden stems have less influence

        return dict(element_count)

    @staticmethod
    def convert_to_percentage(element_counts: Dict[Element, float]) -> Dict[str, float]:
        """Convert element counts to percentages."""
        total = sum(element_counts.values())
        if total == 0:
            return {elem.value: 0.0 for elem in Element}

        percentages = {}
        for element, count in element_counts.items():
            percentage = (count / total) * 100
            percentages[element.value] = round(percentage, 1)

        # Ensure total is exactly 100% (handle rounding errors)
        current_total = sum(percentages.values())
        if abs(current_total - 100.0) > 0.1:  # Allow 0.1% tolerance
            # Adjust the largest percentage to make total exactly 100%
            max_key = max(percentages.keys(), key=lambda k: percentages[k])
            percentages[max_key] = round(
                percentages[max_key] + (100.0 - current_total), 1
            )

        return percentages

    @staticmethod
    def validate_percentage_total(percentages: Dict[str, float]) -> bool:
        """Validate that percentages sum to 100% within tolerance."""
        total = sum(percentages.values())
        return abs(total - 100.0) <= 0.1

    @staticmethod
    def analyze_day_master_strength(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, Any]:
        """Analyze the strength of the day master (日主)."""
        day_master_stem = pillars["day"][0]
        day_master_element, day_master_polarity = STEM_ELEMENTS[day_master_stem]

        # Count supporting and opposing elements
        element_counts = ElementAnalysis.count_elements(pillars)

        # Elements that support day master
        same_element_count = element_counts.get(day_master_element, 0)
        generating_element = None
        for element_enum, generated_element in GENERATION_CYCLE.items():
            if generated_element == day_master_element:
                generating_element = element_enum
                break

        support_strength = same_element_count
        if generating_element:
            support_strength += element_counts.get(generating_element, 0)

        # Elements that weaken day master
        element_generated_by_day_master = GENERATION_CYCLE.get(day_master_element)
        element_destroyed_by_day_master = DESTRUCTION_CYCLE.get(day_master_element)
        element_destroying_day_master = None
        for element_enum, destroyed_element in DESTRUCTION_CYCLE.items():
            if destroyed_element == day_master_element:
                element_destroying_day_master = element_enum
                break

        weaken_strength = 0
        if element_generated_by_day_master:
            weaken_strength += element_counts.get(element_generated_by_day_master, 0)
        if element_destroyed_by_day_master:
            weaken_strength += element_counts.get(element_destroyed_by_day_master, 0)
        if element_destroying_day_master:
            weaken_strength += element_counts.get(element_destroying_day_master, 0)

        # Determine strength level
        if support_strength > weaken_strength * 1.5:
            strength_level = "强"
        elif support_strength < weaken_strength * 0.7:
            strength_level = "弱"
        else:
            strength_level = "中和"

        # Convert to percentage format
        element_percentages = ElementAnalysis.convert_to_percentage(element_counts)

        return {
            "day_master": day_master_stem,
            "day_element": day_master_element.value,
            "day_polarity": day_master_polarity.value,
            "support_strength": support_strength,
            "weaken_strength": weaken_strength,
            "strength_level": strength_level,
            "element_distribution": element_percentages,
            "element_distribution_raw": {
                element_enum.value: count
                for element_enum, count in element_counts.items()
            },  # Keep raw scores for internal calculations
        }

    @staticmethod
    def analyze_ten_gods(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Dict[str, str]]]:
        """Analyze the Ten Gods relationships in the chart."""
        day_master_stem = pillars["day"][0]
        ten_gods_analysis = {}

        for pillar_name, (pillar_stem, pillar_branch) in pillars.items():
            pillar_ten_gods = []

            # Analyze stem
            if (
                pillar_name != "day" or pillar_stem != day_master_stem
            ):  # Don't analyze day stem with itself
                ten_god_relationship = get_ten_god(day_master_stem, pillar_stem)
                pillar_ten_gods.append(
                    {
                        "position": f"{pillar_name}_stem",
                        "character": pillar_stem,
                        "ten_god": ten_god_relationship.value,
                    }
                )

            # Analyze hidden stems in branch
            hidden_stems_in_branch = BRANCH_HIDDEN_STEMS[pillar_branch]
            for hidden_stem_index, hidden_stem in enumerate(hidden_stems_in_branch):
                # Hidden stems that share the day-master stem still matter —
                # they represent the day master's 根 (root strength) and show
                # up as 比肩 in classical ten-god tables. Skipping them used to
                # hide a chart's roots (e.g. 庚日 at 巳月 藏 庚 should list
                # 比肩, not disappear).
                ten_god_relationship = get_ten_god(day_master_stem, hidden_stem)
                pillar_ten_gods.append(
                    {
                        "position": f"{pillar_name}_branch_hidden_{hidden_stem_index+1}",
                        "character": hidden_stem,
                        "ten_god": ten_god_relationship.value,
                    }
                )

            ten_gods_analysis[pillar_name] = pillar_ten_gods

        return ten_gods_analysis

    @staticmethod
    def get_favorable_elements(day_master_analysis: Dict[str, Any]) -> List[Element]:
        """Determine favorable elements based on day master strength."""
        day_master_element = None
        for element_enum in Element:
            if element_enum.value == day_master_analysis["day_element"]:
                day_master_element = element_enum
                break

        day_master_strength_level = day_master_analysis["strength_level"]

        if day_master_strength_level == "强":
            # Strong day master needs elements that drain or control it
            favorable_elements = []

            # Elements generated by day master (drain)
            if day_master_element in GENERATION_CYCLE:
                favorable_elements.append(GENERATION_CYCLE[day_master_element])

            # Elements that destroy day master (control)
            for element_enum, destroyed_element in DESTRUCTION_CYCLE.items():
                if destroyed_element == day_master_element:
                    favorable_elements.append(element_enum)
                    break

            # Wealth elements (destroyed by day master)
            if day_master_element in DESTRUCTION_CYCLE:
                favorable_elements.append(DESTRUCTION_CYCLE[day_master_element])

        elif day_master_strength_level == "弱":
            # Weak day master needs support
            favorable_elements = []

            # Same element (support)
            favorable_elements.append(day_master_element)

            # Elements that generate day master
            for element_enum, generated_element in GENERATION_CYCLE.items():
                if generated_element == day_master_element:
                    favorable_elements.append(element_enum)
                    break

        else:  # 中和
            # Balanced day master - depends on seasonal and other factors
            # For simplicity, we'll include elements that provide balance
            favorable_elements = [day_master_element]

        return favorable_elements

    @staticmethod
    def comprehensive_analysis(pillars: Dict[str, Tuple[str, str]]) -> Dict[str, Any]:
        """Perform comprehensive element analysis."""
        day_master_analysis = ElementAnalysis.analyze_day_master_strength(pillars)
        ten_gods_analysis = ElementAnalysis.analyze_ten_gods(pillars)
        favorable_elements = ElementAnalysis.get_favorable_elements(day_master_analysis)

        # Validate percentage totals
        element_distribution = day_master_analysis["element_distribution"]
        is_valid = ElementAnalysis.validate_percentage_total(element_distribution)

        result = {
            "day_master": day_master_analysis,
            "ten_gods": ten_gods_analysis,
            "favorable_elements": [elem.value for elem in favorable_elements],
            "element_distribution": element_distribution,
            "percentage_validation": {
                "is_valid": is_valid,
                "total": round(sum(element_distribution.values()), 1),
            },
        }

        # Add warning if validation fails
        if not is_valid:
            result["warning"] = (
                f"百分比总和异常: {result['percentage_validation']['total']}%"
            )

        return result
