# Travel Story System

Personalisierte, reise-synchronisierte Story-Generierung mit PostgreSQL und Claude API.

## Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TRAVEL STORY SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────────┐    │
│  │   INTAKE     │     │  CALCULATOR  │     │   STORY MAPPER       │    │
│  │   (HTML)     │────▶│  (Python)    │────▶│   (Python)           │    │
│  │              │     │              │     │                       │    │
│  │ Reisedaten   │     │ Lesezeit-    │     │ Beat-zu-Kapitel      │    │
│  │ erfassen     │     │ Berechnung   │     │ Mapping              │    │
│  └──────────────┘     └──────────────┘     └──────────────────────┘    │
│                                                       │                  │
│                                                       ▼                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    LOCATION DATABASE (PostgreSQL)                │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │   │
│  │  │ BASE_LOCATIONS  │  │ LOCATION_LAYERS │  │  USER_WORLDS    │  │   │
│  │  │ (shared)        │  │ (shared/genre)  │  │  (user-specific)│  │   │
│  │  │                 │  │                 │  │                 │  │   │
│  │  │ • Barcelona     │  │ • romance       │  │ • Charaktere    │  │   │
│  │  │ • Rom           │  │ • thriller      │  │ • Erinnerungen  │  │   │
│  │  │ • Paris         │  │ • mystery       │  │ • Ausschlüsse   │  │   │
│  │  │ • ...           │  │ • foodie        │  │ • Präferenzen   │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │   │
│  │                                                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                        │   │
│  │  │ RESEARCH_CACHE  │  │ GENERATED_      │                        │   │
│  │  │ (TTL 30 days)   │  │ STORIES         │                        │   │
│  │  └─────────────────┘  └─────────────────┘                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│                               ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  INTEGRATED STORY GENERATOR                       │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │   │
│  │  │ LocationGen     │  │ StoryContext    │  │ ChapterSpec     │  │   │
│  │  │                 │  │                 │  │                 │  │   │
│  │  │ On-Demand       │  │ • Protagonist   │  │ • Beat          │  │   │
│  │  │ Location        │  │ • Love Interest │  │ • Pacing        │  │   │
│  │  │ Generation      │  │ • Antagonist    │  │ • Location      │  │   │
│  │  │ via Claude API  │  │ • Conflict      │  │ • Target Words  │  │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘  │   │
│  │                               │                                   │   │
│  │                               ▼                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐│   │
│  │  │                    CLAUDE API                                ││   │
│  │  │                                                              ││   │
│  │  │  • claude-sonnet-4-20250514 (Story)                     ││   │
│  │  │  • Location-Context + Story-Context + Chapter-Spec → Text   ││   │
│  │  └─────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                          │
│                               ▼                                          │
│                      ┌─────────────────┐                                │
│                      │    OUTPUT       │                                │
│                      │                 │                                │
│                      │  • Markdown     │                                │
│                      │  • JSON         │                                │
│                      │  • (EPUB)       │                                │
│                      └─────────────────┘                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Dateien

### Core Location System
| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `location_models.py` | 555 | Datenmodelle für 3-Schichten-Architektur |
| `location_repository.py` | 549 | PostgreSQL Repository mit Connection Pool |
| `location_generator.py` | 622 | On-Demand Generation mit LLM |
| `location_demo.py` | 342 | Demo & Seed-Daten |

### Story Generation
| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `integrated_generator.py` | 519 | Kombiniert Location + Story Generation |
| `integration_demo.py` | 318 | Vollständige Pipeline Demo |

### Travel Calculator (Original)
| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `models.py` | 387 | Reise-Datenmodelle |
| `calculator.py` | 462 | Lesezeit-Berechnung |
| `story_models.py` | 250 | Story-Struktur (Acts, Beats) |
| `story_mapper.py` | 381 | Beat-zu-Kapitel Mapping |
| `agent_prompts.py` | 397 | Prompt-Templates |
| `story_generator.py` | 427 | Story-Text-Generierung |

**Gesamt: ~6.000 Zeilen Python**

## Setup

### 1. PostgreSQL

```bash
# Database erstellen
createdb travel_story

# Oder via psql
psql -U postgres -c "CREATE DATABASE travel_story;"
```

