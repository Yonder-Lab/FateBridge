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
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, get_origin

from fatebridge.core.tool_spec import (
    ToolSpec,
    describe_spec,
    execute_spec,
)
from fatebridge.core.tool_spec import field_type_name as _type_name
from fatebridge.core.tool_spec import (
    invalid_input_result,
    project_fields,
    result_is_error,
)
from fatebridge.core.tool_spec import spec_is_cli_safe as _cli_safe
from fatebridge.core.tool_spec import unwrap_optional as _unwrap_optional
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.services.tool_catalog import CATALOG
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    format_json_response,
    resolve_birth_place_context,
)


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


def _add_field_argument(
    parser: argparse.ArgumentParser,
    name: str,
    field: Any,
    *,
    relax_required: bool = False,
) -> None:
    annotation = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    is_required = field.is_required()
    # When a --subject-file supplies this field, drop the argparse-level
    # requirement so the file value can satisfy it; pydantic still validates the
    # merged result, so a genuinely-missing field is still reported.
    required = is_required and not relax_required
    # Suppress argparse-level defaults so the parsed namespace contains ONLY the
    # flags the user actually passed. This lets a --subject-file fill optional
    # fields (gender, birth_place, ...) without their model defaults silently
    # shadowing the file values, while pydantic still supplies the real default
    # for anything neither source provides.
    default = argparse.SUPPRESS
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


def build_parser(
    relaxed_required: Optional[set[str]] = None,
) -> argparse.ArgumentParser:
    relaxed = relaxed_required or set()
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

    _add_profile_parser(sub)

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
            _add_field_argument(sp, fname, field, relax_required=fname in relaxed)
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
    parser.add_argument(
        "--compact",
        action="store_true",
        default=False,
        help="紧凑 JSON 输出（无缩进），便于脚本管道；默认美化缩进。",
    )
    parser.add_argument(
        "--include-snapshot-text",
        dest="include_snapshot_text",
        action=_BooleanFlagAction,
        default=None,
        help=(
            "是否包含人类可读的 snapshot_text 文本段（默认随工具而定）；"
            "用 --no-include-snapshot-text 关闭可显著省 token。"
        ),
    )
    parser.add_argument(
        "--subject-file",
        dest="subject_file",
        default=None,
        metavar="PATH",
        help=(
            "从 JSON/YAML 档案读取命主信息（name/gender/birth_* 等）作为默认值，"
            "省去多次调用时重复输入；命令行显式参数优先于档案值。"
        ),
    )


def _parse_json_subject(text: str, path: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"subject 档案 {path} 不是合法 JSON：{error}") from error


def _parse_yaml_subject(text: str, path: str) -> Any:
    try:
        import yaml
    except ImportError as error:  # pyyaml is an optional dependency
        raise ValueError(
            f"解析 YAML subject 档案 {path} 需要 pyyaml；请 `pip install pyyaml` "
            "或改用 JSON 档案。"
        ) from error
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ValueError(f"subject 档案 {path} 不是合法 YAML：{error}") from error


def _load_subject_file(path: str) -> Dict[str, Any]:
    """Load a reusable subject profile (person fields) from JSON or YAML.

    JSON is parsed with the stdlib; YAML needs the optional ``pyyaml`` extra.
    Returns a flat ``field name -> value`` mapping; the caller decides which
    keys are relevant to the invoked tool (extras are ignored downstream).
    """
    file_path = Path(path).expanduser()
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"无法读取 subject 档案 {path}：{error}") from error

    suffix = file_path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        data: Any = _parse_yaml_subject(text, path)
    elif suffix == ".json":
        data = _parse_json_subject(text, path)
    else:
        # Unknown extension: try strict JSON first, then fall back to YAML.
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = _parse_yaml_subject(text, path)

    if not isinstance(data, dict):
        raise ValueError(
            f"subject 档案 {path} 必须是键值映射（字段名→值），"
            f"实际得到 {type(data).__name__}"
        )
    return data


def _preload_subject(
    argv: Optional[List[str]],
) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Peek at ``--subject-file`` before the main parse.

    Returns ``(path, data)`` so the loaded fields can relax otherwise-required
    flags. ``data`` is ``None`` when no usable ``--subject-file`` is present.
    Raises ``ValueError`` if the referenced file cannot be loaded.
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--subject-file", dest="subject_file", default=None)
    try:
        pre_args, _ = pre.parse_known_args(argv)
    except SystemExit:
        # Malformed pre-parse (e.g. --subject-file with no value): defer to the
        # main parser so the canonical JSON usage error is emitted.
        return None, None
    path = pre_args.subject_file
    if not path:
        return None, None
    return path, _load_subject_file(path)


