---
status: proposed
date: 2026-05-06
updated: 2026-05-06
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: [ADR-120]
related: [ADR-021, ADR-022, ADR-056, ADR-066, ADR-094, ADR-120, ADR-174]
implementation_status: partial
implementation_evidence:
  - "Pilot: risk-hub/.github/workflows/complete-check.yml (Phase A)"
tags: [deployment, agent, automation, ci-cd]
---

# ADR-185: Adopt Gate-controlled Deploy-Agent for automated Staging→Prod deployments

## Context and Problem Statement

Deployments aller IIL-Platform-Repos folgen einem wiederkehrenden, deterministischen Ablauf:

1. Pre-flight Checks (Migration-Konflikte, Tests, Banned Patterns)
2. Build & Push (Docker Image → GHCR)
3. Staging-Deploy (Pull + Compose Up + Health-Check)
4. Staging-Verification (HTTP 200, Smoke-Test)
5. Prod-Deploy (nach Approval)
6. Prod-Verification (Health-Check, Rollback bei Failure)

Dieser Ablauf ist heute teils manuell über IDE-Workflows (`/ship`, `/ship-staging`) und teils
automatisiert über `_deploy-unified.yml` (ADR-120) gesteuert.

### Problem

- **Staging wird übersprungen** — `deploy.yml` erlaubt `target_environment: production` direkt; Tag-basierte Deploys skippen Staging per ADR-120 Design (`deploy_staging=false` bei `v*`-Tags)
- **Kein Pre-flight vor Deploy** — Migration-Konflikte und Banned Patterns werden im CI geprüft, aber nicht als Gate im Deploy-Flow
- **Rollback ohne Observability** — `deploy.sh` hat Rollback (seit ADR-120/166), aber kein Audit-Trail, keine Benachrichtigung, keine Verifikation nach Rollback
- **Kein einheitlicher Audit-Trail** — Deploys werden nicht in pgvector Memory protokolliert
- **IDE-Workflows und CI/CD sind entkoppelt** — `/ship` in der IDE und `deploy.yml` in GitHub Actions haben unterschiedliche Logik

### Decision Drivers

- Staging-Skip-Rate auf 0% senken (aktuell geschätzt >50%)
- Rollback-Observability: pgvector-Audit + GitHub Actions Summary bei Rollback
- Einheitlicher Audit-Trail (pgvector + GitHub Actions Log)
- Kompatibilität mit existierender `_deploy-unified.yml` (ADR-120) — kein Parallel-System
- Gate-Modell konsistent mit ADR-066 (AI Engineering Squad)

## Considered Options

### Option A — Status Quo: Manuelle IDE-Workflows + separates CI/CD

`/ship` in IDE → manuell, `deploy.yml` in CI → automatisch auf push/tag.

- **Pro**: Einfach, funktioniert
- **Con**: Staging-Skip, keine Rollback-Observability, kein Audit, IDE und CI entkoppelt

### Option B — Gate-controlled Deploy-Agent (gewählt)

Agent-gesteuerte Deployment-Pipeline mit Gate-Modell aus ADR-066.
Baut auf `_deploy-unified.yml` auf, ergänzt Pre-flight, Verification, Rollback-Observability und Audit.

- **Pro**: Staging nie übersprungen, Rollback-Observability, Audit-Trail, Gate-konsistent
- **Con**: Komplexer, erfordert zuverlässige Health-Endpoints

### Option C — Rein CI/CD-basiert (GitHub Actions only, kein Agent)

Alles in GitHub Actions, kein Agent-Eingriff.

- **Pro**: Standard-Tooling, kein Agent nötig
- **Con**: Kein Memory-Audit (pgvector), kein IDE-Integration, regelbasiert genügt aktuell (KI-basierte Failure-Analyse als Deferred Decision)

## Decision Outcome

**Gewählt: Option B** — Gate-controlled Deploy-Agent, implementiert als Erweiterung von
`_deploy-unified.yml` (ADR-120) und den IDE-Workflows `/ship` + `/ship-staging`.

