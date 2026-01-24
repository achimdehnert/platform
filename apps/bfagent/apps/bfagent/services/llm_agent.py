"""
Zentraler LLM-Agent - Single Source of Truth für alle LLM-Aufrufe.

Features:
- Intelligentes Model-Routing
- Response-Caching
- Cost-Tracking (in DB via Controlling Models)
- Automatischer Fallback
- Usage Logging für Controlling Dashboard

Nutzt den LLM MCP Gateway als Backend.
"""
import hashlib
import json
import logging
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from functools import lru_cache
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Gateway URL - kann über Settings überschrieben werden
LLM_GATEWAY_URL = getattr(settings, 'LLM_GATEWAY_URL', 'http://127.0.0.1:8100')


@dataclass
class LLMResponse:
    """Einheitliche Response-Struktur für alle LLM-Aufrufe."""
    success: bool
    content: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    model_used: Optional[str] = None
    cost_estimate: float = 0.0
    error: Optional[str] = None
    cached: bool = False
    latency_ms: float = 0.0


@dataclass
class ModelPreference:
    """Präferenzen für Model-Auswahl."""
    quality: str = "balanced"  # "fast", "balanced", "best"
    max_cost_per_call: float = 0.01  # Max Kosten pro Aufruf
    preferred_provider: Optional[str] = None  # "openai", "groq", etc.


