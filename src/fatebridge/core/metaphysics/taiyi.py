"""
太乙神数 (Tai Yi) 命法 board construction for the FateBridge metaphysics package.

This is a FAITHFUL pure-Python port of the 太乙統宗 人道命法 ("year-counting"
life chart, ``ji_style=0`` / ``taiyi_acumyear=0`` path) from the reference
implementation ``kintaiyi`` by kentang2017 (https://github.com/kentang2017/kintaiyi,
MIT License). The vendored algorithm and the lookup tables below are transcribed
from that project's ``kintaiyi.py`` and ``config.py``; see the NOTICE block at the
bottom of this module for full attribution.

Net-zero new runtime deps: kintaiyi's ``numpy``/``cn2an`` usages are replaced with
plain Python lists and FateBridge's existing ``chinese_numeral``; its
``ephem``/``sxtwl`` calendar engine is NOT used — the four 干支 pillars and the
lunar year come from FateBridge's own swisseph-backed calendar via
``MetaphysicsSeed``. The life chart (``ji_style=0``) depends only on the four
pillars plus the lunar year, so 节气 boundaries do not enter this path.

The output keeps the historical FateBridge taiyi contract keys
(``style_label``, ``accumulation_label``, ``rotation``, ``life_method``,
``taiyi_palace``, ``wenchang_palace``, ``core_board.*``, ``palace_marks``) but now
populated with REAL values, and extends it with the genuine markers
(始击/定目/主算/客算/君臣民基 …) under ``core_board`` and the per-palace star
placements under ``palace_marks``.
"""

from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional, TypeVar

from .common import MetaphysicsSeed, chinese_numeral, require_lunar_month_day

_T = TypeVar("_T")

# --------------------------------------------------------------------------- #
# Vendored constant tables (from kintaiyi config.py, verbatim).               #
# --------------------------------------------------------------------------- #

_DI_ZHI = list("子丑寅卯辰巳午未申酉戌亥")

# 太乙、四神、天乙、地乙、值符 排法 (72-long).
_TAIYI_PAI = list(
    "乾乾乾午午午艮艮艮卯卯卯酉酉酉坤坤坤子子子巽巽巽"
    "乾乾乾午午午艮艮艮卯卯卯酉酉酉坤坤坤子子子巽巽巽"
    "乾乾乾午午午艮艮艮卯卯卯酉酉酉坤坤坤子子子巽巽巽"
)
_SF_LIST = list(
    "坤戌亥丑寅辰巳坤酉乾丑寅辰午坤酉亥子艮辰巳未申戌亥艮卯巽未丑戌子艮卯巳午"
    "坤戌亥丑寅辰巳坤酉乾丑寅辰午坤酉亥子艮辰巳未申戌亥艮卯巽未丑戌子艮卯巳午"
)
_FOUR_GOD = list(
    "乾乾乾午午午艮艮艮卯卯卯中中中酉酉酉坤坤坤子子子巽巽巽巳巳巳申申申寅寅寅"
)
_SKY_YI = list(
    "酉酉酉坤坤坤子子子巽巽巽巳巳巳申申申寅寅寅乾乾乾午午午艮艮艮卯卯卯中中中"
)
_EARTH_YI = list(
    "巽巽巽巳巳巳申申申寅寅寅乾乾乾午午午艮艮艮卯卯卯中中中酉酉酉坤坤坤子子子"
)
_ZHI_FU = list(
    "中中中酉酉酉坤坤坤子子子巽巽巽巳巳巳申申申寅寅寅乾乾乾午午午艮艮艮卯卯卯"
)
_OFFICER_BASE = list(
    "巳巳午午午未未未申申申酉酉酉戌戌戌亥亥亥子子子丑丑丑寅寅寅卯卯卯辰辰辰巳"
)

_NUM = [8, 3, 4, 9, 2, 7, 6, 1]
_JC = list("丑寅辰巳未申戌亥")
_JC1 = list("巽艮坤乾")
_TYJC = [1, 3, 7, 9]
_SIXTEEN = list("子丑艮寅卯辰巽巳午未坤申酉戌乾亥")
_GONG1 = list("子丑艮寅卯辰巽巳午未坤申酉戌乾亥")
_L_NUM = [8, 8, 3, 3, 4, 4, 9, 9, 2, 2, 7, 7, 6, 6, 1, 1]

