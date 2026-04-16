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
16. bazi_direct - Standalone BaZi direct timing snapshot
17. liushi_analysis - Standalone flow-hour timing snapshot
18. solarreturn - Standalone solar return snapshot
19. lunarreturn - Standalone lunar return snapshot
20. transit - Standalone transit snapshot
21. solararc - Standalone solar arc snapshot
22. givenyear - Standalone given-year chart snapshot
23. profection - Standalone annual profection snapshot
24. pd - Standalone primary-directions snapshot
25. pdchart - Standalone primary-direction chart snapshot
26. zr - Standalone zodiacal releasing snapshot
27. firdaria - Standalone firdaria snapshot
28. decennials - Standalone decennials snapshot
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastmcp import FastMCP

from fatebridge.services.astrology import (
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
    calculate_relative_chart_analysis,
)
from fatebridge.services.bazi import (
    calculate_bazi_birth as calculate_bazi_birth_service,
)
from fatebridge.services.bazi import (
    calculate_bazi_direct as calculate_bazi_direct_service,
)
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.compatibility import calculate_compatibility_analysis
from fatebridge.services.divination import (
    calculate_gua_lookup,
    calculate_gua_meiyi,
    calculate_meihua_analysis,
    calculate_otherbu_analysis,
    calculate_sanshiunited_analysis,
    calculate_sixyao_analysis,
    calculate_suzhan_analysis,
    calculate_tongshefa_analysis,
)
from fatebridge.services.metaphysics import (
    calculate_jinkou_analysis as calculate_jinkou_analysis_service,
)
from fatebridge.services.metaphysics import (
    calculate_liureng_gods as calculate_liureng_gods_service,
)
from fatebridge.services.metaphysics import (
    calculate_liureng_runyear as calculate_liureng_runyear_service,
)
from fatebridge.services.metaphysics import (
    calculate_qimen_analysis as calculate_qimen_analysis_service,
)
from fatebridge.services.metaphysics import (
    calculate_taiyi_analysis as calculate_taiyi_analysis_service,
)
from fatebridge.services.metaphysics import (
    calculate_ziwei_birth as calculate_ziwei_birth_service,
)
from fatebridge.services.metaphysics import (
    calculate_ziwei_rules as calculate_ziwei_rules_service,
)
from fatebridge.services.timing import (
    calculate_comprehensive_timing,
    calculate_dayun_analysis,
    calculate_jieqi_timeline_analysis,
    calculate_jieqi_year,
    calculate_liunian_analysis,
    calculate_liuri_analysis,
    calculate_liushi_analysis,
    calculate_liuyue_analysis,
    calculate_nongli_time,
)
from fatebridge.services.run_metadata import (
    attach_run_metadata,
    infer_tool_name_from_payload,
)
from fatebridge.services.tool_registry import get_tool_descriptor
from fatebridge.services.western_timing import calculate_western_timing_analysis
from fatebridge.utils.helpers import (
    create_person_info,
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
logger = logging.getLogger(__name__)


# =============================================================================
# FastMCP 应用配置
# =============================================================================

app = FastMCP(
    name="fatebridge",
    instructions="中国传统八字、时运、节气/农历 helper、FateBridge 导出协议/悬浮知识 helper 与离线星盘测算工具（优先本地高精度 ephemeris，缺失时回退近似模型），提供单人分析、双人配合度、时运分析、梅花时卦辅助、卦义 helper 与核心/关系星盘。只输出计算数据，不包含建议。",
    version="2.4.0",
)


def _render_tool_response(
    data: Dict[str, Any],
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
    tool_name: Optional[str] = None,
) -> str:
    resolved_tool_name = tool_name or infer_tool_name_from_payload(data)
    payload = attach_run_metadata(data, tool_name=resolved_tool_name)
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


def _run_registry_tool(
    tool_key: str,
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
    **kwargs: Any,
) -> str:
    descriptor = get_tool_descriptor(tool_key)
    result = descriptor.service(**kwargs)

    if "error" in result:
        return _render_tool_error(result, descriptor.operation_label_zh, compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name=descriptor.key,
    )


@app.tool
def analyze_destiny(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> str:
    """
    个人命理分析工具

    根据出生年月日时计算个人命理分析，提供完整的分析，包括：
    - 四柱信息（年月日时柱的天干地支）
    - 日主分析（日干的五行属性、阴阳、强弱程度）
    - 五行分布（各五行在命局中的百分比）
    - 十神分析（根据日干与其他干支的关系确定十神）
    - 格局分析（三合、六合、六冲、刑害等特殊组合）
    - 喜用神（对命局有利的五行）

    Args:
        birth_year: 出生年份（公历），如1990
        birth_month: 出生月份，1-12
        birth_day: 出生日期，1-31
        birth_hour: 出生时辰，0-23（24小时制）
        name: 姓名（可选），默认为"未提供"
        gender: 性别（可选），默认为"未知"
        birth_place: 出生地（可选），默认为"未提供"
        birth_minute: 出生分钟，默认0
        birth_timezone: 出生时区（可选）
        birth_longitude: 出生地经度（可选）
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        JSON格式的字符串，包含完整的命理分析结果
    """

    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    data = calculate_destiny_analysis(person)
    return _render_tool_response(data, tool_name="analyze_destiny")


@app.tool
def bazi_birth(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    八字命盘工具

    根据出生信息生成离线八字命盘，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_bazi_birth_service(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "八字命盘", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="qimen",
    )


@app.tool
def bazi_direct(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    八字直断工具

    根据出生信息生成离线八字直断，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_bazi_direct_service(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "八字直断", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="taiyi",
    )


@app.tool
def two_person_compatibility(
    person1_name: str,
    person1_birth_year: int,
    person1_birth_month: int,
    person1_birth_day: int,
    person1_birth_hour: int,
    person2_name: str,
    person2_birth_year: int,
    person2_birth_month: int,
    person2_birth_day: int,
    person2_birth_hour: int,
    person1_gender: str = "未知",
    person1_birth_place: str = "未提供",
    person2_gender: str = "未知",
    person2_birth_place: str = "未提供",
    relationship_type: str = "general",
    *,
    person1_birth_minute: int = 0,
    person2_birth_minute: int = 0,
    person1_birth_timezone: Optional[str] = None,
    person2_birth_timezone: Optional[str] = None,
    person1_birth_longitude: Optional[float] = None,
    person2_birth_longitude: Optional[float] = None,
    person1_use_true_solar_time: bool = False,
    person2_use_true_solar_time: bool = False,
) -> str:
    """
    双人配合度分析工具

    分析两人命理的相互关系和配合程度，提供多维度的配合度评估：
    - 总体配合度评分（0-100分）
    - 五行配合度（两人五行的互补性和协调性）
    - 十神关系分析（两人十神配置的相互影响）
    - 格局协同分析（两人命局格局的配合程度）
    - 关系特化分析（针对特定关系类型的专门分析）

    Args:
        person1_name: 第一人姓名
        person1_birth_year: 第一人出生年份（公历）
        person1_birth_month: 第一人出生月份，1-12
        person1_birth_day: 第一人出生日期，1-31
        person1_birth_hour: 第一人出生时辰，0-23
        person2_name: 第二人姓名
        person2_birth_year: 第二人出生年份（公历）
        person2_birth_month: 第二人出生月份，1-12
        person2_birth_day: 第二人出生日期，1-31
        person2_birth_hour: 第二人出生时辰，0-23
        person1_gender: 第一人性别，默认为"未知"
        person1_birth_place: 第一人出生地，默认为"未提供"
        person2_gender: 第二人性别，默认为"未知"
        person2_birth_place: 第二人出生地，默认为"未提供"
        person1_birth_minute: 第一人出生分钟，默认0
        person2_birth_minute: 第二人出生分钟，默认0
        person1_birth_timezone: 第一人出生时区（可选）
        person2_birth_timezone: 第二人出生时区（可选）
        person1_birth_longitude: 第一人出生地经度（可选）
        person2_birth_longitude: 第二人出生地经度（可选）
        person1_use_true_solar_time: 第一人是否启用真太阳时修正
        person2_use_true_solar_time: 第二人是否启用真太阳时修正
        relationship_type: 关系类型，可选值：
            - "marriage": 婚姻关系
            - "friendship": 友谊关系
            - "business": 商业合作
            - "family": 家庭关系
            - "general": 一般关系（默认）

    Returns:
        JSON格式的字符串，包含详细的配合度分析结果
    """
    # 创建PersonInfo对象
    person1 = create_person_info(
        person1_birth_year,
        person1_birth_month,
        person1_birth_day,
        person1_birth_hour,
        person1_name,
        person1_gender,
        person1_birth_place,
        birth_minute=person1_birth_minute,
        birth_timezone=person1_birth_timezone,
        birth_longitude=person1_birth_longitude,
        use_true_solar_time=person1_use_true_solar_time,
    )

    person2 = create_person_info(
        person2_birth_year,
        person2_birth_month,
        person2_birth_day,
        person2_birth_hour,
        person2_name,
        person2_gender,
        person2_birth_place,
        birth_minute=person2_birth_minute,
        birth_timezone=person2_birth_timezone,
        birth_longitude=person2_birth_longitude,
        use_true_solar_time=person2_use_true_solar_time,
    )

    data = calculate_compatibility_analysis(person1, person2, relationship_type)
    return _render_tool_response(data, tool_name="two_person_compatibility")


@app.tool
def timing_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    analysis_age: Optional[int] = None,
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    时运分析工具 - 分析大运、流年、流月对命局的影响，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        name: 姓名（可选）
        gender: 性别（可选）
        birth_place: 出生地（可选）
        analysis_year: 分析年份（可选，默认当前年份）
        analysis_month: 分析月份（可选，默认当前月份）
        analysis_day: 分析日期（可选，默认 1）
        analysis_hour: 分析时（可选，默认 0）
        analysis_minute: 分析分（可选，默认 0）
        analysis_age: 分析年龄（可选，用于大运分析）
        birth_minute: 出生分钟，默认0
        birth_timezone: 出生时区（可选）
        birth_longitude: 出生地经度（可选）
        selected_sections: 仅导出指定 section（可选）
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        格式化的时运分析结果
    """

    # 创建PersonInfo对象
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    # 计算时运分析
    result = calculate_comprehensive_timing(
        person,
        analysis_year,
        analysis_month,
        analysis_age,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "时运分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="timing_analysis",
    )


@app.tool
def dayun_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    gender: str,
    analysis_age: int,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    大运分析工具 - 专门分析指定年龄的大运情况，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        gender: 性别（男/女）
        analysis_age: 分析年龄
        name: 姓名（可选）
        birth_place: 出生地（可选）
        birth_minute: 出生分钟，默认0
        birth_timezone: 出生时区（可选）
        birth_longitude: 出生地经度（可选）
        selected_sections: 仅导出指定 section（可选）
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        格式化的大运分析结果
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_dayun_analysis(
        person,
        analysis_age,
        selected_sections=selected_sections,
    )

    if "error" in result and result.get("analysis_type") is None:
        # Only treat as error response if it's not a partial error inside the result
        return _render_tool_error(result, "大运分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="dayun_analysis",
    )


@app.tool
def liunian_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    target_year: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    流年分析工具 - 专门分析指定年份的流年影响，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        target_year: 目标分析年份
        name: 姓名（可选）
        gender: 性别（可选）
        birth_place: 出生地（可选）
        birth_minute: 出生分钟，默认0
        birth_timezone: 出生时区（可选）
        birth_longitude: 出生地经度（可选）
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        格式化的流年分析结果
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_liunian_analysis(
        person,
        target_year,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "流年分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="liunian_analysis",
    )


@app.tool
def liuyue_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    流月分析工具 - 专门分析指定日期所在节令月的影响，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        name: 姓名（可选）
        gender: 性别（可选）
        birth_place: 出生地（可选）
        analysis_year: 分析年份（可选）
        analysis_month: 分析月份（可选）
        analysis_day: 分析日期（可选）
        analysis_hour: 分析时刻（小时，可选）
        analysis_minute: 分析时刻（分钟，可选）
        birth_minute: 出生分钟，默认0
        birth_timezone: 出生时区（可选）
        birth_longitude: 出生地经度（可选）
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        格式化的流月专项分析结果
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_liuyue_analysis(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "流月分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="liuyue_analysis",
    )


def _run_astro_chart_tool(
    chart_variant: str,
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
    **payload: Any,
) -> str:
    result = calculate_core_chart_analysis(chart_variant=chart_variant, **payload)
    if "error" in result:
        return _render_tool_error(result, f"{chart_variant} 星盘", compact=compact)
    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name=chart_variant if chart_variant in {"chart", "chart13", "germany"} else {
            "hellen_chart": "astro_hellen_chart",
            "guolao_chart": "astro_guolao_chart",
            "india_chart": "astro_india_chart",
        }.get(chart_variant, "astro_chart"),
    )


@app.tool
def astro_chart13(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    13宫扩展盘工具 - 生成 13 扇区覆盖层

    未显式传入时沿用 FateBridge 对 chart13 的默认离线语义；显式传入 `hsys` /
    `zodiacal` 时，会走核心星盘家族统一的离线覆盖逻辑。
    """
    return _run_astro_chart_tool(
        "chart13",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        hsys=hsys,
        zodiacal=zodiacal,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def astro_hellen_chart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    希腊星盘工具 - 生成 whole-sign + sect + fortune lot 输出

    未显式传入时沿用 FateBridge 对 hellen_chart 的默认离线语义；显式传入 `hsys` /
    `zodiacal` 时，会走核心星盘家族统一的离线覆盖逻辑。
    """
    return _run_astro_chart_tool(
        "hellen_chart",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        hsys=hsys,
        zodiacal=zodiacal,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def astro_guolao_chart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    果老/七政四余风格星盘工具 - 生成二十八宿辅助输出

    未显式传入时沿用 FateBridge 对 guolao_chart 的默认离线语义；显式传入 `hsys` /
    `zodiacal` 时，会走核心星盘家族统一的离线覆盖逻辑。
    """
    return _run_astro_chart_tool(
        "guolao_chart",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        hsys=hsys,
        zodiacal=zodiacal,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def astro_india_chart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    印度盘工具 - 生成 sidereal + nakshatra 输出

    未显式传入时沿用 FateBridge 对 india_chart 的默认离线语义；显式传入 `hsys` /
    `zodiacal` 时，会走核心星盘家族统一的离线覆盖逻辑。
    """
    return _run_astro_chart_tool(
        "india_chart",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        hsys=hsys,
        zodiacal=zodiacal,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def astro_germany_chart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    量化盘/中点盘工具 - 输出传统七曜中点与相位

    `hsys` / `zodiacal` 会先作用于其底层基准 chart，再派生出中点层，保持核心盘
    与 germany 中点盘的离线覆盖语义一致。
    """
    result = calculate_germany_chart_analysis(
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        hsys=hsys,
        zodiacal=zodiacal,
    )
    if "error" in result:
        return _render_tool_error(result, "germany 中点盘", compact=compact)
    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="germany",
    )


@app.tool
def export_registry(
    technique: Optional[str] = None,
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    AI 导出协议注册表工具 - 返回 FateBridge 的导出设置目录。
    """
    return _run_registry_tool(
        "export_registry",
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        technique=technique,
    )


@app.tool
def export_parse(
    technique: str,
    content: str,
    *,
    selected_sections: Optional[list[str]] = None,
    planet_info: Optional[dict] = None,
    astro_meaning: Optional[dict] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    AI 导出正文解析工具 - 将快照文本拆分为可筛选的结构化分段。
    """
    return _run_registry_tool(
        "export_parse",
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        technique=technique,
        content=content,
        selected_sections=selected_sections,
        planet_info=planet_info,
        astro_meaning=astro_meaning,
    )


@app.tool
def knowledge_registry(
    domain: Optional[str] = None,
    *,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    悬浮知识目录工具 - 列出 astrology / 六壬 / 奇门的本地知识分类，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    return _run_registry_tool(
        "knowledge_registry",
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        domain=domain,
        selected_sections=selected_sections,
    )


@app.tool
def knowledge_read(
    domain: str,
    category: str,
    key: Optional[str] = None,
    *,
    selected_sections: Optional[list[str]] = None,
    aspect_degree: Optional[int] = None,
    object_a: Optional[str] = None,
    object_b: Optional[str] = None,
    jiang_name: Optional[str] = None,
    tian_branch: Optional[str] = None,
    di_branch: Optional[str] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    悬浮知识读取工具 - 按 domain/category/key 读取单条本地知识，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    return _run_registry_tool(
        "knowledge_read",
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        domain=domain,
        category=category,
        key=key,
        selected_sections=selected_sections,
        aspect_degree=aspect_degree,
        object_a=object_a,
        object_b=object_b,
        jiang_name=jiang_name,
        tian_branch=tian_branch,
        di_branch=di_branch,
    )


@app.tool
def jieqi_year(
    year: int,
    zone: Optional[str] = "Asia/Shanghai",
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    *,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    jieqis: Optional[list[str]] = None,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    全年节气盘辅助工具 - 输出全年 24 节气节点，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_jieqi_year(
        year=year,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        jieqis=jieqis,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "全年节气盘", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="western_timing_analysis",
    )


@app.tool
def nongli_time(
    date: str,
    time: str,
    zone: Optional[str] = "Asia/Shanghai",
    lon: Optional[str] = None,
    *,
    lat: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    gender: Optional[bool] = None,
    after23_new_day: bool = False,
    time_alg: int = 0,
    ad: int = 1,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    农历换算辅助工具 - 输出农历日期、节气与四柱上下文，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_nongli_time(
        date=date,
        time=time,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        gender=gender,
        after23_new_day=after23_new_day,
        time_alg=time_alg,
        ad=ad,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "农历换算", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="nongli_time",
    )


@app.tool
def gua_meiyi(
    name: list[str],
    *,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    梅易卦义辅助工具 - 批量返回偏梅花易数语境的卦义摘要，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_gua_meiyi(name=name, selected_sections=selected_sections)

    if "error" in result:
        return _render_tool_error(result, "梅易卦义", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="gua_meiyi",
    )


@app.tool
def gua_lookup(
    query: str,
    lookup_mode: str = "auto",
    *,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    卦义检索工具 - 查询六十四卦或八卦的离线义理说明，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export

    Args:
        query: 卦名或二进制卦码。六十四卦可用 6 位码如 111111，八卦可用 3 位码如 111
        lookup_mode: 查询模式，可选 auto、hexagram、trigram

    Returns:
        格式化的卦义检索结果
    """
    result = calculate_gua_lookup(
        query=query,
        lookup_mode=lookup_mode,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "卦义检索", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="gua_lookup",
    )


@app.tool
def meihua_analysis(
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    question: Optional[str] = None,
    *,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    梅花时卦分析工具 - 根据指定时刻起本卦、变卦、互卦、综卦与体用关系

    Args:
        analysis_year: 起卦年份
        analysis_month: 起卦月份 (1-12)
        analysis_day: 起卦日期 (1-31)
        analysis_hour: 起卦时辰 (0-23)
        question: 占问主题（可选）
        analysis_minute: 起卦分钟，默认0
        analysis_timezone: 起卦时区（可选）

    Returns:
        格式化的梅花时卦分析结果
    """
    result = calculate_meihua_analysis(
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        question=question,
    )

    if "error" in result:
        return _render_tool_error(result, "梅花时卦分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def tongshefa(
    taiyin: Optional[str] = "巽",
    taiyang: Optional[str] = "坤",
    shaoyang: Optional[str] = "震",
    shaoyin: Optional[str] = "震",
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    统摄法工具 - 本地生成左右本卦、潜藏与亲和关系
    """
    result = calculate_tongshefa_analysis(
        taiyin=taiyin,
        taiyang=taiyang,
        shaoyang=shaoyang,
        shaoyin=shaoyin,
    )

    if "error" in result:
        return _render_tool_error(result, "统摄法分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def sixyao(
    date: str,
    time: str,
    zone: Optional[str] = "+08:00",
    lat: Optional[str] = "31n13",
    lon: Optional[str] = "121e28",
    question: Optional[str] = None,
    gua_code: Optional[str] = None,
    changed_code: Optional[str] = None,
    *,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    lines: Optional[list] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    六爻 / 易卦工具 - 本地生成本卦、之卦、爻变与卦辞摘要
    """
    result = calculate_sixyao_analysis(
        date=date,
        time=time,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        question=question,
        gua_code=gua_code,
        changed_code=changed_code,
        lines=lines,
    )

    if "error" in result:
        return _render_tool_error(result, "六爻分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def suzhan(
    date: str,
    time: str,
    zone: Optional[str] = "+08:00",
    lat: Optional[str] = "31n13",
    lon: Optional[str] = "121e28",
    *,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    szchart: int = 0,
    szshape: int = 0,
    house_start_mode: int = 1,
    doubing_su28: bool = True,
    hsys: int = 8,
    zodiacal: int = 0,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    宿占 / 宿盘工具 - 本地生成二十八宿与宫位分布
    """
    result = calculate_suzhan_analysis(
        date=date,
        time=time,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        szchart=szchart,
        szshape=szshape,
        house_start_mode=house_start_mode,
        doubing_su28=doubing_su28,
        hsys=hsys,
        zodiacal=zodiacal,
    )

    if "error" in result:
        return _render_tool_error(result, "宿占分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def otherbu(
    date: str,
    time: str,
    zone: Optional[str] = "+08:00",
    lat: Optional[str] = "31n13",
    lon: Optional[str] = "121e28",
    question: Optional[str] = None,
    *,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    tradition: bool = False,
    sign: Optional[str] = "Aries",
    house: int = 0,
    planet: Optional[str] = "Sun",
    hsys: int = 8,
    zodiacal: int = 0,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    西洋游戏 / 占星骰子工具 - 本地生成骰面与对应解释
    """
    result = calculate_otherbu_analysis(
        date=date,
        time=time,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        tradition=tradition,
        sign=sign,
        house=house,
        planet=planet,
        hsys=hsys,
        zodiacal=zodiacal,
        question=question,
    )

    if "error" in result:
        return _render_tool_error(result, "占星骰子分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def sanshiunited(
    date: str,
    time: str,
    zone: Optional[str] = "+08:00",
    lat: Optional[str] = "31n13",
    lon: Optional[str] = "121e28",
    *,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    qimen_options: Optional[dict] = None,
    taiyi_options: Optional[dict] = None,
    selected_sections: Optional[list[str]] = None,
    liureng_yue: Optional[str] = None,
    liureng_is_diurnal: Optional[bool] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    三式合一工具 - 本地聚合奇门、太乙与六壬摘要，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export
    """
    result = calculate_sanshiunited_analysis(
        date=date,
        time=time,
        zone=zone,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        qimen_options=qimen_options,
        taiyi_options=taiyi_options,
        selected_sections=selected_sections,
        liureng_yue=liureng_yue,
        liureng_is_diurnal=liureng_is_diurnal,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "三式合一分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def ziwei_birth(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    紫微斗数命盘工具

    根据出生信息生成离线紫微斗数命盘，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_ziwei_birth_service(
        person,
        selected_sections=selected_sections,
    )
    if "error" in result:
        return _render_tool_error(result, "紫微斗数命盘", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def ziwei_rules(
    year_stem: Optional[str] = None,
    *,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    紫微规则库工具

    查询 FateBridge 内置的紫微宫位、命身宫与四化规则，可按天干过滤，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_ziwei_rules_service(
        year_stem=year_stem,
        selected_sections=selected_sections,
    )
    if "error" in result:
        return _render_tool_error(result, "紫微规则库", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def liureng_gods(
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    gender: Optional[str] = "未知",
    *,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    大六壬起课工具

    根据指定时刻生成月将、四课、三传、贵人盘序与概览，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_liureng_gods_service(
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        analysis_longitude=analysis_longitude,
        gender=gender or "未知",
        selected_sections=selected_sections,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "大六壬起课", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def liureng_runyear(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    gender: Optional[str] = "未知",
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    大六壬行年工具

    在起课结果上叠加行年干支与年龄信息，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_liureng_runyear_service(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        analysis_longitude=analysis_longitude,
        selected_sections=selected_sections,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "大六壬行年", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def qimen(
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    *,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    qimen_options: Optional[dict] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    奇门遁甲工具

    生成离线奇门盘，支持本地 layout/palaceShift 变体，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_qimen_analysis_service(
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        analysis_longitude=analysis_longitude,
        qimen_options=qimen_options,
        selected_sections=selected_sections,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "奇门遁甲", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def taiyi(
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    gender: Optional[str] = "未知",
    *,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    太乙神数工具

    生成离线太乙盘，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_taiyi_analysis_service(
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        analysis_longitude=analysis_longitude,
        gender=gender or "未知",
        selected_sections=selected_sections,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "太乙神数", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def jinkou(
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    gender: Optional[str] = "未知",
    di_fen: Optional[str] = None,
    *,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    金口诀工具

    在六壬语境上生成金口诀四位、用爻、四大空亡与四位神煞，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export。
    """
    result = calculate_jinkou_analysis_service(
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        analysis_timezone=analysis_timezone,
        analysis_longitude=analysis_longitude,
        gender=gender or "未知",
        di_fen=di_fen,
        selected_sections=selected_sections,
        use_true_solar_time=use_true_solar_time,
    )

    if "error" in result:
        return _render_tool_error(result, "金口诀", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def liuri_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    流日分析工具 - 专门分析指定日期的流日影响，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_liuri_analysis(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "流日分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def liushi_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    流时分析工具 - 专门分析指定时刻的流时影响，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_liushi_analysis(
        person,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        analysis_hour=analysis_hour,
        analysis_minute=analysis_minute,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "流时分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name="liushi_analysis",
    )


@app.tool
def jieqi_timeline_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    target_year: Optional[int] = None,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    selected_sections: Optional[list[str]] = None,
    use_true_solar_time: bool = False,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    节气节点时间轴分析工具 - 输出全年 24 节气节点的流月/流日切换信息，并返回完整 snapshot_text 与可按 selected_sections 过滤的 snapshot_export
    """
    person = create_person_info(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        name,
        gender,
        birth_place,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )

    result = calculate_jieqi_timeline_analysis(
        person,
        target_year=target_year,
        selected_sections=selected_sections,
    )

    if "error" in result:
        return _render_tool_error(result, "节气时间轴分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def astro_chart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    chart_variant: str = "chart",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = "UTC",
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    离线星盘工具

    支持核心盘、13 宫扩展盘、希腊式整宫盘、果老/宿度盘、印度式恒星黄道盘，以及中点量化盘。
    计算优先走本地 Swiss Ephemeris runtime；缺失时回退 FateBridge 近似模型。
    未显式传入时，会沿用各盘型原本的默认宫制与黄道类型；显式传入 `hsys` /
    `zodiacal` 时，会走 FateBridge 离线宫制与黄道覆盖逻辑。
    """
    payload: Dict[str, Any] = {
        "birth_year": birth_year,
        "birth_month": birth_month,
        "birth_day": birth_day,
        "birth_hour": birth_hour,
        "birth_minute": birth_minute,
        "birth_timezone": birth_timezone,
        "birth_longitude": birth_longitude,
        "birth_latitude": birth_latitude,
        "name": name,
        "birth_place": birth_place,
        "hsys": hsys,
        "zodiacal": zodiacal,
    }

    if chart_variant == "germany":
        result = calculate_germany_chart_analysis(**payload)
    else:
        result = calculate_core_chart_analysis(
            chart_variant=chart_variant,
            **payload,
        )

    if "error" in result:
        return _render_tool_error(result, "星盘分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        tool_name=chart_variant if chart_variant in {"chart", "chart13"} else {
            "germany": "germany",
            "hellen_chart": "astro_hellen_chart",
            "guolao_chart": "astro_guolao_chart",
            "india_chart": "astro_india_chart",
        }.get(chart_variant, "astro_chart"),
    )


@app.tool
def astro_relative_chart(
    inner_birth_year: int,
    inner_birth_month: int,
    inner_birth_day: int,
    inner_birth_hour: int,
    inner_birth_longitude: float,
    inner_birth_latitude: float,
    outer_birth_year: int,
    outer_birth_month: int,
    outer_birth_day: int,
    outer_birth_hour: int,
    outer_birth_longitude: float,
    outer_birth_latitude: float,
    inner_name: Optional[str] = "内盘",
    outer_name: Optional[str] = "外盘",
    inner_birth_place: Optional[str] = "未提供",
    outer_birth_place: Optional[str] = "未提供",
    relationship_mode: Optional[str | int] = None,
    relative_mode: Optional[str | int] = None,
    *,
    inner_birth_minute: int = 0,
    outer_birth_minute: int = 0,
    inner_birth_timezone: Optional[str] = "UTC",
    outer_birth_timezone: Optional[str] = "UTC",
    hsys: int = 0,
    zodiacal: int = 0,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    离线关系盘工具

    返回双人本命盘、方向相位层、合成盘与基础兼容度评分。
    关系盘底层本命盘优先走本地 Swiss Ephemeris runtime；缺失时回退近似模型。
    `relative_mode` 走现代 Horosa 风格语义；旧 `relationship_mode='synastry'`
    仍保留为 FateBridge 比较盘兼容路径。
    """
    result = calculate_relative_chart_analysis(
        inner_payload={
            "name": inner_name,
            "birth_year": inner_birth_year,
            "birth_month": inner_birth_month,
            "birth_day": inner_birth_day,
            "birth_hour": inner_birth_hour,
            "birth_minute": inner_birth_minute,
            "birth_timezone": inner_birth_timezone,
            "birth_longitude": inner_birth_longitude,
            "birth_latitude": inner_birth_latitude,
            "birth_place": inner_birth_place,
        },
        outer_payload={
            "name": outer_name,
            "birth_year": outer_birth_year,
            "birth_month": outer_birth_month,
            "birth_day": outer_birth_day,
            "birth_hour": outer_birth_hour,
            "birth_minute": outer_birth_minute,
            "birth_timezone": outer_birth_timezone,
            "birth_longitude": outer_birth_longitude,
            "birth_latitude": outer_birth_latitude,
            "birth_place": outer_birth_place,
        },
        relative_mode=relative_mode,
        relationship_mode=relationship_mode,
        hsys=hsys,
        zodiacal=zodiacal,
    )

    if "error" in result:
        return _render_tool_error(result, "关系星盘分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def western_timing_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """
    西占时运分析工具

    输出太阳返照、月返、指定年盘、次限推运、太阳弧、主限、小限、法达与十年星限结构。
    主限支持 Arc / 赤经 / FateBridge 离线 SemiArc 坐标近似。
    """
    result = calculate_western_timing_analysis(
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
    )

    if "error" in result:
        return _render_tool_error(result, "西占时运分析", compact=compact)

    return _render_tool_response(
        result,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


def _run_western_timing_module_tool(
    tool_key: str,
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    return _run_registry_tool(
        tool_key,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
    )


@app.tool
def solarreturn(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占太阳返照独立工具。"""
    return _run_western_timing_module_tool(
        "solarreturn",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def lunarreturn(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占月亮返照独立工具。"""
    return _run_western_timing_module_tool(
        "lunarreturn",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def transit(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占行运盘独立工具。"""
    return _run_western_timing_module_tool(
        "transit",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def solararc(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占太阳弧独立工具。"""
    return _run_western_timing_module_tool(
        "solararc",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def givenyear(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占指定年盘独立工具。"""
    return _run_western_timing_module_tool(
        "givenyear",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def profection(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占年小限独立工具。"""
    return _run_western_timing_module_tool(
        "profection",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def pd(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占主限独立工具。"""
    return _run_western_timing_module_tool(
        "pd",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def pdchart(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占主限法盘独立工具。"""
    return _run_western_timing_module_tool(
        "pdchart",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def zr(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占黄道释放独立工具。"""
    return _run_western_timing_module_tool(
        "zr",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def firdaria(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占法达星限独立工具。"""
    return _run_western_timing_module_tool(
        "firdaria",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


@app.tool
def decennials(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_timezone: str,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    *,
    birth_minute: int = 0,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[list[int]] = None,
    show_pd_bounds: bool = True,
    selected_sections: Optional[list[str]] = None,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """西占十年星限独立工具。"""
    return _run_western_timing_module_tool(
        "decennials",
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        birth_timezone=birth_timezone,
        name=name,
        birth_place=birth_place,
        analysis_year=analysis_year,
        analysis_month=analysis_month,
        analysis_day=analysis_day,
        birth_minute=birth_minute,
        return_longitude=return_longitude,
        return_latitude=return_latitude,
        return_timezone=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
        show_pd_bounds=show_pd_bounds,
        selected_sections=selected_sections,
        compact=compact,
        include_snapshot_text=include_snapshot_text,
    )


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
