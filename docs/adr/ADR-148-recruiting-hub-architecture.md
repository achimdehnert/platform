# ADR-148: Adopt Django Multi-Tenant SaaS Architecture for Recruiting Hub

| Attribut       | Wert                                    |
|----------------|-----------------------------------------|
| **Status**     | Proposed                                |
| **Scope**      | New Hub                                 |
| **Repo**       | recruiting-hub                          |
| **Erstellt**   | 2026-03-26                              |
| **Autor**      | Achim Dehnert                           |
| **Reviewer**   | Cascade (AI Review 2026-03-26)          |
| **Supersedes** | –                                       |
| **Relates to** | ADR-137 (Tenant-Lifecycle), ADR-120 (CI/CD), ADR-045 (Secrets), ADR-062 (billing-hub), ADR-093 (aifw), ADR-098 (Compose Hardening) |
| **implementation_status** | none                          |
| **Port**       | 8103 (prod), TBD (staging)              |
| **Deploy-Path**| `/opt/recruiting-hub`                   |
| **Registry**   | `ghcr.io/achimdehnert/recruiting-hub`   |
| **Domain**     | TBD (OP-8)                              |

---

## 1. Kontext

### 1.1 Ausgangslage

Ein Kunde aus der Personalberatung benötigt eine strukturierte Sourcing-Plattform,
die den gesamten Recruiting-Workflow abbildet: Von der Stellenbeschreibung über
LinkedIn-Sourcing und Kandidatenbewertung bis zum CRM-Export. Aktuell läuft der
Prozess manuell über LinkedIn Recruiter und Hunter.io — ohne Dublettenprüfung,
ohne Pipeline-Übersicht, ohne Conversion-Metriken.

Das System soll **mandantenfähig** sein, um es als SaaS für mehrere
Personalberatungen anzubieten.

### 1.2 Problem / Lücken

- Kein zentrales System für Suchprojekte und Kandidaten-Pipelines
- Manuelle Dublettenprüfung zwischen LinkedIn und Hunter ist fehleranfällig
- Keine automatische Profilbewertung oder Suchstring-Generierung
- Kein Reporting über Funnel-Metriken und Conversion-Raten
- Compliance-Risiko: Kein Audit-Trail für Kandidatenkontakte (DSGVO)

### 1.3 Constraints

- **Human-in-the-Loop ist Pflicht**: Kein automatischer Versand ohne Freigabe
- **Dublettencheck vor Versand**: Kein Kandidatenkontakt ohne CRM-Prüfung
- **LLM via iil-aifw**: Keine direkten API-Calls zu LLM-Providern (Platform-Standard)
- **DSGVO**: Kandidatendaten sind personenbezogen — Löschfristen, Auskunftsrecht, Audit-Log
- **LinkedIn API**: Nur Self-Service-Scopes verfügbar (openid, profile, email, w_member_social). Kein People Search, kein Recruiter System Connect ohne Partner-Status. Referenz-Implementierung: `docs/adr/inputs/linkedin_oauth/`
- **Multi-Tenant-Isolation**: Kandidatendaten zwischen Tenants NICHT sichtbar (RLS)

---

## 2. Entscheidung

Wir erstellen ein neues Repo `achimdehnert/recruiting-hub` als Django 5.x
Multi-Tenant SaaS-Anwendung, die dem bewährten Hub-Pattern folgt:

- **django-tenancy** (ADR-137) für Mandantenverwaltung und RLS
- **billing-hub** (ADR-062) für Subscription-Management
- **iil-aifw** (ADR-093) für LLM-basierte Funktionen (Scoring, Suchstrings, Klassifikation)
- **infra-deploy** (ADR-120) für CI/CD Reusable Workflows
- Docker + Hetzner + Nginx + Cloudflare (Platform-Standard)
- **Port**: 8103 (prod), Deploy-Path: `/opt/recruiting-hub`
- **Registry**: `ghcr.io/achimdehnert/recruiting-hub`
- **Health-Endpoints**: `/livez/` (liveness) + `/healthz/` (readiness) — `HEALTH_PATHS = frozenset`, `@csrf_exempt` + `@require_GET`

