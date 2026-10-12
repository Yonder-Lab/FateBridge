# 输出契约的 Linux 参考环境验证

本轮最终完整测试：**1,960 passed、0 failed、0 skipped**。原先在 macOS 跳过的 89 项全部补齐：88 项 golden 字节比对，以及 1 项模拟时钟变化验证。JUnit 中逐项核实执行状态，没有关闭或绕过参考环境检查。

## 环境与受测内容

- Ubuntu 24.04.5 LTS，Linux x86_64 用户态，Python 3.12.3，glibc 2.39。
- 固定镜像 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，在本机 Colima/Rosetta 的 `linux/amd64` 容器中运行；没有伪造 `platform` 或 Python 版本。该验证是本地参考容器运行，不是托管 CI 或部署验收。
- FastMCP 4.1.0、MCP SDK 2.3.0、Pydantic 2.14.0、Kerykeion 5.12.10、pyswisseph 2.10.3.2、lunardate 0.3.0。完整环境见 [environment.json](audits/2026-10-12/output-projection-linux/environment.json)。
- 包含当前已暂存、未暂存、未跟踪文件的独立只读快照。最终运行涵盖并行工作中新增的八字、宿曜、知识和导出契约。结束时核对源代码、测试、脚本、技能与 CI 配置的哈希，全部与当前工作区一致；快照也未被运行修改。
- `golden_diff_active=true`，未设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF`。源包实际从 `/workspace/src/fatebridge` 导入，CLI 子进程使用容器的项目 Python。

## 本轮修复

Linux 类型检查发现 MCP SDK 2.x 的构造函数使用 `structured_content` / `is_error` 属性名，旧 SDK 1.x 的构造函数使用 `structuredContent` / `isError`。原构造方式虽然能按别名运行，但新版 SDK 的类型检查拒绝旧关键字。

`src/fatebridge/mcp_transport.py` 现在通过 `CallToolResult.model_validate` 读取协议字典，统一新旧 SDK，并保留相同的公开 `structuredContent`、`isError` 和文本内容。新增 `tests/test_mcp_protocol_result.py` 覆盖成功与错误结果的原生序列化；SDK 1.28.0 / FastMCP 3.4.2 的本地相关回归 56 项通过，SDK 2.3.0 在本轮 Linux 完整测试与类型检查中通过。

只读源快照下，mypy 2.4 的默认缓存目录不能写入，因此明确将缓存设为可写 `/audit/mypy-release-cache`；没有通过屏蔽类型检查解决问题。

## 三端、规则与数值

- 完整测试包含全目录投影检查和原生 MCP 客户端的输出 schema 校验，保留严格/宽松投影、错误包络、数组整块选择和 CLI `--no-metadata` 的边界。
- 额外用 REST TestClient、真实原生 MCP 会话和独立 CLI 进程检查完整四层合参、规则版本投影和朝向分界的部分结果。三端业务 JSON、合同摘要、输入摘要及完整业务输出摘要均一致；MCP 文本与 `structuredContent` 一致。见 [三端记录](audits/2026-10-12/output-projection-linux/surface-contracts.json) 与 [可复跑探针](audits/2026-10-12/output-projection-linux/surface-probe.py)。
- 基础规则版本为 `1.0.0`，玄空中州派为 `1.0.1`。年度飞星与玄空宅盘继续分层，例中分别为九运和八运；规则来源 ID、URL 与适用范围均保留。
- 88 份 golden **逐字节完全匹配**，没有缺失或陈旧快照。88 份基线与两份风水规则登记 JSON 的运行前后哈希完全相同，没有重新冻结基线。见 [golden 报告](audits/2026-10-12/output-projection-linux/linux-release-golden.json)。
- 独立事实复核继续通过：命卦 400 个案例、八宅 64 个方向配对；玄空 7 个公开盘例、48 项独立转录的五黄阴阳/飞序事实。固定第三方的 216 个下卦盘中 192 个一致，24 个山五黄差异仍逐项验证为已登记的相反飞序，按所选规则保留。48 项事实不是 48 个公开盘图；第三方差异没有被隐藏或用于批量修改基线。见 [独立比较](audits/2026-10-12/output-projection-linux/xuankong-release-independent.json)。

Linux 的 black、isort 全部通过（248 个 Python 文件），mypy 通过 129 个源文件；工作区 `git diff --check` 通过。

## 证据与复跑

[完整汇总](audits/2026-10-12/output-projection-linux/validation.json)、[完整测试日志](audits/2026-10-12/output-projection-linux/linux-release-full.log)、[JUnit](audits/2026-10-12/output-projection-linux/linux-release-full.xml)、[源文件哈希](audits/2026-10-12/output-projection-linux/source-hashes.json)。镜像、只读源快照位置、依赖和运行命令均登记在汇总及 [检查命令记录](audits/2026-10-12/output-projection-linux/checks-release.json)。

在相同容器中，源快照挂到只读 `/workspace`，证据目录挂到可写 `/audit`，使用 `PYTHONPATH=/workspace/src:/workspace`、`PYTHONDONTWRITEBYTECODE=1`，执行：

```bash
pytest -q -ra -p no:cacheprovider --junitxml=/audit/linux-release-full.xml
python -m scripts.audit_linux_golden --report /audit/linux-release-golden.json
python /audit/surface-probe.py
python -m scripts.audit_xuankong_independent --report /audit/xuankong-release-independent.json
black --check src/fatebridge scripts tests
isort --check-only src/fatebridge scripts tests
mypy --cache-dir /audit/mypy-release-cache src/fatebridge/
```

运行结束后恢复原 Docker context，并将本轮临时启动的 Colima profile 恢复为停止状态；源快照和日志保留供复核。

## master 提交前的独立复跑

随后按授权将必要前置实现拆为公共契约／MCP 基础和住宅风水两个提交，再将 Ruleset 投影修复与 MCP SDK 兼容修复单独提交。提交前从原 `master` 基点构建仅含这些选定内容的快照；环境模板、新增 `.gitattributes`、另一轮 PR／CI 的文档和审查记录没有进入受测快照或提交。测试期间出现的其他并行清理／缓存优化也未加入，原样留在工作区。

该快照在上述 Linux x86_64 / Python 3.12.3 固定镜像中重新执行完整测试：**1,960 passed、0 failed、0 skipped，570.22 秒**。JUnit 逐项确认 88 项 golden 比较及 1 项时钟验证全部通过；另一次 standalone golden 审计也为 88/88 字节一致。Black、isort、mypy、场景生成物检查、两个前置阶段的 REST／原生 MCP 启动验证及三端实际调用探针全部通过。383 个执行文件和 90 个受保护的基线／规则文件在快照测试前后哈希一致。

本次 [提交前完整汇总](audits/2026-10-12/output-projection-linux/precommit/validation.json)、[完整日志](audits/2026-10-12/output-projection-linux/precommit/precommit-full.log)、[JUnit](audits/2026-10-12/output-projection-linux/precommit/precommit-full.xml) 和 [执行文件哈希](audits/2026-10-12/output-projection-linux/precommit/execution-hashes.json) 单独保留。汇总中的 tested_candidate_tree 标识受测内容树；测试结束后仅加入这份文档补记和验证证据，执行源码未变。该记录仍为本地参考容器验证，不宣称远端 CI 或部署结果。

## master 推送后的 GitHub Actions CI

2026-10-12 核对远端 push 触发的 [CI run 38233642808](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808)，受测提交为 [`5fafc61f7bbbf24329103f46ccd87f02dc80daf2`](https://github.com/Yonder-Lab/FateBridge/commit/5fafc61f7bbbf24329103f46ccd87f02dc80daf2)。该提交包含公共契约／MCP 前置实现 `1cbebe8`、住宅风水前置实现 `4e92ea3` 和独立的 Ruleset／MCP 修复 `5fafc61`。已核对五个作业的 checkout SHA、步骤结论和实际测试日志；运行及全部作业均为 `completed / success`。

各作业运行于 Ubuntu 24.04；四个常规版本独立安装当前可解析依赖，floor 使用 Python 3.10 和 `uv pip install --system --resolution lowest-direct -e ".[dev]"` 检查直接依赖的兼容下限。

| 作业与日志 | 通过 | 失败 | 跳过 | 测试耗时 | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| [Python 3.10](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808/job/114758861268) | 1,871 | 0 | 89 | 879.93 秒 | success |
| [Python 3.11](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808/job/114758861177) | 1,871 | 0 | 89 | 594.41 秒 | success |
| [Python 3.12](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808/job/114758861265) | 1,960 | 0 | 0 | 529.51 秒 | success |
| [Python 3.13](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808/job/114758861071) | 1,871 | 0 | 89 | 473.17 秒 | success |
| [floor / Python 3.10](https://github.com/Yonder-Lab/FateBridge/actions/runs/38233642808/job/114758860650) | 1,871 | 0 | 89 | 1,031.72 秒 | success |

Python 3.12 实际执行了全部 88 项 golden 字节比较及 1 项模拟时钟验证，没有跳过。其他常规版本的 89 项跳过来自既有参考平台条件；floor 依照现有工作流设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF=1`，由 Python 3.12 作业承担参考环境的数值基线验证。

四个常规 Python 作业的 Black、isort、mypy 步骤全部通过：Black 检查 248 个 Python 文件，mypy 检查 129 个源文件。floor 的依赖下限安装和完整测试步骤均通过，其工作流没有另设这三项静态检查。此次远端验证无失败，无需额外代码修复；工作区其他改动未纳入上述受测提交。
