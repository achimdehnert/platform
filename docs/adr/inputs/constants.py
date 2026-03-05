"""
aifw/constants.py — Named constants for the quality_level integer scale.

ADR-095 §5.1 — QualityLevel constants.
Use these instead of raw integers in all consumer code.
"""
from __future__ import annotations


class QualityLevel:
    """
    Named constants for the quality_level integer scale (1–9).

    The full 1–9 scale is valid; these constants represent canonical
    midpoints for each band. Use ranges for range-checks:

        if quality_level <= 3:   # economy band
        if 4 <= quality_level <= 6:  # balanced band
        if quality_level >= 7:   # premium band

    Band → Canonical midpoint:
        Economy  (1–3): Together AI Qwen, Groq Llama, OpenRouter Mistral Nemo
        Balanced (4–6): GPT-4o-mini, Gemini 2.0 Flash, Llama 3.3 70B
        Premium  (7–9): Claude Sonnet/Opus, GPT-4o full, o3

    Consumer example:
        from aifw import QualityLevel
        result = sync_completion(
            action_code="story_writing",
            messages=messages,
            quality_level=QualityLevel.PREMIUM,
        )
    """

    # Canonical midpoints (use these in consumer code)
    ECONOMY: int = 2
    BALANCED: int = 5
    PREMIUM: int = 8

    # Band boundaries (use these in range checks / mapping logic)
    ECONOMY_MIN: int = 1
    ECONOMY_MAX: int = 3
    BALANCED_MIN: int = 4
    BALANCED_MAX: int = 6
    PREMIUM_MIN: int = 7
    PREMIUM_MAX: int = 9

    # Allowed values
    MIN: int = 1
    MAX: int = 9

    @classmethod
    def band_for(cls, quality_level: int) -> str:
        """Return the band name for a given quality_level integer."""
        if quality_level <= cls.ECONOMY_MAX:
            return "economy"
        if quality_level <= cls.BALANCED_MAX:
            return "balanced"
        return "premium"

    @classmethod
    def is_valid(cls, quality_level: int) -> bool:
        """Return True if quality_level is in the valid range 1–9."""
        return cls.MIN <= quality_level <= cls.MAX


# Valid priority values as a constant for validation
VALID_PRIORITIES: frozenset[str] = frozenset({"fast", "balanced", "quality"})
