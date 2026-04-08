from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import BaziBirthRequest, BaziDirectRequest
from fastmcp_server import bazi_birth, bazi_direct
from fatebridge.services.bazi import calculate_bazi_birth, calculate_bazi_direct
from fatebridge.utils.helpers import create_person_info


def _build_person():
    return create_person_info(
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


def test_bazi_request_models_accept_birth_and_analysis_fields():
    birth_request = BaziBirthRequest(
        name="张三",
        gender="男",
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        selected_sections=["起盘信息", "四柱与三元"],
    )
    direct_request = BaziDirectRequest(
        name="张三",
        gender="男",
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        birth_minute=30,
        birth_place="上海",
        birth_timezone="Asia/Shanghai",
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        selected_sections=["起盘信息", "流年行运概略"],
    )

    birth_payload = birth_request.model_dump()
    direct_payload = direct_request.model_dump()

    assert birth_payload["birth_timezone"] == "Asia/Shanghai"
    assert birth_payload["selected_sections"] == ["起盘信息", "四柱与三元"]
    assert direct_payload["analysis_year"] == 2028
    assert direct_payload["analysis_month"] == 4
    assert direct_payload["analysis_day"] == 1
    assert direct_payload["selected_sections"] == ["起盘信息", "流年行运概略"]


def test_calculate_bazi_birth_returns_snapshot_sections():
    result = calculate_bazi_birth(
        _build_person(),
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
    )

    assert result["analysis_type"] == "八字命盘"
    assert result["bazi_birth"]["engine"] == "fatebridge-offline"
    assert result["bazi_birth"]["time_algorithm"] in {"直接时间", "真太阳时"}
    assert set(result["bazi_birth"]["four_pillars"]) == {"year", "month", "day", "hour"}
    assert set(result["bazi_birth"]["three_origins"]) == {"taiyuan", "minggong", "shengong"}
    assert result["bazi_birth"]["timing_overview"]["liunian"]["pillar"] == "戊申"
    assert "[起盘信息]" in result["snapshot_text"]
    assert "[四柱与三元]" in result["snapshot_text"]
    assert "[流年行运概略]" in result["snapshot_text"]
    assert "[神煞（四柱与三元）]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_bazi_direct_supports_selected_export_sections():
    result = calculate_bazi_direct(
        _build_person(),
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        selected_sections=["起盘信息", "流年行运概略"],
    )

    assert result["analysis_type"] == "八字直断"
    assert result["bazi_direct"]["engine"] == "fatebridge-offline"
    assert result["bazi_direct"]["analysis_date"] == "2028-04-01"
    assert result["bazi_direct"]["timing_overview"]["liuyue"]["pillar"] == "乙卯"
    assert result["bazi_direct"]["timing_overview"]["liuri"]["pillar"] == "丙辰"
    assert result["snapshot_export"]["selected_sections"] == ["起盘信息", "流年行运概略"]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[流年行运概略]" in result["snapshot_export"]["export_text"]
    assert "[四柱与三元]" not in result["snapshot_export"]["export_text"]


def test_fastmcp_bazi_tools_expose_parameters():
    birth_properties = bazi_birth.parameters["properties"]
    direct_properties = bazi_direct.parameters["properties"]

    assert "selected_sections" in birth_properties
    assert "analysis_year" in birth_properties
    assert "analysis_month" in birth_properties
    assert "analysis_day" in birth_properties
    assert "analysis_year" in direct_properties
    assert "analysis_month" in direct_properties
    assert "analysis_day" in direct_properties
    assert "selected_sections" in direct_properties
