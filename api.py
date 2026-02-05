"""
FastAPI REST server for FateBridge calculations.
Provides HTTP endpoints for birth analysis and compatibility calculations.
"""

import logging
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from logic import calculate_fatebridge
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
    birth_place: Optional[str] = Field(default="未提供", description="Birth place (optional)")


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
        )

        # Perform calculation
        result = calculate_fatebridge(person)

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


# ============================================================================
# Main
# ============================================================================


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        log_level="info",
    )
