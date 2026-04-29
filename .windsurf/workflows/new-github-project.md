---
description: GitHub-Infrastruktur in einem Repo verankern — Issue Templates, ADR, Use Cases, CORE_CONTEXT, AGENT_HANDOVER, Perfect Prompt
---

# New GitHub Project Infrastructure Workflow

**Trigger:** User sagt eines von:
- "GitHub-Infra für [repo] einrichten"
- "Issue Templates für [repo] anlegen"
- "Repo [name] für Coding Agents vorbereiten"
- `/new-github-project`

> Unterschied zu `/onboard-repo`: Dieser Workflow richtet die **Dokumentations- und
> Template-Infrastruktur** ein (Issue Forms, ADRs, Use Cases, Agent-Kontext).
> `/onboard-repo` richtet die **technische Infrastruktur** ein (Docker, CI/CD, Server).
> Beide ergänzen sich — für ein neues Repo idealerweise beide ausführen.

---

## Step 0: Infos sammeln

```
Ich brauche folgende Infos für [REPO_NAME]:
1. Produkt-Beschreibung (1–2 Sätze)
2. Tech Stack (z.B. Django 5.1 + PostgreSQL + HTMX)
3. Betroffene Django-Apps (z.B. apps.core, apps.books, apps.community)
4. Production-Domain(s)
5. Related Repos (falls vorhanden)
```

---

## Step 1: GitHub Issue Templates anlegen

Erstelle `.github/ISSUE_TEMPLATE/` mit 4 YAML-Formularen:

### 1.1 `bug_report.yml`

```yaml
name: "🐛 Bug Report"
description: "Einen Fehler melden"
title: "[BUG] "
labels: ["bug", "triage"]
body:
  - type: textarea
    id: summary
    attributes:
      label: "Zusammenfassung"
      description: "Was passiert? Was wird erwartet?"
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: "Reproduktionsschritte"
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: "Erwartetes Verhalten"
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: "Tatsächliches Verhalten"
    validations:
      required: true
  - type: textarea
    id: environment
    attributes:
      label: "Umgebung"
      description: "Branch, Commit, Browser, OS"
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: "Logs / Traceback"
      render: text
  - type: dropdown
    id: severity
    attributes:
      label: "Schweregrad"
      options:
        - "critical — Produktionsausfall"
        - "high — Kernfunktion defekt"
        - "medium — Workaround möglich"
        - "low — Kosmetisch"
    validations:
      required: true
  - type: checkboxes
    id: checklist
    attributes:
      label: "Checkliste"
      options:
        - label: "Auf Duplikate geprüft"
          required: true
        - label: "Auf aktuellem main reproduzierbar"
          required: true
```

### 1.2 `feature_request.yml`

```yaml
name: "✨ Feature Request"
description: "Neue Funktion vorschlagen"
title: "[FEATURE] "
labels: ["enhancement", "triage"]
body:
  - type: textarea
    id: problem
    attributes:
      label: "Problem / Motivation"
    validations:
      required: true
  - type: textarea
    id: solution
    attributes:
      label: "Vorgeschlagene Lösung"
    validations:
      required: true
  - type: textarea
    id: acceptance
    attributes:
      label: "Akzeptanzkriterien (Definition of Done)"
      description: "Checkboxen: Was muss erfüllt sein?"
    validations:
      required: true
  - type: dropdown
    id: priority
    attributes:
      label: "Priorität"
      options:
        - "high — MVP-relevant"
        - "medium — Wichtig, nicht blockierend"
        - "low — Nice-to-have"
    validations:
      required: true
```

### 1.3 `task.yml`

```yaml
name: "📋 Task"
description: "Technische Aufgabe / Refactoring / Chore"
title: "[TASK] "
labels: ["task", "triage"]
body:
  - type: dropdown
    id: task_type
    attributes:
      label: "Task-Typ"
      options:
        - refactoring
        - dependency-update
        - migration
        - ci-cd
        - documentation
        - test-coverage
        - infrastructure
        - performance
        - security
        - chore
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: "Beschreibung"
    validations:
      required: true
  - type: textarea
    id: done
    attributes:
      label: "Definition of Done"
    validations:
      required: true
  - type: dropdown
    id: effort
    attributes:
      label: "Aufwand"
      options:
        - "XS — < 1h"
        - "S — 1-4h"
        - "M — 0.5-1 Tag"
        - "L — 1-3 Tage"
        - "XL — > 3 Tage"
    validations:
      required: true
```

