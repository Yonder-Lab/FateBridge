"""Progressive catalog discovery shared by REST, CLI and MCP resources."""

from typing import Any, Dict, List, Literal, Optional, Set

from pydantic import BaseModel, ConfigDict, ValidationError

from fatebridge.core.tool_spec import ToolSpec, describe_spec, spec_is_cli_safe
from fatebridge.utils.errors import ParameterError, validation_error_result


class DiscoveryQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: Optional[str] = None
    scenario: Optional[str] = None
    q: Optional[str] = None
    tool: Optional[str] = None
    surface: Optional[Literal["rest", "mcp", "cli"]] = None
    detail: Literal["summary", "full"] = "full"


def select_specs(
    specs: List[ToolSpec],
    *,
    family: Optional[str] = None,
    scenario: Optional[str] = None,
    q: Optional[str] = None,
    tool: Optional[str] = None,
    surface: Optional[str] = None,
    allowed_names: Optional[Set[str]] = None,
) -> List[ToolSpec]:
    """Filter declarations before materializing any expensive schemas."""
    selected = specs
    if scenario is not None:
        from fatebridge.core.scenarios import scenario_keys

        keys = scenario_keys(specs, scenario)
        selected = [spec for spec in selected if spec.key in keys]
    if family is not None:
        families = [part.strip() for part in family.split(",")]
        known = {spec.family for spec in specs}
        if any(not name or name not in known for name in families):
            raise ParameterError(
                "工具分类无效",
                [
                    {
                        "path": "family",
                        "code": "unknown_family",
                        "constraints": {"allowed": sorted(known)},
                    }
                ],
            )
        selected = [spec for spec in selected if spec.family in families]
    if tool is not None:
        if not any(spec.tool_name == tool for spec in specs):
            raise ParameterError(
                "工具名称无效", [{"path": "tool", "code": "unknown_tool"}]
            )
        selected = [spec for spec in selected if spec.tool_name == tool]
    if surface:
        available = {
            "rest": lambda spec: bool(spec.rest_path),
            "mcp": lambda spec: bool(spec.mcp_name),
            "cli": spec_is_cli_safe,
        }
        if surface not in available:
            raise ParameterError(
                "工具接口无效", [{"path": "surface", "code": "invalid_surface"}]
            )
        selected = [spec for spec in selected if available[surface](spec)]
    if allowed_names is not None:
        selected = [spec for spec in selected if spec.tool_name in allowed_names]
    if q:
        needle = q.strip().casefold()
        selected = [
            spec
            for spec in selected
            if needle
            in " ".join(
                (
                    spec.tool_name,
                    spec.summary,
                    spec.operation_label_zh,
                    spec.family,
                )
            ).casefold()
        ]
    return selected


def summarize_spec(spec: ToolSpec) -> Dict[str, Any]:
    return {
        "tool": spec.tool_name,
        "summary": spec.summary,
        "operation_label_zh": spec.operation_label_zh,
        "family": spec.family,
        "surfaces": {
            "cli": spec_is_cli_safe(spec),
            "rest_path": spec.rest_path,
            "mcp_name": spec.mcp_name,
        },
        "cli_request_file": spec.cli_request_file,
        "annotations": spec.execution_hints.as_annotations(),
        "reproducibility": spec.reproducibility.as_manifest(),
    }


def discover_specs(
    specs: List[ToolSpec],
    *,
    family: Optional[str] = None,
    scenario: Optional[str] = None,
    q: Optional[str] = None,
    tool: Optional[str] = None,
    surface: Optional[str] = None,
    detail: str = "full",
    allowed_names: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    try:
        query = DiscoveryQuery.model_validate(
            dict(
                family=family,
                scenario=scenario,
                q=q,
                tool=tool,
                surface=surface,
                detail=detail,
            )
        )
    except ValidationError as exc:
        failure = validation_error_result(exc)
        raise ParameterError(failure["error"], failure["issues"]) from None
    selected = select_specs(
        specs, **query.model_dump(exclude={"detail"}), allowed_names=allowed_names
    )
    describe = summarize_spec if query.detail == "summary" else describe_spec
    return {
        # Counts retain their original global-catalog meaning under filtering.
        "counts": {
            "rest": sum(bool(spec.rest_path) for spec in specs),
            "mcp": sum(bool(spec.mcp_name) for spec in specs),
            "total": len(specs),
        },
        "matched_count": len(selected),
        "detail": query.detail,
        "tools": [describe(spec) for spec in selected],
    }
