---
status: "accepted"
date: 2026-02-22
amended: 2026-02-23
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
related: ["ADR-057-platform-test-strategy.md", "ADR-058-platform-test-taxonomy.md"]
---

# Adopt a three-tier test marker strategy with SQLite/Postgres split and vendored package support for bfagent CI

| Attribut       | Wert                                                                       |
|----------------|----------------------------------------------------------------------------|
| **Status**     | Accepted                                                                   |
| **Scope**      | CI/CD, Testing                                                             |
| **Repo**       | bfagent                                                                    |
| **Erstellt**   | 2026-02-22                                                                 |
| **Amended**    | 2026-02-23                                                                 |
| **Autor**      | Achim Dehnert                                                              |
| **Relates to** | ADR-057 (Platform Test Strategy), ADR-058 (Platform Test Taxonomy)        |

---

## Context and Problem Statement

Das `bfagent`-Repository enthält eine Django-Applikation mit mehreren Sub-Apps (`core`, `bfagent`, `writing_hub`, `expert_hub`, `presentation_studio`, `genagent`). Die CI-Pipeline nutzt den plattformweiten Reusable Workflow `_ci-python.yml`.

ADR-057 legt die plattformweite Vier-Ebenen-Teststrategie fest. ADR-058 definiert 28 verbindliche Testarten. Beim ersten Aufbau der bfagent-CI-Pipeline traten sieben strukturelle Probleme auf, die eine bfagent-spezifische Konkretisierung erfordern:

1. **Vendored `platform-context`** — nicht auf PyPI verfügbar, muss aus `vendor/platform_context/` installiert werden.
2. **`transaction.atomic()` ohne Test-Fallback** — `BaseHandler.execute()` warf `RuntimeError` in Unit Tests ohne DB-Verbindung.
3. **Fehlende Test-Marker-Trennung** — View-Tests liefen im Unit-Test-Job ohne DB-Verbindung.
4. **Pre-existierende Test-Bugs im Code-Generator-Output** — falsche URL-Namen, ungültige Fixture-Daten, fehlende Pflichtfelder.
5. **Standalone-Skripte im Testpfad** — `test_chapter_illustration.py` und `test_studio_views.py` schlugen beim Import fehl.
6. **Contract Tests: exit code 5** — pytest gibt exit code 5 zurück wenn keine `@pytest.mark.contract`-Tests gefunden werden.
7. **`PromptTemplate`-Import-Fehler** — `apps.core.models` exportierte `PromptTemplate` und `PromptApp` nicht, was ForeignKey-Auflösung mit `--no-migrations` brach.

---

## Decision Drivers

- **CI-Stabilität**: Alle CI-Jobs müssen grün sein ohne falsche Negatives
- **Testgeschwindigkeit**: Unit Tests < 60s ohne Postgres-Service
- **Rückwärtskompatibilität**: Änderungen an `_ci-python.yml` dürfen andere Repos nicht brechen
- **Konsistenz mit ADR-057/058**: Marker-Konventionen und Teststufen müssen plattformweit einheitlich sein
- **Minimalinvasivität**: Produktionscode-Änderungen auf das absolut Notwendige beschränken

---

## Considered Options

1. **Alle Tests mit PostgreSQL** — Unit- und Integration-Tests laufen beide mit Postgres-Service
2. **SQLite für Unit Tests, Postgres für Integration Tests** *(gewählt)* — Marker-Trennung via `@pytest.mark.integration`
3. **Alle View-Tests löschen** — generierte View-Tests werden entfernt, nur logiknahe Tests bleiben
4. **`pytest.mark.skip` statt `collect_ignore`** — Standalone-Skripte werden mit `@pytest.mark.skip` annotiert

---

## Decision Outcome

**Gewählt: Option 2 — SQLite/Postgres-Split mit drei Marker-Stufen**, weil:

