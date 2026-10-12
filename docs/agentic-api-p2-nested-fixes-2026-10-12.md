# FateBridge 长尾专业输出嵌套合同验收

日期：2026-10-12。承接 [API 审查](agentic-api-review-2026-10-09.md)、[P1 修复](agentic-api-fixes-2026-10-12.md) 和 [P2 场景与复现](agentic-api-p2-replay-fixes-2026-10-12.md)。本轮保持 `core → services → transports` 与中央 `ToolSpec` 架构，补齐专业嵌套事实合同；尚未提交、推送或部署。

## 实现与范围

`response_models.py` 继续生成各工具根模型并绑定目录；嵌套模型拆入 `output_western.py`、`output_charts.py`、`output_chinese.py`，共用 `output_base.PartialOutput`。执行、投影和各端发布仍由现有共享注册器处理，没有新增计算分支或第二份工具目录。

[覆盖清单](audits/2026-10-12/agentic-api-p2-nested/coverage.json) 记录本轮新增或扩展嵌套类型的 **68 条工具记录**。全部目录仍为 89 条，REST 87、默认 MCP 87、CLI 可执行 88；包含同期独立风水工作，其业务计算与黄金数据未由本轮修改。

| 输出领域 | 已声明的稳定嵌套事实 |
| --- | --- |
| 西占主限与时序 | 命中、事件年龄/时间、坐标环与坐标上下文、诊断、界限叠层、返照/行运/推运位置、年度/月度小限、综合模块 |
| 时主 | 法达主限与子限、十年时主递归子级、黄道释放层级时间线与峰期/脱节标志 |
| 寿限专业工具 | 调波位置/同频合相、行星年龄与本命状态、三分主星阶段、月相入相时间线、界推运参与者、Balbillus 子限、129 年系统、关键点激活、太阳弧/吠陀命中、波斯主限、年龄点、赤纬平行 |
| 古典与专业星盘 | 星体/宫位/相位、恒星、行星时、尊贵/失势、定位链、阿尔穆滕、阿拉伯点、传光/集光、希腊盘、七政四余格局、印度盘、十三宫、中点 |
| 关系盘与事件 | 内外/组合盘、双向相位与映点、中点条目及旧别名；世俗盘位置、额外返照可空时点、卜卦征象星/月亮/成事与警示 |
| 中国术数 | 四柱/历法/节气、紫微宫位与星曜细节/四化、六壬四课三传及来源索引、奇门宫位/卦码、太乙核心数值与宫位标记、金口诀条目 |
| 地方术数与合参 | 卦义与梅花卦/体用、统摄法、六爻爻位/变爻/卦宫/动态卦码说明、参平条目、河洛运段、宿占/骰子地方盘、三式合参子结果 |

这是一份部分响应兼容的事实合同，不是对所有解释 JSON 的封闭格式声明。八字专题解释、宿曜关系、知识/导出扩展等本轮未重新建模的部分继续使用已有合同；未声明的解释字段与未来扩展保持开放。独立风水领域继续使用其自己的分层模型。

## 兼容性

- 已声明事实采用严格类型；动态星体、卦码、规则名、坐标标识等字典键保持开放，值采用嵌套模型。不同工具的同名 `chart`、`dayun`、`lines` 按工具映射，避免把不同语义合成任意 JSON。
- 任意对象投影可删除兄弟字段，因此对象事实字段可选；既有可空值继续允许 null。数组仍整体选择；本轮未添加数组索引投影。Schema 不保证完整响应的事实全部存在。
- 校验不通过模型重序列化结果：不补默认字段、不删除扩展、不改写整数/浮点、不修改业务排序、文本或计算规则。旧 `.fn` 文本入口、快照裁剪和 CLI 全局 `--no-metadata` 保留。
- 关系模式保留整数与字符串两种合法格式；地方盘 `House1` 宫位字符串、可空星曜亮度、返照时间对象、空时间线和递归子级均按实际构建器声明。
- 嵌套违规在投影前按内部失败处理：REST 500、MCP `isError=true`、CLI 退出 1，保留安全 trace；不归为用户输入错误、不回显违规值。保留既有传输包络差异：HTTP 状态在 HTTP 层，MCP 包络另含 `operation`，CLI 包络含 `status_code`。
- Schema 变化使复现 receipt 的 `contract_sha256` 及实现/环境指纹变化，这是预期版本证据；业务数据格式保持。实现指纹按进程缓存，更新源码后须重新启动。

