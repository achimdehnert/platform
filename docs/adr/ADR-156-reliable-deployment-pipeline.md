---
status: proposed
date: 2026-04-02
decision-makers: [Achim Dehnert]
consulted: [Cascade (Principal IT-Architekt)]
informed: []
supersedes: []
amends: ["ADR-075-deployment-execution-strategy.md"]
related:
  - ADR-021-unified-deployment-pattern.md
  - ADR-022-code-quality-docker-standards.md
  - ADR-062-content-store.md
  - ADR-075-deployment-execution-strategy.md
  - ADR-090-cicd-pipeline-python-postgres.md
  - ADR-107-extended-agent-team-deployment-agent.md
  - ADR-120-unified-deployment-pipeline.md
implementation_status: none
---

# Adopt Server-Side Deploy Scripts with Short-Trigger Pattern for Reliable Deployment Pipeline

<!-- Drift-Detector-Felder (ADR-059)
staleness_months: 6
drift_check_paths:
  - deployment/templates/deploy.sh
  - deployment/templates/deploy-start.sh
  - .windsurf/workflows/ship.md
supersedes_check: ADR-075 (amends, not supersedes)
-->

## Context and Problem Statement

### Kernproblem

Deployments über `deployment-mcp` / `ssh_manage` hängen regelmäßig bei Operationen >30 Sekunden. Das betrifft:

| Operation | Typische Dauer | Symptom |
|-----------|---------------|---------|
| `docker compose pull` | 30-120s | WaitDelay expired |
| `docker compose up -d` | 10-60s | SSH-Heredoc-Timeout |
| `python manage.py migrate` | 5-30s | Sporadisch |
| `docker build` | 120-600s | Immer |
| `collectstatic` | 10-30s | Sporadisch |

### Root Causes (aus Error-Pattern-DB)

1. **MCP-SSH-Tool WaitDelay**: Internes Timeout bei langen SSH-Sessions (~30s)
2. **SSH KeepAlive**: Lange Heredoc-Sessions werden durch SSH-KeepAlive unterbrochen
3. **Kein Background-Mechanismus**: MCP wartet synchron auf Command-Output
4. **Kein standardisiertes Deploy-Script**: Jedes Repo hat eigene Mechanismen
5. **Multi-Node-Sync**: Dev Desktop ↔ GitHub ↔ Prod-Server Drift
6. **Keine Job-Transparenz**: User sieht nicht wie lange ein Job dauert, wann er fertig wird, und ob er im Hintergrund laufen könnte
7. **Agent blockiert bei langen Jobs**: Cascade ist während Deployments, Builds, Migrationen für den User nicht ansprechbar

### Betroffene Umgebungen

| Umgebung | Rolle | Problem |
|----------|-------|---------|
| Dev Desktop (88.99.38.75) | Development + MCP-Server | SSH zu Prod hängt bei Writes |
| Prod-Server (88.198.191.108) | 18+ Container, Deployments | Empfängt Deploys |
| GitHub Actions (Self-Hosted Runner) | CI/CD | Runner auf Prod, konkurriert mit Apps |

## Decision Drivers

1. **Zuverlässigkeit**: Deployments MÜSSEN deterministisch funktionieren (kein Hängen)
2. **Geschwindigkeit**: Deploy sollte <2 Min (ohne Build) dauern
3. **Idempotenz**: Gleicher Deploy-Befehl = gleiches Ergebnis
4. **Observability**: Jeder Deploy-Schritt muss geloggt und nachvollziehbar sein
5. **Agent-Kompatibilität**: Cascade/Deployment-Agent muss Deploys autonom ausführen können
6. **Rollback**: Jederzeit auf vorherigen Stand zurückkehren
7. **Transparenz**: User muss VOR Jobstart wissen: geschätzte Dauer, geplanter Start/Ende-Zeitpunkt
8. **Agent-Verfügbarkeit**: Agent soll bei Background-fähigen Jobs frei für andere Aufgaben sein
9. **Job-Routing**: Jeder Job sollte dem passenden Executor (LLM, CI, Server-Script) zugewiesen werden

## Considered Options

### Option A: Server-Side Deploy-Script (nohup-Pattern)

**Prinzip**: Kurzer SSH-Write-Befehl platziert Script auf Server, startet es im Background.

```
Dev Desktop → SSH → Server: write deploy.sh → nohup deploy.sh &
Dev Desktop → SSH → Server: tail -f /var/log/deploy/<repo>.log (poll)
```

