# FateBridge 引擎参考层（fatebridge-engine）

> 这是所有 FateBridge 场景 Skill 共用的「计算层」。  
> **一条铁律：所有排盘、干支、十神、大运流年、神煞、合婚分、安星、起局、星盘——全部交给 FateBridge 引擎算，AI 永远不要手算。** 手算干支必然出错（节气换月、真太阳时、阴阳遁），这是 FateBridge 「预测准确」的根。AI 只负责读引擎吐出来的事实，然后用人话讲给人听。

---

## 一、怎么调引擎

引擎完全离线，不需要起服务、不需要联网。两种等价写法：

```bash
# 推荐（无需安装，仓库根目录下直接跑）
python3 -m fatebridge.cli <tool> [参数...]

# 若已 pip install 本仓库，等价于
fatebridge <tool> [参数...]
```

常用全局开关：

- `--no-metadata`：去掉 `run_id`/`trace_id` 等溯源字段，输出更干净，**解读时建议都带上**。
- `fatebridge.cli list`：列出全部工具。
- `fatebridge.cli describe <tool>`：输出某工具的**完整参数 schema、接口、类型、是否必填**（JSON）。**记不清参数时，先 `describe`，不要猜 flag。**

调用前的自检：

1. 不确定某工具要哪些字段 → 先 `describe <tool>`。
2. 跑完先看 exit code 和 JSON 是否完整，再解读。
3. 报错先读报错（多半是缺必填字段或 flag 名写错），按 `describe` 改，不要重试同一条。

**成功和失败都走 stdout JSON**：CLI 永远在 stdout 输出一段 JSON——成功是结果，失败是 `{"error": ..., "error_code": ..., "status_code": ..., "retryable": ...}`。用 **exit code≠0** 判失败，再读 stdout 里的 `error_code`/`error` 决定怎么改；**不要只在出错时去读 stderr**（错误信息不在那儿）。常见 `error_code`：CLI 调用层的 `usage_error`（缺必填/flag 写错）、`cli_unsupported`（含嵌套结构，`error` 会指向可用的扁平变体命令）、`unknown_tool`；引擎层（与 REST/MCP 一致）的 `validation_error`、`dependency_missing`、`timeout`、`internal_error`。`retryable=true` 才值得重试。

---

## 二、两种输出形态（决定你怎么读）

**现在所有工具都带 `snapshot_text` + `snapshot_export`**（统一契约，不用再区分有没有）。但有一类工具的 `snapshot_text` 只是其结构化字段的「中文摊平」，**精确解读仍以结构化字段为准**：

| 形态 | 谁是这种（已实测核对） | 怎么读 |
|------|---------|--------|
| **`snapshot_text` 即主依据** | `bazi_birth` / `analyze_destiny`、时运全系、紫微、梅花、奇门、六壬、太乙、金口、`astro_chart` 等命盘/起局/起卦类 | 直接读 `snapshot_text`，它已经是结构化的中文事实（四柱/十神/格局/神煞/大运流年）。 |
| **`snapshot_text` 是摘要，细节看结构化字段** | **八字 9 大专项**（`bazi_marriage`/`romance`/`career`/`wealth`/`health`/`children`/`education`/`personality`/`relatives`）、`two_person_compatibility`、`sukuyo_compatibility`、`astro_relative_chart` | 快速看 `snapshot_text` 抓要点；要精确字段（分数/落点/相位）再读下面的业务字段。`astro_relative_chart` 的 `snapshot_text` 只摘 关系画像/互动相位/配合度，完整盘在结构化字段里。 |

