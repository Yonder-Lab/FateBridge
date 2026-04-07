from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    GuaLookupRequest,
    MeihuaAnalysisRequest,
    OtherBuRequest,
    SanShiUnitedRequest,
    SixYaoRequest,
    SuZhanRequest,
    TongSheFaRequest,
)
from fastmcp_server import (
    gua_lookup,
    meihua_analysis,
    otherbu,
    sanshiunited,
    sixyao,
    suzhan,
    tongshefa,
)
from fatebridge.services.divination import (
    calculate_gua_lookup,
    calculate_meihua_analysis,
    calculate_otherbu_analysis,
    calculate_sanshiunited_analysis,
    calculate_sixyao_analysis,
    calculate_suzhan_analysis,
    calculate_tongshefa_analysis,
)


def test_meihua_request_model_accepts_analysis_fields():
    request = MeihuaAnalysisRequest(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        question="事业推进节奏",
    )

    payload = request.model_dump()

    assert payload["analysis_year"] == 2028
    assert payload["analysis_month"] == 4
    assert payload["analysis_day"] == 1
    assert payload["analysis_hour"] == 9
    assert payload["analysis_minute"] == 0
    assert payload["analysis_timezone"] == "Asia/Shanghai"
    assert payload["question"] == "事业推进节奏"


def test_gua_lookup_request_model_accepts_fields():
    request = GuaLookupRequest(
        query="111111",
        lookup_mode="hexagram",
    )

    payload = request.model_dump()

    assert payload["query"] == "111111"
    assert payload["lookup_mode"] == "hexagram"


def test_phase2_request_models_accept_alias_and_nested_fields():
    tongshefa_request = TongSheFaRequest(
        taiyin="巽",
        taiyang="坤",
        shaoyang="震",
        shaoyin="震",
    )
    sixyao_request = SixYaoRequest(
        date="2028-04-06",
        time="09:33:00",
        zone="+08:00",
        gpsLat=31.2,
        gpsLon=121.4,
        lines=[{"value": 1, "change": True}],
    )
    suzhan_request = SuZhanRequest(
        date="2028-04-06",
        time="09:33:00",
        houseStartMode=2,
        doubingSu28=False,
    )
    otherbu_request = OtherBuRequest(
        date="2028-04-06",
        time="09:33:00",
        sign="Aries",
        house=3,
        planet="Sun",
    )
    sanshiunited_request = SanShiUnitedRequest(
        date="2028-04-06",
        time="09:33:00",
        qimen_options={"layout": "fly"},
        taiyi_options={"accNum": 1},
        liureng_yue="辰",
        liureng_is_diurnal=True,
    )

    sixyao_payload = sixyao_request.model_dump(by_alias=True)
    suzhan_payload = suzhan_request.model_dump(by_alias=True)

    assert tongshefa_request.shaoyin == "震"
    assert sixyao_payload["gpsLat"] == 31.2
    assert sixyao_payload["gpsLon"] == 121.4
    assert sixyao_payload["lines"][0]["change"] is True
    assert suzhan_payload["houseStartMode"] == 2
    assert suzhan_payload["doubingSu28"] is False
    assert otherbu_request.house == 3
    assert sanshiunited_request.qimen_options["layout"] == "fly"
    assert sanshiunited_request.liureng_is_diurnal is True


def test_calculate_gua_lookup_supports_hexagram_and_trigram_queries():
    hexagram_result = calculate_gua_lookup(query="111111", lookup_mode="auto")
    trigram_result = calculate_gua_lookup(query="111", lookup_mode="auto")

    assert hexagram_result["result"]["lookup_type"] == "hexagram"
    assert hexagram_result["result"]["name"] == "乾为天"
    assert hexagram_result["result"]["theme"] == "开创与自强"
    assert hexagram_result["result"]["judgement"] == "局势昂扬，宜先定大方向再强力推进。"
    assert "六阳纯健" in hexagram_result["result"]["image"]
    assert "立战略" in hexagram_result["result"]["favorable"]
    assert "刚愎" in hexagram_result["result"]["caution"]
    assert "主动定方向" in hexagram_result["summary"]
    assert "忌刚愎" in hexagram_result["summary"]

    assert trigram_result["result"]["lookup_type"] == "trigram"
    assert trigram_result["result"]["name"] == "乾"
    assert trigram_result["result"]["theme"] == "主动开创"
    assert "纯阳在上" in trigram_result["result"]["image"]
    assert "立规" in trigram_result["result"]["favorable"]
    assert "刚亢" in trigram_result["result"]["caution"]
    assert "立方向" in trigram_result["summary"]
    assert "忌刚亢" in trigram_result["summary"]


