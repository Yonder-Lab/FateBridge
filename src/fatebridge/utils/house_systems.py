"""Swiss Ephemeris house-system code/alias mapping.

Extracted verbatim from utils/helpers.py (god-file split). Pure lookup
tables + normalisation — no numerical computation.
"""

from typing import Any, Dict, Optional, Tuple

# Swiss Ephemeris 宫位系统代码 ↔ 常见英文/中文别名
# Keys normalized via casefold + strip for lookup. Values are the
# single-letter codes accepted by swisseph / kerykeion.
_HOUSE_SYSTEM_ALIASES: Dict[str, str] = {
    # Placidus (default)
    "placidus": "P",
    "placidian": "P",
    "普拉西德": "P",
    "普拉西迪斯": "P",
    # Koch
    "koch": "K",
    "koh": "K",
    "柯赫": "K",
    "科赫": "K",
    # Equal house (A and E both map to Equal from Ascendant in swisseph)
    "equal": "A",
    "equalhouse": "A",
    "equal-house": "A",
    "equalasc": "A",
    "equal sign": "A",
    "等宫": "A",
    "等分制": "A",
    # Whole sign
    "whole": "W",
    "wholesign": "W",
    "whole-sign": "W",
    "whole_signs": "W",
    "whole signs": "W",
    "整宫": "W",
    "整宫制": "W",
    # Regiomontanus
    "regiomontanus": "R",
    "regio": "R",
    "雷乔蒙塔努斯": "R",
    # Campanus
    "campanus": "C",
    "坎帕努斯": "C",
    # Porphyry / Porphyrius
    "porphyry": "O",
    "porphyrius": "O",
    "波菲利": "O",
    # Alcabitius
    "alcabitius": "B",
    "alchabitius": "B",
    "alchabitus": "B",
    "阿卡比特斯": "B",
    # Morinus
    "morinus": "M",
    "莫里努斯": "M",
    # Topocentric / Polich-Page
    "topocentric": "T",
    "polich": "T",
    "polichpage": "T",
    "polich-page": "T",
    "polich page": "T",
    # Horizontal / Azimuthal
    "horizontal": "H",
    "azimuthal": "H",
    # Axial rotation / Meridian
    "axial": "X",
    "meridian": "X",
    "axial rotation": "X",
    # Vehlow Equal
    "vehlow": "V",
    "vehlowequal": "V",
    "vehlow equal": "V",
    # Equal anchored on the MC (10th cusp = MC; the core chart's equal_mc / code 8)
    "equalmc": "D",
    "equalmidheaven": "D",
    "天顶为10宫中点等宫制": "D",
    # Sripati (core chart code 7) — was missing, so "sripati" fell back to P
    "sripati": "S",
    # APC / Krusinski
    "apc": "Y",
    "krusinski": "U",
}

# Integer house-system codes (the ``hsys`` convention used by the core/relative
# chart family) mapped to the Swiss Ephemeris letters the western family uses.
# Mirrors RELATIVE_HOUSE_SYSTEM_SPECS in core/astrology.py so a single integer
# code means the same system on every surface.
_HOUSE_SYSTEM_CODE_TO_LETTER: Dict[int, str] = {
    0: "W",  # whole_sign
    1: "B",  # Alcabitus
    2: "R",  # Regiomontanus
    3: "P",  # Placidus
    4: "K",  # Koch
    5: "V",  # Vehlow Equal
    6: "T",  # Polich Page / Topocentric
    7: "S",  # Sripati
    8: "D",  # equal_mc
}

