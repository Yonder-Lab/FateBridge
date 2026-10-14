"""Audit observed MCP evidence; consultation success needs independent answer review.

Evaluator contracts must never be supplied to the model. All FateBridge calls,
all supplied facts, and business receipts are checked. A keyword, a completeness
flag or a numeric score cannot establish consultation success. Opaque code-mode
calls and missing results are insufficient evidence, never an automated pass.
"""

import argparse
import json
import re
from functools import lru_cache
from pathlib import Path


def read_path(value, path):
    """Read dotted object/list paths without treating missing values as null."""
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):
            value = value[int(part)]
        else:
            return False, None
    return True, value


def call_arguments(item):
    value = item.get("arguments")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


def leaf_paths(value, prefix=""):
    """Visit every supplied value, including empty containers and later members."""
    if isinstance(value, dict) and value:
        for key, child in value.items():
            yield from leaf_paths(child, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list) and value:
        for index, child in enumerate(value):
            yield from leaf_paths(child, f"{prefix}.{index}")
    else:
        yield prefix, value


def identical(value, expected):
    """JSON equality with type identity: false, zero, null and absence differ."""
    if type(value) is not type(expected):
        return False
    if isinstance(value, dict):
        return value.keys() == expected.keys() and all(
            identical(value[k], expected[k]) for k in value
        )
    if isinstance(value, list):
        return len(value) == len(expected) and all(
            identical(a, b) for a, b in zip(value, expected)
        )
    return value == expected


@lru_cache(maxsize=1)
def shared_specs():
    from fatebridge.services.tool_catalog import CATALOG

    return {spec.tool_name: spec for spec in CATALOG if spec.mcp_name}


def validate_arguments(tool, arguments):
    """Use shared business models and MCP flags; check schema and semantics.

    JSON Schema rejects coercions and extra fields; model validation supplies
    calendar, reference and cross-field rules that JSON Schema cannot express.
    No evaluator-owned approximation of a production business schema is used.
    """
    from jsonschema import Draft202012Validator
    from pydantic import ValidationError

    from fatebridge.mcp_transport import OutputFlags

    spec = shared_specs().get(tool)
    if spec is None:
        return None, ["unknown_published_tool"]
    flags = {k: v for k, v in arguments.items() if k in OutputFlags.model_fields}
    inputs = {k: v for k, v in arguments.items() if k not in OutputFlags.model_fields}
    errors = []
    for model, values, label in (
        (OutputFlags, flags, "controls"),
        (spec.request_model, inputs, "business"),
    ):
        for error in Draft202012Validator(model.model_json_schema()).iter_errors(
            values
        ):
            path = ".".join(map(str, error.absolute_path)) or "$"
            errors.append(f"{label}:{path}:{error.validator}")
        try:
            validated = model.model_validate_json(json.dumps(values), strict=True)
        except ValidationError as exc:
            errors.extend(
                f"{label}:{'.'.join(map(str, e['loc'])) or '$'}:{e['type']}"
                for e in exc.errors(include_input=False, include_url=False)
            )
        else:
            if model is spec.request_model:
                request = validated
    return (None if errors else request), sorted(set(errors))


def result_payload(call):
    """Prefer structured content, accept native JSON text, reject disagreement."""
    result = call.get("result")
    if not isinstance(result, dict) or not result:
        return None, False
    payload = result.get("structuredContent")
    if not isinstance(payload, dict):
        payload = None
    texts = []
    for content in result.get("content", []):
        if content.get("type") == "text":
            try:
                parsed = json.loads(content.get("text", ""))
            except (ValueError, TypeError):
                continue
            if isinstance(parsed, dict):
                texts.append(parsed)
    candidates = ([payload] if payload is not None else []) + texts
    if not candidates:
        return None, False
    return candidates[0], any(not identical(candidates[0], p) for p in candidates[1:])


