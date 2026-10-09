"""Reproducible, optional third-party correctness audit (no runtime changes).

Install lunar-python==1.4.8, skyfield==1.55 and optionally sxtwl==2.0.7 in
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
    from lunardate import LunarDate

    start, end = date(1900, 1, 31), date(2100, 2, 8)
    dt, rows, count = start, [], 0
    while dt <= end:
        s = sxtwl.fromSolar(dt.year, dt.month, dt.day)
        ref = [s.getLunarYear(), s.getLunarMonth(), s.getLunarDay(), s.isLunarLeap()]
        lunar = LunarDate.fromSolarDate(dt.year, dt.month, dt.day)
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
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
const result=cases.map(c=>{
 const chart=astro.bySolar(c.date,c.index,c.gender,true,'zh-CN');
 const h=chart.horoscope(c.target,c.target_index);
 return {ming:chart.earthlyBranchOfSoulPalace,shen:chart.earthlyBranchOfBodyPalace,ju:chart.fiveElementsClass,
 palaces:chart.palaces.map(p=>({branch:p.earthlyBranch,ganzhi:p.heavenlyStem+p.earthlyBranch,name:p.name,decadal:p.decadal.range,stars:[...p.majorStars,...p.minorStars,...p.adjectiveStars].map(s=>({name:s.name,brightness:s.brightness||null,mutagen:s.mutagen||null}))})),
 horoscope:Object.fromEntries(['decadal','age','yearly','monthly','daily','hourly'].map(k=>[k,{branch:chart.palaces[h[k].index]?.earthlyBranch,calendarBranch:h[k].earthlyBranch,index:h[k].index,mutagen:h[k].mutagen,nominalAge:h[k].nominalAge}]))};
});process.stdout.write(JSON.stringify(result));
"""


def ziwei_audit(out, iztro):
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
    refs = json.loads(
        subprocess.check_output(
            ["node", "-e", IZTRO_SCRIPT, str(iztro)], input=json.dumps(cases).encode()
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
            natal_year_branch=seed.pillars["year"][1],
            target_pillars=target.pillars,
            birth_year=y,
            target_year=ty,
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
    save(
        out,
        "ziwei",
        {
            "summary": {
                "charts": len(cases),
                "charts_with_differences": len(rows),
                "checked_fields": checked,
                "different_fields": counts,
            },
            "differences": rows,
            "reference_results": [
                {"input": c, "output": r} for c, r in zip(cases, refs)
            ],
        },
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
                "analysis_strategy": "longitude_only",
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--iztro", type=Path, required=True)
    parser.add_argument("--ephemeris", type=Path, required=True)
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
                "scope": "Synthetic audit, UTC/+08:00, no true-solar correction",
            }
        },
    )
    calendar_audit(args.out)
    lunar_exhaustive_audit(args.out)
    ziwei_audit(args.out, args.iztro)
    skyfield_audit(args.out, args.ephemeris)
    solar_time_and_returns_audit(args.out, args.ephemeris)


if __name__ == "__main__":
    main()
