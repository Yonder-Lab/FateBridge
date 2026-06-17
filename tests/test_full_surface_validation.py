import asyncio
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import api as api_module
import fastmcp_server as mcp_module


def _birth_payload(
    *,
    name: str = "张三",
    gender: str = "男",
    birth_place: str = "上海",
    birth_longitude: float = 121.4737,
) -> dict:
    return {
        "name": name,
        "gender": gender,
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 15,
        "birth_hour": 10,
        "birth_minute": 30,
        "birth_timezone": "Asia/Shanghai",
        "birth_longitude": birth_longitude,
        "birth_place": birth_place,
        "use_true_solar_time": False,
    }


def _astro_payload(
    *,
    name: str = "测试者",
    birth_place: str = "上海",
    birth_longitude: float = 121.4667,
    birth_latitude: float = 31.2167,
) -> dict:
    return {
        "name": name,
        "birth_year": 1990,
        "birth_month": 4,
        "birth_day": 6,
        "birth_hour": 9,
        "birth_minute": 33,
        "birth_timezone": "Asia/Shanghai",
        "birth_longitude": birth_longitude,
        "birth_latitude": birth_latitude,
        "birth_place": birth_place,
    }


def _western_payload() -> dict:
    return {
        "name": "Alice",
        "birth_year": 1990,
        "birth_month": 5,
        "birth_day": 17,
        "birth_hour": 15,
        "birth_minute": 30,
        "birth_place": "上海",
        "birth_timezone": "Asia/Shanghai",
        "birth_longitude": 121.4737,
        "birth_latitude": 31.2304,
        "analysis_year": 2025,
        "analysis_month": 5,
        "analysis_day": 20,
        "pd_method": "astroapp_alchabitius",
        "pd_time_key": "Naibod",
        "pd_aspects": [0, 90, 180],
        "show_pd_bounds": True,
    }


def _metaphysics_payload() -> dict:
    return {
        "analysis_year": 2026,
        "analysis_month": 4,
        "analysis_day": 8,
        "analysis_hour": 9,
        "analysis_minute": 30,
        "analysis_timezone": "Asia/Shanghai",
        "analysis_longitude": 121.4737,
        "selected_sections": ["起盘信息", "九宫方盘"],
        "use_true_solar_time": False,
    }


def _compatibility_payload() -> dict:
    return {
        "person1_name": "甲",
        "person1_birth_year": 1990,
        "person1_birth_month": 5,
        "person1_birth_day": 15,
        "person1_birth_hour": 10,
        "person1_birth_minute": 30,
        "person1_gender": "男",
        "person1_birth_place": "上海",
        "person1_birth_timezone": "Asia/Shanghai",
        "person1_birth_longitude": 121.4737,
        "person2_name": "乙",
        "person2_birth_year": 1992,
        "person2_birth_month": 3,
        "person2_birth_day": 2,
        "person2_birth_hour": 8,
        "person2_birth_minute": 18,
        "person2_gender": "女",
        "person2_birth_place": "北京",
        "person2_birth_timezone": "Asia/Shanghai",
        "person2_birth_longitude": 116.4074,
        "relationship_type": "marriage",
    }


def _relative_payload() -> dict:
    return {
        "inner": {
            **_astro_payload(name="甲"),
        },
        "outer": {
            **_astro_payload(
                name="乙",
                birth_place="北京",
                birth_longitude=116.4074,
                birth_latitude=39.9042,
            ),
            "birth_year": 1992,
            "birth_month": 3,
            "birth_day": 2,
            "birth_hour": 8,
            "birth_minute": 18,
        },
        "relative_mode": "Composite",
        "hsys": 0,
        "zodiacal": 0,
    }


