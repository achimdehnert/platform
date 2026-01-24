"""OpenRouter Presets für BFA Agent.

Presets ermöglichen:
- Model-Wechsel ohne Code-Änderung
- Fallback-Konfiguration
- Provider-Auswahl (Preis, Latenz, Qualität)
- System-Prompts zentral verwalten
- A/B Testing verschiedener Modelle

Setup:
1. Presets in OpenRouter UI anlegen: https://openrouter.ai/settings/presets
2. Im Code via @preset/slug referenzieren
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import json
from pathlib import Path


class ProviderSort(str, Enum):
    """Sortierung für Provider-Auswahl."""
    PRICE = "price"           # Günstigster zuerst
    LATENCY = "latency"       # Schnellster zuerst (TTFT)
    THROUGHPUT = "throughput" # Höchster Durchsatz zuerst
    QUALITY = "quality"       # Höchste Qualität zuerst


@dataclass
class PresetConfig:
    """Konfiguration für ein OpenRouter Preset."""
    
    slug: str
    """Preset-Slug (z.B. 'bfa-analyzer')"""
    
    description: str
    """Beschreibung für UI"""
    
    model: str
    """Primäres Modell"""
    
    fallback_models: list[str] = field(default_factory=list)
    """Fallback-Modelle in Reihenfolge"""
    
    system_prompt: str = ""
    """System Prompt (in OpenRouter UI setzen)"""
    
    temperature: float = 0.3
    """Temperatur (0.0-2.0)"""
    
    top_p: float = 0.9
    """Top-P Sampling"""
    
    max_tokens: int | None = None
    """Max Output Tokens"""
    
    provider_sort: ProviderSort = ProviderSort.QUALITY
    """Provider-Sortierung"""
    
    provider_allow: list[str] = field(default_factory=list)
    """Erlaubte Provider (leer = alle)"""
    
    @property
    def model_id(self) -> str:
        """Model-String für API-Calls."""
        return f"@preset/{self.slug}"
    
    def to_openrouter_json(self) -> dict[str, Any]:
        """Exportiert als OpenRouter-kompatibles Dict."""
        config = {
            "slug": self.slug,
            "description": self.description,
            "model": self.model,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        
        if self.fallback_models:
            config["models"] = [self.model] + self.fallback_models
            config["route"] = "fallback"
        
        if self.system_prompt:
            config["system_prompt"] = self.system_prompt
        
        if self.max_tokens:
            config["max_tokens"] = self.max_tokens
        
        provider_config = {"sort": self.provider_sort.value}
        if self.provider_allow:
            provider_config["allow"] = self.provider_allow
        config["provider"] = provider_config
        
        return config


# ============================================================
# BFA Presets Definition
# ============================================================

BFA_PRESETS = {
    # --------------------------------------------------------
    # Haupt-Analyse (höchste Qualität)
    # --------------------------------------------------------
    "bfa-analyzer": PresetConfig(
        slug="bfa-analyzer",
        description="Ex-Zonen Analyse mit höchster Präzision",
        model="anthropic/claude-sonnet-4-20250514",
        fallback_models=[
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001",
        ],
        system_prompt="""Du bist ein Experte für Explosionsschutz nach TRGS 720ff, ATEX und IECEx.

Deine Aufgaben:
- Ex-Zonen klassifizieren mit Normbezug
- Freisetzungsquellen identifizieren
- Lüftungseffektivität bewerten
- Zonenausdehnungen berechnen

Antworte auf Deutsch. Begründe jede Klassifizierung präzise.""",
        temperature=0.2,
        top_p=0.9,
        provider_sort=ProviderSort.QUALITY,
        provider_allow=["anthropic", "openai", "google"],
    ),
    
    # --------------------------------------------------------
    # Equipment-Prüfung (strukturierte Ausgabe)
    # --------------------------------------------------------
    "bfa-equipment": PresetConfig(
        slug="bfa-equipment",
        description="Equipment-Eignungsprüfung für Ex-Zonen",
        model="anthropic/claude-sonnet-4-20250514",
        fallback_models=["openai/gpt-4o"],
        system_prompt="""Du prüfst Betriebsmittel auf Ex-Schutz Eignung nach ATEX.

Prüfkriterien:
1. Gerätekategorie (1G/2G/3G) passend zur Zone
2. Explosionsgruppe (IIA/IIB/IIC) kompatibel
3. Temperaturklasse (T1-T6) ausreichend
4. Zündschutzart (d/e/i/n) geeignet

Bei Mängeln: Konkrete Handlungsempfehlung geben!
Format: Strukturiert mit klarem Urteil (geeignet/nicht geeignet).""",
        temperature=0.1,
        top_p=0.85,
        provider_sort=ProviderSort.QUALITY,
    ),
    
    # --------------------------------------------------------
    # CAD-Verarbeitung (schnell)
    # --------------------------------------------------------
    "bfa-cad": PresetConfig(
        slug="bfa-cad",
        description="CAD-Datei Analyse und Daten-Extraktion",
        model="google/gemini-2.0-flash-001",
        fallback_models=[
            "openai/gpt-4o-mini",
            "anthropic/claude-haiku-4-20250514",
        ],
        system_prompt="""Du analysierst CAD-Daten für Explosionsschutz.

