"""Phase 3b (part 2) tests: fixed stars (恒星).

The catalogue is vendored (J2000 tropical longitudes extracted from the Swiss
Ephemeris star catalogue — public astronomical fact) and precessed in pure
Python, so the feature needs no ephemeris data file and runs on every engine.

* **Pure** tests (precession, conjunction detection, catalogue integrity) run
  everywhere.
* A **calibration** test locks the vendored table against swisseph's
  authoritative ``fixstar_ut`` — gated on the ``sefstars.txt`` catalogue being
  reachable (kerykeion bundles it), so it runs locally and skips in CI.
"""

from __future__ import annotations

import pytest

from fatebridge.core import astrology
from fatebridge.core.astrology import build_astro_birth_info, build_core_chart_payload
from fatebridge.core.classical_western import (
    _J2000_JD,
    FIXED_STARS,
    PRECESSION_DEG_PER_YEAR,
    build_fixed_star_hits,
    fixed_star_longitude,
)
from fatebridge.services.astrology import calculate_core_chart_analysis

_NATAL = dict(
    birth_year=2000,
    birth_month=12,
    birth_day=10,
    birth_hour=9,
    birth_minute=55,
    birth_timezone="Asia/Shanghai",
    birth_longitude=120.4667,
    birth_latitude=32.5417,
    name="左右",
    birth_place="海安",
)


def _configure_star_catalogue() -> bool:
    """Point swisseph at kerykeion's bundled ``sefstars.txt`` for calibration.

    Returns True when ``fixstar_ut`` then works; False (→ skip) otherwise, e.g.
    in CI where the catalogue file is not on the swisseph search path.
    """
    if astrology.swe is None:
        return False
    try:
        import pathlib

        import kerykeion

        astrology.swe.set_ephe_path(
            str(pathlib.Path(kerykeion.__file__).parent / "sweph")
        )
        astrology.swe.fixstar_ut("Spica", _J2000_JD, astrology.swe.FLG_SWIEPH)
        return True
    except Exception:
        return False


# ── pure: catalogue + precession ──────────────────────────────────────────────


def test_catalogue_is_well_formed():
    assert len(FIXED_STARS) == 20
    for star, data in FIXED_STARS.items():
        assert 0.0 <= data["lon2000"] < 360.0
        assert data["nature"]  # at least one Ptolemaic nature (traditional attr)
        assert data["cn"]  # traditional Chinese name
        # No interpretive prose in the engine — that's the skills layer's job.
        assert "gloss" not in data


def test_precession_is_zero_at_j2000_and_advances_forward():
    # At J2000 the precessed longitude is the stored value.
    assert fixed_star_longitude(100.0, _J2000_JD) == pytest.approx(100.0)
    # One century forward advances by ~100 × 50.29″ ≈ 1.397°.
    one_century = _J2000_JD + 365.25 * 100
    advanced = fixed_star_longitude(100.0, one_century)
    assert advanced - 100.0 == pytest.approx(PRECESSION_DEG_PER_YEAR * 100, rel=1e-9)
    assert 1.39 < advanced - 100.0 < 1.40


# ── pure: conjunction detection ───────────────────────────────────────────────


def test_conjunction_detected_within_orb_and_excluded_beyond():
    spica_lon = fixed_star_longitude(FIXED_STARS["Spica"]["lon2000"], _J2000_JD)
    # A point sitting on Spica is a hit; one 1.5° away (orb 1°) is not.
    on = build_fixed_star_hits({"Venus": spica_lon}, _J2000_JD)
    assert any(h["star"] == "Spica" and h["point"] == "Venus" for h in on)
    off = build_fixed_star_hits({"Venus": (spica_lon + 1.5) % 360.0}, _J2000_JD)
    assert not any(h["star"] == "Spica" for h in off)


def test_hits_sorted_by_orb_tightest_first():
    spica = fixed_star_longitude(FIXED_STARS["Spica"]["lon2000"], _J2000_JD)
    points = {"Venus": spica + 0.1, "Mars": spica + 0.6}
    hits = [h for h in build_fixed_star_hits(points, _J2000_JD) if h["star"] == "Spica"]
    assert [h["point"] for h in hits] == ["Venus", "Mars"]


# ── integration: real chart ───────────────────────────────────────────────────


@pytest.fixture(scope="module")
def natal_stars():
    info = build_astro_birth_info(use_true_solar_time=True, **_NATAL)
    return build_core_chart_payload(info, "hellen_chart")["fixed_stars"]


def test_natal_chart_surfaces_antares_on_mercury(natal_stars):
    # Real sky: Antares sits ~0.1° from this chart's Mercury.
    antares = [h for h in natal_stars if h["star"] == "Antares"]
    assert antares, "expected Antares conjunct a chart point"
    assert antares[0]["point"] == "Mercury"
    assert antares[0]["orb"] < 0.2


def test_snapshot_renders_fixed_stars_section():
    payload = calculate_core_chart_analysis(
        chart_variant="hellen_chart", use_true_solar_time=True, **_NATAL
    )
    text = payload["snapshot_text"]
    assert "[恒星]" in text
    assert "心宿二" in text  # Antares' Chinese name


# ── calibration: vendored table vs authoritative swisseph (local only) ────────


@pytest.mark.skipif(
    not _configure_star_catalogue(),
    reason="sefstars.txt 不可达：恒星表校准需要 swisseph 星表",
)
def test_vendored_longitudes_match_swisseph_within_conjunction_orb():
    # Vendored J2000 + linear precession tracks swisseph's full model (which also
    # carries proper motion + nutation/aberration) to ~12″ at epoch, and < 0.05°
    # across ±150 years — the high-PM stars (Sirius, Arcturus) drift most but stay
    # far inside the 1° conjunction orb the feature uses.
    for jd in (_J2000_JD - 365.25 * 150, _J2000_JD, _J2000_JD + 365.25 * 150):
        for star, data in FIXED_STARS.items():
            mine = fixed_star_longitude(data["lon2000"], jd)
            coords, _, _ = astrology.swe.fixstar_ut(star, jd, astrology.swe.FLG_SWIEPH)
            delta = abs(((mine - coords[0] + 180.0) % 360.0) - 180.0)
            assert delta < 0.05, f"{star} off by {delta * 3600:.0f}″ at jd {jd}"