def _relative_mcp_kwargs() -> dict:
    return {
        "inner_birth_year": 1990,
        "inner_birth_month": 4,
        "inner_birth_day": 6,
        "inner_birth_hour": 9,
        "inner_birth_minute": 33,
        "inner_birth_timezone": "Asia/Shanghai",
        "inner_birth_longitude": 121.4667,
        "inner_birth_latitude": 31.2167,
        "inner_name": "甲",
        "inner_birth_place": "上海",
        "outer_birth_year": 1992,
        "outer_birth_month": 3,
        "outer_birth_day": 2,
        "outer_birth_hour": 8,
        "outer_birth_minute": 18,
        "outer_birth_timezone": "Asia/Shanghai",
        "outer_birth_longitude": 116.4074,
        "outer_birth_latitude": 39.9042,
        "outer_name": "乙",
        "outer_birth_place": "北京",
        "relative_mode": "Composite",
        "hsys": 0,
        "zodiacal": 0,
    }


def _phase2_base() -> dict:
    return {
        "date": "2028-04-06",
        "time": "09:33:00",
        "zone": "+08:00",
        "lat": "31n13",
        "lon": "121e28",
    }


def _export_content() -> str:
    return "\n".join(
        [
            "[起盘信息]",
            "排盘参数",
            "",
            "[八宫]",
            "这里是八宫详解内容",
            "",
            "[演卦]",
            "这里是奇门演卦内容",
        ]
    )