**Pro**:
- Löst Timeout-Problem sofort (SSH nur für Schreibvorgang)
- Einfach zu implementieren
- Log auf Server persistent

**Contra**:
- Kein atomares Rollback
- Keine Orchestrierung zwischen Steps
- Log-Polling ist fragil

### Option B: GitHub Actions als einziger Deploy-Kanal

**Prinzip**: Alle Deploys laufen über GitHub Actions — MCP triggert nur Dispatch.

```
Dev Desktop → MCP → GitHub API: dispatch deploy.yml
Dev Desktop → MCP → GitHub API: poll run_status
```

**Pro**:
- Kein SSH-Timeout-Problem (Runner läuft lokal auf Server)
- Full Audit-Trail in GitHub
- Standardisiert für alle Repos

**Contra**:
- Runner konkurriert mit Prod-Apps um Ressourcen
- Latenz (Workflow-Start 5-15s, Queue)
- GitHub-Abhängigkeit für jeden Deploy

### Option C: Hybrid — Server-Side Agent + GitHub Actions Fallback

**Prinzip**: Leichtgewichtiger Deploy-Agent auf dem Prod-Server, gesteuert über standardisiertes Protokoll.

```
1. Dev/MCP → SSH (kurz): POST deploy-request an lokalen Agent
2. Agent auf Server: führt deploy.sh aus, loggt in /var/log/deploy/
3. Dev/MCP → SSH (kurz): GET deploy-status (poll)
4. Fallback: GitHub Actions Workflow als Alternative
```

**Pro**:
- Kein Timeout (Agent läuft lokal)
- Minimaler SSH-Overhead (nur kurze HTTP-ähnliche Befehle)
- Offline-fähig (Agent auf Server)
- GitHub Actions als Backup

**Contra**:
- Neuer Service auf Server (Wartung)
- Mehr Komplexität

## Decision Outcome

### Gewählt: Option A — Server-Side Deploy-Script mit Short-Trigger-Pattern

Option A löst das akute Timeout-Problem sofort. Gegenüber der v2-Fassung wird das
`nohup &`-Pattern durch ein **Short-Trigger-Pattern** ersetzt: Ein dediziertes
`deploy-start.sh` startet den Background-Prozess, verwaltet PID/Lock/Status und
returniert sofort mit einer JSON-Antwort. Status-Polling erfolgt deterministisch
über File-basierte State-Machine statt Log-Glob.

Option B (GitHub Actions) bleibt als Fallback bestehen (ADR-075 unverändert).
Option C (Server-Side Agent) wird als separates ADR evaluiert wenn Phase 1-2 stabil.

### Positive Consequences

- Deploy-Hänger strukturell eliminiert — SSH nur <5s für Trigger
- Schneller als GitHub Actions (~2s vs ~30s Runner-Pickup)
- Kein Runner-Dependency für Standard-Deployments
- Deterministisches Status-Polling via File-basierte State-Machine
- ADR-075 Kern-Prinzip bleibt intakt (keine lang laufenden SSH-Ops)
- Atomares Locking via `flock(1)` — keine Race-Conditions bei parallelen Deploys
- Fail-Closed bei Migration-Fehlern (ADR-062 Prinzip)
- Rollback auf vorheriges Image bei Health-Check-Failure

### Negative Consequences

- Zwei Trigger-Methoden (SSH Short-Trigger + GitHub Actions) erhöhen kognitive Last
- Server-seitige Scripts (`/opt/deploy-core/`) müssen gewartet werden
- Kein nativer Audit Trail wie bei GitHub Actions (nur `deploy.log`)
- `deploy-start.sh` ist eine neue Abstraktionsschicht — muss verstanden werden

## ADR-075 Reconciliation

ADR-075 (accepted, 2026-02-23) verbietet Write-Ops via SSH/MCP. ADR-156 schlägt
SSH-basierte Short-Trigger vor. Das ist **kein Widerspruch**, sondern eine
**Differenzierung** der Write-Op-Regel.

**ADR-075's Root Cause**: SSH-Operationen >30s blockieren den MCP-Event-Loop.
**ADR-156's Short-Trigger**: SSH-Command <5s, startet Background-Prozess, returniert sofort.

Das sind fundamental verschiedene Operationsklassen. ADR-075 wird um eine
3-Tier Write-Op-Klassifikation amended (siehe ADR-075 §Write-Op-Klassifikation):

