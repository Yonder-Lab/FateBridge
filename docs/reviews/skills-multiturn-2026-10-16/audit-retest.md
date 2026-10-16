> 本副本仅将临时归档链接改为本目录；审查正文未改，原文另存 `.raw.md`。

# FateBridge 自然多轮咨询：独立复测审查

**j/k/l 全部通过：3个案例、12轮，7次真实工具调用均成功。** 未发现新增输入、返回事实或解释范围错误。j首轮投影失败消失；l补清混合总分局限；k开头说明粒度并使用真实2027月线。年度广取后再补聚合的效率问题仍在，不能算已解决。

m已在独立 [audit-holdout.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/audit-holdout.md) 中审查，其两轮不计入本报告j/k/l的通过数量。

## 范围与证据

- 逐轮读取j/k/l用户、答复、skills-read、真实record和result-reads；对延后字段读取metadata登记的同run审查快照。没有调用FateBridge、重算或改写任何原证据/项目/答复。
- 与原g/c/b原始成功结果和相关错误逐项比较；不以本轮回答更长、字段更多或调用数量更多作为改善。
- 对k新年度月级数据做根审查员逐项核对，并由独立子审查员audit_k并行复核，结论一致。没有向咨询代理发送任何信息。
- 7份raw record及4份延后快照登记SHA-256全部匹配；5条result读取路径与字段都能链接到同run。校验是归档一致性与支持链核查，不是现实预测效力证明。
- 以revised/skills冻结版本审查复测；不把根代理随后拟做的进一步优化视为本轮已经解决。

本报告评价调用与具体咨询可用性，不验证命理/占星的现实预测效力。独立上下文属性按本次运行安排描述，不能仅由结果文件证明全部上下文隔离。

## 与基线的逐项比较

| 基线问题 | 复测 | 判定 | 实际变化 |
|---|---|---|---|
| G-01 | dialogue_j | resolved_in_observed_retest | 3套主证各1次成功，无错误或资源发现回退。analyze_destiny使用根字段，astro_chart使用person_info，ziwei使用ziwei_birth.*。 |
| G-02 | dialogue_j | wording_improved | 改为“该版本收录的特殊主格”，保留扶抑/喜用的实际范围，不再倾倒内部白名单词。 |
| C-01 | dialogue_k | resolved_in_observed_retest | 开头明确粒度不同，随后实际使用2027各节气月与2026年10月月证对照，不宣称2027全年更顺/收入更多/压力更高。 |
| C-02 | dialogue_k | not_resolved | fields=null流年广取及再补聚合的绕路仍在，见K-01；不能因为共享说明已改便视为通过该项。 |
| B-01 | dialogue_l | delivery_explanation_fixed_upstream_metric_unchanged | 明确总分混合个人结构与跨盘规则；仍使用真实54.5，没有剔除项目手算新分。两轮原始business_output_sha256完全相同，评分算法与该数据没有因解释优化而改变。 |

判改善的依据是失败调用消失、字段/作用域说明更准确、月份对照有实际数据支持；没有按回答长度、术语数量或调用数量计分。

## 保留问题

### K-01 · P3 · 2027仍先取全量流年及出生历法，再补所需聚合月线

turn-03/000001 的 liunian_analysis 使用target_year=2027、fields=null，取回snapshot_export并延后calendar_context；result-reads显示实际读取了calendar_context，但它是1990-05-15出生历法。之后000002 timing_analysis才取得2027年analysis_calendar.liuyue_timeline并用于答复。

本次比较口径与真实月级覆盖已改善，首次年度取数绕路却没有解决。liunian里的年度干支/节气与随后聚合有重叠，出生calendar_context对最终年/月比较帮助有限；但第二次聚合确实补足前一次没有的月级数据，不能把它判成无效重算。没有把出生历法错写成2027，也没有因此产生错误结论。

建议：目标年改变且仍要大运/月度节奏比较时，直接构造新目标聚合并保留所需月线；纯流年窄查询才选liunian已验证字段。保留真实需要的月级数据，不通过删去必要计算来追求更少调用。

证据：

- [000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000001.json) · `record.arguments.fields; response.snapshot_export; result_delivery.deferred_fields`
- [result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/result-reads.json) · `[0].fields; [0].command; [1].fields` · 分别读取出生calendar_context与新目标月线
- [000001-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/audit-deferred/000001-001-1.bin) · `payload.calendar_context.solar_datetime` · 出生历法1990-05-15
- [000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000002.json) · `record.arguments.fields; response.result_delivery`
- [000002-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/audit-deferred/000002-001-1.bin) · `payload.analysis_calendar.liuyue_timeline` · 最终真正使用的月级证据

