# FateBridge

FateBridge 是一个面向命理、占术与离线占星场景的 Python 后端仓库。当前仓库只包含服务端与核心算法，不包含前端应用；同一套领域能力通过 FastAPI、FastMCP 与命令行（`fatebridge` CLI）三类接口对外暴露，便于 Web 集成、脚本调用与 Agent 工具接入。三类接口均由中央工具目录（`fatebridge/services/tool_catalog.py`）统一声明、自动注册。

> 当前仓库默认提供 63 个 REST 路由（含 `/health`、`/ready`、`/metrics`）、60 个 FastMCP 工具，以及对应的 `fatebridge` CLI 子命令。

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
```

推荐用 [uv](https://docs.astral.sh/uv/)，建虚拟环境和装依赖一步到位，也快很多：

```bash
uv venv                  # 在 .venv 建虚拟环境（可加 --python 3.13 指定版本）
source .venv/bin/activate
uv pip install -e .      # 装运行依赖；想跑测试/格式化就用 -e ".[dev]"
```

还没装 uv 的话：`curl -LsSf https://astral.sh/uv/install.sh | sh`。

也可以继续用 pip：

```bash
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

# 可选：启用 REST API key 鉴权
FATEBRIDGE_API_KEYS=agent:replace-me
API_KEY_HEADER_NAME=X-API-Key
```

- 端口 `8010` 应视为内部服务端口，不应直接暴露为公网业务入口。

### 3. 启动 REST API

