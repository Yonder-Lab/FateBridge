# FateBridge 工作方式

先按用户请求识别任务：开发、安装、排错、代码审查与验收是工程任务；只要求排盘、看事业/关系/时运或解释计算结果是用户咨询。

## 用户咨询

- 当前消息完整给出人物资料的独立咨询是自包含任务，不需要仓库、项目历史或记忆中的人物资料。用户明确要求沿用历史资料时再核对。不要因正在这个仓库工作就先运行命令、查目录或安装诊断。
- 直接使用已连接 FateBridge 的参数 Schema 和工具描述。专项分析已自动推算大运/流年，首轮优先一项主证，必要时补旁证，不重复计算已有结果。
- 下方已核对合同覆盖的工具直接调用；其余工具可从代码模式的 `ALL_TOOLS` 条目获取说明和参数定义。检索时一次返回所需主证的完整条目，不先输出全部候选、再用一轮检索同一工具；不要只返回工具名而漏掉调用参数。事业/换工作首选 `bazi_career`，双人相处首选 `two_person_compatibility`，综合时运首选 `timing_analysis`；其他问题按用途选择，选择确有歧义才展开候选。拿到完整定义后直接计算。
- 按所选计算核对必要资料，必要信息缺失或日期明显无效时一次简短追问。八字/紫微排盘缺出生时刻不能猜；命卦支持 `birth_date`，非立春当日不需要出生小时。未说明双人关系类型用 `general`。
- 风水布局使用通用 `fengshui_assess`，设 `analyze_layout=true`，让已确认布局进入计算。位置与朝向分开，未知项省略并保留部分结果，不把桌朝向当住宅坐向或对象落宫。根据计算说明是否调整位置/朝向、匹配方位和元素关系；形峦及具体物件效力缺少规则时明确标注，不用收纳建议代替风水计算。按工具名限定 `ALL_TOOLS`，避免匹配所有工具共有的说明；使用描述中的首轮字段直接调用。
- 布局建议结合用户目的及已说明的搬动、转向、预算和多人共用约束；缺少某项约束不阻塞已具备资料的部分计算，只在会改变行动选择时简短追问。匹配方位仅是规则候选，先核对现实可行性再建议搬动；无共同方向或无可行调整时保留权衡，不以摆件替代布局结论。后续用户更正位置、朝向、观察或使用人时，以最新确认替换旧事实，重建受影响计算的输入并沿用 `trace_id`/`parent_run_id`；只解释未改变的结果无需重算。
- 当前方向布局对象支持门、床、书桌、灶，室内形态支持床、书桌、灶；沙发、书柜、餐桌等其他家具不映射为这些用途。先说明未支持的规则范围，能给的生活建议单独标明，不承诺工具已计算其他家具的吉凶。
- 独立形态只需 `form_observations`，不构造没有已知位置或朝向的 `placements` 占位对象。观察字段只保留用户确认的粒度：入口可见不能补出具体相对位置，换座位后未重新确认的旧位置不沿用；其他未知项同理。
- 室内形态关系用 `form_observations`；独立分析可 `methods=[]`，无需生辰/宅向。入口相对位置、可见性、直线和实体背靠分别确认，距离不套通用吉凶阈值，照片观察仅作候选。元素方案用 `element_adjustments` 绑定已算事实、作用域和明确调节目标，按作者版本给条件式物件/颜色，不推断缺五行；年度规则须显式选版本且不外推年份，作者分歧保留。
- 使用经过验证的首轮 `fields`、`strict_fields=true`、`include_snapshot_text=false`。只在当前问题需要时展开完整契约或全年时间线。
- 首轮先回答要点，给2–3条实际依据和一项现实建议，通常约200–300字。技术回执留在工具结果，精度警告需说明。区分传统规则与现实建议，分数不是成功概率，不替用户决定辞职或关系成败。

## 工程任务

按现有工程流程检查当前源代码、适用历史、共享契约和相关测试，保留用户改动。咨询流程的简短输出要求不适用于开发、根因分析或完整验收报告。修改共享计算和跨传输契约时验证 REST、MCP、CLI 的一致性；真实模型对话与本地测试分别报告。

<!-- codex-call-contracts:begin -->
## 已核对的常用 MCP 调用合同

此段由 `scripts/build_codex_call_contracts.py` 从实际 MCP inputSchema 与共享首轮字段生成，只删标题和说明，保留全部参数、默认值、必填项与约束。更新接口后重新生成，检查模式用 `--check`。

下面三项工具已具备调用所需定义。当前公历资料齐全且工具在连接中公开时，直接调用 `tools.mcp__fatebridge__<tool>(参数)`，无需先检索或打印 ALL_TOOLS。如需确认公开范围，可在同一次 exec 中检查 ALL_TOOLS 的名称并调用，不另起发现往返。合同未覆盖的工具或参数疑问再读取实际工具定义，不猜测。

