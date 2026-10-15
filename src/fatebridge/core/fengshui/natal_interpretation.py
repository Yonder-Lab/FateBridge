"""Opt-in, source-bounded natal relationships and external-form conditions.

This layer consumes an already calculated chart. It never changes natal period,
selects among bearing candidates, or treats a mechanical element relationship as
a fortune verdict.
"""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from fatebridge.core.divination import ELEMENT_CONTROLS, ELEMENT_GENERATES

from .models import ExternalFormObservation, Placement, XuankongInterpretationRequest


@lru_cache(maxsize=1)
def _bundle() -> Dict[str, Any]:
    path = (
        Path(__file__).parents[2] / "data" / "fengshui" / "natal-interpretation-v1.json"
    )
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def interpretation_provenance() -> Dict[str, Any]:
    """Return this interpretation version without altering chart provenance."""
    bundle = _bundle()
    result = deepcopy(bundle["ruleset"])
    result["sources"] = [
        dict(source_id=key, **deepcopy(bundle["sources"][key]))
        for key in result["source_ids"]
    ]
    result["bundle_version"] = bundle["bundle_version"]
    return cast(Dict[str, Any], result)


def _rule(key: str) -> Dict[str, Any]:
    return cast(Dict[str, Any], deepcopy(_bundle()["rules"][key]))


def _ordered_relationship(mountain: str, facing: str) -> str:
    if mountain == facing:
        return "same_element"
    if ELEMENT_GENERATES[mountain] == facing:
        return "mountain_generates_facing"
    if ELEMENT_GENERATES[facing] == mountain:
        return "facing_generates_mountain"
    if ELEMENT_CONTROLS[mountain] == facing:
        return "mountain_controls_facing"
    return "facing_controls_mountain"


def _timeliness(number: int, current: Optional[int]) -> Dict[str, Any]:
    return {
        **_rule("current_period"),
        "star_number": number,
        "current_period_number": current,
        "status": (
            "unknown"
            if current is None
            else "current" if number == current else "not_current"
        ),
        "evidence": {
            "star_number": number,
            "explicit_current_period_number": current,
        },
        "non_current_policy": "no_inauspicious_verdict_or_future_past_subdivision",
    }


def _external_condition(
    direction: str,
    role: str,
    number: int,
    current: Optional[int],
    observation: Optional[ExternalFormObservation],
) -> Dict[str, Any]:
    field = "mountain_present" if role == "mountain" else "water_present"
    observed = getattr(observation, field) if observation is not None else None
    image = (
        observation is not None and observation.observation_basis == "image_observed"
    )
    if direction == "C":
        status = "not_applicable_center"
    elif current is None:
        status = "needs_current_period"
    elif number != current:
        status = "rule_not_covered_not_inauspicious"
    elif observed is None:
        status = "needs_confirmation"
    elif image:
        status = "candidate_only"
    else:
        status = "matches_presence_requirement" if observed else "required_form_absent"
    return {
        **_rule("current_star_external_forms"),
        "status": status,
        "direction": direction,
        "star_role": role,
        "star_number": number,
        "criterion": field,
        "observed": observed,
        "candidate_only": image and direction != "C",
        "observation_basis": (
            observation.observation_basis if observation is not None else None
        ),
        "evidence": observation.evidence if observation is not None else None,
        "condition_match": (
            observed
            if status in {"matches_presence_requirement", "required_form_absent"}
            else None
        ),
        "verdict_scope": "presence_condition_only_no_quality_distance_or_overall_verdict",
    }


def _placement_finding(
    placement: Placement,
    palaces: Dict[str, Any],
    candidate_id: str,
    ambiguous: bool,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        **_rule("placement_role"),
        "object_id": placement.object_id,
        "purpose": placement.purpose,
        "candidate_id": candidate_id,
        "candidate_only": ambiguous,
        "location_direction": placement.location_direction,
        "facing_direction": placement.facing_direction,
        "evidence": placement.model_dump(mode="json"),
        "application_scope": "confirmed_location_role_only_no_relocation_or_merged_verdict",
    }
    if placement.purpose not in {"bed", "door"}:
        return {
            **result,
            "status": "unsupported",
            "reason": "selected_rules_do_not_cover_desk_or_stove",
        }
    role = "mountain" if placement.purpose == "bed" else "facing"
    result["selected_star_role"] = role
    if placement.location_direction is None:
        return {
            **result,
            "status": "needs_location",
            "reason": "facing_does_not_establish_house_centred_location",
        }
    palace = palaces[placement.location_direction]
    timeliness = palace["timeliness"][role]
    external = palace["external_form_analysis"][
        "mountain" if role == "mountain" else "water"
    ]
    status = external["status"]
    if status in {"matches_presence_requirement", "required_form_absent"}:
        status = "candidate_only" if ambiguous else "conditional_role_assessment"
    return {
        **result,
        "status": status,
        "candidate_only": ambiguous or external["candidate_only"],
        "selected_star_number": palace[f"{role}_star_number"],
        "timeliness": deepcopy(timeliness),
        "external_form_condition": deepcopy(external),
        "ordered_pair": deepcopy(palace["ordered_pair"]),
        "condition_match": external["condition_match"] if not ambiguous else None,
        "overall_auspiciousness": "not_produced",
    }


