"""
Window Schemas
ADR-009: Pydantic models with strict validation
"""

from pydantic import BaseModel, ConfigDict, Field


class WindowResponse(BaseModel):
    """Schema for window response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    model_id: int
    floor_id: int | None = None
    floor_name: str | None = None
    ifc_guid: str
    name: str
    width: float
    height: float
    area: float
    u_value: float | None = None
    material: str = ""


class WindowListResponse(BaseModel):
    """Schema for window list response."""

    items: list[WindowResponse]
    total: int
    total_area: float = Field(description="Total window area in m²")


class WindowFilterParams(BaseModel):
    """Query parameters for filtering windows."""

    floor_id: int | None = None
    min_area: float | None = None
    max_area: float | None = None
    material: str | None = None
