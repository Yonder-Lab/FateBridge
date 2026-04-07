"""
Calendar conversion utilities for BaZi calculations.
Converts Gregorian dates to Chinese sexagenary cycle (干支).
"""

from datetime import datetime, date
from typing import Tuple, Dict

from .almanac import (
    DEFAULT_TIMEZONE,
    get_bazi_month_context,
    get_bazi_year,
    localize_datetime,
)
from ..utils.data import (
    HEAVENLY_STEMS,
    EARTHLY_BRANCHES,
    MONTH_BRANCHES,
    get_hour_branch,
)


class BaZiCalendar:
    """
    八字历法转换工具类，负责将公历日期转换为中国传统干支历法

    该类提供了完整的四柱（年月日时）计算功能，包括：
    - 年柱计算：基于六十甲子循环
    - 月柱计算：根据年干和月份确定月干支
    - 日柱计算：基于基准日期的偏移量计算
    - 时柱计算：根据日干和时辰确定时干支

    基准参考点：
    - 基准年份：1984年（甲子年）
    - 基准日期：1984-03-31（甲子日）

    Attributes:
        BASE_YEAR (int): 基准年份，用于年柱计算
    """

    # Base reference point: 甲子年甲子月甲子日甲子时
    # Using 1984-02-02 as base year (甲子年)
    BASE_YEAR = 1984

    @staticmethod
    def get_stem_branch_index(base_index: int, offset: int, cycle_length: int) -> int:
        """Calculate index in stem-branch cycle."""
        return (base_index + offset) % cycle_length

    @classmethod
    def calculate_year_pillar(cls, year: int) -> Tuple[str, str]:
        """Calculate the year pillar (年柱) for a given year."""
        # Calculate offset from base year
        year_offset = year - cls.BASE_YEAR

        # Calculate indices
        stem_index = cls.get_stem_branch_index(0, year_offset, 10)  # 甲 is index 0
        branch_index = cls.get_stem_branch_index(0, year_offset, 12)  # 子 is index 0

        return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

    @classmethod
    def calculate_month_pillar(cls, year: int, month: int) -> Tuple[str, str]:
        """Calculate the month pillar (月柱) for a given year and month."""
        # Get the earthly branch for the month
        month_branch = MONTH_BRANCHES[month]

        return cls.calculate_month_pillar_by_branch(year, month_branch)

    @classmethod
    def calculate_month_pillar_by_branch(
        cls, year: int, month_branch: str
    ) -> Tuple[str, str]:
        """Calculate the month pillar using a resolved BaZi month branch."""
        month_index = [
            "寅",
            "卯",
            "辰",
            "巳",
            "午",
            "未",
            "申",
            "酉",
            "戌",
            "亥",
            "子",
            "丑",
        ].index(month_branch)

        # Calculate heavenly stem based on year stem
        year_stem, _ = cls.calculate_year_pillar(year)
        year_stem_index = HEAVENLY_STEMS.index(year_stem)

        # Month stem calculation based on year stem
        # 甲己年丙作首，乙庚年戊为头，丙辛年庚上起，丁壬年壬位流，戊癸年甲好求
        month_stem_base_mapping = {
            0: 2,  # 甲年 -> 丙寅月开始 (丙 is index 2)
            5: 2,  # 己年 -> 丙寅月开始
            1: 4,  # 乙年 -> 戊寅月开始 (戊 is index 4)
            6: 4,  # 庚年 -> 戊寅月开始
            2: 6,  # 丙年 -> 庚寅月开始 (庚 is index 6)
            7: 6,  # 辛年 -> 庚寅月开始
            3: 8,  # 丁年 -> 壬寅月开始 (壬 is index 8)
            8: 8,  # 壬年 -> 壬寅月开始
            4: 0,  # 戊年 -> 甲寅月开始 (甲 is index 0)
            9: 0,  # 癸年 -> 甲寅月开始
        }

        base_stem_index = month_stem_base_mapping[year_stem_index]

        month_stem_index = (base_stem_index + month_index) % 10
        month_stem = HEAVENLY_STEMS[month_stem_index]

        return month_stem, month_branch

    @classmethod
    def calculate_day_pillar(cls, year: int, month: int, day: int) -> Tuple[str, str]:
        """Calculate the day pillar (日柱) for a given date."""
        # 使用已知准确的基准：1984年3月31日是甲子日
        base_date = date(1984, 3, 31)  # 甲子日
        target_date = date(year, month, day)

        days_diff = (target_date - base_date).days

        # 从甲子日开始计算
        # 甲在天干中索引为0，子在地支中索引为0
        base_stem_index = 0  # 甲
        base_branch_index = 0  # 子

        # 计算目标日期的干支索引
        stem_index = (base_stem_index + days_diff) % 10
        branch_index = (base_branch_index + days_diff) % 12

        return HEAVENLY_STEMS[stem_index], EARTHLY_BRANCHES[branch_index]

    @classmethod
    def calculate_hour_pillar(
        cls, year: int, month: int, day: int, hour: int
    ) -> Tuple[str, str]:
        """Calculate the hour pillar (时柱) for a given datetime."""
        # Get the earthly branch for the hour
        hour_branch = get_hour_branch(hour)

        # Calculate heavenly stem based on day stem
        day_stem, _ = cls.calculate_day_pillar(year, month, day)
        day_stem_index = HEAVENLY_STEMS.index(day_stem)

        # Hour stem calculation based on day stem
        # 甲己还加甲，乙庚丙作初，丙辛从戊起，丁壬庚子居，戊癸何方发，壬子是真途
        hour_stem_base_mapping = {
            0: 0,  # 甲日 -> 甲子时开始
            5: 0,  # 己日 -> 甲子时开始
            1: 2,  # 乙日 -> 丙子时开始
            6: 2,  # 庚日 -> 丙子时开始
            2: 4,  # 丙日 -> 戊子时开始
            7: 4,  # 辛日 -> 戊子时开始
            3: 6,  # 丁日 -> 庚子时开始
            8: 6,  # 壬日 -> 庚子时开始
            4: 8,  # 戊日 -> 壬子时开始
            9: 8,  # 癸日 -> 壬子时开始
        }

        base_stem_index = hour_stem_base_mapping[day_stem_index]

        # Get hour branch index to calculate offset
        hour_branch_index = EARTHLY_BRANCHES.index(hour_branch)

        # Calculate hour stem
        hour_stem_index = (base_stem_index + hour_branch_index) % 10
        hour_stem = HEAVENLY_STEMS[hour_stem_index]

        return hour_stem, hour_branch

    @classmethod
    def get_four_pillars(
        cls,
        birth_datetime: datetime,
        timezone_name: str = DEFAULT_TIMEZONE,
    ) -> Dict[str, Tuple[str, str]]:
        """
        Calculate all four pillars (四柱) for a given birth datetime.

        Returns:
            Dict with keys: 'year', 'month', 'day', 'hour'
            Each value is a tuple of (heavenly_stem, earthly_branch)
        """
        local_birth_datetime = localize_datetime(birth_datetime, timezone_name)
        year = local_birth_datetime.year
        month = local_birth_datetime.month
        day = local_birth_datetime.day
        hour = local_birth_datetime.hour

        bazi_year = get_bazi_year(local_birth_datetime, timezone_name)
        month_context = get_bazi_month_context(local_birth_datetime, timezone_name)
        month_branch = month_context["branch"]

        return {
            "year": cls.calculate_year_pillar(bazi_year),
            "month": cls.calculate_month_pillar_by_branch(bazi_year, month_branch),
            "day": cls.calculate_day_pillar(year, month, day),
            "hour": cls.calculate_hour_pillar(year, month, day, hour),
        }

    @classmethod
    def format_pillars(cls, pillars: Dict[str, Tuple[str, str]]) -> str:
        """Format the four pillars as a readable string."""
        pillar_names = ["年柱", "月柱", "日柱", "时柱"]
        pillar_keys = ["year", "month", "day", "hour"]

        formatted_pillars = []
        for name, key in zip(pillar_names, pillar_keys):
            stem, branch = pillars[key]
            formatted_pillars.append(f"{name}: {stem}{branch}")

        return "  ".join(formatted_pillars)