### 1.4 `use_case.yml`

```yaml
name: "🎯 Use Case"
description: "Use Case definieren und tracken"
title: "[UC] "
labels: ["use-case", "triage"]
body:
  - type: input
    id: uc_id
    attributes:
      label: "Use Case ID"
      placeholder: "UC-007"
    validations:
      required: true
  - type: input
    id: uc_name
    attributes:
      label: "Use Case Name"
    validations:
      required: true
  - type: dropdown
    id: uc_level
    attributes:
      label: "Level"
      options:
        - "summary — Epic"
        - "user-goal — Primäres Nutzerziel (Standard)"
        - "subfunction — Hilfsfunktion"
    validations:
      required: true
  - type: input
    id: primary_actor
    attributes:
      label: "Primärer Akteur"
    validations:
      required: true
  - type: textarea
    id: preconditions
    attributes:
      label: "Vorbedingungen"
    validations:
      required: true
  - type: textarea
    id: main_flow
    attributes:
      label: "Hauptszenario (Happy Path)"
      description: "Nummerierte Schritt-für-Schritt-Beschreibung"
    validations:
      required: true
  - type: textarea
    id: postconditions
    attributes:
      label: "Nachbedingungen"
    validations:
      required: true
```

---

## Step 2: Pull Request Template anlegen

Erstelle `.github/PULL_REQUEST_TEMPLATE.md`:

```markdown
## Beschreibung
<!-- Was wurde geändert und warum? -->

## Typ der Änderung
- [ ] 🐛 Bug Fix
- [ ] ✨ Feature
- [ ] 💥 Breaking Change
- [ ] 📋 Refactoring / Chore
- [ ] 📖 Dokumentation
- [ ] 🔧 Infrastructure / CI-CD

## Verknüpfte Issues / ADRs
<!-- Closes #XX | Relates to ADR-XXX | UC-XXX -->

## Testabdeckung
- [ ] Tests hinzugefügt / aktualisiert
- [ ] Alle Tests grün (`pytest`)
- [ ] Manuelle Tests durchgeführt

## Deployment-Hinweise
- [ ] Keine Migrations
- [ ] Migrations vorhanden
- [ ] Neue Env-Variablen: `_______`

## Checkliste
- [ ] Service Layer korrekt (views → services → models)
- [ ] Keine hard-codierten Secrets
- [ ] Ready for Review
```

---

## Step 3: Labels Bootstrap Script anlegen

Erstelle `.github/scripts/bootstrap_labels.py` — idempotentes Label-Setup:

```python
#!/usr/bin/env python3
"""
Usage: python .github/scripts/bootstrap_labels.py --repo owner/repo --token $GITHUB_TOKEN
"""
import argparse, sys, requests

LABELS = [
    {"name": "bug",              "color": "d73a4a", "description": "Fehler"},
    {"name": "enhancement",      "color": "a2eeef", "description": "Neue Funktion"},
    {"name": "task",             "color": "e4e669", "description": "Technische Aufgabe"},
    {"name": "use-case",         "color": "0075ca", "description": "Use Case"},
    {"name": "adr",              "color": "7057ff", "description": "Architecture Decision"},
    {"name": "triage",           "color": "e99695", "description": "Neu, nicht bewertet"},
    {"name": "wontfix",          "color": "ffffff", "description": "Nicht umgesetzt"},
    {"name": "blocked",          "color": "ee0701", "description": "Blockiert"},
    {"name": "good first issue", "color": "7fc97f", "description": "Für Einsteiger"},
    {"name": "documentation",    "color": "0075ca", "description": "Dokumentation"},
    {"name": "security",         "color": "ee0701", "description": "Sicherheitsrelevant"},
    {"name": "dependencies",     "color": "0366d6", "description": "Dependency Update"},
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {args.token}",
                             "Accept": "application/vnd.github+json"})
    resp = session.get(f"https://api.github.com/repos/{args.repo}/labels", params={"per_page": 100})
    existing = {l["name"] for l in resp.json()}
    for label in LABELS:
        if label["name"] in existing:
            session.patch(f"https://api.github.com/repos/{args.repo}/labels/{requests.utils.quote(label['name'])}", json=label)
            print(f"↻ updated: {label['name']}")
        else:
            session.post(f"https://api.github.com/repos/{args.repo}/labels", json=label)
            print(f"✓ created: {label['name']}")

if __name__ == "__main__":
    main()
```

