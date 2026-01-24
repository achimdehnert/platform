"""
Outline Generation Handler
Generates story outlines using LLM with full project context from previous phases.

Event-Driven Architecture:
- Publishes CONTENT_GENERATED events when USE_EVENT_BUS is enabled
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Event Bus imports (Feature Flag controlled)
from apps.core.event_bus import event_bus
from apps.core.events import Events

logger = logging.getLogger(__name__)


@dataclass
class OutlineContext:
    """Context for outline generation - pulls from all previous phases"""
    project_id: int
    title: str = ""
    genre: str = ""
    description: str = ""
    premise: str = ""
    logline: str = ""
    themes: str = ""
    target_audience: str = ""
    target_word_count: int = 0
    # Characters from Phase 2
    characters: List[Dict] = field(default_factory=list)
    # Worlds from Phase 3
    worlds: List[Dict] = field(default_factory=list)
    # Framework settings
    framework: str = "save_the_cat"
    chapter_count: int = 15
    
    def to_prompt_context(self) -> str:
        """Build comprehensive context string for LLM prompt"""
        parts = []
        
        # Basic project info
        if self.title:
            parts.append(f"**Titel:** {self.title}")
        if self.genre:
            parts.append(f"**Genre:** {self.genre}")
        if self.description:
            parts.append(f"**Beschreibung:** {self.description}")
        if self.premise:
            parts.append(f"**Premise:** {self.premise}")
        if self.logline:
            parts.append(f"**Logline:** {self.logline}")
        if self.themes:
            parts.append(f"**Themen:** {self.themes}")
        if self.target_audience:
            parts.append(f"**Zielgruppe:** {self.target_audience}")
        if self.target_word_count:
            parts.append(f"**Ziel-Wörter:** {self.target_word_count:,}")
        
        # Characters summary
        if self.characters:
            char_parts = ["**Charaktere:**"]
            for char in self.characters[:5]:  # Limit to main characters
                role = char.get('role', 'supporting')
                name = char.get('name', 'Unbekannt')
                desc = char.get('description', '')[:100]
                char_parts.append(f"- {name} ({role}): {desc}")
            parts.append("\n".join(char_parts))
        
        # Worlds summary
        if self.worlds:
            world_parts = ["**Welten/Settings:**"]
            for world in self.worlds[:3]:  # Limit to main worlds
                name = world.get('name', 'Unbekannt')
                desc = world.get('description', '')[:100]
                world_parts.append(f"- {name}: {desc}")
            parts.append("\n".join(world_parts))
        
        return "\n\n".join(parts)
    
    @classmethod
    def from_project(cls, project_id: int) -> 'OutlineContext':
        """Create OutlineContext from project ID, loading all related data"""
        from apps.bfagent.models import BookProjects, Characters, Worlds
        from apps.writing_hub.models import IdeaSession
        
        try:
            project = BookProjects.objects.get(id=project_id)
        except BookProjects.DoesNotExist:
            return cls(project_id=project_id)
        
        # Load characters
        characters = list(Characters.objects.filter(project=project).values(
            'name', 'role', 'description', 'motivation'
        )[:10])
        
        # Load worlds
        worlds = list(Worlds.objects.filter(project=project).values(
            'name', 'description', 'setting_details', 'world_type'
        )[:5])
        
        # Try to get premise/themes from IdeaSession
        premise = project.story_premise or ''
        themes = ''
        logline = ''
        
        try:
            idea_session = IdeaSession.objects.filter(
                project=project, 
                status='completed'
            ).order_by('-updated_at').first()
            
            if idea_session:
                for resp in idea_session.responses.filter(is_accepted=True).select_related('step'):
                    step_key = resp.step.step_key if resp.step else ''
                    if step_key == 'premise' and resp.content:
                        premise = resp.content
                    elif step_key == 'themes' and resp.content:
                        themes = resp.content
                    elif step_key == 'logline' and resp.content:
                        logline = resp.content
        except Exception:
            pass
        
        return cls(
            project_id=project_id,
            title=project.title or '',
            genre=project.genre or '',
            description=project.description or '',
            premise=premise,
            logline=logline,
            themes=themes,
            target_audience=project.target_audience or '',
            target_word_count=project.target_word_count or 0,
            characters=characters,
            worlds=worlds,
        )


class OutlineGenerationHandler:
    """
    Handler for generating story outlines using LLM with full project context.
    
    Usage:
        handler = OutlineGenerationHandler()
        result = handler.generate_full_outline(context)
        result = handler.generate_chapter_outline(context, chapter_number, beat_name)
    """
    
    PROMPTS = {
        'full_outline': {
            'system': """Du bist ein erfahrener Romanautor und Story-Strukturexperte.
