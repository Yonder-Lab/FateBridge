"""Compare business results, request contracts and shared utility edge cases."""

import json
import runpy
import sys
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from fatebridge.core.execution_context import call_clock
from fatebridge.core.requests.astrology import AstroChartPolyRequest as _model_0
from fatebridge.core.requests.astrology import AstroChartRequest as _model_1
from fatebridge.core.requests.astrology import AstroRelativeFlatRequest as _model_2
from fatebridge.core.requests.astrology import AstroRelativePartyRequest as _model_3
from fatebridge.core.requests.astrology import AstroRelativeRequest as _model_4
from fatebridge.core.requests.base import _DeferredModel
from fatebridge.core.requests.bazi import BaziBirthRequest as _model_5
from fatebridge.core.requests.bazi import BaziCareerRequest as _model_6
from fatebridge.core.requests.bazi import BaziChildrenRequest as _model_7
from fatebridge.core.requests.bazi import BaziDimensionRequest as _model_8
from fatebridge.core.requests.bazi import BaziEducationRequest as _model_9
from fatebridge.core.requests.bazi import BaziHealthRequest as _model_10
from fatebridge.core.requests.bazi import BaziMarriageRequest as _model_11
from fatebridge.core.requests.bazi import BaziPersonalityRequest as _model_12
from fatebridge.core.requests.bazi import BaziRelativesRequest as _model_13
from fatebridge.core.requests.bazi import BaziRomanceRequest as _model_14
from fatebridge.core.requests.bazi import BaziWealthRequest as _model_15
from fatebridge.core.requests.birth import AstroBirthRequest as _model_16
from fatebridge.core.requests.birth import FateBridgeRequest as _model_17
from fatebridge.core.requests.calendar import JieqiYearRequest as _model_18
from fatebridge.core.requests.calendar import NongliTimeRequest as _model_19
from fatebridge.core.requests.compatibility import (
    SukuyoCompatibilityRequest as _model_20,
)
from fatebridge.core.requests.compatibility import (
    TwoPersonCompatibilityRequest as _model_21,
)
from fatebridge.core.requests.divination import CanpingRequest as _model_22
from fatebridge.core.requests.divination import GuaLookupRequest as _model_23
from fatebridge.core.requests.divination import GuaMeiyiRequest as _model_24
from fatebridge.core.requests.divination import HeluoRequest as _model_25
from fatebridge.core.requests.divination import MeihuaAnalysisRequest as _model_26
from fatebridge.core.requests.divination import OtherBuRequest as _model_27
from fatebridge.core.requests.divination import SanShiUnitedRequest as _model_28
from fatebridge.core.requests.divination import SixYaoLineRequest as _model_29
from fatebridge.core.requests.divination import SixYaoRequest as _model_30
from fatebridge.core.requests.divination import SuZhanRequest as _model_31
from fatebridge.core.requests.divination import TongSheFaRequest as _model_32
from fatebridge.core.requests.metaphysics import JinkouAnalysisRequest as _model_33
from fatebridge.core.requests.metaphysics import LiuRengGodsRequest as _model_34
from fatebridge.core.requests.metaphysics import LiuRengRunyearRequest as _model_35
from fatebridge.core.requests.metaphysics import QimenAnalysisRequest as _model_36
from fatebridge.core.requests.metaphysics import TaiyiAnalysisRequest as _model_37
from fatebridge.core.requests.metaphysics import ZiweiBirthRequest as _model_38
from fatebridge.core.requests.metaphysics import ZiweiHoroscopeRequest as _model_39
from fatebridge.core.requests.metaphysics import ZiweiRulesRequest as _model_40
from fatebridge.core.requests.reference import ExportParseRequest as _model_41
from fatebridge.core.requests.reference import ExportRegistryRequest as _model_42
from fatebridge.core.requests.reference import KnowledgeReadRequest as _model_43
from fatebridge.core.requests.reference import KnowledgeRegistryRequest as _model_44
from fatebridge.core.requests.timing import DayunAnalysisRequest as _model_45
from fatebridge.core.requests.timing import JieqiTimelineRequest as _model_46
from fatebridge.core.requests.timing import LiunianAnalysisRequest as _model_47
from fatebridge.core.requests.timing import LiuriAnalysisRequest as _model_48
from fatebridge.core.requests.timing import LiushiAnalysisRequest as _model_49
from fatebridge.core.requests.timing import LiuyueAnalysisRequest as _model_50
from fatebridge.core.requests.timing import TimingAnalysisRequest as _model_51
from fatebridge.core.requests.western_events import AstroElectionRequest as _model_52
from fatebridge.core.requests.western_events import (
    AstroExtraReturnsRequest as _model_53,
)
from fatebridge.core.requests.western_events import AstroHoraryRequest as _model_54
from fatebridge.core.requests.western_events import AstroMundaneRequest as _model_55
from fatebridge.core.requests.western_lifespan import AstroAgePointRequest as _model_56
from fatebridge.core.requests.western_lifespan import AstroBalbillusRequest as _model_57
from fatebridge.core.requests.western_lifespan import (
    AstroDistributionsRequest as _model_58,
)
from fatebridge.core.requests.western_lifespan import AstroHarmonicRequest as _model_59
from fatebridge.core.requests.western_lifespan import (
    AstroJaynesProgRequest as _model_60,
)
from fatebridge.core.requests.western_lifespan import AstroKeypointsRequest as _model_61
from fatebridge.core.requests.western_lifespan import AstroLifespanRequest as _model_62
from fatebridge.core.requests.western_lifespan import (
    AstroLunationPhaseRequest as _model_63,
)
from fatebridge.core.requests.western_lifespan import (
    AstroPersianDirectedRequest as _model_64,
)
from fatebridge.core.requests.western_lifespan import (
    AstroPlanetaryAgesRequest as _model_65,
)
from fatebridge.core.requests.western_lifespan import (
    AstroPlanetaryArcRequest as _model_66,
)
from fatebridge.core.requests.western_lifespan import (
    AstroTriplicityRulersRequest as _model_67,
)
from fatebridge.core.requests.western_lifespan import AstroVedicProgRequest as _model_68
from fatebridge.core.requests.western_lifespan import (
    AstroYearSystem129Request as _model_69,
)
from fatebridge.core.requests.western_timing import (
    WesternTimingModuleRequest as _model_70,
)
from fatebridge.core.requests.western_timing import WesternTimingRequest as _model_71
from fatebridge.services.tool_catalog import CATALOG
from fatebridge.utils.analysis_clock import get_current_analysis_date
from fatebridge.utils.birth_input import create_person_info, normalize_gender
from fatebridge.utils.elements import get_element_relationship
from fatebridge.utils.formatting import format_json_response
from fatebridge.utils.solar_time import (
    calculate_solar_time_adjustment,
    normalize_birth_time,
)

