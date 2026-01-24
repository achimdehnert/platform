"""
Character Generation Handler
Generates characters and character details for book projects using LLM.

Event-Driven Architecture:
- Publishes CHARACTER_CREATED events when USE_EVENT_BUS is enabled
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Event Bus imports (Feature Flag controlled)
from apps.core.event_bus import event_bus
from apps.core.events import Events

logger = logging.getLogger(__name__)


@dataclass
class CharacterContext:
    """Context for character generation"""
    project_id: int
    title: str = ""
    genre: str = ""
    premise: str = ""
    themes: str = ""
    target_audience: str = ""
    existing_characters: List[Dict] = None
    
    def __post_init__(self):
        if self.existing_characters is None:
            self.existing_characters = []
    
    def to_prompt_context(self) -> str:
        """Build context string for LLM prompt"""
        parts = []
        if self.title:
            parts.append(f"Titel: {self.title}")
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.premise:
            parts.append(f"Premise: {self.premise}")
        if self.themes:
            parts.append(f"Themen: {self.themes}")
        if self.target_audience:
            parts.append(f"Zielgruppe: {self.target_audience}")
        if self.existing_characters:
            char_names = [c.get('name', 'Unbekannt') for c in self.existing_characters]
            parts.append(f"Vorhandene Charaktere: {', '.join(char_names)}")
        
        return "\n".join(parts)


class CharacterGenerationHandler:
    """
    Handler for generating characters using an assigned LLM.
    
    Usage:
        handler = CharacterGenerationHandler()
        result = handler.generate_characters(context, count=3)
        result = handler.generate_character_details(context, name, role)
    """
    
    PROMPTS = {
        'characters': {
            'system': """Du bist ein erfahrener Romanautor und Charakterdesigner. 
Du erstellst interessante, vielschichtige Charaktere mit einzigartigen Eigenschaften.
Antworte immer auf Deutsch und im JSON-Format.""",
            'user': """Erstelle {count} Charaktere für folgendes Buchprojekt:

{context}

Erstelle Charaktere mit verschiedenen Rollen (protagonist, antagonist, mentor, ally, love_interest, supporting).
Jeder Charakter braucht einen einzigartigen Namen passend zum Genre.

Antworte NUR mit einem JSON-Array in diesem Format:
[
  {{"name": "...", "role": "protagonist", "description": "...", "age": "...", "motivation": "..."}},
  {{"name": "...", "role": "antagonist", "description": "...", "age": "...", "motivation": "..."}}
]

Keine Erklärung, nur das JSON-Array."""
        },
        'details': {
            'system': """Du bist ein erfahrener Charakterdesigner für Romane.
Du erstellst detaillierte, konsistente Charakterprofile.
Antworte immer auf Deutsch und im JSON-Format.""",
            'user': """Erstelle ein detailliertes Profil für folgenden Charakter:

Name: {name}
Rolle: {role}

Buchkontext:
{context}

Erstelle ein vollständiges Charakterprofil mit allen Details.

Antworte NUR mit einem JSON-Objekt in diesem Format:
{{
  "appearance": "Detaillierte physische Beschreibung...",
  "personality": "Persönlichkeitszüge und Verhalten...",
  "motivation": "Was treibt den Charakter an...",
  "conflict": "Innere und äußere Konflikte...",
  "background": "Hintergrundgeschichte...",
  "arc": "Charakterentwicklung im Verlauf der Geschichte..."
}}

Keine Erklärung, nur das JSON-Objekt."""
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
        
        # 1. Try WorkflowPhaseLLMConfig for 'characters' phase
        config_llm = WorkflowPhaseLLMConfig.get_llm_for_phase('characters')
        if config_llm:
            self._llm = config_llm
            logger.info(f"Using workflow config LLM for characters: {self._llm.name}")
            return self._llm
        
        # 2. Try specific LLM ID if provided
        if self.llm_id:
            self._llm = Llms.objects.filter(id=self.llm_id, is_active=True).first()
            if self._llm:
                logger.info(f"Using specified LLM ID {self.llm_id}: {self._llm.name}")
                return self._llm
        
        # 3. Fallback: any active LLM (prefer fast ones like Groq)
        self._llm = Llms.objects.filter(
            is_active=True, 
            provider__icontains='groq'
        ).first()
        
        if not self._llm:
            self._llm = Llms.objects.filter(is_active=True).first()
        
        if self._llm:
            logger.info(f"Using fallback LLM: {self._llm.name}")
        
        return self._llm
    
    def generate_characters(self, context: CharacterContext, count: int = 3) -> Dict[str, Any]:
        """
        Generate multiple characters using LLM.
        
        Args:
            context: CharacterContext with project data
            count: Number of characters to generate (1-5)
        
        Returns:
            Dict with 'success', 'characters', 'llm_used', 'error'
        """
        count = max(1, min(count, 5))  # Limit 1-5
        
        llm = self.get_llm()
        if not llm:
            return {
                'success': False,
                'error': 'Kein aktives LLM konfiguriert. Bitte im Control Center ein LLM aktivieren.'
            }
        
        prompt_config = self.PROMPTS['characters']
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(context=context_str, count=count),
            temperature=0.8,  # More creative for characters
            max_tokens=1500,
        )
        
        logger.info(f"Calling LLM {llm.name} for character generation (count={count})")
        response = generate_text(req)
        
        if not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler')
            logger.error(f"LLM error for character generation: {error_msg}")
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
            
            characters = json.loads(result_text)
            if not isinstance(characters, list):
                characters = [characters]
            
            logger.info(f"Successfully generated {len(characters)} characters using {llm.name}")
            
            # Publish event (only if feature flag enabled)
            event_bus.publish(
                Events.CHARACTER_CREATED,
                source="CharacterGenerationHandler",
                project_id=context.project_id,
                character_count=len(characters),
                llm_used=llm.name,
            )
            
            return {
                'success': True,
                'characters': characters,
                'llm_used': llm.name,
                'latency_ms': response.get('latency_ms')
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse character JSON: {e}, response: {result_text[:200]}")
            return {
                'success': False,
                'error': f'Fehler beim Parsen der KI-Antwort: {str(e)}',
                'raw_response': result_text,
                'llm_used': llm.name
            }
    
    def generate_character_details(self, context: CharacterContext, name: str, role: str) -> Dict[str, Any]:
        """
        Generate detailed attributes for a specific character.
        
        Args:
            context: CharacterContext with project data
            name: Character name
            role: Character role (protagonist, antagonist, etc.)
        
        Returns:
            Dict with 'success', 'data', 'llm_used', 'error'
        """
        llm = self.get_llm()
        if not llm:
            return {
                'success': False,
                'error': 'Kein aktives LLM konfiguriert.'
            }
        
        prompt_config = self.PROMPTS['details']
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(context=context_str, name=name, role=role),
            temperature=0.7,
            max_tokens=1000,
        )
        
        logger.info(f"Calling LLM {llm.name} for character details: {name} ({role})")
        response = generate_text(req)
        
        if not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler')
            logger.error(f"LLM error for character details: {error_msg}")
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
            
            details = json.loads(result_text)
            
            logger.info(f"Successfully generated details for {name} using {llm.name}")
            
            return {
                'success': True,
                'data': details,
                'llm_used': llm.name,
                'latency_ms': response.get('latency_ms')
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse details JSON: {e}")
            return {
                'success': False,
                'error': f'Fehler beim Parsen der KI-Antwort: {str(e)}',
                'raw_response': result_text,
                'llm_used': llm.name
            }


# Singleton instance
character_handler = CharacterGenerationHandler()
