# FateBridge

> 一座连接中国传统命理、占术与西方占星的「计算桥」——把八字、紫微、奇门、星盘等推演沉淀为**可调用、可溯源、三端一致**的后端能力。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-alpha-orange.svg)](#项目状态)
[![Tools](https://img.shields.io/badge/tools-80%20across%2013%20families-success.svg)](docs/ALGORITHM_COVERAGE.md)
[![Interfaces](https://img.shields.io/badge/interfaces-REST%20%7C%20MCP%20%7C%20CLI-informational.svg)](docs/AGENT_GUIDE.md)
[![CI](https://github.com/thomas-yanxin/FateBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/thomas-yanxin/FateBridge/actions/workflows/ci.yml)

FateBridge 是一个 **backend-only** 的 Python 仓库：只包含服务端与核心算法，不含前端应用。同一套领域能力通过 **FastAPI（REST）**、**FastMCP** 与 **命令行（`fatebridge` CLI）** 三类接口对外暴露，三者均由中央工具目录（[`fatebridge/services/tool_catalog.py`](fatebridge/services/tool_catalog.py)）统一声明、自动注册。

> 当前默认提供 **80 个业务 REST 路由**（另含 `/health`、`/ready`、`/metrics` 三个运维端点）、**80 个 FastMCP 工具**，以及对应的 `fatebridge` CLI 子命令。以上数字均由中央目录派生，并由 `tests/test_doc_tool_counts.py` 锁定，避免与代码漂移。

## 目录

- [核心特性](#核心特性)
- [能力一览](#能力一览)
- [快速开始](#快速开始)
- [给 Agent / 开发者](#给-agent--开发者)
- [统一约定](#统一约定)
- [文档地图](#文档地图)
- [仓库结构](#仓库结构)
- [开发与验证](#开发与验证)
- [项目状态](#项目状态)
- [许可证](#许可证)

## 核心特性

- 🀄 **中国命理为核心**：八字（含九大专项维度）、配合度、大运/流年时运、节气/农历 helper、梅花、六爻、奇门、太乙、六壬、金口诀、紫微斗数等
- 🔭 **离线占星**：标准盘、13 扇区盘、希腊盘、果老盘、印度盘、德国中点盘、关系/合盘；本地有 Swiss Ephemeris 走高精度，否则回退内置近似模型
- 🪐 **西占进阶推运**：太阳/月返照、行运、太阳弧、小限、指定年盘、主限、黄道释放、法达、十年星限，以及事件盘与全生命周期技法
- 🔌 **三端一致**：REST / MCP / CLI 由单一 `ToolSpec` 目录派生，工具集合、参数 schema、错误形状天然对齐
- 🤖 **Agent 友好**：机读自描述（`/api/tools`、`fatebridge describe`）、统一错误包络、字段投影（token 预算）、可导出快照协议
- 🧾 **可溯源**：结构化响应统一带 `run_metadata`（`run_id` / `trace_id` / `tool_name` / `generated_at` / `engine`）

## 能力一览

| 能力域 | 代表接口 | 说明 |
| --- | --- | --- |
| 八字与命理 | `/api/calculate`、`/api/cn/bazi/*` | 出生信息归一化、四柱、五行、格局、喜用神 + 婚姻/事业/财运/健康/子女/学业/性格/六亲/正缘九大专项 |
| 双人配合 | `/api/compatibility`、`/api/compatibility/sukuyo` | 八字合婚 / 合作；宿曜相性 |
| 时运分析 | `/api/timing/*` | 综合时运、大运、流年、流月、流日、流时、节气时间轴 |
| Calendar / 卦义 helper | `/api/cn/jieqi/year`、`/api/cn/nongli/time`、`/api/divination/gua` | 历法与义理辅助面 |
| 占卜 / 本地技法 | `/api/divination/*` | 梅花、统摄法、六爻、参评数、河洛、宿占、占星骰子、三式合参 |
| 中国术数独立盘 | `/api/cn/ziwei/*`、`/api/cn/liureng/*`、`/api/cn/qimen`、`/api/cn/taiyi`、`/api/cn/jinkou` | 统一支持 `snapshot_text + snapshot_export` |
| 核心占星盘 | `/api/astro/*` | 离线星盘、派生盘、关系盘 |
| 西占推运 / 事件 / 寿命 | `/api/astro/timing*`、`/api/astro/event/*`、`/api/astro/lifespan/*` | 独立 technique 工具 |
| 导出与知识 | `/api/export/*`、`/api/knowledge/*` | 导出协议与内置知识库（含八字知识库） |

完整的「13 family / 80 工具」算法矩阵与精度/依赖说明见 **[docs/ALGORITHM_COVERAGE.md](docs/ALGORITHM_COVERAGE.md)**。

能力建议按三类理解：

- **已实现**：八字、时运、主要 divination / metaphysics 工具、导出与知识 helper
- **近似离线**：核心占星盘与部分关系盘在缺少本地 Swiss Ephemeris 时回退到内置近似轨道模型
- **依赖本地运行时**：西占推运 / 事件 / 寿命能力依赖 `kerykeion` / Swiss Ephemeris，缺依赖时**直接报错而非静默降级**

## 快速开始

### 1. 克隆与安装

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge
```

推荐用 [uv](https://docs.astral.sh/uv/)（建虚拟环境 + 装依赖一步到位）：

```bash
uv venv                  # 可加 --python 3.13 指定版本
source .venv/bin/activate
uv pip install -e .      # 跑测试/格式化用 -e ".[dev]"
```

没装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`。也可继续用 pip：

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
```

默认让 REST API 监听 `http://localhost:8010`。可选项：

```bash
API_HOST=0.0.0.0
API_PORT=8010
ALLOWED_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO

# 可选：启用 REST API key 鉴权
FATEBRIDGE_API_KEYS=agent:replace-me
API_KEY_HEADER_NAME=X-API-Key
```

> 端口 `8010` 应视为内部服务端口，不应直接暴露为公网业务入口。

### 3. 启动服务

```bash
python -m fatebridge.api      # REST，或：fatebridge-api
python -m fatebridge.mcp_server  # FastMCP，或：fatebridge-mcp
```

REST 启动后可访问 Swagger UI `:/docs`、ReDoc `:/redoc`、健康检查 `:/health`、就绪 `:/ready`、指标 `:/metrics`。FastMCP 适合给 Claude、Cursor、Codex 等 Agent 宿主作为工具面接入。

### 4. 发送第一个请求

```bash
curl -X POST http://localhost:8010/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三", "gender": "男",
    "birth_year": 1990, "birth_month": 5, "birth_day": 15,
    "birth_hour": 10, "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai", "use_true_solar_time": true,
    "birth_place": "北京"
  }'
```

未配置 `FATEBRIDGE_API_KEYS` 时可省略 `X-API-Key`；一旦配置，除 `/health`、`/ready`、`/metrics` 与文档页外都需带上。

更细的上手步骤见 [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)。

## 给 Agent / 开发者

所有工具（80 个）只在中央目录 [`fatebridge/services/tool_catalog.py`](fatebridge/services/tool_catalog.py) 中以 `ToolSpec` **声明一次**，自动挂载到三端：

- **REST**（[`fatebridge/api.py`](fatebridge/api.py) → `register_rest`）
- **MCP**（[`fatebridge/mcp_server.py`](fatebridge/mcp_server.py) → `register_mcp`）
- **CLI**（[`fatebridge/cli.py`](fatebridge/cli.py)）

新增一个工具或分析维度只需在目录中追加一个 `ToolSpec`，无需改动任何接口文件。

```bash
# 机读能力发现（不必硬编码工具表）
curl http://localhost:8010/api/tools     # REST：返回每个工具的参数 schema/接口/family
fatebridge list                          # CLI：列出所有工具
fatebridge describe bazi_wealth           # CLI：单工具 schema + 示例（JSON）

# 大运/流年自动推算，无需手动输入
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male

# 字段投影（token 预算）：只取需要的字段，run_metadata 始终保留
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields analysis_type wealth_analysis
```

端到端接入说明（自助发现、错误处理、字段投影、MCP host 配置、Python/JS 示例）见 **[docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md)**。

## 统一约定

- **错误包络**：三端统一返回扁平的 `{error, error_code, retryable}`；请基于 `error_code`（`validation_error` / `authentication_required` / `dependency_missing` / `internal_error`）而非文案分支。
- **快照协议**：大量工具返回 `snapshot_text`（人读）+ `snapshot_export`（可按 `selected_sections` 裁剪导出），让结果可直接二次消费或喂给 Agent。`selected_sections` 只裁剪导出层，不裁完整结构化 payload。
- **字段投影**：CLI 的 `--fields` 与 MCP 工具的 `fields` 参数可把响应裁剪到指定顶层 key 或点号子路径（如 `bazi_birth.day_master`）。

```json
{
  "run_metadata": {"run_id": "f5c3...", "tool_name": "qimen", "engine": "fatebridge-offline"},
  "snapshot_text": "[起盘信息]\n...",
  "snapshot_export": {"selected_sections": ["起盘信息"], "export_text": "[起盘信息]\n..."}
}
```

完整字段与请求族见 [docs/API.md](docs/API.md)。

## 文档地图

| 文档 | 适合谁 | 内容 |
| --- | --- | --- |
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | 新用户、集成方 | 安装、环境变量、启动、第一条请求 |
| [docs/AGENT_GUIDE.md](docs/AGENT_GUIDE.md) | Agent / 开发者 | 三端接入、自助发现、错误/投影/快照、host 配置、Python/JS 示例 |
| [docs/API.md](docs/API.md) | 集成方 | REST 路由、FastMCP 工具、请求族、响应字段 |
| [docs/ALGORITHM_COVERAGE.md](docs/ALGORITHM_COVERAGE.md) | 维护者、评审者 | 13 family / 80 工具算法矩阵 + 精度/依赖说明 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 开发者、架构师 | 代码分层、数据流、设计决策 |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | 贡献者 | 开发命令、测试策略、扩展路径 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 所有人 | 安装/依赖/端口/CORS/快照导出问题 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献者 | 分支、PR 流程、提交规范 |

文档总入口：[docs/README.md](docs/README.md)。

## 仓库结构

```text
FateBridge/
├── fatebridge/
│   ├── api.py          # REST (FastAPI) 入口
│   ├── mcp_server.py   # MCP (FastMCP) 入口
│   ├── cli.py          # CLI 入口
│   ├── services/       # transport-facing 编排层 + 中央工具目录
│   ├── core/           # 核心算法：历法、八字、占星、占术、导出合同
│   ├── analysis/       # 复合分析（配合度、时运影响…）
│   ├── data/           # 内置知识 bundle
│   └── utils/          # 输入归一化、真太阳时、地点解析
├── tests/
├── docs/
├── requirements.txt
├── pyproject.toml
└── CONTRIBUTING.md
```

各层职责详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 开发与验证

```bash
pytest -q
pytest tests/test_api_alignment.py -q

black --check fatebridge scripts tests
isort --check-only fatebridge scripts tests
mypy fatebridge/
```

> 测试需在装了 `.[dev]` 的 Python 3.10–3.13 环境里跑（对齐 CI 矩阵），别用系统解释器。详见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 项目状态

- 当前为 **Alpha**（`0.1.0`），API 仍可能调整
- 本仓库**不含** in-repo Web 前端；接 UI 需自行对接 REST API 或 MCP
- 核心占星 chart 家族支持本地高精度与近似离线双路径
- 西占推运/事件/寿命能力**不做静默降级**——缺运行时依赖时直接报错
- `selected_sections` 只影响 `snapshot_export.export_text` 的裁剪，不裁完整结构化 payload

欢迎贡献：见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[Apache-2.0](LICENSE)。
