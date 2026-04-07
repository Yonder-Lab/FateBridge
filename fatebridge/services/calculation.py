"""
FateBridge Calculation Services
"""
from typing import Dict

# Import core modules
from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from fatebridge.core.rules import BaZiRules
from fatebridge.utils.helpers import (
    PersonInfo,
    handle_calculation_error,
    create_pillar_dict,
    format_birth_datetime_display,
    normalize_birth_time,
)

def calculate_destiny_analysis(person: PersonInfo) -> Dict:
    """
    Calculate individual destiny analysis based on birth information.
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_datetime = normalized_birth_time.input_datetime
        corrected_birth_datetime = normalized_birth_time.corrected_datetime
        include_minutes = (
            person.birth_minute != 0
            or normalized_birth_time.applied
            or corrected_birth_datetime.minute != 0
        )

        # 计算四柱
        pillars = BaZiCalendar.get_four_pillars(
            corrected_birth_datetime,
            timezone_name=normalized_birth_time.timezone,
        )
        calendar_context = build_calendar_context(
            corrected_birth_datetime,
            timezone_name=normalized_birth_time.timezone,
            pillars=pillars,
        )

        # 五行分析
        element_analysis = ElementAnalysis.comprehensive_analysis(pillars)

        # 格局分析
        harmony_patterns = BaZiRules.check_harmony_patterns(pillars)
        clash_patterns = BaZiRules.check_clash_patterns(pillars)
        stem_patterns = BaZiRules.check_stem_patterns(pillars)
        hidden_patterns = BaZiRules.check_hidden_patterns(pillars)
        pillar_patterns = BaZiRules.check_pillar_patterns(pillars)
        fu_yin_fan_yin = BaZiRules.check_fu_yin_fan_yin(pillars)
        special_patterns = BaZiRules.analyze_special_patterns(
            pillars, corrected_birth_datetime.hour
        )

        return {
            "person_info": {
                "name": person.name or "未提供",
                "birth_datetime": format_birth_datetime_display(
                    birth_datetime, include_minutes=include_minutes
                ),
                "normalized_birth_datetime": format_birth_datetime_display(
                    corrected_birth_datetime, include_minutes=True
                ),
                "gender": person.gender or "未知",
                "birth_place": person.birth_place or "未提供",
                "birth_timezone": normalized_birth_time.timezone,
                "birth_longitude": normalized_birth_time.longitude,
                "time_adjustment": normalized_birth_time.as_dict(),
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
                "stems": stem_patterns,
                "hidden": hidden_patterns,
                "pillar_relationships": pillar_patterns,
                "fu_yin_fan_yin": fu_yin_fan_yin,
                "special": special_patterns,
            },
            "calendar_context": calendar_context,
        }
    except Exception as e:
        return handle_calculation_error(e, "命理分析计算")
