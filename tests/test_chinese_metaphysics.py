from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    JinkouAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    QimenAnalysisRequest,
    TaiyiAnalysisRequest,
    ZiweiBirthRequest,
    ZiweiRulesRequest,
)
from fastmcp_server import (
    jinkou,
    liureng_gods,
    liureng_runyear,
    qimen,
    taiyi,
    ziwei_birth,
    ziwei_rules,
)
from fatebridge.services.metaphysics import (
    calculate_jinkou_analysis,
    calculate_liureng_gods,
    calculate_liureng_runyear,
    calculate_qimen_analysis,
    calculate_taiyi_analysis,
    calculate_ziwei_birth,
    calculate_ziwei_rules,
)
from fatebridge.utils.helpers import create_person_info


def test_ziwei_birth_request_model_accepts_birth_fields():
    request = ZiweiBirthRequest(
        name="张三",
        gender="男",
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        selected_sections=["起盘信息", "宫位总览"],
    )

    payload = request.model_dump()

    assert payload["name"] == "张三"
    assert payload["gender"] == "男"
    assert payload["birth_hour"] == 14
    assert payload["birth_minute"] == 30
    assert payload["birth_timezone"] == "Asia/Shanghai"
    assert payload["selected_sections"] == ["起盘信息", "宫位总览"]


def test_cn_analysis_request_models_accept_fields():
    liureng_request = LiuRengGodsRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        selected_sections=["起盘信息", "三传"],
    )
    qimen_request = QimenAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        qimen_options={"layout": "fly"},
        selected_sections=["起盘信息", "九宫方盘"],
    )
    taiyi_request = TaiyiAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        selected_sections=["起盘信息", "十六宫标记"],
    )
    jinkou_request = JinkouAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        selected_sections=["起盘信息", "金口诀四位"],
    )
    runyear_request = LiuRengRunyearRequest(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        gender="男",
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        selected_sections=["起盘信息", "行年"],
    )
    rules_request = ZiweiRulesRequest(
        year_stem="甲",
        selected_sections=["规则概览", "当前天干四化"],
    )

    assert liureng_request.model_dump()["analysis_longitude"] == 121.4737
    assert liureng_request.model_dump()["selected_sections"] == ["起盘信息", "三传"]
    assert qimen_request.model_dump()["analysis_hour"] == 21
    assert qimen_request.model_dump()["qimen_options"]["layout"] == "fly"
    assert qimen_request.model_dump()["selected_sections"] == ["起盘信息", "九宫方盘"]
    assert taiyi_request.model_dump()["gender"] == "男"
    assert taiyi_request.model_dump()["selected_sections"] == ["起盘信息", "十六宫标记"]
    assert jinkou_request.model_dump()["di_fen"] == "酉"
    assert jinkou_request.model_dump()["selected_sections"] == ["起盘信息", "金口诀四位"]
    assert runyear_request.model_dump()["birth_year"] == 1994
    assert runyear_request.model_dump()["selected_sections"] == ["起盘信息", "行年"]
    assert rules_request.model_dump()["year_stem"] == "甲"
    assert rules_request.model_dump()["selected_sections"] == ["规则概览", "当前天干四化"]


