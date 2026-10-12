# FateBridge Agentic API 第一、二阶段修复验收

日期：2026-10-12。对应 [原审查报告](agentic-api-review-2026-10-09.md) 的 P1 可靠调用与公开输出契约问题。基于 `204635e2073a1ef33a0e2ef86bb98fced27e7618` 的本地工作区修改，尚未提交、推送或部署。

## 已完成

保留 `core → services → transports` 和中央 `ToolSpec` / `CATALOG` 架构，目录仍为 82 条记录，REST / MCP 各 80 个工具，CLI 可执行 81 个工具。没有调整计算规则或黄金基线。

| 原问题 | 修复结果 | 验证方式 |
| --- | --- | --- |
| MCP 领域失败被标成成功 | 原生 `isError=true`，同时返回结构化错误与等价文本；保留 `.fn` 文本兼容入口 | 真实 FastMCP Client 正反例，含默认 `ToolError` 行为 |
| 模型校验绕过统一错误包络 | MCP 前置 middleware 与 REST / CLI 共用安全校验错误转换 | 缺字段、越界、无效完整日期、未知字段、非法枚举 |
| REST 校验不能指导纠错 | `issues[]` 提供字段路径、错误类型、可选约束，不回显提交值或原始异常 | 三端纠错提示与隐私回归 |
| 非法主题静默换成另一项任务 | 择日 `topic_id`、卜卦 `category` 使用 Literal；服务层也拒绝未知选项 | REST / MCP / CLI 都失败，服务独立测试也不回退 |
| 普通请求的未知字段被忽略 | 请求模型统一 `extra=forbid`；CLI 普通未知 flag 仍按用法错误拒绝 | 三端 `birth_mintue` 拼错用例 |
| 成功结果没有机器契约 | 82 条记录均绑定输出模型；OpenAPI / MCP / manifest / CLI describe 发布 Schema | 80 个 REST 成功 Schema、80 个 MCP outputSchema，全 CLI 输出校验 |
| 服务输出违规容易被归为输入错误 | 投影前校验成功结果，违规通过 `OutputContractError` 归为内部失败 | 实际错误输出三端均为 `internal_error` |
| 未捕获异常的代码与重试策略不一致 | REST / MCP / CLI 使用共享异常分类，内部信息保持在服务日志中 | 内部故障、缺依赖、超时三端一致性测试 |
| OpenAPI 缺少集成信息 | 稳定目录 operationId、共享错误响应模型、按配置声明 API Key 需求 | 全目录 Schema 检查与启用鉴权配置测试 |

严格校验揭示关系盘原来会丢弃共享出生字段：现在明确接收已支持的 `gender` 标签与 `use_true_solar_time`，并在扁平 MCP / CLI 入口公开双侧太阳时选项。默认仍为民用时间；显式开启某一侧时，嵌套 REST 与扁平 MCP / CLI 返回相同的业务数据及实际修正标志。

## 三端行为约定

| 情况 | REST | MCP | CLI |
| --- | --- | --- | --- |
| 正常调用 / 合法投影 | HTTP 200，JSON | `isError=false`，结构化 JSON + 文本 | 退出 0，JSON |
| 请求模型校验失败 | HTTP 422，`validation_error` + issues | `isError=true`，同类错误 + issues | 进入模型后退出 1，同类错误 + issues |
| 领域计算拒绝 | HTTP 400，`validation_error` | `isError=true`，`validation_error` | 退出 1，`validation_error` |
| 输出合同违规 / 内部故障 | HTTP 500，`internal_error`，retryable=true | `isError=true`，相同代码和重试提示 | 退出 1，相同代码和重试提示 |
| 运行依赖缺失 | HTTP 503，`dependency_missing`，retryable=false | `isError=true`，相同代码和重试提示 | 退出 1，相同代码和重试提示 |
| 计算超时异常 | HTTP 504，`timeout`，retryable=true | `isError=true`，相同代码和重试提示 | 退出 1，相同代码和重试提示 |

