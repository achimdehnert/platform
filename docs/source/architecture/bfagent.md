# BF Agent Architektur

AI Book Writing Platform mit Zero-Hardcoding CRUD System.

**URL**: [bfagent.iil.pet](https://bfagent.iil.pet) | **Repo**: `achimdehnert/bfagent`

## Tech Stack

| Layer | Technologie |
|-------|------------|
| Backend | Django 5.2 LTS |
| Database | SQLite (dev) / PostgreSQL 16 (prod) |
| Frontend | Bootstrap 5 + HTMX |
| Deployment | Docker Compose auf Hetzner VM |

## Kern-Features

- **Book Writing Studio** — Projekte, Kapitel, Charaktere, Welten
- **AI Enrichment** — LLM-basierte Inhaltsgeneration (OpenAI, Anthropic)
- **Character Cast Generation** — Automatische Figurenerstellung
- **Zero-Hardcoding CRUD** — CRUDConfig Meta-Programming System
- **Control Center** — Enterprise Toolset Dashboard
- **Handler Generator** — AI-gestützte Handler-Erstellung

## App-Struktur

```text
apps/
├── bfagent/              # Haupt-App
│   ├── models.py         # BookProjects, Agents, Characters, etc.
│   ├── views/            # Package: main_views, crud_views, auth_views
│   ├── utils/
│   │   └── crud_config.py  # CRUDConfig + BFAgentTheme
│   ├── services/
│   │   └── project_enrichment.py
│   └── domains/
│       └── book_writing/
│           ├── models/
│           ├── handlers/
│           └── services/   # llm_service, context_builder
├── hub/                  # Central dashboard
├── core/                 # Shared utilities
└── control_center/       # Enterprise tools
```

## Authentifizierung

| Gruppe | Zugriff |
|--------|---------|
| BookWriting | Book Writing Studio |
| MedicalTranslation | Medical Translation |
| Superuser | Alles + Control Center |

## CRUDConfig System

Meta-Programming: Ein `CRUDConfig` im Model generiert automatisch
List-Displays, Search, Filter, Form-Layouts, HTMX-Verhalten und Actions.

```text
GET /api/crud-config/bookprojects/  → JSON mit kompletter Konfiguration
GET /dynamic/projects/              → Dynamisch generierte Views
```

## Enterprise Tools (Control Center)

1. **migration_fixer** — Database Migration Safety
2. **htmx_scanner_v3** — HTMX Code Analysis
3. **quality_assurance** — Comprehensive QA
4. **template_url_validator** — URL Pattern Validation
5. **model_consistency_checker** — Model/Form/Template Sync
6. **model_consistency_checker_v2** — BF Agent v2.0 Compliance
