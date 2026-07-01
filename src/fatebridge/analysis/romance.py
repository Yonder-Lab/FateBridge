"""
正缘桃花分析模块

区别于「婚姻」模块（侧重配偶宫/配偶星/婚姻质量），本模块侧重感情、异性缘与桃花，
综合以下经典技法：
- 桃花（咸池）神煞：申子辰见酉、寅午戌见卯、亥卯未见子、巳酉丑见午
- 红鸾、天喜：主婚恋喜庆
- 异性缘星：男命以财为异性缘，女命以官杀为异性缘
- 桃花正邪：逢合为正缘助力，逢刑冲为烂桃花/感情波折

核心分析维度：
1. 桃花（咸池）定位与多寡
2. 红鸾天喜
3. 异性缘星（按性别）强弱
4. 桃花正邪（合/刑冲）
5. 正缘出现时机（大运流年引动桃花/异性缘星）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..utils.data import (
    TenGod,
    check_branch_combination,
    check_branch_conflict,
    get_ten_god,
    normalize_gender,
    sum_ten_god_weight,
)

# 桃花（咸池）：三合局 -> 桃花地支
_PEACH_TARGETS = (
    (("申", "子", "辰"), "酉"),
    (("寅", "午", "戌"), "卯"),
    (("亥", "卯", "未"), "子"),
    (("巳", "酉", "丑"), "午"),
)

# 红鸾（年支 -> 红鸾地支）
_HONGLUAN = {
    "子": "卯",
    "丑": "寅",
    "寅": "丑",
    "卯": "子",
    "辰": "亥",
    "巳": "戌",
    "午": "酉",
    "未": "申",
    "申": "未",
    "酉": "午",
    "戌": "巳",
    "亥": "辰",
}
# 天喜（年支 -> 天喜地支，红鸾对宫）
_TIANXI = {
    "子": "酉",
    "丑": "申",
    "寅": "未",
    "卯": "午",
    "辰": "巳",
    "巳": "辰",
    "午": "卯",
    "未": "寅",
    "申": "丑",
    "酉": "子",
    "戌": "亥",
    "亥": "戌",
}


class RomanceAnalysis:
    """正缘桃花分析工具类"""

    @staticmethod
    def analyze_romance(
        pillars: Dict[str, Tuple[str, str]],
        gender: Optional[str] = None,
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        day_stem = pillars["day"][0]
        norm_gender = normalize_gender(gender)
        branches = {name: branch for name, (_, branch) in pillars.items()}

        peach = RomanceAnalysis._peach_blossom(pillars, branches)
        luan_xi = RomanceAnalysis._hongluan_tianxi(pillars, branches)
        opposite = RomanceAnalysis._opposite_sex_star(pillars, day_stem, norm_gender)
        quality = RomanceAnalysis._peach_quality(peach, pillars)
        timing = RomanceAnalysis._romance_timing(
            pillars, day_stem, norm_gender, peach, dayun_pillar, liunian_pillar
        )

        return {
            "gender_basis": opposite["basis"],
            "peach_blossom": peach,
            "hongluan_tianxi": luan_xi,
            "opposite_sex_star": opposite,
            "peach_quality": quality,
            "romance_timing": timing,
        }

    @staticmethod
    def _peach_targets(branches: Dict[str, str]) -> set:
        triggers = {branches.get("year"), branches.get("day")}
        targets = set()
        for group, target in _PEACH_TARGETS:
            if triggers & set(group):
                targets.add(target)
        return targets

    @staticmethod
    def _peach_blossom(
        pillars: Dict[str, Tuple[str, str]], branches: Dict[str, str]
    ) -> Dict[str, Any]:
        targets = RomanceAnalysis._peach_targets(branches)
        hits = [name for name, b in branches.items() if b in targets]
        if hits:
            note = "命带桃花（咸池），异性缘旺、有魅力；多则需防感情纷扰"
        else:
            note = "命无明显桃花，异性缘平稳，逢桃花之大运流年增强"
        return {
            "peach_branches": sorted(targets),
            "hit_pillars": hits,
            "count": len(hits),
            "note": note,
        }

    @staticmethod
    def _hongluan_tianxi(
        pillars: Dict[str, Tuple[str, str]], branches: Dict[str, str]
    ) -> Dict[str, Any]:
        year_branch = branches.get("year", "")
        hongluan = _HONGLUAN.get(year_branch)
        tianxi = _TIANXI.get(year_branch)
        luan_hits = [n for n, b in branches.items() if b == hongluan]
        xi_hits = [n for n, b in branches.items() if b == tianxi]
        notes: List[str] = []
        if luan_hits:
            notes.append("命带红鸾，主婚恋喜事、姻缘显")
        if xi_hits:
            notes.append("命带天喜，主喜庆、添丁、婚嫁之喜")
        if not notes:
            notes.append(
                f"命无红鸾天喜（红鸾在{hongluan}、天喜在{tianxi}），逢之流年主婚恋喜庆"
            )
        return {
            "hongluan_branch": hongluan,
            "tianxi_branch": tianxi,
            "hongluan_hits": luan_hits,
            "tianxi_hits": xi_hits,
            "notes": notes,
        }

    @staticmethod
    def _opposite_sex_star(
        pillars: Dict[str, Tuple[str, str]], day_stem: str, norm_gender: Optional[str]
    ) -> Dict[str, Any]:
        if norm_gender == "male":
            gods: Tuple[TenGod, ...] = (TenGod.POSITIVE_WEALTH, TenGod.PARTIAL_WEALTH)
            basis = "财星（男命异性缘）"
        elif norm_gender == "female":
            gods = (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER)
            basis = "官杀（女命异性缘）"
        else:
            gods = (
                TenGod.POSITIVE_WEALTH,
                TenGod.PARTIAL_WEALTH,
                TenGod.POSITIVE_OFFICER,
                TenGod.SEVEN_KILLER,
            )
            basis = "财/官杀（性别未提供，兼看）"

        weight = sum_ten_god_weight(pillars, day_stem, gods)
        if weight == 0:
            status = "异性缘星不显，感情主动性弱或缘分较晚，宜主动把握"
        elif weight >= 2.5:
            status = "异性缘星旺，异性缘佳、追求者多，但易眼花缭乱、感情多波"
        else:
            status = "异性缘星适中，感情发展平稳"
        return {"basis": basis, "weight": weight, "status": status}

    @staticmethod
    def _peach_quality(
        peach: Dict[str, Any], pillars: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Any]:
        notes: List[str] = []
        branches = [b for _, b in pillars.values()]
        for name in peach["hit_pillars"]:
            pb = dict(pillars)[name][1] if name in pillars else None
            if pb is None:
                continue
            if any(o != pb and check_branch_conflict(pb, o) for o in branches):
                notes.append(f"{name}桃花逢冲，主烂桃花/感情起伏、聚散无常")
            elif any(o != pb and check_branch_combination(pb, o) for o in branches):
                notes.append(f"{name}桃花逢合，主正桃花/感情有归宿、易成姻缘")
        if not peach["hit_pillars"]:
            notes.append("命无桃花入局，感情较少外缘干扰")
        elif not notes:
            notes.append("桃花无明显刑冲合，异性缘平稳")
        return {"notes": notes}

    @staticmethod
    def _romance_timing(
        pillars: Dict[str, Tuple[str, str]],
        day_stem: str,
        norm_gender: Optional[str],
        peach: Dict[str, Any],
        dayun_pillar: Optional[Tuple[str, str]] = None,
        liunian_pillar: Optional[Tuple[str, str]] = None,
    ) -> Dict[str, Any]:
        signals: List[str] = []
        year_branch = pillars["year"][1]
        peach_targets = set(peach["peach_branches"])
        hongluan = _HONGLUAN.get(year_branch)
        tianxi = _TIANXI.get(year_branch)

        if norm_gender == "male":
            star_gods: Tuple[TenGod, ...] = (
                TenGod.POSITIVE_WEALTH,
                TenGod.PARTIAL_WEALTH,
            )
        elif norm_gender == "female":
            star_gods = (TenGod.POSITIVE_OFFICER, TenGod.SEVEN_KILLER)
        else:
            star_gods = (
                TenGod.POSITIVE_WEALTH,
                TenGod.PARTIAL_WEALTH,
                TenGod.POSITIVE_OFFICER,
                TenGod.SEVEN_KILLER,
            )

        def _assess(label: str, pillar: Tuple[str, str]) -> None:
            stem, branch = pillar
            if get_ten_god(day_stem, stem) in star_gods:
                signals.append(
                    f"{label}{stem}{branch}引动异性缘星，利于桃花、恋爱、正缘出现"
                )
            if branch in peach_targets:
                signals.append(f"{label}逢桃花{branch}，异性缘旺、易有感情际遇")
            if branch == hongluan:
                signals.append(f"{label}逢红鸾{branch}，主姻缘、婚恋喜事")
            elif branch == tianxi:
                signals.append(f"{label}逢天喜{branch}，主喜庆、婚嫁添丁")

        if dayun_pillar:
            _assess("大运", dayun_pillar)
        if liunian_pillar:
            _assess("流年", liunian_pillar)
        if not signals:
            signals.append("未提供大运/流年，无法判断正缘/桃花时机")
        return {"timing_signals": signals}
