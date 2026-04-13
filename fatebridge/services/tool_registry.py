"""
Shared transport tool descriptors for REST and FastMCP surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

from fatebridge.services.export_tools import (
    calculate_export_parse,
    calculate_export_registry,
)
from fatebridge.services.knowledge import (
    calculate_knowledge_read,
    calculate_knowledge_registry,
)
from fatebridge.services.western_timing_tools import (
    calculate_decennials,
    calculate_firdaria,
    calculate_givenyear,
    calculate_lunarreturn,
    calculate_pd,
    calculate_pdchart,
    calculate_profection,
    calculate_solararc,
    calculate_solarreturn,
    calculate_transit,
    calculate_zr,
)


ServiceCallable = Callable[..., Dict[str, Any]]


@dataclass(frozen=True)
class ToolDescriptor:
    key: str
    rest_path: str
    mcp_name: str
    request_model_name: Optional[str]
    service: ServiceCallable
    operation_label_zh: str
    summary: str
    supports_selected_sections: bool = False
    supports_snapshot_export: bool = False
    family: str = "misc"


def _descriptor(
    key: str,
    *,
    rest_path: str,
    request_model_name: Optional[str],
    service: ServiceCallable,
    operation_label_zh: str,
    summary: str,
    supports_selected_sections: bool = False,
    supports_snapshot_export: bool = False,
    family: str,
) -> ToolDescriptor:
    return ToolDescriptor(
        key=key,
        rest_path=rest_path,
        mcp_name=key,
        request_model_name=request_model_name,
        service=service,
        operation_label_zh=operation_label_zh,
        summary=summary,
        supports_selected_sections=supports_selected_sections,
        supports_snapshot_export=supports_snapshot_export,
        family=family,
    )


TOOL_REGISTRY: Dict[str, ToolDescriptor] = {
    "export_registry": _descriptor(
        "export_registry",
        rest_path="/api/export/registry",
        request_model_name="ExportRegistryRequest",
        service=calculate_export_registry,
        operation_label_zh="导出注册表",
        summary="返回 FateBridge 导出协议注册表。",
        family="export",
    ),
    "export_parse": _descriptor(
        "export_parse",
        rest_path="/api/export/parse",
        request_model_name="ExportParseRequest",
        service=calculate_export_parse,
        operation_label_zh="导出解析",
        summary="将快照文本解析为可筛选的结构化 section。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="export",
    ),
    "knowledge_registry": _descriptor(
        "knowledge_registry",
        rest_path="/api/knowledge/registry",
        request_model_name="KnowledgeRegistryRequest",
        service=calculate_knowledge_registry,
        operation_label_zh="知识目录",
        summary="列出内置知识域与分类。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="knowledge",
    ),
    "knowledge_read": _descriptor(
        "knowledge_read",
        rest_path="/api/knowledge/read",
        request_model_name="KnowledgeReadRequest",
        service=calculate_knowledge_read,
        operation_label_zh="知识读取",
        summary="读取单条内置知识并支持导出裁剪。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="knowledge",
    ),
    "solarreturn": _descriptor(
        "solarreturn",
        rest_path="/api/astro/timing/solarreturn",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_solarreturn,
        operation_label_zh="西占太阳返照",
        summary="生成独立太阳返照结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "lunarreturn": _descriptor(
        "lunarreturn",
        rest_path="/api/astro/timing/lunarreturn",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_lunarreturn,
        operation_label_zh="西占月亮返照",
        summary="生成独立月返结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "transit": _descriptor(
        "transit",
        rest_path="/api/astro/timing/transit",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_transit,
        operation_label_zh="西占行运盘",
        summary="生成独立行运结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "solararc": _descriptor(
        "solararc",
        rest_path="/api/astro/timing/solararc",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_solararc,
        operation_label_zh="西占太阳弧",
        summary="生成独立太阳弧结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "givenyear": _descriptor(
        "givenyear",
        rest_path="/api/astro/timing/givenyear",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_givenyear,
        operation_label_zh="西占指定年盘",
        summary="生成独立指定年盘结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "profection": _descriptor(
        "profection",
        rest_path="/api/astro/timing/profection",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_profection,
        operation_label_zh="西占年小限",
        summary="生成独立年小限结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "pd": _descriptor(
        "pd",
        rest_path="/api/astro/timing/pd",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_pd,
        operation_label_zh="西占主限",
        summary="生成独立主限结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "pdchart": _descriptor(
        "pdchart",
        rest_path="/api/astro/timing/pdchart",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_pdchart,
        operation_label_zh="西占主限法盘",
        summary="生成独立主限法盘结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "zr": _descriptor(
        "zr",
        rest_path="/api/astro/timing/zr",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_zr,
        operation_label_zh="西占黄道释放",
        summary="生成独立黄道释放结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "firdaria": _descriptor(
        "firdaria",
        rest_path="/api/astro/timing/firdaria",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_firdaria,
        operation_label_zh="西占法达星限",
        summary="生成独立法达结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
    "decennials": _descriptor(
        "decennials",
        rest_path="/api/astro/timing/decennials",
        request_model_name="WesternTimingModuleRequest",
        service=calculate_decennials,
        operation_label_zh="西占十年星限",
        summary="生成独立十年星限结果。",
        supports_selected_sections=True,
        supports_snapshot_export=True,
        family="western_timing_tool",
    ),
}


def get_tool_descriptor(key: str) -> ToolDescriptor:
    return TOOL_REGISTRY[key]


def iter_tool_descriptors(*, family: Optional[str] = None) -> Iterable[ToolDescriptor]:
    for descriptor in TOOL_REGISTRY.values():
        if family is not None and descriptor.family != family:
            continue
        yield descriptor
