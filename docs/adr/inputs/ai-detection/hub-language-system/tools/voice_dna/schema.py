"""
Hub Language Identity System — Voice DNA Schema (ADR-052)
Pydantic v2 validation for hub-voice-dna.yaml files.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ToneAttribute(str, Enum):
    PRECISE       = "precise"
    AUTHORITATIVE = "authoritative"
    DIRECT        = "direct"
    WARM          = "warm"
    EDITORIAL     = "editorial"
    PLAYFUL       = "playful"
    TECHNICAL     = "technical"
    ACADEMIC      = "academic"
    URGENT        = "urgent"
    MINIMAL       = "minimal"
    CONVERSATIONAL= "conversational"
    FORMAL        = "formal"
    BOLD          = "bold"


class SentenceLength(str, Enum):
    SHORT  = "short"   # avg < 10 words
    MEDIUM = "medium"  # avg 10–18 words
    LONG   = "long"    # avg > 18 words
    VARIED = "varied"  # mix of short and long


class LocalizedMicroCopy(BaseModel):
    """All micro-copy strings for one language."""

    # CTAs
    cta_primary:   str = Field(..., description="Primary action button text")
    cta_secondary: str = Field(..., description="Secondary / cancel button text")
    cta_save:      str
    cta_delete:    str
    cta_edit:      str
    cta_cancel:    str
    cta_confirm:   str
    cta_back:      str
    cta_next:      str
    cta_search:    str
    cta_filter:    str
    cta_export:    str
    cta_import:    str
    cta_create:    str
    cta_submit:    str

    # Status & Feedback
    status_loading:  str
    status_saving:   str
    status_success:  str
    status_error:    str
    status_empty:    str
    status_no_results: str

    # Toast Messages
    toast_saved:      str
    toast_deleted:     str
    toast_error:       str
    toast_updated:     str
    toast_created:     str

    # Error Messages
    error_generic:        str
    error_not_found:      str
    error_unauthorized:   str
    error_server:         str
    error_network:        str
    error_validation:     str
    error_timeout:        str

    # Form Labels & Hints
    label_required:   str = Field(..., description="Required field indicator text")
    label_optional:   str
    hint_search:      str
    hint_select:      str

    # Navigation
    nav_home:         str
    nav_back:         str
    nav_settings:     str
    nav_logout:       str
    nav_profile:      str

    # Confirmation Dialogs
    dialog_confirm_delete: str
    dialog_confirm_action: str
    dialog_unsaved_changes: str

    @field_validator("*", mode="before")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if isinstance(v, str) and not v.strip():
            raise ValueError("Micro-copy string must not be empty")
        return v


class MicroCopySet(BaseModel):
    de: LocalizedMicroCopy
    en: LocalizedMicroCopy


class MutationRecord(BaseModel):
    timestamp: datetime
    reason: str
    previous_score: float
    new_score: Optional[float] = None
    language: str = "all"
    changed_keys: list[str] = Field(default_factory=list)


class HubVoiceDNA(BaseModel):
    """
    Complete Hub Language / Voice Identity DNA.

    Single source of truth for a hub's textual personality.
    The pipeline.py generates locale/{de,en}/LC_MESSAGES/django.po from this.
    """

    hub: str = Field(..., pattern=r"^[a-z][a-z0-9-]*$")
    display_name: str

    # Voice personality
    tone: list[ToneAttribute] = Field(
        ..., min_length=2, max_length=5,
        description="2–5 tone attributes that define this hub's voice"
    )
    voice_description: str = Field(
        ..., min_length=20,
        description="Human-readable description of the hub's voice & style"
    )
    sentence_length: SentenceLength = SentenceLength.MEDIUM

    # Style rules
    use_formal_address: bool = Field(
        ...,
        description="True = 'Sie' (formal), False = 'du' (informal) — DE only"
    )
    use_active_voice:   bool = True
    use_imperatives:    bool = Field(
        ...,
        description="CTAs as imperative ('Starte') vs. noun ('Start')"
    )

    # Banned words / phrases (AI fingerprint signals)
    banned_words_de: list[str] = Field(
        default_factory=list,
        description="Words/phrases that MUST NOT appear in DE copy (AI fingerprints)"
    )
    banned_words_en: list[str] = Field(
        default_factory=list,
        description="Words/phrases that MUST NOT appear in EN copy (AI fingerprints)"
    )

    # Preferred vocabulary
    preferred_words_de: dict[str, str] = Field(
        default_factory=dict,
        description="Replacement map: {'nahtlos': 'direkt'} for DE"
    )
    preferred_words_en: dict[str, str] = Field(
        default_factory=dict,
        description="Replacement map: {'seamlessly': 'directly'} for EN"
    )

    # Micro-copy
    micro_copy: MicroCopySet

    # Audit metadata
    text_fingerprint_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0,
        description="AI text fingerprint score: 0=clearly human, 100=clearly AI"
    )
    last_audited:    Optional[datetime] = None
    last_mutated:    Optional[datetime] = None
    mutation_history: list[MutationRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def score_warning(self) -> "HubVoiceDNA":
        if self.text_fingerprint_score is not None and self.text_fingerprint_score > 35:
            import warnings
            warnings.warn(
                f"Hub '{self.hub}' has text fingerprint score "
                f"{self.text_fingerprint_score:.1f} > 35. "
                "Run 'python -m tools.voice_dna mutate' to evolve copy.",
                stacklevel=2,
            )
        return self

    @classmethod
    def from_yaml(cls, path: str) -> "HubVoiceDNA":
        import yaml
        from pathlib import Path
        with open(Path(path)) as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)

    def to_yaml(self, path: str) -> None:
        import yaml
        from pathlib import Path
        data = self.model_dump(mode="json", exclude_none=False)
        with open(Path(path), "w") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, width=120)
