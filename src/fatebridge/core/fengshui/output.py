"""Public layered contract, including projection-compatible optional fields."""

from typing import Dict, List, Literal, Optional

from fatebridge.core.response_models import (
    Object,
    PartialOutput,
    ProjectedOutput,
    RunMetadata,
    SnapshotExport,
)


class RuleSource(PartialOutput):
    # Only exposed as array items: projections select sources whole.
    source_id: str
    title: str
    url: str
    kind: str
    scope: str


class Ruleset(PartialOutput):
    ruleset_id: Optional[str] = None
    version: Optional[str] = None
    method: Optional[str] = None
    source_ids: Optional[List[str]] = None
    sources: Optional[List[RuleSource]] = None
    scope: Optional[str] = None
    conventions: Optional[List[str]] = None
    bundle_version: Optional[str] = None


class Star(PartialOutput):
    name: Optional[str] = None
    element: Optional[str] = None
    polarity: Optional[Literal["auspicious", "inauspicious"]] = None


class Palace(PartialOutput):
    direction: Optional[str] = None
    palace_number: Optional[int] = None
    trigram: Optional[str] = None
    annual_star_number: Optional[int] = None
    annual_star: Optional[Star] = None
    star: Optional[Star] = None
    subject_id: Optional[str] = None
    rule_id: Optional[str] = None
    source_ids: Optional[List[str]] = None


class MingguaCandidate(PartialOutput):
    gender_convention: Optional[Literal["male", "female"]] = None
    raw_number: Optional[int] = None
    palace_number: Optional[int] = None
    substitution: Optional[bool] = None
    trigram: Optional[str] = None
    group: Optional[Literal["east", "west"]] = None
    sectors: Optional[Dict[str, Palace]] = None


class PersonalChart(PartialOutput):
    status: Optional[Literal["complete", "partial"]] = None
    subject_id: Optional[str] = None
    candidates: Optional[List[MingguaCandidate]] = None
    time_context: Optional[Object] = None
    missing_inputs: Optional[List[str]] = None


class HouseChart(PartialOutput):
    object_id: Optional[str] = None
    sitting_trigram: Optional[str] = None
    north_reference: Optional[Literal["true", "magnetic"]] = None
    sectors: Optional[Dict[str, Palace]] = None


class Layer(PersonalChart):
    ruleset: Optional[Ruleset] = None
    house: Optional[HouseChart] = None
    occupants: Optional[List[PersonalChart]] = None
    placement_findings: Optional[List[Object]] = None
    feature_findings: Optional[List[Object]] = None
    preferences: Optional[Dict[str, Object]] = None
    palaces: Optional[Dict[str, Palace]] = None
    effective_year: Optional[int] = None
    center_star_number: Optional[int] = None
    current_period: Optional[Object] = None
    directions: Optional[Dict[str, Object]] = None
    bearing: Optional[Object] = None


class NatalPalace(PartialOutput):
    direction: Optional[str] = None
    palace_number: Optional[int] = None
    period_star_number: Optional[int] = None
    mountain_star_number: Optional[int] = None
    facing_star_number: Optional[int] = None


class NatalCandidate(PartialOutput):
    candidate_id: Optional[str] = None
    period_number: Optional[int] = None
    facing: Optional[Object] = None
    sitting: Optional[Object] = None
    chart_mode: Optional[Literal["lower", "replacement"]] = None
    mode_reason: Optional[str] = None
    palaces: Optional[Dict[str, NatalPalace]] = None
    period_chart: Optional[Dict[str, int]] = None
    mountain_chart: Optional[Dict[str, int]] = None
    facing_chart: Optional[Dict[str, int]] = None
    trace: Optional[Dict[str, Object]] = None
    flight_path: Optional[List[str]] = None


class NatalLayer(PartialOutput):
    status: Optional[Literal["complete", "partial"]] = None
    subject_id: Optional[str] = None
    ruleset: Optional[Ruleset] = None
    period_context: Optional[Object] = None
    orientation_context: Optional[Object] = None
    chart: Optional[NatalCandidate] = None
    candidates: Optional[List[NatalCandidate]] = None
    missing_inputs: Optional[List[str]] = None
    interpretation_scope: Optional[str] = None
    mountain_registry: Optional[List[Object]] = None


class Layers(PartialOutput):
    directions: Optional[Layer] = None
    minggua: Optional[Layer] = None
    bazhai: Optional[Layer] = None
    jinsuo: Optional[Layer] = None
    annual_stars: Optional[Layer] = None
    xuankong_natal: Optional[NatalLayer] = None


class Coverage(PartialOutput):
    implemented_layers: Optional[List[str]] = None
    missing_inputs: Optional[List[str]] = None
    unavailable_layers: Optional[List[str]] = None
    not_requested_layers: Optional[List[str]] = None


class FengshuiOutput(ProjectedOutput):
    analysis_type: Optional[str] = None
    engine: Optional[str] = None
    status: Optional[Literal["complete", "partial"]] = None
    layers: Optional[Layers] = None
    rulesets: Optional[List[Ruleset]] = None
    coverage: Optional[Coverage] = None
    conflicts: Optional[List[Object]] = None
    rule_trace: Optional[List[Object]] = None
    summary: Optional[str] = None
    snapshot_text: Optional[str] = None
    snapshot_export: Optional[SnapshotExport] = None
    run_metadata: Optional[RunMetadata] = None
