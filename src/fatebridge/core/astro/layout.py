"""Shared house layouts and cusp geometry for natal and relationship charts."""

from __future__ import annotations

from typing import Any, Dict, List

from fatebridge.core.astro import runtime
from fatebridge.core.astro.birth import AstroBirthInfo
from fatebridge.core.astro.ephemeris import _swisseph_angles
from fatebridge.core.astro.geometry import (
    _angles,
    _ayanamsha,
    _julian_day,
    _midpoint,
    normalize_angle,
)
from fatebridge.core.astro.parts import _build_houses


def _house_cusp_values_from_payload(chart_payload: Dict[str, Any]) -> List[float]:
    return [
        float(item["cusp_longitude"])
        for item in chart_payload.get("houses", [])
        if "cusp_longitude" in item
    ]


def _midpoint_house_cusps(
    left_cusps: List[float],
    right_cusps: List[float],
) -> List[float]:
    if len(left_cusps) != 12 or len(right_cusps) != 12:
        return []
    return [_midpoint(left_cusps[index], right_cusps[index]) for index in range(12)]


def _relative_house_layout(
    birth_info: AstroBirthInfo,
    *,
    house_system_info: Dict[str, Any],
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    julian_day = _julian_day(birth_info.utc_datetime)
    ayanamsha = _ayanamsha(julian_day) if zodiacal_info["sidereal"] else None

    if runtime.swe is None or house_system_info["key"] in {"whole_sign", "equal"}:
        angle_state = _swisseph_angles(
            julian_day,
            birth_info.longitude,
            birth_info.latitude,
        ) or _angles(julian_day, birth_info.longitude, birth_info.latitude)
        ascendant = angle_state["ascendant"]
        midheaven = angle_state["midheaven"]
        if ayanamsha is not None:
            ascendant = normalize_angle(ascendant - ayanamsha)
            midheaven = normalize_angle(midheaven - ayanamsha)
        house_cusps = [
            item["cusp_longitude"]
            for item in _build_houses(
                ascendant, house_system_info["key"], midheaven=midheaven
            )
        ]
        return {
            "ascendant": ascendant,
            "midheaven": midheaven,
            "house_cusps": house_cusps,
            "ayanamsha": ayanamsha,
        }

    try:
        cusps, ascmc = runtime.swe.houses_ex(
            julian_day,
            birth_info.latitude,
            birth_info.longitude,
            house_system_info["swisseph_code"],
        )
    except Exception as error:
        # Quadrant house systems have no honest offline equivalent: degrading to
        # _build_houses would anchor the cusps on the ascendant while keeping the
        # requested label, faking an approximation. Fail loud instead — mirrors
        # the offline-mode raise in _resolve_offline_house_system.
        runtime._log_swe_runtime_failure("houses_ex", error)
        raise ValueError(
            f"swisseph 运行时计算 {house_system_info['key']} 宫位失败"
            f"（{type(error).__name__}）：象限宫制无离线近似，"
            "已按 fail-loud 策略中止而非伪装近似结果。"
        ) from error
    ascendant = float(ascmc[0])
    midheaven = float(ascmc[1])
    house_cusps = [float(item) for item in cusps[:12]]

    if ayanamsha is not None:
        ascendant = normalize_angle(ascendant - ayanamsha)
        midheaven = normalize_angle(midheaven - ayanamsha)
        house_cusps = [normalize_angle(item - ayanamsha) for item in house_cusps]

    return {
        "ascendant": ascendant,
        "midheaven": midheaven,
        "house_cusps": house_cusps,
        "ayanamsha": ayanamsha,
    }
