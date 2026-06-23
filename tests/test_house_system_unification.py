"""House-system parameter unification (#2b).

FateBridge historically exposed two parallel conventions for the same concept:
the core/relative chart family takes an integer ``hsys`` (0..8) while the
western timing/lifespan/horary/election family takes a ``house_system`` letter
string ('P', 'R', ...). That split made agents and users guess which knob a
given tool wants.

The integer side already accepts letters and keys (via
``_coerce_house_system_code``). These tests pin the symmetric direction: the
``house_system`` chokepoint (``normalize_house_system``) must also accept the
integer codes 0..8 and the canonical keys ("equal_mc", "sripati", ...), so a
single mental model — int code, SE letter, or key — works on every surface.
"""

from __future__ import annotations

import pytest

from fatebridge.utils.helpers import normalize_house_system

# Integer code -> Swiss Ephemeris letter, identical to the core chart's
# RELATIVE_HOUSE_SYSTEM_SPECS (0=whole_sign ... 8=equal_mc).
_CODE_TO_LETTER = {
    0: "W",
    1: "B",
    2: "R",
    3: "P",
    4: "K",
    5: "V",
    6: "T",
    7: "S",
    8: "D",
}


@pytest.mark.parametrize("code,letter", sorted(_CODE_TO_LETTER.items()))
def test_normalize_accepts_integer_codes(code, letter):
    assert normalize_house_system(code) == letter
    assert normalize_house_system(str(code)) == letter


def test_normalize_accepts_canonical_keys():
    # These keys are the ones the integer (hsys) family reports; the letter
    # family must understand them too. equal_mc and sripati were the gaps that
    # silently fell back to Placidus.
    assert normalize_house_system("equal_mc") == "D"
    assert normalize_house_system("equal_mc".upper()) == "D"
    assert normalize_house_system("sripati") == "S"
    assert normalize_house_system("whole_sign") == "W"


def test_unknown_still_falls_back_to_default():
    # Out-of-range integers and gibberish keep the documented fallback so a
    # typo can't masquerade as a valid system.
    assert normalize_house_system(99) == "P"
    assert normalize_house_system("not-a-system") == "P"
    assert normalize_house_system(0, default="R") == "W"  # valid code wins over default


@pytest.mark.parametrize("value", [8, "8", "equal_mc", "R", "regiomontanus"])
def test_western_models_accept_every_convention(value):
    # The western timing/horary/election models must accept an integer code, a
    # numeric string, a key, or an SE letter — the same mental model as the
    # integer ``hsys`` family. (Previously the field was typed ``str`` and a bare
    # integer raised a ValidationError.)
    from fatebridge.core.request_models import (
        AstroHoraryRequest,
        WesternTimingRequest,
    )

    common = dict(
        birth_year=2000,
        birth_month=12,
        birth_day=10,
        birth_hour=9,
        birth_longitude=120.0,
        birth_latitude=30.0,
    )
    timing = WesternTimingRequest(**common, house_system=value)
    assert normalize_house_system(timing.house_system) in {
        "W",
        "B",
        "R",
        "P",
        "K",
        "V",
        "T",
        "S",
        "D",
    }
    horary = AstroHoraryRequest(
        question_year=2000,
        question_month=12,
        question_day=10,
        question_hour=9,
        longitude=121.47,
        latitude=31.23,
        house_system=value,
    )
    assert isinstance(horary.house_system, (int, str))


def test_western_default_house_system_unchanged():
    # The unification must not move any default: timing stays Placidus, horary
    # stays Regiomontanus (golden output must be byte-stable).
    from fatebridge.core.request_models import (
        AstroHoraryRequest,
        WesternTimingRequest,
    )

    timing = WesternTimingRequest(
        birth_year=2000,
        birth_month=12,
        birth_day=10,
        birth_hour=9,
        birth_longitude=120.0,
        birth_latitude=30.0,
    )
    assert normalize_house_system(timing.house_system) == "P"
    horary = AstroHoraryRequest(
        question_year=2000,
        question_month=12,
        question_day=10,
        question_hour=9,
        longitude=121.47,
        latitude=31.23,
    )
    assert normalize_house_system(horary.house_system) == "R"
