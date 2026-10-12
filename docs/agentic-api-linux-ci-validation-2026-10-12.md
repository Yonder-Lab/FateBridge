# FateBridge 本轮契约改动的 Linux 黄金与 CI 验证

日期：2026-10-12。承接 [八字专题、宿曜及知识/导出验收](agentic-api-p2-domain-contracts-fixes-2026-10-12.md)。当前工作区原先尚未入 Git，本轮将其形成独立可审查快照，创建 [草稿 PR #180](https://github.com/Yonder-Lab/FateBridge/pull/180)，触发 [GitHub Actions CI](https://github.com/Yonder-Lab/FateBridge/actions/runs/38230062567)。原 master 工作区的未提交内容保留，未合并或部署。

## 受测版本与证据链

- PR head：`48c0eaa5c7726fcab2f9a6ee288a231f7dadd62b`；base：`204635e2073a1ef33a0e2ef86bb98fced27e7618`。
- 独立 worktree：`/Users/thomas/.codex/worktrees/agentic-p2-linux-ci/FateBridge`。包含此前 P1/P2 修复及共享目录所需的既有住宅风水工具，避免只上传局部文件造成虚假的验证通过或缺失模块。
- 创建快照时逐项核对已有 Linux 完整测试受测源码、测试、技能、脚本与 CI 配置，共 **383 文件**，当时原工作区与 PR 快照全部相符。已保存的完整 Linux 运行 **1960 passed、0 failed、0 skipped** 可适用于该 PR 执行源码；其 [JUnit](audits/2026-10-12/output-projection-linux/linux-release-full.xml) 与 [受测哈希](audits/2026-10-12/output-projection-linux/source-hashes.json) 均已重新核对。CI 完成时原工作区有后续改动，范围见下文；独立 PR 快照保持不变。
- 新增 `.gitattributes` 仅将 `docs/audits/**` 标记为 generated，以便审查实现而保留原始证据字节；不改变计算、schema、传输或 CI 执行逻辑。

## 独立 Linux 复核

复用固定镜像 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，Ubuntu 24.04.5 LTS / glibc 2.39 / Python 3.12.3，在本机 Colima/Rosetta 的 `linux/amd64` 容器内运行。项目快照只读挂载，禁止联网，设置实际项目 `PYTHONPATH`，没有伪造平台或绕过参考环境条件。

- **88/88 黄金输出逐字节匹配**，无缺失、陈旧或差异样例，`golden_diff_active=true`，未设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF`。见 [黄金报告](audits/2026-10-12/agentic-api-linux-ci/linux-golden.json)。
- **20 个深层 schema 事实**在中央合同、OpenAPI 与原生 MCP 一致。见 [类型核验](audits/2026-10-12/agentic-api-linux-ci/contract-checks.json)。
- **14 个本轮工具**用 REST TestClient、真实原生 MCP 会话和独立 CLI 进程核对严格投影业务 JSON，全部一致，MCP 兼容文本与结构化内容相同。见 [三端结果](audits/2026-10-12/agentic-api-linux-ci/three-surface-projections.json) 和 [可复跑探针](audits/2026-10-12/agentic-api-linux-ci/linux-domain-probe.py)。原生会话保留 schema 校验，没有关闭客户端输出验证。
- **88 份黄金基线哈希保持**；源码只读快照未被执行修改。完整测试另覆盖本轮 216 项领域合同、200 项全目录投影、非默认分支、扩展/空值/原数值、投影前内部失败与原领域失败语义。

依赖版本：FastMCP 4.1.0、MCP SDK 2.3.0、Pydantic 2.14.0、Kerykeion 5.12.10、pyswisseph 2.10.3.2、lunardate 0.3.0。镜像内已有依赖，未在本轮重新解析；托管 CI 独立安装依赖。新的 [发现体积与环境记录](audits/2026-10-12/agentic-api-linux-ci/metrics.json) 保留 SDK 版本变化造成的字节差别，未冒充旧环境的逐字节 schema 发布记录。

## 远端 CI 与失败定位

旧 master 的 [CI 37890386638](https://github.com/Yonder-Lab/FateBridge/actions/runs/37890386638) 四个常规 Python 作业失败，floor 成功。实际日志的失败点是 `tests/test_third_party_correctness_fixes.py` 引用 lunardate 的 `yearInfos`，而 0.3 使用 `YEAR_INFOS`；当前受测快照已兼容两种名称，保留依赖表不被修改的测试目标。见 [失败摘录](audits/2026-10-12/agentic-api-linux-ci/previous-ci-failure.txt)。

另一份已核对的 Linux 验证修复了 MCP SDK 1.x/2.x 构造属性名称差别：通过 `CallToolResult.model_validate` 保留同一公开协议字典。新增成功/错误结果序列化测试；本轮 snapshot 包含此修复。没有更换业务架构、降低依赖下限测试要求、关闭黄金检查或重冻基线。

本轮远端 CI 对准确 PR head 独立执行 Python 3.10 / 3.11 / 3.12 / 3.13 的完整测试、Black、isort、mypy，以及 Python 3.10 的 `--resolution lowest-direct` 全量测试。floor 的黄金跳过设置沿用原 CI 工作流；参考黄金由 Python 3.12 作业执行。

远端 CI 已完成，结论为 **success，五个作业全部通过**；GitHub 返回的受测 head 仍为 `48c0eaa5c7726fcab2f9a6ee288a231f7dadd62b`。见 [运行回执](audits/2026-10-12/agentic-api-linux-ci/workflow-run.json)、[作业步骤](audits/2026-10-12/agentic-api-linux-ci/ci-jobs.json) 和 [结果及依赖版本](audits/2026-10-12/agentic-api-linux-ci/ci-results.json)。

| 作业 | 实际 Python | 通过 | 跳过 | 结论及原始日志 |
| --- | --- | ---: | ---: | --- |
| test (3.10) | 3.10.22 | 1871 | 89 | [success](audits/2026-10-12/agentic-api-linux-ci/ci-test-3-10.txt) |
| test (3.11) | 3.11.17 | 1871 | 89 | [success](audits/2026-10-12/agentic-api-linux-ci/ci-test-3-11.txt) |
| test (3.12) | 3.12.15 | 1960 | 0 | [success](audits/2026-10-12/agentic-api-linux-ci/ci-test-3-12.txt) |
| test (3.13) | 3.13.16 | 1871 | 89 | [success](audits/2026-10-12/agentic-api-linux-ci/ci-test-3-13.txt) |
| floor | 3.10.22 | 1871 | 89 | [success](audits/2026-10-12/agentic-api-linux-ci/ci-floor.txt) |

89 项跳过均遵循既有参考环境策略：88 项黄金字节比对与 1 项依赖黄金基线的时钟测试，仅在 Linux x86_64 / Python 3.12 的参考依赖口径执行。Python 3.12 作业全部执行，无跳过；其它作业仍执行工具覆盖和进程内确定性测试。四个常规作业的 Black、isort、mypy 全部通过；floor 按原工作流只运行完整测试。

常规作业实际解析 FastMCP 4.1.0 / MCP SDK 2.3.0 / Pydantic 2.14.1 / lunardate 0.3.0；floor 通过 `lowest-direct` 解析 FastMCP 3.0.0 / MCP SDK 1.30.0 / Pydantic 2.11.7 / lunardate 0.2.2 / Kerykeion 5.5.0 / pyswisseph 2.10.3.1。这两组结果验证 SDK 1.x/2.x 协议输出与 lunardate 新旧接口兼容。既有失败修复已通过远端验证，本轮复核没有新增失败或业务源码修改，没有改写黄金基线。

最终再次核对 PR worktree 的 383 个执行文件以及 88 份黄金文件，哈希全部保持，worktree 干净，确保验收记录指向通过 CI 的同一版本。本地容器核验与远端 CI 独立记账；新增验收报告与下载日志保存在原工作区，未追加提交改变已验证的 PR head。

最终核对时，原工作区有 **11 个执行文件**发生后续变化，包含 schema 缓存、重复校验清理及依赖 extra 清理等修改；88 份黄金文件仍保持。本轮保留这些修改，没有将它们追加到已通过 CI 的 PR，也没有用本次结果宣称这些后续修改已受测。见 [差异哈希清单](audits/2026-10-12/agentic-api-linux-ci/workspace-drift.json) 和 [相对受测快照的 diff](audits/2026-10-12/agentic-api-linux-ci/workspace-drift.diff)。本报告的通过结论限定为上述 PR head。

[完整本轮证据汇总](audits/2026-10-12/agentic-api-linux-ci/validation.json)。本任务本地核验结束时已停止 Colima 临时 profile，Docker context 为 `default`；最终只读检查时 profile 已重新运行，context 已变为 `colima-fatebridge-ci-linux`。保留后续环境变化，没有再次停机或切换 context。快照、日志与草稿 PR 保留供复查。没有生产部署或远端 REST 服务/MCP GUI 宿主验收。

## 后续验收

上述 11 个文件未受测的状态属于本轮之前的 PR 快照。后续完整清理组合的独立验证与 PR 更新见[后续验收记录](agentic-api-workspace-followup-validation-2026-10-12.md)；两轮结果分别保存，历史回执未改写。
