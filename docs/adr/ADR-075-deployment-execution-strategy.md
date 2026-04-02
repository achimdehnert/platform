---
status: "accepted"
date: 2026-02-23
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: ["ADR-053-deployment-mcp-robustness.md"]
amends: ["ADR-021-unified-deployment-pattern.md", "ADR-056-deployment-preflight-and-pipeline-hardening.md"]
related: ["ADR-021-unified-deployment-pattern.md", "ADR-045-secrets-management.md", "ADR-056-deployment-preflight-and-pipeline-hardening.md", "ADR-066-ai-engineering-team.md", "ADR-156-reliable-deployment-pipeline.md"]
implementation_status: implemented
amended: 2026-04-02
---

# Split deployment execution: read-only local MCP tools and server-side GitHub Actions workflows

---

## Context and Problem Statement

Das `deployment-mcp` (in `mcp-hub`) stellt MCP-Tools für alle Deployment-Operationen
bereit — von `container_logs` bis `compose_up`. In der Praxis hängen alle Write-Operationen
(Deploy, Migrations, Compose-Restart) regelmäßig, weil jeder Tool-Call eine neue
SSH-Verbindung vom lokalen Rechner zum Server öffnet.

**Beobachtete Symptome:**
- `git_manage stash` → hängt, kein Response nach 60s
- `docker_manage compose_up` → blockiert Windsurf-Event-Loop
- `ssh_manage exec` für Migrations → Timeout bei langen Operationen
- Jeder SSH-Handshake kostet 2–5s; bei 30–120s Operationen → MCP-Timeout

**Ursache**: SSH-basierte MCP-Tools sind synchron. Lange Operationen blockieren den
MCP-Event-Loop. Das ist ein strukturelles Problem, kein Konfigurationsfehler.

**Parallel existiert** `infra-deploy` (Repo `achimdehnert/infra-deploy`, erstellt
2026-02-20, ADR-021 §2.14) mit GitHub Actions Workflows (`deploy-service.yml`,
`rollback.yml`) und einem production-grade `deploy.sh` (Health-Check, Auto-Rollback,
State-Tracking, Concurrency-Lock). Dieses System läuft server-seitig und ist
nicht-blockierend.

**Problem**: Keine klare Arbeitsteilung zwischen `deployment-mcp` (lokal, MCP) und
`infra-deploy` (server-seitig, GitHub Actions). Beide Systeme überlappen, das
blockierende System wird für Write-Ops verwendet.

### Betroffene Systeme

| System | Rolle | Aktueller Stand |
|--------|-------|----------------|
| `deployment-mcp` (mcp-hub) | MCP-Server, 20+ Tools | Aktiv, aber Write-Ops hängen |
| `infra-deploy` (eigenes Repo) | GitHub Actions + Shell | Aktiv, deploy + rollback vorhanden |
| `orchestrator_mcp` (mcp-hub) | Agent-Koordination | Nutzt deployment-mcp für Ops |

---

## Decision Drivers

- **Autonomes Arbeiten**: AI-Agenten (Cascade, ADR-066) müssen Deployments triggern
  können ohne den Event-Loop zu blockieren
- **Zuverlässigkeit**: Write-Ops dürfen nicht durch SSH-Timeouts fehlschlagen
- **Audit Trail**: Jede Deploy-Operation muss nachvollziehbar sein (GitHub Actions History)
- **Rollback-Fähigkeit**: Jeder fehlgeschlagene Deploy muss automatisch rollbacken
- **Least-Privilege**: Deploy-Credentials nur dort wo nötig
- **Minimale Disruption**: Bestehende Read-Only-Tools bleiben unverändert

---

## Constraints & Non-Goals

### Constraints (unveränderlich)

- Server: Hetzner VM `88.198.191.108` (kein Wechsel)
- Registry: `ghcr.io/achimdehnert/` (kein Wechsel)
- Orchestration: Docker Compose per App (kein Kubernetes)
- Runner: Self-hosted `[self-hosted, dev-server]` auf `88.198.191.108`
- Auth: SSH Key `DEPLOY_SSH_KEY` in GitHub Secrets

### Non-Goals

- Kein Wechsel der Container-Orchestrierung (Docker Compose bleibt)
- Kein Rewrite von `deployment-mcp` — nur Deprecation der Write-Tools
- Keine Einführung von Kubernetes, Helm oder ähnlichem
- Kein Monitoring-System (separates ADR)

