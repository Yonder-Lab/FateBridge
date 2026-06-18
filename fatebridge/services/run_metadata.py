"""
Lightweight runtime metadata helpers for REST and MCP responses.

``tool_name`` is supplied authoritatively by the transport from the central
``ToolSpec`` (``spec.run_metadata_name``), so it is never inferred from payload
shape. This module only stamps the metadata envelope and detects the runtime
engine that produced a result.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Iterable, Set
from uuid import uuid4

DEFAULT_ENGINE = "fatebridge-offline"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
