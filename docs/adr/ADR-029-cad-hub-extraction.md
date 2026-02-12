# ADR-029: CAD Hub Extraction from bfagent

**Status**: Proposed
**Date**: 2026-02-12
**Author**: Achim Dehnert
**Scope**: bfagent, cad-hub (new repo), platform
**Follows**: ADR-021 (Unified Deployment Pattern), ADR-022 (Platform Consistency)

---

## 1. Problem Statement

`apps/cad_hub/` is a full-featured Django application embedded inside the `bfagent` repository. It has grown to ~50 files and ~500k lines of code covering IFC parsing, DXF/DWG analysis, DIN 277 calculations, fire safety (Brandschutz), tendering (AVB), and natural-language-to-CAD generation.

**Problems with current embedding:**

- **Violation of single-responsibility**: bfagent is a book factory agent; cad-hub is a construction/CAD platform — zero domain overlap
- **Monolith scaling**: bfagent Docker image includes all CAD dependencies (ezdxf, ifcopenshell, openpyxl) even when only book features are used
- **Code quality**: `views.py` (29k lines), `mcp_bridge.py` (35k lines) far exceed platform limits (500 lines/file)
- **No multi-tenancy**: Missing `tenant_id` on all models
- **Deploy coupling**: CAD changes require full bfagent redeploy
- **Testing isolation**: CAD tests run in bfagent CI, slowing unrelated PRs

## 2. Decision

Extract `apps/cad_hub/` into a standalone repository `achimdehnert/cad-hub` following ADR-021 conventions.

### 2.1 New Repository Structure

```
cad-hub/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── healthz.py
├── apps/
│   ├── core/             # Shared: base models, LLM client, tenant middleware
│   ├── ifc/              # IFC models, views, services (from models/ifc.py)
│   ├── dxf/              # DXF/DWG parser, renderer, NL2DXF
│   ├── areas/            # DIN 277, WoFlV calculators
│   ├── brandschutz/      # Fire safety models, views
│   ├── avb/              # Tendering (AVB) models, views
│   └── export/           # Excel, GAEB export services
├── docker/
│   └── app/Dockerfile
├── docker-compose.prod.yml
├── manage.py
├── pyproject.toml
└── README.md
```

### 2.2 Deployment Parameters (per ADR-021)

| Parameter | Value |
|-----------|-------|
| Repository | `achimdehnert/cad-hub` |
| Server path | `/opt/cad-hub` |
| Dockerfile | `docker/app/Dockerfile` |
| Compose file | `docker-compose.prod.yml` |
| GHCR image | `ghcr.io/achimdehnert/cad-hub:latest` |
| Container (web) | `cad_hub_web` |
| Container (worker) | `cad_hub_worker` |
| Internal port | 8030 → 8000 |
| Health endpoints | `/livez/`, `/healthz/` |
| Domain | `cad-hub.iil.pet` (initial, TBD) |
| Database | Own stack: `cad_hub_db` (postgres:16-alpine) |

### 2.3 Migration Strategy

**Phase 1: Scaffold + Copy** (this ADR)
1. Create `achimdehnert/cad-hub` repo
2. Set up Django project structure (config/, manage.py, pyproject.toml)
3. Copy code from `bfagent/apps/cad_hub/` into new app structure
4. Replace `from apps.bfagent.services.llm_client` with local `apps.core.llm_client`
5. Add `tenant_id` to all user-data models
6. Split oversized files (views.py → per-module views)

**Phase 2: Deploy**
7. Create Dockerfile + docker-compose.prod.yml
8. Server provisioning (directory, .env.prod, Nginx, SSL)
9. CI/CD workflow (cd-production.yml)
10. Build, push, deploy, health check

**Phase 3: Cleanup**
11. Remove `apps/cad_hub/` from bfagent repo
12. Update bfagent INSTALLED_APPS, urls.py
13. Rebuild and deploy bfagent (slimmer image)

### 2.4 External Dependencies to Resolve

| Dependency | Source | Resolution |
|------------|--------|------------|
| `apps.bfagent.services.llm_client.generate_text` | bfagent LLM wrapper | Copy into `apps/core/llm_client.py` (already has OpenAI fallback) |
| `apps.cad_hub.models_avb` → `..models_avb` | Parent-relative import from bfagent | Move `models_avb.py` into `apps/avb/models.py` |
| `apps.cad_hub.models_ifc_legacy` | Legacy IFC models | Move into `apps/ifc/models_legacy.py` |

### 2.5 File Split Plan

Current oversized files need splitting:

| Current File | Lines | Split Into |
|-------------|-------|------------|
| `views.py` | 29k | `apps/ifc/views.py`, `apps/areas/views.py`, `apps/export/views.py` |
| `views_avb.py` | 18k | `apps/avb/views.py` |
| `views_brandschutz.py` | 18k | `apps/brandschutz/views.py` |
| `views_dxf.py` | 16k | `apps/dxf/views.py` |
| `views_nl2cad.py` | 17k | `apps/dxf/views_nl2cad.py` |
| `views_analysis.py` | 19k | `apps/ifc/views_analysis.py` |
| `mcp_bridge.py` | 35k | `apps/core/services/mcp_bridge.py` (split into classes) |
| `dxf_analyzer.py` | 54k | `apps/dxf/services/analyzer.py` (split by responsibility) |

### 2.6 Multi-Tenancy Addition

All user-data models get:
```python
tenant_id = models.UUIDField(db_index=True)
```

Affected models: `IFCProject`, `IFCModel`, `ConstructionProject`, `BrandschutzPruefung`, `ResearchCache`.

## 3. Consequences

### Positive
- **Independent deployment**: CAD changes don't affect bfagent
- **Smaller images**: bfagent drops ~200MB of CAD dependencies
- **Code quality**: Enforced file size limits, proper app separation
- **Multi-tenancy**: Ready for SaaS model
- **CI isolation**: Faster CI for both repos

### Negative
- **One-time migration effort**: ~4-6 hours for full extraction
- **Template duplication**: base.html needs own copy (standard per ADR-022)
- **LLM client copy**: Minor code duplication until shared package extracted

### Risks
- **Database migration**: New DB means no data migration (acceptable — no production data yet)
- **URL changes**: `/cad-hub/` routes move to new domain
- **bfagent cleanup**: Must remove cad_hub app cleanly to avoid import errors

## 4. Alternatives Considered

### 4.1 Keep in bfagent, refactor only
- Pros: No repo overhead
- Cons: Violates SRP, still coupled deploys, monolith image
- **Rejected**: Domain mismatch is fundamental

### 4.2 Extract as Python package (library)
- Pros: Shared via pip
- Cons: Still needs Django project wrapper for deployment; over-engineering
- **Rejected**: Direct repo extraction is simpler

## 5. References

- ADR-021: Unified Deployment Pattern
- ADR-022: Platform Consistency Standard
- `bfagent/apps/cad_hub/CAD_HUB_STATUS.md`: Current feature inventory
