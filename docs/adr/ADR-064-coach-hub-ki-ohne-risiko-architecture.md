# ADR-064: Adopt Row-Level Multi-Tenant Django SaaS for coach-hub „KI ohne Risiko™"

```yaml
status: proposed
date: 2026-02-22
amended: 2026-02-22
decision-makers: [achim.dehnert]
tags: [coach-hub, multi-tenant, assessment, governance, learning, django, htmx]
drift-detector: paths=[coach-hub/], adr=ADR-064
```

---

## Kontext und Problemstellung

„KI ohne Risiko™" ist ein Buchprojekt und Beratungskonzept für souveränen KI-Einsatz im
Mittelstand. Ziel: Überführung des Frameworks (Modelle, Canvas, Checklisten) in eine
skalierbare SaaS-Plattform für KI-Risikobewertung, Governance und Lernen.

Kernfrage: **Welche Architektur ermöglicht schnellen MVP-Start, sichere Mandantentrennung
und spätere Skalierung ohne Rewrite?**

**Nicht-Ziel (MVP):** SSO/SAML, vollständiges White-Label-Portal, komplexe Integrationen.

---

## Decision Drivers

- Schneller MVP (< 8 Wochen) mit minimalem Infrastruktur-Overhead
- Sichere Mandantentrennung (DSGVO, Corporate-Anforderungen)
- Wiederverwendung bestehender Platform-Patterns (ADR-035, ADR-041, ADR-048)
- Deterministischer, testbarer Scoring-Kern als zentrales IP
- Audit-fähige, unveränderliche Reports
- Skalierung auf 50+ Mandanten ohne Rewrite

---

## Considered Options

1. **Row-Level Isolation** — `tenant_id` auf allen Tabellen, Middleware-Enforcement, expliziter Service Layer
2. **Schema-Isolation** (django-tenants) — separates PostgreSQL-Schema pro Mandant
3. **Externe SaaS-Plattform** (Typeform + Airtable + Zapier) — No-Code-Ansatz ohne eigenes Backend

---

## Decision Outcome

**Gewählte Option: Row-Level Isolation (Option 1)**

Begründung: Schema-Isolation (Option 2) ist für MVP-Phase Overkill — Migrations-Overhead,
komplexes Tooling, kein Mehrwert bei < 100 Mandanten. Externe SaaS (Option 3) verhindert
IP-Schutz des Scoring-Kerns und erlaubt keine Custom-Workflows. Row-Level ist im Platform-
Ökosystem bereits erprobt (travel-beat, risk-hub) und ermöglicht sofortigen Start.

### Consequences

**Good:**
- Sofortiger Start mit bekanntem Stack (Django 5.x, PostgreSQL 16)
- Scoring Engine als pure Python — deterministisch, unit-testbar, kein Django-Coupling
- Wiederverwendung von Platform-Patterns (Service Layer, HTMX-Wizard, ADR-041)
- Mandantentrennung durch Middleware + explizite Service-Parameter — kein Magic Auto-Scoping
- Immutable Reports (Datei + SHA-256-Hash) — audit-ready für Corporate-Kunden

**Bad:**
- Row-Level erfordert disziplinierte Query-Hygiene (kein vergessenes `tenant_id`-Filter)
- Celery ist Pflicht für PDF-Generierung — erhöht Infrastruktur-Komplexität ab Tag 1
- Bei > 500 Mandanten muss auf Schema-Isolation migriert werden (→ ADR-XXX)
- `AssessmentResponse.user_id`-Anonymisierung muss von Anfang an designt sein (DSGVO)

### Confirmation

Compliance wird verifiziert durch:
- `pytest` mit Tenant-Isolation-Tests: jeder Service-Test erhält zwei Mandanten und prüft Cross-Tenant-Leakage
- CI-Check: `python manage.py makemigrations --check` schlägt fehl wenn `tenant_id` fehlt
- Architecture Guardian (ADR-054): `drift-detector` überwacht `coach-hub/` auf ADR-Abweichungen
- Code-Review-Checkliste: jede PR muss `tenant_id`-Filter in allen neuen QuerySets nachweisen

---

## Pros and Cons of the Options

