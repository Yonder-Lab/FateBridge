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
    ("bazhai", "calculate_bazhai", BazhaiRequest, "八宅宅盘、逐人命盘与用途判定"),
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
        "中州派玄空运山向宅盘、历史定运、兼向替星与边界候选（独立于年星）",
    ),
    (
        "assess",
        "assess",
        AssessRequest,
        "通用家居风水与布局合参：门/床/书桌/灶的位置/朝向放 placements，设 analyze_layout=true；床/书桌/灶的形态关系放 form_observations（入口可见、直线、实体背靠分别确认），其他家具不映射为这些用途。独立形态可 methods=[]，无需生辰/宅向。element_adjustments 须绑定已计算对象、方法、作用域和调节目标；物件/颜色取所选作者的有条件候选，不推喜用神。年度候选须显式 annual_remedy_ruleset_id=pang_2026_annual_v1，仅2026南5/西北2，不外推。距离无通用吉凶阈值，照片只作待确认观察；各层及作者分歧分列。",
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
