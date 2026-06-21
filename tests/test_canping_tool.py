"""Tests for the canping (邵子参评数 / 金锁银匙) tool.

The parity golden in ``tests/fixtures/canping_golden_snapshot.txt`` was produced
by running horosa's own ``canpingLocal.js`` (buildSnapshotText) on fixed pillars
庚午/寅/巳/午, 男, 明法, 起运 3, 流年支 戌 — the FateBridge port must reproduce
it byte-for-byte. canping is pure arithmetic + a static condition-text table, so
the golden is deterministic across Python 3.10–3.13 (no ephemeris involved).
"""

from __future__ import annotations

from pathlib import Path

from fatebridge.core.canping import (
    BRANCHES,
    build_snapshot_text,
    calculate,
    compute_number,
    nayin_element,
)
from fatebridge.services.divination import calculate_canping_analysis
from fatebridge.utils.data import get_nayin

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "canping_golden_snapshot.txt"

# horosa NAYIN_PAIRS (canpingLocal.js:18-29): (ganzhi_a, ganzhi_b, element).
_HOROSA_NAYIN_PAIRS = [
    ("甲子", "乙丑", "金"),
    ("丙寅", "丁卯", "火"),
    ("戊辰", "己巳", "木"),
    ("庚午", "辛未", "土"),
    ("壬申", "癸酉", "金"),
    ("甲戌", "乙亥", "火"),
    ("丙子", "丁丑", "水"),
    ("戊寅", "己卯", "土"),
    ("庚辰", "辛巳", "金"),
    ("壬午", "癸未", "木"),
    ("甲申", "乙酉", "水"),
    ("丙戌", "丁亥", "土"),
    ("戊子", "己丑", "火"),
    ("庚寅", "辛卯", "木"),
    ("壬辰", "癸巳", "水"),
    ("甲午", "乙未", "金"),
    ("丙申", "丁酉", "火"),
    ("戊戌", "己亥", "木"),
    ("庚子", "辛丑", "土"),
    ("壬寅", "癸卯", "金"),
    ("甲辰", "乙巳", "火"),
    ("丙午", "丁未", "水"),
    ("戊申", "己酉", "土"),
    ("庚戌", "辛亥", "金"),
    ("壬子", "癸丑", "木"),
    ("甲寅", "乙卯", "水"),
    ("丙辰", "丁巳", "土"),
    ("戊午", "己未", "火"),
    ("庚申", "辛酉", "木"),
    ("壬戌", "癸亥", "水"),
]


def test_canping_nayin_parity_with_fb_get_nayin():
    """FB get_nayin element must match horosa's NAYIN_ELEMENT for all 60 ganzhi."""
    for a, b, element in _HOROSA_NAYIN_PAIRS:
        for ganzhi in (a, b):
            assert nayin_element(ganzhi) == element
            assert get_nayin(ganzhi[0], ganzhi[1])[-1] == element


def test_canping_compute_number_documented_anchor():
    """本命 巳/午/火 → 2242/3242, the algorithm's own documented test case."""
    result = compute_number("巳", "午", "火")
    assert result["numShun"] == 2242
    assert result["numNi"] == 3242


def test_canping_snapshot_byte_identical_to_horosa_golden():
    """Full chain (day_palace→ming_gong→大运→条文→render) == horosa output."""
    result = calculate(
        year_gz="庚午",
        month_branch="寅",
        day_branch="巳",
        hour_branch="午",
        gender="男",
        method="ming",
        qiyun_age=3,
        liunian_branch="戌",
    )
    expected = _FIXTURE.read_text(encoding="utf-8").rstrip("\n")
    assert build_snapshot_text(result) == expected


def test_canping_service_full_shape():
    result = calculate_canping_analysis(
        date="1990-06-15",
        time="09:33:00",
        zone="+08:00",
        gender="男",
        method="ming",
    )
    assert result["analysis_type"] == "邵子参评数 / 金锁银匙"
    assert result["element"] in {"金", "木", "水", "火", "土"}
    assert result["ming_gong"] in BRANCHES
    assert set(result["four_pillars"]) == {"year", "month", "day", "hour"}
    # 全表流年覆盖 1–120 虚岁。
    assert len(result["liunian_series"]["rows"]) == 120
    assert result["snapshot_text"].startswith("[起盘]")


def test_canping_gu_method_uses_day_branch():
    ming = calculate(
        year_gz="庚午",
        month_branch="寅",
        day_branch="巳",
        hour_branch="午",
        method="ming",
    )
    gu = calculate(
        year_gz="庚午",
        month_branch="寅",
        day_branch="巳",
        hour_branch="午",
        method="gu",
    )
    # 古法日宫支 = 八字日支; 明法用月支反向 (寅→亥), so the two diverge.
    assert gu["dayPalaceBranch"] == "巳"
    assert ming["dayPalaceBranch"] == "亥"
