"""锁定大运时间字段的人类可读标签清晰度。

dayun_age = 分析年龄 − 起运岁数 = "起运至今累计行运年数"，此前被标成"当前运龄"
或直接打印英文键，易被误读为起运岁数。本测试钉死清晰标签。
"""

from fatebridge.services.structured_snapshot import _KEY_LABELS, _label


def test_dayun_age_label_is_unambiguous():
    label = _label("dayun_age")
    assert label == "累计行运年数(起运至今)"
    assert label != "dayun_age"  # 不再是原始英文键
    assert "当前运龄" not in label  # 不再用易误读的旧标签


def test_timing_keys_have_chinese_labels():
    for key in (
        "analysis_date",
        "start_age",
        "years_in_period",
        "dayun_pillar",
        "liunian_pillar",
    ):
        assert key in _KEY_LABELS
        assert _label(key) != key


def test_unknown_key_still_falls_back_to_raw():
    assert _label("some_unmapped_key") == "some_unmapped_key"
