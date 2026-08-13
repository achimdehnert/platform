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

## Wann `/ship` — und wann nicht?

`/ship` ist der **kanonische Standard-Pfad** für Prod-Deploys (Deploy-Trias-Kanon 2026-07-04).

- **Wann `/ship`:** regulärer App-Deploy nach main-Merge — verify → push → CI → migrate →
  health-check, primär über GitHub Actions (Short-Trigger nur als Sonderfall, s. Schritt 3).
- **Wann NICHT / stattdessen:**
  - Server/CI nicht erreichbar oder du brauchst einen manuellen Hand-Pfad direkt am
    `docker compose` → **`/run-prod`** (Notfall-Handpfad mit sauberem Ja/Nein-Gate).
  - Deploy schlug fehl, Prod ist rot → **`/rollback`**.
  - Ziel ist Staging (Dev Desktop) statt Prod → **`/ship-staging`**.
  - Pre-Deploy-Checkliste ohne Deploy → **`/deploy-check`**.
  - `/deploy` (infra-deploy-Actions) ist **deprecated** — nicht mehr verwenden.

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

**Vor jedem Deploy** dem User die geschätzte Dauer kommunizieren.

```
mcp__orchestrator__estimate_job:
  job_type: deploy
  repo: {scope}
```

> Fallback ohne gebundenen orchestrator-MCP: Erfahrungswerte 60-180s.

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

## Schritt 3 — Deploy triggern (Actions primär, Short-Trigger als Sonderfall)

### ⚠️ GATE: Explizite Prod-Deploy-Freigabe erforderlich (vor Deploy-Trigger)

> Das Gate in Schritt 1 sitzt vor dem **Push** — der eigentliche **Deploy** braucht ein
> **eigenes** explizites Ja. Frage den User: "Prod-Deploy für `{scope}` jetzt triggern? (ja/nein)"
> → Bei "nein": **STOPP** — Code ist gepusht, aber es wird nicht deployt.
> → Bei "ja": weiter mit dem Deploy-Trigger unten.
>
> Prod-Deploy braucht **IMMER** Freigabe — kein Autopilot, auch nicht bei Routine.
> Siehe `~/.claude/policies/autonomy-gates.md` Gate 2.

**Primary (ADR-075): GitHub Actions.** Der Workflow macht seinen eigenen `docker login`
und pullt deshalb zuverlässig; er baut das Image für den aktuellen `main` mit, falls es
noch nicht existiert.

```
gh workflow run {cd_workflow} --ref main -f target_environment=production
```

Ohne `gh`-CLI derselbe Aufruf über MCP:

```
mcp__deployment-mcp__cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  ref: main
```

> ℹ️ Deploy-Meldung geht in den Session-Output, nicht nach Discord.
> (`mcp__orchestrator__discord_notify` **existiert weiterhin** — der frühere Hinweis
> „existiert nicht mehr" war eine Prefix-Drift-Fehldiagnose, siehe ADR-156-Nachtrag.
> Ob Discord wieder aktiv werden soll, ist eine offene Entscheidung, kein Defekt.)

**Sonderfall (ADR-156): Short-Trigger.** Server-seitiges Deploy, ~2s SSH, non-blocking —
`deploy.sh` erledigt Pull, Migrate, Recreate, Health-Check und ggf. Rollback selbst.
Schneller, aber er **baut nichts**: er kann nur ein Image ziehen, das schon in GHCR liegt,
und er braucht dafür eine Registry-Credential **auf dem Host**.

```
mcp__deployment-mcp__ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "bash /opt/deploy-core/deploy-start.sh {scope} docker-compose.prod.yml {health_port}"
  timeout: 10
```

Erwartete Antwort: `{"status":"started","background_pid":...,"log_file":...}`

> ⚠️ **Vorbedingung, gemessen 2026-08-13 auf prod:** `/root/.docker/config.json` enthielt
> dort **null** Auth-Einträge — jeder Short-Trigger-Pull endet damit in
> `error from registry: unauthorized`, und zwar **vor** dem Container-Tausch (kein
> Ausfall, aber auch kein Deploy). Der Actions-Pfad war davon nie betroffen, weil er sich
> pro Lauf selbst einloggt. Deshalb ist die Reihenfolge hier gedreht.
> Vor der Nutzung des Short-Triggers prüfen:
> `ssh root@<host> "python3 -c \"import json;print(list(json.load(open('/root/.docker/config.json')).get('auths',{}).keys()))\""`
> — **leere Liste ⇒ Actions-Pfad nehmen**, der Short-Trigger schlägt dann fehl.
> Beleg: platform#1969.

---

## Schritt 4 — Deploy-Status verfolgen

**Bei Actions (Schritt 3 primär):** `gh run watch <run-id> --exit-status` oder pollen:

```
mcp__deployment-mcp__cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  per_page: 1
```

Warte auf `conclusion: success`. Bei `failure` → Schritt 6.

⚠️ **`conclusion` allein ist kein Beweis** — der Deploy-Schritt kann grün melden und die
Instanz trotzdem alt sein. Immer Schritt 5 hinterherziehen und dabei das **laufende
Image** gegen den erwarteten Commit halten:
`docker ps --filter name={web_container} --format '{{.Image}}'`.

**Bei Short-Trigger (Schritt 3 Sonderfall):** Polle alle 15s via deploy-status.sh:

```
mcp__deployment-mcp__ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "bash /opt/deploy-core/deploy-status.sh {scope}"
```

Warte auf `"status":"SUCCESS"`. Bei `"status":"FAILED"` → Rollback wurde automatisch durchgeführt.

**Bei FAILED — Error Pattern automatisch loggen (ADR-156):**

Deploy-Log lesen und Fehler als Pattern speichern:

```
mcp__deployment-mcp__ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "tail -20 /var/log/deploy/{scope}-latest.log"
```

Dann Error-Pattern in pgvector sichern:
```
mcp__orchestrator__agent_memory_upsert(
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

(Der Actions-Pfad ist oben beschrieben — er ist seit 2026-08-13 der primäre.)

---

## Schritt 5 — Health Check (Verifikation)

Nach erfolgreichem Deploy nochmal explizit prüfen:

```
mcp__deployment-mcp__ssh_manage:
  action: http_check
  host: 88.198.191.108
  url: http://127.0.0.1:{health_port}/livez/
  expect_status: 200
```

Bei HTTP 200 → Deploy erfolgreich. Bei Failure → Schritt 6.

**Nach erfolgreichem Health Check:**

→ Im Cascade-Output melden: `✅ Deploy erfolgreich: {scope} | Dauer: {elapsed}s | Port {health_port}`

> ℹ️ `mcp__orchestrator__discord_notify` und `mcp__orchestrator__record_job_measurement` existieren nicht mehr (Issue #80).

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
| Branch falsch | im Ziel-Repo-Checkout `git pull origin main`; NICHT den geteilten Haupt-Tree switchen (ADR-233) |

**Wichtig:** Bei JEDEM Fehler in diesem Workflow ein `error_pattern` Memory-Entry via `mcp__orchestrator__agent_memory_search` schreiben (siehe Schritt 6).