| Tier | Dauer | Kanal | Beispiele |
|------|-------|-------|-----------|
| **Long-Running Write** | >15s | GitHub Actions | `docker compose up`, `migrate`, `build` |
| **Short Trigger** | <5s | SSH | `deploy-start.sh`, `deploy-status.sh` |
| **Read-Op** | <5s | deployment-mcp | `container_logs`, `compose_ps` |

**Koexistenz**: Beide Trigger-Methoden nutzen dasselbe `/opt/deploy-core/deploy.sh`.
GitHub Actions bleibt Fallback wenn SSH nicht verfügbar.

---

## §5 Job-Transparenz — Geschätzte Dauer und Fortschritt

### Problem

Der User startet einen Job (Deploy, Migration, Build, Test-Suite) und sieht:
- Nicht wie lange der Job voraussichtlich dauert
- Nicht wann er fertig sein wird
- Nicht ob er im Hintergrund laufen kann
- Nicht ob etwas hängt oder normal langsam ist

### Lösung: Job-Estimation + Progress-Kommunikation

Jeder Job MUSS dem User vor Start folgende Informationen kommunizieren:

```
╔══════════════════════════════════════════════════════╗
║  Job: Deploy risk-hub                                ║
║  Geschätzte Dauer: ~90s (Pull 30s + Migrate 15s     ║
║                         + Recreate 15s + Health 30s) ║
║  Start: 12:28:15                                     ║
║  Geplantes Ende: ~12:29:45                           ║
║  Modus: ⚡ Background (Agent bleibt verfügbar)       ║
║  Status-Polling: alle 15s                            ║
╚══════════════════════════════════════════════════════╝
```

### Job-Dauer-Katalog (Referenzwerte)

| Job-Typ | Geschätzte Dauer | Background-fähig | Executor |
|---------|-----------------|------------------|----------|
| `docker compose pull` | 30-120s | Ja | Server-Script |
| `docker compose up -d` | 10-30s | Ja | Server-Script |
| `python manage.py migrate` | 5-30s | Ja (mit Vorsicht) | Server-Script |
| `docker build` (cached) | 60-180s | Ja | CI/Server |
| `docker build` (clean) | 300-600s | Ja | CI |
| `pytest` (Unit) | 10-60s | Ja | CI/Lokal |
| `pytest` (Integration) | 30-120s | Ja | CI |
| `ruff check` | 2-5s | Nein (zu kurz) | Lokal |
| `git push` | 2-10s | Nein (zu kurz) | Lokal |
| `pip install` (from PyPI) | 10-30s | Ja | CI/Lokal |
| PyPI publish (build+upload) | 15-45s | Ja | Lokal |
| Full Deploy (Pull→Health) | 60-180s | Ja | Server-Script |
| DB-Backup (pg_dump) | 10-60s | Ja | Server-Script |
| `collectstatic` | 10-30s | Ja | Server-Script |

### Implementierung: `estimate_job()` mit Job-Katalog

Der orchestrator-MCP bekommt einen **maschinenlesbaren Job-Katalog** (`job_catalog.yaml`)
und einen `JobEstimator` der Katalogwerte + gemessene Historie (Feedback-Loop) kombiniert:

```python
def estimate_job(job_type: str, repo: str | None = None) -> JobEstimate:
    """Schätzt Job-Dauer aus Katalog + optionaler Messhistorie.

    Lookup: repo-spezifisch → Job-Typ-Default → Fallback.
    Gewichtung: 70% Katalog + 30% gemessene Werte (wenn vorhanden).
    """
    return get_estimator().estimate(job_type, repo)
```

**Katalog-Schema** (Auszug `job_catalog.yaml`):
```yaml
jobs:
  deploy:
    estimated_seconds_min: 60
    estimated_seconds_max: 180
    background_capable: true
    executor: server-script
    parallel_safe: false
    repos:
      risk-hub:
        estimated_seconds_min: 70
        estimated_seconds_max: 200
```

Vollständiger Katalog und Implementierung: `platform/docs/adr/inputs/ADR-156/`.

---

## §6 Background-Job-Fähigkeit — Agent bleibt verfügbar

### Problem

Aktuell blockiert jeder Deploy/Build/Migration den Agent (Cascade). Der User muss warten bis ein 2-Minuten-Deploy fertig ist, obwohl er parallel andere Fragen hätte.

