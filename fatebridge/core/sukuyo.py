#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""宿曜（二十七宿）双人相性 —— 三九の秘法。

宿曜占星术以双方的本命宿（月所在之宿）为基准，按二十七宿的循环距离判定关系：
本命宿为「命」，逆向第 9 宿为「業」、第 18 宿为「胎」，其余以「栄・衰・安・危・
成・壊・友・親」按近/中/遠三段距离循环填充。关系是有向的（A 看 B 与 B 看 A 互
为配对：栄↔親、衰↔友、安↔壊、危↔成、業↔胎）。

本模块只承载纯算法（无 I/O），本命宿由调用方（宿占盘的月宿）提供。

距离与方向已用可核验实例锁定：本命宿=斗 时，親 落在 胃(近)/張(中)/箕(遠)，
仅在「前向距离 d=(other-self) mod 27」下，宿名与近中远三段同时吻合。
参考：
- 日本占い師協会 https://www.uranai.org/shukuyo/shukuyo-column10/
- JAAMP https://www.domap.net/uranai/syukuyo/syukuyo-column08/
"""

from typing import Any, Dict, List, Optional

from .local_techniques import SU28_NAMES

# 二十七宿循环顺序：在中式二十八宿黄道序列上去掉牛宿。
SU27_ORDER: List[str] = [name for name in SU28_NAMES if name != "牛"]

# 三九の秘法关系模板：每九宿一组，组首依次为 命/業/胎，组内其余八宿固定为
# 栄・衰・安・危・成・壊・友・親。共 27 项。
_GROUP_HEADS = ["命", "業", "胎"]
_GROUP_TAIL = ["栄", "衰", "安", "危", "成", "壊", "友", "親"]
RELATION_TEMPLATE: List[str] = []
for _head in _GROUP_HEADS:
    RELATION_TEMPLATE.append(_head)
    RELATION_TEMPLATE.extend(_GROUP_TAIL)

# 关系 → 配对类型（合并方向后的六类相性）。
RELATION_PAIR: Dict[str, str] = {
    "命": "命",
    "業": "業胎",
    "胎": "業胎",
    "栄": "栄親",
    "親": "栄親",
    "衰": "友衰",
    "友": "友衰",
    "安": "安壊",
    "壊": "安壊",
    "危": "危成",
    "成": "危成",
}

RELATION_MEANING: Dict[str, str] = {
    "命": "同宿同心，缘分极深，性格与价值取向相近。",
    "業": "業胎之缘，前世今生般的深缘；業偏过去世的牵引与课题。",
    "胎": "業胎之缘，胎承安心与守护，带来被接纳的治愈感。",
    "栄": "栄親为最佳相性之一；栄主繁荣，更多是你给予对方提携与好处。",
    "親": "栄親为最佳相性之一；親主亲爱，更多是你受到对方的善待与尊重。",
    "衰": "友衰相性；在磨练中彼此成长，过程偏消耗、需要付出。",
    "友": "友衰相性；亦师亦友，互相学习，相处自然。",
    "安": "安壊相性；你从对方处获得安定，但暗藏被打破的风险。",
    "壊": "安壊相性；你对这段看似稳定的关系，可能带来突然的破坏。",
    "危": "危成相性；异质而充满挑战，克服之后可得大成就。",
    "成": "危成相性；伴随危机与考验，成则收获满足与突破。",
}

# 业/胎/命没有距离概念；其余按所在「九组」分近(1)/中(2)/遠(3)。
_NO_DISTANCE_OFFSETS = {0, 9, 18}


def _distance_grade(offset: int) -> Optional[str]:
    if offset in _NO_DISTANCE_OFFSETS:
        return None
    if 1 <= offset <= 8:
        return "近"
    if 10 <= offset <= 17:
        return "中"
    return "遠"


def su28_to_su27(name: str, longitude: Optional[float] = None) -> str:
    """把宿占盘的二十八宿宿名映射到二十七宿。

    牛宿在二十七宿体系中不存在；当月宿恰好落在牛宿时，按其黄经在牛宿等分带
    内的位置就近归入相邻宿（前半→斗，后半→女）。缺经度信息时默认归入斗。
    """
    if name not in SU28_NAMES:
        raise ValueError(f"未知宿名：{name!r}")
    if name != "牛":
        return name

    niu_index = SU28_NAMES.index("牛")
    span = 360.0 / 28.0
    midpoint = niu_index * span + span / 2.0
    if longitude is None:
        return "斗"
    return "斗" if (float(longitude) % 360.0) < midpoint else "女"


def relation_between_su27(self_su27: str, other_su27: str) -> Dict[str, Any]:
    """给定双方的二十七宿，返回 self 看 other 的有向关系。"""
    if self_su27 not in SU27_ORDER:
        raise ValueError(f"非二十七宿宿名：{self_su27!r}")
    if other_su27 not in SU27_ORDER:
        raise ValueError(f"非二十七宿宿名：{other_su27!r}")

    offset = (SU27_ORDER.index(other_su27) - SU27_ORDER.index(self_su27)) % 27
    relation = RELATION_TEMPLATE[offset]
    return {
        "relation": relation,
        "pair": RELATION_PAIR[relation],
        "distance": _distance_grade(offset),
        "offset": offset,
        "meaning": RELATION_MEANING[relation],
    }


def sukuyo_relation(
    self_su: str,
    other_su: str,
    self_longitude: Optional[float] = None,
    other_longitude: Optional[float] = None,
) -> Dict[str, Any]:
    """接受宿占盘的二十八宿宿名，映射到二十七宿后返回有向关系。"""
    self_su27 = su28_to_su27(self_su, self_longitude)
    other_su27 = su28_to_su27(other_su, other_longitude)
    result = relation_between_su27(self_su27, other_su27)
    result.update(
        {
            "self_su28": self_su,
            "other_su28": other_su,
            "self_su27": self_su27,
            "other_su27": other_su27,
        }
    )
    return result
