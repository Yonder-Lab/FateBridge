"""Same-environment contract and branch-output comparison for structural changes."""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from fatebridge.application.discovery import discover_specs
from fatebridge.application.execution import execute_tool
from fatebridge.application.scenarios import discover_scenarios
from fatebridge.core.astro.birth import build_astro_birth_info
from fatebridge.core.astro.chart import build_core_chart_payload
from fatebridge.core.astro.reference import (
    CORE_CHART_DEFAULT_HOUSE_SYSTEMS,
    RELATIVE_MODE_LABELS_ZH,
)
from fatebridge.core.astro.relationship import build_relative_payload
from fatebridge.core.execution_context import ExecutionOptions, call_clock
from fatebridge.services.birth_context import build_birth_computation_context
from fatebridge.services.timing_state import build_current_timing_state
from fatebridge.services.tool_catalog import CATALOG
from fatebridge.utils.birth_input import create_person_info
from tests.fixtures.surface_payloads import MCP_CASES, REST_POST_CASES

AS_OF = "2026-10-12T12:00:00+08:00"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def capture():
    results = {}
    for spec in CATALOG:
        factory = (
            REST_POST_CASES[spec.rest_path]
            if spec.rest_path
            else MCP_CASES[spec.tool_name][1]
        )
        request = spec.request_model.model_validate(factory())
        body = execute_tool(spec, request, options=ExecutionOptions(as_of=AS_OF))
        assert "error" not in body, (spec.key, body)
        body.pop("run_metadata", None)
        results[f"tool/{spec.key}"] = digest(body)
    results["contract/catalog"] = digest(discover_specs(CATALOG))
    results["contract/scenarios"] = digest(discover_scenarios(CATALOG))
    from fatebridge.api import app

    results["contract/openapi"] = digest(app.openapi())
    births = [
        build_astro_birth_info(
            name="结构回归虚构样例",
            birth_year=year,
            birth_month=month,
            birth_day=day,
            birth_hour=hour,
            birth_minute=minute,
            birth_timezone="Asia/Shanghai",
            birth_longitude=121.4737,
            birth_latitude=31.2304,
            use_true_solar_time=solar,
        )
        for year, month, day, hour, minute, solar in [
            (1990, 6, 1, 1, 0, False),
            (2000, 12, 10, 9, 55, True),
        ]
    ]
    for variant in CORE_CHART_DEFAULT_HOUSE_SYSTEMS:
        for index, birth in enumerate(births):
            results[f"chart/{variant}/{index}/default"] = digest(
                build_core_chart_payload(birth, variant)
            )
    for house in range(9):
        for zodiac in (0, 1):
            results[f"chart/house-{house}/zodiac-{zodiac}"] = digest(
                build_core_chart_payload(
                    births[1], "chart", hsys=house, zodiacal=zodiac
                )
            )
    for mode in RELATIVE_MODE_LABELS_ZH:
        for zodiac in (0, 1):
            results[f"relative/{mode}/{zodiac}"] = digest(
                build_relative_payload(
                    *births,
                    relative_mode=mode,
                    hsys=3,
                    zodiacal=zodiac,
                    relationship_focus="marriage",
                )
            )
    for house in range(9):
        results[f"relative/house-{house}"] = digest(
            build_relative_payload(*births, hsys=house, zodiacal=1)
        )
    from fatebridge.core.astro import runtime

    with patch.object(runtime, "swe", None):
        for variant in ("chart13", "hellen_chart", "india_chart"):
            results[f"approximate/{variant}"] = digest(
                build_core_chart_payload(births[0], variant)
            )
        for key, call in [
            (
                "quadrant",
                lambda: build_core_chart_payload(births[0], "chart", hsys=3),
            ),
            (
                "bad-zodiac",
                lambda: build_core_chart_payload(births[0], "chart13", zodiacal=8),
            ),
        ]:
            try:
                call()
            except ValueError as exc:
                results[f"error/{key}"] = digest(str(exc))
            else:
                raise AssertionError(key)
    person = create_person_info(
        1990,
        5,
        15,
        10,
        "结构回归虚构样例",
        "男",
        "上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        use_true_solar_time=True,
    )
    context = build_birth_computation_context(person)
    for moment in (
        "2028-02-04T15:29:00",
        "2028-02-04T15:31:00",
        "2028-04-04T14:59:00",
        "2028-04-04T15:01:00",
        "2028-05-15T09:00:00",
    ):
        for age in (None, 38):
            with call_clock(AS_OF):
                state = build_current_timing_state(
                    context,
                    analysis_date=datetime.fromisoformat(moment),
                    analysis_age=age,
                )
            state["analysis_date"] = state["analysis_date"].isoformat()
            results[f"timing-state/{moment}/{age}"] = digest(state)
    return results


if __name__ == "__main__":
    results = capture()
    Path(sys.argv[1]).write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    print(f"Captured {len(results)} output and contract hashes")
