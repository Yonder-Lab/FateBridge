"""
Canping (参评盘) local technique.

Pure relocation from the package facade.
"""

from __future__ import annotations

from ...utils.helpers import create_pillar_dict
from ..canping import build_snapshot_text as _canping_snapshot_text
from ..canping import calculate as _canping_calculate
from ..canping import liunian_series as _canping_liunian_series
from .chart import (
    DEFAULT_BIRTH_TIMEZONE,
    Any,
    Dict,
    Optional,
    _build_metaphysics_analysis_context,
    _build_metaphysics_seed,
    _normalize_canping_gender,
    _normalize_date_text,
    _normalize_time_text,
)


def _normalize_canping_method(value: Any) -> str:
    text = f"{value if value is not None else ''}".strip().lower()
    return "gu" if text == "gu" else "ming"


def build_canping_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    gender: Optional[str] = None,
    method: str = "ming",
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    """邵子参评数 / 金锁银匙（canping）。

    四柱来自 FateBridge 自有历法引擎，金锁银匙起数 + 条文查表由
    ``fatebridge.core.canping`` 完成（与 horosa ``canpingLocal.js`` 逐字节对齐）。
    """
    normalized_gender = _normalize_canping_gender(gender)
    normalized_method = _normalize_canping_method(method)
    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "gender": normalized_gender,
        "method": normalized_method,
        "use_true_solar_time": bool(use_true_solar_time),
    }
    seed = _build_metaphysics_seed(
        date_text=input_normalized["date"],
        time_text=input_normalized["time"],
        timezone_name=input_normalized["zone"],
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        use_true_solar_time=bool(use_true_solar_time),
    )
    year_stem, year_branch = seed.pillars["year"]
    year_gz = f"{year_stem}{year_branch}"
    month_branch = seed.pillars["month"][1]
    day_branch = seed.pillars["day"][1]
    hour_branch = seed.pillars["hour"][1]
    birth_year = seed.input_datetime.year

    result = _canping_calculate(
        year_gz=year_gz,
        month_branch=month_branch,
        day_branch=day_branch,
        hour_branch=hour_branch,
        gender=normalized_gender,
        method=normalized_method,
    )
    series = _canping_liunian_series(
        year_gz=year_gz,
        month_branch=month_branch,
        day_branch=day_branch,
        hour_branch=hour_branch,
        gender=normalized_gender,
        method=normalized_method,
        birth_year=birth_year,
    )
    snapshot_text = _canping_snapshot_text(result)
    analysis_context = _build_metaphysics_analysis_context(seed)
    four_pillars = create_pillar_dict(seed.pillars)

    return {
        "analysis_type": "邵子参评数 / 金锁银匙",
        "input_normalized": input_normalized,
        "analysis_context": analysis_context,
        "four_pillars": four_pillars,
        "calendar_context": seed.calendar_context,
        "element": result["element"],
        "part_name": result["partName"],
        "day_palace_branch": result["dayPalaceBranch"],
        "ming_gong": result["mingGong"],
        "benming": result["benming"],
        "dayun": result["dayun"],
        "liunian_series": series,
        "snapshot_text": snapshot_text,
        "summary": (
            f"已生成邵子参评数 / 金锁银匙输出。年纳音：{result['element']}部，"
            f"命宫：{result['mingGong']}，取法："
            f"{'古法' if normalized_method == 'gu' else '明法'}。"
        ),
    }
