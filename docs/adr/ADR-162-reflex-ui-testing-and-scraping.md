---
id: ADR-162
title: "Adopt REFLEX as Standard Methodology for Evidence-based UI Development"
status: accepted
date: 2026-04-15
author: Achim Dehnert
scope: platform
tags: [methodology, ui-tdd, playwright, use-case, quality, scraping, testing]
staleness_months: 12
related_adrs: [ADR-040, ADR-041, ADR-050, ADR-051, ADR-058, ADR-059]
---

# ADR-162: Adopt REFLEX as Standard Methodology for Evidence-based UI Development

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 12
  - drift_check_paths:
      - dev-hub/apps/ui_tdd/
      - dev-hub/tests/ui/
      - dev-hub/use-cases/
      - dev-hub/scripts/run_reflex_loop.sh
      - platform/packages/platform-governance/
  - supersedes_check: false
-->

## Context

Die Platform besteht aus 11 Repositories mit Django 5.x, HTMX und
Tailwind CSS. Neue Features entstehen bislang direkt aus Annahmen —
Use Cases sind implizit, Wireframes fehlen, Tests entstehen nachträglich.
Das führt zu späten Fehlern in Review oder UAT, zu Use Cases die das
Falsche beschreiben, und zu UI-Komponenten die ohne Accessibility-
Grundlage gebaut werden.

Drei konkrete Probleme motivieren diese Entscheidung:

**Problem 1 — Domänenfehler.** Für neue Hubs (risk-hub, cad-hub, tax-hub)
existiert das Fachwissen nicht im Team. Use Cases werden ohne Domain
Expert formuliert und Fehler pflanzen sich bis in die Implementierung fort.

**Problem 2 — UI-Qualität nicht messbar.** Es gibt keine systematische
Prüfung auf Keyboard-Navigation, ARIA-Semantik, HTMX-Korrektheit
oder Permission-basiertes Rendering.

**Problem 3 — Authentifiziertes Scraping ungelöst.** Mehrere Hubs
benötigen Daten aus login-geschützten Systemen (Odoo, Broker-Portale,
Compliance-DBs). Ein Platform-Standard fehlt.

## Decision Drivers

- Use Cases entstehen evidenzbasiert, nicht aus Annahmen
- Jede UI-Komponente wird vor der Implementierung durch Tests validiert
- Domain-Expertise wird versioniert und wiederverwendbar ongeboardet
- Playwright gilt als einheitliches Tool für Testing und Scraping
- Die Methodik ist selbstreferenziell: v0.1 spezifiziert v1.0 durch
  seinen eigenen ersten Run
- Alle Artefakte folgen Platform-Standards (ADR-050): TenantAwareModel,
  Service-Layer, Audit-Trail, i18n, soft-delete

## Decision

**Wir führen REFLEX (Reflexive Evidence-based Loop) als
Standard-Entwicklungsmethodik für UI-Features ein.**

REFLEX definiert drei aufeinanderfolgende Qualitätszirkel. Kein Artefakt
entsteht bevor der vorherige Zirkel grüne Evidenz geliefert hat.

### Zirkel 0 — Expertise-Onboarding

**Bekannte Domäne** (dev-hub, risk-hub mit bestehenden ADRs):
Cascade prüft UC gegen ADRs und `domain/[hub]-kb.md`. Gate: kein
Widerspruch zu bestehenden ADRs, alle Begriffe in KB definiert.

**Neue Domäne** (cad-hub, tax-hub, ...):
Cascade generiert strukturierten Fragenkatalog. Domain Expert antwortet.
Cascade destilliert → `domain/[hub]-kb.md` (Glossar, Pflichtfelder,
Invarianten, Scope-Grenzen). Expert sign-off mit Datum. Gate: KB
vorhanden, Expert-Signatur im Header.

### Zirkel 1 — Inhaltliche UC-Qualität

Cascade prüft UC gegen Quality Checklist (Akteur spezifisch, Ziel
formuliert, max. 7 Schritte, Fehlerfälle, min. 2 testbare Kriterien,
keine Implementierungsdetails, keine weiche Sprache). Wiederholt bis
100% und in zwei aufeinanderfolgenden Runs stabil.

