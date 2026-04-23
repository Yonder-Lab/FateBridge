import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    DayunAnalysisRequest,
    FateBridgeRequest,
    JieqiTimelineRequest,
    LiunianAnalysisRequest,
    LiuriAnalysisRequest,
    LiushiAnalysisRequest,
    LiuyueAnalysisRequest,
    TimingAnalysisRequest,
)
from fastmcp_server import (
    analyze_destiny,
    dayun_analysis,
    jieqi_timeline_analysis,
    liunian_analysis,
    liuri_analysis,
    liushi_analysis,
    liuyue_analysis,
    timing_analysis,
    two_person_compatibility,
)
from fatebridge.core.timing import TimingAnalysis
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.timing import (
    calculate_comprehensive_timing,
    calculate_dayun_analysis,
    calculate_jieqi_timeline_analysis,
    calculate_liunian_analysis,
    calculate_liuri_analysis,
    calculate_liushi_analysis,
    calculate_liuyue_analysis,
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
    timing_request = TimingAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=21,
        analysis_minute=55,
        analysis_age=38,
        selected_sections=["查询信息", "综合影响"],
    )
    dayun_request = DayunAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        gender="男",
        analysis_age=38,
        selected_sections=["查询信息", "大运信息"],
    )
    liunian_request = LiunianAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        target_year=2028,
        selected_sections=["查询信息", "流年信息"],
    )
    liuyue_request = LiuyueAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=21,
        analysis_minute=55,
        selected_sections=["查询信息", "流月信息"],
    )
    liuri_request = LiuriAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=21,
        analysis_minute=55,
    )
    liushi_request = LiushiAnalysisRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=21,
        analysis_minute=55,
        selected_sections=["查询信息", "流时信息"],
    )
    jieqi_request = JieqiTimelineRequest(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        target_year=2028,
        selected_sections=["查询信息", "节点时间轴"],
    )

    timing_payload = timing_request.model_dump()
    dayun_payload = dayun_request.model_dump()
    liunian_payload = liunian_request.model_dump()
    liuyue_payload = liuyue_request.model_dump()
    liuri_payload = liuri_request.model_dump()
    liushi_payload = liushi_request.model_dump()
    jieqi_payload = jieqi_request.model_dump()

    assert timing_payload["analysis_year"] == 2028
    assert timing_payload["analysis_month"] == 4
    assert timing_payload["analysis_day"] == 6
    assert timing_payload["analysis_hour"] == 21
    assert timing_payload["analysis_minute"] == 55
    assert timing_payload["analysis_age"] == 38
    assert timing_payload["selected_sections"] == ["查询信息", "综合影响"]
    assert dayun_payload["gender"] == "男"
    assert dayun_payload["analysis_age"] == 38
    assert dayun_payload["selected_sections"] == ["查询信息", "大运信息"]
    assert liunian_payload["target_year"] == 2028
    assert liunian_payload["selected_sections"] == ["查询信息", "流年信息"]
    assert liuyue_payload["analysis_year"] == 2028
    assert liuyue_payload["analysis_month"] == 4
    assert liuyue_payload["analysis_day"] == 1
    assert liuyue_payload["analysis_hour"] == 21
    assert liuyue_payload["analysis_minute"] == 55
    assert liuyue_payload["selected_sections"] == ["查询信息", "流月信息"]
    assert liuri_payload["analysis_year"] == 2028
    assert liuri_payload["analysis_month"] == 4
    assert liuri_payload["analysis_day"] == 1
    assert liuri_payload["analysis_hour"] == 21
    assert liuri_payload["analysis_minute"] == 55
    assert liushi_payload["analysis_year"] == 2028
    assert liushi_payload["analysis_month"] == 4
    assert liushi_payload["analysis_day"] == 1
    assert liushi_payload["analysis_hour"] == 21
    assert liushi_payload["analysis_minute"] == 55
    assert liushi_payload["selected_sections"] == ["查询信息", "流时信息"]
    assert jieqi_payload["target_year"] == 2028
    assert jieqi_payload["selected_sections"] == ["查询信息", "节点时间轴"]


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
    # 1990-05-15 于中国夏令时期 (CDT, UTC+9)，钟表 10:30 实际对应 CST 09:30。
    # 真太阳时修正应先脱 DST 再做 longitude + EoT 校正：
    #   09:30 + (-14.37) + 3.75 ≈ 09:19
    assert normalized.corrected_datetime.hour == 9
    assert normalized.corrected_datetime.minute == 19
    assert normalized.daylight_saving_minutes == pytest.approx(60.0, abs=0.1)
    assert normalized.total_correction_minutes == pytest.approx(-70.62, abs=0.1)
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
    assert (
        result["person_info"]["normalized_birth_datetime"] == "2019年12月31日 22时16分"
    )
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