---

## Considered Options

### Option 1 — Read/Write-Split: MCP lokal (Read) + GitHub Actions (Write) (gewählt)

`deployment-mcp` behält alle Read-Only-Tools. Write-Operationen (Deploy, Restart,
Migrations, Backup) werden ausschließlich über `infra-deploy` GitHub Actions ausgeführt.
AI-Agenten triggern Workflows via `repository_dispatch` (GitHub MCP).

**Pro:**
- Write-Ops laufen server-seitig — kein SSH-Timeout, kein Event-Loop-Block
- GitHub Actions History = vollständiger Audit Trail ohne Zusatzaufwand
- `concurrency:` in GitHub Actions verhindert parallele Deploys (race condition)
- `deploy.sh` hat bereits Health-Check + Auto-Rollback — production-grade
- AI-Agenten können via `mcp7_cicd_manage dispatch` non-blocking triggern
- Read-Only-Tools (Logs, Status) bleiben schnell und lokal verfügbar

**Contra:**
- Zwei Systeme statt einem (erhöhte kognitive Last)
- GitHub Actions Latenz: ~30s bis Workflow startet (Runner-Pickup)
- `infra-deploy` muss um `migrate.yml`, `db-backup.yml`, `health-check.yml` erweitert werden
- Self-hosted Runner muss dauerhaft laufen (Single Point of Failure)

**Entscheidung**: Gewählt — strukturell korrekt, löst das Hang-Problem an der Wurzel.

---

### Option 2 — deployment-mcp komplett rewriten (async SSH)

`deployment-mcp` wird auf async SSH (asyncssh / Fabric) umgestellt, alle Tools
werden non-blocking.

**Pro:**
- Ein System statt zwei
- Kein Wechsel der Trigger-Methode für AI-Agenten

**Contra:**
- Hoher Aufwand (kompletter Rewrite aller 20+ Tools)
- Async SSH löst nicht das Timeout-Problem bei 120s-Operationen
- Kein nativer Audit Trail (müsste selbst implementiert werden)
- Kein Rollback-Mechanismus ohne zusätzliche Implementierung
- MCP-Protokoll selbst ist synchron — Timeout-Problem bleibt strukturell

**Verworfen**: Löst das strukturelle Problem nicht; hoher Aufwand ohne Mehrwert.

---

### Option 3 — Nur GitHub Actions, deployment-mcp komplett entfernen

Alle Operationen (auch Read-Only) über GitHub Actions.

**Pro:**
- Ein System, klare Verantwortung

**Contra:**
- `container_logs` via GitHub Actions: 30s Latenz für eine Log-Zeile — inakzeptabel
- `dns_record_list`, `ssl_status` — Read-Only-Queries brauchen keine GitHub Actions
- Verlust der interaktiven Debugging-Fähigkeit (Logs, Status direkt in Windsurf)
- Jede kleine Status-Abfrage erzeugt einen GitHub Actions Run

**Verworfen**: Read-Only-Ops sind lokal schnell und zuverlässig — kein Grund sie zu migrieren.

---

### Option 4 — Webhook-basierter Deploy-Trigger auf dem Server

Ein HTTP-Endpoint auf dem Server nimmt Deploy-Requests entgegen (z.B. via `webhook`-Tool
oder eigener FastAPI-Service).

**Pro:**
- Kein GitHub Actions nötig
- Sehr schnell (kein Runner-Pickup)

**Contra:**
- Neuer Service muss deployed, gesichert und gewartet werden
- Auth-Konzept (Token, mTLS) muss selbst implementiert werden
- Kein nativer Audit Trail
- Erhöht Angriffsfläche (HTTP-Endpoint auf Prod-Server)

**Verworfen**: Sicherheitsrisiko; `infra-deploy` existiert bereits und ist besser.

---

## Decision Outcome

**Gewählt: Option 1** — Read/Write-Split. `deployment-mcp` für Read-Only,
`infra-deploy` GitHub Actions für alle Write-Operationen.

### Positive Consequences

- Deploy-Hänger strukturell eliminiert — Write-Ops laufen server-seitig
- Vollständiger Audit Trail via GitHub Actions History ohne Zusatzaufwand
- AI-Agenten können non-blocking deployen via `mcp7_cicd_manage dispatch`
- `deploy.sh` Auto-Rollback schützt vor fehlgeschlagenen Deploys
- Concurrency-Lock verhindert parallele Deploys (race condition)

