"""
FateBridge astrology services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fatebridge.core.astrology import (
    build_astro_birth_info,
    build_core_chart_payload,
    build_midpoint_payload,
    build_relative_payload,
)
from fatebridge.core.export_parser import parse_export_content
from fatebridge.utils.helpers import handle_calculation_error


SUPPORTED_CHART_VARIANTS = {
    "chart",
    "chart13",
    "hellen_chart",
    "guolao_chart",
    "india_chart",
}

PLANET_LABELS_ZH = {
    "Sun": "太阳",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
    "North Node": "北交点",
}

ASPECT_LABELS_ZH = {
    "conjunction": "合相",
    "sextile": "六合",
    "square": "刑相",
    "trine": "拱相",
    "opposition": "冲相",
}

ELEMENT_LABELS_ZH = {
    "Fire": "火",
    "Earth": "土",
    "Air": "风",
    "Water": "水",
}

MODALITY_LABELS_ZH = {
    "Cardinal": "基本",
    "Fixed": "固定",
    "Mutable": "变动",
}

CORE_CHART_EXPORT_TECHNIQUES = {
    "chart": "astrochart",
    "chart13": "astrochart",
    "hellen_chart": "astrochart_like",
    "india_chart": "indiachart",
    "guolao_chart": "guolao",
}


def _format_degree(value: Any) -> str:
    try:
        return f"{float(value):.2f}°"
    except (TypeError, ValueError):
        return "—"


def _render_snapshot_text(sections: List[tuple[str, str]]) -> str:
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body.strip():
            blocks.append(body)
        blocks.append("")
    return "\n".join(blocks).strip()


def _build_balance_line(balance: Dict[str, Any], labels: Dict[str, str]) -> str:
    ordered_keys = [key for key in labels if key in balance]
    if not ordered_keys:
        return "无"
    return "，".join(
        f"{labels[key]} {balance.get(key, 0)}" for key in ordered_keys
    )


def _build_house_lines(houses: List[Dict[str, Any]]) -> str:
    return "\n".join(
        f"第{item['house']}宫：{item['sign_zh']} {_format_degree(item['cusp_longitude'])}"
        for item in houses
    ).strip() or "无"


def _build_angle_lines(angles: Dict[str, Any]) -> str:
    ascendant = angles.get("ascendant", {})
    midheaven = angles.get("midheaven", {})
    return "\n".join(
        [
            f"Asc：{ascendant.get('sign_zh', '未知')} {_format_degree(ascendant.get('longitude'))}",
            f"MC：{midheaven.get('sign_zh', '未知')} {_format_degree(midheaven.get('longitude'))}",
        ]
    ).strip()


def _build_planet_lines(planets: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in planets:
        extras: List[str] = []
        if "sector13" in item:
            extras.append(f"13扇区 {item['sector13']}")
        if item.get("nakshatra"):
            extras.append(f"宿 {item['nakshatra']}")
        if item.get("su28"):
            extras.append(f"二十八宿 {item['su28']}")
        extras_text = f"，{'，'.join(extras)}" if extras else ""
        lines.append(
            f"{PLANET_LABELS_ZH.get(item['id'], item['id'])}："
            f"{item.get('sign_zh', '未知')} {_format_degree(item.get('degree_in_sign'))}，"
            f"第{item.get('house', '—')}宫，黄纬 {_format_degree(item.get('latitude'))}"
            f"{extras_text}"
        )
    return "\n".join(lines).strip() or "无"


def _build_aspect_lines(aspects: List[Dict[str, Any]]) -> str:
    if not aspects:
        return "无"
    return "\n".join(
        f"{PLANET_LABELS_ZH.get(item['planet_a'], item['planet_a'])}"
        f" 与 {PLANET_LABELS_ZH.get(item['planet_b'], item['planet_b'])}"
        f" 形成 {ASPECT_LABELS_ZH.get(item['aspect'], item['aspect'])}，"
        f"容许度 {_format_degree(item['orb'])}"
        for item in aspects
    )


def _build_standard_chart_snapshot_sections(
    payload: Dict[str, Any], *, chart_variant: str
) -> List[tuple[str, str]]:
    person_info = payload.get("person_info", {})
    chart_profile = payload.get("chart_profile", {})
    info_lines = [
        f"姓名：{person_info.get('name', '未提供')}",
        f"出生地：{person_info.get('birth_place', '未提供')}",
        f"出生时间：{str(person_info.get('birth_datetime', '未提供')).replace('T', ' ')}",
        f"时区：{person_info.get('birth_timezone', '未提供')}",
        f"经纬度：{_format_degree(person_info.get('birth_longitude'))} / {_format_degree(person_info.get('birth_latitude'))}",
        f"盘型：{chart_profile.get('chart_type', chart_variant)}",
        f"黄道：{chart_profile.get('zodiac_label_zh', chart_profile.get('zodiac', '未知'))}",
        f"宫制：{chart_profile.get('house_system_label_zh', chart_profile.get('house_system', '未知'))}",
        f"精度层：{chart_profile.get('engine_precision', '未知')}",
    ]

    detail_lines = [
        f"元素分布：{_build_balance_line(payload.get('element_balance', {}), ELEMENT_LABELS_ZH)}",
        f"模式分布：{_build_balance_line(payload.get('modality_balance', {}), MODALITY_LABELS_ZH)}",
    ]

    if chart_variant == "chart13":
        detail_lines.append(
            f"13扇区数量：{len(payload.get('thirteen_sectors', []))}"
        )

    hellenistic = payload.get("hellenistic", {})
    if chart_variant == "hellen_chart":
        detail_lines.extend(
            [
                f"昼夜属性：{hellenistic.get('sect', '未知')}",
                f"上升主星：{PLANET_LABELS_ZH.get(hellenistic.get('ascendant_ruler', ''), hellenistic.get('ascendant_ruler', '未知'))}",
                f"角宫星体：{', '.join(PLANET_LABELS_ZH.get(item, item) for item in hellenistic.get('angular_planets', [])) or '无'}",
            ]
        )

    india = payload.get("india", {})
    if chart_variant == "india_chart":
        detail_lines.extend(
            [
                f"Ayanamsha：{_format_degree(india.get('ayanamsha'))}",
                f"上升宿：{india.get('rising_nakshatra', '未知')}",
                f"月宿：{india.get('moon_nakshatra', '未知')}",
            ]
        )

    greek_lines = ["无"]
    lot_of_fortune = hellenistic.get("lot_of_fortune")
    if isinstance(lot_of_fortune, dict):
        greek_lines = [
            f"福点：{lot_of_fortune.get('sign_zh', '未知')} {_format_degree(lot_of_fortune.get('degree_in_sign'))}，第{lot_of_fortune.get('house', '—')}宫"
        ]

    summary_lines = payload.get("summary") or ["无"]

    return [
        ("起盘信息", "\n".join(info_lines).strip()),
        ("宫位宫头", _build_house_lines(payload.get("houses", []))),
        ("星与虚点", _build_angle_lines(payload.get("angles", {}))),
        ("信息", "\n".join(detail_lines).strip()),
        ("相位", _build_aspect_lines(payload.get("aspects", []))),
        ("行星", _build_planet_lines(payload.get("planets", []))),
        ("希腊点", "\n".join(greek_lines).strip()),
        ("可能性", "\n".join(summary_lines).strip()),
    ]


def _build_guolao_snapshot_sections(payload: Dict[str, Any]) -> List[tuple[str, str]]:
    person_info = payload.get("person_info", {})
    chart_profile = payload.get("chart_profile", {})
    guolao = payload.get("guolao", {})

    setup_lines = [
        f"姓名：{person_info.get('name', '未提供')}",
        f"出生地：{person_info.get('birth_place', '未提供')}",
        f"出生时间：{str(person_info.get('birth_datetime', '未提供')).replace('T', ' ')}",
        f"时区：{person_info.get('birth_timezone', '未提供')}",
        f"经纬度：{_format_degree(person_info.get('birth_longitude'))} / {_format_degree(person_info.get('birth_latitude'))}",
        f"黄道：{chart_profile.get('zodiac_label_zh', chart_profile.get('zodiac', '未知'))}",
        f"宫制：{chart_profile.get('house_system_label_zh', chart_profile.get('house_system', '未知'))}",
    ]

    star_lines = [
        f"{PLANET_LABELS_ZH.get(item['id'], item['id'])}："
        f"{item.get('sign_zh', '未知')} {_format_degree(item.get('degree_in_sign'))}，"
        f"第{item.get('house', '—')}宫，二十八宿 {item.get('su28', '未知')}"
        for item in payload.get("planets", [])
    ]

    shensha_lines = [
        f"星期主星：{PLANET_LABELS_ZH.get(guolao.get('weekday_ruler', ''), guolao.get('weekday_ruler', '未知'))}",
        f"月宿：{guolao.get('moon_mansion', '未知')}",
    ]

    return [
        ("起盘信息", "\n".join(setup_lines).strip()),
        ("七政四余宫位与二十八宿星曜", "\n".join(star_lines).strip() or "无"),
        ("神煞", "\n".join(shensha_lines).strip()),
    ]


def _build_chart_snapshot(payload: Dict[str, Any], chart_variant: str) -> Dict[str, Any]:
    technique = CORE_CHART_EXPORT_TECHNIQUES.get(chart_variant, "astrochart")
    sections = (
        _build_guolao_snapshot_sections(payload)
        if chart_variant == "guolao_chart"
        else _build_standard_chart_snapshot_sections(payload, chart_variant=chart_variant)
    )
    snapshot_text = _render_snapshot_text(sections)
    snapshot_export = parse_export_content(
        technique=technique,
        content=snapshot_text,
    )
    return {
        "snapshot_text": snapshot_text,
        "snapshot_export": snapshot_export,
    }


def _build_birth_info(payload: Dict[str, Any]):
    return build_astro_birth_info(
        birth_year=payload["birth_year"],
        birth_month=payload["birth_month"],
        birth_day=payload["birth_day"],
        birth_hour=payload["birth_hour"],
        birth_minute=payload.get("birth_minute", 0),
        birth_timezone=payload.get("birth_timezone"),
        birth_longitude=payload.get("birth_longitude"),
        birth_latitude=payload.get("birth_latitude"),
        name=payload.get("name"),
        birth_place=payload.get("birth_place"),
    )


def calculate_core_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    chart_variant: str = "chart",
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build an offline approximate core astrology chart family payload.
    """
    try:
        if chart_variant not in SUPPORTED_CHART_VARIANTS:
            raise ValueError(
                f"不支持的 chart_variant: {chart_variant}。"
                f"可选值：{', '.join(sorted(SUPPORTED_CHART_VARIANTS))}"
            )

        birth_info = _build_birth_info(
            {
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
            }
        )
        result = build_core_chart_payload(
            birth_info,
            chart_variant,
            hsys=hsys,
            zodiacal=zodiacal,
        )
        result.update(_build_chart_snapshot(result, chart_variant))
        return result
    except Exception as exc:
        return handle_calculation_error(exc, "核心星盘分析")


