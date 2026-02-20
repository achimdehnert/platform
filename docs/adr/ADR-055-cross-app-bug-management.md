# ADR-055: Cross-App Bug & Feature Management

| Field       | Value                                      |
|-------------|--------------------------------------------|
| **ID**      | ADR-055                                    |
| **Title**   | Cross-App Bug & Feature Management         |
| **Status**  | Accepted                                   |
| **Date**    | 2026-02-20                                 |
| **Author**  | Achim Dehnert                              |
| **Domain**  | platform                                   |
| **Tags**    | bug-management, developer-experience, api  |

---

## Context

Die Platform besteht aus mehreren unabhängigen Apps (dev-hub, travel-beat/drifttales, trading-hub, cad-hub, risk-hub, bfagent u.a.). Bug Management ist eine **Platform-weite Querschnittsaufgabe** — nicht eine Funktion von bfagent.

Entwickler und Tester arbeiten täglich in allen Apps und entdecken Bugs oder haben Feature-Ideen direkt im Kontext der laufenden Anwendung. Das Bug Management muss daher **in jeder App verfügbar** sein, unabhängig davon welche App gerade genutzt wird.

**bfagent dient dabei ausschließlich als zentraler Speicher** (TestRequirement-Datenbank) — vergleichbar mit einem Jira oder GitHub Issues. Die eigentliche Bug-Erfassung, Prompt-Generierung und UI findet in der jeweiligen App statt.

Bisher gibt es keinen einheitlichen Mechanismus um:
- Bugs kontextbezogen zu erfassen (URL, App, Priorität) — **in jeder App**
- Bugs zentral zu verwalten und als `TestRequirement` in bfagent zu speichern
- Einen optimalen Prompt für Cascade/Windsurf zu generieren, damit Bugs sofort bearbeitet werden können
- Die Sichtbarkeit der Bug-Buttons zwischen Development und Production zu steuern

Bestehende Versuche (`bug_reporter.html` in bfagent, travel-beat) sind inkonsistent:
- Unterschiedliche API-Endpunkte (`/bfagent/bug-to-test/` vs. `/bookwriting/api/external/bugs/`)
- Fehlende CORS-Konfiguration
- DB-Fehler durch fehlende Spalten (`initiative_id`)
- Keine einheitliche Cascade-Prompt-Generierung
- Keine klare Dev/Prod-Trennung
- Kein Shared Template — jede App hat eigene Implementierung

---

## Decision

### 1. Zentraler Bug-API-Endpunkt in bfagent

Ein einziger, stabiler, öffentlicher API-Endpunkt in bfagent:

```
POST https://bfagent.iil.pet/api/bugs/report/
```

- **CSRF-frei** (`@csrf_exempt`) — Cross-Origin POST von anderen Apps
- **CORS-offen** für alle `*.iil.pet` und bekannte App-Domains
- **JSON-Body** (kein FormData)
- **Kein Login erforderlich** — App-Key zur Authentifizierung (`X-App-Key` Header)
- **Robuste DB-Insertion** via Raw SQL (kein ORM) um Migrations-Drift zu vermeiden
- **Cascade-Prompt** wird serverseitig generiert und in der Response zurückgegeben

**Request:**
```json
{
  "type": "bug" | "feature",
  "title": "Kurze Beschreibung",
  "description": "Detaillierte Beschreibung",
  "url": "https://devhub.iil.pet/adrs/",
  "priority": "low" | "medium" | "high" | "critical",
  "app_name": "dev-hub",
  "repo_path": "/home/deploy/projects/dev-hub",
  "screenshot": "data:image/png;base64,...",
  "user_email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "id": "uuid",
  "cascade_prompt": "## 🐛 Bug Fix — dev-hub\n\n...",
  "view_url": "https://bfagent.iil.pet/bookwriting/test-studio/requirements/<uuid>/"
}
```

### 2. Einheitliches `bug_reporter.html` Partial (Shared Template)

Ein einziges Template wird in **allen** Apps identisch eingebunden:

```
templates/includes/bug_reporter.html
```

**Struktur:**
- FAB-Container (`position: fixed`, `flex-direction: column`, `bottom: 20px`, `right: 20px`)
- Zwei Buttons: 🐛 Bug (lila) + 📋 Feature (grün)
- Ein Modal für beide Typen
- Formular: Titel + Beschreibung + Priorität + Screenshot (optional)
- Nach Submit: Cascade-Prompt aus API-Response automatisch in Clipboard kopieren
- Graceful Degradation: API nicht erreichbar → Prompt lokal generieren + kopieren

**Guard:** `{% if user.is_authenticated %}` — identisch zu bfagent-Pattern.

### 3. Dev/Prod-Steuerung

