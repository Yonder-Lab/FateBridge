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
from fastmcp.tools import ToolResult

from fatebridge import __version__ as APP_VERSION
from fatebridge.mcp_transport import protocol_result
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
    "先按所选计算核对必要资料；八字/紫微等出生排盘需历法、日期、出生小时、地点/时区与适用性别规则。"
    "命卦可传 birth_date，非立春当日无需出生小时；不将出生排盘要求套用于命卦。"
    "必要资料缺失或日期明显无效时先一次简短追问，不提前加载完整契约或排盘，"
    "不能填 0 或套用示例。"
    "只有时段时保留不确定性，不能沿用确定时刻的结果；当前没有无时盘接口。"
    "风水布局使用通用 fengshui_assess，设 analyze_layout=true；提供已确认 placements/features。"
    "工位/合租场景依次审查九宫飞星、金锁，八宅个人命卦独立；不将本人或周围人的八字紫微喜忌代入环境，不以年盘替代历史宅盘。"
    "environmental_context保存方向/户型偏移/中心确认、家庭辈分排行、多层院落与环境事实；家庭人物对应不要求生辰，不按实际决策权取代辈分。"
    "household_scope=symbolic_reference只解释卦名与对宫，不追罗盘；家庭索引适用飞星/金锁，不能代替八宅命卦。"
    "缺方向不推实际卦位；厨卫/材质器形只按已注册规则，未覆盖保留；拱门开放厨房只轻提醒，院落归第一层，跨层按实际使用与共同因素复核。"
    "楼层subject_ids仅正向使用事实；负向排除需有关楼层及院落usage_confirmed与usage_evidence，名单须覆盖对象显式使用人。"
    "场景首轮fields可追加method_policy；有environmental_context时追加layout_analysis.environmental_context，细节解释按需读method_details。"
    "纯方法参考可用scene=home作查询标签、analyze_layout=false并按需投影method_details；无实际事实省略environmental_context，不造房屋或摆位。"
    "household_scope=symbolic_reference仅实际家庭资料的象意范围，不是通用reference_only开关。"
    "method_policy的优先方法审查与已选计算状态分开；available_engine_layers仅现状，候选单列，显式排除不反复追资料。"
    "有来源的厨卫/镜面/梁管/柱角等双对象关系用environmental_context.interior_relations，明确源/目标角色及必传可null的present；照片true/false均候选，相邻不补直接相对。"
    "材质器形用material_facts，属性独立确认；element_use仅代表物资格问题，不是个人喜用或环境所需元素，AFSI材料/颜色与FSI器形参考分开。"
    "仅相关输入存在时追加layout_analysis.interior_analysis或material_analysis；候选关系两端任一移动都重核，空间归属改变须声明location，不借搬转更换已确认物件属性。"
    "室内形态用 form_observations；methods=[] 可独立算已确认入口视野、入口直线和背靠，无需生辰/宅向。"
    "独立形态不造无位置/朝向的 placements 占位；观察只保留确认粒度，可见性不补相对位置，换座位后未确认的旧位置不沿用。"
    "现状观察与行动约束分别保存；目标、预算及禁止动作不能证明现有物件或物理条件，未知布尔观察省略，不能从允许或禁止动作补成 true/false。"
    "元素调节用 element_adjustments 绑定已有规则结果及明确目标；有条件物件按作者版本分列，不能推断缺五行。"
    "年度物件规则需显式选作者版本，不外推年份；距离只记录不造吉凶阈值，照片观察保留待确认状态。"
    "位置与朝向独立，未知项省略并使用部分计算，不能猜住宅朝向、立极、砂水或将桌朝向当落宫。"
    "布局建议结合用户目的及已说明的搬动、转向、预算和多人共用约束；缺某项约束不阻塞部分计算，只在影响行动时简短追问。"
    "同一对象只关联已确认使用人：一人用 subject_id，多人用 subject_ids（两者不同时传），未指定则按全部已提供住户计算；同住不代表共用，未明确的使用范围先核对，不把无关住户纳入共同方位。"
    "匹配方位只是规则候选，核对可行性再建议搬动；无共同方向或可行调整时保留权衡，不以摆件替代布局结论。"
    "方向布局对象支持门/床/书桌/灶，室内形态支持床/书桌/灶；其他家具不映射成这些用途，先说明未支持范围，生活建议另标。"
    "用户更正位置、朝向、观察或使用人时，以最新确认替换旧事实，重建受影响计算输入并沿用 trace_id/parent_run_id；只解释未变结果无需重算。"
    "根据实际规则说明位置/朝向、形态和元素候选；作者规则不能称全门派一致，未实现范围须明确，不用生活建议代替风水计算。"
    "布局咨询先区分个人匹配、室内形态、宅/年盘、桌面作者规则的覆盖，不把一个方向结论称完整审查。"
    "照片列候选事实，实际入口与经过通道单独确认；窗、背靠、物件材质及可行区域未知时保持未知。"
    "不可搬转时继续筛有规则依据且允许的动作；每项动作连接已确认事实、rule/source、作用域、目标位置和条件，缺项只追问会改变方案的资料。"
    "桌面规则用 surface_layouts 显式选 desktop_bagua_btb_v1，坐者近沿定位；surface_constraints 保存移动/新增许可及可行区域，不证明现状。"
    "surface 请求在首轮 fields 追加 layout_analysis.surface_analysis、rulesets；八宅个人匹配可追加 layers.bazhai.occupants，说明命卦不等于八字喜用。"
    "作者桌面BTB与罗盘八宅、年盘分别呈现，不自动用桌面左后代替东南；blocked/candidate_only 不能称可立即执行，无物件规则可明确保留，不编吉侧也不以整理建议充当任务完成。"
    "不同作用域不声称补偿、抵消或加分；conditional_option 未确认前不能放进立即执行清单。"
    "不要补造工具未返回的物件处方，未确认问题先核对；高背椅、靠垫、帘布不等于本规则的实体背靠，不用它们填补未知solid_backing。"
    "双人关系未说明类型时用 general，不能从性别推断婚姻。"
    "信息齐全且已发布工具的参数 Schema 与描述足够时，直接调用相关工具，"
    "不要为了常规咨询先列资源或重复读取契约；首轮字段建议已在工具描述中。"
    "代码模式检索 ALL_TOOLS 时一次取所需主证的完整条目，不先输出全部候选再检索同一工具，"
    "优先按工具名限定检索，不用所有工具共有的咨询说明做关键词匹配。"
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


def _render_protocol_response(data: Dict[str, Any], **flags: Any) -> ToolResult:
    from fatebridge.application.result_delivery import bound_response

    limit = flags.pop("response_char_limit", 8192)
    payload = _tool_response_payload(data, **flags)
    payload = bound_response(payload, limit, compact=flags.get("compact", True))
    return protocol_result(
        payload,
        failed=False,
        text=format_json_response(payload, compact=flags.get("compact", True)),
    )


def _render_protocol_error(
    data: Dict[str, Any], operation: str, *, compact: bool = True
) -> ToolResult:
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