**结构化字段怎么读（snapshot_text 之外要精确时）：**
- 八字 9 专项 → `{"analysis_type": "...", "<dim>_analysis": {...}}`。解读读 `<dim>_analysis`，里面是该维度的子项。例：`bazi_romance` → `romance_analysis.{peach_blossom, hongluan_tianxi, opposite_sex_star, peach_quality, romance_timing, timing_context}`；`bazi_wealth` → `wealth_analysis.{...}`。`timing_context` 段是引擎自动推算的当前大运/流年，看时机就看它。
- `two_person_compatibility` → `summary`（overall_score / compatibility_level）、`detailed_analysis`（element_balance / favorable_synergy）、`strengths`、`challenges`、`recommendations`。
- `sukuyo_compatibility` → 27 宿相性，**有方向**：`person1_to_person2` 与 `person2_to_person1` 各一套关系判定，别只读一边；另有 `pair`（双向综合）、`su27_basis`（各自本命宿）、`summary`。
- `astro_relative_chart` → `relationship_profile`、`inner_chart`、`outer_chart`、`synastry_aspects`、`composite_chart`、`compatibility`。

取 `snapshot_text` 的稳妥写法：

```bash
python3 -m fatebridge.cli --no-metadata bazi_birth ... \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('snapshot_text') or json.dumps(d,ensure_ascii=False,indent=2))"
```

很多工具支持 `--selected-sections`（逗号分隔）只取需要的快照段，省 token。段名可先全量跑一次、从 `snapshot_export` 里看有哪些。

**精确投影 `--fields`：只取你要的结构化字段，省 token。** 支持顶层 key，也支持点号子路径（从输出根算起的绝对路径，不深搜）。多个字段用**空格**分隔（不是逗号；逗号会被当成一个不存在的 key，返回空对象）。`run_metadata` 始终保留。

```bash
# 单字段：直接拿四柱
python3 -m fatebridge.cli --no-metadata bazi_birth <出生参数> \
  --fields bazi_birth.four_pillars

# 多字段（空格分隔）：四柱 + 三元
python3 -m fatebridge.cli --no-metadata bazi_birth <出生参数> \
  --fields bazi_birth.four_pillars bazi_birth.three_origins

# 专项嵌套字段：只取正缘时机信号
python3 -m fatebridge.cli --no-metadata bazi_romance <出生参数> \
  --fields romance_analysis.romance_timing
```

路径写法跟上面「结构化字段怎么读」一致：命盘类带 `bazi_birth.` 前缀，八字 9 专项带 `<dim>_analysis.` 前缀。路径不存在不会报错，会返回空对象——按「指不到字段就别说」处理，别编。

**关掉快照文本省 token（`--no-include-snapshot-text`）。** 只要结构化字段、不要那段几十 KB 的 `snapshot_text` 中文摊平时，加 `--no-include-snapshot-text`（或 `--include-snapshot-text false`）。脚本管道里想要单行紧凑 JSON 再加 `--compact`。两者默认都不改变现状（默认仍带快照、仍美化缩进），所以只在你确实要省 token 时才开。

```bash
# 只取结构化字段 + 关掉快照 + 紧凑：最省 token 的取数姿势
python3 -m fatebridge.cli --no-metadata bazi_birth <出生参数> \
  --no-include-snapshot-text --compact --fields bazi_birth.four_pillars
```

**三端等价：** 这套输出精炼在 REST / MCP / CLI 上语义一致。REST 用查询参数：`POST /api/cn/bazi/birth?include_snapshot_text=false&fields=bazi_birth.day_master&fields=...`（`fields` 可重复，等价于 CLI 的空格分隔）；MCP 工具用同名 keyword 参数 `fields` / `include_snapshot_text` / `compact`。无论哪端，`run_metadata` 始终保留。

---

## 三、参数字典（共用字段）

**出生信息（中式工具：八字 / 时运 / 紫微 / 六壬）**

```
--name 张三 --gender 男|女
--birth-year 1992 --birth-month 8 --birth-day 15
--birth-hour 14 --birth-minute 30
--birth-place 北京          # 用于查经度算真太阳时
--birth-longitude 116.40    # 可选，直接给经度更准
--birth-timezone Asia/Shanghai
--use-true-solar-time       # 开启真太阳时校正（推荐）
```

- **性别影响大运顺逆**，看大运/流年类必填。
- **时辰未知**：可不传 `--birth-hour`，但要在解读里说明「无时盘，时柱相关结论从略」。
- **出生地** 只为算经度/真太阳时，给到市即可。

