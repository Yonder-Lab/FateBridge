# FateBridge 算法与能力覆盖矩阵

本文档描述 FateBridge 当前代码库“实际上支持哪些算法/技法”，以及每项能力在运行时属于哪一类。它的目标不是描述理想状态，而是描述代码里的真实状态。

状态分类：

- `Implemented`：仓库内已有实现，且可通过 REST / MCP / CLI 访问
- `Approximate`：可用，但算法明确是离线近似、轻量近似或依赖回退路径
- `Placeholder`：合同或模式入口存在，但主输出层仍是占位兼容
- `Excluded`：当前仓库不提供该能力

> 工具的唯一信源是中央目录 `fatebridge/services/tool_catalog.py`。当前共 **80 个工具**，分为 **13 个 family**，三端（REST / MCP / CLI）由同一份目录自动派生。下表逐 family 列出全部工具；新增能力时请同步本页（计数由 `tests/test_doc_tool_counts.py` 锁定）。

## 1. 总览：13 个 family / 80 个工具

| family | 工具数 | 主题 | 总体状态 |
| --- | --- | --- | --- |
| `bazi` | 11 | 八字命盘 + 九大专项维度 + 综合命理 | Implemented |
| `compatibility` | 2 | 双人配合（八字合婚 / 宿曜相性） | Implemented |
| `timing` | 9 | 大运 / 流年 / 流月 / 流日 / 流时 / 节气 / 农历 | Implemented |
| `divination` | 10 | 梅花、六爻、统摄法、参评数、河洛、宿占、三式合参等 | Implemented |
| `metaphysics` | 8 | 紫微斗数、六壬、奇门、太乙、金口诀 | Implemented |
| `astro` | 7 | 离线核心星盘家族 + 关系/合盘 | Implemented（精度依赖星历） |
| `western_timing` | 1 | 西占推运总览 bundle | Implemented（依赖 backend） |
| `western_timing_tool` | 11 | 独立西占推运技法（返照/行运/主限/法达…） | Implemented（依赖 backend） |
| `western_event` | 4 | 事件占星（世俗/卜卦/择日/多重回归） | Implemented（依赖 backend） |
| `western_lifespan` | 13 | 全生命周期 / 寿命技法（古典+西占） | Implemented（依赖 backend） |
| `knowledge` | 2 | 内置知识库目录与读取 | Implemented |
| `export` | 2 | 导出协议注册表与快照解析 | Implemented |
| 仓库内前端 | — | 内置 Web UI | Excluded |
| 存储 / 账户 | — | 数据库、历史记录、用户体系 | Excluded |

## 2. 逐 family 工具清单

### 2.1 `bazi` —— 八字与命理分析（Implemented）

底层由 `fatebridge.core.calendar` / `elements` / `rules` 与 `fatebridge.services.bazi` / `calculation` 提供；九大专项维度的大运、流年缺省由命盘 + 分析日期内部推算，可用 `dayun_pillar` / `liunian_pillar` 覆盖。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `analyze_destiny` | 综合命理分析（八字 + 喜用 + 格局） | Implemented |
| `bazi_birth` | 离线八字命盘，完整 `snapshot_text` + 可筛选 `snapshot_export` | Implemented |
| `bazi_marriage` | 婚姻：配偶星/宫、婚期信号、婚姻质量 | Implemented |
| `bazi_career` | 事业：事业类型、行业、创业倾向、贵人方位 | Implemented |
| `bazi_wealth` | 财运：正偏财、财库、求财方式/方位、破财风险 | Implemented |
| `bazi_health` | 健康：体质、五行脏腑、易患疾病、养生方向（仅命理参考） | Implemented |
| `bazi_children` | 子女：子女星/宫、缘分、生育时机 | Implemented |
| `bazi_education` | 学业：印星/食伤/官星、学历倾向、文昌、考试时机 | Implemented |
| `bazi_personality` | 性格：日主心性、十神性格、刚柔内外向 | Implemented |
| `bazi_relatives` | 六亲：父母/兄弟姐妹星、六亲宫位、贵人 | Implemented |
| `bazi_romance` | 正缘桃花：桃花咸池、红鸾天喜、异性缘星、正缘时机 | Implemented |

