# FateBridge 代码与文档清理审查

日期：2026-10-12。审查对象为 `/Users/thomas/Desktop/FateBridge` 当前工作区，HEAD 为 `204635e2073a1ef33a0e2ef86bb98fced27e7618`，包含大量未提交的 Agentic 合同、输出模型及风水功能。结论不能只套用到该提交本身。本次没有修改仓库代码、文档、依赖或测试；报告和探针单独保存在本聊天的文件目录。

**结论：存在明确的清理与优化空间。优先处理稳定 Schema 的重复生成、测试维持的兼容入口和导入边界，再处理小型遗留代码与文档归档。没有证据支持直接批量删除所有带 legacy / compatibility 名称的实现。**

本次覆盖中央目录、REST/MCP/CLI 注册与执行、输入/输出合同、复现元数据、服务编排、核心算法模块的调用引用、依赖声明、全量本地测试、CI 配置、公开文档、技能引用及审计附件。没有重新进行所有算法的第三方数学正确性审查，也没有验证外部使用者是否依赖 Python 直接导入路径。

优先级 P2 表示值得优先安排的维护或性能问题，P3 表示后续整理；本报告没有发现需要按 P0/P1 紧急处理的清理项。每项的“仓库内无使用”均不等于“仓库外无人使用”。

| 顺序 | 项目 | 判断 | 优先级 | 建议动作 |
| --- | --- | --- | --- | --- |
| 1 | 每次执行重建 Schema / contract digest | 已实测开销 | P2 | 按模型身份缓存稳定合同与摘要 |
| 2 | 完整能力发现重建所有 Schema | 已实测开销 | P2 | 缓存合同；继续使用摘要/按需发现 |
| 3 | MCP `.fn` 文本外壳与异步导入适配 | 已证实测试依赖及运行警告 | P2 | 迁移测试后退出兼容外壳 |
| 4 | REST 17 个直接调用别名和旧导出 | 仓库测试仍依赖 | P2 | 将测试转向真实路由/标准执行入口 |
| 5 | helpers 转导出层 | 22 个转导出名被 22 个源文件继续消费 | P2 | 先迁移内部导入，再决定对外保留范围 |
| 6 | predictive 大量星号导入与聚合导出 | 使用边界隐式 | P2 | 显式导入、明确公开接口 |
| 7 | API 提前加载域服务，抵消目录延迟导入 | 已核实导入状态 | P3 | 分离旧导出与 readiness 检查的依赖 |
| 8 | 旧扁平 `/api/calculate` 与关系盘旧别名 | 公开接口仍有文档和测试合同 | P2 | 制订退役合同，不能当死代码直接删除 |
| 9 | `iztro-verify` 旧 extra | 当前验证流程不用它 | P3 | 移除旧额外依赖及过时安装指引 |
| 10 | 小型旧入口、无效参数与不可达分支 | 有具体调用证据 | P3 | 小批次删除并保留当前行为覆盖 |
| 11 | 输出校验与元数据附加的重复职责 | REST 第三次校验重复 | P3 | 保留不同边界检查，移除同边界重复 |
| 12 | 小型无用 import / 测试路径注入 | 有确定项及需区分项 | P3 | 精确清理，避免 AST 误报 |
| 13 | 双人分析中的两套关系识别逻辑 | 活跃业务重复，评分并不相同 | P2 | 共用关系事实，保留评分策略 |
| 14 | 大文件及执行层依赖方向 | 维护问题，非删除理由 | P3 | 按职责拆分，保持信源与合同 |
| 15 | 审计材料、导航与重复文档数字 | 存储和查找负担明确 | P3 | 建索引、去重/归档、生成固定表格 |
| 16 | 文档示例测试依赖 shell 的解释器 | 已复现环境误失败并重跑通过 | P3 | 子进程绑定项目解释器 |

**1. 稳定 Schema 在每次业务调用中重新生成，是最优先的性能优化项。**

