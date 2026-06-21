"""锁定文档中的工具计数与中央目录一致，防止散文数字与代码漂移。

背景：README / API.md / ARCHITECTURE.md 里写死的 “N 个 REST 路由 / N 个 MCP 工具”
是仓库中唯一不受任何测试约束的 “第二份描述”，历史上一度漂移到三个互不相同的
错误值（63/60、54/51、54/50，而真值是 76/76）。

本测试从文档里把这些数字**抽出来**，与 ``tool_catalog`` 的实时计数比对：
任何人新增/删除工具后若忘了同步文档，CI 会失败。计数的唯一信源永远是
``rest_specs()`` / ``mcp_specs()``。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fatebridge.api import app
from fatebridge.services.tool_catalog import mcp_specs, rest_specs

REPO_ROOT = Path(__file__).resolve().parent.parent

LIVE_REST = len(rest_specs())
LIVE_MCP = len(mcp_specs())

# (相对路径, 人类可读标签, 抽取数字的正则, 期望的实时计数)
# 正则用 (\d+) 捕获文档当前声称的数字；期望值取自实时目录。
CHECKS = [
    ("README.md", "README REST 业务路由", r"(\d+)\s*个业务\s*REST\s*路由", LIVE_REST),
    ("README.md", "README FastMCP 工具", r"(\d+)\s*个\s*FastMCP\s*工具", LIVE_MCP),
    ("README.md", "README 所有工具", r"所有工具（(\d+)\s*个）", LIVE_MCP),
    ("docs/API.md", "API.md REST 业务路由", r"(\d+)\s*个业务\s*REST\s*路由", LIVE_REST),
    ("docs/API.md", "API.md FastMCP 工具", r"(\d+)\s*个\s*FastMCP\s*工具", LIVE_MCP),
    (
        "docs/ARCHITECTURE.md",
        "ARCHITECTURE REST 业务路由",
        r"(\d+)\s*个业务\s*REST\s*路由",
        LIVE_REST,
    ),
    (
        "docs/ARCHITECTURE.md",
        "ARCHITECTURE MCP 工具",
        r"(\d+)\s*个\s*MCP\s*工具",
        LIVE_MCP,
    ),
]


@pytest.mark.parametrize(
    "rel_path,label,pattern,expected", CHECKS, ids=[c[1] for c in CHECKS]
)
def test_documented_count_matches_catalog(
    rel_path: str, label: str, pattern: str, expected: int
) -> None:
    text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    found = re.findall(pattern, text)
    assert found, (
        f"{label}: 在 {rel_path} 未找到匹配 /{pattern}/ 的计数语句——"
        f"文档措辞可能被改动，请同步更新本测试的正则。"
    )
    documented = {int(n) for n in found}
    assert documented == {expected}, (
        f"{label}: {rel_path} 声称 {sorted(documented)}，但中央目录实时计数为 {expected}。"
        f"请把文档数字改为 {expected}（计数唯一信源是 tool_catalog 的 rest_specs()/mcp_specs()）。"
    )


def test_rest_and_mcp_counts_are_plausible() -> None:
    """守一道下限，防止目录被意外清空时上面的相等断言变得无意义。"""
    assert LIVE_REST > 0 and LIVE_MCP > 0


def test_api_md_documents_every_live_rest_route() -> None:
    """API.md 必须列出每一个真实 ``/api`` 路由——新增工具忘记写文档即 CI 失败。

    历史上 API.md 漏掉过 20+ 个真实端点（八字九大专项、astro event/lifespan 族等），
    Agent 只读文档便发现不了它们。这里把「文档覆盖全部路由」固化为断言。
    """
    live_routes = {
        r.path for r in app.routes if getattr(r, "path", "").startswith("/api")
    }
    api_md = (REPO_ROOT / "docs/API.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"/api/[A-Za-z0-9_/]+", api_md))
    missing = sorted(p for p in live_routes if p not in documented)
    assert (
        not missing
    ), "docs/API.md 漏列以下真实 REST 路由，请补到对应 §4 端点表：\n  " + "\n  ".join(
        missing
    )
