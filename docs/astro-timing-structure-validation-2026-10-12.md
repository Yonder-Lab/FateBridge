# 星盘与时运结构整理验收（2026-10-12）

## 范围与结果

本轮继续处理[结构审查报告](code-structure-review-2026-10-12.md)的三个中优先级热点：星盘引擎、时运服务、被多个服务复用的命盘响应构造器。沿用既有计算与响应合同，内部导入迁到定义模块，历史 Python 路径保留兼容导出。工作区已有的 Agent/CLI、配合度和占卜功能修改保留，不归入本轮重构成果；没有重写黄金快照。

同一解释器、数据环境、固定分析时刻下，**154 项输出与合同 SHA-256 逐项一致**。对迁移定义的 AST 比较，仅归一化运行时属性归属与共享构造器命名后，**153 项定义与整理前相同**。这些证据说明结构迁移保持既有实现与样例输出；它们不构成对原算法本身正确性的独立认证。

## 星盘的职责归属

原 `core/astrology.py` 的 3,457 行实现迁到 `core/astro/`。旧模块现为 281 行兼容导出，内部生产代码不再导入它。

| 模块 | 职责 | 行数 |
| --- | --- | ---: |
| `birth.py` | 出生信息、时区/太阳时归一化后的星盘输入 | 89 |
| `geometry.py` / `orbits.py` | 角度、黄道/时间几何；独立近似轨道计算 | 200 / 195 |
| `runtime.py` / `ephemeris.py` | 后端可用性与一次性故障日志；星体位置与回退路径 | 36 / 179 |
| `reference.py` / `profiles.py` | 引擎配置表；宫制/黄道选择与精度来源 | 407 / 262 |
| `layout.py` / `parts.py` | 共享宫位布局；宫位/行星记录、平衡和摘要 | 102 / 183 |
| `aspects.py` / `classical.py` | 相位、中点、反映点；行星时、恒星与古典层 | 320 / 347 |
| `chart.py` | 本命、变体与中点盘响应组装 | 323 |
| `relationship_charts.py` | 组合、时空、影响、马盘等关系盘构造 | 525 |
| `relationship.py` | 关系模式/焦点归一化和最终关系响应 | 469 |

基础星盘构造与关系盘编排各有独立入口，共享位置、宫位和盘面组件。`core.astrology_tables` 仍为共用星座/尊贵表的信源；引擎选项在 `astro.reference`，不复制既有领域表。

后端缺失、调用失败、近似引擎及精度标记共用 `astro.runtime`。原有 Swiss Ephemeris 调用锁、共享 C 状态和第三方路径恢复仍由 `core.ephemeris_runtime` 维护。迁移没有新增运行时容器或第二套计算引擎。测试的故障注入迁到运行时定义模块。

## 时运与命盘响应的职责归属

| 模块 | 职责 | 行数 |
| --- | --- | ---: |
| `services/timing.py` | 综合时运、大运、流年/月/日/时等七个用例与响应编排 | 891（原 2,028） |
| `timing_state.py` | 年龄、各时间层状态、五维评分、月/节气时间线补全 | 323 |
| `timing_snapshots.py` | 按传入数据渲染时运和日历快照文本 | 600 |
| `calendar_tools.py` / `calendar_input.py` | 节气/农历查询用例；专用日期/坐标/选项解析 | 266 / 64 |
| `birth_payload.py` | 共享命盘分析响应构造 `build_destiny_payload` | 97 |

`birth_context` 负责出生计算上下文，`birth_payload` 负责公共命盘响应，`timing_state` 负责当前时间层状态。八字、综合分析与配合度直接依赖这些共享模块，消除了对兄弟用例服务私有构造器的依赖。评分权重、计算顺序、历法边界、失败降级和文本内容保持原实现。