### Negative Consequences

- GitHub Actions Startup-Latenz ~30s (akzeptabel für Deploy-Ops)
- Self-hosted Runner als Single Point of Failure — muss überwacht werden
- `infra-deploy` muss um 3 Workflows erweitert werden (migrate, backup, health-check)

---

## Implementation Details

### Architektur: Read/Write-Split

```
┌─────────────────────────────────────────────────────────────┐
│  Windsurf / Cascade (lokal)                                  │
│                                                              │
│  READ-OPS (schnell, lokal)    WRITE-OPS (server-seitig)     │
│  ─────────────────────────    ──────────────────────────     │
│  deployment-mcp Tools:        GitHub MCP:                    │
│  • container_logs             • mcp7_cicd_manage dispatch    │
│  • container_list             • mcp7_cicd_manage run_status  │
│  • compose_ps                 • mcp7_cicd_manage run_logs    │
│  • service_status                      │                     │
│  • ssl_status                          │                     │
│  • dns_record_list                     ▼                     │
│  • server_status              infra-deploy Workflows:        │
│           │                   • deploy-service.yml           │
│           │                   • rollback.yml                 │
│           ▼                   • migrate.yml (neu)            │
│  SSH → 88.198.191.108         • db-backup.yml (neu)          │
│  (Read-only, < 5s)            • health-check.yml (neu)       │
│                                        │                     │
│                               Self-hosted Runner             │
│                               → 88.198.191.108               │
│                               → deploy.sh (server-seitig)   │
└─────────────────────────────────────────────────────────────┘
```

### Workflow-Sequenz: AI-Agent Deploy

```
1. Cascade: mcp7_cicd_manage dispatch
   → owner: achimdehnert, repo: infra-deploy
   → workflow_id: deploy-service.yml
   → inputs: {service: "travel-beat", image_tag: "latest", has_migrations: "false"}

2. GitHub Actions: Runner-Pickup (~30s)
   → deploy-service.yml startet auf [self-hosted, dev-server]
   → concurrency group: deploy-production-travel-beat (verhindert parallele Deploys)

3. deploy.sh auf Server:
   → docker compose pull web
   → (optional) python manage.py migrate --noinput
   → docker compose up -d --force-recreate web
   → Health-Check: curl http://127.0.0.1:8002/healthz/ (12x, 5s Intervall)
   → Bei Erfolg: TAG_FILE aktualisieren, deploy.log schreiben
   → Bei Fehler: Auto-Rollback auf OLD_TAG, deploy.log schreiben, exit 1

4. Cascade: mcp7_cicd_manage run_status (polling, non-blocking)
   → Prüft Workflow-Status alle 30s
   → Bei completed/success: Done
   → Bei completed/failure: Rollback bereits erfolgt, Mensch informieren (Gate 2)
```

### Neue Workflows für `infra-deploy`

| Workflow | Trigger | Zweck | Timeout |
|----------|---------|-------|---------|
| `deploy-service.yml` | `repository_dispatch` / `workflow_dispatch` | Deploy + Health-Check + Auto-Rollback | 15 min |
| `rollback.yml` | `workflow_dispatch` | Expliziter Rollback auf Tag | 10 min |
| `migrate.yml` | `workflow_dispatch` | Nur Migrations (ohne Deploy) | 10 min |
| `db-backup.yml` | `workflow_dispatch` / `schedule` | PostgreSQL Backup vor Migrations | 15 min |
| `health-check.yml` | `workflow_dispatch` / `schedule` | Post-Deploy Verification aller Services | 5 min |

### Deprecation-Plan `deployment-mcp` Write-Tools

| Tool | Kategorie | Aktion | Bis |
|------|-----------|--------|-----|
| `compose_up` | Write | Deprecated → `deploy-service.yml` | ADR-075 accepted |
| `compose_restart` | Write | Deprecated → `deploy-service.yml` | ADR-075 accepted |
| `compose_down` | Write | Deprecated → manuell (Gate 4) | ADR-075 accepted |
| `container_restart` | Write | Deprecated → `deploy-service.yml` | ADR-075 accepted |
| `migrate` (db_manage) | Write | Deprecated → `migrate.yml` | ADR-075 accepted |
| `backup` (db_manage) | Write | Deprecated → `db-backup.yml` | ADR-075 accepted |
| `container_logs` | Read | Bleibt in deployment-mcp | — |
| `container_list` | Read | Bleibt in deployment-mcp | — |
| `compose_ps` | Read | Bleibt in deployment-mcp | — |
| `service_status` | Read | Bleibt in deployment-mcp | — |
| `ssl_status` | Read | Bleibt in deployment-mcp | — |
| `dns_record_list` | Read | Bleibt in deployment-mcp | — |
| `server_status` | Read | Bleibt in deployment-mcp | — |

