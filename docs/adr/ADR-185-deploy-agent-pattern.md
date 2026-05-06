---
status: proposed
date: 2026-05-06
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: [ADR-021, ADR-022, ADR-056, ADR-066, ADR-094, ADR-120, ADR-174]
implementation_status: partial
implementation_evidence:
  - "risk-hub: .github/workflows/complete-check.yml (Phase A)"
tags: [deployment, agent, automation, ci-cd]
---

# ADR-185: Adopt Gate-controlled Deploy-Agent for automated Staging→Prod deployments

## Context and Problem Statement

Deployments aller IIL-Platform-Repos folgen einem wiederkehrenden, deterministischen Ablauf:

1. Pre-flight Checks (Migration-Konflikte, Tests, Banned Patterns)
2. Build & Push (Docker Image → GHCR)
3. Staging-Deploy (Pull + Compose Up + Health-Check)
4. Staging-Verification (HTTP 200, JS-Errors, Smoke-Test)
5. Prod-Deploy (nach Approval)
6. Prod-Verification (Health-Check, Rollback bei Failure)

Dieser Ablauf ist heute teils manuell über IDE-Workflows (`/ship`, `/ship-staging`) und teils
automatisiert über `_deploy-unified.yml` (ADR-120) gesteuert.

### Problem

- **Staging wird übersprungen** — `deploy.yml` erlaubt `target_environment: production` direkt
- **Kein Pre-flight vor Deploy** — Migration-Konflikte und Banned Patterns werden erst im CI geprüft, nicht im Deploy-Flow
- **Kein automatisches Rollback** — bei Health-Check-Failure bleibt die fehlerhafte Version live
- **Kein einheitlicher Audit-Trail** — Deploys werden nicht in pgvector Memory protokolliert
- **IDE-Workflows und CI/CD sind entkoppelt** — `/ship` in der IDE und `deploy.yml` in GitHub Actions haben unterschiedliche Logik

### Decision Drivers

- Staging-Skip-Rate auf 0% senken (aktuell geschätzt >50%)
- Automatischer Rollback bei Prod-Health-Check-Failure
- Einheitlicher Audit-Trail (pgvector + Outline + Discord)
- Kompatibilität mit existierender `_deploy-unified.yml` (ADR-120) — kein Parallel-System
- Gate-Modell konsistent mit ADR-066 (AI Engineering Squad)

## Considered Options

### Option A — Status Quo: Manuelle IDE-Workflows + separates CI/CD

`/ship` in IDE → manuell, `deploy.yml` in CI → automatisch auf push/tag.

- **Pro**: Einfach, funktioniert
- **Con**: Staging-Skip, kein Rollback, kein Audit, IDE und CI entkoppelt

### Option B — Gate-controlled Deploy-Agent (gewählt)

Agent-gesteuerte Deployment-Pipeline mit Gate-Modell aus ADR-066.
Baut auf `_deploy-unified.yml` auf, ergänzt Pre-flight, Verification und Rollback.

- **Pro**: Staging nie übersprungen, automatischer Rollback, Audit-Trail, Gate-konsistent
- **Con**: Komplexer, erfordert zuverlässige Health-Endpoints, Discord-Webhook nötig

### Option C — Rein CI/CD-basiert (GitHub Actions only, kein Agent)

Alles in GitHub Actions, kein lokaler Agent-Eingriff.

- **Pro**: Standard-Tooling, kein lokaler Agent nötig
- **Con**: Kein ADR-Parsing, keine intelligente Failure-Analyse, kein Memory-Audit, kein IDE-Integration

## Decision Outcome

**Gewählt: Option B** — Gate-controlled Deploy-Agent, implementiert als Erweiterung von
`_deploy-unified.yml` (ADR-120) und den IDE-Workflows `/ship` + `/ship-staging`.

## Decision

### Gate-Modell (konsistent mit ADR-066 §Gate-System)

| Phase | Gate | Automatisierung | Approval |
|-------|------|----------------|----------|
| Pre-flight Checks | Gate 0 (Autonomous) | Vollautomatisch | Keine |
| Build & Push to GHCR | Gate 0 (Autonomous) | Vollautomatisch | Keine |
| Staging Deploy | Gate 1 (Notify) | Vollautomatisch | User wird informiert |
| Staging Verification | Gate 0 (Autonomous) | Vollautomatisch | Keine |
| **Prod Deploy** | **Gate 4 (Human-Only)** | Vorbereitet, wartet | **Explizite Freigabe** |
| Prod Verification | Gate 0 (Autonomous) | Vollautomatisch nach Freigabe | Keine |
| Rollback | Gate 0 (Autonomous) | Automatisch bei Health-Failure | Keine |

> **Gate 4 für Prod-Deploy** ist verbindlich per ADR-066 §Gate-System.
> Prod-Deploy darf NIEMALS automatisch erfolgen — immer Human-Only.

### Ablauf im Detail

