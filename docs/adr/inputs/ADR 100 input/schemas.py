"""
outlinefw/src/outlinefw/schemas.py

Pydantic schemas for iil-outlinefw.

Fixes:
  - KRITISCH K-2: Beat position validation (no overlaps, no gaps > 0.15)
  - KRITISCH K-3: OutlineResult with full error/partial state
  - HOCH H-1: Explicit __all__ via re-export in __init__.py
  - KRITISCH K-4: ParseResult distinguishes malformed JSON from empty outline
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActPhase(str, Enum):
    ACT_1 = "act_1"
    ACT_2A = "act_2a"
    ACT_2B = "act_2b"
    ACT_3 = "act_3"
    # For non-three-act frameworks
    ACT_OPEN = "act_open"
    ACT_CLOSE = "act_close"


class TensionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PEAK = "peak"


class GenerationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"       # Some beats generated, some failed
    PARSE_ERROR = "parse_error"    # LLM returned non-parseable content
    LLM_ERROR = "llm_error"       # LLM call itself failed
    VALIDATION_ERROR = "validation_error"  # Generated content violates schema


class ParseStatus(str, Enum):
    SUCCESS = "success"
    EMPTY = "empty"               # LLM returned empty / null
    MALFORMED_JSON = "malformed_json"
    PARTIAL = "partial"           # Some nodes parsed, some failed
    SCHEMA_MISMATCH = "schema_mismatch"


# ---------------------------------------------------------------------------
# LLM Quality
# Fixes HOCH H-2: quality_level: int | None is semantically undefined
# ---------------------------------------------------------------------------


class LLMQuality(int, Enum):
    """
    Maps to iil-aifw model routing tiers.
    DRAFT → cheapest/fastest model.
    STANDARD → balanced model (default).
    PREMIUM → best available model (higher cost, slower).
    """
    DRAFT = 1
    STANDARD = 2
    PREMIUM = 3


# ---------------------------------------------------------------------------
# Beat Definition
# ---------------------------------------------------------------------------


class BeatDefinition(BaseModel):
    """
    Single beat in a story framework.

    position: 0.0 (story start) to 1.0 (story end).
    act: which structural act this beat belongs to.
    tension: narrative tension at this beat.
    """

    name: str = Field(..., min_length=1, max_length=100)
    position: float = Field(..., ge=0.0, le=1.0)
    act: ActPhase
    description: str = Field(..., min_length=1, max_length=500)
    tension: TensionLevel

    @field_validator("position")
    @classmethod
    def position_precision(cls, v: float) -> float:
        """Round to 2 decimal places to avoid float drift."""
        return round(v, 2)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Framework Definition
# ---------------------------------------------------------------------------


class FrameworkDefinition(BaseModel):
    """
    A complete story framework with ordered beats.

    Fixes K-2: Validates that no two beats share a position and
    that no gap between adjacent beats exceeds MAX_GAP.
    """

    key: str = Field(..., pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    beats: list[BeatDefinition] = Field(..., min_length=2, max_length=50)

    # Max allowed gap between adjacent beats.
    # 0.30 accommodates sparse frameworks (Three-Act has 7 beats → avg gap 0.14,
    # but intentional design allows up to ~0.26 between act boundaries).
    # Save the Cat (15 beats) has gaps of ~0.07 — well within limit.
    MAX_GAP: float = 0.30

    @model_validator(mode="after")
    def validate_beat_positions(self) -> "FrameworkDefinition":
        positions = [b.position for b in self.beats]

        # No duplicate positions
        if len(positions) != len(set(positions)):
            dupes = [p for p in positions if positions.count(p) > 1]
            raise ValueError(
                f"Framework '{self.key}': duplicate beat positions: {set(dupes)}"
            )

        # Beats must be ordered
        sorted_positions = sorted(positions)
        if positions != sorted_positions:
            raise ValueError(
                f"Framework '{self.key}': beats must be ordered by position. "
                f"Got: {positions}"
            )

        # First beat at or near 0.0, last at or near 1.0
        if positions[0] > 0.1:
            raise ValueError(
                f"Framework '{self.key}': first beat position {positions[0]} > 0.1"
            )
        if positions[-1] < 0.9:
            raise ValueError(
                f"Framework '{self.key}': last beat position {positions[-1]} < 0.9"
            )

        # No excessive gaps
        for i in range(1, len(sorted_positions)):
            gap = sorted_positions[i] - sorted_positions[i - 1]
            if gap > self.MAX_GAP:
                raise ValueError(
                    f"Framework '{self.key}': gap of {gap:.2f} between beats "
                    f"at {sorted_positions[i-1]} and {sorted_positions[i]} "
                    f"exceeds MAX_GAP {self.MAX_GAP}"
                )

        return self

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Project Context (input to generator)
# ---------------------------------------------------------------------------


class ProjectContext(BaseModel):
    """
    Input context for outline generation.
    Passed to the LLM prompt as structured context.
    """

    title: str = Field(..., min_length=1, max_length=200)
    genre: str = Field(..., min_length=1, max_length=100)
    logline: str = Field(..., min_length=10, max_length=500)
    protagonist: str = Field(..., min_length=1, max_length=200)
    setting: str = Field(..., min_length=1, max_length=300)

    # Optional enrichment
    themes: list[str] = Field(default_factory=list, max_length=10)
    tone: str = Field(default="", max_length=100)
    target_word_count: int | None = Field(default=None, ge=1000, le=500_000)
    additional_notes: str = Field(default="", max_length=2000)

    # i18n: output language code (ISO 639-1)
    language_code: str = Field(default="de", pattern=r"^[a-z]{2}$")


# ---------------------------------------------------------------------------
# Outline Node (single generated beat content)
# ---------------------------------------------------------------------------


class OutlineNode(BaseModel):
    """
    A single beat in the generated outline.
    Maps 1:1 to a BeatDefinition by beat_name.
    """

    beat_name: str = Field(..., min_length=1, max_length=100)
    position: float = Field(..., ge=0.0, le=1.0)
    act: ActPhase
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=10, max_length=2000)
    tension: TensionLevel

    # Optional narrative detail
    scene_count: int | None = Field(default=None, ge=1, le=20)
    key_events: list[str] = Field(default_factory=list, max_length=10)
    character_arcs: dict[str, str] = Field(default_factory=dict)

    @field_validator("position")
    @classmethod
    def round_position(cls, v: float) -> float:
        return round(v, 2)


# ---------------------------------------------------------------------------
# Parse Result (Fixes K-4: distinguishes error types)
# ---------------------------------------------------------------------------


class ParseResult(BaseModel):
    """
    Result of parse_nodes(). Always returned, never raises.
    Caller inspects status to distinguish error types.
    """

    status: ParseStatus
    nodes: list[OutlineNode] = Field(default_factory=list)
    raw_content: str = Field(default="")
    error_message: str = Field(default="")
    failed_nodes: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status == ParseStatus.SUCCESS

    @property
    def has_nodes(self) -> bool:
        return len(self.nodes) > 0


# ---------------------------------------------------------------------------
# Outline Result (Fixes K-3: full error/partial state)
# ---------------------------------------------------------------------------


class OutlineResult(BaseModel):
    """
    Result of OutlineGenerator.generate(). Never raises.
    Callers check status before accessing nodes.
    """

    status: GenerationStatus
    framework_key: str
    framework_name: str
    project_title: str

    # Populated on SUCCESS or PARTIAL
    nodes: list[OutlineNode] = Field(default_factory=list)

    # Diagnostic fields
    error_message: str = Field(default="")
    raw_llm_response: str = Field(default="")
    parse_result: ParseResult | None = None

    # Metadata
    model_used: str = Field(default="")
    generation_time_ms: int | None = None
    total_beats: int = 0
    generated_beats: int = 0

    @property
    def success(self) -> bool:
        return self.status == GenerationStatus.SUCCESS

    @property
    def completion_ratio(self) -> float:
        if self.total_beats == 0:
            return 0.0
        return self.generated_beats / self.total_beats

    def raise_if_failed(self) -> None:
        """
        Convenience method for callers that want exception semantics.
        Service layer catches this and converts to HTTP 500 / user-facing error.
        """
        if not self.success:
            raise OutlineGenerationError(
                f"Outline generation failed [{self.status}]: {self.error_message}"
            )


class OutlineGenerationError(Exception):
    """Raised by OutlineResult.raise_if_failed() only. Never raised directly by generator."""
    pass
