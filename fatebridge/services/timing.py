"""
FateBridge Timing Services
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging

from fatebridge.core.almanac import build_calendar_context, get_jieqi_year_grid
from fatebridge.core.export_parser import parse_export_content
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    PersonInfo,
    handle_calculation_error,
    create_pillar_dict,
    get_current_analysis_date,
    format_json_response,
    normalize_birth_time,
)
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.timing import TimingAnalysis
from fatebridge.analysis.timing_effects import TimingEffectsAnalysis

logger = logging.getLogger(__name__)


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
    ad: int,
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
        f"time_alg：{time_alg}",
        f"ad：{ad}",
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
        f"分析日期：{analysis_date.strftime('%Y-%m-%d')}",
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
        f"分析日期：{analysis_date.strftime('%Y-%m-%d')}",
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
        f"分析日期：{analysis_date.strftime('%Y-%m-%d')}",
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
        timezone_name = zone or DEFAULT_BIRTH_TIMEZONE
        analysis_datetime = _parse_calendar_datetime(date, time)
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
            time_alg=time_alg,
            ad=ad,
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

        return {
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
                "time_alg": time_alg,
                "ad": ad,
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
    except Exception as exc:
        return handle_calculation_error(exc, "农历换算")

def calculate_comprehensive_timing(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_age: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    计算时运分析，包括大运、流年、流月的影响分析
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        input_birth_datetime = normalized_birth_time.input_datetime
        birth_date = normalized_birth_time.corrected_datetime

        # 计算四柱（使用原始格式）
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        # 设置分析日期
        analysis_year, analysis_month = get_current_analysis_date(
            analysis_year, analysis_month
        )

        analysis_date = datetime(analysis_year, analysis_month, 1)
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        analysis_year_jieqi = get_jieqi_year_grid(
            analysis_year, normalized_birth_time.timezone
        )
        liuyue_timeline = TimingAnalysis.calculate_liuyue_timeline(
            analysis_year, timezone_name=normalized_birth_time.timezone
        )
        for item in liuyue_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_effect = TimingEffectsAnalysis.analyze_liuyue_effects(
                birth_pillars,
                anchor.year,
                anchor.month,
                target_day=anchor.day,
                timezone_name=normalized_birth_time.timezone,
                target_date=anchor,
            )
            item["overall_effect"] = liuyue_effect["element_effects"]["overall_effect"]
            item["summary"] = liuyue_effect["enhanced_summary"]
        jieqi_timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
            analysis_year, timezone_name=normalized_birth_time.timezone
        )
        for item in jieqi_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_pillar = item["liuyue"]
            liuri_pillar = item["liuri"]
            node_effect = TimingEffectsAnalysis.analyze_element_strength_changes(
                birth_pillars,
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
            )
            liuri_effect = TimingEffectsAnalysis.analyze_liuri_effects(
                birth_pillars,
                anchor,
                timezone_name=normalized_birth_time.timezone,
            )
            item["overall_effect"] = node_effect["overall_effect"]
            item["liuri_summary"] = liuri_effect["enhanced_summary"]
            item["summary"] = (
                f"{item['jieqi']['name']}节点，流月{liuyue_pillar['pillar']}，"
                f"流日{liuri_pillar['pillar']}，{node_effect['overall_effect']}"
            )

        # 计算当前年龄
        if analysis_age is None:
            current_age = analysis_date.year - birth_date.year
            if analysis_date.month < birth_date.month or (
                analysis_date.month == birth_date.month
                and analysis_date.day < birth_date.day
            ):
                current_age -= 1
        else:
            current_age = analysis_age

        # 进行综合时运分析
        timing_result = TimingEffectsAnalysis.comprehensive_timing_analysis(
            birth_pillars,
            birth_date,
            person.gender,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        if analysis_age is not None:
            timing_result["dayun_analysis"] = TimingEffectsAnalysis.analyze_dayun_effects(
                birth_pillars,
                birth_date,
                person.gender,
                analysis_age,
                timezone_name=normalized_birth_time.timezone,
            )
            combined_timing_pillars: Dict[str, Dict[str, str]] = {}
            if "dayun_info" in timing_result["dayun_analysis"]:
                combined_timing_pillars["dayun"] = {
                    "stem": timing_result["dayun_analysis"]["dayun_info"]["stem"],
                    "branch": timing_result["dayun_analysis"]["dayun_info"]["branch"],
                }
            combined_timing_pillars["liunian"] = {
                "stem": timing_result["liunian_analysis"]["liunian_info"]["stem"],
                "branch": timing_result["liunian_analysis"]["liunian_info"]["branch"],
            }
            combined_timing_pillars["liuyue"] = {
                "stem": timing_result["liuyue_analysis"]["liuyue_info"]["stem"],
                "branch": timing_result["liuyue_analysis"]["liuyue_info"]["branch"],
            }
            combined_timing_pillars["liuri"] = {
                "stem": timing_result["liuri_analysis"]["liuri_info"]["stem"],
                "branch": timing_result["liuri_analysis"]["liuri_info"]["branch"],
            }
            timing_result["combined_effects"] = (
                TimingEffectsAnalysis.analyze_element_strength_changes(
                    birth_pillars,
                    combined_timing_pillars,
                )
            )
            timing_result["comprehensive_summary"] = (
                TimingEffectsAnalysis._generate_comprehensive_summary(
                    timing_result["dayun_analysis"],
                    timing_result["liunian_analysis"],
                    timing_result["liuyue_analysis"],
                    timing_result["liuri_analysis"],
                    timing_result["combined_effects"],
                )
            )

        # 构建最终结果结构
        result = {
            "analysis_type": "综合时运分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": input_birth_datetime.strftime("%Y-%m-%d %H:%M"),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "gender": person.gender,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "current_age": current_age,
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "birth_pillars": create_pillar_dict(birth_pillars),
            "calendar_context": birth_calendar_context,
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
            result["dayun_analysis"] = {
                "current_dayun": dayun_info["pillar"],
                "stem": dayun_info["stem"],
                "branch": dayun_info["branch"],
                "start_age": age_info["start_age"],
                "dayun_age": age_info["dayun_age"],
                "years_in_period": age_info["years_in_period"],
                "summary": dayun_analysis["summary"],
            }
        else:
            result["dayun_analysis"] = {
                "error": dayun_analysis.get("message", "大运信息不可用")
            }

        # 流年分析
        liunian_analysis = timing_result["liunian_analysis"]
        liunian_info = liunian_analysis["liunian_info"]
        result["liunian_analysis"] = {
            "pillar": liunian_info["pillar"],
            "stem": liunian_info["stem"],
            "branch": liunian_info["branch"],
            "summary": liunian_analysis["summary"],
        }

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

        # 综合影响
        combined_effects = timing_result["combined_effects"]
        result["combined_effects"] = {
            "overall_effect": combined_effects["overall_effect"],
            "element_changes": {},
        }

        # 只包含有变化的五行
        element_changes = combined_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["combined_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
                }

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
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_pillars,
            birth_date,
            person.gender,
            analysis_age,
            timezone_name=normalized_birth_time.timezone,
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
            "calendar_context": birth_calendar_context,
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

            result["element_effects"] = {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            }

            # 只包含有变化的五行
            element_changes = element_effects["element_changes"]
            for element, change_info in element_changes.items():
                if change_info["change"] != 0:
                    result["element_effects"]["element_changes"][element] = {
                        "original": change_info["original"],
                        "new": change_info["new"],
                        "change": change_info["change"],
                        "change_type": change_info["change_type"],
                    }

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
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        liunian_result = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_pillars, target_year
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
            "calendar_context": birth_calendar_context,
            "target_year_jieqi": get_jieqi_year_grid(
                target_year, normalized_birth_time.timezone
            ),
            "liunian_info": {
                "pillar": liunian_info["pillar"],
                "stem": liunian_info["stem"],
                "branch": liunian_info["branch"],
                "element": liunian_info["element"],
            },
            "element_effects": {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            },
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

        element_changes = element_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["element_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
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
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流月分析工具 - 专门分析指定日期所在节令月的影响
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = 1

        analysis_date = datetime(analysis_year, analysis_month, analysis_day)
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuyue_result = TimingEffectsAnalysis.analyze_liuyue_comprehensive(
            birth_pillars,
            analysis_year,
            analysis_month,
            include_dayun=False,
            include_liunian=True,
            target_day=analysis_day,
            timezone_name=normalized_birth_time.timezone,
            target_date=analysis_date,
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
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
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
            "element_effects": {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            },
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

        for element, change_info in element_effects["element_changes"].items():
            if change_info["change"] != 0:
                result["element_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
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
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    流日分析工具 - 专门分析指定日期的流日影响
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = now.day

        analysis_date = datetime(analysis_year, analysis_month, analysis_day)
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuri_result = TimingEffectsAnalysis.analyze_liuri_effects(
            birth_pillars,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
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
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
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
            "element_effects": {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            },
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

        element_changes = element_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["element_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
                }

        return result

    except Exception as e:
        return handle_calculation_error(e, "流日分析计算")


def calculate_jieqi_timeline_analysis(
    person: PersonInfo,
    target_year: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict:
    """
    节气节点时间轴分析 - 输出全年 24 节气节点的流月/流日切换信息
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        if target_year is None:
            target_year = datetime.now().year

        jieqi_timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
            target_year,
            timezone_name=normalized_birth_time.timezone,
        )

        for item in jieqi_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_pillar = item["liuyue"]
            liuri_pillar = item["liuri"]
            node_effect = TimingEffectsAnalysis.analyze_element_strength_changes(
                birth_pillars,
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
            )
            liuri_effect = TimingEffectsAnalysis.analyze_liuri_effects(
                birth_pillars,
                anchor,
                timezone_name=normalized_birth_time.timezone,
            )
            item["overall_effect"] = node_effect["overall_effect"]
            item["liuri_summary"] = liuri_effect["enhanced_summary"]
            item["summary"] = (
                f"{item['jieqi']['name']}节点，流月{liuyue_pillar['pillar']}，"
                f"流日{liuri_pillar['pillar']}，{node_effect['overall_effect']}"
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
            "calendar_context": birth_calendar_context,
            "target_year_jieqi": target_year_jieqi,
            "jieqi_timeline": jieqi_timeline,
            "summary": summary,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }

    except Exception as e:
        return handle_calculation_error(e, "节气时间轴分析计算")
