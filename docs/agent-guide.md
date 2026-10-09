# FateBridge 开发者 / Agent 接入指南

这份文档写给两类调用方：想在自己的应用或脚本里集成 FateBridge 的开发者，以及把 FateBridge 当作工具集让模型自主调用的 Agent。

FateBridge 的领域能力通过三条通道暴露出来：

- REST：`python -m fatebridge.api`，默认监听 `:8010`，适合 Web、后端服务或脚本调用
- FastMCP：`python -m fatebridge.mcp_server`，供 Claude / Cursor / Codex 等 MCP host 使用
- CLI：`fatebridge <tool> ...`，适合 Agentic 流程、shell 或自动化脚本

三条通道的工具声明来自 `src/fatebridge/services/tool_catalog.py`，请求字段来自 `core/request_models.py`。共享领域计算和错误字段，各端仍有名称、绑定和校验阶段差异。

> 目前 REST 和 MCP 各暴露 80 个工具；目录共有 82 条记录，其中 CLI 可执行 81 条。`calculate_legacy` 是旧版 REST 的绑定，`astro_relative` 是嵌套 REST 请求；它们分别与 MCP 能力存在对应关系，不是所有记录都能按同名跨端调用。完整算法清单见 [algorithm-coverage.md](algorithm-coverage.md)，完整端点说明见 [api-reference.md](api-reference.md)。

---

## 自助发现：别硬编码工具列表

FateBridge 设计成可被机器自描述。Agent 不需要把本文档里的工具列表写死，启动时拉一次目录就能得到全部工具及其调用约定。

### REST：`GET /api/tools`

```bash
curl http://localhost:8010/api/tools
```

返回示例（节选）：

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

如果某个工具不在某一端暴露，`surfaces.rest_path` 或 `surfaces.mcp_name` 会返回 `null`。`parameters` 是参数摘要（名称、类型、必填、默认值、描述），不包含完整范围约束和嵌套 JSON Schema。生成可校验的函数定义时，REST 使用 `/openapi.json`，MCP 使用 `tools/list` 的 `inputSchema`。

### CLI：`list` 和 `describe`

```bash
fatebridge list                 # 列出所有工具，一行一个
fatebridge describe bazi_wealth # 输出单个工具的参数 schema、接口和示例（JSON）
```

`describe` 的输出比 REST 多一个 `cli_example` 字段，可以直接复制运行。

### FastMCP

MCP host 连接后通过标准 `tools/list` 拿到全部工具及 input schema，无需额外配置。

> 推荐做法：Agent 启动时调用一次 `/api/tools`（或 MCP `tools/list`），把工具表按 `family` 分组缓存。之后按完整 Schema 校验入参。工具增删时不必再改 Agent 代码。

---

## 公共调用约定

### 统一错误包络

业务计算错误共享顶层 `error`、`error_code`、`retryable`。REST 请求校验与 MCP 协议校验还需分别处理，CLI 错误可额外包含 `status_code`。分支判断请用 `error_code`，不要依赖 `error` 文案：

```json
{
  "error": "无效的八字分析参数",
  "error_code": "validation_error",
  "retryable": false
}
```

`error_code` 目前有以下几种：

- `validation_error`：领域参数或日期错误返回 400；REST 请求字段缺失、类型/范围错误、非法 JSON 返回 422
- `authentication_required`：缺少或无效 API key（仅在配置了密钥时），REST 返回 401
- `dependency_missing`：运行依赖缺失（例如西占 backend 不可用），REST 返回 503
- `internal_error`：服务内部异常，REST 返回 500
- `timeout`：计算超时，REST 返回 504；是否重试以 `retryable` 为准

MCP 的 schema 校验可能在执行工具前被协议层拒绝，应检查工具调用的 `isError` / 异常，再解析 JSON 文本。CLI 用退出码判定：0 成功，1 计算/模型校验失败，2 用法错误或不支持；工具结果及错误写 stdout，日志写 stderr，`list` / `--help` 返回文本。

### `run_metadata` 溯源层

成功的工具响应默认带上 `run_metadata`（错误和发现接口不保证附带；CLI 可用 `--no-metadata` 关闭）：

```json
{
  "run_metadata": {
    "run_id": "f5c3...",
    "trace_id": "5f17...",
    "tool_name": "qimen",
    "generated_at": "2026-04-13T08:00:00Z",
    "engine": "fatebridge-offline",
    "engine_is_approximate": false
  }
}
```

### 快照协议：`snapshot_text` + `snapshot_export`

