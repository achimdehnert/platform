# Architecture Decision Records — Index

> **Last updated:** 2026-02-26  
> **Next free ADR number:** 089

## Legend

| Status | Bedeutung |
|--------|-----------|
| `Proposed` | Vorgeschlagen, noch nicht akzeptiert |
| `Accepted` | Akzeptiert und gültig |
| `Deprecated` | Veraltet, ersetzt durch neueres ADR |
| `Superseded` | Vollständig ersetzt |

| Repository | Kürzel |
|-----------|--------|
| platform | `platform` |
| bfagent | `bfagent` |
| risk-hub | `risk-hub` |
| weltenhub | `weltenhub` |
| travel-beat | `travel-beat` |
| mcp-hub | `mcp-hub` |
| wedding-hub | `wedding-hub` |
| pptx-hub | `pptx-hub` |

---

## ADR Index

| # | Title | Status | Repo | Link |
|---|-------|--------|------|------|
| 001 | Initial Architecture Decisions | `Accepted` | `platform` | [ADR-001](ADR-001-initial-architecture.md) |
| 002 | Django as Web Framework | `Accepted` | `platform` | [ADR-002](ADR-002-django-framework.md) |
| 003 | PostgreSQL as Primary Database | `Accepted` | `platform` | [ADR-003](ADR-003-postgresql.md) |
| 004 | Docker-based Deployment | `Accepted` | `platform` | [ADR-004](ADR-004-docker-deployment.md) |
| 005 | Hetzner Cloud Infrastructure | `Accepted` | `platform` | [ADR-005](ADR-005-hetzner-cloud.md) |
| 006 | GitHub Actions for CI/CD | `Accepted` | `platform` | [ADR-006](ADR-006-github-actions.md) |
| 007 | Tailwind CSS for Styling | `Accepted` | `platform` | [ADR-007](ADR-007-tailwind-css.md) |
| 008 | HTMX for Dynamic Interactions | `Accepted` | `platform` | [ADR-008](ADR-008-htmx.md) |
| 009 | Django REST Framework for APIs | `Accepted` | `platform` | [ADR-009](ADR-009-drf.md) |
| 010 | Redis for Caching and Message Broker | `Accepted` | `platform` | [ADR-010](ADR-010-redis.md) |
| 011 | Celery for Background Tasks | `Accepted` | `platform` | [ADR-011](ADR-011-celery.md) |
| 012 | Pytest as Test Framework | `Accepted` | `platform` | [ADR-012](ADR-012-pytest.md) |
| 013 | Ruff for Linting and Formatting | `Accepted` | `platform` | [ADR-013](ADR-013-ruff.md) |
| 014 | Pydantic v2 for Data Validation | `Accepted` | `platform` | [ADR-014](ADR-014-pydantic-v2.md) |
| 015 | GHCR as Container Registry | `Accepted` | `platform` | [ADR-015](ADR-015-ghcr.md) |
| 016 | Nginx as Reverse Proxy | `Accepted` | `platform` | [ADR-016](ADR-016-nginx.md) |
| 017 | Let's Encrypt for TLS | `Accepted` | `platform` | [ADR-017](ADR-017-lets-encrypt.md) |
| 018 | Feature Branch Workflow | `Accepted` | `platform` | [ADR-018](ADR-018-feature-branches.md) |
| 019 | Semantic Versioning | `Accepted` | `platform` | [ADR-019](ADR-019-semver.md) |
| 020 | MADR 4.0 as ADR Format | `Accepted` | `platform` | [ADR-020](ADR-020-madr-format.md) |
| 021 | Platform Infrastructure Conventions | `Accepted` | `platform` | [ADR-021](ADR-021-platform-infrastructure.md) |
| 022 | Service Layer Pattern | `Accepted` | `platform` | [ADR-022](ADR-022-service-layer.md) |
| 023 | Multi-Tenant Architecture | `Accepted` | `platform` | [ADR-023](ADR-023-multi-tenant.md) |
| 024 | Django Shared Tenancy Package | `Accepted` | `platform` | [ADR-024](ADR-024-shared-tenancy.md) |
| 025 | Monitoring with Prometheus + Grafana | `Proposed` | `platform` | [ADR-025](ADR-025-monitoring.md) |
| 026 | Error Tracking with Sentry | `Proposed` | `platform` | [ADR-026](ADR-026-sentry.md) |
| 027 | API Versioning Strategy | `Accepted` | `platform` | [ADR-027](ADR-027-api-versioning.md) |
| 028 | Database Migration Safety | `Accepted` | `platform` | [ADR-028](ADR-028-migration-safety.md) |
| 029 | Shared Python Packages | `Accepted` | `platform` | [ADR-029](ADR-029-shared-packages.md) |
| 030 | Component Pattern for HTMX | `Accepted` | `platform` | [ADR-030](ADR-030-component-pattern.md) |
| 031 | Factory Boy for Test Data | `Accepted` | `platform` | [ADR-031](ADR-031-factory-boy.md) |
| 032 | Google-Style Docstrings | `Accepted` | `platform` | [ADR-032](ADR-032-docstrings.md) |
| 033 | isort for Import Sorting | `Deprecated` | `platform` | [ADR-033](ADR-033-isort.md) |
| 034 | Type Hints Required | `Accepted` | `platform` | [ADR-034](ADR-034-type-hints.md) |
| 035 | Shared Django Tenancy Package | `Accepted` | `platform` | [ADR-035](ADR-035-shared-tenancy-package.md) |
| 036 | Content Security Policy | `Proposed` | `platform` | [ADR-036](ADR-036-csp.md) |
| 037 | Rate Limiting Strategy | `Proposed` | `platform` | [ADR-037](ADR-037-rate-limiting.md) |
| 038 | Backup Strategy | `Accepted` | `platform` | [ADR-038](ADR-038-backup-strategy.md) |
| 039 | Log Aggregation | `Proposed` | `platform` | [ADR-039](ADR-039-log-aggregation.md) |
| 040 | Health Check Endpoints | `Accepted` | `platform` | [ADR-040](ADR-040-health-checks.md) |
| 041 | HTMX Component Pattern | `Accepted` | `platform` | [ADR-041](ADR-041-htmx-components.md) |
| 042 | Django Ninja for risk-hub API | `Accepted` | `risk-hub` | [ADR-042](ADR-042-django-ninja.md) |
| 043 | Expand-Contract Migrations | `Accepted` | `platform` | [ADR-043](ADR-043-expand-contract.md) |
| 044 | Non-Root Docker Containers | `Accepted` | `platform` | [ADR-044](ADR-044-non-root-docker.md) |
| 045 | Secret Management with SOPS | `Accepted` | `platform` | [ADR-045](ADR-045-sops.md) |
| 046 | Three-Stage CI/CD Pipeline | `Accepted` | `platform` | [ADR-046](ADR-046-three-stage-pipeline.md) |
| 047 | Docker Compose Hardening | `Accepted` | `platform` | [ADR-047](ADR-047-compose-hardening.md) |
| 048 | Multi-Stage Docker Builds | `Accepted` | `platform` | [ADR-048](ADR-048-multi-stage-builds.md) |
| 049 | Worker Healthcheck Pattern | `Accepted` | `platform` | [ADR-049](ADR-049-worker-healthcheck.md) |
| 050 | Self-Hosted GitHub Runner | `Accepted` | `platform` | [ADR-050](ADR-050-self-hosted-runner.md) |
| 051 | Deploy Path Convention | `Accepted` | `platform` | [ADR-051](ADR-051-deploy-path.md) |
| 052 | Port Allocation Registry | `Accepted` | `platform` | [ADR-052](ADR-052-port-allocation.md) |
| 053 | Zero Breaking Changes Policy | `Accepted` | `platform` | [ADR-053](ADR-053-zero-breaking-changes.md) |
| 054 | Architecture Guardian Agent | `Accepted` | `platform` | [ADR-054](ADR-054-architecture-guardian.md) |
| 055 | ADR Lifecycle Management | `Accepted` | `platform` | [ADR-055](ADR-055-adr-lifecycle.md) |
| 056 | Conscious SSH Root Access | `Accepted` | `platform` | [ADR-056](ADR-056-ssh-root.md) |
| 057 | Nginx over Traefik | `Accepted` | `platform` | [ADR-057](ADR-057-nginx-over-traefik.md) |
| 058 | Image Tagging Strategy | `Accepted` | `platform` | [ADR-058](ADR-058-image-tags.md) |
| 059 | ADR Drift Detection | `Accepted` | `platform` | [ADR-059](ADR-059-drift-detection.md) |
| 060 | Org-Level GitHub Secrets | `Accepted` | `platform` | [ADR-060](ADR-060-org-secrets.md) |
| 061 | env_file over environment interpolation | `Accepted` | `platform` | [ADR-061](ADR-061-env-file.md) |
| 062 | Content Store Architecture | `Accepted` | `platform` | [ADR-062](ADR-062-content-store.md) |
| 063 | Healthcheck in Compose not Dockerfile | `Accepted` | `platform` | [ADR-063](ADR-063-healthcheck-compose.md) |
| 064 | Migration Tracking Table | `Accepted` | `platform` | [ADR-064](ADR-064-migration-tracking.md) |
| 065 | OpenAI as Default LLM Provider | `Accepted` | `platform` | [ADR-065](ADR-065-openai-llm.md) |
| 066 | Structured Logging Format | `Proposed` | `platform` | [ADR-066](ADR-066-structured-logging.md) |
| 067 | Feature Flags via Django Settings | `Accepted` | `platform` | [ADR-067](ADR-067-feature-flags.md) |
| 068 | Celery Beat for Scheduled Tasks | `Accepted` | `platform` | [ADR-068](ADR-068-celery-beat.md) |
| 069 | Django Channels for WebSocket | `Proposed` | `platform` | [ADR-069](ADR-069-django-channels.md) |
| 070 | PDF Generation with WeasyPrint | `Accepted` | `platform` | [ADR-070](ADR-070-weasyprint.md) |
| 071 | S3-Compatible Object Storage | `Proposed` | `platform` | [ADR-071](ADR-071-s3-storage.md) |
| 072 | Multi-Tenancy Schema Isolation | `Accepted` | `platform` | [ADR-072](ADR-072-schema-isolation.md) |
| 073 | Automated Dependency Updates | `Accepted` | `platform` | [ADR-073](ADR-073-dependency-updates.md) |
| 074 | Pre-commit Hooks | `Accepted` | `platform` | [ADR-074](ADR-074-pre-commit.md) |
| 075 | Infrastructure Deploy via GitHub Actions | `Accepted` | `platform` | [ADR-075](ADR-075-infra-deploy.md) |
| 076 | MCP Server Architecture | `Accepted` | `mcp-hub` | [ADR-076](ADR-076-mcp-architecture.md) |
| 077 | Service Catalog with Backstage | `Accepted` | `platform` | [ADR-077](ADR-077-service-catalog.md) |
| 078 | Temporal for Durable Workflows | `Accepted` | `mcp-hub` | [ADR-078](ADR-078-temporal-workflows.md) |
| 079 | Django 5.x as Minimum Version | `Accepted` | `platform` | [ADR-079](ADR-079-django-5.md) |
| 080 | httpx as HTTP Client | `Accepted` | `platform` | [ADR-080](ADR-080-httpx.md) |
| 081 | Alembic for Non-Django Migrations | `Accepted` | `mcp-hub` | [ADR-081](ADR-081-alembic.md) |
| 082 | FastMCP Pattern | `Accepted` | `mcp-hub` | [ADR-082](ADR-082-fastmcp.md) |
| 083 | UV as Python Package Manager | `Proposed` | `platform` | [ADR-083](ADR-083-uv.md) |
| 084 | Shared Test Fixtures Package | `Proposed` | `platform` | [ADR-084](ADR-084-shared-fixtures.md) |
| 085 | OpenClaw Adoption Strategy | `Accepted` | `platform` | [ADR-085](ADR-085-openclaw-adoption.md) |
| 086 | Agent Team Workflow Definition | `Accepted` | `platform` | [ADR-086](ADR-086-agent-team-workflow-definition.md) |
| 087 | Adopt pgvector + FTS Hybrid Search as Platform-wide Semantic Search Engine | `Accepted` | `platform` | [ADR-087](ADR-087-hybrid-search-architecture.md) |
| 088 | Adopt a Shared Notification Registry as Platform-wide Multi-Channel Messaging System | `Accepted` | `platform` | [ADR-088](ADR-088-notification-registry.md) |

---

## Open Points / Hygiene Backlog

- [ ] ADR-025 (Monitoring): Noch `Proposed` — evaluieren oder archivieren
- [ ] ADR-026 (Sentry): Noch `Proposed` — evaluieren oder archivieren
- [ ] ADR-033 (isort): `Deprecated` — Ruff übernimmt Import-Sortierung
- [ ] ADR-036 (CSP): Noch `Proposed` — Security-Review planen
- [ ] ADR-037 (Rate Limiting): Noch `Proposed` — mit ADR-088 Notification Rate-Limiting abgleichen
- [ ] ADR-039 (Log Aggregation): Noch `Proposed` — mit Structured Logging (ADR-066) zusammenführen?
- [ ] ADR-066 (Structured Logging): Noch `Proposed` — Implementierung priorisieren
- [ ] ADR-069 (Django Channels): Noch `Proposed` — WebSocket-Bedarf evaluieren
- [ ] ADR-071 (S3 Storage): Noch `Proposed` — Hetzner Object Storage testen
- [ ] ADR-083 (UV): Noch `Proposed` — Migration von pip → uv planen
- [ ] ADR-084 (Shared Fixtures): Noch `Proposed` — Implementierung nach ADR-087/088
