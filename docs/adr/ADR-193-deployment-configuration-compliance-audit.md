---
status: proposed
date: 2026-05-09
decision-makers:
  - Achim Dehnert
depends-on:
  - ADR-191 (platform-context MCP Code Compliance)
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
implementation_status: none
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
| **Status** | Proposed |
| **Datum** | 2026-05-09 |
| **Autor** | Achim Dehnert |
| **Depends On** | ADR-191, ADR-022, ADR-021, ADR-056, ADR-094 |
| **Consumers** | dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub, infra-deploy |

---

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

We implement a `check_compose` MCP tool (ADR-191) and a `check_dockerfile` check within `audit_repo` that structurally parse deployment configs against platform standards. This complements REFLEX's regex approach with YAML/Dockerfile-aware parsing.

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

### check_dockerfile Rules

| ID | Severity | Check | ADR |
|----|----------|-------|-----|
| `DF-001` | error | No `HEALTHCHECK` instruction | ADR-056 |
| `DF-002` | warning | HEALTHCHECK uses `curl` instead of `python -c "import urllib..."` | ADR-056 |
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

The `audit_repo` MCP tool accepts a `repo` parameter. For platform-wide audits:

```
# In /adr-health or /platform-audit workflow:
for repo in [dev-hub, travel-beat, bfagent, risk-hub, weltenhub, wedding-hub, coach-hub]:
    MCP: audit_repo(repo=repo)
    → Aggregates: SL-*, HX-*, DC-*, DF-* violations
    → Generates: Platform Compliance Scorecard
```

| Score | Rating |
|-------|--------|
| 0 critical, 0 error | ✅ Compliant |
| 0 critical, ≤3 error | ⚠️ Mostly Compliant |
| ≥1 critical | ❌ Non-Compliant — fix before deploy |

## Open Questions

- **OQ-1**: Should DC-007 (port binding 0.0.0.0) be error or warning? Some services (Redis for debugging) intentionally bind publicly on dev.
- **OQ-2**: Should multi-stage build (DF-005) be enforced for all repos or only production images?
- **OQ-3**: How to handle Nginx checks when configs are only on the server? SSH-based check or copy-to-repo pattern?
