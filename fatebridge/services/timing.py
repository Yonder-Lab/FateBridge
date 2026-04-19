"""
FateBridge Timing Services
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from fatebridge.core.almanac import build_calendar_context, get_jieqi_year_grid
from fatebridge.core.export_parser import parse_export_content
from fatebridge.services.calculation import (
    BirthComputationContext,
    _build_birth_computation_context,
)
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    PersonInfo,
    handle_calculation_error,
    create_pillar_dict,
    get_current_analysis_date,
    format_json_response,
    calculate_solar_time_adjustment,
    normalize_birth_time,
)
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.timing import TimingAnalysis
from fatebridge.analysis.timing_effects import TimingEffectsAnalysis
from fatebridge.analysis.life_dimensions import LifeDimensionAnalysis

logger = logging.getLogger(__name__)

GEO_COORDINATE_RE = re.compile(
    r"^\s*(?P<degrees>-?\d+(?:\.\d+)?)(?:(?P<direction>[NSEWnsew])(?P<minutes>\d+(?:\.\d+)?))?\s*$"
)


def _calculate_analysis_age(
    birth_datetime: datetime,
    analysis_date: datetime,
    explicit_age: Optional[int] = None,
) -> int:
    if explicit_age is not None:
        return explicit_age

    age = analysis_date.year - birth_datetime.year
    if (analysis_date.month, analysis_date.day) < (
        birth_datetime.month,
        birth_datetime.day,
    ):
        age -= 1
    return age


def _compute_life_dimensions_for_moment(
    birth_context: BirthComputationContext,
    analysis_date: datetime,
) -> Optional[Dict[str, float]]:
    """
    为指定时刻计算用户的五维生命维度分值（爱情/财富/事业/学习/人际）。

    汇总本命四柱 + 当前可用的时间层柱（大运/流年/流月/流日/流时），
    任何一层失败都不会让整体崩溃 —— 只是少一个层级权重，
    最终 dimension 分数仍然有意义。
    """
    try:
        normalized_birth_time = birth_context.normalized_birth_time
        timezone_name = normalized_birth_time.timezone
        gender = birth_context.person.gender

        current_pillars: Dict[str, tuple] = {}

        # 流时（小时粒度）
        try:
            liushi = TimingAnalysis.calculate_liushi(analysis_date, timezone_name=timezone_name)
            current_pillars["liushi"] = (liushi["stem"], liushi["branch"])
        except Exception:
            logger.debug("life_dimensions: liushi 计算失败", exc_info=True)

        # 流日
        try:
            liuri = TimingAnalysis.calculate_liuri(analysis_date, timezone_name=timezone_name)
            current_pillars["liuri"] = (liuri["stem"], liuri["branch"])
        except Exception:
            logger.debug("life_dimensions: liuri 计算失败", exc_info=True)

        # 流月
        try:
            liuyue = TimingAnalysis.calculate_liuyue(
                analysis_date.year,
                analysis_date.month,
                analysis_date.day,
                timezone_name=timezone_name,
                target_date=analysis_date,
            )
            current_pillars["liuyue"] = (liuyue["stem"], liuyue["branch"])
        except Exception:
            logger.debug("life_dimensions: liuyue 计算失败", exc_info=True)

        # 流年
        try:
            liunian = TimingAnalysis.calculate_liunian(
                analysis_date.year, moment=analysis_date, timezone_name=timezone_name
            )
            current_pillars["liunian"] = (liunian["stem"], liunian["branch"])
        except Exception:
            logger.debug("life_dimensions: liunian 计算失败", exc_info=True)

        # 大运（依赖 gender + age）
        try:
            birth_date = normalized_birth_time.corrected_datetime
            analysis_age = _calculate_analysis_age(birth_date, analysis_date)
            dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
                birth_context.birth_pillars,
                birth_date,
                gender,
                analysis_age,
                timezone_name=timezone_name,
                original_element_counts=birth_context.original_element_counts,
            )
            dayun_info = dayun_result.get("dayun_info") if isinstance(dayun_result, dict) else None
            if dayun_info and dayun_info.get("stem") and dayun_info.get("branch"):
                current_pillars["dayun"] = (dayun_info["stem"], dayun_info["branch"])
        except Exception:
            logger.debug("life_dimensions: dayun 计算失败", exc_info=True)

        return LifeDimensionAnalysis.calculate_life_dimensions(
            birth_pillars=birth_context.birth_pillars,
            current_pillars=current_pillars,
            gender=gender,
        )
    except Exception:
        logger.warning("life_dimensions 计算整体失败，返回 None", exc_info=True)
        return None


def _serialize_element_effects(element_effects: Dict[str, Any]) -> Dict[str, Any]:
    serialized = {
        "overall_effect": element_effects["overall_effect"],
        "element_changes": {},
    }
    for element, change_info in (element_effects.get("element_changes") or {}).items():
        if change_info.get("change") != 0:
            serialized["element_changes"][element] = {
                "original": change_info["original"],
                "new": change_info["new"],
                "change": change_info["change"],
                "change_type": change_info["change_type"],
            }
    return serialized


def _build_current_timing_state(
    birth_context: BirthComputationContext,
    *,
    analysis_date: datetime,
    analysis_age: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the current timing analyses once from shared birth context."""
    timezone_name = birth_context.normalized_birth_time.timezone
    current_age = _calculate_analysis_age(
        birth_context.normalized_birth_time.corrected_datetime,
        analysis_date,
        explicit_age=analysis_age,
    )
    liuyue_info = TimingAnalysis.calculate_liuyue(
        analysis_date.year,
        analysis_date.month,
        target_day=analysis_date.day,
        timezone_name=timezone_name,
        target_date=analysis_date,
    )
    liuri_info = TimingAnalysis.calculate_liuri(
        analysis_date,
        timezone_name=timezone_name,
    )
    liushi_info = TimingAnalysis.calculate_liushi(
        analysis_date,
        timezone_name=timezone_name,
    )
    dayun_analysis = TimingEffectsAnalysis.analyze_dayun_effects(
        birth_context.birth_pillars,
        birth_context.normalized_birth_time.corrected_datetime,
        birth_context.person.gender,
        current_age,
        timezone_name=timezone_name,
        original_element_counts=birth_context.original_element_counts,
    )
    liunian_analysis = TimingEffectsAnalysis.analyze_liunian_effects(
        birth_context.birth_pillars,
        analysis_date.year,
        original_element_counts=birth_context.original_element_counts,
        moment=analysis_date,
        timezone_name=timezone_name,
    )
    liuyue_analysis = TimingEffectsAnalysis.analyze_liuyue_effects(
        birth_context.birth_pillars,
        analysis_date.year,
        analysis_date.month,
        target_day=analysis_date.day,
        timezone_name=timezone_name,
        target_date=analysis_date,
        liuyue_info=liuyue_info,
        original_element_counts=birth_context.original_element_counts,
    )
    liuri_analysis = TimingEffectsAnalysis.analyze_liuri_effects(
        birth_context.birth_pillars,
        analysis_date,
        timezone_name=timezone_name,
        liuri_info=liuri_info,
        original_element_counts=birth_context.original_element_counts,
    )
    liushi_analysis = TimingEffectsAnalysis.analyze_liushi_effects(
        birth_context.birth_pillars,
        analysis_date,
        timezone_name=timezone_name,
        liushi_info=liushi_info,
        original_element_counts=birth_context.original_element_counts,
    )

    combined_timing_pillars: Dict[str, Dict[str, str]] = {}
    if "dayun_info" in dayun_analysis:
        combined_timing_pillars["dayun"] = {
            "stem": dayun_analysis["dayun_info"]["stem"],
            "branch": dayun_analysis["dayun_info"]["branch"],
        }
    combined_timing_pillars["liunian"] = {
        "stem": liunian_analysis["liunian_info"]["stem"],
        "branch": liunian_analysis["liunian_info"]["branch"],
    }
    combined_timing_pillars["liuyue"] = {
        "stem": liuyue_analysis["liuyue_info"]["stem"],
        "branch": liuyue_analysis["liuyue_info"]["branch"],
    }
    combined_timing_pillars["liuri"] = {
        "stem": liuri_analysis["liuri_info"]["stem"],
        "branch": liuri_analysis["liuri_info"]["branch"],
    }
    combined_timing_pillars["liushi"] = {
        "stem": liushi_analysis["liushi_info"]["stem"],
        "branch": liushi_analysis["liushi_info"]["branch"],
    }

    combined_effects = TimingEffectsAnalysis.analyze_element_strength_changes(
        birth_context.birth_pillars,
        combined_timing_pillars,
        original_element_counts=birth_context.original_element_counts,
    )

    return {
        "analysis_date": analysis_date,
        "current_age": current_age,
        "dayun_analysis": dayun_analysis,
        "liunian_analysis": liunian_analysis,
        "liuyue_analysis": liuyue_analysis,
        "liuri_analysis": liuri_analysis,
        "liushi_analysis": liushi_analysis,
        "combined_effects": combined_effects,
        "comprehensive_summary": TimingEffectsAnalysis._generate_comprehensive_summary(
            dayun_analysis,
            liunian_analysis,
            liuyue_analysis,
            liuri_analysis,
            combined_effects,
            liushi_analysis=liushi_analysis,
        ),
    }


