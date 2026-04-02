# ADR-156 Review: Reliable Deployment Pipeline

**Reviewer:** Claude (Principal IT-Architekt-Rolle)
**Datum:** 2026-04-02
**ADR-Version:** v2
**Gesamtbewertung:** ⛔ REJECT — 7 BLOCKER, davon 3 sicherheitskritisch. Das deploy.sh-Script **darf nicht as-is in Produktion** eingesetzt werden.

---

## 1. Review-Tabelle

| # | Befund | Severity | Bereich | Begründung |
|---|--------|----------|---------|-----------|
| B1 | Lock-File im Risiko-Abschnitt erwähnt, aber **nie implementiert** im Script | **BLOCKER** | `deploy.sh` | Parallele MCP-Aufrufe (z.B. Agent-Retry) starten zwei parallele Deploys → doppeltes `docker compose up` auf gleicher DB → Race auf Migrations |
| B2 | `migration ... \|\| true` maskiert DB-Schema-Fehler **lautlos** | **BLOCKER** | `deploy.sh:382-383` | Bei echter Migration-Failure (Column Conflict, Data Error): Container startet mit kaputtem Schema, Health-Check besteht (HTTP 200), kein Alert → Prod-DB in defektem Zustand |
| B3 | Kein Rollback bei Health-Check-Failure — nur `exit 1` | **BLOCKER** | `deploy.sh:402-404` | Decision Driver §6 "Rollback jederzeit" ist nicht implementiert. Nach fehlgeschlagenem Pull eines broken Image bleibt der alte Container down |
| B4 | `nohup bash deploy.sh & ` — PID geht verloren, kein Liveness-Check | **BLOCKER** | MCP-Pattern | `$!` existiert nur im SSH-Client-Prozess, nicht auf dem Server. Es gibt keinen Mechanismus zu prüfen ob der Deploy-Prozess noch läuft oder silent gecrasht ist |
| B5 | Log-Glob `file_read path="/var/log/deploy/<repo>-*.log"` → undefinierte Reihenfolge nach mehreren Deploys | **BLOCKER** | MCP-Pattern | Nach 10 Deploys: 10 Logdateien, Glob-Expansion ungeordnet — Agent liest älteres Log, hält Deploy für fertig obwohl aktueller noch läuft |
| B6 | Kein `COMPOSE_PROJECT_NAME` — verletzt ADR-022 | **BLOCKER** | `deploy.sh` | ADR-022 mandatiert `COMPOSE_PROJECT_NAME` in allen Docker-Compose-Operationen. Ohne: Container-Name-Kollisionen zwischen Repos auf gleichem Host (18+ Hubs auf Prod) |
| B7 | Phase-3 Status-Endpoint `GET /deploy/status/<repo>` ohne Authentifizierung | **BLOCKER** | §6 / Phase 3 | Jeder Actor im Netzwerk kann Deployment-Informationen abfragen. Kein Token, kein localhost-Binding erwähnt — Security-Violation |
| K1 | `2>/dev/null` auf Migration-Kommando eliminiert Fehler-Output für Debugging | **KRITISCH** | `deploy.sh:382` | Wenn Migration fehlschlägt, ist der Fehler im Log nicht sichtbar. Diagnose unmöglich. |
| K2 | Health-Check prüft nur HTTP 200 — nicht ob Container innerhalb von Health-Window bleibt | **KRITISCH** | `deploy.sh:390-401` | Container kann kurz nach Health-Check crashen (OOMKill, Startup-Exception) → unbemerkt |
| K3 | MADR 4.0 Non-Compliance: fehlende Abschnitte `Pros and Cons`, `More Information`, Drift-Detector-Felder | **KRITISCH** | ADR-Struktur | ADR-059 Drift-Detector kann ADR nicht korrekt verarbeiten. Kein `staleness_months`, kein `drift_check_paths` |
| K4 | Phase 4 "Server-Side Deploy-Agent als Systemd-Service" ohne Security-Konzept (Credentials, TLS) | **KRITISCH** | §7 Phase 4 | Ein REST-Service auf Prod-Server für Deployment-Trigger ist ein hochprivilegiertes Target ohne Threat-Model |
| H1 | `exec > >(tee -a "$LOG") 2>&1` — Process-Substitution mit `set -e` hat plattformspezifisches Verhalten | **HOCH** | `deploy.sh:372` | Auf manchen Systemen exitiert das Skript nicht korrekt wenn der tee-Prozess stirbt. Logging-Infrastruktur wird Teil des kritischen Pfads |
| H2 | `docker compose up -d --force-recreate web` ohne `--no-deps` | **HOCH** | `deploy.sh:386` | Kann abhängige Services (DB, Redis) neu starten — Service-Unterbrechung für alle anderen Hubs auf gleichem Host |
| H3 | `estimate_job()` ist ein hardcodierter Stub — gibt immer 90s zurück unabhängig von Repo/Context | **HOCH** | `estimate_job()` | Kein echter Algorithmus. Nutzwert = 0 bis echte Daten vorliegen |
| H4 | Phase 3 "Deploy-Status-API auf Server" benötigt Port-Öffnung/Routing — nicht beschrieben | **HOCH** | §7 Phase 3 | Hetzner Firewall-Konfiguration, Cloudflare-Routing, Nginx-Proxy fehlen komplett |
| M1 | Log-Dateiname mit Timestamp: symlink-less → Agent braucht komplexe Logik zur aktuellen Log-Identifikation | **MEDIUM** | `deploy.sh` | Fix: Symlink `<repo>-latest.log` → aktuelle Datei |
| M2 | Kein `ADR-022` in `related`-Liste | **MEDIUM** | Frontmatter | ADR-022 (Code Quality + Docker-Standards) direkt relevant |
| M3 | Background-Job-Threshold "15 Sekunden" ohne Basis — `ruff check` (2-5s) als Grenzfall | **MEDIUM** | §6 | Feste Grenze ohne Implementierung hinter `estimate_job()` ist bedeutungslos |
| M4 | Discord-Notification in Phase 2 erwähnt aber kein Webhook-Handling beschrieben | **MEDIUM** | §6 Phase 2 | Entweder implementieren oder als separates ADR definen |

