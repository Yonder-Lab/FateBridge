# 玄空运山向宅盘：版本、输入和验证

`fengshui_xuankong_natal` 的 REST 入口为 `POST /api/fengshui/xuankong_natal`，MCP 与 CLI 同名。选定版本 `xuankong_zhongzhou_v1@1.0.1` 完整计算九宫运星、山星、向星，支持下卦和中州派兼向替星。与 `layers.annual_stars` 独立；查询年份变化不改变历史宅盘。基础三法合同见[家居风水](fengshui.md)。

## 规则核实和版本选择

本实现锁定一套明确的中州派网页传法，不能把结果称为所有玄空门派统一结论，也不是《沈氏玄空学》原版的逐页复刻。生产规则为离线 [xuankong-v1.json](../src/fatebridge/data/fengshui/xuankong-v1.json)，原有第一阶段规则文件和版本保持不变。规则语义变化须另建版本及独立样本；1.0.1修复既定角区的浮点实现与不确定输入处理，五黄和替星表未改。

| 事项 | 本版本约定 | 核实来源与版本限制 |
| --- | --- | --- |
| 三元九运 | 1864一运锚点，20年一运，180年循环 | X1《沈氏玄空学》卷四网络转录“玄空浅说”；不是认证印刷版 |
| 住宅定运 | 调用方选择历史竣工、首次入住、已确认换运的大修或专家确认宅运，并提供证据 | X2涉及搬迁／装修；X4陈癸龙讨论现代大厦换天心与普通装修不能直接换运；存在门派和建筑条件分歧，不自动选择最新事件 |
| 日期定运 | 带时区事件时刻按立春换年；明确有效年表示已确认交节归属 | 本实现的显式工程约定，不能以年度换年证据声称住宅事件选择也无争议；逐项暴露实际节气求解器；跨运年份事件时刻遇近似回退须确认有效年或宅运；X6只核对2024日期和分钟 |
| 二十四山 | 每山15°，子0°，顺时针；坐山＝向首＋180° | X1及X2对应表，使用磁北，不自动将真北转磁北 |
| 三元龙阴阳 | 先查运星本宫中与物理山向同一元龙的山，阳顺阴逆 | X1/X2；不能直接按星数奇偶或物理山的阴阳起所有山向盘 |
| 五黄入中 | 借宅运所属卦的同元龙阴阳，仍以5入中，不替星 | X2公开七运卯酉盘；X3 AFSI 2005教材印刷页8–9交叉核对。其PDF经网页工具核实，直接下载403，未登记虚构文件散列 |
| 五运 | 五入中顺飞为元旦盘；外宫山向原星不会是5 | X1及洛书固定数；这里不需要五运前后十年寄宫，不混用分金寄卦规则 |
| 下卦／替卦 | 正中9°，两边各3°；同宫同阴阳仍用下卦，异阴阳或跨宫兼向用替 | X2所载中州派；不是“所有偏离中心超过4.5°一律替星”的版本 |
| 替星 | 在原星所属卦的同元龙找到替星，以原元龙阴阳飞布 | X2替星口诀及完整公开盘例；替后的星不能重新决定阴阳 |
| 分界 | 恰在山界或下／替分界取两侧候选；误差区间内全部角区枚举 | FateBridge明确的保守应用约定，古籍没有现代浮点端点合同 |

来源均在响应 `rulesets[].sources` 返回名称、URL、作用范围和版本；X1/X2/X4/X5登记2026-10-12获取网页的 SHA-256，便于发现网页更新。网页散列用于追溯，不声称具有古籍校勘权威。

