"""
FastAPI REST server for FateBridge calculations.
Provides HTTP endpoints for birth analysis, timing, and divination calculations.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from fatebridge.services.astrology import (
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
    calculate_relative_chart_analysis,
)
from fatebridge.services.western_timing import calculate_western_timing_analysis
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.divination import (
    calculate_gua_lookup,
    calculate_gua_meiyi,
    calculate_meihua_analysis,
    calculate_otherbu_analysis,
    calculate_sanshiunited_analysis,
    calculate_sixyao_analysis,
    calculate_suzhan_analysis,
    calculate_tongshefa_analysis,
)
from fatebridge.services.export_tools import (
    calculate_export_parse,
    calculate_export_registry,
)
from fatebridge.services.knowledge import (
    calculate_knowledge_read,
    calculate_knowledge_registry,
)
from fatebridge.services.metaphysics import (
    calculate_jinkou_analysis,
    calculate_liureng_gods,
    calculate_liureng_runyear,
    calculate_qimen_analysis,
    calculate_taiyi_analysis,
    calculate_ziwei_birth,
    calculate_ziwei_rules,
)
from fatebridge.services.timing import (
    calculate_jieqi_year,
    calculate_jieqi_timeline_analysis,
    calculate_liuyue_analysis,
    calculate_liuri_analysis,
    calculate_nongli_time,
)
from fatebridge.utils.helpers import create_person_info

# ============================================================================
# Setup
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FateBridge API",
    description="API for FateBridge calculations across BaZi, divination, timing, and approximate offline astrology charts",
    version="0.2.0",
)

# ============================================================================
# CORS Configuration - FIXED SECURITY ISSUE
# ============================================================================

# Get allowed origins from environment variable, default to localhost for development
ALLOWED_ORIGINS = [
    origin.strip() for origin in
    os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # FIXED: Changed from True (security issue)
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


# ============================================================================
# Request/Response Models
# ============================================================================


class FateBridgeRequest(BaseModel):
    """Request model for individual destiny analysis"""

    name: Optional[str] = Field(default="未提供", description="Name (optional)")
    gender: Optional[str] = Field(default="未知", description="Gender (optional)")
    birth_year: int = Field(description="Birth year, e.g., 1990")
    birth_month: int = Field(ge=1, le=12, description="Birth month (1-12)")
    birth_day: int = Field(ge=1, le=31, description="Birth day (1-31)")
    birth_hour: int = Field(ge=0, le=23, description="Birth hour (0-23)")
    birth_minute: int = Field(default=0, ge=0, le=59, description="Birth minute (0-59)")
    birth_place: Optional[str] = Field(default="未提供", description="Birth place (optional)")
    birth_timezone: Optional[str] = Field(
        default=None, description="Birth timezone (IANA name or UTC offset)"
    )
    birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="Birth longitude (optional)"
    )
    use_true_solar_time: bool = Field(
        default=False, description="Enable true solar time correction"
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


class JieqiTimelineRequest(FateBridgeRequest):
    """Request model for jieqi timeline analysis."""

    target_year: Optional[int] = Field(default=None, description="Target year")


class LiuyueAnalysisRequest(FateBridgeRequest):
    """Request model for liuyue analysis."""

    analysis_year: Optional[int] = Field(default=None, description="Analysis year")
    analysis_month: Optional[int] = Field(
        default=None, ge=1, le=12, description="Analysis month (1-12)"
    )
    analysis_day: Optional[int] = Field(
        default=None, ge=1, le=31, description="Analysis day (1-31)"
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


class JieqiYearRequest(BaseModel):
    """Request model for annual jieqi helper output."""

    model_config = ConfigDict(populate_by_name=True)

    year: int = Field(description="Target year, e.g. 2028")
    zone: Optional[str] = Field(default="Asia/Shanghai", description="Timezone spec")
    lat: Optional[str] = Field(default=None, description="Latitude text hint")
    lon: Optional[str] = Field(default=None, description="Longitude text hint")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    jieqis: List[str] = Field(default_factory=list, description="Optional focused jieqi names")


class NongliTimeRequest(BaseModel):
    """Request model for nongli-time helper output."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-01")
    time: str = Field(description="Time string, e.g. 09:00:00")
    zone: Optional[str] = Field(default="Asia/Shanghai", description="Timezone spec")
    lat: Optional[str] = Field(default=None, description="Latitude text hint")
    lon: Optional[str] = Field(default=None, description="Longitude text hint")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    gender: Optional[bool] = Field(default=None, description="Optional gender flag passthrough")
    after23_new_day: bool = Field(default=False, alias="after23NewDay", description="Whether 23:00 counts as next day")
    time_alg: int = Field(default=0, alias="timeAlg", description="Time algorithm passthrough flag")
    ad: int = Field(default=1, description="Common era flag passthrough")


