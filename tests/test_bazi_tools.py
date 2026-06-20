import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.api import BaziBirthRequest
from fatebridge.mcp_server import bazi_birth
from fatebridge.services.bazi import calculate_bazi_birth
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
    analysis_request = BaziBirthRequest(
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
    analysis_payload = analysis_request.model_dump()

    assert birth_payload["birth_timezone"] == "Asia/Shanghai"
    assert birth_payload["selected_sections"] == ["起盘信息", "四柱与三元"]
    assert analysis_payload["analysis_year"] == 2028
    assert analysis_payload["analysis_month"] == 4
    assert analysis_payload["analysis_day"] == 1
    assert analysis_payload["selected_sections"] == ["起盘信息", "流年行运概略"]


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
    assert set(result["bazi_birth"]["three_origins"]) == {
        "taiyuan",
        "minggong",
        "shengong",
    }
    assert "structure_profile" in result["bazi_birth"]
    assert "dominant_structure" in result["bazi_birth"]["structure_profile"]
    assert result["bazi_birth"]["timing_overview"]["liunian"]["pillar"] == "戊申"
    assert result["bazi_birth"]["timing_overview"]["liushi"]["pillar"]
    assert "[起盘信息]" in result["snapshot_text"]
    assert "[四柱与三元]" in result["snapshot_text"]
    assert "[流年行运概略]" in result["snapshot_text"]
    assert "[神煞（四柱与三元）]" in result["snapshot_text"]
    assert result["snapshot_export"]["export_text"] == result["snapshot_text"]


def test_calculate_bazi_birth_supports_selected_export_sections():
    result = calculate_bazi_birth(
        _build_person(),
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        selected_sections=["起盘信息", "流年行运概略"],
    )

    assert result["analysis_type"] == "八字命盘"
    assert result["bazi_birth"]["engine"] == "fatebridge-offline"
    assert result["bazi_birth"]["analysis_date"] == "2028-04-01"
    assert result["bazi_birth"]["timing_overview"]["liuyue"]["pillar"] == "乙卯"
    assert result["bazi_birth"]["timing_overview"]["liuri"]["pillar"] == "丙辰"
    assert result["bazi_birth"]["timing_overview"]["liushi"]["pillar"]
    assert "structure_profile" in result["bazi_birth"]
    assert result["snapshot_export"]["selected_sections"] == [
        "起盘信息",
        "流年行运概略",
    ]
    assert "[起盘信息]" in result["snapshot_export"]["export_text"]
    assert "[流年行运概略]" in result["snapshot_export"]["export_text"]
    assert "[四柱与三元]" not in result["snapshot_export"]["export_text"]


def test_fastmcp_bazi_tools_expose_parameters():
    birth_properties = bazi_birth.parameters["properties"]

    assert "selected_sections" in birth_properties
    assert "compact" in birth_properties
    assert "include_snapshot_text" in birth_properties
    assert "analysis_year" in birth_properties
    assert "analysis_month" in birth_properties


def test_fastmcp_bazi_birth_compact_mode_can_drop_snapshot_text():
    rendered = bazi_birth.fn(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        compact=True,
        include_snapshot_text=False,
    )

    payload = json.loads(rendered)

    assert "snapshot_text" not in payload
    assert "snapshot_export" in payload
    assert "\n" not in rendered


def test_fastmcp_bazi_birth_pretty_mode_keeps_snapshot_text():
    birth_properties = bazi_birth.parameters["properties"]

    rendered = bazi_birth.fn(
        birth_year=1994,
        birth_month=8,
        birth_day=23,
        birth_hour=14,
        name="张三",
        gender="男",
        birth_place="上海",
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        analysis_year=2028,
        analysis_month=4,
        analysis_day=1,
        compact=False,
        include_snapshot_text=True,
    )

    payload = json.loads(rendered)

    assert "snapshot_text" in payload
    assert "\n" in rendered
    assert "analysis_day" in birth_properties
    assert "analysis_year" in birth_properties
    assert "analysis_month" in birth_properties
    assert "selected_sections" in birth_properties
