---
name: onda-shiyun
description: 用 FateBridge 的八字、紫微或西占时运计算，说明当前阶段、当年与月度节奏；按实际边界交付简明时间线或候选时段对照，让用户据此安排现实准备。Use when 用户问今年明年运势、大运流年流月、人生转折、何时做事、择日、本命年或运势起伏；仅在有相应粒度结果时细化，不预言具体事件。
---

# 人生时运 · 择时（Onda）

用户明确要求完整结构、全部时间线或保存完整文件时，第一次调用必须设 `fields=null`（CLI 省略 `--fields`），保留默认响应预算；本技能的精简首轮字段只适用于普通摘要咨询。随后用 `result_delivery` 读取同一 run，不能先裁成摘要再补算全文。

来问时运的人，要的是「我现在在哪一段、接下来大概什么节奏」。盘给的是节奏感，不是日历上的判决。

## 用户能得到什么

先回答所问时段最有参考价值的变化，挑 2–3 项实际依据，再给一项现实准备。短答不需要铺全部技法；只有时间之间确有可比较的返回，才用时间线或短表。

| 本次问题 | 实际计算依据 | 合适的交付 |
| --- | --- | --- |
| 当前处在哪段／今年怎样 | `dayun_analysis`、`liunian_analysis` 与当前 `liuyue_analysis` | 分开讲阶段背景、当年主题和当前月，指出同向与分歧；不把当月扩写成全年每月 |
| 全年月份／某段安排 | 明确所需范围后，选择 `analysis_calendar.liuyue_timeline` 及实际起止边界 | 以“时段／有何区别／准备什么”列出最相关的几段，完整请求保留全部；节气换月和公历月不混写 |
| 西占推运／紫微运限 | 相应聚合的实际时间主星、时间线、运限或四化，按该体系读取 | 说明哪些层是阶段背景、哪些落在目标时点；各体系分开署明，不把多体系同向当作预测有效性的证据 |
| 明确活动择时 | `astro_election` 的实际候选与条件 | 对照已计算候选和用户的现实可用时段；普通运势不能替代择日结果，吉时也不保证活动结果 |

全年时间线在普通首轮字段之外：问题本来就要求全年结构或全部时间线，首次即 `fields=null`，随后读同一 run 的 `result_delivery`；首轮只做摘要时不能声称未保留的月份已交付。没有真实时间差异就直接说明，不为表格补出“更旺”的月份。准备动作如核对项目截止、预算或沟通安排，来自现实建议，不能写成计算出的事件。

用户把某个月与另一年比较时，开头就说明粒度不同，再分清未变的长期背景、新目标实际返回的信号和仍不可比较的部分。月度十神与年度十神不同，不足以推出后一年的责任、收入或压力比前一年更强；只有同粒度、同口径的依据才作强弱比较。年度仍有某主题，就说“仍有”，不把不变结构包装成新利好；不为凑出升降额外跑齐所有专项。

## 引用路径

发现入口可能是软链接。优先进入入口目录后用 shell 内建 `pwd -P` 取得真实目录，再按它读取下面的相对引用；不要为解析路径调用未经核实的系统 `python3`。不能先裁剪 `.agents/skills/onda-*` 入口的字符串父目录，否则会误指到 `.agents/skills/_shared` 或 `.agents/docs`。读取已知引用无需搜索仓库。

## 先读这两份（必读）
- 计算怎么调：[../_shared/fatebridge-engine.md](../_shared/fatebridge-engine.md)
- 怎么开口说话：[../_shared/onda-counsel.md](../_shared/onda-counsel.md)
- 场景取舍与去重：[../../docs/scenario-routing.md](../../docs/scenario-routing.md)

**铁律：大运起运、流年干支、节气换月、星历推运全部交给引擎。手算这些必错。**

