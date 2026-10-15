"""Residential inputs: location, facing and observed form stay distinct."""

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import (
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)

from fatebridge.core.requests.base import _DeferredModel
from fatebridge.utils.timezones import parse_timezone_name

from .layout_inputs import ElementAdjustment, FormObservation
from .surface_inputs import SurfaceConstraints, SurfaceLayout

Direction = Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
Trigram = Literal["坎", "艮", "震", "巽", "离", "坤", "兑", "乾"]
NorthReference = Literal["magnetic", "true"]
Basis = Literal["measured", "user_confirmed"]
BazhaiRuleset = Literal["bazhai_sitting_v1"]
JinsuoRuleset = Literal["jinsuo_basic_fixed_v1"]
AnnualRuleset = Literal["annual_zibai_lichun_v1"]
Method = Literal["bazhai", "jinsuo", "annual_stars", "xuankong_natal"]
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
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "anyOf": [
                        {"properties": {left: {"type": "null"}}},
                        {"properties": {right: {"type": "null"}}},
                    ]
                }
                for left, right in [
                    ("birth_date", "birth_at"),
                    ("birth_date", "effective_birth_year"),
                    ("birth_at", "effective_birth_year"),
                ]
            ]
        }
    )
    birth_date: Optional[date] = Field(
        default=None,
        description="公历出生日期；非立春当日无需出生时刻，与有效生年/出生时刻三选一",
    )
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
        if (
            sum(
                v is not None
                for v in (self.effective_birth_year, self.birth_at, self.birth_date)
            )
            > 1
        ):
            raise ValueError("effective_birth_year、birth_at、birth_date 只能提供一项")
        if self.birth_date is not None and not 1801 <= self.birth_date.year <= 2199:
            raise ValueError("birth_date 支持 1801–2199 年")
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


_PLACEMENT_FACING_ROLES = {
    "door": "door_facing",
    "bed": "headboard",
    "desk": "desk_facing",
    "stove": "fire_mouth",
}


_PLACEMENT_SCHEMA_CONSTRAINTS: Dict[str, Any] = {
    "allOf": [
        {
            "anyOf": [
                {
                    "required": [field],
                    "properties": {field: {"type": "string"}},
                }
                for field in ("location_direction", "facing_direction")
            ]
        },
        {
            "anyOf": [
                {
                    "properties": {
                        field: {"type": "null"}
                        for field in ("facing_direction", "facing_role")
                    }
                },
                {
                    "required": ["facing_direction", "facing_role"],
                    "properties": {
                        field: {"type": "string"}
                        for field in ("facing_direction", "facing_role")
                    },
                },
            ]
        },
        *[
            {
                "if": {"properties": {"purpose": {"const": purpose}}},
                "then": {"properties": {"facing_role": {"enum": [None, role]}}},
            }
            for purpose, role in _PLACEMENT_FACING_ROLES.items()
        ],
        {
            "anyOf": [
                {"properties": {"subject_id": {"type": "null"}}},
                {"properties": {"subject_ids": {"type": "null"}}},
            ]
        },
    ]
}


