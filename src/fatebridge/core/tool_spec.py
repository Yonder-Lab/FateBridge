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

import importlib
import inspect
from copy import copy
from dataclasses import dataclass, field
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

from pydantic import BaseModel, Field, ValidationError
from pydantic_core import PydanticUndefined

from fatebridge.core.execution_context import (
    ExecutionOptions,
    call_clock,
    correlate_error,
    safe_correlation,
)
from fatebridge.core.reproducibility import ReproducibilityPolicy
from fatebridge.utils.errors import (
    ErrorEnvelope,
    ParameterError,
    handle_calculation_error,
    validation_error_result,
)
from fatebridge.utils.helpers import (
    VALIDATION_ERROR_CODE,
    PersonInfo,
    create_person_info,
)

ServiceResult = Dict[str, Any]
# A bind turns a validated request model into a concrete service call:
#   (service_callable, positional_args, keyword_args)
# The shared execution unit invokes this binding (REST offloads the unit to a
# threadpool; MCP/CLI call it synchronously), keeping domain work off the event
# loop while freezing time and attaching receipts consistently.
Bind = Callable[[BaseModel], Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]]


def lazy_service(module: str, name: str) -> Callable[..., ServiceResult]:
    """Return a proxy that imports ``module`` and resolves ``name`` on first call.

    Lets the tool catalog declare a tool's service without importing the
    (sometimes heavy — e.g. the kerykeion-backed western modules) service module
    until that tool is actually invoked. The proxy carries an ``__fb_lazy__``
    marker so binders that introspect the service signature (``raw_invoke``)
    resolve the *real* function rather than the proxy's ``(*args, **kwargs)``
    signature, which would otherwise silently disable kwargs filtering.
    """
    cell: List[Callable[..., ServiceResult]] = []

    def _proxy(*args: Any, **kwargs: Any) -> ServiceResult:
        if not cell:
            cell.append(getattr(importlib.import_module(module), name))
        return cell[0](*args, **kwargs)

    _proxy.__fb_lazy__ = (module, name)  # type: ignore[attr-defined]
    _proxy.__name__ = name
    _proxy.__qualname__ = name
    return _proxy


def resolve_service(service: Callable[..., Any]) -> Callable[..., Any]:
    """Return the real service callable, importing it if ``service`` is lazy."""
    marker = getattr(service, "__fb_lazy__", None)
    if marker is None:
        return service
    module, name = marker
    resolved: Callable[..., Any] = getattr(importlib.import_module(module), name)
    return resolved


def _resolver(
    service: Callable[..., ServiceResult],
) -> Callable[[], Callable[..., ServiceResult]]:
    """Memoise lazy-proxy resolution so a bind unwraps its service exactly once.

    Binders return the *resolved* domain function (not the proxy) so the unit of
    work handed to the surfaces — REST's threadpool, MCP/CLI's direct call — is
    the real service, while the import stays deferred until the first invocation.
    """
    cache: List[Callable[..., ServiceResult]] = []

    def get() -> Callable[..., ServiceResult]:
        if not cache:
            cache.append(resolve_service(service))
        return cache[0]

    return get


@dataclass(frozen=True)
class ExecutionHints:
    """Environment effects, independent of numerical output determinism."""

    read_only: bool = True
    destructive: bool = False
    idempotent: bool = True
    open_world: bool = False

    def as_annotations(self) -> Dict[str, bool]:
        return {
            "readOnlyHint": self.read_only,
            "destructiveHint": self.destructive,
            "idempotentHint": self.idempotent,
            "openWorldHint": self.open_world,
        }


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
    output_model: Optional[Type[BaseModel]] = None
    cli_request_file: bool = False
    execution_hints: ExecutionHints = field(default_factory=ExecutionHints)
    reproducibility: ReproducibilityPolicy = field(
        default_factory=ReproducibilityPolicy
    )

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
    get_service = _resolver(service)

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
        return get_service(), (person,), extras

    return _bind


