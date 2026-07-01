"""服务层共享的快照构造原语（单一信源）。

历史上 ``_render_snapshot_text`` / ``_build_snapshot_export`` 在十余个 service
模块里逐字重复。它们的意图完全一致：把 ``[标题] + 正文`` 块拼成人类可读的
``snapshot_text``，再交给 ``parse_export_content`` 生成 ``snapshot_export``。
本模块把这套原语收敛到一处，供各 service 直接复用，避免再各自维护一份。

两种正文形态对应两个渲染函数：

- :func:`render_snapshot_text`  —— 正文已是单个字符串（八字独立盘、各西占工具）
- :func:`render_snapshot_lines` —— 正文是一组文本行（knowledge / divination / timing）

二者的换行与空行规则**保持与历史实现逐字一致**，以满足 golden 快照零漂移。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from fatebridge.core.export_parser import parse_export_content

__all__ = [
    "render_snapshot_text",
    "render_snapshot_lines",
    "build_snapshot_export",
]


def render_snapshot_text(sections: Sequence[Tuple[str, str]]) -> str:
    """把 ``(标题, 正文字符串)`` 块渲染为 ``[标题]`` + 正文，块与块之间空一行。

    正文为空（``strip()`` 后无内容）时只输出标题行。
    """
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body.strip():
            blocks.append(body)
        blocks.append("")
    return "\n".join(blocks).strip()


def render_snapshot_lines(sections: Sequence[Tuple[str, Sequence[str]]]) -> str:
    """把 ``(标题, 正文行列表)`` 块渲染为快照文本，块间以空行分隔。

    会丢弃 ``None`` 行；正文整体为空时只保留标题。
    """
    blocks: List[str] = []
    for title, lines in sections:
        body = "\n".join(line for line in lines if line is not None).strip()
        if body:
            blocks.append(f"[{title}]\n{body}")
        else:
            blocks.append(f"[{title}]")
    return "\n\n".join(blocks).strip()


def build_snapshot_export(
    *,
    technique: str,
    snapshot_text: str,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """``parse_export_content`` 的轻量包装，统一 service 层的调用形态。"""
    return parse_export_content(
        technique=technique,
        content=snapshot_text,
        selected_sections=selected_sections,
    )
