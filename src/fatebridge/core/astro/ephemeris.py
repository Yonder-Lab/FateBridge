"""Native ephemeris calls and explicit approximation fallback."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fatebridge.core import guolao_moira
from fatebridge.core.astro import runtime
from fatebridge.core.astro.geometry import normalize_angle
from fatebridge.core.astro.orbits import _planet_state, _sun_state
from fatebridge.core.astro.profiles import _consolidate_ephemeris_model
from fatebridge.core.astro.reference import (
    PLANET_SEQUENCE,
    PLANET_SWISSEPH_IDS,
    TRADITIONAL_PLANETS,
)


def _swisseph_angles(
    julian_day: float,
    longitude: float,
    latitude: float,
) -> Optional[Dict[str, float]]:
    if runtime.swe is None:
        return None
    try:
        _, ascmc = runtime.swe.houses_ex(julian_day, latitude, longitude, b"E")
    except Exception as error:
        runtime._log_swe_runtime_failure("houses_ex", error)
        return None
    return {
        "ascendant": normalize_angle(float(ascmc[0])),
        "midheaven": normalize_angle(float(ascmc[1])),
    }


def _planet_set(chart_variant: str) -> List[str]:
    if chart_variant in {"hellen_chart", "guolao_chart"}:
        return list(TRADITIONAL_PLANETS)
    return list(PLANET_SEQUENCE)


def _swisseph_planet_state(
    planet: str,
    julian_day: float,
) -> Optional[Tuple[Dict[str, float], str]]:
    """Return ``(state, ephemeris_model)`` for a planet, or ``None`` on failure.

    ``ephemeris_model`` reports the model swisseph *actually* used ("swieph" when
    data files are present, "moshier" when it silently downgraded to the built-in
    analytical model). A ``retflag < 0`` is treated as a failure so it falls
    through to the offline approximation engine instead of being accepted as a
    valid position.
    """
    if runtime.swe is None:
        return None
    planet_id = PLANET_SWISSEPH_IDS.get(planet)
    if planet_id is None:
        return None
    try:
        coordinates, retflag = runtime.ephemeris_call(
            "calc_ut",
            julian_day,
            planet_id,
            runtime.swe.FLG_SWIEPH | runtime.swe.FLG_SPEED,
        )
    except Exception as error:
        runtime._log_swe_runtime_failure("calc_ut", error)
        return None
    if retflag < 0:
        runtime._log_swe_runtime_failure("calc_ut", RuntimeError(f"retflag={retflag}"))
        return None
    state = {
        "longitude": normalize_angle(float(coordinates[0])),
        "latitude": float(coordinates[1]),
        "longitude_speed": float(coordinates[3]),
    }
    # Second pass in equatorial coordinates: ``coordinates[1]`` becomes the
    # declination, which drives the out-of-bounds flag. A soft failure here only
    # costs the declination key — the ecliptic position above is still valid, so
    # the planet still places and out-of-bounds simply reports "unknown".
    try:
        equatorial, eq_retflag = runtime.ephemeris_call(
            "calc_ut",
            julian_day,
            planet_id,
            runtime.swe.FLG_SWIEPH | runtime.swe.FLG_EQUATORIAL,
        )
        if eq_retflag >= 0:
            state["declination"] = float(equatorial[1])
    except Exception as error:  # pragma: no cover - defensive, ecliptic still usable
        runtime._log_swe_runtime_failure("calc_ut(equatorial)", error)
    return state, runtime.ephemeris_model_from_retflag(retflag)


def _guolao_si_yu_signidx(
    julian_day: float,
    sidereal: bool,
    ayanamsha: float,
) -> Dict[str, int]:
    """七政四余 之 四余（孛/罗/计/炁）的星座序号（0=白羊…11=双鱼）。

    孛 = 月亮平均远地点（swisseph ``MEAN_APOG``）；罗 = 月亮平交点（``MEAN_NODE``）；
    计 = 罗 + 180°。紫炁（木余）无 swisseph 对应，由 ``guolao_moira.purple_clouds_longitude``
    以 horosa 标定的线性步紫气算出（不依赖星历，恒可得）。孛/罗/计 在星历缺失时回退 -1。
    """

    def _eff(lon: float) -> int:
        effective = (
            normalize_angle(lon - ayanamsha) if sidereal else normalize_angle(lon)
        )
        return int(effective // 30) % 12

    # 紫炁：纯线性公式，与 swisseph 无关，先行算出。
    result = {
        "孛": -1,
        "罗": -1,
        "计": -1,
        "炁": _eff(guolao_moira.purple_clouds_longitude(julian_day)),
    }
    if runtime.swe is None:
        return result

    def _sign_idx(body_id: int) -> int:
        try:
            coordinates, retflag = runtime.ephemeris_call(
                "calc_ut", julian_day, body_id, runtime.swe.FLG_SWIEPH
            )
        except Exception as error:  # pragma: no cover - swe runtime guard
            runtime._log_swe_runtime_failure("calc_ut", error)
            return -1
        if retflag < 0:
            return -1
        return _eff(float(coordinates[0]))

    apogee_id = getattr(runtime.swe, "MEAN_APOG", 12)
    result["孛"] = _sign_idx(apogee_id)
    node_idx = _sign_idx(runtime.swe.MEAN_NODE)
    result["罗"] = node_idx
    if node_idx >= 0:
        result["计"] = (node_idx + 6) % 12
    return result


def _build_planet_states(
    chart_variant: str,
    julian_day: float,
    day_number: float,
) -> Tuple[Dict[str, Dict[str, float]], str, str, str]:
    planet_names = _planet_set(chart_variant)
    if runtime.swe is not None:
        ephemeris_states: Dict[str, Dict[str, float]] = {}
        models: set[str] = set()
        for planet in planet_names:
            result = _swisseph_planet_state(planet, julian_day)
            if result is None:
                ephemeris_states = {}
                break
            state, model = result
            ephemeris_states[planet] = state
            models.add(model)
        if ephemeris_states:
            return (
                ephemeris_states,
                "ephemeris_runtime_model",
                "swisseph_api",
                _consolidate_ephemeris_model(models),
            )

    sun_state = _sun_state(day_number)
    return (
        {
            planet: _planet_state(planet, day_number, sun_state)
            for planet in planet_names
        },
        "approximate_orbital_model",
        "fatebridge_approximate_orbital_model",
        "none",
    )
