#!/usr/bin/env python3
"""
FateBridge FastMCP Server - 命运之桥：连接古典智慧与现代技术的命理工具

Provides core BaZi fortune-telling functionality via FastMCP protocol:
1. analyze_destiny - Individual destiny analysis
2. two_person_compatibility - Compatibility analysis between two people
3. timing_analysis - Comprehensive timing (luck period) analysis
"""

import json
import logging
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from fastmcp import FastMCP

# 导入核心计算模块
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from fatebridge.core.rules import BaZiRules
from fatebridge.analysis.compatibility import AdvancedCompatibility, RelationshipType
from fatebridge.analysis.timing_effects import TimingEffectsAnalysis
from fatebridge.utils.helpers import (
    PersonInfo,
    create_person_info,
    create_birth_datetime,
    handle_calculation_error,
    create_pillar_dict,
    format_json_response,
    get_current_analysis_date,
)

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# 数据模型
# ============================================================================


class TwoPersonRequest(BaseModel):
    """双人配合度请求模型"""

    person1: PersonInfo = Field(description="第一人信息")
    person2: PersonInfo = Field(description="第二人信息")
    relationship_type: Optional[str] = Field(
        default="general",
        description="关系类型：marriage(婚姻), friendship(友谊), business(商业), family(家庭), general(一般)",
    )


class TimingAnalysisRequest(BaseModel):
    """时运分析请求模型"""

    person: PersonInfo = Field(description="个人信息")
    analysis_year: Optional[int] = Field(
        default=None, description="分析年份，默认为当前年份"
    )
    analysis_month: Optional[int] = Field(
        default=None, description="分析月份，默认为当前月份"
    )
    analysis_age: Optional[int] = Field(
        default=None, description="分析年龄，用于大运分析"
    )


# =============================================================================
# 核心分析逻辑
# =============================================================================


def calculate_single_analysis(person: PersonInfo) -> dict:
    """
    计算单人命理分析数据，包括四柱、五行、十神、格局等基础信息

    Args:
        person: 个人信息对象，包含出生年月日时等基本信息

    Returns:
        dict: 包含以下键值的字典：
            - person_info: 个人基本信息
            - four_pillars: 四柱信息（年月日时柱）
            - day_master: 日主信息（天干、五行、阴阳、强弱）
            - element_distribution: 五行分布百分比
            - favorable_elements: 喜用神
            - ten_gods: 十神分析
            - patterns: 格局分析（三合、六合、六冲、刑害等）

    Raises:
        Exception: 当计算过程中出现错误时返回包含错误信息的字典
    """
    try:
        # 转换为datetime
        birth_datetime = create_birth_datetime(
            person.birth_year, person.birth_month, person.birth_day, person.birth_hour
        )

        # 计算四柱
        pillars = BaZiCalendar.get_four_pillars(birth_datetime)

        # 五行分析
        element_analysis = ElementAnalysis.comprehensive_analysis(pillars)

        # 格局分析
        harmony_patterns = BaZiRules.check_harmony_patterns(pillars)
        clash_patterns = BaZiRules.check_clash_patterns(pillars)
        special_patterns = BaZiRules.analyze_special_patterns(
            pillars, person.birth_hour
        )

        return {
            "person_info": {
                "name": person.name or "未提供",
                "birth_datetime": birth_datetime.strftime("%Y年%m月%d日 %H时"),
                "gender": person.gender or "未知",
                "birth_place": person.birth_place or "未提供",
            },
            "four_pillars": create_pillar_dict(pillars),
            "day_master": {
                "stem": pillars["day"][0],
                "element": element_analysis["day_master"]["day_element"],
                "polarity": element_analysis["day_master"]["day_polarity"],
                "strength": element_analysis["day_master"]["strength_level"],
            },
            "element_distribution": element_analysis["day_master"][
                "element_distribution"
            ],
            "favorable_elements": element_analysis.get("favorable_elements", []),
            "ten_gods": element_analysis["ten_gods"],
            "patterns": {
                "harmony": harmony_patterns,
                "clash": clash_patterns,
                "special": special_patterns,
            },
        }
    except Exception as e:
        return handle_calculation_error(e, "命理分析计算")


