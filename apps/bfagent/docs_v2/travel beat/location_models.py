"""
Travel Story - Location Database
================================
On-Demand Location System mit User-Welten.

Part 1: Datenmodelle für die 3-Schichten-Architektur
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import json


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════

class LayerType(Enum):
    """Genre/Interest Layer Types"""
    ROMANCE = "romance"
    THRILLER = "thriller"
    MYSTERY = "mystery"
    FOODIE = "foodie"
    ART = "art"
    HISTORY = "history"
    ADVENTURE = "adventure"
    NIGHTLIFE = "nightlife"
    NATURE = "nature"
    SPIRITUAL = "spiritual"


class PlaceType(Enum):
    """Types of places"""
    RESTAURANT = "restaurant"
    BAR = "bar"
    CAFE = "cafe"
    HOTEL = "hotel"
    MUSEUM = "museum"
    LANDMARK = "landmark"
    VIEWPOINT = "viewpoint"
    PARK = "park"
    BEACH = "beach"
    STREET = "street"
    PLAZA = "plaza"
    MARKET = "market"
    CHURCH = "church"
    HIDDEN_GEM = "hidden_gem"
    DANGER_SPOT = "danger_spot"  # Für Thriller


class TimeOfDay(Enum):
    """Time contexts for atmospheres"""
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    DAWN = "dawn"
    DUSK = "dusk"


# ═══════════════════════════════════════════════════════════════
# SCHICHT 1: BASE_LOCATION (shared)
# ═══════════════════════════════════════════════════════════════

@dataclass
class District:
    """Ein Stadtviertel/Bezirk"""
    name: str
    local_name: Optional[str] = None  # z.B. "Barri Gòtic"
    vibe: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "local_name": self.local_name,
            "vibe": self.vibe,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "District":
        return cls(**data)


@dataclass
class BaseLocation:
    """
    SCHICHT 1: Basis-Informationen über einen Ort.
    Shared für alle User, einmal generiert.
    """
    id: str  # z.B. "barcelona", "rom", "paris"
    name: str
    country: str
    region: Optional[str] = None
    
    # Geographie
    coordinates: Optional[tuple] = None  # (lat, lon)
    timezone: str = "UTC"
    
    # Sprache & Kultur
    languages: List[str] = field(default_factory=list)
    currency: str = "EUR"
    
    # Klima
    climate: str = ""
    best_seasons: List[str] = field(default_factory=list)
    
    # Struktur
    districts: List[District] = field(default_factory=list)
    
    # Basis-Fakten
    population: Optional[int] = None
    known_for: List[str] = field(default_factory=list)
    
    # Metadaten
    generated_at: str = ""
    source: str = "web_research"
    quality_score: float = 0.0
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "region": self.region,
            "coordinates": self.coordinates,
            "timezone": self.timezone,
            "languages": self.languages,
            "currency": self.currency,
            "climate": self.climate,
            "best_seasons": self.best_seasons,
            "districts": [d.to_dict() for d in self.districts],
            "population": self.population,
            "known_for": self.known_for,
            "generated_at": self.generated_at,
            "source": self.source,
            "quality_score": self.quality_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "BaseLocation":
        data = data.copy()
        if "districts" in data:
            data["districts"] = [District.from_dict(d) for d in data["districts"]]
        if "coordinates" in data and data["coordinates"]:
            data["coordinates"] = tuple(data["coordinates"])
        return cls(**data)


# ═══════════════════════════════════════════════════════════════
# SCHICHT 2: LOCATION_LAYER (shared, genre-spezifisch)
# ═══════════════════════════════════════════════════════════════

@dataclass
class LayerPlace:
    """Ein Ort innerhalb eines Layers"""
    name: str
    place_type: PlaceType
    district: Optional[str] = None
    
    # Bewertung für dieses Genre
    relevance_score: int = 3  # 1-5
    
    # Beschreibungen
    description: str = ""
    atmosphere: str = ""
    story_potential: str = ""  # Wie kann dieser Ort in einer Story verwendet werden?
    
    # Spezifische Details
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "place_type": self.place_type.value,
            "district": self.district,
            "relevance_score": self.relevance_score,
            "description": self.description,
            "atmosphere": self.atmosphere,
            "story_potential": self.story_potential,
            "details": self.details,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LayerPlace":
        data = data.copy()
        data["place_type"] = PlaceType(data["place_type"])
        return cls(**data)


@dataclass
class SensoryDetails:
    """Sensorische Details für einen Layer"""
    smells: List[str] = field(default_factory=list)
    sounds: List[str] = field(default_factory=list)
    textures: List[str] = field(default_factory=list)
    tastes: List[str] = field(default_factory=list)
    visuals: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "smells": self.smells,
            "sounds": self.sounds,
            "textures": self.textures,
            "tastes": self.tastes,
            "visuals": self.visuals,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SensoryDetails":
        return cls(**data)


@dataclass
class LocationLayer:
    """
    SCHICHT 2: Genre/Interest-spezifische Informationen.
    Shared für alle User mit diesem Genre.
    """
    location_id: str  # Referenz zu BaseLocation
    layer_type: LayerType
    
    # Atmosphären nach Tageszeit
    atmospheres: Dict[str, str] = field(default_factory=dict)  # TimeOfDay -> Description
    
    # Genre-spezifische Orte
    places: List[LayerPlace] = field(default_factory=list)
    
    # Sensorische Details
    sensory: SensoryDetails = field(default_factory=SensoryDetails)
    
    # Story-Hooks für dieses Genre
    story_hooks: List[str] = field(default_factory=list)
    
    # Typische Szenen-Settings
    scene_settings: List[str] = field(default_factory=list)
    
    # Konflikte/Gefahren (besonders für Thriller)
    potential_conflicts: List[str] = field(default_factory=list)
    
    # Metadaten
    generated_at: str = ""
    quality_score: float = 0.0
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "location_id": self.location_id,
            "layer_type": self.layer_type.value,
            "atmospheres": self.atmospheres,
            "places": [p.to_dict() for p in self.places],
            "sensory": self.sensory.to_dict(),
            "story_hooks": self.story_hooks,
            "scene_settings": self.scene_settings,
            "potential_conflicts": self.potential_conflicts,
            "generated_at": self.generated_at,
            "quality_score": self.quality_score,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LocationLayer":
        data = data.copy()
        data["layer_type"] = LayerType(data["layer_type"])
        data["places"] = [LayerPlace.from_dict(p) for p in data.get("places", [])]
        data["sensory"] = SensoryDetails.from_dict(data.get("sensory", {}))
        return cls(**data)


# ═══════════════════════════════════════════════════════════════
# SCHICHT 3: USER_WORLD (user-spezifisch)
# ═══════════════════════════════════════════════════════════════

@dataclass
class PersonalPlace:
    """Ein persönlicher Ort des Users"""
    location_id: str
    name: str
    place_type: PlaceType
    note: str = ""  # Persönliche Notiz
    use_in_story: bool = True  # False = Ausschluss
    sentiment: str = "positive"  # positive, negative, neutral
    
    def to_dict(self) -> Dict:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "place_type": self.place_type.value,
            "note": self.note,
            "use_in_story": self.use_in_story,
            "sentiment": self.sentiment,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PersonalPlace":
        data = data.copy()
        data["place_type"] = PlaceType(data["place_type"])
        return cls(**data)


@dataclass
class StoryCharacter:
    """Ein Charakter aus User's Story-Universum"""
    name: str
    full_name: Optional[str] = None
    introduced_in: Optional[str] = None  # story_id
    role: str = "protagonist"  # protagonist, love_interest, antagonist, supporting
    current_status: str = ""
    known_facts: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)  # character_name -> relationship
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "introduced_in": self.introduced_in,
            "role": self.role,
            "current_status": self.current_status,
            "known_facts": self.known_facts,
            "relationships": self.relationships,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "StoryCharacter":
        return cls(**data)