```bash
python -m fatebridge.api
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
python -m fatebridge.mcp_server
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

其中八字类结果新增 `structure_profile`，会把当前主格局、次级格局、最终喜用五行、可用十神与合冲事件对格局流通的影响结构化返回；`/api/compatibility` 的 `detailed_analysis` 也会补充 `score_basis`、`supportive_patterns`、`tension_patterns`、`risk_patterns` / `risk_reasons` 等解释字段，用于区分"和合支持""高张力吸引"和"明显风险"。

### 婚姻分析结果

`/api/cn/bazi/marriage` 端点返回婚姻专项分析：

- `spouse_star`：配偶星定位与特征（正财/偏财为妻、正官/七杀为夫）
- `spouse_palace`：配偶宫（日支）分析与稳定性
- `marriage_quality`：婚姻质量评分（0-100）与等级
- `marriage_timing`：婚期推断信号与早婚/晚婚倾向
- `risk_factors`：婚姻风险因素（日支逢冲、伤官见官、比劫争财等）
- `suggestions`：综合婚姻建议

### 事业分析结果

`/api/cn/bazi/career` 端点返回事业专项分析：

- `dominant_ten_gods`：主导十神与事业类型（独立经营/竞争型/才华型/创新型/稳健型等）
- `industry_analysis`：适合行业推荐（基于喜用神五行）
- `career_structure`：事业格局评分与等级
- `entrepreneurship`：创业 vs 打工倾向评分
- `career_timing`：事业时机信号
- `noble_direction`：贵人方位
- `suggestions`：综合事业建议

### 财运分析结果

`/api/cn/bazi/wealth` 端点返回财运专项分析：

- `wealth_stars`：财星定位（正财/偏财，含地支藏干）与正偏财比重
- `wealth_structure`：财富格局（身财两停/财多身弱/身旺财旺/身旺财轻等）与评分
- `wealth_storage`：墓库财分析（辰戌丑未财库与冲开时机）
- `wealth_style` / `wealth_direction`：求财方式（正业/投资）与求财方位
- `wealth_risk`：破财风险（比劫夺财、财星受冲）
- `wealth_timing`：大运/流年财运与破财信号

### 健康分析结果

`/api/cn/bazi/health` 端点返回健康专项分析（仅供命理参考，非医学诊断）：

- `constitution`：体质（日主强弱 + 寒暖燥湿调候）
- `organ_analysis`：五行脏腑强弱（过旺/偏弱/缺失对应隐患）
- `disease_risks`：易患疾病提示（地支相冲、五行受克处）
- `health_timing`：健康风险时机（冲克日主、七杀攻身）
- `regimen`：养生调理方向（喜用神对应脏腑）

### 子女分析结果

`/api/cn/bazi/children` 端点返回子女专项分析（按性别取子女星）：

- `child_star`：子女星定位（男命官杀、女命食伤）与力量
- `child_palace`：子女宫（时柱）状态与冲合
- `affinity`：子女缘分厚薄、数量倾向评分
- `relationship`：与子女关系及子女成就倾向
- `children_timing`：生育/添丁时机信号

### 学业分析结果

`/api/cn/bazi/education` 端点返回学业专项分析：

- `study_stars`：印星/食伤/官星/财星力量（学业关键十神）
- `education_level`：学历层次倾向（官印相生/食伤配印/财破印等）与评分
- `wenchang`：文昌贵人
- `subject_orientation`：文理倾向与适合学科方向
- `exam_timing`：考试/升学时机信号

### 性格 / 六亲 / 正缘桃花分析结果

- `/api/cn/bazi/personality`（性格心性）：日主五行心性、主导十神性格、刚柔内外向、优劣势与调适建议。
- `/api/cn/bazi/relatives`（六亲关系）：父母星（偏财/正印）、兄弟姐妹星（比劫）、六亲宫位与贵人助力。
- `/api/cn/bazi/romance`（正缘桃花）：桃花（咸池）、红鸾天喜、异性缘星（按性别）、桃花正邪与正缘时机（区别于侧重配偶宫的「婚姻」维度）。

> 以上九个八字专项维度（婚姻/事业/财运/健康/子女/学业/性格/六亲/正缘桃花）均同时提供独立 REST 端点、MCP 工具与 CLI 子命令：`bazi_marriage` / `bazi_career` / `bazi_wealth` / `bazi_health` / `bazi_children` / `bazi_education` / `bazi_personality` / `bazi_relatives` / `bazi_romance`。
>
> **大运/流年自动推算**：用户无需自己知道大运。各维度默认由命盘 + 分析日期（缺省为今天，或传 `analysis_year`/`analysis_month`/`analysis_day`）**内部推算**当前大运、流年柱，并在结果的 `timing_context` 中回显所用的大运/流年与起运年龄。如确需指定，可传 `dayun_pillar`、`liunian_pillar`（如 `"甲子"`）作为覆盖。

### 统一工具目录与三大接口

所有工具（约 60 个）现在只在中央目录 `fatebridge/services/tool_catalog.py` 中以 `ToolSpec` **声明一次**，由注册器自动挂载到三个接口：

- **REST**（`fatebridge/api.py` → `register_rest`）：FastAPI HTTP 端点
- **MCP**（`fatebridge/mcp_server.py` → `register_mcp`）：FastMCP 工具
- **CLI**（`fatebridge/cli.py`）：命令行子命令，面向 Agentic/脚本化使用

新增一个工具或分析维度只需在目录中追加一个 `ToolSpec`，无需改动任何接口文件。

```bash
# CLI 示例
fatebridge list                       # 列出所有工具
fatebridge describe bazi_wealth        # 输出某工具的参数 schema/接口/示例（JSON，供 agent 自助发现）
# 大运/流年自动推算，无需手动输入：
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male
fatebridge knowledge_read --domain bazi --category romance --key 桃花咸池
# 字段投影（token 预算）：只取需要的字段，run_metadata 始终保留
fatebridge bazi_wealth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields analysis_type wealth_analysis
# 点号子路径：从大块 payload 里只抽某个标量，避免整盘 dump
fatebridge bazi_birth --birth-year 1990 --birth-month 6 --birth-day 15 \
    --birth-hour 10 --gender male --fields snapshot_text bazi_birth.day_master