中央工具目录只把节气/农历服务定义路径改到 `calendar_tools`，名称、请求模型、默认值、响应、跨端映射保持既有合同。`services.timing.calculate_jieqi_year`、`calculate_nongli_time` 与历史私有辅助入口仍为同对象别名；`services.calculation._render_destiny_analysis` 仍指向新公共构造器。

## 回归与复核

比较矩阵使用 `as_of=2026-10-12T12:00:00+08:00`，包括：

- 全目录 89 项工具业务输出，以及完整发现、场景与 OpenAPI 合同。
- 全部基础盘变体的缺省配置、两种出生/太阳时输入、0–8 宫制和两种黄道。
- 全部关系模式的两种黄道、关系盘 0–8 宫制。
- 禁用星历后的近似输出、显式复杂宫制失败、非法黄道错误。
- 五个固定分析时刻、缺省/显式年龄的十份共享时运状态。

业务哈希比较移除 `run_metadata`，因为 run ID、耗时、时间和源码指纹可变。元数据、跨端错误、投影、重放和兼容入口由完整测试验证，不宣称元数据哈希恒定。精确节气切换由已有 `test_jieqi_boundary_precision.py` 等回归覆盖，固定时刻矩阵不宣称恰好跨越节气时刻。

星盘、太阳时、宫制、星历失败、日历与共享计算相关定向测试 **136 passed**；新依赖边界与旧入口兼容测试 **20 passed**。完整回归 **1,917 passed、89 skipped、0 failed**，测试期间源码、测试、脚本与规则数据没有变化。89 项跳过均为平台限定的 Linux 黄金字节比对。文档合同 **27 passed**；black（291 个文件）、isort、mypy（166 个源码文件）、`git diff --check` 和五份修改文档的链接/围栏检查通过。[原始验证记录](audits/2026-10-12/astro-timing-structure/validation.json)保存环境版本、哈希比较、跳过原因和完整 JUnit。

架构检查现在解析绝对导入、相对导入和函数内导入，受检静态图无循环；核心/分析/工具层不依赖外层，星盘消费者不依赖旧聚合入口，共享命盘/时运构造器不回调用例入口。动态导入和第三方内部依赖不在静态图结论范围内。

复核命令（仓库根、项目虚拟环境）：

```bash
PYTHONPATH=.:src .venv/bin/python \
  docs/audits/2026-10-12/astro-timing-structure/capture_outputs.py /tmp/fatebridge-current.json
.venv/bin/python \
  docs/audits/2026-10-12/astro-timing-structure/verify_definitions.py
.venv/bin/python -m pytest -q
.venv/bin/black --check src/fatebridge scripts tests
.venv/bin/isort --check-only src/fatebridge scripts tests
.venv/bin/mypy src/fatebridge
```

整理前/后输出指纹、定义基线及比较结果保存于[审计目录](audits/2026-10-12/astro-timing-structure/before-hashes.json)。本轮验收是本地 macOS 环境的验证；平台限定的 Linux 黄金字节比对与远程 CI 应按其自身源码快照另行确认。

## 低优先级热点

请求模型与工具目录继续保留各自的统一合同和装配职责；它们按领域拆文件的建议仍是后续可选工作。`utils/helpers` 的出生输入、时间归一化和展示边界尚未进一步拆分。本轮完成上述三个中优先级热点，不把低优先级模块列为已重构项目。

上述状态对应星盘/时运这一轮的验收快照。后续已完成请求模型、工具目录与 helpers 拆分，见[低优先级热点整理验收](request-catalog-helpers-validation-2026-10-12.md)。

2026-10-13 后续更新：本报告记录的旧导入路径、Python 别名和 `/api/calculate` 兼容入口已按用户要求删除。当前迁移方式及验证证据见[旧入口与兼容层清理验收](legacy-entry-cleanup-validation-2026-10-13.md)。历史 AST 基线对应当时源码；输出捕获脚本已改为从职责模块导入，不应将当前目录哈希与旧全目录哈希直接相等比较。
