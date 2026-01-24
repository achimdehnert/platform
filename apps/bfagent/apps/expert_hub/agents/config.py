"""OpenRouter Konfiguration für BFA Agent."""

import os

# Django settings import (optional - für standalone use)
try:
    from django.conf import settings as django_settings
except ImportError:
    django_settings = None


def setup_openrouter(api_key: str | None = None):
    """Konfiguriert OpenRouter als LLM Backend.
    
    Args:
        api_key: OpenRouter API Key (oder aus Settings/Env)
        
    Returns:
        Konfigurierter Client
    """
    api_key = api_key or (getattr(django_settings, 'OPENROUTER_API_KEY', None) if django_settings else None) or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY nicht gesetzt!")
    
    # Lazy import to avoid issues if openai-agents not installed
    try:
        from openai import AsyncOpenAI
        from agents import set_default_openai_client, set_default_openai_api
        
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://bfagent.iil.pet",
                "X-Title": "BFA Agent - Explosionsschutz"
            }
        )
        
        set_default_openai_client(client)
        set_default_openai_api("chat_completions")
        
        return client
    except ImportError:
        # Fallback wenn openai-agents nicht installiert
        return None


class Models:
    """OpenRouter Model-IDs für BFA Agent."""
    
    # Schnell & günstig
    FAST = "google/gemini-2.0-flash-001"
    
    # Präzise
    PRECISE = "anthropic/claude-sonnet-4-20250514"
    
    # Kreativ
    CREATIVE = "openai/gpt-4o"
    
    # Fallback
    FALLBACK = "meta-llama/llama-3.3-70b-instruct"
    
    # Budget
    BUDGET = "openai/gpt-4o-mini"
    
    # Preset-IDs (für OpenRouter Presets)
    PRESET_ANALYZER = "@preset/bfa-analyzer"
    PRESET_EQUIPMENT = "@preset/bfa-equipment"
    PRESET_CAD = "@preset/bfa-cad"
    PRESET_REPORT = "@preset/bfa-report"
    PRESET_TRIAGE = "@preset/bfa-triage"
    
    _use_presets = False
    
    @classmethod
    def use_presets(cls, enabled: bool = True):
        """Schaltet zwischen Presets und direkten Models um."""
        cls._use_presets = enabled
    
    @classmethod
    def for_analysis(cls) -> str:
        return cls.PRESET_ANALYZER if cls._use_presets else cls.PRECISE
    
    @classmethod
    def for_equipment(cls) -> str:
        return cls.PRESET_EQUIPMENT if cls._use_presets else cls.PRECISE
    
    @classmethod
    def for_cad(cls) -> str:
        return cls.PRESET_CAD if cls._use_presets else cls.FAST
    
    @classmethod
    def for_report(cls) -> str:
        return cls.PRESET_REPORT if cls._use_presets else cls.CREATIVE
    
    @classmethod
    def for_triage(cls) -> str:
        return cls.PRESET_TRIAGE if cls._use_presets else cls.FAST
