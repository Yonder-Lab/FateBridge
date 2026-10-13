"""Request contracts for astrology."""

from __future__ import annotations

from typing import Any, Optional, Union

from pydantic import Field, PrivateAttr, model_validator

from fatebridge.core.requests.base import _DeferredModel
from fatebridge.core.requests.birth import AstroBirthRequest


class AstroChartRequest(AstroBirthRequest):
    """Request model for offline astrology chart generation."""

    gender: Optional[str] = Field(
        default="未知",
        description=(
            "性别（可选，仅用于结果标识；西方星盘计算不使用性别）。接受此字段是为了让"
            "同一套出生信息可以原样喂给八字/紫微/星盘等工具，避免批量调用时'有的工具收、"
            "有的不收'造成的反复试错。"
        ),
    )
    birth_timezone: Optional[str] = Field(  # type: ignore[assignment]
        default=None,
        description=(
            "Birth timezone (IANA name or UTC offset). Optional: when omitted, "
            "FateBridge infers it from birth_place (same as the BaZi/ZiWei "
            "engines) and only falls back to UTC if no place is recognized. The "
            "old 'UTC' default silently treated an eastern wall-clock time as UTC "
            "and rotated the whole chart."
        ),
    )
    birth_longitude: Optional[float] = Field(  # type: ignore[assignment]
        default=None,
        ge=-180,
        le=180,
        description=(
            "Birth longitude. Optional for core chart endpoints when FateBridge can "
            "infer it from a supported birth_place."
        ),
    )
    birth_latitude: Optional[float] = Field(  # type: ignore[assignment]
        default=None,
        ge=-90,
        le=90,
        description=(
            "Birth latitude. Optional for core chart endpoints when FateBridge can "
            "infer it from a supported birth_place."
        ),
    )
    hsys: Optional[int] = Field(
        default=None,
        description=(
            "Optional offline house system override; if omitted, FateBridge keeps each "
            "chart variant's historical default. Explicit values currently support "
            "0=whole_sign, 1=Alcabitus, 2=Regiomontanus, 3=Placidus, 4=Koch, "
            "5=Vehlow Equal, 6=Polich Page, 7=Sripati, 8=equal_mc"
        ),
    )
    zodiacal: Optional[int] = Field(
        default=None,
        description=(
            "Optional offline zodiac override; if omitted, FateBridge keeps each "
            "chart variant's historical default. Explicit values currently support "
            "0=tropical and 1=sidereal(Lahiri-like)"
        ),
    )
    use_true_solar_time: bool = Field(
        default=False,
        alias="useTrueSolarTime",
        description=(
            "Rebase the birth clock onto true solar time (longitude + equation of "
            "time). Default OFF: western astrology conventionally casts on the "
            "recorded civil (zone) clock time. Set true to align the western chart "
            "with the BaZi engine's apparent-solar instant."
        ),
    )


class AstroRelativePartyRequest(AstroBirthRequest):
    """One side of a relative/synastry request."""

    gender: Optional[str] = Field(
        default="未知",
        description="Shared subject label; not used in western chart calculation",
    )
    use_true_solar_time: bool = Field(
        default=False,
        alias="useTrueSolarTime",
        description="Use apparent solar time for this party; defaults to civil time",
    )

    # AstroBirthRequest defaults birth_timezone to "UTC", which silently treats
    # an eastern wall-clock time as UTC and rotates the chart. Mirror the core
    # AstroChartRequest fix: default to None so the engine infers the zone from
    # birth_place and only falls back to UTC when no place is recognized.
    birth_timezone: Optional[str] = Field(  # type: ignore[assignment]
        default=None,
        description=(
            "Birth timezone (IANA name or UTC offset). Optional: when omitted, "
            "FateBridge infers it from birth_place and only falls back to UTC if "
            "no place is recognized."
        ),
    )