# --- profile: run several charts for one subject in a single invocation ------

DEFAULT_PROFILE_SYSTEMS = "bazi,ziwei,astro"

# Friendly system tokens -> catalog command names. Raw command names also work.
SYSTEM_ALIASES = {
    "bazi": "bazi_birth",
    "八字": "bazi_birth",
    "ziwei": "ziwei_birth",
    "紫微": "ziwei_birth",
    "紫微斗数": "ziwei_birth",
    "astro": "astro_chart",
    "astrology": "astro_chart",
    "西占": "astro_chart",
    "占星": "astro_chart",
    "personality": "bazi_personality",
    "性格": "bazi_personality",
    "career": "bazi_career",
    "事业": "bazi_career",
    "marriage": "bazi_marriage",
    "婚姻": "bazi_marriage",
    "health": "bazi_health",
    "健康": "bazi_health",
    "romance": "bazi_romance",
    "桃花": "bazi_romance",
}

# Person/time inputs shared by every chart; gathered from the core specs so
# types/help stay in sync with the models. birth_latitude lives only on astro.
_PROFILE_PERSON_FIELDS = (
    "name",
    "gender",
    "birth_year",
    "birth_month",
    "birth_day",
    "birth_hour",
    "birth_minute",
    "birth_place",
    "birth_longitude",
    "birth_latitude",
    "birth_timezone",
    "use_true_solar_time",
)
_PROFILE_REQUIRED_FIELDS = ("birth_year", "birth_month", "birth_day", "birth_hour")


def _profile_field_objects() -> Dict[str, Any]:
    """Resolve each shared person field to a model field object from a core spec."""
    core = ("bazi_birth", "ziwei_birth", "astro_chart")
    specs = [s for s in CATALOG if _command_name(s) in core]
    resolved: Dict[str, Any] = {}
    for name in _PROFILE_PERSON_FIELDS:
        for spec in specs:
            field = spec.request_model.model_fields.get(name)
            if field is not None:
                resolved[name] = field
                break
    return resolved


def _add_profile_parser(sub: Any) -> None:
    parser = sub.add_parser(
        "profile",
        help="综合命盘：一次为同一命主排多套盘（默认 八字/紫微/西占）",
    )
    parser.add_argument(
        "--systems",
        default=None,
        metavar="LIST",
        help=(
            "逗号分隔的体系或工具，默认 bazi,ziwei,astro。"
            "支持别名（八字/紫微/西占/性格/事业/婚姻/健康/桃花）或直接用工具命令名。"
        ),
    )
    # Person flags are never argparse-required here; requiredness is checked
    # after merging --subject-file so the file alone can drive a profile.
    for fname, field in _profile_field_objects().items():
        _add_field_argument(parser, fname, field, relax_required=True)
    parser.add_argument(
        "--subject-file",
        dest="subject_file",
        default=None,
        metavar="PATH",
        help="从 JSON/YAML 档案读取命主信息；命令行参数优先于档案值。",
    )
    parser.set_defaults(_profile=True)


def _resolve_profile_systems(
    tokens: List[str],
) -> "tuple[List[tuple[str, ToolSpec]], List[str]]":
    resolved: List[tuple[str, ToolSpec]] = []
    unknown: List[str] = []
    for token in tokens:
        name = SYSTEM_ALIASES.get(token.lower(), token)
        spec = next((s for s in CATALOG if _command_name(s) == name), None)
        if spec is None or not _cli_safe(spec):
            unknown.append(token)
        else:
            resolved.append((token, spec))
    return resolved, unknown


def _unify_birth_instant(inputs: Dict[str, Any]) -> None:
    """Resolve ONE birth timezone for every profile leg.

    The legs historically disagreed on timezone defaults: ``astro_chart`` once
    defaulted ``birth_timezone='UTC'`` while ``bazi_birth``/``ziwei_birth``
    derived it from the place. Left alone, omitting the timezone made the
    western leg read a China wall-clock time as UTC — landing it ~8h off the
    Chinese legs and rotating the whole chart. We resolve the timezone once here
    (mirroring the BaZi normalizer: ``explicit -> place-derived ->
    DEFAULT_BIRTH_TIMEZONE``; see ``normalize_birth_time`` in utils/helpers) and
    inject it into every leg so they share one civil instant.

    True-solar policy is deliberately NOT unified: each leg keeps its own
    tradition default — 八字/紫微 rebase onto true solar time (apparent-solar
    时辰/命宫), western astrology casts on the recorded civil clock. The two
    differ only by the longitude + equation-of-time offset (~minutes), not the
    ~8h timezone gap, and the difference reflects each system's convention
    rather than a bug. A user-supplied ``use_true_solar_time`` still wins and
    applies uniformly to every leg.

    Mutates ``inputs`` in place; ``birth_timezone`` is only filled when absent.
    """
    if not inputs.get("birth_timezone"):
        resolved = resolve_birth_place_context(inputs.get("birth_place"))
        inputs["birth_timezone"] = resolved.timezone or DEFAULT_BIRTH_TIMEZONE


