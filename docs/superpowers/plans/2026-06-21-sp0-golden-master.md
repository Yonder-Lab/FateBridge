# SP0 Golden-Master 安全网 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为全部 66 个对外工具冻结一份确定性 JSON 输出基线，建立「数值锁」，供 SP1–SP3 重构期间字节级守护计算准确性。

**Architecture:** 复用 `tests/test_full_surface_validation.py` 已有的 `REST_POST_CASES`（66 个工具的代表性 payload）。先把这些 payload 夹具抽到共享模块 `tests/fixtures/surface_payloads.py`（单一信源，DRY）；再写规范化器（剔除易变字段 `generated_at`、浮点定精度、键排序）、runner（经 REST `TestClient` 跑遍 66 工具）、以及参数化 diff 测试。基线在 **Moshier 星历模式**下冻结，与 CI 一致。

**Tech Stack:** Python 3.13（`.venv`）、pytest、FastAPI `TestClient`、stdlib `json` / `difflib`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|---|---|---|
| `tests/fixtures/__init__.py` | 标记 fixtures 包 | Create |
| `tests/fixtures/surface_payloads.py` | 三端代表性 payload 的**单一信源**（payload 构造器 + `REST_POST_CASES` / `REST_GET_CASES` / `MCP_CASES`） | Create（内容从 full_surface 搬迁） |
| `tests/test_full_surface_validation.py` | 改为从 `surface_payloads` 导入这些夹具 | Modify |
| `tests/golden/__init__.py` | 标记 golden 包 | Create |
| `tests/golden/canonical.py` | 响应 → 确定性 JSON 文本（剔易变字段 / 定浮点精度 / 排序键） | Create |
| `tests/golden/runner.py` | 用固定输入驱动 66 工具，产出 `{slug: canonical_json}`；冻结基线入口 | Create |
| `tests/golden/snapshots/<slug>.json` | 66 份冻结基线 | Create（由 runner 生成） |
| `tests/test_golden_master.py` | 参数化重算并与基线逐字节 diff | Create |

---

## Task 1: 抽取共享 payload 夹具（DRY，零行为变化）

**Files:**
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/surface_payloads.py`
- Modify: `tests/test_full_surface_validation.py`（删除被搬走的定义，改为 import）

- [ ] **Step 1: 建包标记文件**

```bash
mkdir -p tests/fixtures
printf '"""共享测试夹具。"""\n' > tests/fixtures/__init__.py
```

- [ ] **Step 2: 把 payload 定义搬进 `surface_payloads.py`**

在 `tests/test_full_surface_validation.py` 中，从第一个 `def _birth_payload(` 起，到 `MCP_CASES = { ... }` 字典闭合为止（含所有 `_*_payload` / `_*_base` / `_export_content` / `_relative_mcp_kwargs` 构造器与 `REST_POST_CASES`、`REST_GET_CASES`、`MCP_CASES` 三张映射），整段**剪切**到新文件 `tests/fixtures/surface_payloads.py`。新文件顶部加：

```python
"""三端（REST / MCP）代表性 payload 的单一信源。

`full_surface` 契约测试与 `golden-master` 数值锁都从这里取输入，确保两套
回归用的是同一组确定性夹具。
"""
from __future__ import annotations
```

不改动任何 payload 的值——纯搬迁。

- [ ] **Step 3: 在 full_surface 顶部改为导入**

在 `tests/test_full_surface_validation.py` 原定义位置替换为：

```python
from tests.fixtures.surface_payloads import (
    MCP_CASES,
    REST_GET_CASES,
    REST_POST_CASES,
)
```

（若该文件内的测试函数引用了某个 `_xxx_payload` 构造器，按需把对应名字一并加入此 import。）

- [ ] **Step 4: 跑 full_surface，确认搬迁零回归**

Run: `.venv/bin/python -m pytest tests/test_full_surface_validation.py -q`
Expected: PASS（与搬迁前同样的通过数；尤其 `test_rest_post_endpoints_all_accept_representative_payloads`、`test_mcp_case_map_covers_all_registered_tools` 绿）

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ tests/test_full_surface_validation.py
git commit -m "test(fixtures): 抽取三端代表性 payload 为共享单一信源"
```

---

## Task 2: 输出规范化器 `canonical.py`

**Files:**
- Create: `tests/golden/__init__.py`
- Create: `tests/golden/canonical.py`
- Test: `tests/golden/test_canonical.py`

- [ ] **Step 1: 建包标记 + 写失败测试**

```bash
mkdir -p tests/golden
printf '"""Golden-master 安全网。"""\n' > tests/golden/__init__.py
```

`tests/golden/test_canonical.py`:

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/python -m pytest tests/golden/test_canonical.py -q`
Expected: FAIL（`ModuleNotFoundError: tests.golden.canonical`）

- [ ] **Step 3: 实现 `canonical.py`**

```python
"""Golden-master 输出规范化：把工具响应压成确定性的 JSON 文本。

规范化做三件事，让「同一份计算」永远得到逐字节相同的快照：
1. 剔除易变字段（如 ``run_metadata.generated_at`` 这种每次都变的时间戳）；
2. 浮点统一 round 到固定精度，吸收跨 Python 版本的末位浮点噪声；
3. 键排序后序列化。
"""
from __future__ import annotations

import json
from typing import Any

#: 每次重算都会变、与命理计算无关的字段，冻结前一律剔除。
VOLATILE_KEYS = frozenset({"generated_at"})

#: 浮点保留精度。远高于任何命理意义阈值，仅用于吸收末位浮点噪声。
FLOAT_PRECISION = 8


def _scrub(value: Any) -> Any:
    """递归剔除易变字段并规整浮点。"""
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, float):
        return round(value, FLOAT_PRECISION)
    return value


