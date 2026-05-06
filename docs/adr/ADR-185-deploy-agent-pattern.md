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
  - "Pilot: risk-hub/.github/workflows/complete-check.yml (Phase A — lokal, noch nicht gepusht)"
tags: [deployment, agent, automation, ci-cd]
---

# ADR-185: Adopt Gate-controlled Deploy-Agent for automated Staging→Prod deployments

## Scope

**Platform-weit** — gilt für alle 20+ IIL-Repos die `_deploy-unified.yml` (ADR-120) nutzen.
Implementierung als Reusable Workflows im `platform`-Repo + Erweiterung von `deploy.sh`.
Jedes Repo bindet die Workflows als Thin Caller ein (≤15 Zeilen pro Caller).

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
- Rollback-Observability: Audit-Trail + GitHub Actions Summary bei Rollback
- Einheitlicher Audit-Trail (pgvector + GitHub Actions Log)
- Kompatibilität mit existierender `_deploy-unified.yml` (ADR-120) — kein Parallel-System
- Gate-Modell konsistent mit ADR-066 (AI Engineering Squad)
- Platform-weite Standardisierung: ein Reusable Workflow für alle Repos

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
- **Con**: Kein Memory-Audit (pgvector), keine IDE-Integration, regelbasiert genügt aktuell (KI-basierte Failure-Analyse als Deferred Decision)

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
│  ├─ _complete-check.yml (Banned Patterns + Template Validation) │
│  ├─ python manage.py migrate --check (Migration-Konflikte)      │
│  └─ Bei Failure → STOP + GH Actions Annotation ❌               │
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
│  └─ Summary-Datei: /tmp/deploy-summary-$$.md                   │
│                                                                │
│  Phase 4: Staging Verification (Gate 0 — autonom)              │
│  ├─ verify-staging Job: HTTP 200 auf Health-URL                │
│  ├─ Container-Status-Check (kein unhealthy/exit/error)         │
│  └─ Bei Failure → STOP + GH Actions Annotation ❌               │
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
│  └─ Summary-Datei → GH Actions Job Summary                     │
│                                                                │
│  Phase 6: Audit (Gate 0 — autonom)                             │
│  ├─ pgvector: deploy.sh --audit → psql INSERT (auf Server)     │
│  ├─ GH Actions Job Summary mit Duration, Tag, Status           │
│  └─ GitHub Issue close (wenn Issue-triggered)                  │
└────────────────────────────────────────────────────────────────┘
```

### Tag-basierte Prod-Deploys: SHA-Match-Check

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
    - name: Login to GHCR
      run: echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin

    - name: Check if SHA was staged
      run: |
        SHA="${{ github.sha }}"
        SHORT="${SHA:0:7}"
        APP="${{ inputs.app_name }}"

        # Prüfe ob main-{sha} Image in GHCR existiert (= wurde gebaut + staged)
        if docker manifest inspect "ghcr.io/${{ github.repository_owner }}/${APP}:main-${SHORT}" >/dev/null 2>&1; then
          echo "✅ SHA ${SHORT} was previously staged (GHCR tag exists)"
        else
          echo "❌ SHA ${SHORT} was NEVER staged — blocking production deploy"
          exit 1
        fi

deploy-production:
  needs: [resolve, build, verify-staging-history]
  if: needs.verify-staging-history.result == 'success'
```

**Ausnahme**: `workflow_dispatch` mit `image_tag_override` (Rollback auf
bekanntes Image) überspringt den SHA-Match-Check — der Operator wählt
bewusst ein bekanntes Image.

### Environment-Datei-Konvention

Zwei Dateien mit verschiedenen Zwecken, konsistent über Staging und Prod:

| Datei | Zweck | Gelesen von | Inhalt |
|-------|-------|-------------|--------|
| `.env` | Compose-Interpolation | `docker compose` CLI | `IMAGE_TAG`, `GHCR_OWNER`, `GHCR_REPO`, `COMPOSE_PROJECT_NAME` |
| `.env.prod` / `.env.staging` | App-Secrets | Container (via `env_file:`) | `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, etc. |

**CRITICAL**: `deploy.sh` liest/schreibt `IMAGE_TAG` in `.env` (nicht `.env.prod`!):

```bash
# KORREKT (deploy.sh):
PREVIOUS_TAG=$(grep "^IMAGE_TAG=" "$APP_PATH/.env" | cut -d= -f2 || true)
sed -i "s|^IMAGE_TAG=.*|IMAGE_TAG=${IMAGE_TAG}|" "$APP_PATH/.env"
```

### Rollback-Observability

`deploy.sh` hat bereits Rollback-Logik (seit ADR-120/166: `trap rollback ERR`).
Was **fehlt** ist Observability — gelöst über **Summary-Datei + pgvector-Audit**:

#### Summary-Datei-Pattern (deploy.sh → GH Actions)

`GITHUB_STEP_SUMMARY` ist nur im GH Actions Runner verfügbar, nicht in SSH-Sessions.
Daher schreibt deploy.sh eine **Summary-Datei**, die der GH Actions Step danach liest:

```bash
# In deploy.sh (erweitert):
SUMMARY_FILE="/tmp/deploy-summary-${APP_NAME}-$$.md"

# Nach erfolgreichem Deploy:
cat > "$SUMMARY_FILE" <<EOF
## ✅ Deploy erfolgreich
- **App**: ${APP_NAME}
- **Tag**: ${IMAGE_TAG}
- **Environment**: ${ENVIRONMENT}
- **Vorheriger Tag**: ${PREVIOUS_TAG:-keiner}
- **Dauer**: ${SECONDS}s
EOF

# Nach Rollback (in rollback() Funktion):
cat > "$SUMMARY_FILE" <<EOF
## ⚠️ Rollback ausgeführt
- **App**: ${APP_NAME}
- **Fehlgeschlagener Tag**: ${IMAGE_TAG}
- **Rollback auf**: ${PREVIOUS_TAG}
- **Grund**: Health-Check fehlgeschlagen (exit $ec)
EOF
```

GH Actions Step liest die Datei:

```yaml
# In _deploy-unified.yml (nach deploy step):
- name: Publish deploy summary
  if: always()
  run: |
    SUMMARY="/tmp/deploy-summary-${{ inputs.app_name }}-*.md"
    if ls $SUMMARY 1>/dev/null 2>&1; then
      cat $SUMMARY >> "$GITHUB_STEP_SUMMARY"
      rm -f $SUMMARY
    fi
```

> **Für SSH-basierte Deploys** (Staging via appleboy/ssh-action): Summary-Datei
> muss via `scp` zurückgeholt werden, oder der SSH-Step parsed stdout.

#### pgvector-Audit via psql (deploy.sh --audit)

deploy.sh läuft auf dem Server, wo pgvector unter `127.0.0.1:15435` erreichbar ist:

```bash
# In deploy.sh (erweitert) — optionaler --audit Flag:
if [[ "${AUDIT:-false}" == "true" ]] && command -v psql >/dev/null 2>&1; then
  AUDIT_JSON=$(cat <<EOJSON
{"app":"${APP_NAME}","environment":"${ENVIRONMENT}","image_tag":"${IMAGE_TAG}",
 "previous_tag":"${PREVIOUS_TAG}","git_sha":"${GIT_SHA:-unknown}",
 "status":"${DEPLOY_STATUS}","duration_seconds":${SECONDS},
 "rollback_executed":${ROLLBACK_EXECUTED:-false},
 "trigger":"${DEPLOY_TRIGGER:-manual}"}
EOJSON
  )
  psql "postgresql://mcp_hub:${PGVECTOR_PASSWORD}@127.0.0.1:15435/mcp_hub" -c "
    INSERT INTO memory_entries (entry_key, entry_type, title, content, agent, tags, created_at)
    VALUES (
      'deploy:$(date +%Y-%m-%d):${APP_NAME}',
      'context',
      'Deploy ${APP_NAME}:${IMAGE_TAG} (${ENVIRONMENT})',
      '${AUDIT_JSON}',
      'deploy-guardian',
      ARRAY['deploy','${APP_NAME}','${ENVIRONMENT}','${DEPLOY_STATUS}'],
      NOW()
    ) ON CONFLICT (entry_key) DO UPDATE SET content=EXCLUDED.content, updated_at=NOW()
  " 2>/dev/null || echo "WARN: pgvector audit skipped"
