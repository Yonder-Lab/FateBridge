# FateBridge 开发指南

这份指南写给要在本仓库里改算法、补接口或修文档的开发者。当前仓库是 backend-only 的 Python 项目，没有内置前端应用。

## 环境准备

推荐用 [uv](https://docs.astral.sh/uv/) 安装依赖：

```bash
git clone https://github.com/Yonder-Lab/FateBridge.git
cd FateBridge

uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

如果你更习惯 pip，也可以这样操作：

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

环境变量可以按需复制一份：

```bash
cp .env.example .env
```

默认配置如下：

```bash
API_HOST=0.0.0.0
API_PORT=8010
ALLOWED_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

## 项目结构概览

```text
FateBridge/
├── src/
│   └── fatebridge/         # 包代码（src layout：装包后才可 import）
│       ├── api.py          # REST (FastAPI) 入口
│       ├── mcp_server.py   # MCP (FastMCP) 入口
│       ├── cli.py          # CLI 入口
│       ├── analysis/
│       ├── core/
│       ├── data/
│       ├── services/
│       └── utils/
├── tests/
├── docs/
├── pyproject.toml
└── CONTRIBUTING.md
```

各目录的职责大致如下：

- `src/fatebridge/services/tool_catalog.py`：中央工具目录（`ToolSpec` / `CATALOG`），REST、MCP、CLI 三端共用这一份信源。
- `src/fatebridge/core/tool_spec.py`：`ToolSpec` 定义，以及 `register_rest` / `register_mcp` 注册器。
- `src/fatebridge/api.py`：从目录派生 REST 路由，处理 HTTP 层错误。
- `src/fatebridge/mcp_server.py`：从目录派生 MCP 工具，做 JSON 文本封装。
- `src/fatebridge/cli.py`：从目录派生 CLI 子命令，支持 `list` / `describe` 自助发现。
- `src/fatebridge/core`：核心算法与合同。
- `src/fatebridge/services`：面向 transport 的编排层。
- `src/fatebridge/analysis`：复合分析逻辑。
- `src/fatebridge/utils`：时间、地点、输入归一化等辅助函数。
- `tests`：回归测试、合同测试、API/MCP 对齐测试。
- `docs`：用户文档与开发者文档。

## 本地运行

启动 REST API：

```bash
python -m fatebridge.api
```

启动 FastMCP：

```bash
python -m fatebridge.mcp_server
```

健康检查：

```bash
curl http://localhost:8010/health
```

## 常用开发命令

### 测试

```bash
pytest -q
pytest tests/test_api_alignment.py -q
pytest tests/test_astrology_tools.py -q
pytest tests/test_chinese_metaphysics.py -q
```

测试需要在已安装 `.[dev]` 的 Python 3.10–3.13 环境里跑，这跟 CI 矩阵保持一致。注意不要用系统自带的解释器，否则容易出现伪失败。例如异步测试在缺少 `pytest-asyncio` 时不会真正执行，而是直接报 `FAILED`，错误信息通常是 `async def functions are not natively supported`。这类失败是环境问题，不是代码问题：先确认当前解释器里已经执行过 `pip install -e ".[dev]"`，再判断测试本身是否有错。同理，`black`、`isort`、`mypy` 也都来自 `.[dev]`，系统解释器里一般没有。

### 格式化与静态检查

```bash
black src/fatebridge/ scripts tests
isort src/fatebridge/ scripts tests
mypy src/fatebridge/
```

如果只想检查、不修改文件：

```bash
black --check src/fatebridge/ scripts tests
isort --check-only src/fatebridge/ scripts tests
mypy src/fatebridge/
```

## 推荐开发流程

### 新增或修改一个领域能力

建议按这个顺序来：

1. 先改 `src/fatebridge/core/*` 或 `src/fatebridge/analysis/*`。
2. 在 `src/fatebridge/services/*` 封装成对 transport 友好的返回结构。
3. 在 `src/fatebridge/core/request_models.py` 定义工具的 Pydantic 请求模型。
4. 在 `src/fatebridge/services/tool_catalog.py` 的 `CATALOG` 追加一个 `ToolSpec`。REST、MCP、CLI 三端会自动派生，不需要再改 `api.py`、`mcp_server.py` 或 `cli.py`。
5. 在 `tests/` 增加能力测试。三端 parity 由 `tests/test_full_surface_validation.py` 自动覆盖，记得为新工具补一个代表性的 payload fixture。
6. 更新 `docs/api-reference.md` 与 `docs/algorithm-coverage.md`。工具计数由 `tests/test_doc_tool_counts.py` 锁定。

### 只改 transport 行为，不改算法

如果只是调整某一端的绑定（例如自定义 REST 绑定、CLI 不支持嵌套模型时的降级提示），改动应集中在 `src/fatebridge/core/tool_spec.py` 的注册器，或 `tool_catalog.py` 的命名绑定处，并补充：

- request model 验证用例；
- `tests/test_full_surface_validation.py` 覆盖的三端 parity。

这样可以避免三端接入层继续漂移。

## 设计约束

### 输入归一化不要分散实现

涉及出生时间、地点、时区、真太阳时修正时，优先复用：

- `create_person_info`
- `normalize_birth_time`
- `resolve_birth_place_context`

不要在具体 endpoint 或 tool 里复制这些逻辑。

### 快照能力尽量复用统一合同

如果新增的工具需要“可读文本 + 可筛选 section”，优先复用：

- `snapshot_text`
- `snapshot_export`
- `parse_export_content`

不要自己发明另一套 section 过滤格式。

### 三端应共享 service 层与中央目录

新增能力时，不要把领域逻辑直接写进 `src/fatebridge/api.py`、`src/fatebridge/mcp_server.py` 或 `src/fatebridge/cli.py`。这三处只是从 `tool_catalog.py` 派生的 adapter，业务实现应留在 `services` / `core`，工具声明应留在 `CATALOG`。

## 测试策略

### 什么时候补 API/MCP 对齐测试

满足以下任一条件时建议补：

- 同时暴露 REST 与 MCP；
- 修改了请求字段默认值；
- 修改了响应结构；
- 修改了 `selected_sections`、`snapshot_export` 或 section 名映射。

### 什么时候补能力回归测试

满足以下任一条件时建议补：

- 改动了 `src/fatebridge/core/*`；
- 改动了算法边界条件；
- 改动了占星精度回退逻辑；
- 改动了导出合同或知识索引。

## 文档改动的最低同步面

如果你改了接口或能力范围，至少同步更新：

- `README.md`
- `docs/api-reference.md`
- `docs/algorithm-coverage.md`

如果改了结构性设计，再补 `docs/architecture.md`。

## 依赖与运行时注意事项

### 核心占星盘

- 可以在缺少 `swisseph` 时继续运行；
- 但会回退到近似轨道模型；
- 某些 `hsys` 覆盖值依赖 `swisseph`。

### 西占推运

- 依赖 `kerykeion` / Swiss Ephemeris；
- 缺少依赖时不会自动降级。

这两类能力的差异在文档和代码里都要保持清晰，不要把“可运行”写成“等精度”。

## 提交前检查清单

提交前建议自查：

1. `pytest -q` 至少跑过相关子集。
2. `black --check` / `isort --check-only` / `mypy` 通过。
3. 新工具是否已在 `tool_catalog.py` 的 `CATALOG` 中声明（三端由此派生），并补了 `test_full_surface_validation.py` 的代表性 payload。
4. 文档是否更新了端口、能力名、section 名；若工具计数变化，`tests/test_doc_tool_counts.py` 是否仍通过。
5. 是否错误地把近似实现写成了高精度实现。

## 常用入口

- 交互接口文档：`http://localhost:8010/docs`
- 架构说明：[architecture.md](architecture.md)
- API 参考：[api-reference.md](api-reference.md)
- 故障排除：[troubleshooting.md](troubleshooting.md)
