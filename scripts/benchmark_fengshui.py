#!/usr/bin/env python3
"""Reproducible local fengshui benchmark; no model/network latency claims.

Run: .venv/bin/python scripts/benchmark_fengshui.py --mcp --json --output PATH
First-case calls share caches and are not fresh-process cold starts. Timings are
not CI thresholds. Payload sizes are exact UTF-8 JSON bytes, never token counts.
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import hashlib
import json
import platform
import pstats
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fatebridge.application.description import describe_input_spec, describe_spec
from fatebridge.application.examples import suggested_fields
from fatebridge.application.execution import execute_tool
from fatebridge.core.execution_context import ExecutionOptions
from fatebridge.services.fengshui import assess
from fatebridge.services.tool_catalog import CATALOG

SPEC = next(s for s in CATALOG if s.key == "fengshui_assess")
OPTIONS = ExecutionOptions(as_of="2026-10-14T12:00:00+08:00")
DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def build_cases(sizes: list[int]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for size in sizes:
        forms = [
            {
                "object_id": f"object-{i}",
                "purpose": "desk",
                "entrance_position": "back_right",
                "entrance_visible": False,
                "entrance_direct_line": False,
                "solid_backing": True,
                "observation_basis": "user_confirmed",
                "evidence": "Synthetic benchmark: user-confirmed independent relations",
            }
            for i in range(size)
        ]
        cases[f"forms-{size}"] = {
            "methods": [],
            "analyze_layout": True,
            "form_observations": forms,
        }
        base = {
            "analyze_layout": True,
            "effective_year": 2026,
            "house": {
                "object_id": "home",
                "facing_degrees": 255,
                "north_reference": "magnetic",
            },
            "occupants": [
                {
                    "subject_id": "a",
                    "effective_birth_year": 1990,
                    "gender_convention": "male",
                },
                {
                    "subject_id": "b",
                    "effective_birth_year": 1990,
                    "gender_convention": "female",
                },
            ],
            "placements": [
                {
                    "object_id": f"object-{i}",
                    "purpose": "desk",
                    "location_direction": DIRECTIONS[i % 8],
                    "facing_direction": DIRECTIONS[(i + 2) % 8],
                    "facing_role": "desk_facing",
                    "subject_id": "a",
                }
                for i in range(size)
            ],
            "features": [
                {
                    "object_id": f"feature-{i}",
                    "direction": DIRECTIONS[i % 8],
                    "classification": "sand" if i % 2 else "water",
                    "classification_basis": "user_confirmed",
                    "evidence": "Synthetic benchmark: confirmed classification",
                }
                for i in range(size)
            ],
        }
        cases[f"bazhai-{size}"] = {**base, "methods": ["bazhai"]}
        cases[f"foundation-{size}"] = {
            **base,
            "methods": ["bazhai", "jinsuo", "annual_stars"],
        }
        cases[f"all-methods-{size}"] = {
            **base,
            "methods": ["bazhai", "jinsuo", "annual_stars", "xuankong_natal"],
            "xuankong": {
                "period": {
                    "basis": "construction_completion",
                    "effective_event_year": 2004,
                    "evidence": "Synthetic benchmark: confirmed completion",
                }
            },
        }
    cases["partial-facing-only"] = {
        "methods": ["bazhai", "annual_stars"],
        "effective_year": 2026,
        "analyze_layout": True,
        "occupants": [
            {"subject_id": "a", "birth_date": "2000-12-10", "gender_convention": "male"}
        ],
        "placements": [
            {
                "object_id": "desk",
                "purpose": "desk",
                "facing_direction": "W",
                "facing_role": "desk_facing",
                "subject_id": "a",
            }
        ],
        "element_adjustments": [
            {
                "request_id": "r",
                "object_id": "desk",
                "target_method": "bazhai",
                "subject_id": "a",
                "aspect": "facing",
                "goal": "drain",
                "evidence": "Synthetic benchmark: explicit target",
            }
        ],
    }
    crowd = json.loads(json.dumps(cases[f"foundation-{sizes[0]}"]))
    crowd["occupants"] = [
        {
            "subject_id": f"person-{i}",
            "effective_birth_year": 1970 + i,
            "gender_convention": "male" if i % 2 else "female",
        }
        for i in range(50)
    ]
    for placement in crowd["placements"]:
        placement.pop("subject_id")
    cases["50-occupants"] = crowd
    return cases


def checked(value: Any) -> Any:
    if isinstance(value, dict) and "error" in value:
        raise RuntimeError(f"Benchmark must not accept error payload: {value}")
    return value


def distribution(samples: list[float]) -> dict[str, Any]:
    ordered = sorted(samples)
    # Linear interpolation makes the quantile definition explicit/reproducible.
    index = (len(ordered) - 1) * 0.95
    low = int(index)
    p95 = ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (
        index - low
    )
    return {
        "samples_ms": [round(x, 4) for x in samples],
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(p95, 4),
        "min_ms": round(min(samples), 4),
        "max_ms": round(max(samples), 4),
    }


def measure(fn: Callable[[], Any], repeats: int, warmups: int) -> dict[str, Any]:
    start = time.perf_counter()
    checked(fn())
    first = (time.perf_counter() - start) * 1000
    for _ in range(warmups):
        checked(fn())
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        value = fn()
        samples.append((time.perf_counter() - start) * 1000)
        checked(value)
    return {"first_case_call_ms": round(first, 4), **distribution(samples)}


def payload_size(value: Any) -> dict[str, int]:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return {"utf8_json_bytes": len(text.encode("utf-8")), "json_characters": len(text)}


def profile(fn: Callable[[], Any]) -> list[dict[str, Any]]:
    profiler = cProfile.Profile()
    profiler.runcall(fn)
    return profile_records(profiler)


def profile_records(profiler: cProfile.Profile) -> list[dict[str, Any]]:
    stats: Any = pstats.Stats(profiler)
    return [
        {
            "function": f"{Path(key[0]).name}:{key[1]}:{key[2]}",
            "calls": data[1],
            "self_ms": round(data[2] * 1000, 4),
            "cumulative_ms": round(data[3] * 1000, 4),
        }
        for key, data in sorted(
            stats.stats.items(), key=lambda pair: pair[1][3], reverse=True
        )[:20]
    ]


async def mcp_bench(
    cases: dict[str, dict[str, Any]], repeats: int, warmups: int
) -> dict[str, Any]:
    from fastmcp import Client

    from fatebridge.mcp_server import create_mcp_app

    output: dict[str, Any] = {
        "scope": "in_process_FastMCP_no_network_no_model",
        "cases": {},
    }
    for family in (None, "fengshui"):
        start = time.perf_counter()
        app = create_mcp_app(families=family)
        creation_ms = (time.perf_counter() - start) * 1000
        async with Client(app) as client:
            start = time.perf_counter()
            tools = await client.list_tools()
            discovery_ms = (time.perf_counter() - start) * 1000
            output["discovery_" + (family or "all")] = {
                "app_creation_ms": round(creation_ms, 4),
                "list_tools_single_call_ms": round(discovery_ms, 4),
                "tool_count": len(tools),
                **payload_size([tool.model_dump(mode="json") for tool in tools]),
                "coverage_note": "Different exposure scopes; family reduction is not a like-for-like speedup",
                "schemas": {
                    tool.name: {
                        "input": payload_size(tool.inputSchema),
                        "output": payload_size(tool.outputSchema),
                        "input_ref_count": json.dumps(tool.inputSchema).count('"$ref"'),
                        "output_ref_count": json.dumps(tool.outputSchema).count(
                            '"$ref"'
                        ),
                    }
                    for tool in tools
                },
            }
            if family != "fengshui":
                continue
            for name, request in cases.items():
                output["cases"][name] = {}
                for view in ("full", "first_view"):
                    args = {
                        **request,
                        "as_of": OPTIONS.as_of,
                        "include_snapshot_text": view == "full",
                    }
                    if view == "first_view":
                        args.update(fields=suggested_fields(SPEC), strict_fields=True)
                    samples = []
                    for _ in range(warmups + repeats):
                        start = time.perf_counter()
                        result = await client.call_tool(
                            "fengshui_assess", args, raise_on_error=False
                        )
                        elapsed = (time.perf_counter() - start) * 1000
                        if result.is_error:
                            raise RuntimeError(str(result))
                        samples.append(elapsed)
                    output["cases"][name][view] = {
                        **distribution(samples[warmups:]),
                        "structured_content": payload_size(result.structured_content),
                        "text_content_utf8_bytes": sum(
                            len(getattr(c, "text", "").encode("utf-8"))
                            for c in result.content
                        ),
                        "duplication_note": "MCP carries text plus structuredContent; host tokenization may deduplicate",
                    }
            first_name = next(iter(cases))
            profiler = cProfile.Profile()
            profiler.enable()
            await client.call_tool("fengshui_assess", cases[first_name])
            profiler.disable()
            output["profile_first_case"] = {
                "name": first_name,
                "warning": "Profiled timing is instrumented; use unprofiled samples for latency",
                "functions": profile_records(profiler),
            }
    return output


async def compare_mcp_inputs(ref: str) -> dict[str, Any]:
    """Isolate registrar expansion using identical current domain schemas."""
    from fastmcp import Client, FastMCP

    from fatebridge.application.discovery import select_specs
    from fatebridge.mcp_server import _render_protocol_error, _render_protocol_response
    from fatebridge.transports.mcp import register_mcp

    source = subprocess.check_output(
        ["git", "show", f"{ref}:src/fatebridge/transports/mcp.py"], cwd=ROOT, text=True
    )
    namespace: dict[str, Any] = {
        "__name__": "fatebridge.transports._benchmark_baseline",
        "__package__": "fatebridge.transports",
    }
    exec(compile(source, "baseline/mcp.py", "exec"), namespace)
    result: dict[str, Any] = {
        "baseline_ref": ref,
        "scope": "Paired public MCP registration with identical current domain schemas and descriptions",
        "families": {},
    }
    for family in (None, "fengshui"):
        specs = select_specs(CATALOG, family=family, surface="mcp")
        views: dict[str, Any] = {}
        for name, registrar in (
            ("baseline", namespace["register_mcp"]),
            ("current", register_mcp),
        ):
            server = FastMCP(name="fatebridge", dereference_schemas=False)
            registrar(
                server,
                specs,
                render_response=_render_protocol_response,
                render_error=_render_protocol_error,
            )
            async with Client(server) as client:
                definitions = await client.list_tools()
                views[name] = {
                    **payload_size(
                        [tool.model_dump(mode="json") for tool in definitions]
                    ),
                    "tool_count": len(definitions),
                    "schemas": {
                        tool.name: {
                            "input_bytes": payload_size(tool.inputSchema)[
                                "utf8_json_bytes"
                            ],
                            "output_sha256": hashlib.sha256(
                                json.dumps(tool.outputSchema, sort_keys=True).encode()
                            ).hexdigest(),
                            "input_ref_count": json.dumps(tool.inputSchema).count(
                                '"$ref"'
                            ),
                        }
                        for tool in definitions
                    },
                }
        old, new = views["baseline"], views["current"]
        assert old["schemas"].keys() == new["schemas"].keys()
        assert all(
            old["schemas"][name]["output_sha256"] == value["output_sha256"]
            for name, value in new["schemas"].items()
        )
        views["comparison"] = {
            "output_schemas_exactly_equal": True,
            "tools_json_bytes_delta": new["utf8_json_bytes"] - old["utf8_json_bytes"],
            "input_bytes_delta": sum(
                value["input_bytes"] - old["schemas"][name]["input_bytes"]
                for name, value in new["schemas"].items()
            ),
        }
        result["families"][family or "all"] = views
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--sizes", type=int, nargs="+", default=[1, 8, 32, 128, 200])
    parser.add_argument("--mcp", action="store_true")
    parser.add_argument(
        "--mcp-max-size",
        type=int,
        default=32,
        help="Protocol matrix includes cases at or below this size; local matrix always retains all sizes",
    )
    parser.add_argument(
        "--compare-layout-ref",
        help="Trusted local git ref for isolated layout algorithm comparison",
    )
    parser.add_argument(
        "--compare-mcp-input-ref",
        help="Trusted local registrar git ref for paired input expansion/size comparison",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (
        args.repeats < 1
        or args.warmups < 0
        or any(n < 1 or n > 200 for n in args.sizes)
    ):
        parser.error("repeats >= 1, warmups >= 0 and sizes in 1..200 required")
    from fatebridge.mcp_server import _tool_response_payload
    from fatebridge.utils.formatting import format_json_response

    cases = build_cases(args.sizes)
    report: dict[str, Any] = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "source_hashes": {
                str(path.relative_to(ROOT)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in sorted((ROOT / "src/fatebridge").rglob("*.py"))
            },
        },
        "methodology": {
            "repeats": args.repeats,
            "warmups": args.warmups,
            "frozen_as_of": OPTIONS.as_of,
            "first_view_fields": suggested_fields(SPEC),
            "timing_boundary": "local wall clock; validation/execution/render/serialization separately sampled",
            "token_counts": "not measured: tokenizer/host representation unspecified; bytes are not tokens",
            "model_latency": "not measured",
            "network_latency": "not measured",
            "first_calls": "shared process caches, not fresh-process cold starts",
        },
        "cases": {},
    }
    for name, inputs in cases.items():
        request = SPEC.request_model.model_validate(inputs)
        raw = checked(assess(**inputs))
        executed = checked(execute_tool(SPEC, request, options=OPTIONS))
        result: dict[str, Any] = {
            "inputs": inputs,
            "status": raw["status"],
            "layout_status": raw["layout_analysis"]["status"],
            "counts": {
                "placements": len(inputs.get("placements", [])),
                "occupants": len(inputs.get("occupants", [])),
                "form_observations": len(inputs.get("form_observations", [])),
                "conflicts": len(raw["conflicts"]),
            },
            "request_validation": measure(
                lambda: SPEC.request_model.model_validate(inputs),
                args.repeats,
                args.warmups,
            ),
            "service_with_snapshot": measure(
                lambda: assess(**inputs), args.repeats, args.warmups
            ),
            "validated_execution_with_receipt": measure(
                lambda: execute_tool(SPEC, request, options=OPTIONS),
                args.repeats,
                args.warmups,
            ),
            "views": {},
        }
        for view in ("full", "first_view"):
            flags: dict[str, Any] = {
                "include_snapshot_text": view == "full",
                "tool_name": SPEC.key,
                "fields": suggested_fields(SPEC) if view == "first_view" else None,
                "strict_fields": True,
            }
            render = lambda: _tool_response_payload(executed, **flags)
            payload = render()
            if view == "first_view":
                # Entire selected business subtrees must survive exactly; smaller
                # payloads are not allowed to silently lose partial/conflict data.
                for field in suggested_fields(SPEC) or []:
                    selected, original = payload, executed
                    for part in field.split("."):
                        selected, original = selected[part], original[part]
                    assert selected == original, field
                assert payload["run_metadata"] == executed["run_metadata"]
            result["views"][view] = {
                **payload_size(payload),
                "render_projection": measure(render, args.repeats, args.warmups),
                "serialize_json": measure(
                    lambda: format_json_response(payload, compact=True),
                    args.repeats,
                    args.warmups,
                ),
            }
        report["cases"][name] = result
    largest = f"all-methods-{max(args.sizes)}"
    report["profile_largest_execution"] = profile(
        lambda: execute_tool(
            SPEC, SPEC.request_model.model_validate(cases[largest]), options=OPTIONS
        )
    )
    report["discovery"] = {}
    for name, fn in (
        ("input_contract", lambda: describe_input_spec(SPEC)),
        ("full_contract", lambda: describe_spec(SPEC)),
    ):
        report["discovery"][name] = {
            **measure(fn, args.repeats, args.warmups),
            **payload_size(fn()),
        }
    if args.mcp:
        protocol_cases = {
            name: inputs
            for name, inputs in cases.items()
            if max(
                len(inputs.get("placements", [])),
                len(inputs.get("form_observations", [])),
            )
            <= args.mcp_max_size
        }
        report["mcp"] = asyncio.run(
            mcp_bench(protocol_cases, args.repeats, args.warmups)
        )
        report["methodology"]["mcp_max_object_size"] = args.mcp_max_size
    if args.compare_layout_ref:
        from fatebridge.core.fengshui.layout import analyze_layout
        from fatebridge.core.fengshui.models import AssessRequest

        source = subprocess.check_output(
            [
                "git",
                "show",
                f"{args.compare_layout_ref}:src/fatebridge/core/fengshui/layout.py",
            ],
            cwd=ROOT,
            text=True,
        )
        namespace: dict[str, Any] = {
            "__name__": "fatebridge.core.fengshui._benchmark_baseline",
            "__package__": "fatebridge.core.fengshui",
        }
        exec(compile(source, "baseline/layout.py", "exec"), namespace)
        old_layout = namespace["analyze_layout"]
        comparisons: dict[str, Any] = {}
        for size in args.sizes:
            inputs = cases[f"all-methods-{size}"]
            layout_request = AssessRequest.model_validate(inputs)
            layers = assess(**inputs)["layers"]
            baseline = old_layout(layout_request, layers)
            current = analyze_layout(layout_request, layers)
            assert (
                baseline == current
            ), "Isolated algorithm comparison must preserve complete results"
            comparisons[str(size)] = {
                "result_exactly_equal": True,
                "baseline": measure(
                    lambda: old_layout(layout_request, layers),
                    args.repeats,
                    args.warmups,
                ),
                "current": measure(
                    lambda: analyze_layout(layout_request, layers),
                    args.repeats,
                    args.warmups,
                ),
            }
        report["isolated_layout_comparison"] = {
            "baseline_ref": args.compare_layout_ref,
            "baseline_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "scope": "Same precomputed layers and all selected methods; domain readiness fixes excluded",
            "cases": comparisons,
        }
    if args.compare_mcp_input_ref:
        report["paired_mcp_input_comparison"] = asyncio.run(
            compare_mcp_inputs(args.compare_mcp_input_ref)
        )
    report["environment"]["source_files_changed_during_run"] = [
        name
        for name, digest in report["environment"]["source_hashes"].items()
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
    ]
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    if args.json:
        print(serialized, end="")
    else:
        print("case | execution median ms | full bytes | first-view bytes")
        for name, result in report["cases"].items():
            print(
                f"{name} | {result['validated_execution_with_receipt']['median_ms']:.3f} | "
                f"{result['views']['full']['utf8_json_bytes']} | {result['views']['first_view']['utf8_json_bytes']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
