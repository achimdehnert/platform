---
status: accepted
decision_date: 2026-05-09
amended: 2026-05-10
deciders:
  - Achim Dehnert
reviewed_by:
  - Cascade (ADR-Review, 2026-05-10)
  - Claude (Sparring Review on ADR-191, 2026-05-09)
depends_on:
  - ADR-191 (iil-codeguard Library-First Tooling)
  - ADR-022 (BigAutoField Platform Standard)
  - ADR-021 (Unified Deployment Pipeline)
  - ADR-056 (Deployment Pre-Flight Validation)
  - ADR-094 (Migration Conflict Resolution)
repo: platform
consumers:
  - dev-hub
  - travel-beat
  - bfagent
  - risk-hub
  - weltenhub
  - wedding-hub
  - coach-hub
  - infra-deploy
domains:
  - deployment
  - docker
  - nginx
  - security
implementation_status: verified
staleness_months: 6
last_reviewed: 2026-05-09
drift_check_paths:
  - "*/docker-compose.prod.yml"
  - "*/Dockerfile"
  - "*/docker/app/Dockerfile"
---

# ADR-193: Automated Deployment Configuration Compliance Audit

| Metadaten | |
|-----------|---|
| **Status** | Accepted (v1.1, amended 2026-05-10) — Implementation verified |
| **Datum** | 2026-05-09 (v1.0), 2026-05-10 (v1.1) |
| **Autor** | Achim Dehnert |
| **Reviewer** | Cascade (Self-Review), Claude (Sparring auf ADR-191) |
| **Depends On** | ADR-191, ADR-022, ADR-021, ADR-056, ADR-094 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub, infra-deploy |

---

## v1.0 → v1.1 — Änderungen

| Aspekt | v1.0 | v1.1 |
|--------|------|------|
| **DF-001 HEALTHCHECK** | "error if missing in Dockerfile" | **Invertiert**: "error if HEALTHCHECK present in Dockerfile" — gehört in compose (Coach-hub Incident, ADR-021 §2.4) |
| **Architektur** | Teil von platform-context MCP | **Modul in `iil-codeguard`** (ADR-191 v1.1 Library-First) |
| **Worker/Beat HEALTHCHECK** | nicht erfasst | **DC-009**: `pidof python3.12` als Worker/Beat-Healthcheck (ADR-021 §3.10) |
| **Glossar** | fehlte | ergänzt |

## Context

The platform operates 19 repositories, each with its own `docker-compose.prod.yml`, `Dockerfile`, and Nginx configuration. ADR-022 and ADR-056 define clear standards:

| Standard | Source ADR | Current Enforcement |
|----------|-----------|-------------------|
| `env_file: .env.prod` (not `environment: ${VAR}`) | ADR-022 | REFLEX regex rule |
| HEALTHCHECK in Dockerfile | ADR-056 | REFLEX regex rule |
| Multi-stage Dockerfile build | ADR-056 | Manual PR review |
| Non-root user (`app:1000`) | ADR-056 | Manual PR review |
| OCI labels in Dockerfile | ADR-056 | Not checked |
| Memory limits in compose | ADR-021 | Not checked |
| Image tag from `ghcr.io/achimdehnert/` | ADR-021 | Manual PR review |
| HEALTHCHECK via python urllib (not curl) | ADR-056 | Not checked |
| Nginx: IPv6, SSL, security headers | ADR-060 | `/nginx-check` workflow (manual trigger) |

REFLEX catches 2 of 9 standards. The `/compose-audit` and `/nginx-check` workflows exist but require manual triggering. In Feb 2026, a production incident occurred because a compose file used `environment: DATABASE_URL=${DATABASE_URL}` instead of `env_file` — the variable was empty on the server, causing a silent connection to the wrong database.

## Decision

We implement `compose_security` and `dockerfile_audit` checker modules in the `iil-codeguard` package (per ADR-191 v1.1) that structurally parse deployment configs against platform standards. This complements REFLEX's regex approach with YAML/Dockerfile-aware parsing.

### check_compose Rules

| ID | Severity | Check | ADR |
|----|----------|-------|-----|
| `DC-001` | critical | `environment:` block contains `${VAR}` interpolation → must use `env_file` | ADR-022 |
| `DC-002` | error | Missing `env_file: .env.prod` on web service | ADR-022 |
| `DC-003` | error | Missing HEALTHCHECK-equivalent (`healthcheck:` key) in compose | ADR-056 |
| `DC-004` | warning | Missing `mem_limit` or `deploy.resources.limits.memory` | ADR-021 |
| `DC-005` | warning | Image not from `ghcr.io/achimdehnert/` registry | ADR-021 |
| `DC-006` | error | Missing `restart: unless-stopped` | ADR-021 |
| `DC-007` | info | Port binding on `0.0.0.0` instead of `127.0.0.1` | Security |
| `DC-008` | warning | Missing separate `migrate` service | ADR-094 |
| `DC-009` | error | Worker/Beat service uses `celery inspect ping` instead of `pidof python3.12` (Slim-Image Issue) | ADR-021 §3.10 |

