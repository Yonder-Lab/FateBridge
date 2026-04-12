import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api as api_module
from api import (
    AstroChartRequest,
    AstroRelativePartyRequest,
    AstroRelativeRequest,
    DayunAnalysisRequest,
    LiunianAnalysisRequest,
    TimingAnalysisRequest,
    TwoPersonCompatibilityRequest,
    WesternTimingModuleRequest,
    WesternTimingRequest,
    calculate_astro_chart,
    calculate_dayun,
    calculate_liunian,
    calculate_relative_chart,
    calculate_solarreturn_module,
    calculate_timing_analysis,
    calculate_two_person_compatibility,
    calculate_western_timing,
)
from fastmcp_server import (
    astro_chart,
    astro_relative_chart,
    dayun_analysis,
    liunian_analysis,
    timing_analysis,
    two_person_compatibility,
)


def _build_birth_payload(name: str, gender: str, birth_place: str) -> dict:
    return {
        "name": name,
        "gender": gender,
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 15,
        "birth_hour": 10,
        "birth_minute": 30,
        "birth_timezone": "Asia/Shanghai",
        "birth_longitude": 121.4737,
        "birth_place": birth_place,
        "use_true_solar_time": False,
    }


def test_alignment_request_models_accept_fastmcp_offline_fields():
    compatibility_request = TwoPersonCompatibilityRequest(
        person1_name="甲",
        person1_birth_year=1990,
        person1_birth_month=5,
        person1_birth_day=15,
        person1_birth_hour=10,
        person1_gender="男",
        person1_birth_place="上海",
        person1_birth_minute=30,
        person1_birth_timezone="Asia/Shanghai",
        person1_birth_longitude=121.4737,
        person2_name="乙",
        person2_birth_year=1992,
        person2_birth_month=3,
        person2_birth_day=2,
        person2_birth_hour=8,
        person2_gender="女",
        person2_birth_place="北京",
        person2_birth_minute=18,
        person2_birth_timezone="Asia/Shanghai",
        person2_birth_longitude=116.4074,
        relationship_type="marriage",
    )
    timing_request = TimingAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=21,
        analysis_minute=55,
        analysis_age=38,
        selected_sections=["查询信息", "综合影响"],
    )
    dayun_request = DayunAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        analysis_age=38,
        selected_sections=["查询信息", "大运信息"],
    )
    liunian_request = LiunianAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        target_year=2028,
    )

    compatibility_payload = compatibility_request.model_dump()
    timing_payload = timing_request.model_dump()
    dayun_payload = dayun_request.model_dump()
    liunian_payload = liunian_request.model_dump()

    assert compatibility_payload["person1_birth_minute"] == 30
    assert compatibility_payload["person2_birth_timezone"] == "Asia/Shanghai"
    assert compatibility_payload["person2_birth_longitude"] == 116.4074
    assert compatibility_payload["relationship_type"] == "marriage"
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


def test_two_person_compatibility_api_matches_fastmcp_tool_output():
    request = TwoPersonCompatibilityRequest(
        person1_name="甲",
        person1_birth_year=1990,
        person1_birth_month=5,
        person1_birth_day=15,
        person1_birth_hour=10,
        person1_gender="男",
        person1_birth_place="上海",
        person1_birth_minute=30,
        person1_birth_timezone="Asia/Shanghai",
        person1_birth_longitude=121.4737,
        person2_name="乙",
        person2_birth_year=1992,
        person2_birth_month=3,
        person2_birth_day=2,
        person2_birth_hour=8,
        person2_gender="女",
        person2_birth_place="北京",
        person2_birth_minute=18,
        person2_birth_timezone="Asia/Shanghai",
        person2_birth_longitude=116.4074,
        relationship_type="marriage",
    )

    api_result = asyncio.run(calculate_two_person_compatibility(request))
    mcp_result = json.loads(two_person_compatibility.fn(**request.model_dump()))

    assert api_result == mcp_result