```
┌─── TRIGGER: push main / v-tag / workflow_dispatch / /ship ───┐
│                                                                │
│  Phase 1: Pre-flight (Gate 0 — autonom)                        │
│  ├─ CI Job: _ci-python.yml (Ruff + Tests)                      │
│  ├─ complete-check.yml (Banned Patterns + Template Validation)  │
│  ├─ python manage.py migrate --check (Migration-Konflikte)      │
│  └─ Bei Failure → STOP + Discord ❌                             │
│                                                                │
│  Phase 2: Build & Push (Gate 0 — autonom)                      │
│  ├─ docker/build-push-action → ghcr.io/{owner}/{app}:{tag}     │
│  ├─ Tags: {sha-short} + latest                                 │
│  └─ Cache: GitHub Actions Cache (type=gha)                     │
│                                                                │
│  Phase 3: Staging Deploy (Gate 1 — autonom, User notified)     │
│  ├─ SSH → /opt/scripts/deploy.sh {app} {path} {tag} staging    │
│  ├─ docker compose pull + up -d                                │
│  ├─ Health-Check: /livez/ + /healthz/                          │
│  └─ Discord: "🧪 Staging deployed — {app}:{tag}"               │
│                                                                │
│  Phase 4: Staging Verification (Gate 0 — autonom)              │
│  ├─ HTTP 200 alle bekannten Endpoints                          │
│  ├─ Console-Error-Check (0 JS Errors, wenn Playwright)         │
│  └─ Bei Failure → STOP + Discord ❌                             │
│                                                                │
│  ──── GATE 4: Human-Only Approval ────                         │
│  ├─ GitHub Environment Protection Rule "production"             │
│  ├─ Discord: "✅ Staging OK — Prod bereit, warte auf Approval"  │
│  └─ Timeout: 72h (danach verfällt der Run)                     │
│                                                                │
│  Phase 5: Prod Deploy (nach Approval)                          │
│  ├─ /opt/scripts/deploy.sh {app} {path} {tag} production       │
│  ├─ docker stop + rm → compose pull + up -d (ADR-094)          │
│  ├─ Health-Check: /livez/ + /healthz/ (30s Timeout)            │
│  ├─ Bei Failure → AUTOMATISCHER ROLLBACK (vorheriges Image)    │
│  └─ Discord: "✅ Production deployed" / "❌ Rollback executed"   │
│                                                                │
│  Phase 6: Audit (Gate 0 — autonom)                             │
│  ├─ pgvector Memory: deploy:{date}:{app}                       │
│  ├─ Discord Summary mit Image-Tag, Duration, Status            │
│  └─ GitHub Issue close (wenn Issue-triggered)                  │
└────────────────────────────────────────────────────────────────┘
```

### Rollback-Strategie

Rollback nutzt GHCR Image-Tags. Jeder Deploy speichert den vorherigen Tag:

```bash
# In /opt/scripts/deploy.sh (erweitert):
PREV_TAG=$(grep "IMAGE_TAG=" /opt/{app}/.env.prod | cut -d= -f2)

# Deploy neue Version...
# Health-Check nach 30s:
if ! curl -sf --max-time 5 http://127.0.0.1:{port}/healthz/; then
  echo "❌ Health-Check failed — Rolling back to ${PREV_TAG}"
  sed -i "s/IMAGE_TAG=.*/IMAGE_TAG=${PREV_TAG}/" /opt/{app}/.env.prod
  docker compose -f docker-compose.prod.yml pull
  docker compose -f docker-compose.prod.yml up -d
  exit 1
fi
```

### Trigger-Mechanismen

| Trigger | Environment | Gate für Prod |
|---------|------------|---------------|
| `push main` | Staging (auto) | — |
| `push v*` tag | Production | Gate 4 (GitHub Environment) |
| `workflow_dispatch` staging | Staging | — |
| `workflow_dispatch` production | Production | Gate 4 (GitHub Environment) |
| `/ship` in IDE | Staging → Prod | Gate 4 (Discord Approval) |
| GitHub Issue `[deploy]` + `[auto]` | Staging → Prod | Gate 4 (Discord Approval) |

### Staging-Skip-Prevention

```yaml
# In deploy.yml (erweitert): Prod-Deploy REQUIRES vorherigen Staging-Success
deploy-production:
  needs: [resolve, build, deploy-staging, verify-staging]
  if: needs.verify-staging.result == 'success'
```

Für `workflow_dispatch` mit `target_environment: production` (direkter Prod-Deploy):
- Nur erlaubt mit `image_tag_override` (= Rollback auf bekanntes Image)
- Neubauten MÜSSEN durch Staging

### Was NICHT automatisiert wird

- **Erste Deployments neuer Repos** — DNS, Nginx, SSL, `/opt/scripts/deploy.sh` Setup
- **DB-Migrationen mit Datenverlust** — `RunPython` mit `DELETE`/`DROP` → manuell
- **Major Version Upgrades** (Django 5→6, PostgreSQL 16→17) → manuelles Testing
- **Infrastruktur-Änderungen** (neue Server, Firewall-Rules, Cloudflare)
- **Secret-Rotation** — immer Gate 4, manuell

### Implementierung

