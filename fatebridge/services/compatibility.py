"""
FateBridge Compatibility Services
"""

import logging
from typing import Any, Dict

from fatebridge.analysis.compatibility import AdvancedCompatibility, RelationshipType
from fatebridge.core.export_parser import parse_export_content
from fatebridge.core.rules import BaZiRules
from fatebridge.services.calculation import (
    _build_birth_computation_context,
    _render_destiny_analysis,
)
from fatebridge.services.structured_snapshot import render_structured_snapshot_text
from fatebridge.utils.helpers import (
    PersonInfo,
    calculation_guard,
    get_element_relationship,
    handle_calculation_error,
)

logger = logging.getLogger(__name__)


@calculation_guard("配合度分析")
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
    context1 = _build_birth_computation_context(person1)
    context2 = _build_birth_computation_context(person2)
    analysis1 = _render_destiny_analysis(context1)
    analysis2 = _render_destiny_analysis(context2)

    # Propagate the underlying per-person error preserving its status_code/
    # error_code so the HTTP layer can return the correct class instead of
    # collapsing everything into a generic 500.
    for upstream in (analysis1, analysis2):
        if "error" in upstream:
            return {
                "error": upstream.get("error", "计算个人分析时出现错误"),
                "error_code": upstream.get("error_code", "internal_error"),
                "status_code": upstream.get("status_code", 500),
                "retryable": upstream.get("retryable", False),
            }

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
    pillars1 = context1.birth_pillars
    pillars2 = context2.birth_pillars
    traditional_compatibility = BaZiRules.calculate_compatibility_score(
        pillars1, pillars2
    )

    # 五行关系分析
    element1 = analysis1["day_master"]["element"]
    element2 = analysis2["day_master"]["element"]
    element_relationship = get_element_relationship(element1, element2)

    # 优化的JSON输出格式
    result: Dict[str, Any] = {
        "summary": {
            "overall_score": advanced_analysis["overall_score"],
            "compatibility_level": advanced_analysis["summary"],
            "relationship_type": relationship_type,
        },
        "detailed_analysis": {
            "element_balance": advanced_analysis["detailed_analysis"][
                "element_balance"
            ],
            "favorable_synergy": advanced_analysis["detailed_analysis"][
                "favorable_synergy"
            ],
            "ten_gods_relationship": advanced_analysis["detailed_analysis"][
                "ten_gods_relationship"
            ],
            "pattern_synergy": advanced_analysis["detailed_analysis"][
                "pattern_synergy"
            ],
            "traditional_analysis": {
                **advanced_analysis["detailed_analysis"]["traditional_analysis"],
                "score": advanced_analysis["detailed_analysis"]["traditional_analysis"][
                    "normalized_score"
                ],
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
    snapshot_text = render_structured_snapshot_text(result, title="双人配合度分析")
    result["snapshot_text"] = snapshot_text
    result["snapshot_export"] = parse_export_content(
        technique="generic", content=snapshot_text
    )
    return result
