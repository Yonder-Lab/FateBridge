"""Local contract baseline and failure probes; only synthetic inputs are used."""

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
BIRTH = dict(
    birth_year=1990,
    birth_month=5,
    birth_day=15,
    birth_hour=10,
    gender="男",
    birth_place="北京",
    birth_timezone="Asia/Shanghai",
    use_true_solar_time=False,
    analysis_year=2026,
    analysis_month=10,
    analysis_day=12,
)


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


async def main():
    # Disable optional auth only in this probe process; never read/output keys.
    api.API_KEY_AUTHENTICATOR = api.ApiKeyAuthenticator(
        header_name="X-API-Key", api_keys={}
    )
    rest = TestClient(api.app)
    schema = api.app.openapi()
    write("openapi.json", schema)
    cases = [
        ("missing_required", "bazi_birth", "/api/cn/bazi/birth", {}),
        (
            "range_error",
            "bazi_birth",
            "/api/cn/bazi/birth",
            {**BIRTH, "birth_month": 13},
        ),
        (
            "invalid_date",
            "bazi_birth",
            "/api/cn/bazi/birth",
            {**BIRTH, "birth_month": 2, "birth_day": 30},
        ),
        (
            "unknown_input",
            "bazi_birth",
            "/api/cn/bazi/birth",
            {**BIRTH, "birth_mintue": 59},
        ),
        (
            "domain_error",
            "bazi_birth",
            "/api/cn/bazi/birth",
            {**BIRTH, "birth_place": "未提供", "use_true_solar_time": True},
        ),
        (
            "unknown_topic",
            "astro_election",
            "/api/astro/event/election",
            dict(
                candidate_year=2026,
                candidate_month=10,
                candidate_day=12,
                candidate_hour=10,
                longitude=116.4,
                latitude=39.9,
                topic_id="contrcat",
            ),
        ),
        (
            "unknown_category",
            "astro_horary",
            "/api/astro/event/horary",
            dict(
                question_year=2026,
                question_month=10,
                question_day=12,
                question_hour=10,
                longitude=116.4,
                latitude=39.9,
                category="carreer",
            ),
        ),
    ]
    probes = {}
    async with Client(mcp.app) as protocol:
        tools = await protocol.list_tools()
        write(
            "mcp-tools.json",
            [tool.model_dump(mode="json", by_alias=True) for tool in tools],
        )
        for label, name, path, inputs in cases:
            http = rest.post(path, json=inputs)
            result = await protocol.call_tool(name, inputs, raise_on_error=False)
            args = [sys.executable, "-m", "fatebridge.cli", name]
            for key, value in inputs.items():
                args += [
                    "--" + key.replace("_", "-"),
                    str(value).lower() if isinstance(value, bool) else str(value),
                ]
            command = subprocess.run(args, capture_output=True, text=True, timeout=30)
            assert (
                http.status_code in (400, 422)
                and result.is_error
                and command.returncode != 0
            )
            assert (
                http.json()["error_code"]
                == result.structured_content["error_code"]
                == "validation_error"
            )
            assert json.loads(result.content[0].text) == result.structured_content
            probes[label] = dict(
                rest=dict(status=http.status_code, body=http.json()),
                mcp=dict(
                    is_error=result.is_error,
                    structured_content=result.structured_content,
                ),
                cli=dict(exit_code=command.returncode, body=json.loads(command.stdout)),
            )
        success = await protocol.call_tool(
            "bazi_birth", {**BIRTH, "fields": ["bazi_birth.day_master"]}
        )
        assert (
            not success.is_error
            and success.structured_content["bazi_birth"]["day_master"]
        )
    write("failure-probes.json", probes)
    write(
        "summary.json",
        dict(
            date="2026-10-12",
            source_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            worktree_dirty=bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain"], text=True
                ).strip()
            ),
            environment={
                "python": platform.python_version(),
                **{
                    name: version(name)
                    for name in ("fastapi", "fastmcp", "pydantic", "kerykeion")
                },
            },
            catalog_count=len(CATALOG),
            output_contract_count=sum(
                spec.output_model is not None for spec in CATALOG
            ),
            rest_count=sum(bool(spec.rest_path) for spec in CATALOG),
            rest_success_schema_count=sum(
                bool(
                    schema["paths"][spec.rest_path]["post"]["responses"]["200"][
                        "content"
                    ]["application/json"]["schema"]
                )
                for spec in CATALOG
                if spec.rest_path
            ),
            mcp_count=len(tools),
            mcp_output_schema_count=sum(bool(tool.outputSchema) for tool in tools),
            cli_count=sum(spec_is_cli_safe(spec) for spec in CATALOG),
            failure_probe_count=len(probes),
            boundary="Local TestClient, in-memory native MCP Client, actual CLI subprocesses; no hosted deployment evaluation",
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
