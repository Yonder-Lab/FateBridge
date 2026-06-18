"""
Chinese metaphysics services for FateBridge.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fatebridge.core.almanac import (
    DAY_GANZHI_STRATEGY_STANDARD,
    build_calendar_context,
)
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.export_parser import parse_export_content
from fatebridge.core.metaphysics import (
    MetaphysicsSeed,
    build_jinkou_board,
    build_liureng_board,
    build_liureng_runyear,
    build_taiyi_board,
    build_ziwei_chart,
    build_ziwei_rules,
)
from fatebridge.core.phase2_local import (
    build_qimen_snapshot_text,
    build_qimen_with_options,
)
from fatebridge.utils.helpers import (
    DEFAULT_BIRTH_TIMEZONE,
    PersonInfo,
    SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
    calculate_solar_time_adjustment,
    create_pillar_dict,
    format_birth_datetime_display,
    handle_calculation_error,
    normalize_birth_time,
)


def _build_analysis_seed(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
    day_pillar_strategy: str = DAY_GANZHI_STRATEGY_STANDARD,
) -> MetaphysicsSeed:
    timezone_name = analysis_timezone or DEFAULT_BIRTH_TIMEZONE
    input_datetime = datetime(
        analysis_year,
        analysis_month,
        analysis_day,
        analysis_hour,
        analysis_minute,
    )
    corrected_datetime = input_datetime
    total_correction_minutes = 0.0

    if use_true_solar_time:
        if analysis_longitude is None:
            raise ValueError("真太阳时修正需要 analysis_longitude")

        adjustment = calculate_solar_time_adjustment(
            input_datetime,
            timezone_name,
            analysis_longitude,
            strategy=SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
        )
        total_correction_minutes = adjustment["total_correction_minutes"]
        corrected_datetime = input_datetime + timedelta(
            minutes=total_correction_minutes
        )

    pillars = BaZiCalendar.get_four_pillars(
        corrected_datetime,
        timezone_name=timezone_name,
        day_pillar_strategy=day_pillar_strategy,
    )
    calendar_context = build_calendar_context(
        corrected_datetime,
        timezone_name=timezone_name,
        pillars=pillars,
    )
    return MetaphysicsSeed(
        input_datetime=input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=timezone_name,
        longitude=analysis_longitude,
        applied_true_solar=use_true_solar_time,
        total_correction_minutes=total_correction_minutes,
        pillars=pillars,
        calendar_context=calendar_context,
    )


def _build_person_seed(person: PersonInfo) -> MetaphysicsSeed:
    normalized_birth_time = normalize_birth_time(
        person,
        solar_time_strategy=SOLAR_TIME_STRATEGY_LONGITUDE_ONLY,
    )
    corrected_datetime = normalized_birth_time.corrected_datetime
    pillars = BaZiCalendar.get_four_pillars(
        corrected_datetime,
        timezone_name=normalized_birth_time.timezone,
        day_pillar_strategy=DAY_GANZHI_STRATEGY_STANDARD,
    )
    calendar_context = build_calendar_context(
        corrected_datetime,
        timezone_name=normalized_birth_time.timezone,
        pillars=pillars,
    )
    return MetaphysicsSeed(
        input_datetime=normalized_birth_time.input_datetime,
        corrected_datetime=corrected_datetime,
        timezone=normalized_birth_time.timezone,
        longitude=normalized_birth_time.longitude,
        applied_true_solar=normalized_birth_time.applied,
        total_correction_minutes=normalized_birth_time.total_correction_minutes,
        pillars=pillars,
        calendar_context=calendar_context,
    )


def _analysis_context_payload(seed: MetaphysicsSeed) -> Dict[str, Any]:
    lunar_context = seed.calendar_context.get("lunar_calendar") or {}
    return {
        "input_datetime": seed.input_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "corrected_datetime": seed.corrected_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": seed.timezone,
        "longitude": seed.longitude,
        "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
        "total_correction_minutes": round(seed.total_correction_minutes, 2),
        "current_jieqi": seed.calendar_context["current_solar_term"]["name"],
        "next_jieqi": seed.calendar_context["next_solar_term"]["name"],
        "lunar_display": lunar_context.get("display"),
    }


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


def _join_snapshot_lines(lines: List[str]) -> str:
    return "\n".join(line for line in lines if line).strip()


def _render_snapshot_text(sections: List[tuple[str, str]]) -> str:
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body:
            blocks.append(body.strip())
        blocks.append("")
    return "\n".join(blocks).strip()


def _build_taiyi_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    taiyi: Dict[str, Any],
) -> str:
    lunar_calendar = seed.calendar_context.get("lunar_calendar") or {}
    mark_lines = [
        f"{item.get('palace', '宫位')}：{'、'.join(item.get('markers', []) or []) or '无'}"
        for item in taiyi.get("palace_marks", []) or []
        if isinstance(item, dict)
    ]
    sections = [
        (
            "起盘信息",
            _join_snapshot_lines(
                [
                    f"农历：{lunar_calendar.get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    (
                        f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/"
                        f"{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/"
                        f"{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/"
                        f"{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时"
                    ),
                    f"当前节气：{seed.calendar_context['current_solar_term']['name']}",
                    f"下个节气：{seed.calendar_context['next_solar_term']['name']}",
                    f"时间算法：{'真太阳时' if seed.applied_true_solar else '直接时间'}",
                ]
            ),
        ),
        (
            "太乙盘",
            _join_snapshot_lines(
                [
                    taiyi.get("style_label", "无"),
                    taiyi.get("accumulation_label", "无"),
                    f"布盘方向：{taiyi.get('rotation', '无')}",
                    f"命法：{taiyi.get('life_method', '无')}",
                    (taiyi.get("core_board") or {}).get("main_calculation", "无"),
                    (taiyi.get("core_board") or {}).get("taiyi_position", "无"),
                    (taiyi.get("core_board") or {}).get("wenchang_position", "无"),
                    f"岁君：{(taiyi.get('core_board') or {}).get('suijun', '无')}",
                    f"合神：{(taiyi.get('core_board') or {}).get('heshen', '无')}",
                ]
            ),
        ),
        ("十六宫标记", _join_snapshot_lines(mark_lines) or "无"),
    ]
    return _render_snapshot_text(sections)


def _build_liureng_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    liureng: Dict[str, Any],
    runyear: Optional[Dict[str, Any]] = None,
) -> str:
    lunar_calendar = seed.calendar_context.get("lunar_calendar") or {}
    month_general = liureng.get("month_general", {}) if isinstance(liureng, dict) else {}
    transmissions = liureng.get("three_transmissions", {}) if isinstance(liureng, dict) else {}
    pattern_lines = [
        f"{item.get('name', '无')}：{item.get('basis', '无')}"
        for item in liureng.get("patterns", []) or []
        if isinstance(item, dict)
    ]
    board_lines = [
        (
            f"{item.get('earth_branch', '无')}位："
            f"天盘{item.get('sky_branch', '无')}；"
            f"贵神{item.get('god', '无')}"
        )
        for item in liureng.get("twelve_board", []) or []
        if isinstance(item, dict)
    ]
    lesson_lines = []
    for lesson in liureng.get("four_lessons", []) or []:
        if not isinstance(lesson, dict):
            continue
        lesson_lines.append(
            (
                f"第{lesson.get('index', 0)}课：{lesson.get('text', '无')}；"
                f"六亲：{lesson.get('relation', '无')}；"
                f"上下：{lesson.get('upper_lower_relation', '无')}；"
                f"与日：{(lesson.get('relations') or {}).get('with_day_branch', '无')}；"
                f"与下：{(lesson.get('relations') or {}).get('with_lower_branch', '无')}"
                + ("；发用候选" if lesson.get("use_candidate") else "")
            )
        )
    transmission_lines = [
        f"取传法：{transmissions.get('method', '无')}",
        (
            f"初传：{(transmissions.get('initial') or {}).get('branch', '无')} / "
            f"{(transmissions.get('initial') or {}).get('relation', '无')} / "
            f"{(transmissions.get('initial') or {}).get('god', '无')}"
        ),
        (
            f"中传：{(transmissions.get('middle') or {}).get('branch', '无')} / "
            f"{(transmissions.get('middle') or {}).get('relation', '无')} / "
            f"{(transmissions.get('middle') or {}).get('god', '无')}"
        ),
        (
            f"末传：{(transmissions.get('final') or {}).get('branch', '无')} / "
            f"{(transmissions.get('final') or {}).get('relation', '无')} / "
            f"{(transmissions.get('final') or {}).get('god', '无')}"
        ),
    ]
    runyear_lines = ["无"]
    if runyear:
        runyear_lines = [
            f"年龄：{runyear.get('age', '无')}",
            f"行年：{runyear.get('ganzhi', '无')}",
            f"性别：{runyear.get('gender', '无')}",
        ]
    sections = [
        (
            "起盘信息",
            _join_snapshot_lines(
                [
                    f"农历：{lunar_calendar.get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    (
                        f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/"
                        f"{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/"
                        f"{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/"
                        f"{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时"
                    ),
                    f"当前节气：{seed.calendar_context['current_solar_term']['name']}",
                    f"下个节气：{seed.calendar_context['next_solar_term']['name']}",
                    f"时间算法：{'真太阳时' if seed.applied_true_solar else '直接时间'}",
                ]
            ),
        ),
        (
            "十二盘式",
            _join_snapshot_lines(
                [
                    f"月将：{month_general.get('branch', '无')}({month_general.get('name', '无')})",
                    f"课体：{liureng.get('board_style', '无')}",
                    f"细课体：{liureng.get('board_style_detail', '无')}",
                    f"盘序：{liureng.get('board_order', '无')}",
                    f"贵人体系：{liureng.get('guiren_system', '无')}",
                ]
            ),
        ),
        ("十二地盘/十二天盘/十二贵神对应", _join_snapshot_lines(board_lines) or "无"),
        ("四课", _join_snapshot_lines(lesson_lines) or "无"),
        ("三传", _join_snapshot_lines(transmission_lines) or "无"),
        ("行年", _join_snapshot_lines(runyear_lines) or "无"),
        (
            "旬日",
            _join_snapshot_lines(
                [
                    f"旬首：{liureng.get('xun_head', '无')}",
                    f"空亡：{liureng.get('kongwang', '无')}",
                ]
            ),
        ),
        (
            "旺衰",
            _join_snapshot_lines(
                [
                    f"月建十二长生所属：{liureng.get('twelve_life_element', '无')}",
                    f"昼夜：{'昼占' if (liureng.get('meta') or {}).get('is_diurnal') else '夜占'}",
                    f"发用课序：第{(liureng.get('meta') or {}).get('selected_lesson_index', '无')}课",
                ]
            ),
        ),
        (
            "基础神煞",
            _join_snapshot_lines(
                [
                    f"月将：{month_general.get('branch', '无')}({month_general.get('name', '无')})",
                    f"贵人体系：{liureng.get('guiren_system', '无')}",
                    f"盘序：{liureng.get('board_order', '无')}",
                ]
            ),
        ),
        (
            "干煞",
            _join_snapshot_lines(
                [
                    f"日干：{seed.pillars['day'][0]}",
                    f"旬首：{liureng.get('xun_head', '无')}",
                    f"空亡：{liureng.get('kongwang', '无')}",
                ]
            ),
        ),
        (
            "月煞",
            _join_snapshot_lines(
                [
                    f"月将：{month_general.get('branch', '无')}({month_general.get('name', '无')})",
                    f"当前节气：{(liureng.get('meta') or {}).get('current_term', '无')}",
                    f"月建所属五行：{liureng.get('twelve_life_element', '无')}",
                ]
            ),
        ),
        (
            "支煞",
            _join_snapshot_lines(
                [
                    f"日支：{seed.pillars['day'][1]}",
                    f"时支：{seed.pillars['hour'][1]}",
                    f"首传所临：{(transmissions.get('initial') or {}).get('branch', '无')}",
                ]
            ),
        ),
        (
            "岁煞",
            _join_snapshot_lines(
                [
                    f"岁干：{seed.pillars['year'][0]}",
                    f"岁支：{seed.pillars['year'][1]}",
                    f"问占性别：{(liureng.get('meta') or {}).get('questioner_gender', '无')}",
                ]
            ),
        ),
        (
            "十二长生",
            _join_snapshot_lines(
                [
                    f"月建十二长生所属：{liureng.get('twelve_life_element', '无')}",
                ]
            ),
        ),
        ("大格", _join_snapshot_lines(pattern_lines) or "无"),
        ("小局", _join_snapshot_lines(transmission_lines) or "无"),
        ("参考", _join_snapshot_lines(liureng.get("overview", [])) or "无"),
        (
            "概览",
            _join_snapshot_lines(
                [
                    f"{liureng.get('board_style', '无')}课 / {liureng.get('board_style_detail', '无')}",
                    (
                        f"月将{month_general.get('branch', '无')}({month_general.get('name', '无')})，"
                        f"{liureng.get('board_order', '无')}。"
                    ),
                    f"首传：{(transmissions.get('initial') or {}).get('branch', '无')}",
                ]
            ),
        ),
    ]
    return _render_snapshot_text(sections)


def _build_jinkou_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    jinkou: Dict[str, Any],
) -> str:
    lunar_calendar = seed.calendar_context.get("lunar_calendar") or {}
    overview = jinkou.get("overview", {}) if isinstance(jinkou, dict) else {}
    yuejiang = overview.get("yuejiang", {}) if isinstance(overview, dict) else {}
    guishen = overview.get("guishen", {}) if isinstance(overview, dict) else {}
    row_lines = []
    for row in jinkou.get("rows", []) or []:
        if not isinstance(row, dict):
            continue
        row_lines.append(
            (
                f"{row.get('label', '四位')}：{row.get('content', '无')}；"
                f"神将：{row.get('shenjiang', '无')}；"
                f"五行：{row.get('element', '无')}；"
                f"旺衰：{row.get('power', '无')}"
            )
        )
    shensha_lines = [
        f"{item.get('label', '神煞')}：{item.get('value', '无')}"
        for item in jinkou.get("shensha", []) or []
        if isinstance(item, dict)
    ]
    sections = [
        (
            "起盘信息",
            _join_snapshot_lines(
                [
                    f"农历：{lunar_calendar.get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    (
                        f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/"
                        f"{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/"
                        f"{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/"
                        f"{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时"
                    ),
                    f"当前节气：{seed.calendar_context['current_solar_term']['name']}",
                    f"下个节气：{seed.calendar_context['next_solar_term']['name']}",
                    f"时间算法：{'真太阳时' if seed.applied_true_solar else '直接时间'}",
                ]
            ),
        ),
        (
            "金口诀速览",
            _join_snapshot_lines(
                [
                    f"地分：{overview.get('di_fen', '无')}",
                    f"月将：{yuejiang.get('branch', '无')}({yuejiang.get('name', '无')})",
                    (
                        f"贵神：{guishen.get('branch', '无')}({guishen.get('name', '无')})；"
                        f"贵人起位：{guishen.get('start_branch', '无')}"
                    ),
                    (
                        f"课体：{overview.get('board_style', '无')} / "
                        f"{overview.get('board_style_detail', '无') or '无细课体'}"
                    ),
                    f"取传：{overview.get('transmission_method', '无')}",
                    f"用爻：{overview.get('use_position', '无')}",
                    f"取用依据：{overview.get('use_position_basis', '无')}",
                    f"空亡：{overview.get('kongwang', '无')}",
                    f"四大空亡：{overview.get('si_da_kong', '无')}",
                ]
            ),
        ),
        ("金口诀四位", _join_snapshot_lines(row_lines) or "无"),
        ("四位神煞", _join_snapshot_lines(shensha_lines) or "无"),
    ]
    return _render_snapshot_text(sections)


def _build_ziwei_snapshot_text(
    *,
    seed: MetaphysicsSeed,
    ziwei_birth: Dict[str, Any],
) -> str:
    lunar_calendar = seed.calendar_context.get("lunar_calendar") or {}
    ming_gong = ziwei_birth.get("ming_gong", {}) if isinstance(ziwei_birth, dict) else {}
    shen_gong = ziwei_birth.get("shen_gong", {}) if isinstance(ziwei_birth, dict) else {}
    sihua = ziwei_birth.get("sihua", {}) if isinstance(ziwei_birth, dict) else {}
    palace_lines = []
    for palace in ziwei_birth.get("palaces", []) or []:
        if not isinstance(palace, dict):
            continue
        palace_lines.append(
            (
                f"{palace.get('name', '宫位')}：{palace.get('ganzhi', '无')}；"
                f"大限：{palace.get('daxian', '无')}；"
                f"星曜：{'、'.join(palace.get('stars', []) or []) or '无'}"
            )
        )
    sections = [
        (
            "起盘信息",
            _join_snapshot_lines(
                [
                    f"农历：{lunar_calendar.get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    (
                        f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/"
                        f"{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/"
                        f"{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/"
                        f"{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时"
                    ),
                    f"当前节气：{seed.calendar_context['current_solar_term']['name']}",
                    f"下个节气：{seed.calendar_context['next_solar_term']['name']}",
                    f"时间算法：{'真太阳时' if seed.applied_true_solar else '直接时间'}",
                    f"生年天干：{ziwei_birth.get('year_stem', '无')}",
                    (
                        f"命宫：{ming_gong.get('branch', '无')} / "
                        f"{ming_gong.get('ganzhi', '无')}"
                    ),
                    (
                        f"身宫：{shen_gong.get('branch', '无')} / "
                        f"{shen_gong.get('ganzhi', '无')}"
                    ),
                ]
            ),
        ),
        (
            "宫位总览",
            _join_snapshot_lines(
                [
                    (
                        "四化："
                        f"化禄={sihua.get('化禄', '无')}；"
                        f"化权={sihua.get('化权', '无')}；"
                        f"化科={sihua.get('化科', '无')}；"
                        f"化忌={sihua.get('化忌', '无')}"
                    ),
                    *palace_lines,
                ]
            ),
        ),
    ]
    return _render_snapshot_text(sections)


def _build_ziwei_rules_snapshot_text(payload: Dict[str, Any]) -> str:
    rule_catalogue = payload.get("rule_catalogue", {}) if isinstance(payload, dict) else {}
    focused_rules = payload.get("focused_rules", {}) if isinstance(payload, dict) else {}
    palace_sequence = "、".join(rule_catalogue.get("palace_sequence", []) or []) or "无"
    sihua_lines = [
        f"{stem}："
        + "；".join(
            f"{label}={star}"
            for label, star in (mapping.items() if isinstance(mapping, dict) else [])
        )
        for stem, mapping in (rule_catalogue.get("sihua_by_year_stem", {}) or {}).items()
        if isinstance(mapping, dict)
    ]
    focused_sihua = focused_rules.get("sihua", {}) if isinstance(focused_rules, dict) else {}
    sections = [
        (
            "规则概览",
            _join_snapshot_lines(
                [
                    f"请求天干：{payload.get('requested_year_stem') or '全部'}",
                    f"引擎：{payload.get('engine', 'fatebridge-offline')}",
                ]
            ),
        ),
        ("宫位序列", palace_sequence),
        (
            "命身宫规则",
            _join_snapshot_lines(
                [
                    f"命宫：{rule_catalogue.get('ming_gong_method', '无')}",
                    f"身宫：{rule_catalogue.get('shen_gong_method', '无')}",
                ]
            ),
        ),
        ("四化总表", _join_snapshot_lines(sihua_lines) or "无"),
    ]
    if focused_sihua:
        sections.append(
            (
                "当前天干四化",
                _join_snapshot_lines(
                    [
                        f"天干：{focused_rules.get('year_stem', payload.get('requested_year_stem') or '无')}",
                        *[
                            f"{label}：{star}"
                            for label, star in focused_sihua.items()
                        ],
                    ]
                ),
            )
        )
    return _render_snapshot_text(sections)


def calculate_ziwei_birth(
    person: PersonInfo,
    *,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_person_seed(person)
        ziwei_birth = build_ziwei_chart(seed, person.gender or "未知")
        ziwei_birth["engine"] = "fatebridge-offline"
        snapshot_text = _build_ziwei_snapshot_text(seed=seed, ziwei_birth=ziwei_birth)
        snapshot_export = _build_snapshot_export(
            technique="ziwei",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "紫微斗数命盘",
            "person_info": {
                "name": person.name or "未提供",
                "birth_datetime": format_birth_datetime_display(
                    seed.input_datetime, include_minutes=True
                ),
                "normalized_birth_datetime": format_birth_datetime_display(
                    seed.corrected_datetime, include_minutes=True
                ),
                "gender": person.gender or "未知",
                "birth_place": person.birth_place or "未提供",
                "birth_timezone": seed.timezone,
                "birth_longitude": seed.longitude,
                "time_algorithm": "真太阳时" if seed.applied_true_solar else "直接时间",
            },
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "ziwei_birth": ziwei_birth,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "紫微斗数命盘")


def calculate_ziwei_rules(
    year_stem: Optional[str] = None,
    *,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        if year_stem is not None and year_stem not in "甲乙丙丁戊己庚辛壬癸":
            raise ValueError("year_stem 必须是单个天干")
        payload = build_ziwei_rules(year_stem)
        payload["engine"] = "fatebridge-offline"
        snapshot_text = _build_ziwei_rules_snapshot_text(payload)
        snapshot_export = _build_snapshot_export(
            technique="ziwei_rules",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "紫微规则库",
            **payload,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "紫微规则库")


def calculate_liureng_gods(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    use_true_solar_time: bool = False,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        liureng = build_liureng_board(seed, gender=gender)
        liureng["engine"] = "fatebridge-offline"
        snapshot_text = _build_liureng_snapshot_text(seed=seed, liureng=liureng)
        snapshot_export = _build_snapshot_export(
            technique="liureng",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "大六壬起课",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "liureng": liureng,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "大六壬起课")


def calculate_liureng_runyear(
    person: PersonInfo,
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        # 大六壬行年以「分析时刻」起课，不依赖出生四柱；
        # 仅 person.gender / person.birth_year 在下方直接使用。
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        liureng = build_liureng_board(seed, gender=person.gender or "未知")
        liureng["engine"] = "fatebridge-offline"
        runyear = build_liureng_runyear(
            seed,
            gender=person.gender or "未知",
            birth_year=person.birth_year,
        )
        runyear["engine"] = "fatebridge-offline"
        snapshot_text = _build_liureng_snapshot_text(
            seed=seed,
            liureng=liureng,
            runyear=runyear,
        )
        snapshot_export = _build_snapshot_export(
            technique="liureng",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "大六壬行年",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "runyear": runyear,
            "liureng": liureng,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "大六壬行年")


def calculate_qimen_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    use_true_solar_time: bool = False,
    qimen_options: Optional[Dict[str, Any]] = None,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
            day_pillar_strategy=DAY_GANZHI_STRATEGY_STANDARD,
        )
        qimen = build_qimen_with_options(seed, qimen_options)
        qimen["engine"] = "fatebridge-offline"
        snapshot_text = build_qimen_snapshot_text(seed=seed, qimen=qimen)
        snapshot_export = _build_snapshot_export(
            technique="qimen",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "奇门遁甲",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "qimen": qimen,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "奇门遁甲")


def calculate_taiyi_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    use_true_solar_time: bool = False,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        taiyi = build_taiyi_board(seed, gender=gender)
        taiyi["engine"] = "fatebridge-offline"
        snapshot_text = _build_taiyi_snapshot_text(seed=seed, taiyi=taiyi)
        snapshot_export = _build_snapshot_export(
            technique="taiyi",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "太乙神数",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "taiyi": taiyi,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "太乙神数")


def calculate_jinkou_analysis(
    *,
    analysis_year: int,
    analysis_month: int,
    analysis_day: int,
    analysis_hour: int,
    analysis_minute: int = 0,
    analysis_timezone: Optional[str] = None,
    analysis_longitude: Optional[float] = None,
    gender: str = "未知",
    di_fen: Optional[str] = None,
    use_true_solar_time: bool = False,
    selected_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    try:
        seed = _build_analysis_seed(
            analysis_year=analysis_year,
            analysis_month=analysis_month,
            analysis_day=analysis_day,
            analysis_hour=analysis_hour,
            analysis_minute=analysis_minute,
            analysis_timezone=analysis_timezone,
            analysis_longitude=analysis_longitude,
            use_true_solar_time=use_true_solar_time,
        )
        local_liureng = build_liureng_board(seed, gender=gender)
        local_liureng["engine"] = "fatebridge-offline"
        liureng = local_liureng
        jinkou = build_jinkou_board(
            seed,
            local_liureng,
            gender=gender,
            di_fen=di_fen,
        )
        jinkou["engine"] = "fatebridge-offline"
        snapshot_text = _build_jinkou_snapshot_text(seed=seed, jinkou=jinkou)
        snapshot_export = _build_snapshot_export(
            technique="jinkou",
            snapshot_text=snapshot_text,
            selected_sections=selected_sections,
        )
        return {
            "analysis_type": "金口诀",
            "analysis_context": _analysis_context_payload(seed),
            "four_pillars": create_pillar_dict(seed.pillars),
            "calendar_context": seed.calendar_context,
            "liureng": liureng,
            "jinkou": jinkou,
            "snapshot_text": snapshot_text,
            "snapshot_export": snapshot_export,
        }
    except Exception as exc:
        return handle_calculation_error(exc, "金口诀")
