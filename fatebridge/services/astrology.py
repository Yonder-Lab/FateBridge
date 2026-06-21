"""
FateBridge astrology services.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from fatebridge.core import guolao_moira
from fatebridge.core.astrology import (
    AstroBirthInfo,
    build_astro_birth_info,
    build_core_chart_payload,
    build_midpoint_payload,
    build_relative_payload,
)
from fatebridge.core.export_parser import parse_export_content
from fatebridge.services.structured_snapshot import render_structured_snapshot_text
from fatebridge.utils.helpers import handle_calculation_error

SUPPORTED_CHART_VARIANTS = {
    "chart",
    "chart13",
    "hellen_chart",
    "guolao_chart",
    "india_chart",
}

PLANET_LABELS_ZH: Dict[Any, str] = {
    "Sun": "太阳",
    "Moon": "月亮",
    "Mercury": "水星",
    "Venus": "金星",
    "Mars": "火星",
    "Jupiter": "木星",
    "Saturn": "土星",
    "Uranus": "天王星",
    "Neptune": "海王星",
    "Pluto": "冥王星",
    "North Node": "北交点",
}

ASPECT_LABELS_ZH: Dict[Any, str] = {
    "conjunction": "合相",
    "sextile": "六合",
    "square": "刑相",
    "trine": "拱相",
    "opposition": "冲相",
}

ELEMENT_LABELS_ZH = {
    "Fire": "火",
    "Earth": "土",
    "Air": "风",
    "Water": "水",
}

SIGN_LABELS_ZH = {
    "Aries": "白羊",
    "Taurus": "金牛",
    "Gemini": "双子",
    "Cancer": "巨蟹",
    "Leo": "狮子",
    "Virgo": "处女",
    "Libra": "天秤",
    "Scorpio": "天蝎",
    "Sagittarius": "射手",
    "Capricorn": "摩羯",
    "Aquarius": "水瓶",
    "Pisces": "双鱼",
}

MODALITY_LABELS_ZH = {
    "Cardinal": "基本",
    "Fixed": "固定",
    "Mutable": "变动",
}

CORE_CHART_EXPORT_TECHNIQUES = {
    "chart": "astrochart",
    "chart13": "astrochart",
    "hellen_chart": "astrochart_like",
    "india_chart": "indiachart",
    "guolao_chart": "guolao",
}

SIGN_INTERPRETATION = {
    "Aries": {
        "core": "主动开局、喜欢用直接行动证明自己",
        "emotion": "情绪反应快，越能立刻推进事情越安心",
        "persona": "给人果断、带头、不太拖泥带水的印象",
        "relationship": "相处时重视爽快、真实与行动回应",
        "growth": "学会在速度之外保留耐心与策略空间",
    },
    "Taurus": {
        "core": "重视稳定、质感与可持续累积",
        "emotion": "需要可预期的节奏和身体层面的安全感",
        "persona": "给人稳、慢热、抗压和讲究质感的印象",
        "relationship": "会用陪伴、资源与稳定投入表达在意",
        "growth": "在守成之外练习适度调整和试错",
    },
    "Gemini": {
        "core": "好奇、灵活，靠信息交换建立存在感",
        "emotion": "情绪需要被说出来、想清楚、聊明白",
        "persona": "给人机敏、会观察、反应快的印象",
        "relationship": "喜欢有来有往的沟通和脑力互动",
        "growth": "把分散兴趣收束成真正能沉淀的方向",
    },
    "Cancer": {
        "core": "重视归属、照顾与内在安全边界",
        "emotion": "情绪细腻，容易先感受气氛再决定行动",
        "persona": "给人温和、敏感、有保护欲的印象",
        "relationship": "会通过照料、记挂与情绪承接表达亲近",
        "growth": "在保护自己时也保留清晰表达需求的能力",
    },
    "Leo": {
        "core": "希望被看见，也愿意主动发光和承担",
        "emotion": "需要被尊重、被肯定，才能稳定输出热情",
        "persona": "给人有存在感、体面、愿意撑场面的印象",
        "relationship": "看重真诚欣赏、忠诚与明确的心意表达",
        "growth": "把自尊转化为稳定创作，而不是只靠外界回馈",
    },
    "Virgo": {
        "core": "靠辨析、修正和打磨细节建立秩序",
        "emotion": "情绪容易通过整理、复盘、改进来安放",
        "persona": "给人认真、克制、可靠且有标准的印象",
        "relationship": "会通过帮忙、照应细节和务实支持表达在乎",
        "growth": "把挑剔变成建设性判断，而不是过度消耗自己",
    },
    "Libra": {
        "core": "追求平衡、审美与关系中的恰当分寸",
        "emotion": "情绪常受关系气氛影响，需要和谐与对话",
        "persona": "给人有礼、讲究体面、会协调的印象",
        "relationship": "重视对等、好看、顺畅与互相体谅",
        "growth": "在顾及关系时别放掉自己的明确立场",
    },
    "Scorpio": {
        "core": "重视深度、真实和穿透表象的力量感",
        "emotion": "情绪浓度高，信任建立后才会真正敞开",
        "persona": "给人沉静、强烈、边界感重的印象",
        "relationship": "需要深度投入、忠诚与心理层面的链接",
        "growth": "把控制欲转化为洞察力和稳定承诺",
    },
    "Sagittarius": {
        "core": "靠探索、扩张和寻找意义感来确认方向",
        "emotion": "情绪需要空间、远景和更大的可能性",
        "persona": "给人开阔、直率、愿意尝试的印象",
        "relationship": "喜欢坦率、成长型、能一起看更远的关系",
        "growth": "把理想落到具体行动，避免只停留在热情",
    },
    "Capricorn": {
        "core": "重视结果、责任与长期结构的建立",
        "emotion": "情绪习惯先收住，再用规划与承担感处理",
        "persona": "给人稳重、专业、有边界的印象",
        "relationship": "重视可靠、兑现承诺和现实层面的共建",
        "growth": "在自律之外保留柔软和情绪表达的出口",
    },
    "Aquarius": {
        "core": "重视独立判断、系统视角和非传统路径",
        "emotion": "需要精神空间与自由度，先想明白再投入",
        "persona": "给人理性、特别、保持距离但有想法的印象",
        "relationship": "适合建立在理念认同和彼此尊重基础上的连结",
        "growth": "把抽离感转化为稳定参与，而不是只做旁观者",
    },
    "Pisces": {
        "core": "重视感受、想象和与更大整体的连接",
        "emotion": "情绪边界柔软，容易吸收环境中的细微波动",
        "persona": "给人温柔、感性、带点梦境感的印象",
        "relationship": "常以共情、包容和情绪理解来靠近别人",
        "growth": "学会在敏感之中建立边界和现实锚点",
    },
}

HOUSE_TOPICS: Dict[Any, str] = {
    1: "自我呈现、身体感受与个人启动方式",
    2: "资源、安全感与价值判断",
    3: "沟通、学习与近距离环境",
    4: "家庭根基、内在归属与私人空间",
    5: "创造表达、恋爱、兴趣与舞台感",
    6: "日常事务、工作方法、健康与服务意识",
    7: "亲密关系、合作与镜像课题",
    8: "共享资源、心理转化与深层牵引",
    9: "信念、远行、学术与世界观扩展",
    10: "事业方向、公众形象与成就目标",
    11: "社群、朋友、理想与未来议题",
    12: "潜意识、退隐、疗愈与无形压力",
}

ELEMENT_THEMES = {
    "Fire": "火元素偏强，行动与直觉往往先于迟疑，适合先点燃热情再校正路线。",
    "Earth": "土元素偏强，会优先考虑可落地、可持续、可验证的部分，耐力是优势。",
    "Air": "风元素偏强，思考、交流与观察是天然驱动力，适合在连接信息中找答案。",
    "Water": "水元素偏强，感受力和共情力很突出，很多决定先经过内在情绪过滤。",
}

MODALITY_THEMES = {
    "Cardinal": "基本模式偏强，适合起头、定方向、推动局面，但也要防止过早耗尽冲劲。",
    "Fixed": "固定模式偏强，定力和坚持是优势，但遇到转弯时要练习更柔软地调整。",
    "Mutable": "变动模式偏强，适应性和转译能力很强，但需要防止能量过于分散。",
}

ASPECT_INTERPRETATION = {
    "conjunction": "这组能量会被强力绑在一起，优点是集中，难点是容易彼此放大。",
    "sextile": "这组能量存在顺手的配合感，只要主动使用，就能形成实际助力。",
    "square": "这组能量之间摩擦较强，往往通过不舒服的过程逼出成长和行动。",
    "trine": "这组能量流动自然，常能形成天赋感，但也容易因为太顺而少了打磨。",
    "opposition": "这组能量像在两端拉扯，需要在对立面之间学会平衡和整合。",
}

CHALLENGING_ASPECTS = {"square", "opposition"}
HARMONIOUS_ASPECTS = {"sextile", "trine"}


def _format_degree(value: Any) -> str:
    try:
        return f"{float(value):.2f}°"
    except (TypeError, ValueError):
        return "—"


def _render_snapshot_text(sections: List[tuple[str, str]]) -> str:
    blocks: List[str] = []
    for title, body in sections:
        blocks.append(f"[{title}]")
        if body.strip():
            blocks.append(body)
        blocks.append("")
    return "\n".join(blocks).strip()


def _build_balance_line(balance: Dict[str, Any], labels: Dict[str, str]) -> str:
    ordered_keys = [key for key in labels if key in balance]
    if not ordered_keys:
        return "无"
    return "，".join(f"{labels[key]} {balance.get(key, 0)}" for key in ordered_keys)


def _build_house_lines(houses: List[Dict[str, Any]]) -> str:
    return (
        "\n".join(
            f"第{item['house']}宫：{item['sign_zh']} {_format_degree(item['cusp_longitude'])}"
            for item in houses
        ).strip()
        or "无"
    )


def _build_angle_lines(angles: Dict[str, Any]) -> str:
    ascendant = angles.get("ascendant", {})
    midheaven = angles.get("midheaven", {})
    return "\n".join(
        [
            f"Asc：{ascendant.get('sign_zh', '未知')} {_format_degree(ascendant.get('longitude'))}",
            f"MC：{midheaven.get('sign_zh', '未知')} {_format_degree(midheaven.get('longitude'))}",
        ]
    ).strip()


def _build_planet_lines(planets: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in planets:
        extras: List[str] = []
        dignity = item.get("dignity")
        if dignity and dignity.get("dignity") != "peregrine":
            extras.append(f"{dignity['status_zh']}（{dignity['dignity']}）")
        if "sector13" in item:
            extras.append(f"13扇区 {item['sector13']}")
        if item.get("nakshatra"):
            extras.append(f"宿 {item['nakshatra']}")
        if item.get("su28"):
            extras.append(f"二十八宿 {item['su28']}")
        extras_text = f"，{'，'.join(extras)}" if extras else ""
        lines.append(
            f"{PLANET_LABELS_ZH.get(item['id'], item['id'])}："
            f"{item.get('sign_zh', '未知')} {_format_degree(item.get('degree_in_sign'))}，"
            f"第{item.get('house', '—')}宫，黄纬 {_format_degree(item.get('latitude'))}"
            f"{extras_text}"
        )
    return "\n".join(lines).strip() or "无"


def _build_aspect_lines(aspects: List[Dict[str, Any]]) -> str:
    if not aspects:
        return "无"
    return "\n".join(
        f"{PLANET_LABELS_ZH.get(item['planet_a'], item['planet_a'])}"
        f" 与 {PLANET_LABELS_ZH.get(item['planet_b'], item['planet_b'])}"
        f" 形成 {ASPECT_LABELS_ZH.get(item['aspect'], item['aspect'])}，"
        f"容许度 {_format_degree(item['orb'])}"
        for item in aspects
    )


def _planet_by_id(planets: List[Dict[str, Any]], planet_id: str) -> Dict[str, Any]:
    return next((item for item in planets if item.get("id") == planet_id), {})


def _top_balance_key(balance: Dict[str, Any]) -> Optional[str]:
    if not balance:
        return None
    return sorted(balance.items(), key=lambda item: (-int(item[1]), item[0]))[0][0]


def _house_focus(planets: List[Dict[str, Any]]) -> List[tuple[int, int]]:
    counter = Counter(
        int(item["house"])
        for item in planets
        if item.get("house") is not None and item.get("id") != "North Node"
    )
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def _sign_focus(planets: List[Dict[str, Any]]) -> List[tuple[str, int]]:
    counter = Counter(
        item["sign"]
        for item in planets
        if item.get("sign") and item.get("id") != "North Node"
    )
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def _format_topic_list(items: List[str]) -> str:
    filtered = [item for item in items if item]
    if not filtered:
        return "未知主题"
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]}与{filtered[1]}"
    return f"{'、'.join(filtered[:-1])}与{filtered[-1]}"


def _build_signature(planets: List[Dict[str, Any]], angles: Dict[str, Any]) -> str:
    sun = _planet_by_id(planets, "Sun")
    moon = _planet_by_id(planets, "Moon")
    ascendant = angles.get("ascendant", {})
    return (
        f"太阳{sun.get('sign_zh', '未知')}、"
        f"月亮{moon.get('sign_zh', '未知')}、"
        f"上升{ascendant.get('sign_zh', '未知')}"
    )


def _build_dominant_energy(
    element_balance: Dict[str, Any], modality_balance: Dict[str, Any]
) -> str:
    dominant_element = _top_balance_key(element_balance)
    dominant_modality = _top_balance_key(modality_balance)
    lines: List[str] = []
    if dominant_element:
        lines.append(ELEMENT_THEMES.get(dominant_element, ""))
    if dominant_modality:
        lines.append(MODALITY_THEMES.get(dominant_modality, ""))
    return (
        " ".join(item for item in lines if item).strip() or "当前盘面主导能量尚不明显。"
    )


def _build_core_identity(planets: List[Dict[str, Any]]) -> str:
    sun = _planet_by_id(planets, "Sun")
    sign = sun.get("sign")
    trait = SIGN_INTERPRETATION.get(sign or "", {})
    house_topic = HOUSE_TOPICS.get(sun.get("house"), "个人成长议题")
    return (
        f"太阳落在{sun.get('sign_zh', '未知')}第{sun.get('house', '—')}宫，"
        f"核心驱动力偏向{trait.get('core', '通过经验确认自我方向')}。"
        f"很多自我实现会围绕{house_topic}展开。"
    )


def _build_emotional_style(planets: List[Dict[str, Any]]) -> str:
    moon = _planet_by_id(planets, "Moon")
    sign = moon.get("sign")
    trait = SIGN_INTERPRETATION.get(sign or "", {})
    house_topic = HOUSE_TOPICS.get(moon.get("house"), "情绪与安全感议题")
    return (
        f"月亮落在{moon.get('sign_zh', '未知')}第{moon.get('house', '—')}宫，"
        f"{trait.get('emotion', '情绪处理方式会深刻影响日常节奏')}。"
        f"安全感通常与{house_topic}强相关。"
    )


def _build_social_style(planets: List[Dict[str, Any]], angles: Dict[str, Any]) -> str:
    ascendant = angles.get("ascendant", {})
    midheaven = angles.get("midheaven", {})
    asc_trait = SIGN_INTERPRETATION.get(ascendant.get("sign") or "", {})
    mc_topic = HOUSE_TOPICS.get(10, "事业与公众方向")
    return (
        f"上升{ascendant.get('sign_zh', '未知')}让你在外界面前更容易呈现出"
        f"{asc_trait.get('persona', '鲜明的个人风格')}。"
        f"MC落在{midheaven.get('sign_zh', '未知')}，说明{mc_topic}里会带着这类气质被看见。"
    )


def _build_relationship_pattern(planets: List[Dict[str, Any]]) -> str:
    venus = _planet_by_id(planets, "Venus")
    mars = _planet_by_id(planets, "Mars")
    venus_trait = SIGN_INTERPRETATION.get(venus.get("sign") or "", {})
    mars_trait = SIGN_INTERPRETATION.get(mars.get("sign") or "", {})
    venus_topic = HOUSE_TOPICS.get(venus.get("house"), "关系与价值议题")
    mars_topic = HOUSE_TOPICS.get(mars.get("house"), "行动与欲望议题")
    return (
        f"金星在{venus.get('sign_zh', '未知')}第{venus.get('house', '—')}宫，"
        f"{venus_trait.get('relationship', '会通过关系中的价值感表达喜欢')}，"
        f"而且往往会把心力投向{venus_topic}。"
        f"火星在{mars.get('sign_zh', '未知')}第{mars.get('house', '—')}宫，"
        f"行动时更容易走向{mars_trait.get('core', '直接推进目标')}，"
        f"尤其在{mars_topic}上表现明显。"
    )


def _build_life_focus(planets: List[Dict[str, Any]]) -> str:
    house_focus = _house_focus(planets)
    sign_focus = _sign_focus(planets)
    lines: List[str] = []
    if house_focus:
        top_houses = house_focus[:2]
        topics = _format_topic_list(
            [HOUSE_TOPICS.get(house, f"第{house}宫议题") for house, _ in top_houses]
        )
        labels = "、".join(f"第{house}宫({count})" for house, count in top_houses)
        lines.append(f"盘面重心偏向{labels}，说明{topics}会反复成为人生主轴。")
    if sign_focus and sign_focus[0][1] >= 3:
        sign_name = sign_focus[0][0]
        sign_label = SIGN_INTERPRETATION.get(sign_name, {})
        lines.append(
            f"{SIGN_LABELS_ZH.get(sign_name, sign_name)}能量聚集较多，整个人会更明显地表现出"
            f"{sign_label.get('core', '这一星座的核心气质')}。"
        )
    north_node = _planet_by_id(planets, "North Node")
    if north_node:
        node_topic = HOUSE_TOPICS.get(north_node.get("house"), "长期成长课题")
        lines.append(
            f"北交点落在{north_node.get('sign_zh', '未知')}第{north_node.get('house', '—')}宫，"
            f"长期成长往往要朝{node_topic}持续打开。"
        )
    return " ".join(lines).strip() or "盘面焦点较平均，需要结合现实阶段观察重心。"


def _build_aspect_pattern(aspects: List[Dict[str, Any]]) -> str:
    if not aspects:
        return "显著相位较少，很多主题更像通过整体配置慢慢展开。"

    top_aspect = aspects[0]
    aspect_name = top_aspect.get("aspect")
    top_line = (
        f"最强主相位是{PLANET_LABELS_ZH.get(top_aspect.get('planet_a'), top_aspect.get('planet_a'))}"
        f"与{PLANET_LABELS_ZH.get(top_aspect.get('planet_b'), top_aspect.get('planet_b'))}"
        f"的{ASPECT_LABELS_ZH.get(aspect_name, aspect_name)}，"
        f"容许度{_format_degree(top_aspect.get('orb'))}。"
    )
    aspect_meaning = ASPECT_INTERPRETATION.get(
        aspect_name or "", "这组能量会成为盘面里很难忽略的主旋律。"
    )
    harmony_count = sum(
        1 for item in aspects if item.get("aspect") in HARMONIOUS_ASPECTS
    )
    tension_count = sum(
        1 for item in aspects if item.get("aspect") in CHALLENGING_ASPECTS
    )
    if tension_count > harmony_count:
        tone = "整体相位张力略强，成长通常来自摩擦、决断和重新分配能量。"
    elif harmony_count > tension_count:
        tone = "整体相位协同感更好，很多优势在顺势发挥时会很自然地出现。"
    else:
        tone = "盘面中的顺流与阻力比较均衡，关键在于何时推进、何时收束。"
    return f"{top_line}{aspect_meaning} {tone}"


def _build_development_advice(
    planets: List[Dict[str, Any]],
    element_balance: Dict[str, Any],
    modality_balance: Dict[str, Any],
) -> str:
    dominant_element = _top_balance_key(element_balance)
    dominant_modality = _top_balance_key(modality_balance)
    north_node = _planet_by_id(planets, "North Node")
    sign_trait = SIGN_INTERPRETATION.get(north_node.get("sign") or "", {})
    advice_parts: List[str] = []
    if dominant_element:
        advice_parts.append(ELEMENT_THEMES.get(dominant_element, ""))
    if dominant_modality:
        advice_parts.append(MODALITY_THEMES.get(dominant_modality, ""))
    if north_node:
        advice_parts.append(
            f"成长建议可以特别参考北交点：往{sign_trait.get('growth', '更成熟地承担长期课题')}"
            f"，并把重心逐步放到第{north_node.get('house', '—')}宫对应的人生领域。"
        )
    return (
        " ".join(item for item in advice_parts if item).strip()
        or "当前盘面建议先观察现实情境中的重复模式。"
    )


def _build_variant_note(payload: Dict[str, Any], chart_variant: str) -> Optional[str]:
    if chart_variant == "hellen_chart":
        hellenistic = payload.get("hellenistic", {})
        ascendant_ruler = PLANET_LABELS_ZH.get(
            hellenistic.get("ascendant_ruler", ""),
            hellenistic.get("ascendant_ruler", "未知"),
        )
        angular_planets = (
            "、".join(
                PLANET_LABELS_ZH.get(item, item)
                for item in hellenistic.get("angular_planets", [])
            )
            or "无"
        )
        return (
            f"希腊盘补充信息显示这是{hellenistic.get('sect', '未知')}盘，"
            f"上升主星为{ascendant_ruler}，角宫星体有{angular_planets}。"
        )
    if chart_variant == "india_chart":
        india = payload.get("india", {})
        return (
            f"印度律盘里，上升宿为{india.get('rising_nakshatra', '未知')}，"
            f"月宿为{india.get('moon_nakshatra', '未知')}，"
            f"Ayanamsha约为{_format_degree(india.get('ayanamsha'))}。"
        )
    if chart_variant == "chart13":
        return (
            f"13扇区盘把生命经验进一步切成{len(payload.get('thirteen_sectors', []))}个细段，"
            "适合拿来观察能量落点的细部分区。"
        )
    if chart_variant == "guolao_chart":
        guolao = payload.get("guolao", {})
        return (
            f"七政四余补充信息里，星期主星为"
            f"{PLANET_LABELS_ZH.get(guolao.get('weekday_ruler', ''), guolao.get('weekday_ruler', '未知'))}，"
            f"月宿为{guolao.get('moon_mansion', '未知')}。"
        )
    return None


def _build_chart_interpretation(
    payload: Dict[str, Any], chart_variant: str
) -> Dict[str, str]:
    planets = payload.get("planets", [])
    angles = payload.get("angles", {})
    element_balance = payload.get("element_balance", {})
    modality_balance = payload.get("modality_balance", {})
    interpretation = {
        "signature": _build_signature(planets, angles),
        "dominant_energy": _build_dominant_energy(element_balance, modality_balance),
        "core_identity": _build_core_identity(planets),
        "emotional_style": _build_emotional_style(planets),
        "social_style": _build_social_style(planets, angles),
        "relationship_pattern": _build_relationship_pattern(planets),
        "life_focus": _build_life_focus(planets),
        "aspect_pattern": _build_aspect_pattern(payload.get("aspects", [])),
        "development_advice": _build_development_advice(
            planets, element_balance, modality_balance
        ),
    }
    variant_note = _build_variant_note(payload, chart_variant)
    if variant_note:
        interpretation["variant_note"] = variant_note
    return interpretation


def _build_chart_summary(
    chart_variant: str,
    interpretation: Dict[str, str],
    *,
    engine_precision: str,
) -> List[str]:
    chart_label = (
        "FateBridge 离线高精度星盘"
        if engine_precision == "ephemeris_runtime_model"
        else "FateBridge 离线近似星盘"
    )
    lines = [
        f"已生成 {chart_variant} 的 {chart_label}。",
        f"核心签名：{interpretation['signature']}。",
        interpretation["core_identity"],
        interpretation["emotional_style"],
        interpretation["social_style"],
        interpretation["life_focus"],
        interpretation["aspect_pattern"],
        interpretation["development_advice"],
    ]
    if interpretation.get("variant_note"):
        lines.append(interpretation["variant_note"])
    return lines


def _augment_core_chart_reading(
    payload: Dict[str, Any], chart_variant: str
) -> Dict[str, Any]:
    interpretation = _build_chart_interpretation(payload, chart_variant)
    return {
        "interpretation": interpretation,
        "summary": _build_chart_summary(
            chart_variant,
            interpretation,
            engine_precision=payload.get("chart_profile", {}).get(
                "engine_precision",
                "approximate_orbital_model",
            ),
        ),
    }


_CLASSICAL_PLANET_ORDER = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
]
_ANGULARITY_ZH = {"angular": "角宫", "succedent": "续宫", "cadent": "果宫"}
_COMBUSTION_ZH = {"cazimi": "日心", "combust": "焦伤", "under_beams": "日下"}


def _build_classical_lines(payload: Dict[str, Any]) -> str:
    """One readable line per traditional planet for the ``[古典]`` section."""
    classical = payload.get("classical", {})
    planets = classical.get("planets", {})
    if not planets:
        return "无"
    lines: List[str] = []
    for planet in _CLASSICAL_PLANET_ORDER:
        entry = planets.get(planet)
        if not entry:
            continue
        essential = entry.get("essential") or {}
        labels = essential.get("labels_zh") or ["平"]
        score = essential.get("score", 0)
        parts = [
            PLANET_LABELS_ZH.get(planet, planet),
            f"{'·'.join(labels)}({score:+d})",
            _ANGULARITY_ZH.get(entry.get("angularity"), ""),
        ]
        if entry.get("sect_placement") == "of_sect":
            parts.append("得宗派")
        if entry.get("combustion"):
            parts.append(_COMBUSTION_ZH.get(entry["combustion"], entry["combustion"]))
        if entry.get("retrograde"):
            parts.append("逆行")
        if entry.get("out_of_bounds"):
            parts.append("出界")
        if entry.get("joy"):
            parts.append("喜乐宫")
        lines.append(" ".join(part for part in parts if part))
    return "\n".join(lines).strip() or "无"


_TERMINAL_ZH = {
    "domicile": "入庙自主",
    "mutual_reception": "互含",
    "loop": "循环",
    "unknown": "未定",
}


def _build_dispositor_lines(payload: Dict[str, Any]) -> str:
    """``[主宰]`` section: final dispositor(s) + each traditional planet's chain."""
    classical = payload.get("classical", {})
    dispositors = classical.get("dispositors", {})
    chains = dispositors.get("chains", {})
    if not chains:
        return "无"
    finals = dispositors.get("final_dispositors", [])
    finals_zh = (
        "、".join(PLANET_LABELS_ZH.get(p, p) for p in finals) or "无（多为互含/循环）"
    )
    lines = [f"终极主宰：{finals_zh}"]
    for planet in _CLASSICAL_PLANET_ORDER:
        info = chains.get(planet)
        if not info:
            continue
        arrow = "→".join(PLANET_LABELS_ZH.get(p, p) for p in info.get("chain", []))
        lines.append(f"{arrow}（{_TERMINAL_ZH.get(info.get('terminal_type'), '')}）")
    return "\n".join(lines).strip()


