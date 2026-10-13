"""Solar-time strategies and birth-clock normalization with place and timezone provenance."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fatebridge.utils.birth_input import PersonInfo, create_birth_datetime
from fatebridge.utils.places import DEFAULT_BIRTH_TIMEZONE, resolve_birth_place_context
from fatebridge.utils.timezones import (
    invalid_timezone_message as _invalid_timezone_message,
)
from fatebridge.utils.timezones import (
    parse_timezone_name,
)

SOLAR_TIME_STRATEGY_APPARENT = "apparent"


SOLAR_TIME_STRATEGY_LONGITUDE_ONLY = "longitude_only"


# the astrology engine would reject an address the BaZi engine happily accepts.


@dataclass(frozen=True)
class NormalizedBirthTime:
    """Normalized birth-time details used across calculation services."""

    input_datetime: datetime
    corrected_datetime: datetime
    timezone: str
    longitude: Optional[float]
    longitude_source: Optional[str]
    resolved_place: Optional[str]
    resolution_level: Optional[str]
    longitude_correction_minutes: float
    equation_of_time_minutes: float
    daylight_saving_minutes: float
    total_correction_minutes: float
    applied: bool
    # 仅当经度是从 birth_place 推断、且只匹配到省级中心点（而非具体市县）时填充：
    # 告知调用方此次校正用的是省级近似经度，可能与实际地点相差数分钟。
    resolution_advisory: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe summary for API responses."""
        summary: Dict[str, Any] = {
            "applied": self.applied,
            "timezone": self.timezone,
            "longitude": self.longitude,
            "longitude_source": self.longitude_source,
            "resolved_place": self.resolved_place,
            "resolution_level": self.resolution_level,
            "longitude_correction_minutes": round(self.longitude_correction_minutes, 2),
            "equation_of_time_minutes": round(self.equation_of_time_minutes, 2),
            "daylight_saving_minutes": round(self.daylight_saving_minutes, 2),
            "total_correction_minutes": round(self.total_correction_minutes, 2),
        }
        # 仅在有提示时才加入此键：保持无歧义场景（用户显式传经度、市县级匹配）
        # 的输出结构不变，避免给既有消费者凭空多一个 null 字段。
        if self.resolution_advisory is not None:
            summary["resolution_advisory"] = self.resolution_advisory
        return summary


def calculate_equation_of_time_minutes(target_datetime: datetime) -> float:
    """Approximate equation of time in minutes for a given date."""
    day_of_year = target_datetime.timetuple().tm_yday
    b = 2 * math.pi * (day_of_year - 81) / 364
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def calculate_solar_time_adjustment(
    input_datetime: datetime,
    timezone_name: str,
    longitude: float,
    *,
    strategy: str = SOLAR_TIME_STRATEGY_APPARENT,
) -> Dict[str, float]:
    """Calculate solar-time correction details for a local civil datetime."""
    timezone_info = parse_timezone_name(timezone_name)
    aware_datetime = input_datetime.replace(tzinfo=timezone_info)
    utc_offset = aware_datetime.utcoffset()
    if utc_offset is None:
        raise ValueError(_invalid_timezone_message(timezone_name))

    daylight_saving = aware_datetime.dst() or timedelta(0)
    standard_offset = utc_offset - daylight_saving
    standard_meridian = (standard_offset.total_seconds() / 3600) * 15
    longitude_correction_minutes = 4 * (longitude - standard_meridian)
    # Chinese metaphysics conventions use 标准时 (standard civil time) as the
    # base before applying longitude / equation-of-time corrections. When the
    # user's wall-clock input was recorded during a DST period (e.g. China's
    # 夏令时 1986-1991, historic European/US DST dates), the naive clock is an
    # hour ahead of standard time. We subtract the DST amount here so that the
    # resulting normalized datetime reflects true solar time anchored at the
    # standard meridian — otherwise users born near 时辰 boundaries during a
    # DST period land in the wrong hour pillar.
    dst_offset_minutes = daylight_saving.total_seconds() / 60

    if strategy == SOLAR_TIME_STRATEGY_APPARENT:
        equation_of_time_minutes = calculate_equation_of_time_minutes(input_datetime)
        total_correction_minutes = (
            longitude_correction_minutes + equation_of_time_minutes - dst_offset_minutes
        )
    elif strategy == SOLAR_TIME_STRATEGY_LONGITUDE_ONLY:
        # Some local metaphysics techniques use a longitude-only civil-time
        # correction without the equation-of-time term. The sign of the
        # longitude correction must match the SOLAR_TIME_STRATEGY_APPARENT
        # branch: east of the standard meridian -> solar time runs AHEAD of
        # the wall clock, so we ADD longitude_correction_minutes (which is
        # positive east of meridian) and subtract the DST offset to rebase
        # onto standard time before applying the longitude delta.
        equation_of_time_minutes = 0.0
        total_correction_minutes = longitude_correction_minutes - dst_offset_minutes
    else:
        raise ValueError(f"Unsupported solar time strategy: {strategy}")

    return {
        "standard_meridian": standard_meridian,
        "longitude_correction_minutes": longitude_correction_minutes,
        "equation_of_time_minutes": equation_of_time_minutes,
        "daylight_saving_minutes": dst_offset_minutes,
        "total_correction_minutes": total_correction_minutes,
    }


