"""
AI-Powered Document Import Service

Uses LLM to analyze and extract structured data from various document formats.
Supports manuscripts, planning documents, character sheets, and mixed content.

Usage:
    from apps.writing_hub.services.ai_import_service import AIImportService
    
    service = AIImportService()
    result = await service.analyze_document(content, filename)
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas for Structured LLM Outputs
# =============================================================================

class ExtractedCharacter(BaseModel):
    """Schema for extracted character data"""
    name: str = Field(description="Full name of the character")
    role: str = Field(default="supporting", description="Role: protagonist, antagonist, supporting, minor")
    age: Optional[str] = Field(default=None, description="Age or age range")
    occupation: Optional[str] = Field(default=None, description="Job or role in story")
    background: Optional[str] = Field(default=None, description="Background/history")
    personality: Optional[str] = Field(default=None, description="Personality traits")
    appearance: Optional[str] = Field(default=None, description="Physical description")
    motivation: Optional[str] = Field(default=None, description="Goals and motivations")
    arc: Optional[str] = Field(default=None, description="Character development arc")
    relationships: List[str] = Field(default_factory=list, description="Key relationships")


class ExtractedLocation(BaseModel):
    """Schema for extracted location/world data"""
    name: str = Field(description="Name of the location")
    type: str = Field(default="location", description="Type: city, region, world, building, etc.")
    description: Optional[str] = Field(default=None, description="Description of the place")
    features: List[str] = Field(default_factory=list, description="Notable features")
    atmosphere: Optional[str] = Field(default=None, description="Mood/atmosphere")


class ExtractedChapter(BaseModel):
    """Schema for extracted chapter data"""
    number: int = Field(description="Chapter number")
    title: str = Field(description="Chapter title")
    summary: Optional[str] = Field(default=None, description="Brief summary")
    pov: Optional[str] = Field(default=None, description="Point of view character")
    location: Optional[str] = Field(default=None, description="Main location")
    word_count: int = Field(default=0, description="Approximate word count")
    status: str = Field(default="draft", description="Status: draft, outlined, planned")
    key_events: List[str] = Field(default_factory=list, description="Key plot events")


class ExtractedPlotPoint(BaseModel):
    """Schema for extracted plot/story structure"""
    type: str = Field(description="Type: inciting_incident, midpoint, climax, resolution, etc.")
    description: str = Field(description="Description of the plot point")
    chapter: Optional[int] = Field(default=None, description="Associated chapter number")


class DocumentAnalysisResult(BaseModel):
    """Complete analysis result from LLM"""
    title: str = Field(description="Detected or suggested title")
    genre: str = Field(default="Fiction", description="Detected genre")
    document_type: str = Field(description="Type: manuscript, planning, character_sheet, mixed")
    summary: Optional[str] = Field(default=None, description="Brief summary of the content")
    themes: List[str] = Field(default_factory=list, description="Main themes")
    
    characters: List[ExtractedCharacter] = Field(default_factory=list)
    locations: List[ExtractedLocation] = Field(default_factory=list)
    chapters: List[ExtractedChapter] = Field(default_factory=list)
    plot_points: List[ExtractedPlotPoint] = Field(default_factory=list)
    
    word_count: int = Field(default=0, description="Total word count")
    confidence: float = Field(default=0.8, description="Confidence score 0-1")


# =============================================================================
# Prompt Templates
# =============================================================================

ANALYSIS_SYSTEM_PROMPT = """Du bist ein Experte für Buchanalyse und Textstrukturierung.
Analysiere das bereitgestellte Dokument und extrahiere strukturierte Informationen.

WICHTIG:
- Extrahiere NUR Informationen, die tatsächlich im Text vorhanden sind
- Erfinde keine Charaktere, Orte oder Handlungselemente
- Bei Unsicherheit: lieber weglassen als raten
- Antworte IMMER im angegebenen JSON-Format"""


DOCUMENT_ANALYSIS_PROMPT = """Analysiere folgendes Dokument und extrahiere alle relevanten Informationen:

DATEINAME: {filename}

DOKUMENT:
---
{content}
---