def format_single_analysis(data: dict) -> str:
    """格式化单人命理分析数据"""
    error_response = format_error_response(data, "计算")
    if error_response:
        return error_response

    lines = []
    info = data["person_info"]

    # 基本信息
    lines.append("【基本信息】")
    lines.append(f"姓名: {info['name']}")
    lines.append(f"出生时间: {info['birth_datetime']}")
    lines.append(f"性别: {info['gender']}")
    if info["birth_place"] != "未提供":
        lines.append(f"出生地: {info['birth_place']}")
    lines.append("")

    # 四柱八字
    pillars = data["four_pillars"]
    lines.append("【四柱八字】")
    lines.append(f"年柱: {pillars['year']['stem']}{pillars['year']['branch']}")
    lines.append(f"月柱: {pillars['month']['stem']}{pillars['month']['branch']}")
    lines.append(f"日柱: {pillars['day']['stem']}{pillars['day']['branch']}")
    lines.append(f"时柱: {pillars['hour']['stem']}{pillars['hour']['branch']}")
    lines.append("")

    # 日主信息
    day_master = data["day_master"]
    lines.append("【日主信息】")
    lines.append(f"日主: {day_master['stem']} ({day_master['element']})")
    lines.append(f"阴阳: {day_master['polarity']}")
    lines.append(f"强弱: {day_master['strength']}")
    lines.append("")

    # 五行分布
    lines.append("【五行分布】")
    for element, percentage in data["element_distribution"].items():
        if percentage > 0:
            lines.append(f"{element}: {percentage}%")
    lines.append("")

    # 喜用神
    if data.get("favorable_elements"):
        lines.append("【喜用神】")
        lines.append(", ".join(data["favorable_elements"]))
        lines.append("")

    # 十神分析
    ten_gods = data["ten_gods"]
    lines.append("【十神分析】")
    pillar_names = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
    for pillar, gods in ten_gods.items():
        if gods:
            lines.append(f"{pillar_names.get(pillar, pillar)}:")
            for god in gods:
                lines.append(f"  {god['character']} - {god['ten_god']}")
    lines.append("")

    # 格局分析
    patterns = data["patterns"]
    if any([patterns["harmony"], patterns["clash"], patterns["special"]]):
        lines.append("【格局分析】")

        # 三合六合
        harmony = patterns["harmony"]
        if harmony.get("triple_harmony"):
            for pattern in harmony["triple_harmony"]:
                status = "成局" if pattern["complete"] else "半合"
                lines.append(
                    f"三合: {pattern['type']} - {', '.join(pattern['branches'])} ({status})"
                )
        if harmony.get("six_harmony"):
            for pair in harmony["six_harmony"]:
                lines.append(f"六合: {', '.join(pair)}")

        # 六冲
        clash = patterns["clash"]
        if clash.get("six_clash"):
            for pair in clash["six_clash"]:
                lines.append(f"六冲: {', '.join(pair)}")

        # 特殊格局
        special = patterns["special"]
        if special.get("noble_day"):
            noble_day_text = "特殊格局: 日贵格"
            if special.get("noble_day_type"):
                noble_day_text += f" ({special['noble_day_type']})"
            lines.append(noble_day_text)
        if special.get("kui_gang"):
            lines.append("特殊格局: 魁罡格")

    return "\n".join(lines)


