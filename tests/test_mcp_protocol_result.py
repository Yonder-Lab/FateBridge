"""SDK 1.x and 2.x serialize the same native success/error wire contracts."""

import json

import pytest
from mcp.types import CallToolResult

from fatebridge.mcp_transport import protocol_result


@pytest.mark.parametrize(
    "payload,failed",
    [
        ({"layers": {"directions": {"ruleset": {"version": "1.0.0"}}}}, False),
        (
            {
                "error": "请求参数无效",
                "error_code": "validation_error",
                "retryable": False,
                "issues": [{"path": "fields", "code": "unknown_projection_path"}],
            },
            True,
        ),
    ],
)
def test_native_result_preserves_sdk_independent_wire_contract(payload, failed):
    result = protocol_result(payload, failed=failed).to_mcp_result()
    assert isinstance(result, CallToolResult)
    wire = result.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert wire["structuredContent"] == payload
    assert wire["isError"] is failed
    assert "structured_content" not in wire and "is_error" not in wire
    assert json.loads(wire["content"][0]["text"]) == payload