class GuaMeiyiRequest(BaseModel):
    """Request model for batch Meiyi hexagram meanings."""

    name: List[str] = Field(description="Trigram or hexagram names/codes")


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


class KnowledgeReadRequest(BaseModel):
    """Request model for bundled knowledge lookup."""

    domain: str = Field(description="Knowledge domain: astro, liureng, or qimen")
    category: str = Field(description="Category within the domain")
    key: Optional[str] = Field(default=None, description="Primary lookup key")
    aspect_degree: Optional[int] = Field(
        default=None,
        description="Optional aspect degree for astro aspect lookups",
    )
    object_a: Optional[str] = Field(default=None, description="First astro object")
    object_b: Optional[str] = Field(default=None, description="Second astro object")
    jiang_name: Optional[str] = Field(default=None, description="Liureng general name")
    tian_branch: Optional[str] = Field(default=None, description="Liureng heaven branch")
    di_branch: Optional[str] = Field(default=None, description="Liureng earth branch")


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
    lon: Optional[str] = Field(default="121e28", description="Longitude text or decimal")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    question: Optional[str] = Field(default=None, description="Question or topic")
    gua_code: Optional[str] = Field(default=None, description="Current hexagram code")
    changed_code: Optional[str] = Field(default=None, description="Changed hexagram code")
    lines: List[SixYaoLineRequest] = Field(default_factory=list, description="Optional six lines")


class SuZhanRequest(BaseModel):
    """Request model for suzhan."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(default="121e28", description="Longitude text or decimal")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    szchart: int = Field(default=0, description="Chart mode flag")
    szshape: int = Field(default=0, description="Chart shape flag")
    house_start_mode: int = Field(default=1, alias="houseStartMode", description="House start mode")
    doubing_su28: bool = Field(default=True, alias="doubingSu28", description="Whether to double-check su28 labels")


class OtherBuRequest(BaseModel):
    """Request model for otherbu."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(default="121e28", description="Longitude text or decimal")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    tradition: bool = Field(default=False, description="Traditional mode without outer planets")
    sign: Optional[str] = Field(default="Aries", description="Dice sign")
    house: int = Field(default=0, ge=0, le=11, description="Dice house index (0-11)")
    planet: Optional[str] = Field(default="Sun", description="Dice planet")
    question: Optional[str] = Field(default=None, description="Question or topic")


