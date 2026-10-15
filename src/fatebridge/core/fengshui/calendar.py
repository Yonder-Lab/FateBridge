"""Civil time and explicitly selected year boundaries, independent of BaZi."""

from datetime import datetime
from typing import Any, Dict, Optional

from fatebridge.core import almanac
from fatebridge.utils.timezones import parse_timezone_name


def lichun(year: int, timezone_name: str) -> datetime:
    return next(
        t.moment
        for t in almanac.get_solar_terms_for_year(year, timezone_name)
        if t.name == "立春"
    )


def lichun_resolution(year: int, timezone_name: str) -> Dict[str, Any]:
    """Report the actual per-term provider, not just Swiss import availability."""
    term = next(
        t
        for t in almanac.get_solar_terms_for_year(year, timezone_name)
        if t.name == "立春"
    )
    return {
        "moment": term.moment.isoformat(),
        "provider": term.resolution_provider,
        "approximate": term.resolution_provider != "swisseph",
        "precision_scope": "engine_computed_not_independently_certified_to_seconds",
    }


def year_context(
    effective_year: Optional[int],
    moment: Optional[datetime],
    timezone_name: str,
    boundary: str = "lichun",
    *,
    resolve_interval: bool = True,
) -> Dict[str, Any]:
    tz = parse_timezone_name(timezone_name)
    local = moment.astimezone(tz) if moment is not None else None
    if effective_year is None and local is None:
        return {
            "effective_year": None,
            "year_boundary": boundary,
            "timezone_name": timezone_name,
        }
    year = effective_year
    uncertain_boundary = None
    if year is None and local is not None:
        year = (
            almanac.get_bazi_year(local, timezone_name)
            if boundary == "lichun"
            else local.year
        )
        if boundary == "lichun":
            resolution = lichun_resolution(local.year, timezone_name)
            boundary_date = datetime.fromisoformat(resolution["moment"]).date()
            # Same conservative adjacent-civil-date policy as date-only
            # Minggua; this is solver uncertainty, not a Feng Shui rule.
            if (
                resolution["approximate"]
                and abs((local.date() - boundary_date).days) <= 1
            ):
                uncertain_boundary = resolution
    assert year is not None
    if not resolve_interval:
        return {
            "effective_year": year,
            "year_boundary": boundary,
            "input_basis": "effective_year_override",
            "timezone_name": timezone_name,
            "valid_from": None,
            "valid_until": None,
            "interval_scope": "not_needed_for_confirmed_effective_birth_year",
        }
    if boundary == "lichun":
        start, end = lichun(year, timezone_name), lichun(year + 1, timezone_name)
        # The shared runtime currently exposes Swiss availability, not the
        # per-term fallback path. Do not certify exact-second precision here.
        timing = {
            "provider": "fatebridge.core.almanac.get_solar_terms_for_year",
            "runtime_swiss_available": almanac.swe is not None,
            "possible_linear_fallback": True,
            "independent_precision_verification": "2026_date_and_minute_only",
            "source_ids": ["S7", "S8"],
        }
    else:
        start, end = datetime(year, 1, 1, tzinfo=tz), datetime(
            year + 1, 1, 1, tzinfo=tz
        )
        timing = {"provider": "civil_calendar", "convention": "explicit_january_1"}
    result = {
        "effective_year": year,
        "year_boundary": boundary,
        "input_basis": (
            "effective_year_override"
            if effective_year is not None
            else "aware_datetime"
        ),
        "local_moment": local.isoformat() if local is not None else None,
        "timezone_name": timezone_name,
        "valid_from": start.isoformat(),
        "valid_until": end.isoformat(),
        "interval_policy": "start_inclusive_end_exclusive",
        "timing": timing,
    }
    if uncertain_boundary is not None:
        assert local is not None
        result.update(
            effective_year_status="requires_confirmation",
            candidate_effective_years=[local.year - 1, local.year],
            boundary_resolution=uncertain_boundary,
        )
    return result