| Umgebung    | Mechanismus                                      | Buttons |
|-------------|--------------------------------------------------|---------|
| Development | `SHOW_BUG_REPORTER=True` in `.env`               | ✅ sichtbar |
| Production  | `SHOW_BUG_REPORTER=False` (oder nicht gesetzt)   | ❌ versteckt |
| Fallback    | `DEBUG=True` → Buttons sichtbar                  | ✅ sichtbar |

Template-Guard:
```django
{% if user.is_authenticated and SHOW_BUG_REPORTER %}
```

Context Processor in jeder App:
```python
def bug_reporter(request):
    return {
        "SHOW_BUG_REPORTER": getattr(settings, "SHOW_BUG_REPORTER", settings.DEBUG)
    }
```

### 4. Cascade-Prompt-Standard

Der generierte Prompt folgt einem festen Schema:

```markdown
## 🐛 Bug Fix — {app_name}

**Repo:** `{github_org}/{repo_name}`
**Pfad:** `{repo_path}`
**App:** `{app_module}`
**Seite:** {url}
**Priorität:** {priority}

### ❌ Aktuelles Verhalten
{title}: {description}

### ✅ Erwartetes Verhalten
{expected_behavior}

### Aufgabe
Analysiere den Bug, finde die Ursache in `{repo_path}` und behebe ihn minimal.
```

### 5. Rollout-Reihenfolge

| Phase | App | Aktion |
|-------|-----|--------|
| M1 | bfagent | `/api/bugs/report/` Endpunkt implementieren + CORS + Cascade-Prompt |
| M2 | dev-hub | `bug_reporter.html` + Context Processor + `SHOW_BUG_REPORTER` |
| M3 | travel-beat | `bug_reporter.html` auf neue API umstellen |
| M4 | alle weiteren | cad-hub, risk-hub, trading-hub |

---

## Consequences

### Positiv
- **Ein Endpunkt** — keine URL-Verwirrung mehr
- **Cascade-Prompt serverseitig** — konsistent, versionierbar, erweiterbar
- **Dev/Prod klar getrennt** — ein Setting, eine Entscheidung
- **Graceful Degradation** — API-Ausfall blockiert nicht den Prompt-Workflow
- **Kein CSRF-Problem** — Cross-Origin funktioniert sauber
- **Kein ORM-Drift** — Raw SQL INSERT umgeht Migrations-Probleme

### Negativ / Risiken
- bfagent ist Single Point of Failure für Bug-Erfassung (akzeptabel — Fallback via Clipboard)
- App-Key muss in allen `.env` Dateien gepflegt werden

---

## Alternatives Considered

| Option | Abgelehnt weil |
|--------|----------------|
| Jede App hat eigene Bug-DB | Kein zentrales Management, doppelter Aufwand |
| GitHub Issues direkt | Kein Cascade-Prompt, kein TestRequirement-Lifecycle |
| Bestehenden `/bfagent/bug-to-test/` nutzen | Login-required, kein CORS, FormData statt JSON |
| `/bookwriting/api/external/bugs/` nutzen | Falscher URL-Prefix, DB-Fehler, kein Cascade-Prompt |

---

## ADR Relationships

- **Implements**: ADR-015 (Platform Governance System)
- **Extends**: ADR-049 (App Identity Standard)
- **References**: ADR-054 (Deployment Pre-Flight Validation)

---

## Implementation Plan

### M1 — bfagent: `/api/bugs/report/` (Priorität: hoch)

- [ ] `apps/bfagent/views/bug_report_api.py` — neuer View
- [ ] `config/urls.py` — unter `/api/bugs/report/` registrieren (nicht unter `/bookwriting/`)
- [ ] CORS-Middleware oder manuelle CORS-Header für `*.iil.pet`
- [ ] Cascade-Prompt-Generator Funktion
- [ ] `APP_BUG_REPORT_KEY` Setting für App-Key Validierung

### M2 — dev-hub: Bug Reporter

- [ ] `templates/includes/bug_reporter.html` — einheitliches Template
- [ ] `apps/core/context_processors.py` — `SHOW_BUG_REPORTER` Context Variable
- [ ] `config/settings/base.py` — `SHOW_BUG_REPORTER` Setting
- [ ] `templates/base.html` — Include einbinden
- [ ] `.env.prod` — `SHOW_BUG_REPORTER=True` für aktuelle Test-Phase

### M3 — travel-beat: Migration auf neue API

- [ ] `templates/includes/bug_reporter.html` — URL auf `/api/bugs/report/` aktualisieren
- [ ] `BFAGENT_API_URL` aus Settings

### M4 — Weitere Apps

- [ ] cad-hub, risk-hub, trading-hub analog zu M2/M3

---

## Changelog

| Date       | Author        | Change                    |
|------------|---------------|---------------------------|
| 2026-02-20 | Achim Dehnert | Initial ADR created       |
