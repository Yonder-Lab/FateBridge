import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api as api_module


def test_ready_endpoint_no_longer_reports_api_key_quota():
    api_module._reset_runtime_state_for_tests()
    client = TestClient(api_module.app)

    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert "api_key_quota" not in payload["checks"]


def test_metrics_endpoint_no_longer_exports_api_key_quota_metric():
    api_module._reset_runtime_state_for_tests()
    client = TestClient(api_module.app)

    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "fatebridge_api_key_daily_quota" not in response.text


def test_repeated_requests_are_not_rate_limited_even_when_legacy_limiter_is_injected(
    monkeypatch,
):
    class RejectAllLimiter:
        def check(self, *, client_id, path, now=None):
            return False, 60

    api_module._reset_runtime_state_for_tests()
    if hasattr(api_module, "REQUEST_RATE_LIMITER"):
        monkeypatch.setattr(
            api_module,
            "REQUEST_RATE_LIMITER",
            RejectAllLimiter(),
        )

    client = TestClient(api_module.app)

    first = client.post("/api/divination/gua", json={"query": "乾"})
    second = client.post("/api/divination/gua", json={"query": "乾"})

    assert first.status_code == 200
    assert second.status_code == 200


def test_api_key_requests_are_not_quota_limited_even_when_legacy_tracker_is_injected(
    monkeypatch,
):
    class ExhaustedQuotaTracker:
        enabled = True
        daily_quota = 1

        def check_and_consume(self, *, key_id, now=None):
            return False, 0, 60

    api_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api_module,
        "API_KEY_AUTHENTICATOR",
        api_module.ApiKeyAuthenticator(
            header_name="X-API-Key",
            api_keys={"agent": "secret-key"},
        ),
    )
    if hasattr(api_module, "API_KEY_QUOTA_TRACKER"):
        monkeypatch.setattr(
            api_module,
            "API_KEY_QUOTA_TRACKER",
            ExhaustedQuotaTracker(),
        )

    client = TestClient(api_module.app)
    headers = {"X-API-Key": "secret-key"}

    first = client.post("/api/divination/gua", json={"query": "乾"}, headers=headers)
    second = client.post("/api/divination/gua", json={"query": "乾"}, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
