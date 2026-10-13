# FateBridge 代码结构审查与整理（2026-10-12）

## 结论与范围

FateBridge 已有中央工具目录、统一请求/响应合同、领域服务与多协议入口。主要问题是跨层职责聚集在少数模块，以及共用计算/常量依附于较高层的消费者。此次沿用原有计算链，按职责抽取模块，保留公开工具、算法与兼容导入。

审查初始扫描覆盖 130 个 Python 模块、56,856 行包代码，包含函数内部的全限定导入。发现五条 DFS 循环路径，分别集中于发现/场景/协议工具链和占星/古典规则/推运共享模块。这里的循环是代码依赖循环，不等同于运行时必然发生 ImportError；原有延迟导入已经规避了部分加载错误，但职责之间仍互相依赖。

工作区原有的未提交文档和 CI 证据保留。整理期间另有 CLI 示例、诊断与发现能力的更新；那些功能调整不作为本次内聚/耦合整理的成果。验证报告记录当前工作区状态，不能替代它们各自的功能审查。

## 发现与已落实的整理

| 发现 | 对内聚与耦合的影响 | 落实方式 |
| --- | --- | --- |
| `core/tool_spec.py` 初始 1,150 行，同时定义工具、绑定请求、执行服务、生成描述、投影输出、注册 REST/MCP | 协议签名、领域绑定和运行时编排一起变化；核心目录依赖服务与 MCP 适配器 | 定义、绑定、执行、投影和描述拆到 `application`；注册器拆到 `transports` |
| `core/discovery.py` 筛选时调用 scenarios，而 scenarios 为输出摘要回调 discovery | 两个用途不同的模块互相依赖 | 移入应用层；两者共享 `application.description.summarize_spec` |
| `services/calculation.py` 同时拥有出生计算上下文和综合分析响应；八字/时运/配合度导入其私有上下文构造器 | 通用出生计算依附于一个具体分析服务 | 抽出 `services.birth_context`，提供公开 `build_birth_computation_context` |
| `classical_western` 从 astrology 取星座与尊贵表，又从 predictive._common 取埃及界表；astrology 反过来调用古典规则 | 基础表绑在引擎模块中，古典规则取常量就会加载推运后端 | 原值移到无引擎依赖的 `core.astrology_tables`；三个消费者共同依赖它 |
| 测试和内部代码把旧 `core.tool_spec` 同时当作执行器与注册器 | 拆分后容易继续依赖兼容聚合模块，或把故障注入打在非定义模块 | 内部调用与故障注入迁到定义模块；兼容性测试专门覆盖旧路径 |

`application/tool_spec.py` 保持冻结的 `ToolSpec` 和 `ExecutionHints`。`application/execution.py` 保持绑定后执行、成功结果转换、输出校验、随机 seed、时钟隔离和 receipt 的顺序；`execute_spec` 仍是无元数据调用，`execute_tool` 为三端共享执行入口。

`transports/rest.py` 与 `transports/mcp.py` 保持真实动态签名、输出选项、校验错误和协议返回语义。两个注册器的公共选项描述放在 `transports/flags.py`。没有引入依赖注入容器、服务基类或插件框架；中央目录仍承担装配职责。

## 整理后的结构

```text
src/fatebridge/
├── api.py / mcp_server.py / cli.py  # 应用入口
├── transports/
│   ├── rest.py                    # HTTP 注册与协议处理
│   ├── mcp.py                     # MCP 注册与签名适配
│   └── flags.py                   # 输出选项说明
├── application/
│   ├── tool_spec.py               # 工具声明
│   ├── bindings.py                # 请求 -> 服务参数
│   ├── execution.py               # 统一执行/校验/receipt
│   ├── projection.py              # 输出字段投影
│   ├── description.py             # 共享工具描述
│   ├── discovery.py               # 目录筛选与发现
│   └── scenarios.py               # 场景与实时能力关联
├── services/
│   ├── tool_catalog.py            # 工具装配的唯一信源
│   ├── birth_context.py           # 通用出生计算上下文
│   └── ...                        # 各领域用例与响应编排
├── analysis/                      # 复合分析规则
├── core/
│   ├── astrology_tables.py        # 无引擎依赖的公共领域表
│   ├── tool_spec.py               # 旧路径兼容导出
│   ├── discovery.py / scenarios.py# 旧路径兼容导出
│   └── ...                        # 领域算法与合同
└── utils/ / data/                  # 归一化、运行公共层、规则数据
```

此图列出本次整理的模块；同一工作区新增的 examples/diagnostics 能力由其自身文档维护。

依赖约束：核心算法/分析/共享工具不依赖应用编排或协议层；应用编排与领域服务不依赖 REST/MCP/CLI 适配器。`services.tool_catalog` 是装配点，依赖工具声明和绑定器符合它的职责。

