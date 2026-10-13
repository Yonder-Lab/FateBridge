"""Small, explicitly fictional starter inputs shared by all transports."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from fatebridge.application.tool_spec import ToolSpec


@lru_cache(maxsize=1)
def _examples() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "data/agent_examples.json"
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def example_input(spec: ToolSpec) -> Optional[Dict[str, Any]]:
    bundle = _examples()
    source = bundle["tools"].get(spec.key)
    if source is None:
        return None
    if isinstance(source, str):
        source = bundle["subjects"][source]
    inputs = {k: v for k, v in source.items() if k in spec.request_model.model_fields}
    # Fail loudly on stale published examples; never substitute fabricated input.
    spec.request_model.model_validate(inputs)
    return inputs


def suggested_fields(spec: ToolSpec) -> Optional[List[str]]:
    """Small first-response views; callers can expand for a deeper question."""
    fields = _examples().get("suggested_fields", {}).get(spec.key)
    return list(fields) if fields is not None else None