### Zirkel 2 — Technische UI-Qualität

Cascade erstellt Django Template als Wireframe (mit HTMX-Handler, ohne
Model-Aufruf). Cascade generiert pytest-playwright Tests (ein Test pro
Akzeptanzkriterium). Tests laufen via `subprocess.run()` — kein
`asyncio.run()` im ASGI-Kontext. Failures werden per Entscheidungsbaum
klassifiziert: UI-Problem → Wireframe korrigieren; UC-Problem → Zirkel 1
neu. Ergebnisse landen in `TestRun`-Model mit `emit_audit_event()`.

Gate: alle Tests grün, ARIA-Snapshot in zwei Runs identisch, mindestens
ein UC_PROBLEM dokumentiert (Beweis der Selbstverbesserung).

### REFLEX für existierende UI — Audit-Lauf

Für laufende Hubs entfallen Zirkel 0 und 1. Playwright-Audit-Tests
laufen direkt gegen die echte App. Cascade analysiert ARIA-Snapshots
und liefert priorisierte Optimierungsliste mit Template-Zeile und
Aufwandsschätzung.

### Authentifiziertes Scraping

Playwright gilt als Platform-Standard für Content-Extraktion aus
login-geschützten Systemen. Der Session-State-Mechanismus (einmaliger
Login, Speicherung als `.auth/*.json`) ist verbindlich. Credentials
ausschließlich in `tests/ui/.env.test` (gitignored, mit
`.env.test.example` als committed Vorlage). Pre-commit-Hook via
`detect-secrets` erzwingt `.gitignore`-Compliance. Playwright-Runs
aus Celery-Tasks erfolgen via `subprocess.run()` — niemals `asyncio.run()`.

### Platform-Standard-Compliance

Alle REFLEX-Artefakte (`UseCase`, `WireframeIteration`, `TestRun`,
`DomainKB`, `TestFailure`) implementieren vollständig:

- `TenantAwareModel` als Basis (UUIDField `tenant_id`)
- `public_id = UUIDField(default=uuid4, unique=True, editable=False)`
- `deleted_at = DateTimeField(null=True, blank=True, db_index=True)`
- `UniqueConstraint` mit `condition=Q(deleted_at__isnull=True)`
- `BigAutoField` PK via `DEFAULT_AUTO_FIELD`
- `gettext_lazy` auf allen `verbose_name` / `help_text`
- `emit_audit_event()` bei jedem State-Change
- Business-Logik ausschließlich in `services.py`

### `/dev-login/` Pattern (alle Hubs)

```python
# apps/core/views_dev_login.py
class DevLoginView(View):
    def get(self, request):
        token = request.GET.get("token")
        data = signing.loads(token, max_age=300)  # 5 min TTL
        user = User.objects.get(pk=data["uid"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect(data.get("next", "/"))
```

Generierung via Management Command:

```bash
python manage.py dev_login_url --next /projekte/
# → /dev-login/?token=<signed>
```

### Sicherheit

- Token ist SECRET_KEY-signiert, nicht erratbar
- TTL 5 Minuten — abgelaufene Tokens werden abgelehnt
- Kein Passwort wird gespeichert oder übertragen
- `.auth/`, `.env.test`, `.env.scraper` in `.gitignore`
- Pre-commit: `detect-secrets` Hook verhindert Token-Commit
- Session-Dateien (`.auth/`) erfordern disziplinierte `.gitignore`-Pflege

## Consequences

### Positiv

- Domänenfehler werden in Zirkel 0 gefunden — nicht in Produktion
- UC-Fehler in Zirkel 1 — vor dem ersten Wireframe-Pixel
- UI-Fehler in Zirkel 2 — vor dem ersten Service-Call
- ARIA-Vollständigkeit, Keyboard-Navigation, HTMX-Korrektheit testbar erzwungen
- Permission-Rendering durch Multi-Rollen-Fixtures prüfbar
- Scraping-Standard verhindert N Insellösungen in N Hubs
- REFLEX verbessert sich durch seinen ersten Run — kein externes Feedback nötig

### Negativ

