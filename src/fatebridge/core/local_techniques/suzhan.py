"""
Su Zhan (宿占) local technique.

Pure relocation from the package facade.
"""

from __future__ import annotations

from .chart import (
    DEFAULT_BIRTH_TIMEZONE,
    Any,
    Dict,
    List,
    Optional,
    _build_local_chart_response,
    _join_lines,
    _normalize_date_text,
    _normalize_mode,
    _normalize_time_text,
    _render_snapshot_text,
    _split_degree,
)


def _build_suzhan_snapshot_text(
    input_normalized: Dict[str, Any], response: Dict[str, Any]
) -> str:
    chart = response.get("chart", {}) if isinstance(response, dict) else {}
    houses = chart.get("houses") if isinstance(chart, dict) else []
    objects = chart.get("objects") if isinstance(chart, dict) else []
    house_lines: List[str] = []
    for house in houses or []:
        if not isinstance(house, dict):
            continue
        house_id = house.get("id", "House")
        house_lines.append(f"宫位：{house_id}")
        in_house = [
            item
            for item in objects or []
            if isinstance(item, dict) and item.get("house") == house_id
        ]
        if not in_house:
            house_lines.append("星曜：无")
            house_lines.append("")
            continue
        for item in in_house:
            degree, minute = _split_degree(item.get("signlon", item.get("lon")))
            su28 = str(item.get("su28") or "").strip()
            star_text = f"{degree}˚{su28}{minute}分" if su28 else f"{degree}˚{minute}分"
            house_lines.append(f"星曜：{item.get('id')} {star_text}".strip())
        house_lines.append("")

    return _render_snapshot_text(
        [
            (
                "起盘信息",
                _join_lines(
                    [
                        f"日期：{input_normalized['date']} {input_normalized['time']}",
                        f"时区：{input_normalized['zone']}",
                        f"经纬度：{input_normalized.get('lon') or '无'} {input_normalized.get('lat') or '无'}",
                        f"外盘：{input_normalized.get('szchart', 0)}",
                        f"盘型：{input_normalized.get('szshape', 0)}",
                        f"宫制：{((response.get('params') or {}).get('houseSystemResolved') or 'equal')}",
                        f"黄道：{((response.get('params') or {}).get('zodiacLabelZh') or (response.get('params') or {}).get('zodiacMode') or 'tropical')}",
                    ]
                ),
            ),
            ("宿盘宫位与二十八宿星曜", _join_lines(house_lines) or "无"),
        ]
    )


def build_suzhan_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    szchart: int = 0,
    szshape: int = 0,
    house_start_mode: int = 1,
    doubing_su28: bool = True,
    hsys: int = 8,
    zodiacal: int = 0,
) -> Dict[str, Any]:
    normalized_szchart = 1 if _normalize_mode(szchart, default=0) else 0
    normalized_szshape = 1 if _normalize_mode(szshape, default=0) else 0
    normalized_house_start_mode = (
        2 if _normalize_mode(house_start_mode, default=1) == 2 else 1
    )
    include_su28 = bool(doubing_su28)
    normalized_hsys = 8 if hsys is None else int(hsys)
    normalized_zodiacal = 0 if zodiacal is None else int(zodiacal)
    chart_variant = "guolao_chart" if normalized_szchart else "chart"
    if normalized_szchart and (normalized_hsys != 8 or normalized_zodiacal != 0):
        raise ValueError("宿占果老盘模式暂仅支持固定离线宫制 / 黄道语义。")
    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "szchart": normalized_szchart,
        "szshape": normalized_szshape,
        "houseStartMode": normalized_house_start_mode,
        "doubingSu28": include_su28,
        "hsys": normalized_hsys,
        "zodiacal": normalized_zodiacal,
    }
    response = _build_local_chart_response(
        date_text=input_normalized["date"],
        time_text=input_normalized["time"],
        timezone_name=input_normalized["zone"],
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        tradition=False,
        include_su28=include_su28,
        chart_variant=chart_variant,
        house_start_mode=normalized_house_start_mode,
        shape_mode=normalized_szshape,
        hsys=normalized_hsys,
        zodiacal=normalized_zodiacal,
        allow_extended_hsys=not bool(normalized_szchart),
        extra_params={
            "szchart": normalized_szchart,
            "szshape": normalized_szshape,
            "houseStartMode": normalized_house_start_mode,
            "doubingSu28": include_su28,
            "hsys": normalized_hsys,
            "zodiacal": normalized_zodiacal,
        },
    )
    chart = response["chart"]
    snapshot_text = _build_suzhan_snapshot_text(input_normalized, response)
    return {
        "analysis_type": "宿占 / 宿盘",
        "input_normalized": input_normalized,
        "params": response["params"],
        "chart": chart,
        "snapshot_text": snapshot_text,
        "summary": f"已生成宿占 / 宿盘输出。星曜数量：{len(chart.get('objects', []))}。",
    }