### 2. Environment

```bash
# PostgreSQL
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=travel_story
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=xxx

# Oder CONNECTION STRING:
export DATABASE_URL=postgresql://user:pass@host:5432/db

# Anthropic API (für echte Generierung)
export ANTHROPIC_API_KEY=sk-ant-xxx
```

### 3. Dependencies

```bash
pip install psycopg2-binary anthropic
```

### 4. Schema & Seed

```bash
# Schema initialisieren
python location_demo.py --init

# Seed-Daten laden (Barcelona, Rom, Demo-User)
python location_demo.py --seed

# Prüfen
python location_demo.py --stats
```

## Usage

### Location Demo

```bash
# Vollständige Demo
python location_demo.py

# Nur Stats
python location_demo.py --stats
```

### Story Generation

```bash
# Mock-Generierung (ohne API)
python integration_demo.py

# Echte Generierung (mit Claude API)
python integration_demo.py --real

# Nur ein Kapitel
python integration_demo.py --real --chapter 1
```

### Programmatisch

```python
from location_repository import LocationRepository, DatabaseConfig
from location_generator import LocationGenerator
from integrated_generator import IntegratedStoryGenerator, StoryContext, ChapterSpec

# Setup
config = DatabaseConfig()
repo = LocationRepository(config)
repo.connect()

# Story Generator
generator = IntegratedStoryGenerator(repo, use_real_llm=True)

# Context
context = StoryContext(
    title="Schatten über Barcelona",
    genre="romantic_suspense",
    protagonist_name="Elena",
    love_interest_name="Marco",
    primary_location="Barcelona",
    central_conflict="Kunstfälschungsring",
)

# Chapter
spec = ChapterSpec(
    chapter_number=1,
    beat_name="HOOK",
    story_location="Barcelona",
    target_words=2500,
)

# Generate
chapter = generator.generate_chapter(spec, context)
print(chapter.content)

# Cleanup
repo.close()
```

## 3-Schichten-Architektur

### Schicht 1: BASE_LOCATION (shared)
- Einmal generiert, für alle User nutzbar
- Fakten: Koordinaten, Sprache, Viertel, Klima
- Wächst organisch mit neuen Reisezielen

### Schicht 2: LOCATION_LAYER (shared, genre-spezifisch)
- Barcelona + Romance = romantische Plätze
- Barcelona + Thriller = gefährliche Orte
- Atmosphären, sensorische Details, Story-Hooks

### Schicht 3: USER_WORLD (user-spezifisch)
- Persönliche Orte ("Mein Lieblingscafé")
- Ausschlüsse ("Nicht Sagrada Familia - war mit Ex dort")
- Story-Kontinuität (Elena & Marco's Geschichte)
- Charakter-Entwicklung über mehrere Bücher

## On-Demand Generation Flow

```
User fragt: "Story in Lissabon"
     │
     ▼
┌─────────────────────────────┐
│ 1. Check base_locations     │
│    → Lissabon nicht da      │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ 2. Check research_cache     │
│    → Nicht gecached         │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ 3. Generate via Claude API  │
│    → Base Location          │
│    → Save to DB + Cache     │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ 4. Check location_layers    │
│    → Romance Layer fehlt    │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ 5. Generate Romance Layer   │
│    → Save to DB + Cache     │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ 6. Merge mit User World     │
│    → Ausschlüsse anwenden   │
│    → Persönliche Orte add   │
└─────────────────────────────┘
     │
     ▼
   Story-Generator erhält
   personalisierten Location-Context
```

## Kosten-Schätzung

| Operation | Tokens (ca.) | Kosten (Sonnet) |
|-----------|--------------|-----------------|
| Base Location | ~1.500 | ~$0.005 |
| Layer Generation | ~2.000 | ~$0.007 |
| Kapitel (2.500 Wörter) | ~4.000 | ~$0.015 |
| **10-Kapitel Story** | ~45.000 | **~$0.15** |

## Nächste Schritte

- [ ] FastAPI Server für Web-Integration
- [ ] EPUB Export
- [ ] Streaming-Generierung
- [ ] User-Management (Auth)
- [ ] Web-Research für aktuelle Details
- [ ] Cover-Generierung (FLUX)
