# FateBridge Agentic API P2 优先项修复验收

日期：2026-10-12。对应 [原审查报告](agentic-api-review-2026-10-09.md) 的未知投影路径、渐进发现和 MCP annotations 三项优先问题；承接 [P1 验收](agentic-api-fixes-2026-10-12.md)。保留 `core → services → transports`、中央 `ToolSpec` / `CATALOG` 和现有入口，尚未提交、推送或部署。

## 本轮结果

| 问题 | 修复与兼容策略 |
| --- | --- |
| 未知投影路径静默返回空结构 | 默认保留旧的数据选择和成功状态，增加根级 `projection_warnings[]`；显式启用 `strict_fields` 后返回校验失败。三个入口共用路径验证与错误类型。 |
| 全目录 Schema 一次性加载 | REST 和 CLI 共用摘要、family、关键词、单工具与入口过滤；先过滤，再生成完整 Schema。MCP 增加发现 resources 和可选 family 配置。 |
| MCP 工具缺少执行提示 | `ToolSpec.execution_hints` 统一生成目录与原生 MCP annotations；当前所有 87 个 MCP 工具均声明只读、无破坏、幂等及封闭环境提示。 |

本轮证据快照包含 89 条目录记录：REST 87、默认 MCP 87、CLI 可执行 88。该数字包含工作区中同期新增的风水与玄空入口；其计算实现与研究证据属于独立工作，本轮没有修改计算规则或重写黄金数据。P1 报告及其历史数字保持原样。

## 投影契约

REST 使用 `strict_fields=true`；MCP 使用同名布尔参数；CLI 使用 `--strict-fields`，也支持显式 true / false 与 `--no-strict-fields`。默认 false。

| 调用结果 | REST | MCP | CLI |
| --- | --- | --- | --- |
| 合法投影 | 200，原业务 JSON | `isError=false`，结构化 JSON 与文本一致 | 退出 0，原业务 JSON |
| 无效路径，默认模式 | 200，附 `projection_warnings` | `isError=false`，附相同警告 | 退出 0，附相同警告 |
| 无效路径，严格模式 | 422，`validation_error` + `issues` | `isError=true`，同类错误与 issues | 退出 1，同类错误与 issues |
| 计算本身失败且路径也无效 | 保留原失败包络和状态 | 保留原失败包络与 `isError` | 保留原失败包络及退出 1 |

每个路径都按实际成功输出验证，避免静态 Schema 的可扩展字段被误拒绝。错误包括 `unknown_projection_path`、`invalid_projection_path` 和 `non_object_projection_path`；不会回显原输入值。空段、拼错字段、标量或数组下钻均可识别；数组只支持整字段选择。选择完整父对象不会掩盖同时提交的错误子路径，重复错误去重。

合法 null、空对象、整数组和动态扩展字段保持原样；省略 fields 或空集合保持原结果。`run_metadata` 仍完整保留，警告不会被投影裁掉。所有根输出模型公开可选 `projection_warnings`，包括新增风水根模型；未通过输出合同的结果仍先按 P1 内部错误处理。严格投影发生在计算之后，不是提前校验或算力预算机制。

## 渐进发现

- REST：`GET /api/tools?detail=summary`；支持 `family=bazi,knowledge`、`q`、`tool` 和 `surface=rest|mcp|cli`。省略 detail 仍返回历史完整记录。
- CLI：新增 `discover`，默认 JSON 摘要；支持 `--family`、`--query`、`--tool`、`--surface`、`--detail full`。`list --json` 共用发现结果；无参数 `list`、无参数启动及原 `describe` 入口保持兼容。
- MCP：`fatebridge://catalog/summary` 返回可见工具摘要；`fatebridge://families/{family}` 返回分类摘要；`fatebridge://tools/{tool}` 返回单工具完整合同。
- MCP 配置：省略或留空 `FATEBRIDGE_MCP_FAMILIES` 仍注册全部工具；设置 `bazi,knowledge` 只注册这两个 family，并让 resources 与实际暴露工具一致。REST / CLI 不受该配置影响。未知 family 在启动时失败。

