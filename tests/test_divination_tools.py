from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import MeihuaAnalysisRequest
from fastmcp_server import meihua_analysis
from fatebridge.services.divination import calculate_meihua_analysis


def test_meihua_request_model_accepts_analysis_fields():
    request = MeihuaAnalysisRequest(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        question="事业推进节奏",
    )

    payload = request.model_dump()

    assert payload["analysis_year"] == 2028
    assert payload["analysis_month"] == 4
    assert payload["analysis_day"] == 1
    assert payload["analysis_hour"] == 9
    assert payload["analysis_minute"] == 0
    assert payload["analysis_timezone"] == "Asia/Shanghai"
    assert payload["question"] == "事业推进节奏"


def test_calculate_meihua_analysis_returns_expected_hexagram_chain():
    result = calculate_meihua_analysis(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        question="事业推进节奏",
    )

    meihua = result["meihua"]

    assert result["analysis_context"]["lunar_display"] == "三月初七"
    assert result["analysis_context"]["current_jieqi"] == "春分"
    assert meihua["base_hexagram"]["name"] == "火天大有"
    assert meihua["changed_hexagram"]["name"] == "火风鼎"
    assert meihua["mutual_hexagram"]["name"] == "泽天夬"
    assert meihua["opposite_hexagram"]["name"] == "水地比"
    assert meihua["moving_palace"] == "下卦"
    assert meihua["body_trigram"]["name"] == "离"
    assert meihua["use_trigram"]["name"] == "乾"
    assert meihua["body_use_relation"] == "体克用"
    assert "体卦离、用卦乾" in meihua["body_use_summary"]
    assert "火天大有" in result["summary"]


def test_fastmcp_meihua_tool_exposes_parameters():
    properties = meihua_analysis.parameters["properties"]

    assert "analysis_year" in properties
    assert "analysis_month" in properties
    assert "analysis_day" in properties
    assert "analysis_hour" in properties
    assert "analysis_minute" in properties
    assert "analysis_timezone" in properties
    assert "question" in properties