Labels bootstrappen:
```bash
python .github/scripts/bootstrap_labels.py --repo achimdehnert/<REPO> --token $GITHUB_TOKEN
```

---

## Step 4: Dokumentations-Infrastruktur anlegen

### 4.1 `docs/CORE_CONTEXT.md`

Die einzige Wahrheitsquelle für Kontext. Pflichtinhalt:

```markdown
# CORE_CONTEXT — [REPO_NAME]
> Pflichtlektüre für jeden Coding Agent, Contributor und Reviewer.

## 1. Projekt-Identität
| Attribut | Wert |
|---|---|
| Repo | achimdehnert/[REPO_NAME] |
| Produkt | [BESCHREIBUNG] |
| Domains | [domain.de], [domain.ai] |

## 2. Tech Stack
| Schicht | Technologie | Version |
|---|---|---|
| Backend | Django | 5.1 |
| DB | PostgreSQL | 16 |
| Frontend | Tailwind + HTMX | — |

## 3. Django-Konfiguration
Settings: config.settings.base (split: base/development/production/test)
ROOT_URLCONF: config.urls | WSGI: config.wsgi.application
DEFAULT_AUTO_FIELD: BigAutoField ← KEIN UUID
Templates: templates/ (project-root)
HTMX: request.htmx (django_htmx aktiv)

## 4. App-Struktur
| App | Pfad | Zweck |
|---|---|---|
| apps.core | apps/core/ | Health, Utilities |
| apps.[X] | apps/[X]/ | [Zweck] |

## 5. Architektur-Regeln (NON-NEGOTIABLE)
views.py → services.py → models.py
- Views: nur HTTP. Services: Businesslogik. Models: datenzentriert.
- Zero Breaking Changes. Tests: test_should_*. BigAutoField immer.

## 6. Verbotene Muster
| ❌ Verboten | ✅ Korrekt |
|---|---|
| Businesslogik in views.py | services.py |
| UUID als PK | BigAutoField |
| request.headers.get("HX-Request") | request.htmx |
| Templates in apps/<app>/templates/ | templates/<app>/ |
| Hard-coded Secrets | decouple.config() |
```

### 4.2 `docs/AGENT_HANDOVER.md`

Session-Gedächtnis — wird nach jeder Session aktualisiert:

```markdown
# AGENT_HANDOVER — [REPO_NAME]
> Lesen vor jeder Session. Aktualisieren nach jeder Session.

## Aktueller Stand
| Attribut | Wert |
|---|---|
| Zuletzt aktualisiert | YYYY-MM-DD |
| Branch | main |
| Phase | [z.B. MVP / Infrastruktur-Setup] |

## Was wurde zuletzt getan?
- YYYY-MM-DD — [Was wurde gemacht]

## Offene Aufgaben (Priorisiert)
- [ ] [Aufgabe 1]
- [ ] [Aufgabe 2]

## Bekannte Probleme / Technical Debt
| Problem | Priorität |
|---|---|
| [Problem] | High/Medium/Low |

## Wichtige Befehle
```bash
pytest tests/ -q
cd src && python manage.py runserver
```
```

### 4.3 ADR-Infrastruktur

Erstelle `docs/adr/README.md` (Index) und `docs/adr/ADR-000-template.md`.

Template: Vollständiges MADR 4.0 Format — siehe `platform/docs/adr/` als Vorlage.

### 4.4 Use Case Infrastruktur

Erstelle `docs/use-cases/README.md` (Index) und `docs/use-cases/UC-000-template.md`.

Template: RUP/UML-Format mit Hauptszenario, Alternativen, Business Rules.

### 4.5 `docs/PERFECT_PROMPT.md`

Den universellen Agent-Bootstrap-Prompt für dieses Repo (5 Varianten: Bootstrap, BugFix, Feature, ArchReview, UseCase).

---

## Step 5: Ersten echten ADR anlegen