class LLMAgent:
    """
    Zentraler Agent für alle LLM-Aufrufe im System.
    
    Usage:
        agent = LLMAgent()
        
        # Einfacher Aufruf
        response = agent.generate("Schreibe eine kurze Geschichte")
        
        # Mit Model-ID
        response = agent.generate("...", model_id=8)
        
        # Mit Präferenzen
        response = agent.generate("...", preferences=ModelPreference(quality="fast"))
    """
    
    # Model-Kategorien für intelligentes Routing
    MODEL_TIERS = {
        "fast": [26, 27],      # Groq Llama 3.1 8B, Compound Mini
        "balanced": [8, 11],   # GPT-4o Mini, Gemini Flash
        "best": [7, 30],       # GPT-4o, Groq Compound
    }
    
    # Fallback-Kette
    FALLBACK_CHAIN = [8, 26, 11]  # GPT-4o Mini -> Groq -> Gemini
    
    def __init__(self, gateway_url: str = None):
        self.gateway_url = gateway_url or LLM_GATEWAY_URL
        self._models_cache: Optional[List[Dict]] = None
        self._models_cache_time: float = 0
        
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_id: Optional[int] = None,
        preferences: Optional[ModelPreference] = None,
        response_format: str = "text",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> LLMResponse:
        """
        Führt einen LLM-Aufruf durch.
        
        Args:
            prompt: Der User-Prompt
            system_prompt: Optional System-Prompt
            model_id: Explizite Model-ID (überschreibt Routing)
            preferences: Model-Präferenzen für Routing
            response_format: "text", "json", "markdown"
            temperature: 0.0 - 2.0
            max_tokens: Max Output Tokens
            use_cache: Response cachen?
            cache_ttl: Cache-Lebenszeit in Sekunden
            
        Returns:
            LLMResponse mit Ergebnis oder Fehler
        """
        start_time = time.time()
        
        # 1. Cache-Check
        if use_cache:
            cache_key = self._make_cache_key(prompt, system_prompt, model_id, response_format)
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.info(f"LLM Cache Hit: {cache_key[:20]}...")
                cached_response['cached'] = True
                cached_response['latency_ms'] = (time.time() - start_time) * 1000
                return LLMResponse(**cached_response)
        
        # 2. Model-Routing
        if model_id is None:
            model_id = self._select_model(preferences or ModelPreference())
        
        # 3. LLM-Aufruf mit Fallback
        response = self._call_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            model_id=model_id,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        response.latency_ms = (time.time() - start_time) * 1000
        
        # 4. Cache speichern bei Erfolg
        if use_cache and response.success:
            cache_data = {
                'success': response.success,
                'content': response.content,
                'usage': response.usage,
                'model_used': response.model_used,
                'cost_estimate': response.cost_estimate,
            }
            cache.set(cache_key, cache_data, cache_ttl)
            logger.info(f"LLM Cache Set: {cache_key[:20]}... TTL={cache_ttl}s")
        
        # 5. Cost-Tracking (asynchron in DB speichern)
        self._track_cost(
            response,
            agent_name=getattr(self, '_current_agent', 'direct'),
            task_name=getattr(self, '_current_task', 'generate'),
            fallback_used=getattr(response, '_fallback_used', False),
        )
        
        return response
    
    def generate_for_agent(
        self,
        prompt: str,
        agent_name: str,
        task_name: str,
        **kwargs
    ) -> LLMResponse:
        """
        Generate mit Agent-Kontext für Controlling.
        
        Usage:
            response = agent.generate_for_agent(
                "Validiere diesen Code",
                agent_name="DjangoAgent",
                task_name="validate_view"
            )
        """
        self._current_agent = agent_name
        self._current_task = task_name
        try:
            return self.generate(prompt, **kwargs)
        finally:
            self._current_agent = 'direct'
            self._current_task = 'generate'
    
    def list_models(self, refresh: bool = False) -> List[Dict]:
        """Liste verfügbare Models."""
        # Cache für 5 Minuten
        if not refresh and self._models_cache and (time.time() - self._models_cache_time) < 300:
            return self._models_cache
        
        try:
            r = requests.get(f"{self.gateway_url}/models", timeout=5)
            if r.status_code == 200:
                data = r.json()
                self._models_cache = data.get('models', [])
                self._models_cache_time = time.time()
                return self._models_cache
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        
        return []
    
    def health_check(self) -> bool:
        """Prüfe ob Gateway erreichbar ist."""
        try:
            r = requests.get(f"{self.gateway_url}/health", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    # --- Private Methods ---
    
    def _select_model(self, preferences: ModelPreference) -> int:
        """Wähle Model basierend auf Präferenzen."""
        tier = preferences.quality
        
        # Preferred Provider?
        if preferences.preferred_provider:
            models = self.list_models()
            for m in models:
                if m['provider'] == preferences.preferred_provider:
                    return m['id']
        
        # Tier-basierte Auswahl
        tier_models = self.MODEL_TIERS.get(tier, self.MODEL_TIERS['balanced'])
        
        # Prüfe welche Models verfügbar sind
        available = self.list_models()
        available_ids = {m['id'] for m in available}
        
        for model_id in tier_models:
            if model_id in available_ids:
                return model_id
        
        # Fallback zum ersten verfügbaren
        if available:
            return available[0]['id']
        
        # Default
        return 8  # GPT-4o Mini
    
    def _call_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model_id: int,
        response_format: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Rufe LLM auf mit automatischem Fallback."""
        
        # Versuche primäres Model
        response = self._call_gateway(
            prompt, system_prompt, model_id, response_format, temperature, max_tokens
        )
        
        if response.success:
            return response
        
        # Fallback-Kette durchlaufen
        logger.warning(f"Primary model {model_id} failed: {response.error}")
        
        for fallback_id in self.FALLBACK_CHAIN:
            if fallback_id == model_id:
                continue  # Skip bereits versuchtes Model
            
            logger.info(f"Trying fallback model {fallback_id}")
            response = self._call_gateway(
                prompt, system_prompt, fallback_id, response_format, temperature, max_tokens
            )
            
            if response.success:
                logger.info(f"Fallback to model {fallback_id} succeeded")
                return response
        
        # Alle Fallbacks fehlgeschlagen
        return LLMResponse(
            success=False,
            error=f"All models failed. Last error: {response.error}"
        )
    
    def _call_gateway(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model_id: int,
        response_format: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Einzelner Gateway-Aufruf."""
        try:
            payload = {
                "prompt": prompt,
                "model": str(model_id),
                "response_format": response_format,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system_prompt:
                payload["system_prompt"] = system_prompt
            
            r = requests.post(
                f"{self.gateway_url}/generate",
                json=payload,
                timeout=60
            )
            
            data = r.json()
            
            return LLMResponse(
                success=data.get('success', False),
                content=data.get('content'),
                usage=data.get('usage'),
                model_used=data.get('model_used'),
                cost_estimate=data.get('cost_estimate', 0.0),
                error=data.get('error'),
            )
            
        except requests.Timeout:
            return LLMResponse(success=False, error="Gateway timeout")
        except requests.ConnectionError:
            return LLMResponse(success=False, error="Gateway not reachable")
        except Exception as e:
            return LLMResponse(success=False, error=str(e))
    
    def _make_cache_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model_id: Optional[int],
        response_format: str,
    ) -> str:
        """Erstelle eindeutigen Cache-Key."""
        key_data = f"{prompt}|{system_prompt}|{model_id}|{response_format}"
        return f"llm_agent:{hashlib.sha256(key_data.encode()).hexdigest()[:32]}"
    
    def _track_cost(
        self,
        response: LLMResponse,
        agent_name: str = "direct",
        task_name: str = "generate",
        fallback_used: bool = False,
    ):
        """
        Tracke Kosten und Usage in der Controlling-Datenbank.
        
        Läuft asynchron im Hintergrund um Performance nicht zu beeinflussen.
        """
        # Log immer
        if response.cost_estimate > 0:
            logger.info(
                f"LLM Cost: {response.model_used} - "
                f"${response.cost_estimate:.6f} - "
                f"Tokens: {response.usage}"
            )
        
        # In DB speichern (async)
        def _save_to_db():
            try:
                from apps.bfagent.models_controlling import LLMUsageLog
                
                # Provider aus Model-Name extrahieren
                provider = "unknown"
                model = response.model_used or "unknown"
                if "gpt" in model.lower():
                    provider = "openai"
                elif "llama" in model.lower() or "groq" in model.lower():
                    provider = "groq"
                elif "gemini" in model.lower():
                    provider = "gemini"
                elif "claude" in model.lower():
                    provider = "anthropic"
                
                # Usage extrahieren
                usage = response.usage or {}
                tokens_in = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0) or usage.get("output_tokens", 0)
                
                LLMUsageLog.objects.create(
                    agent=agent_name,
                    task=task_name,
                    model=model,
                    provider=provider,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=Decimal(str(response.cost_estimate)),
                    latency_ms=response.latency_ms,
                    cached=response.cached,
                    fallback_used=fallback_used,
                    success=response.success,
                    error_message=response.error,
                )
            except Exception as e:
                logger.warning(f"Failed to save LLM usage to DB: {e}")
        
        # Im Hintergrund-Thread speichern
        thread = threading.Thread(target=_save_to_db, daemon=True)
        thread.start()


# Singleton-Instanz für einfache Nutzung
_agent_instance: Optional[LLMAgent] = None


def get_llm_agent() -> LLMAgent:
    """Hole Singleton LLM-Agent Instanz."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = LLMAgent()
    return _agent_instance


# Convenience-Funktionen
def llm_generate(prompt: str, **kwargs) -> LLMResponse:
    """Shortcut für agent.generate()."""
    return get_llm_agent().generate(prompt, **kwargs)


def llm_generate_json(prompt: str, **kwargs) -> LLMResponse:
    """Shortcut für JSON-Response."""
    return get_llm_agent().generate(prompt, response_format="json", **kwargs)
