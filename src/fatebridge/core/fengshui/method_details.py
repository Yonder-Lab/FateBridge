"""Source-labelled method and palace references; these do not judge a house."""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, cast

from .directions import rule_data


@lru_cache(maxsize=1)
def _bundle() -> Dict[str, Any]:
    path = Path(__file__).parents[2] / "data" / "fengshui" / "expert-methods-v1.json"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def reference_data(key: str) -> Any:
    """Return isolated data so projections and callers cannot mutate the cache."""
    return deepcopy(_bundle()[key])


def method_reference_provenance() -> Dict[str, Any]:
    record = reference_data("ruleset")
    sources = reference_data("sources")
    return {
        **record,
        "bundle_version": _bundle()["bundle_version"],
        "sources": [dict(source_id=s, **sources[s]) for s in record["source_ids"]],
    }


def method_details(methods: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Explain selected engines, keeping fixed palaces and visiting stars apart.

    An omitted filter gives the three method families. An explicit empty list
    gives no method chapters while retaining the common directional reference.
    """
    families = {
        "annual_stars": "nine_palace_flying_stars",
        "xuankong_natal": "nine_palace_flying_stars",
        "nine_palace_flying_stars": "nine_palace_flying_stars",
        "jinsuo": "jinsuo",
        "bazhai": "bazhai",
    }
    chapters = reference_data("method_details")
    selected = (
        list(chapters)
        if methods is None
        else list(dict.fromkeys(families[m] for m in methods))
    )
    palaces = reference_data("direction_references")
    for direction, record in palaces.items():
        if direction != "C":
            fixed = rule_data("directions")[direction]
            record.update(
                direction=direction,
                label=fixed["label"],
                fixed_palace_number=fixed["palace_number"],
                fixed_palace_trigram=fixed["trigram"],
                fixed_palace_element=fixed["element"],
            )
        else:
            record.update(
                direction="C",
                label="中宫",
                fixed_palace_number=5,
                fixed_palace_trigram=None,
                fixed_palace_element="土",
            )
    return {
        "status": "reference_only",
        "scope": "source_labelled_reference_not_additional_selected_calculation",
        "ruleset": method_reference_provenance(),
        "methods": {key: chapters[key] for key in selected},
        "palaces": palaces,
        "star_elements": {
            number: {"name": star["name"], "element": star["element"]}
            for number, star in rule_data("annual_stars").items()
        },
        "sand_water_reference": reference_data("sand_water_reference"),
        "limitations": reference_data("limitations"),
    }