### App-Struktur

```
recruiting-hub/
├── src/
│   ├── config/              → Django Settings, URLs, WSGI
│   ├── identity/            → User-Model (Platform-Standard)
│   ├── tenancy/             → django-tenancy (ADR-137)
│   ├── projects/            → Suchprojekte, Stellenbeschreibungen
│   ├── candidates/          → Kandidatenprofile, Statushistorie
│   ├── pipeline/            → Pipeline-Stufen, Approval-Queue
│   ├── linkedin_oauth/       → LinkedIn OAuth 2.0 (Ref: docs/adr/inputs/linkedin_oauth/)
│   ├── integrations/        → LinkedIn-CSV-Import, Hunter-Sync, Export
│   ├── dedup/               → Dublettencheck (E-Mail, LinkedIn-URL, Fuzzy)
│   ├── intelligence/        → LLM via iil-aifw: Scoring, Suchstrings
│   ├── reporting/           → Funnel, Conversion, Cockpit
│   ├── notifications/       → Follow-up-Erinnerungen (Celery)
│   ├── compliance/          → DSGVO: Löschfristen, Auskunft, Audit-Log
│   └── common/              → Shared Utils, Middleware
├── docker/
│   ├── app/Dockerfile       → Multi-Stage, python:3.12-slim, Non-Root
│   └── ...
├── docker-compose.prod.yml
├── catalog-info.yaml            → ADR-077 Backstage-Format
├── requirements/
│   ├── base.txt
│   ├── prod.txt
│   └── dev.txt
└── tests/
```

---

## 3. Betrachtete Alternativen

### 3.1 Bestehende ATS-Plattform nutzen (Personio, Greenhouse, etc.)

- **Pro**: Sofort verfügbar, LinkedIn-Integration vorhanden
- **Contra**: Nicht mandantenfähig im Sinne des Kunden, keine LLM-Integration,
  kein Zugriff auf Sourcing-Logik, Vendor-Lock-in
- **Verworfen**: Passt nicht zum Multi-Tenant-SaaS-Geschäftsmodell

### 3.2 risk-hub erweitern statt neues Repo

- **Pro**: Infrastruktur bereits vorhanden
- **Contra**: Domäne (Arbeitsschutz) hat nichts mit Recruiting zu tun,
  Separation of Concerns verletzt, Deployment-Kopplung
- **Verworfen**: Eigenständiges Repo für eigenständige Domäne

### 3.3 No-Code-Plattform (Retool, Budibase)

- **Pro**: Schneller MVP
- **Contra**: Keine RLS, keine LLM-Integration, keine CI/CD-Pipeline,
  nicht im Platform-Ökosystem
- **Verworfen**: Skaliert nicht für SaaS

---

## 4. Begründung im Detail

### 4.1 Warum Django + django-tenancy?

Das identische Pattern wie risk-hub (ADR-137):

- `tenant_id` auf allen Models (UUID)
- Row-Level Security (RLS) in PostgreSQL
- Middleware setzt `request.tenant_id`
- `TenantManager` filtert automatisch per Tenant
- Module-Subscriptions über billing-hub

### 4.2 Warum eigenes Repo?

Recruiting ist eine eigenständige Domäne mit eigenen Datenmodellen (Kandidaten,
Suchprojekte, Pipelines). Diese haben keinen fachlichen Overlap mit Arbeitsschutz,
CAD oder Trading. Ein eigenes Repo ermöglicht:

- Unabhängige Deployment-Zyklen
- Eigene Domain (z.B. `recruiting.iil.pet` oder kundenspezifisch)
- Klare Team-Ownership

