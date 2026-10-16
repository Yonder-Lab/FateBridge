# 工位 P0–P2：Linux 验证与独立提交

日期：2026-10-16（Asia/Shanghai）。本记录衔接[上一阶段实现与复审](fengshui-workstation-p012-validation-2026-10-15.md)。来源与规则范围见[工位作者规则](../../skills/onda-fengshui/references/workstation-authored.md)，研究原始登记保留在同目录。

## 提交边界

执行本轮请求时，主工作区已经干净，P0–P2 已与其他咨询技能改写、资料迁移及审查归档一起包含在远端 `0c68ae1709aa21185b64a8e938c83ef1592ae1fd`。本轮没有回退或改写该历史，也没有把它重新作为“仅 P0–P2”的提交推送。

独立交付分支 `codex/fengshui-p012-linux` 从其父提交 `e606e6dfc0132f952b32dd17012f02238b1e8adb` 重建，只保留工位实现、数据、来源、例子、对应测试及最小接入文档。P0 所依赖的“已有依据可解释／执行状态独立”合同及对应风水回归一并保留；其他场景技能改写、通用咨询资料迁移、命理文案变化和 `docs/reviews/` 的大量归档均排除。

独立提交阶段保留了原有 `master`、其他分支及工作区。后续按用户 merge 指令将独立分支历史并入 master；已发布功能不重复实现，master 上的技能资料迁移及其他改动保持。P3 继续是 `reference_only`，`placement_rules_enabled=false`，没有新增固定吉位、手机方向、龙虎高低、物件数量或水晶球摆放规则。

## 独立分支验证

验证的是暂存树 `ecc0f0bcea9e2c407af66547ead755e49db2ddbb` 的归档，SHA-256 为 `0f989f5a55e09245e91f3f09917bc1a02ae069b9ae0b73d695a7675225de6067`。此后只新增本次验证记录，不修改经过验证的实现、测试、规则数据、生成合同或路由。

Linux 环境为 x86_64／Python3.12.11／glibc2.35（独立临时 venv），符合仓库 golden 平台门槛；没有设置 `FATEBRIDGE_SKIP_GOLDEN_DIFF`。依赖版本与结果散列见[机器可读回执](fengshui-workstation-linux-validation-2026-10-16.json)。

- `python -m scripts.audit_linux_golden`：**87/87 匹配**，没有缺失或过时快照，基线未修改。
- 完整 `python -m pytest -q -rs`：**3209 passed，0 failed，0 skipped**，耗时217.10秒。
- 定向工位／状态／关系／三端合同：本地170项通过，包含49项新增工位测试。
- Black、isort、mypy（213源文件）、Codex生成合同检查、场景manifest检查及 `git diff --check`：全部通过。
- 新增输入的 REST／原生MCP／CLI成功和失败、严格投影、默认预算下的同一次结果读取及三个实际 CLI 子进程例子均由工位合同测试覆盖；没有用重新计算代替结果读取。

独立归档验证前后的文件散列逐项对照；原始日志和JUnit回执保存在 `/Users/thomas/.codex/backups/fatebridge-p012-linux-20261016/`。提交只增加本节说明和机器回执，不把临时虚拟环境、安装日志、运行脚本或整套审查输出加入仓库。

## 已发布版本的补充证据

另对冻结的 `0c68ae1` 做了独立 Linux/Python3.12 验证：**3214 passed，0 skipped**，golden **87/87**，源码归档1073项文件验证前后未变化。

该已发布提交的[托管CI](https://github.com/Yonder-Lab/FateBridge/actions/runs/38840864662)也已核对：Ubuntu24.04／Python3.12完整3214项通过，Python3.10、3.11、3.13及最低依赖作业全部通过。这些是已发布混合提交的证据，和上面的独立分支验证分开记录。

首次独立环境启动时，审查脚本通过文件路径执行导致本地 `tests` 包不在导入路径；改用原文档建议的 `python -m scripts.audit_linux_golden` 后通过，没有更改项目源码或快照来绕过失败。此启动失败日志保留在归档中。

这些结果证明本次实现和传输合同的回归检查通过，不代表新Desktop会话或真实空间的效果已验收。

## 合并核对

合并基线为 `0c68ae1`，独立分支头为 `2fbceac`。重复的文档说明和生成清单按 master 的现有版本解决，保留资料迁移后的路径。相对于合并前 master，`src/`、`tests/`、`scripts/`、`skills/`、AGENTS 及 CI 配置均保持字节一致；最终内容差异仅为两份 Linux 验证回执和原阶段记录的后续链接。合并采用双父提交保留两条历史，不重写原提交。
