---
status: accepted
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-018: Weltenhub - Zentrale Story-Universe Plattform

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-04 |
| **Author** | Achim Dehnert |
| **Scope** | platform |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-015 (Platform Governance), ADR-017 (Story Entity Generation) |

---

## 1. Executive Summary

Weltenhub ist eine **zentrale, multi-tenant-fähige Plattform** für die Verwaltung von:

- **Welten** (Worlds) - Fiktive Universen mit Regeln, Settings, Geschichte
- **Locations** - Hierarchische Orte innerhalb von Welten
- **Characters** - Figuren mit Arcs, Relationships, Rollen
- **Scenes** - Szenen mit Templates, Beats, Connections
- **Stories** - Geschichten mit Chapters, Timelines, PlotThreads
- **Templates** - Wiederverwendbare Vorlagen für alle Entitäten

**Kernprinzipien:**
- Database-First (keine Enums, alles aus Lookup Tables)
- Strikte Normalisierung (3NF)
- Tenant-Isolation (Row-Level Security)
- Separation of Concerns
- Idempotente Operationen

---

## 2. Context

### 2.1 Problem Statement

| Problem | Betroffene Apps | Impact |
|---------|-----------------|--------|
| Redundante Models für Scenes, Locations | travel-beat, bfagent | Inkonsistenz, Wartungsaufwand |
| Keine zentrale Weltenverwaltung | alle | Welten nicht wiederverwendbar |
| Hardcoded Choices statt DB Lookups | bfagent | Code-Änderung für neue Optionen |
| Keine Tenant-Isolation | alle | Datenschutz, Multi-Kunde nicht möglich |

### 2.2 Anforderungen

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | Zentrale Models für World, Location, Scene, Character, Story | CRITICAL |
| R2 | Multi-Tenant mit Row-Level Security | CRITICAL |
| R3 | Database-driven Lookups (Genre, Mood, ConflictLevel, etc.) | CRITICAL |
| R4 | API für Consumer-Apps (travel-beat, bfagent) | HIGH |
| R5 | Soft-Migration ohne Breaking Changes | HIGH |
| R6 | Django + HTMX + Postgres 16 auf Hetzner | HIGH |
| R7 | Docker-basiertes Deployment | HIGH |
| R8 | Idempotente Migrationen und Scripts | MEDIUM |

### 2.3 Design-Prinzipien

| Prinzip | Umsetzung |
|---------|-----------|
| **Database-First** | Alle Choices aus `lkp_*` Tables |
| **Strict Normalization** | 3NF, keine Redundanz |
| **Tenant-Isolation** | `tenant_id` FK auf allen Daten-Models |
| **Separation of Concerns** | Models, Services, Views, APIs getrennt |
| **Idempotent** | Alle Scripts mehrfach ausführbar |
| **No Magic** | Explizite Konfiguration, keine stillen Fallbacks |

---

## 3. Architecture

