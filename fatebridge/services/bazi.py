"""
Standalone BaZi tool surfaces for FateBridge.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.export_parser import parse_export_content
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.timing import (
    calculate_dayun_analysis,
    calculate_liunian_analysis,
    calculate_liuri_analysis,
    calculate_liuyue_analysis,
)
from fatebridge.utils.data import (
    BRANCH_HIDDEN_STEMS,
    EARTHLY_BRANCHES,
    HEAVENLY_STEMS,
    get_nayin,
    get_ten_god,
)
from fatebridge.utils.helpers import (
    PersonInfo,
    format_birth_datetime_display,
    handle_calculation_error,
    normalize_birth_time,
)

PILLAR_LABELS = {
    "year": "年柱",
    "month": "月柱",
    "day": "日柱",
    "hour": "时柱",
    "taiyuan": "胎元",
    "minggong": "命宫",
    "shengong": "身宫",
}

MONTH_HOUR_ORDER = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

PEACH_BLOSSOM_TARGETS = (
    (("申", "子", "辰"), "酉"),
    (("寅", "午", "戌"), "卯"),
    (("亥", "卯", "未"), "子"),
    (("巳", "酉", "丑"), "午"),
)

TRAVEL_HORSE_TARGETS = (
    (("申", "子", "辰"), "寅"),
    (("寅", "午", "戌"), "申"),
    (("亥", "卯", "未"), "巳"),
    (("巳", "酉", "丑"), "亥"),
)

HUA_GAI_TARGETS = (
    (("申", "子", "辰"), "辰"),
    (("寅", "午", "戌"), "戌"),
    (("亥", "卯", "未"), "未"),
    (("巳", "酉", "丑"), "丑"),
)

TIAN_YI_TARGETS = {
    "甲": ["丑", "未"],
    "戊": ["丑", "未"],
    "庚": ["丑", "未"],
    "乙": ["子", "申"],
    "己": ["子", "申"],
    "丙": ["亥", "酉"],
    "丁": ["亥", "酉"],
    "辛": ["寅", "午"],
    "壬": ["卯", "巳"],
    "癸": ["卯", "巳"],
}

WEN_CHANG_TARGETS = {
    "甲": "巳",
    "乙": "午",
    "丙": "申",
    "丁": "酉",
    "戊": "申",
    "己": "酉",
    "庚": "亥",
    "辛": "子",
    "壬": "寅",
    "癸": "卯",
}


def _resolve_analysis_date(
    analysis_year: Optional[int],
    analysis_month: Optional[int],
    analysis_day: Optional[int],
) -> datetime:
    now = datetime.now()
    return datetime(
        analysis_year or now.year,
        analysis_month or now.month,
        analysis_day or now.day,
    )


def _calculate_age(birth_datetime: datetime, analysis_date: datetime) -> int:
    age = analysis_date.year - birth_datetime.year
    if (analysis_date.month, analysis_date.day) < (birth_datetime.month, birth_datetime.day):
        age -= 1
    return max(age, 0)


def _cycle_stem(stem: str, steps: int) -> str:
    return HEAVENLY_STEMS[(HEAVENLY_STEMS.index(stem) + steps) % len(HEAVENLY_STEMS)]


def _branch_offset(start_branch: str, end_branch: str) -> int:
    return (MONTH_HOUR_ORDER.index(end_branch) - MONTH_HOUR_ORDER.index(start_branch)) % len(
        MONTH_HOUR_ORDER
    )


def _build_origin_payload(
    *,
    label_key: str,
    stem: str,
    branch: str,
    day_stem: str,
) -> Dict[str, Any]:
    return {
        "label": PILLAR_LABELS[label_key],
        "stem": stem,
        "branch": branch,
        "pillar": f"{stem}{branch}",
        "nayin": get_nayin(stem, branch),
        "hidden_stems": BRANCH_HIDDEN_STEMS.get(branch, []),
        "ten_god": get_ten_god(day_stem, stem).value,
    }


def _build_three_origins(pillars: Dict[str, Tuple[str, str]]) -> Dict[str, Dict[str, Any]]:
    month_stem, month_branch = pillars["month"]
    day_stem = pillars["day"][0]
    hour_branch = pillars["hour"][1]

    taiyuan = _build_origin_payload(
        label_key="taiyuan",
        stem=_cycle_stem(month_stem, 1),
        branch=EARTHLY_BRANCHES[(EARTHLY_BRANCHES.index(month_branch) + 3) % len(EARTHLY_BRANCHES)],
        day_stem=day_stem,
    )

    month_order = MONTH_HOUR_ORDER.index(month_branch) + 1
    hour_order = MONTH_HOUR_ORDER.index(hour_branch) + 1

    ming_order = 14 - (month_order + hour_order)
    while ming_order <= 0:
        ming_order += 12
    ming_branch = MONTH_HOUR_ORDER[ming_order - 1]
    ming_stem = _cycle_stem(month_stem, _branch_offset(month_branch, ming_branch))

    shen_order = month_order + hour_order - 2
    while shen_order > 12:
        shen_order -= 12
    while shen_order <= 0:
        shen_order += 12
    shen_branch = MONTH_HOUR_ORDER[shen_order - 1]
    shen_stem = _cycle_stem(month_stem, _branch_offset(month_branch, shen_branch))

    return {
        "taiyuan": taiyuan,
        "minggong": _build_origin_payload(
            label_key="minggong",
            stem=ming_stem,
            branch=ming_branch,
            day_stem=day_stem,
        ),
        "shengong": _build_origin_payload(
            label_key="shengong",
            stem=shen_stem,
            branch=shen_branch,
            day_stem=day_stem,
        ),
    }


def _find_group_target(source_branch: str, mappings: tuple[tuple[tuple[str, ...], str], ...]) -> Optional[str]:
    for group, target in mappings:
        if source_branch in group:
            return target
    return None


def _collect_branch_hits(
    target_branches: List[str],
    positions: Dict[str, str],
) -> List[str]:
    hits: List[str] = []
    for key, branch in positions.items():
        if branch in target_branches:
            hits.append(f"{PILLAR_LABELS[key]}{branch}")
    return hits


def _build_shensha_entries(
    *,
    pillars: Dict[str, Tuple[str, str]],
    three_origins: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    positions = {
        "year": pillars["year"][1],
        "month": pillars["month"][1],
        "day": pillars["day"][1],
        "hour": pillars["hour"][1],
        "taiyuan": three_origins["taiyuan"]["branch"],
        "minggong": three_origins["minggong"]["branch"],
        "shengong": three_origins["shengong"]["branch"],
    }
    day_stem = pillars["day"][0]
    year_branch = pillars["year"][1]
    day_branch = pillars["day"][1]

    entries: List[Dict[str, str]] = []
    for key, (stem, branch) in pillars.items():
        entries.append(
            {
                "label": f"{PILLAR_LABELS[key]}纳音",
                "value": get_nayin(stem, branch),
            }
        )
    for origin_key, origin in three_origins.items():
        entries.append(
            {
                "label": f"{PILLAR_LABELS[origin_key]}纳音",
                "value": origin["nayin"],
            }
        )

    year_peach = _find_group_target(year_branch, PEACH_BLOSSOM_TARGETS)
    day_peach = _find_group_target(day_branch, PEACH_BLOSSOM_TARGETS)
    year_horse = _find_group_target(year_branch, TRAVEL_HORSE_TARGETS)
    day_horse = _find_group_target(day_branch, TRAVEL_HORSE_TARGETS)
    year_huagai = _find_group_target(year_branch, HUA_GAI_TARGETS)
    day_huagai = _find_group_target(day_branch, HUA_GAI_TARGETS)

    rule_rows = [
        ("年支桃花", [year_peach] if year_peach else []),
        ("日支桃花", [day_peach] if day_peach else []),
        ("年支驿马", [year_horse] if year_horse else []),
        ("日支驿马", [day_horse] if day_horse else []),
        ("年支华盖", [year_huagai] if year_huagai else []),
        ("日支华盖", [day_huagai] if day_huagai else []),
        ("日主天乙贵人", TIAN_YI_TARGETS.get(day_stem, [])),
        ("日主文昌", [WEN_CHANG_TARGETS[day_stem]] if day_stem in WEN_CHANG_TARGETS else []),
    ]

    for label, targets in rule_rows:
        hits = _collect_branch_hits(targets, positions) if targets else []
        entries.append(
            {
                "label": label,
                "value": "、".join(hits) if hits else "未触发",
            }
        )

    return entries


def _build_timing_overview(
    *,
    person: PersonInfo,
    normalized_birth_datetime: datetime,
    analysis_date: datetime,
) -> Dict[str, Any]:
    analysis_age = _calculate_age(normalized_birth_datetime, analysis_date)
    dayun_result = calculate_dayun_analysis(person, analysis_age)
    liunian_result = calculate_liunian_analysis(person, analysis_date.year)
    liuyue_result = calculate_liuyue_analysis(
        person,
        analysis_year=analysis_date.year,
        analysis_month=analysis_date.month,
        analysis_day=analysis_date.day,
    )
    liuri_result = calculate_liuri_analysis(
        person,
        analysis_year=analysis_date.year,
        analysis_month=analysis_date.month,
        analysis_day=analysis_date.day,
    )

    dayun_payload: Dict[str, Any]
    if "dayun_info" in dayun_result:
        dayun_payload = {
            "pillar": dayun_result["dayun_info"]["current_dayun"],
            "start_age": dayun_result["dayun_info"]["start_age"],
            "dayun_age": dayun_result["dayun_info"]["dayun_age"],
            "years_in_period": dayun_result["dayun_info"]["years_in_period"],
            "summary": dayun_result.get("summary", ""),
        }
    else:
        dayun_payload = {
            "pillar": None,
            "summary": dayun_result.get("error", "大运信息不可用"),
        }

    liuyue_info = liuyue_result["liuyue_info"]
    liuri_info = liuri_result["liuri_info"]
    return {
        "analysis_date": analysis_date.strftime("%Y-%m-%d"),
        "dayun": dayun_payload,
        "liunian": {
            "pillar": liunian_result["liunian_info"]["pillar"],
            "summary": liunian_result.get("summary", ""),
        },
        "liuyue": {
            "pillar": liuyue_info["pillar"],
            "summary": liuyue_result.get("summary", ""),
            "start_term": liuyue_info["solar_term_window"]["start_term"]["name"],
            "end_term": liuyue_info["solar_term_window"]["next_term"]["name"],
        },
        "liuri": {
            "pillar": liuri_info["pillar"],
            "summary": liuri_result.get("summary", ""),
            "weekday": liuri_info["weekday"],
        },
        "current_jieqi": liuyue_result["analysis_calendar"]["analysis_date_context"]["current_solar_term"]["name"],
        "next_jieqi": liuyue_result["analysis_calendar"]["analysis_date_context"]["next_solar_term"]["name"],
    }


def _format_pillar_line(label: str, stem: str, branch: str, day_stem: str) -> str:
    hidden_stems = "、".join(BRANCH_HIDDEN_STEMS.get(branch, [])) or "无"
    return (
        f"{label}：{stem}{branch}；"
        f"纳音：{get_nayin(stem, branch)}；"
        f"十神：{get_ten_god(day_stem, stem).value}；"
        f"藏干：{hidden_stems}"
    )


def _format_origin_line(origin: Dict[str, Any]) -> str:
    hidden_stems = "、".join(origin.get("hidden_stems") or []) or "无"
    return (
        f"{origin['label']}：{origin['pillar']}；"
        f"纳音：{origin['nayin']}；"
        f"十神：{origin['ten_god']}；"
        f"藏干：{hidden_stems}"
    )


def _build_snapshot_text(
    *,
    person: PersonInfo,
    normalized_birth_datetime: datetime,
    input_birth_datetime: datetime,
    timezone_name: str,
    longitude: Optional[float],
    applied_true_solar: bool,
    calendar_context: Dict[str, Any],
    pillars: Dict[str, Tuple[str, str]],
    three_origins: Dict[str, Dict[str, Any]],
    shensha_entries: List[Dict[str, str]],
    timing_overview: Dict[str, Any],
) -> str:
    include_minutes = (
        person.birth_minute != 0
        or applied_true_solar
        or input_birth_datetime.minute != 0
        or normalized_birth_datetime.minute != 0
    )
    day_stem = pillars["day"][0]
    lunar_calendar = calendar_context.get("lunar_calendar") or {}

    sections = [
        (
            "起盘信息",
            "\n".join(
                [
                    f"姓名：{person.name or '未提供'}",
                    f"性别：{person.gender or '未知'}",
                    f"出生时间：{format_birth_datetime_display(input_birth_datetime, include_minutes=include_minutes)}",
                    f"校正时间：{format_birth_datetime_display(normalized_birth_datetime, include_minutes=True)}",
                    f"出生地：{person.birth_place or '未提供'}",
                    f"时区：{timezone_name}",
                    f"经度：{longitude if longitude is not None else '未提供'}",
                    f"时间算法：{'真太阳时' if applied_true_solar else '直接时间'}",
                    f"农历：{lunar_calendar.get('display', '未知')}",
                    f"当前节气：{calendar_context['current_solar_term']['name']}",
                    f"下个节气：{calendar_context['next_solar_term']['name']}",
                ]
            ).strip(),
        ),
        (
            "四柱与三元",
            "\n".join(
                [
                    _format_pillar_line("年柱", *pillars["year"], day_stem),
                    _format_pillar_line("月柱", *pillars["month"], day_stem),
                    _format_pillar_line("日柱", *pillars["day"], day_stem),
                    _format_pillar_line("时柱", *pillars["hour"], day_stem),
                    _format_origin_line(three_origins["taiyuan"]),
                    _format_origin_line(three_origins["minggong"]),
                    _format_origin_line(three_origins["shengong"]),
                ]
            ).strip(),
        ),
        (
            "流年行运概略",
            "\n".join(
                [
                    f"分析日期：{timing_overview['analysis_date']}",
                    (
                        "当前大运："
                        f"{timing_overview['dayun']['pillar'] or '未进入稳定大运'}；"
                        f"{timing_overview['dayun']['summary']}"
                    ),
                    f"流年：{timing_overview['liunian']['pillar']}；{timing_overview['liunian']['summary']}",
                    (
                        f"流月：{timing_overview['liuyue']['pillar']}；"
                        f"节气窗口：{timing_overview['liuyue']['start_term']}→{timing_overview['liuyue']['end_term']}；"
                        f"{timing_overview['liuyue']['summary']}"
                    ),
                    (
                        f"流日：{timing_overview['liuri']['pillar']}；"
                        f"星期：{timing_overview['liuri']['weekday']}；"
                        f"{timing_overview['liuri']['summary']}"
                    ),
                    f"当下节气：{timing_overview['current_jieqi']}",
                    f"后续节气：{timing_overview['next_jieqi']}",
                ]
            ).strip(),
        ),
        (
            "神煞（四柱与三元）",
            "\n".join(
                f"{item['label']}：{item['value']}" for item in shensha_entries
            ).strip(),
        ),
    ]

    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body:
            blocks.append(body)
        blocks.append("")
    return "\n".join(blocks).strip()


def _build_base_bazi_payload(
    *,
    person: PersonInfo,
    analysis_date: datetime,
) -> Dict[str, Any]:
    normalized_birth_time = normalize_birth_time(person)
    input_birth_datetime = normalized_birth_time.input_datetime
    normalized_birth_datetime = normalized_birth_time.corrected_datetime
    pillars = BaZiCalendar.get_four_pillars(
        normalized_birth_datetime,
        timezone_name=normalized_birth_time.timezone,
    )
    calendar_context = build_calendar_context(
        normalized_birth_datetime,
        timezone_name=normalized_birth_time.timezone,
        pillars=pillars,
    )
    base_analysis = calculate_destiny_analysis(person)
    three_origins = _build_three_origins(pillars)
    shensha_entries = _build_shensha_entries(
        pillars=pillars,
        three_origins=three_origins,
    )
    timing_overview = _build_timing_overview(
        person=person,
        normalized_birth_datetime=normalized_birth_datetime,
        analysis_date=analysis_date,
    )
    snapshot_text = _build_snapshot_text(
        person=person,
        normalized_birth_datetime=normalized_birth_datetime,
        input_birth_datetime=input_birth_datetime,
        timezone_name=normalized_birth_time.timezone,
        longitude=normalized_birth_time.longitude,
        applied_true_solar=normalized_birth_time.applied,
        calendar_context=calendar_context,
        pillars=pillars,
        three_origins=three_origins,
        shensha_entries=shensha_entries,
        timing_overview=timing_overview,
    )
    return {
        "input_birth_datetime": input_birth_datetime,
        "normalized_birth_datetime": normalized_birth_datetime,
        "normalized_birth_time": normalized_birth_time,
        "calendar_context": calendar_context,
        "base_analysis": base_analysis,
        "three_origins": three_origins,
        "shensha_entries": shensha_entries,
        "timing_overview": timing_overview,
        "snapshot_text": snapshot_text,
    }


def calculate_bazi_birth(
    person: PersonInfo,
    *,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        analysis_date = _resolve_analysis_date(analysis_year, analysis_month, analysis_day)
        payload = _build_base_bazi_payload(person=person, analysis_date=analysis_date)
        base_analysis = payload["base_analysis"]
        snapshot_text = payload["snapshot_text"]
        snapshot_export = parse_export_content(
            technique="bazi",
            content=snapshot_text,
            selected_sections=selected_sections,
        )

        return {
            "analysis_type": "八字命盘",
            "bazi_birth": {
                "engine": "fatebridge-offline",
                "time_algorithm": "真太阳时"
                if payload["normalized_birth_time"].applied
                else "直接时间",
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "person_info": base_analysis["person_info"],
                "four_pillars": base_analysis["four_pillars"],
                "three_origins": payload["three_origins"],
                "day_master": base_analysis["day_master"],
                "element_distribution": base_analysis["element_distribution"],
                "favorable_elements": base_analysis["favorable_elements"],
                "structure_profile": base_analysis["structure_profile"],
                "ten_gods": base_analysis["ten_gods"],
                "patterns": base_analysis["patterns"],
                "calendar_context": base_analysis["calendar_context"],
                "timing_overview": payload["timing_overview"],
                "shensha": payload["shensha_entries"],
            },
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "八字命盘")


def calculate_bazi_direct(
    person: PersonInfo,
    *,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        analysis_date = _resolve_analysis_date(analysis_year, analysis_month, analysis_day)
        payload = _build_base_bazi_payload(person=person, analysis_date=analysis_date)
        base_analysis = payload["base_analysis"]
        snapshot_text = payload["snapshot_text"]
        snapshot_export = parse_export_content(
            technique="bazi",
            content=snapshot_text,
            selected_sections=selected_sections,
        )

        return {
            "analysis_type": "八字直断",
            "bazi_direct": {
                "engine": "fatebridge-offline",
                "time_algorithm": "真太阳时"
                if payload["normalized_birth_time"].applied
                else "直接时间",
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "person_info": base_analysis["person_info"],
                "four_pillars": base_analysis["four_pillars"],
                "three_origins": payload["three_origins"],
                "timing_overview": payload["timing_overview"],
                "shensha": payload["shensha_entries"],
                "calendar_context": base_analysis["calendar_context"],
                "structure_profile": base_analysis["structure_profile"],
                "patterns": base_analysis["patterns"],
            },
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "八字直断")
