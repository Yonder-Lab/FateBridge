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
        "工位/家居布局主入口。scene=workstation|home 时未传 methods 则按已有事实选层，显式 methods 优先；独立形态/桌面未传 methods 默认不引入无关罗盘层，旧无场景请求保留三法默认。layout_constraints 记录门床桌灶 can_relocate/can_rotate/can_add_items 的明确许可；禁止动作返回 blocked 且不再追问。layout_alternatives 接收用户实际提出的候选，changes 明确搬位/转向，placement/form_observation 为新位置独立观察，physically_feasible 与许可分开；fields 追加 layout_analysis.alternatives_analysis，ready仅表示所选门槛满足，逐规则比较不选综合赢家。xuankong.interpretation 可显式启用有限山向星五行关系、当令外局及床/门取用；current_period_number/period_evidence 成对，external_forms 以全宅中心分宫确认山形/水形，不沿用金锁分类或室内靠背，不由照片确认事实；fields 追加 layout_analysis.natal_interpretation。coverage.scene_scope 明示完整峦头、阳宅三要结构、三合水法及完整玄空81组合断法未覆盖。通用家居风水与布局合参：门/床/书桌/灶的位置/朝向放 placements，设 analyze_layout=true；关联使用人一人用 subject_id、多人用 subject_ids，二者互斥；未指定关联则应用全部已提供住户，不将同住推成共用。床/书桌/灶的形态关系放 form_observations，实际入口与经过通道分别记录，窗在侧边仅按所选作者规则判断；其他家具不映射为这些用途。独立形态可 methods=[]，无需生辰/宅向。桌面物件可用 surface_layouts 显式选择 desktop_bagua_btb_v1，确认矩形边界、坐者近沿与事业/丰盛目标；surface_constraints 单独保存动作许可与可行区。远左植物/鲜花及近中水景/深色用品为现代BTB作者候选，不能当八宅或年盘；手机、瓶杯、玩偶不按名称推断五行或固定吉侧。请求桌面时 fields 追加 layout_analysis.surface_analysis 和 rulesets；做八宅个人匹配时可追加 layers.bazhai.occupants 说明所用命卦。element_adjustments 须绑定已计算对象、方法、作用域和调节目标；物件/颜色取所选作者的有条件候选，不推喜用神。年度候选须显式 annual_remedy_ruleset_id=pang_2026_annual_v1，仅2026南5/西北2，不外推。距离无通用吉凶阈值，照片只作待确认观察；每项行动依据事实、规则与约束，blocked/candidate_only 不表述为可立即执行；各层及作者分歧分列。",
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
