"""
FateBridge Timing Services
"""
from typing import Optional, Dict
from datetime import datetime
import logging

from fatebridge.utils.helpers import (
    PersonInfo,
    handle_calculation_error,
    create_pillar_dict,
    get_current_analysis_date,
    format_json_response,
)
from fatebridge.core.calendar import BaZiCalendar
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
        # 创建出生日期
        birth_date = datetime(
            person.birth_year, person.birth_month, person.birth_day, person.birth_hour
        )

        # 计算四柱（使用原始格式）
        birth_pillars = BaZiCalendar.get_four_pillars(birth_date)

        # 设置分析日期
        analysis_year, analysis_month = get_current_analysis_date(
            analysis_year, analysis_month
        )

        analysis_date = datetime(analysis_year, analysis_month, 1)

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
            birth_pillars, birth_date, person.gender, analysis_date
        )

        # 构建最终结果结构
        result = {
            "analysis_type": "综合时运分析",
            "personal_info": {
                "name": person.name,
                "birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "gender": person.gender,
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "current_age": current_age,
            },
            "birth_pillars": create_pillar_dict(birth_pillars),
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
        birth_date = datetime(
            person.birth_year, person.birth_month, person.birth_day, person.birth_hour
        )
        birth_pillars = BaZiCalendar.get_four_pillars(birth_date)

        dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_pillars, birth_date, person.gender, analysis_age
        )

        result = {
            "analysis_type": "大运专项分析",
            "personal_info": {
                "name": person.name,
                "gender": person.gender,
                "analysis_age": analysis_age,
            },
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
        birth_date = datetime(
            person.birth_year, person.birth_month, person.birth_day, person.birth_hour
        )
        birth_pillars = BaZiCalendar.get_four_pillars(birth_date)

        liunian_result = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_pillars, target_year
        )

        liunian_info = liunian_result["liunian_info"]
        element_effects = liunian_result["element_effects"]

        result = {
            "analysis_type": "流年专项分析",
            "personal_info": {"name": person.name, "target_year": target_year},
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
