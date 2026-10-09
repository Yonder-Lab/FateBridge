"""Regressions through FastMCP's real validation/default injection path."""

import asyncio
import json
from typing import Any

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from fatebridge.core.request_models import (
    FateBridgeRequest,
    TwoPersonCompatibilityRequest,
)
from fatebridge.core.tool_spec import ToolSpec, pair_invoke, register_mcp
from fatebridge.services.tool_catalog import CATALOG

BIRTH = dict(birth_year=1990, birth_month=6, birth_day=15, birth_hour=10, gender="男")
ANALYSIS = dict(analysis_year=2024, analysis_month=6, analysis_day=15, analysis_hour=10)


def _app(spec: ToolSpec) -> FastMCP:
    app = FastMCP("audit regression")
    register_mcp(
        app,
        [spec],
        render_response=lambda result, **kwargs: json.dumps(result),
        render_error=lambda result, *args, **kwargs: json.dumps(result),
    )
    return app


async def _call(client: Client, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = await client.call_tool(name, payload)
    return json.loads(result.content[0].text)


@pytest.mark.parametrize("name,payload", [("bazi_birth", BIRTH), ("qimen", ANALYSIS)])
def test_real_mcp_omission_and_explicit_solar_flags(name, payload):
    spec = next(spec for spec in CATALOG if spec.tool_name == name)

    async def run():
        async with Client(_app(spec)) as client:
            schema = (await client.list_tools())[0].inputSchema
            solar = schema["properties"]["use_true_solar_time"]
            assert solar["type"] == "boolean"
            assert solar["default"] is True
            assert "use_true_solar_time" not in schema["required"]
            # Missing coordinates degrade only when correction was omitted.
            assert "error" not in await _call(client, name, payload)
            assert "error" in await _call(
                client, name, {**payload, "use_true_solar_time": True}
            )
            assert "error" not in await _call(
                client, name, {**payload, "use_true_solar_time": False}
            )
            with pytest.raises(ToolError):
                await _call(client, name, {**payload, "use_true_solar_time": None})
            assert "error" not in await _call(client, name, payload)

    asyncio.run(run())


def test_real_mcp_pair_keeps_each_person_explicitness_separate():
    def service(person1, person2, relationship):
        return {
            "solar": [person1.use_true_solar_time, person2.use_true_solar_time],
            "explicit": [person1.true_solar_explicit, person2.true_solar_explicit],
        }

    spec = ToolSpec(
        key="pair",
        bind=pair_invoke(service),
        request_model=TwoPersonCompatibilityRequest,
        summary="Pair omission regression",
        operation_label_zh="测试",
        family="test",
    )
    payload = {
        **{f"person1_{key}": value for key, value in BIRTH.items()},
        **{f"person2_{key}": value for key, value in BIRTH.items()},
        "person1_name": "A",
        "person2_name": "B",
    }

    async def run():
        async with Client(_app(spec)) as client:
            assert await _call(client, "pair", payload) == {
                "solar": [True, True],
                "explicit": [False, False],
            }
            assert await _call(
                client,
                "pair",
                {
                    **payload,
                    "person1_use_true_solar_time": False,
                    "person2_use_true_solar_time": True,
                },
            ) == {"solar": [False, True], "explicit": [True, True]}
            with pytest.raises(ToolError):
                await _call(
                    client, "pair", {**payload, "person1_use_true_solar_time": None}
                )

    asyncio.run(run())


def test_real_mcp_exposes_constraints_descriptions_and_keeps_canonical_names():
    class Request(BaseModel):
        model_config = ConfigDict(populate_by_name=True)

        birth_month: int = FateBridgeRequest.model_fields["birth_month"]
        use_true_solar_time: bool = Field(
            default=True, alias="useTrueSolarTime", description="Correction flag"
        )

    def bind(request):
        return (
            lambda: {
                "month": request.birth_month,
                "solar": request.use_true_solar_time,
                "explicit": "use_true_solar_time" in request.model_fields_set,
            },
            (),
            {},
        )

    spec = ToolSpec(
        key="schema",
        bind=bind,
        request_model=Request,
        summary="Schema regression",
        operation_label_zh="测试",
        family="test",
    )

    async def run():
        async with Client(_app(spec)) as client:
            schema = (await client.list_tools())[0].inputSchema
            month = schema["properties"]["birth_month"]
            reference = FateBridgeRequest.model_json_schema()["properties"][
                "birth_month"
            ]
            for key in ("minimum", "maximum", "description", "type"):
                assert month[key] == reference[key]
            assert schema["properties"]["use_true_solar_time"]["default"] is True
            assert await _call(client, "schema", {"birth_month": 6}) == {
                "month": 6,
                "solar": True,
                "explicit": False,
            }
            assert "useTrueSolarTime" not in schema["properties"]
            assert await _call(
                client, "schema", {"birth_month": 6, "use_true_solar_time": False}
            ) == {"month": 6, "solar": False, "explicit": True}
            with pytest.raises(ToolError):
                await _call(client, "schema", {"birth_month": 13})

    asyncio.run(run())
