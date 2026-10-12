# FateBridge API、功能与 Agentic 设计审查

审查日期：2026-10-09。代码基线：`204635e2073a1ef33a0e2ef86bb98fced27e7618`。

## 结论

FateBridge 已经具有明确的 Agent 工具基础，尤其是中央目录、共享请求模型、离线计算、三端注册、字段投影和场景技能。它可以定位为 **Agent 可调用的领域计算引擎**。目前的 Agentic 原生程度属于部分实现：发现能力已经具备，理解输出、识别失败、自行纠错、控制计算预算和复现执行仍有缺口。

这里的“Agentic 原生”是本次审查的工作定义：Agent 能通过机器契约理解能力和限制，构造正确输入，识别成功/失败/降级，进行有边界的组合调用，并保留可复核证据。它不要求引擎自己拥有 LLM、数据库或自主规划器；无状态计算服务也可以做到 Agent 原生。

| 维度 | 判断 | 主要依据 |
| --- | --- | --- |
| 功能覆盖 | 广，已有较完整的计算工具库 | 12 个 family；REST / MCP 各 80 个业务工具 |
| Agent 友好 | 较好，但失败处理存在实际缺陷 | 有工具发现、描述、投影、错误码；MCP 领域失败仍标记成功 |
| 开发者友好 | 服务维护较好，客户端集成一般 | 中央目录减少重复；80 个 REST 成功 schema 全部为空 |
| Agentic 原生 | 部分实现 | 输入契约较强；输出、恢复、预算与场景编排契约不完整 |

这是一份设计和本地接口行为审查，不是算法准确率、真实预测有效性或已部署服务的验收。没有实际测量某个 LLM 的工具选择成功率。

## 已有设计值得保留

1. **中央工具目录是正确的核心。** `ToolSpec` 和 `services/tool_catalog.py` 从同一份定义派生 REST、MCP、CLI，绑定请求模型和服务实现，减少接口漂移。当前目录 82 条记录，REST / MCP 各 80 条，CLI 可执行 81 条；关系盘嵌套/扁平输入及旧版综合接口的差异已有明确说明。
2. **计算与场景解读分层。** `core → services → transports` 清楚；Onda 场景技能和主证/旁证路由已经表达工具选择、去重和追问深度。引擎无需内置通用 Agent runtime。
3. **输入基础较好。** 日期分量、经纬度等有 Pydantic 约束，地点、时区、宫制和真太阳时有共享处理；西占与中式技法保留各自的时间政策。共享出生信息时应共享同一个民用时间基准，同时保留体系的真太阳时默认值。
4. **CLI 有有用的复合能力。** `--subject-file` 支持复用档案，`profile` 可一次跑八字/紫微/西占等多工具，允许各分支独立失败；这已是高层功能的雏形。
5. **输出裁剪与精度提示已有基础。** `fields` 支持点路径，保留 `run_metadata`；星历实际模型与近似标志帮助消费者识别降级。九大八字专项可自行推算大运/流年，调用者无需先掌握这些术语。
6. **已有较好的接口回归覆盖。** 本次运行 8 组相关测试文件，103 项通过，其中包含所有 REST 代表请求与真实 FastMCP Client 的全部 80 个工具调用。

## 优先修复的可靠性问题

### P1：MCP 领域错误被标为成功，三端错误契约并不完全统一

实测 `bazi_birth` 输入 `birth_month=2, birth_day=30`：

- REST 返回 HTTP 400 和 `error_code=validation_error`。
- MCP 文本里返回同类错误 JSON，但 `isError=false`，`structuredContent=null`。
- MCP 缺必填项或 `birth_month=13` 时，FastMCP 先行校验，返回 `isError=true` 的 Pydantic 文本，缺少 FateBridge 自己的 JSON 错误信封。

根因：`core/tool_spec.py:809` 的适配函数返回 `str`；领域错误经 `render_error` 变成普通字符串，FastMCP 将其视为正常输出。调用签名校验发生在该函数之前，不能由函数内的 `try` 统一处理。

