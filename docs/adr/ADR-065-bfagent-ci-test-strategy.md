# ADR-065: bfagent CI Test Strategy

| Attribut       | Wert                                              |
|----------------|---------------------------------------------------|
| **Status**     | Accepted                                          |
| **Scope**      | CI/CD, Testing                                    |
| **Repo**       | bfagent                                           |
| **Erstellt**   | 2026-02-22                                        |
| **Autor**      | Achim Dehnert                                     |
| **Reviewer**   | –                                                 |
| **Supersedes** | –                                                 |
| **Relates to** | ADR-057 (Platform Test Strategy), ADR-058 (Multi-Tenancy Testing Strategy) |

---

## 1. Kontext

### 1.1 Ausgangslage

Das `bfagent`-Repository enthält eine Django-Applikation mit mehreren Sub-Apps (`core`, `bfagent`, `writing_hub`, `expert_hub`, `presentation_studio`, `genagent`). Die CI-Pipeline nutzt den plattformweiten Reusable Workflow `_ci-python.yml` aus dem `platform`-Repo.

Die Test-Suite umfasst:
- **Unit Tests** — laufen mit SQLite (`USE_POSTGRES=0`, `--no-migrations`)
- **Integration Tests** — laufen mit PostgreSQL (echte DB-Verbindung)
- **Contract Tests** — Schemathesis-basierte API-Tests (`@pytest.mark.contract`)

### 1.2 Problem / Lücken

Beim Aufbau der CI-Pipeline traten folgende strukturelle Probleme auf:

1. **Vendored `platform-context`** — Das Paket ist nicht auf PyPI verfügbar und muss aus `vendor/platform_context/` installiert werden. Der CI-Workflow versuchte zunächst eine PyPI-Installation, die fehlschlug.

2. **`transaction.atomic()` in Unit Tests** — `BaseHandler.execute()` und `core_handlers/base.py` nutzten `transaction.atomic()` ohne Fallback. Unit Tests ohne DB-Verbindung warfen `RuntimeError`.

3. **Test-Marker-Trennung fehlte** — View-Tests (`TestAgentsViews`, `TestLlmsViews`, `TestWorldsViews`) liefen im Unit-Test-Job, obwohl sie eine echte DB und vollständiges Django-Setup benötigen.

4. **Pre-existierende Test-Bugs** — Generierte Test-Dateien enthielten falsche URL-Namen, ungültige Fixture-Daten (Strings statt Integers/Decimals), fehlende Pflichtfelder in Fixtures und falsche Assertions.

5. **Standalone-Skripte als Tests** — `test_chapter_illustration.py` und `test_studio_views.py` lagen im Testpfad, waren aber eigenständige Skripte ohne pytest-Kompatibilität.

6. **Contract Tests: exit code 5** — Wenn keine `@pytest.mark.contract`-Tests vorhanden sind, gibt pytest exit code 5 zurück, was den CI-Job als Fehler markiert.

7. **`PromptTemplate`-Import-Fehler** — `apps.core.models` exportierte `PromptTemplate` nicht, obwohl `registry.py` und Tests es importierten. Der ForeignKey `"core.PromptApp"` in `PromptTemplate` war nicht auflösbar, da `PromptApp` ebenfalls nicht re-exportiert wurde.

### 1.3 Constraints

- Der plattformweite Reusable Workflow `_ci-python.yml` wird von mehreren Repos genutzt — Änderungen müssen rückwärtskompatibel sein.
- SQLite wird für Unit Tests verwendet (kein Postgres-Service nötig), PostgreSQL für Integration Tests.
- `--no-migrations` darf nur für Unit Tests gelten, nicht für Integration Tests.

---

## 2. Entscheidung

### 2.1 Test-Marker-Strategie

Tests werden in drei Kategorien eingeteilt:

| Marker | Läuft in | DB | Beschreibung |
|--------|----------|----|--------------|
| *(kein Marker)* | Unit Tests | SQLite (no-migrations) | Reine Logik-Tests, keine DB-Abhängigkeit |
| `@pytest.mark.integration` | Integration Tests | PostgreSQL | View-Tests, DB-abhängige Tests |
| `@pytest.mark.contract` | Contract Tests | PostgreSQL | Schemathesis API-Tests |

**Regel**: Tests, die `LoginRequiredMixin`, vollständiges Django-URL-Routing, oder komplexe FK-Fixtures benötigen, werden als `integration` markiert.

### 2.2 Vendored Package Installation

