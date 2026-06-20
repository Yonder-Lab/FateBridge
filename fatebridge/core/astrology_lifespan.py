"""
FateBridge western *lifespan* techniques.

This module hosts a family of classical western-astrology techniques that read a
single natal chart and project it across a whole life rather than around one
target date. None of them needs an external "analysis moment" — they are pure
functions of the natal positions plus a fixed table or a fixed progression rate,
which makes them deterministic and cheap to verify.

The five techniques:

* :func:`build_harmonic_payload` — 调波盘 (harmonic chart): natal longitudes
  multiplied by an integer ``harmonic`` number, then re-read for conjunctions.
* :func:`build_planetary_ages_payload` — 行星年龄 (Ptolemy's seven ages):
  a fixed age table mapping each life band to its ruling planet.
* :func:`build_triplicity_rulers_payload` — 三分主星推运: the sect light's
  triplicity rulers, ordered by sect, divide life into three qualitative stages.
* :func:`build_lunation_phase_payload` — 月相推运: the natal Sun–Moon
  elongation advanced at the secondary synodic rate across the eight lunar phases.
* :func:`build_distributions_payload` — 界推运 / 分配法: the Ascendant directed
  through the Egyptian bounds, each bound's lord governing one period.

Every builder takes an already-built kerykeion ``subject`` (and, where a real
calendar age matters, the :class:`AstroBirthInfo`) and returns a plain ``dict``.
Envelope assembly and snapshot rendering live in the service layer, mirroring
``western_timing_tools`` — this module stays computation-only.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fatebridge.core.astrology import ELEMENT_BY_SIGN
from fatebridge.core.astrology_predictive import (
    TIMING_POINT_NAMES,
    longitude_to_point_dict,
    normalize_sign_name,
    planet_label,
    resolve_egyptian_bound,
    sign_label,
)

# ---------------------------------------------------------------------------
# Fixed classical tables.
# ---------------------------------------------------------------------------

# Ptolemy's seven ages of man (Tetrabiblos IV.10). Each entry is the *start* age
# of the band in years; the band runs until the next entry's start (Saturn runs
# open-ended to the end of life). The order is the natural planetary speed order
# from fastest (Moon) to slowest (Saturn).
PTOLEMY_SEVEN_AGES: List[tuple[str, float, Optional[float]]] = [
    ("Moon", 0.0, 4.0),
    ("Mercury", 4.0, 14.0),
    ("Venus", 14.0, 22.0),
    ("Sun", 22.0, 41.0),
    ("Mars", 41.0, 56.0),
    ("Jupiter", 56.0, 68.0),
    ("Saturn", 68.0, None),
]
PTOLEMY_AGE_THEMES_ZH: Dict[str, str] = {
    "Moon": "婴幼期：身体与情绪的萌发",
    "Mercury": "学习期：心智、语言与技能成形",
    "Venus": "青春期：情感、审美与人际觉醒",
    "Sun": "壮年期：自我确立与社会角色巅峰",
    "Mars": "盛年期：进取、竞争与行动力",
    "Jupiter": "成熟期：经验沉淀与扩展整合",
    "Saturn": "晚年期：收束、责任与时间的清算",
}

# Dorothean triplicity rulers — the standard table used for triplicity life-period
# techniques (distinct from the Ptolemaic variant, which we deliberately do not
# use here). Each element maps to its day ruler, night ruler, and the cooperating
# "participating" ruler.
DOROTHEAN_TRIPLICITY_RULERS: Dict[str, Dict[str, str]] = {
    "Fire": {"day": "Sun", "night": "Jupiter", "participating": "Saturn"},
    "Earth": {"day": "Venus", "night": "Moon", "participating": "Mars"},
    "Air": {"day": "Saturn", "night": "Mercury", "participating": "Jupiter"},
    "Water": {"day": "Venus", "night": "Mars", "participating": "Moon"},
}
ELEMENT_LABELS_ZH: Dict[str, str] = {
    "Fire": "火象",
    "Earth": "土象",
    "Air": "风象",
    "Water": "水象",
}

# Classical planetary period-years (行星期), used to time triplicity stage handovers.
PLANETARY_PERIOD_YEARS: Dict[str, int] = {
    "Sun": 19,
    "Moon": 25,
    "Mercury": 20,
    "Venus": 8,
    "Mars": 15,
    "Jupiter": 12,
    "Saturn": 30,
}

# Nominal lifespan that triplicity stages divide. 75 matches the 星阙/Horosa
# reference default; it is an explicit dividing convention, not a prediction.
TRIPLICITY_DEFAULT_LIFESPAN = 75.0

# House angularity classes (角/续/果宫) for a quick ruler-strength readout.
ANGULAR_HOUSES = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}
ANGULARITY_LABELS_ZH = {
    "angular": "角宫·旺",
    "succedent": "续宫·中",
    "cadent": "果宫·衰",
}

# The eight lunar phases, each spanning 45° of Sun–Moon elongation.
LUNAR_PHASES: List[tuple[str, str, float]] = [
    ("new", "新月", 0.0),
    ("crescent", "蛾眉月", 45.0),
    ("first_quarter", "上弦月", 90.0),
    ("gibbous", "盈凸月", 135.0),
    ("full", "满月", 180.0),
    ("disseminating", "亏凸月", 225.0),
    ("last_quarter", "下弦月", 270.0),
    ("balsamic", "残月", 315.0),
]
# Mean secondary synodic rate: mean Moon motion (≈13.176°/day) minus mean Sun
# motion (≈0.985°/day) ≈ 12.1907°/day. Under "a day for a year" this is the
# elongation gained per year of life. Pinned to 12.1908 to stay value-for-value
# with the 星阙/Horosa reference engine (its ``PROG_ELONG_RATE``), so the two
# systems cross-validate exactly rather than drifting at the 4th decimal.
SECONDARY_SYNODIC_RATE_DEG_PER_YEAR = 12.1908

# Time-key rates for directing the Ascendant in 界推运 (degrees of arc per year).
DISTRIBUTION_TIME_KEY_RATES: Dict[str, float] = {
    "Ptolemy": 1.0,
    "Naibod": 0.98564733,
}


# ---------------------------------------------------------------------------
# Small geometry helpers.
# ---------------------------------------------------------------------------


def _wrap360(degree: float) -> float:
    """Normalize an angle into the ``[0, 360)`` range."""
    return degree % 360.0


def _angular_separation(first_degree: float, second_degree: float) -> float:
    """Smallest unsigned separation between two ecliptic longitudes (0–180°)."""
    delta = abs(_wrap360(first_degree) - _wrap360(second_degree)) % 360.0
    return delta if delta <= 180.0 else 360.0 - delta


def _natal_longitudes(natal_reference: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Map ``TIMING_POINT_NAMES`` to their absolute natal longitudes."""
    longitudes: Dict[str, float] = {}
    for point_name in TIMING_POINT_NAMES:
        point = natal_reference.get(point_name.lower())
        if point is not None:
            longitudes[point_name] = float(point["absolute_degree"])
    return longitudes


