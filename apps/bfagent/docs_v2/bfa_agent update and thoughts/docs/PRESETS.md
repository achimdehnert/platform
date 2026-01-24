# OpenRouter Presets für BFA Agent

## Übersicht

Presets ermöglichen Model-Konfiguration **ohne Code-Änderung**:

| Preset | Verwendung | Model | Kosten* |
|--------|------------|-------|---------|
| `bfa-analyzer` | Ex-Zonen Analyse | Claude Sonnet | ~$3/1M |
| `bfa-quick` | Schnelle Checks | Gemini Flash | ~$0.10/1M |
| `bfa-equipment` | Equipment-Prüfung | Claude Sonnet | ~$3/1M |
| `bfa-report` | Berichterstellung | GPT-4o | ~$2.50/1M |
| `bfa-triage` | Routing | Gemini Flash | ~$0.10/1M |
| `bfa-cad` | CAD-Verarbeitung | Gemini Flash | ~$0.10/1M |
| `bfa-substances` | Stoffdaten | Claude Sonnet | ~$3/1M |

*Ungefähre Preise, Stand Jan 2025

## Setup in OpenRouter UI

### Schritt 1: Presets exportieren

```bash
cd bfa_agent
python -c "from bfa_agent.presets import export_presets_for_openrouter; print(export_presets_for_openrouter())" > presets.json
```

### Schritt 2: In OpenRouter anlegen

1. Öffne https://openrouter.ai/settings/presets
2. Klicke **"New Preset"**
3. Fülle die Felder aus:

#### Preset: bfa-analyzer

```
Slug:           bfa-analyzer
Description:    Ex-Zonen Analyse mit höchster Präzision
Model:          anthropic/claude-sonnet-4-20250514
Temperature:    0.3

System Prompt:
Du bist ein Experte für Explosionsschutz nach TRGS 720ff, ATEX und IECEx.
Analysiere präzise und begründe jede Klassifizierung mit Normbezug.
Antworte auf Deutsch.

Advanced → Models (Fallbacks):
- openai/gpt-4o
- google/gemini-2.0-flash-001

Advanced → Provider:
{
  "sort": "quality",
  "allow": ["anthropic", "openai", "google"]
}
```

#### Preset: bfa-quick

```
Slug:           bfa-quick
Description:    Schnelle Vorab-Klassifizierung
Model:          google/gemini-2.0-flash-001
Temperature:    0.2

Advanced → Models (Fallbacks):
- meta-llama/llama-3.3-70b-instruct
- mistralai/mistral-large-latest

Advanced → Provider:
{
  "sort": "price"
}
```

#### Preset: bfa-equipment

```
Slug:           bfa-equipment
Description:    Equipment-Eignungsprüfung
Model:          anthropic/claude-sonnet-4-20250514
Temperature:    0.1

System Prompt:
Prüfe Betriebsmittel auf Ex-Schutz Eignung.
Antworte IMMER im strukturierten JSON-Format.
Begründe jede Entscheidung mit ATEX-Anforderungen.

Advanced → Models (Fallbacks):
- openai/gpt-4o
```

#### Preset: bfa-report

```
Slug:           bfa-report
Description:    Professionelle Berichterstellung
Model:          openai/gpt-4o
Temperature:    0.5
Max Tokens:     4000

System Prompt:
Erstelle professionelle technische Berichte.
Struktur: Zusammenfassung, Analyse, Maßnahmen, Normbezüge.
Sprache: Deutsch, sachlich, präzise.

Advanced → Models (Fallbacks):
- anthropic/claude-sonnet-4-20250514
```

#### Preset: bfa-triage

```
Slug:           bfa-triage
Description:    Schnelles Routing
Model:          google/gemini-2.0-flash-001
Temperature:    0.1
Max Tokens:     500

Advanced → Provider:
{
  "sort": "latency"
}

Advanced → Models (Fallbacks):
- openai/gpt-4o-mini
```

#### Preset: bfa-cad

```
Slug:           bfa-cad
Description:    CAD-Datei Analyse
Model:          google/gemini-2.0-flash-001
Temperature:    0.2

System Prompt:
Analysiere CAD-Daten für Explosionsschutz.
Extrahiere: Räume, Equipment, Lüftung, Ex-Zonen-Layer.
Strukturiere die Ausgabe klar und übersichtlich.

Advanced → Models (Fallbacks):
- anthropic/claude-sonnet-4-20250514
```

### Schritt 3: Testen

```python
from bfa_agent import setup_openrouter
from bfa_agent.agents_presets import zone_analyzer_preset
from agents import Runner
import asyncio

setup_openrouter()

async def test():
    result = await Runner.run(
        zone_analyzer_preset,
        "Klassifiziere einen Lackierraum"
    )
    print(result.final_output)

asyncio.run(test())
```

## Nutzung im Code

### Mit Preset-Agents (empfohlen)

```python
from bfa_agent.agents_presets import (
    triage_preset,
    zone_analyzer_preset,
    equipment_checker_preset,
)

# Nutzt automatisch @preset/bfa-analyzer
result = await Runner.run(zone_analyzer_preset, "...")
```

### Mit Factory

```python
from bfa_agent.agents_presets import create_agent_with_preset

# Standard-Preset
agent = create_agent_with_preset("analyzer")

# Custom Preset
agent = create_agent_with_preset("analyzer", preset_slug="my-custom-preset")

# Direktes Model (ohne Preset)
agent = create_agent_with_preset("analyzer", override_model="openai/gpt-4o")
```

### Presets global umschalten

```python
from bfa_agent.config import Models

# Presets aktivieren (default)
Models.use_presets(enabled=True)

# Direkte Models nutzen
Models.use_presets(enabled=False)
```

## Preset-Strategien

### Kostenoptimierung

```
User Request
     │
     ▼
┌─────────────┐
│ bfa-triage  │  $0.10/1M (Gemini Flash)
│ Routing     │
└──────┬──────┘
       │
   ┌───┴───────────────────┐
   │                       │
   ▼                       ▼
┌─────────────┐     ┌─────────────┐
│ bfa-quick   │     │ bfa-analyzer│
│ Einfach     │     │ Komplex     │
│ $0.10/1M    │     │ $3.00/1M    │
└─────────────┘     └─────────────┘
```

### A/B Testing

1. Erstelle zwei Varianten: `bfa-analyzer-v1`, `bfa-analyzer-v2`
2. Unterschiedliche Models/Prompts
3. Traffic aufteilen
4. Qualität messen

### Fallback-Kette

```
Claude Sonnet (Primary)
     │
     │ (wenn nicht verfügbar)
     ▼
GPT-4o (Fallback 1)
     │
     │ (wenn nicht verfügbar)
     ▼
Gemini Flash (Fallback 2)
```

## Troubleshooting

### Preset nicht gefunden

```
Error: Model @preset/bfa-analyzer not found
```

**Lösung:** Preset in OpenRouter UI anlegen (siehe oben)

### Falsches Model wird verwendet

Prüfe in OpenRouter Activity: https://openrouter.ai/activity

### Fallback greift nicht

Provider muss in `allow`-Liste sein:
```json
{"allow": ["anthropic", "openai", "google"]}
```

## Weitere Ressourcen

- [OpenRouter Presets Docs](https://openrouter.ai/docs/guides/features/presets)
- [Model Fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [Provider Selection](https://openrouter.ai/docs/guides/routing/provider-selection)
