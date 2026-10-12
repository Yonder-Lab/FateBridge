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

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from typing import Any, Dict, Optional

from fastmcp import FastMCP

from fatebridge import __version__ as APP_VERSION
from fatebridge.services.run_metadata import attach_run_metadata
from fatebridge.utils.helpers import format_error_response, format_json_response
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


def _render_tool_response(
    data: Dict[str, Any],
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
    fields: Optional[list] = None,
    strict_fields: bool = False,
    tool_name: Optional[str] = None,
) -> str:
    # tool_name is supplied by the catalog registrar (spec.run_metadata_name);
    # the neutral fallback only guards a stray non-catalog caller.
    payload = attach_run_metadata(data, tool_name=tool_name or "unknown_tool")
    # Project AFTER run_metadata is attached so provenance survives a field
    # selection (project_fields always keeps run_metadata).
    payload = project_fields(payload, fields, strict_fields=strict_fields)
    return format_json_response(
        payload,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
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
    families: Optional[str] = None, scenarios: Optional[str] = None
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
        render_response=_render_tool_response,
        render_error=_render_tool_error,
    )
    register_discovery_resources(server, CATALOG, exposed)
    return server


app = create_mcp_app(
    os.getenv("FATEBRIDGE_MCP_FAMILIES") or None,
    os.getenv("FATEBRIDGE_MCP_SCENARIOS") or None,
)


def _attach_fastmcp_legacy_metadata() -> None:
    """
    Expose each registered tool as a module-level attribute carrying `.fn` and
    `.parameters`, the contract some FateBridge tests and host integrations rely
    on. Keep this text-returning facade separate from the protocol callable,
    which returns structured data and a native MCP error flag.
    """

    async def _load_registered_tools() -> list[Any]:
        return list(await app.list_tools(run_middleware=False))

    try:
        registered_tools = asyncio.run(_load_registered_tools())
    except RuntimeError as exc:
        if "asyncio.run() cannot be called from a running event loop" not in str(exc):
            raise

        with ThreadPoolExecutor(max_workers=1) as executor:
            registered_tools = executor.submit(
                lambda: asyncio.run(_load_registered_tools())
            ).result()

    for tool in registered_tools:
        target = globals().get(tool.name)
        if callable(target):
            setattr(target, "fn", tool.fn)
            setattr(target, "parameters", tool.parameters)
            setattr(target, "schema", getattr(tool, "schema", None))
            setattr(target, "description", getattr(tool, "description", None))
        else:
            # Keep the documented in-process `.fn -> JSON text` compatibility
            # facade separate from the native protocol callable.
            globals()[tool.name] = SimpleNamespace(
                fn=getattr(tool.fn, "__fb_legacy_fn__", tool.fn),
                parameters=tool.parameters,
                schema=getattr(tool, "schema", None),
                description=tool.description,
            )


_attach_fastmcp_legacy_metadata()


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
