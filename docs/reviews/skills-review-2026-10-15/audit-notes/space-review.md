# onda-fengshui 深度 review 与增量修改

本次独占 `skills/onda-fengshui/`。以根代理保存的本轮基线为比较对象，保留工作区已有风水改动；没有修改引擎、共享资料、AGENTS、全局技能，也没有 commit。

## 审查判断

当前技能的优势是规则、来源、观察粒度、缺失和执行边界已经很完整。主要缺口是**计算与规则明细没有被组织成用户可以直接核对的交付**，而非缺少更多排盘或更多补资料要求。此次优化针对交付，不新增风水判断规则。

| 问题 | 现有实现与技能证据 | 本轮处理 |
| --- | --- | --- |
| P2：入口展示过度指向“具体调整”，用户难以看到无需搬动的价值 | 基线 SKILL frontmatter、openai.yaml 均强调可执行调整；但实际存在符合规则、关系未成立、无独立规则三种不同收尾 | 元数据改为逐对象依据、现状与候选、可保留／可调整／未覆盖；前置“用户应拿到什么” |
| P2：完整审查虽要求覆盖对象，但没有稳定的对象到依据组织方式 | 基线 SKILL 尾部仅给覆盖原则；`LayoutAnalysis` 已有 placement、form、interior、material、surface 独立分支；`surface.py:164-210` 明确区分未知与确认无规则 | 新交付参考按对象／两端关系列出事实、判断与理由、调整和条件，覆盖用户点名对象，不强制每行安排动作 |
| P2：候选合同细致，缺少面向用户的差异与代价呈现 | `planning.py` 的 `rule_comparisons`、`comparison_scope`、`layer_statuses` 已支持逐规则比较；基线主要解释如何构造候选 | 对照表把现状作为一列；解释哪条关系改变、什么权衡保留、尚缺什么条件，不按 ready 选综合赢家 |
| P2：解释状态已有实现，但仍容易被大量执行缺项淹没 | `output.py:175-222` 独立建模 interpretation_status、conclusion_candidates、execution_only、assessment_complete、action_readiness；`tests/test_fengshui_analysis_progress.py:89-155` 覆盖普通解释不依赖行动 ready | 交付参考把各状态翻译成可说的用户含义，要求已知结论先行，缺项只按当前问题择要追问 |
| P2：已确认无规则虽有合同，仍缺可见的交付位置 | `surface.py` 返回 no_independent_placement_rule／reviewed_unsupported；`test_confirmed_no_rule_item_finishes_review_without_changing_legacy_partial` 证明可结束范围说明 | 无规则对象也占一行，明确“本轮没有依据要求搬到吉侧”，不等同有利、不继续追问强求吉位 |
| P3：入口与咨询参考重复候选技术细节，稀释前面的用户交付目标 | 基线 SKILL 实际候选布局七个长段，consultation 已有同类候选与复核合同 | 将入口候选部分缩为三个概括段并明确调用前阅读；金锁新 features 和物理可行性两项原入口专门说明补入 consultation，保留边界 |

已检查 SKILL、consultation、interface.yaml 和 openai.yaml。用户已写入的专家政策、飞星／金锁／八宅优先次序、家庭／楼层、BTB 显式选择、照片候选、两端关系、材质资格、有限玄空和来源交付均保留。

## 修改文件

- `skills/onda-fengshui/SKILL.md`：用户交付前置；更新描述；精简重复候选条款，以明确链接转入完整合同。入口字节由 24966 减至 23625。
- `skills/onda-fengshui/references/delivery.md`：新增按需交付参考，覆盖单项解释、逐对象表、分支取证、现状与候选、无规则收尾、现场复核。
- `skills/onda-fengshui/references/consultation.md`：连接交付参考；补齐从入口迁移的金锁候选与物理可行性要求。
- `skills/onda-fengshui/agents/interface.yaml`：版本 0.6.0，更新 summary／reads。
- `skills/onda-fengshui/agents/openai.yaml`：更新展示文案与默认提示，保持显式 `$onda-fengshui`、25–64 字符约束及隐式调用许可；已读取系统 skill-creator 的 openai_yaml.md 规范。