def test_two_person_compatibility_exposes_structured_pattern_fields():
    request = TwoPersonCompatibilityRequest(
        person1_name="甲",
        person1_birth_year=1990,
        person1_birth_month=5,
        person1_birth_day=15,
        person1_birth_hour=10,
        person1_gender="男",
        person1_birth_place="上海",
        person1_birth_minute=30,
        person1_birth_timezone="Asia/Shanghai",
        person1_birth_longitude=121.4737,
        person2_name="乙",
        person2_birth_year=1992,
        person2_birth_month=3,
        person2_birth_day=2,
        person2_birth_hour=8,
        person2_gender="女",
        person2_birth_place="北京",
        person2_birth_minute=18,
        person2_birth_timezone="Asia/Shanghai",
        person2_birth_longitude=116.4074,
        relationship_type="marriage",
    )

    api_result = asyncio.run(calculate_two_person_compatibility(request))
    pattern_synergy = api_result["detailed_analysis"]["pattern_synergy"]
    favorable_synergy = api_result["detailed_analysis"]["favorable_synergy"]
    ten_gods_relationship = api_result["detailed_analysis"]["ten_gods_relationship"]

    assert "supportive_patterns" in pattern_synergy
    assert "tension_patterns" in pattern_synergy
    assert "risk_patterns" in pattern_synergy
    assert "score_basis" in pattern_synergy
    assert "score_basis" in favorable_synergy
    assert "useful_ten_gods_support" in favorable_synergy
    assert "useful_ten_gods_support" in ten_gods_relationship
    assert "risk_reasons" in ten_gods_relationship


def test_astro_chart_api_matches_fastmcp_tool_output():
    request = AstroChartRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
    )

    api_result = asyncio.run(calculate_astro_chart(request))
    mcp_result = json.loads(astro_chart.fn(**request.model_dump()))

    assert api_result == mcp_result


def test_astro_relative_api_matches_fastmcp_tool_output():
    request = AstroRelativeRequest(
        inner=AstroRelativePartyRequest(
            **_build_birth_payload(name="甲", gender="男", birth_place="上海"),
            birth_latitude=31.2304,
        ),
        outer=AstroRelativePartyRequest(
            **{
                **_build_birth_payload(name="乙", gender="女", birth_place="北京"),
                "birth_year": 1992,
                "birth_month": 3,
                "birth_day": 2,
                "birth_hour": 8,
                "birth_minute": 18,
                "birth_longitude": 116.4074,
                "birth_latitude": 39.9042,
            }
        ),
        relative_mode="Composite",
        hsys=0,
        zodiacal=0,
    )

    api_result = asyncio.run(calculate_relative_chart(request))
    mcp_result = json.loads(
        astro_relative_chart.fn(
            inner_birth_year=request.inner.birth_year,
            inner_birth_month=request.inner.birth_month,
            inner_birth_day=request.inner.birth_day,
            inner_birth_hour=request.inner.birth_hour,
            inner_birth_minute=request.inner.birth_minute,
            inner_birth_timezone=request.inner.birth_timezone,
            inner_birth_longitude=request.inner.birth_longitude,
            inner_birth_latitude=request.inner.birth_latitude,
            inner_name=request.inner.name,
            inner_birth_place=request.inner.birth_place,
            outer_birth_year=request.outer.birth_year,
            outer_birth_month=request.outer.birth_month,
            outer_birth_day=request.outer.birth_day,
            outer_birth_hour=request.outer.birth_hour,
            outer_birth_minute=request.outer.birth_minute,
            outer_birth_timezone=request.outer.birth_timezone,
            outer_birth_longitude=request.outer.birth_longitude,
            outer_birth_latitude=request.outer.birth_latitude,
            outer_name=request.outer.name,
            outer_birth_place=request.outer.birth_place,
            relationship_mode=request.relationship_mode,
            relative_mode=request.relative_mode,
            hsys=request.hsys,
            zodiacal=request.zodiacal,
        )
    )

    assert api_result == mcp_result


def test_timing_analysis_api_matches_fastmcp_tool_output():
    request = TimingAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=21,
        analysis_minute=55,
        analysis_age=38,
        selected_sections=["查询信息", "综合影响"],
    )

    api_result = asyncio.run(calculate_timing_analysis(request))
    mcp_result = json.loads(timing_analysis.fn(**request.model_dump()))

    assert api_result == mcp_result