### Option 1: Row-Level Isolation

**Pros:**
- Bekanntes Pattern im Platform-Ökosystem (travel-beat, risk-hub)
- Einfache Migrations — Standard Django
- Kein zusätzliches Tooling (kein django-tenants)
- Expliziter Service Layer macht Tenant-Kontext sichtbar

**Cons:**
- Query-Disziplin erforderlich — kein automatischer Schutz
- Performance-Risiko bei sehr vielen Mandanten (Tabellenpartitionierung nötig)

### Option 2: Schema-Isolation (django-tenants)

**Pros:**
- Starke DB-seitige Isolation
- Kein Query-Filter-Overhead

**Cons:**
- Migrations-Overhead (jedes Schema einzeln migrieren)
- Komplexes Tooling, schlechte Django-5.x-Kompatibilität
- Overkill für < 100 Mandanten
- Nicht im Platform-Ökosystem erprobt

### Option 3: Externe SaaS-Plattform

**Pros:**
- Kein Backend-Aufwand für MVP
- Schnelle Prototypen

**Cons:**
- Kein IP-Schutz für Scoring-Kern
- Keine Custom-Workflows möglich
- Vendor Lock-in
- Nicht skalierbar für Corporate-Kunden

---

## Entscheidung: Stack + Architekturprinzipien

| Dimension | Entscheidung |
|---|---|
| Stack | Python 3.12, Django 5.x, HTMX, PostgreSQL 16, Celery + Redis |
| Multi-Tenancy | Row-Level Isolation (`tenant_id`) + Middleware-Enforcement |
| Auth | django-allauth (E-Mail), RBAC (Owner/Admin/Facilitator/Member/Viewer) |
| Frontend | HTMX-first, Tailwind CSS, server-seitige SVG/PNG-Charts |
| Deployment | Docker Compose, Hetzner VM `88.198.191.108`, Nginx + Let's Encrypt, GHCR |
| Domain | `kiohnerisiko.de` (A-Record → `88.198.191.108` ✅) |
| Repo | `github.com/achimdehnert/coach-hub` |
| Deploy-Pfad | `/opt/coach-hub` |
| Port | `8007` (registriert in ADR-021 §2.3) |
| Health Endpoints | `/livez/` (liveness) + `/healthz/` (readiness) |
| Registry | `ghcr.io/achimdehnert/coach-hub:latest` |

**Tenant-Strategie:** Row-Level mit explizitem Service Layer (kein Auto-Scoping Manager).
Middleware setzt `request.tenant`; Service-Funktionen erhalten `tenant` als expliziten Parameter.

---

## Domain-Modell (ER-Diagramm)

```
Tenant (1) ──< TenantMembership >── (N) User
   │
   ├──< AssessmentTemplate (versioniert)
   │       └──< TemplateQuestion
   │
   ├──< Assessment
   │       ├──< AssessmentResponse
   │       └──< AssessmentReport (immutable, hash)
   │               └──< ShareToken (expiry, revoked)
   │
   ├──< GovernanceDocument (versioniert)
   │       └──< GovernanceAction
   │
   ├──< LearningModule
   │       └──< LearningProgress
   │
   └──< AuditLog
```

---

## Django-Projektstruktur

```
coach-hub/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── tenants/          # Tenant, TenantMembership, RBAC
│   ├── assessment/       # AssessmentTemplate, Assessment, Response
│   ├── scoring/          # Pure Python Scoring Engine (kein Django-Coupling)
│   ├── governance/       # GovernanceDocument, GovernanceAction
│   ├── learning/         # LearningModule, LearningProgress
│   ├── reports/          # AssessmentReport, ShareToken, PDF-Celery-Task
│   └── core/             # AuditLog, BaseModel, Middleware
├── templates/
├── docker/
│   └── app/
│       └── Dockerfile
├── docker-compose.prod.yml
└── .env.prod             # nie committen
```

---

## Tenant-Enforcement Middleware + RBAC

