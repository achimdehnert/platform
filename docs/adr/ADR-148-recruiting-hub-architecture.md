# ADR-148: Recruiting-Hub — Multi-Tenant SaaS für Personalberatung

| Attribut       | Wert                                    |
|----------------|-----------------------------------------|
| **Status**     | Proposed                                |
| **Scope**      | New Hub                                 |
| **Repo**       | recruiting-hub                          |
| **Erstellt**   | 2026-03-26                              |
| **Autor**      | Achim Dehnert                           |
| **Reviewer**   | –                                       |
| **Supersedes** | –                                       |
| **Relates to** | ADR-137 (Tenant-Lifecycle), ADR-120 (CI/CD), ADR-045 (Secrets), ADR-062 (billing-hub), ADR-093 (aifw) |

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
- **LinkedIn API**: Stark eingeschränkt — Integrationsstrategie wird separat geklärt
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
│   ├── integrations/        → LinkedIn-Import, Hunter-Sync, Export
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
                ↑                    ↑
         Human Review          Duplettencheck
         (Pflicht)             (automatisch)
```

- **Kein Übergang Reviewed → Contacted** ohne manuelles Approval
- **Kein Übergang Approved → Contacted** ohne bestandenen Dublettencheck
- Status-Änderungen werden als Events geloggt (Audit-Trail)

### 4.6 Hunter.io Integration

- Import: Kandidaten aus Hunter-Kampagnen → recruiting-hub Pipeline
- Export: Freigegebene Kandidaten → Hunter-Kampagne
- Sync: Status-Updates bidirektional (Webhook oder Polling)
- API-Key pro Tenant in `decouple.config()` (ADR-045)

### 4.7 DSGVO-Architektur (Phase 1 Pflicht!)

| Anforderung | Lösung |
|-------------|--------|
| Löschfristen | `compliance.RetentionPolicy` pro Tenant, Celery-Task prüft täglich |
| Auskunftsrecht | `compliance.DataExportService` — alle Daten eines Kandidaten als JSON/PDF |
| Einwilligung | `candidates.ConsentRecord` — Opt-In/Opt-Out mit Timestamp |
| Audit-Log | `compliance.AuditEntry` — Wer hat wann welches Profil gesehen/bearbeitet |
| Datenisolation | RLS (ADR-137) — Kandidaten zwischen Tenants nicht sichtbar |

---

## 5. Implementation Plan

### Phase 1: Operativer Kern (4-6 Wochen)

| # | Deliverable | Abhängigkeit |
|---|-------------|--------------|
| 1.1 | Repo-Setup: `/onboard-repo`, Dockerfile, CI/CD, django-tenancy | — |
| 1.2 | `projects/` App: Suchprojekt CRUD, Stellenbeschreibung | 1.1 |
| 1.3 | `candidates/` App: Profil-Model, Import (CSV, manuell) | 1.1 |
| 1.4 | `pipeline/` App: Pipeline-Stufen, Status-Transitions, Approval-Queue | 1.3 |
| 1.5 | `dedup/` App: Dublettencheck (E-Mail, LinkedIn-URL, Fuzzy-Name) | 1.3 |
| 1.6 | `integrations/` App: Hunter.io Export/Import (API) | 1.4 |
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

### 7.1 Positiv

- **Wiederverwendung**: django-tenancy, billing-hub, iil-aifw, infra-deploy — kein Greenfield
- **Time-to-Market**: Phase 1 in 4-6 Wochen realistisch dank Platform-Stack
- **Skalierbar**: Vom ersten Kunden zum Multi-Tenant-SaaS ohne Architekturänderung
- **Compliance-by-Design**: DSGVO von Tag 1 in der Architektur

### 7.2 Trade-offs

- **Zusätzliches Repo**: Mehr Repos = mehr Maintenance (CI/CD, Updates, Monitoring)
- **LinkedIn-Unsicherheit**: Ohne API-Zugang ist manueller Import nötig
- **LLM-Kosten**: Scoring und Klassifikation verursachen Token-Kosten pro Candidate

### 7.3 Nicht in Scope

- **Eigenes ATS**: Kein vollwertiges Applicant Tracking System — Fokus auf Sourcing
- **Kandidaten-Portal**: Kein Self-Service für Kandidaten (nur Recruiter-Facing)
- **Video-Interview**: Keine Video-Integration geplant
- **Gehaltsverhandlung**: Kein Compensation-Modul

---

## 8. Validation Criteria

### Phase 1

- [ ] Suchprojekt anlegen und Kandidaten importieren (CSV)
- [ ] Pipeline-Board zeigt Kandidaten in korrekten Stufen
- [ ] Approval-Queue: Kein Versand ohne manuelles Review
- [ ] Dublettencheck: Doppelte E-Mail/LinkedIn-URL wird erkannt
- [ ] Hunter-Export: Freigegebene Kandidaten erscheinen in Hunter-Kampagne
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

---

## 10. Offene Punkte (separat zu beschreiben)

| # | Punkt | Owner | Status |
|---|-------|-------|--------|
| OP-1 | LinkedIn-Integrationsstrategie (API vs. Extension vs. CSV) | Achim | 🔍 In Klärung |
| OP-2 | Detaillierter Teilprozess Dublettencheck in Hunter | Team | ⬜ Offen |
| OP-3 | Blacklist-Prüfung: Regeln und Datenmodell | Team | ⬜ Offen |
| OP-4 | Kriterienlogik Profilbewertung (Score-Dimensionen, Gewichtung) | Team | ⬜ Offen |
| OP-5 | Statuspflege-Regeln im CRM | Team | ⬜ Offen |
| OP-6 | Eskalationslogik bei uneindeutigen Reaktionen | Team | ⬜ Offen |
| OP-7 | Projekt-Beendigungskriterien | Team | ⬜ Offen |
| OP-8 | Domain-Wahl (recruiting.iil.pet? kundenspezifisch?) | Achim | ⬜ Offen |
| OP-9 | Nachrichtenvorlagen: In recruiting-hub oder in Hunter? | Achim | ⬜ Offen |

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-03-26 | Achim Dehnert | Initial draft — Proposed |
