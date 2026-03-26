---
description: App auf Production deployen — verify, push, CI, migrate, health check
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

## Schritt 1 — Branch + Status verifizieren

**KEIN auto-run. User-Bestätigung vor Push erforderlich.**

```bash
git -C /home/dehnert/github/{scope} branch --show-current
git -C /home/dehnert/github/{scope} status
git -C /home/dehnert/github/{scope} diff --stat HEAD
```

Erwartung: Branch = `main`, keine uncommitted WIP-Änderungen.
**Abbruch wenn:** Branch != main ODER uncommitted Änderungen vorhanden.

---

## Schritt 2 — Änderungen pushen

Erst nach User-Bestätigung aus Schritt 1:

// turbo
```bash
git -C /home/dehnert/github/{scope} push origin main
```

---

## Schritt 3 — GitHub Actions Deploy triggern

```
mcp6_cicd_manage:
  action: dispatch
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  ref: main
```

---

## Schritt 4 — Deploy-Status verfolgen

```
mcp6_cicd_manage:
  action: workflow_runs
  owner: achimdehnert
  repo: {scope}
  workflow_id: {cd_workflow}
  per_page: 1
```

Warte auf `conclusion: success`. Bei `failure` → Schritt 6 (Rollback).

---

## Schritt 5 — Health Check

```
mcp6_docker_manage:
  action: container_status
  host: 88.198.191.108
  container_id: {web_container}
```

```
mcp6_ssh_manage:
  action: http_check
  host: 88.198.191.108
  url: http://127.0.0.1:{health_port}/livez/
  expect_status: 200
```

Bei HTTP 200 → Deploy erfolgreich. Bei Failure → Schritt 6.

---

## Schritt 6 — Rollback (nur bei Health-Check-Failure)

```bash
docker compose -f docker-compose.prod.yml pull web
docker compose -f docker-compose.prod.yml up -d --force-recreate web
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
