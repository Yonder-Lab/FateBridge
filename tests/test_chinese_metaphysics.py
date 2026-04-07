from pathlib import Path
import sys

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
    )

    payload = request.model_dump()

    assert payload["name"] == "张三"
    assert payload["gender"] == "男"
    assert payload["birth_hour"] == 14
    assert payload["birth_minute"] == 30
    assert payload["birth_timezone"] == "Asia/Shanghai"


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
    )
    qimen_request = QimenAnalysisRequest(
        analysis_year=2026,
        analysis_month=4,
        analysis_day=4,
        analysis_hour=21,
        analysis_minute=18,
        analysis_timezone="Asia/Shanghai",
        analysis_longitude=121.4737,
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
    )
    rules_request = ZiweiRulesRequest(year_stem="甲")

    assert liureng_request.model_dump()["analysis_longitude"] == 121.4737
    assert qimen_request.model_dump()["analysis_hour"] == 21
    assert taiyi_request.model_dump()["gender"] == "男"
    assert jinkou_request.model_dump()["di_fen"] == "酉"
    assert runyear_request.model_dump()["birth_year"] == 1994
    assert rules_request.model_dump()["year_stem"] == "甲"


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
    assert result["ziwei_birth"]["time_algorithm"] in {"直接时间", "真太阳时"}
    assert len(result["ziwei_birth"]["palaces"]) == 12
    assert result["ziwei_birth"]["ming_gong"]["name"] == "命宫"
    assert result["ziwei_birth"]["shen_gong"]["name"] == "身宫"
    assert set(result["ziwei_birth"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert any("紫微" in "、".join(palace["stars"]) for palace in result["ziwei_birth"]["palaces"])


def test_calculate_ziwei_rules_supports_year_stem_filter():
    result = calculate_ziwei_rules(year_stem="甲")

    assert result["analysis_type"] == "紫微规则库"
    assert result["requested_year_stem"] == "甲"
    assert result["focused_rules"]["year_stem"] == "甲"
    assert set(result["focused_rules"]["sihua"].keys()) == {"化禄", "化权", "化科", "化忌"}
    assert "palace_sequence" in result["rule_catalogue"]


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
    assert result["liureng"]["month_general"]["branch"]
    assert len(result["liureng"]["four_lessons"]) == 4
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]
    assert result["liureng"]["overview"]
    assert "空" in result["liureng"]["kongwang"]


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
    assert result["runyear"]["age"] > 0
    assert len(result["runyear"]["ganzhi"]) == 2
    assert result["liureng"]["three_transmissions"]["initial"]["branch"]


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
    assert result["taiyi"]["taiyi_palace"]
    assert len(result["taiyi"]["palace_marks"]) == 16
    assert result["taiyi"]["core_board"]["main_calculation"]


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
    assert result["jinkou"]["overview"]["di_fen"] == "酉"
    assert len(result["jinkou"]["rows"]) == 4
    assert result["jinkou"]["overview"]["yuejiang"]["name"]
    assert result["jinkou"]["overview"]["guishen"]["name"]
    assert result["jinkou"]["shensha"]


def test_fastmcp_tools_expose_new_parameters():
    assert "birth_year" in ziwei_birth.parameters["properties"]
    assert "year_stem" in ziwei_rules.parameters["properties"]
    assert "analysis_year" in liureng_gods.parameters["properties"]
    assert "birth_year" in liureng_runyear.parameters["properties"]
    assert "analysis_year" in qimen.parameters["properties"]
    assert "gender" in taiyi.parameters["properties"]
    assert "di_fen" in jinkou.parameters["properties"]
