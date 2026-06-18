"""run_metadata: tool_name is authoritative (from the spec), never guessed.

After the catalog unification every surface stamps run_metadata with the
ToolSpec's name, so the old payload-shape inference is dead. These tests lock
that contract: the renderer must NOT reverse-engineer a name from payload shape.
"""

import json

from fatebridge.services import run_metadata
from fatebridge.services.run_metadata import (
    attach_run_metadata,
    resolve_runtime_engine,
)


def test_attach_run_metadata_uses_explicit_name():
    out = attach_run_metadata({"x": 1}, tool_name="bazi_wealth")
    assert out["run_metadata"]["tool_name"] == "bazi_wealth"


def test_attach_run_metadata_is_idempotent():
    seeded = {"run_metadata": {"tool_name": "already"}, "x": 1}
    assert attach_run_metadata(seeded, tool_name="other") is seeded


def test_resolve_runtime_engine_still_detects_engine():
    assert (
        resolve_runtime_engine({"chart_profile": {"engine_backend": "swiss"}})
        == "swiss"
    )
    assert resolve_runtime_engine({"nothing": 1}) == run_metadata.DEFAULT_ENGINE


def test_payload_inference_heuristics_are_removed():
    # Guard against reintroducing the fragile guesser.
    assert not hasattr(run_metadata, "infer_tool_name_from_payload")
    assert not hasattr(run_metadata, "infer_tool_name_from_service")


def test_render_does_not_guess_tool_name_from_payload_shape():
    from fastmcp_server import _render_tool_response

    # A payload whose shape the OLD guesser would have mapped to "chart13".
    misleading = {"chart_profile": {"chart_type": "chart13"}}
    rendered = _render_tool_response(misleading, tool_name=None)
    payload = json.loads(rendered)
    # No explicit name supplied -> a neutral marker, NOT a shape-derived guess.
    assert payload["run_metadata"]["tool_name"] == "unknown_tool"