def _build_lots_lines(payload: Dict[str, Any]) -> str:
    """``[阿拉伯点]`` section: each lot's sign/degree + domicile lord and almuten."""
    lots = payload.get("classical", {}).get("lots", {})
    if not lots:
        return "无"
    lines = []
    for lot in lots.values():
        sign_zh = SIGN_LABELS_ZH.get(lot.get("sign"), lot.get("sign", "?"))
        disp = PLANET_LABELS_ZH.get(lot.get("dispositor"), lot.get("dispositor") or "—")
        almuten = PLANET_LABELS_ZH.get(lot.get("almuten"), lot.get("almuten") or "—")
        lines.append(
            f"{lot.get('cn', '?')} {sign_zh}{_format_degree(lot.get('degree_in_sign'))}"
            f" 主{disp} 力主{almuten}"
        )
    return "\n".join(lines).strip()


_BESIEGE_ZH = {"besieged_by_malefics": "凶星围攻", "enclosed_by_benefics": "吉星拱卫"}


def _build_classical_patterns_lines(payload: Dict[str, Any]) -> str:
    """``[古典格局]`` section: sect benefics + overcoming + besiegement + 吉凶化."""
    patterns = payload.get("classical_patterns", {})
    if not patterns:
        return "无"

    def zh(planet: str) -> str:
        return PLANET_LABELS_ZH.get(planet, planet)

    lines = [
        f"宗派吉星：{zh(patterns.get('sect_benefic'))}　宗派凶星：{zh(patterns.get('sect_malefic'))}"
    ]
    overcoming = patterns.get("overcoming", [])
    if overcoming:
        lines.append(
            "制胜（上弦刑凌驾）："
            + "；".join(
                f"{zh(o['overcomer'])}凌驾{zh(o['overcome'])}" for o in overcoming
            )
        )
    besiegement = patterns.get("besiegement", {})
    if besiegement:
        lines.append(
            "围攻："
            + "；".join(
                f"{zh(p)}{_BESIEGE_ZH.get(s, s)}" for p, s in besiegement.items()
            )
        )
    bonification = patterns.get("bonification", {})
    for planet, info in bonification.items():
        parts = []
        if info["bonified_by"]:
            parts.append("吉化←" + "·".join(zh(p) for p in info["bonified_by"]))
        if info["maltreated_by"]:
            parts.append("凶伤←" + "·".join(zh(p) for p in info["maltreated_by"]))
        if parts:
            lines.append(f"{zh(planet)}：{'　'.join(parts)}")
    return "\n".join(lines).strip()


