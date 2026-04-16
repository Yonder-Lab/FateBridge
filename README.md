# FateBridge

FateBridge 是一个面向命理、占术与离线占星场景的 Python 后端仓库。当前仓库只包含服务端与核心算法，不包含前端应用；同一套领域能力同时通过 FastAPI 和 FastMCP 对外暴露，便于 Web 集成、脚本调用与 Agent 工具接入。

> 当前仓库默认提供 51 个 REST 路由（含 `/health`）和 50 个 FastMCP 工具。

## 项目定位

- 以中国命理为核心：八字、配合度、时运、节气/农历 helper、梅花易数、六爻、奇门、太乙、六壬、金口诀等
- 提供离线占星能力：标准盘、13 扇区盘、希腊盘、果老风格盘、印度盘、中点盘、关系盘
- 提供西占推运能力：太阳返照、月返、行运、太阳弧、小限、指定年盘、主限、黄道释放、法达、十年星限
- 提供可导出的快照协议：大量工具统一返回 `snapshot_text` 和 `snapshot_export`
- 提供知识与导出 helper：`knowledge_registry` / `knowledge_read` / `export_registry` / `export_parse`
- 结构化工具响应额外返回 `run_metadata`，统一暴露 `run_id` / `trace_id` / `tool_name` / `generated_at` / `engine`

## 能力状态

FateBridge 当前能力建议按三类理解：

- 已实现：八字、时运、主要 divination / metaphysics 工具、导出与知识 helper
- 近似离线：核心占星盘与部分关系盘在缺少本地 Swiss Ephemeris 时会回退到 FateBridge 内置近似轨道模型
- 依赖本地运行时：西占推运能力依赖 `kerykeion` / Swiss Ephemeris 运行时

完整矩阵见 [docs/ALGORITHM_COVERAGE.md](docs/ALGORITHM_COVERAGE.md)。

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
```

默认配置会让 REST API 监听 `http://localhost:8010`。如需修改，可编辑 `.env`：

```bash
API_HOST=0.0.0.0
API_PORT=8010
ALLOWED_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
RATE_LIMIT_EXEMPT_CLIENTS=

# 可选：启用 REST API key 鉴权
FATEBRIDGE_API_KEYS=agent:replace-me
API_KEY_HEADER_NAME=X-API-Key

# 可选：单个 API key 的 UTC 日配额，0 表示关闭
API_KEY_DAILY_QUOTA=0
```

- `RATE_LIMIT_EXEMPT_CLIENTS` 允许你为受信任的内部来源跳过通用请求频率限制。
- 当 FateBridge 仅作为 HorizonX 的同机私有上游时，推荐设置为 `127.0.0.1,::1`。
- 端口 `8010` 应视为内部服务端口，不应直接暴露为公网业务入口。

### 3. 启动 REST API

```bash
python api.py
# 或
fatebridge-api
```

可访问：

- Swagger UI: `http://localhost:8010/docs`
- ReDoc: `http://localhost:8010/redoc`
- 健康检查: `http://localhost:8010/health`
- 就绪检查: `http://localhost:8010/ready`
- 指标: `http://localhost:8010/metrics`

### 4. 启动 FastMCP

```bash
python fastmcp_server.py
# 或
fatebridge-mcp
```

FastMCP 适合给 Claude、ChatGPT、Cursor、Codex 等 Agent 宿主作为工具面接入。

### 5. 发送第一个请求

```bash
curl -X POST http://localhost:8010/api/calculate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace-me" \
  -d '{
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": true,
    "birth_place": "北京"
  }'
```

如果没有配置 `FATEBRIDGE_API_KEYS`，可以省略 `X-API-Key` 请求头；一旦配置了，除 `/health`、`/ready`、`/metrics` 和文档页外，其他 REST 端点都需要带上 API key。

## 你会拿到什么

### 基础分析类结果

`/api/calculate`、`/api/compatibility`、`/api/timing/*` 这类端点会返回结构化 JSON，例如：

- `run_metadata`
- `person_info`
- `four_pillars`
- `day_master`
- `element_distribution`
- `structure_profile`
- `patterns`
- `calendar_context`

其中八字类结果新增 `structure_profile`，会把当前主格局、次级格局、最终喜用五行、可用十神与合冲事件对格局流通的影响结构化返回；`/api/compatibility` 的 `detailed_analysis` 也会补充 `score_basis`、`supportive_patterns`、`tension_patterns`、`risk_patterns` / `risk_reasons` 等解释字段，用于区分“和合支持”“高张力吸引”和“明显风险”。

