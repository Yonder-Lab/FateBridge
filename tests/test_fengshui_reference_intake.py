"""A method-reference label must not turn into a request for site facts."""

import asyncio
import json

import pytest
from fastmcp import Client

from fatebridge.cli import run
from fatebridge.mcp_server import create_mcp_app
from fatebridge.services.fengshui import assess
from tests.test_fengshui_surfaces import SPECS, rest_client, without_transport


@pytest.mark.parametrize("scene", ["home", "workstation", "shared_rental"])
@pytest.mark.parametrize("layout_flag", [{}, {"analyze_layout": False}])
def test_reference_label_does_not_create_missing_physical_facts(scene, layout_flag):
    result = assess(scene=scene, methods=[], **layout_flag)
    assert result["method_details"]["status"] == "reference_only"
    assert result["status"] == "complete"
    assert result["coverage"]["missing_inputs"] == []
    assert result["layers"] == {}
    # A completed reference lookup does not claim a completed site assessment.
    assert "layout_analysis" not in result
    assert "analysis_progress" not in result["coverage"]


def test_explicit_empty_layout_request_still_requires_observations():
    result = assess(scene="home", methods=[], analyze_layout=True)
    assert result["method_details"]["status"] == "reference_only"
    progress = result["layout_analysis"]["analysis_progress"]
    assert progress["interpretation_status"] == "insufficient_evidence"
    assert progress["follow_up"]["conclusion_candidates"]


def test_reference_with_actual_observation_retains_its_independent_assessment():
    result = assess(
        scene="workstation",
        methods=[],
        analyze_layout=False,
        form_observations=[
            {
                "object_id": "desk",
                "purpose": "desk",
                "entrance_visible": False,
                "observation_basis": "user_confirmed",
                "evidence": "正常坐姿看不到入口",
            }
        ],
    )
    progress = result["layout_analysis"]["analysis_progress"]
    assert progress["interpretation_status"] == "available"
    assert not progress["assessment_complete"]


def test_reference_intake_matches_rest_mcp_cli(monkeypatch, tmp_path, capsys):
    inputs = {
        "scene": "home",
        "methods": [],
        "analyze_layout": False,
    }
    response = rest_client(monkeypatch).post(SPECS["assess"].rest_path, json=inputs)

    async def call():
        async with Client(create_mcp_app(families="fengshui")) as client:
            return await client.call_tool(
                "fengshui_assess", {**inputs, "response_char_limit": 0}
            )

    protocol = asyncio.run(call())
    request_file = tmp_path / "reference.json"
    request_file.write_text(json.dumps(inputs, ensure_ascii=False))
    code = run(["fengshui_assess", "--request-file", str(request_file)])
    cli_result = json.loads(capsys.readouterr().out)
    assert response.status_code == 200, response.text
    assert not protocol.is_error
    assert code == 0
    assert (
        without_transport(response.json())
        == without_transport(protocol.structured_content)
        == without_transport(cli_result)
    )
    assert response.json()["status"] == "complete"
    assert response.json()["coverage"]["missing_inputs"] == []
