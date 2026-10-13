"""Local native-client evidence for scenario discovery and replay receipts."""

import asyncio
import hashlib
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient
from fastmcp import Client

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.application.scenarios import discover_scenarios, scenario_keys
from fatebridge.application.description import spec_is_cli_safe
from fatebridge.services.replay_metadata import digest
from fatebridge.services.tool_catalog import CATALOG

OUT = Path(__file__).resolve().parent
CONTROLS = {"as_of": "2024-02-29T16:30:00Z", "trace_id": "p2-replay-evidence"}
BIRTH = {
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_place": "上海",
    "birth_timezone": "Asia/Shanghai",
    "gender": "男",
    "use_true_solar_time": False,
}
SIXYAO = {
    "date": "2026-10-12",
    "time": "10:00",
    "zone": "Asia/Shanghai",
    "method": "coin",
}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def compact_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


def business(value):
    return {key: data for key, data in value.items() if key != "run_metadata"}


def cli(name, inputs, controls=None):
    args = [sys.executable, "-m", "fatebridge.cli", name]
    for key, value in {**inputs, **(controls or {})}.items():
        args += [
            "--" + key.replace("_", "-"),
            str(value).lower() if isinstance(value, bool) else str(value),
        ]
    result = subprocess.run(args, capture_output=True, text=True, timeout=40)
    return result.returncode, json.loads(result.stdout)


async def main():
    api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(
        header_name="X-API-Key", api_keys={}
    )
    rest = TestClient(api.app)
    scenario_manifest = rest.get("/api/scenarios", params={"surface": "mcp"}).json()
    code, scenario_cli = cli("scenarios", {"surface": "mcp", "detail": "full"})
    assert code == 0 and scenario_cli == scenario_manifest
    write("scenario-manifest.json", scenario_manifest)
    write("openapi.json", api.app.openapi())
    receipts = {}
    async with Client(mcp.app) as client:
        tools = [
            tool.model_dump(mode="json", by_alias=True)
            for tool in await client.list_tools()
        ]
        write("mcp-tools.json", tools)
        for record in scenario_manifest["scenarios"]:
            resource = json.loads(
                (await client.read_resource("fatebridge://scenarios/" + record["id"]))[
                    0
                ].text
            )
            assert resource["scenarios"][0] == record
        for name, path, inputs in (
            ("bazi_birth", "/api/cn/bazi/birth", BIRTH),
            ("sixyao", "/api/divination/sixyao", SIXYAO),
        ):
            original = rest.post(path, json=inputs, params=CONTROLS)
            assert original.status_code == 200
            receipt = original.json()["run_metadata"]
            replay_inputs = {**inputs, **receipt["replay"]["overrides"]}
            replay_controls = {**CONTROLS, "as_of": receipt["replay"]["as_of"]}
            response = rest.post(path, json=replay_inputs, params=replay_controls)
            protocol = await client.call_tool(
                name, {**replay_inputs, **replay_controls}, raise_on_error=False
            )
            code, command = cli(name, replay_inputs, replay_controls)
            assert response.status_code == 200 and not protocol.is_error and code == 0
            assert (
                business(original.json())
                == business(response.json())
                == business(protocol.structured_content)
                == business(command)
            )
            assert receipt["business_output_sha256"] == digest(business(command))
            receipts[name] = {
                "business_equal": True,
                "original": receipt,
                "rest": response.json()["run_metadata"],
                "mcp": protocol.structured_content["run_metadata"],
                "cli": command["run_metadata"],
            }
        bad = {**BIRTH, "birth_day": 0}
        http = rest.post("/api/cn/bazi/birth", json=bad, params=CONTROLS)
        protocol = await client.call_tool(
            "bazi_birth", {**bad, **CONTROLS}, raise_on_error=False
        )
        code, command = cli("bazi_birth", bad, CONTROLS)
        assert http.status_code == 422 and protocol.is_error and code == 1
        write(
            "correlation-error-probes.json",
            {"rest": http.json(), "mcp": protocol.structured_content, "cli": command},
        )
    write("replay-probes.json", receipts)
    async with Client(mcp.create_mcp_app(scenarios="onda-jiankang")) as client:
        profile = [
            tool.model_dump(mode="json", by_alias=True)
            for tool in await client.list_tools()
        ]
        names = {tool["name"] for tool in profile}
        expected = {
            spec.tool_name
            for spec in CATALOG
            if spec.key in scenario_keys(CATALOG, "onda-jiankang") and spec.mcp_name
        }
        assert names == expected
        write("health-profile-tools.json", profile)
    summary = {
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "worktree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
        ),
        "environment": {
            key: version(key) for key in ("fastapi", "fastmcp", "pydantic", "kerykeion")
        },
        "python": sys.version.split()[0],
        "counts": {
            "catalog": len(CATALOG),
            "rest": sum(bool(spec.rest_path) for spec in CATALOG),
            "mcp": len(tools),
            "cli": sum(spec_is_cli_safe(spec) for spec in CATALOG),
            "scenarios": len(scenario_manifest["scenarios"]),
        },
        "utf8_bytes": {
            "mcp_all_tools": compact_size(tools),
            "mcp_health_profile_tools": compact_size(profile),
            "scenario_manifest_full_mcp": compact_size(scenario_manifest),
            "scenario_manifest_summary_mcp": compact_size(
                discover_scenarios(CATALOG, surface="mcp", detail="summary")
            ),
            "bazi_receipt": compact_size(receipts["bazi_birth"]["original"]),
        },
        "scope": "Local REST TestClient, native in-memory FastMCP Client and CLI subprocesses; UTF-8 bytes, not tokens/latency; original sample input is fictional",
    }
    write("summary.json", summary)
    root = Path.cwd()
    paths = [
        str(path.relative_to(root))
        for path in sorted((root / "src/fatebridge").rglob("*.py"))
    ]
    paths += [
        "src/fatebridge/data/agent_scenarios.json",
        "scripts/build_scenario_manifest.py",
        "tests/test_agentic_replay.py",
        "tests/golden/runner.py",
    ]
    write(
        "source-hashes.json",
        {
            path: hashlib.sha256((root / path).read_bytes()).hexdigest()
            for path in paths
        },
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
