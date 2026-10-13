"""Request contracts for compatibility."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from fatebridge.core.requests.base import _DeferredModel


class TwoPersonCompatibilityRequest(_DeferredModel):
    """Request model for two-person compatibility analysis."""

    person1_name: str = Field(description="First person name")
    person1_birth_year: int = Field(description="First person birth year, e.g., 1990")
    person1_birth_month: int = Field(
        ge=1, le=12, description="First person birth month"
    )
    person1_birth_day: int = Field(ge=1, le=31, description="First person birth day")
    person1_birth_hour: int = Field(ge=0, le=23, description="First person birth hour")
    person1_gender: str = Field(
        default="未知",
        description=(
            "第一人性别（影响大运顺逆与部分六亲判断）。"
            "接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法；省略默认 未知。"
        ),
    )
    person1_birth_place: str = Field(
        default="未提供", description="First person birth place"
    )
    person1_birth_minute: int = Field(
        default=0, ge=0, le=59, description="First person birth minute"
    )
    person1_birth_timezone: Optional[str] = Field(
        default=None, description="First person birth timezone"
    )
    person1_birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="First person birth longitude"
    )
    person1_use_true_solar_time: bool = Field(
        default=True,
        description="Enable true solar time for first person (八字 default on)",
    )
    person2_name: str = Field(description="Second person name")
    person2_birth_year: int = Field(description="Second person birth year, e.g., 1992")
    person2_birth_month: int = Field(
        ge=1, le=12, description="Second person birth month"
    )
    person2_birth_day: int = Field(ge=1, le=31, description="Second person birth day")
    person2_birth_hour: int = Field(ge=0, le=23, description="Second person birth hour")
    person2_gender: str = Field(
        default="未知",
        description=(
            "第二人性别（影响大运顺逆与部分六亲判断）。"
            "接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法；省略默认 未知。"
        ),
    )
    person2_birth_place: str = Field(
        default="未提供", description="Second person birth place"
    )
    person2_birth_minute: int = Field(
        default=0, ge=0, le=59, description="Second person birth minute"
    )
    person2_birth_timezone: Optional[str] = Field(
        default=None, description="Second person birth timezone"
    )
    person2_birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Second person birth longitude"
    )
    person2_use_true_solar_time: bool = Field(
        default=True,
        description="Enable true solar time for second person (八字 default on)",
    )
    relationship_type: str = Field(
        default="general",
        description=(
            "关系类型：general / marriage / friendship / business / family。"
            "用户未说明关系时保留 general；不能因两人性别或‘我们两个人’推断为婚姻。"
        ),
    )


class SukuyoCompatibilityRequest(_DeferredModel):
    """Request model for 宿曜 two-person compatibility (三九の秘法).

    Each person is located by their suzhan-style birth event; the natal 宿
    is the mansion of the Moon, kept identical to the suzhan tool.
    """

    person1_name: str = Field(default="甲方", description="First person name / label")
    person1_date: str = Field(description="First person birth date, e.g. 1990-06-15")
    person1_time: str = Field(description="First person birth time, e.g. 08:30:00")
    person1_zone: Optional[str] = Field(
        default="+08:00", description="First person timezone spec"
    )
    person1_lat: Optional[str] = Field(
        default="31n13", description="First person latitude text or decimal"
    )
    person1_lon: Optional[str] = Field(
        default="121e28", description="First person longitude text or decimal"
    )
    person1_gps_lat: Optional[float] = Field(
        default=None, description="First person GPS latitude"
    )
    person1_gps_lon: Optional[float] = Field(
        default=None, description="First person GPS longitude"
    )
    person2_name: str = Field(default="乙方", description="Second person name / label")
    person2_date: str = Field(description="Second person birth date")
    person2_time: str = Field(description="Second person birth time")
    person2_zone: Optional[str] = Field(
        default="+08:00", description="Second person timezone spec"
    )
    person2_lat: Optional[str] = Field(
        default="31n13", description="Second person latitude text or decimal"
    )
    person2_lon: Optional[str] = Field(
        default="121e28", description="Second person longitude text or decimal"
    )
    person2_gps_lat: Optional[float] = Field(
        default=None, description="Second person GPS latitude"
    )
    person2_gps_lon: Optional[float] = Field(
        default=None, description="Second person GPS longitude"
    )
