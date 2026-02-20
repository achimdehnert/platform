---
status: "accepted"
date: 2026-02-20
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related: ["ADR-057-platform-test-strategy.md"]
---

# ADR-058: Platform Test Taxonomy — 28 verbindliche Testarten für alle Repos

> **Input**: `docs/adr/inputs/testarten-matrix.md` (2026-02-20)
> **Basis**: ADR-057 (Platform Test Strategy — 4-Ebenen-Pyramide)

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

---

### Dimension 1: FUNKTION — Business Logic (5 Testarten)

Testen reine Logik ohne DB, HTTP oder UI. Schnellste Tests, höchster Anteil.

| # | Testart | Was wird geprüft | Tool | Pflicht | CI |
|---|---------|-----------------|------|---------|-----|
| F1 | **Unit Test** | Eine Funktion/Methode, ein Ergebnis | pytest | 🔴 | push |
| F2 | **Parametrized Test** | Gleiche Funktion, viele Eingaben/Grenzwerte | `@pytest.mark.parametrize` | 🟡 | push |
| F3 | **Exception Test** | Fehlerbehandlung — korrekter Exception-Typ + Message | `pytest.raises` | 🔴 | push |
| F4 | **Pure Function Test** | Utility-Funktionen ohne Seiteneffekte | pytest | 🟡 | push |
| F5 | **Property-Based Test** | Invarianten bei zufälligen Eingaben | Hypothesis | 🟢 | push |

**Beispiel F1 + F2 + F3:**

```python
# F1 — Unit Test
def test_should_calculate_risk_score_within_range():
    result = calculate_explosion_risk(zone_type="1", volume_m3=50)
    assert 0 <= result <= 100

# F2 — Parametrized Test
@pytest.mark.parametrize("zone_type,volume,expected_min", [
    ("0",  10,  80),
    ("1",  50,  40),
    ("2", 100,  10),
])
def test_should_return_correct_risk_by_zone(zone_type, volume, expected_min):
    assert calculate_explosion_risk(zone_type=zone_type, volume_m3=volume) >= expected_min

# F3 — Exception Test
def test_should_raise_on_negative_volume():
    with pytest.raises(ValueError, match="Volumen muss positiv sein"):
        calculate_explosion_risk(zone_type="1", volume_m3=-5)
```

---

### Dimension 2: DB — Datenschicht (8 Testarten)

Testen Models, Queries, Constraints, Schema-Verträge.

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

**Beispiel D1 + D3:**

```python
# D1 — Model Constraint Test
@pytest.mark.django_db
def test_should_reject_blank_title():
    with pytest.raises(IntegrityError):
        AssessmentFactory(title="")

# D3 — Custom Manager Test
@pytest.mark.django_db
def test_should_active_manager_exclude_archived():
    AssessmentFactory(status="active")
    AssessmentFactory(status="archived")
    result = Assessment.objects.active()
    assert result.count() == 1
    assert result.first().status == "active"
```

---

### Dimension 3: API — Schnittstellen (11 Testarten)

Testen REST/JSON Endpoints, Auth, Service-zu-Service-Verträge.

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

**Beispiel A1 + A2 + A6:**

```python
# A1 — Endpoint Test
@pytest.mark.django_db
def test_should_list_assessments_returns_200(authenticated_client):
    AssessmentFactory.create_batch(3)
    response = authenticated_client.get("/api/v1/assessments/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 3

# A2 — Auth Test
@pytest.mark.django_db
def test_should_reject_unauthenticated_request(client):
    response = client.get("/api/v1/assessments/")
    assert response.status_code in (401, 403)

# A6 — Error Handling Test
@pytest.mark.django_db
def test_should_return_404_not_500_for_unknown_id(authenticated_client):
    response = authenticated_client.get("/api/v1/assessments/99999/")
    assert response.status_code == 404
    assert "detail" in response.json()  # Saubere Fehlermeldung, kein Traceback
```

---

### Dimension 4: UI/HTMX — Frontend (9 Testarten)

Testen was der User sieht — ohne Browser (BeautifulSoup), außer Smoke Tests.

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
| U9 | **Smoke Test** | Live-System erreichbar nach Deployment | requests / curl | 🔴 | post-deploy |

**Beispiel U3 + U4 (HTMX — kritischste Lücke aktuell):**

```python
# U3 — HTMX Fragment Test
@pytest.mark.django_db
def test_should_return_partial_on_htmx_request(authenticated_client):
    response = authenticated_client.get(
        "/assessments/",
        HTTP_HX_REQUEST="true",
        HTTP_HX_TARGET="assessment-list",
    )
    content = response.content.decode()
    assert "<html" not in content          # Kein Full-Page-Response
    assert "assessment-list" in content    # Fragment vorhanden

# U4 — HTMX Attribute Test
@pytest.mark.django_db
def test_should_delete_button_have_htmx_confirm(authenticated_client):
    assessment = AssessmentFactory()
    response = authenticated_client.get(f"/assessments/{assessment.pk}/")
    soup = BeautifulSoup(response.content, "html.parser")
    btn = soup.find("button", {"id": "delete-assessment"})
    assert btn is not None
    assert btn.get("hx-delete")
    assert btn.get("hx-confirm")
```

---

## Pflicht-Mindestset pro Repo-Typ

Jedes Repo muss mindestens die 🔴-Testarten seiner genutzten Dimensionen abdecken.