### Write-Op-Klassifikation (Amendment 2026-04-02, ADR-156)

Die ursprüngliche Regel "alle Write-Ops via GitHub Actions" wird differenziert.
Das Kern-Problem (SSH-Operationen >30s blockieren MCP-Event-Loop) bleibt bestanden.
Kurze Trigger-Commands (<5s) die nur einen Server-seitigen Prozess starten,
sind strukturell verschieden von lang laufenden synchronen SSH-Operationen.

| Tier | Dauer | Kanal | Bedingungen | Beispiele |
|------|-------|-------|-------------|-----------|
| **Long-Running Write** | >15s | GitHub Actions (`infra-deploy`) | Regel unverändert — MUSS über CI laufen | `docker compose up`, `migrate`, `build` |
| **Short Trigger** | <5s | SSH (`deploy-start.sh`) | Startet nur Background-Prozess, returniert sofort mit Job-ID (JSON), idempotent, atomares Locking (flock) | `deploy-start.sh <repo>`, `deploy-status.sh <repo>` |
| **Read-Op** | <5s | deployment-mcp SSH | Regel unverändert — bleibt in deployment-mcp | `container_logs`, `compose_ps`, `file_read` |

**Koexistenz-Modell**: Beide Trigger-Methoden (GitHub Actions + SSH Short-Trigger)
nutzen dasselbe server-seitige `deploy.sh` — die Deploy-Logik ist einmal implementiert
in `/opt/deploy-core/`. GitHub Actions bleibt Fallback wenn SSH nicht verfügbar.

**Referenz**: ADR-156 §Phase 1 (deploy-start.sh), ADR-107 §4.3 (Deployment Agent shell_exec).

### Security-Anforderungen

| Anforderung | Implementierung | Status |
|-------------|----------------|--------|
| Secrets nie in Logs | `::add-mask::` in GitHub Actions | ✅ done |
| Least-Privilege SSH | `DEPLOY_SSH_KEY` nur in `infra-deploy` Secrets | ✅ done |
| Concurrent Deploy Protection | `concurrency: group: deploy-production-$service` | ✅ done |
| Audit Trail | GitHub Actions History + `deploy.log` auf Server | ✅ done |
| Auto-Rollback | `deploy.sh` Health-Check + Rollback bei Failure | ✅ done |
| Idempotentes Deploy | `--force-recreate` + Tag-State-File | ✅ done |
| Pre-Deploy DB-Backup | `db-backup.yml` vor `migrate.yml` | ⬜ pending |
| Separate Deploy-User | Aktuell `root` — Risiko, Mitigation: Firewall + Key-Scope | ⚠️ accepted risk |

### Operational Runbook

| Szenario | Aktion | Methode |
|----------|--------|---------|
| Service deployen | `deploy-service.yml` triggern | GitHub Actions UI oder `mcp7_cicd_manage dispatch` |
| Rollback | `rollback.yml` triggern | GitHub Actions UI (Gate 3) |
| Nur Migrations | `migrate.yml` triggern | GitHub Actions UI (Gate 2) |
| DB-Backup | `db-backup.yml` triggern | GitHub Actions UI (Gate 2) |
| Deploy-Status | `run_status` pollen | `mcp7_cicd_manage run_status` |
| Logs prüfen | `container_logs` | `deployment-mcp container_logs` |
| Deploy-History | GitHub Actions History | `infra-deploy/actions` |
| Server-seitiger Log | `deploy.log` | `deployment-mcp ssh_manage file_read /opt/deploy/production/.deployed/deploy.log` |

---

## Migration Tracking

