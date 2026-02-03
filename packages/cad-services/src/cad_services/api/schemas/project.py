"""
Project Schemas
ADR-009: Pydantic models with strict validation
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default="", max_length=2000)


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    pass


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class ProjectResponse(ProjectBase):
    """Schema for project response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_count: int = 0


class ProjectListResponse(BaseModel):
    """Schema for project list response."""

    items: list[ProjectResponse]
    total: int
    page: int = 1
    page_size: int = 20