def pair_invoke(
    service: Callable[..., ServiceResult],
    *,
    relationship_field: str = "relationship_type",
) -> Bind:
    """Two-person compatibility: bind to service(person1, person2, relationship)."""
    get_service = _resolver(service)

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
        return get_service(), (p1, p2, rel), {}

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

    The accepted-kwargs set is computed lazily on first bind (against the
    *resolved* service, so a lazy proxy is unwrapped to its real signature) and
    memoised — this keeps a lazily-imported service module unloaded until the
    tool is actually invoked.
    """
    get_service = _resolver(service)
    accepted_cache: List[Any] = []  # one-slot memo; the value itself may be None

    def _bind(
        req: BaseModel,
    ) -> Tuple[Callable[..., ServiceResult], tuple, Dict[str, Any]]:
        resolved = get_service()
        if not accepted_cache:
            accepted_cache.append(_accepted_kwargs(resolved))
        accepted = accepted_cache[0]
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
        return resolved, (), data

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
    validate_output(spec, result)
    return result


def execute_tool(
    spec: ToolSpec,
    request: BaseModel,
    *,
    options: Optional[ExecutionOptions] = None,
    include_metadata: bool = True,
) -> ServiceResult:
    """Common transport execution: scoped clock, replay seed and receipt.

    execute_spec remains the metadata-free service execution contract for
    existing library callers; REST still offloads this unit through its executor.
    """
    import secrets
    from time import perf_counter

    from fatebridge.services.replay_metadata import execution_receipt
    from fatebridge.services.run_metadata import attach_run_metadata

    controls = options or ExecutionOptions()
    generated_seed = False
    data = request.model_dump()
    random_cast = False
    if spec.key == "sixyao":
        from fatebridge.core.local_techniques.sixyao import needs_random_coin_cast

        random_cast = needs_random_coin_cast(data)
    if (
        spec.reproducibility.random_seed_field == "seed"
        and random_cast
        and data.get("seed") is None
    ):
        request = request.model_copy(update={"seed": secrets.randbits(32)})
        generated_seed = True
    with call_clock(controls.as_of) as clock:
        started = perf_counter()
        try:
            result = execute_spec(spec, request)
        except ValueError:
            return correlate_error(invalid_input_result(spec), controls)
        except Exception as exc:
            return correlate_error(
                handle_calculation_error(exc, spec.operation_label_zh), controls
            )
        elapsed_ms = (perf_counter() - started) * 1000
        if result_is_error(spec, result):
            return correlate_error(result, controls)
        if not include_metadata:
            return result
        try:
            receipt = execution_receipt(
                spec,
                request,
                result,
                clock=clock,
                options=controls,
                elapsed_ms=elapsed_ms,
                generated_seed=generated_seed,
            )
        except Exception:
            # Receipt serialization/fingerprinting is server output work, never
            # an input rejection even if json.dumps raises ValueError.
            return correlate_error(
                handle_calculation_error(
                    OutputContractError("执行元数据生成失败"), spec.operation_label_zh
                ),
                controls,
            )
        result = attach_run_metadata(result, tool_name=spec.run_metadata_name)
        result["run_metadata"] = {**result["run_metadata"], **receipt}
        if result["run_metadata"]["engine_is_approximate"]:
            result["run_metadata"]["warnings"].append("approximate_engine")
        if controls.trace_id is not None:
            result["run_metadata"]["trace_id"] = controls.trace_id
        validate_output(spec, result)
        return result


class OutputContractError(RuntimeError):
    """A service bug, never a user-input error."""


def validate_output(spec: ToolSpec, result: ServiceResult) -> None:
    if spec.output_model is not None and not result_is_error(spec, result):
        try:
            spec.output_model.model_validate(result)
        except ValidationError as exc:
            raise OutputContractError("工具输出不符合公开契约") from exc


def project_fields(
    result: ServiceResult,
    fields: Optional[Iterable[str]],
    *,
    strict_fields: bool = False,
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
    ``None``/empty selection returns the result unchanged. Lenient projection
    retains historical data shaping, with visible ``projection_warnings`` for
    every invalid path. Strict projection rejects them before shaping any data.
    Paths traverse objects only; arrays and scalars must be selected whole.
    """
    if not fields:
        return result
    fields = list(fields)
    if not fields:
        return result
    issues = _projection_issues(result, fields)
    if issues and strict_fields:
        raise ParameterError("输出字段投影无效", issues)
    tree = _build_selection_tree(fields)
    tree["run_metadata"] = True  # provenance always survives, whole
    projected = {
        key: _apply_selection(result[key], child)
        for key, child in tree.items()
        if key in result
    }
    if issues:
        projected["projection_warnings"] = issues
    return projected


