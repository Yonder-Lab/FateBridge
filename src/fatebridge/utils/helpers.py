"""
Shared utility functions and models for FateBridge.
This module centralizes common functions used across fatebridge/api.py and
fatebridge/mcp_server.py.
"""

import json
import logging
import math
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field, ValidationInfo, field_validator

# --- god-file split: re-export moved symbols for backward-compatible imports ---
# (errors / places / house_systems were factored out; all prior
#  `from fatebridge.utils.helpers import X` call sites keep working.)
from fatebridge.utils.errors import (  # noqa: F401,E402
    DEPENDENCY_ERROR_CODE,
    DEPENDENCY_ERROR_HINTS,
    INTERNAL_ERROR_CODE,
    TIMEOUT_ERROR_CODE,
    VALIDATION_ERROR_CODE,
    calculation_guard,
    handle_calculation_error,
)
from fatebridge.utils.house_systems import (  # noqa: F401,E402
    house_system_fields,
    normalize_house_system,
)
from fatebridge.utils.places import (  # noqa: F401,E402
    DEFAULT_BIRTH_PLACE_ALIASES,
    DEFAULT_BIRTH_TIMEZONE,
    KNOWN_BIRTH_PLACE_ENTRIES,
    KNOWN_BIRTH_PLACE_LATITUDES,
    PLACE_SPECIFICITY,
    PLACE_TEXT_SANITIZER,
    BirthPlaceResolution,
    _resolve_birth_place_context_cached,
    make_birth_place_entry,
    normalize_birth_place_text,
    resolve_birth_place_context,
)
from fatebridge.utils.timezones import (  # noqa: F401
    invalid_timezone_message as _invalid_timezone_message,
)
from fatebridge.utils.timezones import parse_timezone_name  # noqa: F401

logger = logging.getLogger(__name__)


SOLAR_TIME_STRATEGY_APPARENT = "apparent"
SOLAR_TIME_STRATEGY_LONGITUDE_ONLY = "longitude_only"


_MALE_GENDER_TOKENS = frozenset(
    {"男", "male", "m", "man", "boy", "1", "true", "阳", "乾"}
)
_FEMALE_GENDER_TOKENS = frozenset(
    {"女", "female", "f", "woman", "girl", "0", "false", "阴", "坤"}
)


def normalize_gender(gender: Any) -> str:
    """规范化性别输入为中文 "男"/"女"/"未知"。

    接受中英文、大小写、布尔型等多种输入形式，统一输出内部使用的中文标识。
    任何无法识别的输入返回 "未知"。
    """
    if gender is None:
        return "未知"
    if isinstance(gender, bool):
        return "男" if gender else "女"
    token = str(gender).strip().casefold()
    if not token:
        return "未知"
    if token in _MALE_GENDER_TOKENS:
        return "男"
    if token in _FEMALE_GENDER_TOKENS:
        return "女"
    return "未知"


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


# ============================================================================
# Data Models
# ============================================================================


class PersonInfo(BaseModel):
    """个人信息模型"""

    name: Optional[str] = Field(default="未提供", description="姓名（可选）")
    birth_year: int = Field(ge=1900, le=2100, description="出生年份，如2000")
    birth_month: int = Field(ge=1, le=12, description="出生月份 1-12")
    birth_day: int = Field(ge=1, le=31, description="出生日期 1-31")
    birth_hour: int = Field(ge=0, le=23, description="出生时辰 0-23")
    birth_minute: int = Field(default=0, ge=0, le=59, description="出生分钟 0-59")
    gender: Optional[str] = Field(default="未知", description="性别（可选）")
    birth_place: Optional[str] = Field(default="未提供", description="出生地（可选）")
    birth_timezone: Optional[str] = Field(
        default=None, description="出生时区（IANA 名称或 UTC 偏移）"
    )
    birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="出生地经度（可选）"
    )
    use_true_solar_time: bool = Field(default=False, description="是否启用真太阳时修正")
    true_solar_explicit: bool = Field(
        default=True,
        description=(
            "调用方是否「显式」要求了真太阳时（用于缺经度时的失败策略）。True=显式："
            "缺经度则报错(fail-loud)；False=默认值：缺经度则降级为钟表时间并附 advisory。"
            "请求层据 model_fields_set 注入；直接构造默认按显式处理。"
        ),
    )

    @field_validator("birth_day")
    @classmethod
    def validate_birth_day(cls, v: int, info: ValidationInfo) -> int:
        """验证日期是否有效"""
        month = info.data.get("birth_month")
        year = info.data.get("birth_year")

        if month and year:
            max_day = monthrange(year, month)[1]
            if v > max_day:
                raise ValueError(
                    f"无效的日期: {year}年{month}月{v}日 " f"(该月只有{max_day}天)"
                )
        return v


# ============================================================================
# Helper Functions
# ============================================================================


def create_person_info(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
    true_solar_explicit: bool = True,
) -> PersonInfo:
    """创建PersonInfo对象的工具函数

    Args:
        birth_year: 出生年份
        birth_month: 出生月份
        birth_day: 出生日期
        birth_hour: 出生时辰
        name: 姓名
        gender: 性别
        birth_place: 出生地
        birth_minute: 出生分钟
        birth_timezone: 出生时区
        birth_longitude: 出生地经度
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        PersonInfo对象
    """
    return PersonInfo(
        name=name,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        gender=gender,
        birth_place=birth_place,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
        true_solar_explicit=true_solar_explicit,
    )


