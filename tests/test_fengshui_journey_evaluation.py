"""Fault injection: adversarial evidence must not improve the Harness verdict."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "fengshui_journey_evaluator",
    Path(__file__).resolve().parents[1] / "scripts/evaluate_fengshui_journeys.py",
)
evaluator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluator)

VALID_ARGUMENTS = {
    "analyze_layout": True,
    "methods": ["bazhai"],
    "occupants": [
        {"subject_id": "user", "birth_date": "2000-12-10", "gender_convention": "male"}
    ],
    "placements": [
        {
            "object_id": "desk",
            "purpose": "desk",
            "subject_id": "user",
            "facing_direction": "W",
            "facing_role": "desk_facing",
        }
    ],
}
CONTRACT = {
    "require_assess": True,
    "allowed_tools": ["fengshui_assess", "read_mcp_resource"],
    "required_arguments": {
        "analyze_layout": True,
        "methods": ["bazhai"],
        "occupants.0.birth_date": "2000-12-10",
        "occupants.0.gender_convention": "male",
        "placements.0.purpose": "desk",
        "placements.0.facing_direction": "W",
        "placements.0.facing_role": "desk_facing",
    },
    "forbidden_argument_paths": ["placements.0.location_direction", "house"],
    "allowed_argument_paths": [
        "occupants.0.subject_id",
        "placements.0.object_id",
        "placements.0.subject_id",
        "fields",
        "strict_fields",
        "include_snapshot_text",
        "compact",
        "trace_id",
        "parent_run_id",
    ],
    "argument_array_counts": {
        "occupants": 1,
        "placements": 1,
        "form_observations": 0,
        "features": 0,
        "element_adjustments": 0,
    },
}


@pytest.fixture(scope="module")
def business_result():
    """Use a real shared execution receipt; do not invent a success-shaped result."""
    from fatebridge.application.execution import execute_tool

    shared = evaluator.shared_specs()["fengshui_assess"]
    request = shared.request_model.model_validate(VALID_ARGUMENTS)
    return execute_tool(shared, request)


def turn(business_result, arguments=None, text=""):
    items = [{"type": "agentMessage", "text": text}]
    if arguments is not None:
        items.append(
            {
                "id": "call",
                "type": "mcpToolCall",
                "server": "fatebridge",
                "tool": "fengshui_assess",
                "status": "completed",
                "arguments": copy.deepcopy(arguments),
                "result": {"structuredContent": copy.deepcopy(business_result)},
            }
        )
    return {"status": "completed", "items": items}


def valid_turn(business_result):
    return turn(business_result, VALID_ARGUMENTS)


def test_disclaimers_and_rule_keywords_without_call_cannot_pass(business_result):
    result = evaluator.audit_turn(
        turn(
            business_result, text="partial 不保证成功 方位 朝向 保留分歧 complete 依据"
        ),
        CONTRACT,
    )
    assert result["call_evidence_status"] == "insufficient_evidence"
    assert result["human_review"]["status"] == "pending"


@pytest.mark.parametrize("wrong", ["E", None])
def test_correction_cannot_reuse_stale_or_unknown_direction(business_result, wrong):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["placements"][0]["facing_direction"] = wrong
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


def test_correct_answer_does_not_hide_invented_house_or_location(business_result):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["house"] = None
    current["items"][-1]["arguments"]["placements"][0]["location_direction"] = "W"
    current["items"][0]["text"] = "位置未知，只算朝向"
    result = evaluator.audit_turn(current, CONTRACT)
    assert "unconfirmed_fact_supplied:house" in result["failures"]
    assert (
        "unconfirmed_fact_supplied:placements.0.location_direction"
        in result["failures"]
    )


@pytest.mark.parametrize(
    "arguments", [{}, {"analyze_layout": 1}, {"analyze_layout": None}]
)
def test_missing_required_null_and_boolean_integer_are_distinct(
    business_result, arguments
):
    assert (
        evaluator.audit_turn(turn(business_result, arguments), CONTRACT)[
            "call_evidence_status"
        ]
        == "fail"
    )


def test_valid_call_and_receipt_still_require_independent_answer_review(
    business_result,
):
    result = evaluator.audit_turn(valid_turn(business_result), CONTRACT)
    assert result["call_evidence_status"] == "pass", result
    assert (
        result["assessment_calls"][0]["receipt_input_binding"]
        == "verified_current_request_model"
    )
    assert (
        result["assessment_calls"][0]["receipt_business_binding"]
        == "verified_full_payload"
    )
    assert result["consultation_success"] == "not_established_by_call_checks"


def test_all_calls_checked_so_later_recovery_cannot_hide_stale_call(business_result):
    current = valid_turn(business_result)
    old = valid_turn(business_result)
    old["items"][-1]["arguments"]["placements"][0]["facing_direction"] = "E"
    current["items"].extend(old["items"])
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


@pytest.mark.parametrize("turn_count", [0, 2])
def test_incomplete_or_uncontracted_journeys_do_not_pass(business_result, turn_count):
    record = {"case": "a", "turns": [turn(business_result)] * turn_count}
    assert evaluator.audit(record, {"turns": [CONTRACT]})["status"] == "fail"


def test_opaque_code_mode_identifiers_do_not_prove_arguments():
    result = evaluator.audit_turn(
        {
            "status": "completed",
            "items": [],
            "stages": {"tool_identifiers": ["mcp__fatebridge__fengshui_assess"]},
        },
        CONTRACT,
    )
    assert result["call_evidence_status"] == "insufficient_evidence"


@pytest.mark.parametrize(
    "result",
    [{"isError": True}, {"structuredContent": {"error_code": "validation_error"}}],
)
def test_completed_transport_does_not_hide_business_failure(business_result, result):
    current = valid_turn(business_result)
    current["items"][-1]["result"] = result
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


def test_wrong_case_contract_cannot_be_used_to_pass_another_journey(business_result):
    record = {"case": "a", "turns": [turn(business_result)]}
    assert evaluator.audit(record, {"case": "b", "turns": [{}]})["status"] == "fail"


def test_bundle_never_substitutes_another_cases_contract(business_result):
    record = {"case": "a", "turns": [turn(business_result)]}
    assert (
        evaluator.audit(record, {"turn_expectations": {"b": [{}]}})["status"] == "fail"
    )


def test_unchanged_explanation_cannot_hide_unneeded_assessment(business_result):
    result = evaluator.audit_turn(
        valid_turn(business_result), {"forbid_assess": True, "allowed_tools": []}
    )
    assert result["call_evidence_status"] == "fail"


# Four independently reproduced loopholes: none may pass after these changes.
def test_correct_arguments_without_result_are_insufficient(business_result):
    current = valid_turn(business_result)
    del current["items"][-1]["result"]
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "insufficient_evidence"
    assert "business_result_not_observed" in result["unavailable_evidence"]


def test_invented_schema_argument_is_rejected(business_result):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["invented_argument"] = "secret"
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "fail"
    assert result["assessment_calls"][0]["parameter_validation_errors"]


def test_later_invented_array_member_cannot_hide_behind_first_member(business_result):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["placements"].append(
        {"object_id": "invented", "purpose": "bed", "location_direction": "S"}
    )
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "fail"
    assert "unconfirmed_object_count:placements" in result["failures"]
    assert (
        "unconfirmed_argument_supplied:placements.1.location_direction"
        in result["failures"]
    )


def test_correct_assessment_cannot_hide_unrelated_bad_fatebridge_call(business_result):
    current = valid_turn(business_result)
    current["items"].append(
        {
            "id": "extra",
            "type": "mcpToolCall",
            "server": "fatebridge",
            "tool": "bazi_career",
            "status": "completed",
            "arguments": {},
        }
    )
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "fail"
    assert "tool_not_permitted_by_evidence_contract:bazi_career" in result["failures"]
    assert len(result["fatebridge_calls"]) == 2


@pytest.mark.parametrize("unknown", [None, False])
def test_unconfirmed_fact_is_not_null_or_false(business_result, unknown):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["placements"][0]["location_direction"] = unknown
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


@pytest.mark.parametrize("fields", [3, [True], [None]])
def test_invalid_output_control_is_not_valid_call_evidence(business_result, fields):
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["fields"] = fields
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "fail"
    assert any(
        "controls" in error
        for error in result["assessment_calls"][0]["parameter_validation_errors"]
    )


def test_native_json_text_result_is_equivalent_evidence(business_result):
    current = valid_turn(business_result)
    current["items"][-1]["result"] = {
        "content": [{"type": "text", "text": json.dumps(business_result)}]
    }
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "pass"


def test_business_result_with_no_receipt_cannot_pass(business_result):
    current = valid_turn(business_result)
    del current["items"][-1]["result"]["structuredContent"]["run_metadata"]
    assert (
        evaluator.audit_turn(current, CONTRACT)["call_evidence_status"]
        == "insufficient_evidence"
    )


def test_receipt_for_other_arguments_is_rejected(business_result):
    current = valid_turn(business_result)
    current["items"][-1]["result"]["structuredContent"]["run_metadata"][
        "input_sha256"
    ] = ("0" * 64)
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


def test_if_present_fact_may_be_omitted_but_cannot_be_fabricated(business_result):
    optional = copy.deepcopy(CONTRACT)
    optional["if_present_arguments"] = {
        "placements.0.observation_basis": "user_confirmed"
    }
    assert (
        evaluator.audit_turn(valid_turn(business_result), optional)[
            "call_evidence_status"
        ]
        == "pass"
    )
    current = valid_turn(business_result)
    current["items"][-1]["arguments"]["placements"][0]["observation_basis"] = "measured"
    assert evaluator.audit_turn(current, optional)["call_evidence_status"] == "fail"


def test_discovery_is_allowed_but_cannot_hide_extra_arguments(business_result):
    current = valid_turn(business_result)
    current["items"].append(
        {
            "id": "read",
            "type": "mcpToolCall",
            "server": "fatebridge",
            "tool": "read_mcp_resource",
            "status": "completed",
            "arguments": {
                "server": "fatebridge",
                "uri": "fatebridge://tools/fengshui_assess/input",
            },
            "result": {"content": [{"type": "text", "text": '{"contents": []}'}]},
        }
    )
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "pass"
    current["items"][-1]["arguments"]["invented_argument"] = True
    assert evaluator.audit_turn(current, CONTRACT)["call_evidence_status"] == "fail"


def test_missing_server_and_result_cannot_be_pass(business_result):
    current = valid_turn(business_result)
    del current["items"][-1]["server"]
    del current["items"][-1]["result"]
    result = evaluator.audit_turn(current, CONTRACT)
    assert result["call_evidence_status"] == "insufficient_evidence"
    assert "call_server_not_observed:fengshui_assess" in result["unavailable_evidence"]
    assert "business_result_not_observed" in result["unavailable_evidence"]
