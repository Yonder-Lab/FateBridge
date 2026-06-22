from __future__ import annotations

"""
FastAPI REST server for FateBridge calculations.
Provides HTTP endpoints for birth analysis, timing, and divination calculations.
"""

import asyncio
import hmac
import logging
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Any, Callable, Dict, Optional, Tuple

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from fatebridge.core import astrology as astrology_core
from fatebridge.core import predictive as astrology_predictive_core

# Re-exported so callers and tests can import request models from `api`
# directly (the canonical definitions live in fatebridge.core.request_models).
from fatebridge.core.request_models import (  # noqa: F401
    AstroBirthRequest,
    AstroChartRequest,
    AstroRelativePartyRequest,
    AstroRelativeRequest,
    BaziBirthRequest,
    BaziCareerRequest,
    BaziChildrenRequest,
    BaziEducationRequest,
    BaziHealthRequest,
    BaziMarriageRequest,
    BaziWealthRequest,
    DayunAnalysisRequest,
    ExportParseRequest,
    ExportRegistryRequest,
    FateBridgeRequest,
    GuaLookupRequest,
    GuaMeiyiRequest,
    JieqiTimelineRequest,
    JieqiYearRequest,
    JinkouAnalysisRequest,
    KnowledgeReadRequest,
    KnowledgeRegistryRequest,
    LiunianAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    LiuriAnalysisRequest,
    LiushiAnalysisRequest,
    LiuyueAnalysisRequest,
    MeihuaAnalysisRequest,
    NongliTimeRequest,
    OtherBuRequest,
    QimenAnalysisRequest,
    SanShiUnitedRequest,
    SixYaoLineRequest,
    SixYaoRequest,
    SuZhanRequest,
    TaiyiAnalysisRequest,
    TimingAnalysisRequest,
    TongSheFaRequest,
    TwoPersonCompatibilityRequest,
    WesternTimingModuleRequest,
    WesternTimingRequest,
    ZiweiBirthRequest,
    ZiweiRulesRequest,
)