def calculate_compatibility(
    person1: PersonInfo, person2: PersonInfo, relationship_type: str = "general"
) -> dict:
    """
    计算双人配合度，分析两人的命理相互关系和配合程度

    Args:
        person1: 第一人的个人信息对象
        person2: 第二人的个人信息对象
        relationship_type: 关系类型，可选值：
            - "marriage": 婚姻关系
            - "friendship": 友谊关系
            - "business": 商业合作
            - "family": 家庭关系
            - "general": 一般关系（默认）

    Returns:
        dict: 包含以下键值的字典：
            - person1_info: 第一人基本信息和分析
            - person2_info: 第二人基本信息和分析
            - compatibility_analysis: 配合度分析结果
                - overall_score: 总体配合度评分
                - element_compatibility: 五行配合度
                - pillar_interactions: 四柱相互作用
                - relationship_specific: 特定关系类型的分析

    Raises:
         Exception: 当计算过程中出现错误时返回包含错误信息的字典
    """
    try:
        # 分别计算两人命理分析
        analysis1 = calculate_single_analysis(person1)
        analysis2 = calculate_single_analysis(person2)

        if "error" in analysis1 or "error" in analysis2:
            return {"error": "计算个人分析时出现错误"}

        # 转换关系类型
        rel_type_map = {
            "marriage": RelationshipType.MARRIAGE,
            "friendship": RelationshipType.FRIENDSHIP,
            "business": RelationshipType.BUSINESS,
            "family": RelationshipType.FAMILY,
            "general": RelationshipType.GENERAL,
        }
        rel_type = rel_type_map.get(relationship_type, RelationshipType.GENERAL)

        # 使用高级合盘分析
        advanced_analysis = AdvancedCompatibility.analyze_comprehensive_compatibility(
            analysis1, analysis2, rel_type
        )

        # 保持向后兼容，同时提供传统分析
        pillars1 = {
            k: (v["stem"], v["branch"]) for k, v in analysis1["four_pillars"].items()
        }
        pillars2 = {
            k: (v["stem"], v["branch"]) for k, v in analysis2["four_pillars"].items()
        }
        traditional_compatibility = BaZiRules.calculate_compatibility_score(
            pillars1, pillars2
        )

        # 五行关系分析
        element1 = analysis1["day_master"]["element"]
        element2 = analysis2["day_master"]["element"]
        element_relationship = get_element_relationship(element1, element2)

        # 喜用神对比 - 安全处理，避免unhashable type错误
        favorable1 = analysis1.get("favorable_elements", [])
        favorable2 = analysis2.get("favorable_elements", [])

        # 确保favorable_elements是字符串列表
        if isinstance(favorable1, list) and all(isinstance(x, str) for x in favorable1):
            favorable1_set = set(favorable1)
        else:
            favorable1_set = set()

        if isinstance(favorable2, list) and all(isinstance(x, str) for x in favorable2):
            favorable2_set = set(favorable2)
        else:
            favorable2_set = set()

        # 优化的JSON输出格式
        return {
            "summary": {
                "overall_score": advanced_analysis["overall_score"],
                "compatibility_level": advanced_analysis["summary"],
                "relationship_type": relationship_type,
            },
            "detailed_analysis": {
                "element_balance": {
                    "score": advanced_analysis["detailed_analysis"]["element_balance"][
                        "score"
                    ],
                    "details": advanced_analysis["detailed_analysis"][
                        "element_balance"
                    ]["details"],
                },
                "favorable_synergy": {
                    "score": advanced_analysis["detailed_analysis"][
                        "favorable_synergy"
                    ]["score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "favorable_synergy"
                    ]["details"],
                },
                "ten_gods_relationship": {
                    "score": advanced_analysis["detailed_analysis"][
                        "ten_gods_relationship"
                    ]["score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "ten_gods_relationship"
                    ]["details"],
                },
                "pattern_synergy": {
                    "score": advanced_analysis["detailed_analysis"]["pattern_synergy"][
                        "score"
                    ],
                    "details": advanced_analysis["detailed_analysis"][
                        "pattern_synergy"
                    ]["details"],
                },
                "traditional_analysis": {
                    "score": advanced_analysis["detailed_analysis"][
                        "traditional_analysis"
                    ]["normalized_score"],
                    "details": advanced_analysis["detailed_analysis"][
                        "traditional_analysis"
                    ]["details"],
                },
            },
            "strengths": advanced_analysis["strengths"],
            "challenges": advanced_analysis["challenges"],
            "recommendations": advanced_analysis["recommendations"],
            "person_info": {
                "person1": {
                    "name": analysis1["person_info"]["name"],
                    "birth_datetime": analysis1["person_info"]["birth_datetime"],
                    "day_master": f"{analysis1['day_master']['stem']}({analysis1['day_master']['element']})",
                    "strength": analysis1["day_master"]["strength"],
                    "favorable_elements": analysis1.get("favorable_elements", []),
                },
                "person2": {
                    "name": analysis2["person_info"]["name"],
                    "birth_datetime": analysis2["person_info"]["birth_datetime"],
                    "day_master": f"{analysis2['day_master']['stem']}({analysis2['day_master']['element']})",
                    "strength": analysis2["day_master"]["strength"],
                    "favorable_elements": analysis2.get("favorable_elements", []),
                },
            },
            "element_relationship": {
                "person1_element": element1,
                "person2_element": element2,
                "relationship_type": element_relationship["type"],
                "description": element_relationship["description"],
            },
            "traditional_compatibility": {
                "score": traditional_compatibility["overall_score"],
                "level": traditional_compatibility["level"],
                "details": traditional_compatibility.get("details", []),
            },
        }
    except Exception as e:
        return handle_calculation_error(e, "配合度分析")


