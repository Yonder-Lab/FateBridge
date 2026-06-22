"""
本地技法辅助模块（local technique helpers）。

实现 FateBridge 本地技法层（六爻、宿占、统摄法、三式合一等），
以纯 Python 离线逻辑为主，尽量复用本仓库现有本地引擎。
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    SOLAR_TIME_STRATEGY_APPARENT,
    calculate_solar_time_adjustment,
    create_pillar_dict,
)
from ..almanac import (
    DAY_GANZHI_STRATEGY_STANDARD,
    build_calendar_context,
    localize_datetime,
)
from ..astrology import (
    AstroBirthInfo,
    build_astro_birth_info,
    build_core_chart_payload,
)
from ..calendar import BaZiCalendar
from ..canping import build_snapshot_text as _canping_snapshot_text
from ..canping import calculate as _canping_calculate
from ..canping import liunian_series as _canping_liunian_series
from ..divination import (
    BAGUA_BY_NAME,
    HEXAGRAM_NAMES,
    build_hexagram,
    lookup_hexagram_by_code,
)
from ..heluo import build_snapshot_text as _heluo_snapshot_text
from ..heluo import calculate as _heluo_calculate
from ..heluo import da_yun as _heluo_da_yun
from ..heluo import judge as _heluo_judge
from ..heluo import solar_term as _heluo_solar_term
from ..metaphysics import (
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    MetaphysicsSeed,
    build_liureng_board,
    build_qimen_board,
    build_taiyi_board,
)
from .chart import (
    GEO_COORDINATE_RE,
    OUTER_PLANETS,
    SANSHI_REFERENCES,
    SU28_NAMES,
    TRADITIONAL_PLANETS,
    ZODIAC_SIGN_CN,
    ZODIAC_SIGNS,
    _adapt_chart_houses,
    _adapt_chart_objects,
    _build_birth_info,
    _build_house_ring,
    _build_houses,
    _build_local_chart_response,
    _build_metaphysics_analysis_context,
    _build_metaphysics_seed,
    _build_point_object,
    _build_qimen_palace_overview_lines,
    _display_house_system_name,
    _house_direction,
    _house_id_for_houses,
    _house_id_for_longitude,
    _house_step,
    _join_lines,
    _julian_day,
    _normalize_canping_gender,
    _normalize_date_text,
    _normalize_mode,
    _normalize_time_text,
    _option_value,
    _reindex_houses,
    _render_qimen_palace_sections,
    _render_snapshot_text,
    _resolve_coordinates,
    _reverse_houses,
    _rotate_items,
    _sign_name,
    _split_degree,
    _su28_name,
    build_pseudo_chart,
    parse_geo_coordinate,
    parse_local_datetime,
)
from .sixyao import build_sixyao_result

PLANET_DEFS: List[Dict[str, Any]] = [
    {"id": "Sun", "base": 280.46, "speed": 0.9856474},
    {"id": "Moon", "base": 218.32, "speed": 13.176396},
    {"id": "Mercury", "base": 60.0, "speed": 4.09233445},
    {"id": "Venus", "base": 85.0, "speed": 1.60213034},
    {"id": "Mars", "base": 19.0, "speed": 0.52402068},
    {"id": "Jupiter", "base": 238.0, "speed": 0.08308529},
    {"id": "Saturn", "base": 266.0, "speed": 0.03344414},
    {"id": "Uranus", "base": 244.0, "speed": 0.01172834},
    {"id": "Neptune", "base": 84.0, "speed": 0.00598103},
    {"id": "Pluto", "base": 246.0, "speed": 0.00396422},
]


PLANET_KEYWORDS = {
    "Sun": "核心意志、主导权、要不要由自己拍板",
    "Moon": "情绪需求、回应速度、当下感受",
    "Mercury": "沟通、文书、协商与策略细节",
    "Venus": "关系温度、吸引、资源交换与和气",
    "Mars": "行动力、冲突点、推进与突破",
    "Jupiter": "放大、机会、贵人与增长空间",
    "Saturn": "边界、责任、压力与长期结构",
    "Uranus": "突变、跳脱、反常与临时改道",
    "Neptune": "想象、模糊、投射与理想化",
    "Pluto": "深层翻盘、控制欲与结构重置",
}

SIGN_KEYWORDS = {
    "Aries": "先动手、先试、先抢节奏",
    "Taurus": "稳住、保值、看实际回报",
    "Gemini": "多线沟通、试探消息与机动调整",
    "Cancer": "情绪与安全感优先，先顾根基",
    "Leo": "聚焦主角感、表达与结果面子",
    "Virgo": "拆细节、做校对、边做边修",
    "Libra": "看关系平衡、谈条件、求共识",
    "Scorpio": "深挖动机、看隐情、先破后立",
    "Sagittarius": "放眼远处、扩大视角、先看方向",
    "Capricorn": "按规则推进，先定边界与责任",
    "Aquarius": "跳出旧框，靠新方法或新连接",
    "Pisces": "凭感受与直觉，边走边感应变化",
}

HOUSE_KEYWORDS = {
    0: "自己、形象、主动权与起手姿态",
    1: "金钱、资源、投入产出与占有感",
    2: "沟通、消息、合同、短程变化与近身互动",
    3: "家庭、基底、内在安全感与根系",
    4: "表达、恋爱、创作、兴趣与想不想要",
    5: "工作细节、健康节律、日常事务与服务",
    6: "合作、对手、关系镜像与正面对线",
    7: "风险、债务、深层绑定与不可控变化",
    8: "远行、进修、信念、法务与远景",
    9: "事业、目标、名声、上级与结果面",
    10: "社群、人脉、团队、愿景与外部助力",
    11: "退场、隐情、休整、潜意识与幕后因素",
}


QIMEN_STARS = ["天蓬", "天任", "天冲", "天辅", "天英", "天芮", "天柱", "天心", "天禽"]
QIMEN_DOORS = ["休门", "生门", "伤门", "杜门", "景门", "死门", "惊门", "开门"]
QIMEN_GODS = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]
QIMEN_PALACES = ["坎宫", "艮宫", "震宫", "巽宫", "离宫", "坤宫", "兑宫", "乾宫"]
QIMEN_NINE_GRID_LAYOUT = (
    ("巽四宫", "离九宫", "坤二宫"),
    ("震三宫", "中五宫", "兑七宫"),
    ("艮八宫", "坎一宫", "乾六宫"),
)
TAIYI_BIG_PATTERNS = [
    "贵人顺行格",
    "龙德扶身格",
    "青龙转关格",
    "朱雀投江格",
    "白虎当关格",
    "六合成局格",
    "玄武伏吟格",
    "太常合德格",
    "天空反照格",
    "天后持静格",
    "勾陈守户格",
    "腾蛇绕局格",
]
TAIYI_SMALL_PATTERNS = [
    "青龙返首",
    "六合入局",
    "白虎守门",
    "腾蛇绕身",
    "九地蓄势",
    "九天扬兵",
    "太阴护局",
    "玄武回环",
]


def _normalize_sign(sign: Optional[str]) -> str:
    if not sign:
        return "Aries"
    lowered = str(sign).strip().casefold()
    for item in ZODIAC_SIGNS:
        if item.casefold() == lowered:
            return item
    for item, label in ZODIAC_SIGN_CN.items():
        if label.casefold() == lowered:
            return item
    return "Aries"


def _normalize_planet(planet: Optional[str]) -> str:
    if not planet:
        return "Sun"
    lowered = str(planet).strip().casefold()
    for item in [str(definition["id"]) for definition in PLANET_DEFS]:
        if item.casefold() == lowered:
            return item
    return "Sun"


def _normalize_house_index(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 11))


def _reassign_chart_object_houses(
    objects: List[Dict[str, Any]],
    *,
    houses: List[Dict[str, Any]],
) -> None:
    for item in objects:
        if not isinstance(item, dict):
            continue
        item["house"] = _house_id_for_houses(
            float(item.get("lon", 0.0)),
            houses,
        )


def _bagua(name: str) -> Dict[str, Any]:
    source = BAGUA_BY_NAME[name]
    return {
        "name": name,
        "cname": source["nature"],
        "nature": source["nature"],
        "elem": source["element"],
        "element": source["element"],
        "value": list(source["lines"]),
        "lines": list(source["lines"]),
        "symbol": source["symbol"],
    }


def _bagua_from_lines(lines: List[int]) -> Dict[str, Any]:
    for name, source in BAGUA_BY_NAME.items():
        if list(source["lines"]) == list(lines):
            return _bagua(name)
    return _bagua("乾")


def _hex(upper: Dict[str, Any], lower: Dict[str, Any]) -> Dict[str, Any]:
    lines = [*lower["value"], *upper["value"]]
    name = HEXAGRAM_NAMES.get(
        (upper["name"], lower["name"]), f"{upper['cname']}{lower['cname']}"
    )
    payload: Dict[str, Any] = {
        "name": name,
        "upper": upper,
        "lower": lower,
        "lines": lines,
        "value": lines,
        "binary_code": "".join(str(bit) for bit in lines),
        "symbol": f"{upper['symbol']}{lower['symbol']}",
    }
    try:
        detail = lookup_hexagram_by_code(payload["binary_code"])
        payload.update(
            {
                "theme": detail.get("theme"),
                "judgement": detail.get("judgement"),
                "image": detail.get("image"),
            }
        )
    except ValueError:
        pass
    return payload


def _mutual_hex(hexagram: Dict[str, Any]) -> Dict[str, Any]:
    lines = hexagram["lines"]
    mutual_lines = [lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]]
    lower = _bagua_from_lines(mutual_lines[:3])
    upper = _bagua_from_lines(mutual_lines[3:])
    return _hex(upper, lower)


def _opposite_hex(hexagram: Dict[str, Any]) -> Dict[str, Any]:
    opposite_lines = [0 if bit == 1 else 1 for bit in hexagram["lines"]]
    lower = _bagua_from_lines(opposite_lines[:3])
    upper = _bagua_from_lines(opposite_lines[3:])
    return _hex(upper, lower)


def _tongshefa_relation_by_elem(left_elem: str, right_elem: str) -> str:
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
    if left_elem == right_elem:
        return "思同实"
    if sheng[left_elem] == right_elem:
        return "思生实"
    if ke[left_elem] == right_elem:
        return "思克实"
    if sheng[right_elem] == left_elem:
        return "实生思"
    if ke[right_elem] == left_elem:
        return "实克思"
    return "思同实"


def _build_tongshefa_snapshot(model: Dict[str, Any]) -> str:
    rows = []
    for index in range(5, -1, -1):
        rows.append(
            f"第{index + 1}爻：左{'阳' if model['baseLeft']['lines'][index] == 1 else '阴'} / "
            f"右{'阳' if model['baseRight']['lines'][index] == 1 else '阴'} / "
            f"{'不变' if model['baseLeft']['lines'][index] == model['baseRight']['lines'][index] else '已变'}"
        )
    return _render_snapshot_text(
        [
            (
                "本卦",
                _join_lines(
                    [
                        f"左卦：{model['baseLeft']['name']}（上卦{model['baseLeft']['upper']['name']} / 下卦{model['baseLeft']['lower']['name']}）",
                        f"右卦：{model['baseRight']['name']}（上卦{model['baseRight']['upper']['name']} / 下卦{model['baseRight']['lower']['name']}）",
                    ]
                ),
            ),
            ("六爻", _join_lines(rows)),
            (
                "潜藏",
                _join_lines(
                    [
                        f"左潜藏：{model['mutualLeft']['name']}",
                        f"右潜藏：{model['mutualRight']['name']}",
                    ]
                ),
            ),
            (
                "亲和",
                _join_lines(
                    [
                        f"左亲和：{model['oppositeLeft']['name']}",
                        f"右亲和：{model['oppositeRight']['name']}",
                    ]
                ),
            ),
        ]
    )


def build_tongshefa_result(
    *,
    taiyin: Optional[str] = None,
    taiyang: Optional[str] = None,
    shaoyang: Optional[str] = None,
    shaoyin: Optional[str] = None,
) -> Dict[str, Any]:
    selected = {
        "taiyin": taiyin if taiyin in BAGUA_BY_NAME else "巽",
        "taiyang": taiyang if taiyang in BAGUA_BY_NAME else "坤",
        "shaoyang": shaoyang if shaoyang in BAGUA_BY_NAME else "震",
        "shaoyin": shaoyin if shaoyin in BAGUA_BY_NAME else "震",
    }
    taiyin_gua = _bagua(selected["taiyin"])
    taiyang_gua = _bagua(selected["taiyang"])
    shaoyang_gua = _bagua(selected["shaoyang"])
    shaoyin_gua = _bagua(selected["shaoyin"])

    base_left = _hex(taiyin_gua, shaoyang_gua)
    base_right = _hex(taiyang_gua, shaoyin_gua)
    mutual_left = _mutual_hex(base_left)
    mutual_right = _mutual_hex(base_right)
    opposite_left = _opposite_hex(base_left)
    opposite_right = _opposite_hex(base_right)
    left_elem = base_left["upper"]["elem"]
    right_elem = base_right["upper"]["elem"]
    main_relation = _tongshefa_relation_by_elem(left_elem, right_elem)
    model = {
        "selected": selected,
        "baseLeft": base_left,
        "baseRight": base_right,
        "mutualLeft": mutual_left,
        "mutualRight": mutual_right,
        "oppositeLeft": opposite_left,
        "oppositeRight": opposite_right,
        "left_elem": left_elem,
        "right_elem": right_elem,
        "main_relation": main_relation,
    }
    snapshot_text = _build_tongshefa_snapshot(model)
    return {
        "analysis_type": "统摄法分析",
        "input_normalized": selected,
        "tongshefa": model,
        "snapshot_text": snapshot_text,
        "summary": f"已运行本地统摄法算法。本卦：左{base_left['name']}，右{base_right['name']}。主关系：{main_relation}。",
    }


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


def _build_otherbu_snapshot_text(
    input_normalized: Dict[str, Any], response: Dict[str, Any]
) -> str:
    chart_params = (
        ((response.get("chart") or {}).get("params") or {})
        if isinstance(response, dict)
        else {}
    )

    def chart_lines(chart_payload: Dict[str, Any]) -> List[str]:
        chart = (
            chart_payload.get("chart", {}) if isinstance(chart_payload, dict) else {}
        )
        houses = chart.get("houses") if isinstance(chart, dict) else []
        objects = chart.get("objects") if isinstance(chart, dict) else []
        lines: List[str] = []
        for house in houses or []:
            if not isinstance(house, dict):
                continue
            lines.append(house.get("id", "House"))
            in_house = [
                item
                for item in objects or []
                if isinstance(item, dict) and item.get("house") == house.get("id")
            ]
            if not in_house:
                lines.append("星体：无")
                continue
            for item in in_house:
                degree, minute = _split_degree(item.get("signlon", item.get("lon")))
                lines.append(
                    f"星体：{item.get('id')} {degree}˚{item.get('sign')}{minute}分"
                )
        return lines

    return _render_snapshot_text(
        [
            (
                "起盘信息",
                _join_lines(
                    [
                        f"日期：{input_normalized['date']} {input_normalized['time']}",
                        f"时区：{input_normalized['zone']}",
                        f"经纬度：{input_normalized.get('lon') or '无'} {input_normalized.get('lat') or '无'}",
                        f"传统模式：{'无三王星' if input_normalized.get('tradition') else '含三王星'}",
                        f"宫制：{chart_params.get('houseSystemResolved') or 'equal'}",
                        f"黄道：{chart_params.get('zodiacLabelZh') or chart_params.get('zodiacMode') or 'tropical'}",
                        f"问题：{input_normalized.get('question') or '未填写'}",
                    ]
                ),
            ),
            (
                "骰子结果",
                _join_lines(
                    [
                        f"行星：{response.get('planet')}",
                        f"星座：{response.get('sign') or '无'}",
                        f"宫位：House{response.get('house', 0) + 1}",
                    ]
                ),
            ),
            (
                "骰子盘宫位与星体",
                _join_lines(chart_lines(response.get("diceChart", {}))) or "无",
            ),
            (
                "天象盘宫位与星体",
                _join_lines(chart_lines(response.get("chart", {}))) or "无",
            ),
        ]
    )


def build_otherbu_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
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
    normalized_sign = _normalize_sign(sign)
    normalized_planet = _normalize_planet(planet)
    normalized_house = _normalize_house_index(house)
    normalized_hsys = 8 if hsys is None else int(hsys)
    normalized_zodiacal = 0 if zodiacal is None else int(zodiacal)

    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "tradition": tradition,
        "sign": normalized_sign,
        "house": normalized_house,
        "planet": normalized_planet,
        "question": question,
        "hsys": normalized_hsys,
        "zodiacal": normalized_zodiacal,
    }
    base_chart = _build_local_chart_response(
        date_text=input_normalized["date"],
        time_text=input_normalized["time"],
        timezone_name=input_normalized["zone"],
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        tradition=tradition,
        include_su28=True,
        hsys=normalized_hsys,
        zodiacal=normalized_zodiacal,
        allow_extended_hsys=True,
    )
    dice_chart = copy.deepcopy(base_chart)
    target_longitude = ZODIAC_SIGNS.index(normalized_sign) * 30.0 + 15.0
    target_house_id = f"House{normalized_house + 1}"
    dice_house1_longitude = round(
        (target_longitude - normalized_house * 30.0 - 15.0) % 360.0, 4
    )
    dice_chart["chart"]["houses"] = _build_house_ring(
        dice_house1_longitude,
        step_degrees=30.0,
    )
    dice_chart["chart"]["angles"]["ascendant"] = dice_house1_longitude
    dice_chart["chart"]["angles"]["midheaven"] = round(
        (dice_house1_longitude + 90.0) % 360.0, 4
    )
    target_object = None
    for item in dice_chart["chart"]["objects"]:
        if item.get("id") == normalized_planet:
            target_object = item
            break
    if target_object is None:
        target_object = {
            "id": normalized_planet,
            "house": target_house_id,
            "sign": normalized_sign,
            "signlon": 15.0,
            "lon": round(target_longitude, 4),
            "su28": _su28_name(target_longitude),
        }
        dice_chart["chart"]["objects"].append(target_object)
    else:
        target_object.update(
            {
                "house": target_house_id,
                "sign": normalized_sign,
                "signlon": 15.0,
                "lon": round(target_longitude, 4),
                "su28": _su28_name(target_longitude),
            }
        )

    _reassign_chart_object_houses(
        dice_chart["chart"]["objects"],
        houses=dice_chart["chart"]["houses"],
    )
    dice_chart["params"]["diceHouse1Longitude"] = dice_house1_longitude
    dice_chart["params"]["diceTargetHouse"] = target_house_id

    interpretation = {
        "planet_keyword": PLANET_KEYWORDS.get(
            normalized_planet, PLANET_KEYWORDS["Sun"]
        ),
        "sign_keyword": SIGN_KEYWORDS.get(normalized_sign, SIGN_KEYWORDS["Aries"]),
        "house_keyword": HOUSE_KEYWORDS[normalized_house],
    }
    interpretation["summary"] = (
        f"{normalized_planet}主{interpretation['planet_keyword']}，"
        f"落{ZODIAC_SIGN_CN.get(normalized_sign, normalized_sign)}强调{interpretation['sign_keyword']}，"
        f"事情多会落在第{normalized_house + 1}宫的{interpretation['house_keyword']}。"
    )
    if question:
        interpretation["question_adjustment"] = (
            f"若问“{question}”，宜先抓住{normalized_planet}所示的主动线索。"
        )

    response = {
        "planet": normalized_planet,
        "sign": normalized_sign,
        "house": normalized_house,
        "diceChart": dice_chart,
        "chart": base_chart,
        "question": question,
        "interpretation": interpretation,
    }
    snapshot_text = _build_otherbu_snapshot_text(input_normalized, response)

    return {
        "analysis_type": "西洋游戏 / 占星骰子",
        "input_normalized": input_normalized,
        **response,
        "snapshot_text": snapshot_text,
        "summary": f"已生成西洋游戏 / 占星骰子结果。骰面：{normalized_planet} / {normalized_sign}。",
    }


def _build_qimen_nine_grid_lines(qimen: Dict[str, Any]) -> List[str]:
    palace_map = {
        palace.get("name"): palace
        for palace in qimen.get("palaces", []) or []
        if isinstance(palace, dict) and palace.get("name")
    }
    rows: List[str] = []
    for row in QIMEN_NINE_GRID_LAYOUT:
        cells: List[str] = []
        for palace_name in row:
            palace = palace_map.get(palace_name, {})
            cell = (
                f"{palace_name}："
                f"{palace.get('door', '无')}/"
                f"{palace.get('star', '无')}/"
                f"{palace.get('god', '无')}"
            )
            if palace.get("content_palace") and (
                palace.get("content_palace") != palace.get("name")
                or palace.get("content_trigram") != palace.get("trigram")
            ):
                cell += (
                    f" <- {palace.get('content_palace', '无')}/"
                    f"{palace.get('content_trigram', '无')}"
                )
            cells.append(cell)
        rows.append(" | ".join(cells))
    return rows


def build_qimen_snapshot_text(*, seed: MetaphysicsSeed, qimen: Dict[str, Any]) -> str:
    zhifu = qimen.get("zhifu") or {}
    zhishi = qimen.get("zhishi") or {}
    palace_map = {
        palace.get("name"): palace
        for palace in qimen.get("palaces", []) or []
        if isinstance(palace, dict) and palace.get("name")
    }
    zhifu_palace = palace_map.get(zhifu.get("palace"), {})
    zhishi_palace = palace_map.get(zhishi.get("palace"), {})

    def _content_note(item: Dict[str, Any]) -> str:
        if not item.get("content_palace"):
            return ""
        if item.get("content_palace") == item.get("palace") and item.get(
            "content_trigram"
        ) == item.get("trigram"):
            return ""
        return (
            f"；内容来源：{item.get('content_palace', '无')} / "
            f"{item.get('content_trigram', '无')}"
        )

    sections = [
        (
            "起盘信息",
            _join_lines(
                [
                    f"农历：{(seed.calendar_context.get('lunar_calendar') or {}).get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时",
                    "时间算法：本地节气换月",
                    "换日：子初换日",
                ]
            ),
        ),
        (
            "盘型",
            _join_lines(
                [
                    f"当前节气：{(seed.calendar_context.get('current_solar_term') or {}).get('name', '无')}",
                    f"下个节气：{(seed.calendar_context.get('next_solar_term') or {}).get('name', '无')}",
                    f"盘型：{qimen.get('ju_text', '无')}",
                    f"遁型：{qimen.get('dun_type', '无')}",
                    f"三元：{qimen.get('yuan', '无')}",
                    f"符头：{qimen.get('fu_tou', '无')}",
                    f"旬首：{qimen.get('xun_head', '无')}",
                    f"空亡：{qimen.get('kongwang', '无')}",
                ]
            ),
        ),
        (
            "盘面要素",
            _join_lines(
                [
                    (
                        f"值符：{zhifu.get('star', '无')}在{zhifu.get('palace', '无')}"
                        + _content_note(zhifu)
                    ),
                    (
                        f"值使：{zhishi.get('door', '无')}在{zhishi.get('palace', '无')}"
                        + _content_note(zhishi)
                    ),
                    f"布局：{qimen.get('layout', 'direct')}",
                    f"参考句：{qimen.get('reference', '无')}",
                ]
            ),
        ),
        (
            "奇门演卦",
            _join_lines(
                [
                    f"伏使卦：{(qimen.get('fushi_hexagram') or {}).get('name', '无')} / {(qimen.get('fushi_hexagram') or {}).get('binary_code', '无')}",
                    f"值符宫门卦：{(zhifu_palace.get('door_hexagram') or {}).get('name', '无')}",
                    f"值使宫门卦：{(zhishi_palace.get('door_hexagram') or {}).get('name', '无')}",
                ]
            ),
        ),
        ("八宫详解", _join_lines(_build_qimen_palace_overview_lines(qimen)) or "无"),
        ("九宫方盘", _join_lines(_build_qimen_nine_grid_lines(qimen)) or "无"),
        *_render_qimen_palace_sections(qimen),
    ]
    return _render_snapshot_text(sections)


def build_qimen_with_options(
    seed: MetaphysicsSeed, options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    board = build_qimen_board(seed)
    normalized_options = dict(options or {})
    if not normalized_options:
        return board

    layout = (
        str(_option_value(normalized_options, "layout") or "direct").strip().lower()
    )
    shift = _normalize_mode(
        _option_value(normalized_options, "palaceShift", "palace_shift"),
        default=0,
    )
    if layout in {"fly", "fei"}:
        shift += max(1, int(board.get("ju_number", 1)) % 9)
    reverse = layout in {"mirror", "reverse"}

    palaces = board.get("palaces", []) or []
    content_sequence = [
        {
            "content_palace": palace.get("name"),
            "content_trigram": palace.get("trigram"),
            "heaven_stem": palace.get("heaven_stem"),
            "earth_stem": palace.get("earth_stem"),
            "god": palace.get("god"),
            "door": palace.get("door"),
            "star": palace.get("star"),
        }
        for palace in palaces
        if isinstance(palace, dict)
    ]
    if reverse:
        content_sequence = list(reversed(content_sequence))
    content_sequence = _rotate_items(content_sequence, shift)

    transformed_palaces: List[Dict[str, Any]] = []
    for palace, content in zip(palaces, content_sequence):
        updated_palace = copy.deepcopy(palace)
        updated_palace.update(content)
        slot_trigram = palace.get("trigram", updated_palace.get("trigram"))
        updated_palace["trigram"] = slot_trigram
        palace_trigram = slot_trigram if slot_trigram != "中" else "坤"
        door_hexagram = build_hexagram(
            upper_name=palace_trigram,
            lower_name=QIMEN_DOOR_TO_TRIGRAM.get(updated_palace.get("door"), "坤"),
        )
        updated_palace["door_hexagram"] = {
            "name": door_hexagram["name"],
            "binary_code": door_hexagram["binary_code"],
        }
        transformed_palaces.append(updated_palace)

    zhifu_star = (board.get("zhifu") or {}).get("star")
    zhishi_door = (board.get("zhishi") or {}).get("door")
    zhifu_palace = next(
        (palace for palace in transformed_palaces if palace.get("star") == zhifu_star),
        transformed_palaces[0] if transformed_palaces else {},
    )
    zhishi_palace = next(
        (palace for palace in transformed_palaces if palace.get("door") == zhishi_door),
        transformed_palaces[0] if transformed_palaces else {},
    )
    fushi_hexagram = build_hexagram(
        upper_name=(
            zhifu_palace.get("trigram", "坤")
            if zhifu_palace.get("trigram") != "中"
            else "坤"
        ),
        lower_name=QIMEN_DOOR_TO_TRIGRAM.get(zhishi_palace.get("door"), "坤"),
    )

    transformed_board = copy.deepcopy(board)
    transformed_board.update(
        {
            "layout": layout,
            "options_applied": {
                "layout": layout,
                "palaceShift": shift,
                "reverse": reverse,
            },
            "palaces": transformed_palaces,
            "zhifu": {
                "star": zhifu_palace.get("star"),
                "palace": zhifu_palace.get("name"),
                "trigram": zhifu_palace.get("trigram"),
                "content_palace": zhifu_palace.get(
                    "content_palace", zhifu_palace.get("name")
                ),
                "content_trigram": zhifu_palace.get(
                    "content_trigram", zhifu_palace.get("trigram")
                ),
                "code": QIMEN_STAR_CODE_BY_DISPLAY.get(zhifu_palace.get("star")),
            },
            "zhishi": {
                "door": zhishi_palace.get("door"),
                "palace": zhishi_palace.get("name"),
                "trigram": zhishi_palace.get("trigram"),
                "content_palace": zhishi_palace.get(
                    "content_palace", zhishi_palace.get("name")
                ),
                "content_trigram": zhishi_palace.get(
                    "content_trigram", zhishi_palace.get("trigram")
                ),
                "code": QIMEN_DOOR_CODE_BY_DISPLAY.get(zhishi_palace.get("door")),
            },
            "fushi_hexagram": {
                "name": fushi_hexagram["name"],
                "binary_code": fushi_hexagram["binary_code"],
            },
            "reference": SANSHI_REFERENCES[shift % len(SANSHI_REFERENCES)],
        }
    )
    return transformed_board


def _build_taiyi_with_options(
    seed: MetaphysicsSeed, options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    board = build_taiyi_board(seed, gender="未知")
    normalized_options = dict(options or {})
    if not normalized_options:
        return board

    acc_num = _normalize_mode(
        _option_value(normalized_options, "accNum", "acc_num"), default=0
    )
    rotation = str(
        _option_value(normalized_options, "rotation") or board.get("rotation", "")
    ).strip() or board.get("rotation", "")

    palace_marks = board.get("palace_marks", []) or []
    palace_names = [
        item.get("palace")
        for item in palace_marks
        if isinstance(item, dict) and item.get("palace")
    ]
    marker_rows = [
        copy.deepcopy(item.get("markers", []))
        for item in palace_marks
        if isinstance(item, dict) and item.get("palace")
    ]

    if rotation.lower() in {"reverse", "逆布"}:
        marker_rows = list(reversed(marker_rows))
    marker_rows = _rotate_items(marker_rows, acc_num)
    transformed_marks = [
        {
            "palace": palace,
            "markers": rows,
        }
        for palace, rows in zip(palace_names, marker_rows)
    ]

    palace_index_map = {name: index for index, name in enumerate(palace_names)}
    taiyi_index = palace_index_map.get(board.get("taiyi_palace"), 0)
    wenchang_index = palace_index_map.get(board.get("wenchang_palace"), 0)
    transformed_taiyi_palace = palace_names[(taiyi_index + acc_num) % len(palace_names)]
    transformed_wenchang_palace = palace_names[
        (wenchang_index + acc_num) % len(palace_names)
    ]

    transformed_core_board = copy.deepcopy(board.get("core_board", {}))
    transformed_core_board["main_calculation"] = (
        f"{transformed_core_board.get('main_calculation', '太乙局')}（积数+{acc_num}）"
    )
    transformed_core_board["taiyi_position"] = f"太乙在{transformed_taiyi_palace}宫"
    transformed_core_board["wenchang_position"] = (
        f"文昌在{transformed_wenchang_palace}宫"
    )

    transformed_board = copy.deepcopy(board)
    transformed_board.update(
        {
            "rotation": rotation,
            "accumulation_label": f"{board.get('accumulation_label', '太乙积年')}偏移{acc_num}",
            "taiyi_palace": transformed_taiyi_palace,
            "wenchang_palace": transformed_wenchang_palace,
            "core_board": transformed_core_board,
            "palace_marks": transformed_marks,
            "options_applied": {
                "accNum": acc_num,
                "rotation": rotation,
            },
            "big_pattern": TAIYI_BIG_PATTERNS[acc_num % len(TAIYI_BIG_PATTERNS)],
            "small_pattern": TAIYI_SMALL_PATTERNS[acc_num % len(TAIYI_SMALL_PATTERNS)],
        }
    )
    return transformed_board


def _build_sanshi_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    qimen_seed: Optional[MetaphysicsSeed],
    qimen: Dict[str, Any],
    taiyi: Dict[str, Any],
    liureng: Dict[str, Any],
) -> str:
    qimen_display_seed = qimen_seed or seed
    palace_lines = _build_qimen_palace_overview_lines(qimen)
    taiyi_mark_lines = [
        f"{item.get('palace', '宫位')}：{'、'.join(item.get('markers', []) or []) or '无'}"
        for item in taiyi.get("palace_marks", []) or []
        if isinstance(item, dict)
    ]
    liureng_four_lesson_lines = [
        f"第{lesson.get('index', 0)}课：{lesson.get('text', '无')}（{lesson.get('relation', '无')}）"
        for lesson in liureng.get("four_lessons", []) or []
        if isinstance(lesson, dict)
    ]
    liureng_transmission_lines = []
    transmissions = (
        liureng.get("three_transmissions", {}) if isinstance(liureng, dict) else {}
    )
    for label, title in (("initial", "初传"), ("middle", "中传"), ("final", "末传")):
        item = transmissions.get(label, {}) if isinstance(transmissions, dict) else {}
        liureng_transmission_lines.append(
            f"{title}：{item.get('branch', '无')} / {item.get('relation', '无')} / {item.get('god', '无')}"
        )
    big_pattern = next(
        (item for item in liureng.get("patterns", []) or [] if isinstance(item, dict)),
        {},
    )
    month_general = (
        liureng.get("month_general", {}) if isinstance(liureng, dict) else {}
    )
    sections = [
        (
            "起盘信息",
            _join_lines(
                [
                    f"农历：{(seed.calendar_context.get('lunar_calendar') or {}).get('display') or '无'}",
                    f"直接时间：{qimen_display_seed.calendar_context['solar_datetime']}",
                    f"四柱：{qimen_display_seed.pillars['year'][0]}{qimen_display_seed.pillars['year'][1]}年/{qimen_display_seed.pillars['month'][0]}{qimen_display_seed.pillars['month'][1]}月/{qimen_display_seed.pillars['day'][0]}{qimen_display_seed.pillars['day'][1]}日/{qimen_display_seed.pillars['hour'][0]}{qimen_display_seed.pillars['hour'][1]}时",
                    (
                        "时间算法：真太阳时 + 本地节气换月"
                        if qimen_display_seed.applied_true_solar
                        else "时间算法：直接时间 + 本地节气换月"
                    ),
                    "换日：子初换日",
                    f"月将：{month_general.get('branch', '无')}({month_general.get('name', '无')})",
                    f"年命：{seed.pillars['year'][1]}",
                ]
            ),
        ),
        (
            "概览",
            _join_lines(
                [
                    f"盘型：{qimen.get('dun_type', '无')}{qimen.get('ju_number', '无')}局",
                    f"旬首：{qimen.get('xun_head', '无')}",
                    f"空亡：{qimen.get('kongwang', '无')}",
                    f"值符：{(qimen.get('zhifu') or {}).get('star', '无')}在{(qimen.get('zhifu') or {}).get('palace', '无')}",
                    f"值使：{(qimen.get('zhishi') or {}).get('door', '无')}在{(qimen.get('zhishi') or {}).get('palace', '无')}",
                    f"伏使卦：{(qimen.get('fushi_hexagram') or {}).get('name', '无')}",
                ]
            ),
        ),
        (
            "太乙",
            _join_lines(
                [
                    taiyi.get("style_label", "无"),
                    taiyi.get("accumulation_label", "无"),
                    taiyi.get("rotation", "无"),
                    taiyi.get("life_method", "无"),
                    taiyi.get("big_pattern", ""),
                    taiyi.get("small_pattern", ""),
                    (taiyi.get("core_board") or {}).get("main_calculation", "无"),
                    (taiyi.get("core_board") or {}).get("taiyi_position", "无"),
                    (taiyi.get("core_board") or {}).get("wenchang_position", "无"),
                    f"岁君：{(taiyi.get('core_board') or {}).get('suijun', '无')}",
                    f"合神：{(taiyi.get('core_board') or {}).get('heshen', '无')}",
                ]
            ),
        ),
        ("太乙十六宫", _join_lines(taiyi_mark_lines) or "无"),
        (
            "神煞",
            _join_lines(
                [
                    f"月将：{month_general.get('branch', '无')}({month_general.get('name', '无')})",
                    f"布盘：{liureng.get('board_order', '无')}",
                    f"课体：{liureng.get('board_style', '无')}",
                    f"旬首：{liureng.get('xun_head', '无')}",
                    f"空亡：{liureng.get('kongwang', '无')}",
                    f"贵人体系：{liureng.get('guiren_system', '无')}",
                ]
            ),
        ),
        ("大六壬", _join_lines(liureng_four_lesson_lines) or "无"),
        (
            "六壬大格",
            _join_lines(
                [
                    big_pattern.get("name", "无"),
                    f"依据：{big_pattern.get('basis', '无')}",
                ]
            ),
        ),
        ("六壬小局", _join_lines(liureng_transmission_lines) or "无"),
        ("六壬参考", _join_lines(liureng.get("overview", [])) or "无"),
        ("六壬概览", _join_lines(liureng.get("overview", [])) or "无"),
        ("八宫详解", _join_lines(palace_lines) or "无"),
        *_render_qimen_palace_sections(qimen),
    ]
    return _render_snapshot_text(sections)


def build_sanshiunited_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    qimen_options: Optional[Dict[str, Any]] = None,
    taiyi_options: Optional[Dict[str, Any]] = None,
    liureng_yue: Optional[str] = None,
    liureng_is_diurnal: Optional[bool] = None,
    use_true_solar_time: bool = False,
) -> Dict[str, Any]:
    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "qimen_options": qimen_options or {},
        "taiyi_options": taiyi_options or {},
        "liureng_yue": liureng_yue,
        "liureng_is_diurnal": liureng_is_diurnal,
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
    qimen_seed = _build_metaphysics_seed(
        date_text=input_normalized["date"],
        time_text=input_normalized["time"],
        timezone_name=input_normalized["zone"],
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        use_true_solar_time=bool(use_true_solar_time),
        day_pillar_strategy=DAY_GANZHI_STRATEGY_STANDARD,
    )
    qimen = build_qimen_with_options(qimen_seed, qimen_options)
    taiyi = _build_taiyi_with_options(seed, taiyi_options)
    liureng = build_liureng_board(
        seed,
        gender="未知",
        month_general_override=liureng_yue,
        is_diurnal_override=liureng_is_diurnal,
    )

    snapshot_text = _build_sanshi_snapshot_text(
        seed=seed,
        qimen_seed=qimen_seed,
        qimen=qimen,
        taiyi=taiyi,
        liureng=liureng,
    )
    analysis_context = _build_metaphysics_analysis_context(seed)
    four_pillars = create_pillar_dict(seed.pillars)
    qimen_analysis_context = _build_metaphysics_analysis_context(qimen_seed)
    qimen_four_pillars = create_pillar_dict(qimen_seed.pillars)
    subresults = {
        "qimen": {
            "analysis_type": "奇门遁甲",
            "analysis_context": qimen_analysis_context,
            "four_pillars": qimen_four_pillars,
            "calendar_context": qimen_seed.calendar_context,
            "pan": qimen,
        },
        "taiyi": {
            "analysis_type": "太乙神数",
            "analysis_context": analysis_context,
            "four_pillars": four_pillars,
            "calendar_context": seed.calendar_context,
            "pan": taiyi,
        },
        "liureng_gods": {
            "analysis_type": "大六壬起课",
            "analysis_context": analysis_context,
            "four_pillars": four_pillars,
            "calendar_context": seed.calendar_context,
            "liureng": liureng,
        },
    }

    return {
        "analysis_type": "三式合一",
        "analysis_context": analysis_context,
        "input_normalized": input_normalized,
        "qimen": qimen,
        "taiyi": taiyi,
        "liureng": liureng,
        "subresults": subresults,
        "sources": {
            "four_pillars": four_pillars,
            "calendar_context": seed.calendar_context,
        },
        "snapshot_text": snapshot_text,
        "summary": (
            f"已运行本地三式合一聚合算法。"
            f"奇门：{qimen['dun_type']}{qimen['ju_number']}局。"
            f"太乙：{(taiyi.get('core_board') or {}).get('main_calculation', '无')}。"
            f"六壬：{next((item.get('name') for item in liureng.get('patterns', []) if isinstance(item, dict)), '无')}。"
        ),
    }