- Zirkel 0 erfordert Domain-Expert-Zugang — nicht immer kurzfristig verfügbar
- v0.1 ist manuell — initial langsamer als direktes Implementieren
- Playwright-Browser-Binary muss in Docker-Workern installiert sein
  (`Dockerfile.worker` mit `playwright install chromium --with-deps`)
- Session-Dateien (`.auth/`) erfordern disziplinierte `.gitignore`-Pflege

### Neutral

- Bestehende Unit- und Integrations-Tests werden nicht ersetzt
- CI-Integration folgt in v1.0 (nicht Bestandteil von v0.1)
- Multi-Tenant-Isolation in Tests via `X-Tenant-ID` Header bereits
  in v0.1 korrekt implementiert

## Alternatives Considered

| Alternative | Pro | Contra | Entscheidung |
|---|---|---|---|
| Selenium | Bekannt | Kein ARIA-Snapshot, kein Session-State, langsamer | Abgelehnt |
| Cypress | Gute DX | JavaScript-only, kein Python-Ökosystem, kein MCP | Abgelehnt |
| Tests nachträglich | Schneller initial | Fehler spät, kein UC-Evidence, kein Gate | Abgelehnt |
| Nur Zirkel 2 | Einfacher | Domänenfehler vor Wireframe nicht aufgedeckt | Abgelehnt |
| Scrapy / BeautifulSoup | Schnell für statische Seiten | Kein JS-Rendering, kein Session-State, zweites Tool | Abgelehnt |
| Wireframe als statisches HTML | Einfacher | Kein HTMX-Verhalten testbar, kein Auth-Fixture | Abgelehnt |
| asyncio für Playwright-Tasks | Native async | asyncio.run() im ASGI-Kontext verboten (ADR-050) | Abgelehnt |

## Implementation

### Phase 1 — REFLEX v0.1 (manuell, 5 Tage)

**Tag 1 — Setup:**
- [ ] `pip install pytest-playwright pytest-json-report python-dotenv`
- [ ] `playwright install chromium`
- [ ] `tests/ui/.env.test` anlegen (nach `.env.test.example`)
- [ ] `.gitignore`: `tests/ui/.auth/`, `tests/ui/.env.test`, `.auth/`
- [ ] Pre-commit: `detect-secrets` Hook aktivieren
- [ ] `scripts/run_reflex_loop.sh` deployen (enthält `set -euo pipefail`)

**Tag 2 — Zirkel 0 + 1:**
- [ ] `domain/dev-hub-kb.md` aus ADR-051 destillieren
- [ ] `use-cases/concept-inline-create.md` (UC v0.1) schreiben
- [ ] Zirkel 0: UC gegen KB und ADR-051 prüfen
- [ ] Zirkel 1: Quality-Check via `python manage.py shell` und `services.check_uc_quality()`
- [ ] UC bis Checklist 100% iterieren

**Tag 3–4 — Zirkel 2:**
- [ ] `wireframes/concept_inline_create.html` (Django Template + HTMX-Handler)
- [ ] `apps/adr_lifecycle/views.py`: Wireframe-View + Submit-View ergänzen
      (Business-Logik in services.py, nicht in View)
- [ ] `tests/ui/test_concept_inline_create.py` generieren
- [ ] Loop: pytest → feedback.json → Cascade korrigiert → pytest → ...
- [ ] Bis Gate grün

**Tag 5 — Abschluss:**
- [ ] Implementierung: Stub-View durch echte ConceptInlineCreateView ersetzen
- [ ] `docs/reflex-v01-learnings.md` schreiben
- [ ] Concept in dev-hub → READY_FOR_ADR setzen

### Phase 2 — REFLEX v1.0 (automatisiert, nach v0.1-Abschluss)

- [ ] `apps/ui_tdd/` in dev-hub anlegen
- [ ] Models: `UseCase`, `WireframeIteration`, `TestRun`, `DomainKB`, `TestFailure`
      (alle platform-compliant: public_id, deleted_at, UniqueConstraint, i18n)
- [ ] Migration: `0001_initial.py` (idempotent, dependency auf core)
- [ ] Services: vollständig in `services.py` (kein Business-Code in Views/Tasks)
- [ ] Celery-Task: `run_playwright_tests_task` (Queue: `reflex`,
      via `subprocess.run()` — kein `asyncio.run()`)
