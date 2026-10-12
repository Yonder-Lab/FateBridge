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
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from fatebridge import __version__ as APP_VERSION
from fatebridge.mcp_transport import ProtocolResult, protocol_result
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.utils.errors import error_response_payload
from fatebridge.utils.helpers import (
    _prepare_json_response_payload,
    format_error_response,
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

_MCP_INSTRUCTIONS = "中国传统八字、时运、节气/农历 helper、FateBridge 导出协议/悬浮知识 helper 与离线星盘测算工具（优先本地高精度 ephemeris，缺失时回退近似模型），提供单人分析、双人配合度、时运分析、梅花时卦辅助、卦义 helper 与核心/关系星盘。只输出计算数据，不包含建议。"


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


def _render_tool_response(data: Dict[str, Any], **flags: Any) -> str:
    payload = _tool_response_payload(data, **flags)
    return format_json_response(payload, compact=flags.get("compact", True))


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


def _render_tool_error(
    data: Dict[str, Any],
    operation: str,
    *,
    compact: bool = True,
) -> str:
    return format_error_response(data, operation, compact=compact)


# ============================================================================
# Tool registration — every tool is declared once in the central catalog and
# auto-registered here. To add a tool, edit fatebridge/services/tool_catalog.py.
# ============================================================================

from fatebridge.core.discovery import select_specs  # noqa: E402
from fatebridge.core.tool_spec import project_fields, register_mcp  # noqa: E402
from fatebridge.mcp_transport import (  # noqa: E402
    SerializableSchemaMiddleware,
    register_discovery_resources,
)
from fatebridge.services.tool_catalog import CATALOG  # noqa: E402


def create_mcp_app(
    families: Optional[str] = None,
    scenarios: Optional[str] = None,
    *,
    _legacy_exports: Optional[Dict[str, Any]] = None,
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
    registered = register_mcp(
        server,
        exposed,
        render_response=_render_tool_response,
        render_error=_render_tool_error,
        native_response=_render_protocol_response,
        native_error=_render_protocol_error,
    )
    if _legacy_exports is not None:
        for tool in registered:
            _legacy_exports[tool.name] = SimpleNamespace(
                fn=tool.fn.__fb_legacy_fn__,
                parameters=tool.parameters,
                schema=getattr(tool, "schema", None),
                description=tool.description,
            )
    register_discovery_resources(server, CATALOG, exposed)
    return server


app = create_mcp_app(
    os.getenv("FATEBRIDGE_MCP_FAMILIES") or None,
    os.getenv("FATEBRIDGE_MCP_SCENARIOS") or None,
    _legacy_exports=globals(),
)


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
