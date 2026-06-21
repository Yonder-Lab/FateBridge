"""Tests for the heluo (河洛理数) tool.

Two parity goldens, both produced by horosa's own `heluoLocal.js` / `runHeluo`:

- ``heluo_judge_snapshot.txt`` — fixed pillars 甲子/丁卯/庚申/庚辰 (阳男·辰时) +
  an explicit 清明 化工, so it pins the 节气-*independent* algorithm
  (起命/元堂/爻辞/大限) **and** the 命运篇 judge logic, with no ephemeris in play.
- ``heluo_e2e_snapshot.txt`` — horosa's full `runHeluo` for 2000-05-15 09:33 (a
  节气-safe date). FateBridge reproduces it byte-for-byte using its **own** four
  pillars and its **own** 24-term solar-term engine — proving the 节气-source swap
  (lunar-javascript → FB) is transparent off-boundary.
"""

from __future__ import annotations

from pathlib import Path

from fatebridge.core.heluo import (
    build_snapshot_text,
    calculate,
    da_yun,
    judge,
    solar_term_huagong,
)
from fatebridge.services.divination import calculate_heluo_analysis

_FIX = Path(__file__).resolve().parent / "fixtures"

_CASE1 = {"year": "甲子", "month": "丁卯", "day": "庚申", "hour": "庚辰"}


def test_heluo_documented_anchors():
    """heluoLocal.js:3-4 算例：甲子…→天風姤/上九；丁巳…→水風井。"""
    c1 = calculate(
        four_pillars=_CASE1, gender="男", hour_zhi="辰", birth_year=1924, month_zhi="卯"
    )
    assert c1["xian"]["name"] == "天風姤"
    assert c1["xian"]["yuan"] == 6  # 上九

    c2 = calculate(
        four_pillars={"year": "丁巳", "month": "丙午", "day": "壬寅", "hour": "辛丑"},
        gender="男",
        hour_zhi="丑",
        birth_year=1917,
        month_zhi="午",
    )
    assert c2["xian"]["name"] == "水風井"


def test_heluo_judge_snapshot_byte_identical_to_horosa():
    """起命 + 元堂爻辞 + 命运篇 + 大限 == horosa (fixed pillars + 清明 化工)."""
    chart = calculate(
        four_pillars=_CASE1, gender="男", hour_zhi="辰", birth_year=1924, month_zhi="卯"
    )
    hg = solar_term_huagong("清明", False)
    jg = judge(chart, _CASE1, "卯", hg)
    dy = da_yun(chart["xian"], chart["hou"], 1924)
    expected = (
        (_FIX / "heluo_judge_snapshot.txt").read_text(encoding="utf-8").rstrip("\n")
    )
    assert build_snapshot_text(chart, jg, dy) == expected


def test_heluo_end_to_end_matches_horosa_runheluo():
    """Full service (FB pillars + FB 24-term 节气) == horosa runHeluo, 2000-05-15."""
    result = calculate_heluo_analysis(
        date="2000-05-15", time="09:33:00", zone="+08:00", gender="男"
    )
    expected = (
        (_FIX / "heluo_e2e_snapshot.txt").read_text(encoding="utf-8").rstrip("\n")
    )
    assert result["snapshot_text"] == expected


def test_heluo_service_shape():
    result = calculate_heluo_analysis(
        date="2000-05-15", time="09:33:00", zone="+08:00", gender="男"
    )
    assert result["analysis_type"] == "河洛理数"
    assert result["chart"]["xian"]["name"] and result["chart"]["hou"]["name"]
    assert len(result["dayun"]["all"]) == 12  # 先天 6 段 + 后天 6 段
    assert result["solar_term"]["term"] == "立夏"
    assert result["snapshot_text"].startswith("[起命]")
    assert set(result["four_pillars"]) == {"year", "month", "day", "hour"}


def test_heluo_zhizun_bian_er_bu_yi():
    """三至尊卦(坎為水/水雷屯/水山蹇) 九五阴令/上六阳令『变而不易』特例覆盖。"""
    from fatebridge.core.heluo import transform_houtian

    lines = [0, 1, 0, 0, 1, 0]  # 坎為水
    # 上六(yuan=6) + 阳令 → 变而不易：只翻爻、不互换上下卦、元堂位不动。
    hou = transform_houtian("坎為水", lines, 6, True)
    assert hou["yuan"] == 6
    assert hou["lines"] == [0, 1, 0, 0, 1, 1]
