"""Apply existing rule charts to layout objects, preserving method and scope.

This is a generic fengshui calculation, shared by doors, beds, desks and stoves.
It derives alternatives from the same charts that produced current findings.
Element cycles are calculated relationships, not an invented object cure rule.
"""

from typing import Any, Dict, List

from fatebridge.core.divination import ELEMENT_CONTROLS, ELEMENT_GENERATES

from .bazhai import placement_polarity
from .directions import rule_data
from .layout_supplements import analyze_supplements
from .models import AssessRequest


def element_relationships(element: str) -> Dict[str, str]:
    """All five directed relationships; never confuse drain with control."""
    return {
        "same_element": element,
        "generating_element": next(
            k for k, v in ELEMENT_GENERATES.items() if v == element
        ),
        "draining_element": ELEMENT_GENERATES[element],
        "controlling_element": next(
            k for k, v in ELEMENT_CONTROLS.items() if v == element
        ),
        "controlled_element": ELEMENT_CONTROLS[element],
    }


def analyze_layout(req: AssessRequest, layers: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    options: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    missing: List[str] = []
    if not req.placements and any(
        m in req.methods for m in ("bazhai", "annual_stars", "xuankong_natal")
    ):
        missing.append("placements")
    annual = layers.get("annual_stars", {})
    natal = layers.get("xuankong_natal", {})
    bazhai = layers.get("bazhai", {})
    findings_by_object: Dict[str, List[Dict[str, Any]]] = {}
    for finding in bazhai.get("placement_findings", []):
        findings_by_object.setdefault(finding["object_id"], []).append(finding)
    charts = []
    if bazhai.get("house"):
        h = bazhai["house"]
        charts.append((h["object_id"], "house", None, False, h["sectors"]))
    for person in bazhai.get("occupants", []):
        for candidate in person["candidates"]:
            charts.append(
                (
                    person["subject_id"],
                    "occupant",
                    candidate["gender_convention"],
                    person["status"] != "complete",
                    candidate["sectors"],
                )
            )
    annual_table = rule_data("annual_stars")

    def add_element(entry: Dict[str, Any], star: Dict[str, Any]) -> None:
        elements.append(
            {
                **entry,
                "star_element": star["element"],
                **element_relationships(star["element"]),
                "cycle_derivation": "fatebridge.core.divination.ELEMENT_GENERATES/ELEMENT_CONTROLS",
                "application_scope": "element_relation_only_not_object_prescription",
            }
        )

    for placement in req.placements:
        common = {
            "object_id": placement.object_id,
            "purpose": placement.purpose,
            "observation_basis": placement.observation_basis,
        }
        # A facing bearing cannot determine the object's palace around the house
        # centre. Annual/natal stars apply to location, never the facing direction.
        location = placement.location_direction
        if location is None and any(
            m in layers for m in ("bazhai", "annual_stars", "xuankong_natal")
        ):
            missing.append(f"placements.{placement.object_id}.location_direction")
        findings.extend(findings_by_object.get(placement.object_id, []))
        for aspect, direction in (
            ("location", location),
            ("facing", placement.facing_direction),
        ):
            if direction is None or "bazhai" not in layers:
                continue
            expected = placement_polarity(placement.purpose, aspect)
            scope_options = []
            confirmed_sets = []
            for subject, kind, convention, candidate_only, chart in charts:
                if kind == "occupant" and not placement.applies_to_occupant(subject):
                    continue
                directions = [
                    d for d, p in chart.items() if p["star"]["polarity"] == expected
                ]
                entry = {
                    **common,
                    "method": "bazhai",
                    "subject_id": subject,
                    "subject_kind": kind,
                    "gender_convention": convention,
                    "candidate_only": candidate_only,
                    "aspect": aspect,
                    "direction": direction,
                    "star": chart[direction]["star"],
                    "rule_id": (
                        "bazhai_sitting_v1.stove_seat_fire_mouth"
                        if placement.purpose == "stove"
                        else "bazhai_sitting_v1.placement_application"
                    ),
                    "source_ids": ["S3"],
                }
                add_element(entry, chart[direction]["star"])
                scope_options.append(
                    {
                        **entry,
                        "expected_polarity": expected,
                        "matches_convention": chart[direction]["star"]["polarity"]
                        == expected,
                        "matching_directions": directions,
                        "matching_stars": {d: chart[d]["star"] for d in directions},
                    }
                )
                if not candidate_only:
                    confirmed_sets.append(set(directions))
            intersection = (
                set.intersection(*confirmed_sets) if confirmed_sets else set()
            )
            confirmed_matches = {
                s["matches_convention"]
                for s in scope_options
                if not s["candidate_only"]
            }
            options.append(
                {
                    **common,
                    "aspect": aspect,
                    "current_direction": direction,
                    "scopes": scope_options,
                    "agreed_matching_directions": [
                        d for d in rule_data("directions") if d in intersection
                    ],
                    "resolution": (
                        "confirmed_scopes_intersection"
                        if confirmed_sets
                        else "no_confirmed_scope"
                    ),
                    "candidate_scopes_excluded_from_intersection": True,
                    "current_result": (
                        "matches_selected_conventions"
                        if confirmed_matches == {True}
                        else (
                            "opposes_selected_conventions"
                            if confirmed_matches == {False}
                            else (
                                "scope_difference"
                                if confirmed_matches == {True, False}
                                else "no_confirmed_scope"
                            )
                        )
                    ),
                    "decision_scope": "direction_relation_not_verified_relocation_feasibility",
                }
            )
        if location is None:
            continue
        if "annual_stars" in layers:
            if annual.get("palaces"):
                palace = annual["palaces"][location]
                entry = {
                    **common,
                    "method": "annual_stars",
                    "aspect": "location",
                    "direction": location,
                    "effective_year": annual["effective_year"],
                    "annual_star_number": palace["annual_star_number"],
                    "annual_star": palace["annual_star"],
                    "time_context": annual["time_context"],
                    "rule_id": palace["rule_id"],
                    "source_ids": palace["source_ids"],
                    "application_scope": "annual_palace_not_house_natal_or_facing",
                }
                findings.append(entry)
                add_element(entry, palace["annual_star"])
            else:
                missing.extend(annual["missing_inputs"])
        if "xuankong_natal" in layers:
            if not natal.get("candidates"):
                missing.extend(natal["missing_inputs"])
            for candidate in natal.get("candidates", []):
                palace = candidate["palaces"][location]
                entry = {
                    **common,
                    "method": "xuankong_natal",
                    "aspect": "location",
                    "direction": location,
                    "candidate_id": candidate["candidate_id"],
                    "candidate_only": natal["status"] != "complete",
                    "period_number": candidate["period_number"],
                    "palace": palace,
                    "rule_id": "xuankong_zhongzhou_v1.same_yuan_then_replacement",
                    "source_ids": natal["ruleset"]["source_ids"],
                    "application_scope": "natal_palace_three_roles_kept_separate",
                }
                findings.append(entry)
                for role in ("period", "mountain", "facing"):
                    number = palace[f"{role}_star_number"]
                    add_element(
                        {**entry, "star_role": role, "star_number": number},
                        annual_table[str(number)],
                    )

    environment = []
    for finding in layers.get("jinsuo", {}).get("feature_findings", []):
        environment.append(
            {
                **finding,
                "adjustment": (
                    "retain_classification"
                    if finding["finding"] == "matches_preference"
                    else (
                        "consider_matching_classification"
                        if finding["finding"] == "opposes_preference"
                        else "needs_confirmed_classification"
                    )
                ),
                "target_classification": (
                    finding["preferred_classification"]
                    if finding["finding"] != "undetermined"
                    else None
                ),
                "application_scope": "confirmed_environment_classification_not_small_object_substitution",
            }
        )
    # Completeness refers to applying selected calculations to supplied objects.
    # Missing charts and candidate charts remain missing/partial, never hidden.
    for layer in layers.values():
        missing.extend(layer["missing_inputs"])
    supplements = analyze_supplements(req, layers, elements)
    missing.extend(supplements["missing_inputs"])
    return {
        "status": (
            "partial"
            if missing or supplements["incomplete_requested_supplements"]
            else "complete"
        ),
        "calculation_scope": "selected_methods_and_authored_rules_on_supplied_objects",
        **(
            {"surface_analysis": supplements["surface_analysis"]}
            if "surface_analysis" in supplements
            else {}
        ),
        "placement_findings": findings,
        "adjustment_options": options,
        "environment_adjustments": environment,
        "element_relationships": elements,
        "form_analysis": supplements["form_analysis"],
        "element_remedies": supplements["element_remedies"],
        "annual_remedies": supplements["annual_remedies"],
        "supplemental_rulesets": supplements["supplemental_rulesets"],
        "supplement_statuses": supplements["supplement_statuses"],
        "method_disagreements": supplements["method_disagreements"],
        "missing_inputs": list(dict.fromkeys(missing)),
        "unsupported_queries": [
            "quantitative_form_distance_cutoffs",
            "complete_classical_landform_and_sha_rules",
            "specific_object_effect_magnitude_or_guarantee",
            "candidate_relocation_feasibility",
        ],
        "limitations": [
            "位置与朝向独立；没有位置就不把朝向当作落宫。",
            "各住户、宅盘、年盘、候选盘与星角色保持独立，不合并为总分。",
            "物件候选限定于明确的作者规则和目标；不量化效果、不从命卦推导喜用神，不用摆件覆盖布局问题。",
            "匹配方位是所选规则下的候选方向，不表示家具可搬或该布局现实效果已验证。",
        ],
    }
