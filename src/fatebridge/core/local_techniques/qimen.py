"""
Qi Men (奇门) snapshot rendering and options over a metaphysics seed.

Pure relocation from the package facade.
"""

from __future__ import annotations

import copy

from ..divination import build_hexagram
from ..metaphysics import (
    QIMEN_DOOR_CODE_BY_DISPLAY,
    QIMEN_DOOR_TO_TRIGRAM,
    QIMEN_STAR_CODE_BY_DISPLAY,
    build_qimen_board,
)
from .chart import (
    SANSHI_REFERENCES,
    Any,
    Dict,
    List,
    MetaphysicsSeed,
    Optional,
    _build_qimen_palace_overview_lines,
    _join_lines,
    _normalize_mode,
    _option_value,
    _render_qimen_palace_sections,
    _render_snapshot_text,
    _rotate_items,
)

QIMEN_NINE_GRID_LAYOUT = (
    ("巽四宫", "离九宫", "坤二宫"),
    ("震三宫", "中五宫", "兑七宫"),
    ("艮八宫", "坎一宫", "乾六宫"),
)


def _build_qimen_nine_grid_lines(qimen: Dict[str, Any]) -> List[str]:
    palace_map = {
        palace.get("name"): palace
        for palace in qimen.get("palaces", []) or []
        if isinstance(palace, dict) and palace.get("name")
    }
    rows: List[str] = []
    for row in QIMEN_NINE_GRID_LAYOUT:
        cells: List[str] = []
        for palace_name in row:
            palace = palace_map.get(palace_name, {})
            cell = (
                f"{palace_name}："
                f"{palace.get('door', '无')}/"
                f"{palace.get('star', '无')}/"
                f"{palace.get('god', '无')}"
            )
            if palace.get("content_palace") and (
                palace.get("content_palace") != palace.get("name")
                or palace.get("content_trigram") != palace.get("trigram")
            ):
                cell += (
                    f" <- {palace.get('content_palace', '无')}/"
                    f"{palace.get('content_trigram', '无')}"
                )
            cells.append(cell)
        rows.append(" | ".join(cells))
    return rows


def build_qimen_snapshot_text(*, seed: MetaphysicsSeed, qimen: Dict[str, Any]) -> str:
    zhifu = qimen.get("zhifu") or {}
    zhishi = qimen.get("zhishi") or {}
    palace_map = {
        palace.get("name"): palace
        for palace in qimen.get("palaces", []) or []
        if isinstance(palace, dict) and palace.get("name")
    }
    zhifu_palace = palace_map.get(zhifu.get("palace"), {})
    zhishi_palace = palace_map.get(zhishi.get("palace"), {})

    def _content_note(item: Dict[str, Any]) -> str:
        if not item.get("content_palace"):
            return ""
        if item.get("content_palace") == item.get("palace") and item.get(
            "content_trigram"
        ) == item.get("trigram"):
            return ""
        return (
            f"；内容来源：{item.get('content_palace', '无')} / "
            f"{item.get('content_trigram', '无')}"
        )

    sections = [
        (
            "起盘信息",
            _join_lines(
                [
                    f"农历：{(seed.calendar_context.get('lunar_calendar') or {}).get('display') or '无'}",
                    f"直接时间：{seed.calendar_context['solar_datetime']}",
                    f"四柱：{seed.pillars['year'][0]}{seed.pillars['year'][1]}年/{seed.pillars['month'][0]}{seed.pillars['month'][1]}月/{seed.pillars['day'][0]}{seed.pillars['day'][1]}日/{seed.pillars['hour'][0]}{seed.pillars['hour'][1]}时",
                    "时间算法：本地节气换月",
                    "换日：子初换日",
                ]
            ),
        ),
        (
            "盘型",
            _join_lines(
                [
                    f"当前节气：{(seed.calendar_context.get('current_solar_term') or {}).get('name', '无')}",
                    f"下个节气：{(seed.calendar_context.get('next_solar_term') or {}).get('name', '无')}",
                    f"盘型：{qimen.get('ju_text', '无')}",
                    f"遁型：{qimen.get('dun_type', '无')}",
                    f"三元：{qimen.get('yuan', '无')}",
                    f"符头：{qimen.get('fu_tou', '无')}",
                    f"旬首：{qimen.get('xun_head', '无')}",
                    f"空亡：{qimen.get('kongwang', '无')}",
                ]
            ),
        ),
        (
            "盘面要素",
            _join_lines(
                [
                    (
                        f"值符：{zhifu.get('star', '无')}在{zhifu.get('palace', '无')}"
                        + _content_note(zhifu)
                    ),
                    (
                        f"值使：{zhishi.get('door', '无')}在{zhishi.get('palace', '无')}"
                        + _content_note(zhishi)
                    ),
                    f"布局：{qimen.get('layout', 'direct')}",
                    f"参考句：{qimen.get('reference', '无')}",
                ]
            ),
        ),
        (
            "奇门演卦",
            _join_lines(
                [
                    f"伏使卦：{(qimen.get('fushi_hexagram') or {}).get('name', '无')} / {(qimen.get('fushi_hexagram') or {}).get('binary_code', '无')}",
                    f"值符宫门卦：{(zhifu_palace.get('door_hexagram') or {}).get('name', '无')}",
                    f"值使宫门卦：{(zhishi_palace.get('door_hexagram') or {}).get('name', '无')}",
                ]
            ),
        ),
        ("八宫详解", _join_lines(_build_qimen_palace_overview_lines(qimen)) or "无"),
        ("九宫方盘", _join_lines(_build_qimen_nine_grid_lines(qimen)) or "无"),
        *_render_qimen_palace_sections(qimen),
    ]
    return _render_snapshot_text(sections)


