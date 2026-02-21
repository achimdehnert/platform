---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-029: CAD Hub Extraction from bfagent

**Status**: **Accepted** (2026-02-12) — Phase 1 scaffold ✅, Phase 2 deploy ✅, Phase 3 cleanup ✅
**Date**: 2026-02-12
**Author**: Achim Dehnert
**Scope**: bfagent, cad-hub (new repo), platform
**Follows**: ADR-021 (Unified Deployment Pattern), ADR-022 (Platform Consistency Standard v3)
**Review**: ADR-029-REVIEW.md (2 rounds: R1 7C/5I/4M + R2 7C/6I/5M — all addressed)

---

## 1. Problem Statement

`apps/cad_hub/` is a full-featured Django application embedded inside the `bfagent` repository. Actual inventory:

- **16 root Python modules** (views, models, admin, tasks, urls, etc.)
- **15 handlers** (area_classifier, brandschutz ×3, nl_query, pdf_vision, pdf_lageplan, etc.)
- **16 services** (mcp_bridge, dxf_analyzer, ifc_parser, nl2dxf, avb_service, etc.)
- **4 ifc_complete_parser** files (standalone parser, 705-line dataclass models)
- **48+ HTML templates** across 6 subdirectories (analysis/, avb/, brandschutz/, dxf/, nl2cad/, partials/)
- **3 admin files**, **3 management commands**, **2 URL files**

Covering IFC parsing, DXF/DWG analysis, DIN 277 calculations, fire safety (Brandschutz), tendering (AVB), and natural-language-to-CAD generation.

**Problems with current embedding:**

- **Violation of single-responsibility**: bfagent is a book factory agent; cad-hub is a construction/CAD platform — zero domain overlap
- **Monolith scaling**: bfagent Docker image includes all CAD dependencies (ezdxf, ifcopenshell, openpyxl) even when only book features are used
- **Code quality**: `views.py` (29k), `mcp_bridge.py` (35k), `dxf_analyzer.py` (54k) far exceed platform limits (500 lines/file)
- **No multi-tenancy**: Missing `tenant_id`, Organization model, tenant middleware, TenantAwareManager
- **Deploy coupling**: CAD changes require full bfagent redeploy
- **Testing isolation**: CAD tests run in bfagent CI, slowing unrelated PRs
- **No Celery integration**: `tasks.py` uses plain functions, not `@shared_task` decorators

## 2. Decision

Extract `apps/cad_hub/` into a standalone repository `achimdehnert/cad-hub` following ADR-021 conventions, ADR-022 reference templates (`input/*`), and onboard-repo.md workflow.

### 2.1 New Repository Structure

