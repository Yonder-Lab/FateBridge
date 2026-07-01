"""
Local technique helpers for FateBridge.

The local-technique layer (六爻 / 宿占 / 通蓍法 / 三式合一 / 参评 / 河洛 / 其他卜法),
implemented as offline pure-Python logic. Split by technique — a shared
western/local pseudo-chart substrate in ``chart`` plus one module per technique
— and this ``__init__`` is a thin facade re-exporting the public surface, so
callers keep importing from ``fatebridge.core.local_techniques`` unchanged.
"""

from __future__ import annotations

from .canping import build_canping_result
from .chart import (
    SU28_NAMES,
    _normalize_date_text,
    _normalize_time_text,
    build_pseudo_chart,
)
from .heluo import build_heluo_result
from .otherbu import build_otherbu_result
from .qimen import build_qimen_snapshot_text, build_qimen_with_options
from .sanshi import build_sanshiunited_result
from .sixyao import build_sixyao_result
from .suzhan import build_suzhan_result
from .tongshefa import build_tongshefa_result

__all__ = [
    "SU28_NAMES",
    "_normalize_date_text",
    "_normalize_time_text",
    "build_canping_result",
    "build_heluo_result",
    "build_otherbu_result",
    "build_pseudo_chart",
    "build_qimen_snapshot_text",
    "build_qimen_with_options",
    "build_sanshiunited_result",
    "build_sixyao_result",
    "build_suzhan_result",
    "build_tongshefa_result",
]