# Swiss Ephemeris letter -> (integer code or None, key, Chinese label). The
# label/key for the 0..8 codes mirror RELATIVE_HOUSE_SYSTEM_SPECS so the western
# tools report a house system the same way the core/relative charts do. Letters
# without a 0..8 code (Campanus, Porphyry, ...) still get a readable key+label
# with code=None.
_HOUSE_SYSTEM_LETTER_INFO: Dict[str, Tuple[Optional[int], str, str]] = {
    "W": (0, "whole_sign", "整宫制"),
    "B": (1, "alcabitus", "Alcabitus"),
    "R": (2, "regiomontanus", "Regiomontanus"),
    "P": (3, "placidus", "Placidus"),
    "K": (4, "koch", "Koch"),
    "V": (5, "vehlow_equal", "Vehlow Equal"),
    "T": (6, "polich_page", "Polich Page"),
    "S": (7, "sripati", "Sripati"),
    "D": (8, "equal_mc", "天顶为10宫中点等宫制"),
    "A": (None, "equal", "等宫制（上升起点）"),
    "C": (None, "campanus", "Campanus"),
    "O": (None, "porphyry", "Porphyry"),
    "M": (None, "morinus", "Morinus"),
    "H": (None, "horizontal", "Horizontal"),
    "X": (None, "meridian", "Meridian"),
    "Y": (None, "apc", "APC"),
    "U": (None, "krusinski", "Krusinski"),
}


def house_system_fields(house_system: Any, default: str = "P") -> Dict[str, Any]:
    """Describe a house system the same way on every surface.

    Returns a dict with the resolved Swiss Ephemeris ``house_system`` letter plus
    a numeric ``house_system_code`` (0..8, or ``None`` for letters outside that
    set) and a Chinese ``house_system_label_zh`` — mirroring the core/relative
    chart ``chart_profile`` keys so an agent reading any western result knows
    exactly which system produced it, regardless of how it was requested
    (integer code, SE letter, or key).
    """
    letter = normalize_house_system(house_system, default=default)
    code, _key, label_zh = _HOUSE_SYSTEM_LETTER_INFO.get(letter, (None, letter, letter))
    return {
        "house_system": letter,
        "house_system_code": code,
        "house_system_label_zh": label_zh,
    }


# Valid single-letter codes per kerykeion.schemas.kr_literals.HousesSystemIdentifier
_VALID_HOUSE_SYSTEM_CODES = frozenset(
    {
        "A",
        "B",
        "C",
        "D",
        "F",
        "H",
        "I",
        "i",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
    }
)


def normalize_house_system(house_system: Any, default: str = "P") -> str:
    """Map friendly names (placidus/koch/whole-sign/...) to SE single-letter codes.

    Accepts: single-letter codes (validated and passed through), full English
    names (case-insensitive), Chinese labels, and common variants. Unknown
    input falls back to the supplied default (Placidus by default).
    """
    if house_system is None:
        return default
    token = str(house_system).strip()
    if not token:
        return default
    # Integer code (the ``hsys`` 0..8 convention), passed as int or digit string,
    # so the same code resolves identically on the letter-string surfaces.
    if token.lstrip("+-").isdigit():
        code = int(token)
        if code in _HOUSE_SYSTEM_CODE_TO_LETTER:
            return _HOUSE_SYSTEM_CODE_TO_LETTER[code]
        return default
    # Single-letter code (preserves kerykeion's case-sensitive "i" vs "I")
    if len(token) == 1 and token in _VALID_HOUSE_SYSTEM_CODES:
        return token
    # Alias lookup (case-insensitive, collapse separators)
    lookup = token.casefold().replace("_", "").replace("-", "").replace(" ", "")
    if lookup in _HOUSE_SYSTEM_ALIASES:
        return _HOUSE_SYSTEM_ALIASES[lookup]
    # Re-match without normalization for Chinese labels that don't casefold
    if token in _HOUSE_SYSTEM_ALIASES:
        return _HOUSE_SYSTEM_ALIASES[token]
    # Upper-case fallback for codes given in wrong case (e.g. "p" → "P")
    upper = token.upper()
    if len(upper) == 1 and upper in _VALID_HOUSE_SYSTEM_CODES:
        return upper
    return default
