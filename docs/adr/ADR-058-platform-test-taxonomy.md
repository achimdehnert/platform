---
status: "accepted"
date: 2026-02-20
amended: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-057-platform-test-strategy.md"]
---

# Adopt a 28-type test taxonomy as the binding standard for all platform repos

> **Input**: `docs/adr/inputs/testarten-matrix.md` (2026-02-20)
> **Basis**: ADR-057 (Platform Test Strategy — 4-Ebenen-Pyramide)
> **Amendment**: Review fixes applied 2026-02-20 — see §Review Amendments.

---

## Context and Problem Statement

ADR-057 legt die **Strategie** fest: vier Ebenen (Funktion, DB, API, UI/HTMX), Contract Testing mit Schemathesis, CI-Integration. Was bisher fehlt, ist die **taktische Taxonomie**: Welche konkreten Testarten existieren, was prüft jede, welches Tool wird eingesetzt, und wann ist welche Testart verpflichtend?

Ohne verbindlichen Katalog entstehen inkonsistente Testsuiten: Ein Repo hat nur Unit Tests, ein anderes nur View-Response-Tests, ein drittes gar keine Auth-Tests. Das führt zu blinden Flecken in genau den Bereichen, die in Produktion am häufigsten brechen.

**Problem**: Keine gemeinsame Sprache für Testarten, keine Verbindlichkeit, keine Prüfbarkeit in CI.

---

## Decision Drivers

- **Einheitlichkeit**: Alle Repos sprechen dieselbe Sprache wenn es um Tests geht
- **Vollständigkeit**: Keine strukturellen blinden Flecken (Auth, HTMX-Fragmente, Contract)
- **Prüfbarkeit**: Jede Testart hat ein klares Kriterium — vorhanden oder nicht
- **Pragmatismus**: Keine Testarten die externe Infrastruktur oder Browser-Automation erfordern
- **Skalierbarkeit**: Neue Repos übernehmen den Katalog ohne Diskussion

---

## Considered Options

1. **Kein Katalog** — jedes Repo entscheidet selbst welche Tests es schreibt
2. **Minimalkatalog** — nur Unit + DB + API Endpoint Tests verpflichtend
3. **Vollständiger Katalog (28 Testarten)** — alle vier Dimensionen mit konkreten Testarten, Pflicht/Optional-Klassifizierung, CI-Zuordnung
4. **Externe Teststandards** (z.B. ISO 29119) — formale Norm als Basis

---

## Decision Outcome

**Gewählt: Option 3 — Vollständiger Katalog mit 28 Testarten**, weil:

- Option 1 hat den Status quo produziert: inkonsistente, lückenhafte Testsuiten
- Option 2 deckt die kritischsten Lücken nicht ab (HTMX-Fragmente, Auth, Contract)
- Option 3 ist vollständig, prüfbar und ohne externe Infrastruktur umsetzbar
- Option 4 (ISO 29119) ist für ein 1-3 Personen Team unverhältnismäßig

### Confirmation

Compliance wird auf drei Wegen geprüft:

1. **CI-Gate**: `pytest --cov` läuft auf jedem Push via `_ci-python.yml@main` — Build schlägt fehl wenn Pflicht-Tests fehlen oder rot sind.
2. **grep-basierter Compliance-Check** (manuell oder als ADR-054-Guardian-Regel):

```bash
grep -r "401\|403\|unauthenticated" tests/ | wc -l   # A2 Auth Tests
grep -r "HX_REQUEST\|HX-Request" tests/ | wc -l       # U3 HTMX Fragment Tests
grep -r "status_code == 404" tests/ | wc -l            # A6 Error Handling Tests
```

3. **Migration-Tracking-Tabelle** (§ Migration Tracking): Zeigt pro Repo welche Pflicht-Testarten implementiert sind.

### Consequences

