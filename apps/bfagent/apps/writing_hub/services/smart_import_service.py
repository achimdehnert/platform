"""
Smart Import Service V2

Multi-Step LLM Pipeline for intelligent document import.

Features:
- Type Detection (Serie, Standalone, Exposé, etc.)
- Metadata Extraction (Title, Genre, Themes)
- Character Extraction (with wound, arc, secret)
- World/Location Extraction (hierarchical)
- Structure Extraction (chapters, plot points)
- Relationship Mapping

Usage:
    from apps.writing_hub.services.smart_import_service import SmartImportService
    
    service = SmartImportService()
    result = await service.import_document(content, filename)

Author: BF Agent Team
Date: 2026-01-22
"""

import json
import logging
import asyncio
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas for Structured Outputs (Extended)
# =============================================================================

class ExtractedCharacterV2(BaseModel):
    """Extended character schema with psychological depth"""
    name: str = Field(description="Full name")
    aliases: List[str] = Field(default_factory=list, description="Nicknames, aliases")
    role: str = Field(default="supporting", description="protagonist|antagonist|love_interest|mentor|ally|minor")
    importance: int = Field(default=3, description="1-5 (1=most important)")
    
    # Demographics
    age: Optional[str] = Field(default=None, description="Age or age range")
    gender: Optional[str] = Field(default=None, description="Gender")
    nationality: Optional[str] = Field(default=None)
    ethnicity: Optional[str] = Field(default=None)
    
    # Profession
    occupation: Optional[str] = Field(default=None)
    organization: Optional[str] = Field(default=None)
    
    # Psychology
    background: Optional[str] = Field(default=None, description="Biography/history")
    motivation: Optional[str] = Field(default=None, description="What drives them")
    wound: Optional[str] = Field(default=None, description="Inner wound/trauma")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    secret: Optional[str] = Field(default=None, description="Hidden secret")
    dark_trait: Optional[str] = Field(default=None, description="Dark side")
    arc: Optional[str] = Field(default=None, description="Character development")
    
    # Expression
    voice_sample: Optional[str] = Field(default=None, description="Example dialogue")
    speech_patterns: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None)
    appearance: Optional[str] = Field(default=None)
    
    # Relationships
    relationships: List[Dict[str, str]] = Field(
        default_factory=list, 
        description="[{to: 'Name', type: 'love_interest|enemy|family'}]"
    )
    
    # Confidence
    source_confidence: str = Field(default="explicit", description="explicit|inferred")


class ExtractedLocationV2(BaseModel):
    """Hierarchical location schema"""
    name: str = Field(description="Name of location")
    type: str = Field(default="location", description="country|city|district|building|room")
    parent: Optional[str] = Field(default=None, description="Parent location name")
    
    description: Optional[str] = Field(default=None)
    atmosphere: Optional[str] = Field(default=None, description="Mood/feeling")
    features: List[str] = Field(default_factory=list)
    symbolism: Optional[str] = Field(default=None, description="Symbolic meaning")
    
    time_period: Optional[str] = Field(default=None)
    scenes: List[str] = Field(default_factory=list, description="Chapters/scenes set here")


class ExtractedChapterV2(BaseModel):
    """Chapter with plot function"""
    number: int
    title: str
    summary: Optional[str] = Field(default=None)
    pov_character: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    
    plot_function: Optional[str] = Field(
        default=None, 
        description="exposition|inciting_incident|rising_action|midpoint|climax|resolution"
    )
    act: Optional[int] = Field(default=None, description="Act number (1, 2, 3)")
    
    word_count: int = Field(default=0)
    status: str = Field(default="planned")
    key_events: List[str] = Field(default_factory=list)


class ExtractedPlotPointV2(BaseModel):
    """Plot point with beat type"""
    type: str = Field(description="opening_image|theme_stated|setup|catalyst|debate|break_into_two|b_story|fun_and_games|midpoint|bad_guys_close_in|all_is_lost|dark_night|break_into_three|finale|final_image")
    description: str
    chapter: Optional[int] = Field(default=None)
    act: Optional[int] = Field(default=None)


