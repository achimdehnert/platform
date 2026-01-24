"""
Travel Story - Story Agent
==========================
Generiert Kapitel basierend auf Story-Outline.

Part 1: Prompt Templates
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from story_models import (
    ChapterOutline, StoryOutline, StoryPreferences,
    StoryAct, StoryBeat, PacingType,
)


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Du bist ein erfahrener Romanautor, spezialisiert auf {genre}.

DEINE AUFGABE:
Du schreibst Kapitel für eine personalisierte Reise-Geschichte. Die Story ist synchronisiert 
mit der echten Reise des Lesers - wenn der Leser in Barcelona ist, spielt das Kapitel in Barcelona.

DEIN STIL:
- Lebendige, sinnliche Beschreibungen der Orte
- Authentische Dialoge
- Show, don't tell
- Emotionale Tiefe
- Page-Turner Qualität

WICHTIGE REGELN:
1. Halte dich EXAKT an die Wort-Vorgabe (±10%)
2. Nutze die echten Orte und Details der Reiseziele
3. Passe das Pacing an den Lesekontext an
4. Ende jedes Kapitel mit einem Hook
5. Vermeide die angegebenen Trigger-Themen

GENRE-SPEZIFISCH ({genre}):
{genre_instructions}

SPICE-LEVEL: {spice_level}
{spice_instructions}
"""

GENRE_INSTRUCTIONS = {
    "romance": """
- Fokus auf emotionale Entwicklung der Beziehung
- Spannung durch Missverständnisse, Hindernisse, unausgesprochene Gefühle
- Tender moments und grand gestures
- Befriedigender emotionaler Payoff
""",
    "thriller": """
- Konstante Spannung und Bedrohung
- Cliffhanger an Kapitelenden
- Rote Heringe und Überraschungen
- Protagonist in Gefahr
- Schnelles Pacing in Action-Szenen
""",
    "romantic_suspense": """
- Balance zwischen Romance und Spannung
- Beziehungsentwicklung während der Gefahr
- Protagonist und Love Interest als Team
- Romantische Szenen als Kontrast zur Spannung
- Emotional stakes UND physical stakes
""",
    "mystery": """
- Hinweise geschickt einstreuen
- Atmosphärische Beschreibungen
- Verdächtige Charaktere
- Puzzle-Elemente für den Leser
- Befriedigende Auflösung
""",
    "cozy": """
- Warme, einladende Atmosphäre
- Liebenswerte Charaktere
- Leichte Konflikte, keine echte Gefahr
- Feel-good Momente
- Kulinarische und kulturelle Details
""",
}

SPICE_INSTRUCTIONS = {
    "none": "Keine romantischen/intimen Szenen. Beziehung bleibt auf emotionaler Ebene.",
    "mild": "Küsse und Umarmungen OK. Intimität angedeutet, 'Fade to Black' vor expliziten Szenen.",
    "moderate": "Tastvolle intime Szenen erlaubt. Fokus auf Emotionen und Verbindung, nicht nur Physisches.",
    "spicy": "Explizite Szenen erlaubt. Detaillierte Beschreibungen von Intimität. Consent immer klar.",
}


# ═══════════════════════════════════════════════════════════════
# CHAPTER PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════

CHAPTER_PROMPT = """
# KAPITEL {chapter_number} SCHREIBEN

## STORY-KONTEXT
{story_context}

## VORHERIGES KAPITEL (Zusammenfassung)
{previous_summary}

## DIESES KAPITEL

### Technische Vorgaben
- **Wörter**: {word_target} (±10%)
- **Akt**: {act}
- **Beat**: {beat}
- **Pacing**: {pacing}

### Orts-Synchronisation
- **Leser ist gerade in**: {reader_location}
- **Story spielt in**: {story_location}
- **Sync-Typ**: {location_sync}

### Lesekontext
- **Datum**: {reading_date}
- **Leser liest**: {reading_context}
- **Atmosphäre anpassen an**: {context_atmosphere}

### Emotionaler Ton
{emotional_tone}

### Beat-Beschreibung
{beat_description}

### Spezielle Anweisungen
{special_instructions}

### Kapitel-Ende
{chapter_end_hook}

## CHARAKTERE IN DIESEM KAPITEL
{characters}

## OFFENE PLOT-THREADS
{plot_threads}

---

SCHREIBE JETZT KAPITEL {chapter_number}:
"""