def _enrich_liuyue_timeline(
    birth_context: BirthComputationContext,
    *,
    target_year: int,
) -> List[Dict[str, Any]]:
    timezone_name = birth_context.normalized_birth_time.timezone
    liuyue_timeline = TimingAnalysis.calculate_liuyue_timeline(
        target_year,
        timezone_name=timezone_name,
    )
    for item in liuyue_timeline:
        anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
        liuyue_effect = TimingEffectsAnalysis.analyze_liuyue_effects(
            birth_context.birth_pillars,
            anchor.year,
            anchor.month,
            target_day=anchor.day,
            timezone_name=timezone_name,
            target_date=anchor,
            liuyue_info=item["liuyue"],
            original_element_counts=birth_context.original_element_counts,
        )
        item["overall_effect"] = liuyue_effect["element_effects"]["overall_effect"]
        item["summary"] = liuyue_effect["enhanced_summary"]
    return liuyue_timeline


def _enrich_jieqi_timeline(
    birth_context: BirthComputationContext,
    *,
    target_year: int,
) -> List[Dict[str, Any]]:
    timezone_name = birth_context.normalized_birth_time.timezone
    jieqi_timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
        target_year,
        timezone_name=timezone_name,
    )
    for item in jieqi_timeline:
        anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
        liuyue_pillar = item["liuyue"]
        liuri_pillar = item["liuri"]
        node_effect = TimingEffectsAnalysis.analyze_element_strength_changes(
            birth_context.birth_pillars,
            {
                "liuyue": {
                    "stem": liuyue_pillar["stem"],
                    "branch": liuyue_pillar["branch"],
                },
                "liuri": {
                    "stem": liuri_pillar["stem"],
                    "branch": liuri_pillar["branch"],
                },
            },
            original_element_counts=birth_context.original_element_counts,
        )
        liuri_effect = TimingEffectsAnalysis.analyze_liuri_effects(
            birth_context.birth_pillars,
            anchor,
            timezone_name=timezone_name,
            liuri_info=liuri_pillar,
            original_element_counts=birth_context.original_element_counts,
        )
        item["overall_effect"] = node_effect["overall_effect"]
        item["liuri_summary"] = liuri_effect["enhanced_summary"]
        item["summary"] = (
            f"{item['jieqi']['name']}节点，流月{liuyue_pillar['pillar']}，"
            f"流日{liuri_pillar['pillar']}，{node_effect['overall_effect']}"
        )
    return jieqi_timeline


def _build_snapshot_export(
    *,
    technique: str,
    snapshot_text: str,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return parse_export_content(
        technique=technique,
        content=snapshot_text,
        selected_sections=selected_sections,
    )


def _render_snapshot_text(sections: List[tuple[str, List[str]]]) -> str:
    blocks: list[str] = []
    for title, lines in sections:
        body = "\n".join(line for line in lines if line is not None).strip()
        if body:
            blocks.append(f"[{title}]\n{body}")
        else:
            blocks.append(f"[{title}]")
    return "\n\n".join(blocks).strip()


def _format_location_line(
    *,
    lat: Optional[str],
    lon: Optional[str],
    gps_lat: Optional[float],
    gps_lon: Optional[float],
) -> str:
    parts: list[str] = []
    if lat or lon:
        parts.append(f"文本提示：{lat or '未提供'} / {lon or '未提供'}")
    if gps_lat is not None or gps_lon is not None:
        parts.append(f"GPS：{gps_lat if gps_lat is not None else '未提供'} / {gps_lon if gps_lon is not None else '未提供'}")
    return "；".join(parts) if parts else "位置：未提供"


def _build_jieqi_year_snapshot_text(
    *,
    year: int,
    timezone_name: str,
    lat: Optional[str],
    lon: Optional[str],
    gps_lat: Optional[float],
    gps_lon: Optional[float],
    requested_terms: List[str],
    annual_grid: List[Dict[str, Any]],
    selected_terms: List[Dict[str, Any]],
    missing_terms: List[str],
    summary: str,
) -> str:
    query_lines = [
        f"年份：{year}",
        f"时区：{timezone_name}",
        _format_location_line(lat=lat, lon=lon, gps_lat=gps_lat, gps_lon=gps_lon),
        f"请求节气：{'、'.join(requested_terms) if requested_terms else '全部'}",
        f"返回重点节气数：{len(selected_terms)}",
        f"摘要：{summary}",
    ]
    if missing_terms:
        query_lines.append(f"未识别节气：{'、'.join(missing_terms)}")

    annual_lines = [
        f"{item.get('name', '未知')}：{item.get('datetime', '未知')} / 日干支 {item.get('day_ganzhi', '未知')}"
        for item in annual_grid
    ]
    selected_lines = [
        f"{item.get('name', '未知')}：{item.get('datetime', '未知')} / 日干支 {item.get('day_ganzhi', '未知')}"
        for item in selected_terms
    ] or ["无"]
    source_lines = [
        "来源：FateBridge 离线节气算法",
        "引用：fatebridge.core.almanac.get_jieqi_year_grid",
    ]

    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("全年节气", annual_lines),
            ("重点节气", selected_lines),
            ("来源", source_lines),
        ]
    )


