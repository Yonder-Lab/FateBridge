from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import WesternTimingRequest
from fastmcp_server import western_timing_analysis
from fatebridge.core.astrology_predictive import build_releasing_level_within_interval
from fatebridge.services.astrology import calculate_core_chart_analysis
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
        pd_method="astroapp_alchabitius",
        pd_time_key="Ptolemy",
        pd_aspects=[0, 60, 90, 120, 180],
        show_pd_bounds=True,
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
    assert payload["pd_method"] == "astroapp_alchabitius"
    assert payload["pd_time_key"] == "Ptolemy"
    assert payload["pd_aspects"] == [0, 60, 90, 120, 180]
    assert payload["show_pd_bounds"] is True


def test_western_timing_request_model_accepts_pd_type():
    request = WesternTimingRequest(
        name="Alice",
        birth_year=1990,
        birth_month=5,
        birth_day=17,
        birth_hour=15,
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        birth_latitude=31.2304,
        pd_type=1,
    )

    payload = request.model_dump()

    assert payload["pd_type"] == 1


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
        pd_method="astroapp_alchabitius",
        pd_time_key="Naibod",
        pd_aspects=[0, 90, 180],
        show_pd_bounds=True,
    )

    assert result["analysis_type"] == "西占推运与返照分析"
    assert result["natal_reference"]["sun"]["sign"] == "Taurus"
    assert result["natal_reference"]["sun"]["sign_label"] == "金牛座"
    assert result["natal_reference"]["ascendant"]["sign"] == "Libra"
    assert result["natal_reference"]["ascendant"]["sign_label"] == "天秤座"
    assert result["natal_reference"]["lots"]["lot_of_fortune"]["sign"] == "Gemini"
    assert result["natal_reference"]["lots"]["lot_of_fortune"]["sign_label"] == "双子座"
    assert result["natal_reference"]["lots"]["lot_of_spirit"]["sign"] == "Capricorn"
    assert result["natal_reference"]["lots"]["lot_of_spirit"]["sign_label"] == "摩羯座"

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
    given_year = result["directions"]["given_year"]
    assert given_year["analysis_datetime"].startswith("2025-05-20T15:30:00+08:00")
    assert given_year["sun"]["sign"] == "Taurus"
    assert given_year["ascendant"]["sign"] == "Libra"
    assert len(given_year["monthly_profections"]) == 12
    assert given_year["monthly_profections"][0]["house"] == 12
    assert given_year["monthly_profections"][0]["sign"] == "Virgo"
    primary_directions = result["directions"]["primary_directions"]
    assert primary_directions["method"] == "astroapp_alchabitius"
    assert primary_directions["time_key"] == "Naibod"
    assert primary_directions["coordinate_system"] == "ecliptic_longitude"
    assert primary_directions["coordinate_label"] == "Arc"
    assert primary_directions["aspects"] == [0, 90, 180]
    assert primary_directions["current_arc_degrees"] == pytest.approx(
        34.5072, abs=0.01
    )
    assert len(primary_directions["current_window"]) > 0
    assert len(primary_directions["past_window"]) > 0
    assert len(primary_directions["future_window"]) > 0
    assert primary_directions["past_window"][0]["relative_years_from_current"] <= 0
    assert primary_directions["future_window"][0]["relative_years_from_current"] >= 0

    primary_direction_chart = result["directions"]["primary_direction_chart"]
    assert primary_direction_chart["analysis_datetime"].startswith(
        "2025-05-20T15:30:00+08:00"
    )
    assert primary_direction_chart["show_pd_bounds"] is True
    assert primary_direction_chart["coordinate_system"] == "ecliptic_longitude"
    assert primary_direction_chart["coordinate_label"] == "Arc"
    assert primary_direction_chart["current_arc_degrees"] == pytest.approx(
        34.5072, abs=0.01
    )
    assert primary_direction_chart["bounds_overlay"]["system"] == "egyptian_bounds"
    assert primary_direction_chart["bounds_overlay"]["enabled"] is True
    assert primary_direction_chart["bounds_overlay"]["points"]["Sun"]["sign"] == "Cancer"
    assert (
        primary_direction_chart["bounds_overlay"]["points"]["Sun"]["bound_lord"]
        == "Mars"
    )
    assert (
        primary_direction_chart["bounds_overlay"]["points"]["Sun"][
            "bound_lord_label"
        ]
        == "火星"
    )
    assert primary_direction_chart["directed_points"]["Sun"]["sign"] == "Cancer"
    assert primary_direction_chart["directed_points"]["Moon"]["sign"] == "Pisces"
    assert (
        primary_direction_chart["directed_lots"]["lot_of_fortune"]["sign"] == "Leo"
    )
    sun_sign_change = next(
        item
        for item in primary_direction_chart["sign_changes"]
        if item["point"] == "Sun"
    )
    assert sun_sign_change["from_sign"] == "Taurus"
    assert sun_sign_change["to_sign"] == "Cancer"

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

    zodiacal_releasing = result["time_lords"]["zodiacal_releasing"]
    assert zodiacal_releasing["spirit"]["lot"]["sign"] == "Capricorn"
    assert zodiacal_releasing["fortune"]["lot"]["sign"] == "Gemini"
    assert zodiacal_releasing["spirit"]["current_level_1"]["sign"] == "Aquarius"
    assert zodiacal_releasing["spirit"]["current_level_2"]["sign"] == "Cancer"
    assert zodiacal_releasing["spirit"]["current_level_3"]["sign"] == "Gemini"
    assert zodiacal_releasing["fortune"]["current_level_1"]["sign"] == "Cancer"
    assert zodiacal_releasing["fortune"]["current_level_2"]["sign"] == "Taurus"
    assert zodiacal_releasing["fortune"]["current_level_3"]["sign"] == "Cancer"

    assert "太阳返照" in result["summary"]
    assert "法达" in result["summary"]
    assert "Spirit 黄道释放" in result["summary"]


