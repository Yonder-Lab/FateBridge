"""
FateBridge Timing Services
"""
from typing import Optional, Dict
from datetime import datetime
import logging

from fatebridge.core.almanac import build_calendar_context, get_jieqi_year_grid
from fatebridge.utils.helpers import (
    PersonInfo,
    handle_calculation_error,
    create_pillar_dict,
    get_current_analysis_date,
    format_json_response,
    normalize_birth_time,
)
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.timing import TimingAnalysis
from fatebridge.analysis.timing_effects import TimingEffectsAnalysis

logger = logging.getLogger(__name__)

def calculate_comprehensive_timing(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_age: Optional[int] = None,
) -> Dict:
    """
    计算时运分析，包括大运、流年、流月的影响分析
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        input_birth_datetime = normalized_birth_time.input_datetime
        birth_date = normalized_birth_time.corrected_datetime

        # 计算四柱（使用原始格式）
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        # 设置分析日期
        analysis_year, analysis_month = get_current_analysis_date(
            analysis_year, analysis_month
        )

        analysis_date = datetime(analysis_year, analysis_month, 1)
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )
        analysis_year_jieqi = get_jieqi_year_grid(
            analysis_year, normalized_birth_time.timezone
        )
        liuyue_timeline = TimingAnalysis.calculate_liuyue_timeline(
            analysis_year, timezone_name=normalized_birth_time.timezone
        )
        for item in liuyue_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_effect = TimingEffectsAnalysis.analyze_liuyue_effects(
                birth_pillars,
                anchor.year,
                anchor.month,
                target_day=anchor.day,
                timezone_name=normalized_birth_time.timezone,
                target_date=anchor,
            )
            item["overall_effect"] = liuyue_effect["element_effects"]["overall_effect"]
            item["summary"] = liuyue_effect["enhanced_summary"]
        jieqi_timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
            analysis_year, timezone_name=normalized_birth_time.timezone
        )
        for item in jieqi_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_pillar = item["liuyue"]
            liuri_pillar = item["liuri"]
            node_effect = TimingEffectsAnalysis.analyze_element_strength_changes(
                birth_pillars,
                {
                    "liuyue": {
                        "stem": liuyue_pillar["stem"],
                        "branch": liuyue_pillar["branch"],
                    },
                    "liuri": {
                        "stem": liuri_pillar["stem"],
                        "branch": liuri_pillar["branch"],
                    },
                },
            )
            liuri_effect = TimingEffectsAnalysis.analyze_liuri_effects(
                birth_pillars,
                anchor,
                timezone_name=normalized_birth_time.timezone,
            )
            item["overall_effect"] = node_effect["overall_effect"]
            item["liuri_summary"] = liuri_effect["enhanced_summary"]
            item["summary"] = (
                f"{item['jieqi']['name']}节点，流月{liuyue_pillar['pillar']}，"
                f"流日{liuri_pillar['pillar']}，{node_effect['overall_effect']}"
            )

        # 计算当前年龄
        if analysis_age is None:
            current_age = analysis_date.year - birth_date.year
            if analysis_date.month < birth_date.month or (
                analysis_date.month == birth_date.month
                and analysis_date.day < birth_date.day
            ):
                current_age -= 1
        else:
            current_age = analysis_age

        # 进行综合时运分析
        timing_result = TimingEffectsAnalysis.comprehensive_timing_analysis(
            birth_pillars,
            birth_date,
            person.gender,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        # 构建最终结果结构
        result = {
            "analysis_type": "综合时运分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": input_birth_datetime.strftime("%Y-%m-%d %H:%M"),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "gender": person.gender,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "current_age": current_age,
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "birth_pillars": create_pillar_dict(birth_pillars),
            "calendar_context": birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
                "analysis_year_jieqi": analysis_year_jieqi,
                "liuyue_timeline": liuyue_timeline,
                "jieqi_timeline": jieqi_timeline,
            },
        }
        
        # 大运分析
        dayun_analysis = timing_result["dayun_analysis"]
        if "dayun_info" in dayun_analysis:
            dayun_info = dayun_analysis["dayun_info"]
            age_info = dayun_analysis["age_info"]
            result["dayun_analysis"] = {
                "current_dayun": dayun_info["pillar"],
                "stem": dayun_info["stem"],
                "branch": dayun_info["branch"],
                "start_age": age_info["start_age"],
                "dayun_age": age_info["dayun_age"],
                "years_in_period": age_info["years_in_period"],
                "summary": dayun_analysis["summary"],
            }
        else:
            result["dayun_analysis"] = {
                "error": dayun_analysis.get("message", "大运信息不可用")
            }

        # 流年分析
        liunian_analysis = timing_result["liunian_analysis"]
        liunian_info = liunian_analysis["liunian_info"]
        result["liunian_analysis"] = {
            "pillar": liunian_info["pillar"],
            "stem": liunian_info["stem"],
            "branch": liunian_info["branch"],
            "summary": liunian_analysis["summary"],
        }

        # 流月分析
        liuyue_analysis = timing_result["liuyue_analysis"]
        liuyue_info = liuyue_analysis["liuyue_info"]
        result["liuyue_analysis"] = {
            "pillar": liuyue_info["pillar"],
            "stem": liuyue_info["stem"],
            "branch": liuyue_info["branch"],
            "summary": liuyue_analysis["summary"],
        }

        # 流日分析
        liuri_analysis = timing_result["liuri_analysis"]
        liuri_info = liuri_analysis["liuri_info"]
        result["liuri_analysis"] = {
            "pillar": liuri_info["pillar"],
            "stem": liuri_info["stem"],
            "branch": liuri_info["branch"],
            "summary": liuri_analysis["summary"],
        }

        # 综合影响
        combined_effects = timing_result["combined_effects"]
        result["combined_effects"] = {
            "overall_effect": combined_effects["overall_effect"],
            "element_changes": {},
        }

        # 只包含有变化的五行
        element_changes = combined_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["combined_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
                }

        # 综合总结
        result["comprehensive_summary"] = timing_result["comprehensive_summary"]

        return result

    except Exception as e:
        return handle_calculation_error(e, "时运分析计算")

def calculate_dayun_analysis(
    person: PersonInfo,
    analysis_age: int,
) -> Dict:
    """
    大运分析工具 - 专门分析指定年龄的大运情况
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_pillars,
            birth_date,
            person.gender,
            analysis_age,
            timezone_name=normalized_birth_time.timezone,
        )

        result = {
            "analysis_type": "大运专项分析",
            "personal_info": {
                "name": person.name,
                "gender": person.gender,
                "analysis_age": analysis_age,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
        }

        if "dayun_info" in dayun_result:
            dayun_info = dayun_result["dayun_info"]
            age_info = dayun_result["age_info"]
            element_effects = dayun_result["element_effects"]

            result["dayun_info"] = {
                "current_dayun": dayun_info["pillar"],
                "stem": dayun_info["stem"],
                "branch": dayun_info["branch"],
                "start_age": age_info["start_age"],
                "dayun_age": age_info["dayun_age"],
                "years_in_period": age_info["years_in_period"],
            }

            result["element_effects"] = {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            }

            # 只包含有变化的五行
            element_changes = element_effects["element_changes"]
            for element, change_info in element_changes.items():
                if change_info["change"] != 0:
                    result["element_effects"]["element_changes"][element] = {
                        "original": change_info["original"],
                        "new": change_info["new"],
                        "change": change_info["change"],
                        "change_type": change_info["change_type"],
                    }

            result["summary"] = dayun_result["summary"]
        else:
            result["error"] = dayun_result.get("message", "大运信息不可用")

        return result

    except Exception as e:
        return handle_calculation_error(e, "大运分析计算")

def calculate_liunian_analysis(
    person: PersonInfo,
    target_year: int,
) -> Dict:
    """
    流年分析工具 - 专门分析指定年份的流年影响
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        liunian_result = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_pillars, target_year
        )

        liunian_info = liunian_result["liunian_info"]
        element_effects = liunian_result["element_effects"]

        result = {
            "analysis_type": "流年专项分析",
            "personal_info": {
                "name": person.name,
                "target_year": target_year,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
            "target_year_jieqi": get_jieqi_year_grid(
                target_year, normalized_birth_time.timezone
            ),
            "liunian_info": {
                "pillar": liunian_info["pillar"],
                "stem": liunian_info["stem"],
                "branch": liunian_info["branch"],
                "element": liunian_info["element"],
            },
            "element_effects": {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            },
        }

        element_changes = element_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["element_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
                }

        result["summary"] = liunian_result["summary"]
        return result

    except Exception as e:
        return handle_calculation_error(e, "流年分析计算")


def calculate_liuri_analysis(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_day: Optional[int] = None,
) -> Dict:
    """
    流日分析工具 - 专门分析指定日期的流日影响
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        now = datetime.now()
        if analysis_year is None:
            analysis_year = now.year
        if analysis_month is None:
            analysis_month = now.month
        if analysis_day is None:
            analysis_day = now.day

        analysis_date = datetime(analysis_year, analysis_month, analysis_day)
        analysis_calendar_context = build_calendar_context(
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuri_result = TimingEffectsAnalysis.analyze_liuri_effects(
            birth_pillars,
            analysis_date,
            timezone_name=normalized_birth_time.timezone,
        )

        liuri_info = liuri_result["liuri_info"]
        element_effects = liuri_result["element_effects"]

        result = {
            "analysis_type": "流日专项分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
            "analysis_calendar": {
                "analysis_date_context": analysis_calendar_context,
            },
            "liuri_info": {
                "pillar": liuri_info["pillar"],
                "stem": liuri_info["stem"],
                "branch": liuri_info["branch"],
                "element": liuri_info["element"],
                "weekday": liuri_info["weekday"],
            },
            "element_effects": {
                "overall_effect": element_effects["overall_effect"],
                "element_changes": {},
            },
            "summary": liuri_result["enhanced_summary"],
        }

        element_changes = element_effects["element_changes"]
        for element, change_info in element_changes.items():
            if change_info["change"] != 0:
                result["element_effects"]["element_changes"][element] = {
                    "original": change_info["original"],
                    "new": change_info["new"],
                    "change": change_info["change"],
                    "change_type": change_info["change_type"],
                }

        return result

    except Exception as e:
        return handle_calculation_error(e, "流日分析计算")


def calculate_jieqi_timeline_analysis(
    person: PersonInfo,
    target_year: Optional[int] = None,
) -> Dict:
    """
    节气节点时间轴分析 - 输出全年 24 节气节点的流月/流日切换信息
    """
    try:
        normalized_birth_time = normalize_birth_time(person)
        birth_date = normalized_birth_time.corrected_datetime
        birth_pillars = BaZiCalendar.get_four_pillars(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
        )
        birth_calendar_context = build_calendar_context(
            birth_date,
            timezone_name=normalized_birth_time.timezone,
            pillars=birth_pillars,
        )

        if target_year is None:
            target_year = datetime.now().year

        jieqi_timeline = TimingAnalysis.calculate_jieqi_transition_timeline(
            target_year,
            timezone_name=normalized_birth_time.timezone,
        )

        for item in jieqi_timeline:
            anchor = datetime.strptime(item["analysis_anchor"], "%Y-%m-%d %H:%M:%S")
            liuyue_pillar = item["liuyue"]
            liuri_pillar = item["liuri"]
            node_effect = TimingEffectsAnalysis.analyze_element_strength_changes(
                birth_pillars,
                {
                    "liuyue": {
                        "stem": liuyue_pillar["stem"],
                        "branch": liuyue_pillar["branch"],
                    },
                    "liuri": {
                        "stem": liuri_pillar["stem"],
                        "branch": liuri_pillar["branch"],
                    },
                },
            )
            liuri_effect = TimingEffectsAnalysis.analyze_liuri_effects(
                birth_pillars,
                anchor,
                timezone_name=normalized_birth_time.timezone,
            )
            item["overall_effect"] = node_effect["overall_effect"]
            item["liuri_summary"] = liuri_effect["enhanced_summary"]
            item["summary"] = (
                f"{item['jieqi']['name']}节点，流月{liuyue_pillar['pillar']}，"
                f"流日{liuri_pillar['pillar']}，{node_effect['overall_effect']}"
            )

        return {
            "analysis_type": "节气节点时间轴分析",
            "personal_info": {
                "name": person.name,
                "target_year": target_year,
                "birth_datetime": normalized_birth_time.input_datetime.strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "normalized_birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "time_adjustment": normalized_birth_time.as_dict(),
            },
            "calendar_context": birth_calendar_context,
            "target_year_jieqi": get_jieqi_year_grid(
                target_year, normalized_birth_time.timezone
            ),
            "jieqi_timeline": jieqi_timeline,
        }

    except Exception as e:
        return handle_calculation_error(e, "节气时间轴分析计算")
