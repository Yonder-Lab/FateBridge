"""场景路由文档必须恰好覆盖 CATALOG 全部工具——防止新增工具变成无场景归属的『闲置工具』。"""

import pathlib
import re

from fatebridge.services.tool_catalog import CATALOG

DOC = pathlib.Path(__file__).resolve().parent.parent / "docs" / "SCENARIO_ROUTING.md"


def _checklist_keys() -> set[str]:
    text = DOC.read_text(encoding="utf-8")
    assert "## 覆盖核对清单" in text, "SCENARIO_ROUTING.md 缺少『覆盖核对清单』节"
    section = text.split("## 覆盖核对清单", 1)[1]
    return set(re.findall(r"^- `([a-z0-9_]+)`", section, re.MULTILINE))


def test_checklist_covers_every_catalog_tool_exactly():
    listed = _checklist_keys()
    catalog = {spec.key for spec in CATALOG}
    missing = catalog - listed  # 工具存在但清单漏登记 = 新孤儿
    extra = listed - catalog  # 清单写了不存在的工具 = 笔误/已删
    assert not missing, f"未在场景路由清单登记的工具（闲置风险）: {sorted(missing)}"
    assert not extra, f"清单里存在但 CATALOG 已无的工具: {sorted(extra)}"


def test_checklist_has_no_duplicate_keys():
    text = DOC.read_text(encoding="utf-8")
    section = text.split("## 覆盖核对清单", 1)[1]
    keys = re.findall(r"^- `([a-z0-9_]+)`", section, re.MULTILINE)
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    assert not dupes, f"清单中有重复工具: {dupes}"
