"""Shared timezone parsing for input normalization and calendar calculations."""

import re
from datetime import timedelta, timezone, tzinfo
from functools import lru_cache
from typing import cast

from dateutil import tz

_OFFSET = re.compile(r"^(?:UTC|GMT)?([+-]?)(\d{1,2})(?::?(\d{2}))?$", re.IGNORECASE)
_HOURS = re.compile(r"^[+-]?\d{1,2}(?:\.\d+)?$")


def invalid_timezone_message(value: str) -> str:
    return (
        f"Invalid birth timezone: {value!r}. "
        "Use an IANA name (e.g. 'Asia/Shanghai'), a UTC offset "
        "(e.g. '+08:00' or 'UTC+8'), or a bare offset in hours "
        "(e.g. '8', '-5', '5.5')."
    )


def parse_timezone_name(timezone_name: str) -> tzinfo:
    """Parse a named zone or a validated UTC offset shared by all engines."""
    return _parse_timezone_name_cached(timezone_name.strip())


@lru_cache(maxsize=128)
def _parse_timezone_name_cached(value: str) -> tzinfo:
    if value.upper() in {"UTC", "GMT", "Z"}:
        return timezone.utc
    match = _OFFSET.fullmatch(value)
    if match:
        sign, hour_text, minute_text = match.groups()
        hours, minutes = int(hour_text), int(minute_text or 0)
        if minutes >= 60 or hours > 15 or (hours == 15 and minutes):
            raise ValueError(invalid_timezone_message(value))
        seconds = (hours * 3600 + minutes * 60) * (-1 if sign == "-" else 1)
        return timezone(timedelta(seconds=seconds))
    if _HOURS.fullmatch(value):
        offset_hours = float(value)
        if abs(offset_hours) <= 15:
            return timezone(timedelta(seconds=round(offset_hours * 3600)))
        raise ValueError(invalid_timezone_message(value))
    # Never let dateutil normalize malformed offsets (e.g. UTC+08:90).
    if value.upper().startswith(("UTC", "GMT", "+", "-")):
        raise ValueError(invalid_timezone_message(value))
    zone = tz.gettz(value)
    if zone is None:
        raise ValueError(invalid_timezone_message(value))
    return cast(tzinfo, zone)