Du erstellst detaillierte, spannende Outlines für Bücher basierend auf bewährten Storytelling-Frameworks.
Antworte immer auf Deutsch und im JSON-Format.""",
            'user': """Erstelle ein vollständiges Outline für folgendes Buchprojekt:

{context}

**Framework:** {framework}
**Anzahl Kapitel:** {chapter_count}

Erstelle für JEDES Kapitel:
- title: Aussagekräftiger Kapiteltitel
- beat: Story-Beat (z.B. "Opening Image", "Catalyst", "Midpoint")
- act: Akt-Nummer (1, 2, oder 3)
- outline: 2-3 Sätze was in diesem Kapitel passiert
- emotional_arc: Emotionaler Zustand/Entwicklung des Protagonisten

Antworte NUR mit einem JSON-Array:
[
  {{"number": 1, "title": "...", "beat": "...", "act": 1, "outline": "...", "emotional_arc": "..."}},
  ...
]"""
        },
        'chapter_outline': {
            'system': """Du bist ein erfahrener Romanautor.
Du erstellst detaillierte Kapitel-Outlines die zur Gesamtgeschichte passen.
Antworte auf Deutsch.""",
            'user': """Erstelle ein detailliertes Outline für Kapitel {chapter_number}:

{context}

**Story-Beat:** {beat_name}
**Bisheriger Inhalt:** {existing_content}

Beschreibe in 3-5 Sätzen:
- Was passiert in diesem Kapitel?
- Welche Charaktere sind involviert?
- Wie entwickelt sich die Spannung?

Antworte NUR mit dem Outline-Text, keine JSON-Formatierung."""
        },
        'enrich_outline': {
            'system': """Du bist ein erfahrener Romanautor und Story-Entwickler.
Du erweiterst bestehende Kapitel-Outlines zu detaillierten Szenenplanungen.
Dein Ziel ist es, kurze Zusammenfassungen in ausführliche, handwerklich präzise Outlines zu transformieren.
Antworte auf Deutsch.""",
            'user': """Erweitere das folgende kurze Kapitel-Outline zu einem DETAILLIERTEN Szenenplan:

{context}

**Kapitel {chapter_number}:** {beat_name}

**KURZES OUTLINE (zu erweitern):**
{existing_content}

**FRAMEWORK-SPEZIFISCHE ANWEISUNGEN FÜR DIESEN BEAT:**
{beat_llm_prompt}

---

Erstelle ein AUSFÜHRLICHES Outline mit folgender Struktur:

## Kapitel {chapter_number}: [Titel] – Detailliertes Outline

**Ziel:** [Was dieses Kapitel für die Geschichte erreichen soll, basierend auf den Framework-Anweisungen]

### Szene 1: [Ort] (Wörter: ca. X)
* **Beschreibung:** [2-3 Sätze zur Szene]
* **Dialog:** [Wichtige Gesprächspunkte]
* **Innerer Monolog:** [Gedanken/Gefühle des POV-Charakters]

### Szene 2: [Ort] (Wörter: ca. X)
[gleiche Struktur]

Füge so viele Szenen hinzu wie nötig (typisch 2-4 pro Kapitel).

WICHTIG:
- Befolge die Framework-spezifischen Anweisungen oben
- Jede Szene braucht einen klaren Ort/Setting
- Beschreibe konkrete Aktionen, nicht nur Zusammenfassungen
- Füge Dialog-Hinweise und innere Monologe ein
- Halte die Szenen im Rahmen des Story-Beats

Antworte NUR mit dem erweiterten Outline-Text."""
        },
        'complete_outline': {
            'system': """Du bist ein erfahrener Romanautor und Story-Entwickler.
Du erstellst VOLLSTÄNDIGE, detaillierte Kapitel-Outlines von Grund auf.
Dein Ziel ist es, umfassende, ausführliche Szenenplanungen zu erstellen, die direkt zum Schreiben verwendet werden können.
Antworte auf Deutsch.""",
            'user': """Erstelle ein VOLLSTÄNDIGES, detailliertes Outline für dieses Kapitel:

{context}

**Kapitel {chapter_number}:** {beat_name}

**FRAMEWORK-SPEZIFISCHE ANWEISUNGEN FÜR DIESEN BEAT:**
{beat_llm_prompt}

