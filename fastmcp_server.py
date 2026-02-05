#!/usr/bin/env python3
"""
FateBridge FastMCP Server - 命运之桥：连接古典智慧与现代技术的命理工具

Provides core BaZi fortune-telling functionality via FastMCP protocol:
1. analyze_destiny - Individual destiny analysis
2. two_person_compatibility - Compatibility analysis between two people
3. timing_analysis - Comprehensive timing (luck period) analysis
"""

import logging
from typing import Optional

from fastmcp import FastMCP

from fatebridge.utils.helpers import (
    create_person_info,
    format_json_response,
    format_error_response,
)
from fatebridge.services.calculation import calculate_destiny_analysis
from fatebridge.services.compatibility import calculate_compatibility_analysis
from fatebridge.services.timing import (
    calculate_comprehensive_timing,
    calculate_dayun_analysis,
    calculate_liunian_analysis,
)

# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    """

    person = create_person_info(
        birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
    )

    data = calculate_destiny_analysis(person)
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

    data = calculate_compatibility_analysis(person1, person2, relationship_type)
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
    result = calculate_comprehensive_timing(
        person, analysis_year, analysis_month, analysis_age
    )

    if "error" in result:
        return format_error_response(result, "时运分析")

    return format_json_response(result)


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
    person = create_person_info(
        birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
    )

    result = calculate_dayun_analysis(person, analysis_age)
    
    if "error" in result and result.get("analysis_type") is None:
         # Only treat as error response if it's not a partial error inside the result
         return format_error_response(result, "大运分析")

    return format_json_response(result)


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
    person = create_person_info(
        birth_year, birth_month, birth_day, birth_hour, name, gender, birth_place
    )

    result = calculate_liunian_analysis(person, target_year)
    
    if "error" in result:
        return format_error_response(result, "流年分析")

    return format_json_response(result)


if __name__ == "__main__":
    app.run()
