---
adr_id: ADR-061
title: "Adopt hardcode_scanner.py as Platform-wide Hardcoding Prevention Tool"
status: Proposed
date: 2026-02-21
author: Achim Dehnert
scope: platform (all repos)
repos:
  - platform
  - dev-hub
  - bfagent
  - mcp-hub
  - trading-hub
  - cad-hub
  - travel-beat
  - risk-hub
related: ADR-021 (Deployment Standard), ADR-045 (Secrets Management/SOPS), ADR-046 (Docs Hygiene), ADR-059 (ADR Drift Detector), ADR-060 (Developer Workstation SSH)
amended: 2026-02-22
tags: [security, governance, hardcoding, secrets, configuration]
---

# ADR-061: Adopt hardcode_scanner.py as Platform-wide Hardcoding Prevention Tool

## 1. Executive Summary

Hardcodierte Werte (IPs, Ports, Secrets, URLs, Pfade) sind eine der häufigsten Ursachen für
Deployment-Fehler, Security-Incidents und Konfigurationsdrift über alle 8 Platform-Repos.
Diese ADR definiert eine verbindliche Strategie zur systematischen Erkennung und Elimination
aller Hardcoding-Probleme sowie zur Prävention neuer Verstöße.

**Kernbefund aus erstem Scan (2026-02-21):**
- 119 Findings über 7 Repos (39 Critical, 80 High)
- Kritischster Fund: echte API-Keys (Gemini, Groq, Anthropic) in `bfagent/views_ai_config.py`
- Sofortmaßnahme bereits durchgeführt: Keys durch `os.environ.get()` ersetzt

---

## 2. Problem Statement

| Kategorie | Findings | Kritischste Beispiele |
|-----------|----------|-----------------------|
| **SECRET** | 16 | API-Keys (Gemini, Groq, Anthropic) direkt im Code |
| **PORT** | 65 | `localhost:8000` hardcodiert in Views/Tests |
| **IP** | 26 | `88.198.191.108`, `46.225.113.1` in Python-Code |
| **PATH** | 8 | `/opt/dev-hub/`, `/home/deploy/` in Code |
| **URL** | 4 | `https://devhub.iil.pet` in Python-Code |
| **DOMAIN** | 0 | (via ALLOWED_HOSTS abgedeckt) |

**Auswirkungen:**
- Security: Leaked API-Keys können missbraucht werden (Kosten, Datenverlust)
- Portabilität: Kein Staging/Dev-Environment möglich ohne Code-Änderungen
- Drift: Werte in Code und `.env.prod` laufen auseinander → Silent failures
- CI/CD: Tests schlagen fehl wenn Ports/IPs nicht verfügbar

---

## 3. Decision Drivers

- **Security**: Keine Credentials im Git-History (auch nicht in alten Commits)
- **12-Factor App**: Config via Environment, nicht via Code
- **Portabilität**: Gleicher Code in Dev, Staging, Prod
- **Automatisierung**: Scanner läuft in CI — kein manueller Review nötig
- **Pragmatismus**: Nicht alle Hardcodings sind gleich kritisch — Severity-basiertes Vorgehen

---

## 4. Considered Options

### Option A: Manuelle Code-Reviews (Status quo)
- **Pro**: Kein Aufwand für Tooling
- **Con**: Nicht skalierbar, fehleranfällig, keine Garantie

### Option B: `detect-secrets` (Yelp) als Pre-commit Hook
- **Pro**: Etabliertes Tool, viele Pattern
- **Con**: Nur Secrets, keine IPs/Ports/Pfade; false-positive-lastig; kein Platform-Kontext

### Option C: Eigener `hardcode_scanner.py` + CI-Integration ✅ **Gewählt**
- **Pro**: Platform-spezifische Pattern, Severity-Stufen, JSON-Output für dev-hub, kein externer Dependency
- **Con**: Eigene Wartung nötig

### Option D: Kombination C + `detect-secrets` für Secrets-Layer
- **Pro**: Beste Coverage
- **Con**: Zwei Tools zu pflegen — für spätere Phase vorgesehen

---

## 5. Decision Outcome

