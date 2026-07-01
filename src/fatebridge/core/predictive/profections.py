"""岁运（年主星）推运法（Annual Profections）。"""

from __future__ import annotations

from ._common import *


def monthly_profection_segment(
    year_start: datetime, year_end: datetime, month_offset: int
) -> tuple[datetime, datetime]:
    """Return the [start, end) of the ``month_offset``-th equal twelfth.

    The profected year is divided into 12 equal parts (~30.44 days), not into
    calendar months. The final segment ends exactly on ``year_end`` to absorb
    any float drift.
    """
    span = (year_end - year_start) / 12
    start = year_start + span * month_offset
    end = year_start + span * (month_offset + 1) if month_offset < 11 else year_end
    return start, end


def monthly_profection_index(
    year_start: datetime, year_end: datetime, moment: datetime
) -> int:
    """Index (0–11) of the equal-twelfth segment that contains ``moment``."""
    span = (year_end - year_start).total_seconds() / 12.0
    elapsed = (moment - year_start).total_seconds()
    return max(0, min(11, int(elapsed // span)))


def build_annual_profection_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
) -> Dict[str, Any]:
    age_years_int = calculate_age_years_int(birth_info, analysis_datetime)
    asc_sign = normalize_sign_name(natal_subject.ascendant.sign)
    asc_index = SIGNS.index(asc_sign)
    activated_house = (age_years_int % 12) + 1
    activated_sign = SIGNS[(asc_index + activated_house - 1) % 12]
    lord = RULER_BY_SIGN[activated_sign]

    birthday_this_year = resolve_local_birthday_anniversary(
        birth_info.local_datetime,
        analysis_datetime.year,
        tzinfo=analysis_datetime.tzinfo,
    )
    if analysis_datetime < birthday_this_year:
        last_birthday = resolve_local_birthday_anniversary(
            birth_info.local_datetime,
            analysis_datetime.year - 1,
            tzinfo=analysis_datetime.tzinfo,
        )
    else:
        last_birthday = birthday_this_year

    next_birthday = add_months(last_birthday, 12)
    months_since_birthday = monthly_profection_index(
        last_birthday, next_birthday, analysis_datetime
    )
    monthly_house = ((activated_house - 1 + months_since_birthday) % 12) + 1
    monthly_sign = SIGNS[(asc_index + monthly_house - 1) % 12]

    return {
        "activated_house": activated_house,
        "activated_sign": activated_sign,
        "activated_sign_label": sign_label(activated_sign),
        "lord": lord,
        "lord_label": planet_label(lord),
        "monthly_house": monthly_house,
        "monthly_sign": monthly_sign,
        "monthly_sign_label": sign_label(monthly_sign),
    }


def resolve_last_birthday(
    birth_info: AstroBirthInfo,
    *,
    analysis_datetime: datetime,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    analysis_local = rebuild_local_datetime(analysis_datetime, timezone_name)
    birthday_this_year = resolve_local_birthday_anniversary(
        birth_info.local_datetime,
        analysis_local.year,
        tzinfo=analysis_local.tzinfo,
    )
    if analysis_local < birthday_this_year:
        last_birthday = resolve_local_birthday_anniversary(
            birth_info.local_datetime,
            analysis_local.year - 1,
            tzinfo=analysis_local.tzinfo,
        )
    else:
        last_birthday = birthday_this_year
    return analysis_local, last_birthday


def build_monthly_profections_payload(
    *,
    annual_house: int,
    asc_sign: str,
    year_start: datetime,
    analysis_datetime: datetime,
) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    asc_index = SIGNS.index(asc_sign)
    year_end = add_months(year_start, 12)
    for month_offset in range(12):
        start, end = monthly_profection_segment(year_start, year_end, month_offset)
        house = ((annual_house - 1 + month_offset) % 12) + 1
        sign_name = SIGNS[(asc_index + house - 1) % 12]
        ruler = RULER_BY_SIGN[sign_name]
        timeline.append(
            {
                "month_index": month_offset + 1,
                "house": house,
                "house_label": f"第{house}宫",
                "sign": sign_name,
                "sign_label": sign_label(sign_name),
                "lord": ruler,
                "lord_label": planet_label(ruler),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "active": start <= analysis_datetime < end,
            }
        )
    return timeline


def build_given_year_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
    annual_profection: Dict[str, Any],
    return_longitude: float,
    return_latitude: float,
    return_timezone: str,
    house_system: str = "P",
    zodiac_type: str = "Tropic",
) -> Dict[str, Any]:
    analysis_local, last_birthday = resolve_last_birthday(
        birth_info,
        analysis_datetime=analysis_datetime,
        timezone_name=return_timezone,
    )
    year_end = add_months(last_birthday, 12)
    given_year_subject = build_subject(
        name=f"{birth_info.name}-given-year",
        local_datetime=analysis_local,
        longitude=return_longitude,
        latitude=return_latitude,
        timezone_name=return_timezone,
        house_system=house_system,
        zodiac_type=zodiac_type,
    )
    monthly_profections = build_monthly_profections_payload(
        annual_house=annual_profection["activated_house"],
        asc_sign=normalize_sign_name(natal_subject.ascendant.sign),
        year_start=last_birthday,
        analysis_datetime=analysis_local,
    )
    hits = collect_aspect_hits(
        source_longitudes=extract_reference_longitudes(given_year_subject),
        target_longitudes=extract_reference_longitudes(natal_subject),
        orb_limit=1.5,
    )
    return {
        "analysis_datetime": analysis_local.isoformat(),
        "year_start": last_birthday.isoformat(),
        "year_end": year_end.isoformat(),
        "sun": point_to_dict("Sun", given_year_subject.sun),
        "moon": point_to_dict("Moon", given_year_subject.moon),
        "ascendant": point_to_dict("Ascendant", given_year_subject.ascendant),
        "medium_coeli": point_to_dict(
            "Medium_Coeli",
            given_year_subject.medium_coeli,
        ),
        "annual_profection": annual_profection,
        "monthly_profections": monthly_profections,
        "hits": hits[:8],
        "location": {
            "longitude": return_longitude,
            "latitude": return_latitude,
            "timezone": return_timezone,
        },
    }