class ExtractedMetadataV2(BaseModel):
    """Extended metadata"""
    title: str
    subtitle: Optional[str] = Field(default=None)
    
    # Genre
    genre_primary: str = Field(default="Fiction")
    genre_secondary: List[str] = Field(default_factory=list)
    
    # Format
    format_type: str = Field(default="standalone", description="standalone|series|trilogy")
    planned_books: int = Field(default=1)
    book_number: int = Field(default=1)
    
    # Core Story
    logline: Optional[str] = Field(default=None, description="One-sentence summary")
    premise: Optional[str] = Field(default=None, description="Extended premise (2-5 sentences)")
    central_question: Optional[str] = Field(default=None, description="Thematic core question")
    themes: List[str] = Field(default_factory=list)
    
    # Setting
    setting_time: Optional[str] = Field(default=None)
    setting_location: Optional[str] = Field(default=None)
    
    # Style
    pov: Optional[str] = Field(default=None, description="first_person|third_limited|dual_pov|multiple")
    tense: Optional[str] = Field(default=None, description="present|past")
    narrative_voice: Optional[str] = Field(default=None)
    prose_style: Optional[str] = Field(default=None)
    pacing: Optional[str] = Field(default=None)
    dialogue_style: Optional[str] = Field(default=None)
    
    # Genre-specific
    spice_level: Optional[str] = Field(default=None, description="none|low|medium|high")
    content_warnings: List[str] = Field(default_factory=list)
    
    # Comparisons
    comparable_titles: List[str] = Field(default_factory=list)
    
    # Target
    target_word_count: int = Field(default=80000)
    target_audience: Optional[str] = Field(default=None)
    
    # Document
    document_type: str = Field(default="planning", description="manuscript|planning|character_sheet|expose|mixed")
    confidence: float = Field(default=0.8)


class ImportResultV2(BaseModel):
    """Complete import result"""
    metadata: ExtractedMetadataV2
    characters: List[ExtractedCharacterV2] = Field(default_factory=list)
    locations: List[ExtractedLocationV2] = Field(default_factory=list)
    chapters: List[ExtractedChapterV2] = Field(default_factory=list)
    plot_points: List[ExtractedPlotPointV2] = Field(default_factory=list)
    
    # Series context
    series_arc: Optional[str] = Field(default=None)
    threads_to_continue: List[str] = Field(default_factory=list)
    
    # Raw data for reference
    raw_content: Optional[str] = Field(default=None)
    source_filename: Optional[str] = Field(default=None)
    
    # Analysis info
    ai_analyzed: bool = Field(default=True)
    total_tokens_used: int = Field(default=0)


# =============================================================================
# Prompt Templates
# =============================================================================

TYPE_DETECTION_PROMPT = """Analysiere dieses Dokument und bestimme den Typ:

DATEINAME: {filename}

DOKUMENT (erste 3000 Zeichen):
---
{content_preview}
---

Mögliche Typen:
- SERIE: Mehrere Bände, Serienübersicht, durchgehende Charaktere
- STANDALONE: Einzelnes Buch, keine Bandstruktur
- TRILOGIE: Dreiteiler mit zusammenhängendem Arc
- EXPOSE: Verlagsformat mit Pitch, Inhaltsangabe, Marktpotenzial
- MANUSKRIPT: Fertiger Text mit Kapiteln
- PLANNING: Outline, Notizen, Ideen
- CHARACTER_SHEET: Fokus auf Charakterprofile
- MIXED: Kombination aus mehreren

Antworte NUR als JSON:
{{
  "document_type": "SERIE|STANDALONE|TRILOGIE|EXPOSE|MANUSKRIPT|PLANNING|CHARACTER_SHEET|MIXED",
  "confidence": 0.0-1.0,
  "detected_elements": ["logline", "characters", "chapters", "worldbuilding", ...],
  "format_type": "standalone|series|trilogy",
  "planned_books": 1-N,
  "reasoning": "Kurze Begründung"
}}"""