- Good, because alle Repos eine einheitliche Sprache für Testarten haben.
- Good, because Lücken sichtbar und messbar sind — kein "wir haben Tests" ohne Substanz.
- Good, because CI-Gates Regressions in den häufigsten Fehlerklassen verhindern.
- Good, because neue Repos den Katalog direkt übernehmen können ohne Diskussion.
- Bad, because initiale Implementierung Zeit kostet (Phase 2: ~2-3 Tage pro Repo).
- Bad, because HTMX Fragment Tests (U3) Kenntnis der `HTTP_HX_REQUEST` Header-Syntax erfordern.
- Bad, because Schemathesis (A7/A8) gepflegte OpenAPI Specs erfordert — Repos ohne `drf-spectacular` müssen nachziehen.
- Neutral: Kein Playwright/Selenium — Browser-Automation unverhältnismäßig; reserviert für ADR-060+.
- Neutral: Kein Pact Broker — Schemathesis deckt 80% ohne zusätzliche Infrastruktur.
- Neutral: Odoo-Tests bleiben statisch — Odoo hat eigenes Test-Framework für Integration Tests.

---

## Pros and Cons of the Options

### Option 1 — Kein Katalog

- Good, because kein Aufwand für Standardisierung.
- Good, because maximale Flexibilität pro Repo.
- Bad, because der Status quo produziert inkonsistente, lückenhafte Testsuiten.
- Bad, because keine gemeinsame Sprache — "wir haben Tests" bedeutet für jedes Repo etwas anderes.
- Bad, because blinde Flecken (Auth, HTMX, Contract) bleiben unsichtbar bis zur Produktion.

### Option 2 — Minimalkatalog (Unit + DB + API Endpoint)

- Good, because geringer initialer Aufwand.
- Good, because deckt die häufigsten intra-service Bugs ab.
- Bad, because HTMX-Fragment-Regressions nicht abgedeckt (U3 fehlt).
- Bad, because Auth-Lücken nicht systematisch erkannt (A2 optional).
- Bad, because Cross-Service-Contract-Brüche (A9, odoo-hub ↔ risk-hub) bleiben lautlos.

### Option 3 — Vollständiger Katalog mit 28 Testarten (gewählt)

- Good, because alle vier Dimensionen mit Pflicht/Empfohlen/Optional-Klassifizierung.
- Good, because CI-Zuordnung klar: was läuft auf push, was auf main, was post-deploy.
- Good, because Repo-Typ-spezifische Mindestsets (Django, Package, Odoo, MCP).
- Good, because Compliance grep-basiert prüfbar — kein zusätzliches Tooling nötig.
- Bad, because 28 Testarten initial überwältigend wirken können.
- Bad, because Phasen-Roadmap Disziplin erfordert — ohne Tracking-Tabelle verblasst der Plan.

### Option 4 — Externe Teststandards (ISO 29119)

- Good, because international anerkannte Norm.
- Good, because vollständige Dokumentation und Zertifizierungsmöglichkeit.
- Bad, because für ein 1-3 Personen Team unverhältnismäßig komplex.
- Bad, because nicht Django/HTMX-spezifisch — erheblicher Adaptionsaufwand.
- Bad, because Lizenzkosten für Norm-Dokumente.
- **Abgelehnt** — kein Mehrwert gegenüber Option 3 für dieses Team.

---

## Der Katalog: 28 Testarten in 4 Dimensionen

### Legende

| Symbol | Bedeutung |
|--------|-----------|
| 🔴 **Pflicht** | Muss in jedem Repo vorhanden sein das diese Dimension nutzt |
| 🟡 **Empfohlen** | Soll vorhanden sein, Ausnahmen dokumentieren |
| 🟢 **Optional** | Sinnvoll für komplexe Fälle, kein Pflicht-Gate |
| **CI: push** | Läuft auf jedem Push (Feature-Branch + main) |
| **CI: main** | Läuft nur auf main/develop |
| **CI: post-deploy** | Läuft nach Deployment gegen Live-System |

### Dimension 1: FUNKTION — Business Logic (5 Testarten)

| # | Testart | Was wird geprüft | Tool | Pflicht | CI |
|---|---------|-----------------|------|---------|-----|
| F1 | **Unit Test** | Eine Funktion/Methode, ein Ergebnis | pytest | 🔴 | push |
| F2 | **Parametrized Test** | Gleiche Funktion, viele Eingaben/Grenzwerte | `@pytest.mark.parametrize` | 🟡 | push |
| F3 | **Exception Test** | Fehlerbehandlung — korrekter Exception-Typ + Message | `pytest.raises` | 🔴 | push |
| F4 | **Pure Function Test** | Utility-Funktionen ohne Seiteneffekte | pytest | 🟡 | push |
| F5 | **Property-Based Test** | Invarianten bei zufälligen Eingaben | Hypothesis | 🟢 | push |