## 归档边界

- l的skills-read.json只登记onda-yuanfen入口；冻结技能依然列shared engine、counsel与scenario-routing为必读。现有归档没有这三份引用的原始读取命令。 只据此记录引用读取归档不足，不能确认实际未读，也不回填路径或否定已由真实数据支持的答复。j完整登记入口与共享引用；k首轮已登记共享引用，后续可复用。
- k/l共有5条result-reads记录，包含原交付路径、字段与打印命令；全部链接到对应raw record的result_delivery/file_path及同run快照，字段真实存在。 这些记录比基线只保留延后快照/事后说明更便于复核，但该文件本身未附每次stdout、exit_code或独立平台执行证明。本报告确认路径、字段和数据支持链，不将recorder复制本身当模型自动消费。j没有延后结果，后续无需本地结果文件读取。

上游关系指标仍包含个人事件。l只是如实解释54.5的范围，没有修改算法；原b与l的业务payload散列相同。

## 逐case、逐轮审查

### dialogue_j / case_07 · pass

输入：男，公历1990-05-15，北京当地10:30，Asia/Shanghai、116.4074/39.9042均正确；中式工具不传纬度，真太阳时开启；西占保留民用钟时且hsys=3/zodiacal=0与Placidus/回归黄道一致。三套主证均是初算，不需绑定同一run或把太阳时开关强灌三系。严格投影与无快照文本均正确。

实际主证：

- `astro_chart`：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000001.json)；run `147cf44448e84d8daeb078410e8afea7`
- `analyze_destiny`：[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000002.json)；run `11ea5336095b49cd879f8c228a5111f3`
- `ziwei_birth`：[000003.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000003.json)；run `d76dce265bc843a8afc307779c387539`

读到的数据与支持链：

- 八字庚午/辛巳/庚辰/辛巳、庚金中和，天干比劫多见，扶抑调候喜金；element_distribution木/水各3.7，basis明确结构计数未含月令权重。 自主/同辈的传统读法、比例不当缺陷/补物建议有据；并未把最大元素当喜用。
  证据：[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000002.json) `response.four_pillars; day_master; ten_gods; structure_profile; element_distribution_basis`
- 命宫子破军庙，官禄贪狼庙，夫妻戌武曲庙化权，身宫戌；仆役巨门旺/文昌庙。 性格变化、职业兴趣联系、关系责任分工与新增协作线索都有对应宫位stars_detail支持，没有只凭命身宫位置补星。
  证据：[000003.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000003.json) `response.ziwei_birth.palaces; shen_gong; sihua`
- 西占日金牛11宫、月摩羯6宫、上升巨蟹、MC白羊；日土三分、月土合、水天三分、金星白羊与天/海四分。出生datetime为10:30+09:00。 稳定/承担与改变/新办法的分歧真实，能解释工作方式与关系观察。没有由单人盘断伴侣，也没有静态盘推半年。
  证据：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/000001.json) `response.angles; planets; aspects; person_info`
- 与g成功主证逐字段比较：astro angles/planets/aspects/interpretation/person_info、八字四柱/日主/十神/结构/basis/人物、紫微ziwei_birth/analysis_context均相同。 首轮调用改进没有改变所解释的基本盘面；astro仅宫制来源从默认变为explicit，选择仍是同一Placidus。
  证据：[000006.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_g/turn-01/000006.json)；[000007.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_g/turn-01/000007.json)；[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_g/turn-01/000002.json)

逐轮：

- 第1轮 **pass**：三套主证一次成功，按生活主题交付并保留稳定/变化张力；来源与时间口径可核。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-01/assistant.md)
- 第2轮 **pass**：区分自主、改进、长期交付的各自来源；八字金与金牛、不同行星庙旺不混成能力分，未为展开再算。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-02/assistant.md)
- 第3轮 **pass**：区分侧面不同、真实分歧和未覆盖；拒绝挑高分、平均总分及三票验证，允许现实不贴合。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-03/assistant.md)
- 第4轮 **pass**：工作先确认标准再试一个环节、相处表达具体请求，各有反馈；半年只是观察周期。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_j/turn-04/assistant.md)

复用与trace：仅turn-01有3次tool；turn-02至04均复用，没有重排、时运或本地结果读取。三系首次run各自独立，符合范围。

可用性：保留原本可用的三系对照，并把岗位标准/判断空间、关系请求落成小实验；新增团队线索有实际宫位证据。详细程度符合全面请求，但更长本身不计改进；首轮技术失败减少才是明确进步。

