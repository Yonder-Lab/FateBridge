"""Derived chart assembly for composite, timespace, influence and marks modes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fatebridge.core.astro.aspects import _build_aspects
from fatebridge.core.astro.birth import AstroBirthInfo
from fatebridge.core.astro.chart import build_core_chart_payload
from fatebridge.core.astro.geometry import _midpoint, _sign_name, normalize_angle
from fatebridge.core.astro.layout import (
    _house_cusp_values_from_payload,
    _midpoint_house_cusps,
    _relative_house_layout,
)
from fatebridge.core.astro.parts import _balance, _build_houses, _build_planet_record
from fatebridge.core.astro.profiles import (
    _derive_engine_profile,
    _precision_label_zh,
    _relative_house_profile_overrides,
    _relative_zodiac_profile_overrides,
)
from fatebridge.core.astro.reference import BALANCE_BASIS, PLANET_SEQUENCE
from fatebridge.core.astrology_tables import SIGN_LABELS_ZH as SIGN_LABELS_ZH
from fatebridge.utils.timezones import parse_timezone_name


def _composite_chart(
    inner_chart: Dict[str, Any],
    outer_chart: Dict[str, Any],
    *,
    house_system: str = "equal",
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    engine_profile = _derive_engine_profile(
        inner_chart.get("chart_profile", {}),
        outer_chart.get("chart_profile", {}),
    )
    inner_planets = {item["id"]: item for item in inner_chart["planets"]}
    outer_planets = {item["id"]: item for item in outer_chart["planets"]}
    house_cusps = (
        []
        if house_system == "whole_sign"
        else _midpoint_house_cusps(
            _house_cusp_values_from_payload(inner_chart),
            _house_cusp_values_from_payload(outer_chart),
        )
    )
    composite_planets: List[Dict[str, Any]] = []
    ascendant = _midpoint(
        inner_chart["angles"]["ascendant"]["longitude"],
        outer_chart["angles"]["ascendant"]["longitude"],
    )
    midheaven = _midpoint(
        inner_chart["angles"]["midheaven"]["longitude"],
        outer_chart["angles"]["midheaven"]["longitude"],
    )
    for planet in PLANET_SEQUENCE:
        if planet not in inner_planets or planet not in outer_planets:
            continue
        longitude = _midpoint(
            inner_planets[planet]["longitude"],
            outer_planets[planet]["longitude"],
        )
        composite_planets.append(
            _build_planet_record(
                planet,
                longitude,
                (inner_planets[planet]["latitude"] + outer_planets[planet]["latitude"])
                / 2.0,
                ascendant,
                house_system,
                house_cusps=house_cusps or None,
            )
        )
    aspects = _build_aspects(composite_planets)
    return {
        "person_info": {
            "name": f"{inner_chart['person_info']['name']} / {outer_chart['person_info']['name']} 组合盘",
            "birth_place": f"{inner_chart['person_info']['birth_place']} / {outer_chart['person_info']['birth_place']}",
            "birth_timezone": inner_chart["person_info"]["birth_timezone"],
            "birth_longitude": round(
                (
                    inner_chart["person_info"]["birth_longitude"]
                    + outer_chart["person_info"]["birth_longitude"]
                )
                / 2.0,
                4,
            ),
            "birth_latitude": round(
                (
                    inner_chart["person_info"]["birth_latitude"]
                    + outer_chart["person_info"]["birth_latitude"]
                )
                / 2.0,
                4,
            ),
        },
        "chart_profile": {
            "chart_type": "composite",
            "tradition": inner_chart.get("chart_profile", {}).get("tradition", False),
            "house_system": house_system,
            "house_system_code": inner_chart.get("chart_profile", {}).get(
                "house_system_code"
            ),
            "house_system_label_zh": inner_chart.get("chart_profile", {}).get(
                "house_system_label_zh"
            ),
            **_relative_zodiac_profile_overrides(zodiacal_info),
            **engine_profile,
        },
        "angles": {
            "ascendant": {
                "longitude": round(ascendant, 4),
                "sign": _sign_name(ascendant),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(ascendant)],
            },
            "midheaven": {
                "longitude": round(midheaven, 4),
                "sign": _sign_name(midheaven),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(midheaven)],
            },
        },
        "houses": _build_houses(
            ascendant,
            house_system,
            house_cusps=house_cusps or None,
        ),
        "planets": composite_planets,
        "aspects": aspects,
        "element_balance": _balance(composite_planets, "element"),
        "modality_balance": _balance(composite_planets, "modality"),
        "balance_basis": BALANCE_BASIS,
        "summary": [
            f"已生成 FateBridge 组合盘{_precision_label_zh(engine_profile['engine_precision'])}层。",
            f"行星数量：{len(composite_planets)}。",
            f"相位数量：{len(aspects)}。",
        ],
    }


def _person_info_from_birth_info(
    birth_info: AstroBirthInfo,
    *,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "name": name or birth_info.name,
        "birth_place": birth_place or birth_info.birth_place,
        "birth_timezone": birth_info.timezone,
        "birth_longitude": birth_info.longitude,
        "birth_latitude": birth_info.latitude,
        "birth_datetime": birth_info.local_datetime.isoformat(),
        "utc_datetime": birth_info.utc_datetime.isoformat(),
    }


def _chart_source_planets(chart_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "longitude": item["longitude"],
            "latitude": item.get("latitude", 0.0),
        }
        for item in chart_payload["planets"]
    ]


def _build_relative_base_chart(
    birth_info: AstroBirthInfo,
    *,
    house_system_info: Dict[str, Any],
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    base_chart = build_core_chart_payload(birth_info, "chart")
    engine_profile = _derive_engine_profile(base_chart.get("chart_profile", {}))
    source_planets = _chart_source_planets(base_chart)
    layout = _relative_house_layout(
        birth_info,
        house_system_info=house_system_info,
        zodiacal_info=zodiacal_info,
    )
    ayanamsha = layout["ayanamsha"]
    if ayanamsha is not None:
        source_planets = [
            {
                **item,
                "longitude": normalize_angle(item["longitude"] - ayanamsha),
            }
            for item in source_planets
        ]
    return _build_chart_from_positions(
        chart_type=base_chart["chart_profile"]["chart_type"],
        person_info=base_chart["person_info"],
        source_planets=source_planets,
        ascendant=layout["ascendant"],
        midheaven=layout["midheaven"],
        house_system=house_system_info["key"],
        house_cusps=(
            None if house_system_info["key"] == "whole_sign" else layout["house_cusps"]
        ),
        summary_prefix="已生成 FateBridge 关系盘基础命盘。",
        engine_profile=engine_profile,
        profile_overrides={
            "tradition": base_chart["chart_profile"].get("tradition", False),
            **_relative_house_profile_overrides(house_system_info),
            **_relative_zodiac_profile_overrides(zodiacal_info, ayanamsha=ayanamsha),
        },
    )


def _planet_sort_key(item: Dict[str, Any]) -> Tuple[int, Any]:
    planet_id = item.get("id")
    if planet_id in PLANET_SEQUENCE:
        return (0, PLANET_SEQUENCE.index(planet_id))
    return (1, planet_id or "")


def _build_chart_from_positions(
    *,
    chart_type: str,
    person_info: Dict[str, Any],
    source_planets: List[Dict[str, Any]],
    ascendant: float,
    midheaven: float,
    house_system: str,
    house_cusps: Optional[List[float]] = None,
    summary_prefix: str,
    profile_overrides: Optional[Dict[str, Any]] = None,
    engine_profile: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    planets = [
        _build_planet_record(
            item["id"],
            item["longitude"],
            item.get("latitude", 0.0),
            ascendant,
            house_system,
            house_cusps=house_cusps,
        )
        for item in sorted(source_planets, key=_planet_sort_key)
    ]
    aspects = _build_aspects(planets)
    chart_profile = {
        "chart_type": chart_type,
        "zodiac": "tropical",
        "house_system": house_system,
        "tradition": False,
        "engine_precision": "approximate_orbital_model",
        "engine_backend": "fatebridge_approximate_orbital_model",
    }
    if engine_profile:
        chart_profile.update(engine_profile)
    if profile_overrides:
        chart_profile.update(profile_overrides)
    return {
        "person_info": person_info,
        "chart_profile": chart_profile,
        "angles": {
            "ascendant": {
                "longitude": round(ascendant, 4),
                "sign": _sign_name(ascendant),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(ascendant)],
            },
            "midheaven": {
                "longitude": round(midheaven, 4),
                "sign": _sign_name(midheaven),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(midheaven)],
            },
        },
        "houses": _build_houses(ascendant, house_system, house_cusps=house_cusps),
        "planets": planets,
        "aspects": aspects,
        "element_balance": _balance(planets, "element"),
        "modality_balance": _balance(planets, "modality"),
        "balance_basis": BALANCE_BASIS,
        "summary": [
            summary_prefix,
            f"行星数量：{len(planets)}。",
            f"相位数量：{len(aspects)}。",
        ],
    }


def _build_midpoint_birth_info(
    inner_birth: AstroBirthInfo,
    outer_birth: AstroBirthInfo,
) -> AstroBirthInfo:
    midpoint_utc = (
        inner_birth.utc_datetime
        + (outer_birth.utc_datetime - inner_birth.utc_datetime) / 2
    )
    timezone_name = (
        inner_birth.timezone if inner_birth.timezone == outer_birth.timezone else "UTC"
    )
    midpoint_local = midpoint_utc.astimezone(parse_timezone_name(timezone_name))
    return AstroBirthInfo(
        name=f"{inner_birth.name}/{outer_birth.name} 时空中点",
        birth_place=f"{inner_birth.birth_place} / {outer_birth.birth_place} 中点",
        timezone=timezone_name,
        longitude=round((inner_birth.longitude + outer_birth.longitude) / 2.0, 4),
        latitude=round((inner_birth.latitude + outer_birth.latitude) / 2.0, 4),
        local_datetime=midpoint_local,
        utc_datetime=midpoint_utc,
    )


def _build_timespace_chart(
    inner_birth: AstroBirthInfo,
    outer_birth: AstroBirthInfo,
    *,
    house_system_info: Dict[str, Any],
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    midpoint_birth = _build_midpoint_birth_info(inner_birth, outer_birth)
    midpoint_chart = build_core_chart_payload(midpoint_birth, "chart")
    engine_profile = _derive_engine_profile(midpoint_chart.get("chart_profile", {}))
    source_planets = _chart_source_planets(midpoint_chart)
    layout = _relative_house_layout(
        midpoint_birth,
        house_system_info=house_system_info,
        zodiacal_info=zodiacal_info,
    )
    ayanamsha = layout["ayanamsha"]
    if ayanamsha is not None:
        source_planets = [
            {
                **item,
                "longitude": normalize_angle(item["longitude"] - ayanamsha),
            }
            for item in source_planets
        ]
    return _build_chart_from_positions(
        chart_type="timespace",
        person_info=_person_info_from_birth_info(midpoint_birth),
        source_planets=source_planets,
        ascendant=layout["ascendant"],
        midheaven=layout["midheaven"],
        house_system=house_system_info["key"],
        house_cusps=(
            None if house_system_info["key"] == "whole_sign" else layout["house_cusps"]
        ),
        summary_prefix="已生成 FateBridge 时空中点盘。",
        engine_profile=engine_profile,
        profile_overrides={
            "derivation": "midpoint_birth",
            "tradition": midpoint_chart["chart_profile"].get("tradition", False),
            **_relative_house_profile_overrides(house_system_info),
            **_relative_zodiac_profile_overrides(zodiacal_info, ayanamsha=ayanamsha),
        },
    )


def _build_influence_chart_wrapper(
    *,
    role: str,
    house_chart: Dict[str, Any],
    source_chart: Dict[str, Any],
    house_system: str,
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    engine_profile = _derive_engine_profile(
        house_chart.get("chart_profile", {}),
        source_chart.get("chart_profile", {}),
    )
    target_name = house_chart["person_info"]["name"]
    source_name = source_chart["person_info"]["name"]
    house_cusps = (
        None
        if house_system == "whole_sign"
        else _house_cusp_values_from_payload(house_chart)
    )
    influence_chart = _build_chart_from_positions(
        chart_type=f"influence_{role}",
        person_info={
            **house_chart["person_info"],
            "name": f"{target_name}受{source_name}影响",
        },
        source_planets=source_chart["planets"],
        ascendant=house_chart["angles"]["ascendant"]["longitude"],
        midheaven=house_chart["angles"]["midheaven"]["longitude"],
        house_system=house_system,
        house_cusps=house_cusps,
        summary_prefix=f"已生成 {target_name} 视角的影响图盘。",
        engine_profile=engine_profile,
        profile_overrides={
            "reference_frame": f"{source_name}_planets_in_{target_name}_houses",
            "tradition": house_chart.get("chart_profile", {}).get("tradition", False),
            "house_system_code": house_chart.get("chart_profile", {}).get(
                "house_system_code"
            ),
            "house_system_label_zh": house_chart.get("chart_profile", {}).get(
                "house_system_label_zh"
            ),
            **_relative_zodiac_profile_overrides(zodiacal_info),
        },
    )
    return {
        "chart_profile": {
            "chart_type": f"influence_{role}",
            "house_system": house_system,
            "house_system_code": house_chart.get("chart_profile", {}).get(
                "house_system_code"
            ),
            "house_system_label_zh": house_chart.get("chart_profile", {}).get(
                "house_system_label_zh"
            ),
            "zodiac": influence_chart["chart_profile"].get("zodiac", "tropical"),
            "zodiacal": zodiacal_info["value"],
            "zodiac_label_zh": zodiacal_info["label_zh"],
            "reference_frame": influence_chart["chart_profile"]["reference_frame"],
            **engine_profile,
        },
        "chart": influence_chart,
        "summary": [
            f"以 {target_name} 的宫位框架投影 {source_name} 的星体。",
            f"星体数量：{len(influence_chart['planets'])}。",
            f"相位数量：{len(influence_chart['aspects'])}。",
        ],
    }


def _build_relative_influence_pair(
    inner_chart: Dict[str, Any],
    outer_chart: Dict[str, Any],
    *,
    house_system: str,
    zodiacal_info: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    return (
        _build_influence_chart_wrapper(
            role="inner",
            house_chart=inner_chart,
            source_chart=outer_chart,
            house_system=house_system,
            zodiacal_info=zodiacal_info,
        ),
        _build_influence_chart_wrapper(
            role="outer",
            house_chart=outer_chart,
            source_chart=inner_chart,
            house_system=house_system,
            zodiacal_info=zodiacal_info,
        ),
    )


def _build_marks_chart(
    composite_chart: Dict[str, Any],
    timespace_chart: Dict[str, Any],
    *,
    house_system: str,
    zodiacal_info: Dict[str, Any],
) -> Dict[str, Any]:
    engine_profile = _derive_engine_profile(
        composite_chart.get("chart_profile", {}),
        timespace_chart.get("chart_profile", {}),
    )
    composite_planets = {item["id"]: item for item in composite_chart["planets"]}
    timespace_planets = {item["id"]: item for item in timespace_chart["planets"]}
    house_cusps = (
        []
        if house_system == "whole_sign"
        else _midpoint_house_cusps(
            _house_cusp_values_from_payload(composite_chart),
            _house_cusp_values_from_payload(timespace_chart),
        )
    )
    blended_planets: List[Dict[str, Any]] = []
    for planet in PLANET_SEQUENCE:
        if planet not in composite_planets or planet not in timespace_planets:
            continue
        blended_planets.append(
            {
                "id": planet,
                "longitude": _midpoint(
                    composite_planets[planet]["longitude"],
                    timespace_planets[planet]["longitude"],
                ),
                "latitude": round(
                    (
                        composite_planets[planet]["latitude"]
                        + timespace_planets[planet]["latitude"]
                    )
                    / 2.0,
                    4,
                ),
            }
        )
    ascendant = _midpoint(
        composite_chart["angles"]["ascendant"]["longitude"],
        timespace_chart["angles"]["ascendant"]["longitude"],
    )
    midheaven = _midpoint(
        composite_chart["angles"]["midheaven"]["longitude"],
        timespace_chart["angles"]["midheaven"]["longitude"],
    )
    return _build_chart_from_positions(
        chart_type="marks",
        person_info={
            **timespace_chart["person_info"],
            "name": "关系马克斯盘",
        },
        source_planets=blended_planets,
        ascendant=ascendant,
        midheaven=midheaven,
        house_system=house_system,
        house_cusps=house_cusps or None,
        summary_prefix=f"已生成 FateBridge 马克斯盘{_precision_label_zh(engine_profile['engine_precision'])}层。",
        engine_profile=engine_profile,
        profile_overrides={
            "derivation": "composite_timespace_blend",
            "tradition": composite_chart.get("chart_profile", {}).get(
                "tradition", False
            ),
            "house_system_code": composite_chart.get("chart_profile", {}).get(
                "house_system_code"
            ),
            "house_system_label_zh": composite_chart.get("chart_profile", {}).get(
                "house_system_label_zh"
            ),
            **_relative_zodiac_profile_overrides(zodiacal_info),
        },
    )