> **Hinweis**: Die KI-basierte intelligente Failure-Analyse ist eine Deferred Decision.
> In Phase 1 ist der Deploy-Agent **regelbasiert** (Guardian-Erweiterung, kein LLM).
> Die Agent-Rolle ist: **Deploy-Guardian** (Tier: Regelbasiert, Gate: 0–4), ergänzt die
> bestehende Guardian-Rolle aus ADR-066 um Deployment-spezifische Checks.

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
│  └─ Bei Failure → STOP + GH Actions Summary ❌                  │
│                                                                │
│  Phase 2: Build & Push (Gate 0 — autonom)                      │
│  ├─ docker/build-push-action → ghcr.io/{owner}/{app}:{tag}     │
│  ├─ Tags: main-{sha-7} (Staging) oder v{semver} (Prod)        │
│  └─ Cache: GitHub Actions Cache (type=gha)                     │
│                                                                │
│  Phase 3: Staging Deploy (Gate 1 — autonom, User notified)     │
│  ├─ SSH → /opt/scripts/deploy.sh {app} {path} {tag} staging    │
│  ├─ deploy.sh: pull + up -d --force-recreate (ADR-094 §2.4a)  │
│  ├─ Health-Check: /livez/ + /healthz/ (12 Versuche, 60s)      │
│  └─ GH Actions Summary: "🧪 Staging deployed — {app}:{tag}"   │
│                                                                │
│  Phase 4: Staging Verification (Gate 0 — autonom)              │
│  ├─ verify-staging Job: HTTP 200 auf Health-URL                │
│  ├─ Container-Status-Check (kein unhealthy/exit/error)         │
│  └─ Bei Failure → STOP + GH Actions Summary ❌                  │
│                                                                │
│  ──── GATE 4: Human-Only Approval ────                         │
│  ├─ GitHub Environment Protection Rule "production"             │
│  ├─ GH Actions: "✅ Staging OK — warte auf Production Approval" │
│  └─ Timeout: 72h (danach verfällt der Run)                     │
│                                                                │
│  Phase 5: Prod Deploy (nach Approval)                          │
│  ├─ /opt/scripts/deploy.sh {app} {path} {tag} production       │
│  ├─ deploy.sh: pull + up -d --force-recreate (ADR-094 §2.4a)  │
│  ├─ Health-Check: /livez/ + /healthz/ (12 Versuche, 60s)      │
│  ├─ Bei Failure → AUTOMATISCHER ROLLBACK (deploy.sh trap ERR)  │
│  └─ GH Actions Summary: "✅ Production deployed" / "❌ Rollback" │
│                                                                │
│  Phase 6: Audit (Gate 0 — autonom)                             │
│  ├─ pgvector Memory: deploy:{date}:{app} (entry_type: context) │
│  ├─ GH Actions Job Summary mit Duration, Tag, Status           │
│  └─ GitHub Issue close (wenn Issue-triggered)                  │
└────────────────────────────────────────────────────────────────┘
```

### Tag-basierte Prod-Deploys: SHA-Match-Check (K1)

ADR-120 erlaubt Tag-basierte Deploys (`v*`) direkt nach Production.
ADR-185 verlangt: kein Prod-Deploy ohne vorherige Staging-Verifikation.

**Lösung: SHA-Match-Check** — der Prod-Deploy prüft ob der Git-SHA des
Tags bereits auf Staging deployed und verifiziert wurde:

```yaml
# In _deploy-unified.yml (erweitert):
verify-staging-history:
  name: "🔍 Verify Staging History"
  runs-on: self-hosted
  needs: [resolve, build]
  if: needs.resolve.outputs.deploy_prod == 'true'
  steps:
    - name: Check if SHA was staged
      run: |
        SHA="${{ github.sha }}"
        SHORT="${SHA:0:7}"
        APP="${{ inputs.app_name }}"

        # Prüfe ob main-{sha} Image in GHCR existiert (= wurde gebaut + staged)
        if docker manifest inspect "ghcr.io/${{ github.repository_owner }}/${APP}:main-${SHORT}" >/dev/null 2>&1; then
          echo "✅ SHA ${SHORT} was previously staged (GHCR tag exists)"
          echo "staged=true" >> "$GITHUB_OUTPUT"
        else
          echo "❌ SHA ${SHORT} was NEVER staged — blocking production deploy"
          echo "staged=false" >> "$GITHUB_OUTPUT"
          exit 1
        fi

