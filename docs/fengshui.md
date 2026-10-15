# 家居风水基础计算

第一阶段提供六个基础工具：公共方位、个人命卦、八宅、金锁玉关基础砂水、年度紫白飞星和三法合参。三端来自同一目录，核心规则离线计算，不依赖外部风水服务。结果表示选定传统规则中的关系；规则来源、计算一致性和现实预测效力是不同事项。

## 入口与最小输入

| REST POST | MCP / CLI | 输入 | 输出层 |
| --- | --- | --- | --- |
| `/api/fengshui/directions` | `fengshui_directions` | 可选 `bearing_degrees` 和 `north_reference` | 固定八方、宫数；角度对应的八方与24山索引 |
| `/api/fengshui/minggua` | `fengshui_minggua` | 公历 `birth_date`、`effective_birth_year` 或含时区的 `birth_at` 三选一；`gender_convention` | 命卦、原始数、寄宫、东西组、个人八方关系 |
| `/api/fengshui/bazhai` | `fengshui_bazhai` | `house`、`occupants`；可选 `placements` | 坐山宅盘、逐人命盘、位置与朝向的用途判断 |
| `/api/fengshui/jinsuo` | `fengshui_jinsuo` | `features` | 八宫砂水偏好、逐个观察判定 |
| `/api/fengshui/annual_stars` | `fengshui_annual_stars` | `effective_year` 或含时区的 `query_at` | 当年入中星、九宫年星、立春有效期、当前元运 |
| `/api/fengshui/assess` | `fengshui_assess` | 上述住宅、住户、环境和年度输入；可选 `methods` | `bazhai` / `jinsuo` / `annual_stars` 独立分层与差异清单 |

完整约束见 `/openapi.json`、MCP `tools/list` 和 `fatebridge describe fengshui_assess`。新 family 是 `fengshui`；不加入个人 `analyze_destiny` 或 `profile` 默认系统。

第二阶段增加 `fengshui_xuankong_natal`，实现中州派完整运／山／向盘与兼向替星；聚合时显式选择 `xuankong_natal`，与年度飞星独立。定运资料、分界候选、规则版本及独立盘例见 [玄空宅盘](fengshui-xuankong.md)。

## 三端例子

将以下内容保存为 `home.json`。仓库另提供可直接运行的 [示例文件](examples/fengshui-home.json)。

```json
{
  "house": {
    "object_id": "home",
    "facing_degrees": 180,
    "north_reference": "magnetic",
    "orientation_basis": "measured"
  },
  "occupants": [
    {"subject_id": "a", "effective_birth_year": 1990, "gender_convention": "male"},
    {"subject_id": "b", "effective_birth_year": 1990, "gender_convention": "female"}
  ],
  "features": [
    {
      "object_id": "pond",
      "direction": "S",
      "classification": "water",
      "classification_basis": "user_confirmed",
      "evidence": "已确认南方为水体"
    }
  ],
  "effective_year": 2026
}
```

```bash
# REST：API Key 鉴权按服务配置额外提供请求头。
curl -X POST http://localhost:8010/api/fengshui/assess \
  -H 'Content-Type: application/json' --data-binary @home.json

# CLI：完整 JSON 请求，适用于住宅、住户和环境嵌套对象。
fatebridge fengshui_assess --request-file home.json --compact

# 简单工具也支持普通参数。
fatebridge fengshui_minggua --effective-birth-year 1990 --gender-convention female
fatebridge fengshui_annual_stars --query-at '2026-02-04T04:03:00+08:00'

# 复杂字段可用 JSON 参数；显式字段覆盖请求文件同名顶层字段。
fatebridge fengshui_assess --request-file home.json \
  --methods '["annual_stars"]' --effective-year 2027
```

```python
import asyncio
import json
from pathlib import Path
from fastmcp import Client

async def main():
    async with Client({"mcpServers": {"fatebridge": {
        "command": "fatebridge-mcp", "args": []
    }}}) as client:
        inputs = json.loads(Path("home.json").read_text())
        result = await client.call_tool("fengshui_assess", inputs, raise_on_error=False)
        print(result.is_error, result.structured_content)

asyncio.run(main())
```

