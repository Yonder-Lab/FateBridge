"""Guard normally loaded call contracts against interface and projection drift."""

import importlib.util
from pathlib import Path

import pytest
from fastmcp import Client
from jsonschema import ValidationError, validate

from fatebridge.application.examples import example_input
from fatebridge.mcp_server import create_mcp_app
from fatebridge.services.tool_catalog import CATALOG

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "codex_contract_builder", ROOT / "scripts/build_codex_call_contracts.py"
)
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)


@pytest.mark.asyncio
async def test_normally_loaded_contracts_match_current_public_interface():
    guide = (ROOT / "AGENTS.md").read_text()
    block = guide.split(builder.BEGIN, 1)[1].split(builder.END, 1)[0]
    assert builder.BEGIN + block + builder.END == await builder.render_block()


@pytest.mark.asyncio
async def test_preloaded_contract_keeps_required_time_and_solar_flag_constraints():
    record = (await builder.call_contracts())[0]
    spec = next(s for s in CATALOG if s.tool_name == record["tool"])
    params = example_input(spec)
    validate(params, record["input"])
    for invalid in [
        {k: v for k, v in params.items() if k != "birth_hour"},
        {**params, "birth_hour": 24},
        {**params, "use_true_solar_time": None},
        {**params, "birth_latitude": 39.9},
    ]:
        with pytest.raises(ValidationError):
            validate(invalid, record["input"])
    validate({**params, "use_true_solar_time": False}, record["input"])


@pytest.mark.asyncio
async def test_only_preloaded_inputs_and_views_are_enough_for_real_mcp_calls():
    records = await builder.call_contracts()
    specs = {s.tool_name: s for s in CATALOG}
    async with Client(create_mcp_app()) as client:
        for record in records:
            params = {
                **example_input(specs[record["tool"]]),
                **record["first_view"],
                "as_of": "2026-10-12T12:00:00+08:00",
            }
            validate(params, record["input"])
            result = await client.call_tool(record["tool"], params)
            assert not result.is_error
            payload = result.structured_content
            assert payload["run_metadata"]["tool_name"] == record["tool"]
            if record["tool"] == "bazi_career":
                assert payload["career_analysis"]["career_structure"]["score"] == 75
                assert "timing_context" in payload["career_analysis"]
            elif record["tool"] == "two_person_compatibility":
                assert payload["summary"]["overall_score"] == 54.5
                assert "score_basis" in payload["traditional_compatibility"]
            else:
                assert "analysis_calendar" in payload
                assert "time_adjustment" in payload["personal_info"]


def test_schema_annotations_do_not_remove_similarly_named_input_properties():
    source = {
        "title": "Schema",
        "properties": {
            "title": {"title": "Field", "type": "string"},
            "description": {"description": "Field", "type": "integer"},
        },
    }
    assert builder.without_annotations(source) == {
        "properties": {"title": {"type": "string"}, "description": {"type": "integer"}}
    }