def calculate_germany_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build the FateBridge midpoint/germany chart payload.
    """
    try:
        birth_info = _build_birth_info(
            {
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
            }
        )
        return build_midpoint_payload(
            birth_info,
            hsys=hsys,
            zodiacal=zodiacal,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "量化盘分析")


def calculate_relative_chart_analysis(
    *,
    inner_payload: Dict[str, Any],
    outer_payload: Dict[str, Any],
    relative_mode: Any = None,
    relationship_mode: Any = None,
    relative_mode_source: Optional[str] = None,
    hsys: int = 0,
    zodiacal: int = 0,
) -> Dict[str, Any]:
    """
    Build synastry/composite payloads for two parties.
    """
    try:
        inner_birth = _build_birth_info(inner_payload)
        outer_birth = _build_birth_info(outer_payload)
        resolved_mode_source = relative_mode_source
        if resolved_mode_source not in {"default", "relative_mode", "relationship_mode"}:
            if relative_mode not in (None, ""):
                resolved_mode_source = "relative_mode"
            elif relationship_mode not in (None, ""):
                resolved_mode_source = "relationship_mode"
            else:
                resolved_mode_source = "default"
        resolved_mode = relative_mode if relative_mode not in (None, "") else relationship_mode
        return build_relative_payload(
            inner_birth=inner_birth,
            outer_birth=outer_birth,
            relative_mode=resolved_mode,
            relative_mode_source=resolved_mode_source,
            hsys=hsys,
            zodiacal=zodiacal,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "关系星盘分析")