**Bisheriger Outline (falls vorhanden):**
{existing_content}

---

Erstelle ein UMFASSENDES Outline mit folgender Struktur:

## Kapitel {chapter_number}: [Titel]

**Beat-Funktion:** [Was dieses Kapitel für die Geschichte erreichen muss]
**Emotionaler Bogen:** [Anfang → Ende des Kapitels]

### Kapitel-Outline

* **Opening Hook:** [Einstiegsszene die den Leser fesselt]
* **Tobias alarmiert die Polizei:** [Szene 1 mit Details]
* **[Weitere Szenen mit konkreten Handlungen]**

**HauptSzenen (2-4 Szenen):**

### Szene 1: [Setting/Ort]
* **Ziel:** [Was diese Szene erreichen soll]
* **Charaktere:** [Wer ist beteiligt]
* **Handlung:** [Konkrete Ereignisse, 3-5 Bullet Points]
* **Dialog-Highlights:** [Wichtige Gespräche/Konflikte]
* **Innerer Konflikt:** [Gedanken/Gefühle des POV-Charakters]
* **Spannungsbogen:** [Wie steigt die Spannung]

### Szene 2: [Setting/Ort]
[gleiche Struktur]

**Kapitel-Ende:**
* **Cliffhanger/Hook:** [Was den Leser zum Weiterlesen motiviert]
* **Offene Fragen:** [Welche Fragen bleiben offen]

**Geschätzte Wörter:** [ca. X Wörter]

WICHTIG:
- Befolge die Framework-spezifischen Anweisungen genau
- Sei KONKRET - keine vagen Zusammenfassungen
- Jede Szene braucht einen klaren Ort und konkrete Handlungen
- Baue Spannung auf und halte den Leser bei der Stange
- Das Outline soll zum direkten Schreiben verwendet werden können

Antworte NUR mit dem vollständigen Outline-Text."""
        },
        'chapter_title': {
            'system': "Du bist ein kreativer Autor. Antworte auf Deutsch.",
            'user': """Erstelle einen aussagekräftigen Kapiteltitel für:

{context}

**Kapitel:** {chapter_number}
**Beat:** {beat_name}
**Outline:** {existing_content}

Antworte NUR mit dem Titel (ohne Anführungszeichen)."""
        },
        'emotional_arc': {
            'system': "Du bist ein Experte für Charakterentwicklung. Antworte auf Deutsch.",
            'user': """Beschreibe den emotionalen Bogen für dieses Kapitel:

{context}

**Kapitel:** {chapter_number}
**Beat:** {beat_name}
**Outline:** {existing_content}

Beschreibe in 1-2 Sätzen:
- Emotionaler Zustand des Protagonisten am Anfang
- Emotionale Entwicklung/Veränderung
- Emotionaler Zustand am Ende

