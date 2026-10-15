# 风水九条要求系统复审（2026-10-15）

本报告对应首轮专家意见迭代之后的再次系统审查：沿用户最初九条，核对计算路径、REST／MCP／CLI 合同、首轮字段、覆盖状态、技能与来源说明。审查目标是发现一般性事实／作用域问题，不以某个案例的吉凶或建议数量作为通过标准。

[首轮迭代与验收](fengshui-expert-iteration-2026-10-15.md)的 Linux 2917 项、macOS 2829 项通过／88 跳过及 golden 87/87，均是其登记源码快照的**历史证据**。本轮新增反例与修复后，不能将首轮数值当作当前工作区、当前安装包或新 Desktop 连接的验证。本报告下方的本轮统一验收由主 Agent 在最终源码冻结后补齐。

## 九条一致性矩阵

| 要求 | 计算与实际输出 | 工具合同与技能路径 | 本轮判断及保留边界 |
| --- | --- | --- | --- |
| 1. 主法为九宫飞星、金锁、八宅 | `method_policy.method_priority` 保留三法；`annual_stars` 与 `xuankong_natal` 为飞星家族独立层，金锁与八宅各自计算 | `src/fatebridge/services/catalog/fengshui.py`、`src/fatebridge/data/agent_examples.json`；技能“工位与家居选法” | 已实现主法及方法分层；没有三法总分。用户选某法不代表其所有传统分支均覆盖 |
| 2. 局部先飞星、次金锁 | 自动选法按已有事实展开，显式列表优先；`priority_review_status`、每法 `not_selected_reason` 与已选计算状态分开 | `src/fatebridge/core/fengshui/method_policy.py`；`consultation.md`“选择和读取结果”及首轮 `method_policy` | 本轮补足自动缺事实与显式排除的区别；已选八宅／形态 complete 不能称飞星金锁已审完，显式排除不追资料 |
| 3. 环境与本人／周围人八字紫微隔离 | 环境模型没有个人喜用神／命盘属性字段，额外字段拒绝；元素调节只绑定已算方法及对象 | `src/fatebridge/core/fengshui/context_inputs.py`、同目录 `models.py`；技能“工位与家居选法”、AGENTS 风水条目 | 已实现输入及解读隔离；不把同名五行当跨域换算或补偿关系 |
| 4. 房屋关联人物；八宅命卦独立 | 家庭／生肖输出为环境象征索引；`scope`、`applicable_methods`、`selected_applicable_methods` 明示仅飞星／金锁适用。八宅个人关系仍来自 `layers.bazhai.occupants` | `src/fatebridge/core/fengshui/context.py`、`src/fatebridge/data/fengshui/expert-policy-v1.json`；技能“家庭、多层和现代设计” | 本轮补明确作用域；索引不会从房屋直接推出某人的健康、财富或关系结果，也不代替八宅命卦 |
| 5. 方位与偏移重要；无方位看明确禁忌 | 全宅方向、图纸对齐、中心独立确认；显式不确定时拒绝实际分宫。无方向的原有形态可独立运行，四类厨卫关系及枚举材质器形可记录 | `AssessRequest` 的方向门槛与 `EnvironmentalObservation.feature`；技能“资料核对与调用”“家庭、多层和现代设计” | **部分覆盖**：方向门槛与有限事实记录已实现；具体厨卫／材质／器形禁忌及处方未实现。其他关系不能假装已有完整结构化保存能力 |
| 6. 多层统一方向、院落归一层、整体互动与异层影响 | 各空间独立中心／对齐；院落 `level=1`；影响区分局限本层、共享和未知。使用者正向名单与完整使用范围分开，负向排除须 `usage_confirmed`／`usage_evidence` | `FloorSpace`、`FloorInfluence`、`floor_review`；技能多层段、场景合同 | 本轮修复省略名单被误当不使用的漏洞。异层适宜及局限性依赖带依据的显式确认；不自动排每层宅运、推几何或宣称现实安全 |
| 7. 辈分、妻随夫序、双身份、生肖与对宫主次 | 完整同住范围后按辈分处理父母宫；妻随夫排行显式启用，双身份保留，多宫不相加；生肖独立确认，对宫次级。`household_scope` 区分纯象征与环境绑定 | `HouseholdMember`、`EnvironmentalContext`、`household_correspondences`；技能、咨询闭环、专家政策家庭段 | 本轮加入 `symbolic_reference` 路由，纯卦名／对宫说明不再迫使补罗盘；不是任意配偶双向随序，也不是精确二十四山人物影响判定 |
| 8. 现代设计抓大放小 | 拱门／开放厨房返回低优先提醒、`action_required=false`；不直接生成拆改或摆件要求 | `environment_findings`、`expert_environment_2026_10_v1.modern_design_priority`；技能现代设计段 | 已实现本次专家版本的提醒强度；真实通风、卫生、消防另作现实／工程判断，不由样式预言灾祸 |
| 9. 补充五行、职业、家具、砂水细节 | `method_details.status=reference_only`；固定宫与到宫星五行独立。四宫有限古代职业角色，其他职业 `not_covered`；家具及砂水为观察提示 | `src/fatebridge/core/fengshui/method_details.py`、`src/fatebridge/data/fengshui/expert-methods-v1.json`；细节请求追加 `method_details`，技能末段与专家政策“方法细节” | **部分覆盖**：有来源的基础五行、有限象意与观察提示；没有九星现代职业全表、按职业算吉凶、各法完整家具处方或自动砂水分类 |