def _build_nongli_time_snapshot_text(
    *,
    date: str,
    time: str,
    timezone_name: str,
    lat: Optional[str],
    lon: Optional[str],
    gps_lat: Optional[float],
    gps_lon: Optional[float],
    gender: Optional[Any],
    after23_new_day: bool,
    time_alg: int,
    time_algorithm_label: str,
    ad: int,
    effective_longitude: Optional[float],
    total_correction_minutes: float,
    calendar_context: Dict[str, Any],
    lunar_calendar: Dict[str, Any],
    year_ganzhi: str,
    month_ganzhi: str,
    day_ganzhi: str,
    time_ganzhi: str,
    summary: str,
) -> str:
    boundary = calendar_context.get("bazi_month_boundary") or {}
    current_term = calendar_context.get("current_solar_term") or {}
    next_term = calendar_context.get("next_solar_term") or {}
    query_lines = [
        f"输入公历：{date} {time}",
        f"时区：{timezone_name}",
        _format_location_line(lat=lat, lon=lon, gps_lat=gps_lat, gps_lon=gps_lon),
        f"gender 透传：{gender if gender is not None else '未提供'}",
        f"after23_new_day：{'是' if after23_new_day else '否'}",
        f"time_alg：{time_alg}（{time_algorithm_label}）",
        f"ad：{ad}",
        f"有效经度：{round(effective_longitude, 4) if effective_longitude is not None else '未提供'}",
        f"太阳时修正分钟：{round(total_correction_minutes, 2)}",
        f"摘要：{summary}",
    ]

    lunar_lines = [
        f"换算时刻：{calendar_context.get('solar_datetime', '未知')}",
        f"农历：{lunar_calendar.get('display', '未知')}",
        f"农历年月日：{lunar_calendar.get('year_cn', '')}年{lunar_calendar.get('month_cn', '')}{lunar_calendar.get('day_cn', '')}".strip(),
        f"当前节气：{current_term.get('name', '未知')} / {current_term.get('datetime', '未知')}",
        f"下一节气：{next_term.get('name', '未知')} / {next_term.get('datetime', '未知')}",
        f"节差：{lunar_calendar.get('jiedelta', '未知')}",
        f"月令窗口：{boundary.get('start_term', {}).get('name', '未知')} -> {boundary.get('next_term', {}).get('name', '未知')}",
        f"是否闰月：{'是' if lunar_calendar.get('is_leap_month') else '否'}",
    ]
    if lunar_calendar.get("meihua"):
        lunar_lines.append("梅花时卦辅助：已生成")

    pillar_lines = [
        f"年柱：{year_ganzhi}",
        f"节气分年：{lunar_calendar.get('year_jieqi_ganzhi', year_ganzhi)}",
        f"月柱：{month_ganzhi}",
        f"日柱：{day_ganzhi}",
        f"时柱：{time_ganzhi}",
        f"月令分支：{boundary.get('branch', '未知')}",
        f"距下个节气天数：{lunar_calendar.get('days_until_next_jieqi', '未知')}",
    ]

    source_lines = [
        "来源：FateBridge 离线农历/节气算法",
        "引用：fatebridge.core.almanac.build_calendar_context / fatebridge.core.calendar.BaZiCalendar",
    ]

    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("农历上下文", lunar_lines),
            ("四柱上下文", pillar_lines),
            ("来源", source_lines),
        ]
    )


def _build_liuyue_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    analysis_date: datetime,
    analysis_calendar_context: Dict[str, Any],
    liuyue_info: Dict[str, Any],
    liunian_info: Optional[Dict[str, Any]],
    detailed_analysis: Dict[str, Any],
    element_effects: Dict[str, Any],
    combination_effects: Dict[str, Any],
    summary: str,
) -> str:
    current_term = (analysis_calendar_context.get("current_solar_term") or {}).get("name", "未知")
    next_term = (analysis_calendar_context.get("next_solar_term") or {}).get("name", "未知")
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"分析时刻：{analysis_date.strftime('%Y-%m-%d %H:%M')}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"分析日节气：{current_term} -> {next_term}",
        f"摘要：{summary}",
    ]

    solar_term_window = liuyue_info.get("solar_term_window") or {}
    liuyue_lines = [
        f"流月：{liuyue_info.get('pillar', '未知')}",
        f"月干支：{liuyue_info.get('stem', '未知')}{liuyue_info.get('branch', '未知')}",
        f"五行：{liuyue_info.get('element', '未知')}",
        f"纳音：{liuyue_info.get('nayin', '未知')}",
        f"节令窗口：{solar_term_window.get('start_term', {}).get('name', '未知')} -> {solar_term_window.get('next_term', {}).get('name', '未知')}",
        f"窗口时刻：{solar_term_window.get('start_term', {}).get('datetime', '未知')} -> {solar_term_window.get('next_term', {}).get('datetime', '未知')}",
    ]

    combo_lines: list[str] = []
    if liunian_info:
        combo_lines.append(f"流年：{liunian_info.get('pillar', '未知')}")
        combo_lines.append(
            f"流年月支：{liuyue_info.get('branch', '未知')} / 流年支：{liunian_info.get('branch', '未知')}"
        )
    liuyue_liunian = combination_effects.get("liuyue_liunian") or {}
    if liuyue_liunian:
        combo_lines.append(f"组合总效应：{liuyue_liunian.get('overall_effect', '未知')}")
        combo_lines.append(f"组合影响分：{liuyue_liunian.get('total_impact_score', '未知')}")
        for relation in liuyue_liunian.get("relations") or []:
            combo_lines.append(
                f"{relation.get('type', '普通')}：{relation.get('description', '无')} / "
                f"{relation.get('effect', '无')} / 分值 {relation.get('impact_score', '未知')}"
            )
    if not combo_lines:
        combo_lines.append("无流年联动信息")

    effect_lines = [
        f"十神关系：{detailed_analysis.get('stem_relation', '未知')}",
        f"总体五行：{element_effects.get('overall_effect', '未知')}",
    ]
    fortune_analysis = detailed_analysis.get("fortune_analysis") or {}
    if fortune_analysis:
        effect_lines.append(f"运势等级：{fortune_analysis.get('overall_fortune', '未知')}")
        effect_lines.append(f"运势分数：{fortune_analysis.get('fortune_score', '未知')}")
        effect_lines.append(f"细断：{fortune_analysis.get('detailed_analysis', '无')}")
    for relation in detailed_analysis.get("branch_relations") or []:
        effect_lines.append(
            f"{relation.get('type', '普通')}：{relation.get('description', '无')}"
        )
    for suggestion in detailed_analysis.get("suggestions") or []:
        effect_lines.append(f"建议：{suggestion}")

    source_lines = [
        "来源：FateBridge 离线时运分析",
        "引用：fatebridge.analysis.timing_effects / analyze_liuyue_comprehensive",
    ]

    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("流月信息", liuyue_lines),
            ("流年联动", combo_lines),
            ("影响摘要", effect_lines),
            ("来源", source_lines),
        ]
    )