@dataclass
class LocationMemory:
    """Eine Erinnerung an einem Ort aus einer früheren Story"""
    location_id: str
    story_id: str
    chapter: Optional[int] = None
    event: str = ""
    characters_involved: List[str] = field(default_factory=list)
    emotional_tone: str = ""  # happy, sad, tense, romantic, etc.
    can_reference: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "location_id": self.location_id,
            "story_id": self.story_id,
            "chapter": self.chapter,
            "event": self.event,
            "characters_involved": self.characters_involved,
            "emotional_tone": self.emotional_tone,
            "can_reference": self.can_reference,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "LocationMemory":
        return cls(**data)


@dataclass
class UserWorld:
    """
    SCHICHT 3: User-spezifische Welt.
    Enthält Personalisierung, Kontinuität, Ausschlüsse.
    """
    user_id: str
    
    # Interessen-Profil
    interests_primary: List[LayerType] = field(default_factory=list)
    interests_secondary: List[LayerType] = field(default_factory=list)
    interests_avoid: List[LayerType] = field(default_factory=list)
    
    # Persönliche Orte
    personal_places: List[PersonalPlace] = field(default_factory=list)
    
    # Story-Universum
    story_universe_name: Optional[str] = None  # z.B. "elena_universe"
    characters: List[StoryCharacter] = field(default_factory=list)
    location_memories: List[LocationMemory] = field(default_factory=list)
    
    # Content-Einstellungen
    triggers_avoid: List[str] = field(default_factory=list)
    preferred_spice_level: str = "mild"
    preferred_ending: str = "happy"
    
    # Statistiken
    stories_generated: int = 0
    total_words_read: int = 0
    favorite_locations: List[str] = field(default_factory=list)
    
    # Metadaten
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
    
    def get_character(self, name: str) -> Optional[StoryCharacter]:
        """Finde Charakter nach Name"""
        for char in self.characters:
            if char.name.lower() == name.lower():
                return char
        return None
    
    def get_memories_for_location(self, location_id: str) -> List[LocationMemory]:
        """Alle Erinnerungen für einen Ort"""
        return [m for m in self.location_memories if m.location_id == location_id]
    
    def get_excluded_places(self, location_id: str) -> List[str]:
        """Alle ausgeschlossenen Orte für eine Location"""
        return [
            p.name for p in self.personal_places 
            if p.location_id == location_id and not p.use_in_story
        ]
    
    def get_personal_places(self, location_id: str) -> List[PersonalPlace]:
        """Alle persönlichen Orte für eine Location (die verwendet werden sollen)"""
        return [
            p for p in self.personal_places 
            if p.location_id == location_id and p.use_in_story
        ]
    
    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "interests_primary": [i.value for i in self.interests_primary],
            "interests_secondary": [i.value for i in self.interests_secondary],
            "interests_avoid": [i.value for i in self.interests_avoid],
            "personal_places": [p.to_dict() for p in self.personal_places],
            "story_universe_name": self.story_universe_name,
            "characters": [c.to_dict() for c in self.characters],
            "location_memories": [m.to_dict() for m in self.location_memories],
            "triggers_avoid": self.triggers_avoid,
            "preferred_spice_level": self.preferred_spice_level,
            "preferred_ending": self.preferred_ending,
            "stories_generated": self.stories_generated,
            "total_words_read": self.total_words_read,
            "favorite_locations": self.favorite_locations,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "UserWorld":
        data = data.copy()
        data["interests_primary"] = [LayerType(i) for i in data.get("interests_primary", [])]
        data["interests_secondary"] = [LayerType(i) for i in data.get("interests_secondary", [])]
        data["interests_avoid"] = [LayerType(i) for i in data.get("interests_avoid", [])]
        data["personal_places"] = [PersonalPlace.from_dict(p) for p in data.get("personal_places", [])]
        data["characters"] = [StoryCharacter.from_dict(c) for c in data.get("characters", [])]
        data["location_memories"] = [LocationMemory.from_dict(m) for m in data.get("location_memories", [])]
        return cls(**data)