_SKYEYES_DICT = {
    "陽": list(
        "申酉戌乾乾亥子丑艮寅卯辰巽巳午未坤坤申酉戌乾乾亥子丑艮寅卯辰巽巳午未坤坤"
        "申酉戌乾乾亥子丑艮寅卯辰巽巳午未坤坤申酉戌乾乾亥子丑艮寅卯辰巽巳午未坤坤"
    ),
    "陰": list(
        "寅卯辰巽巽巳午未坤申酉戌乾亥子丑艮艮寅卯辰巽巽巳午未坤申酉戌乾亥子丑艮艮"
        "寅卯辰巽巽巳午未坤申酉戌乾亥子丑艮艮寅卯辰巽巽巳午未坤申酉戌乾亥子丑艮艮"
    ),
}
_SKYEYES_SUMMARY = {
    "陽": (
        ",始擊擊,,內迫,,,辰迫,,囚,,囚,,,,,,囚,囚,客挾,,,,,,,,囚,囚,始擊擊,,,始擊擊,"
        "始擊掩,始擊掩,,,,囚,辰迫,,客挾,客挾,囚,客挾,宮迫,,主挾，宮迫,辰迫,,,,主挾，辰迫,"
        "宮迫,宮迫,始擊掩,,,,客挾,,,,,,主挾,辰擊,,始擊掩,始擊擊,始擊擊,囚,始擊擊"
    ).split(","),
    "陰": (
        ",內辰迫,外辰迫,內辰擊,,,外宮迫,掩、辰迫,掩,掩、辰迫,掩、囚,內宮迫,內宮擊,,,"
        "掩、外辰迫,掩,掩,,關客,關客,關客,,外宮擊,,,外宮擊,,,,內宮擊,,關主,關客,,,"
        "外辰迫,掩,內辰迫,關客,內辰擊,,掩,內辰迫,內宮迫,掩,外宮迫,外宮迫,外宮擊,內宮擊,,"
        "內辰迫,外辰擊,掩,關主,,,外宮擊,掩,內宮擊,內宮迫,外宮擊,,內宮擊,,,,,,,,,"
    ).split(","),
}

# 主/客 定算查表 (find_cal): [home, away, set] per (阴/阳, 局數 1-72).
_YANG_CAL = [
    [7, 13, 13],
    [6, 1, 1],
    [1, 40, 32],
    [25, 17, 10],
    [25, 14, 1],
    [25, 10, 12],
    [8, 25, 9],
    [1, 22, 3],
    [3, 15, 33],
    [1, 12, 25],
    [4, 4, 13],
    [37, 1, 4],
    [18, 19, 19],
    [10, 9, 9],
    [9, 7, 6],
    [1, 33, 26],
    [7, 27, 16],
    [7, 26, 11],
    [8, 32, 14],
    [7, 26, 2],
    [2, 17, 33],
    [16, 30, 1],
    [16, 23, 32],
    [16, 17, 23],
    [39, 40, 40],
    [32, 31, 31],
    [31, 28, 31],
    [14, 9, 38],
    [13, 39, 26],
    [10, 32, 17],
    [33, 10, 34],
    [25, 8, 24],
    [24, 3, 15],
    [26, 4, 11],
    [25, 28, 1],
    [25, 27, 36],
    [1, 7, 7],
    [6, 35, 35],
    [35, 34, 26],
    [27, 19, 12],
    [27, 16, 3],
    [27, 12, 34],
    [8, 17, 1],
    [23, 14, 32],
    [32, 7, 25],
    [5, 16, 29],
    [4, 8, 17],
    [1, 5, 8],
    [24, 25, 25],
    [16, 15, 15],
    [15, 13, 6],
    [39, 31, 24],
    [38, 25, 14],
    [38, 24, 9],
    [16, 3, 22],
    [15, 34, 10],
    [10, 25, 10],
    [12, 26, 27],
    [12, 19, 28],
    [12, 13, 19],
    [33, 34, 34],
    [26, 25, 25],
    [25, 22, 18],
    [16, 11, 7],
    [15, 1, 28],
    [12, 34, 19],
    [25, 2, 26],
    [17, 8, 16],
    [16, 32, 7],
    [30, 4, 15],
    [29, 32, 5],
    [29, 31, 9],
]
_YING_CAL = [
    [5, 29, 7],
    [4, 17, 1],
    [1, 16, 30],
    [25, 33, 2],
    [25, 30, 1],
    [17, 26, 10],
    [2, 3, 3],
    [1, 7, 7],
    [7, 33, 27],
    [1, 24, 25],
    [6, 26, 19],
    [35, 23, 8],
    [12, 37, 12],
    [12, 27, 11],
    [11, 25, 4],
    [1, 15, 24],
    [3, 9, 16],
    [3, 8, 9],
    [14, 16, 16],
    [13, 10, 10],
    [10, 1, 39],
    [24, 14, 1],
    [24, 7, 40],
    [16, 1, 29],
    [31, 16, 32],
    [30, 7, 29],
    [29, 4, 26],
    [8, 25, 32],
    [7, 15, 26],
    [2, 8, 15],
    [27, 28, 28],
    [27, 26, 26],
    [26, 18, 15],
    [29, 22, 9],
    [25, 10, 1],
    [25, 9, 34],
    [1, 25, 3],
    [4, 13, 37],
    [37, 12, 26],
    [33, 1, 10],
    [33, 38, 9],
    [25, 34, 38],
    [2, 1, 1],
    [39, 38, 38],
    [38, 31, 25],
    [7, 1, 31],
    [6, 32, 25],
    [1, 29, 14],
    [16, 1, 17],
    [16, 31, 15],
    [15, 29, 4],
    [33, 7, 16],
    [32, 1, 8],
    [32, 8, 1],
    [16, 18, 18],
    [15, 12, 12],
    [12, 3, 1],
    [18, 8, 35],
    [18, 1, 34],
    [10, 35, 25],
    [27, 22, 28],
    [26, 3, 25],
    [25, 4, 12],
    [16, 33, 3],
    [15, 23, 34],
    [10, 16, 23],
    [25, 26, 26],
    [25, 24, 24],
    [24, 16, 13],
    [32, 28, 15],
    [31, 16, 7],
    [31, 15, 1],
]

