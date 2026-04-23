"""Regression tests for the 2026-04-23 FateBridge logic audit.

These tests lock in fixes for defects discovered by the
"chief logic auditor" sweep:

1. Longitude-only true-solar-time strategy had the longitude correction
   inverted (east of meridian was pushed back, not forward).
2. ``build_sixyao_result`` reused demo placeholder lines when callers
   supplied ``gua_code`` + ``changed_code`` without explicit lines,
   emitting spurious moving lines driven by the fallback seed.
3. ``_normalize_date_text`` did not zero-pad month/day, so natural
   inputs like ``"2026/4/23"`` crashed ``datetime.fromisoformat``.
4. ``analyze_ten_gods`` dropped hidden stems equal to the day master,
   hiding 比肩 roots (e.g. 庚日 in 巳月 藏 庚).
5. Offline astro house-system codes accepted only integers 0..8, so the
   timing endpoints' ``house_system="P"`` strings were rejected on the
   core-chart side. Both input styles now resolve to the same spec.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fatebridge.core.astrology import _resolve_offline_house_system
from fatebridge.core.elements import ElementAnalysis
from fatebridge.core.phase2_local import (
    _normalize_date_text,
    _normalize_time_text,
    build_sixyao_result,
)
from fatebridge.utils.helpers import (
    SOLAR_TIME_STRATEGY_APPARENT,
    SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
    calculate_solar_time_adjustment,
)


def test_longitude_only_strategy_sign_matches_physics() -> None:
    """At Shanghai's +08 meridian (120°E), 130°E sits 10° east; true solar
    time must run AHEAD of the wall clock. The longitude-only strategy
    used to flip this, pushing eastern longitudes backward."""
    moment = datetime(2024, 6, 21, 14, 30)
    tz = "Asia/Shanghai"

    east = calculate_solar_time_adjustment(
        moment, tz, 130.0, strategy=SOLAR_TIME_STRATEGY_LONGITUDE_ONLY
    )
    west = calculate_solar_time_adjustment(
        moment, tz, 100.0, strategy=SOLAR_TIME_STRATEGY_LONGITUDE_ONLY
    )
    same_east = calculate_solar_time_adjustment(
        moment, tz, 130.0, strategy=SOLAR_TIME_STRATEGY_APPARENT
    )

    # 4 minutes per degree: 10° * 4 = 40 min.
    assert east["total_correction_minutes"] == 40.0
    assert west["total_correction_minutes"] == -80.0
    # Both strategies must agree in sign (apparent adds the equation-of-time
    # term, so magnitudes differ by a few minutes but direction must match).
    assert (east["total_correction_minutes"] > 0) == (
        same_east["total_correction_minutes"] > 0
    )


def test_normalize_date_text_zero_pads_single_digits() -> None:
    # Both slash and dash separators, padded or not, must normalize.
    assert _normalize_date_text("2026/4/23") == "2026-04-23"
    assert _normalize_date_text("2026/04/23") == "2026-04-23"
    assert _normalize_date_text("2026-4-23") == "2026-04-23"
    assert _normalize_date_text("2026-04-23") == "2026-04-23"
    # Non-matching inputs pass through unchanged so callers get a useful
    # fromisoformat error message rather than silently corrupted data.
    assert _normalize_date_text("not-a-date") == "not-a-date"


def test_normalize_time_text_zero_pads_hours_and_seconds() -> None:
    assert _normalize_time_text("9:15") == "09:15:00"
    assert _normalize_time_text("9:5:3") == "09:05:03"
    assert _normalize_time_text("") == "00:00:00"
    assert _normalize_time_text("12:00:00") == "12:00:00"


def test_sixyao_moving_lines_honor_supplied_codes() -> None:
    """If caller passes gua_code and changed_code but no lines, the change
    flags must be derived from the codes (not from the placeholder seed,
    which would report lines 3 and 6 as moving for any request)."""
    result = build_sixyao_result(
        date="2026/04/23",
        time="12:00",
        zone="+08:00",
        lat="31n13",
        lon="121e28",
        question="audit",
        gua_code="111000",
        changed_code="110000",
    )
    assert result["moving_lines"] == [3]
    # Line 6 (上爻) had a hardcoded change=True in the old default seed — it
    # must now correctly report no change.
    assert result["lines"][5]["change"] is False
    assert "is_fuyin_line" not in result["lines"][5]


def test_hidden_stems_include_day_master_as_bi_jian() -> None:
    """庚日主生于巳月, 巳藏丙/庚/戊. The old code silently dropped the
    庚 hidden stem because it matched the day master, hiding the 日主之根.
    The fix keeps it and labels it 比肩."""
    pillars = {
        "year": ("庚", "午"),
        "month": ("辛", "巳"),
        "day": ("庚", "辰"),
        "hour": ("癸", "未"),
    }
    ten_gods = ElementAnalysis.analyze_ten_gods(pillars)

    month_hidden = [
        entry
        for entry in ten_gods["month"]
        if entry["position"].startswith("month_branch_hidden_")
    ]
    characters = [entry["character"] for entry in month_hidden]
    assert characters == ["丙", "庚", "戊"], month_hidden

    bi_jian = next(entry for entry in month_hidden if entry["character"] == "庚")
    assert bi_jian["ten_god"] == "比肩"


@pytest.mark.parametrize(
    "value,expected_key",
    [
        (0, "whole_sign"),
        ("0", "whole_sign"),
        ("W", "whole_sign"),
        ("whole_sign", "whole_sign"),
        ("P", "placidus"),
        ("p", "placidus"),
        ("Placidus", "placidus"),
        ("placidus", "placidus"),
        ("K", "koch"),
        ("Koch", "koch"),
        ("R", "regiomontanus"),
        ("Regiomontanus", "regiomontanus"),
    ],
)
def test_astro_house_system_accepts_string_and_integer(value, expected_key) -> None:
    info = _resolve_offline_house_system(value, context_label="test")
    assert info["key"] == expected_key


@pytest.mark.parametrize("bad", ["", None, "nonsense", 99, "equal"])
def test_astro_house_system_rejects_unknown(bad) -> None:
    with pytest.raises(ValueError):
        _resolve_offline_house_system(bad, context_label="test")


def test_compatibility_score_rewards_three_harmony_and_penalises_harm() -> None:
    """``BaZiRules.calculate_compatibility_score`` previously only scored 六合
    and 六冲. Three-harmony, half-harmony, 六害 and 三刑 are now included so
    the traditional_compatibility block reflects classical jipan matching."""
    from fatebridge.core.rules import BaZiRules

    # 一方: 申子辰 水三合 分散在三柱; 二方: 亥子丑 混合 (主要对冲六合已有)
    pillars_full_triple = {
        "year": ("甲", "申"),
        "month": ("乙", "子"),
        "day": ("丙", "辰"),  # 三合水局齐
        "hour": ("丁", "卯"),
    }
    # 对方也有自己部分同组支, 跨盘凑成 三合
    pillars_partial = {
        "year": ("戊", "申"),  # 跨盘与前者 辰 凑 半合
        "month": ("己", "子"),
        "day": ("庚", "午"),  # 日支 六冲 前者的子
        "hour": ("辛", "未"),  # 前者日支辰 与 未 六害
    }
    result = BaZiRules.calculate_compatibility_score(
        pillars_full_triple, pillars_partial
    )
    joined = " | ".join(result["details"])
    assert "半合" in joined, joined
    # Six harm shows as "相害" note — we use 六害 consistently
    assert "六害" in joined, joined
    assert result["harmony_score"] > 0
    assert result["clash_score"] > 0


def test_dayun_analysis_exposes_precise_start_age_and_direction() -> None:
    """With the display ``start_age`` ceil-rounded to 8 for a chart whose real
    起运 is ~7.25岁, consumers need ``start_age_precise`` to reconcile the
    fractional ``dayun_age`` and show the correct 顺/逆行 direction."""
    from fatebridge.services.timing import calculate_dayun_analysis
    from fatebridge.utils.helpers import PersonInfo

    person = PersonInfo(
        name="zhang",
        gender="男",
        birth_year=1990,
        birth_month=5,
        birth_day=15,
        birth_hour=14,
        birth_minute=30,
        birth_timezone="Asia/Shanghai",
        birth_longitude=121.47,
        use_true_solar_time=True,
    )
    result = calculate_dayun_analysis(person, analysis_age=30)
    info = result["dayun_info"]
    assert info["start_age"] == 8
    assert info["start_age_precise"] is not None
    # 7 < precise < 8 for this chart (roughly 7.25). Use a loose window to stay
    # resilient to precision tweaks while still catching a stale display.
    assert 7.0 <= info["start_age_precise"] < 8.0
    # dayun_age + start_age_precise must sum to the analysis age (within 1s).
    assert abs(info["dayun_age"] + info["start_age_precise"] - 30) < 0.02
    # 1990 年干 庚 (阳) + 男 → 顺行
    assert info["direction"] == "顺行"


def test_compatibility_score_detects_cross_chart_triple_punishment() -> None:
    from fatebridge.core.rules import BaZiRules

    pillars_a = {
        "year": ("甲", "寅"),
        "month": ("乙", "卯"),
        "day": ("丙", "辰"),
        "hour": ("丁", "巳"),
    }
    pillars_b = {
        "year": ("戊", "申"),
        "month": ("己", "酉"),
        "day": ("庚", "戌"),
        "hour": ("辛", "亥"),
    }
    result = BaZiRules.calculate_compatibility_score(pillars_a, pillars_b)
    # 寅巳申 三刑 已由 前者 (寅/巳) + 后者 (申) 合成
    assert any("三刑" in d for d in result["details"]), result["details"]
    assert result["clash_score"] >= 5
