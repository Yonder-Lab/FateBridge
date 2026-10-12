# FateBridge P2 场景 manifest、确定性与复现验收

日期：2026-10-12。承接 [原审查](agentic-api-review-2026-10-09.md)、[P1 验收](agentic-api-fixes-2026-10-12.md) 与 [P2 投影/发现/annotations 验收](agentic-api-p2-fixes-2026-10-12.md)。基于 `204635e2073a1ef33a0e2ef86bb98fced27e7618` 的本地未提交工作区；没有推送、发布或部署。

## 已完成

| 审查缺口 | 本轮结果 |
| --- | --- |
| 场景资料无法机器发现 | 从 8 个技能 YAML 接口和住宅路由文档生成 9 个打包场景；与实时 ToolSpec 关联 REST / MCP / CLI 入口、输入要求和主证/旁证/深调路由。 |
| 场景配置未贯通发现与执行集合 | REST `/api/scenarios`、CLI `scenarios`、MCP resources 共用 manifest；工具发现支持 scenario 筛选；MCP scenario 配置与 family 取交集，并明示缺失能力。 |
| 幂等性混同结果确定性 | 新增独立 ReproducibilityPolicy，声明时间默认与 seed 条件；不修改 MCP 副作用 annotations。 |
| 默认时刻或随机性无法固定重放 | 三端可选 as_of 固定默认时间；随机六爻生成并返回实际 seed，手动与时间起卦优先级保持。 |
| 元数据仅有运行标识 | 新增包/格式/合同版本与指纹、有效输入与业务摘要、耗时、实现/数据/依赖/星历库存、时间上下文、规则口径、警告与 replay 控制。 |
| trace 未贯通失败与子调用 | 有效调用方 trace / parent 标识传播到模型、领域、投影及内部失败；CLI profile 共用时间与 trace，子 receipt 指向根 run_id。 |

保持中央 `ToolSpec` / `CATALOG` 和 `core → services → transports`。新 execute_tool 包装已有 execute_spec，REST 仍通过原限流/线程池执行器卸载同步计算；execute_spec 保持无元数据的旧契约，直接调用领域服务仍沿用原时间行为。没有引入 Agent runtime、数据库、持久化历史查询或网络服务，没有修改数值规则、参考数据或黄金 snapshot。

当前快照为 89 条目录记录、REST / MCP 各 87 个业务工具、CLI 可执行 88 个，另有 9 个场景；数字包含同期独立风水/玄空工作。本轮没有认领其计算与参考资料改动。此前验收目录和历史报告保持原样。

## 场景来源与入口

生成器为 `scripts/build_scenario_manifest.py`，生成物为 `src/fatebridge/data/agent_scenarios.json`。生产读取包内 JSON，不新增 YAML 运行依赖；测试核对来源指纹、生成物、工具引用和路由角色。旧 Markdown 与技能接口继续作为源资料。

| 用途 | REST | MCP | CLI |
| --- | --- | --- | --- |
| 场景摘要 | `/api/scenarios?detail=summary` | `fatebridge://scenarios` | `scenarios` |
| 完整单场景 | `/api/scenarios?scenario=onda-shiyun` | `fatebridge://scenarios/onda-shiyun` | `scenarios --scenario onda-shiyun --detail full` |
| 场景候选工具 | `/api/tools?scenario=onda-shiyun&detail=summary` | 当前 profile 的 catalog/resource 发现 | `discover --scenario onda-shiyun` |

场景 ID 的逗号组合取并集，与 family / q / surface 取交集。未知 ID 明确失败。REST 嵌套、MCP/CLI 扁平孪生工具按中央目录的同操作关联实际名称。技能层 required_inputs 是采集指引，调用要求以各工具 required_parameters / 完整 Schema 为准。

路由保留主/旁/深角色、条件和替代组；替代组不是要求全调。MCP `FATEBRIDGE_MCP_SCENARIOS` 选择已有工具，省略或空值保留全部；同时配置 family 时取交集。resources 仅列可调用工具，部分能力通过 availability / available=false 标记，不会把缺失主证换成旁证，也不执行自动编排。

## 确定性与重放契约

REST 查询与 MCP 参数支持 as_of / trace_id / parent_run_id，CLI 支持同名连字符 flag。as_of 必须包含时区，统一为 UTC；各工具仍使用原民用时区、显式日期优先及部分日期默认规则。ContextVar 按调用隔离，异常后清理，不改进程时区或全局时钟。

正常默认调用捕获执行起点时间，不会把工具变成固定日期计算。无 seed 随机六爻仍随机，每次获得本次 seed；引擎与重放层共用手动输入判定，避免空白/非二进制卦码导致未记录的随机性。既有 seed、coins、lines、有效卦码及 time 起卦保持原优先级。

重放需保存原始请求与 receipt，将 replay.overrides 合并至原输入，再用 replay.as_of 调用。相同实现、数据、运行环境和星历配置下，业务 JSON 可核对；运行 ID、生成时间、耗时和“本次生成 seed”标志不承诺相同。generated_at 是实际执行时间，不是 as_of 的分析时点。