# Re-exported for back-compat / test identity checks: some tests assert the
# threadpool offload runs exactly these service objects via `api.<name>`.
from fatebridge.services.astrology import (  # noqa: F401
    calculate_core_chart_analysis,
    calculate_relative_chart_analysis,
)
from fatebridge.services.bazi import calculate_bazi_birth  # noqa: F401
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.services.western_timing import (  # noqa: F401
    calculate_western_timing_analysis,
)
from fatebridge.utils.runtime import (
    get_api_key_header_name,
    get_log_level,
    load_runtime_env,
    parse_allowed_origins,
    parse_api_keys,
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


def _default_heavy_calc_max_concurrency() -> int:
    return min(4, max(1, os.cpu_count() or 1))


HEAVY_CALC_MAX_CONCURRENCY = max(
    1,
    _get_env_int(
        "FATEBRIDGE_HEAVY_CALC_MAX_CONCURRENCY",
        _default_heavy_calc_max_concurrency(),
    ),
)
HEAVY_CALC_SEMAPHORE: Optional[asyncio.Semaphore] = None
HEAVY_CALC_SEMAPHORE_LOOP: Optional[asyncio.AbstractEventLoop] = None


def _prometheus_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


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
        # Order-stable list for constant-time comparison against every secret.
        self._known_secrets: Tuple[Tuple[bytes, str], ...] = tuple(
            (secret.encode("utf-8"), key_id) for key_id, secret in self.api_keys.items()
        )

    @property
    def enabled(self) -> bool:
        return bool(self._known_secrets)

    def authenticate(self, request: Request) -> Optional[str]:
        if not self.enabled:
            return None

        secret = request.headers.get(self.header_name)
        if not secret:
            return None

        # hmac.compare_digest avoids short-circuiting on mismatch byte,
        # preventing timing-based key probing. We must compare against every
        # configured secret unconditionally so total runtime does not leak
        # how many candidates matched a prefix of the supplied value.
        candidate_bytes = secret.encode("utf-8")
        matched_id: Optional[str] = None
        for known_secret, key_id in self._known_secrets:
            if hmac.compare_digest(candidate_bytes, known_secret):
                matched_id = key_id
        return matched_id


API_KEY_EXEMPT_PATHS = frozenset(
    {
        "/health",
        "/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
)
API_KEY_AUTHENTICATOR = ApiKeyAuthenticator(
    header_name=API_KEY_HEADER_NAME,
    api_keys=parse_api_keys(),
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
    }
    required_checks_ok = all(
        item["ok"] for item in checks.values() if item.get("required")
    )
    return {
        "status": "ready" if required_checks_ok else "not_ready",
        "checks": checks,
    }


def _build_authentication_detail() -> Dict[str, Any]:
    return {
        "error": "缺少或无效的 API key",
        "error_code": "authentication_required",
        "retryable": False,
    }


def _reset_runtime_state_for_tests() -> None:
    global HEAVY_CALC_SEMAPHORE, HEAVY_CALC_SEMAPHORE_LOOP
    REQUEST_METRICS.reset()
    HEAVY_CALC_SEMAPHORE = None
    HEAVY_CALC_SEMAPHORE_LOOP = None


@app.middleware("http")
async def instrument_request_lifecycle(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    path = request.url.path
    method = request.method.upper()

    if method != "OPTIONS" and path not in API_KEY_EXEMPT_PATHS:
        if API_KEY_AUTHENTICATOR.enabled:
            authenticated_key_id = API_KEY_AUTHENTICATOR.authenticate(request)
            if authenticated_key_id is None:
                auth_response = JSONResponse(
                    status_code=401,
                    content=_build_authentication_detail(),
                )
                REQUEST_METRICS.observe(
                    method=method,
                    path=path,
                    status_code=401,
                    duration_seconds=0.0,
                )
                return auth_response

            request.state.api_key_id = authenticated_key_id

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


@app.exception_handler(HTTPException)
async def _http_error_envelope(request: Request, exc: HTTPException) -> JSONResponse:
    """Render every HTTPException as a flat top-level error envelope.

    REST historically nested the error under FastAPI's ``detail`` key, while MCP
    and the CLI emit a flat ``{error, error_code, retryable}``. This handler
    flattens the HTTP body so all three surfaces agree — an agent branches on the
    same top-level ``error_code`` everywhere — and backfills ``error_code`` for
    the bare-string 400/500 paths that previously carried none. The exception
    object keeps its ``.detail`` intact for in-process callers that inspect it.
    """
    detail = exc.detail
    if isinstance(detail, dict) and "error_code" in detail:
        body = {
            "error": detail.get("error"),
            "error_code": detail.get("error_code", "internal_error"),
            "retryable": detail.get("retryable", False),
        }
    else:
        body = {
            "error": detail,
            "error_code": (
                "validation_error" if exc.status_code == 400 else "internal_error"
            ),
            "retryable": False,
        }
    return JSONResponse(status_code=exc.status_code, content=body)


def _get_heavy_calc_semaphore() -> asyncio.Semaphore:
    global HEAVY_CALC_SEMAPHORE, HEAVY_CALC_SEMAPHORE_LOOP
    loop = asyncio.get_running_loop()
    if HEAVY_CALC_SEMAPHORE is not None and HEAVY_CALC_SEMAPHORE_LOOP is None:
        HEAVY_CALC_SEMAPHORE_LOOP = loop
        return HEAVY_CALC_SEMAPHORE
    if HEAVY_CALC_SEMAPHORE is None or HEAVY_CALC_SEMAPHORE_LOOP is not loop:
        HEAVY_CALC_SEMAPHORE = asyncio.Semaphore(HEAVY_CALC_MAX_CONCURRENCY)
        HEAVY_CALC_SEMAPHORE_LOOP = loop
    return HEAVY_CALC_SEMAPHORE


async def _run_heavy_calculation(
    service: Callable[..., Dict[str, Any]],
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    semaphore = _get_heavy_calc_semaphore()
    async with semaphore:
        return await run_in_threadpool(service, *args, **kwargs)


async def _execute_service(
    service: Callable[..., Dict[str, Any]],
    *args: Any,
    error_is_fatal: Optional[Callable[[Dict[str, Any]], bool]] = None,
    tool_name: Optional[str] = None,
    cpu_bound: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    if cpu_bound:
        result = await _run_heavy_calculation(service, *args, **kwargs)
    else:
        result = await run_in_threadpool(service, *args, **kwargs)
    fatal_error = error_is_fatal(result) if error_is_fatal else "error" in result
    if fatal_error:
        _raise_service_http_error(result)
    # tool_name is supplied by the catalog registrar (spec.run_metadata_name);
    # the neutral fallback only guards a stray non-catalog caller.
    return attach_run_metadata(result, tool_name=tool_name or "unknown_tool")


# ============================================================================
# Request/Response Models
# ============================================================================


# ============================================================================
# API Endpoints
# ============================================================================


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
        ),
        media_type="text/plain; version=0.0.4",
    )


# ============================================================================
# Main
# ============================================================================


# ============================================================================
# Catalog-driven REST registration. Every business POST route is declared once
# in fatebridge/services/tool_catalog.py and mounted here. To add a route, edit
# the catalog — not this file.
# ============================================================================

from fatebridge.core.tool_spec import (  # noqa: E402
    describe_spec,
    make_rest_handler,
    register_rest,
)
from fatebridge.services.tool_catalog import (  # noqa: E402
    CATALOG,
    mcp_specs,
    rest_specs,
)

register_rest(
    app,
    rest_specs(),
    execute_service=_execute_service,
    logger=logger,
)


@app.get("/api/tools")
async def list_tools() -> Dict[str, Any]:
    """Machine-readable capability manifest for agents.

    Returns the same self-describing record as ``fatebridge describe`` for every
    catalog tool — parameters, types, surfaces, family — so an agent can
    enumerate the framework's capabilities and call conventions without scraping
    the Markdown docs. Derived from the central ToolSpec catalog, so it never
    drifts from the live tool set.
    """
    return {
        "counts": {
            "rest": len(rest_specs()),
            "mcp": len(mcp_specs()),
            "total": len(CATALOG),
        },
        "tools": [describe_spec(spec) for spec in CATALOG],
    }


# Backward-compatible direct-call handlers. Older tests / integrations call the
# REST handlers as plain coroutines (e.g. ``await calculate_astro_chart(req)``);
# expose those names as catalog-driven handlers so they keep working.
_REST_HANDLER_ALIASES = {
    "calculate_destiny": "calculate_legacy",
    "calculate_two_person_compatibility": "two_person_compatibility",
    "calculate_astro_chart": "astro_chart",
    "calculate_relative_chart": "astro_relative",
    "calculate_timing_analysis": "timing_analysis",
    "calculate_dayun": "dayun_analysis",
    "calculate_liunian": "liunian_analysis",
    "calculate_liushi": "liushi_analysis",
    "calculate_western_timing": "western_timing_analysis",
    "calculate_solarreturn_module": "solarreturn",
    "calculate_pdchart_module": "pdchart",
    "get_qimen_analysis": "qimen",
    "get_taiyi_analysis": "taiyi",
    "get_jinkou_analysis": "jinkou",
    "knowledge_read_helper": "knowledge_read",
    "knowledge_registry_helper": "knowledge_registry",
    "export_registry_helper": "export_registry",
}
_SPECS_BY_KEY = {spec.key: spec for spec in rest_specs()}
for _alias, _key in _REST_HANDLER_ALIASES.items():
    globals()[_alias] = make_rest_handler(
        _SPECS_BY_KEY[_key],
        execute_service=_execute_service,
        http_exception=HTTPException,
        logger=logger,
    )


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8010")),
        log_level=get_log_level().lower(),
    )


if __name__ == "__main__":
    main()
