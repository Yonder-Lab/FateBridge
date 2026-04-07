"""
FateBridge divination services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    create_pillar_dict,
    handle_calculation_error,
)


def calculate_meihua_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    question: Optional[str] = None,
) -> Dict:
    """
    梅花时卦分析工具 - 按指定时刻生成本卦、变卦、互卦、综卦与体用关系。
    """
    try:
        timezone_name = analysis_timezone or DEFAULT_BIRTH_TIMEZONE
        analysis_datetime = datetime(
            analysis_year,
            analysis_month,
            analysis_day,
            analysis_hour,
            analysis_minute,
        )

        pillars = BaZiCalendar.get_four_pillars(
            analysis_datetime,
            timezone_name=timezone_name,
        )
        calendar_context = build_calendar_context(
            analysis_datetime,
            timezone_name=timezone_name,
            pillars=pillars,
        )
        lunar_calendar = calendar_context.get("lunar_calendar") or {}
        meihua = lunar_calendar.get("meihua")

        if not meihua:
            return {
                "error": "当前环境缺少农历上下文，无法生成梅花时卦。",
                "analysis_type": "梅花时卦分析",
            }

        return {
            "analysis_type": "梅花时卦分析",
            "analysis_context": {
                "analysis_datetime": calendar_context["solar_datetime"],
                "timezone": timezone_name,
                "question": question or "",
                "lunar_display": lunar_calendar.get("display"),
                "current_jieqi": calendar_context["current_solar_term"]["name"],
                "next_jieqi": calendar_context["next_solar_term"]["name"],
            },
            "four_pillars": create_pillar_dict(pillars),
            "calendar_context": calendar_context,
            "meihua": meihua,
            "summary": (
                f"{meihua['summary']}{meihua['body_use_summary']}"
                if meihua.get("body_use_summary")
                else meihua["summary"]
            ),
        }

    except Exception as exc:
        return handle_calculation_error(exc, "梅花时卦分析")