def _run_profile(
    args: argparse.Namespace, subject_data: Optional[Dict[str, Any]]
) -> int:
    raw = getattr(args, "systems", None) or DEFAULT_PROFILE_SYSTEMS
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    resolved, unknown = _resolve_profile_systems(tokens)
    if unknown:
        return _emit_error(
            {
                "error": (
                    f"未知体系/工具: {', '.join(unknown)}；"
                    "可用别名见 `fatebridge profile --help`，或用 `fatebridge list` 的命令名。"
                ),
                "error_code": "usage_error",
                "status_code": 400,
                "retryable": False,
            },
            2,
        )

    # Shared person inputs: subject-file defaults, then explicit CLI flags win.
    inputs: Dict[str, Any] = {}
    if subject_data:
        inputs.update({k: v for k, v in subject_data.items() if v is not None})
    for fname in _PROFILE_PERSON_FIELDS:
        if fname in vars(args):  # SUPPRESS -> present only if user passed it
            inputs[fname] = getattr(args, fname)

    missing = [f for f in _PROFILE_REQUIRED_FIELDS if inputs.get(f) is None]
    if missing:
        flags = ", ".join("--" + f.replace("_", "-") for f in missing)
        return _emit_error(
            {
                "error": (
                    f"综合命盘缺少必填出生信息: {flags}（可由 --subject-file 提供）。"
                ),
                "error_code": "usage_error",
                "status_code": 400,
                "retryable": False,
            },
            2,
        )

    _unify_birth_instant(inputs)

    profile: Dict[str, Any] = {}
    any_error = False
    for token, spec in resolved:
        field_names = set(spec.request_model.model_fields)
        provided = {
            k: v for k, v in inputs.items() if k in field_names and v is not None
        }
        try:
            result = execute_spec(spec, spec.request_model(**provided))
        except ValueError:
            result = invalid_input_result(spec)
        except Exception as exc:  # noqa: BLE001 - surface, don't abort the batch
            result = {
                "error": str(exc),
                "error_code": "internal_error",
                "status_code": 500,
                "retryable": False,
            }
        if result_is_error(spec, result):
            any_error = True
        profile[token] = result

    output: Dict[str, Any] = {
        "analysis_type": "综合命盘",
        "systems": [token for token, _ in resolved],
        "profile": profile,
    }
    if not args.no_metadata:
        output = attach_run_metadata(output, tool_name="profile")
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 1 if any_error else 0


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
    try:
        _subject_path, subject_data = _preload_subject(argv)
    except ValueError as error:
        return _emit_error(
            {
                "error": str(error),
                "error_code": "usage_error",
                "status_code": 400,
                "retryable": False,
            },
            2,
        )
    relaxed = set(subject_data) if subject_data else set()
    parser = build_parser(relaxed)
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

    if getattr(args, "_profile", False):
        return _run_profile(args, subject_data)

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

    # A --subject-file supplies reusable person defaults so multi-tool sessions
    # need not re-type birth data. Explicit CLI flags always win over the file.
    if subject_data:
        defaults = {
            k: v
            for k, v in subject_data.items()
            if k in field_names and v is not None and k not in provided
        }
        provided = {**defaults, **provided}

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

    # Output shaping, mirroring REST/MCP. ``--include-snapshot-text`` defaults to
    # None -> fall back to the spec's own default, preserving today's behavior
    # (snapshot kept, pretty-printed). Error payloads carry no snapshot_text, so
    # the flag is a no-op for them; --compact still applies uniformly.
    include_snapshot_text = getattr(args, "include_snapshot_text", None)
    if include_snapshot_text is None:
        include_snapshot_text = spec.include_snapshot_text
    print(
        format_json_response(
            result,
            compact=getattr(args, "compact", False),
            include_snapshot_text=include_snapshot_text,
        )
    )
    return 1 if is_error else 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
