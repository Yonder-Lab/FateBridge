"""Golden-master 回归：重算每个工具输出，与冻结基线逐字节比对。

任何差异都视为失败——这是 SP1–SP3 重构期间的数值锁。若某次差异确属「经确认
的输出变更」，用 `python -m tests.golden.runner` 重新生成基线后再提交。
"""

from __future__ import annotations

import difflib

import pytest

from tests.golden.runner import SNAPSHOT_DIR, compute_outputs

_OUTPUTS = compute_outputs()


@pytest.mark.parametrize("slug", sorted(_OUTPUTS))
def test_output_matches_golden(slug: str) -> None:
    snapshot = SNAPSHOT_DIR / f"{slug}.json"
    assert (
        snapshot.exists()
    ), f"缺少基线 {snapshot.name}；用 `python -m tests.golden.runner` 生成"
    expected = snapshot.read_text(encoding="utf-8").rstrip("\n")
    actual = _OUTPUTS[slug]
    if actual != expected:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=f"{slug}.golden",
                tofile=f"{slug}.actual",
                lineterm="",
            )
        )
        pytest.fail(f"{slug} 输出偏离基线：\n{diff}")


def test_golden_covers_all_cases() -> None:
    """基线文件集必须与工具 case 集完全一致，防止悄悄漏掉/多出工具。"""
    frozen = {p.stem for p in SNAPSHOT_DIR.glob("*.json")}
    assert frozen == set(_OUTPUTS), {
        "missing": sorted(set(_OUTPUTS) - frozen),
        "stale": sorted(frozen - set(_OUTPUTS)),
    }