deploy-production:
  needs: [resolve, build, verify-staging-history]
  if: needs.verify-staging-history.result == 'success'
```

**Ausnahme**: `workflow_dispatch` mit `image_tag_override` (Rollback auf
bekanntes Image) überspringt den SHA-Match-Check — der Operator wählt
bewusst ein bekanntes Image.

### Environment-Datei-Konvention (K3)

Zwei Dateien mit verschiedenen Zwecken, konsistent über Staging und Prod:

| Datei | Zweck | Gelesen von | Inhalt |
|-------|-------|-------------|--------|
| `.env` | Compose-Interpolation | `docker compose` CLI | `IMAGE_TAG`, `GHCR_OWNER`, `GHCR_REPO`, `COMPOSE_PROJECT_NAME` |
| `.env.prod` / `.env.staging` | App-Secrets | Container (via `env_file:`) | `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, etc. |

**Staging-Besonderheiten**:
- Compose-File: `docker-compose.prod.yml` (gleiche Struktur wie Prod)
- `COMPOSE_PROJECT_NAME=staging-{app}` (in `.env` oder via deploy.sh)
- `.env.staging` für Staging-spezifische App-Secrets (z.B. andere DB)

**CRITICAL**: `deploy.sh` liest `IMAGE_TAG` aus `.env` (nicht `.env.prod`).
Rollback-Code muss ebenfalls `.env` verwenden:

```bash
# KORREKT (deploy.sh Zeile 37):
PREVIOUS_TAG=$(grep "^IMAGE_TAG=" "$APP_PATH/.env" | cut -d= -f2 || true)

# FALSCH — .env.prod enthält kein IMAGE_TAG:
# PREVIOUS_TAG=$(grep "IMAGE_TAG=" "$APP_PATH/.env.prod" | cut -d= -f2)
```

### Rollback-Observability (K2)

`deploy.sh` hat bereits Rollback-Logik (seit ADR-120/166: `trap rollback ERR`,
`PREVIOUS_TAG` Speicherung). Was **fehlt** ist Observability:

| Feature | Ist-Zustand | Soll (ADR-185) |
|---------|------------|----------------|
| Rollback-Ausführung | ✅ deploy.sh trap ERR | ✅ unverändert |
| Rollback-Logging | ✅ stdout/log-file | ✅ unverändert |
| pgvector Memory-Entry | ❌ | ✅ Phase E |
| GH Actions Job Summary | ❌ | ✅ Phase C |
| Health-Check nach Rollback | ❌ | ✅ Phase C |
| Rollback-Reason (HTTP-Code) | ❌ | ✅ Phase C |

**Phase C erweitert deploy.sh** um:

```bash
# Nach Rollback (in rollback() Funktion):
echo "::warning::Rollback executed: ${APP_NAME} ${IMAGE_TAG} → ${PREVIOUS_TAG}" # GH Actions Annotation
echo "## ⚠️ Rollback" >> "$GITHUB_STEP_SUMMARY"  # GH Actions Job Summary
echo "- **App**: ${APP_NAME}" >> "$GITHUB_STEP_SUMMARY"
echo "- **Failed Tag**: ${IMAGE_TAG}" >> "$GITHUB_STEP_SUMMARY"
echo "- **Rolled back to**: ${PREVIOUS_TAG}" >> "$GITHUB_STEP_SUMMARY"
echo "- **Reason**: Health-Check failed (exit $ec)" >> "$GITHUB_STEP_SUMMARY"

# Health-Check nach Rollback (NEU):
sleep 10
if curl -sf --max-time 5 "http://127.0.0.1:${INTERNAL_PORT}${HEALTH_PATH}" >/dev/null; then
  echo "✅ Post-Rollback Health-Check OK"
else
  echo "::error::KRITISCH: Post-Rollback Health-Check fehlgeschlagen!"
fi
```

### Deploy-Varianten (K4, konsistent mit ADR-094 §2.4)