REST 错误 body 保留顶层包络；MCP / CLI 可额外包含 `status_code`。CLI 未知 flag、缺少必填命令参数及 argparse 类型错误在模型校验之前发生，保留退出 2 / `usage_error`。未知 MCP 工具、非法 RPC 属于框架协议错误。超时测试验证异常分类，没有引入新的执行 deadline。

所有 CLI 可执行工具已用其对应代表输入逐项与可用的 REST / MCP 入口比较业务 JSON；只剔除每次重新生成的 `run_metadata`。嵌套关系盘另有三端等价验证。发现接口、输出投影、快照开关、省略太阳时标志的历史语义均有回归覆盖。

## 兼容影响与合同边界

- 省略可选参数继续采用声明默认值；显式非法主题、未知普通请求字段、无效完整公历日期会失败。老调用应清理之前被忽略的键。CLI subject/profile 文件仍按各工具选取字段，以支持跨工具资料复用。
- FastMCP Client 默认对 `isError=true` 抛出 `ToolError`。需要读取错误包络时用 `raise_on_error=False`，读取 `structured_content`；成功 JSON 文本及本地 `.fn` 兼容入口仍可用。
- 完整日期现在属于模型校验失败（422），而领域计算拒绝保留 400。客户端应按 `error_code`、`issues` 和 `retryable` 分支。
- 成功业务数据只验证，不从 Pydantic 模型重新序列化，避免注入 null、丢失扩展字段或改写数值。
- 输出合同包含每个工具的根字段，以及运行元数据、八字日主/命盘核心、行星、择日因子和快照导出等稳定结构。长尾专业字段仍是可扩展 JSON；为支持任意投影和 `--no-metadata`，公开业务字段为可选，不能据此断言完整响应的每个字段必然存在。
- 本次属于 Unreleased 修改，没有发布新包版本。严格输入与 MCP 失败行为的迁移说明已写入 CHANGELOG 和使用文档；本次保存带日期的 OpenAPI / MCP Schema 基线供后续比较。

## 验证证据

- [环境、覆盖数字](audits/2026-10-12/agentic-api/summary.json)：Python 3.13.5 / FastMCP 3.4.2 / FastAPI 0.138.0 / Pydantic 2.13.4。
- [全量 pytest](audits/2026-10-12/agentic-api/pytest.txt)：953 passed、82 skipped。82 项全部因 macOS 不满足 Linux-x86_64 / Python 3.12 黄金字节比较的参考平台要求而跳过；黄金 fixture 未被重写。
- [FastMCP 3.0.0 兼容测试](audits/2026-10-12/agentic-api/fastmcp-floor-pytest.txt)：独立 Python 3.10.20 环境，29 passed，对新增合同、全工具调用及 MCP 修复测试进行验证；其余依赖使用解析后的版本，不代表全部依赖最低版本组合或 Linux CI。
- [静态检查](audits/2026-10-12/agentic-api/static-checks.txt)：mypy 107 个源文件通过；black、isort 与 `git diff --check` 通过。
- [可复跑探针](audits/2026-10-12/agentic-api/probe.py)、[七组失败结果](audits/2026-10-12/agentic-api/failure-probes.json)、[OpenAPI 基线](audits/2026-10-12/agentic-api/openapi.json)、[MCP 工具基线](audits/2026-10-12/agentic-api/mcp-tools.json)。原审查证据保留在 2026-10-09 目录。

验证范围为本地 TestClient、真实 in-memory MCP Client、CLI 解析器与实际子进程。尚未验证部署服务、外部 Agent host 或真实 LLM 对话，不将本地回归等同于这些验收。

后续按原报告 P2 继续：严格投影路径、渐进发现与场景 manifest、MCP annotations、长尾嵌套类型深化和复现元数据。本次保留未知投影路径返回空结构的兼容行为，该问题没有被归为已修复。