input_sha256 针对有效模型请求和影响真太阳时拒绝语义的显式字段状态，包括本次 seed；嵌套与扁平输入合同摘要不要求相同。business_output_sha256 在投影/快照删减前生成，排除 run_metadata，不可直接用部分响应验算。duration_ms 为绑定、计算及业务变换耗时，不是端到端延迟。

环境指纹包含包内 Python 源码、内置 JSON、依赖版本、Python / 平台和配置 `.se1` 库存内容；不返回服务器绝对路径。库存不能证明实际用到某文件，实际模型和规则/时间口径另外保留。指纹按进程缓存，更新后须重启；receipt 不是完整环境锁文件，不能保证版本相同的第三方安装内容或时区数据库完全相同，跨平台浮点仍可能微差。

trace_id / parent_run_id 为受约束的关联标识，不是历史查询或授权凭证。默认失败包络保持旧形状，调用方有效标识为可选增量字段；CLI 语法错误仍退出 2，框架非法 RPC / 未知工具仍按协议处理。元数据构造失败按内部失败处理，保留有效 trace，不将服务输出问题归为输入错误。

## 兼容性与成本

- 默认完整工具目录、无参数 CLI list、旧 describe、MCP `.fn` JSON 文本 facade、字段投影和 CLI --no-metadata 均保留。业务字段与计算规则保持；六个基础元数据字段保留，新增字段在 Schema 中为可选。
- 严格要求“元数据必须恰好只有六个字段”的客户端需要允许新增字段。输出 Schema 为部分响应兼容合同，不保证所有元数据扩展总是存在；直接 legacy helper 可只附基础元数据。
- profile 保留 CLI 批量入口，新增根/子关联；没有将其升级为 REST/MCP 复合业务工具，也没有按 run_id 自动加载原始输入。

当前紧凑 JSON 的 UTF-8 体积：

| 对象 | 字节 |
| --- | ---: |
| MCP 全工具合同 | 1,319,729 |
| MCP 健康场景 profile，5 个工具 | 48,608 |
| MCP 全场景完整 manifest | 129,566 |
| MCP 全场景摘要 | 5,444 |
| 示例八字 receipt | 2,024 |

这些是字节数，不是 token 或延迟。场景 profile 减少可见工具数量，并非相同工具集合的无损压缩；新增元数据也使极小投影响应增大，约 2 KB 的示例 receipt 是获得复现证据的实际成本。

## 验证证据与边界

- [全量 pytest](audits/2026-10-12/agentic-api-p2-replay/pytest.txt)：1314 passed、89 skipped、7 warnings。89 项全部要求 Linux-x86_64 / Python 3.12 黄金字节比较环境；本地为 Darwin-arm64 / Python 3.13，未重写黄金 snapshot。冻结时钟测试支架保留旧 fixture 的各时区固定墙钟语义，生产的单 UTC 瞬间与并发隔离由新测试单独覆盖。
- 新增 [29 项重放与场景测试](../tests/test_agentic_replay.py)：来源一致性、三端场景与过滤、原生 MCP profile/资源、实际启动进程、历史闰日时区和部分日期、随机/手动起卦、seed 重放、有效/非法控制项、trace 失败传播、并发隔离、输入隐私、环境/星历内容指纹、投影后口径保留与 profile 根/子关联。
- [FastMCP 3.0.0 / Python 3.10.20](audits/2026-10-12/agentic-api-p2-replay/fastmcp-floor-pytest.txt)：90 passed，覆盖本轮、前轮 P2、P1 合同与全业务入口。其他依赖为解析后的版本，不是全部依赖最低版本组合。
- [静态检查](audits/2026-10-12/agentic-api-p2-replay/static-checks.txt)：mypy 123 个源文件，black 239 个文件、isort 与 git diff --check 通过；生成物 --check 通过。
- [wheel 构建与隔离读取](audits/2026-10-12/agentic-api-p2-replay/packaging.txt)、[wheel 内容与哈希](audits/2026-10-12/agentic-api-p2-replay/wheel-verification.json)：确认场景 JSON 已打包，从解包 wheel 而非源码读取 9 个场景；使用当前环境依赖，没有上传包。
- [独立探针](audits/2026-10-12/agentic-api-p2-replay/probe.py)、[重放 receipts](audits/2026-10-12/agentic-api-p2-replay/replay-probes.json)、[失败关联证据](audits/2026-10-12/agentic-api-p2-replay/correlation-error-probes.json)、[场景 manifest](audits/2026-10-12/agentic-api-p2-replay/scenario-manifest.json)、[OpenAPI](audits/2026-10-12/agentic-api-p2-replay/openapi.json)、[原生 MCP 合同](audits/2026-10-12/agentic-api-p2-replay/mcp-tools.json)、[环境与测量](audits/2026-10-12/agentic-api-p2-replay/summary.json)、[源文件哈希](audits/2026-10-12/agentic-api-p2-replay/source-hashes.json)。

验证为本地 REST TestClient、真实 in-memory FastMCP Client、实际 CLI 子进程和 wheel 读取。未验部署服务、外部 Agent host、真实 LLM 选择率或 Linux 参考平台 CI。长尾专业输出的嵌套类型深化与显式输出视图仍可继续优化；本轮完成场景和复现优先项，不将整个审查或算法正确性标为全部验收。