def _build_temperament_lines(payload: Dict[str, Any]) -> str:
    """``[体质]`` section: humor (温/湿 tally) + each traditional planet's 12分度."""
    classical = payload.get("classical", {})
    temperament = classical.get("temperament")
    if not temperament:
        return "无"
    tally = temperament.get("tally", {})
    lines = [
        f"气质：{temperament.get('cn', '?')}"
        f"（热{tally.get('hot', 0)}寒{tally.get('cold', 0)} "
        f"燥{tally.get('dry', 0)}湿{tally.get('moist', 0)}）"
    ]
    dodeka = []
    for planet in _CLASSICAL_PLANET_ORDER:
        entry = (classical.get("planets") or {}).get(planet)
        if not entry or not entry.get("dodekatemorion"):
            continue
        dodeka.append(
            f"{PLANET_LABELS_ZH.get(planet, planet)}"
            f"→{SIGN_LABELS_ZH.get(entry['dodekatemorion'], entry['dodekatemorion'])}"
        )
    if dodeka:
        lines.append("12分度：" + " ".join(dodeka))
    return "\n".join(lines).strip()


def _build_topic_almuten_line(payload: Dict[str, Any]) -> str:
    topic = payload.get("classical", {}).get("topic_almutens", {})
    if not topic:
        return "无"
    parts = []
    for house in sorted(topic, key=lambda h: int(h)):
        winner = topic[house].get("winner")
        parts.append(f"{house}宫{PLANET_LABELS_ZH.get(winner, winner or '—')}")
    return " ".join(parts)


