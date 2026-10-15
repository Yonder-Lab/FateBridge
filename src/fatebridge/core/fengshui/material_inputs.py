"""Observed attributes and an optional representation-use question, not natal needs."""

from typing import Literal, Optional

from pydantic import Field, StrictBool, field_validator, model_validator

from fatebridge.core.requests.base import _DeferredModel

Material = Literal[
    "wood",
    "processed_wood",
    "living_plant",
    "metal",
    "stone",
    "ceramic",
    "glass",
    "plastic",
    "textile",
    "water",
    "mixed",
    "unknown",
]
Shape = Literal[
    "columnar", "triangular", "square", "round", "wavy", "irregular", "unknown"
]
Colour = Literal[
    "green",
    "red",
    "brown",
    "beige",
    "yellow",
    "white",
    "gold",
    "blue",
    "black",
    "other",
    "mixed",
    "unknown",
]
ElementUse = Literal[
    "wood_remedy", "fire_remedy", "earth_remedy", "metal_remedy", "water_remedy"
]


class MaterialShapeFact(_DeferredModel):
    fact_id: str = Field(min_length=1, max_length=100)
    object_id: str = Field(min_length=1, max_length=100)
    material: Optional[Material] = None
    shape: Optional[Shape] = None
    colour: Optional[Colour] = None
    element_use: Optional[ElementUse] = Field(
        default=None,
        description="用户明确询问该物可否充当某元素代表物；不是所需/喜用元素，不证明任意宫位需要它或可立即摆放",
    )
    observation_basis: Literal["measured", "user_confirmed", "image_observed"]
    evidence: str = Field(min_length=1, max_length=1000)
    plant_alive: Optional[StrictBool] = Field(
        default=None,
        description="仅living_plant的存活状态；不得由绿色/照片外观补为确认存活",
    )

    @field_validator("fact_id", "object_id", "evidence")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("材质器形事实的ID与依据不能为空白")
        return value

    @model_validator(mode="after")
    def observed_attributes(self) -> "MaterialShapeFact":
        if self.material is None and self.shape is None and self.colour is None:
            raise ValueError(
                "材质器形事实至少提供一种实际属性；未知用unknown，不以目标代替观察"
            )
        if self.plant_alive is not None and self.material != "living_plant":
            raise ValueError("plant_alive只用于明确的living_plant")
        return self