class SanShiUnitedRequest(BaseModel):
    """Request model for sanshiunited."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(description="Date string, e.g. 2028-04-06")
    time: str = Field(description="Time string, e.g. 09:33:00")
    zone: Optional[str] = Field(default="+08:00", description="Timezone spec")
    lat: Optional[str] = Field(default="31n13", description="Latitude text or decimal")
    lon: Optional[str] = Field(default="121e28", description="Longitude text or decimal")
    gps_lat: Optional[float] = Field(default=None, alias="gpsLat", description="GPS latitude")
    gps_lon: Optional[float] = Field(default=None, alias="gpsLon", description="GPS longitude")
    qimen_options: Dict[str, Any] = Field(default_factory=dict, alias="qimen_options", description="Optional qimen settings")
    taiyi_options: Dict[str, Any] = Field(default_factory=dict, alias="taiyi_options", description="Optional taiyi settings")
    liureng_yue: Optional[str] = Field(default=None, alias="liureng_yue", description="Optional liureng month-general override")
    liureng_is_diurnal: Optional[bool] = Field(default=None, alias="liureng_isDiurnal", description="Optional liureng day/night override")


class ZiweiBirthRequest(FateBridgeRequest):
    """Request model for Zi Wei birth chart analysis."""


class ZiweiRulesRequest(BaseModel):
    """Request model for Zi Wei rule catalogue lookup."""

    year_stem: Optional[str] = Field(
        default=None,
        description="Optional heavenly stem filter, e.g. 甲",
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
    gender: Optional[str] = Field(default="未知", description="Gender")
    use_true_solar_time: bool = Field(
        default=False, description="Enable true solar time correction"
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
    use_true_solar_time: bool = Field(
        default=False, description="Enable true solar time correction"
    )


class TaiyiAnalysisRequest(QimenAnalysisRequest):
    """Request model for Taiyi analysis."""

    gender: Optional[str] = Field(default="未知", description="Gender")


class JinkouAnalysisRequest(LiuRengGodsRequest):
    """Request model for Jin Kou analysis."""

    di_fen: Optional[str] = Field(default=None, description="Ground division branch")


class AstroChartRequest(BaseModel):
    """Request model for approximate offline astrology chart generation."""

    name: Optional[str] = Field(default="未提供", description="Name (optional)")
    birth_year: int = Field(description="Birth year, e.g., 1990")
    birth_month: int = Field(ge=1, le=12, description="Birth month (1-12)")
    birth_day: int = Field(ge=1, le=31, description="Birth day (1-31)")
    birth_hour: int = Field(ge=0, le=23, description="Birth hour (0-23)")
    birth_minute: int = Field(default=0, ge=0, le=59, description="Birth minute (0-59)")
    birth_timezone: Optional[str] = Field(
        default="UTC", description="Birth timezone (IANA name or UTC offset)"
    )
    birth_longitude: float = Field(ge=-180, le=180, description="Birth longitude")
    birth_latitude: float = Field(ge=-90, le=90, description="Birth latitude")
    birth_place: Optional[str] = Field(default="未提供", description="Birth place")


class AstroRelativePartyRequest(AstroChartRequest):
    """One side of a relative/synastry request."""


class AstroRelativeRequest(BaseModel):
    """Request model for relative / synastry chart generation."""

    inner: AstroRelativePartyRequest
    outer: AstroRelativePartyRequest
    relationship_mode: str = Field(
        default="synastry",
        description="Relationship mode, e.g. synastry or composite",
    )


class WesternTimingRequest(AstroChartRequest):
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
    house_system: str = Field(
        default="P", description="House system identifier, e.g. P for Placidus"
    )
    zodiac_type: str = Field(
        default="Tropic", description="Zodiac type, e.g. Tropic or Sidereal"
    )
    pd_method: str = Field(
        default="astroapp_alchabitius",
        description="Primary direction method identifier",
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


# ============================================================================
# API Endpoints
# ============================================================================


@app.post("/api/calculate")
async def calculate_destiny(request: FateBridgeRequest) -> dict:
    """
    Calculate individual destiny analysis based on birth information.

    Args:
        request: Birth information for analysis

    Returns:
        Dictionary containing four pillars, element analysis, patterns, etc.

    Raises:
        HTTPException: On invalid input (400) or server error (500)
    """
    try:
        logger.info(f"Processing calculation request for {request.name}")

        # Validate and create person info
        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        # Perform calculation
        result = calculate_destiny_analysis(person)

        # Check for errors in result
        if "error" in result:
            logger.warning(f"Calculation failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Calculation successful for {request.name}")
        return result

    except ValueError as e:
        logger.warning(f"Invalid input received: {type(e).__name__}")
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during calculation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.post("/api/divination/gua")
async def calculate_gua_description(request: GuaLookupRequest) -> dict:
    """
    Look up offline trigram/hexagram meanings by name or binary code.
    """
    try:
        logger.info("Processing gua lookup request for %s", request.query)

        result = calculate_gua_lookup(
            query=request.query,
            lookup_mode=request.lookup_mode,
        )

        if "error" in result:
            logger.warning(f"Gua lookup failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Gua lookup successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的卦象查询参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during gua lookup: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/jieqi/year")
async def calculate_jieqi_year_helper(request: JieqiYearRequest) -> dict:
    """
    Generate annual jieqi helper output.
    """
    try:
        logger.info("Processing jieqi year helper request for %s", request.year)

        result = calculate_jieqi_year(**request.model_dump())

        if "error" in result:
            logger.warning(f"Jieqi year helper failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Jieqi year helper successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的节气年份参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during jieqi year helper: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/nongli/time")
async def calculate_nongli_time_helper(request: NongliTimeRequest) -> dict:
    """
    Convert a solar datetime into lunar calendar and ganzhi context.
    """
    try:
        logger.info(
            "Processing nongli time helper request for %s %s",
            request.date,
            request.time,
        )

        result = calculate_nongli_time(**request.model_dump())

        if "error" in result:
            logger.warning(f"Nongli time helper failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Nongli time helper successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的农历换算参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during nongli time helper: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/gua/meiyi")
async def calculate_gua_meiyi_helper(request: GuaMeiyiRequest) -> dict:
    """
    Return batch Meiyi-oriented gua explanations.
    """
    try:
        logger.info("Processing gua meiyi helper request for %s", request.name)

        result = calculate_gua_meiyi(**request.model_dump())

        if "error" in result:
            logger.warning(f"Gua meiyi helper failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Gua meiyi helper successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的梅易卦义参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during gua meiyi helper: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/export/registry")
async def export_registry_helper(request: ExportRegistryRequest) -> dict:
    """
    Return the local AI export registry compatible with horosa-style settings.
    """
    try:
        logger.info("Processing export registry request for %s", request.technique)

        result = calculate_export_registry(**request.model_dump())

        if "error" in result:
            logger.warning(f"Export registry failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Export registry successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的导出注册表参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during export registry lookup: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/export/parse")
async def export_parse_helper(request: ExportParseRequest) -> dict:
    """
    Parse snapshot text into horosa-style export sections.
    """
    try:
        logger.info("Processing export parse request for %s", request.technique)

        payload = request.model_dump(by_alias=True)
        result = calculate_export_parse(
            technique=payload["technique"],
            content=payload["content"],
            selected_sections=payload.get("selected_sections") or None,
            planet_info=payload.get("planetInfo"),
            astro_meaning=payload.get("astroMeaning"),
        )

        if "error" in result:
            logger.warning(f"Export parse failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Export parse successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的导出解析参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during export parse: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/knowledge/registry")
async def knowledge_registry_helper(request: KnowledgeRegistryRequest) -> dict:
    """
    List bundled knowledge domains and categories.
    """
    try:
        logger.info("Processing knowledge registry request for %s", request.domain)

        result = calculate_knowledge_registry(**request.model_dump())

        if "error" in result:
            logger.warning(f"Knowledge registry failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Knowledge registry successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识目录参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during knowledge registry lookup: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/knowledge/read")
async def knowledge_read_helper(request: KnowledgeReadRequest) -> dict:
    """
    Read one bundled knowledge entry by domain/category/key.
    """
    try:
        logger.info(
            "Processing knowledge read request for %s/%s",
            request.domain,
            request.category,
        )

        result = calculate_knowledge_read(**request.model_dump())

        if "error" in result:
            logger.warning(f"Knowledge read failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Knowledge read successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的知识读取参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during knowledge read: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/meihua")
async def calculate_meihua(request: MeihuaAnalysisRequest) -> dict:
    """
    Calculate a Mei Hua Yi Shu time-seeded hexagram for the specified moment.
    """
    try:
        logger.info(
            "Processing meihua analysis request for %s-%s-%s %s:%s",
            request.analysis_year,
            request.analysis_month,
            request.analysis_day,
            request.analysis_hour,
            request.analysis_minute,
        )

        result = calculate_meihua_analysis(
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            question=request.question,
        )

        if "error" in result:
            logger.warning(f"Meihua analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Meihua analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during meihua analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/tongshefa")
async def calculate_tongshefa(request: TongSheFaRequest) -> dict:
    """Calculate local tongshefa analysis."""
    try:
        logger.info("Processing tongshefa request")
        result = calculate_tongshefa_analysis(
            taiyin=request.taiyin,
            taiyang=request.taiyang,
            shaoyang=request.shaoyang,
            shaoyin=request.shaoyin,
        )

        if "error" in result:
            logger.warning(f"Tongshefa analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Tongshefa analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的统摄法参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during tongshefa analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/sixyao")
async def calculate_sixyao(request: SixYaoRequest) -> dict:
    """Calculate local sixyao analysis."""
    try:
        logger.info("Processing sixyao request for %s %s", request.date, request.time)
        result = calculate_sixyao_analysis(
            date=request.date,
            time=request.time,
            zone=request.zone,
            lat=request.lat,
            lon=request.lon,
            gps_lat=request.gps_lat,
            gps_lon=request.gps_lon,
            question=request.question,
            gua_code=request.gua_code,
            changed_code=request.changed_code,
            lines=[line.model_dump() for line in request.lines],
        )

        if "error" in result:
            logger.warning(f"Sixyao analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Sixyao analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六爻参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during sixyao analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/suzhan")
async def calculate_suzhan(request: SuZhanRequest) -> dict:
    """Calculate local suzhan analysis."""
    try:
        logger.info("Processing suzhan request for %s %s", request.date, request.time)
        result = calculate_suzhan_analysis(
            date=request.date,
            time=request.time,
            zone=request.zone,
            lat=request.lat,
            lon=request.lon,
            gps_lat=request.gps_lat,
            gps_lon=request.gps_lon,
            szchart=request.szchart,
            szshape=request.szshape,
            house_start_mode=request.house_start_mode,
            doubing_su28=request.doubing_su28,
        )

        if "error" in result:
            logger.warning(f"Suzhan analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Suzhan analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的宿占参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during suzhan analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/otherbu")
async def calculate_otherbu(request: OtherBuRequest) -> dict:
    """Calculate local otherbu analysis."""
    try:
        logger.info("Processing otherbu request for %s %s", request.date, request.time)
        result = calculate_otherbu_analysis(
            date=request.date,
            time=request.time,
            zone=request.zone,
            lat=request.lat,
            lon=request.lon,
            gps_lat=request.gps_lat,
            gps_lon=request.gps_lon,
            tradition=request.tradition,
            sign=request.sign,
            house=request.house,
            planet=request.planet,
            question=request.question,
        )

        if "error" in result:
            logger.warning(f"Otherbu analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Otherbu analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的占星骰子参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during otherbu analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/sanshiunited")
async def calculate_sanshiunited(request: SanShiUnitedRequest) -> dict:
    """Calculate local sanshiunited analysis."""
    try:
        logger.info("Processing sanshiunited request for %s %s", request.date, request.time)
        result = calculate_sanshiunited_analysis(
            date=request.date,
            time=request.time,
            zone=request.zone,
            lat=request.lat,
            lon=request.lon,
            gps_lat=request.gps_lat,
            gps_lon=request.gps_lon,
            qimen_options=request.qimen_options,
            taiyi_options=request.taiyi_options,
            liureng_yue=request.liureng_yue,
            liureng_is_diurnal=request.liureng_is_diurnal,
        )

        if "error" in result:
            logger.warning(f"Sanshiunited analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Sanshiunited analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的三式合一参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during sanshiunited analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/ziwei/birth")
async def calculate_ziwei_birth_chart(request: ZiweiBirthRequest) -> dict:
    """
    Calculate a Zi Wei birth chart from birth information.
    """
    try:
        logger.info("Processing ziwei birth request for %s", request.name)

        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        result = calculate_ziwei_birth(person)

        if "error" in result:
            logger.warning(f"Ziwei birth calculation failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info("Ziwei birth calculation successful for %s", request.name)
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during ziwei birth analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/ziwei/rules")
async def get_ziwei_rules(request: ZiweiRulesRequest) -> dict:
    """
    Return the Zi Wei rule catalogue, optionally filtered by year stem.
    """
    try:
        result = calculate_ziwei_rules(year_stem=request.year_stem)

        if "error" in result:
            logger.warning(f"Ziwei rule lookup failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的紫微规则查询参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during ziwei rule lookup: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/liureng/gods")
async def get_liureng_gods(request: LiuRengGodsRequest) -> dict:
    """
    Calculate a Liu Ren divination board.
    """
    try:
        result = calculate_liureng_gods(
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            use_true_solar_time=request.use_true_solar_time,
        )

        if "error" in result:
            logger.warning(f"LiuReng gods analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六壬参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during LiuReng gods analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/liureng/runyear")
async def get_liureng_runyear(request: LiuRengRunyearRequest) -> dict:
    """
    Calculate a Liu Ren runyear analysis using birth context.
    """
    try:
        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )
        result = calculate_liureng_runyear(
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        if "error" in result:
            logger.warning(f"LiuReng runyear analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六壬行年参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during LiuReng runyear analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/qimen")
async def get_qimen_analysis(request: QimenAnalysisRequest) -> dict:
    """
    Calculate a Qi Men Dun Jia board.
    """
    try:
        result = calculate_qimen_analysis(
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        if "error" in result:
            logger.warning(f"Qimen analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的奇门参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during qimen analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/taiyi")
async def get_taiyi_analysis(request: TaiyiAnalysisRequest) -> dict:
    """
    Calculate a Taiyi board.
    """
    try:
        result = calculate_taiyi_analysis(
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            use_true_solar_time=request.use_true_solar_time,
        )

        if "error" in result:
            logger.warning(f"Taiyi analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的太乙参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during taiyi analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/jinkou")
async def get_jinkou_analysis(request: JinkouAnalysisRequest) -> dict:
    """
    Calculate a Jin Kou board.
    """
    try:
        result = calculate_jinkou_analysis(
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            di_fen=request.di_fen,
            use_true_solar_time=request.use_true_solar_time,
        )

        if "error" in result:
            logger.warning(f"Jinkou analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的金口诀参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during jinkou analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


def _run_astro_chart_variant(request: AstroChartRequest, chart_variant: str) -> dict:
    result = calculate_core_chart_analysis(
        chart_variant=chart_variant,
        **request.model_dump(),
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/astro/chart")
async def calculate_astro_chart(request: AstroChartRequest) -> dict:
    """Generate a core approximate astrology chart."""
    try:
        logger.info("Processing astrology chart request for %s", request.name)
        return _run_astro_chart_variant(request, "chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/chart13")
async def calculate_astro_chart13(request: AstroChartRequest) -> dict:
    """Generate an experimental 13-sector chart overlay."""
    try:
        logger.info("Processing chart13 request for %s", request.name)
        return _run_astro_chart_variant(request, "chart13")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during chart13 calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/hellen")
async def calculate_hellen_chart(request: AstroChartRequest) -> dict:
    """Generate a Hellenistic-leaning whole-sign chart."""
    try:
        logger.info("Processing hellen chart request for %s", request.name)
        return _run_astro_chart_variant(request, "hellen_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during hellen chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/guolao")
async def calculate_guolao_chart(request: AstroChartRequest) -> dict:
    """Generate a Guolao/Qizheng-Siyu inspired chart view."""
    try:
        logger.info("Processing guolao chart request for %s", request.name)
        return _run_astro_chart_variant(request, "guolao_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during guolao chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/india")
async def calculate_india_chart(request: AstroChartRequest) -> dict:
    """Generate a sidereal / India-style chart view."""
    try:
        logger.info("Processing india chart request for %s", request.name)
        return _run_astro_chart_variant(request, "india_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during india chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/germany")
async def calculate_germany_chart(request: AstroChartRequest) -> dict:
    """Generate midpoint / germany style analysis."""
    try:
        logger.info("Processing germany chart request for %s", request.name)
        result = calculate_germany_chart_analysis(**request.model_dump())
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during germany chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/relative")
async def calculate_relative_chart(request: AstroRelativeRequest) -> dict:
    """Generate synastry / relative chart output for two people."""
    try:
        logger.info(
            "Processing relative chart request for %s and %s",
            request.inner.name,
            request.outer.name,
        )
        result = calculate_relative_chart_analysis(
            inner_payload=request.inner.model_dump(),
            outer_payload=request.outer.model_dump(),
            relationship_mode=request.relationship_mode,
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during relative chart calculation: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/timing")
async def calculate_western_timing(request: WesternTimingRequest) -> dict:
    """Generate western predictive timing output for a target analysis date."""
    try:
        logger.info("Processing western timing request for %s", request.name)
        result = calculate_western_timing_analysis(**request.model_dump())
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during western timing calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/liuyue")
async def calculate_liuyue(request: LiuyueAnalysisRequest) -> dict:
    """
    Calculate liuyue analysis for the jieqi month containing the analysis date.
    """
    try:
        logger.info(f"Processing liuyue analysis request for {request.name}")

        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        result = calculate_liuyue_analysis(
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
        )

        if "error" in result:
            logger.warning(f"Liuyue analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Liuyue analysis successful for {request.name}")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during liuyue analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/liuri")
async def calculate_liuri(request: LiuriAnalysisRequest) -> dict:
    """
    Calculate liuri analysis for a specific analysis date.
    """
    try:
        logger.info(f"Processing liuri analysis request for {request.name}")

        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        result = calculate_liuri_analysis(
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
        )

        if "error" in result:
            logger.warning(f"Liuri analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Liuri analysis successful for {request.name}")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during liuri analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/jieqi")
async def calculate_jieqi_timeline(request: JieqiTimelineRequest) -> dict:
    """
    Calculate yearly jieqi timeline analysis.
    """
    try:
        logger.info(f"Processing jieqi timeline request for {request.name}")

        person = create_person_info(
            birth_year=request.birth_year,
            birth_month=request.birth_month,
            birth_day=request.birth_day,
            birth_hour=request.birth_hour,
            name=request.name,
            gender=request.gender,
            birth_place=request.birth_place,
            birth_minute=request.birth_minute,
            birth_timezone=request.birth_timezone,
            birth_longitude=request.birth_longitude,
            use_true_solar_time=request.use_true_solar_time,
        )

        result = calculate_jieqi_timeline_analysis(
            person,
            target_year=request.target_year,
        )

        if "error" in result:
            logger.warning(f"Jieqi timeline analysis failed: {result['error']}")
            raise HTTPException(status_code=400, detail=result["error"])

        logger.info(f"Jieqi timeline analysis successful for {request.name}")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during jieqi timeline analysis: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8010")),
        log_level="info",
    )
