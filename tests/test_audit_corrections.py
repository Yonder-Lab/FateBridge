"""
Regression + coverage tests for the audit corrections.

Covers the five issues fixed (B1 true-solar-time meridian from longitude,
B2 gender required for 大运 direction, B3 月令 weighting in day-master strength,
B4 is a packaging change, B5 partial analysis-date clamping) plus the
previously-missing value/behaviour assertions for the new analysis dimensions
(gender-dependent star selection, 大运/流年 auto-derivation, 子时 day rollover).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fatebridge.services.bazi as bazi
from fatebridge.core.elements import ElementAnalysis
from fatebridge.services.bazi import _resolve_analysis_date
from fatebridge.utils.helpers import create_person_info

# ---- B1: true solar time uses longitude-derived meridian when no timezone ----


def test_longitude_only_true_solar_matches_explicit_timezone():
    """A western longitude without a timezone must not use Asia/Shanghai's meridian."""
    implicit = create_person_info(
        1990,
        5,
        20,
        10,
        "t",
        "男",
        "未提供",
        birth_longitude=-74.0,
        use_true_solar_time=True,
    )
    explicit = create_person_info(
        1990,
        5,
        20,
        10,
        "t",
        "男",
        "未提供",
        birth_longitude=-74.0,
        birth_timezone="America/New_York",
        use_true_solar_time=True,
    )
    pi = bazi.calculate_bazi_birth(implicit)["bazi_birth"]["four_pillars"]
    pe = bazi.calculate_bazi_birth(explicit)["bazi_birth"]["four_pillars"]
    assert pi["day"] == pe["day"]
    assert pi["hour"] == pe["hour"]


def test_china_longitude_unaffected_by_b1_fix():
    p = create_person_info(
        1990,
        5,
        20,
        10,
        "t",
        "男",
        "北京",
        birth_longitude=116.4,
        use_true_solar_time=True,
    )
    day = bazi.calculate_bazi_birth(p)["bazi_birth"]["four_pillars"]["day"]
    assert day == {"stem": "乙", "branch": "酉"}


# ---- B2: 大运 direction requires an explicit gender ----


def test_unknown_gender_errors_on_dayun_dimension():
    person = create_person_info(1990, 5, 20, 10, "t", birth_place="北京")  # gender 未知
    result = bazi.calculate_bazi_career(person, analysis_year=2026)
    assert "error" in result
    assert "性别" in result["error"]


def test_known_gender_produces_forward_dayun_for_yang_year_male():
    person = create_person_info(1990, 5, 20, 10, "t", "男", "北京")  # 1990 庚午 阳年
    tc = bazi.calculate_bazi_career(person, analysis_year=2026)["career_analysis"][
        "timing_context"
    ]
    assert tc["dayun_pillar"] == "乙酉"  # forward (顺行) from month pillar


# ---- B3: 月令 (month command) drives day-master strength ----


def test_month_command_flips_borderline_strength():
    base = {"year": ("庚", "戌"), "day": ("甲", "子"), "hour": ("己", "巳")}
    de_ling = ElementAnalysis.analyze_day_master_strength(
        {**base, "month": ("丁", "卯")}
    )
    shi_ling = ElementAnalysis.analyze_day_master_strength(
        {**base, "month": ("丁", "酉")}
    )
    # 甲 in 卯 (得令/帮身) is stronger than 甲 in 酉 (失令/克身).
    assert de_ling["support_strength"] > shi_ling["support_strength"]
    assert shi_ling["strength_level"] == "弱"
    assert de_ling["strength_level"] != "弱"


# ---- B5: partial analysis date is clamped, never clock-dependent ----


def test_resolve_analysis_date_clamps_day():
    assert _resolve_analysis_date(2030, 6, 31).day == 30  # June has 30 days
    assert _resolve_analysis_date(2025, 2, 31).day == 28  # non-leap Feb
    assert _resolve_analysis_date(2024, 2, 31).day == 29  # leap Feb


# ---- New coverage: gender-dependent star selection in dimensions ----


def test_children_star_differs_by_gender():
    male = create_person_info(1990, 6, 15, 10, "t", "男", "北京")
    female = create_person_info(1990, 6, 15, 10, "t", "女", "北京")
    cs_m = bazi.calculate_bazi_children(male, dayun_pillar="壬戌")["children_analysis"][
        "child_star"
    ]["star"]
    cs_f = bazi.calculate_bazi_children(female, dayun_pillar="壬戌")[
        "children_analysis"
    ]["child_star"]["star"]
    assert "官杀" in cs_m  # 男命子女星 = 官杀
    assert "食伤" in cs_f  # 女命子女星 = 食伤
    assert cs_m != cs_f


def test_romance_opposite_sex_star_differs_by_gender():
    male = create_person_info(1990, 6, 15, 10, "t", "男", "北京")
    female = create_person_info(1990, 6, 15, 10, "t", "女", "北京")
    bm = bazi.calculate_bazi_romance(male, dayun_pillar="壬戌")["romance_analysis"][
        "opposite_sex_star"
    ]["basis"]
    bf = bazi.calculate_bazi_romance(female, dayun_pillar="壬戌")["romance_analysis"][
        "opposite_sex_star"
    ]["basis"]
    assert "财" in bm  # 男命异性缘 = 财
    assert "官杀" in bf  # 女命异性缘 = 官杀


# ---- New coverage: 大运/流年 auto-derivation correctness ----


def test_dimension_auto_derives_correct_dayun_and_liunian():
    person = create_person_info(1990, 6, 15, 10, "t", "男", "北京")
    tc = bazi.calculate_bazi_wealth(person, analysis_year=2026)["wealth_analysis"][
        "timing_context"
    ]
    assert tc["liunian_pillar"] == "丙午"  # 2026 year ganzhi
    assert tc["dayun_pillar"] == "乙酉"
    assert tc["overridden"] == {"dayun_pillar": False, "liunian_pillar": False}
    assert abs(tc["dayun_age"] - 28.56) < 0.5


def test_explicit_pillars_override_auto_derivation():
    person = create_person_info(1990, 6, 15, 10, "t", "男", "北京")
    tc = bazi.calculate_bazi_wealth(person, analysis_year=2026, dayun_pillar="壬戌")[
        "wealth_analysis"
    ]["timing_context"]
    assert tc["overridden"]["dayun_pillar"] is True


# ---- New coverage: 子时 (23:00-01:00) day rollover ----


def test_zi_shi_rolls_day_pillar_to_next_civil_day():
    same_day = create_person_info(2024, 2, 4, 22, "t", "男", "北京")
    zi_shi = create_person_info(2024, 2, 4, 23, "t", "男", "北京", birth_minute=30)
    next_day = create_person_info(2024, 2, 5, 1, "t", "男", "北京")

    d_same = bazi.calculate_bazi_birth(same_day)["bazi_birth"]["four_pillars"]["day"]
    d_zi = bazi.calculate_bazi_birth(zi_shi)["bazi_birth"]["four_pillars"]["day"]
    d_next = bazi.calculate_bazi_birth(next_day)["bazi_birth"]["four_pillars"]["day"]

    assert d_zi == d_next  # 23:30 belongs to the next day's pillar
    assert d_zi != d_same  # and differs from the same civil day's earlier pillar
