"""Pydantic v2 models for d.velop DMS API responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HalLink(BaseModel):
    """JSON-HAL _links entry."""

    href: str
    templated: bool = False


class Repository(BaseModel):
    """d.velop DMS repository."""

    id: str
    name: str
    href: str = ""


class Category(BaseModel):
    """d.velop DMS document category."""

    key: str
    display_name: str = ""


class DmsProperty(BaseModel):
    """A single property on a DMS object."""

    key: str
    value: str
    display_name: str = ""


class BlobRef(BaseModel):
    """Reference to an uploaded blob (Step 1 of 2-step upload)."""

    blob_id: str
    location_uri: str
    content_type: str = "application/pdf"


class DmsObject(BaseModel):
    """d.velop DMS document object (Step 2 result)."""

    id: str
    location_uri: str
    repo_id: str = ""
    category: str = ""
    properties: list[DmsProperty] = Field(default_factory=list)
    created_at: datetime | None = None


class SearchResult(BaseModel):
    """Single search hit."""

    id: str
    title: str = ""
    category: str = ""
    location_uri: str = ""
    properties: list[DmsProperty] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Paginated search response."""

    items: list[SearchResult] = Field(default_factory=list)
    total: int = 0