# ═══════════════════════════════════════════════════════════════
# CONTEXT ATMOSPHERE BY READING CONTEXT
# ═══════════════════════════════════════════════════════════════

CONTEXT_ATMOSPHERE = {
    "transport": """
Der Leser sitzt im Flugzeug/Zug. 
- Halte Spannung hoch, um Ablenkungen zu überwinden
- Kurze, punchy Absätze
- Cliffhanger-Momente
- Action oder intensive Dialoge
""",
    "morning": """
Der Leser liest morgens vor dem Aufstehen.
- Sanfter Einstieg
- Reflexive Momente des Protagonisten
- Setup für den Tag
- Nicht zu intensiv
""",
    "evening": """
Der Leser liest abends im Bett.
- Emotionale Tiefe erlaubt
- Längere, immersive Beschreibungen
- Intime Momente passend
- Kann intensiver sein
""",
    "pool": """
Der Leser entspannt am Pool/Strand.
- Atmosphärisch und sinnlich
- Entspanntes Tempo
- Beschreibungen von Wärme, Sonne, Wasser
- Leichte, genussvolle Szenen
""",
    "cafe": """
Der Leser sitzt in einem Café.
- Atmosphärische Beschreibungen
- Dialoglastig
- Beobachtungen der Umgebung
- Mittleres Tempo
""",
    "waiting": """
Der Leser wartet (Flughafen, Restaurant, etc.)
- Schnelles Pacing
- Page-Turner Qualität
- Kurze Kapitelabschnitte
- Cliffhanger
""",
}


# ═══════════════════════════════════════════════════════════════
# PROMPT BUILDER CLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class StoryContext:
    """Accumulated story context for generation"""
    title: str
    genre: str
    protagonist_name: str
    protagonist_description: str
    setting_description: str
    central_conflict: str
    love_interest_name: Optional[str] = None
    love_interest_description: Optional[str] = None
    antagonist_name: Optional[str] = None
    antagonist_description: Optional[str] = None
    
    def to_prompt(self) -> str:
        lines = [
            f"**Titel**: {self.title}",
            f"**Genre**: {self.genre}",
            f"**Protagonist**: {self.protagonist_name} - {self.protagonist_description}",
            f"**Setting**: {self.setting_description}",
            f"**Zentraler Konflikt**: {self.central_conflict}",
        ]
        if self.love_interest_name:
            lines.append(f"**Love Interest**: {self.love_interest_name} - {self.love_interest_description}")
        if self.antagonist_name:
            lines.append(f"**Antagonist**: {self.antagonist_name} - {self.antagonist_description}")
        return "\n".join(lines)


@dataclass
class ChapterState:
    """State tracking for chapter generation"""
    chapter_summaries: Dict[int, str]  # chapter_number -> summary
    plot_threads: List[str]  # Active plot threads
    character_states: Dict[str, str]  # character_name -> current state
    
    def get_previous_summary(self, chapter_number: int) -> str:
        if chapter_number <= 1:
            return "Dies ist das erste Kapitel."
        prev = chapter_number - 1
        return self.chapter_summaries.get(prev, f"[Zusammenfassung Kapitel {prev} fehlt]")
    
    def get_plot_threads(self) -> str:
        if not self.plot_threads:
            return "Noch keine offenen Threads."
        return "\n".join(f"- {thread}" for thread in self.plot_threads)
    
    def get_characters(self) -> str:
        if not self.character_states:
            return "Charaktere werden in diesem Kapitel eingeführt."
        return "\n".join(f"- **{name}**: {state}" for name, state in self.character_states.items())


