"""Optional, sourced indoor-form observations and element adjustment targets."""

from typing import Literal, Optional

from pydantic import Field, StrictBool, model_validator

from fatebridge.core.requests.base import _DeferredModel


class FormObservation(_DeferredModel):
    object_id: str = Field(min_length=1, max_length=100)
    purpose: Literal["bed", "desk", "stove"]
    entrance_position: Optional[
        Literal[
            "front",
            "front_left",
            "front_right",
            "left",
            "right",
            "back",
            "back_left",
            "back_right",
        ]
    ] = Field(default=None, description="以实际使用者的正面为前；不是住宅分宫")
    entrance_visible: Optional[StrictBool] = Field(
        default=None,
        description="正常使用方向下实际可见入口；转身才能看见不能传 true。镜面补视野须另外确认。",
    )
    entrance_direct_line: Optional[StrictBool] = None
    solid_backing: Optional[StrictBool] = None
    backing_distance_m: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False, strict=True
    )
    view_via_mirror: Optional[StrictBool] = None
    observation_basis: Literal["measured", "user_confirmed", "image_observed"]
    evidence: str = Field(min_length=1, max_length=1000)
    source_ref: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def consistent_observation(self) -> "FormObservation":
        if not self.evidence.strip():
            raise ValueError("形态观察依据不能为空白")
        if all(
            v is None
            for v in (
                self.entrance_position,
                self.entrance_visible,
                self.entrance_direct_line,
                self.solid_backing,
                self.backing_distance_m,
            )
        ):
            raise ValueError("至少提供一项观察，未知值省略")
        if (
            self.observation_basis == "image_observed"
            and self.backing_distance_m is not None
        ):
            raise ValueError("照片不能代替距离测量或用户确认")
        if (
            self.entrance_position in {"back", "back_left", "back_right"}
            and self.entrance_visible is True
            and self.view_via_mirror is not True
        ):
            raise ValueError("入口在身后但正面可见需确认镜面视野或纠正使用者参考方向")
        if self.view_via_mirror is True and self.entrance_visible is not True:
            raise ValueError("镜面补视野须确认入口实际可见")
        return self


class ElementAdjustment(_DeferredModel):
    request_id: str = Field(min_length=1, max_length=100)
    object_id: str = Field(min_length=1, max_length=100)
    target_method: Literal["bazhai", "annual_stars", "xuankong_natal"]
    goal: Literal["drain", "support"] = Field(
        description="调用方明确的调节目标；不自动把命卦当缺五行"
    )
    subject_id: Optional[str] = None
    aspect: Optional[Literal["location", "facing"]] = None
    star_role: Optional[Literal["period", "mountain", "facing"]] = None
    evidence: str = Field(
        min_length=1, max_length=1000, description="本目标的规则判定或用户意图依据"
    )

    @model_validator(mode="after")
    def target_scope(self) -> "ElementAdjustment":
        if not self.evidence.strip():
            raise ValueError("调节目标依据不能为空白")
        if (self.target_method == "xuankong_natal") != (self.star_role is not None):
            raise ValueError("玄空目标须指定运/山/向星角色；其他方法不得指定玄空角色")
        if self.target_method != "bazhai" and self.subject_id is not None:
            raise ValueError("住户/宅卦筛选仅适用于八宅，不能覆盖年盘或玄空宅盘")
        if self.target_method == "bazhai" and (
            self.subject_id is None or self.aspect is None
        ):
            raise ValueError(
                "八宅调节须指定宅/人的 subject_id 和位置/朝向 aspect，不合并作用域"
            )
        if self.target_method != "bazhai" and self.aspect == "facing":
            raise ValueError("年盘/玄空调节只关联位置，不能用对象朝向代替落宫")
        return self