_FIGURIS_POINT_ZH = {
    "Sun": "日",
    "Moon": "月",
    "Ascendant": "命",
    "fortune": "福",
    "syzygy": "朔",
}
_SYZYGY_TYPE_ZH = {"new": "新月", "full": "满月"}


def _build_almuten_figuris_line(payload: Dict[str, Any]) -> str:
    """``[命主]`` section: the Almuten Figuris + its five hylegic points + 朔望."""
    classical = payload.get("classical", {})
    figuris = classical.get("almuten_figuris") or {}
    winner = figuris.get("winner")
    if not winner:
        return "无"
    totals = figuris.get("totals", {})
    lines = [
        f"命主：{PLANET_LABELS_ZH.get(winner, winner)}（{totals.get(winner, 0)}分）"
    ]
    points = figuris.get("points", {})
    point_parts = []
    for point_id in ("Sun", "Moon", "Ascendant", "fortune", "syzygy"):
        info = points.get(point_id)
        if not info:
            continue
        ruler = info.get("winner")
        point_parts.append(
            f"{_FIGURIS_POINT_ZH.get(point_id, point_id)}→"
            f"{PLANET_LABELS_ZH.get(ruler, ruler or '—')}"
        )
    if point_parts:
        lines.append("点主：" + " ".join(point_parts))
    syzygy = classical.get("syzygy")
    if isinstance(syzygy, dict):
        sign = str(syzygy.get("sign") or "?")
        syzygy_type = str(syzygy.get("type") or "?")
        type_zh = _SYZYGY_TYPE_ZH.get(syzygy_type, syzygy_type)
        sign_zh = SIGN_LABELS_ZH.get(sign, sign)
        lines.append(
            f"朔望：{type_zh} {sign_zh}{_format_degree(syzygy.get('degree_in_sign'))}"
        )
    return "\n".join(lines).strip()