class PromptBuilder:
    """
    Builds prompts for chapter generation.
    """
    
    def __init__(
        self,
        story_outline: StoryOutline,
        story_context: StoryContext,
        story_preferences: StoryPreferences,
    ):
        self.outline = story_outline
        self.context = story_context
        self.preferences = story_preferences
        
        # Initialize state
        self.state = ChapterState(
            chapter_summaries={},
            plot_threads=[],
            character_states={},
        )
    
    def build_system_prompt(self) -> str:
        """Build the system prompt for the LLM"""
        genre = self.preferences.genre
        genre_instructions = GENRE_INSTRUCTIONS.get(genre, GENRE_INSTRUCTIONS["romantic_suspense"])
        spice_instructions = SPICE_INSTRUCTIONS.get(self.preferences.spice_level, SPICE_INSTRUCTIONS["mild"])
        
        return SYSTEM_PROMPT.format(
            genre=genre,
            genre_instructions=genre_instructions,
            spice_level=self.preferences.spice_level,
            spice_instructions=spice_instructions,
        )
    
    def build_chapter_prompt(self, chapter: ChapterOutline) -> str:
        """Build the prompt for a specific chapter"""
        
        # Get context atmosphere
        context_atm = CONTEXT_ATMOSPHERE.get(
            chapter.reading_context, 
            CONTEXT_ATMOSPHERE["evening"]
        )
        
        # Format special instructions
        special_instr = "\n".join(f"- {instr}" for instr in chapter.special_instructions) \
            if chapter.special_instructions else "Keine besonderen Anweisungen."
        
        # Format beat
        beat_str = ", ".join(b.value for b in chapter.beats) if chapter.beats else "—"
        
        return CHAPTER_PROMPT.format(
            chapter_number=chapter.chapter_number,
            story_context=self.context.to_prompt(),
            previous_summary=self.state.get_previous_summary(chapter.chapter_number),
            word_target=chapter.word_target,
            act=chapter.act.value,
            beat=beat_str,
            pacing=chapter.pacing.value,
            reader_location=chapter.reader_location,
            story_location=chapter.story_location,
            location_sync=chapter.location_sync.value,
            reading_date=chapter.reading_date,
            reading_context=chapter.reading_context,
            context_atmosphere=context_atm,
            emotional_tone=chapter.emotional_tone,
            beat_description=chapter.beat_description,
            special_instructions=special_instr,
            chapter_end_hook=chapter.chapter_end_hook,
            characters=self.state.get_characters(),
            plot_threads=self.state.get_plot_threads(),
        )
    
    def update_state(
        self, 
        chapter_number: int, 
        summary: str,
        new_plot_threads: List[str] = None,
        resolved_threads: List[str] = None,
        character_updates: Dict[str, str] = None,
    ):
        """Update state after chapter generation"""
        self.state.chapter_summaries[chapter_number] = summary
        
        if new_plot_threads:
            self.state.plot_threads.extend(new_plot_threads)
        
        if resolved_threads:
            for thread in resolved_threads:
                if thread in self.state.plot_threads:
                    self.state.plot_threads.remove(thread)
        
        if character_updates:
            self.state.character_states.update(character_updates)


# ═══════════════════════════════════════════════════════════════
# SUMMARY EXTRACTION PROMPT
# ═══════════════════════════════════════════════════════════════

SUMMARY_PROMPT = """
Analysiere das folgende Kapitel und extrahiere:

1. **Zusammenfassung** (2-3 Sätze): Was passiert in diesem Kapitel?
2. **Neue Plot-Threads**: Welche neuen Fragen/Konflikte wurden eröffnet?
3. **Gelöste Threads**: Welche Fragen wurden beantwortet?
4. **Charakter-Updates**: Wie haben sich die Charaktere verändert?

KAPITEL:
{chapter_text}

Antworte im folgenden JSON-Format:
```json
{{
    "summary": "...",
    "new_plot_threads": ["...", "..."],
    "resolved_threads": ["...", "..."],
    "character_updates": {{
        "Name": "Aktueller Zustand/Entwicklung"
    }}
}}
```
"""


# ═══════════════════════════════════════════════════════════════
# LOCATION DETAIL PROMPTS
# ═══════════════════════════════════════════════════════════════

LOCATION_RESEARCH_PROMPT = """
Recherchiere Details über {location} für eine Romanszene.

Liefere:
1. **Atmosphäre**: Wie fühlt sich der Ort an? Gerüche, Geräusche, Licht?
2. **Bekannte Orte**: 3-5 spezifische Orte (Plätze, Cafés, Straßen) die authentisch sind
3. **Lokale Details**: Typische Speisen, Getränke, Bräuche
4. **Romantische Spots**: Orte für romantische Szenen
5. **Spannungsorte**: Orte für Thriller-Szenen (dunkle Gassen, verlassene Plätze)

Fokus auf: {focus_aspect}
Genre: {genre}
"""
