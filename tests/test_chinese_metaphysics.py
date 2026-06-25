import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.api import (
    JinkouAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    QimenAnalysisRequest,
    TaiyiAnalysisRequest,
    ZiweiBirthRequest,
    ZiweiRulesRequest,
)
from fatebridge.mcp_server import (
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
    assert jinkou_request.model_dump()["selected_sections"] == [
        "起盘信息",
        "金口诀四位",
    ]
    assert runyear_request.model_dump()["birth_year"] == 1994
    assert runyear_request.model_dump()["selected_sections"] == ["起盘信息", "行年"]
    assert rules_request.model_dump()["year_stem"] == "甲"
    assert rules_request.model_dump()["selected_sections"] == [
        "规则概览",
        "当前天干四化",
    ]


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
    assert set(result["ziwei_birth"]["sihua"].keys()) == {
        "化禄",
        "化权",
        "化科",
        "化忌",
    }
    assert any(
        "紫微" in "、".join(palace["stars"])
        for palace in result["ziwei_birth"]["palaces"]
    )
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
    assert set(result["focused_rules"]["sihua"].keys()) == {
        "化禄",
        "化权",
        "化科",
        "化忌",
    }
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

    assert result["snapshot_export"]["selected_sections"] == [
        "规则概览",
        "当前天干四化",
    ]
    assert "[规则概览]" in result["snapshot_export"]["export_text"]
    assert "[当前天干四化]" in result["snapshot_export"]["export_text"]
    assert "[四化总表]" not in result["snapshot_export"]["export_text"]


def test_fastmcp_metaphysics_tools_expose_compact_controls():
    for tool in (
        ziwei_birth,
        ziwei_rules,
        liureng_gods,
        liureng_runyear,
        qimen,
        taiyi,
        jinkou,
    ):
        properties = tool.parameters["properties"]
        assert "compact" in properties
        assert "include_snapshot_text" in properties
        assert "fields" in properties


def test_fastmcp_ziwei_birth_compact_mode_can_drop_snapshot_text():
    rendered = ziwei_birth.fn(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        compact=True,
        include_snapshot_text=False,
    )

    payload = json.loads(rendered)

    assert "snapshot_text" not in payload
    assert "snapshot_export" in payload
    assert "\n" not in rendered


def test_fastmcp_ziwei_birth_fields_projection_trims_to_subset():
    rendered = ziwei_birth.fn(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        fields=["snapshot_export"],
    )

    payload = json.loads(rendered)

    # Only the requested key survives; run_metadata is always preserved.
    assert set(payload) <= {"snapshot_export", "run_metadata"}
    assert "snapshot_export" in payload
    assert "snapshot_text" not in payload
    assert isinstance(payload.get("run_metadata"), dict)


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


def test_liureng_runyear_independent_of_birth_pillars(monkeypatch):
    # 大六壬行年以「分析时刻」起课，不依赖出生四柱的构建。
    # 回归测试：曾有一处废弃的 _build_person_seed(person) 调用，会让非法出生数据
    # 误使整个行年分析报错。即便出生四柱构建失败，行年分析也应正常返回。
    import fatebridge.services.metaphysics as meta

    def _boom(*args, **kwargs):
        raise ValueError("行年分析不应依赖出生四柱")

    monkeypatch.setattr(meta, "_build_person_seed", _boom)

    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
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

    assert "error" not in result
    assert result["analysis_type"] == "大六壬行年"
    assert result["runyear"]["engine"] == "fatebridge-offline"


def test_calculate_liureng_gods_distinguishes_liuhe_style():
    # 2028-04-06 09:33 (辛酉日巳时, 月将戌)：经典 大六壬 四课 中 一课 上下相合 (上卯下戌)，
    # 但 三/四课 出现下贼上，按 贼克优先 规则，整体课体判为 "重审"。此用例验证一课
    # 的 六合 关系仍被识别出来，并且不被错误地提升为 board_style。
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

    assert (
        result["liureng"]["four_lessons"][0]["relations"]["with_day_branch"] == "六合"
    )
    assert (
        result["liureng"]["four_lessons"][0]["relations"]["with_lower_branch"] == "六合"
    )
    assert result["liureng"]["four_lessons"][0]["style_hint"] == "六合"
    assert result["liureng"]["board_style"] == "重审"


def test_calculate_liureng_gods_uses_zeike_transmission_rule():
    # 2028-04-06 09:33 (辛酉日巳时, 月将戌) 经典 发用：
    # 四课中 课1 上卯下戌 为上克下 (卯木克戌土 — classically 克; relation 六害 but 上克下),
    # 课3/4 出现下贼上 (寅木克酉金...)。按贼克优先，发用落课4 未(土)下寅(木)，为下贼上。
    # 三传依次 初=未, 中=sky[未]=子, 末=sky[子]=巳 (月将戌加占时巳偏移+5)。
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
    assert result["liureng"]["board_style"] == "重审"
    assert transmissions["initial"]["branch"] == "未"
    assert transmissions["middle"]["branch"] == "子"
    assert transmissions["final"]["branch"] == "巳"


def test_calculate_liureng_gods_uses_fanyin_transmission_rule():
    # 经典返吟条件：月将 与 占时 正好相冲。 2026-01-01 冬至期 月将=丑，故占时需落 未时
    # (丑冲未)，即 13:00-15:00。14:00 = 未时。
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=1,
        analysis_hour=14,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    transmissions = result["liureng"]["three_transmissions"]
    assert result["liureng"]["board_style"] == "返吟"
    assert transmissions["method"] == "返吟取冲"
    # 阴日 (乙)：初=支上 (亥的上神=sky[亥]=巳)；中=初之冲=亥；末=sky[中]=巳。
    assert transmissions["initial"]["branch"] == "巳"
    assert transmissions["middle"]["branch"] == "亥"
    assert transmissions["final"]["branch"] == "巳"


def test_calculate_liureng_gods_uses_fuyin_transmission_rule():
    # 经典伏吟：月将 == 占时。 2026-01-01 冬至期 月将=丑，02:00 = 丑时，正好伏吟。
    # 乙亥日是阴日 → 初传=支上神=亥 (伏吟下 sky=earth，上=下)。中=干上神=辰 (乙寄辰)。
    # 末=中之刑，辰为自刑支 → 末=辰。
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
    assert transmissions["initial"]["branch"] == "亥"
    assert transmissions["middle"]["branch"] == "辰"
    assert transmissions["final"]["branch"] == "辰"


def test_calculate_liureng_gods_prefers_zeike_over_yaoke():
    # 2026-01-01 18:00 (乙亥日酉时, 月将丑) 四课上下存在 下贼上 (课4 未克卯)，
    # 依 贼克优先 于 遥克 原则，应以 重审 为课体，而非 遥克。选用课 index=4。
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

    assert result["liureng"]["board_style"] == "重审"
    assert result["liureng"]["board_style_detail"] == "重审"
    assert result["liureng"]["meta"]["selected_lesson_index"] == 4


def test_calculate_liureng_gods_marks_bazhuan_detail():
    # 八专课需干支共位 (日干寄宫 == 日支)。 2026-02-09 是甲寅日 (甲寄寅=支寅)。
    # 立春期 月将=子，10:00=巳时。四课上下皆来自 sky[寅] / sky[其上神]，仅两套，
    # 形成典型 "八专" 课体。
    result = calculate_liureng_gods(
        analysis_year=2026,
        analysis_month=2,
        analysis_day=9,
        analysis_hour=10,
        analysis_minute=0,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
        gender="男",
    )

    assert result["liureng"]["board_style_detail"] == "八专"
    assert any(pattern["name"] == "八专课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_bieze_detail():
    # 别责课：四课之间无上下克贼，初传依下生上之义取用。 2026-01-02 10:00 (丙子日巳时)
    # 月将=丑，四课上下皆 下生上/上生下，无克贼，课体判为 "别责"。
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

    assert result["liureng"]["board_style_detail"] == "别责"
    assert result["liureng"]["meta"]["selected_lesson_relation"] == "下生上"
    assert any(pattern["name"] == "别责课" for pattern in result["liureng"]["patterns"])


def test_calculate_liureng_gods_marks_zhongshen_detail():
    # 重审课 = 下贼上。 2026-01-06 09:00 (庚辰日巳时) 月将=丑。四课中 课2 上子下辰为下贼上
    # (辰土克子水)，发用从 课2，整体课体为 "重审"。
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

    assert result["liureng"]["board_style_detail"] == "重审"
    assert result["liureng"]["meta"]["selected_lesson_relation"] == "下贼上"
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
    assert (
        result["qimen"]["palaces"][0]["content_palace"]
        == result["qimen"]["palaces"][0]["name"]
    )
    assert (
        result["qimen"]["palaces"][0]["content_trigram"]
        == result["qimen"]["palaces"][0]["trigram"]
    )
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

    # 121.4737°E sits east of the 120°E standard meridian, so true solar time
    # runs AHEAD of the wall clock. A 1.4737° offset adds ~5.89 min, moving
    # 21:18 civil time to 21:23:53 solar time.
    assert result["analysis_context"]["time_algorithm"] == "真太阳时"
    assert result["analysis_context"]["corrected_datetime"].startswith(
        "2026-04-04 21:23:"
    )
    assert result["analysis_context"]["total_correction_minutes"] == pytest.approx(
        5.89, abs=0.05
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
    assert (
        optioned_result["qimen"]["zhifu"]["content_palace"]
        == optioned_zhifu_palace["content_palace"]
    )
    assert (
        optioned_result["qimen"]["zhifu"]["content_trigram"]
        == optioned_zhifu_palace["content_trigram"]
    )
    assert (
        optioned_result["qimen"]["zhishi"]["content_palace"]
        == optioned_zhishi_palace["content_palace"]
    )
    assert (
        optioned_result["qimen"]["zhishi"]["content_trigram"]
        == optioned_zhishi_palace["content_trigram"]
    )


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
    assert result["snapshot_export"]["selected_sections"] == [
        "起盘信息",
        "九宫方盘",
        "离九宫",
    ]
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
    # 太乙統宗 人道命法 (ji_style=0)，对齐参考实现 kintaiyi。2026-04-04 21:18
    # 真太阳 → 四柱 丙午/辛卯/戊申/癸亥，农历年 2026 → 积年数 10155943，
    # 局数 = 10155943 % 72 = 55 → 陽遁五十五局；太乙落宫 艮、文昌(天目) 申。
    assert result["taiyi"]["taiyi_palace"] == "艮"
    assert result["taiyi"]["wenchang_palace"] == "申"
    assert len(result["taiyi"]["palace_marks"]) == 16
    assert result["taiyi"]["core_board"]["main_calculation"] == "陽遁五十五局"
    assert result["taiyi"]["core_board"]["kook_number"] == 55
    assert result["taiyi"]["core_board"]["shiji"] == "艮"
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

    assert result["snapshot_export"]["selected_sections"] == [
        "起盘信息",
        "三传",
        "概览",
    ]
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
    # 戊日亥时夜贵 → guiren_start=未 反布 → 亥位落 太常 (金口诀贵神)。
    assert result["jinkou"]["overview"]["guishen"]["name"] == "太常"
    assert (
        result["jinkou"]["overview"]["board_style"] == result["liureng"]["board_style"]
    )
    # 当前为元首课，四位同旺时 JINKOU_USE_POSITION_PREFERENCE["元首"]="贵神"，但依具体旺衰
    # 规则最终落实在哪一位上取决于四位力量排序。此用例用 `in` 断言保证返回 of the 标准集合。
    assert result["jinkou"]["overview"]["use_position"] in {
        "人元",
        "贵神",
        "将神",
        "地分",
    }
    assert len(result["jinkou"]["rows"]) == 4
    assert result["jinkou"]["overview"]["yuejiang"]["name"]
    assert result["jinkou"]["overview"]["guishen"]["name"]
    assert result["jinkou"]["shensha"]
    assert "[金口诀速览]" in result["snapshot_text"]
    assert "[金口诀四位]" in result["snapshot_text"]
    assert "[四位神煞]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_jinkou_analysis_uses_liureng_detail_to_break_ties():
    # 2026-01-02 10:00 (丙子日巳时, 月将丑) 四课无克贼，课体判为 "别责"。
    # 金口诀借此 detail 在四位旺衰并列时落实 use_position="地分"。
    result = calculate_jinkou_analysis(
        analysis_year=2026,
        analysis_month=1,
        analysis_day=2,
        analysis_hour=10,
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


def test_ziwei_birth_palaces_have_stars_detail():
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
    palaces = result["ziwei_birth"]["palaces"]

    for palace in palaces:
        # additive: legacy `stars` list is preserved unchanged
        assert "stars" in palace
        assert "stars_detail" in palace
        # a star-less palace must still carry stars_detail as an empty list
        assert isinstance(palace["stars_detail"], list)
        assert len(palace["stars_detail"]) == len(palace["stars"])
        for legacy, detail in zip(palace["stars"], palace["stars_detail"]):
            assert legacy == detail["label"]
            assert set(detail.keys()) == {"name", "label", "brightness", "mutagen"}

    # at least one major star must carry a non-null brightness
    all_details = [d for p in palaces for d in p["stars_detail"]]
    assert any(d["brightness"] is not None for d in all_details)

    # mutagen parsing: any 化X suffix in legacy stars surfaces in detail.mutagen
    for palace in palaces:
        for detail in palace["stars_detail"]:
            if detail["mutagen"] is not None:
                assert detail["label"] == f"{detail['name']}{detail['mutagen']}"
                assert detail["mutagen"] in {"化禄", "化权", "化科", "化忌"}


def test_ziwei_snapshot_text_annotates_brightness():
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
    snapshot = result["snapshot_text"]

    # brightness must render as `star(brightness)` — a brightness char in
    # parentheses immediately after a star name (e.g. "紫微(庙)", "廉贞化禄(利)"),
    # not merely somewhere in the text.
    assert re.search(r"[一-鿿]+\([庙旺得利平不陷]\)", snapshot)


def test_ziwei_horoscope_request_requires_target_datetime():
    from fatebridge.core.request_models import ZiweiHoroscopeRequest

    req = ZiweiHoroscopeRequest(
        gender="男",
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        target_year=2026,
        target_month=6,
        target_day=19,
        target_hour=14,
    )
    payload = req.model_dump()
    assert payload["target_year"] == 2026
    assert payload["target_month"] == 6
    assert payload["target_day"] == 19
    assert payload["target_hour"] == 14

    import pytest as _pytest
    from pydantic import ValidationError

    with _pytest.raises(ValidationError):
        ZiweiHoroscopeRequest(  # missing target_* → invalid
            gender="男",
            birth_year=1994,
            birth_month=8,
            birth_day=23,
            birth_hour=14,
        )


def test_calculate_ziwei_horoscope_returns_six_scopes_and_snapshot():
    from fatebridge.services.metaphysics import calculate_ziwei_horoscope

    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        gender="男",
    )
    result = calculate_ziwei_horoscope(
        person,
        target_year=2026,
        target_month=6,
        target_day=19,
        target_hour=14,
    )
    assert result["analysis_type"] == "紫微斗数运限"
    h = result["ziwei_horoscope"]
    assert h["engine"] == "fatebridge-offline"
    assert h["nominal_age"] == 2026 - 1994 + 1  # 虚岁 drives 大限 selection
    assert {s["scope"] for s in h["scopes"]} == {
        "大限",
        "小限",
        "流年",
        "流月",
        "流日",
        "流时",
    }
    assert "[起盘信息]" in result["snapshot_text"]
    assert "[流年]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_ziwei_horoscope_supports_selected_sections():
    from fatebridge.services.metaphysics import calculate_ziwei_horoscope

    person = create_person_info(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        gender="男",
    )
    result = calculate_ziwei_horoscope(
        person,
        target_year=2026,
        target_month=6,
        target_day=19,
        target_hour=14,
        selected_sections=["流年"],
    )
    assert result["snapshot_export"]["selected_sections"] == ["流年"]
    assert "[流年]" in result["snapshot_export"]["export_text"]
    assert "[起盘信息]" not in result["snapshot_export"]["export_text"]


def test_ziwei_horoscope_registered_on_all_surfaces():
    from fatebridge.services.tool_catalog import mcp_specs, rest_specs

    assert any(getattr(s, "key", None) == "ziwei_horoscope" for s in rest_specs())
    assert any(getattr(s, "mcp_name", None) == "ziwei_horoscope" for s in mcp_specs())


def test_qimen_qinxing_zhishi_is_always_death_door():
    """天禽星作值符时值使门恒为「死」——锁定已验证规则。

    天禽寄坤宫（死门），故禽为值符时值使门恒为死门，与阴/阳遁、节气无关。
    已对照权威实现 kentang2017/kinqimen 验证：禽为值符的多个时辰/落宫下，
    其「值使門」均为「死」（如 2024-01-04 多个时辰：禽→中/離/艮/兌，门皆死）。
    本测试防止该规则被误改或被「补」成随遁向/节气变化的伪逻辑。
    """
    from fatebridge.core.metaphysics.qimen import _qimen_resolve_special_zhishi

    assert _qimen_resolve_special_zhishi(dun_type="阳", current_term="冬至") == "死"
    assert _qimen_resolve_special_zhishi(dun_type="阴", current_term="夏至") == "死"
    assert _qimen_resolve_special_zhishi(dun_type="阳") == "死"
