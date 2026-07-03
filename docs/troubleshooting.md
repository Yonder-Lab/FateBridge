# FateBridge 故障排除

这份文档覆盖当前仓库真实存在的问题场景：Python 服务启动、REST / MCP 启动、占星依赖、快照导出与输入归一化。不假设仓库内存在前端应用。

## 安装问题

### `ModuleNotFoundError: no module named 'fatebridge'`

常见原因是：没有 cd 到仓库根目录、虚拟环境未激活、或者没有安装开发模式依赖。

按下面顺序检查：

```bash
cd /path/to/FateBridge
source venv/bin/activate
pip install -e .
python -c "import fatebridge; print(fatebridge.__file__)"
```

### `pip install -e .` 失败

先升级打包工具：

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -e .
```

如果网络较慢，可以切换镜像源，但这通常不是 FateBridge 自身逻辑问题。也可以换用 [uv](https://docs.astral.sh/uv/)，解析和下载都快很多，pip 卡住或解析超时的情况往往直接就好了：

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
```

## 启动问题

### 端口占用

如果看到类似下面的输出：

```text
Address already in use
```

当前默认端口是 `8010`，先检查谁占用了它：

```bash
lsof -i :8010
```

或者临时换端口启动：

```bash
API_PORT=8011 python -m fatebridge.api
```

### `/health` 不通

确认服务真的启动在预期端口：

```bash
python -m fatebridge.api
curl http://localhost:8010/health
```

如果你改过 `.env` 里的端口，那访问地址就不再是 `8010`。

### FastMCP 没启动成功

确认在仓库根目录直接运行：

```bash
python -m fatebridge.mcp_server
```

如果 host 侧仍然连不上，优先检查两件事：

- MCP host 是否正确注册了该进程
- Python 虚拟环境和 host 用的是不是同一套解释器

## API 输入问题

### 日期非法

典型错误：

```json
{
  "detail": "无效的输入参数，请检查日期有效性"
}
```

常见原因是传了不存在的日期，例如 `1990-02-30`，或者月份、小时超出范围。建议先在调用侧做基础校验。

### `birth_place` 没有命中预期地点

FateBridge 的地点解析是内置静态近似，不是联网地理编码。建议：

- 需要高精度时直接传 `birth_longitude`
- 同时传 `birth_timezone`
- 通过响应里的 `person_info.time_adjustment.resolved_place` 和 `resolution_level` 检查系统最终采用的地点层级

### 真太阳时结果和原时间不同

这通常不是错误，而是预期行为。开启 `use_true_solar_time=true` 后，系统会结合时区、经度和均时差对出生时刻做修正。可以检查：

- `person_info.normalized_birth_datetime`
- `person_info.time_adjustment`

## 占星与推运问题

### 核心 chart 精度不够

查看返回值：

```json
{
  "chart_profile": {
    "engine_precision": "...",
    "engine_backend": "..."
  }
}
```

如果看到的是近似模型，说明当前环境没有可用的本地高精度 ephemeris 路径。

### 显式 `hsys` 覆盖时报错

如果报错类似：

```text
当前环境缺少 swisseph，...离线模式仅能在 hsys=0(整宫制) 下运行。
```

含义是：默认 chart 仍可能可用，但显式请求更复杂的离线宫制时，当前环境缺少 `swisseph`。

解决方式二选一：

- 去掉 `hsys` 覆盖，让 chart 使用默认宫制
- 在具备 `swisseph` 的环境下运行

### 西占推运直接报依赖缺失

如果报错接近：

```text
kerykeion / Swiss Ephemeris 未安装，无法启用西占推运能力。
```

这表示：

- `astro/chart*` 族可能仍能运行
- `astro/timing*` 族不会自动降级，而是直接失败

这是 FateBridge 的设计选择，不是异常行为。

### 关系盘结果和预期的 `synastry` 不一致

FateBridge 里有一条 legacy 兼容规则：

- `relative_mode="synastry"`：现代语义，映射到 `influence`
- `relationship_mode="synastry"`：旧语义，仍按 `compare` 兼容

如果你在迁移旧调用，请显式检查自己用了哪个字段。

## 快照导出问题

### `selected_sections` 没生效

先检查响应里的这两个字段：

- `snapshot_export.section_titles_detected`
- `snapshot_export.missing_selected_sections`

最常见原因不是功能坏了，而是 section 名写错了。例如 `qimen` 常见 section 名包括：

- `起盘信息`
- `九宫方盘`
- `离九宫`

如果写成别名或旧标题，最终会被归一化或判定为缺失。

### 只想裁掉导出文本，不想丢结构化字段

这是 FateBridge 当前的既定行为：

- `selected_sections` 只作用于 `snapshot_export.export_text`
- 完整 payload 和 `snapshot_text` 仍会保留

如果你的场景需要“整体裁剪”，应在调用侧再做一层过滤。

## CORS 问题

如果浏览器报跨域错误，优先检查 `.env`：

```bash
ALLOWED_ORIGINS=http://localhost:3000
```

修改后重启 `python -m fatebridge.api`。当前 `src/fatebridge/api.py` 使用 `ALLOWED_ORIGINS` 环境变量，默认只放行 `http://localhost:3000`。

## 文档和代码不一致时怎么办

优先以代码为准，然后检查：

- `src/fatebridge/api.py`
- `src/fatebridge/mcp_server.py`
- `tests/test_api_alignment.py`
- `docs/api-reference.md`
- `docs/algorithm-coverage.md`

如果你刚修改了能力却忘了更新文档，建议至少同步改这两页：

- `docs/api-reference.md`
- `docs/algorithm-coverage.md`

## 最小诊断命令

```bash
python -m fatebridge.api
curl http://localhost:8010/health
pytest tests/test_api_alignment.py -q
```

如果只是排查主文档是否还残留旧版仓库结构或旧默认端口，可以对 `README.md`、主 `docs/*.md` 和 `.env.example` 做一次定向 `rg` 检查。
