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
        "住户命卦及个人八方关系（独立于宅卦）",
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
        "家居分层合参、可选玄空宅盘、逐人差异、缺失输入与规则来源",
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
