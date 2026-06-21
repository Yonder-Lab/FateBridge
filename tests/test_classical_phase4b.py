"""Phase 4b tests: translation / collection of light + nodal bending.

These extend the [古典格局] relational layer with the configurations that need
planetary speed (applying/separating) and the nodal axis — the plumbing Phase 2b
put on the chart. The layer emits **structural facts only** (which planets, what
relation); interpretation is the skills layer's job, so the tests assert shape
and configuration, never signification prose.
"""

from __future__ import annotations

import pytest

from fatebridge.core import astrology
from fatebridge.core.astrology import build_astro_birth_info, build_core_chart_payload
from fatebridge.core.classical_western import (
    NODE_BENDING_ORB,
    _aspect_is_applying,
    build_classical_patterns,
)
from fatebridge.services.astrology import _build_classical_patterns_lines

_NATAL = dict(
    birth_year=2000,
    birth_month=12,
    birth_day=10,
    birth_hour=9,
    birth_minute=55,
    birth_timezone="Asia/Shanghai",
    birth_longitude=120.4667,
    birth_latitude=32.5417,
    name="左右",
    birth_place="海安",
)


# ── applying / separating ─────────────────────────────────────────────────────


def test_applying_when_gap_to_exact_shrinks():
    # Moon at 11° approaching a trine (120°) to Jupiter at 132° → applying.
    assert _aspect_is_applying(11.0, 13.0, 132.0, 0.08, 120.0) is True
    # Moon at 11° just past a conjunction with Saturn at 10° → separating.
    assert _aspect_is_applying(11.0, 13.0, 10.0, 0.03, 0.0) is False


def test_applying_unknown_without_speed():
    assert _aspect_is_applying(10.0, None, 50.0, 1.0, 0.0) is None


# ── translation of light ──────────────────────────────────────────────────────


def test_translation_of_light_fires():
    planets = [
        {"id": "Moon", "sign": "Aries", "longitude": 11.0},
        {"id": "Saturn", "sign": "Aries", "longitude": 10.0},
        {"id": "Jupiter", "sign": "Leo", "longitude": 132.0},
    ]
    aspects = [
        {"planet_a": "Moon", "planet_b": "Saturn", "aspect": "conjunction"},
        {"planet_a": "Moon", "planet_b": "Jupiter", "aspect": "trine"},
    ]
    speeds = {"Moon": 13.0, "Saturn": 0.03, "Jupiter": 0.08}
    result = build_classical_patterns(planets, aspects, "day", speeds=speeds)
    assert result["translation_of_light"] == [
        {"translator": "Moon", "from": "Saturn", "to": "Jupiter"}
    ]


def test_translation_requires_the_endpoints_to_be_in_aversion():
    # If Saturn and Jupiter DO aspect each other, no light needs carrying.
    planets = [
        {"id": "Moon", "sign": "Aries", "longitude": 11.0},
        {"id": "Saturn", "sign": "Aries", "longitude": 10.0},
        {"id": "Jupiter", "sign": "Leo", "longitude": 132.0},
    ]
    aspects = [
        {"planet_a": "Moon", "planet_b": "Saturn", "aspect": "conjunction"},
        {"planet_a": "Moon", "planet_b": "Jupiter", "aspect": "trine"},
        {"planet_a": "Saturn", "planet_b": "Jupiter", "aspect": "trine"},
    ]
    speeds = {"Moon": 13.0, "Saturn": 0.03, "Jupiter": 0.08}
    result = build_classical_patterns(planets, aspects, "day", speeds=speeds)
    assert result["translation_of_light"] == []


# ── collection of light ───────────────────────────────────────────────────────


