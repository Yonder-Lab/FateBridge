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
from typing import Any, List, NoReturn, Optional, get_args, get_origin

from fatebridge.core.tool_spec import (
    ToolSpec,
    describe_spec,
    execute_spec,
)
from fatebridge.core.tool_spec import field_type_name as _type_name
from fatebridge.core.tool_spec import (
    invalid_input_result,
)
from fatebridge.core.tool_spec import is_model_field as _is_model_field
from fatebridge.core.tool_spec import (
    project_fields,
    result_is_error,
)
from fatebridge.core.tool_spec import spec_is_cli_safe as _cli_safe
from fatebridge.core.tool_spec import unwrap_optional as _unwrap_optional
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.services.tool_catalog import CATALOG


class _JsonErrorParser(argparse.ArgumentParser):
    """Argparse parser whose usage errors are emitted as JSON on stdout.

    Argparse's default ``error()`` writes a usage string to *stderr* and exits 2.
    A machine consumer that reads stdout as JSON then sees an empty stdout and
    fails with ``Expecting value: line 1 column 1 (char 0)``. Routing the error
    onto stdout — the same stream a successful result uses — keeps stdout always
    valid JSON; the non-zero exit code carries the success/failure signal. The
    argparse message ("the following arguments are required: --birth-hour") is
    the most actionable feedback an agent can get, so it is preserved verbatim.

    Subparsers created via ``add_subparsers`` inherit this class automatically
    (argparse defaults ``parser_class`` to ``type(self)``), so per-tool flag
    errors are routed too.
    """

    def error(self, message: str) -> "NoReturn":  # type: ignore[override]
        print(
            json.dumps(
                {
                    "error": message,
                    "error_code": "usage_error",
                    "status_code": 400,
                    "retryable": False,
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(2)


def _emit_error(payload: dict, code: int) -> int:
    """Print an error payload as JSON on stdout and return the exit code.

    Error payloads deliberately share the success stream (stdout): a consumer
    that does ``json.loads(stdout)`` always gets valid JSON, on success and on
    failure alike. The exit code, not the stream, distinguishes the two.
    """
    print(json.dumps(payload, ensure_ascii=False))
    return code


_BOOL_TRUE_TOKENS = {"true", "1", "yes", "y", "on"}
_BOOL_FALSE_TOKENS = {"false", "0", "no", "n", "off"}


class _BooleanFlagAction(argparse.Action):
    """Boolean flag usable as a bare switch *and* with an explicit value.

    For a flag ``--use-true-solar-time`` all of these work::

        --use-true-solar-time              -> True   (bare switch)
        --use-true-solar-time true|false   -> parsed (space-separated value)
        --use-true-solar-time=false        -> parsed (= value)
        --no-use-true-solar-time           -> False  (negated switch)

    The stdlib :class:`argparse.BooleanOptionalAction` supports only the bare
    and negated switches; passing ``--flag true`` there dies with
    ``unrecognized arguments: true`` — a common stumble for users used to
    passing explicit ``true``/``false``. This action keeps both stdlib forms and
    additionally accepts the explicit value, so neither mental model surprises
    the caller.
    """

    def __init__(
        self,
        option_strings: List[str],
        dest: str,
        default: Any = None,
        required: bool = False,
        help: Optional[str] = None,
    ) -> None:
        expanded: List[str] = []
        for opt in option_strings:
            expanded.append(opt)
            if opt.startswith("--"):
                expanded.append("--no-" + opt[2:])
        super().__init__(
            option_strings=expanded,
            dest=dest,
            nargs="?",
            default=default,
            required=required,
            help=help,
            metavar="{true,false}",
        )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: Optional[str] = None,
    ) -> None:
        negated = option_string is not None and option_string.startswith("--no-")
        if negated:
            if values is not None:
                parser.error(
                    f"{option_string} 为关闭开关，不接受取值（直接用 {option_string}）"
                )
            result = False
        elif values is None:
            result = True
        else:
            token = str(values).strip().lower()
            if token in _BOOL_TRUE_TOKENS:
                result = True
            elif token in _BOOL_FALSE_TOKENS:
                result = False
            else:
                parser.error(
                    f"{option_string} 的取值无法识别为布尔值：{values!r}"
                    "（用 true/false；或省略值表示 true、用 --no- 前缀表示 false）"
                )
        setattr(namespace, self.dest, result)


def _command_name(spec: ToolSpec) -> str:
    return spec.mcp_name or spec.key


def _describe_spec(spec: ToolSpec) -> dict:
    """CLI view of a tool: the shared descriptor plus a copy-pasteable example.

    The transport-agnostic schema (surfaces, parameters, family) comes from
    :func:`describe_spec` — the same record REST serves at ``GET /api/tools`` —
    so the CLI only adds the CLI-specific ``cli_example`` / ``cli_hint``.
    """
    info = describe_spec(spec)
    if info["surfaces"]["cli"]:
        info["cli_example"] = _cli_example(spec)
    else:
        info["cli_hint"] = _unsupported_hint(spec)
    return info


def _cli_example(spec: ToolSpec) -> str:
    """A copy-pasteable example invocation showing the required flags."""
    parts = ["fatebridge", _command_name(spec)]
    for name, field in spec.request_model.model_fields.items():
        if field.is_required():
            flag = "--" + name.replace("_", "-")
            parts.append(f"{flag} <{_type_name(field.annotation)}>")
    return " ".join(parts)


def _add_field_argument(parser: argparse.ArgumentParser, name: str, field: Any) -> None:
    annotation = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    required = field.is_required()
    default = None if required else field.get_default(call_default_factory=True)
    flag = "--" + name.replace("_", "-")
    help_text = field.description or ""

    if annotation is bool:
        # argparse renders the action as "--flag, --no-flag" and does not
        # surface that it also accepts an explicit value, so spell it out here:
        # the explicit true/false form is exactly what trips users up.
        no_flag = flag.replace("--", "--no-", 1)
        bool_hint = f"开关；亦可写 {flag} true/false，关闭用 {no_flag}"
        bool_help = f"{help_text}（{bool_hint}）" if help_text else bool_hint
        parser.add_argument(
            flag,
            dest=name,
            action=_BooleanFlagAction,
            default=default,
            help=bool_help,
        )
    elif origin in (list, List):
        parser.add_argument(flag, dest=name, nargs="*", default=default, help=help_text)
    elif annotation is int:
        parser.add_argument(
            flag,
            dest=name,
            type=int,
            default=default,
            required=required,
            help=help_text,
        )
    elif annotation is float:
        parser.add_argument(
            flag,
            dest=name,
            type=float,
            default=default,
            required=required,
            help=help_text,
        )
    else:
        parser.add_argument(
            flag,
            dest=name,
            type=str,
            default=default,
            required=required,
            help=help_text,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = _JsonErrorParser(
        prog="fatebridge",
        description="FateBridge 命理/占星离线计算 CLI（数据驱动自中央工具目录）。",
    )
    parser.add_argument(
        "--no-metadata", action="store_true", help="不附加 run_metadata"
    )
    sub = parser.add_subparsers(dest="command", metavar="<tool>")

    sub.add_parser("list", help="列出所有可用工具命令")

    describe_parser = sub.add_parser(
        "describe", help="输出某工具的参数 schema、可用接口与示例（JSON）"
    )
    describe_parser.add_argument(
        "tool", nargs="?", help="工具命令名（见 `fatebridge list`）"
    )

    for spec in CATALOG:
        if not _cli_safe(spec):
            # Register a stub so invoking it gives a helpful hint instead of
            # argparse's opaque "invalid choice".
            sp = sub.add_parser(
                _command_name(spec),
                help=f"{spec.summary}（CLI 暂不支持：含嵌套结构，见提示）",
            )
            sp.set_defaults(
                _spec=spec, _cli_unsupported=True, _hint=_unsupported_hint(spec)
            )
            continue
        sp = sub.add_parser(_command_name(spec), help=spec.summary)
        for fname, field in spec.request_model.model_fields.items():
            _add_field_argument(sp, fname, field)
        _add_transport_flags(sp)
        sp.set_defaults(_spec=spec)
    return parser


def _add_transport_flags(parser: argparse.ArgumentParser) -> None:
    """Per-tool flags that control output shape rather than the calculation.

    These live on each tool subparser (not the top-level parser) so they can be
    passed naturally after the tool name, e.g. `fatebridge bazi_wealth ... --fields summary`.
    """
    parser.add_argument(
        "--fields",
        nargs="*",
        default=None,
        metavar="KEY",
        help=(
            "只输出这些字段（token 预算控制；run_metadata 始终保留）。"
            "支持顶层 key 或点号子路径，如 bazi_birth.day_master"
        ),
    )


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
    target = spec.rest_path or (
        f"MCP 工具 {spec.mcp_name}" if spec.mcp_name else "REST/MCP 接口"
    )
    return f"该工具含嵌套结构，CLI 暂不支持；请改用 {target}。"


def _print_tools() -> None:
    rows = []
    for spec in CATALOG:
        mark = "" if _cli_safe(spec) else "  (CLI 不支持: 含嵌套结构)"
        rows.append(f"  {_command_name(spec):<28} {spec.operation_label_zh}{mark}")
    print("可用工具命令：\n" + "\n".join(rows))


def _run_describe(tool_name: Optional[str]) -> int:
    if not tool_name:
        return _emit_error(
            {
                "error": "用法: fatebridge describe <tool>；运行 `fatebridge list` 查看所有工具",
                "error_code": "usage_error",
                "status_code": 400,
                "retryable": False,
            },
            2,
        )
    spec = next((s for s in CATALOG if _command_name(s) == tool_name), None)
    if spec is None:
        return _emit_error(
            {
                "error": f"未知工具: {tool_name}",
                "error_code": "unknown_tool",
                "status_code": 404,
                "retryable": False,
            },
            2,
        )
    print(json.dumps(_describe_spec(spec), ensure_ascii=False, indent=2, default=str))
    return 0


def run(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse usage errors already emitted JSON on stdout (see
        # _JsonErrorParser.error); --help printed to stdout with code 0. Surface
        # the code as a normal return so callers needn't catch SystemExit.
        return int(exc.code) if exc.code is not None else 0

    if not args.command or args.command == "list":
        _print_tools()
        return 0

    if args.command == "describe":
        return _run_describe(getattr(args, "tool", None))

    spec: Optional[ToolSpec] = getattr(args, "_spec", None)
    if spec is None:
        parser.error(f"未知工具: {args.command}")
        return 2

    if getattr(args, "_cli_unsupported", False):
        return _emit_error(
            {
                "error": getattr(args, "_hint", "该工具 CLI 暂不支持。"),
                "error_code": "cli_unsupported",
                "status_code": 400,
                "retryable": False,
            },
            2,
        )

    # Build the request model from only the flags the user actually provided.
    field_names = set(spec.request_model.model_fields)
    provided = {
        k: v for k, v in vars(args).items() if k in field_names and v is not None
    }
    try:
        request = spec.request_model(**provided)
        result = execute_spec(spec, request)
    except ValueError:
        # Mirror REST/MCP: bad input (pydantic ValidationError or a date check
        # raised during binding) renders as a clean, generic error rather than
        # dumping a raw exception string. It shares stdout with success output so
        # a json.loads(stdout) consumer always parses; exit 1 signals failure.
        return _emit_error(invalid_input_result(spec), 1)
    except Exception as exc:  # noqa: BLE001 - unexpected internal failure
        return _emit_error(
            {
                "error": str(exc),
                "error_code": "internal_error",
                "status_code": 500,
                "retryable": False,
            },
            1,
        )

    is_error = result_is_error(spec, result)
    if not args.no_metadata and not is_error:
        result = attach_run_metadata(result, tool_name=spec.run_metadata_name)

    # Project to requested top-level fields (token budgeting). Never trim an
    # error payload — that would drop the `error` key the caller needs.
    if not is_error and getattr(args, "fields", None):
        result = project_fields(result, args.fields)

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if is_error else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
