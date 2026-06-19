"""Unit tests for the shared Swiss Ephemeris runtime helpers."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.core import ephemeris_runtime
from fatebridge.core.ephemeris_runtime import (
    configure_ephemeris_path,
    ephemeris_model_from_retflag,
)


def test_configure_ephemeris_path_uses_explicit_argument(monkeypatch):
    swe = pytest.importorskip("swisseph")
    captured = {}
    monkeypatch.setattr(
        swe, "set_ephe_path", lambda path: captured.setdefault("path", path)
    )

    applied = configure_ephemeris_path("/tmp/fatebridge-ephe")

    assert applied == "/tmp/fatebridge-ephe"
    assert captured["path"] == "/tmp/fatebridge-ephe"


def test_configure_ephemeris_path_reads_env(monkeypatch):
    swe = pytest.importorskip("swisseph")
    captured = {}
    monkeypatch.setattr(
        swe, "set_ephe_path", lambda path: captured.setdefault("path", path)
    )
    monkeypatch.setenv("SE_EPHE_PATH", "/data/ephe")

    applied = configure_ephemeris_path()

    assert applied == "/data/ephe"
    assert captured["path"] == "/data/ephe"


def test_configure_ephemeris_path_noop_without_path(monkeypatch):
    swe = pytest.importorskip("swisseph")
    calls = []
    monkeypatch.setattr(swe, "set_ephe_path", lambda path: calls.append(path))
    monkeypatch.delenv("SE_EPHE_PATH", raising=False)

    assert configure_ephemeris_path() is None
    assert calls == []


def test_ephemeris_model_from_retflag_maps_known_flags():
    swe = pytest.importorskip("swisseph")

    assert ephemeris_model_from_retflag(swe.FLG_SWIEPH) == "swieph"
    assert ephemeris_model_from_retflag(swe.FLG_MOSEPH) == "moshier"
    assert ephemeris_model_from_retflag(swe.FLG_JPLEPH) == "jpl"


def test_ephemeris_model_from_retflag_flags_errors():
    pytest.importorskip("swisseph")

    assert ephemeris_model_from_retflag(-1) == "error"


def test_ephemeris_model_from_retflag_unavailable(monkeypatch):
    monkeypatch.setattr(ephemeris_runtime, "swe", None)

    assert ephemeris_model_from_retflag(2) == "unavailable"
    assert configure_ephemeris_path("/whatever") is None
