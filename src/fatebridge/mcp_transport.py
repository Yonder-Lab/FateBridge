"""MCP protocol contracts around the shared catalog execution functions."""

import json
from typing import Any, Callable, Dict, List, Optional, cast

from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools import ToolResult
from mcp.types import CallToolResult
from pydantic import BaseModel, ConfigDict, ValidationError

from fatebridge.core.discovery import discover_specs
from fatebridge.core.execution_context import (
    ExecutionOptions,
    correlate_error,
    safe_correlation,
)
from fatebridge.core.scenarios import discover_scenarios
from fatebridge.utils.errors import validation_error_result


def _serializable_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Keep standard refs when FastMCP's inliner creates a Python object cycle.

    FastMCP 3.0 may inline a recursive output into a cyclic dict instead of
    retaining its $defs. Preserve input and nonrecursive output inlining for
    existing hosts; a recursive schema must retain refs to be valid wire JSON.
    """
    from fastmcp.utilities.json_schema import dereference_refs

    expanded = dereference_refs(schema)
    try:
        json.dumps(expanded)
    except (ValueError, RecursionError):
        return schema
    return expanded


class SerializableSchemaMiddleware(Middleware):
    """Publish serializable schemas on both the minimum and current FastMCP."""

    async def on_list_tools(self, context: Any, call_next: Any) -> Any:
        tools = await call_next(context)
        output = []
        for tool in tools:
            updates = {"parameters": _serializable_schema(tool.parameters)}
            if tool.output_schema is not None:
                updates["output_schema"] = _serializable_schema(tool.output_schema)
            output.append(tool.model_copy(update=updates))
        return output

    async def on_list_resource_templates(self, context: Any, call_next: Any) -> Any:
        templates = await call_next(context)
        return [
            template.model_copy(
                update={"parameters": _serializable_schema(template.parameters)}
            )
            for template in templates
        ]


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
        if tool not in allowed:
            raise ValueError("工具未在当前 MCP 配置中公开")
        return lookup(tool=tool, detail="full")

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


class ProtocolResult(ToolResult):
    """Use MCP's native error flag also on the supported FastMCP 3.0 floor.

    Earlier FastMCP releases lack ToolResult(is_error=...). Returning the native
    MCP result avoids a dependency upgrade solely for that convenience flag.
    """

    failed: bool = False

    def __init__(
        self, *, content: Any, structured_content: Dict[str, Any], failed: bool
    ) -> None:
        super().__init__(content=content, structured_content=structured_content)
        self.failed = failed

    def to_mcp_result(self) -> Any:
        # SDK 1.x names constructor fields in camelCase; SDK 2.x uses snake_case
        # attributes with wire aliases. Validating the protocol dictionary works
        # with both versions without depending on either constructor signature.
        return CallToolResult.model_validate(
            {
                "content": self.content,
                "structuredContent": self.structured_content,
                "isError": self.failed,
            }
        )


def protocol_result(
    payload: Dict[str, Any], *, failed: bool, text: Optional[str] = None
) -> ProtocolResult:
    return ProtocolResult(
        content=text or json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        structured_content=payload,
        failed=failed,
    )


def native_tool_function(legacy_fn: Callable[..., str]) -> Callable[..., Any]:
    def invoke(**kwargs: Any) -> ToolResult:
        rendered = legacy_fn(**kwargs)
        payload = json.loads(rendered)
        # The legacy renderer runs after the shared error classifier; an error
        # envelope is always a protocol failure, never ordinary text success.
        return protocol_result(payload, failed="error_code" in payload, text=rendered)

    invoke.__name__ = legacy_fn.__name__
    invoke.__doc__ = legacy_fn.__doc__
    invoke.__signature__ = legacy_fn.__signature__  # type: ignore[attr-defined]
    invoke.__annotations__ = {**legacy_fn.__annotations__, "return": ToolResult}
    invoke.__fb_legacy_fn__ = legacy_fn  # type: ignore[attr-defined]
    return invoke


class OutputFlags(ExecutionOptions):
    model_config = ConfigDict(extra="forbid")
    compact: bool = True
    include_snapshot_text: bool = True
    fields: Optional[List[str]] = None
    strict_fields: bool = False


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
