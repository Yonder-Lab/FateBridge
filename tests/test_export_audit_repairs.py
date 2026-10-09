"""Explicit export selections never broaden to unrequested sections."""

from fatebridge.core.export_parser import parse_export_content

CONTENT = "[秘密]\nprivate\n\n[公开]\npublic"


def test_unmatched_explicit_export_selection_returns_empty_text():
    result = parse_export_content(
        technique="generic", content=CONTENT, selected_sections=["不存在"]
    )
    assert result["export_text"] == ""
    assert result["missing_selected_sections"] == ["不存在"]
    assert not any(section["included"] for section in result["sections"])


def test_matching_export_selection_only_contains_requested_section():
    result = parse_export_content(
        technique="generic", content=CONTENT, selected_sections=["公开"]
    )
    assert result["export_text"] == "[公开]\npublic"


def test_empty_default_selection_keeps_existing_preset_behavior():
    result = parse_export_content(technique="generic", content=CONTENT)
    assert result["export_text"] == CONTENT


def test_unmatched_selection_excludes_untitled_preamble():
    result = parse_export_content(
        technique="generic",
        content="private preamble\n[公开]\npublic",
        selected_sections=["不存在"],
    )
    assert result["export_text"] == ""
    assert not any(section["included"] for section in result["sections"])


def test_matching_selection_excludes_untitled_preamble():
    result = parse_export_content(
        technique="generic",
        content="private preamble\n[公开]\npublic",
        selected_sections=["公开"],
    )
    assert result["export_text"] == "[公开]\npublic"
    assert result["sections"][0]["included"] is False


def test_no_explicit_selection_preserves_untitled_preamble():
    content = "private preamble\n[公开]\npublic"
    result = parse_export_content(technique="generic", content=content)
    assert "private preamble" in result["export_text"]
