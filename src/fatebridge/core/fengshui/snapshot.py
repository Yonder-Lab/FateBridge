"""Readable facts preserve the same method/subject scopes as structured JSON."""

from typing import Any, Dict, List, Tuple


def sections(result: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    output = [("起盘信息", [result["summary"], f"覆盖状态：{result['status']}"])]
    if "method_policy" in result:
        policy = result["method_policy"]
        output.append(
            (
                "方法选择",
                [
                    "主法参考：九宫飞星、金锁玉关、八宅；局部按此前两法优先，实际计算仅含已选层。",
                    "本次计算顺序：" + "、".join(policy["selected_method_order"]),
                    "八字、紫微及周围人的个人喜忌不代入客观环境；八宅个人命卦独立。",
                    "优先级表示审查顺序，不产生综合评分或抵消。",
                    f"现状优先方法审查：{policy['priority_review_status']}；"
                    f"未覆盖优先法：{'、'.join(policy['priority_missing_methods']) or '无'}；"
                    "与已选计算完成状态分别读取，显式排除不追资料。",
                ],
            )
        )
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
            interpretation = layer.get("interpretation")
            if interpretation is not None:
                lines.append(
                    f"有限解释：{interpretation['ruleset_id']}；状态{interpretation['status']}；"
                    f"当前评价运{interpretation['current_period_context']['number']}，不重置历史宅运"
                )
                for candidate in interpretation["candidates"]:
                    lines.append(f"解释候选：{candidate['candidate_id']}")
                    for direction, palace in candidate["palaces"].items():
                        pair = palace["ordered_pair"]
                        forms = palace["external_form_analysis"]
                        lines.append(
                            f"{direction} 山星/向星五行：{pair['relationship']}；"
                            f"山形条件{forms['mountain']['status']}；水形条件{forms['water']['status']}"
                        )
                    for use in candidate["placement_findings"]:
                        lines.append(f"用途对象{use['object_id']}：{use['status']}")
                lines.extend(interpretation["limitations"])
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
    if "layout_analysis" in result:
        layout = result["layout_analysis"]
        lines = [
            f"布局计算状态：{layout['status']}；范围：{layout['calculation_scope']}"
        ]
        for option in layout["adjustment_options"]:
            agreement = (
                "尚无已确认作用域"
                if option["resolution"] == "no_confirmed_scope"
                else "、".join(option["agreed_matching_directions"])
                or "已确认作用域之间没有共同匹配方位"
            )
            lines.append(
                f"对象{option['object_id']} {option['aspect']} 当前{option['current_direction']}；已确认作用域共同匹配方位：{agreement}"
            )
            if option.get("action_status") == "blocked":
                lines.append(
                    f"对象{option['object_id']} {option['aspect']}调整受限：用户明确禁止相应动作"
                )
            for scope in option["scopes"]:
                lines.append(
                    f"{scope['subject_kind']}:{scope['subject_id']} 候选：{scope['candidate_only']}；匹配方位：{'、'.join(scope['matching_directions'])}"
                )
        for finding in layout.get("form_analysis", {}).get("findings", []):
            lines.append(
                f"对象{finding['object_id']} 形态判定：{finding['finding']}；依据：{finding['evidence']}"
            )
            lines.extend(
                f"{check['criterion']}：{check['finding']}；规则：{check['rule_id']}"
                for check in finding["checks"]
            )
        for finding in layout.get("element_remedies", []) + layout.get(
            "annual_remedies", {}
        ).get("findings", []):
            lines.append(
                f"对象{finding['object_id']} 元素方案：{finding['status']}；元素：{finding.get('introduced_element', '未生成')}；范围：{finding.get('application_scope', '条件不足或不适用')}"
            )
        for surface in layout.get("surface_analysis", {}).get("findings", []):
            lines.append(
                f"桌面{surface['object_id']} 目标{surface['goal']}；参考系：坐者近侧桌沿，不是罗盘落宫"
            )
            for option in surface["action_options"]:
                lines.append(
                    f"物件{option['item_id'] or '可选代表物'} {option['action']} → {option['to_zone_label']}；"
                    f"{option['status']}；规则{option['rule_id']}；{option['traditional_reason']}"
                )
            for item in surface["item_findings"]:
                if item["status"] == "no_independent_placement_rule":
                    lines.append(
                        f"物件{item['object_id']}：没有独立摆放规则，不按名称推断五行或吉侧"
                    )
        for proposal in layout.get("alternatives_analysis", {}).get("findings", []):
            lines.append(
                f"对象{proposal['object_id']} 候选{proposal['candidate_id']}：{proposal['status']}；计算{proposal['calculation_status']}；新位置形态独立核对，未沿用旧观察"
            )
        context = layout.get("environmental_context")
        for finding in layout.get("interior_analysis", {}).get("findings", []):
            lines.append(
                f"室内关系{finding['source_object_id']} → {finding['target_object_id']}："
                f"{finding['kind']}，{finding['status']}；规则{finding['rule_id']}；"
                f"动作{finding['action_status']}，按各对象独立核对。"
            )
        for finding in layout.get("material_analysis", {}).get("findings", []):
            lines.append(
                f"材质器形{finding['object_id']}：{finding['finding']}；"
                f"材料资格{finding['material_eligibility']}，颜色资格{finding['colour_eligibility']}；"
                "器形参考不等于实际尖角关系，代表物资格不认证摆位。"
            )
        if context is not None:
            orientation = context["orientation_review"]
            lines.append(
                f"环境上下文：{context['status']}；实际分宫确认："
                f"{orientation['physical_sector_binding_allowed']}；人物象征对应不代替环境方位。"
            )
            for member in context["household_correspondences"]:
                for association in member["associations"]:
                    lines.append(
                        f"家庭成员{member['subject_id']}：主宫{association['primary_palace']}，"
                        f"对宫{association['opposite_palace']}为次级关注；"
                        f"实际落宫{association['physical_sector_binding']}；"
                        f"作用域{association['scope']}，非八宅个人命卦，不据此推断事件。"
                    )
            for influence in context["floor_review"]["influences"]:
                for scope in influence["subject_scope"]:
                    lines.append(
                        f"楼层影响{influence['influence_id']} 对{scope['subject_id']}："
                        f"{scope['status']}；共同因素不取消。"
                    )
            for finding in context["environment_findings"]:
                lines.append(
                    f"环境对象{finding['object_id']} {finding['feature']}："
                    f"{finding['finding']}；无独立规则不编绝对禁忌。"
                )
            lines.extend(context["limitations"])
        lines.extend(layout["limitations"])
        output.append(("布局计算", lines))
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
                *(
                    [
                        "请求整体状态："
                        + result["coverage"]["requested_analysis_status"],
                        "布局缺失输入："
                        + "、".join(result["coverage"]["layout_missing_inputs"]),
                    ]
                    if "layout_status" in result["coverage"]
                    else []
                ),
                "未实现层：" + "、".join(result["coverage"]["unavailable_layers"]),
                *(
                    [
                        (
                            "场景范围：仅已提交对象与所选规则，不代表全宅审查；本次玄空只含有限五行、当令外局与床门条件，完整形势、门主灶结构及81组合断法尚未覆盖"
                            if result.get("layers", {})
                            .get("xuankong_natal", {})
                            .get("interpretation")
                            is not None
                            else "场景范围：仅已提交对象与所选规则，不代表全宅审查；完整形势、门主灶结构及宅盘组合解释尚未覆盖"
                        )
                    ]
                    if "scene_scope" in result["coverage"]
                    else []
                ),
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
