# 五项生活场景 skills 审查与落地

审查时间：2026-10-15（Asia/Shanghai）。范围：onda-shiye、onda-yuanfen、onda-shiyun、onda-jiankang、onda-mingge。未修改计算代码、根 AGENTS、共享层或用户已有风水改动；未 commit。

## 总体发现

这五项原来已具备真实工具调用、投影、去重、时区和传统参考边界，主要缺口不是少算几项，而是回答没有稳定地利用“本次实际差异”：同一个“给一件小事”可以套在完全不同的计算结果后；工具清单与谨慎表述比交付内容更明确。单纯把全部工具都调用一次，不能补上这层缺口。

另有两个实质语义问题已在本次 skill 层修复：健康入口承诺看“身体哪里弱／神经情绪倾向”，与其后禁止诊断的要求冲突；命格把孩子本人的天性与父母盘里的子女星／子女宫混为同一路由，存在拿错人物资料解释的风险。

## 能力—问题—交付—边界矩阵

| skill | 已有计算能力与典型问题 | 原始缺口 | 本次交付形态 | 边界与缺失 |
| --- | --- | --- | --- | --- |
| onda-shiye | 事业类型、事业结构、创业倾向、自动大运流年；财星、求财方式、规则风险；岗位、跳槽、创业、合伙 | 给出工具列表，但“今年能动的”建议较泛；未充分区分自主经营倾向与准备条件，行业类比可能被误读为职业资格 | 工作方式与岗位条件对照；创业一个付费需求／交付／现金核对；财务一笔预算或回款核对；合伙一个分工或权限问题 | 未对 offer、企业或项目算成功率；行业五行归类不是能力测评或就业排除清单；现实动作须注明来源 |
| onda-yuanfen | 单人婚姻／桃花及年级时机；双人五行、喜用、十神、格局与传统规则维度 | 仍易把综合分作为结论，把维度内部差异讲成泛泛沟通建议 | 与问题最相关的一处配合、一处张力，明确个人／跨盘作用域；必要时“维度／依据／可核对什么”短表；一次观察真实回应的沟通 | 不判断对方心意／忠诚／关系成败；个人内部事件不扩大为双方冲突；空 recommendations 不造引擎建议 |
| onda-shiyun | 大运／流年／当前月聚合、全年节气月份时间线；西占／紫微及择日 | 38 个工具的清单盖过时间之间到底有什么区别；摘要已有当前月容易误写成全年每月 | 阶段背景、当年主题、当前月分开；有数据时用“时段／变化／准备”时间线；择日候选按实际结果对照 | 年级不切上下半年／月份；聚合已有当前月不等于完整全年已交付；全年或全量首次 fields=null，再从同一 run 取 result_delivery |
| onda-jiankang | 五行权重、传统寒暖分类、藏象映射及规则建议，自动 timing_context | 开场和表格称能看真实身体弱点、神经／情绪倾向，容易给引擎中的病名标签增加医学权威 | 明确“计算权重／传统对应／独立生活观察”三种来源；用户有生活目标时给一项记录或安排 | 病名／器官“弱”不是个体发现；不把 regimen 当临床证据；具体不适先现实求助，不为症状收生辰或安排排盘 |
| onda-mingge | 本命结构、性格十神、学业星与学科倾向；子女星／宫及六亲文化；紫微星曜亮度 | 路由与工作流主证不一致；“看清为什么是这样”暗示已证实人格；孩子本人天性错接父母子女星计算 | 一项特点、一项条件与一个可观察小尝试；学业对照实际方法反馈；孩子本人和命主子女宫分开取人 | 不由学历分数限定学历／录取概率；不由父母子女宫判断孩子能力；真实经历不贴合时保留不贴合，不能强行贴标签 |

## 可复核的代码／字段证据

### 事业与财运

- `src/fatebridge/analysis/career.py:240` 起实际返回 `dominant_ten_gods`、`industry_analysis`、`career_structure`、`entrepreneurship`、`career_timing`、`suggestions`。
- 当前金样本 `tests/golden/snapshots/api_cn_bazi_career.json`：主导类型为独立经营，事业结构 75 为中等格局，创业倾向 73；两个分数都带不同 scope 与 score_basis，不表示成功率。样本使用显式柱覆盖，不可当作当前 2026 年年运。
- `tests/test_relationship_and_career_semantics.py:140` 起已有创业／事业评分语义及 REST/MCP/CLI 一致性测试。
- `src/fatebridge/services/bazi.py:961` 起统一专项运行器自动推大运流年并附 `timing_context`，故默认不再拼调同样的时运。
- 财运实际字段可由 `tests/golden/snapshots/api_cn_bazi_wealth.json` 核对：`wealth_stars`、`wealth_style`、`wealth_risk`、`wealth_timing`。它仍含“破财／忌合伙”等传统标签，本次只修解释方式，未改规则引擎。

### 缘分

- `src/fatebridge/services/compatibility.py` 返回独立的 summary、detailed_analysis 五维、traditional_compatibility、strengths、challenges、recommendations。summary 的 0–100 综合分、传统净分和其中 traditional_analysis 维度不是一个尺度。
- `src/fatebridge/analysis/compatibility.py:852` 起将 combined chart events 放入 pattern_synergy；事件的 `source_scope` 必须在实际事件层核对，不能因为外层叫“合盘”就认定全部是双方互动。
- `src/fatebridge/analysis/romance.py:94` 返回 `peach_blossom`、`hongluan_tianxi`、`opposite_sex_star`、`peach_quality`、`romance_timing`。`romance_timing` 内是大运／流年信号，不是对象到来的月份。

### 时运

