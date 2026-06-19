"""Contract test guarding the public ``skills/`` suite against engine drift.

The Onda skills delegate every calculation to ``python3 -m fatebridge.cli
<tool>``; if a tool is renamed/removed in the catalog, or a newly added tool is
never surfaced to the skills, the docs silently drift out of sync with the
engine. The engine itself is covered by test_cli / test_full_surface_validation,
but nothing previously checked the skills docs against the catalog.

This asserts the coverage contract the project promises: every CLI-exposable
tool is documented somewhere under ``skills/``.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from fatebridge.services.tool_catalog import CATALOG

_SKILLS_ROOT = Path(__file__).resolve().parents[1] / "skills"


def _is_model_field(annotation: object) -> bool:
    try:
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return True
    except TypeError:
        pass
    return any(
        isinstance(arg, type) and issubclass(arg, BaseModel)
        for arg in getattr(annotation, "__args__", ())
    )


def _supports_cli(spec: object) -> bool:
    """Mirror fatebridge.cli._supports_cli: no nested-model request fields."""
    return not any(
        _is_model_field(f.annotation)
        for f in spec.request_model.model_fields.values()  # type: ignore[attr-defined]
    )


def _cli_tool_names() -> set[str]:
    names = set()
    for spec in CATALOG:
        if not _supports_cli(spec):
            continue
        names.add(spec.mcp_name or spec.key)
    return {n for n in names if n}


def _skills_backticked_tokens() -> set[str]:
    text = "\n".join(p.read_text() for p in _SKILLS_ROOT.rglob("*.md"))
    return set(re.findall(r"`([a-z][a-z0-9_]+)`", text))


def test_every_cli_tool_is_documented_in_skills():
    """No orphan tools: each CLI-exposable tool is referenced in skills docs."""
    documented = _skills_backticked_tokens()
    undocumented = sorted(t for t in _cli_tool_names() if t not in documented)
    assert not undocumented, (
        "These CLI tools exist in the catalog but no skill references them "
        f"(agents can't reach them): {undocumented}"
    )


def test_skills_root_is_present_and_nonempty():
    # Guard against the test silently passing if skills/ is moved or emptied.
    skill_files = list(_SKILLS_ROOT.rglob("SKILL.md"))
    assert len(skill_files) >= 5
