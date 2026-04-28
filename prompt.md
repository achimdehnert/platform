---
description: Aus einer kurzen Repo-Anweisung einen optimalen, lückenlosen Prompt generieren — spart Iterations-Overhead durch fehlenden Kontext
---

# /prompt — Optimal Prompt Generator

**Usage:** `/prompt <reponame> "<kurze Anweisung>"`

**Beispiele:**
- `/prompt risk-hub "fix den Login-Bug: redirect nach /accounts/login statt /dashboard"`
- `/prompt tax-hub "neues Model: Steuerrate mit Prozentsatz und Gültigkeitszeitraum"`
- `/prompt writing-hub "refactor: CharacterService auslagern aus views.py"`

---

## Schritt 1 — Input parsen

Extrahiere aus der User-Eingabe:
- **REPO**: Repository-Name (z.B. `risk-hub`)
- **INSTRUCTION**: Die kurze Anweisung (alles in Anführungszeichen)
- **TASK_TYPE**: Einer von `bugfix | feature | refactor | test | deploy | docs` — aus der Anweisung ableiten

---

## Schritt 2 — Repo-Kontext laden (via MCP)

Lade parallel:

```
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="project-facts.md")
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="CORE_CONTEXT.md")
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="AGENT_HANDOVER.md")
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="config/settings")
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="apps")
```

Falls `project-facts.md` 404 → Fallback: `docs/project-facts.md` versuchen.

**Extrakte aus dem Kontext:**
- `SETTINGS_MODULE` — z.B. `config.settings.production`
- `DB_NAME` — PostgreSQL DB-Name
- `HTMX_DETECTION` — `request.htmx` oder `request.headers.get("HX-Request")`
- `AUTH_USER_MODEL` — Custom User oder `auth.User`
- `LOCAL_APPS` — Liste der App-Namen
- `PROD_URL` — Production URL
- `PORT` — Prod-Port

---

## Schritt 3 — Task-Typ-spezifische ADRs ermitteln

| Task-Typ | Relevante ADRs / Constraints |
|----------|------------------------------|
| `bugfix` | Service-Layer (ADR-009), NEVER ORM in views, regression test pflicht |
| `feature` | Service-Layer + DB-First (BigAutoField, kein UUIDField PK, kein JSONField), HTMX-Pattern (ADR-048) |
| `refactor` | Service-Layer-Grenze einhalten, keine API-Brüche, Tests müssen weiter grünen |
| `test` | iil-testkit (ADR-058), `test_should_*` Naming, max 5 Assertions pro Test |
| `deploy` | ADR-094 Preflight, env_file statt environment:, HEALTHCHECK, /livez/ + /healthz/ |
| `docs` | CHANGELOG.md, README.md, kein Code-Brechen |

---

## Schritt 4 — Optimalen Prompt generieren

Generiere jetzt einen vollständigen, selbstenthaltenden Prompt der **alle** folgenden Blöcke enthält.
Der Prompt muss ohne zusätzlichen Session-Kontext funktionieren.

---

**OUTPUT FORMAT — Fertig formatierten Prompt ausgeben:**

````markdown
# [TASK_TYPE]: [INSTRUCTION — kurz auf 1 Zeile]

> Selbstenthaltender Prompt — kein separater Session-Kontext nötig.
> Ziel-Repo: achimdehnert/[REPO] · Stand: [HEUTE YYYY-MM-DD]

---

## Kontext

**Repo:** `[REPO]` · Pfad: `${GITHUB_DIR:-~/CascadeProjects}/[REPO]`
**Tech-Stack:** Django 5.x · PostgreSQL 16 · [HTMX falls in INSTALLED_APPS] · Gunicorn · Docker
**Settings-Modul (Prod):** `[SETTINGS_MODULE]`
**Settings-Modul (Test):** `[TEST_SETTINGS_MODULE]` ← aus pyproject.toml DJANGO_SETTINGS_MODULE
**Auth-User:** `[AUTH_USER_MODEL]`
**Prod-URL:** `https://[PROD_URL]` · Port: `[PORT]`
**Lokale DB:** `[DB_NAME]`

**Apps im Repo:**
[LOCAL_APPS als Liste]

**HTMX-Detection in diesem Repo:** `[HTMX_DETECTION]` ← aus project-facts.md

