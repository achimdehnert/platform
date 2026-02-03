"""
Model (IFC/DXF) Schemas
ADR-009: Pydantic models with strict validation
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelBase(BaseModel):
    """Base model schema."""

    name: str = Field(..., min_length=1, max_length=255)


class ModelCreate(ModelBase):
    """Schema for creating a model."""

    project_id: int


class ModelResponse(ModelBase):
    """Schema for model response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    file_path: str
    file_size_bytes: int
    file_size_mb: float
    source_format: str
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ModelUploadResponse(BaseModel):
    """Schema for model upload response."""

    id: int
    name: str
    file_path: str
    file_size_bytes: int
    parse_status: str
    message: str = "File uploaded successfully"


class ModelStatsResponse(BaseModel):
    """Schema for model statistics."""

    model_id: int
    floor_count: int
    room_count: int
    window_count: int
    door_count: int
    wall_count: int
    slab_count: int
    total_room_area: float
    total_window_area: float
