"""
Shared utility functions and models for FateBridge.
This module centralizes common functions used across api.py and fastmcp_server.py.
"""

import json
import logging
from calendar import monthrange
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


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
    gender: Optional[str] = Field(default="未知", description="性别（可选）")
    birth_place: Optional[str] = Field(default="未提供", description="出生地（可选）")

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

    Returns:
        PersonInfo对象
    """
    return PersonInfo(
        name=name,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        gender=gender,
        birth_place=birth_place,
    )


def create_birth_datetime(
    birth_year: int, birth_month: int, birth_day: int, birth_hour: int
) -> datetime:
    """创建出生时间datetime对象的工具函数

    Args:
        birth_year: 出生年份
        birth_month: 出生月份
        birth_day: 出生日期
        birth_hour: 出生时辰

    Returns:
        datetime对象

    Raises:
        ValueError: 如果日期无效
    """
    try:
        return datetime(birth_year, birth_month, birth_day, birth_hour)
    except ValueError as e:
        error_msg = f"Invalid birth date: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_hour:02d}:00"
        logger.warning(error_msg)
        raise ValueError(error_msg) from e


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
