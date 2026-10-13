"""Golden computations isolate ephemeris data and restore caller state."""

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from fatebridge.core import ephemeris_runtime as runtime
from fatebridge.core.almanac import get_solar_terms_for_year
from tests.golden import runner


@pytest.mark.parametrize("original_env", [None, "", "/operator/ephe"])
@pytest.mark.parametrize("fail", [False, True])
@pytest.mark.parametrize("configured", [None, "local"])
def test_compute_outputs_forces_moshier_and_restores_state(
    monkeypatch, tmp_path, original_env, fail, configured
):
    swe = pytest.importorskip("swisseph")
    original_path = runtime.configured_ephemeris_path()
    local_ephe = tmp_path / "ephe"
    local_ephe.mkdir()
    (local_ephe / "sepl_18.se1").write_bytes(b"local-data-must-not-be-read")
    monkeypatch.setattr(runtime, "_PROJECT_ROOT", tmp_path)
    if original_env is None:
        monkeypatch.delenv("SE_EPHE_PATH", raising=False)
    else:
        monkeypatch.setenv("SE_EPHE_PATH", original_env)
    previous_configured = str(local_ephe) if configured else None
    monkeypatch.setattr(runtime, "_configured_path", previous_configured)
    calls = []
    real_set_path = swe.set_ephe_path

    def set_path(path):
        calls.append(path)
        return real_set_path(path)

    monkeypatch.setattr(swe, "set_ephe_path", set_path)
    monkeypatch.setattr(runner, "REST_POST_CASES", {"/probe": lambda: {}})
    monkeypatch.setattr(runner, "_MCP_ONLY_CASES", {})
    isolated_paths = []

    class Client:
        def __init__(self, app):
            pass

        def post(self, path, json):
            directory = runtime.configured_ephemeris_path()
            isolated_paths.append(directory)
            assert directory == os.environ["SE_EPHE_PATH"]
            assert directory != str(local_ephe)
            assert list(Path(directory).iterdir()) == []
            assert get_solar_terms_for_year.cache_info().currsize == 0
            # Real C-library return flags prove the actual model, not just config.
            _, flag = runtime.ephemeris_call(
                "calc_ut", 2451545.0, swe.SUN, swe.FLG_SWIEPH
            )
            assert runtime.ephemeris_model_from_retflag(flag) == "moshier"
            get_solar_terms_for_year(2026)
            return SimpleNamespace(
                status_code=500 if fail else 200,
                text="probe error",
                json=lambda: {"model": "moshier"},
            )

    monkeypatch.setattr(runner, "TestClient", Client)
    # Pre-existing terms must be invalidated, as must terms built inside golden.
    get_solar_terms_for_year(2025)
    assert get_solar_terms_for_year.cache_info().currsize > 0
    try:
        if fail:
            with pytest.raises(AssertionError, match="probe error"):
                runner.compute_outputs()
        else:
            assert json.loads(runner.compute_outputs()["probe"]) == {"model": "moshier"}
        assert os.environ.get("SE_EPHE_PATH") == original_env
        assert runtime.configured_ephemeris_path() == previous_configured
        assert calls[-1] == (previous_configured or "")
        assert get_solar_terms_for_year.cache_info().currsize == 0
        assert all(not Path(path).exists() for path in isolated_paths)
    finally:
        # Our local-path probe is fake; restore the real C path for sibling tests.
        monkeypatch.undo()
        with runtime._EPHEMERIS_LOCK:
            real_set_path(original_path or "")
