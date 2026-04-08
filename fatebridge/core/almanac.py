"""
Calendrical helpers for solar terms, lunar context, and BaZi boundaries.

This module keeps the expensive year-level calculations cached so service-layer
code can enrich responses without recomputing 24 solar terms on every call.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from dateutil import tz as dateutil_tz

try:
    from lunardate import LunarDate
except ImportError:  # pragma: no cover - exercised only in misconfigured envs
    LunarDate = None

from .divination import derive_meihua_hexagram


DEFAULT_TIMEZONE = "Asia/Shanghai"
DAY_GANZHI_STRATEGY_STANDARD = "standard"
DAY_GANZHI_STRATEGY_REFERENCE_OFFSET = "reference_offset"

SOLAR_TERM_NAMES = [
    "小寒",
    "大寒",
    "立春",
    "雨水",
    "惊蛰",
    "春分",
    "清明",
    "谷雨",
    "立夏",
    "小满",
    "芒种",
    "夏至",
    "小暑",
    "大暑",
    "立秋",
    "处暑",
    "白露",
    "秋分",
    "寒露",
    "霜降",
    "立冬",
    "小雪",
    "大雪",
    "冬至",
]

# Standard fixed-qì approximation often used in offline Chinese calendar tools.
SOLAR_TERM_MINUTE_OFFSETS = [
    0,
    21208,
    42467,
    63836,
    85337,
    107014,
    128867,
    150921,
    173149,
    195551,
    218072,
    240693,
    263343,
    285989,
    308563,
    331033,
    353350,
    375494,
    397447,
    419210,
    440795,
    462224,
    483532,
    504758,
]

MILLISECONDS_PER_TROPICAL_YEAR = 31556925974.7
SOLAR_TERM_BASE_UTC = datetime(1900, 1, 6, 2, 5, tzinfo=timezone.utc)

GAN = tuple("甲乙丙丁戊己庚辛壬癸")
ZHI = tuple("子丑寅卯辰巳午未申酉戌亥")

BAZI_MONTH_START_TERMS = {
    "立春": "寅",
    "惊蛰": "卯",
    "清明": "辰",
    "立夏": "巳",
    "芒种": "午",
    "小暑": "未",
    "立秋": "申",
    "白露": "酉",
    "寒露": "戌",
    "立冬": "亥",
    "大雪": "子",
    "小寒": "丑",
}

BAZI_MONTH_SEQUENCE = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]

LUNAR_MONTH_NAMES = {
    1: "正月",
    2: "二月",
    3: "三月",
    4: "四月",
    5: "五月",
    6: "六月",
    7: "七月",
    8: "八月",
    9: "九月",
    10: "十月",
    11: "冬月",
    12: "腊月",
}

LUNAR_DAY_NAMES = {
    1: "初一",
    2: "初二",
    3: "初三",
    4: "初四",
    5: "初五",
    6: "初六",
    7: "初七",
    8: "初八",
    9: "初九",
    10: "初十",
    11: "十一",
    12: "十二",
    13: "十三",
    14: "十四",
    15: "十五",
    16: "十六",
    17: "十七",
    18: "十八",
    19: "十九",
    20: "二十",
    21: "廿一",
    22: "廿二",
    23: "廿三",
    24: "廿四",
    25: "廿五",
    26: "廿六",
    27: "廿七",
    28: "廿八",
    29: "廿九",
    30: "三十",
}

OFFSET_RE = re.compile(r"^([+-]?)(\d{1,2})(?::?(\d{2}))?$")

LUNAR_SUPPORTED_SOLAR_START = datetime(1900, 1, 31).date()
LUNAR_SUPPORTED_SOLAR_END = datetime(2100, 2, 8).date()

DAY_GANZHI_JDN_OFFSETS = {
    DAY_GANZHI_STRATEGY_STANDARD: 49,
    DAY_GANZHI_STRATEGY_REFERENCE_OFFSET: 38,
}


@dataclass(frozen=True)
class SolarTerm:
    name: str
    moment: datetime
    date_key: str
    day_ganzhi: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "datetime": self.moment.strftime("%Y-%m-%d %H:%M:%S"),
            "date_key": self.date_key,
            "day_ganzhi": self.day_ganzhi,
        }


def _parse_timezone_spec(timezone_name: Optional[str]):
    value = (timezone_name or DEFAULT_TIMEZONE).strip()
    tzinfo = dateutil_tz.gettz(value)
    if tzinfo is not None:
        return tzinfo

    match = OFFSET_RE.match(value)
    if not match:
        raise ValueError(f"Unsupported timezone spec: {value}")

    sign_text, hour_text, minute_text = match.groups()
    sign = -1 if sign_text == "-" else 1
    hours = int(hour_text or "0")
    minutes = int(minute_text or "0")
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def localize_datetime(moment: datetime, timezone_name: Optional[str]) -> datetime:
    tzinfo = _parse_timezone_spec(timezone_name)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tzinfo)
    return moment.astimezone(tzinfo)


def _julian_day_number(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + ((153 * m + 2) // 5) + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def get_day_ganzhi(
    year: int,
    month: int,
    day: int,
    *,
    strategy: str = DAY_GANZHI_STRATEGY_STANDARD,
) -> str:
    if strategy not in DAY_GANZHI_JDN_OFFSETS:
        raise ValueError(f"Unsupported day ganzhi strategy: {strategy}")

    index = (_julian_day_number(year, month, day) + DAY_GANZHI_JDN_OFFSETS[strategy]) % 60
    return f"{GAN[index % 10]}{ZHI[index % 12]}"


@lru_cache(maxsize=128)
def get_solar_terms_for_year(
    year: int, timezone_name: str = DEFAULT_TIMEZONE
) -> Tuple[SolarTerm, ...]:
    tzinfo = _parse_timezone_spec(timezone_name)
    terms: List[SolarTerm] = []

    for term_name, offset_minutes in zip(SOLAR_TERM_NAMES, SOLAR_TERM_MINUTE_OFFSETS):
        total_milliseconds = (
            MILLISECONDS_PER_TROPICAL_YEAR * (year - 1900)
            + offset_minutes * 60_000
        )
        utc_moment = SOLAR_TERM_BASE_UTC + timedelta(
            milliseconds=total_milliseconds
        )
        local_moment = utc_moment.astimezone(tzinfo)
        terms.append(
            SolarTerm(
                name=term_name,
                moment=local_moment,
                date_key=local_moment.strftime("%Y%m%d"),
                day_ganzhi=get_day_ganzhi(
                    local_moment.year, local_moment.month, local_moment.day
                ),
            )
        )

    return tuple(terms)


def get_jieqi_year_grid(
    year: int, timezone_name: str = DEFAULT_TIMEZONE
) -> List[Dict[str, str]]:
    return [item.as_dict() for item in get_solar_terms_for_year(year, timezone_name)]


def _term_window(moment: datetime, timezone_name: str) -> List[SolarTerm]:
    local_moment = localize_datetime(moment, timezone_name)
    window: List[SolarTerm] = []
    for year in (local_moment.year - 1, local_moment.year, local_moment.year + 1):
        window.extend(get_solar_terms_for_year(year, timezone_name))
    return sorted(window, key=lambda item: item.moment)


def get_adjacent_solar_terms(
    moment: datetime, timezone_name: str = DEFAULT_TIMEZONE
) -> Tuple[SolarTerm, SolarTerm]:
    local_moment = localize_datetime(moment, timezone_name)
    previous = None
    upcoming = None

    for term in _term_window(local_moment, timezone_name):
        if term.moment <= local_moment:
            previous = term
            continue
        upcoming = term
        break

    if previous is None or upcoming is None:
        raise ValueError("Unable to resolve neighbouring solar terms.")

    return previous, upcoming


def get_bazi_year(moment: datetime, timezone_name: str = DEFAULT_TIMEZONE) -> int:
    local_moment = localize_datetime(moment, timezone_name)
    current_year_terms = {
        term.name: term for term in get_solar_terms_for_year(local_moment.year, timezone_name)
    }
    li_chun = current_year_terms["立春"]
    return local_moment.year if local_moment >= li_chun.moment else local_moment.year - 1


def get_bazi_month_context(
    moment: datetime, timezone_name: str = DEFAULT_TIMEZONE
) -> Dict[str, object]:
    current_boundary, next_boundary, month_branch, month_index = get_bazi_month_boundaries(
        moment, timezone_name
    )
    local_moment = localize_datetime(moment, timezone_name)

    return {
        "branch": month_branch,
        "month_index": month_index,
        "start_term": current_boundary.as_dict(),
        "next_term": next_boundary.as_dict(),
        "days_since_start": round(
            (local_moment - current_boundary.moment).total_seconds() / 86400, 4
        ),
        "days_until_next": round(
            (next_boundary.moment - local_moment).total_seconds() / 86400, 4
        ),
    }


def get_bazi_month_boundaries(
    moment: datetime, timezone_name: str = DEFAULT_TIMEZONE
) -> Tuple[SolarTerm, SolarTerm, str, int]:
    local_moment = localize_datetime(moment, timezone_name)
    candidates = [
        term
        for term in _term_window(local_moment, timezone_name)
        if term.name in BAZI_MONTH_START_TERMS
    ]

    current_boundary = None
    next_boundary = None
    for term in candidates:
        if term.moment <= local_moment:
            current_boundary = term
            continue
        next_boundary = term
        break

    if current_boundary is None or next_boundary is None:
        raise ValueError("Unable to resolve BaZi month boundary.")

    month_branch = BAZI_MONTH_START_TERMS[current_boundary.name]
    month_index = BAZI_MONTH_SEQUENCE.index(month_branch)
    return current_boundary, next_boundary, month_branch, month_index


def _format_lunar_year(year: int) -> str:
    digits = "零一二三四五六七八九"
    return "".join(digits[int(char)] for char in str(year))


def _lunar_supported_range_payload() -> Dict[str, str]:
    return {
        "start": LUNAR_SUPPORTED_SOLAR_START.isoformat(),
        "end": LUNAR_SUPPORTED_SOLAR_END.isoformat(),
    }


def _safe_lunar_date_from_solar(
    moment: datetime, timezone_name: str
) -> Optional["LunarDate"]:
    if LunarDate is None:
        return None

    local_moment = localize_datetime(moment, timezone_name)
    solar_date = local_moment.date()
    if (
        solar_date < LUNAR_SUPPORTED_SOLAR_START
        or solar_date > LUNAR_SUPPORTED_SOLAR_END
    ):
        return None

    try:
        lunar = LunarDate.fromSolarDate(
            solar_date.year, solar_date.month, solar_date.day
        )
        if lunar.toSolarDate() != solar_date:
            return None
    except ValueError:
        return None

    return lunar


def get_lunar_context(
    moment: datetime,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    pillars: Optional[Dict[str, Tuple[str, str]]] = None,
) -> Optional[Dict[str, object]]:
    local_moment = localize_datetime(moment, timezone_name)
    lunar = _safe_lunar_date_from_solar(local_moment, timezone_name)
    if lunar is None:
        return None

    previous_term, next_term = get_adjacent_solar_terms(local_moment, timezone_name)
    days_since_term = (local_moment.date() - previous_term.moment.date()).days

    context: Dict[str, object] = {
        "solar_datetime": local_moment.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone_name,
        "birth": local_moment.strftime("%Y-%m-%d %H:%M:%S"),
        "year": lunar.year,
        "month": lunar.month,
        "day": lunar.day,
        "is_leap_month": bool(lunar.isLeapMonth),
        "year_cn": _format_lunar_year(lunar.year),
        "month_cn": f"{'闰' if lunar.isLeapMonth else ''}{LUNAR_MONTH_NAMES[lunar.month]}",
        "day_cn": LUNAR_DAY_NAMES[lunar.day],
        "display": (
            f"{'闰' if lunar.isLeapMonth else ''}{LUNAR_MONTH_NAMES[lunar.month]}"
            f"{LUNAR_DAY_NAMES[lunar.day]}"
        ),
        "jieqi": previous_term.name,
        "jiedelta": f"{previous_term.name}后第{days_since_term}天",
        "previous_jieqi": previous_term.as_dict(),
        "next_jieqi": next_term.as_dict(),
        "days_until_next_jieqi": round(
            (next_term.moment - local_moment).total_seconds() / 86400, 4
        ),
    }

    if pillars:
        context["year_jieqi_ganzhi"] = f"{pillars['year'][0]}{pillars['year'][1]}"
        context["month_ganzhi"] = f"{pillars['month'][0]}{pillars['month'][1]}"
        context["day_ganzhi"] = f"{pillars['day'][0]}{pillars['day'][1]}"
        context["time_ganzhi"] = f"{pillars['hour'][0]}{pillars['hour'][1]}"
        context["meihua"] = derive_meihua_hexagram(
            year_branch=pillars["year"][1],
            lunar_month=lunar.month,
            lunar_day=lunar.day,
            hour_branch=pillars["hour"][1],
        )

    return context


def build_calendar_context(
    moment: datetime,
    *,
    timezone_name: str = DEFAULT_TIMEZONE,
    pillars: Optional[Dict[str, Tuple[str, str]]] = None,
) -> Dict[str, object]:
    local_moment = localize_datetime(moment, timezone_name)
    previous_term, next_term = get_adjacent_solar_terms(local_moment, timezone_name)
    month_context = get_bazi_month_context(local_moment, timezone_name)
    lunar_context = get_lunar_context(
        local_moment, timezone_name=timezone_name, pillars=pillars
    )
    lunar_support = {
        "supported": lunar_context is not None,
        "supported_range": _lunar_supported_range_payload(),
    }
    if lunar_context is None:
        lunar_support["reason"] = (
            "离线农历换算仅支持公历 1900-01-31 至 2100-02-08。"
        )

    return {
        "timezone": timezone_name,
        "solar_datetime": local_moment.strftime("%Y-%m-%d %H:%M:%S"),
        "current_solar_term": previous_term.as_dict(),
        "next_solar_term": next_term.as_dict(),
        "solar_term_delta": {
            "days_since_current": round(
                (local_moment - previous_term.moment).total_seconds() / 86400, 4
            ),
            "days_until_next": round(
                (next_term.moment - local_moment).total_seconds() / 86400, 4
            ),
            "description": f"{previous_term.name}后第{(local_moment.date() - previous_term.moment.date()).days}天",
        },
        "bazi_month_boundary": month_context,
        "lunar_calendar": lunar_context,
        "lunar_calendar_support": lunar_support,
    }
