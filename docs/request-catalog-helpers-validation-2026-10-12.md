# 请求模型、工具目录与 helpers 整理验收（2026-10-12）

## 范围与结论

本轮完成[结构审查报告](code-structure-review-2026-10-12.md)剩余的三个低优先级热点：请求模型、工具目录和 helpers。按独立职责迁移定义，生产代码与一般测试直接导入定义模块，历史 Python 路径保留同对象导出。现有接口、字段默认值、别名、计算规则、工具顺序和延迟加载方式保持原实现，没有更新黄金快照。

结构迁移完成后的同环境比较 **360 项业务输出、接口合同和公共工具样例，逐项一致**。**177 项迁移定义的 AST 完全相同**；82 条逐项工具声明、7 条风水声明所在的循环、两次目录合同补全过程也保持原 AST（风水循环仅将容器名 `CATALOG` 归一化回原名）。这验证结构迁移与样例行为一致，不替代原算法的独立正确性核验。

工作区包含上一轮结构整理及其他任务的 Agent、CLI、占卜/配合度变更；本轮保留它们。审计记录描述当前本地工作区，其他功能的验收应使用其各自记录。

## 职责划分

| 原热点 | 新归属 | 保留入口 |
| --- | --- | --- |
| `core/request_models.py`（1,769 行） | `core/requests/` 的公共基类和领域合同 | 原文件 167 行，仅重导出 |
| `services/tool_catalog.py`（1,294 行） | `services/catalog/` 的领域声明、绑定和延迟服务代理 | 原文件 412 行，负责有序装配、合同补全和历史导出 |
| `utils/helpers.py`（643 行） | 出生输入、太阳钟、响应格式、分析时钟、五行关系 | 原文件保留兼容导出与原日志名称 |

### 请求模型

`core/requests/base.py` 保留 `_DeferredModel` 的真实公历日期校验、`extra="forbid"` 和 `defer_build=True`。`birth.py` 保留中式 `FateBridgeRequest` 与西式 `AstroBirthRequest`；各自的默认值与太阳时语义未合并或改写。

领域模型位于 `bazi.py`、`compatibility.py`、`timing.py`、`calendar.py`、`divination.py`、`metaphysics.py`、`reference.py`、`astrology.py`、`western_timing.py`、`western_lifespan.py`、`western_events.py`。每个定义只存在一份；继承和嵌套类型直接从所属模块导入。73 个类体逐项 AST 一致，所有类的 JSON Schema 与字段顺序均与整理前一致。风水模型沿用已有 `core/fengshui/models.py` 边界。

### 工具目录

`services/catalog/` 的 `bazi`、`compatibility`、`timing`、`divination`、`metaphysics`、`reference`、`astrology`、`western_timing`、`western_lifespan`、`western_events`、`fengshui` 拥有各领域的 `SPECS`；星盘特殊请求绑定与其共享延迟服务代理位于 `astro_bindings.py`。目录文件只导入领域声明，按历史顺序拼接，然后统一补全 output model 与 reproducibility policy。

89 项工具仍只声明一次，中央 `CATALOG` 仍为三端唯一装配结果。旧的 `rest_specs()`、`mcp_specs()`、私有绑定/声明工厂和具名服务代理保留；历史代理与领域代理是同一个对象。原有宿曜工具虽属于 compatibility family，仍放在拥有其实现的 divination 声明模块，保留其原目录位置。

服务继续使用 `lazy_service`，避免目录导入时加载真实计算模块。冷启动测试确认不加载 kerykeion、八字、星盘或西占时运服务，也不加载旧请求/helpers 聚合入口。

### 公共工具

| 模块 | 职责 | 行数 |
| --- | --- | ---: |
| `utils/birth_input.py` | `PersonInfo`、性别规范化、输入构造与民用出生时刻 | 176 |
| `utils/solar_time.py` | 两种太阳钟策略、时间方程、DST、地点/时区来源与归一化结果 | 258 |
| `utils/formatting.py` | 日期展示、四柱表示、JSON/错误格式、快照文本筛选 | 95 |
| `utils/analysis_clock.py` | 复用执行时钟补全分析年/月 | 29 |
| `utils/elements.py` | 五行关系说明 | 77 |

已有 errors、places、house_systems 和 timezones 继续保持独立。19 项迁移定义 AST 一致，helpers 的历史函数、类和常量保留重导出；原 helpers 日志名称也保留。黄金测试的出生时间冻结点迁到 `birth_input.datetime`，不改变冻结时刻或基线。

