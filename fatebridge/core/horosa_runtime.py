"""
Optional bridge to an externally installed horosa-core-js runtime.

This keeps FateBridge's built-in Python fallback intact while allowing
qimen, taiyi, and jinkou calculations to delegate to Horosa's local JS
engine when the user explicitly provides a CLI path via environment.
"""

from __future__ import annotations

import copy
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .divination import build_hexagram
from .metaphysics import (
    MetaphysicsSeed,
    QIMEN_DOOR_TO_TRIGRAM,
    kongwang_for_ganzhi,
    xun_head_for_ganzhi,
)
from ..utils.helpers import parse_timezone_name


HOROSA_CORE_JS_CLI_ENV = "HOROSA_CORE_JS_CLI"
HOROSA_SKILL_CLI_ENV = "HOROSA_SKILL_CLI"
HOROSA_SKILL_PYTHONPATH_ENV = "HOROSA_SKILL_PYTHONPATH"
HOROSA_SKILL_DATA_DIR_ENV = "HOROSA_SKILL_DATA_DIR"
HOROSA_RUNTIME_ROOT_ENV = "HOROSA_RUNTIME_ROOT"

HOROSA_QIMEN_PALACE_LABELS = {
    1: "巽一宫",
    2: "离二宫",
    3: "坤三宫",
    4: "震四宫",
    5: "中五宫",
    6: "兑六宫",
    7: "艮七宫",
    8: "坎八宫",
    9: "乾九宫",
}

HOROSA_QIMEN_GOD_NAMES = {
    "符": "值符",
    "蛇": "螣蛇",
    "阴": "太阴",
    "合": "六合",
    "虎": "白虎",
    "玄": "玄武",
    "地": "九地",
    "天": "九天",
}

HOROSA_QIMEN_DOOR_NAMES = {
    "休": "休门",
    "生": "生门",
    "伤": "伤门",
    "杜": "杜门",
    "景": "景门",
    "死": "死门",
    "惊": "惊门",
    "开": "开门",
}

HOROSA_QIMEN_STAR_NAMES = {
    "蓬": "天蓬",
    "任": "天任",
    "冲": "天冲",
    "辅": "天辅",
    "英": "天英",
    "芮": "天芮",
    "柱": "天柱",
    "心": "天心",
    "禽": "天禽",
    "芮禽": "芮禽",
}

CHINESE_NUMERAL_TO_INT = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def _resolve_cli_path() -> Optional[Path]:
    raw_path = os.environ.get(HOROSA_CORE_JS_CLI_ENV, "").strip()
    if not raw_path:
        return None
    cli_path = Path(raw_path).expanduser().resolve()
    if not cli_path.is_file():
        raise FileNotFoundError(
            f"{HOROSA_CORE_JS_CLI_ENV} points to a missing file: {cli_path}"
        )
    return cli_path


def _prepare_horosa_skill_env() -> Dict[str, str]:
    env = os.environ.copy()
    env.setdefault(HOROSA_SKILL_DATA_DIR_ENV, "/tmp/fatebridge-horosa-skill")
    env.setdefault(HOROSA_RUNTIME_ROOT_ENV, "/tmp/fatebridge-horosa-runtime")
    extra_pythonpath = os.environ.get(HOROSA_SKILL_PYTHONPATH_ENV, "").strip()
    if extra_pythonpath:
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            extra_pythonpath
            if not current_pythonpath
            else f"{extra_pythonpath}{os.pathsep}{current_pythonpath}"
        )
    return env


