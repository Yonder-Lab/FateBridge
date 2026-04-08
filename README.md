# FateBridge - 命运之桥

基于 FastMCP 框架的中国传统命理工具，连接古典智慧与现代技术，为您搭建通向命运洞察的桥梁。

**[English](README_EN.md)** | 中文

---

## ✨ 特性

### 🎯 核心功能

- **四柱命理计算**：精确计算年、月、日、时柱
- **节气历边界**：以立春分年、以十二节判月，补足传统八字关键边界
- **出生时间精修**：支持出生分钟、时区、经度与真太阳时修正
- **五行分析**：全面的五行分布与强弱分析
- **十神关系**：详细的十神配置分析
- **格局识别**：识别三合、六合、六冲等特殊格局
- **喜用神推算**：科学推断命局所需的平衡元素
- **核心星盘与派生星盘**：新增标准星盘、13 扇区扩展盘、希腊星盘、果老风格盘、印度盘、量化中点盘与关系盘
- **FateBridge 导出协议 helper**：新增 `export_registry` 与 `export_parse`，支持按 FateBridge AI 导出 contract 解析快照文本
- **悬浮知识 helper**：新增 `knowledge_registry` 与 `knowledge_read`，支持 astrology / 六壬 / 奇门离线知识读取；两者现已统一返回 `snapshot_text + snapshot_export`
- **农历与卦象辅助**：输出农历、节气上下文与梅花易数时卦辅助信息
- **节气 / 农历 helper**：`jieqi_year` 与 `nongli_time` 现已统一返回 `snapshot_text + snapshot_export`，便于历法辅助结果按 section 离线导出
- **时运 helper 导出协议**：`liuyue_analysis` 与 `jieqi_timeline_analysis` 现已统一返回 `snapshot_text + snapshot_export`，可按 section 离线导出时运摘要
- **流年 / 流日导出协议**：`liunian_analysis` 与 `liuri_analysis` 现已统一返回 `snapshot_text + snapshot_export`，便于时运专项结果按 section 离线消费
- **综合时运 / 大运导出协议**：`timing_analysis` 与 `dayun_analysis` 现已统一返回 `snapshot_text + snapshot_export`，并补上专项结果一致性回归
- **梅花时卦分析**：独立输出本卦、变卦、互卦、综卦与体用关系
- **梅易卦义批量查询**：支持按卦码 / 卦名批量读取偏梅花易数语境的卦义摘要
- **梅花问事骨架**：自动串联本卦、变卦、体用与动爻阶段，生成可直接阅读的占断摘要
- **动爻细断层**：补充爻位断语、时机提示、问事适配与体用修正建议
- **六爻全表**：按本卦 1-6 爻逐条生成变卦走向、体用关系与爻位摘要
- **卦义断辞层**：本卦、变卦、互卦、综卦与卦义检索统一返回 `judgement`、`image`、`favorable`、`caution`
- **卦义检索**：支持按卦名或二进制卦码查询八卦/六十四卦义理摘要
- **卦义 helper 导出协议**：`gua_lookup` 与 `gua_meiyi` 现已统一返回 `snapshot_text + snapshot_export`
- **Phase 2 本地技法**：统摄法、六爻、宿占、占星骰子、三式合一均由 FateBridge 离线内核直接计算，无需外部 runtime
- **宿占离线宫制 / 黄道切换**：标准 `suzhan` 现已支持 FateBridge 本地 `0..8` 全套旧版兼容宫制与 `tropical / sidereal(Lahiri-like)` 模式；当 `houseStartMode=1` 时，`1..8` 会保留真实离线宫头
- **占星骰子离线宫制 / 黄道切换**：`otherbu` 现已支持 FateBridge 本地 `0..8` 全套旧版兼容宫制与 `tropical / sidereal(Lahiri-like)` 模式，且 `1..7` 会保留真实离线宫头而不是退化成等宽 30° ring
- **奇门变体盘语义稳定化**：独立 `qimen` 与 `qimen_options` 变体盘统一返回 `content_palace / content_trigram`，`zhifu / zhishi` 也会直接带内容来源，并新增独立 `snapshot_text` 与可按 `selected_sections` 过滤的 `snapshot_export`
- **三式合一本地真太阳时**：`sanshiunited` 现已支持 `use_true_solar_time`，会直接复用 FateBridge 离线真太阳时修正链路重算三式盘面
- **三式合一离线导出协议**：`sanshiunited` 新增 `snapshot_export`，可按 `selected_sections` 定向导出起盘摘要、太乙/六壬分段与单宫详解
- **独立八字 / 紫微 / 规则库 / 太乙 / 六壬 / 金口诀导出协议**：`bazi_birth`、`bazi_direct`、`ziwei_birth`、`ziwei_rules`、`taiyi`、`liureng_gods`、`liureng_runyear`、`jinkou` 现已统一返回 `snapshot_text + snapshot_export`