Direkt nach Setup: `docs/adr/ADR-001-[tech-stack].md` anlegen.

```
Status: accepted
Beschreibt: Warum Django/FastAPI/etc. gewählt wurde
Alternativen dokumentiert
Konsequenzen klar benannt
```

---

## Step 6: Verifikation

```
✅ GitHub-Infra Checkliste für [REPO]

Issue Templates:
  [ ] .github/ISSUE_TEMPLATE/bug_report.yml
  [ ] .github/ISSUE_TEMPLATE/feature_request.yml
  [ ] .github/ISSUE_TEMPLATE/task.yml
  [ ] .github/ISSUE_TEMPLATE/use_case.yml
  [ ] .github/PULL_REQUEST_TEMPLATE.md
  [ ] .github/scripts/bootstrap_labels.py

Dokumentation:
  [ ] docs/CORE_CONTEXT.md (vollständig ausgefüllt — kein Platzhalter)
  [ ] docs/AGENT_HANDOVER.md (mit aktuellem Stand)
  [ ] docs/adr/ADR-000-template.md + README.md
  [ ] docs/adr/ADR-001-[stack].md (erster echter ADR)
  [ ] docs/use-cases/UC-000-template.md + README.md
  [ ] docs/PERFECT_PROMPT.md (alle 5 Varianten)
  [ ] docs/konzept/05_project_governance.md

GitHub:
  [ ] Labels gebootstrappt (bug, enhancement, task, use-case, adr, triage, ...)
  [ ] Mindestens 1 Milestone angelegt (z.B. v0.1 — MVP)
  [ ] GitHub Project angelegt + Automationen aktiv
```

---

## Step 7: GitHub Project anlegen

> **Warum:** Ein Project-Board macht Issues planbar, priorisierbar und für alle Agents/Humans sichtbar.
> Ohne Board landen Issues im Nirwana — niemand weiß was gerade aktiv bearbeitet wird.

### 7.1 Project erstellen (GitHub UI oder CLI)

**Via GitHub CLI (empfohlen):**
```bash
gh project create --owner achimdehnert --title "[REPO_NAME] Development" --format json
```

**Via GitHub UI:**
1. Repo → Tab "Projects" → "Link a project" → "New project"
2. Template: **"Board"** (Kanban) wählen
3. Name: `[REPO_NAME] Development` (z.B. "137-hub Development")
4. Visibility: **Private**

### 7.2 Standard-Spalten einrichten

Board-Spalten (in dieser Reihenfolge):
```
📋 Backlog  |  🔍 In Review  |  🚧 In Progress  |  ✅ Done
```

Optionale Zusatzspalten:
```
🧊 Icebox   (nice-to-have, kein Termin)
🚫 Blocked  (wartet auf externe Abhängigkeit)
```

### 7.3 Automationen aktivieren (Pflicht)

Im Project → Settings → Workflows — diese 3 aktivieren:

| Automation | Trigger | Aktion |
|---|---|---|
| **Auto-add to project** | Issue opened | → Status: Backlog |
| **Item closed** | Issue/PR closed | → Status: Done |
| **Pull request merged** | PR merged | → Status: Done |

### 7.4 Custom Fields anlegen (empfohlen)

| Field | Typ | Optionen |
|---|---|---|
| Priority | Single select | 🔴 Critical, 🟠 High, 🟡 Medium, 🟢 Low |
| Type | Single select | Bug, Feature, Task, Use Case, ADR |
| Sprint | Iteration | (optional, wenn Sprints genutzt werden) |

### 7.5 Project mit Repo verknüpfen

Im Repo → Settings → General → "Link to project" → neu erstelltes Project auswählen.

### 7.6 Bestehende Issues ins Board importieren

```bash
# Alle offenen Issues des Repos ins Project importieren
gh issue list --repo achimdehnert/[REPO] --state open --json number \
  | jq '.[].number' \
  | xargs -I{} gh project item-add [PROJECT_NUMBER] --owner achimdehnert --url \
    "https://github.com/achimdehnert/[REPO]/issues/{}"
```

---

## Step 8: Issue Triage Workflow anlegen

> **Was das macht:** Wenn ein Issue erstellt wird (egal über welches Template), triggert ein
> GitHub Actions Workflow automatisch: Labels setzen, ins Repo-Project einordnen,
> kritische Issues ins Platform-Überblick-Project eskalieren.

