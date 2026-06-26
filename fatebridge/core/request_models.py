"""
FateBridge request models (Pydantic).

Extracted from api.py into a neutral module so that the central tool catalog,
the REST app, and other surfaces can all import them without circular imports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator


class FateBridgeRequest(BaseModel):
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


class BaziDimensionRequest(FateBridgeRequest):
    """Shared base for BaZi single-dimension analyses.

    大运/流年默认由命盘 + 分析日期内部推算（analysis_* 缺省为今天），用户无需自己
    知道大运；dayun_pillar / liunian_pillar 为可选覆盖。
    """

    analysis_year: Optional[int] = Field(
        default=None, description="Analysis year (defaults to current year)"
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    dayun_pillar: Optional[str] = Field(
        default=None, description="Optional override: current dayun pillar, e.g. '甲子'"
    )
    liunian_pillar: Optional[str] = Field(
        default=None,
        description="Optional override: current liunian pillar, e.g. '丙寅'",
    )


class BaziBirthRequest(FateBridgeRequest):
    """Request model for standalone BaZi birth output."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class TwoPersonCompatibilityRequest(BaseModel):
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
        default="general", description="Relationship type, e.g. marriage or business"
    )


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


class MeihuaAnalysisRequest(BaseModel):
    """Request model for time-seeded Mei Hua Yi Shu analysis."""

    analysis_year: int = Field(description="Analysis year, e.g., 2028")
    analysis_month: int = Field(ge=1, le=12, description="Analysis month (1-12)")
    analysis_day: int = Field(ge=1, le=31, description="Analysis day (1-31)")
    analysis_hour: int = Field(ge=0, le=23, description="Analysis hour (0-23)")
    analysis_minute: int = Field(
        default=0, ge=0, le=59, description="Analysis minute (0-59)"
    )
    analysis_timezone: Optional[str] = Field(
        default=None, description="Analysis timezone (IANA name or UTC offset)"
    )
    question: Optional[str] = Field(
        default=None, description="Question or topic for the divination context"
    )


class GuaLookupRequest(BaseModel):
    """Request model for trigram/hexagram lookup."""

    query: str = Field(description="Hexagram/trigram name or binary code")
    lookup_mode: str = Field(
        default="auto",
        description="Lookup mode: auto, hexagram, or trigram",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class JieqiYearRequest(BaseModel):
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


class NongliTimeRequest(BaseModel):
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


class GuaMeiyiRequest(BaseModel):
    """Request model for batch Meiyi hexagram meanings."""

    name: List[str] = Field(description="Trigram or hexagram names/codes")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class ExportRegistryRequest(BaseModel):
    """Request model for export registry lookup."""

    technique: Optional[str] = Field(default=None, description="Optional technique key")


class ExportParseRequest(BaseModel):
    """Request model for export snapshot parsing."""

    model_config = ConfigDict(populate_by_name=True)

    technique: str = Field(description="Technique key, e.g. qimen")
    content: str = Field(description="Snapshot text content")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional selected section titles",
    )
    planet_info: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="planetInfo",
        description="Optional planet info export toggles",
    )
    astro_meaning: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="astroMeaning",
        description="Optional astro meaning export toggles",
    )


class KnowledgeRegistryRequest(BaseModel):
    """Request model for bundled knowledge registry."""

    domain: Optional[str] = Field(default=None, description="Optional domain filter")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class KnowledgeReadRequest(BaseModel):
    """Request model for bundled knowledge lookup."""

    domain: str = Field(
        description=(
            "知识域：astro / bazi / liureng / qimen。各域适用字段不同——"
            "astro：key 或 (object_a, object_b[, aspect_degree])；"
            "bazi / qimen：key（category 可省略，自动解析）；"
            "liureng：(jiang_name, tian_branch, di_branch)。"
        )
    )
    category: Optional[str] = Field(
        default=None,
        description=(
            "Category within the domain. Optional: if omitted, it is auto-resolved "
            "from `key` (astro/bazi/qimen only)."
        ),
    )
    key: Optional[str] = Field(default=None, description="Primary lookup key")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    aspect_degree: Optional[int] = Field(
        default=None,
        description="[domain=astro] 相位角度（可选，用于 astro 相位查询）",
    )
    object_a: Optional[str] = Field(
        default=None, description="[domain=astro] 第一星体（相位查询）"
    )
    object_b: Optional[str] = Field(
        default=None, description="[domain=astro] 第二星体（相位查询）"
    )
    jiang_name: Optional[str] = Field(
        default=None, description="[domain=liureng] 贵神名"
    )
    tian_branch: Optional[str] = Field(
        default=None, description="[domain=liureng] 天盘地支"
    )
    di_branch: Optional[str] = Field(
        default=None, description="[domain=liureng] 地盘地支"
    )


