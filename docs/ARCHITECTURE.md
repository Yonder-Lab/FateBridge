# FateBridge 架构说明

本文档描述当前仓库的真实结构、运行路径和设计取舍。FateBridge 当前是一个 backend-only Python 仓库，同一套领域能力通过 FastAPI 和 FastMCP 双通道暴露。

## 1. 系统边界

```mermaid
flowchart LR
    Client["HTTP Client / Script / Agent Host"] --> REST["FastAPI<br/>fatebridge/api.py"]
    Client --> MCP["FastMCP<br/>fatebridge/mcp_server.py"]

    REST --> Models["Pydantic 请求模型"]
    MCP --> Args["Tool 参数归一化"]

    Models --> Services["fatebridge.services.*"]
    Args --> Services

    Services --> Helpers["fatebridge.utils.helpers"]
    Services --> Analysis["fatebridge.analysis.*"]
    Services --> Core["fatebridge.core.*"]

    Core --> Bundles["fatebridge/data/knowledge/*"]
    Core --> Contracts["导出合同 / section 规则"]
```

### 核心结论

- `fatebridge/api.py` 和 `fatebridge/mcp_server.py` 是两层 transport adapter，不承担核心算法
- 两层 transport 已开始共享 `fatebridge/services/tool_registry.py`，用来收敛部分 tool name / service binding / 描述定义
- `fatebridge/services` 是服务编排层，负责把 transport 输入转换成核心算法调用
- `fatebridge/core` 是主要算法层
- `fatebridge/utils/helpers.py` 是输入归一化和真太阳时修正的关键入口
- `fatebridge/data/knowledge` 与导出合同共同构成了“结果可消费层”
- `fatebridge/services/run_metadata.py` 为 REST / MCP 统一补充轻量 `run_metadata`

## 2. 分层职责

| 层 | 主要文件 | 职责 |
| --- | --- | --- |
| 传输层 | `fatebridge/api.py`, `fatebridge/mcp_server.py` | 路由、工具定义、请求模型、HTTP/MCP 错误包装 |
| 服务层 | `fatebridge/services/*.py` | 编排核心算法、拼装响应、生成 `snapshot_text` / `snapshot_export` |
| 分析层 | `fatebridge/analysis/*.py` | 复合分析逻辑，如配合度和时运影响 |
| 核心层 | `fatebridge/core/*.py` | 历法、八字、占星、占术、导出解析、知识索引 |
| 通用工具层 | `fatebridge/utils/*.py` | 出生信息模型、地点解析、真太阳时、公共格式化 |
| 数据层 | `fatebridge/data/knowledge/*.json` | 内置知识 bundle |
| 测试层 | `tests/*.py` | API/MCP 对齐、合同回归、算法回归 |

## 3. 代码地图

### 3.1 Transport

- `fatebridge/api.py`
  - 定义 FastAPI app、CORS、中英文 request model
  - 暴露 54 个 REST 路由（含 `/health`、`/ready`、`/metrics`）
  - 负责把 Pydantic 模型转为 service 参数
- `fatebridge/mcp_server.py`
  - 定义 FastMCP app
  - 暴露 50 个 MCP 工具
  - 返回 JSON 字符串，适合 Agent host 直接消费

### 3.2 Services

| 文件 | 职责 |
| --- | --- |
| `fatebridge/services/calculation.py` | 单人命理分析 |
| `fatebridge/services/compatibility.py` | 双人配合分析 |
| `fatebridge/services/timing.py` | 综合时运、大运、流年、流月、流日、流时、节气时间轴、calendar helper |
| `fatebridge/services/divination.py` | 梅花、卦义、统摄法、六爻、宿占、占星骰子、三式合一 |
| `fatebridge/services/metaphysics.py` | 紫微、六壬、奇门、太乙、金口诀 |
| `fatebridge/services/astrology.py` | 核心盘、关系盘、中点盘以及对应快照 |
| `fatebridge/services/western_timing.py` | 西占推运总览 |
| `fatebridge/services/western_timing_tools.py` | 独立 western timing technique 工具 |
| `fatebridge/services/knowledge.py` | 内置知识目录与条目读取 |
| `fatebridge/services/export_tools.py` | 导出注册表与快照解析 |
| `fatebridge/services/bazi.py` | 八字命盘与直断的独立快照输出 |
| `fatebridge/services/tool_registry.py` | 首批共享 tool descriptor registry |
| `fatebridge/services/run_metadata.py` | 统一生成 `run_id` / `trace_id` / `tool_name` / `generated_at` / `engine` |

### 3.3 Core

| 文件 | 职责 |
| --- | --- |
| `fatebridge/core/calendar.py` | 四柱计算、干支历法 |
| `fatebridge/core/almanac.py` | 节气、农历、calendar context |
| `fatebridge/core/elements.py` | 五行、十神、日主强弱 |
| `fatebridge/core/rules.py` | 格局、合冲刑害等规则 |
| `fatebridge/core/timing.py` | 时运基础算法 |
| `fatebridge/core/divination.py` | 梅花易数与卦义核心 |
| `fatebridge/core/gua_meanings.py` | 八卦/六十四卦离线断辞 |
| `fatebridge/core/astrology.py` | 核心占星盘、关系盘、近似/高精度双路径 |
| `fatebridge/core/astrology_predictive.py` | 西占返照、推运、时间主星系统 |
| `fatebridge/core/local_techniques.py` | 宿占、占星骰子、三式本地适配 |
| `fatebridge/core/export_contracts.py` | section 预设、导出规则、标准化 |
| `fatebridge/core/export_parser.py` | `snapshot_text -> snapshot_export` 解析 |
| `fatebridge/core/knowledge_store.py` | 内置知识索引与读取 |

