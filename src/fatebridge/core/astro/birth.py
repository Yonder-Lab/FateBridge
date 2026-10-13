"""Birth coordinates and civil/solar-time normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from fatebridge.utils.places import resolve_birth_place_context
from fatebridge.utils.solar_time import (
    SOLAR_TIME_STRATEGY_APPARENT,
    calculate_solar_time_adjustment,
)
from fatebridge.utils.timezones import parse_timezone_name


@dataclass(frozen=True)
class AstroBirthInfo:
    name: str
    birth_place: str
    timezone: str
    longitude: float
    latitude: float
    local_datetime: datetime
    utc_datetime: datetime
    applied_true_solar: bool = False
    solar_correction_minutes: float = 0.0


def build_astro_birth_info(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    birth_latitude: Optional[float] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
    use_true_solar_time: bool = False,
) -> AstroBirthInfo:
    place_context = resolve_birth_place_context(birth_place)
    timezone_name = birth_timezone or place_context.timezone or "UTC"
    effective_longitude = (
        birth_longitude if birth_longitude is not None else place_context.longitude
    )
    effective_latitude = (
        birth_latitude if birth_latitude is not None else place_context.latitude
    )
    if effective_longitude is None or effective_latitude is None:
        raise ValueError(
            "核心星盘需要 birth_longitude / birth_latitude，或提供 FateBridge 支持的 birth_place 以自动补全坐标。"
        )
    tzinfo = parse_timezone_name(timezone_name)
    local_datetime = datetime(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        birth_minute,
        tzinfo=tzinfo,
    )
    # True solar time: rebase the civil clock onto the apparent Sun (longitude +
    # equation of time), the same correction the BaZi engine applies, so western
    # and Chinese charts share one notion of the birth instant.
    correction_minutes = 0.0
    if use_true_solar_time:
        adjustment = calculate_solar_time_adjustment(
            datetime(birth_year, birth_month, birth_day, birth_hour, birth_minute),
            timezone_name,
            effective_longitude,
            strategy=SOLAR_TIME_STRATEGY_APPARENT,
        )
        correction_minutes = adjustment["total_correction_minutes"]
        local_datetime = local_datetime + timedelta(minutes=correction_minutes)
    utc_datetime = local_datetime.astimezone(parse_timezone_name("UTC"))
    return AstroBirthInfo(
        name=(name or "未提供").strip() or "未提供",
        birth_place=(birth_place or "未提供").strip() or "未提供",
        timezone=timezone_name,
        longitude=effective_longitude,
        latitude=effective_latitude,
        local_datetime=local_datetime,
        utc_datetime=utc_datetime,
        applied_true_solar=use_true_solar_time,
        solar_correction_minutes=round(correction_minutes, 4),
    )
