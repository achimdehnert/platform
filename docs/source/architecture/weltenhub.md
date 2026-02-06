# Weltenhub Architektur

Zentrale Multi-Tenant Story-Universe Plattform.

**URL**: [weltenforger.com](https://weltenforger.com) | **Repo**: `achimdehnert/weltenhub`

## Tech Stack

| Layer | Technologie |
|-------|------------|
| Backend | Django 5.0 + DRF |
| Database | PostgreSQL 16 (shared `bfagent_db`) |
| Cache | Redis 7 |
| Task Queue | Celery + django-celery-beat |
| Frontend | Bootstrap 5 + HTMX 1.9 |
| Deployment | Docker Compose auf Hetzner VM |

## Django Apps

```text
apps/
├── core/           # Base models, mixins, middleware, LLM services
├── public/         # Landing page, Impressum, Datenschutz
├── dashboard/      # Authenticated CRUD UI (Bootstrap + HTMX)
├── tenants/        # Tenant, Permission, TenantUser
├── lookups/        # Genre, Mood, ConflictLevel, etc.
├── governance/     # DDL: BusinessCase, UseCase, ADR (ADR-017)
├── worlds/         # World, WorldRule
├── locations/      # Location (hierarchisch)
├── characters/     # Character, CharacterArc, Relationship
├── scenes/         # Scene, SceneTemplate, SceneBeat
├── stories/        # Story, Chapter, Timeline, PlotThread
└── enrichment/     # AI Enrichment (DB-driven, LLM-Integration)
```

## Model-Hierarchie

```text
models.Model
  └─ TimestampedModel        (created_at, updated_at)
       └─ AuditableSoftDeleteModel  (+deleted_at, created_by, updated_by)
            └─ TenantAwareModel      (+tenant FK, SoftDeleteManager)
                 └─ World / Character / Story / Scene / Location
```

## Enrichment System

DB-driven AI-Anreicherung: Prompts in `lkp_enrichment_action`, Logs in `wh_enrichment_log`.

**Flow**: Preview → Apply (kein doppelter LLM-Call)

1. User klickt Aktion → HTMX POST → `EnrichExecuteView`
2. LLM generiert → Preview in `EnrichmentLog` (status=preview)
3. User klickt "Übernehmen" → `EnrichApplyView`
4. `apply_preview(log_id)` → Felder gesetzt, status=success

## Referenz-ADRs

- **ADR-018**: Weltenhub Architecture
- **ADR-019**: Weltenhub UI, Templates, APIs

Vollständige Architektur-Doku: `weltenhub/docs/ARCHITECTURE.md`