Antworte NUR mit der Beschreibung."""
        }
    }
    
    def __init__(self, llm_id: Optional[int] = None):
        """Initialize handler with optional specific LLM."""
        self.llm_id = llm_id
        self._llm = None
    
    def get_llm(self):
        """Get the LLM to use - checks WorkflowPhaseLLMConfig first"""
        if self._llm:
            return self._llm
        
        from apps.bfagent.models import Llms
        from apps.writing_hub.models import WorkflowPhaseLLMConfig
        
        # 1. Try WorkflowPhaseLLMConfig for 'outline' phase
        config_llm = WorkflowPhaseLLMConfig.get_llm_for_phase('outline')
        if config_llm:
            self._llm = config_llm
            logger.info(f"Using workflow config LLM for outline: {self._llm.name}")
            return self._llm
        
        # 2. Try specific LLM ID if provided
        if self.llm_id:
            self._llm = Llms.objects.filter(id=self.llm_id, is_active=True).first()
            if self._llm:
                logger.info(f"Using specified LLM ID {self.llm_id}: {self._llm.name}")
                return self._llm
        
        # 3. Fallback: any active LLM
        self._llm = Llms.objects.filter(is_active=True).first()
        if self._llm:
            logger.info(f"Using fallback LLM: {self._llm.name}")
        
        return self._llm
    
    def generate_full_outline(self, context: OutlineContext) -> Dict[str, Any]:
        """
        Generate complete outline for all chapters using LLM.
        
        Args:
            context: OutlineContext with project data
        
        Returns:
            Dict with 'success', 'chapters', 'llm_used', 'error'
        """
        llm = self.get_llm()
        if not llm:
            return {
                'success': False,
                'error': 'Kein aktives LLM konfiguriert. Bitte im Control Center ein LLM aktivieren.'
            }
        
        prompt_config = self.PROMPTS['full_outline']
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(
                context=context_str,
                framework=context.framework,
                chapter_count=context.chapter_count
            ),
            temperature=0.7,
            max_tokens=4000,
        )
        
        logger.info(f"Calling LLM {llm.name} for full outline generation")
        response = generate_text(req)
        
        if not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler')
            logger.error(f"LLM error for outline generation: {error_msg}")
            return {
                'success': False,
                'error': f"LLM Fehler: {error_msg}",
                'llm_used': llm.name
            }
        
        result_text = response.get('text', '').strip()
        
        # Parse JSON response
        try:
            # Clean up potential markdown code blocks
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            chapters = json.loads(result_text)
            if not isinstance(chapters, list):
                chapters = [chapters]
            
            # Ensure all chapters have required fields
            for i, ch in enumerate(chapters):
                ch.setdefault('number', i + 1)
                ch.setdefault('title', f'Kapitel {i + 1}')
                ch.setdefault('beat', '')
                ch.setdefault('act', 1 if i < len(chapters) * 0.25 else (2 if i < len(chapters) * 0.75 else 3))
                ch.setdefault('outline', '')
                ch.setdefault('emotional_arc', '')
                ch.setdefault('target_words', context.target_word_count // max(len(chapters), 1))
            
            logger.info(f"Successfully generated {len(chapters)} chapter outlines using {llm.name}")
            
            # Publish event (only if feature flag enabled)
            event_bus.publish(
                Events.CONTENT_GENERATED,
                source="OutlineGenerationHandler",
                content_type="outline",
                project_id=context.project_id,
                chapter_count=len(chapters),
                llm_used=llm.name,
            )
            
            return {
                'success': True,
                'chapters': chapters,
                'llm_used': llm.name,
                'latency_ms': response.get('latency_ms')
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outline JSON: {e}")
            return {
                'success': False,
                'error': f'Fehler beim Parsen der KI-Antwort: {str(e)}',
                'raw_response': result_text[:500],
                'llm_used': llm.name
            }
    
    def generate_field(self, context: OutlineContext, field_type: str, 
                       chapter_number: int, beat_name: str = '', 
                       existing_content: str = '', beat_llm_prompt: str = '') -> Dict[str, Any]:
        """
        Generate content for a specific outline field.
        
        Args:
            context: OutlineContext
            field_type: 'chapter_outline', 'chapter_title', 'emotional_arc'
            chapter_number: Chapter number
            beat_name: Story beat name
            existing_content: Existing content to expand/improve
        
        Returns:
            Dict with 'success', 'content', 'llm_used', 'error'
        """
        if field_type not in self.PROMPTS:
            return {'success': False, 'error': f'Unbekannter Feldtyp: {field_type}'}
        
        llm = self.get_llm()
        if not llm:
            return {'success': False, 'error': 'Kein aktives LLM konfiguriert.'}
        
        prompt_config = self.PROMPTS[field_type]
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        # Field-specific max_tokens - outlines need more space
        field_max_tokens = {
            'chapter_outline': 2000,  # Detailed chapter outline
            'enrich_outline': 4000,   # Expanded detailed outline with scenes
            'complete_outline': 4000, # Full complete outline from scratch
            'chapter_title': 100,     # Just a title
            'emotional_arc': 300,     # Short description
        }
        max_tokens = field_max_tokens.get(field_type, 1000)
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(
                context=context_str,
                chapter_number=chapter_number,
                beat_name=beat_name or 'Unbekannt',
                existing_content=existing_content or 'Noch nicht definiert',
                beat_llm_prompt=beat_llm_prompt or 'Keine spezifischen Anweisungen für diesen Beat.'
            ),
            temperature=0.7,
            max_tokens=max_tokens,
        )
        
        logger.info(f"Calling LLM {llm.name} for {field_type} (chapter {chapter_number})")
        response = generate_text(req)
        
        if not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler')
            return {'success': False, 'error': f"LLM Fehler: {error_msg}", 'llm_used': llm.name}
        
        content = response.get('text', '').strip()
        
        logger.info(f"Successfully generated {field_type} using {llm.name}")
        
        return {
            'success': True,
            'content': content,
            'llm_used': llm.name,
            'latency_ms': response.get('latency_ms')
        }


# Singleton instance
outline_handler = OutlineGenerationHandler()
