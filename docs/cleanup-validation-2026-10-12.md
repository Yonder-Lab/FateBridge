# 代码与文档清理验收（2026-10-12）

依据本轮[系统审查](audits/2026-10-12/cleanup/review.md)，按合同缓存、低风险清理、测试与内部导入迁移的顺序推进。受测对象为当前未提交工作区，包含此前已存在的契约及风水实现；具体源码由[文件哈希](audits/2026-10-12/cleanup/source-hashes.json)标识，不能把其他 PR / CI 的通过结果套用到本轮。

## 完成的清理

- `core/schema_cache.py` 对默认模型 Schema 和合同 SHA-256 分别提供 256 条的有界缓存。键包含真实模型类、保持存活的 core schema 身份，避免同名模型及对象 id 重用串缓存；重建模型自动失效，公开字典深拷贝，失败不缓存，并发冷调用只生成一次。动态 Schema hook / 配置或未重建根模型的嵌套变化需显式清缓存。输入、业务结果与 execution receipt 仍逐次计算。
- discovery、MCP 输出 Schema 和 receipt 合同摘要复用缓存。保留领域输出与 receipt 附加后的两道校验，去掉 REST 第三次重复校验；严格投影及错误分类保留。
- 原生 MCP 从同一响应字典生成 structuredContent 与 text JSON，省去文本反解析。旧 `.fn` 文本接口在注册时同步建立，不再在模块导入时调用 `asyncio.run` 或开启线程。历史自定义 registrar 的文本回调仍由兼容适配器支持。
- REST Python 别名引用实际挂载 endpoint，消除重复创建。生产和测试导入迁到 errors / places / house_systems / timezones、请求模型及 predictive 定义模块；predictive 子模块和公共聚合入口改为明确导入。聚合入口保留历史导出，内部不再依赖 helpers 转导出。
- 测试通过实际注册 REST endpoint、原生 FastMCP Client 调用及共享执行层验证，保留线程池／并发、错误、默认值和三端对齐覆盖；旧 Python 出口由专门兼容测试守护。移除每份测试文件的路径注入，CLI 文档示例绑定测试解释器并按参数执行。
- 删除旧 `iztro-verify` extra，保留实际使用的依赖与 Kerykeion 5 上限；紫微亮度独立验证仍使用固定版本 JS iztro 资料。删除无用导入、私有未用参数、不可达的兼容错误转发及重复导出章节映射；更新生成脚本说明、架构／开发文档、文档索引和 CHANGELOG。

## 保持的行为与边界

CATALOG 89、REST 87、MCP 87、CLI 88，工具名称、请求参数、公开错误和投影约定保留。保留 helpers 的 22 个历史出口、API 44 个请求模型出口、17 个 REST Python 别名和 87 个 MCP Python 工具出口；旧 `/api/calculate`、relationship mode 别名及导出标题兼容规则继续生效。

没有修改核心历法、八字、紫微、式占或占星计算。核心算法函数／类 AST 核查无额外变更；配合度私有函数仅去掉未使用参数及相关说明／删除语句，原建议分支与返回一致。未修改 88 份黄金基线。[结构核查](audits/2026-10-12/cleanup/integrity.json)记录无星号导入、无测试路径注入及无内部兼容 helper 消费。

大型模块重构、传统配合度策略统一、公开旧入口退役和历史审计证据删减仍需独立迁移方案，本轮保留。清理前已保存 589 文件的恢复 ZIP 和逐文件哈希，路径见[范围记录](audits/2026-10-12/cleanup/scope.json)；既有未提交工作保留。

## 验证

同一 macOS / Python 3.13 环境冻结时钟，修改前后 **88 份业务 JSON 逐字节一致**，完整 discovery 合同按 JSON 内容一致，发现体积仍为 2,268,806 UTF-8 字节。[比对结果](audits/2026-10-12/cleanup/before-after.json)。另外验证了缓存副本隔离、模型覆写／重建、冷并发、失败重试、逐次输入／输出摘要、旧 Python 出口及事件循环内安全导入。

