"""MCP protocol contracts around the shared catalog execution functions."""

import json
from typing import Any, Dict, List, Optional, cast

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from pydantic import ConfigDict, Field, ValidationError

from fatebridge.application.description import describe_input_spec, resolve_spec
from fatebridge.application.discovery import discover_specs
from fatebridge.application.scenarios import discover_scenarios
from fatebridge.core.execution_context import (
    ExecutionOptions,
    correlate_error,
    safe_correlation,
)
from fatebridge.utils.errors import validation_error_result


def register_discovery_resources(
    app: Any, catalog: list[Any], exposed: list[Any]
) -> None:
    """Expose summaries and on-demand contracts without extra business tools."""
    allowed = {spec.tool_name for spec in exposed}

    def lookup(**filters: Any) -> str:
        manifest = discover_specs(
            catalog, surface="mcp", allowed_names=allowed, **filters
        )
        return json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))

    @app.resource("fatebridge://catalog/summary", mime_type="application/json")
    def catalog_summary() -> str:
        """Compact summaries for this host's exposed tool set."""
        return lookup(detail="summary")

    @app.resource("fatebridge://families/{family}", mime_type="application/json")
    def family_summary(family: str) -> str:
        """Compact tool discovery inside one or several known families."""
        return lookup(family=family, detail="summary")

    @app.resource("fatebridge://tools/{tool}", mime_type="application/json")
    def tool_contract(tool: str) -> str:
        """Full shared contract for one exposed tool; hidden tools stay hidden."""
        spec = resolve_spec(catalog, tool)
        if spec is None or spec.tool_name not in allowed:
            raise ValueError("工具未在当前 MCP 配置中公开")
        return lookup(tool=spec.tool_name, detail="full")

    @app.resource("fatebridge://tools/{tool}/input", mime_type="application/json")
    def tool_input_contract(tool: str) -> str:
        """Small call contract and output roots; full schemas remain on demand."""
        spec = resolve_spec(catalog, tool)
        if spec is None or spec.tool_name not in allowed:
            raise ValueError("工具未在当前 MCP 配置中公开")
        return json.dumps(
            {
                "detail": "input",
                "matched_count": 1,
                "tools": [describe_input_spec(spec)],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @app.resource("fatebridge://scenarios", mime_type="application/json")
    def scenarios_summary() -> str:
        """Scenario summaries limited to this host's registered tools."""
        return json.dumps(
            discover_scenarios(
                catalog, surface="mcp", detail="summary", allowed_names=allowed
            ),
            ensure_ascii=False,
        )

    @app.resource("fatebridge://scenarios/{scenario}", mime_type="application/json")
    def scenario_manifest(scenario: str) -> str:
        """Evidence roles and callable tools, including explicit missing capability markers."""
        return json.dumps(
            discover_scenarios(
                catalog, scenario=scenario, surface="mcp", allowed_names=allowed
            ),
            ensure_ascii=False,
        )

    from fatebridge.application.result_delivery import RESULT_STORE

    allowed_receipts = {spec.run_metadata_name for spec in exposed}

    def check_result_scope(result_id: str) -> None:
        payload = RESULT_STORE.get(result_id)
        if (payload.get("run_metadata") or {}).get("tool_name") not in allowed_receipts:
            raise ValueError("结果所属工具未在当前 MCP 配置中公开")

    @app.resource("fatebridge://results/{result_id}", mime_type="application/json")
    def result_manifest(result_id: str) -> str:
        """Fields and paging references for one retained, unchanged result."""
        check_result_scope(result_id)
        return json.dumps(RESULT_STORE.manifest(result_id), ensure_ascii=False)

    @app.resource(
        "fatebridge://results/{result_id}/pages/{offset}", mime_type="application/json"
    )
    def result_page(result_id: str, offset: int) -> str:
        """A complete JSON page envelope; join text fragments only when needed."""
        check_result_scope(result_id)
        return json.dumps(RESULT_STORE.page(result_id, offset), ensure_ascii=False)

    @app.resource(
        "fatebridge://results/{result_id}/fields/{path}/{offset}",
        mime_type="application/json",
    )
    def result_field_page(result_id: str, path: str, offset: int) -> str:
        """Read a dotted field, including array numeric indices, from the same run."""
        check_result_scope(result_id)
        return json.dumps(
            RESULT_STORE.page(result_id, offset, path), ensure_ascii=False
        )


def protocol_result(
    payload: Dict[str, Any], *, failed: bool, text: Optional[str] = None
) -> ToolResult:
    return ToolResult(
        content=text or json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        structured_content=payload,
        is_error=failed,
    )


class OutputFlags(ExecutionOptions):
    model_config = ConfigDict(extra="forbid")
    compact: bool = True
    include_snapshot_text: bool = True
    fields: Optional[List[str]] = None
    strict_fields: bool = False
    response_char_limit: int = Field(default=8192, ge=0, le=65536)


class InputValidationMiddleware(Middleware):
    """Catch user input before FastMCP's signature validator can echo it."""

    def __init__(self, specs: list[Any]) -> None:
        self.specs = {spec.tool_name: spec for spec in specs}

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: Any
    ) -> ToolResult:
        spec = self.specs.get(context.message.name)
        if spec is None:
            return cast(ToolResult, await call_next(context))
        arguments = context.message.arguments or {}
        flags = {k: v for k, v in arguments.items() if k in OutputFlags.model_fields}
        inputs = {
            k: v for k, v in arguments.items() if k not in OutputFlags.model_fields
        }
        unknown = set(inputs) - set(spec.request_model.model_fields)
        if unknown:
            return protocol_result(
                {
                    "error": "请求参数无效",
                    "error_code": "validation_error",
                    "status_code": 422,
                    "retryable": False,
                    "issues": [
                        {"path": key, "code": "extra_forbidden"}
                        for key in sorted(unknown)
                    ],
                    **safe_correlation(arguments).model_dump(exclude_none=True),
                },
                failed=True,
            )
        try:
            OutputFlags.model_validate(flags)
            spec.request_model.model_validate(inputs)
            return cast(ToolResult, await call_next(context))
        except ValidationError as exc:
            return protocol_result(
                correlate_error(
                    validation_error_result(exc), safe_correlation(arguments)
                ),
                failed=True,
            )
