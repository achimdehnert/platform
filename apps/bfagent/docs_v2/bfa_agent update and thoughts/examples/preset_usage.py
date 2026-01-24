"""Beispiele: OpenRouter Presets mit BFA Agent.

Zeigt verschiedene Preset-Strategien:
1. Presets auflisten
2. JSON für OpenRouter UI exportieren
3. Agents mit Presets nutzen
4. Dynamischer Preset-Wechsel
5. Fallback-Konfiguration
"""

import asyncio
import json
from agents import Runner

from bfa_agent.config import setup_openrouter, Models, ModelWithFallback
from bfa_agent.presets import (
    BFA_PRESETS,
    PresetManager,
    get_preset,
    get_preset_model,
    export_presets_for_openrouter,
    list_presets,
)
from bfa_agent.agents_presets import (
    triage_preset,
    zone_analyzer_preset,
    create_agent_with_preset,
)


def example_1_list_presets():
    """Beispiel 1: Verfügbare Presets anzeigen."""
    print("\n" + "="*60)
    print("Beispiel 1: Verfügbare BFA Presets")
    print("="*60)
    
    presets = list_presets()
    
    print("\nVordefinierte Presets:\n")
    for slug, description in presets.items():
        preset = get_preset(slug)
        print(f"  {preset.model_id}")
        print(f"    → {description}")
        print(f"    → Model: {preset.model}")
        if preset.fallback_models:
            print(f"    → Fallbacks: {', '.join(preset.fallback_models[:2])}...")
        print()


def example_2_export_presets():
    """Beispiel 2: Presets für OpenRouter UI exportieren."""
    print("\n" + "="*60)
    print("Beispiel 2: Export für OpenRouter UI")
    print("="*60)
    
    # JSON exportieren
    json_export = export_presets_for_openrouter()
    
    # Speichern
    output_file = "openrouter_presets.json"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json_export)
    
    print(f"\nPresets exportiert nach: {output_file}")
    print("\nSo legst du die Presets an:")
    print("1. Öffne https://openrouter.ai/settings/presets")
    print("2. Klicke 'Create New Preset'")
    print("3. Kopiere die Werte aus dem JSON")
    print("4. Speichern")
    
    # Preview
    data = json.loads(json_export)
    print(f"\n{len(data['presets'])} Presets zum Anlegen:")
    for p in data["presets"]:
        print(f"  - {p['slug']}: {p['model']}")


async def example_3_use_presets():
    """Beispiel 3: Agents mit Presets ausführen."""
    print("\n" + "="*60)
    print("Beispiel 3: Agents mit Presets")
    print("="*60)
    
    # OpenRouter initialisieren
    setup_openrouter()
    
    # Agent mit Preset nutzen
    print(f"\nZone Analyzer nutzt: {zone_analyzer_preset.model}")
    
    result = await Runner.run(
        zone_analyzer_preset,
        "Klassifiziere einen Lackierraum mit 450m³, 25 Luftwechseln/h und Aceton. Kurze Antwort."
    )
    
    print(f"\nErgebnis:\n{result.final_output}")


async def example_4_dynamic_presets():
    """Beispiel 4: Dynamischer Preset-Wechsel."""
    print("\n" + "="*60)
    print("Beispiel 4: Dynamische Preset-Auswahl")
    print("="*60)
    
    setup_openrouter()
    
    # Verschiedene Konfigurationen
    configs = [
        ("analyzer", None, None, "Standard Preset"),
        ("analyzer", "bfa-budget", None, "Budget Preset"),
        ("analyzer", None, "openai/gpt-4o-mini", "Direktes Model"),
    ]
    
    for agent_type, preset, direct_model, description in configs:
        print(f"\n{description}:")
        
        agent = create_agent_with_preset(
            agent_type,
            custom_preset=preset,
            direct_model=direct_model
        )
        print(f"  Model: {agent.model}")


def example_5_fallback_config():
    """Beispiel 5: Manuelle Fallback-Konfiguration."""
    print("\n" + "="*60)
    print("Beispiel 5: Fallback ohne Presets")
    print("="*60)
    
    # Fallback-Konfiguration
    fallback = ModelWithFallback(
        primary="anthropic/claude-sonnet-4-20250514",
        fallbacks=[
            "openai/gpt-4o",
            "google/gemini-2.0-flash-001"
        ],
        provider_sort="quality"
    )
    
    print(f"\nPrimary: {fallback.primary}")
    print(f"Fallbacks: {fallback.fallbacks}")
    print(f"\nextra_body für API-Call:")
    print(json.dumps(fallback.to_extra_body(), indent=2))


def example_6_preset_manager():
    """Beispiel 6: Preset Manager für Custom Presets."""
    print("\n" + "="*60)
    print("Beispiel 6: Preset Manager")
    print("="*60)
    
    manager = PresetManager()
    
    # Alle Presets auflisten
    print("\nAlle Presets:")
    for slug, desc in manager.list_all():
        print(f"  {slug}: {desc[:40]}...")
    
    # Markdown-Guide generieren
    guide = manager.generate_markdown_guide()
    
    # Speichern
    with open("PRESETS_GUIDE.md", "w", encoding="utf-8") as f:
        f.write(guide)
    
    print(f"\nMarkdown-Guide gespeichert: PRESETS_GUIDE.md")


async def main():
    """Führt alle Beispiele aus."""
    
    # Sync Beispiele
    example_1_list_presets()
    example_2_export_presets()
    example_5_fallback_config()
    example_6_preset_manager()
    
    # Async Beispiele (benötigen API Key)
    try:
        await example_3_use_presets()
        await example_4_dynamic_presets()
    except ValueError as e:
        print(f"\n⚠️  API-Beispiele übersprungen: {e}")


if __name__ == "__main__":
    asyncio.run(main())
