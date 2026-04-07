"""
Approximate offline astrology engine for FateBridge.

This module intentionally uses lightweight orbital approximations so the new
chart family can run without external ephemeris dependencies.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fatebridge.utils.helpers import parse_timezone_name

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

SIGN_LABELS_ZH = {
    "Aries": "白羊",
    "Taurus": "金牛",
    "Gemini": "双子",
    "Cancer": "巨蟹",
    "Leo": "狮子",
    "Virgo": "处女",
    "Libra": "天秤",
    "Scorpio": "天蝎",
    "Sagittarius": "射手",
    "Capricorn": "摩羯",
    "Aquarius": "水瓶",
    "Pisces": "双鱼",
}

ELEMENT_BY_SIGN = {
    "Aries": "Fire",
    "Leo": "Fire",
    "Sagittarius": "Fire",
    "Taurus": "Earth",
    "Virgo": "Earth",
    "Capricorn": "Earth",
    "Gemini": "Air",
    "Libra": "Air",
    "Aquarius": "Air",
    "Cancer": "Water",
    "Scorpio": "Water",
    "Pisces": "Water",
}

MODALITY_BY_SIGN = {
    "Aries": "Cardinal",
    "Cancer": "Cardinal",
    "Libra": "Cardinal",
    "Capricorn": "Cardinal",
    "Taurus": "Fixed",
    "Leo": "Fixed",
    "Scorpio": "Fixed",
    "Aquarius": "Fixed",
    "Gemini": "Mutable",
    "Virgo": "Mutable",
    "Sagittarius": "Mutable",
    "Pisces": "Mutable",
}

RULER_BY_SIGN = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

SU28 = [
    "角宿",
    "亢宿",
    "氐宿",
    "房宿",
    "心宿",
    "尾宿",
    "箕宿",
    "斗宿",
    "牛宿",
    "女宿",
    "虚宿",
    "危宿",
    "室宿",
    "壁宿",
    "奎宿",
    "娄宿",
    "胃宿",
    "昴宿",
    "毕宿",
    "觜宿",
    "参宿",
    "井宿",
    "鬼宿",
    "柳宿",
    "星宿",
    "张宿",
    "翼宿",
    "轸宿",
]

PLANET_SEQUENCE = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "North Node",
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

ASPECTS = [
    ("conjunction", 0.0),
    ("sextile", 60.0),
    ("square", 90.0),
    ("trine", 120.0),
    ("opposition", 180.0),
]

HARMONIOUS_ASPECTS = {"conjunction", "sextile", "trine"}

PLANET_ORBITAL_ELEMENTS = {
    "Mercury": lambda d: (48.3313 + 3.24587e-5 * d, 7.0047 + 5e-8 * d, 29.1241 + 1.01444e-5 * d, 0.387098, 0.205635 + 5.59e-10 * d, 168.6562 + 4.0923344368 * d),
    "Venus": lambda d: (76.6799 + 2.4659e-5 * d, 3.3946 + 2.75e-8 * d, 54.8910 + 1.38374e-5 * d, 0.72333, 0.006773 - 1.302e-9 * d, 48.0052 + 1.6021302244 * d),
    "Mars": lambda d: (49.5574 + 2.11081e-5 * d, 1.8497 - 1.78e-8 * d, 286.5016 + 2.92961e-5 * d, 1.523688, 0.093405 + 2.516e-9 * d, 18.6021 + 0.5240207766 * d),
    "Jupiter": lambda d: (100.4542 + 2.76854e-5 * d, 1.303 - 1.557e-7 * d, 273.8777 + 1.64505e-5 * d, 5.20256, 0.048498 + 4.469e-9 * d, 19.895 + 0.0830853001 * d),
    "Saturn": lambda d: (113.6634 + 2.3898e-5 * d, 2.4886 - 1.081e-7 * d, 339.3939 + 2.97661e-5 * d, 9.55475, 0.055546 - 9.499e-9 * d, 316.967 + 0.0334442282 * d),
    "Uranus": lambda d: (74.0005 + 1.3978e-5 * d, 0.7733 + 1.9e-8 * d, 96.6612 + 3.0565e-5 * d, 19.18171 - 1.55e-8 * d, 0.047318 + 7.45e-9 * d, 142.5905 + 0.011725806 * d),
    "Neptune": lambda d: (131.7806 + 3.0173e-5 * d, 1.77 - 2.55e-7 * d, 272.8461 - 6.027e-6 * d, 30.05826 + 3.313e-8 * d, 0.008606 + 2.15e-9 * d, 260.2471 + 0.005995147 * d),
}


@dataclass(frozen=True)
class AstroBirthInfo:
    name: str
    birth_place: str
    timezone: str
    longitude: float
    latitude: float
    local_datetime: datetime
    utc_datetime: datetime


def build_astro_birth_info(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: float,
    birth_latitude: float,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
) -> AstroBirthInfo:
    timezone_name = birth_timezone or "UTC"
    tzinfo = parse_timezone_name(timezone_name)
    local_datetime = datetime(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        birth_minute,
        tzinfo=tzinfo,
    )
    utc_datetime = local_datetime.astimezone(parse_timezone_name("UTC"))
    return AstroBirthInfo(
        name=(name or "未提供").strip() or "未提供",
        birth_place=(birth_place or "未提供").strip() or "未提供",
        timezone=timezone_name,
        longitude=birth_longitude,
        latitude=birth_latitude,
        local_datetime=local_datetime,
        utc_datetime=utc_datetime,
    )


def normalize_angle(angle: float) -> float:
    return angle % 360.0


def _deg_to_rad(value: float) -> float:
    return math.radians(value)


def _rad_to_deg(value: float) -> float:
    return math.degrees(value)


def _sin_deg(value: float) -> float:
    return math.sin(_deg_to_rad(value))


def _cos_deg(value: float) -> float:
    return math.cos(_deg_to_rad(value))


def _julian_day(target: datetime) -> float:
    year = target.year
    month = target.month
    day = target.day + (
        target.hour + target.minute / 60.0 + target.second / 3600.0
    ) / 24.0

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + a // 4
    return (
        int(365.25 * (year + 4716))
        + int(30.6001 * (month + 1))
        + day
        + b
        - 1524.5
    )


def _solve_kepler(mean_anomaly_deg: float, eccentricity: float) -> float:
    mean_anomaly_rad = _deg_to_rad(mean_anomaly_deg)
    estimate = mean_anomaly_rad
    for _ in range(8):
        numerator = estimate - eccentricity * math.sin(estimate) - mean_anomaly_rad
        denominator = 1 - eccentricity * math.cos(estimate)
        estimate -= numerator / denominator
    return estimate


def _planet_heliocentric_coords(planet: str, day_number: float) -> Tuple[float, float, float]:
    ascending_node, inclination, perihelion, semi_major_axis, eccentricity, mean_anomaly = PLANET_ORBITAL_ELEMENTS[planet](day_number)
    eccentric_anomaly = _solve_kepler(normalize_angle(mean_anomaly), eccentricity)
    xv = semi_major_axis * (math.cos(eccentric_anomaly) - eccentricity)
    yv = semi_major_axis * (
        math.sqrt(1 - eccentricity * eccentricity) * math.sin(eccentric_anomaly)
    )
    true_anomaly = _rad_to_deg(math.atan2(yv, xv))
    radius = math.sqrt(xv * xv + yv * yv)
    argument = normalize_angle(true_anomaly + perihelion)
    xh = radius * (
        _cos_deg(ascending_node) * _cos_deg(argument)
        - _sin_deg(ascending_node) * _sin_deg(argument) * _cos_deg(inclination)
    )
    yh = radius * (
        _sin_deg(ascending_node) * _cos_deg(argument)
        + _cos_deg(ascending_node) * _sin_deg(argument) * _cos_deg(inclination)
    )
    zh = radius * (_sin_deg(argument) * _sin_deg(inclination))
    return xh, yh, zh


def _sun_state(day_number: float) -> Dict[str, float]:
    perihelion = 282.9404 + 4.70935e-5 * day_number
    eccentricity = 0.016709 - 1.151e-9 * day_number
    mean_anomaly = normalize_angle(356.047 + 0.9856002585 * day_number)
    eccentric_anomaly = _solve_kepler(mean_anomaly, eccentricity)
    xv = math.cos(eccentric_anomaly) - eccentricity
    yv = math.sqrt(1 - eccentricity * eccentricity) * math.sin(eccentric_anomaly)
    true_anomaly = _rad_to_deg(math.atan2(yv, xv))
    radius = math.sqrt(xv * xv + yv * yv)
    longitude = normalize_angle(true_anomaly + perihelion)
    return {
        "longitude": longitude,
        "radius": radius,
        "mean_anomaly": mean_anomaly,
        "x": radius * _cos_deg(longitude),
        "y": radius * _sin_deg(longitude),
    }


def _moon_state(day_number: float, sun_state: Dict[str, float]) -> Dict[str, float]:
    ascending_node = 125.1228 - 0.0529538083 * day_number
    inclination = 5.1454
    perihelion = 318.0634 + 0.1643573223 * day_number
    semi_major_axis = 60.2666
    eccentricity = 0.0549
    mean_anomaly = normalize_angle(115.3654 + 13.0649929509 * day_number)
    eccentric_anomaly = _solve_kepler(mean_anomaly, eccentricity)
    xv = semi_major_axis * (math.cos(eccentric_anomaly) - eccentricity)
    yv = semi_major_axis * (
        math.sqrt(1 - eccentricity * eccentricity) * math.sin(eccentric_anomaly)
    )
    true_anomaly = _rad_to_deg(math.atan2(yv, xv))
    radius = math.sqrt(xv * xv + yv * yv)
    argument = normalize_angle(true_anomaly + perihelion)
    xh = radius * (
        _cos_deg(ascending_node) * _cos_deg(argument)
        - _sin_deg(ascending_node) * _sin_deg(argument) * _cos_deg(inclination)
    )
    yh = radius * (
        _sin_deg(ascending_node) * _cos_deg(argument)
        + _cos_deg(ascending_node) * _sin_deg(argument) * _cos_deg(inclination)
    )
    zh = radius * (_sin_deg(argument) * _sin_deg(inclination))

    longitude = normalize_angle(_rad_to_deg(math.atan2(yh, xh)))
    latitude = _rad_to_deg(math.atan2(zh, math.sqrt(xh * xh + yh * yh)))
    mean_longitude = normalize_angle(ascending_node + perihelion + mean_anomaly)
    elongation = normalize_angle(mean_longitude - sun_state["longitude"])
    argument_of_latitude = normalize_angle(mean_longitude - ascending_node)
    sun_mean_anomaly = sun_state["mean_anomaly"]

    longitude += (
        -1.274 * _sin_deg(mean_anomaly - 2 * elongation)
        + 0.658 * _sin_deg(2 * elongation)
        - 0.186 * _sin_deg(sun_mean_anomaly)
        - 0.059 * _sin_deg(2 * mean_anomaly - 2 * elongation)
        - 0.057 * _sin_deg(mean_anomaly - 2 * elongation + sun_mean_anomaly)
        + 0.053 * _sin_deg(mean_anomaly + 2 * elongation)
        + 0.046 * _sin_deg(2 * elongation - sun_mean_anomaly)
        + 0.041 * _sin_deg(mean_anomaly - sun_mean_anomaly)
        - 0.035 * _sin_deg(elongation)
        - 0.031 * _sin_deg(mean_anomaly + sun_mean_anomaly)
        - 0.015 * _sin_deg(2 * argument_of_latitude - 2 * elongation)
        + 0.011 * _sin_deg(mean_anomaly - 4 * elongation)
    )
    latitude += (
        -0.173 * _sin_deg(argument_of_latitude - 2 * elongation)
        - 0.055 * _sin_deg(mean_anomaly - argument_of_latitude - 2 * elongation)
        - 0.046 * _sin_deg(mean_anomaly + argument_of_latitude - 2 * elongation)
        + 0.033 * _sin_deg(argument_of_latitude + 2 * elongation)
        + 0.017 * _sin_deg(2 * mean_anomaly + argument_of_latitude)
    )
    return {"longitude": normalize_angle(longitude), "latitude": latitude}


def _pluto_state(day_number: float) -> Dict[str, float]:
    s = 50.03 + 0.033459652 * day_number
    p = 238.95 + 0.003968789 * day_number
    longitude = (
        238.9508
        + 0.00400703 * day_number
        - 19.799 * _sin_deg(p)
        + 19.848 * _cos_deg(p)
        + 0.897 * _sin_deg(2 * p)
        - 4.956 * _cos_deg(2 * p)
        + 0.61 * _sin_deg(3 * p)
        + 1.211 * _cos_deg(3 * p)
        - 0.341 * _sin_deg(4 * p)
        - 0.19 * _cos_deg(4 * p)
        + 0.128 * _sin_deg(5 * p)
        - 0.034 * _cos_deg(5 * p)
        - 0.038 * _sin_deg(6 * p)
        + 0.031 * _cos_deg(6 * p)
        + 0.02 * _sin_deg(s - p)
        - 0.01 * _cos_deg(s - p)
    )
    latitude = (
        -3.9082
        - 5.453 * _sin_deg(p)
        - 14.975 * _cos_deg(p)
        + 3.527 * _sin_deg(2 * p)
        + 1.673 * _cos_deg(2 * p)
        - 1.051 * _sin_deg(3 * p)
        + 0.328 * _cos_deg(3 * p)
        + 0.179 * _sin_deg(4 * p)
        - 0.292 * _cos_deg(4 * p)
        + 0.019 * _sin_deg(5 * p)
        + 0.1 * _cos_deg(5 * p)
        - 0.031 * _sin_deg(6 * p)
        - 0.026 * _cos_deg(6 * p)
        + 0.011 * _cos_deg(s - p)
    )
    return {"longitude": normalize_angle(longitude), "latitude": latitude}


def _planet_state(planet: str, day_number: float, sun_state: Dict[str, float]) -> Dict[str, float]:
    if planet == "Sun":
        return {"longitude": sun_state["longitude"], "latitude": 0.0}
    if planet == "Moon":
        return _moon_state(day_number, sun_state)
    if planet == "Pluto":
        return _pluto_state(day_number)
    if planet == "North Node":
        return {
            "longitude": normalize_angle(125.1228 - 0.0529538083 * day_number),
            "latitude": 0.0,
        }

    xh, yh, zh = _planet_heliocentric_coords(planet, day_number)
    xg = xh + sun_state["x"]
    yg = yh + sun_state["y"]
    zg = zh
    longitude = normalize_angle(_rad_to_deg(math.atan2(yg, xg)))
    latitude = _rad_to_deg(math.atan2(zg, math.sqrt(xg * xg + yg * yg)))
    return {"longitude": longitude, "latitude": latitude}


def _sign_name(longitude: float) -> str:
    return SIGNS[int(normalize_angle(longitude) // 30)]


def _degree_in_sign(longitude: float) -> float:
    return normalize_angle(longitude) % 30


def _house_for_longitude(longitude: float, ascendant: float, house_system: str) -> int:
    if house_system == "whole_sign":
        asc_sign_index = int(normalize_angle(ascendant) // 30)
        sign_index = int(normalize_angle(longitude) // 30)
        return ((sign_index - asc_sign_index) % 12) + 1
    return int(normalize_angle(longitude - ascendant) // 30) + 1


def _sector13_for_longitude(longitude: float, ascendant: float) -> int:
    return int(normalize_angle(longitude - ascendant) // (360.0 / 13.0)) + 1


def _midpoint(longitude_a: float, longitude_b: float) -> float:
    delta = normalize_angle(longitude_b - longitude_a)
    if delta > 180:
        delta -= 360
    return normalize_angle(longitude_a + delta / 2)


def _ayanamsha(julian_day: float) -> float:
    return 24.0 + ((julian_day - 2451545.0) / 36525.0) * 0.6986


def _nakshatra(longitude: float) -> str:
    index = int(normalize_angle(longitude) // (360.0 / 27.0))
    return NAKSHATRAS[index]


def _su28(longitude: float) -> str:
    index = int(normalize_angle(longitude) // (360.0 / 28.0))
    return SU28[index]


def _week_ruler(target: datetime) -> str:
    weekday_index = target.weekday()
    return [
        "Moon",
        "Mars",
        "Mercury",
        "Jupiter",
        "Venus",
        "Saturn",
        "Sun",
    ][weekday_index]


def _gmst(julian_day: float) -> float:
    t = (julian_day - 2451545.0) / 36525.0
    return normalize_angle(
        280.46061837
        + 360.98564736629 * (julian_day - 2451545.0)
        + 0.000387933 * t * t
        - (t * t * t) / 38710000.0
    )


def _angles(julian_day: float, longitude: float, latitude: float) -> Dict[str, float]:
    armc = normalize_angle(_gmst(julian_day) + longitude)
    epsilon = 23.439291 - 0.0130042 * ((julian_day - 2451545.0) / 36525.0)
    ascendant = _rad_to_deg(
        math.atan2(
            -_cos_deg(armc),
            _sin_deg(armc) * _cos_deg(epsilon)
            + math.tan(_deg_to_rad(latitude)) * _sin_deg(epsilon),
        )
    )
    ascendant = normalize_angle(ascendant)
    midheaven = _rad_to_deg(
        math.atan2(
            _sin_deg(armc) * _cos_deg(epsilon),
            _cos_deg(armc),
        )
    )
    midheaven = normalize_angle(midheaven)
    return {"ascendant": ascendant, "midheaven": midheaven}


def _build_houses(ascendant: float, house_system: str) -> List[Dict[str, Any]]:
    houses: List[Dict[str, Any]] = []
    if house_system == "whole_sign":
        first_cusp = math.floor(ascendant / 30.0) * 30.0
    else:
        first_cusp = ascendant
    for house_number in range(1, 13):
        cusp = normalize_angle(first_cusp + (house_number - 1) * 30.0)
        sign = _sign_name(cusp)
        houses.append(
            {
                "house": house_number,
                "cusp_longitude": round(cusp, 4),
                "sign": sign,
                "sign_zh": SIGN_LABELS_ZH[sign],
            }
        )
    return houses


def _build_thirteen_sectors(ascendant: float) -> List[Dict[str, Any]]:
    sectors: List[Dict[str, Any]] = []
    step = 360.0 / 13.0
    for sector_number in range(1, 14):
        cusp = normalize_angle(ascendant + (sector_number - 1) * step)
        sectors.append(
            {
                "sector": sector_number,
                "cusp_longitude": round(cusp, 4),
                "sign": _sign_name(cusp),
            }
        )
    return sectors


def _planet_set(chart_variant: str) -> List[str]:
    if chart_variant in {"hellen_chart", "guolao_chart"}:
        return list(TRADITIONAL_PLANETS)
    return list(PLANET_SEQUENCE)


def _build_planet_record(
    planet: str,
    longitude: float,
    latitude: float,
    ascendant: float,
    house_system: str,
    *,
    sidereal: bool = False,
    ayanamsha: float = 0.0,
    include_sector13: bool = False,
    include_nakshatra: bool = False,
    include_su28: bool = False,
) -> Dict[str, Any]:
    effective_longitude = normalize_angle(longitude - ayanamsha) if sidereal else normalize_angle(longitude)
    sign = _sign_name(effective_longitude)
    record = {
        "id": planet,
        "longitude": round(effective_longitude, 4),
        "latitude": round(latitude, 4),
        "sign": sign,
        "sign_zh": SIGN_LABELS_ZH[sign],
        "degree_in_sign": round(_degree_in_sign(effective_longitude), 4),
        "house": _house_for_longitude(effective_longitude, ascendant, house_system),
        "element": ELEMENT_BY_SIGN[sign],
        "modality": MODALITY_BY_SIGN[sign],
    }
    if include_sector13:
        record["sector13"] = _sector13_for_longitude(effective_longitude, ascendant)
    if include_nakshatra:
        record["nakshatra"] = _nakshatra(effective_longitude)
    if include_su28:
        record["su28"] = _su28(effective_longitude)
    return record


def _build_aspects(planets: Iterable[Dict[str, Any]], orb: float = 6.0) -> List[Dict[str, Any]]:
    items = list(planets)
    aspects: List[Dict[str, Any]] = []
    for index, first in enumerate(items):
        for second in items[index + 1:]:
            difference = abs(first["longitude"] - second["longitude"])
            if difference > 180:
                difference = 360 - difference
            matched: Optional[Tuple[str, float]] = None
            for aspect_name, exact_angle in ASPECTS:
                current_orb = abs(difference - exact_angle)
                if current_orb <= orb and (matched is None or current_orb < matched[1]):
                    matched = (aspect_name, current_orb)
            if matched is None:
                continue
            aspects.append(
                {
                    "planet_a": first["id"],
                    "planet_b": second["id"],
                    "aspect": matched[0],
                    "orb": round(matched[1], 4),
                }
            )
    return sorted(aspects, key=lambda item: (item["orb"], item["planet_a"], item["planet_b"]))


def _balance(planets: Iterable[Dict[str, Any]], key: str) -> Dict[str, int]:
    counter = Counter(item[key] for item in planets)
    return dict(counter)


def _summary(chart_variant: str, planets: List[Dict[str, Any]], aspects: List[Dict[str, Any]]) -> List[str]:
    sun = next((item for item in planets if item["id"] == "Sun"), None)
    moon = next((item for item in planets if item["id"] == "Moon"), None)
    top_aspect = aspects[0] if aspects else None
    lines = [f"已生成 {chart_variant} 的离线近似星盘。"]
    if sun is not None:
        lines.append(f"太阳落在 {sun['sign_zh']}，宫位 {sun['house']}。")
    if moon is not None:
        lines.append(f"月亮落在 {moon['sign_zh']}，宫位 {moon['house']}。")
    if top_aspect is not None:
        lines.append(
            f"{top_aspect['planet_a']} 与 {top_aspect['planet_b']} 形成 {top_aspect['aspect']}，容许度 {top_aspect['orb']}。"
        )
    return lines


def _sect(planets: List[Dict[str, Any]]) -> str:
    sun = next((item for item in planets if item["id"] == "Sun"), None)
    if sun is None:
        return "day"
    return "day" if sun["house"] >= 7 else "night"


def _fortune_lot(planets: List[Dict[str, Any]], ascendant: float) -> Dict[str, Any]:
    sun = next(item for item in planets if item["id"] == "Sun")
    moon = next(item for item in planets if item["id"] == "Moon")
    sect = _sect(planets)
    if sect == "day":
        longitude = normalize_angle(ascendant + moon["longitude"] - sun["longitude"])
    else:
        longitude = normalize_angle(ascendant + sun["longitude"] - moon["longitude"])
    sign = _sign_name(longitude)
    return {
        "longitude": round(longitude, 4),
        "sign": sign,
        "sign_zh": SIGN_LABELS_ZH[sign],
        "degree_in_sign": round(_degree_in_sign(longitude), 4),
    }


def _compatibility_score(inner: List[Dict[str, Any]], outer: List[Dict[str, Any]], aspects: List[Dict[str, Any]]) -> Dict[str, int]:
    inner_elements = Counter(item["element"] for item in inner if item["id"] in TRADITIONAL_PLANETS)
    outer_elements = Counter(item["element"] for item in outer if item["id"] in TRADITIONAL_PLANETS)
    inner_modalities = Counter(item["modality"] for item in inner if item["id"] in TRADITIONAL_PLANETS)
    outer_modalities = Counter(item["modality"] for item in outer if item["id"] in TRADITIONAL_PLANETS)

    def overlap_score(left: Counter, right: Counter) -> int:
        overlap = sum(min(left[key], right[key]) for key in left)
        total = max(sum(left.values()), sum(right.values()), 1)
        return int(round(100 * overlap / total))

    element_score = overlap_score(inner_elements, outer_elements)
    modality_score = overlap_score(inner_modalities, outer_modalities)
    harmony = 50
    for aspect in aspects[:24]:
        harmony += 4 if aspect["aspect"] in HARMONIOUS_ASPECTS else -4
    harmony = max(0, min(100, harmony))
    overall = int(round((element_score + modality_score + harmony) / 3))
    return {
        "element_harmony_score": element_score,
        "modality_balance_score": modality_score,
        "synastry_aspect_score": harmony,
        "overall_score": overall,
    }


def build_core_chart_payload(birth_info: AstroBirthInfo, chart_variant: str) -> Dict[str, Any]:
    julian_day = _julian_day(birth_info.utc_datetime)
    day_number = julian_day - 2451543.5
    sun_state = _sun_state(day_number)
    house_system = "whole_sign" if chart_variant in {"hellen_chart", "guolao_chart", "india_chart"} else "equal"
    sidereal = chart_variant == "india_chart"
    ayanamsha = _ayanamsha(julian_day) if sidereal else 0.0
    angle_state = _angles(julian_day, birth_info.longitude, birth_info.latitude)
    effective_ascendant = normalize_angle(angle_state["ascendant"] - ayanamsha) if sidereal else angle_state["ascendant"]
    effective_midheaven = normalize_angle(angle_state["midheaven"] - ayanamsha) if sidereal else angle_state["midheaven"]
    planet_states = {
        planet: _planet_state(planet, day_number, sun_state)
        for planet in _planet_set(chart_variant)
    }
    planets = [
        _build_planet_record(
            planet,
            planet_states[planet]["longitude"],
            planet_states[planet]["latitude"],
            effective_ascendant,
            house_system,
            sidereal=sidereal,
            ayanamsha=ayanamsha,
            include_sector13=chart_variant == "chart13",
            include_nakshatra=chart_variant == "india_chart",
            include_su28=chart_variant == "guolao_chart",
        )
        for planet in _planet_set(chart_variant)
    ]
    aspects = _build_aspects(planets)
    result: Dict[str, Any] = {
        "person_info": {
            "name": birth_info.name,
            "birth_place": birth_info.birth_place,
            "birth_timezone": birth_info.timezone,
            "birth_longitude": birth_info.longitude,
            "birth_latitude": birth_info.latitude,
            "birth_datetime": birth_info.local_datetime.isoformat(),
            "utc_datetime": birth_info.utc_datetime.isoformat(),
        },
        "chart_profile": {
            "chart_type": chart_variant,
            "zodiac": "sidereal" if sidereal else "tropical",
            "house_system": house_system,
            "tradition": chart_variant in {"hellen_chart", "guolao_chart"},
            "engine_precision": "approximate_orbital_model",
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
        "houses": _build_houses(effective_ascendant, house_system),
        "planets": planets,
        "aspects": aspects,
        "element_balance": _balance(planets, "element"),
        "modality_balance": _balance(planets, "modality"),
        "summary": _summary(chart_variant, planets, aspects),
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


def build_midpoint_payload(birth_info: AstroBirthInfo) -> Dict[str, Any]:
    base_chart = build_core_chart_payload(birth_info, "chart")
    midpoint_bodies = [
        item for item in base_chart["planets"] if item["id"] in TRADITIONAL_PLANETS
    ]
    midpoints: List[Dict[str, Any]] = []
    for index, first in enumerate(midpoint_bodies):
        for second in midpoint_bodies[index + 1:]:
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
            "engine_precision": "approximate_orbital_model",
            "analysis_focus": "midpoints",
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


def _composite_chart(inner_chart: Dict[str, Any], outer_chart: Dict[str, Any]) -> Dict[str, Any]:
    inner_planets = {item["id"]: item for item in inner_chart["planets"]}
    outer_planets = {item["id"]: item for item in outer_chart["planets"]}
    composite_planets: List[Dict[str, Any]] = []
    ascendant = _midpoint(
        inner_chart["angles"]["ascendant"]["longitude"],
        outer_chart["angles"]["ascendant"]["longitude"],
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
                (inner_planets[planet]["latitude"] + outer_planets[planet]["latitude"]) / 2.0,
                ascendant,
                "equal",
            )
        )
    return {
        "angles": {
            "ascendant": {
                "longitude": round(ascendant, 4),
                "sign": _sign_name(ascendant),
                "sign_zh": SIGN_LABELS_ZH[_sign_name(ascendant)],
            }
        },
        "houses": _build_houses(ascendant, "equal"),
        "planets": composite_planets,
        "aspects": _build_aspects(composite_planets),
    }


def build_relative_payload(
    inner_birth: AstroBirthInfo,
    outer_birth: AstroBirthInfo,
    relationship_mode: str = "synastry",
) -> Dict[str, Any]:
    inner_chart = build_core_chart_payload(inner_birth, "chart")
    outer_chart = build_core_chart_payload(outer_birth, "chart")
    synastry_aspects: List[Dict[str, Any]] = []
    for inner_planet in inner_chart["planets"]:
        for outer_planet in outer_chart["planets"]:
            if inner_planet["id"] not in TRADITIONAL_PLANETS or outer_planet["id"] not in TRADITIONAL_PLANETS:
                continue
            difference = abs(inner_planet["longitude"] - outer_planet["longitude"])
            if difference > 180:
                difference = 360 - difference
            for aspect_name, exact_angle in ASPECTS:
                orb = abs(difference - exact_angle)
                if orb <= 4.0:
                    synastry_aspects.append(
                        {
                            "inner": inner_planet["id"],
                            "outer": outer_planet["id"],
                            "aspect": aspect_name,
                            "orb": round(orb, 4),
                        }
                    )
                    break
    synastry_aspects = sorted(
        synastry_aspects,
        key=lambda item: (item["orb"], item["inner"], item["outer"]),
    )
    composite_chart = _composite_chart(inner_chart, outer_chart)
    compatibility = _compatibility_score(
        inner_chart["planets"], outer_chart["planets"], synastry_aspects
    )
    return {
        "relationship_profile": {
            "chart_type": "relative",
            "relationship_mode": relationship_mode,
            "engine_precision": "approximate_orbital_model",
        },
        "inner_chart": inner_chart,
        "outer_chart": outer_chart,
        "synastry_aspects": synastry_aspects,
        "composite_chart": composite_chart,
        "compatibility": compatibility,
        "summary": [
            "已生成 FateBridge 关系盘 / 合盘分析。",
            f"跨盘相位数量：{len(synastry_aspects)}。",
            f"综合分：{compatibility['overall_score']}。",
        ],
    }