调用纪律与去重见 [引擎调用纪律](../_shared/fatebridge-engine.md#全局调用纪律) 与 [交叉印证与去重](../_shared/fatebridge-engine.md#交叉印证与去重防矛盾)。

## 这个场景用哪些工具

「人生时运 · 择时」对应路由（主=出结论必调；旁=只加强/修正；深=追问或专家模式才调）：

**中式时运（聚合优先）**

| 用户想问 | 工具 | 优先级 | 要点 |
|---------|------|--------|------|
| 今年/明年运势 | `timing_analysis` | 主 | 一次拿大运+流年全景 |
| 今年/明年运势 | `liunian_analysis` | 旁 | 流年细节（全景已用 timing_analysis 时按需升级） |
| 今年/明年运势（西占视角） | `western_timing_analysis` | 主 | 西占整体推运 |
| 今年/明年运势（西占视角） | `solarreturn` | 深 | 太阳返照，追问才单调 |
| 今年/明年运势（西占视角） | `transit` | 深 | 行运单技法 |
| 大运走到哪 | `dayun_analysis` | 主 | `--analysis-age N`（虚岁必填） |
| 大限/流年的紫微视角（运限） | `ziwei_horoscope` | 主 | 紫微第三套时运体系：六层运限（大限/小限/流年/流月/流日/流时）+ 动态四化；`--target-year/--target-month/--target-day/--target-hour` 都要传 |
| 人生转折点 | `timing_analysis` | 旁 | |
| 人生转折点 | `dayun_analysis` | 旁 | |
| 人生转折点 | `western_timing_analysis` | 旁 | |
| 人生转折点 | `solararc` | 旁 | |
| 人生转折点 | `pd` | 深 | 主限，专家模式 |
| 人生转折点 | `firdaria` | 深 | 法达，专家模式 |
| 人生转折点 | `decennials` | 深 | 十年星限，专家模式 |
| 最近为什么不顺·本命年 | `liunian_analysis` | 主 | |
| 最近为什么不顺·本命年 | `liuyue_analysis` | 旁 | 流月节奏 |
| 最近为什么不顺·本命年 | `transit` | 旁 | 西占行运旁证 |
| 什么时候适合做某事·择日 | `astro_election` | 主 | 唯一择日主证 |
| 某月/某天的小节奏 | `liuyue_analysis` | — | 月级 |
| 某月/某天的小节奏 | `liuri_analysis` | — | 日级 |
| 某月/某天的小节奏 | `liushi_analysis` | — | 时级 |
| 节气/农历换算、节气年表 | `jieqi_timeline_analysis` / `jieqi_year` / `nongli_time` | — | 历法支撑（场景路由「支撑与元工具」） |

**点名技法再展开**：入口能力索引如下，说明与适用范围按需读 [技法参考](references/techniques.md)，普通咨询不逐项调用。

- 单技法：`solarreturn`、`lunarreturn`、`transit`、`solararc`、`givenyear`、`profection`、`pd`、`pdchart`、`zr`、`firdaria`、`decennials`。
- 全生命周期：`astro_planetary_ages`、`astro_triplicity_rulers`、`astro_lunation_phase`、`astro_distributions`、`astro_harmonic`、`astro_balbillus`、`astro_keypoints`、`astro_yearsystem129`、`astro_planetaryarc`、`astro_persiandirected`、`astro_agepoint`、`astro_vedicprog`、`astro_jaynesprog`。
- 非个人盘：`astro_mundane`、`astro_extrareturns`。

> 紫微运限：`ziwei_horoscope` 是八字时运、西占推运之外的**第三套时运体系**，给大限/流年的紫微视角；按 scenario-routing 场景路由「交叉印证与去重」，与另两套一致则合并去重、分歧则显式标出，不把同一结论重复罗列三遍。
> 聚合优先：全景时运用 `timing_analysis`（中式）或 `western_timing_analysis`（西占），不连发多个单技法。
> 粒度升级：年→`liunian_analysis`，月→`liuyue_analysis`，日→`liuri_analysis`，时→`liushi_analysis`，不许跨级说成「几月/几日」。
> 择日专属：`astro_election` 是唯一择日主证，不用时运聚合工具替代。
> 全生命周期：13 种全生命周期技法（astro_harmonic…astro_jaynesprog）仅在用户明确要「全生命周期」或专家模式时才深调。

中式与西占可以互相印证，但别强行拼。先用一套讲清楚，另一套作旁证。

「全生命周期技法」不挑某一年，而是把整张本命盘摊成一生的分期或共振结构——讲「人生大段落」时用它，讲「今年具体怎样」时用上面的年运工具。`astro_planetary_ages` 可传 `--analysis-year/month/day` 标出当前所处年龄段。

## 怎么收信息
个人运限核对出生年月日时、适用性别规则、城市／时区（西占推运需要经纬度 `--birth-latitude/longitude`），以及已要求的年／时段／年龄。活动择时 `astro_election` 使用候选时间与活动地点，不收出生资料；节气／农历换算也只核对所选日期，不套出生问卷。

一次核对缺项、历法及出生时区，出生与分析时间分开。综合首轮保留实际 `analysis_datetime`、时间校正及分析日历中的时区、当前／下一节气、八字换月边界。未给具体分析时点才使用当前值，复现用带时区 `as_of`；不能沿用示例日期冒充今天。

西占聚合与单项推运都支持 `analysis_hour`、`analysis_minute`，明确时点时同时传入，零点／零分不可遗漏；它们按 `birth_timezone` 解释，换到行运地点只转换同一时刻。不能用 `as_of` 替代明确钟时，也不能让出生10:30覆盖分析12:00。首轮采用西占工具公布的精简字段，保留 `analysis_context.analysis_datetime` 和行运实际时点；大时间线需要时从 `result_delivery` 按字段分页读取原 run，不重复排盘。

## 工作流
1. 按用户已说的时段与目的选择运势或择时分支；只有会改变计算范围时再简短核对。
2. 调引擎：综合运势主用 `timing_analysis`，只问流年细节才用 `liunian_analysis`。用户更换目标年份，仍要大运背景或月份对照时，直接用新目标的聚合，不先取流年专项再补聚合。纯流年窄查询可用已验证的 `fields=["liunian_info","personal_info","summary","target_year_jieqi"]`，按所问进一步缩小；普通解释不因缺首轮预设就默认 `fields=null` 取全快照。大运段用 `dayun_analysis --analysis-age N`（虚岁必填）。西占整体推运主用 `western_timing_analysis`，用户点名太阳返照或小限才分别调 `solarreturn` / `profection`，不默认连发单技法。
3. 读首轮结构化时运信号，按实际返回的年/月/日粒度和节气边界表述；仅有流年不能推断上半年或下半年。更细节奏只补尚未返回的层，不重算聚合已有内容；全年时间线在明确要求时展开。
4. 给节奏建议，不给死期。
5. 按 [Onda 解读层](../_shared/onda-counsel.md) 自然收尾；建议已在正文讲清就停，不重复排程或强造一句结尾。

## 红线
- 不报「灾年」「劫数」吓人；不下「某月必出事」的死期。
- 不顺的年份，说成「适合收一收、打基础的一段」，给可做的事。
- 核心星盘可回退轨道近似；西占推运缺 backend 时直接报 `dependency_missing`，不能按近似模型继续解读。实际星历模型仍需核对输出。

## 样例
```bash
# 综合首轮：保留实际分析时间、时区及节气换月边界
python3 -m fatebridge.cli --no-metadata timing_analysis \
  --gender 男 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-place 北京 \
  --analysis-year 2026 --analysis-month 10 --analysis-day 14 \
  --strict-fields --no-include-snapshot-text \
  --fields dayun_analysis liunian_analysis liuyue_analysis comprehensive_summary personal_info.analysis_datetime personal_info.time_adjustment analysis_calendar.analysis_date_context.timezone analysis_calendar.analysis_date_context.current_solar_term analysis_calendar.analysis_date_context.next_solar_term analysis_calendar.analysis_date_context.bazi_month_boundary

python3 -m fatebridge.cli --no-metadata liunian_analysis \
  --gender 男 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-place 北京 --target-year 2026

python3 -m fatebridge.cli --no-metadata profection \
  --name 我 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-minute 30 \
  --birth-latitude 39.90 --birth-longitude 116.40 --birth-place 北京 --analysis-year 2026

# 全生命周期：行星年龄（标出当前所处段），可只取 summary
python3 -m fatebridge.cli --no-metadata astro_planetary_ages --fields summary \
  --name 我 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-minute 30 \
  --birth-latitude 39.90 --birth-longitude 116.40 --birth-place 北京 --analysis-year 2026

# 月相推运：本命月相 + 八相时间轴（默认看到 90 岁）
python3 -m fatebridge.cli --no-metadata astro_lunation_phase \
  --name 我 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-minute 30 \
  --birth-latitude 39.90 --birth-longitude 116.40 --birth-place 北京

# 紫微运限：第三套时运体系，看目标时间点的六层运限+动态四化
python3 -m fatebridge.cli --no-metadata ziwei_horoscope \
  --gender 男 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 \
  --target-year 2026 --target-month 6 --target-day 19 --target-hour 14 --fields summary
```