- [ ] Management-Command: `run_reflex_loop`
- [ ] Views: Loop-Dashboard, Iteration-Detail, Transition-Views
- [ ] Concept Pipeline Integration: Loop aus Concept heraus starten
- [ ] `Dockerfile.worker` für playwright-fähigen Celery-Worker
- [ ] `pyproject.toml`: Playwright + pytest Sektion
- [ ] CI: pytest-playwright in GitHub Actions (separater `reflex`-Job)
- [ ] Unit-Tests für Service-Layer (check_uc_quality, transition_use_case,
      classify_failure, check_circle_2_gate)

### Phase 3 — Scraper-MCP (parallel zu Phase 2)

- [ ] `scraper_mcp/` in mcp-hub anlegen
- [ ] `auth.py`: Session-State, Multi-Rollen, Auto-Renew, Secret-Scanning
- [ ] `extractors.py`: Tabellen, Pagination, Downloads, API-Intercept
- [ ] `outputs.py`: CSV, JSON, PostgreSQL via Django ORM, Excel
- [ ] MCP-Tools: `scrape_table()`, `download_report()`, `screenshot_hub()`
- [ ] Windsurf-Konfiguration: `scraper_mcp` als MCP-Server

## Dateipfade (Vollständige Referenz-Implementierung)

```
dev-hub/
├── apps/
│   └── ui_tdd/
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py           # TenantAwareModel, public_id, deleted_at, i18n
│       ├── services.py         # Business-Logik, State Machine, Audit-Trail
│       ├── views.py            # HTTP-Handling only, Permission-Guards
│       ├── tasks.py            # Celery, subprocess.run(), Queue: reflex
│       ├── urls.py
│       ├── admin.py
│       └── migrations/
│           └── 0001_initial.py
├── use-cases/
│   └── concept-inline-create.md
├── domain/
│   └── dev-hub-kb.md
├── wireframes/
│   └── concept_inline_create.html
├── tests/
│   └── ui/
│       ├── .env.test              # gitignored
│       ├── .env.test.example      # committed
│       ├── .auth/                 # gitignored
│       ├── conftest.py            # tenant_id + Session-State + Multi-Rolle
│       ├── snapshots/
│       ├── test_concept_inline_create.py
│       └── audit/
│           └── test_dev_hub_audit.py
├── scripts/
│   └── run_reflex_loop.sh     # set -euo pipefail
└── docs/
    └── reflex-v01-learnings.md
```

## Technischer Stack

| Komponente | Entscheidung | Begründung |
|---|---|---|
| Test-Framework | `pytest-playwright` + `pytest-json-report` | Python, maschinenlesbare Ausgabe |
| Browser | Chromium headless | Standard, schnell, Docker-kompatibel |
| Django-Server (v0.1) | `python manage.py runserver` | Minimal |
| Playwright in Celery | `subprocess.run()` — kein `asyncio.run()` | ASGI-sicher (ADR-050) |
| Session-Management | Playwright Storage State (`.auth/*.json`) | Login einmalig |
| Credentials | `.env.test` + `detect-secrets` pre-commit | Sicherheit erzwungen |
| Wireframe | Django Template + Stub-View + HTMX-Handler | Echtes HTMX testbar |
| Feedback-Persistenz | `TestRun`-Model + `emit_audit_event()` | Audit-Trail (ADR-050 §6.5) |
| UC-Dokument | `use-cases/[name].md` | Versionierbar, diff-bar |
| Domain KB | `domain/[hub]-kb.md` + `DomainKB`-Model | Versioniert + durchsuchbar |
| Docker (Worker) | `Dockerfile.worker` mit playwright-Browser | Browser in Container |

## Glossar