class Placement(_DeferredModel):
    """门床桌灶的已确认方位。至少提供位置或朝向；两者均未知时省略本对象，
    可在 form_observations 中独立提供形态。朝向和对应 facing_role 必须成对。
    """

    # Publish the same cross-field constraints that facing_semantics enforces.
    # Optional fields may be omitted or explicitly null; neither is a bearing.
    model_config = ConfigDict(json_schema_extra=_PLACEMENT_SCHEMA_CONSTRAINTS)

    object_id: str = Field(min_length=1, max_length=100)
    purpose: Literal["door", "bed", "desk", "stove"]
    location_direction: Optional[Direction] = Field(
        default=None,
        description="已确认对象相对全宅中心的落宫；未知则省略，不能由朝向推断",
    )
    facing_direction: Optional[Direction] = Field(
        default=None,
        description="门朝向、床头、书桌朝向或已确认的灶火门，独立于位置；提供时必须同时提供对应 facing_role",
    )
    facing_role: Optional[
        Literal["door_facing", "headboard", "desk_facing", "fire_mouth"]
    ] = Field(
        default=None,
        description="与 facing_direction 成对：door=door_facing、bed=headboard、desk=desk_facing、stove=fire_mouth",
    )
    subject_id: Optional[str] = Field(
        default=None,
        description="单人使用；与 subject_ids 互斥，两者省略时应用全部已提供住户",
    )
    subject_ids: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        max_length=50,
        json_schema_extra={"uniqueItems": True},
        description="对象实际共用住户 ID 集合；与 subject_id 互斥，不纳入其他住户，宅盘仍单独保留",
    )
    observation_basis: Basis = "user_confirmed"

    def applies_to_occupant(self, subject_id: str) -> bool:
        """Use one scope predicate for findings and inverse direction options."""
        if self.subject_ids is not None:
            return subject_id in self.subject_ids
        return self.subject_id is None or self.subject_id == subject_id

    @model_validator(mode="after")
    def facing_semantics(self) -> "Placement":
        if self.subject_id is not None and self.subject_ids is not None:
            raise ValueError("subject_id 和 subject_ids 只能提供一项")
        if self.subject_ids is not None and len(set(self.subject_ids)) != len(
            self.subject_ids
        ):
            raise ValueError("对象共用住户 subject_ids 必须唯一")
        if self.location_direction is None and self.facing_direction is None:
            raise ValueError("布局对象至少提供位置或朝向，不猜测缺失位置")
        if (self.facing_direction is None) != (self.facing_role is None):
            raise ValueError("facing_direction 和 facing_role 必须一起提供")
        if (
            self.facing_role is not None
            and self.facing_role != _PLACEMENT_FACING_ROLES[self.purpose]
        ):
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
            referenced not in ids
            for p in self.placements
            for referenced in (
                p.subject_ids
                if p.subject_ids is not None
                else [p.subject_id] if p.subject_id is not None else []
            )
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


class ExternalFormObservation(_DeferredModel):
    """Confirmed external forms in house-centred sectors, not indoor backing."""

    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {"properties": {key: {"type": "boolean"}}, "required": [key]}
                for key in ("mountain_present", "water_present")
            ]
        }
    )
    direction: Direction
    mountain_present: Optional[StrictBool] = None
    water_present: Optional[StrictBool] = None
    observation_basis: Literal["measured", "user_confirmed", "image_observed"]
    evidence: str = Field(min_length=1, max_length=1000, pattern=r"\S")

    @model_validator(mode="after")
    def explicit_observation(self) -> "ExternalFormObservation":
        if self.mountain_present is None and self.water_present is None:
            raise ValueError("外局须至少明确山形或水形的一项存在/不存在观察")
        if not self.evidence.strip():
            raise ValueError("外局 evidence 不得为空白")
        return self


