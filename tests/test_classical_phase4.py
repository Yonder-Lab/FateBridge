"""Phase 4 tests: [古典格局] relational patterns.

Whole-sign relations (aspect/aversion/overcoming) are checked by classical
ground truths; besiegement and bonification by hand-built mini-charts.
Translation/collection of light are out of scope (need planetary speed).
"""

from __future__ import annotations

from fatebridge.core.classical_western import (
    build_classical_patterns,
    overcomes,
    whole_sign_aspect,
)
from fatebridge.services.astrology import calculate_core_chart_analysis


def test_whole_sign_aspect_and_aversion():
    assert whole_sign_aspect("Aries", "Aries") == "conjunction"
    assert whole_sign_aspect("Aries", "Gemini") == "sextile"
    assert whole_sign_aspect("Aries", "Cancer") == "square"
    assert whole_sign_aspect("Aries", "Leo") == "trine"
    assert whole_sign_aspect("Aries", "Libra") == "opposition"
    # Aversion: 2nd/12th (Taurus/Pisces) and 6th/8th (Virgo/Scorpio) from Aries.
    assert whole_sign_aspect("Aries", "Taurus") is None
    assert whole_sign_aspect("Aries", "Scorpio") is None


def test_overcoming_is_tenth_sign_superior_square():
    # Capricorn is the 10th sign from Aries → Capricorn overcomes Aries.
    assert overcomes("Capricorn", "Aries") is True
    assert overcomes("Aries", "Capricorn") is False  # directional


def _pos(pid, sign, lon):
    return {"id": pid, "sign": sign, "longitude": lon}


def test_besiegement_by_malefics_and_enclosure_by_benefics():
    # Mercury at 10° flanked by Mars (5°) and Saturn (15°) → besieged by malefics.
    positions = [
        _pos("Mars", "Aries", 5.0),
        _pos("Mercury", "Aries", 10.0),
        _pos("Saturn", "Aries", 15.0),
        _pos("Sun", "Aries", 25.0),
        _pos("Moon", "Aries", 28.0),
        _pos("Venus", "Aries", 1.0),
        _pos("Jupiter", "Aries", 2.0),
    ]
    patterns = build_classical_patterns(positions, [], "day")
    assert patterns["besiegement"].get("Mercury") == "besieged_by_malefics"


def test_besiegement_requires_malefics_within_orb():
    # Mercury's nearest neighbours are both malefic but ~50° away on each side.
    # Enclosure by body requires the flanking bodies within ~15°, so this is
    # NOT besiegement.
    positions = [
        _pos("Venus", "Aries", 1.0),
        _pos("Jupiter", "Aries", 2.0),
        _pos("Mars", "Cancer", 100.0),
        _pos("Mercury", "Virgo", 150.0),
        _pos("Saturn", "Libra", 200.0),
        _pos("Sun", "Capricorn", 250.0),
        _pos("Moon", "Capricorn", 280.0),
    ]
    patterns = build_classical_patterns(positions, [], "day")
    assert patterns["besiegement"].get("Mercury") is None


def test_bonification_and_maltreatment_from_aspects():
    positions = [
        _pos(p, "Aries", float(i))
        for i, p in enumerate(
            ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        )
    ]
    aspects = [
        {"planet_a": "Jupiter", "planet_b": "Moon", "aspect": "trine"},
        {"planet_a": "Saturn", "planet_b": "Moon", "aspect": "square"},
    ]
    patterns = build_classical_patterns(positions, aspects, "day")
    assert patterns["bonification"]["Moon"]["bonified_by"] == ["Jupiter"]
    assert patterns["bonification"]["Moon"]["maltreated_by"] == ["Saturn"]


def test_sect_benefic_malefic_by_sect():
    day = build_classical_patterns([], [], "day")
    night = build_classical_patterns([], [], "night")
    assert (day["sect_benefic"], day["sect_malefic"]) == ("Jupiter", "Saturn")
    assert (night["sect_benefic"], night["sect_malefic"]) == ("Venus", "Mars")


def test_chart_exposes_classical_patterns():
    result = calculate_core_chart_analysis(
        name="t",
        birth_year=2000,
        birth_month=12,
        birth_day=10,
        birth_hour=9,
        birth_minute=55,
        birth_timezone="Asia/Shanghai",
        birth_longitude=120.45,
        birth_latitude=32.54,
        chart_variant="chart",
    )
    cp = result["classical_patterns"]
    assert cp["sect_benefic"] in {"Jupiter", "Venus"}
    assert "aversions" in cp and "overcoming" in cp and "besiegement" in cp
    assert "[古典格局]" in result["snapshot_text"]
