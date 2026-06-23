"""
FateBridge export protocol services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fatebridge.core.export_contracts import build_export_registry
from fatebridge.core.export_parser import parse_export_content
from fatebridge.utils.helpers import calculation_guard, handle_calculation_error


@calculation_guard("导出注册表")
def calculate_export_registry(
    *,
    technique: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return the local AI-export registry in FateBridge's normalized registry shape.
    """
    return build_export_registry(technique=technique)


@calculation_guard("导出解析")
def calculate_export_parse(
    *,
    technique: str,
    content: str,
    selected_sections: Optional[List[str]] = None,
    planet_info: Optional[Dict[str, Any]] = None,
    astro_meaning: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Parse snapshot text into normalized export sections.
    """
    return parse_export_content(
        technique=technique,
        content=content,
        selected_sections=selected_sections,
        planet_info=planet_info,
        astro_meaning=astro_meaning,
    )