全部 **89 个工具的缓存合同摘要与原未缓存公式一致**，见[逐工具核对](audits/2026-10-12/cleanup/contract-fingerprints.json)。最终再次核对 369 个执行文件，当前源码与 Linux 受测快照一致；[执行文件哈希](audits/2026-10-12/cleanup/execution-hashes.json)与文档／历史证据哈希分开记录。

| 完整回归环境 | 通过 | 失败 | 跳过 | 日志 / JUnit |
| --- | ---: | ---: | ---: | --- |
| macOS ARM64 / Python 3.13.5 | 1882 | 0 | 89 | [日志](audits/2026-10-12/cleanup/local-full.log) / [JUnit](audits/2026-10-12/cleanup/local-full.xml) |
| Linux x86_64 / Python 3.12.3 | 1971 | 0 | 0 | [日志](audits/2026-10-12/cleanup/linux-full.log) / [JUnit](audits/2026-10-12/cleanup/linux-full.xml) |
| macOS ARM64 / Python 3.10.20 / FastMCP 3.0 下限 | 1882 | 0 | 89 | [日志](audits/2026-10-12/cleanup/floor-full.log) / [JUnit](audits/2026-10-12/cleanup/floor-full.xml) |

FastMCP 下限全量执行后，最后迁移的两份测试又在同一环境补跑 30 项，全部通过；生产执行代码与最终快照一致。这组仅验证 FastMCP 3.0 下限，其他依赖为已安装版本，不等同于 CI 的 `--resolution lowest-direct` 作业。依赖版本见[本地环境](audits/2026-10-12/cleanup/local-environment.json)、[FastMCP 下限环境](audits/2026-10-12/cleanup/floor-environment.json)和[Linux 黄金报告](audits/2026-10-12/cleanup/linux-golden.json)。Linux 镜像固定为 `sha256:78e70cc82ced587f39e7cd2dfb27a41cbcb5d458871acbc25e10029755a2931e`，FastMCP 4.1.0 / MCP SDK 2.3.0；本地分别覆盖 FastMCP 3.4.2 和下限 3.0.0。

Linux 使用真正的 x86_64 / Python 3.12 固定镜像、只读源码、禁用网络，不设置跳过黄金条件，也不重新冻结基线。独立黄金核验 **88/88 匹配**、零差异／缺失／陈旧样例，完整测试另验证两次输出确定性及模拟时钟变化。macOS 的 89 项平台跳过不能作为 Linux 黄金验收通过。

Black / isort（252 文件）、mypy（130 源文件）和 `git diff --check` 通过。文档与技能检查 27 项通过；39 份 Markdown 的 343 个本地链接／锚点检查零错误。原始日志与[验证汇总](audits/2026-10-12/cleanup/validation.json)保留。本轮临时恢复已停止的 Colima profile 执行核验，结束后恢复停止状态；Docker context 保持 `default`。

## 本地性能探针

| 探针（热缓存） | 清理前 | 清理后 |
| --- | ---: | ---: |
| `gua_lookup` 单次总耗时中位数 | 5.606 ms | 0.151 ms |
| `bazi_birth` 单次总耗时中位数 | 13.146 ms | 1.066 ms |
| `fengshui_directions` 单次总耗时中位数 | 9.285 ms | 0.275 ms |
| 完整 discovery 三次耗时中位数 | 788.484 ms | 53.333 ms |

数据来自同机、相同依赖的代表 payload，各执行探针取五次中位数，discovery 取三次；这是本地探针，不能当作线上 SLA 或负载压测。原始数据：[清理前](audits/2026-10-12/cleanup/performance-before.json)、[清理后](audits/2026-10-12/cleanup/performance-after.json)，附[探针代码](audits/2026-10-12/cleanup/performance-probe.py)。REST 输出校验由三次降至两次，MCP 保持两次；文本与结构化输出一致，事件循环内导入的 coroutine 警告已消除。

本轮没有提交、推送、合并或部署，不声称托管 CI、远端服务或 GUI MCP 宿主已验证本轮源码。