_NUMDICT = {
    1: "雜陰",
    2: "純陰",
    3: "純陽",
    4: "雜陽",
    6: "純陰",
    7: "雜陰",
    8: "雜陽",
    9: "純陽",
    11: "陰中重陽",
    12: "下和",
    13: "雜重陽",
    14: "上和",
    16: "下和",
    17: "陰中重陽",
    18: "上和",
    19: "雜重陽",
    22: "純陰",
    23: "次和",
    24: "雜重陰",
    26: "純陰",
    27: "下和",
    28: "雜重陰",
    29: "次和",
    31: "雜重陽",
    32: "次和",
    33: "純陽",
    34: "下和",
    37: "雜重陽",
    38: "下和",
    39: "純陽",
}

# 16-palace display order (FateBridge legacy contract for palace_marks list).
TAIYI_PALACE16_ORDER = [
    "巽",
    "巳",
    "午",
    "未",
    "坤",
    "申",
    "酉",
    "戌",
    "乾",
    "亥",
    "子",
    "丑",
    "艮",
    "寅",
    "卯",
    "辰",
]


# --------------------------------------------------------------------------- #
# Vendored leaf helpers (kintaiyi config.py).                                 #
# --------------------------------------------------------------------------- #


def _new_list(values: List[_T], start: _T) -> List[_T]:
    index = values.index(start)
    return values[index:] + values[:index]


def _num2gong(num: Optional[int]) -> Optional[str]:
    return dict(zip(range(1, 10), list("乾午艮卯中酉坤子巽"))).get(num)  # type: ignore[arg-type]


def _cal_des(num: int) -> List[str]:
    tnum: List[str] = []
    if num > 10 and num % 10 > 5:
        tnum.append("三才足數")
    if num < 10:
        tnum.append("無天，二曜虛蝕、五緯失度、慧孛飛流、霜雹為害")
    if num % 10 < 5:
        tnum.append("無地，有崩地震、川竭蝗蝻之象")
    if num % 10 == 0:
        tnum.append("無人，口舌妖言更相殘賊，疾疫、遷移、流亡")
    extra = _NUMDICT.get(num)
    if extra is not None:
        tnum.append(extra)
    return tnum


