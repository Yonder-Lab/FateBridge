"""Person input validation, gender normalization and civil birth datetime construction."""

import logging
from calendar import monthrange
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator

logger = logging.getLogger(__name__)


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
