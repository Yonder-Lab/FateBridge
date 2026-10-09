# FateBridge

> 一座把中国传统命理、占术与西方占星从「口耳相传」变成「可调用、可验证、可溯源」的计算桥。

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](pyproject.toml)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](CHANGELOG.md)
[![CI](https://github.com/Yonder-Lab/FateBridge/actions/workflows/ci.yml/badge.svg)](https://github.com/Yonder-Lab/FateBridge/actions/workflows/ci.yml)

FateBridge 不是占卜 App，也不是命理 frontend，而是一个**后端能力库**。它把八字、紫微、奇门、六壬、太乙、梅花、六爻、西方占星与推运等技法，沉淀成一套统一的服务端接口，让开发者、研究者或 Agent 能够像调用普通 API 一样调用它们。

同一套能力，通过三种形态对外提供：

- **REST** —— 用 HTTP 调用，适合网页、脚本、微服务接入；
- **MCP** —— 用 FastMCP 暴露给 Claude、Cursor、Codex 等 Agent；
- **CLI** —— 命令行直接交互，适合本地调试与自动化脚本。

当前版本将所有工具（80 个）同时暴露为 **80 个业务 REST 路由** 与 **80 个 FastMCP 工具**，三端由同一份中央目录派生；目录含 82 条记录，CLI 可执行其中 81 条。各端的名称与请求形态差异见 [API 参考](docs/api-reference.md#24-三端能力边界)。

> 当前版本为 **Beta 0.2.0**，API 仍可能微调，欢迎试用与反馈。

完整的「12 family / 80 工具」算法矩阵与精度/依赖说明见 **[docs/algorithm-coverage.md](docs/algorithm-coverage.md)**。

---

## 它想解决什么问题

传统命理知识往往散落在不同书籍、软件和师承体系里，格式不统一，难以被现代系统复用。FateBridge 尝试做三件事：

1. **统一接口**：把 80 项公开能力收敛成一致的调用方式，不用为每个技法重新对接；
2. **离线可跑**：核心能力不依赖外部服务，本地启动即可计算；
3. **可追溯**：成功的工具响应默认附带 `run_metadata`，知道是什么工具、什么时候、跑出了什么结果。

---

## 能力概览

| 领域 | 示例能力 |
| --- | --- |
| 八字命理 | 四柱、日主强弱、格局、喜用神，以及婚姻、事业、财运、健康、子女、学业、性格、六亲、正缘九大专项 |
| 双人关系 | 八字合婚 / 合作配合度、宿曜相性 |
| 时运流年 | 大运、流年、流月、流日、流时、节气时间轴 |
| 中国术数独立盘 | 紫微斗数、奇门遁甲、六壬、太乙神数、金口诀 |
| 占卜与本地技法 | 梅花易数、六爻、统摄法、参评数、河洛理数、宿占、占星骰子、三式合参 |
| 西方占星 | 标准盘、13 扇区盘、希腊盘、果老盘、印度盘、中点盘、关系盘 |
| 西占推运 | 太阳/月返照、行运、太阳弧、小限、主限、黄道释放、法达、十年星限等 |

更详细的算法矩阵与精度说明，请见 [`docs/algorithm-coverage.md`](docs/algorithm-coverage.md)。

---

## 快速开始

### 1. 安装

推荐使用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/Yonder-Lab/FateBridge.git
cd FateBridge

uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

没有 uv 也可以用 pip：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

安装完成后，会同时获得三个入口：

- `fatebridge`（CLI）
- `fatebridge-api`（REST 服务）
- `fatebridge-mcp`（MCP 服务）

### 2. 启动 REST 服务

```bash
API_HOST=127.0.0.1 fatebridge-api
```

默认监听 `http://localhost:8010`。打开浏览器访问：

- 交互文档：`http://localhost:8010/docs`
- 健康检查：`http://localhost:8010/health`

> 端口 `8010` 建议只作为内部服务端口，不要直接暴露在公网。

### 3. 发送第一条请求

```bash
curl -X POST http://localhost:8010/api/cn/bazi/birth \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三", "gender": "男",
    "birth_year": 1990, "birth_month": 5, "birth_day": 15,
    "birth_hour": 10, "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "birth_place": "北京",
    "use_true_solar_time": true
  }'
```

这是推荐的独立八字命盘入口，业务字段位于 `bazi_birth`。`/api/calculate` 保留旧版扁平响应；综合命理 `analyze_destiny` 通过 MCP / CLI 调用。若配置了 `FATEBRIDGE_API_KEYS`，请求需额外带上 `X-API-Key`。

### 4. 命令行用法

```bash
# 列出所有工具
fatebridge list

# 查看某个工具的参数
fatebridge describe bazi_wealth

# 直接调用
fatebridge bazi_wealth \
  --birth-year 1990 --birth-month 6 --birth-day 15 \
  --birth-hour 10 --gender male
```

---

## 给 Agent 开发者

FateBridge 被设计成 Agent 友好的：

- 所有工具从同一个中央目录派生，共享请求模型派生各端 schema；
- `GET /api/tools`（或 MCP 的 `tools/list`）可以自动枚举全部能力；
- 错误返回统一的 `{error, error_code, retryable}` 结构；
- 成功响应默认包含 `run_metadata`，便于追踪；CLI 可用 `--no-metadata` 关闭。

接入示例、字段投影、快照导出等细节，请见 [`docs/agent-guide.md`](docs/agent-guide.md)。

---

## 文档地图

| 文档 | 适合谁 | 内容 |
| --- | --- | --- |
| [`docs/getting-started.md`](docs/getting-started.md) | 第一次使用的人 | 安装、环境变量、启动、第一条请求 |
| [`docs/agent-guide.md`](docs/agent-guide.md) | Agent / 开发者 | 三端接入、自助发现、错误/投影/快照、host 配置、Python/JS 示例 |
| [`docs/api-reference.md`](docs/api-reference.md) | 集成方 | REST 路由、FastMCP 工具、请求族、响应字段 |
| [`docs/algorithm-coverage.md`](docs/algorithm-coverage.md) | 维护者、评审者 | 12 family / 80 工具算法矩阵 + 精度/依赖说明 |
| [`docs/scenario-routing.md`](docs/scenario-routing.md) | Agent / 技能作者 | 按用户场景选主证/旁证工具的路由矩阵 |
| [`docs/architecture.md`](docs/architecture.md) | 开发者、架构师 | 代码分层、数据流、设计决策 |
| [`docs/development-guide.md`](docs/development-guide.md) | 贡献者 | 开发命令、测试策略、扩展路径 |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | 所有人 | 安装/依赖/端口/CORS/快照导出问题 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 贡献者 | 分支、PR 流程、提交规范 |
| [`skills/README.md`](skills/README.md) | Onda / 场景技能开发者 | 8 个泛心理陪伴场景 Skill，对工具的场景化再包装 |

文档总入口：[docs/README.md](docs/README.md)。

---

## 仓库结构

```text
FateBridge/
├── src/
│   └── fatebridge/         # 包代码（src layout：装包后才可 import）
│       ├── api.py          # REST (FastAPI) 入口
│       ├── mcp_server.py   # MCP (FastMCP) 入口
│       ├── cli.py          # CLI 入口
│       ├── services/       # transport-facing 编排层 + 中央工具目录
│       ├── core/           # 核心算法：历法、八字、占星、占术、导出合同
│       ├── analysis/       # 复合分析（配合度、时运影响…）
│       ├── data/           # 内置知识 bundle
│       └── utils/          # 输入归一化、真太阳时、地点解析
├── tests/
├── docs/
├── pyproject.toml
└── CONTRIBUTING.md
```

各层职责详见 [`docs/architecture.md`](docs/architecture.md)。

---

## 开发与验证

```bash
pytest -q
pytest tests/test_api_alignment.py -q

black --check src/fatebridge scripts tests
isort --check-only src/fatebridge scripts tests
mypy src/fatebridge/
```

> 测试需在装了 `.[dev]` 的 Python 3.10–3.13 环境里跑（对齐 CI 矩阵），别用系统解释器。详见 [`docs/development-guide.md`](docs/development-guide.md)。

---

## 项目状态

- 当前为 **Beta 0.2.0**，API 在到达 1.0 之前仍可能调整；
- 本仓库**不含前端界面**，接 UI 需要自行对接 REST 或 MCP；
- 核心占星盘支持本地星历与离线近似路径，实际模型需检查 `chart_profile.ephemeris_model` 和 `run_metadata.engine_is_approximate`；
- 西占推运 / 事件 / 寿命能力依赖 `kerykeion` / Swiss Ephemeris，缺失时会明确报错，不会静默降级。

完整变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。

---

## 参与贡献

欢迎提交 Issue 与 Pull Request。开发环境搭建、编码规范与提交流程，请见 [`CONTRIBUTING.md`](CONTRIBUTING.md) 与 [`docs/development-guide.md`](docs/development-guide.md)。

---

## 许可证

本仓库代码采用 [Apache-2.0](LICENSE)，第三方组件说明见 [NOTICE](NOTICE)。星历数据需单独获取，安装与运行边界见 [快速入门](docs/getting-started.md#星历数据与精度)。
