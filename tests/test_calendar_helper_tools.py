import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import GuaMeiyiRequest, JieqiYearRequest, NongliTimeRequest
from fastmcp_server import gua_meiyi, jieqi_year, nongli_time
from fatebridge.services.divination import calculate_gua_meiyi
from fatebridge.services.timing import calculate_jieqi_year, calculate_nongli_time


def test_helper_request_models_accept_legacy_style_fields():
    jieqi_request = JieqiYearRequest(
        year=2028,
        zone="+08:00",
        lat="31n13",
        lon="121e28",
        gpsLat=31.2167,
        gpsLon=121.4667,
        jieqis=["春分", "冬至"],
        selected_sections=["查询信息", "重点节气"],
    )
    nongli_request = NongliTimeRequest(
        date="2028-04-01",
        time="09:00:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
        gpsLat=31.2167,
        gpsLon=121.4667,
        after23NewDay=True,
        timeAlg=0,
        selected_sections=["农历上下文", "四柱上下文"],
    )
    gua_request = GuaMeiyiRequest(name=["111", "000"])

    jieqi_payload = jieqi_request.model_dump(by_alias=True)
    nongli_payload = nongli_request.model_dump(by_alias=True)

    assert jieqi_payload["gpsLat"] == 31.2167
    assert jieqi_payload["gpsLon"] == 121.4667
    assert jieqi_payload["jieqis"] == ["春分", "冬至"]
    assert jieqi_payload["selected_sections"] == ["查询信息", "重点节气"]
    assert nongli_payload["after23NewDay"] is True
    assert nongli_payload["timeAlg"] == 0
    assert nongli_payload["gpsLat"] == 31.2167
    assert nongli_payload["selected_sections"] == ["农历上下文", "四柱上下文"]
    assert gua_request.name == ["111", "000"]


def test_calculate_jieqi_year_returns_year_grid_and_selected_terms():
    result = calculate_jieqi_year(
        year=2028,
        zone="Asia/Shanghai",
        lat="31n13",
        lon="121e28",
        jieqis=["春分", "冬至"],
    )

    assert result["analysis_type"] == "全年节气盘"
    assert result["query_context"]["year"] == 2028
    assert result["query_context"]["timezone"] == "Asia/Shanghai"
    assert len(result["jieqi_year"]) == 24
    assert result["jieqi_year"][0]["name"] == "小寒"
    assert result["jieqi_year"][-1]["name"] == "冬至"
    assert [item["name"] for item in result["selected_jieqi"]] == ["春分", "冬至"]
    assert result["year"] == 2028
    assert result["jieqi24"] == result["jieqi_year"]
    assert "2028年" in result["summary"]
    assert "24个节气节点" in result["summary"]
    assert "[查询信息]" in result["snapshot_text"]
    assert "[全年节气]" in result["snapshot_text"]
    assert "[重点节气]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_jieqi_year_supports_selected_export_sections():
    result = calculate_jieqi_year(
        year=2028,
        zone="Asia/Shanghai",
        jieqis=["春分", "冬至"],
        selected_sections=["查询信息", "重点节气"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["查询信息", "重点节气"]
    assert "[查询信息]" in result["snapshot_export"]["export_text"]
    assert "[重点节气]" in result["snapshot_export"]["export_text"]
    assert "[全年节气]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_nongli_time_returns_lunar_and_ganzhi_context():
    result = calculate_nongli_time(
        date="2028-04-01",
        time="09:00:00",
        zone="Asia/Shanghai",
        lon="121e28",
    )

    assert result["analysis_type"] == "农历换算"
    assert result["input_context"]["date"] == "2028-04-01"
    assert result["input_context"]["time"] == "09:00:00"
    assert result["input_context"]["timezone"] == "Asia/Shanghai"
    assert result["birth"] == "2028-04-01 09:00:00"
    assert result["yearJieqi"] == "戊申"
    assert result["monthGanZi"] == "乙卯"
    assert result["dayGanZi"] == "丙辰"
    assert result["time"] == "癸巳"
    assert result["month"] == "三月"
    assert result["day"] == "初七"
    assert result["monthInt"] == 3
    assert result["dayInt"] == 7
    assert result["leap"] is False
    assert result["lunar_calendar"]["display"] == "三月初七"
    assert result["lunar_calendar"]["jieqi"] == "春分"
    assert set(result["four_pillars"]) == {"year", "month", "day", "hour"}
    assert result["calendar_context"]["current_solar_term"]["name"] == "春分"
    assert "三月初七" in result["summary"]
    assert "春分" in result["summary"]
    assert "[查询信息]" in result["snapshot_text"]
    assert "[农历上下文]" in result["snapshot_text"]
    assert "[四柱上下文]" in result["snapshot_text"]
    assert "[来源]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_nongli_time_supports_selected_export_sections():
    result = calculate_nongli_time(
        date="2028-04-01",
        time="09:00:00",
        zone="Asia/Shanghai",
        lon="121e28",
        selected_sections=["农历上下文", "四柱上下文"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["农历上下文", "四柱上下文"]
    assert "[农历上下文]" in result["snapshot_export"]["export_text"]
    assert "[四柱上下文]" in result["snapshot_export"]["export_text"]
    assert "[查询信息]" not in result["snapshot_export"]["export_text"]
    assert "[来源]" not in result["snapshot_export"]["export_text"]


def test_calculate_gua_meiyi_returns_batch_meiyi_explanations():
    result = calculate_gua_meiyi(name=["111", "000"])

    assert result["analysis_type"] == "梅易卦义"
    assert result["queries"] == ["111", "000"]
    assert result["results"]["111"]["name"] == "乾"
    assert result["results"]["111"]["lookup_type"] == "trigram"
    assert "主动开创" in result["results"]["111"]["desc"]
    assert result["111"]["name"] == "乾"
    assert result["111"]["text"] == result["results"]["111"]["desc"]
    assert result["results"]["000"]["name"] == "坤"
    assert result["results"]["000"]["lookup_type"] == "trigram"
    assert "承载顺势" in result["results"]["000"]["desc"]
    assert result["000"]["name"] == "坤"
    assert "乾" in result["summary"]
    assert "坤" in result["summary"]


def test_helper_mcp_tools_return_formatted_json_strings():
    jieqi_result = json.loads(
        jieqi_year.fn(
            year=2028,
            zone="Asia/Shanghai",
            lat="31n13",
            lon="121e28",
            jieqis=["春分", "冬至"],
            selected_sections=["查询信息", "重点节气"],
        )
    )
    nongli_result = json.loads(
        nongli_time.fn(
            date="2028-04-01",
            time="09:00:00",
            zone="Asia/Shanghai",
            lon="121e28",
            selected_sections=["农历上下文"],
        )
    )
    gua_result = json.loads(gua_meiyi.fn(name=["111", "000"]))

    assert jieqi_result["analysis_type"] == "全年节气盘"
    assert jieqi_result["selected_jieqi"][0]["name"] == "春分"
    assert jieqi_result["snapshot_export"]["selected_sections"] == ["查询信息", "重点节气"]
    assert nongli_result["analysis_type"] == "农历换算"
    assert nongli_result["lunar_calendar"]["display"] == "三月初七"
    assert nongli_result["snapshot_export"]["selected_sections"] == ["农历上下文"]
    assert gua_result["analysis_type"] == "梅易卦义"
    assert gua_result["results"]["111"]["name"] == "乾"


def test_calendar_helper_tools_expose_selected_sections_parameter():
    assert "selected_sections" in jieqi_year.parameters["properties"]
    assert "selected_sections" in nongli_time.parameters["properties"]
