"""
Central FateBridge tool catalog.

Every tool is declared exactly once here as a ``ToolSpec``. The REST app, the
FastMCP server, and the CLI all build their surfaces by iterating this list, so
adding a tool (or a whole new analysis dimension) means appending one entry —
no transport file needs editing.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fatebridge.core.request_models import (
    AstroChartPolyRequest,
    AstroChartRequest,
    AstroRelativeFlatRequest,
    AstroRelativeRequest,
    BaziBirthRequest,
    BaziCareerRequest,
    BaziChildrenRequest,
    BaziDirectRequest,
    BaziEducationRequest,
    BaziHealthRequest,
    BaziMarriageRequest,
    BaziPersonalityRequest,
    BaziRelativesRequest,
    BaziRomanceRequest,
    BaziWealthRequest,
    DayunAnalysisRequest,
    ExportParseRequest,
    ExportRegistryRequest,
    FateBridgeRequest,
    GuaLookupRequest,
    GuaMeiyiRequest,
    JieqiTimelineRequest,
    JieqiYearRequest,
    JinkouAnalysisRequest,
    KnowledgeReadRequest,
    KnowledgeRegistryRequest,
    LiunianAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    LiuriAnalysisRequest,
    LiushiAnalysisRequest,
    LiuyueAnalysisRequest,
    MeihuaAnalysisRequest,
    NongliTimeRequest,
    OtherBuRequest,
    QimenAnalysisRequest,
    SanShiUnitedRequest,
    SixYaoRequest,
    SukuyoCompatibilityRequest,
    SuZhanRequest,
    TaiyiAnalysisRequest,
    TimingAnalysisRequest,
    TongSheFaRequest,
    TwoPersonCompatibilityRequest,
    WesternTimingModuleRequest,
    WesternTimingRequest,
    ZiweiBirthRequest,
    ZiweiRulesRequest,
)
from fatebridge.core.tool_spec import (
    ToolSpec,
    pair_invoke,
    person_invoke,
    raw_invoke,
)
from fatebridge.services.astrology import (
    calculate_core_chart_analysis,
    calculate_germany_chart_analysis,
    calculate_relative_chart_analysis,
)
from fatebridge.services.bazi import (
    calculate_bazi_birth,
    calculate_bazi_career,
    calculate_bazi_children,
    calculate_bazi_direct,
    calculate_bazi_education,
    calculate_bazi_health,
    calculate_bazi_marriage,
    calculate_bazi_personality,
    calculate_bazi_relatives,
    calculate_bazi_romance,
    calculate_bazi_wealth,
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
    calculate_sukuyo_compatibility,
    calculate_suzhan_analysis,
    calculate_tongshefa_analysis,
)
from fatebridge.services.export_tools import (
    calculate_export_parse,
    calculate_export_registry,
)
from fatebridge.services.knowledge import (
    calculate_knowledge_read,
    calculate_knowledge_registry,
)
from fatebridge.services.metaphysics import (
    calculate_jinkou_analysis,
    calculate_liureng_gods,
    calculate_liureng_runyear,
    calculate_qimen_analysis,
    calculate_taiyi_analysis,
    calculate_ziwei_birth,
    calculate_ziwei_rules,
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
from fatebridge.services.western_timing import calculate_western_timing_analysis
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

# ---------------------------------------------------------------------------
# Custom invokes for the few tools whose glue does not fit a standard binder.
# ---------------------------------------------------------------------------


def _flatten_legacy_destiny(result: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy /api/calculate flattens the bazi_birth payload to the top level."""
    bazi_birth = result.get("bazi_birth")
    if not isinstance(bazi_birth, dict):
        return result
    payload = {
        key: bazi_birth[key]
        for key in (
            "person_info",
            "four_pillars",
            "day_master",
            "element_distribution",
            "favorable_elements",
            "ten_gods",
            "structure_profile",
            "patterns",
            "calendar_context",
        )
        if key in bazi_birth
    }
    for passthrough in ("snapshot_text", "snapshot_export", "run_metadata"):
        if passthrough in result:
            payload[passthrough] = result[passthrough]
    return payload


def _astro_chart_bind(req: Any):
    data = req.model_dump()
    variant = data.pop("chart_variant", "chart")
    if variant == "germany":
        return calculate_germany_chart_analysis, (), data
    return calculate_core_chart_analysis, (), {**data, "chart_variant": variant}


