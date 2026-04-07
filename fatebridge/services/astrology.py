"""
FateBridge astrology services.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fatebridge.core.astrology import (
    build_astro_birth_info,
    build_core_chart_payload,
    build_midpoint_payload,
    build_relative_payload,
)
from fatebridge.utils.helpers import handle_calculation_error


SUPPORTED_CHART_VARIANTS = {
    "chart",
    "chart13",
    "hellen_chart",
    "guolao_chart",
    "india_chart",
}


def _build_birth_info(payload: Dict[str, Any]):
    return build_astro_birth_info(
        birth_year=payload["birth_year"],
        birth_month=payload["birth_month"],
        birth_day=payload["birth_day"],
        birth_hour=payload["birth_hour"],
        birth_minute=payload.get("birth_minute", 0),
        birth_timezone=payload.get("birth_timezone"),
        birth_longitude=payload["birth_longitude"],
        birth_latitude=payload["birth_latitude"],
        name=payload.get("name"),
        birth_place=payload.get("birth_place"),
    )


def calculate_core_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    chart_variant: str = "chart",
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an offline approximate core astrology chart family payload.
    """
    try:
        if chart_variant not in SUPPORTED_CHART_VARIANTS:
            raise ValueError(
                f"不支持的 chart_variant: {chart_variant}。"
                f"可选值：{', '.join(sorted(SUPPORTED_CHART_VARIANTS))}"
            )

        birth_info = _build_birth_info(
            {
                "birth_year": birth_year,
                "birth_month": birth_month,
                "birth_day": birth_day,
                "birth_hour": birth_hour,
                "birth_minute": birth_minute,
                "birth_timezone": birth_timezone,
                "birth_longitude": birth_longitude,
                "birth_latitude": birth_latitude,
                "name": name,
                "birth_place": birth_place,
            }
        )
        return build_core_chart_payload(birth_info, chart_variant)
    except Exception as exc:
        return handle_calculation_error(exc, "核心星盘分析")


def calculate_germany_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the FateBridge midpoint/germany chart payload.
    """
    try:
        birth_info = _build_birth_info(
            {
                "birth_year": birth_year,
                "birth_month": birth_month,
                "birth_day": birth_day,
                "birth_hour": birth_hour,
                "birth_minute": birth_minute,
                "birth_timezone": birth_timezone,
                "birth_longitude": birth_longitude,
                "birth_latitude": birth_latitude,
                "name": name,
                "birth_place": birth_place,
            }
        )
        return build_midpoint_payload(birth_info)
    except Exception as exc:
        return handle_calculation_error(exc, "量化盘分析")


def calculate_relative_chart_analysis(
    *,
    inner_payload: Dict[str, Any],
    outer_payload: Dict[str, Any],
    relationship_mode: str = "synastry",
) -> Dict[str, Any]:
    """
    Build synastry/composite payloads for two parties.
    """
    try:
        inner_birth = _build_birth_info(inner_payload)
        outer_birth = _build_birth_info(outer_payload)
        return build_relative_payload(
            inner_birth=inner_birth,
            outer_birth=outer_birth,
            relationship_mode=relationship_mode,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "关系星盘分析")
