"""
Hub Visual Identity System — DNA Schema (ADR-051)
Pydantic v2 validation models for hub-dna.yaml files.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class AsymmetryLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GridVariant(str, Enum):
    STANDARD = "standard"
    BENTO = "bento"
    EDITORIAL = "editorial"
    DASHBOARD = "dashboard"
    MAGAZINE = "magazine"


class Palette(BaseModel):
    primary: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    primary_hover: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    accent: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    surface: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    surface_alt: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    foreground: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    muted: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    border: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    danger: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    success: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")
    warning: str = Field(..., pattern=r"^#[0-9a-fA-F]{6}$")

    @field_validator("primary", "primary_hover", "accent", "surface", "surface_alt",
                     "foreground", "muted", "border", "danger", "success", "warning",
                     mode="before")
    @classmethod
    def normalize_hex(cls, v: str) -> str:
        return v.upper() if v else v


class Typography(BaseModel):
    display_font: str
    body_font: str
    mono_font: str
    display_weight: str = "700"
    body_weight: str = "400,500,600"
    font_source: str  # Bunny Fonts URL (DSGVO-konform)

    @field_validator("font_source")
    @classmethod
    def must_use_bunny_fonts(cls, v: str) -> str:
        """Enforce DSGVO-compliant font source — no Google Fonts."""
        if "fonts.google.com" in v or "fonts.googleapis.com" in v:
            raise ValueError(
                "Google Fonts sind DSGVO-problematisch. "
                "Verwende fonts.bunny.net stattdessen."
            )
        return v


class Layout(BaseModel):
    radius_sm: str = "2px"
    radius_md: str = "4px"
    radius_lg: str = "8px"
    radius_xl: str = "16px"
    asymmetry_level: AsymmetryLevel = AsymmetryLevel.MEDIUM
    grid_variant: GridVariant = GridVariant.STANDARD

    @field_validator("radius_sm", "radius_md", "radius_lg", "radius_xl")
    @classmethod
    def validate_css_length(cls, v: str) -> str:
        if not v.endswith(("px", "rem", "%")):
            raise ValueError(f"Invalid CSS length: {v}")
        return v


class Motion(BaseModel):
    duration_fast: str = "100ms"
    duration_normal: str = "200ms"
    easing_standard: str = "cubic-bezier(0.4, 0, 0.2, 1)"
    easing_spring: str = "cubic-bezier(0.34, 1.4, 0.64, 1)"
    hover_lift: str = "-2px"

    @field_validator("duration_fast", "duration_normal")
    @classmethod
    def validate_duration(cls, v: str) -> str:
        if not v.endswith("ms") and not v.endswith("s"):
            raise ValueError(f"Invalid CSS duration: {v}")
        return v


class MutationRecord(BaseModel):
    timestamp: datetime
    reason: str
    previous_score: float
    new_score: Optional[float] = None
    changed_fields: list[str] = Field(default_factory=list)


class HubDNA(BaseModel):
    """
    Complete Hub Visual Identity DNA.

    This is the single source of truth for a hub's visual personality.
    The pipeline.py generates pui-tokens-{hub}.css from this schema.
    """

    hub: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str
    personality: str = Field(..., min_length=10, description="Human-readable personality description")
    aesthetic: str = Field(..., description="One-word aesthetic archetype e.g. 'institutional-minimalism'")

    palette: Palette
    typography: Typography
    layout: Layout
    motion: Motion

    # Audit metadata — populated by audit.py, not manually
    fingerprint_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="AI-fingerprint score: 0=clearly human, 100=clearly AI. Updated by audit.py."
    )
    fingerprint_details: Optional[dict[str, float]] = None
    last_audited: Optional[datetime] = None
    last_mutated: Optional[datetime] = None
    mutation_history: list[MutationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def score_threshold_warning(self) -> "HubDNA":
        if self.fingerprint_score is not None and self.fingerprint_score > 60:
            import warnings
            warnings.warn(
                f"Hub '{self.hub}' has AI fingerprint score {self.fingerprint_score:.1f} > 60. "
                "Run 'python -m tools.design_dna mutate' to generate a new DNA variant.",
                stacklevel=2,
            )
        return self

    @classmethod
    def from_yaml(cls, path: str) -> "HubDNA":
        """Load and validate a hub DNA from YAML file."""
        import yaml
        from pathlib import Path

        with open(Path(path)) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def to_yaml(self, path: str) -> None:
        """Persist DNA back to YAML (used after mutation)."""
        import yaml
        from pathlib import Path

        data = self.model_dump(mode="json", exclude_none=False)
        with open(Path(path), "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