### 2.2 `compatibility` —— 双人配合（Implemented）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `two_person_compatibility` | 双人配合度分析（八字合婚 / 合作），复用两份个人分析做组合 | Implemented |
| `sukuyo_compatibility` | 宿曜双人相性（三九の秘法，二十七宿） | Implemented |

### 2.3 `timing` —— 时运与历法（Implemented）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `timing_analysis` | 综合时运（大运/流年/流月等综合影响） | Implemented |
| `dayun_analysis` | 大运分析 | Implemented |
| `liunian_analysis` | 流年分析 | Implemented |
| `liuyue_analysis` | 流月分析 | Implemented |
| `liuri_analysis` | 流日分析 | Implemented |
| `liushi_analysis` | 流时分析 | Implemented |
| `jieqi_timeline_analysis` | 节气时间轴分析 | Implemented |
| `jieqi_year` | 指定年份节气时刻表（calendar helper） | Implemented |
| `nongli_time` | 公历↔农历换算与干支（calendar helper） | Implemented |

> 历法基于本地算法（`fatebridge.core.almanac`），不依赖外部服务。真太阳时修正含经度 + 均时差，统一走 `fatebridge.utils.helpers`。

### 2.4 `divination` —— 占卜与本地技法（Implemented）

均为本地离线技法，多数返回 `snapshot_text + snapshot_export`。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `gua_lookup` | 卦象查询（六十四卦义理） | Implemented |
| `gua_meiyi` | 卦义 helper（批量说明） | Implemented |
| `meihua_analysis` | 梅花易数时卦辅助 | Implemented |
| `tongshefa` | 通蓍法起卦 | Implemented |
| `sixyao` | 六爻纳甲分析 | Implemented |
| `canping` | 邵子参评数 / 金锁银匙（数算） | Implemented |
| `heluo` | 河洛理数（数算） | Implemented |
| `suzhan` | 宿占分析 | Implemented |
| `otherbu` | 占星骰子 / 其他卜法 | Implemented |
| `sanshiunited` | 三式合参（聚合太乙/六壬/奇门并统一快照导出） | Implemented |

### 2.5 `metaphysics` —— 中国术数独立盘（Implemented）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `ziwei_birth` | 紫微斗数命盘 | Implemented |
| `ziwei_horoscope` | 紫微斗数运限（大限/小限/流年/流月/流日/流时 + 动态四化） | Implemented |
| `ziwei_rules` | 紫微斗数规则 helper | Implemented |
| `liureng_gods` | 六壬课体与天将 | Implemented |
| `liureng_runyear` | 六壬流年分析 | Implemented |
| `qimen` | 奇门遁甲排盘分析 | Implemented |
| `taiyi` | 太乙神数分析 | Implemented |
| `jinkou` | 金口诀分析 | Implemented |

> 紫微斗数计算以 iztro JS 库为对齐基线，命宫/身宫/五行局/四化/大限等核心字段已逐一核验；运限以正月初一为年界。

### 2.6 `astro` —— 离线核心星盘与关系盘（Implemented，精度依赖星历）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `astro_chart` | 离线核心星盘（`chart_variant` 切换盘式） | Implemented / Approximate（见 §3.1） |
| `astro_chart13` | 离线 13 星座盘 | Implemented / Approximate |
| `astro_hellen_chart` | 离线希腊盘 | Implemented / Approximate |
| `astro_guolao_chart` | 离线果老星宗 / 七政四余盘 | Implemented / Approximate |
| `astro_india_chart` | 离线印度 sidereal 盘 | Implemented / Approximate |
| `astro_germany_chart` | 离线德国中点盘（派生盘） | Implemented / Approximate |
| `astro_relative_chart` | 离线关系/合盘（`compare`/`composite`/`influence`/`timespace`/`marks`） | Implemented / Approximate |

