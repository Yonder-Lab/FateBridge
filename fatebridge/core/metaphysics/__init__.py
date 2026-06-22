"""
Offline Chinese metaphysics package for FateBridge.

Exposes structured Zi Wei, Liu Ren, Qi Men, Tai Yi, and Jin Kou outputs. The
package is split by technique — shared primitives in ``common`` plus one module
per system (``ziwei`` / ``liureng`` / ``qimen`` / ``taiyi`` / ``jinkou``) — and
this ``__init__`` is a thin facade re-exporting the public surface, so callers
keep importing from ``fatebridge.core.metaphysics`` unchanged.
"""

from __future__ import annotations

from .common import MetaphysicsSeed, kongwang_for_ganzhi
from .jinkou import build_jinkou_board
from .liureng import build_liureng_board, build_liureng_runyear
from .qimen import (
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    build_qimen_board,
    qimen_futou_for_ganzhi,
)
from .taiyi import build_taiyi_board
from .ziwei import (
    ZIWEI_SIHUA_RULES,
    build_ziwei_chart,
    build_ziwei_horoscope,
    build_ziwei_rules,
)

__all__ = [
    "MetaphysicsSeed",
    "QIMEN_DOOR_CODE_BY_DISPLAY",
    "QIMEN_DOOR_TO_TRIGRAM",
    "QIMEN_STAR_CODE_BY_DISPLAY",
    "ZIWEI_SIHUA_RULES",
    "build_jinkou_board",
    "build_liureng_board",
    "build_liureng_runyear",
    "build_qimen_board",
    "build_taiyi_board",
    "build_ziwei_chart",
    "build_ziwei_horoscope",
    "build_ziwei_rules",
    "kongwang_for_ganzhi",
    "qimen_futou_for_ganzhi",
]