def format_error_response(data: dict, operation: str) -> str:
    """格式化错误响应

    Args:
        data: 包含错误信息的字典
        operation: 操作名称

    Returns:
        格式化的错误信息字符串
    """
    if "error" in data:
        return format_json_response({
            "error": data["error"],
            "operation": operation
        })
    return ""


def get_element_relationship(element1: str, element2: str) -> dict:
    """分析两个五行元素的关系

    Args:
        element1: 第一个元素名称
        element2: 第二个元素名称

    Returns:
        关系分析字典

    Raises:
        ValueError: 如果元素无效
    """
    from fatebridge.utils.data import Element, GENERATION_CYCLE, DESTRUCTION_CYCLE

    # 找到对应的Element枚举
    element1_enum = None
    element2_enum = None

    for element_enum in Element:
        if element_enum.value == element1:
            element1_enum = element_enum
        if element_enum.value == element2:
            element2_enum = element_enum

    # FIXED: Check for None values before using
    if element1_enum is None or element2_enum is None:
        logger.warning(f"Invalid element reference: {element1} or {element2}")
        return {
            "type": "错误",
            "description": f"无效的五行元素: {element1 if element1_enum is None else element2}",
        }

    if element1_enum == element2_enum:
        return {"type": "相同", "description": "同类元素，容易理解对方"}
    elif (
        element1_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相生",
            "description": f"{element1}生{element2}，{element1}方能助{element2}方",
        }
    elif (
        element2_enum in GENERATION_CYCLE
        and GENERATION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相生",
            "description": f"{element2}生{element1}，{element2}方能助{element1}方",
        }
    elif (
        element1_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element1_enum] == element2_enum
    ):
        return {
            "type": "相克",
            "description": f"{element1}克{element2}，{element1}方较为强势",
        }
    elif (
        element2_enum in DESTRUCTION_CYCLE
        and DESTRUCTION_CYCLE[element2_enum] == element1_enum
    ):
        return {
            "type": "相克",
            "description": f"{element2}克{element1}，{element2}方较为强势",
        }
    else:
        return {"type": "无直接关系", "description": "元素间无直接生克关系"}