def build_qimen_with_options(
    seed: MetaphysicsSeed, options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    board = build_qimen_board(seed)
    normalized_options = dict(options or {})
    if not normalized_options:
        return board

    layout = (
        str(_option_value(normalized_options, "layout") or "direct").strip().lower()
    )
    shift = _normalize_mode(
        _option_value(normalized_options, "palaceShift", "palace_shift"),
        default=0,
    )
    if layout in {"fly", "fei"}:
        shift += max(1, int(board.get("ju_number", 1)) % 9)
    reverse = layout in {"mirror", "reverse"}

    palaces = board.get("palaces", []) or []
    content_sequence = [
        {
            "content_palace": palace.get("name"),
            "content_trigram": palace.get("trigram"),
            "heaven_stem": palace.get("heaven_stem"),
            "earth_stem": palace.get("earth_stem"),
            "god": palace.get("god"),
            "door": palace.get("door"),
            "star": palace.get("star"),
        }
        for palace in palaces
        if isinstance(palace, dict)
    ]
    if reverse:
        content_sequence = list(reversed(content_sequence))
    content_sequence = _rotate_items(content_sequence, shift)

    transformed_palaces: List[Dict[str, Any]] = []
    for palace, content in zip(palaces, content_sequence):
        updated_palace = copy.deepcopy(palace)
        updated_palace.update(content)
        slot_trigram = palace.get("trigram", updated_palace.get("trigram"))
        updated_palace["trigram"] = slot_trigram
        palace_trigram = slot_trigram if slot_trigram != "中" else "坤"
        door_hexagram = build_hexagram(
            upper_name=palace_trigram,
            lower_name=QIMEN_DOOR_TO_TRIGRAM.get(updated_palace.get("door"), "坤"),
        )
        updated_palace["door_hexagram"] = {
            "name": door_hexagram["name"],
            "binary_code": door_hexagram["binary_code"],
        }
        transformed_palaces.append(updated_palace)

    zhifu_star = (board.get("zhifu") or {}).get("star")
    zhishi_door = (board.get("zhishi") or {}).get("door")
    zhifu_palace = next(
        (palace for palace in transformed_palaces if palace.get("star") == zhifu_star),
        transformed_palaces[0] if transformed_palaces else {},
    )
    zhishi_palace = next(
        (palace for palace in transformed_palaces if palace.get("door") == zhishi_door),
        transformed_palaces[0] if transformed_palaces else {},
    )
    fushi_hexagram = build_hexagram(
        upper_name=(
            zhifu_palace.get("trigram", "坤")
            if zhifu_palace.get("trigram") != "中"
            else "坤"
        ),
        lower_name=QIMEN_DOOR_TO_TRIGRAM.get(zhishi_palace.get("door"), "坤"),
    )

    transformed_board = copy.deepcopy(board)
    transformed_board.update(
        {
            "layout": layout,
            "options_applied": {
                "layout": layout,
                "palaceShift": shift,
                "reverse": reverse,
            },
            "palaces": transformed_palaces,
            "zhifu": {
                "star": zhifu_palace.get("star"),
                "palace": zhifu_palace.get("name"),
                "trigram": zhifu_palace.get("trigram"),
                "content_palace": zhifu_palace.get(
                    "content_palace", zhifu_palace.get("name")
                ),
                "content_trigram": zhifu_palace.get(
                    "content_trigram", zhifu_palace.get("trigram")
                ),
                "code": QIMEN_STAR_CODE_BY_DISPLAY.get(zhifu_palace.get("star")),
            },
            "zhishi": {
                "door": zhishi_palace.get("door"),
                "palace": zhishi_palace.get("name"),
                "trigram": zhishi_palace.get("trigram"),
                "content_palace": zhishi_palace.get(
                    "content_palace", zhishi_palace.get("name")
                ),
                "content_trigram": zhishi_palace.get(
                    "content_trigram", zhishi_palace.get("trigram")
                ),
                "code": QIMEN_DOOR_CODE_BY_DISPLAY.get(zhishi_palace.get("door")),
            },
            "fushi_hexagram": {
                "name": fushi_hexagram["name"],
                "binary_code": fushi_hexagram["binary_code"],
            },
            "reference": SANSHI_REFERENCES[shift % len(SANSHI_REFERENCES)],
        }
    )
    return transformed_board
