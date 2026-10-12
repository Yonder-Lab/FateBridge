# Ruleset 点路径投影修复与全目录检查

修复 `fengshui_directions(fields=["layers.directions.ruleset.version"])` 成功结果被原生 MCP 客户端拒绝的问题。原输出 schema 将 `Ruleset` 的八个字段全部列为必填；投影只保留一个字段后，服务返回 `isError=false`，但 SDK 校验 `structuredContent` 时抛出 `RuntimeError`，即使 `raise_on_error=False` 也无法消费结果。

`core/fengshui/output.py` 中八个字段现在支持缺省，仍严格校验已提供字段的类型。模型仅校验，不重序列化响应，不补 null，不删除扩展，不改写计算结果。规则来源、规则版本和黄金样例没有修改；运行元数据的 `contract_sha256` 根据修正后的 schema 自然变化。

## 系统检查范围

- 当前中央目录的 89 个工具，包含共享西方占星、中国术数、风水及动态字典值的嵌套输出。
- 首次修复时沿 `$ref`、对象属性、字典值和组合 schema 检查可投影对象，共 3,268 个对象位置（按各工具展开计数），未发现其他兄弟字段必填冲突；随后新增领域模型也已纳入 Linux 完整复核。
- 89 个工具的既有黄金业务样例，共 21,751 个合法叶路径，逐一按严格模式投影并执行 Pydantic 与 JSON Schema 校验。关系盘的 REST/MCP 别名复用同一黄金样例。黄金样例会去除不完整的规范化 `run_metadata` 后校验业务字段；实时元数据在三端调用中另行校验。
- REST OpenAPI、REST 工具目录、CLI `describe` 与原生 MCP `tools/list` 的已发布 schema，按实际注册的各端入口检查。没有将 REST 兼容入口当成同名 MCP 工具。

数组、标量及 null 只能整块选择。`RuleSource` 只作为 `sources` 数组条目出现，保留来源记录必填事实；它不受对象点路径裁剪。`run_metadata` 始终完整保留，也继续要求基础回执字段。回归检查明确区分这两种情况与可裁剪业务对象。

## 原生客户端与三端验证

新增 `tests/test_output_projection_contracts.py`，使用实际 `fastmcp.Client(app)` 的原生 MCP 会话，不绕过客户端输出 schema 校验。测试覆盖：

- 七个住宅工具及合参的八宅、金锁、年度飞星和玄空宅盘各层，逐一投影每个 `Ruleset` 字段；共 80 个工具/层/字段组合，再分别验证 CLI 默认元数据与全局 `--no-metadata`，合计 160 组三端调用。
- REST 状态、MCP `isError`、CLI 退出码，完整业务 JSON 的精确相等，原生 MCP 文本与 `structuredContent` 一致，部分结果可通过模型及原生公开 schema 校验。
- 已提供的字段类型仍受约束；拼写错误与数组索引路径在宽松模式返回一致警告，在严格模式返回一致校验问题。
- 既有 `test_agentic_nested_outputs.py` 等测试继续验证其他专业嵌套结果的原生 MCP 三端投影与错误处理。

另用独立 CLI 进程执行审查报告中的单字段请求，与 REST TestClient 和原生 MCP 会话比对，三个入口均成功，业务 JSON 一致。

## 复跑

此前 macOS 相关回归测试：431 passed；其中新增投影合同文件包含 200 项测试。当时全仓结果：1,653 passed、89 skipped、0 failed；89 项均为参考平台专用检查。随后 [Linux 参考环境完整复核](output-projection-linux-validation-2026-10-12.md) 已补齐这些检查，最新全仓 **1,960 passed、0 failed、0 skipped**，88 份 golden 全部逐字节匹配，并修复 MCP SDK 2.x 的原生结果构造类型兼容问题。

首次全仓运行的文档示例子进程误用了未安装 FateBridge 的系统 Python 3.14。将项目虚拟环境加入 PATH 后，文档示例 5 项通过，再按下方命令完整复跑通过；无需修改业务代码或系统 Python。

```bash
.venv/bin/python -m pytest -q tests/test_output_projection_contracts.py
.venv/bin/python -m pytest -q tests/test_output_projection_contracts.py tests/test_agentic_nested_outputs.py tests/test_agentic_contracts.py tests/test_agentic_p2.py tests/test_fengshui_surfaces.py tests/test_output_shaping_parity.py
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q
.venv/bin/python -m black --check tests/test_output_projection_contracts.py src/fatebridge/core/fengshui/output.py src/fatebridge/core/output_base.py
.venv/bin/python -m isort --check-only tests/test_output_projection_contracts.py src/fatebridge/core/fengshui/output.py src/fatebridge/core/output_base.py
.venv/bin/python -m mypy src/fatebridge/core/fengshui/output.py src/fatebridge/core/output_base.py
git diff --check
```

本轮本地环境：Darwin arm64 / Python 3.13，FastMCP 3.4.2、MCP SDK 1.28.0、Pydantic 2.13.4。范围为本地真实协议会话、REST TestClient 与 CLI，不代表部署服务或外部 Agent host 验收。黄金业务样例的投影校验跨平台运行，与 Linux/Python 3.12 的完整 golden 字节比对是不同检查。