MODELS = {
    "_DeferredModel": _DeferredModel,
    "AstroChartPolyRequest": _model_0,
    "AstroChartRequest": _model_1,
    "AstroRelativeFlatRequest": _model_2,
    "AstroRelativePartyRequest": _model_3,
    "AstroRelativeRequest": _model_4,
    "BaziBirthRequest": _model_5,
    "BaziCareerRequest": _model_6,
    "BaziChildrenRequest": _model_7,
    "BaziDimensionRequest": _model_8,
    "BaziEducationRequest": _model_9,
    "BaziHealthRequest": _model_10,
    "BaziMarriageRequest": _model_11,
    "BaziPersonalityRequest": _model_12,
    "BaziRelativesRequest": _model_13,
    "BaziRomanceRequest": _model_14,
    "BaziWealthRequest": _model_15,
    "AstroBirthRequest": _model_16,
    "FateBridgeRequest": _model_17,
    "JieqiYearRequest": _model_18,
    "NongliTimeRequest": _model_19,
    "SukuyoCompatibilityRequest": _model_20,
    "TwoPersonCompatibilityRequest": _model_21,
    "CanpingRequest": _model_22,
    "GuaLookupRequest": _model_23,
    "GuaMeiyiRequest": _model_24,
    "HeluoRequest": _model_25,
    "MeihuaAnalysisRequest": _model_26,
    "OtherBuRequest": _model_27,
    "SanShiUnitedRequest": _model_28,
    "SixYaoLineRequest": _model_29,
    "SixYaoRequest": _model_30,
    "SuZhanRequest": _model_31,
    "TongSheFaRequest": _model_32,
    "JinkouAnalysisRequest": _model_33,
    "LiuRengGodsRequest": _model_34,
    "LiuRengRunyearRequest": _model_35,
    "QimenAnalysisRequest": _model_36,
    "TaiyiAnalysisRequest": _model_37,
    "ZiweiBirthRequest": _model_38,
    "ZiweiHoroscopeRequest": _model_39,
    "ZiweiRulesRequest": _model_40,
    "ExportParseRequest": _model_41,
    "ExportRegistryRequest": _model_42,
    "KnowledgeReadRequest": _model_43,
    "KnowledgeRegistryRequest": _model_44,
    "DayunAnalysisRequest": _model_45,
    "JieqiTimelineRequest": _model_46,
    "LiunianAnalysisRequest": _model_47,
    "LiuriAnalysisRequest": _model_48,
    "LiushiAnalysisRequest": _model_49,
    "LiuyueAnalysisRequest": _model_50,
    "TimingAnalysisRequest": _model_51,
    "AstroElectionRequest": _model_52,
    "AstroExtraReturnsRequest": _model_53,
    "AstroHoraryRequest": _model_54,
    "AstroMundaneRequest": _model_55,
    "AstroAgePointRequest": _model_56,
    "AstroBalbillusRequest": _model_57,
    "AstroDistributionsRequest": _model_58,
    "AstroHarmonicRequest": _model_59,
    "AstroJaynesProgRequest": _model_60,
    "AstroKeypointsRequest": _model_61,
    "AstroLifespanRequest": _model_62,
    "AstroLunationPhaseRequest": _model_63,
    "AstroPersianDirectedRequest": _model_64,
    "AstroPlanetaryAgesRequest": _model_65,
    "AstroPlanetaryArcRequest": _model_66,
    "AstroTriplicityRulersRequest": _model_67,
    "AstroVedicProgRequest": _model_68,
    "AstroYearSystem129Request": _model_69,
    "WesternTimingModuleRequest": _model_70,
    "WesternTimingRequest": _model_71,
}

