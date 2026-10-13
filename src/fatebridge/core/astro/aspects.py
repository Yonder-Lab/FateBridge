"""Natal and directional relationship aspects, midpoints and antiscia."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fatebridge.core.astro.geometry import _midpoint, normalize_angle
from fatebridge.core.astro.reference import (
    _TRADITIONAL_PLANET_IDS,
    ASPECTS,
    DEFAULT_PLANET_ORBS,
    HARMONIOUS_ASPECTS,
)


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


def _compatibility_score(
    inner: List[Dict[str, Any]],
    outer: List[Dict[str, Any]],
    aspects: List[Dict[str, Any]],
) -> Dict[str, int]:
    inner_elements = Counter(
        item["element"] for item in inner if item["id"] in _TRADITIONAL_PLANET_IDS
    )
    outer_elements = Counter(
        item["element"] for item in outer if item["id"] in _TRADITIONAL_PLANET_IDS
    )
    inner_modalities = Counter(
        item["modality"] for item in inner if item["id"] in _TRADITIONAL_PLANET_IDS
    )
    outer_modalities = Counter(
        item["modality"] for item in outer if item["id"] in _TRADITIONAL_PLANET_IDS
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
        if source_planet["id"] not in _TRADITIONAL_PLANET_IDS:
            continue

        matches: List[Dict[str, Any]] = []
        for target_planet in target_planets:
            if target_planet["id"] not in _TRADITIONAL_PLANET_IDS:
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
        item for item in target_planets if item["id"] in _TRADITIONAL_PLANET_IDS
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
        if source_planet["id"] not in _TRADITIONAL_PLANET_IDS:
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
        if source_planet["id"] not in _TRADITIONAL_PLANET_IDS:
            continue

        for target_planet in target_planets:
            if target_planet["id"] not in _TRADITIONAL_PLANET_IDS:
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
