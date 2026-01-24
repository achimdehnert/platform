# Travel Story - Technische Dokumentation

## Teil 1: Architektur

---

## Inhaltsverzeichnis

1. [System-Übersicht](#1-system-übersicht)
2. [Tech Stack](#2-tech-stack)
3. [Architektur-Diagramm](#3-architektur-diagramm)
4. [Komponenten](#4-komponenten)
5. [Datenfluss](#5-datenfluss)

---

## 1. System-Übersicht

Travel Story ist eine Django-basierte Web-Applikation zur Generierung personalisierter Reise-Geschichten. Das System kombiniert:

- **3-Schichten Location-Database** für wiederverwendbare Ortsdaten
- **On-Demand LLM-Generierung** für Locations und Story-Text
- **User Worlds** für Personalisierung und Story-Kontinuität
- **HTMX** für reaktive UI ohne JavaScript-Framework

### Kernprinzipien

| Prinzip | Umsetzung |
|---------|-----------|
| **DRY** | Shared Locations, wiederverwendbare Layer |
| **Lazy Generation** | Daten nur bei Bedarf generieren |
| **Caching** | PostgreSQL + Redis für Performance |
| **Separation of Concerns** | Django Apps für jeden Bereich |

---

## 2. Tech Stack

### Backend

| Komponente | Technologie | Version |
|------------|-------------|---------|
| **Framework** | Django | 5.0+ |
| **Datenbank** | PostgreSQL | 15+ |
| **Cache** | Redis | 7+ |
| **Task Queue** | Celery | 5.3+ |
| **LLM API** | Anthropic Claude | claude-sonnet-4-20250514 |

### Frontend

| Komponente | Technologie | Version |
|------------|-------------|---------|
| **Interaktivität** | HTMX | 1.9+ |
| **CSS** | Tailwind CSS | 3.4+ |
| **Icons** | Heroicons | 2.0 |
| **Alpine.js** | Alpine.js | 3.x (minimal) |

### Infrastructure

| Komponente | Technologie |
|------------|-------------|
| **Container** | Docker + Docker Compose |
| **Reverse Proxy** | Nginx |
| **SSL** | Let's Encrypt |
| **Monitoring** | Sentry |

---

## 3. Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRAVEL STORY SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                           FRONTEND (HTMX)                            │   │
│   ├─────────────────────────────────────────────────────────────────────┤   │
│   │                                                                      │   │
│   │   Browser ──────► Django Templates ──────► HTMX Partials            │   │
│   │      │                   │                      │                    │   │
│   │      │              Tailwind CSS           hx-get, hx-post          │   │
│   │      │                   │                 hx-trigger               │   │
│   │      ▼                   ▼                      │                    │   │
│   │   [Form Submit] ───► [Partial Response] ◄──────┘                    │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                        DJANGO BACKEND                                │   │
│   ├─────────────────────────────────────────────────────────────────────┤   │
│   │                                                                      │   │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │   │
│   │   │    trips     │  │   stories    │  │   worlds     │             │   │
│   │   │    (App)     │  │    (App)     │  │    (App)     │             │   │
│   │   │              │  │              │  │              │             │   │
│   │   │ • TripCreate │  │ • Generate   │  │ • UserWorld  │             │   │
│   │   │ • StopCreate │  │ • Read       │  │ • Characters │             │   │
│   │   │ • Calculate  │  │ • Export     │  │ • Places     │             │   │
│   │   └──────────────┘  └──────────────┘  └──────────────┘             │   │
│   │          │                 │                 │                      │   │
│   │          └────────────────┼────────────────┘                       │   │
│   │                           │                                         │   │
│   │   ┌──────────────┐  ┌─────▼────────┐  ┌──────────────┐             │   │
│   │   │  locations   │  │   services   │  │    users     │             │   │
│   │   │    (App)     │  │   (Module)   │  │    (App)     │             │   │
│   │   │              │  │              │  │              │             │   │
│   │   │ • BaseLocations│ • Calculator │  │ • Auth       │             │   │
│   │   │ • Layers     │  │ • StoryMapper│  │ • Profile    │             │   │
│   │   │ • Generator  │  │ • Generator  │  │ • Settings   │             │   │
│   │   └──────────────┘  └──────────────┘  └──────────────┘             │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                          │              │                                    │
│              ┌───────────┴──────────────┴───────────┐                       │
│              ▼                                      ▼                       │
│   ┌─────────────────────┐              ┌─────────────────────┐             │
│   │    PostgreSQL       │              │    Celery + Redis   │             │
│   │                     │              │                     │             │
│   │ • base_locations    │              │ • Story Generation  │             │
│   │ • location_layers   │              │ • Location Gen      │             │
│   │ • user_worlds       │              │ • Export Tasks      │             │
│   │ • trips            │              │ • Email             │             │
│   │ • stories          │              │                     │             │
│   │ • chapters         │              │                     │             │
│   └─────────────────────┘              └─────────────────────┘             │
│                                                   │                         │
│                                                   ▼                         │
│                                        ┌─────────────────────┐             │
│                                        │   Anthropic API     │             │
│                                        │                     │             │
│                                        │ • Location Data     │             │
│                                        │ • Story Content     │             │
│                                        └─────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Komponenten

### 4.1 Django Apps

#### `trips` - Reiseverwaltung

```
trips/
├── models.py          # Trip, Stop, Transport
├── views.py           # CRUD Views
├── forms.py           # TripForm, StopFormSet
├── services.py        # ReadingTimeCalculator
├── templates/
│   └── trips/
│       ├── trip_form.html
│       ├── trip_detail.html
│       └── partials/
│           ├── stop_form.html
│           └── transport_form.html
└── urls.py
```

**Models:**
- `Trip` - Hauptreise (User, Name, Datum)
- `Stop` - Einzelner Stopp (Stadt, Land, Unterkunft, Daten)
- `Transport` - Transport zwischen Stopps (Typ, Dauer)

#### `locations` - 3-Schichten Location-System

```
locations/
├── models.py          # BaseLocation, LocationLayer
├── repository.py      # DB-Zugriff
├── generator.py       # On-Demand LLM Generation
├── services.py        # get_merged_location()
├── management/
│   └── commands/
│       ├── seed_locations.py
│       └── clear_cache.py
└── admin.py
```

**Models:**
- `BaseLocation` - Basis-Ortsdaten (shared)
- `LocationLayer` - Genre-spezifische Layer (shared)
- `ResearchCache` - LLM-Response Cache

#### `worlds` - User Worlds

```
worlds/
├── models.py          # UserWorld, Character, PersonalPlace
├── views.py           # CRUD für User-Daten
├── forms.py           # CharacterForm, PlaceForm
├── services.py        # get_or_create_world()
└── templates/
    └── worlds/
        ├── world_detail.html
        ├── character_form.html
        └── partials/
```

**Models:**
- `UserWorld` - User-spezifische Einstellungen
- `Character` - Story-Charaktere
- `PersonalPlace` - Persönliche Orte
- `LocationMemory` - Story-Erinnerungen

#### `stories` - Story-Generierung

```
stories/
├── models.py          # Story, Chapter, ReadingProgress
├── views.py           # Generate, Read, Export
├── tasks.py           # Celery Tasks
├── generator.py       # IntegratedStoryGenerator
├── prompts.py         # Prompt Templates
└── templates/
    └── stories/
        ├── story_detail.html
        ├── chapter_read.html
        └── partials/
            └── chapter_content.html
```

**Models:**
- `Story` - Generierte Geschichte
- `Chapter` - Einzelnes Kapitel
- `ReadingProgress` - Lesefortschritt

### 4.2 Services Module

```
services/
├── calculator.py      # ReadingTimeCalculator
├── story_mapper.py    # StoryMapper (Beats → Chapters)
├── llm_client.py      # Anthropic API Wrapper
└── exporters/
    ├── markdown.py
    ├── pdf.py
    └── epub.py
```

---

## 5. Datenfluss

### 5.1 Reise erstellen

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│  trips/  │────▶│  trips/  │────▶│  trips/  │
│  Form    │     │  views   │     │  forms   │     │  models  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                                  │
                      │                                  ▼
                      │                           ┌──────────┐
                      │                           │PostgreSQL│
                      │                           └──────────┘
                      ▼
               ┌──────────────┐
               │ HTMX Partial │
               │   Response   │
               └──────────────┘
```

### 5.2 Story generieren

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────▶│ stories/ │────▶│  Celery  │────▶│  Task    │
│  Click   │     │  views   │     │  Queue   │     │  Worker  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                                                   │
     │                                                   ▼
     │           ┌───────────────────────────────────────────┐
     │           │                                           │
     │           │  ┌──────────┐  ┌──────────┐  ┌────────┐  │
     │           │  │Calculator│  │  Mapper  │  │LocGen  │  │
     │           │  │          │──▶│          │──▶│        │  │
     │           │  │ReadTime  │  │ Chapters │  │Merged  │  │
     │           │  └──────────┘  └──────────┘  └────────┘  │
     │           │                                   │       │
     │           │                                   ▼       │
     │           │                            ┌──────────┐  │
     │           │                            │ Anthropic│  │
     │           │                            │   API    │  │
     │           │                            └──────────┘  │
     │           │                                   │       │
     │           │                                   ▼       │
     │           │                            ┌──────────┐  │
     │           │                            │ Chapters │  │
     │           │                            │ Content  │  │
     │           │                            └──────────┘  │
     │           │                                           │
     │           └───────────────────────────────────────────┘
     │                                                   │
     ▼                                                   ▼
┌──────────────┐                               ┌──────────────┐
│ HTMX Polling │◄──────────────────────────────│   Webhook    │
│   Progress   │                               │   /done      │
└──────────────┘                               └──────────────┘
```

### 5.3 Location on-demand

```
┌──────────────────────────────────────────────────────────────┐
│                    get_merged_location()                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│   1. Check BaseLocation                                       │
│      │                                                        │
│      ├─── EXISTS ────────────────────────────┐               │
│      │                                        │               │
│      └─── NOT FOUND                           │               │
│           │                                   │               │
│           ▼                                   │               │
│      Check Cache ─── EXISTS ──────────┐      │               │
│           │                           │      │               │
│           └─── NOT FOUND              │      │               │
│                │                      │      │               │
│                ▼                      ▼      ▼               │
│           ┌─────────┐           ┌─────────────┐              │
│           │Claude   │           │ PostgreSQL  │              │
│           │API Call │───────────▶│   Save      │              │
│           └─────────┘           └─────────────┘              │
│                                       │                       │
│   2. Check LocationLayer              │                       │
│      (same flow)                      │                       │
│                                       │                       │
│   3. Load UserWorld                   │                       │
│      │                                │                       │
│      ▼                                ▼                       │
│   ┌─────────────────────────────────────────────────────┐    │
│   │                    MERGE                             │    │
│   │                                                      │    │
│   │  BaseLocation + Layer + UserWorld                   │    │
│   │  - Apply exclusions                                 │    │
│   │  - Add personal places                              │    │
│   │  - Include memories                                 │    │
│   │                                                      │    │
│   └─────────────────────────────────────────────────────┘    │
│                          │                                    │
│                          ▼                                    │
│                  MergedLocationData                           │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Nächster Teil

→ **Teil 2: Datenmodelle** (Django Models, Datenbankschema)
