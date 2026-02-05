#!/usr/bin/env python3
"""
时运影响分析模块

本模块分析大运、流年、流月对原命局的具体影响：
1. 五行力量变化分析
2. 十神关系变化
3. 格局影响分析
4. 吉凶趋势判断
"""

from typing import Dict, Optional
from datetime import datetime
from ..core.timing import TimingAnalysis
from ..core.elements import ElementAnalysis


class TimingEffectsAnalysis:
    """时运影响分析类"""

    @staticmethod
    def analyze_element_strength_changes(
        original_pillars: Dict, timing_pillars: Dict
    ) -> Dict:
        """
        分析时运对五行力量的影响

        Args:
            original_pillars: 原命局四柱
            timing_pillars: 时运干支（大运、流年、流月）

        Returns:
            五行力量变化分析
        """
        # 获取原命局五行分布
        original_analysis = ElementAnalysis.comprehensive_analysis(original_pillars)
        original_distribution = original_analysis["day_master"]["element_distribution"]

        # 计算加入时运后的五行分布
        all_stems = []
        all_branches = []

        # 添加原命局干支
        for pillar_name, pillar_info in original_pillars.items():
            all_stems.append(pillar_info[0])  # 天干
            all_branches.append(pillar_info[1])  # 地支

        # 添加时运干支
        for timing_name, timing_info in timing_pillars.items():
            if "stem" in timing_info and "branch" in timing_info:
                all_stems.append(timing_info["stem"])
                all_branches.append(timing_info["branch"])

        # 重新计算五行分布
        combined_pillars = {}
        pillar_names = ["year", "month", "day", "hour"]
        for i, (stem, branch) in enumerate(zip(all_stems[:4], all_branches[:4])):
            combined_pillars[pillar_names[i]] = (stem, branch)

        # 添加时运作为额外柱
        timing_index = 5
        for timing_name, timing_info in timing_pillars.items():
            if "stem" in timing_info and "branch" in timing_info:
                combined_pillars[f"timing_{timing_index}"] = (
                    timing_info["stem"],
                    timing_info["branch"],
                )
                timing_index += 1

        new_analysis = ElementAnalysis.comprehensive_analysis(combined_pillars)
        new_distribution = new_analysis["day_master"]["element_distribution"]

        # 计算变化
        element_changes = {}
        for element in ["木", "火", "土", "金", "水"]:
            original_count = original_distribution.get(element, 0)
            new_count = new_distribution.get(element, 0)
            change = new_count - original_count

            element_changes[element] = {
                "original": original_count,
                "new": new_count,
                "change": change,
                "change_type": (
                    "增强" if change > 0 else "减弱" if change < 0 else "无变化"
                ),
            }

        return {
            "original_distribution": original_distribution,
            "new_distribution": new_distribution,
            "element_changes": element_changes,
            "overall_effect": TimingEffectsAnalysis._evaluate_overall_effect(
                element_changes
            ),
        }

    @staticmethod
    def _evaluate_overall_effect(element_changes: Dict) -> str:
        """评估整体影响效果"""
        positive_changes = sum(
            1 for change in element_changes.values() if change["change"] > 0
        )
        negative_changes = sum(
            1 for change in element_changes.values() if change["change"] < 0
        )

        if positive_changes > negative_changes:
            return "整体五行力量增强"
        elif negative_changes > positive_changes:
            return "整体五行力量减弱"
        else:
            return "五行力量基本平衡"

    @staticmethod
    def analyze_dayun_effects(
        birth_pillars: Dict, birth_date: datetime, gender: str, analysis_age: int
    ) -> Dict:
        """
        分析指定年龄的大运影响

        Args:
            birth_pillars: 出生四柱
            birth_date: 出生日期
            gender: 性别
            analysis_age: 分析年龄

        Returns:
            大运影响分析
        """
        month_stem = birth_pillars["month"][0]
        month_branch = birth_pillars["month"][1]

        # 计算起运年龄
        start_age = TimingAnalysis.calculate_dayun_start_age(
            birth_date, month_stem, gender
        )

        if analysis_age < start_age:
            return {
                "status": "before_dayun",
                "message": f"尚未起运，将在{start_age}岁起运",
            }

        # 获取大运序列
        dayun_sequence = TimingAnalysis.calculate_dayun_sequence(
            month_stem, month_branch, gender, birth_date.year
        )

        # 确定当前大运期
        dayun_age = analysis_age - start_age + 1
        current_period = (dayun_age - 1) // 10 + 1

        if current_period > len(dayun_sequence):
            return {"status": "beyond_calculation", "message": "超出计算范围"}

        current_dayun = dayun_sequence[current_period - 1]

        # 分析大运对命局的影响
        timing_pillars = {
            "dayun": {"stem": current_dayun["stem"], "branch": current_dayun["branch"]}
        }

        element_effects = TimingEffectsAnalysis.analyze_element_strength_changes(
            birth_pillars, timing_pillars
        )

        return {
            "dayun_info": current_dayun,
            "age_info": {
                "analysis_age": analysis_age,
                "start_age": start_age,
                "dayun_age": dayun_age,
                "years_in_period": (dayun_age - 1) % 10 + 1,
            },
            "element_effects": element_effects,
            "summary": TimingEffectsAnalysis._generate_dayun_summary(
                current_dayun, element_effects
            ),
        }

    @staticmethod
    def _generate_dayun_summary(dayun_info: Dict, element_effects: Dict) -> str:
        """生成大运影响总结"""
        dayun_pillar = dayun_info["pillar"]
        overall_effect = element_effects["overall_effect"]

        return f"大运{dayun_pillar}期间，{overall_effect}，需要注意五行平衡的调节。"

    @staticmethod
    def analyze_liunian_effects(birth_pillars: Dict, target_year: int) -> Dict:
        """
        分析流年影响

        Args:
            birth_pillars: 出生四柱
            target_year: 目标年份

        Returns:
            流年影响分析
        """
        # 获取流年信息
        liunian_info = TimingAnalysis.calculate_liunian(target_year)

        # 分析流年对命局的影响
        timing_pillars = {
            "liunian": {"stem": liunian_info["stem"], "branch": liunian_info["branch"]}
        }

        element_effects = TimingEffectsAnalysis.analyze_element_strength_changes(
            birth_pillars, timing_pillars
        )

        return {
            "liunian_info": liunian_info,
            "element_effects": element_effects,
            "summary": f"流年{liunian_info['pillar']}，{element_effects['overall_effect']}",
        }

    @staticmethod
    def analyze_liuyue_effects(
        birth_pillars: Dict, target_year: int, target_month: int
    ) -> Dict:
        """
        分析流月影响

        Args:
            birth_pillars: 出生四柱
            target_year: 目标年份
            target_month: 目标月份

        Returns:
            流月影响分析
        """
        # 获取流月信息
        liuyue_info = TimingAnalysis.calculate_liuyue(target_year, target_month)

        # 使用新的详细分析功能
        detailed_analysis = TimingAnalysis.analyze_liuyue_detailed(
            birth_pillars, target_year, target_month
        )

        # 分析流月对命局的影响
        timing_pillars = {
            "liuyue": {"stem": liuyue_info["stem"], "branch": liuyue_info["branch"]}
        }

        element_effects = TimingEffectsAnalysis.analyze_element_strength_changes(
            birth_pillars, timing_pillars
        )

        return {
            "liuyue_info": liuyue_info,
            "detailed_analysis": detailed_analysis,
            "element_effects": element_effects,
            "summary": f"流月{liuyue_info['pillar']}，{element_effects['overall_effect']}",
            "enhanced_summary": detailed_analysis["overall_summary"],
        }

    @staticmethod
    def analyze_liuyue_comprehensive(
        birth_pillars: Dict,
        target_year: int,
        target_month: int,
        include_dayun: bool = True,
        include_liunian: bool = True,
    ) -> Dict:
        """
        流月的综合分析，包括与大运、流年的组合影响

        Args:
            birth_pillars: 出生四柱
            target_year: 目标年份
            target_month: 目标月份
            include_dayun: 是否包含大运分析
            include_liunian: 是否包含流年分析

        Returns:
            流月综合影响分析
        """
        # 基础流月分析
        liuyue_analysis = TimingEffectsAnalysis.analyze_liuyue_effects(
            birth_pillars, target_year, target_month
        )

        result = {"liuyue_analysis": liuyue_analysis, "combination_effects": {}}

        # 添加流年分析
        if include_liunian:
            liunian_analysis = TimingEffectsAnalysis.analyze_liunian_effects(
                birth_pillars, target_year
            )
            result["liunian_analysis"] = liunian_analysis

            # 分析流月与流年的组合效应
            liuyue_branch = liuyue_analysis["liuyue_info"]["branch"]
            liunian_branch = liunian_analysis["liunian_info"]["branch"]

            combination_analysis = TimingEffectsAnalysis._analyze_branch_combination(
                liuyue_branch, liunian_branch, "流月", "流年"
            )
            result["combination_effects"]["liuyue_liunian"] = combination_analysis

        # 添加大运分析（需要额外的出生信息）
        if include_dayun:
            # 这里需要更多的出生信息来计算大运，暂时省略
            result["combination_effects"][
                "note"
            ] = "大运分析需要完整的出生信息（性别、出生日期等）"

        # 生成综合总结
        result["comprehensive_summary"] = (
            TimingEffectsAnalysis._generate_comprehensive_liuyue_summary(result)
        )

        return result

    @staticmethod
    def _analyze_branch_combination(
        branch1: str, branch2: str, type1: str, type2: str
    ) -> Dict:
        """
        分析两个地支的组合关系

        Args:
            branch1: 第一个地支
            branch2: 第二个地支
            type1: 第一个地支的类型描述
            type2: 第二个地支的类型描述

        Returns:
            组合关系分析
        """
        from ..utils.data import check_branch_conflict, check_branch_combination

        relations = []

        if check_branch_conflict(branch1, branch2):
            relations.append(
                {
                    "type": "六冲",
                    "description": f"{type1}{branch1}与{type2}{branch2}相冲",
                    "effect": "冲突较大，需要化解",
                    "impact_score": -3,
                }
            )

        if check_branch_combination(branch1, branch2):
            relations.append(
                {
                    "type": "六合",
                    "description": f"{type1}{branch1}与{type2}{branch2}六合",
                    "effect": "关系和谐，相互助益",
                    "impact_score": 3,
                }
            )

        if not relations:
            relations.append(
                {
                    "type": "普通",
                    "description": f"{type1}{branch1}与{type2}{branch2}关系普通",
                    "effect": "影响中性",
                    "impact_score": 0,
                }
            )

        # 计算总体影响分数
        total_score = sum(r["impact_score"] for r in relations)

        return {
            "branch1": branch1,
            "branch2": branch2,
            "relations": relations,
            "total_impact_score": total_score,
            "overall_effect": TimingEffectsAnalysis._score_to_effect(total_score),
        }

    @staticmethod
    def _score_to_effect(score: int) -> str:
        """将分数转换为效果描述"""
        if score >= 3:
            return "非常有利"
        elif score > 0:
            return "有利"
        elif score == 0:
            return "中性"
        elif score > -3:
            return "不利"
        else:
            return "非常不利"

    @staticmethod
    def _generate_comprehensive_liuyue_summary(analysis_result: Dict) -> str:
        """
        生成流月综合分析总结

        Args:
            analysis_result: 综合分析结果

        Returns:
            总结文本
        """
        summary_parts = []

        # 流月基础信息
        liuyue_info = analysis_result["liuyue_analysis"]["liuyue_info"]
        summary_parts.append(
            f"{liuyue_info['year']}年{liuyue_info['month']}月流月{liuyue_info['pillar']}"
        )

        # 流月详细分析
        detailed = analysis_result["liuyue_analysis"]["detailed_analysis"]
        fortune = detailed["fortune_analysis"]["overall_fortune"]
        summary_parts.append(f"运势{fortune}")

        # 组合效应
        combination_effects = analysis_result.get("combination_effects", {})
        for combo_key, combo_data in combination_effects.items():
            if isinstance(combo_data, dict) and "overall_effect" in combo_data:
                summary_parts.append(
                    f"与{combo_key.replace('_', '、')}组合{combo_data['overall_effect']}"
                )

        return "，".join(summary_parts) + "。"

    @staticmethod
    def comprehensive_timing_analysis(
        birth_pillars: Dict,
        birth_date: datetime,
        gender: str,
        analysis_date: Optional[datetime] = None,
    ) -> Dict:
        """
        综合时运分析

        Args:
            birth_pillars: 出生四柱
            birth_date: 出生日期
            gender: 性别
            analysis_date: 分析日期，默认为当前日期

        Returns:
            综合时运分析结果
        """
        if analysis_date is None:
            analysis_date = datetime.now()

        # 计算当前年龄
        current_age = analysis_date.year - birth_date.year
        if analysis_date.month < birth_date.month or (
            analysis_date.month == birth_date.month
            and analysis_date.day < birth_date.day
        ):
            current_age -= 1

        # 大运分析
        dayun_analysis = TimingEffectsAnalysis.analyze_dayun_effects(
            birth_pillars, birth_date, gender, current_age
        )

        # 流年分析
        liunian_analysis = TimingEffectsAnalysis.analyze_liunian_effects(
            birth_pillars, analysis_date.year
        )

        # 流月分析
        liuyue_analysis = TimingEffectsAnalysis.analyze_liuyue_effects(
            birth_pillars, analysis_date.year, analysis_date.month
        )

        # 综合分析
        combined_timing_pillars = {}
        if "dayun_info" in dayun_analysis:
            combined_timing_pillars["dayun"] = {
                "stem": dayun_analysis["dayun_info"]["stem"],
                "branch": dayun_analysis["dayun_info"]["branch"],
            }

        combined_timing_pillars["liunian"] = {
            "stem": liunian_analysis["liunian_info"]["stem"],
            "branch": liunian_analysis["liunian_info"]["branch"],
        }

        combined_timing_pillars["liuyue"] = {
            "stem": liuyue_analysis["liuyue_info"]["stem"],
            "branch": liuyue_analysis["liuyue_info"]["branch"],
        }

        combined_effects = TimingEffectsAnalysis.analyze_element_strength_changes(
            birth_pillars, combined_timing_pillars
        )

        return {
            "analysis_date": analysis_date.strftime("%Y-%m-%d"),
            "current_age": current_age,
            "dayun_analysis": dayun_analysis,
            "liunian_analysis": liunian_analysis,
            "liuyue_analysis": liuyue_analysis,
            "combined_effects": combined_effects,
            "comprehensive_summary": TimingEffectsAnalysis._generate_comprehensive_summary(
                dayun_analysis, liunian_analysis, liuyue_analysis, combined_effects
            ),
        }

    @staticmethod
    def _generate_comprehensive_summary(
        dayun_analysis: Dict,
        liunian_analysis: Dict,
        liuyue_analysis: Dict,
        combined_effects: Dict,
    ) -> str:
        """生成综合时运分析总结"""
        summary_parts = []

        if "dayun_info" in dayun_analysis:
            dayun_pillar = dayun_analysis["dayun_info"]["pillar"]
            summary_parts.append(f"大运{dayun_pillar}")

        liunian_pillar = liunian_analysis["liunian_info"]["pillar"]
        liuyue_pillar = liuyue_analysis["liuyue_info"]["pillar"]

        summary_parts.extend([f"流年{liunian_pillar}", f"流月{liuyue_pillar}"])

        overall_effect = combined_effects["overall_effect"]

        return f"当前时运组合：{' + '.join(summary_parts)}，{overall_effect}。建议根据五行变化调整生活和工作重点。"