| Begriff | Definition |
|---|---|
| REFLEX | Reflexive Evidence-based Loop — die Gesamtmethodik |
| Zirkel | Abgeschlossene Qualitätsstufe mit binärem Gate |
| Gate | Binäre Entscheidung: Zirkel bestanden oder nicht |
| Domain KB | Destilliertes Expertenwissen, versioniert als `domain/[hub]-kb.md` |
| UC-Problem | Fehler dessen Ursache im Use Case liegt |
| UI-Problem | Fehler dessen Ursache im Wireframe liegt |
| Wireframe | Django Template ohne Model/Service-Aufruf |
| Audit-Lauf | REFLEX-Variante für existierende UI — Zirkel 2 direkt |
| Session State | Playwright-Mechanismus: Login einmalig, JSON-Datei wiederverwenden |
| Evidenz | Maschinenlesbares Testergebnis — nicht Meinung, nicht Schätzung |

## Confirmation

Diese Entscheidung gilt als bestätigt wenn:

1. REFLEX v0.1 den Pilot-Use-Case (Concept Inline-Create, UC-DEVHUB-001)
   vollständig durchlaufen hat — alle drei Zirkel mit grünem Gate
2. `docs/reflex-v01-learnings.md` existiert mit dokumentierten Reibungspunkten
3. Mindestens ein `UC_PROBLEM` durch Testergebnisse aufgedeckt und
   behoben wurde — Beweis der Selbstverbesserung
4. `apps/ui_tdd/models.py` und `0001_initial.py` existieren und sind
   platform-compliant (public_id, deleted_at, UniqueConstraint, i18n)
5. Das Feature ist live in dev-hub und durch Playwright-Tests dauerhaft
   abgedeckt
6. Pre-commit-Hook `detect-secrets` ist aktiv — kein Session-Token
   je committed

Überprüfung: Nach Phase 1 (erwartet innerhalb von 5 Werktagen).
Staleness-Review in 12 Monaten: Ist `apps/ui_tdd/` (v1.0) implementiert?
Ist der Drift-Detector aktiv für `tests/ui/`? Ist Scraper-MCP produktiv?

## REFLEX v2.0 Erweiterungen

### Domain Agent (D-6) — LLM-gestütztes Expertise-Onboarding

Zirkel 0 wird durch einen variablen Domain Agent erweitert. Der Agent
ist **nicht hub-spezifisch** — ein `vertical` Parameter bestimmt die
Domäne (z.B. `chemical_safety`, `creative_writing`, `real_estate`).

**Ablauf:**
1. Auto-Recherche: Outline + Paperless + pgvector Memory → `domain_context`
2. LLM Domain Research via promptfw Template → strukturiertes KB-Draft
3. LLM generiert Interview-Fragen (nur Lücken, nicht alles)
4. Expert füllt Lücken (minimaler Aufwand)
5. LLM destilliert → `domain/[hub]-kb.md` (Glossar, Pflichtfelder, Invarianten)
6. LLM Cross-Check gegen ADRs + Platform-Regeln → Violations flagged

**Architektur-Prinzipien:**
- Pure Python — keine Django-Abhängigkeit im Core
- Provider-Pattern für Wissensquellen (`KnowledgeProvider` Protocol)
- promptfw-native Templates (`.jinja2` Frontmatter)
- Konfiguration via `reflex.yaml` pro Hub (deklarativ)

### Package: iil-reflex (PyPI)

Der Domain Agent und die REFLEX-Methodik-Logik leben in einem eigenen
Python Package `iil-reflex`. Dependency: nur `iil-promptfw>=0.7.0`.
Django-Integration (Models, Views, Tasks) bleibt hub-spezifisch.

```
iil-reflex/
├── reflex/
│   ├── agent.py           # DomainAgent (pure Python)
│   ├── quality.py          # UC Quality Checker
│   ├── classify.py         # Failure Classifier
│   ├── config.py           # ReflexConfig from reflex.yaml
│   ├── providers.py        # KnowledgeProvider, DocumentProvider (Protocol)
│   ├── types.py            # Dataclasses (Results, Questions, Entries)
│   └── templates/          # package_data (.jinja2)
│       ├── domain_research.jinja2
│       ├── domain_interview.jinja2
│       ├── domain_kb_distill.jinja2
│       ├── uc_quality_check.jinja2
│       ├── failure_classify.jinja2
│       └── wireframe_review.jinja2
└── tests/
```

### Erweiterte UI-Qualität (Zirkel 2)

