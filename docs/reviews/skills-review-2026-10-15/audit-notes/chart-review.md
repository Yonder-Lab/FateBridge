# FateBridge 星盘、全面画像与问事 Skills 审查

日期：2026-10-15。范围：`skills/onda-xingpan`、`skills/onda-zige`、`skills/onda-zhanbu`。仅修改三目录共九个 Markdown/YAML 文件；不改引擎、AGENTS、全局 skills，不提交。

## 主要判断

原有三项具备输入边界和工具路由，但“能力体感”主要靠工具数量与抽象口吻，交付缺少用户可见的计算区别。关键不是多算，而是让实际落点、相位、宫位、卦变和冲突进入回答，并连接到可由现实经验对照的安排。

审查发现真实合同漂移：核心本命盘坐标可从受支持 `birth_place` 解析，旧文却要求缺坐标先停；西占默认民用钟，不能沿用中式太阳时默认。三系合参旧文要求每个维度融合、把单系结果自动称弱信号、默认健康及未来节奏，超过三张静态主盘覆盖。问事旧文把多个卜法的输入与成败能力一概化，缺少本卦、动爻、变卦和现实验证之间的交付链。

## 逐技能与字段映射

| Skill | 原有问题 | 实际能力与证据字段 | 本次改动 |
| --- | --- | --- | --- |
| onda-xingpan | 日月上升入口停留在“挑2–3点”；流派盘、中点、互动/组合证据的不同未落到用户交付；坐标要求过严 | 本命 `planets.{id,sign_zh,house,degree_in_sign}`、`angles`、`aspects.{planet_a,planet_b,aspect,orb}`、元素/模式及 `balance_basis`；古典 `classical.{sect,planets,dispositors,topic_almutens}` 与 `classical_patterns`；变体 `hellenistic/india/guolao/thirteen_sectors`；德国 `midpoints/midpoint_aspects`；关系 `relationship_profile`、`synastry_aspects`、方向数据与 `chart` | 问题→实际盘层→字段→含义；区分本命、实际交互与第三盘；可见落点/相位、关系背景与方向；按需古典层与流派边界；地点解析、民用钟、分钟更正先查边界；UI强调用户能得到什么 |
| onda-zige | 以十一工具层次暗示全面度；强行融合每维三系；本命大限列表易冒充动态运限；健康未询问就扩展 | 八字 `day_master/ten_gods/structure_profile`、分布依据；紫微 `ming_gong/shen_gong`仅位置，星曜须 `palaces[*].stars_detail` 与 `sihua`；西占实际日月角度相位；专项已有 `timing_context`；主盘不等于每维专项 | 三系主证仍保留，按生活问题组织；来源/分歧/缺失对照表可选；不要求每维三系齐全；健康、时运按需补；不把单系自动弱化，不以同措辞提升准确率；给两三项可对照小尝试 |
| onda-zhanbu | 起卦后只写心态易变成通用建议；工具列表暗示统一成败、应期能力；所有卜法套时间必填；“类似塔罗”容易误解 | 梅花 `analysis_context`、`meihua.{method,base_hexagram,seed.moving_line,changed_hexagram,body_trigram,use_trigram,body_use_relation}`；`interpretation.{moving_line_phase,moving_line_oracle,action_hint,risk_hint}`；奇门局号/阴阳遁与实际相关宫位；其余按真实文本或字段 | 卦变一行和体用明确可见；分清引擎象意和经典爻辞；问时/时区核对、同卦解释不重起；现实选项/待验证条件/低成本下一步；不强迫二元结局；工具输入按各家核对，文本唯一结果保留，星骰不称塔罗 |

完整字段库存见 `/tmp/fatebridge-skills-review-20261015/chart-output-fields.json`，由当前仓库 golden payload 枚举，非基于模型记忆补出。

### 具体能力与限制核查

- `src/fatebridge/core/requests/astrology.py`：`AstroChartRequest.birth_longitude/latitude` 可选，地点解析；关系双方坐标必填；`use_true_solar_time` 默认 false。`tests/test_astro_true_solar.py` 与 `tests/test_astrology_tools.py` 有对应测试。
- `src/fatebridge/core/astro/chart.py` 与 `services/astrology.py`：标准盘含古典层、实际相位/尊贵、流派附层；印度当前附层为 ayanamsha、上升宿和月宿，不据名称宣称完整 Jyotish。13扇区与天文星座边界分开。德国为单人中点。
- `src/fatebridge/core/astro/relationship.py`：`relationship_profile` 标识实际 mode/primary_layer，双方本命、跨人相位与组合第三盘不同；focus 只筛选关注点，不改变已经算出的相位。
- `src/fatebridge/core/metaphysics/ziwei.py`：命身宫摘要不含全部星曜；palaces 包含 stars_detail、亮度与四化。本命大限表本身不构成当前动态运限。未为画像新增紫微运限工具。
- `src/fatebridge/services/divination.py` 与 `core/divination.py`：梅花为时间取数；返回主变互错综、动爻、体用、阶段与启示。生成 oracle 是该引擎结构化象意，不能直接称原文经文；未据此补入月令旺衰、外应和精确应期。
- 投影差异经主代理真实 MCP 证实：结果资源支持数字索引，不代表 `fields` 支持；`planets.0`、`aspects.0`、`palaces.0` 会报 `non_object_projection_path`。本分支最终示例仅用 `planets/aspects/synastry_aspects` 等合法顶层字段。主代理统一维护 suggested_fields 与预算。
- 三项均保留 `strict_fields=true`、`include_snapshot_text=false`、`fields=null` 完整导出例外、同 run delivery、精确西占目标钟时与 trace 父子链语义。