### Dimension 2: DB — Datenschicht (8 Testarten)

| # | Testart | Was wird geprüft | Tool | Pflicht | CI |
|---|---------|-----------------|------|---------|-----|
| D1 | **Model Constraint Test** | DB-Constraints halten (Unique, NOT NULL, Check) | pytest-django | 🔴 | push |
| D2 | **Validator Test** | Django Model/Form Validatoren | pytest-django | 🔴 | push |
| D3 | **Custom Manager Test** | QuerySet-Methoden (`.active()`, `.by_tenant()`) | pytest-django | 🔴 | push |
| D4 | **Annotation/Aggregation Test** | Komplexe Queries mit `annotate()`, `aggregate()` | pytest-django | 🟡 | push |
| D5 | **Migration Test** | Schema-Änderungen brechen nichts, Rückwärts-Migration | django-test-migrations | 🟡 | main |
| D6 | **DB View Schema Test** | Shared Views halten ihren Spalten-Vertrag | pytest + raw SQL | 🟡 | main |
| D7 | **Transaction Test** | Atomare Operationen (zusammen oder gar nicht) | TransactionTestCase | 🟢 | push |
| D8 | **Factory Consistency Test** | Factory Boy erzeugt valide, konsistente Objekte | factory-boy | 🟡 | push |

### Dimension 3: API — Schnittstellen (11 Testarten)

| # | Testart | Was wird geprüft | Tool | Pflicht | CI |
|---|---------|-----------------|------|---------|-----|
| A1 | **Endpoint Test** | Status Code + Response-Struktur | Django Test Client | 🔴 | push |
| A2 | **Auth Test** | Unauthentifiziert → 401/403, kein Datenleck | Django Test Client | 🔴 | push |
| A3 | **CRUD Test** | POST erstellt, PUT ändert, DELETE entfernt | Django Test Client | 🔴 | push |
| A4 | **Pagination Test** | `next`/`previous` Links, korrekte Seitengröße | Django Test Client | 🟡 | push |
| A5 | **Filter/Search Test** | Query-Parameter filtern korrekt | Django Test Client | 🟡 | push |
| A6 | **Error Handling Test** | 4xx/5xx liefern JSON-Body, keinen Traceback | Django Test Client | 🔴 | push |
| A7 | **Schema Validation Test** | Response passt zum OpenAPI Schema | Schemathesis | 🟡 | main |
| A8 | **Provider Contract Test** | Unsere API liefert was Consumer erwarten | Schemathesis | 🟡 | main |
| A9 | **Consumer Contract Test** | Unser Client versteht die API des anderen Service | responses + jsonschema | 🟡 | main |
| A10 | **Celery Payload Contract** | Task-Payloads stimmen zwischen Sender/Empfänger überein | jsonschema | 🟢 | main |
| A11 | **Rate Limiting Test** | Throttling greift ab definiertem Limit | Django Test Client | 🟢 | push |

### Dimension 4: UI/HTMX — Frontend (9 Testarten)

U9 Smoke Tests prüfen `/livez/` (Liveness) + `/healthz/` (Readiness) gemäß ADR-021 §2.8.

| # | Testart | Was wird geprüft | Tool | Pflicht | CI |
|---|---------|-----------------|------|---------|-----|
| U1 | **View Response Test** | Richtiger Status Code + Template verwendet | Django Test Client | 🔴 | push |
| U2 | **Template Content Test** | Richtiger Inhalt gerendert (Titel, Username, Daten) | BeautifulSoup | 🟡 | push |
| U3 | **HTMX Fragment Test** | `HX-Request: true` → nur Fragment, kein `<html>` | BeautifulSoup | 🔴 | push |
| U4 | **HTMX Attribute Test** | Korrekte `hx-*` Attribute auf Buttons/Forms | BeautifulSoup | 🟡 | push |
| U5 | **Form Rendering Test** | Alle Felder da, CSRF Token, Validierungsfehler | BeautifulSoup | 🔴 | push |
| U6 | **Navigation Test** | Login-Redirect, Breadcrumbs, `next`-Parameter | Django Test Client | 🟡 | push |
| U7 | **Permission UI Test** | Admin sieht Delete-Button, normaler User nicht | BeautifulSoup | 🟡 | push |
| U8 | **Error Page Test** | 404/500 Custom-Template wird gerendert | Django Test Client | 🟡 | push |
| U9 | **Smoke Test** | `/livez/` + `/healthz/` erreichbar nach Deployment | requests / curl | 🔴 | post-deploy |