def _build_fixed_stars_lines(payload: Dict[str, Any]) -> str:
    """``[恒星]`` section: each catalogue star conjunct a chart point (orb ≤ 1°)."""
    hits = payload.get("fixed_stars")
    if not isinstance(hits, list) or not hits:
        return "无"
    point_zh = {**PLANET_LABELS_ZH, "Ascendant": "上升", "Midheaven": "中天"}
    lines = []
    for hit in hits:
        point = point_zh.get(hit.get("point"), hit.get("point", "?"))
        nature = "/".join(
            PLANET_LABELS_ZH.get(planet, planet) for planet in hit.get("nature", [])
        )
        lines.append(
            f"{hit.get('cn', '')}({hit.get('star', '?')}) 合 {point}"
            f" {_format_degree(hit.get('orb'))}　[{nature}]"
        )
    return "\n".join(lines).strip()


def _build_planetary_hours_line(payload: Dict[str, Any]) -> str:
    """``[行星时]`` section: the birth's planetary hour + the planetary day ruler."""
    hours = payload.get("planetary_hours")
    if not isinstance(hours, dict) or not hours.get("hour_ruler"):
        return "无"
    period = "昼" if hours.get("is_day") else "夜"
    hour_ruler = PLANET_LABELS_ZH.get(hours["hour_ruler"], hours["hour_ruler"])
    day_ruler = hours.get("day_ruler")
    day_ruler_zh = PLANET_LABELS_ZH.get(day_ruler, day_ruler or "—")
    return (
        f"生时主星：{hour_ruler}（{period}第{hours.get('hour_number', '?')}时）"
        f"  当日主星：{day_ruler_zh}"
    )


