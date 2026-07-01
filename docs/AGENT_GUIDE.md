# FateBridge 开发者 / Agent 接入指南

本指南面向两类调用方：

- **开发者**：用 HTTP / SDK / CLI 把 FateBridge 接进自己的应用或脚本
- **Agent**：把 FateBridge 当作一组工具（tool / function）由模型自主调用

FateBridge 的同一套领域能力通过三条通道暴露，全部从中央目录 `src/fatebridge/services/tool_catalog.py` 自动派生，因此**工具集合、参数 schema、错误形状三端一致**：

| 通道 | 入口 | 适合 |
| --- | --- | --- |
| REST | `python -m fatebridge.api`（默认 `:8010`） | Web / 后端服务 / 脚本 |
| FastMCP | `python -m fatebridge.mcp_server` | Claude / Cursor / Codex 等 MCP host |
| CLI | `fatebridge <tool> ...` | Agentic / shell / 自动化脚本 |

> 当前共 80 个工具同时暴露在 REST 与 MCP；CLI 另含少量别名（如 `calculate_legacy`），故 `/api/tools` 的 `counts.total` 略大于 80。完整算法清单见 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)，完整端点见 [API.md](API.md)。

---

## 1. 自助发现：不要硬编码工具列表

FateBridge 的核心设计是**机读自描述**——Agent 无需抓取本文档即可枚举全部工具及其调用约定。三端都提供发现入口：

### 1.1 REST：`GET /api/tools`

```bash
curl http://localhost:8010/api/tools
```

返回：

```json
{
  "counts": {"rest": 80, "mcp": 80, "total": 82},
  "tools": [
    {
      "tool": "bazi_wealth",
      "summary": "八字财运分析（可传 dayun_pillar / liunian_pillar 输出时机信号）",
      "operation_label_zh": "八字财运分析",
      "family": "bazi",
      "surfaces": {"cli": true, "rest_path": "/api/cn/bazi/wealth", "mcp_name": "bazi_wealth"},
      "parameters": [
        {"name": "birth_year", "type": "int", "required": true, "description": "..."}
      ]
    }
  ]
}
```

- `surfaces.rest_path` / `surfaces.mcp_name` 为 `null` 表示该工具不在对应端暴露
- `parameters` 即该工具的参数 schema，可直接转成你框架的 tool/function 定义

### 1.2 CLI：`list` / `describe`

```bash
fatebridge list                  # 列出所有工具（一行一个）
fatebridge describe bazi_wealth   # 输出单个工具的参数 schema / 接口 / 示例（JSON）
```

`describe` 的输出比 REST 多一个 `cli_example` 字段，可直接拷贝运行。

### 1.3 FastMCP

MCP host 连接后会通过标准 `tools/list` 拿到全部工具及其 input schema，无需额外配置。

> **推荐模式**：Agent 启动时调用一次 `/api/tools`（或 MCP `tools/list`）缓存工具表，按 `family` 分组路由，按 `parameters` 校验入参——这样工具增删时无需改 Agent 代码。

---

## 2. 公共调用约定（三端一致）

### 2.1 统一错误包络

REST / FastMCP / CLI 三端返回**扁平的顶层错误包络**，字段一致。请基于 `error_code` 而非 `error` 文案分支：

```json
{
  "error": "无效的八字分析参数",
  "error_code": "validation_error",
  "retryable": false
}
```

| `error_code` | 含义 | REST 状态码 |
| --- | --- | --- |
| `validation_error` | 入参错误 / 日期非法 | 400 |
| `authentication_required` | 缺少或无效 API key（仅配置了密钥时） | 401 |
| `dependency_missing` | 运行依赖缺失（如西占 backend 不可用） | 503 |
| `internal_error` | 服务内部异常 | 500 |

### 2.2 `run_metadata`（溯源层）

结构化工具响应统一带 `run_metadata`：

```json
{
  "run_metadata": {
    "run_id": "f5c3...",
    "trace_id": "5f17...",
    "tool_name": "qimen",
    "generated_at": "2026-04-13T08:00:00Z",
    "engine": "fatebridge-offline"
  }
}
```

### 2.3 快照协议（`snapshot_text` + `snapshot_export`）

大量工具返回统一的“可读文本 + 可筛选导出”双层结构：

```json
{
  "snapshot_text": "[起盘信息]\n...",
  "snapshot_export": {
    "technique": {"key": "qimen"},
    "selected_sections": ["起盘信息", "九宫方盘"],
    "section_titles_detected": ["起盘信息", "九宫方盘", "离九宫"],
    "export_text": "[起盘信息]\n..."
  }
}
```

- `snapshot_text`：完整人读文本，适合日志或直接展示
- `snapshot_export.export_text`：按 `selected_sections` 过滤后的导出文本
- `selected_sections` **只裁剪导出层**，不会裁掉完整结构化 payload
- section 名不生效时，先看 `section_titles_detected` / `missing_selected_sections`

### 2.4 字段投影（token 预算控制）

把响应裁剪到指定字段，便于 Agent 按 token 预算取数：

| 端 | 用法 |
| --- | --- |
| CLI | `--fields KEY [KEY ...]` |
| FastMCP | 工具参数 `fields: [...]` |
| REST | 在调用侧自行裁剪（REST 不内置 `fields`） |

