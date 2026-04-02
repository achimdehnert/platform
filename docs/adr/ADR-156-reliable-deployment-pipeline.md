---
status: proposed
date: 2026-04-02
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related:
  - ADR-075-deployment-agent.md
  - ADR-090-cicd-pipeline-python-postgres.md
  - ADR-120-unified-deployment-pipeline.md
---

# ADR-156: Reliable Deployment Pipeline & Agent Job Management — Solving SSH/MCP Timeout, Transparency, and Job-Routing

## Metadaten

| Attribut          | Wert                                                        |
|-------------------|-------------------------------------------------------------|
| **Status**        | Proposed                                                    |
| **Scope**         | platform-wide (alle 18+ Hub-Repos, Prod-Server, Dev Desktop, Agent-Team) |
| **Erstellt**      | 2026-04-02                                                  |
| **Autor**         | Achim Dehnert                                               |

## Problemstellung

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

## Entscheidung

### Gewählt: Option A (Server-Side Deploy-Script) als Phase 1, Option C als Langfrist-Ziel

**Begründung**: Option A löst das akute Problem sofort mit minimalem Aufwand. Option C ist das strategische Ziel, aber erfordert mehr Planung.

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

### Implementierung: `estimate_job()` Funktion

Der orchestrator-MCP bekommt eine neue Funktion:

```python
def estimate_job(job_type: str, repo: str | None = None) -> JobEstimate:
    """Gibt geschätzte Dauer, Background-Fähigkeit und empfohlenen Executor zurück."""
    return JobEstimate(
        estimated_seconds=90,
        background_capable=True,
        executor="server-script",        # server-script | ci | local | llm
        recommended_model=None,           # z.B. "gpt_low" für einfache Tasks
        steps=["pull (30s)", "migrate (15s)", "recreate (15s)", "health (30s)"],
    )
```

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
  3. Startet: ssh_manage(exec, "nohup deploy.sh risk-hub &")
  4. Setzt Timer: Nach 90s automatisch Status prüfen
  5. Arbeitet parallel an anderer User-Anfrage
  6. Nach ~90s: ssh_manage(file_read, deploy-log) → "Deploy erfolgreich ✓"
  7. Meldet User: "risk-hub Deploy abgeschlossen. Health: ✓"
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

### Phase 1: Standardisiertes Deploy-Script (sofort)

Jedes Hub-Repo bekommt ein `/opt/<repo>/deploy.sh`:

```bash
#!/bin/bash
set -euo pipefail
REPO="$1"
LOG="/var/log/deploy/${REPO}-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1

echo "=== Deploy $REPO started at $(date) ==="

cd /opt/$REPO

# 1. Pull latest image
docker compose -f docker-compose.prod.yml pull web

# 2. Run migrations (if migrate service exists)
docker compose -f docker-compose.prod.yml run --rm migrate 2>/dev/null || \
  docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate --noinput || true

# 3. Recreate web + workers
docker compose -f docker-compose.prod.yml up -d --force-recreate web
docker compose -f docker-compose.prod.yml up -d --force-recreate celery 2>/dev/null || true

# 4. Health check (max 30s)
for i in $(seq 1 6); do
  if docker compose -f docker-compose.prod.yml exec -T web python -c "
import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')
" 2>/dev/null; then
    echo "=== Health check PASSED ==="
    echo "=== Deploy $REPO completed at $(date) ==="
    exit 0
  fi
  echo "Health check attempt $i/6 failed, waiting 5s..."
  sleep 5
done

echo "=== HEALTH CHECK FAILED — consider rollback ==="
exit 1
```

### MCP-Aufruf (Agent-Pattern)

```python
# 1. Script schreiben (kurzer SSH-Write)
ssh_manage(action="file_write", path="/opt/<repo>/deploy.sh", content=SCRIPT)

# 2. Deploy im Background starten (kurzer SSH-Exec)
ssh_manage(action="exec", command="nohup bash /opt/<repo>/deploy.sh <repo> &", timeout=10)

# 3. Status pollen (kurzer SSH-Read)
ssh_manage(action="file_read", path="/var/log/deploy/<repo>-*.log", tail=20)
```