def canonical_json(payload: Any) -> str:
    """把响应对象压成确定性 JSON 文本（剔易变字段、定浮点精度、排序键）。"""
    return json.dumps(_scrub(payload), sort_keys=True, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/python -m pytest tests/golden/test_canonical.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add tests/golden/__init__.py tests/golden/canonical.py tests/golden/test_canonical.py
git commit -m "test(golden): 加输出规范化器（剔易变字段/定浮点精度/排序键）"
```

---

## Task 3: Runner `runner.py`

**Files:**
- Create: `tests/golden/runner.py`
- Test: `tests/golden/test_runner.py`

- [ ] **Step 1: 写失败测试**

`tests/golden/test_runner.py`:

```python
from tests.fixtures.surface_payloads import REST_POST_CASES
from tests.golden.runner import compute_outputs


def test_runner_covers_every_rest_tool():
    outputs = compute_outputs()
    # 每个 REST 工具都要产出一份规范化文本，数量与 case 数一致。
    assert len(outputs) == len(REST_POST_CASES)
    assert all(isinstance(text, str) and text for text in outputs.values())
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/bin/python -m pytest tests/golden/test_runner.py -q`
Expected: FAIL（`ModuleNotFoundError: tests.golden.runner`）

- [ ] **Step 3: 实现 `runner.py`**

```python
"""Golden-master runner：用固定输入驱动每个工具，产出 ``{slug: canonical_json}``。

只走 REST 一个面即可覆盖全部工具——三端共享同一 catalog 与 service 层，REST
响应是最完整的结构化输出。健康端点（/health、/ready、/metrics）含非确定计数，
不在冻结范围。冻结基线时强制 Moshier 星历模式，与 CI 对齐。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

import fatebridge.api as api_module
from tests.fixtures.surface_payloads import REST_POST_CASES
from tests.golden.canonical import canonical_json

#: 冻结基线的存放目录。
SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


def _slug(path: str) -> str:
    """把 REST 路径压成稳定文件名，如 /api/cn/bazi/birth → api_cn_bazi_birth。"""
    return path.strip("/").replace("/", "_")


def compute_outputs() -> Dict[str, str]:
    """跑遍全部 REST 工具 case，返回 {slug: 规范化 JSON}。"""
    # 强制 Moshier：本地若设了 SE_EPHE_PATH（高精度星历），输出会与 CI 不一致。
    os.environ.pop("SE_EPHE_PATH", None)
    client = TestClient(api_module.app)
    outputs: Dict[str, str] = {}
    for path, build_payload in REST_POST_CASES.items():
        response = client.post(path, json=build_payload())
        outputs[_slug(path)] = canonical_json(response.json())
    return outputs


def freeze_baseline() -> int:
    """把当前输出写进 snapshots/。仅在「经确认的输出变更」时调用。返回写入文件数。"""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = compute_outputs()
    for slug, text in outputs.items():
        (SNAPSHOT_DIR / f"{slug}.json").write_text(text + "\n", encoding="utf-8")
    return len(outputs)


if __name__ == "__main__":  # `python -m tests.golden.runner` 重新生成基线
    count = freeze_baseline()
    print(f"冻结 {count} 份基线到 {SNAPSHOT_DIR}")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `.venv/bin/python -m pytest tests/golden/test_runner.py -q`
Expected: PASS（runner 返回 66 条，全为非空字符串）

- [ ] **Step 5: Commit**

```bash
git add tests/golden/runner.py tests/golden/test_runner.py
git commit -m "test(golden): 加 runner（REST 驱动 66 工具 + Moshier 锁定 + 冻结入口）"
```

---

## Task 4: Golden diff 测试 `test_golden_master.py`

**Files:**
- Create: `tests/test_golden_master.py`

- [ ] **Step 1: 写测试（此时尚无基线，预期失败）**

```python
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
    assert snapshot.exists(), (
        f"缺少基线 {snapshot.name}；用 `python -m tests.golden.runner` 生成"
    )
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
```

- [ ] **Step 2: 运行确认失败（基线缺失）**

Run: `.venv/bin/python -m pytest tests/test_golden_master.py -q`
Expected: FAIL（每个 case 断言 `缺少基线 ...`）

---

## Task 5: 生成并冻结基线

**Files:**
- Create: `tests/golden/snapshots/*.json`（66 份）

- [ ] **Step 1: 生成基线**

Run: `.venv/bin/python -m tests.golden.runner`
Expected: 打印 `冻结 66 份基线到 .../tests/golden/snapshots`

- [ ] **Step 2: 抽查基线内容合理**

Run: `head -20 tests/golden/snapshots/api_cn_bazi_birth.json`
Expected: 一段排序键的 JSON，含八字结构字段；**不含** `generated_at`。

- [ ] **Step 3: 运行 golden 测试确认全绿**

Run: `.venv/bin/python -m pytest tests/test_golden_master.py -q`
Expected: PASS（67 passed = 66 参数化 + 1 覆盖检查）

- [ ] **Step 4: Commit 基线**

```bash
git add tests/golden/snapshots/ tests/test_golden_master.py
git commit -m "test(golden): 冻结 66 工具输出基线 + 上线 diff 数值锁"
```

---

## Task 6: 全量验证 + 四道门禁

- [ ] **Step 1: 全量测试**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS（原 471 + golden 新增，全绿）

- [ ] **Step 2: 四道门禁**

```bash
.venv/bin/black --check fatebridge tests scripts
.venv/bin/isort --check-only fatebridge tests scripts
.venv/bin/mypy fatebridge/
```
Expected: 全绿。（注：mypy 范围是 `fatebridge/`，不含 tests；新代码仅在 tests/ 下，不入 mypy 门禁。）

- [ ] **Step 3: 若 black/isort 有改动则修复并补提交**

```bash
.venv/bin/black fatebridge tests scripts && .venv/bin/isort fatebridge tests scripts
git add -A && git commit -m "style(golden): 格式化" || echo "无需格式化"
```

---

## 验收标准（对照 spec SP0）

- [ ] 基线覆盖全部 66 个对外 REST 工具（`test_golden_covers_all_cases` 绿）。
- [ ] `test_golden_master` 在当前 master 状态全绿。
- [ ] 易变字段 `generated_at` 已剔除；浮点按 8 位规范化。
- [ ] 基线在 Moshier 模式冻结（runner 强制 `pop SE_EPHE_PATH`），与 CI 一致。
- [ ] 提供重生成入口 `python -m tests.golden.runner`。
- [ ] 全量 pytest + black + isort + mypy 全绿。

## 风险与备注

- **跨 Python 版本浮点**：基线本地在 3.13 冻结，CI 跑 3.10–3.13。8 位浮点规范化吸收末位差异；纯 Python 与 C 扩展（pyswisseph/kerykeion）的计算跨版本应一致。首个 PR 的 CI 会立即暴露任何跨版本漂移；若出现，降低 `FLOAT_PRECISION` 或定位真实差异源。
- **基线冻结既有行为，不保证命理正确**：golden 只锁「重构零漂移」。若后续发现既有 bug，单列修正项、显式声明输出变更、用 runner 重生成基线。
- **CI 是否纳入 golden**：golden 测试随 `pytest -q` 默认收集执行，自动进入 CI 四门禁的 pytest 门，无需改 `ci.yml`。
- **66 vs 68 口径（已更新）**：catalog 共 68 个 `ToolSpec`，66 个有 `rest_path`，差额 2 个中：
  - `astro_relative_chart`：经验证为真正的 alias（不产生独立输出），不单独冻结。
  - `analyze_destiny`：原计划误判为 alias，实为绑定 `calculate_destiny_analysis` 的独立工具，已通过 MCP 面补入黄金覆盖（slug `mcp_analyze_destiny`）。
  当前黄金 case 总数：**67**（66 REST + 1 MCP）。`test_golden_covers_all_cases` 断言快照集与 `compute_outputs()` 返回集完全一致。