Erstelle `.github/workflows/issue-triage.yml` — **identisch in ALLEN Repos**.

Das Template liegt in `achimdehnert/137-hub/.github/workflows/issue-triage.yml` (Musterbeispiel).

### Was der Workflow tut

```
Issue opened/edited
       │
       ├─ Title-Prefix → Label
       │   [BUG]     → bug
       │   [FEATURE] → enhancement
       │   [TASK]    → task
       │   [UC]      → use-case
       │   [ADR]     → adr
       │   [HOTFIX]  → hotfix + bug
       │
       ├─ Body-Inhalt → Severity-Label
       │   "critical" → severity:critical
       │   "high —"   → severity:high
       │   "medium —" → severity:medium
       │   "low —"    → severity:low
       │
       ├─ Issue → Repo-Project-Board (immer)
       │   Status: Backlog
       │
       └─ Issue → Platform-Überblick-Project (nur wenn relevant)
           Trigger: severity:critical | severity:high | use-case | adr
```

### Benötigte Konfiguration pro Repo (Settings → Variables/Secrets)

| Name | Typ | Wert | Zweck |
|------|-----|------|-------|
| `PROJECT_NUMBER` | Variable | z.B. `1` | Nummer des Repo-eigenen Projects |
| `PLATFORM_PROJECT_NUMBER` | Variable | z.B. `42` | Nummer des Platform-Überblick-Projects |
| `PROJECT_PAT` | Secret | GitHub PAT | PAT mit `project` + `read:org` Scope |

> **`PROJECT_PAT`** muss ein Personal Access Token sein (nicht `GITHUB_TOKEN`) —
> GitHub Projects V2 API erfordert explizite `project`-Berechtigung.
> PAT anlegen: GitHub → Settings → Developer settings → Personal access tokens → Fine-grained
> Scopes: `project` (read+write), `issues` (read+write), `contents` (read)

### Rollout auf alle Repos

Kopiere `.github/workflows/issue-triage.yml` aus `137-hub` in alle aktiven Repos.
Dann pro Repo: `PROJECT_NUMBER` + `PROJECT_PAT` + `PLATFORM_PROJECT_NUMBER` setzen.

Aktive Repos für Rollout: bfagent, risk-hub, travel-beat, weltenhub, 137-hub,
mcp-hub, dev-hub, pptx-hub, trading-hub, coach-hub, infra-deploy

---

## Step 9: Platform-Überblick-Project anlegen (einmalig)

> **Einmal anlegen bei `achimdehnert/platform`** — dann alle Repos darauf zeigen lassen.

### 9.1 Project erstellen

```bash
gh project create --owner achimdehnert --title "Platform Overview" --format json
# → gibt PROJECT_NUMBER zurück (z.B. 42) — diese in alle Repos als PLATFORM_PROJECT_NUMBER eintragen
```

### 9.2 Board-Struktur

```
📋 Backlog  |  🚨 Critical  |  🚧 In Progress  |  👀 In Review  |  ✅ Done
```

Zusätzliches Feld: **Repo** (Single Select: bfagent, risk-hub, travel-beat, ...)

### 9.3 Filter-Views anlegen

| View-Name | Filter |
|-----------|--------|
| 🚨 Critical | `label:severity:critical` |
| 🔥 High Priority | `label:severity:high` |
| 📐 ADRs | `label:adr` |
| 👤 Use Cases | `label:use-case` |
| Alle Repos | (kein Filter) |

### 9.4 Was automatisch ins Platform-Project kommt

Via `issue-triage.yml` aus jedem Repo:
- Issues mit `severity:critical`
- Issues mit `severity:high`
- Issues mit Label `use-case`
- Issues mit Label `adr`

Alles andere bleibt im Repo-eigenen Board — kein Rauschen im Platform-Überblick.

---

## Verifikation + Referenz

→ **[`docs/onboarding/new-github-project-checklist.md`](../../docs/onboarding/new-github-project-checklist.md)**

Inhalte:
- Vollständige Checkliste (Issue Templates, GitHub Actions, GitHub Projects, Dokumentation)
- Referenz: `137-hub` als Musterbeispiel mit allen Komponenten