class XuankongInterpretationRequest(_DeferredModel):
    """An opt-in, limited rule layer; current period never resets natal age."""

    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {
                    "properties": {
                        "current_period_number": {"type": "null"},
                        "period_evidence": {"type": "null"},
                    }
                },
                {
                    "properties": {
                        "current_period_number": {"type": "integer"},
                        "period_evidence": {"type": "string"},
                    },
                    "required": ["current_period_number", "period_evidence"],
                },
            ]
        }
    )
    ruleset_id: Literal["xuankong_conditioned_v1"] = "xuankong_conditioned_v1"
    current_period_number: Optional[StrictInt] = Field(
        default=None,
        ge=1,
        le=9,
        description="明确确认的评价时运，与历史宅运分开；不从宅运或年星数字推断",
    )
    period_evidence: Optional[str] = Field(
        default=None, min_length=1, max_length=1000, pattern=r"\S"
    )
    external_forms: List[ExternalFormObservation] = Field(
        default_factory=list,
        max_length=8,
        json_schema_extra={
            "allOf": [
                {
                    "contains": {
                        "type": "object",
                        "properties": {"direction": {"const": direction}},
                        "required": ["direction"],
                    },
                    "minContains": 0,
                    "maxContains": 1,
                }
                for direction in ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
            ]
        },
        description="以全宅中心八宫记录外部山形/水形；不沿用金锁砂水、室内靠背或摆件分类",
    )

    @model_validator(mode="after")
    def distinct_confirmed_facts(self) -> "XuankongInterpretationRequest":
        if (self.current_period_number is None) != (self.period_evidence is None):
            raise ValueError("current_period_number 与 period_evidence 必须一起提供")
        if self.period_evidence is not None and not self.period_evidence.strip():
            raise ValueError("period_evidence 不得为空白")
        directions = [o.direction for o in self.external_forms]
        if len(set(directions)) != len(directions):
            raise ValueError("同一全宅外局方向不能重复或互相覆盖")
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
    interpretation: Optional[XuankongInterpretationRequest] = Field(
        default=None,
        description="显式启用有限星组合五行、当令外局与床/门取用条件；不等于完整81组合断法或全宅勘察",
    )

    @model_validator(mode="after")
    def magnetic_reference(self) -> "XuankongRequest":
        if (
            self.house is not None
            and self.house.facing_degrees is not None
            and self.house.north_reference != "magnetic"
        ):
            raise ValueError("本玄空版本使用磁北宅向；真北需先由用户完成磁偏角校正")
        return self