class AstroRelativeRequest(_DeferredModel):
    """Request model for relative / synastry chart generation."""

    inner: AstroRelativePartyRequest
    outer: AstroRelativePartyRequest
    _mode_input_source: str = PrivateAttr(default="default")
    relative_mode: Optional[Union[str, int]] = Field(
        default=None,
        description=(
            "Modern relative mode selector, e.g. 0/1/2/3/4, Comp, Composite, "
            "Synastry, TimeSpace, or Marks; when using relative_mode, "
            "Synastry/synastry will resolve to the Horosa-style influence chart"
        ),
    )
    relationship_mode: Optional[Union[str, int]] = Field(
        default=None,
        description=(
            "Legacy alias for relative_mode; relationship_mode='synastry' is "
            "preserved as FateBridge's older compare-mode compatibility path"
        ),
    )
    hsys: int = Field(
        default=3,
        description="House system identifier (0..8 via local Swiss house cusps). "
        "Defaults to Placidus (3) to match the natal chart so a person's natal "
        "and relative charts share one house system.",
    )
    zodiacal: int = Field(
        default=0,
        description="Legacy-compatible zodiac selector; offline mode currently supports 0=tropical and 1=sidereal(Lahiri-like) only",
    )
    relationship_focus: Optional[str] = Field(
        default=None,
        description=(
            "Optional relationship intent lens: marriage/婚姻 (emphasises 7th "
            "house + Sun/Moon/Venus/Saturn) or romance/恋爱 (emphasises 5th "
            "house + Sun/Moon/Venus/Mars). Adds a focus block + intent-filtered "
            "synastry aspects without changing computed aspects; default/unset "
            "is general (no filtering)."
        ),
    )

    def __init__(self, **data: Any):
        mode_source = "default"
        if data.get("relative_mode") not in (None, ""):
            mode_source = "relative_mode"
        elif data.get("relationship_mode") not in (None, ""):
            mode_source = "relationship_mode"
        super().__init__(**data)
        self._mode_input_source = mode_source

    @property
    def mode_input_source(self) -> str:
        return self._mode_input_source

    @model_validator(mode="before")
    @classmethod
    def _sync_relative_mode_aliases(cls, payload: Any) -> Any:
        if not isinstance(payload, dict):
            return payload
        relative_mode = payload.get("relative_mode")
        relationship_mode = payload.get("relationship_mode")
        if relative_mode in (None, "") and relationship_mode not in (None, ""):
            payload["relative_mode"] = relationship_mode
        elif relationship_mode in (None, "") and relative_mode not in (None, ""):
            payload["relationship_mode"] = relative_mode
        elif relative_mode in (None, "") and relationship_mode in (None, ""):
            payload["relative_mode"] = 0
            payload["relationship_mode"] = 0
        return payload


class AstroChartPolyRequest(AstroChartRequest):
    """Polymorphic astro chart request (adds a chart_variant selector)."""

    chart_variant: str = Field(
        default="chart",
        description="Chart variant: chart, chart13, hellen_chart, guolao_chart, india_chart, germany",
    )


class AstroRelativeFlatRequest(_DeferredModel):
    """Flat (non-nested) relative/synastry chart request for tool surfaces."""

    inner_use_true_solar_time: bool = Field(
        default=False, description="Use apparent solar time for the inner chart"
    )
    outer_use_true_solar_time: bool = Field(
        default=False, description="Use apparent solar time for the outer chart"
    )

    inner_birth_year: int = Field(description="Inner chart birth year")
    inner_birth_month: int = Field(ge=1, le=12, description="Inner chart birth month")
    inner_birth_day: int = Field(ge=1, le=31, description="Inner chart birth day")
    inner_birth_hour: int = Field(ge=0, le=23, description="Inner chart birth hour")
    inner_birth_longitude: float = Field(ge=-180, le=180, description="Inner longitude")
    inner_birth_latitude: float = Field(ge=-90, le=90, description="Inner latitude")
    outer_birth_year: int = Field(description="Outer chart birth year")
    outer_birth_month: int = Field(ge=1, le=12, description="Outer chart birth month")
    outer_birth_day: int = Field(ge=1, le=31, description="Outer chart birth day")
    outer_birth_hour: int = Field(ge=0, le=23, description="Outer chart birth hour")
    outer_birth_longitude: float = Field(ge=-180, le=180, description="Outer longitude")
    outer_birth_latitude: float = Field(ge=-90, le=90, description="Outer latitude")
    inner_name: Optional[str] = Field(default="内盘", description="Inner chart name")
    outer_name: Optional[str] = Field(default="外盘", description="Outer chart name")
    inner_birth_place: Optional[str] = Field(
        default="未提供", description="Inner birth place"
    )
    outer_birth_place: Optional[str] = Field(
        default="未提供", description="Outer birth place"
    )
    relationship_mode: Optional[Union[str, int]] = Field(
        default=None, description="Legacy relative mode alias"
    )
    relative_mode: Optional[Union[str, int]] = Field(
        default=None, description="Modern relative mode selector"
    )
    inner_birth_minute: int = Field(
        default=0, ge=0, le=59, description="Inner birth minute"
    )
    outer_birth_minute: int = Field(
        default=0, ge=0, le=59, description="Outer birth minute"
    )
    inner_birth_timezone: Optional[str] = Field(
        default=None,
        description=(
            "Inner timezone (IANA name or UTC offset). Optional: when omitted, "
            "FateBridge infers it from inner_birth_place and only falls back to "
            "UTC if no place is recognized. A hardcoded 'UTC' default silently "
            "treated an eastern wall-clock time as UTC and rotated the chart."
        ),
    )
    outer_birth_timezone: Optional[str] = Field(
        default=None,
        description=(
            "Outer timezone (IANA name or UTC offset). Optional: when omitted, "
            "FateBridge infers it from outer_birth_place and only falls back to "
            "UTC if no place is recognized. A hardcoded 'UTC' default silently "
            "treated an eastern wall-clock time as UTC and rotated the chart."
        ),
    )
    hsys: int = Field(
        default=3,
        description="House system identifier (0..8). Defaults to Placidus (3) to "
        "match the natal chart.",
    )
    zodiacal: int = Field(default=0, description="Zodiac selector")
    relationship_focus: Optional[str] = Field(
        default=None,
        description=(
            "Optional relationship intent lens: marriage/婚姻 or romance/恋爱; "
            "adds a focus block + intent-filtered synastry aspects. Default/unset "
            "is general (no filtering)."
        ),
    )