METADATA_EXTRACTION_PROMPT = """Extrahiere die Metadaten aus diesem Buchprojekt-Dokument:

DOKUMENTTYP: {document_type}

DOKUMENT:
---
{content}
---

Extrahiere alle verfügbaren Informationen. Erfinde NICHTS - nur was im Text steht.

Antworte NUR als JSON:
{{
  "title": "Titel",
  "subtitle": "Untertitel oder null",
  "genre_primary": "Hauptgenre (Thriller, Romance, Fantasy, etc.)",
  "genre_secondary": ["Subgenres"],
  "logline": "Ein-Satz-Zusammenfassung oder null",
  "premise": "Ausführliche Prämisse (2-5 Sätze) oder null",
  "central_question": "Thematische Kernfrage oder null",
  "themes": ["Thema 1", "Thema 2"],
  "setting_time": "Zeitraum (z.B. '2026', 'Mittelalter')",
  "setting_location": "Hauptschauplatz",
  "pov": "first_person|third_limited|dual_pov|multiple|null",
  "tense": "present|past|null",
  "narrative_voice": "Beschreibung der Erzählstimme oder null",
  "prose_style": "Beschreibung des Prosa-Stils oder null",
  "pacing": "Tempo-Beschreibung oder null",
  "dialogue_style": "Dialog-Stil oder null",
  "spice_level": "none|low|medium|high|null",
  "content_warnings": ["Warning 1", "Warning 2"],
  "comparable_titles": ["Buch/Autor 1", "Buch/Autor 2"],
  "target_word_count": 80000,
  "target_audience": "Zielgruppe oder null"
}}"""

CHARACTER_EXTRACTION_PROMPT = """Extrahiere ALLE Charaktere aus diesem Dokument mit maximaler Detailtiefe.

METADATEN-KONTEXT:
Titel: {title}
Genre: {genre}
Themes: {themes}

DOKUMENT:
---
{content}
---

Für JEDEN Charakter extrahiere (soweit vorhanden):

Antworte NUR als JSON:
{{
  "characters": [
    {{
      "name": "Vollständiger Name",
      "aliases": ["Spitzname"],
      "role": "protagonist|antagonist|love_interest|mentor|ally|minor",
      "importance": 1-5,
      
      "age": "Alter oder Altersbereich",
      "gender": "female|male|nonbinary|null",
      "nationality": "Nationalität oder null",
      "ethnicity": "Ethnische Herkunft oder null",
      
      "occupation": "Beruf",
      "organization": "Firma/Organisation oder null",
      
      "background": "Kurzbiografie",
      "motivation": "Was treibt sie an (bewusst und unbewusst)",
      "wound": "Innere Verletzung/Trauma",
      "strengths": ["Stärke 1", "Stärke 2"],
      "weaknesses": ["Schwäche 1", "Schwäche 2"],
      "secret": "Verborgenes Geheimnis",
      "dark_trait": "Dunkle Seite (falls vorhanden)",
      "arc": "Von X zu Y Entwicklung",
      
      "voice_sample": "Beispiel-Dialog der die Stimme zeigt",
      "speech_patterns": "Sprachmuster, Dialekt, typische Ausdrücke",
      "personality": "Persönlichkeitsbeschreibung",
      "appearance": "Physische Beschreibung",
      
      "relationships": [
        {{"to": "Anderer Charakter", "type": "love_interest|enemy|family|colleague|friend"}}
      ],
      
      "source_confidence": "explicit|inferred"
    }}
  ]
}}"""

WORLD_EXTRACTION_PROMPT = """Extrahiere ALLE Schauplätze und Welten aus diesem Dokument.

KONTEXT:
Titel: {title}
Setting: {setting_time} - {setting_location}

DOKUMENT:
---
{content}
---

Erstelle eine HIERARCHISCHE Struktur: Land → Stadt → Stadtteil → Gebäude → Raum

Antworte NUR als JSON:
{{
  "locations": [
    {{
      "name": "Name des Ortes",
      "type": "country|city|district|building|room|region|world",
      "parent": "Name des übergeordneten Ortes oder null",
      "description": "Beschreibung",
      "atmosphere": "Stimmung/Atmosphäre",
      "features": ["Merkmal 1", "Merkmal 2"],
      "symbolism": "Symbolische Bedeutung (falls erkennbar)",
      "time_period": "Zeitraum (falls anders als Hauptsetting)",
      "scenes": ["Kapitel/Szene wo der Ort vorkommt"]
    }}
  ]
}}"""