### 4.3 LLM-Integration via iil-aifw

Alle KI-Funktionen laufen über das iil-aifw Package (ADR-093):

| Funktion | iil-aifw Feature |
|----------|-----------------|
| Suchstring-Generierung | `aifw.generate()` mit Recruiting-Prompt-Template |
| Profilbewertung / Scoring | `aifw.generate()` mit Scoring-Schema (Pydantic) |
| Antwortklassifikation | `aifw.generate()` mit Klassifikations-Template |
| Projektfit-Vorschläge | `aifw.generate()` mit Matching-Template |

Keine direkten API-Calls zu OpenAI, Anthropic, etc. — Token-Kosten werden
über aifw geroutet und sind per Tenant messbar.

### 4.4 Dublettencheck-Architektur

```
Neuer Kandidat
  → E-Mail-Match (exakt)
  → LinkedIn-URL-Match (normalisiert)
  → Name + Firma Fuzzy-Match (trigram, pg_trgm)
  → Ergebnis: duplicate / possible_duplicate / unique
```

Schwellwerte konfigurierbar per Tenant.

### 4.5 Pipeline & Approval-Workflow

```
Sourced → Reviewed → Approved → Contacted → Replied → Interview → Placed
                ↑           ↑          ↑
         Human Review  Duplettencheck  Email Verification
         (Pflicht)     (automatisch)   (Hunter.io /v2/email-verifier)
```

- **Kein Übergang Reviewed → Approved** ohne manuelles Approval
- **Kein Übergang Approved → Contacted** ohne bestandenen Dublettencheck
- **Kein Übergang Approved → Contacted** ohne E-Mail-Verification (`valid` Status)
- Nach Approval: automatisch Lead in Hunter anlegen (`/v2/leads`)
- Status-Änderungen werden als Events geloggt (Audit-Trail)

### 4.6 LinkedIn Integration (3-Tier-Strategie)

Referenz-Implementierung: `docs/adr/inputs/linkedin_oauth/` — produktionsreife Django-App
mit OAuth 2.0 Flow, Token-Refresh (Celery Beat), CSRF-Schutz und Service-Layer.

#### Tier 1: OAuth Self-Service (Phase 1 — sofort umsetzbar)

Die bestehende `linkedin_oauth` App wird als eigenständige Django-App in den
recruiting-hub integriert. Verfügbare Funktionen ohne LinkedIn-Partner-Genehmigung:

| Feature | Scope | Nutzen im Recruiting |
|---------|-------|---------------------|
| Recruiter-Login via LinkedIn | `openid`, `profile`, `email` | SSO, Identitätsverifikation |
| Job-Posts veröffentlichen | `w_member_social` | Employer Branding, Stellenanzeigen |
| Token auto-refresh | — (Celery Beat, 7d Fenster) | Unterbrechungsfreier Betrieb |
| Token-Status / Introspection | — | Settings-Page, Health-Monitoring |

**Architektur-Anpassungen an Referenz-Code:**

| Bereich | Ist (Referenz) | Soll (recruiting-hub) |
|---------|---------------|----------------------|
| Config | `getattr(settings, "LINKEDIN_OAUTH")` | `decouple.config("LINKEDIN_CLIENT_ID")` (ADR-045) |
| Token-Felder | `TextField` (Klartext) | `EncryptedTextField` (django-fernet-fields) |
| Rate-Limiting | Nicht implementiert | `tenacity` retry mit exponential backoff |
| Multi-Tenant | `tenant_id` vorhanden | + RLS-Policy auf `linkedin_oauth_token` Tabelle |

**OAuth-Flow (aus Referenz-Code):**

```
Recruiter → GET /linkedin/login/
         → Redirect → LinkedIn Consent Page
         → LinkedIn → GET /linkedin/callback/?code=X&state=Y
         → Token in DB (LinkedInToken) → Redirect /dashboard/?li_connected=1
```

