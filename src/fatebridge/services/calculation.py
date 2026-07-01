"""
FateBridge Calculation Services
"""

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from fatebridge.core.rules import BaZiRules
from fatebridge.utils.data import Element
from fatebridge.utils.helpers import (
    NormalizedBirthTime,
    PersonInfo,
    calculation_guard,
    create_pillar_dict,
    format_birth_datetime_display,
    normalize_birth_time,
)


@dataclass(frozen=True)
class BirthComputationContext:
    """Shared deterministic birth-computation primitives for heavy services."""

    person: PersonInfo
    normalized_birth_time: NormalizedBirthTime
    birth_pillars: Dict[str, Tuple[str, str]]
    birth_calendar_context: Dict[str, Any]
    element_analysis: Dict[str, Any]
    original_element_counts: Dict[Element, float]


def _extract_original_element_counts(
    element_analysis: Dict[str, Any],
) -> Dict[Element, float]:
    """Reuse raw element counts from comprehensive analysis when available."""
    raw_counts = element_analysis["day_master"].get("element_distribution_raw") or {}
    return {element: float(raw_counts.get(element.value, 0.0)) for element in Element}


def _build_birth_computation_context(person: PersonInfo) -> BirthComputationContext:
    """Build the shared birth context once so downstream services can reuse it."""
    normalized_birth_time = normalize_birth_time(person)
    corrected_birth_datetime = normalized_birth_time.corrected_datetime
    birth_pillars = BaZiCalendar.get_four_pillars(
        corrected_birth_datetime,
        timezone_name=normalized_birth_time.timezone,
    )
    birth_calendar_context = build_calendar_context(
        corrected_birth_datetime,
        timezone_name=normalized_birth_time.timezone,
        pillars=birth_pillars,
    )
    element_analysis = ElementAnalysis.comprehensive_analysis(birth_pillars)

    return BirthComputationContext(
        person=person,
        normalized_birth_time=normalized_birth_time,
        birth_pillars=birth_pillars,
        birth_calendar_context=birth_calendar_context,
        element_analysis=element_analysis,
        original_element_counts=_extract_original_element_counts(element_analysis),
    )


def _render_destiny_analysis(context: BirthComputationContext) -> Dict[str, Any]:
    """Render the public destiny-analysis payload from a shared birth context."""
    person = context.person
    normalized_birth_time = context.normalized_birth_time
    birth_datetime = normalized_birth_time.input_datetime
    corrected_birth_datetime = normalized_birth_time.corrected_datetime
    include_minutes = (
        person.birth_minute != 0
        or normalized_birth_time.applied
        or corrected_birth_datetime.minute != 0
    )

    harmony_patterns = BaZiRules.check_harmony_patterns(context.birth_pillars)
    clash_patterns = BaZiRules.check_clash_patterns(context.birth_pillars)
    stem_patterns = BaZiRules.check_stem_patterns(context.birth_pillars)
    hidden_patterns = BaZiRules.check_hidden_patterns(context.birth_pillars)
    pillar_patterns = BaZiRules.check_pillar_patterns(context.birth_pillars)
    fu_yin_fan_yin = BaZiRules.check_fu_yin_fan_yin(context.birth_pillars)
    special_pattern_metadata = BaZiRules.analyze_special_patterns(
        context.birth_pillars,
        corrected_birth_datetime.hour,
    )
    structure_profile = BaZiRules.build_structure_profile(
        pillars=context.birth_pillars,
        element_analysis=context.element_analysis,
        harmony_patterns=harmony_patterns,
        clash_patterns=clash_patterns,
        special_patterns=special_pattern_metadata,
    )
    special_patterns = {
        **special_pattern_metadata,
        "recognized_structures": structure_profile["recognized_structures"],
        "metadata": special_pattern_metadata,
    }

    return {
        "person_info": {
            "name": person.name or "未提供",
            "birth_datetime": format_birth_datetime_display(
                birth_datetime,
                include_minutes=include_minutes,
            ),
            "normalized_birth_datetime": format_birth_datetime_display(
                corrected_birth_datetime,
                include_minutes=True,
            ),
            "gender": person.gender or "未知",
            "birth_place": person.birth_place or "未提供",
            "birth_timezone": normalized_birth_time.timezone,
            "birth_longitude": normalized_birth_time.longitude,
            "time_adjustment": normalized_birth_time.as_dict(),
        },
        "four_pillars": create_pillar_dict(context.birth_pillars),
        "day_master": {
            "stem": context.birth_pillars["day"][0],
            "element": context.element_analysis["day_master"]["day_element"],
            "polarity": context.element_analysis["day_master"]["day_polarity"],
            "strength": context.element_analysis["day_master"]["strength_level"],
        },
        "element_distribution": context.element_analysis["day_master"][
            "element_distribution"
        ],
        "element_distribution_adjusted": context.element_analysis["day_master"].get(
            "element_distribution_adjusted"
        ),
        "element_relations": context.element_analysis["day_master"].get(
            "element_relations", []
        ),
        "element_distribution_basis": context.element_analysis["day_master"].get(
            "element_distribution_basis"
        ),
        "element_seasonal_phase": context.element_analysis["day_master"].get(
            "element_seasonal_phase"
        ),
        "favorable_elements": structure_profile.get("useful_elements", []),
        "ten_gods": context.element_analysis["ten_gods"],
        "structure_profile": structure_profile,
        "patterns": {
            "harmony": harmony_patterns,
            "clash": clash_patterns,
            "stems": stem_patterns,
            "hidden": hidden_patterns,
            "pillar_relationships": pillar_patterns,
            "fu_yin_fan_yin": fu_yin_fan_yin,
            "special": special_patterns,
        },
        "calendar_context": context.birth_calendar_context,
    }


@calculation_guard("命理分析计算")
def calculate_destiny_analysis(person: PersonInfo) -> Dict:
    """
    Calculate individual destiny analysis based on birth information.
    """
    return _render_destiny_analysis(_build_birth_computation_context(person))
