"""出生地解析精度回归：省级中心点回退时须显式提示，市县级/显式经度不提示。

「江苏省南通市海安市」这类县级地名不在离线地名表中，会回退匹配到省份「江苏」，
用省级中心点经度（119.42°，与海安实际 ~120.47° 相差约 1°≈4 分钟）做真太阳时
校正。此前这一省级近似被当成精确结果静默使用；现要求在 time_adjustment 中给出
resolution_advisory，提示调用方改传 birth_longitude。

均为纯字符串/历法判断，跨平台确定，无需 golden 字节锁。
"""

from fatebridge.utils.helpers import PersonInfo, normalize_birth_time


def _person(**overrides) -> PersonInfo:
    base = dict(
        birth_year=2000,
        birth_month=12,
        birth_day=10,
        birth_hour=9,
        birth_minute=55,
        gender="男",
        use_true_solar_time=True,
    )
    base.update(overrides)
    return PersonInfo(**base)


def test_province_fallback_emits_resolution_advisory():
    # 宿迁未收录于市级地名库，故按省级（江苏）近似回退，触发 advisory。
    nb = normalize_birth_time(_person(birth_place="江苏省宿迁市宿豫区"))
    summary = nb.as_dict()
    assert nb.applied is True
    assert summary["resolved_place"] == "江苏"
    assert summary["resolution_level"] == "province"
    advisory = summary.get("resolution_advisory")
    assert advisory is not None
    # 提示须可操作：点名地点、说明是省级近似、并指向 birth_longitude。
    assert "宿迁" in advisory
    assert "省级" in advisory
    assert "birth_longitude" in advisory


def test_explicit_longitude_has_no_advisory():
    nb = normalize_birth_time(
        _person(birth_place="江苏省南通市海安市", birth_longitude=120.47)
    )
    summary = nb.as_dict()
    assert nb.applied is True
    assert summary["longitude_source"] == "birth_longitude"
    # 用户显式给了经度：精度无歧义，不应多出 advisory 键。
    assert "resolution_advisory" not in summary


def test_city_level_place_has_no_advisory():
    nb = normalize_birth_time(_person(birth_place="杭州"))
    summary = nb.as_dict()
    assert summary["resolved_place"] == "杭州"
    assert summary["resolution_level"] == "city"
    assert "resolution_advisory" not in summary


def test_no_true_solar_no_advisory_even_for_province():
    # 未启用真太阳时：不做校正，省级回退也无精度顾虑，不提示。
    nb = normalize_birth_time(
        _person(birth_place="江苏省南通市海安市", use_true_solar_time=False)
    )
    summary = nb.as_dict()
    assert nb.applied is False
    assert "resolution_advisory" not in summary