REST_POST_CASES = {
    "/api/calculate": lambda: _birth_payload(),
    "/api/cn/bazi/birth": lambda: _birth_payload(),
    "/api/cn/bazi/direct": lambda: {
        **_birth_payload(),
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 1,
    },
    "/api/cn/bazi/marriage": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/career": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/wealth": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/health": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/children": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/education": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/personality": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/relatives": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/cn/bazi/romance": lambda: {
        **_birth_payload(),
        "dayun_pillar": "壬戌",
        "liunian_pillar": "丁卯",
    },
    "/api/compatibility": _compatibility_payload,
    "/api/timing/comprehensive": lambda: {
        **_birth_payload(),
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 6,
        "analysis_hour": 21,
        "analysis_minute": 55,
        "analysis_age": 38,
        "selected_sections": ["查询信息", "综合影响"],
    },
    "/api/timing/dayun": lambda: {
        **_birth_payload(),
        "analysis_age": 38,
        "selected_sections": ["查询信息", "大运信息"],
    },
    "/api/timing/liunian": lambda: {
        **_birth_payload(),
        "target_year": 2028,
    },
    "/api/divination/gua": lambda: {
        "query": "111111",
        "lookup_mode": "hexagram",
        "selected_sections": ["查询信息", "义理摘要"],
    },
    "/api/cn/jieqi/year": lambda: {
        "year": 2028,
        "zone": "Asia/Shanghai",
        "lat": "31n13",
        "lon": "121e28",
        "jieqis": ["春分", "冬至"],
        "selected_sections": ["查询信息", "重点节气"],
    },
    "/api/cn/nongli/time": lambda: {
        "date": "2028-04-01",
        "time": "09:00:00",
        "zone": "Asia/Shanghai",
        "lon": "121e28",
        "selected_sections": ["农历上下文", "四柱上下文"],
    },
    "/api/cn/gua/meiyi": lambda: {
        "name": ["111", "000"],
        "selected_sections": ["查询概览", "批量结果"],
    },
    "/api/export/registry": lambda: {
        "technique": "qimen",
    },
    "/api/export/parse": lambda: {
        "technique": "qimen",
        "content": _export_content(),
        "selected_sections": ["起盘信息", "八宫详解", "奇门演卦"],
    },
    "/api/knowledge/registry": lambda: {
        "domain": "astro",
        "selected_sections": ["目录概览", "astro"],
    },
    "/api/knowledge/read": lambda: {
        "domain": "astro",
        "category": "aspect",
        "aspect_degree": 90,
        "object_a": "Sun",
        "object_b": "Jupiter",
        "selected_sections": ["查询信息", "知识正文"],
    },
    "/api/divination/meihua": lambda: {
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 1,
        "analysis_hour": 9,
        "analysis_minute": 0,
        "analysis_timezone": "Asia/Shanghai",
        "question": "事业推进节奏",
    },
    "/api/divination/tongshefa": lambda: {
        "taiyin": "巽",
        "taiyang": "坤",
        "shaoyang": "震",
        "shaoyin": "震",
    },
    "/api/divination/sixyao": lambda: {
        **_phase2_base(),
        "gpsLat": 31.2,
        "gpsLon": 121.4,
    },
    "/api/divination/suzhan": lambda: {
        **_phase2_base(),
        "szchart": 1,
        "szshape": 1,
        "house_start_mode": 2,
        "doubing_su28": False,
    },
    "/api/divination/otherbu": lambda: {
        **_phase2_base(),
        "sign": "Aries",
        "house": 6,
        "planet": "Sun",
        "question": "合作",
    },
    "/api/divination/sanshiunited": lambda: {
        **_phase2_base(),
        "qimen_options": {"layout": "fly"},
        "taiyi_options": {"accNum": 1},
        "liureng_yue": "申",
        "liureng_is_diurnal": False,
    },
    "/api/cn/ziwei/birth": lambda: {
        **_birth_payload(name="张三", gender="男"),
        "birth_year": 1994,
        "birth_month": 8,
        "birth_day": 23,
        "birth_hour": 14,
        "selected_sections": ["起盘信息", "宫位总览"],
    },
    "/api/cn/ziwei/rules": lambda: {
        "year_stem": "甲",
        "selected_sections": ["规则概览", "当前天干四化"],
    },
    "/api/cn/liureng/gods": lambda: {
        **_metaphysics_payload(),
        "gender": "男",
        "selected_sections": ["起盘信息", "三传"],
    },
    "/api/cn/liureng/runyear": lambda: {
        **_birth_payload(name="张三", gender="男"),
        "birth_year": 1994,
        "birth_month": 8,
        "birth_day": 23,
        "birth_hour": 14,
        "analysis_year": 2026,
        "analysis_month": 4,
        "analysis_day": 4,
        "analysis_hour": 21,
        "analysis_minute": 18,
        "analysis_timezone": "Asia/Shanghai",
        "analysis_longitude": 121.4737,
        "selected_sections": ["起盘信息", "行年"],
    },
    "/api/cn/qimen": lambda: {
        **_metaphysics_payload(),
        "qimen_options": {"layout": "rotating"},
    },
    "/api/cn/taiyi": lambda: {
        **_metaphysics_payload(),
        "gender": "男",
        "selected_sections": ["起盘信息", "太乙"],
    },
    "/api/cn/jinkou": lambda: {
        **_metaphysics_payload(),
        "gender": "男",
        "di_fen": "酉",
        "selected_sections": ["起盘信息", "金口诀四位"],
    },
    "/api/astro/chart": lambda: _astro_payload(),
    "/api/astro/chart13": lambda: _astro_payload(),
    "/api/astro/hellen": lambda: _astro_payload(),
    "/api/astro/guolao": lambda: _astro_payload(),
    "/api/astro/india": lambda: _astro_payload(),
    "/api/astro/germany": lambda: _astro_payload(),
    "/api/astro/relative": _relative_payload,
    "/api/astro/timing": _western_payload,
    "/api/astro/timing/solarreturn": _western_payload,
    "/api/astro/timing/lunarreturn": _western_payload,
    "/api/astro/timing/transit": _western_payload,
    "/api/astro/timing/solararc": _western_payload,
    "/api/astro/timing/givenyear": _western_payload,
    "/api/astro/timing/profection": _western_payload,
    "/api/astro/timing/pd": _western_payload,
    "/api/astro/timing/pdchart": _western_payload,
    "/api/astro/timing/zr": _western_payload,
    "/api/astro/timing/firdaria": _western_payload,
    "/api/astro/timing/decennials": _western_payload,
    "/api/timing/liuyue": lambda: {
        **_birth_payload(),
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 1,
        "selected_sections": ["查询信息", "流月信息"],
    },
    "/api/timing/liuri": lambda: {
        **_birth_payload(),
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 1,
        "analysis_hour": 9,
        "analysis_minute": 0,
        "selected_sections": ["查询信息", "流日信息"],
    },
    "/api/timing/liushi": lambda: {
        **_birth_payload(),
        "analysis_year": 2028,
        "analysis_month": 4,
        "analysis_day": 1,
        "analysis_hour": 21,
        "analysis_minute": 55,
        "selected_sections": ["查询信息", "流时信息"],
    },
    "/api/timing/jieqi": lambda: {
        **_birth_payload(),
        "target_year": 2028,
        "selected_sections": ["查询信息", "节点时间轴"],
    },
}

