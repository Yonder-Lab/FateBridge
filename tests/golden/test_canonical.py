from tests.golden.canonical import canonical_json


def test_drops_volatile_generated_at():
    a = {"x": 1, "run_metadata": {"generated_at": "2026-01-01T00:00:00Z", "tool": "t"}}
    b = {"x": 1, "run_metadata": {"generated_at": "2099-12-31T23:59:59Z", "tool": "t"}}
    assert canonical_json(a) == canonical_json(b)


def test_rounds_floats_to_fixed_precision():
    # 第 9 位起的差异被 8 位精度吸收 → 视为相等
    assert canonical_json({"deg": 123.12345678123}) == canonical_json({"deg": 123.12345678456})
    # 但第 8 位的真实差异必须保留 → 精度恰为 8，既不过粗也不过细
    assert canonical_json({"deg": 123.12345678}) != canonical_json({"deg": 123.12345679})


def test_sorts_keys_stably():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_scrubs_nested_lists_and_dicts():
    payload = {"items": [{"generated_at": "x", "v": 1.0000000001}]}
    out = canonical_json(payload)
    assert "generated_at" not in out
