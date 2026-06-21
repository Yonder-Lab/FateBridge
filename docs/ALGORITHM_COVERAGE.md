# FateBridge 能力覆盖矩阵

本文档描述 FateBridge 当前代码库“实际上能做什么”，以及这些能力在运行时属于哪一类：

- `Implemented`：仓库内已有实现，且可通过 API / MCP 访问
- `Approximate`：可用，但算法明确是离线近似、轻量近似或依赖回退路径
- `Placeholder`：合同或模式入口存在，但主输出层仍是占位兼容
- `Excluded`：当前仓库不提供该能力

> 本页的目标不是描述理想状态，而是描述代码里的真实状态。

## 总览

| 域 | 能力 | 状态 | 说明 |
| --- | --- | --- | --- |
| 核心命理 | 单人八字分析、八字命盘 | Implemented | 由 `fatebridge.services.calculation`、`fatebridge.services.bazi` 提供 |
| 配合度 | 双人配合分析 | Implemented | 复用两份个人分析结果做组合分析 |
| 时运 | 综合时运、大运、流年、流月、流日、节气时间轴 | Implemented | 统一支持结构化结果；多项工具支持 `snapshot_export` |
| Calendar helper | 节气年盘、农历换算 | Implemented | 基于本地历法辅助逻辑，不依赖外部服务 |
| 卦义 helper | `gua_lookup`、`gua_meiyi` | Implemented | 支持批量说明与快照导出 |
| Divination | 梅花、统摄法、六爻、宿占、占星骰子、三式合一 | Implemented | 均为本地离线服务面，可直接通过 REST / MCP 调用 |
| 中国术数独立盘 | 紫微、六壬、奇门、太乙、金口诀 | Implemented | 统一支持 `snapshot_text + snapshot_export` |
| 导出协议 | `export_registry`、`export_parse` | Implemented | FateBridge 内部导出合同与 section 过滤面 |
| 知识 helper | `knowledge_registry`、`knowledge_read` | Implemented | 当前知识域为 `astro`、`liureng`、`qimen` |
| 核心占星盘 | `chart` / `chart13` / `hellen` / `guolao` / `india` / `germany` | Implemented | 运行时精度取决于本地 ephemeris 可用性 |
| 关系盘 | `compare` / `composite` / `influence` / `timespace` / `marks` | Implemented | 各主模式都有实装主层；精度同样依赖 chart backend |
| 西占总览推运 | `western_timing_analysis` | Implemented | 依赖 `kerykeion` / Swiss Ephemeris 运行时 |
| 西占独立 technique | `solarreturn` / `lunarreturn` / `transit` / `solararc` / `givenyear` / `profection` / `pd` / `pdchart` / `zr` / `firdaria` / `decennials` | Implemented | 独立工具已实装，并支持 `selected_sections` |
| 仓库内前端 | 内置 Web UI | Excluded | 当前仓库不包含前端应用 |
| 存储层 | 数据库、账号体系、历史记录 | Excluded | 当前仓库是纯服务/算法仓库 |

## 精度与依赖说明

### 1. 核心占星盘

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| Chart 家族默认路径 | Implemented | `fatebridge.core.astrology` 会优先使用本地 `swisseph` |
| 无 `swisseph` 时的核心盘 | Approximate | 回退到 FateBridge 内置近似轨道模型 |
| `hsys` 覆盖为 `1..8` 的离线宫制 | Implemented | 但依赖 `swisseph`；缺失时会报错而不是静默退化 |
| `zodiacal=1` sidereal(Lahiri-like) | Implemented | 为离线 sidereal 模式，不是联网服务 |
| `germany` 中点盘 | Implemented | 作为派生盘使用底层 core chart 结果 |

### 2. 关系盘

| 模式 | 状态 | 说明 |
| --- | --- | --- |
| `compare` | Implemented | 方向相位层为主 |
| `composite` | Implemented | 组合盘主层 |
| `influence` | Implemented | 影响盘双向主层 |
| `timespace` | Implemented | 时空中点盘主层 |
| `marks` | Implemented | 派生关系主层 |
| 未识别的 `relative_mode` | Excluded | 当前公开接口会返回 `validation_error`，不把非法 mode 视作受支持能力 |

补充说明：

- `relative_mode="Synastry"` / `"synastry"` 会按现代语义收敛到 `influence`
- 旧字段 `relationship_mode="synastry"` 仍保留早期“比较盘”兼容路径
- 这两条语义不同，调用时应显式区分

### 3. 西占推运

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 太阳返照 / 月返 / 行运 / 太阳弧 | Implemented | 依赖 `kerykeion` / Swiss Ephemeris |
| 指定年盘 / 小限 / 法达 / 十年星限 / 黄道释放 | Implemented | 走 `fatebridge.core.astrology_predictive` |
| 主限 / 主限图盘 | Implemented | 已包含 coordinate / approximation 元数据 |
| 缺少 predictive backend 时的西占推运 | Excluded | 当前不会降级成近似版，而是直接报依赖缺失错误 |

补充说明：

- `ensure_predictive_backend_available()` 会在缺少 `kerykeion` / Swiss Ephemeris 时抛错
- `pd` / `pdchart` 虽然是已实现能力，但内部会公开其近似/坐标策略，不应被误读为单一路径高精度结果

### 4. 中国术数与本地技法

| 能力 | 状态 | 说明 |
| --- | --- | --- |
| 八字、配合度、时运 | Implemented | FateBridge 的主干能力 |
| 节气、农历 helper | Implemented | 本地历法算法 |
| 梅花易数、六爻、统摄法 | Implemented | 本地离线技法 |
| 宿占、占星骰子 | Implemented | 共享本地 chart / palace 适配逻辑 |
| 三式合一 | Implemented | 聚合太乙、六壬、奇门并统一快照导出 |
| 紫微、六壬、奇门、太乙、金口诀 | Implemented | 独立盘与规则库接口均已存在 |

## 快照协议覆盖

下列能力族已经把 `snapshot_text + snapshot_export` 视为公共合同：

- `bazi_birth`
- `timing_analysis` / `dayun_analysis` / `liunian_analysis` / `liuyue_analysis` / `liuri_analysis` / `jieqi_timeline_analysis`
- `knowledge_registry` / `knowledge_read`
- `gua_lookup` / `gua_meiyi`
- `suzhan` / `otherbu` / `sanshiunited` / `canping` / `heluo`
- `ziwei_birth` / `ziwei_rules` / `liureng_gods` / `liureng_runyear` / `qimen` / `taiyi` / `jinkou`
- 占星独立 technique 与 chart 家族

使用建议：

- `snapshot_text` 适合直接阅读或写入日志
- `snapshot_export.export_text` 适合按 `selected_sections` 精简后给 Agent 或下游 UI
- `section_titles_detected` 与 `missing_selected_sections` 可用于调试 section 名是否写对

## 这页不包含什么

以下内容不应从本页推断：

- 不是所有能力都保证“天文级精度”
- 不是所有实现都意味着“无需本地依赖”
- 不是所有 legacy mode 都代表推荐用法

如果你准备修改接口或新增能力，请同步更新本页，确保“文档状态”仍然是从代码反推出来的结果，而不是愿景描述。
