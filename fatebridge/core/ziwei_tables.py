"""
Static lookup tables ported from iztro (紫微斗数), kept separate from the
placement logic in ``metaphysics.py`` so the transcribed data is auditable.

Source of truth: iztro ``src/data/stars.ts`` -> ``STARS_INFO[*].brightness``.
Each brightness row is ordered "从寅开始" (starting at 寅), which is exactly
``fatebridge.utils.data.ZIWEI_BRANCH_SEQUENCE`` order, so no index translation
is needed.
Romanization map applied: miao=庙, wang=旺, de=得, li=利, ping=平, bu=不,
xian=陷; iztro's empty string '' (brightness not applicable at that branch)
becomes ``None`` here.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fatebridge.utils.data import ZIWEI_BRANCH_SEQUENCE

_BRANCH_INDEX = {branch: i for i, branch in enumerate(ZIWEI_BRANCH_SEQUENCE)}

_MUTAGEN_SUFFIXES: Tuple[str, ...] = ("化禄", "化权", "化科", "化忌")

# star name -> 12 brightness values (寅-indexed); None = not applicable.
ZIWEI_STAR_BRIGHTNESS: Dict[str, List[Optional[str]]] = {
    # --- 14 主星 ---
    "紫微": ["旺", "旺", "得", "旺", "庙", "庙", "旺", "旺", "得", "旺", "平", "庙"],
    "天机": ["得", "旺", "利", "平", "庙", "陷", "得", "旺", "利", "平", "庙", "陷"],
    "太阳": ["旺", "庙", "旺", "旺", "旺", "得", "得", "陷", "不", "陷", "陷", "不"],
    "武曲": ["得", "利", "庙", "平", "旺", "庙", "得", "利", "庙", "平", "旺", "庙"],
    "天同": ["利", "平", "平", "庙", "陷", "不", "旺", "平", "平", "庙", "旺", "不"],
    "廉贞": ["庙", "平", "利", "陷", "平", "利", "庙", "平", "利", "陷", "平", "利"],
    "天府": ["庙", "得", "庙", "得", "旺", "庙", "得", "旺", "庙", "得", "庙", "庙"],
    "太阴": ["旺", "陷", "陷", "陷", "不", "不", "利", "不", "旺", "庙", "庙", "庙"],
    "贪狼": ["平", "利", "庙", "陷", "旺", "庙", "平", "利", "庙", "陷", "旺", "庙"],
    "巨门": ["庙", "庙", "陷", "旺", "旺", "不", "庙", "庙", "陷", "旺", "旺", "不"],
    "天相": ["庙", "陷", "得", "得", "庙", "得", "庙", "陷", "得", "得", "庙", "庙"],
    "天梁": ["庙", "庙", "庙", "陷", "庙", "旺", "陷", "得", "庙", "陷", "庙", "旺"],
    "七杀": ["庙", "旺", "庙", "平", "旺", "庙", "庙", "庙", "庙", "平", "旺", "庙"],
    "破军": ["得", "陷", "旺", "平", "庙", "旺", "得", "陷", "旺", "平", "庙", "旺"],
    # --- 辅煞星 with brightness ---
    "文昌": ["陷", "利", "得", "庙", "陷", "利", "得", "庙", "陷", "利", "得", "庙"],
    "文曲": ["平", "旺", "得", "庙", "陷", "旺", "得", "庙", "陷", "旺", "得", "庙"],
    "火星": ["庙", "利", "陷", "得", "庙", "利", "陷", "得", "庙", "利", "陷", "得"],
    "铃星": ["庙", "利", "陷", "得", "庙", "利", "陷", "得", "庙", "利", "陷", "得"],
    "擎羊": [None, "陷", "庙", None, "陷", "庙", None, "陷", "庙", None, "陷", "庙"],
    "陀罗": ["陷", None, "庙", "陷", None, "庙", "陷", None, "庙", "陷", None, "庙"],
}


def lookup_star_brightness(star: str, branch: str) -> Optional[str]:
    """Return the brightness char for ``star`` at earthly ``branch``.

    Returns ``None`` when the star has no brightness, the branch is unknown,
    or the branch is one where the star's brightness is not applicable.
    """
    row = ZIWEI_STAR_BRIGHTNESS.get(star)
    idx = _BRANCH_INDEX.get(branch)
    if row is None or idx is None:
        return None
    return row[idx]


def split_star_mutagen(star_label: str) -> Tuple[str, Optional[str]]:
    """Split a possibly mutagen-suffixed star label.

    ``"紫微化科"`` -> ``("紫微", "化科")``; ``"天府"`` -> ``("天府", None)``.
    """
    for suffix in _MUTAGEN_SUFFIXES:
        if star_label.endswith(suffix):
            return star_label[: -len(suffix)], suffix
    return star_label, None