def _build_dayun_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    analysis_age: int,
    dayun_info: Optional[Dict[str, Any]],
    element_effects: Dict[str, Any],
    summary: str,
) -> str:
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"分析年龄：{analysis_age}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"摘要：{summary}",
    ]
    if dayun_info:
        dayun_lines = [
            f"当前大运：{dayun_info.get('pillar', dayun_info.get('current_dayun', '未知'))}",
            f"大运干支：{dayun_info.get('stem', '未知')}{dayun_info.get('branch', '未知')}",
            f"起运年龄：{dayun_info.get('start_age', '未知')}",
            f"当前运龄：{dayun_info.get('dayun_age', '未知')}",
            f"本运已行年数：{dayun_info.get('years_in_period', '未知')}",
        ]
    else:
        dayun_lines = ["当前大运：不可用"]

    effect_lines = [
        f"总体五行：{element_effects.get('overall_effect', '未知')}",
    ]
    for element, change_info in (element_effects.get("element_changes") or {}).items():
        if change_info.get("change") != 0:
            effect_lines.append(
                f"{element}：{change_info.get('change_type', '变化')} "
                f"({change_info.get('original', '未知')} -> {change_info.get('new', '未知')})"
            )

    source_lines = [
        "来源：FateBridge 离线大运分析",
        "引用：fatebridge.analysis.timing_effects / analyze_dayun_effects",
    ]
    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("大运信息", dayun_lines),
            ("影响摘要", effect_lines),
            ("来源", source_lines),
        ]
    )


def _build_liunian_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    target_year: int,
    liunian_info: Dict[str, Any],
    element_effects: Dict[str, Any],
    summary: str,
) -> str:
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"目标年份：{target_year}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"摘要：{summary}",
    ]
    year_lines = [
        f"流年：{liunian_info.get('pillar', '未知')}",
        f"年干支：{liunian_info.get('stem', '未知')}{liunian_info.get('branch', '未知')}",
        f"五行：{liunian_info.get('element', '未知')}",
    ]
    effect_lines = [
        f"总体五行：{element_effects.get('overall_effect', '未知')}",
    ]
    for element, change_info in (element_effects.get("element_changes") or {}).items():
        if change_info.get("change") != 0:
            effect_lines.append(
                f"{element}：{change_info.get('change_type', '变化')} "
                f"({change_info.get('original', '未知')} -> {change_info.get('new', '未知')})"
            )
    source_lines = [
        "来源：FateBridge 离线流年分析",
        "引用：fatebridge.analysis.timing_effects / analyze_liunian_effects",
    ]
    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("流年信息", year_lines),
            ("影响摘要", effect_lines),
            ("来源", source_lines),
        ]
    )


def _build_liuri_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    analysis_date: datetime,
    analysis_calendar_context: Dict[str, Any],
    liuri_info: Dict[str, Any],
    element_effects: Dict[str, Any],
    summary: str,
) -> str:
    current_term = (analysis_calendar_context.get("current_solar_term") or {}).get("name", "未知")
    next_term = (analysis_calendar_context.get("next_solar_term") or {}).get("name", "未知")
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"分析时刻：{analysis_date.strftime('%Y-%m-%d %H:%M')}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"分析日节气：{current_term} -> {next_term}",
        f"摘要：{summary}",
    ]
    day_lines = [
        f"流日：{liuri_info.get('pillar', '未知')}",
        f"日干支：{liuri_info.get('stem', '未知')}{liuri_info.get('branch', '未知')}",
        f"五行：{liuri_info.get('element', '未知')}",
        f"星期：{liuri_info.get('weekday', '未知')}",
    ]
    effect_lines = [
        f"总体五行：{element_effects.get('overall_effect', '未知')}",
    ]
    for element, change_info in (element_effects.get("element_changes") or {}).items():
        if change_info.get("change") != 0:
            effect_lines.append(
                f"{element}：{change_info.get('change_type', '变化')} "
                f"({change_info.get('original', '未知')} -> {change_info.get('new', '未知')})"
            )
    source_lines = [
        "来源：FateBridge 离线流日分析",
        "引用：fatebridge.analysis.timing_effects / analyze_liuri_effects",
    ]
    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("流日信息", day_lines),
            ("影响摘要", effect_lines),
            ("来源", source_lines),
        ]
    )


def _build_liushi_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    analysis_date: datetime,
    analysis_calendar_context: Dict[str, Any],
    liushi_info: Dict[str, Any],
    detailed_analysis: Dict[str, Any],
    element_effects: Dict[str, Any],
    summary: str,
) -> str:
    current_term = (analysis_calendar_context.get("current_solar_term") or {}).get(
        "name", "未知"
    )
    next_term = (analysis_calendar_context.get("next_solar_term") or {}).get(
        "name", "未知"
    )
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"分析时刻：{analysis_date.strftime('%Y-%m-%d %H:%M')}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"分析日节气：{current_term} -> {next_term}",
        f"摘要：{summary}",
    ]
    hour_lines = [
        f"流时：{liushi_info.get('pillar', '未知')}",
        f"时干支：{liushi_info.get('stem', '未知')}{liushi_info.get('branch', '未知')}",
        f"五行：{liushi_info.get('element', '未知')}",
        f"纳音：{liushi_info.get('nayin', '未知')}",
        f"时刻：{liushi_info.get('analysis_datetime', '未知')}",
        f"时辰支：{liushi_info.get('shichen', '未知')}",
    ]
    effect_lines = [
        f"总体五行：{element_effects.get('overall_effect', '未知')}",
        f"十神关系：{detailed_analysis.get('stem_relation', '未知')}",
    ]
    fortune_analysis = detailed_analysis.get("fortune_analysis") or {}
    if fortune_analysis:
        effect_lines.append(f"运势等级：{fortune_analysis.get('overall_fortune', '未知')}")
        effect_lines.append(f"运势分数：{fortune_analysis.get('fortune_score', '未知')}")
        effect_lines.append(f"细断：{fortune_analysis.get('detailed_analysis', '无')}")
    for relation in detailed_analysis.get("branch_relations") or []:
        effect_lines.append(
            f"{relation.get('type', '普通')}：{relation.get('description', '无')}"
        )
    for suggestion in detailed_analysis.get("suggestions") or []:
        effect_lines.append(f"建议：{suggestion}")

    source_lines = [
        "来源：FateBridge 离线流时分析",
        "引用：fatebridge.analysis.timing_effects / analyze_liushi_effects",
    ]
    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("流时信息", hour_lines),
            ("影响摘要", effect_lines),
            ("来源", source_lines),
        ]
    )


def _build_jieqi_timeline_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    target_year: int,
    target_year_jieqi: List[Dict[str, Any]],
    jieqi_timeline: List[Dict[str, Any]],
    summary: str,
) -> str:
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"目标年份：{target_year}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"节点数量：{len(jieqi_timeline)}",
        f"摘要：{summary}",
    ]
    annual_lines = [
        f"{item.get('name', '未知')}：{item.get('datetime', '未知')} / 日干支 {item.get('day_ganzhi', '未知')}"
        for item in target_year_jieqi
    ]
    timeline_lines = [
        f"{item.get('order', '?')}. {item.get('jieqi', {}).get('name', '未知')} / "
        f"{item.get('analysis_anchor', '未知')} / 流月 {item.get('liuyue', {}).get('pillar', '未知')} / "
        f"流日 {item.get('liuri', {}).get('pillar', '未知')} / {item.get('overall_effect', '未知')}"
        for item in jieqi_timeline
    ]
    source_lines = [
        "来源：FateBridge 离线节气时间轴分析",
        "引用：fatebridge.core.timing.calculate_jieqi_transition_timeline",
    ]

    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("年度节气", annual_lines),
            ("节点时间轴", timeline_lines),
            ("来源", source_lines),
        ]
    )


