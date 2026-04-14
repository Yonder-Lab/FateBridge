"""
FastAPI REST server for FateBridge calculations.
Provides HTTP endpoints for birth analysis, timing, and divination calculations.
"""

import logging
import math
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from fatebridge.core import astrology as astrology_core
from fatebridge.core import astrology_predictive as astrology_predictive_core
from fatebridge.services.astrology import (
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
    calculate_relative_chart_analysis,
)
from fatebridge.services.bazi import calculate_bazi_birth, calculate_bazi_direct
from fatebridge.services.compatibility import calculate_compatibility_analysis
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
    calculate_comprehensive_timing,
    calculate_dayun_analysis,
    calculate_jieqi_timeline_analysis,
    calculate_jieqi_year,
    calculate_liunian_analysis,
    calculate_liuri_analysis,
    calculate_liuyue_analysis,
    calculate_nongli_time,
)
from fatebridge.services.run_metadata import (
    attach_run_metadata,
    infer_tool_name_from_service,
)
from fatebridge.services.tool_registry import get_tool_descriptor
from fatebridge.services.western_timing import calculate_western_timing_analysis
from fatebridge.utils.helpers import create_person_info
from fatebridge.utils.runtime import (
    get_api_key_header_name,
    get_log_level,
    load_runtime_env,
    parse_allowed_origins,
    parse_api_keys,
    summarize_request_context,
)

# ============================================================================
# Setup
# ============================================================================

load_runtime_env()

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_log_level(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FateBridge API",
    description="API for FateBridge calculations across BaZi, divination, timing, and offline astrology charts with local ephemeris preference",
    version="0.2.0",
)

# ============================================================================
# CORS Configuration - FIXED SECURITY ISSUE
# ============================================================================

# Get allowed origins from environment variable, default to localhost for development
ALLOWED_ORIGINS = parse_allowed_origins()
API_KEY_HEADER_NAME = get_api_key_header_name()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,  # FIXED: Changed from True (security issue)
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", API_KEY_HEADER_NAME],
)


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        logger.warning("Invalid integer for %s, falling back to %s", name, default)
        return default