fi
```

#### Post-Rollback-Health-Check

```bash
# In deploy.sh rollback() Funktion (erweitert):
# Nach Rollback: Health-Check auf alte Version
sleep 10
if [[ -n "$HEALTH_CHECK_URL" ]]; then
  HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_CHECK_URL" 2>/dev/null) || HTTP_CODE="000"
  if [[ "$HTTP_CODE" == "200" ]]; then
    echo "✅ Post-Rollback Health-Check OK (HTTP $HTTP_CODE)"
  else
    echo "::error::KRITISCH: Post-Rollback Health-Check fehlgeschlagen (HTTP $HTTP_CODE)!"
  fi
fi
```

### Worker Graceful Shutdown

Repos mit Celery-Workers werden sequentiell restartet. deploy.sh erkennt
Worker-Services dynamisch:

```bash
# In deploy.sh (erweitert):
WORKERS=$(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null \
  | grep -E 'worker|celery|beat' || true)

if [[ -n "$WORKERS" ]]; then
  # 1. Web-Service zuerst
  WEB_SERVICE=$(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null \
    | grep -E 'web$' | head -1)
  docker compose -f "$COMPOSE_FILE" pull
  docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "$WEB_SERVICE"
  _wait_for_health  # Health-Check
  # 2. Worker-Services danach
  for svc in $WORKERS; do
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate "$svc"
  done
else
  # Kein Worker → alles auf einmal
  docker compose -f "$COMPOSE_FILE" pull
  docker compose -f "$COMPOSE_FILE" up -d --force-recreate --remove-orphans
fi
```

### Deploy-Varianten (konsistent mit ADR-094 §2.4)

| Variante | Methode | Wann |
|----------|---------|------|
| **A: GHCR-Pull** (Standard) | `pull` + `up -d --force-recreate` | Normaler Deploy via CI/CD |
| **B: Lokaler Build** (Notfall) | `docker build` + `stop/rm` + `up -d` | Hotfix ohne CI |

### Trigger-Mechanismen (Ist → Soll)

| Trigger | Ist-Zustand | ADR-185 Soll | Transition |
|---------|------------|--------------|------------|
| `push main` | Staging (auto) | Staging (auto) | Keine Änderung |
| `push v*` tag | Direkt Prod | Prod **nur wenn SHA vorher staged** | Phase D: SHA-Match-Check |
| `workflow_dispatch` prod | Direkt Prod (erlaubt) | Nur mit `image_tag_override` (Rollback) | Phase D |
| `/ship` in IDE | SSH direkt auf Server | `workflow_dispatch` Trigger | Phase F |

### Migration-Safety

| Szenario | Risiko | Mitigation |
|----------|--------|------------|
| Migration schlägt in entrypoint fehl | Container crasht → Rollback-Trigger | deploy.sh `trap ERR` → Rollback auf PREVIOUS_TAG |
| Migration halb ausgeführt + Rollback | Alte Code-Version + teilweise neues DB-Schema | Expand-Contract-Pattern (ADR-021 §2.16) |
| `RunPython` mit DELETE/DROP | Datenverlust bei Rollback | "Was NICHT automatisiert wird" → manuell |

### Was NICHT automatisiert wird

- **Erste Deployments neuer Repos** — DNS, Nginx, SSL, deploy.sh Setup
- **DB-Migrationen mit Datenverlust** — `RunPython` mit `DELETE`/`DROP` → manuell
- **Major Version Upgrades** (Django 5→6, PostgreSQL 16→17) → manuelles Testing
- **Infrastruktur-Änderungen** (neue Server, Firewall-Rules, Cloudflare)
- **Secret-Rotation** — immer Gate 4, manuell

### Platform-weite Implementierung

#### Reusable Workflows (platform-Repo)

| Workflow | Inputs | Zweck |
|----------|--------|-------|
| `_complete-check.yml` | `template_dir`, `src_dir`, `settings_module`, `python_version` | Banned Patterns + Template Validation |
| `_deploy-unified.yml` (erweitert) | bestehende + `audit` | + verify-staging-history, Summary, Audit |

#### Caller-Template für Repos (≤15 Zeilen)

```yaml
# {repo}/.github/workflows/complete-check.yml
name: "Complete Check"
on:
  pull_request:
    branches: ["main"]
  workflow_dispatch:

