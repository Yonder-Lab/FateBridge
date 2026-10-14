"""Composition only: preserve method, person, observation and time scopes."""

from itertools import combinations
from typing import Any, Dict, List

from fatebridge.core.fengshui.annual import annual_stars
from fatebridge.core.fengshui.bazhai import bazhai, minggua
from fatebridge.core.fengshui.directions import bearing_context, provenance, rule_data
from fatebridge.core.fengshui.jinsuo import jinsuo
from fatebridge.core.fengshui.layout import analyze_layout
from fatebridge.core.fengshui.models import (
    AnnualRequest,
    AssessRequest,
    BazhaiRequest,
    DirectionsRequest,
    JinsuoRequest,
    MingguaRequest,
    XuankongRequest,
)
from fatebridge.core.fengshui.snapshot import sections
from fatebridge.core.fengshui.xuankong import natal_provenance, xuankong_natal
from fatebridge.services.snapshot_builders import (
    build_snapshot_export,
    render_snapshot_lines,
)


def _layer(result: Dict[str, Any], ruleset_id: str) -> Dict[str, Any]:
    return {**result, "ruleset": provenance(ruleset_id)}


def _compose(
    layers: Dict[str, Any],
    conflicts: List[Dict[str, Any]],
    layout: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    missing = [m for layer in layers.values() for m in layer["missing_inputs"]]
    status = "partial" if missing else "complete"
    summary = "；".join(f"{name}: {layer['status']}" for name, layer in layers.items())
    natal_selected = "xuankong_natal" in layers
    result: Dict[str, Any] = {
        "analysis_type": "家居风水分层计算" if natal_selected else "家居风水基础计算",
        "engine": (
            "fatebridge-fengshui-natal-v1"
            if natal_selected
            else "fatebridge-fengshui-foundation-v1"
        ),
        "status": status,
        "layers": layers,
        "rulesets": [layer["ruleset"] for layer in layers.values()],
        "coverage": {
            "implemented_layers": list(layers),
            "missing_inputs": missing,
            "unavailable_layers": [
                n for n in rule_data("unavailable_layers") if n != "xuankong_natal"
            ],
            "not_requested_layers": [
                n
                for n in ("bazhai", "jinsuo", "annual_stars", "xuankong_natal")
                if n not in layers
            ],
        },
        "conflicts": conflicts,
        "rule_trace": [
            {
                "method": name,
                "ruleset_id": layer["ruleset"]["ruleset_id"],
                "version": layer["ruleset"]["version"],
                "source_ids": layer["ruleset"]["source_ids"],
                "scope": layer["ruleset"]["scope"],
            }
            for name, layer in layers.items()
        ],
        "summary": summary,
    }
    if layout is not None:
        result["layout_analysis"] = layout
        # Top-level status retains the raw-chart contract. Requested layout
        # readiness is separate and must survive a coverage-only projection.
        result["coverage"].update(
            layout_status=layout["status"],
            layout_missing_inputs=layout["missing_inputs"],
            requested_analysis_status=(
                "partial"
                if status == "partial" or layout["status"] == "partial"
                else "complete"
            ),
        )
        result["summary"] = (
            f"{summary}；layout: {layout['status']}"
            if layers
            else f"layout: {layout['status']}"
        )
        extra_rules = layout["supplemental_rulesets"]
        if extra_rules:
            result["rulesets"].extend(extra_rules)
            result["coverage"]["supplemental_rulesets"] = [
                r["ruleset_id"] for r in extra_rules
            ]
            result["rule_trace"].extend(
                {
                    "method": r["method"],
                    "ruleset_id": r["ruleset_id"],
                    "version": r["version"],
                    "source_ids": r["source_ids"],
                    "scope": r["scope"],
                }
                for r in extra_rules
            )
        if not layers:
            result["status"] = layout["status"]
            result["summary"] = f"layout: {layout['status']}"
            result["coverage"]["missing_inputs"] = layout["missing_inputs"]
    snapshot_sections = sections(result)
    result["snapshot_text"] = render_snapshot_lines(snapshot_sections)
    result["snapshot_export"] = build_snapshot_export(
        technique="fengshui",
        snapshot_text=result["snapshot_text"],
        selected_sections=[title for title, _ in snapshot_sections],
    )
    return result


def calculate_directions(**kwargs: Any) -> Dict[str, Any]:
    req = DirectionsRequest.model_validate(kwargs)
    bearing = None
    if req.bearing_degrees is not None:
        assert req.north_reference is not None
        bearing = bearing_context(req.bearing_degrees, req.north_reference)
    result = {
        "status": "complete",
        "directions": rule_data("directions"),
        "missing_inputs": [],
        "bearing": bearing,
        "division_scope": "confirmed_angular_sectors_no_automatic_geometry",
    }
    return _compose({"directions": _layer(result, req.ruleset_id)}, [])


def calculate_minggua(**kwargs: Any) -> Dict[str, Any]:
    req = MingguaRequest.model_validate(kwargs)
    return _compose({"minggua": _layer(minggua(req), req.ruleset_id)}, [])


def calculate_bazhai(**kwargs: Any) -> Dict[str, Any]:
    req = BazhaiRequest.model_validate(kwargs)
    layer = _layer(bazhai(req), req.ruleset_id)
    return _compose({"bazhai": layer}, _differences({"bazhai": layer}))


def calculate_jinsuo(**kwargs: Any) -> Dict[str, Any]:
    req = JinsuoRequest.model_validate(kwargs)
    return _compose({"jinsuo": _layer(jinsuo(req), req.ruleset_id)}, [])


def calculate_annual_stars(**kwargs: Any) -> Dict[str, Any]:
    req = AnnualRequest.model_validate(kwargs)
    return _compose({"annual_stars": _layer(annual_stars(req), req.ruleset_id)}, [])


def _natal_layer(req: XuankongRequest) -> Dict[str, Any]:
    return {**xuankong_natal(req), "ruleset": natal_provenance()}


def calculate_xuankong_natal(**kwargs: Any) -> Dict[str, Any]:
    req = XuankongRequest.model_validate(kwargs)
    return _compose({"xuankong_natal": _natal_layer(req)}, [])


def _differences(layers: Dict[str, Any]) -> List[Dict[str, Any]]:
    differences: List[Dict[str, Any]] = []
    bazhai_layer = layers.get("bazhai", {})
    charts = []
    if bazhai_layer.get("house"):
        house = bazhai_layer["house"]
        charts.append((house["object_id"], "house", house["sectors"]))
    for occupant in bazhai_layer.get("occupants", []):
        # Unknown birth convention produces alternatives, never a confirmed
        # conflict between imaginary residents.
        if occupant["status"] == "complete":
            charts.append(
                (
                    occupant["subject_id"],
                    "occupant",
                    occupant["candidates"][0]["sectors"],
                )
            )
    for a, b in combinations(charts, 2):
        for direction in rule_data("directions"):
            first, second = a[2][direction]["star"], b[2][direction]["star"]
            if first["polarity"] != second["polarity"]:
                differences.append(
                    {
                        "kind": (
                            "personal_direction_difference"
                            if a[1] == b[1] == "occupant"
                            else "house_person_scope_difference"
                        ),
                        "direction": direction,
                        "entries": [
                            {
                                "subject_id": c[0],
                                "subject_kind": c[1],
                                "star": c[2][direction]["star"],
                            }
                            for c in (a, b)
                        ],
                        "resolution": "keep_each_subject_result_no_household_override",
                        "rule_id": "bazhai_sitting_v1.dayounian_xor",
                        "source_ids": ["S3"],
                    }
                )
    if (
        all(name in layers for name in ("bazhai", "jinsuo", "annual_stars"))
        and bazhai_layer.get("house")
        and layers["annual_stars"].get("palaces")
    ):
        for direction in rule_data("directions"):
            differences.append(
                {
                    "kind": "distinct_scope_overlay",
                    "direction": direction,
                    "bazhai_house_star": bazhai_layer["house"]["sectors"][direction][
                        "star"
                    ],
                    "jinsuo_preference": layers["jinsuo"]["preferences"][direction][
                        "preferred_classification"
                    ],
                    "annual_star_number": layers["annual_stars"]["palaces"][direction][
                        "annual_star_number"
                    ],
                    "resolution": "different_conditions_and_time_scopes_no_combined_score",
                    "rule_ids": [
                        "bazhai_sitting_v1.dayounian_xor",
                        "jinsuo_basic_fixed_v1.palace_preference",
                        "annual_zibai_lichun_v1.forward_flight",
                    ],
                    "source_ids": ["S3", "S4", "S5"],
                }
            )
    return differences


def assess(**kwargs: Any) -> Dict[str, Any]:
    req = AssessRequest.model_validate(kwargs)
    layers = {}
    if "bazhai" in req.methods:
        layers["bazhai"] = _layer(bazhai(req), req.ruleset_id)
    if "jinsuo" in req.methods:
        layers["jinsuo"] = _layer(
            jinsuo(
                JinsuoRequest(features=req.features, ruleset_id=req.jinsuo_ruleset_id)
            ),
            req.jinsuo_ruleset_id,
        )
    if "annual_stars" in req.methods:
        layers["annual_stars"] = _layer(
            annual_stars(
                AnnualRequest(
                    effective_year=req.effective_year,
                    query_at=req.query_at,
                    timezone_name=req.timezone_name,
                    ruleset_id=req.annual_ruleset_id,
                )
            ),
            req.annual_ruleset_id,
        )
    if "xuankong_natal" in req.methods:
        natal = req.xuankong or XuankongRequest()
        natal = XuankongRequest.model_validate(
            {**natal.model_dump(), "house": natal.house or req.house}
        )
        layers["xuankong_natal"] = _natal_layer(natal)
    return _compose(
        layers,
        _differences(layers),
        (
            analyze_layout(req, layers)
            if req.analyze_layout
            or req.form_observations
            or req.element_adjustments
            or req.annual_remedy_ruleset_id is not None
            else None
        ),
    )
