"""Astrology tool declarations and domain binding helpers."""

from __future__ import annotations

from typing import List

from fatebridge.application.bindings import raw_invoke
from fatebridge.application.tool_spec import ToolSpec
from fatebridge.core.requests.astrology import (
    AstroChartPolyRequest,
    AstroChartRequest,
    AstroRelativeFlatRequest,
    AstroRelativeRequest,
)
from fatebridge.services.catalog.astro_bindings import (
    _astro_chart_bind,
    _astro_relative_flat_bind,
    _astro_relative_rest_bind,
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
)


def _chart_spec(
    key: str,
    rest_path: str,
    mcp_name: str,
    variant: str,
    label: str,
    metadata_name: str,
) -> ToolSpec:
    return ToolSpec(
        key=key,
        bind=raw_invoke(
            calculate_core_chart_analysis, fixed={"chart_variant": variant}
        ),
        request_model=AstroChartRequest,
        summary=f"离线{label}（优先本地高精度星历，缺失时回退近似模型）。",
        operation_label_zh=label,
        family="astro",
        rest_path=rest_path,
        mcp_name=mcp_name,
        metadata_name=metadata_name,
    )


SPECS: List[ToolSpec] = [
    # --- Astrology charts --------------------------------------------------
    ToolSpec(
        key="astro_chart",
        bind=_astro_chart_bind,
        request_model=AstroChartPolyRequest,
        summary=(
            "离线核心星盘：默认本命盘；可选 chart_variant 切换盘式"
            "（chart13=13星座 / hellen_chart=希腊 / guolao_chart=果老星宗 / "
            "india_chart=印度 / germany=德国盘引擎），等价于对应的 astro_chart13 等专用工具。"
        ),
        operation_label_zh="星盘",
        family="astro",
        rest_path="/api/astro/chart",
        mcp_name="astro_chart",
        metadata_name="chart",
    ),
    _chart_spec(
        "astro_chart13",
        "/api/astro/chart13",
        "astro_chart13",
        "chart13",
        "13星座盘",
        "chart13",
    ),
    _chart_spec(
        "astro_hellen",
        "/api/astro/hellen",
        "astro_hellen_chart",
        "hellen_chart",
        "希腊盘",
        "astro_hellen_chart",
    ),
    _chart_spec(
        "astro_guolao",
        "/api/astro/guolao",
        "astro_guolao_chart",
        "guolao_chart",
        "果老星宗盘",
        "astro_guolao_chart",
    ),
    _chart_spec(
        "astro_india",
        "/api/astro/india",
        "astro_india_chart",
        "india_chart",
        "印度盘",
        "astro_india_chart",
    ),
    ToolSpec(
        key="astro_germany",
        bind=raw_invoke(calculate_germany_chart_analysis),
        request_model=AstroChartRequest,
        summary="离线德国盘。",
        operation_label_zh="德国盘",
        family="astro",
        rest_path="/api/astro/germany",
        mcp_name="astro_germany_chart",
        metadata_name="germany",
    ),
    # The relative/合盘 tool is exposed as ONE logical tool through two request
    # shapes: a nested inner/outer model on REST, and a flat inner_/outer_ model
    # on MCP. They INTENTIONALLY share a single provenance name
    # (``astro_relative_chart``) so downstream metrics/logs treat them as one
    # tool regardless of surface — this parity is locked by
    # tests/test_api_alignment.py (both surfaces assert the same run_metadata
    # tool_name). The ``metadata_name`` override on the REST spec is what aligns
    # its provenance to the MCP name; do not split them without updating that test.
    ToolSpec(
        key="astro_relative",
        bind=_astro_relative_rest_bind,
        request_model=AstroRelativeRequest,
        summary="离线关系/合盘（与 astro_relative_chart 同一计算，本工具用嵌套 inner/outer 结构，REST 端）。",
        operation_label_zh="关系星盘分析",
        family="astro",
        rest_path="/api/astro/relative",
        mcp_name=None,
        metadata_name="astro_relative_chart",
    ),
    ToolSpec(
        key="astro_relative_chart",
        bind=_astro_relative_flat_bind,
        request_model=AstroRelativeFlatRequest,
        summary="离线关系/合盘（与 astro_relative 同一计算，本工具用扁平 inner_/outer_ 参数，MCP 端）。",
        operation_label_zh="关系星盘分析",
        family="astro",
        rest_path=None,
        mcp_name="astro_relative_chart",
    ),
]