FastMCP 3.0.0 的默认展开器会把递归 Schema 变成循环 Python 字典，导致整个 `tools/list` 无法序列化。本轮在既有 MCP 适配层增加 `SerializableSchemaMiddleware`：普通输入/输出与资源模板继续展开；若展开结果不能序列化，则保留原始合法 `$defs` / `$ref`。递归结构的类型没有弱化，未提高依赖下限，也没有修改第三方库。

## 验证

新增 [139 项测试](../tests/test_agentic_nested_outputs.py)：旧黄金业务 JSON 的 Pydantic 与 JSON Schema 校验、23 类嵌套类型违规的三端失败语义、16 类深层投影与关闭元数据、非默认专业分支、递归/空列表/null/扩展保留、发布 schema 的深层事实一致性及旧整数关系模式。黄金文件不回写；历史快照的易变 receipt 字段本就被规范化剔除，业务合同验证将 `run_metadata` 排除。

- 当前环境全量回归：**1653 passed、89 skipped、7 warnings**，见 [pytest 日志](audits/2026-10-12/agentic-api-p2-nested/pytest.txt)。89 项跳过均要求 Linux-x86_64 / Python 3.12 的黄金字节比较；本轮旧业务快照结构验证在本地实际执行。
- Python 3.10.20 / FastMCP 3.0.0：**229 passed、50 warnings**，见 [下限回归日志](audits/2026-10-12/agentic-api-p2-nested/fastmcp-floor-pytest.txt)，涵盖本轮与此前 P1/P2、全部业务入口。其他依赖为该环境解析版本，不是所有依赖的最低版本组合。
- mypy：127 个源文件通过；Black：244 个文件无需修改；isort、`git diff --check`、场景 manifest 源文件一致性检查通过。
- [独立本地探针](audits/2026-10-12/agentic-api-p2-nested/probe.py) 核对 19 个深层类型的中央合同、OpenAPI 与原生 MCP 发布结果，并通过实际 CLI 子进程核对主限、递归时主和紫微的投影业务 JSON。[结果](audits/2026-10-12/agentic-api-p2-nested/three-surface-projections.json) 与 [代表合同](audits/2026-10-12/agentic-api-p2-nested/representative-output-schemas.json) 已保存。
- Wheel 构建通过，解包后从打包模块加载新合同并验证嵌套响应；[打包校验](audits/2026-10-12/agentic-api-p2-nested/wheel-verification.json) 使用当前虚拟环境依赖，不等同于全新环境安装验证。

当前为 macOS-arm64 / Python 3.13.5 / FastMCP 3.4.2 的本地验证。未执行 Linux CI、部署后 REST、外部 MCP host 或真实 LLM 工具选择验收。

## 发现成本

[紧凑 UTF-8 JSON 实测](audits/2026-10-12/agentic-api-p2-nested/metrics.json)：

| 对象 | 字节 |
| --- | ---: |
| MCP 全部 87 工具合同 | 3,483,135 |
| MCP 健康场景 5 工具合同 | 202,513 |
| REST 完整工具 manifest | 1,873,961 |
| 共享工具摘要 manifest | 72,801 |

与上一轮 1,319,729 字节的 MCP 全目录相比，专业合同增加了发现成本。这是字节数，不是 token 或延迟测量。摘要发现不携带嵌套 schema；按场景/分类缩小工具集合，再按需读取单工具合同的既有入口继续保留。
