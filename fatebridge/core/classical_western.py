"""Western classical-astrology primitives (Hellenistic / medieval).

Phase 1 of the 西占古典深度段 project: per-planet essential + accidental
condition, shared by ``astro_chart`` (the new ``classical`` layer) and the
horary engine. Dignity tables are reused from :mod:`fatebridge.core.astrology`
and :mod:`fatebridge.core.predictive` (single source); only the genuinely
missing pieces — Chaldean faces, Dorothean triplicity rulers, Lilly dignity
scores, combustion / orientality / sect / joy — are added here.

Reference data ported verbatim from horosa `data/dignities.js` (Egyptian terms,
Dorothean triplicity, Chaldean faces, Lilly scores); derivation logic follows
the standard classical definitions those tables cite (Ptolemy / Lilly /
Dorotheus). There is no closed byte-oracle, so correctness is pinned by
table-parity + classical invariants (see tests).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fatebridge.core.astrology import (
    DOMICILE_RULERS,
    ELEMENT_BY_SIGN,
    EXALTATION_SIGNS,
    RULER_BY_SIGN,
    _opposite_sign,
)
from fatebridge.core.predictive import EGYPTIAN_BOUNDS_BY_SIGN

# Chaldean decan faces — each sign's three 10° faces, Chaldean order from Mars at
# 0° Aries. Ported verbatim from horosa data/dignities.js FACES (lowercased there).
CHALDEAN_FACES: Dict[str, List[str]] = {
    "Aries": ["Mars", "Sun", "Venus"],
    "Taurus": ["Mercury", "Moon", "Saturn"],
    "Gemini": ["Jupiter", "Mars", "Sun"],
    "Cancer": ["Venus", "Mercury", "Moon"],
    "Leo": ["Saturn", "Jupiter", "Mars"],
    "Virgo": ["Sun", "Venus", "Mercury"],
    "Libra": ["Moon", "Saturn", "Jupiter"],
    "Scorpio": ["Mars", "Sun", "Venus"],
    "Sagittarius": ["Mercury", "Moon", "Saturn"],
    "Capricorn": ["Jupiter", "Mars", "Sun"],
    "Aquarius": ["Venus", "Mercury", "Moon"],
    "Pisces": ["Saturn", "Jupiter", "Mars"],
}

# Dorothean triplicity rulers by element → day / night / participating ruler.
DOROTHEAN_TRIPLICITY: Dict[str, Dict[str, str]] = {
    "Fire": {"day": "Sun", "night": "Jupiter", "participating": "Saturn"},
    "Earth": {"day": "Venus", "night": "Moon", "participating": "Mars"},
    "Air": {"day": "Saturn", "night": "Mercury", "participating": "Jupiter"},
    "Water": {"day": "Venus", "night": "Mars", "participating": "Moon"},
}

# Lilly's essential-dignity scores (domicile +5 … face +1; detriment −5 / fall −4).
DIGNITY_SCORE: Dict[str, int] = {
    "rulership": 5,
    "exaltation": 4,
    "triplicity": 3,
    "bound": 2,
    "face": 1,
    "detriment": -5,
    "fall": -4,
}

DIGNITY_LABELS_ZH: Dict[str, str] = {
    "rulership": "庙",
    "exaltation": "旺",
    "triplicity": "三分",
    "bound": "界",
    "face": "面",
    "detriment": "陷",
    "fall": "弱",
    "peregrine": "平",
}

# Planetary joys by house (Hellenistic): Mercury 1, Moon 3, Venus 5, Mars 6,
# Sun 9, Jupiter 11, Saturn 12.
PLANETARY_JOYS: Dict[str, int] = {
    "Mercury": 1,
    "Moon": 3,
    "Venus": 5,
    "Mars": 6,
    "Sun": 9,
    "Jupiter": 11,
    "Saturn": 12,
}

# Natural sect of the seven traditional planets (Mercury is sect-neutral —
# resolved by orientality at call sites).
DIURNAL_PLANETS = frozenset({"Sun", "Jupiter", "Saturn"})
NOCTURNAL_PLANETS = frozenset({"Moon", "Venus", "Mars"})

TRADITIONAL_PLANETS = frozenset(
    {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
)

# Combustion thresholds (degrees) — cazimi 17′, combust 8.5°, under-beams 17°.
_COMBUST_CAZIMI = 17.0 / 60.0
_COMBUST_LIMIT = 8.5
_UNDER_BEAMS_LIMIT = 17.0
# Solar obliquity bound — a body beyond this declination is "out of bounds".
OUT_OF_BOUNDS_LIMIT = 23.4367


def _angular_distance(first: float, second: float) -> float:
    """Unsigned 0–180° separation."""
    diff = abs((first - second) % 360.0)
    return min(diff, 360.0 - diff)


def _signed_delta(reference: float, target: float) -> float:
    """``target − reference`` folded into (−180, 180]."""
    return (target - reference + 540.0) % 360.0 - 180.0


def bound_lord(sign: str, degree_in_sign: float) -> Optional[str]:
    """Egyptian-term (bound) lord at this sign + degree."""
    for lord, start, end in EGYPTIAN_BOUNDS_BY_SIGN.get(sign, []):
        if start <= degree_in_sign < end:
            return lord
    return None


def face_lord(sign: str, degree_in_sign: float) -> Optional[str]:
    """Chaldean face (decan) lord at this sign + degree."""
    faces = CHALDEAN_FACES.get(sign)
    if not faces:
        return None
    return faces[min(2, int(degree_in_sign // 10))]


def triplicity_members(sign: str) -> List[str]:
    """All three Dorothean triplicity rulers of the sign's element (unordered).

    Used for reception / horary's membership-style dignity flag.
    """
    rulers = DOROTHEAN_TRIPLICITY.get(ELEMENT_BY_SIGN.get(sign, ""))
    if not rulers:
        return []
    return [rulers["day"], rulers["night"], rulers["participating"]]


def triplicity_ruler(sign: str, is_day: bool) -> Optional[str]:
    """The sect triplicity ruler (Lilly scores the in-sect ruler +3)."""
    rulers = DOROTHEAN_TRIPLICITY.get(ELEMENT_BY_SIGN.get(sign, ""))
    if not rulers:
        return None
    return rulers["day"] if is_day else rulers["night"]


def _detriment_signs(planet: str) -> set:
    return {_opposite_sign(s) for s in DOMICILE_RULERS.get(planet, ())}


def essential_dignities(
    planet: str, sign: str, degree_in_sign: float, is_day: bool
) -> Optional[Dict[str, Any]]:
    """Full classical essential-dignity picture for a traditional planet.

    Returns the dignities held (rulership/exaltation/triplicity/bound/face) and
    debilities (detriment/fall), a Lilly score, and the bound/triplicity/face
    lords of the placement. ``None`` for non-traditional bodies (outers/nodes).
    """
    if planet not in TRADITIONAL_PLANETS:
        return None

    held: List[str] = []
    if sign in DOMICILE_RULERS.get(planet, ()):
        held.append("rulership")
    if EXALTATION_SIGNS.get(planet) == sign:
        held.append("exaltation")
    if triplicity_ruler(sign, is_day) == planet:
        held.append("triplicity")
    if bound_lord(sign, degree_in_sign) == planet:
        held.append("bound")
    if face_lord(sign, degree_in_sign) == planet:
        held.append("face")

    debilities: List[str] = []
    if sign in _detriment_signs(planet):
        debilities.append("detriment")
    if sign == _opposite_sign(EXALTATION_SIGNS.get(planet, "")):
        debilities.append("fall")

    score = sum(DIGNITY_SCORE[d] for d in held) + sum(
        DIGNITY_SCORE[d] for d in debilities
    )
    peregrine = not held and not debilities

    return {
        "dignities": held,
        "debilities": debilities,
        "peregrine": peregrine,
        "score": score,
        "bound_lord": bound_lord(sign, degree_in_sign),
        "triplicity_ruler": triplicity_ruler(sign, is_day),
        "face_lord": face_lord(sign, degree_in_sign),
        "labels_zh": [DIGNITY_LABELS_ZH[d] for d in held]
        + [DIGNITY_LABELS_ZH[d] for d in debilities]
        + (["平"] if peregrine else []),
    }


def is_above_horizon(house: Optional[int]) -> Optional[bool]:
    """Houses 7–12 are above the horizon (Desc → MC → Asc)."""
    if not house:
        return None
    return house >= 7


def sect_of_chart(sun_house: Optional[int]) -> Optional[str]:
    """Day chart when the Sun is above the horizon, else night."""
    above = is_above_horizon(sun_house)
    if above is None:
        return None
    return "day" if above else "night"


def angularity(house: Optional[int]) -> Optional[str]:
    """Angular (1/4/7/10) · succedent (2/5/8/11) · cadent (3/6/9/12)."""
    if not house:
        return None
    if house in (1, 4, 7, 10):
        return "angular"
    if house in (2, 5, 8, 11):
        return "succedent"
    return "cadent"


def combustion_state(planet_lon: float, sun_lon: Optional[float]) -> Optional[str]:
    """cazimi (≤17′) · combust (<8.5°) · under_beams (<17°), else None."""
    if sun_lon is None:
        return None
    distance = _angular_distance(planet_lon, sun_lon)
    if distance <= _COMBUST_CAZIMI:
        return "cazimi"
    if distance < _COMBUST_LIMIT:
        return "combust"
    if distance < _UNDER_BEAMS_LIMIT:
        return "under_beams"
    return None


def orientality(planet_lon: float, sun_lon: Optional[float]) -> Optional[str]:
    """oriental (rises before the Sun) / occidental (sets after)."""
    if sun_lon is None:
        return None
    delta = _signed_delta(sun_lon, planet_lon)  # planet − sun ∈ (−180, 180]
    if abs(delta) < 1e-4:
        return None
    return "oriental" if delta < 0 else "occidental"


def planet_sect(planet: str, orientality_value: Optional[str]) -> Optional[str]:
    """Natural sect of a planet; Mercury follows its orientality."""
    if planet in DIURNAL_PLANETS:
        return "day"
    if planet in NOCTURNAL_PLANETS:
        return "night"
    if planet == "Mercury":
        if orientality_value == "oriental":
            return "day"
        if orientality_value == "occidental":
            return "night"
    return None


def sect_placement(
    planet: str, chart_sect: Optional[str], orientality_value: Optional[str]
) -> Optional[str]:
    """Whether the planet is of the chart's sect or contrary to it."""
    own = planet_sect(planet, orientality_value)
    if own is None or chart_sect is None:
        return None
    return "of_sect" if own == chart_sect else "contrary_to_sect"