## 首审反例与修复关系

| 问题 | 可复现触发与原行为 | 修复后的合同／文档要求 |
| --- | --- | --- |
| 楼层省略名单被误作负向事实 | 问题层 `subject_ids` 省略／默认空，住户仅登记在适宜的另一层，原路径可输出 `local_exposure_not_assigned_to_other_floor`；没有证据证明此人不使用问题层 | `subject_ids` 仅正向；需要负向排除才核对有关作用空间的完整住用范围，`usage_confirmed=true` 与 `usage_evidence` 成对。未知保持待确认，同层室内及院落分别考虑 |
| 完整楼层名单可与对象显式使用人矛盾 | 某人通过 `placement.subject_id/subject_ids` 已明确使用该层对象，却被该层“完整”名单排除，可能错误获负向豁免 | 校验完整楼层名单须覆盖该层对象明确使用者；省略 selector 的兼容语义不作为真实使用声明 |
| 候选可误搬非目标固定砂水坐标 | 只搬一张桌，候选上下文却把另一固定砂水特征归入新层；或省略该特征后丢失其原楼层元数据 | 拒绝改变非目标固定特征坐标；候选省略时保留原楼层元数据；家具候选不得将已确认全局磁北改真北，目标新特征仍独立确认 |
| 候选逐规则比较漏飞星参考 | 原 `rule_comparisons` 有八宅、形态、金锁，却没有已算年星／历史宅盘；与技能“逐规则比较”范围不一致 | 加入星数／角色／落宫参考，`comparison_scope` 明示非完整组合吉凶；`layer_statuses` 与方法策略分别保留现状／候选真实计算状态 |
| 已选层完成遮住优先方法未审 | 局部自动请求仅有八宅／形态资料，已选计算能 complete，但飞星／金锁没有实际计算；旧策略只给未选参考状态，容易被概括为整个优先审查完成 | `priority_review_status` 与每法未选原因单独交付，区分自动缺事实和显式排除；不修改已有选中层的计算数值 |
| 自动选法语义未穿透模型序列化 | 直接调用服务的自动局部请求显示优先范围 partial，但 `AssessRequest` 的 before-validator 将 `methods=None` 提前改成实际列表；真实三端经 `raw_invoke` 序列化后，服务误认用户显式选法，可把同一优先范围报告为 complete | 请求模型保留 `methods=None` 的自动语义，`selected_methods` 属性按已确认事实求实际列表；不增加额外公开参数，并以真实 REST／FastMCP／CLI 反例验证语义一致，不能仅凭直接服务探针验收 |
| 家庭索引可被误读为八宅个人结果 | 仅选择八宅且附家庭上下文，仍有家庭／生肖象征条目；旧条目缺明确适用方法字段 | 为家庭条目及关联增加环境象征作用域和适用方法；无已选适用环境法时仅为参考，不据此宣称八宅判断 |
| 纯家庭卦象被要求补罗盘 | 已确认老父身份、`methods=[]`，可给乾／对巽且无物理绑定，但旧路径仍把三项方向确认为必补，并令本次审查不完成 | 纯说明使用 `household_scope=symbolic_reference`，保持实际方向为空，不为家庭象意追罗盘；同时请求的楼层物理要求不因此免除 |
| 场景投影提示会触发 422 | `scene=workstation`、`methods=[]`、合法 `form_observations` 且没有环境上下文；按旧 catalog“新范围追加两路径”读取 `method_policy` 与 `layout_analysis.environmental_context`，严格投影返回 `unknown_projection_path` | catalog 与技能／MCP 指令统一：有场景或上下文才加 `method_policy`，有上下文才加其结果路径；既有首轮通用字段不无条件加入可缺路径 |
| 厨卫事实保存范围文字过宽 | 明确输入 `feature=bathroom_door_faces_stove` 会因不在枚举中被拒绝；旧政策文字说相关事实可以“完整保存” | 明列四类当前关系；其他用户描述在咨询中原样保留并标未支持，不换错误 `feature`，不把禁忌未实现藏在事实记录完成中 |
| 新来源被笼统声称有检索／散列 | 新专家政策与象意来源只有实际标题、URL、类别、范围等字段，没有统一内容 SHA 或检索记录 | 将检索／散列说明限定于实际保存它们的既有作者证据包；新规则按真实来源字段及规则版本交付，不虚构追溯信息 |