新参考按逐对象／完整审查／候选问题需要加载。总体包增加了一份资料，不能把入口缩短说成全部提示总量降低。

## 开源社区对照

2026-10-15 实际浏览下列官方仓库原文；借鉴的是交付和取证方式，没有把它们当成风水规则来源，也没有复制原技能内容。

| 一手来源 | 可取之处 | FateBridge 对应落实 |
| --- | --- | --- |
| [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | 从用户具体内容与任务组织体验，词语帮助用户理解，交付前自评 | 每件真实对象有事实和理由；不堆工具名、不强套整宅模板 |
| [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md) | 先观察再行动，用实际状态选操作 | 现场观察、作者判据、候选新事实分别取证；搬动后按可见事实复核 |
| [Anthropic knowledge-work architecture](https://github.com/anthropics/knowledge-work-plugins/blob/main/engineering/skills/architecture/SKILL.md) | 明确方案、限制、取舍、后果与回看事项 | 现状／候选逐判据对照，解释改变与保留的限制，不编综合总分 |
| [OpenAI pdf](https://github.com/openai/skills/blob/main/skills/.curated/pdf/SKILL.md) | 交付物要能被直接检查；可读引用与最终检查不能只留在执行日志 | 方法版本和来源对用户集中交付；每条主结论能回查规则与现场事实 |

也按 `site:github.com "fengshui" "SKILL.md"` 和 `"feng shui" "skills"` 检索；本轮检索没有得到足以支持“知名且可比的风水 skill”的一手证据，因此没有虚构同领域社区标杆。上述对照是相邻任务模式借鉴，不构成领域有效性认证。

## 验证

1. `git diff --check -- skills/onda-fengshui` 通过。
2. 原有技能接口／发现／场景路由检查，以及解释状态和来源关系跨传输用例共 **23 passed**（4.77 秒）。包括 7 个 sourced cases 的真实 REST、MCP、CLI 一致性；没有新增镜像实现的文案测试。
3. 逐个核对该目录 Markdown 本地链接与 openai.yaml 文案长度、技能名；均符合约束。
4. 为根代理准备虚构评测：`fengshui-input.json`、`fengshui-question.txt`、`fengshui-local-result.json`，保存在本报告同目录。用当前核心 schema 与 service 真跑：全局 partial，但 interpretation_status=available，supported=4，confirmed_unsupported=1，年星缺 query_at_or_effective_year；手机为 no_independent_placement_rule，镜床为 authored_caution。其 optional_action 缺项刻意保留，用于评测是否错误阻塞现有解释。
5. 准备评测时两次误把 transport 控制字段 fields/include_snapshot_text 直接传核心 AssessRequest／catalog model，被 extra_forbidden 拒绝；正确做法是核心校验剥离传输字段，公开 MCP 请求保留它们。该失败不计入通过用例。
6. 使用本地 FastMCP Client 实际调用公开的 fengshui_assess，最终评测请求成功；超预算部分由 result_delivery 交付。本次为进程内 MCP，根代理仍独立用 stdio 固定结果，不能把该调用当作新 Desktop 会话验收。

未把上述检查报告为用户体验改善已获验证；真实模型的新旧结果解释评测由根代理独立完成。现有风水效力没有被本轮软件检查证明。

## 进行中代码的边界

初审时新 workstation.py 主要自引用；审查过程中，工作区其他活动继续添加 models/context_inputs/layout/output/services 的接入，最后已看到 workstation_analysis 的本地调用路径。该变化属于用户原有进行中工程，非本轮新增能力，也不能以最初的“未接入”印象覆盖最终事实。此次 skill 没有宣传这批尚未完成全链路验收、未核对当前连接缓存的新能力；最终工程接入／公开 schema／验收应由对应任务单独确认。

## 记忆使用

轻量记忆核对用于保留既有分层和工作区边界，实际实现均重新读取：`MEMORY.md:519-536`。相关 rollout id：`01a1392c-2e1c-78f1-9923-aafd962296a6`、`01a13a4e-9e02-7770-8082-07e54c48f262`。没有更新记忆。