证据：[execution_receipt](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/replay_metadata.py:183) 每次调用都执行 `spec.request_model.model_json_schema()`、`spec.output_model.model_json_schema()`，随后计算 `contract_sha256`。实现和数据指纹已有进程缓存，合同摘要没有。

保存探针预热后的五次中位数如下。业务时长为当前 receipt 记录的 `duration_ms`；总时长为 `execute_tool` 的本地同步调用时长，不是网络请求延迟。

| 样例 | 业务执行 ms | receipt 生成 ms | execute_tool 总时长 ms |
| --- | ---: | ---: | ---: |
| gua_lookup | 0.078 | 5.396 | 5.606 |
| bazi_birth | 0.828 | 11.944 | 13.146 |
| fengshui_directions | 0.169 | 8.985 | 9.285 |

独立 cProfile 探针也把卦义查询的 receipt 累计时间定位到 Schema 生成，不能把上表所有 receipt 时间都认定为仅 Schema 的成本。样例很轻，也经过预热；这些数字不能推广成重型西占计算的百分比收益。

建议缓存输入/输出模型对应的合同摘要，按实际模型类及相关配置区分，避免仅按工具字符串缓存后忽略模型覆写。复用 Schema 时防止调用方修改共享 dict。输入摘要、业务输出摘要、时间、seed、trace 等仍须逐次计算，不能缓存用户结果。验证应检查摘要完全相等、模型变化后的摘要变化、元数据生成异常仍归类为服务端错误，以及实际调用次数与耗时。

**2. 能力发现的完整响应应复用稳定合同，摘要模式则已经有效。**

证据：[describe_spec](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/tool_spec.py:722) 每次展开输入/输出 Schema，[discover_specs](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/discovery.py:104) 对筛选后的工具逐个描述。保存探针结果：

| 模式 | 紧凑 UTF-8 JSON | 本地生成时间 |
| --- | ---: | --- |
| 全目录 summary | 72,801 字节，约 71.1 KiB | 0.4–0.7 ms |
| 全目录 full | 2,268,806 字节，约 2.16 MiB | 首次约 1.15 s，后两次约 0.75 / 0.79 s |
| 单工具 bazi_birth full | 28,856 字节，约 28.2 KiB | 10.6–14.3 ms |

这是本地生成耗时和 JSON 字节数，不是 token 数、网络延迟或部署性能。新嵌套合同提供了实际的校验价值，不宜为缩小响应删除合同。现有先筛选后展开、summary、MCP family/scenario profiles 都应保留；优先复用第 1 项合同缓存。客户端接入文档继续推荐 summary → 单工具合同。原生 MCP tools/list 有自己的协议要求，不能把全部工具的参数/输出合同随意去掉。

`parameters` 与 `input_schema` 是另一处双重表示，未来有版本化发现接口时可收敛；当前不建议无通知改变 full 的公共结构。

**3. MCP 的旧 Python 调用外壳已经成为可退出的兼容层。**

证据：[旧元数据适配](/Users/thomas/Desktop/FateBridge/src/fatebridge/mcp_server.py:143) 枚举已注册工具，注入模块属性及 `.fn/.parameters`，还为已有事件循环增加线程池分支。[原生工具包装](/Users/thomas/Desktop/FateBridge/src/fatebridge/mcp_transport.py:149) 先调用返回 JSON 字符串的旧函数，再 `json.loads`，转为原生 structuredContent。当前全工具表面测试仍有 `.fn` 路径，但也已有真正 FastMCP Client 全工具路径。

已在独立子进程复现：在运行中的事件循环内导入 `fatebridge.mcp_server`，会产生 `RuntimeWarning: coroutine '_attach_fastmcp_legacy_metadata.<locals>._load_registered_tools' was never awaited`。原因是先构造协程并交给 `asyncio.run`，运行中事件循环使 run 提前抛异常，原协程未被等待；随后才走线程池补救。