def _build_standard_chart_snapshot_sections(
    payload: Dict[str, Any], *, chart_variant: str
) -> List[tuple[str, str]]:
    person_info = payload.get("person_info", {})
    chart_profile = payload.get("chart_profile", {})
    interpretation = payload.get("interpretation", {})
    info_lines = [
        f"姓名：{person_info.get('name', '未提供')}",
        f"出生地：{person_info.get('birth_place', '未提供')}",
        f"出生时间：{str(person_info.get('birth_datetime', '未提供')).replace('T', ' ')}",
        f"时区：{person_info.get('birth_timezone', '未提供')}",
        f"经纬度：{_format_degree(person_info.get('birth_longitude'))} / {_format_degree(person_info.get('birth_latitude'))}",
        f"盘型：{chart_profile.get('chart_type', chart_variant)}",
        f"黄道：{chart_profile.get('zodiac_label_zh', chart_profile.get('zodiac', '未知'))}",
        f"宫制：{chart_profile.get('house_system_label_zh', chart_profile.get('house_system', '未知'))}",
        f"精度层：{chart_profile.get('engine_precision', '未知')}",
    ]

    detail_lines = [
        f"元素分布：{_build_balance_line(payload.get('element_balance', {}), ELEMENT_LABELS_ZH)}",
        f"模式分布：{_build_balance_line(payload.get('modality_balance', {}), MODALITY_LABELS_ZH)}",
        f"人格签名：{interpretation.get('signature', '无')}",
        f"主导能量：{interpretation.get('dominant_energy', '无')}",
        f"人生重心：{interpretation.get('life_focus', '无')}",
    ]

    if chart_variant == "chart13":
        detail_lines.append(f"13扇区数量：{len(payload.get('thirteen_sectors', []))}")

    hellenistic = payload.get("hellenistic", {})
    if chart_variant == "hellen_chart":
        detail_lines.extend(
            [
                f"昼夜属性：{hellenistic.get('sect', '未知')}",
                f"上升主星：{PLANET_LABELS_ZH.get(hellenistic.get('ascendant_ruler', ''), hellenistic.get('ascendant_ruler', '未知'))}",
                f"角宫星体：{', '.join(PLANET_LABELS_ZH.get(item, item) for item in hellenistic.get('angular_planets', [])) or '无'}",
            ]
        )

    india = payload.get("india", {})
    if chart_variant == "india_chart":
        detail_lines.extend(
            [
                f"Ayanamsha：{_format_degree(india.get('ayanamsha'))}",
                f"上升宿：{india.get('rising_nakshatra', '未知')}",
                f"月宿：{india.get('moon_nakshatra', '未知')}",
            ]
        )

    greek_lines = ["无"]
    lot_of_fortune = hellenistic.get("lot_of_fortune")
    if isinstance(lot_of_fortune, dict):
        greek_lines = [
            f"福点：{lot_of_fortune.get('sign_zh', '未知')} {_format_degree(lot_of_fortune.get('degree_in_sign'))}，第{lot_of_fortune.get('house', '—')}宫"
        ]

    return [
        ("起盘信息", "\n".join(info_lines).strip()),
        ("宫位宫头", _build_house_lines(payload.get("houses", []))),
        ("星与虚点", _build_angle_lines(payload.get("angles", {}))),
        ("信息", "\n".join(detail_lines).strip()),
        ("相位", _build_aspect_lines(payload.get("aspects", []))),
        ("行星", _build_planet_lines(payload.get("planets", []))),
        ("古典", _build_classical_lines(payload)),
        ("主宰", _build_dispositor_lines(payload)),
        ("命主", _build_almuten_figuris_line(payload)),
        ("宫主星", _build_topic_almuten_line(payload)),
        ("阿拉伯点", _build_lots_lines(payload)),
        ("古典格局", _build_classical_patterns_lines(payload)),
        ("恒星", _build_fixed_stars_lines(payload)),
        ("行星时", _build_planetary_hours_line(payload)),
        ("体质", _build_temperament_lines(payload)),
        ("希腊点", "\n".join(greek_lines).strip()),
        (
            "可能性",
            "\n".join(
                [
                    f"核心人格：{interpretation.get('core_identity', '无')}",
                    f"情绪风格：{interpretation.get('emotional_style', '无')}",
                    f"外在呈现：{interpretation.get('social_style', '无')}",
                    f"关系模式：{interpretation.get('relationship_pattern', '无')}",
                    f"相位主题：{interpretation.get('aspect_pattern', '无')}",
                    f"成长建议：{interpretation.get('development_advice', '无')}",
                    (
                        f"盘型附注：{interpretation.get('variant_note')}"
                        if interpretation.get("variant_note")
                        else ""
                    ),
                ]
            ).strip(),
        ),
    ]