def _find_cal(yingyang: str, num: int) -> List[int]:
    table = {"陰": _YING_CAL, "陽": _YANG_CAL}[yingyang]
    return dict(zip(range(1, 73), table))[num]


# accnum-based markers (kintaiyi config.py); they take the raw 積年數 (accnum).


def _divide(num: int, division_num: int) -> int:
    while num % division_num == 0:
        num = num // division_num
    return num


def _wufu(acc: int) -> int:
    f = (acc + 250) % 225 % 45
    fv = f % 5
    if fv != 0:
        return fv
    return 5


def _kingfu(acc: int) -> Optional[str]:
    kingfu_num = acc % 20
    if kingfu_num == 0:
        kingfu_num = _divide(acc, 20)
        kingfu_num = kingfu_num % 20
    if kingfu_num > 16:
        kingfu_num -= 16
    return dict(zip(range(1, 17), _new_list(_GONG1, "戌"))).get(int(kingfu_num))


def _taijun(acc: int) -> Optional[str]:
    f = acc % 4
    if f == 0:
        f = _divide(acc, 4)
        f_v = f % 4
        if f_v > 16:
            f_v -= 16
        return dict(zip(range(1, 17), _GONG1)).get(f_v)
    return dict(zip(range(1, 5), list("子午卯酉"))).get(int(f))


def _flybird(acc: int) -> Any:
    f = acc % 8
    if f == 0:
        return "坤"
    return dict(zip(range(1, 9), [1, 8, 3, 4, 9, 2, 7, 6])).get(int(f))


def _threewind(acc: int) -> Optional[int]:
    f = acc % 9
    table = dict(zip(range(1, 9), [7, 2, 6, 1, 3, 9, 4, 8]))
    if f == 0:
        fv = acc // 9
        return fv % 9
    return table.get(int(f % 9)) if f % 9 != 0 else table.get(int(f / 9))


def _fivewind(acc: int) -> Optional[int]:
    f = acc % 29
    table = dict(zip(range(1, 10), [1, 3, 5, 7, 9, 2, 4, 6, 8]))
    if f == 0:
        fv = acc // 29
        return fv % 29
    return table.get(int(f % 9)) if f % 9 != 0 else table.get(int(f / 9))


def _eightwind(acc: int) -> Optional[int]:
    f = acc % 9
    table = dict(zip(range(1, 9), [2, 3, 4, 6, 7, 8, 9, 1]))
    if f == 0:
        fv = acc // 9
        return fv % 9
    return table.get(int(f % 9)) if f % 9 != 0 else table.get(int(f / 9))


def _bigyo(acc: int) -> Optional[int]:
    big_yo: float = (acc + 34) % 288
    if big_yo > 36:
        big_yo = big_yo / 36
    if big_yo < 6:
        big_yo = 6
    return dict(zip([7, 8, 9, 1, 2, 3, 4, 6], range(1, 9))).get(int(big_yo))


def _smyo(acc: int) -> int:
    small_yo = acc % 360
    sm = 0
    table = dict(zip([1, 2, 3, 4, 6, 7, 8, 9], range(1, 9)))
    if small_yo < 24:
        sm = small_yo % 3
    elif small_yo > 24:
        sm = small_yo % 24
        if small_yo > 10:
            sm = small_yo - 9
        if sm % 3 != 0:
            return table.get(int(sm % 3), 1)
        a = table.get(int(sm / 3))
        return a if a is not None else 1
    return table.get(int(sm % 3), 1)


def _yangjiu(lunar_year: int) -> Optional[str]:
    getyj = (lunar_year + 12607) % 4560 % 456 % 12
    if getyj >= 12:
        getyj = getyj % 12
        return dict(zip(range(1, 13), _new_list(_DI_ZHI, "寅"))).get(getyj)
    if getyj == 0:
        return dict(zip(range(1, 13), _new_list(_DI_ZHI, "寅"))).get(12)
    return dict(zip(range(1, 13), _new_list(_DI_ZHI, "寅"))).get(getyj)


def _baliu(lunar_year: int) -> Optional[str]:
    getbl = (lunar_year + 12607) % 4320 % 288 % 24
    if getbl > 12:
        getbl = (getbl - 12) % 12
        return dict(zip(range(1, 13), _new_list(_DI_ZHI, "卯"))).get(getbl)
    if getbl == 0:
        return dict(zip(range(1, 13), _new_list(_DI_ZHI, "酉"))).get(12)
    return dict(zip(range(1, 13), _new_list(_DI_ZHI, "酉"))).get(getbl)


