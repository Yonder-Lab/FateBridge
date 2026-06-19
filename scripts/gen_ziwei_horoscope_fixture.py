#!/usr/bin/env python3
"""Generate tests/fixtures/ziwei_horoscope_reference.json from py-iztro.

Run ONCE in an ISOLATED venv (py-iztro must NOT touch the project env):
    python3.11 -m venv /tmp/iztro_oracle
    /tmp/iztro_oracle/bin/pip install py-iztro
    /tmp/iztro_oracle/bin/python3.11 scripts/gen_ziwei_horoscope_fixture.py

DO NOT re-run without pinning the py-iztro version that produced the committed
fixture: a silent upstream change could otherwise rewrite the oracle and let the
cross-check pass against drifted reference data. The fixture committed here was
generated with py-iztro 0.1.5.

Per (birth, target) case it records, per scope, the active palace's earthly
branch and the four 四化 target star names — a branch+stars tuple is
convention-independent and survives palace-index/name differences between
iztro and FateBridge.

Verified API (py-iztro 0.1.x):
  Astro().by_solar(date_str, time_index, gender_zh, is_leap, locale)
    -> Astrolabe with .horoscope(target_date_str, target_time_index)
       -> HoroscopeModel with attrs: decadal, age, yearly, monthly, daily, hourly
          each HoroscopeItemModel has:
            .earthly_branch  -> single CJK char (e.g. "辰")
            .mutagen         -> list of 4 star name strings
"""

import json
from pathlib import Path

from py_iztro import Astro  # type: ignore[import-not-found]

# (label, birth "Y-M-D", birth time index 0..12, gender zh, target "Y-M-D", target time index)
CASES = [
    ("m_1994", "1994-8-23", 7, "男", "2026-6-19", 7),
    ("f_1988", "1988-2-29", 3, "女", "2025-10-1", 3),
    ("m_2001", "2001-11-5", 11, "男", "2030-1-15", 11),
]

OUT = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / ("ziwei_horoscope_reference.json")
)

# our scope name -> py-iztro horoscope attribute
SCOPE_ATTR = [
    ("大限", "decadal"),
    ("小限", "age"),
    ("流年", "yearly"),
    ("流月", "monthly"),
    ("流日", "daily"),
    ("流时", "hourly"),
]


def main() -> None:
    astro = Astro()
    fixture: dict = {}
    for label, bdate, bidx, gender, tdate, tidx in CASES:
        chart = astro.by_solar(bdate, bidx, gender, True, "zh-CN")
        h = chart.horoscope(tdate, tidx)
        scopes: dict = {}
        for our_name, attr in SCOPE_ATTR:
            sc = getattr(h, attr)
            scopes[our_name] = {
                "branch": sc.earthly_branch,
                "mutagen": list(sc.mutagen),
            }
        fixture[label] = {
            "birth": {"date": bdate, "time_index": bidx, "gender": gender},
            "target": {"date": tdate, "time_index": tidx},
            "scopes": scopes,
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(fixture)} cases to {OUT}")


if __name__ == "__main__":
    main()