def test_core_chart_supports_fixed_offset_timezones():
    result = calculate_core_chart_analysis(
        birth_year=2028,
        birth_month=4,
        birth_day=6,
        birth_hour=9,
        birth_minute=33,
        birth_timezone="+08:00",
        birth_longitude=121.4667,
        birth_latitude=31.2167,
    )

    assert result["chart_profile"]["chart_type"] == "chart"
    assert result["chart_profile"]["engine_precision"] == "approximate_orbital_model"


def test_western_timing_supports_fixed_offset_timezones():
    result = calculate_western_timing_analysis(
        birth_year=2028,
        birth_month=4,
        birth_day=6,
        birth_hour=9,
        birth_minute=33,
        birth_timezone="+00:00",
        birth_longitude=174.5,
        birth_latitude=-41.433333,
        analysis_year=2031,
        analysis_month=4,
        analysis_day=6,
        return_timezone="+08:00",
        return_longitude=121.4667,
        return_latitude=31.2167,
    )

    assert result["analysis_type"] == "西占推运与返照分析"
    assert result["returns"]["solar_return"]["return_datetime"].endswith("+08:00")
    assert result["returns"]["lunar_return"]["return_datetime"].endswith("+08:00")


def test_primary_directions_support_converse_mode():
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
        pd_method="astroapp_alchabitius",
        pd_time_key="Naibod",
        pd_aspects=[0, 90, 180],
        pd_type=1,
        show_pd_bounds=True,
    )

    primary_directions = result["directions"]["primary_directions"]
    assert primary_directions["direction_mode"] == "converse"
    assert primary_directions["direction_mode_label"] == "逆推"
    assert primary_directions["current_arc_degrees"] == pytest.approx(
        -34.5072, abs=0.01
    )
    assert primary_directions["current_arc_absolute_degrees"] == pytest.approx(
        34.5072, abs=0.01
    )
    assert primary_directions["current_window"][0]["promissor"] == "Ascendant"
    assert primary_directions["current_window"][0]["significator"] == "Sun"
    assert primary_directions["current_window"][0]["aspect"] == "square"
    assert primary_directions["current_window"][0]["arc_degrees"] == pytest.approx(
        37.0687, abs=0.01
    )
    first_timeline = primary_directions["timeline"][0]
    natal_promissor_coordinate = primary_directions["coordinate_points"][
        first_timeline["promissor"]
    ]["coordinate_degrees"]
    assert (
        first_timeline["coordinate_context"]["promissor_current"]["coordinate_degrees"]
        == pytest.approx(
            (natal_promissor_coordinate - first_timeline["arc_degrees"]) % 360.0,
            abs=0.01,
        )
    )
    assert first_timeline["arc_applied_degrees"] == pytest.approx(
        -first_timeline["arc_degrees"],
        abs=0.01,
    )
    assert first_timeline["timing_phase"] == "past"
    assert first_timeline["relative_years_from_current"] < 0
    assert first_timeline["coordinate_context"]["current_orb_degrees"] == pytest.approx(
        0.0,
        abs=0.01,
    )

    primary_direction_chart = result["directions"]["primary_direction_chart"]
    assert primary_direction_chart["direction_mode"] == "converse"
    assert primary_direction_chart["bounds_overlay"]["enabled"] is True
    assert (
        primary_direction_chart["bounds_overlay"]["points"]["Sun"]["bound_lord"]
        == "Mars"
    )
    assert primary_direction_chart["directed_points"]["Sun"]["sign"] == "Aries"
    sun_sign_change = next(
        item
        for item in primary_direction_chart["sign_changes"]
        if item["point"] == "Sun"
    )
    assert sun_sign_change["from_sign"] == "Taurus"
    assert sun_sign_change["to_sign"] == "Aries"


