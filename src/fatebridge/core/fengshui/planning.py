"""Compare independently observed proposals using the same existing rules.

This is an engineering feasibility policy, not another Feng Shui lineage.
There are no invented scores, prescription rules, or inferred floorplan facts.
"""

from typing import Any, Dict, List

from .actions import permission_state
from .bazhai import bazhai
from .layout import analyze_layout
from .models import AssessRequest


def evaluate_alternatives(req: AssessRequest, layers: Dict[str, Any]) -> Dict[str, Any]:
    constraints = {c.object_id: c for c in req.layout_constraints}
    current_placements = {p.object_id: p for p in req.placements}
    current_forms = {o.object_id: o for o in req.form_observations}
    findings: List[Dict[str, Any]] = []
    for candidate in req.layout_alternatives:
        # Never transfer old entrance/backing observations after a move or turn.
        proposed = req.model_copy(
            update={
                "placements": [candidate.placement] if candidate.placement else [],
                "form_observations": (
                    [candidate.form_observation] if candidate.form_observation else []
                ),
                "surface_layouts": [],
                "surface_constraints": [],
                "layout_alternatives": [],
                "layout_constraints": [
                    c
                    for c in req.layout_constraints
                    if c.object_id == candidate.object_id
                ],
                "element_adjustments": [],
                "annual_remedy_ruleset_id": None,
            }
        )
        candidate_layers = dict(layers)
        if "bazhai" in layers:
            candidate_layers["bazhai"] = {
                **bazhai(proposed),
                "ruleset": layers["bazhai"]["ruleset"],
            }
        layout = analyze_layout(proposed, candidate_layers)
        missing = list(layout["missing_inputs"])
        if candidate.object_id in current_forms and candidate.form_observation is None:
            missing.append(
                f"layout_alternatives.{candidate.candidate_id}.form_observation"
            )
        elif candidate.object_id in current_forms:
            before_form = current_forms[candidate.object_id]
            for field in (
                "entrance_visible",
                "entrance_direct_line",
                "solid_backing",
                "passage_direct_line",
                "exposed_beam_over_user",
                "sharp_corner_points_at_user",
                "window_position",
            ):
                if (
                    getattr(before_form, field) is not None
                    and getattr(candidate.form_observation, field) is None
                ):
                    missing.append(
                        f"layout_alternatives.{candidate.candidate_id}.form_observation.{field}"
                    )
        if (
            candidate.object_id in current_placements
            and candidate.placement is None
            and any(m in layers for m in ("bazhai", "annual_stars", "xuankong_natal"))
        ):
            missing.append(f"layout_alternatives.{candidate.candidate_id}.placement")
        elif (
            candidate.object_id in current_placements
            and candidate.placement is not None
        ):
            for aspect in ("location", "facing"):
                field = f"{aspect}_direction"
                if (
                    getattr(current_placements[candidate.object_id], field) is not None
                    and getattr(candidate.placement, field) is None
                ):
                    missing.append(
                        f"layout_alternatives.{candidate.candidate_id}.placement.{field}"
                    )
        constraint = constraints.get(candidate.object_id)
        permission = permission_state(constraint, [list(candidate.changes)])
        blocked = permission == "blocked" or candidate.physically_feasible is False
        partial = bool(missing) or layout["status"] != "complete"
        status = (
            "blocked"
            if blocked
            else (
                "candidate_only"
                if partial
                else (
                    "ready"
                    if permission == "allowed" and candidate.physically_feasible is True
                    else "conditional_option"
                )
            )
        )
        pending = []
        if not blocked:
            for field, reason in [
                ("layout_constraints", "confirm_action_permissions"),
                (
                    f"layout_alternatives.{candidate.candidate_id}.physically_feasible",
                    "confirm_proposal_space_clearance_and_operation",
                ),
            ]:
                if (field == "layout_constraints" and permission == "unknown") or (
                    field != "layout_constraints"
                    and candidate.physically_feasible is None
                ):
                    pending.append(
                        {
                            "path": field,
                            "reason": reason,
                            "object_id": candidate.object_id,
                            "action_id": candidate.candidate_id,
                            "required_for": "optional_action",
                        }
                    )
            pending.extend(
                {
                    "path": p,
                    "reason": "confirm_independent_proposal_observation",
                    "object_id": candidate.object_id,
                    "action_id": candidate.candidate_id,
                    "required_for": "optional_action",
                }
                for p in dict.fromkeys(missing)
            )
        comparisons = []
        for finding in layout["placement_findings"]:
            if finding["method"] == "bazhai":
                comparisons.append(
                    {
                        key: finding[key]
                        for key in (
                            "method",
                            "subject_id",
                            "subject_kind",
                            "gender_convention",
                            "aspect",
                            "matches_convention",
                            "candidate_only",
                            "rule_id",
                            "source_ids",
                        )
                    }
                )
        for form in layout["form_analysis"]["findings"]:
            comparisons.extend(
                {"method": "indoor_forms", **check} for check in form["checks"]
            )
        findings.append(
            {
                "candidate_id": candidate.candidate_id,
                "object_id": candidate.object_id,
                "changes": candidate.changes,
                "evidence": candidate.evidence,
                "status": status,
                "optional": True,
                "permission_status": permission,
                "physically_feasible": candidate.physically_feasible,
                "calculation_status": "partial" if partial else "complete",
                "missing_inputs": list(dict.fromkeys(missing)),
                "pending_confirmations": pending,
                "rule_comparisons": comparisons,
                "placement_findings": layout["placement_findings"],
                "form_analysis": layout["form_analysis"],
                **(
                    {"natal_interpretation": layout["natal_interpretation"]}
                    if "natal_interpretation" in layout
                    else {}
                ),
                "supplemental_rulesets": layout["supplemental_rulesets"],
                "decision_scope": "executable_proposal_not_universal_recommendation_or_effect_guarantee",
                "old_form_observations_reused": False,
            }
        )
    return {
        "policy_id": "layout_feasibility_v1",
        "findings": findings,
        "ready_candidate_ids": [
            f["candidate_id"] for f in findings if f["status"] == "ready"
        ],
        "selection_policy": "compare_rules_individually_no_weighted_score_or_automatic_winner",
        "limitations": [
            "ready只确认所选计算与动作门槛已满足，不代表候选符合所有流派或具有现实效力。",
            "候选仅来自明确提交的方案，不自动生成户型、推断可用空间或继承搬转前的形态。",
            (
                "年盘保持独立；玄空只列有限五行与当令外局条件，不合成总分或自动排名。"
                if layers.get("xuankong_natal", {}).get("interpretation") is not None
                else "年盘与玄空只列落宫关系，没有来源支持的组合判断或外局条件时不自动排名。"
            ),
        ],
    }
