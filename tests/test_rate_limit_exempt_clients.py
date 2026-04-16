import asyncio
import sys
from pathlib import Path

from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api as api_module
from fatebridge.utils.runtime import parse_rate_limit_exempt_clients


def _build_request(
    *,
    client_host: str,
    path: str = "/api/divination/gua",
    method: str = "POST",
) -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": b"",
            "headers": [],
            "client": (client_host, 12345),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive=receive,
    )


def test_parse_rate_limit_exempt_clients_filters_blank_entries(monkeypatch):
    monkeypatch.setenv(
        "RATE_LIMIT_EXEMPT_CLIENTS",
        "127.0.0.1, ::1, ,10.0.0.5",
    )

    assert parse_rate_limit_exempt_clients() == [
        "127.0.0.1",
        "::1",
        "10.0.0.5",
    ]


def test_loopback_client_bypasses_request_rate_limit(monkeypatch):
    api_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api_module,
        "REQUEST_RATE_LIMITER",
        api_module.RequestRateLimiter(max_requests=1, window_seconds=60),
    )
    monkeypatch.setattr(
        api_module,
        "RATE_LIMIT_EXEMPT_CLIENTS",
        frozenset({"127.0.0.1"}),
    )

    async def fake_call_next(_request):
        return api_module.JSONResponse(status_code=200, content={"ok": True})

    first = asyncio.run(
        api_module.instrument_request_lifecycle(
            _build_request(client_host="127.0.0.1"),
            fake_call_next,
        )
    )
    second = asyncio.run(
        api_module.instrument_request_lifecycle(
            _build_request(client_host="127.0.0.1"),
            fake_call_next,
        )
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_non_exempt_client_still_hits_request_rate_limit(monkeypatch):
    api_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api_module,
        "REQUEST_RATE_LIMITER",
        api_module.RequestRateLimiter(max_requests=1, window_seconds=60),
    )
    monkeypatch.setattr(
        api_module,
        "RATE_LIMIT_EXEMPT_CLIENTS",
        frozenset({"127.0.0.1"}),
    )

    async def fake_call_next(_request):
        return api_module.JSONResponse(status_code=200, content={"ok": True})

    first = asyncio.run(
        api_module.instrument_request_lifecycle(
            _build_request(client_host="198.51.100.10"),
            fake_call_next,
        )
    )
    second = asyncio.run(
        api_module.instrument_request_lifecycle(
            _build_request(client_host="198.51.100.10"),
            fake_call_next,
        )
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["retry-after"] == "60"
