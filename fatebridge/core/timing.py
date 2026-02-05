#!/usr/bin/env python3
"""
时运分析模块 - 大运、流年、流月计算

本模块提供八字时运分析的核心功能：
1. 大运计算 - 10年一个周期的运势变化
2. 流年计算 - 每年的运势影响
3. 流月计算 - 每月的运势变化
"""

from datetime import datetime
from typing import Dict, List, Optional
from ..utils.data import (
    HEAVENLY_STEMS,
    EARTHLY_BRANCHES,
    STEM_ELEMENTS,
    get_nayin,
    get_shishen,
    check_branch_conflict,
    check_branch_combination,
)


class TimingAnalysis:
    """
    时运分析工具类，负责计算和分析八字中的时间运势变化

    该类提供了完整的时运分析功能，包括：
    - 大运计算：10年一个周期的长期运势变化
    - 流年计算：每年的运势影响和变化
    - 流月计算：每月的短期运势波动
    - 起运年龄：根据出生时间和性别计算开始行运的年龄
    - 运势组合：分析大运、流年、流月与原局的相互作用

    计算原理：
    - 大运：根据月柱和性别确定顺逆行方向
    - 流年：基于年份的天干地支循环
    - 流月：基于月份的天干地支组合
    - 起运：考虑性别、年干阴阳和节气因素

    注意事项：
    - 男命阳年、女命阴年为顺行大运
    - 男命阴年、女命阳年为逆行大运
    - 起运年龄通常在1-10岁之间
    """

    @staticmethod
    def calculate_dayun_start_age(
        birth_date: datetime, month_pillar_stem: str, gender: str
    ) -> int:
        """
        计算起运年龄

        Args:
            birth_date: 出生日期
            month_pillar_stem: 月柱天干
            gender: 性别 ("男" 或 "女")

        Returns:
            起运年龄
        """
        birth_year = birth_date.year
        birth_month = birth_date.month
        birth_day = birth_date.day

        # 判断阳年还是阴年
        year_stem_index = (birth_year - 4) % 10
        is_yang_year = year_stem_index % 2 == 0

        # 判断男女和阴阳年的组合
        if (gender == "男" and is_yang_year) or (gender == "女" and not is_yang_year):
            # 顺行大运
            forward_direction = True
        else:
            # 逆行大运
            forward_direction = False

        # 计算到下一个节气的天数
        # 简化计算：假设每月15日为节气
        if forward_direction:
            # 顺行：计算到下个月节气的天数
            if birth_day <= 15:
                days_to_next_jieqi = 15 - birth_day
            else:
                # 到下个月15日
                if birth_month == 12:
                    next_month_date = datetime(birth_year + 1, 1, 15)
                else:
                    next_month_date = datetime(birth_year, birth_month + 1, 15)
                days_to_next_jieqi = (next_month_date - birth_date).days
        else:
            # 逆行：计算到上个节气的天数
            if birth_day >= 15:
                days_to_next_jieqi = birth_day - 15
            else:
                # 到上个月15日
                if birth_month == 1:
                    prev_month_date = datetime(birth_year - 1, 12, 15)
                else:
                    prev_month_date = datetime(birth_year, birth_month - 1, 15)
                days_to_next_jieqi = (birth_date - prev_month_date).days

        # 3天为1年，计算起运年龄
        start_age = days_to_next_jieqi // 3
        if days_to_next_jieqi % 3 > 0:
            start_age += 1

        return max(1, start_age)  # 最小1岁起运

    @staticmethod
    def calculate_dayun_sequence(
        month_pillar_stem: str,
        month_pillar_branch: str,
        gender: str,
        birth_year: int,
        periods: int = 8,
    ) -> List[Dict]:
        """
        计算大运序列

        Args:
            month_pillar_stem: 月柱天干
            month_pillar_branch: 月柱地支
            gender: 性别
            birth_year: 出生年份
            periods: 计算的大运期数，默认8期（80年）

        Returns:
            大运序列列表
        """
        # 判断大运方向
        year_stem_index = (birth_year - 4) % 10
        is_yang_year = year_stem_index % 2 == 0

        if (gender == "男" and is_yang_year) or (gender == "女" and not is_yang_year):
            direction = 1  # 顺行
        else:
            direction = -1  # 逆行

        # 获取月柱干支的索引
        month_stem_index = HEAVENLY_STEMS.index(month_pillar_stem)
        month_branch_index = EARTHLY_BRANCHES.index(month_pillar_branch)

        dayun_sequence = []

        for period_index in range(periods):
            # 计算当前大运的干支索引
            current_stem_index = (
                month_stem_index + direction * (period_index + 1)
            ) % 10
            current_branch_index = (
                month_branch_index + direction * (period_index + 1)
            ) % 12

            dayun_stem = HEAVENLY_STEMS[current_stem_index]
            dayun_branch = EARTHLY_BRANCHES[current_branch_index]

            dayun_info = {
                "period": period_index + 1,
                "stem": dayun_stem,
                "branch": dayun_branch,
                "pillar": f"{dayun_stem}{dayun_branch}",
                "age_range": {
                    "start": period_index * 10 + 1,
                    "end": (period_index + 1) * 10,
                },
            }

            dayun_sequence.append(dayun_info)

        return dayun_sequence

    @staticmethod
    def calculate_liunian(target_year: int) -> Dict:
        """
        计算指定年份的流年干支

        Args:
            target_year: 目标年份

        Returns:
            流年信息
        """
        # 计算年干支（以甲子年为基准：1984年）
        base_year = 1984  # 甲子年
        year_offset = target_year - base_year

        stem_index = year_offset % 10
        branch_index = year_offset % 12

        liunian_stem = HEAVENLY_STEMS[stem_index]
        liunian_branch = EARTHLY_BRANCHES[branch_index]

        # 获取天干五行
        stem_element, stem_polarity = STEM_ELEMENTS[liunian_stem]

        return {
            "year": target_year,
            "stem": liunian_stem,
            "branch": liunian_branch,
            "pillar": f"{liunian_stem}{liunian_branch}",
            "element": stem_element.value,
        }

    @staticmethod
    def calculate_liuyue(target_year: int, target_month: int) -> Dict:
        """
        计算指定年月的流月干支

        Args:
            target_year: 目标年份
            target_month: 目标月份 (1-12)

        Returns:
            流月信息
        """
        # 获取年干
        liunian_info = TimingAnalysis.calculate_liunian(target_year)
        year_stem_index = HEAVENLY_STEMS.index(liunian_info["stem"])

        # 月干计算公式：年干索引 * 2 + 月份索引
        # 正月建寅，从寅月开始
        month_branch_index = (target_month + 1) % 12  # 寅月为起始

        # 月干的计算
        if year_stem_index in [0, 5]:  # 甲己年
            month_stem_base = 2  # 丙
        elif year_stem_index in [1, 6]:  # 乙庚年
            month_stem_base = 4  # 戊
        elif year_stem_index in [2, 7]:  # 丙辛年
            month_stem_base = 6  # 庚
        elif year_stem_index in [3, 8]:  # 丁壬年
            month_stem_base = 8  # 壬
        else:  # 戊癸年
            month_stem_base = 0  # 甲

        month_stem_index = (month_stem_base + target_month - 1) % 10

        liuyue_stem = HEAVENLY_STEMS[month_stem_index]
        liuyue_branch = EARTHLY_BRANCHES[month_branch_index]

        # 获取天干五行
        stem_element, stem_polarity = STEM_ELEMENTS[liuyue_stem]

        # 获取纳音
        nayin = get_nayin(liuyue_stem, liuyue_branch)

        return {
            "year": target_year,
            "month": target_month,
            "stem": liuyue_stem,
            "branch": liuyue_branch,
            "pillar": f"{liuyue_stem}{liuyue_branch}",
            "element": stem_element.value,
            "polarity": stem_polarity.value,
            "nayin": nayin,
        }

    @staticmethod
    def analyze_liuyue_detailed(
        birth_pillars: Dict,
        target_year: int,
        target_month: int,
        day_stem: Optional[str] = None,
    ) -> Dict:
        """
        流月的详细分析，包括十神关系、吉凶判断等

        Args:
            birth_pillars: 出生四柱
            target_year: 目标年份
            target_month: 目标月份
            day_stem: 日主天干，如果未提供则从birth_pillars中获取

        Returns:
            流月详细分析结果
        """
        # 获取基础流月信息
        liuyue_info = TimingAnalysis.calculate_liuyue(target_year, target_month)

        # 获取日主
        if day_stem is None:
            day_stem = birth_pillars["day"][0]

        # 分析流月天干与日主的十神关系
        stem_shishen = get_shishen(day_stem, liuyue_info["stem"])

        # 分析流月与命局的冲合关系
        branch_relations = []
        for pillar_name, pillar_data in birth_pillars.items():
            pillar_branch = pillar_data[1]  # 地支

            # 检查六冲
            if check_branch_conflict(liuyue_info["branch"], pillar_branch):
                branch_relations.append(
                    {
                        "type": "六冲",
                        "with_pillar": pillar_name,
                        "with_branch": pillar_branch,
                        "description": f"流月{liuyue_info['branch']}与{pillar_name}柱{pillar_branch}相冲",
                    }
                )

            # 检查六合
            if check_branch_combination(liuyue_info["branch"], pillar_branch):
                branch_relations.append(
                    {
                        "type": "六合",
                        "with_pillar": pillar_name,
                        "with_branch": pillar_branch,
                        "description": f"流月{liuyue_info['branch']}与{pillar_name}柱{pillar_branch}六合",
                    }
                )

        # 分析吉凶趋势
        fortune_analysis = TimingAnalysis._analyze_liuyue_fortune(
            stem_shishen, branch_relations, liuyue_info
        )

        # 生成运势建议
        suggestions = TimingAnalysis._generate_liuyue_suggestions(
            stem_shishen, branch_relations, fortune_analysis
        )

        return {
            "basic_info": liuyue_info,
            "shishen_analysis": {
                "stem_relation": stem_shishen,
                "description": f"流月天干{liuyue_info['stem']}对日主{day_stem}为{stem_shishen}",
            },
            "branch_relations": branch_relations,
            "fortune_analysis": fortune_analysis,
            "suggestions": suggestions,
            "overall_summary": TimingAnalysis._generate_liuyue_summary(
                liuyue_info, stem_shishen, branch_relations, fortune_analysis
            ),
        }

    @staticmethod
    def _analyze_liuyue_fortune(
        stem_shishen: str, branch_relations: List[Dict], liuyue_info: Dict
    ) -> Dict:
        """
        分析流月的吉凶趋势

        Args:
            stem_shishen: 天干十神关系
            branch_relations: 地支关系列表
            liuyue_info: 流月基础信息

        Returns:
            吉凶分析结果
        """
        fortune_score = 0
        fortune_factors = []

        # 基于十神关系评分
        shishen_scores = {
            "比肩": 0,
            "劫财": -1,
            "食神": 2,
            "伤官": -1,
            "正财": 1,
            "偏财": 1,
            "正官": 1,
            "七杀": -2,
            "正印": 2,
            "偏印": -1,
        }

        stem_score = shishen_scores.get(stem_shishen, 0)
        fortune_score += stem_score
        fortune_factors.append(
            f"十神{stem_shishen}: {'+' if stem_score >= 0 else ''}{stem_score}分"
        )

        # 基于地支关系评分
        for relation in branch_relations:
            if relation["type"] == "六冲":
                fortune_score -= 2
                fortune_factors.append(f"{relation['description']}: -2分")
            elif relation["type"] == "六合":
                fortune_score += 2
                fortune_factors.append(f"{relation['description']}: +2分")

        # 基于纳音属性评分（简化处理）
        nayin = liuyue_info["nayin"]
        if "金" in nayin:
            nayin_desc = "金类纳音，主收敛、坚毅"
        elif "木" in nayin:
            nayin_desc = "木类纳音，主生发、创新"
        elif "水" in nayin:
            nayin_desc = "水类纳音，主智慧、灵活"
        elif "火" in nayin:
            nayin_desc = "火类纳音，主热情、积极"
        elif "土" in nayin:
            nayin_desc = "土类纳音，主稳重、务实"
        else:
            nayin_desc = "纳音属性平和"

        # 判断总体吉凶
        if fortune_score >= 3:
            overall_fortune = "大吉"
        elif fortune_score >= 1:
            overall_fortune = "小吉"
        elif fortune_score >= -1:
            overall_fortune = "平"
        elif fortune_score >= -3:
            overall_fortune = "小凶"
        else:
            overall_fortune = "大凶"

        return {
            "fortune_score": fortune_score,
            "fortune_factors": fortune_factors,
            "overall_fortune": overall_fortune,
            "nayin_description": nayin_desc,
            "detailed_analysis": f"本月运势{overall_fortune}，总分{fortune_score}分",
        }

    @staticmethod
    def _generate_liuyue_suggestions(
        stem_shishen: str, branch_relations: List[Dict], fortune_analysis: Dict
    ) -> List[str]:
        """
        生成流月运势建议

        Args:
            stem_shishen: 天干十神关系
            branch_relations: 地支关系
            fortune_analysis: 吉凶分析

        Returns:
            建议列表
        """
        suggestions = []

        # 基于十神关系的建议
        shishen_suggestions = {
            "比肩": "适合团队合作，与同行交流",
            "劫财": "注意财务管理，避免冲动消费",
            "食神": "发挥创造力，展现才华的好时机",
            "伤官": "注意言行，避免与人发生冲突",
            "正财": "财运不错，适合投资理财",
            "偏财": "偏财运佳，但需谨慎决策",
            "正官": "工作运势良好，适合求职晋升",
            "七杀": "面临压力挑战，需谨慎应对",
            "正印": "学习运佳，适合进修充电",
            "偏印": "思维活跃但易多变，需专注",
        }

        if stem_shishen in shishen_suggestions:
            suggestions.append(shishen_suggestions[stem_shishen])

        # 基于地支关系的建议
        has_conflict = any(r["type"] == "六冲" for r in branch_relations)
        has_combination = any(r["type"] == "六合" for r in branch_relations)

        if has_conflict:
            suggestions.append("本月有冲克之象，宜静不宜动，避免重大决策")
        if has_combination:
            suggestions.append("本月有合化之象，人际关系和谐，适合合作")

        # 基于总体运势的建议
        overall_fortune = fortune_analysis["overall_fortune"]
        if overall_fortune in ["大吉", "小吉"]:
            suggestions.append("运势良好，可积极进取，把握机会")
        elif overall_fortune == "平":
            suggestions.append("运势平稳，保持现状，稳中求进")
        else:
            suggestions.append("运势欠佳，宜保守行事，等待时机")

        return suggestions

    @staticmethod
    def _generate_liuyue_summary(
        liuyue_info: Dict,
        stem_shishen: str,
        branch_relations: List[Dict],
        fortune_analysis: Dict,
    ) -> str:
        """
        生成流月分析总结

        Args:
            liuyue_info: 流月基础信息
            stem_shishen: 十神关系
            branch_relations: 地支关系
            fortune_analysis: 吉凶分析

        Returns:
            分析总结
        """
        year_month = f"{liuyue_info['year']}年{liuyue_info['month']}月"
        pillar = liuyue_info["pillar"]
        nayin = liuyue_info["nayin"]
        overall_fortune = fortune_analysis["overall_fortune"]

        summary_parts = [
            f"{year_month}流月{pillar}({nayin})",
            f"十神{stem_shishen}",
            f"总体运势{overall_fortune}",
        ]

        if branch_relations:
            relation_desc = "、".join([r["type"] for r in branch_relations])
            summary_parts.append(f"有{relation_desc}关系")

        return "，".join(summary_parts) + "。"

    @staticmethod
    def get_current_dayun(
        birth_date: datetime,
        month_pillar_stem: str,
        month_pillar_branch: str,
        gender: str,
        current_date: Optional[datetime] = None,
    ) -> Dict:
        """
        获取当前大运信息

        Args:
            birth_date: 出生日期
            month_pillar_stem: 月柱天干
            month_pillar_branch: 月柱地支
            gender: 性别
            current_date: 当前日期，默认为今天

        Returns:
            当前大运信息
        """
        if current_date is None:
            current_date = datetime.now()

        # 计算起运年龄
        start_age = TimingAnalysis.calculate_dayun_start_age(
            birth_date, month_pillar_stem, gender
        )

        # 计算当前年龄
        current_age = current_date.year - birth_date.year
        if current_date.month < birth_date.month or (
            current_date.month == birth_date.month and current_date.day < birth_date.day
        ):
            current_age -= 1

        # 计算当前大运期数
        if current_age < start_age:
            return {
                "status": "before_dayun",
                "message": f"尚未起运，将在{start_age}岁起运",
                "start_age": start_age,
            }

        dayun_age = current_age - start_age + 1
        current_period = (dayun_age - 1) // 10 + 1

        # 获取大运序列
        dayun_sequence = TimingAnalysis.calculate_dayun_sequence(
            month_pillar_stem, month_pillar_branch, gender, birth_date.year
        )

        if current_period <= len(dayun_sequence):
            current_dayun = dayun_sequence[current_period - 1]
            current_dayun["current_age"] = current_age
            current_dayun["dayun_age"] = dayun_age
            current_dayun["years_in_period"] = (dayun_age - 1) % 10 + 1
            return current_dayun
        else:
            return {
                "status": "beyond_calculation",
                "message": "超出计算范围",
                "current_age": current_age,
            }

    @staticmethod
    def analyze_timing_combination(
        birth_pillars: Dict, current_date: Optional[datetime] = None
    ) -> Dict:
        """
        分析时运组合（大运、流年、流月的综合影响）

        Args:
            birth_pillars: 出生四柱信息
            current_date: 分析日期，默认为当前日期

        Returns:
            时运分析结果
        """
        if current_date is None:
            current_date = datetime.now()

        # 这里需要从birth_pillars中提取必要信息
        # 假设birth_pillars包含必要的信息
        month_stem = birth_pillars["month"]["stem"]
        month_branch = birth_pillars["month"]["branch"]

        # 获取当前流年
        current_liunian = TimingAnalysis.calculate_liunian(current_date.year)

        # 获取当前流月
        current_liuyue = TimingAnalysis.calculate_liuyue(
            current_date.year, current_date.month
        )

        return {
            "analysis_date": current_date.strftime("%Y-%m-%d"),
            "liunian": current_liunian,
            "liuyue": current_liuyue,
            "summary": {
                "year_pillar": current_liunian["pillar"],
                "month_pillar": current_liuyue["pillar"],
                "analysis": "时运分析需要结合具体命局进行详细解读",
            },
        }
