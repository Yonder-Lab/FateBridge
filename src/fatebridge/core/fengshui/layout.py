"""Apply existing rule charts to layout objects, preserving method and scope.

This is a generic fengshui calculation, shared by doors, beds, desks and stoves.
It derives alternatives from the same charts that produced current findings.
Element cycles are calculated relationships, not an invented object cure rule.
"""

from typing import Any, Dict, List

from fatebridge.core.divination import ELEMENT_CONTROLS, ELEMENT_GENERATES

from .actions import FORM_ACTION_ROUTES, apply_permission
from .bazhai import placement_polarity
from .directions import rule_data
from .layout_supplements import analyze_supplements
from .models import AssessRequest
from .natal_interpretation import analyze_natal_interpretation
from .surface import summarize_analysis_progress


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


def _summarize_layout_progress(
    req: AssessRequest,
    missing: List[str],
    options: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
    environment: List[Dict[str, Any]],
    supplements: Dict[str, Any],
    natal_interpretation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Summarize reviewed records separately from optional physical actions."""
    progress_counts = dict(supported=0, confirmed_unsupported=0, unknown=0)
    progress_actions: List[Dict[str, Any]] = []
    progress_pending: List[Dict[str, Any]] = []
    constraints = {c.object_id: c for c in req.layout_constraints}
    surface = supplements.get("surface_analysis")
    if surface is not None:
        # A desk-wide prohibition also covers optional desktop additions.
        for finding in surface["findings"]:
            for action in finding["action_options"]:
                if action["action"] == "consider_representation":
                    apply_permission(
                        action,
                        constraints.get(finding["object_id"]),
                        [["add_items"]],
                        status_key="status",
                    )
        if req.layout_constraints:
            surface["analysis_progress"] = summarize_analysis_progress(
                surface["missing_inputs"],
                surface["analysis_progress"]["rule_coverage_counts"],
                [a for f in surface["findings"] for a in f["action_options"]],
                [
                    p
                    for f in surface["findings"]
                    for a in f["action_options"]
                    for p in a["pending_confirmations"]
                ]
                + [
                    p
                    for p in surface["analysis_progress"]["pending_confirmations"]
                    if p["required_for"] == "assessment"
                ],
                count_unit="surface_items",
            )
        surface_progress = surface["analysis_progress"]
        progress_counts.update(surface_progress["rule_coverage_counts"])
        progress_pending.extend(surface_progress["pending_confirmations"])
        progress_actions.extend(
            action
            for finding in surface["findings"]
            for action in finding["action_options"]
        )
    for option in options:
        # Direction relations have no relocation/rotation feasibility contract;
        # a matching direction never certifies a physically executable move.
        action_status = (
            "no_action_needed"
            if option["current_result"] == "matches_selected_conventions"
            else (
                "candidate_only"
                if option["resolution"] == "no_confirmed_scope"
                else "conditional_option"
            )
        )
        action_id = f"direction:{option['object_id']}:{option['aspect']}"
        action_pending = (
            []
            if action_status == "no_action_needed"
            else [
                {
                    "path": f"layout_analysis.adjustment_options.{option['object_id']}.{option['aspect']}",
                    "reason": "relocation_feasibility_not_in_current_contract",
                    "object_id": option["object_id"],
                    "action_id": action_id,
                    "required_for": "optional_action",
                }
            ]
        )
        option.update(
            action_id=action_id,
            action_status=action_status,
            optional=True,
            pending_confirmations=action_pending,
        )
        if action_status != "no_action_needed":
            apply_permission(
                option, constraints.get(option["object_id"]), [[option["aspect"]]]
            )
        progress_actions.append({"status": option["action_status"], "optional": True})
        progress_pending.extend(option["pending_confirmations"])
        for scope in option["scopes"]:
            progress_counts["unknown" if scope["candidate_only"] else "supported"] += 1
    for finding in supplements["form_analysis"]["findings"]:
        for check in finding["checks"]:
            progress_counts[
                (
                    "unknown"
                    if check["candidate_only"] or check["finding"] == "undetermined"
                    else "supported"
                )
            ] += 1
            if check["adjustment"] is not None:
                action_id = f"form:{finding['object_id']}:{check['criterion']}"
                action_pending = [
                    {
                        "path": f"layout_analysis.form_analysis.{finding['object_id']}.{check['criterion']}",
                        "reason": "verify_form_adjustment_feasibility",
                        "object_id": finding["object_id"],
                        "action_id": action_id,
                        "required_for": "optional_action",
                    }
                ]
                action_status = (
                    "candidate_only"
                    if check["candidate_only"]
                    else "conditional_option"
                )
                check.update(
                    action_id=action_id,
                    action_status=action_status,
                    optional=True,
                    pending_confirmations=action_pending,
                )
                routes = FORM_ACTION_ROUTES.get(check["criterion"])
                if routes:
                    apply_permission(
                        check, constraints.get(finding["object_id"]), routes
                    )
                progress_actions.append(
                    {"status": check["action_status"], "optional": True}
                )
                progress_pending.extend(check["pending_confirmations"])
        for action in finding["object_options"]:
            apply_permission(
                action,
                constraints.get(finding["object_id"]),
                [["add_items"]],
                status_key="status",
            )
        progress_actions.extend(finding["object_options"])
        progress_pending.extend(
            p
            for action in finding["object_options"]
            for p in action["pending_confirmations"]
        )
    for finding in findings:
        if finding.get("method") in {"annual_stars", "xuankong_natal"}:
            progress_counts[
                "unknown" if finding.get("candidate_only") else "supported"
            ] += 1
    for adjustment in environment:
        state = adjustment["adjustment"]
        progress_counts[
            "unknown" if state == "needs_confirmed_classification" else "supported"
        ] += 1
        if state != "retain_classification":
            action_status = (
                "candidate_only"
                if state == "needs_confirmed_classification"
                else "conditional_option"
            )
            action_id = f"environment:{adjustment['object_id']}"
            action_pending = [
                {
                    "path": f"features.{adjustment['object_id']}.classification",
                    "reason": (
                        "confirm_environment_classification"
                        if state == "needs_confirmed_classification"
                        else "verify_environment_adjustment_feasibility"
                    ),
                    "object_id": adjustment["object_id"],
                    "action_id": action_id,
                    "required_for": (
                        "assessment"
                        if state == "needs_confirmed_classification"
                        else "optional_action"
                    ),
                }
            ]
            adjustment.update(
                action_id=action_id,
                action_status=action_status,
                optional=True,
                pending_confirmations=action_pending,
            )
            progress_actions.append({"status": action_status, "optional": True})
            progress_pending.extend(action_pending)
    limited = supplements["annual_remedies"]["status"] == "unsupported_year"
    if natal_interpretation is not None:
        limited = limited or natal_interpretation["rule_coverage_status"] == "limited"
        # Count interpretation checks separately from merely looking up the
        # natal numbers. Uncovered uses cannot become supported by that lookup.
        for candidate in natal_interpretation["candidates"]:
            for finding in candidate["placement_findings"]:
                state = finding["status"]
                progress_counts[
                    (
                        "confirmed_unsupported"
                        if state in {"unsupported", "rule_not_covered_not_inauspicious"}
                        else (
                            "unknown"
                            if state
                            in {
                                "needs_location",
                                "needs_current_period",
                                "needs_confirmation",
                                "candidate_only",
                            }
                            else "supported"
                        )
                    )
                ] += 1
    remedies = [
        ("layout_analysis.element_remedies", remedy)
        for remedy in supplements["element_remedies"]
    ] + [
        ("layout_analysis.annual_remedies.findings", remedy)
        for remedy in supplements["annual_remedies"]["findings"]
    ]
    for branch, remedy in remedies:
        state = remedy["status"]
        if state in {"unsupported_application", "no_registered_prescription"}:
            progress_counts["confirmed_unsupported"] += 1
            limited = True
        elif state in {"needs_computed_target", "needs_location", "candidate_only"}:
            progress_counts["unknown"] += 1
        else:
            progress_counts["supported"] += 1
        if state in {
            "conditional_options",
            "conditional_author_rule",
            "candidate_only",
        }:
            target_id = remedy.get("request_id", remedy["object_id"])
            action_id = f"{branch}:{target_id}"
            action_pending = [
                {
                    "path": f"{branch}.{target_id}",
                    "reason": "verify_authored_representation_conditions",
                    "object_id": remedy["object_id"],
                    "action_id": action_id,
                    "required_for": "optional_action",
                }
            ]
            remedy.update(
                action_id=action_id, optional=True, pending_confirmations=action_pending
            )
            remedy["action_status"] = (
                "candidate_only" if state == "candidate_only" else "conditional_option"
            )
            apply_permission(
                remedy, constraints.get(remedy["object_id"]), [["add_items"]]
            )
            progress_actions.append(
                {
                    "status": remedy["action_status"],
                    "optional": True,
                }
            )
            progress_pending.extend(remedy["pending_confirmations"])
    surface_missing = set(surface["missing_inputs"]) if surface is not None else set()
    pending_paths = {p["path"] for p in progress_pending}
    for path in dict.fromkeys(missing):
        if path not in surface_missing and path not in pending_paths:
            progress_pending.append(
                {
                    "path": path,
                    "reason": "missing_calculation_input",
                    "required_for": "assessment",
                }
            )
    return summarize_analysis_progress(
        missing,
        progress_counts,
        progress_actions,
        progress_pending,
        count_unit="surface_items_and_layout_checks",
        limited=limited,
    )


def analyze_layout(req: AssessRequest, layers: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    options: List[Dict[str, Any]] = []
    elements: List[Dict[str, Any]] = []
    missing: List[str] = []
    if not layers and not req.form_observations and not req.surface_layouts:
        missing.append("form_observations_or_surface_layouts_or_selected_methods")
    if not req.placements and any(
        m in req.selected_methods for m in ("bazhai", "annual_stars", "xuankong_natal")
    ):
        missing.append("placements")
    annual = layers.get("annual_stars", {})
    natal = layers.get("xuankong_natal", {})
    natal_interpretation = None
    if natal and req.xuankong is not None and req.xuankong.interpretation is not None:
        # Re-evaluate uses at the proposal's actual location. External forms are
        # house-centred sectors and stay fixed when a piece of furniture moves.
        natal_interpretation = analyze_natal_interpretation(
            req.xuankong.interpretation, natal, req.placements
        )
        missing.extend(natal_interpretation["missing_inputs"])
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
    progress = _summarize_layout_progress(
        req, missing, options, findings, environment, supplements, natal_interpretation
    )
    return {
        "status": (
            "partial"
            if missing or supplements["incomplete_requested_supplements"]
            else "complete"
        ),
        "calculation_scope": "selected_methods_and_authored_rules_on_supplied_objects",
        "analysis_progress": progress,
        **(
            {"natal_interpretation": natal_interpretation}
            if natal_interpretation is not None
            else {}
        ),
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
            "automatic_candidate_relocation_feasibility",
            "automatic_floorplan_geometry_and_external_landform_analysis",
            "yangzhai_sanyao_structural_rules",
            "sanhe_water_formulas_and_xuankong_dagua",
            "complete_natal_combination_interpretation_and_external_activation",
        ],
        "limitations": [
            "位置与朝向独立；没有位置就不把朝向当作落宫。",
            "各住户、宅盘、年盘、候选盘与星角色保持独立，不合并为总分。",
            "物件候选限定于明确的作者规则和目标；不量化效果、不从命卦推导喜用神，不用摆件覆盖布局问题。",
            "匹配方位是所选规则下的候选方向，不表示家具可搬或该布局现实效果已验证。",
        ],
    }