问题：未发现实质咨询错误。

### dialogue_k / case_03 · pass

输入：缺时刻先追问；补齐后本人男、1990-05-15 10:30、北京、Asia/Shanghai正确，未猜经度、未传纬度，太阳时保持默认开启。2026指定10月返回10-01 00:00锚点；2027聚合analysis_year=2027且as_of沿用，默认月取冻结时钟的10月，实际锚点2027-10-01 00:00。答复明确“此次大运定位”，没有将10月锚点冒充全年逐时核对。真正月份对照来自同run2027年度月线。

实际主证：

- `timing_analysis 2026/10`：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-02/000001.json)；run `9551f08069004e1884798e156c76767c`
- `liunian_analysis 2027`：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000001.json)；run `4fe7a9a541ff43f9983bd0cc32214778`
- `timing_analysis 2027 + 实际月线`：[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000002.json)；run `f6e21a0cb1d241c7acca9567d0e2e8a6`

读到的数据与支持链：

- 2026月线丁酉正官/六合至10-08 14:29:18，之后戊戌偏印/六冲；分析日历时区Asia/Shanghai。 第2轮整个月分段准确，十神用作职责/研究的传统提示，不由冲断工作变动或支出损失。
  证据：[000001-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-02/audit-deferred/000001-001-1.bin) `payload.analysis_calendar.liuyue_timeline[8:10]`；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-02/result-reads.json)
- 2027聚合大运甲申、流年丁未，月线实际4/5–6/6偏财→正财，6/6–7/7七杀，7/7–10/8正官→偏印→正印且六合，10/8起比肩六冲，11/7–12/7劫财六冲。 第3轮所述月份均有对应真实条目，且与2026寒露后偏印/六冲用同月级数据对照。日期省略小时，但明确按北京时当天节气交接，不误导整日零点换月。没有把五行增强译成全年更顺或钱更多。
  证据：[000002-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/audit-deferred/000002-001-1.bin) `payload.analysis_calendar.liuyue_timeline`；[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000002.json) `response.dayun_analysis; liunian_analysis`；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/result-reads.json) `[1]`
- 三个run共同trace_id=bda943c8f63e4c82960811da24560447，parent依次接续；三条result读取分别命中对应file_path与快照字段。 更换目标年份有新计算，解释旧月证复用。年度窄查和出生calendar_context读取虽冗余，没有把旧run或出生日期冒充新月份。
  证据：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-02/000001.json) `response.run_metadata`；[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000001.json) `response.run_metadata`；[000002.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/000002.json) `response.run_metadata`

2027真实月级条目（北京时，原始数组索引）：

| 索引 | 窗口 | 柱与摘要 |
|---|---|---|
| [3] | 2027-04-05 08:17:30 – 2027-05-06 01:25:12 | 2027年4月流月甲辰(覆灯火)，十神偏财，总体运势小吉。 |
| [4] | 2027-05-06 01:25:12 – 2027-06-06 05:25:49 | 2027年5月流月乙巳(覆灯火)，十神正财，总体运势小吉。 |
| [5] | 2027-06-06 05:25:49 – 2027-07-07 15:37:04 | 2027年6月流月丙午(天河水)，十神七杀，总体运势小凶。 |
| [6] | 2027-07-07 15:37:04 – 2027-08-08 01:26:46 | 2027年7月流月丁未(天河水)，十神正官，总体运势大吉，有六合关系。 |
| [7] | 2027-08-08 01:26:46 – 2027-09-08 04:28:27 | 2027年8月流月戊申(大驿土)，十神偏印，总体运势大吉，有六合、六合关系。 |
| [8] | 2027-09-08 04:28:27 – 2027-10-08 20:17:05 | 2027年9月流月己酉(大驿土)，十神正印，总体运势大吉，有六合关系。 |
| [9] | 2027-10-08 20:17:05 – 2027-11-07 23:38:34 | 2027年10月流月庚戌(钗钏金)，十神比肩，总体运势小凶，有六冲关系。 |
| [10] | 2027-11-07 23:38:34 – 2027-12-07 16:37:41 | 2027年11月流月辛亥(钗钏金)，十神劫财，总体运势大凶，有六冲、六冲关系。 |

逐轮：

