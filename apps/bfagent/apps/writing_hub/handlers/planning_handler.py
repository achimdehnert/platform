"""
Planning Generation Handler
Generates premise, logline, and themes for book projects using LLM.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlanningContext:
    """Context for planning generation"""
    project_id: int
    title: str = ""
    genre: str = ""
    description: str = ""
    target_audience: str = ""
    custom_context: Dict[str, str] = None
    worlds: List[Dict[str, str]] = None  # World context from V2 World system
    
    def __post_init__(self):
        if self.custom_context is None:
            self.custom_context = {}
        if self.worlds is None:
            self.worlds = []
    
    def to_prompt_context(self) -> str:
        """Build context string for LLM prompt"""
        parts = []
        if self.title:
            parts.append(f"Titel: {self.title}")
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.description:
            parts.append(f"Beschreibung: {self.description}")
        if self.target_audience:
            parts.append(f"Zielgruppe: {self.target_audience}")
        
        for key, value in self.custom_context.items():
            if value and key not in ['description', 'genre', 'title']:
                parts.append(f"{key.title()}: {value}")
        
        # Add world context if available
        if self.worlds:
            parts.append("\n--- WELT-KONTEXT ---")
            for world in self.worlds:
                parts.append(f"\nWelt: {world.get('name', 'Unbenannt')}")
                if world.get('world_type'):
                    parts.append(f"  Typ: {world['world_type']}")
                if world.get('description'):
                    parts.append(f"  Beschreibung: {world['description'][:300]}")
                if world.get('geography'):
                    parts.append(f"  Geographie: {world['geography'][:200]}")
                if world.get('culture'):
                    parts.append(f"  Kultur: {world['culture'][:200]}")
                if world.get('magic_system'):
                    parts.append(f"  Magie: {world['magic_system'][:200]}")
                if world.get('technology_level'):
                    parts.append(f"  Technologie: {world['technology_level'][:100]}")
        
        return "\n".join(parts)


class PlanningGenerationHandler:
    """
    Handler for generating planning elements (premise, logline, themes)
    using an assigned LLM.
    
    Usage:
        handler = PlanningGenerationHandler()
        result = handler.generate_premise(context)
    """
    
    PROMPTS = {
        'premise': {
            'system': "Du bist ein erfahrener Autor. Schreibe prägnant und kreativ auf Deutsch.",
            'user': """Erstelle eine Premise (Kernidee) für folgendes Buchprojekt:

{context}

Die Premise sollte 2-3 Sätze lang sein und das Herz der Geschichte beschreiben.
Antworte NUR mit der Premise, ohne Einleitung oder Erklärung."""
        },
        'themes': {
            'system': "Du bist ein Literaturexperte. Antworte auf Deutsch.",
            'user': """Schlage 4 passende Themen für folgendes Buchprojekt vor:

{context}

Antworte NUR mit den Themen, getrennt durch Kommas.
Beispiel: Selbstfindung, Macht, Freundschaft, Verrat"""
        },
        'logline': {
            'system': "Du bist ein Drehbuchautor. Schreibe prägnant auf Deutsch.",
            'user': """Erstelle eine Logline für folgendes Buchprojekt:

{context}

Eine Logline ist EIN Satz nach dem Schema:
"Wenn [Protagonist] [Herausforderung] begegnet, muss [er/sie] [Handlung], bevor [Konsequenz]."