### check_dockerfile Rules

| ID | Severity | Check | ADR |
|----|----------|-------|-----|
| `DF-001` | error | **HEALTHCHECK present in Dockerfile** — muss in compose pro Service (sonst: Restart-Loop bei Worker/Beat, Coach-hub Incident) | ADR-021 §2.4 |
| `DF-002` | warning | (reserviert — ehemals "HEALTHCHECK uses curl"; verschoben zu DC-003 da HEALTHCHECK in compose lebt) | n/a |
| `DF-003` | warning | No `USER` instruction (runs as root) | ADR-056 |
| `DF-004` | info | Missing OCI labels (`LABEL org.opencontainers.*`) | ADR-056 |
| `DF-005` | error | Single-stage build (no `FROM ... AS builder`) | ADR-056 |
| `DF-006` | critical | Contains `StrictHostKeyChecking=no` | Security |
| `DF-007` | critical | Contains hardcoded IP `88.198.191.108` | Security |
| `DF-008` | critical | Contains hardcoded secret (`SECRET_KEY=`, `password=`) | Security |
| `DF-009` | warning | Base image not `python:3.12-slim` | Platform Standard |

### check_nginx Rules (optional, server-side)

| ID | Severity | Check |
|----|----------|-------|
| `NX-001` | error | Missing `listen [::]:443 ssl` (IPv6) |
| `NX-002` | error | Missing `ssl_certificate` directives |
| `NX-003` | warning | Missing `X-Frame-Options` header |
| `NX-004` | warning | Missing `X-Content-Type-Options` header |
| `NX-005` | info | Missing `proxy_set_header X-Request-ID` |

## Consequences

### Positive
- Catches deployment config drift before it reaches production
- Structural YAML parsing eliminates false positives from regex matching
- All rules reference specific ADRs — traceable governance
- Composable with `audit_repo` for full-stack compliance reports
- Shared rule IDs (`DC-001`, `DF-001`) for consistent communication

### Negative
- Compose file format varies (v2 vs v3.x) — parser must handle both
- Nginx configs are on the server, not in repos — requires SSH access or separate check
- Some rules (DC-007 port binding) may have legitimate exceptions (e.g., public-facing services)
- Adds maintenance burden for rule updates when ADR standards change

## Alternatives Considered

1. **Extend REFLEX with YAML-aware parsing** — REFLEX is intentionally regex-based for speed. Adding YAML parsing changes its architecture.
2. **hadolint for Dockerfiles** — Good but opinionated about general Docker best practices, not our platform-specific rules (env_file pattern, python urllib HEALTHCHECK).
3. **docker-compose config --quiet** — Only validates syntax, not platform-specific standards.
4. **OPA/Rego policies** — Powerful but adds a policy engine dependency. Overkill for 9 rules.

## Multi-Repo Audit Mode

The `codeguard_audit` MCP tool (per ADR-191 v1.1) accepts a `repo` parameter. For platform-wide audits:

```
# In /adr-health or /platform-audit workflow:
for repo in [dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub]:
    MCP: codeguard_audit(repo=repo, summary_only=True)
    → Aggregates: SL-*, HX-*, DC-*, DF-* violations
    → Generates: Platform Compliance Scorecard (SARIF)
```

| Score | Rating |
|-------|--------|
| 0 critical, 0 error | ✅ Compliant |
| 0 critical, ≤3 error | ⚠️ Mostly Compliant |
| ≥1 critical | ❌ Non-Compliant — fix before deploy |

## Open Questions

- **OQ-1**: Should DC-007 (port binding 0.0.0.0) be error or warning? Some services (Redis for debugging) intentionally bind publicly on dev.
- **OQ-2**: Should multi-stage build (DF-005) be enforced for all repos or only production images?
- **OQ-3**: How to handle Nginx checks when configs are only on the server? SSH-based check or copy-to-repo pattern? → Vorschlag für ADR-194: "Nginx Compliance Strategy".

## Glossar

- **HEALTHCHECK** — Docker/Compose-Mechanismus zum Prüfen ob Container gesund ist; gehört **per Service in compose**, nicht ins Dockerfile (gilt sonst für alle Container)
- **OCI** — Open Container Initiative, Standard für Container-Images und Labels
- **OPA/Rego** — Open Policy Agent / Rego, deklarative Policy-Engine (verworfen als zu schwer)
- **REFLEX** — Internes regex-basiertes Compliance-Tool der Platform, scannt 19 Repos
- **SARIF** — Static Analysis Results Interchange Format (OASIS-Standard für Linter-Output)
- **GHA** — GitHub Actions
- **CSRF** — Cross-Site Request Forgery (Django-Schutz via `{% csrf_token %}`)