Extrahiere:
1. **Titel**: Der erkannte oder vorgeschlagene Titel des Werks
2. **Genre**: Das erkannte Genre (Fantasy, Thriller, Romance, Sci-Fi, Mystery, Horror, Literary, etc.)
3. **Dokumenttyp**: manuscript (fertiger Text), planning (Planung/Outline), character_sheet (Charakterbögen), mixed
4. **Zusammenfassung**: Kurze Zusammenfassung in 2-3 Sätzen
5. **Premise**: Die zentrale Story-Prämisse (ausführlicher als Logline, 2-5 Sätze)
6. **Logline**: Ein-Satz-Zusammenfassung ("Wenn [Protagonist] [Herausforderung] begegnet, muss er/sie [Handlung], bevor [Konsequenz]")
7. **Setting**: Hauptschauplatz mit Zeitangabe (z.B. "München 2026", "Mittelalterliche Fantasy-Welt")
8. **Themen**: Hauptthemen des Werks
9. **Charaktere**: Alle erkannten Charaktere mit verfügbaren Details
10. **Orte/Welten**: Alle erkannten Schauplätze (Städte, Regionen, Länder, Fantasy-Welten)
11. **Kapitel**: Falls vorhanden, die Kapitelstruktur
12. **Plot-Punkte**: Wichtige Handlungspunkte (Inciting Incident, Midpoint, Climax, etc.)
13. **Wortanzahl**: Geschätzte Gesamtwortanzahl

Antworte im folgenden JSON-Format:
```json
{{
    "title": "Erkannter Titel",
    "genre": "Genre",
    "document_type": "manuscript|planning|character_sheet|mixed",
    "summary": "Kurze Zusammenfassung",
    "premise": "Die zentrale Prämisse/Story-Idee des Werks (2-5 Sätze)",
    "logline": "Ein-Satz-Zusammenfassung der Geschichte",
    "setting": "Hauptschauplatz mit Zeit (z.B. 'München 2026', 'Fantasy-Welt Eldoria')",
    "themes": ["Thema 1", "Thema 2"],
    "characters": [
        {{
            "name": "Name",
            "role": "protagonist|antagonist|supporting|minor",
            "age": "Alter oder null",
            "occupation": "Beruf oder null",
            "background": "Hintergrund oder null",
            "personality": "Persönlichkeit oder null",
            "appearance": "Aussehen oder null",
            "motivation": "Motivation oder null",
            "arc": "Charakterentwicklung oder null",
            "relationships": ["Beziehung 1", "Beziehung 2"]
        }}
    ],
    "locations": [
        {{
            "name": "Ortsname",
            "type": "city|region|world|building|realm",
            "description": "Beschreibung oder null",
            "features": ["Merkmal 1", "Merkmal 2"],
            "atmosphere": "Atmosphäre oder null"
        }}
    ],
    "chapters": [
        {{
            "number": 1,
            "title": "Kapiteltitel",
            "summary": "Zusammenfassung oder null",
            "pov": "POV-Charakter oder null",
            "location": "Hauptort oder null",
            "word_count": 0,
            "status": "draft|outlined|planned",
            "key_events": ["Event 1", "Event 2"]
        }}
    ],
    "plot_points": [
        {{
            "type": "inciting_incident|first_plot_point|midpoint|climax|resolution",
            "description": "Beschreibung",
            "chapter": 1
        }}
    ],
    "word_count": 50000,
    "confidence": 0.85
}}
```"""


CHARACTER_EXTRACTION_PROMPT = """Extrahiere alle Charaktere aus folgendem Text.
Fokussiere dich auf:
- Namen und Rollen
- Persönlichkeitsmerkmale
- Beziehungen zueinander
- Motivationen und Ziele
- Charakterentwicklung (Arc)

TEXT:
---
{content}
---

Antworte als JSON-Array von Charakteren."""


CHAPTER_STRUCTURE_PROMPT = """Analysiere die Kapitelstruktur des folgenden Textes.
Identifiziere:
- Kapitelnummern und -titel
- POV-Charaktere pro Kapitel
- Hauptschauplätze
- Wichtige Ereignisse
- Ungefähre Wortanzahl

TEXT:
---
{content}
---

