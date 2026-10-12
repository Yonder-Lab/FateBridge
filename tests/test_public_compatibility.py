"""Public Python adapters remain thin and preserve the historical contracts."""

import asyncio
import json
import subprocess
import sys

import pytest
from fastmcp import Client

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.core import request_models
from tests.fixtures.transports import rest_handler


def test_rest_python_aliases_use_mounted_endpoints_and_canonical_models():
    for alias, key in api._REST_HANDLER_ALIASES.items():
        assert getattr(api, alias) is rest_handler(key)
    for name, model in vars(request_models).items():
        if name.endswith("Request") and hasattr(api, name):
            assert getattr(api, name) is model


@pytest.mark.parametrize(
    "arguments",
    [
        {"name": ["111", "000"], "compact": False, "include_snapshot_text": False},
        {"name": ["111"], "fields": ["missing"], "strict_fields": True},
    ],
)
def test_legacy_mcp_text_matches_native_success_and_error_payloads(arguments):
    legacy = mcp.gua_meiyi.fn(**arguments)

    async def run():
        async with Client(mcp.app) as client:
            result = await client.call_tool(
                "gua_meiyi", arguments, raise_on_error=False
            )
            text = result.content[0].text
            # Compare complete text after removing only per-execution metadata.
            old, new = json.loads(legacy), json.loads(text)
            old.pop("run_metadata", None)
            new.pop("run_metadata", None)
            assert (
                old
                == new
                == {
                    k: v
                    for k, v in result.structured_content.items()
                    if k != "run_metadata"
                }
            )
            assert result.is_error is ("error_code" in new)
            if not arguments.get("strict_fields"):
                assert "\n" in legacy and "\n" in text
                assert "snapshot_text" not in new

    asyncio.run(run())


def test_native_registration_does_not_use_text_roundtrip_adapter(monkeypatch):
    import fatebridge.mcp_transport as transport

    def forbidden(*args, **kwargs):
        raise AssertionError("native registration must not use the legacy text adapter")

    monkeypatch.setattr(transport, "native_tool_function", forbidden)
    server = mcp.create_mcp_app(families="divination")

    async def run():
        async with Client(server) as client:
            result = await client.call_tool("gua_meiyi", {"name": ["111"]})
            assert json.loads(result.content[0].text) == result.structured_content

    asyncio.run(run())


def test_mcp_import_inside_running_loop_has_no_coroutine_warning():
    code = """
import asyncio, gc, warnings
warnings.simplefilter('error', RuntimeWarning)
async def load():
    import fatebridge.mcp_server as module
    assert callable(module.gua_meiyi.fn)
    gc.collect()
asyncio.run(load())
"""
    proc = subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "never awaited" not in proc.stderr
