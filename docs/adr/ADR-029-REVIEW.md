# ADR-029 Review: CAD Hub Extraction from bfagent

**Reviewer**: Cascade (AI Pair Programmer)
**Date**: 2026-02-12
**Reviewed against**: ADR-021, ADR-022, onboard-repo.md, Global Development Rules

---

## Verdict: **REVISE** — 7 Critical, 5 Important, 4 Minor Issues

---

## CRITICAL Issues (Must Fix Before Accept)

### C-1: Wrong Port — 8030 does not exist in Port Map

ADR says `Internal port: 8030 → 8000`. The onboard-repo Port Map has no 8030:

| Port | App |
|------|-----|
| 8080 | governance |
| 8081 | weltenhub |
| 8088 | trading-hub |
| 8089 | travel-beat |
| 8090 | risk-hub |
| 8091 | bfagent |
| 8092 | pptx-hub |
| 8093 | wedding-hub |

**Fix**: Use `8094` (next free) and update the Port Map in `onboard-repo.md`.

### C-2: Wrong Domain — nl2cad.de already configured, not cad-hub.iil.pet

ADR says `Domain: cad-hub.iil.pet (initial, TBD)`. DNS screenshot shows:
- `nl2cad.de` A-Record → `88.198.191.108` (already live!)
- `www.nl2cad.de` A-Record → `88.198.191.108`

**Fix**: Domain = `nl2cad.de`. Remove "TBD". Add `www.nl2cad.de`.

### C-3: Missing entrypoint.sh — MANDATORY per onboard-repo.md

ADR repo structure shows no `docker/app/entrypoint.sh`. Per onboard-repo Step 3.2, this is **PFLICHT** — handles DB wait, migrations, superuser auto-creation, web/worker/beat dispatch.

**Fix**: Add `docker/app/entrypoint.sh` to repo structure tree.

### C-4: Missing .env.example and .dockerignore — MANDATORY

Per onboard-repo Steps 1.4 and 1.5:
- `.env.example` is **PFLICHT** (template for `.env.prod`)
- `.dockerignore` is **PFLICHT** (prevents .git/, .env.prod in build context)

Neither appears in ADR-029 repo structure.

**Fix**: Add both to repo structure tree.

### C-5: Missing Platform Integration Steps (onboard-repo Step 6)

ADR-029 has **zero mention** of:
1. MCP-Orchestrator registration (`orchestrator_mcp/local_tools.py` + `server.py`)
2. Deploy workflow update (`.windsurf/workflows/deploy.md` table)
3. Backup workflow update (`.windsurf/workflows/backup.md` table)
4. ADR scope registration
5. SSH/Deployment Memory creation

These are required by onboard-repo Step 6 and ensure the platform tools can manage the new app.

**Fix**: Add Phase 2.5 or Phase 3 substep for platform integration.

### C-6: CI/CD Workflow uses wrong pattern

ADR says `cd-production.yml`. Onboard standard is `ci-cd.yml` using **platform reusable workflows** (`_ci-python.yml`, `_build-docker.yml`, `_deploy-hetzner.yml`).

**Fix**: Specify `ci-cd.yml` with reusable workflows. Don't create standalone pipeline.

### C-7: Multi-Tenancy is incomplete

ADR says "add `tenant_id`" but Global Development Rules require:
- `tenant_id = UUIDField(db_index=True)` on every user-data model ✓
- **Organization model** with `id != tenant_id` — not mentioned
- **Tenant middleware** sets `request.tenant_id` from subdomain — not mentioned
- **All queries MUST filter by `tenant_id`** — not mentioned
- Missing models: `Floor`, `Room`, `Window`, `Door`, `Wall`, `Slab` also need tenant isolation

**Fix**: Specify Organization model, middleware, and queryset filtering. List ALL affected models (not just 5).

---

## IMPORTANT Issues (Should Fix)

### I-1: Missing Verification Checklist (onboard-repo Step 7)

ADR has no verification checklist. Onboard-repo requires a complete checklist covering:
repo structure, server provisioning, network (DNS/Nginx/SSL), CI/CD, platform integration.

**Fix**: Add verification checklist from onboard-repo Step 7 template.