def _run_horosa_skill_tool(
    tool_name: str, payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    raw_command = os.environ.get(HOROSA_SKILL_CLI_ENV, "").strip()
    if not raw_command:
        return None
    command_prefix = shlex.split(raw_command)
    if not command_prefix:
        return None

    command = [
        *command_prefix,
        "tool",
        "run",
        tool_name,
        "--stdin",
        "--no-save-result",
    ]
    completed = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
        env=_prepare_horosa_skill_env(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(f"horosa-skill {tool_name} failed: {details}")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError(
            f"horosa-skill {tool_name} returned invalid JSON"
        ) from exc

    if result.get("ok") is False:
        error = result.get("error") or {}
        raise RuntimeError(
            f"horosa-skill {tool_name} failed: {error.get('message') or result}"
        )

    return result


def _run_horosa_core_js(tool_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cli_path = _resolve_cli_path()
    if cli_path is None:
        return None

    command = ["node", str(cli_path), "run", tool_name]
    completed = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(f"horosa-core-js {tool_name} failed: {details}")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive branch
        raise RuntimeError(
            f"horosa-core-js {tool_name} returned invalid JSON"
        ) from exc

    if result.get("ok") is False:
        error = result.get("error") or {}
        raise RuntimeError(
            f"horosa-core-js {tool_name} failed: {error.get('message') or result}"
        )

    return result


def _format_ganzhi(pillar: Any) -> str:
    if isinstance(pillar, str):
        return pillar
    if isinstance(pillar, (list, tuple)) and len(pillar) == 2:
        return f"{pillar[0]}{pillar[1]}"
    return ""


def _analysis_moment(seed: MetaphysicsSeed) -> Any:
    return seed.corrected_datetime if seed.applied_true_solar else seed.input_datetime


def _gender_to_horosa_bool(gender: str) -> Optional[bool]:
    if gender == "男":
        return True
    if gender == "女":
        return False
    return None


def _format_horosa_coord(
    value: Optional[float], *, positive_suffix: str, negative_suffix: str
) -> str:
    if value is None:
        return ""
    absolute_value = abs(value)
    degrees = int(absolute_value)
    minutes = int(round((absolute_value - degrees) * 60))
    if minutes == 60:
        degrees += 1
        minutes = 0
    suffix = positive_suffix if value >= 0 else negative_suffix
    return f"{degrees}{suffix}{minutes:02d}"


def _build_horosa_skill_cn_payload(seed: MetaphysicsSeed) -> Dict[str, Any]:
    moment = _analysis_moment(seed)
    return {
        "date": moment.strftime("%Y-%m-%d"),
        "time": moment.strftime("%H:%M:%S"),
        "zone": _seed_zone_offset(seed),
        "lat": "",
        "lon": _format_horosa_coord(
            seed.longitude,
            positive_suffix="e",
            negative_suffix="w",
        ),
        "ad": 1,
        "after23NewDay": False,
    }


def _extract_horosa_skill_data(result: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    data = result.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"horosa-skill {tool_name} returned no data payload")
    return data


def build_horosa_phase2_tool(
    tool_name: str, payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    result = _run_horosa_skill_tool(tool_name, payload)
    if result is None:
        return None

    data = _extract_horosa_skill_data(result, tool_name)
    adapted = copy.deepcopy(data)
    input_normalized = result.get("input_normalized")
    if isinstance(input_normalized, dict):
        adapted["input_normalized"] = copy.deepcopy(input_normalized)
    adapted["engine"] = "horosa-skill-cli"
    return adapted


def _seed_zone_offset(seed: MetaphysicsSeed) -> str:
    tzinfo = parse_timezone_name(seed.timezone)
    offset = seed.corrected_datetime.replace(tzinfo=tzinfo).utcoffset()
    if offset is None:
        return "+08:00"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"{sign}{hours:02d}:{minutes:02d}"


def _build_horosa_nongli_payload(seed: MetaphysicsSeed) -> Dict[str, Any]:
    lunar = seed.calendar_context.get("lunar_calendar") or {}
    year_ganzhi = lunar.get("year_jieqi_ganzhi") or _format_ganzhi(seed.pillars["year"])
    month_ganzhi = lunar.get("month_ganzhi") or _format_ganzhi(seed.pillars["month"])
    day_ganzhi = lunar.get("day_ganzhi") or _format_ganzhi(seed.pillars["day"])
    time_ganzhi = lunar.get("time_ganzhi") or _format_ganzhi(seed.pillars["hour"])
    return {
        "birth": seed.corrected_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "year": year_ganzhi,
        "yearJieqi": year_ganzhi,
        "yearGanZi": year_ganzhi,
        "monthGanZi": month_ganzhi,
        "dayGanZi": day_ganzhi,
        "time": time_ganzhi,
        "jieqi": lunar.get("jieqi") or seed.calendar_context["current_solar_term"]["name"],
        "jiedelta": lunar.get("jiedelta")
        or seed.calendar_context["solar_term_delta"]["description"],
        "month": lunar.get("month_cn"),
        "day": lunar.get("day_cn"),
        "monthInt": lunar.get("month"),
        "dayInt": lunar.get("day"),
        "leap": bool(lunar.get("is_leap_month")),
        "bazi": {
            "fourColumns": {
                "year": {"ganzi": year_ganzhi},
                "month": {"ganzi": month_ganzhi},
                "day": {"ganzi": day_ganzhi},
                "time": {"ganzi": time_ganzhi},
            }
        },
    }


def _normalize_qimen_door(raw_door: str) -> str:
    if not raw_door:
        return ""
    if raw_door.endswith("门"):
        return raw_door
    return HOROSA_QIMEN_DOOR_NAMES.get(raw_door, f"{raw_door}门")


def _normalize_qimen_star(raw_star: str) -> str:
    if not raw_star:
        return ""
    if raw_star.startswith("天") or raw_star == "芮禽":
        return raw_star
    return HOROSA_QIMEN_STAR_NAMES.get(raw_star, raw_star)


def _normalize_qimen_god(raw_god: str) -> str:
    if not raw_god:
        return ""
    return HOROSA_QIMEN_GOD_NAMES.get(raw_god, raw_god)


def _qimen_hexagram_for_palace(trigram: str, door: str) -> Optional[Dict[str, str]]:
    lower_trigram = QIMEN_DOOR_TO_TRIGRAM.get(door)
    if not lower_trigram:
        return None
    upper_trigram = trigram if trigram != "中" else "坤"
    hexagram = build_hexagram(upper_name=upper_trigram, lower_name=lower_trigram)
    return {
        "name": hexagram["name"],
        "binary_code": hexagram["binary_code"],
    }


def _transform_horosa_qimen(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result["data"]
    cells = sorted(data.get("cells") or [], key=lambda item: item.get("palaceNum", 0))
    palace_lookup = {cell.get("palaceNum"): cell for cell in cells}

    palaces: List[Dict[str, Any]] = []
    for cell in cells:
        trigram = cell.get("palaceName") or ""
        door = _normalize_qimen_door(cell.get("door") or "")
        palaces.append(
            {
                "name": HOROSA_QIMEN_PALACE_LABELS.get(
                    cell.get("palaceNum", 0), f"{trigram}宫"
                ),
                "trigram": trigram,
                "heaven_stem": cell.get("tianGan") or "",
                "earth_stem": cell.get("diGan") or "",
                "god": _normalize_qimen_god(cell.get("god") or ""),
                "door": door,
                "star": _normalize_qimen_star(cell.get("tianXing") or ""),
                "door_hexagram": _qimen_hexagram_for_palace(trigram, door),
                "is_zhifu": bool(cell.get("isZhiFu")),
                "is_zhishi": bool(cell.get("isZhiShi")),
            }
        )

    zhifu_cell = palace_lookup.get(data.get("zhiFuPalace"))
    zhishi_cell = palace_lookup.get(data.get("zhiShiPalace"))
    fushi_hexagram = None
    if zhifu_cell and zhishi_cell:
        fushi_hexagram = _qimen_hexagram_for_palace(
            zhifu_cell.get("palaceName") or "",
            _normalize_qimen_door(data.get("zhiShi") or ""),
        )

    ju_char = f"{data.get('juShu') or ''}"[:1]
    kongwang = data.get("kongWang") or ""
    if kongwang and not kongwang.endswith("空"):
        kongwang = f"{kongwang}空"

    return {
        "engine": "horosa-core-js",
        "dun_type": data.get("yinYangDun"),
        "ju_number": CHINESE_NUMERAL_TO_INT.get(ju_char),
        "ju_text": data.get("juText"),
        "jieqi_text": data.get("jieqiText"),
        "fu_tou": data.get("fuTou"),
        "xun_head": data.get("xunShou"),
        "kongwang": kongwang,
        "zhifu": {
            "star": data.get("zhiFu"),
            "palace": HOROSA_QIMEN_PALACE_LABELS.get(data.get("zhiFuPalace")),
        },
        "zhishi": {
            "door": data.get("zhiShi"),
            "palace": HOROSA_QIMEN_PALACE_LABELS.get(data.get("zhiShiPalace")),
        },
        "fushi_hexagram": fushi_hexagram,
        "palaces": palaces,
        "snapshot_text": result.get("snapshot_text"),
    }


def build_horosa_qimen(seed: MetaphysicsSeed) -> Optional[Dict[str, Any]]:
    payload = {
        "date": seed.input_datetime.strftime("%Y-%m-%d"),
        "time": seed.input_datetime.strftime("%H:%M:%S"),
        "zone": _seed_zone_offset(seed),
        "lon": seed.longitude,
        "nongli": _build_horosa_nongli_payload(seed),
        "options": {
            "timeAlg": 0 if seed.applied_true_solar else 1,
        },
    }
    result = _run_horosa_core_js("qimen", payload)
    if result is None:
        return None
    return _transform_horosa_qimen(result)


def _transform_horosa_taiyi(result: Dict[str, Any]) -> Dict[str, Any]:
    data = result["data"]
    options = data.get("options") or {}
    return {
        "engine": "horosa-core-js",
        "style_label": options.get("styleLabel"),
        "accumulation_label": options.get("accumLabel"),
        "rotation": data.get("rotation") or "固定",
        "life_method": f"{options.get('sexLabel') or ''}命",
        "taiyi_palace": data.get("taiyiPalace"),
        "wenchang_palace": data.get("skyeyes"),
        "core_board": {
            "main_calculation": f"{data.get('homeCal')}局",
            "taiyi_position": f"太乙在{data.get('taiyiPalace')}宫",
            "wenchang_position": f"文昌在{data.get('skyeyes')}宫",
            "suijun": data.get("taishui"),
            "heshen": data.get("hegod"),
        },
        "palace_marks": [
            {
                "palace": palace.get("palace"),
                "markers": list(palace.get("items") or []),
            }
            for palace in data.get("palaces") or []
        ],
        "snapshot_text": result.get("snapshot_text"),
    }


def build_horosa_taiyi(seed: MetaphysicsSeed, gender: str) -> Optional[Dict[str, Any]]:
    calc_moment = seed.corrected_datetime if seed.applied_true_solar else seed.input_datetime
    payload = {
        "date": calc_moment.strftime("%Y-%m-%d"),
        "time": calc_moment.strftime("%H:%M:%S"),
        "zone": _seed_zone_offset(seed),
        "nongli": _build_horosa_nongli_payload(seed),
        "options": {
            "sex": gender if gender in {"男", "女"} else "男",
        },
    }
    result = _run_horosa_core_js("taiyi", payload)
    if result is None:
        return None
    return _transform_horosa_taiyi(result)


def _build_horosa_liureng_stub(
    seed: MetaphysicsSeed,
    *,
    yue_branch: Optional[str] = None,
    is_diurnal: Optional[bool] = None,
) -> Dict[str, Any]:
    day_ganzhi = _format_ganzhi(seed.pillars["day"])
    month_ganzhi = _format_ganzhi(seed.pillars["month"])
    year_ganzhi = _format_ganzhi(seed.pillars["year"])
    time_ganzhi = _format_ganzhi(seed.pillars["hour"])
    xun_head = xun_head_for_ganzhi(day_ganzhi)
    kongwang = kongwang_for_ganzhi(day_ganzhi)
    nongli = _build_horosa_nongli_payload(seed)
    return {
        "nongli": nongli,
        "fourColumns": {
            "year": {"ganzi": year_ganzhi},
            "month": {"ganzi": month_ganzhi},
            "day": {"ganzi": day_ganzhi},
            "time": {"ganzi": time_ganzhi},
        },
        "xun": {
            "旬首": xun_head,
            "旬空": kongwang.replace("空", ""),
        },
        "yue": yue_branch or seed.pillars["month"][1],
        "meta": {
            "is_diurnal": is_diurnal,
        },
    }


def build_horosa_liureng(
    seed: MetaphysicsSeed,
    *,
    month_general_override: Optional[str] = None,
    is_diurnal_override: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    payload = _build_horosa_skill_cn_payload(seed)
    if month_general_override is not None:
        payload["yue"] = month_general_override
    if is_diurnal_override is not None:
        payload["isDiurnal"] = is_diurnal_override

    result = _run_horosa_skill_tool("liureng_gods", payload)
    if result is None:
        return None

    data = _extract_horosa_skill_data(result, "liureng_gods")
    raw_liureng = data.get("liureng") if isinstance(data.get("liureng"), dict) else data
    if not isinstance(raw_liureng, dict):
        raise RuntimeError("horosa-skill liureng_gods returned an invalid liureng payload")

    adapted = copy.deepcopy(raw_liureng)
    adapted["engine"] = "horosa-skill-cli"
    if data.get("snapshot_text"):
        adapted["snapshot_text"] = data.get("snapshot_text")
    if data.get("export_snapshot") is not None:
        adapted["export_snapshot"] = data.get("export_snapshot")
    adapted["_raw_liureng"] = copy.deepcopy(raw_liureng)
    return adapted


def build_horosa_liureng_runyear(
    *,
    birth_seed: MetaphysicsSeed,
    analysis_seed: MetaphysicsSeed,
    gender: str,
) -> Optional[Dict[str, Any]]:
    payload = _build_horosa_skill_cn_payload(birth_seed)
    horosa_gender = _gender_to_horosa_bool(gender)
    if horosa_gender is not None:
        payload["gender"] = horosa_gender

    gua_moment = _analysis_moment(analysis_seed)
    payload.update(
        {
            "guaDate": gua_moment.strftime("%Y-%m-%d"),
            "guaTime": gua_moment.strftime("%H:%M:%S"),
            "guaZone": _seed_zone_offset(analysis_seed),
            "guaLat": "",
            "guaLon": _format_horosa_coord(
                analysis_seed.longitude,
                positive_suffix="e",
                negative_suffix="w",
            ),
            "guaAd": 1,
            "guaAfter23NewDay": False,
        }
    )

    result = _run_horosa_skill_tool("liureng_runyear", payload)
    if result is None:
        return None

    data = _extract_horosa_skill_data(result, "liureng_runyear")
    raw_liureng = (
        data.get("liureng") if isinstance(data.get("liureng"), dict) else None
    )
    liureng = copy.deepcopy(raw_liureng) if raw_liureng is not None else {}
    if liureng:
        liureng["engine"] = "horosa-skill-cli"
        if data.get("snapshot_text"):
            liureng["snapshot_text"] = data.get("snapshot_text")
        if data.get("export_snapshot") is not None:
            liureng["export_snapshot"] = data.get("export_snapshot")
        liureng["_raw_liureng"] = copy.deepcopy(raw_liureng)

    runyear = copy.deepcopy(data.get("runyear") or data.get("runYear") or {})
    if isinstance(runyear, dict):
        runyear["engine"] = "horosa-skill-cli"

    return {
        "liureng": liureng,
        "runyear": runyear,
    }


def _transform_horosa_jinkou(
    result: Dict[str, Any], *, gender: str, runyear: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    data = result["data"]
    kongwang = (data.get("topInfo") or {}).get("xunKong") or ""
    if kongwang and not kongwang.endswith("空"):
        kongwang = f"{kongwang}空"
    si_da_kong = data.get("siDaKong") or "无"
    if si_da_kong not in {"", "无"} and not si_da_kong.endswith("空"):
        si_da_kong = f"{si_da_kong}空"

    overview = {
        "di_fen": data.get("diFen"),
        "kongwang": kongwang,
        "si_da_kong": si_da_kong,
        "use_position": (data.get("yongYao") or {}).get("label"),
        "use_reason": (data.get("yongYao") or {}).get("reason"),
        "yuejiang": {
            "branch": data.get("jiangZi"),
            "name": data.get("jiangName"),
            "origin_branch": data.get("yuejiang"),
        },
        "guishen": {
            "start_branch": data.get("guiStartZi"),
            "branch": data.get("guiZi"),
            "name": data.get("guiName"),
        },
        "gender": gender,
    }
    if runyear:
        overview["runyear"] = runyear

    return {
        "engine": "horosa-core-js",
        "overview": overview,
        "rows": [
            {
                "label": row.get("label"),
                "content": row.get("content"),
                "shenjiang": row.get("shenjiang"),
                "element": row.get("elem"),
                "power": row.get("power"),
                "gan": row.get("gan"),
                "kong": row.get("kong"),
            }
            for row in data.get("rows") or []
        ],
        "shensha": [
            {
                "label": row.get("label"),
                "value": row.get("value"),
            }
            for row in data.get("shenshaRows") or []
        ],
        "snapshot_text": result.get("snapshot_text"),
    }


def build_horosa_jinkou(
    seed: MetaphysicsSeed,
    *,
    gender: str,
    di_fen: Optional[str],
    yue_branch: Optional[str] = None,
    runyear: Optional[Dict[str, Any]] = None,
    is_diurnal: Optional[bool] = None,
    liureng_payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    payload = {
        "diFen": di_fen,
        "liureng": copy.deepcopy(liureng_payload)
        if liureng_payload is not None
        else _build_horosa_liureng_stub(
            seed,
            yue_branch=yue_branch,
            is_diurnal=is_diurnal,
        ),
    }
    if is_diurnal is not None:
        payload["isDiurnal"] = is_diurnal
    result = _run_horosa_core_js("jinkou", payload)
    if result is None:
        return None
    return _transform_horosa_jinkou(result, gender=gender, runyear=runyear)
