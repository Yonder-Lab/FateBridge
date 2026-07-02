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

> 当前版本为 **Beta 0.2.0**，API 仍可能微调，欢迎试用与反馈。

---

## 它想解决什么问题

传统命理知识往往散落在不同书籍、软件和师承体系里，格式不统一，难以被现代系统复用。FateBridge 尝试做三件事：

1. **统一接口**：把 80 余种能力收敛成一致的调用方式，不用为每个技法重新对接；
2. **离线可跑**：核心能力不依赖外部服务，本地启动即可计算；
3. **可追溯**：每次调用都附带 `run_metadata`，知道是什么工具、什么时候、跑出了什么结果。

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

更详细的算法矩阵与精度说明，请见 [`docs/ALGORITHM_COVERAGE.md`](docs/ALGORITHM_COVERAGE.md)。

---

## 快速开始

### 1. 安装

推荐使用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/Yonder-Lab/FateBridge.git
cd FateBridge

uv venv
source .venv/bin/activate
uv pip install -e .
```

没有 uv 也可以用 pip：

```bash
python -m venv venv
source venv/bin/activate
pip install -e .
```

安装完成后，会同时获得三个入口：

- `fatebridge`（CLI）
- `fatebridge-api`（REST 服务）
- `fatebridge-mcp`（MCP 服务）

### 2. 启动 REST 服务

```bash
fatebridge-api
```

默认监听 `http://localhost:8010`。打开浏览器访问：

- 交互文档：`http://localhost:8010/docs`
- 健康检查：`http://localhost:8010/health`

> 端口 `8010` 建议只作为内部服务端口，不要直接暴露在公网。

### 3. 发送第一条请求

```bash
curl -X POST http://localhost:8010/api/calculate \
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

如果配置了 `FATEBRIDGE_API_KEYS`，需要额外带上 `X-API-Key` 请求头。

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

- 所有工具从同一个中央目录派生，参数 schema 三端一致；
- `GET /api/tools`（或 MCP 的 `tools/list`）可以自动枚举全部能力；
- 错误返回统一的 `{error, error_code, retryable}` 结构；
- 响应中始终包含 `run_metadata`，便于追踪与复现。

接入示例、字段投影、快照导出等细节，请见 [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md)。

---

## 文档地图

| 文档 | 适合谁 |
| --- | --- |
| [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) | 第一次使用的人 |
| [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) | 想把 FateBridge 接入 Agent 的开发者 |
| [`docs/API.md`](docs/API.md) | 需要查接口与参数的集成方 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 想理解代码结构的人 |
| [`docs/ALGORITHM_COVERAGE.md`](docs/ALGORITHM_COVERAGE.md) | 关心算法覆盖与精度的人 |
| [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) | 贡献者 |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | 遇到问题的人 |

---

## 项目状态

- 当前为 **Beta 0.2.0**，API 在到达 1.0 之前仍可能调整；
- 本仓库**不含前端界面**，接 UI 需要自行对接 REST 或 MCP；
- 核心占星盘支持本地高精度与近似离线两种路径；
- 西占推运 / 事件 / 寿命能力依赖 `kerykeion` / Swiss Ephemeris，缺失时会明确报错，不会静默降级。

完整变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。

---

## 参与贡献

欢迎提交 Issue 与 Pull Request。开发环境搭建、编码规范与提交流程，请见 [`CONTRIBUTING.md`](CONTRIBUTING.md) 与 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

---

## 许可证

[Apache-2.0](LICENSE)