### 3.1 System-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HETZNER VM                                     │
│                          88.198.191.108                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Docker Compose Stack                              │   │
│  │                                                                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │   │
│  │  │ weltenhub   │  │   nginx     │  │   redis     │                  │   │
│  │  │  (Django)   │  │  (Reverse   │  │  (Cache,    │                  │   │
│  │  │             │  │   Proxy)    │  │   Sessions) │                  │   │
│  │  │ Port: 8000  │  │ Port: 80/443│  │ Port: 6379  │                  │   │
│  │  └──────┬──────┘  └─────────────┘  └─────────────┘                  │   │
│  │         │                                                            │   │
│  │         │  ┌─────────────────────────────────────────────────────┐  │   │
│  │         │  │              PostgreSQL 16 (External)               │  │   │
│  │         └──┤              weltenhub_db                           │  │   │
│  │            │              Port: 5432                              │  │   │
│  │            │              + pgbouncer (optional)                  │  │   │
│  │            └─────────────────────────────────────────────────────┘  │   │
│  │                                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                           CONSUMER APPS                                     │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ travel-beat │  │   bfagent   │  │   mcp-hub   │  │ Future Apps │       │
│  │             │  │             │  │             │  │             │       │
│  │ Trips→Scene │  │ BookProject │  │ Integration │  │ Games, VR   │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                │                │                │               │
│         └────────────────┴────────────────┴────────────────┘               │
│                                   │                                         │
│                                   ▼                                         │
│                    ┌─────────────────────────────┐                          │
│                    │   Weltenhub REST API        │                          │
│                    │   /api/v1/worlds/           │                          │
│                    │   /api/v1/locations/        │                          │
│                    │   /api/v1/scenes/           │                          │
│                    └─────────────────────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WELTENHUB DATABASE SCHEMA                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TENANT LAYER                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ wh_tenant       │  │ wh_tenant_user  │  │ wh_permission   │             │
│  │                 │  │                 │  │                 │             │
│  │ id (UUID)       │  │ id (UUID)       │  │ id (UUID)       │             │
│  │ name            │◄─┤ tenant_id (FK)  │  │ code            │             │
│  │ slug            │  │ user_id (FK)    │  │ name            │             │
│  │ is_active       │  │ role            │  │ description     │             │
│  │ settings (JSON) │  │ permissions     │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  LOOKUP TABLES (Database-Driven Choices)                                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ lkp_genre       │  │ lkp_mood        │  │ lkp_conflict_lvl│             │
│  │                 │  │                 │  │                 │             │
│  │ id, code, name  │  │ id, code, name  │  │ id, code, name  │             │
│  │ name_de, color  │  │ name_de, color  │  │ intensity       │             │
│  │ order, is_active│  │ order, is_active│  │ order, is_active│             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ lkp_location_typ│  │ lkp_scene_type  │  │ lkp_char_role   │             │
│  │                 │  │                 │  │                 │             │
│  │ id, code, name  │  │ id, code, name  │  │ id, code, name  │             │
│  │ parent_type     │  │ icon, color     │  │ description     │             │
│  │ order, is_active│  │ order, is_active│  │ order, is_active│             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  CORE MODELS                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ wh_world        │  │ wh_location     │  │ wh_character    │             │
│  │                 │  │                 │  │                 │             │
│  │ id (UUID)       │  │ id (UUID)       │  │ id (UUID)       │             │
│  │ tenant_id (FK)  │◄─┤ tenant_id (FK)  │  │ tenant_id (FK)  │             │
│  │ name            │  │ world_id (FK)───┼──┤ world_id (FK)   │             │
│  │ slug            │  │ parent_id (FK)  │  │ name            │             │
│  │ genre_id (FK)   │  │ location_type_id│  │ role_id (FK)    │             │
│  │ description     │  │ name            │  │ description     │             │
│  │ setting_era     │  │ description     │  │ personality     │             │
│  │ rules (JSON)    │  │ coordinates     │  │ backstory       │             │
│  │ is_public       │  │ is_public       │  │ is_protagonist  │             │
│  │ version         │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ wh_scene_templ  │  │ wh_scene        │  │ wh_story        │             │
│  │                 │  │                 │  │                 │             │
│  │ id (UUID)       │  │ id (UUID)       │  │ id (UUID)       │             │
│  │ tenant_id (FK)  │◄─┤ tenant_id (FK)  │  │ tenant_id (FK)  │             │
│  │ name            │  │ template_id(FK)─┼──┤ world_id (FK)   │             │
│  │ slug            │  │ story_id (FK)───┼──┤ title           │             │
│  │ scene_type_id   │  │ chapter_id (FK) │  │ genre_id (FK)   │             │
│  │ genre_id (FK)   │  │ from_location   │  │ spice_level     │             │
│  │ description_1-5 │  │ to_location     │  │ status          │             │
│  │ mood_tags (JSON)│  │ title           │  │ premise         │             │
│  │ is_public       │  │ description     │  │                 │             │
│  │ order           │  │ mood_id (FK)    │  │                 │             │
│  └─────────────────┘  │ order           │  └─────────────────┘             │
│                       │ is_auto_gen     │                                   │
│                       └─────────────────┘                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation

### 4.1 Project Structure

