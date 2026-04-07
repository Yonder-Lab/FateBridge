"""
High-precision western predictive astrology helpers for FateBridge.

This module layers timing techniques on top of kerykeion / Swiss Ephemeris so
FateBridge can offer returns, progressions, and time-lord style outputs on top
of the existing offline natal chart surface.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fatebridge.core.astrology import (
    AstroBirthInfo,
    RULER_BY_SIGN,
    SIGN_LABELS_ZH,
    SIGNS,
    build_astro_birth_info,
)
from fatebridge.utils.helpers import parse_timezone_name

try:
    from kerykeion import AstrologicalSubjectFactory, PlanetaryReturnFactory
except ImportError as exc:  # pragma: no cover - exercised via service error path
    AstrologicalSubjectFactory = None
    PlanetaryReturnFactory = None
    KERYKEION_IMPORT_ERROR = exc
else:
    KERYKEION_IMPORT_ERROR = None


TROPICAL_YEAR_DAYS = 365.2425
TIMING_POINT_NAMES = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Ascendant",
    "Medium_Coeli",
]
TRADITIONAL_PLANETS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
]

POINT_ATTRIBUTE_NAMES = {
    "Sun": "sun",
    "Moon": "moon",
    "Mercury": "mercury",
    "Venus": "venus",
    "Mars": "mars",
    "Jupiter": "jupiter",
    "Saturn": "saturn",
    "Ascendant": "ascendant",
    "Medium_Coeli": "medium_coeli",
}

SIGN_ABBREVIATIONS = {
    "Ari": "Aries",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Can": "Cancer",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Lib": "Libra",
    "Sco": "Scorpio",
    "Sag": "Sagittarius",
    "Cap": "Capricorn",
    "Aqu": "Aquarius",
    "Pis": "Pisces",
}

PLANET_LABELS = {
    "Sun": "太阳",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Ascendant": "上升点",
    "Medium_Coeli": "天顶",
    "North Node": "北交点",
    "South Node": "南交点",
}

HOUSE_NAME_TO_NUMBER = {
    "First_House": 1,
    "Second_House": 2,
    "Third_House": 3,
    "Fourth_House": 4,
    "Fifth_House": 5,
    "Sixth_House": 6,
    "Seventh_House": 7,
    "Eighth_House": 8,
    "Ninth_House": 9,
    "Tenth_House": 10,
    "Eleventh_House": 11,
    "Twelfth_House": 12,
}

ASPECT_DEGREES = [
    ("conjunction", "合相", 0.0),
    ("sextile", "六合", 60.0),
    ("square", "刑", 90.0),
    ("trine", "拱", 120.0),
    ("opposition", "冲", 180.0),
]

FIRDARIA_DAY_SEQUENCE = [
    ("Sun", 10),
    ("Venus", 8),
    ("Mercury", 13),
    ("Moon", 9),
    ("Saturn", 11),
    ("Jupiter", 12),
    ("Mars", 7),
    ("North Node", 3),
    ("South Node", 2),
]
FIRDARIA_NIGHT_SEQUENCE = [
    ("Moon", 9),
    ("Saturn", 11),
    ("Jupiter", 12),
    ("Mars", 7),
    ("Sun", 10),
    ("Venus", 8),
    ("Mercury", 13),
    ("North Node", 3),
    ("South Node", 2),
]

# Horosa-skill decennials constants, adapted to operate on FateBridge subjects.
DECENNIAL_START_MODE_SECT_LIGHT = "sect_light"
DECENNIAL_ORDER_ZODIACAL = "zodiacal"
DECENNIAL_ORDER_CHALDEAN = "chaldean"
DECENNIAL_DAY_METHOD_VALENS = "valens"
DECENNIAL_DAY_METHOD_HEPHAISTIO = "hephaistio"
DECENNIAL_CALENDAR_TRADITIONAL = "calendar_360"
DECENNIAL_CALENDAR_ACTUAL = "calendar_365_25"
DECENNIAL_TRADITIONAL_PLANETS = [
    "Saturn",
    "Jupiter",
    "Mars",
    "Sun",
    "Venus",
    "Mercury",
    "Moon",
]
DECENNIAL_PLANET_BASE_MONTHS = {
    "Saturn": 30,
    "Jupiter": 12,
    "Mars": 15,
    "Sun": 19,
    "Venus": 8,
    "Mercury": 20,
    "Moon": 25,
}
DECENNIAL_HEPHAISTIO_DAY_TABLE = {
    "Saturn": {
        "Saturn": 210,
        "Jupiter": 84,
        "Mars": 105,
        "Sun": 133,
        "Venus": 56,
        "Mercury": 150,
        "Moon": 175,
    },
    "Jupiter": {
        "Jupiter": 34,
        "Saturn": 85,
        "Mars": 42,
        "Sun": 54,
        "Venus": 22,
        "Mercury": 57,
        "Moon": 71,
    },
    "Mars": {
        "Mars": 52,
        "Sun": 66,
        "Venus": 28,
        "Mercury": 70,
        "Moon": 87,
        "Saturn": 105,
        "Jupiter": 42,
    },
    "Sun": {
        "Sun": 83,
        "Moon": 118,
        "Saturn": 130,
        "Jupiter": 52,
        "Mars": 64,
        "Venus": 35,
        "Mercury": 87,
    },
    "Venus": {
        "Venus": 15,
        "Sun": 36,
        "Moon": 47,
        "Saturn": 57,
        "Jupiter": 22,
        "Mars": 28,
        "Mercury": 38,
    },
    "Mercury": {
        "Mercury": 96,
        "Sun": 90,
        "Moon": 117,
        "Saturn": 141,
        "Jupiter": 56,
        "Mars": 70,
        "Venus": 36,
    },
    "Moon": {
        "Moon": 148,
        "Sun": 115,
        "Saturn": 177,
        "Jupiter": 71,
        "Mars": 87,
        "Venus": 47,
        "Mercury": 119,
    },
}
DECENNIAL_TOTAL_BASE_MONTHS = 129
DECENNIAL_TOTAL_L1_DAYS = DECENNIAL_TOTAL_BASE_MONTHS * 30
DECENNIAL_FIVE_MINUTES = 5
DECENNIAL_MINUTES_PER_DAY = 24 * 60
DECENNIAL_MINUTES_PER_MONTH = 30 * DECENNIAL_MINUTES_PER_DAY
DECENNIAL_MINUTES_PER_YEAR = 12 * DECENNIAL_MINUTES_PER_MONTH
DECENNIAL_ACTUAL_YEAR_SCALE_NUMERATOR = 1461
DECENNIAL_ACTUAL_YEAR_SCALE_DENOMINATOR = 1440


def ensure_predictive_backend_available() -> None:
    if AstrologicalSubjectFactory is None or PlanetaryReturnFactory is None:
        raise ImportError(
            "kerykeion / Swiss Ephemeris 未安装，无法启用西占推运能力。"
        ) from KERYKEION_IMPORT_ERROR


def build_predictive_birth_info(
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
) -> AstroBirthInfo:
    return build_astro_birth_info(
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        birth_latitude=birth_latitude,
        name=name,
        birth_place=birth_place,
    )


def build_analysis_datetime(
    birth_info: AstroBirthInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
) -> datetime:
    timezone_name = birth_info.timezone
    tzinfo = parse_timezone_name(timezone_name)
    if analysis_year is None or analysis_month is None or analysis_day is None:
        now = datetime.now(tz=tzinfo)
        return now.replace(
            hour=birth_info.local_datetime.hour,
            minute=birth_info.local_datetime.minute,
            second=0,
            microsecond=0,
        )
    return datetime(
        analysis_year,
        analysis_month,
        analysis_day,
        birth_info.local_datetime.hour,
        birth_info.local_datetime.minute,
        tzinfo=tzinfo,
    )


def normalize_sign_name(sign_name: str) -> str:
    return SIGN_ABBREVIATIONS.get(sign_name, sign_name)


def sign_label(sign_name: str) -> str:
    normalized = normalize_sign_name(sign_name)
    return f"{SIGN_LABELS_ZH.get(normalized, normalized)}座"


def planet_label(planet_name: str) -> str:
    return PLANET_LABELS.get(planet_name, planet_name)


def house_number(house_name: Optional[str]) -> Optional[int]:
    if house_name is None:
        return None
    return HOUSE_NAME_TO_NUMBER.get(house_name)


def house_label(house_name: Optional[str]) -> Optional[str]:
    number = house_number(house_name)
    if number is None:
        return None
    return f"第{number}宫"


def point_attribute_name(point_name: str) -> str:
    return POINT_ATTRIBUTE_NAMES.get(point_name, point_name.lower())


def point_absolute_position(subject: Any, point_name: str) -> float:
    point = getattr(subject, point_attribute_name(point_name))
    return float(point.abs_pos)


def point_to_dict(point_name: str, point: Any) -> Dict[str, Any]:
    sign_name = normalize_sign_name(getattr(point, "sign", ""))
    house_name = getattr(point, "house", None)
    return {
        "point": point_name,
        "point_label": planet_label(point_name),
        "sign": sign_name,
        "sign_label": sign_label(sign_name),
        "degree": round(float(getattr(point, "position", 0.0)), 4),
        "absolute_degree": round(float(getattr(point, "abs_pos", 0.0)), 4),
        "house": house_number(house_name),
        "house_label": house_label(house_name),
        "retrograde": bool(getattr(point, "retrograde", False)),
    }


def longitude_to_point_dict(point_name: str, absolute_degree: float) -> Dict[str, Any]:
    normalized_degree = absolute_degree % 360.0
    sign_index = int(normalized_degree // 30)
    sign_name = SIGNS[sign_index]
    return {
        "point": point_name,
        "point_label": planet_label(point_name),
        "sign": sign_name,
        "sign_label": sign_label(sign_name),
        "degree": round(normalized_degree % 30, 4),
        "absolute_degree": round(normalized_degree, 4),
    }


def build_subject(
    *,
    name: str,
    local_datetime: datetime,
    longitude: float,
    latitude: float,
    timezone_name: str,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Any:
    ensure_predictive_backend_available()
    return AstrologicalSubjectFactory.from_birth_data(
        name=name,
        year=local_datetime.year,
        month=local_datetime.month,
        day=local_datetime.day,
        hour=local_datetime.hour,
        minute=local_datetime.minute,
        seconds=local_datetime.second,
        lng=longitude,
        lat=latitude,
        tz_str=timezone_name,
        online=False,
        houses_system_identifier=house_system,
        zodiac_type=zodiac_type,
    )


def build_natal_subject(
    birth_info: AstroBirthInfo,
    *,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Any:
    return build_subject(
        name=birth_info.name,
        local_datetime=birth_info.local_datetime,
        longitude=birth_info.longitude,
        latitude=birth_info.latitude,
        timezone_name=birth_info.timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )


def determine_sect(subject: Any) -> str:
    sun_house = house_number(getattr(subject.sun, "house", None))
    if sun_house is not None and sun_house >= 7:
        return "day"
    return "night"


def sect_label(sect: str) -> str:
    return "日盘" if sect == "day" else "夜盘"


def calculate_age_years(
    birth_info: AstroBirthInfo,
    analysis_datetime: datetime,
) -> float:
    birth_utc = birth_info.utc_datetime
    analysis_utc = analysis_datetime.astimezone(parse_timezone_name("UTC"))
    delta = analysis_utc - birth_utc
    return delta.total_seconds() / (TROPICAL_YEAR_DAYS * 86400.0)


def calculate_age_years_int(
    birth_info: AstroBirthInfo,
    analysis_datetime: datetime,
) -> int:
    years = analysis_datetime.year - birth_info.local_datetime.year
    birthday_this_year = birth_info.local_datetime.replace(year=analysis_datetime.year)
    if analysis_datetime < birthday_this_year:
        years -= 1
    return years


def extract_reference_points(subject: Any) -> Dict[str, Dict[str, Any]]:
    result = {}
    for point_name in TIMING_POINT_NAMES:
        result[point_name.lower()] = point_to_dict(
            point_name,
            getattr(subject, point_attribute_name(point_name)),
        )
    return result


def extract_reference_longitudes(subject: Any) -> Dict[str, float]:
    return {
        point_name: point_absolute_position(subject, point_name)
        for point_name in TIMING_POINT_NAMES
    }


def build_return_payload(
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    return_longitude: float,
    return_latitude: float,
    return_timezone: str,
) -> Dict[str, Any]:
    factory = PlanetaryReturnFactory(
        natal_subject,
        lng=return_longitude,
        lat=return_latitude,
        tz_str=return_timezone,
        online=False,
    )
    solar_return = factory.next_return_from_year(analysis_datetime.year, "Solar")
    lunar_return = factory.next_return_from_month_and_year(
        analysis_datetime.year,
        analysis_datetime.month,
        "Lunar",
    )
    return {
        "solar_return": {
            "return_datetime": solar_return.iso_formatted_local_datetime,
            "sun": point_to_dict("Sun", solar_return.sun),
            "moon": point_to_dict("Moon", solar_return.moon),
            "ascendant": point_to_dict("Ascendant", solar_return.ascendant),
            "medium_coeli": point_to_dict(
                "Medium_Coeli",
                solar_return.medium_coeli,
            ),
        },
        "lunar_return": {
            "return_datetime": lunar_return.iso_formatted_local_datetime,
            "sun": point_to_dict("Sun", lunar_return.sun),
            "moon": point_to_dict("Moon", lunar_return.moon),
            "ascendant": point_to_dict("Ascendant", lunar_return.ascendant),
            "medium_coeli": point_to_dict(
                "Medium_Coeli",
                lunar_return.medium_coeli,
            ),
        },
    }


def build_secondary_progression_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Dict[str, Any]:
    age_years = calculate_age_years(birth_info, analysis_datetime)
    progressed_utc = birth_info.utc_datetime + timedelta(days=age_years)
    progressed_local = progressed_utc.astimezone(parse_timezone_name(birth_info.timezone))
    progressed_subject = build_subject(
        name=f"{birth_info.name}-progressed",
        local_datetime=progressed_local,
        longitude=birth_info.longitude,
        latitude=birth_info.latitude,
        timezone_name=birth_info.timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    hits = collect_aspect_hits(
        source_longitudes=extract_reference_longitudes(progressed_subject),
        target_longitudes=extract_reference_longitudes(natal_subject),
        orb_limit=1.5,
    )
    return {
        "progressed_datetime": progressed_local.isoformat(),
        "sun": point_to_dict("Sun", progressed_subject.sun),
        "moon": point_to_dict("Moon", progressed_subject.moon),
        "ascendant": point_to_dict("Ascendant", progressed_subject.ascendant),
        "medium_coeli": point_to_dict(
            "Medium_Coeli",
            progressed_subject.medium_coeli,
        ),
        "hits": hits[:8],
        "subject": progressed_subject,
    }


def build_solar_arc_payload(
    natal_subject: Any,
    progressed_subject: Any,
) -> Dict[str, Any]:
    natal_longitudes = extract_reference_longitudes(natal_subject)
    arc_degrees = (
        point_absolute_position(progressed_subject, "Sun")
        - point_absolute_position(natal_subject, "Sun")
    ) % 360.0
    directed_points = {}
    for point_name, longitude in natal_longitudes.items():
        directed_points[point_name] = (longitude + arc_degrees) % 360.0
    hits = collect_aspect_hits(
        source_longitudes=directed_points,
        target_longitudes=natal_longitudes,
        orb_limit=1.5,
    )
    return {
        "arc_degrees": round(arc_degrees, 4),
        "sun": longitude_to_point_dict("Sun", directed_points["Sun"]),
        "moon": longitude_to_point_dict("Moon", directed_points["Moon"]),
        "ascendant": longitude_to_point_dict(
            "Ascendant",
            directed_points["Ascendant"],
        ),
        "medium_coeli": longitude_to_point_dict(
            "Medium_Coeli",
            directed_points["Medium_Coeli"],
        ),
        "hits": hits[:8],
    }


def collect_aspect_hits(
    *,
    source_longitudes: Dict[str, float],
    target_longitudes: Dict[str, float],
    orb_limit: float = 1.5,
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for source_name, source_longitude in source_longitudes.items():
        for target_name, target_longitude in target_longitudes.items():
            difference = abs(
                ((source_longitude - target_longitude + 180.0) % 360.0) - 180.0
            )
            for aspect_key, aspect_label_text, aspect_degree in ASPECT_DEGREES:
                orb = abs(difference - aspect_degree)
                if orb <= orb_limit:
                    hits.append(
                        {
                            "source": source_name,
                            "source_label": planet_label(source_name),
                            "target": target_name,
                            "target_label": planet_label(target_name),
                            "aspect": aspect_key,
                            "aspect_label": aspect_label_text,
                            "orb": round(orb, 4),
                        }
                    )
    hits.sort(key=lambda item: item["orb"])
    return hits


def build_annual_profection_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
) -> Dict[str, Any]:
    age_years_int = calculate_age_years_int(birth_info, analysis_datetime)
    asc_sign = normalize_sign_name(natal_subject.ascendant.sign)
    asc_index = SIGNS.index(asc_sign)
    activated_house = (age_years_int % 12) + 1
    activated_sign = SIGNS[(asc_index + activated_house - 1) % 12]
    lord = RULER_BY_SIGN[activated_sign]

    birthday_this_year = birth_info.local_datetime.replace(year=analysis_datetime.year)
    if analysis_datetime < birthday_this_year:
        last_birthday = birthday_this_year.replace(year=analysis_datetime.year - 1)
    else:
        last_birthday = birthday_this_year

    months_since_birthday = (
        (analysis_datetime.year - last_birthday.year) * 12
        + (analysis_datetime.month - last_birthday.month)
    )
    if analysis_datetime.day < last_birthday.day:
        months_since_birthday -= 1
    months_since_birthday = max(0, months_since_birthday)
    monthly_house = ((activated_house - 1 + months_since_birthday) % 12) + 1
    monthly_sign = SIGNS[(asc_index + monthly_house - 1) % 12]

    return {
        "activated_house": activated_house,
        "activated_sign": activated_sign,
        "activated_sign_label": sign_label(activated_sign),
        "lord": lord,
        "lord_label": planet_label(lord),
        "monthly_house": monthly_house,
        "monthly_sign": monthly_sign,
        "monthly_sign_label": sign_label(monthly_sign),
    }


def build_firdaria_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
) -> Dict[str, Any]:
    sect = determine_sect(natal_subject)
    sequence = FIRDARIA_DAY_SEQUENCE if sect == "day" else FIRDARIA_NIGHT_SEQUENCE
    sub_planet_order = [planet for planet, _ in sequence if "Node" not in planet]

    timeline = []
    cursor = birth_info.local_datetime
    current_major = None
    current_sub = None

    while cursor <= analysis_datetime + timedelta(days=90 * TROPICAL_YEAR_DAYS):
        for planet, years in sequence:
            start = cursor
            end = start + timedelta(days=years * TROPICAL_YEAR_DAYS)
            main_period = {
                "planet": planet,
                "planet_label": planet_label(planet),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "years": years,
                "subperiods": [],
            }

            if "Node" not in planet:
                order = (
                    sub_planet_order[sub_planet_order.index(planet):]
                    + sub_planet_order[: sub_planet_order.index(planet)]
                )
                sub_years = years / 7.0
                sub_cursor = start
                for sub_planet in order:
                    sub_end = sub_cursor + timedelta(days=sub_years * TROPICAL_YEAR_DAYS)
                    sub_period = {
                        "planet": sub_planet,
                        "planet_label": planet_label(sub_planet),
                        "start": sub_cursor.isoformat(),
                        "end": sub_end.isoformat(),
                    }
                    main_period["subperiods"].append(sub_period)
                    if sub_cursor <= analysis_datetime < sub_end:
                        current_sub = sub_period
                    sub_cursor = sub_end

            if start <= analysis_datetime < end:
                current_major = main_period

            timeline.append(main_period)
            cursor = end
            if cursor > analysis_datetime + timedelta(days=90 * TROPICAL_YEAR_DAYS):
                break
        else:
            continue
        break

    return {
        "sect": sect,
        "sect_label": sect_label(sect),
        "current_major": current_major,
        "current_sub": current_sub,
        "timeline": timeline[:12],
    }


def _rotate_items(items: List[str], start_value: Optional[str]) -> List[str]:
    if not items or not start_value or start_value not in items:
        return list(items)
    index = items.index(start_value)
    return items[index:] + items[:index]


def _build_decennial_zodiacal_order(subject: Any) -> List[str]:
    ranked = []
    for index, planet in enumerate(DECENNIAL_TRADITIONAL_PLANETS):
        longitude = point_absolute_position(subject, planet)
        ranked.append((longitude, index, planet))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [planet for _, _, planet in ranked]


def resolve_decennial_start_planet(subject: Any, start_mode: Optional[str]) -> str:
    if start_mode and start_mode != DECENNIAL_START_MODE_SECT_LIGHT:
        if start_mode in DECENNIAL_TRADITIONAL_PLANETS:
            return start_mode
    return "Sun" if determine_sect(subject) == "day" else "Moon"


def get_decennial_order(subject: Any, start_planet: str, order_type: Optional[str]) -> List[str]:
    if order_type == DECENNIAL_ORDER_CHALDEAN:
        base = list(DECENNIAL_TRADITIONAL_PLANETS)
    else:
        base = _build_decennial_zodiacal_order(subject)
    return _rotate_items(base, start_planet)


def _rounded_distribution(
    total_value: float,
    order: List[str],
    round_unit: int,
    preserve_last: bool = True,
) -> List[Dict[str, Any]]:
    segments = []
    consumed = 0.0
    for index, planet in enumerate(order):
        exact = (
            total_value
            * DECENNIAL_PLANET_BASE_MONTHS[planet]
            / DECENNIAL_TOTAL_BASE_MONTHS
        )
        value = exact
        if index == len(order) - 1 and preserve_last:
            value = total_value - consumed
        elif round_unit > 0:
            value = round(exact / round_unit) * round_unit
        value = max(0.0, value)
        consumed += value
        segments.append({"planet": planet, "value": value})
    return segments


def _minutes_from_level_three(
    total_days: float,
    day_method: Optional[str],
    month_lord: str,
    order: List[str],
) -> List[Dict[str, Any]]:
    if day_method == DECENNIAL_DAY_METHOD_HEPHAISTIO:
        table = DECENNIAL_HEPHAISTIO_DAY_TABLE.get(month_lord)
        if table:
            return [
                {
                    "planet": planet,
                    "value": table.get(planet, 0) * DECENNIAL_MINUTES_PER_DAY,
                }
                for planet in order
            ]
    return _rounded_distribution(
        total_days * DECENNIAL_MINUTES_PER_DAY,
        order,
        DECENNIAL_FIVE_MINUTES,
    )


def _minutes_from_level_four(
    total_minutes: float,
    order: List[str],
) -> List[Dict[str, Any]]:
    return _rounded_distribution(total_minutes, order, 1)


def _scale_nominal_minutes(total_minutes: float, calendar_type: Optional[str]) -> int:
    normalized = max(0, round(float(total_minutes or 0)))
    if calendar_type != DECENNIAL_CALENDAR_ACTUAL:
        return normalized
    return round(
        normalized
        * DECENNIAL_ACTUAL_YEAR_SCALE_NUMERATOR
        / DECENNIAL_ACTUAL_YEAR_SCALE_DENOMINATOR
    )


def _scale_nominal_segments(
    segments: List[Dict[str, Any]],
    calendar_type: Optional[str],
    round_unit: int = 1,
) -> List[Dict[str, Any]]:
    if calendar_type != DECENNIAL_CALENDAR_ACTUAL:
        return [
            {
                "planet": item["planet"],
                "value": max(0, round(float(item["value"] or 0))),
            }
            for item in segments
        ]

    unit = round_unit if round_unit > 0 else 1
    total_nominal = sum(max(0.0, float(item["value"] or 0)) for item in segments)
    total_scaled = round(_scale_nominal_minutes(total_nominal, calendar_type) / unit) * unit
    scaled = []
    consumed = 0
    cumulative_exact = 0.0
    for index, item in enumerate(segments):
        nominal_value = max(0.0, float(item["value"] or 0))
        cumulative_exact += (
            nominal_value
            * DECENNIAL_ACTUAL_YEAR_SCALE_NUMERATOR
            / DECENNIAL_ACTUAL_YEAR_SCALE_DENOMINATOR
        )
        if index == len(segments) - 1:
            value = total_scaled - consumed
        else:
            value = round(cumulative_exact / unit) * unit - consumed
        value = max(0, value)
        consumed += value
        scaled.append({"planet": item["planet"], "value": value})
    return scaled


def _format_nominal_offset(total_minutes: int, level: int) -> str:
    minutes = max(0, round(total_minutes or 0))
    years, minutes = divmod(minutes, DECENNIAL_MINUTES_PER_YEAR)
    months, minutes = divmod(minutes, DECENNIAL_MINUTES_PER_MONTH)
    days, minutes = divmod(minutes, DECENNIAL_MINUTES_PER_DAY)
    hours, minutes = divmod(minutes, 60)
    if level >= 4:
        prefix = ""
        if years:
            prefix += f"{years}年"
        if months:
            prefix += f"{months}个月"
        if days:
            prefix += f"{days}天"
        return f"{prefix or '0天'} {hours:02d}:{minutes:02d}"
    if level == 3:
        parts = []
        if years:
            parts.append(f"{years}年")
        if months:
            parts.append(f"{months}个月")
        if days or not parts:
            parts.append(f"{days}天")
        return "".join(parts)
    parts = []
    if years:
        parts.append(f"{years}年")
    if months or not parts:
        parts.append(f"{months}个月")
    return "".join(parts)


def _format_nominal_range(start_offset_minutes: int, end_offset_minutes: int, level: int) -> str:
    return (
        f"{_format_nominal_offset(start_offset_minutes, level)} - "
        f"{_format_nominal_offset(end_offset_minutes, level)}"
    )


def _build_decennial_node(
    level: int,
    key: str,
    planet: str,
    start_moment: datetime,
    end_moment: datetime,
    analysis_datetime: datetime,
    sublevel: List[Dict[str, Any]],
    start_offset_minutes: int,
    end_offset_minutes: int,
) -> Dict[str, Any]:
    active = start_moment <= analysis_datetime < end_moment
    return {
        "key": key,
        "level": level,
        "planet": planet,
        "planet_label": planet_label(planet),
        "date": (
            f"{start_moment.strftime('%Y-%m-%d')} - {end_moment.strftime('%Y-%m-%d')}"
        ),
        "nominal": _format_nominal_range(start_offset_minutes, end_offset_minutes, level),
        "start": start_moment.isoformat(),
        "end": end_moment.isoformat(),
        "active": active,
        "sublevel": sublevel,
        "start_offset_minutes": start_offset_minutes,
        "end_offset_minutes": end_offset_minutes,
    }


def _build_decennial_level_four(
    level_three_node: Dict[str, Any],
    base_order: List[str],
    analysis_datetime: datetime,
    calendar_type: Optional[str],
) -> List[Dict[str, Any]]:
    order = _rotate_items(base_order, level_three_node["planet"])
    nominal_segments = _minutes_from_level_four(level_three_node["nominal_minutes"], order)
    actual_segments = _scale_nominal_segments(nominal_segments, calendar_type, 1)
    data = []
    cursor = level_three_node["start_moment"]
    cursor_offset = level_three_node["start_offset_minutes"]
    for index, nominal_item in enumerate(nominal_segments):
        actual_item = actual_segments[index]
        next_moment = cursor + timedelta(minutes=actual_item["value"])
        next_offset = cursor_offset + round(nominal_item["value"])
        data.append(
            _build_decennial_node(
                4,
                f"{level_three_node['key']}_l4_{index}",
                actual_item["planet"],
                cursor,
                next_moment,
                analysis_datetime,
                [],
                cursor_offset,
                next_offset,
            )
        )
        cursor = next_moment
        cursor_offset = next_offset
    return data


def _build_decennial_level_three(
    level_two_node: Dict[str, Any],
    base_order: List[str],
    day_method: Optional[str],
    analysis_datetime: datetime,
    calendar_type: Optional[str],
) -> List[Dict[str, Any]]:
    order = _rotate_items(base_order, level_two_node["planet"])
    nominal_segments = _minutes_from_level_three(
        level_two_node["nominal_days"],
        day_method,
        level_two_node["planet"],
        order,
    )
    actual_segments = _scale_nominal_segments(nominal_segments, calendar_type, 1)
    data = []
    cursor = level_two_node["start_moment"]
    cursor_offset = level_two_node["start_offset_minutes"]
    for index, nominal_item in enumerate(nominal_segments):
        actual_item = actual_segments[index]
        next_moment = cursor + timedelta(minutes=actual_item["value"])
        meta = {
            "key": f"{level_two_node['key']}_l3_{index}",
            "planet": actual_item["planet"],
            "start_moment": cursor,
            "end_moment": next_moment,
            "nominal_minutes": round(nominal_item["value"]),
            "start_offset_minutes": cursor_offset,
            "end_offset_minutes": cursor_offset + round(nominal_item["value"]),
        }
        sublevel = _build_decennial_level_four(
            meta,
            base_order,
            analysis_datetime,
            calendar_type,
        )
        data.append(
            _build_decennial_node(
                3,
                meta["key"],
                meta["planet"],
                meta["start_moment"],
                meta["end_moment"],
                analysis_datetime,
                sublevel,
                meta["start_offset_minutes"],
                meta["end_offset_minutes"],
            )
        )
        cursor = next_moment
        cursor_offset = meta["end_offset_minutes"]
    return data


def _build_decennial_level_two(
    level_one_node: Dict[str, Any],
    base_order: List[str],
    day_method: Optional[str],
    analysis_datetime: datetime,
    calendar_type: Optional[str],
) -> List[Dict[str, Any]]:
    order = _rotate_items(base_order, level_one_node["planet"])
    nominal_segments = [
        {
            "planet": planet,
            "value": DECENNIAL_PLANET_BASE_MONTHS[planet] * DECENNIAL_MINUTES_PER_MONTH,
        }
        for planet in order
    ]
    actual_segments = _scale_nominal_segments(nominal_segments, calendar_type, 1)
    data = []
    cursor = level_one_node["start_moment"]
    cursor_offset = level_one_node["start_offset_minutes"]
    for index, nominal_item in enumerate(nominal_segments):
        actual_item = actual_segments[index]
        next_moment = cursor + timedelta(minutes=actual_item["value"])
        meta = {
            "key": f"{level_one_node['key']}_l2_{index}",
            "planet": nominal_item["planet"],
            "nominal_days": round(nominal_item["value"]) / DECENNIAL_MINUTES_PER_DAY,
            "start_moment": cursor,
            "end_moment": next_moment,
            "start_offset_minutes": cursor_offset,
            "end_offset_minutes": cursor_offset + round(nominal_item["value"]),
        }
        sublevel = _build_decennial_level_three(
            meta,
            base_order,
            day_method,
            analysis_datetime,
            calendar_type,
        )
        data.append(
            _build_decennial_node(
                2,
                meta["key"],
                meta["planet"],
                meta["start_moment"],
                meta["end_moment"],
                analysis_datetime,
                sublevel,
                meta["start_offset_minutes"],
                meta["end_offset_minutes"],
            )
        )
        cursor = next_moment
        cursor_offset = meta["end_offset_minutes"]
    return data


def _resolve_decennial_count(
    birth_moment: datetime,
    analysis_datetime: datetime,
    calendar_type: Optional[str],
) -> int:
    age_minutes = max(0.0, (analysis_datetime - birth_moment).total_seconds() / 60.0)
    l1_minutes = _scale_nominal_minutes(
        DECENNIAL_TOTAL_L1_DAYS * DECENNIAL_MINUTES_PER_DAY,
        calendar_type,
    )
    return max(7, int((age_minutes + l1_minutes - 1) // l1_minutes) + 2)


def build_decennials_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    start_mode: str = DECENNIAL_START_MODE_SECT_LIGHT,
    order_type: str = DECENNIAL_ORDER_ZODIACAL,
    day_method: str = DECENNIAL_DAY_METHOD_VALENS,
    calendar_type: str = DECENNIAL_CALENDAR_TRADITIONAL,
) -> Dict[str, Any]:
    birth_moment = birth_info.local_datetime
    start_planet = resolve_decennial_start_planet(natal_subject, start_mode)
    base_order = get_decennial_order(natal_subject, start_planet, order_type)
    count = _resolve_decennial_count(birth_moment, analysis_datetime, calendar_type)
    data = []
    l1_nominal_minutes = DECENNIAL_TOTAL_L1_DAYS * DECENNIAL_MINUTES_PER_DAY
    l1_actual_minutes = _scale_nominal_minutes(l1_nominal_minutes, calendar_type)
    cursor = birth_moment
    for index in range(count):
        planet = base_order[index % len(base_order)]
        start_moment = cursor
        end_moment = start_moment + timedelta(minutes=l1_actual_minutes)
        start_offset = l1_nominal_minutes * index
        end_offset = start_offset + l1_nominal_minutes
        meta = {
            "key": f"l1_{index}",
            "planet": planet,
            "start_moment": start_moment,
            "end_moment": end_moment,
            "start_offset_minutes": start_offset,
            "end_offset_minutes": end_offset,
        }
        sublevel = _build_decennial_level_two(
            meta,
            base_order,
            day_method,
            analysis_datetime,
            calendar_type,
        )
        data.append(
            _build_decennial_node(
                1,
                meta["key"],
                planet,
                start_moment,
                end_moment,
                analysis_datetime,
                sublevel,
                start_offset,
                end_offset,
            )
        )
        cursor = end_moment

    current_level_1 = next((node for node in data if node["active"]), None)
    current_level_2 = None
    current_level_3 = None
    if current_level_1:
        current_level_2 = next(
            (node for node in current_level_1["sublevel"] if node["active"]),
            None,
        )
        if current_level_2:
            current_level_3 = next(
                (node for node in current_level_2["sublevel"] if node["active"]),
                None,
            )

    return {
        "resolved_start_planet": start_planet,
        "resolved_start_planet_label": planet_label(start_planet),
        "base_order": base_order,
        "current_level_1": current_level_1,
        "current_level_2": current_level_2,
        "current_level_3": current_level_3,
        "timeline": data[:7],
    }


def build_western_timing_payload(
    birth_info: AstroBirthInfo,
    *,
    analysis_datetime: datetime,
    return_longitude: Optional[float] = None,
    return_latitude: Optional[float] = None,
    return_timezone: Optional[str] = None,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Dict[str, Any]:
    natal_subject = build_natal_subject(
        birth_info,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    natal_reference = extract_reference_points(natal_subject)
    sect = determine_sect(natal_subject)
    natal_reference["sect"] = {"key": sect, "label": sect_label(sect)}

    effective_return_longitude = (
        birth_info.longitude if return_longitude is None else return_longitude
    )
    effective_return_latitude = (
        birth_info.latitude if return_latitude is None else return_latitude
    )
    effective_return_timezone = return_timezone or birth_info.timezone

    returns_payload = build_return_payload(
        natal_subject,
        analysis_datetime=analysis_datetime,
        return_longitude=effective_return_longitude,
        return_latitude=effective_return_latitude,
        return_timezone=effective_return_timezone,
    )
    progression_payload = build_secondary_progression_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    progressed_subject = progression_payload.pop("subject")
    solar_arc_payload = build_solar_arc_payload(natal_subject, progressed_subject)
    profection_payload = build_annual_profection_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
    )
    firdaria_payload = build_firdaria_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
    )
    decennials_payload = build_decennials_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
    )

    age_years = calculate_age_years(birth_info, analysis_datetime)
    summary = (
        f"{analysis_datetime.strftime('%Y-%m-%d')} 西占时运："
        f"太阳返照 {returns_payload['solar_return']['return_datetime']}，"
        f"月返 {returns_payload['lunar_return']['return_datetime']}，"
        f"年小限落第{profection_payload['activated_house']}宫"
        f"{profection_payload['activated_sign_label']}，"
        f"法达 {firdaria_payload['current_major']['planet_label']}"
        f"/{firdaria_payload['current_sub']['planet_label']}，"
        f"太阳弧 {solar_arc_payload['arc_degrees']:.2f}°。"
    )

    return {
        "analysis_type": "西占推运与返照分析",
        "analysis_context": {
            "name": birth_info.name,
            "birth_place": birth_info.birth_place,
            "birth_datetime": birth_info.local_datetime.isoformat(),
            "analysis_datetime": analysis_datetime.isoformat(),
            "age_years": round(age_years, 4),
            "house_system": house_system,
            "zodiac_type": zodiac_type,
            "return_location": {
                "longitude": effective_return_longitude,
                "latitude": effective_return_latitude,
                "timezone": effective_return_timezone,
            },
        },
        "natal_reference": natal_reference,
        "returns": returns_payload,
        "directions": {
            "secondary_progression": progression_payload,
            "solar_arc": solar_arc_payload,
        },
        "time_lords": {
            "annual_profection": profection_payload,
            "firdaria": firdaria_payload,
            "decennials": decennials_payload,
        },
        "summary": summary,
    }