Antworte NUR mit der Logline."""
        }
    }
    
    # Default LLM ID for planning (can be overridden via WorkflowPhaseLLM config)
    DEFAULT_LLM_ID = 8  # GPT-4 Turbo
    
    def __init__(self, llm_id: Optional[int] = None):
        """
        Initialize handler with optional specific LLM.
        
        Args:
            llm_id: Specific LLM ID to use, or None for default (ID 8)
        """
        self.llm_id = llm_id or self.DEFAULT_LLM_ID
        self._llm = None
    
    def get_llm(self):
        """Get the LLM to use - checks WorkflowPhaseLLMConfig first, then fallback"""
        if self._llm:
            return self._llm
        
        from apps.bfagent.models import Llms
        from apps.writing_hub.models import WorkflowPhaseLLMConfig
        
        # 1. Try WorkflowPhaseLLMConfig for 'planning' phase
        config_llm = WorkflowPhaseLLMConfig.get_llm_for_phase('planning')
        if config_llm:
            self._llm = config_llm
            logger.info(f"Using workflow config LLM: {self._llm.name}")
            return self._llm
        
        # 2. Try specific LLM ID (default or passed)
        if self.llm_id:
            self._llm = Llms.objects.filter(id=self.llm_id, is_active=True).first()
            if self._llm:
                logger.info(f"Using default LLM ID {self.llm_id}: {self._llm.name}")
                return self._llm
        
        # 3. Fallback: Prefer OpenAI
        self._llm = Llms.objects.filter(
            is_active=True, 
            provider__icontains='openai'
        ).first()
        
        if self._llm:
            logger.info(f"Fallback to OpenAI LLM: {self._llm.name}")
            return self._llm
        
        # 4. Last resort: any active LLM
        self._llm = Llms.objects.filter(is_active=True).first()
        if self._llm:
            logger.info(f"Using any active LLM: {self._llm.name}")
        
        return self._llm
    
    def generate(self, element: str, context: PlanningContext) -> Dict[str, Any]:
        """
        Generate a planning element using LLM.
        
        Args:
            element: 'premise', 'themes', or 'logline'
            context: PlanningContext with project data
        
        Returns:
            Dict with 'success', 'result', 'llm_used', 'error'
        """
        if element not in self.PROMPTS:
            return {
                'success': False,
                'error': f'Unbekanntes Element: {element}'
            }
        
        llm = self.get_llm()
        if not llm:
            return {
                'success': False,
                'error': 'Kein aktives LLM konfiguriert. Bitte im Control Center ein LLM aktivieren.'
            }
        
        prompt_config = self.PROMPTS[element]
        context_str = context.to_prompt_context()
        
        from apps.bfagent.services.llm_client import LlmRequest, generate_text
        
        req = LlmRequest(
            provider=llm.provider or 'openai',
            api_endpoint=llm.api_endpoint or 'https://api.openai.com',
            api_key=llm.api_key or '',
            model=llm.llm_name or 'gpt-4o-mini',
            system=prompt_config['system'],
            prompt=prompt_config['user'].format(context=context_str),
            temperature=0.7,
            max_tokens=500,
        )
        
        logger.info(f"Calling LLM {llm.name} for {element} generation")
        response = generate_text(req)
        
        if not response.get('ok'):
            error_msg = response.get('error', 'Unbekannter Fehler')
            logger.error(f"LLM error for {element}: {error_msg}")
            return {
                'success': False,
                'error': f"LLM Fehler: {error_msg}",
                'llm_used': llm.name
            }
        
        result_text = response.get('text', '').strip()
        
        # Parse themes as list
        if element == 'themes':
            result = [t.strip() for t in result_text.split(',') if t.strip()]
        else:
            result = result_text
        
        logger.info(f"Successfully generated {element} using {llm.name}")
        
        return {
            'success': True,
            'result': result,
            'element': element,
            'llm_used': llm.name,
            'latency_ms': response.get('latency_ms')
        }
    
    def generate_premise(self, context: PlanningContext) -> Dict[str, Any]:
        """Generate premise"""
        return self.generate('premise', context)
    
    def generate_themes(self, context: PlanningContext) -> Dict[str, Any]:
        """Generate themes"""
        return self.generate('themes', context)
    
    def generate_logline(self, context: PlanningContext) -> Dict[str, Any]:
        """Generate logline"""
        return self.generate('logline', context)


# Singleton instance
planning_handler = PlanningGenerationHandler()