## 4. 典型请求流

### 4.1 单人命理分析

```mermaid
sequenceDiagram
    participant C as Client
    participant API as fatebridge/api.py
    participant H as helpers.py
    participant S as services/calculation.py
    participant CAL as core/calendar.py
    participant ELE as core/elements.py
    participant RULE as core/rules.py
    participant ALM as core/almanac.py

    C->>API: POST /api/calculate
    API->>H: create_person_info(...)
    API->>S: calculate_destiny_analysis(person)
    S->>H: normalize_birth_time(person)
    S->>CAL: get_four_pillars(...)
    S->>ALM: build_calendar_context(...)
    S->>ELE: comprehensive_analysis(...)
    S->>RULE: harmony / clash / special pattern checks
    S-->>API: structured JSON result
    API-->>C: HTTP JSON response
```

这一条链路说明了 FateBridge 的一个核心原则：时间、地点和真太阳时修正必须先被标准化，然后才进入算法层。

### 4.2 快照导出流

```mermaid
flowchart TD
    Input["某独立工具结果"] --> Snapshot["service 生成 snapshot_text"]
    Snapshot --> Parser["core/export_parser.parse_export_content"]
    Parser --> Export["snapshot_export"]
    Export --> Downstream["Agent / UI / 二次导出"]
```

这套机制让大量工具共享一致的“可读文本 + 可筛选导出”合同，而不是各自发明私有输出格式。

## 5. 关键设计决策

### 5.1 双 transport，单核心

FateBridge 没有为 REST 和 MCP 分别维护两套领域逻辑。`fatebridge/api.py` 与 `fatebridge/mcp_server.py` 只负责接入层差异，真正算法都下沉到 `services` / `core`。当前首批 transport 定义已经通过共享 registry 收敛在 `fatebridge/services/tool_registry.py`，并继续按工具家族逐步迁移。

好处：

- REST 与 MCP 更容易保持响应一致
- API/MCP parity test 更容易写
- 文档可以按能力域组织，而不是按 transport 分裂

### 5.2 输入归一化前置

`fatebridge.utils.helpers` 统一处理以下问题：

- 出生地文本解析
- 时区名解析
- 经度补全
- 真太阳时修正
- 标准化出生时刻对象

这是 FateBridge 非常关键的稳定器，因为几乎所有八字、时运与部分 metaphysics 工具都依赖这条链路。

### 5.3 快照协议统一

很多术数工具天然适合“读一段说明”，但系统集成又需要结构化 section。FateBridge 的选择是同时输出：

- `snapshot_text`：面向人读
- `snapshot_export`：面向机器和二次消费

这让同一份结果既能给开发者看，也能给 Agent 继续拆解、裁剪和转述。

### 5.4 占星采用双精度路径

`fatebridge.core.astrology` 的策略是：

1. 若本地 `swisseph` 可用，优先走本地高精度路径
2. 若不可用，保留完全离线的近似轨道模型

这意味着：

- 核心 chart 家族具备“能跑起来”的兜底能力
- 但高阶 house system override 不会在缺失 `swisseph` 时假装精确，而是直接报错

### 5.5 西占推运不做静默降级

与核心 chart 不同，`fatebridge.core.astrology_predictive` 明确依赖 `kerykeion` / Swiss Ephemeris 运行时。缺依赖时，FateBridge 会直接报错，而不是伪造近似推运结果。

这是一个准确性优先的设计选择。

## 6. 运行时与配置

默认运行参数来自 `fatebridge/api.py`：

- `API_HOST=0.0.0.0`
- `API_PORT=8010`
- `ALLOWED_ORIGINS=http://localhost:3000`

`fatebridge/mcp_server.py` 则通过 `app.run()` 启动 FastMCP 服务。

## 7. 测试策略

当前测试大致分为四类：

- 领域能力测试：如 `tests/test_chinese_metaphysics.py`
- 占星与推运测试：如 `tests/test_astrology_tools.py`、`tests/test_western_timing_tools.py`
- API/MCP 对齐测试：`tests/test_api_alignment.py`
- 合同/导出测试：`snapshot_text`、`snapshot_export`、`selected_sections`

对于文档来说，最重要的事实是：FateBridge 不是只测算法本身，也在测 transport 层结果是否一致。

## 8. 扩展方式

新增一个能力时，推荐遵循下面的顺序：

1. 在 `core` 实现或补充底层算法
2. 在 `services` 中封装领域返回结构
3. 在 `fatebridge/api.py` 增加 request model 和 REST 路由
4. 在 `fatebridge/mcp_server.py` 增加对应 MCP 工具
5. 在 `tests/` 增加能力测试与 API/MCP 对齐测试
6. 更新 [API.md](API.md) 和 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)

## 9. 当前非目标

以下内容当前不在仓库架构内：

- 内置 Web 前端
- 数据库存储与账户体系
- 任务编排平台、队列、缓存层
- 多服务拆分

因此阅读和扩展本仓库时，应把它理解为“单仓库、多能力的 Python 领域服务”，而不是完整产品栈。
