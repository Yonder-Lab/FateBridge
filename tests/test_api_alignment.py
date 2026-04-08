import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    DayunAnalysisRequest,
    LiunianAnalysisRequest,
    TimingAnalysisRequest,
    TwoPersonCompatibilityRequest,
    calculate_dayun,
    calculate_liunian,
    calculate_timing_analysis,
    calculate_two_person_compatibility,
)
from fastmcp_server import (
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


def test_timing_analysis_api_matches_fastmcp_tool_output():
    request = TimingAnalysisRequest(
        **_build_birth_payload(name="张三", gender="男", birth_place="上海"),
        analysis_year=2028,
        analysis_month=4,
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
