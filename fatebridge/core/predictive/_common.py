"""西占推运共享底座：导入、常量与跨技法工具函数。"""

from __future__ import annotations

import math
from calendar import monthrange
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

import pytz

from fatebridge.core.astrology import (
    RULER_BY_SIGN,
    SIGN_LABELS_ZH,
    SIGNS,
    AstroBirthInfo,
    build_astro_birth_info,
    normalize_angle,
)
from fatebridge.core.ephemeris_runtime import swe
from fatebridge.utils.helpers import parse_timezone_name

KERYKEION_IMPORT_ERROR: Optional[ImportError] = None
try:
    from kerykeion import AstrologicalSubjectFactory, PlanetaryReturnFactory
except ImportError as exc:  # pragma: no cover - exercised via service error path
    # Optional dependency: rebind imported classes to None so callers can detect
    # absence via KERYKEION_IMPORT_ERROR. mypy cannot model rebinding an imported
    # class to None, so these assignments are explicitly ignored.
    AstrologicalSubjectFactory = None  # type: ignore[assignment,misc]
    PlanetaryReturnFactory = None  # type: ignore[assignment,misc]
    KERYKEION_IMPORT_ERROR = exc


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
TRANSIT_POINT_NAMES = [
    *TIMING_POINT_NAMES,
    "Uranus",
    "Neptune",
    "Pluto",
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
    "Uranus": "uranus",
    "Neptune": "neptune",
    "Pluto": "pluto",
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
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
    "Ascendant": "上升点",
    "Medium_Coeli": "天顶",
    "North Node": "北交点",
    "South Node": "南交点",
    "Fortune": "幸运点",
    "Spirit": "精神点",
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
SWISSEPH_PLANET_IDS = {
    "Sun": 0,
    "Moon": 1,
    "Mercury": 2,
    "Venus": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
}
EGYPTIAN_BOUNDS_BY_SIGN = {
    "Aries": [
        ("Jupiter", 0.0, 6.0),
        ("Venus", 6.0, 14.0),
        ("Mercury", 14.0, 21.0),
        ("Mars", 21.0, 26.0),
        ("Saturn", 26.0, 30.0),
    ],
    "Taurus": [
        ("Venus", 0.0, 8.0),
        ("Mercury", 8.0, 14.0),
        ("Jupiter", 14.0, 22.0),
        ("Saturn", 22.0, 27.0),
        ("Mars", 27.0, 30.0),
    ],
    "Gemini": [
        ("Mercury", 0.0, 6.0),
        ("Jupiter", 6.0, 12.0),
        ("Venus", 12.0, 17.0),
        ("Mars", 17.0, 24.0),
        ("Saturn", 24.0, 30.0),
    ],
    "Cancer": [
        ("Mars", 0.0, 7.0),
        ("Venus", 7.0, 13.0),
        ("Mercury", 13.0, 19.0),
        ("Jupiter", 19.0, 26.0),
        ("Saturn", 26.0, 30.0),
    ],
    "Leo": [
        ("Saturn", 0.0, 6.0),
        ("Mercury", 6.0, 13.0),
        ("Venus", 13.0, 19.0),
        ("Jupiter", 19.0, 25.0),
        ("Mars", 25.0, 30.0),
    ],
    "Virgo": [
        ("Mercury", 0.0, 7.0),
        ("Venus", 7.0, 17.0),
        ("Jupiter", 17.0, 21.0),
        ("Mars", 21.0, 28.0),
        ("Saturn", 28.0, 30.0),
    ],
    "Libra": [
        ("Saturn", 0.0, 6.0),
        ("Mercury", 6.0, 14.0),
        ("Jupiter", 14.0, 21.0),
        ("Venus", 21.0, 28.0),
        ("Mars", 28.0, 30.0),
    ],
    "Scorpio": [
        ("Mars", 0.0, 7.0),
        ("Venus", 7.0, 11.0),
        ("Mercury", 11.0, 19.0),
        ("Jupiter", 19.0, 24.0),
        ("Saturn", 24.0, 30.0),
    ],
    "Sagittarius": [
        ("Jupiter", 0.0, 12.0),
        ("Venus", 12.0, 17.0),
        ("Mercury", 17.0, 21.0),
        ("Saturn", 21.0, 26.0),
        ("Mars", 26.0, 30.0),
    ],
    "Capricorn": [
        ("Mercury", 0.0, 7.0),
        ("Jupiter", 7.0, 14.0),
        ("Venus", 14.0, 22.0),
        ("Saturn", 22.0, 26.0),
        ("Mars", 26.0, 30.0),
    ],
    "Aquarius": [
        ("Mercury", 0.0, 7.0),
        ("Venus", 7.0, 13.0),
        ("Jupiter", 13.0, 20.0),
        ("Mars", 20.0, 25.0),
        ("Saturn", 25.0, 30.0),
    ],
    "Pisces": [
        ("Venus", 0.0, 12.0),
        ("Jupiter", 12.0, 16.0),
        ("Mercury", 16.0, 19.0),
        ("Mars", 19.0, 28.0),
        ("Saturn", 28.0, 30.0),
    ],
}

LOT_LABELS = {
    "lot_of_fortune": "幸运点",
    "lot_of_spirit": "精神点",
}
LOT_POINT_NAMES = {
    "lot_of_fortune": "Fortune",
    "lot_of_spirit": "Spirit",
}
LOT_KEY_BY_POINT_NAME = {value: key for key, value in LOT_POINT_NAMES.items()}
ZR_PHASE_LABELS = {
    "angular": "角宫",
    "succedent": "续宫",
    "cadent": "衰宫",
}


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


def rebuild_local_datetime(moment: datetime, timezone_name: str) -> datetime:
    # Predictive charts use the target local wall clock at the directed place.
    tzinfo = parse_timezone_name(timezone_name)
    return datetime(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second,
        moment.microsecond,
        tzinfo=tzinfo,
    )


def resolve_local_birthday_anniversary(
    birth_local_datetime: datetime,
    target_year: int,
    *,
    tzinfo: Optional[Any] = None,
) -> datetime:
    target_day = min(
        birth_local_datetime.day,
        monthrange(target_year, birth_local_datetime.month)[1],
    )
    return datetime(
        target_year,
        birth_local_datetime.month,
        target_day,
        birth_local_datetime.hour,
        birth_local_datetime.minute,
        birth_local_datetime.second,
        birth_local_datetime.microsecond,
        tzinfo=tzinfo or birth_local_datetime.tzinfo,
    )


def add_months(moment: datetime, months: int) -> datetime:
    month_index = (moment.month - 1) + months
    target_year = moment.year + (month_index // 12)
    target_month = (month_index % 12) + 1
    target_day = min(moment.day, monthrange(target_year, target_month)[1])
    return datetime(
        target_year,
        target_month,
        target_day,
        moment.hour,
        moment.minute,
        moment.second,
        moment.microsecond,
        tzinfo=moment.tzinfo,
    )


def normalize_sign_name(sign_name: str) -> str:
    return SIGN_ABBREVIATIONS.get(sign_name, sign_name)


def sign_label(sign_name: str) -> str:
    normalized = normalize_sign_name(sign_name)
    return f"{SIGN_LABELS_ZH.get(normalized, normalized)}座"


def resolve_egyptian_bound(sign_name: str, degree_in_sign: float) -> Dict[str, Any]:
    normalized_sign = normalize_sign_name(sign_name)
    normalized_degree = max(0.0, min(float(degree_in_sign), 29.9999))
    for lord, start_degree, end_degree in EGYPTIAN_BOUNDS_BY_SIGN[normalized_sign]:
        if start_degree <= normalized_degree < end_degree:
            return {
                "bound_lord": lord,
                "bound_lord_label": planet_label(lord),
                "segment_start_degree": round(start_degree, 4),
                "segment_end_degree": round(end_degree, 4),
            }
    fallback_lord, start_degree, end_degree = EGYPTIAN_BOUNDS_BY_SIGN[normalized_sign][
        -1
    ]
    return {
        "bound_lord": fallback_lord,
        "bound_lord_label": planet_label(fallback_lord),
        "segment_start_degree": round(start_degree, 4),
        "segment_end_degree": round(end_degree, 4),
    }


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


def next_sign(sign_name: str) -> str:
    return SIGNS[(SIGNS.index(sign_name) + 1) % 12]


def opposite_sign(sign_name: str) -> str:
    return SIGNS[(SIGNS.index(sign_name) + 6) % 12]


def classify_releasing_phase(sign_name: str, root_sign: str) -> Dict[str, Any]:
    relative_index = ((SIGNS.index(sign_name) - SIGNS.index(root_sign)) % 12) + 1
    if relative_index in {1, 4, 7, 10}:
        phase = "angular"
    elif relative_index in {2, 5, 8, 11}:
        phase = "succedent"
    else:
        phase = "cadent"
    return {
        "relative_sign_index": relative_index,
        "phase": phase,
        "phase_label": ZR_PHASE_LABELS[phase],
        "is_peak_period": phase == "angular",
    }


def whole_sign_house_from_asc(asc_sign: str, target_sign: str) -> int:
    return ((SIGNS.index(target_sign) - SIGNS.index(asc_sign)) % 12) + 1


def build_lot_point_dict(
    lot_key: str,
    absolute_degree: float,
    *,
    asc_sign: str,
) -> Dict[str, Any]:
    point_name = LOT_POINT_NAMES[lot_key]
    payload = longitude_to_point_dict(point_name, absolute_degree)
    sign_name = payload["sign"]
    house = whole_sign_house_from_asc(asc_sign, sign_name)
    payload.update(
        {
            "lot": lot_key,
            "lot_label": LOT_LABELS[lot_key],
            "house": house,
            "house_label": f"第{house}宫",
        }
    )
    return payload


def build_lot_payloads(natal_subject: Any) -> Dict[str, Dict[str, Any]]:
    asc_sign = normalize_sign_name(natal_subject.ascendant.sign)
    sect = determine_sect(natal_subject)
    sun_longitude = point_absolute_position(natal_subject, "Sun")
    moon_longitude = point_absolute_position(natal_subject, "Moon")
    asc_longitude = point_absolute_position(natal_subject, "Ascendant")
    if sect == "day":
        fortune_longitude = (asc_longitude + moon_longitude - sun_longitude) % 360.0
        spirit_longitude = (asc_longitude + sun_longitude - moon_longitude) % 360.0
    else:
        fortune_longitude = (asc_longitude + sun_longitude - moon_longitude) % 360.0
        spirit_longitude = (asc_longitude + moon_longitude - sun_longitude) % 360.0
    return {
        "lot_of_fortune": build_lot_point_dict(
            "lot_of_fortune",
            fortune_longitude,
            asc_sign=asc_sign,
        ),
        "lot_of_spirit": build_lot_point_dict(
            "lot_of_spirit",
            spirit_longitude,
            asc_sign=asc_sign,
        ),
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
    local_datetime, timezone_name = adapt_datetime_for_kerykeion(
        local_datetime,
        timezone_name,
    )
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
        houses_system_identifier=cast(Any, house_system),
        zodiac_type=cast(Any, zodiac_type),
    )


def resolve_kerykeion_timezone_name(timezone_name: str) -> Optional[str]:
    """Map fixed-offset strings into pytz-compatible timezone identifiers."""
    try:
        pytz.timezone(timezone_name)
        return timezone_name
    except Exception:
        pass

    tzinfo = parse_timezone_name(timezone_name)
    reference_moment = datetime(2000, 1, 1, tzinfo=tzinfo)
    offset = reference_moment.utcoffset()
    if offset is None:
        return None

    total_minutes = int(offset.total_seconds() // 60)
    if total_minutes == 0:
        return "UTC"
    if total_minutes % 60 != 0:
        return None

    hours = total_minutes // 60
    # pytz's Etc/GMT zones invert the sign relative to UTC offsets.
    sign = "-" if hours > 0 else "+"
    return f"Etc/GMT{sign}{abs(hours)}"


def adapt_datetime_for_kerykeion(
    local_datetime: datetime,
    timezone_name: str,
) -> tuple[datetime, str]:
    """Prepare datetime/timezone inputs for pytz-based predictive backends."""
    backend_timezone = resolve_kerykeion_timezone_name(timezone_name)
    if backend_timezone is not None:
        return local_datetime, backend_timezone
    utc_datetime = local_datetime.astimezone(parse_timezone_name("UTC"))
    return utc_datetime, "UTC"


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
    birthday_this_year = resolve_local_birthday_anniversary(
        birth_info.local_datetime,
        analysis_datetime.year,
        tzinfo=analysis_datetime.tzinfo,
    )
    if analysis_datetime < birthday_this_year:
        years -= 1
    return years


def extract_reference_points(subject: Any) -> Dict[str, Dict[str, Any]]:
    return extract_named_points(subject, TIMING_POINT_NAMES)


def extract_named_points(
    subject: Any,
    point_names: List[str],
) -> Dict[str, Dict[str, Any]]:
    result = {}
    for point_name in point_names:
        result[point_name.lower()] = point_to_dict(
            point_name,
            getattr(subject, point_attribute_name(point_name)),
        )
    return result


def extract_reference_longitudes(subject: Any) -> Dict[str, float]:
    return extract_named_longitudes(subject, TIMING_POINT_NAMES)


def extract_named_longitudes(
    subject: Any,
    point_names: List[str],
) -> Dict[str, float]:
    return {
        point_name: point_absolute_position(subject, point_name)
        for point_name in point_names
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


def normalize_signed_angle(angle: float) -> float:
    normalized = normalize_angle(angle)
    if normalized >= 180.0:
        normalized -= 360.0
    return normalized
