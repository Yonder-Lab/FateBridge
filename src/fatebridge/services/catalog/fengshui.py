"""Fengshui tool declarations and domain binding helpers."""

from __future__ import annotations

from typing import List

from fatebridge.application.bindings import lazy_service, raw_invoke
from fatebridge.application.tool_spec import ToolSpec
from fatebridge.core.fengshui.models import (
    AnnualRequest,
    AssessRequest,
    BazhaiRequest,
    DirectionsRequest,
    JinsuoRequest,
    MingguaRequest,
    XuankongRequest,
)
from fatebridge.core.fengshui.output import FengshuiOutput

SPECS: List[ToolSpec] = []

for _name, _service, _model, _summary in (
    (
        "directions",
        "calculate_directions",
        DirectionsRequest,
        "后天八卦固定方位、宫数与角区索引",
    ),
    (
        "minggua",
        "calculate_minggua",
        MingguaRequest,
        "住户命卦及个人八方关系（独立于宅卦）：支持公历 birth_date，非立春当日不需要出生小时；布局问题优先 fengshui_assess 的 analyze_layout。",
    ),
    (
        "bazhai",
        "calculate_bazhai",
        BazhaiRequest,
        "八宅坐山宅盘、逐人命盘与用途判定；不是完整阳宅三要门主灶结构法",
    ),
    (
        "jinsuo",
        "calculate_jinsuo",
        JinsuoRequest,
        "金锁玉关八宫基础砂水偏好（已确认分类）",
    ),
    (
        "annual_stars",
        "calculate_annual_stars",
        AnnualRequest,
        "立春换年的年度九宫紫白飞星（非山向宅盘）",
    ),
    (
        "xuankong_natal",
        "calculate_xuankong_natal",
        XuankongRequest,
        "中州派玄空运山向宅盘、历史定运、兼向替星与边界候选（独立于年星）；interpretation 显式启用 xuankong_conditioned_v1 有限解释，current_period_number/period_evidence 成对，外局分宫独立确认山形/水形，不复用金锁或室内靠背。",
    ),
    (
        "assess",
        "assess",
        AssessRequest,
        "工位/合租/家居布局主入口。普通解释先给已有依据和条件式建议，不等待全部complete或动作ready；读取analysis_progress.interpretation_status及follow_up：conclusion_candidates只择影响当前结论的缺项，execution_only只约束动作落实。照片保留候选但可按条件解释；未实现或无规则直接说明，不反复补资料。scene=workstation|shared_rental|home 时未传 methods 则按已有事实选层，显式 methods 优先；局部审查以九宫飞星第一、金锁第二、八宅独立命卦关系展开，不用年盘替代历史宅盘，不把个人或周围人的八字/紫微喜忌混入客观环境。environmental_context 独立保存方向/户型偏移/中心确认、家庭辈分与随配偶排行、多身份/生肖主次、楼层/院落与环境事实，无需为人物对应收集生辰。显式未确认方向时不能提交实际落宫；无方向保留独立形态与未覆盖事实。院落归第一层，局限本层与共同影响分开，异层适宜及实际使用范围须明确确认；subject_ids仅正向，负向排除需usage_confirmed/usage_evidence且覆盖对象显式使用人。household_scope=symbolic_reference只给卦名/对宫、不追罗盘，家庭索引仅飞星/金锁适用、非八宅命卦。拱门/开放厨房低优先提醒。有来源的12类厨卫/床灶/镜面/梁管/尖角关系用environmental_context.interior_relations，明确源/目标ID、kind、必传可null的present及独立basis/evidence；objects.role明确功能，不由label猜；床边柱角仅pillar_corner。照片true/false均候选，确认false仅本条不触发。仅相关输入时fields追加layout_analysis.interior_analysis。材质器形用material_facts，material/shape/colour独立证据；element_use仅代表物用途资格，AFSI材料/颜色与FSI器形参考分开，不推个人喜用或所需元素。仅相关输入时fields追加layout_analysis.material_analysis。旧单对象观察不自动升级为明确关系，未注册禁忌不编断语。有scene或environmental_context时fields追加method_policy；只有提供environmental_context时才追加layout_analysis.environmental_context，不向strict_fields请求不存在的分支；三法五行/物象/职业家具与砂水参考按需追加 method_details，参考不等于处方。纯方法参考可用scene=home作通用查询标签、analyze_layout=false并按问题显式methods，按需投影method_details；年度仅加有效年/确认时刻。没有实际环境事实则省略environmental_context，不造空上下文、房屋或摆位；household_scope=symbolic_reference仅实际家庭资料的象意范围，不等于通用reference_only。method_policy.priority_review_status/missing与已选计算完成分开；available_engine_layers仅现状，候选读priority_review_by_scope.candidates及available_candidate_engine_layers。独立形态/桌面未传 methods 默认不引入无关罗盘层，旧无场景请求保留三法默认。layout_constraints 记录门床桌灶及明确环境物件 can_relocate/can_rotate/can_add_items 的明确许可；禁止动作返回 blocked 且不再追问。layout_alternatives 接收用户实际提出的候选，changes 明确搬位/转向，placement/form_observation 为新位置独立观察；镜等可仅给与目标相关的双对象关系environmental_context；原关系任一端移动都重核，静态端已知楼层保留，空间归属改变必须声明location，不能借搬转改写已确认材质/器形/颜色/存活状态或代表物用途，physically_feasible 与许可分开；同对象金锁特征用候选features在新位置独立确认并重算，方向与新placement一致，缺新特征不ready，其他固定环境保留原楼层坐标，候选不得改写非目标固定对象参考系；fields 追加 layout_analysis.alternatives_analysis，ready仅表示所选门槛满足，逐规则比较不选综合赢家；layer_statuses列候选真实计算，飞星comparison_scope仅原始盘参考。xuankong.interpretation 可显式启用有限山向星五行关系、当令外局及床/门取用；current_period_number/period_evidence 成对，external_forms 以全宅中心分宫确认山形/水形，不沿用金锁分类或室内靠背，不由照片确认事实；fields 追加 layout_analysis.natal_interpretation。coverage.scene_scope 明示完整峦头、阳宅三要结构、三合水法及完整玄空81组合断法未覆盖。通用家居风水与布局合参：门/床/书桌/灶的位置/朝向放 placements，设 analyze_layout=true；关联使用人一人用 subject_id、多人用 subject_ids，二者互斥；未指定关联则应用全部已提供住户，不将同住推成共用。床/书桌/灶的形态关系放 form_observations，实际入口与经过通道分别记录，窗在侧边仅按所选作者规则判断；其他家具不映射为这些用途。独立形态可 methods=[]，无需生辰/宅向。桌面物件可用 surface_layouts 显式选择 desktop_bagua_btb_v1，确认矩形边界、坐者近沿与事业/丰盛目标；surface_constraints 单独保存动作许可与可行区。远左植物/鲜花及近中水景/深色用品为现代BTB作者候选，不能当八宅或年盘；手机、瓶杯、玩偶不按名称推断五行或固定吉侧。请求桌面时 fields 追加 layout_analysis.surface_analysis 和 rulesets；做八宅个人匹配时可追加 layers.bazhai.occupants 说明所用命卦。element_adjustments 须绑定已计算对象、方法、作用域和调节目标；物件/颜色取所选作者的有条件候选，不推喜用神。年度候选须显式 annual_remedy_ruleset_id=pang_2026_annual_v1，仅2026南5/西北2，不外推。距离无通用吉凶阈值，照片只作待确认观察；每项行动依据事实、规则与约束，blocked/candidate_only 不表述为可立即执行；各层及作者分歧分列。工位活动/隔挡显式用environmental_context.workstation_review，activities选workstation_activity_authored_v1，entry_barriers选afsi_entry_barrier_v1；fields追加layout_analysis.workstation_analysis。material_facts.application选afsi_application_conditions_v1核运行/尺度等条件，target_request_id仅绑定本轮已算元素目标。WOFS非BTB桌面仍reference_only，不启用固定摆位。",
    ),
):
    SPECS.append(
        ToolSpec(
            key=f"fengshui_{_name}",
            bind=raw_invoke(lazy_service("fatebridge.services.fengshui", _service)),
            request_model=_model,
            summary=_summary,
            operation_label_zh=_summary,
            family="fengshui",
            rest_path=f"/api/fengshui/{_name}",
            mcp_name=f"fengshui_{_name}",
            output_model=FengshuiOutput,
            cli_request_file=True,
        )
    )