```python
# apps/core/middleware.py
class TenantMiddleware:
    def __call__(self, request):
        tenant_id = request.session.get("active_tenant_id")
        if tenant_id:
            request.tenant = Tenant.objects.get(id=tenant_id)
        else:
            request.tenant = None
        return self.get_response(request)

# apps/core/rbac.py
ROLE_PERMISSIONS = {
    "owner":       {"manage_tenant", "manage_members", "run_assessment", "view_reports", "manage_governance"},
    "admin":       {"manage_members", "run_assessment", "view_reports", "manage_governance"},
    "facilitator": {"run_assessment", "view_reports"},
    "member":      {"run_assessment"},
    "viewer":      {"view_reports"},
}

def require_permission(permission: str):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, request.tenant, permission):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

---

## Service Layer Pattern

```python
# apps/assessment/services.py
def create_assessment(tenant: Tenant, template_id: int, created_by: User) -> Assessment:
    template = AssessmentTemplate.objects.get(id=template_id, tenant=tenant)
    return Assessment.objects.create(
        tenant=tenant,
        template=template,
        created_by=created_by,
        status="draft",
    )

def submit_response(tenant: Tenant, assessment_id: int, question_id: int,
                    user: User, value: str) -> AssessmentResponse:
    assessment = Assessment.objects.get(id=assessment_id, tenant=tenant)
    return AssessmentResponse.objects.update_or_create(
        assessment=assessment,
        question_id=question_id,
        defaults={"value": value, "answered_by": user},
    )[0]
```

---

## Scoring Engine (Pure Python)

```python
# apps/scoring/engine.py
from dataclasses import dataclass
from typing import Literal

Dimension = Literal["strategy", "governance", "technology", "people", "process"]

@dataclass(frozen=True)
class ScoreResult:
    dimension: Dimension
    raw_score: float       # 0.0 - 1.0
    risk_level: Literal["low", "medium", "high", "critical"]
    label: str

def calculate_dimension_score(responses: list[dict]) -> list[ScoreResult]:
    """Pure function — no Django, no DB. Fully unit-testable."""
    ...
```

---

## HTMX UI Flow (Assessment-Wizard)

```
GET  /assessment/<id>/wizard/step/<n>/     → Wizard-Step partial
POST /assessment/<id>/wizard/step/<n>/     → Autosave + next step
GET  /assessment/<id>/results/             → Score-Dashboard
POST /assessment/<id>/report/generate/    → Celery-Task starten
GET  /assessment/<id>/report/<report_id>/ → Report-Download
POST /report/<token>/share/               → ShareToken erstellen
```

HTMX-Pattern:
- `hx-post` + `hx-target="#wizard-content"` für Schritt-Navigation
- `hx-trigger="change delay:500ms"` für Autosave
- `hx-get` + `hx-trigger="every 2s"` für PDF-Generierungs-Polling

---

## Docker & CI/CD

```dockerfile
# docker/app/Dockerfile (Multi-Stage)
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt gunicorn whitenoise

FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
RUN adduser --disabled-password --gecos "" coachuser
WORKDIR /app
COPY . /app
USER coachuser
HEALTHCHECK --interval=30s --timeout=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

CI/CD-Pipeline (3-Stufen):
1. `_ci-python.yml` — ruff, pytest, makemigrations --check
2. `_build-docker.yml` — Build + Push `ghcr.io/achimdehnert/coach-hub`
3. `_deploy-hetzner.yml` — SSH → docker compose pull + up -d --force-recreate

---

## Epics & User Stories (MVP)

### Epic 1: Tenant & RBAC
- **US-01** Als Owner kann ich meinen Workspace anlegen und Mitglieder einladen
- **US-02** Als Admin kann ich Rollen zuweisen und entziehen
- **AC:** Tenant-Isolation-Test: User A sieht keine Daten von Tenant B

### Epic 2: Assessment-Wizard
- **US-03** Als Facilitator kann ich ein Assessment aus einem Template starten
- **US-04** Als Member kann ich Fragen beantworten mit Autosave
- **US-05** Als Facilitator kann ich ein Assessment abschließen und Ergebnisse sehen
- **AC:** Wizard speichert nach jedem Schritt, Fortschritt bleibt bei Browser-Refresh