def test_calculate_meihua_analysis_returns_expected_hexagram_chain():
    result = calculate_meihua_analysis(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        question="事业推进节奏",
    )

    meihua = result["meihua"]
    interpretation = result["interpretation"]

    assert result["analysis_context"]["lunar_display"] == "三月初七"
    assert result["analysis_context"]["current_jieqi"] == "春分"
    assert meihua["base_hexagram"]["name"] == "火天大有"
    assert meihua["changed_hexagram"]["name"] == "火风鼎"
    assert meihua["mutual_hexagram"]["name"] == "泽天夬"
    assert meihua["opposite_hexagram"]["name"] == "水地比"
    assert meihua["base_hexagram"]["judgement"] == "资源在手，宜放大优势并守住尺度。"
    assert "火在天上" in meihua["base_hexagram"]["image"]
    assert meihua["moving_palace"] == "下卦"
    assert meihua["body_trigram"]["name"] == "离"
    assert meihua["use_trigram"]["name"] == "乾"
    assert meihua["body_use_relation"] == "体克用"
    assert "体卦离、用卦乾" in meihua["body_use_summary"]
    assert interpretation["question_domain"]["label"] == "事业/项目"
    assert interpretation["moving_line_phase"]["stage"] == "起念与启动"
    assert len(interpretation["line_oracles"]) == 6
    assert sum(1 for item in interpretation["line_oracles"] if item["is_active"]) == 1
    assert interpretation["moving_line_oracle"]["position"] == "初爻"
    assert interpretation["moving_line_oracle"]["title"] == "发端位"
    assert interpretation["moving_line_oracle"]["focus"] == "起势、试探与基础"
    assert interpretation["moving_line_oracle"]["timing"] == "先小后大"
    assert interpretation["moving_line_oracle"]["changed_hexagram"]["name"] == "火风鼎"
    assert interpretation["moving_line_oracle"]["body_trigram"] == "离"
    assert interpretation["moving_line_oracle"]["use_trigram"] == "乾"
    assert "第一步踩稳" in interpretation["moving_line_oracle"]["judgement"]
    assert "试探、起步" in interpretation["moving_line_oracle"]["favorable"]
    assert "起手过满" in interpretation["moving_line_oracle"]["caution"]
    assert "里程碑先钉牢" in interpretation["moving_line_oracle"]["domain_hint"]
    assert "主动拿节奏" in interpretation["moving_line_oracle"]["body_use_adjustment"]
    assert interpretation["line_oracles"][0]["is_active"] is True
    assert interpretation["line_oracles"][-1]["changed_hexagram"]["name"] == "雷天大壮"
    assert "主动掌控" in interpretation["body_use_reading"]
    assert "火天大有" in interpretation["base_reading"]
    assert "火风鼎" in interpretation["changed_reading"]
    assert interpretation["base_oracle"]["judgement"] == "资源在手，宜放大优势并守住尺度。"
    assert "扩成果" in interpretation["base_oracle"]["favorable"]
    assert interpretation["changed_oracle"]["judgement"] == "重整器局可成新局，关键在结构升级。"
    assert "重组团队" in interpretation["changed_oracle"]["favorable"]
    assert "扩成果" in interpretation["action_hint"]
    assert "试探、起步" in interpretation["action_hint"]
    assert "重组团队" in interpretation["action_hint"]
    assert "骄满" in interpretation["risk_hint"]
    assert "起手过满" in interpretation["risk_hint"]
    assert "站错队" in interpretation["risk_hint"]
    assert len(interpretation["judgement_outline"]) == 7
    assert "事业/项目" in result["summary"]
    assert "起念与启动" in result["summary"]
    assert "第一步踩稳" in result["summary"]


def test_calculate_tongshefa_analysis_returns_expected_local_structure():
    result = calculate_tongshefa_analysis(
        taiyin="巽",
        taiyang="坤",
        shaoyang="震",
        shaoyin="震",
    )

    model = result["tongshefa"]

    assert result["analysis_type"] == "统摄法分析"
    assert model["baseLeft"]["name"] == "风雷益"
    assert model["baseRight"]["name"] == "地雷复"
    assert model["mutualLeft"]["name"] == "山地剥"
    assert model["mutualRight"]["name"] == "坤为地"
    assert model["oppositeLeft"]["name"] == "雷风恒"
    assert model["oppositeRight"]["name"] == "天风姤"
    assert model["main_relation"] == "思克实"
    assert "[潜藏]" in result["snapshot_text"]
    assert "[亲和]" in result["snapshot_text"]


