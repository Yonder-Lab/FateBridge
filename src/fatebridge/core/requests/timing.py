"""Request contracts for timing."""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from fatebridge.core.requests.birth import FateBridgeRequest


class TimingAnalysisRequest(FateBridgeRequest):
    """Request model for comprehensive timing analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    analysis_hour: Optional[int] = Field(
        default=None, ge=0, le=23, description="Analysis hour (0-23)"
    )
    analysis_minute: Optional[int] = Field(
        default=None, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_age: Optional[int] = Field(
        default=None, ge=0, description="Analysis age override"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class DayunAnalysisRequest(FateBridgeRequest):
    """Request model for dayun analysis."""

    gender: str = Field(
        description=(
            "性别（必填：决定大运顺逆/起运方向，无法以默认值替代）。"
            "接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法。"
        )
    )
    analysis_age: int = Field(ge=0, description="Analysis age")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiunianAnalysisRequest(FateBridgeRequest):
    """Request model for liunian analysis."""

    target_year: int = Field(description="Target analysis year")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiuriAnalysisRequest(FateBridgeRequest):
    """Request model for liuri analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    analysis_hour: Optional[int] = Field(
        default=None, ge=0, le=23, description="Analysis hour (0-23)"
    )
    analysis_minute: Optional[int] = Field(
        default=None, ge=0, le=59, description="Analysis minute (0-59)"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiushiAnalysisRequest(FateBridgeRequest):
    """Request model for liushi analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    analysis_hour: Optional[int] = Field(
        default=None, ge=0, le=23, description="Analysis hour (0-23)"
    )
    analysis_minute: Optional[int] = Field(
        default=None, ge=0, le=59, description="Analysis minute (0-59)"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class JieqiTimelineRequest(FateBridgeRequest):
    """Request model for jieqi timeline analysis."""

    target_year: Optional[int] = Field(default=None, description="Target year")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiuyueAnalysisRequest(FateBridgeRequest):
    """Request model for liuyue analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    analysis_hour: Optional[int] = Field(
        default=None, ge=0, le=23, description="Analysis hour (0-23)"
    )
    analysis_minute: Optional[int] = Field(
        default=None, ge=0, le=59, description="Analysis minute (0-59)"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