def _projection_issues(
    result: ServiceResult, fields: List[str]
) -> List[Dict[str, str]]:
    issues = []
    for path in dict.fromkeys(fields):
        parts = path.split(".")
        code = ""
        if any(not part or part.strip() != part for part in parts):
            code = "invalid_projection_path"
        else:
            value: Any = result
            for part in parts:
                if not isinstance(value, dict):
                    code = "non_object_projection_path"
                    break
                if part not in value:
                    code = "unknown_projection_path"
                    break
                value = value[part]
        if code:
            issues.append({"path": path, "code": code})
    return issues


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

    REST maps a ``ValueError`` raised while binding a validated request to
    HTTP 400 with a generic ``无效的<label>`` detail
    (it deliberately does not leak the raw exception text). MCP and the CLI have
    no HTTP layer, so they render this same shape through the normal error
    renderer — keeping bad-input handling identical across every surface instead
    of leaking a raw traceback on MCP.

    The ``error_code`` reuses the same ``validation_error`` token that
    ``handle_calculation_error`` emits for service-layer ``ValueError``s, so an
    agent can branch on ``error_code`` regardless of *where* the bad input was
    caught. The two paths differ only in message detail — and that difference is
    intentional: this binding-layer path stays generic, whereas a service raises a
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


_MCP_OMITTED = object()
_MCP_SOLAR_FIELDS = {
    "use_true_solar_time",
    "person1_use_true_solar_time",
    "person2_use_true_solar_time",
}


def _mcp_omitted_default() -> Any:
    return _MCP_OMITTED


def model_parameters(
    model: Type[BaseModel],
) -> Tuple[List[inspect.Parameter], Dict[str, Any]]:
    """Expose model constraints while preserving omitted solar-time flags."""
    required: List[inspect.Parameter] = []
    optional: List[inspect.Parameter] = []
    annotations: Dict[str, Any] = {}
    for name, field in model.model_fields.items():
        metadata = copy(field)
        metadata.default = PydanticUndefined
        metadata.default_factory = None
        # MCP has always exposed Python names. Keep them stable; model-level
        # aliases remain the REST contract, not callable-parameter metadata.
        metadata.alias = None
        metadata.validation_alias = None
        metadata.serialization_alias = None
        preserve_omission = name in _MCP_SOLAR_FIELDS and not field.is_required()
        if preserve_omission:
            # Pydantic fills signature defaults before calling impl. A factory
            # gives omitted booleans a private sentinel without accepting null
            # or changing the request model's actual default.
            metadata.default_factory = _mcp_omitted_default
        ann: Any = Annotated[
            field.annotation if field.annotation is not None else Any, metadata
        ]
        annotations[name] = ann
        if field.is_required():
            required.append(
                inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, annotation=ann)
            )
        else:
            default = field.get_default(call_default_factory=True)
            optional.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=ann,
                    default=inspect.Parameter.empty if preserve_omission else default,
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
    # Multi-member Unions (e.g. ``house_system: Union[int, str]``) must surface
    # every accepted type, not just the first — otherwise an agent reading the
    # self-describe surface sees only ``int`` and never learns it may pass
    # ``"placidus"``/``"equal_mc"``. (MCP input validation is unaffected; it
    # binds the live annotation, but the human/agent-readable ``type`` string
    # comes from here.)
    if get_origin(annotation) is Union:
        non_none = [a for a in get_args(annotation) if a is not type(None)]
        if len(non_none) > 1:
            return " | ".join(field_type_name(a) for a in non_none)
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
    """Nested models need an explicit JSON request-file/argument contract."""
    return spec.cli_request_file or not any(
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
        "annotations": spec.execution_hints.as_annotations(),
        "reproducibility": spec.reproducibility.as_manifest(),
        "surfaces": {
            "cli": spec_is_cli_safe(spec),
            "rest_path": spec.rest_path,
            "mcp_name": spec.mcp_name,
        },
        "parameters": parameters,
        "input_schema": spec.request_model.model_json_schema(),
        "cli_request_file": spec.cli_request_file,
        "output_schema": (
            spec.output_model.model_json_schema() if spec.output_model else None
        ),
    }


# ---------------------------------------------------------------------------
# REST registrar (FastAPI)
# ---------------------------------------------------------------------------

# Query-param names the REST handler injects for output shaping; a request model
# field of the same name would be routed to the body and shadow the param.
_REST_RESERVED_FIELDS = {
    "include_snapshot_text",
    "fields",
    "strict_fields",
    *ExecutionOptions.model_fields,
}


def register_rest(
    app: Any,
    specs: List[ToolSpec],
    *,
    execute_service: Callable[..., Any],
    logger: Any = None,
) -> None:
    """Mount every spec with a ``rest_path`` as a POST route on the FastAPI app."""
    from fastapi import HTTPException

    for spec in specs:
        if not spec.rest_path:
            continue
        # Guard the output-shaping query params against a request-model field of
        # the same name (which FastAPI would route to the body, making the query
        # param unsettable). MCP guards these in ``_make_mcp_fn``; REST-only tools
        # (e.g. calculate_legacy, astro_relative) never pass through that path, so
        # enforce it here too — fail loud rather than silently shadow a flag.
        _clash = _REST_RESERVED_FIELDS & set(spec.request_model.model_fields)
        if _clash:
            raise ValueError(
                f"Tool '{spec.tool_name}' request model has reserved field name(s) "
                f"{_clash}; these collide with REST output-shaping query params."
            )
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
            operation_id=spec.key,
            response_model=None,
            responses={
                **({200: {"model": spec.output_model}} if spec.output_model else {}),
                **{
                    code: {"model": ErrorEnvelope}
                    for code in (400, 401, 422, 500, 503, 504)
                },
            },
        )


