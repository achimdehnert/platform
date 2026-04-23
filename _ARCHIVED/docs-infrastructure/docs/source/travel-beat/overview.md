# Übersicht

Travel Beat ist eine AI-powered Plattform für Travel Content Generation.

## Features

- **Destination Profiles** - AI-generierte Reiseziel-Beschreibungen
- **Itinerary Generation** - Automatische Reiseplanung
- **Content Localization** - Mehrsprachige Inhalte
- **Image Integration** - Automatische Bildauswahl

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                      Travel Beat                                 │
├─────────────────────────────────────────────────────────────────┤
│  Destinations    │  Itineraries   │  Content       │  Media     │
│  - Profiles      │  - Day Plans   │  - Articles    │  - Images  │
│  - POIs          │  - Activities  │  - Guides      │  - Videos  │
│  - Reviews       │  - Transport   │  - Tips        │  - Maps    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Creative Services                               │
│  DynamicLLMClient → Tier-based LLM Selection → Content Gen      │
└─────────────────────────────────────────────────────────────────┘
```

## Integration mit Creative Services

```python
from creative_services import DynamicLLMClient, LLMTier

client = DynamicLLMClient.from_env()

# Destination beschreiben
response = await client.generate(
    prompt="Describe Tokyo as a travel destination",
    system_prompt="You are a travel writer.",
    tier=LLMTier.STANDARD,
)

# Itinerary generieren
itinerary = await client.generate(
    prompt="Create a 3-day itinerary for Paris",
    tier=LLMTier.PREMIUM,  # Höhere Qualität für komplexe Aufgaben
)
```

## LLM Tiers für Travel Content

| Content Type | Empfohlener Tier | Grund |
|--------------|------------------|-------|
| Quick Facts | ECONOMY | Einfache, faktische Infos |
| Descriptions | STANDARD | Ausgewogene Qualität |
| Full Articles | PREMIUM | Kreative, detaillierte Texte |
| Translations | STANDARD | Gute Sprachqualität |