```text
cad-hub/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                  # Platform reusable workflows (@v1)
├── .dockerignore                      # PFLICHT (onboard Step 1.5)
├── .env.example                       # PFLICHT (onboard Step 1.4)
├── requirements.txt                   # Pinned deps (input/Dockerfile uses this)
├── config/
│   ├── __init__.py
│   ├── celery.py                      # Celery app configuration (NEW)
│   ├── settings/
│   │   ├── __init__.py                # Env-dispatcher (reads DJANGO_ENV)
│   │   ├── base.py                    # Shared settings, LOGGING (JSON)
│   │   ├── development.py             # DEBUG=True, sqlite
│   │   └── production.py              # SECURE_*, env-driven
│   ├── urls.py                        # Health + app URL registration
│   ├── wsgi.py
│   └── views.py                       # Landing page + login views
├── apps/
│   ├── core/                          # Shared: org, auth, health, LLM, MCP
│   │   ├── models.py                  # Organization, Membership
│   │   ├── admin.py                   # Organization admin
│   │   ├── middleware.py              # SubdomainTenantMiddleware (excludes HEALTH_PATHS)
│   │   ├── managers.py                # TenantAwareManager
│   │   ├── healthz.py                 # ADR-022 input/healthz.py: HEALTH_PATHS, @csrf_exempt, @require_GET
│   │   └── services/
│   │       ├── llm_client.py          # Extracted from bfagent (has OpenAI fallback)
│   │       └── mcp_bridge/            # Split from 35k-line mcp_bridge.py
│   │           ├── __init__.py
│   │           ├── ifc_bridge.py      # ≤400 lines
│   │           ├── dxf_bridge.py      # ≤400 lines
│   │           └── batch_bridge.py    # ≤400 lines
│   ├── ifc/                           # IFC models, views, services, parser
│   │   ├── models.py                  # IFCProject, IFCModel, Floor, Room, Window, Door, Wall, Slab
│   │   ├── models_legacy.py           # From models_ifc_legacy.py
│   │   ├── admin.py                   # From admin.py (IFC-related registrations)
│   │   ├── urls.py
│   │   ├── tasks.py                   # @shared_task: process_ifc_upload (converted from plain fn)
│   │   ├── views.py                   # Project/Model CRUD (≤400 lines)
│   │   ├── views_analysis.py          # Analysis views (≤400 lines)
│   │   ├── views_query.py             # NL query views (≤400 lines)
│   │   ├── handlers/                  # From handlers/ (IFC-related)
│   │   │   ├── room_analysis.py
│   │   │   ├── area_classifier.py
│   │   │   ├── cad_file_input.py
│   │   │   ├── massen.py
│   │   │   └── use_case_tracker.py
│   │   ├── parser/                    # From ifc_complete_parser/ (4 files, dataclasses)
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # 705 lines — dataclasses, NOT Django models
│   │   │   ├── parser.py
│   │   │   └── example.py
│   │   └── services/
│   │       ├── ifc_parser.py
│   │       ├── ifc_x83_converter.py
│   │       ├── ifc_mcp_client.py
│   │       └── cad_loader.py
│   ├── dxf/                           # DXF/DWG parser, renderer, NL2DXF
│   │   ├── urls.py
│   │   ├── views.py                   # ≤400 lines
│   │   ├── views_upload.py            # ≤400 lines
│   │   ├── views_nl2cad.py            # ≤400 lines
│   │   ├── views_nl2cad_api.py        # ≤400 lines
│   │   ├── handlers/                  # From handlers/ (DXF-related)
│   │   │   ├── nl_query.py
│   │   │   ├── nl_learning.py
│   │   │   ├── pdf_vision.py
│   │   │   ├── pdf_lageplan.py
│   │   │   └── pdf_abstandsflaechen.py
│   │   └── services/
│   │       ├── dxf_parser.py
│   │       ├── dxf_renderer.py
│   │       ├── dwg_converter.py
│   │       ├── nl2dxf.py
│   │       └── analyzer/              # Split from 54k-line dxf_analyzer.py
│   │           ├── __init__.py
│   │           ├── geometry.py        # ≤400 lines
│   │           ├── layers.py          # ≤400 lines
│   │           ├── entities.py        # ≤400 lines
│   │           └── dimensions.py      # ≤400 lines
│   ├── areas/                         # DIN 277, WoFlV calculators
│   │   ├── urls.py
│   │   ├── views.py                   # ≤400 lines
│   │   └── services/
│   │       ├── din277_calculator.py
│   │       └── woflv_calculator.py
│   ├── brandschutz/                   # Fire safety models, views, handlers
│   │   ├── models.py                  # BrandschutzPruefung, Symbol, Mangel, etc.
│   │   ├── admin.py                   # From admin_brandschutz.py
│   │   ├── urls.py                    # From urls_brandschutz.py
│   │   ├── views.py                   # ≤400 lines
│   │   ├── views_report.py            # ≤400 lines
│   │   ├── handlers/                  # From handlers/ (Brandschutz-related)
│   │   │   ├── brandschutz.py
│   │   │   ├── brandschutz_report.py
│   │   │   └── brandschutz_symbols.py
│   │   └── services/
│   ├── avb/                           # Tendering (AVB) models, views
│   │   ├── models.py                  # From models_avb.py (14 models)
│   │   ├── admin.py                   # From admin_avb.py
│   │   ├── urls.py
│   │   ├── views.py                   # ≤400 lines
│   │   ├── views_detail.py            # ≤400 lines
│   │   └── services/
│   │       └── avb_service.py
│   └── export/                        # Excel, GAEB export services
│       ├── urls.py
│       ├── views.py                   # ≤400 lines
│       └── services/
│           ├── export_service.py
│           └── gaeb_generator.py
├── templates/                         # 48+ templates distributed per app
│   ├── base.html                      # App-wide base (Tailwind + HTMX)
│   ├── landing.html                   # Public landing page for nl2cad.de
│   ├── login.html                     # Custom login page
│   └── cad_hub/                       # Per-app template dirs
│       ├── dashboard.html
│       ├── analysis/                  # 5 templates
│       ├── avb/                       # 7 templates
│       ├── brandschutz/               # 7 templates + partials/
│       ├── dxf/                       # 2 templates
│       ├── nl2cad/                    # 1 template
│       └── partials/                  # 8 partial templates
├── docker/
│   └── app/
│       ├── Dockerfile                 # Based on ADR-022 input/Dockerfile
│       └── entrypoint.sh             # Based on ADR-022 input/entrypoint.sh (bash, set -euo pipefail)
├── docker-compose.prod.yml            # Based on ADR-022 input/docker-compose.prod.yml
├── manage.py
├── pyproject.toml
└── README.md
```