**影响：** Agent host、工作流和 MCP 客户端可能将领域失败视作成功；按统一 `error_code` 分支的消费者遇到框架校验错误时又无法直接解析。

**建议：** MCP 返回协议原生结果，在工具执行失败时设置 `isError=true`，同时保留机器可读错误内容。框架输入校验通过受支持的 middleware / 适配机制归一化；保留 text 兼容层。FastMCP 已有结构化输出与自定义结果支持，无需自行实现 MCP 协议。

[MCP 工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) 将工具执行失败放在 `isError` 结果中，并说明其反馈应帮助模型修正调用；[FastMCP 工具文档](https://gofastmcp.com/servers/tools) 提供结构化输出、结果和错误处理机制。

**验收：** 成功、缺字段、字段越界、非法公历日期、依赖缺失等通过真实 Client 检查协议标志和机器错误码，而不只调用 `.fn` 后解析字符串。

### P1：非法参数可能静默改变任务

实测择日接口 `POST /api/astro/event/election` 输入 `topic_id="contrcat"`，返回 HTTP 200，结果的 `analysis_context.topic_id` 变成 `marriage`，即把拼错的“签约”变成“结婚”。`services/western_election.py:49` 主动回退到婚姻主题。卜卦 `services/western_horary.py:52` 也对未知 `category` 回退 `general`，后者本次仅静态确认。

另一个实测：REST 输入未知键 `birth_mintue=59`，返回 HTTP 200，未知键被 Pydantic 默认忽略；MCP 同一未知键返回校验失败。这破坏了跨端的一致预期。

**建议：** 固定选项使用 Enum / Literal，让 schema 直接表达可选值；省略参数可以有默认值，显式传入非法值应返回校验错误。允许已知别名转换，但不能把未知意图转换成另一个业务主题。对未知字段采用一致、可见的政策；需要复用大档案时，由 subject/profile 入口明确筛选共享字段，普通工具严格校验。

严格未知字段策略可能影响老客户端，应采用有记录的兼容迁移或新版本入口，不能直接全局修改并假设无破坏。

### P1：REST 错误缺少可纠错信息

实测缺失全部出生字段与 `birth_month=13` 都返回同样的：

```json
{"error":"请求参数无效","error_code":"validation_error","retryable":false}
```

`api.py:480` 有意避免输出原始提交内容，但也删除了字段位置与约束。Agent 无法仅凭响应知道补哪一项、如何修正。

**建议：** 在不回显提交值或秘密的前提下输出安全的 `issues[]`：字段路径、错误类型、允许范围/选项、必填要求。明确区分“相同参数是否可以重试”和“修改参数后是否可以重新调用”；`retryable=false` 不应被理解成不可纠错。

例如：

```json
{
  "error_code": "validation_error",
  "retryable": false,
  "issues": [
    {"path":"birth_month","code":"out_of_range","minimum":1,"maximum":12}
  ]
}
```

### P1：成功结果缺少机器输出契约

运行时导出的 OpenAPI 中，**80 / 80 个业务 POST 的 HTTP 200 schema 都是 `{}`**；MCP **80 / 80 工具没有 `outputSchema`**，成功调用只返回 text JSON，没有 `structuredContent`。

根因：`ToolSpec` 只有 `request_model`；REST registrar 没有声明输出模型，MCP 适配器将返回类型固定成 `str`。现有输入模型与 `py.typed` 并不能替代响应类型。

**影响：** Agent 需要猜测 `bazi_birth.day_master` 等路径；TypeScript / Python 客户端无法从 OpenAPI 获得实际响应字段；只靠 golden 锁住已有结果，难以完整表达公开兼容契约。

**建议：** 为 `ToolSpec` 增加输出模型/JSON Schema，并从同一来源派生 REST 与 MCP 输出契约。优先覆盖核心命盘、关系、专项分析、时运、择日，再覆盖专家长尾工具。业务 JSON 应作为结构化数据返回，文本快照作为可选展示。

必须同时处理 `fields` 投影：不能声明“所有业务字段必填”的完整 schema，却在投影后删除它们。可以使用明确定义的 full/summary/projected 视图，或对投影结果提供允许部分字段的 schema；也要设计 MCP 错误结果与成功输出校验的关系。

[MCP 输出规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) 支持 `structuredContent` 和 `outputSchema`；提供 schema 后结果需要符合该契约。

## Agent 发现、预算与执行体验

### P2：有完整目录，但缺少渐进发现

实测全部工具描述的紧凑 JSON 体积：REST manifest **251,590 bytes**；MCP `tools/list` **255,259 bytes**。这是 UTF-8 字节数，不是 token 计数，也不是已经测得的延迟。

`GET /api/tools` 返回全部 82 条记录，未提供 family、scenario、关键词或摘要模式。`describe_spec` 输出参数名、简化类型、描述、默认值，但没有完整输入 JSON Schema、输出路径、可用性或算法状态；REST OpenAPI 和 MCP inputSchema 本身已有更完整的类型约束，问题在于中央发现记录仍是简化视图。

**建议：** 保留完整目录，为 REST 提供按 family / scenario / query 筛选和单工具描述；MCP 增加 family/scenario 的 host 配置档，按场景提供核心工具集合。给 ToolSpec 增加使用条件、替代/聚合关系、输出路径、例子和依赖要求。

场景 YAML 和路由 Markdown 已有，应从已有目录生成机器场景 manifest，并考虑 MCP Resource 暴露文档与知识，避免再维护一套清单。此次 MCP resources / prompts 均为 0；这些是可选增强，不是协议违规或 Agent 原生的硬性门槛。

### P2：字段投影有效，但其路径无法自助校验

同一八字命盘请求的 HTTP 响应：

| 输出选择 | UTF-8 响应体积 |
| --- | ---: |
| 默认全量 | 38,371 bytes |
| `include_snapshot_text=false` | 35,627 bytes |
| `fields=bazi_birth.day_master` | 334 bytes |

全量结构化数据、快照以及导出内容同时存在，单独关闭顶层 `snapshot_text` 只减少约 7.2%；点路径投影则减少约 99.1%。这一能力应保留。

但拼错 `fields=bazi_birth.day_mastr` 会返回 HTTP 200 和 `bazi_birth={}`，没有警告。Agent 可能把错误路径当成领域数据缺失。当前投影在计算结束后执行，主要节省传输与上下文，不会省掉前面的计算工作。

**建议：** 发布可发现的返回路径/视图；支持严格投影或返回 `unknown_fields` 提示。新增 `view=summary|structured|full` 等显式输出选项，保持旧接口默认兼容；只有测得生成快照开销明显时，再将可跳过的文本生成下推至服务层。

### P2：MCP 缺少执行语义声明

80 个 MCP 工具都没有 annotations。建议为纯本地计算/查询工具声明 `readOnlyHint`、`destructiveHint` 和 `openWorldHint` 等，使 host 更容易判断执行性质。

**应分开表达环境副作用与结果确定性：** MCP 的 `idempotentHint` 指重复调用对环境没有额外影响，并不保证返回结果字节相同。六爻 `method=coin` 未提供 seed 时会随机起卦；部分时运默认取当前时间；每次 run_metadata ID 也会变化。可另加 `deterministic` / `requires_seed_for_replay` / `uses_current_time` 元数据，不能用一个幂等标签覆盖所有含义。

具体 annotations 和结构化输出均可在 [FastMCP 工具文档](https://gofastmcp.com/servers/tools) 中找到支持。

### P2：运行元数据有定位作用，但尚不足以完整复现

`services/run_metadata.py:115` 为成功响应生成新的 run_id / trace_id，并附加工具名、时刻、引擎和近似标志。当前未记录包/算法/契约版本、输入归一化摘要、星历数据版本、执行耗时；trace_id 没有从请求传播到多工具调用与错误响应。

已有时间调整、来源、星历模型和部分规则标志不能说成“完全没有溯源”，但分布在不同业务 payload 中，投影后可能消失。六爻已返回掷币结果，已有分析日期字段也可显式固定，都是可复用的基础。

**建议：** 在统一元数据中增加 package_version / schema_version、effective time context、规则口径、数据版本、耗时和标准 warnings；支持调用方 trace 与子调用关系。按工具说明固定分析日期、seed/掷币结果、时间政策和依赖版本的重放方式。无需为此强制引入数据库。

## 功能层的优化空间

### 1. 将已有 profile 能力提升为共享服务

CLI 的 `profile` 和 subject-file 已解决一部分“一份出生信息、多套计算”的需求，但它们未进入中央目录，也没有 REST / MCP 对应入口。profile 为每个分支调用服务、在最外层附加一次元数据；可以提升为受 ToolSpec 管理的复合服务，定义每个分支的成功/错误状态、输入适用性与执行政策。

八字专项每次在 `services/bazi.py:969` 构建 BirthComputationContext。单次服务内部已有复用，而跨多个专项请求仍会重复构建。共享复合请求内可以先归一化出生信息、建立相应 context，再输出指定维度；实际性能收益需要基准测量。优先请求内复用，避免贸然缓存个人数据或引入账户存储。

### 2. 择日增加“搜索候选”的高层功能

当前 `astro_election` 是**单个候选时刻评分器**，不会搜索“接下来一个月适合签约的三个时段”。这个功能边界在服务和请求模型中很清楚，但场景文档的“什么时候适合做某事”容易让 Agent 期待完整搜索能力。

可增加可选的范围搜索：时间区间、当地时区、时间窗口/步长、主题、地点、最大候选数、Top-K；复用现有单时刻 scorer。返回候选、评分因子、排除原因和执行预算。先设候选上限，慢任务确有需求时再考虑异步作业、进度与取消，避免 Agent 自行无上限逐分钟循环。

### 3. 支持出生时刻不确定的显式工作流

目前大多数命盘要求 `birth_hour`，并默认 `birth_minute=0`。API 尚无“出生时刻未知/大致在一个时段”的契约。Agent 处理普通用户资料时容易为了满足必填而填入任意时刻。

建议按算法能力提供 `time_precision=exact|hour|range|unknown`，先返回适用能力和所需澄清；允许的无时结果只包含不依赖精确时刻的字段，受影响字段附上缺失原因。范围模式可比较指定时间段中的稳定结论与变化结论；需要逐算法确认，不能只是把 hour 改成 Optional。

### 4. 区分计算精度、传统规则解释与评分含义

当前输出中包含原始位置、传统规则判断、配合度/择日等 0–100 评分和建议性文本。MCP 总说明说“只输出计算数据，不包含建议”，而择日响应具有 `recommendation`；描述口径需要对齐。

建议为结果声明 `interpretation_kind`、规则来源/版本、score_semantics 和 itemised evidence。星历高精度只描述天文计算；传统评分不是已校准的现实事件概率，多体系一致也不能自动转换成统计置信度。返回契约应帮助 Agent 保持这些区别，同时保留已有可解释的因素与权重。

## 开发者集成与运行边界

- **OpenAPI 未描述实际认证。** REST 已有 optional API Key middleware，但导出的 `securitySchemes` 为 null，客户端生成器和交互文档无法从契约获知鉴权。应按配置声明 APIKey security，保留健康/文档等例外。
- **错误响应文档不完整。** 业务操作 schema 目前只列 200 / 422，而运行时可能产生 400 / 401 / 500 / 503 / 504；需要从共享错误分类生成响应说明。
- **版本策略需固定。** 包和 FastAPI info.version 是 0.2.0，现有路径没有公开 API 版本。为输入严格化、输出结构化和返回视图建立兼容政策；新版本可保留旧路径别名。operationId 应采用显式稳定名称。
- **SDK 先依赖正确契约。** 完善 OpenAPI 后生成薄 Python/TypeScript 客户端，统一错误类、输出投影、超时和有限重试；不必先手写一套巨大 SDK。
- **服务定位决定部署要求。** stdio MCP / 本地 CLI 已适合本机工具调用。REST 有重计算 semaphore，但没有执行 deadline、排队上限或内置请求限流；默认监听 0.0.0.0，认证需配置。仓库 SECURITY.md 已说明网关边界。面向网络开发者时应给出可直接采用的 TLS/认证/请求大小/限流部署范例，而不是将本地工具要求成多租户平台。
- **并发不等于线性加速。** Swiss Ephemeris 已有共享锁保护，新的 batch / range search 要尊重它。CLI/MCP/REST 执行策略和限额可共享；基准之后再决定线程、进程或作业模型。本次没有进行负载测试。

## 建议实施顺序

| 阶段 | 工作 | 验收结果 |
| --- | --- | --- |
| 第一阶段：可靠调用 | MCP 错误标志、机器错误信封、安全字段错误、主题枚举与未知输入政策 | 错误不伪装成功；Agent 能按字段纠错；非法主题不变更任务 |
| 第二阶段：公开契约 | ToolSpec 输出模型、结构化 MCP、投影 schema、OpenAPI auth/错误/operationId、版本基线 | 客户端能生成实际响应类型；跨端同一错误码和可解释的差异 |
| 第三阶段：控制上下文 | 渐进发现、场景 manifest、核心工具配置、输出视图与投影校验 | 常见场景无需加载全部长尾 schema，也无需取得全部快照 |
| 第四阶段：高层功能 | 共享 profile/context、有限择日搜索、时间精度、重放与追踪 | 用户意图转成少量有预算、有证据的调用 |

在第二阶段保存版本化 OpenAPI / JSON Schema，并建立真实客户端的契约与破坏性变更检查。Agent 评估至少覆盖“信息不足→追问”“选择主工具→避免重复”“非法参数→纠错”“依赖不足→识别不可用”“结果降级→保留限制”“单候选与范围搜索的区分”。

## 验证和产物

环境：Python 3.13.5、FastAPI 0.138.0、FastMCP 3.4.2、Pydantic 2.13.4、Kerykeion 5.12.9。调用全部在本机 TestClient / in-memory MCP Client 中完成，无生产写操作、未验证外部 MCP host 或发布服务。

- [复现脚本](audits/2026-10-09/agentic-api/probe.py)：导出 schema，执行 REST / MCP 的正反例并记录行为。
- [摘要与环境](audits/2026-10-09/agentic-api/summary.json)、[REST 原始结果](audits/2026-10-09/agentic-api/rest-probes.json)、[MCP 原始结果](audits/2026-10-09/agentic-api/mcp-probes.json)。结果仅使用虚构/测试输入。
- [OpenAPI](audits/2026-10-09/agentic-api/openapi.json)、[能力目录](audits/2026-10-09/agentic-api/manifest.json)、[MCP 工具 schema](audits/2026-10-09/agentic-api/mcp-tools.json)。
- [pytest 输出](audits/2026-10-09/agentic-api/pytest.txt)：103 passed，5 个依赖/框架 warnings。
- [API linter 输出](audits/2026-10-09/agentic-api/lint.json)：0 errors、756 warnings、4 info；754 条是 naming 类，不能视为 754 个实际缺陷。不建议为满足其 camelCase 偏好破坏当前 Python 风格字段。
- [通用 REST scorecard](audits/2026-10-09/agentic-api/scorecard.json)：52.78 / F。该工具只读取 OpenAPI，无法看见认证 middleware、实际数值计算、MCP/CLI、场景技能，也对分页/缓存等作通用假设；**这不是本报告对产品质量或 Agentic 程度的评分**。它对 auth 文档等缺口有提示价值。
- 仓库未提供可用于版本比较的历史 OpenAPI 基线，本次未运行无意义的同版本 breaking-change 对比；不声称证明了历史兼容性。

本次只新增审查报告与证据文件，没有修改 API、算法或运行配置。