```
weltenhub/
├── .env.example                 # Environment template
├── .env.prod                    # Production environment (gitignored)
├── docker-compose.yml           # Development stack
├── docker-compose.prod.yml      # Production stack
├── Dockerfile                   # Django app container
├── manage.py
├── requirements.txt
├── pyproject.toml
│
├── config/                      # Django settings (Separation of Concerns)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py              # Shared settings
│   │   ├── development.py       # Dev overrides
│   │   └── production.py        # Prod overrides
│   ├── urls.py
│   └── wsgi.py
│
├── apps/
│   ├── core/                    # Shared utilities
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # AuditableSoftDeleteModel
│   │   │   └── tenant.py        # TenantAwareModel
│   │   ├── middleware/
│   │   │   └── tenant.py        # TenantMiddleware
│   │   └── services/
│   │       └── lookup_service.py
│   │
│   ├── tenants/                 # Tenant management
│   │   ├── models.py            # Tenant, TenantUser
│   │   ├── admin.py
│   │   └── services.py
│   │
│   ├── lookups/                 # Database-driven choices
│   │   ├── models.py            # Genre, Mood, ConflictLevel, etc.
│   │   ├── admin.py
│   │   ├── fixtures/
│   │   │   └── initial_lookups.json
│   │   └── services.py
│   │
│   ├── worlds/                  # World management
│   │   ├── models.py            # World, WorldRule, WorldSetting
│   │   ├── admin.py
│   │   ├── services.py
│   │   └── api/
│   │       ├── views.py
│   │       ├── serializers.py
│   │       └── urls.py
│   │
│   ├── locations/               # Location management
│   │   ├── models.py            # Location (hierarchical)
│   │   ├── admin.py
│   │   ├── services.py
│   │   └── api/
│   │
│   ├── characters/              # Character management
│   │   ├── models.py            # Character, CharacterArc, Relationship
│   │   ├── admin.py
│   │   ├── services.py
│   │   └── api/
│   │
│   ├── scenes/                  # Scene management
│   │   ├── models.py            # SceneTemplate, Scene, Beat
│   │   ├── admin.py
│   │   ├── services.py
│   │   └── api/
│   │
│   ├── stories/                 # Story management
│   │   ├── models.py            # Story, Chapter, Timeline
│   │   ├── admin.py
│   │   ├── services.py
│   │   └── api/
│   │
│   └── api/                     # Central API configuration
│       ├── urls.py
│       └── permissions.py
│
├── scripts/
│   ├── deploy.sh                # Deployment script
│   ├── migrate.sh               # Migration script
│   └── seed_lookups.sh          # Initial data seeding
│
└── tests/
    ├── conftest.py
    └── ...
```

---

## 5. Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| **Tables** | `wh_` prefix + snake_case | `wh_world`, `wh_scene_template` |
| **Lookup Tables** | `lkp_` prefix + snake_case | `lkp_genre`, `lkp_mood` |
| **Models** | PascalCase | `World`, `SceneTemplate` |
| **Fields** | snake_case | `tenant_id`, `created_at` |
| **Foreign Keys** | `<entity>_id` | `world_id`, `genre_id` |
| **Services** | `<Entity>Service` | `WorldService`, `SceneService` |
| **Views** | `<Entity>ViewSet` | `WorldViewSet` |
| **URLs** | kebab-case | `/api/v1/scene-templates/` |

---

## 6. Migration Strategy

### 6.1 Phasen

| Phase | Zeitraum | Aktion | Risiko |
|-------|----------|--------|--------|
| **1: Setup** | Woche 1 | Weltenhub Monorepo + Docker | Niedrig |
| **2: Models** | Woche 2 | Core Models + Lookups | Niedrig |
| **3: API** | Woche 3 | REST API für Consumer | Niedrig |
| **4: Shadow** | Woche 4 | Dual-Write Mode | Mittel |
| **5: Switch** | Woche 5 | Consumer auf Weltenhub | Mittel |
| **6: Cleanup** | Woche 6 | Alte Models deprecated | Niedrig |

### 6.2 Breaking Change Policy

- **Keine Breaking Changes** in Phase 1-4
- Feature Flags für alle neuen Funktionen
- Alte APIs bleiben 6 Monate verfügbar (deprecated)
- Migration Scripts sind idempotent

---

## 7. References

- ADR-015: Platform Governance System
- ADR-017: Story Entity Generation (travel-beat)
- Writing-Hub Models (bfagent)

