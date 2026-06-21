# FateBridge API 参考

本文档按“能力域”描述 FateBridge 当前对外接口，而不是按历史模块拆散说明。当前仓库同时提供：

- REST API：FastAPI，默认 `http://localhost:8010`
- FastMCP：`python -m fatebridge.mcp_server` 启动的 MCP 工具面

> 当前实际暴露 78 个业务 REST 路由（另含 `/health`、`/ready`、`/metrics` 三个运维端点）和 78 个 FastMCP 工具。两个数字由中央目录派生，并由 `tests/test_doc_tool_counts.py` 锁定。

## 1. 基础信息

### REST

- 基础地址：`http://localhost:8010`
- Swagger UI：`/docs`
- ReDoc：`/redoc`
- Content-Type：`application/json`

### FastMCP

- 启动命令：`python -m fatebridge.mcp_server`
- 返回格式：多数工具返回 JSON 字符串，而不是原生 Python dict
- 设计目标：让 Agent 宿主可以直接把 FateBridge 视作工具箱使用

## 2. 公共约定

### 2.1 错误格式

REST 端通常返回：

```json
{
  "detail": "无效的输入参数，请检查日期有效性"
}
```

常见状态码：

- `400`：输入参数错误、日期无效、能力依赖缺失
- `500`：服务内部异常

### 2.2 快照协议

很多工具返回下面两层快照字段：

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

要点：

- `run_metadata` 是统一的 transport 元数据层
- `run_id` / `trace_id` 是本次响应生成的轻量标识
- `tool_name` 对应当前 REST 入口或 MCP 工具入口
- `generated_at` 是 UTC ISO 8601 时间戳
- `engine` 是从当前 payload 推导出的运行引擎标识
- `snapshot_text` 是完整的人类可读文本
- `snapshot_export.export_text` 是根据 `selected_sections` 过滤后的导出文本
- `selected_sections` 只裁剪导出层，不会裁掉完整结构化 payload

### 2.3 `selected_sections`

下列能力族通常支持 `selected_sections`：

- 八字独立盘
- 时运独立工具
- knowledge/export helper
- 卦义 helper
- 多数中国术数独立盘
- 占星独立 chart / timing tools

排查 section 名不生效时，优先看：

- `snapshot_export.section_titles_detected`
- `snapshot_export.missing_selected_sections`

### 2.4 精度与依赖

- 核心占星盘优先使用本地 `swisseph`，缺失时会回退到 FateBridge 内置近似模型
- 西占推运不走近似回退；缺少 `kerykeion` / Swiss Ephemeris 时会直接报错
- 完整说明见 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)

## 3. 共享请求族

### 3.1 `FateBridgeRequest` 家族

用于：

- `/api/calculate`
- `/api/cn/bazi/*`
- `/api/timing/*`

| 字段 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 否 | 默认 `未提供` |
| `gender` | string | 否 | 默认 `未知` |
| `birth_year` | int | 是 | 出生年 |
| `birth_month` | int | 是 | `1..12` |
| `birth_day` | int | 是 | `1..31`，还需满足真实日期 |
| `birth_hour` | int | 是 | `0..23` |
| `birth_minute` | int | 否 | 默认 `0` |
| `birth_place` | string | 否 | 支持中文、英文、拼音地点文本 |
| `birth_timezone` | string | 否 | IANA 时区或 UTC offset |
| `birth_longitude` | float | 否 | `-180..180` |
| `use_true_solar_time` | bool | 否 | 是否启用真太阳时修正 |

### 3.2 `AstroChartRequest` 家族

用于：

- `/api/astro/chart`
- `/api/astro/chart13`
- `/api/astro/hellen`
- `/api/astro/guolao`
- `/api/astro/india`
- `/api/astro/germany`