| Schritt | Abhängigkeit | Status | Datum |
|---------|-------------|--------|-------|
| `migrate.yml` in `infra-deploy` erstellen | — | ✅ done (2026-02-23) | — |
| `db-backup.yml` in `infra-deploy` erstellen | — | ✅ done (2026-02-23) | — |
| `health-check.yml` in `infra-deploy` erstellen | — | ✅ done (2026-02-23) | — |
| `deployment-mcp` Write-Tools mit Deprecation-Warning versehen | migrate.yml done | ✅ done (2026-02-23) | — |
| ADR-053 als Superseded markieren | ADR-075 accepted | ✅ done (2026-02-23) | — |
| Windsurf-Workflow `/deploy` auf `infra-deploy` umstellen | alle Workflows done | ✅ done (2026-02-23) | — |
| Self-hosted Runner Health-Monitor einrichten | — | ✅ done (2026-02-23) | runner-health.yml |

---

## Consequences

### Risks

| Risiko | Schwere | Wahrscheinlichkeit | Mitigation |
|--------|---------|-------------------|-----------|
| Self-hosted Runner down → kein Deploy möglich | HIGH | LOW | Runner als systemd-Service mit auto-restart; Monitoring via `health-check.yml` |
| GitHub Actions Startup-Latenz (~30s) | LOW | HIGH | Akzeptiert — Deploy ist kein Echtzeit-Vorgang |
| `root`-SSH auf Prod-Server | MEDIUM | LOW | Akzeptiertes Risiko; Firewall auf Port 22 + Key-Scope; separater Deploy-User als Follow-up |
| Zwei Systeme erhöhen kognitive Last | LOW | MEDIUM | Klare Regel: Write = infra-deploy, Read = deployment-mcp |
| `infra-deploy` Scripts veralten (Service-Registry) | MEDIUM | MEDIUM | Service-Registry in `deploy.sh` spiegelt ADR-021 §2.3 — bei neuem Service beide aktualisieren |

### Confirmation (messbare Kriterien)

- [ ] Kein `deployment-mcp` Write-Tool-Call hängt mehr in Windsurf
- [ ] `deploy-service.yml` läuft erfolgreich für alle 6 Services
- [ ] `rollback.yml` rollt erfolgreich auf `prev`-Tag zurück
- [ ] `migrate.yml` und `db-backup.yml` existieren und sind getestet
- [ ] AI-Agent (Cascade) kann via `mcp7_cicd_manage dispatch` deployen ohne Hang
- [ ] GitHub Actions History zeigt vollständigen Audit Trail aller Deploys
- [ ] Self-hosted Runner läuft als systemd-Service mit auto-restart

### Deprecation-Pfad

| Was wird deprecated | Bis wann | Ersatz |
|--------------------|----------|--------|
| `deployment-mcp` Write-Tools (compose_up, migrate, backup, restart) | ADR-075 `accepted` | `infra-deploy` Workflows |
| ADR-053 (deployment-mcp Robustness) | ADR-075 `accepted` | Dieses ADR |

---

## Best Practices Compliance

| Best Practice | Status | Notiz |
|--------------|--------|-------|
| Immutable Infrastructure (Tags statt `latest` in Prod) | ⚠️ | `latest` aktuell erlaubt; SHA-Tags empfohlen als Follow-up |
| Health-Check nach jedem Deploy | ✅ | `deploy.sh`: 12 Retries × 5s = 60s Window |
| Automatischer Rollback bei Health-Check-Failure | ✅ | `deploy.sh`: Auto-Rollback auf `OLD_TAG` |
| Concurrent Deploy Protection | ✅ | `concurrency: cancel-in-progress: false` |
| Audit Trail (append-only Log) | ✅ | `deploy.log` + GitHub Actions History |
| Secrets nie in Logs/Outputs | ✅ | `DEPLOY_SSH_KEY` via `${{ secrets.* }}` |
| Idempotentes Deploy-Script | ✅ | `--force-recreate` + State-File |
| Least-Privilege Principle | ⚠️ | `root`-SSH akzeptiertes Risiko; Follow-up: Deploy-User |
| Separate Deploy-User (nicht root) | ❌ | Aktuell `root`; ADR-068 als Follow-up geplant |
| Pre-Deploy Backup (DB) bei Migrations | ⬜ | `db-backup.yml` pending |
| Non-blocking für AI-Agenten | ✅ | `mcp7_cicd_manage dispatch` + `run_status` polling |
| Runner-Availability-Monitoring | ⬜ | `health-check.yml` pending |

---

## Drift-Detector Governance Note

```yaml
paths:
  - infra-deploy/.github/workflows/
  - infra-deploy/scripts/
  - mcp-hub/deployment_mcp/src/deployment_mcp/tools/
gate: APPROVE
```