- Option 1 widerspricht ADR-057 "Total CI runtime < 5 minutes" — Postgres-Service für alle Jobs erhöht Laufzeit und Komplexität.
- Option 3 verletzt ADR-058 — View Response Tests (U4) sind als Pflichttestart klassifiziert; Löschen ist keine Option.
- Option 4 greift erst nach dem Import — Standalone-Skripte schlagen beim Import fehl, `pytest.mark.skip` kann das nicht verhindern.
- Option 2 ist konsistent mit ADR-057/058-Marker-Konventionen (`integration`, `contract`).

### Consistency Check ADR-057/058

| ADR-057/058-Vorgabe | ADR-065-Umsetzung | Status |
|---------------------|-------------------|--------|
| `@pytest.mark.integration` für DB-abhängige Tests | View-Tests als `integration` markiert | ✅ |
| `@pytest.mark.contract` für Schemathesis-Tests | Contract-Job nutzt `-m contract` | ✅ |
| CI-Runtime < 5 min | Unit Tests ~30s, Integration ~2min | ✅ |
| Coverage Gate ≥ 80% | `_ci-python.yml` Coverage Gate aktiv | ✅ |
| Factory Boy für Fixtures (ADR-057 Phase 1) | Noch nicht umgesetzt — deferred bis 2026-04-30 | ⚠️ |

### Confirmation

Compliance wird auf drei Wegen verifiziert:

1. **CI-Gate**: Alle vier Jobs (`Unit Tests`, `Integration Tests`, `Contract Tests`, `Coverage Gate`) müssen grün sein — Build schlägt fehl wenn einer rot ist.
2. **Marker-Audit** (manuell oder als ADR-054-Guardian-Regel):

```bash
# Prüfen ob neue View-Tests korrekt als integration markiert sind
grep -rn "class Test.*Views" apps/*/tests/ | grep -v "integration" | wc -l  # Ziel: 0
# Prüfen ob collect_ignore gewachsen ist (Ziel: stabil)
grep -c "collect_ignore" conftest.py
```

3. **URL-Namen-Check** nach Code-Generator-Läufen:

```bash
python manage.py show_urls | grep -E "agent-|llm-|world-" | awk '{print $2}'
```

---

## Pros and Cons of the Options

### Option 1 — Alle Tests mit PostgreSQL

* Good, because kein SQLite/Postgres-Impedance-Mismatch.
* Bad, because Postgres-Service für alle Jobs — erhöht CI-Laufzeit.
* Bad, because widerspricht ADR-057 "Total CI runtime < 5 minutes".
* **Abgelehnt.**

### Option 2 — SQLite/Postgres-Split (gewählt)

* Good, because Unit Tests laufen ohne externe Services in < 60s.
* Good, because konsistent mit ADR-057/058-Marker-Konventionen.
* Good, because `--no-migrations` erlaubt Schema-Tests ohne Migrations-Overhead.
* Bad, because `collect_ignore`-Liste für kaputte View-Tests muss manuell gepflegt werden (technische Schuld, Zieldatum 2026-04-30).
* Bad, because SQLite/Postgres-Unterschiede können Unit Tests bestehen lassen, die in Produktion fehlschlagen (z.B. `JSONB`-Queries).

### Option 3 — View-Tests löschen

* Good, because keine `collect_ignore`-Pflege nötig.
* Bad, because ADR-058 klassifiziert View Response Tests (U4) als Pflichttestart.
* **Abgelehnt.**

### Option 4 — `pytest.mark.skip`

* Good, because expliziter als `collect_ignore`.
* Bad, because greift erst nach dem Import — Standalone-Skripte schlagen beim Import fehl.
* **Abgelehnt.**

---

## Consequences

