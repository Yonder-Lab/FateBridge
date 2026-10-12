"""Linux REST/native MCP/independent CLI process contract and rules probe."""

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from fastmcp import Client
from jsonschema import Draft202012Validator

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.services.tool_catalog import CATALOG
from tests.fixtures.fengshui import payload

AS_OF = "2026-10-12T02:00:00Z"
spec = next(s for s in CATALOG if s.key == "fengshui_assess")
inputs = payload("assess")
natal = payload("xuankong_natal")
inputs["house"] = natal.pop("house")
inputs["xuankong"] = natal
inputs["methods"] = ["bazhai", "jinsuo", "annual_stars", "xuankong_natal"]
api._reset_runtime_state_for_tests()
api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(header_name="X-API-Key", api_keys={})


def business(data):
    return {key: value for key, value in data.items() if key != "run_metadata"}


async def main():
    results = []
    async with Client(mcp.app) as client:
        async_tools = {tool.name: tool for tool in await client.list_tools()}
        native_schema = async_tools[spec.tool_name].outputSchema
        for case in ["complete-four-layers", "projected-rules", "boundary-partial"]:
            request = json.loads(json.dumps(inputs))
            fields = []
            if case == "projected-rules":
                fields = ["layers." + layer + ".ruleset.version" for layer in inputs["methods"]]
            if case == "boundary-partial":
                request["house"]["facing_degrees"] = 355.5
            flags = {"as_of": AS_OF, "strict_fields": True, "include_snapshot_text": False}
            if fields:
                flags["fields"] = fields
            with TestClient(api.app) as rest:
                response = rest.post(spec.rest_path, json=request, params=flags)
            protocol = await client.call_tool(spec.tool_name, {**request, **flags})
            request_file = Path("/audit/" + case + ".json")
            request_file.write_text(json.dumps(request))
            command = [sys.executable, "-m", "fatebridge.cli", spec.tool_name,
                       "--request-file", str(request_file), "--as-of", AS_OF,
                       "--strict-fields", "--no-include-snapshot-text"]
            if fields:
                command += ["--fields", *fields]
            cli = subprocess.run(command, capture_output=True, text=True, check=True)
            cli_json = json.loads(cli.stdout)
            assert response.status_code == 200 and not protocol.is_error
            assert json.loads(protocol.content[0].text) == protocol.structured_content
            bodies = [response.json(), protocol.structured_content, cli_json]
            assert business(bodies[0]) == business(bodies[1]) == business(bodies[2])
            for data in bodies:
                spec.output_model.model_validate(data)
                Draft202012Validator(native_schema).validate(data)
                versions = {k: v["ruleset"]["version"] for k, v in data["layers"].items()}
                assert versions == {k: "1.0.1" if k == "xuankong_natal" else "1.0.0"
                                    for k in inputs["methods"]}
                if not fields:
                    for layer in data["layers"].values():
                        rules = layer["ruleset"]
                        assert rules["source_ids"] == [s["source_id"] for s in rules["sources"]]
                        assert all(s["scope"] and s["url"] for s in rules["sources"])
                    annual = data["layers"]["annual_stars"]
                    natal_layer = data["layers"]["xuankong_natal"]
                    assert annual["current_period"]["number"] == 9
                    assert natal_layer["period_context"]["number"] == 8
                    if case == "complete-four-layers":
                        assert data["status"] == "complete"
                        # Pinned external eight-period Geng-facing case: [8, 6, 1].
                        assert natal_layer["chart"]["palaces"]["C"]["mountain_star_number"] == 6
                    else:
                        assert data["status"] == "partial" and natal_layer["chart"] is None
            for key in ["contract_sha256", "input_sha256", "business_output_sha256"]:
                assert len({data["run_metadata"][key] for data in bodies}) == 1, key
            results.append({"case": case, "REST_status": response.status_code,
                            "MCP_is_error": protocol.is_error, "CLI_exit": cli.returncode,
                            "business_equal": True, "stable_receipt_hashes_equal": True,
                            "versions": versions})
    report = {"cases": results, "native_client_validation_enabled": True,
              "actual_cli_process": True, "ruleset_registry_sha256": {
                  p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in Path("src/fatebridge/data/fengshui").glob("*.json")}}
    Path("/audit/surface-contracts.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


asyncio.run(main())