### I-2: File Split Plan doesn't enforce 500-line limit

The split plan moves files between apps but doesn't specify target sizes. For example:
- `views.py` (29k) → `apps/ifc/views.py` — how big will this be? Still oversized?
- `mcp_bridge.py` (35k) → single file? Still oversized.
- `dxf_analyzer.py` (54k) → single file? Definitely oversized.

Global Rules: "Maximum file length: 500 lines".

**Fix**: Each target file must be ≤500 lines. Add explicit sub-split targets for the 3 largest files.

### I-3: Service Layer Pattern not specified

Global Rules require `views.py → services.py → models.py`. The current cad_hub has business logic in views (29k lines). The split plan moves views between apps but doesn't mention creating service layers.

**Fix**: Each app must have `services.py` with business logic extracted from views.

### I-4: No Landing Page mentioned

All deployed apps have a public landing page (DriftTales, Weltenforger, Prezimo). ADR-029 doesn't mention creating one for nl2cad.de.

**Fix**: Add landing page to Phase 2 (before deploy).

### I-5: Worker type unclear — Django Q2 or Celery?

bfagent uses Django Q2. The onboard entrypoint template uses Celery. ADR-029 doesn't specify which task queue system cad-hub will use.

**Fix**: Explicitly state Celery (per onboard standard) or Django Q2 (if preferred).

---

## MINOR Issues (Nice to Fix)

### M-1: GHCR Image naming inconsistency

ADR says `ghcr.io/achimdehnert/cad-hub:latest`. ADR-021 says flat naming. But existing pptx-hub uses `ghcr.io/achimdehnert/pptx-hub/pptx-hub-web:latest` (nested). Pick one pattern and be consistent.

**Recommendation**: Use flat `ghcr.io/achimdehnert/cad-hub:latest` per ADR-021.

### M-2: Settings pattern recommendation

ADR says `config/settings.py` (single file). Onboard-repo recommends split settings (`config/settings/base.py` + `production.py`). Both are acceptable, but split is recommended for new projects.

**Recommendation**: Use split settings for a new greenfield project.

### M-3: Health endpoint `/health/` backwards-compat missing

Onboard-repo specifies 3 endpoints: `/livez/`, `/healthz/`, `/health/` (compat). ADR-029 only mentions `/livez/` and `/healthz/`.

**Fix**: Add `/health/` to health endpoints list.

### M-4: No mention of reference templates

ADR-022 v3 defines 4 canonical reference templates in `platform/docs/adr/input/`:
- `input/Dockerfile`
- `input/docker-compose.prod.yml`
- `input/entrypoint.sh`
- `input/healthz.py`

ADR-029 should state "Use ADR-022 reference templates as basis".

---

## Positive Aspects

- **Problem statement is clear** — domain mismatch between bfagent and CAD is well articulated
- **3-phase approach** (scaffold → deploy → cleanup) is pragmatic
- **External dependency analysis** is thorough — only 3 dependencies to resolve
- **Alternatives considered** section is well-reasoned
- **Consequences section** covers positive, negative, and risks

---

## Recommended ADR-029 Updates

```
Section 2.1 (Repo Structure):
  + docker/app/entrypoint.sh
  + .env.example
  + .dockerignore
  + .github/workflows/ci-cd.yml (not cd-production.yml)

Section 2.2 (Deployment Parameters):
  Domain: nl2cad.de (+ www.nl2cad.de)
  Port: 8094 → 8000
  CI/CD: ci-cd.yml with platform reusable workflows
  Health: /livez/, /healthz/, /health/

Section 2.3 (Migration Strategy):
  Phase 1: Add service layer creation to each app
  Phase 2: Add landing page, entrypoint.sh, .env.example
  Phase 2.5 (NEW): Platform integration (MCP, deploy/backup workflows)
  Phase 3: Add onboard-repo Step 7 verification checklist

Section 2.5 (File Split):
  Add target sizes (≤500 lines each)
  Add sub-splits for mcp_bridge.py and dxf_analyzer.py

Section 2.6 (Multi-Tenancy):
  Add Organization model
  Add tenant middleware
  List ALL affected models (not just 5)
  Specify queryset filtering requirement
```
