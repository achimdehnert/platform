"""
Room Schemas
ADR-009: Pydantic models with strict validation
"""

from pydantic import BaseModel, ConfigDict, Field


class RoomResponse(BaseModel):
    """Schema for room response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    floor_id: int | None = None
    floor_name: str | None = None
    ifc_guid: str
    number: str
    name: str
    area: float
    height: float
    volume: float
    perimeter: float
    usage_category_code: str | None = None
    usage_category_name: str | None = None
    woflv_area: float = 0


class RoomListResponse(BaseModel):
    """Schema for room list response."""

    items: list[RoomResponse]
    total: int
    total_area: float = Field(description="Total room area in m²")
    total_volume: float = Field(description="Total room volume in m³")


class RoomFilterParams(BaseModel):
    """Query parameters for filtering rooms."""

    floor_id: int | None = None
    usage_category_id: int | None = None
    min_area: float | None = None
    max_area: float | None = None