# --------------------------------------------------------------------------- #
# 命法 engine (kintaiyi.Taiyi 人道命法 path: ji_style=0, taiyi_acumyear=0).    #
# --------------------------------------------------------------------------- #


class _TaiyiLife:
    """Faithful reproduction of kintaiyi's life-chart helpers for ji_style=0.

    Inputs are the four 干支 pillars (year/month/day/hour) as ``"干支"`` strings
    and the lunar year — all sourced from FateBridge's calendar, not sxtwl.
    """

    def __init__(
        self,
        year_gz: str,
        month_gz: str,
        day_gz: str,
        hour_gz: str,
        lunar_year: int,
    ) -> None:
        self._gz = [year_gz, month_gz, day_gz, hour_gz]
        self._lunar_year = lunar_year
        self._di_zhi = _DI_ZHI
        self._di_zhi_reversed = list(reversed(_DI_ZHI))
        self._jigod_map = dict(
            zip(self._di_zhi, _new_list(self._di_zhi_reversed, "寅"))
        )
        self._jigod_map_r = dict(
            zip(list(reversed(self._di_zhi)), _new_list(self._di_zhi, "酉"))
        )
        self._hegod_map = dict(
            zip(self._di_zhi, _new_list(self._di_zhi_reversed, "丑"))
        )

    # --- 積年數 (year-counting accnum) ------------------------------------- #
    def accnum(self) -> int:
        # tndict[0] = 10153917; ji_style 0 (年計): tn_c + lunar_year (+1 if <0)
        tn_c = 10153917
        return tn_c + self._lunar_year + (1 if self._lunar_year < 0 else 0)

    # --- 局數 -------------------------------------------------------------- #
    def kook(self) -> Dict[str, Any]:
        acc = self.accnum()
        k = acc % 72 or 72
        three_year = {0: "理天", 1: "理地", 2: "理人"}[
            {i: v for i, v in zip(range(1, 73), [0, 1, 2] * 24)}[k]
        ]
        # ji_style in (0,1,5,2) -> always 陽遁 for the life chart.
        dun = "陽遁"
        return {
            "文": f"{dun}{chinese_numeral(k)}局",
            "數": k,
            "年": three_year,
            "積年數": acc,
        }

    # --- 太歲/合神/計神 ---------------------------------------------------- #
    def taishui(self) -> str:
        return self._gz[0][1]

    def hegod(self) -> Optional[str]:
        return self._hegod_map.get(self.taishui())

    def jigod(self) -> Optional[str]:
        yy = self.kook()["文"][0]
        if yy == "陽":
            return self._jigod_map.get(self.taishui())
        return self._jigod_map_r.get(self.taishui())

    # --- 文昌(天目) -------------------------------------------------------- #
    def skyeyes(self) -> Optional[str]:
        kook = self.kook()
        return dict(zip(range(1, 73), _SKYEYES_DICT[kook["文"][0]])).get(kook["數"])

    def skyeyes_des(self) -> Optional[str]:
        kook = self.kook()
        return dict(zip(range(1, 73), _SKYEYES_SUMMARY[kook["文"][0]])).get(kook["數"])

    # --- 太乙落宮 ---------------------------------------------------------- #
    def ty(self) -> int:
        # arrangement = repeat(range(10), 3) -> [0,0,0,1,1,1,...,9,9,9]
        arrangement = [v for v in range(10) for _ in range(3)]
        arrangement_r = list(reversed(arrangement))
        yy_dict = {
            "陽": dict(
                zip(
                    range(1, 73),
                    (arrangement[3:15] + arrangement[18:]) * 3,
                )
            ),
            "陰": dict(
                zip(range(1, 73), (arrangement_r[:12] + arrangement_r[15:-3]) * 3)
            ),
        }
        kook = self.kook()
        return int(yy_dict[kook["文"][0]][kook["數"]])

    def ty_gong(self) -> Optional[str]:
        return dict(zip(range(1, 73), _TAIYI_PAI)).get(self.kook()["數"])

    # --- 始擊 -------------------------------------------------------------- #
    def sf(self) -> Optional[str]:
        return dict(zip(range(1, 73), _SF_LIST)).get(self.kook()["數"])

    # --- 定目 -------------------------------------------------------------- #
    def se(self) -> str:
        wc = self.skyeyes()
        hg = self.hegod()
        ts = self.taishui()
        assert wc is not None and hg is not None
        start = _new_list(_GONG1, hg)
        wc_order = _new_list(_GONG1, wc)
        return wc_order[len(start[: start.index(ts) + 1]) - 1]

    # --- 主算 -------------------------------------------------------------- #
    def home_cal(self) -> int:
        wancheong = self.skyeyes()
        assert wancheong is not None
        wc_order = self._wc_num_order(wancheong)
        taiyi = self.ty()
        return sum(wc_order[: wc_order.index(taiyi)])

    def _wc_num_order(self, marker: str) -> List[int]:
        wc_num = dict(zip(_new_list(_SIXTEEN, "亥"), _L_NUM))[marker]
        return _new_list(_NUM, wc_num)

    def home_general(self) -> int:
        kook = self.kook()
        home_cal = _find_cal(kook["文"][0], kook["數"])[0]
        result = {
            True: self.home_cal(),
            home_cal < 10: home_cal,
            home_cal % 10 == 0: 1,
            10 < home_cal < 20: home_cal - 10,
            20 < home_cal < 30: home_cal - 20,
            30 < home_cal < 40: home_cal - 30,
        }.get(True, 1)
        return int(result)

    def home_vgen(self) -> int:
        home_vg = self.home_general() * 3 % 10
        return 5 if home_vg == 0 else home_vg

    # --- 客算 -------------------------------------------------------------- #
    def away_cal(self) -> int:
        shiji = self.sf()
        assert shiji is not None
        sf_num = dict(zip(_new_list(_SIXTEEN, "亥"), _L_NUM))[shiji]
        taiyi = self.ty()
        sf_jc = shiji in _JC
        ty_jc = taiyi in _TYJC
        sf_jc1 = shiji in _JC1
        sf_order = _new_list(_NUM, sf_num)

        logic_map = {
            (True, False, False): lambda: (
                sum(sf_order[: sf_order.index(taiyi)]) + 1
                if sf_jc == ty_jc
                else sum(sf_order[: _JC.index(shiji) + 1]) + 1
            ),
            (False, False, True): lambda: (
                sum(sf_order[taiyi - 2 :])
                if sf_jc == ty_jc and 5 < taiyi < 7
                else (
                    sum(sf_order[: taiyi + 1])
                    if sf_jc == ty_jc and taiyi < 5
                    else sum(sf_order[: sf_order.index(taiyi)])
                )
            ),
            (False, True, False): lambda: (
                sum(sf_order[sf_order.index(taiyi) :])
                if sf_jc == ty_jc
                else sum(
                    sf_order[: sf_order.index(_TYJC[0])]
                    if ty_jc
                    else sf_order[: sf_order.index(taiyi)]
                )
            ),
            (True, True, False): lambda: (
                sum(sf_order[: sf_order.index(taiyi)]) + 1
                if sf_jc == ty_jc
                else sum(sf_order[:taiyi])
            ),
            (False, True, True): lambda: sum(sf_order[: sf_order.index(taiyi)]),
            (False, False, False): lambda: (
                taiyi if sf_num == taiyi else sum(sf_order[: sf_order.index(taiyi)])
            ),
        }
        return int(logic_map.get((sf_jc, ty_jc, sf_jc1), lambda: taiyi)())

    def away_general(self) -> int:
        kook = self.kook()
        away_cal = _find_cal(kook["文"][0], kook["數"])[1]
        result = {
            away_cal == 1: 1,
            away_cal < 10: away_cal,
            away_cal % 10 == 0: 5,
            10 < away_cal < 20: away_cal - 10,
            20 < away_cal < 30: away_cal - 20,
            30 < away_cal < 40: away_cal - 30,
        }.get(True, 5)
        return int(result)

    def away_vgen(self) -> int:
        away_vg = self.away_general() * 3 % 10
        return 5 if away_vg == 0 else away_vg

    # --- 定算 -------------------------------------------------------------- #
    def set_cal(self) -> int:
        setcal = self.se()
        se_num = dict(zip(_new_list(_SIXTEEN, "亥"), _L_NUM))[setcal]
        taiyi = self.ty()
        se_jc = setcal in _JC
        ty_jc = taiyi in _TYJC
        se_jc1 = setcal in _JC1
        se_order = _new_list(_NUM, se_num)

        logic_map = {
            (True, False, False): lambda: (
                1
                if sum(se_order[: se_order.index(taiyi)]) == 0
                else sum(se_order[: se_order.index(taiyi)]) + 1
            ),
            (False, False, True): lambda: sum(se_order[: se_order.index(taiyi)]),
            (False, True, False): lambda: sum(se_order[: se_order.index(taiyi)]),
            (True, True, False): lambda: sum(se_order[: se_order.index(taiyi)]) + 1,
            (False, True, True): lambda: (
                1
                if sum(se_order[: se_order.index(taiyi)]) == 0
                else sum(se_order[: se_order.index(taiyi)])
            ),
            (False, False, False): lambda: (
                taiyi if se_num == taiyi else sum(se_order[: se_order.index(taiyi)])
            ),
        }
        return int(
            logic_map.get(
                (se_jc, ty_jc, se_jc1),
                lambda: sum(se_order[: se_order.index(taiyi)]),
            )()
        )

    # --- 八將分布 ---------------------------------------------------------- #
    def skyyi(self) -> Optional[str]:
        return dict(zip(range(1, 73), itertools.cycle(_SKY_YI))).get(self.kook()["數"])

    def earthyi(self) -> Optional[str]:
        return dict(zip(range(1, 73), itertools.cycle(_EARTH_YI))).get(
            self.kook()["數"]
        )

    def fgd(self) -> Optional[str]:
        return dict(zip(range(1, 73), itertools.cycle(_FOUR_GOD))).get(
            self.kook()["數"]
        )

    def zhifu(self) -> Optional[str]:
        return dict(zip(range(1, 73), itertools.cycle(_ZHI_FU))).get(self.kook()["數"])

    # --- 君/臣/民基 -------------------------------------------------------- #
    def kingbase(self) -> Optional[str]:
        king_base = (self.accnum() + 250) % 360 // 30 or 1
        return dict(zip(range(1, 13), _new_list(self._di_zhi, "午"))).get(
            int(king_base)
        )

    def officerbase(self) -> Optional[str]:
        return dict(zip(range(1, 73), itertools.cycle(_OFFICER_BASE))).get(
            self.kook()["數"]
        )

    def pplbase(self) -> Optional[str]:
        return dict(
            zip(range(1, 73), itertools.cycle(_new_list(self._di_zhi, "申")))
        ).get(self.kook()["數"])


