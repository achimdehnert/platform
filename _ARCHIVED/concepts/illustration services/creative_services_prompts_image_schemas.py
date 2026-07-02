"""
Schema-Erweiterung: Image Generation für Prompt-Template-System
================================================================

Package: creative_services.prompts.schemas_image
Erweitert: creative_services.prompts.schemas

Diese Module erweitert das bestehende Prompt-Template-System um
Image-Generation-Fähigkeiten (Stable Diffusion, etc.).

Architektur-Prinzipien (gemäß PLATFORM_ARCHITECTURE_MASTER.md):
- Spec vs. Derived: Nur Fakten persistieren, Berechnetes zur Laufzeit
- Zero Breaking Changes: Bestehende Schemas bleiben kompatibel
- Database-First: Schemas können direkt in DB gespeichert werden
- Fail Loud: Strenge Validierung, keine stillen Defaults

Version: 1.0
Datum: 2026-01-29
Status: Implementation Ready
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Optional, Union
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# =============================================================================
# SECTION 1: Basis-Enums und Typen
# =============================================================================

class OutputFormat(str, Enum):
    """
    Output-Format für Prompt-Templates.
    
    Erweitert um IMAGE für Bildgenerierung.
    """
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    STRUCTURED = "structured"
    IMAGE = "image"  # 🆕 NEU für Bildgenerierung


class TemplateType(str, Enum):
    """
    Typ des Templates.
    
    Unterscheidet zwischen vollständigen Templates und Partials.
    """
    STANDARD = "standard"           # Normales Prompt-Template
    PARTIAL = "partial"             # Wiederverwendbarer Block
    STYLE_PARTIAL = "style_partial" # 🆕 Spezialisiert für Illustration-Styles
    CHAIN = "chain"                 # Multi-Step Template


class ImageFunction(str, Enum):
    """
    Funktion/Zweck eines Bildes im Buchkontext.
    
    Aus dem Buchillustrations-Konzept übernommen.
    """
    NARRATIVE = "erzählend"         # Erzählt/zeigt Handlung
    EXPLANATORY = "erklärend"       # Erklärt Konzepte
    ATMOSPHERIC = "atmosphärisch"   # Stimmung/Ambiente
    ICONIC = "ikonisch"             # Symbolisch/repräsentativ


class LightingType(str, Enum):
    """Beleuchtungstypen für Illustrationen."""
    SOFT = "soft"
    DIFFUSE = "diffuse"
    DRAMATIC = "dramatic"           # Oft in forbidden-Liste
    DIRECTIONAL = "directional"
    AMBIENT = "ambient"
    GLOBAL = "global"


class ContrastLevel(str, Enum):
    """Kontrastlevel für Illustrationen."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    DRAMATIC = "dramatic"           # Oft in forbidden-Liste


class CompositionType(str, Enum):
    """Kompositionstypen."""
    CENTERED = "centered"
    ASYMMETRIC = "asymmetric"
    RULE_OF_THIRDS = "rule_of_thirds"
    DIAGONAL = "diagonal"
    FRAMED = "framed"


class PerspectiveType(str, Enum):
    """Perspektiven für Illustrationen."""
    EYE_LEVEL = "eye_level"
    SLIGHTLY_ELEVATED = "slightly_elevated"
    BIRDS_EYE = "birds_eye"
    WORMS_EYE = "worms_eye"
    ISOMETRIC = "isometric"


class StyleStatus(str, Enum):
    """Status eines Style-Manifests."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


# =============================================================================
# SECTION 2: Farbpaletten-Schemas
# =============================================================================

# Hex-Color Regex Pattern
HEX_COLOR_PATTERN = r'^#[0-9A-Fa-f]{6}$'


class ColorRole(str, Enum):
    """Rolle einer Farbe in der Palette."""
    PRIMARY = "primary"
    ACCENT = "accent"
    FORBIDDEN = "forbidden"
    BACKGROUND = "background"
    HIGHLIGHT = "highlight"


class ColorSpec(BaseModel):
    """
    Spezifikation einer einzelnen Farbe.
    
    Enthält Hex-Code, Name und semantische Bedeutung.
    
    Example:
        ColorSpec(
            hex_code="#5B6E7A",
            name="dusty_blue",
            role=ColorRole.PRIMARY,
            semantic="Ruhe, Weite, Technologie"
        )
    """
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,  # Immutable nach Erstellung
    )
    
    hex_code: str = Field(
        ...,
        pattern=HEX_COLOR_PATTERN,
        description="Hex-Farbcode, z.B. '#5B6E7A'",
        examples=["#5B6E7A", "#8A8F94", "#E6E1D8"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Interner Name der Farbe (snake_case empfohlen)",
        examples=["dusty_blue", "warm_offwhite", "rust_orange"],
    )
    role: ColorRole = Field(
        ...,
        description="Rolle der Farbe in der Palette",
    )
    semantic: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Semantische Bedeutung der Farbe im Kontext",
        examples=["Technologie, Zukunft", "Verfall, Vergangenheit"],
    )
    usage_hint: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Hinweis zur Verwendung",
        examples=["Sparsam für technische Elemente", "Nur als Akzent"],
    )
    
    @field_validator('hex_code')
    @classmethod
    def normalize_hex_code(cls, v: str) -> str:
        """Normalisiert Hex-Code zu Großbuchstaben."""
        return v.upper()
    
    @field_validator('name')
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Stellt sicher, dass Name snake_case oder kebab-case ist."""
        if not re.match(r'^[a-z][a-z0-9_-]*$', v):
            raise ValueError(
                f"Name '{v}' muss mit Kleinbuchstabe beginnen und "
                "nur a-z, 0-9, _, - enthalten"
            )
        return v


