"""Nested contracts for classical, specialized and relationship charts.

Shared value contracts describe the canonical response fields. Dynamic
planet and midpoint keys remain open; interpretation prose remains extensible.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from fatebridge.core.output_base import PartialOutput


class Dignity(PartialOutput):
    dignity: Optional[str] = None
    status_zh: Optional[str] = None


class ChartPlanet(PartialOutput):
    id: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    degree_in_sign: Optional[float] = None
    sign: Optional[str] = None
    sign_zh: Optional[str] = None
    house: Optional[int] = None
    element: Optional[str] = None
    modality: Optional[str] = None
    dignity: Optional[Dignity] = None
    su28: Optional[str] = None
    nakshatra: Optional[str] = None


class ChartAngle(PartialOutput):
    longitude: Optional[float] = None
    sign: Optional[str] = None
    sign_zh: Optional[str] = None


class ChartHouse(PartialOutput):
    cusp_longitude: Optional[float] = None
    house: Optional[int] = None
    sign: Optional[str] = None
    sign_zh: Optional[str] = None


class ChartAspect(PartialOutput):
    planet_a: Optional[str] = None
    planet_b: Optional[str] = None
    aspect: Optional[str] = None
    orb: Optional[float] = None


class FixedStar(PartialOutput):
    cn: Optional[str] = None
    nature: Optional[List[str]] = None
    orb: Optional[float] = None
    point: Optional[str] = None
    star: Optional[str] = None
    star_longitude: Optional[float] = None


class PlanetaryHours(PartialOutput):
    day_ruler: Optional[str] = None
    hour_number: Optional[int] = None
    hour_ruler: Optional[str] = None
    is_day: Optional[bool] = None


class ChartProfile(PartialOutput):
    ayanamsha: Optional[float] = None
    chart_type: Optional[str] = None
    engine_backend: Optional[str] = None
    engine_precision: Optional[str] = None
    ephemeris_model: Optional[str] = None
    house_system: Optional[str] = None
    house_system_code: Optional[int] = None
    house_system_label_zh: Optional[str] = None
    house_system_source: Optional[str] = None
    tradition: Optional[bool] = None
    zodiac: Optional[str] = None
    zodiac_label_zh: Optional[str] = None
    zodiacal: Optional[int] = None
    analysis_focus: Optional[str] = None


class ClassicalLot(PartialOutput):
    almuten: Optional[str] = None
    cn: Optional[str] = None
    degree_in_sign: Optional[float] = None
    dispositor: Optional[str] = None
    longitude: Optional[float] = None
    sign: Optional[str] = None


class EssentialDignities(PartialOutput):
    bound_lord: Optional[str] = None
    debilities: Optional[List[str]] = None
    dignities: Optional[List[str]] = None
    face_lord: Optional[str] = None
    labels_zh: Optional[List[str]] = None
    peregrine: Optional[bool] = None
    score: Optional[int] = None
    triplicity_ruler: Optional[str] = None


class Melothesia(PartialOutput):
    body_parts: Optional[List[str]] = None
    position: Optional[str] = None


class ClassicalPlanet(PartialOutput):
    above_horizon: Optional[bool] = None
    angularity: Optional[str] = None
    combustion: Optional[str] = None
    dodekatemorion: Optional[str] = None
    essential: Optional[EssentialDignities] = None
    in_halb: Optional[bool] = None
    joy: Optional[bool] = None
    melothesia: Optional[Melothesia] = None
    ninth_part: Optional[str] = None
    orientality: Optional[str] = None
    out_of_bounds: Optional[bool] = None
    retrograde: Optional[bool] = None
    sect_placement: Optional[str] = None


class AlmutenPoint(PartialOutput):
    degree_in_sign: Optional[float] = None
    sign: Optional[str] = None
    totals: Optional[Dict[str, int]] = None
    winner: Optional[str] = None


class AlmutenFiguris(PartialOutput):
    points: Optional[Dict[str, AlmutenPoint]] = None
    totals: Optional[Dict[str, int]] = None
    winner: Optional[str] = None


class DispositorChain(PartialOutput):
    chain: Optional[List[str]] = None
    terminal: Optional[str] = None
    terminal_type: Optional[str] = None


class Dispositors(PartialOutput):
    chains: Optional[Dict[str, DispositorChain]] = None
    final_dispositors: Optional[List[str]] = None
    mutual_receptions: Optional[List[List[str]]] = None


class Syzygy(PartialOutput):
    degree_in_sign: Optional[float] = None
    julian_day: Optional[float] = None
    longitude: Optional[float] = None
    sign: Optional[str] = None
    type: Optional[str] = None


class Temperament(PartialOutput):
    cn: Optional[str] = None
    humor: Optional[str] = None
    hygral: Optional[str] = None
    tally: Optional[Dict[str, int]] = None
    thermal: Optional[str] = None


class TopicAlmuten(PartialOutput):
    sign: Optional[str] = None
    winner: Optional[str] = None


class Classical(PartialOutput):
    almuten_figuris: Optional[AlmutenFiguris] = None
    dispositors: Optional[Dispositors] = None
    lots: Optional[Dict[str, ClassicalLot]] = None
    planets: Optional[Dict[str, ClassicalPlanet]] = None
    sect: Optional[str] = None
    syzygy: Optional[Syzygy] = None
    temperament: Optional[Temperament] = None
    topic_almutens: Optional[Dict[str, TopicAlmuten]] = None


class Bonification(PartialOutput):
    bonified_by: Optional[List[str]] = None
    maltreated_by: Optional[List[str]] = None


class Overcoming(PartialOutput):
    overcome: Optional[str] = None
    overcomer: Optional[str] = None


class Translation(PartialOutput):
    from_: Optional[str] = Field(default=None, alias="from")
    translator: Optional[str] = None
    to: Optional[str] = None


class Collection(PartialOutput):
    from_: Optional[List[str]] = Field(default=None, alias="from")
    collector: Optional[str] = None


class NodalBending(PartialOutput):
    planet: Optional[str] = None
    bending: Optional[str] = None
    orb: Optional[float] = None


class ClassicalPatterns(PartialOutput):
    aversions: Optional[List[List[str]]] = None
    besiegement: Optional[Dict[str, str]] = None
    bonification: Optional[Dict[str, Bonification]] = None
    collection_of_light: Optional[List[Collection]] = None
    nodal_bending: Optional[List[NodalBending]] = None
    overcoming: Optional[List[Overcoming]] = None
    sect_benefic: Optional[str] = None
    sect_malefic: Optional[str] = None
    translation_of_light: Optional[List[Translation]] = None


class Hellenistic(PartialOutput):
    angular_planets: Optional[List[str]] = None
    ascendant_ruler: Optional[str] = None
    lot_of_fortune: Optional[ChartPlanet] = None
    sect: Optional[str] = None


class PlanetMansion(PartialOutput):
    id: Optional[str] = None
    su28: Optional[str] = None


class MoiraPattern(PartialOutput):
    detail: Optional[str] = None
    dsl: Optional[str] = None
    level: Optional[str] = None
    name: Optional[str] = None
    score: Optional[str] = None
    source: Optional[str] = None


class Guolao(PartialOutput):
    god_sign_index: Optional[Dict[str, int]] = None
    lunar_mansion_system: Optional[str] = None
    moira_patterns: Optional[List[MoiraPattern]] = None
    moon_mansion: Optional[str] = None
    planetary_mansions: Optional[List[PlanetMansion]] = None
    si_yu_sign_index: Optional[Dict[str, int]] = None
    weekday_ruler: Optional[str] = None


class India(PartialOutput):
    ayanamsha: Optional[float] = None
    moon_nakshatra: Optional[str] = None
    rising_nakshatra: Optional[str] = None


class ThirteenSector(PartialOutput):
    cusp_longitude: Optional[float] = None
    sector: Optional[int] = None
    sign: Optional[str] = None


class Midpoint(PartialOutput):
    degree_in_sign: Optional[float] = None
    id_a: Optional[str] = None
    id_b: Optional[str] = None
    idA: Optional[str] = None
    idB: Optional[str] = None
    longitude: Optional[float] = None
    sign: Optional[str] = None
    sign_zh: Optional[str] = None


class MidpointAspect(PartialOutput):
    aspect: Optional[str] = None
    midpoint: Optional[str] = None
    orb: Optional[float] = None
    planet: Optional[str] = None


class RelativeMidpointHit(PartialOutput):
    aspect: Optional[str] = None
    delta: Optional[float] = None
    midpoint: Optional[Midpoint] = None


class RelativeContact(PartialOutput):
    aspect: Optional[str] = None
    delta: Optional[float] = None
    id: Optional[str] = None


class DirectionalContacts(PartialOutput):
    id: Optional[str] = None
    objects: Optional[List[RelativeContact]] = None


class RelativeAntiscia(PartialOutput):
    idA: Optional[str] = None
    idB: Optional[str] = None
    delta: Optional[float] = None


class SynastryAspect(PartialOutput):
    aspect: Optional[str] = None
    inner: Optional[str] = None
    orb: Optional[float] = None
    outer: Optional[str] = None


class CompatibilityScores(PartialOutput):
    element_harmony_score: Optional[int] = None
    modality_balance_score: Optional[int] = None
    overall_score: Optional[int] = None
    synastry_aspect_score: Optional[int] = None


class ChartPerson(PartialOutput):
    birth_latitude: Optional[float] = None
    birth_longitude: Optional[float] = None
    birth_place: Optional[str] = None
    birth_timezone: Optional[str] = None
    name: Optional[str] = None


class Chart(PartialOutput):
    angles: Optional[Dict[str, ChartAngle]] = None
    aspects: Optional[List[ChartAspect]] = None
    balance_basis: Optional[str] = None
    chart_profile: Optional[ChartProfile] = None
    element_balance: Optional[Dict[str, float]] = None
    houses: Optional[List[ChartHouse]] = None
    modality_balance: Optional[Dict[str, float]] = None
    person_info: Optional[ChartPerson] = None
    planets: Optional[List[ChartPlanet]] = None
    summary: Optional[List[str]] = None


class InnerOuter(PartialOutput):
    chart: Optional[Chart] = None
    chart_profile: Optional[ChartProfile] = None
    summary: Optional[List[str]] = None


class RelationshipFocus(PartialOutput):
    emphasis_bodies: Optional[List[str]] = None
    emphasis_houses: Optional[List[int]] = None
    focus: Optional[str] = None
    focus_label_zh: Optional[str] = None
    focused_aspect_count: Optional[int] = None
    focused_synastry_aspects: Optional[List[SynastryAspect]] = None
    note: Optional[str] = None


class RelationshipProfile(PartialOutput):
    chart_type: Optional[str] = None
    engine_backend: Optional[str] = None
    engine_precision: Optional[str] = None
    focus: Optional[RelationshipFocus] = None
    house_system: Optional[str] = None
    house_system_label_zh: Optional[str] = None
    hsys: Optional[int] = None
    mode_status: Optional[str] = None
    primary_layer: Optional[str] = None
    relative_mode_input: Optional[Union[str, int]] = None
    relative_mode_label_zh: Optional[str] = None
    relative_mode_normalized: Optional[str] = None
    relative_mode_resolution: Optional[str] = None
    zodiac_label_zh: Optional[str] = None
    zodiac_mode: Optional[str] = None
    zodiacal: Optional[int] = None


CHART_FIELDS: Dict[str, Any] = {
    "angles": Dict[str, ChartAngle],
    "aspects": List[ChartAspect],
    "houses": List[ChartHouse],
    "planets": List[ChartPlanet],
    "fixed_stars": List[FixedStar],
    "planetary_hours": PlanetaryHours,
    "chart_profile": ChartProfile,
    "classical": Classical,
    "classical_patterns": ClassicalPatterns,
    "hellenistic": Hellenistic,
    "guolao": Guolao,
    "india": India,
    "thirteen_sectors": List[ThirteenSector],
    "midpoints": List[Midpoint],
    "midpoint_aspects": List[MidpointAspect],
    "element_balance": Dict[str, float],
    "modality_balance": Dict[str, float],
    "base_chart": Chart,
    "inner_chart": Chart,
    "outer_chart": Chart,
    "inner": InnerOuter,
    "outer": InnerOuter,
    "compatibility": CompatibilityScores,
    "relationship_profile": RelationshipProfile,
    "synastry_aspects": List[SynastryAspect],
    **{
        name: List[DirectionalContacts]
        for name in (
            "in_to_out_aspects",
            "out_to_in_aspects",
        )
    },
    **{
        name: List[RelativeAntiscia]
        for name in (
            "in_to_out_antiscia",
            "out_to_in_antiscia",
            "in_to_out_contra_antiscia",
            "out_to_in_contra_antiscia",
        )
    },
    **{
        name: Dict[str, List[RelativeMidpointHit]]
        for name in (
            "in_to_out_midpoint",
            "out_to_in_midpoint",
        )
    },
}

CHART_TOOL_FIELDS: Dict[str, Dict[str, Any]] = {
    "astro_relative": {"chart": Chart},
    "astro_relative_chart": {"chart": Chart},
}
