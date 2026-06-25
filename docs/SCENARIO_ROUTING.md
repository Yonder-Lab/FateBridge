# FateBridge 场景路由矩阵（Scenario Routing）

> 面向 Agent / 解读技能的**路由权威参照**。引擎只算不解读；本文件回答「某类问题该调哪些工具、谁主谁次、怎么省 token、怎么不自相矛盾」。
> 工具发现仍以机读为准（`/api/tools`、MCP `tools/list`、`fatebridge list`），本文件不替代发现，而是给出**场景→工具**的取舍。
> 单元格优先级标记贯穿全文：**主**=出结论必调；**旁**=只加强/修正主证，不单独下判断；**深**=用户追问或专家模式才调。

## §A 全局调用纪律（省 token / 防重复运算）

1. **命盘复用**：要综合命理画像调一次 `analyze_destiny`（已含命盘 + 喜用 + 格局），**不要**再调 `bazi_birth`；只要四柱/十神原始命盘才单独用 `bazi_birth`。同一出生信息在八字/紫微/西占之间复用，不重复向用户采集。
2. **聚合优先**：要时运全景用 `timing_analysis`（中式）或 `western_timing_analysis`（西占），**不要**连发多个单技法工具；反过来，只需要某一项技法时才用对应单工具（如只看太阳返照用 `solarreturn`）。
3. **粒度匹配**：年级工具（如 `bazi_romance` 的 `romance_timing`）只给到流年级，**不许**说成「几月」；要月级才升级 `liuyue_analysis`，要日级才 `liuri_analysis`。
4. **token 默认收口**：聚焦问题默认用 `fields`/`--fields`（支持点号子路径，如 `bazi_birth.day_master`）或 `selected_sections` 裁剪，**不要**对一个小问题裸吐整张 `snapshot_text`。`run_metadata` 始终保留以便溯源。
5. **一次一项收信息**：缺字段像聊天一样一项项问，别甩一张表。记不清某工具参数先 `describe <tool>`，报错先读 `error_code` 再改，**不盲目重试同一条**。

## §B 交叉印证与去重策略（防矛盾）

**主证 + 旁证 + 显式分歧**，是本文件处理多体系并用的统一原则：

- **每个场景域钉一个主证系统**出结论，其余系统只作旁证（加强或修正），不单独下判断。各域主证见 §C 每张表的「主」列与下表：

  | 场景域 | 主证系统 | 旁证 |
  |---|---|---|
  | 命格（性格/天赋/学业/六亲/原生家庭） | 紫微（性格底色/六亲宫）+ 八字（十神格局） | 西占 |
  | 事业 / 财运 | 八字（事业/财专项） | 时运、合作配合度 |
  | 缘分 / 感情 | 八字婚姻/正缘（单人）、配合度（双人） | 紫微夫妻宫、宿曜、关系盘 |
  | 健康 | 八字健康专项 | 时运对身心影响 |
  | 时运 / 择时 | 时运全系（聚合优先）、西占推运 | 节气农历 |
  | 星盘（西占本体） | `astro_chart`（含流派 variant） | 西占推运衔接 |
  | 问事 / 抉择 | 占卜类（梅花/六爻/奇门/六壬/金口/太乙/宿占/三式/星骰） | —— |

- **一致 → 合并去重**：多系统指向同一结论时合并讲，不重复罗列。
- **冲突 → 显式标注**：系统间分歧时明确说「两套口径不一」并各自给出，**不静默二选一**，保留整合画像让用户自己权衡。
- **同信号去重**：同一神煞在多个工具里重复出现（如咸池/红鸾在 `bazi_romance` 与 `bazi_marriage` 各出现一次，且口径可能不同——romance 当机会、marriage 提醒防烂桃花），按当前场景**取一个口径讲一次**，不要当两件事讲两遍。

## §C 场景路由矩阵

每张表：行＝用户 query 意图，列＝候选工具，单元格＝ 主 / 旁 / 深（空＝该场景不调）。

### §C.1 命格 · 性格天赋六亲（onda-mingge）

| query 意图 | analyze_destiny | bazi_birth | bazi_personality | bazi_education | bazi_children | bazi_relatives | ziwei_birth | ziwei_rules | canping | heluo | astro_chart |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 我是个什么样的人 | 主 | | 旁 | | | | 主 | | | | 旁 |
| 我的天赋适合什么 | 主 | | 旁 | | | | 旁 | | | | |
| 学业考试运 | 旁 | | | 主 | | | 旁 | 深 | | | |
| 跟父母兄弟关系·原生家庭 | 旁 | | | | | 主 | 旁 | 深 | | | |
| 孩子的命 | 旁 | | | | 主 | | 旁 | 深 | | | |
| 想要一份完整命盘 | | 主 | | | | | 主 | 深 | 深 | 深 | 旁 |

> 去重：`analyze_destiny` 已含命盘+喜用+格局，调过它**不要**再调 `bazi_birth`；仅当用户明确要原始四柱/十神数据时单独调 `bazi_birth`。
> 主证：性格/天赋类由紫微（性格底色）+ 八字（十神格局）双主，西占仅作心理底色旁证。
> 深调：`ziwei_rules`/`canping`/`heluo` 为专家查表，普通场景不默认调用。

