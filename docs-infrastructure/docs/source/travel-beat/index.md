# Travel Beat

```{toctree}
:maxdepth: 2

overview
```

## Übersicht

Travel Beat ist eine AI-powered Plattform für Travel Content Generation.

### Features

- **Destination Profiles** - AI-generierte Reiseziel-Beschreibungen
- **Itinerary Generation** - Automatische Reiseplanung
- **Content Localization** - Mehrsprachige Inhalte
- **Integration** - Nutzt Creative Services für LLM-Aufrufe

### Quick Start

```python
from creative_services import DynamicLLMClient, LLMTier

client = DynamicLLMClient.from_env()

response = await client.generate(
    prompt="Describe Tokyo as a travel destination",
    tier=LLMTier.STANDARD,
)
```