AUDIT = Path(__file__).resolve().parent
PRIOR = AUDIT / "capture_branches.py"


def capture():
    shared = runpy.run_path(str(PRIOR))
    results = shared["capture"]()
    digest = shared["digest"]
    results["catalog/order"] = digest([spec.key for spec in CATALOG])
    for name, model in MODELS.items():
        if (
            isinstance(model, type)
            and issubclass(model, BaseModel)
            and model is not BaseModel
        ):
            results[f"request/schema/{name}"] = digest(model.model_json_schema())
            results[f"request/fields/{name}"] = digest(list(model.model_fields))
    for value in (None, "男", "female", "m", "阴", True, False, "", "unknown"):
        results[f"gender/{value!r}"] = digest(normalize_gender(value))
    for solar, explicit, place, longitude in [
        (False, True, "上海", None),
        (True, True, "上海", None),
        (True, True, "江苏省南通市海安市", None),
        (True, False, "未知地点", None),
        (True, True, "未知地点", None),
        (True, True, "未提供", -74.0),
    ]:
        person = create_person_info(
            1990,
            6,
            1,
            0,
            gender="female",
            birth_minute=2,
            birth_place=place,
            birth_longitude=longitude,
            use_true_solar_time=solar,
            true_solar_explicit=explicit,
        )
        key = f"birth/{solar}/{explicit}/{place}/{longitude}"
        try:
            normalized = normalize_birth_time(person)
            value = {
                **normalized.as_dict(),
                "input": normalized.input_datetime.isoformat(),
                "corrected": normalized.corrected_datetime.isoformat(),
            }
        except ValueError as exc:
            value = {"error": str(exc)}
        results[key] = digest(value)
    for zone, longitude in [("Asia/Shanghai", 121.47), ("America/New_York", -74.0)]:
        for strategy in ("apparent", "longitude_only"):
            results[f"solar/{zone}/{strategy}"] = digest(
                calculate_solar_time_adjustment(
                    datetime(1990, 6, 1, 0, 2), zone, longitude, strategy=strategy
                )
            )
    with call_clock(shared["AS_OF"]):
        for year, month in [(None, None), (2028, None), (None, 2), (2028, 2)]:
            results[f"clock/{year}/{month}"] = digest(
                get_current_analysis_date(year, month)
            )
    for compact in (True, False):
        for snapshot in (True, False):
            data = {"text": "虚构样例", "snapshot_text": "快照", "nested": [1, None]}
            results[f"format/{compact}/{snapshot}"] = digest(
                format_json_response(
                    data, compact=compact, include_snapshot_text=snapshot
                )
            )
    for first in ("木", "火", "土", "金", "水", "invalid"):
        for second in ("木", "火", "土", "金", "水"):
            results[f"elements/{first}/{second}"] = digest(
                get_element_relationship(first, second)
            )
    for name, model, payload in [
        (
            "bad-date",
            MODELS["FateBridgeRequest"],
            {"birth_year": 2028, "birth_month": 2, "birth_day": 30, "birth_hour": 0},
        ),
        (
            "unknown-field",
            MODELS["GuaLookupRequest"],
            {"name": "乾", "unknown": "must be rejected"},
        ),
    ]:
        try:
            model.model_validate(payload)
        except ValidationError as exc:
            results[f"validation/{name}"] = digest(exc.errors(include_url=False))
        else:
            raise AssertionError(name)
    return results


if __name__ == "__main__":
    result = capture()
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Captured {len(result)} business, contract and utility hashes")
