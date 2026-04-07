from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import AstroChartRequest, AstroRelativePartyRequest, AstroRelativeRequest
from fastmcp_server import astro_chart, astro_relative_chart
from fatebridge.services.astrology import (
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
    calculate_relative_chart_analysis,
)


def _build_birth_payload():
    return {
        "name": "测试者",
        "birth_year": 1990,
        "birth_month": 4,
        "birth_day": 6,
        "birth_hour": 9,
        "birth_minute": 33,
        "birth_timezone": "Asia/Shanghai",
        "birth_longitude": 121.4667,
        "birth_latitude": 31.2167,
        "birth_place": "上海",
    }


def test_astro_request_models_accept_geo_fields():
    request = AstroChartRequest(**_build_birth_payload())
    relative_request = AstroRelativeRequest(
        inner=AstroRelativePartyRequest(**_build_birth_payload()),
        outer=AstroRelativePartyRequest(
            **{
                **_build_birth_payload(),
                "name": "对盘者",
                "birth_year": 1992,
                "birth_month": 3,
                "birth_day": 2,
                "birth_hour": 8,
                "birth_minute": 18,
            }
        ),
        relationship_mode="synastry",
    )

    chart_payload = request.model_dump()
    relation_payload = relative_request.model_dump()

    assert chart_payload["birth_longitude"] == 121.4667
    assert chart_payload["birth_latitude"] == 31.2167
    assert relation_payload["inner"]["birth_latitude"] == 31.2167
    assert relation_payload["outer"]["name"] == "对盘者"


def test_core_chart_variants_expose_variant_specific_fields():
    chart = calculate_core_chart_analysis(chart_variant="chart", **_build_birth_payload())
    chart13 = calculate_core_chart_analysis(
        chart_variant="chart13",
        **_build_birth_payload(),
    )
    hellen = calculate_core_chart_analysis(
        chart_variant="hellen_chart",
        **_build_birth_payload(),
    )
    guolao = calculate_core_chart_analysis(
        chart_variant="guolao_chart",
        **_build_birth_payload(),
    )
    india = calculate_core_chart_analysis(
        chart_variant="india_chart",
        **_build_birth_payload(),
    )

    assert chart["chart_profile"]["chart_type"] == "chart"
    assert len(chart["houses"]) == 12
    assert len(chart["planets"]) >= 10
    assert any(item["id"] == "Sun" for item in chart["planets"])
    assert any(item["id"] == "Moon" for item in chart["planets"])
    assert isinstance(chart["angles"]["ascendant"]["longitude"], float)

    assert chart13["chart_profile"]["chart_type"] == "chart13"
    assert len(chart13["thirteen_sectors"]) == 13
    assert "sector13" in next(item for item in chart13["planets"] if item["id"] == "Sun")

    assert hellen["chart_profile"]["chart_type"] == "hellen_chart"
    assert hellen["chart_profile"]["house_system"] == "whole_sign"
    assert hellen["hellenistic"]["sect"] in {"day", "night"}
    assert "lot_of_fortune" in hellen["hellenistic"]

    assert guolao["chart_profile"]["chart_type"] == "guolao_chart"
    assert guolao["guolao"]["lunar_mansion_system"] == "su28"
    assert len(guolao["guolao"]["planetary_mansions"]) >= 7

    assert india["chart_profile"]["chart_type"] == "india_chart"
    assert india["chart_profile"]["zodiac"] == "sidereal"
    assert india["india"]["ayanamsha"] > 0
    assert "nakshatra" in next(item for item in india["planets"] if item["id"] == "Moon")


def test_germany_chart_returns_midpoint_payload():
    result = calculate_germany_chart_analysis(**_build_birth_payload())

    assert result["chart_profile"]["chart_type"] == "germany"
    assert result["midpoints"]
    assert result["midpoint_aspects"]
    assert result["base_chart"]["planets"]


def test_relative_chart_returns_synastry_and_composite_layers():
    result = calculate_relative_chart_analysis(
        inner_payload=_build_birth_payload(),
        outer_payload={
            **_build_birth_payload(),
            "name": "对盘者",
            "birth_year": 1992,
            "birth_month": 3,
            "birth_day": 2,
            "birth_hour": 8,
            "birth_minute": 18,
        },
        relationship_mode="synastry",
    )

    assert result["relationship_profile"]["chart_type"] == "relative"
    assert result["synastry_aspects"]
    assert result["composite_chart"]["planets"]
    assert result["compatibility"]["element_harmony_score"] >= 0
    assert result["compatibility"]["element_harmony_score"] <= 100


def test_fastmcp_astro_tools_expose_geo_parameters():
    chart_properties = astro_chart.parameters["properties"]
    relative_properties = astro_relative_chart.parameters["properties"]

    assert "birth_longitude" in chart_properties
    assert "birth_latitude" in chart_properties
    assert "inner_birth_latitude" in relative_properties
    assert "outer_birth_longitude" in relative_properties
