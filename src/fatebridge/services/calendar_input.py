"""Calendar query parsing, coordinate coercion and input conventions."""

import re
from datetime import datetime
from typing import Any, Optional

GEO_COORDINATE_RE = re.compile(
    r"^\s*(?P<degrees>-?\d+(?:\.\d+)?)(?:(?P<direction>[NSEWnsew])(?P<minutes>\d+(?:\.\d+)?))?\s*$"
)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def _parse_calendar_datetime(date_text: str, time_text: str) -> datetime:
    normalized_date = (date_text or "").strip().replace("/", "-")
    normalized_time = (time_text or "").strip()
    if not normalized_date or not normalized_time:
        raise ValueError("date 和 time 不能为空。")

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(
                f"{normalized_date} {normalized_time}",
                fmt,
            )
        except ValueError:
            continue

    raise ValueError("无法解析 date/time，请使用 YYYY-MM-DD 与 HH:MM[:SS]。")


def _normalize_time_alg(value: Any) -> int:
    return 1 if value == 1 else 0


def _parse_geo_coordinate(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = GEO_COORDINATE_RE.match(str(value))
    if not match:
        return None

    degrees = float(match.group("degrees"))
    direction = (match.group("direction") or "").upper()
    minutes = float(match.group("minutes") or "0")

    if direction:
        decimal = abs(degrees) + minutes / 60.0
        if direction in {"S", "W"}:
            decimal *= -1
        return decimal

    return degrees
