# ADR-029: CAD Hub Extraction from bfagent

**Status**: Proposed → **Revised** (Review incorporated 2026-02-12)
**Date**: 2026-02-12
**Author**: Achim Dehnert
**Scope**: bfagent, cad-hub (new repo), platform
**Follows**: ADR-021 (Unified Deployment Pattern), ADR-022 (Platform Consistency)
**Review**: ADR-029-REVIEW.md (7 Critical, 5 Important, 4 Minor — all addressed)

---

## 1. Problem Statement

`apps/cad_hub/` is a full-featured Django application embedded inside the `bfagent` repository. It has grown to ~50 files covering IFC parsing, DXF/DWG analysis, DIN 277 calculations, fire safety (Brandschutz), tendering (AVB), and natural-language-to-CAD generation.

**Problems with current embedding:**

- **Violation of single-responsibility**: bfagent is a book factory agent; cad-hub is a construction/CAD platform — zero domain overlap
- **Monolith scaling**: bfagent Docker image includes all CAD dependencies (ezdxf, ifcopenshell, openpyxl) even when only book features are used
- **Code quality**: `views.py` (29k lines), `mcp_bridge.py` (35k lines) far exceed platform limits (500 lines/file)
- **No multi-tenancy**: Missing `tenant_id`, Organization model, and tenant middleware
- **Deploy coupling**: CAD changes require full bfagent redeploy
- **Testing isolation**: CAD tests run in bfagent CI, slowing unrelated PRs

## 2. Decision

Extract `apps/cad_hub/` into a standalone repository `achimdehnert/cad-hub` following ADR-021 conventions and ADR-022 reference templates.

### 2.1 New Repository Structure

```text
cad-hub/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                # Platform reusable workflows
├── .dockerignore                    # PFLICHT (onboard Step 1.5)
├── .env.example                     # PFLICHT (onboard Step 1.4)
├── config/
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                  # Shared settings
│   │   └── production.py            # SECURE_*, env-driven
│   ├── urls.py
│   ├── wsgi.py
│   ├── healthz.py                   # /livez/, /healthz/, /health/
│   └── views.py                     # Landing page view
├── apps/
│   ├── core/                        # Organization, LLM client, tenant middleware
│   │   ├── models.py                # Organization, Membership
│   │   ├── middleware.py             # SubdomainTenantMiddleware
│   │   └── services/
│   │       ├── llm_client.py        # Extracted from bfagent
│   │       └── mcp_bridge/          # Split into modules (≤500 lines each)
│   │           ├── __init__.py
│   │           ├── ifc_bridge.py
│   │           ├── dxf_bridge.py
│   │           └── batch_bridge.py
│   ├── ifc/                         # IFC models, views, services
│   │   ├── models.py                # IFCProject, IFCModel, Floor, Room, etc.
│   │   ├── views.py                 # Project/Model CRUD (≤500 lines)
│   │   ├── views_analysis.py        # Analysis views (≤500 lines)
│   │   └── services/
│   │       ├── ifc_parser.py
│   │       └── ifc_x83_converter.py
│   ├── dxf/                         # DXF/DWG parser, renderer, NL2DXF
│   │   ├── views.py
│   │   ├── views_nl2cad.py
│   │   └── services/
│   │       ├── dxf_parser.py
│   │       ├── dxf_renderer.py
│   │       ├── dwg_converter.py
│   │       ├── nl2dxf.py
│   │       └── analyzer/            # Split from 54k-line dxf_analyzer.py
│   │           ├── __init__.py
│   │           ├── geometry.py
│   │           ├── layers.py
│   │           └── entities.py
│   ├── areas/                       # DIN 277, WoFlV calculators
│   │   ├── views.py
│   │   └── services/
│   │       ├── din277_calculator.py
│   │       └── woflv_calculator.py
│   ├── brandschutz/                 # Fire safety models, views
│   │   ├── models.py
│   │   ├── views.py
│   │   └── services/
│   ├── avb/                         # Tendering (AVB) models, views
│   │   ├── models.py                # From models_avb.py
│   │   ├── views.py
│   │   └── services/
│   │       └── avb_service.py
│   └── export/                      # Excel, GAEB export services
│       ├── views.py
│       └── services/
│           ├── export_service.py
│           └── gaeb_generator.py
├── templates/
│   └── cad_hub/
│       ├── base.html                # Extends nothing, standalone LP design
│       ├── landing.html             # Public landing page
│       └── login.html               # Custom login page
├── docker/
│   └── app/
│       ├── Dockerfile               # ADR-022 reference template
│       └── entrypoint.sh            # PFLICHT (onboard Step 3.2)
├── docker-compose.prod.yml
├── manage.py
├── pyproject.toml
└── README.md
```

