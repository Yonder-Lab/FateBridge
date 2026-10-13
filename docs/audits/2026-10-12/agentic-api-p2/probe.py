"""Reproducible local P2 probes and UTF-8 discovery-size measurements."""

import asyncio
import json
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient
from fastmcp import Client

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.application.description import spec_is_cli_safe
from fatebridge.services.tool_catalog import CATALOG

OUT = Path(__file__).resolve().parent
BIRTH = {
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "gender": "男",
    "birth_place": "上海",
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": False,
    "analysis_year": 2026,
    "analysis_month": 10,
    "analysis_day": 12,
}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


def command(args):
    result = subprocess.run(
        [sys.executable, "-m", "fatebridge.cli", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, json.loads(result.stdout)


async def main():
    api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(
        header_name="X-API-Key", api_keys={}
    )
    rest = TestClient(api.app)
    write("openapi.json", api.app.openapi())
    full = rest.get("/api/tools")
    summary = rest.get("/api/tools", params={"detail": "summary"})
    selected = rest.get(
        "/api/tools", params={"detail": "summary", "family": "bazi", "surface": "mcp"}
    )
    exit_code, cli_summary = command(
        ["discover", "--family", "bazi", "--surface", "mcp"]
    )
    assert exit_code == 0 and cli_summary == selected.json()
    write("summary-manifest.json", summary.json())
    projections = {}
    async with Client(mcp.app) as client:
        tools = [
            tool.model_dump(mode="json", by_alias=True)
            for tool in await client.list_tools()
        ]
        write("mcp-tools.json", tools)
        family = json.loads(
            (await client.read_resource("fatebridge://families/bazi"))[0].text
        )
        assert family == selected.json()
        for strict in (False, True):
            fields = ["bazi_birth.day_master", "bazi_birth.day_mastr"]
            http = rest.post(
                "/api/cn/bazi/birth",
                json=BIRTH,
                params={"fields": fields, "strict_fields": str(strict).lower()},
            )
            result = await client.call_tool(
                "bazi_birth",
                {**BIRTH, "fields": fields, "strict_fields": strict},
                raise_on_error=False,
            )
            args = ["bazi_birth"]
            for key, value in BIRTH.items():
                args += [
                    "--" + key.replace("_", "-"),
                    str(value).lower() if isinstance(value, bool) else str(value),
                ]
            code, cli_payload = command(
                [*args, "--strict-fields", str(strict).lower(), "--fields", *fields]
            )
            assert (
                http.status_code == (422 if strict else 200)
                and result.is_error is strict
                and code == int(strict)
            )
            issue_key = "issues" if strict else "projection_warnings"
            assert (
                http.json()[issue_key]
                == result.structured_content[issue_key]
                == cli_payload[issue_key]
            )
            projections["strict" if strict else "compatible"] = {
                "rest": {"status": http.status_code, "body": http.json()},
                "mcp": {"is_error": result.is_error, "body": result.structured_content},
                "cli": {"exit_code": code, "body": cli_payload},
            }
    async with Client(mcp.create_mcp_app("bazi,knowledge")) as profile:
        profile_tools = [
            tool.model_dump(mode="json", by_alias=True)
            for tool in await profile.list_tools()
        ]
        profile_manifest = json.loads(
            (await profile.read_resource("fatebridge://catalog/summary"))[0].text
        )
        assert (
            profile_manifest
            == rest.get(
                "/api/tools",
                params={
                    "detail": "summary",
                    "family": "bazi,knowledge",
                    "surface": "mcp",
                },
            ).json()
        )
    write("projection-probes.json", projections)
    write(
        "summary.json",
        {
            "date": "2026-10-12",
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "worktree_dirty": True,
            "environment": {
                "python": platform.python_version(),
                **{
                    name: version(name)
                    for name in ("fastapi", "fastmcp", "pydantic", "kerykeion")
                },
            },
            "catalog_count": len(CATALOG),
            "rest_count": sum(bool(s.rest_path) for s in CATALOG),
            "mcp_count": len(tools),
            "cli_count": sum(spec_is_cli_safe(s) for s in CATALOG),
            "mcp_annotations_count": sum(bool(tool["annotations"]) for tool in tools),
            "rest_discovery_utf8_bytes": {
                "full": len(full.content),
                "summary": len(summary.content),
                "bazi_mcp_summary": len(selected.content),
            },
            "mcp_tools_utf8_bytes": {
                "full": size(tools),
                "bazi_knowledge_profile": size(profile_tools),
            },
            "profile_tool_count": len(profile_tools),
            "scope": "Local REST TestClient, native in-memory MCP Client and actual CLI subprocesses; byte sizes, not token counts or latency",
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
