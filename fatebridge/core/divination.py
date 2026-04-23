"""
I Ching and Mei Hua Yi Shu helper utilities.

This module adds lightweight divination support around trigram/hexagram
composition so FateBridge can expose contextual gua information without
depending on an external runtime.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..utils.data import EARTHLY_BRANCHES
from .gua_meanings import (
    HEXAGRAM_INTERPRETATIONS,
    get_hexagram_meaning,
    get_trigram_meaning,
)


BAGUA_BY_NAME: Dict[str, Dict[str, object]] = {
    "乾": {"name": "乾", "nature": "天", "element": "金", "lines": [1, 1, 1], "symbol": "☰", "keywords": "刚健、开创、天道"},
    "兑": {"name": "兑", "nature": "泽", "element": "金", "lines": [1, 1, 0], "symbol": "☱", "keywords": "喜悦、交流、润泽"},
    "离": {"name": "离", "nature": "火", "element": "火", "lines": [1, 0, 1], "symbol": "☲", "keywords": "光明、表达、洞察"},
    "震": {"name": "震", "nature": "雷", "element": "木", "lines": [1, 0, 0], "symbol": "☳", "keywords": "发动、突破、惊醒"},
    "巽": {"name": "巽", "nature": "风", "element": "木", "lines": [0, 1, 1], "symbol": "☴", "keywords": "渗透、谋划、柔入"},
    "坎": {"name": "坎", "nature": "水", "element": "水", "lines": [0, 1, 0], "symbol": "☵", "keywords": "流动、隐忧、险中求通"},
    "艮": {"name": "艮", "nature": "山", "element": "土", "lines": [0, 0, 1], "symbol": "☶", "keywords": "止守、边界、收束"},
    "坤": {"name": "坤", "nature": "地", "element": "土", "lines": [0, 0, 0], "symbol": "☷", "keywords": "承载、包容、顺势"},
}

BAGUA_BY_NUMBER = {
    1: "乾",
    2: "兑",
    3: "离",
    4: "震",
    5: "巽",
    6: "坎",
    7: "艮",
    8: "坤",
}

HEXAGRAM_NAMES: Dict[Tuple[str, str], str] = {
    ("乾", "乾"): "乾为天",
    ("乾", "兑"): "天泽履",
    ("乾", "离"): "天火同人",
    ("乾", "震"): "天雷无妄",
    ("乾", "巽"): "天风姤",
    ("乾", "坎"): "天水讼",
    ("乾", "艮"): "天山遁",
    ("乾", "坤"): "天地否",
    ("兑", "乾"): "泽天夬",
    ("兑", "兑"): "兑为泽",
    ("兑", "离"): "泽火革",
    ("兑", "震"): "泽雷随",
    ("兑", "巽"): "泽风大过",
    ("兑", "坎"): "泽水困",
    ("兑", "艮"): "泽山咸",
    ("兑", "坤"): "泽地萃",
    ("离", "乾"): "火天大有",
    ("离", "兑"): "火泽睽",
    ("离", "离"): "离为火",
    ("离", "震"): "火雷噬嗑",
    ("离", "巽"): "火风鼎",
    ("离", "坎"): "火水未济",
    ("离", "艮"): "火山旅",
    ("离", "坤"): "火地晋",
    ("震", "乾"): "雷天大壮",
    ("震", "兑"): "雷泽归妹",
    ("震", "离"): "雷火丰",
    ("震", "震"): "震为雷",
    ("震", "巽"): "雷风恒",
    ("震", "坎"): "雷水解",
    ("震", "艮"): "雷山小过",
    ("震", "坤"): "雷地豫",
    ("巽", "乾"): "风天小畜",
    ("巽", "兑"): "风泽中孚",
    ("巽", "离"): "风火家人",
    ("巽", "震"): "风雷益",
    ("巽", "巽"): "巽为风",
    ("巽", "坎"): "风水涣",
    ("巽", "艮"): "风山渐",
    ("巽", "坤"): "风地观",
    ("坎", "乾"): "水天需",
    ("坎", "兑"): "水泽节",
    ("坎", "离"): "水火既济",
    ("坎", "震"): "水雷屯",
    ("坎", "巽"): "水风井",
    ("坎", "坎"): "坎为水",
    ("坎", "艮"): "水山蹇",
    ("坎", "坤"): "水地比",
    ("艮", "乾"): "山天大畜",
    ("艮", "兑"): "山泽损",
    ("艮", "离"): "山火贲",
    ("艮", "震"): "山雷颐",
    ("艮", "巽"): "山风蛊",
    ("艮", "坎"): "山水蒙",
    ("艮", "艮"): "艮为山",
    ("艮", "坤"): "山地剥",
    ("坤", "乾"): "地天泰",
    ("坤", "兑"): "地泽临",
    ("坤", "离"): "地火明夷",
    ("坤", "震"): "地雷复",
    ("坤", "巽"): "地风升",
    ("坤", "坎"): "地水师",
    ("坤", "艮"): "地山谦",
    ("坤", "坤"): "坤为地",
}

ELEMENT_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

QUESTION_DOMAIN_RULES = {
    "career": {
        "label": "事业/项目",
        "focus": "资源调度、节奏推进与结果落地",
        "keywords": (
            "事业",
            "工作",
            "项目",
            "推进",
            "合作",
            "职位",
            "升职",
            "创业",
            "客户",
            "career",
            "project",
            "work",
        ),
    },
    "relationship": {
        "label": "感情/关系",
        "focus": "双方态度、沟通温度与后续走向",
        "keywords": (
            "感情",
            "关系",
            "婚姻",
            "恋爱",
            "相处",
            "复合",
            "桃花",
            "relationship",
            "love",
        ),
    },
    "wealth": {
        "label": "财务/经营",
        "focus": "现金流、投入回报与风险边界",
        "keywords": (
            "财",
            "收入",
            "投资",
            "收益",
            "订单",
            "生意",
            "经营",
            "wealth",
            "money",
            "business",
        ),
    },
    "study": {
        "label": "学业/考试",
        "focus": "准备质量、临场状态与结果兑现",
        "keywords": (
            "学业",
            "考试",
            "申请",
            "论文",
            "面试",
            "留学",
            "study",
            "exam",
        ),
    },
    "health": {
        "label": "健康/恢复",
        "focus": "身体负担、恢复节奏与风险防控",
        "keywords": (
            "健康",
            "身体",
            "病",
            "恢复",
            "睡眠",
            "手术",
            "health",
        ),
    },
    "travel": {
        "label": "出行/迁动",
        "focus": "路径变化、外部阻力与安全边界",
        "keywords": (
            "出行",
            "旅行",
            "出差",
            "搬家",
            "迁移",
            "通勤",
            "travel",
            "move",
        ),
    },
}

BODY_USE_INTERPRETATIONS = {
    "体用比和": "主体与外部条件较为同频，推进阻力相对较小。",
    "体生用": "事情更依赖自身先投入与付出，先给出去，后见回响。",
    "体克用": "更适合主动掌控和定节奏，但会消耗心力，不宜贪多。",
    "用生体": "外部资源会反过来扶助自身，宜借势借人借平台。",
    "用克体": "客观环境对主体形成压制，宜先化解阻力再推进。",
    "体用关系未明": "主客力量暂不鲜明，可先观察一轮再下判断。",
}

MOVING_LINE_PHASES = {
    1: {"stage": "起念与启动", "meaning": "事情多落在开头、动机或第一步动作上"},
    2: {"stage": "内部联系与配合", "meaning": "事情重点在资源协同、内部承接与近身关系"},
    3: {"stage": "进退临界", "meaning": "事情已到卡口，最怕躁进或停滞不决"},
    4: {"stage": "外部执行", "meaning": "事情开始向外展开，需处理外部人事与执行面"},
    5: {"stage": "核心结果位", "meaning": "事情已触及主轴或结果位，成败关键最集中"},
    6: {"stage": "收尾与反思", "meaning": "事情来到尾段或过强之处，宜收束而非再加码"},
}

MOVING_LINE_ORACLE_DETAILS = {
    1: {
        "position": "初爻",
        "title": "发端位",
        "focus": "起势、试探与基础",
        "judgement": "事在初起，重在把第一步踩稳，小动可取，妄进易失序。",
        "favorable": "试探、起步、先立基线",
        "caution": "起手过满、仓促定局",
        "timing": "先小后大",
    },
    2: {
        "position": "二爻",
        "title": "承接位",
        "focus": "内部协同、承接与近身关系",
        "judgement": "重心在近身协同与内部承接，关系顺则事顺，关系乱则事缓。",
        "favorable": "对齐、承接、稳住关键配合",
        "caution": "各做各的、近身失配",
        "timing": "先内后外",
    },
    3: {
        "position": "三爻",
        "title": "转折位",
        "focus": "门槛压力、进退选择与节奏校正",
        "judgement": "事情到了进退两难之口，最忌情绪上头，宜停一下再定打法。",
        "favorable": "减速、复盘、换挡",
        "caution": "硬顶、赌气、边乱边冲",
        "timing": "先稳后进",
    },
    4: {
        "position": "四爻",
        "title": "外应位",
        "focus": "对外执行、接口与外部反馈",
        "judgement": "局面开始真正进入外部执行层，方向对了就要抓落实。",
        "favorable": "执行、落地、处理外部接口",
        "caution": "纸上推进、对外失控",
        "timing": "由内转外",
    },
    5: {
        "position": "五爻",
        "title": "主位",
        "focus": "核心结果、主轴资源与拍板权",
        "judgement": "已到主轴结果位，宜抓住核心人、核心事、核心窗口一击定势。",
        "favorable": "聚焦主轴、拍板、拿结果",
        "caution": "贪多分心、权重失衡",
        "timing": "关键窗口",
    },
    6: {
        "position": "上爻",
        "title": "收束位",
        "focus": "收尾、过满与结构回看",
        "judgement": "事已近尾或势已过满，宜收束定界，过推反伤。",
        "favorable": "收尾、止盈、回看结构",
        "caution": "临门再加码、强撑过头",
        "timing": "宜收不宜放",
    },
}

DOMAIN_LINE_ADJUSTMENTS = {
    "career": "在事业/项目上，更适合把角色、边界、里程碑先钉牢。",
    "relationship": "在感情/关系上，更应先看回应与温度，再决定推进深浅。",
    "wealth": "在财务/经营上，更要先控投入节奏，再看回收与扩张。",
    "study": "在学业/考试上，先稳准备质量，再谈临场发挥。",
    "health": "在健康/恢复上，以节律、恢复度和风险管理为先。",
    "travel": "在出行/迁动上，优先确认路径、安全与变动边界。",
    "general": "先把当前所在步骤看清，再决定发力还是收束。",
}

BODY_USE_LINE_ADJUSTMENTS = {
    "体用比和": "主客力量相对同频，宜顺势推进，不必刻意造势。",
    "体生用": "主体付出会比较多，宜先控投入强度，避免一开始就透支。",
    "体克用": "主体掌控力较强，宜主动拿节奏，但别把推动变成硬压。",
    "用生体": "外援更能扶身，宜借平台、借关系、借时机来放大成效。",
    "用克体": "环境压力偏大，宜先卸阻、减压，再求推进。",
    "体用关系未明": "主客轻重未定，宜多观察一轮，不急着下重手。",
}


def _enrich_trigram(trigram: Dict[str, object]) -> Dict[str, object]:
    enriched = dict(trigram)
    enriched.update(get_trigram_meaning(trigram["name"]))
    return enriched


def _enrich_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    enriched = dict(hexagram)
    detail = get_hexagram_meaning(enriched["name"])
    enriched.update(detail)
    if "summary" not in enriched:
        enriched["summary"] = (
            f"{enriched['name']}：{detail.get('theme', '卦义待补充')}。"
            f"{detail.get('judgement', detail.get('guidance', ''))}"
        ).strip()
    return enriched


def _build_oracle_payload(hexagram: Dict[str, object]) -> Dict[str, str]:
    return {
        "name": hexagram["name"],
        "theme": str(hexagram.get("theme", "")),
        "judgement": str(hexagram.get("judgement", "")),
        "image": str(hexagram.get("image", "")),
        "favorable": str(hexagram.get("favorable", "")),
        "caution": str(hexagram.get("caution", "")),
    }


def build_moving_line_oracle(
    hexagram: Dict[str, object],
    moving_line: int,
    domain: Dict[str, str],
) -> Dict[str, object]:
    detail = MOVING_LINE_ORACLE_DETAILS[moving_line]
    changed_hexagram = build_changed_hexagram(hexagram, moving_line)
    line_body_use = resolve_body_use(hexagram, moving_line)
    body_use_relation = line_body_use["body_use_relation"]
    domain_hint = DOMAIN_LINE_ADJUSTMENTS.get(
        domain["key"],
        DOMAIN_LINE_ADJUSTMENTS["general"],
    )
    body_use_hint = BODY_USE_LINE_ADJUSTMENTS.get(
        body_use_relation,
        BODY_USE_LINE_ADJUSTMENTS["体用关系未明"],
    )
    judgement = (
        f"在{hexagram['name']}中，{detail['position']}属{detail['title']}，"
        f"重点看{detail['focus']}。{detail['judgement']}"
    )
    transition = (
        f"此爻一动，局面多转向{changed_hexagram['name']}的{changed_hexagram['theme']}，"
        f"{changed_hexagram['judgement']}"
    )
    favorable = (
        f"{detail['favorable']}；并顺着本卦所宜{hexagram.get('favorable', '顺势推进')}"
    )
    caution = (
        f"{detail['caution']}；并防本卦所忌{hexagram.get('caution', '失衡冒进')}"
    )
    summary = (
        f"动{moving_line}爻居{detail['position']}，{judgement}{transition}"
        f"宜{favorable}，忌{caution}。"
        f"{domain_hint}{body_use_hint}"
    )
    return {
        "line": moving_line,
        "position": detail["position"],
        "title": detail["title"],
        "focus": detail["focus"],
        "judgement": judgement,
        "favorable": favorable,
        "caution": caution,
        "timing": detail["timing"],
        "moving_palace": line_body_use["moving_palace"],
        "body_use_relation": body_use_relation,
        "body_trigram": line_body_use["body_trigram"]["name"],
        "use_trigram": line_body_use["use_trigram"]["name"],
        "changed_hexagram": _build_oracle_payload(changed_hexagram),
        "domain_hint": domain_hint,
        "body_use_adjustment": body_use_hint,
        "transition": transition,
        "summary": summary,
    }


def build_line_oracles(
    hexagram: Dict[str, object],
    active_line: int,
    domain: Dict[str, str],
) -> List[Dict[str, object]]:
    line_oracles: List[Dict[str, object]] = []
    for line_number in range(1, 7):
        oracle = build_moving_line_oracle(
            hexagram=hexagram,
            moving_line=line_number,
            domain=domain,
        )
        oracle["is_active"] = line_number == active_line
        line_oracles.append(oracle)
    return line_oracles


def _bagua_from_lines(lines: List[int]) -> Dict[str, object]:
    target = ",".join(str(bit) for bit in lines)
    for item in BAGUA_BY_NAME.values():
        if ",".join(str(bit) for bit in item["lines"]) == target:
            return _enrich_trigram(item)
    return _enrich_trigram(BAGUA_BY_NAME["乾"])


def _bagua_from_number(number: int) -> Dict[str, object]:
    normalized = ((number - 1) % 8) + 1
    return _enrich_trigram(BAGUA_BY_NAME[BAGUA_BY_NUMBER[normalized]])


def build_hexagram(upper_name: str, lower_name: str) -> Dict[str, object]:
    upper = _enrich_trigram(BAGUA_BY_NAME[upper_name])
    lower = _enrich_trigram(BAGUA_BY_NAME[lower_name])
    lines = [*lower["lines"], *upper["lines"]]
    return _enrich_hexagram({
        "name": HEXAGRAM_NAMES.get((upper_name, lower_name), f"{upper['nature']}{lower['nature']}"),
        "upper": upper,
        "lower": lower,
        "lines": lines,
        "binary_code": "".join(str(bit) for bit in lines),
        "symbol": f"{upper['symbol']}{lower['symbol']}",
    })


def build_mutual_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    lines = hexagram["lines"]
    mutual_lines = [lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]]
    lower = _bagua_from_lines(mutual_lines[:3])
    upper = _bagua_from_lines(mutual_lines[3:])
    return build_hexagram(upper["name"], lower["name"])


def build_opposite_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    """错卦（旁通卦）: 每爻阴阳相反。"""
    opposite_lines = [0 if bit == 1 else 1 for bit in hexagram["lines"]]
    lower = _bagua_from_lines(opposite_lines[:3])
    upper = _bagua_from_lines(opposite_lines[3:])
    return build_hexagram(upper["name"], lower["name"])


def build_inverted_hexagram(hexagram: Dict[str, object]) -> Dict[str, object]:
    """综卦（倒颠卦）: 将原卦初爻与上爻、二爻与五爻、三爻与四爻对换 —
    即整卦 180° 倒读。当卦为"错自身"时（如乾/坤/颐/大过/中孚/小过/坎/离），
    返回的综卦即原卦。"""
    inverted_lines = list(reversed(hexagram["lines"]))
    lower = _bagua_from_lines(inverted_lines[:3])
    upper = _bagua_from_lines(inverted_lines[3:])
    return build_hexagram(upper["name"], lower["name"])


def build_changed_hexagram(hexagram: Dict[str, object], moving_line: int) -> Dict[str, object]:
    normalized_line = 6 if moving_line % 6 == 0 else moving_line % 6
    changed_lines = list(hexagram["lines"])
    changed_lines[normalized_line - 1] = 0 if changed_lines[normalized_line - 1] == 1 else 1
    lower = _bagua_from_lines(changed_lines[:3])
    upper = _bagua_from_lines(changed_lines[3:])
    changed = build_hexagram(upper["name"], lower["name"])
    changed["moving_line"] = normalized_line
    return changed


def relationship_by_element(left_element: str, right_element: str) -> str:
    if left_element == right_element:
        return "同气相应"
    if ELEMENT_GENERATES[left_element] == right_element:
        return "上生下"
    if ELEMENT_CONTROLS[left_element] == right_element:
        return "上制下"
    if ELEMENT_GENERATES[right_element] == left_element:
        return "下生上"
    if ELEMENT_CONTROLS[right_element] == left_element:
        return "下制上"
    return "关系未明"


def relationship_by_role(body_element: str, use_element: str) -> str:
    if body_element == use_element:
        return "体用比和"
    if ELEMENT_GENERATES[body_element] == use_element:
        return "体生用"
    if ELEMENT_CONTROLS[body_element] == use_element:
        return "体克用"
    if ELEMENT_GENERATES[use_element] == body_element:
        return "用生体"
    if ELEMENT_CONTROLS[use_element] == body_element:
        return "用克体"
    return "体用关系未明"


def detect_question_domain(question: str) -> Dict[str, str]:
    query = (question or "").strip()
    if not query:
        return {
            "key": "general",
            "label": "综合问事",
            "focus": "整体趋势、主客力量与后续走向",
        }

    lowered = query.casefold()
    for key, info in QUESTION_DOMAIN_RULES.items():
        if any(keyword in query or keyword in lowered for keyword in info["keywords"]):
            return {
                "key": key,
                "label": info["label"],
                "focus": info["focus"],
            }

    return {
        "key": "general",
        "label": "综合问事",
        "focus": "整体趋势、主客力量与后续走向",
    }


def resolve_body_use(
    hexagram: Dict[str, object], moving_line: int
) -> Dict[str, object]:
    normalized_line = 6 if moving_line % 6 == 0 else moving_line % 6
    moving_palace = "下卦" if normalized_line <= 3 else "上卦"
    if moving_palace == "下卦":
        body = hexagram["upper"]
        use = hexagram["lower"]
    else:
        body = hexagram["lower"]
        use = hexagram["upper"]

    relation = relationship_by_role(body["element"], use["element"])
    return {
        "moving_palace": moving_palace,
        "body_trigram": body,
        "use_trigram": use,
        "body_use_relation": relation,
        "body_use_summary": (
            f"动爻落{moving_palace}，体卦{body['name']}、用卦{use['name']}，"
            f"五行关系为{relation}。"
        ),
    }


def build_meihua_interpretation(
    meihua: Dict[str, object], question: str = ""
) -> Dict[str, object]:
    base = meihua["base_hexagram"]
    changed = meihua["changed_hexagram"]
    mutual = meihua["mutual_hexagram"]
    opposite = meihua["opposite_hexagram"]
    moving_line = meihua["seed"]["moving_line"]
    domain = detect_question_domain(question)
    phase = MOVING_LINE_PHASES[moving_line]
    line_oracles = build_line_oracles(
        hexagram=base,
        active_line=moving_line,
        domain=domain,
    )
    moving_line_oracle = next(
        oracle for oracle in line_oracles if oracle["is_active"]
    )
    body_use_relation = moving_line_oracle["body_use_relation"]
    body_use_detail = BODY_USE_INTERPRETATIONS.get(
        body_use_relation, BODY_USE_INTERPRETATIONS["体用关系未明"]
    )

    question_reading = (
        f"若问{domain['label']}，重点看{domain['focus']}。"
        if domain["key"] != "general"
        else f"此卦宜先看{domain['focus']}。"
    )
    base_reading = (
        f"本卦{base['name']}主{base['theme']}，{base['judgement']}"
        f"{base['guidance']}"
    )
    changed_reading = (
        f"变卦{changed['name']}主{changed['theme']}，后续多转向{changed['judgement']}"
        f"{changed['guidance']}"
    )
    mutual_reading = (
        f"互卦{mutual['name']}提示内在牵动在{mutual['theme']}，"
        f"{mutual['judgement']}{mutual['guidance']}"
    )
    opposite_reading = (
        f"综卦{opposite['name']}提醒反面镜像在{opposite['theme']}，"
        f"{opposite['judgement']}{opposite['guidance']}"
    )
    body_use_reading = f"{meihua['body_use_summary']}{body_use_detail}"
    phase_reading = (
        f"动{moving_line}爻对应{phase['stage']}，{phase['meaning']}。"
        f"{moving_line_oracle['summary']}"
    )
    action_hint = (
        f"可为之处在于{base.get('favorable', '顺势推进')}，"
        f"同时动爻位更利于{moving_line_oracle['favorable']}，"
        f"并逐步过渡到{changed.get('favorable', '稳步成事')}。"
    )
    risk_hint = (
        f"需防{base.get('caution', '失衡冒进')}，"
        f"动爻位最忌{moving_line_oracle['caution']}，"
        f"并留意反面镜像里的{opposite.get('caution', '内外失序')}。"
    )

    outline = [
        question_reading,
        base_reading,
        changed_reading,
        body_use_reading,
        phase_reading,
        mutual_reading,
        opposite_reading,
    ]

    comprehensive = (
        f"{question_reading}"
        f"本卦{base['name']}示{base['theme']}，"
        f"变卦{changed['name']}示{changed['theme']}；"
        f"{body_use_detail}"
        f"当前更应把握{phase['stage']}这一步，"
        f"{moving_line_oracle['judgement']}"
        f"宜{base.get('favorable', '顺势推进')}，"
        f"忌{base.get('caution', '失衡冒进')}。"
    )

    return {
        "question_domain": domain,
        "moving_line_phase": {
            "line": moving_line,
            "stage": phase["stage"],
            "meaning": phase["meaning"],
        },
        "line_oracles": line_oracles,
        "moving_line_oracle": moving_line_oracle,
        "base_reading": base_reading,
        "changed_reading": changed_reading,
        "mutual_reading": mutual_reading,
        "opposite_reading": opposite_reading,
        "body_use_reading": body_use_reading,
        "base_oracle": _build_oracle_payload(base),
        "changed_oracle": _build_oracle_payload(changed),
        "mutual_oracle": _build_oracle_payload(mutual),
        "opposite_oracle": _build_oracle_payload(opposite),
        "action_hint": action_hint,
        "risk_hint": risk_hint,
        "judgement_outline": outline,
        "comprehensive_judgement": comprehensive,
    }


def lookup_hexagram_by_code(code: str) -> Dict[str, object]:
    normalized = "".join(ch for ch in (code or "") if ch in {"0", "1"})
    if len(normalized) != 6:
        raise ValueError("卦码必须是 6 位 0/1 字符串，例如 111111。")
    lower = _bagua_from_lines([int(bit) for bit in normalized[:3]])
    upper = _bagua_from_lines([int(bit) for bit in normalized[3:]])
    hexagram = build_hexagram(upper["name"], lower["name"])
    hexagram["code"] = normalized
    hexagram["summary"] = (
        f"{hexagram['name']}：{hexagram.get('theme', '卦意聚焦待补充')}。"
        f"{hexagram.get('judgement', '')}"
        f"上卦{upper['name']}({upper['keywords']})，下卦{lower['name']}({lower['keywords']})。"
        f"{hexagram.get('guidance', '')}"
        f"宜{hexagram.get('favorable', '顺势推进')}，忌{hexagram.get('caution', '失衡冒进')}。"
    )
    return hexagram


def lookup_trigram_by_code(code: str) -> Dict[str, object]:
    normalized = "".join(ch for ch in (code or "") if ch in {"0", "1"})
    if len(normalized) != 3:
        raise ValueError("八卦码必须是 3 位 0/1 字符串，例如 111。")
    trigram = _bagua_from_lines([int(bit) for bit in normalized])
    trigram["code"] = normalized
    trigram["summary"] = (
        f"{trigram['name']}卦：{trigram.get('theme', trigram['keywords'])}。"
        f"{trigram.get('guidance', '')}"
        f"宜{trigram.get('favorable', '顺势而行')}，忌{trigram.get('caution', '避免失衡')}。"
    )
    return trigram


def lookup_hexagram_by_name(name: str) -> Dict[str, object]:
    normalized = (name or "").strip().replace("卦", "")
    candidates = {item.replace("卦", ""): item for item in HEXAGRAM_INTERPRETATIONS}
    if normalized not in candidates:
        raise ValueError(f"未识别的六十四卦名称：{name}")
    target = candidates[normalized]
    for (upper_name, lower_name), hexagram_name in HEXAGRAM_NAMES.items():
        if hexagram_name == target:
            hexagram = build_hexagram(upper_name, lower_name)
            hexagram["code"] = hexagram["binary_code"]
            hexagram["summary"] = (
                f"{hexagram['name']}：{hexagram.get('theme', '卦意聚焦待补充')}。"
                f"{hexagram.get('judgement', '')}"
                f"{hexagram.get('guidance', '')}"
                f"宜{hexagram.get('favorable', '顺势推进')}，忌{hexagram.get('caution', '失衡冒进')}。"
            )
            return hexagram
    raise ValueError(f"未能定位卦名对应的结构：{name}")


def lookup_trigram_by_name(name: str) -> Dict[str, object]:
    normalized = (name or "").strip().replace("卦", "")
    if normalized not in BAGUA_BY_NAME:
        raise ValueError(f"未识别的八卦名称：{name}")
    trigram = _enrich_trigram(BAGUA_BY_NAME[normalized])
    trigram["code"] = "".join(str(bit) for bit in trigram["lines"])
    trigram["summary"] = (
        f"{trigram['name']}卦：{trigram.get('theme', trigram['keywords'])}。"
        f"{trigram.get('guidance', '')}"
        f"宜{trigram.get('favorable', '顺势而行')}，忌{trigram.get('caution', '避免失衡')}。"
    )
    return trigram


def lookup_gua(query: str, lookup_mode: str = "auto") -> Dict[str, object]:
    normalized_mode = (lookup_mode or "auto").strip().lower()
    if normalized_mode not in {"auto", "hexagram", "trigram"}:
        raise ValueError("lookup_mode 必须是 auto、hexagram 或 trigram。")

    query_text = (query or "").strip()
    if not query_text:
        raise ValueError("query 不能为空。")

    if normalized_mode in {"auto", "hexagram"}:
        if len("".join(ch for ch in query_text if ch in {"0", "1"})) == 6:
            result = lookup_hexagram_by_code(query_text)
            result["lookup_type"] = "hexagram"
            result["matched_query"] = query_text
            return result
        if normalized_mode == "hexagram" or query_text.replace("卦", "") not in BAGUA_BY_NAME:
            try:
                result = lookup_hexagram_by_name(query_text)
                result["lookup_type"] = "hexagram"
                result["matched_query"] = query_text
                return result
            except ValueError:
                if normalized_mode == "hexagram":
                    raise

    if normalized_mode in {"auto", "trigram"}:
        if len("".join(ch for ch in query_text if ch in {"0", "1"})) == 3:
            result = lookup_trigram_by_code(query_text)
            result["lookup_type"] = "trigram"
            result["matched_query"] = query_text
            return result
        result = lookup_trigram_by_name(query_text)
        result["lookup_type"] = "trigram"
        result["matched_query"] = query_text
        return result

    raise ValueError(f"未找到可匹配的卦象：{query}")


def derive_meihua_hexagram(
    *,
    year_branch: str,
    lunar_month: int,
    lunar_day: int,
    hour_branch: str,
) -> Dict[str, object]:
    year_number = EARTHLY_BRANCHES.index(year_branch) + 1
    hour_number = EARTHLY_BRANCHES.index(hour_branch) + 1
    upper_number = (year_number + lunar_month + lunar_day) % 8 or 8
    lower_number = (year_number + lunar_month + lunar_day + hour_number) % 8 or 8
    moving_line = (year_number + lunar_month + lunar_day + hour_number) % 6 or 6

    upper = _bagua_from_number(upper_number)
    lower = _bagua_from_number(lower_number)
    base = build_hexagram(upper["name"], lower["name"])
    changed = build_changed_hexagram(base, moving_line)
    mutual = build_mutual_hexagram(base)
    opposite = build_opposite_hexagram(base)  # 错卦：每爻阴阳相反
    inverted = build_inverted_hexagram(base)  # 综卦：整卦倒颠
    relation = relationship_by_element(upper["element"], lower["element"])
    body_use = resolve_body_use(base, moving_line)

    return {
        "method": "meihua_time_seed",
        "seed": {
            "year_branch": year_branch,
            "lunar_month": lunar_month,
            "lunar_day": lunar_day,
            "hour_branch": hour_branch,
            "upper_number": upper_number,
            "lower_number": lower_number,
            "moving_line": moving_line,
        },
        "base_hexagram": base,
        "changed_hexagram": changed,
        "mutual_hexagram": mutual,
        # 历史字段保留以维持后向兼容；opposite_hexagram 指"错卦"语义。
        "opposite_hexagram": opposite,
        "cuo_hexagram": opposite,
        "zong_hexagram": inverted,
        "element_relation": relation,
        "moving_palace": body_use["moving_palace"],
        "body_trigram": body_use["body_trigram"],
        "use_trigram": body_use["use_trigram"],
        "body_use_relation": body_use["body_use_relation"],
        "body_use_summary": body_use["body_use_summary"],
        "summary": (
            f"梅花时卦得{base['name']}，动{moving_line}爻，之{changed['name']}；"
            f"上卦{upper['name']}、下卦{lower['name']}，五行关系为{relation}。"
        ),
    }
