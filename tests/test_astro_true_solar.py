"""Western natal charts default to true solar time (consistent with BaZi).

The correction reuses the BaZi engine's ``calculate_solar_time_adjustment``
(longitude + equation of time), so a birth feeds one shared solar instant into
both the Chinese and western charts.
"""

from __future__ import annotations

from datetime import datetime

from fatebridge.services.astrology import calculate_core_chart_analysis
from fatebridge.utils.helpers import (
    SOLAR_TIME_STRATEGY_APPARENT,
    calculate_solar_time_adjustment,
)

_BIRTH = dict(
    name="左右",
    birth_year=2000,
    birth_month=12,
    birth_day=10,
    birth_hour=9,
    birth_minute=55,
    birth_timezone="Asia/Shanghai",
    birth_longitude=120.45,
    birth_latitude=32.54,
    chart_variant="chart",
)


def test_true_solar_is_on_by_default():
    result = calculate_core_chart_analysis(**_BIRTH)
    ts = result["person_info"]["true_solar"]
    assert ts["applied"] is True
    assert ts["correction_minutes"] != 0.0


def test_true_solar_opt_out_uses_raw_clock():
    result = calculate_core_chart_analysis(**_BIRTH, use_true_solar_time=False)
    ts = result["person_info"]["true_solar"]
    assert ts["applied"] is False
    assert ts["correction_minutes"] == 0.0
    assert result["person_info"]["birth_datetime"].startswith("2000-12-10T09:55")


def test_correction_matches_bazi_helper_single_source():
    expected = calculate_solar_time_adjustment(
        datetime(2000, 12, 10, 9, 55),
        "Asia/Shanghai",
        120.45,
        strategy=SOLAR_TIME_STRATEGY_APPARENT,
    )["total_correction_minutes"]
    result = calculate_core_chart_analysis(**_BIRTH)
    assert result["person_info"]["true_solar"]["correction_minutes"] == round(
        expected, 4
    )


def test_core_chart_request_default_timezone_is_none():
    # The 'UTC' default belonged to the request-model layer (REST/MCP/CLI):
    # Pydantic filled birth_timezone='UTC' when omitted, pre-empting the
    # place-based inference in build_astro_birth_info. The core chart model must
    # default to None so an omitted timezone falls through to the birth place.
    from fatebridge.core.request_models import AstroChartRequest

    req = AstroChartRequest(
        birth_year=2000, birth_month=12, birth_day=10, birth_hour=9, birth_place="上海"
    )
    assert req.birth_timezone is None


def test_omitted_timezone_uses_birth_place_not_utc():
    # End-to-end through the request layer: a known birth place with no timezone
    # must infer the place's timezone (as BaZi does), not fall back to 'UTC' and
    # rotate the whole chart.
    from fatebridge.core.request_models import AstroChartRequest

    req = AstroChartRequest(
        birth_year=2000,
        birth_month=12,
        birth_day=10,
        birth_hour=9,
        birth_minute=55,
        birth_place="上海",
        birth_longitude=121.47,
        birth_latitude=31.23,
    )
    result = calculate_core_chart_analysis(**req.model_dump())
    assert result["person_info"]["birth_timezone"] == "Asia/Shanghai"
    assert result["person_info"]["utc_datetime"].startswith("2000-12-10T0")


def test_true_solar_shifts_birth_instant_and_positions():
    on = calculate_core_chart_analysis(**_BIRTH)
    off = calculate_core_chart_analysis(**_BIRTH, use_true_solar_time=False)
    # Corrected clock is later than the raw 09:55 (east of the standard meridian).
    assert on["person_info"]["birth_datetime"] > off["person_info"]["birth_datetime"]
    sun_on = next(p for p in on["planets"] if p["id"] == "Sun")["longitude"]
    sun_off = next(p for p in off["planets"] if p["id"] == "Sun")["longitude"]
    assert sun_on != sun_off