**Gewählt: Option C** — `hardcode_scanner.py` als primäres Tool, in CI integriert.

**Begründung:** Option C wird gewählt, weil (a) platform-spezifische Pattern (IPs, Ports, Pfade) von generischen Tools wie `detect-secrets` nicht erkannt werden, (b) kein externer Dependency eingeführt wird, (c) der JSON-Output direkt in dev-hub AgentRun-Dashboard integrierbar ist, und (d) Severity-Stufen ein pragmatisches, phasenweises Vorgehen ermöglichen. Option D (C + `detect-secrets`) wird für Phase 3 vorgesehen, wenn der Scanner stabil ist.

### 5.1 Kategorien und Severity

| Kategorie | Severity | Beispiel | Fix-Strategie |
|-----------|----------|---------|---------------|
| API-Keys/Tokens | **Critical** | `api_key = 'sk-ant-...'` | `os.environ.get('ANTHROPIC_API_KEY')` |
| Server-IPs | **Critical** | `88.198.191.108` in Code | `settings.DEPLOY_HOST` oder env var |
| SECRET_KEY | **Critical** | `SECRET_KEY = 'abc...'` | `config('SECRET_KEY')` via decouple |
| localhost-URLs | **High** | `http://localhost:8000` | `settings.BASE_URL` |
| Absolute Pfade | **High** | `/opt/dev-hub/` | `DEPLOY_PATH` env var |
| GitHub-Org | **Low** | `'achimdehnert'` in Code | `settings.GITHUB_ORG` |

### 5.2 Fix-Strategie pro Typ

```python
# ❌ Vorher
api_key = 'sk-ant-api03-...'
ALLOWED_HOSTS = ['devhub.iil.pet']
BASE_URL = 'http://localhost:8000'

# ✅ Nachher
import os
from decouple import config, Csv

api_key = os.environ.get('ANTHROPIC_API_KEY', '')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='localhost')
BASE_URL = config('BASE_URL', default='http://localhost:8000')
```

### 5.3 Env-Var Konvention (Platform-Standard)

| Typ | Naming-Convention | Beispiel |
|-----|-------------------|---------|
| API-Keys | `<PROVIDER>_API_KEY` | `ANTHROPIC_API_KEY`, `GROQ_API_KEY` |
| Server-Hosts | `DEPLOY_HOST`, `DEV_HOST` | `88.198.191.108` |
| Ports | `<SERVICE>_PORT` | `DEVHUB_PORT=8000` |
| Basis-URLs | `<SERVICE>_BASE_URL` | `DEVHUB_BASE_URL` |
| Pfade | `<SERVICE>_DEPLOY_PATH` | `DEVHUB_DEPLOY_PATH=/opt/dev-hub` |
| GitHub | `GITHUB_ORG`, `GITHUB_TOKEN` | `achimdehnert` |

---

## 5a. Pros and Cons of the Options

### Option A: Manuelle Code-Reviews

- **Pro:** Kein Tooling-Aufwand
- **Con:** Nicht skalierbar über 8 Repos
- **Con:** Keine Garantie — menschliche Fehler unvermeidbar
- **Con:** Kein Audit-Trail

### Option B: `detect-secrets` (Yelp)

- **Pro:** Etabliertes, gut gepflegtes Tool
- **Pro:** Viele Secret-Pattern out-of-the-box
- **Con:** Erkennt nur Secrets — keine IPs, Ports, Pfade, URLs
- **Con:** Hohe False-Positive-Rate ohne Platform-Kontext
- **Con:** Kein JSON-Output für dev-hub Integration

### Option C: Eigener `hardcode_scanner.py` ✅ Gewählt

- **Pro:** Platform-spezifische Pattern (IPs, Ports, Pfade, GitHub-Org)
- **Pro:** Severity-Stufen (Critical/High/Low) für phasenweises Vorgehen
- **Pro:** JSON-Output direkt in dev-hub AgentRun integrierbar
- **Pro:** Kein externer Dependency
- **Con:** Eigene Wartung nötig — Pattern müssen aktuell gehalten werden
- **Con:** Kein Baseline-Mechanismus (alle Findings bei jedem Lauf)