| Variante | Methode | Wann |
|----------|---------|------|
| **A: GHCR-Pull** (Standard) | `pull` + `up -d --force-recreate` | Normaler Deploy via CI/CD |
| **B: Lokaler Build** (Notfall) | `docker build` + `stop/rm` + `up -d` | Hotfix ohne CI, lokaler Build |

Variante A ist der Standard seit ADR-120. `deploy.sh` implementiert Variante A.
Variante B ist in ADR-094 §2.4b dokumentiert für Notfälle.

### Trigger-Mechanismen

| Trigger | Ist-Zustand | ADR-185 Soll | Transition |
|---------|------------|--------------|------------|
| `push main` | Staging (auto) | Staging (auto) | Keine Änderung |
| `push v*` tag | Direkt Prod | Prod **nur wenn SHA vorher staged** | Phase D: SHA-Match-Check |
| `workflow_dispatch` staging | Staging | Staging | Keine Änderung |
| `workflow_dispatch` production | Direkt Prod (erlaubt) | Nur mit `image_tag_override` (Rollback) | Phase D |
| `/ship` in IDE | SSH direkt auf Server | workflow_dispatch Trigger | Phase F |
| GitHub Issue `[deploy]+[auto]` | Existiert nicht | Staging → Prod (Gate 4) | Phase F |

### Staging-Skip-Prevention

```yaml
# In _deploy-unified.yml (erweitert):

# Für push-auf-main: Staging läuft normal (keine Änderung)

# Für v*-Tags: SHA-Match-Check als Prerequisite
deploy-production:
  needs: [resolve, build, verify-staging-history]
  if: |
    always() &&
    needs.resolve.outputs.deploy_prod == 'true' &&
    (needs.build.result == 'success' || needs.build.result == 'skipped') &&
    (needs.verify-staging-history.result == 'success' || needs.verify-staging-history.result == 'skipped')

# Für workflow_dispatch mit target_environment=production:
# Nur erlaubt mit image_tag_override (= Rollback auf bekanntes Image)
# Neubauten MÜSSEN durch Staging (SHA-Match-Check blockiert)
```

### Worker Graceful Shutdown

Repos mit Celery-Workers (risk-hub, travel-beat, weltenhub):

```bash
# In deploy.sh (Erweiterung Phase C):
# 1. Web-Service neu starten
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "${APP_NAME}-web"

# 2. Health-Check Web
_wait_for_health

# 3. Worker mit Grace Period neu starten (10s für laufende Tasks)
docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "${APP_NAME}-worker"
```

**Deferred**: Celery-spezifisches `SIGTERM` Handling mit `--pool=prefork`
Grace Period. Aktuell akzeptabel weil Worker-Tasks idempotent sind.

### Migration-Safety

| Szenario | Risiko | Mitigation |
|----------|--------|------------|
| Migration schlägt in `entrypoint.sh` fehl | Container crasht → Rollback-Trigger | deploy.sh trap ERR → Rollback auf PREVIOUS_TAG |
| Migration halb ausgeführt + Rollback | Alte Code-Version + teilweise neues DB-Schema | Expand-Contract-Pattern (ADR-021 §2.16): nur additive Änderungen in einem Release |
| `RunPython` mit DELETE/DROP | Datenverlust bei Rollback | "Was NICHT automatisiert wird" → manuell |

### Was NICHT automatisiert wird

- **Erste Deployments neuer Repos** — DNS, Nginx, SSL, `/opt/scripts/deploy.sh` Setup
- **DB-Migrationen mit Datenverlust** — `RunPython` mit `DELETE`/`DROP` → manuell
- **Major Version Upgrades** (Django 5→6, PostgreSQL 16→17) → manuelles Testing
- **Infrastruktur-Änderungen** (neue Server, Firewall-Rules, Cloudflare)
- **Secret-Rotation** — immer Gate 4, manuell

### pgvector Audit-Schema

Jeder Deploy erzeugt einen Memory-Entry:

