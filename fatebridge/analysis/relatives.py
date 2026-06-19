"""
六亲关系分析模块

基于八字命理的六亲分析（聚焦父母与兄弟姐妹，配偶见婚姻模块、子女见子女模块），
综合以下经典技法：
- 子平六亲法：父为偏财、母为正印、兄弟姐妹为比劫
- 宫位法：年柱主祖上/父母，月柱主父母/兄弟
- 星宫同参：星之强弱定缘分助力，宫之冲合定亲疏

核心分析维度：
1. 父母星（偏财/正印）定位、强弱与缘分助力
2. 兄弟姐妹星（比劫）多寡与助益/竞争
3. 六亲宫位（年/月柱）状态
4. 与六亲关系（生克冲合）
5. 贵人助力提示
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils.data import (
    TenGod,
    check_branch_combination,
    check_branch_conflict,
    iter_pillar_gods,
)


class RelativesAnalysis:
    """六亲关系分析工具类"""

    @staticmethod
    def analyze_relatives(
        pillars: Dict[str, Tuple[str, str]],
        gender: Optional[str] = None,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        day_stem = pillars["day"][0]

        parents = RelativesAnalysis._analyze_parents(pillars, day_stem)
        siblings = RelativesAnalysis._analyze_siblings(pillars, day_stem)
        palaces = RelativesAnalysis._analyze_palaces(pillars)
        nobles = RelativesAnalysis._analyze_support(pillars, day_stem)

        return {
            "parents": parents,
            "siblings": siblings,
            "palaces": palaces,
            "support": nobles,
        }

    @staticmethod
    def _star_weight(
        pillars: Dict[str, Tuple[str, str]], day_stem: str, gods: Tuple[TenGod, ...]
    ) -> float:
        weight = sum(
            e.weight for e in iter_pillar_gods(pillars, day_stem) if e.ten_god in gods
        )
        return round(weight, 1)

    @staticmethod
    def _analyze_parents(
        pillars: Dict[str, Tuple[str, str]], day_stem: str
    ) -> Dict[str, Any]:
        father = RelativesAnalysis._star_weight(
            pillars, day_stem, (TenGod.PARTIAL_WEALTH,)
        )
        mother = RelativesAnalysis._star_weight(
            pillars, day_stem, (TenGod.POSITIVE_SEAL,)
        )

        notes: List[str] = []
        notes.append(
            "父星（偏财）有力，与父缘分较厚、父辈有助"
            if father >= 1.0
            else "父星（偏财）不显，与父缘较淡或聚少离多"
        )
        notes.append(
            "母星（正印）有力，得母荫庇、母慈而助力大"
            if mother >= 1.0
            else "母星（正印）不显，与母缘较淡或母操劳"
        )
        return {
            "father_star_weight": father,
            "mother_star_weight": mother,
            "notes": notes,
        }

    @staticmethod
    def _analyze_siblings(
        pillars: Dict[str, Tuple[str, str]], day_stem: str
    ) -> Dict[str, Any]:
        weight = RelativesAnalysis._star_weight(
            pillars, day_stem, (TenGod.COMPARE, TenGod.ROB_WEALTH)
        )
        from ..core.elements import ElementAnalysis

        strength = ElementAnalysis.analyze_day_master_strength(pillars)[
            "strength_level"
        ]
        notes: List[str] = []
        if weight >= 2.0:
            if strength == "弱":
                notes.append("比劫旺而日主弱，兄弟朋友多且为助力（帮身）")
            else:
                notes.append("比劫旺而日主强，兄弟朋友多但易竞争夺财，宜防合伙纠纷")
        elif weight == 0:
            notes.append("比劫不显，兄弟姐妹缘薄或助力有限，凡事多靠自己")
        else:
            notes.append("比劫适中，手足关系平稳")
        return {"sibling_star_weight": weight, "notes": notes}

    @staticmethod
    def _analyze_palaces(pillars: Dict[str, Tuple[str, str]]) -> Dict[str, Any]:
        year_branch = pillars["year"][1]
        month_branch = pillars["month"][1]
        relations: List[str] = []

        # 年柱（祖上/父母宫）、月柱（父母/兄弟宫）与日支冲合
        day_branch = pillars["day"][1]
        if check_branch_conflict(year_branch, day_branch):
            relations.append("年支与日支相冲，与祖上/长辈缘分较动荡或早年离乡")
        if check_branch_conflict(month_branch, day_branch):
            relations.append("月支与日支相冲，与父母兄弟易有摩擦或聚少离多")
        elif check_branch_combination(month_branch, day_branch):
            relations.append("月支与日支相合，与父母兄弟关系融洽、得助")
        if not relations:
            relations.append("年/月柱六亲宫无明显冲合，六亲关系平稳")
        return {
            "year_pillar": "".join(pillars["year"]),
            "month_pillar": "".join(pillars["month"]),
            "relations": relations,
        }

    @staticmethod
    def _analyze_support(
        pillars: Dict[str, Tuple[str, str]], day_stem: str
    ) -> Dict[str, Any]:
        seal = RelativesAnalysis._star_weight(
            pillars, day_stem, (TenGod.POSITIVE_SEAL, TenGod.PARTIAL_SEAL)
        )
        peer = RelativesAnalysis._star_weight(
            pillars, day_stem, (TenGod.COMPARE, TenGod.ROB_WEALTH)
        )
        notes: List[str] = []
        if seal >= 1.0:
            notes.append("印星为助，长辈/贵人/师长助力明显")
        if peer >= 1.0:
            notes.append("比劫为助，平辈/朋友/合作伙伴可借力")
        if not notes:
            notes.append("印比偏弱，贵人助力有限，宜主动经营人脉")
        return {"seal_weight": seal, "peer_weight": peer, "notes": notes}
