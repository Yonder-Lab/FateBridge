from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.core.almanac import get_bazi_month_context, get_solar_terms_for_year
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.timing import TimingAnalysis
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.timing import calculate_comprehensive_timing
from fatebridge.utils.helpers import create_person_info


def test_lichun_boundary_updates_bazi_year_and_month():
    terms = {
        term.name: term
        for term in get_solar_terms_for_year(2024, "Asia/Shanghai")
    }
    li_chun = terms["立春"].moment

    before = li_chun - timedelta(minutes=1)
    after = li_chun + timedelta(minutes=1)

    before_pillars = BaZiCalendar.get_four_pillars(
        before, timezone_name="Asia/Shanghai"
    )
    after_pillars = BaZiCalendar.get_four_pillars(
        after, timezone_name="Asia/Shanghai"
    )

    assert before_pillars["year"] == ("癸", "卯")
    assert before_pillars["month"] == ("乙", "丑")
    assert get_bazi_month_context(before, "Asia/Shanghai")["branch"] == "丑"

    assert after_pillars["year"] == ("甲", "辰")
    assert after_pillars["month"] == ("丙", "寅")
    assert get_bazi_month_context(after, "Asia/Shanghai")["branch"] == "寅"


def test_dayun_start_details_use_jieqi_boundary():
    birth = datetime(2028, 4, 6, 9, 33)
    pillars = BaZiCalendar.get_four_pillars(birth, timezone_name="Asia/Shanghai")

    details = TimingAnalysis.calculate_dayun_start_details(
        birth,
        pillars["month"][0],
        "男",
        timezone_name="Asia/Shanghai",
    )

    assert details["forward_direction"] is True
    assert details["year_stem"] == "戊"
    assert details["reference_term"]["name"] == "立夏"
    assert details["start_age_precise"] == pytest.approx(9.76, abs=0.05)
    assert details["start_age_rounded"] == 10


def test_destiny_analysis_exposes_lunar_and_meihua_context():
    person = create_person_info(
        2028,
        4,
        6,
        9,
        "测试",
        "男",
        birth_minute=33,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_destiny_analysis(person)
    calendar_context = result["calendar_context"]
    lunar_calendar = calendar_context["lunar_calendar"]
    meihua = lunar_calendar["meihua"]

    assert calendar_context["current_solar_term"]["name"] == "清明"
    assert lunar_calendar["display"] == "三月十二"
    assert meihua["base_hexagram"]["name"] == "地水师"
    assert meihua["changed_hexagram"]["name"] == "山水蒙"


def test_comprehensive_timing_returns_jieqi_grid_and_analysis_calendar():
    person = create_person_info(
        2028,
        4,
        6,
        9,
        "测试",
        "男",
        birth_minute=33,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_comprehensive_timing(
        person, analysis_year=2028, analysis_month=4
    )

    assert (
        result["calendar_context"]["lunar_calendar"]["meihua"]["base_hexagram"][
            "name"
        ]
        == "地水师"
    )
    assert (
        result["analysis_calendar"]["analysis_date_context"]["current_solar_term"][
            "name"
        ]
        == "春分"
    )
    assert (
        result["analysis_calendar"]["analysis_date_context"]["next_solar_term"]["name"]
        == "清明"
    )
    assert result["liuyue_analysis"]["pillar"] == "乙卯"
    assert result["liuri_analysis"]["pillar"] == "丙辰"
    assert len(result["analysis_calendar"]["analysis_year_jieqi"]) == 24
    assert result["analysis_calendar"]["analysis_year_jieqi"][0]["name"] == "小寒"
    assert len(result["analysis_calendar"]["liuyue_timeline"]) == 12
    assert result["analysis_calendar"]["liuyue_timeline"][1]["start_term"]["name"] == "立春"
    assert result["analysis_calendar"]["liuyue_timeline"][1]["liuyue"]["pillar"] == "甲寅"
    assert len(result["analysis_calendar"]["jieqi_timeline"]) == 24
    qingming_node = next(
        item
        for item in result["analysis_calendar"]["jieqi_timeline"]
        if item["jieqi"]["name"] == "清明"
    )
    assert qingming_node["liuyue"]["pillar"] == "丙辰"
    assert qingming_node["liuri"]["pillar"] == "己未"
