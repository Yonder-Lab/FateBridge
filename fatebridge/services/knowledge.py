"""
FateBridge bundled knowledge services.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fatebridge.core.export_parser import parse_export_content
from fatebridge.core.knowledge_store import (
    ToolValidationError,
    build_knowledge_registry,
    read_knowledge_entry,
)
from fatebridge.utils.helpers import handle_calculation_error


def _validation_error_payload(exc: ToolValidationError) -> Dict[str, Any]:
    # Include status_code/error_code so the HTTP transport (_execute_service)
    # maps this to a 400 instead of the default 500.
    return {
        "error": str(exc),
        "error_code": exc.code or "validation_error",
        "code": exc.code,
        "details": exc.details,
        "status_code": 400,
        "retryable": False,
    }


_QUERY_LABELS = {
    "key": "归一化主键",
    "object_a": "对象 A",
    "object_b": "对象 B",
    "jiang_name": "将神",
    "tian_branch": "天盘地支",
    "di_branch": "地盘地支",
}


def _render_snapshot_text(sections: List[tuple[str, List[str]]]) -> str:
    blocks: list[str] = []
    for title, lines in sections:
        body = "\n".join(line for line in lines if line is not None).strip()
        if body:
            blocks.append(f"[{title}]\n{body}")
        else:
            blocks.append(f"[{title}]")
    return "\n\n".join(blocks).strip()


def _build_snapshot_export(
    *,
    technique: str = "knowledge",
    snapshot_text: str,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return parse_export_content(
        technique=technique,
        content=snapshot_text,
        selected_sections=selected_sections,
    )


def _build_knowledge_registry_snapshot_text(
    registry: Dict[str, Any], *, domain: Optional[str]
) -> str:
    provenance = registry.get("provenance") or {}
    domains = registry.get("domains") or []
    overview_lines = [
        f"领域过滤：{domain or '全部'}",
        f"域数量：{len(domains)}",
        f"来源：{registry.get('source', '未提供')}",
    ]
    if registry.get("bundle_version") is not None:
        overview_lines.append(f"Bundle 版本：{registry['bundle_version']}")

    sections: List[tuple[str, List[str]]] = [("目录概览", overview_lines)]
    for item in domains:
        if not isinstance(item, dict):
            continue
        category_lines = [
            f"域：{item.get('domain', '未知')}",
            f"分类数：{len(item.get('categories') or [])}",
        ]
        for category in item.get("categories") or []:
            if not isinstance(category, dict):
                continue
            supports = "/".join(category.get("supports") or []) or "无"
            keys = "、".join(category.get("keys") or []) or "无"
            category_lines.append(
                f"{category.get('name', '未命名')}："
                f"{category.get('count', 0)} 条；"
                f"支持={supports}；"
                f"样例={keys}"
            )
        sections.append((item.get("domain", "未知"), category_lines))

    source_lines = [
        f"来源：{provenance.get('source_domain', registry.get('source', '未提供'))}",
    ]
    if provenance.get("bundle_version") is not None:
        source_lines.append(f"Bundle 版本：{provenance['bundle_version']}")
    if provenance.get("upstream_source_marker"):
        source_lines.append(f"上游标记：{provenance['upstream_source_marker']}")
    if provenance.get("build_timestamp"):
        source_lines.append(f"构建时间：{provenance['build_timestamp']}")
    sections.append(("来源", source_lines))
    return _render_snapshot_text(sections)


def _build_knowledge_snapshot_text(entry: Dict[str, Any]) -> str:
    query_normalized = entry.get("query_normalized") or {}
    provenance = entry.get("provenance") or {}
    query_lines = [
        f"领域：{entry.get('domain', '未知')}",
        f"分类：{entry.get('category', '未知')}",
        f"键：{entry.get('key', '未提供')}",
    ]
    if entry.get("title"):
        query_lines.append(f"标题：{entry['title']}")
    for field, label in _QUERY_LABELS.items():
        value = query_normalized.get(field)
        if value in {None, ""}:
            continue
        query_lines.append(f"{label}：{value}")

    body_lines: list[str] = []
    if entry.get("title"):
        body_lines.append(f"标题：{entry['title']}")
    tips = entry.get("tips")
    if isinstance(tips, list) and tips:
        for tip in tips:
            text = f"{tip}".strip()
            if not text:
                body_lines.append("")
                continue
            if text == "==":
                body_lines.append("")
                continue
            body_lines.append(text)
    else:
        for line in entry.get("lines") or []:
            text = f"{line}".strip()
            if text:
                body_lines.append(text)

    source_lines = [
        f"来源：{entry.get('source', '未提供')}",
        f"引文：{entry.get('citation', '未提供')}",
    ]
    if entry.get("bundle_version") is not None:
        source_lines.append(f"Bundle 版本：{entry['bundle_version']}")
    if provenance.get("upstream_source_marker"):
        source_lines.append(f"上游标记：{provenance['upstream_source_marker']}")
    if provenance.get("build_timestamp"):
        source_lines.append(f"构建时间：{provenance['build_timestamp']}")

    return _render_snapshot_text(
        [
            ("查询信息", query_lines),
            ("知识正文", body_lines),
            ("来源", source_lines),
        ]
    )


def calculate_knowledge_registry(
    *,
    domain: Optional[str] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Return bundled hover-knowledge domains and categories.
    """
    try:
        registry = build_knowledge_registry(domain=domain)
        snapshot_text = _build_knowledge_registry_snapshot_text(registry, domain=domain)
        snapshot_export = _build_snapshot_export(
            technique="knowledge_registry",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            **registry,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except ToolValidationError as exc:
        return _validation_error_payload(exc)
    except Exception as exc:
        return handle_calculation_error(exc, "知识目录")


def calculate_knowledge_read(
    *,
    domain: str,
    category: str,
    key: Optional[str] = None,
    selected_sections: Optional[List[str]] = None,
    aspect_degree: Optional[int | str] = None,
    object_a: Optional[str] = None,
    object_b: Optional[str] = None,
    jiang_name: Optional[str] = None,
    tian_branch: Optional[str] = None,
    di_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read one bundled hover-knowledge entry for astrology, 六壬, or 奇门.
    """
    try:
        entry = read_knowledge_entry(
            {
                "domain": domain,
                "category": category,
                "key": key,
                "aspect_degree": aspect_degree,
                "object_a": object_a,
                "object_b": object_b,
                "jiang_name": jiang_name,
                "tian_branch": tian_branch,
                "di_branch": di_branch,
            }
        )
        snapshot_text = _build_knowledge_snapshot_text(entry)
        snapshot_export = _build_snapshot_export(
            technique="knowledge",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            **entry,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except ToolValidationError as exc:
        return _validation_error_payload(exc)
    except Exception as exc:
        return handle_calculation_error(exc, "知识读取")