def create_birth_datetime(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
) -> datetime:
    """创建出生时间datetime对象的工具函数

    Args:
        birth_year: 出生年份
        birth_month: 出生月份
        birth_day: 出生日期
        birth_hour: 出生时辰
        birth_minute: 出生分钟

    Returns:
        datetime对象

    Raises:
        ValueError: 如果日期无效
    """
    try:
        return datetime(birth_year, birth_month, birth_day, birth_hour, birth_minute)
    except ValueError as e:
        error_msg = (
            "Invalid birth date: "
            f"{birth_year}-{birth_month:02d}-{birth_day:02d} "
            f"{birth_hour:02d}:{birth_minute:02d}"
        )
        logger.warning(error_msg)
        raise ValueError(error_msg) from e


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


def format_birth_datetime_display(
    birth_datetime: datetime, include_minutes: bool = False
) -> str:
    """Format birth datetime for user-facing API responses."""
    if include_minutes:
        return birth_datetime.strftime("%Y年%m月%d日 %H时%M分")
    return birth_datetime.strftime("%Y年%m月%d日 %H时")


def create_pillar_dict(
    pillars: Dict[str, Tuple[str, str]],
) -> Dict[str, Dict[str, str]]:
    """创建标准化的四柱字典格式

    Args:
        pillars: 四柱数据

    Returns:
        标准化的四柱字典
    """
    return {
        "year": {"stem": pillars["year"][0], "branch": pillars["year"][1]},
        "month": {"stem": pillars["month"][0], "branch": pillars["month"][1]},
        "day": {"stem": pillars["day"][0], "branch": pillars["day"][1]},
        "hour": {"stem": pillars["hour"][0], "branch": pillars["hour"][1]},
    }


def _prepare_json_response_payload(
    data: Dict[str, Any],
    *,
    include_snapshot_text: bool,
) -> Dict[str, Any]:
    if include_snapshot_text or "snapshot_text" not in data:
        return data

    payload = dict(data)
    payload.pop("snapshot_text", None)
    return payload


def format_json_response(
    data: Dict[str, Any],
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """统一的JSON格式化函数

    Args:
        data: 要格式化的数据字典
        compact: 是否输出紧凑 JSON
        include_snapshot_text: 是否保留 snapshot_text 字段

    Returns:
        格式化的JSON字符串
    """
    payload = _prepare_json_response_payload(
        data,
        include_snapshot_text=include_snapshot_text,
    )
    if compact:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_current_analysis_date(
    analysis_year: Optional[int] = None, analysis_month: Optional[int] = None
) -> Tuple[int, int]:
    """获取当前分析日期

    Args:
        analysis_year: 指定的分析年份
        analysis_month: 指定的分析月份

    Returns:
        (年份, 月份) 元组
    """
    # Local import: helpers is a foundational module imported by core.almanac's
    # consumers, so we avoid a module-level dependency back onto core.
    from ..core.almanac import current_local_datetime

    current_date = current_local_datetime()

    if analysis_year is None:
        analysis_year = current_date.year
    if analysis_month is None:
        analysis_month = current_date.month

    return analysis_year, analysis_month


def format_error_response(
    data: Dict[str, Any],
    operation: str,
    *,
    compact: bool = True,
) -> str:
    """格式化错误响应

    Args:
        data: 包含错误信息的字典
        operation: 操作名称

    Returns:
        格式化的错误信息字符串
    """
    if "error" in data:
        return format_json_response(
            {
                "error": data["error"],
                "error_code": data.get("error_code", INTERNAL_ERROR_CODE),
                "status_code": data.get("status_code", 500),
                "retryable": data.get("retryable", False),
                "operation": operation,
            },
            compact=compact,
        )
    return ""


def get_element_relationship(element1: str, element2: str) -> Dict[str, str]:
    """分析两个五行元素的关系

    Args:
        element1: 第一个元素名称
        element2: 第二个元素名称

    Returns:
        关系分析字典

    Raises:
        ValueError: 如果元素无效
    """
    from fatebridge.utils.data import DESTRUCTION_CYCLE, GENERATION_CYCLE, Element

    # 找到对应的Element枚举
    element1_enum = None
    element2_enum = None

    for element_enum in Element:
        if element_enum.value == element1:
            element1_enum = element_enum
        if element_enum.value == element2:
            element2_enum = element_enum

    # Check for None values before using
    if element1_enum is None or element2_enum is None:
        logger.warning(f"Invalid element reference: {element1} or {element2}")
        return {
            "type": "错误",
            "description": f"无效的五行元素: {element1 if element1_enum is None else element2}",
        }

    if element1_enum == element2_enum:
        return {"type": "相同", "description": "同类元素"}
    elif (
        element1_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相生",
            "description": f"{element1}生{element2}",
        }
    elif (
        element2_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相生",
            "description": f"{element2}生{element1}",
        }
    elif (
        element1_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相克",
            "description": f"{element1}克{element2}",
        }
    elif (
        element2_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相克",
            "description": f"{element2}克{element1}",
        }
    else:
        return {"type": "无直接关系", "description": "元素间无直接生克关系"}
