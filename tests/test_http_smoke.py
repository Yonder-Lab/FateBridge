import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api as api_module


def _build_client(monkeypatch) -> TestClient:
    api_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api_module,
        "API_KEY_AUTHENTICATOR",
        api_module.ApiKeyAuthenticator(header_name="X-API-Key", api_keys={}),
    )
    return TestClient(api_module.app)


def _assert_run_metadata(payload: dict, *, tool_name: str) -> None:
    metadata = payload.get("run_metadata")

    assert isinstance(metadata, dict)
    assert metadata["tool_name"] == tool_name
    assert metadata["engine"]
    assert metadata["run_id"]
    assert metadata["trace_id"]
    assert metadata["generated_at"]


HTTP_SMOKE_CASES = [
    (
        "/api/astro/chart",
        {
            "name": "测试者",
            "birth_year": 1990,
            "birth_month": 4,
            "birth_day": 6,
            "birth_hour": 9,
            "birth_minute": 33,
            "birth_timezone": "Asia/Shanghai",
            "birth_longitude": 121.4667,
            "birth_latitude": 31.2167,
            "birth_place": "上海",
        },
        "chart",
        lambda body: body["chart_profile"]["chart_type"] == "chart",
    ),
    (
        "/api/astro/timing/solarreturn",
        {
            "name": "Alice",
            "birth_year": 1990,
            "birth_month": 5,
            "birth_day": 17,
            "birth_hour": 15,
            "birth_minute": 30,
            "birth_place": "上海",
            "birth_timezone": "Asia/Shanghai",
            "birth_longitude": 121.4737,
            "birth_latitude": 31.2304,
            "analysis_year": 2025,
            "analysis_month": 5,
            "analysis_day": 20,
            "pd_method": "astroapp_alchabitius",
            "pd_time_key": "Naibod",
            "pd_aspects": [0, 90, 180],
            "show_pd_bounds": True,
        },
        "solarreturn",
        lambda body: body["analysis_type"] == "西占太阳返照",
    ),
    (
        "/api/cn/qimen",
        {
            "analysis_year": 2026,
            "analysis_month": 4,
            "analysis_day": 8,
            "analysis_hour": 9,
            "analysis_minute": 30,
            "analysis_timezone": "Asia/Shanghai",
            "analysis_longitude": 121.4737,
            "qimen_options": {"layout": "rotating"},
            "selected_sections": ["起盘信息", "九宫方盘"],
            "use_true_solar_time": False,
        },
        "qimen",
        lambda body: body["snapshot_export"]["technique"]["key"] == "qimen",
    ),
    (
        "/api/knowledge/registry",
        {
            "domain": "astro",
            "selected_sections": ["目录概览", "astro"],
        },
        "knowledge_registry",
        lambda body: body["domains"][0]["domain"] == "astro",
    ),
    (
        "/api/export/registry",
        {
            "technique": "qimen",
        },
        "export_registry",
        lambda body: body["selected_technique"]["key"] == "qimen",
    ),
]


@pytest.mark.parametrize(
    ("path", "payload", "tool_name", "assertion"),
    HTTP_SMOKE_CASES,
    ids=[
        "astro_chart",
        "solarreturn",
        "qimen",
        "knowledge_registry",
        "export_registry",
    ],
)
def test_http_smoke_endpoints_return_expected_payloads(
    monkeypatch,
    path,
    payload,
    tool_name,
    assertion,
):
    client = _build_client(monkeypatch)
    response = client.post(path, json=payload)

    if tool_name == "solarreturn" and response.status_code == 503:
        detail = response.json().get("detail", {})
        if (
            isinstance(detail, dict)
            and detail.get("error_code") == "dependency_missing"
        ):
            pytest.skip("western predictive runtime unavailable in test environment")

    assert response.status_code == 200
    body = response.json()
    _assert_run_metadata(body, tool_name=tool_name)
    assert assertion(body)
