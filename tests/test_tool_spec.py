"""Transport-agnostic tool_spec helpers (shared by REST/MCP/CLI)."""

import inspect

import pytest
from pydantic import BaseModel

from fatebridge.core.tool_spec import ToolSpec, _make_mcp_fn, project_fields
from fatebridge.services.tool_catalog import CATALOG


def test_project_fields_keeps_subset_and_always_run_metadata():
    payload = {
        "analysis_type": "x",
        "detailed_analysis": {"big": "blob"},
        "run_metadata": {"run_id": "r"},
    }
    out = project_fields(payload, ["analysis_type"])
    assert set(out) == {"analysis_type", "run_metadata"}
    assert out["run_metadata"]["run_id"] == "r"


def test_project_fields_none_or_empty_is_identity():
    payload = {"a": 1, "b": 2}
    assert project_fields(payload, None) == payload
    assert project_fields(payload, []) == payload


def test_project_fields_ignores_unknown_keys():
    payload = {"a": 1, "run_metadata": {}}
    out = project_fields(payload, ["a", "no_such_key"])
    assert set(out) == {"a", "run_metadata"}


def _fake_renderers():
    captured = {}

    def render_response(result, **kwargs):
        captured["result"] = result
        captured.update(kwargs)
        return "ok"

    def render_error(result, operation, **kwargs):
        captured["error_result"] = result
        return "err"

    return captured, render_response, render_error


def test_mcp_fn_exposes_fields_param_and_threads_it():
    spec = next(s for s in CATALOG if s.rest_path == "/api/cn/bazi/wealth")
    captured, render_response, render_error = _fake_renderers()
    fn = _make_mcp_fn(spec, render_response=render_response, render_error=render_error)

    assert "fields" in inspect.signature(fn).parameters

    fn(
        birth_year=1990,
        birth_month=6,
        birth_day=15,
        birth_hour=10,
        gender="male",
        dayun_pillar="壬戌",
        fields=["wealth_analysis"],
    )
    assert captured["fields"] == ["wealth_analysis"]


def test_mcp_fn_reserved_field_clash_raises():
    class Bad(BaseModel):
        fields: list = []

    spec = ToolSpec(
        key="bad",
        bind=lambda req: (lambda: {}, (), {}),
        request_model=Bad,
        summary="",
        operation_label_zh="",
        family="",
    )
    _, render_response, render_error = _fake_renderers()
    with pytest.raises(ValueError):
        _make_mcp_fn(spec, render_response=render_response, render_error=render_error)
