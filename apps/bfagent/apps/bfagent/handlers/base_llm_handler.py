"""
Base LLM Handler
================

Standardized base class for all handlers that use LLM.
Provides consistent LLM selection, request building, and error handling.

Usage:
    class MyHandler(BaseLLMHandler):
        phase_name = 'my_phase'  # For WorkflowPhaseLLMConfig lookup
        
        def do_something(self, text):
            return self.call_llm(
                system="You are helpful.",
                prompt=f"Process: {text}",
                max_tokens=2000
            )
"""

import json
import logging
from abc import ABC
from typing import Any, Dict, Optional

from apps.bfagent.models import Llms
from apps.bfagent.services.llm_client import LlmRequest, generate_text

logger = logging.getLogger(__name__)


class BaseLLMHandler(ABC):
    """
    Base class for all handlers that need LLM access.
    
    Provides:
    - Consistent LLM selection (WorkflowPhaseLLMConfig → llm_id → fallback)
    - Standard call_llm() method
    - JSON parsing with error handling
    - Logging
    
    Subclasses should set:
    - phase_name: str - for WorkflowPhaseLLMConfig lookup (e.g., 'editing', 'illustration')
    """
    
    phase_name: str = 'default'  # Override in subclass
    
    def __init__(self, llm_id: Optional[int] = None):
        """
        Initialize handler.
        
        Args:
            llm_id: Optional specific LLM ID to use
        """
        self.llm_id = llm_id
        self._llm: Optional[Llms] = None
    
    def get_llm(self) -> Optional[Llms]:
        """
        Get the LLM to use for this handler.
        
        Priority:
        1. Cached LLM (if already resolved)
        2. WorkflowPhaseLLMConfig for phase_name
        3. Specific llm_id if provided
        4. Any active LLM (fallback)
        """
        if self._llm:
            return self._llm
        
        # 1. Try WorkflowPhaseLLMConfig
        try:
            from apps.writing_hub.models import WorkflowPhaseLLMConfig
            self._llm = WorkflowPhaseLLMConfig.get_llm_for_phase(self.phase_name)
            if self._llm:
                logger.debug(f"[{self.__class__.__name__}] Using workflow config LLM: {self._llm.name}")
                return self._llm
        except Exception:
            pass
        
        # 2. Try specific LLM ID
        if self.llm_id:
            try:
                self._llm = Llms.objects.get(id=self.llm_id, is_active=True)
                logger.debug(f"[{self.__class__.__name__}] Using specified LLM ID {self.llm_id}")
                return self._llm
            except Llms.DoesNotExist:
                pass
        
        # 3. Fallback - prefer fast/cheap models (Groq, Ollama) over expensive ones
        # Try Groq first (fast and free)
        self._llm = Llms.objects.filter(
            is_active=True, 
            provider__icontains='groq'
        ).first()
        
        if not self._llm:
            # Try Ollama (local, free)
            self._llm = Llms.objects.filter(
                is_active=True,
                provider__icontains='ollama'
            ).first()
        
        if not self._llm:
            # Any active LLM as last resort
            self._llm = Llms.objects.filter(is_active=True).first()
        
        if self._llm:
            logger.debug(f"[{self.__class__.__name__}] Using fallback LLM: {self._llm.name} ({self._llm.provider})")
        
        return self._llm
    
    def call_llm(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        parse_json: bool = False
    ) -> Dict[str, Any]:
        """
        Call the LLM with standardized error handling.
        
        Args:
            system: System prompt
            prompt: User prompt
            temperature: LLM temperature (default 0.3)
            max_tokens: Max tokens (default 2000)
            parse_json: If True, parse response as JSON
            
        Returns:
            Dict with:
            - success: bool
            - text: str (raw response) or data: dict (if parse_json=True)
            - error: str (if failed)
            - llm_name: str
        """
        llm = self.get_llm()
        if not llm:
            return {
                'success': False,
                'error': 'Kein LLM konfiguriert. Bitte im Control Center ein LLM aktivieren.'
            }
        
        request = LlmRequest(
            provider=llm.provider,
            api_endpoint=llm.api_endpoint,
            api_key=llm.api_key,
            model=llm.llm_name,
            system=system,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        try:
            response = generate_text(request)
            
            if not response or not response.get('ok'):
                error = response.get('error', 'Unknown error') if response else 'No response'
                logger.error(f"[{self.__class__.__name__}] LLM error: {error}")
                return {
                    'success': False,
                    'error': f'LLM-Fehler: {error}',
                    'llm_name': llm.name
                }
            
            text = response.get('text', '')
            
            if parse_json:
                try:
                    data = self._parse_json(text)
                    return {
                        'success': True,
                        'data': data,
                        'llm_name': llm.name,
                        'tokens': response.get('usage', {}).get('total_tokens', 0)
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"[{self.__class__.__name__}] JSON parse error: {e}")
                    return {
                        'success': False,
                        'error': f'JSON-Fehler: {e}',
                        'raw_text': text[:500],
                        'llm_name': llm.name
                    }
            
            return {
                'success': True,
                'text': text,
                'llm_name': llm.name,
                'tokens': response.get('usage', {}).get('total_tokens', 0)
            }
            
        except Exception as e:
            logger.exception(f"[{self.__class__.__name__}] Exception in LLM call")
            return {
                'success': False,
                'error': str(e),
                'llm_name': llm.name if llm else None
            }
    
    def _parse_json(self, text: str) -> Any:
        """Parse JSON, handling markdown code blocks."""
        cleaned = text.strip()
        if cleaned.startswith('```'):
            lines = [l for l in cleaned.split('\n') if not l.strip().startswith('```')]
            cleaned = '\n'.join(lines)
        return json.loads(cleaned)
