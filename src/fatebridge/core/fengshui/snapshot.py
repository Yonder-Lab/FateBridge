"""Readable facts preserve the same method/subject scopes as structured JSON."""

from typing import Any, Dict, List, Tuple


def sections(result: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    output = [("起盘信息", [result["summary"], f"覆盖状态：{result['status']}"])]
    for name, layer in result["layers"].items():
        lines = [
            f"规则：{layer['ruleset']['ruleset_id']}@{layer['ruleset']['version']}"
        ]
        if name == "directions":
            lines.extend(
                f"{d} {p['trigram']} 宫数{p['palace_number']}"
                for d, p in layer["directions"].items()
            )
            if layer["bearing"]:
                b = layer["bearing"]
                lines.append(
                    f"输入方位：{b['bearing_degrees']}° {b['north_reference']} {b['direction']} {b['mountain']}"
                )
        elif name == "xuankong_natal":
            period = layer.get("period_context")
            if period:
                lines.append(
                    f"历史宅运：{period['number']}；定运依据：{period['basis']}；证据：{period['evidence']}"
                )
            lines.append(f"候选数：{len(layer['candidates'])}；状态：{layer['status']}")
            for chart in layer["candidates"]:
                lines.append(
                    f"{chart['candidate_id']} {chart['sitting']['name']}山{chart['facing']['name']}向；{chart['chart_mode']}；{chart['mode_reason']}"
                )
                lines.extend(
                    f"{d} 固定宫数{p['palace_number']} 运星{p['period_star_number']} 山星{p['mountain_star_number']} 向星{p['facing_star_number']}"
                    for d, p in chart["palaces"].items()
                )
                for role, trace in chart["trace"].items():
                    lines.append(
                        f"{role} 原星{trace['seed_star_number']} 同元龙{trace['mapped_mountain']} {trace['polarity']} {trace['flight']} 入中{trace['center_star_number']}；五黄借法：{trace['five_yellow_policy']}"
                    )
        elif name == "annual_stars":
            if layer.get("effective_year") is not None:
                lines.append(
                    f"有效年：{layer['effective_year']}；入中：{layer['center_star_number']}"
                )
                lines.extend(
                    f"{d} 固定宫数{p['palace_number']} 年星{p['annual_star_number']} {p['annual_star']['name']}"
                    for d, p in layer["palaces"].items()
                )
                lines.append(
                    f"有效期：{layer['time_context']['valid_from']} 至 {layer['time_context']['valid_until']}（结束不含）"
                )
        elif name == "jinsuo":
            lines.extend(
                f"{d} 偏好{p['preferred_classification']}"
                for d, p in layer["preferences"].items()
            )
            lines.extend(
                f"{f['object_id']} {f['direction']} {f['classification']}：{f['finding']}；依据：{f['evidence']}"
                for f in layer["feature_findings"]
            )
        elif name in {"bazhai", "minggua"}:
            house = layer.get("house")
            if house:
                lines.append(
                    f"宅卦：{house['sitting_trigram']}；住宅：{house['object_id']}"
                )
                lines.extend(
                    f"宅盘 {d} {p['star']['name']} {p['star']['polarity']}"
                    for d, p in house["sectors"].items()
                )
            people = layer.get("occupants", [layer] if name == "minggua" else [])
            for person in people:
                for candidate in person["candidates"]:
                    lines.append(
                        f"住户{person['subject_id']} {candidate['gender_convention']}：有效生年{person['time_context']['effective_year']}；原始数{candidate['raw_number']}；寄宫后{candidate['palace_number']} {candidate['trigram']}；{person['status']}"
                    )
                    lines.extend(
                        f"个人盘 {person['subject_id']} {d} {p['star']['name']} {p['star']['polarity']}"
                        for d, p in candidate["sectors"].items()
                    )
            lines.extend(
                f"{f['subject_kind']}:{f['subject_id']} 对象{f['object_id']} {f['aspect']} {f['direction']} {f['star']['name']}；符合用途约定：{f['matches_convention']}"
                for f in layer.get("placement_findings", [])
            )
        output.append(
            (
                {
                    "directions": "公共方位",
                    "minggua": "住户命卦",
                    "bazhai": "八宅分层",
                    "annual_stars": "年度飞星",
                    "jinsuo": "砂水判定",
                    "xuankong_natal": "玄空宅盘",
                }[name],
                lines,
            )
        )
    output.append(
        (
            "冲突清单",
            [
                f"{c['direction']} {c['kind']}：{c['resolution']}"
                for c in result["conflicts"]
            ]
            or ["无已确认的方向差异；各方法保持独立作用范围"],
        )
    )
    output.append(
        (
            "覆盖范围",
            [
                "缺失输入：" + "、".join(result["coverage"]["missing_inputs"]),
                "未实现层：" + "、".join(result["coverage"]["unavailable_layers"]),
            ],
        )
    )
    output.append(
        (
            "规则来源",
            [
                f"{ruleset['ruleset_id']}@{ruleset['version']} {source['source_id']} {source['title']} {source['url']}；范围：{source['scope']}"
                for ruleset in result["rulesets"]
                for source in ruleset["sources"]
            ],
        )
    )
    return output