**Celery Beat Schedule:**
```python
CELERY_BEAT_SCHEDULE = {
    "refresh-linkedin-tokens": {
        "task": "linkedin_oauth.tasks.refresh_expiring_tokens",
        "schedule": crontab(hour=2, minute=0),  # daily at 02:00
    },
}
```

#### Tier 2: Manueller Import (Phase 1 — Hauptweg für Kandidaten)

LinkedIn bietet **keine öffentliche API** für Kandidatensuche oder Profilzugriff
Dritter. Der operative Hauptweg für Kandidatendaten:

| Methode | Beschreibung | Aufwand |
|---------|-------------|--------|
| CSV-Export aus LinkedIn Recruiter | Recruiter exportiert Kandidatenlisten → Upload in recruiting-hub | Gering |
| Manuelles Profil-Erfassen | Recruiter kopiert Profildaten in Formular | Gering |
| Browser-Extension (Zukunft) | One-Click-Import von LinkedIn-Profilseiten | Mittel |

**CSV-Import-Format (zu definieren):**
- Pflichtfelder: Name, LinkedIn-URL
- Optional: E-Mail, Firma, Titel, Standort, Skills
- Duplettencheck automatisch beim Import (E-Mail + LinkedIn-URL)

#### Tier 3: Recruiter System Connect (Langfrist — requires Partnership)

LinkedIn Talent Solutions API (RSC) erfordert LinkedIn-Partner-Status:

| Feature | API | Voraussetzung |
|---------|-----|---------------|
| Programmatische Kandidatensuche | People Search API | Partner-Vertrag |
| InMail senden | Messaging API | Recruiter-Lizenz + Partner |
| ATS-Sync | Recruiter System Connect | Zertifizierung |

**Entscheidung**: Tier 3 wird als Langfrist-Option dokumentiert, aber NICHT in Phase 1-3
implementiert. Die Architektur (Adapter-Pattern in `integrations/`) erlaubt spätere
Ergänzung ohne Refactoring. Bei Erreichen des LinkedIn-Partner-Status → **eigener ADR** für RSC-Integration.

### 4.7 Hunter.io Integration

Hunter.io wird als primärer Outreach-Kanal genutzt. Die V2 REST API bietet
drei Kernfunktionen, die direkt in den Recruiting-Workflow integriert werden.

#### API-Endpoints (V2)

| # | Endpoint | Methode | Zweck im Workflow |
|---|----------|---------|-------------------|
| A | `/v2/email-finder` | `GET` | Geschäftliche E-Mail aus Name + Domain ermitteln |
| B | `/v2/email-verifier` | `GET` | Gefundene E-Mail validieren (deliverable?) |
| C | `/v2/leads` | `POST` | Kandidat als Lead in Hunter speichern |

**A. Email Finder** — nach CSV-Import aus LinkedIn (Kandidat hat Name + Firma, braucht E-Mail):
```
GET https://api.hunter.io/v2/email-finder
    ?domain=example.com
    &first_name=Max
    &last_name=Muster
    &api_key={HUNTER_API_KEY}
```
Falls die Domain nicht direkt aus LinkedIn kommt: Mapping-Logik `company_name → domain`
über Domain-Search (`/v2/domain-search`) oder manuelles Firmen-Directory.

**B. Email Verification** — vor Pipeline-Übergang `Approved → Contacted`:
```
GET https://api.hunter.io/v2/email-verifier
    ?email=max.muster@example.com
    &api_key={HUNTER_API_KEY}
```
Ergebnis: `valid` / `invalid` / `accept_all` / `unknown` — nur `valid` darf in Outreach.

**C. Lead anlegen** — nach Approval, Kandidat wird für Outreach-Kampagne vorbereitet:
```
POST https://api.hunter.io/v2/leads?api_key={HUNTER_API_KEY}
Content-Type: application/json

{
    "first_name": "Max",
    "last_name": "Muster",
    "email": "max.muster@example.com",
    "company": "Example AG"
}
```

