"""
FateBridge bundled knowledge services.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fatebridge.core.knowledge_store import (
    ToolValidationError,
    build_knowledge_registry,
    read_knowledge_entry,
)
from fatebridge.utils.helpers import handle_calculation_error


def _validation_error_payload(exc: ToolValidationError) -> Dict[str, Any]:
    return {
        "error": str(exc),
        "code": exc.code,
        "details": exc.details,
    }


def calculate_knowledge_registry(
    *,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return bundled hover-knowledge domains and categories.
    """
    try:
        return build_knowledge_registry(domain=domain)
    except ToolValidationError as exc:
        return _validation_error_payload(exc)
    except Exception as exc:
        return handle_calculation_error(exc, "知识目录")


def calculate_knowledge_read(
    *,
    domain: str,
    category: str,
    key: Optional[str] = None,
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
        return read_knowledge_entry(
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
    except ToolValidationError as exc:
        return _validation_error_payload(exc)
    except Exception as exc:
        return handle_calculation_error(exc, "知识读取")
