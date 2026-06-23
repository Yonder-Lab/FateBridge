"""
Service surface for 卜卦 (horary).

Casts a chart for the moment the question was asked (NOT a birth) and runs the
classical judgment engine in :mod:`fatebridge.core.astrology_horary`.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fatebridge.core.astrology_horary import (
    CATEGORY_LABELS_ZH,
    HOUSE_BY_CATEGORY,
    build_horary_payload,
)
from fatebridge.core.predictive import build_subject
from fatebridge.services.snapshot_builders import (
    render_snapshot_text as _render_snapshot_text,
)
from fatebridge.utils.helpers import (
    handle_calculation_error,
    house_system_fields,
    normalize_house_system,
)


def _json_block(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def calculate_horary(
    *,
    question_year: int,
    question_month: int,
    question_day: int,
    question_hour: int,
    question_minute: int = 0,
    timezone_name: str = "+08:00",
    longitude: float,
    latitude: float,
    category: str = "general",
    name: Optional[str] = None,
    house_system: str = "R",
    zodiac_type: str = "Tropic",
) -> Dict[str, Any]:
    """按提问时刻起卜卦盘，依古典卜卦法判断事情成否。"""
    label = "卜卦判断"
    try:
        if category not in HOUSE_BY_CATEGORY:
            category = "general"
        house_system = normalize_house_system(house_system)
        question_local = datetime(
            question_year,
            question_month,
            question_day,
            question_hour,
            question_minute,
        )
        subject = build_subject(
            name=name or "卜卦盘",
            local_datetime=question_local,
            longitude=longitude,
            latitude=latitude,
            timezone_name=timezone_name,
            house_system=house_system,
            zodiac_type=zodiac_type,
        )
        payload = build_horary_payload(subject, category=category)

        context = {
            "tool": label,
            "question_datetime": question_local.isoformat(),
            "timezone": timezone_name,
            "category": category,
            "category_label": CATEGORY_LABELS_ZH[category],
            "location": {"longitude": longitude, "latitude": latitude},
            **house_system_fields(house_system),
            "zodiac_type": zodiac_type,
            "engine": "fatebridge-offline",
        }
        summary = (
            f"卜卦（{payload['category_label']}）：{payload['verdict']} — "
            f"{payload['reasoning']}"
        )
        sections = [
            ("起盘信息", _json_block(context)),
            (
                "主星与判词",
                _json_block(
                    {
                        "ascendant": payload["ascendant"],
                        "significators": payload["significators"],
                        "perfection": payload["perfection"],
                        "verdict": payload["verdict"],
                        "reasoning": payload["reasoning"],
                    }
                ),
            ),
            (
                "月相与裁决",
                _json_block(
                    {"moon": payload["moon"], "radicality": payload["radicality"]}
                ),
            ),
        ]
        return {
            "analysis_type": "西占卜卦",
            "engine": "fatebridge-offline",
            "analysis_context": context,
            "horary": payload,
            "summary": summary,
            "snapshot_text": _render_snapshot_text(sections),
        }
    except Exception as exc:
        return handle_calculation_error(exc, label)