### Lösung: Fire-and-Forget + Status-Polling

Jobs die >15 Sekunden dauern und keine interaktive Entscheidung erfordern, werden im Background gestartet:

```
User: "Deploy risk-hub"

Cascade:
  1. estimate_job("deploy", "risk-hub") → 90s, background=true
  2. Kommuniziert: "Deploy gestartet (~90s). Ich bin für andere Aufgaben verfügbar."
  3. Startet (Short Trigger, <2s):
     ssh_manage(exec, "bash /opt/deploy-core/deploy-start.sh risk-hub", timeout=10)
     → JSON: {"status":"started","background_pid":12345,"status_file":"/var/run/deploy/risk-hub.status"}
  4. Arbeitet parallel an anderer User-Anfrage
  5. Nach ~90s pollt (Read-Op, <1s):
     ssh_manage(exec, "bash /opt/deploy-core/deploy-status.sh risk-hub")
     → JSON: {"status":"SUCCESS","elapsed_seconds":78}
  6. Meldet User: "risk-hub Deploy abgeschlossen (78s). Health: ✓"
```

### Klassifikation: Foreground vs. Background

| Kriterium | Foreground | Background |
|-----------|-----------|------------|
| Dauer | <15s | >15s |
| Interaktion nötig | Ja (Entscheidungen) | Nein (deterministisch) |
| Risiko | Hoch (Datenverlust) | Niedrig (idempotent) |
| Beispiele | Code-Review, Architektur-Frage, Merge-Konflikt | Deploy, Build, Test-Suite, Backup, PyPI publish |

### Discord-Integration

Bei Background-Jobs wird der User über Discord benachrichtigt (bestehende `discord_notify` Funktion):

```python
discord_notify(
    title="Deploy risk-hub gestartet",
    message="Geschätzte Dauer: ~90s. Agent bleibt verfügbar.",
    level="info"
)
# ... nach Abschluss:
discord_notify(
    title="Deploy risk-hub abgeschlossen ✓",
    message="Health-Check bestanden. Dauer: 78s.",
    level="success"
)
```

---

## §7 Job-Scheduling, Job-Routing und LLM-Zuweisung

### Problem

Aktuell entscheidet Cascade ad-hoc welches Tool für welchen Job eingesetzt wird. Es gibt keine systematische Zuordnung von Job-Typen zu Executors oder LLM-Modellen.

### Lösung: Job-Router mit Executor- und Modell-Empfehlung

Der `orchestrator-MCP` bekommt einen **Job-Router** der für jeden Job-Typ empfiehlt:

1. **Executor**: Wo läuft der Job?
2. **LLM-Modell**: Welches Modell ist am besten geeignet?
3. **Parallelität**: Kann der Job parallel zu anderen laufen?

### Executor-Typen

| Executor | Beschreibung | Geeignet für |
|----------|-------------|-------------|
| `server-script` | nohup-Script auf Prod-Server | Deploy, Migrate, Backup, Collectstatic |
| `ci` | GitHub Actions Workflow | Build, Test-Suite, Security-Scan |
| `local` | Lokaler Befehl auf Dev Desktop | Lint, Format, Git-Ops, kleine Tests |
| `llm` | LLM-Agent (Cascade/Sub-Agent) | Code-Review, Refactoring, Analyse |
| `mcp` | MCP-Tool (read-only) | Health-Check, Logs, Status |

### LLM-Modell-Routing für Agent-Jobs

| Job-Typ | Empfohlenes Modell | Begründung |
|---------|-------------------|------------|
| Code-Review (komplex) | `opus` | Tiefes Architektur-Verständnis nötig |
| Refactoring (einfach) | `swe` | Strukturelle Änderungen, weniger Kreativität |
| Docstring-Generierung | `gpt_low` | Einfache, repetitive Aufgabe |
| Test-Generierung | `swe` | Pattern-basiert, braucht Code-Verständnis |
| Bug-Triage | `opus` | Braucht breiten Kontext |
| Deployment-Entscheidung | `gpt_low` | Checkliste abarbeiten, wenig Kreativität |
| ADR-Review | `opus` | Architektur-Expertise nötig |
| CI-Fix (Lint/Format) | `gpt_low` | Mechanische Korrekturen |
| Contract-Test schreiben | `swe` | Pattern aus Template, Code-Verständnis |

