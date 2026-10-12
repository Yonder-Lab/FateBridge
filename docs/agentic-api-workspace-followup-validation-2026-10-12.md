# 原工作区后续改动的 Linux 与 PR #180 验证

日期：2026-10-12。承接[上一轮 Linux / CI 验收](agentic-api-linux-ci-validation-2026-10-12.md)，将此前未纳入 PR 的后续修改更新到[草稿 PR #180](https://github.com/Yonder-Lab/FateBridge/pull/180)。不合并、不部署，保留原 master 工作区的未提交内容。

## 受测范围

上一轮发现的 11 个文件属于随后完成的清理。相对 PR 旧 head `48c0eaa5c7726fcab2f9a6ee288a231f7dadd62b`，当前完整清理组合共有 **88 个执行文件**变化，包括关联导入迁移、合同缓存和兼容测试。本轮复制原工作区的实际文件到已附加的 PR worktree，包含这些依赖，未只摘取 11 个局部文件。

原工作区 Git head 为 `5fafc61f7bbbf24329103f46ccd87f02dc80daf2`，清理内容仍是未提交状态；不能用该 head 单独代表受测源码。369 个执行文件哈希与[清理验收快照](audits/2026-10-12/cleanup/execution-hashes.json)逐项一致，88 份黄金文件分别保存哈希。完整捕获见[范围记录](audits/2026-10-12/pr180-workspace-followup/capture.json)，执行哈希和黄金哈希分别保存在[执行清单](audits/2026-10-12/pr180-workspace-followup/execution-hashes.json)与[基线清单](audits/2026-10-12/pr180-workspace-followup/golden-hashes.json)。

保留 ToolSpec → services → core 架构。缓存只复用模型合同及合同摘要；输入、业务结果和执行 receipt 仍逐次计算。REST 保留业务结果与 receipt 附加后的两道校验；MCP 原生文本和 structuredContent 从同一字典产生，保留旧 `.fn` 文本出口与自定义 registrar 的适配。公开工具、参数、投影、错误约定及 Python 兼容入口继续由完整回归守护。旧 `iztro-verify` extra 的移除沿用清理范围；运行依赖及 Kerykeion 主版本上限保持。

## 独立 Linux 复核

固定镜像 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，Ubuntu 24.04 / Linux x86_64 / Python 3.12.3，FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.0。通过 Colima/Rosetta 的 Linux amd64 容器运行，真实平台检查生效；源码只读、禁用网络，不设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF`，不重冻基线。

- 黄金输出 **88/88 逐字节一致**，无差异、缺失或陈旧样例。
- 14 个领域工具经 REST TestClient、原生 MCP 会话及实际 CLI 子进程验证，严格投影业务 JSON 全部一致；MCP 文本与结构化数据相同，原生输出 schema 验证保持开启。
- 20 个嵌套 schema 类型事实在中央合同、OpenAPI 与 MCP 一致。
- 89 个工具的缓存 schema 与未缓存模型 schema 相同，缓存合同 SHA-256 与原未缓存公式全部相同。
- 同一 Linux 镜像下，完整 MCP 工具列表的 SHA-256 与上轮记录相同；工具数量、场景 profile 及发现体积也保持。CATALOG 89 / REST 87 / MCP 87 / CLI 88，完整 MCP 工具列表 3,918,612 UTF-8 字节，REST 完整 manifest 2,268,806 字节。
- Black / isort 检查 252 个文件通过，mypy 检查 130 个源码文件通过。

新的 Linux 完整测试正在执行，完成后登记实际 JUnit 统计。以上为本轮独立执行的结果，不借用上一轮 PR 的绿色 CI。[提交时验证回执](audits/2026-10-12/pr180-workspace-followup/submission-validation.json)保留运行状态；完成后的统计记录在 PR 验证说明与本地最终验收记录中。

## PR 与托管 CI

提交到 PR #180 的既有分支，触发 Python 3.10–3.13 及 `lowest-direct` 五项 CI，本地完整回归继续独立执行。最终结论仅以更新提交所关联的作业状态、真实测试日志与文件哈希为准；Python 3.12 必须零黄金跳过，其它作业沿用既有参考环境策略。

本轮不改变计算算法、黄金基线、CI 参考环境或最低依赖检查要求。托管 CI 与本地容器结果分别记录；远端 REST 服务及 GUI MCP 宿主不在本轮验收范围。