class TongSheFaRequest(BaseModel):
    """Request model for tongshefa."""

    taiyin: Optional[str] = Field(default="巽", description="Taiyin trigram")
    taiyang: Optional[str] = Field(default="坤", description="Taiyang trigram")
    shaoyang: Optional[str] = Field(default="震", description="Shaoyang trigram")
    shaoyin: Optional[str] = Field(default="震", description="Shaoyin trigram")


class SixYaoLineRequest(BaseModel):
    """One six-yao line item."""

    value: int = Field(ge=0, le=1, description="0 for yin, 1 for yang")
    change: bool = Field(default=False, description="Whether the line is moving")
    god: Optional[str] = Field(default=None, description="Optional six-god label")
    name: Optional[str] = Field(default=None, description="Optional line label")


class SixYaoRequest(BaseModel):
    """Request model for sixyao."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    question: Optional[str] = Field(default=None, description="Question or topic")
    gua_code: Optional[str] = Field(default=None, description="Current hexagram code")
    changed_code: Optional[str] = Field(
        default=None, description="Changed hexagram code"
    )
    lines: List[SixYaoLineRequest] = Field(
        default_factory=list, description="Optional six lines"
    )


class SuZhanRequest(BaseModel):
    """Request model for suzhan."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    szchart: int = Field(
        default=0, description="宿占盘模式开关（透传至宿曜引擎；默认 0）"
    )
    szshape: int = Field(
        default=0, description="宿占盘形态开关（透传至宿曜引擎；默认 0）"
    )
    house_start_mode: int = Field(
        default=1,
        alias="houseStartMode",
        description="宫位起始模式（透传至宿曜引擎；默认 1）",
    )
    doubing_su28: bool = Field(
        default=True,
        alias="doubingSu28",
        description="是否按斗柄(doubing)标注二十八宿(su28)；默认开启",
    )
    hsys: int = Field(
        default=8,
        description="Offline house system selector; standard suzhan supports 0..8 with the same FateBridge local house semantics as core chart",
    )
    zodiacal: int = Field(
        default=0,
        description="Offline zodiac selector; standard suzhan supports 0=tropical and 1=sidereal(Lahiri-like)",
    )


