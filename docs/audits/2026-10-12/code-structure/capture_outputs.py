import hashlib
import json
import sys
from pathlib import Path

from fatebridge.application.discovery import discover_specs
from fatebridge.application.execution import execute_tool
from fatebridge.application.scenarios import discover_scenarios
from fatebridge.core.execution_context import ExecutionOptions
from fatebridge.services.tool_catalog import CATALOG
from tests.fixtures.surface_payloads import REST_POST_CASES


def digest(v):
    return hashlib.sha256(
        json.dumps(v, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


results = {}
for spec in CATALOG:
    if not spec.rest_path:
        continue
    request = spec.request_model.model_validate(REST_POST_CASES[spec.rest_path]())
    body = execute_tool(
        spec, request, options=ExecutionOptions(as_of="2026-10-12T12:00:00+08:00")
    )
    if "error" in body:
        raise RuntimeError((spec.key, body))
    body.pop("run_metadata", None)
    results[spec.key] = digest(body)
results["discovery"] = digest(discover_specs(CATALOG))
results["scenarios"] = digest(discover_scenarios(CATALOG))
Path(sys.argv[1]).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
print("Captured", len(results) - 2, "business outputs and discovery/scenarios")
