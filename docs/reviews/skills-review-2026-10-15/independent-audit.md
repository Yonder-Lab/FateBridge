# 9 个场景技能独立审核

审核者：independent_audit。记录时间：2026-10-15 15:39 UTC。

审核过程中主代理正在修订同一工作区。本报告区分最初确认的问题、已经直接看到的修正，以及仍交由主代理最终核对的项目；不是对后续未读取修改的签字。未读取 `/tmp/` 的审查结论或其他代理报告，未修改技能、引擎、全局技能或记忆。

## 实际核对范围

- 阅读全部 9 份 `skills/onda-*/SKILL.md`、全部 `agents/interface.yaml` 和 `agents/openai.yaml`；核对发现入口、相对引用、UI 提示与技能范围。
- 阅读 `skills/_shared/fatebridge-engine.md`、`onda-counsel.md`、`consultation-delivery.md`，以及 `docs/scenario-routing.md`。风水深入核对到 `SKILL.md`、`references/consultation.md` 中的条件、作用域、输入和交付路径；未把并行风水工程作为本次独立工程审计范围。
- 追查当前 `ToolSpec`、请求模型、业务输出模型、实际服务实现、`suggested_fields`、场景生成脚本和 `discover_scenarios`。不是仅核对关键词出现次数。
- 用虚构预设实际执行 14 类工具，检查技能引用的关键字段：事业、财运、健康、教育、性格、六亲、子女、桃花、婚姻、八字综合、紫微、本命星盘、关系盘、梅花。所检查路径全部存在；没有发现这些证据地图中需要靠猜测补出的字段。
- 独立检查了人物归属：孩子本人性格／学习用孩子资料；命主子女缘及六亲用命主资料；双人八字用 `person1_/person2_`，西占关系用 `inner_/outer_`；西占核心盘可解析城市，但关系盘／推运显式要求坐标；西占默认民用钟时、中式默认太阳时。相关正文与实际请求模型一致。

## 确认的问题及处理状态

### 1. [P2] 普通现实决定被无条件导向占卜

最初 `onda-yuanfen/SKILL.md:53` 和路由矩阵把“要不要表白／复合”直接交给梅花／六爻；`onda-zhanbu/agents/interface.yaml` 的触发词又包含没有术数前提的“一个具体决定”“要不要做某件事”。这与 `onda-zhanbu/SKILL.md:24` 的“普通现实决定但未请求术数时，不因‘要不要’三个字自动起卦”冲突。用户只想讨论复合条件时，可能被要求选问时并起卦。

已直接看到修正：`docs/scenario-routing.md:86` 改成“明确求卦看表白／复合”，`:140` 加入全节的明确术数前提，`onda-zhanbu/agents/interface.yaml:7-8` 改成“求卦辅助…”和“起卦问…”。

最终仍需核对：生成器 `scripts/build_scenario_manifest.py:39-68` 仅保存表格单元格的条件，节前说明不会进入机读行；当前 `:144` 等行的主证单元格仍是裸“主”。主代理应检查最终生成清单是否也能保留“用户明确求卦”条件，而非只修正文。这里是机读指引可能误导的风险，不是已测得运行时误触发。

### 2. [P2] 把固定四卦组合称作“大衍／蓍草随机起卦”

最初 `onda-zhanbu/SKILL.md:29`、共享引擎说明及场景路由把 `tongshefa` 推荐为大衍蓍草起卦，还按“正式郑重”偏好选择它。实际请求 `core/requests/divination.py:54-60` 仅有四个带固定默认值的卦名；`core/local_techniques/tongshefa.py:142-187` 对给定四卦作左右卦、潜藏、亲和的确定性组合，不实现随机蓍草过程。

独立实际调用 `{}` 得到固定输入 `巽／坤／震／震`，结果为左风雷益、右地雷复、主关系思克实。命令能成功，不能证明替用户完成了其所求取法。

已直接看到修正：`onda-zhanbu/SKILL.md:29`、`skills/_shared/fatebridge-engine.md:208`、`docs/scenario-routing.md:159` 及 `services/catalog/divination.py:117-118` 均收口为实际四卦组合，明确默认不是用户起卦。主代理最后核对所有副入口与原有测试中的文案预期即可；无需改算法来满足不存在的承诺。

### 3. [P2] 把读取既有星骰面称作随机抽骰；梅花也残留随机能力描述