class LayoutConstraint(_DeferredModel):
    """Action permissions, never evidence of a layout's physical properties."""

    object_id: str = Field(min_length=1, max_length=100)
    can_relocate: Optional[StrictBool] = None
    can_rotate: Optional[StrictBool] = None
    can_add_items: Optional[StrictBool] = None
    evidence: str = Field(min_length=1, max_length=1000)

    @field_validator("evidence")
    @classmethod
    def nonblank_evidence(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("动作约束依据不得为空白")
        return value


class LayoutAlternative(_DeferredModel):
    """A user-supplied proposal, independently observed at its new position.

    A move within the same compass sector is still a move. Explicit changes
    therefore cannot be inferred solely from the two directional labels.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {"required": [field], "properties": {field: {"type": "object"}}}
                for field in ("placement", "form_observation")
            ]
        }
    )

    candidate_id: str = Field(min_length=1, max_length=100)
    object_id: str = Field(min_length=1, max_length=100)
    changes: List[Literal["location", "facing"]] = Field(
        min_length=1, max_length=2, json_schema_extra={"uniqueItems": True}
    )
    placement: Optional[Placement] = None
    form_observation: Optional[FormObservation] = None
    physically_feasible: Optional[StrictBool] = Field(
        default=None,
        description="逐方案确认能容纳家具、保持操作空间与通行；允许移动不等于此项为真",
    )
    evidence: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def consistent_candidate(self) -> "LayoutAlternative":
        if not self.evidence.strip() or len(set(self.changes)) != len(self.changes):
            raise ValueError("候选依据不得空白，changes 不得重复")
        observations = [self.placement, self.form_observation]
        supplied = [o for o in observations if o is not None]
        if not supplied or any(o.object_id != self.object_id for o in supplied):
            raise ValueError("候选需独立位置或形态观察，且 object_id 必须一致")
        if len({o.purpose for o in supplied}) != 1:
            raise ValueError("候选位置与形态用途必须一致")
        return self


class AssessRequest(BazhaiRequest):
    scene: Optional[Literal["workstation", "home"]] = Field(
        default=None,
        description="显式场景；未指定 methods 时按已有事实选层。未指定场景保留旧默认；独立形态/桌面默认不引入罗盘层。",
    )
    layout_constraints: List[LayoutConstraint] = Field(
        default_factory=list, max_length=200
    )
    layout_alternatives: List[LayoutAlternative] = Field(
        default_factory=list, max_length=50
    )
    surface_layouts: List[SurfaceLayout] = Field(default_factory=list, max_length=100)
    surface_constraints: List[SurfaceConstraints] = Field(
        default_factory=list, max_length=100
    )
    form_observations: List[FormObservation] = Field(
        default_factory=list, max_length=200
    )
    form_ruleset_id: Literal["indoor_command_authored_v1"] = (
        "indoor_command_authored_v1"
    )
    element_adjustments: List[ElementAdjustment] = Field(
        default_factory=list, max_length=100
    )
    element_ruleset_id: Literal["afsi_element_balance_v1"] = "afsi_element_balance_v1"
    annual_remedy_ruleset_id: Optional[Literal["pang_2026_annual_v1"]] = Field(
        default=None,
        description="显式选择作者2026年盘的有限调节规则；不外推年份或全宅结论",
    )
    analyze_layout: bool = Field(
        default=False,
        description="对布局对象计算跨层落宫、位置/朝向调整方位及五行关系；通用于门床桌灶。原始盘与本分析的完成状态分别保留。",
    )
    features: List[EnvironmentFeature] = Field(default_factory=list, max_length=500)
    effective_year: Optional[Year] = Field(default=None, ge=1800, le=2199)
    query_at: Optional[datetime] = None
    timezone_name: str = "Asia/Shanghai"
    methods: Optional[List[Method]] = Field(
        default=None,
        description="null/省略表示自动选法；场景/作者输入按事实选择，旧无场景无作者请求使用三法。显式列表（含空列表）优先。",
    )
    jinsuo_ruleset_id: JinsuoRuleset = "jinsuo_basic_fixed_v1"
    annual_ruleset_id: AnnualRuleset = "annual_zibai_lichun_v1"
    xuankong: Optional[XuankongRequest] = Field(
        default=None,
        description="显式启用宅盘时的历史定运和宅向；可继承顶层 house，年星不继承宅运",
    )

    @model_validator(mode="before")
    @classmethod
    def select_relevant_methods(cls, value: Any) -> Any:
        if not isinstance(value, dict) or value.get("methods") is not None:
            return value
        authored = bool(value.get("form_observations") or value.get("surface_layouts"))
        if value.get("scene") is None and not authored:
            return {**value, "methods": ["bazhai", "jinsuo", "annual_stars"]}
        selected = []
        if (value.get("placements") or value.get("scene") == "home") and (
            value.get("house") or value.get("occupants")
        ):
            selected.append("bazhai")
        if value.get("features"):
            selected.append("jinsuo")
        if value.get("effective_year") is not None or value.get("query_at") is not None:
            selected.append("annual_stars")
        if value.get("xuankong") is not None:
            selected.append("xuankong_natal")
        return {**value, "methods": selected}

    @property
    def selected_methods(self) -> List[Method]:
        # The before-validator normalizes null on every transport, including
        # MCP hosts which materialize schema defaults before invocation.
        assert self.methods is not None
        return self.methods

    @model_validator(mode="after")
    def validate_layers(self) -> "AssessRequest":
        if (
            not self.selected_methods
            and not self.form_observations
            and not self.surface_layouts
            and self.scene is None
        ):
            raise ValueError(
                "至少选择一层计算；独立形态/桌面作者计算可用 methods=[] 并提供相应观察"
            )
        surfaces = {s.object_id: s for s in self.surface_layouts}
        if len(surfaces) != len(self.surface_layouts):
            raise ValueError("桌面对象不能重复")
        constraints = {c.object_id: c for c in self.surface_constraints}
        if len(constraints) != len(self.surface_constraints):
            raise ValueError("同一桌面的动作约束不能重复")
        if set(constraints) - set(surfaces):
            raise ValueError("桌面约束必须关联已提供桌面")
        for constraint in self.surface_constraints:
            item_ids = {i.object_id for i in surfaces[constraint.object_id].items}
            if set(constraint.locked_item_ids) - item_ids:
                raise ValueError("固定物件必须属于关联桌面")
        for placement in self.placements:
            if placement.object_id in surfaces and placement.purpose != "desk":
                raise ValueError("桌面作者规则只能关联实际书桌，不能套用其他家具")
        if any(
            a.target_method not in self.selected_methods
            for a in self.element_adjustments
        ):
            raise ValueError("元素目标须属于本次选中的计算方法")
        forms = {o.object_id: o for o in self.form_observations}
        if len(forms) != len(self.form_observations):
            raise ValueError("同一对象形态观察不能重复或互相覆盖")
        for object_id in set(forms) & set(surfaces):
            if forms[object_id].purpose != "desk":
                raise ValueError(
                    "同一对象的桌面与形态用途不一致；桌面作者规则只能用于书桌"
                )
        for placement in self.placements:
            if (
                placement.object_id in forms
                and placement.purpose != forms[placement.object_id].purpose
            ):
                raise ValueError("同一对象的形态用途与布局用途不一致")
        request_ids = [a.request_id for a in self.element_adjustments]
        if len(request_ids) != len(set(request_ids)):
            raise ValueError("元素调节请求 ID 必须唯一")
        objects = {p.object_id for p in self.placements}
        known = objects | set(forms)
        constraint_ids = [c.object_id for c in self.layout_constraints]
        if (
            len(set(constraint_ids)) != len(constraint_ids)
            or set(constraint_ids) - known
        ):
            raise ValueError("家具动作约束须唯一且引用已提供对象")
        for furniture_constraint in self.layout_constraints:
            surface_constraint = constraints.get(furniture_constraint.object_id)
            if (
                surface_constraint is not None
                and furniture_constraint.can_add_items is not None
                and surface_constraint.can_add_items is not None
                and furniture_constraint.can_add_items
                != surface_constraint.can_add_items
            ):
                raise ValueError("同一对象的家具与桌面新增许可不得冲突")
        candidates = [c.candidate_id for c in self.layout_alternatives]
        if len(set(candidates)) != len(candidates):
            raise ValueError("布局候选 candidate_id 必须唯一")
        current = {p.object_id: p for p in self.placements}
        for candidate in self.layout_alternatives:
            if candidate.object_id not in objects | set(forms):
                raise ValueError("布局候选须引用已有位置或形态对象")
            base = current.get(candidate.object_id) or forms[candidate.object_id]
            for obs in (candidate.placement, candidate.form_observation):
                if obs is not None and obs.purpose != base.purpose:
                    raise ValueError("候选不得改变对象用途")
            proposal = candidate.placement
            if proposal is not None:
                BazhaiRequest(
                    house=self.house, occupants=self.occupants, placements=[proposal]
                )
                before = current.get(candidate.object_id)
                if before is not None:
                    if any(
                        before.applies_to_occupant(o.subject_id)
                        != proposal.applies_to_occupant(o.subject_id)
                        for o in self.occupants
                    ):
                        raise ValueError("候选不得更换对象使用人范围")
                    for aspect in ("location", "facing"):
                        old = getattr(before, f"{aspect}_direction")
                        new = getattr(proposal, f"{aspect}_direction")
                        if (
                            old is not None
                            and new is not None
                            and old != new
                            and aspect not in candidate.changes
                        ):
                            raise ValueError("候选方向变化必须在 changes 中明确声明")
        if any(a.object_id not in objects for a in self.element_adjustments):
            raise ValueError("元素调节须引用已提供的布局对象")
        if (
            self.annual_remedy_ruleset_id is not None
            and "annual_stars" not in self.selected_methods
        ):
            raise ValueError("作者年度调节规则须显式选择 annual_stars")
        if len(set(self.selected_methods)) != len(self.selected_methods):
            raise ValueError("methods 不得重复")
        AnnualRequest(
            effective_year=self.effective_year,
            query_at=self.query_at,
            timezone_name=self.timezone_name,
            ruleset_id=self.annual_ruleset_id,
        )
        JinsuoRequest(features=self.features, ruleset_id=self.jinsuo_ruleset_id)
        if self.xuankong is not None and "xuankong_natal" not in self.selected_methods:
            raise ValueError("提供 xuankong 时须在 methods 中选择 xuankong_natal")
        if "xuankong_natal" in self.selected_methods:
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