## 验证与证据

比较矩阵固定 `as_of=2026-10-12T12:00:00+08:00`，覆盖：

- 全目录 89 项工具业务输出，完整发现、场景和 OpenAPI 合同，以及目录顺序。
- 全部 73 个请求类的 Schema 与字段顺序，包括公共基类和嵌套模型。
- 上轮星盘/时运矩阵：盘型、宫制、黄道、关系模式、太阳时、近似路径和共享时运状态。
- 性别输入、已知/未知地点、省级近似、缺经度的显式报错/缺省降级、经度推断时区、两种太阳钟策略与历史 DST。
- 固定分析时钟的缺省值、紧凑/展开 JSON、快照文本筛选、五行组合、非法日期与未知字段校验。

业务哈希移除 `run_metadata`，因为每次执行的 ID、耗时、时间及重构后的源码指纹会变化。元数据、错误、投影、重放与真实协议输出仍由完整回归验证。

定向回归 **158 passed**，职责边界、兼容入口与冷启动检查 **27 passed**，文档合同 **27 passed**。本地工作区完整回归 **1,924 passed、89 skipped、0 failed**；89 项跳过均为平台限定的 Linux 黄金字节比对。black（325 个文件）、isort、mypy（198 个源码文件）和 `git diff --check` 通过，九份修改文档的本地链接/围栏与审计 JSON 检查通过。

工作区全套测试期间，另一个任务修改了 `application/description.py`、`diagnostics.py` 和体验脚本。为使最终证据对应固定源码，随后保存当前源码/测试/脚本与规则数据副本，以同一虚拟环境、显式 `PYTHONPATH=.:src` 从副本运行完整回归；包路径确认指向副本。固定副本的最终结果与工作区记录均保存于[验证记录](audits/2026-10-12/request-catalog-helpers/validation.json)，源码清单见[验证源码指纹](audits/2026-10-12/request-catalog-helpers/verified-source-manifest.json)。

固定副本也通过 **1,924 passed、89 skipped、0 failed**；源码清单与三份本地星历数据在测试期间未变化。星历目录被 Git 忽略，因此另行复制并保存[星历指纹](audits/2026-10-12/request-catalog-helpers/ephemeris-inventory.json)，保持原数据精度。后续工作区的 CLI/MCP 检查另有 **95 passed**；它们与固定副本验证分开记录。

另一个任务在固定副本保存前修改了 `analysis/career.py` 的一条官印相生说明。故最终副本原始比较为 **359 项相同、1 项事业文案变化**，不能把它写成最终工作区 360 项原始哈希相同。将这句新文案在事业响应及其快照中精确还原为旧文案后，事业整体 SHA-256 与原基线完全一致，证明评分及其他字段未变。该文案更改不属于本轮重构，未撤销它，也未重新冻结基线；原始与归一化结果见[并行文案差异](audits/2026-10-12/request-catalog-helpers/concurrent-career-text-delta.json)。

架构检查覆盖相对、绝对和函数内导入；受检静态图无循环，生产代码不再依赖旧 request/helpers 聚合模块，领域目录不反向导入装配器或直接导入计算服务。检查不展开动态导入和第三方内部依赖。

复核命令（仓库根、项目虚拟环境）：

```bash
PYTHONPATH=.:src .venv/bin/python \
  docs/audits/2026-10-12/request-catalog-helpers/capture_outputs.py /tmp/fatebridge-current.json
.venv/bin/python \
  docs/audits/2026-10-12/request-catalog-helpers/verify_definitions.py
.venv/bin/python -m pytest -q
.venv/bin/black --check src/fatebridge scripts tests
.venv/bin/isort --check-only src/fatebridge scripts tests
.venv/bin/mypy src/fatebridge
```

[审计目录](audits/2026-10-12/request-catalog-helpers/before-hashes.json)保留整理前/后指纹、原源码 SHA-256、定义基线和可重复比较脚本。本轮为本地 macOS 验证；Linux 参考环境的黄金字节比对和本轮重构的远程 CI 应单独确认。

2026-10-13 后续更新：本报告记录的旧导入路径、Python 别名和 `/api/calculate` 兼容入口已按用户要求删除。当前迁移方式及验证证据见[旧入口与兼容层清理验收](legacy-entry-cleanup-validation-2026-10-13.md)。历史 AST 基线对应当时源码；输出捕获脚本已改为从职责模块导入，不应将当前目录哈希与旧全目录哈希直接相等比较。
