"""太阳弧度推运法（Solar Arc Directions）。"""

from __future__ import annotations

from ._common import *


def build_solar_arc_payload(
    natal_subject: Any,
    progressed_subject: Any,
) -> Dict[str, Any]:
    natal_longitudes = extract_reference_longitudes(natal_subject)
    arc_degrees = (
        point_absolute_position(progressed_subject, "Sun")
        - point_absolute_position(natal_subject, "Sun")
    ) % 360.0
    directed_points = {}
    for point_name, longitude in natal_longitudes.items():
        directed_points[point_name] = (longitude + arc_degrees) % 360.0
    hits = collect_aspect_hits(
        source_longitudes=directed_points,
        target_longitudes=natal_longitudes,
        orb_limit=1.5,
    )
    return {
        "arc_degrees": round(arc_degrees, 4),
        "sun": longitude_to_point_dict("Sun", directed_points["Sun"]),
        "moon": longitude_to_point_dict("Moon", directed_points["Moon"]),
        "ascendant": longitude_to_point_dict(
            "Ascendant",
            directed_points["Ascendant"],
        ),
        "medium_coeli": longitude_to_point_dict(
            "Medium_Coeli",
            directed_points["Medium_Coeli"],
        ),
        "hits": hits[:8],
    }