## 一手开源／公开技能对照

元数据来自 GitHub API 本次快照，文件保存于 `/tmp/fatebridge-skills-review-20261015/chart-sources/`。这些星数说明可见度，不证明方法或预测有效。未发现可据证据称“知名”的直接星盘/术数 Agent Skill；明确区分成熟通用基准与小众同类。

| 来源 | 本次成熟度证据 | 可取之处与实际吸收 | 局限／未采纳 |
| --- | --- | --- | --- |
| [wvanderen/astrology-skill](https://github.com/wvanderen/astrology-skill)，[SKILL.md](https://github.com/wvanderen/astrology-skill/blob/main/SKILL.md) | 0 stars / 0 forks；MIT；最近推送2026-09-22；有解释/输入/报告 schema 和自检 | 先按问题和盘型取证，再选相关因素；报告仅需时生成；关系背景不一律浪漫化。本次用在字段取证、关系盘分层与按需表格 | 小众参考，不称知名；不移植其大套参考包和 schema，不把它的因素权重冒充 FateBridge 引擎权重 |
| [Fyrgo8/meihua-divination-skill](https://github.com/Fyrgo8/meihua-divination-skill)，[SKILL.md](https://github.com/Fyrgo8/meihua-divination-skill/blob/main/SKILL.md) | 7 stars / 0 forks；API未给license；最近推送2026-09-23；有 evals、输入归一化和分层参考 | 卦义、体用、问事角色与现实背景分开；可复盘输入与结论关系。本次用在可见卦变和体用角色区分 | 当前强制完整九步、强制二元成败和降低不确定性表达，本次不采纳；不复制文本或无许可资源，不移植月令/外应规则 |
| [Johnson-Jia/liuyao-divination](https://github.com/Johnson-Jia/liuyao-divination)，[skill](https://github.com/Johnson-Jia/liuyao-divination/blob/main/skill/liuyao-divination/SKILL.md) | 6 stars / 1 fork；MIT；最近推送2026-07-17；有机械排盘/解释分层及方法文档 | 明确排盘事实再解释，记录影响结论的要素，避免只说吉凶。本次强调按实际返回事实引用 | 小众参考；其完整纳甲解释规则不能当作 FateBridge 已实现项；其手算后备与宿命性表述不采纳 |
| [anthropics/skills](https://github.com/anthropics/skills)，[skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | 181305 stars / 21466 forks；官方示例仓库；最近推送2026-10-09；有测试/评价迭代流程 | 用户实际任务→明确产物→验收→迭代，按需加载。用于三项“让用户拿到什么”与发送前核对 | 不是直接术数同行，也不证明本领域有效性；仓库各子项license分别检查 |
| [Anthropic xlsx skill](https://github.com/anthropics/skills/blob/main/skills/xlsx/SKILL.md) | 同官方仓库；生产文档技能为 source-available，不能把它称完整开源 | 输出正确性不能只看工具成功；相关结果需要意义核对。本次化为“相位/盘型/时刻/作用域”检查 | 仅工作方式参照，不复制其受限文本，不移植电子表格实现 |

## 验证

已完成：

1. `.venv/bin/python -m pytest -q tests/test_skills_interface_contract.py tests/test_skills_engine_contract.py tests/test_astro_true_solar.py`：**18 passed in 7.59s**。包括工具/接口一致、真实 CLI 示例执行、软链接引用与 UI 配置，以及西占民用钟/太阳时行为。
2. `git diff --check -- skills/onda-xingpan skills/onda-zige skills/onda-zhanbu`：通过。
3. 本次从真实源码和十份 golden payload 逐项核对字段，源文件/接口定义与 tests 相互印证。
4. `agents/openai.yaml` 按本机 skill-creator 的 `references/openai_yaml.md` 校对：所有字符串加引号，25–64字 short_description，default_prompt 明确含对应 `$skill-name`。

主代理负责统一重建场景 manifest、建议字段预算与真实 MCP 新旧解读对照；本报告的18项通过不等于实际用户对话质量、真实预测或 Codex Desktop 端验收。主代理已反馈独立 stdio 的固定证据与三种建议字段预算验证，最终以其合并报告为准。

## 本次文件

- 三项 SKILL.md：能力→实际字段→用户可见交付，合计减少旧重复文字。
- 三项 agents/interface.yaml：0.2.0，补 output.deliverables、input_notes；星盘不再把可选坐标当统一必填；问事不再把时间梅花的必填套所有卜法。
- 三项 agents/openai.yaml：用户价值描述与可直接发起的示例请求。

旧问事技能的参评／河洛本命示例没有删引擎功能，改为链接已有 onda-mingge 场景，避免以出生条文充当本次问事卦。
