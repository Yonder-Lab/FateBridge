# FateBridge 风水性能独立评估（2026-10-14）

性能目标是以完整、正确、可追溯的资料得到有用的布局判断。更少的规则、消失的冲突、被删掉的未知项或空白答复都不能算加速。

## 可复现的范围

```sh
.venv/bin/python scripts/benchmark_fengshui.py --repeats 7 --warmups 2 \
  --mcp --mcp-max-size 32 --compare-layout-ref HEAD \
  --output docs/audits/2026-10-14/fengshui-performance.json
```

基准覆盖形态、八宅、三基础方法、四方法合参；每类 1、8、32、128、200 个对象，另含只知道朝向的部分资料请求和 50 住户压力请求。对象规模是基准负载，不是对真实用户人数的估计。输入使用明确标注的虚构数据，时间冻结为 2026-10-14T12:00:00+08:00。

数据为 macOS arm64 / Python 3.13.5 的本地 wall-clock，各项分开计时、预热 2 次、保留 7 个原始样本。P95 使用线性插值，仅描述该组样本，不能当生产 SLO；团队同时工作的负载可能影响时间。首次调用共享进程缓存，不是 fresh-process 冷启动。JSON 中记录源码 SHA，当前主测量期间只有 `mcp_server.py` 发生文案修改；不要将其标为静态全仓快照。初测 `fengshui-performance-initial.json` 保留审计轨迹，因并行修改，不用于前后改善声称。

MCP 指 `fastmcp.Client(app)` 的进程内实际协议调用，包含 SDK 的服务端/客户端验证，没有网络或 Codex 模型。真实连接器 wall-clock、模型工具选择/规划/生成需另测。`duration_ms` 是服务执行与首次输出验证，尚未包含 receipt 构造、最终验证、传输渲染、SDK 或模型；不能拿它冒充用户等待时间。

## 测量结果

完整和首轮视图执行同一方法及输入。以下原始主测量使用运行时共享 `suggested_fields`：`status`、`layout_analysis`、`coverage`、`conflicts`、`rule_trace`，保留完整 `run_metadata`，关闭 `snapshot_text`。后续字段优化的候选量测另见下文。

| 请求 | 本地服务含快照，中位 ms | 共享执行含验证/receipt，中位 ms | 完整 JSON bytes | 首轮 JSON bytes | 进程内 MCP 完整/首轮，中位 ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| 单对象形态 | 0.198 | 0.390 | 16,246 | 7,460 | 152.35 / 149.04 |
| 单对象四方法 | 1.323 | 3.221 | 104,187 | 28,498 | 155.30 / 142.10 |
| 8 对象四方法 | 2.318 | 6.768 | 234,238 | 125,076 | 228.33 / 171.76 |
| 32 对象四方法 | 6.080 | 18.979 | 681,000 | 456,582 | 317.55 / 421.64 |
| 200 对象四方法 | 约 33 | 107.550 | 3,813,692 | 2,779,518 | 本轮最终协议矩阵未测此规模 |
| 50 住户压力 | 29.269 | 146.741 | 4,074,534 | 2,436,360 | 798.88 / 717.11 |

字节是精确 UTF-8 紧凑 JSON 大小，不是 token 数。MCP 的 text 和 structuredContent 分别传递同一业务负载，host 是否去重、如何转换成模型上下文并未测量；不能简单将两份字节加起来换算 tokens。投影减小负载，但样本没有证明所有请求的 MCP 都更快（32 对象这一组首轮更慢），因此不能报告统一时延提升比例。

## 根因及落实

1. **计算结果按对象反复扫描。** 原 `analyze_layout` 对每个 placement 扫描全体八宅 placement findings，搜索成本为 O(P² × 作用域)。技术负责人已改为按 `object_id` 一次建立索引；这是通用算法修复，没有改变风水规则。基准从可信本地 HEAD 读取旧函数，以当前同一请求和预计算 layers 比较，两份完整 layout 输出严格相等，避免把其它功能修复带来的输出减少混作改善。1/8/32/128/200 对象分别测得旧函数中位 0.059/0.389/1.591/8.245/14.397 ms，当前 0.054/0.368/1.488/6.602/9.600 ms。大规模有价值，不能将 200 对象约 33% 的 layout 子步骤改善称为整体用户等待改善。

2. **首轮字段控制的是输出，不能消除完整计算成本。** `services/fengshui._compose` 先生成快照和 export；`execute_tool` 构造全部数据、两次输出验证、业务指纹，再由传输层 `project_fields` 投影。首轮保留整个 layout subtree，随对象/作用域放大，200 对象仍达 2.78 MB。进一步优化需要明确可复用的结果/展开合同，不能默默省略方法、作用域、候选或冲突；当前仅测量，没有为了 benchmark 改动业务语义。`parent_run_id` 只是关联标记，不是存储结果索引，下一轮重调同一工具仍会计算。

3. **MCP 小请求主要受 SDK 重复 schema 检查影响。** 可复现的单形态 cProfile 中，两次 `jsonschema.validate` 的 `check_schema` 约 408.7 ms，占受 instrumentation 放大后的总 profile 约 97%。检查公开 schema 的成本远大于单形态业务计算。当前 SDK 服务端与客户端各校验输出；公开 outputSchema 使用复杂引用。未关闭任何校验，未压缩合同掩盖问题。安全方向是 SDK 层复用已验证 schema/validator；需仍完整验证每次实例，保留 invalid-schema、invalid-output、契约版本变化的行为。该方向未实现，不把 profile 时间当正常 wall-clock。