建议将内部执行结果保持为 dict，最后从同一份 dict 派生 text JSON 与 structuredContent。迁移 `.fn` 测试至标准 `execute_tool` 或原生 Client 后，可退出模块级外壳、`__fb_legacy_fn__` 标记及为它服务的异步/线程池逻辑。text JSON 与 structuredContent 双表示是已公布的对外返回合同，不应和旧 `.fn` 入口一起删除。

外部 Python 集成依赖情况尚未核实；在退出外壳前需明确公开支持的接口范围。如暂时保留，至少先解决未等待协程问题。

**4. REST 直接调用别名主要是在维持旧测试入口。**

证据：[api.py 的别名表](/Users/thomas/Desktop/FateBridge/src/fatebridge/api.py:711) 包含 17 个旧 handler 名称。这些别名不负责注册 HTTP 路由；真实路由由中央目录挂载。仓库测试直接调用 `calculate_destiny`、`calculate_relative_chart` 等 coroutine。api 顶部还转导出 44 个 request model，以及用于 identity 检查的服务函数。

建议先把请求模型 import 改到 `core.request_models`，业务身份检查改到 canonical service 模块，路由行为测试通过 TestClient 执行；明确测注册器时直接测 `make_rest_handler`。随后可删除别名表和仅为它们保留的导出。

不要为了清理而丢掉线程池卸载、重计算并发限制、HTTP 错误、默认值和字段投影覆盖；这些是现存测试的实质价值。仓库内观察到的旧 handler 使用以测试为主，不能据此证明外部库用户没有使用。

**5. helpers 的“兼容出口”仍被生产代码广泛使用。**

证据：[helpers 转导出](/Users/thomas/Desktop/FateBridge/src/fatebridge/utils/helpers.py:17) 从 errors / house_systems / places / timezones 导出 22 个名称。静态导入核查发现 22 个当前源文件仍通过 helpers 消费这些已经拆出的名称，包括服务、core、CLI。

建议迁移 `calculation_guard/handle_calculation_error` 到 errors，地点常量/解析到 places，宫制到 house_systems，时区解析到 timezones。保留 PersonInfo、出生时间归一化等 helpers 自身定义的职责。先让内部源代码不再消费转导出层，再按公开 Python 接口政策决定是否保留少量明确出口。

直接删掉转导出 import 会破坏当前生产代码；这不是单纯无用 import。不要额外复制一份实现来“消除依赖”。

**6. predictive 的星号导入使拆分后的边界仍然隐式。**

证据：[predictive/__init__.py](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/predictive/__init__.py:5) 从 `_common` 和各技法模块星号导出，各子模块也从 `_common import *`。`_common` 没有 `__all__`；其中的 math、Counter、timedelta、swe、RULER_BY_SIGN 等可能通过星号被其他模块消费。

这会让静态“未用 import”检查失真，也使普通导入间接加载全部技法。建议子模块明确导入所需类型/常量/函数，聚合入口明确导出真正公共 builder，并把 readiness 对后端状态的访问指向唯一模块。禁止直接按 `_common` 的局部 AST 报告删除其 import。

**7. API 的旧服务导出部分抵消了目录延迟导入设计。**

证据：[API 服务转导出](/Users/thomas/Desktop/FateBridge/src/fatebridge/api.py:99) 提前导入 astrology / bazi / western_timing；[readiness](/Users/thomas/Desktop/FateBridge/src/fatebridge/api.py:332) 也引用 predictive 聚合模块。独立新进程中，导入中央目录约 0.14 秒且未加载 kerykeion；导入 api 约 0.48 秒且已加载 kerykeion。时间仅为单次本地观察，加载状态是确定证据。

建议结合第 4、6 项减少不必要提前导入，再评估 readiness 是否能在检查阶段解析后端状态。readiness 仍需报告真实可用性，不能只检查 package 是否存在而忽略运行时失败。readiness 本身会造成一部分必要加载，不能把全部导入成本归因于兼容导出。

