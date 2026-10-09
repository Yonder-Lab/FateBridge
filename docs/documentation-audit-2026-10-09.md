# FateBridge 文档审查记录

日期：2026-10-09。范围：根目录说明、`docs/` 用户/开发文档、Onda 场景说明与共用引擎参考。以本轮工作区实际代码为准，包括原有算法/接口修复；历史审计记录保留。本轮只修改文档，没有改动算法、请求模型或测试。

## 修正内容与依据

| 问题 | 修正 | 代码/验证依据 |
| --- | --- | --- |
| API Key 已实现，安全文档仍声称无鉴权 | 说明默认关闭、配置格式、启动拒绝、免检路径和各端边界 | `api.py`、`utils/runtime.py` |
| 把各端能力理解为同名同形 | 区分 82 条目录、80 REST、80 MCP、81 CLI；说明 legacy 与嵌套关系盘绑定 | `services/tool_catalog.py`、`core/tool_spec.py` |
| `/api/calculate` 等同 `analyze_destiny` | 新入门推荐 `bazi_birth`，说明扁平兼容与综合分析不同 service | catalog 绑定与实际响应 |
| REST 投影写成不支持，错误仍示例 `detail` | 补查询投影、快照开关、顶层错误及 400/422 区分、504 与协议拒绝 | 注册器、HTTP/MCP/输出对齐测试 |
| 参数摘要当完整 schema，默认 UTC/太阳时描述过时 | 说明 OpenAPI / MCP schema 与各模型默认值、必填小时、显式/缺省经度策略 | request models、helpers、schema discovery |
| 快照覆盖一概宣称双层，示例显式太阳时缺地点 | 按实际输出分三类，区分导出存在与参数支持；为 REST/Python/JS 示例补地点 | 全部 80 REST 代表结果与具体 HTTP 调用 |
| runtime 可用误写成精度已保证 | 区分 `.se1`、Moshier、轨道近似、backend 缺失，补实际模型检查和数据路径 | ephemeris runtime、run metadata、fetcher |
| 架构路径、注册关系和请求流过时 | 重绘声明/注册/执行路径；加入线程池、共享星历锁与溯源边界 | tool spec、API、services、ephemeris runtime |
| src 布局仍写“无需安装”、MCP host 只用相对解释器 | 统一安装环境、进程配置加载、stdio 与绝对解释器路径 | pyproject、CLI、runtime、MCP 入口 |
| 贡献指南重复过长、主分支和发布流程冲突 | 精简至实际流程，统一 master；说明 CI/floor/golden 与 Release 发布 | workflows、版本常量、golden runner |
| 技能说明与自身调用纪律矛盾 | 修正无时盘、错误 flag、缺 backend 回退、梅花必填时间、重复命盘/时运及失效节号 | 模型与技能合同；保持机器工具集合不变 |
| 紫微示例虽退出成功，导出实际为空 | 改用真实 `宫位总览`，说明空格分隔与宫名不等于 section；检查实际选择结果 | CLI `selected_sections` / `missing_selected_sections` / `export_text` 回显 |
| 把多体系一致当作预测已验证 | 改为标注来源的文化视角对照，保留分歧与输入误差 | 与套件既有文化参考边界一致 |

## 验证

本节在检查结束后记录当前实测结果，不沿用历史审计的测试数字。

本地 Python 3.13 环境执行以下现有测试：

```bash
python -m pytest -q tests/test_doc_tool_counts.py tests/test_scenario_routing_coverage.py \
  tests/test_skills_interface_contract.py tests/test_skills_engine_contract.py \
  tests/test_output_shaping_parity.py tests/test_http_audit_repairs.py \
  tests/test_mcp_audit_repairs.py
git diff --check
```

结果：**58 passed，5 warnings**。其中技能合同实际执行了 **27 条具体 CLI 示例**。警告来自现有 Kerykeion、Starlette TestClient 与 Pydantic 依赖/Schema 行为，本轮未改相关代码。

另做以下直接复核：

- 26 份 Markdown 的代码围栏、171 处本地文件/章节链接检查通过；外部网站链接未逐一联网验证。
- 主文档 15 条 CLI 示例调用均成功；13 条 HTTP 示例通过本地 FastAPI TestClient，9 个 JSON 代码块可解析。
- 全部 80 个 REST 代表请求经目录/服务执行均无业务错误：52 个返回双层快照、23 个仅文本快照、5 个仅结构化数据。该数字是代表请求的输出检查，不是所有参数组合的证明。
- 直接比较 `bazi_birth`、`calculate_legacy` 与 `analyze_destiny` 的业务层级，验证新命盘嵌套结构和旧扁平结构；结合绑定代码确认综合分析不是旧 REST 的同一个 service。
- 紫微示例修正后，`selected_sections=["宫位总览"]`、`missing_selected_sections=[]`，导出正文非空。

本轮验证为本地文档/接口/CLI 检查，没有触发远端 CI、重新生成 Linux 黄金基线、测试 GUI MCP host 或发布服务。历史审计的修复与测试结果另见 [代码审计记录](audit-repairs-2026-10-09.md)。
