"""
Lightweight runtime metadata helpers for REST and MCP responses.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Iterable, Optional, Set
from uuid import uuid4

DEFAULT_ENGINE = "fatebridge-offline"

_SNAPSHOT_TECHNIQUE_TOOL_NAMES = {
    "knowledge_registry": "knowledge_registry",
    "knowledge": "knowledge_read",
    "primarydirect": "pd",
    "primarydirchart": "pdchart",
    "zodialrelease": "zr",
}

_KNOWN_PAYLOAD_TOOL_KEYS = {
    "bazi_birth",
    "bazi_direct",
    "qimen",
    "taiyi",
    "jinkou",
    "solarreturn",
    "lunarreturn",
    "transit",
    "solararc",
    "givenyear",
    "profection",
    "pd",
    "pdchart",
    "zr",
    "firdaria",
    "decennials",
    "liureng",
    "runyear",
    "ziwei_birth",
    "ziwei_rules",
}

_STANDARD_RESPONSE_KEYS = {
    "analysis_type",
    "summary",
    "snapshot_text",
    "snapshot_export",
    "analysis_context",
    "natal_reference",
    "chart_profile",
    "relationship_profile",
    "run_metadata",
    "person_info",
    "personal_info",
    "compatibility",
    "detailed_analysis",
    "inner_chart",
    "outer_chart",
    "composite_chart",
    "synastry_aspects",
    "in_to_out_aspects",
    "out_to_in_aspects",
    "in_to_out_midpoint",
    "out_to_in_midpoint",
    "in_to_out_antiscia",
    "out_to_in_antiscia",
    "in_to_out_contra_antiscia",
    "out_to_in_contra_antiscia",
    "inToOutAsp",
    "outToInAsp",
    "inToOutMidpoint",
    "outToInMidpoint",
    "inToOutAnti",
    "outToInAnti",
    "inToOutCAnti",
    "outToInCAnti",
    "chart",
    "inner",
    "outer",
    "base_chart",
}

_EXPLICIT_SERVICE_NAME_MAP = {
    "calculate_destiny_analysis": "analyze_destiny",
    "calculate_compatibility_analysis": "two_person_compatibility",
    "calculate_comprehensive_timing": "timing_analysis",
    "calculate_dayun_analysis": "dayun_analysis",
    "calculate_liunian_analysis": "liunian_analysis",
    "calculate_liuyue_analysis": "liuyue_analysis",
    "calculate_liuri_analysis": "liuri_analysis",
    "calculate_liushi_analysis": "liushi_analysis",
    "calculate_jieqi_timeline_analysis": "jieqi_timeline_analysis",
    "calculate_core_chart_analysis": None,
    "calculate_relative_chart_analysis": "astro_relative_chart",
    "calculate_germany_chart_analysis": "germany",
}


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _chart_variant_tool_name(chart_variant: Optional[str]) -> Optional[str]:
    if chart_variant in {"chart", "chart13", "germany"}:
        return chart_variant
    if chart_variant == "hellen_chart":
        return "astro_hellen_chart"
    if chart_variant == "guolao_chart":
        return "astro_guolao_chart"
    if chart_variant == "india_chart":
        return "astro_india_chart"
    return None


def infer_tool_name_from_service(
    *,
    explicit_tool_name: Optional[str] = None,
    service_name: Optional[str] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> str:
    if explicit_tool_name:
        return explicit_tool_name

    kwargs = kwargs or {}

    if service_name in _EXPLICIT_SERVICE_NAME_MAP:
        mapped = _EXPLICIT_SERVICE_NAME_MAP[service_name]
        if mapped:
            return mapped
        if service_name == "calculate_core_chart_analysis":
            return _chart_variant_tool_name(kwargs.get("chart_variant")) or "astro_chart"

    if not service_name:
        return "unknown_tool"

    name = service_name
    if name.startswith("calculate_"):
        name = name[len("calculate_") :]
    if name.endswith("_service"):
        name = name[: -len("_service")]
    if name.endswith("_analysis"):
        name = name[: -len("_analysis")]

    return name or "unknown_tool"


def infer_tool_name_from_payload(payload: Dict[str, Any]) -> str:
    metadata = payload.get("run_metadata")
    if isinstance(metadata, dict):
        tool_name = metadata.get("tool_name")
        if isinstance(tool_name, str) and tool_name:
            return tool_name

    snapshot_export = payload.get("snapshot_export")
    if isinstance(snapshot_export, dict):
        technique = snapshot_export.get("technique")
        if isinstance(technique, dict):
            technique_key = technique.get("key")
            if isinstance(technique_key, str) and technique_key:
                return _SNAPSHOT_TECHNIQUE_TOOL_NAMES.get(technique_key, technique_key)

    chart_profile = payload.get("chart_profile")
    if isinstance(chart_profile, dict):
        chart_type = chart_profile.get("chart_type")
        if isinstance(chart_type, str) and chart_type:
            return _chart_variant_tool_name(chart_type) or chart_type

    if "relationship_profile" in payload:
        return "astro_relative_chart"

    for key in payload.keys():
        if key in _KNOWN_PAYLOAD_TOOL_KEYS:
            return key

    candidates = [
        key
        for key, value in payload.items()
        if key not in _STANDARD_RESPONSE_KEYS and isinstance(value, (dict, list))
    ]
    if len(candidates) == 1:
        return candidates[0]

    return "unknown_tool"


def _enqueue_children(queue: Deque[Any], values: Iterable[Any]) -> None:
    for value in values:
        if isinstance(value, (dict, list, tuple)):
            queue.append(value)


def resolve_runtime_engine(payload: Dict[str, Any]) -> str:
    queue: Deque[Any] = deque([payload])
    seen_dict_ids: Set[int] = set()

    while queue:
        current = queue.popleft()
        if isinstance(current, dict):
            current_id = id(current)
            if current_id in seen_dict_ids:
                continue
            seen_dict_ids.add(current_id)

            direct_engine = current.get("engine")
            if isinstance(direct_engine, str) and direct_engine:
                return direct_engine

            for profile_key in ("relationship_profile", "chart_profile"):
                profile = current.get(profile_key)
                if isinstance(profile, dict):
                    engine_backend = profile.get("engine_backend")
                    if isinstance(engine_backend, str) and engine_backend:
                        return engine_backend
                    engine_precision = profile.get("engine_precision")
                    if isinstance(engine_precision, str) and engine_precision:
                        return engine_precision

            _enqueue_children(queue, current.values())
            continue

        if isinstance(current, (list, tuple)):
            _enqueue_children(queue, current)

    return DEFAULT_ENGINE


def attach_run_metadata(
    payload: Dict[str, Any],
    *,
    tool_name: str,
) -> Dict[str, Any]:
    existing = payload.get("run_metadata")
    if isinstance(existing, dict):
        return payload

    run_id = uuid4().hex
    trace_id = uuid4().hex
    enriched = dict(payload)
    enriched["run_metadata"] = {
        "run_id": run_id,
        "trace_id": trace_id,
        "tool_name": tool_name,
        "generated_at": _utc_timestamp(),
        "engine": resolve_runtime_engine(payload),
    }
    return enriched