**8. 旧 HTTP 响应与关系盘别名具备退役价值，但仍是公开合同。**

证据：[calculate_legacy](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/tool_catalog.py:528) 保留 `/api/calculate`、扁平转换和 `metadata_name='analyze_destiny'`；[API 参考](/Users/thomas/Desktop/FateBridge/docs/api-reference.md:127) 明确说明它与 `bazi_birth`、综合 `analyze_destiny` 的区别。关系盘还保留 `relationship_mode`、数值模式和旧 camelCase 参数，其中 `relationship_mode='synastry'` 与新的 `relative_mode='synastry'` 具有不同解释。

值得收敛的地方是同一能力需要维护多种命名/形状，以及旧 provenance 标签与实际服务名称不一致。但缺少外部调用记录，不能证明这些入口已经没人使用。当前 ToolSpec 没有统一退役字段；旧入口主要通过说明文本提示。

建议先给目录和公开发现建立 deprecated / replacement 的统一信息，在 OpenAPI 标记旧路由，并记录版本化退役策略。真正删除时同步 request model、binder、结果转换、CLI、复现策略、文档和旧快照，不能只删路由。关系盘旧别名不能直接重定向到新语义，必须显式说明迁移映射。

**9. 旧 iztro 验证 extra 可清理；multipart 直接声明可评估，但不会让它消失。**

证据：[pyproject.toml](/Users/thomas/Desktop/FateBridge/pyproject.toml:58) 把 `iztro-verify` 标成 legacy。当前 horoscope oracle 使用固定 JS iztro 2.5.8；brightness 生成器采用来源表的独立转录。没有当前执行代码 import py_iztro，只剩生成器里建议安装 extra 并自行适配的旧说明。

建议删除这一可选 extra 与过时安装段，保留来源版本、JS generator、固定 fixture 和第三方比较材料。不要因旧 verifier 已退出而删除真正的 oracle。

`python-multipart` 没有 FateBridge 的直接 Form/File/UploadFile 消费，根项目直接依赖声明可在安装/floor 检查后收敛。但当前 mcp 和 fastmcp-slim server 本身都依赖它，删除根声明不代表从环境中删除这个包，也不能宣称显著减小依赖体积。

`pytz` 被 predictive / Kerykeion 使用，dateutil 被时区解析使用，lunardate 是历法实现依赖，Kerykeion `<6` 是适配器与数值基线边界；不能用“看起来旧”作为删除它们的依据。

**10. 已找到几处小型遗留逻辑，适合独立清理。**

| 位置 | 现状 | 判断与动作 |
| --- | --- | --- |
| [calendar.calculate_month_pillar](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/calendar.py:84) | 仓库内无调用，使用整月 → 地支固定映射；`MONTH_BRANCHES` 仅供它使用 | 可退出旧便捷入口及表，保留实际节气驱动的月柱路径；外部直接 Python 调用未知 |
| [build_pseudo_chart](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/local_techniques/chart.py:635) | 转发到统一 chart runtime，只有转导出和一个旧入口测试消费 | 可在明确 Python 公开接口后移除 wrapper 与仅锁 wrapper 的测试；保留 suzhan/otherbu 实际精度覆盖 |
| [关系类型建议私有方法](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/compatibility.py:968) | 立即 `del detailed_analysis`，调用方仍传入该参数 | 删除无用参数，按实际“生成建议”的职责命名；当前关系类型与建议输出保持一致 |
| [compatibility 上游错误扫描](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/compatibility.py:43) | `_render_destiny_analysis` 直接构建成功 dict；异常由外层 calculation_guard 捕获 | 当前内部调用路径下 error-envelope 扫描已无实际来源，可删除旧传播分支；保留外层异常转义测试 |
| [export_parser 章节归一化](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/export_parser.py:104) | 对同一个 selected section 最多重复调用三次 map_legacy_section_title | 一次归一化后再筛选；保持 forbidden/顺序/去重和旧标题映射 |