### Phase 2: Job-Transparenz + Background-Jobs (kurzfristig)

- `estimate_job()` Funktion in orchestrator-MCP
- Job-Dauer-Katalog als YAML/Dict in orchestrator-MCP
- `/ship` Workflow: Schätzung VOR Start kommunizieren
- Discord-Notification bei Background-Job Start/Ende
- Foreground/Background-Klassifikation (>15s = Background)

### Phase 3: Deploy-Status-API + Job-Router (mittelfristig)

- Status-Endpoint auf Server: `GET /deploy/status/<repo>` → JSON
- `analyze_task()` erweitern um Executor, Schätzung, Background-Flag
- Job-Routing-Matrix in orchestrator-MCP
- LLM-Modell-Empfehlung pro Job-Typ

### Phase 4: Server-Side Deploy-Agent + Job-Queue (langfristig — Option C)

- Systemd-Service auf Prod-Server (REST-API)
- Job-Queue mit Prioritäten und Abhängigkeiten
- Parallele LLM-Jobs + sequentielle Server-Jobs
- Integriertes Rollback (vorheriges Image-Tag speichern)

## Sofort-Maßnahmen (Quick Wins)

1. **`/var/log/deploy/` Verzeichnis** auf Prod-Server erstellen
2. **`deploy.sh` Template** in `platform/deployment/templates/` bereitstellen
3. **MCP-Workflow** `/ship` anpassen auf nohup-Pattern
4. **Logrotate** für Deploy-Logs (7 Tage Retention)
5. **Job-Dauer-Katalog** als Dict in orchestrator-MCP hinterlegen
6. **Agent-Pattern**: Vor jedem Job >15s die Schätzung ausgeben

## Risiken

| Risiko | Mitigation |
|--------|-----------|
| Deploy-Script hängt auf Server | Timeout in Script (max 300s), Logfile zeigt Status |
| Parallele Deploys | Lock-File `/tmp/deploy-<repo>.lock` |
| Log-Verzeichnis voll | Logrotate, max 7 Tage |
| SSH-Key-Rotation | Nicht betroffen (Standard-SSH-Keys) |
| Job-Schätzung zu ungenau | Katalog-Werte aus Erfahrungsdaten, Korrektur über Feedback-Loop |
| Background-Job scheitert unbemerkt | Discord-Notification bei Failure, Log persistent |
| Falsches LLM-Modell zugewiesen | Routing-Matrix als Empfehlung, Agent kann übersteuern |

## Confirmation

### Phase 1 — Deploy-Script
- [ ] `/var/log/deploy/` auf Prod-Server erstellt
- [ ] `deploy.sh` Template in platform/deployment/templates/
- [ ] `/ship` Workflow auf nohup-Pattern umgestellt
- [ ] Erster erfolgreicher Deploy über neues Pattern
- [ ] Logrotate konfiguriert

### Phase 2 — Job-Transparenz
- [ ] `estimate_job()` in orchestrator-MCP implementiert
- [ ] Job-Dauer-Katalog als Datenstruktur hinterlegt
- [ ] Agent gibt Schätzung vor jedem Job >15s aus
- [ ] Discord-Notification bei Background-Job Start/Ende

### Phase 3 — Job-Router
- [ ] `analyze_task()` um Executor/Schätzung/Background erweitert
- [ ] LLM-Modell-Routing-Matrix in orchestrator-MCP
- [ ] Deploy-Status-API auf Server

### Phase 4 — Job-Queue
- [ ] Server-Side Deploy-Agent als Systemd-Service
- [ ] Job-Queue mit Abhängigkeiten
- [ ] Parallele LLM-Jobs + sequentielle Server-Jobs

## Changelog

| Version | Datum | Änderung |
|---------|-------|----------|
| v1 | 2026-04-02 | Initial — Problemanalyse + 3 Optionen + Phasenplan |
| v2 | 2026-04-02 | Erweitert: §5 Job-Transparenz, §6 Background-Jobs, §7 Job-Routing + LLM-Zuweisung |