**分析时点（专项/时运/占卜，默认今天）**

```
--analysis-year 2026 --analysis-month 6 --analysis-day 18   # 想看哪天的运
--analysis-age 35                                            # dayun_analysis 按虚岁定位大运
--target-year 2026                                           # liunian_analysis 指定流年
```

- 八字九维专项工具（marriage/career/...）**会自动推算当前大运、流年**，用户不用懂大运。`--dayun-pillar`/`--liunian-pillar` 只是手动覆盖，正常别传。

**西占工具（astro_* / 推运）** 用的是另一套：

```
--birth-latitude 39.90 --birth-longitude 116.40   # 西占要经纬度
--hsys P            # 宫位制（如 Placidus）
--zodiacal tropic   # 回归/恒星
--analysis-year/month/day   # 推运目标时间
```

西占工具优先用本地 Swiss Ephemeris（kerykeion）；没装时回退 FateBridge 内置近似轨道模型，结论可用但精度略降，解读时可点一句「按近似星历」。

---

## 四、全量工具地图（按家族）

> 每个场景 Skill 只需引用与自己相关的几个；这张表是「全集」，保证 60+ 能力都有归属。

### 八字 · 命主本命（snapshot_text）
| 工具 | 用途 |
|------|------|
| `bazi_birth` | 完整命盘：四柱三元、纳音、十神、藏干、格局调候、十二长生、当前大运流年、神煞 |
| `analyze_destiny` | 综合命理：八字+喜用+格局，一站式 |
| `calculate_legacy` | 兼容旧版扁平命盘结构 |

### 八字 · 九大专项（结构化 JSON，自动带时机信号）
`bazi_marriage` 婚姻 · `bazi_romance` 正缘桃花 · `bazi_career` 事业 · `bazi_wealth` 财运 · `bazi_health` 健康 · `bazi_children` 子女 · `bazi_education` 学业 · `bazi_personality` 性格 · `bazi_relatives` 六亲。  
均接受 `--analysis-year/month/day`，内部自动推大运/流年（结果在 `<dim>_analysis.timing_context`）。**返回 JSON `{analysis_type, <dim>_analysis}`，无 snapshot_text**——按上面「结构化 JSON 怎么读」取 `<dim>_analysis`。

### 配合度 · 双人（结构化 JSON）
| 工具 | 用途 |
|------|------|
| `two_person_compatibility` | 八字合婚 / 合作配合度：综合分、五行互补、共同喜用、优势/挑战/建议。两人各一套 `--person1-*` / `--person2-*` 字段（名/年/月/日/时/性别） |
| `sukuyo_compatibility` | 宿曜 27 宿双人相性（按月亮经度），有方向性。两人各一套 `--person1-date/-time/-zone/-lat/-lon` 等字段 |

### 时运 · 推命（snapshot_text）
`timing_analysis` 时运综合 · `dayun_analysis` 大运 · `liunian_analysis` 流年 · `liuyue_analysis` 流月 · `liuri_analysis` 流日 · `liushi_analysis` 流时 · `jieqi_timeline_analysis` 节气时间轴 · `jieqi_year` 节气年表 · `nongli_time` 农历时间换算。

> **综合 vs 颗粒怎么选**：`timing_analysis` 是聚合器，一次把当前大运+流年（+流月等）的综合影响给全，**问「最近运势/这两年怎么样」用它**；`dayun_analysis`/`liunian_analysis`/… 是单层颗粒，**只盯某一层（如就看某个大运、某个特定流年）才单独调**。综合工具的内容与颗粒工具有意重叠——别为了拼一个时运全景去逐层调颗粒再自己拼，那是 `timing_analysis` 的活。