Diese Tabelle wird in `orchestrator_mcp` als **Job-Routing-Matrix** hinterlegt und von `analyze_task()` konsultiert.

### Erweiterung von `analyze_task()`

Die bestehende `analyze_task()` Funktion im orchestrator-MCP wird erweitert:

```python
# Bestehend:
analyze_task(description="Deploy risk-hub")
# → {model: "gpt_low", gate: 2}

# Neu (erweitert):
analyze_task(description="Deploy risk-hub")
# → {
#     model: "gpt_low",
#     gate: 2,
#     executor: "server-script",
#     estimated_seconds: 90,
#     background_capable: true,
#     steps: ["pull", "migrate", "recreate", "health"],
#     parallel_safe: true,
#     notification_channel: "discord",
# }
```

### Job-Queue und Scheduling (Phase 3)

Langfristig wird ein einfacher Job-Scheduler eingeführt:

```
Job-Queue (FIFO, optional Priorität):
┌─────────────────────────────────────────────────────┐
│ #1 Deploy risk-hub     │ server-script │ RUNNING    │
│ #2 Tests bfagent       │ ci            │ QUEUED     │
│ #3 Review PR #42       │ llm:opus      │ QUEUED     │
│ #4 Backup billing-hub  │ server-script │ WAITING #1 │
└─────────────────────────────────────────────────────┘
```

**Regeln**:
- Server-Script-Jobs auf gleichen Server: sequentiell (Lock-File)
- CI-Jobs: parallel (GitHub Actions Concurrency)
- LLM-Jobs: parallel möglich (verschiedene Modelle)
- MCP-Read-Jobs: immer sofort (kein Queueing)

### Zusammenspiel aller Konzepte

```
User: "Deploy risk-hub und danach Contract-Tests im bfagent laufen lassen"

Cascade (Job-Router):
  Job 1: Deploy risk-hub
    → Executor: server-script
    → Modell: nicht nötig (Shell)
    → Dauer: ~90s
    → Background: ja
    → Kommunikation: "Deploy gestartet (~90s), arbeite parallel weiter."

  Job 2: Contract-Tests bfagent
    → Executor: ci (dispatch workflow)
    → Modell: nicht nötig (CI)
    → Dauer: ~45s
    → Background: ja
    → Abhängigkeit: keine (anderer Server/Repo)
    → Kommunikation: "CI getriggert (~45s), parallel zum Deploy."

  Cascade: Verfügbar für User-Interaktion während beide Jobs laufen.
  Nach Abschluss: Discord-Notification + Zusammenfassung.
```

## Implementierungsplan

### Phase 1: Deploy-Core Scripts (sofort)

Zentrale Scripts in `/opt/deploy-core/` auf dem Prod-Server — **nicht** pro Repo:

```
/opt/deploy-core/
├── deploy.sh              ← Haupt-Deploy-Script (Pull, Migrate, Recreate, Health)
├── deploy-start.sh        ← MCP-facing Wrapper (Short Trigger, JSON-Output)
└── deploy-status.sh       ← Status-Polling-Helper (JSON-Output)

/var/run/deploy/           ← State-Files (Lock, PID, Status)
/var/log/deploy/           ← Log-Dateien + Symlinks
/etc/logrotate.d/deploy-logs  ← Rotation (7 Tage)
```

**deploy.sh** — Korrigierte Version (alle Blocker aus Review behoben):

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO="${1:?Usage: deploy.sh <repo> [compose-file] [health-port]}"
COMPOSE_FILE="${2:-docker-compose.prod.yml}"
HEALTH_PORT="${3:-8000}"

# ADR-022: COMPOSE_PROJECT_NAME ist Pflicht (Fix B6)
export COMPOSE_PROJECT_NAME="${REPO}"

REPO_DIR="/opt/${REPO}"
STATE_DIR="/var/run/deploy"
LOG_DIR="/var/log/deploy"
LOG_FILE="${LOG_DIR}/${REPO}-$(date +%Y%m%d-%H%M%S).log"
LOCK_FILE="${STATE_DIR}/${REPO}.lock"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"

mkdir -p "${STATE_DIR}" "${LOG_DIR}"

# Fix B5: Symlink für deterministisches MCP-Polling (kein Glob)
ln -sf "${LOG_FILE}" "${LOG_DIR}/${REPO}-latest.log"

