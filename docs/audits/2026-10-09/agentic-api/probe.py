"""Read-only local API/Agent review probes; no production calls or domain edits."""

import asyncio
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path

from fastapi.testclient import TestClient
from fastmcp import Client

import fatebridge.api as api
import fatebridge.mcp_server as mcp
from fatebridge.core.tool_spec import describe_spec
from fatebridge.services.tool_catalog import CATALOG

OUT = Path(__file__).resolve().parent
BIRTH = dict(
    birth_year=1990,
    birth_month=5,
    birth_day=15,
    birth_hour=10,
    birth_minute=30,
    gender="男",
    birth_place="北京",
    birth_timezone="Asia/Shanghai",
    use_true_solar_time=False,
    analysis_year=2026,
    analysis_month=10,
    analysis_day=9,
)


def write(name, value):
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())


async def main():
    # Only this probe process has auth disabled, to avoid using any configured key.
    api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(
        header_name="X-API-Key", api_keys={}
    )
    rest = TestClient(api.app)
    spec = api.app.openapi()
    write("openapi.json", spec)
    manifest = rest.get("/api/tools").json()
    write("manifest.json", manifest)
    operations = [
        (path, method, op)
        for path, item in spec["paths"].items()
        for method, op in item.items()
        if method in {"get", "post", "put", "patch", "delete"}
    ]
    rest_probes = {}
    for name, body, params in [
        ("missing_required", {}, None),
        ("range_error", {**BIRTH, "birth_month": 13}, None),
        ("invalid_calendar_date", {**BIRTH, "birth_month": 2, "birth_day": 30}, None),
        ("unknown_input", {**BIRTH, "birth_mintue": 59}, None),
        ("unknown_projection", BIRTH, [("fields", "bazi_birth.day_mastr")]),
        ("full_output", BIRTH, None),
        ("no_snapshot_text", BIRTH, [("include_snapshot_text", "false")]),
        ("projected_output", BIRTH, [("fields", "bazi_birth.day_master")]),
    ]:
        result = rest.post("/api/cn/bazi/birth", json=body, params=params)
        value = result.json()
        rest_probes[name] = dict(
            status=result.status_code, bytes=len(result.content), body=value
        )
    election = rest.post(
        "/api/astro/event/election",
        json=dict(
            candidate_year=2026,
            candidate_month=10,
            candidate_day=9,
            candidate_hour=10,
            longitude=116.4074,
            latitude=39.9042,
            timezone_name="Asia/Shanghai",
            topic_id="contrcat",
        ),
    )
    rest_probes["unknown_election_topic"] = dict(
        status=election.status_code, body=election.json()
    )
    write("rest-probes.json", rest_probes)
    mcp_probes = {}
    async with Client(mcp.app) as client:
        tools = await client.list_tools()
        write(
            "mcp-tools.json", [t.model_dump(mode="json", by_alias=True) for t in tools]
        )
        for name, body in [
            ("success", BIRTH),
            ("missing_required", {}),
            ("range_error", {**BIRTH, "birth_month": 13}),
            ("invalid_calendar_date", {**BIRTH, "birth_month": 2, "birth_day": 30}),
            ("unknown_input", {**BIRTH, "birth_mintue": 59}),
        ]:
            result = await client.call_tool("bazi_birth", body, raise_on_error=False)
            mcp_probes[name] = dict(
                is_error=result.is_error,
                structured_content=result.structured_content,
                content=[c.model_dump(mode="json") for c in result.content],
            )
        resources = await client.list_resources()
        prompts = await client.list_prompts()
    write("mcp-probes.json", mcp_probes)
    summary = dict(
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        python=platform.python_version(),
        packages={
            p: version(p) for p in ["fastapi", "fastmcp", "pydantic", "kerykeion"]
        },
        counts=manifest["counts"],
        rest_operations=len(operations),
        empty_business_success_schemas=sum(
            op["responses"]["200"]
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
            == {}
            for _, method, op in operations
            if method == "post"
        ),
        probe_scope="Local FastAPI TestClient and FastMCP in-memory Client; no remote host/deployment acceptance.",
        success_schema_examples={
            p: op["responses"]["200"].get("content", {})
            for p, method, op in operations
            if method == "post" and p in {"/api/cn/bazi/birth", "/api/astro/chart"}
        },
        security_schemes=spec.get("components", {}).get("securitySchemes"),
        error_response_codes=sorted(
            {
                code
                for _, _, op in operations
                for code in op["responses"]
                if code != "200"
            }
        ),
        manifest_bytes=size(manifest),
        mcp_tool_schema_bytes=size(
            [t.model_dump(mode="json", by_alias=True) for t in tools]
        ),
        mcp_tools_with_annotations=sum(t.annotations is not None for t in tools),
        mcp_tools_with_output_schema=sum(t.outputSchema is not None for t in tools),
        mcp_output_schema_example=next(
            t.outputSchema for t in tools if t.name == "bazi_birth"
        ),
        mcp_resources=len(resources),
        mcp_prompts=len(prompts),
        input_extra_policy=next(
            s.request_model.model_config.get("extra", "ignore (Pydantic default)")
            for s in CATALOG
            if s.key == "bazi_birth"
        ),
        descriptor=describe_spec(next(s for s in CATALOG if s.key == "bazi_birth")),
        rest_probe_summary={
            k: {
                "status": v["status"],
                "bytes": v.get("bytes"),
                "error_code": v["body"].get("error_code"),
                "top_keys": list(v["body"]),
            }
            for k, v in rest_probes.items()
        },
        mcp_probe_summary={
            k: {
                "is_error": v["is_error"],
                "structured_content_type": type(v["structured_content"]).__name__,
                "content_types": [c["type"] for c in v["content"]],
            }
            for k, v in mcp_probes.items()
        },
    )
    write("summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
