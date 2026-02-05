"""
Business logic module for FateBridge - imports shared utilities.
"""

from typing import Dict

# Import core modules
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from fatebridge.core.rules import BaZiRules
from fatebridge.utils.helpers import (
    PersonInfo,
    create_person_info,
    create_birth_datetime,
    handle_calculation_error,
    create_pillar_dict,
)


# ============================================================================
# Core Logic
# ============================================================================


def calculate_fatebridge(person: PersonInfo) -> Dict:
    try:
        # 转换为datetime
        birth_datetime = create_birth_datetime(
            person.birth_year, person.birth_month, person.birth_day, person.birth_hour
        )

        # 计算四柱
        pillars = BaZiCalendar.get_four_pillars(birth_datetime)

        # 五行分析
        element_analysis = ElementAnalysis.comprehensive_analysis(pillars)

        # 格局分析
        harmony_patterns = BaZiRules.check_harmony_patterns(pillars)
        clash_patterns = BaZiRules.check_clash_patterns(pillars)
        special_patterns = BaZiRules.analyze_special_patterns(
            pillars, person.birth_hour
        )

        return {
            "person_info": {
                "name": person.name or "未提供",
                "birth_datetime": birth_datetime.strftime("%Y年%m月%d日 %H时"),
                "gender": person.gender or "未知",
                "birth_place": person.birth_place or "未提供",
            },
            "four_pillars": create_pillar_dict(pillars),
            "day_master": {
                "stem": pillars["day"][0],
                "element": element_analysis["day_master"]["day_element"],
                "polarity": element_analysis["day_master"]["day_polarity"],
                "strength": element_analysis["day_master"]["strength_level"],
            },
            "element_distribution": element_analysis["day_master"][
                "element_distribution"
            ],
            "favorable_elements": element_analysis.get("favorable_elements", []),
            "ten_gods": element_analysis["ten_gods"],
            "patterns": {
                "harmony": harmony_patterns,
                "clash": clash_patterns,
                "special": special_patterns,
            },
        }
    except Exception as e:
        return handle_calculation_error(e, "命理分析计算")
