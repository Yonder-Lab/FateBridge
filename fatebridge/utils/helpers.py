"""
Shared utility functions and models for FateBridge.
This module centralizes common functions used across api.py and fastmcp_server.py.
"""

import json
import logging
import math
import re
import unicodedata
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from dateutil import tz

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


DEFAULT_BIRTH_TIMEZONE = "Asia/Shanghai"
PLACE_TEXT_SANITIZER = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")

PLACE_SPECIFICITY = {
    "province": 1,
    "special_region": 2,
    "city": 3,
    "municipality": 4,
}

DEFAULT_BIRTH_PLACE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "北京": ("beijing", "peking"),
    "上海": ("shanghai",),
    "天津": ("tianjin",),
    "重庆": ("chongqing",),
    "香港": ("hong kong", "hongkong"),
    "澳门": ("macau", "macao"),
    "台北": ("taipei",),
    "河北": ("hebei",),
    "山西": ("shanxi",),
    "辽宁": ("liaoning",),
    "吉林": ("jilin",),
    "黑龙江": ("heilongjiang", "hei longjiang"),
    "江苏": ("jiangsu",),
    "浙江": ("zhejiang",),
    "安徽": ("anhui",),
    "福建": ("fujian",),
    "江西": ("jiangxi",),
    "山东": ("shandong",),
    "河南": ("henan",),
    "湖北": ("hubei",),
    "湖南": ("hunan",),
    "广东": ("guangdong",),
    "海南": ("hainan",),
    "四川": ("sichuan",),
    "贵州": ("guizhou",),
    "云南": ("yunnan",),
    "陕西": ("shaanxi",),
    "甘肃": ("gansu",),
    "青海": ("qinghai",),
    "台湾": ("taiwan",),
    "内蒙古": ("neimenggu", "inner mongolia"),
    "广西": ("guangxi",),
    "西藏": ("xizang", "tibet"),
    "宁夏": ("ningxia",),
    "新疆": ("xinjiang",),
    "广州": ("guangzhou", "canton"),
    "深圳": ("shenzhen",),
    "杭州": ("hangzhou",),
    "宁波": ("ningbo",),
    "南京": ("nanjing",),
    "苏州": ("suzhou",),
    "武汉": ("wuhan",),
    "成都": ("chengdu",),
    "西安": ("xi'an", "xi an", "xian"),
    "乌鲁木齐": ("urumqi", "wulumuqi", "urumchi"),
    "石家庄": ("shijiazhuang",),
    "济南": ("jinan",),
    "青岛": ("qingdao", "tsingtao"),
    "郑州": ("zhengzhou",),
    "长沙": ("changsha",),
    "福州": ("fuzhou",),
    "厦门": ("xiamen", "amoy"),
    "合肥": ("hefei",),
    "南昌": ("nanchang",),
    "昆明": ("kunming",),
    "贵阳": ("guiyang",),
    "南宁": ("nanning",),
    "海口": ("haikou",),
    "呼和浩特": ("huhehaote", "hohhot"),
    "银川": ("yinchuan",),
    "兰州": ("lanzhou",),
    "西宁": ("xining",),
    "拉萨": ("lhasa", "lasa"),
    "喀什": ("kashi", "kashgar"),
    "纽约": ("new york", "newyork", "nyc"),
    "伦敦": ("london",),
    "东京": ("tokyo",),
    "悉尼": ("sydney",),
}


def normalize_birth_place_text(text: str) -> str:
    """Normalize Chinese/English place text for fuzzy offline matching."""
    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    return PLACE_TEXT_SANITIZER.sub("", normalized_text)


