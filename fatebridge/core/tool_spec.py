"""
Central tool specification + multi-surface registrars for FateBridge.

A ``ToolSpec`` declares a tool ONCE — its service function, input model, paths,
and metadata — and the registrars in this module mount it onto every transport
surface (FastAPI REST, FastMCP, and the CLI). Adding a new tool means adding one
``ToolSpec`` to the catalog; no transport file needs editing.

The module is transport-agnostic: the heavy/threaded execution wrapper, the
HTTP error raiser, and the MCP renderers are injected by the caller so this
module imports neither FastAPI nor FastMCP at import time.

NOTE: this module intentionally does NOT use ``from __future__ import
annotations`` — FastAPI/FastMCP read live annotation objects off the generated
handler signatures, and stringified annotations would break schema inference.
"""

import inspect
from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field

from fatebridge.utils.helpers import (
    VALIDATION_ERROR_CODE,
    PersonInfo,
    create_person_info,
)

ServiceResult = Dict[str, Any]
# A bind turns a validated request model into a concrete service call:
#   (service_callable, positional_args, keyword_args)
# Surfaces then execute it (REST offloads it to a threadpool; MCP calls it
# directly), which keeps the *domain service* — not a wrapper — as the unit of
# work that gets offloaded.
Bind = Callable[[BaseModel], Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]]


@dataclass(frozen=True)
class ToolSpec:
    """Single source of truth for one FateBridge tool across all surfaces."""

    key: str
    bind: Bind
    request_model: Type[BaseModel]
    summary: str
    operation_label_zh: str
    family: str
    rest_path: Optional[str] = None
    mcp_name: Optional[str] = None
    cpu_bound: bool = False
    include_snapshot_text: bool = True
    result_transform: Optional[Callable[[ServiceResult], ServiceResult]] = None
    error_is_fatal: Optional[Callable[[ServiceResult], bool]] = None
    rest_error_label: Optional[str] = None
    metadata_name: Optional[str] = None

    @property
    def tool_name(self) -> str:
        return self.mcp_name or self.key

    @property
    def run_metadata_name(self) -> str:
        """The tool_name stamped into run_metadata (may differ from the registered name)."""
        return self.metadata_name or self.mcp_name or self.key


# ---------------------------------------------------------------------------
# Binder factories: validated request model -> raw service result dict
# ---------------------------------------------------------------------------

_PERSON_POSITIONAL = (
    "birth_year",
    "birth_month",
    "birth_day",
    "birth_hour",
    "name",
    "gender",
    "birth_place",
)
_PERSON_KEYWORD = (
    "birth_minute",
    "birth_timezone",
    "birth_longitude",
    "use_true_solar_time",
)


def _build_person(
    data: Dict[str, Any], prefix: str = "", *, true_solar_explicit: bool = True
) -> PersonInfo:
    def g(field: str, default: Any = None) -> Any:
        return data.get(f"{prefix}{field}", default)

    return create_person_info(
        g("birth_year"),
        g("birth_month"),
        g("birth_day"),
        g("birth_hour"),
        g("name", "未提供"),
        g("gender", "未知"),
        g("birth_place", "未提供"),
        birth_minute=g("birth_minute", 0),
        birth_timezone=g("birth_timezone"),
        birth_longitude=g("birth_longitude"),
        use_true_solar_time=g("use_true_solar_time", False),
        true_solar_explicit=true_solar_explicit,
    )


def person_invoke(
    service: Callable[..., ServiceResult], *, also_pass: Tuple[str, ...] = ()
) -> Bind:
    """Single-person tools: bind to service(person, **extras).

    ``extras`` is auto-derived as every request field that is NOT a standard
    person field, so a tool only needs to declare its model. ``also_pass`` adds
    back person fields that a service consumes a second time (e.g. a tool whose
    analysis step also honours ``use_true_solar_time``).
    """
    person_fields = set(_PERSON_POSITIONAL) | set(_PERSON_KEYWORD)

    def _bind(
        req: BaseModel,
    ) -> Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]:
        data = req.model_dump()
        # 区分「用户显式要求真太阳时」与「吃了模型默认」：缺经度时前者 fail-loud、
        # 后者降级为钟表时间并附 advisory（见 normalize_birth_time）。
        explicit = "use_true_solar_time" in req.model_fields_set
        person = _build_person(data, true_solar_explicit=explicit)
        extras = {k: v for k, v in data.items() if k not in person_fields}
        for field in also_pass:
            if field in data:
                extras[field] = data[field]
        return service, (person,), extras

    return _bind


