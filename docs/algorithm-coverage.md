# FateBridge 算法与能力覆盖矩阵

本文档描述 FateBridge 当前代码库“实际上支持哪些算法/技法”，以及每项能力在运行时属于哪一类。它的目标不是描述理想状态，而是描述代码里的真实状态。

状态分类：

- `Implemented`：仓库内已有实现，可通过中央目录声明的接口访问；不代表所有端均有同名入口，也不代表预测有效性已被验证
- `Approximate`：可用，但算法明确是离线近似、轻量近似或依赖回退路径
- `Placeholder`：合同或模式入口存在，但主输出层仍是占位兼容
- `Excluded`：当前仓库不提供该能力

> 工具的唯一信源是中央目录 `src/fatebridge/services/tool_catalog.py`。REST / MCP 各公开 **80 个工具**，分为 **12 个 family**。本页按 MCP 集合统计；目录有 82 条记录，CLI 可执行 81 条，差异见 [API 参考](api-reference.md#24-三端能力边界)。下表逐 family 列出全部工具；新增能力时请同步本页（工具总数由 `tests/test_doc_tool_counts.py` 锁定）。

## 1. 总览：12 个 family / 80 个工具

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
| `nongli_time` | 公历时刻转农历与干支（calendar helper） | Implemented |

> 历法基于本地算法（`fatebridge.core.almanac`），不依赖外部服务。真太阳时修正含经度 + 均时差，统一走 `fatebridge.utils.helpers`。

### 2.4 `divination` —— 占卜与本地技法（Implemented）

均为本地离线技法，输出分为双层快照、仅文本和结构化数据，详见 §4。

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `gua_lookup` | 卦象查询（六十四卦义理） | Implemented |
| `gua_meiyi` | 卦义 helper（批量说明） | Implemented |
| `meihua_analysis` | 梅花易数时卦辅助 | Implemented |
| `tongshefa` | 统摄法 / 大衍筮法起卦 | Implemented |
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

> 紫微斗数以 iztro 2.5.8 为对齐基线，采用正月初一年界、虚岁自然年递增、本命晚子时算当天、闰月后半月算下月的规则。400 组本命与运限已比较字段一致；流月/流日/流时比较实际落宫索引，不能用历法地支代替。返回的 `branch` 是实际落宫，`palace_ganzhi` 是本命宫干支，`stem` 是该运限四化所用天干；后两者可能不同。童限按命、财帛、疾厄、夫妻、福德、官禄取宫，农历日期或大限超出支持范围时明确报错。

> 六壬取传按九宗门，第一课生克用日干五行、寄宫只定位；贵人顺逆按贵人实际落地盘的位置判断（巳至戌逆布）。已与独立 daliurenpython 的 8,640 种日干支/时支/月将组合对照，三传全部一致。初轮 kinliuren 参考软件的部分三传存在不稳定与异常，不能把与该软件的所有差异一律判为 FateBridge 错误。完整依据与范围见 [计算修复记录](audits/2026-10-09/FIXES.md)。

### 2.6 `astro` —— 离线核心星盘与关系盘（Implemented，精度依赖星历）

| 工具 | 说明 | 状态 |
| --- | --- | --- |
| `astro_chart` | 离线核心星盘（`chart_variant` 切换盘式） | Implemented / Approximate（见 §3.1） |
| `astro_chart13` | 离线 13 扇区扩展盘 | Implemented / Approximate |
| `astro_hellen_chart` | 离线希腊盘 | Implemented / Approximate |
| `astro_guolao_chart` | 离线果老星宗 / 七政四余盘 | Implemented / Approximate |
| `astro_india_chart` | 离线印度 sidereal 盘 | Implemented / Approximate |
| `astro_germany_chart` | 离线德国中点盘（派生盘） | Implemented / Approximate |
| `astro_relative_chart` | 离线关系/合盘（`compare`/`composite`/`influence`/`timespace`/`marks`） | Implemented / Approximate |

### 2.7 `western_timing` + `western_timing_tool` —— 西占推运（Implemented，依赖 backend）

走 `fatebridge.core.predictive.*`；缺 `kerykeion` / Swiss Ephemeris 时**直接报错，不降级**（见 §3.3）。

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
| 本地有 `swisseph` 且加载相应星历数据 | Implemented | 本地星历路径，实际模型由返回标志确定 |
| `swisseph` 可导入，但缺相应 `.se1` 数据 | Implemented / Approximate | 可能使用内置 Moshier 模型，不能仅凭包可导入或 `engine_backend` 判断数据精度 |
| 无 `swisseph` | Approximate | 回退到 FateBridge 内置近似轨道模型 |
| 显式 `hsys` 覆盖为 `1..8` 的离线宫制 | Implemented（但依赖 `swisseph`） | 缺失时**直接报错**，不静默退化为整宫制 |
| `zodiacal=1` sidereal(Lahiri-like) | Implemented | 离线 sidereal 模式，非联网服务 |

检查 `chart_profile.engine_precision` / `engine_backend` 确认代码路径，再用 `chart_profile.ephemeris_model` 确认实际模型：`swieph` / `jpl` 为相应数据模型，`moshier` 为内置模型，`mixed` 表示混合。`run_metadata.engine_is_approximate` 会标记已识别的降级。数据获取、路径与版本复现见 [快速入门](getting-started.md#星历数据与精度)。

`pyswisseph` 与 `kerykeion` 都是 `pyproject.toml` 的常规安装依赖。“缺依赖回退”描述的是异常/裁剪环境的能力边界，不是另一种官方安装模式。

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
- 与核心 chart 不同，缺 backend 时不会使用 FateBridge 内置轨道近似；但这不保证所有 backend 都加载了相同星历数据，仍需检查返回的精度/模型字段
- `pd` / `pdchart` 虽已实装，但内部会公开其近似/坐标策略（time key、direct/converse、相位列表等），不应被误读为单一路径高精度结果

## 4. 快照协议覆盖

快照双层结构不是所有工具的通用保证。当前典型成功响应按以下形态组织；工具输入是否支持 `selected_sections` 另查 [API 参考](api-reference.md#23-selected_sections)。

| 形态 | 工具范围 | 读取方式 |
| --- | --- | --- |
| `snapshot_text` + `snapshot_export` | 八字独立盘/专项/综合分析、双人配合、全部时运与历法、卦义查询、三式合参、中国术数独立盘、knowledge、核心/关系星盘（中点盘除外）、独立西占推运 | 业务数据为准，快照辅助阅读；支持选择的模型才裁剪导出 |
| `snapshot_text`，无 `snapshot_export` | `tongshefa`、`sixyao`、`canping`、`heluo`、`suzhan`、`otherbu`、西占事件与生命周期工具 | 读取文本与结构化业务数据；需要 section 解析时另调用 `export_parse` |
| 结构化数据，无双层快照 | `meihua_analysis`、`astro_germany_chart`、`western_timing_analysis`、`export_registry`、`export_parse` | 读取各自的业务字段；`export_parse` 直接返回解析结果，不再嵌套 `snapshot_export` |

使用建议：

- 存在的 `snapshot_text` 适合直接阅读；日志中的出生资料需按实际用途管理。
- `snapshot_export.export_text` 是可消费的导出层，不等于所有工具都支持筛选输入。
- `section_titles_detected` / `missing_selected_sections` 用于调试标题；`export_parse` 的这些字段位于响应根。
- `selected_sections` 不删除完整快照或业务数据。整体精简使用 `fields` 与 `include_snapshot_text`。

## 5. 这页不包含什么

以下内容不应从本页推断：

- 不是所有能力都保证“天文级精度”（见 §3）
- 不是所有实现都意味着“无需本地依赖”（`western_*` 需要 backend）
- 不是所有 legacy mode 都代表推荐用法（见 §3.2）

如果你准备修改接口或新增能力，请同步更新本页，确保“文档状态”仍然是从代码反推出来的结果，而不是愿景描述。
