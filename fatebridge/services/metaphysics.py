"""
Chinese metaphysics services for FateBridge.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.metaphysics import (
    MetaphysicsSeed,
    build_jinkou_board,
    build_liureng_board,
    build_liureng_runyear,
    build_qimen_board,
    build_taiyi_board,
    build_ziwei_chart,
    build_ziwei_rules,
)
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    PersonInfo,
    calculate_equation_of_time_minutes,
    create_pillar_dict,
    format_birth_datetime_display,
    handle_calculation_error,
    normalize_birth_time,
    parse_timezone_name,
)


def _build_analysis_seed(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> MetaphysicsSeed:
    timezone_name = analysis_timezone or DEFAULT_BIRTH_TIMEZONE
    input_datetime = datetime(
        analysis_year,
        analysis_month,
        analysis_day,
        analysis_hour,
        analysis_minute,
    )
    corrected_datetime = input_datetime
    total_correction_minutes = 0.0

    if use_true_solar_time:
        if analysis_longitude is None:
            raise ValueError("真太阳时修正需要 analysis_longitude")

        timezone_info = parse_timezone_name(timezone_name)
        aware_datetime = input_datetime.replace(tzinfo=timezone_info)
        utc_offset = aware_datetime.utcoffset()
        if utc_offset is None:
            raise ValueError(f"Invalid analysis timezone: {timezone_name}")

        daylight_saving = aware_datetime.dst() or timedelta(0)
        standard_offset = utc_offset - daylight_saving
        standard_meridian = (standard_offset.total_seconds() / 3600) * 15
        longitude_correction_minutes = 4 * (analysis_longitude - standard_meridian)
        equation_of_time_minutes = calculate_equation_of_time_minutes(input_datetime)
        total_correction_minutes = (
            longitude_correction_minutes + equation_of_time_minutes
        )
        corrected_datetime = input_datetime + timedelta(
            minutes=total_correction_minutes
        )

    pillars = BaZiCalendar.get_four_pillars(
        corrected_datetime,
        timezone_name=timezone_name,
    )
    calendar_context = build_calendar_context(
        corrected_datetime,
        timezone_name=timezone_name,
        pillars=pillars,
    )
    return MetaphysicsSeed(
        input_datetime=input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=timezone_name,
        longitude=analysis_longitude,
        applied_true_solar=use_true_solar_time,
        total_correction_minutes=total_correction_minutes,
        pillars=pillars,
        calendar_context=calendar_context,
    )


def _build_person_seed(person: PersonInfo) -> MetaphysicsSeed:
    normalized_birth_time = normalize_birth_time(person)
    corrected_datetime = normalized_birth_time.corrected_datetime
    pillars = BaZiCalendar.get_four_pillars(
        corrected_datetime,
        timezone_name=normalized_birth_time.timezone,
    )
    calendar_context = build_calendar_context(
        corrected_datetime,
        timezone_name=normalized_birth_time.timezone,
        pillars=pillars,
    )
    return MetaphysicsSeed(
        input_datetime=normalized_birth_time.input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=normalized_birth_time.timezone,
        longitude=normalized_birth_time.longitude,
        applied_true_solar=normalized_birth_time.applied,
        total_correction_minutes=normalized_birth_time.total_correction_minutes,
        pillars=pillars,
        calendar_context=calendar_context,
    )


def _analysis_context_payload(seed: MetaphysicsSeed) -> Dict[str, Any]:
    lunar_context = seed.calendar_context.get("lunar_calendar") or {}
    return {
        "input_datetime": seed.input_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "corrected_datetime": seed.corrected_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": seed.timezone,
        "longitude": seed.longitude,
        "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
        "total_correction_minutes": round(seed.total_correction_minutes, 2),
        "current_jieqi": seed.calendar_context["current_solar_term"]["name"],
        "next_jieqi": seed.calendar_context["next_solar_term"]["name"],
        "lunar_display": lunar_context.get("display"),
    }


def calculate_ziwei_birth(person: PersonInfo) -> Dict[str, Any]:
    try:
        seed = _build_person_seed(person)
        ziwei_birth = build_ziwei_chart(seed, person.gender or "未知")
        return {
            "analysis_type": "紫微斗数命盘",
            "person_info": {
                "name": person.name or "未提供",
                "birth_datetime": format_birth_datetime_display(
                    seed.input_datetime, include_minutes=True
                ),
                "normalized_birth_datetime": format_birth_datetime_display(
                    seed.corrected_datetime, include_minutes=True
                ),
                "gender": person.gender or "未知",
                "birth_place": person.birth_place or "未提供",
                "birth_timezone": seed.timezone,
                "birth_longitude": seed.longitude,
                "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
            },
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "ziwei_birth": ziwei_birth,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "紫微斗数命盘")


def calculate_ziwei_rules(year_stem: Optional[str] = None) -> Dict[str, Any]:
    try:
        if year_stem is not None and year_stem not in "甲乙丙丁戊己庚辛壬癸":
            raise ValueError("year_stem 必须是单个天干")
        payload = build_ziwei_rules(year_stem)
        return {
            "analysis_type": "紫微规则库",
            **payload,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "紫微规则库")


def calculate_liureng_gods(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        liureng = build_liureng_board(seed, gender=gender)
        return {
            "analysis_type": "大六壬起课",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "liureng": liureng,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "大六壬起课")


def calculate_liureng_runyear(
    person: PersonInfo,
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        liureng = build_liureng_board(seed, gender=person.gender or "未知")
        runyear = build_liureng_runyear(
            seed,
            gender=person.gender or "未知",
            birth_year=person.birth_year,
        )
        return {
            "analysis_type": "大六壬行年",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "runyear": runyear,
            "liureng": liureng,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "大六壬行年")


def calculate_qimen_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        qimen = build_qimen_board(seed)
        return {
            "analysis_type": "奇门遁甲",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "qimen": qimen,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "奇门遁甲")


def calculate_taiyi_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        taiyi = build_taiyi_board(seed, gender=gender)
        return {
            "analysis_type": "太乙神数",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "taiyi": taiyi,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "太乙神数")


def calculate_jinkou_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    di_fen: Optional[str] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        liureng = build_liureng_board(seed, gender=gender)
        jinkou = build_jinkou_board(
            seed,
            liureng,
            gender=gender,
            di_fen=di_fen,
        )
        return {
            "analysis_type": "金口诀",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "liureng": liureng,
            "jinkou": jinkou,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "金口诀")