`otherbu` 的实际实现 `core/local_techniques/otherbu.py:223-225` 归一化传入的星座、行星和宫位，再在 `:323-339` 返回这些值；没有自动抽骰。独立调用只给时刻及问题时，结果为默认 `Sun / Aries / house=0`。最初 `docs/scenario-routing.md` 的“西式随机问事”会令一次成功调用被误报成实际抽取。

已直接看到技能／共享层／路由和 `services/catalog/divination.py:194-195` 改为解读用户已有骰面。

记录时仍待主代理收口的真实工具描述：

- `services/catalog/divination.py:104` 称梅花为“随机取数”，`:133` 交叉推荐“即兴随机一问用 meihua_analysis”。实际 `MeihuaAnalysisRequest` 只有显式时间输入；`core/divination.py:818-865` 返回 `method=meihua_time_seed`，由年支、农历月日、时支确定结果。
- 同文件 `:172` 的宿占描述仍交叉推荐“西式随机问事用 otherbu”。单独修正 `otherbu` 自身描述仍会留下这个反向误导入口。

### 4. [P2] 段后正文的择一条件未进入机读路由

独立读取 `discover_scenarios(..., surface='mcp')` 时，最初“我是个什么样的人”有 `analyze_destiny` 和 `ziwei_birth` 两个 `primary`，`condition` 都为空；“孩子本人的性格／学习”同样同时主选 `analyze_destiny` 与 `bazi_education`。正文已要求按所问选择，但机读使用者拿不到这个区别。普通性格问题可能扩成多体系／多专项，孩子学习和性格也被混成同一分支。

原因是 `scripts/build_scenario_manifest.py:49-65` 只从单元格提取条件，不读取表后解释。实际生成结果证明不是单纯文风问题。

已直接看到修正：`docs/scenario-routing.md:51` 将八字默认／用户选择紫微写入单元格，`:56-57` 拆开孩子性格与学习；`:105` 把中式默认／西占视角写入单元格。最终生成清单及条件输出等待主代理最后检查；不能只用源 Markdown 已改作为机读验收。

### 5. [P2] 入口元数据仍有范围和人物输入条件丢失

记录时交由主代理最后修正／核对：

- `onda-zige/agents/interface.yaml:7` 的“我是一个什么样的人”是无条件全面画像触发，和 `onda-mingge` 的“我是个什么样的人”几乎相同；`onda-zige/SKILL.md:3` 明确仅在要求全面、多维度时使用。应使机读触发也保留全面要求，避免把单项性格扩大成三体系报告。
- `onda-shiyun/SKILL.md:85-86` 与 `agents/interface.yaml:59-66` 列出统一出生资料，但其择日主证 `astro_election` 不收出生资料。`core/requests/western_events.py:115-143` 要的是候选活动时刻、活动地点与时区；`services/western_election.py:27-76` 只评估该候选时刻。这个分支应核对候选时刻／活动地点，不能让统一生辰清单成为额外前置问卷，也不能暗示已有自动搜索整段日期能力。
- `onda-jiankang/agents/interface.yaml:13-15` 把疲累、睡不好、情绪内耗列为触发，又在 `:23-29` 无条件列出生资料；正文 `SKILL.md:44,55` 明确具体不适不采生辰。即使 `required_inputs_scope` 声明实际工具优先，元数据本身仍缺少该分支条件，应加明确输入说明或去掉无条件清单。

这些是静态指引冲突；没有声称模型必然按清单追问，亦未测运行时发生比例。

### 6. [P3] 共享资料中的两处过时解释会削弱已正确的场景规则

- 最初共享引擎 `:277` 把只有一套体系提到的结论自动称“弱信号”，与全面画像 `onda-zige/SKILL.md:49` 的“不因另两系没讲而降成弱信号”冲突；没有统计依据支持自动降级。已直接看到共享层改成“标出体系与范围，不自动表示较弱”。
- 最初共享引擎 `:61` 把六爻、统摄、星骰等笼统称为“只有文本快照”，实际它们有结构化业务字段；既有严格字段投影也能运行。已直接看到 `:61` 改为分别核对业务字段、文本和导出形态，避免把没有 `snapshot_export` 误当没有结构化结果。

## 9 个常见场景的路由 desk-check

这是把问题逐条对照入口描述、路由、请求／返回合同的桌面检查；没有运行模型来测自然语言触发，没有成功率、触发率或端到端对话质量统计。