### §C.2 事业 · 财运（onda-shiye）

| query 意图 | bazi_career | bazi_wealth | two_person_compatibility | timing_analysis | dayun_analysis | liunian_analysis | analyze_destiny |
|---|---|---|---|---|---|---|---|
| 事业方向适不适合 | 主 | | | | | | 旁 |
| 今年财运 | | 主 | | 旁 | 旁 | 旁 | |
| 要不要跳槽 | 主 | | | 旁 | 旁 | 旁 | 旁 |
| 要不要创业 | 主 | 旁 | | 旁 | 旁 | | 旁 |
| 合伙靠不靠谱 | | | 主 | | | | 旁 |
| 求职方向 | 主 | | | | | | 旁 |
| 正财偏财·破财 | | 主 | | | | 旁 | 旁 |

> 去重：时运三工具（`timing_analysis`/`dayun_analysis`/`liunian_analysis`）聚合优先，只需全景时调 `timing_analysis`，仅需大运/流年细节再单独调对应工具。
> 主证：事业/财运以八字为主，时运类工具只作时机旁证，不单独下事业判断。
> 合伙场景：`two_person_compatibility` 看合作契合度，不替代八字事业分析。

### §C.3 缘分 · 感情合婚（onda-yuanfen）

| query 意图 | bazi_marriage | bazi_romance | two_person_compatibility | sukuyo_compatibility | ziwei_birth(夫妻宫) | astro_relative_chart | liuyue_analysis | 占卜类(meihua/sixyao) |
|---|---|---|---|---|---|---|---|---|
| 我的姻缘/感情走向 | 主 | 旁 | | | 旁 | | | |
| 正缘/桃花何时来、旺不旺 | 旁 | 主 | | | | | 深(追问到几月) | |
| 我俩合不合（恋爱/结婚） | | | 主 | 旁 | 深 | 深(需经纬度) | | |
| 关系的星盘视角/互动相位 | | | 旁 | | | 主(需经纬度) | | |
| 要不要表白 / 要不要复合 | | | | | | | | 主 |

> 去重：`bazi_romance` 与 `bazi_marriage` 同时跑时，咸池/红鸾等神煞会两处各出现一次且口径不同，按当前场景取一个口径讲一次（见 §B）。
> 粒度：`romance_timing` 只到流年级，要「几月」才升级 `liuyue_analysis`（见 §A.3）。
> 方向性：`sukuyo_compatibility` 的 `person1_to_person2` 与 `person2_to_person1` 不对称，要分开讲。

### §C.4 健康 · 养生（onda-jiankang）

| query 意图 | bazi_health | timing_analysis | liunian_analysis | analyze_destiny |
|---|---|---|---|---|
| 身体哪里弱 | 主 | | | 旁 |
| 今年健康要注意什么 | 主 | 旁 | 旁 | |
| 容易累睡不好情绪内耗 | 主 | | | 旁 |
| 五行养生调理方向 | 主 | | | 旁 |

> 主证：健康场景以 `bazi_health` 为唯一主证，时运类（`timing_analysis`/`liunian_analysis`）只提示今年身心影响，不单独下健康判断。
> 去重：`analyze_destiny` 含五行偏枯信息，调过后不重复拆讲五行，只补充未覆盖的具体健康方向。
> 触发：西占推运不在此域出现，健康追问到季节/月份才升级 `liunian_analysis` 或 `liuyue_analysis`。

### §C.5 时运 · 择时（onda-shiyun）

| query 意图 | timing_analysis | dayun_analysis | liunian_analysis | liuyue_analysis | liuri_analysis | liushi_analysis | western_timing_analysis | solarreturn | lunarreturn | transit | solararc | givenyear | profection | pd | pdchart | zr | firdaria | decennials | astro_election |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 今年/明年运势 | 主 | | 旁 | | | | 主 | 深 | | 深 | | | | | | | | | |
| 大运走到哪 | | 主 | | | | | | | | | | | | | | | | | |
| 人生转折点 | 旁 | 旁 | | | | | 旁 | | | | 旁 | | | 深 | | | 深 | 深 | |
| 最近为什么不顺·本命年 | | | 主 | 旁 | | | | | | 旁 | | | | | | | | | |
| 什么时候适合做某事·择日 | | | | | | | | | | | | | | | | | | | 主 |
| 人生各阶段（全生命周期） | 深 | 深 | | | | | 深 | 深 | 深 | 深 | 深 | 深 | 深 | 深 | 深 | 深 | 深 | 深 | |

> 聚合优先：全景时运用 `timing_analysis`（中式）或 `western_timing_analysis`（西占），不连发多个单技法。
> 粒度升级：年→`liunian_analysis`，月→`liuyue_analysis`，日→`liuri_analysis`，时→`liushi_analysis`，不许跨级说成「几月/几日」。
> 择日专属：`astro_election` 是唯一择日主证，不用时运聚合工具替代。
> 全生命周期：13 个西占单技法（`solarreturn`/`lunarreturn`/`transit`/`solararc`/`givenyear`/`profection`/`pd`/`pdchart`/`zr`/`firdaria`/`decennials` 等）仅在用户明确要「全生命周期」或专家模式时才深调。