#### Integration in den Recruiting-Workflow

```
CSV-Import (LinkedIn)
  → Kandidat in recruiting-hub (Name, Firma, LinkedIn-URL)
  → [A] Email Finder: Name + Domain → E-Mail
  → [B] Email Verifier: E-Mail validieren
  → Human Review (Approval-Queue)
  → [C] Lead anlegen in Hunter (nach Freigabe)
  → Hunter-Kampagne: Outreach via E-Mail-Sequenz
  → Status-Sync: Hunter → recruiting-hub (Replied/Bounced/Opened)
```

#### Service-Architektur

```python
# integrations/services/hunter.py

class HunterService:
    """Stateless service — API-Key pro Tenant via decouple.config()."""

    BASE_URL = "https://api.hunter.io/v2"

    def find_email(self, first_name: str, last_name: str, domain: str) -> EmailFinderResult
    def verify_email(self, email: str) -> EmailVerifyResult
    def create_lead(self, lead: LeadData) -> LeadResult
    def get_lead(self, lead_id: int) -> LeadResult
    def list_leads(self, offset: int = 0, limit: int = 20) -> list[LeadResult]
```

**Config (ADR-045):**
```python
# settings.py
HUNTER_API_KEY = config("HUNTER_API_KEY")          # pro Tenant in .env
HUNTER_RATE_LIMIT_PER_SECOND = config("HUNTER_RATE_LIMIT", default=10, cast=int)
```

#### Rate-Limits & Quotas

| Plan | Requests/Sek | Email-Finds/Monat | Verifications/Monat |
|------|-------------|-------------------|---------------------|
| Free | 10 | 25 | 50 |
| Starter | 10 | 500 | 1.000 |
| Growth | 15 | 5.000 | 10.000 |
| Business | 20 | 50.000 | 100.000 |

**Implementierung:**
- `tenacity` retry mit exponential backoff bei 429 (Rate Limit)
- Quota-Tracking pro Tenant in DB (`integrations.HunterQuota`)
- Warnung an Recruiter wenn 80% des Monatskontingents erreicht

#### Adapter-Pattern für Erweiterbarkeit

```python
# integrations/adapters/base.py
class OutreachAdapter(Protocol):
    def find_email(self, first_name, last_name, domain) -> EmailResult: ...
    def verify_email(self, email) -> VerifyResult: ...
    def create_lead(self, lead) -> LeadResult: ...

# integrations/adapters/hunter.py
class HunterAdapter(OutreachAdapter): ...

# integrations/adapters/apollo.py  (Zukunft)
class ApolloAdapter(OutreachAdapter): ...
```

Erlaubt späteren Wechsel zu Apollo.io, Lemlist, etc. ohne Refactoring der Pipeline-Logik.

### 4.8 Health-Endpoints (Platform-Standard)

```python
# common/views.py
HEALTH_PATHS = frozenset({"/livez/", "/healthz/"})

@csrf_exempt
@require_GET
def livez(request):
    return JsonResponse({"status": "ok"})

@csrf_exempt
@require_GET
def healthz(request):
    # Prüft DB-Verbindung + Redis + Hunter-API-Erreichbarkeit
    return JsonResponse({"status": "ok", "db": "connected", "redis": "connected"})
```

**Compose-HEALTHCHECK** (nur in `docker-compose.prod.yml`, NICHT im Dockerfile):
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/livez/')"]
  interval: 30s
  timeout: 5s
  retries: 3
```

**Worker/Beat Healthcheck**: `pidof python3.12` (nicht `celery inspect ping`).

### 4.9 catalog-info.yaml (ADR-077)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: recruiting-hub
  description: Multi-Tenant SaaS für Personalberatung
  annotations:
    github.com/project-slug: achimdehnert/recruiting-hub
spec:
  type: service
  lifecycle: development
  owner: achimdehnert
  system: iil-platform
```

