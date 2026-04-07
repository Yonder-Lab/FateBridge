from datetime import datetime
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import FateBridgeRequest, JieqiTimelineRequest, LiuriAnalysisRequest
from fastmcp_server import (
    analyze_destiny,
    jieqi_timeline_analysis,
    liuri_analysis,
    timing_analysis,
    two_person_compatibility,
)
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.timing import (
    calculate_comprehensive_timing,
    calculate_jieqi_timeline_analysis,
    calculate_liuri_analysis,
)
from fatebridge.utils.helpers import create_person_info, normalize_birth_time


def test_request_model_accepts_birth_time_precision_fields():
    request = FateBridgeRequest(
        name="张三",
        gender="男",
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        birth_longitude=116.4074,
        use_true_solar_time=True,
        birth_place="北京",
    )

    payload = request.model_dump()

    assert payload["birth_minute"] == 30
    assert payload["birth_timezone"] == "Asia/Shanghai"
    assert payload["birth_longitude"] == pytest.approx(116.4074)
    assert payload["use_true_solar_time"] is True


def test_timing_request_models_accept_analysis_fields():
    liuri_request = LiuriAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
    )
    jieqi_request = JieqiTimelineRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        target_year=2028,
    )

    liuri_payload = liuri_request.model_dump()
    jieqi_payload = jieqi_request.model_dump()

    assert liuri_payload["analysis_year"] == 2028
    assert liuri_payload["analysis_month"] == 4
    assert liuri_payload["analysis_day"] == 1
    assert jieqi_payload["target_year"] == 2028


def test_normalize_birth_time_preserves_legacy_hour_only_behavior():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        name="张三",
    )

    normalized = normalize_birth_time(person)

    assert normalized.input_datetime == datetime(1990, 5, 15, 10, 0)
    assert normalized.corrected_datetime == datetime(1990, 5, 15, 10, 0)
    assert normalized.total_correction_minutes == pytest.approx(0.0)
    assert normalized.applied is False