### 2.2 Deployment Parameters (per ADR-021 + ADR-022)

| Parameter | Value |
| --- | --- |
| Repository | `achimdehnert/cad-hub` |
| Server path | `/opt/cad-hub` |
| Dockerfile | `docker/app/Dockerfile` (based on `input/Dockerfile`) |
| Entrypoint | `docker/app/entrypoint.sh` (based on `input/entrypoint.sh`: `bash`, `set -euo pipefail`) |
| Compose file | `docker-compose.prod.yml` (based on `input/docker-compose.prod.yml`) |
| GHCR image | `ghcr.io/achimdehnert/cad-hub:${IMAGE_TAG:-latest}` + `:sha-<7char>` |
| Service (migrate) | `cad-hub-migrate` → container `cad_hub_migrate` (`restart: "no"`, runs once) |
| Service (web) | `cad-hub-web` → container `cad_hub_web` |
| Service (worker) | `cad-hub-worker` → container `cad_hub_worker` |
| Service (db) | `cad-hub-db` → container `cad_hub_db` (postgres:16-alpine, `shm_size: 128m`) |
| Service (redis) | `cad-hub-redis` → container `cad_hub_redis` (redis:7-alpine) |
| Internal port | **8094** → 8000 (update ADR-021 §2.9 AND onboard-repo Port Map) |
| Health endpoints | `/livez/` (Docker HC), `/healthz/` (readiness), `/health/` (compat) |
| Health module | `apps/core/healthz.py` with `HEALTH_PATHS`, `@csrf_exempt`, `@require_GET` |
| Domain | **nl2cad.de** (primary) + **www.nl2cad.de** → 301 redirect to non-www |
| DNS | Both A-Records → 88.198.191.108 (already configured) |
| Network | `cad_hub_network` (bridge) |
| Volumes | `cad_hub_pgdata`, `cad_hub_redis_data` |
| Task queue | Celery (convert `tasks.py` plain functions → `@shared_task`) |
| Celery config | `config/celery.py` |
| CI/CD | `ci-cd.yml` with platform reusable workflows (`@v1`) |
| Settings | Split: `config/settings/{base,development,production}.py` |
| `DJANGO_SETTINGS_MODULE` | Production: `config.settings.production`, CI: `config.settings.base` |
| Memory limits | web: 512M, worker: 512M, db: 512M, redis: 256M, migrate: 256M |
| Logging | `json-file` with `max-size`/`max-file` on all services |

### 2.3 Migration Strategy

**Phase 1: Scaffold + Code**

1. Create `achimdehnert/cad-hub` repo
2. Set up Django project structure with split settings + `config/celery.py`
3. Copy code from `bfagent/apps/cad_hub/` into new app structure (see §2.1)
4. Map 15 handlers to target apps (see §2.1 handler directories)
5. Move `ifc_complete_parser/` → `apps/ifc/parser/` (4 files, dataclasses)
6. Map 3 admin files: `admin.py` → `apps/ifc/admin.py`, `admin_avb.py` → `apps/avb/admin.py`, `admin_brandschutz.py` → `apps/brandschutz/admin.py`
7. Distribute 48+ templates to per-app template directories
8. Replace `from apps.bfagent.services.llm_client` with `apps.core.services.llm_client`
9. Create `apps/core/healthz.py` from `input/healthz.py` (HEALTH_PATHS, @csrf_exempt, @require_GET)
10. Create Organization model, Membership, TenantAwareManager, tenant middleware in `apps/core/`
11. Add `tenant_id` to ALL user-data models (see §2.6)
12. Split oversized files — each target file ≤400 lines (see §2.5)
13. Extract business logic from views into `services.py` per app
14. Convert `tasks.py` plain functions → `@shared_task` decorators
15. Create public landing page + custom login page for nl2cad.de
16. Add `requirements.txt` with pinned dependencies (Dockerfile needs this)