def test_calculate_comprehensive_timing_supports_snapshot_export_and_age_override():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    result = calculate_comprehensive_timing(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=21,
        analysis_minute=55,
        analysis_age=42,
        selected_sections=["查询信息", "综合影响"],
    )
    dayun_result = calculate_dayun_analysis(person, 42)

    assert result["personal_info"]["current_age"] == 42
    assert result["personal_info"]["analysis_date"] == "2028-04-06"
    assert result["personal_info"]["analysis_datetime"] == "2028-04-06 21:55"
    assert (
        result["dayun_analysis"]["current_dayun"]
        == dayun_result["dayun_info"]["current_dayun"]
    )
    assert "[查询信息]" in result["snapshot_text"]
    assert "[大运摘要]" in result["snapshot_text"]
    assert "[流年流月流日]" in result["snapshot_text"]
    assert "[综合影响]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "综合影响"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[综合影响]" in result["snapshot_export"]["export_text"]
    assert "[大运摘要]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_comprehensive_timing_supports_analysis_day_boundaries():
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

    timing_result = calculate_comprehensive_timing(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )
    liuyue_result = calculate_liuyue_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )
    liuri_result = calculate_liuri_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )

    assert timing_result["personal_info"]["analysis_date"] == "2028-04-06"
    assert (
        timing_result["analysis_calendar"]["analysis_date_context"][
            "current_solar_term"
        ]["name"]
        == "清明"
    )
    assert (
        timing_result["analysis_calendar"]["analysis_date_context"]["next_solar_term"][
            "name"
        ]
        == "谷雨"
    )
    assert timing_result["liuyue_analysis"]["pillar"] == "丙辰"
    assert timing_result["liuri_analysis"]["pillar"] == "辛酉"
    assert (
        timing_result["liuyue_analysis"]["pillar"]
        == liuyue_result["liuyue_info"]["pillar"]
    )
    assert (
        timing_result["liuri_analysis"]["pillar"]
        == liuri_result["liuri_info"]["pillar"]
    )


def test_time_precision_changes_liuyue_across_qingming_boundary():
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
    qingming_node = next(
        item
        for item in TimingAnalysis.calculate_jieqi_transition_timeline(
            2028, timezone_name="Asia/Shanghai"
        )
        if item["jieqi"]["name"] == "清明"
    )

    before_result = calculate_liuyue_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=4,
    )
    boundary_result = calculate_liuyue_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=55,
    )

    assert before_result["liuyue_info"]["pillar"] == "乙卯"
    assert (
        before_result["analysis_calendar"]["analysis_date_context"][
            "current_solar_term"
        ]["name"]
        == "春分"
    )
    assert boundary_result["liuyue_info"]["pillar"] == qingming_node["liuyue"]["pillar"]
    assert (
        boundary_result["analysis_calendar"]["analysis_date_context"][
            "current_solar_term"
        ]["name"]
        == "清明"
    )
    assert (
        boundary_result["analysis_calendar"]["analysis_date_context"][
            "next_solar_term"
        ]["name"]
        == "谷雨"
    )


