# ADR-029 Review: CAD Hub Extraction from bfagent

**Reviewer**: Cascade (AI Pair Programmer)
**Review Rounds**: 2 (initial + comprehensive)
**Date**: 2026-02-12
**Reviewed against**: ADR-021, ADR-022 (incl. `input/*` templates), onboard-repo.md, Global Development Rules, actual cad_hub source code

---

## Review Round 2 Verdict: **REVISE** — 7 New Critical, 6 New Important, 5 New Minor

Round 1 found 7C/5I/4M (all addressed in v2). Round 2 found additional issues by deep-checking ADR-022 reference templates and actual cad_hub code.

---

## NEW CRITICAL Issues (Round 2)

### C2-1: Missing `migrate` service in Compose (ADR-022 A1)

ADR-022 §3.5 + `input/docker-compose.prod.yml` require a **separate migrate service** (`restart: "no"`, `service_completed_successfully`). ADR-029 only lists `cad_hub_web` + `cad_hub_worker`. Web/worker depend on `migrate` completing.

**Fix**: Add `cad_hub_migrate` container. Use `input/docker-compose.prod.yml` as basis.

### C2-2: Missing Redis service (Celery requires broker)

ADR-029 says "Task queue: Celery" but lists no Redis container. `input/docker-compose.prod.yml` includes Redis. Without it, Celery cannot start.

**Fix**: Add `cad_hub_redis` (redis:7-alpine) to deployment parameters.

### C2-3: healthz.py in wrong location

ADR-029 puts health endpoints in `config/healthz.py`. ADR-022 §3.3 + §3.7 specifies `apps/core/healthz.py`. The import path `from apps.core.healthz import HEALTH_PATHS` is used in SubdomainTenantMiddleware.

**Fix**: Move to `apps/core/healthz.py`. Must include `HEALTH_PATHS = frozenset(...)`, `@csrf_exempt`, `@require_GET`.

### C2-4: tasks.py uses plain functions, not Celery tasks

Current `tasks.py` has `def process_ifc_upload(model_id)` — a plain function, no `@shared_task`. ADR says Celery but doesn't address this conversion. Also missing `config/celery.py`.

**Fix**: Add `config/celery.py` to repo structure. Note tasks.py → `@shared_task` conversion in migration plan.

### C2-5: 15 handlers not mapped to target apps

`handlers/` directory has 15 files (area_classifier, brandschutz, nl_query, pdf_vision, pdf_lageplan, pdf_abstandsflaechen, massen, cad_file_input, nl_learning, room_analysis, use_case_tracker, base, brandschutz_report, brandschutz_symbols). ADR-029 repo structure doesn't show where these go.

**Fix**: Map each handler to its target app (e.g., `handlers/brandschutz*.py` → `apps/brandschutz/handlers/`).

### C2-6: `ifc_complete_parser/` submodule not addressed

4-file submodule with 705-line `models.py` (dataclasses, not Django models). Not mentioned in ADR-029. Contains core IFC parsing logic with ifcopenshell dependency.

**Fix**: Map to `apps/ifc/parser/` or `apps/ifc/services/complete_parser/`.

### C2-7: Entrypoint pattern conflict — ADR-022 vs onboard-repo

ADR-022 `input/entrypoint.sh`: `#!/bin/bash` + `set -euo pipefail` + NO migrations (separate service).
onboard-repo entrypoint: `#!/bin/sh` + `set -e` + migrations IN entrypoint.

ADR-029 must pick one. Since ADR-022 is the canonical reference, use `input/entrypoint.sh`.

**Fix**: Specify `input/entrypoint.sh` pattern (bash, strict, no inline migrations).

---

## NEW IMPORTANT Issues (Round 2)

### I2-1: 48 templates not accounted for

Current cad_hub has 48+ HTML templates in 6 subdirectories (analysis/, avb/, brandschutz/, dxf/, nl2cad/, partials/). ADR-029 template section only shows 3 files (base.html, landing.html, login.html).

**Fix**: Show template distribution per app in repo structure or migration plan.

### I2-2: 3 admin files not mapped

`admin.py`, `admin_avb.py`, `admin_brandschutz.py` must be split into per-app admin modules. Not mentioned in file split plan.

**Fix**: Add admin file mapping (admin.py → apps/ifc/admin.py, admin_avb.py → apps/avb/admin.py, etc.)

### I2-3: tenant_id model list incomplete + incorrect

ADR lists `DesignProfile`, `TemplateCollection`, `ResearchCache` — these don't exist in `models/__init__.py`. Missing actual AVB sub-models: `ProjectMilestone`, `CostEstimate`, `CostGroup`, `ProjectPhase`, `TenderPosition`, `TenderGroup`, `BidPosition`. Also: `BrandschutzKategorie`, `Feuerwiderstandsklasse` etc. are TextChoices, NOT models — they don't need tenant_id.

**Fix**: List only actual Django Model classes that store user data. Verify against `models/__init__.py`.

### I2-4: Missing `requirements.txt`

ADR shows `pyproject.toml` but no `requirements.txt`. Dockerfile template (`input/Dockerfile`) uses `COPY requirements.txt` + `pip install -r requirements.txt`. Either provide requirements.txt or adapt Dockerfile.

**Fix**: Add `requirements.txt` to repo structure (Dockerfile depends on it).

### I2-5: Missing `shm_size: 128m` for postgres

ADR-021 §2.10 requires `shm_size: 128m` for postgres to prevent "could not resize shared memory" errors.

**Fix**: Add to compose DB service definition.

### I2-6: DJANGO_SETTINGS_MODULE not specified

Split settings require explicit module path. Production: `config.settings.production`. CI: `config.settings.base` or `config.settings.test`. Not specified anywhere in ADR.

**Fix**: Add to deployment parameters table and CI/CD config.

---

## NEW MINOR Issues (Round 2)

### M2-1: Network naming missing

ADR-022 requires named network. Should be `cad_hub_network` (bridge).

### M2-2: Volume naming missing

ADR-022 requires `${APP_NAME}_pgdata`, `${APP_NAME}_redis_data`.

### M2-3: Compose service naming not specified

Services: `cad-hub-web`, `cad-hub-worker`, `cad-hub-db` (hyphens). Containers: `cad_hub_web` etc. (underscores). Per ADR-021 §2.2.

### M2-4: No www redirect strategy

Both `nl2cad.de` and `www.nl2cad.de` have DNS records. Nginx should redirect `www` → non-www (or vice versa). Not specified.

### M2-5: Port registry update needed in BOTH ADR-021 AND onboard-repo

Port 8094 must be added to ADR-021 §2.9 AND onboard-repo Port Map. Currently only onboard mentioned.

---

## Round 1 Issues Status (all fixed in v2)

All 7C + 5I + 4M from Round 1 were addressed:
- C-1 Port 8030→8094 ✅ | C-2 Domain nl2cad.de ✅ | C-3 entrypoint.sh ✅
- C-4 .env.example/.dockerignore ✅ | C-5 Platform integration ✅
- C-6 ci-cd.yml ✅ | C-7 Multi-tenancy expanded ✅
- I-1 through I-5 ✅ | M-1 through M-4 ✅