旧 `core.tool_spec`、`core.discovery`、`core.scenarios` 重导出同一函数和模型对象，没有复制执行实现。历史 `services.calculation._build_birth_computation_context` 仍为新构造器的别名。内部故障注入、monkeypatch 应针对定义模块；旧聚合模块属性不是另一份执行器。

## 验证方法

整理前使用全工具代表输入固定 `as_of=2026-10-12T12:00:00+08:00`，保存 87 个 REST 工具业务输出，以及完整发现和场景合同的规范 JSON SHA-256。结构抽取完成后的第一轮重新计算，逐项相同。最终工作区复核时，87 项业务输出仍相同；发现与场景合同随后因并行任务新增 key、CLI 名称及示例发生变化，保留在 final-workspace-hashes.json，不能归因于本次结构整理。

业务比较移除整个 `run_metadata`：run ID、耗时、执行时间会变化，源码指纹在重构后也应变化。元数据、错误、投影、MCP 原生结构化输出和旧 Python 入口由现有回归另行验证，因此哈希一致不是元数据完全相同的声明。

证据和复核脚本在 [code-structure 审计目录](audits/2026-10-12/code-structure/validation.json)。可在仓库根使用项目解释器重新运行：

```bash
PYTHONPATH=.:src .venv/bin/python \
  docs/audits/2026-10-12/code-structure/capture_outputs.py /tmp/fatebridge-outputs.json
```

`tests/test_architecture_boundaries.py` 检查分层依赖以及包含函数内导入的全限定静态导入图。整理后的受检图无循环；此检查不展开动态服务导入和第三方内部依赖，不代表所有形式的运行时耦合都已消除。

完整回归结果为 **1,908 passed、89 skipped、0 failed**；89 项跳过均为平台限定的 Linux 黄金字节比对。格式、导入顺序与 mypy（146 个源码模块）通过，27 项文档合同检查通过。25 个迁移的工具声明/绑定/执行/注册定义 AST 与原实现相同，八份基础表逐值相同。源码、测试与规则数据在最终整套回归期间稳定，仅并行任务的 `scripts/experience_codex.py` 更新。结果与原始 JUnit、pytest 输出写入上述审计目录。这里是本地 macOS 验证；受平台约束的 Linux 黄金快照字节比对以及远程 CI 不作为已完成项。

## 后续热点与优先级

| 优先级 | 热点 | 建议与边界 |
| --- | --- | --- |
| 中，已完成后续整理 | `core/astrology.py` 初始 3,457 行，包含出生信息、基础星盘、相位、中点和多种关系盘 | 实现迁到 `core/astro/`，本命/关系盘、位置/宫位、相位/古典层各有归属；旧模块仅兼容导出。宫制、黄道、太阳时、近似引擎与关系变体比较一致 |
| 中，已完成后续整理 | `services/timing.py` 初始 2,028 行，同时组织多个时间层、五维评分与快照 | 时间层状态与时间线迁到 `timing_state`，文本迁到 `timing_snapshots`，日历查询迁到 `calendar_tools`；八字直接依赖公开状态构造器 |
| 中，已完成后续整理 | `services/bazi.py`、`services/compatibility.py` 仍复用 calculation 的 `_render_destiny_analysis` | 公共命盘响应迁到 `birth_payload.build_destiny_payload`；消费者直接调用它，旧私有入口保留别名 |
| 低，已完成后续整理 | `core/request_models.py` 初始 1,769 行，`services/tool_catalog.py` 初始 1,294 行 | 模型迁到 `core/requests/`，声明与绑定迁到 `services/catalog/`；中央目录保留有序装配和合同补全，继承、顺序、唯一性与跨端合同验证一致 |
| 低，已完成后续整理 | `utils/helpers.py` 聚合输入模型、出生时间归一化与显示格式 | 拆为出生输入、太阳时、展示格式、分析时钟和五行关系；旧入口重导出，内部消费者使用定义模块 |

大文件不是自动的架构错误。`core/fengshui`、`core/predictive`、`core/local_techniques` 已按领域/技法组织，保留其边界；专业输出模型也已按领域拆分。后续整理应以独立变化的职责和真实复用关系为依据，并保留同环境输出比较及跨端回归。

中优先级热点已完成，详情见 [星盘与时运结构整理验收](astro-timing-structure-validation-2026-10-12.md)。剩余低优先级请求模型、目录和 helpers 也已按职责拆分，详情见 [低优先级热点整理验收](request-catalog-helpers-validation-2026-10-12.md)。两轮沿用既有合同和计算实现，分别保留整理前/后比较与回归证据。

2026-10-13 后续更新：本报告记录的旧导入路径、Python 别名和 `/api/calculate` 兼容入口已按用户要求删除。当前迁移方式及验证证据见[旧入口与兼容层清理验收](legacy-entry-cleanup-validation-2026-10-13.md)。历史 AST 基线对应当时源码；输出捕获脚本已改为从职责模块导入，不应将当前目录哈希与旧全目录哈希直接相等比较。
