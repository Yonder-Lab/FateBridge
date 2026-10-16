# 工位风水 P0／P1／P2 实现与复审记录

> 本文保留2026-10-15工作区实现阶段的历史记录；后续Linux验证与独立提交见[2026-10-16记录](fengshui-workstation-linux-release-2026-10-16.md)。

日期：2026-10-15（Asia/Shanghai）。基线提交：e606e6d。本轮为当前工作区实现与本地验证，未提交、推送或部署。

用户授权：按[系统调研](fengshui-workstation-gap-research-2026-10-15.md)落实 P0、P1、P2；P3 仅作者参考；保留原有改动，补来源／文档／测试，核对 REST／MCP／CLI，并完成复审。来源清单的历史研究结论保持原记录，生产采用范围另见[工位作者规则](../../skills/onda-fengshui/references/workstation-authored.md)。

## 实现范围

| 阶段 | 本次交付 | 明确边界 |
| --- | --- | --- |
| P0 | WOFS／Joey Yap 尖角异议、物件路线异议、材料覆盖理由；资格／条件／目标／行动分开；补署名、定位和实际取得的散列 | 原 WOFS 提醒不自动取消；不称全派共识；未实现的规则不产生事实追问 |
| P1 | 显式 workstation_activity_authored_v1；工作／学习按已确认落宫读取实际宅盘向星角色，保留同宫山星、元素关系及各测量候选 | 不改起盘；不以坐向替代落宫；不由水星推真实水装置；不生成综合吉凶或排名；旧 xuankong_conditioned_v1 桌未覆盖回执保留 |
| P2 | afsi_entry_barrier_v1 独立入口—坐者—隔挡关系；afsi_application_conditions_v1 的水／金属／活植物条件及可选实际元素目标绑定 | 三端与材料条件逐项有证据；执行条件不阻塞普通解释；材料条件通过不等于足量、位置有利、可以执行或有效 |
| P3 | 带 W1 来源的 non_btb_desktop_reference | placement_rules_enabled=false；无罗盘桌面坐标算法；不启用电话／手机、水晶球、龙虎高低、固定数量或新的吉位规则 |

四个新规则集（另含 workstation_source_boundaries_v1）均为 1.0.0；数据位于 `src/fatebridge/data/fengshui/workstation-authored-v1.json`。11 个实际采用的来源 ID 均可回溯至研究登记。声明了字节散列的来源已逐项与本轮下载文件核对；工具托管正文而未保存原始字节的文章不声称散列。

AFSI《The Principles of Feng Shui》本轮直接取得 4,418,704 字节原 PDF，SHA-256 为 `6ab5135060df281fd6a6e376e0516e660c185dd2af2f146a5f850df64cc3b024`，与原记录相同。修正一基 PDF 页码：第三章印刷19–28对应 PDF36–45；材料重点印刷23、25对应 PDF40、42。FS305 的入口图与 FS227 的材料条件保留各自教材定位，不从图示造数值距离或重量阈值。

## 公共合同与兼容

- 沿用 `fengshui_assess`，未新增传输专用计算器。工位输入在 `environmental_context.workstation_review`，材料条件在 `material_facts[].application`；每项新作者规则必须显式选 `ruleset_id`。
- 共享模型检查实际书桌、实际入口、独立隔挡、唯一关系、严格布尔与证据；未知引用、互相矛盾的事实、错误材质条件或借搬位改材料／用途会被拒绝。
- 新输出为 `layout_analysis.workstation_analysis` 及材料中的 `application_analysis`，支持严格投影；规则集与逐条追踪同时交付。不提交新分支时不增加其计算或规则。
- 评价运明确独立于历史宅运、年度及系统日期；搬位候选可以沿用同次明确查询评价运，但不能更换它，也不能沿用旧位置／旧入口关系。
- 候选移动入口、书桌或隔挡任一端均需新核对同一三端关系；换成另一条关系不能抹掉原项。旧材料施用观察不能无声丢失。同一隔挡的执行阻碍与未知条件会传递到候选状态。
- 材料绑定只引用同轮实际算出的 `element_adjustments.request_id`，对照实际 `introduced_element`；不证明材料物件已位于目标宫。候选未重算目标时保留缺失，不复制现状目标。
- 新增可读快照说明；默认响应预算超限时通过原 `result_delivery` 读取同一 run，未重算或丢弃作者与候选数据。

