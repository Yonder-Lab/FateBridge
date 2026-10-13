# FateBridge 工作方式

先按用户请求识别任务：开发、安装、排错、代码审查与验收是工程任务；只要求排盘、看事业/关系/时运或解释计算结果是用户咨询。

## 用户咨询

- 当前消息完整给出人物资料的独立咨询是自包含任务，不需要仓库、项目历史或记忆中的人物资料。用户明确要求沿用历史资料时再核对。不要因正在这个仓库工作就先运行命令、查目录或安装诊断。
- 直接使用已连接 FateBridge 的参数 Schema 和工具描述。专项分析已自动推算大运/流年，首轮优先一项主证，必要时补旁证，不重复计算已有结果。
- 下方已核对合同覆盖的工具直接调用；其余工具可从代码模式的 `ALL_TOOLS` 条目获取说明和参数定义。检索时一次返回所需主证的完整条目，不先输出全部候选、再用一轮检索同一工具；不要只返回工具名而漏掉调用参数。事业/换工作首选 `bazi_career`，双人相处首选 `two_person_compatibility`，综合时运首选 `timing_analysis`；其他问题按用途选择，选择确有歧义才展开候选。拿到完整定义后直接计算。
- 资料缺失或日期明显无效时先一次简短追问，不提前检索工具或加载契约。缺出生时刻不猜时刻、不套示例。没有无时盘接口；时间未知时不承诺排盘。布局缺户型或朝向先问，未说明双人关系类型用 `general`。
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
{"tool":"bazi_career","input":{"additionalProperties":false,"properties":{"birth_year":{"type":"integer"},"birth_month":{"maximum":12,"minimum":1,"type":"integer"},"birth_day":{"maximum":31,"minimum":1,"type":"integer"},"birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"name":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"gender":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未知"},"birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"birth_place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"use_true_solar_time":{"type":"boolean","default":true},"analysis_year":{"anyOf":[{"type":"integer"},{"type":"null"}],"default":null},"analysis_month":{"anyOf":[{"maximum":12,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_day":{"anyOf":[{"maximum":31,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"dayun_pillar":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"liunian_pillar":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"compact":{"default":true,"type":"boolean"},"include_snapshot_text":{"default":true,"type":"boolean"},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"strict_fields":{"default":false,"type":"boolean"},"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null}},"required":["birth_year","birth_month","birth_day","birth_hour"],"type":"object"},"first_view":{"fields":["career_analysis.dominant_ten_gods.primary_career_type","career_analysis.career_timing","career_analysis.timing_context","career_analysis.career_structure","career_analysis.entrepreneurship","career_analysis.suggestions"],"strict_fields":true,"include_snapshot_text":false}}
```

### two_person_compatibility

```json
{"tool":"two_person_compatibility","input":{"additionalProperties":false,"properties":{"person1_name":{"type":"string"},"person1_birth_year":{"type":"integer"},"person1_birth_month":{"maximum":12,"minimum":1,"type":"integer"},"person1_birth_day":{"maximum":31,"minimum":1,"type":"integer"},"person1_birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"person2_name":{"type":"string"},"person2_birth_year":{"type":"integer"},"person2_birth_month":{"maximum":12,"minimum":1,"type":"integer"},"person2_birth_day":{"maximum":31,"minimum":1,"type":"integer"},"person2_birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"person1_gender":{"default":"未知","type":"string"},"person1_birth_place":{"default":"未提供","type":"string"},"person1_birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"person1_birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"person1_birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"person1_use_true_solar_time":{"type":"boolean","default":true},"person2_gender":{"default":"未知","type":"string"},"person2_birth_place":{"default":"未提供","type":"string"},"person2_birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"person2_birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"person2_birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"person2_use_true_solar_time":{"type":"boolean","default":true},"relationship_type":{"default":"general","type":"string"},"compact":{"default":true,"type":"boolean"},"include_snapshot_text":{"default":true,"type":"boolean"},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"strict_fields":{"default":false,"type":"boolean"},"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null}},"required":["person1_name","person1_birth_year","person1_birth_month","person1_birth_day","person1_birth_hour","person2_name","person2_birth_year","person2_birth_month","person2_birth_day","person2_birth_hour"],"type":"object"},"first_view":{"fields":["summary","strengths","challenges","traditional_compatibility","detailed_analysis","recommendations","person_info","element_relationship"],"strict_fields":true,"include_snapshot_text":false}}
```

### timing_analysis

```json
{"tool":"timing_analysis","input":{"additionalProperties":false,"properties":{"birth_year":{"type":"integer"},"birth_month":{"maximum":12,"minimum":1,"type":"integer"},"birth_day":{"maximum":31,"minimum":1,"type":"integer"},"birth_hour":{"maximum":23,"minimum":0,"type":"integer"},"name":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"gender":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未知"},"birth_minute":{"default":0,"maximum":59,"minimum":0,"type":"integer"},"birth_place":{"anyOf":[{"type":"string"},{"type":"null"}],"default":"未提供"},"birth_timezone":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"birth_longitude":{"anyOf":[{"maximum":180,"minimum":-180,"type":"number"},{"type":"null"}],"default":null},"use_true_solar_time":{"type":"boolean","default":true},"analysis_year":{"anyOf":[{"type":"integer"},{"type":"null"}],"default":null},"analysis_month":{"anyOf":[{"maximum":12,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_day":{"anyOf":[{"maximum":31,"minimum":1,"type":"integer"},{"type":"null"}],"default":null},"analysis_hour":{"anyOf":[{"maximum":23,"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"analysis_minute":{"anyOf":[{"maximum":59,"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"analysis_age":{"anyOf":[{"minimum":0,"type":"integer"},{"type":"null"}],"default":null},"selected_sections":{"default":[],"items":{"type":"string"},"type":"array"},"compact":{"default":true,"type":"boolean"},"include_snapshot_text":{"default":true,"type":"boolean"},"fields":{"anyOf":[{"items":{"type":"string"},"type":"array"},{"type":"null"}],"default":null},"strict_fields":{"default":false,"type":"boolean"},"as_of":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"trace_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null},"parent_run_id":{"anyOf":[{"type":"string"},{"type":"null"}],"default":null}},"required":["birth_year","birth_month","birth_day","birth_hour"],"type":"object"},"first_view":{"fields":["dayun_analysis","liunian_analysis","liuyue_analysis","comprehensive_summary","personal_info.analysis_datetime","personal_info.time_adjustment","analysis_calendar.analysis_date_context.timezone","analysis_calendar.analysis_date_context.current_solar_term","analysis_calendar.analysis_date_context.next_solar_term","analysis_calendar.analysis_date_context.bazi_month_boundary"],"strict_fields":true,"include_snapshot_text":false}}
```

<!-- codex-call-contracts:end -->