### Django-Repos (weltenhub, travel-beat, bfagent, risk-hub, cad-hub, wedding-hub, trading-hub, dev-hub, pptx-hub)

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F3 | ≥ 5 |
| DB | D1, D2, D3 | ≥ 5 |
| API | A1, A2, A3, A6 | ≥ 8 (wenn DRF vorhanden) |
| UI/HTMX | U1, U3, U5, U9 | ≥ 5 (wenn HTMX vorhanden) |

### Python-Package-Repos (platform-context, pptx-hub als Library)

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F2, F3 | ≥ 10 |
| DB | — (kein eigenes DB-Schema) | — |
| API | — (Library, kein HTTP) | — |
| UI | — | — |

### Odoo-Addon-Repos (odoo-hub)

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | Manifest-Validierung, Struktur-Tests | ≥ 10 (statisch, kein Odoo-Runtime) |
| Contract | A9 (Consumer Contract gegen risk-hub API) | ≥ 3 |

### MCP-Repos (mcp-hub)

| Dimension | Pflicht-Testarten | Mindest-Anzahl Tests |
|-----------|------------------|---------------------|
| Funktion | F1, F3 | ≥ 5 pro MCP-Modul |
| API | A1 (Tool-Endpoint Tests) | ≥ 3 pro MCP-Modul |

---

## CI-Zuordnung

```text
 Push auf Feature-Branch          Push auf main/develop         Nach Deployment
 ─────────────────────           ────────────────────          ──────────────
 ┌──────────────────────┐         ┌──────────────────────┐      ┌────────────┐
 │ ✅ F1, F2, F3, F4    │         │ ✅ F1–F5              │      │ ✅ U9      │
 │ ✅ D1, D2, D3, D8    │         │ ✅ D1–D8              │      │   Smoke    │
 │ ✅ A1, A2, A3, A6    │         │ ✅ A1–A11             │      │   Tests    │
 │ ✅ U1, U3, U5        │         │ ✅ U1–U8              │      └────────────┘
 │ ❌ Contract Tests    │         │ ✅ A7, A8, A9 (Contr.)│
 │ ❌ Migration Tests   │         │ ✅ D5, D6 (Migration) │
 └──────────────────────┘         └──────────────────────┘
    Ziel: < 3 Min                    Ziel: < 5 Min              Ziel: < 30 Sek
```

---

## Priorisierte Implementierungs-Reihenfolge

Basierend auf Risiko × Aufwand:

### Phase 1 — Sofort (bereits in ADR-057 Phase 1+2 begonnen)

- F1, F3, D1, D3, A1, A2, U1 in allen Repos ✅ (teilweise vorhanden)

### Phase 2 — Nächste 4 Wochen (höchster Mehrwert)

- **A2 Auth Tests** für alle API-Repos — schützt vor Permission-Regressions
- **A6 Error Handling Tests** — überall fehlend, 2-3 Zeilen pro Endpoint
- **U3 HTMX Fragment Tests** — kritischster blinder Fleck in weltenhub + bfagent
- **A9 Consumer Contract** odoo-hub ↔ risk-hub — bricht aktuell lautlos

### Phase 3 — Mittelfristig (4-8 Wochen)

- D5 Migration Tests für risk-hub + weltenhub
- A7/A8 Schemathesis für risk-hub + weltenhub (haben drf-spectacular)
- U4 HTMX Attribute Tests

### Phase 4 — Langfristig

- F5 Property-Based Tests (Hypothesis) für Berechnungslogik
- A10 Celery Payload Contracts
- D6 DB View Schema Tests

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

## Konsequenzen

### Positiv

- Einheitliche Sprache: "Wir brauchen einen A2 Auth Test" ist für alle klar
- Lücken sind sichtbar und messbar — kein "wir haben Tests" ohne Substanz
- CI-Gates verhindern Regressions in den häufigsten Fehlerklassen
- Neue Repos können den Katalog direkt übernehmen ohne Diskussion

### Negativ / Risiken

- Initiale Implementierung kostet Zeit (Phase 2: ~2-3 Tage pro Repo)
- HTMX Fragment Tests (U3) erfordern Kenntnis der `HTTP_HX_REQUEST` Header-Syntax
- Schemathesis (A7/A8) erfordert gepflegte OpenAPI Specs — Repos ohne drf-spectacular müssen nachziehen

### Neutrale Entscheidungen

- Kein Playwright/Selenium — Browser-Automation ist für dieses Team unverhältnismäßig
- Kein Pact Broker — Schemathesis deckt 80% der Contract-Testing-Anforderungen
- Odoo-Tests bleiben statisch (kein Odoo-Runtime in CI) — Odoo hat eigenes Test-Framework für Integration Tests

---

## Compliance-Check

Jedes Repo kann gegen diesen Katalog geprüft werden:

```bash
# Prüfe ob Auth Tests vorhanden
grep -r "401\|403\|unauthenticated\|force_login" tests/ | wc -l

# Prüfe ob HTMX Fragment Tests vorhanden
grep -r "HX_REQUEST\|HX-Request" tests/ | wc -l

# Prüfe ob Error Handling Tests vorhanden
grep -r "status_code == 404\|status_code == 500" tests/ | wc -l
```

---

## Referenzen

- **ADR-057**: Platform Test Strategy — 4-Ebenen-Pyramide, CI-Integration, Schemathesis-Entscheidung
- **Input**: `docs/adr/inputs/testarten-matrix.md` — vollständige Codebeispiele für alle 28 Testarten
- **ADR-022**: Code Quality Tooling — ruff, pytest als Standard-Tools
- **ADR-048**: HTMX Playbook — Kontext für U3/U4 HTMX Fragment Tests
