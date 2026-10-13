"""Request contracts for metaphysics."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from fatebridge.core.requests.base import _DeferredModel
from fatebridge.core.requests.birth import FateBridgeRequest


class ZiweiBirthRequest(FateBridgeRequest):
    """Request model for Zi Wei birth chart analysis."""

    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class ZiweiHoroscopeRequest(FateBridgeRequest):
    """Request model for 紫微斗数 horoscope (运限) at a target date-time."""

    target_year: int = Field(description="Target year, e.g., 2026")
    target_month: int = Field(ge=1, le=12, description="Target month (1-12)")
    target_day: int = Field(ge=1, le=31, description="Target day (1-31)")
    target_hour: int = Field(ge=0, le=23, description="Target hour (0-23)")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class ZiweiRulesRequest(_DeferredModel):
    """Request model for Zi Wei rule catalogue lookup."""

    year_stem: Optional[str] = Field(
        default=None,
        description="Optional heavenly stem filter, e.g. 甲",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiuRengGodsRequest(_DeferredModel):
    """Request model for Liu Ren divination."""

    analysis_year: int = Field(description="Analysis year, e.g., 2026")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    analysis_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Analysis longitude"
    )
    gender: Optional[str] = Field(
        default="未知",
        description=(
            "性别（可选）。接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法；"
            "省略默认 未知。"
        ),
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Enable true solar time correction (default on — 式占 keys off the apparent-solar 时辰)",
    )


class LiuRengRunyearRequest(FateBridgeRequest):
    """Request model for Liu Ren runyear analysis."""

    analysis_year: int = Field(description="Analysis year, e.g., 2026")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    analysis_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Analysis longitude"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class QimenAnalysisRequest(_DeferredModel):
    """Request model for Qi Men analysis."""

    analysis_year: int = Field(description="Analysis year, e.g., 2026")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    analysis_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Analysis longitude"
    )
    qimen_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional qimen settings like layout or palaceShift",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Enable true solar time correction (default on — 奇门 定局 keys off the apparent-solar 时辰)",
    )


class TaiyiAnalysisRequest(_DeferredModel):
    """Request model for Taiyi analysis.

    太乙 does NOT take 奇门's ``qimen_options`` (layout/palaceShift) — it used to
    inherit ``QimenAnalysisRequest`` purely to reuse the date/time fields, which
    leaked ``qimen_options`` onto the 太乙 schema where it is meaningless. The
    fields below are exactly what ``calculate_taiyi_analysis`` consumes.
    """

    analysis_year: int = Field(description="Analysis year, e.g., 2026")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    analysis_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Analysis longitude"
    )
    gender: Optional[str] = Field(
        default="未知",
        description=(
            "性别（可选）。接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法；"
            "省略默认 未知。"
        ),
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Enable true solar time correction (default on — 太乙 定局 keys off the apparent-solar 时辰)",
    )


class JinkouAnalysisRequest(LiuRengGodsRequest):
    """Request model for Jin Kou analysis."""

    di_fen: Optional[str] = Field(default=None, description="Ground division branch")
