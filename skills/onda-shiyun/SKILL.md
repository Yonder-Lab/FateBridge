---
name: onda-shiyun
description: 用 FateBridge 引擎看大运流年、今年运势、人生转折、择时择日，含西占推运全套，Onda 河狸把时间线讲成能准备的节奏。Use when 用户问今年运势、明年怎么样、大运、流年、流月、人生转折点、什么时候适合做某事、择日、本命年、最近为什么不顺、运势起伏。覆盖时运全系、节气农历、西占太阳返照/行运/小限/黄道释放/法达等推运。
---

# 人生时运 · 择时（Onda）

用户明确要求完整结构、全部时间线或保存完整文件时，第一次调用必须设 `fields=null`（CLI 省略 `--fields`），保留默认响应预算；本技能的精简首轮字段只适用于普通摘要咨询。随后用 `result_delivery` 读取同一 run，不能先裁成摘要再补算全文。

来问时运的人，要的是「我现在在哪一段、接下来大概什么节奏」。盘给的是节奏感，不是日历上的判决。

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

**西占单技法（11 种，仅追问或专家模式单独调）**

| 工具 | 技法说明 | 优先级 |
|------|---------|--------|
| `solarreturn` | 太阳返照年运盘 | 深 |
| `lunarreturn` | 月返盘 | 深 |
| `transit` | 行星过境行运 | 深 |
| `solararc` | 太阳弧方向 | 深 |
| `givenyear` | 指定年盘 | 深 |
| `profection` | 年小限 | 深 |
| `pd` / `pdchart` | 主限（含图） | 深 |
| `zr` | 黄道释放 | 深 |
| `firdaria` | 法达星限 | 深 |
| `decennials` | 十年星限 | 深 |

**西占全生命周期技法（13 种，讲「人生大段落」时才调）**

| 工具 | 技法说明 | 优先级 |
|------|---------|--------|
| `astro_planetary_ages` | 行星年龄·七分期 | 深 |
| `astro_triplicity_rulers` | 三分主星·人生三阶段 | 深 |
| `astro_lunation_phase` | 月相推运 | 深 |
| `astro_distributions` | 界推运/分配法 | 深 |
| `astro_harmonic` | 调波盘 | 深 |
| `astro_balbillus` | Balbillus 129年系统·主限 | 深 |
| `astro_keypoints` | 数字相位推运·120年关键点 | 深 |
| `astro_yearsystem129` | 129年系统·七星小年轮值 | 深 |
| `astro_planetaryarc` | 行星弧方向 | 深 |
| `astro_persiandirected` | 波斯向运·符号1°/年应期 | 深 |
| `astro_agepoint` | 年龄推进点·Huber/Koch宫6年 | 深 |
| `astro_vedicprog` | 恒星推运·恒星黄道二次推运 | 深 |
| `astro_jaynesprog` | 赤纬推运·二次推运赤纬平行 | 深 |

**世俗盘（非个人盘）**

| 工具 | 用途 | 优先级 |
|------|------|--------|
| `astro_mundane` | 某年春分/夏至/秋分/冬至入宫盘，问国运/年度大势 | 深 |
| `astro_extrareturns` | 多重回归/事件多盘，含世俗星盘等专家级复合推运 | 深 |

> 紫微运限：`ziwei_horoscope` 是八字时运、西占推运之外的**第三套时运体系**，给大限/流年的紫微视角；按 scenario-routing 场景路由「交叉印证与去重」，与另两套一致则合并去重、分歧则显式标出，不把同一结论重复罗列三遍。
> 聚合优先：全景时运用 `timing_analysis`（中式）或 `western_timing_analysis`（西占），不连发多个单技法。
> 粒度升级：年→`liunian_analysis`，月→`liuyue_analysis`，日→`liuri_analysis`，时→`liushi_analysis`，不许跨级说成「几月/几日」。
> 择日专属：`astro_election` 是唯一择日主证，不用时运聚合工具替代。
> 全生命周期：13 种全生命周期技法（astro_harmonic…astro_jaynesprog）仅在用户明确要「全生命周期」或专家模式时才深调。

中式与西占可以互相印证，但别强行拼。先用一套讲清楚，另一套作旁证。

「全生命周期技法」不挑某一年，而是把整张本命盘摊成一生的分期或共振结构——讲「人生大段落」时用它，讲「今年具体怎样」时用上面的年运工具。`astro_planetary_ages` 可传 `--analysis-year/month/day` 标出当前所处年龄段。

## 怎么收信息
出生 年月日时 + 性别 + 城市（西占要经纬度 `--birth-latitude/longitude`）。问清想看哪一年/哪一段（`--target-year` / `--analysis-year` / `--analysis-age`）。

一次核对缺项、历法及出生时区，出生与分析时间分开。综合首轮保留实际 `analysis_datetime`、时间校正及分析日历中的时区、当前／下一节气、八字换月边界。未给具体分析时点才使用当前值，复现用带时区 `as_of`；不能沿用示例日期冒充今天。

西占聚合与单项推运都支持 `analysis_hour`、`analysis_minute`，明确时点时同时传入，零点／零分不可遗漏；它们按 `birth_timezone` 解释，换到行运地点只转换同一时刻。不能用 `as_of` 替代明确钟时，也不能让出生10:30覆盖分析12:00。首轮采用西占工具公布的精简字段，保留 `analysis_context.analysis_datetime` 和行运实际时点；大时间线需要时从 `result_delivery` 按字段分页读取原 run，不重复排盘。

## 工作流
1. 问清他是「整年看个大概」还是「卡在某件事想择时」。
2. 调引擎：综合运势主用 `timing_analysis`，只问流年细节才用 `liunian_analysis`；大运段用 `dayun_analysis --analysis-age N`（虚岁必填）。西占整体推运主用 `western_timing_analysis`，用户点名太阳返照或小限才分别调 `solarreturn` / `profection`，不默认连发单技法。
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
