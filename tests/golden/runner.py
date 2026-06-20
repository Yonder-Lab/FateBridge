"""Golden-master runner：用固定输入驱动每个工具，产出 ``{slug: canonical_json}``。

只走 REST 一个面即可覆盖全部工具——三端共享同一 catalog 与 service 层，REST
响应是最完整的结构化输出。健康端点（/health、/ready、/metrics）含非确定计数，
不在冻结范围。冻结基线时强制 Moshier 星历模式，与 CI 对齐。

还包含 MCP-only 工具（无 rest_path）的黄金覆盖，目前仅 analyze_destiny
通过其 MCP 面驱动，slug 为 ``mcp_analyze_destiny``。
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime as _RealDatetime
from pathlib import Path
from typing import Dict, Generator
from unittest.mock import patch

from fastapi.testclient import TestClient

import fatebridge.api as api_module
from tests.fixtures.surface_payloads import MCP_CASES, REST_POST_CASES
from tests.golden.canonical import canonical_json

#: 冻结基线的存放目录。
SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"

# ---------------------------------------------------------------------------
# 时钟冻结
# ---------------------------------------------------------------------------
# 凡是不提供 analysis_* 日期的 payload（如 /api/calculate、/api/cn/bazi/birth）
# 都会在服务层落到 datetime.now() 回退路径，导致基线随日历漂移。
# 在 compute_outputs() 期间把所有工具模块里的 datetime 替换成此固定子类，
# 使 now()/today() 永远返回同一瞬间，无需任何三方库。
#
# 日期选 2026-01-01T12:00:00：处于历法「平稳期」，远离节气边界，方便人工核查。
FROZEN_NOW = _RealDatetime(2026, 1, 1, 12, 0, 0)

# 所有通过 ``from datetime import datetime`` 引入、且在输出路径上调用
# now()/today() 的模块。新增工具若在输出路径用了 datetime.now()，须在此补记。
_DATETIME_PATCH_TARGETS = [
    "fatebridge.services.bazi.datetime",
    "fatebridge.services.timing.datetime",
    "fatebridge.analysis.timing_effects.datetime",
    "fatebridge.utils.helpers.datetime",
    "fatebridge.core.timing.datetime",
    "fatebridge.core.astrology_predictive.datetime",
]

# analyze_destiny 是唯一没有 rest_path 的独立工具，通过 MCP 面覆盖。
# key → slug 前缀，value → MCP_CASES 里对应的 key。
_MCP_ONLY_CASES: Dict[str, str] = {
    "mcp_analyze_destiny": "analyze_destiny",
}


def _make_frozen_datetime(frozen: _RealDatetime) -> type:
    """返回一个 datetime 子类，其 now()/today() 固定返回 ``frozen``。"""

    class FrozenDatetime(_RealDatetime):
        # now() 可带 tz 参数；忽略时区仅返回裸 naive datetime，与 bazi.py 保持一致。
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            if tz is not None:
                # 服务层偶尔传 tz（astrology_predictive）；返回 aware 固定值。
                return _RealDatetime(
                    frozen.year,
                    frozen.month,
                    frozen.day,
                    frozen.hour,
                    frozen.minute,
                    frozen.second,
                    tzinfo=tz,
                )
            return frozen

        @classmethod
        def today(cls):  # type: ignore[override]
            return frozen

    FrozenDatetime.__name__ = "FrozenDatetime"
    FrozenDatetime.__qualname__ = "FrozenDatetime"
    return FrozenDatetime


@contextmanager
def freeze_clock(frozen: _RealDatetime = FROZEN_NOW) -> Generator[None, None, None]:
    """上下文管理器：在所有工具模块里把 datetime 冻结到 ``frozen``。

    只替换模块属性，不影响其他 stdlib 使用者；退出时自动恢复。
    """
    frozen_cls = _make_frozen_datetime(frozen)
    patches = [patch(target, frozen_cls) for target in _DATETIME_PATCH_TARGETS]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


def _slug(path: str) -> str:
    """把 REST 路径压成稳定文件名，如 /api/cn/bazi/birth → api_cn_bazi_birth。"""
    return path.strip("/").replace("/", "_")


def compute_outputs(frozen: _RealDatetime = FROZEN_NOW) -> Dict[str, str]:
    """跑遍全部 REST 工具 case 及 MCP-only case，返回 {slug: 规范化 JSON}。

    时钟冻结到 ``frozen``，使所有 now() 回退路径产出确定性输出。
    """
    # 强制 Moshier：本地若设了 SE_EPHE_PATH（高精度星历），输出会与 CI 不一致。
    os.environ.pop("SE_EPHE_PATH", None)
    outputs: Dict[str, str] = {}

    with freeze_clock(frozen):
        # --- REST 面 ---
        client = TestClient(api_module.app)
        for path, build_payload in REST_POST_CASES.items():
            response = client.post(path, json=build_payload())
            # 非 200 会把错误体当成「黄金真相」冻进基线，掩盖真正的回归——当场拦下。
            assert (
                response.status_code == 200
            ), f"{path} 返回 {response.status_code}：{response.text}"
            outputs[_slug(path)] = canonical_json(response.json())

        # --- MCP-only 面 ---
        import fatebridge.mcp_server as mcp_module  # noqa: PLC0415

        for slug, mcp_key in _MCP_ONLY_CASES.items():
            tool_name, payload_fn = MCP_CASES[mcp_key]
            tool = getattr(mcp_module, tool_name)
            raw_text = tool.fn(**payload_fn())
            outputs[slug] = canonical_json(json.loads(raw_text))

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