---

## 2. Kritische Analyse: Das Kern-Architekturproblem

### Option A (gewählt) vs. Architecture-Guardian-Pattern

Das ADR wählt `nohup`-Pattern (Option A) korrekt für Phase 1. **Aber**: Die MCP-Aufruf-Sequenz ist fehlerhaft:

```
# ADR-Version (FALSCH):
ssh → "nohup bash /opt/repo/deploy.sh repo &"
# Problem: Background-Prozess-PID geht verloren im SSH-Context
# MCP sieht nur: "SSH Befehl exit 0" — nicht ob Deploy läuft

# Korrekt (Gegenvorschlag):
ssh → "bash /opt/repo/deploy-start.sh repo"
# deploy-start.sh: schreibt PID, verwaltet Lock, returnt Job-ID
# MCP kann danach: "cat /var/run/deploy/repo.status" pollen
```

### Migration-Fehler-Toleranz vs. Fail-Closed

Das ADR verletzt das Plattform-Prinzip **"Fail-Closed über Fail-Open"** (aus ADR-062):

```bash
# ADR-Version (FAIL-OPEN — FALSCH für Migrations):
docker compose run --rm migrate 2>/dev/null || \
  docker compose exec -T web python manage.py migrate --noinput || true
# → Prod DB kann mit fehlerhafter Migration in Betrieb gehen

# Korrekt (FAIL-CLOSED):
if ! docker compose -p "${COMPOSE_PROJECT_NAME}" run --rm migrate; then
  echo "FATAL: Migration failed — aborting deploy" >&2
  exit 2
fi
```

---

## 3. Alternativen-Bewertung: Besser als Option A

### Alternative: Start-Script + Status-File (empfohlen statt nohup-Pattern)

**Konzept**: Statt `nohup &` verwendet das Script eine **State-Machine auf Dateiebene**. Kein PID-Tracking nötig.

```
/var/run/deploy/
├── risk-hub.lock          # flock-Datei (atomarer Mutex)
├── risk-hub.status        # RUNNING | SUCCESS | FAILED | ROLLBACK
├── risk-hub.pid           # PID des Deploy-Prozesses
└── risk-hub.start         # Startzeit (unix timestamp)

/var/log/deploy/
├── risk-hub-latest.log    # Symlink auf aktuelles Log
└── risk-hub-20260402-122815.log
```

**MCP-Polling** (statt Glob):
```python
# Deterministisch:
ssh_manage(action="file_read", path="/var/run/deploy/risk-hub.status")
# → "RUNNING" | "SUCCESS" | "FAILED"
```

**Trade-off**: Etwas mehr Script-Komplexität (+40 Zeilen). Dafür:
- Deterministisches Polling (kein Glob)
- Atomarer Lock (flock statt Datei-Existenz-Check)
- Rollback-Mechanismus
- Liveness-Check über PID-File

---

## 4. Vollständiger Implementierungsplan

### Phase 1 — Sofort (fixes alle BLOCKER)

```
/opt/deploy-core/
├── deploy.sh                    ← Korrigiertes Haupt-Script (siehe Deliverable)
├── deploy-lib.sh                ← Gemeinsame Funktionen (Lock, Rollback, Health)
└── deploy-status.sh             ← Status-Polling-Helper für MCP

/var/run/deploy/                 ← State-Files (tmpfs oder persistent)
/var/log/deploy/                 ← Log-Dateien
/etc/logrotate.d/deploy-logs     ← Rotation (7 Tage)
```

### Phase 2 — Job-Transparenz (1-2 Wochen)

```
orchestrator-mcp/
└── tools/
    ├── estimate_job.py          ← Echter Algorithmus (kein Stub)
    └── job_catalog.yaml         ← Dauer-Katalog (maschinenlesbar)
```

### Phase 3 — Status-API (nur localhost, Token-Auth)

```
/opt/deploy-core/
└── status-api.py                ← Flask/FastAPI, 127.0.0.1 only, Token-Auth
```