| 场景与示例意图 | 应走的入口／主证 | 人物、条件和交付核对 |
| --- | --- | --- |
| 事业：按已给资料看是否适合换岗 | `onda-shiye` / `bazi_career` | 读结构、创业倾向、当期时机；已有专项不再重复算大运流年，岗位事实来自用户 |
| 双人：看双方如何相处，未说明关系类型 | `onda-yuanfen` / `two_person_compatibility` | 两套人物资料，`relationship_type=general`；个人内部事件不转成跨盘矛盾 |
| 时运：看今年整体节奏 | `onda-shiyun` / `timing_analysis`，明确西占才选西占聚合 | 保留实际分析时间和节气边界；全年月份需相应时间线，年级结果不能造月／日 |
| 健康文化：想了解五行传统对应 | `onda-jiankang` / `bazi_health` | 计算权重、传统藏象和生活建议分开，不把疾病词当个体诊断 |
| 孩子学习：看孩子的学习倾向 | `onda-mingge` / `bazi_education` | 使用孩子资料；不用父母 `bazi_children` 推孩子学习能力。机读行原混合问题见问题 4 |
| 星盘：按城市和出生时刻看本命日月上升 | `onda-xingpan` / `astro_chart` | 核心盘坐标可由受支持城市解析；默认民用时，实际角度／行星／相位均有对应输出 |
| 问事：明确指定时间与时区起梅花 | `onda-zhanbu` / `meihua_analysis` | 原样传问时并核对 `analysis_context`；给真实本卦→动爻→变卦，不另起卦补全文 |
| 全面画像：明确要求八字、紫微、西占对照 | `onda-zige` / 三套主证 | 分别构造输入；保留缺失、单系证据和分歧，不默认健康／所有专项，不把一致当统计证明 |
| 风水：从照片讨论镜与床的关系 | `onda-fengshui` / `fengshui_assess` | 依实际观察保留候选；两端角色、关系、证据独立，不为非罗盘关系强要生辰／宅向；普通解释不等动作 ready |

## 不应触发及范围反例

| 用户意图 | 应有处理 | 静态核对结论 |
| --- | --- | --- |
| “帮我整理桌面，让拿东西方便” | 普通收纳 | 风水技能正文和 description 明确排除；不应因“桌面／搬动”自动算风水 |
| “我该不该复合，先帮我分析现实条件” | 现实关系讨论 | 不自动起卦；最初跨文件冲突已反馈并看到修订，机读条件仍须最终核对 |
| “两个 offer 的工资、通勤和成长怎么比较” | 现实方案比较 | 没请求术数不自动采生辰或排盘，工作关键词不是充分触发条件 |
| “我是个什么样的人，只谈性格” | 单项性格入口 | 不应因近义触发词扩大为全面三体系画像；元数据问题见问题 5 |
| “最近睡不好，白天很累” | 现实不适回应 | 不要求出生资料；只有另要传统文化参考时才进入计算 |
| “修风水工具的 projection 错误” | 工程流程 | 不走咨询采集、不起盘；技能 description 已排除开发排错 |
| “用大衍蓍草给我起一卦” | 说明当前能力范围 | 不用四卦默认值伪造本次起卦 |
| “现在随机抽一次星骰” | 说明当前不自动抽骰 | 不能把 Sun／Aries／第一宫默认值声称为抽取结果；已有骰面才解读 |

## 已执行验证及其边界

1. `.venv/bin/python -m pytest -q tests/test_skills_interface_contract.py tests/test_skills_engine_contract.py tests/test_scenario_routing_coverage.py tests/test_codex_experience.py -k 'skills or interface or scenario or starter_projection'`：**39 passed, 31 deselected**。包括真实 CLI 示例、名称／参数／引用一致性和已发布首轮投影。两条依赖弃用警告，不影响结果。
2. `.venv/bin/python scripts/build_scenario_manifest.py --check`：审核早期通过；其后主代理继续修路由和 YAML，最终生成物检查交主代理重新执行。
3. 14 类工具关键字段实际存在性检查：全部通过。四卦默认和星骰默认另作了两次实际复现，结果如上。

这些验证证明当前样例、合同及所检查路径可用；不能证明自然语言路由实际触发正确、解释具有现实预测效力、已部署 MCP 与本地代码一致，也不能替代主代理对最后修改和真实解释样例的复核。本报告完成后停止扩展测试，释放独立审核槽位。
