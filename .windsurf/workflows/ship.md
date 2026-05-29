---
description: App auf Production deployen — verify, push, CI, migrate, health check
mode: write
---

# /ship — Universal Deploy Workflow

> **Parametrisiert über Frontmatter.** Der Agent liest `scope`, `health_port`,
> `cd_workflow`, `web_container` aus der repo-eigenen `ship.md` ODER erkennt
> sie automatisch aus `docker-compose.prod.yml` und `ports.yaml`.
>
> Falls das Repo eine **eigene** `ship.md` hat, wird diese bevorzugt.
> Falls nicht, nutzt der Agent dieses Template und ermittelt die Parameter.

## Step 0: Parameter ermitteln

Ermittle die 4 Deploy-Parameter für dieses Repo:

1. **scope** — Repo-Name (z.B. `risk-hub`)
2. **health_port** — Port des Web-Containers auf dem Server
3. **cd_workflow** — GitHub Actions Workflow-Datei (z.B. `ci.yml`, `docker-build.yml`)
4. **web_container** — Docker Container-Name (z.B. `risk_hub_web`)

Quellen (in Prioritätsreihenfolge):
1. Repo-eigene `ship.md` Frontmatter (falls vorhanden)
2. `platform/ports.yaml` (health_port)
3. `docker-compose.prod.yml` im Repo (web_container, health_port)
4. `.github/workflows/*.yml` (cd_workflow)

Bekannte Repos (Schnellreferenz):

| Repo | Port | CI-Workflow | Container |
|------|------|-------------|-----------|
| risk-hub | 8090 | docker-build.yml | risk_hub_web |
| billing-hub | 8096 | ci.yml | billing_hub_web |
| cad-hub | 8094 | cd-production.yml | cad_hub_web |
| coach-hub | 8007 | ci.yml | coach_hub_web |
| trading-hub | 8088 | ci.yml | trading_hub_web |
| travel-beat | 8089 | cd-production.yml | travel_beat_web |
| weltenhub | 8081 | ci.yml | weltenhub_web |
| wedding-hub | 8093 | ci.yml | wedding_hub_web |
| pptx-hub | 8020 | cd-production.yml | pptx_hub_web |
| dev-hub | 8085 | ci.yml | devhub_web |
| ausschreibungs-hub | 8095 | ci.yml | ausschreibungs_hub_web |
| recruiting-hub | 8103 | ci.yml | recruiting_hub_web |

---

## Schritt 0.5 — Connectivity-Gate (PFLICHT)

⚠️ **NIEMALS `ping` verwenden** — Hetzner blockiert ICMP (100% loss ist NORMAL).
TCP-Probe auf SSH/HTTP/HTTPS stattdessen:

// turbo
```bash
python3 ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/server_probe.py --host 88.198.191.108
```

→ **Server erreichbar**: Weiter mit Schritt 0.6
→ **Server NICHT erreichbar**: **STOPP** — MCP-SSH-Calls in Schritt 3–5 werden hängen!
  Fallback: Deploy via GitHub Actions (Schritt 3 Fallback-Pfad)
→ Lesson Learned 2026-04-03: Fehlende Connectivity-Prüfung führte zu hängenden Deploys

---

## Schritt 0.6 — Job-Schätzung ausgeben (ADR-156)

**Vor jedem Deploy** dem User die geschätzte Dauer kommunizieren (Erfahrungswerte: 60-180s).