def test_normalize_birth_time_uses_birth_place_for_true_solar_time():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="北京",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.timezone == "Asia/Shanghai"
    assert normalized.longitude == pytest.approx(116.4074, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.corrected_datetime.hour == 10
    assert normalized.corrected_datetime.minute == 19
    assert normalized.total_correction_minutes == pytest.approx(-10.62, abs=0.1)
    assert normalized.applied is True


def test_normalize_birth_time_resolves_full_form_chinese_city_address():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="浙江省宁波市海曙区灵桥路190号",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.timezone == "Asia/Shanghai"
    assert normalized.longitude == pytest.approx(121.5503, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "宁波"
    assert normalized.resolution_level == "city"
    assert normalized.applied is True


def test_normalize_birth_time_supports_english_city_address():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="Haishu District, Ningbo, Zhejiang, China",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.longitude == pytest.approx(121.5503, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "宁波"
    assert normalized.resolution_level == "city"


def test_normalize_birth_time_supports_pinyin_city_address():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="zhejiang sheng hangzhou shi xihu qu wensan lu 138 hao",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.longitude == pytest.approx(120.1551, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "杭州"
    assert normalized.resolution_level == "city"


def test_normalize_birth_time_prefers_more_specific_city_match_over_province():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="浙江省杭州市西湖区文三路138号",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.longitude == pytest.approx(120.1551, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "杭州"
    assert normalized.resolution_level == "city"


def test_normalize_birth_time_falls_back_to_province_when_city_is_unknown():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="河北省保定市莲池区东风东路",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.longitude == pytest.approx(114.5149, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "河北"
    assert normalized.resolution_level == "province"


def test_normalize_birth_time_supports_english_province_fallback():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_place="Lianchi District, Baoding, Hebei, China",
        use_true_solar_time=True,
    )

    normalized = normalize_birth_time(person)

    assert normalized.longitude == pytest.approx(114.5149, abs=0.01)
    assert normalized.longitude_source == "birth_place"
    assert normalized.resolved_place == "河北"
    assert normalized.resolution_level == "province"


def test_calculate_destiny_analysis_uses_corrected_solar_time_for_hour_pillar():
    person = create_person_info(
        birth_year=2020,
        birth_month=1,
        birth_day=1,
        birth_hour=0,
        birth_minute=30,
        birth_place="乌鲁木齐",
        use_true_solar_time=True,
        name="测试",
    )

    result = calculate_destiny_analysis(person)

    assert result["person_info"]["birth_datetime"] == "2020年01月01日 00时30分"
    assert result["person_info"]["normalized_birth_datetime"] == "2019年12月31日 22时16分"
    assert result["person_info"]["time_adjustment"]["applied"] is True
    assert result["person_info"]["time_adjustment"]["timezone"] == "Asia/Shanghai"
    assert result["person_info"]["time_adjustment"]["longitude_source"] == "birth_place"
    assert result["person_info"]["time_adjustment"]["resolved_place"] == "乌鲁木齐"
    assert result["person_info"]["time_adjustment"]["resolution_level"] == "city"
    assert result["four_pillars"]["hour"]["branch"] == "亥"


def test_calculate_comprehensive_timing_uses_corrected_birth_time():
    person = create_person_info(
        birth_year=2020,
        birth_month=1,
        birth_day=1,
        birth_hour=0,
        birth_minute=30,
        birth_place="乌鲁木齐",
        use_true_solar_time=True,
        name="测试",
    )

    result = calculate_comprehensive_timing(
        person, analysis_year=2020, analysis_month=1
    )

    assert result["personal_info"]["birth_datetime"] == "2020-01-01 00:30"
    assert result["personal_info"]["normalized_birth_datetime"] == "2019-12-31 22:16"
    assert result["personal_info"]["time_adjustment"]["applied"] is True
    assert result["personal_info"]["time_adjustment"]["resolved_place"] == "乌鲁木齐"
    assert result["personal_info"]["time_adjustment"]["resolution_level"] == "city"
    assert result["birth_pillars"]["hour"]["branch"] == "亥"


def test_calculate_liuri_analysis_returns_expected_pillar():
    person = create_person_info(
        birth_year=2028,
        birth_month=4,
        birth_day=6,
        birth_hour=9,
        birth_minute=33,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    result = calculate_liuri_analysis(
        person, analysis_year=2028, analysis_month=4, analysis_day=1
    )

    assert result["liuri_info"]["pillar"] == "丙辰"
    assert result["analysis_calendar"]["analysis_date_context"]["current_solar_term"]["name"] == "春分"


def test_calculate_jieqi_timeline_analysis_returns_qingming_node():
    person = create_person_info(
        birth_year=2028,
        birth_month=4,
        birth_day=6,
        birth_hour=9,
        birth_minute=33,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    result = calculate_jieqi_timeline_analysis(person, target_year=2028)

    assert len(result["jieqi_timeline"]) == 24
    qingming_node = next(
        item for item in result["jieqi_timeline"] if item["jieqi"]["name"] == "清明"
    )
    assert qingming_node["liuyue"]["pillar"] == "丙辰"
    assert qingming_node["liuri"]["pillar"] == "己未"


def test_fastmcp_tools_expose_birth_time_precision_arguments():
    analyze_properties = analyze_destiny.parameters["properties"]
    compatibility_properties = two_person_compatibility.parameters["properties"]
    timing_properties = timing_analysis.parameters["properties"]
    liuri_properties = liuri_analysis.parameters["properties"]
    jieqi_properties = jieqi_timeline_analysis.parameters["properties"]

    assert "birth_minute" in analyze_properties
    assert "birth_timezone" in analyze_properties
    assert "birth_longitude" in analyze_properties
    assert "use_true_solar_time" in analyze_properties

    assert "person1_birth_minute" in compatibility_properties
    assert "person2_birth_minute" in compatibility_properties
    assert "person1_birth_timezone" in compatibility_properties
    assert "person2_birth_timezone" in compatibility_properties
    assert "person1_birth_longitude" in compatibility_properties
    assert "person2_birth_longitude" in compatibility_properties
    assert "use_true_solar_time" in timing_properties
    assert "analysis_year" in liuri_properties
    assert "analysis_month" in liuri_properties
    assert "analysis_day" in liuri_properties
    assert "target_year" in jieqi_properties