class ForbiddenColorSpec(BaseModel):
    """
    Spezifikation einer verbotenen Farbe oder eines Farbmusters.
    
    Kann entweder ein konkreter Hex-Code oder ein Pattern sein.
    
    Example:
        ForbiddenColorSpec(pattern="neon", reason="Zu grell für Buchillustration")
        ForbiddenColorSpec(hex_code="#000000", reason="Kein reines Schwarz")
    """
    model_config = ConfigDict(extra="forbid")
    
    hex_code: Optional[str] = Field(
        default=None,
        pattern=HEX_COLOR_PATTERN,
        description="Konkreter verbotener Hex-Code",
    )
    pattern: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Beschreibendes Pattern (z.B. 'neon', 'saturated RGB')",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Begründung warum diese Farbe/Pattern verboten ist",
    )
    
    @model_validator(mode='after')
    def validate_has_target(self) -> 'ForbiddenColorSpec':
        """Stellt sicher, dass entweder hex_code oder pattern gesetzt ist."""
        if not self.hex_code and not self.pattern:
            raise ValueError("Entweder hex_code oder pattern muss gesetzt sein")
        return self


class ColorPalette(BaseModel):
    """
    Vollständige Farbpalette für einen Illustration-Stil.
    
    Strukturiert in Primary, Accent und Forbidden.
    
    Example:
        ColorPalette(
            primary=[
                ColorSpec(hex_code="#5B6E7A", name="dusty_blue", role=ColorRole.PRIMARY),
            ],
            accent=[
                ColorSpec(hex_code="#6FAFB2", name="cool_cyan", role=ColorRole.ACCENT),
            ],
            forbidden=[
                ForbiddenColorSpec(pattern="neon", reason="Zu grell"),
            ]
        )
    """
    model_config = ConfigDict(extra="forbid")
    
    primary: list[ColorSpec] = Field(
        default_factory=list,
        min_length=1,
        max_length=5,
        description="Primärfarben (dominant im Bild)",
    )
    accent: list[ColorSpec] = Field(
        default_factory=list,
        max_length=5,
        description="Akzentfarben (sparsam einsetzen)",
    )
    forbidden: list[ForbiddenColorSpec] = Field(
        default_factory=list,
        description="Verbotene Farben/Patterns",
    )
    
    @field_validator('primary')
    @classmethod
    def validate_primary_roles(cls, v: list[ColorSpec]) -> list[ColorSpec]:
        """Stellt sicher, dass Primary-Farben auch die Rolle PRIMARY haben."""
        for color in v:
            if color.role != ColorRole.PRIMARY:
                raise ValueError(
                    f"Farbe '{color.name}' in primary-Liste muss role=PRIMARY haben"
                )
        return v
    
    @field_validator('accent')
    @classmethod
    def validate_accent_roles(cls, v: list[ColorSpec]) -> list[ColorSpec]:
        """Stellt sicher, dass Accent-Farben auch die Rolle ACCENT haben."""
        for color in v:
            if color.role != ColorRole.ACCENT:
                raise ValueError(
                    f"Farbe '{color.name}' in accent-Liste muss role=ACCENT haben"
                )
        return v
    
    def get_all_hex_codes(self) -> list[str]:
        """Gibt alle erlaubten Hex-Codes zurück."""
        return [c.hex_code for c in self.primary + self.accent]
    
    def get_forbidden_patterns(self) -> list[str]:
        """Gibt alle verbotenen Patterns zurück (für Negative Prompt)."""
        patterns = []
        for f in self.forbidden:
            if f.pattern:
                patterns.append(f.pattern)
            if f.hex_code:
                patterns.append(f.hex_code)
        return patterns


# =============================================================================
# SECTION 3: Stable Diffusion Parameter
# =============================================================================

class SDSampler(str, Enum):
    """
    Unterstützte Stable Diffusion Sampler.
    
    Nur die bewährtesten für konsistente Ergebnisse.
    """
    DPM_PP_2M_KARRAS = "DPM++ 2M Karras"
    DPM_PP_SDE_KARRAS = "DPM++ SDE Karras"
    EULER_A = "Euler a"
    EULER = "Euler"
    DDIM = "DDIM"
    LMS = "LMS"
    HEUN = "Heun"