### 占卜 · 问事起卦（snapshot_text）
| 工具 | 用途 / 输入 |
|------|------|
| `meihua_analysis` | 梅花易数：`--question`（可选）+ **起卦时间必填** `--analysis-year/month/day/hour`（要按当下起卦就传当前日期时间） |
| `sixyao` | 六爻：`--question`，可手摇 `--lines`/`--gua-code` 或按时间起 |
| `tongshefa` | 大衍筮法（蓍草） |
| `gua_lookup` / `gua_meiyi` | 卦象查询 / 卦义 |
| `qimen` | 奇门遁甲：起局 + 用神 |
| `taiyi` | 太乙神数 |
| `jinkou` | 金口诀：`--di-fen` 地分 + 时间 |
| `liureng_gods` | 大六壬起课 |
| `liureng_runyear` | 六壬流年（行年） |
| `suzhan` | 宿占 / 二十八宿 |
| `otherbu` | 其他卜法 |
| `sanshiunited` | 三式合参（奇门+太乙+六壬同盘） |

### 紫微斗数（snapshot_text）
`ziwei_birth` 紫微命盘（含十二宫安星）· `ziwei_rules` 紫微规则查询（`--year-stem`）。

### 占星 · 出生盘与关系盘
`astro_chart` 标准盘 · `astro_chart13` 13星座盘 · `astro_hellen_chart` 希腊盘 · `astro_guolao_chart` 果老星宗 · `astro_india_chart` 印度盘 · `astro_germany_chart` 德国盘。  
`astro_relative_chart` 关系盘（`astro_relative` 同义但 CLI 因嵌套不支持，用 `_chart` 版本）：**两人用 `--inner-birth-*` 和 `--outer-birth-*`**（各需 year/month/day/hour/longitude/latitude，name/place/minute/timezone 可选），返回 JSON（见上）。

### 西占 · 推运（依赖本地星历更精确）
`western_timing_analysis` 时运综合 · `solarreturn` 太阳返照 · `lunarreturn` 月返 · `transit` 行运 · `solararc` 太阳弧 · `givenyear` 指定年盘 · `profection` 年小限 · `pd`/`pdchart` 主限 · `zr` 黄道释放 · `firdaria` 法达星限 · `decennials` 十年星限。

> 同八字时运的逻辑：`western_timing_analysis` 是综合聚合（要整体推运用它），`solarreturn`/`transit`/`profection`/… 是单一技法颗粒（只看某一术时单独调），两者内容有意重叠。

### 知识与导出 helper
`knowledge_registry` 知识目录 · `knowledge_read` 读取词条（`--domain --category --key`）· `export_registry` 导出注册表 · `export_parse` 导出解析。用于给一段结果补充传统词条释义。

---

## 五、读 snapshot_text 的速查（以八字为例）

引擎吐出的 `snapshot_text` 已经分好段，对应着「事实」。解读时按段取信号：

- `[起盘信息]` — 真太阳时校正、农历、节气。**先确认起盘对不对**（出生地/时辰）。
- `[四柱与三元]` — 年月日时柱、纳音、十神、藏干。日柱天干＝**日主**（命主本人）。
- `[格局调候]` — 月令格局（如正官格）、调候用神（如「主用丁」）、日主十二长生。**用神＝这个人最需要补的五行**，是吉凶判断的轴。
- `[流年行运概略]` — 当前大运、流年、流月，及五行力量增减。**看时机就看这段。**
- `[神煞...]` — 桃花、驿马、华盖、天乙贵人、空亡、红鸾天喜等。神煞是「色彩」，别当铁口直断。

判吉凶的总原则：**看某五行/十神是不是命主的「喜用」**。喜用被生扶＝顺；忌神当旺/喜用被克＝有挑战。引擎已经把喜用、力量增减写在快照里，照着读即可，不要自己重排五行。

---

## 六、跨体系交叉印证（提高可信度）

八字、紫微、西占是三套**互不重叠**的算法：干支五行、星曜十二宫、行星黄道，各算各的。正因为不重叠，它们的结论才能相互当证据用。问性格、命局、整体走向这类「多套都能答」的问题时，**别只跑一套就下结论**——并行跑两到三套，再这样读：

