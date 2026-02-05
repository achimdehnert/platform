from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .element import CADElement, SourceFormat


class CADWarning(BaseModel):
    code: str
    message: str
    element_external_id: str | None = None


class CADParseStatistics(BaseModel):
    total_elements: int = 0
    elements_by_category: dict[str, int] = Field(default_factory=dict)
    warnings_count: int = 0

    parse_duration_ms: int = 0
    extract_duration_ms: int = 0

    file_size_bytes: int = 0
    memory_peak_mb: float | None = None

    ifc_schema: str | None = None
    ifc_application: str | None = None


class CADParseResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    file_hash: str
    source_format: SourceFormat
    parser_version: str
    profile_name: str | None = None
    profile_version: str | None = None

    elements: list[CADElement] = Field(default_factory=list)
    warnings: list[CADWarning] = Field(default_factory=list)
    statistics: CADParseStatistics = Field(default_factory=CADParseStatistics)
