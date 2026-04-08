"""
Phase 2 local technique helpers for FateBridge.

These helpers implement the Phase 2 local-technique surface with offline
Python logic that fits the current FateBridge architecture and reuses the
repo's existing local engines whenever possible.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from .almanac import build_calendar_context, localize_datetime
from .astrology import build_astro_birth_info, build_core_chart_payload
from .calendar import BaZiCalendar
from .divination import (
    BAGUA_BY_NAME,
    HEXAGRAM_NAMES,
    build_hexagram,
    lookup_hexagram_by_code,
)
from .metaphysics import (
    MetaphysicsSeed,
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    build_liureng_board,
    build_qimen_board,
    build_taiyi_board,
)
from ..utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
    calculate_solar_time_adjustment,
    create_pillar_dict,
)


GEO_COORDINATE_RE = re.compile(
    r"^\s*(?P<degrees>-?\d+(?:\.\d+)?)(?:(?P<direction>[NSEWnsew])(?P<minutes>\d+(?:\.\d+)?))?\s*$"
)

SU28_NAMES = [
    "角",
    "亢",
    "氐",
    "房",
    "心",
    "尾",
    "箕",
    "斗",
    "牛",
    "女",
    "虚",
    "危",
    "室",
    "壁",
    "奎",
    "娄",
    "胃",
    "昴",
    "毕",
    "觜",
    "参",
    "井",
    "鬼",
    "柳",
    "星",
    "张",
    "翼",
    "轸",
]

ZODIAC_SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

ZODIAC_SIGN_CN = {
    "Aries": "白羊座",
    "Taurus": "金牛座",
    "Gemini": "双子座",
    "Cancer": "巨蟹座",
    "Leo": "狮子座",
    "Virgo": "处女座",
    "Libra": "天秤座",
    "Scorpio": "天蝎座",
    "Sagittarius": "射手座",
    "Capricorn": "摩羯座",
    "Aquarius": "水瓶座",
    "Pisces": "双鱼座",
}

PLANET_DEFS = [
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

TRADITIONAL_PLANETS = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
OUTER_PLANETS = {"Uranus", "Neptune", "Pluto"}

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

SIX_YAO_GODS = ["青龙", "朱雀", "勾陈", "腾蛇", "白虎", "玄武"]
SIX_YAO_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]

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
SANSHI_REFERENCES = [
    "门迫逢旺，先阻后成。",
    "先整队形，再抢窗口。",
    "利于借势，不利单点硬冲。",
    "宜先稳住节奏，再谈放大。",
    "外部有助，内部更要对齐。",
    "此局贵在先定边界后发力。",
]


def _option_value(options: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in options and options[key] is not None:
            return options[key]
    return None


def _rotate_items(items: List[Any], shift: int) -> List[Any]:
    if not items:
        return []
    normalized_shift = shift % len(items)
    if normalized_shift == 0:
        return list(items)
    return list(items[normalized_shift:] + items[:normalized_shift])


def _join_lines(lines: List[str]) -> str:
    return "\n".join(line for line in lines if line).strip()


def _render_snapshot_text(sections: List[Tuple[str, str]]) -> str:
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body:
            blocks.append(body.strip())
        blocks.append("")
    return "\n".join(blocks).strip()


def _normalize_date_text(date_text: str) -> str:
    return (date_text or "").strip().replace("/", "-")


def _normalize_time_text(time_text: str) -> str:
    value = (time_text or "").strip()
    if not value:
        return "00:00:00"
    if len(value.split(":")) == 2:
        return f"{value}:00"
    return value


def parse_phase2_datetime(
    date_text: str,
    time_text: str,
    timezone_name: Optional[str] = None,
) -> datetime:
    moment = datetime.fromisoformat(
        f"{_normalize_date_text(date_text)} {_normalize_time_text(time_text)}"
    )
    return localize_datetime(moment, timezone_name or DEFAULT_BIRTH_TIMEZONE)


def parse_geo_coordinate(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)

    match = GEO_COORDINATE_RE.match(str(value))
    if not match:
        return None

    degrees = float(match.group("degrees"))
    direction = (match.group("direction") or "").upper()
    minutes = float(match.group("minutes") or "0")

    if direction:
        decimal = abs(degrees) + minutes / 60.0
        if direction in {"S", "W"}:
            decimal *= -1
        return decimal

    return degrees


def _julian_day(moment: datetime) -> float:
    utc_moment = moment.astimezone(timezone.utc) if moment.tzinfo else moment
    timestamp = utc_moment.timestamp()
    return timestamp / 86400.0 + 2440587.5


def _sign_name(longitude: float) -> str:
    return ZODIAC_SIGNS[int(longitude // 30) % 12]


def _sign_degree(longitude: float) -> float:
    return round(longitude % 30, 2)


def _su28_name(longitude: float) -> str:
    span = 360.0 / 28.0
    index = int(longitude // span) % 28
    return SU28_NAMES[index]


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
    for item in [definition["id"] for definition in PLANET_DEFS]:
        if item.casefold() == lowered:
            return item
    return "Sun"


def _normalize_house_index(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 11))


def _split_degree(value: Any) -> Tuple[int, int]:
    try:
        degree = float(value)
    except (TypeError, ValueError):
        return 0, 0
    if degree < 0:
        degree += 360.0
    degree %= 30.0
    whole_degree = int(degree)
    minute = int((degree - whole_degree) * 60)
    return whole_degree, minute


def _resolve_phase2_coordinates(
    *,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
) -> Tuple[float, float]:
    latitude = gps_lat if gps_lat is not None else parse_geo_coordinate(lat)
    longitude = gps_lon if gps_lon is not None else parse_geo_coordinate(lon)
    return latitude or 31.2167, longitude or 121.4667


def _build_phase2_birth_info(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str],
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
):
    moment = parse_phase2_datetime(date_text, time_text, timezone_name)
    latitude, longitude = _resolve_phase2_coordinates(
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )
    birth_info = build_astro_birth_info(
        birth_year=moment.year,
        birth_month=moment.month,
        birth_day=moment.day,
        birth_hour=moment.hour,
        birth_minute=moment.minute,
        birth_timezone=timezone_name or DEFAULT_BIRTH_TIMEZONE,
        birth_longitude=longitude,
        birth_latitude=latitude,
    )
    return birth_info, latitude, longitude


def _normalize_mode(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _phase2_house_step(shape_mode: int) -> float:
    return -30.0 if shape_mode % 2 else 30.0


def _display_house_system_name(house_system: Any) -> Optional[str]:
    name = str(house_system or "").strip()
    if not name:
        return None
    if name == "equal_mc":
        return "equal"
    return name


def _build_phase2_house_ring(
    house1_longitude: float,
    *,
    step_degrees: float = 30.0,
) -> List[Dict[str, Any]]:
    houses: List[Dict[str, Any]] = []
    for index in range(12):
        longitude = round((house1_longitude + index * step_degrees) % 360.0, 4)
        sign = _sign_name(longitude)
        houses.append(
            {
                "id": f"House{index + 1}",
                "lon": longitude,
                "sign": sign,
                "sign_zh": ZODIAC_SIGN_CN.get(sign),
            }
        )
    return houses


def _reindex_phase2_houses(source_houses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    houses: List[Dict[str, Any]] = []
    for index, item in enumerate(source_houses, start=1):
        longitude = round(float(item.get("lon", 0.0)), 4)
        sign = item.get("sign") or _sign_name(longitude)
        houses.append(
            {
                "id": f"House{index}",
                "lon": longitude,
                "sign": sign,
                "sign_zh": item.get("sign_zh") or ZODIAC_SIGN_CN.get(sign),
            }
        )
    return houses


def _reverse_phase2_houses(source_houses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not source_houses:
        return []
    return _reindex_phase2_houses(
        [source_houses[0], *reversed(source_houses[1:])]
    )


def _phase2_house_direction(houses: List[Dict[str, Any]]) -> str:
    if len(houses) < 2:
        return "forward"

    forward_steps = 0
    reverse_steps = 0
    for index, house in enumerate(houses):
        current = float(house.get("lon", 0.0))
        next_longitude = float(houses[(index + 1) % len(houses)].get("lon", 0.0))
        delta = (next_longitude - current) % 360.0
        if delta == 0:
            continue
        if delta <= 180.0:
            forward_steps += 1
        else:
            reverse_steps += 1

    return "reverse" if reverse_steps > forward_steps else "forward"


def _build_phase2_houses(
    core_payload: Dict[str, Any],
    *,
    house_start_mode: int = 1,
    shape_mode: int = 0,
    preserve_core_cusps: bool = False,
) -> Tuple[List[Dict[str, Any]], float, float]:
    ascendant = round(float(core_payload["angles"]["ascendant"]["longitude"]), 4)
    base_houses = _adapt_chart_houses(core_payload)
    if preserve_core_cusps and house_start_mode != 2 and base_houses:
        houses = _reindex_phase2_houses(base_houses)
        if shape_mode % 2:
            houses = _reverse_phase2_houses(houses)
        house_direction = _phase2_house_direction(houses)
        house_step = -30.0 if house_direction == "reverse" else 30.0
        house1_longitude = houses[0]["lon"]
        return houses, house1_longitude, house_step

    if house_start_mode == 2:
        house1_longitude = round(float(int(ascendant // 30) * 30), 4)
    else:
        house1_longitude = base_houses[0]["lon"] if base_houses else ascendant

    house_step = _phase2_house_step(shape_mode)
    houses = _build_phase2_house_ring(house1_longitude, step_degrees=house_step)
    return houses, house1_longitude, house_step


def _adapt_chart_houses(core_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    houses: List[Dict[str, Any]] = []
    for item in core_payload.get("houses", []):
        if not isinstance(item, dict):
            continue
        houses.append(
            {
                "id": f"House{item.get('house')}",
                "lon": round(float(item.get("cusp_longitude", 0.0)), 4),
                "sign": item.get("sign"),
                "sign_zh": item.get("sign_zh"),
            }
        )
    return houses


def _build_phase2_point_object(
    *,
    point_id: str,
    longitude: float,
    houses: List[Dict[str, Any]],
    include_su28: bool,
) -> Dict[str, Any]:
    sign = _sign_name(longitude)
    payload = {
        "id": point_id,
        "house": _house_id_for_phase2_houses(longitude, houses),
        "sign": sign,
        "signlon": round(longitude % 30.0, 4),
        "lon": round(longitude, 4),
    }
    if include_su28:
        payload["su28"] = _su28_name(longitude)
    return payload


def _adapt_chart_objects(
    core_payload: Dict[str, Any],
    *,
    tradition: bool,
    include_su28: bool,
    houses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    objects: List[Dict[str, Any]] = []
    for item in core_payload.get("planets", []):
        if not isinstance(item, dict):
            continue
        point_id = str(item.get("id") or "")
        if tradition and point_id in OUTER_PLANETS:
            continue
        longitude = round(float(item.get("longitude", 0.0)), 4)
        payload = {
            "id": point_id,
            "house": _house_id_for_phase2_houses(longitude, houses),
            "sign": item.get("sign"),
            "signlon": round(float(item.get("degree_in_sign", 0.0)), 4),
            "lon": longitude,
        }
        if include_su28:
            payload["su28"] = _su28_name(payload["lon"])
        objects.append(payload)

    north_node = next((item for item in objects if item.get("id") == "North Node"), None)
    if north_node is not None:
        south_node_longitude = round((float(north_node["lon"]) + 180.0) % 360.0, 4)
        objects.append(
            _build_phase2_point_object(
                point_id="South Node",
                longitude=south_node_longitude,
                houses=houses,
                include_su28=include_su28,
            )
        )

    sun = next((item for item in objects if item.get("id") == "Sun"), None)
    moon = next((item for item in objects if item.get("id") == "Moon"), None)
    if sun is not None and moon is not None:
        try:
            sun_house = int(str(sun["house"]).removeprefix("House"))
        except (TypeError, ValueError):
            sun_house = 7
        if sun_house >= 7:
            fortuna_longitude = (float(houses[0]["lon"]) + moon["lon"] - sun["lon"]) % 360.0
        else:
            fortuna_longitude = (float(houses[0]["lon"]) + sun["lon"] - moon["lon"]) % 360.0
        objects.append(
            _build_phase2_point_object(
                point_id="Pars Fortuna",
                longitude=fortuna_longitude,
                houses=houses,
                include_su28=include_su28,
            )
        )

    return objects


def _reassign_chart_object_houses(
    objects: List[Dict[str, Any]],
    *,
    houses: List[Dict[str, Any]],
) -> None:
    for item in objects:
        if not isinstance(item, dict):
            continue
        item["house"] = _house_id_for_phase2_houses(
            float(item.get("lon", 0.0)),
            houses,
        )


def _build_local_chart_response(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str],
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    tradition: bool = False,
    include_su28: bool = True,
    chart_variant: str = "chart",
    house_start_mode: int = 1,
    shape_mode: int = 0,
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    allow_extended_hsys: bool = False,
) -> Dict[str, Any]:
    birth_info, latitude, longitude = _build_phase2_birth_info(
        date_text=date_text,
        time_text=time_text,
        timezone_name=timezone_name,
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )
    resolved_hsys = None
    if chart_variant == "chart" and (hsys is not None or zodiacal is not None):
        resolved_hsys = 8 if hsys is None else int(hsys)
        resolved_zodiacal = 0 if zodiacal is None else int(zodiacal)
        if not allow_extended_hsys and resolved_hsys not in {0, 8}:
            raise ValueError(
                "Phase 2 本地盘当前仅支持 hsys=0(整宫制) 或 hsys=8(等宫制)。"
            )
        core_payload = build_core_chart_payload(
            birth_info,
            chart_variant,
            hsys=resolved_hsys,
            zodiacal=resolved_zodiacal,
        )
    else:
        core_payload = build_core_chart_payload(birth_info, chart_variant)
    houses, house1_longitude, house_step_degrees = _build_phase2_houses(
        core_payload,
        house_start_mode=house_start_mode,
        shape_mode=shape_mode,
        preserve_core_cusps=allow_extended_hsys,
    )
    objects = _adapt_chart_objects(
        core_payload,
        tradition=tradition,
        include_su28=include_su28,
        houses=houses,
    )
    params = {
        "date": _normalize_date_text(date_text),
        "time": _normalize_time_text(time_text),
        "zone": timezone_name or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "birthLatitude": round(latitude, 4),
        "birthLongitude": round(longitude, 4),
        "tradition": tradition,
        "chartVariant": chart_variant,
        "houseStartModeApplied": house_start_mode,
        "houseOrientation": "reverse" if house_step_degrees < 0 else "forward",
        "houseSystemResolved": _display_house_system_name(
            (core_payload.get("chart_profile") or {}).get("house_system")
        ),
        "zodiacMode": (core_payload.get("chart_profile") or {}).get("zodiac"),
    }
    if resolved_hsys is not None:
        params["hsys"] = resolved_hsys
    if resolved_hsys is not None:
        params["zodiacal"] = (core_payload.get("chart_profile") or {}).get("zodiacal")
        params["zodiacLabelZh"] = (core_payload.get("chart_profile") or {}).get("zodiac_label_zh")
    ayanamsha = (core_payload.get("chart_profile") or {}).get("ayanamsha")
    if ayanamsha:
        params["ayanamsha"] = ayanamsha
    if extra_params:
        params.update(extra_params)
    return {
        "params": params,
        "chart": {
            "ok": True,
            "houses": houses,
            "objects": objects,
            "angles": {
                "ascendant": round(float(core_payload["angles"]["ascendant"]["longitude"]), 4),
                "midheaven": round(float(core_payload["angles"]["midheaven"]["longitude"]), 4),
            },
        },
    }


def _house_longitudes(ascendant: float) -> List[Dict[str, float]]:
    return [
        {"id": f"House{index + 1}", "lon": round((ascendant + index * 30.0) % 360.0, 2)}
        for index in range(12)
    ]


def _house_id_for_phase2_houses(longitude: float, houses: List[Dict[str, Any]]) -> str:
    if not houses:
        return "House1"

    ring_direction = _phase2_house_direction(houses)
    normalized_longitude = float(longitude) % 360.0
    for index, house in enumerate(houses):
        current = float(house.get("lon", 0.0)) % 360.0
        next_longitude = float(houses[(index + 1) % len(houses)].get("lon", 0.0)) % 360.0
        if ring_direction == "reverse":
            span = (current - next_longitude) % 360.0 or 360.0
            distance = (current - normalized_longitude) % 360.0
        else:
            span = (next_longitude - current) % 360.0 or 360.0
            distance = (normalized_longitude - current) % 360.0
        if distance < span or abs(distance) < 1e-9:
            return str(house.get("id") or f"House{index + 1}")

    return str(houses[0].get("id") or "House1")


def _house_id_for_longitude(
    longitude: float,
    ascendant: float,
    *,
    step_degrees: float = 30.0,
) -> str:
    if step_degrees < 0:
        index = int(((ascendant - longitude) % 360.0) // 30.0) + 1
    else:
        index = int(((longitude - ascendant) % 360.0) // 30.0) + 1
    return f"House{index}"


def _planet_longitude(days_since_j2000: float, base: float, speed: float) -> float:
    return (base + speed * days_since_j2000) % 360.0


def build_pseudo_chart(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    tradition: bool = False,
) -> Dict[str, Any]:
    moment = parse_phase2_datetime(date_text, time_text, timezone_name)
    latitude = parse_geo_coordinate(lat) or 31.2167
    longitude = parse_geo_coordinate(lon) or 121.4667
    days_since_j2000 = _julian_day(moment) - 2451545.0

    local_hours = moment.hour + moment.minute / 60.0 + moment.second / 3600.0
    ascendant = (100.46 + 0.985647 * days_since_j2000 + longitude + local_hours * 15.0 + latitude * 0.25) % 360.0

    objects: List[Dict[str, Any]] = []
    for definition in PLANET_DEFS:
        if tradition and definition["id"] not in TRADITIONAL_PLANETS:
            continue
        longitude_value = round(
            _planet_longitude(days_since_j2000, definition["base"], definition["speed"]),
            2,
        )
        objects.append(
            {
                "id": definition["id"],
                "house": _house_id_for_longitude(longitude_value, ascendant),
                "sign": _sign_name(longitude_value),
                "signlon": _sign_degree(longitude_value),
                "lon": longitude_value,
                "su28": _su28_name(longitude_value),
            }
        )

    north_node_longitude = round((125.0 - 0.0529539 * days_since_j2000) % 360.0, 2)
    south_node_longitude = round((north_node_longitude + 180.0) % 360.0, 2)
    for object_id, longitude_value in (
        ("North Node", north_node_longitude),
        ("South Node", south_node_longitude),
    ):
        objects.append(
            {
                "id": object_id,
                "house": _house_id_for_longitude(longitude_value, ascendant),
                "sign": _sign_name(longitude_value),
                "signlon": _sign_degree(longitude_value),
                "lon": longitude_value,
                "su28": _su28_name(longitude_value),
            }
        )

    moon_longitude = next(item["lon"] for item in objects if item["id"] == "Moon")
    sun_longitude = next(item["lon"] for item in objects if item["id"] == "Sun")
    fortuna_longitude = round((moon_longitude - sun_longitude + ascendant) % 360.0, 2)
    objects.append(
        {
            "id": "Pars Fortuna",
            "house": _house_id_for_longitude(fortuna_longitude, ascendant),
            "sign": _sign_name(fortuna_longitude),
            "signlon": _sign_degree(fortuna_longitude),
            "lon": fortuna_longitude,
            "su28": _su28_name(fortuna_longitude),
        }
    )

    return {
        "params": {
            "date": _normalize_date_text(date_text),
            "time": _normalize_time_text(time_text),
            "zone": timezone_name or DEFAULT_BIRTH_TIMEZONE,
            "lat": lat,
            "lon": lon,
            "tradition": tradition,
        },
        "chart": {
            "ok": True,
            "houses": _house_longitudes(ascendant),
            "objects": objects,
            "angles": {"ascendant": round(ascendant, 2)},
        },
    }


def _phase2_bagua(name: str) -> Dict[str, Any]:
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


def _phase2_bagua_from_lines(lines: List[int]) -> Dict[str, Any]:
    for name, source in BAGUA_BY_NAME.items():
        if list(source["lines"]) == list(lines):
            return _phase2_bagua(name)
    return _phase2_bagua("乾")


def _phase2_hex(upper: Dict[str, Any], lower: Dict[str, Any]) -> Dict[str, Any]:
    lines = [*lower["value"], *upper["value"]]
    name = HEXAGRAM_NAMES.get((upper["name"], lower["name"]), f"{upper['cname']}{lower['cname']}")
    payload = {
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


def _phase2_mutual_hex(hexagram: Dict[str, Any]) -> Dict[str, Any]:
    lines = hexagram["lines"]
    mutual_lines = [lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]]
    lower = _phase2_bagua_from_lines(mutual_lines[:3])
    upper = _phase2_bagua_from_lines(mutual_lines[3:])
    return _phase2_hex(upper, lower)


def _phase2_opposite_hex(hexagram: Dict[str, Any]) -> Dict[str, Any]:
    opposite_lines = [0 if bit == 1 else 1 for bit in hexagram["lines"]]
    lower = _phase2_bagua_from_lines(opposite_lines[:3])
    upper = _phase2_bagua_from_lines(opposite_lines[3:])
    return _phase2_hex(upper, lower)


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
    taiyin_gua = _phase2_bagua(selected["taiyin"])
    taiyang_gua = _phase2_bagua(selected["taiyang"])
    shaoyang_gua = _phase2_bagua(selected["shaoyang"])
    shaoyin_gua = _phase2_bagua(selected["shaoyin"])

    base_left = _phase2_hex(taiyin_gua, shaoyang_gua)
    base_right = _phase2_hex(taiyang_gua, shaoyin_gua)
    mutual_left = _phase2_mutual_hex(base_left)
    mutual_right = _phase2_mutual_hex(base_right)
    opposite_left = _phase2_opposite_hex(base_left)
    opposite_right = _phase2_opposite_hex(base_right)
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


def _build_phase2_context(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str],
) -> Dict[str, Any]:
    moment = parse_phase2_datetime(date_text, time_text, timezone_name)
    timezone_value = timezone_name or DEFAULT_BIRTH_TIMEZONE
    pillars = BaZiCalendar.get_four_pillars(moment, timezone_name=timezone_value)
    calendar_context = build_calendar_context(moment, timezone_name=timezone_value, pillars=pillars)
    lunar = calendar_context.get("lunar_calendar") or {}
    nongli = {
        "birth": calendar_context["solar_datetime"],
        "nongli": lunar.get("display"),
        "yearJieqi": f"{pillars['year'][0]}{pillars['year'][1]}",
        "year": f"{pillars['year'][0]}{pillars['year'][1]}",
        "yearGanZi": f"{pillars['year'][0]}{pillars['year'][1]}",
        "monthGanZi": f"{pillars['month'][0]}{pillars['month'][1]}",
        "dayGanZi": f"{pillars['day'][0]}{pillars['day'][1]}",
        "time": f"{pillars['hour'][0]}{pillars['hour'][1]}",
        "jieqi": calendar_context["current_solar_term"]["name"],
        "jiedelta": calendar_context["solar_term_delta"]["description"],
        "monthInt": lunar.get("month"),
        "dayInt": lunar.get("day"),
        "month": lunar.get("month_cn"),
        "day": lunar.get("day_cn"),
        "leap": lunar.get("is_leap_month"),
    }
    return {
        "moment": moment,
        "timezone_name": timezone_value,
        "pillars": pillars,
        "calendar_context": calendar_context,
        "lunar": lunar,
        "nongli": nongli,
    }


def _build_phase2_metaphysics_seed(
    *,
    date_text: str,
    time_text: str,
    timezone_name: Optional[str],
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    use_true_solar_time: bool = False,
) -> MetaphysicsSeed:
    timezone_value = timezone_name or DEFAULT_BIRTH_TIMEZONE
    input_datetime_naive = datetime.fromisoformat(
        f"{_normalize_date_text(date_text)} {_normalize_time_text(time_text)}"
    )
    input_datetime = localize_datetime(input_datetime_naive, timezone_value)
    corrected_datetime = input_datetime
    total_correction_minutes = 0.0
    _, longitude = _resolve_phase2_coordinates(
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )

    if use_true_solar_time:
        adjustment = calculate_solar_time_adjustment(
            input_datetime_naive,
            timezone_value,
            longitude,
            strategy=SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
        )
        total_correction_minutes = adjustment["total_correction_minutes"]
        corrected_datetime = localize_datetime(
            input_datetime_naive + timedelta(
                minutes=total_correction_minutes
            ),
            timezone_value,
        )

    pillars = BaZiCalendar.get_four_pillars(
        corrected_datetime,
        timezone_name=timezone_value,
    )
    calendar_context = build_calendar_context(
        corrected_datetime,
        timezone_name=timezone_value,
        pillars=pillars,
    )
    return MetaphysicsSeed(
        input_datetime=input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=timezone_value,
        longitude=longitude,
        applied_true_solar=use_true_solar_time,
        total_correction_minutes=total_correction_minutes,
        pillars=pillars,
        calendar_context=calendar_context,
    )


def _normalize_gua_lines(lines: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in lines or []:
        if not isinstance(item, dict):
            continue
        # Keep legacy truthiness semantics here for request compatibility.
        value = 1 if bool(item.get("value")) else 0
        normalized.append(
            {
                "value": value,
                "change": bool(item.get("change")),
                "god": item.get("god"),
                "name": item.get("name"),
            }
        )
    return normalized[:6]


def _clean_code(code: Optional[str]) -> str:
    return "".join(ch for ch in str(code or "") if ch in {"0", "1"})


def _derive_gua_code(lines: List[Dict[str, Any]]) -> str:
    return "".join(str(int(line.get("value", 0))) for line in lines) or "000000"


def _derive_changed_code(lines: List[Dict[str, Any]]) -> str:
    chars: List[str] = []
    for line in lines:
        value = int(line.get("value", 0))
        if line.get("change"):
            value = 1 - value
        chars.append(str(value))
    return "".join(chars) or "000000"


def _lines_from_codes(current_code: str, changed_code: Optional[str] = None) -> List[Dict[str, Any]]:
    current = _clean_code(current_code)
    changed = _clean_code(changed_code or current_code)
    if len(current) != 6 or len(changed) != 6:
        raise ValueError("六爻卦码必须是 6 位 0/1 字符串。")

    normalized: List[Dict[str, Any]] = []
    for index, (current_bit, changed_bit) in enumerate(zip(current, changed)):
        normalized.append(
            {
                "value": int(current_bit),
                "change": current_bit != changed_bit,
                "god": SIX_YAO_GODS[index],
                "name": SIX_YAO_NAMES[index],
            }
        )
    return normalized


def _default_sixyao_lines() -> List[Dict[str, Any]]:
    return [
        {"value": 1, "change": False, "god": "青龙", "name": "初爻"},
        {"value": 0, "change": False, "god": "朱雀", "name": "二爻"},
        {"value": 1, "change": True, "god": "勾陈", "name": "三爻"},
        {"value": 0, "change": False, "god": "腾蛇", "name": "四爻"},
        {"value": 1, "change": False, "god": "白虎", "name": "五爻"},
        {"value": 0, "change": True, "god": "玄武", "name": "上爻"},
    ]


def _hexagram_desc_payload(code: str) -> Dict[str, Any]:
    detail = lookup_hexagram_by_code(code)
    return {
        "code": code,
        "name": detail.get("name"),
        "theme": detail.get("theme"),
        "卦辞": detail.get("judgement"),
        "象曰": detail.get("image"),
        "guidance": detail.get("guidance"),
        "favorable": detail.get("favorable"),
        "caution": detail.get("caution"),
        "summary": detail.get("summary"),
        "raw": detail,
    }


def _build_sixyao_snapshot_text(
    *,
    input_normalized: Dict[str, Any],
    nongli: Dict[str, Any],
    current_payload: Dict[str, Any],
    changed_payload: Dict[str, Any],
    lines: List[Dict[str, Any]],
) -> str:
    line_texts = []
    for index, line in enumerate(lines, start=1):
        yao_type = "阳爻" if int(line.get("value", 0)) == 1 else "阴爻"
        moving = "（动）" if line.get("change") else "（静）"
        extras = []
        if line.get("god"):
            extras.append(f"六神:{line['god']}")
        if line.get("name"):
            extras.append(f"爻名:{line['name']}")
        suffix = f"，{'，'.join(extras)}" if extras else ""
        line_texts.append(f"第{index}爻：{yao_type}{moving}{suffix}")

    judge_lines = []
    if input_normalized.get("question"):
        judge_lines.append(f"问题：{input_normalized['question']}")
    judge_lines.append(f"本卦：{current_payload.get('name', input_normalized['gua_code'])}")
    if current_payload.get("卦辞"):
        judge_lines.append(f"卦辞：{current_payload['卦辞']}")
    judge_lines.append(f"之卦：{changed_payload.get('name', input_normalized['changed_code'])}")
    if changed_payload.get("卦辞"):
        judge_lines.append(f"之卦卦辞：{changed_payload['卦辞']}")

    return _render_snapshot_text(
        [
            (
                "起盘信息",
                _join_lines(
                    [
                        f"日期：{input_normalized['date']} {input_normalized['time']}",
                        f"时区：{input_normalized['zone']}",
                        f"经纬度：{input_normalized.get('lon') or '无'} {input_normalized.get('lat') or '无'}",
                        f"起卦时间：{nongli.get('birth', '无')}",
                        f"干支：年{nongli.get('yearJieqi', '无')} 月{nongli.get('monthGanZi', '无')} 日{nongli.get('dayGanZi', '无')} 时{nongli.get('time', '无')}",
                    ]
                ),
            ),
            (
                "卦象",
                _join_lines(
                    [
                        f"本卦：{current_payload.get('name', input_normalized['gua_code'])}",
                        f"之卦：{changed_payload.get('name', input_normalized['changed_code'])}",
                    ]
                ),
            ),
            ("六爻与动爻", _join_lines(line_texts) or "暂无爻线数据"),
            ("卦辞与断语", _join_lines(judge_lines) or "无"),
        ]
    )


def build_sixyao_result(
    *,
    date: str,
    time: str,
    zone: Optional[str] = None,
    lat: Any = None,
    lon: Any = None,
    gps_lat: Optional[float] = None,
    gps_lon: Optional[float] = None,
    question: Optional[str] = None,
    gua_code: Optional[str] = None,
    changed_code: Optional[str] = None,
    lines: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    context = _build_phase2_context(date_text=date, time_text=time, timezone_name=zone)
    normalized_lines = _normalize_gua_lines(lines)
    if not normalized_lines:
        normalized_lines = _default_sixyao_lines()

    current_code = _clean_code(gua_code) or _derive_gua_code(normalized_lines)
    next_code = _clean_code(changed_code) or _derive_changed_code(normalized_lines)

    if len(current_code) != 6 or len(next_code) != 6:
        raise ValueError("六爻卦码必须是 6 位 0/1 字符串。")

    input_normalized = {
        "date": _normalize_date_text(date),
        "time": _normalize_time_text(time),
        "zone": zone or DEFAULT_BIRTH_TIMEZONE,
        "lat": lat,
        "lon": lon,
        "gpsLat": gps_lat,
        "gpsLon": gps_lon,
        "question": question,
        "gua_code": current_code,
        "changed_code": next_code,
    }
    current_payload = _hexagram_desc_payload(current_code)
    changed_payload = _hexagram_desc_payload(next_code)
    descriptions = {
        current_code: current_payload,
        next_code: changed_payload,
    }

    snapshot_text = _build_sixyao_snapshot_text(
        input_normalized=input_normalized,
        nongli=context["nongli"],
        current_payload=current_payload,
        changed_payload=changed_payload,
        lines=normalized_lines,
    )

    moving_lines = [index + 1 for index, line in enumerate(normalized_lines) if line.get("change")]
    return {
        "analysis_type": "六爻 / 易卦",
        "input_normalized": input_normalized,
        "nongli": context["nongli"],
        "current_code": current_code,
        "changed_code": next_code,
        "lines": normalized_lines,
        "moving_lines": moving_lines,
        "question": question,
        "descriptions": descriptions,
        "current_hexagram": current_payload["raw"],
        "changed_hexagram": changed_payload["raw"],
        "snapshot_text": snapshot_text,
        "summary": f"已生成易卦 / 六爻输出。本卦编码：{current_code}。之卦编码：{next_code}。",
    }


def _build_suzhan_snapshot_text(input_normalized: Dict[str, Any], response: Dict[str, Any]) -> str:
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
            house_lines.append(
                f"星曜：{item.get('id')} {star_text}".strip()
            )
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
    normalized_house_start_mode = 2 if _normalize_mode(house_start_mode, default=1) == 2 else 1
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


def _build_otherbu_snapshot_text(input_normalized: Dict[str, Any], response: Dict[str, Any]) -> str:
    chart_params = ((response.get("chart") or {}).get("params") or {}) if isinstance(response, dict) else {}

    def chart_lines(chart_payload: Dict[str, Any]) -> List[str]:
        chart = chart_payload.get("chart", {}) if isinstance(chart_payload, dict) else {}
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
            ("骰子盘宫位与星体", _join_lines(chart_lines(response.get("diceChart", {}))) or "无"),
            ("天象盘宫位与星体", _join_lines(chart_lines(response.get("chart", {}))) or "无"),
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
    dice_house1_longitude = round((target_longitude - normalized_house * 30.0 - 15.0) % 360.0, 4)
    dice_chart["chart"]["houses"] = _build_phase2_house_ring(
        dice_house1_longitude,
        step_degrees=30.0,
    )
    dice_chart["chart"]["angles"]["ascendant"] = dice_house1_longitude
    dice_chart["chart"]["angles"]["midheaven"] = round((dice_house1_longitude + 90.0) % 360.0, 4)
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
        "planet_keyword": PLANET_KEYWORDS.get(normalized_planet, PLANET_KEYWORDS["Sun"]),
        "sign_keyword": SIGN_KEYWORDS.get(normalized_sign, SIGN_KEYWORDS["Aries"]),
        "house_keyword": HOUSE_KEYWORDS[normalized_house],
    }
    interpretation["summary"] = (
        f"{normalized_planet}主{interpretation['planet_keyword']}，"
        f"落{ZODIAC_SIGN_CN.get(normalized_sign, normalized_sign)}强调{interpretation['sign_keyword']}，"
        f"事情多会落在第{normalized_house + 1}宫的{interpretation['house_keyword']}。"
    )
    if question:
        interpretation["question_adjustment"] = f"若问“{question}”，宜先抓住{normalized_planet}所示的主动线索。"

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


def _build_metaphysics_analysis_context(seed: MetaphysicsSeed) -> Dict[str, Any]:
    lunar_context = seed.calendar_context.get("lunar_calendar") or {}
    return {
        "input_datetime": seed.input_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "corrected_datetime": seed.corrected_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": seed.timezone,
        "longitude": seed.longitude,
        "applied_true_solar": seed.applied_true_solar,
        "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
        "total_correction_minutes": round(seed.total_correction_minutes, 2),
        "current_jieqi": seed.calendar_context["current_solar_term"]["name"],
        "next_jieqi": seed.calendar_context["next_solar_term"]["name"],
        "lunar_display": lunar_context.get("display"),
    }


def _render_qimen_palace_sections(qimen: Dict[str, Any]) -> List[Tuple[str, str]]:
    sections: List[Tuple[str, str]] = []
    for palace in qimen.get("palaces", []) or []:
        if not isinstance(palace, dict):
            continue
        content_palace = palace.get("content_palace")
        content_trigram = palace.get("content_trigram")
        content_line = ""
        if content_palace and (
            content_palace != palace.get("name")
            or content_trigram != palace.get("trigram")
        ):
            content_line = f"内容来源：{content_palace} / {content_trigram or '无'}"
        sections.append(
            (
                palace.get("name", "宫位"),
                _join_lines(
                    [
                        f"宫卦：{palace.get('trigram', '无')}",
                        content_line,
                        f"天盘干：{palace.get('heaven_stem', '无')}",
                        f"地盘干：{palace.get('earth_stem', '无')}",
                        f"八神：{palace.get('god', '无')}",
                        f"九星：{palace.get('star', '无')}",
                        f"八门：{palace.get('door', '无')}",
                        f"门卦：{(palace.get('door_hexagram') or {}).get('name', '无')}",
                    ]
                ),
            )
        )
    return sections


def _build_qimen_palace_overview_lines(qimen: Dict[str, Any]) -> List[str]:
    return [
        (
            f"{palace.get('name', '宫位')}："
            f"天盘干：{palace.get('heaven_stem', '无')}；"
            f"地盘干：{palace.get('earth_stem', '无')}；"
            f"八神：{palace.get('god', '无')}；"
            f"九星：{palace.get('star', '无')}；"
            f"八门：{palace.get('door', '无')}"
            + (
                f"；内容来源：{palace.get('content_palace', '无')} / {palace.get('content_trigram', '无')}"
                if palace.get("content_palace")
                and (
                    palace.get("content_palace") != palace.get("name")
                    or palace.get("content_trigram") != palace.get("trigram")
                )
                else ""
            )
        )
        for palace in qimen.get("palaces", []) or []
        if isinstance(palace, dict)
    ]


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
        if (
            item.get("content_palace") == item.get("palace")
            and item.get("content_trigram") == item.get("trigram")
        ):
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


def build_qimen_with_options(seed: MetaphysicsSeed, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    board = build_qimen_board(seed)
    normalized_options = dict(options or {})
    if not normalized_options:
        return board

    layout = str(_option_value(normalized_options, "layout") or "direct").strip().lower()
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
        upper_name=zhifu_palace.get("trigram", "坤") if zhifu_palace.get("trigram") != "中" else "坤",
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


def _build_taiyi_with_options(seed: MetaphysicsSeed, options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    board = build_taiyi_board(seed, gender="未知")
    normalized_options = dict(options or {})
    if not normalized_options:
        return board

    acc_num = _normalize_mode(_option_value(normalized_options, "accNum", "acc_num"), default=0)
    rotation = str(_option_value(normalized_options, "rotation") or board.get("rotation", "")).strip() or board.get("rotation", "")

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
    transformed_wenchang_palace = palace_names[(wenchang_index + acc_num) % len(palace_names)]

    transformed_core_board = copy.deepcopy(board.get("core_board", {}))
    transformed_core_board["main_calculation"] = (
        f"{transformed_core_board.get('main_calculation', '太乙局')}（积数+{acc_num}）"
    )
    transformed_core_board["taiyi_position"] = f"太乙在{transformed_taiyi_palace}宫"
    transformed_core_board["wenchang_position"] = f"文昌在{transformed_wenchang_palace}宫"

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
    qimen: Dict[str, Any],
    taiyi: Dict[str, Any],
    liureng: Dict[str, Any],
) -> str:
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
    transmissions = liureng.get("three_transmissions", {}) if isinstance(liureng, dict) else {}
    for label, title in (("initial", "初传"), ("middle", "中传"), ("final", "末传")):
        item = transmissions.get(label, {}) if isinstance(transmissions, dict) else {}
        liureng_transmission_lines.append(
            f"{title}：{item.get('branch', '无')} / {item.get('relation', '无')} / {item.get('god', '无')}"
        )
    big_pattern = next(
        (item for item in liureng.get("patterns", []) or [] if isinstance(item, dict)),
        {},
    )
    month_general = liureng.get("month_general", {}) if isinstance(liureng, dict) else {}
    sections = [
        (
            "起盘信息",
            _join_lines(
                [
                    f"农历：{(seed.calendar_context.get('lunar_calendar') or {}).get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时",
                    (
                        "时间算法：真太阳时 + 本地节气换月"
                        if seed.applied_true_solar
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
    seed = _build_phase2_metaphysics_seed(
        date_text=input_normalized["date"],
        time_text=input_normalized["time"],
        timezone_name=input_normalized["zone"],
        lat=lat,
        lon=lon,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
        use_true_solar_time=bool(use_true_solar_time),
    )
    qimen = build_qimen_with_options(seed, qimen_options)
    taiyi = _build_taiyi_with_options(seed, taiyi_options)
    liureng = build_liureng_board(
        seed,
        gender="未知",
        month_general_override=liureng_yue,
        is_diurnal_override=liureng_is_diurnal,
    )

    snapshot_text = _build_sanshi_snapshot_text(
        seed=seed,
        qimen=qimen,
        taiyi=taiyi,
        liureng=liureng,
    )
    analysis_context = _build_metaphysics_analysis_context(seed)
    four_pillars = create_pillar_dict(seed.pillars)
    subresults = {
        "qimen": {
            "analysis_type": "奇门遁甲",
            "analysis_context": analysis_context,
            "four_pillars": four_pillars,
            "calendar_context": seed.calendar_context,
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