`--request-file` 当前由七个风水工具明确启用，接受 JSON 对象，未知字段照常报错；不是只挑出生字段的 `--subject-file`。合并优先级为模型默认值 < subject 档案 < request 文件 < 显式字段参数。嵌套字段整体替换，不做递归混合。请求文件解析失败退出2，模型校验失败退出1，合法 `partial` 退出0。

## 规则与版本

规则数据位于 `src/fatebridge/data/fengshui/rules-v1.json`，随 wheel 打包。四个规则集当前均为 `1.0.0`，每个输出层含 `ruleset_id`、`version`、`bundle_version`、来源标题／URL／类别／适用范围与约定。逐项关系带 `rule_id` 和 `source_ids`，不能只在最终文本附一条笼统来源。

| 规则集 | 精确范围 | 来源与约定 |
| --- | --- | --- |
| `houtian_directions_v1` | 后天八卦、固定宫数、八方角区、24山索引 | 《沈氏玄空学》转录；0°北、顺时针；左闭右开 |
| `bazhai_sitting_v1` | 坐山起伏位；1864命卦锚点；8×8大游年；明确用途约定 | 《八宅明镜》上下卷转录、书目及现代三元纪元；默认命卦立春换年，可明确选 `january_1` |
| `jinsuo_basic_fixed_v1` | 一二三四砂、六七八九水；逐个确认观察 | 署名陈益峰《九砂九水》注解所引传本；转载及底本归属限制明确登记 |
| `annual_zibai_lichun_v1` | 年度紫白入中、顺飞九宫、立春区间、当前20年元运 | 《沈氏玄空学》转录、Joey Yap 2026年盘、作者立春约定与香港天文台年历 |

详见 [调研与原典范围](fengshui-research-2026-10-12.md)。未知规则 ID 拒绝；改变纪元、换年、坐山起法或砂水规则时，应新增规则版本与独立样本，不能静默替换原版本。`january_1` 是命卦中显式可选的现代计算约定，不宣称所有《八宅明镜》古本都按立春换年。

定义 `wrap9(n) = (n - 1) % 9 + 1`，有效年为 Y：

- 男命原始宫数 `wrap9(1 - (Y - 1864))`；女命 `wrap9(5 + (Y - 1864))`。原始五数在计算完成后分别寄坤二、艮八，输出保留原始数与替换信息。
- 两卦三爻从初爻开始编码为 bit0/1/2；异或0至7分别对应伏位、祸害、绝命、天医、生气、六煞、五鬼、延年。
- 年星入中 `wrap9(1 - (Y - 1864))`；路径 `C,NW,W,NE,S,N,SW,E,SE` 逐宫递增。年际入中递减与同年顺飞不同。

## 输入语义和边界

工位/家居可传 `scene=workstation|home`；未显式传方法时按已有事实选层，独立形态/桌面不再自动引入无关三法。家具动作许可与独立候选方案分别用 `layout_constraints` / `layout_alternatives`，详见[场景选法与候选布局合同](fengshui-scene-planning.md)。候选重算现有规则、不继承旧形态、不平均评分；完整古典形势、独立阳宅三要结构、三合/大卦及完整玄空组合解释仍明确未覆盖。

角度范围0–360，360归零；八方中心间隔45°，半宽22.5°；24山中心间隔15°，半宽7.5°。正好22.5°归东北／丑山。宅向推导坐山时加180°；同时提供 `sitting_trigram` 必须一致。基础方位／八宅角度必须声明 `north_reference=magnetic|true`（玄空当前版本要求 magnetic），不自动校正磁偏角。只有已确认宅卦时可直接提供 `sitting_trigram`。

`house.division_method` 只接受 `confirmed_angular_sectors`。八方角区、九等分网格和示意九宫图不是同一个几何计算；第一阶段不识别户型图片、不自动定中心、也不推断不规则户型分宫。