三个可运行虚构请求：[玄空活动](../examples/fengshui-workstation-activity.json)、[入口隔挡](../examples/fengshui-entry-barrier.json)、[材料条件](../examples/fengshui-material-application.json)。咨询资料沿用工作区正在进行的 skill references 迁移，相关入口、来源与例子已链接；没有恢复被迁移的旧 docs 文件。

## 验证

- 新增 `tests/test_fengshui_workstation_authored.py` 共49项：八方位置与坐向变换、未知／已知未覆盖用途、混用、照片候选、评价运、多个宅盘候选、人物资料隔离、三端重核、不同动作许可、执行条件独立性、材料未知／不符合／目标绑定、来源索引、P3关闭，以及三端成功／失败／严格投影与同次结果交付。
- 新规则与 `test_agentic_replay.py` 联合回归：81 passed。
- 三个例子另通过真实 CLI 子进程执行，新增分支、规则集与逐条追踪和共享计算一致。协议测试使用实际 FastAPI TestClient、FastMCP Client 与 CLI 入口，不只比较服务函数。
- `black --check src/fatebridge scripts tests`、`isort --check-only src/fatebridge scripts tests`、`mypy src/fatebridge/`（213源文件）及 `git diff --check` 通过。
- `build_codex_call_contracts.py --check` 与 `build_scenario_manifest.py --check` 通过；AGENTS 生成合同通过脚本更新。14份相关 Markdown 的本地链接均有效。
- 最终全仓回归：**3124 passed，88 skipped，0 failed**，耗时221.38秒；跳过的1项 golden runner 与87项 golden master 都要求 Linux-x86_64／Python3.12，当前为 Darwin-arm64／Python3.13。

首轮全仓在代码／数据仍被更新时出现两项运行环境散列不一致：3112 passed、88 skipped、2 failed，业务输出一致。停止修改实现后，两项连同回放套件复跑通过。保留此次失败说明，不将它隐藏为一次通过；最后全仓结果采用固定实现后的轮次。

本地为 macOS／Python3.13。平台限定的 Linux golden、托管 CI、新连接 Desktop 会话及实际现场效果不由这些测试证明。

## 复审修正

1. 材料条件明确不符合时结束该项施用判断，不为填满清单继续索取未知观察；材料身份未知保留 needs_material_confirmation，不能误当作者排除。
2. 植物存活照片候选不当成已确认事实，避免与独立健康观察构成伪冲突；真正确认死亡与确认健康仍拒绝矛盾。
3. 候选的工位规则比较曾误归为材料方法，已按活动／入口规则单独标注；保持实际来源与作用域。
4. 候选上已确认的通行阻碍，或同一隔挡执行条件未知，分别阻止 blocked／conditional_option 被误写为 ready；普通关系与用途解释仍可给出。
5. 评价运沿用明确查询事实，几何和关系重新观察；既不暗补当前运，也不让搬位悄悄改查询运。
6. 新规则复用实际宅盘、既有五行运算与通用约束，不根据某张照片、某个物件名、某人资料或指定星数硬编码建议。

## 工作区保留

开始时已有改动及研究文件已记录在 `/tmp/fatebridge-p012-baseline-20261015/`。本轮没有 reset、restore、stash、切分支或自动提交，原有解释／执行状态修订及其他技能资料改动保留。全仓验证覆盖当前合并工作区，不把其他任务的技能迁移和命理文案变更列为本次新增能力。

最终源码／JSON 冻结清单：`/tmp/fatebridge-p012-final-source-manifest.json`，233项，清单 SHA-256 `837c9633cc9ba71e76d72ae9069a97d2d97330b6a9d178aa8d0c3dfdfbf5b573`。全仓验证日志及 JUnit 在 `/tmp/fatebridge-p012-final-pytest.log`、`/tmp/fatebridge-p012-final-pytest.xml`；测试完成后已逐项复核，233个冻结文件均未变化。