def in_halb(
    planet: str,
    chart_sect: Optional[str],
    above_horizon: Optional[bool],
    orientality_value: Optional[str],
) -> Optional[bool]:
    """Rejoicing by halb: an of-sect planet on its preferred side of the horizon
    (diurnal above by day / nocturnal below by day, and vice-versa)."""
    own = planet_sect(planet, orientality_value)
    if own is None or chart_sect is None or above_horizon is None:
        return None
    if own != chart_sect:
        return False
    if chart_sect == "day":
        return above_horizon if own == "day" else not above_horizon
    return not above_horizon if own == "day" else above_horizon


def planetary_joy(planet: str, house: Optional[int]) -> bool:
    return bool(house) and PLANETARY_JOYS.get(planet) == house


# ── Phase 2: almuten (essential-dignity rulership of a degree) + dispositors ──

# Reverse of EXALTATION_SIGNS: sign → the planet exalted there (7 of 12 signs).
EXALT_RULER_BY_SIGN: Dict[str, str] = {
    sign: planet for planet, sign in EXALTATION_SIGNS.items()
}

# Five essential-dignity weights used to score an almuten (Lilly / Ibn Ezra).
_ALMUTEN_WEIGHTS = {
    "domicile": DIGNITY_SCORE["rulership"],
    "exaltation": DIGNITY_SCORE["exaltation"],
    "triplicity": DIGNITY_SCORE["triplicity"],
    "term": DIGNITY_SCORE["bound"],
    "face": DIGNITY_SCORE["face"],
}