def pair_invoke(
    service: Callable[..., ServiceResult],
    *,
    relationship_field: str = "relationship_type",
) -> Bind:
    """Two-person compatibility: bind to service(person1, person2, relationship)."""

    def _bind(
        req: BaseModel,
    ) -> Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]:
        data = req.model_dump()
        fields_set = req.model_fields_set
        p1 = _build_person(
            data,
            prefix="person1_",
            true_solar_explicit="person1_use_true_solar_time" in fields_set,
        )
        p2 = _build_person(
            data,
            prefix="person2_",
            true_solar_explicit="person2_use_true_solar_time" in fields_set,
        )
        rel = data.get(relationship_field, "general")
        return service, (p1, p2, rel), {}

    return _bind


def _accepted_kwargs(service: Callable[..., Any]) -> Optional[set]:
    """Return the set of keyword param names a service accepts, or None if it has **kwargs."""
    sig = inspect.signature(service)
    accepted = set()
    for name, param in sig.parameters.items():
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            return None  # accepts anything
        if param.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            accepted.add(name)
    return accepted


def raw_invoke(
    service: Callable[..., ServiceResult],
    *,
    fixed: Optional[Dict[str, Any]] = None,
) -> Bind:
    """Raw tools: bind to service(**model_dump), filtered to accepted kwargs.

    Filtering lets a model carry inherited fields a service does not consume
    (e.g. TaiyiAnalysisRequest inherits ``qimen_options`` from its base).
    """
    accepted = _accepted_kwargs(service)

    def _bind(
        req: BaseModel,
    ) -> Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]:
        data = req.model_dump()
        if accepted is not None:
            data = {k: v for k, v in data.items() if k in accepted}
        # Thread whether the user explicitly asked for true solar time so the
        # service can fail-loud on an explicit request that lacks a longitude,
        # yet gracefully fall back to civil time when the flag merely defaulted
        # on (mirrors the person path in ``person_invoke``). Only inject into
        # services that explicitly declare the parameter — never into a
        # ``**kwargs`` dispatcher (``accepted is None``), which would forward the
        # unknown kwarg to an inner service that does not accept it.
        if accepted is not None and "true_solar_explicit" in accepted:
            data["true_solar_explicit"] = "use_true_solar_time" in req.model_fields_set
        if fixed:
            data = {**data, **fixed}
        return service, (), data

    return _bind


# ---------------------------------------------------------------------------
# Pydantic model -> inspect.Parameter list (drives MCP schema + CLI args)
# ---------------------------------------------------------------------------


def execute_spec(spec: ToolSpec, request: BaseModel) -> ServiceResult:
    """Synchronously run a spec's bound service call (used by MCP and the CLI).

    ``result_transform`` is applied only to *non-error* results, mirroring the
    REST surface (where a fatal error short-circuits before the transform ever
    runs). This keeps error payloads identical across REST/MCP/CLI, so a
    transform that assumes a success-shaped result can never silently corrupt
    an error dict on the MCP/CLI path.
    """
    service, args, kwargs = spec.bind(request)
    result = service(*args, **kwargs)
    if spec.result_transform is not None and not result_is_error(spec, result):
        result = spec.result_transform(result)
    return result


def project_fields(
    result: ServiceResult, fields: Optional[Iterable[str]]
) -> ServiceResult:
    """Project a result to a subset of keys for token budgeting.

    Supports two forms, freely mixed:

    - **Top-level**: ``"snapshot_text"`` keeps that whole top-level value.
    - **Dotted sub-path**: ``"bazi_birth.day_master"`` keeps ``bazi_birth`` but
      prunes it to just ``day_master`` (recurses to any depth). This lets an
      agent pull a scalar buried in an otherwise huge block (e.g. the ~50KB
      ``bazi_birth`` payload) without dumping the whole thing.

    Rules: ``run_metadata`` is always preserved whole. Asking for a whole parent
    AND a sub-path of it keeps the whole parent (whole wins, any order). A
    ``None``/empty selection returns the result unchanged. Unknown top-level keys
    are ignored; an unknown sub-key yields an empty parent; a sub-path under a
    non-dict value keeps that value as-is.
    """
    if not fields:
        return result
    tree = _build_selection_tree(fields)
    tree["run_metadata"] = True  # provenance always survives, whole
    return {
        key: _apply_selection(result[key], child)
        for key, child in tree.items()
        if key in result
    }


