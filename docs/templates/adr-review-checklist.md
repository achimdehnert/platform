# ADR Review Checklist

> Platform-specific review template for `achimdehnert` platform ADRs.
> Reconstructed from ADR-021 review (2026-02-20). Based on Zimmermann's ADR Review Checklist + MADR 4.0.
> Updated 2026-02-24: HEALTHCHECK-Konvention korrigiert, Modern Platform Patterns (ADR-062/072/075/077) ergänzt.

---

## 1. MADR 4.0 Compliance

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 1.1 | YAML frontmatter present (`status`, `date`, `decision-makers`) | ☐ | |
| 1.2 | Title is a decision statement (not a topic) | ☐ | e.g. "Adopt X for Y" not "X Architecture" |
| 1.3 | `## Context and Problem Statement` section present | ☐ | |
| 1.4 | `## Decision Drivers` section present (bullet list) | ☐ | |
| 1.5 | `## Considered Options` section lists ≥ 3 options | ☐ | |
| 1.6 | `## Decision Outcome` states chosen option with explicit reasoning | ☐ | |
| 1.7 | `## Pros and Cons of the Options` covers all considered options | ☐ | |
| 1.8 | `## Consequences` uses Good/Bad bullet format | ☐ | |
| 1.9 | `### Confirmation` subsection explains how compliance is verified | ☐ | |
| 1.10 | `## More Information` links related ADRs | ☐ | |

---

## 2. Platform Infrastructure Specifics

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 2.1 | Server IP `88.198.191.108` referenced correctly (not hardcoded elsewhere) | ☐ | |
| 2.2 | SSH access: `root` user — rationale documented if used | ☐ | ADR-021 §2.1 pattern |
| 2.3 | `StrictHostKeyChecking=no` absent — `ssh-keyscan` used instead | ☐ | Security requirement |
| 2.4 | Registry `ghcr.io/achimdehnert/` used (not Docker Hub) | ☐ | |
| 2.5 | `GITHUB_TOKEN` scope: `packages: write` declared in workflow `permissions:` | ☐ | |
| 2.6 | Secrets via `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER` (not hardcoded) | ☐ | |
| 2.7 | Deploy path follows `/opt/<repo>` convention (exception: bfagent → `/opt/bfagent-app`) | ☐ | |
| 2.8 | Health endpoints: `/livez/` (liveness) + `/healthz/` (readiness) | ☐ | |
| 2.9 | Port allocation: new port registered in ADR-021 §2.9 table | ☐ | |
| 2.10 | Nginx retained as reverse proxy (Traefik deferred — ADR-021 §2.10) | ☐ | |

---

## 3. CI/CD & Docker Conventions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 3.1 | Dockerfile at `docker/app/Dockerfile` (or deviation documented in ADR-021 §2.3) | ☐ | |
| 3.2 | `docker-compose.prod.yml` at project root (or deviation documented) | ☐ | |
| 3.3 | Non-root user in Dockerfile (`USER <appname>`) | ☐ | |
| 3.4 | `HEALTHCHECK` **nicht** im Dockerfile — ausschließlich pro-Service in `docker-compose.prod.yml` | ☐ | Coach-hub Incident: HEALTHCHECK im Dockerfile gilt für alle Container (web+worker+beat) → Restart-Loop |
| 3.5 | Multi-stage build (recommended) | ☐ | |
| 3.10 | Worker/Beat Healthcheck: `pidof python3.12` (nicht `celery inspect ping`) | ☐ | Slim-Images benennen Binary versioniert; celery inspect schlägt bei Broker-Ausfall fehl |
| 3.6 | Image tags: `latest` + `<sha7>` + semver (via `_build-docker.yml`) | ☐ | |
| 3.7 | Compose hardening: `logging`, `deploy.resources.limits.memory`, `restart: unless-stopped` | ☐ | ADR-021 §2.11 |
| 3.8 | `env_file: .env.prod` used — no `${VAR}` interpolation in compose `environment:` | ☐ | |
| 3.9 | Three-stage pipeline: `_ci-python.yml` → `_build-docker.yml` → `_deploy-hetzner.yml` | ☐ | ADR-021 §2.5 |

---

## 4. Database & Migration Safety

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 4.1 | DB migrations follow Expand-Contract pattern (no DROP/RENAME in same release) | ☐ | ADR-021 §2.16 |
| 4.2 | `python manage.py makemigrations --check` passes | ☐ | |
| 4.3 | Migration is backwards-compatible (old code works with new DB schema) | ☐ | |
| 4.4 | Multi-tenant models have `tenant_id = UUIDField(db_index=True)` | ☐ | Only for multi-tenant apps |
| 4.5 | Shared DB risk assessed (weltenhub/bfagent share `bfagent_db`) | ☐ | Only if relevant |

---

