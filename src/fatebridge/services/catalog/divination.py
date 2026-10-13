"""Divination tool declarations and domain binding helpers."""

from __future__ import annotations

from typing import List

from fatebridge.application.bindings import lazy_service, raw_invoke
from fatebridge.application.tool_spec import ToolSpec
from fatebridge.core.requests.compatibility import SukuyoCompatibilityRequest
from fatebridge.core.requests.divination import (
    CanpingRequest,
    GuaLookupRequest,
    GuaMeiyiRequest,
    HeluoRequest,
    MeihuaAnalysisRequest,
    OtherBuRequest,
    SanShiUnitedRequest,
    SixYaoRequest,
    SuZhanRequest,
    TongSheFaRequest,
)

calculate_canping_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_canping_analysis"
)


calculate_gua_lookup = lazy_service(
    "fatebridge.services.divination", "calculate_gua_lookup"
)


calculate_gua_meiyi = lazy_service(
    "fatebridge.services.divination", "calculate_gua_meiyi"
)


calculate_heluo_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_heluo_analysis"
)


calculate_meihua_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_meihua_analysis"
)


calculate_otherbu_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_otherbu_analysis"
)


calculate_sanshiunited_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_sanshiunited_analysis"
)


calculate_sixyao_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_sixyao_analysis"
)


calculate_sukuyo_compatibility = lazy_service(
    "fatebridge.services.divination", "calculate_sukuyo_compatibility"
)


calculate_suzhan_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_suzhan_analysis"
)


calculate_tongshefa_analysis = lazy_service(
    "fatebridge.services.divination", "calculate_tongshefa_analysis"
)

SPECS: List[ToolSpec] = [
    # --- Divination --------------------------------------------------------
    ToolSpec(
        key="gua_lookup",
        bind=raw_invoke(calculate_gua_lookup),
        request_model=GuaLookupRequest,
        summary="卦象查询：传单个卦名或卦码，返回该卦的六十四卦义理；要一次查多卦用 gua_meiyi。",
        operation_label_zh="卦象查询",
        family="divination",
        rest_path="/api/divination/gua",
        mcp_name="gua_lookup",
    ),
    ToolSpec(
        key="gua_meiyi",
        bind=raw_invoke(calculate_gua_meiyi),
        request_model=GuaMeiyiRequest,
        summary="卦义批量查询：传一组卦名/卦码（List），一次返回多卦义理；单卦查询用 gua_lookup。",
        operation_label_zh="卦义",
        family="divination",
        rest_path="/api/cn/gua/meiyi",
        mcp_name="gua_meiyi",
    ),
    ToolSpec(
        key="meihua_analysis",
        bind=raw_invoke(calculate_meihua_analysis),
        request_model=MeihuaAnalysisRequest,
        summary=(
            "梅花易数：当下起念、随机取数的即兴一问；"
            "问具体事成败用 sixyao，问方位时机用 qimen。"
        ),
        operation_label_zh="梅花易数",
        family="divination",
        rest_path="/api/divination/meihua",
        mcp_name="meihua_analysis",
    ),
    ToolSpec(
        key="tongshefa",
        bind=raw_invoke(calculate_tongshefa_analysis),
        request_model=TongSheFaRequest,
        summary=(
            "通蓍法起卦：古法蓍草起卦问一事；"
            "即兴起念用 meihua_analysis，问成败用 sixyao。"
        ),
        operation_label_zh="通蓍法",
        family="divination",
        rest_path="/api/divination/tongshefa",
        mcp_name="tongshefa",
    ),
    ToolSpec(
        key="sixyao",
        bind=raw_invoke(calculate_sixyao_analysis),
        request_model=SixYaoRequest,
        summary=(
            "六爻纳甲：问一件具体事能不能成（需明确一事一方向）；"
            "method=coin 真·摇钱起卦（系统随机六掷，可传 coins 报真实掷果或 seed 复现）；"
            "传 gua_code/lines 用已摇之卦，未传则按起卦时刻自动时间起卦；"
            "即兴随机一问用 meihua_analysis，问方位谋略用 qimen。"
        ),
        operation_label_zh="六爻",
        family="divination",
        rest_path="/api/divination/sixyao",
        mcp_name="sixyao",
    ),
    ToolSpec(
        key="canping",
        bind=raw_invoke(calculate_canping_analysis),
        request_model=CanpingRequest,
        summary=(
            "邵子参评数 / 金锁银匙（数算命格）：专家级数算查命，"
            "普通命格画像用 analyze_destiny 或 ziwei_birth，仅深追问才调。"
        ),
        operation_label_zh="邵子参评数",
        family="divination",
        rest_path="/api/divination/canping",
        mcp_name="canping",
    ),
    ToolSpec(
        key="heluo",
        bind=raw_invoke(calculate_heluo_analysis),
        request_model=HeluoRequest,
        summary=(
            "河洛理数（数算命格）：以河洛数推命的专家级数算，"
            "普通命格用 analyze_destiny 或 ziwei_birth，仅深追问才调。"
        ),
        operation_label_zh="河洛理数",
        family="divination",
        rest_path="/api/divination/heluo",
        mcp_name="heluo",
    ),
    ToolSpec(
        key="suzhan",
        bind=raw_invoke(calculate_suzhan_analysis),
        request_model=SuZhanRequest,
        summary=(
            "宿占：以二十八宿星宿为核心的择日 / 星宿吉凶；"
            "西式随机问事用 otherbu，中式起卦用 sixyao 或 meihua_analysis。"
        ),
        operation_label_zh="宿占",
        family="divination",
        rest_path="/api/divination/suzhan",
        mcp_name="suzhan",
    ),
    ToolSpec(
        key="sukuyo_compatibility",
        bind=raw_invoke(calculate_sukuyo_compatibility),
        request_model=SukuyoCompatibilityRequest,
        summary="宿曜双人相性分析（三九の秘法，二十七宿）。",
        operation_label_zh="宿曜合盘",
        family="compatibility",
        rest_path="/api/compatibility/sukuyo",
        mcp_name="sukuyo_compatibility",
    ),
    ToolSpec(
        key="otherbu",
        bind=raw_invoke(calculate_otherbu_analysis),
        request_model=OtherBuRequest,
        summary=(
            "其他卜法：基于占星骰子（星座/宫位/行星 + 所问之事）起课的西式占卜，"
            "区别于六爻/梅花/通蓍等中式卜法。"
        ),
        operation_label_zh="其他卜法",
        family="divination",
        rest_path="/api/divination/otherbu",
        mcp_name="otherbu",
    ),
    ToolSpec(
        key="sanshiunited",
        bind=raw_invoke(calculate_sanshiunited_analysis),
        request_model=SanShiUnitedRequest,
        summary=(
            "三式合参：太乙＋六壬＋奇门联合推算，专家模式或重大决策才调；"
            "普通问事用单术 sixyao / qimen / meihua_analysis。"
        ),
        operation_label_zh="三式合参",
        family="divination",
        rest_path="/api/divination/sanshiunited",
        mcp_name="sanshiunited",
    ),
]