Neben ARIA-Snapshot und pytest-playwright werden folgende Dimensionen
in Zirkel 2 geprüft:

**U-1 HTMX-Validation (ADR-048):** hx-swap Modus, hx-target Existenz,
hx-indicator Pflicht, Error-Response-Handling, kein hx-boost (AP-001).

**U-2 Component Pattern (ADR-041):** Inclusion Tag, HTMX-Fragment,
Template-Include — alle 3 Zugriffspfade pro Component.

**U-3 data-testid (ADR-040):** Coverage-Metrik für interactive Elemente.
`testid_coverage = elements_with_testid / total_interactive`.

**U-4 Responsive:** 3 Viewports (375px, 768px, 1280px), kein
horizontaler Scroll, Touch-Targets ≥ 44px.

**U-5 WCAG/axe-core:** Farbkontrast, Focus-Indikatoren, Skip-Links,
Label-Zuordnung via `@axe-core/playwright`.

**U-6 Permission-Matrix:** Systematische Matrix View × Rolle →
erwarteter HTTP-Status. Konfigurierbar via `reflex.yaml`.

### Domain-Integration

**D-1 Knowledge-Quellen:** Outline + Paperless + pgvector Memory
automatisch vor Zirkel 0 durchsucht.

**D-2 ADR Cross-Reference:** UC wird via `check_violations()` gegen
alle ADRs geprüft.

**D-3 Post-Deploy Audit:** Nach `/ship` optional Zirkel 2 Audit-Lauf
gegen frisch deployten UI.

**D-4 Error → UC Loop:** Production-Error-Patterns werden als
UC-Revision-Vorschlag in Zirkel 1 eingespeist.

**D-5 Semantic KB:** DomainKB parallel im pgvector Store für
hub-übergreifende semantische Suche.

### Provider-Pattern (Dependency Inversion)

```python
class KnowledgeProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[KnowledgeEntry]: ...

class DocumentProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[DocumentEntry]: ...
```

Implementierungen: `OutlineProvider`, `PaperlessProvider`,
`MemoryProvider`, `MockProvider` (für Tests).

### Hub-Konfiguration via reflex.yaml

```yaml
hub_name: risk-hub
vertical: chemical_safety
domain_keywords: ["SDS", "CAS", "GHS", "REACH"]
quality:
  min_acceptance_criteria: 2
  max_uc_steps: 7
viewports:
  - {name: mobile, width: 375, height: 812}
  - {name: desktop, width: 1280, height: 800}
htmx_patterns:
  banned: ["hx-boost"]
  required_on_forms: ["hx-indicator"]
permissions_matrix:
  /substances/: {anonymous: 302, viewer: 200, admin: 200}
  /substances/create/: {anonymous: 302, viewer: 403, admin: 200}
```

### Implementierungs-Reihenfolge (v2.0)

| Phase | Was | Timing |
|-------|-----|--------|
| Phase 1 | REFLEX v0.1 in dev-hub (inline, manuell) | 5 Tage |
| Phase 2a | iil-reflex Package (Core + Templates) | Nach Phase 1 |
| Phase 2b | apps/ui_tdd/ in dev-hub (nutzt iil-reflex) | Parallel |
| Phase 2c | Enhanced conftest.py (U-1..U-6) | Parallel |
| Phase 3 | Provider-Implementierungen (Outline, Paperless) | Nach Phase 2 |
| Phase 4 | Post-Deploy Audit in /ship Workflow | Nach Phase 3 |
| Phase 5 | Scraper-MCP | Parallel zu Phase 3-4 |

## Implementation Evidence

- writing-hub: `/dev-login/` + `dev_login_url` Command (Commit 5f5e8bd)
- writing-hub: `tests/ui/` Infrastruktur + 27 Audit-Tests (Commit 5f5e8bd)
- writing-hub: `feedback/writing-hub-audit.v1.feedback.json` — 27/27 PASS
- Referenz-Implementierung: `ADR-XXX-final.zip` (models, services, views, tasks,
  migration, conftest, tests, shell-script) — platform-reviewed
- iil-reflex Package-Scaffold: types, providers, agent, templates — platform-reviewed