def format_compatibility(data: dict) -> str:
    """格式化合盘数据"""
    error_response = format_error_response(data, "合盘计算")
    if error_response:
        return error_response

    lines = []
    # 修复数据结构访问路径
    person1_info = data["person_info"]["person1"]
    person2_info = data["person_info"]["person2"]

    # 基本信息
    lines.append("【合盘基本信息】")
    lines.append(f"第一人: {person1_info['name']} ({person1_info.get('birth_datetime', '未提供')})")
    lines.append(f"第二人: {person2_info['name']} ({person2_info.get('birth_datetime', '未提供')})")
    lines.append("")

    return "\n".join(lines)


def calculate_timing_analysis(
    person: PersonInfo,
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_age: Optional[int] = None,
) -> dict:
    """
    计算时运分析，包括大运、流年、流月的影响分析

    Args:
        person: 个人信息对象，包含出生年月日时等基本信息
        analysis_year: 分析年份，默认为当前年份
        analysis_month: 分析月份，默认为当前月份
        analysis_age: 分析年龄，用于大运分析，默认根据当前年份计算

    Returns:
        dict: 包含以下键值的字典：
            - person_info: 个人基本信息
            - base_analysis: 基础命理信息
            - timing_analysis: 时运分析结果
                - dayun: 大运分析（10年一运）
                - liunian: 流年分析（年运）
                - liuyue: 流月分析（月运）
                - timing_effects: 时运对命局的影响
                - favorable_periods: 有利时期分析

    Raises:
        Exception: 当计算过程中出现错误时返回包含错误信息的字典
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

        return {
            "person_info": {
                "name": person.name,
                "birth_datetime": birth_date.strftime("%Y-%m-%d %H:%M"),
                "gender": person.gender,
                "birth_place": person.birth_place,
            },
            "analysis_info": {
                "analysis_date": analysis_date.strftime("%Y-%m-%d"),
                "current_age": current_age,
            },
            "birth_pillars": create_pillar_dict(birth_pillars),
            "timing_analysis": timing_result,
        }

    except Exception as e:
        return handle_calculation_error(e, "时运分析计算")


def format_timing_analysis(data: dict) -> str:
    """格式化时运分析数据为JSON格式"""
    if "error" in data:
        return format_json_response({"error": data["error"]})

    info = data["person_info"]
    analysis_info = data["analysis_info"]
    timing = data["timing_analysis"]
    pillars = data["birth_pillars"]

    # 构建JSON格式的输出
    result = {
        "analysis_type": "综合时运分析",
        "personal_info": {
            "name": info["name"],
            "birth_datetime": info["birth_datetime"],
            "gender": info["gender"],
            "analysis_date": analysis_info["analysis_date"],
            "current_age": analysis_info["current_age"],
        },
        "birth_pillars": {
            "year": {
                "stem": pillars["year"]["stem"],
                "branch": pillars["year"]["branch"],
            },
            "month": {
                "stem": pillars["month"]["stem"],
                "branch": pillars["month"]["branch"],
            },
            "day": {"stem": pillars["day"]["stem"], "branch": pillars["day"]["branch"]},
            "hour": {
                "stem": pillars["hour"]["stem"],
                "branch": pillars["hour"]["branch"],
            },
        },
    }

    # 大运分析
    dayun_analysis = timing["dayun_analysis"]
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
    liunian_analysis = timing["liunian_analysis"]
    liunian_info = liunian_analysis["liunian_info"]
    result["liunian_analysis"] = {
        "pillar": liunian_info["pillar"],
        "stem": liunian_info["stem"],
        "branch": liunian_info["branch"],
        "summary": liunian_analysis["summary"],
    }

    # 流月分析
    liuyue_analysis = timing["liuyue_analysis"]
    liuyue_info = liuyue_analysis["liuyue_info"]
    result["liuyue_analysis"] = {
        "pillar": liuyue_info["pillar"],
        "stem": liuyue_info["stem"],
        "branch": liuyue_info["branch"],
        "summary": liuyue_analysis["summary"],
    }

    # 综合影响
    combined_effects = timing["combined_effects"]
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
    result["comprehensive_summary"] = timing["comprehensive_summary"]

    return format_json_response(result)


# =============================================================================
# FastMCP 应用配置
# =============================================================================

app = FastMCP(
    name="fatebridge",
    instructions="中国传统八字测算工具，提供单人分析、双人配合度计算和时运分析（大运、流年、流月）。只输出计算数据，不包含建议。",
    version="2.1.0",
)


@app.tool
def analyze_destiny(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
) -> str:
    """
    个人命理分析工具

    根据出生年月日时计算个人命理分析，提供完整的分析，包括：
    - 四柱信息（年月日时柱的天干地支）
    - 日主分析（日干的五行属性、阴阳、强弱程度）
    - 五行分布（各五行在命局中的百分比）
    - 十神分析（根据日干与其他干支的关系确定十神）
    - 格局分析（三合、六合、六冲、刑害等特殊组合）
    - 喜用神（对命局有利的五行）

    Args:
        birth_year: 出生年份（公历），如1990
        birth_month: 出生月份，1-12
        birth_day: 出生日期，1-31
        birth_hour: 出生时辰，0-23（24小时制）
        name: 姓名（可选），默认为"未提供"
        gender: 性别（可选），默认为"未知"
        birth_place: 出生地（可选），默认为"未提供"

    Returns:
        JSON格式的字符串，包含完整的命理分析结果

    Example:
        analyze_destiny(1990, 5, 15, 14, "张三", "男", "北京")
    """

    person = create_person_info(
        birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
    )

    data = calculate_single_analysis(person)
    return format_json_response(data)


@app.tool
def two_person_compatibility(
    person1_name: str,
    person1_birth_year: int,
    person1_birth_month: int,
    person1_birth_day: int,
    person1_birth_hour: int,
    person2_name: str,
    person2_birth_year: int,
    person2_birth_month: int,
    person2_birth_day: int,
    person2_birth_hour: int,
    person1_gender: str = "未知",
    person1_birth_place: str = "未提供",
    person2_gender: str = "未知",
    person2_birth_place: str = "未提供",
    relationship_type: str = "general",
) -> str:
    """
    双人配合度分析工具

    分析两人命理的相互关系和配合程度，提供多维度的配合度评估：
    - 总体配合度评分（0-100分）
    - 五行配合度（两人五行的互补性和协调性）
    - 十神关系分析（两人十神配置的相互影响）
    - 格局协同分析（两人命局格局的配合程度）
    - 关系特化分析（针对特定关系类型的专门分析）

    Args:
        person1_name: 第一人姓名
        person1_birth_year: 第一人出生年份（公历）
        person1_birth_month: 第一人出生月份，1-12
        person1_birth_day: 第一人出生日期，1-31
        person1_birth_hour: 第一人出生时辰，0-23
        person2_name: 第二人姓名
        person2_birth_year: 第二人出生年份（公历）
        person2_birth_month: 第二人出生月份，1-12
        person2_birth_day: 第二人出生日期，1-31
        person2_birth_hour: 第二人出生时辰，0-23
        person1_gender: 第一人性别，默认为"未知"
        person1_birth_place: 第一人出生地，默认为"未提供"
        person2_gender: 第二人性别，默认为"未知"
        person2_birth_place: 第二人出生地，默认为"未提供"
        relationship_type: 关系类型，可选值：
            - "marriage": 婚姻关系
            - "friendship": 友谊关系
            - "business": 商业合作
            - "family": 家庭关系
            - "general": 一般关系（默认）

    Returns:
        JSON格式的字符串，包含详细的配合度分析结果

    Example:
        two_person_compatibility("张三", 1990, 5, 15, 14, "李四", 1992, 8, 20, 10,
                               "男", "北京", "女", "上海", "marriage")
    """
    # 创建PersonInfo对象
    person1 = create_person_info(
        person1_birth_year,
        person1_birth_month,
        person1_birth_day,
        person1_birth_hour,
        person1_name,
        person1_gender,
        person1_birth_place,
    )

    person2 = create_person_info(
        person2_birth_year,
        person2_birth_month,
        person2_birth_day,
        person2_birth_hour,
        person2_name,
        person2_gender,
        person2_birth_place,
    )

    data = calculate_compatibility(person1, person2, relationship_type)
    return format_json_response(data)


@app.tool
def timing_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
    analysis_year: Optional[int] = None,
    analysis_month: Optional[int] = None,
    analysis_age: Optional[int] = None,
) -> str:
    """
    时运分析工具 - 分析大运、流年、流月对命局的影响

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        name: 姓名（可选）
        gender: 性别（可选）
        birth_place: 出生地（可选）
        analysis_year: 分析年份（可选，默认当前年份）
        analysis_month: 分析月份（可选，默认当前月份）
        analysis_age: 分析年龄（可选，用于大运分析）

    Returns:
        格式化的时运分析结果
    """

    # 创建PersonInfo对象
    person = create_person_info(
        birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
    )

    # 计算时运分析
    result = calculate_timing_analysis(
        person, analysis_year, analysis_month, analysis_age
    )

    return format_timing_analysis(result)


@app.tool
def dayun_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    gender: str,
    analysis_age: int,
    name: Optional[str] = "未提供",
    birth_place: Optional[str] = "未提供",
) -> str:
    """
    大运分析工具 - 专门分析指定年龄的大运情况

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        gender: 性别（男/女）
        analysis_age: 分析年龄
        name: 姓名（可选）
        birth_place: 出生地（可选）

    Returns:
        格式化的大运分析结果
    """
    try:
        # 创建出生日期
        birth_date = datetime(birth_year, birth_month, birth_day, birth_hour)

        # 计算四柱
        person = create_person_info(
            birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
        )

        # 直接获取原始四柱数据（元组格式）
        birth_pillars = BaZiCalendar.get_four_pillars(birth_date)

        # 进行大运分析
        dayun_result = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_pillars, birth_date, gender, analysis_age
        )

        # 构建JSON格式的输出
        result = {
            "analysis_type": "大运专项分析",
            "personal_info": {
                "name": name,
                "gender": gender,
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

        return format_json_response(result)

    except Exception as e:
        error_data = handle_calculation_error(e, "大运分析计算")
        return format_error_response(error_data, "大运分析")


@app.tool
def liunian_analysis(
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    target_year: int,
    name: Optional[str] = "未提供",
    gender: Optional[str] = "未知",
    birth_place: Optional[str] = "未提供",
) -> str:
    """
    流年分析工具 - 专门分析指定年份的流年影响

    Args:
        birth_year: 出生年份
        birth_month: 出生月份 (1-12)
        birth_day: 出生日期 (1-31)
        birth_hour: 出生时辰 (0-23)
        target_year: 目标分析年份
        name: 姓名（可选）
        gender: 性别（可选）
        birth_place: 出生地（可选）

    Returns:
        格式化的流年分析结果
    """
    try:
        # 计算四柱
        person = create_person_info(
            birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
        )

        # 创建出生日期并直接获取原始四柱数据（元组格式）
        birth_date = datetime(birth_year, birth_month, birth_day, birth_hour)
        birth_pillars = BaZiCalendar.get_four_pillars(birth_date)

        # 进行流年分析
        liunian_result = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_pillars, target_year
        )

        # 构建JSON格式的输出
        liunian_info = liunian_result["liunian_info"]
        element_effects = liunian_result["element_effects"]

        result = {
            "analysis_type": "流年专项分析",
            "personal_info": {"name": name, "target_year": target_year},
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

        result["summary"] = liunian_result["summary"]

        return format_json_response(result)

    except Exception as e:
        error_data = handle_calculation_error(e, "流年分析计算")
        return format_error_response(error_data, "流年分析")


if __name__ == "__main__":
    app.run()