def make_birth_place_entry(
    canonical_name: str,
    longitude: float,
    *,
    timezone: str = DEFAULT_BIRTH_TIMEZONE,
    level: str = "city",
    aliases: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """Build one offline address-resolution entry."""
    merged_aliases = tuple(
        dict.fromkeys(
            (
                canonical_name,
                *DEFAULT_BIRTH_PLACE_ALIASES.get(canonical_name, ()),
                *aliases,
            )
        )
    )
    normalized_aliases = tuple(
        dict.fromkeys(
            normalize_birth_place_text(alias)
            for alias in merged_aliases
            if normalize_birth_place_text(alias)
        )
    )
    return {
        "canonical_name": canonical_name,
        "longitude": longitude,
        "timezone": timezone,
        "level": level,
        "specificity": PLACE_SPECIFICITY[level],
        "aliases": merged_aliases,
        "normalized_aliases": normalized_aliases,
    }


# Offline location hints for true solar time correction. This is still an
# approximate parser: it matches province/city aliases in free-form text and
# falls back to province-level coordinates when no known city appears.
KNOWN_BIRTH_PLACE_ENTRIES = (
    # Municipalities and SARs
    make_birth_place_entry("北京", 116.4074, level="municipality", aliases=("北京市",)),
    make_birth_place_entry("上海", 121.4737, level="municipality", aliases=("上海市",)),
    make_birth_place_entry("天津", 117.2000, level="municipality", aliases=("天津市",)),
    make_birth_place_entry("重庆", 106.5516, level="municipality", aliases=("重庆市",)),
    make_birth_place_entry(
        "香港",
        114.1694,
        timezone="Asia/Hong_Kong",
        level="special_region",
        aliases=("香港特别行政区",),
    ),
    make_birth_place_entry(
        "澳门",
        113.5439,
        timezone="Asia/Macau",
        level="special_region",
        aliases=("澳门特别行政区",),
    ),
    make_birth_place_entry(
        "台北",
        121.5654,
        timezone="Asia/Taipei",
        level="special_region",
        aliases=("臺北", "台北市", "臺北市"),
    ),
    # Province-level fallbacks
    make_birth_place_entry("河北", 114.5149, level="province", aliases=("河北省",)),
    make_birth_place_entry("山西", 112.5492, level="province", aliases=("山西省",)),
    make_birth_place_entry("辽宁", 123.4315, level="province", aliases=("辽宁省",)),
    make_birth_place_entry("吉林", 125.3235, level="province", aliases=("吉林省",)),
    make_birth_place_entry("黑龙江", 126.6424, level="province", aliases=("黑龙江省",)),
    make_birth_place_entry("江苏", 119.4210, level="province", aliases=("江苏省",)),
    make_birth_place_entry("浙江", 119.9572, level="province", aliases=("浙江省",)),
    make_birth_place_entry("安徽", 117.2272, level="province", aliases=("安徽省",)),
    make_birth_place_entry("福建", 119.2965, level="province", aliases=("福建省",)),
    make_birth_place_entry("江西", 115.8582, level="province", aliases=("江西省",)),
    make_birth_place_entry("山东", 117.1201, level="province", aliases=("山东省",)),
    make_birth_place_entry("河南", 113.6254, level="province", aliases=("河南省",)),
    make_birth_place_entry("湖北", 114.3419, level="province", aliases=("湖北省",)),
    make_birth_place_entry("湖南", 112.9388, level="province", aliases=("湖南省",)),
    make_birth_place_entry("广东", 113.2665, level="province", aliases=("广东省",)),
    make_birth_place_entry("海南", 110.3312, level="province", aliases=("海南省",)),
    make_birth_place_entry("四川", 104.0758, level="province", aliases=("四川省",)),
    make_birth_place_entry("贵州", 106.6302, level="province", aliases=("贵州省",)),
    make_birth_place_entry("云南", 102.8329, level="province", aliases=("云南省",)),
    make_birth_place_entry("陕西", 108.9398, level="province", aliases=("陕西省",)),
    make_birth_place_entry("甘肃", 103.8343, level="province", aliases=("甘肃省",)),
    make_birth_place_entry("青海", 101.7782, level="province", aliases=("青海省",)),
    make_birth_place_entry("台湾", 121.5654, timezone="Asia/Taipei", level="province", aliases=("台湾省", "臺灣", "臺灣省")),
    make_birth_place_entry("内蒙古", 111.6708, level="province", aliases=("内蒙古自治区",)),
    make_birth_place_entry("广西", 108.3200, level="province", aliases=("广西", "广西壮族自治区")),
    make_birth_place_entry("西藏", 91.1322, level="province", aliases=("西藏自治区",)),
    make_birth_place_entry("宁夏", 106.2782, level="province", aliases=("宁夏回族自治区",)),
    make_birth_place_entry("新疆", 87.6168, level="province", aliases=("新疆", "新疆维吾尔自治区")),
    # Broader city coverage
    make_birth_place_entry("广州", 113.2644, aliases=("广州市",)),
    make_birth_place_entry("深圳", 114.0579, aliases=("深圳市",)),
    make_birth_place_entry("杭州", 120.1551, aliases=("杭州市",)),
    make_birth_place_entry("宁波", 121.5503, aliases=("宁波市",)),
    make_birth_place_entry("南京", 118.7969, aliases=("南京市",)),
    make_birth_place_entry("苏州", 120.5853, aliases=("苏州市",)),
    make_birth_place_entry("武汉", 114.3054, aliases=("武汉市",)),
    make_birth_place_entry("成都", 104.0665, aliases=("成都市",)),
    make_birth_place_entry("西安", 108.9398, aliases=("西安市",)),
    make_birth_place_entry("乌鲁木齐", 87.6168, aliases=("乌鲁木齐市",)),
    make_birth_place_entry("石家庄", 114.5149, aliases=("石家庄市",)),
    make_birth_place_entry("济南", 117.1201, aliases=("济南市",)),
    make_birth_place_entry("青岛", 120.3826, aliases=("青岛市",)),
    make_birth_place_entry("郑州", 113.6254, aliases=("郑州市",)),
    make_birth_place_entry("长沙", 112.9388, aliases=("长沙市",)),
    make_birth_place_entry("福州", 119.2965, aliases=("福州市",)),
    make_birth_place_entry("厦门", 118.0894, aliases=("厦门市",)),
    make_birth_place_entry("合肥", 117.2272, aliases=("合肥市",)),
    make_birth_place_entry("南昌", 115.8582, aliases=("南昌市",)),
    make_birth_place_entry("昆明", 102.8329, aliases=("昆明市",)),
    make_birth_place_entry("贵阳", 106.6302, aliases=("贵阳市",)),
    make_birth_place_entry("南宁", 108.3200, aliases=("南宁市",)),
    make_birth_place_entry("海口", 110.3312, aliases=("海口市",)),
    make_birth_place_entry("呼和浩特", 111.6708, aliases=("呼和浩特市",)),
    make_birth_place_entry("银川", 106.2782, aliases=("银川市",)),
    make_birth_place_entry("兰州", 103.8343, aliases=("兰州市",)),
    make_birth_place_entry("西宁", 101.7782, aliases=("西宁市",)),
    make_birth_place_entry("拉萨", 91.1322, aliases=("拉萨市",)),
    make_birth_place_entry("喀什", 75.9898, aliases=("喀什地区", "喀什市")),
    # International cities retained from the previous version
    make_birth_place_entry("纽约", -74.0060, timezone="America/New_York", aliases=("纽约市",)),
    make_birth_place_entry("伦敦", -0.1278, timezone="Europe/London"),
    make_birth_place_entry("东京", 139.6917, timezone="Asia/Tokyo", aliases=("东京都",)),
    make_birth_place_entry("悉尼", 151.2093, timezone="Australia/Sydney", aliases=("悉尼市",)),
)


@dataclass(frozen=True)
class BirthPlaceResolution:
    """One resolved address candidate from the offline catalog."""

    canonical_name: Optional[str]
    longitude: Optional[float]
    timezone: Optional[str]
    source: Optional[str]
    level: Optional[str]


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
    total_correction_minutes: float
    applied: bool

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe summary for API responses."""
        return {
            "applied": self.applied,
            "timezone": self.timezone,
            "longitude": self.longitude,
            "longitude_source": self.longitude_source,
            "resolved_place": self.resolved_place,
            "resolution_level": self.resolution_level,
            "longitude_correction_minutes": round(
                self.longitude_correction_minutes, 2
            ),
            "equation_of_time_minutes": round(self.equation_of_time_minutes, 2),
            "total_correction_minutes": round(self.total_correction_minutes, 2),
        }


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
    use_true_solar_time: bool = Field(
        default=False, description="是否启用真太阳时修正"
    )

    @field_validator('birth_day')
    @classmethod
    def validate_birth_day(cls, v: int, info) -> int:
        """验证日期是否有效"""
        month = info.data.get('birth_month')
        year = info.data.get('birth_year')

        if month and year:
            max_day = monthrange(year, month)[1]
            if v > max_day:
                raise ValueError(
                    f"无效的日期: {year}年{month}月{v}日 "
                    f"(该月只有{max_day}天)"
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
        return datetime(
            birth_year, birth_month, birth_day, birth_hour, birth_minute
        )
    except ValueError as e:
        error_msg = (
            "Invalid birth date: "
            f"{birth_year}-{birth_month:02d}-{birth_day:02d} "
            f"{birth_hour:02d}:{birth_minute:02d}"
        )
        logger.warning(error_msg)
        raise ValueError(error_msg) from e


def resolve_birth_place_context(
    birth_place: Optional[str],
) -> BirthPlaceResolution:
    """Resolve longitude/timezone hints from a free-form birth place string."""
    if not birth_place or birth_place == "未提供":
        return BirthPlaceResolution(None, None, None, None, None)

    normalized_place = normalize_birth_place_text(birth_place)

    best_match: Optional[Tuple[int, int, int, Dict[str, Any]]] = None
    for entry in KNOWN_BIRTH_PLACE_ENTRIES:
        for alias in entry["normalized_aliases"]:
            if alias and alias in normalized_place:
                score = (
                    entry["specificity"],
                    len(alias),
                    len(entry["canonical_name"]),
                    1,
                )
                if best_match is None or score > best_match[:4]:
                    best_match = (*score, entry)

    if best_match is None:
        return BirthPlaceResolution(None, None, None, None, None)

    entry = best_match[4]
    return BirthPlaceResolution(
        canonical_name=entry["canonical_name"],
        longitude=entry["longitude"],
        timezone=entry["timezone"],
        source="birth_place",
        level=entry["level"],
    )


def parse_timezone_name(timezone_name: str):
    """Parse IANA names or UTC±HH[:MM] offsets into a tzinfo."""
    timezone_name = timezone_name.strip()
    timezone_info = tz.gettz(timezone_name)
    if timezone_info is not None:
        return timezone_info

    normalized_name = timezone_name.upper().replace("GMT", "UTC")
    if normalized_name == "UTC":
        return tz.tzutc()

    if not normalized_name.startswith("UTC") or len(normalized_name) < 5:
        raise ValueError(f"Invalid birth timezone: {timezone_name}")

    sign = normalized_name[3]
    if sign not in {"+", "-"}:
        raise ValueError(f"Invalid birth timezone: {timezone_name}")

    remainder = normalized_name[4:]
    if ":" in remainder:
        hour_text, minute_text = remainder.split(":", 1)
    else:
        hour_text, minute_text = remainder, "0"

    try:
        hours = int(hour_text)
        minutes = int(minute_text)
    except ValueError as error:
        raise ValueError(f"Invalid birth timezone: {timezone_name}") from error

    direction = 1 if sign == "+" else -1
    offset_seconds = direction * ((hours * 60 + minutes) * 60)
    return tz.tzoffset(timezone_name, offset_seconds)


def calculate_equation_of_time_minutes(target_datetime: datetime) -> float:
    """Approximate equation of time in minutes for a given date."""
    day_of_year = target_datetime.timetuple().tm_yday
    b = 2 * math.pi * (day_of_year - 81) / 364
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def normalize_birth_time(person: PersonInfo) -> NormalizedBirthTime:
    """Normalize birth time and optionally apply true solar time correction."""
    input_datetime = create_birth_datetime(
        person.birth_year,
        person.birth_month,
        person.birth_day,
        person.birth_hour,
        person.birth_minute,
    )

    inferred_place = resolve_birth_place_context(person.birth_place)

    timezone_name = (
        person.birth_timezone or inferred_place.timezone or DEFAULT_BIRTH_TIMEZONE
    )
    timezone_info = parse_timezone_name(timezone_name)
    aware_datetime = input_datetime.replace(tzinfo=timezone_info)
    utc_offset = aware_datetime.utcoffset()
    if utc_offset is None:
        raise ValueError(f"Invalid birth timezone: {timezone_name}")

    daylight_saving = aware_datetime.dst() or timedelta(0)
    standard_offset = utc_offset - daylight_saving
    standard_meridian = (standard_offset.total_seconds() / 3600) * 15

    longitude = person.birth_longitude
    longitude_source = "birth_longitude" if longitude is not None else None
    resolved_place = None if longitude is not None else inferred_place.canonical_name
    resolution_level = None if longitude is not None else inferred_place.level
    if longitude is None and inferred_place.longitude is not None:
        longitude = inferred_place.longitude
        longitude_source = inferred_place.source

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
            total_correction_minutes=0.0,
            applied=False,
        )

    if longitude is None:
        raise ValueError(
            "True solar time correction requires birth_longitude or a supported birth_place"
        )

    longitude_correction_minutes = 4 * (longitude - standard_meridian)
    equation_of_time_minutes = calculate_equation_of_time_minutes(input_datetime)
    total_correction_minutes = (
        longitude_correction_minutes + equation_of_time_minutes
    )
    corrected_datetime = input_datetime + timedelta(minutes=total_correction_minutes)

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
        total_correction_minutes=total_correction_minutes,
        applied=True,
    )


def format_birth_datetime_display(
    birth_datetime: datetime, include_minutes: bool = False
) -> str:
    """Format birth datetime for user-facing API responses."""
    if include_minutes:
        return birth_datetime.strftime("%Y年%m月%d日 %H时%M分")
    return birth_datetime.strftime("%Y年%m月%d日 %H时")


def handle_calculation_error(error: Exception, operation: str) -> Dict[str, str]:
    """统一的错误处理函数

    Logs full error server-side but returns generic message to client
    for security reasons.

    Args:
        error: 异常对象
        operation: 操作名称

    Returns:
        包含错误信息的字典（不暴露内部细节）
    """
    logger.error(f"{operation} failed: {str(error)}", exc_info=True)
    return {"error": f"{operation}失败，请重试"}


def create_pillar_dict(pillars: Dict[str, Tuple[str, str]]) -> Dict[str, Dict[str, str]]:
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


def format_json_response(data: Dict[str, Any]) -> str:
    """统一的JSON格式化函数

    Args:
        data: 要格式化的数据字典

    Returns:
        格式化的JSON字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


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
    current_date = datetime.now()

    if analysis_year is None:
        analysis_year = current_date.year
    if analysis_month is None:
        analysis_month = current_date.month

    return analysis_year, analysis_month


def format_error_response(data: Dict[str, Any], operation: str) -> str:
    """格式化错误响应

    Args:
        data: 包含错误信息的字典
        operation: 操作名称

    Returns:
        格式化的错误信息字符串
    """
    if "error" in data:
        return format_json_response({
            "error": data["error"],
            "operation": operation
        })
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
    from fatebridge.utils.data import Element, GENERATION_CYCLE, DESTRUCTION_CYCLE

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
        return {"type": "相同", "description": "同类元素，容易理解对方"}
    elif (
        element1_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相生",
            "description": f"{element1}生{element2}，{element1}方能助{element2}方",
        }
    elif (
        element2_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相生",
            "description": f"{element2}生{element1}，{element2}方能助{element1}方",
        }
    elif (
        element1_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相克",
            "description": f"{element1}克{element2}，{element1}方较为强势",
        }
    elif (
        element2_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相克",
            "description": f"{element2}克{element1}，{element2}方较为强势",
        }
    else:
        return {"type": "无直接关系", "description": "元素间无直接生克关系"}