class SDParameters(BaseModel):
    """
    Stable Diffusion technische Parameter.
    
    Diese Werte sind FIXWERTE für einen Stil und sollten nicht
    pro Bild geändert werden (außer seed).
    
    Folgt dem Platform-Prinzip: Technische Fixwerte als Spec,
    nicht zur Laufzeit berechnet.
    
    Example:
        SDParameters(
            base_model="sd_xl_base_1.0",
            sampler=SDSampler.DPM_PP_2M_KARRAS,
            steps=30,
            cfg_scale=5.5,
            width=768,
            height=1024,
            lora_key="scifi_book_style_v1",
            lora_strength=1.0,
        )
    """
    model_config = ConfigDict(extra="forbid")
    
    # Modell-Konfiguration
    base_model: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Basis-Modell (z.B. 'sd_xl_base_1.0', 'realistic_vision_v5')",
        examples=["sd_xl_base_1.0", "realistic_vision_v5.1", "dreamshaper_8"],
    )
    vae: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional: Spezifisches VAE (wenn nicht Model-Default)",
        examples=["sdxl_vae", "vae-ft-mse-840000-ema-pruned"],
    )
    
    # Sampler-Konfiguration
    sampler: SDSampler = Field(
        default=SDSampler.DPM_PP_2M_KARRAS,
        description="Sampling-Algorithmus",
    )
    steps: int = Field(
        default=30,
        ge=10,
        le=100,
        description="Anzahl Sampling-Steps (mehr = detaillierter, aber langsamer)",
    )
    cfg_scale: float = Field(
        default=7.0,
        ge=1.0,
        le=20.0,
        description="Classifier-Free Guidance Scale (höher = prompt-treuer)",
    )
    
    # Auflösung
    width: int = Field(
        default=768,
        ge=512,
        le=2048,
        multiple_of=64,
        description="Bildbreite in Pixeln (muss durch 64 teilbar sein)",
    )
    height: int = Field(
        default=1024,
        ge=512,
        le=2048,
        multiple_of=64,
        description="Bildhöhe in Pixeln (muss durch 64 teilbar sein)",
    )
    
    # LoRA-Konfiguration
    lora_key: Optional[str] = Field(
        default=None,
        max_length=200,
        pattern=r'^[a-z][a-z0-9_-]*$',
        description="LoRA-Identifier (ohne Dateierweiterung)",
        examples=["scifi_book_style_v1", "watercolor_ink_v2"],
    )
    lora_strength: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="LoRA-Stärke (0.0 = aus, 1.0 = normal, >1.0 = verstärkt)",
    )
    
    # Reproduzierbarkeit
    seed: Optional[int] = Field(
        default=None,
        ge=-1,
        description="Seed für Reproduzierbarkeit (-1 oder None = random)",
    )
    
    # High-Res Fix (optional)
    enable_hr: bool = Field(
        default=False,
        description="High-Resolution Fix aktivieren",
    )
    hr_scale: float = Field(
        default=1.5,
        ge=1.0,
        le=4.0,
        description="Upscale-Faktor für HR Fix",
    )
    hr_upscaler: Optional[str] = Field(
        default="Latent",
        description="Upscaler für HR Fix",
    )
    denoising_strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Denoising-Stärke für HR Fix/img2img",
    )
    
    @property
    def resolution(self) -> tuple[int, int]:
        """Gibt Auflösung als Tuple zurück."""
        return (self.width, self.height)
    
    @property
    def aspect_ratio(self) -> float:
        """Berechnet Aspect Ratio."""
        return self.width / self.height
    
    def get_lora_prompt_tag(self) -> str:
        """
        Generiert den LoRA-Tag für den Prompt.
        
        Returns:
            Leerer String wenn keine LoRA, sonst "<lora_key:strength>"
        """
        if not self.lora_key:
            return ""
        return f"<{self.lora_key}:{self.lora_strength}>"


# =============================================================================
# SECTION 4: Style-Manifest (Illustration-Stil)
# =============================================================================

class MediumSpec(BaseModel):
    """
    Spezifikation des Illustrations-Mediums.
    
    Beschreibt die technische Ausführung der Illustration.
    """
    model_config = ConfigDict(extra="forbid")
    
    medium: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Haupt-Medium (wird im Prompt verwendet)",
        examples=[
            "ink and watercolor illustration",
            "digital painting with traditional feel",
            "pencil sketch with soft shading",
        ],
    )
    line_character: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Liniencharakter",
        examples=[
            "thin, precise ink lines, architectural clarity",
            "loose, expressive brush strokes",
            "no visible lines, soft edges",
        ],
    )
    color_application: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Art des Farbauftrags",
        examples=[
            "soft watercolor washes, translucent layers",
            "flat colors, no gradients",
            "rich oil paint texture, visible brush strokes",
        ],
    )
    texture: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Textur-Beschreibung",
        examples=[
            "natural paper grain, no digital smoothness",
            "canvas texture visible",
            "smooth, clean digital finish",
        ],
    )


