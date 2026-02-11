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
    → V2 Legacy: Outline → Chapter Generation (per stop)
    → V3 Three-Phase (ADR-025, feature-gated):
      Phase 1: Storyline (LLM → PlotThreads, StopNarrativeRoles)
      Phase 2: Chapter Consolidation (deterministic)
      Phase 3: Chapter Generation (LLM, per chapter)
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

### 3-Phase Story Pipeline (ADR-025)

Feature-gated via `TierConfig.has_feature("three_phase_pipeline")`.
Falls back to V2 legacy pipeline when disabled.

| Phase | Service | Type | Output |
|-------|---------|------|--------|
| 1. Storyline | `StorylineGenerator` | LLM call | PlotThreads, StopNarrativeRoles, TransportMoments |
| 2. Consolidation | `ChapterConsolidator` | Deterministic | Chapter plans (stops → chapters) |
| 3. Chapters | Orchestrator loop | LLM calls | Final chapter text |

New models (Migration 0014):

- `PlotThread` — Named story arcs spanning multiple stops
- `StopNarrativeRole` — Per-stop narrative role + emotional tone
- `TransportMoment` — Narrative use of transport segments

Files: `apps/stories/services/storyline_generator.py`,
`apps/stories/services/chapter_consolidator.py`,
`apps/stories/models/storyline.py`,
`apps/stories/schemas/storyline_spec.py`

### Tier-Gating

All enrichment and review features are gated via `TierConfig`:

| Feature | Free | Standard | Premium |
|---------|------|----------|---------|
| Geocoding + Weather + Culture | Yes | Yes | Yes |
| Weltenhub Sync (World+Location) | No | Yes | Yes |
| Plan Compliance Check | No | Yes | Yes |
| Full Quality Review | No | No | Yes |
| Auto-Optimization | No | No | Yes |
| 3-Phase Pipeline (ADR-025) | No | No | Yes |

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
              ├── pipeline_version (V2_LEGACY / V3_THREE_PHASE)
              ├── (N) Chapter
              ├── (1) StoryOutline
              │         ├── storyline_theme, narrative_arc (V3)
              │         ├── (N) PlotThread (V3)
              │         ├── (N) StopNarrativeRole (V3)
              │         └── (N) TransportMoment (V3)
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
| ADR-025 | 3-Phase Story Generation Pipeline | **Implemented** |
| ADR-026 | Smart Location Enrichment v2 | Proposed |
