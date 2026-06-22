"""
San Shi United (三式合一：奇门 + 太乙 + 六壬/金口 综合) board.

Pure relocation from the package facade.
"""

from __future__ import annotations

import copy

from ...utils.helpers import create_pillar_dict
from ..metaphysics import build_liureng_board, build_taiyi_board
from .chart import (
    DAY_GANZHI_STRATEGY_STANDARD,
    DEFAULT_BIRTH_TIMEZONE,
    Any,
    Dict,
    MetaphysicsSeed,
    Optional,
    _build_metaphysics_analysis_context,
    _build_metaphysics_seed,
    _build_qimen_palace_overview_lines,
    _join_lines,
    _normalize_date_text,
    _normalize_mode,
    _normalize_time_text,
    _option_value,
    _render_qimen_palace_sections,
    _render_snapshot_text,
    _rotate_items,
)
from .qimen import build_qimen_with_options

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