**Phase 2: Deploy**

17. Create Dockerfile from `input/Dockerfile` (add ifcopenshell, ezdxf system deps)
18. Create entrypoint.sh from `input/entrypoint.sh` (bash, `set -euo pipefail`, NO inline migrations)
19. Create docker-compose.prod.yml from `input/docker-compose.prod.yml`:
    - `cad-hub-migrate` (separate service, `restart: "no"`, `service_completed_successfully`)
    - `cad-hub-web` (depends_on migrate)
    - `cad-hub-worker` (Celery, depends_on migrate)
    - `cad-hub-db` (postgres:16-alpine, `shm_size: 128m`)
    - `cad-hub-redis` (redis:7-alpine, Celery broker)
    - Network: `cad_hub_network`, Volumes: `cad_hub_pgdata`, `cad_hub_redis_data`
20. Create `.env.example`, `.dockerignore`
21. Server provisioning: `/opt/cad-hub`, `.env.prod`
22. Nginx config: `nl2cad.de.conf` (www → non-www 301 redirect, proxy to 127.0.0.1:8094)
23. SSL: `certbot certonly --webroot -d nl2cad.de -d www.nl2cad.de`
24. CI/CD workflow (`ci-cd.yml` with platform reusable workflows `@v1`)
25. Build, push, deploy, health check (`https://nl2cad.de/livez/`)

**Phase 2.5: Platform Integration**

26. Register in MCP orchestrator (`orchestrator_mcp/local_tools.py` + `server.py`)
27. Update `deploy.md` workflow table
28. Update `backup.md` workflow table
29. Update Port Map in onboard-repo.md (8094 = cad-hub)
30. Update Port Registry in ADR-021 §2.9
31. Create deployment memory with container names, credentials, URLs

**Phase 3: Cleanup**

32. Remove `apps/cad_hub/` from bfagent repo
33. Remove `models_avb.py`, `models_ifc_legacy.py` from bfagent
34. Update bfagent INSTALLED_APPS, urls.py, requirements
35. Rebuild and deploy bfagent (slimmer image)
36. Verify bfagent health after removal

### 2.4 External Dependencies to Resolve

| Dependency | Source | Resolution |
| --- | --- | --- |
| `apps.bfagent.services.llm_client.generate_text` | bfagent LLM wrapper | Copy into `apps/core/services/llm_client.py` (already has OpenAI fallback) |
| `apps.cad_hub.models_avb` → `..models_avb` | Parent-relative import | Move `models_avb.py` into `apps/avb/models.py` (14 models) |
| `apps.cad_hub.models_ifc_legacy` | Legacy IFC models | Move into `apps/ifc/models_legacy.py` |
| `apps.cad_hub.ifc_complete_parser` | Standalone parser submodule | Move into `apps/ifc/parser/` (4 files, dataclasses not Django models) |
| `apps.cad_hub.handlers.base` | Handler base class | Move into `apps/core/handlers/base.py` (shared across apps) |
| `config/celery.py` | Does not exist yet | Create new Celery app configuration |
| `tasks.py` (plain functions) | No `@shared_task` | Convert to Celery tasks, add `config/celery.py` |

### 2.5 File Split Plan (≤400 lines per file)

| Current File | Lines | Split Into | Target Size |
| --- | --- | --- | --- |
| `views.py` (29k) | 29k | `apps/ifc/views.py` + `apps/areas/views.py` + `apps/export/views.py` | ≤400 each |
| `views_avb.py` | 18k | `apps/avb/views.py` + `apps/avb/views_detail.py` | ≤400 each |
| `views_brandschutz.py` | 18k | `apps/brandschutz/views.py` + `views_report.py` | ≤400 each |
| `views_dxf.py` | 16k | `apps/dxf/views.py` + `views_upload.py` | ≤400 each |
| `views_nl2cad.py` | 17k | `apps/dxf/views_nl2cad.py` + `views_nl2cad_api.py` | ≤400 each |
| `views_analysis.py` | 19k | `apps/ifc/views_analysis.py` + `views_query.py` | ≤400 each |
| `mcp_bridge.py` (35k) | 35k | `apps/core/services/mcp_bridge/` (3 modules) | ≤400 each |
| `dxf_analyzer.py` (54k) | 54k | `apps/dxf/services/analyzer/` (4 modules) | ≤400 each |

