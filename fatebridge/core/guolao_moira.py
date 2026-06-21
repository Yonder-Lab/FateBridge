"""七政四余 政余格局 (Moira DSL) — native-Python port of horosa ``guolaoMoira.js``.

Ported verbatim (structure-preserving) from horosa-skill
``horosa-core-js/src/vendor/guolao/guolaoMoira.js`` (星阙 v2.6.x, 抽取自
GuoLaoChartMain.js). The JS reads a fully-computed 七政四余 chart and emits 喜格/忌格
pattern lines; this module reproduces the **盘面物象格局** subset that runs on data
FateBridge can supply (planet sign positions + ASC + 孛/罗 + 昼夜/季节).

Scope notes (see docs/superpowers/specs/2026-06-21-guolao-moira-engine-design.md):

* **神煞 gods are not yet supplied** (``_GOD_SIGNS`` is empty), so the two
  god-dependent patterns — 日月拱贵人 (天贵/玉贵) and 命登岁驾 (岁驾) — are inert here,
  exactly as in horosa's *offline* skill (``guolaoGods`` is not returned by its
  offline ``/chart`` either). They light up once Phase 2 ports the 神煞 起例.
* **紫炁 (木余) is not yet computed.** It feeds no pattern *directly*, but
  ``孤月独明`` counts shared-sign bodies over the full 11-body ``MOIRA_PLANET_ORDER``
  which includes 炁; with 炁 absent that count omits it. Faithful once Phase 4 adds 紫炁.
* **命坐两歧** ships its 近宫界 half only; 近宿界 needs a real 宿度 table FB lacks
  (``_su28`` is equal-spaced) — deferred to Phase 3.

The remaining patterns (八杀朝天/日月拱官/金水相涵/日月失所/官福失垣/孛犯太阳/罗犯太阳/
孛罗交战) match ``guolaoMoira.js`` byte-for-byte given identical chart inputs, and are
locked by a Node-oracle parity test.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# --- 数据表（verbatim from guolaoMoira.js / SZConst.js）-----------------------

# LIST_SIGNS index (0=Aries … 11=Pisces) → 地支（七政四余 戌将盘；SZConst.SignZi）。
_SIGN_ZI = ["戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥"]

# 行星中文 → 喜用名（guolaoMoira MOIRA_PLANET_CN_TO_ID 的中文键）。
# 在本端口中 facts["planet_signidx"] 直接以中文键给出星座序号。
_MOIRA_PLANET_ORDER = ["日", "月", "金", "木", "水", "火", "土", "计", "罗", "炁", "孛"]

# MOIRA_RULER_BY_SIGN：星座序号 → 庙主行星中文（Aries…Pisces）。
_RULER_BY_SIGN_IDX = [
    "火",
    "金",
    "水",
    "月",
    "日",
    "水",
    "金",
    "火",
    "木",
    "土",
    "土",
    "木",
]

# MOIRA_OVERCOMING：克制关系（行星中文 → 被其克的行星中文）。
_OVERCOMING = {
    "日": "月",
    "月": "日",
    "金": "火",
    "木": "金",
    "水": "土",
    "火": "水",
    "土": "木",
    "炁": "金",
    "孛": "土",
    "罗": "水",
    "计": "木",
}

# Phase 1：神煞未供（与 horosa 离线版一致），天贵/玉贵/岁驾 等查表恒空。
_GOD_SIGNS: Dict[str, int] = {}

# 命宫起十二宫的次序偏移（localMoiraHouseSign）。
_HOUSE_OFFSET = {
    "命": 0,
    "命宫": 0,
    "财": 1,
    "财帛": 1,
    "兄弟": 2,
    "田": 3,
    "田宅": 3,
    "嗣": 4,
    "男女": 4,
    "奴": 5,
    "奴仆": 5,
    "妻": 6,
    "夫妻": 6,
    "疾": 7,
    "疾厄": 7,
    "迁": 8,
    "迁移": 8,
    "官": 9,
    "官禄": 9,
    "福": 10,
    "福德": 10,
    "相": 11,
    "相貌": 11,
}


# --- 工具函数 ----------------------------------------------------------------


def _sign_zi(sign_idx: int) -> str:
    if sign_idx < 0:
        return ""
    return _SIGN_ZI[(sign_idx + 12) % 12]


def _same(a: int, b: int) -> bool:
    return a >= 0 and b >= 0 and a == b


def _rel(base: int, offset: int) -> int:
    return (base + offset + 12) % 12


def _house_sign(life_sign_idx: int, offset: int) -> int:
    return -1 if life_sign_idx < 0 else (life_sign_idx + offset + 12) % 12


# --- Pattern record ----------------------------------------------------------


def _add(
    patterns: List[Dict[str, Any]],
    name: str,
    level: str,
    score: str,
    detail: str,
    dsl: str,
) -> None:
    patterns.append(
        {
            "name": name,
            "level": level,
            "score": score,
            "source": "moira_s.prop-local",
            "dsl": dsl,
            "detail": detail,
        }
    )


class _Resolver:
    """localSignOfCn：把宫名/行星/地支/神煞名解析为星座序号（与 JS 同序）。"""

    def __init__(
        self, planet_signidx: Dict[str, int], life_sign_idx: int, self_sign_idx: int
    ) -> None:
        self._planets = planet_signidx
        self._life = life_sign_idx
        self._self = self_sign_idx

    def __call__(self, name: str) -> int:
        if name in _HOUSE_OFFSET:
            return _house_sign(self._life, _HOUSE_OFFSET[name])
        if name == "身":
            return self._self
        if name in _GOD_SIGNS:
            return _GOD_SIGNS[name]
        if name in self._planets:
            return self._planets[name]
        try:
            return _SIGN_ZI.index(name)
        except ValueError:
            return -1


def _lost_rulership(signof: _Resolver, subject: str) -> bool:
    """localMoiraLostRulership：宫主落于被其克之星所主之宫（失垣）。"""
    sign_idx = signof(subject)
    if sign_idx < 0:
        return False
    ruler_cn = _RULER_BY_SIGN_IDX[sign_idx]
    ruler_sign = signof(ruler_cn)
    if ruler_sign < 0:
        return False
    ruler_of_ruler = _RULER_BY_SIGN_IDX[ruler_sign]
    return ruler_of_ruler == _OVERCOMING.get(ruler_cn)


def _near_sign_boundary(lon: Optional[float]) -> bool:
    if lon is None:
        return False
    val = ((lon % 30) + 30) % 30
    return val <= 1 or val >= 29


# --- 主入口 ------------------------------------------------------------------


def calculate(facts: Dict[str, Any]) -> List[Dict[str, Any]]:
    """buildLocalMoiraPatterns 的 Python 端口。

    ``facts`` 形如::

        {
          "asc_lon": float,                     # 命度（默认命主=ASC）
          "planet_signidx": {"日": int, "月": int, "金": int, "水": int,
                              "火": int, "木": int, "土": int,
                              "孛": int, "罗": int, "计": int, "炁": int},  # 缺省 -1
          "is_day": bool,                       # 昼生（6<=hour<18）
          "is_winter": bool,                    # 冬令（月 ∈ {11,12,1}）
        }

    返回排序后的格局列表（good 在前、bad 在后），结构与 JS 一致。
    """
    planet_signidx = {k: v for k, v in (facts.get("planet_signidx") or {}).items()}
    asc_lon = facts.get("asc_lon")
    life_sign_idx = -1 if asc_lon is None else int(asc_lon // 30) % 12
    self_sign_idx = planet_signidx.get("月", -1)
    is_day = bool(facts.get("is_day", True))
    is_winter = bool(facts.get("is_winter", False))

    signof = _Resolver(planet_signidx, life_sign_idx, self_sign_idx)

    sun = signof("日")
    moon = signof("月")
    venus = signof("金")
    mercury = signof("水")
    dark_moon = signof("孛")
    north_node = signof("罗")
    guan = signof("官")

    patterns: List[Dict[str, Any]] = []
    life_zi = _sign_zi(life_sign_idx) if life_sign_idx >= 0 else ""

    # 八杀朝天（喜）：疾厄宫主入命，且命临戌亥。
    if life_sign_idx >= 0 and life_zi and life_zi in "戌亥":
        disease_ruler_cn = _RULER_BY_SIGN_IDX[signof("疾")]
        if _same(signof(disease_ruler_cn), life_sign_idx):
            _add(
                patterns,
                "八杀朝天",
                "good",
                "3.2.0",
                "政余喜格：疾厄宫主入命，且命临戌亥。",
                "@{@{疾厄}[1]}=@命",
            )

    # 孤月独明（喜）：夜生月曜独居一方。
    if moon >= 0:
        same_moon = sum(
            1 for cn in _MOIRA_PLANET_ORDER if planet_signidx.get(cn, -1) == moon
        )
        if not is_day and same_moon == 1:
            _add(
                patterns,
                "孤月独明",
                "good",
                "2.3.0",
                "政余喜格：夜生月曜独居一方。",
                "?{孤月} & ?夜",
            )

    # 日月拱官（喜）：日月分拱官禄。
    if (_same(sun, _rel(guan, 4)) and _same(moon, _rel(guan, -4))) or (
        _same(sun, _rel(guan, -4)) and _same(moon, _rel(guan, 4))
    ):
        _add(
            patterns,
            "日月拱官",
            "good",
            "2.3.0",
            "政余喜格：日月分拱官禄。",
            "@日=@官禄+4 & @月=@官禄-4",
        )

    # 金水相涵（喜）：金水同宫，且不以冬令破格。
    if _same(venus, mercury) and not is_winter:
        _add(
            patterns,
            "金水相涵",
            "good",
            "2.3.0",
            "政余喜格：金水同宫，且不以冬令破格。",
            "?{金水会} & !?冬",
        )

    # 日月拱贵人（喜）：神煞依赖，Phase 1 恒空（天贵/玉贵 未供）。
    noble = signof("天贵" if is_day else "玉贵")
    if (_same(sun, _rel(noble, 4)) and _same(moon, _rel(noble, -4))) or (
        _same(sun, _rel(noble, -4)) and _same(moon, _rel(noble, 4))
    ):
        _add(
            patterns,
            "日月拱贵人",
            "good",
            "2.2.0",
            f"政余喜格：{'昼取天贵' if is_day else '夜取玉贵'}，日月分拱。",
            "?昼/夜 & 日月拱贵人",
        )

    # 命登岁驾（喜）：神煞依赖，Phase 1 恒空（岁驾 未供）。
    if _same(life_sign_idx, signof("岁驾")):
        _add(
            patterns,
            "命登岁驾",
            "good",
            "2.0.3",
            "政余喜格：命度临岁驾。",
            "@命=@{岁驾}",
        )

    # 日月失所（忌）：日居西北、月居东南。
    if sun >= 0 and moon >= 0:
        sun_zi = _sign_zi(sun)
        moon_zi = _sign_zi(moon)
        if sun_zi in "申酉戌亥子丑" and moon_zi in "寅卯辰巳午未":
            _add(
                patterns,
                "日月失所",
                "bad",
                "2.3.0",
                "政余忌格：日居西北、月居东南。",
                "(?{日西}|?{日北}) & (?{月东}|?{月南})",
            )

    # 官福失垣（忌）：官禄、福德主失垣。
    if _lost_rulership(signof, "官") and _lost_rulership(signof, "福"):
        _add(
            patterns,
            "官福失垣",
            "bad",
            "2.2.0",
            "政余忌格：官禄、福德主失垣。",
            "?{官失垣} & ?{福失垣}",
        )

    # 孛犯太阳（忌）：孛与太阳同宫。
    if _same(dark_moon, sun):
        _add(
            patterns,
            "孛犯太阳",
            "bad",
            "2.2.0",
            "政余忌格：孛与太阳同宫。",
            "?{日孛遇}",
        )

    # 罗犯太阳（忌）：罗与太阳同宫。
    if _same(north_node, sun):
        _add(
            patterns,
            "罗犯太阳",
            "bad",
            "2.2.0",
            "政余忌格：罗与太阳同宫。",
            "?{日罗遇}",
        )

    # 孛罗交战（忌）：罗孛同宫。
    if _same(north_node, dark_moon):
        _add(patterns, "孛罗交战", "bad", "2.2.0", "政余忌格：罗孛同宫。", "?{罗孛遇}")

    # 命坐两歧（忌）：命度近宫界（近宿界 half 见 Phase 3，FB 无真实宿度表）。
    if _near_sign_boundary(asc_lon):
        _add(
            patterns, "命坐两歧", "bad", "2.0.4", "政余忌格：命度近宫界。", "?{命宫歧}"
        )

    def _level_rank(level: str) -> int:
        return 0 if level == "good" else (1 if level == "bad" else 2)

    patterns.sort(key=lambda p: _level_rank(p["level"]))
    return patterns


def build_section_text(patterns: List[Dict[str, Any]]) -> str:
    """runGuolaoMoira 的输出格式：喜格/忌格/察看 三行。"""

    def fmt(items: List[Dict[str, Any]]) -> str:
        return "；".join(
            f"{it['name']}（{it.get('detail') or it.get('dsl') or ''}）" for it in items
        )

    good = [p for p in patterns if p["level"] == "good"]
    bad = [p for p in patterns if p["level"] == "bad"]
    other = [p for p in patterns if p["level"] not in ("good", "bad")]

    lines = [
        f"喜格：{fmt(good) if good else '（无）'}",
        f"忌格：{fmt(bad) if bad else '（无）'}",
    ]
    if other:
        lines.append(f"察看：{fmt(other)}")
    return "\n".join(lines)
