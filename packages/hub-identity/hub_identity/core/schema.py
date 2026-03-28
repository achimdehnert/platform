"""
Unified Hub DNA Schema (Design #4: Inheritance + #6: Immutable).

Single YAML per hub — visual + voice in one file.
Supports _base.yaml inheritance via 'extends' field.
No mutation_history in YAML — Git is the audit trail.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from hub_identity.core.merge import deep_merge


# ── Enums ───────────────────────────────────────────────────────


class ToneAttribute(str, Enum):
    PRECISE = "precise"
    TECHNICAL = "technical"
    DIRECT = "direct"
    MINIMAL = "minimal"
    WARM = "warm"
    PROFESSIONAL = "professional"
    PLAYFUL = "playful"
    FORMAL = "formal"
    CASUAL = "casual"
    AUTHORITATIVE = "authoritative"


class SentenceLength(str, Enum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class GridVariant(str, Enum):
    STANDARD = "standard"
    BENTO = "bento"
    EDITORIAL = "editorial"
    DASHBOARD = "dashboard"


# ── Visual DNA (ADR-051) ───────────────────────────────────────


class Palette(BaseModel):
    primary: str = "#0f172a"
    primary_foreground: str = "#ffffff"
    secondary: str = "#f1f5f9"
    secondary_foreground: str = "#1e293b"
    accent: str = "#3b82f6"
    accent_foreground: str = "#ffffff"
    background: str = "#fafaf9"
    foreground: str = "#1c1917"
    muted: str = "#f5f5f4"
    muted_foreground: str = "#78716c"
    destructive: str = "#ef4444"
    border: str = "#e7e5e4"
    ring: str = "#3b82f6"


class Typography(BaseModel):
    display: str = "Figtree"
    body: str = "Figtree"
    mono: str = "JetBrains Mono"
    font_source: str = "https://fonts.bunny.net"
    base_size: str = "16px"
    scale_ratio: float = 1.25


class Layout(BaseModel):
    border_radius: int = 10
    spacing_unit: int = 4
    grid_variant: GridVariant = GridVariant.STANDARD
    container_max_width: str = "1280px"


class Motion(BaseModel):
    duration_fast: str = "120ms"
    duration_normal: str = "250ms"
    duration_slow: str = "500ms"
    easing: str = "cubic-bezier(0.22, 1, 0.36, 1)"


class Shadow(BaseModel):
    sm: str = "0 1px 2px rgba(0,0,0,0.06)"
    md: str = "0 4px 6px rgba(0,0,0,0.07)"
    lg: str = "0 10px 15px rgba(0,0,0,0.1)"
    accent: str = ""


class VisualDNA(BaseModel):
    palette: Palette = Field(default_factory=Palette)
    typography: Typography = Field(default_factory=Typography)
    layout: Layout = Field(default_factory=Layout)
    motion: Motion = Field(default_factory=Motion)
    shadow: Shadow = Field(default_factory=Shadow)


# ── Voice DNA (ADR-052) ────────────────────────────────────────


class LocalizedMicroCopy(BaseModel):
    cta_primary: str = ""
    cta_secondary: str = ""
    cta_danger: str = ""
    nav_back: str = ""
    nav_next: str = ""
    status_loading: str = ""
    status_success: str = ""
    status_error: str = ""
    status_empty: str = ""
    error_generic: str = ""
    error_validation: str = ""
    error_not_found: str = ""
    error_permission: str = ""
    dialog_confirm_title: str = ""
    dialog_confirm_body: str = ""
    dialog_confirm_yes: str = ""
    dialog_confirm_no: str = ""
    toast_saved: str = ""
    toast_deleted: str = ""
    toast_error: str = ""


class MicroCopy(BaseModel):
    de: LocalizedMicroCopy = Field(
        default_factory=LocalizedMicroCopy,
    )
    en: LocalizedMicroCopy = Field(
        default_factory=LocalizedMicroCopy,
    )


class VoiceDNA(BaseModel):
    tone: list[ToneAttribute] = Field(default_factory=list)
    voice_description: str = ""
    sentence_length: SentenceLength = SentenceLength.MEDIUM
    use_formal_address: bool = True
    use_active_voice: bool = True
    use_imperatives: bool = False
    banned_words_de: list[str] = Field(default_factory=list)
    banned_words_en: list[str] = Field(default_factory=list)
    preferred_words_de: dict[str, str] = Field(
        default_factory=dict,
    )
    preferred_words_en: dict[str, str] = Field(
        default_factory=dict,
    )
    micro_copy: MicroCopy = Field(default_factory=MicroCopy)


# ── Unified Hub DNA ────────────────────────────────────────────


class HubDNA(BaseModel):
    """
    Single source of truth for a hub's identity.

    Combines visual (ADR-051) and voice (ADR-052) in one model.
    Immutable: no mutation_history — Git is the audit trail.
    Supports inheritance via 'extends' field in YAML.
    """

    hub: str
    display_name: str = ""
    personality: str = ""

    visual: VisualDNA = Field(default_factory=VisualDNA)
    voice: VoiceDNA = Field(default_factory=VoiceDNA)

    # Schema.org / SEO metadata
    schema_org_type: str = "SoftwareApplication"
    og_image: str = ""

    model_config = {"extra": "forbid"}

    # ── I/O ─────────────────────────────────────────────────

    @classmethod
    def from_yaml(
        cls,
        path: str | Path,
        base_dir: str | Path | None = None,
    ) -> HubDNA:
        """
        Load HubDNA from YAML with inheritance support.

        If the YAML contains 'extends: _base', load _base.yaml
        from the same directory and deep-merge.
        """
        path = Path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))

        if "extends" in raw:
            base_path = (
                Path(base_dir) if base_dir
                else path.parent
            ) / f"{raw['extends']}.yaml"
            if not base_path.exists():
                msg = (
                    f"Base DNA '{raw['extends']}' not found "
                    f"at {base_path}"
                )
                raise FileNotFoundError(msg)
            base_raw = yaml.safe_load(
                base_path.read_text(encoding="utf-8"),
            )
            raw = deep_merge(base_raw, raw)

        return cls.model_validate(raw)

    def to_yaml(self, path: str | Path) -> None:
        """Write HubDNA to YAML (without defaults)."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(
            mode="json",
            exclude_defaults=True,
        )
        path.write_text(
            yaml.dump(
                data,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def load_all(
        cls,
        dna_dir: str | Path,
    ) -> list[HubDNA]:
        """Load all hub DNAs from a directory."""
        dna_dir = Path(dna_dir)
        hubs = []
        for path in sorted(dna_dir.glob("*.yaml")):
            if path.name.startswith("_"):
                continue  # Skip base files
            hubs.append(cls.from_yaml(path))
        return hubs

    # ── Helpers ─────────────────────────────────────────────

    def get_css_filename(self) -> str:
        return f"pui-tokens-{self.hub}.css"

    def get_po_dir(self, lang: str) -> str:
        return f"locale/{lang}/LC_MESSAGES"
