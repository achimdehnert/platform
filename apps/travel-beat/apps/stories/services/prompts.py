"""
Prompt Builder - LLM Prompts for Story Generation

Builds structured prompts for Claude API based on:
- Trip data (locations, dates, transport)
- User preferences (genre, spice level, triggers)
- Story structure (beats, pacing)
- Location data (atmosphere, details)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StoryContext:
    """Context for story generation."""
    genre: str
    spice_level: str
    ending_type: str
    protagonist_gender: str
    protagonist_name: str
    total_chapters: int
    total_words: int
    triggers_avoid: list[str]
    user_notes: str = ""


@dataclass
class ChapterContext:
    """Context for single chapter generation."""
    chapter_number: int
    location_name: str
    location_city: str
    location_country: str
    location_atmosphere: str
    location_details: dict
    date: str
    pacing_type: str  # action, emotional, reflective, transitional
    story_beat: str
    word_count: int
    previous_summary: str = ""
    characters_present: list[str] = None
    

class PromptBuilder:
    """Builds prompts for Claude API."""
    
    SYSTEM_PROMPT = """Du bist ein erfahrener Autor für personalisierte Reise-Geschichten.
Du schreibst fesselnde Geschichten, die an echten Orten spielen und authentische Details verwenden.

WICHTIGE REGELN:
1. Die Geschichte spielt IMMER am angegebenen Ort mit korrekten lokalen Details
2. Schreibe in der dritten Person, Vergangenheit
3. Verwende lebendige, sensorische Beschreibungen
4. Integriere lokale Kultur, Sprache und Atmosphäre
5. Halte das Genre und den Ton konsistent
6. Respektiere Trigger-Warnungen und vermeide genannte Themen
7. Jedes Kapitel endet mit einem Hook für das nächste"""

    GENRE_PROMPTS = {
        'romance': """GENRE: Romance
- Fokus auf emotionale Entwicklung und Beziehungsdynamik
- Romantische Spannung und "Slow Burn" aufbauen
- Herzerwärmende Momente mit dem Setting verbinden
- Happy End oder Hopeful End""",
        
        'romantic_suspense': """GENRE: Romantic Suspense
- Balance zwischen Romantik und Spannung
- Geheimnisse und Enthüllungen einstreuen
- Protagonist:in in gefährliche Situationen bringen
- Romantische Entwicklung unter Druck""",
        
        'thriller': """GENRE: Thriller
- Konstante Spannung und Tempo
- Plot-Twists und Überraschungen
- Gefahr fühlt sich real und unmittelbar an
- Cliffhanger am Kapitelende""",
        
        'mystery': """GENRE: Mystery
- Rätsel und Hinweise geschickt einstreuen
- Lokale Geschichte und Geheimnisse nutzen
- Leser zum Mitraten einladen
- Überraschende aber faire Auflösung""",
        
        'fantasy': """GENRE: Urban Fantasy
- Magische Elemente subtil in reale Welt einweben
- Lokale Mythen und Legenden nutzen
- Sense of Wonder beibehalten
- Worldbuilding konsistent halten""",
        
        'adventure': """GENRE: Adventure
- Action und Erkundung im Vordergrund
- Herausforderungen und Hindernisse
- Kulturelle Entdeckungen
- Protagonist:in wächst durch Erfahrungen""",
    }
    
    SPICE_LEVELS = {
        'sweet': "Romantik bleibt bei Händchenhalten, zärtlichen Blicken und einem Kuss.",
        'mild': "Küsse und leichte Intimität sind erlaubt, aber Türen schließen sich.",
        'medium': "Sinnliche Szenen mit emotionaler Tiefe, aber nicht explizit.",
        'spicy': "Explizitere Szenen erlaubt, aber immer mit emotionalem Kontext.",
    }
    
    PACING_GUIDES = {
        'action': "Schnelles Tempo, kurze Sätze, physische Bewegung, Spannung.",
        'emotional': "Tiefe Gefühle, innere Monologe, bedeutsame Dialoge.",
        'reflective': "Ruhiger Moment, Nachdenken, Charakterentwicklung.",
        'transitional': "Verbindung zwischen Szenen, Reise, neue Informationen.",
        'climax': "Höhepunkt der Spannung, alles kommt zusammen.",
        'resolution': "Auflösung, emotionale Befriedigung, Abschluss.",
    }
    
    STORY_BEATS = {
        # Act 1
        'opening_image': "Eröffnungsbild: Zeige die normale Welt der Protagonist:in",
        'setup': "Setup: Etabliere Charakter, Welt, Ausgangssituation",
        'catalyst': "Katalysator: Ein Ereignis verändert alles",
        'debate': "Debatte: Innerer Konflikt, Zögern vor der Reise",
        
        # Act 2A
        'break_into_two': "Aufbruch: Die Protagonist:in betritt die neue Welt",
        'b_story': "B-Story: Neue Beziehung beginnt (oft Love Interest)",
        'fun_and_games': "Fun & Games: Versprechen der Prämisse, Genre-typische Szenen",
        'midpoint': "Midpoint: Falscher Sieg oder Niederlage, Stakes erhöhen",
        
        # Act 2B
        'bad_guys_close_in': "Antagonist nähert sich: Druck steigt",
        'all_is_lost': "Alles verloren: Tiefpunkt, scheint unmöglich",
        'dark_night': "Dunkle Nacht der Seele: Reflexion, innere Wandlung beginnt",
        
        # Act 3
        'break_into_three': "Aufbruch in Akt 3: Neue Entschlossenheit, Plan",
        'finale': "Finale: Konfrontation, alles kommt zusammen",
        'final_image': "Schlussbild: Zeige die Veränderung, neue Normalität",
    }
    
    @classmethod
    def build_story_outline_prompt(cls, context: StoryContext, locations: list[dict]) -> str:
        """Build prompt for generating story outline."""
        
        genre_guide = cls.GENRE_PROMPTS.get(context.genre, cls.GENRE_PROMPTS['romance'])
        spice_guide = cls.SPICE_LEVELS.get(context.spice_level, cls.SPICE_LEVELS['mild'])
        
        locations_text = "\n".join([
            f"- Tag {i+1}: {loc['city']}, {loc['country']} ({loc.get('atmosphere', 'neutral')})"
            for i, loc in enumerate(locations)
        ])
        
        triggers_text = ", ".join(context.triggers_avoid) if context.triggers_avoid else "Keine"
        
        prompt = f"""Erstelle eine detaillierte Story-Outline für eine personalisierte Reise-Geschichte.