支持**顶层 key**（如 `wealth_analysis`）与**点号子路径**（如 `bazi_birth.day_master`）。`run_metadata` 始终保留以维持溯源；错误响应不会被裁剪。

```bash
# 只取需要的顶层字段
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields analysis_type wealth_analysis

# 点号子路径：从大块 payload 里只抽某个标量
fatebridge bazi_birth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields snapshot_text bazi_birth.day_master
```

---

## 3. 出生信息：一次说清

绝大多数命理/占星工具共享出生信息字段（详见 [API.md](API.md) §3）。最少需要 `birth_year/month/day/hour`，其余可选：

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `birth_year` / `birth_month` / `birth_day` / `birth_hour` | 是 | 出生日期与时刻 |
| `birth_minute` | 否 | 默认 0 |
| `gender` | 否（八字专项建议传） | `男` / `女` |
| `birth_place` | 否 | 中文/英文/拼音地名；内置静态近似，非联网地理编码 |
| `birth_timezone` | 否 | IANA 时区或 UTC offset |
| `birth_longitude` / `birth_latitude` | 视工具 | 占星盘建议显式传以保证精度 |
| `use_true_solar_time` | 否 | 真太阳时修正（含经度 + 均时差） |

> 真太阳时、地点解析、时区补全统一走 `fatebridge.utils.helpers`，结果回显在 `person_info.time_adjustment`。要高精度占星盘时优先显式传经纬度，而不是依赖 `birth_place` 推断。

---

## 4. 按通道接入

### 4.1 REST（HTTP）

```bash
curl -X POST http://localhost:8010/api/cn/bazi/wealth \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace-me" \
  -d '{"gender":"男","birth_year":1990,"birth_month":5,"birth_day":15,
       "birth_hour":10,"birth_timezone":"Asia/Shanghai","use_true_solar_time":true}'
```

配置了 `FATEBRIDGE_API_KEYS` 时，除 `/health`、`/ready`、`/metrics` 与文档页外都需带 `X-API-Key`。

**Python（requests）：**

```python
import requests

resp = requests.post(
    "http://localhost:8010/api/cn/bazi/wealth",
    headers={"X-API-Key": "replace-me"},
    json={
        "gender": "男", "birth_year": 1990, "birth_month": 5, "birth_day": 15,
        "birth_hour": 10, "birth_timezone": "Asia/Shanghai", "use_true_solar_time": True,
    },
    timeout=30,
)
resp.raise_for_status()
data = resp.json()
if data.get("error_code"):
    raise RuntimeError(data["error_code"])
print(data["wealth_analysis"])
```

**JavaScript（fetch）：**

```js
const res = await fetch("http://localhost:8010/api/cn/bazi/wealth", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": "replace-me" },
  body: JSON.stringify({
    gender: "男", birth_year: 1990, birth_month: 5, birth_day: 15,
    birth_hour: 10, birth_timezone: "Asia/Shanghai", use_true_solar_time: true,
  }),
});
const data = await res.json();
if (data.error_code) throw new Error(data.error_code);
console.log(data.wealth_analysis);
```

### 4.2 FastMCP（Agent host）

启动：

```bash
python -m fatebridge.mcp_server
```

注册到 MCP host（以 Claude Code / Claude Desktop 为例）：

```json
{
  "mcpServers": {
    "fatebridge": {
      "command": "python",
      "args": ["-m", "fatebridge.mcp_server"]
    }
  }
}
```

要点：

- MCP 工具多数返回 **JSON 字符串**（而非原生对象），消费时记得 parse
- 错误以工具字符串里的错误 JSON 形式返回，同样带 `error_code`
- 用 `fields` 参数控制返回体积

### 4.3 CLI（脚本 / 自动化）

```bash
fatebridge list
fatebridge describe ziwei_birth
fatebridge ziwei_birth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male
fatebridge knowledge_read --domain bazi --category romance --key 桃花咸池
```

CLI 子命令与参数同样从中央目录派生，`--help` 可查每个工具的参数。

---

## 5. Agent 接入清单（建议）

1. **发现**：启动时拉一次 `/api/tools`（或 MCP `tools/list`），按 `family` 建立工具路由表
2. **路由**：按用户意图选 family（八字→`bazi`，运势→`timing`，星盘→`astro`，术数→`metaphysics`/`divination`）

> 场景级取舍（谁主谁次、怎么省 token、怎么不自相矛盾）见 [SCENARIO_ROUTING.md](SCENARIO_ROUTING.md)。

3. **取数**：传齐出生信息；需要真太阳时就显式 `use_true_solar_time=true`
4. **裁剪**：用 `fields` / `--fields` 或 `selected_sections` 控制 token
5. **判错**：永远基于 `error_code` 分支；`dependency_missing` 说明环境缺西占 backend，而非入参问题
6. **溯源**：把 `run_metadata.run_id` / `trace_id` 记进日志，便于复现

---

## 6. 相关文档

- [API.md](API.md)：全部 REST 路由、FastMCP 工具、请求族、响应字段
- [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)：13 family / 80 工具的算法与精度/依赖矩阵
- [SCENARIO_ROUTING.md](SCENARIO_ROUTING.md)：场景→工具路由矩阵、调用纪律、交叉印证与去重策略
- [GETTING_STARTED.md](GETTING_STARTED.md)：从零启动服务
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)：依赖缺失、精度、快照导出等常见问题