时间输入必须含 UTC 偏移或Z，`timezone_name` 默认为 `Asia/Shanghai`，可用 IANA 名称或偏移。每个出生／查询时刻与对应有效年字段二选一。显式有效生年表示调用方已确认换年，无需出生小时或真太阳时。未知 `gender_convention` 应省略或传 null，返回男女候选并标记 `partial`，不会默认男性。支持有效年1800–2199、带时区输入1801–2199；区间结束可延伸下一年。

命卦另接受公历 `birth_date`，与有效生年、出生时刻三选一。按所选时区计算立春所在日期；之前取上一有效生年，之后取本年，立春当日保留 `partial` 并要求出生时刻。选择 `january_1` 时日期即可确定生年。该路径不构造虚假的出生小时，也不使用真太阳时。

年盘有效期是 `[立春, 下次立春)`，不硬编码2月4日午夜，也不按春节。节气沿用现有 `almanac`：优先 Swiss，可能回退线性近似；输出 `timing` 说明供应函数、Swiss可用性、可能回退及独立核验范围。本次外部证据确认2026立春日期和分钟，不认证现有引擎的秒级精度。

布局对象分别提供 `location_direction` 与可选 `facing_direction`。后者必须配套用途语义：门 `door_facing`、床头 `headboard`、书桌 `desk_facing`、灶 `fire_mouth`。灶座按凶方约定、已确认火门按吉方约定；现代燃气旋钮不是自动等同古火门。床头与书桌朝向是本版本明确的应用约定。住宅宅盘与每位住户命盘分别输出；`subject_id` 只筛选一位布局关联住户，`subject_ids` 选择明确的多人使用集合，两者互斥；不传二者则保留应用全部已提供住户的语义，均不修改宅卦。多人列表非空、成员唯一且必须引用已提供住户。对象实际使用者与全宅住户分开，不能把同住自动当共用。未知住户引用、重复住户／布局 ID 被拒绝。

位置和朝向至少提供一项。只知道朝向时仍计算该朝向的宅／人关系，位置缺失明确返回 `partial`；朝向不会填进位置，也不会用来推测住宅坐向。

## 布局对象的通用计算

在现有 `fengshui_assess` 请求中设置 `analyze_layout=true`，输出 `layout_analysis`；不增加工位或其他场景专用接口。它对门、床、桌、灶复用同一套盘和用途规则：

- `placement_findings`：对象的位置分别关联年星和玄空宅盘；玄空候选盘、运／山／向三角色保留。八宅位置和朝向分别返回。
- `adjustment_options`：从当前判定使用的同一规则反算匹配方位。按宅及各住户分列，只有已确认作用域参与交集；没有共同匹配方向时保留差异，不择一覆盖。灶座与火门采用相反的用途偏好。
- `environment_adjustments`：已确认砂水特征的保留／调整分类；未知分类不生成目标分类。水壶、镜子或小摆件不能自动替代已确认环境砂水。
- `element_relationships`：分别计算每个已关联星五行的生、同、泄、克与被克关系。复用共享五行图；例如火由木生、泄到土、被水克。星五行不是住户喜用神，这些关系不证明具体物件、颜色或材质有化煞效果。
- `layout_analysis.status`：本次布局关联计算的完成状态；独立于顶层原始盘 `status`。年盘已算完而对象位置未知时，原始盘可以 `complete`，布局关联保持 `partial`。
- `layout_analysis.analysis_progress` 与 `coverage.analysis_progress`：保留原 status，另分计算完整性、所选规则审查及候选动作可执行性。已确认没有独立规则的物件可结束审查；属性 unknown 或照片候选仍需事实确认。可选新增不变成必做任务，blocked 不再追其执行条件，方向关系未验证搬转可行性时不返回 ready。计数单位与 pending_confirmations 的用途随结果明确，不能把输出确认路径当请求参数。

同一请求包含多件家具时，可分别关联实际使用人。例如住户甲、乙共用床，丙只用书桌，床可传 `subject_ids=["a", "b"]`，桌传 `subject_id="c"`。床的逐人判定和共同匹配方向仅由甲乙派生；加入丙的资料不会改变这张床的结果。住宅宅盘若已提供，仍单独参与该对象判断，不因使用人筛选而消失。更正使用者时替换集合后重新计算，不沿用旧共同方向。

