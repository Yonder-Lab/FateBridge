"""Shared Swiss Ephemeris runtime helpers.

This module is the single import point for the optional ``swisseph`` dependency.
Centralising it lets FateBridge do two things consistently across every module
that touches the ephemeris (charts, almanac, predictive directions):

* Apply an operator-supplied data-file path once, process-wide, via the
  ``SE_EPHE_PATH`` environment variable. Swiss Ephemeris silently falls back to
  its built-in Moshier analytical model when no ``.se1`` data files are
  reachable; pointing it at the official files unlocks full DE431-precision
  ``SWIEPH`` calculations.
* Translate a ``calc_ut`` return flag into the ephemeris model that was *actually*
  used, so callers can label their output honestly instead of assuming the model
  they requested was the one that ran.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator, Optional

try:  # pragma: no cover - optional runtime dependency
    import swisseph as swe
except ImportError:  # pragma: no cover - exercised only in minimal installs
    swe = None  # type: ignore[assignment]

# Repo root that holds the optional ``ephe/`` data directory (gitignored .se1
# files, never redistributed, so they live outside the package). Module lives at
# ``<root>/src/fatebridge/core/ephemeris_runtime.py``, so the root is three
# parents up.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_EPHEMERIS_LOCK = RLock()
_configured_path: Optional[str] = None


def default_ephe_dir() -> Optional[str]:
    """Return the project-local ``ephe/`` directory when it holds data files.

    Lets a checkout that ran ``python -m fatebridge.fetch_ephe`` pick up full
    precision with zero configuration — no environment variable required. The
    directory is only reported when it actually contains ``.se1`` files, so an
    empty folder does not mask the Moshier fallback.
    """
    candidate = _PROJECT_ROOT / "ephe"
    if candidate.is_dir() and any(candidate.glob("*.se1")):
        return str(candidate)
    return None


def configure_ephemeris_path(path: Optional[str] = None) -> Optional[str]:
    """Point Swiss Ephemeris at ``.se1`` data files, if any can be located.

    Resolution order: the explicit ``path`` argument, then the ``SE_EPHE_PATH``
    environment variable, then a project-local ``ephe/`` directory (see
    :func:`default_ephe_dir`). Returns the path that was applied, or ``None``
    when none was found (or swisseph is unavailable), in which case swisseph
    keeps using its built-in Moshier model.

    ``swe.set_ephe_path`` mutates global C state, so a single call anywhere in
    the process is enough for every module that imports ``swe`` from here.
    """
    global _configured_path
    with _EPHEMERIS_LOCK:
        if swe is None:
            return None
        resolved = (
            path
            if path is not None
            else os.environ.get("SE_EPHE_PATH") or default_ephe_dir()
        )
        if resolved is not None:
            swe.set_ephe_path(resolved)
        _configured_path = resolved
        return resolved


@contextmanager
def preserve_ephemeris_path() -> Iterator[None]:
    """Isolate third-party configuration changes from FateBridge calculations.

    Kerykeion changes the shared Swiss Ephemeris data path. Hold the same lock
    used by direct ephemeris calls until its calculation and path restoration
    finish, including when the third-party call raises.
    """
    with _EPHEMERIS_LOCK:
        try:
            yield
        finally:
            if swe is not None:
                swe.set_ephe_path(_configured_path or "")


def ephemeris_call(operation: str, *args: Any, **kwargs: Any) -> Any:
    """Run a direct Swiss Ephemeris call outside third-party path changes."""
    with _EPHEMERIS_LOCK:
        if swe is None:
            raise ImportError("swisseph is unavailable")
        return getattr(swe, operation)(*args, **kwargs)


def ephemeris_model_from_retflag(retflag: int) -> str:
    """Map a ``swisseph.calc_ut`` return flag to the model that produced it.

    swisseph echoes the ephemeris it actually used in the returned flag, which
    may differ from the one requested (e.g. ``FLG_SWIEPH`` requested but the data
    files are missing, so it quietly downgraded to Moshier). Possible values:

    * ``"swieph"``  – Swiss Ephemeris compressed data files (full precision)
    * ``"moshier"`` – built-in Moshier analytical model (no data files needed)
    * ``"jpl"``     – JPL ephemeris data files
    * ``"error"``   – swisseph reported a soft failure (``retflag < 0``)
    * ``"unknown"`` – flag set none of the recognised ephemeris bits
    * ``"unavailable"`` – swisseph itself is not installed
    """
    if swe is None:
        return "unavailable"
    if retflag < 0:
        return "error"
    if retflag & swe.FLG_MOSEPH:
        return "moshier"
    if retflag & swe.FLG_JPLEPH:
        return "jpl"
    if retflag & swe.FLG_SWIEPH:
        return "swieph"
    return "unknown"


# Apply any operator-supplied ephemeris path at import time so it is in effect
# before the first calc_ut call, regardless of which module imports swe first.
configure_ephemeris_path()