### 2.2 Deployment Parameters (per ADR-021)

| Parameter | Value |
| --- | --- |
| Repository | `achimdehnert/cad-hub` |
| Server path | `/opt/cad-hub` |
| Dockerfile | `docker/app/Dockerfile` (ADR-022 reference) |
| Entrypoint | `docker/app/entrypoint.sh` (ADR-022 reference) |
| Compose file | `docker-compose.prod.yml` |
| GHCR image | `ghcr.io/achimdehnert/cad-hub:latest` + `:sha-<7char>` |
| Container (web) | `cad_hub_web` |
| Container (worker) | `cad_hub_worker` |
| Internal port | **8094** → 8000 |
| Health endpoints | `/livez/`, `/healthz/`, `/health/` |
| Domain | **nl2cad.de** + **www.nl2cad.de** (DNS already → 88.198.191.108) |
| Database | Own stack: `cad_hub_db` (postgres:16-alpine) |
| Task queue | Celery (per onboard standard entrypoint) |
| CI/CD | `ci-cd.yml` with platform reusable workflows |
| Settings | Split: `config/settings/base.py` + `production.py` |

### 2.3 Migration Strategy

**Phase 1: Scaffold + Code**

1. Create `achimdehnert/cad-hub` repo
2. Set up Django project structure with split settings
3. Copy code from `bfagent/apps/cad_hub/` into new app structure
4. Replace `from apps.bfagent.services.llm_client` with `apps.core.services.llm_client`
5. Create Organization model, Membership, tenant middleware in `apps/core/`
6. Add `tenant_id` to ALL user-data models (see Section 2.6)
7. Split oversized files — each target file ≤500 lines (see Section 2.5)
8. Extract business logic from views into `services.py` per app
9. Create public landing page + custom login page for nl2cad.de

**Phase 2: Deploy**

10. Create Dockerfile + entrypoint.sh (from ADR-022 reference templates)
11. Create docker-compose.prod.yml, .env.example, .dockerignore
12. Server provisioning: `/opt/cad-hub`, `.env.prod`, Nginx, SSL
13. CI/CD workflow (`ci-cd.yml` with platform reusable workflows)
14. Build, push, deploy, health check

**Phase 2.5: Platform Integration**

15. Register in MCP orchestrator (`orchestrator_mcp/local_tools.py` + `server.py`)
16. Update `deploy.md` workflow table
17. Update `backup.md` workflow table
18. Create deployment memory with container names, credentials, URLs

**Phase 3: Cleanup**

19. Remove `apps/cad_hub/` from bfagent repo
20. Remove `models_avb.py`, `models_ifc_legacy.py` from bfagent
21. Update bfagent INSTALLED_APPS, urls.py, requirements
22. Rebuild and deploy bfagent (slimmer image)
23. Verify bfagent health after removal

### 2.4 External Dependencies to Resolve

| Dependency | Source | Resolution |
| --- | --- | --- |
| `apps.bfagent.services.llm_client.generate_text` | bfagent LLM wrapper | Copy into `apps/core/services/llm_client.py` (already has OpenAI fallback) |
| `apps.cad_hub.models_avb` → `..models_avb` | Parent-relative import | Move `models_avb.py` into `apps/avb/models.py` |
| `apps.cad_hub.models_ifc_legacy` | Legacy IFC models | Move into `apps/ifc/models_legacy.py` |

### 2.5 File Split Plan (≤500 lines per file)

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

