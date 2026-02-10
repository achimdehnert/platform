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

## Character Trait System (seit 2026-02-10)

Charaktere haben **bipolare Trait-Slider** (0–100):

| Tabelle | Zweck |
|---------|-------|
| `lkp_character_trait` | 10 Traits mit low/high Labels |
| `wh_character_trait_value` | Character × Trait → Wert 0–100 |

Traits (z.B. Vorsichtig ↔ Mutig) werden im Character-Formular
als Range-Slider angezeigt und fließen automatisch in die
AI-Enrichment-Prompts als `{traits}` Platzhalter ein.

## Enrichment System

DB-driven AI-Anreicherung: Prompts in `lkp_enrichment_action`, Logs in `wh_enrichment_log`.

**Flow**: Preview → Apply (kein doppelter LLM-Call)

1. User klickt Aktion → HTMX POST → `EnrichExecuteView`
2. LLM generiert → Preview in `EnrichmentLog` (status=preview)
3. User klickt "Übernehmen" → `EnrichApplyView`
4. `apply_preview(log_id)` → Felder gesetzt, status=success

**Character-Aktionen**: `character_full_profile`, `character_profile`, `character_motivation`

## Referenz-ADRs

- **ADR-018**: Weltenhub Architecture
- **ADR-019**: Weltenhub UI, Templates, APIs

Vollständige Architektur-Doku: `weltenhub/docs/ARCHITECTURE.md` (v1.1.0)