| 字段 | 类型 | 必需 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 否 | 默认 `未提供` |
| `birth_year` / `birth_month` / `birth_day` / `birth_hour` | int | 是 | 出生日期与时刻 |
| `birth_minute` | int | 否 | 默认 `0` |
| `birth_timezone` | string | 否 | 默认 `UTC` |
| `birth_longitude` | float | 条件必需 | 某些情况下可由 `birth_place` 推断 |
| `birth_latitude` | float | 条件必需 | 某些情况下可由 `birth_place` 推断 |
| `birth_place` | string | 否 | 支持有限内置地点推断 |
| `hsys` | int | 否 | 离线宫制覆盖；当前支持 `0..8` |
| `zodiacal` | int | 否 | `0=tropical`，`1=sidereal(Lahiri-like)` |

### 3.3 `WesternTimingRequest` 家族

用于：

- `/api/astro/timing`
- `/api/astro/timing/*`

除出生信息外，还支持：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `analysis_year` / `analysis_month` / `analysis_day` | int | 目标分析日期 |
| `return_longitude` / `return_latitude` / `return_timezone` | mixed | 返照或行运地点 |
| `house_system` | string | 例如 `P` 表示 Placidus |
| `zodiac_type` | string | 例如 `Tropic` |
| `pd_method` | string | 主限方法 |
| `pd_time_key` | string | 例如 `Ptolemy` / `Naibod` |
| `pd_type` | int | `0=direct`，`1=converse` |
| `pd_aspects` | int[] | 主限相位列表 |
| `show_pd_bounds` | bool | 主限图盘是否带界限层 |
| `selected_sections` | string[] | 仅独立 timing tools 支持 |

### 3.4 Phase 2 / metaphysics 本地请求约定

`sixyao`、`suzhan`、`otherbu`、`sanshiunited` 等大量本地技法接口共享如下约定：

| 字段 | 说明 |
| --- | --- |
| `date` / `time` | 输入时刻，例如 `2028-04-06` / `09:33:00` |
| `zone` | 时区，常见默认 `+08:00` |
| `lat` / `lon` | 文本化地理提示 |
| `gpsLat` / `gpsLon` | 浮点 GPS 坐标 |
| `selected_sections` | 快照导出裁剪 |

## 4. REST 端点家族

### 4.1 基础命理与配合

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/calculate` | 单人命理分析 |
| `POST` | `/api/cn/bazi/birth` | 独立八字命盘 |
| `POST` | `/api/compatibility` | 双人配合分析 |

### 4.2 时运分析

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/timing/comprehensive` | 综合时运 |
| `POST` | `/api/timing/dayun` | 大运 |
| `POST` | `/api/timing/liunian` | 流年 |
| `POST` | `/api/timing/liuyue` | 流月 |
| `POST` | `/api/timing/liuri` | 流日 |
| `POST` | `/api/timing/liushi` | 流时 |
| `POST` | `/api/timing/jieqi` | 全年节气节点时间轴 |

### 4.3 Calendar / knowledge / export helper

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/cn/jieqi/year` | 全年节气 helper |
| `POST` | `/api/cn/nongli/time` | 农历换算 helper |
| `POST` | `/api/divination/gua` | 卦义检索 |
| `POST` | `/api/cn/gua/meiyi` | 梅易卦义批量查询 |
| `POST` | `/api/export/registry` | 导出合同注册表 |
| `POST` | `/api/export/parse` | 快照文本解析 |
| `POST` | `/api/knowledge/registry` | 内置知识目录 |
| `POST` | `/api/knowledge/read` | 内置知识条目读取 |

### 4.4 Divination 与本地技法

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/divination/meihua` | 梅花易数时卦 |
| `POST` | `/api/divination/tongshefa` | 统摄法 |
| `POST` | `/api/divination/sixyao` | 六爻 |
| `POST` | `/api/divination/canping` | 邵子参评数 / 金锁银匙 |
| `POST` | `/api/divination/heluo` | 河洛理数 |
| `POST` | `/api/divination/suzhan` | 宿占 |
| `POST` | `/api/divination/otherbu` | 占星骰子 / otherbu |
| `POST` | `/api/divination/sanshiunited` | 三式合一 |