```python
# entry_key: "deploy:2026-05-06:risk-hub"
# entry_type: "context"
# tags: ["deploy", "risk-hub", "production", "success"]
{
    "app": "risk-hub",
    "environment": "production",
    "image_tag": "v1.4.2",
    "previous_tag": "v1.4.1",
    "git_sha": "a3f9d12",
    "status": "success",          # success | rollback | failed
    "duration_seconds": 45,
    "health_check": "ok",
    "rollback_executed": false,
    "trigger": "tag",             # tag | push_main | workflow_dispatch | ship | issue
    "timestamp": "2026-05-06T08:30:00Z"
}
```

### Implementierung

| Phase | Inhalt | DoD | Abhängig von | Status |
|-------|--------|-----|-------------|--------|
| A | `complete-check.yml` in risk-hub (Pilot) | Banned Patterns + Template Validation als CI-Gate | — | ✅ done |
| B | `complete-check.yml` als Reusable Workflow in platform | Alle Repos können es einbinden | A | ⬜ pending |
| C | Rollback-Observability + Worker-Graceful-Shutdown | GH Actions Summary bei Rollback, Health-Check nach Rollback, Worker-Restart-Sequenz | — | ⬜ pending |
| D | SHA-Match-Check + Staging-Skip-Prevention | `verify-staging-history` Job, `deploy-production` requires staged SHA | B | ⬜ pending |
| E | Audit-Phase (pgvector) | Deploy-Memory-Entry nach jedem Deploy (Schema s.o.) | C | ⬜ pending |
| F | IDE-Workflow `/ship` Integration | `/ship` triggert `workflow_dispatch` statt lokale SSH-Commands | D | ⬜ pending |

> **Aufwandsschätzung**: B: 2h, C: 3h, D: 2h, E: 2h, F: 3h = ~12h gesamt

## Consequences

### Positive

- Staging wird nie mehr übersprungen (enforced via SHA-Match-Check)
- Rollback-Observability: pgvector-Audit + GH Actions Summary + Post-Rollback-Health-Check
- Audit-Trail in pgvector + GitHub Actions Log
- Gate 4 für Prod ist platform-weit konsistent (ADR-066)
- Baut auf existierender Infrastruktur auf (kein Parallel-System)
- Deploy-Varianten (GHCR-Pull vs. lokaler Build) konsistent mit ADR-094 §2.4

### Negative

- Erfordert zuverlässige `/healthz/` Endpoints in jedem Repo
- GitHub Environment Protection Rules müssen pro Repo eingerichtet werden
- Rollback funktioniert nur wenn GHCR das vorherige Image noch hat
- SHA-Match-Check fügt ~10s Latenz zu Tag-basierten Deploys hinzu

### Risiken

