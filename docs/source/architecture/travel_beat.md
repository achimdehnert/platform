# Travel-Beat (DriftTales) Architecture

## Overview

Travel-Beat generates AI-powered travel stories from trip data.
Production domain: **drifttales.com** / **drifttales.app**

## Core Pipeline

```text
Trip Import (CSV/Manual)
  → Stop Enrichment (ADR TB-020)
    → Plausibility → Geocoding → Weather → Culture → Weltenhub
  → Story Generation (Orchestrator)
    → Input Collection (TripInputHandler, WeatherInputHandler)
    → Outline Generation (LLM)
    → Chapter Generation (LLM, per stop)
    → Post-Generation Review (ADR TB-019)
      → PlanReviewer → StoryReviewer → StoryOptimizer
    → Weltenhub Sync (World + Locations)
```

## Key Services

### Stop Enrichment Pipeline (TB-020)

| Service | API | Tier |
|---------|-----|------|
| Plausibility | Local (no API) | All |
| Geocoding | Nominatim (OSM) | All |
| Weather | Open-Meteo | All |
| Culture | Static dataset (16 countries) | All |
| Weltenhub Sync | Weltenhub REST API | Standard+ |

Files: `apps/trips/services/enrichment/`

### Story Review Pipeline (TB-019)

| Component | Purpose |
|-----------|---------|
| PlanReviewer | Compliance check vs travel plan |
| StoryReviewer | Chapter quality scoring (0.0-1.0) |
| StoryOptimizer | Patch/Insert/Expand proposals |
| StoryReviewPipeline | Coordinator (230 lines) |

Files: `apps/stories/services/review/`

### Tier-Gating

All enrichment and review features are gated via `TierConfig`:

| Feature | Free | Standard | Premium |
|---------|------|----------|---------|
| Geocoding + Weather + Culture | Yes | Yes | Yes |
| Weltenhub Sync (World+Location) | No | Yes | Yes |
| Plan Compliance Check | No | Yes | Yes |
| Full Quality Review | No | No | Yes |
| Auto-Optimization | No | No | Yes |

### Weltenhub Integration

- `WeltenhubClient` — REST client for Worlds, Characters, Scenes, Locations
- `WeltenhubStopSync` — Syncs Trip→World, Stop→Location
- `WeltenhubIntegration` — Higher-level sync for story generation

## Data Model

```text
Trip (1) ──→ (N) Stop
  │                 ├── enrichment_data (JSONField)
  │                 ├── enrichment_status (none/pending/partial/complete/failed)
  │                 └── enriched_at (DateTimeField)
  │
  └──→ (N) Story
              ├── (N) Chapter
              ├── (1) StoryReview
              │         ├── compliance_report (JSON)
              │         ├── quality_report (JSON)
              │         └── overall_score (0.0-1.0)
              └── (N) StoryOptimization
                        ├── strategy (patch/insert/expand)
                        └── severity (critical/high/medium/low)
```

## Deployment

- **Container**: `travel_beat_web` (Django + Gunicorn)
- **Celery**: `travel_beat_celery` (async tasks)
- **Celery Beat**: `travel_beat_celery_beat` (scheduled)
- **DB**: `travel_beat_db` (PostgreSQL 15)
- **Redis**: `travel_beat_redis`
- **Caddy**: `travel_beat_caddy` (reverse proxy)

## ADRs

| ADR | Title | Status |
|-----|-------|--------|
| TB-019 | Story Review & Optimization | Implemented |
| TB-020 | Stop-Enrichment & Weltenhub Pipeline | Implemented |