前两项是仓库内部无业务调用的公共便捷入口；后三项是有调用链依据的内部代码整理。不能把它们的证据强度混为一谈。

**11. REST 第三次完整输出校验可以收敛，前两次具有不同职责。**

证据：[execute_spec](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/tool_spec.py:352) 校验业务输出，[execute_tool](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/tool_spec.py:429) 附加 receipt 后再校验，[REST handler](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/tool_spec.py:849) 对已经附过 metadata 的相同结果再次校验。

原生调用探针确认：REST 八字样例 3 次，MCP 2 次，每次约 0.11–0.14 ms。业务合同验证和 receipt 合同验证并非完全重复；优先评估删除 REST 最后一次同边界验证。metadata 在 REST/MCP renderer 中还会再次调用 attach_run_metadata，但已有 metadata 时函数直接返回，因此不能把它说成多次昂贵遍历。

不建议删除原生客户端/协议输出校验，也不建议未经设计就删掉 MCP 前置输入校验；后者承担避免框架回显请求内容和规范错误的职责。

**12. 可以精确删除的 import 与测试模板残留。**

确定的局部无使用候选包括：[cli.py 的 execute_spec](/Users/thomas/Desktop/FateBridge/src/fatebridge/cli.py:36)、[mcp_transport.py 的 BaseModel](/Users/thomas/Desktop/FateBridge/src/fatebridge/mcp_transport.py:9)、[almanac.py 的 cast](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/almanac.py:14)，以及 api.py 中非兼容声明的 BaseModel / describe_spec / mcp_specs。API request model 和 helpers 转导出则是有意公开出口，不能一起当无用 import 删除。NoReturn 在字符串注解中使用，也不是死 import。

30 个测试文件仍有重复的 `sys.path.insert(0, repo_root)`。根 conftest 已说明它负责让 pytest 能 import `tests.*`；FateBridge 的 src package 则靠 editable 安装，重复插入仓库根并不能替代装包。可在确认不支持直接执行测试文件的前提下统一去除。脚本里路径注入需分别看是否要 import 仓库测试 fixture，不应批量删除。

mypy 本轮还提示 `dateutil.*` / `lunardate.*` override 未使用。这是配置整理候选，不能仅依据一个已装 types/依赖版本的环境就删除所有 ignore_missing_imports；需核对 floor 环境。

**13. 合盘中两套传统关系事实识别值得共用，不能直接合并分数。**

证据：[AdvancedCompatibility](/Users/thomas/Desktop/FateBridge/src/fatebridge/analysis/compatibility.py:134) 自行遍历六冲、六害、三刑并参与综合权重；[BaZiRules.calculate_compatibility_score](/Users/thomas/Desktop/FateBridge/src/fatebridge/core/rules.py:1621) 另有一套识别、奖惩和总分；[service](/Users/thomas/Desktop/FateBridge/src/fatebridge/services/compatibility.py:72) 同时返回两者。源码仍留有“calculate_compatibility_score 可能还没有更新，我们手动计算”的过时维护理由。

重复的是关系事实提取的部分流程，两套评分的覆盖面/权重并不相同。建议把跨两盘关系事件、来源位置、去重策略提为共同事实，再让两个评分策略消费；保留 public 的 overall / normalized / traditional 分数语义。三刑是否由两方共同构成、重复地支和组合去重是必须保留的回归边界。

**14. 大文件和职责方向可以继续整理，但不建议为行数重写算法。**

当前大文件包括 astrology.py 3,457 行、services/timing.py 2,028 行、request_models.py 1,769 行、rules.py 1,753 行、tool_spec.py 1,132 行。行数只说明阅读/改动跨度，不证明文件有 bug。