- 第1轮 **pass**：不猜出生时刻，简短保留时段不确定性。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-01/assistant.md)
- 第2轮 **pass**：按真实寒露月界分两段；预算先按实际课程目的与可投入时间筛选。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-02/assistant.md)
- 第3轮 **pass**：开头即说明年/月不可直接判强弱，再用真实2027月线解释；无新增事实错误，存在K-01取数绕路。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-03/assistant.md)
- 第4轮 **pass**：预算看承受能力，财星/劫财不作为加码或认亏理由；复盘允许未出现，不为解释重算。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-04/assistant.md)；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_k/turn-04/result-reads.json)

复用与trace：目标年变化后才新算；T4无tool和本地读取。T3新增聚合补足月线，属于有用补充；首个全量liunian属于可避免绕路，单列P3，不影响本次交付pass。

可用性：真实区别已变成工作责任/配合/学习与款项核对提醒；最后把它收回预算上限、任务成果和未出现记录。没有借更多月份强行制造收入强弱；也未用月级标签替用户决定课程付款。

问题：K-01

### dialogue_l / case_02 · pass

输入：首轮许晴缺出生小时，未调用。补齐后person1林舟男1990-05-15 10:30、person2许晴女1992-03-02 08:30、北京/Asia/Shanghai均正确，两人真太阳时明确开启，未猜精确经度；relationship_type=general，未擅定恋爱/婚姻。严格投影与无快照文本正确。

实际主证：

- `two_person_compatibility`：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/000001.json)；run `e3a4b70743cd41149c18ce75ca16e325`

读到的数据与支持链：

- summary.overall_score=54.5；ten_gods_relationship双向承接与共同可用比肩/劫财；寅午/巳丑为cross_person、描述一方受益一方承压。 T2实际使用一处互助与两处跨盘张力，不用日主相克直接诊断双方心理，承认节奏差异来自用户所述。
  证据：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/000001.json) `response.summary; strengths`；[000001-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/audit-deferred/000001-001-1.bin) `payload.detailed_analysis.ten_gods_relationship; pattern_synergy.tension_patterns`；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/result-reads.json)
- 寅申六冲source_scope=person2，source_map两支均女方；同项仍在格局score_basis中(-12)。 T3既分个人与双人证据，也明确该个人事件参与格局配合分、进而总分混合作用域。保留实际54.5，没有算新净分或转概率。
  证据：[000001-001-1.bin](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/audit-deferred/000001-001-1.bin) `payload.detailed_analysis.pattern_synergy.risk_patterns; score_basis`；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-03/result-reads.json)；[assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-03/assistant.md:12)
- 原b与复测l的business_output_sha256同为9c5e27d12990bcc656a34e1f788de7f28950cd8549eed85712d9b1b9b994ea47。 解释优化是对同样业务数据增加准确范围说明，而非换数据、调分或迎合结果；上游指标混合仍在。
  证据：[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_b/turn-02/000001.json) `response.run_metadata.business_output_sha256`；[000001.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/000001.json) `response.run_metadata.business_output_sha256`

逐轮：

- 第1轮 **pass**：只补女方时刻，也允许先讨论真实相处，不强索关系身份。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-01/assistant.md)
- 第2轮 **pass**：双向承接/跨盘承压有据，约定暂停及回来时间属于现实沟通建议。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-02/assistant.md)
- 第3轮 **pass**：准确说明54.5非概率、跨盘与个人范围及混合总分局限，读取的是原同run文件。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-03/assistant.md)；[result-reads.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-03/result-reads.json)
- 第4轮 **pass**：当下确认会谈、约定具体恢复、需要延期则重约；不替双方定动机或谁必须迁就。 [assistant.md](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/runs/dialogue_l/turn-04/assistant.md)

复用与trace：只有T2一次计算。T3窄读原T2同file_path的score_basis/source_scope，不重算。T4直接复用，无工具。共享引用读取归档不足见L-E01，不以此推断内容未遵循。

可用性：保留原本有效的沟通方案，新增的分数局限解释与用户第3问直接相关。第4轮明确可以由对方提可行时间、一次回应不代表关系，不以技术指标取代双方商量。

问题：未发现实质咨询错误。
归档边界：L-E01

## 下一步仅需小范围改进

- 先修K-01：新目标年仍要月度/大运时直接聚合，纯流年才窄投影；不改现有正确月份解读。
- 继续保留l的实际总分与混合作用域说明；评分算法未改变，不能把解释完善标成模型修复。
- 统一共享引用与本地结果读取的当次记录，保留缺失历史证据的边界。

本报告未修改基线或复测答复；完整字段、run、散列与读取链见 [audit-retest.json](/Users/thomas/Desktop/FateBridge/docs/reviews/skills-multiturn-2026-10-16/audit-retest.json)。