### 🤝 高级功能

- **双人配合分析**：深度分析两人八字的配合程度
- **五行互补性分析**：评估两人五行的协调性
- **十神关系对比**：分析两人十神的互动
- **关系类型适配**：针对婚姻、友谊、商业、家庭等特定关系的专化分析
- **时运分析**：大运、流年、流月的综合影响评估
- **流月专项分析**：按真实节令月输出月柱、流年配套关系与节气窗口
- **年内节点观察**：支持流日与 24 节气节点时间轴，便于查看一年内关键转换点
- **离线西占扩展**：内置近似星历算法，可在无外部星历依赖时返回结构化星盘结果
- **西占推运与返照**：支持太阳返照、月返、次限推运、太阳弧、小限、法达与十年星限时间轴

### 💻 技术特点

- ✅ 基于 FastMCP 框架的标准化 API
- ✅ 精确的中国传统历法计算
- ✅ Pydantic 数据验证确保类型安全
- ✅ 模块化架构便于扩展
- ✅ 全面的错误处理和日志记录
- ✅ CORS 和安全配置
- ✅ 生产级代码质量

---

## 🚀 快速开始

### 系统要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 后端启动

```bash
# 1. 克隆仓库
git clone https://github.com/thomas-yanxin/FateBridge.git
cd FateBridge

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境
cp .env.example .env

# 5. 启动 API 服务器
python api.py
# API 将在 http://localhost:8010 运行

# 6. （可选）启动 FastMCP 服务器
python fastmcp_server.py
```

### 前端启动

```bash
cd fatebridge-web

# 1. 安装依赖
npm install

# 2. 配置环境
cp .env.example .env.local
# 编辑 .env.local，设置 API 地址

# 3. 启动开发服务器
npm run dev
# 前端将在 http://localhost:3000 运行
```

### 健康检查

```bash
# 检查 API 是否在线
curl http://localhost:8010/health
# 返回: {"status":"healthy"}
```

---

## 📚 使用示例

### REST API 示例

#### Python

```python
import requests
import json

url = "http://localhost:8010/api/calculate"
payload = {
    "name": "张三",
    "gender": "男",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_place": "北京"
}

response = requests.post(url, json=payload)
result = response.json()

print(json.dumps(result, ensure_ascii=False, indent=2))
```

#### JavaScript/TypeScript

```typescript
const response = await fetch('http://localhost:8010/api/calculate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: '张三',
    birth_year: 1990,
    birth_month: 5,
    birth_day: 15,
    birth_hour: 10,
    birth_minute: 30,
    birth_timezone: 'Asia/Shanghai',
    use_true_solar_time: true,
    birth_place: '北京',
  }),
});

const analysis = await response.json();
console.log(analysis);
```

#### cURL

```bash
curl -X POST http://localhost:8010/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "birth_year": 1990,
    "birth_month": 5,
    "birth_day": 15,
    "birth_hour": 10,
    "birth_minute": 30,
    "birth_timezone": "Asia/Shanghai",
    "use_true_solar_time": true,
    "birth_place": "北京"
  }' | jq .
```

### 出生时间精度说明

- 默认仍兼容旧版调用：只传 `birth_hour` 时，系统按整点小时制计算。
- 需要更细粒度时，可额外传 `birth_minute`。
- 启用真太阳时修正时，推荐同时传 `birth_timezone` 与 `birth_longitude`；若 `birth_place` 命中内置地点库，系统会自动补全经度和默认时区。
- 现在支持更广泛的地址文本输入，既可传中文完整地址，也可传英文或拼音形式，例如 `浙江省宁波市海曙区...`、`Haishu District, Ningbo, Zhejiang`、`zhejiang sheng ningbo shi ...`。
- 当地址同时命中城市和省份时，会优先解析到更具体的城市；若城市未收录但省份可识别，则会回退到省级近似经度。
- 响应里的 `time_adjustment` 会额外返回 `resolved_place` 与 `resolution_level`，方便确认系统最终采用了哪个地点层级。
- 离线地址解析仍是近似值，不是联网地图地理编码；需要最高精度时，优先显式传 `birth_longitude`。
- 当前月柱与起运已改为**本地离线节气口径**：以立春分年、以十二节判月，并按出生时刻到节令边界的天数换算起运岁数。
- 节气时间采用离线 fixed-qì 近似算法，适合本地推演与 API 返回；若需要瑞士星历级精排，仍建议接入专门天文历表。
- 响应新增 `calendar_context`，可直接查看当前/下一节气、农历信息、月令边界与梅花时卦摘要。
- 综合时运响应现已包含 `liuri_analysis` 与 `analysis_calendar.jieqi_timeline`，可直接观察分析日与全年 24 节气节点的时运切换。