**Service layer extraction**: Each app gets `services.py` (or `services/` dir) with business logic moved out of views. Views handle HTTP only (per Global Rules).

### 2.6 Multi-Tenancy (per Global Development Rules)

**Organization model** (`apps/core/models.py`):

```python
class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    tenant_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=100, unique=True)

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=20)
```

**Tenant middleware** (`apps/core/middleware.py`):
- Resolves `request.tenant_id` from subdomain
- Excludes HEALTH_PATHS (`/livez/`, `/healthz/`, `/health/`)

**ALL user-data models** get `tenant_id` (verified against `models/__init__.py`):

IFC models (8):

- `IFCProject`, `IFCModel`, `Floor`, `Room`, `Window`, `Door`, `Wall`, `Slab`

AVB models (14 — from `models_avb.py`):

- `ConstructionProject`, `ProjectMilestone`, `CostEstimate`, `CostGroup`, `ProjectPhase`
- `Tender`, `TenderPosition`, `TenderGroup`
- `Bidder`, `Bid`, `BidPosition`, `Award`

Brandschutz models (4 — only actual Django Models, NOT TextChoices):

- `BrandschutzPruefung`, `BrandschutzSymbol`, `BrandschutzMangel`, `BrandschutzSymbolVorschlag`
- NOTE: `BrandschutzKategorie`, `Feuerwiderstandsklasse`, `ExZoneTyp`, `PruefStatus` are TextChoices/IntegerChoices — they do NOT need `tenant_id`
- NOTE: `BrandschutzRegelwerk` is reference data (shared across tenants) — no `tenant_id`

Total: **24 models** need `tenant_id = UUIDField(db_index=True)`.

**All queries** MUST filter by `tenant_id`. Use `TenantAwareManager`:

```python
class TenantAwareManager(models.Manager):
    def for_tenant(self, tenant_id: uuid.UUID):
        return self.filter(tenant_id=tenant_id)
```

## 3. Consequences

### Positive

- **Independent deployment**: CAD changes don't affect bfagent
- **Smaller images**: bfagent drops ~200MB of CAD dependencies
- **Code quality**: Enforced 400-line limit, proper app/service separation, 7 Django apps
- **Multi-tenancy**: Organization model, middleware, queryset filtering — SaaS-ready
- **CI isolation**: Faster CI for both repos
- **Own domain**: nl2cad.de with proper landing page

### Negative

- **One-time migration effort**: ~10-14 hours (36 steps, 24 models + tenant_id, 48 templates, 15 handlers)
- **Template duplication**: base.html needs own copy (standard per ADR-022)
- **LLM client copy**: Minor code duplication until shared package extracted
- **Celery conversion**: tasks.py needs refactoring from plain functions to @shared_task

### Risks

- **Database migration**: New DB means no data migration (acceptable — no production data yet)
- **URL changes**: `/cad-hub/` routes move to nl2cad.de
- **bfagent cleanup**: Must remove cad_hub app cleanly to avoid import errors
- **File split complexity**: 400-line target may require significant refactoring of tightly coupled code
- **ifc_complete_parser/models.py**: 705 lines of dataclasses — may need splitting if exceeding limit

## 4. Alternatives Considered

### 4.1 Keep in bfagent, refactor only

- Pros: No repo overhead
- Cons: Violates SRP, still coupled deploys, monolith image
- **Rejected**: Domain mismatch is fundamental

### 4.2 Extract as Python package (library)

- Pros: Shared via pip
- Cons: Still needs Django project wrapper for deployment; over-engineering
- **Rejected**: Direct repo extraction is simpler

## 5. Verification Checklist (onboard-repo Step 7 + ADR-022 §8)

