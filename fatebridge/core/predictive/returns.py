"""太阳/月亮回归推运法。"""

from __future__ import annotations

from ._common import *


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
        solar_return = factory.next_return_from_date(
            analysis_datetime.year, 1, 1, return_type="Solar"
        )
        payload["solar_return"] = {
            "return_datetime": solar_return.iso_formatted_local_datetime,
            "sun": point_to_dict("Sun", solar_return.sun),
            "moon": point_to_dict("Moon", solar_return.moon),
            "ascendant": point_to_dict("Ascendant", solar_return.ascendant),
            "medium_coeli": point_to_dict(
                "Medium_Coeli",
                solar_return.medium_coeli,
            ),
        }

    if "lunar_return" in included:
        lunar_return = factory.next_return_from_date(
            analysis_datetime.year,
            analysis_datetime.month,
            1,
            return_type="Lunar",
        )
        payload["lunar_return"] = {
            "return_datetime": lunar_return.iso_formatted_local_datetime,
            "sun": point_to_dict("Sun", lunar_return.sun),
            "moon": point_to_dict("Moon", lunar_return.moon),
            "ascendant": point_to_dict("Ascendant", lunar_return.ascendant),
            "medium_coeli": point_to_dict(
                "Medium_Coeli",
                lunar_return.medium_coeli,
            ),
        }

    return payload