def _prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class RequestRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        *,
        client_id: str,
        path: str,
        now: Optional[float] = None,
    ) -> Tuple[bool, Optional[int]]:
        if self.max_requests <= 0 or self.window_seconds <= 0:
            return True, None

        current_time = now if now is not None else time.monotonic()
        key = (client_id, path)
        cutoff = current_time - self.window_seconds

        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(
                    1,
                    math.ceil(self.window_seconds - (current_time - bucket[0])),
                )
                return False, retry_after

            bucket.append(current_time)
            return True, None

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class RuntimeMetrics:
    def __init__(self) -> None:
        self._request_counts: Dict[Tuple[str, str, str], float] = defaultdict(float)
        self._duration_sums: Dict[Tuple[str, str], float] = defaultdict(float)
        self._duration_counts: Dict[Tuple[str, str], float] = defaultdict(float)
        self._lock = Lock()

    def observe(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        status = str(status_code)
        with self._lock:
            self._request_counts[(method, path, status)] += 1.0
            self._duration_sums[(method, path)] += duration_seconds
            self._duration_counts[(method, path)] += 1.0

    def render_prometheus(
        self,
        *,
        readiness_status: str,
        api_key_auth_enabled: bool,
        configured_api_keys: int,
        api_key_daily_quota: int,
    ) -> str:
        with self._lock:
            request_counts = dict(self._request_counts)
            duration_sums = dict(self._duration_sums)
            duration_counts = dict(self._duration_counts)

        lines = [
            "# HELP fatebridge_http_requests_total Total HTTP requests handled by FateBridge.",
            "# TYPE fatebridge_http_requests_total counter",
        ]
        for (method, path, status), count in sorted(request_counts.items()):
            lines.append(
                'fatebridge_http_requests_total{method="%s",path="%s",status="%s"} %.1f'
                % (
                    _prometheus_escape(method),
                    _prometheus_escape(path),
                    _prometheus_escape(status),
                    count,
                )
            )

        lines.extend(
            [
                "# HELP fatebridge_http_request_duration_seconds_sum Total request duration in seconds grouped by method and path.",
                "# TYPE fatebridge_http_request_duration_seconds_sum counter",
            ]
        )
        for (method, path), duration_sum in sorted(duration_sums.items()):
            lines.append(
                'fatebridge_http_request_duration_seconds_sum{method="%s",path="%s"} %.6f'
                % (
                    _prometheus_escape(method),
                    _prometheus_escape(path),
                    duration_sum,
                )
            )

        lines.extend(
            [
                "# HELP fatebridge_http_request_duration_seconds_count Number of observed requests grouped by method and path.",
                "# TYPE fatebridge_http_request_duration_seconds_count counter",
            ]
        )
        for (method, path), count in sorted(duration_counts.items()):
            lines.append(
                'fatebridge_http_request_duration_seconds_count{method="%s",path="%s"} %.1f'
                % (
                    _prometheus_escape(method),
                    _prometheus_escape(path),
                    count,
                )
            )

        lines.extend(
            [
                "# HELP fatebridge_readiness_state Current readiness state of the API.",
                "# TYPE fatebridge_readiness_state gauge",
                'fatebridge_readiness_state{status="%s"} 1'
                % _prometheus_escape(readiness_status),
                "# HELP fatebridge_api_key_auth_enabled Whether API key authentication is enabled.",
                "# TYPE fatebridge_api_key_auth_enabled gauge",
                f"fatebridge_api_key_auth_enabled {1 if api_key_auth_enabled else 0}",
                "# HELP fatebridge_api_keys_configured_total Number of configured API keys.",
                "# TYPE fatebridge_api_keys_configured_total gauge",
                f"fatebridge_api_keys_configured_total {configured_api_keys}",
                "# HELP fatebridge_api_key_daily_quota Configured daily quota per API key. Zero means disabled.",
                "# TYPE fatebridge_api_key_daily_quota gauge",
                f"fatebridge_api_key_daily_quota {api_key_daily_quota}",
            ]
        )
        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._duration_sums.clear()
            self._duration_counts.clear()


class ApiKeyAuthenticator:
    def __init__(self, *, header_name: str, api_keys: Dict[str, str]) -> None:
        self.header_name = header_name
        self.api_keys = dict(api_keys)
        self._secret_to_id = {
            secret: key_id for key_id, secret in self.api_keys.items()
        }

    @property
    def enabled(self) -> bool:
        return bool(self._secret_to_id)

    def authenticate(self, request: Request) -> Optional[str]:
        if not self.enabled:
            return None

        secret = request.headers.get(self.header_name)
        if not secret:
            return None

        return self._secret_to_id.get(secret)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApiKeyQuotaTracker:
    def __init__(self, *, daily_quota: int) -> None:
        self.daily_quota = daily_quota
        self._usage: Dict[Tuple[str, str], int] = {}
        self._lock = Lock()

    @property
    def enabled(self) -> bool:
        return self.daily_quota > 0

    def check_and_consume(
        self,
        *,
        key_id: str,
        now: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[int], Optional[int]]:
        if not self.enabled:
            return True, None, None

        current_time = now if now is not None else _utc_now()
        current_day = current_time.date().isoformat()
        usage_key = (current_day, key_id)

        with self._lock:
            stale_keys = [item for item in self._usage if item[0] != current_day]
            for stale_key in stale_keys:
                self._usage.pop(stale_key, None)

            used = self._usage.get(usage_key, 0)
            if used >= self.daily_quota:
                return False, 0, self.seconds_until_reset(current_time)

            used += 1
            self._usage[usage_key] = used
            return True, self.daily_quota - used, self.seconds_until_reset(current_time)

    def seconds_until_reset(self, now: Optional[datetime] = None) -> int:
        current_time = now if now is not None else _utc_now()
        next_midnight = current_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        return max(1, int((next_midnight - current_time).total_seconds()))

    def reset(self) -> None:
        with self._lock:
            self._usage.clear()


RATE_LIMIT_MAX_REQUESTS = _get_env_int("RATE_LIMIT_MAX_REQUESTS", 120)
RATE_LIMIT_WINDOW_SECONDS = _get_env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
RATE_LIMIT_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)
API_KEY_EXEMPT_PATHS = RATE_LIMIT_EXEMPT_PATHS
API_KEY_AUTHENTICATOR = ApiKeyAuthenticator(
    header_name=API_KEY_HEADER_NAME,
    api_keys=parse_api_keys(),
)
API_KEY_DAILY_QUOTA = _get_env_int("API_KEY_DAILY_QUOTA", 0)
API_KEY_QUOTA_TRACKER = ApiKeyQuotaTracker(daily_quota=API_KEY_DAILY_QUOTA)
REQUEST_RATE_LIMITER = RequestRateLimiter(
    max_requests=RATE_LIMIT_MAX_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW_SECONDS,
)
REQUEST_METRICS = RuntimeMetrics()


def _build_readiness_payload() -> Dict[str, Any]:
    western_kerykeion_available = (
        astrology_predictive_core.AstrologicalSubjectFactory is not None
        and astrology_predictive_core.PlanetaryReturnFactory is not None
    )
    checks: Dict[str, Dict[str, Any]] = {
        "core_api": {
            "ok": True,
            "required": True,
            "detail": "FastAPI app initialized",
        },
        "offline_astrology": {
            "ok": True,
            "required": True,
            "swisseph_available": astrology_core.swe is not None,
            "fallback_available": True,
        },
        "western_predictive_runtime": {
            "ok": western_kerykeion_available
            and astrology_predictive_core.swe is not None,
            "required": False,
            "swisseph_available": astrology_predictive_core.swe is not None,
            "kerykeion_available": western_kerykeion_available,
        },
        "api_key_auth": {
            "ok": True,
            "required": False,
            "enabled": API_KEY_AUTHENTICATOR.enabled,
            "header_name": API_KEY_AUTHENTICATOR.header_name,
            "configured_keys": len(API_KEY_AUTHENTICATOR.api_keys),
        },
        "api_key_quota": {
            "ok": (not API_KEY_QUOTA_TRACKER.enabled) or API_KEY_AUTHENTICATOR.enabled,
            "required": False,
            "enabled": API_KEY_QUOTA_TRACKER.enabled,
            "daily_quota": API_KEY_QUOTA_TRACKER.daily_quota,
        },
    }
    required_checks_ok = all(
        item["ok"] for item in checks.values() if item.get("required")
    )
    return {
        "status": "ready" if required_checks_ok else "not_ready",
        "checks": checks,
    }