class LightingSpec(BaseModel):
    """
    Licht- und Kontrast-Spezifikation.
    """
    model_config = ConfigDict(extra="forbid")
    
    lighting: LightingType = Field(
        default=LightingType.DIFFUSE,
        description="Hauptbeleuchtungstyp",
    )
    lighting_description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Detaillierte Lichtbeschreibung für Prompt",
        examples=[
            "diffuse, global, atmospheric haze",
            "warm golden hour lighting from the left",
        ],
    )
    contrast: ContrastLevel = Field(
        default=ContrastLevel.MODERATE,
        description="Kontrast-Level",
    )
    atmosphere: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Atmosphärische Qualität",
        examples=["leicht neblig", "staubig", "klar"],
    )


class CompositionSpec(BaseModel):
    """
    Kompositions-Spezifikation.
    """
    model_config = ConfigDict(extra="forbid")
    
    composition: CompositionType = Field(
        default=CompositionType.CENTERED,
        description="Kompositionstyp",
    )
    composition_description: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Detaillierte Kompositionsbeschreibung",
        examples=[
            "centered or slightly asymmetric, generous negative space",
            "dynamic diagonal composition, tight framing",
        ],
    )
    perspective: PerspectiveType = Field(
        default=PerspectiveType.EYE_LEVEL,
        description="Perspektive",
    )
    negative_space: Literal["minimal", "moderate", "generous"] = Field(
        default="moderate",
        description="Menge an Negativraum",
    )
    detail_level: Literal["minimal", "reduced", "moderate", "detailed"] = Field(
        default="reduced",
        description="Detailgrad",
    )


class StyleAnchor(BaseModel):
    """
    Referenz auf ein Stilanker-Bild.
    
    Stilanker definieren den Stil visuell, nicht die Prompts.
    """
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Beschreibender Name",
        examples=["Architektur / Raumstation (leer)", "Menschliche Figur (Rückenansicht)"],
    )
    image_path: Optional[str] = Field(
        default=None,
        description="Pfad zum Bild (relativ zum Projekt)",
    )
    image_url: Optional[str] = Field(
        default=None,
        description="URL zum Bild (falls extern gehostet)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Beschreibung was dieses Anchor-Bild demonstriert",
    )
    
    @model_validator(mode='after')
    def validate_has_reference(self) -> 'StyleAnchor':
        """Stellt sicher, dass entweder path oder url gesetzt ist."""
        if not self.image_path and not self.image_url:
            # Erlaubt Anchor ohne Bild (Platzhalter während Entwicklung)
            pass
        return self


