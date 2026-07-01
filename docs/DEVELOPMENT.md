# FateBridge 开发指南

本指南面向准备在当前仓库里修改算法、补接口或修文档的开发者。当前仓库是 backend-only Python 项目，不包含内置前端应用。

## 1. 环境准备

推荐用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/Yonder-Lab/FateBridge.git
cd FateBridge

uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

或者用 pip：

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

可选环境变量：

```bash
cp .env.example .env
```

默认值：

```bash
API_HOST=0.0.0.0
API_PORT=8010
ALLOWED_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

## 2. 当前项目结构

```text
FateBridge/
├── fatebridge/
│   ├── api.py          # REST (FastAPI) 入口
│   ├── mcp_server.py   # MCP (FastMCP) 入口
│   ├── cli.py          # CLI 入口
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

### 关键目录职责

| 路径 | 职责 |
| --- | --- |
| `fatebridge/services/tool_catalog.py` | 中央工具目录（`ToolSpec` / `CATALOG`），REST/MCP/CLI 三端唯一信源 |
| `fatebridge/core/tool_spec.py` | `ToolSpec` 定义与 `register_rest` / `register_mcp` 注册器 |
| `fatebridge/api.py` | 从目录派生 REST 路由、HTTP 层错误处理 |
| `fatebridge/mcp_server.py` | 从目录派生 MCP 工具、JSON 文本封装 |
| `fatebridge/cli.py` | 从目录派生 CLI 子命令、`list` / `describe` 自助发现 |
| `fatebridge/core` | 核心算法与合同 |
| `fatebridge/services` | transport-facing 编排层 |
| `fatebridge/analysis` | 复合分析逻辑 |
| `fatebridge/utils` | 时间、地点、输入归一化 |
| `tests` | 回归、合同、API/MCP 对齐 |
| `docs` | 用户与开发者文档 |

## 3. 本地运行

### 启动 REST API

```bash
python -m fatebridge.api
```

### 启动 FastMCP

```bash
python -m fatebridge.mcp_server
```

### 健康检查

```bash
curl http://localhost:8010/health
```

## 4. 常用开发命令

### 测试

```bash
pytest -q
pytest tests/test_api_alignment.py -q
pytest tests/test_astrology_tools.py -q
pytest tests/test_chinese_metaphysics.py -q
```

> [!IMPORTANT]
> **测试必须在装了 `.[dev]` 的 Python 3.10–3.13 环境里跑**（对齐 CI 矩阵），别用系统自带的解释器。少了 dev 依赖会出**伪失败**——例如异步测试在缺 `pytest-asyncio` 时不会执行，而是直接被报成 `FAILED`，报错写着 `async def functions are not natively supported`。这类失败是环境问题，不是代码缺陷：先确认 `pip install -e ".[dev]"` 装在当前解释器里，再判断测试本身。同理 `black`/`isort`/`mypy` 也都来自 `.[dev]`，系统解释器里没有。

### 格式化与静态检查

```bash
black fatebridge/ scripts tests
isort fatebridge/ scripts tests
mypy fatebridge/
```

### 只做检查、不改文件

```bash
black --check fatebridge/ scripts tests
isort --check-only fatebridge/ scripts tests
mypy fatebridge/
```

## 5. 推荐开发流程

### 新增或修改一个领域能力

建议顺序：

1. 先改 `fatebridge/core/*` 或 `fatebridge/analysis/*`
2. 在 `fatebridge/services/*` 封装 transport 友好的返回结构
3. 在 `fatebridge/core/request_models.py` 定义工具的 Pydantic 请求模型
4. **在 `fatebridge/services/tool_catalog.py` 的 `CATALOG` 追加一个 `ToolSpec`** —— REST / MCP / CLI 三端自动派生，无需改动 `api.py` / `mcp_server.py` / `cli.py`
5. 在 `tests/` 增加能力测试；三端 parity 由 `tests/test_full_surface_validation.py` 自动覆盖，记得为新工具补一个代表性 payload fixture
6. 更新 `docs/API.md` 与 `docs/ALGORITHM_COVERAGE.md`（工具计数由 `tests/test_doc_tool_counts.py` 锁定）

### 只改 transport 行为，不改算法

如果只是调整某端的绑定（如自定义 REST 绑定、CLI 不支持嵌套模型时的降级提示），改动应集中在 `fatebridge/core/tool_spec.py` 的注册器或 `tool_catalog.py` 的命名绑定处，并补：

- request model 验证用例
- `tests/test_full_surface_validation.py` 覆盖的三端 parity

这样可以防止三端接入层继续漂移。

## 6. 设计约束

### 6.1 输入归一化不要分散实现

涉及出生时间、地点、时区、真太阳时修正时，优先复用：

- `create_person_info`
- `normalize_birth_time`
- `resolve_birth_place_context`

不要在具体 endpoint 或 tool 里复制逻辑。

### 6.2 快照能力尽量复用统一合同

如果新增的工具需要“可读文本 + 可筛选 section”，优先复用：

- `snapshot_text`
- `snapshot_export`
- `parse_export_content`

不要自己发明另一套 section 过滤格式。

### 6.3 三端应共享 service 层与中央目录

新增能力时，不要把领域逻辑直接写进 `fatebridge/api.py`、`fatebridge/mcp_server.py` 或 `fatebridge/cli.py`。这三处都只是从 `tool_catalog.py` 派生的 adapter，业务实现应留在 `services` / `core`，工具声明应留在 `CATALOG`。

## 7. 测试策略

### 7.1 什么时候补 API/MCP 对齐测试

满足任一条件时建议补：

- 同时暴露 REST 与 MCP
- 修改了请求字段默认值
- 修改了响应结构
- 修改了 `selected_sections`、`snapshot_export`、section 名映射

### 7.2 什么时候补能力回归测试

满足任一条件时建议补：

- 改动了 `fatebridge/core/*`
- 改动了算法边界条件
- 改动了占星精度回退逻辑
- 改动了导出合同或知识索引

## 8. 文档改动的最低同步面

如果你改了接口或能力范围，至少同步更新：

- `README.md`
- `docs/API.md`
- `docs/ALGORITHM_COVERAGE.md`

如果改了结构性设计，再补：

- `docs/ARCHITECTURE.md`

## 9. 依赖与运行时注意事项

### 核心占星盘

- 可以在缺少 `swisseph` 时继续运行
- 但会回退到近似轨道模型
- 某些 `hsys` 覆盖值依赖 `swisseph`

### 西占推运

- 依赖 `kerykeion` / Swiss Ephemeris
- 缺少依赖时不会自动降级

这两类能力的差异在文档和代码里都要保持清晰，不要把“可运行”写成“等精度”。

## 10. 提交前检查清单

提交前建议自查：

1. `pytest -q` 至少跑过相关子集
2. `black --check` / `isort --check-only` / `mypy` 通过
3. 新工具是否已在 `tool_catalog.py` 的 `CATALOG` 声明（三端由此派生），并补了 `test_full_surface_validation.py` 的代表性 payload
4. 文档是否更新了端口、能力名、section 名；若工具计数变化，`tests/test_doc_tool_counts.py` 是否仍通过
5. 是否错误地把近似实现写成了高精度实现

## 11. 常用入口

- 交互接口文档：`http://localhost:8010/docs`
- 架构说明：[ARCHITECTURE.md](ARCHITECTURE.md)
- API 参考：[API.md](API.md)
- 故障排除：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)