def make_rest_handler(
    spec: ToolSpec,
    *,
    execute_service: Callable[..., Any],
    http_exception: Any,
    logger: Any = None,
) -> Callable[..., Any]:
    from fastapi import Query

    model = spec.request_model
    error_label = spec.rest_error_label or f"{spec.operation_label_zh}参数"
    # A bare ``List`` param without ``Query()`` is read by FastAPI as a *body*
    # field, which would force the request model to embed under ``request`` and
    # break the flat body contract. Marking both params as Query keeps the body
    # exactly as before (the flat request model) and exposes these as query
    # params (``?include_snapshot_text=false&fields=a&fields=b``).
    snapshot_t = Annotated[bool, Query(description=_SNAPSHOT_FLAG_DESC)]
    fields_t = Annotated[Optional[List[str]], Query(description=_FIELDS_FLAG_DESC)]
    strict_t = Annotated[bool, Query(description=_STRICT_FIELDS_DESC)]
    execution_annotations = {
        name: Annotated[Optional[str], Query(description=definition.description)]
        for name, definition in ExecutionOptions.model_fields.items()
    }

    # Output-shaping query params, mirroring the MCP transport flags so a REST
    # caller can trim a 50KB payload to the few fields it needs. Defaults
    # reproduce the historical full payload exactly (no snapshot dropped, no
    # projection), so existing clients and golden masters see no change.
    # ``compact`` is intentionally omitted — HTTP/JSON serialization is FastAPI's
    # job and is already unindented. ``request`` stays the only required param so
    # the backward-compatible direct-call handlers (``await calculate_x(req)``)
    # keep working.
    async def handler(
        request: Any,
        include_snapshot_text: bool = spec.include_snapshot_text,
        fields: Optional[List[str]] = None,
        strict_fields: bool = False,
        as_of: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_run_id: Optional[str] = None,
    ) -> Any:  # signature injected below
        try:
            if logger is not None:
                logger.info("Processing %s request", spec.tool_name)
            options = ExecutionOptions(
                as_of=as_of, trace_id=trace_id, parent_run_id=parent_run_id
            )
            result = await execute_service(
                execute_tool,
                spec,
                request,
                tool_name=spec.run_metadata_name,
                cpu_bound=spec.cpu_bound,
                error_is_fatal=spec.error_is_fatal,
                options=options,
            )
            # Mirror the MCP/CLI path (see _render_tool_response): only reshape
            # successful payloads so a transform keyed on a domain field can
            # never corrupt an error envelope.
            validate_output(spec, result)
            # Project AFTER run_metadata is attached (execute_service did it) so
            # provenance survives a selection; then drop snapshot_text if opted
            # out. Order matches MCP's _render_tool_response.
            if not result_is_error(spec, result):
                result = project_fields(result, fields, strict_fields=strict_fields)
            if not include_snapshot_text and "snapshot_text" in result:
                result = {k: v for k, v in result.items() if k != "snapshot_text"}
            return result
        except ValidationError as exc:
            raise http_exception(status_code=422, detail=validation_error_result(exc))
        except ParameterError as exc:
            raise http_exception(status_code=422, detail=exc.as_result())
        except ValueError:
            raise http_exception(status_code=400, detail=f"无效的{error_label}")
        except http_exception:
            raise
        except Exception as exc:  # noqa: BLE001
            if logger is not None:
                logger.error(
                    "Unexpected error during %s: %s", spec.tool_name, exc, exc_info=True
                )
            failure = handle_calculation_error(exc, spec.operation_label_zh)
            raise http_exception(status_code=failure["status_code"], detail=failure)

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
                ),
                inspect.Parameter(
                    "include_snapshot_text",
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=snapshot_t,
                    default=spec.include_snapshot_text,
                ),
                inspect.Parameter(
                    "fields",
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=fields_t,
                    default=None,
                ),
                inspect.Parameter(
                    "strict_fields",
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation=strict_t,
                    default=False,
                ),
                *[
                    inspect.Parameter(
                        name,
                        inspect.Parameter.KEYWORD_ONLY,
                        annotation=annotation,
                        default=None,
                    )
                    for name, annotation in execution_annotations.items()
                ],
            ]
        ),
    )
    handler.__annotations__ = {
        "request": model,
        "include_snapshot_text": snapshot_t,
        "fields": fields_t,
        "strict_fields": strict_t,
        **execution_annotations,
        "return": dict,
    }
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
    "无效路径默认附 projection_warnings；strict_fields=true 时拒绝。"
)
_STRICT_FIELDS_DESC = "是否拒绝无效 fields 路径；默认 false，保留兼容投影并返回警告。"