4. **共享输出校验与 receipt 成本随输出规模增长。** 最大请求 profile 中 `validate_output` 两次累计约 67 ms，`execution_receipt` 约 60 ms（profile 时间，不是无 instrumentation 时延）。嵌套输出类型触发共享 `_validate_calendar_dates` 1427 次，虽然多数风水对象没有出生/分析日期，仍执行八组日期前缀反射；业务摘要又遍历并序列化完整输出。已把通用基类成本同步给技术负责人。本轮不擅自跳过这些正确性检查或缓存含用户数据的结果。

5. **工具发现是上下文负载，不只是服务器时间。** 全 catalog 的实际 `list_tools` 共 87 项、约 2.05 MB JSON；仅 fengshui family 共 7 项、约 208 KB。单工具输入合同约 17.8 KB、完整合同约 42.4 KB。限制公开 family 改变了可用能力，不是等价计算加速。真实咨询应优先一次按工具名拿完整参数定义，避免重复打印整个 catalog，再重复读取同一工具；真实模型是否因此少一个往返由另一个评估层验证。为了 Codex 参数可见性而内联 inputSchema 必须报告发现字节增长，不能只报告模型更容易调用。

## 防止 reward hacking 的边界

- 每种投影对选中的业务子树与原始执行结果逐项严格相等，特别保留 `coverage`、部分状态、冲突、规则来源和执行回执；错误 envelope 立即使基准失败。
- 索引因果比较只允许完整输出相等。不同方法之间的耗时表是不同覆盖的横向数据，不能把少方法当优化。
- 多住户冲突输出的规模来自真实作用域差异，不通过删住户或合成总分减小输出。
- 性能脚本不评价建议质量。真实用户资料变化是否改变判断、是否承认未知朝向/落宫、是否把传统规则当普遍事实，仍需独立旅程评估。
- 本地测试、真实 MCP 连接、独立模型对话、Linux golden 是不同证据。此报告不声称模型选择行为、真实模型 token 计费、生产网络 SLO 或 Linux golden 已验证。

基准脚本 Black / isort / Mypy 通过；矩阵包含运行时结果完整性断言。核心修复的业务与跨传输测试由技术负责人报告。

## 通用首轮投影候选

`fengshui-first-view-candidates.json` 测量所有 22 类请求。建议保留 `layout_analysis` 的 status、calculation_scope、placement_findings、adjustment_options、environment_adjustments、form_analysis、element_remedies、annual_remedies、supplement_statuses、method_disagreements、missing_inputs、unsupported_queries、limitations，连同顶层 status、coverage、conflicts、rule_trace 和自动保留的 run_metadata。各项使用完整 dotted path；保留的子树均严格等于完整结果。

仅把 `element_relationships` 的完整派生关系表和 `supplemental_rulesets` 的详细来源说明延后展开；用户明确问元素作用时仍需请求这些字段。建议不要为了再省约 200 bytes 丢 calculation_scope 与补充层状态。规则 ID/版本及方法冲突留在首轮；详细来源 URL 与作者约定可以再展开，首轮不能引用尚未取得的详细来源文本。

| 请求 | 原首轮 bytes | 推荐首轮 bytes | 减少 |
| --- | ---: | ---: | ---: |
| 单对象形态 | 7,462 | 5,755 | 22.88% |
| 8 对象形态 | 19,921 | 18,214 | 8.57% |
| 单对象四方法 | 28,499 | 22,320 | 21.68% |
| 8 对象四方法 | 125,076 | 75,939 | 39.29% |
| 32 对象四方法 | 456,582 | 260,017 | 43.05% |
| 200 对象四方法 | 2,779,519 | 1,550,046 | 44.23% |
| 部分朝向资料 | 10,256 | 7,732 | 24.61% |
| 50 住户压力 | 2,436,360 | 2,366,667 | 2.86% |

多住户的主要负载是需要保留的作用域冲突，不能宣传固定的削减比例。这是字节改善，模型时延/token 成本需真实模型另测。

## inputSchema 内联后的独立复测

技术负责人为 Codex 参数可见性仅内联 inputSchema，没有内联 outputSchema。初次采集恰好已加载新注册器，不能当 before；因此采用可信 HEAD 旧注册器与当前注册器、同一套**当前**领域 schema 和描述做配对，且使用 `select_specs(..., surface="mcp")`，避免将 REST-only 工具混入公开统计。`fengshui-discovery-input-inline-comparison.json` 记录全部逐工具 byte/hash。

- 全公开 MCP 87 项：2,049,864 → 2,049,870 bytes（+6 bytes）。这是方法之间引用删除/展开的净效应，单工具可以增长。
- 风水公开 7 项：209,496 → 209,569 bytes（+73 bytes）。`fengshui_assess` input：11,469 → 11,822 bytes（+353 bytes），9 个 `$ref` → 0。其 output 25,128 bytes，所有 87 项 outputSchema 指纹严格不变。
- `fengshui-performance-input-inline.json` 为无源码变动的后测量，5 样本、1 预热：进程内 MCP 完整/原首轮的单形态 127.24/125.64 ms、单对象四方法 261.12/282.34 ms、8 对象四方法 220.51/178.14 ms、部分资料 144.57/143.56 ms、50住户 920.70/777.77 ms。存在运行负载差异，不能据跨轮数值断言内联使协议更快或更慢。
- 后测 cProfile 仍有两次输出 `check_schema`（累计约454 ms，受 instrumentation 影响）。内联输入解决的是参数可见性，不声称解决输出校验或真实模型等待。

配对发现比较现可复现：`scripts/benchmark_fengshui.py --sizes 1 --repeats 1 --warmups 0 --compare-mcp-input-ref HEAD --json`。这是注册器/公开字节比较，非时延 SLO；参照 ref 必须由操作者信任。