def dignity_lords_at(
    sign: str, degree_in_sign: float, is_day: bool
) -> Dict[str, Optional[str]]:
    """The five essential-dignity lords of a point (domicile/exalt/trip/term/face)."""
    return {
        "domicile": RULER_BY_SIGN.get(sign),
        "exaltation": EXALT_RULER_BY_SIGN.get(sign),
        "triplicity": triplicity_ruler(sign, is_day),
        "term": bound_lord(sign, degree_in_sign),
        "face": face_lord(sign, degree_in_sign),
    }


def almuten_of(sign: str, degree_in_sign: float, is_day: bool) -> Dict[str, Any]:
    """Almuten of a degree: the planet with the most weighted essential dignity.

    Sums the 5 dignity weights (5/4/3/2/1) each planet earns over the point;
    the winner is the strongest ruler. Ties resolve to the heavier dignity then
    the traditional Chaldean order (slowest first) for determinism.
    """
    lords = dignity_lords_at(sign, degree_in_sign, is_day)
    totals: Dict[str, int] = {}
    for dignity, weight in _ALMUTEN_WEIGHTS.items():
        lord = lords[dignity]
        if lord:
            totals[lord] = totals.get(lord, 0) + weight
    winner: Optional[str] = None
    if totals:
        # Deterministic tie-break: higher score, then Chaldean (slowest-first) order.
        order = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
        winner = max(
            totals, key=lambda p: (totals[p], -order.index(p) if p in order else 0)
        )
    return {"winner": winner, "totals": totals, "lords": lords}