### 4.10 DSGVO-Architektur (Phase 1 Pflicht!)

| Anforderung | Lösung |
|-------------|--------|
| Löschfristen | `compliance.RetentionPolicy` pro Tenant, Celery-Task prüft täglich |
| Auskunftsrecht | `compliance.DataExportService` — alle Daten eines Kandidaten als JSON/PDF |
| Einwilligung | `candidates.ConsentRecord` — Opt-In/Opt-Out mit Timestamp |
| Audit-Log | `compliance.AuditEntry` — Wer hat wann welches Profil gesehen/bearbeitet |
| Datenisolation | RLS (ADR-137) — Kandidaten zwischen Tenants nicht sichtbar |

### 4.11 Compose-Hardening (ADR-098)

```yaml
# docker-compose.prod.yml — Platform-Standard
services:
  web:
    deploy:
      resources:
        limits:
          memory: 512M
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    restart: unless-stopped
    env_file: .env.prod
  worker:
    deploy:
      resources:
        limits:
          memory: 384M
    restart: unless-stopped
  db:
    shm_size: 128m
    deploy:
      resources:
        limits:
          memory: 256M
```

---

## 5. Implementation Plan

### Phase 1: Operativer Kern (4-6 Wochen)

| # | Deliverable | Abhängigkeit |
|---|-------------|--------------|
| 1.1 | Repo-Setup: `/onboard-repo`, Dockerfile, CI/CD, django-tenancy | — |
| 1.1b | `linkedin_oauth/` App integrieren (aus Referenz, ADR-045 angepasst) | 1.1 |
| 1.2 | `projects/` App: Suchprojekt CRUD, Stellenbeschreibung | 1.1 |
| 1.3 | `candidates/` App: Profil-Model, Import (CSV, manuell) | 1.1 |
| 1.4 | `pipeline/` App: Pipeline-Stufen, Status-Transitions, Approval-Queue | 1.3 |
| 1.5 | `dedup/` App: Dublettencheck (E-Mail, LinkedIn-URL, Fuzzy-Name) | 1.3 |
| 1.6a | `integrations/` App: HunterService (Email-Finder, Verifier, Leads) | 1.3 |
| 1.6b | `integrations/` App: OutreachAdapter Protocol + HunterAdapter | 1.6a |
| 1.6c | `integrations/` App: Quota-Tracking pro Tenant (HunterQuota Model) | 1.6a |
| 1.7 | `compliance/` App: Audit-Log, Löschfristen, Consent-Tracking | 1.3 |
| 1.8 | Templates + HTMX: Projekt-Dashboard, Kandidaten-Liste, Pipeline-Board | 1.4 |

### Phase 2: Intelligente Unterstützung (3-4 Wochen)

| # | Deliverable | Abhängigkeit |
|---|-------------|--------------|
| 2.1 | `intelligence/` App: Suchstring-Generator via iil-aifw | Phase 1 |
| 2.2 | Profil-Scoring: LLM-basierte Bewertung gegen Stellenbeschreibung | 2.1 |
| 2.3 | Antwortklassifikation: Interesse/Absage/Rückfrage/OOO | 2.1 |
| 2.4 | Projektfit-Vorschläge: Matching bestehender Kandidaten zu neuen Projekten | 2.2 |
| 2.5 | Follow-up-Erinnerungen: Celery-Tasks, konfigurierbar per Tenant | Phase 1 |

### Phase 3: Mandatsintelligenz (2-3 Wochen)

