# 原工作区后续改动的 Linux 与 PR #180 验证

日期：2026-10-12。承接[上一轮 Linux / CI 验收](agentic-api-linux-ci-validation-2026-10-12.md)，将此前未纳入 PR 的后续修改更新到[草稿 PR #180](https://github.com/Yonder-Lab/FateBridge/pull/180)。不合并、不部署，保留原 master 工作区的未提交内容。

## 受测范围

上一轮发现的 11 个文件属于随后完成的清理。相对 PR 旧 head `48c0eaa5c7726fcab2f9a6ee288a231f7dadd62b`，当前完整清理组合共有 **88 个执行文件**变化，包括关联导入迁移、合同缓存和兼容测试。本轮复制原工作区的实际文件到已附加的 PR worktree，包含这些依赖，未只摘取 11 个局部文件。

捕获快照时原工作区 Git head 为 `5fafc61f7bbbf24329103f46ccd87f02dc80daf2`，随后 master 推进到仅补充 CI 文档的 `49ce0228358b09d46458153f8b2ef14472bb0a4a`；清理内容仍是未提交状态，不能用 Git head 单独代表受测源码。369 个执行文件哈希与[清理验收快照](audits/2026-10-12/cleanup/execution-hashes.json)逐项一致，88 份黄金文件分别保存哈希。完整捕获见[范围记录](audits/2026-10-12/pr180-workspace-followup/capture.json)，执行哈希和黄金哈希分别保存在[执行清单](audits/2026-10-12/pr180-workspace-followup/execution-hashes.json)与[基线清单](audits/2026-10-12/pr180-workspace-followup/golden-hashes.json)。

保留 ToolSpec → services → core 架构。缓存只复用模型合同及合同摘要；输入、业务结果和执行 receipt 仍逐次计算。REST 保留业务结果与 receipt 附加后的两道校验；MCP 原生文本和 structuredContent 从同一字典产生，保留旧 `.fn` 文本出口与自定义 registrar 的适配。公开工具、参数、投影、错误约定及 Python 兼容入口继续由完整回归守护。旧 `iztro-verify` extra 的移除沿用清理范围；运行依赖及 Kerykeion 主版本上限保持。

## 独立 Linux 复核

固定镜像 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，Ubuntu 24.04 / Linux x86_64 / Python 3.12.3，FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.0。通过 Colima/Rosetta 的 Linux amd64 容器运行，真实平台检查生效；源码只读、禁用网络，不设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF`，不重冻基线。

- 黄金输出 **88/88 逐字节一致**，无差异、缺失或陈旧样例。
- 14 个领域工具经 REST TestClient、原生 MCP 会话及实际 CLI 子进程验证，严格投影业务 JSON 全部一致；MCP 文本与结构化数据相同，原生输出 schema 验证保持开启。
- 20 个嵌套 schema 类型事实在中央合同、OpenAPI 与 MCP 一致。
- 89 个工具的缓存 schema 与未缓存模型 schema 相同，缓存合同 SHA-256 与原未缓存公式全部相同。
- 同一 Linux 镜像下，完整 MCP 工具列表的 SHA-256 与上轮记录相同；工具数量、场景 profile 及发现体积也保持。CATALOG 89 / REST 87 / MCP 87 / CLI 88，完整 MCP 工具列表 3,918,612 UTF-8 字节，REST 完整 manifest 2,268,806 字节。
- Black / isort 检查 252 个文件通过，mypy 检查 130 个源码文件通过。

新的 Linux 完整测试已完成：**1971 passed、0 failed、0 skipped**，608.27 秒，见[完整日志](audits/2026-10-12/pr180-workspace-followup/linux-full.txt)、[JUnit](audits/2026-10-12/pr180-workspace-followup/linux-full.xml)及[本地验收回执](audits/2026-10-12/pr180-workspace-followup/local-validation.json)。本轮重新执行上述验证，没有借用旧 PR 的绿色结果；[提交时回执](audits/2026-10-12/pr180-workspace-followup/submission-validation.json)作为中间运行状态保留。

## PR 与托管 CI

远端 master 推进到 `49ce0228358b09d46458153f8b2ef14472bb0a4a`，包含前置契约、风水实现及 CI 文档；PR 的重复提交链产生冲突。本轮将该 master 合入 PR 分支，保留已通过全量测试的清理实现、master CI 记录和玄空范围文档修正。整合后 369 个执行文件及 88 份黄金哈希全部不变，见[整合核验](audits/2026-10-12/pr180-workspace-followup/merge-integrity.json)。没有新增计算源码修复或黄金基线修改。

最终 PR head：`951c20d26dca194d34dc5dbe987992426e19e24b`。[CI run 38257181034](https://github.com/Yonder-Lab/FateBridge/actions/runs/38257181034) 为 **completed / success，五个作业全部通过**。已核对运行的 head SHA、每个作业的真实测试日志和检查步骤，见[运行回执](audits/2026-10-12/pr180-workspace-followup/workflow-run.json)、[作业步骤](audits/2026-10-12/pr180-workspace-followup/ci-jobs.json)及[实际测试/依赖统计](audits/2026-10-12/pr180-workspace-followup/ci-results.json)。

| 作业 | 实际 Python | 通过 | 跳过 | 结论及原始日志 |
| --- | --- | ---: | ---: | --- |
| test (3.10) | 3.10.22 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-test-3-10.txt) |
| test (3.11) | 3.11.17 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-test-3-11.txt) |
| test (3.12) | 3.12.15 | 1971 | 0 | [success](audits/2026-10-12/pr180-workspace-followup/ci-test-3-12.txt) |
| test (3.13) | 3.13.16 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-test-3-13.txt) |
| floor | 3.10.22 | 1882 | 89 | [success](audits/2026-10-12/pr180-workspace-followup/ci-floor.txt) |

Python 3.12 执行全部 88 项黄金字节比较和 1 项依赖黄金基线的时钟验证，没有跳过。其余常规版本的 89 项跳过遵循原参考环境策略，floor 沿用原 `FATEBRIDGE_SKIP_GOLDEN_DIFF=1` 设置；工具覆盖及进程内确定性测试继续执行。四个常规作业的 Black、isort、mypy 全部通过；floor 按原工作流运行依赖下限安装和全量测试。

常规作业实际使用 FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.1 / lunardate 0.3.0。`lowest-direct` 实际解析 FastMCP 3.0.0 / MCP SDK 1.30.0 / Pydantic 2.11.7 / lunardate 0.2.2 / Kerykeion 5.5.0 / pyswisseph 2.10.3.1。这两组均通过新增的公开适配器及缓存回归，未降低依赖下限检查要求。

最终再次核对原工作区和 PR worktree 的 369 个执行文件及 88 份黄金文件，哈希全部保持，没有未纳入本轮验证的执行文件差异。原工作区的清理仍保留为未提交内容；PR worktree 干净。最终 CI 下载日志和[验收回执](audits/2026-10-12/pr180-workspace-followup/validation.json)保存于原工作区，PR 验证说明已更新，不再追加提交改变已通过 CI 的 head。

本轮临时启动的 Colima profile 已恢复停止，Docker context 为 `default`。托管 CI 与本地容器结果分别记录；PR 保持草稿，未合并到 master 或部署。远端 REST 服务及 GUI MCP 宿主不在本轮验收范围。

## 最终 master 同步

第一次更新的 `951c20d` 已通过上述五项 CI。最终核对时，远端 master 又推进到 `987370f`，同一清理实现已由 PR #181 合入。同步该 master 时只处理文档和回执冲突，执行代码、测试、脚本及 88 份黄金输出保持；仅 CI 配置增加依赖清单记录、相同 pytest 选择的 JUnit 输出和 artifact 上传，不改变矩阵、参考环境或最低依赖策略。见[最终同步回执](audits/2026-10-12/pr180-workspace-followup/final-master-sync.json)和[最终执行清单](audits/2026-10-12/pr180-workspace-followup/final-execution-hashes.json)。PR #180 因而保留补充审查与验收材料，最终同步提交的五项 CI 将另行登记。