Antworte als JSON-Array von Kapiteln."""


# =============================================================================
# AI Import Service
# =============================================================================

class AIImportService:
    """Service for AI-powered document analysis and import"""
    
    # LLM MCP Gateway URL (from mcp-hub)
    LLM_GATEWAY_URL = "http://127.0.0.1:8100"
    
    def __init__(self, use_ai: bool = True, model: Optional[str] = None):
        """
        Initialize the AI Import Service.
        
        Args:
            use_ai: Whether to use AI (True) or fallback to rule-based (False)
            model: Optional LLM model name or ID (uses default if None)
        """
        self.use_ai = use_ai
        self.model = model
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Make an LLM call via MCP HTTP Gateway and return the response text"""
        import requests
        
        try:
            response = requests.post(
                f"{self.LLM_GATEWAY_URL}/generate",
                json={
                    "prompt": user_prompt,
                    "system_prompt": system_prompt,
                    "model": self.model,  # None = use default
                    "temperature": 0.3,   # Low temperature for structured extraction
                    "max_tokens": 4000,
                    "response_format": "json"
                },
                timeout=120  # 2 minutes for long documents
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    content = result.get('content')
                    # If content is already parsed dict, convert back to string for our processing
                    if isinstance(content, (dict, list)):
                        return json.dumps(content, ensure_ascii=False)
                    return content
                else:
                    logger.warning(f"LLM Gateway error: {result.get('error')}")
                    return None
            else:
                logger.warning(f"LLM Gateway HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.warning("LLM Gateway not running (http://127.0.0.1:8100) - using rule-based fallback")
            return None
        except Exception as e:
            logger.error(f"LLM Gateway call error: {e}")
            return None
    
    def analyze_document(self, content: str, filename: str = "document.md") -> Dict[str, Any]:
        """
        Analyze a document and extract structured data.
        
        Args:
            content: The document content
            filename: Original filename for context
            
        Returns:
            Dict with extracted data in standard format
        """
        if not content or not content.strip():
            return self._empty_result(filename)
        
        # Truncate very long content for LLM
        max_chars = 30000  # ~7500 tokens
        truncated_content = content[:max_chars]
        if len(content) > max_chars:
            truncated_content += "\n\n[... Text gekürzt ...]"
        
        # Try AI analysis first
        if self.use_ai:
            ai_result = self._analyze_with_ai(truncated_content, filename)
            if ai_result:
                return ai_result
        
        # Fallback to rule-based parsing
        logger.info("Using rule-based fallback for document analysis")
        return self._analyze_with_rules(content, filename)
    
    def _analyze_with_ai(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """Analyze document using AI/LLM"""
        prompt = DOCUMENT_ANALYSIS_PROMPT.format(
            filename=filename,
            content=content
        )
        
        response = self._call_llm(ANALYSIS_SYSTEM_PROMPT, prompt)
        if not response:
            return None
        
        try:
            # Parse JSON response
            # Handle markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
            
            data = json.loads(json_str)
            
            # Convert to standard format
            return self._normalize_ai_result(data, content)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return None
    
    def _normalize_ai_result(self, data: Dict, original_content: str) -> Dict[str, Any]:
        """Normalize AI result to standard import format"""
        # Calculate actual word count if not provided
        word_count = data.get('word_count', 0)
        if not word_count:
            word_count = len(original_content.split())
        
        result = {
            'title': data.get('title', 'Unbekannter Titel'),
            'genre': data.get('genre', 'Fiction'),
            'document_type': data.get('document_type', 'mixed'),
            'summary': data.get('summary', ''),
            'premise': data.get('premise', ''),
            'logline': data.get('logline', ''),
            'setting': data.get('setting', ''),
            'themes': data.get('themes', []),
            'word_count': word_count,
            'chapter_count': len(data.get('chapters', [])),
            'confidence': data.get('confidence', 0.8),
            'ai_analyzed': True,
            'raw_content': original_content,  # Store for regex fallback
            
            # Characters
            'characters': [
                {
                    'name': c.get('name', 'Unbekannt'),
                    'role': c.get('role', 'supporting'),
                    'age': c.get('age', ''),
                    'background': c.get('background', ''),
                    'personality': c.get('personality', ''),
                    'appearance': c.get('appearance', ''),
                    'motivation': c.get('motivation', ''),
                    'arc': c.get('arc', ''),
                    'traits': [],  # Could be extracted from personality
                    'source_file': 'AI Analysis',
                }
                for c in data.get('characters', [])
            ],
            
            # Locations
            'locations': [
                {
                    'name': l.get('name', 'Unbekannt'),
                    'description': l.get('description', ''),
                    'features': l.get('features', []),
                    'type': l.get('type', 'location'),
                    'source_file': 'AI Analysis',
                }
                for l in data.get('locations', [])
            ],
            
            # Chapters
            'chapters': [
                {
                    'number': ch.get('number', i + 1),
                    'title': ch.get('title', f'Kapitel {i + 1}'),
                    'summary': ch.get('summary', ''),
                    'pov': ch.get('pov', ''),
                    'location': ch.get('location', ''),
                    'word_count': ch.get('word_count', 0),
                    'status': ch.get('status', 'draft'),
                    'beats': ch.get('key_events', []),
                    'source_file': 'AI Analysis',
                }
                for i, ch in enumerate(data.get('chapters', []))
            ],
            
            # Plot structure
            'story_arc': {
                'type': self._detect_structure_type(data.get('plot_points', [])),
                'parts': len(data.get('plot_points', [])),
                'twists': sum(1 for p in data.get('plot_points', []) if 'twist' in p.get('type', '').lower()),
            },
            
            'plot_points': data.get('plot_points', []),
            'subplots': [],  # Could be extracted in future
            'working_titles': [data.get('title')] if data.get('title') else [],
            'sources': [{'filename': 'AI Analysis', 'type': 'ai', 'word_count': word_count}],
        }
        
        return result
    
    def _detect_structure_type(self, plot_points: List[Dict]) -> str:
        """Detect story structure type from plot points"""
        types = [p.get('type', '').lower() for p in plot_points]
        
        if any('hero' in t or 'journey' in t for t in types):
            return "Hero's Journey"
        elif any('three' in t or '3-act' in t for t in types):
            return "Three-Act Structure"
        elif any('save' in t and 'cat' in t for t in types):
            return "Save the Cat"
        elif len(plot_points) >= 5:
            return "Multi-Act Structure"
        elif len(plot_points) >= 3:
            return "Three-Act Structure"
        else:
            return "Linear"
    
    def _analyze_with_rules(self, content: str, filename: str) -> Dict[str, Any]:
        """Fallback rule-based analysis"""
        from .management.commands.reengineer_book import BookReengineer
        import tempfile
        import os
        
        # Write to temp file and use existing parser
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = f.name
            
            reeng = BookReengineer(temp_path, verbose=False)
            result = reeng.analyze()
            
            # Convert to standard format
            return {
                'title': result.title or filename.replace('.md', ''),
                'genre': result.genre or 'Fiction',
                'document_type': result.document_type or 'mixed',
                'word_count': result.word_count or len(content.split()),
                'chapter_count': result.chapter_count or 0,
                'ai_analyzed': False,
                
                'characters': [
                    {
                        'name': c.name,
                        'role': c.role if c.role != 'unknown' else '',
                        'age': c.age or '',
                        'background': c.background or '',
                        'motivation': c.motivation or '',
                        'arc': c.arc or '',
                        'traits': c.traits or [],
                        'source_file': filename,
                    }
                    for c in result.characters
                ],
                
                'locations': [
                    {
                        'name': l.name,
                        'description': l.description or '',
                        'features': l.features or [],
                        'source_file': filename,
                    }
                    for l in result.locations
                ],
                
                'chapters': [
                    {
                        'number': c.number,
                        'title': c.title,
                        'word_count': c.word_count,
                        'status': c.status,
                        'pov': c.pov,
                        'location': c.location,
                        'beats': c.beats[:5] if c.beats else [],
                        'source_file': filename,
                    }
                    for c in result.chapters
                ],
                
                'story_arc': {
                    'type': result.story_arc.structure_type if result.story_arc else '',
                    'parts': len(result.story_arc.parts) if result.story_arc else 0,
                    'twists': len(result.story_arc.twists) if result.story_arc else 0,
                },
                
                'subplots': [s.name for s in result.subplots] if result.subplots else [],
                'working_titles': result.working_titles or [],
                'sources': [{'filename': filename, 'type': 'file', 'word_count': result.word_count}],
            }
            
        except Exception as e:
            logger.error(f"Rule-based analysis failed: {e}")
            return self._empty_result(filename)
        finally:
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
    
    def _empty_result(self, filename: str) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'title': filename.replace('.md', '') if filename else 'Unbekanntes Dokument',
            'genre': 'Fiction',
            'document_type': 'unknown',
            'word_count': 0,
            'chapter_count': 0,
            'ai_analyzed': False,
            'characters': [],
            'locations': [],
            'chapters': [],
            'story_arc': {'type': '', 'parts': 0, 'twists': 0},
            'subplots': [],
            'working_titles': [],
            'sources': [],
        }
    
    def extract_characters(self, content: str) -> List[Dict]:
        """Extract only characters from content"""
        if not self.use_ai:
            return []
        
        prompt = CHARACTER_EXTRACTION_PROMPT.format(content=content[:15000])
        response = self._call_llm(ANALYSIS_SYSTEM_PROMPT, prompt)
        
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, list):
                    return data
            except:
                pass
        return []
    
    def extract_chapters(self, content: str) -> List[Dict]:
        """Extract only chapter structure from content"""
        if not self.use_ai:
            return []
        
        prompt = CHAPTER_STRUCTURE_PROMPT.format(content=content[:20000])
        response = self._call_llm(ANALYSIS_SYSTEM_PROMPT, prompt)
        
        if response:
            try:
                data = json.loads(response)
                if isinstance(data, list):
                    return data
            except:
                pass
        return []


# =============================================================================
# Convenience Functions
# =============================================================================

def analyze_document_with_ai(content: str, filename: str = "document.md", use_ai: bool = True, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for document analysis.
    
    Args:
        content: Document content
        filename: Original filename
        use_ai: Whether to use AI analysis (requires LLM Gateway on port 8100)
        model: Optional LLM model name or ID
        
    Returns:
        Structured analysis result
    """
    service = AIImportService(use_ai=use_ai, model=model)
    return service.analyze_document(content, filename)


def get_import_service(use_ai: bool = True, model: Optional[str] = None) -> AIImportService:
    """Get an AIImportService instance"""
    return AIImportService(use_ai=use_ai, model=model)