### Option D: Kombination C + `detect-secrets`

- **Pro:** Beste Coverage (Platform-Pattern + Secret-Pattern)
- **Pro:** Defense-in-depth
- **Con:** Zwei Tools zu pflegen
- **Con:** Erhöhte CI-Laufzeit
- **Entscheidung:** Für Phase 3 vorgesehen (nach Scanner-Stabilisierung)

---

## 6. Implementation Plan

### Phase 1 — Sofortmaßnahmen (diese Woche) ✅ Teilweise done

| # | Aufgabe | Repo | Status |
|---|---------|------|--------|
| 1 | API-Keys aus `views_ai_config.py` entfernen | bfagent | ✅ Done |
| 2 | `hardcode_scanner.py` erstellen | platform/scripts | ✅ Done |
| 3 | CI-Job in `sync-adrs-to-devhub.yml` | platform | ✅ Done |
| 4 | GitHub Secret `DEVHUB_WEBHOOK_SECRET` setzen | platform/bfagent | ⏳ Pending |
| 5 | `GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY` in bfagent `.env.prod` | bfagent | ⏳ Pending |

### Phase 2 — Systematische Bereinigung (nächste 2 Sprints)

| Priorität | Repo | Findings | Aufwand |
|-----------|------|----------|---------|
| 1 | bfagent | 62 (PORT-heavy) | 2h |
| 2 | platform | 26 (IP/PATH) | 1h |
| 3 | mcp-hub | 10 | 30min |
| 4 | travel-beat, risk-hub, cad-hub | 17 | 1h |

### Phase 3 — Prävention (dauerhaft)

- `hardcode_scanner.py --severity critical` als **CI-Gate** (exit code 1 blockiert merge)
- Pre-commit hook für lokale Entwicklung
- Quarterly full-scan als Celery-Task in dev-hub (via `AgentType.GUARDIAN`)

---

## 7. Tooling

### `hardcode_scanner.py` — Verwendung

```bash
# Alle Repos, alle Severities
python3 scripts/hardcode_scanner.py

# Nur ein Repo, nur Critical
python3 scripts/hardcode_scanner.py --repo bfagent --severity critical

# JSON-Output für dev-hub Integration
python3 scripts/hardcode_scanner.py --format json > findings.json

# CI-Gate (exit 1 bei critical/high)
python3 scripts/hardcode_scanner.py --severity high
```

### CI-Gate Workflow-Snippet

```yaml
- name: Hardcoding Scan (Critical Gate)
  run: |
    python3 scripts/hardcode_scanner.py \
      --severity critical \
      --format json \
      --output findings.json
    CRITICAL=$(python3 -c "import json; d=json.load(open('findings.json')); print(sum(1 for f in d.get('findings',[]) if f['severity']=='critical'))")
    if [ "$CRITICAL" -gt 0 ]; then
      echo "❌ $CRITICAL critical hardcoding finding(s) — merge blocked"
      cat findings.json
      exit 1
    fi
    echo "✅ No critical hardcoding findings"
```

### Neue Pattern hinzufügen

Pattern werden in `PATTERNS`-Liste in `hardcode_scanner.py` definiert:

```python
{
    "category": "SECRET",
    "severity": "critical",
    "pattern": r"openai_key\s*=\s*['\"][^'\"]{20,}['\"]",
    "description": "OpenAI Key hardcodiert",
    "suggestion": "→ config('OPENAI_API_KEY') via python-decouple",
}
```

---

## 8. Consequences

### Positive
- Keine API-Keys mehr im Git-History (nach BFG Repo Cleaner Lauf)
- Gleicher Code läuft in Dev/Staging/Prod ohne Änderungen
- CI blockiert neue Hardcoding-Verstöße automatisch
- Scanner-Output fließt in dev-hub Dashboard (AgentRun)

