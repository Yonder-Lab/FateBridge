"""Angular, zodiacal and calendar geometry shared by chart families."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional

from fatebridge.core.astro import runtime
from fatebridge.core.astro.reference import NAKSHATRAS, SU28
from fatebridge.core.astrology_tables import SIGNS as SIGNS


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

    # Gregorian calendar from its 1582-10-15 introduction; Julian calendar for
    # earlier civil dates (matching swisseph's GREG_CAL/JUL_CAL convention).
    gregorian = (target.year, target.month, target.day) >= (1582, 10, 15)

    if month <= 2:
        year -= 1
        month += 12

    if gregorian:
        a = year // 100
        b = 2 - a + a // 4
    else:
        b = 0
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5


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
    """Lahiri ayanamsha in degrees.

    Prefer Swiss Ephemeris' authoritative Lahiri model when available — it
    includes the higher-order precession terms the linear fit below omits, so
    it stays correct for far-historic epochs (the linear form diverges by
    degrees pre-1000 CE, though it is accurate to <0.3′ for modern births).
    The linear drift is only an offline fallback; when it is used (no swisseph
    available, or a runtime failure) we log once so the degraded precision is
    never silent.
    """
    if runtime.swe is not None:
        try:
            with runtime.preserve_ephemeris_path():
                runtime.swe.set_sid_mode(runtime.swe.SIDM_LAHIRI, 0, 0)
                return float(runtime.swe.get_ayanamsa_ut(julian_day))
        except Exception as exc:  # pragma: no cover - swisseph runtime guard
            runtime._log_swe_runtime_failure("get_ayanamsa_ut", exc)
    else:
        runtime._log_swe_runtime_failure(
            "get_ayanamsa_ut",
            RuntimeError("swisseph unavailable; using linear ayanamsha approximation"),
        )
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
            _cos_deg(armc),
            -(
                _sin_deg(armc) * _cos_deg(epsilon)
                + math.tan(_deg_to_rad(latitude)) * _sin_deg(epsilon)
            ),
        )
    )
    ascendant = normalize_angle(ascendant)
    midheaven = _rad_to_deg(
        math.atan2(
            _sin_deg(armc),
            _cos_deg(armc) * _cos_deg(epsilon),
        )
    )
    midheaven = normalize_angle(midheaven)
    return {"ascendant": ascendant, "midheaven": midheaven}
