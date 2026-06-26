"""Regression: default "current moment" must not drift with the server's clock.

Bare ``datetime.now()`` reads the *server* timezone, so a UTC-deployed host
resolves the wrong calendar date for callers who omit an explicit
year/month/day — most visibly the 流年 year near the New Year / 立春 boundary.
``current_local_datetime`` anchors the default to a fixed civil timezone
(Asia/Shanghai) so the resolution is deterministic wherever the process runs.
"""

from datetime import datetime, timezone

from dateutil import tz as dateutil_tz

from fatebridge.core.almanac import DEFAULT_TIMEZONE, current_local_datetime


def test_returns_naive_datetime() -> None:
    """Downstream code decomposes this into naive year/month/day; keep it naive
    so it never mixes with the aware datetimes elsewhere (TypeError)."""
    assert current_local_datetime().tzinfo is None


def test_anchored_to_default_timezone_not_server_clock() -> None:
    """The wall-clock must equal UTC-now projected into Asia/Shanghai, proving
    it is anchored to the civil timezone rather than the process's local TZ.

    Against the old ``datetime.now()`` this assertion fails on any non-Shanghai
    server; against the helper it holds regardless of where the test runs.
    """
    shanghai = dateutil_tz.gettz(DEFAULT_TIMEZONE)
    reference = datetime.now(timezone.utc).astimezone(shanghai).replace(tzinfo=None)
    got = current_local_datetime()
    assert abs((got - reference).total_seconds()) < 5


def test_honours_explicit_timezone() -> None:
    """An explicit timezone overrides the default so callers that already carry
    an analysis timezone (e.g. the subject's birth timezone) stay consistent."""
    utc_now = current_local_datetime("UTC")
    reference = datetime.now(timezone.utc).replace(tzinfo=None)
    assert abs((utc_now - reference).total_seconds()) < 5
