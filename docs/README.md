# FateBridge 文档中心

本目录面向三类读者：

- 集成方：想知道有哪些 REST / MCP 能力、如何调用、返回什么
- 开发者：想理解仓库结构、扩展方式、测试约束
- 维护者：想快速确认哪些能力是已实现、近似实现、占位兼容

## 从哪里开始

### 我想先把服务跑起来

- [GETTING_STARTED.md](GETTING_STARTED.md)

### 我想看完整接口清单

- [API.md](API.md)

### 我想把 FateBridge 接进应用或 Agent

- [AGENT_GUIDE.md](AGENT_GUIDE.md)

### 我想理解系统结构

- [ARCHITECTURE.md](ARCHITECTURE.md)

### 我想确认算法覆盖范围和 caveat

- [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)

### 我想参与开发

- [DEVELOPMENT.md](DEVELOPMENT.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)

### 我遇到了运行问题

- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 文档地图

| 文档 | 适合谁 | 主要内容 |
| --- | --- | --- |
| [GETTING_STARTED.md](GETTING_STARTED.md) | 新用户、集成方 | 安装、环境变量、启动 REST / MCP、第一条请求 |
| [AGENT_GUIDE.md](AGENT_GUIDE.md) | Agent / 开发者 | 三端接入、自助发现、错误/投影/快照、host 配置、Python/JS 示例 |
| [API.md](API.md) | 前后端/Agent 集成方 | REST 路由、FastMCP 工具、请求族、快照协议 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 开发者、架构师 | 代码分层、数据流、设计决策、扩展路径 |
| [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md) | 维护者、评审者 | 已实现 / 近似 / 占位 / 排除范围矩阵 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 贡献者 | 项目结构、开发命令、测试策略、提交流程 |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | 所有人 | 安装失败、依赖缺失、端口冲突、CORS、快照导出问题 |

## 建议阅读路径

### 路径 1：我要调用 FateBridge

1. 先读 [GETTING_STARTED.md](GETTING_STARTED.md)
2. 再看 [API.md](API.md) 的“公共约定”和“端点家族”
3. 如需筛选快照内容，补读 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md)

### 路径 2：我要给 Agent 接入工具

1. 先读 [AGENT_GUIDE.md](AGENT_GUIDE.md)（自助发现、错误处理、host 配置）
2. 需要逐工具/字段细节时查 [API.md](API.md) 的 “FastMCP 工具面”
3. 想理解分层再看 [ARCHITECTURE.md](ARCHITECTURE.md)，遇到问题看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 的“MCP 相关问题”

### 路径 3：我要修改代码或补新能力

1. 先读 [ARCHITECTURE.md](ARCHITECTURE.md)
2. 再读 [DEVELOPMENT.md](DEVELOPMENT.md)
3. 提交前对照 [ALGORITHM_COVERAGE.md](ALGORITHM_COVERAGE.md) 更新能力状态

## 当前仓库边界

为避免继续被旧文档误导，这里明确三点：

- 当前仓库是 backend-only 仓库，不含内置前端应用
- 当前实际默认 REST 端口是 `8010`
- 大量工具会返回 `snapshot_text + snapshot_export`，这已经是公共合同的一部分

## 维护规则

更新文档时建议同步检查：

1. README、docs 索引、API 文档里的端口和能力名是否一致
2. `fatebridge/api.py` 与 `fatebridge/mcp_server.py` 是否都已经补齐对应入口
3. `selected_sections`、`snapshot_export`、精度/依赖 caveat 是否写清楚
4. 任何“已实现/近似/占位”的说法是否能在代码里找到依据
