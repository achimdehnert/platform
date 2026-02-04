# Weltenhub

Central multi-tenant story universe platform for managing Worlds, Locations, Characters, Scenes, and Stories.

## Overview

Weltenhub serves as the single source of truth for story-related entities, consumed by:
- **travel-beat**: Travel story generation app
- **bfagent**: Book writing assistant

## Tech Stack

- **Backend**: Django 5.0 + Django REST Framework
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Task Queue**: Celery
- **Frontend**: HTMX + TailwindCSS
- **Deployment**: Docker Compose on Hetzner VM

## Key Features

- **Multi-Tenant Architecture**: Row-level isolation via `tenant_id`
- **Database-First Design**: All choices from lookup tables, no hardcoded enums
- **Soft Delete**: `deleted_at` field instead of hard deletes
- **Full Audit Trail**: `created_at`, `updated_at`, `created_by`, `updated_by`
- **UUID Primary Keys**: For external references and distributed systems

## Quick Start

```bash
# Clone repository
git clone https://github.com/achimdehnert/weltenhub.git
cd weltenhub

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Load initial lookup data
python manage.py loaddata apps/lookups/fixtures/initial_lookups.json

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## API Documentation

After starting the server, visit:
- **Swagger UI**: http://localhost:8000/api/docs/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## API Endpoints

| App | Base URL | Description |
|-----|----------|-------------|
| Tenants | `/api/v1/tenants/` | Tenant management |
| Lookups | `/api/v1/lookups/` | Genres, Moods, Types |
| Worlds | `/api/v1/worlds/` | World building |
| Locations | `/api/v1/locations/` | Hierarchical locations |
| Characters | `/api/v1/characters/` | Character management |
| Scenes | `/api/v1/scenes/` | Scene templates & beats |
| Stories | `/api/v1/stories/` | Stories & chapters |

## Deployment

```bash
# Deploy to production
./scripts/deploy.sh [IMAGE_TAG]
```

## Architecture

See [ADR-018: Weltenhub Architecture](../docs/adr/ADR-018-weltenhub-architecture.md) for detailed architecture decisions.

## License

Proprietary - All rights reserved
