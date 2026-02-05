"""
WeltenhubEnricher - LLM-powered content enrichment for Weltenhub entities.

Provides AI-generated descriptions, backstories, and narratives for:
- Worlds
- Characters
- Stories
- Scenes

Compatible with travel-beat's WeltenhubEnricher pattern for cross-platform integration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings

import structlog

from .llm_client import LlmRequest, generate_text

logger = structlog.get_logger(__name__)


@dataclass
class EnrichmentResult:
    """Result of an enrichment operation."""

    success: bool
    content: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    tokens_used: int = 0
    latency_ms: int = 0


class WeltenhubEnricher:
    """
    LLM-powered content enrichment service for Weltenhub entities.

    Supports multiple LLM providers:
    - OpenAI (gpt-4o-mini, gpt-4o)
    - Anthropic (claude-3-5-haiku, claude-3-5-sonnet)
    - LLM Gateway (local or remote)
    """

    DEFAULT_SYSTEM_PROMPT = """Du bist ein kreativer Schreibassistent für Weltenbau 
und Geschichtenentwicklung. Deine Aufgabe ist es, atmosphärische und konsistente
Inhalte zu generieren, die in Fantasy-, Sci-Fi- oder realistischen Welten verwendet
werden können. Antworte immer auf Deutsch, es sei denn, anders angewiesen."""

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self._api_key: Optional[str] = None
        self._api_endpoint: Optional[str] = None
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize LLM provider configuration."""
        if self.provider == "anthropic":
            self._api_key = getattr(
                settings, "ANTHROPIC_API_KEY", None
            ) or os.getenv("ANTHROPIC_API_KEY")
            self._api_endpoint = "https://api.anthropic.com/v1/messages"
            self.model = self.model or "claude-3-5-haiku-20241022"

        elif self.provider == "openai":
            self._api_key = getattr(
                settings, "OPENAI_API_KEY", None
            ) or os.getenv("OPENAI_API_KEY")
            self._api_endpoint = "https://api.openai.com/v1/chat/completions"
            self.model = self.model or "gpt-4o-mini"

        elif self.provider == "gateway":
            self._api_key = ""
            self._api_endpoint = getattr(
                settings, "LLM_GATEWAY_URL", "http://localhost:8100"
            )
            self.model = self.model or None

        else:
            logger.warning(
                "unknown_llm_provider",
                provider=self.provider,
                fallback="openai"
            )
            self.provider = "openai"
            self._init_provider()

    def _has_llm(self) -> bool:
        """Check if LLM is available."""
        if self.provider == "gateway":
            return bool(self._api_endpoint)
        return bool(self._api_key and self._api_endpoint)

    def _call_llm(
        self,
        prompt: str,
        max_tokens: int = 500,
        system: Optional[str] = None
    ) -> Optional[str]:
        """Execute LLM call and return text content."""
        if not self._has_llm():
            logger.warning("no_llm_available", provider=self.provider)
            return None

        req = LlmRequest(
            provider=self.provider,
            api_endpoint=self._api_endpoint,
            api_key=self._api_key or "",
            model=self.model,
            system=system or self.DEFAULT_SYSTEM_PROMPT,
            prompt=prompt,
            temperature=self.temperature,
            max_tokens=max_tokens,
        )

        result = generate_text(req)

        if result.get("ok"):
            return result.get("text", "")
        else:
            logger.error(
                "llm_call_failed",
                error=result.get("error"),
                provider=self.provider
            )
            return None

    def enrich_world(
        self,
        name: str,
        genre: str = "fantasy",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> EnrichmentResult:
        """
        Generate rich world description using LLM.

        Args:
            name: World name
            genre: Genre (fantasy, sci-fi, romance, etc.)
            description: Existing description to enhance
            tags: Optional tags for context

        Returns:
            EnrichmentResult with description, atmosphere, rules
        """
        if not self._has_llm():
            return EnrichmentResult(success=False, error="No LLM available")

        tags_str = ", ".join(tags) if tags else "keine"
        existing = f"\nBestehende Beschreibung: {description}" if description else ""

        prompt = f"""Erstelle eine atmosphärische Weltbeschreibung.

Name der Welt: {name}
Genre: {genre}
Tags: {tags_str}{existing}

Generiere:
1. BESCHREIBUNG: Eine evokative Beschreibung (3-4 Sätze)
2. ATMOSPHÄRE: Die vorherrschende Stimmung (1-2 Sätze)
3. BESONDERHEIT: Ein einzigartiges Merkmal dieser Welt (1 Satz)

Antworte im Format:
BESCHREIBUNG: [text]
ATMOSPHÄRE: [text]
BESONDERHEIT: [text]"""

        try:
            content = self._call_llm(prompt, max_tokens=600)
            if content:
                parsed = self._parse_labeled_response(
                    content,
                    ["BESCHREIBUNG", "ATMOSPHÄRE", "BESONDERHEIT"]
                )
                return EnrichmentResult(
                    success=True,
                    content={
                        "description": parsed.get("BESCHREIBUNG", content[:500]),
                        "atmosphere": parsed.get("ATMOSPHÄRE", ""),
                        "unique_feature": parsed.get("BESONDERHEIT", ""),
                    }
                )
            return EnrichmentResult(success=False, error="Empty LLM response")
        except Exception as e:
            logger.error("enrich_world_error", error=str(e), world=name)
            return EnrichmentResult(success=False, error=str(e))

    def enrich_character(
        self,
        name: str,
        role: str = "protagonist",
        world_name: str = "",
        traits: Optional[List[str]] = None,
        genre: str = "fantasy",
    ) -> EnrichmentResult:
        """
        Generate rich character profile using LLM.

        Args:
            name: Character name
            role: Role (protagonist, antagonist, sidekick, etc.)
            world_name: Name of the world for context
            traits: Existing traits
            genre: Story genre

        Returns:
            EnrichmentResult with personality, backstory, motivation, goals
        """
        if not self._has_llm():
            return EnrichmentResult(success=False, error="No LLM available")

        traits_str = ", ".join(traits) if traits else "noch nicht definiert"
        world_context = f" in der Welt '{world_name}'" if world_name else ""

        prompt = f"""Erstelle ein Charakterprofil für eine {genre}-Geschichte{world_context}.

Name: {name}
Rolle: {role}
Bekannte Eigenschaften: {traits_str}

Generiere:
1. PERSÖNLICHKEIT: Kernpersönlichkeit (2-3 Sätze)
2. HINTERGRUND: Kurze Backstory (2-3 Sätze)
3. MOTIVATION: Was treibt diesen Charakter an (1-2 Sätze)
4. ZIEL: Hauptziel in der Geschichte (1 Satz)
5. SCHWÄCHE: Eine charakterliche Schwäche (1 Satz)

Antworte im Format:
PERSÖNLICHKEIT: [text]
HINTERGRUND: [text]
MOTIVATION: [text]
ZIEL: [text]
SCHWÄCHE: [text]"""

        try:
            content = self._call_llm(prompt, max_tokens=800)
            if content:
                parsed = self._parse_labeled_response(
                    content,
                    ["PERSÖNLICHKEIT", "HINTERGRUND", "MOTIVATION", "ZIEL", "SCHWÄCHE"]
                )
                return EnrichmentResult(
                    success=True,
                    content={
                        "personality": parsed.get("PERSÖNLICHKEIT", ""),
                        "backstory": parsed.get("HINTERGRUND", ""),
                        "motivation": parsed.get("MOTIVATION", ""),
                        "goals": parsed.get("ZIEL", ""),
                        "flaws": parsed.get("SCHWÄCHE", ""),
                    }
                )
            return EnrichmentResult(success=False, error="Empty LLM response")
        except Exception as e:
            logger.error("enrich_character_error", error=str(e), character=name)
            return EnrichmentResult(success=False, error=str(e))

    def enrich_story(
        self,
        title: str,
        world_name: str = "",
        genre: str = "fantasy",
        characters: Optional[List[str]] = None,
        themes: Optional[List[str]] = None,
    ) -> EnrichmentResult:
        """
        Generate story synopsis and structure using LLM.

        Args:
            title: Story title
            world_name: World context
            genre: Story genre
            characters: Main character names
            themes: Story themes

        Returns:
            EnrichmentResult with logline, synopsis, themes
        """
        if not self._has_llm():
            return EnrichmentResult(success=False, error="No LLM available")

        chars_str = ", ".join(characters) if characters else "nicht definiert"
        themes_str = ", ".join(themes) if themes else "nicht definiert"
        world_ctx = f"Welt: {world_name}\n" if world_name else ""

        prompt = f"""Entwickle eine Geschichtenstruktur.

Titel: {title}
{world_ctx}Genre: {genre}
Hauptcharaktere: {chars_str}
Themen: {themes_str}

Generiere:
1. LOGLINE: Ein packender Satz, der die Geschichte zusammenfasst
2. SYNOPSIS: Kurze Zusammenfassung der Handlung (4-5 Sätze)
3. KONFLIKT: Der zentrale Konflikt (1-2 Sätze)
4. THEMEN: Die Hauptthemen der Geschichte (2-3 Themen)

Antworte im Format:
LOGLINE: [text]
SYNOPSIS: [text]
KONFLIKT: [text]
THEMEN: [text]"""

        try:
            content = self._call_llm(prompt, max_tokens=800)
            if content:
                parsed = self._parse_labeled_response(
                    content,
                    ["LOGLINE", "SYNOPSIS", "KONFLIKT", "THEMEN"]
                )
                return EnrichmentResult(
                    success=True,
                    content={
                        "logline": parsed.get("LOGLINE", ""),
                        "synopsis": parsed.get("SYNOPSIS", ""),
                        "conflict": parsed.get("KONFLIKT", ""),
                        "themes": parsed.get("THEMEN", ""),
                    }
                )
            return EnrichmentResult(success=False, error="Empty LLM response")
        except Exception as e:
            logger.error("enrich_story_error", error=str(e), title=title)
            return EnrichmentResult(success=False, error=str(e))

    def enrich_scene(
        self,
        title: str,
        story_title: str = "",
        location: str = "",
        characters: Optional[List[str]] = None,
        purpose: str = "",
        genre: str = "fantasy",
    ) -> EnrichmentResult:
        """
        Generate scene content and structure using LLM.

        Args:
            title: Scene title
            story_title: Parent story
            location: Scene location
            characters: Characters in scene
            purpose: Scene purpose/goal
            genre: Story genre

        Returns:
            EnrichmentResult with summary, beats, atmosphere
        """
        if not self._has_llm():
            return EnrichmentResult(success=False, error="No LLM available")

        chars_str = ", ".join(characters) if characters else "nicht definiert"
        story_ctx = f"Geschichte: {story_title}\n" if story_title else ""
        loc_ctx = f"Ort: {location}\n" if location else ""
        purpose_ctx = f"Zweck: {purpose}\n" if purpose else ""

        prompt = f"""Entwickle eine Szene für eine {genre}-Geschichte.

Szene: {title}
{story_ctx}{loc_ctx}Charaktere: {chars_str}
{purpose_ctx}

Generiere:
1. ZUSAMMENFASSUNG: Was passiert in dieser Szene (2-3 Sätze)
2. ATMOSPHÄRE: Die Stimmung der Szene (1-2 Sätze)
3. BEATS: Die wichtigsten Handlungsschritte (3-4 Punkte)
4. KONFLIKT: Der Konflikt oder die Spannung in der Szene (1 Satz)

Antworte im Format:
ZUSAMMENFASSUNG: [text]
ATMOSPHÄRE: [text]
BEATS: [text]
KONFLIKT: [text]"""

        try:
            content = self._call_llm(prompt, max_tokens=700)
            if content:
                parsed = self._parse_labeled_response(
                    content,
                    ["ZUSAMMENFASSUNG", "ATMOSPHÄRE", "BEATS", "KONFLIKT"]
                )
                return EnrichmentResult(
                    success=True,
                    content={
                        "summary": parsed.get("ZUSAMMENFASSUNG", ""),
                        "atmosphere": parsed.get("ATMOSPHÄRE", ""),
                        "beats": parsed.get("BEATS", ""),
                        "conflict": parsed.get("KONFLIKT", ""),
                    }
                )
            return EnrichmentResult(success=False, error="Empty LLM response")
        except Exception as e:
            logger.error("enrich_scene_error", error=str(e), scene=title)
            return EnrichmentResult(success=False, error=str(e))

    def _parse_labeled_response(
        self,
        content: str,
        labels: List[str]
    ) -> Dict[str, str]:
        """Parse LLM response with labeled sections."""
        result = {}
        current_label = None
        current_text = []

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            found_label = False
            for label in labels:
                if line.upper().startswith(f"{label}:"):
                    if current_label:
                        result[current_label] = " ".join(current_text).strip()
                    current_label = label
                    current_text = [line.split(":", 1)[1].strip()]
                    found_label = True
                    break

            if not found_label and current_label:
                current_text.append(line)

        if current_label:
            result[current_label] = " ".join(current_text).strip()

        return result


def get_enricher(
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> WeltenhubEnricher:
    """
    Factory function to get configured enricher.

    Uses settings or environment to determine provider.
    """
    if provider is None:
        provider = getattr(settings, "LLM_PROVIDER", None) or os.getenv(
            "LLM_PROVIDER", "openai"
        )

    return WeltenhubEnricher(provider=provider, model=model)