def domicile_ruler(sign: str) -> Optional[str]:
    """Traditional domicile ruler of a sign (for dispositor chains)."""
    return RULER_BY_SIGN.get(sign)


def dispositor_chain(planet: str, placements: Dict[str, str]) -> Dict[str, Any]:
    """Follow the domicile-dispositor chain from ``planet``.

    ``placements`` maps planet → the sign it occupies. Each planet is disposited
    by the ruler of its sign; the chain walks rulers until it reaches a planet in
    its own domicile (final dispositor) or revisits a planet (mutual-reception /
    longer loop). Returns the visited chain + terminal info.
    """
    chain: List[str] = [planet]
    seen = {planet}
    current = planet
    while True:
        sign = placements.get(current)
        ruler = domicile_ruler(sign) if sign else None
        if ruler is None:
            return {"chain": chain, "terminal": None, "terminal_type": "unknown"}
        if ruler == current:
            return {"chain": chain, "terminal": current, "terminal_type": "domicile"}
        if ruler in seen:
            # Loop: a planet rules its own dispositor (mutual reception if length 2).
            kind = "mutual_reception" if ruler == planet and len(chain) == 2 else "loop"
            return {"chain": chain + [ruler], "terminal": ruler, "terminal_type": kind}
        chain.append(ruler)
        seen.add(ruler)
        current = ruler


def build_dispositor_layer(placements: Dict[str, str]) -> Dict[str, Any]:
    """Per-planet dispositor chains + the chart's final dispositor(s)."""
    chains = {planet: dispositor_chain(planet, placements) for planet in placements}
    finals = sorted(
        {
            info["terminal"]
            for info in chains.values()
            if info["terminal_type"] == "domicile" and info["terminal"]
        }
    )
    return {"chains": chains, "final_dispositors": finals}


def build_topic_almutens(
    houses: Dict[int, Dict[str, Any]], is_day: bool
) -> Dict[str, Dict[str, Any]]:
    """Almuten of each house cusp — the topic ruler of that house's matters.

    Keyed by the house number as a **string** so the structure round-trips
    identically through JSON (REST) and in-process (MCP) transports — JSON object
    keys are always strings, and the two surfaces must stay byte-identical.
    """
    topic: Dict[str, Dict[str, Any]] = {}
    for house_number, cusp in houses.items():
        sign = cusp.get("sign")
        degree = cusp.get("degree_in_sign")
        if not sign or degree is None:
            continue
        result = almuten_of(sign, degree, is_day)
        topic[str(house_number)] = {"sign": sign, "winner": result["winner"]}
    return topic


def build_planet_classical(
    *,
    planet: str,
    sign: str,
    degree_in_sign: float,
    longitude: float,
    house: Optional[int],
    sun_longitude: Optional[float],
    chart_sect: Optional[str],
) -> Dict[str, Any]:
    """The per-planet ``classical`` entry surfaced on the chart payload."""
    above = is_above_horizon(house)
    orient = None if planet == "Sun" else orientality(longitude, sun_longitude)
    return {
        "essential": essential_dignities(
            planet, sign, degree_in_sign, chart_sect == "day"
        ),
        "angularity": angularity(house),
        "above_horizon": above,
        "combustion": (
            None if planet == "Sun" else combustion_state(longitude, sun_longitude)
        ),
        "orientality": orient,
        "sect_placement": sect_placement(planet, chart_sect, orient),
        "in_halb": in_halb(planet, chart_sect, above, orient),
        "joy": planetary_joy(planet, house),
    }