### 4.5 中国术数独立盘

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/cn/ziwei/birth` | 紫微斗数命盘 |
| `POST` | `/api/cn/ziwei/rules` | 紫微规则库 |
| `POST` | `/api/cn/liureng/gods` | 六壬起课 |
| `POST` | `/api/cn/liureng/runyear` | 六壬行年 |
| `POST` | `/api/cn/qimen` | 奇门遁甲 |
| `POST` | `/api/cn/taiyi` | 太乙神数 |
| `POST` | `/api/cn/jinkou` | 金口诀 |

### 4.6 核心占星盘

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/astro/chart` | 标准盘 |
| `POST` | `/api/astro/chart13` | 13 扇区扩展盘 |
| `POST` | `/api/astro/hellen` | 希腊风格盘 |
| `POST` | `/api/astro/guolao` | 果老 / 七政四余风格盘 |
| `POST` | `/api/astro/india` | 印度 sidereal 盘 |
| `POST` | `/api/astro/germany` | 中点 / germany 派生盘 |
| `POST` | `/api/astro/relative` | 关系盘 |

### 4.7 西占推运

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/api/astro/timing` | 推运总览 bundle |
| `POST` | `/api/astro/timing/solarreturn` | 太阳返照 |
| `POST` | `/api/astro/timing/lunarreturn` | 月返 |
| `POST` | `/api/astro/timing/transit` | 行运 |
| `POST` | `/api/astro/timing/solararc` | 太阳弧 |
| `POST` | `/api/astro/timing/givenyear` | 指定年盘 |
| `POST` | `/api/astro/timing/profection` | 年小限 |
| `POST` | `/api/astro/timing/pd` | 主限 |
| `POST` | `/api/astro/timing/pdchart` | 主限图盘 |
| `POST` | `/api/astro/timing/zr` | 黄道释放 |
| `POST` | `/api/astro/timing/firdaria` | 法达 |
| `POST` | `/api/astro/timing/decennials` | 十年星限 |

### 4.8 健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | 服务健康检查 |

## 5. Representative REST 示例

### 5.1 单人命理分析

```bash
curl -X POST http://localhost:8010/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "birth_place": "北京",
    "use_true_solar_time": true
  }'
```

返回重点：

- `person_info.time_adjustment`
- `four_pillars`
- `day_master`
- `structure_profile`
- `patterns`
- `calendar_context`

说明：

- `structure_profile` 会给出 `dominant_structure`、`secondary_structures`、`useful_elements`、`avoid_elements`、`useful_ten_gods` 和 `harmony_effects`
- `patterns.special` 现在同时包含 `recognized_structures` 与 `metadata`，便于区分“已识别格局”与“辅助元数据”

### 5.2 核心占星盘

```bash
curl -X POST http://localhost:8010/api/astro/chart \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chart Demo",
    "birth_year": 1990,
    "birth_month": 4,
    "birth_day": 6,
    "birth_hour": 9,
    "birth_minute": 33,
    "birth_timezone": "Asia/Shanghai",
    "birth_longitude": 121.4667,
    "birth_latitude": 31.2167,
    "birth_place": "上海"
  }'
```

返回重点：

- `chart_profile.engine_precision`
- `angles`
- `houses`
- `planets`
- `aspects`
- `snapshot_text`
- `snapshot_export`

### 5.3 独立西占 technique

```bash
curl -X POST http://localhost:8010/api/astro/timing/solarreturn \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SR Demo",
    "birth_year": 1990,
    "birth_month": 4,
    "birth_day": 6,
    "birth_hour": 9,
    "birth_minute": 33,
    "birth_timezone": "Asia/Shanghai",
    "birth_longitude": 121.4667,
    "birth_latitude": 31.2167,
    "birth_place": "上海",
    "analysis_year": 2028,
    "analysis_month": 4,
    "analysis_day": 6,
    "selected_sections": ["起盘信息", "星盘信息"]
  }'
