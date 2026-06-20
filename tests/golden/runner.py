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
        # 非 200 会把错误体当成「黄金真相」冻进基线，掩盖真正的回归——当场拦下。
        assert (
            response.status_code == 200
        ), f"{path} 返回 {response.status_code}：{response.text}"
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
