---
description: Prod-Incident Decision Tree — diagnose und route zu /hotfix, /rollback, oder Stop. Kein Fix-Workflow selbst.
mode: read-only
---

# /incident

> Einsatz: Prod-Symptom beobachtet (Health-Check rot, 5xx, User-Report, Pager).
> Ziel: in < 2 Minuten Routing-Entscheidung, dann konkreter Folge-Workflow.
> Dieser Workflow ändert nichts — er **diagnostiziert und routet**.

---

## Schritt 1: Sofort-Triage (30 Sekunden)

```bash
REPO=REPO_NAME   # ← setzen
PORT=PORT        # ← setzen (falls Health-Check nicht über Domain läuft)

# Live-Health
curl -sf "https://${REPO}.iil.pet/livez/"  && echo "livez OK"   || echo "livez FAIL"
curl -sf "https://${REPO}.iil.pet/healthz/" && echo "healthz OK" || echo "healthz FAIL"

# Container-Status
ssh root@88.198.191.108 "docker ps --filter name=${REPO} --format '{{.Names}}\t{{.Status}}\t{{.Image}}'"
```

Notiere drei Fakten:
- Container `Up` oder `Restarting` / weg?
- livez/healthz-Antwort (200/5xx/Timeout)?
- Aktueller Image-Tag?

---

## Schritt 2: Zeit-Achse (1 Minute)

```bash
# Letzter Deploy auf main
git -C ~/github/${REPO} log origin/main -1 --format='%h %s (%ar)'

# Offene PRs / WIP?
gh -R achimdehnert/${REPO} pr list --state open
```

**Kern-Frage:** Wann war der letzte Deploy?

| Letzter Deploy | Wahrscheinlichstes Profil |
|---|---|
| < 1 h | Neues Code-Problem — Rollback-Pfad vorrangig |
| 1–24 h | Code möglich, externe Drift möglich — Schritt 4 |
| > 24 h | Externe Drift, Config, Daten — Schritt 4, **nicht** Rollback |

---

## Schritt 3: Decision Tree

| Symptom | Letzter Deploy | Pfad |
|---|---|---|
| Container down / restart-loop | < 1 h | → **`/rollback`** |
| 500s auf **allen** Endpoints | < 1 h | → **`/rollback`** |
| 500s auf neuen Endpoints | < 1 h | → **`/rollback`** |
| Partial: alte Endpoints OK, neue 500 | jeglich | → **`/hotfix`** (Rollback würde Fixes mit zurücknehmen) |
| 500s auf vorher-OK-Endpoints | > 1 h | → Schritt 4 |
| Container OK, aber Health rot | jeglich | → Schritt 4 (oft kein Code-Issue) |
| Daten-Korruption vermutet | jeglich | → **STOP** (Schritt 5) |
| Security-Vorfall (Leak, RCE-Verdacht) | jeglich | → **STOP** (Schritt 5) |
| Mehrere Hubs gleichzeitig betroffen | jeglich | → **STOP** (Schritt 5 — Infra, nicht App) |

---

## Schritt 4: Diagnose (wenn Pfad in Schritt 3 nicht eindeutig)

Drei Hypothesen, in Reihenfolge:

### 4a — Externe Abhängigkeit?

```bash
ssh root@88.198.191.108 "docker logs ${REPO}-web --tail 100 | grep -iE 'connection|timeout|refused|dns|certificate|unreachable'"
```

Treffer → **kein** Code-Fix. Folge-Workflow:
- DB/Redis/Mail-Outage → `/infra-health`
- Cert/DNS → ADR-205 / ADR-206 Kontext, `/nginx-check`

### 4b — Config / Secrets-Drift?

```bash
ssh root@88.198.191.108 "ls -la /opt/${REPO}/.env.prod && md5sum /opt/${REPO}/.env.prod"
```

Modification-Time recent + niemand erinnert sich daran → `/secrets` oder manuelle Env-Wiederherstellung. **Kein `/hotfix`**.

### 4c — Code-Bug, aber Deploy > 1 h alt?

Rollback hilft nicht (alter Stand hat denselben Bug, oder es ist eine externe Drift erst recht aufgetaucht). → **`/hotfix`**.

---

## Schritt 5: STOP — nicht weiter routen

| Fall | Warum kein Folge-Workflow | Was stattdessen |
|---|---|---|
| Daten-Korruption | Rollback kann es verschlimmern, Hotfix riskant ohne klares Bild | Manuell: letzten Backup prüfen (`/backup` Reverse), Restore-Plan, **dann** entscheiden |
| Security (Leak, RCE-Verdacht) | Eskalations-Frage, nicht Tooling | Achim direkt informieren, betroffenen Service ggf. via `docker stop` isolieren |
| Multi-Hub-Outage | Sehr wahrscheinlich Infra-Schicht | `/infra-health` + `/platform-audit`, einzelne Hub-Workflows zurückstellen |
| Symptom > 7 Tage offen | Nicht akut — `/incident` ist für *neue* Lagen | Normaler Bug-Fix-Flow via `/agentic-coding` |

---

## Schritt 6: Hand-Off dokumentieren (Pflicht)

Bevor `/hotfix` oder `/rollback` aufgerufen wird, kurzer Doku-Stub (Issue-Comment, PR-Body, oder Outline-Note):

```
[INCIDENT] ${REPO} — ${YYYY-MM-DD HH:MM}
Symptom:      <livez/healthz-State, Container-Status>
Last deploy:  <git short-sha + Alter>
Diagnose:     <Schritt-3-Match oder Schritt-4-Befund>
Hand-Off:     → /hotfix | /rollback | STOP-Reason
```

> **Warum Pflicht:** Sequenzielle Recovery-Workflows brauchen Trail. Ohne Hand-Off-Stub weiß ein nachfolgender Agent/Mensch nicht, was schon geprüft wurde — Doppel-Diagnose riskiert paralleles Rollback + Hotfix-Konflikt.

### Sequenz „Rollback dann Fix"

Häufiges Muster bei Symptom „Container down nach Deploy" mit gleichzeitig wichtigem Fix im neuen Code:

1. `/rollback` → Bleeding stoppen
2. Stabil? → Issue mit Wiederholungs-Plan
3. Im Folge-Session `/hotfix` mit korrigiertem Code
4. Erneuter Deploy via `/ship`

Die `/incident`-Trail-Notiz hält Phase 1+3 zusammen.

---

## Referenzen

- `/hotfix` — Code-Fix-Pfad, wenn Rollback nicht greift
- `/rollback` — Image-Tag-Reset, wenn vorheriger Stand sauber war
- `/infra-health` — bei Verdacht auf externe Drift (DB, Redis, Network)
- `/drift-check`, `/nginx-check`, `/secrets` — situationsspezifische Tools
- ADR-205 / ADR-206 — TLS/Tunnel-Konfig (häufige externe Drift-Quelle)

## Glossar

| Begriff | Bedeutung |
|---|---|
| **Triage** | Schneller Initial-Check zur Klassifikation eines Incidents — analog zur medizinischen Notaufnahme |
| **livez / healthz** | Standard-Probe-Endpoints: `livez` = Container atmet, `healthz` = App-interne Health-Logik OK |
| **Rollback-Pfad** | Recovery durch Zurücksetzen auf vorherige Image-Version, nicht durch Code-Patch |
| **Hotfix-Pfad** | Recovery durch direkten Patch + Re-Deploy, nicht durch Zurücksetzen |