# A selection node is ``True`` ("keep this subtree whole") or a dict of children.
def _build_selection_tree(fields: Iterable[str]) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    for field in fields:
        node = root
        parts = field.split(".")
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                node[part] = True  # whole-keep wins over any partial selection
                break
            child = node.get(part)
            if child is True:
                break  # parent already requested whole; sub-path is subsumed
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
    return root


def _apply_selection(value: Any, node: Any) -> Any:
    if node is True or not isinstance(value, dict):
        return value
    return {
        k: _apply_selection(value[k], child) for k, child in node.items() if k in value
    }


def result_is_error(spec: ToolSpec, result: ServiceResult) -> bool:
    """Classify a service result as an error, honoring spec.error_is_fatal.

    Mirrors the REST transport's logic so every surface (REST/MCP/CLI) treats
    failures identically.
    """
    if spec.error_is_fatal is not None:
        return bool(spec.error_is_fatal(result))
    return "error" in result


def invalid_input_result(spec: ToolSpec) -> ServiceResult:
    """Error result for invalid input, mirroring the REST 400 path.

    REST maps any ``ValueError``/``ValidationError`` raised while binding or
    validating a request to HTTP 400 with a generic ``无效的<label>`` detail
    (it deliberately does not leak the raw exception text). MCP and the CLI have
    no HTTP layer, so they render this same shape through the normal error
    renderer — keeping bad-input handling identical across every surface instead
    of leaking a raw traceback on MCP.

    The ``error_code`` reuses the same ``validation_error`` token that
    ``handle_calculation_error`` emits for service-layer ``ValueError``s, so an
    agent can branch on ``error_code`` regardless of *where* the bad input was
    caught. The two paths differ only in message detail — and that difference is
    intentional: this binding-layer path stays generic because a raw pydantic
    ``ValidationError`` can echo caller input, whereas a service raises a
    hand-written domain message that is safe and useful to surface. Branch on
    ``error_code``, not on message text.
    """
    label = spec.rest_error_label or f"{spec.operation_label_zh}参数"
    return {
        "error": f"无效的{label}",
        "error_code": VALIDATION_ERROR_CODE,
        "status_code": 400,
        "retryable": False,
    }


def model_parameters(
    model: Type[BaseModel],
) -> Tuple[List[inspect.Parameter], Dict[str, Any]]:
    """Convert a pydantic model's fields into ordered inspect.Parameters."""
    required: List[inspect.Parameter] = []
    optional: List[inspect.Parameter] = []
    annotations: Dict[str, Any] = {}
    for name, field in model.model_fields.items():
        ann = field.annotation if field.annotation is not None else Any
        annotations[name] = ann
        if field.is_required():
            required.append(
                inspect.Parameter(
                    name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=ann
                )
            )
        else:
            default = field.get_default(call_default_factory=True)
            optional.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=ann,
                    default=default,
                )
            )
    return required + optional, annotations


# ---------------------------------------------------------------------------
# Capability discovery (shared by the CLI ``describe`` command and REST
# ``GET /api/tools``) — one self-describing record per tool, derived from the
# catalog so it never drifts from the live tool set.
# ---------------------------------------------------------------------------


def unwrap_optional(annotation: Any) -> Any:
    """Strip a single ``Optional[...]`` / ``Union[..., None]`` wrapper."""
    if get_origin(annotation) is Union:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if non_none:
            return non_none[0]
    return annotation


def is_model_field(annotation: Any) -> bool:
    """True if the (unwrapped) annotation is a nested pydantic model."""
    base = unwrap_optional(annotation)
    return isinstance(base, type) and issubclass(base, BaseModel)


