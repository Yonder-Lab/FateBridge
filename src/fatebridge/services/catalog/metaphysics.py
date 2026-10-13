"""Metaphysics tool declarations and domain binding helpers."""

from __future__ import annotations

from typing import List

from fatebridge.application.bindings import lazy_service, person_invoke, raw_invoke
from fatebridge.application.tool_spec import ToolSpec
from fatebridge.core.requests.metaphysics import (
    JinkouAnalysisRequest,
    LiuRengGodsRequest,
    LiuRengRunyearRequest,
    QimenAnalysisRequest,
    TaiyiAnalysisRequest,
    ZiweiBirthRequest,
    ZiweiHoroscopeRequest,
    ZiweiRulesRequest,
)

calculate_jinkou_analysis = lazy_service(
    "fatebridge.services.metaphysics", "calculate_jinkou_analysis"
)


calculate_liureng_gods = lazy_service(
    "fatebridge.services.metaphysics", "calculate_liureng_gods"
)


calculate_liureng_runyear = lazy_service(
    "fatebridge.services.metaphysics", "calculate_liureng_runyear"
)


calculate_qimen_analysis = lazy_service(
    "fatebridge.services.metaphysics", "calculate_qimen_analysis"
)


calculate_taiyi_analysis = lazy_service(
    "fatebridge.services.metaphysics", "calculate_taiyi_analysis"
)


calculate_ziwei_birth = lazy_service(
    "fatebridge.services.metaphysics", "calculate_ziwei_birth"
)


calculate_ziwei_horoscope = lazy_service(
    "fatebridge.services.metaphysics", "calculate_ziwei_horoscope"
)


calculate_ziwei_rules = lazy_service(
    "fatebridge.services.metaphysics", "calculate_ziwei_rules"
)

SPECS: List[ToolSpec] = [
    # --- Metaphysics -------------------------------------------------------
    ToolSpec(
        key="ziwei_birth",
        bind=person_invoke(calculate_ziwei_birth),
        request_model=ZiweiBirthRequest,
        summary="紫微斗数命盘。",
        operation_label_zh="紫微命盘",
        family="metaphysics",
        rest_path="/api/cn/ziwei/birth",
        mcp_name="ziwei_birth",
    ),
    ToolSpec(
        key="ziwei_horoscope",
        bind=person_invoke(calculate_ziwei_horoscope),
        request_model=ZiweiHoroscopeRequest,
        summary="紫微斗数运限（大限/小限/流年/流月/流日/流时 + 动态四化）。",
        operation_label_zh="紫微运限",
        family="metaphysics",
        rest_path="/api/cn/ziwei/horoscope",
        mcp_name="ziwei_horoscope",
    ),
    ToolSpec(
        key="ziwei_rules",
        bind=raw_invoke(calculate_ziwei_rules),
        request_model=ZiweiRulesRequest,
        summary=(
            "紫微斗数规则查表：按年干返回四化等规则参照，供解读时查证；"
            "起命盘用 ziwei_birth，看运限用 ziwei_horoscope。"
        ),
        operation_label_zh="紫微规则",
        family="metaphysics",
        rest_path="/api/cn/ziwei/rules",
        mcp_name="ziwei_rules",
    ),
    ToolSpec(
        key="liureng_gods",
        bind=raw_invoke(calculate_liureng_gods),
        request_model=LiuRengGodsRequest,
        summary=(
            "六壬课体与天将：问具体事件的细节展开与时间应验，信息量最密集；"
            "快问快答用 jinkou，按年看流月用 liureng_runyear。"
        ),
        operation_label_zh="六壬课",
        family="metaphysics",
        rest_path="/api/cn/liureng/gods",
        mcp_name="liureng_gods",
    ),
    ToolSpec(
        key="liureng_runyear",
        bind=person_invoke(
            calculate_liureng_runyear, also_pass=("use_true_solar_time",)
        ),
        request_model=LiuRengRunyearRequest,
        summary=(
            "六壬流年：按年看流月走势的年度辅助；"
            "问具体单事用 liureng_gods，个人年运细看用 timing_analysis。"
        ),
        operation_label_zh="六壬流年",
        family="metaphysics",
        rest_path="/api/cn/liureng/runyear",
        mcp_name="liureng_runyear",
    ),
    ToolSpec(
        key="qimen",
        bind=raw_invoke(calculate_qimen_analysis),
        request_model=QimenAnalysisRequest,
        summary=(
            "奇门遁甲：问方位选择 / 行动时机 / 谋略布局（含趋吉避凶方位）；"
            "问单事成败用 sixyao，看大势国运用 taiyi。"
        ),
        operation_label_zh="奇门遁甲",
        family="metaphysics",
        rest_path="/api/cn/qimen",
        mcp_name="qimen",
    ),
    ToolSpec(
        key="taiyi",
        bind=raw_invoke(calculate_taiyi_analysis),
        request_model=TaiyiAnalysisRequest,
        summary=(
            "太乙神数：看大势 / 国运 / 天地格局，不问个人小事；"
            "个人问事用 sixyao / meihua_analysis / qimen。"
        ),
        operation_label_zh="太乙",
        family="metaphysics",
        rest_path="/api/cn/taiyi",
        mcp_name="taiyi",
    ),
    ToolSpec(
        key="jinkou",
        bind=raw_invoke(calculate_jinkou_analysis),
        request_model=JinkouAnalysisRequest,
        summary=(
            "金口诀：即时简断、快速给吉凶方向，适合快问快答；"
            "要细节展开用 liureng_gods，问成败用 sixyao。"
        ),
        operation_label_zh="金口诀",
        family="metaphysics",
        rest_path="/api/cn/jinkou",
        mcp_name="jinkou",
    ),
]