### Negative / Risiken
- **Git-History**: Alte Commits enthalten noch die Keys → BFG Repo Cleaner nötig (separater Task)
- **False Positives**: Scanner kann legitime Werte flaggen (z.B. Beispiel-IPs in Docs) → `exclude_dirs` konfigurieren
- **Env-Var Proliferation**: Viele neue env vars → `.env.example` muss gepflegt werden
- **SOPS/ADR-045**: Für hochsensible Secrets (API-Keys in Prod) ist `os.environ.get()` ausreichend; SOPS-Encryption (ADR-045) bleibt optionale Erweiterung für Repos mit erhöhtem Schutzbedarf

### Offene Fragen
- BFG Repo Cleaner für bfagent-History: wann, wer, Koordination mit Team? → Separater Task, kein ADR nötig
- Staging-Environment: Voraussetzung für vollständige 12-Factor-Compliance → wird in **ADR-062 (Staging Environment Strategy)** adressiert (geplant Q2 2026)

---

## 8a. Secrets Management Abgrenzung (ADR-045)

Diese ADR adressiert **Erkennung und Prävention** von Hardcoding. Die Frage *wie* Secrets sicher gespeichert werden, ist in **ADR-045 (Secrets Management / SOPS)** geregelt:

| Aspekt | ADR-061 (diese ADR) | ADR-045 |
|--------|--------------------|---------|
| Scope | Erkennung von Hardcoding im Code | Sichere Speicherung von Secrets |
| Tool | `hardcode_scanner.py` | SOPS / python-decouple |
| Trigger | CI-Gate (jeder Push) | Deployment-Zeit |
| Ziel | Kein Secret im Git | Verschlüsselte `.env.prod` |

Für Repos mit erhöhtem Schutzbedarf (z.B. bfagent mit Anthropic/Groq-Keys) wird SOPS-Encryption gemäß ADR-045 **empfohlen**, ist aber nicht Pflicht dieser ADR.

---

## 9. Confirmation

Diese ADR gilt als implementiert wenn:
1. `hardcode_scanner.py --severity critical` in CI läuft und bei Findings fehlschlägt
2. Alle **Critical**-Findings aus Phase-1-Scan behoben sind
3. `.env.example` für alle Repos die neuen env vars dokumentiert
4. bfagent `.env.prod` enthält `GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`

---

## 10. More Information

- **ADR-021**: Deployment Standard — Env-Var Konventionen für `DEPLOY_HOST`, `DEPLOY_USER`
- **ADR-045**: Secrets Management / SOPS — Sichere Speicherung von Credentials
- **ADR-046**: Docs Hygiene — `.env.example` Pflege
- **ADR-054**: Architecture Guardian — automatische Compliance-Prüfung
- **ADR-059**: ADR Drift Detector — Quarterly Full-Scan als Celery-Task
- **ADR-060**: Developer Workstation SSH — SSH-Key Konventionen
- **`hardcode_scanner.py`**: `platform/scripts/hardcode_scanner.py`
- **MADR 4.0**: https://adr.github.io/madr/

---

## 11. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| hardcode_scanner.py erstellt | ✅ Done | 2026-02-21 | 6 Kategorien, 119 Findings |
| bfagent API-Keys entfernt | ✅ Done | 2026-02-21 | views_ai_config.py |
| CI-Job in sync-adrs-to-devhub.yml | ✅ Done | 2026-02-21 | platform repo |
| ADR-061 erstellt | ✅ Done | 2026-02-21 | |
| CI-Gate in dev-hub ci-cd.yml | ✅ Done | 2026-02-22 | hardcode-scan Job, exit 1 bei Critical |
| dev-hub hardcoded IP entfernt | ✅ Done | 2026-02-22 | ci-cd.yml + populate_catalog.py |
| bfagent Git-History bereinigt | ✅ Done | 2026-02-22 | Echte Keys als ***REMOVED*** — keine Keys mehr in History |
| ADR-061 Review-Fixes | ✅ Done | 2026-02-22 | MADR 4.0 Compliance, SOPS-Abgrenzung, Pros/Cons |
| GitHub Secrets setzen | ⏳ Pending | | GEMINI/GROQ/ANTHROPIC_API_KEY in bfagent |
| Phase 2 Bereinigung | ⏳ Pending | | 62 bfagent PORT-findings |
| Scanner noqa-Support | ⏳ Pending | | False Positives (test passwords, dummy keys) |