STRUCTURE_EXTRACTION_PROMPT = """Extrahiere die Buchstruktur: Akte, Kapitel, Plot Points.

KONTEXT:
Titel: {title}
Genre: {genre}

DOKUMENT:
---
{content}
---

Erkenne die narrative Struktur und ordne Kapitel den Akten zu.

Antworte NUR als JSON:
{{
  "structure_type": "three_act|five_act|heroes_journey|episodic|custom",
  "chapters": [
    {{
      "number": 1,
      "title": "Kapiteltitel",
      "summary": "Kurze Zusammenfassung",
      "pov_character": "POV-Charakter oder null",
      "location": "Hauptschauplatz",
      "plot_function": "exposition|inciting_incident|rising_action|midpoint|crisis|climax|resolution",
      "act": 1,
      "key_events": ["Event 1", "Event 2"]
    }}
  ],
  "plot_points": [
    {{
      "type": "opening_image|catalyst|midpoint|all_is_lost|climax|final_image|etc.",
      "description": "Was passiert",
      "chapter": 1,
      "act": 1
    }}
  ],
  "series_context": {{
    "series_arc": "Übergreifender Serien-Arc (falls Serie)",
    "threads_to_continue": ["Offener Handlungsstrang 1", "Offener Strang 2"]
  }}
}}"""


# =============================================================================
# Smart Import Service
# =============================================================================