class CanpingRequest(BaseModel):
    """Request model for canping (邵子参评数 / 金锁银匙)."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Birth date string, e.g. 1990-06-15")
    time: str = Field(description="Birth time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(
        default=None, description="Latitude text or decimal (optional)"
    )
    lon: Optional[str] = Field(
        default=None,
        description="Longitude text or decimal; required when true solar time is on",
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    gender: Optional[str] = Field(
        default="男",
        description=(
            "性别 男/女 — 选择本命男/女断语。接受 男/女、male/female 等写法；"
            "省略默认按男命（男）起盘。"
        ),
    )
    method: str = Field(
        default="ming",
        description="取法: ming 明法(月支反向取日宫支) or gu 古法(八字日支)",
    )
    use_true_solar_time: bool = Field(
        default=True,
        alias="useTrueSolarTime",
        description="Apply true solar time correction (needs lon); default on — 数算 derives from the BaZi pillars",
    )


class HeluoRequest(BaseModel):
    """Request model for heluo (河洛理数)."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Birth date string, e.g. 1990-06-15")
    time: str = Field(description="Birth time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(
        default=None, description="Latitude text or decimal (optional)"
    )
    lon: Optional[str] = Field(
        default=None,
        description="Longitude text or decimal; required when true solar time is on",
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    gender: Optional[str] = Field(
        default="男",
        description=(
            "性别 男/女 — 影响起命相盪与元堂推导。接受 男/女、male/female 等写法；"
            "省略默认按男命（男）起盘。"
        ),
    )
    use_true_solar_time: bool = Field(
        default=True,
        alias="useTrueSolarTime",
        description="Apply true solar time correction (needs lon); default on — 数算 derives from the BaZi pillars",
    )


class SukuyoCompatibilityRequest(BaseModel):
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


class OtherBuRequest(BaseModel):
    """Request model for otherbu."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    tradition: bool = Field(
        default=False, description="Traditional mode without outer planets"
    )
    sign: Optional[str] = Field(default="Aries", description="Dice sign")
    house: int = Field(default=0, ge=0, le=11, description="Dice house index (0-11)")
    planet: Optional[str] = Field(default="Sun", description="Dice planet")
    hsys: int = Field(
        default=8,
        description="Offline house system selector; supports 0..8 via local Swiss house cusps",
    )
    zodiacal: int = Field(
        default=0,
        description="Offline zodiac selector; supports 0=tropical and 1=sidereal(Lahiri-like)",
    )
    question: Optional[str] = Field(default=None, description="Question or topic")


class SanShiUnitedRequest(BaseModel):
    """Request model for sanshiunited."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(
        default="121e28", description="Longitude text or decimal"
    )
    gps_lat: Optional[float] = Field(
        default=None, alias="gpsLat", description="GPS latitude"
    )
    gps_lon: Optional[float] = Field(
        default=None, alias="gpsLon", description="GPS longitude"
    )
    qimen_options: Dict[str, Any] = Field(
        default_factory=dict,
        alias="qimen_options",
        description="Optional qimen settings",
    )
    taiyi_options: Dict[str, Any] = Field(
        default_factory=dict,
        alias="taiyi_options",
        description="Optional taiyi settings",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    liureng_yue: Optional[str] = Field(
        default=None,
        alias="liureng_yue",
        description="Optional liureng month-general override",
    )
    liureng_is_diurnal: Optional[bool] = Field(
        default=None,
        alias="liureng_isDiurnal",
        description="Optional liureng day/night override",
    )
    use_true_solar_time: bool = Field(
        default=True,
        description="Enable local true solar time correction before sanshi aggregation (default on — 式占 keys off the apparent-solar 时辰)",
    )


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


class ZiweiRulesRequest(BaseModel):
    """Request model for Zi Wei rule catalogue lookup."""

    year_stem: Optional[str] = Field(
        default=None,
        description="Optional heavenly stem filter, e.g. 甲",
    )
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )


class LiuRengGodsRequest(BaseModel):
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


class QimenAnalysisRequest(BaseModel):
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


class TaiyiAnalysisRequest(QimenAnalysisRequest):
    """Request model for Taiyi analysis."""

    gender: Optional[str] = Field(
        default="未知",
        description=(
            "性别（可选）。接受 男/女、male/female/m/f、阳/阴、乾/坤 等写法；"
            "省略默认 未知。"
        ),
    )


class JinkouAnalysisRequest(LiuRengGodsRequest):
    """Request model for Jin Kou analysis."""

    di_fen: Optional[str] = Field(default=None, description="Ground division branch")


class AstroBirthRequest(BaseModel):
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


class AstroRelativeRequest(BaseModel):
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


