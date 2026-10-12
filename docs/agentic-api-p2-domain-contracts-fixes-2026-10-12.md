# FateBridge 八字专题、宿曜及知识/导出嵌套契约验收

日期：2026-10-12。承接 [API 审查](agentic-api-review-2026-10-09.md) 与 [上一轮长尾专业输出验收](agentic-api-p2-nested-fixes-2026-10-12.md)。本轮补齐此前未重新建模的 14 条工具记录，保持 ToolSpec → services → core 及 REST / MCP / CLI 共享注册、执行、校验和投影架构。

## 本轮变更

新增 `core/output_bazi.py` 和 `core/output_reference.py`，经既有 `core/response_models.py` 挂入中央目录。没有修改业务计算器、输入参数、传输包络、工具名称、依赖下限或黄金快照。

| 范围 | 已声明的稳定嵌套事实 |
| --- | --- |
| 八字九专题 | 婚姻、事业、财运、健康、子女、学业、性格、六亲、桃花；评分/权重、十神与星位条目、财库、产业方向、藏象、文昌、桃花及提示列表 |
| 八字时运上下文 | 自动推导/部分覆盖的分析日期、大运/流年柱、来源、覆盖标志与累计行运年数；`dayun_age` 为数值，保留引擎的 28.7 等小数 |
| 宿曜关系 | 双方姓名/月亮黄经/本命宿，双向关系、配对、整数偏移、距离与解释；命/业/胎等关系允许距离为 null |
| 知识目录/查询 | domain/category、条目数、键样例、支持能力、来源与构建信息、覆盖/缺失/回退类别、归一化查询参数、正文行列表 |
| 导出目录/解析 | technique、支持标志、可空默认设置、模板与预设/禁止章节、动态技术键下的 settings、分段序号/标题/正文/包含标志、缺失及未知章节 |
| 通用 snapshot_export | 复用完整导出 technique、settings、sections 契约到中央输出模型，避免同一导出结构在专题和直接导出工具里有不同类型 |

[覆盖清单](audits/2026-10-12/agentic-api-p2-domain-contracts/coverage.json) 记录 14 个工具键、新增 75 个模型、4 域共 192 条知识记录、53 个导出模板和 729 组有向宿曜关系。目录数量保持 89 条；REST 87、MCP 87、CLI 可执行 88。独立风水领域继续使用其既有输出模型。

## 兼容边界

- 可按对象路径裁剪的事实均可选且支持 null；数组条目维持整块输出。全部模型保留扩展字段，动态五行名/技术名仍是字典键，其值采用明确类型。
- 输出只校验、不经模型重序列化：缺省字段不补齐，原整数/浮点数、空集合、null、未知扩展和文本保持原样。数值字符串与字符串布尔值不会被自动转换为合法事实。
- 嵌套事实违规在投影前判为内部失败：REST 500、原生 MCP `isError=true`、CLI 退出 1；错误不回显违规值。兼容三端原有包络差异和 trace 传播。
- 性别未知且需要自动推导时运的既有领域失败保持：REST 400、MCP `isError=true`、CLI 退出 1。双柱均显式给定时继续允许未知性别专题；本轮不改变大运方向推导规则。
- `fields`、`strict_fields`、快照选择和 CLI 全局 `--no-metadata` 保持。发布的 schema 及 `contract_sha256` 更新属于契约版本证据，业务 JSON 不改写；源码变化后需重启进程刷新实现指纹。
- 这是稳定事实契约，不是封闭的命理解释格式，也不是业务算法正确性的重新认证。

## 验证

新增 [216 项测试](../tests/test_agentic_domain_outputs.py)：14 工具完整/裁剪三端结果、16 类违规的三端失败、20 个公开深层 schema 类型、性别/自动/部分覆盖/双柱覆盖分支、全部导出模板、全部知识条目、729 组关系、模型各层扩展保留、原数值与空距离兼容，以及未知时运方向的原错误语义。

- 本轮专项：**216 passed**，见 [日志](audits/2026-10-12/agentic-api-p2-domain-contracts/focused-pytest.txt)。
- 全目录投影：**200 passed**，见 [日志](audits/2026-10-12/agentic-api-p2-domain-contracts/projection-pytest.txt)，涵盖可投影对象、历史样例合法叶路径及三端调用。
- 当前环境全量回归：**1871 passed、89 skipped、7 warnings**，见 [日志](audits/2026-10-12/agentic-api-p2-domain-contracts/pytest.txt)。89 项跳过均要求 Linux x86_64 / Python 3.12 的黄金字节比较；历史业务快照的 Pydantic/JSON Schema 结构校验在本地实际执行。
- Python **3.10.20 / FastMCP 3.0.0** 兼容回归：**645 passed、43 warnings**，见 [日志](audits/2026-10-12/agentic-api-p2-domain-contracts/fastmcp-floor-pytest.txt)，涵盖本轮、此前 P1/P2、全目录投影和业务入口。该环境 FastAPI 为 0.143.0、Pydantic 为 2.14.1；这不是所有依赖同时取最低版本的组合。
- mypy **129 source files** 通过；Black、isort、场景 manifest 生成核验和 `git diff --check` 通过。
- [本地探针](audits/2026-10-12/agentic-api-p2-domain-contracts/probe.py) 保存中央契约/OpenAPI/原生 MCP 的深层类型核对，并通过实际 CLI 子进程验证全部 14 工具的严格投影业务 JSON。[三端结果](audits/2026-10-12/agentic-api-p2-domain-contracts/three-surface-projections.json)、[代表 schema](audits/2026-10-12/agentic-api-p2-domain-contracts/representative-output-schemas.json) 与 [源码指纹](audits/2026-10-12/agentic-api-p2-domain-contracts/source-sha256.json) 可复查。
- Wheel 构建通过；解包后确认从打包模块加载并校验本轮全部 14 工具的旧业务快照，见 [打包证据](audits/2026-10-12/agentic-api-p2-domain-contracts/wheel-verification.json)。校验使用当前依赖环境，不能代替全新依赖安装或线上部署验证。

## 发现成本

[紧凑 UTF-8 JSON 实测](audits/2026-10-12/agentic-api-p2-domain-contracts/metrics.json)：

| 入口 | 字节数 |
| --- | ---: |
| 默认 MCP tools/list，87 工具 | 3,917,610 |
| 健康场景 profile，5 工具 | 227,873 |
| REST 完整 manifest | 2,268,806 |
| 共享工具摘要 manifest | 72,801 |

默认 MCP 完整目录比上一轮增加 434,475 字节；摘要大小保持。本表是字节数，不是 token 或延迟测量。沿用现有场景/family profile、摘要发现和单工具 schema 入口，按需获取契约；未新增第二份目录或传输专用模型。

本轮验证为本地执行和原生协议测试；未提交、推送、部署，也未执行远端 Linux CI。
