"""Request contracts for birth."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict, Field

from fatebridge.core.requests.base import _DeferredModel


class FateBridgeRequest(_DeferredModel):
    """Request model for individual destiny analysis"""

    name: Optional[str] = Field(
        default="未提供",
        description="姓名（可选，仅用于结果快照中的标识，不参与计算）",
    )
    gender: Optional[str] = Field(
        default="未知",
        description=(
            "性别（可选但建议提供：影响大运顺逆排布与部分六亲判断）。"
            "接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法。"
        ),
    )
    birth_year: int = Field(description="Birth year, e.g., 1990")
    birth_month: int = Field(ge=1, le=12, description="Birth month (1-12)")
    birth_day: int = Field(ge=1, le=31, description="Birth day (1-31)")
    birth_hour: int = Field(ge=0, le=23, description="Birth hour (0-23)")
    birth_minute: int = Field(default=0, ge=0, le=59, description="Birth minute (0-59)")
    birth_place: Optional[str] = Field(
        default="未提供", description="Birth place (optional)"
    )
    birth_timezone: Optional[str] = Field(
        default=None, description="Birth timezone (IANA name or UTC offset)"
    )
    birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Birth longitude (optional)"
    )
    use_true_solar_time: bool = Field(
        default=True,
        description=(
            "Rebase the birth clock onto true solar time (longitude + equation of "
            "time). Default on: 八字/紫微 traditionally define the hour pillar / "
            "命宫 from apparent solar time. Set false for the raw civil clock."
        ),
    )


class AstroBirthRequest(_DeferredModel):
    """Base birth request model for offline astrology endpoints."""

    # Accept both the Python field name (``use_true_solar_time``) and the JSON
    # alias (``useTrueSolarTime``). Without this, alias-only population means the
    # CLI/MCP surfaces — which bind by Python field name — silently drop
    # ``use_true_solar_time`` and fall back to its default, so the documented
    # ``--no-use-true-solar-time`` / ``--use-true-solar-time false`` switches
    # could never turn the correction off.
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(default="未提供", description="Name (optional)")
    birth_year: int = Field(description="Birth year, e.g., 1990")
    birth_month: int = Field(ge=1, le=12, description="Birth month (1-12)")
    birth_day: int = Field(ge=1, le=31, description="Birth day (1-31)")
    birth_hour: int = Field(ge=0, le=23, description="Birth hour (0-23)")
    birth_minute: int = Field(default=0, ge=0, le=59, description="Birth minute (0-59)")
    birth_timezone: Optional[str] = Field(
        default=None,
        description=(
            "Birth timezone (IANA name or UTC offset). Optional: when omitted, "
            "FateBridge infers it from birth_place (same as the BaZi/ZiWei engines) "
            "and only falls back to UTC if no place is recognized. The default is "
            "None — never 'UTC' — because a truthy 'UTC' default silently treats an "
            "eastern wall-clock time as UTC and rotates the whole chart; every "
            "subclass (chart / relative / timing / lifespan) therefore inherits the "
            "safe place-inference behavior automatically."
        ),
    )
    birth_longitude: float = Field(ge=-180, le=180, description="Birth longitude")
    birth_latitude: float = Field(ge=-90, le=90, description="Birth latitude")
    birth_place: Optional[str] = Field(default="未提供", description="Birth place")