def test_calculate_sixyao_analysis_supports_explicit_lines():
    result = calculate_sixyao_analysis(
        date="2028-04-06",
        time="09:33:00",
        zone="+08:00",
        question="合作",
        lines=[
            {"value": 1, "change": False},
            {"value": 1, "change": True},
            {"value": 1, "change": False},
            {"value": 1, "change": False},
            {"value": 1, "change": False},
            {"value": 1, "change": False},
        ],
    )

    assert result["current_code"] == "111111"
    assert result["changed_code"] == "101111"
    assert result["moving_lines"] == [2]
    assert result["current_hexagram"]["name"] == "乾为天"
    assert result["changed_hexagram"]["name"] == "天火同人"
    assert "第2爻：阳爻（动）" in result["snapshot_text"]
    assert "问题：合作" in result["snapshot_text"]


def test_calculate_suzhan_analysis_returns_chart_and_snapshot():
    result = calculate_suzhan_analysis(
        date="2028-04-06",
        time="09:33:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
    )

    assert result["analysis_type"] == "宿占 / 宿盘"
    assert result["chart"]["ok"] is True
    assert len(result["chart"]["houses"]) == 12
    assert any(item["id"] == "Sun" for item in result["chart"]["objects"])
    assert "[宿盘宫位与二十八宿星曜]" in result["snapshot_text"]
    assert "宫位：House1" in result["snapshot_text"]


def test_calculate_otherbu_analysis_supports_traditional_mode():
    result = calculate_otherbu_analysis(
        date="2028-04-06",
        time="09:33:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
        tradition=True,
        sign="Aries",
        house=0,
        planet="Sun",
        question="合作",
    )

    natal_objects = result["chart"]["chart"]["objects"]
    dice_sun = next(
        item for item in result["diceChart"]["chart"]["objects"] if item["id"] == "Sun"
    )

    assert result["analysis_type"] == "西洋游戏 / 占星骰子"
    assert result["sign"] == "Aries"
    assert result["planet"] == "Sun"
    assert dice_sun["house"] == "House1"
    assert dice_sun["sign"] == "Aries"
    assert not any(item["id"] == "Uranus" for item in natal_objects)
    assert "Sun主核心意志" in result["interpretation"]["summary"]
    assert "问题：合作" in result["snapshot_text"]


def test_calculate_sanshiunited_analysis_returns_local_aggregation():
    result = calculate_sanshiunited_analysis(
        date="2028-04-06",
        time="09:33:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
    )

    assert result["analysis_type"] == "三式合一"
    assert result["qimen"]["ju_text"] == "阳遁1局"
    assert result["taiyi"]["palace"] == "坎"
    assert result["taiyi"]["main_calculation"] == 46
    assert result["liureng"]["big_pattern"] == "太常合德格"
    assert result["liureng"]["small_pattern"] == "六合入局"
    assert "[八宫]" in result["snapshot_text"]
    assert "坎宫：天盘干：辛" in result["snapshot_text"]


def test_fastmcp_meihua_tool_exposes_parameters():
    properties = meihua_analysis.parameters["properties"]

    assert "analysis_year" in properties
    assert "analysis_month" in properties
    assert "analysis_day" in properties
    assert "analysis_hour" in properties
    assert "analysis_minute" in properties
    assert "analysis_timezone" in properties
    assert "question" in properties


def test_fastmcp_gua_lookup_tool_exposes_parameters():
    properties = gua_lookup.parameters["properties"]

    assert "query" in properties
    assert "lookup_mode" in properties


def test_fastmcp_phase2_tools_expose_parameters():
    assert "taiyin" in tongshefa.parameters["properties"]
    assert "taiyang" in tongshefa.parameters["properties"]

    sixyao_properties = sixyao.parameters["properties"]
    assert "date" in sixyao_properties
    assert "time" in sixyao_properties
    assert "gua_code" in sixyao_properties
    assert "changed_code" in sixyao_properties
    assert "lines" in sixyao_properties

    suzhan_properties = suzhan.parameters["properties"]
    assert "szchart" in suzhan_properties
    assert "szshape" in suzhan_properties
    assert "house_start_mode" in suzhan_properties

    otherbu_properties = otherbu.parameters["properties"]
    assert "tradition" in otherbu_properties
    assert "sign" in otherbu_properties
    assert "house" in otherbu_properties
    assert "planet" in otherbu_properties

    sanshi_properties = sanshiunited.parameters["properties"]
    assert "qimen_options" in sanshi_properties
    assert "taiyi_options" in sanshi_properties
    assert "liureng_yue" in sanshi_properties
    assert "liureng_is_diurnal" in sanshi_properties