def _build_rate_limit_detail() -> Dict[str, Any]:
    return {
        "error": "请求过于频繁，请稍后重试",
        "error_code": "rate_limited",
        "retryable": True,
    }


def _build_authentication_detail() -> Dict[str, Any]:
    return {
        "error": "缺少或无效的 API key",
        "error_code": "authentication_required",
        "retryable": False,
    }


def _build_quota_detail(quota_limit: int) -> Dict[str, Any]:
    return {
        "error": "API key 当日配额已用尽，请明日再试",
        "error_code": "quota_exceeded",
        "retryable": True,
        "quota_limit": quota_limit,
        "reset_scope": "utc_day",
    }


def _request_client_id(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or "forwarded-unknown"
    client = request.client
    return client.host if client and client.host else "unknown"


def _reset_runtime_state_for_tests() -> None:
    REQUEST_METRICS.reset()
    REQUEST_RATE_LIMITER.reset()
    API_KEY_QUOTA_TRACKER.reset()


@app.middleware("http")
async def instrument_request_lifecycle(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    path = request.url.path
    method = request.method.upper()
    authenticated_key_id: Optional[str] = None

    if method != "OPTIONS" and path not in API_KEY_EXEMPT_PATHS:
        if API_KEY_AUTHENTICATOR.enabled:
            authenticated_key_id = API_KEY_AUTHENTICATOR.authenticate(request)
            if authenticated_key_id is None:
                auth_response = JSONResponse(
                    status_code=401,
                    content={"detail": _build_authentication_detail()},
                )
                REQUEST_METRICS.observe(
                    method=method,
                    path=path,
                    status_code=401,
                    duration_seconds=0.0,
                )
                return auth_response

            request.state.api_key_id = authenticated_key_id

        if API_KEY_QUOTA_TRACKER.enabled and authenticated_key_id is not None:
            allowed, remaining, retry_after = API_KEY_QUOTA_TRACKER.check_and_consume(
                key_id=authenticated_key_id,
            )
            request.state.api_key_remaining = remaining
            if not allowed:
                quota_response = JSONResponse(
                    status_code=429,
                    content={
                        "detail": _build_quota_detail(API_KEY_QUOTA_TRACKER.daily_quota)
                    },
                )
                if retry_after is not None:
                    quota_response.headers["Retry-After"] = str(retry_after)
                REQUEST_METRICS.observe(
                    method=method,
                    path=path,
                    status_code=429,
                    duration_seconds=0.0,
                )
                return quota_response

    if method != "OPTIONS" and path not in RATE_LIMIT_EXEMPT_PATHS:
        allowed, retry_after = REQUEST_RATE_LIMITER.check(
            client_id=authenticated_key_id or _request_client_id(request),
            path=path,
        )
        if not allowed:
            detail = _build_rate_limit_detail()
            rate_limit_response = JSONResponse(
                status_code=429, content={"detail": detail}
            )
            if retry_after is not None:
                rate_limit_response.headers["Retry-After"] = str(retry_after)
            REQUEST_METRICS.observe(
                method=method,
                path=path,
                status_code=429,
                duration_seconds=0.0,
            )
            return rate_limit_response

    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUEST_METRICS.observe(
            method=method,
            path=path,
            status_code=500,
            duration_seconds=time.perf_counter() - started_at,
        )
        raise

    REQUEST_METRICS.observe(
        method=method,
        path=path,
        status_code=response.status_code,
        duration_seconds=time.perf_counter() - started_at,
    )
    return response


def _build_error_detail(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "error": result["error"],
        "error_code": result.get("error_code", "internal_error"),
        "retryable": result.get("retryable", False),
    }


def _raise_service_http_error(result: Dict[str, Any]) -> None:
    raise HTTPException(
        status_code=int(result.get("status_code", 500)),
        detail=_build_error_detail(result),
    )


async def _execute_service(
    service: Callable[..., Dict[str, Any]],
    *args: Any,
    error_is_fatal: Optional[Callable[[Dict[str, Any]], bool]] = None,
    tool_name: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await run_in_threadpool(service, *args, **kwargs)
    fatal_error = error_is_fatal(result) if error_is_fatal else "error" in result
    if fatal_error:
        _raise_service_http_error(result)
    resolved_tool_name = infer_tool_name_from_service(
        explicit_tool_name=tool_name,
        service_name=getattr(service, "__name__", None),
        kwargs=kwargs,
    )
    return attach_run_metadata(result, tool_name=resolved_tool_name)


async def _execute_registered_tool(
    tool_key: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    descriptor = get_tool_descriptor(tool_key)
    return await _execute_service(
        descriptor.service,
        tool_name=descriptor.key,
        **kwargs,
    )


def _flatten_bazi_birth_for_legacy_destiny_route(result: Dict[str, Any]) -> Dict[str, Any]:
    bazi_birth = result.get("bazi_birth")
    if not isinstance(bazi_birth, dict):
        return result

    payload = {
        key: bazi_birth[key]
        for key in (
            "person_info",
            "four_pillars",
            "day_master",
            "element_distribution",
            "favorable_elements",
            "ten_gods",
            "structure_profile",
            "patterns",
            "calendar_context",
        )
        if key in bazi_birth
    }

    if "snapshot_text" in result:
        payload["snapshot_text"] = result["snapshot_text"]
    if "snapshot_export" in result:
        payload["snapshot_export"] = result["snapshot_export"]
    if "run_metadata" in result:
        payload["run_metadata"] = result["run_metadata"]

    return payload


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
        default=False, description="Enable true solar time correction"
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


class BaziDirectRequest(BaziBirthRequest):
    """Request model for standalone BaZi direct output."""


class TwoPersonCompatibilityRequest(BaseModel):
    """Request model for two-person compatibility analysis."""

    person1_name: str = Field(description="First person name")
    person1_birth_year: int = Field(description="First person birth year, e.g., 1990")
    person1_birth_month: int = Field(
        ge=1, le=12, description="First person birth month"
    )
    person1_birth_day: int = Field(ge=1, le=31, description="First person birth day")
    person1_birth_hour: int = Field(ge=0, le=23, description="First person birth hour")
    person1_gender: str = Field(default="未知", description="First person gender")
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
        default=False, description="Enable true solar time for first person"
    )
    person2_name: str = Field(description="Second person name")
    person2_birth_year: int = Field(description="Second person birth year, e.g., 1992")
    person2_birth_month: int = Field(
        ge=1, le=12, description="Second person birth month"
    )
    person2_birth_day: int = Field(ge=1, le=31, description="Second person birth day")
    person2_birth_hour: int = Field(ge=0, le=23, description="Second person birth hour")
    person2_gender: str = Field(default="未知", description="Second person gender")
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
        default=False, description="Enable true solar time for second person"
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

    gender: str = Field(description="Gender used for dayun direction rules")
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
    gender: Optional[bool] = Field(
        default=None, description="Optional gender flag passthrough"
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

    domain: str = Field(description="Knowledge domain: astro, liureng, or qimen")
    category: str = Field(description="Category within the domain")
    key: Optional[str] = Field(default=None, description="Primary lookup key")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
    aspect_degree: Optional[int] = Field(
        default=None,
        description="Optional aspect degree for astro aspect lookups",
    )
    object_a: Optional[str] = Field(default=None, description="First astro object")
    object_b: Optional[str] = Field(default=None, description="Second astro object")
    jiang_name: Optional[str] = Field(default=None, description="Liureng general name")
    tian_branch: Optional[str] = Field(
        default=None, description="Liureng heaven branch"
    )
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
    szchart: int = Field(default=0, description="Chart mode flag")
    szshape: int = Field(default=0, description="Chart shape flag")
    house_start_mode: int = Field(
        default=1, alias="houseStartMode", description="House start mode"
    )
    doubing_su28: bool = Field(
        default=True,
        alias="doubingSu28",
        description="Whether to double-check su28 labels",
    )
    hsys: int = Field(
        default=8,
        description="Offline house system selector; standard suzhan supports 0..8 with the same FateBridge local house semantics as core chart",
    )
    zodiacal: int = Field(
        default=0,
        description="Offline zodiac selector; standard suzhan supports 0=tropical and 1=sidereal(Lahiri-like)",
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
        default=False,
        description="Enable local true solar time correction before sanshi aggregation",
    )


class ZiweiBirthRequest(FateBridgeRequest):
    """Request model for Zi Wei birth chart analysis."""

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
    gender: Optional[str] = Field(default="未知", description="Gender")
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Optional snapshot section titles for filtered export payload",
    )
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
        default=False, description="Enable true solar time correction"
    )


class TaiyiAnalysisRequest(QimenAnalysisRequest):
    """Request model for Taiyi analysis."""

    gender: Optional[str] = Field(default="未知", description="Gender")


class JinkouAnalysisRequest(LiuRengGodsRequest):
    """Request model for Jin Kou analysis."""

    di_fen: Optional[str] = Field(default=None, description="Ground division branch")


class AstroBirthRequest(BaseModel):
    """Base birth request model for offline astrology endpoints."""

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


class AstroChartRequest(AstroBirthRequest):
    """Request model for offline astrology chart generation."""

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


class AstroRelativePartyRequest(AstroBirthRequest):
    """One side of a relative/synastry request."""


class AstroRelativeRequest(BaseModel):
    """Request model for relative / synastry chart generation."""

    inner: AstroRelativePartyRequest
    outer: AstroRelativePartyRequest
    _mode_input_source: str = PrivateAttr(default="default")
    relative_mode: Optional[str | int] = Field(
        default=None,
        description=(
            "Modern relative mode selector, e.g. 0/1/2/3/4, Comp, Composite, "
            "Synastry, TimeSpace, or Marks; when using relative_mode, "
            "Synastry/synastry will resolve to the Horosa-style influence chart"
        ),
    )
    relationship_mode: Optional[str | int] = Field(
        default=None,
        description=(
            "Legacy alias for relative_mode; relationship_mode='synastry' is "
            "preserved as FateBridge's older compare-mode compatibility path"
        ),
    )
    hsys: int = Field(
        default=0,
        description="Legacy-compatible house system identifier; offline mode currently supports 0..8 via local Swiss house cusps",
    )
    zodiacal: int = Field(
        default=0,
        description="Legacy-compatible zodiac selector; offline mode currently supports 0=tropical and 1=sidereal(Lahiri-like) only",
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
    house_system: str = Field(
        default="P", description="House system identifier, e.g. P for Placidus"
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
        logger.info(
            "Processing calculation request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_bazi_birth,
            person,
            tool_name="analyze_destiny",
        )

        logger.info("Calculation successful")
        return _flatten_bazi_birth_for_legacy_destiny_route(result)

    except ValueError:
        logger.warning("Invalid input received for calculation route")
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during calculation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/bazi/birth")
async def calculate_bazi_birth_chart(request: BaziBirthRequest) -> dict:
    """
    Calculate a standalone BaZi birth chart with export-ready snapshot sections.
    """
    try:
        logger.info(
            "Processing bazi birth request (%s)",
            summarize_request_context(name=request.name),
        )
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

        result = await _execute_service(
            calculate_bazi_birth,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            selected_sections=request.selected_sections or None,
            tool_name="bazi_birth",
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的八字命盘参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during bazi birth analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/bazi/direct")
async def calculate_bazi_direct_chart(request: BaziDirectRequest) -> dict:
    """
    Calculate standalone BaZi direct timing output with export-ready snapshot sections.
    """
    try:
        logger.info(
            "Processing bazi direct request (%s)",
            summarize_request_context(name=request.name),
        )
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

        result = await _execute_service(
            calculate_bazi_direct,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            selected_sections=request.selected_sections or None,
            tool_name="bazi_direct",
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的八字直断参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during bazi direct analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/compatibility")
async def calculate_two_person_compatibility(
    request: TwoPersonCompatibilityRequest,
) -> dict:
    """
    Calculate two-person compatibility using FateBridge's offline compatibility engine.
    """
    try:
        logger.info(
            "Processing compatibility request (%s)",
            summarize_request_context(
                identifiers=[request.person1_name, request.person2_name]
            ),
        )

        person1 = create_person_info(
            birth_year=request.person1_birth_year,
            birth_month=request.person1_birth_month,
            birth_day=request.person1_birth_day,
            birth_hour=request.person1_birth_hour,
            name=request.person1_name,
            gender=request.person1_gender,
            birth_place=request.person1_birth_place,
            birth_minute=request.person1_birth_minute,
            birth_timezone=request.person1_birth_timezone,
            birth_longitude=request.person1_birth_longitude,
            use_true_solar_time=request.person1_use_true_solar_time,
        )
        person2 = create_person_info(
            birth_year=request.person2_birth_year,
            birth_month=request.person2_birth_month,
            birth_day=request.person2_birth_day,
            birth_hour=request.person2_birth_hour,
            name=request.person2_name,
            gender=request.person2_gender,
            birth_place=request.person2_birth_place,
            birth_minute=request.person2_birth_minute,
            birth_timezone=request.person2_birth_timezone,
            birth_longitude=request.person2_birth_longitude,
            use_true_solar_time=request.person2_use_true_solar_time,
        )

        result = await _execute_service(
            calculate_compatibility_analysis,
            person1,
            person2,
            request.relationship_type,
            tool_name="two_person_compatibility",
        )

        logger.info("Compatibility analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的双人配合分析参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during compatibility analysis: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/comprehensive")
async def calculate_timing_analysis(request: TimingAnalysisRequest) -> dict:
    """
    Calculate comprehensive timing analysis using FateBridge's offline timing engine.
    """
    try:
        logger.info(
            "Processing comprehensive timing request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_comprehensive_timing,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_age=request.analysis_age,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            selected_sections=request.selected_sections or None,
            tool_name="timing_analysis",
        )

        logger.info("Comprehensive timing analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的综合时运分析参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during comprehensive timing analysis: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/dayun")
async def calculate_dayun(request: DayunAnalysisRequest) -> dict:
    """
    Calculate dayun analysis using FateBridge's offline timing engine.
    """
    try:
        logger.info(
            "Processing dayun analysis request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_dayun_analysis,
            person,
            request.analysis_age,
            selected_sections=request.selected_sections or None,
            error_is_fatal=lambda payload: "error" in payload
            and payload.get("analysis_type") is None,
            tool_name="dayun_analysis",
        )

        logger.info("Dayun analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的大运分析参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during dayun analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/liunian")
async def calculate_liunian(request: LiunianAnalysisRequest) -> dict:
    """
    Calculate liunian analysis using FateBridge's offline timing engine.
    """
    try:
        logger.info(
            "Processing liunian analysis request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_liunian_analysis,
            person,
            request.target_year,
            selected_sections=request.selected_sections or None,
            tool_name="liunian_analysis",
        )

        logger.info("Liunian analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的流年分析参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during liunian analysis: {str(e)}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check() -> JSONResponse:
    """Readiness endpoint that reports required and optional runtime checks."""
    payload = _build_readiness_payload()
    status_code = 200 if payload["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=payload)


@app.get("/metrics")
async def metrics_endpoint() -> PlainTextResponse:
    """Prometheus-style text metrics for request volume and readiness state."""
    readiness_status = _build_readiness_payload()["status"]
    return PlainTextResponse(
        REQUEST_METRICS.render_prometheus(
            readiness_status=readiness_status,
            api_key_auth_enabled=API_KEY_AUTHENTICATOR.enabled,
            configured_api_keys=len(API_KEY_AUTHENTICATOR.api_keys),
            api_key_daily_quota=API_KEY_QUOTA_TRACKER.daily_quota,
        ),
        media_type="text/plain; version=0.0.4",
    )


@app.post("/api/divination/gua")
async def calculate_gua_description(request: GuaLookupRequest) -> dict:
    """
    Look up offline trigram/hexagram meanings by name or binary code.
    """
    try:
        logger.info("Processing gua lookup request")

        result = await _execute_service(
            calculate_gua_lookup,
            query=request.query,
            lookup_mode=request.lookup_mode,
            selected_sections=request.selected_sections or None,
        )

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
        logger.info("Processing jieqi year helper request")

        result = await _execute_service(calculate_jieqi_year, **request.model_dump())

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
        logger.info("Processing nongli time helper request")

        result = await _execute_service(calculate_nongli_time, **request.model_dump())

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
        logger.info("Processing gua meiyi helper request")

        payload = request.model_dump()
        result = await _execute_service(
            calculate_gua_meiyi,
            name=payload["name"],
            selected_sections=payload.get("selected_sections") or None,
        )

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
    Return the local AI export registry in FateBridge format.
    """
    try:
        logger.info("Processing export registry request")

        result = await _execute_registered_tool(
            "export_registry",
            **request.model_dump(),
        )

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
    Parse snapshot text into FateBridge export sections.
    """
    try:
        logger.info("Processing export parse request")

        payload = request.model_dump(by_alias=True)
        result = await _execute_registered_tool(
            "export_parse",
            technique=payload["technique"],
            content=payload["content"],
            selected_sections=payload.get("selected_sections") or None,
            planet_info=payload.get("planetInfo"),
            astro_meaning=payload.get("astroMeaning"),
        )

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
    List bundled knowledge domains and categories with optional section export.
    """
    try:
        logger.info("Processing knowledge registry request")

        payload = request.model_dump()
        result = await _execute_registered_tool(
            "knowledge_registry",
            **{
                **payload,
                "selected_sections": payload.get("selected_sections") or None,
            },
        )

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
    Read one bundled knowledge entry by domain/category/key with optional section export.
    """
    try:
        logger.info("Processing knowledge read request")

        payload = request.model_dump()
        result = await _execute_registered_tool(
            "knowledge_read",
            **{
                **payload,
                "selected_sections": payload.get("selected_sections") or None,
            },
        )

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
        logger.info("Processing meihua analysis request")

        result = await _execute_service(
            calculate_meihua_analysis,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            question=request.question,
        )

        logger.info("Meihua analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during meihua analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/tongshefa")
async def calculate_tongshefa(request: TongSheFaRequest) -> dict:
    """Calculate local tongshefa analysis."""
    try:
        logger.info("Processing tongshefa request")
        result = await _execute_service(
            calculate_tongshefa_analysis,
            taiyin=request.taiyin,
            taiyang=request.taiyang,
            shaoyang=request.shaoyang,
            shaoyin=request.shaoyin,
        )

        logger.info("Tongshefa analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的统摄法参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during tongshefa analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/sixyao")
async def calculate_sixyao(request: SixYaoRequest) -> dict:
    """Calculate local sixyao analysis."""
    try:
        logger.info("Processing sixyao request")
        result = await _execute_service(
            calculate_sixyao_analysis,
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

        logger.info("Sixyao analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六爻参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during sixyao analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/suzhan")
async def calculate_suzhan(request: SuZhanRequest) -> dict:
    """Calculate local suzhan analysis."""
    try:
        logger.info("Processing suzhan request")
        result = await _execute_service(
            calculate_suzhan_analysis,
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
            hsys=request.hsys,
            zodiacal=request.zodiacal,
        )

        logger.info("Suzhan analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的宿占参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during suzhan analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/otherbu")
async def calculate_otherbu(request: OtherBuRequest) -> dict:
    """Calculate local otherbu analysis."""
    try:
        logger.info("Processing otherbu request")
        result = await _execute_service(
            calculate_otherbu_analysis,
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
            hsys=request.hsys,
            zodiacal=request.zodiacal,
            question=request.question,
        )

        logger.info("Otherbu analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的占星骰子参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during otherbu analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/divination/sanshiunited")
async def calculate_sanshiunited(request: SanShiUnitedRequest) -> dict:
    """Calculate local sanshiunited analysis with stable qimen content metadata and export-ready snapshot sections."""
    try:
        logger.info("Processing sanshiunited request")
        result = await _execute_service(
            calculate_sanshiunited_analysis,
            date=request.date,
            time=request.time,
            zone=request.zone,
            lat=request.lat,
            lon=request.lon,
            gps_lat=request.gps_lat,
            gps_lon=request.gps_lon,
            qimen_options=request.qimen_options,
            taiyi_options=request.taiyi_options,
            selected_sections=request.selected_sections or None,
            liureng_yue=request.liureng_yue,
            liureng_is_diurnal=request.liureng_is_diurnal,
            use_true_solar_time=request.use_true_solar_time,
        )

        logger.info("Sanshiunited analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的三式合一参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during sanshiunited analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/ziwei/birth")
async def calculate_ziwei_birth_chart(request: ZiweiBirthRequest) -> dict:
    """
    Calculate a Zi Wei birth chart with offline snapshot text and export sections.
    """
    try:
        logger.info(
            "Processing ziwei birth request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_ziwei_birth,
            person,
            selected_sections=request.selected_sections or None,
        )

        logger.info("Ziwei birth calculation successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during ziwei birth analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/ziwei/rules")
async def get_ziwei_rules(request: ZiweiRulesRequest) -> dict:
    """
    Return the Zi Wei rule catalogue, optionally filtered by year stem and export sections.
    """
    try:
        logger.info("Processing ziwei rules request")
        result = await _execute_service(
            calculate_ziwei_rules,
            year_stem=request.year_stem,
            selected_sections=request.selected_sections or None,
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的紫微规则查询参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during ziwei rule lookup: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/liureng/gods")
async def get_liureng_gods(request: LiuRengGodsRequest) -> dict:
    """
    Calculate a Liu Ren divination board with offline snapshot text and export sections.
    """
    try:
        logger.info("Processing liureng gods request")
        result = await _execute_service(
            calculate_liureng_gods,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            selected_sections=request.selected_sections or None,
            use_true_solar_time=request.use_true_solar_time,
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六壬参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during LiuReng gods analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/liureng/runyear")
async def get_liureng_runyear(request: LiuRengRunyearRequest) -> dict:
    """
    Calculate a Liu Ren runyear analysis using birth context, with offline snapshot export support.
    """
    try:
        logger.info(
            "Processing liureng runyear request (%s)",
            summarize_request_context(name=request.name),
        )
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
        result = await _execute_service(
            calculate_liureng_runyear,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            selected_sections=request.selected_sections or None,
            use_true_solar_time=request.use_true_solar_time,
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的六壬行年参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during LiuReng runyear analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/cn/qimen")
async def get_qimen_analysis(request: QimenAnalysisRequest) -> dict:
    """
    Calculate a Qi Men Dun Jia board with offline snapshot text, export sections, and optional local layout transforms.
    """
    try:
        logger.info("Processing qimen request")
        result = await _execute_service(
            calculate_qimen_analysis,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            qimen_options=request.qimen_options,
            selected_sections=request.selected_sections or None,
            use_true_solar_time=request.use_true_solar_time,
            tool_name="qimen",
        )

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
    Calculate a Taiyi board with offline snapshot text and export sections.
    """
    try:
        logger.info("Processing taiyi request")
        result = await _execute_service(
            calculate_taiyi_analysis,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            selected_sections=request.selected_sections or None,
            use_true_solar_time=request.use_true_solar_time,
            tool_name="taiyi",
        )

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
    Calculate a Jin Kou board with offline snapshot text and export sections.
    """
    try:
        logger.info("Processing jinkou request")
        result = await _execute_service(
            calculate_jinkou_analysis,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            analysis_timezone=request.analysis_timezone,
            analysis_longitude=request.analysis_longitude,
            gender=request.gender or "未知",
            di_fen=request.di_fen,
            selected_sections=request.selected_sections or None,
            use_true_solar_time=request.use_true_solar_time,
            tool_name="jinkou",
        )

        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的金口诀参数")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during jinkou analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


async def _run_astro_chart_variant(
    request: AstroChartRequest, chart_variant: str
) -> dict:
    return await _execute_service(
        calculate_core_chart_analysis,
        tool_name=chart_variant if chart_variant in {"chart", "chart13"} else {
            "hellen_chart": "astro_hellen_chart",
            "guolao_chart": "astro_guolao_chart",
            "india_chart": "astro_india_chart",
        }.get(chart_variant, "astro_chart"),
        chart_variant=chart_variant,
        **request.model_dump(),
    )


@app.post("/api/astro/chart")
async def calculate_astro_chart(request: AstroChartRequest) -> dict:
    """Generate a core offline astrology chart with local ephemeris preference."""
    try:
        logger.info(
            "Processing astrology chart request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _run_astro_chart_variant(request, "chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during chart calculation: %s", str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/chart13")
async def calculate_astro_chart13(request: AstroChartRequest) -> dict:
    """Generate an experimental 13-sector chart overlay."""
    try:
        logger.info(
            "Processing chart13 request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _run_astro_chart_variant(request, "chart13")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during chart13 calculation: %s", str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/hellen")
async def calculate_hellen_chart(request: AstroChartRequest) -> dict:
    """Generate a Hellenistic-leaning whole-sign chart."""
    try:
        logger.info(
            "Processing hellen chart request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _run_astro_chart_variant(request, "hellen_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during hellen chart calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/guolao")
async def calculate_guolao_chart(request: AstroChartRequest) -> dict:
    """Generate a Guolao/Qizheng-Siyu inspired chart view."""
    try:
        logger.info(
            "Processing guolao chart request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _run_astro_chart_variant(request, "guolao_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during guolao chart calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/india")
async def calculate_india_chart(request: AstroChartRequest) -> dict:
    """Generate a sidereal / India-style chart view."""
    try:
        logger.info(
            "Processing india chart request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _run_astro_chart_variant(request, "india_chart")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during india chart calculation: %s", str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/germany")
async def calculate_germany_chart(request: AstroChartRequest) -> dict:
    """Generate midpoint / germany style analysis."""
    try:
        logger.info(
            "Processing germany chart request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _execute_service(
            calculate_germany_chart_analysis,
            tool_name="germany",
            **request.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during germany chart calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/relative")
async def calculate_relative_chart(request: AstroRelativeRequest) -> dict:
    """Generate synastry / relative chart output for two people."""
    try:
        logger.info(
            "Processing relative chart request (%s)",
            summarize_request_context(
                name=request.inner.name,
                identifiers=[request.relative_mode, request.relationship_mode],
            ),
        )
        return await _execute_service(
            calculate_relative_chart_analysis,
            inner_payload=request.inner.model_dump(),
            outer_payload=request.outer.model_dump(),
            relative_mode=request.relative_mode,
            relationship_mode=request.relationship_mode,
            relative_mode_source=request.mode_input_source or "default",
            hsys=request.hsys,
            zodiacal=request.zodiacal,
            tool_name="astro_relative_chart",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during relative chart calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/timing")
async def calculate_western_timing(request: WesternTimingRequest) -> dict:
    """Generate western predictive timing output for a target analysis date."""
    try:
        logger.info(
            "Processing western timing request (%s)",
            summarize_request_context(name=request.name),
        )
        return await _execute_service(
            calculate_western_timing_analysis,
            tool_name="western_timing_analysis",
            **request.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during western timing calculation: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


async def _run_western_timing_module_request(
    *,
    request: WesternTimingModuleRequest,
    tool_key: str,
) -> dict:
    try:
        descriptor = get_tool_descriptor(tool_key)
        logger.info(
            "Processing %s request (%s)",
            descriptor.key,
            summarize_request_context(name=request.name),
        )
        return await _execute_registered_tool(
            tool_key,
            **request.model_dump(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during %s calculation: %s",
            tool_key,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/astro/timing/solarreturn")
async def calculate_solarreturn_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone solar return output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="solarreturn",
    )


@app.post("/api/astro/timing/lunarreturn")
async def calculate_lunarreturn_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone lunar return output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="lunarreturn",
    )


@app.post("/api/astro/timing/transit")
async def calculate_transit_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone transit chart output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="transit",
    )


@app.post("/api/astro/timing/solararc")
async def calculate_solararc_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone solar arc output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="solararc",
    )


@app.post("/api/astro/timing/givenyear")
async def calculate_givenyear_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone given-year chart output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="givenyear",
    )


@app.post("/api/astro/timing/profection")
async def calculate_profection_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone annual profection output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="profection",
    )


@app.post("/api/astro/timing/pd")
async def calculate_pd_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone primary-directions output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="pd",
    )


@app.post("/api/astro/timing/pdchart")
async def calculate_pdchart_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone primary-direction-chart output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="pdchart",
    )


@app.post("/api/astro/timing/zr")
async def calculate_zr_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone zodiacal releasing output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="zr",
    )


@app.post("/api/astro/timing/firdaria")
async def calculate_firdaria_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone firdaria output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="firdaria",
    )


@app.post("/api/astro/timing/decennials")
async def calculate_decennials_module(request: WesternTimingModuleRequest) -> dict:
    """Generate standalone decennials output."""
    return await _run_western_timing_module_request(
        request=request,
        tool_key="decennials",
    )


@app.post("/api/timing/liuyue")
async def calculate_liuyue(request: LiuyueAnalysisRequest) -> dict:
    """
    Calculate liuyue analysis for the jieqi month containing the analysis date.
    """
    try:
        logger.info(
            "Processing liuyue analysis request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_liuyue_analysis,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            selected_sections=request.selected_sections or None,
        )

        logger.info("Liuyue analysis successful")
        return result

    except ValueError:
        raise HTTPException(status_code=400, detail="无效的输入参数，请检查日期有效性")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error during liuyue analysis: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="内部服务器错误")


@app.post("/api/timing/liuri")
async def calculate_liuri(request: LiuriAnalysisRequest) -> dict:
    """
    Calculate liuri analysis for a specific analysis date.
    """
    try:
        logger.info(
            "Processing liuri analysis request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_liuri_analysis,
            person,
            analysis_year=request.analysis_year,
            analysis_month=request.analysis_month,
            analysis_day=request.analysis_day,
            analysis_hour=request.analysis_hour,
            analysis_minute=request.analysis_minute,
            selected_sections=request.selected_sections or None,
        )

        logger.info("Liuri analysis successful")
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
        logger.info(
            "Processing jieqi timeline request (%s)",
            summarize_request_context(name=request.name),
        )

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

        result = await _execute_service(
            calculate_jieqi_timeline_analysis,
            person,
            target_year=request.target_year,
            selected_sections=request.selected_sections or None,
        )

        logger.info("Jieqi timeline analysis successful")
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


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8010")),
        log_level=get_log_level().lower(),
    )


if __name__ == "__main__":
    main()
