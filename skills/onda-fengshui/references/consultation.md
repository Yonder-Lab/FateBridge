# 风水咨询闭环

本参考只组织现有工具；参数以连接中的定义为准，规则以返回的版本、作用域和来源为准。无需用户先提供全套住宅与出生资料。

## 按请求核对资料

| 请求层 | 必要事实及如何处理缺失 |
| --- | --- |
| 对象方向／个人匹配 | 对象用途、已确认位置或朝向、适用使用人；住户按命卦的三选一生年路径。缺宅向仍可保留个人关系；对象未知方位省略，禁止占位臆造 |
| 室内形态 | 具体对象及入口／通道／背靠等已确认观察与依据；可独立 `methods=[]`。只保留用户确认的粒度，未知布尔项省略 |
| 桌面作者法 | 矩形、坐者使用的近侧桌沿、用户的事业／丰盛目标、物件代表属性及依据；其他形状／目标没有对应处方，不能硬改事实 |
| 金锁基础层 | 环境特征的方位、砂／水／混合／未知分类及依据；照片或物品名称不证明分类 |
| 年盘 | 有效年或含时区查询时刻；采用立春边界，不把公历年自动当有效年。年度物件作者规则须显式选择且限支持年份 |
| 玄空 | 磁北宅向及测量不确定度、历史定运事件和依据、明确版本；资料不足就保留候选／缺失，不用当前年份补齐 |

行动约束与观察分别保存：能否搬位、转向、移动物件、新增，预算，共用范围，固定对象／不可用区域。限制不意味着任何入口、镜面、横梁或尖角存在／不存在。

`entrance_position`、`passage_position`、`window_position` 使用 `front/front_left/front_right/left/right/back/back_left/back_right` 这八种相对位置，未知省略；中文“左侧”不能自行拼成 `left_side_of_bed` 等值。定义仍以当前 schema 为准，校验失败按 issues 的路径和允许值修正一次，不重复失败输入。

## 桌面坐标与证据

桌面均分三行三列：`near` 靠身体、`far` 远离身体；`left/right` 以坐着使用者为基准。近左/近中/近右对应 `near_left/near_center/near_right`，中排对应 `middle_left/middle_center/middle_right`，远排对应 `far_left/far_center/far_right`。不要把房间门口或罗盘方向作为桌面分区锚点。

`surface_layouts` 每项显式 `ruleset_id=desktop_bagua_btb_v1`、`shape=rectangular`、`anchor=seated_near_edge`、`goal=career|abundance`，记录边界的 `observation_basis` 和 `evidence`。每件物品要有 `object_id,label,representation,observation_basis,evidence`；representation 可为 `living_plant/fresh_flowers/water_image/dark_accessory/other/unknown`。不按物品名推元素。

物件属性确认与位置确认是两件事。`zone` 与 `zone_observation_basis` 成对，左右已知但近远未知时不填九格位置；照片所见用 `image_observed`，用户确认用 `user_confirmed`，实际测量用 `measured`。活植物确认不自动确认其位置。

`surface_constraints` 关联同一桌面 ID。`can_move_items/can_add_items` 是许可；`locked_item_ids` 是固定物件；`unavailable_zones` 是不可用区；`feasible_zones` 只列用户明确确认能容纳对象且不遮视野、不影响操作的区域。不从照片空白或允许移动扩展可行区域，未确认时省略。

## 选择和读取结果

按问题显式 `methods`；只做形态／桌面可用空列表。`form_observations` 可以独立存在，不构造无方位的 `placements`。位置和朝向各自观察，给布局计算时 `analyze_layout=true`。元素方案 `element_adjustments` 必须绑定已算对象、方法、作用域和 `drain/support` 目标，不能按“缺五行”开处方。

首轮投影使用工具已公布字段，并为所有风水解读追加 `rulesets` 与 `rule_trace`，以取得本次作者版本和可引用来源；单独命卦也适用。按请求加读这些分支，而不是一次铺满全量：

- 总体状态／覆盖：`status`、`coverage`、`layout_analysis.calculation_scope`、`layout_analysis.missing_inputs`、`layout_analysis.unsupported_queries`、`layout_analysis.limitations`。
- 方向行动：`layout_analysis.placement_findings`、`layout_analysis.adjustment_options`、`layout_analysis.environment_adjustments`；个人关系需要时加 `layers.bazhai.occupants`。
- 形态／元素／年度：`layout_analysis.form_analysis`、`layout_analysis.element_remedies`、`layout_analysis.annual_remedies`、`layout_analysis.supplement_statuses`。
- 桌面物件：`layout_analysis.surface_analysis`，逐对象看覆盖与行动状态。
- 来源／分歧：`rulesets`、`rule_trace`、`conflicts`、`layout_analysis.method_disagreements`；不能把不同流派关系平均为总分。

字段裁剪缺了关键理由或来源时，再针对缺的分支读取，不能凭常识补成计算结论。结果 partial 是合法缺失，不能当成功完成所有请求，也不以相同输入重复尝试。

## 交付与复核

建议按对象说明：当前事实及依据、方法／作者版本、规则来源、改到哪里／保留什么、条件与允许动作。方向候选不是可执行动作；先筛搬转限制、共用方向与实际空间。没有共同方向或没有可行方案时解释权衡，不以摆件替代方向结论。

桌面返回 `ready` 才有已确认物件／边界、许可与可行区；`conditional_option` 写明需确认的条件，`candidate_only` 待核对照片事实，`blocked` 保留约束，`no_independent_placement_rule` 说明无独立摆放规则。无规则也属于完整覆盖的一种结果，但不能称为“算出吉位”。

来源分层：八宅／金锁／年度与历史玄空引用[基础合同](../../../docs/fengshui.md)和[玄空合同](../../../docs/fengshui-xuankong.md)的原典／作者版本；室内形态、元素及年度处方引用[证据审查](../../../docs/fengshui-layout-rules-2026-10-14.md)；桌面现代 BTB 引用[作者规则](../../../docs/fengshui-surface-rules.md)的 Anjie Cho、Tori McBrien。每条行动采用实际返回的来源，不把另一流派文章当这条规则的证明。规则数据含检索记录及散列；来源可追溯不等于现实效力已验证。

交付后保留未解决项目、缺失事实和复核点。后续更正更新输入，维护同一 trace 与父 run；只解释不重算。物理调整是否落实、能否看见入口、是否有遮挡等可以核验，事业或财富改善不能由布局引擎确认。
