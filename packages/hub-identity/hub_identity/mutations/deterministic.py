"""
Deterministic mutation strategies (Design #3).

These strategies require NO LLM — they use rule-based
transformations. 90% of mutations can be handled here.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hub_identity.core.schema import HubDNA
    from hub_identity.core.scoring import ScoreNode


# ── Font Swap ───────────────────────────────────────────────────


FONT_ALTERNATIVES: dict[str, list[str]] = {
    # AI-typical → distinctive alternatives (all on Bunny Fonts)
    "Inter": ["Figtree", "Outfit", "Lexend", "Manrope"],
    "Roboto": ["Barlow", "DM Sans", "Work Sans", "Nunito"],
    "Space Grotesk": ["Syne", "Instrument Sans", "Raleway"],
    "Poppins": ["Plus Jakarta Sans", "Outfit", "Lexend"],
    "system-ui": ["Figtree", "Barlow", "DM Sans"],
    "Arial": ["Barlow", "Work Sans", "Nunito"],
}

MONO_ALTERNATIVES: list[str] = [
    "JetBrains Mono",
    "Fira Code",
    "IBM Plex Mono",
    "Source Code Pro",
]


class FontSwapStrategy:
    """Replace AI-typical fonts with distinctive alternatives."""

    name = "font_swap"
    requires_llm = False

    def should_apply(
        self, dna: HubDNA, score: ScoreNode,
    ) -> bool:
        typo = score.find("Typography")
        if not typo:
            return False
        return typo.raw_score > 15

    def apply(self, dna: HubDNA) -> HubDNA:
        data = dna.model_dump(mode="json")
        typo = data["visual"]["typography"]

        for field in ("display", "body"):
            font = typo[field]
            if font in FONT_ALTERNATIVES:
                alts = FONT_ALTERNATIVES[font]
                typo[field] = random.choice(alts)

        if typo["mono"] not in MONO_ALTERNATIVES:
            typo["mono"] = random.choice(MONO_ALTERNATIVES)

        data["visual"]["typography"] = typo
        return dna.model_validate(data)


# ── Radius Jitter ───────────────────────────────────────────────


AI_TYPICAL_RADII = {4, 6, 8, 12, 16}
HUMAN_RADII = [3, 5, 7, 9, 10, 11, 13, 14, 15, 18, 20]


class RadiusJitterStrategy:
    """Replace AI-typical border radii with human-feeling values."""

    name = "radius_jitter"
    requires_llm = False

    def should_apply(
        self, dna: HubDNA, score: ScoreNode,
    ) -> bool:
        layout = score.find("Layout")
        if not layout:
            return False
        return layout.raw_score > 10

    def apply(self, dna: HubDNA) -> HubDNA:
        data = dna.model_dump(mode="json")
        radius = data["visual"]["layout"]["border_radius"]

        if radius in AI_TYPICAL_RADII:
            data["visual"]["layout"]["border_radius"] = (
                random.choice(HUMAN_RADII)
            )

        return dna.model_validate(data)


# ── Color Entropy ───────────────────────────────────────────────


class ColorEntropyStrategy:
    """
    Add slight imperfection to mathematically perfect palettes.

    AI palettes often have perfectly spaced hue values.
    This adds subtle shifts to make them feel hand-picked.
    """

    name = "color_entropy"
    requires_llm = False

    def should_apply(
        self, dna: HubDNA, score: ScoreNode,
    ) -> bool:
        color = score.find("Color")
        if not color:
            return False
        return color.raw_score > 15

    def apply(self, dna: HubDNA) -> HubDNA:
        data = dna.model_dump(mode="json")
        palette = data["visual"]["palette"]

        for key in ("muted", "border", "muted_foreground"):
            if key in palette and palette[key].startswith("#"):
                palette[key] = _jitter_hex(palette[key])

        data["visual"]["palette"] = palette
        return dna.model_validate(data)


def _jitter_hex(hex_color: str, amount: int = 8) -> str:
    """Add subtle random shift to a hex color."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"#{hex_color}"
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = max(0, min(255, r + random.randint(-amount, amount)))
    g = max(0, min(255, g + random.randint(-amount, amount)))
    b = max(0, min(255, b + random.randint(-amount, amount)))

    return f"#{r:02x}{g:02x}{b:02x}"


# ── Banned Word Replacer ────────────────────────────────────────


class BannedWordReplacer:
    """
    Replace banned words with preferred alternatives.

    Uses the hub's own preferred_words mapping.
    Deterministic 1:1 replacement — no LLM needed.
    """

    name = "banned_words"
    requires_llm = False

    def should_apply(
        self, dna: HubDNA, score: ScoreNode,
    ) -> bool:
        vocab = score.find("Vocabulary")
        if not vocab:
            return False
        return vocab.raw_score > 10

    def apply(self, dna: HubDNA) -> HubDNA:
        data = dna.model_dump(mode="json")
        voice = data["voice"]
        mc = voice["micro_copy"]

        for lang in ("de", "en"):
            prefs = voice.get(f"preferred_words_{lang}", {})
            if not prefs:
                continue
            copy_dict = mc.get(lang, {})
            for field_key, text in copy_dict.items():
                if not isinstance(text, str):
                    continue
                for banned, preferred in prefs.items():
                    text = text.replace(banned, preferred)
                copy_dict[field_key] = text
            mc[lang] = copy_dict

        data["voice"]["micro_copy"] = mc
        return dna.model_validate(data)
