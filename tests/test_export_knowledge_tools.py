import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api import (
    ExportParseRequest,
    ExportRegistryRequest,
    KnowledgeReadRequest,
    KnowledgeRegistryRequest,
)
from fastmcp_server import (
    export_parse,
    export_registry,
    knowledge_read,
    knowledge_registry,
)
from fatebridge.services.export_tools import (
    calculate_export_parse,
    calculate_export_registry,
)
from fatebridge.services.knowledge import (
    calculate_knowledge_read,
    calculate_knowledge_registry,
)


def test_export_request_models_accept_horosa_style_fields():
    registry_request = ExportRegistryRequest(technique="qimen")
    parse_request = ExportParseRequest(
        technique="qimen",
        content="[起盘信息]\n测试",
        selected_sections=["起盘信息", "八宫详解"],
        planetInfo={"showHouse": True, "showRuler": False},
        astroMeaning={"enabled": True},
    )
    knowledge_registry_request = KnowledgeRegistryRequest(domain="astro")
    knowledge_read_request = KnowledgeReadRequest(
        domain="astro",
        category="aspect",
        aspect_degree=90,
        object_a="Sun",
        object_b="Jupiter",
    )

    parse_payload = parse_request.model_dump(by_alias=True)
    knowledge_payload = knowledge_read_request.model_dump()

    assert registry_request.technique == "qimen"
    assert parse_payload["planetInfo"]["showHouse"] is True
    assert parse_payload["planetInfo"]["showRuler"] is False
    assert parse_payload["astroMeaning"]["enabled"] is True
    assert knowledge_registry_request.domain == "astro"
    assert knowledge_payload["aspect_degree"] == 90
    assert knowledge_payload["object_a"] == "Sun"
    assert knowledge_payload["object_b"] == "Jupiter"


def test_calculate_export_registry_matches_horosa_shape():
    result = calculate_export_registry(technique="qimen")

    assert result["settings_key"] == "horosa.ai.export.settings.v1"
    assert result["settings_version"] == 6
    assert result["selected_technique"]["key"] == "qimen"
    assert "奇门演卦" in result["selected_technique"]["preset_sections"]
    assert result["default_normalized_settings"]["sections"] == {}


def test_calculate_export_parse_normalizes_legacy_titles_and_filters_forbidden_sections():
    content = "\n".join(
        [
            "[起盘信息]",
            "排盘参数",
            "",
            "[右侧栏目]",
            "这里不该进入最终导出",
            "",
            "[八宫]",
            "这里是八宫详解内容",
            "",
            "[演卦]",
            "这里是奇门演卦内容",
        ]
    )

    result = calculate_export_parse(
        technique="qimen",
        content=content,
        selected_sections=["起盘信息", "八宫详解", "奇门演卦"],
    )

    assert result["section_titles_detected"] == ["起盘信息", "盘面要素", "八宫详解", "奇门演卦"]
    assert result["selected_sections"] == ["起盘信息", "八宫详解", "奇门演卦"]
    assert "这里不该进入最终导出" not in result["export_text"]
    assert "这里是八宫详解内容" in result["export_text"]
    assert "这里是奇门演卦内容" in result["export_text"]
    assert result["settings_used"]["sections"]["qimen"] == ["起盘信息", "八宫详解", "奇门演卦"]


def test_calculate_knowledge_registry_and_read_match_horosa_samples():
    registry = calculate_knowledge_registry(domain="astro")
    liureng = calculate_knowledge_read(domain="liureng", category="shen", key="子")
    qimen = calculate_knowledge_read(domain="qimen", category="door", key="休门")
    astro = calculate_knowledge_read(
        domain="astro",
        category="aspect",
        aspect_degree=90,
        object_a="Sun",
        object_b="Jupiter",
    )

    assert registry["domains"][0]["domain"] == "astro"
    assert any(category["name"] == "planet" for category in registry["domains"][0]["categories"])
    assert liureng["title"] == "神后子神"
    assert "类象" in liureng["rendered_text"]
    assert qimen["key"] == "休门"
    assert "休养" in qimen["rendered_text"]
    assert astro["title"].startswith("太阳 - 木星")
    assert "相位角：90°" in astro["tips"]


def test_knowledge_registry_full_domain_order_matches_horosa():
    registry = calculate_knowledge_registry()

    assert [item["domain"] for item in registry["domains"]] == ["astro", "liureng", "qimen"]


def test_export_and_knowledge_mcp_tools_return_json_strings():
    content = "\n".join(
        [
            "[起盘信息]",
            "排盘参数",
            "",
            "[八宫]",
            "这里是八宫详解内容",
            "",
            "[演卦]",
            "这里是奇门演卦内容",
        ]
    )

    export_registry_result = json.loads(export_registry.fn(technique="qimen"))
    export_parse_result = json.loads(
        export_parse.fn(
            technique="qimen",
            content=content,
            selected_sections=["起盘信息", "八宫详解", "奇门演卦"],
        )
    )
    knowledge_registry_result = json.loads(knowledge_registry.fn(domain="astro"))
    knowledge_read_result = json.loads(
        knowledge_read.fn(domain="qimen", category="door", key="休门")
    )

    assert export_registry_result["selected_technique"]["key"] == "qimen"
    assert "奇门演卦" in export_registry_result["selected_technique"]["preset_sections"]
    assert "这里是奇门演卦内容" in export_parse_result["export_text"]
    assert knowledge_registry_result["domains"][0]["domain"] == "astro"
    assert knowledge_read_result["key"] == "休门"
    assert "休养" in knowledge_read_result["rendered_text"]
