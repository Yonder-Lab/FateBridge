"""锁定五行月令旺衰相位（旺/相/休/囚/死）与分布口径标注。

element_distribution 是结构计数（非旺衰）。新增 element_seasonal_phase 以
经典确定映射补足旺衰维度：与月令同类为旺、月令所生为相、生月令者为休、
月令所克者为囚、克月令者为死。
"""

from fatebridge.core.elements import ElementAnalysis

ALL_PHASES = {"旺", "相", "休", "囚", "死"}


def test_water_month_phases():
    # 子月（水）：水旺、木相、金休、火囚、土死（命主月令）
    phases = ElementAnalysis.seasonal_phases("子")
    assert phases == {"水": "旺", "木": "相", "金": "休", "火": "囚", "土": "死"}


def test_wood_month_phases():
    # 寅月（木）：木旺、火相、水休、土囚、金死
    phases = ElementAnalysis.seasonal_phases("寅")
    assert phases == {"木": "旺", "火": "相", "水": "休", "土": "囚", "金": "死"}


def test_every_month_assigns_each_phase_exactly_once():
    for branch in "子丑寅卯辰巳午未申酉戌亥":
        phases = ElementAnalysis.seasonal_phases(branch)
        assert set(phases) == {"金", "木", "水", "火", "土"}
        # 五行对五相，恰好一一对应（不含季月土的折中处理）
        assert sorted(phases.values()) == sorted(ALL_PHASES)


def test_basis_documents_static_count_not_strength():
    assert "旺衰" in ElementAnalysis.DISTRIBUTION_BASIS
    assert "element_seasonal_phase" in ElementAnalysis.DISTRIBUTION_BASIS


def test_analyze_day_master_exposes_phase_and_basis():
    pillars = {
        "year": ("庚", "辰"),
        "month": ("戊", "子"),
        "day": ("壬", "寅"),
        "hour": ("乙", "巳"),
    }
    result = ElementAnalysis.analyze_day_master_strength(pillars)
    assert result["element_seasonal_phase"]["火"] == "囚"
    assert result["element_seasonal_phase"]["水"] == "旺"
    assert "element_distribution_basis" in result