### 快照类结果

大量独立工具还会返回统一的快照协议：

```json
{
  "run_metadata": {
    "run_id": "f5c3...",
    "trace_id": "5f17...",
    "tool_name": "qimen",
    "generated_at": "2026-04-13T08:00:00Z",
    "engine": "fatebridge-offline"
  },
  "snapshot_text": "[起盘信息]\n...",
  "snapshot_export": {
    "technique": {
      "key": "qimen"
    },
    "selected_sections": ["起盘信息", "九宫方盘"],
    "section_titles_detected": ["起盘信息", "九宫方盘", "离九宫"],
    "export_text": "[起盘信息]\n..."
  }
}
```

这让 FateBridge 的结果可以直接被二次消费、裁剪导出或喂给 Agent。

## 文档地图

- [docs/README.md](docs/README.md)：文档总入口
- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)：从零启动项目
- [docs/API.md](docs/API.md)：REST 与 FastMCP 参考
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)：系统结构与数据流
- [docs/ALGORITHM_COVERAGE.md](docs/ALGORITHM_COVERAGE.md)：实现范围与近似说明
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)：开发工作流
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)：常见问题

## 当前仓库结构

```text
FateBridge/
├── api.py
├── fastmcp_server.py
├── fatebridge/
│   ├── analysis/
│   ├── core/
│   ├── data/
│   ├── services/
│   └── utils/
├── tests/
├── docs/
├── requirements.txt
├── pyproject.toml
└── CONTRIBUTING.md
```

几个关键目录的职责：

- `api.py`: FastAPI 路由、Pydantic 请求模型、HTTP 错误处理
- `fastmcp_server.py`: FastMCP 工具定义与 JSON 输出封装
- `fatebridge/core`: 核心算法、历法、占星、占术、导出合同
- `fatebridge/services`: 面向 API/MCP 的编排层与快照拼装层
- `fatebridge/analysis`: 高层分析逻辑，如配合度与时运影响
- `fatebridge/utils`: 输入归一化、真太阳时、地点解析、通用 helper
- `tests`: API/MCP 对齐、合同、回归与能力验证

## 主要能力域

| 能力域 | 代表接口 | 说明 |
| --- | --- | --- |
| 八字与命理分析 | `/api/calculate`、`/api/cn/bazi/*` | 出生信息归一化、四柱、五行、格局、喜用神 |
| 双人配合 | `/api/compatibility` | 基于两份个人分析结果做综合配合度评估 |
| 时运分析 | `/api/timing/*` | 综合时运、大运、流年、流月、流日、节气时间轴 |
| Calendar / Gua helper | `/api/cn/jieqi/year`、`/api/cn/nongli/time`、`/api/divination/gua` | 给上层应用和 Agent 的历法/义理辅助面 |
| Phase 2 本地技法 | `/api/divination/*` | 梅花、统摄法、六爻、宿占、占星骰子、三式合一 |
| 中国术数独立盘 | `/api/cn/ziwei/*`、`/api/cn/liureng/*`、`/api/cn/qimen`、`/api/cn/taiyi`、`/api/cn/jinkou` | 统一支持 `snapshot_text + snapshot_export` |
| 核心占星盘 | `/api/astro/*` | 离线星盘、派生盘、关系盘 |
| 西占推运 | `/api/astro/timing*` | 总览与独立 technique 工具 |
| 导出与知识 | `/api/export/*`、`/api/knowledge/*` | 导出协议与内置知识库 |

## 开发与验证

```bash
pytest -q
pytest tests/test_api_alignment.py -q

black --check api.py fastmcp_server.py fatebridge/utils/helpers.py fatebridge/utils/runtime.py tests
isort --check-only api.py fastmcp_server.py fatebridge/utils/helpers.py fatebridge/utils/runtime.py tests
mypy --follow-imports=silent api.py fastmcp_server.py fatebridge/utils/helpers.py fatebridge/utils/runtime.py
```

更细的开发说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 已知边界

- 本仓库不包含 in-repo Web 前端；如果要接 UI，需要自行对接 REST API 或 MCP
- 核心占星 chart 家族支持本地高精度与近似离线双路径
- 西占推运能力不是纯近似实现，缺少相关运行时依赖时会直接报错而不是静默降级
- `selected_sections` 只影响 `snapshot_export.export_text` 的裁剪，不会裁掉完整结构化 payload

## 许可证

见 [LICENSE](LICENSE)。