def _angularity(house: Optional[int]) -> Optional[str]:
    """Classify a house number as angular / succedent / cadent."""
    if house is None:
        return None
    if house in ANGULAR_HOUSES:
        return "angular"
    if house in SUCCEDENT_HOUSES:
        return "succedent"
    return "cadent"


def _planet_condition(
    point_name: str, natal_reference: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Compact natal placement of ``point_name`` for ruler/age readouts."""
    point = natal_reference.get(point_name.lower(), {})
    house = point.get("house")
    angularity = _angularity(house)
    return {
        "planet": point_name,
        "planet_label": planet_label(point_name),
        "sign": point.get("sign"),
        "sign_label": point.get("sign_label"),
        "degree": point.get("degree"),
        "house": house,
        "house_label": point.get("house_label"),
        "angularity": angularity,
        "angularity_label": ANGULARITY_LABELS_ZH.get(angularity or ""),
        "retrograde": point.get("retrograde"),
    }


# ---------------------------------------------------------------------------
# 1. 调波盘 (harmonic chart).
# ---------------------------------------------------------------------------


def build_harmonic_payload(
    natal_reference: Dict[str, Dict[str, Any]],
    *,
    harmonic: int,
    orb: float,
) -> Dict[str, Any]:
    """
    Build the harmonic chart: each natal longitude is multiplied by ``harmonic``
    and reduced mod 360. Bodies that fall within ``orb`` of each other in this
    harmonic field form 同频合相 (harmonic conjunctions).
    """
    longitudes = _natal_longitudes(natal_reference)

    positions: Dict[str, Dict[str, Any]] = {}
    for point_name, natal_lon in longitudes.items():
        harmonic_lon = _wrap360(natal_lon * harmonic)
        position = longitude_to_point_dict(point_name, harmonic_lon)
        position["natal_absolute_degree"] = round(natal_lon, 4)
        positions[point_name.lower()] = position

    conjunctions: List[Dict[str, Any]] = []
    ordered = list(longitudes.keys())
    for index, first_name in enumerate(ordered):
        for second_name in ordered[index + 1 :]:
            separation = _angular_separation(
                positions[first_name.lower()]["absolute_degree"],
                positions[second_name.lower()]["absolute_degree"],
            )
            if separation <= orb:
                conjunctions.append(
                    {
                        "points": [first_name, second_name],
                        "points_label": [
                            planet_label(first_name),
                            planet_label(second_name),
                        ],
                        "separation_degree": round(separation, 4),
                        "orb": orb,
                    }
                )
    conjunctions.sort(key=lambda item: item["separation_degree"])

    return {
        "harmonic": harmonic,
        "orb": orb,
        "method": "natal_longitude_times_harmonic",
        "method_label": f"{harmonic} 调波（本命黄经 × {harmonic} 取模 360°）",
        "positions": positions,
        "resonant_conjunctions": conjunctions,
    }


# ---------------------------------------------------------------------------
# 2. 行星年龄 (Ptolemy's seven ages).
# ---------------------------------------------------------------------------


def build_planetary_ages_payload(
    natal_reference: Dict[str, Dict[str, Any]],
    *,
    current_age_years: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Build Ptolemy's seven-ages table. Each life band is governed by one of the
    seven traditional planets; when ``current_age_years`` is given, the active
    band is flagged.
    """
    bands: List[Dict[str, Any]] = []
    active_planet: Optional[str] = None
    for planet, start_age, end_age in PTOLEMY_SEVEN_AGES:
        is_active = (
            current_age_years is not None
            and start_age <= current_age_years
            and (end_age is None or current_age_years < end_age)
        )
        if is_active:
            active_planet = planet
        bands.append(
            {
                "planet": planet,
                "planet_label": planet_label(planet),
                "start_age": start_age,
                "end_age": end_age,
                "duration_years": (
                    None if end_age is None else round(end_age - start_age, 2)
                ),
                "theme": PTOLEMY_AGE_THEMES_ZH[planet],
                "natal_condition": _planet_condition(planet, natal_reference),
                "active": is_active,
            }
        )

    return {
        "system": "ptolemy_seven_ages",
        "system_label": "托勒密七年龄段",
        "current_age_years": (
            None if current_age_years is None else round(current_age_years, 2)
        ),
        "active_planet": active_planet,
        "active_planet_label": (
            None if active_planet is None else planet_label(active_planet)
        ),
        "bands": bands,
    }


# ---------------------------------------------------------------------------
# 3. 三分主星推运 (triplicity rulers of the sect light).
# ---------------------------------------------------------------------------


def build_triplicity_rulers_payload(
    natal_reference: Dict[str, Dict[str, Any]],
    *,
    sect: str,
    lifespan: float = TRIPLICITY_DEFAULT_LIFESPAN,
    division: str = "thirds",
) -> Dict[str, Any]:
    """
    Divide life into stages governed by the three triplicity rulers of the sect
    light's sign. Ruler order follows sect: a day birth runs day → night →
    participating; a night birth runs night → day → participating.

    ``division`` controls how the (nominal) ``lifespan`` is split:

    * ``"thirds"`` — three equal stages (0–L/3, L/3–2L/3, 2L/3–L).
    * ``"halves"`` — main ruler the first half, secondary the second, with the
      participating ruler running across the whole life.

    The age bands use ``lifespan`` purely as a dividing convention (default 75,
    matching the Horosa reference), not as a prediction.
    """
    light_name = "Sun" if sect == "day" else "Moon"
    light_point = natal_reference.get(light_name.lower(), {})
    light_sign = normalize_sign_name(light_point.get("sign", "") or "")
    element = ELEMENT_BY_SIGN.get(light_sign)
    rulers = DOROTHEAN_TRIPLICITY_RULERS.get(element or "", {})

    if sect == "day":
        ordered_roles = ["day", "night", "participating"]
    else:
        ordered_roles = ["night", "day", "participating"]

    role_labels = {"day": "昼主星", "night": "夜主星", "participating": "共主星"}
    if division == "halves":
        spans = [(0.0, lifespan / 2), (lifespan / 2, lifespan), (0.0, lifespan)]
        stage_labels = ["主星·上半生", "次星·下半生", "共主星·贯穿"]
    else:
        division = "thirds"
        third = lifespan / 3
        spans = [(0.0, third), (third, 2 * third), (2 * third, lifespan)]
        stage_labels = ["前期（早年）", "中期（中年）", "后期（晚年）"]

    stages: List[Dict[str, Any]] = []
    for index, role in enumerate(ordered_roles):
        planet = rulers.get(role)
        start_age, end_age = spans[index]
        stages.append(
            {
                "stage": index + 1,
                "stage_label": stage_labels[index],
                "role": role,
                "role_label": role_labels[role],
                "ruler": planet,
                "ruler_label": None if planet is None else planet_label(planet),
                "start_age": round(start_age, 2),
                "end_age": round(end_age, 2),
                "planetary_period_years": (
                    PLANETARY_PERIOD_YEARS.get(planet) if planet else None
                ),
                "natal_condition": (
                    _planet_condition(planet, natal_reference) if planet else None
                ),
            }
        )

    return {
        "system": "dorothean_triplicity",
        "system_label": "多罗修斯三分主星",
        "sect": sect,
        "sect_label": "日盘" if sect == "day" else "夜盘",
        "sect_light": light_name,
        "sect_light_label": planet_label(light_name),
        "sect_light_sign": light_sign,
        "sect_light_sign_label": sign_label(light_sign) if light_sign else None,
        "element": element,
        "element_label": ELEMENT_LABELS_ZH.get(element or ""),
        "lifespan_years": lifespan,
        "division": division,
        "stages": stages,
    }


# ---------------------------------------------------------------------------
# 4. 月相推运 (progressed lunation phase).
# ---------------------------------------------------------------------------


def _phase_for_elongation(elongation: float) -> tuple[str, str]:
    """Return the ``(key, label)`` of the lunar phase containing ``elongation``."""
    band = int(_wrap360(elongation) // 45) % 8
    key, label, _ = LUNAR_PHASES[band]
    return key, label


def build_lunation_phase_payload(
    natal_reference: Dict[str, Dict[str, Any]],
    *,
    max_age_years: float,
) -> Dict[str, Any]:
    """
    Build the progressed lunation-phase timeline. The natal Sun–Moon elongation
    advances at :data:`SECONDARY_SYNODIC_RATE_DEG_PER_YEAR`; each 45° crossing
    starts a new phase. The timeline lists every phase ingress up to
    ``max_age_years``.
    """
    sun_lon = float(natal_reference["sun"]["absolute_degree"])
    moon_lon = float(natal_reference["moon"]["absolute_degree"])
    natal_elongation = _wrap360(moon_lon - sun_lon)
    natal_key, natal_label = _phase_for_elongation(natal_elongation)
    rate = SECONDARY_SYNODIC_RATE_DEG_PER_YEAR
    cycle_years = 360.0 / rate

    timeline: List[Dict[str, Any]] = []
    # Walk forward to each subsequent 45° boundary until we pass max_age_years.
    next_boundary = (int(natal_elongation // 45) + 1) * 45.0
    boundary = next_boundary
    while True:
        age = (boundary - natal_elongation) / rate
        if age > max_age_years:
            break
        key, label, start_degree = LUNAR_PHASES[int(_wrap360(boundary) // 45) % 8]
        timeline.append(
            {
                "phase": key,
                "phase_label": label,
                "ingress_age_years": round(age, 3),
                "elongation_degree": round(_wrap360(boundary), 4),
            }
        )
        boundary += 45.0

    return {
        "system": "progressed_lunation_phase",
        "system_label": "次限月相推运",
        "natal_elongation_degree": round(natal_elongation, 4),
        "natal_phase": natal_key,
        "natal_phase_label": natal_label,
        "progression_rate_deg_per_year": round(rate, 6),
        "synodic_cycle_years": round(cycle_years, 4),
        "max_age_years": max_age_years,
        "phase_ingresses": timeline,
    }


# ---------------------------------------------------------------------------
# 5. 界推运 / 分配法 (distributions through the Egyptian bounds).
# ---------------------------------------------------------------------------


def _bound_segments_from(
    asc_longitude: float, span_degrees: float
) -> List[Dict[str, Any]]:
    """
    Walk ``span_degrees`` of zodiacal arc forward from ``asc_longitude``, yielding
    one entry per Egyptian bound crossed, with the absolute arc at which the
    directed Ascendant enters that bound.
    """
    segments: List[Dict[str, Any]] = []
    cursor = 0.0
    while cursor < span_degrees:
        directed = longitude_to_point_dict("Ascendant", asc_longitude + cursor)
        sign_name = directed["sign"]
        degree_in_sign = directed["degree"]
        bound = resolve_egyptian_bound(sign_name, degree_in_sign)
        # Arc remaining until the directed Ascendant leaves this bound.
        to_boundary = bound["segment_end_degree"] - degree_in_sign
        if to_boundary <= 1e-9:
            to_boundary = 30.0 - degree_in_sign  # safety: step into the next sign
        segments.append(
            {
                "bound": bound,
                "sign": sign_name,
                "enter_arc": cursor,
                "exit_arc": min(cursor + to_boundary, span_degrees),
            }
        )
        cursor += to_boundary
    return segments


def build_distributions_payload(
    natal_reference: Dict[str, Dict[str, Any]],
    *,
    time_key: str,
    max_age_years: float,
) -> Dict[str, Any]:
    """
    Direct the Ascendant through the Egyptian bounds at the chosen ``time_key``
    rate. Each bound the directed Ascendant occupies defines a period whose
    distributor is that bound's lord; natal bodies the directed Ascendant
    conjoins inside a period are recorded as participants (partners).
    """
    rate = DISTRIBUTION_TIME_KEY_RATES.get(time_key, 1.0)
    asc_longitude = float(natal_reference["ascendant"]["absolute_degree"])
    span_degrees = max_age_years * rate
    longitudes = _natal_longitudes(natal_reference)

    periods: List[Dict[str, Any]] = []
    for segment in _bound_segments_from(asc_longitude, span_degrees):
        bound = segment["bound"]
        start_age = segment["enter_arc"] / rate
        end_age = segment["exit_arc"] / rate

        participants: List[Dict[str, Any]] = []
        for point_name, natal_lon in longitudes.items():
            if point_name in ("Ascendant", "Medium_Coeli"):
                continue
            # Arc from the Ascendant to this body, measured forward.
            contact_arc = _wrap360(natal_lon - asc_longitude)
            if segment["enter_arc"] <= contact_arc < segment["exit_arc"]:
                participants.append(
                    {
                        "planet": point_name,
                        "planet_label": planet_label(point_name),
                        "contact_age_years": round(contact_arc / rate, 3),
                    }
                )
        participants.sort(key=lambda item: item["contact_age_years"])

        periods.append(
            {
                "distributor": bound["bound_lord"],
                "distributor_label": bound["bound_lord_label"],
                "sign": segment["sign"],
                "sign_label": sign_label(segment["sign"]),
                "bound_start_degree": bound["segment_start_degree"],
                "bound_end_degree": bound["segment_end_degree"],
                "start_age_years": round(start_age, 3),
                "end_age_years": round(end_age, 3),
                "participants": participants,
            }
        )

    return {
        "system": "distributions_through_bounds",
        "system_label": "界推运（上升历经埃及界限）",
        "direction_model": "zodiacal",
        "direction_model_label": "黄道度数推进（每年 rate° 推进上升黄经）",
        "time_key": time_key,
        "rate_deg_per_year": round(rate, 8),
        "ascendant_absolute_degree": round(asc_longitude, 4),
        "max_age_years": max_age_years,
        "periods": periods,
    }


__all__ = [
    "build_harmonic_payload",
    "build_planetary_ages_payload",
    "build_triplicity_rulers_payload",
    "build_lunation_phase_payload",
    "build_distributions_payload",
    "PTOLEMY_SEVEN_AGES",
    "DOROTHEAN_TRIPLICITY_RULERS",
    "LUNAR_PHASES",
    "SECONDARY_SYNODIC_RATE_DEG_PER_YEAR",
    "DISTRIBUTION_TIME_KEY_RATES",
]
