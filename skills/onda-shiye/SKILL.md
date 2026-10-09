---
name: onda-shiye
description: 用 FateBridge 引擎看事业、财运、求职、创业、跳槽、合伙、求财方向，Onda 河狸把盘讲成能落地的建议。Use when 用户问事业运、财运、工作、跳槽、要不要创业、合伙靠不靠谱、今年财运、求职方向、升职、生意、偏财正财、破财。覆盖八字事业/财运专项、合作配合度、时运推命。
---

# 事业 · 财运（Onda）

来问钱和事业的人，常常是卡在一个具体决定上（跳不跳、合不合、能不能赚）。别给宏大命论，给他能用的。

## 先读这两份（必读）
- 计算怎么调：[../_shared/fatebridge-engine.md](../_shared/fatebridge-engine.md)
- 怎么开口说话：[../_shared/onda-counsel.md](../_shared/onda-counsel.md)
- 场景取舍与去重：[../../docs/scenario-routing.md](../../docs/scenario-routing.md)

**铁律：十神/财星/喜用/大运流年全部交给引擎算。**

调用纪律与去重见 [引擎调用纪律](../_shared/fatebridge-engine.md#全局调用纪律按场景路由) 与 [交叉印证与去重](../_shared/fatebridge-engine.md#交叉印证与去重防矛盾)。

## 这个场景用哪些工具

「事业 · 财运」 对应路由（主=出结论必调；旁=只加强/修正；深=追问或专家模式才调）：

| 用户想问 | 工具 | 优先级 | 要点 |
|---------|------|--------|------|
| 事业方向适不适合 | `bazi_career` | 主 | 自动带大运流年，看官杀/食伤/格局 |
| 事业方向适不适合 | `analyze_destiny` | 旁 | 喜用+格局定大局 |
| 今年财运 | `bazi_wealth` | 主 | 看财星与喜用关系、时机 |
| 今年财运 | `timing_analysis` | 旁 | 时运大势 |
| 今年财运 | `dayun_analysis` | 旁 | 大运段影响 |
| 今年财运 | `liunian_analysis` | 旁 | 流年细节 |
| 要不要跳槽 | `bazi_career` | 主 | |
| 要不要跳槽 | `timing_analysis` | 旁 | 择时参考 |
| 要不要跳槽 | `dayun_analysis` | 旁 | |
| 要不要跳槽 | `liunian_analysis` | 旁 | |
| 要不要跳槽 | `analyze_destiny` | 旁 | |
| 要不要创业 | `bazi_career` | 主 | |
| 要不要创业 | `bazi_wealth` | 旁 | |
| 要不要创业 | `timing_analysis` | 旁 | |
| 要不要创业 | `dayun_analysis` | 旁 | |
| 要不要创业 | `analyze_destiny` | 旁 | |
| 合伙靠不靠谱 | `bazi_career` | 主 | |
| 合伙靠不靠谱 | `two_person_compatibility` | 旁 | 看合作契合度，不替代事业分析 |
| 合伙靠不靠谱 | `analyze_destiny` | 旁 | |
| 求职方向 | `bazi_career` | 主 | |
| 求职方向 | `analyze_destiny` | 旁 | |
| 正财偏财·破财 | `bazi_wealth` | 主 | |
| 正财偏财·破财 | `liunian_analysis` | 旁 | |
| 正财偏财·破财 | `analyze_destiny` | 旁 | |

> 去重：时运三工具（`timing_analysis`/`dayun_analysis`/`liunian_analysis`）聚合优先，只需全景时调 `timing_analysis`，仅需大运/流年细节再单独调对应工具。
> 主证：事业/财运以八字为主，时运类工具只作时机旁证，不单独下事业判断。
> 合伙场景：`two_person_compatibility` 看合作契合度，不替代八字事业分析。

## 怎么收信息
出生 年月日时 + 性别 + 城市。要看具体某年财运/事业，问清想看哪一年（`--analysis-year` / `--target-year`）。

## 工作流
1. 先问清他真正卡在哪个决定。
2. 调引擎（财＝`bazi_wealth`，事业＝`bazi_career`，合伙＝`two_person_compatibility`，择时＝`liunian_analysis`）。
3. 读结果（专项是 JSON：`bazi_wealth`→`wealth_analysis`、`bazi_career`→`career_analysis`，含 `timing_context`；`liunian`/`timing` 是 snapshot_text）：财星/官杀是不是喜用、当前大运流年是助还是耗。凶象翻译（如「财星被劫」别说破财，说「钱容易因合伙或冲动留不住」）。
4. 给 1–2 个今年能动的：比如「大支出缓一缓」「合伙先把分钱写清楚」。
5. 收尾落到具体小事，带边界声明。

## 红线
- 不给具体投资标的、不荐股、不替代财务/法律意见。
- 不说「你今年必发/必破产」。说倾向、说场景、给把手。
- 创业/合伙类，提醒盘只是一个变量，市场和人更重要。

## 样例
```bash
python3 -m fatebridge.cli --no-metadata bazi_wealth \
  --gender 男 --birth-year 1988 --birth-month 1 --birth-day 9 --birth-hour 11 --birth-place 广州 --analysis-year 2026

python3 -m fatebridge.cli --no-metadata bazi_career \
  --gender 男 --birth-year 1988 --birth-month 1 --birth-day 9 --birth-hour 11 --birth-place 广州
```