def test_fastmcp_western_timing_tool_exposes_parameters():
    properties = western_timing_analysis.parameters["properties"]

    assert "birth_timezone" in properties
    assert "birth_longitude" in properties
    assert "birth_latitude" in properties
    assert "analysis_year" in properties
    assert "analysis_month" in properties
    assert "analysis_day" in properties
    assert "pd_method" in properties
    assert "pd_time_key" in properties
    assert "pd_type" in properties
    assert "pd_aspects" in properties
    assert "show_pd_bounds" in properties


def test_primary_direction_chart_omits_bounds_overlay_when_disabled():
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
        pd_method="astroapp_alchabitius",
        pd_time_key="Naibod",
        pd_aspects=[0, 90, 180],
        show_pd_bounds=False,
    )

    bounds_overlay = result["directions"]["primary_direction_chart"]["bounds_overlay"]

    assert bounds_overlay["system"] == "egyptian_bounds"
    assert bounds_overlay["enabled"] is False
    assert bounds_overlay["points"] == {}


def test_legacy_reference_primary_directions_use_right_ascension_arc():
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
        pd_method="legacy_reference",
        pd_time_key="Ptolemy",
        pd_aspects=[0, 90, 180],
        show_pd_bounds=True,
    )

    primary_directions = result["directions"]["primary_directions"]
    assert primary_directions["coordinate_system"] == "right_ascension"
    assert primary_directions["coordinate_label"] == "赤经"
    assert primary_directions["current_window"][0]["promissor"] == "Ascendant"
    assert primary_directions["current_window"][0]["significator"] == "Mercury"
    assert primary_directions["current_window"][0]["aspect"] == "opposition"
    assert primary_directions["current_window"][0]["arc_degrees"] == pytest.approx(
        33.5787, abs=0.01
    )

    primary_direction_chart = result["directions"]["primary_direction_chart"]
    assert primary_direction_chart["coordinate_system"] == "right_ascension"
    assert primary_direction_chart["coordinate_label"] == "赤经"


def test_legacy_equatorial_alias_matches_legacy_reference_coordinate_branch():
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
        pd_method="legacy_equatorial",
        pd_time_key="Ptolemy",
        pd_aspects=[0, 90, 180],
    )

    primary_directions = result["directions"]["primary_directions"]

    assert primary_directions["coordinate_system"] == "right_ascension"
    assert primary_directions["coordinate_label"] == "赤经"


