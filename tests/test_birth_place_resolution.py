"""出生地解析精度回归：省级中心点回退时须显式提示，市县级/显式经度不提示。

「江苏省南通市海安市」这类县级地名不在离线地名表中，会回退匹配到省份「江苏」，
用省级中心点经度（119.42°，与海安实际 ~120.47° 相差约 1°≈4 分钟）做真太阳时
校正。此前这一省级近似被当成精确结果静默使用；现要求在 time_adjustment 中给出
resolution_advisory，提示调用方改传 birth_longitude。

均为纯字符串/历法判断，跨平台确定，无需 golden 字节锁。
"""

from fatebridge.utils.helpers import (
    PersonInfo,
    normalize_birth_time,
    resolve_birth_place_context,
)


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


def test_no_true_solar_no_advisory_even_for_uncatalogued_tail():
    # 未启用真太阳时：不做校正，无精度顾虑，不提示。
    nb = normalize_birth_time(
        _person(birth_place="江苏省南通市海安市", use_true_solar_time=False)
    )
    summary = nb.as_dict()
    assert nb.applied is False
    assert "resolution_advisory" not in summary


def test_haian_resolves_to_county_not_parent_prefecture():
    # 海安是南通下辖县级市。含「南通海安」的串里府(南通)与县(海安)同时出现，
    # 县级更具体，必须胜出——否则会用南通市区坐标(纬度差约 0.56°)排出偏盘。
    for place in ("海安", "海安市", "南通海安", "江苏南通海安", "中国江苏南通海安市"):
        r = resolve_birth_place_context(place)
        assert r.canonical_name == "海安", place
        assert r.level == "county", place
        assert abs(r.longitude - 120.47) < 0.1, place
        assert abs(r.latitude - 32.54) < 0.1, place


def test_nantong_prefecture_alone_still_resolves_to_itself():
    r = resolve_birth_place_context("南通")
    assert r.canonical_name == "南通"
    assert r.level == "city"


def test_nantong_county_siblings_each_resolve_distinctly():
    # 同府的其它县级单位也补齐，避免「南通X」全部塌回南通市区。
    # 通州 故意不收录：其「通州区」别名与北京通州区撞名。
    for name in ("如皋", "启东", "海门", "如东"):
        r = resolve_birth_place_context(f"南通{name}")
        assert r.canonical_name == name, name
        assert r.level == "county", name


def test_kaizhou_resolves_to_county_not_chongqing_centroid():
    # 开州区是重庆下辖远郊区(原开县)，距渝中半岛约 180km。含「重庆开州」的串里
    # 直辖市(重庆)与区(开州区)同时出现：区级更具体且别名更长，必须胜出——否则会
    # 用重庆市中心坐标(106.55°E/29.56°N)排盘，上升/天顶偏约 1.7°。
    for place in ("开州区", "开州", "开县", "重庆开州", "重庆市开州区", "中国重庆市开州区"):
        r = resolve_birth_place_context(place)
        assert r.canonical_name == "开州区", place
        assert r.level == "county", place
        assert abs(r.longitude - 108.393) < 0.1, place
        assert abs(r.latitude - 31.178) < 0.1, place


def test_chongqing_centroid_and_near_districts_still_resolve_to_chongqing():
    # 安全不变式：直辖市本名及未收录的近郊区(渝中区在市中心附近)仍解析到重庆中心，
    # 区级条目只在显式收录时夺取匹配，绝不劫持直辖市回退。
    for place in ("重庆", "重庆市", "重庆市渝中区"):
        r = resolve_birth_place_context(place)
        assert r.canonical_name == "重庆", place
        assert r.level == "municipality", place


def test_beijing_tongzhou_not_misresolved_to_jiangsu():
    # 回归：county 级别若高于 municipality(或同级但更长别名胜出)，"北京通州区"
    # 会被错判到江苏南通。通州不入库 + county==municipality 共同守住此用例。
    r = resolve_birth_place_context("北京通州区")
    assert r.canonical_name == "北京"


def test_haian_no_longer_emits_province_advisory():
    # 已精确到县级 → 不再触发省级近似 advisory（对比 宿迁 仍触发）。
    nb = normalize_birth_time(_person(birth_place="江苏省南通市海安市"))
    summary = nb.as_dict()
    assert summary["resolved_place"] == "海安"
    assert summary["resolution_level"] == "county"
    assert "resolution_advisory" not in summary