class IllustrationStyleSpec(BaseModel):
    """
    Vollständige Spezifikation eines Buchillustrations-Stils.
    
    Dies ist das zentrale Schema für Style-Manifeste.
    Entspricht dem "Style Manifest" aus dem Buchillustrations-Konzept.
    
    Wird als Pydantic-Schema in der DB gespeichert (via PydanticSchemaField)
    oder als YAML-Datei für GitOps.
    
    Architektur-Prinzip: Dies ist eine SPEC (wird persistiert),
    nicht DERIVED (wird berechnet).
    
    Example:
        IllustrationStyleSpec(
            style_key="scifi_book_v1",
            version="1.0",
            name="Sci-Fi Buchillustration",
            # ... weitere Felder
        )
    """
    model_config = ConfigDict(
        extra="forbid",
        validate_default=True,
    )
    
    # Schema-Version für Migration
    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema-Version für automatische Migration",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    style_key: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r'^[a-z][a-z0-9_-]*$',
        description="Eindeutiger Schlüssel (snake_case oder kebab-case)",
        examples=["scifi_book_v1", "childrens-book-watercolor"],
    )
    version: str = Field(
        default="1.0",
        pattern=r'^\d+\.\d+(\.\d+)?$',
        description="Semantische Version (MAJOR.MINOR oder MAJOR.MINOR.PATCH)",
    )
    name: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Human-readable Name",
        examples=["Sci-Fi Buchillustration", "Kinderbuch Aquarell-Stil"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Ausführliche Beschreibung des Stils",
    )
    status: StyleStatus = Field(
        default=StyleStatus.DRAFT,
        description="Aktueller Status des Stils",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    author: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Autor/Art Director",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Erstellungszeitpunkt",
    )
    approved_at: Optional[datetime] = Field(
        default=None,
        description="Freigabe-Zeitpunkt (wenn status=active)",
    )
    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
        description="Tags für Filterung",
        examples=[["scifi", "book", "watercolor", "ink"]],
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # ZIEL & WIRKUNG
    # ═══════════════════════════════════════════════════════════════════════
    emotion: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Emotionale Wirkung des Stils",
        examples=[["ruhig", "fremd", "kontemplativ", "melancholisch"]],
    )
    target_audience: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Zielgruppe",
        examples=["Erwachsene Sci-Fi-Leser", "Kinder 4-8 Jahre"],
    )
    image_function: list[ImageFunction] = Field(
        ...,
        min_length=1,
        max_length=4,
        description="Funktion der Bilder",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # MEDIUM & TECHNIK
    # ═══════════════════════════════════════════════════════════════════════
    medium: MediumSpec = Field(
        ...,
        description="Medium- und Technik-Spezifikation",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # FARBEN
    # ═══════════════════════════════════════════════════════════════════════
    colors: ColorPalette = Field(
        ...,
        description="Farbpalette",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # LICHT & KONTRAST
    # ═══════════════════════════════════════════════════════════════════════
    lighting: LightingSpec = Field(
        ...,
        description="Licht- und Kontrast-Spezifikation",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # KOMPOSITION
    # ═══════════════════════════════════════════════════════════════════════
    composition: CompositionSpec = Field(
        ...,
        description="Kompositions-Spezifikation",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STILANKER
    # ═══════════════════════════════════════════════════════════════════════
    anchors: list[StyleAnchor] = Field(
        default_factory=list,
        max_length=10,
        description="Stilanker-Bilder (definieren den Stil visuell)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # VERBOTENE ELEMENTE
    # ═══════════════════════════════════════════════════════════════════════
    forbidden_elements: list[str] = Field(
        default_factory=list,
        description="Explizit verbotene Elemente/Stile",
        examples=[[
            "photorealistic",
            "3d render",
            "anime",
            "cartoon",
            "dramatic lighting",
            "lens flare",
        ]],
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STABLE DIFFUSION PARAMETER
    # ═══════════════════════════════════════════════════════════════════════
    sd_params: Optional[SDParameters] = Field(
        default=None,
        description="Technische Fixwerte für Stable Diffusion",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # DERIVED METHODS (nicht persistiert, berechnet)
    # ═══════════════════════════════════════════════════════════════════════
    
    def build_style_block(self) -> str:
        """
        Baut den Style-Block für den Prompt.
        
        Dies ist eine DERIVED-Funktion (berechnet, nicht persistiert).
        
        Returns:
            Fertiger Style-Block String für SD-Prompt
        """
        parts = []
        
        # LoRA-Tag (wenn vorhanden)
        if self.sd_params and self.sd_params.lora_key:
            parts.append(self.sd_params.get_lora_prompt_tag())
        
        # Medium
        parts.append(self.medium.medium)
        parts.append(self.medium.line_character)
        
        # Farben
        primary_hexes = [c.hex_code for c in self.colors.primary]
        if primary_hexes:
            parts.append(f"limited palette: {', '.join(primary_hexes)}")
        
        # Licht
        if self.lighting.lighting_description:
            parts.append(self.lighting.lighting_description)
        else:
            parts.append(f"{self.lighting.lighting.value} lighting")
        
        # Textur
        parts.append(self.medium.texture)
        
        # Kontrast
        parts.append(f"{self.lighting.contrast.value} contrast")
        
        # Komposition
        if self.composition.composition_description:
            parts.append(self.composition.composition_description)
        else:
            parts.append(f"{self.composition.composition.value} composition")
        
        return ",\n".join(parts)
    
    def build_negative_prompt(self) -> str:
        """
        Baut den Negative-Prompt aus verbotenen Elementen.
        
        Dies ist eine DERIVED-Funktion.
        
        Returns:
            Fertiger Negative-Prompt String
        """
        negatives = list(self.forbidden_elements)
        negatives.extend(self.colors.get_forbidden_patterns())
        return ", ".join(negatives)
    
    def get_full_version(self) -> str:
        """Gibt vollständige Version mit Key zurück."""
        return f"{self.style_key}:{self.version}"


# =============================================================================
# SECTION 5: Image-Generation-Parameter für Templates
# =============================================================================

class ImageGenerationParams(BaseModel):
    """
    Image-Generation-Parameter für PromptTemplate.
    
    Wird verwendet wenn PromptTemplate.output_format == IMAGE.
    Referenziert Style-Partial und definiert Validierungsregeln.
    
    Example:
        ImageGenerationParams(
            style_partial_key="illustration.style.scifi_book_v1",
            negative_prompt_template="{{partial:style.negative_prompt}}",
            forbidden_terms=["photorealistic", "3d render"],
        )
    """
    model_config = ConfigDict(extra="forbid")
    
    # Style-Referenz
    style_partial_key: Optional[str] = Field(
        default=None,
        pattern=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$',
        description="Key des Style-Partials (z.B. 'illustration.style.scifi_book_v1')",
    )
    
    # Inline-Style (Alternative zu Partial-Referenz)
    inline_style: Optional[IllustrationStyleSpec] = Field(
        default=None,
        description="Inline Style-Spec (wenn kein Partial verwendet wird)",
    )
    
    # Negative Prompt
    negative_prompt_template: Optional[str] = Field(
        default=None,
        description="Jinja2-Template für Negative-Prompt (kann Partials referenzieren)",
    )
    
    # SD-Parameter Override (überschreibt Style-Defaults)
    sd_params_override: Optional[SDParameters] = Field(
        default=None,
        description="SD-Parameter die Style-Defaults überschreiben",
    )
    
    # Validierung
    forbidden_terms: list[str] = Field(
        default_factory=list,
        description="Terme die im generierten Prompt nicht vorkommen dürfen",
    )
    required_terms: list[str] = Field(
        default_factory=list,
        description="Terme die im generierten Prompt vorkommen müssen",
    )
    
    # Post-Processing
    auto_append_quality_tags: bool = Field(
        default=True,
        description="Automatisch Quality-Tags anhängen (masterpiece, best quality)",
    )
    quality_tags: list[str] = Field(
        default_factory=lambda: ["masterpiece", "best quality", "highly detailed"],
        description="Quality-Tags zum Anhängen",
    )
    
    @model_validator(mode='after')
    def validate_style_source(self) -> 'ImageGenerationParams':
        """Stellt sicher, dass Style-Quelle definiert ist."""
        if not self.style_partial_key and not self.inline_style:
            raise ValueError(
                "Entweder style_partial_key oder inline_style muss gesetzt sein"
            )
        if self.style_partial_key and self.inline_style:
            raise ValueError(
                "Nur style_partial_key ODER inline_style darf gesetzt sein, nicht beide"
            )
        return self


# =============================================================================
# SECTION 6: Execution Results
# =============================================================================

class ImagePromptExecution(BaseModel):
    """
    Ergebnis einer Image-Prompt-Execution.
    
    Enthält alle Informationen um das Bild zu generieren
    und für Audit-Trail.
    
    Kann direkt an SD-Backend übergeben werden via to_sd_request().
    
    Example:
        execution = await executor.execute("illustration.generate.chapter", {...})
        sd_request = execution.to_sd_request()
        # → An Stable Diffusion API senden
    """
    model_config = ConfigDict(extra="forbid")
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTIFIKATION
    # ═══════════════════════════════════════════════════════════════════════
    execution_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Eindeutige Execution-ID",
    )
    template_key: str = Field(
        ...,
        description="Key des verwendeten Templates",
    )
    template_version: str = Field(
        ...,
        description="Version des Templates",
    )
    style_version: str = Field(
        ...,
        description="Version des Styles (key:version)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROMPTS (fertig gerendert)
    # ═══════════════════════════════════════════════════════════════════════
    positive_prompt: str = Field(
        ...,
        description="Fertiger positiver Prompt für SD",
    )
    negative_prompt: str = Field(
        ...,
        description="Fertiger negativer Prompt für SD",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # SD-PARAMETER
    # ═══════════════════════════════════════════════════════════════════════
    sd_params: SDParameters = Field(
        ...,
        description="Finale SD-Parameter (nach Merge von Style + Override)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # AUDIT
    # ═══════════════════════════════════════════════════════════════════════
    variables_used: dict[str, Any] = Field(
        default_factory=dict,
        description="Variablen die für das Rendering verwendet wurden",
    )
    rendered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Zeitpunkt des Renderings",
    )
    app_name: Optional[str] = Field(
        default=None,
        description="Name der App die die Execution ausgelöst hat",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User-ID (falls verfügbar)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # ERGEBNIS (nach Generation)
    # ═══════════════════════════════════════════════════════════════════════
    image_url: Optional[str] = Field(
        default=None,
        description="URL zum generierten Bild",
    )
    image_path: Optional[str] = Field(
        default=None,
        description="Lokaler Pfad zum generierten Bild",
    )
    image_seed: Optional[int] = Field(
        default=None,
        description="Verwendeter Seed (für Reproduzierbarkeit)",
    )
    generation_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Generierungszeit in Millisekunden",
    )
    success: bool = Field(
        default=False,
        description="War die Generation erfolgreich?",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Fehlermeldung falls nicht erfolgreich",
    )
    
    def to_sd_request(self) -> dict[str, Any]:
        """
        Konvertiert zu Stable Diffusion API Request.
        
        Kompatibel mit AUTOMATIC1111 / Forge / ComfyUI APIs.
        
        Returns:
            Dict das direkt an SD API gesendet werden kann
        """
        request = {
            "prompt": self.positive_prompt,
            "negative_prompt": self.negative_prompt,
            "width": self.sd_params.width,
            "height": self.sd_params.height,
            "steps": self.sd_params.steps,
            "cfg_scale": self.sd_params.cfg_scale,
            "sampler_name": self.sd_params.sampler.value,
            "seed": self.sd_params.seed if self.sd_params.seed else -1,
        }
        
        # High-Res Fix
        if self.sd_params.enable_hr:
            request.update({
                "enable_hr": True,
                "hr_scale": self.sd_params.hr_scale,
                "hr_upscaler": self.sd_params.hr_upscaler,
                "denoising_strength": self.sd_params.denoising_strength,
            })
        
        return request
    
    def to_comfyui_workflow(self) -> dict[str, Any]:
        """
        Konvertiert zu ComfyUI Workflow-Format.
        
        Returns:
            Dict für ComfyUI API
        """
        # Basis-Workflow (vereinfacht)
        return {
            "prompt": {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "seed": self.sd_params.seed or -1,
                        "steps": self.sd_params.steps,
                        "cfg": self.sd_params.cfg_scale,
                        "sampler_name": self.sd_params.sampler.value.lower().replace(" ", "_"),
                        "scheduler": "karras",
                        "denoise": 1.0,
                    }
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": self.positive_prompt,
                    }
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": self.negative_prompt,
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": self.sd_params.width,
                        "height": self.sd_params.height,
                        "batch_size": 1,
                    }
                }
            }
        }


# =============================================================================
# SECTION 7: Template-Erweiterungen
# =============================================================================

class PromptVariableType(str, Enum):
    """
    Typen für Template-Variablen.
    
    Erweitert um illustration-spezifische Typen.
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    # 🆕 Illustration-spezifisch
    COLOR = "color"              # Hex-Color
    COLOR_PALETTE = "color_palette"
    SD_PARAMS = "sd_params"
    STYLE_SPEC = "style_spec"


class PromptVariable(BaseModel):
    """
    Definition einer Template-Variable.
    
    Erweitert um illustration-spezifische Typen und Validierung.
    """
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r'^[a-z][a-z0-9_]*$',
        description="Variable name (snake_case)",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Human-readable Beschreibung",
    )
    required: bool = Field(
        default=True,
        description="Ist diese Variable erforderlich?",
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default-Wert wenn nicht angegeben",
    )
    type: PromptVariableType = Field(
        default=PromptVariableType.STRING,
        description="Typ der Variable",
    )
    validation: Optional[str] = Field(
        default=None,
        description="Regex-Pattern oder JSON-Schema Referenz",
    )
    examples: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Beispielwerte für Dokumentation",
    )
    
    # 🆕 Illustration-spezifisch
    prompt_weight: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=2.0,
        description="SD Prompt Weight (z.B. 1.3 für stärkere Gewichtung)",
    )


# =============================================================================
# SECTION 8: Style-Partial Template
# =============================================================================

class StylePartialTemplate(BaseModel):
    """
    Spezialisiertes Template für Illustration-Styles.
    
    Wird als Partial in anderen Templates verwendet.
    Enthält sowohl die Style-Spec als auch die generierten Prompt-Blöcke.
    
    Example YAML:
        key: illustration.style.scifi_book_v1
        type: style_partial
        style_spec:
          style_key: scifi_book_v1
          # ... weitere Spec-Felder
        style_block_template: |
          <{{lora_key}}:{{lora_strength}}>,
          {{medium.medium}},
          ...
    """
    model_config = ConfigDict(extra="forbid")
    
    # ═══════════════════════════════════════════════════════════════════════
    # IDENTITY
    # ═══════════════════════════════════════════════════════════════════════
    key: str = Field(
        ...,
        pattern=r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$',
        description="Unique key für Registry",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable Name",
    )
    version: str = Field(
        default="1.0",
        pattern=r'^\d+\.\d+(\.\d+)?$',
        description="Semantische Version",
    )
    type: Literal[TemplateType.STYLE_PARTIAL] = Field(
        default=TemplateType.STYLE_PARTIAL,
        description="Template-Typ (immer STYLE_PARTIAL)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # METADATA
    # ═══════════════════════════════════════════════════════════════════════
    domain: str = Field(
        default="illustration",
        description="Domain (immer 'illustration' für Style-Partials)",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags für Filterung",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Beschreibung des Stils",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # STYLE SPEC
    # ═══════════════════════════════════════════════════════════════════════
    style_spec: IllustrationStyleSpec = Field(
        ...,
        description="Vollständige Style-Spezifikation",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # TEMPLATES (für Jinja2 Rendering)
    # ═══════════════════════════════════════════════════════════════════════
    style_block_template: Optional[str] = Field(
        default=None,
        description="Jinja2-Template für Style-Block (wenn None, wird aus Spec generiert)",
    )
    negative_prompt_template: Optional[str] = Field(
        default=None,
        description="Jinja2-Template für Negative-Prompt (wenn None, wird aus Spec generiert)",
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # GOVERNANCE
    # ═══════════════════════════════════════════════════════════════════════
    is_active: bool = Field(
        default=True,
        description="Ist dieser Style aktiv/verwendbar?",
    )
    created_at: Optional[datetime] = Field(
        default=None,
        description="Erstellungszeitpunkt",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Letztes Update",
    )
    
    def get_style_block(self) -> str:
        """
        Gibt den Style-Block zurück.
        
        Verwendet custom Template wenn vorhanden, sonst generiert aus Spec.
        """
        if self.style_block_template:
            # TODO: Jinja2 Rendering mit style_spec als Context
            return self.style_block_template
        return self.style_spec.build_style_block()
    
    def get_negative_prompt(self) -> str:
        """
        Gibt den Negative-Prompt zurück.
        
        Verwendet custom Template wenn vorhanden, sonst generiert aus Spec.
        """
        if self.negative_prompt_template:
            # TODO: Jinja2 Rendering
            return self.negative_prompt_template
        return self.style_spec.build_negative_prompt()


# =============================================================================
# SECTION 9: Validation & Migration Utilities
# =============================================================================

class StyleSpecMigrator:
    """
    Migrator für IllustrationStyleSpec Schema-Versionen.
    
    Folgt dem Platform-Pattern für Schema-Migration.
    
    Example:
        migrator = StyleSpecMigrator()
        current_version = migrator.detect_version(old_data)
        migrated_data = migrator.migrate(old_data, target_version=2)
    """
    
    CURRENT_VERSION = 1
    
    @staticmethod
    def detect_version(data: dict) -> int:
        """Erkennt die Schema-Version eines Payloads."""
        return data.get("schema_version", 1)
    
    @classmethod
    def migrate(
        cls,
        data: dict,
        target_version: int | None = None
    ) -> dict:
        """
        Migriert Payload zur Zielversion.
        
        Args:
            data: Rohes Dict (z.B. aus DB)
            target_version: Zielversion (default: CURRENT_VERSION)
            
        Returns:
            Migriertes Dict
        """
        if target_version is None:
            target_version = cls.CURRENT_VERSION
        
        current = cls.detect_version(data)
        result = dict(data)
        
        # Schrittweise Migration
        while current < target_version:
            migration_method = getattr(cls, f"_v{current}_to_v{current + 1}", None)
            if not migration_method:
                raise ValueError(
                    f"Keine Migration von v{current} zu v{current + 1} definiert"
                )
            result = migration_method(result)
            current += 1
        
        return result
    
    @staticmethod
    def _v1_to_v2(data: dict) -> dict:
        """
        Migration v1 → v2.
        
        Beispiel für zukünftige Migrationen.
        Aktuell nur Placeholder.
        """
        data = dict(data)
        # Hier: Felder hinzufügen, umbenennen, etc.
        # data.setdefault("new_field", "default_value")
        data["schema_version"] = 2
        return data


class PromptValidator:
    """
    Validiert generierte Prompts gegen Style-Regeln.
    
    Stellt sicher, dass keine verbotenen Terme verwendet werden
    und alle erforderlichen Elemente vorhanden sind.
    """
    
    @staticmethod
    def validate_prompt(
        prompt: str,
        image_params: ImageGenerationParams,
        style_spec: IllustrationStyleSpec | None = None,
    ) -> tuple[bool, list[str]]:
        """
        Validiert einen Prompt gegen die Regeln.
        
        Args:
            prompt: Generierter Prompt
            image_params: Image-Parameter mit Validierungsregeln
            style_spec: Optional Style-Spec für zusätzliche Validierung
            
        Returns:
            Tuple (is_valid, list_of_errors)
        """
        errors = []
        prompt_lower = prompt.lower()
        
        # Prüfe verbotene Terme
        for term in image_params.forbidden_terms:
            if term.lower() in prompt_lower:
                errors.append(f"Verbotener Term gefunden: '{term}'")
        
        # Prüfe erforderliche Terme
        for term in image_params.required_terms:
            if term.lower() not in prompt_lower:
                errors.append(f"Erforderlicher Term fehlt: '{term}'")
        
        # Prüfe Style-Spec Verbote (wenn vorhanden)
        if style_spec:
            for forbidden in style_spec.forbidden_elements:
                if forbidden.lower() in prompt_lower:
                    errors.append(
                        f"Style-verbotenes Element gefunden: '{forbidden}'"
                    )
        
        return (len(errors) == 0, errors)


# =============================================================================
# SECTION 10: Public API
# =============================================================================

__all__ = [
    # Enums
    "OutputFormat",
    "TemplateType",
    "ImageFunction",
    "LightingType",
    "ContrastLevel",
    "CompositionType",
    "PerspectiveType",
    "StyleStatus",
    "ColorRole",
    "SDSampler",
    "PromptVariableType",
    
    # Color Schemas
    "ColorSpec",
    "ForbiddenColorSpec",
    "ColorPalette",
    
    # SD Schemas
    "SDParameters",
    
    # Style Schemas
    "MediumSpec",
    "LightingSpec",
    "CompositionSpec",
    "StyleAnchor",
    "IllustrationStyleSpec",
    
    # Template Schemas
    "ImageGenerationParams",
    "PromptVariable",
    "StylePartialTemplate",
    
    # Execution
    "ImagePromptExecution",
    
    # Utilities
    "StyleSpecMigrator",
    "PromptValidator",
]
