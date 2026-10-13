"""Stable nested facts, with projection-compatible optional fields.

Validate existing payloads without reserialization; dynamic map keys and
extension fields remain open. Definitions follow the service builders.
"""

from typing import Any, Dict, List, Optional

from fatebridge.core.output_base import PartialOutput


class SukuyoPerson(PartialOutput):
    name: Optional[str] = None
    natal_su27: Optional[str] = None
    natal_su28: Optional[str] = None
    moon_longitude: Optional[float] = None


class SukuyoRelation(PartialOutput):
    relation: Optional[str] = None
    pair: Optional[str] = None
    distance: Optional[str] = None
    meaning: Optional[str] = None
    self_su28: Optional[str] = None
    other_su28: Optional[str] = None
    self_su27: Optional[str] = None
    other_su27: Optional[str] = None
    offset: Optional[int] = None


class KnowledgeCategory(PartialOutput):
    name: Optional[str] = None
    count: Optional[int] = None
    keys: Optional[List[str]] = None
    keys_sample: Optional[List[str]] = None
    supports: Optional[List[str]] = None


class KnowledgeCoverage(PartialOutput):
    domain: Optional[str] = None
    categories: Optional[List[KnowledgeCategory]] = None
    missing_categories: Optional[List[str]] = None
    fallback_categories: Optional[List[str]] = None


class KnowledgeProvenance(PartialOutput):
    source_domain: Optional[str] = None
    domain: Optional[str] = None
    category: Optional[str] = None
    key: Optional[str] = None
    build_timestamp: Optional[str] = None
    upstream_source_marker: Optional[str] = None
    bundle_version: Optional[int] = None
    coverage: Optional[KnowledgeCoverage] = None


class KnowledgeDomain(PartialOutput):
    domain: Optional[str] = None
    source: Optional[str] = None
    bundle_version: Optional[int] = None
    provenance: Optional[KnowledgeProvenance] = None
    categories: Optional[List[KnowledgeCategory]] = None


class KnowledgeQuery(PartialOutput):
    key: Optional[str] = None
    object_a: Optional[str] = None
    object_b: Optional[str] = None
    jiang_name: Optional[str] = None
    tian_branch: Optional[str] = None
    di_branch: Optional[str] = None


class PlanetInfoSetting(PartialOutput):
    showHouse: Optional[int] = None
    showRuler: Optional[int] = None


class AstroMeaningSetting(PartialOutput):
    enabled: Optional[int] = None


class ExportSettingsTemplate(PartialOutput):
    sections: Optional[List[str]] = None
    planetInfo: Optional[PlanetInfoSetting] = None
    astroMeaning: Optional[AstroMeaningSetting] = None


class ExportTechnique(PartialOutput):
    key: Optional[str] = None
    label: Optional[str] = None
    astro_meaning_title: Optional[str] = None
    astro_meaning_checkbox: Optional[str] = None
    preset_sections: Optional[List[str]] = None
    forbidden_sections: Optional[List[str]] = None
    supports_planet_info: Optional[bool] = None
    supports_astro_meaning: Optional[bool] = None
    supports_hover_meaning: Optional[bool] = None
    planet_info_default: Optional[PlanetInfoSetting] = None
    astro_meaning_default: Optional[AstroMeaningSetting] = None
    settings_template: Optional[ExportSettingsTemplate] = None


class NormalizedExportSettings(PartialOutput):
    version: Optional[int] = None
    sections: Optional[Dict[str, List[str]]] = None
    planetInfo: Optional[Dict[str, PlanetInfoSetting]] = None
    astroMeaning: Optional[Dict[str, AstroMeaningSetting]] = None


class ExportSection(PartialOutput):
    index: Optional[int] = None
    raw_title: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    included: Optional[bool] = None


class SnapshotExport(PartialOutput):
    technique: Optional[ExportTechnique] = None
    settings_used: Optional[NormalizedExportSettings] = None
    selected_sections: Optional[List[str]] = None
    section_titles_detected: Optional[List[str]] = None
    unknown_detected_sections: Optional[List[str]] = None
    missing_selected_sections: Optional[List[str]] = None
    sections: Optional[List[ExportSection]] = None
    export_text: Optional[str] = None


REFERENCE_TOOL_FIELDS: Dict[str, Dict[str, Any]] = {
    "sukuyo_compatibility": {
        "person1": SukuyoPerson,
        "person2": SukuyoPerson,
        "person1_to_person2": SukuyoRelation,
        "person2_to_person1": SukuyoRelation,
        "pair": str,
        "summary": str,
    },
    "knowledge_registry": {
        "domains": List[KnowledgeDomain],
        "provenance": KnowledgeProvenance,
    },
    "knowledge_read": {
        "query_normalized": KnowledgeQuery,
        "provenance": KnowledgeProvenance,
        "lines": List[str],
        "tips": List[str],
    },
    "export_registry": {
        "techniques": List[ExportTechnique],
        "selected_technique": ExportTechnique,
        "planet_info_default": PlanetInfoSetting,
        "astro_meaning_default": AstroMeaningSetting,
        "default_normalized_settings": NormalizedExportSettings,
        "jieqi_split_keys": List[str],
    },
    "export_parse": {
        "technique": ExportTechnique,
        "settings_used": NormalizedExportSettings,
        "sections": List[ExportSection],
        "selected_sections": List[str],
        "section_titles_detected": List[str],
        "unknown_detected_sections": List[str],
        "missing_selected_sections": List[str],
    },
}