### §C.6 星盘 · 西占本体（onda-xingpan）

| query 意图 | astro_chart | astro_chart13 | astro_hellen | astro_guolao | astro_india | astro_germany | astro_relative_chart | western_timing_analysis |
|---|---|---|---|---|---|---|---|---|
| 我的星盘/本命盘 | 主 | | | | | | | |
| 上升·太阳·月亮·行星落宫·相位 | 主 | | | | | | | |
| 13 星座盘 | | 主 | | | | | | |
| 希腊传统星盘 | | | 主 | | | | | |
| 果老星宗盘 | | | | 主 | | | | |
| 印度星盘（Jyotish） | | | | | 主 | | | |
| 德国占星/汉堡学派 | | | | | | 主 | | |
| 两人关系星盘 | | | | | | | 主 | |
| 推运/流年（从星盘延伸） | | | | | | | | 深 |

> 流派切换：`astro_chart` 通过 `chart_variant` 参数切换流派，已知具体流派时直接用对应工具（`astro_chart13`/`astro_hellen` 等），避免带参数的 `astro_chart` 与专用工具重复调用。
> 关系盘：`astro_relative_chart` 需双方经纬度，缺任一方位信息须先采集再调用。
> 衔接时运：星盘本体分析完成后若用户追问流年走势，指向 §C.5 时运域而非在此域重复调西占推运工具。

### §C.7 问事 · 抉择（onda-zhanbu）

| query 意图 | meihua_analysis | sixyao | qimen | liureng_gods | liureng_runyear | jinkou | taiyi | suzhan | sanshiunited | otherbu | astro_horary |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 要不要做某件事（即时起念） | 主 | | | | | | | | | | |
| 这事能不能成（具体成败） | | 主 | | | | | | | | | |
| 方位/时机/谋略布局 | | | 主 | | | | | | | | |
| 具体事件细节与时应 | | | | 主 | | | | | | | |
| 年运流月简断 | | | | | 主 | | | | | | |
| 即时简断吉凶 | | | | | | 主 | | | | | |
| 大势国运（深） | | | | | | | 主 | | | | |
| 宿曜择日/星宿吉凶 | | | | | | | | 主 | | | |
| 三式合参（太乙/六壬/奇门） | | | | | | | | | 主 | | |
| 西式随机问事（星骰） | | | | | | | | | | 主 | |
| 西式卜卦（Horary） | | | | | | | | | | | 主 |

> 何时选它（各工具触发一句话）：
> - **梅花易数**（`meihua_analysis`）：用户当下起念、随机取数，适合即兴一问。
> - **六爻**（`sixyao`）：问具体事能否成败，需明确一件事、一个方向。
> - **奇门遁甲**（`qimen`）：问方位选择、行动时机、谋略布局，含趋吉避凶方位。
> - **六壬**（`liureng_gods`）：问具体事件的细节展开与时间应验，信息量最密集。
> - **六壬年运**（`liureng_runyear`）：按年看流月走势，作为年度运势辅助参考。
> - **金口诀**（`jinkou`）：即时简断，快速给吉凶方向，适合快问快答。
> - **太乙神数**（`taiyi`）：看大势、国运、天地格局，不适合问个人小事。
> - **宿占**（`suzhan`）：以二十八宿星宿为核心，择日或问星宿吉凶应用。
> - **三式合参**（`sanshiunited`）：太乙+六壬+奇门联合推算，专家模式或重大决策才调。
> - **星骰**（`otherbu`）：西式随机问事，类似塔罗的即时占卜工具。
> - **西式卜卦**（`astro_horary`）：用起卦时刻星盘回答具体问题，Horary 占星传统。
>
> 去重：`gua_lookup`/`gua_meiyi` 为卦义查表支撑工具，不作为主问事工具调用，仅在解卦时辅助查义。

### §C.8 综合自我画像（onda-zige）

| query 意图 | analyze_destiny | ziwei_birth | astro_chart |
|---|---|---|---|
| 帮我全面分析一下 | 主 | 主 | 主 |
| 我是谁·完整人生说明书 | 主 | 主 | 主 |
| 综合看看我 | 主 | 主 | 主 |

> 三体系并行：此域是 §B 策略最密集的应用处，`analyze_destiny`（八字）、`ziwei_birth`（紫微）、`astro_chart`（西占）三系同时为主证，并行调用、并行出结论。
> 整合原则（按 §B）：三系一致 → 合并去重，用同一语言讲一次；三系分歧 → 显式标注「两套/三套口径不一」，各自呈现，不静默二选一，保留给用户权衡。
> token 控制：三个工具并行时务必用 `fields` 或 `selected_sections` 裁剪，不要对每个工具裸吐完整 `snapshot_text`，避免三倍 token 膨胀。
> 深追问：用户追问具体子域（如感情/事业/健康）时，切换到对应 §C.1–§C.7 的主证系统，不在此域重复展开专项工具。