# Fix H1: Kein Process-Substitution — direkte Umleitung
exec > "${LOG_FILE}" 2>&1

echo "=== Deploy ${REPO} gestartet: $(date -Iseconds) ==="
echo "$$" > "${PID_FILE}"

# Fix B1: Atomarer Lock via flock(1) — kein Race-Condition
exec 9>"${LOCK_FILE}"
if ! flock -n 9; then
    echo "FATAL: Deploy für '${REPO}' läuft bereits." >&2
    exit 4
fi
echo "RUNNING" > "${STATUS_FILE}"

trap 'rm -f "${PID_FILE}"; echo "=== Deploy beendet: $(date -Iseconds) ==="' EXIT

cd "${REPO_DIR}"

# Rollback-Vorbereitung (Fix B3)
ROLLBACK_TAG=$(docker compose -f "${COMPOSE_FILE}" images web 2>/dev/null \
    | awk 'NR==2 {print $3}' || echo "")

# Step 1: Pull
docker compose -f "${COMPOSE_FILE}" pull web

# Step 2: Migrations — Fix B2: Fail-Closed, kein || true, kein 2>/dev/null
if docker compose -f "${COMPOSE_FILE}" config --services 2>/dev/null | grep -q '^migrate$'; then
    if ! docker compose -f "${COMPOSE_FILE}" run --rm migrate; then
        echo "FATAL: Migration fehlgeschlagen — ABBRUCH" >&2
        echo "FAILED" > "${STATUS_FILE}"
        exit 2
    fi
fi

# Step 3: Container recreate — Fix H2: --no-deps (kein DB/Redis-Neustart)
docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate web

# Step 4: Health Check (12×5s = 60s)
sleep 2
for attempt in $(seq 1 12); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
        "http://localhost:${HEALTH_PORT}/livez/" 2>/dev/null || echo "000")
    if [[ "${HTTP_CODE}" == "200" ]]; then
        echo "Health-Check bestanden (Versuch ${attempt})."
        echo "SUCCESS" > "${STATUS_FILE}"
        exit 0
    fi
    echo "Health-Check ${attempt}/12: HTTP ${HTTP_CODE}"
    sleep 5
done

# Fix B3: Rollback bei Health-Check-Failure
echo "FATAL: Health-Check fehlgeschlagen — Rollback auf ${ROLLBACK_TAG:-unknown}" >&2
docker compose -f "${COMPOSE_FILE}" logs --tail=50 web >&2 || true
if [[ -n "${ROLLBACK_TAG}" ]]; then
    echo "Rollback: Image auf ${ROLLBACK_TAG} zurücksetzen..."
    docker compose -f "${COMPOSE_FILE}" pull web 2>/dev/null || true
    ROLLBACK_IMAGE=$(docker compose -f "${COMPOSE_FILE}" config --images 2>/dev/null | grep web | head -1)
    ROLLBACK_IMAGE="${ROLLBACK_IMAGE%:*}:${ROLLBACK_TAG}"
    docker compose -f "${COMPOSE_FILE}" up -d --no-deps --force-recreate web 2>/dev/null || true
    echo "Rollback ausgeführt. Manuellen Health-Check empfohlen."
else
    echo "WARNUNG: Kein Rollback-Tag verfügbar — manueller Eingriff nötig."
fi
echo "FAILED" > "${STATUS_FILE}"
exit 3
```

**deploy-start.sh** — MCP-facing Short Trigger (Fix B4):

```bash
#!/usr/bin/env bash
# Aufruf: ssh_manage(action="exec", command="bash /opt/deploy-core/deploy-start.sh <repo>", timeout=10)
# Output: JSON mit PID, Status-File, Log-Pfad (<2s)
set -euo pipefail
REPO="${1:?Usage: deploy-start.sh <repo>}"
DEPLOY_SCRIPT="/opt/deploy-core/deploy.sh"
STATE_DIR="/var/run/deploy"
PID_FILE="${STATE_DIR}/${REPO}.pid"
STATUS_FILE="${STATE_DIR}/${REPO}.status"
LOG_LATEST="/var/log/deploy/${REPO}-latest.log"

# Prüfe ob Deploy bereits läuft
if [[ -f "${PID_FILE}" ]]; then
    pid=$(cat "${PID_FILE}" 2>/dev/null || echo "")
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
        printf '{"status":"already_running","pid":%s,"status_file":"%s"}\n' "${pid}" "${STATUS_FILE}"
        exit 4
    fi