### 2.7 `western_timing` + `western_timing_tool` —— 西占推运（Implemented，依赖 backend）

走 `fatebridge.core.predictive.*` 与 `fatebridge.core.astrology_predictive`；缺 `kerykeion` / Swiss Ephemeris 时**直接报错，不降级**（见 §3.3）。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `western_timing_analysis` | 西占推运综合总览 bundle | Implemented（依赖 backend） |
| `solarreturn` | 太阳返照 | Implemented（依赖 backend） |
| `lunarreturn` | 月亮返照 | Implemented（依赖 backend） |
| `transit` | 行运盘 | Implemented（依赖 backend） |
| `solararc` | 太阳弧 | Implemented（依赖 backend） |
| `givenyear` | 指定年盘 | Implemented（依赖 backend） |
| `profection` | 年小限 | Implemented（依赖 backend） |
| `pd` | 主限（primary directions） | Implemented（公开近似/坐标策略，见 §3.3） |
| `pdchart` | 主限法盘 | Implemented（含 coordinate / approximation 元数据） |
| `zr` | 黄道释放（zodiacal releasing） | Implemented（依赖 backend） |
| `firdaria` | 法达星限 | Implemented（依赖 backend） |
| `decennials` | 十年星限 | Implemented（依赖 backend） |

### 2.8 `western_event` —— 事件占星（Implemented，依赖 backend）

求解天文时刻后起盘的一组事件类工具，走 `fatebridge.core.astrology_events` / `astrology_horary` / `astrology_election`。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `astro_mundane` | 世俗入宫盘 | Implemented（依赖 backend） |
| `astro_extrareturns` | 多重回归 | Implemented（依赖 backend） |
| `astro_horary` | 卜卦判断 | Implemented（依赖 backend） |
| `astro_election` | 择日 | Implemented（依赖 backend） |

### 2.9 `western_lifespan` —— 全生命周期 / 寿命技法（Implemented，依赖 backend）

读取单张本命盘的一组全生命周期技法，走 `fatebridge.core.astrology_lifespan`。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `astro_harmonic` | 调波盘 | Implemented（依赖 backend） |
| `astro_planetary_ages` | 行星年龄 | Implemented（依赖 backend） |
| `astro_triplicity_rulers` | 三分主星推运 | Implemented（依赖 backend） |
| `astro_lunation_phase` | 月相推运 | Implemented（依赖 backend） |
| `astro_distributions` | 界推运（distributions） | Implemented（依赖 backend） |
| `astro_balbillus` | Balbillus 129 年系统 | Implemented（依赖 backend） |
| `astro_keypoints` | 数字相位推运 | Implemented（依赖 backend） |
| `astro_yearsystem129` | 129 年系统 | Implemented（依赖 backend） |
| `astro_planetaryarc` | 行星弧方向 | Implemented（依赖 backend） |
| `astro_persiandirected` | 波斯向运 | Implemented（依赖 backend） |
| `astro_agepoint` | 年龄推进点（age point） | Implemented（依赖 backend） |
| `astro_vedicprog` | 恒星推运 | Implemented（依赖 backend） |
| `astro_jaynesprog` | 赤纬推运 | Implemented（依赖 backend） |

### 2.10 `knowledge` + `export` —— 知识库与导出（Implemented）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `knowledge_registry` | 列出内置知识域与分类 | Implemented |
| `knowledge_read` | 读取单条内置知识并支持导出裁剪 | Implemented |
| `export_registry` | 返回 FateBridge 导出协议注册表 | Implemented |
| `export_parse` | 将快照文本解析为可筛选的结构化 section | Implemented |

