"""Residential inputs: location, facing and observed form stay distinct."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from fatebridge.core.request_models import _DeferredModel
from fatebridge.utils.timezones import parse_timezone_name

Direction = Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
Trigram = Literal["坎", "艮", "震", "巽", "离", "坤", "兑", "乾"]
NorthReference = Literal["magnetic", "true"]
Basis = Literal["measured", "user_confirmed"]
BazhaiRuleset = Literal["bazhai_sitting_v1"]
JinsuoRuleset = Literal["jinsuo_basic_fixed_v1"]
AnnualRuleset = Literal["annual_zibai_lichun_v1"]
Year = int


class TimeInput(_DeferredModel):
    timezone_name: str = Field(
        default="Asia/Shanghai", description="IANA 时区或 UTC 偏移；用于年度边界"
    )

    @field_validator("timezone_name")
    @classmethod
    def timezone_exists(cls, value: str) -> str:
        parse_timezone_name(value)
        return value


class MingguaRequest(TimeInput):
    effective_birth_year: Optional[Year] = Field(
        default=None,
        ge=1800,
        le=2199,
        description="已确认换年后的有效生年；与 birth_at 二选一",
    )
    birth_at: Optional[datetime] = Field(
        default=None, description="含时区的 ISO 出生时刻；不使用真太阳时"
    )
    gender_convention: Optional[Literal["male", "female"]] = Field(
        default=None, description="传统男女起算法；未知时返回两个候选，不默认男"
    )
    year_boundary: Literal["lichun", "january_1"] = Field(
        default="lichun", description="选定命卦换年约定；非所有古本统一规则"
    )
    ruleset_id: BazhaiRuleset = "bazhai_sitting_v1"

    @model_validator(mode="after")
    def validate_birth(self) -> "MingguaRequest":
        if self.effective_birth_year is not None and self.birth_at is not None:
            raise ValueError("effective_birth_year 与 birth_at 不能同时提供")
        if self.birth_at is not None:
            if self.birth_at.tzinfo is None or self.birth_at.utcoffset() is None:
                raise ValueError("birth_at 必须包含时区")
            if not 1801 <= self.birth_at.year <= 2199:
                raise ValueError("birth_at 支持 1801–2199 年")
        return self


class Occupant(MingguaRequest):
    subject_id: str = Field(min_length=1, max_length=100)


class House(_DeferredModel):
    object_id: str = Field(default="house", min_length=1, max_length=100)
    sitting_trigram: Optional[Trigram] = None
    facing_degrees: Optional[float] = Field(
        default=None,
        ge=0,
        le=360,
        allow_inf_nan=False,
        description="宅向角度，0°北、顺时针；360°归一为0°",
    )
    north_reference: Optional[NorthReference] = None
    orientation_basis: Basis = "user_confirmed"
    division_method: Literal["confirmed_angular_sectors"] = "confirmed_angular_sectors"

    @model_validator(mode="after")
    def bearing_reference(self) -> "House":
        if self.facing_degrees is not None and self.north_reference is None:
            raise ValueError("角度输入必须明确 north_reference")
        if self.facing_degrees is not None and self.sitting_trigram is not None:
            assert self.north_reference is not None
            from .directions import sitting_from_facing

            if (
                sitting_from_facing(self.facing_degrees, self.north_reference)[
                    "trigram"
                ]
                != self.sitting_trigram
            ):
                raise ValueError("宅向推导的坐山与 sitting_trigram 不一致")
        return self


class Placement(_DeferredModel):
    object_id: str = Field(min_length=1, max_length=100)
    purpose: Literal["door", "bed", "desk", "stove"]
    location_direction: Direction
    facing_direction: Optional[Direction] = Field(
        default=None, description="门朝向、床头、书桌朝向或已确认的灶火门，独立于位置"
    )
    facing_role: Optional[
        Literal["door_facing", "headboard", "desk_facing", "fire_mouth"]
    ] = None
    subject_id: Optional[str] = None
    observation_basis: Basis = "user_confirmed"

    @model_validator(mode="after")
    def facing_semantics(self) -> "Placement":
        roles = {
            "door": "door_facing",
            "bed": "headboard",
            "desk": "desk_facing",
            "stove": "fire_mouth",
        }
        if (self.facing_direction is None) != (self.facing_role is None):
            raise ValueError("facing_direction 和 facing_role 必须一起提供")
        if self.facing_role is not None and self.facing_role != roles[self.purpose]:
            raise ValueError("facing_role 与 purpose 不匹配")
        return self


class BazhaiRequest(_DeferredModel):
    house: Optional[House] = None
    occupants: List[Occupant] = Field(default_factory=list, max_length=50)
    placements: List[Placement] = Field(default_factory=list, max_length=200)
    ruleset_id: BazhaiRuleset = "bazhai_sitting_v1"

    @model_validator(mode="after")
    def unique_ids(self) -> "BazhaiRequest":
        ids = [o.subject_id for o in self.occupants]
        objects = [p.object_id for p in self.placements]
        if len(set(ids)) != len(ids) or len(set(objects)) != len(objects):
            raise ValueError("住户及布局对象 ID 必须分别唯一")
        if self.house is not None and self.house.object_id in ids:
            raise ValueError("住宅 ID 不得与住户 ID 重复")
        if self.house is not None and self.house.object_id in objects:
            raise ValueError("布局对象 ID 不得与住宅 ID 重复")
        if any(
            p.subject_id is not None and p.subject_id not in ids
            for p in self.placements
        ):
            raise ValueError("布局对象引用了未提供的住户")
        return self


class EnvironmentFeature(_DeferredModel):
    object_id: str = Field(min_length=1, max_length=100)
    direction: Direction
    classification: Literal["sand", "water", "mixed", "unknown"]
    classification_basis: Basis
    evidence: str = Field(
        min_length=1,
        max_length=1000,
        description="用户确认或测量的分类依据；不按物品名称自动猜测砂水",
    )
    label: Optional[str] = Field(default=None, max_length=100)


class JinsuoRequest(_DeferredModel):
    features: List[EnvironmentFeature] = Field(default_factory=list, max_length=500)
    ruleset_id: JinsuoRuleset = "jinsuo_basic_fixed_v1"

    @model_validator(mode="after")
    def unique_features(self) -> "JinsuoRequest":
        ids = [f.object_id for f in self.features]
        if len(set(ids)) != len(ids):
            raise ValueError("环境特征 object_id 必须唯一")
        return self


class AnnualRequest(TimeInput):
    effective_year: Optional[Year] = Field(
        default=None,
        ge=1800,
        le=2199,
        description="已确认立春后的有效年；与 query_at 二选一",
    )
    query_at: Optional[datetime] = Field(
        default=None, description="含时区的查询时刻，以立春交节换年"
    )
    ruleset_id: AnnualRuleset = "annual_zibai_lichun_v1"

    @model_validator(mode="after")
    def validate_query(self) -> "AnnualRequest":
        if self.effective_year is not None and self.query_at is not None:
            raise ValueError("effective_year 与 query_at 不能同时提供")
        if self.query_at is not None:
            if self.query_at.tzinfo is None or self.query_at.utcoffset() is None:
                raise ValueError("query_at 必须包含时区")
            if not 1801 <= self.query_at.year <= 2199:
                raise ValueError("query_at 支持 1801–2199 年")
        return self


class HousePeriod(TimeInput):
    """One explicitly selected historical event, never the query date."""

    basis: Literal[
        "construction_completion",
        "first_occupancy",
        "confirmed_major_renovation",
        "expert_confirmed",
    ]
    evidence: str = Field(min_length=1, max_length=2000)
    period_number: Optional[int] = Field(default=None, ge=1, le=9)
    effective_event_year: Optional[int] = Field(default=None, ge=1800, le=2199)
    event_at: Optional[datetime] = None
    qualifies_for_period_reset: Optional[bool] = None

    @model_validator(mode="after")
    def selected_event(self) -> "HousePeriod":
        if (
            sum(
                x is not None
                for x in (self.period_number, self.effective_event_year, self.event_at)
            )
            != 1
        ):
            raise ValueError(
                "定运需且仅需 period_number、effective_event_year、event_at 之一"
            )
        if not self.evidence.strip():
            raise ValueError("定运 evidence 不得为空白")
        if self.event_at is not None:
            AnnualRequest(query_at=self.event_at, timezone_name=self.timezone_name)
        if self.basis == "expert_confirmed" and self.period_number is None:
            raise ValueError("expert_confirmed 必须显式确认 period_number")
        if self.basis == "confirmed_major_renovation":
            if self.qualifies_for_period_reset is not True:
                raise ValueError(
                    "大修换运须明确 qualifies_for_period_reset=true 并记录依据"
                )
        elif self.qualifies_for_period_reset is not None:
            raise ValueError("qualifies_for_period_reset 仅用于已确认的大修换运")
        return self


class XuankongRequest(_DeferredModel):
    house: Optional[House] = None
    period: Optional[HousePeriod] = None
    bearing_uncertainty_degrees: float = Field(
        default=0,
        ge=0,
        le=7.5,
        allow_inf_nan=False,
        description="宅向测量误差半径；跨山界或下/替卦阈值返回候选而非唯一宅盘",
    )
    ruleset_id: Literal["xuankong_zhongzhou_v1"] = "xuankong_zhongzhou_v1"

    @model_validator(mode="after")
    def magnetic_reference(self) -> "XuankongRequest":
        if (
            self.house is not None
            and self.house.facing_degrees is not None
            and self.house.north_reference != "magnetic"
        ):
            raise ValueError("本玄空版本使用磁北宅向；真北需先由用户完成磁偏角校正")
        return self


class AssessRequest(BazhaiRequest):
    features: List[EnvironmentFeature] = Field(default_factory=list, max_length=500)
    effective_year: Optional[Year] = Field(default=None, ge=1800, le=2199)
    query_at: Optional[datetime] = None
    timezone_name: str = "Asia/Shanghai"
    methods: List[Literal["bazhai", "jinsuo", "annual_stars", "xuankong_natal"]] = (
        Field(default=["bazhai", "jinsuo", "annual_stars"], min_length=1)
    )
    jinsuo_ruleset_id: JinsuoRuleset = "jinsuo_basic_fixed_v1"
    annual_ruleset_id: AnnualRuleset = "annual_zibai_lichun_v1"
    xuankong: Optional[XuankongRequest] = Field(
        default=None,
        description="显式启用宅盘时的历史定运和宅向；可继承顶层 house，年星不继承宅运",
    )

    @model_validator(mode="after")
    def validate_layers(self) -> "AssessRequest":
        if len(set(self.methods)) != len(self.methods):
            raise ValueError("methods 不得重复")
        AnnualRequest(
            effective_year=self.effective_year,
            query_at=self.query_at,
            timezone_name=self.timezone_name,
            ruleset_id=self.annual_ruleset_id,
        )
        JinsuoRequest(features=self.features, ruleset_id=self.jinsuo_ruleset_id)
        if self.xuankong is not None and "xuankong_natal" not in self.methods:
            raise ValueError("提供 xuankong 时须在 methods 中选择 xuankong_natal")
        if "xuankong_natal" in self.methods:
            natal = self.xuankong or XuankongRequest()
            if self.house is not None and natal.house is not None:
                if self.house.model_dump() != natal.house.model_dump():
                    raise ValueError("合参顶层 house 与 xuankong.house 必须一致")
            XuankongRequest.model_validate(
                {**natal.model_dump(), "house": natal.house or self.house}
            )
        return self


class DirectionsRequest(_DeferredModel):
    bearing_degrees: Optional[float] = Field(
        default=None, ge=0, le=360, allow_inf_nan=False
    )
    north_reference: Optional[NorthReference] = None
    ruleset_id: Literal["houtian_directions_v1"] = "houtian_directions_v1"

    @model_validator(mode="after")
    def validate_reference(self) -> "DirectionsRequest":
        if self.bearing_degrees is not None and self.north_reference is None:
            raise ValueError("角度输入必须明确 north_reference")
        return self
