# FateBridge 文档中心

这份文档主要面向三类人：集成方想了解 REST / MCP / CLI 能力和调用方式；开发者想理解仓库结构、扩展方式和测试约束；维护者想确认实现范围、精度、规则来源与未覆盖项目。

下面按常见目标列出入口，你可以直接跳到对应文档。

## 按目标找文档

- 想把服务跑起来：看 [getting-started.md](getting-started.md)
- 想用 Codex 直接体验：看 [codex-guide.md](codex-guide.md)
- 想看完整接口清单：看 [api-reference.md](api-reference.md)
- 想把 FateBridge 接进应用或 Agent：看 [agent-guide.md](agent-guide.md)
- 想保存完整 JSON 或读取超预算结果：看 [完整结果交付与同次导出](agent-guide.md#完整结果交付与同次导出)
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
- [algorithm-coverage.md](algorithm-coverage.md)：逐工具实现范围、精度、依赖与排除范围矩阵。
- [scenario-routing.md](scenario-routing.md)：按用户场景选择主证 / 旁证工具的路由矩阵。
- [development-guide.md](development-guide.md)：项目结构、开发命令、测试策略、提交流程。
- [troubleshooting.md](troubleshooting.md)：安装失败、依赖缺失、端口冲突、CORS、快照导出问题。
- [../skills/README.md](../skills/README.md)：9 个 Onda 技能；机器场景清单另含独立的 `fengshui` 基础计算路由，共 10 项。

## 风水专题

咨询从 [风水 skill](../skills/onda-fengshui/SKILL.md) 进入。选法、事实核对、规则来源和解读资料统一随 skill 保存在 `skills/onda-fengshui/references/`，按当前问题选读：

| 咨询问题 | Skill 参考资料 |
| --- | --- |
| 方法优先级、家庭人物、楼层与环境事实 | [场景与候选布局](../skills/onda-fengshui/references/scene-planning.md)、[咨询闭环](../skills/onda-fengshui/references/consultation.md) |
| 基础规则、来源层次、定宫与方位边界 | [规则与来源](../skills/onda-fengshui/references/rule-sources.md) |
| 床、桌、灶的形态观察与元素参考 | [布局规则](../skills/onda-fengshui/references/layout-rules.md) |
| 工位／合租选法、家具搬转与候选比较 | [场景与规划](../skills/onda-fengshui/references/scene-planning.md) |
| 厨卫、镜面、梁管、尖角、材质与器形 | [有来源的室内关系规则](../skills/onda-fengshui/references/sourced-interior-rules.md) |
| 玄空历史定运、二十四山与兼向替星 | [历史宅盘资料与来源](../skills/onda-fengshui/references/xuankong.md) |
| 显式启用的山水条件与当令有限解释 | [玄空有限解释](../skills/onda-fengshui/references/xuankong-interpretation.md) |
| 书桌玄空用途、入口隔挡、材料施用条件 | [工位作者规则](../skills/onda-fengshui/references/workstation-authored.md) |
| 用户明确另选的 BTB 桌面规则 | [桌面作者规则](../skills/onda-fengshui/references/surface-rules.md) |

工程接入、可运行请求与验证方法保留在 `docs/`：

- [七个工具、接口输入输出及布局验证](fengshui.md)
- [玄空三端调用、有限解释复现与独立验证](fengshui-xuankong.md)

规则和事实审查的完成状态不代表现实效力已验证。

## 推荐阅读顺序

**调用 FateBridge**

先读 [getting-started.md](getting-started.md)，再浏览 [api-reference.md](api-reference.md) 的“公共约定”和“端点家族”。如果需要按算法筛选快照内容，可以补读 [algorithm-coverage.md](algorithm-coverage.md)。

**给 Agent 接入工具**

从 [agent-guide.md](agent-guide.md) 开始，重点看自助发现、错误处理和 host 配置。需要具体工具或字段说明时查 [api-reference.md](api-reference.md) 的“FastMCP 工具面”。想理解分层设计可以看 [architecture.md](architecture.md)，遇到 MCP 相关问题去 [troubleshooting.md](troubleshooting.md)。

**修改代码或补新能力**

先读 [architecture.md](architecture.md)，再读 [development-guide.md](development-guide.md)。提交前对照 [algorithm-coverage.md](algorithm-coverage.md) 更新能力状态。

## 当前仓库边界

当前公共边界：

- 当前仓库只有 backend，不含内置前端应用。
- 默认 REST 端口是 `8010`。
- 中央目录含 88 条记录，REST / MCP / CLI 分别公开 86 / 87 / 87 项；名称和输入差异见 [三端能力边界](api-reference.md#24-三端能力边界)。
- 快照并非每个工具都支持，读取前核对 [快照覆盖](algorithm-coverage.md#4-快照协议覆盖)。MCP 超预算结果由 `result_delivery` 交付，字段投影会影响保留范围。

## 维护文档时注意

仓库保留当前使用说明、规则来源、示例与回归测试。一次性评审对话、实现快照、采集脚本和运行回执放在仓库外；`docs/reviews/` 仅供本地临时使用，不入库。历史过程记录可从 Git 历史查阅。

更新文档时建议顺手检查：

- README、docs 索引、API 文档里的端口和能力名是否一致。
- 工具是否已在 `services/catalog/` 的领域声明中配置正确 surface，并由 `services/tool_catalog.py` 装配；请求模型、代表 payload 与场景清单是否同步。常规新增不需要手写 transport 入口。
- `selected_sections`、`snapshot_export`、精度 / 依赖 caveat 是否写清楚。
- 任何“已实现 / 近似 / 占位”的说法是否能在代码里找到依据。
- 本地链接、章节锚点、示例命令与实际必填字段是否有效。完整验证流程见 [development-guide.md](development-guide.md#文档维护与验证)。