- `src/fatebridge/services/timing.py:83` 起已经计算 liuyue_timeline 与 jieqi_timeline；`analysis_calendar` 保存 `analysis_date_context`、`analysis_year_jieqi`、`liuyue_timeline`、`jieqi_timeline`。
- 默认摘要 fields 保留大运／年／当前月以及实际 analysis_datetime／节气边界；全年时间线需本来就保留在首次完整调用中，后续分页无法恢复投影前已排除的字段。
- 将 26 项专家／全生命周期／世俗盘的解释长表移至 `skills/onda-shiyun/references/techniques.md`，根 SKILL 保留完整工具索引，避免 interface 工具集合漂移。

### 健康

- `src/fatebridge/analysis/health.py:77` 起实际返回 `constitution`、`organ_analysis`、`disease_risks`、`health_timing`、`regimen`；`organ_analysis.element_distribution` 是五行权重。
- 同文件 `ELEMENT_ORGANS` 和金样本当前确实有“抑郁／咳喘／器官虚弱”等标签。服务 `src/fatebridge/services/bazi.py:1081` 起描述仍称易患疾病与健康风险。本次 skill 修复不能被宣传为引擎本身已经具备医学发现能力，后续如要降低数据层误用风险须另议服务措辞与合同。

### 命格与亲子

- `src/fatebridge/analysis/personality.py:94` 返回 core_nature、dominant_traits、disposition、strengths、weaknesses、advice；`education.py:88` 返回 study_stars、education_level、wenchang、subject_orientation、exam_timing、suggestions。
- `src/fatebridge/analysis/children.py:52-109` 由命主性别选男命官杀／女命食伤，使用命主四柱计算 child_star、child_palace、affinity、relationship。它不能用来算孩子本人的性格／学业。
- `src/fatebridge/analysis/relatives.py:34-53` 同样只接一人的四柱，输出 parents、siblings、palaces、support，是命主视角。
- 已将 skill 的“孩子的天性、亲子”拆成孩子本人资料的性格／学业路线，和命主本人资料的子女缘／子女宫路线；已提醒根代理同步公共 scenario-routing 歧义行。

## 社区一手比较与采用方式

核对的是公开源码，不是安装或执行这些第三方 skills。以下同类案例没有独立核验其预测效果或社区知名度；知名通用方法参考与小众同类分开，不编排名或星数。

| 一手来源 | 源码可见的长处 | 本次吸收 | 不照搬 |
| --- | --- | --- | --- |
| [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill/blob/main/SKILL.md) | 阶段化收集／计算／解释，脚本 stdout 约束四柱，要求引用经典 | 把依据可见地连到结论与交付；计算和传统解释分开 | 逐步收曾用名等非必要资料、强制全维度报告、反推历史事件的“校准”，以及与本仓库不同的无时盘策略 |
| [aryaminus/astro](https://github.com/aryaminus/astro/blob/main/skills/astrology/SKILL.md) | 以问题映射计算 mode 与 reference，先计算再有来源地解释 | 领域问题直接通向合适的交付，深技法按需读取 | 默认查询记忆、未知时间兜底、多体系一致即更有说服力的暗示，以及医疗择时／博彩等范围 |
| [wvanderen/astrology-skill](https://github.com/wvanderen/astrology-skill/blob/main/SKILL.md) | 按用户问题给因子排序，检查缺失与分歧，普通聊天与保存报告分离 | 优先相关差异，不罗列整张命盘；保留数据局限，按需表格／报告 | 把某一西占因子权重原样套到 FateBridge 的中式规则；不存在资料时编造解释 |
| [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) | 在迭代中结合示例、可验证 expectations、定量和人工评阅 | 将“字段→生活含义→动作”的表现交给真实模型样例与固定结果对照检验 | 只因静态合同通过就宣称用户体感提升或预测有效 |
| [Obra brainstorming](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md) | 围绕目的、约束、可选路径与取舍理解所需交付 | 只在有真实选项／差异时对照，先理解当前问题 | 强制每次咨询过多轮设计审批、软件提交工作流 |

## 修改与验证

- 修改 5 个 SKILL.md，新增时运按需技法参考 1 份；同步 5 个 `agents/interface.yaml` 的 0.2.0 版本与摘要，以及 5 个 `agents/openai.yaml` 的具体价值展示和默认问题。
- openai short_description 长度依次为 33／32／32／31／33 字符，均在 25–64 范围，default_prompt 各包含对应 `$skill-name` 一次；按本机 skill-creator 的 `references/openai_yaml.md` 规格核对。
- `git diff --check -- <五个目录>` 通过。
- 现有合同组合执行初次为 **20 passed、1 failed**（2026-10-15）：失败来自并行星盘改动的 `astro_chart` 与 `astro_relative_chart` 新示例把 `planets.0`／`synastry_aspects.0` 用作初次严格字段投影。已通知根代理，非本组五项失败。全部合同最终结论由根代理合并后重跑。
- 本组所有可执行 CLI 示例独立 allowlist 重放 **13／13 通过**，结果写入 `life-example-validation.json`，保留命令、退出码、输出字段与 SHA-256。
- 尚需根代理汇总新上下文真实计算与固定结果新旧解释对照。静态合同和示例可执行只能证明工具与文档一致；不能单独证明用户更有体感，更不能证明传统预测有效。

## 记忆使用

轻量读取 `MEMORY.md:45-58`，用于保留此前确定的平实语气、资料复用、健康三来源与不重复时运计算的偏好；所有本轮能力和字段结论以当前仓库重新核对。关联 rollout：`01a13a55-1b68-7132-9b5d-9bfe4294b399`、`01a13a52-67d4-7b23-8dfa-0ad5e8cd4675`、`01a13a52-7831-7192-a4c4-45a438bdc442`。
