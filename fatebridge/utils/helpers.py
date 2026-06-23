"""
Shared utility functions and models for FateBridge.
This module centralizes common functions used across fatebridge/api.py and
fatebridge/mcp_server.py.
"""

import json
import logging
import math
import re
import unicodedata
from builtins import TimeoutError as BuiltinTimeoutError
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, Tuple, cast

from dateutil import tz
from pydantic import BaseModel, Field, ValidationInfo, field_validator

logger = logging.getLogger(__name__)

DEPENDENCY_ERROR_CODE = "dependency_missing"
INTERNAL_ERROR_CODE = "internal_error"
TIMEOUT_ERROR_CODE = "timeout"
VALIDATION_ERROR_CODE = "validation_error"

DEPENDENCY_ERROR_HINTS = (
    "no module named",
    "module not found",
    "missing dependency",
    "dependency missing",
    "swisseph",
    "ephemeris",
    "kerykeion",
    "依赖缺失",
    "未安装",
)


DEFAULT_BIRTH_TIMEZONE = "Asia/Shanghai"
SOLAR_TIME_STRATEGY_APPARENT = "apparent"
SOLAR_TIME_STRATEGY_LONGITUDE_ONLY = "longitude_only"
PLACE_TEXT_SANITIZER = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")

PLACE_SPECIFICITY = {
    "province": 1,
    "special_region": 2,
    "city": 3,
    "municipality": 4,
}

DEFAULT_BIRTH_PLACE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "北京": ("beijing", "peking"),
    "上海": ("shanghai",),
    "天津": ("tianjin",),
    "重庆": ("chongqing",),
    "香港": ("hong kong", "hongkong"),
    "澳门": ("macau", "macao"),
    "台北": ("taipei",),
    "河北": ("hebei",),
    "山西": ("shanxi",),
    "辽宁": ("liaoning",),
    "吉林": ("jilin",),
    "黑龙江": ("heilongjiang", "hei longjiang"),
    "江苏": ("jiangsu",),
    "浙江": ("zhejiang",),
    "安徽": ("anhui",),
    "福建": ("fujian",),
    "江西": ("jiangxi",),
    "山东": ("shandong",),
    "河南": ("henan",),
    "湖北": ("hubei",),
    "湖南": ("hunan",),
    "广东": ("guangdong",),
    "海南": ("hainan",),
    "四川": ("sichuan",),
    "贵州": ("guizhou",),
    "云南": ("yunnan",),
    "陕西": ("shaanxi",),
    "甘肃": ("gansu",),
    "青海": ("qinghai",),
    "台湾": ("taiwan",),
    "内蒙古": ("neimenggu", "inner mongolia"),
    "广西": ("guangxi",),
    "西藏": ("xizang", "tibet"),
    "宁夏": ("ningxia",),
    "新疆": ("xinjiang",),
    "广州": ("guangzhou", "canton"),
    "深圳": ("shenzhen",),
    "杭州": ("hangzhou",),
    "宁波": ("ningbo",),
    "南京": ("nanjing",),
    "苏州": ("suzhou",),
    "武汉": ("wuhan",),
    "成都": ("chengdu",),
    "西安": ("xi'an", "xi an", "xian"),
    "乌鲁木齐": ("urumqi", "wulumuqi", "urumchi"),
    "石家庄": ("shijiazhuang",),
    "济南": ("jinan",),
    "青岛": ("qingdao", "tsingtao"),
    "郑州": ("zhengzhou",),
    "长沙": ("changsha",),
    "福州": ("fuzhou",),
    "厦门": ("xiamen", "amoy"),
    "合肥": ("hefei",),
    "南昌": ("nanchang",),
    "昆明": ("kunming",),
    "贵阳": ("guiyang",),
    "南宁": ("nanning",),
    "海口": ("haikou",),
    "呼和浩特": ("huhehaote", "hohhot"),
    "银川": ("yinchuan",),
    "兰州": ("lanzhou",),
    "西宁": ("xining",),
    "拉萨": ("lhasa", "lasa"),
    "喀什": ("kashi", "kashgar"),
    "纽约": ("new york", "newyork", "nyc"),
    "伦敦": ("london",),
    "东京": ("tokyo",),
    "悉尼": ("sydney",),
}


def normalize_birth_place_text(text: str) -> str:
    """Normalize Chinese/English place text for fuzzy offline matching."""
    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    return PLACE_TEXT_SANITIZER.sub("", normalized_text)


_MALE_GENDER_TOKENS = frozenset(
    {"男", "male", "m", "man", "boy", "1", "true", "阳", "乾"}
)
_FEMALE_GENDER_TOKENS = frozenset(
    {"女", "female", "f", "woman", "girl", "0", "false", "阴", "坤"}
)


def normalize_gender(gender: Any) -> str:
    """规范化性别输入为中文 "男"/"女"/"未知"。

    接受中英文、大小写、布尔型等多种输入形式，统一输出内部使用的中文标识。
    任何无法识别的输入返回 "未知"。
    """
    if gender is None:
        return "未知"
    if isinstance(gender, bool):
        return "男" if gender else "女"
    token = str(gender).strip().casefold()
    if not token:
        return "未知"
    if token in _MALE_GENDER_TOKENS:
        return "男"
    if token in _FEMALE_GENDER_TOKENS:
        return "女"
    return "未知"


def is_male(gender: Any) -> bool:
    """Convenience: True iff gender normalizes to 男."""
    return normalize_gender(gender) == "男"


def is_female(gender: Any) -> bool:
    """Convenience: True iff gender normalizes to 女."""
    return normalize_gender(gender) == "女"


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