很多工具返回统一的“可读文本 + 可筛选导出”双层结构：

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

- `snapshot_text` 是完整的人读文本，适合日志或直接展示。
- `snapshot_export.export_text` 是按 `selected_sections` 过滤后的导出文本。
- `selected_sections` 只裁剪导出层，不会裁掉完整的结构化 payload。
- 如果 section 名没生效，先看 `section_titles_detected` 或 `missing_selected_sections`。显式非空选择没有命中时，`export_text` 为空，不会回退全文。
- `selected_sections` 并非所有模型都支持，尤其八字九大专项没有此字段；它们仍返回快照，可用 `fields` 或 `include_snapshot_text` 控制体积。
- 梅花、中点盘与西占推运总览不返回双层快照；部分占法、事件和生命周期只有文本，详见 [快照覆盖](algorithm-coverage.md#4-快照协议覆盖)。

### 字段投影：控制 token 预算

三端都支持把响应裁剪到指定字段：

- CLI：`--fields KEY [KEY ...]`
- FastMCP：工具参数 `fields: [...]`
- REST：查询参数 `?fields=wealth_analysis&fields=analysis_type`，每个字段重复一次 `fields`

支持顶层 key（如 `wealth_analysis`）和点号子路径（如 `bazi_birth.day_master`）。已附带的 `run_metadata` 会在投影后保留；错误响应不会被裁剪。路径从响应根开始，未知路径被忽略。

REST 可用 `?include_snapshot_text=false`，MCP 用 `include_snapshot_text=false`，CLI 用 `--no-include-snapshot-text` 去掉顶层快照文本；若还保留 `snapshot_export`，其中导出文本仍存在。MCP 的 `compact=true` 为默认值，CLI 用 `--compact` 输出单行 JSON。

```bash
# 只取需要的顶层字段
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields analysis_type wealth_analysis

# 点号子路径：从大块 payload 里只抽某个标量
fatebridge bazi_birth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields snapshot_text bazi_birth.day_master
```

---

## 出生信息：一次说清

绝大多数命理 / 占星工具共享出生信息字段（详见 [api-reference.md](api-reference.md) §3）。最少需要 `birth_year/month/day/hour`，其余可选：

- `birth_year` / `birth_month` / `birth_day` / `birth_hour`：必需，出生日期与时刻
- `birth_minute`：可选，默认 0
- `gender`：八字专项可选但建议传入；`dayun_analysis` 等工具要求必填，支持 `男` / `女`、`male` / `female` 等写法
- `birth_place`：可选，中文 / 英文 / 拼音地名；内置静态近似，不是联网地理编码
- `birth_timezone`：可选，IANA 时区或 UTC offset
- `birth_longitude` / `birth_latitude`：视工具而定，占星盘建议显式传入以保证精度
- `use_true_solar_time`：中式出生信息模型默认 true，核心星盘默认 false；具体以当前工具模型为准。中式模型缺省开启但没有可解析经度时使用钟表时间并附提示；显式 true 且没有经度会报错，显式 false 使用钟表时间

真太阳时、地点解析、时区补全统一走 `fatebridge.utils.helpers`，结果会回显在 `person_info.time_adjustment`。需要高精度占星盘时，优先显式传经纬度和 IANA 时区；地点/经度推断不包含完整历史夏令时信息。小时是必填项，当前没有可省略小时的“无时盘”入口。

---

## 按通道接入

### REST（HTTP）

```bash
curl -X POST http://localhost:8010/api/cn/bazi/wealth \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace-me" \
  -d '{"gender":"男","birth_year":1990,"birth_month":5,"birth_day":15,
       "birth_hour":10,"birth_timezone":"Asia/Shanghai","birth_place":"北京","use_true_solar_time":true}'
```

如果配置了 `FATEBRIDGE_API_KEYS`，除 `/health`、`/ready`、`/metrics` 和文档页外，其余端点都需要带 `X-API-Key`。

**Python（requests）示例：** 示例客户端需先安装 `requests`，它不是 FateBridge 的直接依赖。

```python
import requests

resp = requests.post(
    "http://localhost:8010/api/cn/bazi/wealth",
    headers={"X-API-Key": "replace-me"},
    json={
        "gender": "男", "birth_year": 1990, "birth_month": 5, "birth_day": 15,
        "birth_hour": 10, "birth_timezone": "Asia/Shanghai", "birth_place": "北京",
        "use_true_solar_time": True,
    },
    timeout=30,
)
data = resp.json()
if not resp.ok or data.get("error_code"):
    raise RuntimeError(f"HTTP {resp.status_code}: {data.get('error_code', data)}")
print(data["wealth_analysis"])
```

**JavaScript（fetch）示例：**

```js
const res = await fetch("http://localhost:8010/api/cn/bazi/wealth", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": "replace-me" },
  body: JSON.stringify({
    gender: "男", birth_year: 1990, birth_month: 5, birth_day: 15,
    birth_hour: 10, birth_timezone: "Asia/Shanghai", birth_place: "北京",
    use_true_solar_time: true,
  }),
});
const data = await res.json();
if (!res.ok || data.error_code) throw new Error(`HTTP ${res.status}: ${data.error_code ?? "request_failed"}`);
console.log(data.wealth_analysis);
```

### FastMCP（Agent host）

启动：

```bash
python -m fatebridge.mcp_server
```

将 stdio 进程注册到支持 `mcpServers` 配置的 MCP host（以下是结构示例，路径需替换为实际安装目录）：

```json
{
  "mcpServers": {
    "fatebridge": {
      "command": "/absolute/path/to/FateBridge/.venv/bin/python",
      "args": ["-m", "fatebridge.mcp_server"]
    }
  }
}
```

几个注意点：

- 默认使用 stdio，由 host 启动子进程；手工启动不会创建 HTTP MCP 地址。
- 使用已安装 FateBridge 的解释器绝对路径，避免 GUI host 继承不到虚拟环境。Windows 使用 `.venv\Scripts\python.exe`。
- MCP 工具返回 JSON 字符串，通常在工具结果的 text content 中，消费时需要 parse。
- 错误同样以 JSON 字符串形式返回，也带 `error_code`。
- 用 `fields` 参数控制返回体积。

### CLI（脚本 / 自动化）

```bash
fatebridge list
fatebridge describe ziwei_birth
fatebridge ziwei_birth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male
fatebridge knowledge_read --domain bazi --category romance --key 桃花咸池
```

CLI 子命令与参数同样从中央目录派生，`--help` 可查每个工具的参数。

`--subject-file /path/to/person.json` 可复用扁平出生字段（`name`、`gender`、`birth_*` 等），显式命令参数优先。JSON 使用标准库；YAML 档案需要 PyYAML（包含在 dev 依赖中）。不要将含真实出生资料的档案直接提交仓库。

CLI 专有 `profile` 可为同一命主组织多套盘，默认 `bazi,ziwei,astro`；逐项结果在 `profile` 下，任一失败会使退出码为 1，其他结果仍返回：

```bash
fatebridge profile --systems bazi,ziwei,astro \
  --birth-year 1990 --birth-month 5 --birth-day 15 --birth-hour 10 \
  --gender 男 --birth-place 北京 --birth-timezone Asia/Shanghai \
  --birth-longitude 116.40 --birth-latitude 39.90
```

`profile` 保留各体系默认太阳时策略，不是全工具并行运行；它的选项以 `profile --help` 为准，不能直接套用所有单工具输出开关。

---

## Agent 接入建议

1. 发现：启动时拉一次 `/api/tools`（或 MCP `tools/list`），按 `family` 建立工具路由表。
2. 路由：按用户意图选 family，例如八字走 `bazi`、运势走 `timing`、星盘走 `astro`、术数走 `metaphysics` / `divination`。场景级取舍（谁主谁次、怎么省 token、怎么避免结论打架）见 [scenario-routing.md](scenario-routing.md)。
3. 取数：传齐出生信息并明确时区、坐标和太阳时策略；复现时同时固定分析日期。
4. 裁剪：用 `fields` / `--fields` 或 `selected_sections` 控制 token。
5. 判错：始终基于 `error_code` 分支；`dependency_missing` 说明环境缺西占 backend，不是入参问题。
6. 溯源：记录输入、版本、分析时点、`run_metadata` 与精度字段。`run_id` / `trace_id` 是本次生成的标识，服务不提供持久化查询或历史重放。

---

## 相关文档

- [api-reference.md](api-reference.md)：全部 REST 路由、FastMCP 工具、请求族、响应字段
- [algorithm-coverage.md](algorithm-coverage.md)：12 family / 80 工具的算法与精度 / 依赖矩阵
- [scenario-routing.md](scenario-routing.md)：场景到工具的路由矩阵、调用纪律、交叉印证与去重策略
- [getting-started.md](getting-started.md)：从零启动服务
- [troubleshooting.md](troubleshooting.md)：依赖缺失、精度、快照导出等常见问题