def _build_comprehensive_timing_snapshot_text(
    *,
    person_name: str,
    birth_datetime: datetime,
    normalized_birth_datetime: datetime,
    timezone_name: str,
    analysis_date: datetime,
    current_age: int,
    analysis_calendar_context: Dict[str, Any],
    dayun_info: Dict[str, Any],
    liunian_info: Dict[str, Any],
    liuyue_info: Dict[str, Any],
    liuri_info: Dict[str, Any],
    liushi_info: Dict[str, Any],
    combined_effects: Dict[str, Any],
    summary: str,
) -> str:
    current_term = (analysis_calendar_context.get("current_solar_term") or {}).get(
        "name", "未知"
    )
    next_term = (analysis_calendar_context.get("next_solar_term") or {}).get(
        "name", "未知"
    )
    query_lines = [
        f"姓名：{person_name or '未提供'}",
        f"分析时刻：{analysis_date.strftime('%Y-%m-%d %H:%M')}",
        f"当前年龄：{current_age}",
        f"出生时间：{birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"归一时间：{normalized_birth_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"时区：{timezone_name}",
        f"分析日节气：{current_term} -> {next_term}",
        f"摘要：{summary}",
    ]

    if dayun_info.get("error"):
        dayun_lines = [f"当前大运：{dayun_info['error']}"]
    else:
        dayun_lines = [
            f"当前大运：{dayun_info.get('current_dayun', '未知')}",
            f"大运干支：{dayun_info.get('stem', '未知')}{dayun_info.get('branch', '未知')}",
            f"起运年龄：{dayun_info.get('start_age', '未知')}",
            f"当前运龄：{dayun_info.get('dayun_age', '未知')}",
            f"本运已行年数：{dayun_info.get('years_in_period', '未知')}",
            f"概览：{dayun_info.get('summary', '无')}",
        ]

    flow_lines = [
        f"流年：{liunian_info.get('pillar', '未知')} / {liunian_info.get('summary', '无')}",
        f"流月：{liuyue_info.get('pillar', '未知')} / {liuyue_info.get('summary', '无')}",
        f"流日：{liuri_info.get('pillar', '未知')} / {liuri_info.get('summary', '无')}",
        f"流时：{liushi_info.get('pillar', '未知')} / {liushi_info.get('summary', '无')}",
    ]

    impact_lines = [
        f"综合效应：{combined_effects.get('overall_effect', '未知')}",
    ]
    for element, change_info in (combined_effects.get("element_changes") or {}).items():
        if change_info.get("change") != 0:
            impact_lines.append(
                f"{element}：{change_info.get('change_type', '变化')} "
                f"({change_info.get('original', '未知')} -> {change_info.get('new', '未知')})"
            )

    source_lines = [
        "来源：FateBridge 离线综合时运分析",
        "引用：fatebridge.analysis.timing_effects / comprehensive_timing_analysis",
    ]
    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("大运摘要", dayun_lines),
            ("流年流月流日", flow_lines),
            ("综合影响", impact_lines),
            ("来源", source_lines),
        ]
    )


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _parse_calendar_datetime(date_text: str, time_text: str) -> datetime:
    normalized_date = (date_text or "").strip().replace("/", "-")
    normalized_time = (time_text or "").strip()
    if not normalized_date or not normalized_time:
        raise ValueError("date 和 time 不能为空。")

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(
                f"{normalized_date} {normalized_time}",
                fmt,
            )
        except ValueError:
            continue

    raise ValueError("无法解析 date/time，请使用 YYYY-MM-DD 与 HH:MM[:SS]。")


def _normalize_time_alg(value: Any) -> int:
    return 1 if value == 1 else 0


