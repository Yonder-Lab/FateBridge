"""Sitting-trigram house chart and separately scoped personal charts."""

from typing import Any, Dict, List

from fatebridge.core.divination import BAGUA_BY_NAME

from .calendar import year_context
from .directions import rule_data, sitting_from_facing, wrap9
from .models import BazhaiRequest, MingguaRequest


def sectors(base: str, subject_id: str, basis: str) -> Dict[str, Any]:
    bits = {
        name: sum(bit << i for i, bit in enumerate(info["lines"]))
        for name, info in BAGUA_BY_NAME.items()
    }
    stars = rule_data("bazhai_stars")
    return {
        direction: {
            **info,
            "star": stars[str(bits[base] ^ bits[info["trigram"]])],
            "changed_line_mask": bits[base] ^ bits[info["trigram"]],
            "base_trigram": base,
            "subject_id": subject_id,
            "basis": basis,
            "method": "bazhai",
            "rule_id": "bazhai_sitting_v1.dayounian_xor",
            "source_ids": ["S3"],
        }
        for direction, info in rule_data("directions").items()
    }


def minggua(req: MingguaRequest, subject_id: str = "occupant") -> Dict[str, Any]:
    time = year_context(
        req.effective_birth_year,
        req.birth_at,
        req.timezone_name,
        req.year_boundary,
        resolve_interval=req.birth_at is not None,
    )
    year = time["effective_year"]
    missing = []
    if year is None:
        missing.append(f"occupants.{subject_id}.birth_at_or_effective_birth_year")
    if req.gender_convention is None:
        missing.append(f"occupants.{subject_id}.gender_convention")
    candidates: List[Dict[str, Any]] = []
    if year is not None:
        for convention in (
            [req.gender_convention] if req.gender_convention else ["male", "female"]
        ):
            raw = wrap9(
                1 - (year - 1864) if convention == "male" else 5 + (year - 1864)
            )
            number = (2 if convention == "male" else 8) if raw == 5 else raw
            trigram = next(
                i["trigram"]
                for i in rule_data("directions").values()
                if i["palace_number"] == number
            )
            candidates.append(
                {
                    "gender_convention": convention,
                    "raw_number": raw,
                    "palace_number": number,
                    "substitution": raw == 5,
                    "trigram": trigram,
                    "group": "east" if number in {1, 3, 4, 9} else "west",
                    "sectors": sectors(trigram, subject_id, "personal_minggua"),
                    "rule_id": "bazhai_sitting_v1.minggua_1864",
                    "source_ids": ["S2", "S4"],
                    "trace": {
                        "epoch_year": 1864,
                        "elapsed_years": year - 1864,
                        "raw_five_mapped_after_cycle": True,
                    },
                }
            )
    return {
        "status": "partial" if missing else "complete",
        "subject_id": subject_id,
        "time_context": time,
        "candidates": candidates,
        "missing_inputs": missing,
    }


def bazhai(req: BazhaiRequest) -> Dict[str, Any]:
    house = None
    missing: List[str] = []
    if req.house is not None:
        data = req.house.model_dump()
        sitting = data["sitting_trigram"]
        if data["facing_degrees"] is not None:
            bearing = sitting_from_facing(
                data["facing_degrees"], data["north_reference"]
            )
            if sitting is not None and sitting != bearing["trigram"]:
                raise ValueError("宅向推导的坐山与 sitting_trigram 不一致")
            sitting = bearing["trigram"]
            data["sitting_bearing"] = bearing
            data["facing_degrees"] %= 360
        if sitting is not None:
            house = {
                **data,
                "sitting_trigram": sitting,
                "sectors": sectors(sitting, data["object_id"], "house_sitting_trigram"),
            }
    if house is None:
        missing.append("house.sitting_trigram_or_confirmed_facing")
    occupants = [minggua(o, o.subject_id) for o in req.occupants]
    for o in occupants:
        missing.extend(o["missing_inputs"])
    if not occupants:
        missing.append("occupants")
    findings = []
    for placement in req.placements:
        bases = []
        if house is not None:
            bases.append((house["object_id"], "house", house["sectors"], None))
        for o in occupants:
            if placement.subject_id is None or placement.subject_id == o["subject_id"]:
                for c in o["candidates"]:
                    bases.append(
                        (
                            o["subject_id"],
                            "occupant",
                            c["sectors"],
                            c["gender_convention"],
                        )
                    )
        for subject_id, basis, chart, convention in bases:
            for aspect, direction in [
                ("location", placement.location_direction),
                ("facing", placement.facing_direction),
            ]:
                if direction is None:
                    continue
                expects = (
                    "inauspicious"
                    if placement.purpose == "stove" and aspect == "location"
                    else "auspicious"
                )
                entry = chart[direction]
                findings.append(
                    {
                        "method": "bazhai",
                        "subject_id": subject_id,
                        "subject_kind": basis,
                        "gender_convention": convention,
                        "object_id": placement.object_id,
                        "purpose": placement.purpose,
                        "aspect": aspect,
                        "facing_role": (
                            placement.facing_role if aspect == "facing" else None
                        ),
                        "direction": direction,
                        "star": entry["star"],
                        "expected_polarity": expects,
                        "matches_convention": entry["star"]["polarity"] == expects,
                        "observation_basis": placement.observation_basis,
                        "rule_id": (
                            "bazhai_sitting_v1.stove_seat_fire_mouth"
                            if placement.purpose == "stove"
                            else "bazhai_sitting_v1.placement_application"
                        ),
                        "source_ids": ["S3"],
                        "application_scope": "selected_ruleset_convention",
                        "candidate_only": (
                            any(
                                o["subject_id"] == subject_id
                                and o["status"] == "partial"
                                for o in occupants
                            )
                            if basis == "occupant"
                            else False
                        ),
                    }
                )
    if req.placements and house is None and not any(o["candidates"] for o in occupants):
        missing.append("placements.usable_house_or_personal_chart")
    return {
        "status": "partial" if missing else "complete",
        "house": house,
        "occupants": occupants,
        "placement_findings": findings,
        "missing_inputs": missing,
    }