**ALL user-data models** get `tenant_id`:
- `IFCProject`, `IFCModel`, `Floor`, `Room`, `Window`, `Door`, `Wall`, `Slab`
- `ConstructionProject`, `Tender`, `Bid`, `Bidder`, `Award`
- `BrandschutzPruefung`, `BrandschutzSymbol`, `BrandschutzMangel`
- `DesignProfile`, `TemplateCollection`, `ResearchCache`

**All queries** MUST filter by `tenant_id`. Use `TenantAwareManager`.

## 3. Consequences

### Positive

- **Independent deployment**: CAD changes don't affect bfagent
- **Smaller images**: bfagent drops ~200MB of CAD dependencies
- **Code quality**: Enforced 500-line limit, proper app/service separation
- **Multi-tenancy**: Organization model, middleware, queryset filtering — SaaS-ready
- **CI isolation**: Faster CI for both repos
- **Own domain**: nl2cad.de with proper landing page

### Negative

- **One-time migration effort**: ~6-8 hours for full extraction + refactoring
- **Template duplication**: base.html needs own copy (standard per ADR-022)
- **LLM client copy**: Minor code duplication until shared package extracted

### Risks

- **Database migration**: New DB means no data migration (acceptable — no production data yet)
- **URL changes**: `/cad-hub/` routes move to nl2cad.de
- **bfagent cleanup**: Must remove cad_hub app cleanly to avoid import errors
- **File split complexity**: 500-line target may require significant refactoring of tightly coupled code

## 4. Alternatives Considered

### 4.1 Keep in bfagent, refactor only

- Pros: No repo overhead
- Cons: Violates SRP, still coupled deploys, monolith image
- **Rejected**: Domain mismatch is fundamental

### 4.2 Extract as Python package (library)

- Pros: Shared via pip
- Cons: Still needs Django project wrapper for deployment; over-engineering
- **Rejected**: Direct repo extraction is simpler

## 5. Verification Checklist (onboard-repo Step 7)

```text
Repo-Struktur:
  [ ] docker/app/Dockerfile existiert (ADR-022 reference)
  [ ] docker/app/entrypoint.sh existiert (chmod +x)
  [ ] docker-compose.prod.yml existiert
  [ ] .github/workflows/ci-cd.yml (reusable workflows)
  [ ] .env.example existiert
  [ ] .dockerignore existiert
  [ ] /livez/, /healthz/, /health/ Endpoints existieren
  [ ] pyproject.toml mit korrekten Metadaten
  [ ] README.md mit Quickstart
  [ ] Landing page + Login page

Server:
  [ ] /opt/cad-hub/ Verzeichnis existiert
  [ ] .env.prod mit echten Werten
  [ ] docker-compose.prod.yml kopiert
  [ ] Container starten und sind healthy

Netzwerk:
  [ ] DNS A-Record nl2cad.de → 88.198.191.108 (bereits ✅)
  [ ] DNS A-Record www.nl2cad.de → 88.198.191.108 (bereits ✅)
  [ ] Nginx Config deployed (nl2cad.de.conf)
  [ ] SSL-Zertifikat aktiv (Let's Encrypt)
  [ ] HTTPS-Redirect funktioniert
  [ ] https://nl2cad.de/livez/ gibt "ok"

CI/CD:
  [ ] GitHub Secrets gesetzt (DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY)
  [ ] Push auf main triggert CI
  [ ] CI baut Docker Image → GHCR
  [ ] CD deployt auf Server

Platform:
  [ ] MCP Orchestrator registriert (local_tools.py + server.py)
  [ ] deploy.md Tabelle aktualisiert
  [ ] backup.md Tabelle aktualisiert
  [ ] Memory mit Container-/Deploy-Infos erstellt
  [ ] Port Map in onboard-repo.md aktualisiert (8094)
```

## 6. References

- ADR-021: Unified Deployment Pattern
- ADR-022: Platform Consistency Standard (reference templates in `input/`)
- ADR-029-REVIEW.md: Detailed review findings
- `bfagent/apps/cad_hub/CAD_HUB_STATUS.md`: Current feature inventory
- `platform/.windsurf/workflows/onboard-repo.md`: Onboarding checklist