```text
Repo-Struktur:
  [x] docker/app/Dockerfile (based on input/Dockerfile: multi-stage, non-root, OCI-Labels)
  [x] docker/app/entrypoint.sh (based on input/entrypoint.sh: bash, set -euo pipefail, NO inline migrations)
  [x] docker-compose.prod.yml (based on input/docker-compose.prod.yml: migrate service, env_file)
  [x] .github/workflows/ci.yml + cd-production.yml
  [x] .env.example existiert
  [x] .dockerignore existiert
  [x] requirements.txt existiert (Dockerfile depends on it)
  [x] config/celery.py existiert
  [x] config/settings/{__init__,base,development,production}.py
  [x] apps/core/healthz.py: HEALTH_PATHS, @csrf_exempt, @require_GET
  [x] apps/core/middleware.py: SubdomainTenantMiddleware excludes HEALTH_PATHS
  [x] apps/core/managers.py: TenantAwareManager
  [x] /livez/, /healthz/, /health/ Endpoints registriert in config/urls.py
  [x] pyproject.toml mit korrekten Metadaten
  [x] README.md mit Quickstart
  [x] Landing page + Login page
  [ ] Alle Dateien ≤400 Zeilen (16 files >500 lines — follow-up PR)

ADR-022 Compliance:
  [x] HEALTHCHECK: python urllib auf 127.0.0.1:8000/livez/ (kein curl)
  [x] Compose: env_file: .env.prod (keine environment: mit ${VAR} für App-Config)
  [x] Compose: Named volumes (cad_hub_pgdata, cad_hub_redis_data)
  [x] Compose: Named network (cad_hub_network)
  [x] Entrypoint: DJANGO_SETTINGS_MODULE Validation
  [x] Dockerfile: Non-root user app:1000
  [x] Dockerfile: collectstatic bei Build-time
  [ ] Compose: migrate Service (restart: "no") — currently inline in entrypoint
  [ ] Compose: logging + memory limits — not yet configured
  [ ] Compose: shm_size: 128m für postgres — not yet configured

Server:
  [x] /opt/cad-hub/ Verzeichnis existiert
  [x] .env.prod mit echten Werten
  [x] docker-compose.prod.yml kopiert
  [x] 4 Container laufen und sind healthy (web, worker, db, redis)

Netzwerk:
  [x] DNS A-Record nl2cad.de → 88.198.191.108
  [x] DNS A-Record www.nl2cad.de → 88.198.191.108
  [x] Nginx Config deployed (nl2cad.de.conf)
  [x] SSL-Zertifikat aktiv (Let's Encrypt, expires 2026-05-14)
  [x] HTTPS-Redirect funktioniert
  [x] https://nl2cad.de/livez/ gibt 200

CI/CD:
  [x] .github/workflows/ci.yml (lint, security, build+push GHCR)
  [x] .github/workflows/cd-production.yml (deploy via SSH + rollback)
  [x] deployment/scripts/deploy-remote.sh (ADR-022 compliant)
  [x] .windsurf/workflows/deploy.md
  [ ] GitHub Secrets (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY) — to be set

Platform (2026-02-13):
  [ ] MCP Orchestrator registriert (local_tools.py + server.py)
  [x] deploy.md Workflow erstellt (.windsurf/workflows/deploy.md)
  [x] backup.md Tabelle aktualisiert (cad-hub, risk-hub, weltenhub)
  [x] Memory mit Container-/Deploy-Infos erstellt
  [x] infrastructure.md Port Map aktualisiert (8094, nl2cad.de)
  [ ] Port Registry in ADR-021 §2.9 aktualisiert

bfagent Cleanup (2026-02-13, commit 29b28467):
  [x] apps/cad_hub/ entfernt (137 files, -35615 lines)
  [x] INSTALLED_APPS: commented out
  [x] config/urls.py: commented out
  [x] hub_registry.py: commented out
  [x] init_hubs.py: commented out

Multi-Tenancy:
  [x] Organization + Membership models in apps/core
  [x] TenantAwareManager in apps/core/managers.py
  [x] SubdomainTenantMiddleware setzt request.tenant_id
  [ ] 24 Models haben tenant_id — scaffold done, code copy pending
```

## 6. References

- ADR-021: Unified Deployment Pattern
- ADR-022: Platform Consistency Standard (reference templates in `input/`)
- ADR-029-REVIEW.md: Detailed review findings
- `bfagent/apps/cad_hub/CAD_HUB_STATUS.md`: Current feature inventory
- `platform/.windsurf/workflows/onboard-repo.md`: Onboarding checklist
