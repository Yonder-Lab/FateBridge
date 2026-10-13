"""Request contracts for calendar."""

from __future__ import annotations

from typing import List, Optional

from pydantic import ConfigDict, Field

from fatebridge.core.requests.base import _DeferredModel


class JieqiYearRequest(_DeferredModel):
    """Request model for annual jieqi helper output."""

    model_config = ConfigDict(populate_by_name=True)

    year: int = Field(description="Target year, e.g. 2028")
    zone: Optional[str] = Field(default="Asia/Shanghai", description="Timezone spec")
    lat: Optional[str] = Field(default=None, description="Latitude text hint")
    lon: Optional[str] = Field(default=None, description="Longitude text hint")
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    jieqis: List[str] = Field(
        default_factory=list, description="Optional focused jieqi names"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class NongliTimeRequest(_DeferredModel):
    """Request model for nongli-time helper output."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-01")
    time: str = Field(description="Time string, e.g. 09:00:00")
    zone: Optional[str] = Field(default="Asia/Shanghai", description="Timezone spec")
    lat: Optional[str] = Field(default=None, description="Latitude text hint")
    lon: Optional[str] = Field(default=None, description="Longitude text hint")
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    gender: Optional[str] = Field(
        default=None,
        description=(
            "性别（可选，仅作元数据透传回显，不参与农历/节气/干支计算）。"
            "接受 男/女、male/female/m/f 等写法；省略则不回显。"
        ),
    )
    after23_new_day: bool = Field(
        default=False,
        alias="after23NewDay",
        description="Whether 23:00 counts as next day",
    )
    time_alg: int = Field(
        default=0,
        alias="timeAlg",
        description="Time algorithm: 0=true solar time (requires longitude), 1=direct clock time",
    )
    ad: int = Field(
        default=1,
        description="Common era flag; offline nongli conversion supports ad=1 only within 1900-01-31 to 2100-02-08",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
