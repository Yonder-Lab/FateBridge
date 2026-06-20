"""
Service surfaces for the western *lifespan* techniques.

Each ``calculate_*`` function turns request fields into the standard FateBridge
envelope: ``analysis_context`` (how the chart was cast), ``natal_reference``
(the natal points the technique reads), the technique payload under its own key,
a one-line ``summary``, and a human-readable ``snapshot_text``.

Computation lives in :mod:`fatebridge.core.astrology_lifespan`; this layer only
prepares the natal chart, dispatches to the right builder, and renders output.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from fatebridge.core.astrology_lifespan import (
    build_balbillus_payload,
    build_distributions_payload,
    build_harmonic_payload,
    build_keypoints_payload,
    build_lunation_phase_payload,
    build_planetary_ages_payload,
    build_triplicity_rulers_payload,
)
from fatebridge.core.astrology_predictive import (
    build_analysis_datetime,
    build_natal_subject,
    build_predictive_birth_info,
    calculate_age_years,
    determine_sect,
    extract_reference_points,
    sect_label,
)
from fatebridge.utils.helpers import handle_calculation_error, normalize_house_system


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _render_snapshot_text(sections: List[Tuple[str, str]]) -> str:
    """Render ``[title]`` + body blocks into a single snapshot string."""
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body.strip():
            blocks.append(body)
        blocks.append("")
    return "\n".join(blocks).strip()


def _prepare_chart(
    *,
    house_system: str,
    zodiac_type: str,
    **birth_kwargs: Any,
) -> Tuple[Any, Any, Dict[str, Any], str]:
    """Build birth info, natal subject, natal reference, and sect from kwargs."""
    house_system = normalize_house_system(house_system)
    birth_info = build_predictive_birth_info(
        birth_year=birth_kwargs["birth_year"],
        birth_month=birth_kwargs["birth_month"],
        birth_day=birth_kwargs["birth_day"],
        birth_hour=birth_kwargs["birth_hour"],
        birth_minute=birth_kwargs.get("birth_minute", 0),
        birth_timezone=birth_kwargs.get("birth_timezone"),
        birth_longitude=birth_kwargs["birth_longitude"],
        birth_latitude=birth_kwargs["birth_latitude"],
        name=birth_kwargs.get("name"),
        birth_place=birth_kwargs.get("birth_place"),
    )
    subject = build_natal_subject(
        birth_info, house_system=house_system, zodiac_type=zodiac_type
    )
    natal_reference = extract_reference_points(subject)
    sect = determine_sect(subject)
    return birth_info, subject, natal_reference, sect


def _analysis_context(
    *,
    label: str,
    birth_info: Any,
    sect: str,
    house_system: str,
    zodiac_type: str,
) -> Dict[str, Any]:
    return {
        "tool": label,
        "birth_datetime": birth_info.local_datetime.isoformat(),
        "timezone": birth_info.timezone,
        "house_system": normalize_house_system(house_system),
        "zodiac_type": zodiac_type,
        "sect": sect,
        "sect_label": sect_label(sect),
        "engine": "fatebridge-offline",
    }


def _envelope(
    *,
    analysis_type: str,
    tool_name: str,
    context: Dict[str, Any],
    natal_reference: Dict[str, Any],
    payload: Dict[str, Any],
    summary: str,
    sections: List[Tuple[str, str]],
) -> Dict[str, Any]:
    return {
        "analysis_type": analysis_type,
        "engine": "fatebridge-offline",
        "analysis_context": context,
        "natal_reference": natal_reference,
        tool_name: payload,
        "summary": summary,
        "snapshot_text": _render_snapshot_text(sections),
    }


# ---------------------------------------------------------------------------
# 1. 调波盘 (astro_harmonic).
# ---------------------------------------------------------------------------


def calculate_harmonic_chart(
    *,
    harmonic: int = 9,
    orb: float = 2.0,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成调波盘（本命黄经 × 调波数）与同频合相。"""
    label = "调波盘"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_harmonic_payload(natal_reference, harmonic=harmonic, orb=orb)
        conjunction_count = len(payload["resonant_conjunctions"])
        summary = (
            f"{harmonic} 调波盘：检出 {conjunction_count} 组同频合相"
            f"（容许度 {orb}°）。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            ("调波位置", _json_block(payload["positions"])),
            ("同频合相", _json_block(payload["resonant_conjunctions"])),
        ]
        return _envelope(
            analysis_type="西占调波盘",
            tool_name="harmonic_chart",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 2. 行星年龄 (astro_planetary_ages).
# ---------------------------------------------------------------------------


def calculate_planetary_ages(
    *,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成托勒密七年龄段；给定参照日期则标注当前所处年龄段。"""
    label = "行星年龄"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        current_age: Optional[float] = None
        if (
            analysis_year is not None
            or analysis_month is not None
            or analysis_day is not None
        ):
            analysis_datetime = build_analysis_datetime(
                birth_info,
                analysis_year=analysis_year,
                analysis_month=analysis_month,
                analysis_day=analysis_day,
            )
            current_age = calculate_age_years(birth_info, analysis_datetime)
        payload = build_planetary_ages_payload(
            natal_reference, current_age_years=current_age
        )
        if payload["active_planet"] is None:
            summary = "托勒密七年龄段：未指定参照日期，仅列出全生命周期分段。"
        else:
            summary = (
                f"托勒密七年龄段：约 {payload['current_age_years']} 岁，"
                f"当前由{payload['active_planet_label']}主管。"
            )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            ("年龄段表", _json_block(payload["bands"])),
        ]
        return _envelope(
            analysis_type="西占行星年龄",
            tool_name="planetary_ages",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 3. 三分主星推运 (astro_triplicity_rulers).
# ---------------------------------------------------------------------------


def calculate_triplicity_rulers(
    *,
    lifespan: float = 75.0,
    division: str = "thirds",
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成区间光体三分主星划分的人生阶段。"""
    label = "三分主星推运"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_triplicity_rulers_payload(
            natal_reference, sect=sect, lifespan=lifespan, division=division
        )
        rulers = "、".join(
            stage["ruler_label"] or "未定" for stage in payload["stages"]
        )
        summary = (
            f"{payload['sect_label']}以{payload['sect_light_label']}为区间光体，"
            f"{payload['element_label']}三分主星依次为 {rulers}。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "区间光体",
                _json_block(
                    {
                        "sect": payload["sect"],
                        "sect_label": payload["sect_label"],
                        "sect_light": payload["sect_light"],
                        "sect_light_label": payload["sect_light_label"],
                        "sect_light_sign": payload["sect_light_sign"],
                        "element": payload["element"],
                        "element_label": payload["element_label"],
                    }
                ),
            ),
            ("人生阶段", _json_block(payload["stages"])),
        ]
        return _envelope(
            analysis_type="西占三分主星推运",
            tool_name="triplicity_rulers",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 4. 月相推运 (astro_lunation_phase).
# ---------------------------------------------------------------------------


def calculate_lunation_phase(
    *,
    max_age_years: float = 90.0,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成次限月相推运八相时间轴。"""
    label = "月相推运"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_lunation_phase_payload(
            natal_reference, max_age_years=max_age_years
        )
        summary = (
            f"次限月相推运：本命{payload['natal_phase_label']}"
            f"（日月相位差 {payload['natal_elongation_degree']}°），"
            f"{max_age_years} 岁内共 {len(payload['phase_ingresses'])} 次相位转换。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "本命月相",
                _json_block(
                    {
                        "natal_phase": payload["natal_phase"],
                        "natal_phase_label": payload["natal_phase_label"],
                        "natal_elongation_degree": payload["natal_elongation_degree"],
                        "progression_rate_deg_per_year": payload[
                            "progression_rate_deg_per_year"
                        ],
                        "synodic_cycle_years": payload["synodic_cycle_years"],
                    }
                ),
            ),
            ("相位转换时间轴", _json_block(payload["phase_ingresses"])),
        ]
        return _envelope(
            analysis_type="西占月相推运",
            tool_name="lunation_phase",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 5. 界推运 / 分配法 (astro_distributions).
# ---------------------------------------------------------------------------


def calculate_distributions(
    *,
    time_key: str = "Ptolemy",
    max_age_years: float = 90.0,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成界推运（上升历经埃及界限）的分配主星时间轴。"""
    label = "界推运"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_distributions_payload(
            natal_reference, time_key=time_key, max_age_years=max_age_years
        )
        summary = (
            f"界推运（{time_key} 时间钥匙）：{max_age_years} 岁内"
            f"上升历经 {len(payload['periods'])} 段界限分配。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "分配设置",
                _json_block(
                    {
                        "time_key": payload["time_key"],
                        "rate_deg_per_year": payload["rate_deg_per_year"],
                        "ascendant_absolute_degree": payload[
                            "ascendant_absolute_degree"
                        ],
                        "max_age_years": payload["max_age_years"],
                    }
                ),
            ),
            ("界限分配时间轴", _json_block(payload["periods"])),
        ]
        return _envelope(
            analysis_type="西占界推运",
            tool_name="distributions",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 6. Balbillus 129年系统 (astro_balbillus).
# ---------------------------------------------------------------------------


def calculate_balbillus(
    *,
    start_planet: str = "Sun",
    mode: str = "nearest",
    max_age_years: float = 120.0,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成 Balbillus 129 年系统主限与子限时间轴。"""
    label = "Balbillus 129年系统"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_balbillus_payload(
            natal_reference,
            start_planet=start_planet,
            mode=mode,
            max_age_years=max_age_years,
        )
        summary = (
            f"Balbillus 129 年系统（{payload['mode_label']}）：自"
            f"{payload['start_planet_label']}起，{max_age_years} 岁内"
            f"共 {len(payload['periods'])} 段主限。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "系统设置",
                _json_block(
                    {
                        "start_planet": payload["start_planet"],
                        "mode": payload["mode"],
                        "mode_label": payload["mode_label"],
                        "zodiacal_order": payload["zodiacal_order"],
                        "max_age_years": payload["max_age_years"],
                    }
                ),
            ),
            ("主限·子限时间轴", _json_block(payload["periods"])),
        ]
        return _envelope(
            analysis_type="西占Balbillus 129年系统",
            tool_name="balbillus",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)


# ---------------------------------------------------------------------------
# 7. 数字相位推运 (astro_keypoints).
# ---------------------------------------------------------------------------


def calculate_keypoints(
    *,
    release_mode: str = "soul",
    max_age_years: int = 120,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
    **birth_kwargs: Any,
) -> Dict[str, Any]:
    """生成数字相位推运（120 年关键点）激活时间轴。"""
    label = "数字相位推运"
    try:
        birth_info, _subject, natal_reference, sect = _prepare_chart(
            house_system=house_system, zodiac_type=zodiac_type, **birth_kwargs
        )
        payload = build_keypoints_payload(
            natal_reference, release_mode=release_mode, max_age_years=max_age_years
        )
        summary = (
            f"数字相位推运（释放点={payload['release_mode_label']}）："
            f"共 {len(payload['activations'])} 个激活年。"
        )
        context = _analysis_context(
            label=label,
            birth_info=birth_info,
            sect=sect,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "星位挂钩",
                _json_block(
                    {
                        "release_mode": payload["release_mode"],
                        "release_mode_label": payload["release_mode_label"],
                        "positions": payload["positions"],
                    }
                ),
            ),
            ("激活时间轴", _json_block(payload["activations"])),
        ]
        return _envelope(
            analysis_type="西占数字相位推运",
            tool_name="keypoints",
            context=context,
            natal_reference=natal_reference,
            payload=payload,
            summary=summary,
            sections=sections,
        )
    except Exception as exc:
        return handle_calculation_error(exc, label)