Extrahiere:
- Räume mit Abmessungen (Volumen, Fläche, Höhe)
- Equipment und Positionen
- Lüftungseinrichtungen
- Ex-Zonen aus Layer-Namen

Strukturiere die Ausgabe klar und tabellarisch.""",
        temperature=0.1,
        max_tokens=4000,
        provider_sort=ProviderSort.LATENCY,
    ),
    
    # --------------------------------------------------------
    # Report-Generierung (gute Sprache)
    # --------------------------------------------------------
    "bfa-report": PresetConfig(
        slug="bfa-report",
        description="Professionelle Berichterstellung",
        model="openai/gpt-4o",
        fallback_models=["anthropic/claude-sonnet-4-20250514"],
        system_prompt="""Du erstellst professionelle Explosionsschutz-Berichte.

Struktur:
1. Executive Summary
2. Analysierte Bereiche
3. Zoneneinteilung mit Begründung
4. Equipment-Bewertung
5. Maßnahmenkatalog (priorisiert)
6. Anhänge (Normverweise)

Stil: Technisch präzise, sachlich, auf Deutsch.""",
        temperature=0.4,
        top_p=0.95,
        max_tokens=8000,
        provider_sort=ProviderSort.QUALITY,
    ),
    
    # --------------------------------------------------------
    # Triage/Routing (schnellstes Modell)
    # --------------------------------------------------------
    "bfa-triage": PresetConfig(
        slug="bfa-triage",
        description="Schnelles Routing von Anfragen",
        model="google/gemini-2.0-flash-001",
        fallback_models=[
            "openai/gpt-4o-mini",
            "anthropic/claude-haiku-4-20250514",
        ],
        system_prompt="""Du routest Explosionsschutz-Anfragen zu Spezialisten.

Routing:
- CAD/Datei/DXF/IFC → CAD Reader
- Zone/Klassifizierung/ATEX → Zone Analyzer
- Equipment/Kennzeichnung/geeignet → Equipment Checker
- Bericht/Report → Report Writer

Bei Unklarheit: Kurz nachfragen.
Antworten: Kurz und prägnant.""",
        temperature=0.2,
        max_tokens=500,
        provider_sort=ProviderSort.LATENCY,
    ),
    
    # --------------------------------------------------------
    # Stoffdaten (Recherche)
    # --------------------------------------------------------
    "bfa-substances": PresetConfig(
        slug="bfa-substances",
        description="Stoffdaten und Gefahrstoff-Expertise",
        model="anthropic/claude-sonnet-4-20250514",
        fallback_models=["openai/gpt-4o"],
        system_prompt="""Du bist Experte für Gefahrstoffe im Explosionsschutz.

Relevante Daten:
- Flammpunkt, Zündtemperatur
- UEG/OEG (LEL/UEL)
- Explosionsgruppe (IIA/IIB/IIC)
- Temperaturklasse (T1-T6)
- Dampfdichte (schwerer/leichter als Luft)

Quellen: GESTIS, Sicherheitsdatenblätter, TRGS 510.""",
        temperature=0.2,
        provider_sort=ProviderSort.QUALITY,
    ),
    
    # --------------------------------------------------------
    # Budget-Variante (kostenoptimiert)
    # --------------------------------------------------------
    "bfa-budget": PresetConfig(
        slug="bfa-budget",
        description="Kostengünstige Analyse für einfache Fälle",
        model="google/gemini-2.0-flash-001",
        fallback_models=[
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.3-70b-instruct",
        ],
        system_prompt="""Du analysierst Explosionsschutz-Fragen.
Antworte präzise und auf Deutsch.
Beziehe dich auf TRGS 720ff wenn relevant.""",
        temperature=0.3,
        provider_sort=ProviderSort.PRICE,
    ),
    
    # --------------------------------------------------------
    # Research (akademische Literatur)
    # --------------------------------------------------------
    "bfa-research": PresetConfig(
        slug="bfa-research",
        description="Wissenschaftliche Literaturrecherche",
        model="anthropic/claude-sonnet-4-20250514",
        fallback_models=[
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001",
        ],
        system_prompt="""Du bist ein Experte für wissenschaftliche Literaturrecherche im Bereich Explosionsschutz.

Deine Aufgaben:
- Stand der Technik recherchieren
- Stoffdaten validieren  
- Normen-Hintergrund liefern

Nutze Paper-Search Tools für:
- arXiv (Physik, Engineering)
- PubMed (Toxikologie, Arbeitsschutz)
- Semantic Scholar (Breite Suche)

