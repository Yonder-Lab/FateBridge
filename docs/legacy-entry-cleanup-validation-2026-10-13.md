# 旧入口与兼容层清理验收（2026-10-13）

本轮按用户要求删除历史入口和转发包装，调用方直接依赖职责模块。旧接口退出支持属于本轮明确变更；保留能力的请求字段、默认值、计算规则和业务输出保持原样。

## 清理范围与迁移方式

| 已删除的入口 | 当前入口 |
| --- | --- |
| `core/tool_spec.py` | `application.tool_spec`、`bindings`、`execution`、`projection`、`description`；协议注册使用 `transports.rest/mcp` |
| `core/discovery.py`、`core/scenarios.py` | `application.discovery`、`application.scenarios` |
| `core/request_models.py` | `core.requests` 中各领域的定义模块 |
| `core/astrology.py` | `core.astro.birth/chart/relationship/ephemeris` 等职责模块；共用表使用 `core.astrology_tables` |
| `utils/helpers.py` | `utils.birth_input/solar_time/formatting/analysis_clock/elements` |
| `core.predictive`、`core.local_techniques` 的包级重导出 | 按推运技法、地方术数导入具体子模块；包初始化仅保留说明 |
| `services.calculation` 的出生构造器/响应私有别名 | `services.birth_context.build_birth_computation_context`、`birth_payload.build_destiny_payload` |
| `services.timing` 的日历查询和私有 helper 重导出 | `services.calendar_tools/calendar_input/timing_state/timing_snapshots` |
| `services.tool_catalog` 的绑定/服务代理重导出 | `services.catalog` 中相应领域模块；中央目录仅负责装配和合同补全 |
| `api` 的请求模型、服务和历史 handler 别名 | 请求模型直接导入定义模块；HTTP 调用正式路由 |
| `mcp_server.<tool>.fn` 文本包装及文本反解析适配器 | 原生 FastMCP Client；`create_mcp_app` 仅注册原生结果工具 |
| `POST /api/calculate`、CLI `calculate_legacy` | 独立命盘使用 `/api/cn/bazi/birth` / `bazi_birth`，字段位于 `bazi_birth` 对象；综合分析使用 MCP / CLI `analyze_destiny` |

删除旧 REST 的扁平响应函数、`ToolSpec.result_transform` 及其执行分支、旧输出模型登记与重现策略登记。删除已退出的 Golden 样例，其余 Golden 没有重新生成。正式 MCP 同时返回 JSON text、`structuredContent` 与原生 `isError`，这属于保留的协议合同。

中央目录从 89 条减少到 **88 条**；REST 从 87 项减少到 **86 项**；MCP 保持 **87 项**；CLI 从 88 条减少到 **87 条**。正式 `bazi_birth` 和 `analyze_destiny` 的职责保持独立。

请求字段别名、领域输出字段、算法模式、导出标题解析和声明支持的 SDK 版本处理继续遵循现有合同。本轮没有修改关系评分、星盘/时运算法或输入的历法语义。

## 调用关系与文档

生产代码、测试和审计脚本都从定义模块导入。中央目录从 412 行缩为 60 行，不再装配历史全局导出。架构测试删除兼容模块豁免，并检查旧模块不得重新出现或被内部导入；静态导入图覆盖相对、绝对和函数内导入。

`test_retired_entries.py` 检查旧 Python 路径、HTTP 路由、目录命令和包装属性退出支持，验证正式路由仍校验输入，以及原生 MCP 成功/错误的 text 与结构化结果一致。独立进程验证在正在运行的 asyncio loop 内导入/使用 MCP 无未等待协程警告。

README、架构/开发/入门/API/Agent 指南、贡献规范、场景清单及共享工具地图同步到当前入口和计数。场景清单删项后重新生成 `agent_scenarios.json`，差异仅为 `sources_sha256`。前几轮审查报告保留历史证据，增加后续迁移说明；旧输出捕获和探针脚本迁到定义模块。

## 回归证据

| 检查 | 结果 |
| --- | --- |
| 旧入口、原生协议、架构、执行与运行错误的定向测试 | 117 passed |
| 文档、场景清单和 Skill 接口检查 | 27 passed |
| 场景生成、三端重放与目录检查 | 34 passed |
| 固定源码副本的全量测试 | **1,943 passed、88 skipped、0 failed**（115.21 秒） |
| mypy | 192 个源码文件无错误 |
| Black / isort | 通过 |
| 同环境业务、请求契约及工具边界样例比较 | 355 项一致 |
| Wheel 构建及内容核对 | 构建成功，203 个源码/数据文件与验证副本一致；6 个已删模块均未打包，正式 console scripts 保留 |

[比较回执](audits/2026-10-13/legacy-entry-cleanup/comparison.json)记录清理前 360 项、清理后 359 项：删除 `tool/calculate_legacy`；4 个聚合哈希变化分别为目录顺序、完整发现、OpenAPI 和场景发现，其余 **355 项完全一致**。保留的 88 条目录记录业务输出全部一致；请求模型 Schema、字段顺序、太阳时、输入/格式/五行边界，以及星盘变体、关系盘、降级路径和时运边界样例均包含在比较中。每次比较冻结同一分析时钟；排除每次调用独立生成的 `run_metadata`，业务字段和快照未归一化或改写。

初次全量测试发现场景清单遗留登记，复验发现生成清单的来源指纹需同步，两项均已修正，分别保留于[首轮回执](audits/2026-10-13/legacy-entry-cleanup/initial-full-result.json)和[来源指纹回执](audits/2026-10-13/legacy-entry-cleanup/manifest-failure-result.json)。

共享工作区中的另一个任务更新了 Codex 主机体验脚本及其测试，最终验证副本纳入该更新，见[并行改动记录](audits/2026-10-13/legacy-entry-cleanup/concurrent-source-delta.json)。副本显式复制 Git 忽略的本地 `ephe/` 星历文件，以同一虚拟环境和 `PYTHONPATH=.:src` 运行；使用源码/测试/规则数据的[固定指纹](audits/2026-10-13/legacy-entry-cleanup/verified-source-manifest.json)和副本输出再次核对。该轮的原生协议测试使用本地 FastMCP Client。

验证环境为本地 macOS / Python 3.13；Linux 平台专属 Golden 跳过不构成本轮 Linux CI 证据。工作仅在本地完成，尚未提交或推送。

## 复验命令

```bash
PYTHONPATH=.:src .venv/bin/pytest -q
PYTHONPATH=.:src .venv/bin/mypy src
.venv/bin/python -m black --check src tests scripts
.venv/bin/python -m isort --check-only src tests scripts
PYTHONPATH=.:src .venv/bin/python scripts/build_scenario_manifest.py
PYTHONPATH=.:src .venv/bin/python \
  docs/audits/2026-10-13/legacy-entry-cleanup/capture_outputs.py /tmp/fatebridge-current.json
```

完整日志、JUnit、前后指纹、被删源码存档与发行包核对结果见 [审计目录](audits/2026-10-13/legacy-entry-cleanup/validation.json)。