def normalize_birth_time(
    person: PersonInfo,
    *,
    solar_time_strategy: str = SOLAR_TIME_STRATEGY_APPARENT,
) -> NormalizedBirthTime:
    """Normalize birth time and optionally apply true solar time correction."""
    input_datetime = create_birth_datetime(
        person.birth_year,
        person.birth_month,
        person.birth_day,
        person.birth_hour,
        person.birth_minute,
    )

    inferred_place = resolve_birth_place_context(person.birth_place)

    explicit_timezone = person.birth_timezone or inferred_place.timezone
    timezone_name = explicit_timezone or DEFAULT_BIRTH_TIMEZONE

    longitude = person.birth_longitude
    longitude_source = "birth_longitude" if longitude is not None else None
    resolved_place = None if longitude is not None else inferred_place.canonical_name
    resolution_level = None if longitude is not None else inferred_place.level
    if longitude is None and inferred_place.longitude is not None:
        longitude = inferred_place.longitude
        longitude_source = inferred_place.source

    # When no timezone is explicitly supplied but a longitude is known, assume the
    # given wall-clock time is local standard time at the zone nearest that
    # longitude — rather than defaulting to Asia/Shanghai's 120°E meridian, which
    # makes true-solar-time correction badly wrong for non-China longitudes.
    if explicit_timezone is None and longitude is not None:
        zone_hours = max(-12, min(14, int(round(longitude / 15.0))))
        timezone_name = f"{'+' if zone_hours >= 0 else '-'}{abs(zone_hours):02d}:00"

    parse_timezone_name(timezone_name)

    if not person.use_true_solar_time:
        return NormalizedBirthTime(
            input_datetime=input_datetime,
            corrected_datetime=input_datetime,
            timezone=timezone_name,
            longitude=longitude,
            longitude_source=longitude_source,
            resolved_place=resolved_place,
            resolution_level=resolution_level,
            longitude_correction_minutes=0.0,
            equation_of_time_minutes=0.0,
            daylight_saving_minutes=0.0,
            total_correction_minutes=0.0,
            applied=False,
        )

    if longitude is None:
        place = person.birth_place
        if place and place != "未提供":
            uncatalogued_msg = (
                f"True solar time correction needs a longitude, but birth_place "
                f"{place!r} is not in the offline place catalog. Pass "
                "birth_longitude explicitly (east positive, e.g. 108.71 for 咸阳), "
                "or use a catalogued city name."
            )
        else:
            uncatalogued_msg = (
                "True solar time correction needs a longitude. Pass birth_longitude "
                "explicitly (east positive), or a catalogued birth_place city name."
            )
        # 显式请求真太阳时却无经度可用 → fail-loud（与用户显式无效请求的处理一致）。
        if person.true_solar_explicit:
            raise ValueError(uncatalogued_msg)
        # 真太阳时是「默认开」而非显式要求，且无经度可解 → 降级为钟表时间，并透明
        # 提示精度损失（与省级 fallback 的 advisory 同一模式），而不是让默认路径报错。
        return NormalizedBirthTime(
            input_datetime=input_datetime,
            corrected_datetime=input_datetime,
            timezone=timezone_name,
            longitude=longitude,
            longitude_source=longitude_source,
            resolved_place=resolved_place,
            resolution_level=resolution_level,
            longitude_correction_minutes=0.0,
            equation_of_time_minutes=0.0,
            daylight_saving_minutes=0.0,
            total_correction_minutes=0.0,
            applied=False,
            resolution_advisory=(
                "未提供可解析的出生地或 birth_longitude，真太阳时校正未生效，结果按"
                "钟表（标准时区）时间计算；补出生地或经度即可启用真太阳时（经度东正）。"
            ),
        )

    adjustment = calculate_solar_time_adjustment(
        input_datetime,
        timezone_name,
        longitude,
        strategy=solar_time_strategy,
    )
    longitude_correction_minutes = adjustment["longitude_correction_minutes"]
    equation_of_time_minutes = adjustment["equation_of_time_minutes"]
    daylight_saving_minutes = adjustment.get("daylight_saving_minutes", 0.0)
    total_correction_minutes = adjustment["total_correction_minutes"]
    corrected_datetime = input_datetime + timedelta(minutes=total_correction_minutes)

    # 经度来自 birth_place 且只匹配到省级中心点时，校正用的是省级近似经度（如
    # 「江苏省南通市海安市」只识别出省份「江苏」119.42°，与海安实际 ~120.47° 相差
    # 约 1°≈4 分钟）。此时给出明确提示，让调用方知道精度限制并可改传 birth_longitude，
    # 而不是把省级近似当成市县级精度静默使用。
    resolution_advisory = None
    if longitude_source != "birth_longitude" and resolution_level == "province":
        resolution_advisory = (
            f"出生地『{person.birth_place}』未匹配到具体市县，仅按省级"
            f"（{resolved_place}）经度 {longitude:.2f}° 做真太阳时校正，"
            "可能与实际地点相差数分钟；如需精确请改传 birth_longitude。"
        )

    return NormalizedBirthTime(
        input_datetime=input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=timezone_name,
        longitude=longitude,
        longitude_source=longitude_source,
        resolved_place=resolved_place,
        resolution_level=resolution_level,
        longitude_correction_minutes=longitude_correction_minutes,
        equation_of_time_minutes=equation_of_time_minutes,
        daylight_saving_minutes=daylight_saving_minutes,
        total_correction_minutes=total_correction_minutes,
        applied=True,
        resolution_advisory=resolution_advisory,
    )