jobs:
  check:
    uses: achimdehnert/platform/.github/workflows/_complete-check.yml@v1
    with:
      template_dir: "src/templates"   # repo-spezifisch
      src_dir: "src"                  # repo-spezifisch
      settings_module: "config.settings_test"
    secrets: inherit
```

#### Per-Repo Konfiguration (was variiert)

| Repo | `template_dir` | `src_dir` | `settings_module` | Workers |
|------|---------------|-----------|-------------------|---------|
| risk-hub | `src/templates` | `src` | `config.settings_test` | celery, celery_beat |
| travel-beat | `templates` | `.` | `config.settings` | celery |
| bfagent | `templates` | `.` | `config.settings` | worker |
| weltenhub | `templates` | `.` | `config.settings` | celery |
| billing-hub | `src/templates` | `src` | `config.settings_test` | — |

### Implementierung

| Phase | Inhalt | Wo | Abhängig von | Aufwand | Status |
|-------|--------|-----|-------------|---------|--------|
| A | `complete-check.yml` risk-hub (Pilot) auf GitHub pushen | risk-hub | — | 0.5h | ⬜ pending |
| B | `_complete-check.yml` als Reusable Workflow + Caller-Templates | platform + alle Repos | A | 3h | ⬜ pending |
| C | deploy.sh: Summary-Datei, Post-Rollback-Health, Worker-Discovery | Server (Prod+Staging) | — | 3h | ⬜ pending |
| D | `_deploy-unified.yml`: verify-staging-history, Summary-Transfer | platform | B, C | 2h | ⬜ pending |
| E | deploy.sh --audit (pgvector via psql) | Server | C | 2h | ⬜ pending |
| F | `/ship` Integration (workflow_dispatch statt SSH) | platform + IDE | D | 3h | ⬜ pending |

> **Gesamt**: ~14h, verteilt über 3–4 Sessions.
> **Kritischer Pfad**: A → B → D → F (complete-check → unified → ship)
> **Paralleler Pfad**: C → E (deploy.sh unabhängig von Workflows)

## Consequences

### Positive

- Platform-weit einheitlich: ein Reusable Workflow für alle 20+ Repos
- Staging wird nie mehr übersprungen (SHA-Match-Check)
- Rollback-Observability: Summary-Datei + pgvector-Audit + Post-Rollback-Health
- Audit-Trail in pgvector + GitHub Actions Log
- Gate 4 für Prod ist platform-weit konsistent (ADR-066)
- Worker-Graceful-Shutdown: Web zuerst, dann Worker (kein Task-Abbruch)
- Baut auf existierender Infrastruktur auf (kein Parallel-System)

### Negative

- Erfordert zuverlässige `/healthz/` Endpoints in jedem Repo (ADR-167: ✅ alle 19 Repos)
- GitHub Environment Protection Rules müssen pro Repo eingerichtet werden
- Rollback funktioniert nur wenn GHCR das vorherige Image noch hat
- SHA-Match-Check fügt ~10s Latenz zu Tag-basierten Deploys hinzu
- pgvector-Audit braucht `psql` + Credentials auf dem Server

### Risiken

| Risiko | Schwere | Mitigation |
|--------|---------|------------|
| Health-Check false positive | HIGH | `/healthz/` prüft DB + Redis (nicht nur HTTP) |
| Approval-Request wird übersehen | MEDIUM | GH Actions "Waiting for review" + 72h Timeout |
| GHCR Image-Retention löscht altes Image | LOW | GHCR retention policy: ≥10 Tags behalten |
| Staging-Env driftet von Prod | MEDIUM | Gleiche Compose-Struktur, gleiche `.env`-Keys |
| Gleichzeitige Deploys (Race Condition) | MEDIUM | `concurrency` group (`deploy-{app}-{env}`) |
| Migration halb ausgeführt + Rollback | HIGH | Expand-Contract-Pattern (ADR-021 §2.16) |
| Worker-Tasks abgebrochen bei Restart | MEDIUM | Web zuerst, Worker danach; Tasks idempotent |
| Summary-Datei bei SSH-Deploy nicht verfügbar | MEDIUM | Stdout-Parsing als Fallback |

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum |
|--------------|------------|-----------|
| KI-basierte Failure-Analyse | Deploy-Agent ist aktuell regelbasiert. LLM-Analyse bei Rollback als Erweiterung | 2026-Q3 |
| Canary-Deploy | `deployment-mcp` hat `canary_deploy` — evaluieren bei >100 Users | 2026-Q3 |
| Playwright Smoke-Test in CI | Browser-Test in CI erfordert Playwright Docker-Setup | 2026-Q3 |
| Multi-Server-Deploy | Aktuell Single-Server — bei Skalierung erweitern | 2026-Q4 |
| Celery SIGTERM Grace Period | `--pool=prefork` mit konfigurierbarer Grace Period | 2026-Q3 |

## Glossar

| Begriff | Erklärung |
|---------|-----------|
| **Gate** | Kontrollstufe im Agent-Workflow (Gate 0=autonom, Gate 4=nur Mensch). ADR-066 §Gate-System |
| **Deploy-Guardian** | Regelbasierte Erweiterung der Guardian-Rolle (ADR-066) für Deployment-Checks. Kein LLM |
| **Pre-flight** | Automatische Prüfungen VOR dem Deploy (Tests, Lint, Migration-Check) |
| **Health-Check** | HTTP-Abfrage an `/livez/` (Liveness) und `/healthz/` (Readiness inkl. DB+Redis) |
| **Rollback** | Zurücksetzen auf vorherige Version. Implementiert in `deploy.sh` via `trap rollback ERR` |
| **GHCR** | GitHub Container Registry — `ghcr.io/achimdehnert/{app}` |
| **SHA-Match-Check** | Verifikation dass ein Git-SHA vorher auf Staging deployed wurde (GHCR manifest inspect) |
| **Summary-Datei** | `/tmp/deploy-summary-{app}-{pid}.md` — deploy.sh Output für GH Actions Job Summary |
| **.env** | Compose-Interpolationsdatei (`IMAGE_TAG`, `GHCR_OWNER`). Nicht `.env.prod` (App-Secrets) |
| **Reusable Workflow** | Zentraler Workflow in `platform` — Repos binden ihn als Thin Caller ein |

## Confirmation

- **Staging-Skip-Rate = 0%** — kein Prod-Deploy ohne SHA-Match-Check
- **Rollback-Observability = 100%** — jeder Rollback hat Summary-Datei + pgvector Entry
- **Audit-Coverage = 100%** — jeder Deploy hat pgvector Memory-Entry (deploy.sh --audit)
- **Gate 4 Enforcement** — kein Prod-Deploy ohne GitHub Environment Approval
- **Post-Rollback-Health = 100%** — nach jedem Rollback läuft ein Health-Check
- **Platform-Adoption ≥ 80%** — mindestens 16 von 20 Repos nutzen `_complete-check.yml` (Phase B)

## Compliance

- **ADR-021**: Unified Deployment Pattern — Expand-Contract (§2.16)
- **ADR-022**: Platform Consistency — `env_file` statt `${VAR}` interpolation
- **ADR-056**: Deployment Preflight — Pre-flight Checks in Phase 1
- **ADR-066**: AI Engineering Squad — Gate-System, Deploy-Guardian Rolle
- **ADR-094**: Migration Conflict Resolution — `migrate --check` + GHCR-Pull (§2.4a)
- **ADR-120**: Unified Deploy Pipeline — Reusable Workflow als Grundlage (amended)
- **ADR-167**: Three-Tier Middleware — `/healthz/` in allen 19 Repos vorhanden
- **ADR-174**: QM Gate — Assumption Check als Teil von Pre-flight

## Drift-Detector Governance Note

```yaml
paths:
  - .github/workflows/_deploy-unified.yml
  - .github/workflows/_complete-check.yml
  - /opt/scripts/deploy.sh
gate: APPROVE
```

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-05-06 | v1 | Initial — Status: Proposed |
| 2026-05-06 | v2 | K1 SHA-Match-Check, K2 Rollback-Observability, K3 .env-Konvention, K4 Deploy-Varianten |
| 2026-05-06 | v3 | Platform-weite Standardisierung: Reusable Workflow `_complete-check.yml`, Summary-Datei-Pattern (GITHUB_STEP_SUMMARY Workaround), pgvector-Audit via psql, Worker-Discovery, Per-Repo Config-Tabelle, SSH-Deploy Summary-Transfer, Phase A korrigiert (noch nicht gepusht), Aufwandsschätzung |
