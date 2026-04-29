---
description: Pre-deployment verification checklist
---

# Deploy-Check Workflow

**Trigger:** Vor jedem Production-Deployment — als Gate zwischen "merged" und "deployed".

---

## Step 1: Code-Stand prüfen

// turbo
```bash
git log --oneline -5 && git status
```

- [ ] Auf `main`-Branch
- [ ] Kein uncommitted work
- [ ] Letzter Commit ist der zu deployende Stand

---

## Step 2: Tests lokal grün

// turbo
```bash
pytest tests/ -q --tb=short 2>&1 | tail -15
```

**Kein Deploy bei roter Test-Suite.** Ausnahme: nur wenn explizit als Hotfix freigegeben.

---

## Step 3: CI/CD Status prüfen

GitHub Actions für den letzten `main`-Commit müssen grün sein:
- [ ] CI-Job grün (Tests + Linting)
- [ ] Build-Job grün (Docker Image gepusht)
- [ ] Kein fehlgeschlagener vorheriger Deploy

→ Status prüfen via: `https://github.com/achimdehnert/[REPO]/actions`

---

## Step 4: Migrations-Check

```bash
cd src && python manage.py migrate --check 2>&1
```

- [ ] Keine ausstehenden unapplied Migrations → OK
- [ ] Migrations vorhanden → `has_migrations: true` im Deploy-Workflow setzen
- [ ] Destructive Migration (DROP, DELETE)? → Backup ZUERST via `/backup`

---

## Step 5: Environment-Check

- [ ] `.env.prod` auf Server aktuell (neue Env-Variablen aus `.env.example` übernommen)?
- [ ] Secrets nicht im Code? (`grep -r "password\|secret\|token" src/ --include="*.py" -l`)
- [ ] `docker-compose.prod.yml` auf Server aktuell (falls geändert)?

---

## Step 5.5: Port-Audit (bei neuem Service oder Port-Änderung)

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/platform && python infra/scripts/port_audit.py
```

- [ ] Keine Duplikate in `ports.yaml`
- [ ] Keine Konflikte mit laufenden Containern auf dem Server
- [ ] Neuer Port in `ports.yaml` eingetragen und committed

> **Hintergrund:** `ports.yaml` ist Single Source of Truth für alle Ports.
> Das Audit-Script vergleicht sie mit dem realen Server-Zustand via SSH.
> Nur `--offline` prüft ohne Server-Zugriff auf Duplikate.

---

## Step 5.8: Job-Schätzung (ADR-156)

Vor dem Deploy die typische Dauer aus Erfahrung kommunizieren (ca. 60-180s je nach Repo).

> ℹ️ Das frühere Tool `mcp2_estimate_job` existiert nicht mehr (Issue #80) —
> Schätzung basiert jetzt auf Repo-Erfahrungswerten oder Memory-Query.

## Step 6: Deploy ausführen

Via `/ship`:
```
service: [app-name]
image_tag: latest
has_migrations: [true/false]
```

---

## Step 7: Post-Deploy Verifikation

// turbo
```bash
curl -sf https://[DOMAIN]/livez/ && echo "✅ Liveness OK"
curl -sf https://[DOMAIN]/healthz/ && echo "✅ Readiness OK"
```

- [ ] `/livez/` antwortet mit 200
- [ ] `/healthz/` antwortet mit 200 + `"db": "connected"`
- [ ] Keine Fehler in den ersten Container-Logs

Container-Logs prüfen via `deployment-mcp` → `container_logs`.

---

## Rollback-Kriterium

**Sofortiger Rollback wenn:**
- `/livez/` gibt nicht 200 nach 60 Sekunden
- Kritische Fehler in Logs (500er, DB-Connection-Fehler)
- Health-Check im Compose failed (Container Restart-Loop)

Rollback via `/deploy` → Rollback-Workflow.