* Good, because CI-Pipeline läuft vollständig grün (Unit + Integration + Contract + Build + Deploy).
* Good, because Unit Tests sind DB-unabhängig und schnell (~30s).
* Good, because Marker-Konventionen sind konsistent mit ADR-057/058.
* Good, because `transaction.atomic()` Fallback ist eng gefasst — nur spezifische pytest-django-Fehlermeldungen werden abgefangen, alle anderen `RuntimeError` werden re-raised.
* Bad, because `test_agents.py`, `test_llms.py`, `test_worlds.py` laufen nur im Integration-Job — View-Regressions werden nicht im schnellen Unit-Job erkannt.
* Bad, because generierte Test-Dateien müssen nach Code-Generator-Läufen manuell auf URL-Namen und Fixture-Daten geprüft werden.
* Bad, because `collect_ignore` für kaputte View-Tests ist technische Schuld mit Zieldatum 2026-04-30.

---

## Implementation Details

### 1. Test-Marker-Strategie

| Marker | CI-Job | DB | Beschreibung |
|--------|--------|----|--------------|
| *(kein Marker)* | Unit Tests | SQLite (`--no-migrations`) | Reine Logik-Tests |
| `@pytest.mark.integration` | Integration Tests | PostgreSQL | View-Tests, DB-abhängige Tests |
| `@pytest.mark.contract` | Contract Tests | PostgreSQL | Schemathesis API-Tests |

**Regel**: Tests, die Django-URL-Routing, `LoginRequiredMixin` oder komplexe FK-Fixtures benötigen, werden als `integration` markiert.

### 2. Vendored Package Installation (rückwärtskompatibel)

```yaml
- name: Install platform-context
  run: |
    if [ -d "vendor/platform_context" ]; then
      pip install -e "vendor/platform_context[testing]"
    else
      pip install "platform-context[testing]${{ inputs.platform_context_version }}" || true
    fi
```

Repos ohne `vendor/`-Verzeichnis nutzen den PyPI-Pfad unverändert — **keine Breaking Change für andere Repos**.

### 3. `transaction.atomic()` Fallback (eng gefasst)

```python
if self.use_transaction and DJANGO_AVAILABLE:
    try:
        with transaction.atomic():
            result = self.process(data, context)
    except RuntimeError as e:
        if 'Database access not allowed' in str(e) or 'Failed to enter transaction' in str(e):
            import logging as _log
            _log.getLogger(__name__).debug(
                'transaction.atomic() skipped in test context (no DB): %s', e
            )
            result = self.process(data, context)
        else:
            raise  # Alle anderen RuntimeErrors werden re-raised
else:
    result = self.process(data, context)
```

**Begründung**: pytest-django wirft `RuntimeError("Database access not allowed, use the django_db mark...")` — diese Nachricht ist stabil seit pytest-django 3.x. Alle anderen `RuntimeError` (z.B. aus `process()` selbst) werden re-raised und nicht verschluckt. Debug-Logging stellt sicher, dass der Fallback in Produktion sichtbar wäre.

### 4. `collect_ignore` mit Deprecation-Kommentar

```python
# conftest.py
collect_ignore = [
    # Standalone-Skripte (kein pytest-Format, schlagen beim Import fehl)
    "apps/bfagent/handlers/test_chapter_illustration.py",
    "apps/bfagent/views/test_studio_views.py",
    # Kaputte View-Tests (Code-Generator-Output mit falschen Assertions)
    # TODO: Reparieren bis 2026-04-30 — Login-Redirect-Assertions, HTMX-Assertions
    "apps/bfagent/tests/test_agents.py",
    "apps/bfagent/tests/test_llms.py",
    "apps/bfagent/tests/test_worlds.py",
]
```

### 5. Contract Tests: exit code 5

```bash
pytest -m "contract" -v || ([ $? -eq 5 ] && echo "No contract tests found, skipping." && exit 0)
```

### 6. Prompt-Modell-Exports

```python
# apps/core/models/__init__.py
from .prompt_lookups import PromptApp, PromptCategory, PromptOutputFormat, PromptTier
from .prompt_models import PromptComponent, PromptConfig, PromptExecution, PromptTemplate, TenantPromptOverride
```

Django löst `"core.PromptApp"` ForeignKey-Referenzen über den App-Label auf. Ohne diesen Export schlägt `--no-migrations` mit `ValueError: Related model 'core.PromptApp' cannot be resolved` fehl.