| Phase | Inhalt | DoD | Status |
|-------|--------|-----|--------|
| A | `complete-check.yml` in risk-hub | Banned Patterns + Template Validation als CI-Gate | ✅ done |
| B | `complete-check.yml` als Reusable Workflow in platform | Alle Repos können es einbinden | ⬜ none |
| C | `_deploy-unified.yml` Rollback-Erweiterung | `deploy.sh` speichert PREV_TAG, Rollback bei Health-Failure | ⬜ none |
| D | Staging-Skip-Prevention | `deploy-production` requires `verify-staging.result == 'success'` | ⬜ none |
| E | Audit-Phase (pgvector + Discord) | Deploy-Memory-Entry + Discord-Summary nach jedem Deploy | ⬜ none |
| F | IDE-Workflow `/ship` Integration | `/ship` triggert `workflow_dispatch` statt lokale SSH-Commands | ⬜ none |

## Consequences

### Positive

- Staging wird nie mehr übersprungen (enforced via Job-Dependency)
- Automatischer Rollback reduziert Prod-Downtime
- Audit-Trail in pgvector + Discord + GitHub Actions Log
- Gate 4 für Prod ist platform-weit konsistent (ADR-066)
- Baut auf existierender Infrastruktur auf (kein Parallel-System)

### Negative

- Erfordert zuverlässige `/healthz/` Endpoints in jedem Repo
- Discord-Webhook muss als Secret konfiguriert sein
- GitHub Environment Protection Rules müssen pro Repo eingerichtet werden
- Rollback funktioniert nur wenn GHCR das vorherige Image noch hat

### Risiken

| Risiko | Schwere | Mitigation |
|--------|---------|------------|
| Health-Check false positive (200 trotz Fehler) | HIGH | `/healthz/` prüft DB + Redis (nicht nur HTTP) |
| Approval-Request wird übersehen | MEDIUM | Discord-Notify + 72h Timeout + Daily Reminder |
| GHCR Image-Retention löscht altes Image | LOW | GHCR retention policy: ≥10 Tags behalten |
| Staging-Env driftet von Prod | MEDIUM | Gleiche Compose-Struktur, gleiche `.env`-Keys |
| Gleichzeitige Deploys (Race Condition) | MEDIUM | `concurrency` group in GitHub Actions |

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum |
|--------------|------------|-----------|
| Canary-Deploy statt Big-Bang | `deployment-mcp` hat `canary_deploy` — evaluieren für Repos mit >100 Users | 2026-Q3 |
| Playwright-basierter Smoke-Test in CI | Aktuell nur lokal — Browser-Test in CI erfordert Playwright Docker-Setup | 2026-Q3 |
| Multi-Server-Deploy | Aktuell Single-Server (Hetzner) — bei Skalierung: Deployment-Targets erweitern | 2026-Q4 |

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Gate** | Kontrollstufe im Agent-Workflow (Gate 0=autonom, Gate 4=nur Mensch). Definiert in ADR-066 §Gate-System |
| **Pre-flight** | Automatische Prüfungen VOR dem Deploy (Tests, Lint, Migration-Check) |
| **Health-Check** | HTTP-Abfrage an `/livez/` (Liveness) und `/healthz/` (Readiness inkl. DB+Redis) |
| **Rollback** | Zurücksetzen auf die vorherige funktionierende Version bei Fehler |
| **GHCR** | GitHub Container Registry — Docker-Image-Speicher unter `ghcr.io/achimdehnert/{app}` |
| **Staging** | Test-Umgebung (Dev Desktop `88.99.38.75` oder dedizierter Server) |
| **Prod** | Produktions-Umgebung (Hetzner `88.198.191.108`) |
| **Banned Patterns** | Code-Muster die per ADR verboten sind (z.B. `onclick=`, `hx-boost`, bare `except:`) |
| **Smoke-Test** | Schneller Funktionstest (HTTP 200 auf alle Seiten) nach Deploy |

## Confirmation

- **Staging-Skip-Rate = 0%** — messbar via GitHub Actions: kein Prod-Deploy ohne vorherigen Staging-Success
- **Rollback-Success-Rate ≥ 95%** — messbar via deploy.sh Exit-Code + Health-Check
- **Audit-Coverage = 100%** — jeder Deploy hat pgvector Memory-Entry
- **Gate 4 Enforcement** — kein Prod-Deploy ohne GitHub Environment Approval

## Compliance

- ADR-021: Unified Deployment Pattern — `_deploy-unified.yml` als Basis
- ADR-022: Platform Consistency — `env_file` statt `${VAR}` interpolation
- ADR-056: Deployment Preflight — Pre-flight Checks in Phase 1
- ADR-066: AI Engineering Squad — Gate-System (Gate 4 = Human-Only für Prod)
- ADR-094: Migration Conflict Resolution — `migrate --check` + `stop/rm` vor `compose up`
- ADR-120: Unified Deploy Pipeline — Reusable Workflow als Grundlage
- ADR-174: QM Gate — Assumption Check als Teil von Pre-flight

## Drift-Detector Governance Note

```yaml
paths:
  - .github/workflows/_deploy-unified.yml
  - .github/workflows/complete-check.yml
  - /opt/scripts/deploy.sh
gate: APPROVE
```