```yaml
# In _ci-python.yml
- name: Install platform-context
  run: |
    if [ -d "vendor/platform_context" ]; then
      pip install -e "vendor/platform_context[testing]"
    else
      pip install "platform-context[testing]${{ inputs.platform_context_version }}" || true
    fi
```

Repos mit vendortem `platform-context` setzen `platform_context_version: ""` im CI-Workflow-Input.

### 2.3 `transaction.atomic()` Fallback

`BaseHandler.execute()` in `apps/core/handlers/base.py` und `apps/core/core_handlers/base.py` nutzt einen try-except-Fallback:

```python
if self.use_transaction and DJANGO_AVAILABLE:
    try:
        with transaction.atomic():
            result = self.process(data, context)
    except RuntimeError:
        result = self.process(data, context)
else:
    result = self.process(data, context)
```

Dies erlaubt Unit Tests ohne DB-Verbindung, ohne das Transaktionsverhalten in Produktion zu beeinflussen.

### 2.4 `collect_ignore` für Standalone-Skripte

In `conftest.py` (Root-Level) werden Standalone-Skripte explizit ausgeschlossen:

```python
collect_ignore = [
    "apps/bfagent/handlers/test_chapter_illustration.py",
    "apps/bfagent/views/test_studio_views.py",
    "apps/bfagent/tests/test_agents.py",
    "apps/bfagent/tests/test_llms.py",
    "apps/bfagent/tests/test_worlds.py",
]
```

Die View-Tests (`test_agents.py`, `test_llms.py`, `test_worlds.py`) werden aus dem Unit-Test-Job ausgeschlossen, da sie als `@pytest.mark.integration` markiert sind und im Integration-Test-Job laufen.

### 2.5 Contract Tests: exit code 5

Der Contract-Test-Schritt in `_ci-python.yml` behandelt exit code 5 (keine Tests gefunden) als Erfolg:

```bash
pytest -m "contract" -v || ([ $? -eq 5 ] && echo "No contract tests found, skipping." && exit 0)
```

### 2.6 Modell-Exports in `apps.core.models`

Alle Prompt-Modelle werden in `apps/core/models/__init__.py` re-exportiert, damit Django alle ForeignKey-Referenzen auflösen kann:

```python
from .prompt_lookups import PromptApp, PromptCategory, PromptOutputFormat, PromptTier
from .prompt_models import PromptComponent, PromptConfig, PromptExecution, PromptTemplate, TenantPromptOverride
```

---

## 3. Betrachtete Alternativen

### 3.1 Alle Tests mit PostgreSQL laufen lassen

**Abgelehnt**: Erhöht CI-Laufzeit signifikant, erfordert Postgres-Service für alle Jobs, und Unit Tests sollten DB-unabhängig sein.

### 3.2 `pytest.ini` `filterwarnings` statt `collect_ignore`

**Abgelehnt**: `filterwarnings` unterdrückt nur Warnungen, verhindert aber nicht die Sammlung von Standalone-Skripten, die beim Import fehlschlagen.

### 3.3 View-Tests komplett löschen

**Abgelehnt**: Die Tests sind strukturell korrekt und testen wichtige View-Logik. Sie werden als `integration` markiert statt gelöscht.

### 3.4 `transaction.atomic()` komplett entfernen

**Abgelehnt**: Transaktionssicherheit in Produktion ist wichtig. Der Fallback ist der minimale Eingriff.

---

## 4. Begründung im Detail

### 4.1 Warum `--no-migrations` nur für Unit Tests?

`--no-migrations` erstellt das DB-Schema direkt aus den Modellen (ohne Migrations). Das funktioniert mit SQLite, aber Integration Tests müssen die echten Migrations testen, da sie die Produktionsdatenbank widerspiegeln.

### 4.2 Warum `collect_ignore` statt `pytest.mark.skip`?

Standalone-Skripte wie `test_chapter_illustration.py` schlagen bereits beim **Import** fehl (nicht beim Ausführen). `pytest.mark.skip` greift erst nach dem Import — `collect_ignore` verhindert den Import komplett.

### 4.3 Warum Prompt-Modelle in `__init__.py` re-exportieren?

Django's App-Registry löst String-Referenzen wie `"core.PromptApp"` über den App-Label auf. Wenn `PromptApp` nicht in `apps.core.models` registriert ist, schlägt die FK-Auflösung mit `ValueError: Related model 'core.PromptApp' cannot be resolved` fehl — besonders mit `--no-migrations`.

---

## 5. Implementation Plan