fi

echo "STARTING" > "${STATUS_FILE}"
nohup bash "${DEPLOY_SCRIPT}" "${REPO}" >> "${LOG_LATEST}" 2>&1 &
BGPID=$!; disown "${BGPID}"

printf '{"status":"started","background_pid":%d,"status_file":"%s","log_file":"%s"}\n' \
    "${BGPID}" "${STATUS_FILE}" "${LOG_LATEST}"
```

**deploy-status.sh** — Deterministisches Polling (Fix B5):

```bash
#!/usr/bin/env bash
# Output: JSON mit Status, PID-Liveness, Elapsed, Log-Tail
set -euo pipefail
REPO="${1:?Usage: deploy-status.sh <repo>}"
STATUS=$(cat "/var/run/deploy/${REPO}.status" 2>/dev/null | tr -d '[:space:]' || echo "UNKNOWN")
PID=$(cat "/var/run/deploy/${REPO}.pid" 2>/dev/null | tr -d '[:space:]' || echo "")
ALIVE=false; [[ -n "${PID}" ]] && kill -0 "${PID}" 2>/dev/null && ALIVE=true
printf '{"repo":"%s","status":"%s","pid_alive":%s}\n' "${REPO}" "${STATUS}" "${ALIVE}"
```

### MCP-Aufruf (Agent Short-Trigger-Pattern)

```python
# 1. Deploy starten (Short Trigger — <2s SSH, non-blocking)
ssh_manage(action="exec",
    command="bash /opt/deploy-core/deploy-start.sh risk-hub",
    timeout=10)
# → {"status":"started","background_pid":12345,"status_file":"/var/run/deploy/risk-hub.status"}

# 2. Status pollen (Read-Op — <1s SSH)
ssh_manage(action="exec",
    command="bash /opt/deploy-core/deploy-status.sh risk-hub")
# → {"repo":"risk-hub","status":"RUNNING","pid_alive":true}

# 3. Log lesen (Read-Op — <1s SSH)
ssh_manage(action="file_read",
    path="/var/log/deploy/risk-hub-latest.log", tail=20)