### 核心模块直接使用

```python
from fatebridge.core.calendar import BaZiCalendar
from fatebridge.core.elements import ElementAnalysis
from datetime import datetime

# 计算四柱命理
birth_time = datetime(1990, 5, 15, 10)
pillars = BaZiCalendar.get_four_pillars(birth_time)
print(BaZiCalendar.format_pillars(pillars))

# 五行分析
element_analysis = ElementAnalysis.comprehensive_analysis(pillars)
print(f"日主: {element_analysis['day_master']['day_element']}")
print(f"强弱: {element_analysis['day_master']['strength_level']}")
```

---

## 📖 文档

### 用户文档

- [API 文档](docs/API.md) - 完整的 API 参考
- [快速入门](docs/GETTING_STARTED.md) - 详细的入门指南
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题解决

### 开发者文档

- [架构设计](docs/ARCHITECTURE.md) - 系统架构和模块设计
- [开发指南](docs/DEVELOPMENT.md) - 开发环境和工作流
- [贡献指南](CONTRIBUTING.md) - 如何参与开发
- [修复记录](FIXES.md) - 最近的安全和质量修复

---

## 📁 项目结构

```
FateBridge/
├── docs/                          # 文档
│   ├── API.md                    # API 完整参考
│   ├── ARCHITECTURE.md           # 架构设计
│   ├── DEVELOPMENT.md            # 开发指南
│   └── TROUBLESHOOTING.md        # 故障排除
│
├── fatebridge/                   # Python 核心包
│   ├── core/
│   │   ├── calendar.py          # 干支历法计算
│   │   ├── astrology.py         # 离线近似星盘与关系盘
│   │   ├── astrology_predictive.py # 西占返照、推运与时间主星系统
│   │   ├── almanac.py           # 节气、农历与本地历法辅助
│   │   ├── divination.py        # 卦象与梅花易数辅助
│   │   ├── gua_meanings.py      # 八卦/六十四卦离线义理与断辞
│   │   ├── elements.py          # 五行分析
│   │   ├── rules.py             # 格局识别
│   │   └── timing.py            # 时运分析
│   ├── services/
│   │   ├── astrology.py         # 西占本命 / 关系盘服务
│   │   └── western_timing.py    # 西占返照 / 推运 / 时运服务
│   ├── analysis/
│   │   ├── compatibility.py     # 双人配合
│   │   └── timing_effects.py    # 时运影响
│   └── utils/
│       ├── data.py              # 数据定义
│       └── helpers.py           # 工具函数
│
├── fatebridge-web/              # Next.js 前端
│   ├── app/                     # 页面和路由
│   ├── components/              # React 组件
│   └── utils/                   # 工具函数
│
├── api.py                       # FastAPI 服务器
├── fastmcp_server.py            # FastMCP 服务器
├── logic.py                     # 业务逻辑层
├── requirements.txt             # Python 依赖
├── pyproject.toml              # 项目配置
└── CONTRIBUTING.md             # 贡献指南
```

---

## 🔌 API 端点

### REST API