# City-centre latitudes, keyed by the same canonical names used for longitudes
# below. Latitude lives here (rather than in a separate astrology-only table)
# so that one place resolves to longitude *and* latitude together: the BaZi
# true-solar path only needs longitude, but the astrology engine needs both, and
# keeping two parallel tables let them silently drift (a city had a longitude but
# no latitude, so an otherwise-resolvable place was rejected by the chart engine).
# Every entry in KNOWN_BIRTH_PLACE_ENTRIES must have a latitude here — enforced by
# an assertion after the catalog is built, so a new city can't be half-resolved.
KNOWN_BIRTH_PLACE_LATITUDES: Dict[str, float] = {
    # Municipalities and SARs
    "北京": 39.9042,
    "上海": 31.2304,
    "天津": 39.3434,
    "重庆": 29.5630,
    "香港": 22.3193,
    "澳门": 22.1987,
    "台北": 25.0330,
    # Province-level fallbacks
    "河北": 38.0428,
    "山西": 37.8706,
    "辽宁": 41.8057,
    "吉林": 43.8171,
    "黑龙江": 45.8038,
    "江苏": 32.0603,
    "浙江": 30.2741,
    "安徽": 31.8206,
    "福建": 26.0745,
    "江西": 28.6829,
    "山东": 36.6512,
    "河南": 34.7466,
    "湖北": 30.5454,
    "湖南": 28.2282,
    "广东": 23.1291,
    "海南": 20.0440,
    "四川": 30.5728,
    "贵州": 26.6470,
    "云南": 25.0389,
    "陕西": 34.3416,
    "甘肃": 36.0611,
    "青海": 36.6171,
    "台湾": 25.0330,
    "内蒙古": 40.8426,
    "广西": 22.8170,
    "西藏": 29.6525,
    "宁夏": 38.4872,
    "新疆": 43.8256,
    # Broader city coverage
    "广州": 23.1291,
    "深圳": 22.5431,
    "杭州": 30.2741,
    "宁波": 29.8683,
    "南京": 32.0603,
    "苏州": 31.2989,
    "武汉": 30.5928,
    "成都": 30.5728,
    "西安": 34.3416,
    "乌鲁木齐": 43.8256,
    "石家庄": 38.0428,
    "济南": 36.6512,
    "青岛": 36.0671,
    "郑州": 34.7473,
    "长沙": 28.2282,
    "福州": 26.0745,
    "厦门": 24.4798,
    "合肥": 31.8206,
    "南昌": 28.6829,
    "昆明": 25.0389,
    "贵阳": 26.6470,
    "南宁": 22.8170,
    "海口": 20.0440,
    "呼和浩特": 40.8426,
    "银川": 38.4872,
    "兰州": 36.0611,
    "西宁": 36.6171,
    "拉萨": 29.6525,
    "喀什": 39.4704,
    # Additional prefecture-level cities
    "咸阳": 34.3294,
    "宝鸡": 34.3614,
    "南通": 31.9802,
    "无锡": 31.4912,
    "常州": 31.7720,
    "徐州": 34.2058,
    "扬州": 32.3942,
    "盐城": 33.3496,
    "镇江": 32.1882,
    "泰州": 32.4558,
    "温州": 27.9939,
    "绍兴": 30.0023,
    "嘉兴": 30.7522,
    "台州": 28.6562,
    "金华": 29.0784,
    "湖州": 30.8927,
    "大连": 38.9140,
    "鞍山": 41.1086,
    "唐山": 39.6304,
    "保定": 38.8740,
    "邯郸": 36.6256,
    "沧州": 38.3045,
    "廊坊": 39.5375,
    "临沂": 35.1045,
    "潍坊": 36.7069,
    "淄博": 36.8131,
    "济宁": 35.4154,
    "泰安": 36.1944,
    "烟台": 37.4638,
    "威海": 37.5128,
    "洛阳": 34.6197,
    "南阳": 32.9908,
    "开封": 34.7972,
    "新乡": 35.3030,
    "许昌": 34.0357,
    "宜昌": 30.6919,
    "襄阳": 32.0090,
    "株洲": 27.8273,
    "湘潭": 27.8294,
    "衡阳": 26.8939,
    "岳阳": 29.3570,
    "泉州": 24.8741,
    "漳州": 24.5130,
    "赣州": 25.8453,
    "九江": 29.7050,
    "芜湖": 31.3526,
    "绵阳": 31.4677,
    "宜宾": 28.7513,
    "遵义": 27.7066,
    "桂林": 25.2736,
    "柳州": 24.3264,
    "佛山": 23.0218,
    "东莞": 23.0207,
    "珠海": 22.2710,
    "汕头": 23.3535,
    "惠州": 23.1117,
    # International cities
    "纽约": 40.7128,
    "伦敦": 51.5074,
    "东京": 35.6762,
    "悉尼": -33.8688,
}


