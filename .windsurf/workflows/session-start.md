---
description: Session starten — Kontext laden, Stand prüfen, sicher loslegen
---

# /session-start

> Gegenstück: `/session-ende`
> Zwei Umgebungen: **WSL** (`/home/dehnert/github/`) und **Dev Desktop** (`/home/devuser/github/`)

---

## Phase 0: Umgebung synchronisieren (IMMER zuerst)

### 0.0 Server-Erreichbarkeit prüfen (PFLICHT — vor allen MCP/SSH-Calls)

⚠️ **NIEMALS `ping` verwenden** — Hetzner-Server blockieren ICMP (100% packet loss ist NORMAL).
TCP-Probe auf SSH (22), HTTP (80), HTTPS (443) stattdessen:

// turbo
```bash
python3 ~/github/platform/infra/scripts/server_probe.py --host 88.198.191.108
```

→ **Server erreichbar**: Normal weiter mit Phase 0.1
→ **Server NICHT erreichbar**: Alle MCP-Calls und SSH-Befehle werden hängen!
  Fallback: `ssh -o ConnectTimeout=10 -o BatchMode=yes root@88.198.191.108 "uptime"`
  Wenn auch SSH scheitert: Hetzner Cloud Console → Server Status prüfen
→ Lesson Learned 2026-04-03: Ping-basierte Diagnose führte zu Fehldiagnose "Server down"

### 0.1 Platform-Repo pullen (enthält Workflows + ADRs)

// turbo
```bash
cd ~/github/platform && git pull --rebase --quiet
```

### 0.2 Workflow-Symlinks aktualisieren

// turbo
```bash
GITHUB_DIR=~/github bash ~/github/platform/scripts/sync-workflows.sh 2>&1 | grep -E "LINK|REPLACE|WARN" | head -20
```
→ Stellt sicher, dass alle Repos die aktuellen Workflows haben.
→ Neue Workflows in platform werden automatisch verteilt.

### 0.3 Aktuelles Workspace-Repo + Kern-Repos synchronisieren

// turbo
```bash
# Aktuelles Repo
git stash --quiet 2>/dev/null
git pull --rebase --quiet
git stash pop --quiet 2>/dev/null

# Kern-Repos (MCP-Infrastruktur)
for repo in mcp-hub platform risk-hub; do
  (cd ~/github/$repo && git pull --rebase --quiet 2>/dev/null) &
done
wait
echo "Git Sync done"
```
→ Stellt sicher, dass WSL ↔ Dev Desktop synchron sind.
→ Bei Konflikten: `git stash pop` manuell lösen, NICHT force-pushen.

### 0.4 SSH Tunnel prüfen — PFLICHT (pgvector MUSS erreichbar sein)

// turbo
```bash
if ! ss -tlnp | grep -q 15435; then
  echo "⚠️ SSH-Tunnel nicht aktiv — starte..."
  sudo systemctl start ssh-tunnel-postgres
  sleep 2
fi
if ss -tlnp | grep -q 15435; then
  echo "✅ pgvector Tunnel aktiv (localhost:15435)"
else
  echo "❌ FEHLER: pgvector Tunnel nicht erreichbar! Memory funktioniert NICHT."
  echo "   Fix: sudo systemctl start ssh-tunnel-postgres"
  echo "   ABBRUCH — pgvector ist Pflicht, kein Fallback erlaubt."
fi
```
→ **KEIN Fallback auf Cascade Memory erlaubt.** pgvector MUSS laufen.
→ Bei Fehler: Session NICHT fortsetzen bis Tunnel steht.

### 0.5 Deploy-Infrastruktur prüfen (ADR-156)

// turbo
```bash
bash ~/github/mcp-hub/scripts/verify-adr156.sh
```
→ Muss `ALL 21 CHECKS PASSED` zeigen.
→ Bei Fehlern: MCP-Server neustarten, dann erneut prüfen.

### 0.6 Deploy-Status aller Apps scannen (ADR-156)

Prüfe ob kürzlich fehlgeschlagene Deploys vorliegen:

