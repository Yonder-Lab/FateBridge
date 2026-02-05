"""
FateBridge Compatibility Services
"""
from typing import Dict
import logging

from fatebridge.utils.helpers import (
    PersonInfo,
    handle_calculation_error,
    get_element_relationship,
)
from fatebridge.core.rules import BaZiRules
from fatebridge.analysis.compatibility import AdvancedCompatibility, RelationshipType
from fatebridge.services.calculation import calculate_destiny_analysis

logger = logging.getLogger(__name__)

def calculate_compatibility_analysis(
    person1: PersonInfo, person2: PersonInfo, relationship_type: str = "general"
) -> Dict:
    """
    计算双人配合度，分析两人的命理相互关系和配合程度

    Args:
        person1: 第一人的个人信息对象
        person2: 第二人的个人信息对象
        relationship_type: 关系类型

    Returns:
        dict: 配合度分析结果
    """
    try:
        # 分别计算两人命理分析
        analysis1 = calculate_destiny_analysis(person1)
        analysis2 = calculate_destiny_analysis(person2)

        if "error" in analysis1 or "error" in analysis2:
            return {"error": "计算个人分析时出现错误"}

        # 转换关系类型
        rel_type_map = {
            "marriage": RelationshipType.MARRIAGE,
            "friendship": RelationshipType.FRIENDSHIP,
            "business": RelationshipType.BUSINESS,
            "family": RelationshipType.FAMILY,
            "general": RelationshipType.GENERAL,
        }
        rel_type = rel_type_map.get(relationship_type, RelationshipType.GENERAL)

        # 使用高级合盘分析
        advanced_analysis = AdvancedCompatibility.analyze_comprehensive_compatibility(
            analysis1, analysis2, rel_type
        )

        # 保持向后兼容，同时提供传统分析
        pillars1 = {
            k: (v["stem"], v["branch"]) for k, v in analysis1["four_pillars"].items()
        }
        pillars2 = {
            k: (v["stem"], v["branch"]) for k, v in analysis2["four_pillars"].items()
        }
        traditional_compatibility = BaZiRules.calculate_compatibility_score(
            pillars1, pillars2
        )

        # 五行关系分析
        element1 = analysis1["day_master"]["element"]
        element2 = analysis2["day_master"]["element"]
        element_relationship = get_element_relationship(element1, element2)

        # 喜用神对比 - 安全处理，避免unhashable type错误
        favorable1 = analysis1.get("favorable_elements", [])
        favorable2 = analysis2.get("favorable_elements", [])

        # 确保favorable_elements是字符串列表
        if isinstance(favorable1, list) and all(isinstance(x, str) for x in favorable1):
            favorable1_set = set(favorable1)
        else:
            favorable1_set = set()

        if isinstance(favorable2, list) and all(isinstance(x, str) for x in favorable2):
            favorable2_set = set(favorable2)
        else:
            favorable2_set = set()

        # 优化的JSON输出格式
        return {
            "summary": {
                "overall_score": advanced_analysis["overall_score"],
                "compatibility_level": advanced_analysis["summary"],
                "relationship_type": relationship_type,
            },
            "detailed_analysis": {
                "element_balance": {
                    "score": advanced_analysis["detailed_analysis"]["element_balance"][
                        "score"
                    ],
                    "details": advanced_analysis["detailed_analysis"][
                        "element_balance"
                    ]["details"],
                },
                "favorable_synergy": {
                    "score": advanced_analysis["detailed_analysis"][
                        "favorable_synergy"
                    ]["score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "favorable_synergy"
                    ]["details"],
                },
                "ten_gods_relationship": {
                    "score": advanced_analysis["detailed_analysis"][
                        "ten_gods_relationship"
                    ]["score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "ten_gods_relationship"
                    ]["details"],
                },
                "pattern_synergy": {
                    "score": advanced_analysis["detailed_analysis"]["pattern_synergy"][
                        "score"
                    ],
                    "details": advanced_analysis["detailed_analysis"][
                        "pattern_synergy"
                    ]["details"],
                },
                "traditional_analysis": {
                    "score": advanced_analysis["detailed_analysis"][
                        "traditional_analysis"
                    ]["normalized_score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "traditional_analysis"
                    ]["details"],
                },
            },
            "strengths": advanced_analysis["strengths"],
            "challenges": advanced_analysis["challenges"],
            "recommendations": advanced_analysis["recommendations"],
            "person_info": {
                "person1": {
                    "name": analysis1["person_info"]["name"],
                    "birth_datetime": analysis1["person_info"]["birth_datetime"],
                    "day_master": f"{analysis1['day_master']['stem']}({analysis1['day_master']['element']})",
                    "strength": analysis1["day_master"]["strength"],
                    "favorable_elements": analysis1.get("favorable_elements", []),
                },
                "person2": {
                    "name": analysis2["person_info"]["name"],
                    "birth_datetime": analysis2["person_info"]["birth_datetime"],
                    "day_master": f"{analysis2['day_master']['stem']}({analysis2['day_master']['element']})",
                    "strength": analysis2["day_master"]["strength"],
                    "favorable_elements": analysis2.get("favorable_elements", []),
                },
            },
            "element_relationship": {
                "person1_element": element1,
                "person2_element": element2,
                "relationship_type": element_relationship["type"],
                "description": element_relationship["description"],
            },
            "traditional_compatibility": {
                "score": traditional_compatibility["overall_score"],
                "level": traditional_compatibility["level"],
                "details": traditional_compatibility.get("details", []),
            },
        }
    except Exception as e:
        return handle_calculation_error(e, "配合度分析")