def test_fatebridge_mundane_semiarc_method_exposes_mundane_projection():
    baseline_result = calculate_western_timing_analysis(
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
        pd_method="astroapp_alchabitius",
        pd_time_key="Ptolemy",
        pd_aspects=[0, 90, 180],
        show_pd_bounds=True,
    )
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
        pd_method="fatebridge_mundane_semiarc",
        pd_time_key="Ptolemy",
        pd_aspects=[0, 90, 180],
        show_pd_bounds=True,
    )

    primary_directions = result["directions"]["primary_directions"]
    assert primary_directions["coordinate_system"] == "mundane_semiarc"
    assert primary_directions["coordinate_label"] == "SemiArc"
    assert primary_directions["approximation"] == "mundane_semiarc_static_key"
    assert primary_directions["current_window"][0]["coordinate_system"] == "mundane_semiarc"
    first_timeline = primary_directions["timeline"][0]
    natal_promissor_coordinate = primary_directions["coordinate_points"][
        first_timeline["promissor"]
    ]["coordinate_degrees"]
    assert (
        first_timeline["coordinate_context"]["promissor_current"]["coordinate_degrees"]
        == pytest.approx(
            (natal_promissor_coordinate + first_timeline["arc_degrees"]) % 360.0,
            abs=0.01,
        )
    )
    assert first_timeline["arc_applied_degrees"] == pytest.approx(
        first_timeline["arc_degrees"],
        abs=0.01,
    )
    assert first_timeline["timing_phase"] == "past"
    assert first_timeline["relative_years_from_current"] < 0
    assert first_timeline["coordinate_context"]["current_orb_degrees"] == pytest.approx(
        0.0,
        abs=0.01,
    )
    assert (
        first_timeline["coordinate_context"]["promissor_current"]["quadrant"]
        in {
            "above_east",
            "above_west",
            "below_west",
            "below_east",
        }
    )
    assert (
        primary_directions["current_window"][0]["arc_degrees"]
        != baseline_result["directions"]["primary_directions"]["current_window"][0][
            "arc_degrees"
        ]
    )

    primary_direction_chart = result["directions"]["primary_direction_chart"]
    assert primary_direction_chart["coordinate_system"] == "mundane_semiarc"
    assert primary_direction_chart["coordinate_label"] == "SemiArc"
    assert primary_direction_chart["approximation"] == "mundane_semiarc_static_key"
    assert (
        primary_direction_chart["natal_coordinate_points"]["Ascendant"][
            "coordinate_degrees"
        ]
        == pytest.approx(0.0, abs=0.01)
    )
    assert (
        primary_direction_chart["directed_coordinate_points"]["Ascendant"][
            "coordinate_degrees"
        ]
        == pytest.approx(primary_direction_chart["current_arc_degrees"], abs=0.01)
    )
    assert (
        primary_direction_chart["directed_coordinate_points"]["Medium_Coeli"][
            "coordinate_degrees"
        ]
        == pytest.approx(
            (90.0 + primary_direction_chart["current_arc_degrees"]) % 360.0,
            abs=0.01,
        )
    )
    assert (
        primary_direction_chart["directed_coordinate_points"]["Ascendant"][
            "quadrant"
        ]
        == "above_east"
    )
    first_hit = primary_direction_chart["hits"][0]
    lot_key_by_point = {"Fortune": "lot_of_fortune", "Spirit": "lot_of_spirit"}
    significator_entry = primary_direction_chart["natal_coordinate_points"].get(
        first_hit["significator"]
    )
    if significator_entry is None:
        significator_entry = primary_direction_chart["natal_coordinate_lots"][
            lot_key_by_point[first_hit["significator"]]
        ]
    assert (
        first_hit["coordinate_context"]["promissor_current"]["coordinate_degrees"]
        == primary_direction_chart["directed_coordinate_points"][first_hit["promissor"]][
            "coordinate_degrees"
        ]
    )
    assert (
        first_hit["coordinate_context"]["significator_natal"]["coordinate_degrees"]
        == significator_entry["coordinate_degrees"]
    )
    assert (
        first_hit["coordinate_context"]["aspect_target"]["coordinate_degrees"]
        == pytest.approx(
            (
                significator_entry["coordinate_degrees"]
                + first_hit["aspect_variant_degrees"]
            )
            % 360.0,
            abs=0.01,
        )
    )
    assert first_hit["coordinate_context"]["current_orb_degrees"] >= 0
    assert (
        primary_direction_chart["coordinate_hits"][0]["coordinate_context"][
            "promissor_current"
        ]["coordinate_degrees"]
        == first_hit["coordinate_context"]["promissor_current"]["coordinate_degrees"]
    )
    assert (
        primary_direction_chart["coordinate_diagnostics"]["Ascendant"][
            "mundane_position_degrees"
        ]
        == pytest.approx(0.0, abs=0.01)
    )
    assert (
        primary_direction_chart["coordinate_diagnostics"]["Medium_Coeli"][
            "mundane_position_degrees"
        ]
        == pytest.approx(90.0, abs=0.01)
    )
    assert (
        primary_direction_chart["coordinate_diagnostics"]["Sun"]["semiarc_degrees"] > 0
    )
    assert primary_direction_chart["coordinate_diagnostics"]["Sun"]["quadrant"] in {
        "above_east",
        "above_west",
        "below_west",
        "below_east",
    }


def test_zodiacal_releasing_loosing_of_bond_jumps_after_full_cycle():
    start = datetime(2000, 1, 1)
    periods = build_releasing_level_within_interval(
        start_sign="Aquarius",
        period_start=start,
        period_end=start + timedelta(days=30 * 360),
        root_sign="Aquarius",
        parent_sign="Aquarius",
        level=2,
        analysis_datetime=start,
        max_periods=20,
    )

    signs = [period["sign"] for period in periods[:14]]
    loosing_flags = [period["loosing_of_bond"] for period in periods[:14]]

    assert signs[:12] == [
        "Aquarius",
        "Pisces",
        "Aries",
        "Taurus",
        "Gemini",
        "Cancer",
        "Leo",
        "Virgo",
        "Libra",
        "Scorpio",
        "Sagittarius",
        "Capricorn",
    ]
    assert signs[12:14] == ["Leo", "Virgo"]
    assert loosing_flags[6] is False
    assert loosing_flags[12] is True
