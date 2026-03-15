---
description: Third-Party Stack upgraden (Outline, Authentik, Paperless) — Backup, Pull, Deploy, Verify
---

# Stack Upgrade Workflow

**Trigger:** User sagt "Upgrade [Stack] auf [Version]" oder neue Version eines Third-Party-Stacks soll eingespielt werden.

> Standardisiertes Upgrade-Pattern für alle Third-Party Docker-Stacks.
> Getestet mit Outline 0.82→1.5→1.6, anwendbar auf Authentik, Paperless, etc.

---

## Step 0: Stack identifizieren

| Stack | Compose-Pfad | Container-Prefix | Domain |
|-------|-------------|-------------------|--------|
| Outline | `/opt/outline/` | `iil_knowledge_outline` | knowledge.iil.pet |
| Authentik | `/opt/authentik/` | `iil_authentik` | id.iil.pet |
| Paperless | `/opt/doc-hub/` | `iil_doc_hub` | docs.iil.pet |

```
MCP: mcp6_docker_manage(action: compose_ps, host: 88.198.191.108, project_path: /opt/<stack>/)
→ Zeigt aktuelle Container + Images + Status
```

---

## Step 1: Changelog prüfen (Breaking Changes?)

```
1. GitHub Releases lesen: https://github.com/<org>/<repo>/releases
2. Prüfe: Breaking Changes? Neue Env-Vars? DB-Migration-Hinweise?
3. Bei Major-Version-Jump (z.B. 0.x→1.x): Extra-Vorsicht, ggf. Zwischenversionen
```

**Bei Breaking Changes → User informieren und Approval einholen.**

---

## Step 2: Pre-Upgrade Backup (Pflicht)

```
MCP: mcp6_ssh_manage(action: exec, host: 88.198.191.108,
     command: "bash /opt/backups/<stack>/backup.sh")
→ Bestätige: Backup OK mit Dateigröße
```

Falls kein Backup-Script existiert → erst `/backup` Workflow ausführen.

---

## Step 3: Neues Image pullen

```
MCP: mcp6_ssh_manage(action: exec, host: 88.198.191.108,
     command: "docker pull <image>:<new-version>")
```

---

## Step 4: Compose aktualisieren + Rolling Upgrade

```
MCP: mcp6_ssh_manage(action: run_script, host: 88.198.191.108, script: "
cd /opt/<stack>
sed -i 's|<image>:<old-version>|<image>:<new-version>|g' docker-compose.yml
docker compose up -d <main-service>
sleep 30
docker ps --filter 'name=<container-prefix>' --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
")
```

**Erwartung:** Container `(healthy)` nach 30-60 Sekunden.

---

## Step 5: Verify (alle 4 Checks müssen grün sein)

| Check | Command | Erwartung |
|-------|---------|-----------|
| **Health** | `curl -s http://127.0.0.1:<port>/_health` | HTTP 200 |
| **OIDC** | `curl -s -L --max-redirs 0 http://127.0.0.1:<port>/auth/oidc` | HTTP 302 |
| **API** | `curl -s -X POST .../api/documents.search -d '{"query":"test"}'` | JSON response |
| **Data** | `SELECT count(*) FROM <main-table>` | Gleich wie vor Upgrade |

```
MCP: mcp6_ssh_manage(action: http_check, host: 88.198.191.108,
     url: "https://<domain>/_health", expect_status: 200)
```

---

## Step 6: Cleanup + Repo aktualisieren

```bash
# Altes Image entfernen
docker rmi <image>:<old-version>

# Platform-Repo aktualisieren
# deployment/stacks/<stack>/docker-compose.yml → neue Version
# docs/adr/ADR-XXX → Version-Referenzen aktualisieren
git commit -m "chore(<stack>): upgrade <old> → <new> — deployed + verified"
git push origin main
```

---

## Step 7: Rollback (falls Verify fehlschlägt)

```
MCP: mcp6_ssh_manage(action: run_script, host: 88.198.191.108, script: "
cd /opt/<stack>
sed -i 's|<image>:<new-version>|<image>:<old-version>|g' docker-compose.yml
docker compose up -d <main-service>
sleep 30
docker ps --filter 'name=<container-prefix>' --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
")
```

Dann Root Cause analysieren, Breaking Changes prüfen, ggf. Env-Vars anpassen.

---

## Checkliste

```
[ ] Changelog gelesen — keine Breaking Changes
[ ] Pre-Upgrade Backup erstellt + Größe verifiziert
[ ] Neues Image gepullt
[ ] Compose aktualisiert + Container gestartet
[ ] Health-Check grün (HTTP 200)
[ ] OIDC funktioniert (HTTP 302)
[ ] API funktioniert (JSON response)
[ ] Daten intakt (gleiche Anzahl)
[ ] Altes Image entfernt
[ ] Repo aktualisiert + committed
[ ] Cascade Memory aktualisiert
```