def test_time_precision_aligns_liuri_and_timing_with_jieqi_anchor():
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
    qingming_node = next(
        item
        for item in TimingAnalysis.calculate_jieqi_transition_timeline(
            2028, timezone_name="Asia/Shanghai"
        )
        if item["jieqi"]["name"] == "清明"
    )

    liuri_result = calculate_liuri_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=55,
    )
    timing_result = calculate_comprehensive_timing(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=55,
    )

    assert liuri_result["liuri_info"]["pillar"] == qingming_node["liuri"]["pillar"]
    assert (
        liuri_result["analysis_calendar"]["analysis_date_context"][
            "current_solar_term"
        ]["name"]
        == "清明"
    )
    assert timing_result["personal_info"]["analysis_datetime"] == "2028-04-04 21:55"
    assert (
        timing_result["liuyue_analysis"]["pillar"] == qingming_node["liuyue"]["pillar"]
    )
    assert timing_result["liuri_analysis"]["pillar"] == qingming_node["liuri"]["pillar"]
    assert (
        timing_result["analysis_calendar"]["analysis_date_context"][
            "current_solar_term"
        ]["name"]
        == "清明"
    )


def test_calculate_dayun_analysis_supports_snapshot_export():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    result = calculate_dayun_analysis(person, 38)

    assert "current_dayun" in result["dayun_info"]
    assert "[查询信息]" in result["snapshot_text"]
    assert "[大运信息]" in result["snapshot_text"]
    assert "[影响摘要]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_dayun_analysis_supports_selected_export_sections():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    result = calculate_dayun_analysis(
        person,
        38,
        selected_sections=["查询信息", "大运信息"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "大运信息"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[大运信息]" in result["snapshot_export"]["export_text"]
    assert "[影响摘要]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


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
    assert (
        result["analysis_calendar"]["analysis_date_context"]["current_solar_term"][
            "name"
        ]
        == "春分"
    )
    assert "[查询信息]" in result["snapshot_text"]
    assert "[流日信息]" in result["snapshot_text"]
    assert "[影响摘要]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liuri_analysis_supports_selected_export_sections():
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
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        selected_sections=["查询信息", "流日信息"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "流日信息"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[流日信息]" in result["snapshot_export"]["export_text"]
    assert "[影响摘要]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_liushi_analysis_returns_expected_pillar():
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
    analysis_dt = datetime(2028, 4, 1, 21, 55)

    result = calculate_liushi_analysis(
        person,
        analysis_year=analysis_dt.year,
        analysis_month=analysis_dt.month,
        analysis_day=analysis_dt.day,
        analysis_hour=analysis_dt.hour,
        analysis_minute=analysis_dt.minute,
    )
    expected_liushi = TimingAnalysis.calculate_liushi(
        analysis_dt,
        timezone_name="Asia/Shanghai",
    )

    assert result["liushi_info"]["pillar"] == expected_liushi["pillar"]
    assert result["liushi_info"]["hour"] == 21
    assert (
        result["analysis_calendar"]["analysis_date_context"]["current_solar_term"][
            "name"
        ]
        == "春分"
    )
    assert "[查询信息]" in result["snapshot_text"]
    assert "[流时信息]" in result["snapshot_text"]
    assert "[影响摘要]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liushi_analysis_supports_selected_export_sections():
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

    result = calculate_liushi_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=21,
        analysis_minute=55,
        selected_sections=["查询信息", "流时信息"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "流时信息"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[流时信息]" in result["snapshot_export"]["export_text"]
    assert "[影响摘要]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_liunian_analysis_supports_snapshot_export():
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

    result = calculate_liunian_analysis(
        person,
        2028,
    )

    assert result["liunian_info"]["pillar"] == "戊申"
    assert "[查询信息]" in result["snapshot_text"]
    assert "[流年信息]" in result["snapshot_text"]
    assert "[影响摘要]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liunian_analysis_supports_selected_export_sections():
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

    result = calculate_liunian_analysis(
        person,
        2028,
        selected_sections=["查询信息", "流年信息"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "流年信息"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[流年信息]" in result["snapshot_export"]["export_text"]
    assert "[影响摘要]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_liuyue_analysis_returns_expected_pillar():
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

    result = calculate_liuyue_analysis(
        person, analysis_year=2028, analysis_month=4, analysis_day=1
    )

    assert result["liuyue_info"]["pillar"] == "乙卯"
    assert result["liuyue_info"]["solar_term_window"]["start_term"]["name"] == "惊蛰"
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
    assert result["liunian_info"]["pillar"] == "戊申"
    assert "[查询信息]" in result["snapshot_text"]
    assert "[流月信息]" in result["snapshot_text"]
    assert "[流年联动]" in result["snapshot_text"]
    assert "[影响摘要]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liuyue_analysis_supports_selected_export_sections():
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

    result = calculate_liuyue_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        selected_sections=["查询信息", "流月信息"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "流月信息"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[流月信息]" in result["snapshot_export"]["export_text"]
    assert "[流年联动]" not in result["snapshot_export"]["export_text"]
    assert "[影响摘要]" not in result["snapshot_export"]["export_text"]


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
    assert qingming_node["analysis_anchor"] == "2028-04-04 14:04:00"
    assert qingming_node["liuyue"]["pillar"] == "丙辰"
    assert qingming_node["liuri"]["pillar"] == "己未"
    assert "[查询信息]" in result["snapshot_text"]
    assert "[年度节气]" in result["snapshot_text"]
    assert "[节点时间轴]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_jieqi_timeline_analysis_supports_selected_export_sections():
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

    result = calculate_jieqi_timeline_analysis(
        person,
        target_year=2028,
        selected_sections=["查询信息", "节点时间轴"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "节点时间轴"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[节点时间轴]" in result["snapshot_export"]["export_text"]
    assert "[年度节气]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_liuyue_timeline_anchor_is_minute_safe_and_replayable():
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

    timeline = TimingAnalysis.calculate_liuyue_timeline(
        2028, timezone_name="Asia/Shanghai"
    )

    for item in timeline:
        anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
        start_term = datetime.strptime(
            item["start_term"]["datetime"], "%Y-%m-%d %H:%M:%S"
        )
        assert anchor.second == 0
        assert timedelta(0) < anchor - start_term <= timedelta(minutes=1)

    qingming_month = next(
        item for item in timeline if item["start_term"]["name"] == "清明"
    )
    anchor = datetime.strptime(qingming_month["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
    liuyue_result = calculate_liuyue_analysis(
        person,
        analysis_year=anchor.year,
        analysis_month=anchor.month,
        analysis_day=anchor.day,
        analysis_hour=anchor.hour,
        analysis_minute=anchor.minute,
    )

    assert qingming_month["analysis_anchor"] == "2028-04-04 14:04:00"
    assert liuyue_result["liuyue_info"]["pillar"] == qingming_month["liuyue"]["pillar"]
    assert (
        liuyue_result["liuyue_info"]["solar_term_window"]["start_term"]["name"]
        == "清明"
    )


def test_jieqi_timeline_anchor_is_minute_safe_and_replayable():
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

    timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
        2028, timezone_name="Asia/Shanghai"
    )
    sample_names = {"清明", "立秋", "冬至"}

    for item in timeline:
        anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
        term = datetime.strptime(item["jieqi"]["datetime"], "%Y-%m-%d %H:%M:%S")
        assert anchor.second == 0
        assert timedelta(0) < anchor - term <= timedelta(minutes=1)

        if item["jieqi"]["name"] not in sample_names:
            continue

        liuyue_result = calculate_liuyue_analysis(
            person,
            analysis_year=anchor.year,
            analysis_month=anchor.month,
            analysis_day=anchor.day,
            analysis_hour=anchor.hour,
            analysis_minute=anchor.minute,
        )
        liuri_result = calculate_liuri_analysis(
            person,
            analysis_year=anchor.year,
            analysis_month=anchor.month,
            analysis_day=anchor.day,
            analysis_hour=anchor.hour,
            analysis_minute=anchor.minute,
        )
        timing_result = calculate_comprehensive_timing(
            person,
            analysis_year=anchor.year,
            analysis_month=anchor.month,
            analysis_day=anchor.day,
            analysis_hour=anchor.hour,
            analysis_minute=anchor.minute,
        )

        assert liuyue_result["liuyue_info"]["pillar"] == item["liuyue"]["pillar"]
        assert liuri_result["liuri_info"]["pillar"] == item["liuri"]["pillar"]
        assert timing_result["liuyue_analysis"]["pillar"] == item["liuyue"]["pillar"]
        assert timing_result["liuri_analysis"]["pillar"] == item["liuri"]["pillar"]


def test_comprehensive_timing_matches_specialized_timing_tools():
    person = create_person_info(
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        name="测试",
        gender="男",
    )

    timing_result = calculate_comprehensive_timing(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_age=42,
    )
    dayun_result = calculate_dayun_analysis(person, 42)
    liunian_result = calculate_liunian_analysis(person, 2028)
    liuyue_result = calculate_liuyue_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )
    liuri_result = calculate_liuri_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )
    liushi_result = calculate_liushi_analysis(
        person,
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=0,
        analysis_minute=0,
    )

    assert (
        timing_result["dayun_analysis"]["current_dayun"]
        == dayun_result["dayun_info"]["current_dayun"]
    )
    assert (
        timing_result["dayun_analysis"]["start_age"]
        == dayun_result["dayun_info"]["start_age"]
    )
    assert (
        timing_result["dayun_analysis"]["dayun_age"]
        == dayun_result["dayun_info"]["dayun_age"]
    )
    assert (
        timing_result["liunian_analysis"]["pillar"]
        == liunian_result["liunian_info"]["pillar"]
    )
    assert (
        timing_result["liuyue_analysis"]["pillar"]
        == liuyue_result["liuyue_info"]["pillar"]
    )
    assert (
        timing_result["liuri_analysis"]["pillar"]
        == liuri_result["liuri_info"]["pillar"]
    )
    assert (
        timing_result["liushi_analysis"]["pillar"]
        == liushi_result["liushi_info"]["pillar"]
    )


def test_fastmcp_tools_expose_birth_time_precision_arguments():
    analyze_properties = analyze_destiny.parameters["properties"]
    compatibility_properties = two_person_compatibility.parameters["properties"]
    timing_properties = timing_analysis.parameters["properties"]
    dayun_properties = dayun_analysis.parameters["properties"]
    liunian_properties = liunian_analysis.parameters["properties"]
    liuyue_properties = liuyue_analysis.parameters["properties"]
    liuri_properties = liuri_analysis.parameters["properties"]
    liushi_properties = liushi_analysis.parameters["properties"]
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
    assert "analysis_day" in timing_properties
    assert "analysis_hour" in timing_properties
    assert "analysis_minute" in timing_properties
    assert "selected_sections" in timing_properties
    assert "selected_sections" in dayun_properties
    assert "selected_sections" in liunian_properties
    assert "analysis_year" in liuyue_properties
    assert "analysis_month" in liuyue_properties
    assert "analysis_day" in liuyue_properties
    assert "analysis_hour" in liuyue_properties
    assert "analysis_minute" in liuyue_properties
    assert "selected_sections" in liuyue_properties
    assert "analysis_year" in liuri_properties
    assert "analysis_month" in liuri_properties
    assert "analysis_day" in liuri_properties
    assert "analysis_hour" in liuri_properties
    assert "analysis_minute" in liuri_properties
    assert "selected_sections" in liuri_properties
    assert "analysis_year" in liushi_properties
    assert "analysis_month" in liushi_properties
    assert "analysis_day" in liushi_properties
    assert "analysis_hour" in liushi_properties
    assert "analysis_minute" in liushi_properties
    assert "selected_sections" in liushi_properties
    assert "target_year" in jieqi_properties
    assert "selected_sections" in jieqi_properties
