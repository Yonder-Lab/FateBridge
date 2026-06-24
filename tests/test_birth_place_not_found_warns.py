"""An uncatalogued birth place must be observable, not silently ignored.

Past geocoding bugs (#142, #143) were silent fallbacks: a place that wasn't in
the offline catalog quietly skipped true-solar-time longitude correction with no
signal. ``resolve_birth_place_context`` still returns an all-``None`` resolution
for an unknown place (callers handle that), but it now emits a WARNING so the
skipped correction is visible in logs instead of disappearing.
"""

from __future__ import annotations

import logging

from fatebridge.utils.helpers import (
    _resolve_birth_place_context_cached,
    resolve_birth_place_context,
)


def test_uncatalogued_birth_place_emits_warning(caplog):
    # The resolver is lru_cached; clear it so the warning path actually runs.
    _resolve_birth_place_context_cached.cache_clear()

    with caplog.at_level(logging.WARNING):
        result = resolve_birth_place_context("齐天大圣花果山水帘洞")

    assert result.longitude is None
    assert result.canonical_name is None
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warnings, "uncatalogued birth place should emit a WARNING"


def test_empty_birth_place_stays_silent(caplog):
    # The "not provided" sentinel is not a failure to resolve — no warning noise.
    _resolve_birth_place_context_cached.cache_clear()

    with caplog.at_level(logging.WARNING):
        result = resolve_birth_place_context("未提供")

    assert result.longitude is None
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
