"""菲尔达利亚时主（Firdaria）推运法。"""

from __future__ import annotations

from ._common import *

# 日盘与夜盘的行星时主顺序（planet, years）
FIRDARIA_DAY_SEQUENCE = [
    ("Sun", 10),
    ("Venus", 8),
    ("Mercury", 13),
    ("Moon", 9),
    ("Saturn", 11),
    ("Jupiter", 12),
    ("Mars", 7),
    ("North Node", 3),
    ("South Node", 2),
]
FIRDARIA_NIGHT_SEQUENCE = [
    ("Moon", 9),
    ("Saturn", 11),
    ("Jupiter", 12),
    ("Mars", 7),
    ("Sun", 10),
    ("Venus", 8),
    ("Mercury", 13),
    ("North Node", 3),
    ("South Node", 2),
]


def build_firdaria_payload(
    birth_info: AstroBirthInfo,
    natal_subject: Any,
    *,
    analysis_datetime: datetime,
) -> Dict[str, Any]:
    sect = determine_sect(natal_subject)
    sequence = FIRDARIA_DAY_SEQUENCE if sect == "day" else FIRDARIA_NIGHT_SEQUENCE
    sub_planet_order = [planet for planet, _ in sequence if "Node" not in planet]

    timeline = []
    cursor = birth_info.local_datetime
    current_major = None
    current_sub = None

    while cursor <= analysis_datetime + timedelta(days=90 * TROPICAL_YEAR_DAYS):
        for planet, years in sequence:
            start = cursor
            end = start + timedelta(days=years * TROPICAL_YEAR_DAYS)
            main_period: Dict[str, Any] = {
                "planet": planet,
                "planet_label": planet_label(planet),
                "start": start.isoformat(),
                "end": end.isoformat(),
                "years": years,
                "subperiods": [],
            }

            if "Node" not in planet:
                order = (
                    sub_planet_order[sub_planet_order.index(planet) :]
                    + sub_planet_order[: sub_planet_order.index(planet)]
                )
                sub_years = years / 7.0
                sub_cursor = start
                for sub_planet in order:
                    sub_end = sub_cursor + timedelta(
                        days=sub_years * TROPICAL_YEAR_DAYS
                    )
                    sub_period = {
                        "planet": sub_planet,
                        "planet_label": planet_label(sub_planet),
                        "start": sub_cursor.isoformat(),
                        "end": sub_end.isoformat(),
                    }
                    main_period["subperiods"].append(sub_period)
                    if sub_cursor <= analysis_datetime < sub_end:
                        current_sub = sub_period
                    sub_cursor = sub_end

            if start <= analysis_datetime < end:
                current_major = main_period

            timeline.append(main_period)
            cursor = end
            if cursor > analysis_datetime + timedelta(days=90 * TROPICAL_YEAR_DAYS):
                break
        else:
            continue
        break

    return {
        "sect": sect,
        "sect_label": sect_label(sect),
        "current_major": current_major,
        "current_sub": current_sub,
        "timeline": timeline[:12],
    }