def _build_guolao_snapshot_sections(payload: Dict[str, Any]) -> List[tuple[str, str]]:
    person_info = payload.get("person_info", {})
    chart_profile = payload.get("chart_profile", {})
    guolao = payload.get("guolao", {})
    interpretation = payload.get("interpretation", {})

    setup_lines = [
        f"姓名：{person_info.get('name', '未提供')}",
        f"出生地：{person_info.get('birth_place', '未提供')}",
        f"出生时间：{str(person_info.get('birth_datetime', '未提供')).replace('T', ' ')}",
        f"时区：{person_info.get('birth_timezone', '未提供')}",
        f"经纬度：{_format_degree(person_info.get('birth_longitude'))} / {_format_degree(person_info.get('birth_latitude'))}",
        f"黄道：{chart_profile.get('zodiac_label_zh', chart_profile.get('zodiac', '未知'))}",
        f"宫制：{chart_profile.get('house_system_label_zh', chart_profile.get('house_system', '未知'))}",
    ]

    star_lines = [
        f"{PLANET_LABELS_ZH.get(item['id'], item['id'])}："
        f"{item.get('sign_zh', '未知')} {_format_degree(item.get('degree_in_sign'))}，"
        f"第{item.get('house', '—')}宫，二十八宿 {item.get('su28', '未知')}"
        for item in payload.get("planets", [])
    ]

    shensha_lines = [
        f"星期主星：{PLANET_LABELS_ZH.get(guolao.get('weekday_ruler', ''), guolao.get('weekday_ruler', '未知'))}",
        f"月宿：{guolao.get('moon_mansion', '未知')}",
        f"人格签名：{interpretation.get('signature', '无')}",
        f"盘面重心：{interpretation.get('life_focus', '无')}",
        f"成长建议：{interpretation.get('development_advice', '无')}",
    ]

    return [
        ("起盘信息", "\n".join(setup_lines).strip()),
        ("七政四余宫位与二十八宿星曜", "\n".join(star_lines).strip() or "无"),
        ("神煞", "\n".join(shensha_lines).strip()),
        ("政余格局", guolao_moira.build_section_text(guolao.get("moira_patterns", []))),
    ]