| # | Deliverable | Abhängigkeit |
|---|-------------|--------------|
| 3.1 | Projektcockpit: KPIs pro Suchauftrag (Pipeline-Füllstand, Response-Rate) | Phase 1 |
| 3.2 | Shortlist-Briefings: PDF-Export für Auftraggeber | Phase 2 |
| 3.3 | Sourcing-Funnel: Visualisierung der Pipeline-Stufen | Phase 1 |
| 3.4 | Conversion-Raten: Sourced→Contacted→Replied→Interview→Placed | Phase 1 |
| 3.5 | Kundenreporting: Multi-Projekt-Übersicht pro Mandant | 3.1 |

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LinkedIn API-Zugang nicht möglich | Hoch | Hoch | CSV-Import als Fallback, Browser-Extension evaluieren |
| Hunter API ändert sich | Mittel | Mittel | Adapter-Pattern, API-Version pinnen |
| LLM-Scoring-Qualität unzureichend | Mittel | Mittel | Prompt-Tuning, Few-Shot-Beispiele, Human-Override |
| DSGVO-Anforderungen unterschätzt | Niedrig | Hoch | Compliance-App in Phase 1 (nicht nachrüsten!) |
| Token-Kosten pro Tenant zu hoch | Niedrig | Mittel | aifw Budget-Limits, Caching, Batch-Scoring |

---

## 7. Konsequenzen

### 7.0 Confirmation

Die Entscheidung gilt als bestätigt wenn:

1. **Phase 1 Validation Criteria** (Section 8) alle erfüllt sind
2. **Erster Tenant** erfolgreich ongeboardet (Suchprojekt + Pipeline + Hunter-Export)
3. **RLS-Isolation** per SQL-Test verifiziert (Tenant A sieht keine Daten von Tenant B)
4. **DSGVO-Audit**: Audit-Log, Löschfristen und Auskunftsrecht funktional getestet
5. **Health-Endpoints** `/livez/` + `/healthz/` auf Port 8103 erreichbar

Nach erfolgreicher Confirmation: Status → `Accepted`, `implementation_status` → `partial`.

### 7.1 Positiv

- **Wiederverwendung**: django-tenancy, billing-hub, iil-aifw, infra-deploy — kein Greenfield
- **Time-to-Market**: Phase 1 in 4-6 Wochen realistisch dank Platform-Stack
- **Skalierbar**: Vom ersten Kunden zum Multi-Tenant-SaaS ohne Architekturänderung
- **Compliance-by-Design**: DSGVO von Tag 1 in der Architektur

### 7.2 Trade-offs

- **Zusätzliches Repo**: Mehr Repos = mehr Maintenance (CI/CD, Updates, Monitoring)
- **LinkedIn-Limitation**: Self-Service OAuth nur für Login + Posts — Kandidatendaten via CSV-Import (Tier 2)
- **LLM-Kosten**: Scoring und Klassifikation verursachen Token-Kosten pro Candidate

### 7.3 Nicht in Scope

- **Eigenes ATS**: Kein vollwertiges Applicant Tracking System — Fokus auf Sourcing
- **Kandidaten-Portal**: Kein Self-Service für Kandidaten (nur Recruiter-Facing)
- **Video-Interview**: Keine Video-Integration geplant
- **Gehaltsverhandlung**: Kein Compensation-Modul

---

## 8. Validation Criteria

### Phase 1

- [ ] LinkedIn OAuth: Recruiter kann sich via LinkedIn verbinden (/linkedin/login/ → callback)
- [ ] LinkedIn Token-Status auf Settings-Seite sichtbar
- [ ] Suchprojekt anlegen und Kandidaten importieren (CSV)
- [ ] Pipeline-Board zeigt Kandidaten in korrekten Stufen
- [ ] Approval-Queue: Kein Versand ohne manuelles Review
- [ ] Dublettencheck: Doppelte E-Mail/LinkedIn-URL wird erkannt
- [ ] Hunter Email-Finder: Name + Domain → E-Mail wird korrekt ermittelt
- [ ] Hunter Email-Verifier: Nur `valid` E-Mails passieren das Gate vor Contacted
- [ ] Hunter Lead-Export: Freigegebene Kandidaten erscheinen als Leads in Hunter
- [ ] Hunter Quota-Tracking: Verbrauch pro Tenant sichtbar, Warnung bei 80%
- [ ] RLS: Tenant A sieht keine Kandidaten von Tenant B
- [ ] Audit-Log: Jede Profil-Ansicht und Status-Änderung geloggt