```

> **字段投影（token 预算控制）**：CLI 的 `--fields KEY...` 与 FastMCP 工具的 `fields` 参数都可把响应裁剪到指定字段，便于 Agent 按 token 预算取数。支持**顶层 key**（如 `wealth_analysis`）与**点号子路径**（如 `bazi_birth.day_master`，把大块裁到指定子字段；请求整块与子路径并存时整块优先）；`run_metadata` 始终保留以维持溯源，错误响应不会被裁剪。

### 扩展神煞系统

八字命盘现在包含 32 项神煞（原 10 项），新增：

- 天德贵人、月德贵人：主逢凶化吉、品德高尚
- 将星：主领导力、权威
- 金舆：主富贵、车马之福
- 亡神、劫煞：主变动、劫难
- 孤辰、寡宿：主孤独、晚婚
- 红鸾、天喜：主婚恋喜事
- 学堂、词馆：主学业、文采

### 八字知识库

`/api/knowledge/read` 支持 `domain=bazi` 查询，包含：

- 十神解释（10 项）：比肩、劫财、食神、伤官、正财、偏财、正官、七杀、正印、偏印
- 神煞解释（12 项）：天乙贵人、文昌、桃花、驿马、华盖、天德/月德、将星、金舆、孤辰寡宿、红鸾天喜、学堂词馆
- 格局解释（10 项）：正官格、七杀格、食神格、伤官格、正财格、偏财格、正印格、偏印格、建禄格、羊刃驾杀格
- 五行解释（5 项）：木、火、土、金、水（含方位、行业、健康对应）
- 财运（8 项）：身财两停、财多身弱、身旺财旺、食伤生财、比劫夺财、财库、正财、偏财
- 健康（8 项）：五行藏象、木主肝胆、火主心、土主脾胃、金主肺、水主肾、七杀攻身、调候寒暖
- 子女（4 项）：子女星、子女宫、时柱十神看子女、生育时机
- 学业（6 项）：印星主学历、官印相生、食伤主才华、文昌贵人、财破印、伤官见官
- 性格（3 项）：日主五行心性、十神定性格、身强身弱定刚柔
- 六亲（3 项）：六亲取象、六亲宫位、比劫论兄弟姐妹
- 正缘桃花（3 项）：桃花咸池、红鸾天喜、异性缘星

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

几个关键目录的职责：

- `fatebridge/api.py`: FastAPI 路由、Pydantic 请求模型、HTTP 错误处理
- `fatebridge/mcp_server.py`: FastMCP 工具定义与 JSON 输出封装
- `fatebridge/core`: 核心算法、历法、占星、占术、导出合同
- `fatebridge/services`: 面向 API/MCP 的编排层与快照拼装层
- `fatebridge/analysis`: 高层分析逻辑，如配合度与时运影响、婚姻分析、事业分析
- `fatebridge/utils`: 输入归一化、真太阳时、地点解析、通用 helper
- `tests`: API/MCP 对齐、合同、回归与能力验证

## 主要能力域

| 能力域 | 代表接口 | 说明 |
| --- | --- | --- |
| 八字与命理分析 | `/api/calculate`、`/api/cn/bazi/*` | 出生信息归一化、四柱、五行、格局、喜用神 |
| 八字婚姻分析 | `/api/cn/bazi/marriage` | 配偶星、配偶宫、婚期推断、婚姻质量评估 |
| 八字事业分析 | `/api/cn/bazi/career` | 事业类型、行业推荐、创业倾向、事业格局 |
| 双人配合 | `/api/compatibility` | 基于两份个人分析结果做综合配合度评估 |
| 时运分析 | `/api/timing/*` | 综合时运、大运、流年、流月、流日、流时、节气时间轴 |
| Calendar / Gua helper | `/api/cn/jieqi/year`、`/api/cn/nongli/time`、`/api/divination/gua` | 给上层应用和 Agent 的历法/义理辅助面 |
| Phase 2 本地技法 | `/api/divination/*` | 梅花、统摄法、六爻、宿占、占星骰子、三式合一 |
| 中国术数独立盘 | `/api/cn/ziwei/*`、`/api/cn/liureng/*`、`/api/cn/qimen`、`/api/cn/taiyi`、`/api/cn/jinkou` | 统一支持 `snapshot_text + snapshot_export` |
| 核心占星盘 | `/api/astro/*` | 离线星盘、派生盘、关系盘 |
| 西占推运 | `/api/astro/timing*` | 总览与独立 technique 工具 |
| 导出与知识 | `/api/export/*`、`/api/knowledge/*` | 导出协议与内置知识库（含八字知识库） |

## 开发与验证

```bash
pytest -q
pytest tests/test_api_alignment.py -q

black --check fatebridge scripts tests
isort --check-only fatebridge scripts tests
mypy fatebridge/
```

更细的开发说明见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 已知边界

- 本仓库不包含 in-repo Web 前端；如果要接 UI，需要自行对接 REST API 或 MCP
- 核心占星 chart 家族支持本地高精度与近似离线双路径
- 西占推运能力不是纯近似实现，缺少相关运行时依赖时会直接报错而不是静默降级
- `selected_sections` 只影响 `snapshot_export.export_text` 的裁剪，不会裁掉完整结构化 payload

## 许可证

见 [LICENSE](LICENSE)。