使用用户已确认的资料，不把接口默认值当成用户已提供的出生小时。这些出生接口使用公历，农历资料需先正确转换。出生日期/小时使用 birth_*（双人分别 person1_/person2_），分析日期使用 analysis_*；as_of 是带时区的 ISO 时间，仅冻结未显式指定的当前时间。性别接受男/女等已确认写法；出生时区是 IANA 名称或 UTC 偏移。太阳时默认开启；仅按用户明确要求关闭。未知经度可省略，以返回精度说明限制，不能猜经度。birth_latitude 不在这些工具的参数中。未指明双人关系类型用 general，不要自行传入大运/流年柱覆盖自动计算。结果仍按实际返回字段、精度和回执解读。

### bazi_career

```json
{"first_view":{"fields":["career_analysis.dominant_ten_gods.primary_career_type","career_analysis.career_timing","career_analysis.timing_context","career_analysis.career_structure","career_analysis.entrepreneurship","career_analysis.suggestions"],"include_snapshot_text":false,"strict_fields":true},"input":{"additionalProperties":false,"properties":{"analysis_day":{"anyOf":[{"maximum":31,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_month":{"anyOf":[{"maximum":12,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_year":{"anyOf":[{"type":"integer"},{"type":"null"}],"default":null},"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_day":{"maximum":31,"minimum":1,"type":"integer"},"birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"birth_month":{"maximum":12,"minimum":1,"type":"integer"},"birth_place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_year":{"type":"integer"},"compact":{"default":true,"type":"boolean"},"dayun_pillar":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"gender":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未知"},"include_snapshot_text":{"default":true,"type":"boolean"},"liunian_pillar":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"name":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"strict_fields":{"default":false,"type":"boolean"},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"use_true_solar_time":{"default":true,"type":"boolean"}},"required":["birth_year","birth_month","birth_day","birth_hour"],"type":"object"},"tool":"bazi_career"}
```

### two_person_compatibility

```json
{"first_view":{"fields":["summary","strengths","challenges","traditional_compatibility","detailed_analysis","recommendations","person_info","element_relationship"],"include_snapshot_text":false,"strict_fields":true},"input":{"additionalProperties":false,"properties":{"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"compact":{"default":true,"type":"boolean"},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"include_snapshot_text":{"default":true,"type":"boolean"},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"person1_birth_day":{"maximum":31,"minimum":1,"type":"integer"},"person1_birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"person1_birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"person1_birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"person1_birth_month":{"maximum":12,"minimum":1,"type":"integer"},"person1_birth_place":{"default":"未提供","type":"string"},"person1_birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"person1_birth_year":{"type":"integer"},"person1_gender":{"default":"未知","type":"string"},"person1_name":{"type":"string"},"person1_use_true_solar_time":{"default":true,"type":"boolean"},"person2_birth_day":{"maximum":31,"minimum":1,"type":"integer"},"person2_birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"person2_birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"person2_birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"person2_birth_month":{"maximum":12,"minimum":1,"type":"integer"},"person2_birth_place":{"default":"未提供","type":"string"},"person2_birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"person2_birth_year":{"type":"integer"},"person2_gender":{"default":"未知","type":"string"},"person2_name":{"type":"string"},"person2_use_true_solar_time":{"default":true,"type":"boolean"},"relationship_type":{"default":"general","type":"string"},"strict_fields":{"default":false,"type":"boolean"},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null}},"required":["person1_name","person1_birth_year","person1_birth_month","person1_birth_day","person1_birth_hour","person2_name","person2_birth_year","person2_birth_month","person2_birth_day","person2_birth_hour"],"type":"object"},"tool":"two_person_compatibility"}
```

### timing_analysis

```json
{"first_view":{"fields":["dayun_analysis","liunian_analysis","liuyue_analysis","comprehensive_summary","personal_info.analysis_datetime","personal_info.time_adjustment","analysis_calendar.analysis_date_context.timezone","analysis_calendar.analysis_date_context.current_solar_term","analysis_calendar.analysis_date_context.next_solar_term","analysis_calendar.analysis_date_context.bazi_month_boundary"],"include_snapshot_text":false,"strict_fields":true},"input":{"additionalProperties":false,"properties":{"analysis_age":{"anyOf":[{"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"analysis_day":{"anyOf":[{"maximum":31,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_hour":{"anyOf":[{"maximum":23,"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"analysis_minute":{"anyOf":[{"maximum":59,"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"analysis_month":{"anyOf":[{"maximum":12,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_year":{"anyOf":[{"type":"integer"},{"type":"null"}],"default":null},"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_day":{"maximum":31,"minimum":1,"type":"integer"},"birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"birth_month":{"maximum":12,"minimum":1,"type":"integer"},"birth_place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_year":{"type":"integer"},"compact":{"default":true,"type":"boolean"},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"gender":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未知"},"include_snapshot_text":{"default":true,"type":"boolean"},"name":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"selected_sections":{"default":[],"items":{"type":"string"},"type":"array"},"strict_fields":{"default":false,"type":"boolean"},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"use_true_solar_time":{"default":true,"type":"boolean"}},"required":["birth_year","birth_month","birth_day","birth_hour"],"type":"object"},"tool":"timing_analysis"}
```

<!-- codex-call-contracts:end -->
