# FateBridge 开发指南

本指南面向准备在当前仓库里修改算法、补接口或修文档的开发者。当前仓库是 backend-only Python 项目，不包含内置前端应用。

## 1. 环境准备

推荐用 [uv](https://docs.astral.sh/uv/)：

```bash
git clone https://github.com/thomas-yanxin/FateBridge.git
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

### 关键目录职责

| 路径 | 职责 |
| --- | --- |
| `api.py` | REST 路由、Pydantic request model、HTTP 层错误处理 |
| `fastmcp_server.py` | MCP 工具定义与 JSON 文本封装 |
| `fatebridge/core` | 核心算法与合同 |
| `fatebridge/services` | transport-facing 编排层 |
| `fatebridge/analysis` | 复合分析逻辑 |
| `fatebridge/utils` | 时间、地点、输入归一化 |
| `tests` | 回归、合同、API/MCP 对齐 |
| `docs` | 用户与开发者文档 |

## 3. 本地运行

### 启动 REST API

```bash
python api.py
```

### 启动 FastMCP

```bash
python fastmcp_server.py
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

### 格式化与静态检查

```bash
black fatebridge/ api.py fastmcp_server.py
isort fatebridge/ api.py fastmcp_server.py
mypy fatebridge/ api.py
```

### 只做检查、不改文件

```bash
black --check fatebridge/ api.py fastmcp_server.py
isort --check-only fatebridge/ api.py fastmcp_server.py
mypy fatebridge/ api.py
```

## 5. 推荐开发流程

### 新增或修改一个领域能力

建议顺序：

1. 先改 `fatebridge/core/*` 或 `fatebridge/analysis/*`
2. 在 `fatebridge/services/*` 封装 transport 友好的返回结构
3. 在 `api.py` 暴露 REST 路由
4. 在 `fastmcp_server.py` 暴露 MCP 工具
5. 在 `tests/` 增加能力测试与 API/MCP 对齐测试
6. 更新 `docs/API.md` 与 `docs/ALGORITHM_COVERAGE.md`

### 只改 transport，不改算法

如果只是补入口或修参数对齐，也建议补：

- request model 验证用例
- API/MCP parity test

这样可以防止两套接入层继续漂移。

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

### 6.3 REST 和 MCP 应共享 service 层

新增能力时，尽量不要把领域逻辑直接写进 `api.py` 或 `fastmcp_server.py`。这两处应尽量保持为 adapter，而不是业务实现层。

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
3. REST 与 MCP 新增入口是否都补齐
4. 文档是否更新了端口、能力名、section 名
5. 是否错误地把近似实现写成了高精度实现

## 11. 常用入口

- 交互接口文档：`http://localhost:8010/docs`
- 架构说明：[ARCHITECTURE.md](ARCHITECTURE.md)
- API 参考：[API.md](API.md)
- 故障排除：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)