def test_calculate_ziwei_birth_returns_twelve_palaces():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_ziwei_birth(person)

    assert result["analysis_type"] == "紫微斗数命盘"
    assert result["ziwei_birth"]["engine"] == "fatebridge-offline"
    assert result["ziwei_birth"]["time_algorithm"] in {"直接时间", "真太阳时"}
    assert len(result["ziwei_birth"]["palaces"]) == 12
    assert result["ziwei_birth"]["ming_gong"]["name"] == "命宫"
    assert result["ziwei_birth"]["shen_gong"]["name"] == "身宫"
    assert set(result["ziwei_birth"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert any("紫微" in "、".join(palace["stars"]) for palace in result["ziwei_birth"]["palaces"])
    assert "[起盘信息]" in result["snapshot_text"]
    assert "[宫位总览]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_ziwei_birth_supports_selected_export_sections():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_ziwei_birth(
        person,
        selected_sections=["宫位总览"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["宫位总览"]
    assert "[宫位总览]" in result["snapshot_export"]["export_text"]
    assert "[起盘信息]" not in result["snapshot_export"]["export_text"]


def test_calculate_ziwei_rules_supports_year_stem_filter():
    result = calculate_ziwei_rules(year_stem="甲")

    assert result["analysis_type"] == "紫微规则库"
    assert result["engine"] == "fatebridge-offline"
    assert result["requested_year_stem"] == "甲"
    assert result["focused_rules"]["year_stem"] == "甲"
    assert set(result["focused_rules"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert "palace_sequence" in result["rule_catalogue"]
    assert "[规则概览]" in result["snapshot_text"]
    assert "[四化总表]" in result["snapshot_text"]
    assert "[当前天干四化]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_ziwei_rules_supports_selected_export_sections():
    result = calculate_ziwei_rules(
        year_stem="甲",
        selected_sections=["规则概览", "当前天干四化"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["规则概览", "当前天干四化"]
    assert "[规则概览]" in result["snapshot_export"]["export_text"]
    assert "[当前天干四化]" in result["snapshot_export"]["export_text"]
    assert "[四化总表]" not in result["snapshot_export"]["export_text"]


def test_calculate_liureng_gods_returns_core_sections():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "大六壬起课"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["liureng"]["month_general"]["branch"] == "戌"
    assert result["liureng"]["month_general"]["branch"]
    assert len(result["liureng"]["four_lessons"]) == 4
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]
    assert result["liureng"]["overview"]
    assert "空" in result["liureng"]["kongwang"]
    assert "[四课]" in result["snapshot_text"]
    assert "[三传]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liureng_runyear_uses_birth_context():
    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
    )

    result = calculate_liureng_runyear(
        person,
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
    )

    assert result["analysis_type"] == "大六壬行年"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["runyear"]["engine"] == "fatebridge-offline"
    assert result["runyear"]["age"] > 0
    assert len(result["runyear"]["ganzhi"]) == 2
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]
    assert "[行年]" in result["snapshot_text"]
    assert result["runyear"]["ganzhi"] in result["snapshot_text"]


def test_calculate_liureng_gods_distinguishes_liuhe_style():
    result = calculate_liureng_gods(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=33,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4667,
        gender="男",
    )

    assert result["liureng"]["board_style"] == "六合"
    assert result["liureng"]["four_lessons"][0]["relations"]["with_day_branch"] == "六合"
    assert result["liureng"]["four_lessons"][0]["relations"]["with_lower_branch"] == "六合"
    assert any(pattern["name"] == "六合课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_uses_liuhe_transmission_rule():
    result = calculate_liureng_gods(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=33,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4667,
        gender="男",
    )

    transmissions = result["liureng"]["three_transmissions"]
    assert result["liureng"]["board_style"] == "六合"
    assert transmissions["method"] == "六合取合"
    assert transmissions["initial"]["branch"] == "卯"
    assert transmissions["middle"]["branch"] == "戌"
    assert transmissions["final"]["branch"] == "卯"


def test_calculate_liureng_gods_uses_fanyin_transmission_rule():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=1,
        analysis_hour=0,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    transmissions = result["liureng"]["three_transmissions"]
    assert result["liureng"]["board_style"] == "返吟"
    assert transmissions["method"] == "返吟取冲"
    assert transmissions["initial"]["branch"] == "午"
    assert transmissions["middle"]["branch"] == "子"
    assert transmissions["final"]["branch"] == "丑"


def test_calculate_liureng_gods_uses_fuyin_transmission_rule():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=1,
        analysis_hour=2,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    transmissions = result["liureng"]["three_transmissions"]
    assert result["liureng"]["board_style"] == "伏吟"
    assert transmissions["method"] == "伏吟守一"
    assert transmissions["initial"]["branch"] == "子"
    assert transmissions["middle"]["branch"] == "子"
    assert transmissions["final"]["branch"] == "子"


def test_calculate_liureng_gods_marks_yaoke_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=1,
        analysis_hour=18,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style"] == "官鬼"
    assert result["liureng"]["board_style_detail"] == "遥克"
    assert result["liureng"]["meta"]["selected_lesson_index"] == 4
    assert any(pattern["name"] == "遥克课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_bazhuan_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=2,
        analysis_hour=10,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style_detail"] == "八专"
    assert any(pattern["name"] == "八专课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_maoxing_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=4,
        analysis_hour=22,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style"] == "比用"
    assert result["liureng"]["board_style_detail"] == "昴星"
    assert any(pattern["name"] == "昴星课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_chongshen_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=1,
        analysis_hour=4,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style"] == "六合"
    assert result["liureng"]["board_style_detail"] == "重审"
    assert any(pattern["name"] == "重审课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_yuanshou_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=3,
        analysis_hour=0,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style_detail"] == "元首"
    assert result["liureng"]["meta"]["selected_lesson_relation"] == "上克下"
    assert any(pattern["name"] == "元首课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_bieze_detail():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style_detail"] == "别责"
    assert result["liureng"]["meta"]["selected_lesson_relation"] == "下生上"
    assert any(pattern["name"] == "别责课" for pattern in result["liureng"]["patterns"])


def test_calculate_qimen_analysis_returns_nine_palaces():
    result = calculate_qimen_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "奇门遁甲"
    assert result["qimen"]["dun_type"] in {"阳遁", "阴遁"}
    assert len(result["qimen"]["palaces"]) == 9
    assert result["qimen"]["zhifu"]["star"]
    assert result["qimen"]["zhishi"]["door"]
    assert result["qimen"]["palaces"][0]["door_hexagram"]["name"]
    assert result["qimen"]["palaces"][0]["content_palace"] == result["qimen"]["palaces"][0]["name"]
    assert result["qimen"]["palaces"][0]["content_trigram"] == result["qimen"]["palaces"][0]["trigram"]
    assert "[八宫详解]" in result["snapshot_text"]
    assert "[九宫方盘]" in result["snapshot_text"]
    assert "[奇门演卦]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]
    assert "离九宫" in result["snapshot_export"]["section_titles_detected"]


def test_metaphysics_true_solar_time_uses_longitude_only_correction():
    result = calculate_qimen_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        use_true_solar_time=True,
    )

    assert result["analysis_context"]["time_algorithm"] == "真太阳时"
    assert result["analysis_context"]["corrected_datetime"].startswith(
        "2026-04-04 21:12:"
    )
    assert result["analysis_context"]["total_correction_minutes"] == pytest.approx(
        -5.89, abs=0.05
    )
    assert result["four_pillars"] == {
        "year": {"stem": "丙", "branch": "午"},
        "month": {"stem": "辛", "branch": "卯"},
        "day": {"stem": "戊", "branch": "申"},
        "hour": {"stem": "癸", "branch": "亥"},
    }
    assert result["qimen"]["ju_text"] == "阳遁六局下元"
    assert result["qimen"]["yuan"] == "下元"
    assert result["qimen"]["fu_tou"] == "甲辰"
    assert result["qimen"]["xun_head"] == "甲辰"
    assert result["qimen"]["kongwang"] == "寅卯空"
    assert result["qimen"]["zhifu"] == {
        "star": "天芮",
        "palace": "坤二宫",
        "trigram": "坤",
        "content_palace": "坤二宫",
        "content_trigram": "坤",
        "code": "芮",
    }
    assert result["qimen"]["zhishi"] == {
        "door": "死门",
        "palace": "坤二宫",
        "trigram": "坤",
        "content_palace": "坤二宫",
        "content_trigram": "坤",
        "code": "死",
    }
    zhifu_palace = next(
        palace
        for palace in result["qimen"]["palaces"]
        if palace["name"] == result["qimen"]["zhifu"]["palace"]
    )
    zhishi_palace = next(
        palace
        for palace in result["qimen"]["palaces"]
        if palace["name"] == result["qimen"]["zhishi"]["palace"]
    )
    assert zhifu_palace["star"] == result["qimen"]["zhifu"]["star"]
    assert zhishi_palace["door"] == result["qimen"]["zhishi"]["door"]
    assert "值符：天芮在坤二宫" in result["snapshot_text"]


def test_calculate_qimen_analysis_applies_qimen_options_and_snapshot_text():
    default_result = calculate_qimen_analysis(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=33,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
    )
    optioned_result = calculate_qimen_analysis(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=33,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        qimen_options={"layout": "fly"},
    )

    assert optioned_result["qimen"] != default_result["qimen"]
    assert optioned_result["qimen"]["layout"] == "fly"
    assert optioned_result["snapshot_text"] != default_result["snapshot_text"]
    assert "[九宫方盘]" in optioned_result["snapshot_text"]
    assert "内容来源：" in optioned_result["snapshot_text"]
    optioned_zhifu_palace = next(
        palace
        for palace in optioned_result["qimen"]["palaces"]
        if palace["name"] == optioned_result["qimen"]["zhifu"]["palace"]
    )
    optioned_zhishi_palace = next(
        palace
        for palace in optioned_result["qimen"]["palaces"]
        if palace["name"] == optioned_result["qimen"]["zhishi"]["palace"]
    )
    assert optioned_result["qimen"]["zhifu"]["content_palace"] == optioned_zhifu_palace["content_palace"]
    assert optioned_result["qimen"]["zhifu"]["content_trigram"] == optioned_zhifu_palace["content_trigram"]
    assert optioned_result["qimen"]["zhishi"]["content_palace"] == optioned_zhishi_palace["content_palace"]
    assert optioned_result["qimen"]["zhishi"]["content_trigram"] == optioned_zhishi_palace["content_trigram"]


def test_calculate_qimen_analysis_supports_selected_export_sections():
    result = calculate_qimen_analysis(
        analysis_year=2028,
        analysis_month=4,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=33,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        selected_sections=["起盘信息", "九宫方盘", "离九宫"],
    )

    assert "[八宫详解]" in result["snapshot_text"]
    assert result["snapshot_export"]["selected_sections"] == ["起盘信息", "九宫方盘", "离九宫"]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[九宫方盘]" in result["snapshot_export"]["export_text"]
    assert "[离九宫]" in result["snapshot_export"]["export_text"]
    assert "[八宫详解]" not in result["snapshot_export"]["export_text"]


def test_calculate_taiyi_analysis_returns_sixteen_palaces():
    result = calculate_taiyi_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "太乙神数"
    assert result["taiyi"]["style_label"]
    assert result["taiyi"]["taiyi_palace"] == "卯"
    assert result["taiyi"]["wenchang_palace"] == "坤"
    assert len(result["taiyi"]["palace_marks"]) == 16
    assert result["taiyi"]["core_board"]["main_calculation"] == "阳遁二十五局"
    assert "[太乙盘]" in result["snapshot_text"]
    assert "[十六宫标记]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_liureng_gods_supports_selected_export_sections():
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        selected_sections=["起盘信息", "三传", "概览"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["起盘信息", "三传", "概览"]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[三传]" in result["snapshot_export"]["export_text"]
    assert "[概览]" in result["snapshot_export"]["export_text"]
    assert "[四课]" not in result["snapshot_export"]["export_text"]


def test_calculate_taiyi_analysis_supports_selected_export_sections():
    result = calculate_taiyi_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        selected_sections=["起盘信息", "十六宫标记"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["起盘信息", "十六宫标记"]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[十六宫标记]" in result["snapshot_export"]["export_text"]
    assert "[太乙盘]" not in result["snapshot_export"]["export_text"]


def test_calculate_jinkou_analysis_returns_four_positions():
    result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        use_true_solar_time=True,
    )

    assert result["analysis_type"] == "金口诀"
    assert result["liureng"]["engine"] == "fatebridge-offline"
    assert result["jinkou"]["engine"] == "fatebridge-offline"
    assert result["liureng"]["month_general"]["branch"] == "戌"
    assert result["jinkou"]["overview"]["di_fen"] == "酉"
    assert result["jinkou"]["overview"]["yuejiang"]["branch"] == "申"
    assert result["jinkou"]["overview"]["guishen"]["name"] == "太阴"
    assert result["jinkou"]["overview"]["board_style"] == result["liureng"]["board_style"]
    assert result["jinkou"]["overview"]["use_position"] == "将神"
    assert len(result["jinkou"]["rows"]) == 4
    assert result["jinkou"]["overview"]["yuejiang"]["name"]
    assert result["jinkou"]["overview"]["guishen"]["name"]
    assert result["jinkou"]["shensha"]
    assert "[金口诀速览]" in result["snapshot_text"]
    assert "[金口诀四位]" in result["snapshot_text"]
    assert "[四位神煞]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_jinkou_analysis_uses_liureng_detail_to_break_ties():
    result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=6,
        analysis_hour=9,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="巳",
    )

    assert result["liureng"]["board_style_detail"] == "别责"
    assert result["jinkou"]["overview"]["board_style_detail"] == "别责"
    assert result["jinkou"]["overview"]["use_position"] == "地分"
    assert any(
        item["label"] == "课体" and item["value"] == "别责课"
        for item in result["jinkou"]["shensha"]
    )
    assert any(
        item["label"] == "取传"
        and item["value"] == result["liureng"]["three_transmissions"]["method"]
        for item in result["jinkou"]["shensha"]
    )


def test_calculate_jinkou_analysis_supports_selected_export_sections():
    result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
        di_fen="酉",
        selected_sections=["起盘信息", "金口诀四位"],
    )

    assert result["snapshot_export"]["selected_sections"] == ["起盘信息", "金口诀四位"]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[金口诀四位]" in result["snapshot_export"]["export_text"]
    assert "[四位神煞]" not in result["snapshot_export"]["export_text"]


def test_fastmcp_tools_expose_new_parameters():
    assert "birth_year" in ziwei_birth.parameters["properties"]
    assert "selected_sections" in ziwei_birth.parameters["properties"]
    assert "year_stem" in ziwei_rules.parameters["properties"]
    assert "selected_sections" in ziwei_rules.parameters["properties"]
    assert "analysis_year" in liureng_gods.parameters["properties"]
    assert "selected_sections" in liureng_gods.parameters["properties"]
    assert "birth_year" in liureng_runyear.parameters["properties"]
    assert "selected_sections" in liureng_runyear.parameters["properties"]
    assert "analysis_year" in qimen.parameters["properties"]
    assert "qimen_options" in qimen.parameters["properties"]
    assert "selected_sections" in qimen.parameters["properties"]
    assert "gender" in taiyi.parameters["properties"]
    assert "selected_sections" in taiyi.parameters["properties"]
    assert "di_fen" in jinkou.parameters["properties"]
    assert "selected_sections" in jinkou.parameters["properties"]
