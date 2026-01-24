"""OpenRouter Konfiguration für BFA Agent."""

from openai import AsyncOpenAI
from agents import set_default_openai_client, set_default_openai_api
import os
from dotenv import load_dotenv

load_dotenv()


def setup_openrouter(api_key: str | None = None) -> AsyncOpenAI:
    """Konfiguriert OpenRouter als LLM Backend.
    
    Args:
        api_key: OpenRouter API Key (oder aus OPENROUTER_API_KEY)
        
    Returns:
        Konfigurierter AsyncOpenAI Client
    """
    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY nicht gesetzt!")
    
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://bfa-agent.local",
            "X-Title": "BFA Agent - Explosionsschutz"
        }
    )
    
    # Global für alle Agents setzen
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")
    
    return client


class Models:
    """OpenRouter Model-IDs für BFA Agent.
    
    Zwei Modi:
    1. Direkte Model-IDs (z.B. "anthropic/claude-sonnet-4-20250514")
    2. Preset-IDs (z.B. "@preset/bfa-analyzer")
    
    Presets bieten:
    - Fallback-Konfiguration
    - System-Prompts
    - Provider-Präferenzen
    - Änderung ohne Code-Deployment
    """
    
    # ========================================
    # Direkte Model-IDs
    # ========================================
    
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
    
    # ========================================
    # Preset-IDs (empfohlen für Production)
    # ========================================
    
    # Hauptanalyse
    PRESET_ANALYZER = "@preset/bfa-analyzer"
    
    # Equipment-Prüfung
    PRESET_EQUIPMENT = "@preset/bfa-equipment"
    
    # CAD-Verarbeitung
    PRESET_CAD = "@preset/bfa-cad"
    
    # Report-Generierung
    PRESET_REPORT = "@preset/bfa-report"
    
    # Triage/Routing
    PRESET_TRIAGE = "@preset/bfa-triage"
    
    # Stoffdaten
    PRESET_SUBSTANCES = "@preset/bfa-substances"
    
    # Budget
    PRESET_BUDGET = "@preset/bfa-budget"
    
    # ========================================
    # Aktive Konfiguration
    # ========================================
    _use_presets = False  # Default: direkte Models
    
    @classmethod
    def use_presets(cls, enabled: bool = True):
        """Schaltet zwischen Presets und direkten Models um.
        
        Args:
            enabled: True für Presets, False für direkte Models
        """
        cls._use_presets = enabled
    
    @classmethod
    def for_analysis(cls) -> str:
        """Model für Analyse-Aufgaben."""
        return cls.PRESET_ANALYZER if cls._use_presets else cls.PRECISE
    
    @classmethod
    def for_equipment(cls) -> str:
        """Model für Equipment-Prüfung."""
        return cls.PRESET_EQUIPMENT if cls._use_presets else cls.PRECISE
    
    @classmethod
    def for_cad(cls) -> str:
        """Model für CAD-Verarbeitung."""
        return cls.PRESET_CAD if cls._use_presets else cls.FAST
    
    @classmethod
    def for_report(cls) -> str:
        """Model für Berichterstellung."""
        return cls.PRESET_REPORT if cls._use_presets else cls.CREATIVE
    
    @classmethod
    def for_triage(cls) -> str:
        """Model für Routing."""
        return cls.PRESET_TRIAGE if cls._use_presets else cls.FAST


class ModelWithFallback:
    """Erstellt Model-Konfiguration mit Fallbacks.
    
    Für Verwendung ohne OpenRouter Presets - Fallbacks werden
    via extra_body im API-Call übergeben.
    
    Beispiel:
        fallback = ModelWithFallback(
            primary="anthropic/claude-sonnet-4",
            fallbacks=["openai/gpt-4o", "google/gemini-flash"]
        )
    """
    
    def __init__(
        self,
        primary: str,
        fallbacks: list[str] | None = None,
        provider_sort: str = "quality"
    ):
        self.primary = primary
        self.fallbacks = fallbacks or []
        self.provider_sort = provider_sort
    
    def to_extra_body(self) -> dict:
        """Erstellt extra_body für OpenAI SDK."""
        body = {}
        
        if self.fallbacks:
            body["models"] = [self.primary] + self.fallbacks
            body["route"] = "fallback"
        
        body["provider"] = {"sort": self.provider_sort}
        
        return body
