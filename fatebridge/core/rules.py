"""
BaZi rules and pattern analysis.
"""

from typing import Dict, List, Tuple, Any
from ..utils.data import HEAVENLY_STEMS, EARTHLY_BRANCHES


class BaZiRules:
    """Analyzes special patterns and rules in BaZi charts."""

    # 地支三合 (Triple Harmony)
    TRIPLE_HARMONY = [
        ("申", "子", "辰"),  # 水局
        ("亥", "卯", "未"),  # 木局
        ("寅", "午", "戌"),  # 火局
        ("巳", "酉", "丑"),  # 金局
    ]

    # 地支六合 (Six Harmony)
    SIX_HARMONY = [
        ("子", "丑"),
        ("寅", "亥"),
        ("卯", "戌"),
        ("辰", "酉"),
        ("巳", "申"),
        ("午", "未"),
    ]

    # 地支六冲 (Six Clash)
    SIX_CLASH = [
        ("子", "午"),
        ("丑", "未"),
        ("寅", "申"),
        ("卯", "酉"),
        ("辰", "戌"),
        ("巳", "亥"),
    ]

    # 地支六害 (Six Harm)
    SIX_HARM = [
        ("子", "未"),
        ("丑", "午"),
        ("寅", "巳"),
        ("卯", "辰"),
        ("申", "亥"),
        ("酉", "戌"),
    ]

    # 地支三刑 (Triple Punishment)
    TRIPLE_PUNISHMENT = [
        ("寅", "巳", "申"),  # 无恩之刑
        ("丑", "戌", "未"),  # 恃势之刑
        ("子", "卯"),  # 无礼之刑
        ("辰",),
        ("午",),
        ("酉",),
        ("亥",),  # 自刑
    ]

    # 天干五合 (Heavenly Stems Combinations)
    STEM_COMBINATIONS = [
        ("甲", "己", "土"),  # 中正之合
        ("乙", "庚", "金"),  # 仁义之合
        ("丙", "辛", "水"),  # 威制之合
        ("丁", "壬", "木"),  # 淫匿之合
        ("戊", "癸", "火"),  # 无情之合
    ]

    # 天干四冲 (Heavenly Stems Clashes)
    STEM_CLASHES = [
        ("甲", "庚"),
        ("乙", "辛"),
        ("丙", "壬"),
        ("丁", "癸"),
    ]

    # 地支拱局 (Arch Combinations)
    # (Branch1, Branch2, Arched_Branch, Element, Related_Stem)
    ARCH_COMBINATIONS = [
        ("寅", "辰", "卯", "木", "乙"),  # 拱东方木
        ("巳", "未", "午", "火", "丁"),  # 拱南方火
        ("申", "戌", "酉", "金", "辛"),  # 拱西方金
        ("亥", "丑", "子", "水", "癸"),  # 拱北方水
    ]

    # 地支暗合 (Dark Combinations)
    # 一般指地支藏干相合
    DARK_COMBINATIONS = [
        ("子", "巳"), # 癸-戊
        ("寅", "丑"), # 甲-己, 丙-辛
        ("午", "亥"), # 丁-壬, 己-甲
        ("卯", "申"), # 乙-庚
        ("子", "辰"), # 癸-戊 (Special case mentioned by user)
    ]

    # 四驿马 (Four Horses / Four Travels) - 生
    FOUR_HORSES = ["寅", "申", "巳", "亥"]

    # 四正 (Four Cardinals / Four Peaches) - 旺
    FOUR_CARDINALS = ["子", "午", "卯", "酉"]

    # 四库 (Four Treasuries / Four Graves) - 墓
    FOUR_TREASURIES = ["辰", "戌", "丑", "未"]

    @staticmethod
    def check_harmony_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[str]]:
        """Check for harmony patterns in the chart."""
        all_branches = [pillar_branch for _, pillar_branch in pillars.values()]
        harmony_patterns = {
            "three_harmony": [],
            "half_harmony": [],
            "six_harmony": [],
        }

        # Check triple harmony and half harmony
        for triple_harmony_set in BaZiRules.TRIPLE_HARMONY:
            found_branches_in_set = [
                branch for branch in triple_harmony_set if branch in all_branches
            ]
            
            element_mapping = {
                ("申", "子", "辰"): "水局",
                ("亥", "卯", "未"): "木局",
                ("寅", "午", "戌"): "火局",
                ("巳", "酉", "丑"): "金局",
            }
            base_type = element_mapping[triple_harmony_set]

            if len(found_branches_in_set) == 3:
                harmony_patterns["three_harmony"].append(
                    {
                        "type": f"三合{base_type}",
                        "branches": found_branches_in_set,
                        "complete": True,
                    }
                )
            elif len(found_branches_in_set) == 2:
                harmony_patterns["half_harmony"].append(
                    {
                        "type": f"半合{base_type}",
                        "branches": found_branches_in_set,
                        "complete": False,
                    }
                )

        # Check six harmony
        for six_harmony_pair in BaZiRules.SIX_HARMONY:
            if all(branch in all_branches for branch in six_harmony_pair):
                harmony_patterns["six_harmony"].append(list(six_harmony_pair))

        return harmony_patterns

    @staticmethod
    def check_clash_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, Any]:
        """Check for clash patterns in the chart."""
        all_branches = [pillar_branch for _, pillar_branch in pillars.values()]
        clash_patterns = {
            "six_clash": [],
            "six_harm": [],
            "punishments": [],  # Unified list for all punishments
        }

        # Check six clash
        for six_clash_pair in BaZiRules.SIX_CLASH:
            if all(branch in all_branches for branch in six_clash_pair):
                clash_patterns["six_clash"].append(list(six_clash_pair))

        # Check six harm
        for six_harm_pair in BaZiRules.SIX_HARM:
            if all(branch in all_branches for branch in six_harm_pair):
                clash_patterns["six_harm"].append(list(six_harm_pair))

        # Check punishments
        # 1. Triple Punishments (寅巳申, 丑戌未)
        for punishment_set in BaZiRules.TRIPLE_PUNISHMENT:
            if len(punishment_set) == 3:
                found_branches = [b for b in punishment_set if b in all_branches]
                
                # Full Triple Punishment
                if len(found_branches) == 3:
                    name_map = {
                        ("寅", "巳", "申"): "无恩之刑",
                        ("丑", "戌", "未"): "恃势之刑"
                    }
                    name = name_map.get(punishment_set, "三刑")
                    clash_patterns["punishments"].append({
                        "name": name,
                        "type": "three_punishment",
                        "branches": found_branches
                    })
                
                # Partial Punishment (Pairs within the set)
                elif len(found_branches) == 2:
                    # Specific pairs logic
                    # 寅巳: Harm + Punishment
                    # 巳申: Harmony + Punishment
                    # 寅申: Clash + Punishment
                    # 丑戌: Punishment
                    # 戌未: Punishment
                    # 丑未: Clash
                    
                    b1, b2 = found_branches[0], found_branches[1]
                    pair_name = f"{b1}{b2}相刑"
                    
                    # Filter out if it's purely a Clash (usually Clash overrides Punishment in nomenclature)
                    # But for completeness we can list it, or filter.
                    # Let's keep it but mark as 'pair_punishment'
                    clash_patterns["punishments"].append({
                        "name": pair_name,
                        "type": "pair_punishment",
                        "branches": found_branches
                    })

            # 2. Rude Punishment (子卯)
            elif len(punishment_set) == 2:
                if all(branch in all_branches for branch in punishment_set):
                    clash_patterns["punishments"].append({
                        "name": "无礼之刑",
                        "type": "pair_punishment",
                        "branches": list(punishment_set)
                    })

            # 3. Self Punishment (辰, 午, 酉, 亥)
            elif len(punishment_set) == 1:
                punishment_branch = punishment_set[0]
                branch_count = all_branches.count(punishment_branch)
                if branch_count >= 2:
                    clash_patterns["punishments"].append({
                        "name": f"{punishment_branch}{punishment_branch}自刑",
                        "type": "self_punishment",
                        "branches": [punishment_branch] * branch_count
                    })

        return clash_patterns

    @staticmethod
    def check_stem_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Check for Heavenly Stem patterns (Combinations, Clashes, Control)."""
        stems = {k: v[0] for k, v in pillars.items()} # position -> stem
        patterns = {
            "combinations": [],
            "clashes": [],
            "controls": []
        }
        
        pillar_names = ["year", "month", "day", "hour"]
        
        # Check adjacent pairs only (Year-Month, Month-Day, Day-Hour)
        # This reflects the rule that stems must be adjacent to interact significantly.
        for i in range(len(pillar_names) - 1):
            p1, p2 = pillar_names[i], pillar_names[i+1]
            s1, s2 = stems[p1], stems[p2]
            
            # Combinations
            for c1, c2, transform in BaZiRules.STEM_COMBINATIONS:
                if (s1 == c1 and s2 == c2) or (s1 == c2 and s2 == c1):
                    patterns["combinations"].append({
                        "stems": [s1, s2],
                        "pillars": [p1, p2],
                        "transform": transform,
                        "name": f"{s1}{s2}合化{transform}"
                    })
            
            # Clashes (Chong)
            for c1, c2 in BaZiRules.STEM_CLASHES:
                if (s1 == c1 and s2 == c2) or (s1 == c2 and s2 == c1):
                    patterns["clashes"].append({
                        "stems": [s1, s2],
                        "pillars": [p1, p2],
                        "name": f"{s1}{s2}相冲"
                    })
            
            # Control (Ke) - General Elemental Control
            from ..utils.data import STEM_ELEMENTS, DESTRUCTION_CYCLE
            e1 = STEM_ELEMENTS[s1][0]
            e2 = STEM_ELEMENTS[s2][0]
            
            is_clash = any((s1==x and s2==y) or (s1==y and s2==x) for x, y in BaZiRules.STEM_CLASHES)
            if not is_clash:
                if DESTRUCTION_CYCLE.get(e1) == e2:
                    patterns["controls"].append({
                            "stems": [s1, s2],
                            "pillars": [p1, p2],
                            "name": f"{s1}克{s2}"
                    })
                elif DESTRUCTION_CYCLE.get(e2) == e1:
                        patterns["controls"].append({
                            "stems": [s2, s1],
                            "pillars": [p2, p1],
                            "name": f"{s2}克{s1}"
                        })

        return patterns

    @staticmethod
    def check_hidden_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Check for Hidden/Dark/Arch patterns."""
        branches = {k: v[1] for k, v in pillars.items()}
        stems = [v[0] for v in pillars.values()] # All stems for Arch check
        patterns = {
            "arch_combinations": [], # 拱局
            "dark_combinations": [], # 暗合
        }
        
        pillar_names = ["year", "month", "day", "hour"]
        
        # Arch Combinations (Gong)
        for i in range(len(pillar_names)):
            for j in range(i + 1, len(pillar_names)):
                p1, p2 = pillar_names[i], pillar_names[j]
                b1, b2 = branches[p1], branches[p2]
                
                for start, end, arched, element, related_stem in BaZiRules.ARCH_COMBINATIONS:
                    if (b1 == start and b2 == end) or (b1 == end and b2 == start):
                        # Found an arch pair
                        entry = {
                            "branches": [b1, b2],
                            "pillars": [p1, p2],
                            "arched": arched,
                            "type": f"拱{element}",
                            "is_enhanced": False
                        }
                        # Check if related stem is present (Dark Three Meeting)
                        if related_stem in stems:
                            entry["is_enhanced"] = True
                            entry["name"] = f"{b1}{b2}见{related_stem}暗拱三会{element}局"
                        else:
                            entry["name"] = f"{b1}{b2}拱{arched}"
                        
                        patterns["arch_combinations"].append(entry)

        # Dark Combinations (An He)
        for i in range(len(pillar_names)):
            for j in range(i + 1, len(pillar_names)):
                p1, p2 = pillar_names[i], pillar_names[j]
                b1, b2 = branches[p1], branches[p2]
                
                for db1, db2 in BaZiRules.DARK_COMBINATIONS:
                    if (b1 == db1 and b2 == db2) or (b1 == db2 and b2 == db1):
                        patterns["dark_combinations"].append({
                            "branches": [b1, b2],
                            "pillars": [p1, p2],
                            "name": f"{b1}{b2}暗合"
                        })
        
        return patterns

    @staticmethod
    def check_pillar_patterns(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Check for single pillar patterns (Gaito, Jiejiao, Fu, Zai)."""
        patterns = {
            "gai_tou": [],   # Stem controls Branch (盖头)
            "jie_jiao": [],  # Branch controls Stem (截脚)
            "fu": [],        # Stem generates Branch (覆 - 天生均)
            "zai": [],       # Branch generates Stem (载 - 地生天)
            "tong": [],      # Same Element (比和 - 天地同气)
        }
        
        from ..utils.data import STEM_ELEMENTS, BRANCH_ELEMENTS, DESTRUCTION_CYCLE, GENERATION_CYCLE
        
        for name, (stem, branch) in pillars.items():
            stem_elem = STEM_ELEMENTS[stem][0]
            branch_elem = BRANCH_ELEMENTS[branch][0]
            
            # Gaito: Stem controls Branch (盖头)
            if DESTRUCTION_CYCLE.get(stem_elem) == branch_elem:
                patterns["gai_tou"].append({
                    "pillar": name,
                    "stem": stem,
                    "branch": branch,
                    "name": f"{stem}{branch}盖头"
                })
            
            # Jie Jiao: Branch controls Stem (截脚)
            elif DESTRUCTION_CYCLE.get(branch_elem) == stem_elem:
                patterns["jie_jiao"].append({
                    "pillar": name,
                    "stem": stem,
                    "branch": branch,
                    "name": f"{stem}{branch}截脚"
                })
                
            # Fu: Stem generates Branch (覆 - 天覆地载之覆)
            elif GENERATION_CYCLE.get(stem_elem) == branch_elem:
                patterns["fu"].append({
                    "pillar": name,
                    "stem": stem,
                    "branch": branch,
                    "name": f"{stem}{branch}相生(覆)"
                })

            # Zai: Branch generates Stem (载 - 天覆地载之载)
            elif GENERATION_CYCLE.get(branch_elem) == stem_elem:
                patterns["zai"].append({
                    "pillar": name,
                    "stem": stem,
                    "branch": branch,
                    "name": f"{stem}{branch}相生(载)"
                })
                
            # Tong: Same Element (比和)
            elif stem_elem == branch_elem:
                patterns["tong"].append({
                    "pillar": name,
                    "stem": stem,
                    "branch": branch,
                    "name": f"{stem}{branch}比和"
                })
                
        return patterns

    @staticmethod
    def check_fu_yin_fan_yin(
        pillars: Dict[str, Tuple[str, str]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Check for Fu Yin (Identical) and Fan Yin (Clashing) Pillars."""
        patterns = {
            "fu_yin": [],  # 伏吟 (Same Pillar)
            "fan_yin": [], # 反吟 (Clashing Pillar: Stem Clash + Branch Clash)
        }
        
        pillar_names = ["year", "month", "day", "hour"]
        stems = {k: v[0] for k, v in pillars.items()}
        branches = {k: v[1] for k, v in pillars.items()}
        
        # Check all pairs
        for i in range(len(pillar_names)):
            for j in range(i + 1, len(pillar_names)):
                p1, p2 = pillar_names[i], pillar_names[j]
                
                # Fu Yin (伏吟): Both Stem and Branch are identical
                if stems[p1] == stems[p2] and branches[p1] == branches[p2]:
                    patterns["fu_yin"].append({
                        "pillars": [p1, p2],
                        "pillar_content": f"{stems[p1]}{branches[p1]}",
                        "name": f"{p1}{p2}伏吟"
                    })
                    
                # Fan Yin (反吟): Stem Clashes AND Branch Clashes
                # Stem Clash check
                s1, s2 = stems[p1], stems[p2]
                is_stem_clash = any((s1==x and s2==y) or (s1==y and s2==x) for x, y in BaZiRules.STEM_CLASHES)
                
                # Branch Clash check
                b1, b2 = branches[p1], branches[p2]
                is_branch_clash = any((b1==x and b2==y) or (b1==y and b2==x) for x, y in BaZiRules.SIX_CLASH)
                
                if is_stem_clash and is_branch_clash:
                    patterns["fan_yin"].append({
                        "pillars": [p1, p2],
                        "pillar_content": [f"{stems[p1]}{branches[p1]}", f"{stems[p2]}{branches[p2]}"],
                        "name": f"{p1}{p2}反吟"
                    })
                    
        return patterns

    @staticmethod
    def analyze_special_patterns(
        pillars: Dict[str, Tuple[str, str]], birth_hour: int = None
    ) -> Dict[str, Any]:
        """Analyze special patterns in the BaZi chart."""
        stems = [stem for stem, _ in pillars.values()]
        branches = [branch for _, branch in pillars.values()]

        patterns = {}

        # Check for special day pillar patterns
        day_stem, day_branch = pillars["day"]

        # 日贵格 (Noble Day Pattern)
        # 正确的日贵格只有四日：丁酉、丁亥、癸巳、癸卯
        day_pillar = f"{day_stem}{day_branch}"
        noble_days = ["丁酉", "丁亥", "癸巳", "癸卯"]

        if day_pillar in noble_days:
            patterns["noble_day"] = True

            # 添加昼夜区分
            if birth_hour is not None:
                # 昼贵：癸卯、丁亥（白天6-18时）
                # 夜贵：癸巳、丁酉（夜晚18-6时）
                is_daytime = 6 <= birth_hour < 18

                if day_pillar in ["癸卯", "丁亥"] and is_daytime:
                    patterns["noble_day_type"] = "昼贵"
                elif day_pillar in ["癸巳", "丁酉"] and not is_daytime:
                    patterns["noble_day_type"] = "夜贵"
                else:
                    patterns["noble_day_type"] = "不合时"

        # 魁罡格 (Kui Gang Pattern)
        kui_gang_days = ["庚戌", "庚辰", "戊戌", "壬辰"]
        if f"{day_stem}{day_branch}" in kui_gang_days:
            patterns["kui_gang"] = True

        # Check stem patterns
        # 四同 (Four Same)
        for stem in HEAVENLY_STEMS:
            if stems.count(stem) == 4:
                patterns["four_same_stems"] = stem

        for branch in EARTHLY_BRANCHES:
            if branches.count(branch) == 4:
                patterns["four_same_branches"] = branch

        # 天干一气 (Heavenly Stems Unity)
        if len(set(stems)) == 1:
            patterns["stem_unity"] = stems[0]

        # 地支一气 (Earthly Branches Unity)
        if len(set(branches)) == 1:
            patterns["branch_unity"] = branches[0]

        # Check for Four Horses, Cardinals, Treasuries
        # 1. Analyze individual branch attributes (per pillar)
        branch_attributes = {}
        for pillar_name, (_, branch) in pillars.items():
            attr_data = {"branch": branch}
            
            if branch in BaZiRules.FOUR_HORSES:
                attr_data["type"] = "驿马" # 生地
            elif branch in BaZiRules.FOUR_CARDINALS:
                attr_data["type"] = "四正" # 旺地
            elif branch in BaZiRules.FOUR_TREASURIES:
                attr_data["type"] = "四库" # 墓库
            else:
                attr_data["type"] = "未知"
            
            branch_attributes[pillar_name] = attr_data

        patterns["branch_attributes"] = branch_attributes

        # 2. Count occurrences and check for patterns
        horses_count = sum(1 for b in branches if b in BaZiRules.FOUR_HORSES)
        cardinals_count = sum(1 for b in branches if b in BaZiRules.FOUR_CARDINALS)
        treasuries_count = sum(1 for b in branches if b in BaZiRules.FOUR_TREASURIES)

        # Store counts
        patterns["counts"] = {
            "horses": horses_count,
            "cardinals": cardinals_count,
            "treasuries": treasuries_count
        }

        # Initialize defaults
        patterns["four_horses_complete"] = False
        patterns["many_horses"] = False
        patterns["all_horses"] = False
        
        patterns["four_cardinals_complete"] = False
        patterns["many_cardinals"] = False
        patterns["all_cardinals"] = False
        
        patterns["four_treasuries_complete"] = False
        patterns["many_treasuries"] = False
        patterns["all_treasuries"] = False

        # Check for complete sets (all 4 unique branches present)
        unique_branches = set(branches)
        if all(b in unique_branches for b in BaZiRules.FOUR_HORSES):
            patterns["four_horses_complete"] = True # 四位纯全 (四驿马)
        elif horses_count >= 3:
            patterns["many_horses"] = True
 
        if all(b in unique_branches for b in BaZiRules.FOUR_CARDINALS):
            patterns["four_cardinals_complete"] = True # 四位纯全 (四正)
        elif cardinals_count >= 3:
            patterns["many_cardinals"] = True
 
        if all(b in unique_branches for b in BaZiRules.FOUR_TREASURIES):
            patterns["four_treasuries_complete"] = True # 四位纯全 (四库)
        elif treasuries_count >= 3:
            patterns["many_treasuries"] = True
             
        # Check if all branches belong to one group (Pure)
        if horses_count == 4:
            patterns["all_horses"] = True # 遍野桃花/四马之地
        if cardinals_count == 4:
            patterns["all_cardinals"] = True # 四败/四正
        if treasuries_count == 4:
            patterns["all_treasuries"] = True # 四库
 
        return patterns

    @staticmethod
    def calculate_compatibility_score(
        pillars1: Dict[str, Tuple[str, str]], pillars2: Dict[str, Tuple[str, str]]
    ) -> Dict[str, Any]:
        """Calculate basic compatibility score between two BaZi charts."""
        compatibility = {
            "harmony_score": 0,
            "clash_score": 0,
            "overall_score": 0,
            "details": [],
        }

        # Extract all branches from both charts
        branches1 = [branch for _, branch in pillars1.values()]
        branches2 = [branch for _, branch in pillars2.values()]

        # Check harmony between charts
        for b1 in branches1:
            for b2 in branches2:
                # Check six harmony
                for harmony_pair in BaZiRules.SIX_HARMONY:
                    if (b1, b2) in [harmony_pair, harmony_pair[::-1]]:
                        compatibility["harmony_score"] += 2
                        compatibility["details"].append(f"{b1}与{b2}六合")

                # Check six clash
                for clash_pair in BaZiRules.SIX_CLASH:
                    if (b1, b2) in [clash_pair, clash_pair[::-1]]:
                        compatibility["clash_score"] += 2
                        compatibility["details"].append(f"{b1}与{b2}六冲")

        # Check day pillar compatibility (most important)
        day_stem1, day_branch1 = pillars1["day"]
        day_stem2, day_branch2 = pillars2["day"]

        # Day branch harmony/clash has higher weight
        for harmony_pair in BaZiRules.SIX_HARMONY:
            if (day_branch1, day_branch2) in [harmony_pair, harmony_pair[::-1]]:
                compatibility["harmony_score"] += 5
                compatibility["details"].append(
                    f"日支{day_branch1}与{day_branch2}六合(重要)"
                )

        for clash_pair in BaZiRules.SIX_CLASH:
            if (day_branch1, day_branch2) in [clash_pair, clash_pair[::-1]]:
                compatibility["clash_score"] += 5
                compatibility["details"].append(
                    f"日支{day_branch1}与{day_branch2}六冲(重要)"
                )

        # Calculate overall score
        compatibility["overall_score"] = (
            compatibility["harmony_score"] - compatibility["clash_score"]
        )

        # Determine compatibility level
        if compatibility["overall_score"] >= 8:
            compatibility["level"] = "非常匹配"
        elif compatibility["overall_score"] >= 4:
            compatibility["level"] = "比较匹配"
        elif compatibility["overall_score"] >= 0:
            compatibility["level"] = "一般匹配"
        elif compatibility["overall_score"] >= -4:
            compatibility["level"] = "需要磨合"
        else:
            compatibility["level"] = "不太匹配"

        return compatibility

    @staticmethod
    def get_life_analysis(
        pillars: Dict[str, Tuple[str, str]], element_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Provide life analysis based on BaZi patterns."""
        analysis = {
            "personality": [],
            "career": [],
            "health": [],
            "relationships": [],
            "fortune": [],
        }

        day_stem = pillars["day"][0]
        day_branch = pillars["day"][1]
        strength_level = element_analysis["day_master"]["strength_level"]

        # Basic personality analysis based on day stem
        personality_map = {
            "甲": "积极主动，有领导能力，但有时过于刚强",
            "乙": "温和柔韧，适应力强，但有时优柔寡断",
            "丙": "热情开朗，有感染力，但有时过于冲动",
            "丁": "细致敏感，有创造力，但有时过于敏感",
            "戊": "稳重踏实，有责任心，但有时过于固执",
            "己": "温和谦逊，有包容心，但有时缺乏主见",
            "庚": "果断坚定，有执行力，但有时过于严厉",
            "辛": "精致细腻，有品味，但有时过于挑剔",
            "壬": "灵活变通，有智慧，但有时过于多变",
            "癸": "温柔体贴，有直觉力，但有时过于被动",
        }

        if day_stem in personality_map:
            analysis["personality"].append(personality_map[day_stem])

        # Add strength analysis
        if strength_level == "强":
            analysis["personality"].append("个性较强，自信心足，但需要注意不要过于自我")
            analysis["career"].append("适合领导管理类工作，创业运佳")
        elif strength_level == "弱":
            analysis["personality"].append("性格较为温和，需要他人扶持")
            analysis["career"].append("适合团队合作，技术专业类工作")
        else:
            analysis["personality"].append("性格较为平衡，能够适应各种环境")

        # Fortune analysis based on favorable elements
        favorable_elements = element_analysis.get("favorable_elements", [])
        if favorable_elements:
            analysis["fortune"].append(f"有利五行: {', '.join(favorable_elements)}")

        return analysis
