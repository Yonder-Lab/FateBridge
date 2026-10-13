"""Natal/chart-variant and midpoint payload assembly."""

from __future__ import annotations

from typing import Any, Dict, List

from fatebridge.core import guolao_moira
from fatebridge.core.astro.aspects import _build_aspects
from fatebridge.core.astro.birth import AstroBirthInfo
from fatebridge.core.astro.classical import (
    _build_classical_layer,
    _build_classical_patterns,
    _build_fixed_stars,
    _fortune_lot,
    _planetary_hours,
    _sect,
)
from fatebridge.core.astro.ephemeris import (
    _build_planet_states,
    _guolao_si_yu_signidx,
    _planet_set,
)
from fatebridge.core.astro.geometry import (
    _degree_in_sign,
    _julian_day,
    _midpoint,
    _nakshatra,
    _sign_name,
    _week_ruler,
    normalize_angle,
)
from fatebridge.core.astro.layout import _relative_house_layout
from fatebridge.core.astro.parts import (
    _balance,
    _build_houses,
    _build_planet_record,
    _build_thirteen_sectors,
    _summary,
)
from fatebridge.core.astro.profiles import (
    _derive_engine_profile,
    _resolve_core_chart_house_system,
    _resolve_core_chart_zodiacal_mode,
)
from fatebridge.core.astro.reference import (
    _GUOLAO_PLANET_CN,
    _TRADITIONAL_PLANET_IDS,
    ASPECTS,
    BALANCE_BASIS,
)
from fatebridge.core.astrology_tables import RULER_BY_SIGN as RULER_BY_SIGN
from fatebridge.core.astrology_tables import SIGN_LABELS_ZH as SIGN_LABELS_ZH
from fatebridge.core.calendar import BaZiCalendar


