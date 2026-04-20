"""
FateBridge western predictive timing services.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fatebridge.core.astrology_predictive import (
    build_analysis_datetime,
    build_predictive_birth_info,
    build_western_timing_module_payload,
    build_western_timing_payload,
)
from fatebridge.utils.helpers import handle_calculation_error, normalize_house_system


def calculate_western_timing_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_timezone: str,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = None,
    birth_minute: int = 0,
    birth_place: Optional[str] = None,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
) -> Dict[str, Any]:
    """
    Build a western astrology predictive package with returns, progressions,
    and time-lord systems around a target analysis date.
    """
    try:
        house_system = normalize_house_system(house_system)
        birth_info = build_predictive_birth_info(
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            birth_timezone=birth_timezone,
            birth_longitude=birth_longitude,
            birth_latitude=birth_latitude,
            name=name,
            birth_place=birth_place,
        )
        analysis_datetime = build_analysis_datetime(
            birth_info,
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
        )
        return build_western_timing_payload(
            birth_info,
            analysis_datetime=analysis_datetime,
            return_longitude=return_longitude,
            return_latitude=return_latitude,
            return_timezone=return_timezone,
            house_system=house_system,
            zodiac_type=zodiac_type,
            pd_method=pd_method,
            pd_time_key=pd_time_key,
            pd_type=pd_type,
            pd_aspects=pd_aspects,
            show_pd_bounds=show_pd_bounds,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "西占推运与返照分析")


def calculate_western_timing_module_analysis(
    *,
    technique: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_timezone: str,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = None,
    birth_minute: int = 0,
    birth_place: Optional[str] = None,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
) -> Dict[str, Any]:
    """Build a single western timing technique payload for standalone tools."""
    try:
        house_system = normalize_house_system(house_system)
        birth_info = build_predictive_birth_info(
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            birth_timezone=birth_timezone,
            birth_longitude=birth_longitude,
            birth_latitude=birth_latitude,
            name=name,
            birth_place=birth_place,
        )
        analysis_datetime = build_analysis_datetime(
            birth_info,
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
        )
        return build_western_timing_module_payload(
            birth_info,
            technique=technique,
            analysis_datetime=analysis_datetime,
            return_longitude=return_longitude,
            return_latitude=return_latitude,
            return_timezone=return_timezone,
            house_system=house_system,
            zodiac_type=zodiac_type,
            pd_method=pd_method,
            pd_time_key=pd_time_key,
            pd_type=pd_type,
            pd_aspects=pd_aspects,
            show_pd_bounds=show_pd_bounds,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "西占推运与返照分析")