```
mcp0_ssh_manage:
  action: exec
  host: 88.198.191.108
  command: "for repo in risk-hub billing-hub cad-hub coach-hub trading-hub travel-beat weltenhub wedding-hub pptx-hub; do bash /opt/deploy-core/deploy-status.sh $repo 2>/dev/null; done"
```

→ Für jedes Repo mit `"status":"FAILED"`: Deploy-Log lesen und Error Pattern loggen:
```
mcp2_log_error_pattern:
  repo: <repo>
  symptom: "Deploy FAILED: <aus Log>"
  root_cause: "<Analyse>"
  fix: "<empfohlener Fix>"
  error_type: deploy
```
→ User über fehlgeschlagene Deploys informieren, bevor an anderen Tasks gearbeitet wird.

### 0.7 Staging-Health-Check (ADR-157)

Prüfe ob Staging-Services auf Dev Desktop (88.99.38.75) erreichbar sind:

// turbo
```bash
python -c "
import yaml, urllib.request, socket
from pathlib import Path
d = yaml.safe_load(Path('$HOME/github/platform/infra/ports.yaml').read_text())
ok = fail = skip = 0
for name, cfg in sorted(d.get('services',{}).items()):
    if not cfg or not cfg.get('staging'): continue
    port = cfg['staging']
    try:
        s = socket.create_connection(('88.99.38.75', port), timeout=2)
        s.close()
        ok += 1
    except (socket.timeout, ConnectionRefusedError, OSError):
        skip += 1
print(f'Staging: {ok} up, {skip} nicht erreichbar (normal wenn nicht deployed)')
"
```
→ Informativ, kein Blocker. Zeigt welche Hubs auf Staging laufen.

---

## Phase 1: Kontext laden

1. **Repo-Kontext laden** — AGENT_HANDOVER.md, CORE_CONTEXT.md, ADR-Index, `get_context_for_task()`
2. **Health Dashboard** (bei Infra/Deploy-Sessions) — `system_manage(action: health_dashboard)`
3. **Aufgabe klären** — Issue? Use Case? ADR? Governance?
4. **Branch-Status prüfen** — `git status && git log --oneline -5`
5. **Tests baseline** — `pytest tests/ -q --tb=no` (falls vorhanden)
6. **Knowledge-Lookup** — Outline durchsuchen (Repo-Steckbrief, Task-Wissen, Lessons, Cascade-Aufträge)
7. **ADR-Inputs prüfen** — Neue Input-Dokumente aus Outline abholen:
```
search_knowledge(query: "Input ADR", collection: null, limit: 10)
```
→ Sucht nach Dokumenten mit Titel "Input ADR-XXX: ..." in allen Collections.
→ Unbearbeitete Inputs (ohne ✅ im Titel) dem User melden.
→ Workflow: User erstellt `Input ADR-156: Deploy-Script Referenz` in Outline → Cascade findet es hier.
→ Nach Verarbeitung: Titel auf `✅ Input ADR-156: ...` setzen via `update_document()`.

---

## Phase 2: pgvector Warm-Start (ADR-154)

8. **Memory Warm-Start** — Relevante Memories aus früheren Sessions laden:
```
agent_memory_context(
  task_description: "<User-Aufgabe aus erster Nachricht>",
  top_k: 5
)
```
→ Zeigt relevante Session-Summaries, Error-Patterns und Lessons.
→ Falls leer: normal weiterarbeiten (Memory füllt sich über `/session-ende`).

9. **Delta-Check** — Was hat sich seit der letzten Session geändert?
```
get_session_delta()
```

10. **Bekannte Fehler prüfen** (bei Bug-Fix-Sessions):
```
find_similar_errors(query: "<Fehlerbeschreibung>", repo: "<aktuelles Repo>")
```

11. **Wiederkehrende Fehler prüfen** (automatisch, jede Session):
```
check_recurring_errors()
```
→ 🟡 ESCALATED (3-5x): nachhaltige Lösung untersuchen.
→ 🔴 CRITICAL (≥6x): sofortige Analyse, Blocker für andere Tasks.

---

## Phase 3: Arbeitsplan

12. **Arbeitsplan aufstellen** — Schritte, Komplexität, Risk Level, Gate (unter Einbezug der Warm-Start-Ergebnisse + Eskalationen)