| 方法 | 端点 | 说明 |
|------|------|------|
| `POST` | `/api/calculate` | 个人命理分析 |
| `POST` | `/api/compatibility` | 双人配合分析 |
| `POST` | `/api/astro/chart` | 标准星盘 |
| `POST` | `/api/astro/chart13` | 13 扇区扩展盘 |
| `POST` | `/api/astro/hellen` | 希腊星盘 |
| `POST` | `/api/astro/guolao` | 果老 / 七政四余风格盘 |
| `POST` | `/api/astro/india` | 印度盘（sidereal） |
| `POST` | `/api/astro/germany` | 量化盘 / 中点盘 |
| `POST` | `/api/astro/relative` | 合盘 / 关系盘 |
| `POST` | `/api/astro/timing` | 西占推运 / 返照 / 时运系统（含指定年盘、顺逆主限、离线 SemiArc 主限、界限 overlay、黄道释放） |
| `POST` | `/api/export/registry` | FateBridge 导出协议注册表 |
| `POST` | `/api/export/parse` | FateBridge 快照导出解析 |
| `POST` | `/api/knowledge/registry` | astrology / 六壬 / 奇门知识目录 |
| `POST` | `/api/knowledge/read` | astrology / 六壬 / 奇门知识读取 |
| `POST` | `/api/cn/jieqi/year` | 全年节气盘 helper |
| `POST` | `/api/cn/nongli/time` | 农历换算 helper |
| `POST` | `/api/cn/gua/meiyi` | 梅易卦义 helper |
| `POST` | `/api/cn/bazi/birth` | 独立八字命盘 |
| `POST` | `/api/cn/bazi/direct` | 独立八字直断 |
| `POST` | `/api/cn/ziwei/birth` | 独立紫微斗数命盘 |
| `POST` | `/api/cn/ziwei/rules` | 紫微规则库 |
| `POST` | `/api/cn/liureng/gods` | 独立六壬起课分析 |
| `POST` | `/api/cn/liureng/runyear` | 独立六壬行年分析 |
| `POST` | `/api/cn/qimen` | 独立奇门遁甲分析 |
| `POST` | `/api/cn/taiyi` | 独立太乙神数分析 |
| `POST` | `/api/cn/jinkou` | 独立金口诀分析 |
| `POST` | `/api/divination/gua` | 卦义检索 |
| `POST` | `/api/divination/meihua` | 梅花时卦分析 |
| `POST` | `/api/divination/tongshefa` | 统摄法分析 |
| `POST` | `/api/divination/sixyao` | 六爻 / 易卦分析 |
| `POST` | `/api/divination/suzhan` | 宿占 / 宿盘分析 |
| `POST` | `/api/divination/otherbu` | 西洋游戏 / 占星骰子分析 |
| `POST` | `/api/divination/sanshiunited` | 三式合一聚合分析 |
| `POST` | `/api/timing/comprehensive` | 综合时运分析 |
| `POST` | `/api/timing/dayun` | 大运专项分析 |
| `POST` | `/api/timing/liunian` | 流年专项分析 |
| `POST` | `/api/timing/liuyue` | 流月专项分析 |
| `POST` | `/api/timing/liuri` | 流日专项分析 |
| `POST` | `/api/timing/jieqi` | 全年 24 节气节点时间轴 |
| `GET` | `/health` | 健康检查 |

### FastMCP 工具

| 工具 | 说明 |
|------|------|
| `analyze_destiny` | 个人命理分析 |
| `two_person_compatibility` | 双人配合分析 |
| `timing_analysis` | 综合时运分析（含 snapshot_export） |
| `astro_chart` | 标准星盘 |
| `astro_chart13` | 13 扇区扩展盘 |
| `astro_hellen_chart` | 希腊星盘 |
| `astro_guolao_chart` | 果老 / 七政四余风格盘 |
| `astro_india_chart` | 印度盘（sidereal） |
| `astro_germany_chart` | 量化盘 / 中点盘 |
| `astro_relative_chart` | 合盘 / 关系盘 |
| `western_timing_analysis` | 西占推运 / 返照 / 时运系统（含指定年盘、顺逆主限、界限 overlay、黄道释放） |
| `dayun_analysis` | 大运专项分析（含 snapshot_export） |
| `liunian_analysis` | 流年专项分析（含 snapshot_export） |
| `liuyue_analysis` | 流月专项分析（含 snapshot_export） |
| `liuri_analysis` | 流日专项分析（含 snapshot_export） |
| `export_registry` | FateBridge 导出协议注册表 |
| `export_parse` | FateBridge 快照导出解析 |
| `knowledge_registry` | astrology / 六壬 / 奇门知识目录（含 snapshot_export） |
| `knowledge_read` | astrology / 六壬 / 奇门知识读取（含 snapshot_export） |
| `jieqi_year` | 全年节气盘 helper |
| `nongli_time` | 农历换算 helper |
| `jieqi_timeline_analysis` | 节气节点时间轴分析（含 snapshot_export） |
| `gua_meiyi` | 梅易卦义 helper（含 snapshot_export） |
| `bazi_birth` | 独立八字命盘 |
| `bazi_direct` | 独立八字直断 |
| `ziwei_birth` | 独立紫微斗数命盘 |
| `ziwei_rules` | 紫微规则库（含 snapshot_export） |
| `liureng_gods` | 独立六壬起课分析 |
| `liureng_runyear` | 独立六壬行年分析 |
| `qimen` | 独立奇门遁甲分析 |
| `taiyi` | 独立太乙神数分析 |
| `jinkou` | 独立金口诀分析 |
| `gua_lookup` | 卦义检索（含 snapshot_export） |
| `meihua_analysis` | 梅花时卦分析 |
| `tongshefa` | 统摄法分析 |
| `sixyao` | 六爻 / 易卦分析 |
| `suzhan` | 宿占 / 宿盘分析 |
| `otherbu` | 西洋游戏 / 占星骰子分析 |
| `sanshiunited` | 三式合一聚合分析 |

