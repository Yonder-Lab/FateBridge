"""
性格心性分析模块

基于八字命理的性格分析，综合以下经典技法：
- 日主五行定基本心性（木仁、火礼、土信、金义、水智）
- 十神定性格倾向（主导十神决定行为风格）
- 日主强弱与阴阳定刚柔、内外向
- 格局清浊定心性层次

核心分析维度：
1. 日主五行基本心性
2. 主导十神性格特征
3. 强弱阴阳（刚柔/内外向）
4. 性格优势与短板
5. 调适建议
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils.data import (
    STEM_ELEMENTS,
    Element,
    Polarity,
    TenGod,
    count_ten_gods,
)

ELEMENT_NATURE = {
    Element.WOOD: {
        "virtue": "仁",
        "traits": "仁慈、有恻隐之心、积极进取、有规划力",
        "short": "过则优柔、固执、好面子",
    },
    Element.FIRE: {
        "virtue": "礼",
        "traits": "热情、礼貌、有表现力、直爽光明",
        "short": "过则急躁、虚荣、缺乏耐性",
    },
    Element.EARTH: {
        "virtue": "信",
        "traits": "诚信、稳重、包容、务实可靠",
        "short": "过则固执、保守、行动迟缓",
    },
    Element.METAL: {
        "virtue": "义",
        "traits": "重义气、果断、有原则、执行力强",
        "short": "过则刚硬、肃杀、不近人情",
    },
    Element.WATER: {
        "virtue": "智",
        "traits": "聪明、灵活、应变力强、有谋略",
        "short": "过则多虑、善变、城府深",
    },
}

TEN_GOD_PERSONALITY = {
    TenGod.COMPARE: "自主独立、重朋友、竞争心强、不喜依赖",
    TenGod.ROB_WEALTH: "行动力强、敢闯敢拼、好胜、理财较冲动",
    TenGod.FOOD_GOD: "温和乐天、有口福才艺、随和包容、享受生活",
    TenGod.HURT_OFFICER: "聪明才高、表现欲强、不拘常规、易恃才傲物",
    TenGod.POSITIVE_WEALTH: "务实节俭、重责任、踏实顾家、计划性强",
    TenGod.PARTIAL_WEALTH: "慷慨豪爽、善交际、机会主义、风流多情",
    TenGod.POSITIVE_OFFICER: "正派守规、有责任感、自律、重名誉",
    TenGod.SEVEN_KILLER: "果敢有魄力、抗压、霸气、易冲动偏激",
    TenGod.POSITIVE_SEAL: "仁厚好学、重感情、有依赖性、慈悲",
    TenGod.PARTIAL_SEAL: "思维独特、敏感内省、有专才、孤僻多疑",
}


class PersonalityAnalysis:
    """性格心性分析工具类"""

    @staticmethod
    def analyze_personality(
        pillars: Dict[str, Tuple[str, str]],
        gender: Optional[str] = None,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        day_stem = pillars["day"][0]
        day_element = STEM_ELEMENTS[day_stem][0]
        day_polarity = STEM_ELEMENTS[day_stem][1]

        core_nature = PersonalityAnalysis._core_nature(day_element)
        dominant = PersonalityAnalysis._dominant_traits(pillars, day_stem)
        disposition = PersonalityAnalysis._disposition(pillars, day_polarity)
        strengths, weaknesses = PersonalityAnalysis._strengths_weaknesses(
            core_nature, dominant, disposition
        )
        advice = PersonalityAnalysis._advice(dominant, disposition)

        return {
            "day_master": f"{day_stem}（{day_element.value}）",
            "core_nature": core_nature,
            "dominant_traits": dominant,
            "disposition": disposition,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "advice": advice,
        }

    @staticmethod
    def _core_nature(day_element: Element) -> Dict[str, Any]:
        info = ELEMENT_NATURE[day_element]
        return {
            "element": day_element.value,
            "virtue": info["virtue"],
            "traits": info["traits"],
            "shortcoming": info["short"],
        }

    @staticmethod
    def _dominant_traits(
        pillars: Dict[str, Tuple[str, str]], day_stem: str
    ) -> Dict[str, Any]:
        counts = count_ten_gods(pillars, day_stem)
        ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top = [(g, c) for g, c in ranked if c > 0][:3]
        return {
            "top_gods": [
                {
                    "ten_god": g.value,
                    "weight": round(c, 1),
                    "traits": TEN_GOD_PERSONALITY.get(g, ""),
                }
                for g, c in top
            ],
            "primary": top[0][0].value if top else "",
        }

    @staticmethod
    def _disposition(
        pillars: Dict[str, Tuple[str, str]], day_polarity: Polarity
    ) -> Dict[str, Any]:
        from ..core.elements import ElementAnalysis

        dm = ElementAnalysis.analyze_day_master_strength(pillars)
        strength = dm["strength_level"]
        notes: List[str] = []
        if strength == "强":
            notes.append("日主旺，自我意识强、主见足、外向主动，但需防刚愎自用")
        elif strength == "弱":
            notes.append("日主弱，随和谦逊、依赖性较强、内敛，宜增强自信与决断")
        else:
            notes.append("日主中和，性格较平衡、能屈能伸")
        yin_yang = (
            "阳（刚健主动）" if day_polarity == Polarity.YANG else "阴（柔顺内敛）"
        )
        notes.append(f"日干为{yin_yang}")
        return {
            "strength": strength,
            "polarity": "阳" if day_polarity == Polarity.YANG else "阴",
            "notes": notes,
        }

    @staticmethod
    def _strengths_weaknesses(
        core: Dict[str, Any], dominant: Dict[str, Any], disposition: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        strengths = [core["traits"]]
        weaknesses = [core["shortcoming"]]
        if dominant["top_gods"]:
            strengths.append(dominant["top_gods"][0]["traits"])
        if disposition["strength"] == "强":
            weaknesses.append("过于强势、不易听取他人意见")
        elif disposition["strength"] == "弱":
            weaknesses.append("决断力不足、易受他人影响")
        return strengths, weaknesses

    @staticmethod
    def _advice(dominant: Dict[str, Any], disposition: Dict[str, Any]) -> List[str]:
        advice: List[str] = []
        primary = dominant.get("primary", "")
        if primary in ("七杀", "伤官", "劫财"):
            advice.append("个性偏刚锐，宜修心养性、控制情绪冲动，刚柔并济")
        elif primary in ("正印", "偏印", "正官"):
            advice.append("个性偏稳内敛，宜主动突破、增强行动力与表达")
        if disposition["strength"] == "弱":
            advice.append("宜培养自信与独立决断，借贵人之力成事")
        if not advice:
            advice.append("性格较为均衡，扬长避短、顺势而为即可")
        return advice