| Risiko | Schwere | Mitigation |
|--------|---------|------------|
| Health-Check false positive (200 trotz Fehler) | HIGH | `/healthz/` prüft DB + Redis (nicht nur HTTP) |
| Approval-Request wird übersehen | MEDIUM | GH Actions "Waiting for review" + 72h Timeout |
| GHCR Image-Retention löscht altes Image | LOW | GHCR retention policy: ≥10 Tags behalten |
| Staging-Env driftet von Prod | MEDIUM | Gleiche Compose-Struktur, gleiche `.env`-Keys |
| Gleichzeitige Deploys (Race Condition) | MEDIUM | `concurrency` group in GitHub Actions (`deploy-{app}-{env}`) |
| Migration halb ausgeführt + Rollback | HIGH | Expand-Contract-Pattern (ADR-021 §2.16) |
| Worker-Tasks abgebrochen bei Restart | MEDIUM | Worker nach Web neu starten (Phase C); Tasks idempotent |

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum |
|--------------|------------|-----------|
| KI-basierte Failure-Analyse | Deploy-Agent ist aktuell regelbasiert (Guardian). LLM-Analyse von Logs bei Rollback als zukünftige Erweiterung | 2026-Q3 |
| Canary-Deploy statt Big-Bang | `deployment-mcp` hat `canary_deploy` — evaluieren für Repos mit >100 Users | 2026-Q3 |
| Playwright-basierter Smoke-Test in CI | Aktuell nur lokal — Browser-Test in CI erfordert Playwright Docker-Setup | 2026-Q3 |
| Multi-Server-Deploy | Aktuell Single-Server (Hetzner) — bei Skalierung: Deployment-Targets erweitern | 2026-Q4 |
| Celery SIGTERM Grace Period | `--pool=prefork` mit `CELERYD_MAX_TASKS_PER_CHILD` + Grace Period | 2026-Q3 |

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Gate** | Kontrollstufe im Agent-Workflow (Gate 0=autonom, Gate 4=nur Mensch). Definiert in ADR-066 §Gate-System |
| **Pre-flight** | Automatische Prüfungen VOR dem Deploy (Tests, Lint, Migration-Check) |
| **Health-Check** | HTTP-Abfrage an `/livez/` (Liveness) und `/healthz/` (Readiness inkl. DB+Redis) |
| **Rollback** | Zurücksetzen auf die vorherige funktionierende Version bei Fehler. Implementiert in `deploy.sh` via `trap rollback ERR` |
| **GHCR** | GitHub Container Registry — Docker-Image-Speicher unter `ghcr.io/achimdehnert/{app}` |
| **Staging** | Test-Umgebung auf dem Dev-Server. Zugang via Cloudflare Access |
| **Prod** | Produktions-Umgebung auf dem Hetzner Prod-Server |
| **Banned Patterns** | Code-Muster die per ADR verboten sind (z.B. `onclick=`, `hx-boost`, bare `except:`) |
| **Smoke-Test** | Schneller Funktionstest (HTTP 200 auf alle Seiten) nach Deploy |
| **SHA-Match-Check** | Verifikation dass ein Git-SHA bereits auf Staging deployed und getestet wurde, bevor Prod-Deploy erlaubt ist |
| **Deploy-Guardian** | Regelbasierte Erweiterung der Guardian-Rolle (ADR-066) für Deployment-Checks. Kein LLM, statische Regeln |
| **.env** | Compose-Interpolationsdatei (`IMAGE_TAG`, `GHCR_OWNER`). Nicht mit `.env.prod` (App-Secrets) verwechseln |

## Confirmation

- **Staging-Skip-Rate = 0%** — messbar via GitHub Actions: kein Prod-Deploy ohne vorherigen Staging-Success (SHA-Match-Check)
- **Rollback-Observability = 100%** — jeder Rollback hat GH Actions Summary + pgvector Entry
- **Audit-Coverage = 100%** — jeder Deploy hat pgvector Memory-Entry
- **Gate 4 Enforcement** — kein Prod-Deploy ohne GitHub Environment Approval
- **Post-Rollback-Health = 100%** — nach jedem Rollback läuft ein Health-Check

## Compliance

- **ADR-021**: Unified Deployment Pattern — `_deploy-unified.yml` als Basis, Expand-Contract (§2.16)
- **ADR-022**: Platform Consistency — `env_file` statt `${VAR}` interpolation
- **ADR-056**: Deployment Preflight — Pre-flight Checks in Phase 1
- **ADR-066**: AI Engineering Squad — Gate-System (Gate 4 = Human-Only für Prod), Deploy-Guardian als Rollen-Erweiterung
- **ADR-094**: Migration Conflict Resolution — `migrate --check` + GHCR-Pull (§2.4a) als Standard-Deploy
- **ADR-120**: Unified Deploy Pipeline — Reusable Workflow als Grundlage (amended by this ADR)
- **ADR-174**: QM Gate — Assumption Check als Teil von Pre-flight

## Drift-Detector Governance Note

```yaml
paths:
  - .github/workflows/_deploy-unified.yml
  - .github/workflows/complete-check.yml
  - /opt/scripts/deploy.sh
gate: APPROVE
```

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-05-06 | Achim Dehnert | Initial — Status: Proposed |
| 2026-05-06 | Achim Dehnert | Review v2: K1 SHA-Match-Check, K2 Rollback-Observability (GH Actions statt Discord), K3 .env-Konvention, K4 Deploy-Varianten (ref ADR-094 §2.4). V1-V10: amends ADR-120, Changelog, Deploy-Guardian Rolle, pgvector Schema, Phase-Abhängigkeiten, Worker-Shutdown, Migration-Safety, Trigger-Ist/Soll-Tabelle, IPs entfernt |