## 5. Security & Secrets

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 5.1 | No secrets hardcoded in ADR examples or code snippets | ☐ | |
| 5.2 | `.env.prod` never committed (in `.gitignore`) | ☐ | |
| 5.3 | SOPS/ADR-045 compatibility considered if new secrets introduced | ☐ | |
| 5.4 | `DEPLOY_*` secrets: org-level preferred over per-repo | ☐ | ADR-021 §2.6 |

---

## 6. Architectural Consistency

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 6.1 | Service layer pattern respected: `views.py` → `services.py` → `models.py` | ☐ | |
| 6.2 | No contradiction with existing accepted ADRs | ☐ | Check ADR INDEX |
| 6.3 | Zero Breaking Changes principle: deprecate first, remove after 2 releases | ☐ | |
| 6.4 | ADR-054 Architecture Guardian compatibility (agent can verify compliance) | ☐ | |
| 6.5 | Migration tracking table present if ADR introduces a transition (§4/§5 pattern) | ☐ | ADR-021 §4 pattern |

---

## 7. Open Questions & Deferred Decisions

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 7.1 | All open questions explicitly listed with pros/cons | ☐ | |
| 7.2 | Deferred decisions reference a future ADR (not left implicit) | ☐ | |
| 7.3 | Conscious decisions (e.g. SSH as root, Nginx over Traefik) documented with rationale | ☐ | |

---

## 8. Modern Platform Patterns

> Nur anwenden wenn das ADR die jeweilige Domäne berührt.

| # | Check | Pass | Notes |
|---|-------|------|-------|
| 8.1 | **infra-deploy (ADR-075)**: Write-Ops (migrate, backup, deploy) via GitHub Actions — nicht via MCP | ☐ | MCP-Tools dürfen nur read-only sein; deployment-mcp write-tools tragen Deprecation-Warning |
| 8.2 | **infra-deploy (ADR-075)**: MCP-Tools mit Deprecation-Warning versehen wenn Write-Op | ☐ | Response enthält `deprecated` Key mit Verweis auf infra-deploy Workflow |
| 8.3 | **Multi-Tenancy (ADR-072)**: Schema-Isolation via PostgreSQL-Schema — kein Mixen in `public` Schema | ☐ | `SET search_path TO <tenant_schema>` statt Row-Level für neue Apps |
| 8.4 | **Multi-Tenancy (ADR-072)**: `tenant_id` Index auf allen Cross-Tenant-Tabellen | ☐ | Gilt auch für `content_store.*` Tabellen |
| 8.5 | **Content Store (ADR-062)**: `SyncContentStore` nutzt `asgiref.async_to_sync` — kein `asyncio.run()` | ☐ | `asyncio.run()` in ASGI-Kontext (Daphne/Uvicorn) → Deadlock |
| 8.6 | **Content Store (ADR-062)**: `CONTENT_STORE_DSN` als Secret, nicht hardcoded | ☐ | Lazy-Init mit `ContentStoreUnavailableError`; App degradiert graceful |
| 8.7 | **Catalog (ADR-077)**: Neues Repo hat `catalog-info.yaml` im Root (Backstage-Format) | ☐ | Pflichtfelder: `metadata.name`, `spec.type`, `spec.lifecycle`, `spec.owner` |
| 8.8 | **Drift-Detector (ADR-059)**: ADR-Datei enthält `<!-- Drift-Detector-Felder -->` Kommentar | ☐ | Felder: `staleness_months`, `drift_check_paths`, `supersedes_check` |
| 8.9 | **Runner (ADR-021)**: Self-hosted Runner Labels `[self-hosted, hetzner, dev]` | ☐ | Nicht `dev-server`; Verzeichnis `/home/github-runner/runner-<repo>` |
| 8.10 | **Temporal (ADR-077 mcp-hub)**: Durable Workflows via Temporal statt in-memory WorkflowExecution | ☐ | Nur für ADRs die mcp-hub Agent Team / Workflows berühren |

---

## 9. Review Scoring

| Category | Score (1–5) | Notes |
|----------|-------------|-------|
| MADR 4.0 compliance | | |
| Platform Infrastructure Specifics | | |
| CI/CD & Docker Conventions | | |
| Database & Migration Safety | | |
| Security & Secrets | | |
| Architectural Consistency | | |
| Open Questions | | |
| Modern Platform Patterns | | |
| **Overall** | | |

**Scoring guide**: 5 = exemplary, 4 = good (minor gaps), 3 = acceptable (improvements needed), 2 = significant gaps, 1 = must rework

---

## 10. Recommendation

- [ ] **Accept** — ready to merge
- [ ] **Accept with changes** — minor fixes required (list below)
- [ ] **Reject** — fundamental issues (list below)

### Required changes (if any)

1.
2.
3.

---

*Template version: 2.0 (2026-02-24) — HEALTHCHECK-Konvention korrigiert (coach-hub Incident), Modern Platform Patterns ergänzt (ADR-059/062/072/075/077)*
