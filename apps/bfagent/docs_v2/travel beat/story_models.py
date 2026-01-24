"""
Travel Story - Story Mapper
===========================
Mappt Story-Beats auf Reise-Segmente.

Part 1: Story Structure Models
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import date


# ═══════════════════════════════════════════════════════════════
# STORY STRUCTURE ENUMS
# ═══════════════════════════════════════════════════════════════

class StoryAct(Enum):
    """Three-Act Structure"""
    ACT_1 = "act_1"      # Setup (25%)
    ACT_2A = "act_2a"    # Rising Action (25%)
    ACT_2B = "act_2b"    # Complications (25%)
    ACT_3 = "act_3"      # Resolution (25%)


class StoryBeat(Enum):
    """Major story beats"""
    # Act 1
    HOOK = "hook"
    SETUP = "setup"
    INCITING_INCIDENT = "inciting_incident"
    FIRST_PLOT_POINT = "first_plot_point"
    
    # Act 2A
    RISING_ACTION = "rising_action"
    FIRST_PINCH = "first_pinch"
    MIDPOINT = "midpoint"
    
    # Act 2B
    SECOND_PINCH = "second_pinch"
    COMPLICATIONS = "complications"
    DARK_NIGHT = "dark_night"
    SECOND_PLOT_POINT = "second_plot_point"
    
    # Act 3
    CLIMAX_BUILDUP = "climax_buildup"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    FINAL_IMAGE = "final_image"


class PacingType(Enum):
    """Story pacing types"""
    ACTION = "action"           # Fast, tense, page-turner
    EMOTIONAL = "emotional"     # Deep feelings, character moments
    REFLECTIVE = "reflective"   # Internal, thoughtful
    ATMOSPHERIC = "atmospheric" # Descriptive, immersive
    ROMANTIC = "romantic"       # Love scenes, tension
    MYSTERIOUS = "mysterious"   # Suspense, questions


class LocationSyncType(Enum):
    """How story location syncs with reader location"""
    EXACT = "exact"           # Same city/place
    INSPIRED = "inspired"     # Similar atmosphere
    METAPHORICAL = "metaphorical"  # Thematic connection
    INDEPENDENT = "independent"    # No connection


# ═══════════════════════════════════════════════════════════════
# STORY STRUCTURE CONSTANTS
# ═══════════════════════════════════════════════════════════════

# Act distribution (percentage of total words)
ACT_DISTRIBUTION = {
    StoryAct.ACT_1: 0.25,
    StoryAct.ACT_2A: 0.25,
    StoryAct.ACT_2B: 0.25,
    StoryAct.ACT_3: 0.25,
}

# Beats within each act (with relative weight within act)
BEATS_BY_ACT = {
    StoryAct.ACT_1: [
        (StoryBeat.HOOK, 0.15),
        (StoryBeat.SETUP, 0.40),
        (StoryBeat.INCITING_INCIDENT, 0.25),
        (StoryBeat.FIRST_PLOT_POINT, 0.20),
    ],
    StoryAct.ACT_2A: [
        (StoryBeat.RISING_ACTION, 0.35),
        (StoryBeat.FIRST_PINCH, 0.25),
        (StoryBeat.MIDPOINT, 0.40),
    ],
    StoryAct.ACT_2B: [
        (StoryBeat.SECOND_PINCH, 0.20),
        (StoryBeat.COMPLICATIONS, 0.35),
        (StoryBeat.DARK_NIGHT, 0.25),
        (StoryBeat.SECOND_PLOT_POINT, 0.20),
    ],
    StoryAct.ACT_3: [
        (StoryBeat.CLIMAX_BUILDUP, 0.25),
        (StoryBeat.CLIMAX, 0.35),
        (StoryBeat.RESOLUTION, 0.25),
        (StoryBeat.FINAL_IMAGE, 0.15),
    ],
}

# Beat descriptions for story generation
BEAT_DESCRIPTIONS = {
    StoryBeat.HOOK: "Greife den Leser sofort. Stelle eine Frage, zeige Konflikt oder Geheimnis.",
    StoryBeat.SETUP: "Etabliere Protagonist, Welt, Status Quo. Zeige was auf dem Spiel steht.",
    StoryBeat.INCITING_INCIDENT: "Das Ereignis, das alles verändert. Kein Zurück mehr.",
    StoryBeat.FIRST_PLOT_POINT: "Protagonist trifft Entscheidung, die Reise beginnt wirklich.",
    
    StoryBeat.RISING_ACTION: "Neue Welt erkunden, Hindernisse überwinden, Beziehungen aufbauen.",
    StoryBeat.FIRST_PINCH: "Erster größerer Rückschlag. Antagonist zeigt Stärke.",
    StoryBeat.MIDPOINT: "WENDEPUNKT. Neue Information verändert alles. Vom Reagieren zum Agieren.",
    
    StoryBeat.SECOND_PINCH: "Zweiter Rückschlag. Alles scheint verloren.",
    StoryBeat.COMPLICATIONS: "Probleme eskalieren, Beziehungen werden getestet.",
    StoryBeat.DARK_NIGHT: "Tiefpunkt. Protagonist muss sich inneren Dämonen stellen.",
    StoryBeat.SECOND_PLOT_POINT: "Letzte Information/Erkenntnis für den finalen Kampf.",
    
    StoryBeat.CLIMAX_BUILDUP: "Alle Fäden laufen zusammen. Vorbereitung auf Konfrontation.",
    StoryBeat.CLIMAX: "Der finale Konflikt. Protagonist muss alles geben.",
    StoryBeat.RESOLUTION: "Nachwirkungen. Neue Normalität etabliert sich.",
    StoryBeat.FINAL_IMAGE: "Letztes Bild spiegelt erstes, zeigt Transformation.",
}

# Optimal pacing for each beat
BEAT_PACING = {
    StoryBeat.HOOK: PacingType.ACTION,
    StoryBeat.SETUP: PacingType.ATMOSPHERIC,
    StoryBeat.INCITING_INCIDENT: PacingType.ACTION,
    StoryBeat.FIRST_PLOT_POINT: PacingType.EMOTIONAL,
    
    StoryBeat.RISING_ACTION: PacingType.ATMOSPHERIC,
    StoryBeat.FIRST_PINCH: PacingType.ACTION,
    StoryBeat.MIDPOINT: PacingType.ACTION,
    
    StoryBeat.SECOND_PINCH: PacingType.ACTION,
    StoryBeat.COMPLICATIONS: PacingType.EMOTIONAL,
    StoryBeat.DARK_NIGHT: PacingType.EMOTIONAL,
    StoryBeat.SECOND_PLOT_POINT: PacingType.REFLECTIVE,
    
    StoryBeat.CLIMAX_BUILDUP: PacingType.ACTION,
    StoryBeat.CLIMAX: PacingType.ACTION,
    StoryBeat.RESOLUTION: PacingType.EMOTIONAL,
    StoryBeat.FINAL_IMAGE: PacingType.REFLECTIVE,
}


# ═══════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════

@dataclass
class ChapterOutline:
    """Outline for a single chapter"""
    chapter_number: int
    title: Optional[str] = None
    word_target: int = 3000
    
    # Story position
    act: StoryAct = StoryAct.ACT_1
    beats: List[StoryBeat] = field(default_factory=list)
    
    # Location & Sync
    story_location: str = ""
    reader_location: str = ""
    location_sync: LocationSyncType = LocationSyncType.EXACT
    
    # Pacing & Tone
    pacing: PacingType = PacingType.ATMOSPHERIC
    emotional_tone: str = ""
    
    # Reading context
    reading_date: Optional[date] = None
    reading_context: str = ""  # "transport", "evening", etc.
    
    # Content hints
    beat_description: str = ""
    chapter_end_hook: str = ""
    special_instructions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "chapter_number": self.chapter_number,
            "title": self.title,
            "word_target": self.word_target,
            "act": self.act.value,
            "beats": [b.value for b in self.beats],
            "story_location": self.story_location,
            "reader_location": self.reader_location,
            "location_sync": self.location_sync.value,
            "pacing": self.pacing.value,
            "emotional_tone": self.emotional_tone,
            "reading_date": self.reading_date.isoformat() if self.reading_date else None,
            "reading_context": self.reading_context,
            "beat_description": self.beat_description,
            "chapter_end_hook": self.chapter_end_hook,
            "special_instructions": self.special_instructions,
        }


@dataclass
class StoryOutline:
    """Complete story outline mapped to travel"""
    title: str
    total_words: int
    total_chapters: int
    chapters: List[ChapterOutline] = field(default_factory=list)
    
    # Metadata
    genre: str = ""
    location_sync_mode: LocationSyncType = LocationSyncType.EXACT
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "total_words": self.total_words,
            "total_chapters": self.total_chapters,
            "genre": self.genre,
            "location_sync_mode": self.location_sync_mode.value,
            "chapters": [ch.to_dict() for ch in self.chapters],
            "act_summary": self._get_act_summary(),
        }
    
    def _get_act_summary(self) -> Dict:
        """Summarize chapters per act"""
        summary = {}
        for act in StoryAct:
            act_chapters = [ch for ch in self.chapters if ch.act == act]
            summary[act.value] = {
                "chapters": [ch.chapter_number for ch in act_chapters],
                "word_count": sum(ch.word_target for ch in act_chapters),
            }
        return summary


@dataclass 
class StoryPreferences:
    """User's story preferences from form"""
    genre: str = "romantic_suspense"
    spice_level: str = "mild"  # none, mild, moderate, spicy
    location_sync: str = "exact"  # exact, inspired, different
    ending: str = "happy"  # happy, hopeful, bittersweet, surprise
    triggers_avoid: List[str] = field(default_factory=list)