```

返回重点：

- `snapshot_text`
- `snapshot_export.selected_sections`
- `snapshot_export.export_text`

### 5.4 导出解析 helper

```bash
curl -X POST http://localhost:8010/api/export/parse \
  -H "Content-Type: application/json" \
  -d '{
    "technique": "qimen",
    "content": "[起盘信息]\n示例\n\n[九宫方盘]\n示例",
    "selected_sections": ["起盘信息"]
  }'
```

## 6. FastMCP 工具面

### 6.1 启动

```bash
python -m fatebridge.mcp_server
```

### 6.2 MCP 工具分组

#### 基础命理与时运

- `analyze_destiny`
- `two_person_compatibility`
- `timing_analysis`
- `dayun_analysis`
- `liunian_analysis`
- `liuyue_analysis`
- `liuri_analysis`
- `jieqi_timeline_analysis`
- `bazi_birth`

#### Calendar / export / knowledge helper

- `jieqi_year`
- `nongli_time`
- `export_registry`
- `export_parse`
- `knowledge_registry`
- `knowledge_read`
- `gua_lookup`
- `gua_meiyi`

#### Divination 与本地技法

- `meihua_analysis`
- `tongshefa`
- `sixyao`
- `canping`
- `heluo`
- `suzhan`
- `otherbu`
- `sanshiunited`

#### 中国术数独立盘

- `ziwei_birth`
- `ziwei_rules`
- `liureng_gods`
- `liureng_runyear`
- `qimen`
- `taiyi`
- `jinkou`

#### 核心占星盘

- `astro_chart`
- `astro_chart13`
- `astro_hellen_chart`
- `astro_guolao_chart`
- `astro_india_chart`
- `astro_germany_chart`
- `astro_relative_chart`

#### 西占推运

- `western_timing_analysis`
- `solarreturn`
- `lunarreturn`
- `transit`
- `solararc`
- `givenyear`
- `profection`
- `pd`
- `pdchart`
- `zr`
- `firdaria`
- `decennials`

### 6.3 MCP 与 REST 的差异

| 维度 | REST | FastMCP |
| --- | --- | --- |
| 传输协议 | HTTP JSON | MCP tool call |
| 返回格式 | JSON object | JSON string |
| 错误表现 | HTTP status + `detail` | 工具字符串中的错误 JSON |
| 使用场景 | Web / script / service integration | Agent host / tool invocation |

## 7. 常见响应字段

### 7.1 命理类

- `person_info`
- `four_pillars`
- `day_master`
- `element_distribution`
- `favorable_elements`
- `structure_profile`
- `ten_gods`
- `patterns`
- `calendar_context`

兼容性分析相关字段补充：

- `detailed_analysis.favorable_synergy.score_basis`
- `detailed_analysis.favorable_synergy.useful_ten_gods_support`
- `detailed_analysis.ten_gods_relationship.supportive_patterns`
- `detailed_analysis.ten_gods_relationship.risk_reasons`
- `detailed_analysis.pattern_synergy.supportive_patterns`
- `detailed_analysis.pattern_synergy.tension_patterns`
- `detailed_analysis.pattern_synergy.risk_patterns`

备注：

- `pattern_synergy.tension_patterns` 中的 `天克地冲` 默认视为高吸引/高摩擦并存的张力型组合，不再直接等同于纯负面结论

### 7.2 占星类

- `chart_profile`
- `angles`
- `houses`
- `planets`
- `aspects`
- `interpretation`
- `snapshot_text`
- `snapshot_export`

### 7.3 推运类

- `summary`
- `analysis_context`
- 各 technique payload，例如 `solar_return`、`primary_directions`、`firdaria`
- `snapshot_text`
- `snapshot_export`

## 8. 调试建议

### 8.1 section 名称不匹配

优先检查：

- `snapshot_export.section_titles_detected`
- `snapshot_export.missing_selected_sections`

### 8.2 占星盘精度不如预期

优先检查：

- `chart_profile.engine_precision`
- `chart_profile.engine_backend`

### 8.3 西占推运直接报错

优先检查本地是否具备：

- `kerykeion`
- Swiss Ephemeris 运行时

## 9. 进一步阅读

- [GETTING_STARTED.md](GETTING_STARTED.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
