"""
Travel Story - Integrated Story Generator
=========================================
Kombiniert Location-Database mit Story-Generation.

Verwendet:
- LocationRepository für Orts-Daten
- LocationGenerator für On-Demand Generierung
- UserWorld für Personalisierung
- Anthropic API für Story-Text
"""

import json
import os
from typing import Optional, List, Generator, Callable
from datetime import datetime
from dataclasses import dataclass, field

from location_models import (
    LayerType, UserWorld, MergedLocationData,
    StoryCharacter, LocationMemory,
)
from location_repository import LocationRepository, DatabaseConfig
from location_generator import LocationGenerator, AnthropicLocationLLM


# ═══════════════════════════════════════════════════════════════
# STORY CONTEXT
# ═══════════════════════════════════════════════════════════════

@dataclass
class StoryContext:
    """Kontext für die Story-Generierung"""
    
    # Basis
    title: str
    genre: str  # romance, thriller, romantic_suspense, mystery
    
    # Protagonist
    protagonist_name: str
    protagonist_background: str = ""
    
    # Setting
    primary_location: str = ""
    time_period: str = "Gegenwart"
    
    # Plot
    central_conflict: str = ""
    
    # Optional: Love Interest (für Romance)
    love_interest_name: str = ""
    love_interest_background: str = ""
    
    # Optional: Antagonist (für Thriller)
    antagonist_name: str = ""
    antagonist_background: str = ""
    
    # Spice Level (für Romance)
    spice_level: str = "mild"  # none, mild, moderate, spicy
    
    def to_prompt(self) -> str:
        """Konvertiere zu Prompt-Text"""
        lines = [
            f"# STORY-KONTEXT",
            f"Titel: {self.title}",
            f"Genre: {self.genre}",
            f"",
            f"## PROTAGONIST",
            f"Name: {self.protagonist_name}",
        ]
        
        if self.protagonist_background:
            lines.append(f"Hintergrund: {self.protagonist_background}")
        
        if self.love_interest_name:
            lines.extend([
                f"",
                f"## LOVE INTEREST",
                f"Name: {self.love_interest_name}",
            ])
            if self.love_interest_background:
                lines.append(f"Hintergrund: {self.love_interest_background}")
        
        if self.antagonist_name:
            lines.extend([
                f"",
                f"## ANTAGONIST",
                f"Name: {self.antagonist_name}",
            ])
            if self.antagonist_background:
                lines.append(f"Hintergrund: {self.antagonist_background}")
        
        lines.extend([
            f"",
            f"## SETTING",
            f"Hauptort: {self.primary_location}",
            f"Zeit: {self.time_period}",
            f"",
            f"## ZENTRALER KONFLIKT",
            f"{self.central_conflict}",
        ])
        
        return "\n".join(lines)


@dataclass
class ChapterSpec:
    """Spezifikation für ein einzelnes Kapitel"""
    
    chapter_number: int
    title: str = ""
    
    # Story-Beat
    beat_name: str = ""
    beat_description: str = ""
    
    # Location
    story_location: str = ""  # Wo spielt das Kapitel
    reader_location: str = "" # Wo ist der Leser
    
    # Pacing
    pacing: str = "balanced"  # action, emotional, reflective, atmospheric
    
    # Ziel-Wörter
    target_words: int = 3000
    
    # Spezielle Anweisungen
    special_instructions: List[str] = field(default_factory=list)
    
    # Kapitel-spezifische Hinweise
    hook_hint: str = ""
    emotional_tone: str = ""


@dataclass 
class GeneratedChapter:
    """Ein generiertes Kapitel"""
    
    chapter_number: int
    title: str
    content: str
    word_count: int
    
    # Location Info
    story_location: str = ""
    reader_location: str = ""
    
    # Metadata
    generated_at: str = ""
    model_used: str = ""
    
    def to_markdown(self) -> str:
        return f"## Kapitel {self.chapter_number}: {self.title}\n\n{self.content}"


# ═══════════════════════════════════════════════════════════════
# PROMPT TEMPLATES
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Du bist ein erfahrener Romanautor, spezialisiert auf {genre}.

SCHREIBSTIL:
- Lebendige, sinnliche Beschreibungen
- Natürliche Dialoge mit Subtext
- Show, don't tell
- Emotionale Tiefe
- Atmosphärische Details

TECHNISCHE VORGABEN:
- Schreibe auf Deutsch
- Ziel: {target_words} Wörter
- Verwende keine Kapitelüberschriften im Text
- Beginne direkt mit der Handlung
- Ende mit einem Hook für das nächste Kapitel

{genre_instructions}"""

GENRE_INSTRUCTIONS = {
    "romance": """ROMANCE-SPEZIFISCH:
- Langsamer Aufbau der Anziehung
- Tension und Sehnsucht
- Emotionale Verwundbarkeit zeigen
- Kleine, bedeutsame Gesten
- Spice Level: {spice_level}""",
    
    "thriller": """THRILLER-SPEZIFISCH:
- Konstante Spannung aufbauen
- Unerwartete Wendungen
- Kurze, dynamische Szenen
- Paranoia und Misstrauen
- Cliffhanger am Ende""",
    
    "romantic_suspense": """ROMANTIC SUSPENSE:
- Balance zwischen Romance und Spannung
- Gefahr bringt Protagonisten zusammen
- Emotionale und physische Stakes
- Vertrauen als zentrales Thema
- Spice Level: {spice_level}""",
    
    "mystery": """MYSTERY-SPEZIFISCH:
- Hinweise geschickt einstreuen
- Red Herrings platzieren
- Atmosphäre des Rätselhaften
- Logische Auflösung vorbereiten
- Leser zum Mitraten einladen""",
}

CHAPTER_PROMPT = """Schreibe Kapitel {chapter_number} der Geschichte.

{story_context}

{location_context}

## KAPITEL-SPEZIFIKATION
Beat: {beat_name}
{beat_description}

Emotionaler Ton: {emotional_tone}
Pacing: {pacing}

{special_instructions}

{hook_hint}

---
Schreibe jetzt das Kapitel ({target_words} Wörter). Beginne direkt mit der Handlung."""


# ═══════════════════════════════════════════════════════════════
# INTEGRATED STORY GENERATOR
# ═══════════════════════════════════════════════════════════════

class IntegratedStoryGenerator:
    """
    Story-Generator mit Location-Database Integration.
    
    Features:
    - Verwendet Location-Daten für atmosphärische Details
    - Personalisierung via UserWorld
    - Story-Kontinuität (Charaktere, Erinnerungen)
    - Ausschluss-System für sensible Orte
    """
    
    def __init__(
        self,
        repository: LocationRepository,
        model: str = "claude-sonnet-4-20250514",
        use_real_llm: bool = True,
    ):
        self.repo = repository
        self.model = model
        self.location_gen = LocationGenerator(repository, use_real_llm=use_real_llm)
        
        # Anthropic Client für Story-Generierung
        self._client = None
        self._use_real_llm = use_real_llm
        
        if use_real_llm:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    import anthropic
                    self._client = anthropic.Anthropic(api_key=api_key)
                except ImportError:
                    print("  ⚠ anthropic nicht installiert")
    
    def _get_location_context(
        self,
        location_name: str,
        country: str,
        layer_type: LayerType,
        user_world: Optional[UserWorld] = None,
    ) -> str:
        """Hole Location-Kontext für Prompt"""
        
        merged = self.location_gen.get_merged_location(
            city=location_name,
            country=country,
            layer_type=layer_type,
            user_world=user_world,
        )
        
        return merged.to_prompt_context()
    
    def _build_system_prompt(
        self,
        genre: str,
        target_words: int,
        spice_level: str = "mild",
    ) -> str:
        """Baue System-Prompt"""
        
        genre_instr = GENRE_INSTRUCTIONS.get(genre, "")
        if "{spice_level}" in genre_instr:
            genre_instr = genre_instr.format(spice_level=spice_level)
        
        return SYSTEM_PROMPT.format(
            genre=genre,
            target_words=target_words,
            genre_instructions=genre_instr,
        )
    
    def _build_chapter_prompt(
        self,
        chapter_spec: ChapterSpec,
        story_context: StoryContext,
        location_context: str,
    ) -> str:
        """Baue Chapter-Prompt"""
        
        special = ""
        if chapter_spec.special_instructions:
            special = "## SPEZIELLE ANWEISUNGEN\n" + "\n".join(
                f"- {i}" for i in chapter_spec.special_instructions
            )
        
        hook = ""
        if chapter_spec.hook_hint:
            hook = f"## HOOK-HINWEIS\n{chapter_spec.hook_hint}"
        
        return CHAPTER_PROMPT.format(
            chapter_number=chapter_spec.chapter_number,
            story_context=story_context.to_prompt(),
            location_context=location_context,
            beat_name=chapter_spec.beat_name,
            beat_description=chapter_spec.beat_description or "",
            emotional_tone=chapter_spec.emotional_tone or "neutral",
            pacing=chapter_spec.pacing,
            special_instructions=special,
            hook_hint=hook,
            target_words=chapter_spec.target_words,
        )
    
    def generate_chapter(
        self,
        chapter_spec: ChapterSpec,
        story_context: StoryContext,
        user_world: Optional[UserWorld] = None,
        location_country: str = "",
    ) -> GeneratedChapter:
        """
        Generiere ein einzelnes Kapitel.
        
        Args:
            chapter_spec: Kapitel-Spezifikation
            story_context: Story-Kontext
            user_world: Optional User World für Personalisierung
            location_country: Land der Location (für Lookup)
        """
        
        # Layer-Type aus Genre ableiten
        layer_type = LayerType.ROMANCE
        if story_context.genre == "thriller":
            layer_type = LayerType.THRILLER
        elif story_context.genre == "mystery":
            layer_type = LayerType.MYSTERY
        
        # Location-Kontext holen
        location_name = chapter_spec.story_location or story_context.primary_location
        location_context = self._get_location_context(
            location_name=location_name,
            country=location_country,
            layer_type=layer_type,
            user_world=user_world,
        )
        
        # Prompts bauen
        system_prompt = self._build_system_prompt(
            genre=story_context.genre,
            target_words=chapter_spec.target_words,
            spice_level=story_context.spice_level,
        )
        
        chapter_prompt = self._build_chapter_prompt(
            chapter_spec=chapter_spec,
            story_context=story_context,
            location_context=location_context,
        )
        
        # Generieren
        if self._client:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=chapter_spec.target_words * 2,
                system=system_prompt,
                messages=[{"role": "user", "content": chapter_prompt}],
            )
            content = response.content[0].text
            model_used = self.model
        else:
            # Mock-Generierung
            content = self._mock_generate(chapter_spec, story_context)
            model_used = "mock"
        
        # Titel generieren falls nicht vorhanden
        title = chapter_spec.title
        if not title:
            title = f"Kapitel {chapter_spec.chapter_number}"
        
        return GeneratedChapter(
            chapter_number=chapter_spec.chapter_number,
            title=title,
            content=content,
            word_count=len(content.split()),
            story_location=chapter_spec.story_location,
            reader_location=chapter_spec.reader_location,
            generated_at=datetime.now().isoformat(),
            model_used=model_used,
        )
    
    def _mock_generate(
        self,
        chapter_spec: ChapterSpec,
        story_context: StoryContext,
    ) -> str:
        """Mock-Generierung für Tests"""
        return f"""[MOCK KAPITEL {chapter_spec.chapter_number}]

