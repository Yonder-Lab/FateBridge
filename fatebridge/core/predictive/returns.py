"""太阳/月亮回归推运法。"""

from __future__ import annotations

from datetime import timezone

from ._common import *

# Search-seed lookback per return type. The governing return is the latest one
# at or before the analysis instant, so we seed the search at least one full
# period earlier and scan forward. Solar returns recur ~yearly, lunar ~27.3d.
_RETURN_SEED_LOOKBACK_DAYS = {"Solar": 367, "Lunar": 31}


def _analysis_julian_day(analysis_datetime: datetime) -> float:
    moment = analysis_datetime.astimezone(timezone.utc)
    return swe.julday(
        moment.year,
        moment.month,
        moment.day,
        moment.hour + moment.minute / 60.0 + moment.second / 3600.0,
    )


def _governing_return(
    factory: Any,
    analysis_datetime: datetime,
    return_type: str,
) -> Any:
    """Return the planetary return that is in effect on ``analysis_datetime``.

    A return chart governs the span from its own moment until the next return,
    so the active chart for a given instant is the *latest return at or before*
    it — not the next upcoming one. ``next_return_from_date`` only finds the
    first return on/after a seed date, so we seed one period early and step
    forward, keeping the last return whose moment does not exceed the analysis
    instant.
    """
    analysis_jd = _analysis_julian_day(analysis_datetime)
    lookback = _RETURN_SEED_LOOKBACK_DAYS[return_type]
    seed = analysis_datetime - timedelta(days=lookback)

    governing = None
    candidate = factory.next_return_from_date(
        seed.year, seed.month, seed.day, return_type=return_type
    )
    # Bounded scan: at most a handful of periods fit in the lookback window.
    for _ in range(40):
        if candidate.julian_day > analysis_jd:
            break
        governing = candidate
        year, month, day, _hour = swe.revjul(candidate.julian_day)
        next_seed = datetime(
            int(year), int(month), int(day), tzinfo=timezone.utc
        ) + timedelta(days=1)
        candidate = factory.next_return_from_date(
            next_seed.year, next_seed.month, next_seed.day, return_type=return_type
        )

    # Fall back to the earliest located return if none precedes the analysis
    # instant (only possible if the chart predates the lookback window).
    return governing if governing is not None else candidate


def _return_section(planet_return: Any) -> Dict[str, Any]:
    return {
        "return_datetime": planet_return.iso_formatted_local_datetime,
        "sun": point_to_dict("Sun", planet_return.sun),
        "moon": point_to_dict("Moon", planet_return.moon),
        "ascendant": point_to_dict("Ascendant", planet_return.ascendant),
        "medium_coeli": point_to_dict("Medium_Coeli", planet_return.medium_coeli),
    }


def build_return_payload(
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    return_longitude: float,
    return_latitude: float,
    return_timezone: str,
    include: Optional[List[str]] = None,
) -> Dict[str, Any]:
    backend_return_timezone = resolve_kerykeion_timezone_name(return_timezone) or "UTC"
    factory = PlanetaryReturnFactory(
        natal_subject,
        lng=return_longitude,
        lat=return_latitude,
        tz_str=backend_return_timezone,
        online=False,
    )
    included = set(include or ["solar_return", "lunar_return"])
    payload: Dict[str, Any] = {}

    if "solar_return" in included:
        solar_return = _governing_return(factory, analysis_datetime, "Solar")
        payload["solar_return"] = _return_section(solar_return)

    if "lunar_return" in included:
        lunar_return = _governing_return(factory, analysis_datetime, "Lunar")
        payload["lunar_return"] = _return_section(lunar_return)

    return payload