### Epic 3: Scoring & Dashboard
- **US-06** Als Facilitator sehe ich ein Radar-Chart mit 5 Dimensionen nach Abschluss
- **US-07** Als Viewer sehe ich nur freigegebene Reports, keine Rohdaten
- **AC:** Score-Berechnung ist deterministisch (gleiche Inputs → gleicher Output)

### Epic 4: Reports & Sharing
- **US-08** Als Facilitator kann ich einen PDF-Report generieren
- **US-09** Als Facilitator kann ich einen Share-Link mit Ablaufdatum erstellen
- **US-10** Als Viewer kann ich einen Report über Share-Link öffnen (kein Login nötig)
- **AC:** Share-Token ist nach Ablauf oder Widerruf ungültig (HTTP 410)

### Epic 5: Governance
- **US-11** Als Admin kann ich Governance-Dokumente hochladen und versionieren
- **US-12** Als Member kann ich zugewiesene Actions als erledigt markieren
- **AC:** Jede Dokumentversion ist unveränderlich (kein Update, nur neue Version)

---

## Test-Strategie

```python
# tests/test_tenant_isolation.py
@pytest.mark.django_db
def test_should_not_leak_assessments_across_tenants():
    tenant_a = TenantFactory()
    tenant_b = TenantFactory()
    AssessmentFactory(tenant=tenant_a)
    result = Assessment.objects.filter(tenant=tenant_b)
    assert result.count() == 0

# tests/test_scoring_engine.py
def test_should_return_deterministic_score():
    responses = [{"question_id": 1, "value": "3"}, {"question_id": 2, "value": "4"}]
    result_1 = calculate_dimension_score(responses)
    result_2 = calculate_dimension_score(responses)
    assert result_1 == result_2

# tests/test_share_token.py
@pytest.mark.django_db
def test_should_reject_expired_share_token():
    token = ShareTokenFactory(expires_at=timezone.now() - timedelta(hours=1))
    response = client.get(f"/report/{token.token}/")
    assert response.status_code == 410
```

---

## Migration Tracking

| Phase | Scope | Status | Ziel-ADR |
|-------|-------|--------|----------|
| 0 | Repo-Setup, Tenant/RBAC, CI/CD | offen | ADR-064 |
| 1 | Assessment-Wizard + Scoring Engine | offen | ADR-064 |
| 2 | Reports + PDF + ShareToken | offen | ADR-064 |
| 3 | Governance + Learning | offen | ADR-064 |
| 4 | SSO/SAML, White-Label | offen | ADR-07x |

---

## Deferred Decisions

| Thema | Begründung | Zukünftige ADR |
|-------|-----------|----------------|
| Schema-Isolation (django-tenants) | Overkill für < 100 Mandanten | ADR-07x wenn > 500 Mandanten |
| SSO/SAML | Kein MVP-Bedarf | ADR-07x Phase 4 |
| White-Label-Portal | Kein MVP-Bedarf | ADR-07x Phase 4 |
| Tabellenpartitionierung | Erst bei > 500 Mandanten relevant | ADR-07x |
| `user_id`-Anonymisierung (DSGVO) | Muss in Phase 1 designt werden | ADR-065 |

---

## Pilot-Angebot (1-Pager)

**„KI ohne Risiko™ — Pilot für Mittelstand"**

| | |
|---|---|
| **Zielgruppe** | Mittelständische Unternehmen 50-500 MA mit KI-Einsatz oder -Planung |
| **Leistung** | 1 Assessment-Durchlauf (30-40 Fragen), 1 PDF-Report, 1 Governance-Kickoff |
| **Dauer** | 4 Wochen |
| **Preis** | 2.500 EUR Festpreis (Pilot) |
| **Ergebnis** | KI-Risiko-Profil, priorisierte Maßnahmen, Governance-Roadmap |
| **Plattform** | coach-hub SaaS (Mandant wird nach Pilot übernommen oder gelöscht) |

---

## More Information

- ADR-035: Shared Django Tenancy Pattern
- ADR-041: Django Component Pattern (HTMX)
- ADR-048: HTMX Playbook
- ADR-054: Architecture Guardian
- ADR-021: Unified Deployment Pattern (Port-Tabelle §2.3)
- ADR-045: Secrets Management
- Konzeptpapier: „KI ohne Risiko™" (intern, 2026-02)
