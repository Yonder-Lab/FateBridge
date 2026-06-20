# FateBridge 架构优化设计：简洁、优雅、零漂移

- **日期**：2026-06-21
- **状态**：已通过 brainstorming 评审，待落实施计划
- **策略**：A —— 安全网优先，自底向上分阶段推进（SP0 → SP1 → SP2 → SP3）

## 1. 背景与动机

FateBridge 的三端入口（CLI / REST / MCP）已由中央 `ToolSpec` catalog 统一驱动，结构健康。
但 `core/` 层积累了若干审美与结构债，与「对开发者友好、对 Agent 友好、命名注释优雅」的目标存在落差：

| 维度 | 现状 | 证据 |
|---|---|---|
| god-modules | `core/` 23 文件 23k 行，5 个巨型文件 | `astrology_predictive 3897`、`astrology 3360`、`metaphysics 2893`、`phase2_local 2671`、`rules 1792` |
| 命名债 | `phase2_local.py` 是开发期阶段名，`phase2_`/`_phase2_` 前缀渗入数十个函数 | `_build_phase2_houses`、`parse_phase2_datetime`、`_resolve_phase2_coordinates` |
| 泛化命名 | `utils/helpers.py`(1100行)、`utils/data.py` 是「杂物抽屉」名 | 看名字无法判断职责 |
| 注释一致性 | 61 文件中 35 个含中文注释、其余英文，无统一约定 | 35/61 |
| 层边界 | `core`/`services`/`analysis` 三层文档清晰，但 `phase2_local` 等文件横跨多层语义 | — |

## 2. 目标与不变量

### 三根支柱
1. **开发者友好 + Agent 友好**：清晰的模块边界、可发现的公共 API、稳定的输出契约。
2. **命名与注释的审美**：优雅、一致、自解释。
3. **code 层面优化**，且**计算准确性零漂移**。

### 贯穿原则
**简洁优雅**：YAGNI、删冗余、抽共享原语、每个文件聚焦单一职责。

### 不可破坏的不变量（铁律）
- 每个子项目 = **独立分支、单一职责**。
- 合并门槛 = `471 测试 + golden-master diff + 四道门禁（black / isort / mypy / pytest）` 全绿。
- **任何工具的 JSON 输出字节级不变**，除非该子项目显式声明输出变更并经用户确认。

### 统一约定（本次确立）
- **标识符英文**（Pythonic），**注释与 docstring 中文**（讲清命理语义）。
- 文件移动一律用 `git mv` 保留历史。

## 3. 子项目分解

### SP0 —— Golden-master 安全网（第一个，先建网）

后续所有重构的「数值锁」。本身是纯新增测试设施，不触碰引擎代码，风险≈0。

- `tests/golden/fixtures.py`：为全部 catalog 工具(当前 68 个 ToolSpec，66 个对外暴露)各配 1–2 组**代表性、确定性**输入（固定生辰 / 时间 / 地点；冻结一切「当前时间」与随机依赖）。
- `tests/golden/snapshots/<tool>.json`：首次运行冻结的规范化输出（键排序、浮点定精度）。
- `tests/test_golden_master.py`：重算并 diff，任何字段差异即失败并打印 diff。
- 提供一个重新生成基线的开关（如 `FATEBRIDGE_REGEN_GOLDEN=1`），仅在**经确认的输出变更**时使用。

**验收**：基线覆盖全部 catalog 工具(68 个 ToolSpec)；`test_golden_master` 在 master 当前状态全绿。

### SP1 —— 命名 + 注释扫荡（纯审美，零行为变化）

- **文件改名**（候选，planning 阶段按内容定稿）：
  - `core/phase2_local.py` → 领域名（候选 `core/local_techniques.py`）
  - `utils/helpers.py` → 职责名（候选 `utils/formatting.py` 等）
  - `utils/data.py` → 职责名（候选 `utils/normalization.py` 等）
- **符号改名**：清除 `phase2_`/`_phase2_` 等开发期前缀，改领域语义名。
- **注释 / docstring 统一**：落实「标识符英文 + 注释中文」；补齐公共 API 的 docstring；删死代码与无用 import。

**验收**：golden-master 字节不变；四门禁全绿；`grep -rE 'phase2|_v[0-9]'` 在 `fatebridge/` 归零。

### SP2 —— god-modules 拆子包（纯搬迁）

候选目标布局（planning 阶段按真实「缝线」定稿）：

```
core/predictive/   ← 由 astrology_predictive.py 按推运法拆：
                     zodiacal_releasing / primary_directions / firdaria /
                     decennials / returns / _subject(共享底座)
core/astrology/    ← 由 astrology.py 按 natal / ephemeris / aspects 拆
core/divination/   ← 收拢 divination.py + 本地术数(原 phase2_local)
```

纯文件搬迁 + import 调整，**逻辑一行不改**。

**验收**：golden-master 字节不变；无文件 > ~800 行（软目标，超出需说明）；四门禁全绿。

### SP3 —— 层边界重构 + 抽共享原语（最贴逻辑，靠 golden-master 兜底）

- 厘清 `core`（纯算法）/ `services`（编排 + 快照）/ `analysis`（复合分析）边界，归位混层代码。
- 抽共享原语（已知候选）：
  1. **十神计数**（ten-god counting，dedup 审计中标记的 pending 原语）
  2. **结构化 dict → 中文快照渲染器**（现散落多处）
  3. **三端统一错误 / 响应包装**
- 每个原语抽取**单独 commit + golden diff**，便于精确归因。

**验收**：golden-master 字节不变；重复逻辑收敛到单一信源；四门禁全绿。

## 4. 每个子项目的统一验证协议

```
建分支 → 改 → .venv(3.13) 跑 471 测试 + golden diff + black/isort/mypy
       → 用户审核 → 推送 + 建 PR + 盯 CI(3.10–3.13 矩阵)
       → 用户授权 squash-merge → 同步 master → 进入下一个 SP
```

每个 SP 合并后，下一个 SP 从最新 master 重新分支，避免堆叠依赖。

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 边界重构误改数值路径 | golden-master 字节级 diff + 原语逐个独立 commit |
| 拆包引入循环 import | 拆前先画依赖方向；`_subject` 等共享底座下沉为叶子模块 |
| 文件改名漏掉引用点 | 沿用 PR #59 验证过的做法：先 `grep` 全量引用面再改，含 docs / tests / 配置 |
| golden 基线把「既有 bug」也冻结了 | 基线只保证「重构零漂移」，不保证「命理正确」；若发现既有 bug，单列工具修正项并显式声明输出变更 |

## 6. 明确不做（YAGNI / Out of scope）

- 不新增命理功能（Horosa 覆盖等另案）。
- 不改三端入口的 catalog 派生机制（已是正资产）。
- 不为重构而重构 `metaphysics.py`/`rules.py` 内部，除非 SP3 边界归位确有需要。
- 不引入新框架 / 新依赖。
