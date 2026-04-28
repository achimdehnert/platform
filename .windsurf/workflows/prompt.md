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

## Schritt 2 — Repo-Kontext laden (via MCP — nur 2 Calls)

> **Token-sparend:** `project-facts.md` enthält alle Repo-Fakten — kein separater Settings/Apps/HTMX-Call nötig.

```
MCP: mcp0_get_file_contents(owner="achimdehnert", repo=REPO, path="project-facts.md")
```

Falls 404 → Fallbacks:
1. `.windsurf/rules/project-facts.md`
2. Direkt `gen-project-facts` Workflow triggern:
   ```
   TOKEN=$(cat ~/.secrets/github_PAT)
   curl -s -X POST -H "Authorization: token $TOKEN" \
     "https://api.github.com/repos/achimdehnert/platform/actions/workflows/gen-project-facts.yml/dispatches" \
     -d "{\"ref\":\"main\",\"inputs\":{\"target_repo\":\"REPO\"}}"
   ```
   Dann 30s warten und erneut laden.

**Aus project-facts.md extrahieren:**
- `SETTINGS_MODULE` (Prod-Modul)
- `TEST_SETTINGS_MODULE` (Test-Modul)
- `HTMX_DETECTION` (exakt — nicht raten!)
- `LOCAL_APPS` (Apps-Liste)
- `PROD_URL`, `PORT`, `DB_NAME`, `PYTHONPATH`

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

## Schritt 3.5 — Affected Files suchen (1 MCP-Call)

Suche nach dem Kernbegriff der Anweisung im Repo-Code:

```
MCP: mcp0_search_code(q="[SCHLÜSSELBEGRIFF] repo:achimdehnert/[REPO]")
```

Extrahiere die Top-3 relevantesten Dateipfade (z.B. `src/identity/views.py`, `src/identity/services.py`).
Falls keine Treffer: leere Liste übergeben.

---

## Schritt 4 — Prompt via Script generieren (Groq oder Template)

Speichere `project-facts.md` Inhalt in `/tmp/pf_[REPO].md` und rufe auf:

```bash
${GITHUB_DIR:-~/CascadeProjects}/platform/.venv/bin/python \
  ${GITHUB_DIR:-~/CascadeProjects}/platform/scripts/run_prompt.py \
  --repo [REPO] \
  --instruction "[INSTRUCTION]" \
  --context-file /tmp/pf_[REPO].md \
  --affected-files "[FILE1],[FILE2],[FILE3]" \
  --task-type [TASK_TYPE]
```

**Mit Groq-Key** (`~/.secrets/groq_api_key` vorhanden): Llama-3.3-70B generiert den Prompt (~0.5s, kostenlos).
**Ohne Key**: Template-Fallback — gleiche Qualität, kein LLM nötig.

Den Script-Output direkt dem User ausgeben (nicht nochmal durch mich re-generieren lassen).

---

## Schritt 4b — Nur wenn Script nicht ausführbar (IDE-Einschränkung)

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
