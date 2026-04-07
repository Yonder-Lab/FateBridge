from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import WesternTimingRequest
from fastmcp_server import western_timing_analysis
from fatebridge.services.western_timing import calculate_western_timing_analysis


def test_western_timing_request_model_accepts_fields():
    request = WesternTimingRequest(
        name="Alice",
        birth_year=1990,
        birth_month=5,
        birth_day=17,
        birth_hour=15,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        birth_latitude=31.2304,
        analysis_year=2025,
        analysis_month=5,
        analysis_day=20,
    )

    payload = request.model_dump()

    assert payload["name"] == "Alice"
    assert payload["birth_minute"] == 30
    assert payload["birth_timezone"] == "Asia/Shanghai"
    assert payload["birth_longitude"] == 121.4737
    assert payload["birth_latitude"] == 31.2304
    assert payload["analysis_year"] == 2025
    assert payload["analysis_month"] == 5
    assert payload["analysis_day"] == 20


def test_calculate_western_timing_analysis_returns_predictive_sections():
    result = calculate_western_timing_analysis(
        name="Alice",
        birth_year=1990,
        birth_month=5,
        birth_day=17,
        birth_hour=15,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        birth_latitude=31.2304,
        analysis_year=2025,
        analysis_month=5,
        analysis_day=20,
    )

    assert result["analysis_type"] == "西占推运与返照分析"
    assert result["natal_reference"]["sun"]["sign"] == "Taurus"
    assert result["natal_reference"]["sun"]["sign_label"] == "金牛座"
    assert result["natal_reference"]["ascendant"]["sign"] == "Libra"
    assert result["natal_reference"]["ascendant"]["sign_label"] == "天秤座"

    assert result["returns"]["solar_return"]["return_datetime"].startswith(
        "2025-05-17T01:47:24+08:00"
    )
    assert result["returns"]["lunar_return"]["return_datetime"].startswith(
        "2025-05-20T01:30:17+08:00"
    )

    assert result["directions"]["secondary_progression"][
        "progressed_datetime"
    ].startswith("1990-06-21")
    assert result["directions"]["solar_arc"]["arc_degrees"] == pytest.approx(
        33.5458, abs=0.01
    )

    profection = result["time_lords"]["annual_profection"]
    assert profection["activated_house"] == 12
    assert profection["activated_sign"] == "Virgo"
    assert profection["activated_sign_label"] == "处女座"
    assert profection["lord"] == "Mercury"
    assert profection["lord_label"] == "水星"

    firdaria = result["time_lords"]["firdaria"]
    assert firdaria["current_major"]["planet"] == "Moon"
    assert firdaria["current_major"]["planet_label"] == "月亮"
    assert firdaria["current_sub"]["planet"] == "Mars"
    assert firdaria["current_sub"]["planet_label"] == "火星"

    decennials = result["time_lords"]["decennials"]
    assert decennials["current_level_1"]["planet"] == "Moon"
    assert decennials["current_level_2"]["planet"] == "Mars"
    assert decennials["current_level_3"]["planet"] == "Moon"

    assert "太阳返照" in result["summary"]
    assert "法达" in result["summary"]


def test_fastmcp_western_timing_tool_exposes_parameters():
    properties = western_timing_analysis.parameters["properties"]

    assert "birth_timezone" in properties
    assert "birth_longitude" in properties
    assert "birth_latitude" in properties
    assert "analysis_year" in properties
    assert "analysis_month" in properties
    assert "analysis_day" in properties