def make_birth_place_entry(
    canonical_name: str,
    longitude: float,
    *,
    latitude: Optional[float] = None,
    timezone: str = DEFAULT_BIRTH_TIMEZONE,
    level: str = "city",
    aliases: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """Build one offline address-resolution entry.

    Latitude defaults to the co-located ``KNOWN_BIRTH_PLACE_LATITUDES`` table
    keyed by ``canonical_name`` (callers may still pass an explicit ``latitude``
    to override it for a boundary case).
    """
    resolved_latitude = (
        latitude
        if latitude is not None
        else KNOWN_BIRTH_PLACE_LATITUDES.get(canonical_name)
    )
    merged_aliases = tuple(
        dict.fromkeys(
            (
                canonical_name,
                *DEFAULT_BIRTH_PLACE_ALIASES.get(canonical_name, ()),
                *aliases,
            )
        )
    )
    normalized_aliases = tuple(
        dict.fromkeys(
            normalize_birth_place_text(alias)
            for alias in merged_aliases
            if normalize_birth_place_text(alias)
        )
    )
    return {
        "canonical_name": canonical_name,
        "longitude": longitude,
        "latitude": resolved_latitude,
        "timezone": timezone,
        "level": level,
        "specificity": PLACE_SPECIFICITY[level],
        "aliases": merged_aliases,
        "normalized_aliases": normalized_aliases,
    }


# Offline location hints for true solar time correction. This is still an
# approximate parser: it matches province/city aliases in free-form text and
# falls back to province-level coordinates when no known city appears.
KNOWN_BIRTH_PLACE_ENTRIES = (
    # Municipalities and SARs
    make_birth_place_entry("北京", 116.4074, level="municipality", aliases=("北京市",)),
    make_birth_place_entry("上海", 121.4737, level="municipality", aliases=("上海市",)),
    make_birth_place_entry("天津", 117.2000, level="municipality", aliases=("天津市",)),
    make_birth_place_entry("重庆", 106.5516, level="municipality", aliases=("重庆市",)),
    make_birth_place_entry(
        "香港",
        114.1694,
        timezone="Asia/Hong_Kong",
        level="special_region",
        aliases=("香港特别行政区",),
    ),
    make_birth_place_entry(
        "澳门",
        113.5439,
        timezone="Asia/Macau",
        level="special_region",
        aliases=("澳门特别行政区",),
    ),
    make_birth_place_entry(
        "台北",
        121.5654,
        timezone="Asia/Taipei",
        level="special_region",
        aliases=("臺北", "台北市", "臺北市"),
    ),
    # Province-level fallbacks
    make_birth_place_entry("河北", 114.5149, level="province", aliases=("河北省",)),
    make_birth_place_entry("山西", 112.5492, level="province", aliases=("山西省",)),
    make_birth_place_entry("辽宁", 123.4315, level="province", aliases=("辽宁省",)),
    make_birth_place_entry("吉林", 125.3235, level="province", aliases=("吉林省",)),
    make_birth_place_entry("黑龙江", 126.6424, level="province", aliases=("黑龙江省",)),
    make_birth_place_entry("江苏", 119.4210, level="province", aliases=("江苏省",)),
    make_birth_place_entry("浙江", 119.9572, level="province", aliases=("浙江省",)),
    make_birth_place_entry("安徽", 117.2272, level="province", aliases=("安徽省",)),
    make_birth_place_entry("福建", 119.2965, level="province", aliases=("福建省",)),
    make_birth_place_entry("江西", 115.8582, level="province", aliases=("江西省",)),
    make_birth_place_entry("山东", 117.1201, level="province", aliases=("山东省",)),
    make_birth_place_entry("河南", 113.6254, level="province", aliases=("河南省",)),
    make_birth_place_entry("湖北", 114.3419, level="province", aliases=("湖北省",)),
    make_birth_place_entry("湖南", 112.9388, level="province", aliases=("湖南省",)),
    make_birth_place_entry("广东", 113.2665, level="province", aliases=("广东省",)),
    make_birth_place_entry("海南", 110.3312, level="province", aliases=("海南省",)),
    make_birth_place_entry("四川", 104.0758, level="province", aliases=("四川省",)),
    make_birth_place_entry("贵州", 106.6302, level="province", aliases=("贵州省",)),
    make_birth_place_entry("云南", 102.8329, level="province", aliases=("云南省",)),
    make_birth_place_entry("陕西", 108.9398, level="province", aliases=("陕西省",)),
    make_birth_place_entry("甘肃", 103.8343, level="province", aliases=("甘肃省",)),
    make_birth_place_entry("青海", 101.7782, level="province", aliases=("青海省",)),
    make_birth_place_entry(
        "台湾",
        121.5654,
        timezone="Asia/Taipei",
        level="province",
        aliases=("台湾省", "臺灣", "臺灣省"),
    ),
    make_birth_place_entry(
        "内蒙古", 111.6708, level="province", aliases=("内蒙古自治区",)
    ),
    make_birth_place_entry(
        "广西", 108.3200, level="province", aliases=("广西", "广西壮族自治区")
    ),
    make_birth_place_entry("西藏", 91.1322, level="province", aliases=("西藏自治区",)),
    make_birth_place_entry(
        "宁夏", 106.2782, level="province", aliases=("宁夏回族自治区",)
    ),
    make_birth_place_entry(
        "新疆", 87.6168, level="province", aliases=("新疆", "新疆维吾尔自治区")
    ),
    # Broader city coverage
    make_birth_place_entry("广州", 113.2644, aliases=("广州市",)),
    make_birth_place_entry("深圳", 114.0579, aliases=("深圳市",)),
    make_birth_place_entry("杭州", 120.1551, aliases=("杭州市",)),
    make_birth_place_entry("宁波", 121.5503, aliases=("宁波市",)),
    make_birth_place_entry("南京", 118.7969, aliases=("南京市",)),
    make_birth_place_entry("苏州", 120.5853, aliases=("苏州市",)),
    make_birth_place_entry("武汉", 114.3054, aliases=("武汉市",)),
    make_birth_place_entry("成都", 104.0665, aliases=("成都市",)),
    make_birth_place_entry("西安", 108.9398, aliases=("西安市",)),
    make_birth_place_entry("乌鲁木齐", 87.6168, aliases=("乌鲁木齐市",)),
    make_birth_place_entry("石家庄", 114.5149, aliases=("石家庄市",)),
    make_birth_place_entry("济南", 117.1201, aliases=("济南市",)),
    make_birth_place_entry("青岛", 120.3826, aliases=("青岛市",)),
    make_birth_place_entry("郑州", 113.6254, aliases=("郑州市",)),
    make_birth_place_entry("长沙", 112.9388, aliases=("长沙市",)),
    make_birth_place_entry("福州", 119.2965, aliases=("福州市",)),
    make_birth_place_entry("厦门", 118.0894, aliases=("厦门市",)),
    make_birth_place_entry("合肥", 117.2272, aliases=("合肥市",)),
    make_birth_place_entry("南昌", 115.8582, aliases=("南昌市",)),
    make_birth_place_entry("昆明", 102.8329, aliases=("昆明市",)),
    make_birth_place_entry("贵阳", 106.6302, aliases=("贵阳市",)),
    make_birth_place_entry("南宁", 108.3200, aliases=("南宁市",)),
    make_birth_place_entry("海口", 110.3312, aliases=("海口市",)),
    make_birth_place_entry("呼和浩特", 111.6708, aliases=("呼和浩特市",)),
    make_birth_place_entry("银川", 106.2782, aliases=("银川市",)),
    make_birth_place_entry("兰州", 103.8343, aliases=("兰州市",)),
    make_birth_place_entry("西宁", 101.7782, aliases=("西宁市",)),
    make_birth_place_entry("拉萨", 91.1322, aliases=("拉萨市",)),
    make_birth_place_entry("喀什", 75.9898, aliases=("喀什地区", "喀什市")),
    # Additional prefecture-level cities (substring match also resolves the
    # "<city>市<district>区" forms, e.g. "咸阳市秦都区" -> 咸阳). Longitudes are
    # city-centre values; for boundary-time births pass birth_longitude exactly.
    make_birth_place_entry("咸阳", 108.7050, aliases=("咸阳市",)),
    make_birth_place_entry("宝鸡", 107.2380, aliases=("宝鸡市",)),
    make_birth_place_entry("南通", 120.8943, aliases=("南通市",)),
    make_birth_place_entry("无锡", 120.3019, aliases=("无锡市",)),
    make_birth_place_entry("常州", 119.9740, aliases=("常州市",)),
    make_birth_place_entry("徐州", 117.1840, aliases=("徐州市",)),
    make_birth_place_entry("扬州", 119.4215, aliases=("扬州市",)),
    make_birth_place_entry("盐城", 120.1398, aliases=("盐城市",)),
    make_birth_place_entry("镇江", 119.4250, aliases=("镇江市",)),
    make_birth_place_entry("泰州", 119.9150, aliases=("泰州市",)),
    make_birth_place_entry("温州", 120.6994, aliases=("温州市",)),
    make_birth_place_entry("绍兴", 120.5820, aliases=("绍兴市",)),
    make_birth_place_entry("嘉兴", 120.7555, aliases=("嘉兴市",)),
    make_birth_place_entry("台州", 121.4287, aliases=("台州市",)),
    make_birth_place_entry("金华", 119.6494, aliases=("金华市",)),
    make_birth_place_entry("湖州", 120.0865, aliases=("湖州市",)),
    make_birth_place_entry("大连", 121.6147, aliases=("大连市",)),
    make_birth_place_entry("鞍山", 122.9950, aliases=("鞍山市",)),
    make_birth_place_entry("唐山", 118.1758, aliases=("唐山市",)),
    make_birth_place_entry("保定", 115.4646, aliases=("保定市",)),
    make_birth_place_entry("邯郸", 114.4900, aliases=("邯郸市",)),
    make_birth_place_entry("沧州", 116.8388, aliases=("沧州市",)),
    make_birth_place_entry("廊坊", 116.7038, aliases=("廊坊市",)),
    make_birth_place_entry("临沂", 118.3563, aliases=("临沂市",)),
    make_birth_place_entry("潍坊", 119.1070, aliases=("潍坊市",)),
    make_birth_place_entry("淄博", 118.0480, aliases=("淄博市",)),
    make_birth_place_entry("济宁", 116.5871, aliases=("济宁市",)),
    make_birth_place_entry("泰安", 117.0890, aliases=("泰安市",)),
    make_birth_place_entry("烟台", 121.4479, aliases=("烟台市",)),
    make_birth_place_entry("威海", 122.1201, aliases=("威海市",)),
    make_birth_place_entry("洛阳", 112.4540, aliases=("洛阳市",)),
    make_birth_place_entry("南阳", 112.5288, aliases=("南阳市",)),
    make_birth_place_entry("开封", 114.3074, aliases=("开封市",)),
    make_birth_place_entry("新乡", 113.9268, aliases=("新乡市",)),
    make_birth_place_entry("许昌", 113.8260, aliases=("许昌市",)),
    make_birth_place_entry("宜昌", 111.2865, aliases=("宜昌市",)),
    make_birth_place_entry("襄阳", 112.1220, aliases=("襄阳市", "襄樊")),
    make_birth_place_entry("株洲", 113.1340, aliases=("株洲市",)),
    make_birth_place_entry("湘潭", 112.9440, aliases=("湘潭市",)),
    make_birth_place_entry("衡阳", 112.6072, aliases=("衡阳市",)),
    make_birth_place_entry("岳阳", 113.1290, aliases=("岳阳市",)),
    make_birth_place_entry("泉州", 118.5894, aliases=("泉州市",)),
    make_birth_place_entry("漳州", 117.6471, aliases=("漳州市",)),
    make_birth_place_entry("赣州", 114.9400, aliases=("赣州市",)),
    make_birth_place_entry("九江", 115.9920, aliases=("九江市",)),
    make_birth_place_entry("芜湖", 118.4330, aliases=("芜湖市",)),
    make_birth_place_entry("绵阳", 104.6790, aliases=("绵阳市",)),
    make_birth_place_entry("宜宾", 104.6430, aliases=("宜宾市",)),
    make_birth_place_entry("遵义", 106.9270, aliases=("遵义市",)),
    make_birth_place_entry("桂林", 110.2900, aliases=("桂林市",)),
    make_birth_place_entry("柳州", 109.4280, aliases=("柳州市",)),
    make_birth_place_entry("佛山", 113.1220, aliases=("佛山市",)),
    make_birth_place_entry("东莞", 113.7460, aliases=("东莞市",)),
    make_birth_place_entry("珠海", 113.5530, aliases=("珠海市",)),
    make_birth_place_entry("汕头", 116.6820, aliases=("汕头市",)),
    make_birth_place_entry("惠州", 114.4160, aliases=("惠州市",)),
    # International cities retained from the previous version
    make_birth_place_entry(
        "纽约", -74.0060, timezone="America/New_York", aliases=("纽约市",)
    ),
    make_birth_place_entry("伦敦", -0.1278, timezone="Europe/London"),
    make_birth_place_entry(
        "东京", 139.6917, timezone="Asia/Tokyo", aliases=("东京都",)
    ),
    make_birth_place_entry(
        "悉尼", 151.2093, timezone="Australia/Sydney", aliases=("悉尼市",)
    ),
)

# Drift guard: every catalogued place must resolve to a latitude too, otherwise
# the astrology engine would reject an address the BaZi engine happily accepts.
_PLACES_MISSING_LATITUDE = [
    entry["canonical_name"]
    for entry in KNOWN_BIRTH_PLACE_ENTRIES
    if entry["latitude"] is None
]
assert not _PLACES_MISSING_LATITUDE, (
    "KNOWN_BIRTH_PLACE_LATITUDES is missing entries for: "
    f"{_PLACES_MISSING_LATITUDE}"
)


@dataclass(frozen=True)
class BirthPlaceResolution:
    """One resolved address candidate from the offline catalog."""

    canonical_name: Optional[str]
    longitude: Optional[float]
    latitude: Optional[float]
    timezone: Optional[str]
    source: Optional[str]
    level: Optional[str]


@dataclass(frozen=True)
class NormalizedBirthTime:
    """Normalized birth-time details used across calculation services."""

    input_datetime: datetime
    corrected_datetime: datetime
    timezone: str
    longitude: Optional[float]
    longitude_source: Optional[str]
    resolved_place: Optional[str]
    resolution_level: Optional[str]
    longitude_correction_minutes: float
    equation_of_time_minutes: float
    daylight_saving_minutes: float
    total_correction_minutes: float
    applied: bool
    # 仅当经度是从 birth_place 推断、且只匹配到省级中心点（而非具体市县）时填充：
    # 告知调用方此次校正用的是省级近似经度，可能与实际地点相差数分钟。
    resolution_advisory: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe summary for API responses."""
        summary: Dict[str, Any] = {
            "applied": self.applied,
            "timezone": self.timezone,
            "longitude": self.longitude,
            "longitude_source": self.longitude_source,
            "resolved_place": self.resolved_place,
            "resolution_level": self.resolution_level,
            "longitude_correction_minutes": round(self.longitude_correction_minutes, 2),
            "equation_of_time_minutes": round(self.equation_of_time_minutes, 2),
            "daylight_saving_minutes": round(self.daylight_saving_minutes, 2),
            "total_correction_minutes": round(self.total_correction_minutes, 2),
        }
        # 仅在有提示时才加入此键：保持无歧义场景（用户显式传经度、市县级匹配）
        # 的输出结构不变，避免给既有消费者凭空多一个 null 字段。
        if self.resolution_advisory is not None:
            summary["resolution_advisory"] = self.resolution_advisory
        return summary


# ============================================================================
# Data Models
# ============================================================================


class PersonInfo(BaseModel):
    """个人信息模型"""

    name: Optional[str] = Field(default="未提供", description="姓名（可选）")
    birth_year: int = Field(ge=1900, le=2100, description="出生年份，如2000")
    birth_month: int = Field(ge=1, le=12, description="出生月份 1-12")
    birth_day: int = Field(ge=1, le=31, description="出生日期 1-31")
    birth_hour: int = Field(ge=0, le=23, description="出生时辰 0-23")
    birth_minute: int = Field(default=0, ge=0, le=59, description="出生分钟 0-59")
    gender: Optional[str] = Field(default="未知", description="性别（可选）")
    birth_place: Optional[str] = Field(default="未提供", description="出生地（可选）")
    birth_timezone: Optional[str] = Field(
        default=None, description="出生时区（IANA 名称或 UTC 偏移）"
    )
    birth_longitude: Optional[float] = Field(
        default=None, ge=-180, le=180, description="出生地经度（可选）"
    )
    use_true_solar_time: bool = Field(default=False, description="是否启用真太阳时修正")

    @field_validator("birth_day")
    @classmethod
    def validate_birth_day(cls, v: int, info: ValidationInfo) -> int:
        """验证日期是否有效"""
        month = info.data.get("birth_month")
        year = info.data.get("birth_year")

        if month and year:
            max_day = monthrange(year, month)[1]
            if v > max_day:
                raise ValueError(
                    f"无效的日期: {year}年{month}月{v}日 " f"(该月只有{max_day}天)"
                )
        return v


# ============================================================================
# Helper Functions
# ============================================================================


def create_person_info(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    *,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    birth_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> PersonInfo:
    """创建PersonInfo对象的工具函数

    Args:
        birth_year: 出生年份
        birth_month: 出生月份
        birth_day: 出生日期
        birth_hour: 出生时辰
        name: 姓名
        gender: 性别
        birth_place: 出生地
        birth_minute: 出生分钟
        birth_timezone: 出生时区
        birth_longitude: 出生地经度
        use_true_solar_time: 是否启用真太阳时修正

    Returns:
        PersonInfo对象
    """
    return PersonInfo(
        name=name,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
        gender=gender,
        birth_place=birth_place,
        birth_timezone=birth_timezone,
        birth_longitude=birth_longitude,
        use_true_solar_time=use_true_solar_time,
    )


def create_birth_datetime(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_minute: int = 0,
) -> datetime:
    """创建出生时间datetime对象的工具函数

    Args:
        birth_year: 出生年份
        birth_month: 出生月份
        birth_day: 出生日期
        birth_hour: 出生时辰
        birth_minute: 出生分钟

    Returns:
        datetime对象

    Raises:
        ValueError: 如果日期无效
    """
    try:
        return datetime(birth_year, birth_month, birth_day, birth_hour, birth_minute)
    except ValueError as e:
        error_msg = (
            "Invalid birth date: "
            f"{birth_year}-{birth_month:02d}-{birth_day:02d} "
            f"{birth_hour:02d}:{birth_minute:02d}"
        )
        logger.warning(error_msg)
        raise ValueError(error_msg) from e


def resolve_birth_place_context(
    birth_place: Optional[str],
) -> BirthPlaceResolution:
    """Resolve longitude/timezone hints from a free-form birth place string."""
    if not birth_place or birth_place == "未提供":
        return BirthPlaceResolution(None, None, None, None, None, None)

    normalized_place = normalize_birth_place_text(birth_place)
    return _resolve_birth_place_context_cached(normalized_place)


@lru_cache(maxsize=256)
def _resolve_birth_place_context_cached(
    normalized_place: str,
) -> BirthPlaceResolution:
    """Cache offline place resolution because it is deterministic and reusable."""
    best_match: Optional[Tuple[int, int, int, int, Dict[str, Any]]] = None
    for entry in KNOWN_BIRTH_PLACE_ENTRIES:
        for alias in entry["normalized_aliases"]:
            if alias and alias in normalized_place:
                score = (
                    entry["specificity"],
                    len(alias),
                    len(entry["canonical_name"]),
                    1,
                )
                if best_match is None or score > best_match[:4]:
                    best_match = (*score, entry)

    if best_match is None:
        return BirthPlaceResolution(None, None, None, None, None, None)

    entry = best_match[4]
    return BirthPlaceResolution(
        canonical_name=entry["canonical_name"],
        longitude=entry["longitude"],
        latitude=entry["latitude"],
        timezone=entry["timezone"],
        source="birth_place",
        level=entry["level"],
    )


def _invalid_timezone_message(value: str) -> str:
    """Build an actionable error that names every accepted timezone format."""
    return (
        f"Invalid birth timezone: {value!r}. "
        "Use an IANA name (e.g. 'Asia/Shanghai'), a UTC offset "
        "(e.g. '+08:00' or 'UTC+8'), or a bare offset in hours "
        "(e.g. '8', '-5', '5.5')."
    )


def parse_timezone_name(timezone_name: str) -> tzinfo:
    """Parse IANA names, UTC±HH[:MM] offsets, or bare hour offsets into a tzinfo."""
    timezone_name = timezone_name.strip()
    return _parse_timezone_name_cached(timezone_name)


@lru_cache(maxsize=128)
def _parse_timezone_name_cached(timezone_name: str) -> tzinfo:
    """Cache parsed tzinfo objects for repeated birth-time normalization."""
    timezone_info = tz.gettz(timezone_name)
    if timezone_info is not None:
        return cast(tzinfo, timezone_info)

    stripped = timezone_name.strip()

    # Accept a bare numeric UTC offset in hours — e.g. "8", "+8", "-5", "5.5"
    # ("5.5" -> +05:30, matching India). This is the most natural thing a user
    # types for a timezone field, so treat it as UTC+N rather than rejecting it.
    # Bound to a sane range so junk like "1e3"/"inf"/"nan" still fails loudly.
    try:
        offset_hours = float(stripped)
    except ValueError:
        pass
    else:
        if -15.0 <= offset_hours <= 15.0:
            offset_seconds = int(round(offset_hours * 3600))
            return cast(tzinfo, tz.tzoffset(stripped, offset_seconds))
        raise ValueError(_invalid_timezone_message(timezone_name))

    normalized_name = stripped.upper().replace("GMT", "UTC")
    if normalized_name.startswith(("+", "-")):
        normalized_name = f"UTC{normalized_name}"
    if normalized_name == "UTC":
        return cast(tzinfo, tz.tzutc())

    if not normalized_name.startswith("UTC") or len(normalized_name) < 5:
        raise ValueError(_invalid_timezone_message(timezone_name))

    sign = normalized_name[3]
    if sign not in {"+", "-"}:
        raise ValueError(_invalid_timezone_message(timezone_name))

    remainder = normalized_name[4:]
    if ":" in remainder:
        hour_text, minute_text = remainder.split(":", 1)
    else:
        hour_text, minute_text = remainder, "0"

    try:
        hours = int(hour_text)
        minutes = int(minute_text)
    except ValueError as error:
        raise ValueError(_invalid_timezone_message(timezone_name)) from error

    direction = 1 if sign == "+" else -1
    offset_seconds = direction * ((hours * 60 + minutes) * 60)
    return cast(tzinfo, tz.tzoffset(timezone_name, offset_seconds))


def calculate_equation_of_time_minutes(target_datetime: datetime) -> float:
    """Approximate equation of time in minutes for a given date."""
    day_of_year = target_datetime.timetuple().tm_yday
    b = 2 * math.pi * (day_of_year - 81) / 364
    return 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)


def calculate_solar_time_adjustment(
    input_datetime: datetime,
    timezone_name: str,
    longitude: float,
    *,
    strategy: str = SOLAR_TIME_STRATEGY_APPARENT,
) -> Dict[str, float]:
    """Calculate solar-time correction details for a local civil datetime."""
    timezone_info = parse_timezone_name(timezone_name)
    aware_datetime = input_datetime.replace(tzinfo=timezone_info)
    utc_offset = aware_datetime.utcoffset()
    if utc_offset is None:
        raise ValueError(_invalid_timezone_message(timezone_name))

    daylight_saving = aware_datetime.dst() or timedelta(0)
    standard_offset = utc_offset - daylight_saving
    standard_meridian = (standard_offset.total_seconds() / 3600) * 15
    longitude_correction_minutes = 4 * (longitude - standard_meridian)
    # Chinese metaphysics conventions use 标准时 (standard civil time) as the
    # base before applying longitude / equation-of-time corrections. When the
    # user's wall-clock input was recorded during a DST period (e.g. China's
    # 夏令时 1986-1991, historic European/US DST dates), the naive clock is an
    # hour ahead of standard time. We subtract the DST amount here so that the
    # resulting normalized datetime reflects true solar time anchored at the
    # standard meridian — otherwise users born near 时辰 boundaries during a
    # DST period land in the wrong hour pillar.
    dst_offset_minutes = daylight_saving.total_seconds() / 60

    if strategy == SOLAR_TIME_STRATEGY_APPARENT:
        equation_of_time_minutes = calculate_equation_of_time_minutes(input_datetime)
        total_correction_minutes = (
            longitude_correction_minutes + equation_of_time_minutes - dst_offset_minutes
        )
    elif strategy == SOLAR_TIME_STRATEGY_LONGITUDE_ONLY:
        # Some local metaphysics techniques use a longitude-only civil-time
        # correction without the equation-of-time term. The sign of the
        # longitude correction must match the SOLAR_TIME_STRATEGY_APPARENT
        # branch: east of the standard meridian -> solar time runs AHEAD of
        # the wall clock, so we ADD longitude_correction_minutes (which is
        # positive east of meridian) and subtract the DST offset to rebase
        # onto standard time before applying the longitude delta.
        equation_of_time_minutes = 0.0
        total_correction_minutes = longitude_correction_minutes - dst_offset_minutes
    else:
        raise ValueError(f"Unsupported solar time strategy: {strategy}")

    return {
        "standard_meridian": standard_meridian,
        "longitude_correction_minutes": longitude_correction_minutes,
        "equation_of_time_minutes": equation_of_time_minutes,
        "daylight_saving_minutes": dst_offset_minutes,
        "total_correction_minutes": total_correction_minutes,
    }


def normalize_birth_time(
    person: PersonInfo,
    *,
    solar_time_strategy: str = SOLAR_TIME_STRATEGY_APPARENT,
) -> NormalizedBirthTime:
    """Normalize birth time and optionally apply true solar time correction."""
    input_datetime = create_birth_datetime(
        person.birth_year,
        person.birth_month,
        person.birth_day,
        person.birth_hour,
        person.birth_minute,
    )

    inferred_place = resolve_birth_place_context(person.birth_place)

    explicit_timezone = person.birth_timezone or inferred_place.timezone
    timezone_name = explicit_timezone or DEFAULT_BIRTH_TIMEZONE

    longitude = person.birth_longitude
    longitude_source = "birth_longitude" if longitude is not None else None
    resolved_place = None if longitude is not None else inferred_place.canonical_name
    resolution_level = None if longitude is not None else inferred_place.level
    if longitude is None and inferred_place.longitude is not None:
        longitude = inferred_place.longitude
        longitude_source = inferred_place.source

    # When no timezone is explicitly supplied but a longitude is known, assume the
    # given wall-clock time is local standard time at the zone nearest that
    # longitude — rather than defaulting to Asia/Shanghai's 120°E meridian, which
    # makes true-solar-time correction badly wrong for non-China longitudes.
    if explicit_timezone is None and longitude is not None:
        zone_hours = max(-12, min(14, int(round(longitude / 15.0))))
        timezone_name = f"{'+' if zone_hours >= 0 else '-'}{abs(zone_hours):02d}:00"

    parse_timezone_name(timezone_name)

    if not person.use_true_solar_time:
        return NormalizedBirthTime(
            input_datetime=input_datetime,
            corrected_datetime=input_datetime,
            timezone=timezone_name,
            longitude=longitude,
            longitude_source=longitude_source,
            resolved_place=resolved_place,
            resolution_level=resolution_level,
            longitude_correction_minutes=0.0,
            equation_of_time_minutes=0.0,
            daylight_saving_minutes=0.0,
            total_correction_minutes=0.0,
            applied=False,
        )

    if longitude is None:
        place = person.birth_place
        if place and place != "未提供":
            raise ValueError(
                f"True solar time correction needs a longitude, but birth_place "
                f"{place!r} is not in the offline place catalog. Pass "
                "birth_longitude explicitly (east positive, e.g. 108.71 for 咸阳), "
                "or use a catalogued city name."
            )
        raise ValueError(
            "True solar time correction needs a longitude. Pass birth_longitude "
            "explicitly (east positive), or a catalogued birth_place city name."
        )

    adjustment = calculate_solar_time_adjustment(
        input_datetime,
        timezone_name,
        longitude,
        strategy=solar_time_strategy,
    )
    longitude_correction_minutes = adjustment["longitude_correction_minutes"]
    equation_of_time_minutes = adjustment["equation_of_time_minutes"]
    daylight_saving_minutes = adjustment.get("daylight_saving_minutes", 0.0)
    total_correction_minutes = adjustment["total_correction_minutes"]
    corrected_datetime = input_datetime + timedelta(minutes=total_correction_minutes)

    # 经度来自 birth_place 且只匹配到省级中心点时，校正用的是省级近似经度（如
    # 「江苏省南通市海安市」只识别出省份「江苏」119.42°，与海安实际 ~120.47° 相差
    # 约 1°≈4 分钟）。此时给出明确提示，让调用方知道精度限制并可改传 birth_longitude，
    # 而不是把省级近似当成市县级精度静默使用。
    resolution_advisory = None
    if longitude_source != "birth_longitude" and resolution_level == "province":
        resolution_advisory = (
            f"出生地『{person.birth_place}』未匹配到具体市县，仅按省级"
            f"（{resolved_place}）经度 {longitude:.2f}° 做真太阳时校正，"
            "可能与实际地点相差数分钟；如需精确请改传 birth_longitude。"
        )

    return NormalizedBirthTime(
        input_datetime=input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=timezone_name,
        longitude=longitude,
        longitude_source=longitude_source,
        resolved_place=resolved_place,
        resolution_level=resolution_level,
        longitude_correction_minutes=longitude_correction_minutes,
        equation_of_time_minutes=equation_of_time_minutes,
        daylight_saving_minutes=daylight_saving_minutes,
        total_correction_minutes=total_correction_minutes,
        applied=True,
        resolution_advisory=resolution_advisory,
    )


def format_birth_datetime_display(
    birth_datetime: datetime, include_minutes: bool = False
) -> str:
    """Format birth datetime for user-facing API responses."""
    if include_minutes:
        return birth_datetime.strftime("%Y年%m月%d日 %H时%M分")
    return birth_datetime.strftime("%Y年%m月%d日 %H时")


def handle_calculation_error(error: Exception, operation: str) -> Dict[str, Any]:
    """统一的错误处理函数

    Logs full error server-side but returns generic message to client
    for security reasons.

    Args:
        error: 异常对象
        operation: 操作名称

    Returns:
        包含错误信息的字典（不暴露内部细节）
    """
    error_text = str(error).strip()
    normalized = error_text.casefold()

    if isinstance(error, (ImportError, ModuleNotFoundError)) or any(
        hint in normalized for hint in DEPENDENCY_ERROR_HINTS
    ):
        logger.error(f"{operation} failed: {error_text}", exc_info=True)
        return {
            "error": f"{operation}所需依赖缺失，请检查运行环境",
            "error_code": DEPENDENCY_ERROR_CODE,
            "status_code": 503,
            "retryable": False,
        }

    if isinstance(error, (TimeoutError, BuiltinTimeoutError)):
        logger.error(f"{operation} failed: {error_text}", exc_info=True)
        return {
            "error": f"{operation}处理超时，请稍后重试",
            "error_code": TIMEOUT_ERROR_CODE,
            "status_code": 504,
            "retryable": True,
        }

    if isinstance(error, ValueError):
        # User/domain input rejection (HTTP 400), not a system fault. Log a
        # concise warning without a stack trace — dumping a full traceback for
        # every "invalid date" or "unknown hexagram name" floods the error log
        # with noise that looks like a crash.
        logger.warning(f"{operation} rejected invalid input: {error_text}")
        return {
            "error": error_text or f"{operation}输入无效",
            "error_code": VALIDATION_ERROR_CODE,
            "status_code": 400,
            "retryable": False,
        }

    # Unexpected internal fault — this is the one case that warrants a full
    # stack trace at ERROR level for server-side diagnosis.
    logger.error(f"{operation} failed: {error_text}", exc_info=True)
    return {
        "error": f"{operation}暂时不可用，请稍后重试",
        "error_code": INTERNAL_ERROR_CODE,
        "status_code": 500,
        "retryable": True,
    }


def calculation_guard(
    operation: str,
) -> Callable[[Callable[..., Dict[str, Any]]], Callable[..., Dict[str, Any]]]:
    """将服务函数包裹为"任何异常都转成标准错误信封"的形式。

    与此前散落在 ~50 个服务调用点的手写写法在行为上完全一致::

        try:
            ...函数体...
        except Exception as exc:
            return handle_calculation_error(exc, operation)

    只适用于"整个函数体都在 try 内、except 是最后一步"的场景；
    若函数在 try 之前另有语句，请勿迁移（包裹整函数会吞掉本应向上抛出的异常）。

    Args:
        operation: 操作名称，原样透传给 :func:`handle_calculation_error`
            （它是错误信封的一部分，必须与迁移前的字符串逐字一致）。
    """

    def decorator(
        func: Callable[..., Dict[str, Any]],
    ) -> Callable[..., Dict[str, Any]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - 故意宽捕获，与迁移前行为一致
                return handle_calculation_error(exc, operation)

        return wrapper

    return decorator


def create_pillar_dict(
    pillars: Dict[str, Tuple[str, str]],
) -> Dict[str, Dict[str, str]]:
    """创建标准化的四柱字典格式

    Args:
        pillars: 四柱数据

    Returns:
        标准化的四柱字典
    """
    return {
        "year": {"stem": pillars["year"][0], "branch": pillars["year"][1]},
        "month": {"stem": pillars["month"][0], "branch": pillars["month"][1]},
        "day": {"stem": pillars["day"][0], "branch": pillars["day"][1]},
        "hour": {"stem": pillars["hour"][0], "branch": pillars["hour"][1]},
    }


def _prepare_json_response_payload(
    data: Dict[str, Any],
    *,
    include_snapshot_text: bool,
) -> Dict[str, Any]:
    if include_snapshot_text or "snapshot_text" not in data:
        return data

    payload = dict(data)
    payload.pop("snapshot_text", None)
    return payload


def format_json_response(
    data: Dict[str, Any],
    *,
    compact: bool = True,
    include_snapshot_text: bool = True,
) -> str:
    """统一的JSON格式化函数

    Args:
        data: 要格式化的数据字典
        compact: 是否输出紧凑 JSON
        include_snapshot_text: 是否保留 snapshot_text 字段

    Returns:
        格式化的JSON字符串
    """
    payload = _prepare_json_response_payload(
        data,
        include_snapshot_text=include_snapshot_text,
    )
    if compact:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def get_current_analysis_date(
    analysis_year: Optional[int] = None, analysis_month: Optional[int] = None
) -> Tuple[int, int]:
    """获取当前分析日期

    Args:
        analysis_year: 指定的分析年份
        analysis_month: 指定的分析月份

    Returns:
        (年份, 月份) 元组
    """
    current_date = datetime.now()

    if analysis_year is None:
        analysis_year = current_date.year
    if analysis_month is None:
        analysis_month = current_date.month

    return analysis_year, analysis_month


def format_error_response(
    data: Dict[str, Any],
    operation: str,
    *,
    compact: bool = True,
) -> str:
    """格式化错误响应

    Args:
        data: 包含错误信息的字典
        operation: 操作名称

    Returns:
        格式化的错误信息字符串
    """
    if "error" in data:
        return format_json_response(
            {
                "error": data["error"],
                "error_code": data.get("error_code", INTERNAL_ERROR_CODE),
                "status_code": data.get("status_code", 500),
                "retryable": data.get("retryable", False),
                "operation": operation,
            },
            compact=compact,
        )
    return ""


def get_element_relationship(element1: str, element2: str) -> Dict[str, str]:
    """分析两个五行元素的关系

    Args:
        element1: 第一个元素名称
        element2: 第二个元素名称

    Returns:
        关系分析字典

    Raises:
        ValueError: 如果元素无效
    """
    from fatebridge.utils.data import DESTRUCTION_CYCLE, GENERATION_CYCLE, Element

    # 找到对应的Element枚举
    element1_enum = None
    element2_enum = None

    for element_enum in Element:
        if element_enum.value == element1:
            element1_enum = element_enum
        if element_enum.value == element2:
            element2_enum = element_enum

    # Check for None values before using
    if element1_enum is None or element2_enum is None:
        logger.warning(f"Invalid element reference: {element1} or {element2}")
        return {
            "type": "错误",
            "description": f"无效的五行元素: {element1 if element1_enum is None else element2}",
        }

    if element1_enum == element2_enum:
        return {"type": "相同", "description": "同类元素"}
    elif (
        element1_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相生",
            "description": f"{element1}生{element2}",
        }
    elif (
        element2_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相生",
            "description": f"{element2}生{element1}",
        }
    elif (
        element1_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相克",
            "description": f"{element1}克{element2}",
        }
    elif (
        element2_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相克",
            "description": f"{element2}克{element1}",
        }
    else:
        return {"type": "无直接关系", "description": "元素间无直接生克关系"}