> 核心星盘家族 `chart / chart13 / hellen / guolao / india / germany` 现已支持显式 `hsys` / `zodiacal` 覆盖。未显式传入时，FateBridge 会保留各盘型原本的离线默认语义：`chart / chart13` 默认 `equal + tropical`，`hellen / guolao` 默认 `whole_sign + tropical`，`india` 默认 `whole_sign + sidereal`；`germany` 会继承其底层基准 chart 的覆盖结果。

> `relative` 关系盘现已支持旧版兼容的 `relative_mode`、`hsys`、`zodiacal` 输入；旧 `relationship_mode` 仍兼容。当前缺省 mode 会按旧版兼容语义的 `0=比较盘` 处理。现代字段 `relative_mode=Synastry/synastry` 现统一收敛为“影响盘”，而旧字段 `relationship_mode=synastry` 仍保留 FateBridge 早期“比较盘”兼容路径，并会在返回 metadata 里显式标注解析来源。`compare` 以方向相位层为主，`composite` 以合成盘层为主，`influence / timespace / marks` 也已提供 FateBridge 离线近似主层；中点相位、映点/反映点与 `inner / outer` 影响图盘均已可用。当前离线 `hsys` 已支持 `0..8` 的整套旧版兼容宫制编号，其中 `1..8` 通过本地 Swiss house cusps 驱动，不再局限于 `0/8`。`zodiacal` 当前离线仅支持 `0=回归黄道` 与 `1=恒星黄道(Lahiri-like)`，且 `1` 会真实切换到 sidereal 近似计算，不再只是 metadata。

---

## ⚙️ 配置

### 环境变量

```bash
# 复制环境模板
cp .env.example .env

# 编辑 .env 文件
ALLOWED_ORIGINS=http://localhost:3000  # CORS 允许的源
API_HOST=0.0.0.0                       # API 绑定地址
API_PORT=8010                          # API 端口
LOG_LEVEL=INFO                         # 日志级别
```

### 安全配置

生产环境必须配置：

```bash
# 设置允许的源为您的域名
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 使用 HTTPS
# 配置反向代理（Nginx、Apache）

# 启用速率限制（未来实现）
# 实施认证和授权（未来实现）
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 查看覆盖率
pytest --cov=fatebridge tests/

# 检查代码风格
black --check fatebridge/
isort --check-only fatebridge/

# 类型检查
mypy fatebridge/
```

---

## 🔒 安全

本项目包含以下安全特性：

- ✅ 输入验证（Pydantic）
- ✅ CORS 配置
- ✅ 错误处理（无堆栈泄露）
- ✅ 结构化日志记录
- ✅ 环境变量配置

详见 [FIXES.md](FIXES.md) 中的安全改进。

---

## 📈 性能

- 单个分析请求：< 100ms
- 双人配合分析：< 150ms
- 支持并发请求
- 优化的算法复杂度：O(1)

---

## 🗺️ 路线图

### 近期（v0.2.0）

- [ ] 批量分析 API
- [ ] 结果缓存（Redis）
- [ ] 数据库持久化

### 中期（v0.3.0）

- [ ] 用户认证系统
- [ ] 历史记录管理
- [ ] 高级建议引擎

### 长期（v1.0.0）

- [ ] GraphQL API
- [ ] WebSocket 实时分析
- [ ] 移动应用
- [ ] 预测模型

---

## 🤝 贡献

我们欢迎各种形式的贡献！

- 🐛 报告 Bug
- 💡 提议新功能
- 📝 改进文档
- 🔧 提交代码

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📝 许可证

本项目采用 Apache License 2.0 许可证。详见 [LICENSE](LICENSE)。

---

## 📧 联系

- GitHub Issues：报告 Bug 和功能请求
- GitHub Discussions：提问和讨论
- Email：[提交建议](mailto:yx20001210@163.com)

---

## 🙏 致谢

感谢所有为 FateBridge 做出贡献的人！

特别感谢：

- FastMCP 框架的开发者
- 传统八字理论的研究者
- 所有提出反馈和建议的用户

---

## ⭐ 如果喜欢，请给个 Star！

如果 FateBridge 对您有帮助，请在 GitHub 上给我们一个 ⭐

这将帮助我们获得更多关注，吸引更多贡献者。

---

**Made with ❤️ by the FateBridge Community**