示例：只知道某人的桌朝西，尚不知道房屋坐向及桌子所在宫位：

```json
{
  "methods": ["bazhai"],
  "analyze_layout": true,
  "occupants": [{"subject_id": "a", "birth_date": "2000-12-10", "gender_convention": "male"}],
  "placements": [{"object_id": "table", "purpose": "desk", "subject_id": "a", "facing_direction": "W", "facing_role": "desk_facing"}]
}
```

该请求直接给出离命西向五鬼及个人匹配方向 N/E/SE/S，保留宅向和位置缺失，不强制补出生分钟。若加入年盘或宅盘，必须补对象的位置才能关联相应落宫；面朝西不能证明对象位于西宫。

室内入口视野、入口直线与实体背靠另按明确作者版本计算；有条件的元素代表物和2026年度候选规则见下节。完整峦头、距离吉凶阈值、搬动几何可行性和具体物件效果大小仍列在 `unsupported_queries`，不会以生活常识或虚构阈值填补。

## 室内形态与有条件物件规则

同一 `fengshui_assess` 接受三个可选输入，提供这些输入即启用布局计算，不必另外开启新工具：

| 输入 | 输出 | 限定范围 |
| --- | --- | --- |
| `form_observations` | `layout_analysis.form_analysis` | 现代作者室内控制位置：入口可见、避开入口直线；床/桌加实体背靠。独立分析可 `methods=[]`，无需生辰或宅向 |
| `element_adjustments` | `layout_analysis.element_remedies` | 绑定已计算对象、方法与明确生/泄目标，再按 AFSI 作者版本给代表物/颜色；不由命卦推断喜用神 |
| `annual_remedy_ruleset_id=pang_2026_annual_v1` | `layout_analysis.annual_remedies` | 显式选取作者2026年盘南5/西北2的金元素候选及避火；只按对象所在宫位，不按朝向或其他年份 |

形态的 `observation_basis` 为 `measured`、`user_confirmed` 或 `image_observed`。照片仅为候选，不能提供米数；实际距离须测量/用户确认。未知视野、直线和背靠省略，不转成 false。右后门仅说明在使用者后半空间，不能证明直线冲，也不能投影成住宅某宫。1.5米等距离只记录，来源没有统一吉凶阈值。镜面只作为确认能补入口视野的条件选项，不作为通用化煞物。

元素目标的 `target_method` 必须已选中，且 `object_id` 必须引用已提供布局对象。八宅还须指定 `subject_id`、`aspect`；玄空须指定运/山/向 `star_role`。候选命卦/候选宅盘只给候选方案，不能输出确认处方。灶座的凶方特殊用途不能套用普通凶星削弱。本版本优先列实际元素代表物，再列色彩替代，不要求购买、数量、重量或效果概率。

方案同时返回 `cross_scope_effects`，显示加入的元素对同一对象其他已算层的生/泄/克关系；这些关系不合成一个“全宅有利”结论。`supplemental_rulesets` 和顶层 `rulesets`/`rule_trace` 保留作者、版本、原文位置和检索 SHA-256；`supplement_statuses` 区分未请求、完成、部分及年份不支持。不同作者对物件路线的分歧在 `method_disagreements` 明示。

可运行示例见 [形态输入](examples/fengshui-forms.json)、[元素目标](examples/fengshui-elements.json) 和 [年度作者候选](examples/fengshui-annual-remedy.json)。来源核对、采用与排除的规则见 [2026-10-14规则证据](fengshui-layout-rules-2026-10-14.md)。

环境特征要求方位、`classification=sand|water|mixed|unknown`、`classification_basis=measured|user_confirmed` 与非空 `evidence`。标签不参与分类；道路、镜子、高楼、缺水都不能自动推导砂水。`mixed`／`unknown` 返回 `undetermined` 和缺失项，不给吉凶。

## 分层结果与覆盖状态

实际结果的主字段：