---

## Aufgabe

**Ziel:** [INSTRUCTION — ausführlich, alle impliziten Details explizit gemacht]

**Betroffene Dateien/Module (Analyse-Pflicht vor Implementierung):**
[Relevante Dateien basierend auf INSTRUCTION und LOCAL_APPS — z.B. apps/[app]/views.py, apps/[app]/services.py]

**Schritt-für-Schritt:**
1. [Konkreter Schritt 1 — aus INSTRUCTION abgeleitet]
2. [Konkreter Schritt 2]
3. [...]
4. Tests schreiben / anpassen

---

## Constraints (NICHT verhandelbar)

### Service-Layer (ADR-009) — CRITICAL
```python
# CORRECT — views.py
def my_view(request):
    result = my_service.do_something(...)
    return render(request, "...", {"result": result})

# BANNED in views.py:
# Model.objects.filter(...)     ← ORM in view
# model.save()                  ← ORM in view
```

### Database-First (ADR-022)
- `DEFAULT_AUTO_FIELD = BigAutoField` — NIEMALS `UUIDField(primary_key=True)`
- Kein `JSONField()` für strukturierte Daten — Lookup-Tabellen
- FK-Naming: `{model}_id` mit `on_delete=PROTECT`

[FALLS HTMX-Task:]
### HTMX (ADR-048)
- IMMER: `hx-target` + `hx-swap` + `hx-indicator` (alle drei, keine Ausnahme)
- IMMER: `data-testid` auf interaktiven Elementen
- Partials: kein `{% extends %}`, kein `<html>`
- Detection: `[HTMX_DETECTION]`

[FALLS Test-Task:]
### Testing (ADR-058)
- Naming: `test_should_{expected_behavior}` — NIEMALS `test_{thing}`
- Max 5 Assertions pro Test
- `@pytest.mark.django_db` bei DB-Tests nicht vergessen
- iil-testkit Fixtures nutzen: `auth_client`, `staff_client`, `db_user`

---

## Akzeptanzkriterien

- [ ] [Kriterium 1 — direkt aus INSTRUCTION ableitbar]
- [ ] [Kriterium 2]
- [ ] Service-Layer-Grenze eingehalten (kein ORM in views.py)
- [ ] Ruff-Check grün: `ruff check . && ruff format --check .`
- [ ] [FALLS bugfix:] Regression-Test vorhanden (`test_should_[was-gefixed-wurde]`)
- [ ] [FALLS feature:] Migration erstellt: `python manage.py makemigrations [app]`
- [ ] Kein `print()` in Code — `logging.getLogger(__name__)` stattdessen

---

## Verboten

- `Model.objects.` direkt in `views.py` oder Templates
- `UUIDField(primary_key=True)`
- `JSONField()` für strukturierte Daten
- Hardcoded Secrets, IPs, API-Keys
- `except:` ohne Exception-Typ
- `unittest.TestCase` — nur pytest-Funktionen
[FALLS HTMX:] - `hx-boost` auf Forms
[FALLS HTMX:] - `onclick=` mit `hx-*` gemischt

---

## Ausgabe-Erwartung

Nach Implementierung folgende Verifikation durchführen:
```bash
cd ${GITHUB_DIR:-~/CascadeProjects}/[REPO]
ruff check . --exit-zero
ruff format --check .
[FALLS Tests:] python -m pytest tests/ -v --tb=short
```

Dann committen: `git add -A && git commit -m "[TASK_TYPE]([app]): [kurze Beschreibung]"`
````

---

## Schritt 5 — Qualitäts-Check des generierten Prompts

Vor der Ausgabe prüfen:
- [ ] Enthält `SETTINGS_MODULE` — kein Raten, aus Kontext geladen
- [ ] Enthält `HTMX_DETECTION` — repo-spezifisch, nicht generic
- [ ] Aufgabe ist in konkrete Schritte zerlegt
- [ ] Akzeptanzkriterien sind messbar (nicht "es funktioniert")
- [ ] Alle Constraints eingebettet — Prompt braucht keinen externen Kontext

Falls ein Feld fehlt (weil Repo-Kontext nicht geladen werden konnte):
→ Feld mit `[TODO: manuell ergänzen — project-facts.md fehlt]` markieren, NICHT weglassen.
