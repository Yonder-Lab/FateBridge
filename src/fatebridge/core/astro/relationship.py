"""Relationship mode/focus selection and final payload orchestration."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from fatebridge.core.astro.aspects import (
    _build_directional_relative_antiscia,
    _build_directional_relative_aspects,
    _build_directional_relative_midpoints,
    _compatibility_score,
    _count_directional_relative_midpoint_hits,
    _flatten_directional_relative_aspects,
)
from fatebridge.core.astro.birth import AstroBirthInfo
from fatebridge.core.astro.profiles import (
    _derive_engine_profile,
    _precision_label_from_profiles,
    _precision_label_zh,
    _resolve_relative_house_system,
    _resolve_relative_zodiacal_mode,
)
from fatebridge.core.astro.reference import (
    _RELATIONSHIP_FOCUS_ALIASES,
    RELATIONSHIP_FOCUS_DEFS,
    RELATIVE_MODE_EXACT_ALIASES,
    RELATIVE_MODE_FALLBACK_ALIASES,
    RELATIVE_MODE_LABELS_ZH,
    RELATIVE_MODE_NUMERIC_MAP,
)
from fatebridge.core.astro.relationship_charts import (
    _build_marks_chart,
    _build_relative_base_chart,
    _build_relative_influence_pair,
    _build_timespace_chart,
    _composite_chart,
)


def _normalize_relative_mode(
    value: Any,
    *,
    source: str = "default",
) -> Dict[str, Any]:
    raw_value = value if value not in (None, "") else 0
    normalized: Optional[str] = None
    resolution = "default"
    note: Optional[str] = None
    mode_source = (
        source
        if source in {"default", "relative_mode", "relationship_mode"}
        else "default"
    )

    if isinstance(raw_value, int) and raw_value in RELATIVE_MODE_NUMERIC_MAP:
        normalized = RELATIVE_MODE_NUMERIC_MAP[raw_value]
        resolution = "numeric"
    elif isinstance(raw_value, str):
        stripped = raw_value.strip()
        if stripped.isdigit():
            numeric_value = int(stripped)
            normalized = RELATIVE_MODE_NUMERIC_MAP.get(numeric_value)
            if normalized is not None:
                resolution = "numeric_string"
        if normalized is None:
            normalized = RELATIVE_MODE_EXACT_ALIASES.get(stripped)
            if normalized is not None:
                resolution = "exact_alias"
        lowered = stripped.lower()
        if normalized is None and lowered == "synastry":
            if mode_source == "relationship_mode":
                normalized = "compare"
                resolution = "legacy_relationship_mode_synastry"
                note = (
                    "兼容旧版 relationship_mode='synastry' 语义，当前仍按比较盘处理；"
                    "如需影响盘语义，请改用 relative_mode='Synastry'、"
                    "'synastry' 或 'influence'。"
                )
            else:
                normalized = "influence"
                resolution = "relative_mode_synastry_alias"
        if normalized is None:
            normalized = RELATIVE_MODE_FALLBACK_ALIASES.get(stripped)
            if normalized is not None:
                resolution = "fallback_alias"
        if normalized is None:
            normalized = RELATIVE_MODE_FALLBACK_ALIASES.get(lowered)
            if normalized is not None:
                resolution = "fallback_alias_casefold"

    if normalized is None:
        if raw_value not in (None, "", 0, "0"):
            raise ValueError(
                "relative_mode 无效，请使用 Compare、Synastry、Composite，"
                "或使用 0/1/2 数值别名。"
            )
        normalized = "compare"
        resolution = "default_compare_fallback"

    payload = {
        "input": raw_value,
        "source": mode_source,
        "resolution": resolution,
        "normalized": normalized,
        "label_zh": RELATIVE_MODE_LABELS_ZH[normalized],
    }
    if note:
        payload["note"] = note
    return payload


def _normalize_relationship_focus(focus: Any) -> str:
    """把多语言/别名的关系取向输入归一化为 marriage/romance/general。"""
    if focus is None:
        return "general"
    raw = str(focus).strip()
    if raw in _RELATIONSHIP_FOCUS_ALIASES:
        return _RELATIONSHIP_FOCUS_ALIASES[raw]
    return _RELATIONSHIP_FOCUS_ALIASES.get(raw.casefold(), "general")


def relationship_focus_block(
    focus: Any, synastry_aspects: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """据关系取向生成解读侧重块，并把 synastry 相位过滤到该取向的关键星体。

    相位只要任一端落在该取向的关键星体集合内即纳入（如恋爱取向纳入所有涉及
    日/月/金/火的互相相位）。general（默认/未指定）不做过滤。
    """
    normalized = _normalize_relationship_focus(focus)
    if normalized == "general":
        return {
            "focus": "general",
            "focus_label_zh": "泛",
            "emphasis_houses": [],
            "emphasis_bodies": [],
            "note": "未指定关系取向，未对 synastry 相位做意图过滤。",
            "focused_synastry_aspects": [],
            "focused_aspect_count": 0,
        }

    spec = RELATIONSHIP_FOCUS_DEFS[normalized]
    bodies = set(spec["bodies"])
    focused = [
        aspect
        for aspect in synastry_aspects
        if aspect.get("inner") in bodies or aspect.get("outer") in bodies
    ]
    return {
        "focus": normalized,
        "focus_label_zh": spec["label_zh"],
        "emphasis_houses": list(spec["houses"]),
        "emphasis_bodies": list(spec["bodies"]),
        "note": spec["note"],
        "focused_synastry_aspects": focused,
        "focused_aspect_count": len(focused),
    }


def _base_relative_relationship_profile(
    relative_mode_info: Dict[str, Any],
    *,
    hsys: int,
    zodiacal: int,
    house_system_info: Dict[str, Any],
    zodiacal_info: Dict[str, Any],
    source_profiles: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    engine_profile = _derive_engine_profile(*(source_profiles or []))
    profile = {
        "chart_type": "relative",
        "relationship_mode": relative_mode_info["input"],
        "relative_mode_input": relative_mode_info["input"],
        "relative_mode_source": relative_mode_info["source"],
        "relative_mode_resolution": relative_mode_info["resolution"],
        "relative_mode_normalized": relative_mode_info["normalized"],
        "relative_mode_label_zh": relative_mode_info["label_zh"],
        "hsys": hsys,
        "house_system": house_system_info["key"],
        "house_system_label_zh": house_system_info["label_zh"],
        "zodiacal": zodiacal,
        "zodiac_mode": zodiacal_info["zodiac"],
        "zodiac_label_zh": zodiacal_info["label_zh"],
        **engine_profile,
    }
    if relative_mode_info.get("note"):
        profile["relative_mode_note"] = relative_mode_info["note"]
    return profile


def _assemble_relative_payload(
    *,
    relative_mode_info: Dict[str, Any],
    hsys: int,
    zodiacal: int,
    house_system_info: Dict[str, Any],
    zodiacal_info: Dict[str, Any],
    inner_chart: Dict[str, Any],
    outer_chart: Dict[str, Any],
    synastry_aspects: List[Dict[str, Any]],
    compatibility: Dict[str, int],
    composite_chart: Dict[str, Any],
    in_to_out_aspects: List[Dict[str, Any]],
    out_to_in_aspects: List[Dict[str, Any]],
    in_to_out_midpoint: Dict[str, Any],
    out_to_in_midpoint: Dict[str, Any],
    in_to_out_antiscia: List[Dict[str, Any]],
    out_to_in_antiscia: List[Dict[str, Any]],
    in_to_out_contra_antiscia: List[Dict[str, Any]],
    out_to_in_contra_antiscia: List[Dict[str, Any]],
    inner_influence: Dict[str, Any],
    outer_influence: Dict[str, Any],
    primary_layer: str,
    third_chart: Dict[str, Any],
    chart_value: Dict[str, Any],
    summary: List[str],
) -> Dict[str, Any]:
    """Assemble the relative-chart payload shared by all 5 relationship modes.

    The 5 modes (compare/composite/influence/timespace/marks) produced
    byte-identical dicts apart from four axes: ``primary_layer``, the third
    ``source_profiles`` chart, the top-level ``chart`` value, and the bespoke
    ``summary`` lines. Those four are parameterised; everything else (including
    the legacy camelCase aliases) is shared here.
    """
    return {
        "relationship_profile": {
            **_base_relative_relationship_profile(
                relative_mode_info,
                hsys=hsys,
                zodiacal=zodiacal,
                house_system_info=house_system_info,
                zodiacal_info=zodiacal_info,
                source_profiles=(
                    inner_chart.get("chart_profile", {}),
                    outer_chart.get("chart_profile", {}),
                    third_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": primary_layer,
            "mode_status": "implemented",
        },
        "inner_chart": inner_chart,
        "outer_chart": outer_chart,
        "synastry_aspects": synastry_aspects,
        "composite_chart": composite_chart,
        "compatibility": compatibility,
        "in_to_out_aspects": in_to_out_aspects,
        "out_to_in_aspects": out_to_in_aspects,
        "in_to_out_midpoint": in_to_out_midpoint,
        "out_to_in_midpoint": out_to_in_midpoint,
        "in_to_out_antiscia": in_to_out_antiscia,
        "out_to_in_antiscia": out_to_in_antiscia,
        "in_to_out_contra_antiscia": in_to_out_contra_antiscia,
        "out_to_in_contra_antiscia": out_to_in_contra_antiscia,
        "chart": chart_value,
        "inner": inner_influence,
        "outer": outer_influence,
        "inToOutAsp": in_to_out_aspects,
        "outToInAsp": out_to_in_aspects,
        "inToOutMidpoint": in_to_out_midpoint,
        "outToInMidpoint": out_to_in_midpoint,
        "inToOutAnti": in_to_out_antiscia,
        "outToInAnti": out_to_in_antiscia,
        "inToOutCAnti": in_to_out_contra_antiscia,
        "outToInCAnti": out_to_in_contra_antiscia,
        "summary": summary,
    }


def build_relative_payload(
    inner_birth: AstroBirthInfo,
    outer_birth: AstroBirthInfo,
    relative_mode: Any = None,
    relative_mode_source: str = "default",
    hsys: int = 3,
    zodiacal: int = 0,
    relationship_focus: Any = None,
) -> Dict[str, Any]:
    relative_mode_info = _normalize_relative_mode(
        relative_mode,
        source=relative_mode_source,
    )
    relative_house_system = _resolve_relative_house_system(hsys)
    zodiacal_info = _resolve_relative_zodiacal_mode(zodiacal)
    inner_chart = _build_relative_base_chart(
        inner_birth,
        house_system_info=relative_house_system,
        zodiacal_info=zodiacal_info,
    )
    outer_chart = _build_relative_base_chart(
        outer_birth,
        house_system_info=relative_house_system,
        zodiacal_info=zodiacal_info,
    )
    in_to_out_aspects = _build_directional_relative_aspects(
        inner_chart["planets"], outer_chart["planets"]
    )
    out_to_in_aspects = _build_directional_relative_aspects(
        outer_chart["planets"], inner_chart["planets"]
    )
    synastry_aspects = _flatten_directional_relative_aspects(
        in_to_out_aspects, source_key="inner", target_key="outer"
    )
    synastry_aspects = sorted(
        synastry_aspects,
        key=lambda item: (item["orb"], item["inner"], item["outer"]),
    )
    composite_chart = _composite_chart(
        inner_chart,
        outer_chart,
        house_system=relative_house_system["key"],
        zodiacal_info=zodiacal_info,
    )
    timespace_chart = _build_timespace_chart(
        inner_birth,
        outer_birth,
        house_system_info=relative_house_system,
        zodiacal_info=zodiacal_info,
    )
    marks_chart = _build_marks_chart(
        composite_chart,
        timespace_chart,
        house_system=relative_house_system["key"],
        zodiacal_info=zodiacal_info,
    )
    inner_influence, outer_influence = _build_relative_influence_pair(
        inner_chart,
        outer_chart,
        house_system=relative_house_system["key"],
        zodiacal_info=zodiacal_info,
    )
    compatibility = _compatibility_score(
        inner_chart["planets"], outer_chart["planets"], synastry_aspects
    )
    in_to_out_midpoint = _build_directional_relative_midpoints(
        inner_chart["planets"], outer_chart["planets"]
    )
    out_to_in_midpoint = _build_directional_relative_midpoints(
        outer_chart["planets"], inner_chart["planets"]
    )
    in_to_out_antiscia = _build_directional_relative_antiscia(
        inner_chart["planets"], outer_chart["planets"]
    )
    out_to_in_antiscia = _build_directional_relative_antiscia(
        outer_chart["planets"], inner_chart["planets"]
    )
    in_to_out_contra_antiscia = _build_directional_relative_antiscia(
        inner_chart["planets"], outer_chart["planets"], contra=True
    )
    out_to_in_contra_antiscia = _build_directional_relative_antiscia(
        outer_chart["planets"], inner_chart["planets"], contra=True
    )
    shared_kwargs: Dict[str, Any] = {
        "relative_mode_info": relative_mode_info,
        "hsys": hsys,
        "zodiacal": zodiacal,
        "house_system_info": relative_house_system,
        "zodiacal_info": zodiacal_info,
        "inner_chart": inner_chart,
        "outer_chart": outer_chart,
        "synastry_aspects": synastry_aspects,
        "compatibility": compatibility,
        "composite_chart": composite_chart,
        "in_to_out_aspects": in_to_out_aspects,
        "out_to_in_aspects": out_to_in_aspects,
        "in_to_out_midpoint": in_to_out_midpoint,
        "out_to_in_midpoint": out_to_in_midpoint,
        "in_to_out_antiscia": in_to_out_antiscia,
        "out_to_in_antiscia": out_to_in_antiscia,
        "in_to_out_contra_antiscia": in_to_out_contra_antiscia,
        "out_to_in_contra_antiscia": out_to_in_contra_antiscia,
        "inner_influence": inner_influence,
        "outer_influence": outer_influence,
    }

    normalized_mode = relative_mode_info["normalized"]
    if normalized_mode == "compare":
        payload = _assemble_relative_payload(
            **shared_kwargs,
            primary_layer="directional_synastry",
            third_chart=composite_chart,
            chart_value={},
            summary=[
                "已生成 FateBridge 比较盘分析。",
                f"A对B相位主体数：{len(in_to_out_aspects)}。",
                f"B对A相位主体数：{len(out_to_in_aspects)}。",
                f"A对B中点相位命中：{_count_directional_relative_midpoint_hits(in_to_out_midpoint)}。",
                f"A对B映点命中：{len(in_to_out_antiscia)}。",
                f"综合分：{compatibility['overall_score']}。",
                "合成图盘保留在 composite_chart 兼容字段；主 chart 层在比较盘模式下当前留空。",
                "影响图盘、中点相位与映点/反映点均已提供"
                f"{_precision_label_from_profiles(inner_chart.get('chart_profile', {}), outer_chart.get('chart_profile', {}), composite_chart.get('chart_profile', {}))}结果。",
            ],
        )
    elif normalized_mode == "composite":
        payload = _assemble_relative_payload(
            **shared_kwargs,
            primary_layer="composite_chart",
            third_chart=composite_chart,
            chart_value=composite_chart,
            summary=[
                "已生成 FateBridge 组合盘分析。",
                f"合成盘行星数量：{len(composite_chart.get('planets', []))}。",
                f"A对B相位主体数：{len(in_to_out_aspects)}。",
                f"A对B中点相位命中：{_count_directional_relative_midpoint_hits(in_to_out_midpoint)}。",
                f"A对B映点命中：{len(in_to_out_antiscia)}。",
                f"综合分：{compatibility['overall_score']}。",
                "影响图盘、中点相位与映点/反映点均已提供"
                f"{_precision_label_from_profiles(inner_chart.get('chart_profile', {}), outer_chart.get('chart_profile', {}), composite_chart.get('chart_profile', {}))}结果。",
            ],
        )
    elif normalized_mode == "influence":
        payload = _assemble_relative_payload(
            **shared_kwargs,
            primary_layer="influence_chart_pair",
            third_chart=composite_chart,
            chart_value=composite_chart,
            summary=[
                "已生成 FateBridge 影响盘分析。",
                f"A视角影响图盘星体数：{len(inner_influence.get('chart', {}).get('planets', []))}。",
                f"B视角影响图盘星体数：{len(outer_influence.get('chart', {}).get('planets', []))}。",
                f"A对B相位主体数：{len(in_to_out_aspects)}。",
                f"综合分：{compatibility['overall_score']}。",
                "合成图盘保留在 chart / composite_chart 中，作为影响盘的辅助层。",
            ],
        )
    elif normalized_mode == "timespace":
        payload = _assemble_relative_payload(
            **shared_kwargs,
            primary_layer="timespace_chart",
            third_chart=timespace_chart,
            chart_value=timespace_chart,
            summary=[
                "已生成 FateBridge 时空中点盘分析。",
                f"时空中点盘行星数量：{len(timespace_chart.get('planets', []))}。",
                f"A对B相位主体数：{len(in_to_out_aspects)}。",
                f"综合分：{compatibility['overall_score']}。",
                (
                    "主 chart 层采用双方出生时间与地理位置中点生成的"
                    f"{_precision_label_zh(timespace_chart.get('chart_profile', {}).get('engine_precision', 'approximate_orbital_model'))}盘。"
                ),
            ],
        )
    elif normalized_mode == "marks":
        payload = _assemble_relative_payload(
            **shared_kwargs,
            primary_layer="marks_chart",
            third_chart=marks_chart,
            chart_value=marks_chart,
            summary=[
                "已生成 FateBridge 马克斯盘分析。",
                f"马克斯盘行星数量：{len(marks_chart.get('planets', []))}。",
                f"A对B相位主体数：{len(in_to_out_aspects)}。",
                f"综合分：{compatibility['overall_score']}。",
                (
                    "主 chart 层采用组合盘与时空中点盘之间的"
                    f"{_precision_label_zh(marks_chart.get('chart_profile', {}).get('engine_precision', 'approximate_orbital_model'))}派生结果。"
                ),
            ],
        )
    else:  # pragma: no cover - _normalize_relative_mode only yields the 5 modes above
        raise ValueError(f"未支持的关系盘模式: {normalized_mode!r}")

    # 关系取向解读侧重对所有盘式通用，在分发后统一附加一次。
    payload.setdefault("relationship_profile", {})["focus"] = relationship_focus_block(
        relationship_focus, synastry_aspects
    )
    return payload
