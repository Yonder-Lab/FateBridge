# FateBridge 文档中心

这份文档主要面向三类人：集成方想了解 REST / MCP 能力和调用方式；开发者想理解仓库结构、扩展方式和测试约束；维护者想快速确认各项能力的实现状态，区分已实现、近似实现还是占位兼容。

下面按常见目标列出入口，你可以直接跳到对应文档。

## 按目标找文档

- 想把服务跑起来：看 [getting-started.md](getting-started.md)
- 想用 Codex 直接体验：看 [codex-guide.md](codex-guide.md)
- 想看完整接口清单：看 [api-reference.md](api-reference.md)
- 想把 FateBridge 接进应用或 Agent：看 [agent-guide.md](agent-guide.md)
- 想理解系统结构：看 [architecture.md](architecture.md)
- 想确认算法覆盖范围和已知限制：看 [algorithm-coverage.md](algorithm-coverage.md)
- 想知道某个用户场景该调哪几个工具：看 [scenario-routing.md](scenario-routing.md)
- 想看把工具场景化包装成技能的例子（Onda）：看 [../skills/README.md](../skills/README.md)
- 想参与开发：看 [development-guide.md](development-guide.md) 和 [../CONTRIBUTING.md](../CONTRIBUTING.md)
- 想了解住宅风水规则和适用边界：看 [fengshui.md](fengshui.md) 和 [fengshui-xuankong.md](fengshui-xuankong.md)
- 遇到了运行问题：看 [troubleshooting.md](troubleshooting.md)

## 各文档简介

- [getting-started.md](getting-started.md)：安装、环境变量、启动 REST / MCP、发起第一条请求。
- [agent-guide.md](agent-guide.md)：三端接入、自助发现、错误/投影/快照处理、host 配置，以及 Python / JS 示例。
- [api-reference.md](api-reference.md)：REST 路由、FastMCP 工具、请求族、快照协议。
- [architecture.md](architecture.md)：代码分层、数据流、设计决策和扩展路径。
- [algorithm-coverage.md](algorithm-coverage.md)：已实现、近似、占位、排除范围矩阵。
- [scenario-routing.md](scenario-routing.md)：按用户场景选择主证 / 旁证工具的路由矩阵。
- [development-guide.md](development-guide.md)：项目结构、开发命令、测试策略、提交流程。
- [troubleshooting.md](troubleshooting.md)：安装失败、依赖缺失、端口冲突、CORS、快照导出问题。
- [../skills/README.md](../skills/README.md)：把工具按用户场景重组为 8 个 Onda 技能。

## 推荐阅读顺序

**调用 FateBridge**

先读 [getting-started.md](getting-started.md)，再浏览 [api-reference.md](api-reference.md) 的“公共约定”和“端点家族”。如果需要按算法筛选快照内容，可以补读 [algorithm-coverage.md](algorithm-coverage.md)。

**给 Agent 接入工具**

从 [agent-guide.md](agent-guide.md) 开始，重点看自助发现、错误处理和 host 配置。需要具体工具或字段说明时查 [api-reference.md](api-reference.md) 的“FastMCP 工具面”。想理解分层设计可以看 [architecture.md](architecture.md)，遇到 MCP 相关问题去 [troubleshooting.md](troubleshooting.md)。

**修改代码或补新能力**

先读 [architecture.md](architecture.md)，再读 [development-guide.md](development-guide.md)。提交前对照 [algorithm-coverage.md](algorithm-coverage.md) 更新能力状态。

## 当前仓库边界

为了避免和旧文档产生歧义，这里明确三点：

- 当前仓库只有 backend，不含内置前端应用。
- 默认 REST 端口是 `8010`。
- 大量工具会同时返回 `snapshot_text` 和 `snapshot_export`，这已经属于公共约定的一部分。

## 维护文档时注意

更新文档时建议顺手检查：

- README、docs 索引、API 文档里的端口和能力名是否一致。
- 工具是否已在 `services/tool_catalog.py` 声明正确 surface，请求模型、代表 payload 与场景清单是否同步；常规新增不需要手写 transport 入口。
- `selected_sections`、`snapshot_export`、精度 / 依赖 caveat 是否写清楚。
- 任何“已实现 / 近似 / 占位”的说法是否能在代码里找到依据。
- 本地链接、章节锚点、示例命令与实际必填字段是否有效。完整验证流程见 [development-guide.md](development-guide.md#文档维护与验证)。

## 审计记录

2026-10-12 的 [Codex 用户体验修复](codex-experience-2026-10-12.md)记录安装诊断、真实 stdio 调用、发现与 CLI 使用、文案修复及验证边界。

2026-10-13 的 [Codex MCP 与真实对话验收](codex-mcp-dialogue-2026-10-13.md)记录桌面原生接入、自动选工具、缺资料追问和最终解读的实际多轮验证。

[audit-repairs-2026-10-09.md](audit-repairs-2026-10-09.md) 是 2026-10-09 工作区代码修复的历史记录，包含本地证据与未验证边界，不代表这些更改已经发布。文档审查记录见 [documentation-audit-2026-10-09.md](documentation-audit-2026-10-09.md)。

2026-10-12 的[代码与文档清理验收](cleanup-validation-2026-10-12.md)记录合同缓存、内部导入及测试迁移的范围、性能和完整回归。原始审计资料保留供复核；每份记录只适用于其明确标识的源码快照和环境。

2026-10-12 的其他后续记录：[Agent 契约修复](agentic-api-fixes-2026-10-12.md)、[领域合同验收](agentic-api-p2-domain-contracts-fixes-2026-10-12.md)、[投影回归](output-projection-fix-2026-10-12.md)、[独立 Linux / CI 快照](agentic-api-linux-ci-validation-2026-10-12.md)。

2026-10-12 的[代码内聚与耦合审查](code-structure-review-2026-10-12.md)记录应用层/协议注册拆分、共享出生上下文、占星基础表与依赖边界验证。

后续[星盘与时运结构整理验收](astro-timing-structure-validation-2026-10-12.md)记录本命/关系盘、时间层状态、快照、日历查询和公共命盘响应的职责拆分与回归证据。

[低优先级热点整理验收](request-catalog-helpers-validation-2026-10-12.md)记录请求模型、领域工具声明与中央装配、出生输入/太阳时/展示等公共工具的职责划分和回归证据。

2026-10-13 的 [Codex MCP 根因定位与优化](codex-mcp-root-cause-2026-10-13.md)记录了 Schema 传输、发现流程、宿主生命周期和角色边界的后续优化。

[旧入口与兼容层清理验收](legacy-entry-cleanup-validation-2026-10-13.md)记录已删除的历史模块、Python 包装与旧 REST/CLI 入口，列出正式迁移路径和回归证据。