### Phase 2

- [ ] Suchstring-Vorschlag aus Stellenbeschreibung (LLM via iil-aifw)
- [ ] Profil-Score > 0.7 Korrelation mit manueller Bewertung (Stichprobe n=50)
- [ ] Antwortklassifikation: > 90% Accuracy auf Testset

### Phase 3

- [ ] Projektcockpit: KPIs korrekt berechnet
- [ ] Shortlist-PDF: Generiert mit Kandidaten-Profilen
- [ ] Funnel-Visualisierung: Drop-off-Raten pro Stufe sichtbar

---

## 9. Referenzen

- **ADR-137**: Tenant-Lifecycle, Self-Service Module-Buchung und RLS
- **ADR-120**: Unified Deployment Pipeline
- **ADR-093**: AI Config App — aifw als shared Django-App
- **ADR-062**: Central Billing Service (billing-hub)
- **ADR-045**: Secrets & Environment Management
- **ADR-022**: Platform Consistency Standard
- **ADR-041**: Django Component Pattern
- **ADR-048**: HTMX Playbook
- Outline Idee: [Recruiting-Hub — Multi-Tenant SaaS für Personalberatung](https://knowledge.iil.pet/doc/recruiting-hub-multi-tenant-saas-fur-personalberatung-iRmTBvTO9f)
- Referenz-Code: `docs/adr/inputs/linkedin_oauth/` (LinkedIn OAuth Django-App)

---

## 10. Offene Punkte (separat zu beschreiben)

| # | Punkt | Owner | Status |
|---|-------|-------|--------|
| OP-1 | LinkedIn-Integrationsstrategie → **Entschieden**: 3-Tier (OAuth Self-Service + CSV-Import + RSC langfristig), siehe Section 4.6 | Achim | ✅ Entschieden |
| OP-2 | Detaillierter Teilprozess Dublettencheck in Hunter → Phase 1.5 | Team | ⬜ Phase 1 |
| OP-3 | Blacklist-Prüfung: Regeln und Datenmodell → Phase 1.5 | Team | ⬜ Phase 1 |
| OP-4 | Kriterienlogik Profilbewertung (Score-Dimensionen, Gewichtung) → Phase 2.2 | Team | ⬜ Phase 2 |
| OP-5 | Statuspflege-Regeln im CRM → Phase 1.6a | Team | ⬜ Phase 1 |
| OP-6 | Eskalationslogik bei uneindeutigen Reaktionen → Phase 2.3 | Team | ⬜ Phase 2 |
| OP-7 | Projekt-Beendigungskriterien → Phase 1.4 | Team | ⬜ Phase 1 |
| OP-8 | Domain-Wahl (recruiting.iil.pet? kundenspezifisch?) → vor Phase 1 Deploy | Achim | ⬜ Pre-Deploy |
| OP-9 | Nachrichtenvorlagen: In recruiting-hub oder in Hunter? → Phase 1.6a | Achim | ⬜ Phase 1 |

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-26 | Achim Dehnert | Initial draft — Proposed |
| 2026-03-26 | Achim Dehnert | LinkedIn-Integration: 3-Tier-Strategie aus Referenz-Code (OP-1 → Entschieden) |
| 2026-03-26 | Achim Dehnert | Hunter.io V2 API: Email-Finder, Verification, Leads + Adapter-Pattern (Section 4.7) |
| 2026-03-26 | Cascade (Review) | Review-Fixes: B1 implementation_status, B2 Health-Endpoints, B3 Port 8103, B4 catalog-info, B5 Confirmation + S1-S7 |