摘要不包含参数展开、input_schema 或 output_schema；完整发现仍发布这些字段。`counts` 保持原全目录含义，新增 `matched_count` 表示当前匹配条数，`detail` 表示返回层级。未知 family / 精确工具名返回可纠正错误，正常搜索无匹配返回空列表。MCP resources 的不可见工具访问使用资源协议错误；它不属于工具调用的 `isError` 包络。

family 配置是在已有中央目录上选择注册范围；没有引入运行中工具加载、工具注册副作用或新服务。摘要 resources 为已连接客户端提供进一步发现，但不会改变 MCP 初始 `tools/list` 的协议；初始 Schema 体积缩减依赖显式 family 配置。

## Annotations 的含义

新增 `ExecutionHints` 默认声明 `readOnlyHint=true`、`destructiveHint=false`、`idempotentHint=true`、`openWorldHint=false`。注册器读取每个 ToolSpec 的配置，不硬编码所有未来工具；新增写入或外部访问工具应覆盖声明。原生工具同时按 family 设置 tag。

Annotations 是客户端提示，不提供鉴权保证，也不证明数值可复现；幂等性描述重复调用的副作用，不能推断带当前时间或运行 ID 的输出字节恒定。语义遵循 [MCP 工具规范](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)。

## 测量与验证

以下为当前目录 JSON 的 UTF-8 紧凑序列化字节数，不是 token、网络延迟或真实 LLM 成功率。

| 发现方式 | 字节数 |
| --- | ---: |
| REST 完整目录 | 895,715 |
| REST 全目录摘要 | 40,470 |
| REST 八字摘要，surface=mcp | 4,571 |
| MCP 默认 tools/list | 1,061,339 |
| MCP 八字 + 知识 profile，13 个工具 | 77,293 |

摘要比完整 REST 目录减少约 95.5%；示例 MCP profile 比默认工具列表减少约 92.7%。profile 不是相同工具集合的无损压缩，需按 Agent 的任务范围配置。

- [全量 pytest](audits/2026-10-12/agentic-api-p2/pytest.txt)：1123 passed、89 skipped、7 warnings；89 项全部要求 Linux-x86_64 / Python 3.12 黄金字节比较参考环境，当前为 Darwin-arm64 / Python 3.13。
- 新增 32 项 P2 测试涵盖三端警告与严格失败、合法投影兼容、错误优先级、摘要与完整发现一致性、无 Schema 摘要、原生 annotations、resources、实际进程的 family 配置和非法配置失败。已有 P1 合同及全入口测试同时覆盖当前目录的业务 JSON 与发布 Schema。
- [FastMCP 3.0.0 兼容测试](audits/2026-10-12/agentic-api-p2/fastmcp-floor-pytest.txt)：独立 Python 3.10.20 环境，61 passed；覆盖 P2、P1 合同、全入口及 MCP 修复。其他依赖是解析后的版本，不能视为全部依赖最低版本组合。
- [静态检查](audits/2026-10-12/agentic-api-p2/static-checks.txt)：mypy 119 个源文件通过，black 232 个文件通过，isort 与 `git diff --check` 通过。
- [可复跑探针](audits/2026-10-12/agentic-api-p2/probe.py)、[投影三端证据](audits/2026-10-12/agentic-api-p2/projection-probes.json)、[摘要目录](audits/2026-10-12/agentic-api-p2/summary-manifest.json)、[OpenAPI](audits/2026-10-12/agentic-api-p2/openapi.json)、[原生 MCP 工具](audits/2026-10-12/agentic-api-p2/mcp-tools.json)、[环境与体积](audits/2026-10-12/agentic-api-p2/summary.json)、[相关源文件哈希](audits/2026-10-12/agentic-api-p2/source-hashes.json)。

验证范围是本地 REST TestClient、真实 in-memory FastMCP Client 和实际 CLI 子进程。未运行 Linux 参考平台 CI、部署服务、外部 Agent host 或真实 LLM 对话。原审查 P2 中场景 manifest、长尾嵌套类型深化、确定性与 replay 元数据等仍待后续推进，本报告不将整个 P2 标为完成。
