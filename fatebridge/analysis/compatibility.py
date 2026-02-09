#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
高级合盘分析模块
提供深层次的命理分析合盘分析，超越简单的刑冲克害
"""

from typing import Dict, List, Any
from enum import Enum
from ..core.rules import BaZiRules
from ..utils.data import Element, TenGod, GENERATION_CYCLE, DESTRUCTION_CYCLE


class RelationshipType(Enum):
    """关系类型枚举"""

    MARRIAGE = "marriage"  # 婚姻
    FRIENDSHIP = "friendship"  # 友谊
    BUSINESS = "business"  # 商业合作
    FAMILY = "family"  # 家庭关系
    GENERAL = "general"  # 一般关系


class AdvancedCompatibility:
    """
    高级合盘分析工具类，提供深层次的命理分析配合度分析

    该类超越传统的刑冲克害分析，提供多维度的配合度评估：
    - 五行平衡：分析两人五行的互补性和协调性
    - 喜用神协同：评估双方喜用神的相互支持程度
    - 十神关系：分析两人十神配置的相互影响
    - 格局协同：评估两人命局格局的配合程度
    - 关系特化：针对不同关系类型提供专门的分析

    支持的关系类型：
    - 婚姻关系：重点分析夫妻宫、财官配置等
    - 商业合作：关注财星、官星、食伤的配合
    - 友谊关系：分析比劫、食伤的和谐程度
    - 家庭关系：考虑长幼有序、五行相生等
    - 一般关系：提供基础的配合度分析

    分析维度权重会根据关系类型动态调整，确保分析结果的针对性和准确性。
    """

    @staticmethod
    def analyze_comprehensive_compatibility(
        analysis1: Dict[str, Any],
        analysis2: Dict[str, Any],
        relationship_type: RelationshipType = RelationshipType.GENERAL,
    ) -> Dict[str, Any]:
        """
        综合分析两人命理分析合盘

        Args:
            analysis1: 第一人的命理分析信息
            analysis2: 第二人的命理分析信息
            relationship_type: 关系类型

        Returns:
            包含详细分析结果的字典
        """
        result = {
            "overall_score": 0.0,
            "relationship_type": relationship_type.value,
            "detailed_analysis": {
                "element_balance": {},
                "favorable_synergy": {},
                "ten_gods_relationship": {},
                "pattern_synergy": {},
                "traditional_analysis": {},
            },
            "recommendations": [],
            "strengths": [],
            "challenges": [],
            "summary": "",
        }

        # 提取四柱信息
        pillars1 = {
            k: (v["stem"], v["branch"]) for k, v in analysis1["four_pillars"].items()
        }
        pillars2 = {
            k: (v["stem"], v["branch"]) for k, v in analysis2["four_pillars"].items()
        }

        # 定义各维度权重（总计100%）
        weights = AdvancedCompatibility._get_dimension_weights(relationship_type)

        # 1. 五行平衡分析 (权重: 25%)
        element_analysis = AdvancedCompatibility._analyze_element_balance(analysis1, analysis2)
        result["detailed_analysis"]["element_balance"] = element_analysis
        weighted_element_score = element_analysis["score"] * weights["element_balance"]
        result["overall_score"] += weighted_element_score

        # 2. 喜用神互助分析 (权重: 30%)
        favorable_analysis = AdvancedCompatibility._analyze_favorable_synergy(
            analysis1, analysis2
        )
        result["detailed_analysis"]["favorable_synergy"] = favorable_analysis
        weighted_favorable_score = (
            favorable_analysis["score"] * weights["favorable_synergy"]
        )
        result["overall_score"] += weighted_favorable_score

        # 3. 十神关系分析 (权重: 25%)
        ten_gods_analysis = AdvancedCompatibility._analyze_ten_gods_relationship(
            analysis1, analysis2, relationship_type
        )
        result["detailed_analysis"]["ten_gods_relationship"] = ten_gods_analysis
        weighted_ten_gods_score = (
            ten_gods_analysis["score"] * weights["ten_gods_relationship"]
        )
        result["overall_score"] += weighted_ten_gods_score

        # 4. 格局配合分析 (权重: 15%)
        pattern_analysis = AdvancedCompatibility._analyze_pattern_synergy(analysis1, analysis2)
        result["detailed_analysis"]["pattern_synergy"] = pattern_analysis
        weighted_pattern_score = pattern_analysis["score"] * weights["pattern_synergy"]
        result["overall_score"] += weighted_pattern_score

        # 5. 传统刑冲克害分析 (权重: 5%)
        # 使用新的规则计算传统分析分数
        # 由于calculate_compatibility_score可能还没有更新，我们手动计算
        traditional_score = 50.0  # 基础分
        details = []
        
        # 提取地支
        branches1 = [branch for _, branch in pillars1.values()]
        branches2 = [branch for _, branch in pillars2.values()]
        
        # 检查六冲
        for b1 in branches1:
            for b2 in branches2:
                for clash_pair in BaZiRules.SIX_CLASH:
                    if (b1, b2) in [clash_pair, clash_pair[::-1]]:
                        traditional_score -= 2
                        details.append(f"{b1}与{b2}六冲")
        
        # 检查六害
        for b1 in branches1:
            for b2 in branches2:
                for harm_pair in BaZiRules.SIX_HARM:
                    if (b1, b2) in [harm_pair, harm_pair[::-1]]:
                        traditional_score -= 2
                        details.append(f"{b1}与{b2}六害")
                        
        # 检查三刑
        # 这是一个简化检查，实际三刑需要三个地支，这里只检查两个人的地支组合
        all_combined_branches = branches1 + branches2
        for punishment_set in BaZiRules.TRIPLE_PUNISHMENT:
             found = [b for b in punishment_set if b in all_combined_branches]
             if len(punishment_set) == 3 and len(found) == 3:
                 traditional_score -= 5
                 details.append(f"合盘构成{''.join(punishment_set)}三刑")
        
        normalized_traditional_score = min(100, max(0, traditional_score))
        
        traditional_analysis = {
            "overall_score": (traditional_score - 50) / 10, # 转换回大致的原始分数范围
            "normalized_score": normalized_traditional_score,
            "details": details
        }
        
        result["detailed_analysis"]["traditional_analysis"] = traditional_analysis
        weighted_traditional_score = (
            normalized_traditional_score * weights["traditional_analysis"]
        )
        result["overall_score"] += weighted_traditional_score

        # 确保总分在0-100范围内
        result["overall_score"] = min(100.0, max(0.0, result["overall_score"]))

        # 6. 根据关系类型调整分析重点
        relationship_adjustment = AdvancedCompatibility._adjust_for_relationship_type(
            result["detailed_analysis"], relationship_type
        )
        result["recommendations"].extend(relationship_adjustment["recommendations"])

        # 7. 生成综合评价
        result = AdvancedCompatibility._generate_comprehensive_summary(result)

        return result

    @staticmethod
    def _get_dimension_weights(relationship_type: RelationshipType) -> Dict[str, float]:
        """
        根据关系类型获取各维度权重

        Args:
            relationship_type: 关系类型

        Returns:
            各维度权重字典，总和为1.0
        """
        if relationship_type == RelationshipType.MARRIAGE:
            return {
                "element_balance": 0.25,  # 五行平衡 25%
                "favorable_synergy": 0.35,  # 喜用神互助 35%
                "ten_gods_relationship": 0.17,  # 十神关系 17%
                "pattern_synergy": 0.18,  # 格局配合 18%
                "traditional_analysis": 0.05,  # 传统分析 5%
            }
        elif relationship_type == RelationshipType.BUSINESS:
            return {
                "element_balance": 0.15,  # 五行平衡 15%
                "favorable_synergy": 0.32,  # 喜用神互助 32%
                "ten_gods_relationship": 0.35,  # 十神关系 35%
                "pattern_synergy": 0.13,  # 格局配合 13%
                "traditional_analysis": 0.05,  # 传统分析 5%
            }
        elif relationship_type == RelationshipType.FRIENDSHIP:
            return {
                "element_balance": 0.35,  # 五行平衡 35%
                "favorable_synergy": 0.30,  # 喜用神互助 30%
                "ten_gods_relationship": 0.20,  # 十神关系 20%
                "pattern_synergy": 0.10,  # 格局配合 10%
                "traditional_analysis": 0.05,  # 传统分析 5%
            }
        elif relationship_type == RelationshipType.FAMILY:
            return {
                "element_balance": 0.25,  # 五行平衡 25%
                "favorable_synergy": 0.30,  # 喜用神互助 30%
                "ten_gods_relationship": 0.20,  # 十神关系 20%
                "pattern_synergy": 0.20,  # 格局配合 20%
                "traditional_analysis": 0.05,  # 传统分析 5%
            }
        else:  # GENERAL
            return {
                "element_balance": 0.25,  # 五行平衡 25%
                "favorable_synergy": 0.35,  # 喜用神互助 35%
                "ten_gods_relationship": 0.22,  # 十神关系 22%
                "pattern_synergy": 0.13,  # 格局配合 13%
                "traditional_analysis": 0.05,  # 传统分析 5%
            }

    @staticmethod
    def _analyze_element_balance(
        analysis1: Dict[str, Any], analysis2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析五行平衡互补，返回0-100分"""
        analysis = {
            "score": 65.0,  # 基础分65分，正常情况下应该有基本的兼容性
            "details": [],
            "balance_type": "",
            "mutual_support": [],
        }

        # 获取两人的五行强弱分布
        person1_elements = analysis1.get("element_analysis", {}).get(
            "element_percentages", {}
        )
        person2_elements = analysis2.get("element_analysis", {}).get(
            "element_percentages", {}
        )

        # 获取日主强弱
        person1_strength = (
            analysis1.get("element_analysis", {})
            .get("day_master_strength", {})
            .get("strength", "中等")
        )
        person2_strength = (
            analysis2.get("element_analysis", {})
            .get("day_master_strength", {})
            .get("strength", "中等")
        )

        # 从day_master字典获取天干和五行
        person1_day_master_dict = analysis1.get("day_master", {})
        person2_day_master_dict = analysis2.get("day_master", {})

        # 正确提取天干
        person1_day_master = (
            person1_day_master_dict.get("stem", "")
            if isinstance(person1_day_master_dict, dict)
            else ""
        )
        person2_day_master = (
            person2_day_master_dict.get("stem", "")
            if isinstance(person2_day_master_dict, dict)
            else ""
        )

        # 直接从day_master字典获取五行，更可靠
        person1_element = (
            person1_day_master_dict.get("element", "")
            if isinstance(person1_day_master_dict, dict)
            else ""
        )
        person2_element = (
            person2_day_master_dict.get("element", "")
            if isinstance(person2_day_master_dict, dict)
            else ""
        )

        # 分析日主五行关系 (权重40%)
        if person1_element and person2_element:
            if person1_element == person2_element:
                analysis["details"].append(
                    f"两人日主同为{person1_element}，容易理解对方"
                )
                analysis["score"] += 15  # +15分
                analysis["balance_type"] = "同类互助"
            else:
                # 检查生克关系
                person1_element_enum = next(
                    (
                        element_enum
                        for element_enum in Element
                        if element_enum.value == person1_element
                    ),
                    None,
                )
                person2_element_enum = next(
                    (
                        element_enum
                        for element_enum in Element
                        if element_enum.value == person2_element
                    ),
                    None,
                )

                if person1_element_enum and person2_element_enum:
                    if (
                        person1_element_enum in GENERATION_CYCLE
                        and GENERATION_CYCLE[person1_element_enum]
                        == person2_element_enum
                    ):
                        analysis["details"].append(
                            f"{person1_element}生{person2_element}，{person1_element}方能助{person2_element}方"
                        )
                        analysis["score"] += 25  # +25分
                        analysis["balance_type"] = "相生互助"
                        analysis["mutual_support"].append(
                            f"{person1_element}→{person2_element}"
                        )
                    elif (
                        person2_element_enum in GENERATION_CYCLE
                        and GENERATION_CYCLE[person2_element_enum]
                        == person1_element_enum
                    ):
                        analysis["details"].append(
                            f"{person2_element}生{person1_element}，{person2_element}方能助{person1_element}方"
                        )
                        analysis["score"] += 25  # +25分
                        analysis["balance_type"] = "相生互助"
                        analysis["mutual_support"].append(
                            f"{person2_element}→{person1_element}"
                        )
                    elif (
                        person1_element_enum in DESTRUCTION_CYCLE
                        and DESTRUCTION_CYCLE[person1_element_enum]
                        == person2_element_enum
                    ):
                        analysis["details"].append(
                            f"{person1_element}克{person2_element}，可能存在压制关系"
                        )
                        analysis["score"] -= 15  # -15分
                        analysis["balance_type"] = "相克制约"
                    elif (
                        person2_element_enum in DESTRUCTION_CYCLE
                        and DESTRUCTION_CYCLE[person2_element_enum]
                        == person1_element_enum
                    ):
                        analysis["details"].append(
                            f"{person2_element}克{person1_element}，可能存在压制关系"
                        )
                        analysis["score"] -= 15  # -15分
                        analysis["balance_type"] = "相克制约"
                    else:
                        analysis["details"].append(
                            f"{person1_element}与{person2_element}关系平和"
                        )
                        analysis["score"] += 10  # +10分
                        analysis["balance_type"] = "平和相处"

        # 分析强弱互补 (权重30%)
        if person1_strength and person2_strength:
            if (person1_strength == "强" and person2_strength == "弱") or (
                person1_strength == "弱" and person2_strength == "强"
            ):
                analysis["details"].append("两人强弱互补，能够相互平衡")
                analysis["score"] += 20  # +20分
            elif person1_strength == person2_strength:
                if person1_strength == "中":
                    analysis["details"].append("两人都较为平衡，关系稳定")
                    analysis["score"] += 10  # +10分
                else:
                    analysis["details"].append(
                        f"两人都偏{person1_strength}，可能缺乏平衡"
                    )
                    analysis["score"] -= 10  # -10分

        # 分析五行分布互补 (权重30%)
        if person1_elements and person2_elements:
            complement_score = 0
            for element in ["木", "火", "土", "金", "水"]:
                person1_element_count = person1_elements.get(element, 0)
                person2_element_count = person2_elements.get(element, 0)

                # 如果一方缺乏某五行，另一方较强，则互补性好
                if person1_element_count == 0 and person2_element_count >= 2:
                    complement_score += 3
                    analysis["details"].append(
                        f"甲方缺{element}，乙方{element}较强，形成互补"
                    )
                elif person2_element_count == 0 and person1_element_count >= 2:
                    complement_score += 3
                    analysis["details"].append(
                        f"乙方缺{element}，甲方{element}较强，形成互补"
                    )
                elif abs(person1_element_count - person2_element_count) <= 1:
                    complement_score += 1  # 平衡也是好的

            analysis["score"] += min(15, complement_score * 2)  # 最多+15分

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_favorable_synergy(
        analysis1: Dict[str, Any], analysis2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析喜用神互助，返回0-100分"""
        analysis = {
            "score": 60.0,  # 基础分60分，即使没有明显互助也应该有基本分数
            "details": [],
            "mutual_help": [],
            "synergy_level": "",
        }

        # 安全处理favorable_elements，避免unhashable type错误
        person1_favorable_list = analysis1.get("favorable_elements", [])
        person2_favorable_list = analysis2.get("favorable_elements", [])

        # 确保是字符串列表后再转换为集合
        if isinstance(person1_favorable_list, list) and all(
            isinstance(x, str) for x in person1_favorable_list
        ):
            person1_favorable_elements = set(person1_favorable_list)
        else:
            person1_favorable_elements = set()

        if isinstance(person2_favorable_list, list) and all(
            isinstance(x, str) for x in person2_favorable_list
        ):
            person2_favorable_elements = set(person2_favorable_list)
        else:
            person2_favorable_elements = set()

        # 获取两人的五行分布
        person1_element_distribution = analysis1.get("element_analysis", {}).get(
            "element_distribution", {}
        )
        person2_element_distribution = analysis2.get("element_analysis", {}).get(
            "element_distribution", {}
        )

        # 分析互助情况 (权重50%)
        mutual_help_count = 0
        mutual_help_strength = 0

        # 检查第一人的喜用神是否在第二人命理分析中较强
        for favorable_element in person1_favorable_elements:
            if favorable_element in person2_element_distribution:
                element_count = person2_element_distribution[favorable_element]
                if element_count >= 3:
                    analysis["mutual_help"].append(
                        f"第二人命理分析中{favorable_element}很强，大助第一人"
                    )
                    mutual_help_count += 1
                    mutual_help_strength += 3
                elif element_count >= 2:
                    analysis["mutual_help"].append(
                        f"第二人命理分析中{favorable_element}较强，有助第一人"
                    )
                    mutual_help_count += 1
                    mutual_help_strength += 2
                elif element_count == 1:
                    analysis["mutual_help"].append(
                        f"第二人命理分析中{favorable_element}一般，略助第一人"
                    )
                    mutual_help_strength += 1

        # 检查第二人的喜用神是否在第一人命理分析中较强
        for favorable_element in person2_favorable_elements:
            if favorable_element in person1_element_distribution:
                element_count = person1_element_distribution[favorable_element]
                if element_count >= 3:
                    analysis["mutual_help"].append(
                        f"第一人命理分析中{favorable_element}很强，大助第二人"
                    )
                    mutual_help_count += 1
                    mutual_help_strength += 3
                elif element_count >= 2:
                    analysis["mutual_help"].append(
                        f"第一人命理分析中{favorable_element}较强，有助第二人"
                    )
                    mutual_help_count += 1
                    mutual_help_strength += 2
                elif element_count == 1:
                    analysis["mutual_help"].append(
                        f"第一人命理分析中{favorable_element}一般，略助第二人"
                    )
                    mutual_help_strength += 1

        # 根据互助情况计算得分
        if mutual_help_count >= 3:
            analysis["score"] += 30  # +30分
            analysis["synergy_level"] = "强力互助"
            analysis["details"].append("两人能够强力相互补益，关系非常和谐")
        elif mutual_help_count == 2:
            analysis["score"] += 25  # +25分
            analysis["synergy_level"] = "双向互助"
            analysis["details"].append("两人能够相互补益，关系和谐")
        elif mutual_help_count == 1:
            analysis["score"] += 15  # +15分
            analysis["synergy_level"] = "单向互助"
            analysis["details"].append("一方能够帮助另一方")
        else:
            analysis["score"] -= 10  # -10分
            analysis["synergy_level"] = "无明显互助"
            analysis["details"].append("在喜用神方面无明显互助关系")

        # 根据互助强度额外加分
        analysis["score"] += min(20, mutual_help_strength * 2)  # 最多+20分

        # 检查共同喜用神 (权重30%)
        common_favorable_elements = (
            person1_favorable_elements & person2_favorable_elements
        )
        if common_favorable_elements:
            common_favorable_score = (
                len(common_favorable_elements) * 8
            )  # 每个共同喜用神+8分
            analysis["details"].append(
                f"共同喜用神：{', '.join(common_favorable_elements)}，目标一致"
            )
            analysis["score"] += min(20, common_favorable_score)  # 最多+20分

        # 检查喜用神冲突 (权重20%)
        # 安全处理unfavorable_elements，避免unhashable type错误
        person1_unfavorable_list = analysis1.get("unfavorable_elements", [])
        person2_unfavorable_list = analysis2.get("unfavorable_elements", [])

        if isinstance(person1_unfavorable_list, list) and all(
            isinstance(x, str) for x in person1_unfavorable_list
        ):
            person1_unfavorable_elements = set(person1_unfavorable_list)
        else:
            person1_unfavorable_elements = set()

        if isinstance(person2_unfavorable_list, list) and all(
            isinstance(x, str) for x in person2_unfavorable_list
        ):
            person2_unfavorable_elements = set(person2_unfavorable_list)
        else:
            person2_unfavorable_elements = set()

        # 如果一方的喜用神是另一方的忌神，扣分
        conflict_count = 0
        if person1_favorable_elements & person2_unfavorable_elements:
            conflict_elements = (
                person1_favorable_elements & person2_unfavorable_elements
            )
            analysis["details"].append(
                f"第一人喜用神{', '.join(conflict_elements)}与第二人忌神冲突"
            )
            conflict_count += len(conflict_elements)

        if person2_favorable_elements & person1_unfavorable_elements:
            conflict_elements = (
                person2_favorable_elements & person1_unfavorable_elements
            )
            analysis["details"].append(
                f"第二人喜用神{', '.join(conflict_elements)}与第一人忌神冲突"
            )
            conflict_count += len(conflict_elements)

        if conflict_count > 0:
            analysis["score"] -= conflict_count * 10  # 每个冲突-10分

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_ten_gods_relationship(
        analysis1: Dict[str, Any],
        analysis2: Dict[str, Any],
        relationship_type: RelationshipType,
    ) -> Dict[str, Any]:
        """分析十神关系 - 基于各自日主计算十神关系"""
        analysis = {
            "score": 65.0,  # 基础分65分，正常的十神关系应该有基本的兼容性
            "details": [],
            "relationship_dynamics": [],
            "compatibility_aspects": [],
        }

        # 获取两人的日主天干（十神计算需要天干，不是五行）
        day_master1_dict = analysis1.get("day_master")
        day_master2_dict = analysis2.get("day_master")

        # 处理不同的日主格式，获取天干
        if isinstance(day_master1_dict, dict):
            day_master1 = day_master1_dict.get("stem", "")
        else:
            day_master1 = day_master1_dict if day_master1_dict else ""

        if isinstance(day_master2_dict, dict):
            day_master2 = day_master2_dict.get("stem", "")
        else:
            day_master2 = day_master2_dict if day_master2_dict else ""

        if not day_master1 or not day_master2:
            analysis["details"].append("无法获取日主信息，无法分析十神关系")
            return analysis

        # 分析A的命理分析对B日主的十神影响
        person1_to_person2_gods = AdvancedCompatibility._calculate_cross_ten_gods(
            analysis1, day_master2, "第一人对第二人"
        )

        # 分析B的命理分析对A日主的十神影响
        person2_to_person1_gods = AdvancedCompatibility._calculate_cross_ten_gods(
            analysis2, day_master1, "第二人对第一人"
        )

        # 合并分析结果 - 使用不同的键来避免覆盖
        all_cross_gods = {
            "person1_to_person2": person1_to_person2_gods,
            "person2_to_person1": person2_to_person1_gods,
        }

        # 根据关系类型分析十神配合
        if relationship_type == RelationshipType.MARRIAGE:
            analysis = AdvancedCompatibility._analyze_marriage_cross_ten_gods(
                all_cross_gods, analysis
            )
        elif relationship_type == RelationshipType.BUSINESS:
            analysis = AdvancedCompatibility._analyze_business_cross_ten_gods(
                all_cross_gods, analysis
            )
        elif relationship_type == RelationshipType.FRIENDSHIP:
            analysis = AdvancedCompatibility._analyze_friendship_cross_ten_gods(
                all_cross_gods, analysis
            )
        else:
            analysis = AdvancedCompatibility._analyze_general_cross_ten_gods(
                all_cross_gods, analysis
            )

        return analysis

    @staticmethod
    def _calculate_cross_ten_gods(
        analysis: Dict[str, Any], target_day_master: str, description: str
    ) -> Dict[str, Any]:
        """计算一个人的命理分析对另一个人日主的十神影响 - 基于天干计算"""
        from ..utils.data import get_ten_god

        cross_gods = {
            "description": description,
            "ten_gods_count": {},
            "strong_influences": [],
            "element_influences": {},
        }

        # 获取目标日主的天干
        target_day_master_stem = target_day_master

        # 如果target_day_master是元素而不是天干，转换为天干
        if target_day_master in ["木", "火", "土", "金", "水"]:
            element_to_stem = {
                "木": "甲",
                "火": "丙",
                "土": "戊",
                "金": "庚",
                "水": "壬",
            }
            target_day_master_stem = element_to_stem.get(target_day_master)

        if not target_day_master_stem:
            return cross_gods

        # 获取四柱信息
        four_pillars = analysis.get("four_pillars", {})

        # 遍历四柱的天干，计算对目标日主的十神关系
        pillar_names = ["year", "month", "day", "hour"]
        for pillar_name in pillar_names:
            if pillar_name in four_pillars:
                pillar = four_pillars[pillar_name]
                stem = pillar.get("stem")

                if stem:
                    # 使用正确的get_ten_god函数计算十神关系
                    ten_god = get_ten_god(target_day_master_stem, stem)

                    # 统计十神数量（每个天干权重为25%）
                    weight = 25.0
                    if ten_god in cross_gods["ten_gods_count"]:
                        cross_gods["ten_gods_count"][ten_god] += weight
                    else:
                        cross_gods["ten_gods_count"][ten_god] = weight

                    # 记录强影响
                    cross_gods["strong_influences"].append(
                        f"{stem}({ten_god})×{weight}"
                    )

        # 计算元素影响（为了保持兼容性）
        element_distribution = analysis.get("element_distribution", {})
        for element_str, percentage in element_distribution.items():
            if percentage > 0:
                # 找到该元素对应的主要十神
                element_to_stem = {
                    "木": "甲",
                    "火": "丙",
                    "土": "戊",
                    "金": "庚",
                    "水": "壬",
                }
                element_stem = element_to_stem.get(element_str)
                if element_stem:
                    ten_god = get_ten_god(target_day_master_stem, element_stem)
                    cross_gods["element_influences"][element_str] = {
                        "ten_god": ten_god,
                        "count": percentage,
                        "strength": (
                            "强"
                            if percentage >= 30
                            else "中" if percentage >= 15 else "弱"
                        ),
                    }

        return cross_gods

    @staticmethod
    def _count_ten_gods(ten_gods: Dict[str, List]) -> Dict[str, int]:
        """统计十神数量"""
        count = {}
        for pillar_gods in ten_gods.values():
            for god_info in pillar_gods:
                god_name = god_info.get("ten_god", "")
                count[god_name] = count.get(god_name, 0) + 1
        return count

    @staticmethod
    def _analyze_marriage_cross_ten_gods(
        cross_gods: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析婚姻关系的跨人十神配合"""

        # 提取所有十神统计
        all_ten_gods = {}
        for key, gods_data in cross_gods.items():
            if isinstance(gods_data, dict) and "ten_gods_count" in gods_data:
                for ten_god, count in gods_data["ten_gods_count"].items():
                    all_ten_gods[ten_god] = all_ten_gods.get(ten_god, 0) + count

        # 导入TenGod枚举

        # 婚姻中有利的十神影响 (权重40%)
        favorable_gods = {
            TenGod.POSITIVE_OFFICER: 15,  # 正官代表责任感，有利婚姻
            TenGod.POSITIVE_WEALTH: 12,  # 正财代表稳定收入，有利婚姻
            TenGod.POSITIVE_SEAL: 10,  # 正印代表关爱，有利婚姻
            TenGod.FOOD_GOD: 8,  # 食神代表温和，有利婚姻
            TenGod.PARTIAL_WEALTH: 6,  # 偏财适度有利
        }

        # 婚姻中不利的十神影响
        unfavorable_gods = {
            TenGod.SEVEN_KILLER: -10,  # 七杀过多易冲突
            TenGod.HURT_OFFICER: -8,  # 伤官过多易争执
            TenGod.ROB_WEALTH: -6,  # 劫财过多易破财
            TenGod.PARTIAL_SEAL: -5,  # 偏印过多易孤独
        }

        # 计算十神影响得分
        for ten_god, count in all_ten_gods.items():
            if ten_god in favorable_gods:
                bonus = favorable_gods[ten_god] * min(count, 2)  # 最多计算2个
                analysis["score"] += bonus
                analysis["details"].append(
                    f"跨人{ten_god.value}影响×{count}，有利婚姻(+{bonus}分)"
                )
                analysis["compatibility_aspects"].append(f"{ten_god.value}互助")
            elif ten_god in unfavorable_gods:
                penalty = unfavorable_gods[ten_god] * min(count, 3)  # 最多扣3个的分
                analysis["score"] += penalty  # penalty是负数
                analysis["details"].append(
                    f"跨人{ten_god.value}影响×{count}，需要注意({penalty}分)"
                )

        # 分析互补性 (权重30%)
        complementary_pairs = [
            (TenGod.POSITIVE_OFFICER, TenGod.POSITIVE_SEAL),  # 官印相生
            (TenGod.POSITIVE_WEALTH, TenGod.FOOD_GOD),  # 食神生财
            (TenGod.COMPARE, TenGod.POSITIVE_OFFICER),  # 官制比肩
        ]

        for god1, god2 in complementary_pairs:
            if all_ten_gods.get(god1, 0) > 0 and all_ten_gods.get(god2, 0) > 0:
                analysis["score"] += 12
                analysis["details"].append(
                    f"跨人{god1.value}与{god2.value}形成互补，有利婚姻"
                )
                analysis["relationship_dynamics"].append(
                    f"{god1.value}-{god2.value}互补"
                )

        # 确保分数在合理范围
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_business_cross_ten_gods(
        cross_gods: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析商业关系的跨人十神配合"""

        # 提取所有十神统计
        all_ten_gods = {}
        for key, gods_data in cross_gods.items():
            if isinstance(gods_data, dict) and "ten_gods_count" in gods_data:
                for ten_god, count in gods_data["ten_gods_count"].items():
                    all_ten_gods[ten_god] = all_ten_gods.get(ten_god, 0) + count

        # 商业中有利的十神影响
        favorable_gods = {
            "正财": 15,  # 正财代表稳定收入
            "偏财": 12,  # 偏财代表投资机会
            "食神": 10,  # 食神代表创意才华
            "伤官": 8,  # 伤官代表技术能力
            "正官": 8,  # 正官代表管理能力
        }

        # 商业中不利的十神影响
        unfavorable_gods = {
            "劫财": -8,  # 劫财易破财
            "偏印": -6,  # 偏印易孤立
            "七杀": -4,  # 七杀过多易冲突
        }

        # 计算十神影响得分
        for ten_god, count in all_ten_gods.items():
            if ten_god in favorable_gods:
                bonus = favorable_gods[ten_god] * min(count, 2)
                analysis["score"] += bonus
                analysis["details"].append(
                    f"跨人{ten_god}影响×{count}，有利商业合作(+{bonus}分)"
                )
                analysis["compatibility_aspects"].append(f"{ten_god}助力")
            elif ten_god in unfavorable_gods:
                penalty = unfavorable_gods[ten_god] * min(count, 2)
                analysis["score"] += penalty
                analysis["details"].append(
                    f"跨人{ten_god}影响×{count}，需要注意({penalty}分)"
                )

        # 分析商业互补性
        business_pairs = [
            ("正财", "食神"),  # 创意变现
            ("偏财", "伤官"),  # 技能变现
            ("正官", "正印", 14),  # 官印相生，管理有序 +14分
            ("七杀", "食神", 15),  # 七杀配食神，执行力强 +15分
            ("比肩", "劫财", 10),  # 比劫合作，资源整合 +10分
            ("偏印", "伤官", 12),  # 偏印伤官，技术创新 +12分
        ]

        # 检查商业组合
        for god1, god2, score_bonus in business_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(f"一方{god1}配另一方{god2}，有利商业合作")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god1}-{god2}商业配合")
            elif gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0:
                analysis["details"].append(f"一方{god2}配另一方{god1}，有利商业合作")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god2}-{god1}商业配合")

        # 分析商业角色互补 (权重30%)
        role_complements = [
            ("正官", "偏财", "一方善管理（正官），一方善经营（偏财）", 12),
            ("正印", "伤官", "一方深策略（正印），一方深执行（伤官）", 10),
            ("七杀", "正印", "一方决断力强（七杀），一方深思熟虑（正印）", 11),
            ("食神", "比肩", "一方创意丰富（食神），一方执行稳定（比肩）", 9),
        ]

        for god1, god2, desc, score_bonus in role_complements:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["relationship_dynamics"].append(desc)
                analysis["score"] += score_bonus

        # 检查商业风险组合 (权重20%)
        risk_combinations = [
            ("劫财", "偏财", "劫财夺财，利益冲突风险", -18),
            ("七杀", "七杀", "双方都过于强势，决策冲突", -15),
            ("伤官", "正官", "伤官见官，管理混乱", -12),
            ("比肩", "比肩", "过于相似，缺乏互补", -8),
        ]

        for god1, god2, desc, score_penalty in risk_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_penalty

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_friendship_cross_ten_gods(
        cross_gods: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析友谊关系的跨人十神配合"""

        # 提取所有十神统计
        all_ten_gods = {}
        for key, gods_data in cross_gods.items():
            if isinstance(gods_data, dict) and "ten_gods_count" in gods_data:
                for ten_god, count in gods_data["ten_gods_count"].items():
                    all_ten_gods[ten_god] = all_ten_gods.get(ten_god, 0) + count

        # 友谊中有利的十神影响
        favorable_gods = {
            "食神": 12,  # 食神代表温和友善
            "正印": 10,  # 正印代表关爱包容
            "比肩": 8,  # 比肩代表平等友好
            "正官": 6,  # 正官代表正直可靠
            "正财": 5,  # 正财代表稳重
        }

        # 友谊中不利的十神影响
        unfavorable_gods = {
            "伤官": -6,  # 伤官易争执
            "七杀": -8,  # 七杀易冲突
            "劫财": -4,  # 劫财易竞争
        }

        # 计算十神影响得分
        for ten_god, count in all_ten_gods.items():
            if ten_god in favorable_gods:
                bonus = favorable_gods[ten_god] * min(count, 2)
                analysis["score"] += bonus
                analysis["details"].append(
                    f"跨人{ten_god}影响×{count}，有利友谊(+{bonus}分)"
                )
                analysis["compatibility_aspects"].append(f"{ten_god}friendly")
            elif ten_god in unfavorable_gods:
                penalty = unfavorable_gods[ten_god] * min(count, 2)
                analysis["score"] += penalty
                analysis["details"].append(
                    f"跨人{ten_god}影响×{count}，需要注意({penalty}分)"
                )

        analysis["score"] = min(100.0, max(0.0, analysis["score"]))
        return analysis

    @staticmethod
    def _analyze_general_cross_ten_gods(
        cross_gods: Dict[str, Any], analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析一般关系的跨人十神配合"""

        # 提取所有十神统计
        all_ten_gods = {}
        for key, gods_data in cross_gods.items():
            if isinstance(gods_data, dict) and "ten_gods_count" in gods_data:
                for ten_god, count in gods_data["ten_gods_count"].items():
                    all_ten_gods[ten_god] = all_ten_gods.get(ten_god, 0) + count

        # 一般关系中的十神影响（相对温和）
        god_influences = {
            "食神": 8,  # 食神温和
            "正印": 6,  # 正印关爱
            "正官": 5,  # 正官正直
            "正财": 4,  # 正财稳重
            "比肩": 3,  # 比肩平等
            "偏财": 2,  # 偏财灵活
            "伤官": -3,  # 伤官易争执
            "七杀": -5,  # 七杀易冲突
            "劫财": -2,  # 劫财易竞争
            "偏印": -2,  # 偏印易孤立
        }

        # 计算十神影响得分
        for ten_god, count in all_ten_gods.items():
            if ten_god in god_influences:
                influence = god_influences[ten_god] * min(count, 2)
                analysis["score"] += influence
                if influence > 0:
                    analysis["details"].append(
                        f"跨人{ten_god}影响×{count}，总体有利(+{influence}分)"
                    )
                    analysis["compatibility_aspects"].append(f"{ten_god}正面")
                else:
                    analysis["details"].append(
                        f"跨人{ten_god}影响×{count}，需要注意({influence}分)"
                    )

        analysis["score"] = min(100.0, max(0.0, analysis["score"]))
        return analysis

    @staticmethod
    def _analyze_marriage_ten_gods(
        gods1: Dict[str, int], gods2: Dict[str, int]
    ) -> Dict[str, Any]:
        """分析婚姻关系的十神配合，返回0-100分"""
        analysis = {
            "score": 50.0,  # 基础分50分
            "details": [],
            "relationship_dynamics": [],
            "compatibility_aspects": [],
        }

        # 婚姻中的有利十神组合 (权重40%)
        favorable_combinations = [
            ("正官", "正印", 15),  # 官印相生 +15分
            ("偏财", "食神", 12),  # 食神生财 +12分
            ("正财", "伤官", 12),  # 伤官生财 +12分
            ("比肩", "劫财", 8),  # 比劫帮身 +8分
            ("正印", "偏印", 10),  # 印星互助 +10分
            ("食神", "伤官", 8),  # 食伤配合 +8分
        ]

        # 检查有利组合
        for god1, god2, score_bonus in favorable_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(f"一方{god1}配另一方{god2}，有利婚姻")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god1}-{god2}配合")
            elif gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0:
                analysis["details"].append(f"一方{god2}配另一方{god1}，有利婚姻")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god2}-{god1}配合")

        # 分析性格互补 (权重30%)
        complement_pairs = [
            ("正官", "伤官", "一方稳重（正官），一方活泼（伤官）", 10),
            ("正印", "食神", "一方内敛（正印），一方外向（食神）", 10),
            ("偏财", "正印", "一方务实（偏财），一方理想（正印）", 8),
            ("七杀", "食神", "一方强势（七杀），一方温和（食神）", 12),
        ]

        for god1, god2, desc, score_bonus in complement_pairs:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["relationship_dynamics"].append(desc)
                analysis["score"] += score_bonus

        # 检查不利组合 (权重30%)
        unfavorable_combinations = [
            ("七杀", "伤官", "七杀配伤官，容易冲突", -15),
            ("劫财", "偏财", "劫财夺财，经济纠纷", -12),
            ("比肩", "正官", "比肩抗官，权威冲突", -10),
        ]

        for god1, god2, desc, score_penalty in unfavorable_combinations:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["details"].append(desc)
                analysis["score"] += score_penalty

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_business_ten_gods(
        gods1: Dict[str, int], gods2: Dict[str, int]
    ) -> Dict[str, Any]:
        """分析商业合作的十神配合，返回0-100分"""
        analysis = {
            "score": 45.0,  # 商业合作基础分45分（相对保守）
            "details": [],
            "relationship_dynamics": [],
            "compatibility_aspects": [],
        }

        # 商业中的有利十神组合 (权重50%)
        business_combinations = [
            ("正财", "食神", 18),  # 食神生财，创意变现 +18分
            ("偏财", "伤官", 16),  # 伤官生财，技能变现 +16分
            ("正官", "正印", 14),  # 官印相生，管理有序 +14分
            ("七杀", "食神", 15),  # 七杀配食神，执行力强 +15分
            ("比肩", "劫财", 10),  # 比劫合作，资源整合 +10分
            ("偏印", "伤官", 12),  # 偏印伤官，技术创新 +12分
        ]

        # 检查商业组合
        for god1, god2, score_bonus in business_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(f"一方{god1}配另一方{god2}，有利商业合作")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god1}-{god2}商业配合")
            elif gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0:
                analysis["details"].append(f"一方{god2}配另一方{god1}，有利商业合作")
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god2}-{god1}商业配合")

        # 分析商业角色互补 (权重30%)
        role_complements = [
            ("正官", "偏财", "一方善管理（正官），一方善经营（偏财）", 12),
            ("正印", "伤官", "一方重策略（正印），一方重执行（伤官）", 10),
            ("七杀", "正印", "一方决断力强（七杀），一方深思熟虑（正印）", 11),
            ("食神", "比肩", "一方创意丰富（食神），一方执行稳定（比肩）", 9),
        ]

        for god1, god2, desc, score_bonus in role_complements:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["relationship_dynamics"].append(desc)
                analysis["score"] += score_bonus

        # 检查商业风险组合 (权重20%)
        risk_combinations = [
            ("劫财", "偏财", "劫财夺财，利益冲突风险", -18),
            ("七杀", "七杀", "双方都过于强势，决策冲突", -15),
            ("伤官", "正官", "伤官见官，管理混乱", -12),
            ("比肩", "比肩", "过于相似，缺乏互补", -8),
        ]

        for god1, god2, desc, score_penalty in risk_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_penalty

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_friendship_ten_gods(
        gods1: Dict[str, int], gods2: Dict[str, int]
    ) -> Dict[str, Any]:
        """分析友谊关系的十神配合，返回0-100分"""
        analysis = {
            "score": 55.0,  # 友谊基础分55分（相对宽松）
            "details": [],
            "relationship_dynamics": [],
            "compatibility_aspects": [],
        }

        # 友谊中的和谐组合 (权重40%)
        harmony_combinations = [
            ("食神", "食神", "双方都开朗乐观，相处愉快", 12),
            ("正印", "正印", "双方都内敛稳重，深度交流", 10),
            ("比肩", "比肩", "性格相似，容易理解", 8),
            ("食神", "比肩", "一方活泼一方稳定，互补平衡", 11),
            ("正印", "食神", "一方深沉一方开朗，互相吸引", 13),
            ("伤官", "食神", "都有创意天赋，共同话题多", 10),
        ]

        # 检查和谐组合
        for god1, god2, desc, score_bonus in harmony_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god1}-{god2}和谐")

        # 友谊中的互补组合 (权重35%)
        complement_combinations = [
            ("正官", "伤官", "一方规矩一方自由，互相学习", 12),
            ("七杀", "食神", "一方强势一方温和，平衡关系", 11),
            ("偏印", "伤官", "一方内向一方外向，互补较强", 10),
            ("正财", "比肩", "一方务实一方理想，视角不同", 9),
            ("劫财", "正印", "一方冲动一方冷静，相互制衡", 8),
        ]

        for god1, god2, desc, score_bonus in complement_combinations:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["relationship_dynamics"].append(desc)
                analysis["score"] += score_bonus

        # 友谊中的冲突组合 (权重25%)
        conflict_combinations = [
            ("七杀", "七杀", "双方都过于强势，容易争执", -12),
            ("劫财", "劫财", "都比较冲动，可能产生摩擦", -10),
            ("伤官", "正官", "价值观差异较大，难以理解", -8),
            ("偏印", "偏印", "都比较孤僻，缺乏交流", -6),
        ]

        for god1, god2, desc, score_penalty in conflict_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_penalty

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_general_ten_gods(
        gods1: Dict[str, int], gods2: Dict[str, int]
    ) -> Dict[str, Any]:
        """通用十神关系分析，返回0-100分"""
        analysis = {
            "score": 50.0,  # 通用关系基础分50分
            "details": [],
            "relationship_dynamics": [],
            "compatibility_aspects": [],
        }

        # 通用的和谐组合 (权重45%)
        harmony_combinations = [
            ("正官", "正印", "官印相生，秩序与智慧结合", 15),
            ("食神", "正财", "食神生财，才华变现", 14),
            ("比肩", "劫财", "比劫帮身，互助合作", 10),
            ("正印", "食神", "印绶食神，学识与创意", 12),
            ("偏财", "伤官", "伤官生财，技能致富", 13),
            ("七杀", "正印", "杀印相生，威权与智慧", 11),
        ]

        # 检查和谐组合
        for god1, god2, desc, score_bonus in harmony_combinations:
            if gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god1}-{god2}配合")
            elif gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0:
                analysis["details"].append(desc)
                analysis["score"] += score_bonus
                analysis["compatibility_aspects"].append(f"{god2}-{god1}配合")

        # 通用的互补组合 (权重35%)
        complement_combinations = [
            ("正官", "伤官", "规范与创新的平衡", 10),
            ("正印", "偏财", "理论与实践的结合", 9),
            ("七杀", "食神", "刚柔并济，相得益彰", 11),
            ("比肩", "正财", "合作与竞争的平衡", 8),
            ("劫财", "正印", "冲动与理性的制衡", 7),
        ]

        for god1, god2, desc, score_bonus in complement_combinations:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["relationship_dynamics"].append(desc)
                analysis["score"] += score_bonus

        # 通用的冲突组合 (权重20%)
        conflict_combinations = [
            ("七杀", "伤官", "威权与叛逆的冲突", -12),
            ("劫财", "正财", "争夺与保守的矛盾", -10),
            ("偏印", "食神", "偏印夺食，创意受阻", -8),
            ("比肩", "正官", "平等与等级的冲突", -6),
        ]

        for god1, god2, desc, score_penalty in conflict_combinations:
            if (gods1.get(god1, 0) > 0 and gods2.get(god2, 0) > 0) or (
                gods1.get(god2, 0) > 0 and gods2.get(god1, 0) > 0
            ):
                analysis["details"].append(desc)
                analysis["score"] += score_penalty

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _analyze_pattern_synergy(
        analysis1: Dict[str, Any], analysis2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析格局配合，返回0-100分"""
        analysis = {
            "score": 70.0,  # 格局协同基础分70分，不同格局之间通常有基本的兼容性
            "details": [],
            "pattern_combination": "",
            "synergy_effects": [],
        }

        # 获取两人的格局信息
        patterns1 = analysis1.get("patterns", {})
        patterns2 = analysis2.get("patterns", {})

        # 分析三合六合配合 (权重40%)
        harmony1 = patterns1.get("harmony", {})
        harmony2 = patterns2.get("harmony", {})

        # 三合局检查 (包括全三合和半三合)
        has_three1 = bool(harmony1.get("three_harmony"))
        has_half1 = bool(harmony1.get("half_harmony"))
        has_three2 = bool(harmony2.get("three_harmony"))
        has_half2 = bool(harmony2.get("half_harmony"))

        if has_three1 and has_three2:
            analysis["details"].append("两人都有三合局，格局高度相配")
            analysis["score"] += 25
            analysis["pattern_combination"] = "双三合"
            analysis["synergy_effects"].append("三合局互相呼应，能量倍增")
        elif (has_three1 and has_half2) or (has_half1 and has_three2):
            analysis["details"].append("三合配合半合，能量互补")
            analysis["score"] += 20
            analysis["pattern_combination"] = "三合配半合"
            analysis["synergy_effects"].append("强弱搭配，互为助力")
        elif has_half1 and has_half2:
            analysis["details"].append("两人都有半合局，气场相投")
            analysis["score"] += 15
            analysis["pattern_combination"] = "双半合"
            analysis["synergy_effects"].append("半合共鸣，潜移默化")
        elif has_three1 or has_three2:
            analysis["details"].append("一方有三合局，带动整体格局")
            analysis["score"] += 15
            if not analysis["pattern_combination"]:
                analysis["pattern_combination"] = "单三合"
        elif has_half1 or has_half2:
            analysis["details"].append("一方有半合局，增加格局灵活性")
            analysis["score"] += 10
            if not analysis["pattern_combination"]:
                analysis["pattern_combination"] = "单半合"

        if harmony1.get("six_harmony") and harmony2.get("six_harmony"):
            analysis["details"].append("两人都有六合，关系和谐稳定")
            analysis["score"] += 20
            if analysis["pattern_combination"]:
                analysis["pattern_combination"] += "+双六合"
            else:
                analysis["pattern_combination"] = "双六合"
            analysis["synergy_effects"].append("六合配合，关系融洽")
        elif harmony1.get("six_harmony") or harmony2.get("six_harmony"):
            analysis["details"].append("一方有六合，增进关系和谐")
            analysis["score"] += 12
            if analysis["pattern_combination"]:
                analysis["pattern_combination"] += "+单六合"
            else:
                analysis["pattern_combination"] = "单六合"

        # 分析特殊格局配合 (权重35%)
        special1 = patterns1.get("special", {})
        special2 = patterns2.get("special", {})

        # 检查是否有相同的特殊格局
        if special1 and special2:
            common_patterns = set(special1.keys()) & set(special2.keys())
            if common_patterns:
                analysis["details"].append(
                    f"两人都有{list(common_patterns)}格局，志同道合"
                )
                analysis["score"] += 18
                analysis["synergy_effects"].append("特殊格局共鸣，理解深刻")
            else:
                analysis["details"].append("两人都有特殊格局，各有所长")
                analysis["score"] += 12
                analysis["synergy_effects"].append("特殊格局互补，各展所长")
        elif special1 or special2:
            analysis["details"].append("一方有特殊格局，带来独特优势")
            analysis["score"] += 8

        # 分析格局强弱配合 (权重25%)
        strength1 = patterns1.get("strength", "medium")
        strength2 = patterns2.get("strength", "medium")

        if strength1 == "strong" and strength2 == "strong":
            analysis["details"].append("两人格局都很强，需要协调配合")
            analysis["score"] += 10
            analysis["synergy_effects"].append("双强格局，需要平衡发展")
        elif strength1 == "strong" or strength2 == "strong":
            analysis["details"].append("一强一弱，可以互相扶持")
            analysis["score"] += 15
            analysis["synergy_effects"].append("强弱配合，相得益彰")
        elif strength1 == "medium" and strength2 == "medium":
            analysis["details"].append("两人格局平衡，发展稳定")
            analysis["score"] += 12

        # 检查格局冲突
        if patterns1.get("conflicts") or patterns2.get("conflicts"):
            analysis["details"].append("存在格局冲突，需要化解")
            analysis["score"] -= 10

        # 确保分数在0-100范围内
        analysis["score"] = min(100.0, max(0.0, analysis["score"]))

        return analysis

    @staticmethod
    def _adjust_for_relationship_type(
        detailed_analysis: Dict[str, Any], relationship_type: RelationshipType
    ) -> Dict[str, Any]:
        """根据关系类型调整分析重点"""
        adjustment = {"score_adjustment": 0, "recommendations": []}

        if relationship_type == RelationshipType.MARRIAGE:
            # 婚姻关系更重视五行互补和喜用神互助
            element_score = detailed_analysis.get("element_balance", {}).get("score", 0)
            favorable_score = detailed_analysis.get("favorable_synergy", {}).get(
                "score", 0
            )
            adjustment["score_adjustment"] = (element_score + favorable_score) * 0.3
            adjustment["recommendations"].append("婚姻关系建议重视五行互补和精神契合")

        elif relationship_type == RelationshipType.BUSINESS:
            # 商业合作更重视十神配合和格局协调
            ten_gods_score = detailed_analysis.get("ten_gods_relationship", {}).get(
                "score", 0
            )
            pattern_score = detailed_analysis.get("pattern_synergy", {}).get("score", 0)
            adjustment["score_adjustment"] = (ten_gods_score + pattern_score) * 0.2
            adjustment["recommendations"].append("商业合作建议发挥各自优势，互补不足")

        elif relationship_type == RelationshipType.FRIENDSHIP:
            # 友谊关系更重视性格相投
            ten_gods_score = detailed_analysis.get("ten_gods_relationship", {}).get(
                "score", 0
            )
            adjustment["score_adjustment"] = ten_gods_score * 0.2
            adjustment["recommendations"].append("友谊关系建议保持真诚，互相理解")

        return adjustment

    @staticmethod
    def _generate_comprehensive_summary(result: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合评价"""
        overall_score = result["overall_score"]

        # 收集优势和挑战
        for analysis_type, analysis_data in result["detailed_analysis"].items():
            if analysis_data.get("score", 0) > 3:
                if analysis_data.get("details"):
                    result["strengths"].extend(analysis_data["details"][:2])  # 取前两个
            elif analysis_data.get("score", 0) < 0:
                if analysis_data.get("details"):
                    result["challenges"].extend(analysis_data["details"][:2])

        # 生成总结
        if overall_score >= 15:
            result["summary"] = "非常匹配，各方面都很协调，是理想的组合"
        elif overall_score >= 10:
            result["summary"] = "比较匹配，大部分方面都很好，小部分需要磨合"
        elif overall_score >= 5:
            result["summary"] = "一般匹配，有优势也有挑战，需要相互理解"
        elif overall_score >= 0:
            result["summary"] = "需要努力，存在一些挑战，但通过努力可以改善"
        else:
            result["summary"] = "匹配度较低，需要慎重考虑或寻求专业指导"

        return result