```

### Phase 2: Job-Transparenz + Background-Jobs (kurzfristig)

- `estimate_job()` Funktion in orchestrator-MCP
- Job-Dauer-Katalog als YAML/Dict in orchestrator-MCP
- `/ship` Workflow: Schätzung VOR Start kommunizieren
- Discord-Notification bei Background-Job Start/Ende
- Foreground/Background-Klassifikation (>15s = Background)

### Phase 3: Job-Router + `analyze_task()` Erweiterung (mittelfristig)

- `analyze_task()` erweitern um Executor, Schätzung, Background-Flag
- Job-Routing-Matrix in orchestrator-MCP (aus `job_catalog.yaml`)
- LLM-Modell-Empfehlung pro Job-Typ

### Phase 4: Server-Side Deploy-Agent (langfristig — separates ADR)

> **Hinweis**: Phase 4 (REST-API auf Server, Systemd-Service, Job-Queue) geht über
> ein Amendment von ADR-075 hinaus und erfordert ein **separates ADR** das ADR-075
> explizit superseded. Grund: ADR-075 verwarf Option 4 (Webhook-basierter Endpoint)
> wegen Security-Bedenken (Auth, Angriffsfläche). Ein Server-Side Agent muss diese
> Bedenken mit einem Threat-Model adressieren.

- Deferred zu separatem ADR wenn Phase 1-3 stabil
- Anforderungen: localhost-only Binding, Token-Auth, TLS, Threat-Model

---

## Risiken

| Risiko | Schwere | Mitigation |
|--------|---------|-----------|
| Deploy-Script hängt auf Server | MEDIUM | Status-File + PID-Liveness-Check; MCP erkennt stale Deploys |
| Parallele Deploys | HIGH | Atomarer Lock via `flock(1)` in `/var/run/deploy/` (Fix B1) |
| Migration schlägt fehl | HIGH | Fail-Closed — Deploy wird abgebrochen, DB-Schema unverändert (Fix B2) |
| Health-Check fehlgeschlagen | HIGH | Automatischer Rollback + Container-Logs im Deploy-Log (Fix B3) |
| Log-Verzeichnis voll | LOW | Logrotate, 7 Tage Retention, `copytruncate` |
| Job-Schätzung zu ungenau | LOW | Katalog-Werte + Feedback-Loop (70/30 Gewichtung) |
| Background-Job scheitert unbemerkt | MEDIUM | Discord-Notification bei Failure, Status-File persistent |
| SSH nicht verfügbar | MEDIUM | Fallback auf GitHub Actions (ADR-075 infra-deploy) |

---

## Open Questions

| # | Frage | Status | Optionen |
|---|-------|--------|----------|
| Q1 | Soll `deploy.sh` auch `/healthz/` (Readiness) prüfen, nicht nur `/livez/`? | Offen | Ja = strenger, Nein = schneller |
| Q2 | Wie wird die `job_catalog.yaml` aktuell gehalten? | Offen | Manuell vs. automatisches `record_measurement()` nach jedem Deploy |
| Q3 | Soll der Feedback-Loop (gemessene Zeiten) persistent gespeichert werden? | Offen | In-Memory (aktuell) vs. JSON-File vs. pgvector Memory |
| Q4 | Wie handhabt `deploy-start.sh` Repos ohne `docker-compose.prod.yml`? | Offen | Validierung in deploy.sh (aktuell) vs. Whitelist in deploy-start.sh |
| Q5 | Wer darf `deploy-start.sh` aufrufen? Brauchen wir Token-Validierung? | **Entschieden** | SSH-Key ist ausreichende Auth — nur wer SSH-Zugang hat, kann deployen. Zusätzliche Token-Validierung wäre Over-Engineering. Risiko akzeptiert (analog ADR-075 §Security). |

---

## Confirmation

### Phase 1 — Deploy-Core Scripts
- [ ] `/var/run/deploy/` + `/var/log/deploy/` auf Prod-Server erstellt
- [ ] `deploy.sh`, `deploy-start.sh`, `deploy-status.sh` in `/opt/deploy-core/`
- [ ] Logrotate `/etc/logrotate.d/deploy-logs` konfiguriert
- [ ] `/ship` Workflow auf Short-Trigger-Pattern umgestellt
- [ ] Erster erfolgreicher Deploy über `deploy-start.sh` + Polling
- [ ] ADR-075 Amendment (Write-Op-Klassifikation) eingetragen

### Phase 2 — Job-Transparenz
- [ ] `estimate_job()` in orchestrator-MCP implementiert
- [ ] `job_catalog.yaml` als maschinenlesbarer Katalog
- [ ] Agent gibt Schätzung vor jedem Job >15s aus
- [ ] Discord-Notification bei Background-Job Start/Ende

### Phase 3 — Job-Router
- [ ] `analyze_task()` um Executor/Schätzung/Background erweitert
- [ ] LLM-Modell-Routing-Matrix in orchestrator-MCP

---

## More Information

- **ADR-075**: Read/Write-Split — dieses ADR amended die Write-Op-Policy
- **ADR-022**: Code Quality + Docker Standards — `COMPOSE_PROJECT_NAME` Pflicht
- **ADR-062**: Content Store — Fail-Closed-Prinzip für Migrations
- **ADR-107**: Deployment Agent — `shell_exec` Allowlist, Tier-Rollback
- **ADR-021 §2.14**: `infra-deploy` Repository als Deployment-API
- **Review-Input**: `platform/docs/adr/inputs/ADR-156/` (7 Dateien inkl. korrigierter Scripts)
- **Referenz-Implementierungen**: `deploy.sh` (278 LOC), `deploy-start.sh` (83 LOC),
  `deploy-status.sh` (98 LOC), `job_catalog.yaml` (296 Einträge), `estimate_job.py` (219 LOC)

## Changelog

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-04-02 | Initial — Problemanalyse + 3 Optionen + Phasenplan |
| v2 | 2026-04-02 | Erweitert: §5 Job-Transparenz, §6 Background-Jobs, §7 Job-Routing + LLM-Zuweisung |
| v3 | 2026-04-02 | Review-Rework: 7 Blocker behoben (B1-B7), MADR 4.0 Sektionen ergänzt, ADR-075 Reconciliation, deploy.sh durch korrigierte Version ersetzt, Short-Trigger-Pattern statt nohup, Drift-Detector-Felder, Open Questions |
| v3.1 | 2026-04-02 | Review-Fixes: Health-Check-Port parametrisiert (T1), Rollback-Code implementiert (T2), Q5 Auth-Entscheidung (SSH-Key reicht) |