---

## Pflicht-Mindestset pro Repo-Typ

### Django-Repos

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F3 | ≥ 5 |
| DB | D1, D2, D3 | ≥ 5 |
| API | A1, A2, A3, A6 | ≥ 8 (wenn DRF vorhanden) |
| UI/HTMX | U1, U3, U5, U9 | ≥ 5 (wenn HTMX vorhanden) |

### Python-Package-Repos

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F2, F3 | ≥ 10 |

### Odoo-Addon-Repos

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | Manifest-Validierung, Struktur-Tests | ≥ 10 (statisch) |
| Contract | A9 (Consumer Contract gegen risk-hub API) | ≥ 3 |

### MCP-Repos

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F3 | ≥ 5 pro MCP-Modul |
| API | A1 | ≥ 3 pro MCP-Modul |

---

## CI-Zuordnung

```text
 Push auf Feature-Branch          Push auf main/develop         Nach Deployment
 ─────────────────────           ────────────────────          ──────────────
 ┌──────────────────────┐         ┌──────────────────────┐      ┌────────────┐
 │ ✅ F1, F2, F3, F4    │         │ ✅ F1–F5              │      │ ✅ U9      │
 │ ✅ D1, D2, D3, D8    │         │ ✅ D1–D8              │      │   /livez/  │
 │ ✅ A1, A2, A3, A6    │         │ ✅ A1–A11             │      │   /healthz/│
 │ ✅ U1, U3, U5        │         │ ✅ U1–U8              │      └────────────┘
 │ ❌ Contract Tests    │         │ ✅ A7, A8, A9 (Contr.)│
 │ ❌ Migration Tests   │         │ ✅ D5, D6 (Migration) │
 └──────────────────────┘         └──────────────────────┘
    Ziel: < 3 Min                    Ziel: < 5 Min              Ziel: < 30 Sek
```

Alle Tests laufen via `_ci-python.yml@main` (ADR-021 §2.5). Contract + Migration Tests nur auf `main` — konsistent mit ADR-057 §2.10.

---

## Tooling-Stack (verbindlich)

| Tool | Version | Zweck |
|------|---------|-------|
| `pytest` | ≥ 8.0 | Test-Runner |
| `pytest-django` | ≥ 4.8 | Django-Integration, `@pytest.mark.django_db` |
| `pytest-cov` | ≥ 5.0 | Coverage-Messung |
| `factory-boy` | ≥ 3.3 | Test-Daten (D8) |
| `beautifulsoup4` | ≥ 4.12 | HTML-Parsing für UI-Tests (U2–U8) |
| `schemathesis` | ≥ 3.30 | OpenAPI Contract Tests (A7, A8) |
| `responses` | ≥ 0.25 | HTTP-Mocking für Consumer Contract Tests (A9) |
| `jsonschema` | ≥ 4.0 | Payload-Validierung (A10) |
| `hypothesis` | ≥ 6.0 | Property-Based Tests (F5) — optional |

---

## Migration Tracking

> **Stand**: 2026-02-20 — Phase 1 abgeschlossen für alle 12 aktiven Repos.

### Pflicht-Testarten: Ist-Stand pro Repo

| Repo | F1 | F3 | D1 | D3 | A1 | A2 | A6 | U1 | U3 | U5 | U9 |
|------|----|----|----|----|----|----|----|----|----|----|-----|
| weltenhub | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | — | — | — |
| travel-beat | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | — | — | — |
| bfagent | ✅ | ✅ | ✅ | — | ✅ | — | — | ✅ | — | — | — |
| risk-hub | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | — | — | — |
| cad-hub | ✅ | — | — | — | — | — | — | ✅ | — | — | — |
| wedding-hub | ✅ | ✅ | — | — | — | — | — | ✅ | — | ✅ | — |
| trading-hub | ✅ | ✅ | — | — | — | — | — | — | — | — | — |
| dev-hub | ✅ | — | — | — | — | — | — | ✅ | — | — | ✅ |
| pptx-hub | ✅ | ✅ | — | — | — | — | — | — | — | — | — |
| mcp-hub | ✅ | ✅ | — | — | ✅ | — | — | — | — | — | — |
| odoo-hub | ✅ | ✅ | — | — | — | — | — | — | — | — | — |
| platform | ✅ | ✅ | — | — | — | — | — | — | — | — | — |

