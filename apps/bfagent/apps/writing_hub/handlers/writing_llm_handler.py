"""
Writing LLM Handler - Handles LLM calls for different content types and phases
Supports OpenAI and Anthropic via the existing LLM infrastructure
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from django.conf import settings
from apps.bfagent.models import Llms, DomainType, DomainPhase

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """Request structure for LLM calls"""
    content_type: str  # novel, essay, scientific
    phase: str  # concept, characters, writing, etc.
    context: Dict[str, Any]  # Project context
    user_input: Dict[str, Any]  # User-provided data
    llm_id: Optional[int] = None  # Specific LLM to use


@dataclass
class LLMResponse:
    """Response structure from LLM calls"""
    success: bool
    content: Dict[str, Any]
    tokens_used: int = 0
    model_used: str = ""
    error: Optional[str] = None


class WritingLLMHandler:
    """
    Handler for LLM calls in the Writing Hub
    
    Usage:
        handler = WritingLLMHandler()
        response = handler.generate(
            content_type="novel",
            phase="characters",
            context={"project_title": "My Novel", "genre": "Fantasy"},
            user_input={"name": "Aldric", "role": "protagonist"}
        )
    """
    
    def __init__(self, llm_id: Optional[int] = None):
        """
        Initialize handler with optional specific LLM
        
        Args:
            llm_id: ID of LLM to use, or None for default
        """
        self.llm = self._get_llm(llm_id)
        self._client = None
    
    def _get_llm(self, llm_id: Optional[int] = None) -> Optional[Llms]:
        """Get LLM configuration from database"""
        try:
            if llm_id:
                return Llms.objects.get(id=llm_id, is_active=True)
            # Get default active LLM
            return Llms.objects.filter(is_active=True).first()
        except Llms.DoesNotExist:
            logger.warning(f"LLM with id {llm_id} not found")
            return None
    
    def _get_phase_config(self, content_type: str, phase: str) -> Optional[Dict[str, Any]]:
        """Get LLM configuration for a specific content type and phase"""
        try:
            domain_phase = DomainPhase.objects.select_related(
                'domain_type', 'workflow_phase'
            ).get(
                domain_type__slug=content_type,
                workflow_phase__name=phase,
                is_active=True
            )
            return domain_phase.config
        except DomainPhase.DoesNotExist:
            logger.warning(f"No phase config found for {content_type}/{phase}")
            return None
    
    def _build_prompt(self, phase_config: Dict[str, Any], context: Dict[str, Any], 
                      user_input: Dict[str, Any]) -> tuple[str, str]:
        """
        Build system and user prompts from phase config
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = phase_config.get("llm_system_prompt", "Du bist ein hilfreicher Schreibassistent.")
        user_template = phase_config.get("llm_user_template", "{input}")
        
        # Merge context and user_input for template substitution
        all_vars = {**context, **user_input}
        
        # Safe template substitution
        try:
            system_prompt = system_prompt.format(**all_vars)
        except KeyError:
            pass  # Keep original if variable missing
        
        try:
            user_prompt = user_template.format(**all_vars)
        except KeyError:
            user_prompt = str(user_input)
        
        return system_prompt, user_prompt
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call OpenAI API"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.llm.api_key or settings.OPENAI_API_KEY
            )
            
            response = client.chat.completions.create(
                model=self.llm.llm_name or "gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens if response.usage else 0
            
            # Track usage
            if self.llm:
                self.llm.track_usage(tokens)
            
            return LLMResponse(
                success=True,
                content={"generated_text": content},
                tokens_used=tokens,
                model_used=self.llm.llm_name or "gpt-4"
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return LLMResponse(success=False, content={}, error=str(e))
    
    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Call Anthropic API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(
                api_key=self.llm.api_key or settings.ANTHROPIC_API_KEY
            )
            
            response = client.messages.create(
                model=self.llm.llm_name or "claude-3-sonnet-20240229",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.content[0].text
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
            # Track usage
            if self.llm:
                self.llm.track_usage(tokens)
            
            return LLMResponse(
                success=True,
                content={"generated_text": content},
                tokens_used=tokens,
                model_used=self.llm.llm_name or "claude-3-sonnet"
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return LLMResponse(success=False, content={}, error=str(e))
    
    def _generate_mock(self, content_type: str, phase: str, 
                       context: Dict[str, Any], user_input: Dict[str, Any]) -> LLMResponse:
        """Generate mock response when no LLM is available"""
        logger.info(f"Using mock generation for {content_type}/{phase}")
        
        mock_responses = {
            ("novel", "concept"): {
                "generated_text": f"""## Konzept für "{context.get('title', 'Unbekannt')}"

**Genre:** {context.get('genre', 'Fantasy')}
**Zielgruppe:** {context.get('target_audience', 'Erwachsene')}

### Prämisse
Eine fesselnde Geschichte über Mut, Freundschaft und die Suche nach Identität in einer Welt voller Geheimnisse.

### Themen
- Selbstfindung und persönliches Wachstum
- Die Macht der Freundschaft
- Gut gegen Böse

### Einzigartiges Element
[Hier dein USP einfügen]

*Dies ist ein Mock-Vorschlag. Aktiviere einen LLM für echte KI-Generierung.*"""
            },
            ("novel", "characters"): {
                "generated_text": f"""## Charakter: {user_input.get('name', 'Unbekannt')}

**Rolle:** {user_input.get('role', 'Protagonist')}
**Alter:** {user_input.get('age', '25')} Jahre

### Erscheinung
Markante Gesichtszüge, die Entschlossenheit und innere Stärke ausstrahlen.

### Persönlichkeit
Mutig, aber mit verborgenen Zweifeln. Loyal zu Freunden, misstrauisch gegenüber Fremden.

### Motivation
Die Wahrheit über die eigene Vergangenheit entdecken.

### Innerer Konflikt
Zwischen Pflichtgefühl und persönlichen Wünschen hin- und hergerissen.

### Hintergrund
Eine mysteriöse Kindheit mit Erinnerungslücken prägt das Weltbild.

### Charakterbogen
Von Unsicherheit zu Selbstakzeptanz und wahrer Stärke.

*Mock-Vorschlag - LLM für detailliertere Charaktere aktivieren.*"""
            },
            ("essay", "concept"): {
                "generated_text": f"""## These zum Thema: {context.get('topic', 'Unbekannt')}

**Perspektive:** {context.get('perspective', 'Analytisch')}

### Hauptthese
[Deine zentrale Behauptung hier]

### Unterstützende Argumente
1. Erstes Hauptargument mit Belegen
2. Zweites Hauptargument mit Beispielen
3. Drittes Hauptargument mit Daten

### Gegenposition
Anerkennung alternativer Sichtweisen und deren Widerlegung.

*Mock-Vorschlag für Essay-Konzept.*"""
            },
            ("scientific", "concept"): {
                "generated_text": f"""## Forschungskonzept: {context.get('topic', 'Unbekannt')}

**Fachgebiet:** {context.get('field', 'Allgemein')}

### Forschungsfrage
Wie beeinflusst [Variable X] den Effekt von [Variable Y] auf [Outcome Z]?

### Hypothese
H1: Es besteht ein signifikanter positiver Zusammenhang zwischen X und Y.
H0: Es besteht kein signifikanter Zusammenhang.

### Forschungsziele
1. Quantitative Analyse der Zusammenhänge
2. Identifikation von Einflussfaktoren
3. Entwicklung eines theoretischen Modells

### Erwarteter Beitrag
Schließung einer Forschungslücke im Bereich [Fachgebiet].

*Mock-Vorschlag für wissenschaftliches Konzept.*"""
            },
        }
        
        key = (content_type, phase)
        mock_content = mock_responses.get(key, {
            "generated_text": f"Mock-Inhalt für {content_type}/{phase}. Aktiviere einen LLM für echte Generierung."
        })
        
        return LLMResponse(
            success=True,
            content=mock_content,
            tokens_used=0,
            model_used="mock"
        )
    
    def generate(self, content_type: str, phase: str, 
                 context: Dict[str, Any], user_input: Dict[str, Any],
                 use_mock: bool = False) -> LLMResponse:
        """
        Generate content using LLM
        
        Args:
            content_type: Type of content (novel, essay, scientific)
            phase: Current phase (concept, characters, writing, etc.)
            context: Project context (title, genre, etc.)
            user_input: User-provided data for this generation
            use_mock: Force mock response (for testing)
            
        Returns:
            LLMResponse with generated content
        """
        # Get phase configuration
        phase_config = self._get_phase_config(content_type, phase)
        if not phase_config:
            logger.warning(f"No config for {content_type}/{phase}, using defaults")
            phase_config = {}
        
        # Use mock if requested or no LLM available
        if use_mock or not self.llm:
            return self._generate_mock(content_type, phase, context, user_input)
        
        # Build prompts
        system_prompt, user_prompt = self._build_prompt(phase_config, context, user_input)
        
        # Call appropriate provider
        provider = self.llm.provider.lower() if self.llm.provider else "openai"
        
        if provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        else:
            logger.warning(f"Unknown provider {provider}, using mock")
            return self._generate_mock(content_type, phase, context, user_input)
    
    @classmethod
    def get_available_llms(cls) -> list[Dict[str, Any]]:
        """Get list of available LLMs for UI selection"""
        llms = Llms.objects.filter(is_active=True).values(
            'id', 'name', 'provider', 'llm_name'
        )
        return list(llms)


# Convenience function for views
def generate_content(content_type: str, phase: str, context: Dict[str, Any],
                     user_input: Dict[str, Any], llm_id: Optional[int] = None,
                     use_mock: bool = False) -> Dict[str, Any]:
    """
    Convenience function for generating content from views
    
    Returns dict with:
        - success: bool
        - content: dict with generated_text
        - error: str if failed
    """
    handler = WritingLLMHandler(llm_id=llm_id)
    response = handler.generate(content_type, phase, context, user_input, use_mock=use_mock)
    
    return {
        "success": response.success,
        "content": response.content,
        "tokens_used": response.tokens_used,
        "model_used": response.model_used,
        "error": response.error
    }