def test_collection_of_light_fires():
    planets = [
        {"id": "Saturn", "sign": "Aries", "longitude": 10.0},
        {"id": "Moon", "sign": "Aries", "longitude": 8.0},
        {"id": "Mercury", "sign": "Leo", "longitude": 129.0},
    ]
    aspects = [
        {"planet_a": "Saturn", "planet_b": "Moon", "aspect": "conjunction"},
        {"planet_a": "Saturn", "planet_b": "Mercury", "aspect": "trine"},
    ]
    speeds = {"Saturn": 0.03, "Moon": 13.0, "Mercury": 1.2}
    result = build_classical_patterns(planets, aspects, "day", speeds=speeds)
    assert result["collection_of_light"] == [
        {"collector": "Saturn", "from": ["Mercury", "Moon"]}
    ]


# ── nodal bending ─────────────────────────────────────────────────────────────


def test_nodal_bending_north_and_south_within_orb():
    node = 100.0
    planets = [
        {"id": "Mars", "sign": "Libra", "longitude": (node + 90.0) + 1.0},  # north
        {"id": "Venus", "sign": "Aries", "longitude": (node - 90.0) - 0.5},  # south
        {"id": "Jupiter", "sign": "Leo", "longitude": node + 45.0},  # clear of bending
    ]
    result = build_classical_patterns(planets, [], "day", node_longitude=node)
    bending = {b["planet"]: b["bending"] for b in result["nodal_bending"]}
    assert bending == {"Mars": "north", "Venus": "south"}


def test_nodal_bending_excluded_beyond_orb():
    node = 100.0
    planets = [
        {"id": "Mars", "sign": "Libra", "longitude": node + 90.0 + NODE_BENDING_ORB + 1}
    ]
    result = build_classical_patterns(planets, [], "day", node_longitude=node)
    assert result["nodal_bending"] == []


# ── honest degradation (offline engine) ───────────────────────────────────────


def test_light_patterns_empty_without_speeds():
    planets = [
        {"id": "Moon", "sign": "Aries", "longitude": 11.0},
        {"id": "Saturn", "sign": "Aries", "longitude": 10.0},
        {"id": "Jupiter", "sign": "Leo", "longitude": 132.0},
    ]
    aspects = [
        {"planet_a": "Moon", "planet_b": "Saturn", "aspect": "conjunction"},
        {"planet_a": "Moon", "planet_b": "Jupiter", "aspect": "trine"},
    ]
    # No speeds passed → applying/separating undefined → no translation/collection.
    result = build_classical_patterns(planets, aspects, "day")
    assert result["translation_of_light"] == []
    assert result["collection_of_light"] == []


def test_nodal_bending_empty_without_node():
    planets = [{"id": "Mars", "sign": "Libra", "longitude": 190.0}]
    result = build_classical_patterns(planets, [], "day")
    assert result["nodal_bending"] == []


# ── integration + rendering ───────────────────────────────────────────────────


@pytest.mark.skipif(astrology.swe is None, reason="swisseph 不可用")
def test_chart_exposes_phase4b_keys_as_lists():
    info = build_astro_birth_info(use_true_solar_time=True, **_NATAL)
    patterns = build_core_chart_payload(info, "hellen_chart")["classical_patterns"]
    for key in ("translation_of_light", "collection_of_light", "nodal_bending"):
        assert isinstance(patterns[key], list)


def test_snapshot_renders_phase4b_configurations():
    payload = {
        "classical_patterns": {
            "sect_benefic": "Jupiter",
            "sect_malefic": "Saturn",
            "overcoming": [],
            "besiegement": {},
            "bonification": {},
            "translation_of_light": [
                {"translator": "Moon", "from": "Saturn", "to": "Jupiter"}
            ],
            "collection_of_light": [{"collector": "Saturn", "from": ["Mars", "Venus"]}],
            "nodal_bending": [{"planet": "Mars", "bending": "north", "orb": 1.0}],
        }
    }
    text = _build_classical_patterns_lines(payload)
    assert "光的传递：月亮 自 土星 递光至 木星" in text
    assert "光的聚集：土星 聚 火星、金星 之光" in text
    assert "交点弯曲：火星北弯" in text
