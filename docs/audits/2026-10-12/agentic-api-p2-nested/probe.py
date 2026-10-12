"""Reproduce local public nested-schema and three-transport evidence."""

import asyncio
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient
from fastmcp import Client

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
sys.path.insert(0, str(ROOT))

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.core.discovery import discover_specs
from fatebridge.core.tool_spec import spec_is_cli_safe
from fatebridge.services.tool_catalog import CATALOG
from tests.test_agentic_nested_outputs import (
    AS_OF,
    SCHEMA_LEAVES,
    SPECS,
    business,
    inputs,
    rest_spec,
    schema_leaf,
)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


async def main():
    api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(
        header_name="X-API-Key", api_keys={}
    )
    rest = TestClient(api.app)
    openapi = rest.get("/openapi.json").json()
    manifest = rest.get("/api/tools").json()
    contract_checks = []
    calls = []
    async with Client(mcp.app) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        for key, path, expected in SCHEMA_LEAVES:
            spec = SPECS[key]
            central = spec.output_model.model_json_schema()
            native = tools[spec.tool_name].outputSchema
            endpoint = rest_spec(spec).rest_path
            http_schema = openapi["paths"][endpoint]["post"]["responses"]["200"][
                "content"
            ]["application/json"]["schema"]
            assert schema_leaf(central, central, path)["type"] == expected
            assert schema_leaf(native, native, path)["type"] == expected
            assert schema_leaf(openapi, http_schema, path)["type"] == expected
            contract_checks.append({"tool": key, "path": path, "type": expected})
        with tempfile.TemporaryDirectory(prefix="fatebridge-nested-") as tmp:
            for key, field in [
                ("pd", "pd.current_coordinate_points.Ascendant.coordinate_degrees"),
                ("decennials", "decennials.current_level_3.sublevel"),
                ("ziwei_birth", "ziwei_birth.palaces"),
            ]:
                spec = SPECS[key]
                request = inputs(spec)
                response = rest.post(
                    spec.rest_path,
                    json=request,
                    params={
                        "as_of": AS_OF,
                        "fields": field,
                        "strict_fields": True,
                        "include_snapshot_text": False,
                    },
                )
                protocol = await client.call_tool(
                    spec.tool_name,
                    {
                        **request,
                        "as_of": AS_OF,
                        "fields": [field],
                        "strict_fields": True,
                        "include_snapshot_text": False,
                    },
                )
                subject = Path(tmp) / "subject.json"
                subject.write_text(json.dumps(request, ensure_ascii=False))
                command = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "fatebridge.cli",
                        "--no-metadata",
                        spec.tool_name,
                        "--subject-file",
                        str(subject),
                        "--as-of",
                        AS_OF,
                        "--fields",
                        field,
                        "--strict-fields",
                        "--no-include-snapshot-text",
                    ],
                    text=True,
                    capture_output=True,
                    timeout=40,
                )
                cli = json.loads(command.stdout)
                assert (
                    response.status_code == 200
                    and not protocol.is_error
                    and command.returncode == 0
                )
                assert (
                    business(response.json())
                    == business(protocol.structured_content)
                    == cli
                )
                assert (
                    json.loads(protocol.content[0].text) == protocol.structured_content
                )
                calls.append(
                    {
                        "tool": key,
                        "field": field,
                        "rest_status": response.status_code,
                        "mcp_is_error": protocol.is_error,
                        "cli_exit": command.returncode,
                        "business_equal": True,
                        "projected_business": cli,
                    }
                )
        native_records = [
            tool.model_dump(mode="json", by_alias=True) for tool in tools.values()
        ]
    async with Client(mcp.create_mcp_app(scenarios="onda-jiankang")) as client:
        profile = [
            tool.model_dump(mode="json", by_alias=True)
            for tool in await client.list_tools()
        ]
    metrics = {
        "catalog_count": len(CATALOG),
        "rest_count": sum(bool(s.rest_path) for s in CATALOG),
        "mcp_count": len(tools),
        "cli_count": sum(spec_is_cli_safe(s) for s in CATALOG),
        "mcp_full_tools_utf8_bytes": len(compact(native_records)),
        "mcp_health_tools_count": len(profile),
        "mcp_health_tools_utf8_bytes": len(compact(profile)),
        "rest_full_manifest_utf8_bytes": len(compact(manifest)),
        "rest_summary_manifest_utf8_bytes": len(
            compact(discover_specs(CATALOG, detail="summary"))
        ),
        "mcp_full_tools_sha256": hashlib.sha256(compact(native_records)).hexdigest(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **{pkg: version(pkg) for pkg in ["fastmcp", "fastapi", "pydantic"]},
        },
    }
    write("contract-checks.json", contract_checks)
    write("three-surface-projections.json", calls)
    write("metrics.json", metrics)
    write(
        "representative-output-schemas.json",
        {
            key: SPECS[key].output_model.model_json_schema()
            for key in ["pd", "decennials", "ziwei_birth", "sanshiunited"]
        },
    )
    write(
        "source-sha256.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "src").rglob("*.py"))
        },
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
