# 桌面作者规则与咨询闭环

扩展复用fengshui_assess，不增加工位专用工具，不按生日、方向或某张照片选择规则，REST/MCP/CLI共用输入输出。

## 来源与方法

desktop_bagua_btb_v1@1.0.0是现代BTB作者方法，与八宅、年度紫白及玄空宅盘独立。须显式选版本，矩形桌面均分三行三列，坐者使用的桌沿为近侧；远左不等于东南，不能触发年星或改变个人朝向判断。

- [Anjie Cho的八卦地图](https://www.anjiecho.com/holistic-spaces-blog/2014/4/28/feng-shui-101-the-bagua-map)明确桌面分区与远左丰盛区。
- [Anjie Cho的事业文章](https://www.anjiecho.com/holistic-spaces-blog/attract-abundance-in-your-career-with-feng-shui)明确远左盆栽/鲜花枝候选及使用者侧窗条件。
- [Tori McBrien的事业文章](https://www.ifsguild.org/nine-tips-to-support-your-career/)明确坐者桌沿定位、近中事业区及深色/水景象征；实现选不新增实际水装置的图案或用品。

原始页面获取时间、SHA-256和字节数记录在src/fatebridge/data/fengshui/desktop-bagua-v1.json。只采用分区、目标、代表物和条件，不采纳健康、财富或事业结果承诺。

[WOFS的办公室作者指引](https://www.wofs.com/7-quick-tips-career-success/)支持书桌避开已确认直走道、裸露横梁正下方和朝向使用者的家具尖角。版本记录于layout-supplements-v1.json的F4；这三项是可选观察，未提供时不推断，不把灯带当横梁或屏幕框当实体尖角，不外推到床/灶。其有线电话接线方向、硬性左右高低、物件数量和健康/财富断语未采用。

AFSI《The Principles of Feng Shui》本次重新获取的PDF散列与原记录相同：6ab5135060df281fd6a6e376e0516e660c185dd2af2f146a5f850df64cc3b024。印刷页104/PDF页121反对机械套用左右青龙白虎决定建筑入口，不能据此推出桌面手机必须左、右屏必须低。保留分歧，不将搜索结果中的左右规则合为共识。

## 合同

surface_layouts保存边界、近沿、用户目标与物件。representation须有依据，支持活植物、鲜花、水景图、深色用品；手机、饮料瓶、玩偶不按名称自动归为火、水、土。未知用unknown/other，照片用image_observed。

surface_constraints单独保存移动/新增许可、固定物件、不可用区域与用户确认的可行区域。许可不证明现状；feasible_zones表示能容纳对象、保持入口视野和必要操作空间，不表示风水效力。

layout_analysis.surface_analysis逐件说明覆盖；每个动作返回rule/source、传统理由、起点/终点、条件和约束。ready指已确认物件/边界、许可与区域可行，执行仍须维护条件；conditional_option先核对许可或可行性；candidate_only先确认照片事实；blocked不能改成无来源次吉位置。no_independent_placement_rule表示没有此物件独立处方，不等于已算为吉。

未覆盖物件列入uncovered_item_ids并保留partial。只有请求桌面才出现新分支，不改变原非桌面业务输出。独立桌面可methods=[]，无需生日/宅向或占位placement；同ID的placement必须是desk，约束须正确关联，重复和未知引用拒绝。

物件属性的observation_basis与位置的zone_observation_basis各自保存；zone与位置依据成对。确认活植物不等于确认其九格位置，照片位置不能作为确定的retain依据。近沿near是靠身体，远沿far是离身体；near_right对应右前、far_left对应左后，完整legend进入MCP描述、input资源与两咨询入口生成合同。

## 咨询闭环

先列请求层次与实际覆盖，再采集会改变行动的事实。实际房间入口与经过通道分开确认；passage_position不触发入口规则。明确window_position时才判断侧窗，不当砂水或宅向。个人匹配说明命卦/八字方法，另算八字不能自动推导物件位置。

部分资料可先算，但继续跟踪未解决项目。不可搬转时筛允许的有据动作，每项建议连接事实、rule/source、作用域、目标位置与条件；没有处方的物件可保留，不能编吉侧或把整理建议算作风水任务完成。深入逐物件请求不受首轮字数限制。

桌面请求在fields追加layout_analysis.surface_analysis、rulesets；八宅个人匹配可追加layers.bazhai.occupants。未变解释不重算，更正事实替换旧值并沿用trace/parent。

## 验收

期待值先从来源独立规定；回归变换目标、九个起始区域、生日/朝向、ID/标签、未知/照片、固定物件和禁止动作。生产代码和测试不包含用户生日/照片或预设用户回答。允许blocked和无规则结果，不按建议数量、关键词或必须摆成某位置奖励。

用户案例用于现场回放，不能替代跨变体回归。真实模型体验、结构化调用、三端一致、Linux golden各自报告；规则来源和软件一致性不证明传统效力。