**Legende**: ✅ vorhanden | — fehlt (Lücke, Phase 2+)

### Phase-Roadmap

| Phase | Inhalt | Zeitraum | Status |
|-------|--------|----------|--------|
| Phase 1 | F1, F3, U1 in allen Repos; CI via `_ci-python.yml@main` | 2026-02 | ✅ Abgeschlossen |
| Phase 2 | A2, A6 für alle API-Repos; U3 für HTMX-Repos; A9 odoo↔risk | 2026-03 | 🔴 Offen |
| Phase 3 | D5 Migration Tests; A7/A8 Schemathesis; U4 HTMX Attribute | 2026-04 | 🔴 Offen |
| Phase 4 | F5 Hypothesis; A10 Celery Contracts; D6 DB View Schema | 2026-05+ | 🔴 Offen |

---

## Offene Fragen

1. **Enforcement-Mechanismus**: Pflicht-Tests sind definiert — aber wer prüft Compliance automatisch? Aktuell nur manuell via grep. ADR-054 Architecture Guardian soll in Phase 2 erweitert werden. → Deferred: **ADR-059** (Guardian-Erweiterung für Taxonomie-Compliance).

2. **Ratio-Konsistenz mit ADR-057**: ADR-057 §2.4 definiert Test-Pyramiden-Ratio 40/45/10/5. ADR-058 definiert Testarten ohne explizite Ratio-Gewichtung. Beide sind kompatibel — Ratio gilt für Test-Anzahl, Taxonomie für Test-Typen. Bei nächstem ADR-057-Amendment zu dokumentieren.

3. **Phase-4-Deferred**: F5 (Hypothesis), A10 (Celery Payload Contracts), D6 (DB View Schema Tests) sind als "Langfristig" markiert. → Deferred: **ADR-060** (Property-Based + Celery Contract Testing) — zu erstellen wenn Phase 3 abgeschlossen oder Team > 3 Personen.

---

## Review Amendments (2026-02-20)

Angewendet nach kritischem Review gegen `docs/templates/adr-review-checklist.md`:

| # | Finding | Fix |
|---|---------|-----|
| R1 | Titel war Thema, keine Entscheidungsaussage | Titel zu "Adopt a 28-type test taxonomy..." geändert |
| R2 | `## Pros and Cons of the Options` fehlte komplett | Abschnitt für alle 4 Optionen mit Good/Bad-Bullets ergänzt |
| R3 | `### Confirmation` fehlte unter `## Decision Outcome` | CI-Gate, grep-Checks, Tracking-Tabelle als Confirmation-Mechanismen dokumentiert |
| R4 | `## More Information` fehlte als eigener Abschnitt | Eigener Abschnitt mit strukturierten Links ergänzt |
| R5 | Migration-Tracking-Tabelle fehlte | Ist-Stand-Tabelle pro Repo + Phase-Roadmap ergänzt |
| R6 | Deferred Decisions ohne ADR-Platzhalter | ADR-059 (Guardian) + ADR-060 (Phase 4) als Platzhalter benannt |

---

## More Information

- **ADR-057**: Platform Test Strategy — 4-Ebenen-Pyramide, CI-Integration, Schemathesis-Entscheidung, Test-Ratio 40/45/10/5
- **ADR-054**: Architecture Guardian — wird in Phase 2 um Taxonomie-Compliance-Checks erweitert (→ ADR-059)
- **ADR-048**: HTMX Playbook — Kontext für U3/U4 HTMX Fragment + Attribute Tests
- **ADR-022**: Code Quality Tooling — ruff, pytest als Standard-Tools
- **ADR-021**: Unified Deployment Pattern — `/livez/` + `/healthz/` Health-Endpoints (U9)
- **Input**: `docs/adr/inputs/testarten-matrix.md` — vollständige Codebeispiele für alle 28 Testarten
- **Deferred**: ADR-059 — Architecture Guardian Erweiterung für automatische Taxonomie-Compliance
- **Deferred**: ADR-060 — Property-Based Tests (Hypothesis) + Celery Payload Contract Testing