> ℹ️ `mcp2_estimate_job` existiert nicht mehr (Issue #80) — Schätzung aus Erfahrung.

Ausgabe an den User im Format:
> Deploy {scope}: ~{estimated_seconds}s ({estimated_seconds_min}–{estimated_seconds_max}s)
> Schritte: pull → migrate → recreate → health-check
> Modus: Background (Agent bleibt verfügbar)

Falls `estimated_seconds > 60`: User darauf hinweisen dass der Deploy im Hintergrund läuft.

---

## Schritt 1 — Branch + Status verifizieren

**KEIN auto-run. User-Bestätigung vor Push erforderlich.**

```bash
git -C ${GITHUB_DIR:-$HOME/github}/{scope} branch --show-current
git -C ${GITHUB_DIR:-$HOME/github}/{scope} status
git -C ${GITHUB_DIR:-$HOME/github}/{scope} diff --stat HEAD
```

Erwartung: Branch = `main`, keine uncommitted WIP-Änderungen.
**Abbruch wenn:** Branch != main ODER uncommitted Änderungen vorhanden.

---

## Schritt 1.5 — Port-Audit Gate (ADR-157)

**Automatisch, kein User-Input nötig.**

// turbo
```bash
python ${GITHUB_DIR:-$HOME/github}/platform/infra/scripts/port_audit.py --offline
```

Erwartung: Exit-Code 0 (keine Duplikate in ports.yaml).
**Abbruch wenn:** Exit-Code != 0 — Port-Konflikte müssen vor Deploy gelöst werden.

---

## Schritt 2 — Änderungen pushen

Erst nach User-Bestätigung aus Schritt 1:

// turbo
```bash
git -C ${GITHUB_DIR:-$HOME/github}/{scope} push origin main
```

---

## Schritt 3 — Deploy triggern (ADR-156 Short-Trigger)

**Primary (ADR-156):** Server-seitiges Deploy via Short-Trigger (~2s SSH, non-blocking).
Deploy.sh führt Pull, Migrate, Recreate, Health-Check und ggf. Rollback automatisch aus.

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "bash /opt/deploy-core/deploy-start.sh {scope} docker-compose.prod.yml {health_port}"
  timeout: 10
```

Erwartete Antwort: `{"status":"started","background_pid":...,"log_file":...}`

> ℹ️ `mcp2_discord_notify` existiert nicht mehr (Issue #80) — Notifications jetzt im Cascade-Output, nicht mehr in Discord.

**Fallback (ADR-075):** Falls SSH nicht verfügbar → GitHub Actions:

```
mcp0_cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  ref: main
```

---

## Schritt 4 — Deploy-Status verfolgen

**Bei Short-Trigger (Schritt 3 Primary):** Polle alle 15s via deploy-status.sh:

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "bash /opt/deploy-core/deploy-status.sh {scope}"
```

Warte auf `"status":"SUCCESS"`. Bei `"status":"FAILED"` → Rollback wurde automatisch durchgeführt.

**Bei FAILED — Error Pattern automatisch loggen (ADR-156):**

Deploy-Log lesen und Fehler als Pattern speichern:

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "tail -20 /var/log/deploy/{scope}-latest.log"
```

Dann Error-Pattern in pgvector sichern:
```
mcp1_agent_memory(
  operation: "upsert",
  agent: "cascade",
  entry: {
    entry_id: "ERROR-DEPLOY-<SCOPE-UPPERCASE>-<YYYYMMDD>",
    entry_type: "error_pattern",
    agent: "cascade",
    title: "Deploy FAILED: {scope}",
    content: "Repo: {scope}\nSymptom: <Fehler aus Log>\nRoot Cause: <Analyse>\nFix: <angewandter oder empfohlener Fix>",
    tags: ["error", "deploy", "{scope}"]
  }
)
```

→ Beim nächsten `/session-start` findet die Memory-Query (`filter_type: error_pattern`) wiederkehrende Probleme.

**Bei GitHub Actions Fallback:**

```
mcp0_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  per_page: 1
```

Warte auf `conclusion: success`. Bei `failure` → Schritt 6.

---

## Schritt 5 — Health Check (Verifikation)

Nach erfolgreichem Deploy nochmal explizit prüfen:

```
mcp0_ssh_manage:
  action: http_check
  host: 88.198.191.108
  url: http://127.0.0.1:{health_port}/livez/
  expect_status: 200
```

Bei HTTP 200 → Deploy erfolgreich. Bei Failure → Schritt 6.

**Nach erfolgreichem Health Check:**

→ Im Cascade-Output melden: `✅ Deploy erfolgreich: {scope} | Dauer: {elapsed}s | Port {health_port}`

> ℹ️ `mcp2_discord_notify` und `mcp2_record_job_measurement` existieren nicht mehr (Issue #80).

---

## Schritt 6 — Rollback (nur bei Health-Check-Failure)

**Short-Trigger-Deploys** führen Rollback automatisch durch (deploy.sh _rollback).
Falls manueller Rollback nötig:

```bash
ssh root@88.198.191.108 "cd /opt/{scope} && docker compose -f docker-compose.prod.yml up -d --no-deps --force-recreate web"
```

Dann Health Check wiederholen. User über Rollback informieren.

---

## Fehlerbehebung

| Problem | Lösung |
|---------|--------|
| Container crasht | `container_logs container_id={web_container} lines=80` |
| Migration fehlt | `container_exec container_id={web_container} command="python manage.py migrate --noinput"` |
| Image nicht aktuell | CI-Log prüfen: `run_logs owner=achimdehnert repo={scope} run_id=<id>` |
| Branch falsch | `git checkout main && git pull origin main` |

**Wichtig:** Bei JEDEM Fehler in diesem Workflow ein `error_pattern` Memory-Entry via `mcp1_agent_memory` schreiben (siehe Schritt 6).
Beim nächsten `/session-start` findet `mcp1_agent_memory(operation: "query", filter_type: "error_pattern")` wiederkehrende Probleme.