class WesternTimingRequest(AstroBirthRequest):
    """Request model for western predictive timing analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
    )
    return_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Return chart longitude"
    )
    return_latitude: Optional[float] = Field(
        default=None, ge=-90, le=90, description="Return chart latitude"
    )
    return_timezone: Optional[str] = Field(
        default=None, description="Return chart timezone (IANA name or UTC offset)"
    )
    house_system: Union[int, str] = Field(
        default="P",
        description="House system, any convention: SE letter ('P'=Placidus, "
        "'R'=Regiomontanus, 'W'=whole sign, 'D'=equal_mc), key ('placidus', "
        "'equal_mc'), or integer code 0..8 (3=Placidus, 8=equal_mc).",
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )
    pd_method: str = Field(
        default="astroapp_alchabitius",
        description=(
            "Primary direction method identifier, e.g. astroapp_alchabitius, "
            "legacy_reference / legacy_equatorial, or fatebridge_mundane_semiarc"
        ),
    )
    pd_time_key: str = Field(
        default="Ptolemy",
        description="Primary direction time key, e.g. Ptolemy or Naibod",
    )
    pd_type: int = Field(
        default=0,
        ge=0,
        le=1,
        description="Primary direction mode: 0 for direct, 1 for converse",
    )
    pd_aspects: List[int] = Field(
        default_factory=lambda: [0, 60, 90, 120, 180],
        description="Primary direction aspects in degrees",
    )
    show_pd_bounds: bool = Field(
        default=True,
        description="Whether to expose the bounds overlay preference for the primary direction chart",
    )


class WesternTimingModuleRequest(WesternTimingRequest):
    """Request model for standalone western timing module tools."""

    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional export sections to keep in snapshot_export",
    )


class AstroLifespanRequest(AstroBirthRequest):
    """Shared base for western *lifespan* techniques cast from a single natal chart."""

    house_system: Union[int, str] = Field(
        default="P",
        description="House system, any convention: SE letter ('P'=Placidus, "
        "'R'=Regiomontanus, 'W'=whole sign, 'D'=equal_mc), key ('placidus', "
        "'equal_mc'), or integer code 0..8 (3=Placidus, 8=equal_mc).",
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )


class AstroHarmonicRequest(AstroLifespanRequest):
    """Request model for the 调波盘 (harmonic chart) tool."""

    harmonic: int = Field(
        default=9,
        ge=1,
        le=360,
        description="Harmonic number H (1-360); natal longitudes are multiplied by H mod 360",
    )
    orb: float = Field(
        default=2.0,
        ge=0,
        le=15,
        description="Conjunction orb in degrees for detecting 同频合相 (harmonic conjunctions)",
    )


class AstroPlanetaryAgesRequest(AstroLifespanRequest):
    """Request model for the 行星年龄 (Ptolemy seven ages) tool."""

    analysis_year: Optional[int] = Field(
        default=None,
        description="Reference year; with month/day, flags the active age band (omit to list all bands)",
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Reference month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Reference day (1-31)"
    )


class AstroTriplicityRulersRequest(AstroLifespanRequest):
    """Request model for the 三分主星推运 (triplicity rulers) tool."""

    lifespan: float = Field(
        default=75.0,
        gt=0,
        le=200,
        description="Nominal lifespan (years) the stages divide — a dividing convention, not a prediction",
    )
    division: str = Field(
        default="thirds",
        description="Stage split: 'thirds' (three equal stages) or 'halves' (main/secondary halves + participating throughout)",
    )


class AstroLunationPhaseRequest(AstroLifespanRequest):
    """Request model for the 月相推运 (progressed lunation phase) tool."""

    max_age_years: float = Field(
        default=90.0,
        gt=0,
        le=200,
        description="Upper age bound (years) for the phase-ingress timeline",
    )


class AstroDistributionsRequest(AstroLifespanRequest):
    """Request model for the 界推运 / 分配法 (distributions) tool."""

    time_key: str = Field(
        default="Ptolemy",
        description="Time key for directing the Ascendant: Ptolemy (1°/yr) or Naibod",
    )
    max_age_years: float = Field(
        default=90.0,
        gt=0,
        le=200,
        description="Upper age bound (years) for the distribution timeline",
    )


class AstroBalbillusRequest(AstroLifespanRequest):
    """Request model for the Balbillus 129年系统 tool."""

    start_planet: str = Field(
        default="Sun",
        description="Starting planet for the period chain (Sun/Moon/Mercury/Venus/Mars/Jupiter/Saturn)",
    )
    mode: str = Field(
        default="nearest",
        description="Exaltation-distance mode: 'nearest' (with reduction fit) or 'forward'",
    )
    max_age_years: float = Field(
        default=120.0,
        gt=0,
        le=200,
        description="Upper age bound (years) for the period table",
    )


class AstroKeypointsRequest(AstroLifespanRequest):
    """Request model for the 数字相位推运 (120-year keypoints) tool."""

    release_mode: str = Field(
        default="soul",
        description="Release point: 'soul' (from the Moon) or 'body' (from the Ascendant)",
    )
    max_age_years: int = Field(
        default=120,
        ge=1,
        le=120,
        description="Upper age bound (years, capped at 120) for the activation timeline",
    )


class AstroYearSystem129Request(AstroLifespanRequest):
    """Request model for the 129年系统 tool."""

    start_planet: str = Field(
        default="Sun",
        description="Starting planet for the small-year rotation (Sun/Moon/Mercury/Venus/Mars/Jupiter/Saturn)",
    )
    max_age_years: float = Field(
        default=129.0,
        gt=0,
        le=200,
        description="Upper age bound (years) for the rotation timeline",
    )


class AstroPlanetaryArcRequest(AstroLifespanRequest):
    """Request model for the 行星弧方向 (planetary arc directions) tool."""

    arc_source: str = Field(
        default="Moon",
        description="Body whose secondary-progressed arc directs the whole chart (default Moon)",
    )
    orb: float = Field(
        default=1.0,
        ge=0,
        le=15,
        description="Aspect orb in degrees for directed-to-natal hits",
    )
    analysis_year: Optional[int] = Field(
        default=None, description="Direction target year (omit for current date)"
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Direction target month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Direction target day (1-31)"
    )


class AstroPersianDirectedRequest(AstroLifespanRequest):
    """Request model for the 波斯向运 (Persian Directed) tool."""

    max_age_years: float = Field(
        default=90.0,
        gt=0,
        le=200,
        description="Upper age bound (years) for the symbolic 1°/year hit list",
    )


class AstroAgePointRequest(AstroLifespanRequest):
    """Request model for the 年龄推进点 (Age Point / Huber) tool.

    Huber's Age Point is defined on Koch houses, so the tool always casts Koch
    regardless of ``house_system``; the inherited field is accepted but ignored.
    """

    max_age_years: float = Field(
        default=72.0,
        gt=0,
        le=200,
        description="Upper age bound (years); one full Age Point cycle is 72 years",
    )


class AstroVedicProgRequest(AstroLifespanRequest):
    """Request model for the 恒星推运 (Vedic sidereal secondary progression) tool.

    The technique is read sidereally, so the tool always casts Sidereal regardless
    of ``zodiac_type``; the inherited field is accepted but ignored.
    """

    orb: float = Field(
        default=1.5,
        ge=0,
        le=15,
        description="Aspect orb (degrees) for progressed→natal hits",
    )
    analysis_year: Optional[int] = Field(
        default=None, description="Progression target year (omit for current date)"
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Progression target month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Progression target day (1-31)"
    )


class AstroJaynesProgRequest(AstroLifespanRequest):
    """Request model for the 赤纬推运 (Jayne declination progression) tool."""

    orb: float = Field(
        default=1.0, ge=0, le=5, description="Declination orb (degrees) for parallels"
    )
    analysis_year: Optional[int] = Field(
        default=None, description="Progression target year (omit for current date)"
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Progression target month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Progression target day (1-31)"
    )


class AstroMundaneRequest(BaseModel):
    """Request model for the 世俗入宫盘 (mundane ingress) tool — cast at a solar ingress, no birth data."""

    name: Optional[str] = Field(default=None, description="Optional chart name")
    year: int = Field(description="Civil year of the ingress, e.g. 2026")
    ingress_term: str = Field(
        default="春分",
        description="Cardinal ingress: 春分 (spring equinox) / 夏至 / 秋分 / 冬至",
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        description="Observation longitude (e.g. capital / place of interest)",
    )
    latitude: float = Field(ge=-90, le=90, description="Observation latitude")
    timezone_name: str = Field(
        default="+08:00", description="Observation timezone (IANA name or UTC offset)"
    )
    house_system: Union[int, str] = Field(
        default="P",
        description="House system, any convention: SE letter ('P'=Placidus, "
        "'R'=Regiomontanus, 'W'=whole sign, 'D'=equal_mc), key ('placidus', "
        "'equal_mc'), or integer code 0..8 (3=Placidus, 8=equal_mc).",
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )


class AstroExtraReturnsRequest(AstroLifespanRequest):
    """Request model for the 多重回归 (Saturn/Jupiter/node returns) tool."""

    analysis_year: Optional[int] = Field(
        default=None,
        description="Reference year for the returns (omit for current date)",
    )
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Reference month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Reference day (1-31)"
    )


class AstroHoraryRequest(BaseModel):
    """Request model for the 卜卦 (horary) tool — chart cast at the question moment."""

    name: Optional[str] = Field(default=None, description="Optional chart name")
    question_year: int = Field(description="Year the question was asked")
    question_month: int = Field(
        ge=1, le=12, description="Month the question was asked (1-12)"
    )
    question_day: int = Field(
        ge=1, le=31, description="Day the question was asked (1-31)"
    )
    question_hour: int = Field(
        ge=0, le=23, description="Hour the question was asked (0-23)"
    )
    question_minute: int = Field(
        default=0, ge=0, le=59, description="Minute the question was asked"
    )
    timezone_name: str = Field(
        default="+08:00", description="Question timezone (IANA name or UTC offset)"
    )
    longitude: float = Field(
        ge=-180, le=180, description="Longitude where the question was asked"
    )
    latitude: float = Field(
        ge=-90, le=90, description="Latitude where the question was asked"
    )
    category: str = Field(
        default="general",
        description=(
            "Question topic, selecting the quesited house: general/wealth/family/"
            "property/pregnancy/health/marriage/lawsuit/theft/travel/career/hope/enemy/death"
        ),
    )
    house_system: Union[int, str] = Field(
        default="R",
        description="House system, any convention (SE letter / key / integer "
        "code 0..8); Regiomontanus (R, code 2) is traditional for horary.",
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )


class AstroElectionRequest(BaseModel):
    """Request model for the 择日 (electional) tool — chart cast at the candidate moment."""

    name: Optional[str] = Field(default=None, description="Optional chart name")
    candidate_year: int = Field(
        description="Year of the candidate moment being evaluated"
    )
    candidate_month: int = Field(
        ge=1, le=12, description="Month of the candidate moment (1-12)"
    )
    candidate_day: int = Field(
        ge=1, le=31, description="Day of the candidate moment (1-31)"
    )
    candidate_hour: int = Field(
        ge=0, le=23, description="Hour of the candidate moment (0-23)"
    )
    candidate_minute: int = Field(
        default=0, ge=0, le=59, description="Minute of the candidate moment"
    )
    timezone_name: str = Field(
        default="+08:00",
        description="Candidate-moment timezone (IANA name or UTC offset)",
    )
    longitude: float = Field(
        ge=-180, le=180, description="Longitude where the act will take place"
    )
    latitude: float = Field(
        ge=-90, le=90, description="Latitude where the act will take place"
    )
    topic_id: str = Field(
        default="marriage",
        description=(
            "Undertaking type, selecting the rule pack: marriage/business/move_in/"
            "buy_property/trade/buy_car/contract/surgery/travel/job_hunt/general"
        ),
    )
    house_system: Union[int, str] = Field(
        default="R",
        description="House system, any convention (SE letter / key / integer "
        "code 0..8); Regiomontanus (R, code 2) is traditional for elections.",
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )


class BaziMarriageRequest(BaziDimensionRequest):
    """Request model for BaZi marriage analysis."""


class BaziCareerRequest(BaziDimensionRequest):
    """Request model for BaZi career analysis."""


class BaziWealthRequest(BaziDimensionRequest):
    """Request model for BaZi wealth analysis."""


class BaziHealthRequest(BaziDimensionRequest):
    """Request model for BaZi health analysis."""


class BaziChildrenRequest(BaziDimensionRequest):
    """Request model for BaZi children analysis."""


class BaziEducationRequest(BaziDimensionRequest):
    """Request model for BaZi education analysis."""


class AstroChartPolyRequest(AstroChartRequest):
    """Polymorphic astro chart request (adds a chart_variant selector)."""

    chart_variant: str = Field(
        default="chart",
        description="Chart variant: chart, chart13, hellen_chart, guolao_chart, india_chart, germany",
    )


class AstroRelativeFlatRequest(BaseModel):
    """Flat (non-nested) relative/synastry chart request for tool surfaces."""

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


class BaziPersonalityRequest(BaziDimensionRequest):
    """Request model for BaZi personality analysis."""


class BaziRelativesRequest(BaziDimensionRequest):
    """Request model for BaZi relatives analysis."""


class BaziRomanceRequest(BaziDimensionRequest):
    """Request model for BaZi romance / peach-blossom analysis."""
