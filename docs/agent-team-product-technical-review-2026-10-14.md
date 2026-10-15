# FateBridge 产品与技术第一性原理审查

审查日期：2026-10-14。团队：主代理、产品与真实旅程代理、技术架构代理、风水规则与验证代理。

审查入口是实际 Desktop 聊天[《审查工位风水布局》](thread://01a13ab7-837b-7700-a730-885801f2d83e?hostId=local)。各代理先读取聊天，再核对当前工作区源码、技能、合同及测试。工程审查不重新排用户命盘，也不将用户生日或照片复制到本报告。

源码参考 HEAD：`60dcdf7968770280a623dd2d97bd4dc58d118fe7`；审查对象包含当时未提交的工作区改动，不能把 HEAD 单独当作本次全部源码快照。已有改动及删除项全部保留，本次只新增审查文档，没有修改实现或提交推送。

## 核心判断

FateBridge 已有相当完整的计算、共享接口、回放凭据和规则边界。当前更值得投入的是：把“可信地算出结果”继续连接到“用户在真实限制内获得清楚的下一步”。

从第一性原理看，交付至少需要回答四个问题：哪些事实已确认；哪条规则支持判断；在现实限制内能做什么；补充或更正资料后哪些结论需要撤回。计算成功、规则覆盖、行动可执行和现场落实是四个不同状态。

真实 case 已经做到命卦与桌面作者法分开、照片候选与确认事实分开、保留固定工位和操作空间、说明无规则物件并给出来源。因此旧报告中的“没有桌面规则”“没有风水免发现合同”不再是当前缺陷。本次没有发现该 case 已交付的计算结果错误。

## 当前应保留的基础

- 中央 `ToolSpec` 及 catalog 派生 REST、MCP、CLI，共享执行、投影与错误模型，避免三端各维护一套算法。
- `as_of`、随机种子回放、运行环境与业务指纹支持复现；它们证明计算可追踪，不证明传统判断的现实预测效力。
- 风水 `rulesets`、`rule_trace`、逐方法覆盖和行动状态已经存在。桌面坐者参考系与房间罗盘分宫没有混用。
- 大结果已有 `result_delivery`，能够读取同一计算的保存结果；这是现有能力，不能再次报告成“完全没有展开机制”。
- Skill 明确要求事实、来源、作用域、约束及复核点，普通整理与传统规则分开。

证据：`src/fatebridge/services/tool_catalog.py`、`src/fatebridge/application/execution.py`、`src/fatebridge/services/replay_metadata.py`、`src/fatebridge/application/result_delivery.py`、`skills/onda-fengshui/SKILL.md`。

## 已复现的问题与交付语义缺口

### 1. 显式非法关系类型被静默降为 general

**类型：输入合同缺陷。优先：近期修复。**

`relationship_type` 是任意字符串；服务对未知值使用 `GENERAL`，结果又回显用户原字符串。使用仓库虚构示例的探针中，`general` 返回 54.5，拼错的 `marrige` 也成功返回 54.5，标签却是 `marrige`；`business` 为 56.9。这里的分数仅用于证明输入影响计算，不是成功概率。

用户和 Agent 会误以为指定的关系模式已生效。“用户没有指定”可以默认，“用户明确指定无效值”应报告错误。

**最小优化：** 共享请求模型使用五种合法值的枚举或 `Literal`；服务的直接调用入口也明确拒绝未知值。生成实际合同，不增加不受控同义词猜测。

**验收：** 三端对非法值给出一致的 `validation_error`、字段路径与合法值；省略时仍为 `general`；五个合法值保持原业务结果。

证据：[请求模型](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/requests/compatibility.py:75)、[静默回退](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/compatibility.py:38)、[结果标签](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/compatibility.py:67)。

### 2. 引擎原始事业文案超出规则所能支持的断言

**类型：原始输出语义缺陷。优先：近期修复。**

当前创业规则在命中食神／七杀条件时直接返回“食神制杀，有魄力有谋略，创业成功率高”。合成四柱 `丙寅 / 庚午 / 甲子 / 庚申`，日干甲，直接调用该分析函数得到 75 分并返回这句话。技术代理另用演示出生资料经真实共享执行取得 50 分、“更适合稳定工作”，notes 仍含“创业成功率高”，说明这不只存在于私有函数调用。这个探针只验证程序分支，不验证传统规则。

咨询指引要求不把分数当成功概率，但输出文本自身已经作出成功率断言。任何直接 API 消费者、报告模板或下游模型都可能继续传播它。可信边界应落实在源输出，而非只靠最后一层解读纠正。

**最小优化：** 改为明确的传统结构解释；为评分返回 `score_kind`、适用范围和依据，检查同类事业、关系、财运及健康文本中是否存在同样越界。保持数值算法与文案修复的验收分开。

**验收：** 原始返回、快照和三端结果均不再把启发式规则写成经验成功率；命中分支保留可追踪依据，不通过删除分析字段规避问题。

证据：[创业评分与原始文案](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/career.py:414)、[当前越界句](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/career.py:456)。

### 3. 同一对象在独立分支中可同时被当作书桌和灶

**类型：跨分支输入一致性缺陷。优先：近期修复。**

请求 `methods=[]`，不给 `placements`，提交相同对象 ID 的矩形桌面和 `purpose=stove` 的形态观察，当前验证正常通过，结果同时包含桌面作者规则和灶形态结果。

当前校验通过 `placements` 分别检查桌面用途与形态用途；缺少 `form_observations` 与 `surface_layouts` 的直接一致性检查。真实 case 未触发此问题，但 Agent 构造嵌套请求时可能产生语义自相矛盾的成功结果。

**最小优化：** 对两分支对象 ID 的交集要求形态用途为 `desk`，并审视其他共享对象引用的校验图。

**验收：** 无 placements 的矛盾请求在 REST、MCP、CLI 均明确拒绝；同 ID 的 desk 形态加桌面请求正常通过；不同对象 ID 可独立存在。

证据：[现有一致性校验](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/models.py:429)。

### 4. complete、未知和无规则尚不足以表达用户任务进展

**类型：已复现的交付语义缺口。优先：紧接合同修复。**

探针 A：矩形、活植物和移动许可都已确认，但目标区能否容纳、是否遮挡尚未确认。顶层、layout、surface 都返回 `complete`，`missing_inputs=[]`，行动却全部为 `conditional_option`。代码明确说明 complete 是对提交对象应用所选计算，因此不能直接把它改称计算错误。

探针 B：已确认物件 `representation=unknown` 与 `representation=other` 都得到 `no_independent_placement_rule`、`partial`、`missing_inputs=[]`。属性未知可能在确认后进入规则；确认的普通手机没有独立规则，则可以完成其范围说明。二者需要不同下一步。

**最小优化：** 保留现有计算状态，增加正交字段：规则覆盖原因、`action_readiness`、`pending_confirmations` 和当前请求的完成依据。未知属性给确认原因；确定无规则给覆盖边界。不要将 optional 新增物件候选变成必须购买或必须补资料。

**验收：** 本 case 的植物只待确认容纳和遮挡；近中被留作键盘后对应候选为 blocked，不再追问是否可用；确认手机无规则可以结束该项；未知物件更正为活植物后撤回旧原因并生成候选。

证据：[规则匹配状态](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/surface.py:46)、[可行动状态](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/surface.py:100)、[完成状态](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/surface.py:170)、[complete 定义](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/layout.py:244)。

## 产品与架构机会

### 完整输出校验需要区别于投影输出校验

**类型：已复现的验证层缺口。优先：近期修复。**

当前业务字段为支持任意投影全部可选，完整 service 输出也用同一模型校验。技术代理在独立进程内替换 bazi_career 的绑定，让合成 service 返回 `{}`，共享执行仍成功返回只有 `run_metadata` 的结果。没有发现真实事业计算当前已缺业务输出，但保护层不能拦住此类回归。

**最小优化：** 每个 ToolSpec 声明完整结果必须存在的业务根字段，或提供独立的完整结果校验器；公共投影模型继续允许省略字段。区分合法 partial 与缺失必需业务输出。

**验收：** 完整 service 的空结果或缺核心根字段应得到带 trace 的 `internal_error`；合法投影及风水部分资料结果继续通过。

证据：[投影模型可选字段](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/response_models.py:132)、[完整执行验证](/Users/thomas/Desktop/FateBridge/src/fatebridge/application/execution.py:16)。

### 5. 建立可携带的咨询事实快照与变更影响

**类型：设计机会，未发现本 case 已发生遗忘。**

真实 case 最新计算只提交桌面。旧入口视野、镜面方案及个人朝向由聊天上下文继续沿用，最终答复沿用正确。`parent_run_id` 只作关联，明确不查存储执行；不能据此宣称系统已经支持事实继承。

建议在独立咨询编排层维护：对象及使用人、确认事实、照片候选、事实来源、行动许可、未解决项目、适用方法和失效依赖。先用可导入导出的快照与显式 patch，不要求立即建设账户或数据库，也不将会话状态塞入规则核心。

例如“植物属性更正”只影响桌面规则；“换座位”应使旧入口、背靠与桌面坐标失效；“换使用人”应重新核对个人匹配及共用关系。保留原始计算记录与有效事实是两回事。

**验收：** 连续更正、换座位、换使用人、长对话摘要后均能撤回受影响结论；无变化的解释不重算；新计算可追踪所用快照版本。

证据：[父 run 合同](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/execution_context.py:21)、[本次请求计算](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/fengshui.py:244)、[当前靠技能维护变更](/Users/thomas/Desktop/FateBridge/skills/onda-fengshui/SKILL.md:60)。

### 6. 可行性应绑定具体动作，保留部分空间信息

**类型：API 表达能力缺口。**

当前可行性绑定整个桌面的 `feasible_zones`，同目标区域的候选共享确认。它不能无损表达“小盆栽 A 能放、大盆栽 B 不能放”，也没有表达多项候选能否同时执行。不能将不符合“区域可行”语义的调用探针直接当作算法 bug。

另外，用户已确认“右边”“左后能腾位置”，但九格近远及无遮挡未齐，程序只能省略精确 zone；已知的部分位置保留在 evidence 自然语言中，难以供下一轮程序复用。形态证据也按整个对象打包，照片窗户与用户确认入口难以各自携带依据。

建议以 `object_id + action_id + target_zone` 绑定物理确认，逐条件保存容纳、视野、操作以及植物状态；事实采用字段级来源与确认状态，允许“只知道右侧”的部分坐标。房间参考系与桌面参考系继续独立。

**验收：** 只确认 A 可放时 B 仍为条件式；照片估计不升级为用户确认；无法搬桌可在结构化行动层过滤转向，而不必靠模型每轮手工排除。可先提供确认合同，不立即引入完整 3D 几何规划。

证据：[区域可行性模型](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/surface_inputs.py:96)、[共享区域检查](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/surface.py:112)、[形态对象级证据](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/fengshui/layout_inputs.py:78)、[非桌面限制当前由咨询层筛选](/Users/thomas/Desktop/FateBridge/skills/onda-fengshui/SKILL.md:45)。

### 7. 将风水的规则溯源方式推广到事业和关系分析

**类型：广域解释合同的设计机会。**

运行环境与源码散列支持复现，但不能直接回答“这个结论由哪条规则、哪些输入、什么阈值、哪个权重推出”。事业评分包含固定基准、增减和上限，关系评分按关系类型使用不同权重。部分关系维度已有 score_basis，不能将全部解释能力说成缺失；目前仍可统一更稳定的规则 ID、作者／来源等级、规则版本、分项贡献和归一化说明。

建议先选 career 与 compatibility 两条高频路径，返回可复核的分项贡献及作者约定，把传统规则、项目启发式、计算精度和现实效力分别表达。不要把来源文章数量或外部软件对齐当成现实预测验证。

**验收：** 分项加权可重构最终分数；切换关系类型时标明变动权重；每条重点判断能定位规则版本和输入事实；不同分数模型不在解读中互换。

证据：[事业评分](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/career.py:414)、[关系权重](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/compatibility.py:215)、[运行溯源白名单](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/replay_metadata.py:95)。

### 8. 优化首次有用答复与阅读路径，再验证整体等待

**类型：真实旅程改进机会，效果尚未做 A/B 验证。**

引用聊天首个 turn 总时长约 271.5 秒，后续约 63.9 秒；三个业务 MCP 调用分别约 288、102、122 毫秒。首 turn 包含用户澄清回复，不能当作首次答复时延，也不能把两者差值归给模型或宿主。

记录中能直接观察到：一次批量读规则文档后又重复读其中两份；后续从大结果临时文件用 jq 展开。这里存在可以减少的读取与解释往返，但尚未证明减少这些动作能带来多少秒的 Desktop 改善。

建议把技能必读内容收敛为短的操作合同，来源与版本仍从结果获取，专题资料按需读一次；根据问题选择首轮字段或命名视图。先给已知资料支持的判断，再把能改变行动的少量问题交给用户；不要机械逐项追问所有可选事实。

桌面交付可试验坐者视角九格图：明确近中操作区、植物候选区和待确认标记，配合每个动作的条件与来源。图是宿主可选渲染，不要求把 FateBridge 后端改为完整前端，也不能由示意图补出照片几何事实。

**验收指标：** 首次有用答复时间、必要澄清次数、重复发现／读取、结果展开次数、用户能否指认目标位置。保持模型、推理与集成配置一致，同时评估来源完整性和未知项保留；记录宿主、模型与工具阶段的明确边界，未知耗时保留未知。

证据：[技能按需读取](/Users/thomas/Desktop/FateBridge/skills/onda-fengshui/SKILL.md:14)、[首轮提问原则](/Users/thomas/Desktop/FateBridge/skills/onda-fengshui/SKILL.md:39)、[按问题选择字段](/Users/thomas/Desktop/FateBridge/skills/onda-fengshui/references/consultation.md:34)。

## 大结果交付的扩展性

### 完整分页重复处理整篇结果

**类型：实测性能机会，未证明影响本 case 的等待。**

每页固定 2048 字符，每次却重新读整个 JSON、解码、序列化和计算整段 SHA256。直接调用 ResultStore.page 的技术代理测量：200011 字符、98 页约 97.29 ms；800011 字符、391 页约 1691.28 ms。载荷四倍时本地完整读取约 17.4 倍，符合当前全量处理乘以页数的复杂度。这是一次合成基准，不是生产 SLO；未包含 MCP 资源权限检查、IPC、模型或网络。

**最小优化：** 写入时预计算规范化文本、长度和散列；分页读取可寻址正文；manifest、权限判断与正文展开共用一次必要读取。字符 offset 与 UTF-8 字节 offset 要明确区分。可试验预算受控的可变页长与文件导出，保留同一 run 和全文散列。

**验收：** 全文重组和原结果严格相等、中文边界正确、散列相同；载荷增长时完整读取接近线性；不能通过减少规则、结果字段或来源来改善指标。

证据：[每页全量 get](/Users/thomas/Desktop/FateBridge/src/fatebridge/application/result_delivery.py:155)、[全量序列化与散列](/Users/thomas/Desktop/FateBridge/src/fatebridge/application/result_delivery.py:176)、[MCP 权限检查再次读取](/Users/thomas/Desktop/FateBridge/src/fatebridge/mcp_transport.py:91)。

### 容量上限检查与写入缺少并发原子性

**类型：压力边界问题，单人真实 case 未触发。**

ResultStore 的清理、预留检查及写入／rename 没有共享锁。同主机不同进程共用目录。技术代理在独立临时目录中把上限缩为 4096 字节，以 8 线程和 Barrier 暴露合法并发顺序；最终成功写入的记录为 12436 字节，超过配置上限。它证明非原子调度问题，不等于已经观察到默认 64 MiB 上限在实际用户环境超额。

**最小优化：** 对共享目录使用跨进程锁或原子容量预留，覆盖 reserve、提交和回收，按实际记录字节计量。

**验收：** 控制并发下已提交记录总量不超上限；回收与读竞争保持明确错误；进程中断可恢复，已存 payload 不受改变。

证据：[清理及容量检查](/Users/thomas/Desktop/FateBridge/src/fatebridge/application/result_delivery.py:51)、[检查后写入](/Users/thomas/Desktop/FateBridge/src/fatebridge/application/result_delivery.py:84)。

## 验收体系应跟随用户目标

当前共享技能、调用合同与三端回放测试证明了接口能力。真实模型观察也已存在，不能概括为“完全没有体验验收”。但已有观察来自不同迭代与不同环境；每一轮发布仍需明确记录对应快照。

建议保留三层验收：确定性的代码／合同回归；固定来源与事实变化的多轮合成案例；少量当前快照的真实 Desktop 体验。无需把付费模型调用放入每次 CI，也不能用合同通过替代用户理解和执行判断。

验收维度包括事实保真、规则来源、约束遵守、撤回能力、未解决项目、首次有用答复和阅读负担。不把建议数量、购买／搬植物或“用户喜欢答案”作为唯一目标。对无规则对象如实交付范围属于有效结果。

证据：[本地回放明确无 LLM](/Users/thomas/Desktop/FateBridge/scripts/experience_codex.py:1)、[计算与现实效力边界](fengshui.md#验证与维护)。

## 建议实施顺序

1. 修复可复现的输入／原始输出问题与完整输出保护，保持三端一致，更新生成合同及相关快照。
2. 拆开计算、覆盖与行动状态，提供按动作的待确认项；同步 Skill 与消费方。
3. 定义轻量咨询快照、事实 patch 和变更失效规则，再逐步添加具体动作可行性。
4. 试验精简阅读路径、命名视图和坐者图示，以真实 Desktop 对照数据决定保留哪些设计。
5. 扩展事业／关系解释溯源；新增方法或几何能力按具体需求及规则证据推进。

分页复杂度及存储原子性可并行作为交付基础设施改进；先用当前大结果负载验证收益，不将本地分页提速宣传为 Desktop 咨询整体提速。

## 本次验证

- 主代理：技能接口、技能引擎、Codex 调用合同与 agentic replay 共 50 项通过；场景 manifest 与生成调用合同的 `--check` 通过。
- 规则代理：当前风水聚焦测试 147 项通过。
- 主代理复现关系类型静默回退、创业原始文案、complete／conditional 状态、unknown／other 混淆，以及同 ID 桌面／灶用途冲突。探针使用虚构示例或合成输入。
- 技术代理：result_delivery、agentic_contracts、runtime_and_errors、schema_cache 共 54 项通过，并验证分页、存储并发及空业务输出边界。

以上为 macOS / Python 3.13 本地证据；不同代理测试组可能重叠，数量不相加。本次未执行全仓 Linux golden、托管 CI、额外真实 Desktop A/B 或现场布局复核，也未证明传统规则的现实效力。