Ausgabe: Titel, Autoren, Kernaussage, Relevanz für die Anfrage.""",
        temperature=0.3,
        provider_sort=ProviderSort.QUALITY,
    ),
}


# ============================================================
# Preset Manager
# ============================================================

class PresetManager:
    """Verwaltet OpenRouter Presets."""
    
    def __init__(self, presets: dict[str, PresetConfig] | None = None):
        self.presets = presets or BFA_PRESETS
    
    def get(self, slug: str) -> PresetConfig:
        """Holt Preset nach Slug."""
        # Normalisiere: entferne 'bfa-' prefix falls vorhanden
        normalized = slug.replace("bfa-", "") if slug.startswith("bfa-") else slug
        full_slug = f"bfa-{normalized}"
        
        if full_slug in self.presets:
            return self.presets[full_slug]
        if slug in self.presets:
            return self.presets[slug]
            
        available = ", ".join(self.presets.keys())
        raise KeyError(f"Preset '{slug}' nicht gefunden. Verfügbar: {available}")
    
    def model_id(self, slug: str) -> str:
        """Gibt Model-ID für Preset zurück."""
        return self.get(slug).model_id
    
    def list_all(self) -> list[tuple[str, str]]:
        """Listet alle Presets mit Beschreibung."""
        return [(p.slug, p.description) for p in self.presets.values()]
    
    def export_all(self, filepath: Path | str | None = None) -> str:
        """Exportiert alle Presets als JSON."""
        data = {
            "presets": [p.to_openrouter_json() for p in self.presets.values()],
            "setup_instructions": """
So legst du die Presets in OpenRouter an:

1. Öffne https://openrouter.ai/settings/presets
2. Klicke "Create New Preset"
3. Fülle die Felder aus diesem JSON:
   - Slug: Der eindeutige Name
   - Model: Das primäre Modell
   - Models + Route: Für Fallbacks (route: "fallback")
   - System Prompt: Der vordefinierte Prompt
   - Temperature, Top P, Max Tokens: Wie angegeben
4. Unter "Provider": Sortierung und erlaubte Provider einstellen
5. Speichern

Dann im Code nutzen: model="@preset/bfa-analyzer"
"""
        }
        
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        
        if filepath:
            Path(filepath).write_text(json_str, encoding="utf-8")
            
        return json_str
    
    def generate_markdown_guide(self) -> str:
        """Generiert Markdown-Anleitung."""
        guide = """# OpenRouter Presets für BFA Agent

## Übersicht

| Preset | Model | Verwendung | Provider-Sort |
|--------|-------|------------|---------------|
"""
        for p in self.presets.values():
            guide += f"| `{p.slug}` | {p.model.split('/')[-1]} | {p.description[:30]}... | {p.provider_sort.value} |\n"
        
        guide += "\n## Preset-Details\n\n"
        
        for p in self.presets.values():
            guide += f"""### {p.slug}

**Beschreibung:** {p.description}

**Model:** `{p.model}`

**Fallbacks:** {', '.join(p.fallback_models) if p.fallback_models else 'keine'}

**Parameter:**
- Temperature: {p.temperature}
- Top P: {p.top_p}
- Max Tokens: {p.max_tokens or 'default'}

**Provider:** Sort by {p.provider_sort.value}

**Verwendung:**
```python
from agents import Agent

agent = Agent(
    name="My Agent",
    model="{p.model_id}"
)
```

---

"""
        return guide


# Globaler Manager
manager = PresetManager()


# ============================================================
# Convenience Functions
# ============================================================

def get_preset(slug: str) -> PresetConfig:
    """Holt ein Preset."""
    return manager.get(slug)


def get_preset_model(slug: str) -> str:
    """Gibt Model-ID für Preset zurück."""
    return manager.model_id(slug)


def list_presets() -> dict[str, str]:
    """Listet alle Presets."""
    return {slug: p.description for slug, p in BFA_PRESETS.items()}


def export_presets_for_openrouter(filepath: str | None = None) -> str:
    """Exportiert Presets für OpenRouter UI."""
    return manager.export_all(filepath)


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("BFA Presets CLI")
        print()
        print("Commands:")
        print("  list     - Liste alle Presets")
        print("  export   - Exportiere JSON für OpenRouter")
        print("  guide    - Markdown Setup-Anleitung")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        print("BFA Presets:\n")
        for slug, desc in manager.list_all():
            preset = manager.get(slug)
            print(f"  {preset.model_id}")
            print(f"    → {desc}")
            print(f"    → Model: {preset.model}")
            print()
            
    elif cmd == "export":
        output = sys.argv[2] if len(sys.argv) > 2 else None
        json_str = manager.export_all(output)
        if output:
            print(f"Exportiert nach: {output}")
        else:
            print(json_str)
            
    elif cmd == "guide":
        print(manager.generate_markdown_guide())
        
    else:
        print(f"Unbekannter Befehl: {cmd}")