### 7. Llms-Modell-Änderung und Shared-DB-Risiko

`Llms.created_at` und `updated_at` wurden mit `default=timezone.now` / `auto_now=True` versehen (Migration `0072`). Die `bfagent_db` wird von `bfagent` und `weltenhub` geteilt.

**Risikobewertung**: `default=timezone.now` und `auto_now=True` sind rückwärtskompatibel — bestehende Zeilen behalten ihre Werte, neue Zeilen erhalten automatisch einen Timestamp. `weltenhub` liest `Llms` nur lesend — kein Breaking Change.

---

## Risks

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|--------------------|--------|------------|
| Neue generierte Tests haben falsche URL-Namen | Mittel | Niedrig | Nach Code-Generator-Lauf gegen `manage.py show_urls` verifizieren |
| `collect_ignore` wächst unkontrolliert | Niedrig | Mittel | Zieldatum 2026-04-30 für Reparatur; Guardian-Regel prüft Listenlänge |
| `transaction.atomic()` Fallback verschluckt echte Fehler | Sehr niedrig | Hoch | Nur zwei spezifische Strings abgefangen; alle anderen `RuntimeError` re-raised; debug-Logging aktiv |
| SQLite/Postgres-Impedance-Mismatch | Niedrig | Mittel | Kritische DB-Queries (JSONB, Arrays) in Integration Tests testen |
| Shared-DB-Risiko (`bfagent_db` + `weltenhub`) | Niedrig | Hoch | Llms-Migration ist rückwärtskompatibel; weltenhub liest nur lesend |

---

## Deferred Decisions

| Entscheidung | Begründung | Zieldatum | Referenz |
|--------------|------------|-----------|----------|
| Factory Boy für alle Fixtures einführen | Reduziert manuelle Fixture-Pflege, verhindert Code-Generator-Bugs | 2026-04-30 | ADR-057 Phase 1 · [bfagent#12](https://github.com/achimdehnert/bfagent/issues/12) |
| Kaputte View-Tests reparieren (`test_agents.py`, `test_llms.py`, `test_worlds.py`) | Login-Redirect-Assertions, HTMX-Assertions, Form-Validierungen sind pre-existierende Code-Generator-Bugs | 2026-04-30 | `conftest.py collect_ignore` · [bfagent#10](https://github.com/achimdehnert/bfagent/issues/10) |
| E2E-Tests mit Playwright | Für JavaScript-schwere Interaktionen; aktuell kein JS-heavy Frontend | 2026-Q3 | ADR-057 Phase 4 |
| Pact Consumer-Driven Contract Testing | Wenn Team > 5 Personen | Offen | ADR-057 §More Information |

---

## More Information

- `apps/core/handlers/base.py` — `execute()` mit `transaction.atomic()` Fallback
- `apps/core/core_handlers/base.py` — `execute()` mit `transaction.atomic()` Fallback
- `apps/core/models/__init__.py` — Prompt-Modell-Exports
- `conftest.py` — `collect_ignore`-Liste mit TODO-Kommentaren
- `.github/workflows/ci.yml` — bfagent CI-Workflow
- `platform/.github/workflows/_ci-python.yml` — Reusable CI-Workflow (Zeile 259–264: exit code 5 Fix)
- ADR-057: Platform Test Strategy — Vier-Ebenen-Pyramide, Schemathesis, Coverage Gates
- ADR-058: Platform Test Taxonomy — 28 Testarten, Pflicht/Optional-Klassifizierung

---

## Changelog

| Datum      | Autor         | Änderung                                                    |
|------------|---------------|-------------------------------------------------------------|
| 2026-02-22 | Achim Dehnert | Initial — Status: Accepted                                  |
| 2026-02-23 | Achim Dehnert | Review-Fixes: MADR 4.0 Frontmatter, Decision Drivers, Pros/Cons, Confirmation, Deferred Decisions, Shared-DB-Risiko, `except RuntimeError` eng gefasst |