可先拆 services/timing 中约五百行快照文本构造，request_models 按领域拆分，tool_spec 按工具定义/绑定、执行合同、发现、transport registrar 拆职责。core/tool_spec 当前内部 import services.replay_metadata / run_metadata 以及 mcp_transport；运行成立，但执行合同与 transport 注册耦合使目录和命令行容易受传输改动影响。建议独立公共执行单元与薄注册器，保持一份实现和一份合同。

拆分时同步迁移内部使用，避免继续增添无边界的兼容出口；真实数学算法、规则来源和数值输出应保持一致。

**15. 文档的主要问题是历史附件堆积与导航，当前计数和文件链接没有发现漂移。**

按 Git 已跟踪 + 非忽略未跟踪文件统计：docs 187 个文件、26.07 MiB，其中 audits 约 25.8 MiB；包源代码和数据合计约 2.59 MiB。审计文件是主要的文档存储体积。

已发现五组超过 1,000 字节的完全相同附件：10-09 results 与 post-fix 的 skyfield.json / returns.json / angles.json / taiyi_live.json，以及 10-12 两次验证中的同一玄空比较 JSON；合计可避免重复约 0.40 MiB。多个时期完整 OpenAPI / capability / MCP Schema 文件虽未必字节相同，也重复保留大量已生成定义。

建议每次审计保留范围、commit/工作区身份、依赖版本、命令、结果、差异及摘要；完全相同数据保留一个内容寻址实体，其余记录引用 hash。较大原始 Schema 可压缩或转为可恢复附件，但必须保留审计报告引用与第三方比较的原始证据。不能删旧结论或 Taiyi 尚未解决的分歧，不能把早期阶段的“未提交”文字未经证据改成“已发布”。

用户文档可以做两项具体改善：

- [docs/README.md](/Users/thomas/Desktop/FateBridge/docs/README.md:9) 的入口尚未收录新风水主文档、玄空文档，审计索引也主要列 10-09 的两个记录；建议补当前领域入口和统一审计索引。
- 当前工具数实测为 catalog 89 / REST 87 / MCP 87 / CLI 88，主文档与之相符。已有计数测试很好，但其 CHECKS 主要锁 REST/MCP/family，并未锁散落的 catalog/CLI 计数。可扩展校验，或由目录生成固定工具表/计数，领域解释仍手写维护。

本轮扫描公开 Markdown 的文件链接，没有发现不存在的文件链接。该扫描不等于全部章节锚点验证、外部 URL 存活性检查或每段示例参数验证。

**16. 文档示例测试的解释器应固定，避免环境误失败。**

证据：[test_documented_cli_examples_run_clean](/Users/thomas/Desktop/FateBridge/tests/test_skills_engine_contract.py:146) 通过 `shell=True` 执行文档中的命令，`python3` 从 PATH 解析，而非由运行 pytest 的 sys.executable 决定。

本次先用项目 `.venv/bin/python -m pytest` 执行全量测试，但未把 venv 放在 PATH 前面；该测试启动了未安装 FateBridge 的系统 Python 3.14，因 ModuleNotFoundError 失败。补上 PATH 后同一测试通过。这是环境耦合证据，不是当前文档业务示例错误。

建议用 shlex 解析受支持的示例命令，将 python / python3 替换为 sys.executable 并用参数列表执行；如果测试目标包括 shell 语法，另保留明确的 shell 用例。文档继续说明安装/激活环境要求。

**应保留的实现和证据。**