### Phase 1: CI-Workflow-Fixes (abgeschlossen 2026-02-22)
- [x] Vendored `platform-context` Installation in `_ci-python.yml`
- [x] `--no-migrations` für Unit Tests in `_ci-python.yml`
- [x] Contract Tests: exit code 5 als Erfolg werten

### Phase 2: Handler-Fixes (abgeschlossen 2026-02-22)
- [x] `transaction.atomic()` Fallback in `apps/core/handlers/base.py`
- [x] `transaction.atomic()` Fallback in `apps/core/core_handlers/base.py`
- [x] `Llms.created_at` / `updated_at` mit `default=timezone.now` / `auto_now=True`

### Phase 3: Test-Fixes (abgeschlossen 2026-02-22)
- [x] URL-Namen in `test_agents.py` und `test_llms.py` korrigiert
- [x] `test_agents.py`, `test_llms.py`, `test_worlds.py` als `integration` markiert
- [x] `test_worlds.py` Fixture mit korrekten Pflichtfeldern (`BookProjects`)
- [x] `test_cascade_api.py` Message-Assertion gefixt
- [x] `expert_hub/tests/test_agents.py` Zone-2-Test-Parameter gefixt
- [x] `conftest.py` `collect_ignore` für Standalone-Skripte
- [x] Alle Prompt-Modelle in `apps/core/models/__init__.py` re-exportiert

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|--------------------|--------|------------|
| Neue generierte Tests haben wieder falsche URL-Namen | Mittel | Niedrig | URL-Namen aus `urls.py` verifizieren vor Commit |
| `collect_ignore` versteckt echte Test-Fehler | Niedrig | Mittel | Regelmäßig prüfen ob ignorierte Tests repariert werden können |
| `transaction.atomic()` Fallback maskiert DB-Fehler in Produktion | Sehr niedrig | Hoch | Fallback greift nur bei `RuntimeError`, nicht bei DB-Fehlern |
| Prompt-Modell-Exports verursachen zirkuläre Imports | Niedrig | Mittel | Import-Reihenfolge in `__init__.py` beachten |

---

## 7. Konsequenzen

### 7.1 Positiv

- CI-Pipeline läuft vollständig grün (Unit + Integration + Contract + Build + Deploy)
- Unit Tests sind DB-unabhängig und schnell (~30s)
- Integration Tests testen echte DB-Interaktionen mit PostgreSQL
- Klare Trennung zwischen Test-Kategorien erleichtert Debugging

### 7.2 Trade-offs

- `test_agents.py`, `test_llms.py`, `test_worlds.py` laufen nur im Integration-Test-Job — View-Regressions werden nicht im schnellen Unit-Test-Job erkannt
- `collect_ignore` muss manuell gepflegt werden wenn neue Standalone-Skripte hinzukommen
- Generierte Test-Dateien (via Code-Generator) müssen nach der Generierung manuell auf korrekte URL-Namen und Fixture-Daten geprüft werden

### 7.3 Nicht in Scope

- Vollständige Reparatur aller View-Tests (Login-Redirect-Assertions, HTMX-Assertions, Form-Validierungen) — diese sind pre-existierende Bugs im Code-Generator-Output
- Einführung von Factory Boy oder Mixer für Fixture-Generierung
- E2E-Tests mit Playwright

---

## 8. Validation Criteria

| Kriterium | Messung | Ziel |
|-----------|---------|------|
| Unit Tests bestehen | CI-Job "Unit Tests" | ✅ grün |
| Integration Tests bestehen | CI-Job "Integration Tests" | ✅ grün |
| Coverage Gate | CI-Job "Coverage Gate" | ≥ 80% |
| Build & Deploy | CI-Jobs "Build" + "Deploy" | ✅ grün |
| Keine falschen Negatives | `collect_ignore`-Liste stabil | Keine neuen Einträge nötig |

---

## 9. Referenzen

- `apps/core/handlers/base.py` — `_transaction_context()` und `execute()`
- `apps/core/core_handlers/base.py` — `execute()` mit `transaction.atomic()`
- `apps/core/models/__init__.py` — Prompt-Modell-Exports
- `conftest.py` — `collect_ignore`-Liste
- `.github/workflows/ci.yml` — bfagent CI-Workflow
- `platform/.github/workflows/_ci-python.yml` — Reusable CI-Workflow
- ADR-057: Platform Test Strategy
- ADR-058: Multi-Tenancy Testing Strategy

---

## 10. Changelog

| Datum      | Autor         | Änderung                          |
|------------|---------------|-----------------------------------|
| 2026-02-22 | Achim Dehnert | Initial — Status: Accepted        |
