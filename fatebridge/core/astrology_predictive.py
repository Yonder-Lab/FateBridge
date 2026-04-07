"""
High-precision western predictive astrology helpers for FateBridge.

This module layers timing techniques on top of kerykeion / Swiss Ephemeris so
FateBridge can offer returns, progressions, and time-lord style outputs on top
of the existing offline natal chart surface.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz

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
PRIMARY_DIRECTION_METHOD_LABELS = {
    "astroapp_alchabitius": "AstroAPP-Alchabitius",
    "horosa_legacy": "Horosa原方法",
}
PRIMARY_DIRECTION_TIME_KEY_RATES = {
    "Ptolemy": 1.0,
    "Naibod": 0.98564733,
    "Cardan": 0.98666667,
}
PRIMARY_DIRECTION_DEFAULT_ASPECTS = [0, 60, 90, 120, 180]
PRIMARY_DIRECTION_PROMISSORS = ["Ascendant", "Medium_Coeli"]
PRIMARY_DIRECTION_MAX_AGE_YEARS = 100.0

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

LOT_LABELS = {
    "lot_of_fortune": "幸运点",
    "lot_of_spirit": "精神点",
}
LOT_POINT_NAMES = {
    "lot_of_fortune": "Fortune",
    "lot_of_spirit": "Spirit",
}
ZR_SIGN_PERIODS = {
    "Aries": 15,
    "Taurus": 8,
    "Gemini": 20,
    "Cancer": 25,
    "Leo": 19,
    "Virgo": 20,
    "Libra": 8,
    "Scorpio": 15,
    "Sagittarius": 12,
    "Capricorn": 27,
    "Aquarius": 30,
    "Pisces": 12,
}
ZR_LEVEL_UNIT_DAYS = {
    1: 360.0,
    2: 30.0,
    3: 2.5,
    4: 5.0 / 24.0,
}
ZR_LEVEL_UNIT_LABELS = {
    1: "years",
    2: "months",
    3: "weeks",
    4: "days",
}
ZR_LEVEL_UNIT_LABELS_ZH = {
    1: "年",
    2: "月",
    3: "周",
    4: "日",
}
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


def replace_local_datetime_year(moment: datetime, year: int) -> datetime:
    target_day = min(moment.day, monthrange(year, moment.month)[1])
    return datetime(
        year,
        moment.month,
        target_day,
        moment.hour,
        moment.minute,
        moment.second,
        moment.microsecond,
        tzinfo=moment.tzinfo,
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


def build_zodiacal_releasing_period(
    *,
    sign_name: str,
    period_start: datetime,
    period_end: datetime,
    root_sign: str,
    parent_sign: str,
    level: int,
    analysis_datetime: datetime,
    loosing_of_bond: bool = False,
) -> Dict[str, Any]:
    ruler = RULER_BY_SIGN[sign_name]
    phase = classify_releasing_phase(sign_name, root_sign)
    return {
        "sign": sign_name,
        "sign_label": sign_label(sign_name),
        "ruler": ruler,
        "ruler_label": planet_label(ruler),
        "level": level,
        "duration_value": ZR_SIGN_PERIODS[sign_name],
        "duration_unit": ZR_LEVEL_UNIT_LABELS[level],
        "duration_unit_label": ZR_LEVEL_UNIT_LABELS_ZH[level],
        "start": period_start.isoformat(),
        "end": period_end.isoformat(),
        "loosing_of_bond": loosing_of_bond,
        "parent_sign": parent_sign,
        "parent_sign_label": sign_label(parent_sign),
        "active": period_start <= analysis_datetime < period_end,
        "_start": period_start,
        "_end": period_end,
        **phase,
    }


def build_releasing_level_preview(
    *,
    start_sign: str,
    period_start: datetime,
    root_sign: str,
    parent_sign: str,
    level: int,
    analysis_datetime: datetime,
    preview_after_active: int = 4,
    max_periods: int = 24,
) -> List[Dict[str, Any]]:
    periods: List[Dict[str, Any]] = []
    current_sign = start_sign
    cursor = period_start
    active_found = False
    future_slots_remaining = preview_after_active

    for _ in range(max_periods):
        duration_days = ZR_SIGN_PERIODS[current_sign] * ZR_LEVEL_UNIT_DAYS[level]
        next_cursor = cursor + timedelta(days=duration_days)
        period = build_zodiacal_releasing_period(
            sign_name=current_sign,
            period_start=cursor,
            period_end=next_cursor,
            root_sign=root_sign,
            parent_sign=parent_sign,
            level=level,
            analysis_datetime=analysis_datetime,
        )
        periods.append(period)
        if period["active"]:
            active_found = True
        elif active_found:
            future_slots_remaining -= 1
            if future_slots_remaining <= 0:
                break
        cursor = next_cursor
        current_sign = next_sign(current_sign)

    return periods


def build_releasing_level_within_interval(
    *,
    start_sign: str,
    period_start: datetime,
    period_end: datetime,
    root_sign: str,
    parent_sign: str,
    level: int,
    analysis_datetime: datetime,
    max_periods: int = 24,
) -> List[Dict[str, Any]]:
    periods: List[Dict[str, Any]] = []
    current_sign = start_sign
    cursor = period_start
    cycle_start_sign = start_sign
    loosing_used = False
    pending_loosing_of_bond = False

    for _ in range(max_periods):
        if cursor >= period_end:
            break
        duration_days = ZR_SIGN_PERIODS[current_sign] * ZR_LEVEL_UNIT_DAYS[level]
        next_cursor = min(period_end, cursor + timedelta(days=duration_days))
        loosing_of_bond = pending_loosing_of_bond
        pending_loosing_of_bond = False
        periods.append(
            build_zodiacal_releasing_period(
                sign_name=current_sign,
                period_start=cursor,
                period_end=next_cursor,
                root_sign=root_sign,
                parent_sign=parent_sign,
                level=level,
                analysis_datetime=analysis_datetime,
                loosing_of_bond=loosing_of_bond,
            )
        )
        cursor = next_cursor
        next_sign_name = next_sign(current_sign)
        if (
            level > 1
            and not loosing_used
            and next_sign_name == cycle_start_sign
            and cursor < period_end
        ):
            current_sign = opposite_sign(cycle_start_sign)
            loosing_used = True
            pending_loosing_of_bond = True
        else:
            current_sign = next_sign_name

    return periods


def clean_releasing_period(period: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if period is None:
        return None
    return {key: value for key, value in period.items() if not key.startswith("_")}


def clean_releasing_timeline(periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [clean_releasing_period(period) for period in periods]


def peak_signs_from_root(root_sign: str) -> List[Dict[str, str]]:
    root_index = SIGNS.index(root_sign)
    offsets = [0, 3, 6, 9]
    signs = [SIGNS[(root_index + offset) % 12] for offset in offsets]
    return [
        {
            "sign": sign_name,
            "sign_label": sign_label(sign_name),
        }
        for sign_name in signs
    ]


def build_zodiacal_releasing_for_lot(
    lot_key: str,
    lot_payload: Dict[str, Any],
    *,
    birth_info: AstroBirthInfo,
    analysis_datetime: datetime,
    start_sign: Optional[str] = None,
) -> Dict[str, Any]:
    root_sign = start_sign or lot_payload["sign"]
    level_one_timeline = build_releasing_level_preview(
        start_sign=root_sign,
        period_start=birth_info.local_datetime,
        root_sign=root_sign,
        parent_sign=root_sign,
        level=1,
        analysis_datetime=analysis_datetime,
    )
    current_level_1 = next((item for item in level_one_timeline if item["active"]), None)

    level_two_timeline: List[Dict[str, Any]] = []
    current_level_2 = None
    if current_level_1 is not None:
        level_two_timeline = build_releasing_level_within_interval(
            start_sign=current_level_1["sign"],
            period_start=current_level_1["_start"],
            period_end=current_level_1["_end"],
            root_sign=root_sign,
            parent_sign=current_level_1["sign"],
            level=2,
            analysis_datetime=analysis_datetime,
        )
        current_level_2 = next((item for item in level_two_timeline if item["active"]), None)

    level_three_timeline: List[Dict[str, Any]] = []
    current_level_3 = None
    if current_level_2 is not None:
        level_three_timeline = build_releasing_level_within_interval(
            start_sign=current_level_2["sign"],
            period_start=current_level_2["_start"],
            period_end=current_level_2["_end"],
            root_sign=root_sign,
            parent_sign=current_level_2["sign"],
            level=3,
            analysis_datetime=analysis_datetime,
        )
        current_level_3 = next(
            (item for item in level_three_timeline if item["active"]),
            None,
        )

    return {
        "base_point": LOT_POINT_NAMES[lot_key],
        "base_point_label": LOT_LABELS[lot_key],
        "lot": lot_payload,
        "release_start_sign": root_sign,
        "release_start_sign_label": sign_label(root_sign),
        "peak_signs": peak_signs_from_root(root_sign),
        "current_level_1": clean_releasing_period(current_level_1),
        "current_level_2": clean_releasing_period(current_level_2),
        "current_level_3": clean_releasing_period(current_level_3),
        "level_1_timeline": clean_releasing_timeline(level_one_timeline),
        "level_2_timeline": clean_releasing_timeline(level_two_timeline),
        "level_3_timeline": clean_releasing_timeline(level_three_timeline),
    }


def build_zodiacal_releasing_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
) -> Dict[str, Any]:
    lots = build_lot_payloads(natal_subject)
    spirit_start_sign = lots["lot_of_spirit"]["sign"]
    if spirit_start_sign == lots["lot_of_fortune"]["sign"]:
        spirit_start_sign = next_sign(spirit_start_sign)
    return {
        "spirit": build_zodiacal_releasing_for_lot(
            "lot_of_spirit",
            lots["lot_of_spirit"],
            birth_info=birth_info,
            analysis_datetime=analysis_datetime,
            start_sign=spirit_start_sign,
        ),
        "fortune": build_zodiacal_releasing_for_lot(
            "lot_of_fortune",
            lots["lot_of_fortune"],
            birth_info=birth_info,
            analysis_datetime=analysis_datetime,
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
        houses_system_identifier=house_system,
        zodiac_type=zodiac_type,
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
    backend_return_timezone = (
        resolve_kerykeion_timezone_name(return_timezone) or "UTC"
    )
    factory = PlanetaryReturnFactory(
        natal_subject,
        lng=return_longitude,
        lat=return_latitude,
        tz_str=backend_return_timezone,
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


def primary_direction_method_label(method_name: str) -> str:
    return PRIMARY_DIRECTION_METHOD_LABELS.get(method_name, method_name)


def primary_direction_time_key_rate(time_key: str) -> float:
    return PRIMARY_DIRECTION_TIME_KEY_RATES.get(time_key, 1.0)


def normalize_primary_direction_aspects(
    pd_aspects: Optional[List[int]],
) -> List[int]:
    if not pd_aspects:
        return PRIMARY_DIRECTION_DEFAULT_ASPECTS.copy()
    normalized: List[int] = []
    for value in pd_aspects:
        try:
            degree = int(float(value)) % 360
        except (TypeError, ValueError):
            continue
        if degree not in normalized:
            normalized.append(degree)
    return normalized or PRIMARY_DIRECTION_DEFAULT_ASPECTS.copy()


def primary_direction_aspect_variants(aspect_degree: int) -> List[float]:
    if aspect_degree in {0, 180}:
        return [float(aspect_degree)]
    return [float(aspect_degree), float((360 - aspect_degree) % 360)]


def primary_direction_aspect_meta(aspect_degree: int) -> tuple[str, str]:
    for aspect_key, aspect_label_text, aspect_value in ASPECT_DEGREES:
        if int(aspect_value) == aspect_degree:
            return aspect_key, aspect_label_text
    return f"{aspect_degree}deg", f"{aspect_degree}°"


def build_primary_direction_targets(natal_subject: Any) -> List[Dict[str, Any]]:
    targets = [
        {
            "name": point_name,
            "label": planet_label(point_name),
            "longitude": point_absolute_position(natal_subject, point_name),
        }
        for point_name in TIMING_POINT_NAMES
    ]
    for lot_key, payload in build_lot_payloads(natal_subject).items():
        point_name = LOT_POINT_NAMES[lot_key]
        targets.append(
            {
                "name": point_name,
                "label": LOT_LABELS[lot_key],
                "longitude": float(payload["absolute_degree"]),
            }
        )
    return targets


def build_primary_direction_points(
    natal_subject: Any,
    *,
    arc_degrees: float,
) -> Dict[str, Dict[str, Any]]:
    natal_longitudes = extract_reference_longitudes(natal_subject)
    return {
        point_name: longitude_to_point_dict(
            point_name,
            natal_longitudes[point_name] + arc_degrees,
        )
        for point_name in PRIMARY_DIRECTION_PROMISSORS
    }


def build_shifted_reference_points(
    natal_subject: Any,
    *,
    arc_degrees: float,
) -> Dict[str, Dict[str, Any]]:
    natal_longitudes = extract_reference_longitudes(natal_subject)
    return {
        point_name: longitude_to_point_dict(
            point_name,
            natal_longitudes[point_name] + arc_degrees,
        )
        for point_name in TIMING_POINT_NAMES
    }


def build_shifted_lot_payloads(
    natal_subject: Any,
    *,
    arc_degrees: float,
) -> Dict[str, Dict[str, Any]]:
    natal_lots = build_lot_payloads(natal_subject)
    asc_sign = normalize_sign_name(natal_subject.ascendant.sign)
    return {
        lot_key: build_lot_point_dict(
            lot_key,
            float(payload["absolute_degree"]) + arc_degrees,
            asc_sign=asc_sign,
        )
        for lot_key, payload in natal_lots.items()
    }


def build_sign_change_payloads(
    natal_points: Dict[str, Dict[str, Any]],
    directed_points: Dict[str, Dict[str, Any]],
    natal_lots: Dict[str, Dict[str, Any]],
    directed_lots: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    changes: List[Dict[str, Any]] = []

    for point_name in TIMING_POINT_NAMES:
        natal_payload = natal_points[point_name.lower()]
        directed_name = next(
            (
                candidate
                for candidate in directed_points
                if candidate.lower() == point_name.lower()
            ),
            point_name,
        )
        directed_payload = directed_points[directed_name]
        if natal_payload["sign"] != directed_payload["sign"]:
            changes.append(
                {
                    "point": directed_name,
                    "point_label": planet_label(directed_name),
                    "from_sign": natal_payload["sign"],
                    "from_sign_label": natal_payload["sign_label"],
                    "to_sign": directed_payload["sign"],
                    "to_sign_label": directed_payload["sign_label"],
                }
            )

    for lot_key, natal_payload in natal_lots.items():
        directed_payload = directed_lots[lot_key]
        if natal_payload["sign"] != directed_payload["sign"]:
            changes.append(
                {
                    "point": LOT_POINT_NAMES[lot_key],
                    "point_label": LOT_LABELS[lot_key],
                    "from_sign": natal_payload["sign"],
                    "from_sign_label": natal_payload["sign_label"],
                    "to_sign": directed_payload["sign"],
                    "to_sign_label": directed_payload["sign_label"],
                }
            )

    return changes


def build_primary_directions_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    pd_method: str,
    pd_time_key: str,
    pd_type: int = 0,
    pd_aspects: Optional[List[int]] = None,
    max_age_years: float = PRIMARY_DIRECTION_MAX_AGE_YEARS,
    current_window_size: int = 12,
) -> Dict[str, Any]:
    age_years = calculate_age_years(birth_info, analysis_datetime)
    time_key_rate = primary_direction_time_key_rate(pd_time_key)
    aspects = normalize_primary_direction_aspects(pd_aspects)
    natal_longitudes = extract_reference_longitudes(natal_subject)
    targets = build_primary_direction_targets(natal_subject)
    direction_mode = "converse" if pd_type == 1 else "direct"
    direction_mode_label = "逆推" if pd_type == 1 else "顺推"
    current_arc = age_years * time_key_rate * (-1 if pd_type == 1 else 1)
    timeline: List[Dict[str, Any]] = []
    seen_hits = set()

    for promissor in PRIMARY_DIRECTION_PROMISSORS:
        promissor_longitude = natal_longitudes[promissor]
        for target in targets:
            for aspect_degree in aspects:
                aspect_key, aspect_label_text = primary_direction_aspect_meta(
                    aspect_degree
                )
                for variant in primary_direction_aspect_variants(aspect_degree):
                    arc = (target["longitude"] + variant - promissor_longitude) % 360.0
                    event_age_years = arc / time_key_rate if time_key_rate else 0.0
                    if event_age_years <= 0.05 or event_age_years > max_age_years:
                        continue
                    dedupe_key = (
                        promissor,
                        target["name"],
                        aspect_key,
                        round(event_age_years, 6),
                    )
                    if dedupe_key in seen_hits:
                        continue
                    seen_hits.add(dedupe_key)
                    event_datetime = birth_info.local_datetime + timedelta(
                        days=event_age_years * TROPICAL_YEAR_DAYS
                    )
                    timeline.append(
                        {
                            "arc_degrees": round(arc, 4),
                            "promissor": promissor,
                            "promissor_label": planet_label(promissor),
                            "significator": target["name"],
                            "significator_label": target["label"],
                            "aspect": aspect_key,
                            "aspect_label": aspect_label_text,
                            "aspect_degree": aspect_degree,
                            "event_age_years": round(event_age_years, 4),
                            "event_datetime": event_datetime.isoformat(),
                            "distance_from_current_years": round(
                                abs(event_age_years - age_years),
                                4,
                            ),
                        }
                    )

    timeline.sort(
        key=lambda item: (
            item["event_age_years"],
            item["arc_degrees"],
            item["promissor"],
            item["significator"],
        )
    )
    current_window = sorted(
        timeline,
        key=lambda item: (
            item["distance_from_current_years"],
            item["event_age_years"],
            item["arc_degrees"],
        ),
    )[:current_window_size]

    return {
        "method": pd_method,
        "method_label": primary_direction_method_label(pd_method),
        "time_key": pd_time_key,
        "time_key_label": pd_time_key,
        "pd_type": pd_type,
        "direction_mode": direction_mode,
        "direction_mode_label": direction_mode_label,
        "approximation": "axis_static_key",
        "approximation_label": "轴点 static key 近似",
        "promissors": PRIMARY_DIRECTION_PROMISSORS,
        "aspects": aspects,
        "current_age_years": round(age_years, 4),
        "current_arc_degrees": round(current_arc, 4),
        "current_arc_absolute_degrees": round(abs(current_arc), 4),
        "current_window": current_window,
        "timeline": timeline,
    }


def build_primary_direction_chart_payload(
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    pd_method: str,
    pd_time_key: str,
    pd_type: int,
    current_arc_degrees: float,
    current_hits: List[Dict[str, Any]],
    show_pd_bounds: bool,
) -> Dict[str, Any]:
    natal_points = extract_reference_points(natal_subject)
    natal_lots = build_lot_payloads(natal_subject)
    directed_points = build_shifted_reference_points(
        natal_subject,
        arc_degrees=current_arc_degrees,
    )
    directed_lots = build_shifted_lot_payloads(
        natal_subject,
        arc_degrees=current_arc_degrees,
    )
    directed_axes = build_primary_direction_points(
        natal_subject,
        arc_degrees=current_arc_degrees,
    )
    return {
        "analysis_datetime": analysis_datetime.isoformat(),
        "method": pd_method,
        "method_label": primary_direction_method_label(pd_method),
        "time_key": pd_time_key,
        "time_key_label": pd_time_key,
        "pd_type": pd_type,
        "direction_mode": "converse" if pd_type == 1 else "direct",
        "direction_mode_label": "逆推" if pd_type == 1 else "顺推",
        "current_arc_degrees": round(current_arc_degrees, 4),
        "current_arc_absolute_degrees": round(abs(current_arc_degrees), 4),
        "show_pd_bounds": show_pd_bounds,
        "approximation": "axis_static_key",
        "directed_points": directed_points,
        "directed_lots": directed_lots,
        "sign_changes": build_sign_change_payloads(
            natal_points,
            directed_points,
            natal_lots,
            directed_lots,
        ),
        "directed_ascendant": directed_axes["Ascendant"],
        "directed_medium_coeli": directed_axes["Medium_Coeli"],
        "hits": current_hits[:8],
    }


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


def resolve_last_birthday(
    birth_info: AstroBirthInfo,
    *,
    analysis_datetime: datetime,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    analysis_local = rebuild_local_datetime(analysis_datetime, timezone_name)
    birthday_this_year = datetime(
        analysis_local.year,
        birth_info.local_datetime.month,
        min(
            birth_info.local_datetime.day,
            monthrange(analysis_local.year, birth_info.local_datetime.month)[1],
        ),
        birth_info.local_datetime.hour,
        birth_info.local_datetime.minute,
        birth_info.local_datetime.second,
        birth_info.local_datetime.microsecond,
        tzinfo=analysis_local.tzinfo,
    )
    if analysis_local < birthday_this_year:
        last_birthday = replace_local_datetime_year(
            birthday_this_year,
            birthday_this_year.year - 1,
        )
    else:
        last_birthday = birthday_this_year
    return analysis_local, last_birthday


def build_monthly_profections_payload(
    *,
    annual_house: int,
    asc_sign: str,
    year_start: datetime,
    analysis_datetime: datetime,
) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    asc_index = SIGNS.index(asc_sign)
    for month_offset in range(12):
        start = add_months(year_start, month_offset)
        end = add_months(year_start, month_offset + 1)
        house = ((annual_house - 1 + month_offset) % 12) + 1
        sign_name = SIGNS[(asc_index + house - 1) % 12]
        ruler = RULER_BY_SIGN[sign_name]
        timeline.append(
            {
                "month_index": month_offset + 1,
                "house": house,
                "house_label": f"第{house}宫",
                "sign": sign_name,
                "sign_label": sign_label(sign_name),
                "lord": ruler,
                "lord_label": planet_label(ruler),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "active": start <= analysis_datetime < end,
            }
        )
    return timeline


def build_given_year_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    annual_profection: Dict[str, Any],
    return_longitude: float,
    return_latitude: float,
    return_timezone: str,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Dict[str, Any]:
    analysis_local, last_birthday = resolve_last_birthday(
        birth_info,
        analysis_datetime=analysis_datetime,
        timezone_name=return_timezone,
    )
    year_end = add_months(last_birthday, 12)
    given_year_subject = build_subject(
        name=f"{birth_info.name}-given-year",
        local_datetime=analysis_local,
        longitude=return_longitude,
        latitude=return_latitude,
        timezone_name=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    monthly_profections = build_monthly_profections_payload(
        annual_house=annual_profection["activated_house"],
        asc_sign=normalize_sign_name(natal_subject.ascendant.sign),
        year_start=last_birthday,
        analysis_datetime=analysis_local,
    )
    hits = collect_aspect_hits(
        source_longitudes=extract_reference_longitudes(given_year_subject),
        target_longitudes=extract_reference_longitudes(natal_subject),
        orb_limit=1.5,
    )
    return {
        "analysis_datetime": analysis_local.isoformat(),
        "year_start": last_birthday.isoformat(),
        "year_end": year_end.isoformat(),
        "sun": point_to_dict("Sun", given_year_subject.sun),
        "moon": point_to_dict("Moon", given_year_subject.moon),
        "ascendant": point_to_dict("Ascendant", given_year_subject.ascendant),
        "medium_coeli": point_to_dict(
            "Medium_Coeli",
            given_year_subject.medium_coeli,
        ),
        "annual_profection": annual_profection,
        "monthly_profections": monthly_profections,
        "hits": hits[:8],
        "location": {
            "longitude": return_longitude,
            "latitude": return_latitude,
            "timezone": return_timezone,
        },
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
    pd_method: str = "astroapp_alchabitius",
    pd_time_key: str = "Ptolemy",
    pd_type: int = 0,
    pd_aspects: Optional[List[int]] = None,
    show_pd_bounds: bool = True,
) -> Dict[str, Any]:
    natal_subject = build_natal_subject(
        birth_info,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    natal_reference = extract_reference_points(natal_subject)
    sect = determine_sect(natal_subject)
    natal_reference["sect"] = {"key": sect, "label": sect_label(sect)}
    natal_reference["lots"] = build_lot_payloads(natal_subject)

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
    primary_directions_payload = build_primary_directions_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        pd_aspects=pd_aspects,
    )
    primary_direction_chart_payload = build_primary_direction_chart_payload(
        natal_subject,
        analysis_datetime=analysis_datetime,
        pd_method=pd_method,
        pd_time_key=pd_time_key,
        pd_type=pd_type,
        current_arc_degrees=primary_directions_payload["current_arc_degrees"],
        current_hits=primary_directions_payload["current_window"],
        show_pd_bounds=show_pd_bounds,
    )
    profection_payload = build_annual_profection_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
    )
    given_year_payload = build_given_year_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
        annual_profection=profection_payload,
        return_longitude=effective_return_longitude,
        return_latitude=effective_return_latitude,
        return_timezone=effective_return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
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
    zodiacal_releasing_payload = build_zodiacal_releasing_payload(
        birth_info,
        natal_subject,
        analysis_datetime=analysis_datetime,
    )

    age_years = calculate_age_years(birth_info, analysis_datetime)
    zr_spirit_current = zodiacal_releasing_payload["spirit"]["current_level_1"]
    summary = (
        f"{analysis_datetime.strftime('%Y-%m-%d')} 西占时运："
        f"太阳返照 {returns_payload['solar_return']['return_datetime']}，"
        f"月返 {returns_payload['lunar_return']['return_datetime']}，"
        f"主限 {primary_directions_payload['time_key_label']}"
        f" {primary_directions_payload['current_arc_degrees']:.2f}°，"
        f"指定年盘上升 {given_year_payload['ascendant']['sign_label']}，"
        f"年小限落第{profection_payload['activated_house']}宫"
        f"{profection_payload['activated_sign_label']}，"
        f"法达 {firdaria_payload['current_major']['planet_label']}"
        f"/{firdaria_payload['current_sub']['planet_label']}，"
        f"Spirit 黄道释放 L1 {zr_spirit_current['sign_label']}，"
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
            "primary_directions": primary_directions_payload,
            "primary_direction_chart": primary_direction_chart_payload,
            "given_year": given_year_payload,
        },
        "time_lords": {
            "annual_profection": profection_payload,
            "firdaria": firdaria_payload,
            "decennials": decennials_payload,
            "zodiacal_releasing": zodiacal_releasing_payload,
        },
        "summary": summary,
    }
