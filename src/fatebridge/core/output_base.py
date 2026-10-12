"""Projection-compatible base for public business output contracts."""

from pydantic import BaseModel, ConfigDict


class PartialOutput(BaseModel):
    """Validate present facts without inserting defaults or removing extensions.

    Object facts reachable by arbitrary field projection must be optional.
    Array items and receipts preserved whole may retain required facts, since
    projection cannot remove their siblings. Service results are validated but
    never serialized through these models.
    """

    model_config = ConfigDict(extra="allow", strict=True, defer_build=True)
