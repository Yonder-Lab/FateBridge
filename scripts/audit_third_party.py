"""Reproducible, optional third-party correctness audit (no runtime changes).

Install lunar-python==1.4.8, skyfield==1.55 and sxtwl==2.0.7 in
an isolated location. Install iztro==2.5.8 with npm in another isolated folder.
Run with the project interpreter, PYTHONPATH pointing at the oracle packages:
  python scripts/audit_third_party.py --out /path/to/results \
    --iztro /path/to/node_modules/iztro --ephemeris /path/to/de440s.bsp
Synthetic inputs only. Results record differences; no baselines are rewritten.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import random
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from lunar_python import Solar

from fatebridge.core.almanac import get_lunar_context, get_solar_terms_for_year
from fatebridge.core.astrology import build_astro_birth_info, build_core_chart_payload
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.metaphysics import build_ziwei_chart, build_ziwei_horoscope
from fatebridge.core.timing import TimingAnalysis
from fatebridge.services.metaphysics import _build_analysis_seed


def save(out, name, value):
    (out / (name + ".json")).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
    )
    print(
        name,
        json.dumps(value.get("summary", {}), ensure_ascii=False, default=str),
        flush=True,
    )


def ref_pillars(dt):
    e = (
        Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)
        .getLunar()
        .getEightChar()
    )
    e.setSect(1)  # Same explicit convention: change day pillar at 23:00.
    return e, dict(
        zip(
            ("year", "month", "day", "hour"),
            (e.getYear(), e.getMonth(), e.getDay(), e.getTime()),
        )
    )


def calendar_audit(out):
    rng = random.Random(20261009)
    samples = [
        datetime(1900, 1, 31)
        + timedelta(
            days=rng.randrange(73057),
            hours=rng.randrange(24),
            minutes=rng.randrange(60),
        )
        for _ in range(1600)
    ]
    for y in (1901, 1936, 1972, 1984, 1990, 2000, 2023, 2024, 2026, 2033, 2099):
        for m, d in ((1, 1), (2, 3), (2, 4), (2, 5), (2, 10), (12, 31)):
            samples.extend(datetime(y, m, d, h, 30) for h in (0, 1, 12, 22, 23))
    diffs, lunar_diffs, term_rows, dayun_diffs = [], [], [], []
    for dt in samples:
        e, ref = ref_pillars(dt)
        ours = {
            k: "".join(v)
            for k, v in BaZiCalendar.get_four_pillars(dt, "+08:00").items()
        }
        if ours != ref:
            diffs.append({"datetime": str(dt), "ours": ours, "reference": ref})
        lunar = Solar.fromYmdHms(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, 0
        ).getLunar()
        r = (
            lunar.getYear(),
            abs(lunar.getMonth()),
            lunar.getDay(),
            lunar.getMonth() < 0,
        )
        o = get_lunar_context(dt, timezone_name="+08:00")
        got = (o["year"], o["month"], o["day"], o["is_leap_month"]) if o else None
        if r != got:
            lunar_diffs.append({"datetime": str(dt), "ours": got, "reference": r})
    for y in (1901, 1936, 1972, 1984, 1990, 2000, 2023, 2024, 2026, 2033, 2099):
        table = Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable()
        for t in get_solar_terms_for_year(y, "+08:00"):
            # The lunar-python table includes the preceding winter solstice
            # as 冬至 and the current year's crossing as DONG_ZHI.
            reference_key = "DONG_ZHI" if t.name == "冬至" else t.name
            r = datetime.strptime(table[reference_key].toYmdHms(), "%Y-%m-%d %H:%M:%S")
            delta = (t.moment.replace(tzinfo=None) - r).total_seconds()
            term_rows.append(
                {
                    "year": y,
                    "term": t.name,
                    "ours": str(t.moment),
                    "reference": str(r),
                    "delta_seconds": delta,
                }
            )
            # Minute-scale near-boundary tests, independently anchored.
            for offset in (-120, 120):
                dt = r + timedelta(seconds=offset)
                _, ref = ref_pillars(dt)
                ours = {
                    k: "".join(v)
                    for k, v in BaZiCalendar.get_four_pillars(dt, "+08:00").items()
                }
                if ours != ref:
                    diffs.append(
                        {
                            "datetime": str(dt),
                            "term": t.name,
                            "ours": ours,
                            "reference": ref,
                        }
                    )
    for dt in samples[:100]:
        e, _ = ref_pillars(dt)
        for gender in ("男", "女"):
            got = TimingAnalysis.calculate_dayun_start_details(dt, gender, "+08:00")
            yun = e.getYun(1 if gender == "男" else 0, 2)
            age = (
                yun.getStartYear()
                + yun.getStartMonth() / 12
                + yun.getStartDay() / 360
                + yun.getStartHour() / 8640
            )
            if (
                yun.isForward() != got["forward_direction"]
                or abs(age - got["start_age_precise"]) > 0.02
            ):
                dayun_diffs.append(
                    {
                        "datetime": str(dt),
                        "gender": gender,
                        "ours": got,
                        "reference_age": age,
                        "reference_forward": yun.isForward(),
                    }
                )
    save(
        out,
        "calendar",
        {
            "summary": {
                "ordinary_samples": len(samples),
                "term_boundary_samples": len(term_rows) * 2,
                "four_pillar_differences": len(diffs),
                "lunar_differences": len(lunar_diffs),
                "solar_terms": len(term_rows),
                "max_term_delta_seconds": max(
                    abs(x["delta_seconds"]) for x in term_rows
                ),
                "dayun_samples": 200,
                "dayun_differences": len(dayun_diffs),
            },
            "pillars": diffs,
            "lunar": lunar_diffs,
            "solar_terms": term_rows,
            "dayun": dayun_diffs,
        },
    )


def lunar_exhaustive_audit(out):
    import sxtwl

    from fatebridge.core.almanac import _lunar_date_from_solar

    start, end = date(1900, 1, 31), date(2100, 2, 8)
    dt, rows, count = start, [], 0
    while dt <= end:
        s = sxtwl.fromSolar(dt.year, dt.month, dt.day)
        ref = [s.getLunarYear(), s.getLunarMonth(), s.getLunarDay(), s.isLunarLeap()]
        lunar = _lunar_date_from_solar(dt)
        ours = [lunar.year, lunar.month, lunar.day, lunar.isLeapMonth]
        if ours != ref:
            rows.append({"date": str(dt), "ours": ours, "reference": ref})
        count += 1
        dt += timedelta(days=1)
    save(
        out,
        "lunar_exhaustive",
        {
            "summary": {
                "days": count,
                "differences": len(rows),
                "year_counts": Counter(r["date"][:4] for r in rows),
            },
            "oracle": "sxtwl 2.0.7 (GitHub source build)",
            "dates": rows,
        },
    )


IZTRO_SCRIPT = r"""
const fs=require('fs'); const {astro}=require(process.argv[1]);
astro.config(JSON.parse(process.argv[2]));
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
const result=cases.map(c=>{
 const chart=astro.bySolar(c.date,c.index,c.gender,true,'zh-CN');
 const h=chart.horoscope(c.target,c.target_index);
 return {ming:chart.earthlyBranchOfSoulPalace,shen:chart.earthlyBranchOfBodyPalace,ju:chart.fiveElementsClass,
 palaces:chart.palaces.map(p=>({branch:p.earthlyBranch,ganzhi:p.heavenlyStem+p.earthlyBranch,name:p.name,decadal:p.decadal.range,stars:[...p.majorStars,...p.minorStars,...p.adjectiveStars].map(s=>({name:s.name,brightness:s.brightness||null,mutagen:s.mutagen||null}))})),
 horoscope:Object.fromEntries(['decadal','age','yearly','monthly','daily','hourly'].map(k=>[k,{branch:chart.palaces[h[k].index]?.earthlyBranch,calendarBranch:h[k].earthlyBranch,index:h[k].index,mutagen:h[k].mutagen,nominalAge:h[k].nominalAge}]))};
});process.stdout.write(JSON.stringify(result));
"""


def ziwei_audit(out, iztro, day_divide="forward"):
    rng = random.Random(43109)
    dates = [
        "1990-5-15",
        "2002-2-8",
        "1995-2-3",
        "1974-2-4",
        "1985-2-15",
        "2023-3-25",
        "2023-4-10",
        "2033-12-23",
        "2000-2-29",
        "2024-2-9",
    ]
    dates.extend(
        (datetime(1940, 1, 1) + timedelta(days=rng.randrange(31000))).strftime(
            "%Y-%m-%d"
        )
        for _ in range(30)
    )
    cases = []
    for date in dates:
        for index in (0, 1, 5, 11, 12):
            for gender in ("男", "女"):
                target = ("2026-1-15", "2026-2-5", "2026-2-18", "2026-10-9")[
                    len(cases) % 4
                ]
                if int(date.split("-")[0]) > 2026:
                    target = target.replace("2026", "2040", 1)
                cases.append(
                    {
                        "date": date,
                        "index": index,
                        "gender": gender,
                        "target": target,
                        "target_index": index,
                    }
                )
    config = {
        "yearDivide": "normal",
        "horoscopeDivide": "normal",
        "ageDivide": "normal",
        "dayDivide": day_divide,
        "algorithm": "default",
    }
    refs = json.loads(
        subprocess.check_output(
            ["node", "-e", IZTRO_SCRIPT, str(iztro), json.dumps(config)],
            input=json.dumps(cases).encode(),
        )
    )
    rows, counts, checked = [], Counter(), Counter()
    hour = {0: 0, 1: 2, 5: 10, 11: 22, 12: 23}
    scopes = dict(
        zip(
            ("大限", "小限", "流年", "流月", "流日", "流时"),
            ("decadal", "age", "yearly", "monthly", "daily", "hourly"),
        )
    )
    for case, ref in zip(cases, refs):
        y, m, d = map(int, case["date"].split("-"))
        seed = _build_analysis_seed(
            analysis_year=y,
            analysis_month=m,
            analysis_day=d,
            analysis_hour=hour[case["index"]],
        )
        ours = build_ziwei_chart(seed, case["gender"])
        differences = []

        def compare(kind, got, want, detail=""):
            checked[kind] += 1
            if got != want:
                counts[kind] += 1
                differences.append(
                    {"field": kind, "detail": detail, "ours": got, "reference": want}
                )

        for key, value in (
            ("ming", ours["ming_gong"]["branch"]),
            ("shen", ours["shen_gong"]["branch"]),
            ("ju", ours["wuxing_ju"]["label"]),
        ):
            compare(key, value, ref[key])
        for p in ours["palaces"]:
            rp = next(x for x in ref["palaces"] if x["branch"] == p["ganzhi"][1])
            compare(
                "palace_name",
                p["name"].removesuffix("宫"),
                rp["name"].removesuffix("宫"),
                rp["branch"],
            )
            compare("palace_stem", p["ganzhi"], rp["ganzhi"], rp["branch"])
            compare(
                "decadal_range",
                list(map(int, p["daxian"].split("~"))),
                rp["decadal"],
                rp["branch"],
            )
        ours_stars = {
            s["name"]: (p["ganzhi"][1], s["brightness"], s["mutagen"])
            for p in ours["palaces"]
            for s in p["stars_detail"]
        }
        ref_stars = {
            s["name"]: (
                p["branch"],
                s["brightness"],
                ("化" + s["mutagen"]) if s["mutagen"] else None,
            )
            for p in ref["palaces"]
            for s in p["stars"]
        }
        for star in sorted(ours_stars.keys() & ref_stars.keys()):
            compare("star_position", ours_stars[star][0], ref_stars[star][0], star)
            compare("brightness", ours_stars[star][1], ref_stars[star][1], star)
            compare("mutagen", ours_stars[star][2], ref_stars[star][2], star)
        ty, tm, td = map(int, case["target"].split("-"))
        target = _build_analysis_seed(
            analysis_year=ty,
            analysis_month=tm,
            analysis_day=td,
            analysis_hour=hour[case["target_index"]],
        )
        h = build_ziwei_horoscope(
            chart=ours,
            gender=case["gender"],
            target_seed=target,
        )
        compare("nominal_age", h["nominal_age"], ref["horoscope"]["age"]["nominalAge"])
        for s in h["scopes"]:
            r = ref["horoscope"][scopes[s["scope"]]]
            compare(
                "horoscope_" + s["scope"],
                (s["branch"], list(s["mutagen"].values())),
                (r["branch"], r["mutagen"]),
            )
        if differences:
            rows.append({"input": case, "differences": differences})
    natal_rows = [
        r
        for r in rows
        if any(
            not d["field"].startswith("horoscope_") and d["field"] != "nominal_age"
            for d in r["differences"]
        )
    ]
    value = {
        "summary": {
            "charts": len(cases),
            "charts_with_differences": len(rows),
            "natal_charts_with_differences": len(natal_rows),
            "natal_differences_outside_late_zi": sum(
                r["input"]["index"] != 12 for r in natal_rows
            ),
            "checked_fields": checked,
            "different_fields": counts,
            "horoscope_palace_difference_counts": Counter(
                d["field"]
                for row in rows
                for d in row["differences"]
                if d["field"].startswith("horoscope_")
                and d["ours"][0] != d["reference"][0]
            ),
            "horoscope_mutagen_difference_counts": Counter(
                d["field"]
                for row in rows
                for d in row["differences"]
                if d["field"].startswith("horoscope_")
                and d["ours"][1] != d["reference"][1]
            ),
        },
        "reference_config": config,
        "differences": rows,
    }
    if day_divide == "forward":
        value["reference_results"] = [
            {"input": c, "output": r} for c, r in zip(cases, refs)
        ]
        first = value["reference_results"][0]["output"]
        value["reference_star_inventory"] = sorted(
            {s["name"] for p in first["palaces"] for s in p["stars"]}
        )
        value["omitted_reference_stars"] = ["天空", "截路", "空亡"]
    save(
        out,
        "ziwei" if day_divide == "forward" else "ziwei_current_day_diagnostic",
        value,
    )


def skyfield_audit(out, ephemeris):
    from skyfield.api import load, load_file
    from skyfield.framelib import ecliptic_frame

    from fatebridge.core.ephemeris_runtime import ephemeris_call, swe

    eph = load_file(str(ephemeris))
    ts = load.timescale(builtin=True)
    earth = eph["earth"]
    names = {
        "Sun": "sun",
        "Moon": "moon",
        "Mercury": "mercury",
        "Venus": "venus",
        "Mars": "mars barycenter",
        "Jupiter": "jupiter barycenter",
        "Saturn": "saturn barycenter",
        "Uranus": "uranus barycenter",
        "Neptune": "neptune barycenter",
        "Pluto": "pluto barycenter",
    }
    rng = random.Random(61009)
    samples = [
        datetime(1901, 1, 1, tzinfo=timezone.utc)
        + timedelta(
            days=rng.randrange(72000),
            hours=rng.randrange(24),
            minutes=rng.randrange(60),
        )
        for _ in range(80)
    ]
    rows = []
    for dt in samples:
        b = build_astro_birth_info(
            birth_year=dt.year,
            birth_month=dt.month,
            birth_day=dt.day,
            birth_hour=dt.hour,
            birth_minute=dt.minute,
            birth_timezone="UTC",
            birth_longitude=116.4,
            birth_latitude=39.9,
        )
        chart = build_core_chart_payload(b, "chart")
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60)
        # calc_ut consumes UT1. Align TT and delta-T for the positional
        # comparison; record Skyfield's independent UT1/delta-T model too.
        t = ts.tt_jd(jd + ephemeris_call("deltat", jd))
        independent_t = ts.ut1_jd(jd)
        for p in chart["planets"]:
            if p["id"] not in names:
                continue
            lat, lon, _ = (
                earth.at(t)
                .observe(eph[names[p["id"]]])
                .apparent()
                .frame_latlon(ecliptic_frame)
            )
            _, ilon, _ = (
                earth.at(independent_t)
                .observe(eph[names[p["id"]]])
                .apparent()
                .frame_latlon(ecliptic_frame)
            )
            delta = float(((p["longitude"] - lon.degrees + 180) % 360 - 180) * 3600)
            rows.append(
                {
                    "datetime": str(dt),
                    "planet": p["id"],
                    "ours": p["longitude"],
                    "reference": float(lon.degrees),
                    "longitude_error_arcsec": delta,
                    "latitude_error_arcsec": float(
                        (p["latitude"] - lat.degrees) * 3600
                    ),
                    "independent_delta_t_error_arcsec": float(
                        ((p["longitude"] - ilon.degrees + 180) % 360 - 180) * 3600
                    ),
                    "delta_t_difference_seconds": float(
                        (t.tt - independent_t.tt) * 86400
                    ),
                    "ephemeris_model": chart["chart_profile"]["ephemeris_model"],
                }
            )
    save(
        out,
        "skyfield",
        {
            "summary": {
                "charts": len(samples),
                "positions": len(rows),
                "max_longitude_error_arcsec": max(
                    abs(r["longitude_error_arcsec"]) for r in rows
                ),
                "max_latitude_error_arcsec": max(
                    abs(r["latitude_error_arcsec"]) for r in rows
                ),
                "over_5_arcsec": int(
                    sum(abs(r["longitude_error_arcsec"]) > 5 for r in rows)
                ),
                "max_independent_delta_t_error_arcsec": max(
                    abs(r["independent_delta_t_error_arcsec"]) for r in rows
                ),
            },
            "positions": rows,
        },
    )


def angles_audit(out):
    import math

    import numpy as np
    from skyfield.api import load
    from skyfield.framelib import ecliptic_frame

    from fatebridge.core.ephemeris_runtime import ephemeris_call, swe

    rows, ts = [], load.timescale(builtin=True)
    for lon, lat in (
        (116.4, 39.9),
        (151.2, -33.9),
        (-74, 40.7),
        (-0.12, 51.5),
        (0, 0),
        (114.2, 22.3),
    ):
        for hour in (0, 6, 12, 18):
            birth = build_astro_birth_info(
                birth_year=2026,
                birth_month=10,
                birth_day=9,
                birth_hour=hour,
                birth_minute=30,
                birth_timezone="UTC",
                birth_longitude=lon,
                birth_latitude=lat,
            )
            ours = build_core_chart_payload(birth, "chart")
            jd = swe.julday(2026, 10, 9, hour + 0.5)
            t = ts.tt_jd(jd + ephemeris_call("deltat", jd))
            # Sidereal time is defined by UT1; do not let Skyfield infer a
            # different UT1 from our explicitly matched TT/delta-T.
            sidereal = math.radians(ts.ut1_jd(jd).gast * 15 + lon)
            phi = math.radians(lat)
            # Independent 3D construction: intersect the ecliptic plane with
            # the horizon and meridian, using Skyfield's coordinate frames.
            rotation = ecliptic_frame.rotation_at(t) @ t.M.T
            zenith = rotation @ np.array(
                [
                    math.cos(phi) * math.cos(sidereal),
                    math.cos(phi) * math.sin(sidereal),
                    math.sin(phi),
                ]
            )
            east = rotation @ np.array([-math.sin(sidereal), math.cos(sidereal), 0])
            asc = np.cross(zenith, [0, 0, 1])
            asc = asc if asc @ east > 0 else -asc
            mc = np.cross(east, [0, 0, 1])
            mc = mc if mc @ zenith > 0 else -mc
            for name, vector in (("ascendant", asc), ("midheaven", mc)):
                reference = math.degrees(math.atan2(vector[1], vector[0])) % 360
                got = ours["angles"][name]["longitude"]
                rows.append(
                    {
                        "longitude": lon,
                        "latitude": lat,
                        "utc_hour": hour + 0.5,
                        "point": name,
                        "ours": got,
                        "reference": reference,
                        "error_arcsec": (got - reference + 180) % 360 * 3600
                        - 180 * 3600,
                    }
                )
    save(
        out,
        "angles",
        {
            "summary": {
                "charts": len(rows) // 2,
                "angles": len(rows),
                "max_error_arcsec": max(abs(r["error_arcsec"]) for r in rows),
            },
            "cases": rows,
        },
    )


def solar_time_and_returns_audit(out, ephemeris):
    from skyfield.api import load, load_file, wgs84
    from skyfield.framelib import ecliptic_frame

    from fatebridge.core.ephemeris_runtime import ephemeris_call, swe
    from fatebridge.services.western_timing_tools import (
        calculate_lunarreturn,
        calculate_solarreturn,
    )
    from fatebridge.utils.helpers import calculate_solar_time_adjustment

    eph, ts = load_file(str(ephemeris)), load.timescale(builtin=True)
    # Apparent solar hour from topocentric Sun hour angle, independent of
    # FateBridge's equation-of-time approximation.
    solar_rows = []
    for month, day, hour, minute in ((11, 3, 0, 50), (2, 11, 1, 10), (6, 21, 12, 0)):
        dt = datetime(
            2026, month, day, hour, minute, tzinfo=timezone(timedelta(hours=8))
        )
        target = (
            (eph["earth"] + wgs84.latlon(30, 120))
            .at(ts.from_datetime(dt))
            .observe(eph["sun"])
            .apparent()
        )
        solar_hours = (target.hadec()[0].hours + 12) % 24
        seed = _build_analysis_seed(
            analysis_year=2026,
            analysis_month=month,
            analysis_day=day,
            analysis_hour=hour,
            analysis_minute=minute,
            analysis_timezone="+08:00",
            analysis_longitude=120,
            use_true_solar_time=True,
        )
        solar_rows.append(
            {
                "input": dt.isoformat(),
                "longitude": 120,
                "skyfield_apparent_solar_hour": solar_hours,
                "analysis_seed_corrected_datetime": str(seed.corrected_datetime),
                "analysis_seed_hour_pillar": "".join(seed.pillars["hour"]),
                "difference_from_skyfield_seconds": (
                    (
                        seed.corrected_datetime.hour
                        + seed.corrected_datetime.minute / 60
                        + seed.corrected_datetime.second / 3600
                        + seed.corrected_datetime.microsecond / 3_600_000_000
                        - solar_hours
                        + 12
                    )
                    % 24
                    - 12
                )
                * 3600,
                "hour_branch_matches_skyfield": seed.pillars["hour"][1]
                == "子丑寅卯辰巳午未申酉戌亥"[int((solar_hours + 1) // 2) % 12],
                "birth_path_adjustment": calculate_solar_time_adjustment(
                    dt.replace(tzinfo=None), "+08:00", 120
                ),
            }
        )
    save(
        out,
        "solar_time",
        {
            "summary": {
                "samples": len(solar_rows),
                "max_clock_error_seconds": max(
                    abs(r["difference_from_skyfield_seconds"]) for r in solar_rows
                ),
                "all_hour_branches_match": all(
                    r["hour_branch_matches_skyfield"] for r in solar_rows
                ),
                "label": "真太阳时",
            },
            "cases": solar_rows,
        },
    )

    def longitude(jd, planet):
        t = ts.tt_jd(jd + ephemeris_call("deltat", jd))
        return float(
            eph["earth"]
            .at(t)
            .observe(eph[planet])
            .apparent()
            .frame_latlon(ecliptic_frame)[1]
            .degrees
        )

    rows = []
    for y, m, d, h, minute in (
        (1990, 5, 17, 15, 30),
        (1988, 2, 29, 6, 15),
        (2000, 12, 10, 23, 10),
        (1978, 9, 2, 2, 30),
        (2024, 2, 10, 0, 0),
        (1954, 12, 1, 10, 30),
    ):
        kwargs = dict(
            birth_year=y,
            birth_month=m,
            birth_day=d,
            birth_hour=h,
            birth_minute=minute,
            birth_timezone="+08:00",
            birth_longitude=121.4737,
            birth_latitude=31.2304,
            analysis_year=2026,
            analysis_month=10,
            analysis_day=9,
        )
        birth_jd = swe.julday(y, m, d, h + minute / 60) - 8 / 24
        analysis_jd = swe.julday(2026, 10, 9, h + minute / 60) - 8 / 24
        for key, planet, call in (
            ("solarreturn", "sun", calculate_solarreturn),
            ("lunarreturn", "moon", calculate_lunarreturn),
        ):
            payload = call(**kwargs)
            if "error" in payload:
                rows.append({"input": kwargs, "tool": key, "error": payload})
                continue
            result = payload[key]
            dt = datetime.fromisoformat(result["return_datetime"]).astimezone(
                timezone.utc
            )
            jd = swe.julday(
                dt.year,
                dt.month,
                dt.day,
                dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3.6e9,
            )
            target_longitude = longitude(birth_jd, planet)

            def diff(j):
                return (longitude(j, planet) - target_longitude + 180) % 360 - 180

            low, high = jd - 0.25, jd + 0.25
            assert diff(low) < 0 < diff(high), (key, dt)
            for _ in range(35):
                mid = (low + high) / 2
                if diff(mid) < 0:
                    low = mid
                else:
                    high = mid
            root = (low + high) / 2
            rows.append(
                {
                    "input": kwargs,
                    "tool": key,
                    "return_datetime": dt.isoformat(),
                    "longitude_residual_arcsec": diff(jd) * 3600,
                    "difference_from_skyfield_root_seconds": (jd - root) * 86400,
                    "return_precedes_analysis": jd <= analysis_jd,
                    "days_before_analysis": analysis_jd - jd,
                }
            )
    successes = [r for r in rows if "error" not in r]
    save(
        out,
        "returns",
        {
            "summary": {
                "cases": len(rows),
                "errors": len(rows) - len(successes),
                "max_time_difference_seconds": max(
                    abs(r["difference_from_skyfield_root_seconds"]) for r in successes
                ),
                "max_residual_arcsec": max(
                    abs(r["longitude_residual_arcsec"]) for r in successes
                ),
                "all_precede_analysis": all(
                    r["return_precedes_analysis"] for r in successes
                ),
            },
            "cases": rows,
        },
    )


def liuren_audit(out):
    # Optional oracle source checkout, pinned by environment manifest.
    from kintaiyi.kinliuren import Liuren

    from fatebridge.core.metaphysics import build_liureng_board

    rows, errors = [], []
    trad = str.maketrans(
        {"惊": "驚", "蛰": "蟄", "谷": "穀", "满": "滿", "种": "種", "处": "處"}
    )
    names = dict(
        zip(
            "貴蛇雀合勾龍空虎常玄陰后",
            (
                "贵人",
                "螣蛇",
                "朱雀",
                "六合",
                "勾陈",
                "青龙",
                "天空",
                "白虎",
                "太常",
                "玄武",
                "太阴",
                "天后",
            ),
        )
    )
    for day_offset in range(60):
        dt = datetime(2026, 9, 1) + timedelta(days=day_offset)
        for hour in (2, 10, 14, 22):
            seed = _build_analysis_seed(
                analysis_year=dt.year,
                analysis_month=dt.month,
                analysis_day=dt.day,
                analysis_hour=hour,
            )
            ours = build_liureng_board(seed)
            term = seed.calendar_context["current_solar_term"]["name"].translate(trad)
            ref = Liuren(
                term, "八", "".join(seed.pillars["day"]), "".join(seed.pillars["hour"])
            )
            try:
                r = ref.result(0)  # 贵人表 option 0 matches FateBridge's table.
            except Exception as exc:
                errors.append(
                    {"date": dt.isoformat(), "hour": hour, "oracle_error": repr(exc)}
                )
                continue
            branches = [
                ours["three_transmissions"][k]["branch"]
                for k in ("initial", "middle", "final")
            ]
            rbranches = [r["三傳"][k][0] for k in ("初傳", "中傳", "末傳")]
            board = {p["earth_branch"]: p["sky_branch"] for p in ours["twelve_board"]}
            gods = {p["earth_branch"]: p["god"] for p in ours["twelve_board"]}
            rgods = {k: names[v] for k, v in r["地轉天將"].items()}
            lesson_upper = [x["upper_branch"] for x in ours["four_lessons"]]
            rupper = [r["四課"][k][0][0] for k in ("一課", "二課", "三課", "四課")]
            rows.append(
                {
                    "input": {
                        "datetime": str(dt.replace(hour=hour)),
                        "day_ganzhi": "".join(seed.pillars["day"]),
                        "hour_ganzhi": "".join(seed.pillars["hour"]),
                        "term": term,
                    },
                    "month_general_match": ours["month_general"]["branch"]
                    == ref.moongeneral(),
                    "sky_board_match": board == r["地轉天盤"],
                    "four_lesson_uppers_match": lesson_upper == rupper,
                    "transmissions_match": branches == rbranches,
                    "earth_gods_match": gods == rgods,
                    "ours_transmissions": branches,
                    "reference_transmissions": rbranches,
                    "ours_style": ours["board_style"],
                    "reference_style": r["格局"],
                    "ours_earth_gods": gods,
                    "reference_earth_gods": rgods,
                }
            )
    save(
        out,
        "liuren",
        {
            "summary": {
                "samples": len(rows),
                "oracle_errors": len(errors),
                "month_general_differences": sum(
                    not r["month_general_match"] for r in rows
                ),
                "sky_board_differences": sum(not r["sky_board_match"] for r in rows),
                "four_lesson_upper_differences": sum(
                    not r["four_lesson_uppers_match"] for r in rows
                ),
                "three_transmission_differences": sum(
                    not r["transmissions_match"] for r in rows
                ),
                "earth_gods_differences": sum(not r["earth_gods_match"] for r in rows),
            },
            "cases": rows,
            "oracle_errors": errors,
        },
    )


def taiyi_audit(out):
    from kintaiyi import config
    from kintaiyi.kintaiyi import Taiyi

    from fatebridge.core.metaphysics.taiyi import _TaiyiLife

    rows, counts = [], Counter()
    methods = (
        "accnum",
        "kook",
        "ty",
        "ty_gong",
        "skyyi",
        "earthyi",
        "fgd",
        "zhifu",
        "skyeyes",
        "sf",
        "home_cal",
        "home_general",
        "home_vgen",
        "away_cal",
        "away_general",
        "away_vgen",
        "set_cal",
        "hegod",
        "jigod",
        "se",
        "kingbase",
        "officerbase",
        "pplbase",
    )
    for year in range(1900, 2100, 2):
        oracle = Taiyi(year, 5, 15, 10, 30)
        pillars = oracle._get_gangzhi()[:4]
        lunar_year = config.lunar_date_d(year, 5, 15)["年"]
        ours = _TaiyiLife(*pillars, lunar_year)
        differences = []
        for method in methods:
            got = getattr(ours, method)()
            ref = (
                getattr(oracle, method)(0)
                if method in ("hegod", "jigod")
                else getattr(oracle, method)(0, 0)
            )
            if got != ref:
                counts[method] += 1
                differences.append({"field": method, "ours": got, "reference": ref})
        rows.append(
            {
                "datetime": f"{year}-05-15 10:30",
                "oracle_pillars": pillars,
                "oracle_lunar_year": lunar_year,
                "differences": differences,
            }
        )
    save(
        out,
        "taiyi_live",
        {
            "summary": {
                "samples": len(rows),
                "field_comparisons": len(rows) * len(methods),
                "cases_with_differences": sum(bool(r["differences"]) for r in rows),
                "field_difference_counts": counts,
            },
            "scope": "Same-input transform; current upstream can differ from the vendored historical snapshot. Not an end-to-end calendar validation.",
            "cases": rows,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iztro", type=Path, required=True)
    parser.add_argument("--ephemeris", type=Path, required=True)
    parser.add_argument(
        "--with-kintaiyi",
        action="store_true",
        help="Also audit live kinliuren; add pinned kintaiyi src to PYTHONPATH",
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    save(
        args.out,
        "environment",
        {
            "summary": {
                "packages": {
                    p: importlib.metadata.version(p)
                    for p in (
                        "fatebridge",
                        "lunar-python",
                        "skyfield",
                        "pyswisseph",
                        "kerykeion",
                        "lunardate",
                        "sxtwl",
                    )
                },
                "iztro": "2.5.8",
                "ephemeris": args.ephemeris.name,
                "ephemeris_sha256": hashlib.sha256(
                    args.ephemeris.read_bytes()
                ).hexdigest(),
                "git_head": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "source_file_sha256": {
                    str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(Path("src/fatebridge").rglob("*.py"))
                },
                "python": sys.version,
                "scope": "Synthetic inputs; UTC/+08:00. Calendar and board comparisons disable solar correction; solar_time separately tests apparent solar time.",
            }
        },
    )
    calendar_audit(args.out)
    lunar_exhaustive_audit(args.out)
    ziwei_audit(args.out, args.iztro)
    ziwei_audit(args.out, args.iztro, day_divide="current")
    skyfield_audit(args.out, args.ephemeris)
    angles_audit(args.out)
    solar_time_and_returns_audit(args.out, args.ephemeris)
    if args.with_kintaiyi:
        liuren_audit(args.out)
        taiyi_audit(args.out)


if __name__ == "__main__":
    main()