def build_core_chart_payload(
    birth_info: AstroBirthInfo,
    chart_variant: str,
    *,
    hsys: Any = None,
    zodiacal: Any = None,
) -> Dict[str, Any]:
    julian_day = _julian_day(birth_info.utc_datetime)
    day_number = julian_day - 2451543.5
    house_system_info = _resolve_core_chart_house_system(
        hsys,
        chart_variant=chart_variant,
    )
    zodiacal_info = _resolve_core_chart_zodiacal_mode(
        zodiacal,
        chart_variant=chart_variant,
    )
    sidereal = zodiacal_info["sidereal"]
    layout = _relative_house_layout(
        birth_info,
        house_system_info=house_system_info,
        zodiacal_info=zodiacal_info,
    )
    effective_ascendant = layout["ascendant"]
    effective_midheaven = layout["midheaven"]
    ayanamsha = layout["ayanamsha"] or 0.0
    house_cusps = (
        None if house_system_info["key"] == "whole_sign" else layout["house_cusps"]
    )
    (
        planet_states,
        engine_precision,
        engine_backend,
        ephemeris_model,
    ) = _build_planet_states(
        chart_variant,
        julian_day,
        day_number,
    )
    planets = [
        _build_planet_record(
            planet,
            planet_states[planet]["longitude"],
            planet_states[planet]["latitude"],
            effective_ascendant,
            house_system_info["key"],
            house_cusps=house_cusps,
            sidereal=sidereal,
            ayanamsha=ayanamsha,
            include_sector13=chart_variant == "chart13",
            include_nakshatra=chart_variant == "india_chart",
            include_su28=chart_variant == "guolao_chart",
        )
        for planet in _planet_set(chart_variant)
    ]
    aspects = _build_aspects(planets)
    house_list = _build_houses(
        effective_ascendant,
        house_system_info["key"],
        house_cusps=house_cusps,
    )
    result: Dict[str, Any] = {
        "person_info": {
            "name": birth_info.name,
            "birth_place": birth_info.birth_place,
            "birth_timezone": birth_info.timezone,
            "birth_longitude": birth_info.longitude,
            "birth_latitude": birth_info.latitude,
            "birth_datetime": birth_info.local_datetime.isoformat(),
            "utc_datetime": birth_info.utc_datetime.isoformat(),
            "true_solar": {
                "applied": birth_info.applied_true_solar,
                "correction_minutes": birth_info.solar_correction_minutes,
            },
        },
        "chart_profile": {
            "chart_type": chart_variant,
            "zodiac": zodiacal_info["zodiac"],
            "zodiacal": zodiacal_info["value"],
            "zodiac_label_zh": zodiacal_info["label_zh"],
            "ayanamsha": round(ayanamsha, 4),
            "house_system": house_system_info["key"],
            "house_system_code": house_system_info["value"],
            "house_system_label_zh": house_system_info["label_zh"],
            "house_system_source": house_system_info.get("source", "explicit"),
            "tradition": chart_variant in {"hellen_chart", "guolao_chart"},
            "engine_precision": engine_precision,
            "engine_backend": engine_backend,
            "ephemeris_model": ephemeris_model,
        },
        "angles": {
            "ascendant": {
                "longitude": round(effective_ascendant, 4),
                "sign": _sign_name(effective_ascendant),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(effective_ascendant)],
            },
            "midheaven": {
                "longitude": round(effective_midheaven, 4),
                "sign": _sign_name(effective_midheaven),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(effective_midheaven)],
            },
        },
        "houses": house_list,
        "planets": planets,
        "aspects": aspects,
        "classical": _build_classical_layer(
            planets,
            house_list,
            effective_ascendant,
            states=planet_states,
            julian_day=julian_day,
        ),
        "classical_patterns": _build_classical_patterns(
            planets, aspects, planet_states
        ),
        "planetary_hours": _planetary_hours(
            julian_day,
            birth_info.longitude,
            birth_info.latitude,
            birth_info.timezone,
        ),
        "fixed_stars": _build_fixed_stars(
            planets, effective_ascendant, effective_midheaven, julian_day
        ),
        "element_balance": _balance(planets, "element"),
        "modality_balance": _balance(planets, "modality"),
        "balance_basis": BALANCE_BASIS,
        "summary": _summary(
            chart_variant,
            planets,
            aspects,
            engine_precision=engine_precision,
        ),
    }

    if chart_variant == "chart13":
        result["thirteen_sectors"] = _build_thirteen_sectors(effective_ascendant)
    if chart_variant == "hellen_chart":
        asc_sign = _sign_name(effective_ascendant)
        result["hellenistic"] = {
            "sect": _sect(planets),
            "lot_of_fortune": _fortune_lot(planets, effective_ascendant),
            "ascendant_ruler": RULER_BY_SIGN[asc_sign],
            "angular_planets": [
                item["id"] for item in planets if item["house"] in {1, 4, 7, 10}
            ],
        }
    if chart_variant == "guolao_chart":
        si_yu = _guolao_si_yu_signidx(julian_day, sidereal, ayanamsha)
        planet_signidx = {
            _GUOLAO_PLANET_CN[item["id"]]: int(normalize_angle(item["longitude"]) // 30)
            % 12
            for item in planets
            if item["id"] in _GUOLAO_PLANET_CN
        }
        planet_signidx.update(si_yu)
        year_stem, year_branch = BaZiCalendar.get_four_pillars(
            birth_info.local_datetime, birth_info.timezone
        )["year"]
        god_signidx = guolao_moira.compute_god_signidx(year_stem, year_branch)
        moira_patterns = guolao_moira.calculate(
            {
                "asc_lon": effective_ascendant,
                "planet_signidx": planet_signidx,
                "god_signidx": god_signidx,
                "is_day": 6 <= birth_info.local_datetime.hour < 18,
                "is_winter": birth_info.local_datetime.month in (11, 12, 1),
            }
        )
        result["guolao"] = {
            "lunar_mansion_system": "su28",
            "weekday_ruler": _week_ruler(birth_info.local_datetime),
            "planetary_mansions": [
                {"id": item["id"], "su28": item["su28"]} for item in planets
            ],
            "moon_mansion": next(
                (item["su28"] for item in planets if item["id"] == "Moon"),
                None,
            ),
            "si_yu_sign_index": si_yu,
            "god_sign_index": god_signidx,
            "moira_patterns": moira_patterns,
        }
    if chart_variant == "india_chart":
        result["india"] = {
            "ayanamsha": round(ayanamsha, 4),
            "rising_nakshatra": _nakshatra(effective_ascendant),
            "moon_nakshatra": next(
                (item["nakshatra"] for item in planets if item["id"] == "Moon"),
                None,
            ),
        }
    return result


def build_midpoint_payload(
    birth_info: AstroBirthInfo,
    *,
    hsys: Any = None,
    zodiacal: Any = None,
) -> Dict[str, Any]:
    base_chart = build_core_chart_payload(
        birth_info,
        "chart",
        hsys=hsys,
        zodiacal=zodiacal,
    )
    engine_profile = _derive_engine_profile(base_chart.get("chart_profile", {}))
    midpoint_bodies = [
        item for item in base_chart["planets"] if item["id"] in _TRADITIONAL_PLANET_IDS
    ]
    midpoints: List[Dict[str, Any]] = []
    for index, first in enumerate(midpoint_bodies):
        for second in midpoint_bodies[index + 1 :]:
            longitude = _midpoint(first["longitude"], second["longitude"])
            sign = _sign_name(longitude)
            midpoints.append(
                {
                    "id_a": first["id"],
                    "id_b": second["id"],
                    "longitude": round(longitude, 4),
                    "sign": sign,
                    "sign_zh": SIGN_LABELS_ZH[sign],
                    "degree_in_sign": round(_degree_in_sign(longitude), 4),
                }
            )
    midpoint_aspects: List[Dict[str, Any]] = []
    for planet in midpoint_bodies:
        for midpoint in midpoints:
            difference = abs(planet["longitude"] - midpoint["longitude"])
            if difference > 180:
                difference = 360 - difference
            for aspect_name, exact_angle in ASPECTS:
                orb = abs(difference - exact_angle)
                if orb <= 2.0:
                    midpoint_aspects.append(
                        {
                            "planet": planet["id"],
                            "midpoint": f"{midpoint['id_a']}/{midpoint['id_b']}",
                            "aspect": aspect_name,
                            "orb": round(orb, 4),
                        }
                    )
                    break
    return {
        "chart_profile": {
            "chart_type": "germany",
            "analysis_focus": "midpoints",
            "house_system": base_chart["chart_profile"]["house_system"],
            "house_system_code": base_chart["chart_profile"].get("house_system_code"),
            "house_system_label_zh": base_chart["chart_profile"].get(
                "house_system_label_zh"
            ),
            "zodiac": base_chart["chart_profile"]["zodiac"],
            "zodiacal": base_chart["chart_profile"].get("zodiacal"),
            "zodiac_label_zh": base_chart["chart_profile"].get("zodiac_label_zh"),
            "ayanamsha": base_chart["chart_profile"].get("ayanamsha"),
            **engine_profile,
        },
        "base_chart": base_chart,
        "midpoints": midpoints,
        "midpoint_aspects": midpoint_aspects,
        "summary": [
            "已生成 FateBridge 量化盘 / 中点盘。",
            f"中点数量：{len(midpoints)}。",
            f"中点相位数量：{len(midpoint_aspects)}。",
        ],
    }
