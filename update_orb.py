import re
import sys

filepath = 'fatebridge/core/astrology.py'

with open(filepath, 'r') as f:
    content = f.read()

# Add DEFAULT_PLANET_ORBS and _get_dynamic_orb
code_to_add = """
DEFAULT_PLANET_ORBS = {
    "Sun": 10.0, "Moon": 10.0,
    "Mercury": 7.0, "Venus": 7.0, "Mars": 7.5,
    "Jupiter": 9.0, "Saturn": 9.0,
    "Uranus": 5.0, "Neptune": 5.0, "Pluto": 5.0,
}

def _get_dynamic_orb(planet_a_id: str, planet_b_id: str, aspect_name: str, default_orb: float = 6.0) -> float:
    orb_a = DEFAULT_PLANET_ORBS.get(planet_a_id, default_orb)
    orb_b = DEFAULT_PLANET_ORBS.get(planet_b_id, default_orb)
    base_orb = (orb_a + orb_b) / 2.0
    
    if aspect_name in {"sextile", "square"}:
        return base_orb * 0.8
    return base_orb

"""

if "DEFAULT_PLANET_ORBS =" not in content:
    # Insert before _build_aspects
    content = content.replace("def _build_aspects(", code_to_add + "def _build_aspects(")


build_aspects_old = """def _build_aspects(planets: Iterable[Dict[str, Any]], orb: float = 6.0) -> List[Dict[str, Any]]:
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
            aspects.append("""

build_aspects_new = """def _build_aspects(planets: Iterable[Dict[str, Any]], orb: float = 6.0) -> List[Dict[str, Any]]:
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
                dynamic_max_orb = _get_dynamic_orb(first["id"], second["id"], aspect_name, default_orb=orb)
                if current_orb <= dynamic_max_orb and (matched is None or current_orb < matched[1]):
                    matched = (aspect_name, current_orb)
            if matched is None:
                continue
            aspects.append("""

content = content.replace(build_aspects_old, build_aspects_new)

match_cross_aspect_old = """def _match_cross_aspect(longitude_a: float, longitude_b: float, orb: float = 4.0) -> Optional[Dict[str, Any]]:
    difference = abs(longitude_a - longitude_b)
    if difference > 180:
        difference = 360 - difference

    matched: Optional[Tuple[str, float]] = None
    for aspect_name, exact_angle in ASPECTS:
        current_orb = abs(difference - exact_angle)
        if current_orb <= orb and (matched is None or current_orb < matched[1]):
            matched = (aspect_name, current_orb)"""

match_cross_aspect_new = """def _match_cross_aspect(
    longitude_a: float,
    longitude_b: float,
    orb: float = 4.0,
    planet_a_id: Optional[str] = None,
    planet_b_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    difference = abs(longitude_a - longitude_b)
    if difference > 180:
        difference = 360 - difference

    matched: Optional[Tuple[str, float]] = None
    for aspect_name, exact_angle in ASPECTS:
        current_orb = abs(difference - exact_angle)
        dynamic_max_orb = orb
        if planet_a_id and planet_b_id:
            dynamic_max_orb = _get_dynamic_orb(planet_a_id, planet_b_id, aspect_name, default_orb=orb)
            
        if current_orb <= dynamic_max_orb and (matched is None or current_orb < matched[1]):
            matched = (aspect_name, current_orb)"""

content = content.replace(match_cross_aspect_old, match_cross_aspect_new)

directional_aspects_old = """            matched = _match_cross_aspect(
                source_planet["longitude"], target_planet["longitude"], orb=orb
            )"""

directional_aspects_new = """            matched = _match_cross_aspect(
                source_planet["longitude"], 
                target_planet["longitude"], 
                orb=orb,
                planet_a_id=source_planet["id"],
                planet_b_id=target_planet["id"]
            )"""

content = content.replace(directional_aspects_old, directional_aspects_new)

with open(filepath, 'w') as f:
    f.write(content)

print("Updates applied to astrology.py")
