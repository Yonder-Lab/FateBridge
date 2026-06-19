"""
Offline astrology engine for FateBridge.

When a local Swiss Ephemeris runtime is available, core charts prefer it for
high-precision planetary and house calculations. The engine still preserves a
fully offline fallback path based on lightweight orbital approximations so the
chart family remains usable without external ephemeris files or network access.
"""

from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fatebridge.utils.helpers import parse_timezone_name, resolve_birth_place_context

try:
    import swisseph as swe
except ImportError:  # pragma: no cover - optional runtime dependency
    swe = None

logger = logging.getLogger(__name__)

# Log the first swisseph runtime failure so operators notice a broken ephemeris
# install instead of silently degrading to the approximation engine. Further
# failures are suppressed to avoid flooding the logs.
_SWE_RUNTIME_FAILURE_LOGGED = False


def _log_swe_runtime_failure(call: str, error: BaseException) -> None:
    global _SWE_RUNTIME_FAILURE_LOGGED
    if _SWE_RUNTIME_FAILURE_LOGGED:
        return
    _SWE_RUNTIME_FAILURE_LOGGED = True
    logger.warning(
        "Swiss Ephemeris %s raised %s (%s); falling back to the offline "
        "approximation engine. Subsequent failures will be suppressed.",
        call,
        type(error).__name__,
        error,
    )


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

