"""Pydantic models for outline_mcp tool inputs and Outline API responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tool Input Models
# ---------------------------------------------------------------------------


class SearchKnowledgeInput(BaseModel):
    """Input for search_knowledge tool."""

    query: str = Field(..., description="Search query (min 3 chars)", min_length=3)
    collection_id: str | None = Field(
        default=None,
        description="Outline collection ID to restrict search. None = all collections.",
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results.")


class GetDocumentInput(BaseModel):
    """Input for get_document tool."""

    document_id: str = Field(..., description="Outline document UUID.")


class CreateRunbookInput(BaseModel):
    """Input for create_runbook tool."""

    title: str = Field(..., description="Runbook title.", min_length=3, max_length=250)
    content: str = Field(
        ...,
        description="Full Markdown content of the runbook.",
        min_length=10,
    )
    related_adrs: list[str] = Field(
        default_factory=list,
        description='List of related ADR IDs (e.g. ["ADR-132", "ADR-145"]).',
    )


class CreateConceptInput(BaseModel):
    """Input for create_concept tool."""

    title: str = Field(..., description="Concept title.", min_length=3, max_length=250)
    content: str = Field(
        ...,
        description="Full Markdown content of the architecture concept.",
        min_length=10,
    )
    related_adrs: list[str] = Field(
        default_factory=list,
        description='List of related ADR IDs (e.g. ["ADR-132", "ADR-145"]).',
    )


class CreateLessonLearnedInput(BaseModel):
    """Input for create_lesson_learned tool."""

    title: str = Field(..., description="Lesson Learned title.", min_length=3, max_length=250)
    content: str = Field(
        ...,
        description="Full Markdown content describing root cause, symptoms and fix.",
        min_length=10,
    )
    session_date: str = Field(
        ...,
        description="Date of the session in ISO format (YYYY-MM-DD).",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    related_adrs: list[str] = Field(default_factory=list)


class UpdateDocumentInput(BaseModel):
    """Input for update_document tool."""

    document_id: str = Field(..., description="Outline document UUID.")
    content: str = Field(..., description="New full Markdown content.", min_length=1)
    append: bool = Field(
        default=False,
        description=(
            "If True, append content to existing document instead of replacing. "
            "Use for adding new findings to an existing Runbook."
        ),
    )


class ListRecentInput(BaseModel):
    """Input for list_recent tool."""

    collection_id: str | None = Field(
        default=None,
        description="Outline collection ID. None = all collections.",
    )
    limit: int = Field(default=10, ge=1, le=25)
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


# ---------------------------------------------------------------------------
# Outline API Response Models (subset — only fields we need)
# ---------------------------------------------------------------------------


class OutlineSearchResult(BaseModel):
    """Single result from Outline documents.search API."""

    document_id: str
    title: str
    collection_id: str
    collection_name: str
    url: str
    context: str  # text snippet around the match
    updated_at: str


class OutlineDocument(BaseModel):
    """Full document from Outline documents.info API."""

    id: str
    title: str
    text: str  # Markdown content
    collection_id: str
    url: str
    created_at: str
    updated_at: str
    revision_count: int


class OutlineDocumentStub(BaseModel):
    """Minimal document representation for list results."""

    id: str
    title: str
    collection_id: str
    url: str
    updated_at: str