def analyze_natal_interpretation(
    config: XuankongInterpretationRequest,
    natal: Dict[str, Any],
    placements: List[Placement],
) -> Dict[str, Any]:
    """Evaluate each possible chart independently using only explicit facts."""
    current = config.current_period_number
    observations = {
        observation.direction: observation for observation in config.external_forms
    }
    charts = natal.get("candidates", [])
    if not charts and natal.get("chart") is not None:
        charts = [natal["chart"]]
    ambiguous = len(charts) > 1
    missing: List[str] = []
    if current is None:
        missing.append("interpretation.current_period_number")
    if not charts:
        missing.extend(
            natal.get("missing_inputs", []) or ["xuankong_natal.computed_chart"]
        )
    elif ambiguous:
        missing.append("xuankong_natal.unambiguous_bearing")
    candidates: List[Dict[str, Any]] = []
    trace: List[Dict[str, Any]] = []
    unsupported: List[Dict[str, Any]] = []
    elements = _bundle()["star_elements"]
    for chart in charts:
        candidate_id = chart["candidate_id"]
        palaces: Dict[str, Any] = {}
        for direction, palace in chart["palaces"].items():
            mountain = palace["mountain_star_number"]
            facing = palace["facing_star_number"]
            mountain_element = elements[str(mountain)]
            facing_element = elements[str(facing)]
            pair = {
                **_rule("ordered_pair"),
                "mountain_star_number": mountain,
                "facing_star_number": facing,
                "mountain_element": mountain_element,
                "facing_element": facing_element,
                "relationship": _ordered_relationship(mountain_element, facing_element),
                "evidence": {
                    "mountain_star_number": mountain,
                    "facing_star_number": facing,
                },
                "verdict_scope": "directed_element_relationship_only_no_81_pair_fortune_judgment",
            }
            external = {
                key: _external_condition(
                    direction, role, number, current, observations.get(direction)
                )
                for key, role, number in (
                    ("mountain", "mountain", mountain),
                    ("water", "facing", facing),
                )
            }
            for condition in external.values():
                path = f"interpretation.external_forms.{direction}"
                if condition["status"] == "needs_confirmation":
                    missing.append(f"{path}.{condition['criterion']}")
                elif condition["status"] == "candidate_only":
                    missing.append(f"{path}.user_or_measurement_confirmation")
            palaces[direction] = {
                "direction": direction,
                "period_star_number": palace["period_star_number"],
                "mountain_star_number": mountain,
                "facing_star_number": facing,
                "ordered_pair": pair,
                "timeliness": {
                    "mountain": _timeliness(mountain, current),
                    "facing": _timeliness(facing, current),
                },
                "external_form_analysis": external,
            }
            trace.append(
                {
                    **_rule("ordered_pair"),
                    "candidate_id": candidate_id,
                    "direction": direction,
                    "evidence": pair["evidence"],
                    "related_rule_ids": [
                        _rule(key)["rule_id"]
                        for key in (
                            "star_elements",
                            "current_period",
                            "current_star_external_forms",
                        )
                    ],
                }
            )
        findings = [
            _placement_finding(placement, palaces, candidate_id, ambiguous)
            for placement in placements
        ]
        for finding in findings:
            if finding["status"] == "needs_location":
                missing.append(f"placements.{finding['object_id']}.location_direction")
            elif finding["status"] == "unsupported":
                unsupported.append(
                    {
                        "object_id": finding["object_id"],
                        "purpose": finding["purpose"],
                        "reason": finding["reason"],
                    }
                )
            trace.append(
                {
                    **_rule("placement_role"),
                    "candidate_id": candidate_id,
                    "object_id": finding["object_id"],
                    "evidence": finding["evidence"],
                    "status": finding["status"],
                }
            )
        candidates.append(
            {
                "candidate_id": candidate_id,
                "candidate_only": ambiguous,
                "natal_period_number": chart["period_number"],
                "palaces": palaces,
                "placement_findings": findings,
            }
        )
    missing = list(dict.fromkeys(missing))
    unique_unsupported = {
        (item["object_id"], item["purpose"]): item for item in unsupported
    }
    return {
        "status": "partial" if missing or not charts else "complete",
        "rule_coverage_status": "limited",
        "ruleset_id": config.ruleset_id,
        "current_period_context": {
            "number": current,
            "evidence": config.period_evidence,
            "source": "explicit_caller_input",
            "natal_period_independent": True,
            **_rule("current_period"),
        },
        "candidates": candidates,
        "missing_inputs": missing,
        "unsupported_queries": list(unique_unsupported.values()),
        "rule_trace": trace,
        "limitations": deepcopy(_bundle()["limitations"]),
        "overall_auspiciousness": "not_produced",
    }
