"""Lightweight discovery and shared execution failures across all adapters."""

import asyncio
import json
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from pydantic import BaseModel

import fatebridge.api as api
import fatebridge.application.execution as execution
import fatebridge.mcp_server as mcp
from fatebridge.application.description import describe_input_spec, describe_spec
from fatebridge.application.tool_spec import ToolSpec
from fatebridge.cli import run as cli_run
from fatebridge.core.schema_cache import clear_contract_caches
from tests.fixtures.surface_payloads import REST_POST_CASES


def test_input_discovery_does_not_materialize_output_schema():
    class Request(BaseModel):
        value: int

    class Output(BaseModel):
        value: int
        schema_calls: ClassVar[int] = 0

        @classmethod
        def model_json_schema(cls, **kwargs):
            cls.schema_calls += 1
            return super().model_json_schema(**kwargs)

    spec = ToolSpec(
        key="review_probe",
        bind=lambda request: (lambda: {"value": request.value}, (), {}),
        request_model=Request,
        output_model=Output,
        summary="Probe",
        operation_label_zh="探针",
        family="test",
    )
    clear_contract_caches()
    try:
        compact = describe_input_spec(spec)
        assert Output.schema_calls == 0
        assert compact["output_fields"] == ["value"]
        full = describe_spec(spec)
        assert Output.schema_calls == 1
        assert {key: compact[key] for key in full if key != "output_schema"} == {
            key: value for key, value in full.items() if key != "output_schema"
        }
    finally:
        clear_contract_caches()


@pytest.mark.parametrize("stage", ["attachment", "validation"])
def test_metadata_failures_are_internal_and_correlated_in_all_transports(
    monkeypatch, capsys, caplog, stage
):
    from fatebridge.services import run_metadata

    def fail(*args, **kwargs):
        raise ValueError("private-server-error")

    if stage == "attachment":
        monkeypatch.setattr(run_metadata, "attach_run_metadata", fail)
    else:
        original = execution.validate_output

        def validate(spec, result):
            if "run_metadata" in result:
                raise execution.OutputContractError("private-server-error")
            return original(spec, result)

        monkeypatch.setattr(execution, "validate_output", validate)

    monkeypatch.setattr(
        api,
        "API_KEY_AUTHENTICATOR",
        api.ApiKeyAuthenticator(header_name="X-API-Key", api_keys={}),
    )
    inputs = REST_POST_CASES["/api/cn/bazi/birth"]()
    controls = {"trace_id": "review-trace", "parent_run_id": "review-parent"}
    http = TestClient(api.app).post("/api/cn/bazi/birth", json=inputs, params=controls)

    async def call():
        async with Client(mcp.app) as client:
            return await client.call_tool(
                "bazi_birth", {**inputs, **controls}, raise_on_error=False
            )

    protocol = asyncio.run(call())
    args = ["bazi_birth"]
    for key, value in {**inputs, **controls}.items():
        if value is not None:
            args += [
                "--" + key.replace("_", "-"),
                json.dumps(value) if isinstance(value, bool) else str(value),
            ]
    code = cli_run(args)
    cli_output = json.loads(capsys.readouterr().out)
    assert http.status_code == 500 and protocol.is_error and code == 1
    assert json.loads(protocol.content[0].text) == protocol.structured_content
    payloads = [http.json(), protocol.structured_content, cli_output]
    for payload in payloads:
        assert payload["error_code"] == "internal_error"
        assert payload["trace_id"] == controls["trace_id"]
        assert payload["parent_run_id"] == controls["parent_run_id"]
        assert "private" not in json.dumps(payload)
    # REST conveys status on the HTTP response; MCP also labels the operation.
    normalized = [
        {
            key: value
            for key, value in payload.items()
            if key not in {"status_code", "operation"}
        }
        for payload in payloads
    ]
    assert normalized[0] == normalized[1] == normalized[2]
    # Sanitization must preserve the actual failure in server-side diagnostics.
    assert any(
        record.exc_info and "private-server-error" in str(record.exc_info[1])
        for record in caplog.records
        if record.name == "fatebridge.utils.errors"
    )