> 内置知识域：`astro`、`bazi`、`liureng`、`qimen`。`bazi` 域含十神（10）、神煞（12）、格局（10）、五行（5）、财运（8）、健康（8）、子女（4）、学业（6）、性格（3）、六亲（3）、正缘桃花（3）等条目。

## 3. 精度与依赖说明

### 3.1 核心占星盘（`astro` family）

| 情形 | 状态 | 说明 |
| --- | --- | --- |
| 本地有 `swisseph` | Implemented | `fatebridge.core.astrology` 优先走本地高精度路径 |
| 无 `swisseph` | Approximate | 回退到 FateBridge 内置近似轨道模型 |
| 显式 `hsys` 覆盖为 `1..8` 的离线宫制 | Implemented（但依赖 `swisseph`） | 缺失时**直接报错**，不静默退化为整宫制 |
| `zodiacal=1` sidereal(Lahiri-like) | Implemented | 离线 sidereal 模式，非联网服务 |

可用 `chart_profile.engine_precision` / `chart_profile.engine_backend` 确认当前实际走了哪条路径。

### 3.2 关系盘（`astro_relative_chart`）

| 模式 | 状态 | 说明 |
| --- | --- | --- |
| `compare` | Implemented | 方向相位层为主 |
| `composite` | Implemented | 组合盘主层 |
| `influence` | Implemented | 影响盘双向主层 |
| `timespace` | Implemented | 时空中点盘（Davison）主层 |
| `marks` | Implemented | 派生关系主层 |
| 未识别的 `relative_mode` | Excluded | 返回 `validation_error`，不把非法 mode 当作受支持能力 |

兼容性提醒：

- `relative_mode="Synastry"` / `"synastry"` 按现代语义收敛到 `influence`
- 旧字段 `relationship_mode="synastry"` 仍保留早期“比较盘”兼容路径
- 两条语义不同，迁移旧调用时应显式区分

### 3.3 西占推运 / 事件 / 寿命（`western_*` families）

- 这四个 family 明确依赖 `kerykeion` / Swiss Ephemeris 运行时
- `ensure_predictive_backend_available()` 会在缺依赖时抛错（`dependency_missing`）
- 与核心 chart 不同，**不会降级成近似版**——这是准确性优先的刻意选择
- `pd` / `pdchart` 虽已实装，但内部会公开其近似/坐标策略（time key、direct/converse、相位列表等），不应被误读为单一路径高精度结果

## 4. 快照协议覆盖

下列能力族已经把 `snapshot_text + snapshot_export` 视为公共合同：

- `bazi_birth` 及八字九大专项维度
- 全部 `timing` 工具
- `knowledge_registry` / `knowledge_read` / `export_*`
- `gua_lookup` / `gua_meiyi`
- 全部 `divination` 工具（`suzhan` / `otherbu` / `sanshiunited` / `canping` / `heluo` 等）
- 全部 `metaphysics` 工具（`ziwei_*` / `liureng_*` / `qimen` / `taiyi` / `jinkou`）
- 全部 `astro` chart 家族、`western_timing_tool` / `western_event` / `western_lifespan` 独立技法

使用建议：

- `snapshot_text` 适合直接阅读或写入日志
- `snapshot_export.export_text` 适合按 `selected_sections` 精简后给 Agent 或下游 UI
- `section_titles_detected` 与 `missing_selected_sections` 用于调试 section 名是否写对
- `selected_sections` 只裁剪导出层，不会裁掉完整结构化 payload

## 5. 这页不包含什么

以下内容不应从本页推断：

- 不是所有能力都保证“天文级精度”（见 §3）
- 不是所有实现都意味着“无需本地依赖”（`western_*` 需要 backend）
- 不是所有 legacy mode 都代表推荐用法（见 §3.2）

如果你准备修改接口或新增能力，请同步更新本页，确保“文档状态”仍然是从代码反推出来的结果，而不是愿景描述。