- **多套独立指向同一处 → 高可信。** 比如八字日主主「智」、紫微文曲入庙、西占月亮双子都指向「思辨型」，这种三方共指的信号才敢讲重话。
- **某结论只有一套提到 → 弱信号。** 标出来当倾向，别当定论。
- **两套打架 → 不是 bug，往往是这个人最真实的内在张力。** 比如八字紫微都偏「刚、压力大」，西占却显「轻盈、社交」，那这层表里落差本身就是画像的一部分，照实讲出来。

读法：先各看各的 `snapshot_text`/结构化字段，抓出每套最突出的 2–3 个信号，再横向比对哪些重合、哪些只此一家、哪些相反。**重合处下结论，相反处讲张力，孤证处留余地。** 别把三套各背一遍堆给用户。

---

## 七、典型调用样例

```bash
# 八字本命盘
python3 -m fatebridge.cli --no-metadata bazi_birth \
  --name 小南 --gender 男 --birth-year 1992 --birth-month 8 --birth-day 15 \
  --birth-hour 14 --birth-minute 30 --birth-place 北京 --use-true-solar-time

# 八字婚姻专项（自动带当前大运/流年）
python3 -m fatebridge.cli --no-metadata bazi_marriage \
  --gender 女 --birth-year 1994 --birth-month 3 --birth-day 2 --birth-hour 9 --birth-place 上海

# 双人合婚
python3 -m fatebridge.cli --no-metadata two_person_compatibility \
  --person1-name 小A --person1-gender 男 --person1-birth-year 1992 --person1-birth-month 8 --person1-birth-day 15 --person1-birth-hour 14 \
  --person2-name 小B --person2-gender 女 --person2-birth-year 1994 --person2-birth-month 3 --person2-birth-day 2 --person2-birth-hour 9

# 流年看 2026
python3 -m fatebridge.cli --no-metadata liunian_analysis \
  --gender 男 --birth-year 1992 --birth-month 8 --birth-day 15 --birth-hour 14 --birth-place 北京 --target-year 2026

# 梅花易数问事（起卦时间必填，按当下就传当前日期时间）
python3 -m fatebridge.cli --no-metadata meihua_analysis --question "这份 offer 该不该接" \
  --analysis-year 2026 --analysis-month 6 --analysis-day 18 --analysis-hour 15

# 占星标准盘
python3 -m fatebridge.cli --no-metadata astro_chart \
  --name Mia --birth-year 1995 --birth-month 6 --birth-day 1 --birth-hour 8 --birth-minute 20 \
  --birth-latitude 31.23 --birth-longitude 121.47 --birth-place 上海
```

跑不通时永远的第一步：`python3 -m fatebridge.cli describe <tool>`。

---

## 八、全局调用纪律（省 token / 防重复运算）

> 权威全文与各场景的工具取舍见 `docs/SCENARIO_ROUTING.md`。本节是所有 onda 技能共享的执行铁律。

1. **命盘复用**：综合命理画像调一次 `analyze_destiny`（已含命盘+喜用+格局），不要再调 `bazi_birth`；只要原始四柱才单用 `bazi_birth`。同一出生信息跨八字/紫微/西占复用，不重复采集。
2. **聚合优先**：时运全景用 `timing_analysis` / `western_timing_analysis`，不连发多个单技法；只要一项才用单工具。
3. **粒度匹配**：年级信号（如 `romance_timing`）不许说成「几月」，要月级才升级 `liuyue_analysis`，日级才 `liuri_analysis`。
4. **token 收口**：聚焦问题默认 `--fields` / `selected_sections` 裁剪，不裸吐整张 `snapshot_text`。
5. **一次一项收信息**，记不清参数先 `describe`，报错先读 `error_code` 再改，不盲重试。

## 九、交叉印证与去重（防矛盾）

**主证 + 旁证 + 显式分歧**：每个场景钉一个主证系统出结论，其余只作旁证（加强/修正），不单独下判断。系统间一致则合并去重；冲突则显式标注「两套口径不一」，不静默二选一。同一神煞在多个工具重复出现时，按当前场景取一个口径讲一次（如咸池在 romance=机会 / marriage=防烂桃花，合并讲一次）。各域主证分配见 `docs/SCENARIO_ROUTING.md` §B。
