"""
FastAPI REST server for FateBridge calculations.
Provides HTTP endpoints for birth analysis, timing, and divination calculations.
"""

import logging
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.divination import calculate_meihua_analysis
from fatebridge.services.timing import (
    calculate_jieqi_timeline_analysis,
    calculate_liuri_analysis,
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
    description="API for FateBridge Calculation - BaZi Fortune Telling",
    version="0.1.0",
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