def audit_result(call, arguments, request, contract, observation):
    from pydantic import ValidationError

    from fatebridge.core.response_models import RunMetadata
    from fatebridge.services.replay_metadata import digest

    failures, unavailable = [], []
    business, disagree = result_payload(call)
    if disagree:
        failures.append("structured_and_text_results_disagree")
    result = call.get("result") or {}
    if (
        call.get("status") != "completed"
        or call.get("error")
        or result.get("isError") is True
        or (business and (business.get("error_code") or business.get("error")))
    ):
        failures.append("assessment_call_not_completed")
        return failures, unavailable
    if business is None:
        return failures, ["business_result_not_observed"]
    for path in contract.get(
        "required_result_paths", ["layout_analysis", "rule_trace"]
    ):
        present, value = read_path(business, path)
        if not present or not value:
            unavailable.append(f"business_evidence_missing:{path}")
    metadata = business.get("run_metadata")
    if not isinstance(metadata, dict):
        return failures, unavailable + ["run_metadata_not_observed"]
    spec = shared_specs()[call["tool"]]
    try:
        RunMetadata.model_validate_json(json.dumps(metadata), strict=True)
        if spec.output_model:
            spec.output_model.model_validate_json(json.dumps(business), strict=True)
    except ValidationError:
        failures.append("result_schema_invalid")
    if metadata.get("tool_name") != spec.run_metadata_name:
        failures.append("receipt_tool_mismatch")
    for name in ("contract_sha256", "input_sha256", "business_output_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", str(metadata.get(name, ""))):
            unavailable.append(f"receipt_digest_missing_or_invalid:{name}")
    if request is not None and spec.family == "fengshui":
        # Fengshui has no true-solar-time presence-sensitive fields. Do not apply
        # this normalization blindly to other catalog families.
        expected = digest(
            {
                "tool_key": spec.key,
                "inputs": request.model_dump(mode="json"),
                "presence": [],
            }
        )
        if metadata.get("input_sha256") != expected:
            failures.append("receipt_input_digest_mismatch")
        else:
            observation["receipt_input_binding"] = "verified_current_request_model"
    elif request is not None:
        observation["receipt_input_binding"] = "not_verified_for_this_family"
        unavailable.append("receipt_input_normalization_not_supported_for_family")
    if not arguments.get("fields"):
        body = {k: v for k, v in business.items() if k != "run_metadata"}
        if metadata.get("business_output_sha256") != digest(body):
            failures.append("receipt_business_digest_mismatch")
        else:
            observation["receipt_business_binding"] = "verified_full_payload"
    else:
        # The server hashes the full business payload before field projection.
        # The projected response cannot independently reproduce that digest.
        observation["receipt_business_binding"] = (
            "full_payload_digest_not_recomputable_from_projection"
        )
    for name in ("trace_id", "parent_run_id"):
        if arguments.get(name) is not None and metadata.get(name) != arguments[name]:
            failures.append(f"receipt_correlation_mismatch:{name}")
    return failures, unavailable


def audit_facts(arguments, contract, observation):
    failures = []
    required = contract.get("required_arguments", {})
    optional = contract.get("if_present_arguments", {})
    for path, expected in {**optional, **required}.items():
        present, value = read_path(arguments, path)
        passed = (not present and path not in required) or (
            present and identical(value, expected)
        )
        observation["checks"].append({"path": path, "passed": passed})
        if not passed:
            failures.append(f"confirmed_fact_not_preserved:{path}")
    for path in contract.get("forbidden_argument_paths", []):
        present, _ = read_path(arguments, path)
        observation["checks"].append({"path": path, "passed": not present})
        if present:
            failures.append(f"unconfirmed_fact_supplied:{path}")
    for path, count in contract.get("argument_array_counts", {}).items():
        present, value = read_path(arguments, path)
        if not present and count == 0:
            continue
        if not present or not isinstance(value, list) or len(value) != count:
            failures.append(f"unconfirmed_object_count:{path}")
    # Allowed paths describe identity/evidence strings and transport controls.
    # Only operational arrays (fields) authorize a subtree; fact objects and
    # their members must be enumerated individually by the evaluator contract.
    allowed = set(contract.get("allowed_argument_paths", []))
    for path, _ in leaf_paths(arguments):
        if any(path == p or path.startswith(p + ".") for p in allowed):
            continue
        if any(path == p or path.startswith(p + ".") for p in required | optional):
            continue  # Whole required arrays/objects were compared recursively.
        failures.append(f"unconfirmed_argument_supplied:{path}")
    return failures


DISCOVERY_TOOLS = {
    "list_mcp_resources",
    "list_mcp_resource_templates",
    "read_mcp_resource",
}


def audit_discovery(call):
    """Validate host-native resource helpers separately from business ToolSpecs."""
    from jsonschema import Draft202012Validator

    failures, unavailable = [], []
    tool = call["tool"]
    arguments = call_arguments(call)
    if arguments is None:
        unavailable.append(f"call_arguments_not_observed:{tool}")
    else:
        properties = {"server": {"type": "string", "const": "fatebridge"}}
        required = []
        if tool == "read_mcp_resource":
            properties["uri"] = {"type": "string", "pattern": "^fatebridge://"}
            required = ["uri"]
        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }
        if list(Draft202012Validator(schema).iter_errors(arguments)):
            failures.append(f"invalid_discovery_arguments:{tool}")
    payload, disagree = result_payload(call)
    if disagree:
        failures.append("structured_and_text_results_disagree")
    if (
        call.get("status") != "completed"
        or call.get("error")
        or (call.get("result") or {}).get("isError")
        or (payload and (payload.get("error") or payload.get("error_code")))
    ):
        failures.append(f"discovery_call_not_completed:{tool}")
    if payload is None:
        unavailable.append(f"discovery_result_not_observed:{tool}")
    return failures, unavailable