KNOWN_ASTRO_PLACE_LATITUDES = {
    "北京": 39.9042,
    "上海": 31.2304,
    "天津": 39.3434,
    "重庆": 29.5630,
    "香港": 22.3193,
    "澳门": 22.1987,
    "台北": 25.0330,
    "河北": 38.0428,
    "山西": 37.8706,
    "辽宁": 41.8057,
    "吉林": 43.8171,
    "黑龙江": 45.8038,
    "江苏": 32.0603,
    "浙江": 30.2741,
    "安徽": 31.8206,
    "福建": 26.0745,
    "江西": 28.6829,
    "山东": 36.6512,
    "河南": 34.7466,
    "湖北": 30.5454,
    "湖南": 28.2282,
    "广东": 23.1291,
    "海南": 20.0440,
    "四川": 30.5728,
    "贵州": 26.6470,
    "云南": 25.0389,
    "陕西": 34.3416,
    "甘肃": 36.0611,
    "青海": 36.6171,
    "台湾": 25.0330,
    "内蒙古": 40.8426,
    "广西": 22.8170,
    "西藏": 29.6525,
    "宁夏": 38.4872,
    "新疆": 43.8256,
    "广州": 23.1291,
    "深圳": 22.5431,
    "杭州": 30.2741,
    "宁波": 29.8683,
    "南京": 32.0603,
    "苏州": 31.2989,
    "武汉": 30.5928,
    "成都": 30.5728,
    "西安": 34.3416,
    "乌鲁木齐": 43.8256,
    "石家庄": 38.0428,
    "济南": 36.6512,
    "青岛": 36.0671,
    "郑州": 34.7473,
    "长沙": 28.2282,
    "福州": 26.0745,
    "厦门": 24.4798,
    "合肥": 31.8206,
    "南昌": 28.6829,
    "昆明": 25.0389,
    "贵阳": 26.6470,
    "南宁": 22.8170,
    "海口": 20.0440,
    "呼和浩特": 40.8426,
    "银川": 38.4872,
    "兰州": 36.0611,
    "西宁": 36.6171,
    "拉萨": 29.6525,
    "喀什": 39.4704,
    "纽约": 40.7128,
    "伦敦": 51.5074,
    "东京": 35.6762,
    "悉尼": -33.8688,
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

PLANET_SWISSEPH_IDS = (
    {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mercury": swe.MERCURY,
        "Venus": swe.VENUS,
        "Mars": swe.MARS,
        "Jupiter": swe.JUPITER,
        "Saturn": swe.SATURN,
        "Uranus": swe.URANUS,
        "Neptune": swe.NEPTUNE,
        "Pluto": swe.PLUTO,
        "North Node": swe.MEAN_NODE,
    }
    if swe is not None
    else {}
)

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

RELATIVE_MODE_LABELS_ZH = {
    "compare": "比较盘",
    "composite": "组合盘",
    "influence": "影响盘",
    "timespace": "时空中点盘",
    "marks": "马克斯盘",
}

RELATIVE_ZODIACAL_LABELS_ZH = {
    0: "回归黄道",
    1: "恒星黄道，岁差:Lahiri",
}

RELATIVE_HOUSE_SYSTEM_SPECS: Dict[int, Dict[str, Any]] = {
    0: {
        "key": "whole_sign",
        "label_zh": "整宫制",
        "swisseph_code": b"W",
    },
    1: {
        "key": "alcabitus",
        "label_zh": "Alcabitus",
        "swisseph_code": b"B",
    },
    2: {
        "key": "regiomontanus",
        "label_zh": "Regiomontanus",
        "swisseph_code": b"R",
    },
    3: {
        "key": "placidus",
        "label_zh": "Placidus",
        "swisseph_code": b"P",
    },
    4: {
        "key": "koch",
        "label_zh": "Koch",
        "swisseph_code": b"K",
    },
    5: {
        "key": "vehlow_equal",
        "label_zh": "Vehlow Equal",
        "swisseph_code": b"V",
    },
    6: {
        "key": "polich_page",
        "label_zh": "Polich Page",
        "swisseph_code": b"T",
    },
    7: {
        "key": "sripati",
        "label_zh": "Sripati",
        "swisseph_code": b"S",
    },
    8: {
        "key": "equal_mc",
        "label_zh": "天顶为10宫中点等宫制",
        "swisseph_code": b"D",
    },
}

RELATIVE_MODE_NUMERIC_MAP = {
    0: "compare",
    1: "composite",
    2: "influence",
    3: "timespace",
    4: "marks",
}

RELATIVE_MODE_EXACT_ALIASES = {
    "Comp": "compare",
    "Composite": "composite",
    "Synastry": "influence",
    "TimeSpace": "timespace",
    "Marks": "marks",
}

RELATIVE_MODE_FALLBACK_ALIASES = {
    "compare": "compare",
    "comparison": "compare",
    "comp": "compare",
    "比较盘": "compare",
    "组合盘": "composite",
    "composite": "composite",
    "influence": "influence",
    "影响盘": "influence",
    "timespace": "timespace",
    "time space": "timespace",
    "时空中点盘": "timespace",
    "marks": "marks",
    "马克斯盘": "marks",
}

CORE_CHART_DEFAULT_HOUSE_SYSTEMS = {
    "chart": "equal",
    "chart13": "equal",
    "hellen_chart": "whole_sign",
    "guolao_chart": "whole_sign",
    "india_chart": "whole_sign",
}

CORE_CHART_DEFAULT_HOUSE_LABELS_ZH = {
    "equal": "等宫制（上升起点）",
    "whole_sign": "整宫制",
}

CORE_CHART_DEFAULT_ZODIACAL = {
    "chart": 0,
    "chart13": 0,
    "hellen_chart": 0,
    "guolao_chart": 0,
    "india_chart": 1,
}

PLANET_ORBITAL_ELEMENTS = {
    "Mercury": lambda d: (
        48.3313 + 3.24587e-5 * d,
        7.0047 + 5e-8 * d,
        29.1241 + 1.01444e-5 * d,
        0.387098,
        0.205635 + 5.59e-10 * d,
        168.6562 + 4.0923344368 * d,
    ),
    "Venus": lambda d: (
        76.6799 + 2.4659e-5 * d,
        3.3946 + 2.75e-8 * d,
        54.8910 + 1.38374e-5 * d,
        0.72333,
        0.006773 - 1.302e-9 * d,
        48.0052 + 1.6021302244 * d,
    ),
    "Mars": lambda d: (
        49.5574 + 2.11081e-5 * d,
        1.8497 - 1.78e-8 * d,
        286.5016 + 2.92961e-5 * d,
        1.523688,
        0.093405 + 2.516e-9 * d,
        18.6021 + 0.5240207766 * d,
    ),
    "Jupiter": lambda d: (
        100.4542 + 2.76854e-5 * d,
        1.303 - 1.557e-7 * d,
        273.8777 + 1.64505e-5 * d,
        5.20256,
        0.048498 + 4.469e-9 * d,
        19.895 + 0.0830853001 * d,
    ),
    "Saturn": lambda d: (
        113.6634 + 2.3898e-5 * d,
        2.4886 - 1.081e-7 * d,
        339.3939 + 2.97661e-5 * d,
        9.55475,
        0.055546 - 9.499e-9 * d,
        316.967 + 0.0334442282 * d,
    ),
    "Uranus": lambda d: (
        74.0005 + 1.3978e-5 * d,
        0.7733 + 1.9e-8 * d,
        96.6612 + 3.0565e-5 * d,
        19.18171 - 1.55e-8 * d,
        0.047318 + 7.45e-9 * d,
        142.5905 + 0.011725806 * d,
    ),
    "Neptune": lambda d: (
        131.7806 + 3.0173e-5 * d,
        1.77 - 2.55e-7 * d,
        272.8461 - 6.027e-6 * d,
        30.05826 + 3.313e-8 * d,
        0.008606 + 2.15e-9 * d,
        260.2471 + 0.005995147 * d,
    ),
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
    birth_longitude: Optional[float] = None,
    birth_latitude: Optional[float] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
) -> AstroBirthInfo:
    place_context = resolve_birth_place_context(birth_place)
    timezone_name = birth_timezone or place_context.timezone or "UTC"
    effective_longitude = (
        birth_longitude if birth_longitude is not None else place_context.longitude
    )
    inferred_latitude = KNOWN_ASTRO_PLACE_LATITUDES.get(
        place_context.canonical_name or ""
    )
    effective_latitude = (
        birth_latitude if birth_latitude is not None else inferred_latitude
    )
    if effective_longitude is None or effective_latitude is None:
        raise ValueError(
            "核心星盘需要 birth_longitude / birth_latitude，或提供 FateBridge 支持的 birth_place 以自动补全坐标。"
        )
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
        longitude=effective_longitude,
        latitude=effective_latitude,
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
    day = (
        target.day
        + (target.hour + target.minute / 60.0 + target.second / 3600.0) / 24.0
    )

    if month <= 2:
        year -= 1
        month += 12

    a = year // 100
    b = 2 - a + a // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


def _solve_kepler(mean_anomaly_deg: float, eccentricity: float) -> float:
    mean_anomaly_rad = _deg_to_rad(mean_anomaly_deg)
    estimate = mean_anomaly_rad
    for _ in range(8):
        numerator = estimate - eccentricity * math.sin(estimate) - mean_anomaly_rad
        denominator = 1 - eccentricity * math.cos(estimate)
        estimate -= numerator / denominator
    return estimate


def _planet_heliocentric_coords(
    planet: str, day_number: float
) -> Tuple[float, float, float]:
    (
        ascending_node,
        inclination,
        perihelion,
        semi_major_axis,
        eccentricity,
        mean_anomaly,
    ) = PLANET_ORBITAL_ELEMENTS[planet](day_number)
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


def _planet_state(
    planet: str, day_number: float, sun_state: Dict[str, float]
) -> Dict[str, float]:
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


def _continuous_house_cusps(house_cusps: List[float]) -> List[float]:
    continuous: List[float] = []
    for cusp in house_cusps:
        normalized = normalize_angle(cusp)
        if continuous:
            while normalized <= continuous[-1]:
                normalized += 360.0
        continuous.append(normalized)
    return continuous


def _house_for_longitude(
    longitude: float,
    ascendant: float,
    house_system: str,
    house_cusps: Optional[List[float]] = None,
) -> int:
    if house_cusps:
        continuous_cusps = _continuous_house_cusps(house_cusps)
        cycle_end = continuous_cusps[0] + 360.0
        continuous_longitude = normalize_angle(longitude)
        while continuous_longitude < continuous_cusps[0]:
            continuous_longitude += 360.0
        while continuous_longitude >= cycle_end:
            continuous_longitude -= 360.0
        for index, start in enumerate(continuous_cusps):
            end = (
                continuous_cusps[index + 1]
                if index < len(continuous_cusps) - 1
                else cycle_end
            )
            if start <= continuous_longitude < end:
                return index + 1
        return 12
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
    # Lahiri-like ayanamsha: base value at J2000.0 plus precession drift.
    # J2000 baseline ≈ 23.853°, precession ≈ 50.29"/yr ≈ 1.3971°/Julian century.
    centuries_since_j2000 = (julian_day - 2451545.0) / 36525.0
    return 23.853 + centuries_since_j2000 * 1.3971


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


def _swisseph_angles(
    julian_day: float,
    longitude: float,
    latitude: float,
) -> Optional[Dict[str, float]]:
    if swe is None:
        return None
    try:
        _, ascmc = swe.houses_ex(julian_day, latitude, longitude, b"E")
    except Exception as error:
        _log_swe_runtime_failure("houses_ex", error)
        return None
    return {
        "ascendant": normalize_angle(float(ascmc[0])),
        "midheaven": normalize_angle(float(ascmc[1])),
    }


def _build_houses(
    ascendant: float,
    house_system: str,
    house_cusps: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    houses: List[Dict[str, Any]] = []
    if house_cusps:
        for house_number, cusp in enumerate(house_cusps, start=1):
            normalized_cusp = normalize_angle(cusp)
            sign = _sign_name(normalized_cusp)
            houses.append(
                {
                    "house": house_number,
                    "cusp_longitude": round(normalized_cusp, 4),
                    "sign": sign,
                    "sign_zh": SIGN_LABELS_ZH[sign],
                }
            )
        return houses
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


def _swisseph_planet_state(
    planet: str,
    julian_day: float,
) -> Optional[Dict[str, float]]:
    if swe is None:
        return None
    planet_id = PLANET_SWISSEPH_IDS.get(planet)
    if planet_id is None:
        return None
    try:
        coordinates, _ = swe.calc_ut(julian_day, planet_id, swe.FLG_SWIEPH)
    except Exception as error:
        _log_swe_runtime_failure("calc_ut", error)
        return None
    return {
        "longitude": normalize_angle(float(coordinates[0])),
        "latitude": float(coordinates[1]),
    }


def _build_planet_states(
    chart_variant: str,
    julian_day: float,
    day_number: float,
) -> Tuple[Dict[str, Dict[str, float]], str, str]:
    planet_names = _planet_set(chart_variant)
    if swe is not None:
        ephemeris_states: Dict[str, Dict[str, float]] = {}
        for planet in planet_names:
            state = _swisseph_planet_state(planet, julian_day)
            if state is None:
                ephemeris_states = {}
                break
            ephemeris_states[planet] = state
        if ephemeris_states:
            return ephemeris_states, "ephemeris_runtime_model", "swisseph_api"

    sun_state = _sun_state(day_number)
    return (
        {
            planet: _planet_state(planet, day_number, sun_state)
            for planet in planet_names
        },
        "approximate_orbital_model",
        "fatebridge_approximate_orbital_model",
    )


def _derive_engine_profile(
    *profiles: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    precisions = {
        str(profile["engine_precision"])
        for profile in profiles
        if isinstance(profile, dict) and profile.get("engine_precision")
    }
    backends = {
        str(profile["engine_backend"])
        for profile in profiles
        if isinstance(profile, dict) and profile.get("engine_backend")
    }

    if not precisions:
        engine_precision = "approximate_orbital_model"
    elif len(precisions) == 1:
        engine_precision = next(iter(precisions))
    else:
        engine_precision = "mixed_precision_runtime_model"

    if not backends:
        if engine_precision == "ephemeris_runtime_model":
            engine_backend = "swisseph_api"
        elif engine_precision == "mixed_precision_runtime_model":
            engine_backend = "mixed_runtime_backends"
        else:
            engine_backend = "fatebridge_approximate_orbital_model"
    elif len(backends) == 1:
        engine_backend = next(iter(backends))
    else:
        engine_backend = "mixed_runtime_backends"

    return {
        "engine_precision": engine_precision,
        "engine_backend": engine_backend,
    }


def _precision_label_zh(engine_precision: str) -> str:
    if engine_precision == "ephemeris_runtime_model":
        return "离线高精度"
    if engine_precision == "mixed_precision_runtime_model":
        return "离线混合精度"
    return "离线近似"


def _precision_label_from_profiles(
    *profiles: Optional[Dict[str, Any]],
) -> str:
    return _precision_label_zh(_derive_engine_profile(*profiles)["engine_precision"])


def _build_planet_record(
    planet: str,
    longitude: float,
    latitude: float,
    ascendant: float,
    house_system: str,
    *,
    house_cusps: Optional[List[float]] = None,
    sidereal: bool = False,
    ayanamsha: float = 0.0,
    include_sector13: bool = False,
    include_nakshatra: bool = False,
    include_su28: bool = False,
) -> Dict[str, Any]:
    effective_longitude = (
        normalize_angle(longitude - ayanamsha)
        if sidereal
        else normalize_angle(longitude)
    )
    sign = _sign_name(effective_longitude)
    record = {
        "id": planet,
        "longitude": round(effective_longitude, 4),
        "latitude": round(latitude, 4),
        "sign": sign,
        "sign_zh": SIGN_LABELS_ZH[sign],
        "degree_in_sign": round(_degree_in_sign(effective_longitude), 4),
        "house": _house_for_longitude(
            effective_longitude,
            ascendant,
            house_system,
            house_cusps=house_cusps,
        ),
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


DEFAULT_PLANET_ORBS = {
    "Sun": 10.0,
    "Moon": 10.0,
    "Mercury": 7.0,
    "Venus": 7.0,
    "Mars": 7.5,
    "Jupiter": 9.0,
    "Saturn": 9.0,
    "Uranus": 5.0,
    "Neptune": 5.0,
    "Pluto": 5.0,
}


def _get_dynamic_orb(
    planet_a_id: str, planet_b_id: str, aspect_name: str, default_orb: float = 6.0
) -> float:
    orb_a = DEFAULT_PLANET_ORBS.get(planet_a_id, default_orb)
    orb_b = DEFAULT_PLANET_ORBS.get(planet_b_id, default_orb)
    base_orb = (orb_a + orb_b) / 2.0

    if aspect_name in {"sextile", "square"}:
        return base_orb * 0.8
    return base_orb


def _build_aspects(
    planets: Iterable[Dict[str, Any]], orb: float = 6.0
) -> List[Dict[str, Any]]:
    items = list(planets)
    aspects: List[Dict[str, Any]] = []
    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            difference = abs(first["longitude"] - second["longitude"])
            if difference > 180:
                difference = 360 - difference
            matched: Optional[Tuple[str, float]] = None
            for aspect_name, exact_angle in ASPECTS:
                current_orb = abs(difference - exact_angle)
                dynamic_max_orb = _get_dynamic_orb(
                    first["id"], second["id"], aspect_name, default_orb=orb
                )
                if current_orb <= dynamic_max_orb and (
                    matched is None or current_orb < matched[1]
                ):
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
    return sorted(
        aspects, key=lambda item: (item["orb"], item["planet_a"], item["planet_b"])
    )


def _balance(planets: Iterable[Dict[str, Any]], key: str) -> Dict[str, int]:
    counter = Counter(item[key] for item in planets)
    return dict(counter)


def _summary(
    chart_variant: str,
    planets: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
    *,
    engine_precision: str,
) -> List[str]:
    sun = next((item for item in planets if item["id"] == "Sun"), None)
    moon = next((item for item in planets if item["id"] == "Moon"), None)
    top_aspect = aspects[0] if aspects else None
    chart_label = (
        "离线高精度星盘"
        if engine_precision == "ephemeris_runtime_model"
        else "离线近似星盘"
    )
    lines = [f"已生成 {chart_variant} 的 {chart_label}。"]
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


def _compatibility_score(
    inner: List[Dict[str, Any]],
    outer: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
) -> Dict[str, int]:
    inner_elements = Counter(
        item["element"] for item in inner if item["id"] in TRADITIONAL_PLANETS
    )
    outer_elements = Counter(
        item["element"] for item in outer if item["id"] in TRADITIONAL_PLANETS
    )
    inner_modalities = Counter(
        item["modality"] for item in inner if item["id"] in TRADITIONAL_PLANETS
    )
    outer_modalities = Counter(
        item["modality"] for item in outer if item["id"] in TRADITIONAL_PLANETS
    )

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
    planet_states, engine_precision, engine_backend = _build_planet_states(
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
        "houses": _build_houses(
            effective_ascendant,
            house_system_info["key"],
            house_cusps=house_cusps,
        ),
        "planets": planets,
        "aspects": aspects,
        "element_balance": _balance(planets, "element"),
        "modality_balance": _balance(planets, "modality"),
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
        item for item in base_chart["planets"] if item["id"] in TRADITIONAL_PLANETS
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
        "summary": [
            f"已生成 FateBridge 组合盘{_precision_label_zh(engine_profile['engine_precision'])}层。",
            f"行星数量：{len(composite_planets)}。",
            f"相位数量：{len(aspects)}。",
        ],
    }


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


def _match_cross_aspect(
    longitude_a: float,
    longitude_b: float,
    orb: float = 4.0,
    planet_a_id: Optional[str] = None,
    planet_b_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    difference = abs(longitude_a - longitude_b)
    if difference > 180:
        difference = 360 - difference

    matched: Optional[Tuple[str, float]] = None
    for aspect_name, exact_angle in ASPECTS:
        current_orb = abs(difference - exact_angle)
        dynamic_max_orb = orb
        if planet_a_id and planet_b_id:
            dynamic_max_orb = _get_dynamic_orb(
                planet_a_id, planet_b_id, aspect_name, default_orb=orb
            )

        if current_orb <= dynamic_max_orb and (
            matched is None or current_orb < matched[1]
        ):
            matched = (aspect_name, current_orb)

    if matched is None:
        return None

    return {
        "aspect": matched[0],
        "delta": round(matched[1], 4),
    }


def _build_directional_relative_aspects(
    source_planets: List[Dict[str, Any]],
    target_planets: List[Dict[str, Any]],
    orb: float = 4.0,
) -> List[Dict[str, Any]]:
    grouped: List[Dict[str, Any]] = []

    for source_planet in source_planets:
        if source_planet["id"] not in TRADITIONAL_PLANETS:
            continue

        matches: List[Dict[str, Any]] = []
        for target_planet in target_planets:
            if target_planet["id"] not in TRADITIONAL_PLANETS:
                continue
            matched = _match_cross_aspect(
                source_planet["longitude"],
                target_planet["longitude"],
                orb=orb,
                planet_a_id=source_planet["id"],
                planet_b_id=target_planet["id"],
            )
            if matched is None:
                continue
            matches.append(
                {
                    "id": target_planet["id"],
                    "aspect": matched["aspect"],
                    "delta": matched["delta"],
                }
            )

        if not matches:
            continue

        grouped.append(
            {
                "id": source_planet["id"],
                "objects": sorted(
                    matches, key=lambda item: (item["delta"], item["id"])
                ),
            }
        )

    return grouped


def _flatten_directional_relative_aspects(
    grouped_aspects: List[Dict[str, Any]],
    *,
    source_key: str,
    target_key: str,
) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for item in grouped_aspects:
        source_id = item.get("id")
        if not source_id:
            continue
        for target in item.get("objects", []):
            target_id = target.get("id")
            if not target_id:
                continue
            flattened.append(
                {
                    source_key: source_id,
                    target_key: target_id,
                    "aspect": target["aspect"],
                    "orb": target["delta"],
                }
            )
    return flattened


def _build_relative_midpoint_catalog(
    target_planets: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    midpoint_bodies = [
        item for item in target_planets if item["id"] in TRADITIONAL_PLANETS
    ]
    catalog: List[Dict[str, Any]] = []
    for index, first in enumerate(midpoint_bodies):
        for second in midpoint_bodies[index + 1 :]:
            midpoint_longitude = _midpoint(first["longitude"], second["longitude"])
            catalog.append(
                {
                    "idA": first["id"],
                    "idB": second["id"],
                    "longitude": round(midpoint_longitude, 4),
                }
            )
    return catalog


def _build_directional_relative_midpoints(
    source_planets: List[Dict[str, Any]],
    target_planets: List[Dict[str, Any]],
    orb: float = 3.0,
) -> Dict[str, List[Dict[str, Any]]]:
    target_midpoints = _build_relative_midpoint_catalog(target_planets)
    midpoint_hits: Dict[str, List[Dict[str, Any]]] = {}

    for source_planet in source_planets:
        if source_planet["id"] not in TRADITIONAL_PLANETS:
            continue

        hits: List[Dict[str, Any]] = []
        for midpoint in target_midpoints:
            matched = _match_cross_aspect(
                source_planet["longitude"], midpoint["longitude"], orb=orb
            )
            if matched is None:
                continue
            hits.append(
                {
                    "midpoint": midpoint,
                    "aspect": matched["aspect"],
                    "delta": matched["delta"],
                }
            )

        if hits:
            midpoint_hits[source_planet["id"]] = sorted(
                hits,
                key=lambda item: (
                    item["delta"],
                    item["midpoint"]["idA"],
                    item["midpoint"]["idB"],
                ),
            )

    return midpoint_hits


def _antiscia_longitude(longitude: float) -> float:
    return normalize_angle(180.0 - longitude)


def _contra_antiscia_longitude(longitude: float) -> float:
    return normalize_angle(_antiscia_longitude(longitude) + 180.0)


def _build_directional_relative_antiscia(
    source_planets: List[Dict[str, Any]],
    target_planets: List[Dict[str, Any]],
    *,
    contra: bool = False,
    orb: float = 3.0,
) -> List[Dict[str, Any]]:
    matched_items: List[Dict[str, Any]] = []

    for source_planet in source_planets:
        if source_planet["id"] not in TRADITIONAL_PLANETS:
            continue

        for target_planet in target_planets:
            if target_planet["id"] not in TRADITIONAL_PLANETS:
                continue
            reference_longitude = (
                _contra_antiscia_longitude(target_planet["longitude"])
                if contra
                else _antiscia_longitude(target_planet["longitude"])
            )
            difference = abs(source_planet["longitude"] - reference_longitude)
            if difference > 180:
                difference = 360 - difference
            if difference > orb:
                continue
            matched_items.append(
                {
                    "idA": source_planet["id"],
                    "idB": target_planet["id"],
                    "delta": round(difference, 4),
                }
            )

    return sorted(
        matched_items,
        key=lambda item: (item["delta"], item["idA"], item["idB"]),
    )


def _count_directional_relative_midpoint_hits(
    midpoint_hits: Dict[str, List[Dict[str, Any]]],
) -> int:
    return sum(len(items) for items in midpoint_hits.values())


def _coerce_house_system_code(hsys: Any) -> Optional[int]:
    """Translate a user-facing house-system identifier into the internal 0-8 code.

    Accepts:
    - ``int``/``str`` numeric values in 0..8
    - Swiss Ephemeris single-letter codes (case-insensitive): P, K, W, R, B,
      V, T, S, D. These match the ``swisseph_code`` bytes on each spec entry
      and align astro/chart hsys with the ``house_system`` strings the
      astro/timing endpoints already accept.
    - Key strings like "placidus"/"whole_sign"/"koch" (case-insensitive),
      matching the internal ``key`` attribute.

    Returns the canonical integer code, or ``None`` if the input cannot be
    resolved (caller raises a descriptive error)."""
    if hsys is None:
        return None
    try:
        resolved_int = int(hsys)
    except (TypeError, ValueError):
        resolved_int = None
    else:
        if resolved_int in RELATIVE_HOUSE_SYSTEM_SPECS:
            return resolved_int

    if not isinstance(hsys, str):
        return None

    normalized = hsys.strip()
    if not normalized:
        return None

    if len(normalized) == 1:
        letter = normalized.upper().encode("ascii", errors="ignore")
        for code, spec in RELATIVE_HOUSE_SYSTEM_SPECS.items():
            if spec["swisseph_code"] == letter:
                return code

    folded = normalized.casefold()
    for code, spec in RELATIVE_HOUSE_SYSTEM_SPECS.items():
        if spec["key"].casefold() == folded:
            return code
        if spec["label_zh"].casefold() == folded:
            return code

    return None


def _resolve_offline_house_system(hsys: Any, *, context_label: str) -> Dict[str, Any]:
    resolved = _coerce_house_system_code(hsys)
    if resolved is None or resolved not in RELATIVE_HOUSE_SYSTEM_SPECS:
        raise ValueError(
            f"{context_label}离线模式暂仅支持 hsys=0..8（整宫制、Alcabitus、Regiomontanus、Placidus、Koch、Vehlow Equal、Polich Page、Sripati、天顶为10宫中点等宫制）。"
        )
    if swe is None and resolved != 0:
        raise ValueError(
            f"当前环境缺少 swisseph，{context_label}离线模式仅能在 hsys=0(整宫制) 下运行。"
        )
    return {"value": resolved, **RELATIVE_HOUSE_SYSTEM_SPECS[resolved]}


def _resolve_relative_house_system(hsys: Any) -> Dict[str, Any]:
    return _resolve_offline_house_system(hsys, context_label="relative 关系盘")


def _resolve_core_chart_house_system(
    hsys: Any,
    *,
    chart_variant: str,
) -> Dict[str, Any]:
    if hsys in (None, ""):
        default_house_system = CORE_CHART_DEFAULT_HOUSE_SYSTEMS[chart_variant]
        return {
            "value": None,
            "key": default_house_system,
            "label_zh": CORE_CHART_DEFAULT_HOUSE_LABELS_ZH[default_house_system],
            "source": "variant_default",
        }
    return {
        **_resolve_offline_house_system(hsys, context_label="核心星盘"),
        "source": "explicit",
    }


def _resolve_offline_zodiacal_mode(
    zodiacal: Any,
    *,
    context_label: str,
) -> Dict[str, Any]:
    try:
        resolved = int(zodiacal)
    except (TypeError, ValueError):
        raise ValueError(
            f"{context_label}离线模式暂仅支持 zodiacal=0(回归黄道) 或 zodiacal=1(恒星黄道/Lahiri)。"
        )
    if resolved not in RELATIVE_ZODIACAL_LABELS_ZH:
        raise ValueError(
            f"{context_label}离线模式暂仅支持 zodiacal=0(回归黄道) 或 zodiacal=1(恒星黄道/Lahiri)。"
        )
    return {
        "value": resolved,
        "zodiac": "sidereal" if resolved == 1 else "tropical",
        "label_zh": RELATIVE_ZODIACAL_LABELS_ZH[resolved],
        "sidereal": resolved == 1,
    }


def _resolve_relative_zodiacal_mode(zodiacal: Any) -> Dict[str, Any]:
    return _resolve_offline_zodiacal_mode(
        zodiacal,
        context_label="relative 关系盘",
    )


def _resolve_core_chart_zodiacal_mode(
    zodiacal: Any,
    *,
    chart_variant: str,
) -> Dict[str, Any]:
    if zodiacal in (None, ""):
        return {
            **_resolve_offline_zodiacal_mode(
                CORE_CHART_DEFAULT_ZODIACAL[chart_variant],
                context_label="核心星盘",
            ),
            "source": "variant_default",
        }
    return {
        **_resolve_offline_zodiacal_mode(
            zodiacal,
            context_label="核心星盘",
        ),
        "source": "explicit",
    }


def _relative_zodiac_profile_overrides(
    zodiacal_info: Dict[str, Any],
    *,
    ayanamsha: Optional[float] = None,
) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {
        "zodiac": zodiacal_info["zodiac"],
        "zodiacal": zodiacal_info["value"],
        "zodiac_label_zh": zodiacal_info["label_zh"],
    }
    if ayanamsha is not None:
        overrides["ayanamsha"] = round(ayanamsha, 4)
    return overrides


def _relative_house_profile_overrides(
    house_system_info: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "house_system": house_system_info["key"],
        "house_system_code": house_system_info["value"],
        "house_system_label_zh": house_system_info["label_zh"],
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


def _rehouse_chart_payload(
    chart_payload: Dict[str, Any],
    *,
    house_system: str,
    house_cusps: Optional[List[float]] = None,
) -> Dict[str, Any]:
    ascendant = chart_payload["angles"]["ascendant"]["longitude"]
    planets = [
        _build_planet_record(
            item["id"],
            item["longitude"],
            item.get("latitude", 0.0),
            ascendant,
            house_system,
            house_cusps=house_cusps,
        )
        for item in sorted(chart_payload["planets"], key=_planet_sort_key)
    ]
    chart_profile = dict(chart_payload.get("chart_profile", {}))
    chart_profile["house_system"] = house_system
    return {
        **chart_payload,
        "chart_profile": chart_profile,
        "houses": _build_houses(ascendant, house_system, house_cusps=house_cusps),
        "planets": planets,
        "aspects": _build_aspects(planets),
        "element_balance": _balance(planets, "element"),
        "modality_balance": _balance(planets, "modality"),
    }


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

    if swe is None or house_system_info["key"] in {"whole_sign", "equal"}:
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
            for item in _build_houses(ascendant, house_system_info["key"])
        ]
        return {
            "ascendant": ascendant,
            "midheaven": midheaven,
            "house_cusps": house_cusps,
            "ayanamsha": ayanamsha,
        }

    cusps, ascmc = swe.houses_ex(
        julian_day,
        birth_info.latitude,
        birth_info.longitude,
        house_system_info["swisseph_code"],
    )
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


def _chart_source_planets(chart_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "id": item["id"],
            "longitude": item["longitude"],
            "latitude": item.get("latitude", 0.0),
        }
        for item in chart_payload["planets"]
    ]


def _relative_chart_positions(
    chart_payload: Dict[str, Any],
    *,
    zodiacal_info: Dict[str, Any],
    utc_datetime: datetime,
) -> Tuple[List[Dict[str, Any]], float, float, Optional[float]]:
    source_planets = _chart_source_planets(chart_payload)
    ascendant = chart_payload["angles"]["ascendant"]["longitude"]
    midheaven = chart_payload["angles"]["midheaven"]["longitude"]
    ayanamsha: Optional[float] = None

    if zodiacal_info["sidereal"]:
        ayanamsha = _ayanamsha(_julian_day(utc_datetime))
        source_planets = [
            {
                **item,
                "longitude": normalize_angle(item["longitude"] - ayanamsha),
            }
            for item in source_planets
        ]
        ascendant = normalize_angle(ascendant - ayanamsha)
        midheaven = normalize_angle(midheaven - ayanamsha)

    return source_planets, ascendant, midheaven, ayanamsha


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


# 关系取向（婚姻/恋爱）的解读侧重：强调宫位 + 关键星体，并据此过滤 synastry 相位。
RELATIONSHIP_FOCUS_DEFS: Dict[str, Dict[str, Any]] = {
    "marriage": {
        "label_zh": "婚姻",
        "houses": [7],
        "bodies": ["Sun", "Moon", "Venus", "Saturn"],
        "note": "婚姻取向：重点观察第7宫（夫妻宫）与日/月/金星/土星之间的 synastry 相位。",
    },
    "romance": {
        "label_zh": "恋爱",
        "houses": [5],
        "bodies": ["Sun", "Moon", "Venus", "Mars"],
        "note": "恋爱取向：重点观察第5宫（恋爱宫）与日/月/金星/火星之间的 synastry 相位。",
    },
}

_RELATIONSHIP_FOCUS_ALIASES = {
    "marriage": "marriage",
    "marry": "marriage",
    "婚姻": "marriage",
    "结婚": "marriage",
    "romance": "romance",
    "romantic": "romance",
    "dating": "romance",
    "love": "romance",
    "恋爱": "romance",
    "戀愛": "romance",
    "general": "general",
    "泛": "general",
    "none": "general",
    "": "general",
}


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


def _build_compare_relative_payload(
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
) -> Dict[str, Any]:
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
                    composite_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "directional_synastry",
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
        "chart": {},
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
        "summary": [
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
    }


def _build_composite_relative_payload(
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
) -> Dict[str, Any]:
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
                    composite_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "composite_chart",
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
        "chart": composite_chart,
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
        "summary": [
            "已生成 FateBridge 组合盘分析。",
            f"合成盘行星数量：{len(composite_chart.get('planets', []))}。",
            f"A对B相位主体数：{len(in_to_out_aspects)}。",
            f"A对B中点相位命中：{_count_directional_relative_midpoint_hits(in_to_out_midpoint)}。",
            f"A对B映点命中：{len(in_to_out_antiscia)}。",
            f"综合分：{compatibility['overall_score']}。",
            "影响图盘、中点相位与映点/反映点均已提供"
            f"{_precision_label_from_profiles(inner_chart.get('chart_profile', {}), outer_chart.get('chart_profile', {}), composite_chart.get('chart_profile', {}))}结果。",
        ],
    }


def _build_influence_relative_payload(
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
) -> Dict[str, Any]:
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
                    composite_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "influence_chart_pair",
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
        "chart": composite_chart,
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
        "summary": [
            "已生成 FateBridge 影响盘分析。",
            f"A视角影响图盘星体数：{len(inner_influence.get('chart', {}).get('planets', []))}。",
            f"B视角影响图盘星体数：{len(outer_influence.get('chart', {}).get('planets', []))}。",
            f"A对B相位主体数：{len(in_to_out_aspects)}。",
            f"综合分：{compatibility['overall_score']}。",
            "合成图盘保留在 chart / composite_chart 中，作为影响盘的辅助层。",
        ],
    }


def _build_timespace_relative_payload(
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
    timespace_chart: Dict[str, Any],
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
) -> Dict[str, Any]:
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
                    timespace_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "timespace_chart",
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
        "chart": timespace_chart,
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
        "summary": [
            "已生成 FateBridge 时空中点盘分析。",
            f"时空中点盘行星数量：{len(timespace_chart.get('planets', []))}。",
            f"A对B相位主体数：{len(in_to_out_aspects)}。",
            f"综合分：{compatibility['overall_score']}。",
            (
                "主 chart 层采用双方出生时间与地理位置中点生成的"
                f"{_precision_label_zh(timespace_chart.get('chart_profile', {}).get('engine_precision', 'approximate_orbital_model'))}盘。"
            ),
        ],
    }


def _build_marks_relative_payload(
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
    marks_chart: Dict[str, Any],
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
) -> Dict[str, Any]:
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
                    marks_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "marks_chart",
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
        "chart": marks_chart,
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
        "summary": [
            "已生成 FateBridge 马克斯盘分析。",
            f"马克斯盘行星数量：{len(marks_chart.get('planets', []))}。",
            f"A对B相位主体数：{len(in_to_out_aspects)}。",
            f"综合分：{compatibility['overall_score']}。",
            (
                "主 chart 层采用组合盘与时空中点盘之间的"
                f"{_precision_label_zh(marks_chart.get('chart_profile', {}).get('engine_precision', 'approximate_orbital_model'))}派生结果。"
            ),
        ],
    }


def _build_unimplemented_relative_payload(
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
) -> Dict[str, Any]:
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
                    composite_chart.get("chart_profile", {}),
                ),
            ),
            "primary_layer": "placeholder",
            "mode_status": "placeholder",
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
        "chart": {},
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
        "summary": [
            f"已生成 FateBridge {relative_mode_info['label_zh']} 占位输出。",
            f"A对B相位主体数：{len(in_to_out_aspects)}。",
            f"A对B中点相位命中：{_count_directional_relative_midpoint_hits(in_to_out_midpoint)}。",
            f"A对B映点命中：{len(in_to_out_antiscia)}。",
            f"综合分：{compatibility['overall_score']}。",
            "该模式的深层图盘算法尚未实现，当前已提供兼容 contract、方向相位层、影响图盘，以及中点/映点"
            f"{_precision_label_from_profiles(inner_chart.get('chart_profile', {}), outer_chart.get('chart_profile', {}), composite_chart.get('chart_profile', {}))}结果。",
        ],
    }


def build_relative_payload(
    inner_birth: AstroBirthInfo,
    outer_birth: AstroBirthInfo,
    relative_mode: Any = None,
    relative_mode_source: str = "default",
    hsys: int = 0,
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
        payload = _build_compare_relative_payload(**shared_kwargs)
    elif normalized_mode == "composite":
        payload = _build_composite_relative_payload(**shared_kwargs)
    elif normalized_mode == "influence":
        payload = _build_influence_relative_payload(**shared_kwargs)
    elif normalized_mode == "timespace":
        payload = _build_timespace_relative_payload(
            **shared_kwargs, timespace_chart=timespace_chart
        )
    elif normalized_mode == "marks":
        payload = _build_marks_relative_payload(
            **shared_kwargs, marks_chart=marks_chart
        )
    else:
        payload = _build_unimplemented_relative_payload(**shared_kwargs)

    # 关系取向解读侧重对所有盘式通用，在分发后统一附加一次。
    payload.setdefault("relationship_profile", {})["focus"] = relationship_focus_block(
        relationship_focus, synastry_aspects
    )
    return payload