{story_context.protagonist_name} stand in {chapter_spec.story_location or story_context.primary_location}.

Die Luft war erfüllt von den Geräuschen der Stadt. {story_context.protagonist_name} 
dachte an alles, was passiert war.

Beat: {chapter_spec.beat_name}
{chapter_spec.beat_description}

[Ende Mock - {chapter_spec.target_words} Wörter Ziel]
"""
    
    def generate_story(
        self,
        chapter_specs: List[ChapterSpec],
        story_context: StoryContext,
        user_world: Optional[UserWorld] = None,
        location_country: str = "",
        progress_callback: Callable[[int, int], None] = None,
    ) -> List[GeneratedChapter]:
        """
        Generiere komplette Story.
        
        Args:
            chapter_specs: Liste von Kapitel-Spezifikationen
            story_context: Story-Kontext
            user_world: Optional User World
            location_country: Land für Location-Lookup
            progress_callback: Optional callback(current, total)
        
        Returns:
            Liste von generierten Kapiteln
        """
        chapters = []
        total = len(chapter_specs)
        
        for i, spec in enumerate(chapter_specs):
            if progress_callback:
                progress_callback(i + 1, total)
            
            chapter = self.generate_chapter(
                chapter_spec=spec,
                story_context=story_context,
                user_world=user_world,
                location_country=location_country,
            )
            chapters.append(chapter)
        
        return chapters
    
    def export_markdown(
        self,
        chapters: List[GeneratedChapter],
        story_context: StoryContext,
        output_path: str,
    ):
        """Exportiere Story als Markdown"""
        
        lines = [
            f"# {story_context.title}",
            f"",
            f"*Genre: {story_context.genre}*",
            f"",
            f"---",
            f"",
        ]
        
        for chapter in chapters:
            lines.append(chapter.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return output_path


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════

def create_story_generator(
    db_config: DatabaseConfig = None,
    use_real_llm: bool = True,
) -> IntegratedStoryGenerator:
    """
    Factory-Funktion für Story-Generator.
    
    Example:
        generator = create_story_generator()
        chapter = generator.generate_chapter(spec, context)
    """
    config = db_config or DatabaseConfig()
    repo = LocationRepository(config)
    repo.connect()
    
    return IntegratedStoryGenerator(
        repository=repo,
        use_real_llm=use_real_llm,
    )