- [X1：沈氏玄空学卷四](https://www.diancangwang.cn/xuanxuewushu/f6f37803664b/90b563d9cb41.html)
- [X2：玄霖易学《第一篇 玄空基础2》](https://xuanlinyi.com/article_detail?id=301282)
- [X3：AFSI 2005教材，印刷页8–9](https://www.amfengshui.com/wp-content/uploads/2014/06/fs340.pdf)
- [X4：陈癸龙《大厦元运及换天心》](https://www.xuankongguan.com/guide-detail/%E5%A4%A7%E5%BB%88%E5%85%83%E9%81%8B%E5%8F%8A%E6%8F%9B%E5%A4%A9%E5%BF%83)
- [X5：沈氏玄空学卷二，五黄寄宫多种说法](https://www.diancangwang.cn/xuanxuewushu/f6f37803664b/34f0e0aa12ff.html)
- [X6：香港天文学会2024-02-04立春当日公告](https://hkas.org.hk/2024/02/04/%E7%AB%8B%E6%98%A5-9/)：仅核对当日16:27，不能认证秒精度或住宅定运事件。登记Firecrawl提取Markdown的SHA-256和格式，未冒称原HTML散列。

X2网页有明显笔误：“阳阳互兼用替”与随后同阳不替的例子冲突；所谓十一山清单重复列入13项口诀中的山、数量也不一致。本版本采用紧接其后的明确文字和图例，以13项口诀的24山补集界定其余11山，未照抄错误清单。X5也明确讨论不同寄法；不把这些寄卦概念直接混进外宫五黄入中。规则核实后的选版与校订范围均登记在 `conventions`。

三元龙表：

| 元龙 | 阳 | 阴 |
| --- | --- | --- |
| 地元 | 壬甲丙庚 | 辰戌丑未 |
| 天元 | 乾巽艮坤 | 子午卯酉 |
| 人元 | 寅申巳亥 | 乙辛丁癸 |

替星表：甲申→1，壬卯乙→2，丑艮丙→7，辰巽巳→6，庚寅→9；其他11山保持原入中星。查的是**运星所属卦的同元龙**，不是看到物理“庚向”就一概用9入中。

## 三端调用

可复制 [独立宅盘请求](examples/fengshui-xuankong.json) 和 [基础三法＋宅盘＋年星合参](examples/fengshui-xuankong-with-annual.json)。

```json
{
  "house": {"object_id": "home", "facing_degrees": 255, "north_reference": "magnetic"},
  "period": {
    "basis": "construction_completion",
    "effective_event_year": 2004,
    "evidence": "已核实立春后竣工，按竣工事件定运"
  },
  "bearing_uncertainty_degrees": 0,
  "ruleset_id": "xuankong_zhongzhou_v1"
}
```

```bash
curl -X POST http://localhost:8010/api/fengshui/xuankong_natal \
  -H 'Content-Type: application/json' \
  --data-binary @docs/examples/fengshui-xuankong.json

fatebridge fengshui_xuankong_natal --request-file docs/examples/fengshui-xuankong.json
fatebridge fengshui_assess --request-file docs/examples/fengshui-xuankong-with-annual.json
fatebridge describe fengshui_xuankong_natal
```

MCP `fengshui_xuankong_natal` 的参数就是上面 JSON 对象。认证设置与其他REST端点一致；工具目录、发现接口、JSON输出schema、错误、字段投影和运行元数据均来自共用目录。CLI也支持 `--house '{...}' --period '{...}'`；请求文件保留未知字段供模型拒绝，不静默删除。

聚合需显式选择 `methods` 中的 `xuankong_natal`，并传 `xuankong` 请求；默认仍是基础三法。内层未提供 `house` 时继承顶层住宅；同时提供时必须一致。年星继续用顶层 `effective_year` 或 `query_at`；宅盘只用 `xuankong.period`，两者不互相补默认值。

## 定运输入和不确定性

`period` 必须含 `basis`、非空白 `evidence`，并且三选一：

- `period_number`：已确认1–9运；不根据今天补造年代、周期或交节日期。
- `effective_event_year`：1800–2199，已确认交节后的有效事件年。不能把“2024某月不详”伪装成已确认的立春后年份。
- `event_at`：1801–2199，含时区的ISO时刻；`timezone_name` 默认 `Asia/Shanghai`。显示事件时刻所属的历史20年区间，区间不是宅盘到期日。

`basis` 为 `construction_completion`、`first_occupancy`、`confirmed_major_renovation` 或 `expert_confirmed`。专家确认要求显式 `period_number`。大修另须 `qualifies_for_period_reset=true`；这表示调用方已经确认条件，算法本身不鉴定重建资格。粉刷、搬家或当前年换运不会自动更新历史盘。

`period_context.timing` 记录历史区间首尾和事件年交节的实际 `provider`／`approximate`。`swisseph` 表示组件求解，不认证所用星历文件或秒精度；`linear_1900_fallback` 表示近似回退。若带时区时刻处于1864加20的整数倍这一跨运公历年，且该年立春求解回退，返回 `resolution_status=requires_confirmation`、`number=null`、两个 `candidate_period_numbers`、空宅盘及明确缺失项。调用方确认 `effective_event_year` 或 `period_number` 后可继续；非跨运年近似换年前后的宅运相同。

缺少宅向或定运资料返回 `partial` 和逐项 `missing_inputs`；仅有坐山卦不能推出确定的二十四山。角度要求磁北，真北输入须在调用前完成用户确认的转换；未知规则ID、越界数值、无时区时刻、冲突事件选择、未知字段均为校验错误。

`bearing_uncertainty_degrees` 是测量误差半径0–7.5°，默认0表示调用方确认精确角度。范围跨多个角区时计算所有候选，不只取两端；恰在边界也保留单侧极限候选。候选由山向和下／替模式去重；只有一个选择时 `chart` 有值、状态 `complete`，多个选择时 `chart=null`、状态 `partial`，候选盘不代表多栋住宅。

1.0.1改为闭角区与测量闭区间的直接相交判断，不扩张浮点容差。所有24山的±4.5°、±7.5°均验证分界及两侧最近可表示浮点数；区间端点碰线也保留双侧候选。给定 `house.sitting_trigram` 时，用已确认坐卦约束候选宫位，避免跨宫误差盘与八宅已确认坐卦冲突；同宫内两山或下／替模式的歧义仍保留。

例如子向354°是子兼壬，采用替卦；子向6°是同宫同阴阳的子兼癸，仍下卦。7.5°在子／癸山界，返回两种山向候选；355.5°在子兼壬的下／替分界，返回两种起法。4.5°双侧都仍下卦，可得到唯一选择。

## 输出分层与计算过程

`layers.xuankong_natal` 包含历史定运、住宅ID、测量依据与误差、24山表、唯一 `chart` 或多个 `candidates`。每盘都有独立 `period_chart`、`mountain_chart`、`facing_chart`，九宫 `palaces` 分别返回固定 `palace_number` 与三个星数；固定宫数不可当成运星。

`trace.mountain`、`trace.facing` 保留原入中星、借用的原星／宅运、同元龙山、阴阳、顺逆、最终入中星、是否发生数值替换与五黄政策。宫位飞行路径是 `C,NW,W,NE,S,N,SW,E,SE`；运盘始终顺飞，山向盘按各自原元龙阴阳顺逆。

聚合年星仅出现在 `layers.annual_stars.palaces.*.annual_star_number`。住宅星与年度星不加总，当前九运不覆盖历史八运，未提供观察形势不产生综合吉凶。快照“玄空宅盘”和“年度飞星”是两个章节，导出注册表也分别识别。

本阶段不包含其他门派替卦策略、玄空大卦、城门、七星打劫、自动立极／纳气定向、月日时盘或峦头裁决。完整运山向数字盘不等于完整住宅勘察断法。

## 独立验证与复现

[固定事实样本](../tests/fixtures/xuankong-reference.json) 保留逐宫数字与出处，生产引擎不生成公开盘例预期值：

- X2的3套下卦：七运午子、八运甲庚、七运卯酉；4套替卦：八运甲庚兼寅申、七运午子兼丙壬、七运乾巽兼戌辰、七运卯酉兼甲庚。七套全部九宫27个数字吻合，包含五黄不替与替后仍按原阴阳飞布。
- Apache-2.0 [YuanZHAO321/FengShuiCalculators固定提交](https://github.com/YuanZHAO321/FengShuiCalculators/blob/2eacd85b9878452469c6669e7fff05d2c6226c97/docs/js/flyingstars.js) 独立生成9运×24山＝216套下卦，保存提交ID和两个文件SHA-256。168套无五黄的盘全部一致；含向五黄的24套也一致；192套吻合、24套山五黄不同。参考实现向五黄直接借物理向山阴阳，未采用本版本的借宅运追踪；这些盘的向山与宅运本宫恰互为相对山，元龙和阴阳相同，所以数值吻合不能证明其借法表述一致。
- 独立抄录X1同元龙山和阴阳表，以X2五黄规则、X3所载二／六／七运阴阳模式交叉核对，再展开48项固定五黄顺逆数字断言（24山盘、24向盘）；这些是独立阴阳表的规则验证，不冒称48幅出版盘图。未调用生产阴阳表或飞布函数生成预期值。
- 外部山五黄分支直接用 `!facing.yang`，相对本版本借宅运同元龙阴阳发生取反。保持原外部结果；[离线回归](../tests/test_xuankong.py)核对固定夹具中的逐盘差异、元龙、借山、阴阳及逆向数列，不修改参考引擎强求216套一致，也不称其支持替星。

```bash
PATH="$PWD/.venv/bin:$PATH" .venv/bin/pytest -q tests/test_xuankong.py tests/test_fengshui_surfaces.py
```

另覆盖9运24山正向及左右兼向共648组合、立春前后／跨时区、定运来源、五运、磁北要求、精确山界与角度误差、缺失输入、聚合层不互相覆盖及REST／实际MCP协议／CLI一致性。规则计算一致与现实预测有效性是不同验证范围。

领域回归、跨传输合同、Linux golden 与真实模型咨询分别验证。可在对应环境运行 `scripts/audit_linux_golden.py`；环境不匹配时不得伪造平台或跳过差异来声称通过。规则计算一致不证明现实效果。

## 显式启用有限解释

在 `xuankong.interpretation`（聚合）或 `interpretation`（独立宅盘）传入独立评价运与证据，可启用 `xuankong_conditioned_v1@1.0.0`：有序山向星五行关系、当令星外部山水存在条件及床/门用途角色。默认不启用，既有宅盘数字和规则版本保持原合同。外局分宫独立确认，未确认、照片及边界候选保持缺失和候选状态；完整81组合断语与全宅勘察仍未覆盖。来源、字段与示例见[有限解释合同](fengshui-xuankong-interpretation.md)。
