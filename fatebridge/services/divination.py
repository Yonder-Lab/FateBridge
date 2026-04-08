"""
FateBridge divination services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fatebridge.core.almanac import build_calendar_context
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.divination import build_meihua_interpretation, lookup_gua
from fatebridge.core.export_parser import parse_export_content
from fatebridge.core.phase2_local import (
    build_otherbu_result,
    build_sanshiunited_result,
    build_sixyao_result,
    build_suzhan_result,
    build_tongshefa_result,
)
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    create_pillar_dict,
    handle_calculation_error,
)


def _build_snapshot_export(
    *,
    technique: str,
    snapshot_text: str,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return parse_export_content(
        technique=technique,
        content=snapshot_text,
        selected_sections=selected_sections,
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

        interpretation = build_meihua_interpretation(meihua, question or "")

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
            "interpretation": interpretation,
            "summary": interpretation["comprehensive_judgement"],
        }

    except Exception as exc:
        return handle_calculation_error(exc, "梅花时卦分析")


def calculate_gua_lookup(
    *,
    query: str,
    lookup_mode: str = "auto",
) -> Dict:
    """
    卦义检索工具 - 支持六十四卦与八卦的离线义理查询。
    """
    try:
        result = lookup_gua(query, lookup_mode=lookup_mode)
        return {
            "analysis_type": "卦义检索",
            "query": query,
            "lookup_mode": lookup_mode,
            "result": result,
            "summary": result["summary"],
        }
    except Exception as exc:
        return handle_calculation_error(exc, "卦义检索")


def calculate_gua_meiyi(
    *,
    name: List[str],
) -> Dict[str, Any]:
    """
    梅易卦义辅助工具 - 批量返回偏梅花易数语境的卦义说明。
    """
    try:
        queries = [item.strip() for item in (name or []) if item and item.strip()]
        if not queries:
            raise ValueError("name 至少需要提供一个卦名或卦码。")

        results: Dict[str, Dict[str, Any]] = {}
        ordered_names: List[str] = []
        for query in queries:
            item = lookup_gua(query, lookup_mode="auto")
            desc = (
                f"{item['name']}：{item.get('theme', '当前之势')}。"
                f"{item.get('judgement') or item.get('guidance', '')}"
                f"宜{item.get('favorable', '顺势推进')}，"
                f"忌{item.get('caution', '失衡冒进')}。"
            )
            results[query] = {
                "name": item["name"],
                "lookup_type": item["lookup_type"],
                "theme": item.get("theme"),
                "judgement": item.get("judgement"),
                "guidance": item.get("guidance"),
                "desc": desc,
                "text": desc,
            }
            ordered_names.append(item["name"])

        return {
            "analysis_type": "梅易卦义",
            "queries": queries,
            "results": results,
            **results,
            "summary": f"共查询{len(queries)}项梅易卦义：{'、'.join(ordered_names)}。",
        }
    except Exception as exc:
        return handle_calculation_error(exc, "梅易卦义")


def calculate_tongshefa_analysis(
    *,
    taiyin: Optional[str] = None,
    taiyang: Optional[str] = None,
    shaoyang: Optional[str] = None,
    shaoyin: Optional[str] = None,
) -> Dict[str, Any]:
    """统摄法分析工具。"""
    try:
        return build_tongshefa_result(
            taiyin=taiyin,
            taiyang=taiyang,
            shaoyang=shaoyang,
            shaoyin=shaoyin,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "统摄法分析")


def calculate_sixyao_analysis(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    question: Optional[str] = None,
    gua_code: Optional[str] = None,
    changed_code: Optional[str] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """六爻 / 易卦分析工具。"""
    try:
        return build_sixyao_result(
            date=date,
            time=time,
            zone=zone,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            question=question,
            gua_code=gua_code,
            changed_code=changed_code,
            lines=lines,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "六爻分析")


def calculate_suzhan_analysis(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    szchart: int = 0,
    szshape: int = 0,
    house_start_mode: int = 1,
    doubing_su28: bool = True,
    hsys: int = 8,
    zodiacal: int = 0,
) -> Dict[str, Any]:
    """宿占 / 宿盘分析工具。"""
    try:
        return build_suzhan_result(
            date=date,
            time=time,
            zone=zone,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            szchart=szchart,
            szshape=szshape,
            house_start_mode=house_start_mode,
            doubing_su28=doubing_su28,
            hsys=hsys,
            zodiacal=zodiacal,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "宿占分析")


def calculate_otherbu_analysis(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    tradition: bool = False,
    sign: Optional[str] = None,
    house: int = 0,
    planet: Optional[str] = None,
    question: Optional[str] = None,
    hsys: int = 8,
    zodiacal: int = 0,
) -> Dict[str, Any]:
    """西洋游戏 / 占星骰子分析工具。"""
    try:
        return build_otherbu_result(
            date=date,
            time=time,
            zone=zone,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            tradition=tradition,
            sign=sign,
            house=house,
            planet=planet,
            question=question,
            hsys=hsys,
            zodiacal=zodiacal,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "占星骰子分析")


def calculate_sanshiunited_analysis(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Optional[str] = None,
    lon: Optional[str] = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    qimen_options: Optional[Dict[str, Any]] = None,
    taiyi_options: Optional[Dict[str, Any]] = None,
    liureng_yue: Optional[str] = None,
    liureng_is_diurnal: Optional[bool] = None,
    selected_sections: Optional[List[str]] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    """三式合一本地聚合工具。"""
    try:
        result = build_sanshiunited_result(
            date=date,
            time=time,
            zone=zone,
            lat=lat,
            lon=lon,
            gps_lat=gps_lat,
            gps_lon=gps_lon,
            qimen_options=qimen_options,
            taiyi_options=taiyi_options,
            liureng_yue=liureng_yue,
            liureng_is_diurnal=liureng_is_diurnal,
            use_true_solar_time=use_true_solar_time,
        )
        snapshot_text = result.get("snapshot_text")
        if isinstance(snapshot_text, str) and snapshot_text.strip():
            result["snapshot_export"] = _build_snapshot_export(
                technique="sanshiunited",
                snapshot_text=snapshot_text,
                selected_sections=selected_sections,
            )
        return result
    except Exception as exc:
        return handle_calculation_error(exc, "三式合一分析")
