#!/usr/bin/env python3
from __future__ import annotations

"""
FateBridge FastMCP Server - 命运之桥：连接古典智慧与现代技术的命理工具

Provides Chinese metaphysics and offline astrology functionality via FastMCP:
1. analyze_destiny - Individual destiny analysis
2. two_person_compatibility - Compatibility analysis between two people
3. timing_analysis - Comprehensive timing (luck period) analysis
4. astro_chart family - Core chart, relative chart, and derived chart overlays
5. export_registry / export_parse - FateBridge export helpers
6. knowledge_registry / knowledge_read - Bundled hover-knowledge helpers
7. jieqi_year / nongli_time - Calendar helper tools
8. gua_lookup / gua_meiyi - Offline trigram/hexagram lookup helpers
9. meihua_analysis - Mei Hua Yi Shu time-seeded divination
10. tongshefa - Local tongshefa analysis
11. sixyao - Local six-yao analysis
12. suzhan - Local lunar-mansion chart output
13. otherbu - Local astrology-dice output
14. sanshiunited - Local Sanshi aggregation output
15. bazi_birth - Standalone BaZi birth chart snapshot
16. liushi_analysis - Standalone flow-hour timing snapshot
17. solarreturn - Standalone solar return snapshot
18. lunarreturn - Standalone lunar return snapshot
19. transit - Standalone transit snapshot
20. solararc - Standalone solar arc snapshot
21. givenyear - Standalone given-year chart snapshot
22. profection - Standalone annual profection snapshot
23. pd - Standalone primary-directions snapshot
24. pdchart - Standalone primary-direction chart snapshot
25. zr - Standalone zodiacal releasing snapshot
26. firdaria - Standalone firdaria snapshot
27. decennials - Standalone decennials snapshot
"""

import logging
import os
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from fatebridge import __version__ as APP_VERSION
from fatebridge.mcp_transport import ProtocolResult, protocol_result
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.utils.errors import error_response_payload
from fatebridge.utils.formatting import (
    _prepare_json_response_payload,
    format_json_response,
)
from fatebridge.utils.runtime import get_log_level, load_runtime_env

# ============================================================================
# Logging Setup
# ============================================================================

load_runtime_env()

logging.basicConfig(
    level=getattr(logging, get_log_level(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


# =============================================================================
# FastMCP 应用配置
# =============================================================================

_MCP_INSTRUCTIONS = (
    "FateBridge 提供本地计算数据，解读必须依据返回字段。"
    "已连接时直接进入咨询流程；用户未要求开发排错时，不搜仓库或运行安装诊断。"
    "出生类分析先核对历法、日期、出生小时、地点/时区与适用性别规则；"
    "资料缺失或日期明显无效时先一次简短追问，不提前检索工具、加载契约或排盘，"
    "不能填 0 或套用示例。"
    "只有时段时保留不确定性，不能沿用确定时刻的结果；当前没有无时盘接口。"
    "住宅布局缺户型或实测朝向时先追问，不能猜方向。"
    "双人关系未说明类型时用 general，不能从性别推断婚姻。"
    "信息齐全且已发布工具的参数 Schema 与描述足够时，直接调用相关工具，"
    "不要为了常规咨询先列资源或重复读取契约；首轮字段建议已在工具描述中。"
    "代码模式检索 ALL_TOOLS 时一次取所需主证的完整条目，不先输出全部候选再检索同一工具，"
    "也不要只取名称而漏掉参数定义；获取完整定义后直接计算。"
    "按主证/必要旁证选最少调用；只在工具选择不明确时读 fatebridge://scenarios，"
    "或 fatebridge://catalog/summary，场景路由在 fatebridge://scenarios/{scenario}。"
    "只在参数仍不清楚时读 fatebridge://tools/{tool}/input；"
    "需要更细字段时才读 fatebridge://tools/{tool} 的完整输出契约。"
    "用 fields 与 strict_fields=true 裁剪结果，保留 run_metadata；"
    "后续调用沿用前次 run_metadata.trace_id，将 run_id 用作 parent_run_id。"
    "isError=true 时按 error_code/issues 修正，仅 retryable=true 才重试。"
    "按精度字段说明近似或 partial 结果，多体系分歧须保留。"
    "先用普通话回答问题，再解释字段依据；分清计算、传统规则与现实建议。"
    "常规首轮约200–300字，给2–3条依据和一项现实建议，用户要深入时再扩展。"
    "回执保留在工具结果中，普通回复不展示完整run_id；有精度警告时简短说明。"
    "不同口径分数不能平均或视为成功概率，不能据此决定辞职或关系成败。"
)


def _tool_response_payload(
    data: Dict[str, Any],
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
    fields: Optional[list] = None,
    strict_fields: bool = False,
    tool_name: Optional[str] = None,
) -> Dict[str, Any]:
    # tool_name is supplied by the catalog registrar (spec.run_metadata_name);
    # the neutral fallback only guards a stray non-catalog caller.
    payload = attach_run_metadata(data, tool_name=tool_name or "unknown_tool")
    # Project AFTER run_metadata is attached so provenance survives a field
    # selection (project_fields always keeps run_metadata).
    payload = project_fields(payload, fields, strict_fields=strict_fields)
    return _prepare_json_response_payload(
        payload,
        include_snapshot_text=include_snapshot_text,
    )


def _render_protocol_response(data: Dict[str, Any], **flags: Any) -> ProtocolResult:
    payload = _tool_response_payload(data, **flags)
    return protocol_result(
        payload,
        failed=False,
        text=format_json_response(payload, compact=flags.get("compact", True)),
    )


def _render_protocol_error(
    data: Dict[str, Any], operation: str, *, compact: bool = True
) -> ProtocolResult:
    payload = error_response_payload(data, operation)
    return protocol_result(
        payload, failed=True, text=format_json_response(payload, compact=compact)
    )


# ============================================================================
# Tool registration — every tool is declared once in the central catalog and
# auto-registered here. To add a tool, edit fatebridge/services/tool_catalog.py.
# ============================================================================

from fatebridge.application.discovery import select_specs
from fatebridge.application.projection import project_fields
from fatebridge.mcp_transport import (  # noqa: E402
    SerializableSchemaMiddleware,
    register_discovery_resources,
)
from fatebridge.services.tool_catalog import CATALOG  # noqa: E402
from fatebridge.transports.mcp import register_mcp


def create_mcp_app(
    families: Optional[str] = None,
    scenarios: Optional[str] = None,
) -> FastMCP:
    """Host-level family profiles; an omitted profile retains every MCP tool."""
    server = FastMCP(
        name="fatebridge",
        instructions=_MCP_INSTRUCTIONS,
        version=APP_VERSION,
        dereference_schemas=False,
    )
    server.add_middleware(SerializableSchemaMiddleware())
    exposed = select_specs(CATALOG, family=families, scenario=scenarios, surface="mcp")
    register_mcp(
        server,
        exposed,
        render_response=_render_protocol_response,
        render_error=_render_protocol_error,
    )
    register_discovery_resources(server, CATALOG, exposed)
    return server


app = create_mcp_app(
    os.getenv("FATEBRIDGE_MCP_FAMILIES") or None,
    os.getenv("FATEBRIDGE_MCP_SCENARIOS") or None,
)


def main() -> None:
    app.run(show_banner=False)


if __name__ == "__main__":
    main()
