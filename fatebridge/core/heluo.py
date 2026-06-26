"""河洛理数 (heluo) — 原生离线计算。

Native Python port of horosa's ``heluoLocal.js`` (+ the ``solarTerm`` helper from
``tools/heluo.js``). Like canping, heluo is computed entirely in-process: four
pillars come from FateBridge's own calendar engine; this module does 起命
(天地数→卦→元堂→后天), 起运 (大限), 命运篇 judge, and 爻辞查表.

The 命运篇 化工/反化 layer is节气-coupled: it needs the real solar term at birth.
We source that from FateBridge's own 24-term engine (``core.almanac``) rather than
lunar-javascript — heluo only consumes the term *name* → 化工象限 + the 土用 flag.

Ported verbatim from 《河洛理数》(陈抟·邵康节); value-aligned with horosa, itself
verified against the文档算例 (heluoLocal.js:3-4).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fatebridge.core.almanac import get_solar_terms_for_year, localize_datetime

# ── 八卦（自下而上三爻 bit：1阳 0阴）──
TRIGRAM_BITS: Dict[str, List[int]] = {
    "乾": [1, 1, 1],
    "兌": [1, 1, 0],
    "離": [1, 0, 1],
    "震": [1, 0, 0],
    "巽": [0, 1, 1],
    "坎": [0, 1, 0],
    "艮": [0, 0, 1],
    "坤": [0, 0, 0],
}
# 洛书数 → 八卦（5 寄中宫，另行处理）
LUOSHU_TRIGRAM: Dict[int, str] = {
    1: "坎",
    2: "坤",
    3: "震",
    4: "巽",
    6: "乾",
    7: "兌",
    8: "艮",
    9: "離",
}
# 天干 → 洛书纳甲数
GAN_NUM: Dict[str, int] = {
    "甲": 6,
    "乙": 2,
    "丙": 8,
    "丁": 7,
    "戊": 1,
    "己": 9,
    "庚": 3,
    "辛": 4,
    "壬": 6,
    "癸": 2,
}
# 地支 → 河图数对 [奇, 偶]
ZHI_PAIR: Dict[str, List[int]] = {
    "子": [1, 6],
    "亥": [1, 6],
    "寅": [3, 8],
    "卯": [3, 8],
    "巳": [7, 2],
    "午": [7, 2],
    "申": [9, 4],
    "酉": [9, 4],
    "辰": [5, 10],
    "戌": [5, 10],
    "丑": [5, 10],
    "未": [5, 10],
}
GAN: List[str] = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI: List[str] = [
    "子",
    "丑",
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
]
YANG_ZHI = frozenset({"子", "寅", "辰", "午", "申", "戌"})  # 阳支(年支定阳命)
YANG_HOURS: List[str] = ["子", "丑", "寅", "卯", "辰", "巳"]  # 上六时·阳时
YIN_HOURS: List[str] = ["午", "未", "申", "酉", "戌", "亥"]  # 下六时·阴时
# 自然象 → 八卦（复合卦名取上下两象）
NATURAL: Dict[str, str] = {
    "天": "乾",
    "地": "坤",
    "水": "坎",
    "火": "離",
    "雷": "震",
    "山": "艮",
    "風": "巽",
    "澤": "兌",
}
# 乾/坤 纯卦元堂配时表（自下而上）
PURE_HOUR_TO_YAO: Dict[str, int] = {
    "子": 1,
    "卯": 1,
    "丑": 2,
    "辰": 2,
    "寅": 3,
    "巳": 3,
    "午": 4,
    "酉": 4,
    "未": 5,
    "戌": 5,
    "申": 6,
    "亥": 6,
}
# 三至尊卦
ZHI_ZUN = frozenset({"坎為水", "水雷屯", "水山蹇"})

# ── 命运篇：元气/反元气/化工 ──
GAN_YUAN: Dict[str, str] = {
    "甲": "乾",
    "壬": "乾",
    "乙": "坤",
    "癸": "坤",
    "庚": "震",
    "辛": "巽",
    "戊": "坎",
    "己": "離",
    "丙": "艮",
    "丁": "兌",
}
ZHI_YUAN: Dict[str, str] = {
    "戌": "乾",
    "亥": "乾",
    "未": "坤",
    "申": "坤",
    "卯": "震",
    "辰": "巽",
    "巳": "巽",
    "子": "坎",
    "午": "離",
    "丑": "艮",
    "寅": "艮",
    "酉": "兌",
}
GAN_FAN: Dict[str, str] = {
    "甲": "坤",
    "壬": "坤",
    "乙": "乾",
    "癸": "乾",
    "庚": "巽",
    "辛": "震",
    "戊": "離",
    "己": "坎",
    "丙": "兌",
    "丁": "艮",
}
ZHI_FAN: Dict[str, str] = {
    "戌": "坤",
    "亥": "坤",
    "未": "乾",
    "申": "乾",
    "卯": "巽",
    "辰": "震",
    "巳": "震",
    "子": "離",
    "午": "坎",
    "丑": "兌",
    "寅": "兌",
    "酉": "艮",
}
QUARTER_HG: Dict[str, Dict[str, str]] = {
    "震": {"hg": "震", "fh": "巽"},
    "離": {"hg": "離", "fh": "坎"},
    "兌": {"hg": "兌", "fh": "艮"},
    "坎": {"hg": "坎", "fh": "離"},
}
# 节气(节/气名)→所属中气象限化工卦（繁简兼容）
JIEQI_QUARTER: Dict[str, str] = {
    "春分": "震",
    "清明": "震",
    "穀雨": "震",
    "谷雨": "震",
    "立夏": "震",
    "小滿": "震",
    "小满": "震",
    "芒種": "震",
    "芒种": "震",
    "夏至": "離",
    "小暑": "離",
    "大暑": "離",
    "立秋": "離",
    "處暑": "離",
    "处暑": "離",
    "白露": "離",
    "秋分": "兌",
    "寒露": "兌",
    "霜降": "兌",
    "立冬": "兌",
    "小雪": "兌",
    "大雪": "兌",
    "冬至": "坎",
    "小寒": "坎",
    "大寒": "坎",
    "立春": "坎",
    "雨水": "坎",
    "驚蟄": "坎",
    "惊蛰": "坎",
}
# 无节气信息时(单测)的月支近似回退
MONTH_HG: Dict[str, List[str]] = {
    "卯": ["震"],
    "辰": ["震"],
    "午": ["離"],
    "未": ["離"],
    "酉": ["兌"],
    "戌": ["兌"],
    "子": ["坎"],
    "丑": ["坎"],
    "寅": ["坤", "艮"],
    "巳": ["坤", "艮"],
    "申": ["坤", "艮"],
    "亥": ["坤", "艮"],
}
MONTH_FH: Dict[str, List[str]] = {
    "卯": ["巽"],
    "辰": ["巽"],
    "午": ["坎"],
    "未": ["坎"],
    "酉": ["艮"],
    "戌": ["艮"],
    "子": ["離"],
    "丑": ["離"],
    "寅": ["乾", "兌"],
    "巳": ["乾", "兌"],
    "申": ["乾", "兌"],
    "亥": ["乾", "兌"],
}
# 八卦纳甲（得势）
NAJIA: Dict[str, List[str]] = {
    "乾": ["壬戌", "壬申", "壬午", "甲辰", "甲寅", "甲子"],
    "坎": ["戊子", "戊戌", "戊申", "戊午", "戊辰", "戊寅"],
    "艮": ["丙寅", "丙子", "丙戌", "丙申", "丙午", "丙辰"],
    "震": ["庚戌", "庚申", "庚午", "庚辰", "庚寅", "庚子"],
    "巽": ["辛卯", "辛巳", "辛未", "辛酉", "辛亥", "辛丑"],
    "離": ["己巳", "己未", "己酉", "己亥", "己丑", "己卯"],
    "坤": ["癸酉", "癸亥", "癸丑", "乙卯", "乙巳", "乙未"],
    "兌": ["丁未", "丁酉", "丁亥", "丁丑", "丁卯", "丁巳"],
}
# 得时：生月(节气)→卦月之卦（短名）
MONTH_GUA: Dict[str, List[str]] = {
    "寅": ["大有", "同人", "泰", "既濟", "咸", "恆", "蠱", "漸"],
    "卯": ["大壯", "晉", "小過", "大過", "革", "訟"],
    "辰": ["井", "睽", "夬", "履", "渙"],
    "巳": ["乾", "艮", "巽", "離"],
    "午": ["姤", "旅", "困", "豫"],
    "未": ["家人", "萃", "遯", "屯"],
    "申": ["節", "比", "隨", "益", "損", "師", "歸妹", "否", "未濟"],
    "酉": ["中孚", "觀", "明夷", "无妄", "升", "蹇", "蒙", "需", "頤"],
    "戌": ["豐", "謙", "噬嗑", "剝"],
    "亥": ["坎", "坤", "兌"],
    "子": ["小畜", "賁", "復"],
    "丑": ["大畜", "震", "解", "鼎", "臨"],
}
# 得体：日干→纳甲卦
DAY_TI: Dict[str, str] = {
    "甲": "乾",
    "乙": "坤",
    "丙": "艮",
    "丁": "兌",
    "戊": "坎",
    "己": "離",
    "庚": "震",
    "辛": "巽",
    "壬": "乾",
    "癸": "坤",
}

# 四立 — 土用 window markers.
LI_TERMS = frozenset({"立春", "立夏", "立秋", "立冬"})

_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "heluo" / "heluoTiaowen.json"
)


@lru_cache(maxsize=1)
def _tiaowen() -> Dict[str, Any]:
    with _DATA_PATH.open(encoding="utf-8") as handle:
        data: Dict[str, Any] = json.load(handle)
    return data


@lru_cache(maxsize=1)
def _gua_tables() -> Tuple[Dict[str, Dict[str, str]], Dict[str, str], Dict[str, int]]:
    """由条文 64 卦名解析 (上卦,下卦) ↔ 卦名 ↔ 王弗序。"""
    name_to_tri: Dict[str, Dict[str, str]] = {}
    tri_to_name: Dict[str, str] = {}
    name_index: Dict[str, int] = {}
    for name, payload in _tiaowen().items():
        if name[1] == "為":  # 纯卦 乾為天
            up = low = name[0]
        else:  # 复合 上象+下象
            up = NATURAL.get(name[0], "")
            low = NATURAL.get(name[1], "")
        if up in TRIGRAM_BITS and low in TRIGRAM_BITS:
            name_to_tri[name] = {"up": up, "low": low}
            tri_to_name[f"{up}|{low}"] = name
            name_index[name] = payload["index"]
    return name_to_tri, tri_to_name, name_index


def _gua_name(up: str, low: str) -> str:
    return _gua_tables()[1].get(f"{up}|{low}", "")


def gua_lines(up: str, low: str) -> List[int]:
    """六爻 bit（自下而上 1-6）= 下卦三爻 + 上卦三爻。"""
    return [*TRIGRAM_BITS[low], *TRIGRAM_BITS[up]]


def lines_to_gua(lines: List[int]) -> Dict[str, str]:
    low = next(
        (t for t, b in TRIGRAM_BITS.items() if all(b[i] == lines[i] for i in range(3))),
        "",
    )
    up = next(
        (
            t
            for t, b in TRIGRAM_BITS.items()
            if all(b[i] == lines[i + 3] for i in range(3))
        ),
        "",
    )
    return {"up": up, "low": low, "name": _gua_name(up, low)}


def _trigram_of(bits: List[int]) -> str:
    return next(
        (t for t, b in TRIGRAM_BITS.items() if all(b[i] == bits[i] for i in range(3))),
        "",
    )


def _san_cai(lines: List[int]) -> List[str]:
    return [
        _trigram_of([lines[i] for i in ix])
        for ix in ([0, 1, 2], [1, 2, 3], [2, 3, 4], [3, 4, 5])
    ]


def _short_name(name: str) -> str:
    return name[0] if name[1] == "為" else name[2:]


# ── 天数(去25)/地数(去30) 归卦数 1-9（5 表示寄中宫）──
def _reduce_tian(t: int) -> int:
    v = t
    while v > 25:
        v -= 25
    if v == 25:
        return 5
    if v >= 10:
        u = v % 10
        return v // 10 if u == 0 else u
    return v


def _reduce_di(d: int) -> int:
    v = d
    while v > 30:
        v -= 30
    if v == 30:
        return 3
    if v >= 10:
        u = v % 10
        return v // 10 if u == 0 else u
    return v


def _wu_ji_gong(minguo_year: int, yang_gan: bool, is_male: bool) -> str:
    """5 寄中宫：按三元(民國年) + 阴阳(年干奇偶) + 男女。"""
    if minguo_year <= 12:  # 上元
        return "艮" if is_male else "坤"
    if minguo_year <= 72:  # 中元
        ay = (yang_gan and is_male) or (not yang_gan and not is_male)  # 阳男 or 阴女
        return "艮" if ay else "坤"
    return "離" if is_male else "兌"  # 下元


def _flip_line(lines: List[int], pos: int) -> List[int]:
    out = lines[:]
    out[pos - 1] = 0 if out[pos - 1] else 1
    return out


def _yuan_tang_pure(gua: Dict[str, Any], hour_zhi: str, is_male: bool) -> int:
    """乾(纯阳)/坤(纯阴) 元堂：男女 + 节气半年。"""
    base = PURE_HOUR_TO_YAO.get(hour_zhi, 1)
    yang_ling = bool(gua.get("yangLing"))  # true=冬至后夏至前
    if gua.get("up") == "乾":
        reverse = (not is_male) and yang_ling  # 乾：女命阳令 自上而下
    else:
        reverse = is_male and (not yang_ling)  # 坤：男命阴令 自上而下
    return 7 - base if reverse else base


def _yuan_tang(
    lines: List[int], hour_zhi: str, is_male: bool, gua: Dict[str, Any]
) -> int:
    """起元堂（动爻 1-6）。"""
    yang = hour_zhi in YANG_HOURS
    hours = YANG_HOURS if yang else YIN_HOURS
    hi = hours.index(hour_zhi)
    match = 1 if yang else 0
    matched: List[int] = []
    others: List[int] = []
    for p in range(1, 7):
        (matched if lines[p - 1] == match else others).append(p)
    k = len(matched)
    if k == 0 or k == 6:  # 乾/坤 纯卦
        return _yuan_tang_pure(gua, hour_zhi, is_male)
    slots = (matched + matched + others if k <= 3 else matched + others)[:6]
    return slots[hi] if hi < len(slots) else slots[-1]


def _swap_trigrams(lines: List[int]) -> List[int]:
    return [lines[3], lines[4], lines[5], lines[0], lines[1], lines[2]]


def transform_houtian(
    xian_name: str, xian_lines: List[int], yuan: int, yang_ling: bool
) -> Dict[str, Any]:
    """翻元堂爻 → 后天卦（三至尊卦「变而不易」特例）。"""
    flipped = _flip_line(xian_lines, yuan)  # ① 元堂爻 阴阳互变
    if xian_name in ZHI_ZUN:
        bu_yi = (yuan == 5 and not yang_ling) or (
            yuan == 6 and yang_ling
        )  # 九五阴令 / 上六阳令
        if bu_yi:  # 变而不易：不互换上下卦、元堂位不动
            return {
                "name": lines_to_gua(flipped)["name"],
                "lines": flipped,
                "yuan": yuan,
            }
    hou_lines = _swap_trigrams(flipped)  # ② 移外卦入内、内卦出外
    hou_yuan = yuan - 3 if yuan > 3 else yuan + 3  # 元堂随上下卦互换而易位
    return {
        "name": lines_to_gua(hou_lines)["name"],
        "lines": hou_lines,
        "yuan": hou_yuan,
    }


def calculate(
    *,
    four_pillars: Dict[str, str],
    gender: str = "男",
    hour_zhi: str,
    birth_year: int,
    month_zhi: str,
    month_yang_ling: Optional[bool] = None,
) -> Dict[str, Any]:
    """起命：天地数→卦→元堂→先天/后天。"""
    year_g = four_pillars["year"][0]
    year_z = four_pillars["year"][1]
    tian = 0
    di = 0
    for key in ("year", "month", "day", "hour"):
        gz = four_pillars[key]
        gn = GAN_NUM[gz[0]]
        if gn % 2 == 1:
            tian += gn
        else:
            di += gn
        odd, even = ZHI_PAIR.get(gz[1], [0, 0])
        tian += odd
        di += even
    is_male = gender not in ("女", "F", "female", 0)
    minguo = (birth_year or 0) - 1911
    yang_gan = GAN.index(year_g) % 2 == 0  # 甲丙戊庚壬=阳
    t_num = _reduce_tian(tian)
    d_num = _reduce_di(di)
    t_gua = (
        _wu_ji_gong(minguo, yang_gan, is_male) if t_num == 5 else LUOSHU_TRIGRAM[t_num]
    )
    d_gua = (
        _wu_ji_gong(minguo, yang_gan, is_male) if d_num == 5 else LUOSHU_TRIGRAM[d_num]
    )

    # 相盪：阳男阴女 天上地下，阴男阳女 天下地上
    yang_ming = year_z in YANG_ZHI
    tian_top = (is_male and yang_ming) or (not is_male and not yang_ming)
    up = t_gua if tian_top else d_gua
    low = d_gua if tian_top else t_gua
    xian_lines = gua_lines(up, low)
    xian_name = _gua_name(up, low)

    # 节气半年：阳令 冬至后~夏至前(子月~巳月)；阴令 夏至后~冬至前。
    yang_ling = (
        month_yang_ling
        if month_yang_ling is not None
        else month_zhi in ("子", "丑", "寅", "卯", "辰", "巳")
    )
    yuan = _yuan_tang(
        xian_lines, hour_zhi, is_male, {"up": up, "low": low, "yangLing": yang_ling}
    )
    hou = transform_houtian(xian_name, xian_lines, yuan, yang_ling)

    return {
        "gender": "男" if is_male else "女",
        "tian": tian,
        "di": di,
        "tianNum": t_num,
        "diNum": d_num,
        "tianGua": t_gua,
        "diGua": d_gua,
        "tianTop": tian_top,
        "yangMing": yang_ming,
        "yangGan": yang_gan,
        "yangLing": yang_ling,
        "hourZhi": hour_zhi,
        "xian": {
            "name": xian_name,
            "up": up,
            "low": low,
            "lines": xian_lines,
            "yuan": yuan,
        },
        "hou": {"name": hou["name"], "lines": hou["lines"], "yuan": hou["yuan"]},
    }


def _ying(p: int) -> int:
    """应爻：1↔4 2↔5 3↔6。"""
    return p + 3 if p <= 3 else p - 3


def da_yun(
    xian: Dict[str, Any], hou: Dict[str, Any], birth_year: int = 0
) -> Dict[str, Any]:
    """大限：先天卦元堂起、自下往上绕行六爻、阳爻9阴爻6年；行完先天接后天。虚岁。"""

    def seg_of(g: Dict[str, Any], start_age: int) -> Dict[str, Any]:
        age = start_age
        segs: List[Dict[str, Any]] = []
        for i in range(6):
            pos = ((g["yuan"] - 1 + i) % 6) + 1
            yang = g["lines"][pos - 1] == 1
            yrs = 9 if yang else 6
            segs.append(
                {
                    "gua": g["name"],
                    "lines": g["lines"][:],
                    "pos": pos,
                    "yang": yang,
                    "years": yrs,
                    "ageStart": age,
                    "ageEnd": age + yrs - 1,
                    "yearStart": birth_year + age - 1 if birth_year else None,
                }
            )
            age += yrs
        return {"segs": segs, "endAge": age - 1}

    a = seg_of(xian, 1)
    b = seg_of(hou, a["endAge"] + 1)
    return {
        "xian": a["segs"],
        "hou": b["segs"],
        "all": [*a["segs"], *b["segs"]],
        "xianEndAge": a["endAge"],
        "endAge": b["endAge"],
    }


def solar_term_huagong(prev_jieqi_name: str, tuyong: bool) -> Dict[str, Any]:
    """据真实节气名 + 土用标志，返回 {hg,fh,quarter,tuyong} 化工/反化工候选。"""
    quarter = JIEQI_QUARTER.get(prev_jieqi_name)
    base = (
        QUARTER_HG.get(quarter, {"hg": "", "fh": ""})
        if quarter
        else {"hg": "", "fh": ""}
    )
    hg = [base["hg"]] if base["hg"] else []
    fh = [base["fh"]] if base["fh"] else []
    if tuyong:
        hg += ["坤", "艮"]
        fh += ["乾", "兌"]
    return {"hg": hg, "fh": fh, "quarter": quarter, "tuyong": bool(tuyong)}


def solar_term(year: int, month: int, day: int, timezone_name: str) -> Dict[str, Any]:
    """出生当下所处节气 + 土用，经 FateBridge 自有 24 节气引擎计算。

    Mirrors horosa ``tools/heluo.js`` ``solarTerm``: 取出生日所处节气名(24 节气
    取最近一个 ≤ 当日)，并判断是否在四立前 18 日土用窗内，喂给 ``judge`` 的
    化工/反化层。节气只取**名称**→化工象限，故对节气安全日(非边界、非土用)与
    horosa(lunar-javascript) 一致。
    """
    anchor = localize_datetime(datetime(year, month, day), timezone_name)
    terms: List[Tuple[datetime, str]] = []
    for yr in (year - 1, year, year + 1):
        for term in get_solar_terms_for_year(yr, timezone_name):
            terms.append((term.moment, term.name))
    terms.sort(key=lambda item: item[0])

    prev_name = ""
    for moment, name in terms:
        if moment <= anchor:
            prev_name = name
        else:
            break
    # 土用：未来 18 日内是否有四立(立春/夏/秋/冬)。
    horizon = anchor + timedelta(days=18)
    tuyong = any(
        name in LI_TERMS and anchor <= moment <= horizon for moment, name in terms
    )
    result = solar_term_huagong(prev_name, tuyong)
    result["term"] = prev_name
    return result


def judge(
    chart: Dict[str, Any],
    four_pillars: Dict[str, str],
    month_zhi: str,
    hg_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """命运篇：元气/化工/得势得时得体/葉否/二数/元堂。"""
    year_g = four_pillars["year"][0]
    year_z = four_pillars["year"][1]
    day_g = four_pillars["day"][0]
    tri_set = set(_san_cai(chart["xian"]["lines"]) + _san_cai(chart["hou"]["lines"]))
    # 得势(纳甲)的基本卦集：horosa 的 calculate() 返回的 hou 不含 up/low，故其 judge 里
    # chart.hou.up/low 实为 undefined、对 NAJIA 命中无贡献——这里只取先天上下卦以逐字节对齐。
    base_tris = {chart["xian"]["up"], chart["xian"]["low"]}

    def mk(gua: str) -> Dict[str, Any]:
        return {"gua": gua, "present": gua in tri_set}

    yuan = {"tian": mk(GAN_YUAN[year_g]), "di": mk(ZHI_YUAN[year_z])}
    fan_yuan = {"tian": mk(GAN_FAN[year_g]), "di": mk(ZHI_FAN[year_z])}
    hg_list = (
        hg_override["hg"]
        if (hg_override and hg_override.get("hg"))
        else MONTH_HG.get(month_zhi, [])
    )
    huagong = {"guas": hg_list, "present": [g for g in hg_list if g in tri_set]}
    fh_list = (
        hg_override["fh"]
        if (hg_override and hg_override.get("fh"))
        else MONTH_FH.get(month_zhi, [])
    )
    fanhua = {"guas": fh_list, "present": [g for g in fh_list if g in tri_set]}
    de_shi = any(
        four_pillars["year"] in NAJIA.get(t, []) for t in base_tris
    )  # 得势(纳甲)
    short = [_short_name(chart["xian"]["name"]), _short_name(chart["hou"]["name"])]
    month_list = MONTH_GUA.get(month_zhi, [])
    de_time = any(s in month_list for s in short)  # 得时(卦月)
    de_ti = mk(DAY_TI[day_g])  # 得体(日干纳甲)
    xie = (
        yuan["tian"]["present"] or yuan["di"]["present"] or len(huagong["present"]) > 0
    )
    er_shu = {
        "tian": chart["tian"],
        "di": chart["di"],
        "tianState": (
            "过" if chart["tian"] > 25 else ("不足" if chart["tian"] < 25 else "得中")
        ),
        "diState": (
            "过" if chart["di"] > 30 else ("不足" if chart["di"] < 30 else "得中")
        ),
    }
    y_pos = chart["xian"]["yuan"]
    y_yang = chart["xian"]["lines"][y_pos - 1] == 1
    ying_pos = _ying(y_pos)
    yuan_tang_info = {
        "pos": y_pos,
        "yang": y_yang,
        "dangWei": (y_pos % 2 == 1) == y_yang,
        "youYing": chart["xian"]["lines"][ying_pos - 1]
        != chart["xian"]["lines"][y_pos - 1],
        "heLi": chart["yangLing"] == y_yang,
    }
    return {
        "yuan": yuan,
        "fanYuan": fan_yuan,
        "huagong": huagong,
        "fanhua": fanhua,
        "deSheng": de_shi,
        "deTime": de_time,
        "deTi": de_ti,
        "xie": xie,
        "erShu": er_shu,
        "yuanTang": yuan_tang_info,
    }


# ── 爻辞查找 ──
def yao_text(gua_name: str, pos: int) -> Optional[Dict[str, Any]]:
    """本卦元堂(动爻)之爻辞。"""
    g = _tiaowen().get(gua_name)
    if not g or not g.get("yao", {}).get(str(pos)):
        return None
    result: Dict[str, Any] = g["yao"][str(pos)]
    return result


_YAO_LABEL = ["初", "二", "三", "四", "五", "上"]


def yao_name(lines: List[int], pos: int) -> str:
    yang = lines[pos - 1] == 1
    if pos == 1:
        return f"初{'九' if yang else '六'}"
    if pos == 6:
        return f"上{'九' if yang else '六'}"
    return f"{'九' if yang else '六'}{_YAO_LABEL[pos - 1]}"


def build_snapshot_text(
    chart: Dict[str, Any], jg: Optional[Dict[str, Any]], dy: Optional[Dict[str, Any]]
) -> str:
    if not chart:
        return ""
    lines: List[str] = []
    lines.append("[起命]")
    lines.append(
        f"天数{chart['tian']}→{chart['tianGua']}　地数{chart['di']}→{chart['diGua']}"
    )
    lines.append(
        f"先天卦：{chart['xian']['name']}　元堂 {yao_name(chart['xian']['lines'], chart['xian']['yuan'])}"
    )
    lines.append(
        f"后天卦：{chart['hou']['name']}　元堂 {yao_name(chart['hou']['lines'], chart['hou']['yuan'])}"
    )
    xt = yao_text(chart["xian"]["name"], chart["xian"]["yuan"])
    ht = yao_text(chart["hou"]["name"], chart["hou"]["yuan"])
    if xt:
        lines += [
            "",
            f"[先天·{chart['xian']['name']} 元堂爻辞]",
            f"摘要：{xt['detail']}",
            f"诗歌：{xt['shige']}",
        ]
    if ht:
        lines += [
            "",
            f"[后天·{chart['hou']['name']} 元堂爻辞]",
            f"摘要：{ht['detail']}",
            f"诗歌：{ht['shige']}",
        ]
    if jg:
        lines.append("")
        lines.append("[命运篇]")
        lines.append(
            f"天元气 {jg['yuan']['tian']['gua']}{'(有)' if jg['yuan']['tian']['present'] else '(无)'}　地元气 {jg['yuan']['di']['gua']}{'(有)' if jg['yuan']['di']['present'] else '(无)'}"
        )
        hg_present = (
            f"(有:{''.join(jg['huagong']['present'])})"
            if jg["huagong"]["present"]
            else "(无)"
        )
        lines.append(
            f"化工 {'/'.join(jg['huagong']['guas'])}{hg_present}　{'葉' if jg['xie'] else '不葉'}"
        )
        lines.append(
            f"得势{'有' if jg['deSheng'] else '无'}　得时{'有' if jg['deTime'] else '无'}　得体 {jg['deTi']['gua']}{'(有)' if jg['deTi']['present'] else '(无)'}"
        )
        lines.append(
            f"二数：天{jg['erShu']['tian']}({jg['erShu']['tianState']}) 地{jg['erShu']['di']}({jg['erShu']['diState']})"
        )
        lines.append(
            f"元堂：{'当位' if jg['yuanTang']['dangWei'] else '不当位'}　{'有应' if jg['yuanTang']['youYing'] else '无应'}　{'顺气' if jg['yuanTang']['heLi'] else '逆气'}"
        )
    if dy and dy.get("all"):
        lines.append("")
        lines.append("[大限·岁运]")
        for s in dy["all"]:
            lines.append(
                f"{s['ageStart']}-{s['ageEnd']}岁 {s['gua']} {yao_name(s['lines'], s['pos'])}（{'阳9' if s['yang'] else '阴6'}）"
            )
    return "\n".join(lines)
