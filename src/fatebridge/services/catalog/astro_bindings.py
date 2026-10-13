"""Astro bindings tool declarations and domain binding helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict, Tuple

from fatebridge.application.bindings import lazy_service, resolve_service

# ---------------------------------------------------------------------------
# Service callables are bound LAZILY: each name below is a proxy that imports
# its service module on first invocation. The catalog itself stays cheap to
# import (it is pure metadata), and a session only loads the engines for the
# tools it actually calls — e.g. a bazi+ziwei session never pays the ~120ms
# kerykeion import that the western modules pull in. The spec definitions below
# reference these names exactly as if they were directly imported.
# ---------------------------------------------------------------------------
calculate_core_chart_analysis = lazy_service(
    "fatebridge.services.astrology", "calculate_core_chart_analysis"
)


calculate_germany_chart_analysis = lazy_service(
    "fatebridge.services.astrology", "calculate_germany_chart_analysis"
)


calculate_relative_chart_analysis = lazy_service(
    "fatebridge.services.astrology", "calculate_relative_chart_analysis"
)


def _astro_chart_bind(
    req: Any,
) -> Tuple[Callable[..., Any], Tuple[Any, ...], Dict[str, Any]]:
    data = req.model_dump()
    variant = data.pop("chart_variant", "chart")
    if variant == "germany":
        return resolve_service(calculate_germany_chart_analysis), (), data
    return (
        resolve_service(calculate_core_chart_analysis),
        (),
        {**data, "chart_variant": variant},
    )


def _astro_relative_rest_bind(
    req: Any,
) -> Tuple[Callable[..., Any], Tuple[Any, ...], Dict[str, Any]]:
    return (
        resolve_service(calculate_relative_chart_analysis),
        (),
        {
            "inner_payload": req.inner.model_dump(),
            "outer_payload": req.outer.model_dump(),
            "relative_mode": req.relative_mode,
            "relationship_mode": req.relationship_mode,
            "relative_mode_source": req.mode_input_source,
            "hsys": req.hsys,
            "zodiacal": req.zodiacal,
            "relationship_focus": req.relationship_focus,
        },
    )


def _astro_relative_flat_bind(
    req: Any,
) -> Tuple[Callable[..., Any], Tuple[Any, ...], Dict[str, Any]]:
    d = req.model_dump()

    def party(prefix: str) -> Dict[str, Any]:
        return {
            "name": d[f"{prefix}_name"],
            "birth_year": d[f"{prefix}_birth_year"],
            "birth_month": d[f"{prefix}_birth_month"],
            "birth_day": d[f"{prefix}_birth_day"],
            "birth_hour": d[f"{prefix}_birth_hour"],
            "birth_minute": d[f"{prefix}_birth_minute"],
            "birth_timezone": d[f"{prefix}_birth_timezone"],
            "birth_longitude": d[f"{prefix}_birth_longitude"],
            "birth_latitude": d[f"{prefix}_birth_latitude"],
            "birth_place": d[f"{prefix}_birth_place"],
            "use_true_solar_time": d[f"{prefix}_use_true_solar_time"],
        }

    return (
        resolve_service(calculate_relative_chart_analysis),
        (),
        {
            "inner_payload": party("inner"),
            "outer_payload": party("outer"),
            "relative_mode": d["relative_mode"],
            "relationship_mode": d["relationship_mode"],
            "hsys": d["hsys"],
            "zodiacal": d["zodiacal"],
            "relationship_focus": d.get("relationship_focus"),
        },
    )
