"""Collect fictional results once, plus strict first views, through real stdio MCP.

Run from the repository with its installed Python; results are local evidence,
not predictions or an LLM evaluation. An existing output is never overwritten.
"""

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from fatebridge.application.examples import example_input, suggested_fields
from fatebridge.services.tool_catalog import CATALOG

ROOT = Path(__file__).resolve().parents[3]
AS_OF = "2026-10-15T12:00:00+08:00"
KEYS = (
    "bazi_career",
    "two_person_compatibility",
    "timing_analysis",
    "bazi_health",
    "bazi_personality",
    "bazi_education",
    "analyze_destiny",
    "ziwei_birth",
    "astro_chart",
    "meihua_analysis",
    "fengshui_assess",
)


def save(path, value):
    with path.open("x", encoding="utf-8") as out:
        out.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def main(output):
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise SystemExit("Evidence already exists; choose a fresh --output directory.")
    specs = {spec.key: spec for spec in CATALOG}
    records = []
    with (output / "stdio-stderr.log").open("w") as log:
        transport = StdioTransport(
            command=sys.executable,
            args=["-m", "fatebridge.mcp_server"],
            cwd=ROOT,
            env={"FATEBRIDGE_MCP_FAMILIES": "", "FATEBRIDGE_MCP_SCENARIOS": ""},
            log_file=log,
        )
        async with Client(transport, timeout=60) as client:
            for key in KEYS:
                spec = specs[key]
                inputs = example_input(spec)
                if key == "fengshui_assess":
                    inputs = json.loads(
                        (
                            Path(__file__).parent / "evidence/fengshui-input.json"
                        ).read_text()
                    )
                elif key == "meihua_analysis":
                    inputs.update(
                        analysis_day=15,
                        analysis_hour=14,
                        analysis_minute=20,
                        question="虚构：新项目先做小范围收费试运行，有哪些条件要核对？",
                    )
                elif key == "timing_analysis":
                    inputs.update(analysis_day=15)
                inputs.update(as_of=AS_OF)
                # Programmatic client saves the complete response without
                # printing it into chat. This is not a chat pagination bypass.
                params = {
                    **inputs,
                    "fields": None,
                    "include_snapshot_text": False,
                    "response_char_limit": 0,
                }
                result = await client.call_tool(
                    spec.tool_name, params, raise_on_error=False
                )
                if result.is_error:
                    raise RuntimeError((key, result.structured_content))
                payload = result.structured_content
                if "result_delivery" in payload:
                    raise RuntimeError("Programmatic full result was not retained")
                receipt = payload["run_metadata"]
                digest = save(
                    output / f"{key}.json", {"input": params, "result": payload}
                )
                record = {
                    "tool": spec.tool_name,
                    "file": f"{key}.json",
                    "file_sha256": digest,
                    "run_id": receipt["run_id"],
                    "trace_id": receipt["trace_id"],
                    "business_output_sha256": receipt["business_output_sha256"],
                }
                if key in {"astro_chart", "ziwei_birth", "meihua_analysis"}:
                    view = await client.call_tool(
                        spec.tool_name,
                        {
                            **inputs,
                            "fields": suggested_fields(spec),
                            "strict_fields": True,
                            "include_snapshot_text": False,
                        },
                        raise_on_error=False,
                    )
                    if view.is_error or "result_delivery" in view.structured_content:
                        raise RuntimeError((key, "first view", view.structured_content))
                    record["first_view_file_sha256"] = save(
                        output / f"{key}-first-view.json", view.structured_content
                    )
                    record["first_view_chars"] = len(
                        json.dumps(
                            view.structured_content,
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                    )
                    assert (
                        receipt["business_output_sha256"]
                        == view.structured_content["run_metadata"][
                            "business_output_sha256"
                        ]
                    )
                records.append(record)
                print(key, "saved", flush=True)
    save(
        output / "manifest.json",
        {
            "scope": "Fictional inputs; real independent stdio MCP; no LLM involved",
            "as_of": AS_OF,
            "first_views": "Separate contract calls; full retained results drive both dialogue variants",
            "records": records,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args().output.resolve()))