{genre_guide}

SPICE LEVEL: {context.spice_level}
{spice_guide}

PROTAGONIST:IN:
- Name: {context.protagonist_name}
- Geschlecht: {context.protagonist_gender}

REISE-ROUTE:
{locations_text}

STORY-PARAMETER:
- Kapitelanzahl: {context.total_chapters}
- Gesamtwörter: ~{context.total_words}
- Ending: {context.ending_type}
- Zu vermeiden: {triggers_text}

{f"USER NOTIZEN: {context.user_notes}" if context.user_notes else ""}

Erstelle eine Outline mit:
1. Logline (1 Satz)
2. Synopsis (3-5 Sätze)
3. Hauptkonflikt
4. Charaktere (Protagonist, Love Interest/Antagonist, 2-3 Nebenfiguren)
5. Kapitel-Breakdown mit:
   - Kapitel-Nummer
   - Location
   - Story Beat
   - Pacing Type
   - Kurze Beschreibung (2-3 Sätze)
   - Hook zum nächsten Kapitel

Antworte im JSON-Format."""

        return prompt
    
    @classmethod
    def build_chapter_prompt(cls, story_context: StoryContext, chapter_context: ChapterContext) -> str:
        """Build prompt for generating a single chapter."""
        
        genre_guide = cls.GENRE_PROMPTS.get(story_context.genre, cls.GENRE_PROMPTS['romance'])
        spice_guide = cls.SPICE_LEVELS.get(story_context.spice_level, cls.SPICE_LEVELS['mild'])
        pacing_guide = cls.PACING_GUIDES.get(chapter_context.pacing_type, "")
        beat_guide = cls.STORY_BEATS.get(chapter_context.story_beat, "")
        
        triggers_text = ", ".join(story_context.triggers_avoid) if story_context.triggers_avoid else "Keine"
        
        prompt = f"""Schreibe Kapitel {chapter_context.chapter_number} der Geschichte.

{genre_guide}

SPICE LEVEL: {story_context.spice_level}
{spice_guide}

LOCATION:
- Ort: {chapter_context.location_name}
- Stadt: {chapter_context.location_city}, {chapter_context.location_country}
- Atmosphäre: {chapter_context.location_atmosphere}
- Datum in der Geschichte: {chapter_context.date}

LOCATION DETAILS:
{chapter_context.location_details}

STORY BEAT: {chapter_context.story_beat}
{beat_guide}

PACING: {chapter_context.pacing_type}
{pacing_guide}

ZIEL-WORTANZAHL: ~{chapter_context.word_count} Wörter

{f"VORHERIGES KAPITEL: {chapter_context.previous_summary}" if chapter_context.previous_summary else "Dies ist das erste Kapitel."}

ZU VERMEIDEN: {triggers_text}

ANWEISUNGEN:
1. Beginne mit einer fesselnden Eröffnung
2. Nutze die Location authentisch und detailliert
3. Halte das Pacing entsprechend dem Typ
4. Entwickle Charaktere und Beziehungen weiter
5. Ende mit einem Hook für das nächste Kapitel
6. Schreibe ~{chapter_context.word_count} Wörter

Antworte NUR mit dem Kapiteltext, ohne Metadaten oder Kommentare."""

        return prompt
    
    @classmethod
    def build_location_research_prompt(cls, city: str, country: str, genre: str) -> str:
        """Build prompt for researching a location."""
        
        genre_focus = {
            'romance': "romantische Orte, Cafés, Parks, Aussichtspunkte, versteckte Ecken",
            'thriller': "dunkle Gassen, historische Gebäude, verlassene Orte, Verstecke",
            'mystery': "historische Stätten, lokale Legenden, Geheimnisse, alte Gebäude",
            'fantasy': "mystische Orte, alte Bäume, Brunnen, Plätze mit Geschichte",
            'adventure': "Märkte, Berge, Gewässer, Aussichtspunkte, Geheimtipps",
        }.get(genre, "interessante Orte, lokale Kultur, Atmosphäre")
        
        prompt = f"""Recherchiere {city}, {country} für eine {genre}-Geschichte.

FOKUS: {genre_focus}

Liefere für 5-7 spezifische Orte:
1. Name des Ortes
2. Typ (Café, Park, Straße, Gebäude, etc.)
3. Atmosphäre (Tags: romantisch, mysteriös, lebendig, etc.)
4. Sensorische Details (Gerüche, Geräusche, Texturen)
5. Lokale Besonderheiten (Sprache, Kultur, Traditionen)
6. Beste Zeit (Morgen, Abend, Nacht)
7. Story-Potenzial (was könnte hier passieren?)

Sei spezifisch mit echten Ortsnamen und authentischen Details.
Antworte im JSON-Format."""

        return prompt