def test_dayun_analysis_api_matches_fastmcp_tool_output():
    request = DayunAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        analysis_age=38,
        selected_sections=["查询信息", "大运信息"],
    )

    api_result = asyncio.run(calculate_dayun(request))
    mcp_result = json.loads(dayun_analysis.fn(**request.model_dump()))

    assert api_result == mcp_result


def test_liunian_analysis_api_matches_fastmcp_tool_output():
    request = LiunianAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        target_year=2028,
    )

    api_result = asyncio.run(calculate_liunian(request))
    mcp_result = json.loads(liunian_analysis.fn(**request.model_dump()))

    assert api_result == mcp_result


def test_western_timing_api_offloads_calculation_to_threadpool(monkeypatch):
    expected = {"analysis_type": "西占推运与返照分析", "summary": "ok"}
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return expected

    monkeypatch.setattr(
        api_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
        raising=False,
    )

    request = WesternTimingRequest(
        name="张三",
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        birth_latitude=31.2304,
        birth_place="上海",
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
    )

    result = asyncio.run(calculate_western_timing(request))

    assert result == expected
    assert captured["func"] is api_module.calculate_western_timing_analysis
    assert captured["args"] == ()
    assert captured["kwargs"]["analysis_year"] == 2028
    assert captured["kwargs"]["birth_latitude"] == 31.2304


def test_western_timing_module_api_offloads_calculation_to_threadpool(monkeypatch):
    expected = {"analysis_type": "西占太阳返照", "summary": "ok"}
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return expected

    monkeypatch.setattr(
        api_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
        raising=False,
    )

    request = WesternTimingModuleRequest(
        name="张三",
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=10,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.4737,
        birth_latitude=31.2304,
        birth_place="上海",
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        selected_sections=["起盘信息"],
    )

    result = asyncio.run(calculate_solarreturn_module(request))

    assert result == expected
    assert captured["func"] is api_module.calculate_solarreturn
    assert captured["args"] == ()
    assert captured["kwargs"]["selected_sections"] == ["起盘信息"]
    assert captured["kwargs"]["analysis_day"] == 6


def test_astro_chart_api_offloads_calculation_to_threadpool(monkeypatch):
    expected = {"analysis_type": "西洋占星本命盘", "summary": "ok"}
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return expected

    monkeypatch.setattr(
        api_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
        raising=False,
    )

    request = AstroChartRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        birth_latitude=31.2304,
    )

    result = asyncio.run(calculate_astro_chart(request))

    assert result == expected
    assert captured["func"] is api_module.calculate_core_chart_analysis
    assert captured["kwargs"]["chart_variant"] == "chart"
    assert captured["kwargs"]["birth_latitude"] == 31.2304


def test_astro_relative_api_offloads_calculation_to_threadpool(monkeypatch):
    expected = {"analysis_type": "关系盘", "summary": "ok"}
    captured = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return expected

    monkeypatch.setattr(
        api_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
        raising=False,
    )

    request = AstroRelativeRequest(
        inner=AstroRelativePartyRequest(
            **_build_birth_payload(name="甲", gender="男", birth_place="上海"),
            birth_latitude=31.2304,
        ),
        outer=AstroRelativePartyRequest(
            **{
                **_build_birth_payload(name="乙", gender="女", birth_place="北京"),
                "birth_year": 1992,
                "birth_month": 3,
                "birth_day": 2,
                "birth_hour": 8,
                "birth_minute": 18,
                "birth_longitude": 116.4074,
                "birth_latitude": 39.9042,
            }
        ),
        relative_mode="Composite",
        hsys=0,
        zodiacal=0,
    )

    result = asyncio.run(calculate_relative_chart(request))

    assert result == expected
    assert captured["func"] is api_module.calculate_relative_chart_analysis
    assert captured["kwargs"]["inner_payload"]["birth_latitude"] == 31.2304
    assert captured["kwargs"]["outer_payload"]["birth_longitude"] == 116.4074
    assert captured["kwargs"]["relative_mode"] == "Composite"