REST_GET_CASES = {
    "/health": lambda body: body["status"] == "healthy",
    "/ready": lambda body: body["status"] == "ready",
    "/metrics": lambda body: body is None,
}

MCP_CASES = {
    "analyze_destiny": ("analyze_destiny", _birth_payload),
    "bazi_birth": ("bazi_birth", _birth_payload),
    "bazi_direct": (
        "bazi_direct",
        lambda: {
            **_birth_payload(),
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 1,
        },
    ),
    "bazi_marriage": (
        "bazi_marriage",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_career": (
        "bazi_career",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_wealth": (
        "bazi_wealth",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_health": (
        "bazi_health",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_children": (
        "bazi_children",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_education": (
        "bazi_education",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_personality": (
        "bazi_personality",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_relatives": (
        "bazi_relatives",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "bazi_romance": (
        "bazi_romance",
        lambda: {**_birth_payload(), "dayun_pillar": "壬戌", "liunian_pillar": "丁卯"},
    ),
    "two_person_compatibility": ("two_person_compatibility", _compatibility_payload),
    "timing_analysis": (
        "timing_analysis",
        lambda: {
            **_birth_payload(),
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 6,
            "analysis_hour": 21,
            "analysis_minute": 55,
            "analysis_age": 38,
            "selected_sections": ["查询信息", "综合影响"],
        },
    ),
    "dayun_analysis": (
        "dayun_analysis",
        lambda: {
            **_birth_payload(),
            "analysis_age": 38,
            "selected_sections": ["查询信息", "大运信息"],
        },
    ),
    "liunian_analysis": (
        "liunian_analysis",
        lambda: {**_birth_payload(), "target_year": 2028},
    ),
    "liuyue_analysis": (
        "liuyue_analysis",
        lambda: {
            **_birth_payload(),
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 1,
            "selected_sections": ["查询信息", "流月信息"],
        },
    ),
    "astro_chart13": ("astro_chart13", _astro_payload),
    "astro_hellen_chart": ("astro_hellen_chart", _astro_payload),
    "astro_guolao_chart": ("astro_guolao_chart", _astro_payload),
    "astro_india_chart": ("astro_india_chart", _astro_payload),
    "astro_germany_chart": ("astro_germany_chart", _astro_payload),
    "export_registry": ("export_registry", lambda: {"technique": "qimen"}),
    "export_parse": (
        "export_parse",
        lambda: {
            "technique": "qimen",
            "content": _export_content(),
            "selected_sections": ["起盘信息", "八宫详解", "奇门演卦"],
        },
    ),
    "knowledge_registry": (
        "knowledge_registry",
        lambda: {"domain": "astro", "selected_sections": ["目录概览", "astro"]},
    ),
    "knowledge_read": (
        "knowledge_read",
        lambda: {
            "domain": "astro",
            "category": "aspect",
            "aspect_degree": 90,
            "object_a": "Sun",
            "object_b": "Jupiter",
            "selected_sections": ["查询信息", "知识正文"],
        },
    ),
    "jieqi_year": (
        "jieqi_year",
        lambda: {
            "year": 2028,
            "zone": "Asia/Shanghai",
            "lat": "31n13",
            "lon": "121e28",
            "jieqis": ["春分", "冬至"],
            "selected_sections": ["查询信息", "重点节气"],
        },
    ),
    "nongli_time": (
        "nongli_time",
        lambda: {
            "date": "2028-04-01",
            "time": "09:00:00",
            "zone": "Asia/Shanghai",
            "lon": "121e28",
            "selected_sections": ["农历上下文", "四柱上下文"],
        },
    ),
    "gua_meiyi": (
        "gua_meiyi",
        lambda: {"name": ["111", "000"], "selected_sections": ["查询概览", "批量结果"]},
    ),
    "gua_lookup": (
        "gua_lookup",
        lambda: {
            "query": "111111",
            "lookup_mode": "hexagram",
            "selected_sections": ["查询信息", "义理摘要"],
        },
    ),
    "meihua_analysis": (
        "meihua_analysis",
        lambda: {
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 1,
            "analysis_hour": 9,
            "analysis_minute": 0,
            "analysis_timezone": "Asia/Shanghai",
            "question": "事业推进节奏",
        },
    ),
    "tongshefa": (
        "tongshefa",
        lambda: {
            "taiyin": "巽",
            "taiyang": "坤",
            "shaoyang": "震",
            "shaoyin": "震",
        },
    ),
    "sixyao": ("sixyao", lambda: {**_phase2_base(), "gps_lat": 31.2, "gps_lon": 121.4}),
    "suzhan": (
        "suzhan",
        lambda: {
            **_phase2_base(),
            "gps_lat": 31.2,
            "gps_lon": 121.4,
            "szchart": 1,
            "szshape": 1,
            "house_start_mode": 2,
            "doubing_su28": False,
        },
    ),
    "otherbu": (
        "otherbu",
        lambda: {
            **_phase2_base(),
            "gps_lat": 31.2,
            "gps_lon": 121.4,
            "sign": "Aries",
            "house": 6,
            "planet": "Sun",
            "question": "合作",
        },
    ),
    "sanshiunited": (
        "sanshiunited",
        lambda: {
            **_phase2_base(),
            "gps_lat": 31.2,
            "gps_lon": 121.4,
            "qimen_options": {"layout": "fly"},
            "taiyi_options": {"accNum": 1},
            "liureng_yue": "申",
            "liureng_is_diurnal": False,
        },
    ),
    "ziwei_birth": (
        "ziwei_birth",
        lambda: {
            **_birth_payload(name="张三", gender="男"),
            "birth_year": 1994,
            "birth_month": 8,
            "birth_day": 23,
            "birth_hour": 14,
            "selected_sections": ["起盘信息", "宫位总览"],
        },
    ),
    "ziwei_rules": (
        "ziwei_rules",
        lambda: {"year_stem": "甲", "selected_sections": ["规则概览", "当前天干四化"]},
    ),
    "liureng_gods": (
        "liureng_gods",
        lambda: {
            **_metaphysics_payload(),
            "gender": "男",
            "selected_sections": ["起盘信息", "三传"],
        },
    ),
    "liureng_runyear": (
        "liureng_runyear",
        lambda: {
            **_birth_payload(name="张三", gender="男"),
            "birth_year": 1994,
            "birth_month": 8,
            "birth_day": 23,
            "birth_hour": 14,
            "analysis_year": 2026,
            "analysis_month": 4,
            "analysis_day": 4,
            "analysis_hour": 21,
            "analysis_minute": 18,
            "analysis_timezone": "Asia/Shanghai",
            "analysis_longitude": 121.4737,
            "selected_sections": ["起盘信息", "行年"],
        },
    ),
    "qimen": ("qimen", lambda: {**_metaphysics_payload(), "qimen_options": {"layout": "rotating"}}),
    "taiyi": (
        "taiyi",
        lambda: {
            **_metaphysics_payload(),
            "gender": "男",
            "selected_sections": ["起盘信息", "太乙"],
        },
    ),
    "jinkou": (
        "jinkou",
        lambda: {
            **_metaphysics_payload(),
            "gender": "男",
            "di_fen": "酉",
            "selected_sections": ["起盘信息", "金口诀四位"],
        },
    ),
    "liuri_analysis": (
        "liuri_analysis",
        lambda: {
            **_birth_payload(),
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 1,
            "analysis_hour": 9,
            "analysis_minute": 0,
            "selected_sections": ["查询信息", "流日信息"],
        },
    ),
    "liushi_analysis": (
        "liushi_analysis",
        lambda: {
            **_birth_payload(),
            "analysis_year": 2028,
            "analysis_month": 4,
            "analysis_day": 1,
            "analysis_hour": 21,
            "analysis_minute": 55,
            "selected_sections": ["查询信息", "流时信息"],
        },
    ),
    "jieqi_timeline_analysis": (
        "jieqi_timeline_analysis",
        lambda: {
            **_birth_payload(),
            "target_year": 2028,
            "selected_sections": ["查询信息", "节点时间轴"],
        },
    ),
    "astro_chart": ("astro_chart", _astro_payload),
    "astro_relative_chart": ("astro_relative_chart", _relative_mcp_kwargs),
    "western_timing_analysis": ("western_timing_analysis", _western_payload),
    "solarreturn": ("solarreturn", _western_payload),
    "lunarreturn": ("lunarreturn", _western_payload),
    "transit": ("transit", _western_payload),
    "solararc": ("solararc", _western_payload),
    "givenyear": ("givenyear", _western_payload),
    "profection": ("profection", _western_payload),
    "pd": ("pd", _western_payload),
    "pdchart": ("pdchart", _western_payload),
    "zr": ("zr", _western_payload),
    "firdaria": ("firdaria", _western_payload),
    "decennials": ("decennials", _western_payload),
}


def _build_client(monkeypatch) -> TestClient:
    api_module._reset_runtime_state_for_tests()
    monkeypatch.setattr(
        api_module,
        "API_KEY_AUTHENTICATOR",
        api_module.ApiKeyAuthenticator(header_name="X-API-Key", api_keys={}),
    )
    return TestClient(api_module.app)


def _assert_run_metadata(payload: dict) -> None:
    metadata = payload.get("run_metadata")
    assert isinstance(metadata, dict)
    assert metadata["tool_name"]
    assert metadata["engine"]
    assert metadata["run_id"]
    assert metadata["trace_id"]
    assert metadata["generated_at"]


def test_rest_case_map_covers_all_business_routes():
    actual_paths = {
        route.path
        for route in api_module.app.routes
        if getattr(route, "path", None)
        and not route.path.startswith("/openapi")
        and not route.path.startswith("/docs")
        and not route.path.startswith("/redoc")
    }
    expected_paths = set(REST_GET_CASES) | set(REST_POST_CASES)

    assert expected_paths == actual_paths


def test_mcp_case_map_covers_all_registered_tools():
    actual_names = {
        tool.name
        for tool in asyncio.run(mcp_module.app.list_tools(run_middleware=False))
    }

    assert set(MCP_CASES) == actual_names


def test_rest_health_endpoints_return_expected_contract(monkeypatch):
    client = _build_client(monkeypatch)

    for path, assertion in REST_GET_CASES.items():
        response = client.get(path)
        assert response.status_code == 200
        if path == "/metrics":
            assert "fatebridge_http_requests_total" in response.text
            continue
        assertion(response.json())


def test_rest_post_endpoints_all_accept_representative_payloads(monkeypatch):
    client = _build_client(monkeypatch)

    for path, payload_factory in REST_POST_CASES.items():
        response = client.post(path, json=payload_factory())
        assert response.status_code == 200, path
        body = response.json()
        assert "error" not in body, path
        _assert_run_metadata(body)


def test_fastmcp_tools_all_accept_representative_payloads():
    for _, (attr_name, kwargs_factory) in MCP_CASES.items():
        tool = getattr(mcp_module, attr_name)
        rendered = tool.fn(**kwargs_factory())
        body = json.loads(rendered)
        assert "error" not in body, attr_name
        _assert_run_metadata(body)
