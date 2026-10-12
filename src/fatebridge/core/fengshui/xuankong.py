"""Versioned Zhongzhou natal charts. No annual overlay or automatic house age."""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple, cast

from fatebridge.utils.timezones import parse_timezone_name

from .calendar import lichun_resolution, year_context
from .directions import rule_data, wrap9
from .models import HousePeriod, XuankongRequest


@lru_cache(maxsize=1)
def _bundle() -> Dict[str, Any]:
    path = Path(__file__).parents[2] / "data" / "fengshui" / "xuankong-v1.json"
    return cast(Dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def natal_rules() -> Dict[str, Any]:
    return deepcopy(_bundle())


def natal_provenance() -> Dict[str, Any]:
    bundle = natal_rules()
    selected = bundle["ruleset"]
    selected["sources"] = [
        dict(source_id=s, **bundle["sources"][s]) for s in selected["source_ids"]
    ]
    selected["bundle_version"] = bundle["bundle_version"]
    return cast(Dict[str, Any], selected)


def period_context(period: HousePeriod) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "basis": period.basis,
        "evidence": period.evidence,
        "qualifies_for_period_reset": period.qualifies_for_period_reset,
        "selection_scope": "caller_selected_historical_event_no_automatic_reset",
        "rule_id": "xuankong_zhongzhou_v1.house_period",
        "source_ids": ["X1", "X2", "X4"],
        "resolution_status": "resolved",
    }
    if period.period_number is not None:
        return {
            **result,
            "number": period.period_number,
            "input_basis": "confirmed_period_number",
            "effective_event_year": None,
            "valid_from": None,
            "valid_until": None,
        }
    time = year_context(
        period.effective_event_year, period.event_at, period.timezone_name
    )
    year = time["effective_year"]
    index = (year - 1864) // 20
    start = 1864 + index * 20
    timing: Dict[str, Any] = {
        "start": lichun_resolution(start, period.timezone_name),
        "end": lichun_resolution(start + 20, period.timezone_name),
        "year_boundary_convention": "explicit_engineering_convention_lichun",
    }
    if period.event_at is not None:
        local_year = period.event_at.astimezone(
            parse_timezone_name(period.timezone_name)
        ).year
        event_boundary = lichun_resolution(local_year, period.timezone_name)
        timing["event_year_boundary"] = event_boundary
        # A failed astronomical resolution in a changeover year cannot certify
        # the side of the boundary. An explicit effective year remains usable.
        if (local_year - 1864) % 20 == 0 and event_boundary["approximate"]:
            new_number = ((local_year - 1864) // 20) % 9 + 1
            return {
                **result,
                "resolution_status": "requires_confirmation",
                "number": None,
                "input_basis": "aware_datetime",
                "event_time_context": time,
                "candidate_period_numbers": [wrap9(new_number - 1), new_number],
                "timing": timing,
                "confirmation_reason": "approximate_lichun_in_period_changeover_year",
                "valid_from": None,
                "valid_until": None,
            }
    return {
        **result,
        "number": index % 9 + 1,
        "input_basis": time["input_basis"],
        "effective_event_year": year,
        "event_time_context": time,
        "start_year": start,
        "end_year": start + 19,
        "valid_from": timing["start"]["moment"],
        "valid_until": timing["end"]["moment"],
        "timing": timing,
        "interval_scope": "historical_event_period_window_not_natal_expiry",
        "year_boundary": "lichun",
        "epoch_year": 1864,
    }


def _fly(center: int, yang: bool = True) -> Dict[str, int]:
    return {
        d: wrap9(center + i * (1 if yang else -1))
        for i, d in enumerate(rule_data("flight_path"))
    }


def _selector(angle: float) -> Tuple[int, str, str]:
    mountains = _bundle()["mountains"]
    index = int(((angle + 7.5) % 360) // 15)
    mountain = mountains[index]
    offset = (angle - mountain["center_degrees"] + 180) % 360 - 180
    if abs(offset) < _bundle()["central_half_width_degrees"]:
        return index, "lower", "central_nine_degrees"
    neighbour = mountains[(index + (1 if offset > 0 else -1)) % 24]
    if (
        mountain["direction"] == neighbour["direction"]
        and mountain["polarity"] == neighbour["polarity"]
    ):
        return index, "lower", "same_palace_same_polarity_no_replacement"
    return index, "replacement", "cross_palace_or_different_polarity"


def _selectors(angle: float, uncertainty: float) -> List[Tuple[int, str, str]]:
    """Partition the *whole* interval; sampling endpoints alone misses small cells.

    At an exact dividing line include both one-sided limits. This is an explicit
    conservative application policy, not a claim that ancient sources specify
    modern floating-point endpoints. Charts are deduplicated by mountain/mode.
    """
    lower, upper = angle - uncertainty, angle + uncertainty
    found: Dict[Tuple[int, str], Tuple[int, str, str]] = {}
    for i in range(-1, 26):
        center = i * 15
        for left, right, midpoint in (
            (-7.5, -4.5, -6),
            (-4.5, 4.5, 0),
            (4.5, 7.5, 6),
        ):
            # Closed-cell intersections include both limits only when the
            # supplied interval actually touches a line. No epsilon expansion.
            if max(lower, center + left) <= min(upper, center + right):
                selector = _selector((center + midpoint) % 360)
                found.setdefault(selector[:2], selector)
    return list(found.values())


def _star_trace(
    seed: int, physical: Dict[str, Any], period: int, mode: str
) -> Dict[str, Any]:
    rules = _bundle()
    home_star = period if seed == 5 else seed
    # In period 5 the forward base is the native Luo Shu chart: five is only
    # central, so no outer sitting/facing seed can be five. No invented fallback.
    assert home_star != 5
    mapped = rules["star_home_mountains"][str(home_star)][physical["yuan"]]
    mapped_mountain = next(m for m in rules["mountains"] if m["name"] == mapped)
    yang = mapped_mountain["polarity"] == "yang"
    center = seed
    if mode == "replacement" and seed != 5:
        center = rules["replacement_stars"].get(mapped, seed)
    return {
        "seed_star_number": seed,
        "home_star_number_for_polarity": home_star,
        "yuan": physical["yuan"],
        "mapped_mountain": mapped,
        "polarity": "yang" if yang else "yin",
        "flight": "forward" if yang else "reverse",
        "center_star_number": center,
        "replacement_applied": center != seed,
        "five_yellow_policy": (
            "borrow_period_same_yuan_keep_five" if seed == 5 else None
        ),
        "rule_id": "xuankong_zhongzhou_v1.same_yuan_then_replacement",
        "source_ids": ["X2", "X3"] if seed == 5 else ["X1", "X2"],
    }


def _chart(period: int, selector: Tuple[int, str, str]) -> Dict[str, Any]:
    index, mode, reason = selector
    mountains = _bundle()["mountains"]
    facing, sitting = mountains[index], mountains[(index + 12) % 24]
    base = _fly(period)
    mountain = _star_trace(base[sitting["direction"]], sitting, period, mode)
    water = _star_trace(base[facing["direction"]], facing, period, mode)
    mountain_chart = _fly(
        mountain["center_star_number"], mountain["polarity"] == "yang"
    )
    facing_chart = _fly(water["center_star_number"], water["polarity"] == "yang")
    palaces = {
        d: {
            "direction": d,
            "palace_number": rule_data("directions").get(d, {"palace_number": 5})[
                "palace_number"
            ],
            "period_star_number": base[d],
            "mountain_star_number": mountain_chart[d],
            "facing_star_number": facing_chart[d],
        }
        for d in base
    }
    return {
        "candidate_id": f"{period}:{sitting['name']}-{facing['name']}:{mode}",
        "period_number": period,
        "facing": deepcopy(facing),
        "sitting": deepcopy(sitting),
        "chart_mode": mode,
        "mode_reason": reason,
        "palaces": palaces,
        "period_chart": base,
        "mountain_chart": mountain_chart,
        "facing_chart": facing_chart,
        "trace": {"mountain": mountain, "facing": water},
        "flight_path": rule_data("flight_path"),
    }


def xuankong_natal(req: XuankongRequest) -> Dict[str, Any]:
    house = req.house
    missing = []
    if house is None or house.facing_degrees is None:
        missing.append("xuankong_natal.house.facing_degrees_magnetic")
    if req.period is None:
        missing.append("xuankong_natal.period")
    period = period_context(req.period) if req.period is not None else None
    if period is not None and period["resolution_status"] != "resolved":
        missing.append("xuankong_natal.period.effective_year_or_period_confirmation")
    result: Dict[str, Any] = {
        "status": "partial",
        "subject_id": house.object_id if house is not None else "house",
        "period_context": period,
        "orientation_context": {
            "facing_degrees": (
                house.facing_degrees % 360
                if house is not None and house.facing_degrees is not None
                else None
            ),
            "north_reference": house.north_reference if house is not None else None,
            "orientation_basis": house.orientation_basis if house is not None else None,
            "uncertainty_degrees": req.bearing_uncertainty_degrees,
            "boundary_policy": "both_one_sided_candidates_at_exact_dividing_lines",
            "confirmed_sitting_trigram": house.sitting_trigram if house else None,
            "candidate_constraint": "respect_confirmed_sitting_trigram",
        },
        "chart": None,
        "candidates": [],
        "missing_inputs": missing,
        "interpretation_scope": "fixed_natal_numbers_no_annual_overlay_or_form_verdict",
        "mountain_registry": natal_rules()["mountains"],
    }
    if missing:
        return result
    assert house is not None and house.facing_degrees is not None and period is not None
    candidates = [
        _chart(period["number"], s)
        for s in _selectors(house.facing_degrees % 360, req.bearing_uncertainty_degrees)
    ]
    if house.sitting_trigram is not None:
        directions = rule_data("directions")
        candidates = [
            c
            for c in candidates
            if directions[c["sitting"]["direction"]]["trigram"] == house.sitting_trigram
        ]
    result["candidates"] = candidates
    if len(candidates) == 1:
        result["status"] = "complete"
        result["chart"] = candidates[0]
    else:
        result["missing_inputs"] = ["xuankong_natal.unambiguous_bearing"]
    return result