class SmartImportService:
    """
    Multi-Step LLM Pipeline for intelligent document import.
    
    Steps:
    1. Type Detection - What kind of document is this?
    2. Metadata Extraction - Title, genre, themes, style
    3. Character Extraction - With psychological depth
    4. World Extraction - Hierarchical locations
    5. Structure Extraction - Chapters, plot points, acts
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize the service.
        
        Args:
            llm_client: Optional LLM client. If None, uses default from settings.
        """
        self.llm_client = llm_client
        self._ensure_llm_client()
    
    def _ensure_llm_client(self):
        """Ensure LLM client is available"""
        if self.llm_client is None:
            try:
                from apps.bfagent.services.llm_client import get_llm_client
                self.llm_client = get_llm_client()
            except ImportError:
                logger.warning("LLM client not available, using mock mode")
                self.llm_client = None
    
    async def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call LLM with prompt"""
        if self.llm_client is None:
            raise ValueError("LLM client not available")
        
        # Use the LLM client to get response
        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt=system_prompt or "Du bist ein Experte für Buchanalyse.",
                temperature=0.2,
                max_tokens=4000
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> dict:
        """Extract and parse JSON from LLM response"""
        # Try to find JSON in response
        import re
        
        # Look for JSON block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to parse entire response as JSON
            json_str = response
        
        # Clean up common issues
        json_str = json_str.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Raw response: {response[:500]}")
            raise ValueError(f"Could not parse LLM response as JSON: {e}")
    
    async def detect_document_type(self, content: str, filename: str) -> dict:
        """
        Step 1: Detect document type.
        
        Returns dict with document_type, confidence, detected_elements
        """
        content_preview = content[:3000]
        
        prompt = TYPE_DETECTION_PROMPT.format(
            filename=filename,
            content_preview=content_preview
        )
        
        response = await self._call_llm(prompt)
        return self._parse_json_response(response)
    
    async def extract_metadata(self, content: str, document_type: str) -> ExtractedMetadataV2:
        """
        Step 2: Extract metadata.
        """
        prompt = METADATA_EXTRACTION_PROMPT.format(
            document_type=document_type,
            content=content[:8000]  # Limit for token management
        )
        
        response = await self._call_llm(prompt)
        data = self._parse_json_response(response)
        
        return ExtractedMetadataV2(**data)
    
    async def extract_characters(
        self, 
        content: str, 
        metadata: ExtractedMetadataV2
    ) -> List[ExtractedCharacterV2]:
        """
        Step 3: Extract characters with psychological depth.
        """
        prompt = CHARACTER_EXTRACTION_PROMPT.format(
            title=metadata.title,
            genre=metadata.genre_primary,
            themes=", ".join(metadata.themes),
            content=content[:10000]
        )
        
        response = await self._call_llm(prompt)
        data = self._parse_json_response(response)
        
        characters = []
        for char_data in data.get('characters', []):
            try:
                characters.append(ExtractedCharacterV2(**char_data))
            except Exception as e:
                logger.warning(f"Could not parse character: {e}")
        
        return characters
    
    async def extract_locations(
        self, 
        content: str, 
        metadata: ExtractedMetadataV2
    ) -> List[ExtractedLocationV2]:
        """
        Step 4: Extract locations hierarchically.
        """
        prompt = WORLD_EXTRACTION_PROMPT.format(
            title=metadata.title,
            setting_time=metadata.setting_time or "Nicht angegeben",
            setting_location=metadata.setting_location or "Nicht angegeben",
            content=content[:8000]
        )
        
        response = await self._call_llm(prompt)
        data = self._parse_json_response(response)
        
        locations = []
        for loc_data in data.get('locations', []):
            try:
                locations.append(ExtractedLocationV2(**loc_data))
            except Exception as e:
                logger.warning(f"Could not parse location: {e}")
        
        return locations
    
    async def extract_structure(
        self, 
        content: str, 
        metadata: ExtractedMetadataV2
    ) -> Tuple[List[ExtractedChapterV2], List[ExtractedPlotPointV2], dict]:
        """
        Step 5: Extract structure (chapters, plot points, series context).
        """
        prompt = STRUCTURE_EXTRACTION_PROMPT.format(
            title=metadata.title,
            genre=metadata.genre_primary,
            content=content[:12000]
        )
        
        response = await self._call_llm(prompt)
        data = self._parse_json_response(response)
        
        chapters = []
        for ch_data in data.get('chapters', []):
            try:
                chapters.append(ExtractedChapterV2(**ch_data))
            except Exception as e:
                logger.warning(f"Could not parse chapter: {e}")
        
        plot_points = []
        for pp_data in data.get('plot_points', []):
            try:
                plot_points.append(ExtractedPlotPointV2(**pp_data))
            except Exception as e:
                logger.warning(f"Could not parse plot point: {e}")
        
        series_context = data.get('series_context', {})
        
        return chapters, plot_points, series_context
    
    async def import_document(
        self, 
        content: str, 
        filename: str,
        use_parallel: bool = True
    ) -> ImportResultV2:
        """
        Full import pipeline.
        
        Args:
            content: Document content
            filename: Original filename
            use_parallel: Run steps 3-5 in parallel (faster but more tokens)
        
        Returns:
            ImportResultV2 with all extracted data
        """
        logger.info(f"Starting smart import for: {filename}")
        
        # Step 1: Detect type
        type_result = await self.detect_document_type(content, filename)
        document_type = type_result.get('document_type', 'MIXED')
        logger.info(f"Detected type: {document_type} (confidence: {type_result.get('confidence', 0):.0%})")
        
        # Step 2: Extract metadata
        metadata = await self.extract_metadata(content, document_type)
        metadata.document_type = document_type.lower()
        metadata.confidence = type_result.get('confidence', 0.8)
        
        # Update format info from type detection
        if type_result.get('format_type'):
            metadata.format_type = type_result['format_type']
        if type_result.get('planned_books'):
            metadata.planned_books = type_result['planned_books']
        
        logger.info(f"Extracted metadata: {metadata.title} ({metadata.genre_primary})")
        
        # Steps 3-5: Extract details (parallel or sequential)
        if use_parallel:
            characters, locations, (chapters, plot_points, series_context) = await asyncio.gather(
                self.extract_characters(content, metadata),
                self.extract_locations(content, metadata),
                self.extract_structure(content, metadata),
            )
        else:
            characters = await self.extract_characters(content, metadata)
            locations = await self.extract_locations(content, metadata)
            chapters, plot_points, series_context = await self.extract_structure(content, metadata)
        
        logger.info(f"Extracted: {len(characters)} characters, {len(locations)} locations, {len(chapters)} chapters")
        
        # Build result
        result = ImportResultV2(
            metadata=metadata,
            characters=characters,
            locations=locations,
            chapters=chapters,
            plot_points=plot_points,
            series_arc=series_context.get('series_arc'),
            threads_to_continue=series_context.get('threads_to_continue', []),
            raw_content=content,
            source_filename=filename,
            ai_analyzed=True
        )
        
        return result
    
    def import_document_sync(self, content: str, filename: str) -> ImportResultV2:
        """
        Synchronous wrapper for import_document.
        
        For use in Django views that aren't async.
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.import_document(content, filename))


# =============================================================================
# Convenience Functions
# =============================================================================

def smart_import_document(content: str, filename: str) -> ImportResultV2:
    """
    Convenience function for document import.
    
    Usage:
        result = smart_import_document(content, "mybook.md")
    """
    service = SmartImportService()
    return service.import_document_sync(content, filename)


async def async_smart_import_document(content: str, filename: str) -> ImportResultV2:
    """
    Async convenience function.
    
    Usage:
        result = await async_smart_import_document(content, "mybook.md")
    """
    service = SmartImportService()
    return await service.import_document(content, filename)