def _astro_relative_rest_bind(req: Any):
    return (
        calculate_relative_chart_analysis,
        (),
        {
            "inner_payload": req.inner.model_dump(),
            "outer_payload": req.outer.model_dump(),
            "relative_mode": req.relative_mode,
            "relationship_mode": req.relationship_mode,
            "relative_mode_source": req.mode_input_source,
            "hsys": req.hsys,
            "zodiacal": req.zodiacal,
            "relationship_focus": req.relationship_focus,
        },
    )


def _astro_relative_flat_bind(req: Any):
    d = req.model_dump()

    def party(prefix: str) -> Dict[str, Any]:
        return {
            "name": d[f"{prefix}_name"],
            "birth_year": d[f"{prefix}_birth_year"],
            "birth_month": d[f"{prefix}_birth_month"],
            "birth_day": d[f"{prefix}_birth_day"],
            "birth_hour": d[f"{prefix}_birth_hour"],
            "birth_minute": d[f"{prefix}_birth_minute"],
            "birth_timezone": d[f"{prefix}_birth_timezone"],
            "birth_longitude": d[f"{prefix}_birth_longitude"],
            "birth_latitude": d[f"{prefix}_birth_latitude"],
            "birth_place": d[f"{prefix}_birth_place"],
        }

    return (
        calculate_relative_chart_analysis,
        (),
        {
            "inner_payload": party("inner"),
            "outer_payload": party("outer"),
            "relative_mode": d["relative_mode"],
            "relationship_mode": d["relationship_mode"],
            "hsys": d["hsys"],
            "zodiacal": d["zodiacal"],
            "relationship_focus": d.get("relationship_focus"),
        },
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


def _western_module_spec(name: str, service: Any, label: str) -> ToolSpec:
    return ToolSpec(
        key=name,
        bind=raw_invoke(service),
        request_model=WesternTimingModuleRequest,
        summary=f"生成独立{label}结果。",
        operation_label_zh=label,
        family="western_timing_tool",
        rest_path=f"/api/astro/timing/{name}",
        mcp_name=name,
    )


def _bazi_dimension_spec(name: str, service: Any, model: Any, label: str) -> ToolSpec:
    return ToolSpec(
        key=f"bazi_{name}",
        bind=person_invoke(service),
        request_model=model,
        summary=f"{label}（可传 dayun_pillar / liunian_pillar 输出时机信号）。",
        operation_label_zh=label,
        family="bazi",
        rest_path=f"/api/cn/bazi/{name}",
        mcp_name=f"bazi_{name}",
        cpu_bound=True,
        include_snapshot_text=False,
    )


# ---------------------------------------------------------------------------
# The catalog.
# ---------------------------------------------------------------------------

CATALOG: List[ToolSpec] = [
    # --- BaZi core ---------------------------------------------------------
    ToolSpec(
        key="calculate_legacy",
        bind=person_invoke(calculate_bazi_birth),
        request_model=FateBridgeRequest,
        summary="八字命盘（兼容旧版 /api/calculate 扁平结构）。",
        operation_label_zh="八字命盘",
        family="bazi",
        rest_path="/api/calculate",
        mcp_name=None,
        cpu_bound=True,
        metadata_name="analyze_destiny",
        result_transform=_flatten_legacy_destiny,
    ),
    ToolSpec(
        key="analyze_destiny",
        bind=person_invoke(calculate_destiny_analysis),
        request_model=FateBridgeRequest,
        summary="综合命理分析（八字 + 喜用 + 格局）。",
        operation_label_zh="命理分析",
        family="bazi",
        rest_path=None,
        mcp_name="analyze_destiny",
        cpu_bound=True,
    ),
    ToolSpec(
        key="bazi_birth",
        bind=person_invoke(calculate_bazi_birth),
        request_model=BaziBirthRequest,
        summary="离线八字命盘，返回完整 snapshot_text 与可筛选 snapshot_export。",
        operation_label_zh="八字命盘",
        family="bazi",
        rest_path="/api/cn/bazi/birth",
        mcp_name="bazi_birth",
        cpu_bound=True,
    ),
    ToolSpec(
        key="bazi_direct",
        bind=person_invoke(calculate_bazi_direct),
        request_model=BaziDirectRequest,
        summary="离线八字直断，返回完整 snapshot_text 与可筛选 snapshot_export。",
        operation_label_zh="八字直断",
        family="bazi",
        rest_path="/api/cn/bazi/direct",
        mcp_name="bazi_direct",
        cpu_bound=True,
    ),
    _bazi_dimension_spec(
        "marriage", calculate_bazi_marriage, BaziMarriageRequest, "八字婚姻分析"
    ),
    _bazi_dimension_spec(
        "career", calculate_bazi_career, BaziCareerRequest, "八字事业分析"
    ),
    _bazi_dimension_spec(
        "wealth", calculate_bazi_wealth, BaziWealthRequest, "八字财运分析"
    ),
    _bazi_dimension_spec(
        "health", calculate_bazi_health, BaziHealthRequest, "八字健康分析"
    ),
    _bazi_dimension_spec(
        "children", calculate_bazi_children, BaziChildrenRequest, "八字子女分析"
    ),
    _bazi_dimension_spec(
        "education", calculate_bazi_education, BaziEducationRequest, "八字学业分析"
    ),
    _bazi_dimension_spec(
        "personality",
        calculate_bazi_personality,
        BaziPersonalityRequest,
        "八字性格分析",
    ),
    _bazi_dimension_spec(
        "relatives", calculate_bazi_relatives, BaziRelativesRequest, "八字六亲分析"
    ),
    _bazi_dimension_spec(
        "romance", calculate_bazi_romance, BaziRomanceRequest, "八字正缘桃花分析"
    ),
    # --- Compatibility -----------------------------------------------------
    ToolSpec(
        key="two_person_compatibility",
        bind=pair_invoke(calculate_compatibility_analysis),
        request_model=TwoPersonCompatibilityRequest,
        summary="双人配合度分析（八字合婚 / 合作）。",
        operation_label_zh="配合度分析",
        family="compatibility",
        rest_path="/api/compatibility",
        mcp_name="two_person_compatibility",
        cpu_bound=True,
    ),
    # --- Timing ------------------------------------------------------------
    ToolSpec(
        key="timing_analysis",
        bind=person_invoke(calculate_comprehensive_timing),
        request_model=TimingAnalysisRequest,
        summary="时运综合分析（大运/流年/流月等综合影响）。",
        operation_label_zh="时运综合分析",
        family="timing",
        rest_path="/api/timing/comprehensive",
        mcp_name="timing_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="dayun_analysis",
        bind=person_invoke(calculate_dayun_analysis),
        request_model=DayunAnalysisRequest,
        summary="大运分析。",
        operation_label_zh="大运分析",
        family="timing",
        rest_path="/api/timing/dayun",
        mcp_name="dayun_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="liunian_analysis",
        bind=person_invoke(calculate_liunian_analysis),
        request_model=LiunianAnalysisRequest,
        summary="流年分析。",
        operation_label_zh="流年分析",
        family="timing",
        rest_path="/api/timing/liunian",
        mcp_name="liunian_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="liuyue_analysis",
        bind=person_invoke(calculate_liuyue_analysis),
        request_model=LiuyueAnalysisRequest,
        summary="流月分析。",
        operation_label_zh="流月分析",
        family="timing",
        rest_path="/api/timing/liuyue",
        mcp_name="liuyue_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="liuri_analysis",
        bind=person_invoke(calculate_liuri_analysis),
        request_model=LiuriAnalysisRequest,
        summary="流日分析。",
        operation_label_zh="流日分析",
        family="timing",
        rest_path="/api/timing/liuri",
        mcp_name="liuri_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="liushi_analysis",
        bind=person_invoke(calculate_liushi_analysis),
        request_model=LiushiAnalysisRequest,
        summary="流时分析。",
        operation_label_zh="流时分析",
        family="timing",
        rest_path="/api/timing/liushi",
        mcp_name="liushi_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="jieqi_timeline_analysis",
        bind=person_invoke(calculate_jieqi_timeline_analysis),
        request_model=JieqiTimelineRequest,
        summary="节气时间轴分析。",
        operation_label_zh="节气时间轴分析",
        family="timing",
        rest_path="/api/timing/jieqi",
        mcp_name="jieqi_timeline_analysis",
        cpu_bound=True,
    ),
    ToolSpec(
        key="jieqi_year",
        bind=raw_invoke(calculate_jieqi_year),
        request_model=JieqiYearRequest,
        summary="指定年份节气时刻表。",
        operation_label_zh="节气年表",
        family="timing",
        rest_path="/api/cn/jieqi/year",
        mcp_name="jieqi_year",
    ),
    ToolSpec(
        key="nongli_time",
        bind=raw_invoke(calculate_nongli_time),
        request_model=NongliTimeRequest,
        summary="公历↔农历时间换算与干支。",
        operation_label_zh="农历时间",
        family="timing",
        rest_path="/api/cn/nongli/time",
        mcp_name="nongli_time",
    ),
    # --- Divination --------------------------------------------------------
    ToolSpec(
        key="gua_lookup",
        bind=raw_invoke(calculate_gua_lookup),
        request_model=GuaLookupRequest,
        summary="卦象查询（六十四卦义理）。",
        operation_label_zh="卦象查询",
        family="divination",
        rest_path="/api/divination/gua",
        mcp_name="gua_lookup",
    ),
    ToolSpec(
        key="gua_meiyi",
        bind=raw_invoke(calculate_gua_meiyi),
        request_model=GuaMeiyiRequest,
        summary="卦义 helper。",
        operation_label_zh="卦义",
        family="divination",
        rest_path="/api/cn/gua/meiyi",
        mcp_name="gua_meiyi",
    ),
    ToolSpec(
        key="meihua_analysis",
        bind=raw_invoke(calculate_meihua_analysis),
        request_model=MeihuaAnalysisRequest,
        summary="梅花易数时卦辅助。",
        operation_label_zh="梅花易数",
        family="divination",
        rest_path="/api/divination/meihua",
        mcp_name="meihua_analysis",
    ),
    ToolSpec(
        key="tongshefa",
        bind=raw_invoke(calculate_tongshefa_analysis),
        request_model=TongSheFaRequest,
        summary="通蓍法起卦。",
        operation_label_zh="通蓍法",
        family="divination",
        rest_path="/api/divination/tongshefa",
        mcp_name="tongshefa",
    ),
    ToolSpec(
        key="sixyao",
        bind=raw_invoke(calculate_sixyao_analysis),
        request_model=SixYaoRequest,
        summary="六爻纳甲分析。",
        operation_label_zh="六爻",
        family="divination",
        rest_path="/api/divination/sixyao",
        mcp_name="sixyao",
    ),
    ToolSpec(
        key="suzhan",
        bind=raw_invoke(calculate_suzhan_analysis),
        request_model=SuZhanRequest,
        summary="宿占分析。",
        operation_label_zh="宿占",
        family="divination",
        rest_path="/api/divination/suzhan",
        mcp_name="suzhan",
    ),
    ToolSpec(
        key="sukuyo_compatibility",
        bind=raw_invoke(calculate_sukuyo_compatibility),
        request_model=SukuyoCompatibilityRequest,
        summary="宿曜双人相性分析（三九の秘法，二十七宿）。",
        operation_label_zh="宿曜合盘",
        family="compatibility",
        rest_path="/api/compatibility/sukuyo",
        mcp_name="sukuyo_compatibility",
    ),
    ToolSpec(
        key="otherbu",
        bind=raw_invoke(calculate_otherbu_analysis),
        request_model=OtherBuRequest,
        summary="其他卜法分析。",
        operation_label_zh="其他卜法",
        family="divination",
        rest_path="/api/divination/otherbu",
        mcp_name="otherbu",
    ),
    ToolSpec(
        key="sanshiunited",
        bind=raw_invoke(calculate_sanshiunited_analysis),
        request_model=SanShiUnitedRequest,
        summary="三式合参分析。",
        operation_label_zh="三式合参",
        family="divination",
        rest_path="/api/divination/sanshiunited",
        mcp_name="sanshiunited",
    ),
    # --- Metaphysics -------------------------------------------------------
    ToolSpec(
        key="ziwei_birth",
        bind=person_invoke(calculate_ziwei_birth),
        request_model=ZiweiBirthRequest,
        summary="紫微斗数命盘。",
        operation_label_zh="紫微命盘",
        family="metaphysics",
        rest_path="/api/cn/ziwei/birth",
        mcp_name="ziwei_birth",
    ),
    ToolSpec(
        key="ziwei_rules",
        bind=raw_invoke(calculate_ziwei_rules),
        request_model=ZiweiRulesRequest,
        summary="紫微斗数规则 helper。",
        operation_label_zh="紫微规则",
        family="metaphysics",
        rest_path="/api/cn/ziwei/rules",
        mcp_name="ziwei_rules",
    ),
    ToolSpec(
        key="liureng_gods",
        bind=raw_invoke(calculate_liureng_gods),
        request_model=LiuRengGodsRequest,
        summary="六壬课体与天将。",
        operation_label_zh="六壬课",
        family="metaphysics",
        rest_path="/api/cn/liureng/gods",
        mcp_name="liureng_gods",
    ),
    ToolSpec(
        key="liureng_runyear",
        bind=person_invoke(
            calculate_liureng_runyear, also_pass=("use_true_solar_time",)
        ),
        request_model=LiuRengRunyearRequest,
        summary="六壬流年分析。",
        operation_label_zh="六壬流年",
        family="metaphysics",
        rest_path="/api/cn/liureng/runyear",
        mcp_name="liureng_runyear",
    ),
    ToolSpec(
        key="qimen",
        bind=raw_invoke(calculate_qimen_analysis),
        request_model=QimenAnalysisRequest,
        summary="奇门遁甲排盘分析。",
        operation_label_zh="奇门遁甲",
        family="metaphysics",
        rest_path="/api/cn/qimen",
        mcp_name="qimen",
    ),
    ToolSpec(
        key="taiyi",
        bind=raw_invoke(calculate_taiyi_analysis),
        request_model=TaiyiAnalysisRequest,
        summary="太乙神数分析。",
        operation_label_zh="太乙",
        family="metaphysics",
        rest_path="/api/cn/taiyi",
        mcp_name="taiyi",
    ),
    ToolSpec(
        key="jinkou",
        bind=raw_invoke(calculate_jinkou_analysis),
        request_model=JinkouAnalysisRequest,
        summary="金口诀分析。",
        operation_label_zh="金口诀",
        family="metaphysics",
        rest_path="/api/cn/jinkou",
        mcp_name="jinkou",
    ),
    # --- Export / Knowledge ------------------------------------------------
    ToolSpec(
        key="export_registry",
        bind=raw_invoke(calculate_export_registry),
        request_model=ExportRegistryRequest,
        summary="返回 FateBridge 导出协议注册表。",
        operation_label_zh="导出注册表",
        family="export",
        rest_path="/api/export/registry",
        mcp_name="export_registry",
    ),
    ToolSpec(
        key="export_parse",
        bind=raw_invoke(calculate_export_parse),
        request_model=ExportParseRequest,
        summary="将快照文本解析为可筛选的结构化 section。",
        operation_label_zh="导出解析",
        family="export",
        rest_path="/api/export/parse",
        mcp_name="export_parse",
    ),
    ToolSpec(
        key="knowledge_registry",
        bind=raw_invoke(calculate_knowledge_registry),
        request_model=KnowledgeRegistryRequest,
        summary="列出内置知识域与分类。",
        operation_label_zh="知识目录",
        family="knowledge",
        rest_path="/api/knowledge/registry",
        mcp_name="knowledge_registry",
    ),
    ToolSpec(
        key="knowledge_read",
        bind=raw_invoke(calculate_knowledge_read),
        request_model=KnowledgeReadRequest,
        summary="读取单条内置知识并支持导出裁剪。",
        operation_label_zh="知识读取",
        family="knowledge",
        rest_path="/api/knowledge/read",
        mcp_name="knowledge_read",
    ),
    # --- Astrology charts --------------------------------------------------
    ToolSpec(
        key="astro_chart",
        bind=_astro_chart_bind,
        request_model=AstroChartPolyRequest,
        summary="离线核心星盘（可选 chart_variant 切换盘式；germany 走德国盘引擎）。",
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
        summary="离线关系/合盘（嵌套 inner/outer 结构）。",
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
        summary="离线关系/合盘（扁平 inner_/outer_ 参数）。",
        operation_label_zh="关系星盘分析",
        family="astro",
        rest_path=None,
        mcp_name="astro_relative_chart",
    ),
    ToolSpec(
        key="western_timing_analysis",
        bind=raw_invoke(calculate_western_timing_analysis),
        request_model=WesternTimingRequest,
        summary="西占预测时运综合分析。",
        operation_label_zh="西占时运",
        family="western_timing",
        rest_path="/api/astro/timing",
        mcp_name="western_timing_analysis",
    ),
    # --- Western timing modules -------------------------------------------
    _western_module_spec("solarreturn", calculate_solarreturn, "西占太阳返照"),
    _western_module_spec("lunarreturn", calculate_lunarreturn, "西占月亮返照"),
    _western_module_spec("transit", calculate_transit, "西占行运盘"),
    _western_module_spec("solararc", calculate_solararc, "西占太阳弧"),
    _western_module_spec("givenyear", calculate_givenyear, "西占指定年盘"),
    _western_module_spec("profection", calculate_profection, "西占年小限"),
    _western_module_spec("pd", calculate_pd, "西占主限"),
    _western_module_spec("pdchart", calculate_pdchart, "西占主限法盘"),
    _western_module_spec("zr", calculate_zr, "西占黄道释放"),
    _western_module_spec("firdaria", calculate_firdaria, "西占法达星限"),
    _western_module_spec("decennials", calculate_decennials, "西占十年星限"),
]


def rest_specs() -> List[ToolSpec]:
    return [s for s in CATALOG if s.rest_path]


def mcp_specs() -> List[ToolSpec]:
    return [s for s in CATALOG if s.mcp_name]