- `services/compatibility.py`、`analysis/compatibility.py` 是双人配合的领域功能，compatibility 不是旧软件适配层的含义。
- export 的旧章节映射是有版本信息、真实输入和测试覆盖的数据迁移合同；可归一化一次或改为声明式表，不能盲删。
- `legacy_reference / legacy_equatorial` 主限方法名、太乙宫序、紫微旧星曜展示字段等可能承载计算/输出合同，需分别证明替代关系；本次未得到删除证据。
- FastMCP 3.0 floor 所需的 ProtocolResult、递归 Schema 序列化兼容，服务于当前声明支持的依赖版本。要删除必须先改变支持范围并验证，和退出 `.fn` 测试外壳是两件事。
- shared execution clock、真太阳时省略/显式 sentinel、星历锁/路径恢复、approximate 标志和部分投影输出类型都有明确职责，属于应保护的边界。
- 第三方 fixture、独立比较脚本与分歧记录，以及有实际分支覆盖的测试，不应因文件老或数量多而清理。
- `.venv`、build、缓存目录和被忽略的 `八字/` 资料是本地生成物/参考资料，不是同一份生产源码；本次没有删除它们。

**建议分四批实施。**

1. 固定合同的 Schema/digest 缓存，清理确定无使用 import、无用私有参数、不可达 error 扫描与重复章节归一化。每项保持公开业务结果不变。
2. 迁移测试和内部导入：`.fn`、REST alias、helpers 转导出、星号导入；先保留真实路由、原生 MCP、错误及线程池覆盖，再退出旧出口。外部直接 Python 合同需要明确。
3. 独立处理公开旧 API 退役；如果用户选择不再支持旧客户端，再统一删除 legacy 请求/路由/转换/标签及旧合同记录。不要把这种行为变更混进纯性能优化。
4. 职责拆分、两套评分共享事实、文档目录与附件归档。保存可恢复的审计原件，数值变化另做独立审查。

不推荐一次大规模重排代码、刷新全部 golden、顺手升级 Kerykeion 主版本或删除所有旧名字。这些动作会掩盖行为差异，降低本轮清理的可审查性。

**本次验证记录。**

- Python 3.13.5 / macOS；FateBridge 0.2.0、FastMCP 3.4.2、MCP SDK 1.28.0、Pydantic 2.13.4、Kerykeion 5.12.9。
- 全量命令：`FATEBRIDGE_SKIP_GOLDEN_DIFF=1 .venv/bin/python -m pytest -q --disable-warnings`。结果：1 个环境失败、1,870 passed、89 skipped、7 warnings，耗时 243.60 秒。
- 单项修正环境重跑：`PATH="$PWD/.venv/bin:$PATH" FATEBRIDGE_SKIP_GOLDEN_DIFF=1 .venv/bin/python -m pytest -q tests/test_skills_engine_contract.py::test_documented_cli_examples_run_clean --disable-warnings`。结果：1 passed，7.58 秒。未完整重跑全量；已执行的 1,871 个非跳过测试最终均通过。
- black / isort 检查通过，black 检查 248 个 Python 文件；mypy 129 个源文件通过，并提示两项未使用 override。
- 原生 FastMCP Client 与 REST TestClient 的真实请求验证了校验次数、text/structured 一致性、正常错误标记；独立异步导入子进程复现了旧 facade 警告。
- 本轮没有运行 Linux CI、最低依赖环境、Linux golden 字节比对、外部 MCP host 或已部署服务测试；没有改写任何黄金快照。

当前审查探针与机器结果：[fatebridge-cleanup-probe.py](/Users/thomas/.codex/visualizations/2026/10/12/01a12f6d-02aa-7d50-9956-09a79dc54384/fatebridge-cleanup-probe.py)、[fatebridge-cleanup-evidence.json](/Users/thomas/.codex/visualizations/2026/10/12/01a12f6d-02aa-7d50-9956-09a79dc54384/fatebridge-cleanup-evidence.json)。在项目根运行 `.venv/bin/python /Users/thomas/.codex/visualizations/2026/10/12/01a12f6d-02aa-7d50-9956-09a79dc54384/fatebridge-cleanup-probe.py` 可重新生成本地性能/调用证据；结果只含 fixture 的统计与环境信息，不保存业务样例个人内容。
