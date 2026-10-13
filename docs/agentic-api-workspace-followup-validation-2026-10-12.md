# 原工作区后续改动的 Linux 与 PR #180 验证

日期：2026-10-12。**已完成：Linux 黄金 88/88 字节一致，REST / MCP / CLI 契约与兼容回归通过，最终 PR head 的五项 CI 全部成功。** [草稿 PR #180](https://github.com/Yonder-Lab/FateBridge/pull/180) 已更新，最终 head 为 `8baebd2fa5c75c31e3939f5c0d61f00ed51bd088`；[最终 CI run 38259707820](https://github.com/Yonder-Lab/FateBridge/actions/runs/38259707820) 为 completed / success。

## 范围与架构

[前轮验收](agentic-api-linux-ci-validation-2026-10-12.md)标出的 11 个执行文件属于随后完成的清理组合。相对旧 PR head `48c0eaa`，本轮整体核对并验证 **88 个执行文件**的变化，包括关联导入迁移、合同缓存、原生传输与兼容测试，未只摘取 11 个局部文件。捕获范围见[快照记录](audits/2026-10-12/pr180-workspace-followup/capture.json)。

保留 ToolSpec → services → core 架构。缓存只复用模型合同和摘要，业务输入、输出与 receipt 仍逐次计算；REST 保留两道输出校验，MCP 从同一字典生成 text 与 structuredContent。公开参数、错误、投影、Python 兼容出口和自定义 registrar 由完整回归守护。旧 `iztro-verify` extra 的移除沿用清理范围，运行依赖与 Kerykeion 主版本上限保持。

验证期间 master 两次推进，分别加入前置实现的 CI 文档，以及通过 PR #181 合入的同一份清理和 CI 证据采集步骤。本任务处理两次同步冲突，保留上游记录和已验证实现。最终分支包含 master `987370fb0bbf780dadd2730390d9e074de49feed`，相对它的运行源码、测试、脚本、包依赖和 CI 工作流没有差异；PR #180 现保留补充审查、P1/P2 修复及验收材料。见[第一次整合核验](audits/2026-10-12/pr180-workspace-followup/merge-integrity.json)与[最终同步核验](audits/2026-10-12/pr180-workspace-followup/final-master-sync.json)。

最终[369 文件执行清单](audits/2026-10-12/pr180-workspace-followup/final-execution-hashes.json)在原工作区和 PR worktree 全部一致。其中 368 个源码、测试、脚本及其它配置文件与本地完整测试完全相同；唯一变动的 CI 配置保留上游新增的依赖清单、相同全量 pytest 选择的 JUnit 输出和 artifact 上传，矩阵、参考平台、黄金条件及最低依赖策略保持。88 份[黄金文件哈希](audits/2026-10-12/pr180-workspace-followup/golden-hashes.json)始终保持，未重冻基线。

## 独立 Linux 验证

固定镜像 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，Ubuntu 24.04 / Linux x86_64 / Python 3.12.3，FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.0。使用 Colima/Rosetta 的实际 Linux amd64 容器，只读源码、禁用网络，不设置黄金跳过条件。

- 完整测试 **1971 passed、0 failed、0 skipped**，608.27 秒：[日志](audits/2026-10-12/pr180-workspace-followup/linux-full.txt)、[JUnit](audits/2026-10-12/pr180-workspace-followup/linux-full.xml)。
- 独立黄金 **88/88 逐字节一致**，无差异、缺失或陈旧样例：[黄金报告](audits/2026-10-12/pr180-workspace-followup/linux-golden.json)。
- 14 个工具通过 REST TestClient、原生 MCP 会话和实际 CLI 子进程验证，严格投影业务 JSON 一致；原生 schema 校验保持开启，MCP text 与 structuredContent 相同：[三端记录](audits/2026-10-12/pr180-workspace-followup/three-surface-projections.json)。
- 20 个嵌套 schema 类型事实在中央合同、OpenAPI 与 MCP 一致；89 个缓存合同与未缓存公式一致：[嵌套事实](audits/2026-10-12/pr180-workspace-followup/contract-checks.json)、[缓存合同核验](audits/2026-10-12/pr180-workspace-followup/linux-catalog-contracts.json)。
- 同一 Linux 环境的完整 MCP 工具列表 SHA-256 与旧快照相同，CATALOG 89 / REST 87 / MCP 87 / CLI 88 保持：[发现兼容记录](audits/2026-10-12/pr180-workspace-followup/discovery-compatibility.json)。
- Black / isort 检查 252 个文件、mypy 检查 130 个源码文件通过。全量回归包含安全错误提示、域错误、投影前输出失败、空值/扩展/原数值、旧 Python 出口、并发缓存及重建失效等分支。

## 最终托管 CI

以下为最终 head `8baebd2` 的实际结果。已核对[运行回执](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/workflow-run.json)、[作业步骤](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-jobs.json)与[统计及解析依赖](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-results.json)。此前 head `951c20d` 的[五项绿色记录](audits/2026-10-12/pr180-workspace-followup/workflow-run.json)另行保留，未套用为最终结果。

| 作业 | 实际 Python | 通过 | 跳过 | 结论及日志 |
| --- | --- | ---: | ---: | --- |
| test (3.10) | 3.10.22 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-test-3-10.txt) |
| test (3.11) | 3.11.17 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-test-3-11.txt) |
| test (3.12) | 3.12.15 | 1971 | 0 | [success](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-test-3-12.txt) |
| test (3.13) | 3.13.16 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-test-3-13.txt) |
| floor | 3.10.22 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/ci-floor.txt) |

四个常规作业的 Black、isort、mypy 均通过，五个作业的 JUnit / 依赖清单上传均成功。Python 3.12 没有跳过；其它版本与 floor 的 89 项跳过沿用既有参考环境策略，工具覆盖和进程内确定性测试仍执行。

已下载并解析最终 CI 的[Python 3.12 JUnit](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/python-3-12-junit.xml)：确认 1971 项零失败/错误/跳过，88 项黄金字节检查实际通过，领域 216 项、专业嵌套 139 项、投影 200 项、公开兼容 5 项、缓存 6 项均无跳过。见[逐模块核对](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/python-3-12-junit-checks.json)及[官方 artifact 回执](audits/2026-10-12/pr180-workspace-followup/ci-after-master-sync/artifacts.json)。

常规作业实际解析 FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.1 / lunardate 0.3.0；lowest-direct 解析 FastMCP 3.0.0 / MCP SDK 1.30.0 / Pydantic 2.11.7 / lunardate 0.2.2 / Kerykeion 5.5.0 / pyswisseph 2.10.3.1。两组均通过公开适配器及缓存回归，没有降低最低依赖检查要求。

最终[验收回执](audits/2026-10-12/pr180-workspace-followup/final-validation.json)与文件哈希再次确认原工作区和 PR 的执行内容一致，PR worktree 干净。本轮没有新的功能测试失败；冲突整合与范围文档修正保持架构和计算输出。最终 CI 日志、JUnit 及此报告保存在原工作区，PR 验证说明同步更新，未追加提交改变已通过 CI 的 head。

临时 Colima profile 已恢复停止，Docker context 保持 default。本任务未合并 PR #180 或部署服务；相关清理实现已由 PR #181 合入 master。远端 REST 服务及 GUI MCP 宿主不在本轮验收范围。