def audit_turn(turn, contract):
    """Check every native call: a later recovery cannot erase an earlier fault."""
    failures, unavailable, observations, all_observations = [], [], [], []
    if turn.get("status") != "completed":
        failures.append("turn_did_not_complete")
    calls = [
        item
        for item in turn.get("items", [])
        if item.get("type") == "mcpToolCall"
        and (
            item.get("server") == "fatebridge"
            or (
                not item.get("server")
                and item.get("tool") in set(shared_specs()) | DISCOVERY_TOOLS
            )
        )
    ]
    assessments = [c for c in calls if c.get("tool") == "fengshui_assess"]
    if assessments and contract.get("forbid_assess"):
        failures.append("assessment_not_permitted_by_evidence_contract")
    if not assessments and contract.get("require_assess"):
        unavailable.append("required_assessment_call_not_observed")
    allowed_tools = contract.get("allowed_tools")
    if allowed_tools is None:
        unavailable.append("explicit_allowed_tools_contract_missing")
        allowed_tools = []
    for call in calls:
        tool = call.get("tool")
        if not call.get("server"):
            unavailable.append(f"call_server_not_observed:{tool}")
        observation = {"item_id": call.get("id"), "tool": tool, "checks": []}
        all_observations.append(observation)
        if tool not in allowed_tools:
            failures.append(f"tool_not_permitted_by_evidence_contract:{tool}")
        if tool in DISCOVERY_TOOLS:
            failed, missing = audit_discovery(call)
            failures.extend(failed)
            unavailable.extend(missing)
            continue
        arguments = call_arguments(call)
        if arguments is None:
            unavailable.append(f"call_arguments_not_observed:{tool}")
            continue
        request, errors = validate_arguments(tool, arguments)
        observation["parameter_validation_errors"] = errors
        if errors:
            failures.extend(
                f"invalid_call_arguments:{tool}:{error}" for error in errors
            )
        if tool != "fengshui_assess":
            payload, disagree = result_payload(call)
            if disagree:
                failures.append("structured_and_text_results_disagree")
            if (
                call.get("status") != "completed"
                or call.get("error")
                or (call.get("result") or {}).get("isError")
                or (payload and (payload.get("error") or payload.get("error_code")))
            ):
                failures.append(f"business_call_not_completed:{tool}")
            if payload is None:
                unavailable.append(f"business_result_not_observed:{tool}")
            # Uncontracted business calls may be schema-valid yet use invented
            # facts. Do not treat an allowlist alone as a fact contract.
            unavailable.append(f"business_fact_contract_not_available:{tool}")
            continue
        observations.append(observation)
        if (
            "allowed_argument_paths" not in contract
            or "argument_array_counts" not in contract
        ):
            unavailable.append("exhaustive_fact_contract_missing")
        failures.extend(audit_facts(arguments, contract, observation))
        failed, missing = audit_result(call, arguments, request, contract, observation)
        failures.extend(failed)
        unavailable.extend(missing)
    return {
        "call_evidence_status": (
            "fail" if failures else "insufficient_evidence" if unavailable else "pass"
        ),
        "failures": sorted(set(failures)),
        "unavailable_evidence": sorted(set(unavailable)),
        "assessment_calls": observations,
        "fatebridge_calls": all_observations,
        "human_review": {
            "status": "pending",
            "criteria": [
                "answer_claims_trace_to_confirmed_facts_and_selected_rules",
                "action_respects_mobility_shared_use_and_user_goal",
                "correction_replaces_stale_facts",
                "unknowns_and_method_disagreements_remain_visible",
                "conditional_objects_do_not_become_guaranteed_cures",
            ],
            "required_evidence": "cite public answer and corresponding tool finding",
        },
        "consultation_success": "not_established_by_call_checks",
    }


def audit(record, contract):
    if "turn_expectations" in contract:
        contract = {
            "case": record.get("case"),
            "turns": contract["turn_expectations"].get(record.get("case"), []),
        }
    turns = record.get("turns", [])
    expectations = contract.get("turns", [])
    report = {
        "case": record.get("case"),
        "evidence_scope": "all_observed_native_fatebridge_calls_shared_schema_confirmed_facts_business_results_and_receipts",
        "turns": [
            audit_turn(turn, expectations[index])
            for index, turn in enumerate(turns)
            if index < len(expectations)
        ],
        "expected_turn_count": len(expectations),
        "observed_turn_count": len(turns),
    }
    report["status"] = (
        "fail"
        if len(turns) != len(expectations)
        or ("case" in contract and contract["case"] != record.get("case"))
        or any(t["call_evidence_status"] == "fail" for t in report["turns"])
        else (
            "insufficient_evidence"
            if not expectations
            or any(
                t["call_evidence_status"] == "insufficient_evidence"
                for t in report["turns"]
            )
            else "pass"
        )
    )
    report["consultation_success"] = "requires_independent_answer_review"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(
        json.loads(args.record.read_text()), json.loads(args.contract.read_text())
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"case": report["case"], "status": report["status"]}))
    raise SystemExit(0 if report["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