# --------------------------------------------------------------------------- #
# Public board assembly.                                                      #
# --------------------------------------------------------------------------- #


def build_taiyi_board(seed: MetaphysicsSeed, gender: str) -> Dict[str, Any]:
    """Build the 太乙統宗 人道命法 (life) board for ``seed``.

    Computation is byte-identical to ``kintaiyi.Taiyi(...).taiyi_life`` for the
    ``ji_style=0`` markers, given the same four pillars and lunar year.
    """
    lunar, _lunar_month, _lunar_day = require_lunar_month_day(seed, "太乙神数")
    lunar_year = lunar.get("year")
    if lunar_year is None:
        raise ValueError("太乙神数需要农历年，无法起盘：农历换算缺少年份")

    year_gz = f"{seed.pillars['year'][0]}{seed.pillars['year'][1]}"
    month_gz = f"{seed.pillars['month'][0]}{seed.pillars['month'][1]}"
    day_gz = f"{seed.pillars['day'][0]}{seed.pillars['day'][1]}"
    hour_gz = f"{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}"

    engine = _TaiyiLife(year_gz, month_gz, day_gz, hour_gz, int(lunar_year))

    acc = engine.accnum()
    kook = engine.kook()
    taiyi_num = engine.ty()
    taiyi_palace = engine.ty_gong()
    skyeyes = engine.skyeyes()  # 文昌 (天目) 地支宫
    sf = engine.sf()  # 始击
    se = engine.se()  # 定目
    home_cal = engine.home_cal()  # 主算
    away_cal = engine.away_cal()  # 客算
    set_cal = engine.set_cal()  # 定算
    home_general = engine.home_general()
    home_vgen = engine.home_vgen()
    away_general = engine.away_general()
    away_vgen = engine.away_vgen()
    hegod = engine.hegod()
    jigod = engine.jigod()
    kingbase = engine.kingbase()
    officerbase = engine.officerbase()
    pplbase = engine.pplbase()
    skyyi = engine.skyyi()
    earthyi = engine.earthyi()
    fgd = engine.fgd()
    zhifu = engine.zhifu()
    wufu = _wufu(acc)
    taishui = engine.taishui()

    # 文昌 lands on the 地支宫 returned by skyeyes; 太乙 lands on ty_gong (八卦/地支宫).
    wenchang_palace = skyeyes

    # --- per-palace star placements (palace_marks list, legacy 16-order) ---- #
    # Place each star marker on its palace label. Markers whose palace is a 八卦
    # name (乾坤艮巽) belong to those; the legacy 16-order uses 巽/坤/艮/乾 for the
    # four corners. num2gong markers (主大/客大 …) yield 八卦 labels too.
    marks: Dict[str, List[str]] = {palace: [] for palace in TAIYI_PALACE16_ORDER}

    def _place(palace: Optional[str], label: str) -> None:
        if palace in marks:
            marks[palace].append(label)

    _place(taiyi_palace, "太乙")
    _place(skyeyes, "文昌")
    _place(sf, "始击")
    _place(se, "定目")
    _place(taishui, "太歲")
    _place(hegod, "合神")
    _place(jigod, "計神")
    _place(kingbase, "君基")
    _place(officerbase, "臣基")
    _place(pplbase, "民基")
    _place(skyyi, "天乙")
    _place(earthyi, "地乙")
    _place(fgd, "四神")
    _place(zhifu, "值符")
    _place(_num2gong(wufu), "五福")
    _place(_num2gong(home_general), "主大")
    _place(_num2gong(home_vgen), "主參")
    _place(_num2gong(away_general), "客大")
    _place(_num2gong(away_vgen), "客參")

    yangjiu = _yangjiu(int(lunar_year))
    baliu = _baliu(int(lunar_year))
    _place(yangjiu, "陽九")
    _place(baliu, "百六")

    return {
        "style_label": "太乙统宗",
        "accumulation_label": f"命法积年数：{acc}",
        "rotation": "顺布",  # 人道命法 ji_style=0 恒为阳遁顺布
        "life_method": f"{gender}命",
        "taiyi_palace": taiyi_palace,
        "wenchang_palace": wenchang_palace,
        "core_board": {
            "main_calculation": kook["文"],
            "kook_number": kook["數"],
            "kook_year": kook["年"],
            "taiyi_position": f"太乙在{taiyi_palace}宫（{taiyi_num}）",
            "wenchang_position": f"文昌在{wenchang_palace}宫",
            "suijun": taishui,
            "heshen": hegod,
            "jishen": jigod,
            "shiji": sf,
            "dingmu": se,
            "main_count": home_cal,
            "guest_count": away_cal,
            "set_count": set_cal,
            "main_count_des": _cal_des(home_cal),
            "guest_count_des": _cal_des(away_cal),
            "main_general": home_general,
            "main_vice_general": home_vgen,
            "guest_general": away_general,
            "guest_vice_general": away_vgen,
            "junji": kingbase,
            "chenji": officerbase,
            "minji": pplbase,
            "tianyi": skyyi,
            "diyi": earthyi,
            "sishen": fgd,
            "zhifu": zhifu,
            "wufu": wufu,
        },
        "palace_marks": [
            {
                "palace": palace,
                "markers": sorted(dict.fromkeys(marks[palace])),
            }
            for palace in TAIYI_PALACE16_ORDER
        ],
    }


# --------------------------------------------------------------------------- #
# NOTICE / attribution.                                                       #
# --------------------------------------------------------------------------- #
# The 太乙 命法 algorithm and lookup tables in this module are a pure-Python
# port of `kintaiyi` by kentang2017 — https://github.com/kentang2017/kintaiyi
# — distributed under the MIT License (Copyright (c) 2023-2026 kentang2017).
# FateBridge vendors the algorithm only (no kintaiyi runtime dependency);
# calendar/节气 inputs come from FateBridge's own swisseph-backed engine. The MIT
# license is permissive and compatible with FateBridge's Apache-2.0 license; the
# required MIT copyright/permission notice is preserved here and in the NOTICE
# file at the repository root.
