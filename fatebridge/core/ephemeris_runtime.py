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
from typing import Optional

try:  # pragma: no cover - optional runtime dependency
    import swisseph as swe
except ImportError:  # pragma: no cover - exercised only in minimal installs
    swe = None  # type: ignore[assignment]


def configure_ephemeris_path(path: Optional[str] = None) -> Optional[str]:
    """Point Swiss Ephemeris at user-supplied ``.se1`` data files.

    Reads the explicit ``path`` argument when given, otherwise the
    ``SE_EPHE_PATH`` environment variable. Returns the path that was applied, or
    ``None`` when no path was configured (or swisseph is unavailable), in which
    case swisseph keeps using its built-in Moshier model.

    ``swe.set_ephe_path`` mutates global C state, so a single call anywhere in
    the process is enough for every module that imports ``swe`` from here.
    """
    if swe is None:
        return None
    resolved = path if path is not None else os.environ.get("SE_EPHE_PATH")
    if resolved:
        swe.set_ephe_path(resolved)
        return resolved
    return None


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