def field_type_name(annotation: Any) -> str:
    """Render a field annotation as a short, agent-readable type string."""
    base = unwrap_optional(annotation)
    origin = get_origin(base)
    if origin in (list, List):
        args = get_args(base)
        inner = getattr(args[0], "__name__", str(args[0])) if args else "str"
        return f"list[{inner}]"
    if isinstance(base, type):
        return base.__name__
    return str(base)


def spec_is_cli_safe(spec: "ToolSpec") -> bool:
    """A spec is CLI-exposable only if none of its fields are nested models."""
    return not any(
        is_model_field(f.annotation) for f in spec.request_model.model_fields.values()
    )


def describe_spec(spec: "ToolSpec") -> Dict[str, Any]:
    """Self-describing, transport-agnostic record for one tool.

    The CLI ``describe`` command and the REST ``GET /api/tools`` endpoint both
    render this, so an agent sees the same parameter schema, surfaces, and family
    regardless of how it discovers the tool. ``surfaces.mcp_name`` is ``None`` for
    REST-only tools so an agent never assumes an MCP tool that does not exist.
    """
    parameters = [
        {
            "name": name,
            "flag": "--" + name.replace("_", "-"),
            "type": field_type_name(field.annotation),
            "required": field.is_required(),
            "default": (
                None
                if field.is_required()
                else field.get_default(call_default_factory=True)
            ),
            "description": field.description or "",
            "nested_model": is_model_field(field.annotation),
        }
        for name, field in spec.request_model.model_fields.items()
    ]
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
        "parameters": parameters,
    }


# ---------------------------------------------------------------------------
# REST registrar (FastAPI)
# ---------------------------------------------------------------------------


def register_rest(
    app: Any,
    specs: List[ToolSpec],
    *,
    execute_service: Callable[..., Any],
    logger: Any = None,
    summarize_context: Optional[Callable[..., str]] = None,
) -> None:
    """Mount every spec with a ``rest_path`` as a POST route on the FastAPI app."""
    from fastapi import HTTPException

    for spec in specs:
        if not spec.rest_path:
            continue
        app.add_api_route(
            spec.rest_path,
            make_rest_handler(
                spec,
                execute_service=execute_service,
                http_exception=HTTPException,
                logger=logger,
            ),
            methods=["POST"],
            name=f"rest_{spec.key}",
        )


def make_rest_handler(
    spec: ToolSpec,
    *,
    execute_service: Callable[..., Any],
    http_exception: Any,
    logger: Any = None,
) -> Callable[..., Any]:
    model = spec.request_model
    error_label = spec.rest_error_label or f"{spec.operation_label_zh}参数"

    async def handler(request: Any) -> Any:  # signature injected below
        try:
            if logger is not None:
                logger.info("Processing %s request", spec.tool_name)
            service, args, kwargs = spec.bind(request)
            result = await execute_service(
                service,
                *args,
                tool_name=spec.run_metadata_name,
                cpu_bound=spec.cpu_bound,
                error_is_fatal=spec.error_is_fatal,
                **kwargs,
            )
            if spec.result_transform is not None:
                result = spec.result_transform(result)
            return result
        except ValueError:
            raise http_exception(status_code=400, detail=f"无效的{error_label}")
        except http_exception:
            raise
        except Exception as exc:  # noqa: BLE001
            if logger is not None:
                logger.error(
                    "Unexpected error during %s: %s", spec.tool_name, exc, exc_info=True
                )
            raise http_exception(status_code=500, detail="内部服务器错误")

    handler.__name__ = f"rest_{spec.key}"
    handler.__doc__ = spec.summary
    setattr(
        handler,
        "__signature__",
        inspect.Signature(
            [
                inspect.Parameter(
                    "request",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=model,
                )
            ]
        ),
    )
    handler.__annotations__ = {"request": model, "return": dict}
    return handler


# ---------------------------------------------------------------------------
# MCP registrar (FastMCP)
# ---------------------------------------------------------------------------