```text
status: complete | partial
layers.bazhai: house.sectors / occupants[].candidates[].sectors / placement_findings
layers.jinsuo: preferences / feature_findings
layers.annual_stars: palaces / effective_year / time_context / current_period
rulesets / rule_trace: 各层规则版本、来源及范围
coverage: implemented_layers / missing_inputs / unavailable_layers / not_requested_layers
conflicts: 逐人方向差异、宅与人作用域差异、三层叠加清单
snapshot_text / snapshot_export: 同一组计算事实的分层可读快照
run_metadata: 三端通用运行元数据
```

示例中，坎宅南方为延年，金锁玉关南方基础偏水，2026南宫年星为五黄；三项条件分别返回，`distinct_scope_overlay` 表示不同作用域并置，不表示已经证明三法矛盾。1990男女两位住户的北方分别为伏位与五鬼，产生 `personal_direction_difference`，不会自动以户主或男性覆盖另一人。未知男女候选不能被当成两个真实住户制造冲突。

`complete` 仅表示请求的基础层已有所需输入，不代表全流派、完整环境勘测或进阶宅盘完成。八宅缺住户时宅盘仍可计算，但个人层缺失使状态为 `partial`；金锁玉关只覆盖提供的特征，不保证全宅环境已勘测。空请求返回各层缺失项，HTTP200／MCP成功／CLI退出0。非法输入返回校验错误，HTTP422／MCP `isError=true`／CLI退出1。`methods` 可以只选择需要的层，未请求的层不计算。

八宅游年星与年度紫白星有不同名称空间，例如八宅生气贪狼属木、一白贪狼属水。`palace_number` 始终是固定宫数，`annual_star_number` 才是当年临宫星数；`current_period` 是当前日历元运，不是住宅建造元运。

本版明确未实现：月飞星、金锁24山及形态／距离／元运组合、自动户型几何。24山角度索引可用不表示这些24山论断可用。没有三法总分，也不生成疾病、死亡或财富断语。

可用通用 `fields` 投影及快照开关降低体积：

```bash
fatebridge fengshui_assess --request-file home.json \
  --fields layers.annual_stars.palaces.S coverage --no-include-snapshot-text --compact
```

快照包含实际方向、命卦、砂水观察、年星、差异和来源。风水请求不接受 `selected_sections`；`snapshot_export` 记录本次实际生成的分层 section，进一步裁剪用 `fields`。

## 验证与维护

```bash
pytest -q tests/test_fengshui.py tests/test_fengshui_surfaces.py
# 可选联网比对，不是生产运行依赖；下载后先校验固定 SHA-256。
python scripts/audit_fengshui_independent.py
```

离线测试用固定提交／SHA-256登记的参考事实核对1900–2099男女命卦400项、独立八宅字典64项，并测试纪元／世纪／五数寄宫、立春前后与时区等价、方位边界、坐向反转、门床灶用途、不同住户、未知／混合砂水、来源版本、三端真实调用／校验／投影／请求文件。2026九宫另用作者出版年盘核对。代表性输入加入现有全端与 golden 覆盖，新增快照不重写旧工具数值基线。

外部参考 [JackieL233/fengshui-master 固定提交](https://github.com/JackieL233/fengshui-master/blob/2666304c5cb4ac13091c8c1fcdd4e40c218b275a/fengshui-master/scripts/minggua.py) 仅核对有效生年和八宅关系，不覆盖精确出生时间、年飞星、金锁玉关或完整玄空。本次未取得金锁玉关独立引擎；其验收依据为明确登记的八宫传本规则与输入语义检查。

2026-10-12 本地验收：全仓1024项通过、88项按既有配置跳过，Black／isort／mypy／diff检查通过；wheel含规则JSON，并在仓库外从解包产物验证服务、目录及CLI。记录见 [验收证据](audits/2026-10-12/fengshui/implementation-validation.json) 和 [六工具公开合同](audits/2026-10-12/fengshui/implementation-contracts.json)。本地 macOS／Python3.13 的通过不代替 Linux／Python3.12 golden 字节基线或发布部署验收；新增六份风水快照，现有导出注册表基线只更新风水章节元数据。