def _parse_geo_coordinate(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = GEO_COORDINATE_RE.match(str(value))
    if not match:
        return None

    degrees = float(match.group("degrees"))
    direction = (match.group("direction") or "").upper()
    minutes = float(match.group("minutes") or "0")

    if direction:
        decimal = abs(degrees) + minutes / 60.0
        if direction in {"S", "W"}:
            decimal *= -1
        return decimal

    return degrees


def calculate_jieqi_year(
    *,
    year: int,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    jieqis: Optional[List[str]] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    全年节气辅助工具 - 生成全年 24 节气列表，并可筛选重点节气。
    """
    try:
        timezone_name = zone or DEFAULT_BIRTH_TIMEZONE
        normalized_year = int(year)
        annual_grid = get_jieqi_year_grid(normalized_year, timezone_name)
        requested_terms = jieqis or []
        by_name = {item["name"]: item for item in annual_grid}
        selected_terms = [
            by_name[name] for name in requested_terms if name in by_name
        ] if requested_terms else annual_grid
        missing_terms = [
            name for name in requested_terms if name not in by_name
        ]

        summary = (
            f"{normalized_year}年共生成{len(annual_grid)}个节气节点，"
            f"当前返回{len(selected_terms)}个重点节气。"
        )
        snapshot_text = _build_jieqi_year_snapshot_text(
            year=normalized_year,
            timezone_name=timezone_name,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            requested_terms=requested_terms,
            annual_grid=annual_grid,
            selected_terms=selected_terms,
            missing_terms=missing_terms,
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="jieqi_year",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        result: Dict[str, Any] = {
            "analysis_type": "全年节气盘",
            "query_context": {
                "year": normalized_year,
                "timezone": timezone_name,
                "lat": lat,
                "lon": lon,
                "gps_lat": gps_lat,
                "gps_lon": gps_lon,
                "requested_jieqis": requested_terms,
            },
            "year": normalized_year,
            "jieqi24": annual_grid,
            "jieqi_year": annual_grid,
            "selected_jieqi": selected_terms,
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
        if missing_terms:
            result["warnings"] = [
                f"未识别的节气名称：{'、'.join(missing_terms)}"
            ]
        return result
    except Exception as exc:
        return handle_calculation_error(exc, "全年节气盘")


def calculate_nongli_time(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    gender: Optional[Any] = None,
    after23_new_day: Optional[Any] = False,
    time_alg: int = 0,
    ad: int = 1,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    农历换算辅助工具 - 输出农历、节气与干支上下文。
    """
    try:
        if ad != 1:
            raise ValueError("离线农历换算当前仅支持公元日期（ad=1）。")

        timezone_name = zone or DEFAULT_BIRTH_TIMEZONE
        normalized_time_alg = _normalize_time_alg(time_alg)
        input_datetime = _parse_calendar_datetime(date, time)
        corrected_datetime = input_datetime
        analysis_datetime = input_datetime
        total_correction_minutes = 0.0
        effective_longitude = (
            gps_lon if gps_lon is not None else _parse_geo_coordinate(lon)
        )
        time_algorithm_label = "直接时间"
        warnings: List[str] = []

        if normalized_time_alg == 0:
            if effective_longitude is not None:
                adjustment = calculate_solar_time_adjustment(
                    input_datetime,
                    timezone_name,
                    effective_longitude,
                )
                total_correction_minutes = adjustment["total_correction_minutes"]
                corrected_datetime = input_datetime + timedelta(
                    minutes=total_correction_minutes
                )
                analysis_datetime = corrected_datetime
                time_algorithm_label = "真太阳时"
            else:
                warnings.append(
                    "time_alg=0 需要 lon 或 gps_lon 才能计算真太阳时，已回退为直接时间。"
                )

        if _coerce_bool(after23_new_day) and analysis_datetime.hour >= 23:
            analysis_datetime += timedelta(days=1)

        pillars = BaZiCalendar.get_four_pillars(
            analysis_datetime,
            timezone_name=timezone_name,
        )
        calendar_context = build_calendar_context(
            analysis_datetime,
            timezone_name=timezone_name,
            pillars=pillars,
        )
        lunar_calendar = calendar_context.get("lunar_calendar") or {}
        lunar_support = calendar_context.get("lunar_calendar_support") or {}
        if not lunar_support.get("supported", bool(lunar_calendar)):
            raise ValueError(
                lunar_support.get("reason")
                or "离线农历换算当前不支持该日期。"
            )
        summary = (
            f"{calendar_context['solar_datetime']} 对应农历"
            f"{lunar_calendar.get('display', '未知')}，"
            f"当前节气为{calendar_context['current_solar_term']['name']}。"
        )

        year_ganzhi = f"{pillars['year'][0]}{pillars['year'][1]}"
        month_ganzhi = f"{pillars['month'][0]}{pillars['month'][1]}"
        day_ganzhi = f"{pillars['day'][0]}{pillars['day'][1]}"
        time_ganzhi = f"{pillars['hour'][0]}{pillars['hour'][1]}"
        nongli_display = (
            f"{lunar_calendar.get('year_cn', '')}年"
            f"{lunar_calendar.get('month_cn', '')}"
            f"{lunar_calendar.get('day_cn', '')}"
        ).strip() or lunar_calendar.get("display", "")
        snapshot_text = _build_nongli_time_snapshot_text(
            date=date,
            time=time,
            timezone_name=timezone_name,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            gender=gender,
            after23_new_day=_coerce_bool(after23_new_day),
            time_alg=normalized_time_alg,
            time_algorithm_label=time_algorithm_label,
            ad=ad,
            effective_longitude=effective_longitude,
            total_correction_minutes=total_correction_minutes,
            calendar_context=calendar_context,
            lunar_calendar=lunar_calendar,
            year_ganzhi=year_ganzhi,
            month_ganzhi=lunar_calendar.get("month_ganzhi", month_ganzhi),
            day_ganzhi=lunar_calendar.get("day_ganzhi", day_ganzhi),
            time_ganzhi=lunar_calendar.get("time_ganzhi", time_ganzhi),
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="nongli_time",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        result = {
            "analysis_type": "农历换算",
            "input_context": {
                "date": date,
                "time": time,
                "timezone": timezone_name,
                "lat": lat,
                "lon": lon,
                "gps_lat": gps_lat,
                "gps_lon": gps_lon,
                "gender": gender,
                "after23_new_day": _coerce_bool(after23_new_day),
                "time_alg": normalized_time_alg,
                "ad": ad,
            },
            "analysis_context": {
                "input_datetime": input_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "corrected_datetime": corrected_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "effective_datetime": analysis_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                "time_algorithm": time_algorithm_label,
                "longitude": effective_longitude,
                "total_correction_minutes": round(total_correction_minutes, 2),
            },
            "birth": calendar_context["solar_datetime"],
            "nongli": nongli_display,
            "year": year_ganzhi,
            "yearGanZi": year_ganzhi,
            "yearJieqi": lunar_calendar.get("year_jieqi_ganzhi", year_ganzhi),
            "monthGanZi": lunar_calendar.get("month_ganzhi", month_ganzhi),
            "dayGanZi": lunar_calendar.get("day_ganzhi", day_ganzhi),
            "time": lunar_calendar.get("time_ganzhi", time_ganzhi),
            "timeGanZi": lunar_calendar.get("time_ganzhi", time_ganzhi),
            "jieqi": lunar_calendar.get("jieqi"),
            "jiedelta": lunar_calendar.get("jiedelta"),
            "month": lunar_calendar.get("month_cn"),
            "day": lunar_calendar.get("day_cn"),
            "monthInt": lunar_calendar.get("month"),
            "dayInt": lunar_calendar.get("day"),
            "leap": lunar_calendar.get("is_leap_month", False),
            "calendar_context": calendar_context,
            "lunar_calendar": lunar_calendar,
            "four_pillars": create_pillar_dict(pillars),
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
        if warnings:
            result["warnings"] = warnings
        return result
    except Exception as exc:
        return handle_calculation_error(exc, "农历换算")


def calculate_comprehensive_timing(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_age: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    计算时运分析，包括大运、流年、流月、流日、流时的影响分析
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        input_birth_datetime = normalized_birth_time.input_datetime
        birth_date = normalized_birth_time.corrected_datetime

        # 设置分析日期
        analysis_year, analysis_month = get_current_analysis_date(
            analysis_year, analysis_month
        )
        if analysis_day is None:
            analysis_day = 1
        if analysis_hour is None:
            analysis_hour = 0
        if analysis_minute is None:
            analysis_minute = 0
        analysis_date = datetime(
            analysis_year,
            analysis_month,
            analysis_day,
            analysis_hour,
            analysis_minute,
        )
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        analysis_year_jieqi = get_jieqi_year_grid(
            analysis_year, normalized_birth_time.timezone
        )
        liuyue_timeline = _enrich_liuyue_timeline(
            birth_context,
            target_year=analysis_year,
        )
        jieqi_timeline = _enrich_jieqi_timeline(
            birth_context,
            target_year=analysis_year,
        )
        timing_result = _build_current_timing_state(
            birth_context,
            analysis_date=analysis_date,
            analysis_age=analysis_age,
        )
        current_age = timing_result["current_age"]

        # 构建最终结果结构
        result = {
            "analysis_type": "综合时运分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": input_birth_datetime.strftime("%Y-%m-%d %H:%M"),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "gender": person.gender,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "analysis_datetime": analysis_date.strftime("%Y-%m-%d %H:%M"),
                "current_age": current_age,
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "birth_pillars": create_pillar_dict(birth_context.birth_pillars),
            "calendar_context": birth_context.birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
                "analysis_year_jieqi": analysis_year_jieqi,
                "liuyue_timeline": liuyue_timeline,
                "jieqi_timeline": jieqi_timeline,
            },
        }

        # 大运分析
        dayun_analysis = timing_result["dayun_analysis"]
        if "dayun_info" in dayun_analysis:
            dayun_info = dayun_analysis["dayun_info"]
            age_info = dayun_analysis["age_info"]
            dayun_section: Dict[str, Any] = {
                "current_dayun": dayun_info["pillar"],
                "stem": dayun_info["stem"],
                "branch": dayun_info["branch"],
                "start_age": age_info["start_age"],
                "dayun_age": age_info["dayun_age"],
                "years_in_period": age_info["years_in_period"],
                "summary": dayun_analysis["summary"],
            }
            # Include element_effects so downstream consumers (e.g. HorizonX
            # letters emotion curve) can score the dayun layer when they
            # receive the comprehensive payload as a fallback.
            if "element_effects" in dayun_analysis:
                dayun_section["element_effects"] = _serialize_element_effects(
                    dayun_analysis["element_effects"]
                )
            result["dayun_analysis"] = dayun_section
        else:
            result["dayun_analysis"] = {
                "error": dayun_analysis.get("message", "大运信息不可用")
            }

        # 流年分析
        liunian_analysis = timing_result["liunian_analysis"]
        liunian_info = liunian_analysis["liunian_info"]
        liunian_section: Dict[str, Any] = {
            "pillar": liunian_info["pillar"],
            "stem": liunian_info["stem"],
            "branch": liunian_info["branch"],
            "summary": liunian_analysis["summary"],
        }
        if "element_effects" in liunian_analysis:
            liunian_section["element_effects"] = _serialize_element_effects(
                liunian_analysis["element_effects"]
            )
        result["liunian_analysis"] = liunian_section

        # 流月分析
        liuyue_analysis = timing_result["liuyue_analysis"]
        liuyue_info = liuyue_analysis["liuyue_info"]
        result["liuyue_analysis"] = {
            "pillar": liuyue_info["pillar"],
            "stem": liuyue_info["stem"],
            "branch": liuyue_info["branch"],
            "summary": liuyue_analysis["summary"],
        }

        # 流日分析
        liuri_analysis = timing_result["liuri_analysis"]
        liuri_info = liuri_analysis["liuri_info"]
        result["liuri_analysis"] = {
            "pillar": liuri_info["pillar"],
            "stem": liuri_info["stem"],
            "branch": liuri_info["branch"],
            "summary": liuri_analysis["summary"],
        }

        # 流时分析
        liushi_analysis = timing_result["liushi_analysis"]
        liushi_info = liushi_analysis["liushi_info"]
        result["liushi_analysis"] = {
            "pillar": liushi_info["pillar"],
            "stem": liushi_info["stem"],
            "branch": liushi_info["branch"],
            "hour": liushi_info["hour"],
            "summary": liushi_analysis["summary"],
        }

        # 综合影响
        combined_effects = timing_result["combined_effects"]
        result["combined_effects"] = _serialize_element_effects(combined_effects)

        # 综合总结
        result["comprehensive_summary"] = timing_result["comprehensive_summary"]
        result["snapshot_text"] = _build_comprehensive_timing_snapshot_text(
            person_name=person.name,
            birth_datetime=input_birth_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            analysis_date=analysis_date,
            current_age=current_age,
            analysis_calendar_context=analysis_calendar_context,
            dayun_info=result["dayun_analysis"],
            liunian_info=result["liunian_analysis"],
            liuyue_info=result["liuyue_analysis"],
            liuri_info=result["liuri_analysis"],
            liushi_info=result["liushi_analysis"],
            combined_effects=result["combined_effects"],
            summary=result["comprehensive_summary"],
        )
        result["snapshot_export"] = _build_snapshot_export(
            technique="timing_analysis",
            snapshot_text=result["snapshot_text"],
            selected_sections=selected_sections,
        )

        return result

    except Exception as e:
        return handle_calculation_error(e, "时运分析计算")

def calculate_dayun_analysis(
    person: PersonInfo,
    analysis_age: int,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    大运分析工具 - 专门分析指定年龄的大运情况
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_context.birth_pillars,
            birth_date,
            person.gender,
            analysis_age,
            timezone_name=normalized_birth_time.timezone,
            original_element_counts=birth_context.original_element_counts,
        )

        result = {
            "analysis_type": "大运专项分析",
            "personal_info": {
                "name": person.name,
                "gender": person.gender,
                "analysis_age": analysis_age,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
        }

        dayun_info: Optional[Dict[str, Any]] = None
        element_effects: Dict[str, Any] = {}

        if "dayun_info" in dayun_result:
            dayun_info = dayun_result["dayun_info"]
            age_info = dayun_result["age_info"]
            element_effects = dayun_result["element_effects"]

            result["dayun_info"] = {
                "current_dayun": dayun_info["pillar"],
                "stem": dayun_info["stem"],
                "branch": dayun_info["branch"],
                "start_age": age_info["start_age"],
                "dayun_age": age_info["dayun_age"],
                "years_in_period": age_info["years_in_period"],
            }

            result["element_effects"] = _serialize_element_effects(element_effects)

            result["summary"] = dayun_result["summary"]
        else:
            result["error"] = dayun_result.get("message", "大运信息不可用")
            result["summary"] = result["error"]

        snapshot_text = _build_dayun_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            analysis_age=analysis_age,
            dayun_info=result.get("dayun_info") or dayun_info,
            element_effects=result.get("element_effects", element_effects),
            summary=result.get("summary", "大运信息不可用"),
        )
        result["snapshot_text"] = snapshot_text
        result["snapshot_export"] = _build_snapshot_export(
            technique="dayun_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        return result

    except Exception as e:
        return handle_calculation_error(e, "大运分析计算")

def calculate_liunian_analysis(
    person: PersonInfo,
    target_year: int,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流年分析工具 - 专门分析指定年份的流年影响
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        liunian_result = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_context.birth_pillars,
            target_year,
            original_element_counts=birth_context.original_element_counts,
        )

        liunian_info = liunian_result["liunian_info"]
        element_effects = liunian_result["element_effects"]
        summary = liunian_result["summary"]
        snapshot_text = _build_liunian_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            target_year=target_year,
            liunian_info=liunian_info,
            element_effects=element_effects,
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="liunian_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        result = {
            "analysis_type": "流年专项分析",
            "personal_info": {
                "name": person.name,
                "target_year": target_year,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
            "target_year_jieqi": get_jieqi_year_grid(
                target_year, normalized_birth_time.timezone
            ),
            "liunian_info": {
                "pillar": liunian_info["pillar"],
                "stem": liunian_info["stem"],
                "branch": liunian_info["branch"],
                "element": liunian_info["element"],
            },
            "element_effects": _serialize_element_effects(element_effects),
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

        result["summary"] = summary
        return result

    except Exception as e:
        return handle_calculation_error(e, "流年分析计算")


def calculate_liuyue_analysis(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流月分析工具 - 专门分析指定日期所在节令月的影响
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = 1
        if analysis_hour is None:
            analysis_hour = 0
        if analysis_minute is None:
            analysis_minute = 0

        analysis_date = datetime(
            analysis_year,
            analysis_month,
            analysis_day,
            analysis_hour,
            analysis_minute,
        )
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        liuyue_info = TimingAnalysis.calculate_liuyue(
            analysis_year,
            analysis_month,
            target_day=analysis_day,
            timezone_name=normalized_birth_time.timezone,
            target_date=analysis_date,
        )
        liunian_analysis = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_context.birth_pillars,
            analysis_year,
            original_element_counts=birth_context.original_element_counts,
            moment=analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuyue_result = TimingEffectsAnalysis.analyze_liuyue_comprehensive(
            birth_context.birth_pillars,
            analysis_year,
            analysis_month,
            include_dayun=False,
            include_liunian=True,
            target_day=analysis_day,
            timezone_name=normalized_birth_time.timezone,
            target_date=analysis_date,
            liuyue_info=liuyue_info,
            liunian_analysis=liunian_analysis,
            original_element_counts=birth_context.original_element_counts,
        )

        liuyue_analysis = liuyue_result["liuyue_analysis"]
        liuyue_info = liuyue_analysis["liuyue_info"]
        detailed_analysis = liuyue_analysis["detailed_analysis"]
        element_effects = liuyue_analysis["element_effects"]
        liunian_analysis = liuyue_result.get("liunian_analysis")
        liunian_info = None
        if liunian_analysis:
            liunian_info = liunian_analysis["liunian_info"]
        summary = liuyue_result["comprehensive_summary"]
        snapshot_text = _build_liuyue_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            analysis_date=analysis_date,
            analysis_calendar_context=analysis_calendar_context,
            liuyue_info=liuyue_info,
            liunian_info=liunian_info,
            detailed_analysis=detailed_analysis,
            element_effects=element_effects,
            combination_effects=liuyue_result.get("combination_effects", {}),
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="liuyue_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        result = {
            "analysis_type": "流月专项分析",
            "personal_info": {
                "name": person.name,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "analysis_datetime": analysis_date.strftime("%Y-%m-%d %H:%M"),
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
            },
            "target_year_jieqi": get_jieqi_year_grid(
                analysis_year, normalized_birth_time.timezone
            ),
            "liuyue_info": {
                "pillar": liuyue_info["pillar"],
                "stem": liuyue_info["stem"],
                "branch": liuyue_info["branch"],
                "element": liuyue_info["element"],
                "nayin": liuyue_info["nayin"],
                "solar_term_window": liuyue_info["solar_term_window"],
            },
            "detailed_analysis": {
                "stem_relation": detailed_analysis["shishen_analysis"][
                    "stem_relation"
                ],
                "branch_relations": detailed_analysis["branch_relations"],
                "fortune_analysis": detailed_analysis["fortune_analysis"],
                "suggestions": detailed_analysis["suggestions"],
            },
            "element_effects": _serialize_element_effects(element_effects),
            "combination_effects": liuyue_result.get("combination_effects", {}),
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

        if liunian_analysis:
            result["liunian_info"] = {
                "pillar": liunian_info["pillar"],
                "stem": liunian_info["stem"],
                "branch": liunian_info["branch"],
                "element": liunian_info["element"],
            }

        result["summary"] = summary
        return result

    except Exception as e:
        return handle_calculation_error(e, "流月分析计算")


def calculate_liuri_analysis(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流日分析工具 - 专门分析指定日期的流日影响
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = now.day
        if analysis_hour is None:
            analysis_hour = 0
        if analysis_minute is None:
            analysis_minute = 0

        analysis_date = datetime(
            analysis_year,
            analysis_month,
            analysis_day,
            analysis_hour,
            analysis_minute,
        )
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        liuri_info = TimingAnalysis.calculate_liuri(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuri_result = TimingEffectsAnalysis.analyze_liuri_effects(
            birth_context.birth_pillars,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
            liuri_info=liuri_info,
            original_element_counts=birth_context.original_element_counts,
        )

        liuri_info = liuri_result["liuri_info"]
        element_effects = liuri_result["element_effects"]
        summary = liuri_result["enhanced_summary"]
        snapshot_text = _build_liuri_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            analysis_date=analysis_date,
            analysis_calendar_context=analysis_calendar_context,
            liuri_info=liuri_info,
            element_effects=element_effects,
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="liuri_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        result = {
            "analysis_type": "流日专项分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "analysis_datetime": analysis_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
            },
            "liuri_info": {
                "pillar": liuri_info["pillar"],
                "stem": liuri_info["stem"],
                "branch": liuri_info["branch"],
                "element": liuri_info["element"],
                "weekday": liuri_info["weekday"],
            },
            "element_effects": _serialize_element_effects(element_effects),
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

        return result

    except Exception as e:
        return handle_calculation_error(e, "流日分析计算")


def calculate_liushi_analysis(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    analysis_hour: Optional[int] = None,
    analysis_minute: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流时分析工具 - 专门分析指定时刻的流时影响
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = now.day
        if analysis_hour is None:
            analysis_hour = now.hour
        if analysis_minute is None:
            analysis_minute = 0

        analysis_date = datetime(
            analysis_year,
            analysis_month,
            analysis_day,
            analysis_hour,
            analysis_minute,
        )
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        liushi_info = TimingAnalysis.calculate_liushi(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liushi_result = TimingEffectsAnalysis.analyze_liushi_effects(
            birth_context.birth_pillars,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
            liushi_info=liushi_info,
            original_element_counts=birth_context.original_element_counts,
        )

        liushi_info = liushi_result["liushi_info"]
        detailed_analysis = liushi_result["detailed_analysis"]
        element_effects = liushi_result["element_effects"]
        summary = liushi_result["enhanced_summary"]
        snapshot_text = _build_liushi_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            analysis_date=analysis_date,
            analysis_calendar_context=analysis_calendar_context,
            liushi_info=liushi_info,
            detailed_analysis={
                "stem_relation": detailed_analysis["shishen_analysis"][
                    "stem_relation"
                ],
                "branch_relations": detailed_analysis["branch_relations"],
                "fortune_analysis": detailed_analysis["fortune_analysis"],
                "suggestions": detailed_analysis["suggestions"],
            },
            element_effects=element_effects,
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="liushi_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        return {
            "analysis_type": "流时专项分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "analysis_datetime": analysis_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
            },
            "liushi_info": {
                "pillar": liushi_info["pillar"],
                "stem": liushi_info["stem"],
                "branch": liushi_info["branch"],
                "element": liushi_info["element"],
                "nayin": liushi_info["nayin"],
                "hour": liushi_info["hour"],
                "analysis_datetime": liushi_info["analysis_datetime"],
                "shichen": liushi_info["shichen"],
            },
            "detailed_analysis": {
                "stem_relation": detailed_analysis["shishen_analysis"][
                    "stem_relation"
                ],
                "branch_relations": detailed_analysis["branch_relations"],
                "fortune_analysis": detailed_analysis["fortune_analysis"],
                "suggestions": detailed_analysis["suggestions"],
            },
            "element_effects": _serialize_element_effects(element_effects),
            "life_dimensions": _compute_life_dimensions_for_moment(
                birth_context, analysis_date
            ),
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

    except Exception as e:
        return handle_calculation_error(e, "流时分析计算")


def calculate_jieqi_timeline_analysis(
    person: PersonInfo,
    target_year: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    节气节点时间轴分析 - 输出全年 24 节气节点的流月/流日切换信息
    """
    try:
        birth_context = _build_birth_computation_context(person)
        normalized_birth_time = birth_context.normalized_birth_time
        birth_date = normalized_birth_time.corrected_datetime

        if target_year is None:
            target_year = datetime.now().year

        jieqi_timeline = _enrich_jieqi_timeline(
            birth_context,
            target_year=target_year,
        )

        target_year_jieqi = get_jieqi_year_grid(
            target_year, normalized_birth_time.timezone
        )
        summary = (
            f"{target_year}年共生成{len(jieqi_timeline)}个节气节点时间轴，"
            f"覆盖全年流月与流日切换。"
        )
        snapshot_text = _build_jieqi_timeline_snapshot_text(
            person_name=person.name,
            birth_datetime=normalized_birth_time.input_datetime,
            normalized_birth_datetime=birth_date,
            timezone_name=normalized_birth_time.timezone,
            target_year=target_year,
            target_year_jieqi=target_year_jieqi,
            jieqi_timeline=jieqi_timeline,
            summary=summary,
        )
        snapshot_export = _build_snapshot_export(
            technique="jieqi_timeline_analysis",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )

        return {
            "analysis_type": "节气节点时间轴分析",
            "personal_info": {
                "name": person.name,
                "target_year": target_year,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_context.birth_calendar_context,
            "target_year_jieqi": target_year_jieqi,
            "jieqi_timeline": jieqi_timeline,
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

    except Exception as e:
        return handle_calculation_error(e, "节气时间轴分析计算")