# Descriptions for the three transport flags every MCP tool gains. Surfaced in
# the tool schema so an agent can use them without out-of-band documentation.
_COMPACT_FLAG_DESC = "紧凑 JSON 输出（无缩进）；设为 false 则美化缩进。默认 true。"
_SNAPSHOT_FLAG_DESC = (
    "是否包含人类可读的 snapshot_text 文本段（默认随工具而定）；"
    "设为 false 可显著减少返回的 token 数。"
)
_FIELDS_FLAG_DESC = (
    "仅返回选定字段以节省 token：接受顶层键（如 'snapshot_text'）或点路径"
    "子字段（如 'bazi_birth.day_master'）。run_metadata 始终保留；留空返回全部字段。"
)


def register_mcp(
    app: Any,
    specs: List[ToolSpec],
    *,
    render_response: Callable[..., str],
    render_error: Callable[..., str],
) -> None:
    """Register every spec with an ``mcp_name`` (or key) as a FastMCP tool."""
    from fastmcp.tools import Tool

    for spec in specs:
        if spec.mcp_name is None and spec.key is None:
            continue
        fn = _make_mcp_fn(
            spec, render_response=render_response, render_error=render_error
        )
        app.add_tool(
            Tool.from_function(fn, name=spec.tool_name, description=spec.summary)
        )


def _make_mcp_fn(
    spec: ToolSpec,
    *,
    render_response: Callable[..., str],
    render_error: Callable[..., str],
) -> Callable[..., str]:
    model = spec.request_model
    params, annotations = model_parameters(model)
    # Transport-level flags appended after model fields; guard against a model
    # field shadowing them (would make the flag unsettable / silently swallowed).
    _reserved = {"compact", "include_snapshot_text", "fields"}
    _clash = _reserved & set(model.model_fields)
    if _clash:
        raise ValueError(
            f"Tool '{spec.tool_name}' request model has reserved field name(s) {_clash}; "
            "these collide with MCP transport flags."
        )
    # Annotated[..., Field(description=...)] is what FastMCP/pydantic read for
    # per-parameter docs — inspect.Parameter has no description slot. Without
    # these, an LLM sees three bare flags and has to guess their meaning (and the
    # dotted-path syntax for ``fields`` lived only in CLI help).
    compact_t = Annotated[bool, Field(description=_COMPACT_FLAG_DESC)]
    snapshot_t = Annotated[bool, Field(description=_SNAPSHOT_FLAG_DESC)]
    fields_t = Annotated[Optional[List[str]], Field(description=_FIELDS_FLAG_DESC)]
    params.append(
        inspect.Parameter(
            "compact",
            inspect.Parameter.KEYWORD_ONLY,
            annotation=compact_t,
            default=True,
        )
    )
    params.append(
        inspect.Parameter(
            "include_snapshot_text",
            inspect.Parameter.KEYWORD_ONLY,
            annotation=snapshot_t,
            default=spec.include_snapshot_text,
        )
    )
    params.append(
        inspect.Parameter(
            "fields",
            inspect.Parameter.KEYWORD_ONLY,
            annotation=fields_t,
            default=None,
        )
    )
    annotations = {
        **annotations,
        "compact": compact_t,
        "include_snapshot_text": snapshot_t,
        "fields": fields_t,
    }

    def impl(**kwargs: Any) -> str:
        compact = kwargs.pop("compact", True)
        include_snapshot_text = kwargs.pop(
            "include_snapshot_text", spec.include_snapshot_text
        )
        fields = kwargs.pop("fields", None)
        try:
            request = model(**kwargs)
            result = execute_spec(spec, request)
        except ValueError:
            # Mirror REST's ValueError -> 400: bad input (incl. pydantic
            # ValidationError, which subclasses ValueError, and date checks
            # raised during binding) renders as a clean error instead of
            # bubbling a raw exception out of the MCP tool.
            return render_error(
                invalid_input_result(spec), spec.operation_label_zh, compact=compact
            )
        if result_is_error(spec, result):
            return render_error(result, spec.operation_label_zh, compact=compact)
        return render_response(
            result,
            compact=compact,
            include_snapshot_text=include_snapshot_text,
            fields=fields,
            tool_name=spec.run_metadata_name,
        )

    impl.__name__ = spec.tool_name
    impl.__doc__ = spec.summary
    setattr(impl, "__signature__", inspect.Signature(params))
    impl.__annotations__ = {**annotations, "return": str}
    return impl