# ═══════════════════════════════════════════════════════════════
# MERGED RESULT: Was der Story-Generator bekommt
# ═══════════════════════════════════════════════════════════════

@dataclass
class MergedLocationData:
    """
    Kombinierte Location-Daten für den Story-Generator.
    Enthält Base + Layer + User-Personalisierung.
    """
    # Basis
    location_id: str
    name: str
    country: str
    
    # Struktur
    districts: List[District] = field(default_factory=list)
    
    # Genre-Layer
    layer_type: LayerType = LayerType.ROMANCE
    atmospheres: Dict[str, str] = field(default_factory=dict)
    places: List[LayerPlace] = field(default_factory=list)
    sensory: SensoryDetails = field(default_factory=SensoryDetails)
    story_hooks: List[str] = field(default_factory=list)
    
    # User-Personalisierung
    personal_places: List[PersonalPlace] = field(default_factory=list)
    excluded_places: List[str] = field(default_factory=list)
    location_memories: List[LocationMemory] = field(default_factory=list)
    
    # Für Story-Kontinuität
    relevant_characters: List[StoryCharacter] = field(default_factory=list)
    
    def to_prompt_context(self) -> str:
        """Konvertiere zu Prompt-Kontext für LLM"""
        lines = [
            f"# LOCATION: {self.name}, {self.country}",
            "",
            "## ATMOSPHÄRE",
        ]
        
        for time, atm in self.atmospheres.items():
            lines.append(f"- {time}: {atm}")
        
        lines.extend([
            "",
            "## WICHTIGE ORTE",
        ])
        
        for place in self.places[:10]:  # Top 10
            lines.append(f"- **{place.name}** ({place.place_type.value}): {place.description}")
            if place.story_potential:
                lines.append(f"  Story-Potenzial: {place.story_potential}")
        
        if self.personal_places:
            lines.extend([
                "",
                "## PERSÖNLICHE ORTE (User-spezifisch)",
            ])
            for pp in self.personal_places:
                lines.append(f"- **{pp.name}**: {pp.note}")
        
        if self.excluded_places:
            lines.extend([
                "",
                "## NICHT VERWENDEN",
                ", ".join(self.excluded_places),
            ])
        
        if self.location_memories:
            lines.extend([
                "",
                "## FRÜHERE STORY-EREIGNISSE AN DIESEM ORT",
            ])
            for mem in self.location_memories:
                lines.append(f"- {mem.event} (Ton: {mem.emotional_tone})")
        
        lines.extend([
            "",
            "## SENSORISCHE DETAILS",
            f"- Gerüche: {', '.join(self.sensory.smells[:5])}",
            f"- Geräusche: {', '.join(self.sensory.sounds[:5])}",
            f"- Texturen: {', '.join(self.sensory.textures[:5])}",
        ])
        
        if self.story_hooks:
            lines.extend([
                "",
                "## STORY-HOOKS",
            ])
            for hook in self.story_hooks[:5]:
                lines.append(f"- {hook}")
        
        return "\n".join(lines)
