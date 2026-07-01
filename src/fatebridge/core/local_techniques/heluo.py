"""
Heluo (河洛理数) local technique.

Pure relocation from the package facade.
"""

from __future__ import annotations

from ...utils.helpers import create_pillar_dict
from ..heluo import build_snapshot_text as _heluo_snapshot_text
from ..heluo import calculate as _heluo_calculate
from ..heluo import da_yun as _heluo_da_yun
from ..heluo import judge as _heluo_judge
from ..heluo import solar_term as _heluo_solar_term
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


def build_heluo_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    gender: Optional[str] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    """河洛理数（heluo）。

    四柱来自 FateBridge 自有历法引擎；起命/起运/命运篇/爻辞由
    ``fatebridge.core.heluo`` 完成（节气经 FB 自有 24 节气引擎，与 horosa
    ``heluoLocal.js`` 逐字节对齐）。
    """
    normalized_gender = _normalize_canping_gender(gender)
    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "gender": normalized_gender,
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
    four_pillars = {
        "year": "".join(seed.pillars["year"]),
        "month": "".join(seed.pillars["month"]),
        "day": "".join(seed.pillars["day"]),
        "hour": "".join(seed.pillars["hour"]),
    }
    month_zhi = seed.pillars["month"][1]
    hour_zhi = seed.pillars["hour"][1]
    birth_year = seed.input_datetime.year

    chart = _heluo_calculate(
        four_pillars=four_pillars,
        gender=normalized_gender,
        hour_zhi=hour_zhi,
        birth_year=birth_year,
        month_zhi=month_zhi,
    )
    dayun = _heluo_da_yun(chart["xian"], chart["hou"], birth_year)
    st = _heluo_solar_term(
        seed.input_datetime.year,
        seed.input_datetime.month,
        seed.input_datetime.day,
        seed.timezone,
    )
    jg = _heluo_judge(chart, four_pillars, month_zhi, st)
    snapshot_text = _heluo_snapshot_text(chart, jg, dayun)
    analysis_context = _build_metaphysics_analysis_context(seed)

    return {
        "analysis_type": "河洛理数",
        "input_normalized": input_normalized,
        "analysis_context": analysis_context,
        "four_pillars": create_pillar_dict(seed.pillars),
        "calendar_context": seed.calendar_context,
        "chart": chart,
        "dayun": dayun,
        "judge": jg,
        "solar_term": st,
        "snapshot_text": snapshot_text,
        "summary": (
            f"已生成河洛理数输出。先天卦：{chart['xian']['name']}，"
            f"后天卦：{chart['hou']['name']}，命运篇{'葉' if jg['xie'] else '不葉'}。"
        ),
    }