def _build_chart_snapshot(
    payload: Dict[str, Any], chart_variant: str
) -> Dict[str, Any]:
    technique = CORE_CHART_EXPORT_TECHNIQUES.get(chart_variant, "astrochart")
    sections = (
        _build_guolao_snapshot_sections(payload)
        if chart_variant == "guolao_chart"
        else _build_standard_chart_snapshot_sections(
            payload, chart_variant=chart_variant
        )
    )
    snapshot_text = _render_snapshot_text(sections)
    snapshot_export = parse_export_content(
        technique=technique,
        content=snapshot_text,
    )
    return {
        "snapshot_text": snapshot_text,
        "snapshot_export": snapshot_export,
    }


def _build_birth_info(payload: Dict[str, Any]) -> AstroBirthInfo:
    return build_astro_birth_info(
        birth_year=payload["birth_year"],
        birth_month=payload["birth_month"],
        birth_day=payload["birth_day"],
        birth_hour=payload["birth_hour"],
        birth_minute=payload.get("birth_minute", 0),
        birth_timezone=payload.get("birth_timezone"),
        birth_longitude=payload.get("birth_longitude"),
        birth_latitude=payload.get("birth_latitude"),
        name=payload.get("name"),
        birth_place=payload.get("birth_place"),
        use_true_solar_time=payload.get("use_true_solar_time", True),
    )


def calculate_core_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: Optional[float],
    birth_latitude: Optional[float],
    chart_variant: str = "chart",
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    use_true_solar_time: bool = True,
) -> Dict[str, Any]:
    """
    Build an offline core astrology chart family payload.

    Core charts prefer a local Swiss Ephemeris runtime when available and fall
    back to the bundled approximate orbital model when it is not.
    """
    try:
        if chart_variant not in SUPPORTED_CHART_VARIANTS:
            raise ValueError(
                f"不支持的 chart_variant: {chart_variant}。"
                f"可选值：{', '.join(sorted(SUPPORTED_CHART_VARIANTS))}"
            )

        birth_info = _build_birth_info(
            {
                "birth_year": birth_year,
                "birth_month": birth_month,
                "birth_day": birth_day,
                "birth_hour": birth_hour,
                "birth_minute": birth_minute,
                "birth_timezone": birth_timezone,
                "birth_longitude": birth_longitude,
                "birth_latitude": birth_latitude,
                "name": name,
                "birth_place": birth_place,
                "use_true_solar_time": use_true_solar_time,
            }
        )
        result = build_core_chart_payload(
            birth_info,
            chart_variant,
            hsys=hsys,
            zodiacal=zodiacal,
        )
        result.update(_augment_core_chart_reading(result, chart_variant))
        result.update(_build_chart_snapshot(result, chart_variant))
        return result
    except Exception as exc:
        return handle_calculation_error(exc, "核心星盘分析")


def calculate_germany_chart_analysis(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    birth_longitude: float,
    birth_latitude: float,
    birth_minute: int = 0,
    birth_timezone: Optional[str] = None,
    name: Optional[str] = None,
    birth_place: Optional[str] = None,
    hsys: Optional[int] = None,
    zodiacal: Optional[int] = None,
    use_true_solar_time: bool = True,
) -> Dict[str, Any]:
    """
    Build the FateBridge midpoint/germany chart payload.
    """
    try:
        birth_info = _build_birth_info(
            {
                "birth_year": birth_year,
                "birth_month": birth_month,
                "birth_day": birth_day,
                "birth_hour": birth_hour,
                "birth_minute": birth_minute,
                "birth_timezone": birth_timezone,
                "birth_longitude": birth_longitude,
                "birth_latitude": birth_latitude,
                "name": name,
                "birth_place": birth_place,
                "use_true_solar_time": use_true_solar_time,
            }
        )
        return build_midpoint_payload(
            birth_info,
            hsys=hsys,
            zodiacal=zodiacal,
        )
    except Exception as exc:
        return handle_calculation_error(exc, "量化盘分析")


def calculate_relative_chart_analysis(
    *,
    inner_payload: Dict[str, Any],
    outer_payload: Dict[str, Any],
    relative_mode: Any = None,
    relationship_mode: Any = None,
    relative_mode_source: Optional[str] = None,
    hsys: int = 0,
    zodiacal: int = 0,
    relationship_focus: Any = None,
) -> Dict[str, Any]:
    """
    Build synastry/composite payloads for two parties.
    """
    try:
        inner_birth = _build_birth_info(inner_payload)
        outer_birth = _build_birth_info(outer_payload)
        resolved_mode_source = relative_mode_source
        if resolved_mode_source not in {
            "default",
            "relative_mode",
            "relationship_mode",
        }:
            if relative_mode not in (None, ""):
                resolved_mode_source = "relative_mode"
            elif relationship_mode not in (None, ""):
                resolved_mode_source = "relationship_mode"
            else:
                resolved_mode_source = "default"
        resolved_mode = (
            relative_mode if relative_mode not in (None, "") else relationship_mode
        )
        payload = build_relative_payload(
            inner_birth=inner_birth,
            outer_birth=outer_birth,
            relative_mode=resolved_mode,
            relative_mode_source=resolved_mode_source,
            hsys=hsys,
            zodiacal=zodiacal,
            relationship_focus=relationship_focus,
        )
        if isinstance(payload, dict) and "error" not in payload:
            # Allowlist the relationship-facing summary; the raw inner/outer/
            # composite charts and the directional aspect/midpoint dumps stay in
            # the structured payload only (they would flood the snapshot).
            summary_view = {
                key: payload[key]
                for key in (
                    "relationship_profile",
                    "synastry_aspects",
                    "compatibility",
                    "summary",
                )
                if key in payload
            }
            snapshot_text = render_structured_snapshot_text(
                summary_view, title="关系星盘分析"
            )
            payload["snapshot_text"] = snapshot_text
            payload["snapshot_export"] = parse_export_content(
                technique="relative", content=snapshot_text
            )
        return payload
    except Exception as exc:
        return handle_calculation_error(exc, "关系星盘分析")