## 覆盖状态与首轮交付

同一结果应分别读取：已选方法的计算状态、`method_policy` 的优先方法审查范围、`analysis_progress.rule_coverage_status`、动作可执行性，以及环境上下文的物理绑定与使用范围。任何一个 complete 都不能替代其他层。

已确认“卫生间门对厨房”的无方位请求，可以合法返回计算 complete、事实审查可结束，同时 `rule_coverage_status=limited`、`confirmed_unsupported=1`、具体 finding 为 `confirmed_fact_without_specific_taboo_rule`、无处方。交付必须说“该事实已记录，具体禁忌规则尚未覆盖”，不能说“厨卫风水已完整分析”。同样，`method_details` 的四宫古代角色参考不应被表述为已完成全部九宫现代职业与家具规则。

首轮使用已公布字段并保留 `rulesets`／`rule_trace`；场景／环境请求再取 `method_policy`，有上下文才取 `layout_analysis.environmental_context`，具体方法细节再取 `method_details`。家庭纯象征也保留来源及其不绑定实际方区的状态。用户只要求已选范围时可以结束该范围说明，不因非本次所需的未选方法或未实现规则反复追资料。

## 本轮验收与交付记录

本报告编写时已用当前本地 REST／服务实际复现投影 422、只读家庭象征被追方向、四类关系枚举及具体禁忌未覆盖状态；这些是发现问题的证据，不是修复完成或发布成功的证据。文档改动没有修改生成区、计算代码或既有 golden 数值。

随后**仅限直接调用本地服务的局部探针**确认：显式 `symbolic_reference` 的家庭说明可 complete、无方向缺失且实际方向为空；同一局部形态请求自动选法的优先范围为 partial，显式 `methods=[]` 为 not_requested；省略问题层完整使用证据时，异层住户保留 `usage_confirmation_required`。其中自动选法的直接服务结果没有覆盖请求模型序列化路径，随后真实三端审查才发现上表中的自动语义丢失问题；不能把该局部结果当作三端已一致。技能合同 12 项通过，七份相关 Markdown 的本地链接通过。这些局部检查仍不替代修复后最终源码的统一全仓与三端验收。

最终冻结 **745** 项源码、规则、Skill 与文档，包含 9 个原始技能软链接；清单 SHA-256 为 `1eb845a3f3cd6d0847b3cb62f67a903a1cf947dbf5e51ddd57002d3d4aeaee18`。本报告与本轮验收 JSON 是验收后生成的证据文件，不参与该源码清单的散列，避免自引用；其余工作区与冻结快照逐项核对无漂移。

| 本轮统一验收 | 结果 |
| --- | --- |
| Linux x86_64／Python 3.12，全仓、源码只读 | **2967 通过，0 跳过，0 失败** |
| macOS arm64／Python 3.13，全仓 | **2879 通过，88 跳过，0 失败** |
| Linux golden 数值基线 | **87/87 一致**，基线未修改 |
| 专家政策及本轮反例回归 | **187 项通过**，已包含于全仓统计 |
| Black／isort／mypy／生成合同／场景清单 | 全部通过 |
| 仓库外 wheel 实际加载与合同回归 | **91 项通过**，含真实 REST／FastMCP／CLI 结果一致及非法输入一致拒绝；新规则 JSON 已打包 |

完整记录见[本轮验收 JSON](audits/2026-10-15/fengshui-expert-systematic-validation.json)。安装包 SHA-256 为 `9ad796aada4d9c68edef1aa687a6456596db9ab333b23e83d732260f7f12d94b`。合同与场景清单均由脚本生成；没有手改生成区，也没有改既有 golden 数值。

本轮保留第 5、9 条矩阵所列的部分覆盖范围；具体厨卫／材质／器形禁忌、现代职业全表与完整家具处方未宣称完成。新 Desktop 真实模型咨询、已有 MCP 进程重新加载、现场调整和现实效力未验收。托管 CI 与 Git 远端状态须在推送后独立核对，不能由本地绿色测试代替；最终提交身份以本报告所在 Git 提交及交付回执为准。
