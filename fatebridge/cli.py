"""
FateBridge command-line interface.

A third transport surface — alongside REST and MCP — built entirely from the
central tool catalog. Every catalog tool becomes a subcommand; its request-model
fields become flags. Adding a tool to the catalog automatically gives it a CLI
command. Designed for agentic/scripted use: results print as JSON to stdout.

Examples:
    fatebridge list
    fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \\
        --birth-hour 10 --gender male --dayun-pillar 壬戌
    fatebridge knowledge_read --domain bazi --category wealth --key 财库
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, List, Optional, Union, get_args, get_origin

from pydantic import BaseModel

from fatebridge.core.tool_spec import ToolSpec, execute_spec, result_is_error
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.services.tool_catalog import CATALOG


def _command_name(spec: ToolSpec) -> str:
    return spec.mcp_name or spec.key


def _unwrap_optional(annotation: Any) -> Any:
    if get_origin(annotation) is Union:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if non_none:
            return non_none[0]
    return annotation


def _is_model_field(annotation: Any) -> bool:
    base = _unwrap_optional(annotation)
    return isinstance(base, type) and issubclass(base, BaseModel)


def _cli_safe(spec: ToolSpec) -> bool:
    """A spec is CLI-exposable if none of its fields are nested models."""
    return not any(_is_model_field(f.annotation) for f in spec.request_model.model_fields.values())


def _add_field_argument(parser: argparse.ArgumentParser, name: str, field: Any) -> None:
    annotation = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    required = field.is_required()
    default = None if required else field.get_default(call_default_factory=True)
    flag = "--" + name.replace("_", "-")
    help_text = field.description or ""

    if annotation is bool:
        parser.add_argument(
            flag, dest=name, action=argparse.BooleanOptionalAction,
            default=default, help=help_text,
        )
    elif origin in (list, List):
        parser.add_argument(flag, dest=name, nargs="*", default=default, help=help_text)
    elif annotation is int:
        parser.add_argument(flag, dest=name, type=int, default=default, required=required, help=help_text)
    elif annotation is float:
        parser.add_argument(flag, dest=name, type=float, default=default, required=required, help=help_text)
    else:
        parser.add_argument(flag, dest=name, type=str, default=default, required=required, help=help_text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fatebridge",
        description="FateBridge 命理/占星离线计算 CLI（数据驱动自中央工具目录）。",
    )
    parser.add_argument(
        "--no-metadata", action="store_true", help="不附加 run_metadata"
    )
    sub = parser.add_subparsers(dest="command", metavar="<tool>")

    sub.add_parser("list", help="列出所有可用工具命令")

    for spec in CATALOG:
        if not _cli_safe(spec):
            # Register a stub so invoking it gives a helpful hint instead of
            # argparse's opaque "invalid choice".
            sp = sub.add_parser(
                _command_name(spec),
                help=f"{spec.summary}（CLI 暂不支持：含嵌套结构，见提示）",
            )
            sp.set_defaults(_spec=spec, _cli_unsupported=True, _hint=_unsupported_hint(spec))
            continue
        sp = sub.add_parser(_command_name(spec), help=spec.summary)
        for fname, field in spec.request_model.model_fields.items():
            _add_field_argument(sp, fname, field)
        sp.set_defaults(_spec=spec)
    return parser


def _unsupported_hint(spec: ToolSpec) -> str:
    """Suggest a CLI-safe flat sibling (same label) or fall back to REST/MCP."""
    sibling = next(
        (
            _command_name(s)
            for s in CATALOG
            if s is not spec
            and _cli_safe(s)
            and s.operation_label_zh == spec.operation_label_zh
        ),
        None,
    )
    if sibling:
        return f"该工具含嵌套结构，CLI 暂不支持；请改用扁平变体命令 `fatebridge {sibling}`。"
    target = spec.rest_path or (f"MCP 工具 {spec.mcp_name}" if spec.mcp_name else "REST/MCP 接口")
    return f"该工具含嵌套结构，CLI 暂不支持；请改用 {target}。"


def _print_tools() -> None:
    rows = []
    for spec in CATALOG:
        mark = "" if _cli_safe(spec) else "  (CLI 不支持: 含嵌套结构)"
        rows.append(f"  {_command_name(spec):<28} {spec.operation_label_zh}{mark}")
    print("可用工具命令：\n" + "\n".join(rows))


def run(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command or args.command == "list":
        _print_tools()
        return 0

    spec: ToolSpec = getattr(args, "_spec", None)
    if spec is None:
        parser.error(f"未知工具: {args.command}")
        return 2

    if getattr(args, "_cli_unsupported", False):
        print(getattr(args, "_hint", "该工具 CLI 暂不支持。"), file=sys.stderr)
        return 2

    # Build the request model from only the flags the user actually provided.
    field_names = set(spec.request_model.model_fields)
    provided = {
        k: v for k, v in vars(args).items()
        if k in field_names and v is not None
    }
    try:
        request = spec.request_model(**provided)
        result = execute_spec(spec, request)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1

    is_error = result_is_error(spec, result)
    if not args.no_metadata and not is_error:
        result = attach_run_metadata(result, tool_name=spec.run_metadata_name)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if is_error else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