def register_mcp(
    app: Any,
    specs: List[ToolSpec],
    *,
    render_response: Callable[..., str],
    render_error: Callable[..., str],
) -> None:
    """Register every spec with an ``mcp_name`` (or key) as a FastMCP tool."""
    from fastmcp.tools import Tool
    from mcp.types import ToolAnnotations

    for spec in specs:
        if spec.mcp_name is None and spec.key is None:
            continue
        fn = _make_mcp_fn(
            spec, render_response=render_response, render_error=render_error
        )
        from fatebridge.mcp_transport import native_tool_function

        tool = Tool.from_function(
            native_tool_function(fn),
            name=spec.tool_name,
            description=spec.summary,
            annotations=ToolAnnotations.model_validate(
                spec.execution_hints.as_annotations()
            ),
            tags={spec.family},
            output_schema=(
                spec.output_model.model_json_schema() if spec.output_model else None
            ),
        )
        for name in _MCP_SOLAR_FIELDS & spec.request_model.model_fields.keys():
            field = spec.request_model.model_fields[name]
            if not field.is_required():
                # The factory is an adapter detail. Discovery describes the
                # domain default, which the request model applies after omission.
                tool.parameters["properties"][name]["default"] = field.get_default(
                    call_default_factory=True
                )
        app.add_tool(tool)
    from fatebridge.mcp_transport import InputValidationMiddleware

    app.add_middleware(InputValidationMiddleware(specs))


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
    _reserved = {
        "compact",
        "include_snapshot_text",
        "fields",
        "strict_fields",
        *ExecutionOptions.model_fields,
    }
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
    strict_t = Annotated[bool, Field(description=_STRICT_FIELDS_DESC)]
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
        "strict_fields": strict_t,
    }
    params.append(
        inspect.Parameter(
            "strict_fields",
            inspect.Parameter.KEYWORD_ONLY,
            annotation=strict_t,
            default=False,
        )
    )
    for name, definition in ExecutionOptions.model_fields.items():
        annotation = Annotated[Optional[str], Field(description=definition.description)]
        annotations[name] = annotation
        params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=annotation,
                default=None,
            )
        )

    def impl(**kwargs: Any) -> str:
        compact = kwargs.pop("compact", True)
        include_snapshot_text = kwargs.pop(
            "include_snapshot_text", spec.include_snapshot_text
        )
        fields = kwargs.pop("fields", None)
        strict_fields = kwargs.pop("strict_fields", False)
        controls = {
            name: kwargs.pop(name, None) for name in ExecutionOptions.model_fields
        }
        kwargs = {
            name: value for name, value in kwargs.items() if value is not _MCP_OMITTED
        }
        try:
            options = ExecutionOptions.model_validate(controls)
            request = model(**kwargs)
            result = execute_tool(spec, request, options=options)
        except ValidationError as exc:
            return render_error(
                correlate_error(
                    validation_error_result(exc), safe_correlation(controls)
                ),
                spec.operation_label_zh,
                compact=compact,
            )
        except ValueError:
            # Binding/domain ValueError remains a generic 400. Model validation
            # has its own sanitized 422 path above.
            return render_error(
                invalid_input_result(spec), spec.operation_label_zh, compact=compact
            )
        except Exception as exc:
            return render_error(
                handle_calculation_error(exc, spec.operation_label_zh),
                spec.operation_label_zh,
                compact=compact,
            )
        if result_is_error(spec, result):
            return render_error(result, spec.operation_label_zh, compact=compact)
        try:
            return render_response(
                result,
                compact=compact,
                include_snapshot_text=include_snapshot_text,
                fields=fields,
                strict_fields=strict_fields,
                tool_name=spec.run_metadata_name,
            )
        except ParameterError as exc:
            return render_error(
                correlate_error(exc.as_result(), options),
                spec.operation_label_zh,
                compact=compact,
            )

    impl.__name__ = spec.tool_name
    impl.__doc__ = spec.summary
    setattr(impl, "__signature__", inspect.Signature(params))
    impl.__annotations__ = {**annotations, "return": str}
    return impl
