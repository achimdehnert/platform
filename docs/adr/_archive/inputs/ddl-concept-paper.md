# Domain Development Lifecycle (DDL)

> **Concept Paper v1.0**  
> BF Agent Platform – Strukturierte Anforderungserfassung mit AI-Unterstützung

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Problemstellung](#2-problemstellung)
3. [Lösungsansatz](#3-lösungsansatz)
4. [Use Cases](#4-use-cases)
5. [Systemarchitektur](#5-systemarchitektur)
6. [Datenmodell](#6-datenmodell)
7. [Komponenten](#7-komponenten)
8. [Workflows](#8-workflows)
9. [Technologie-Stack](#9-technologie-stack)
10. [Integration](#10-integration)
11. [Roadmap](#11-roadmap)

---

## 1. Executive Summary

Das **Domain Development Lifecycle (DDL)** System transformiert unstrukturierte Anforderungen in produktionsreife Spezifikationen durch einen AI-gestützten, iterativen Dialog.

### Kernidee

```
Freitext-Anforderung → Strukturierter Business Case → Use Cases → ADRs → Code
```

### Hauptmerkmale

| Merkmal | Beschreibung |
|---------|--------------|
| **AI-gestützter Dialog** | Iterative Extraktion von Anforderungsdetails |
| **Database-First** | PostgreSQL als Single Source of Truth |
| **Dual-Interface** | MCP Server (AI) + Web UI (Mensch) |
| **Automated Documentation** | Sphinx-Integration für lebende Dokumentation |
| **Platform-konform** | Integriert in ADR-015 Governance System |

### Zielgruppe

- **Product Owner**: Erfassung und Priorisierung von Anforderungen
- **Entwickler**: Klare, detaillierte Use Cases als Entwicklungsbasis
- **Architekten**: Nachvollziehbare Entscheidungen in ADRs
- **Stakeholder**: Transparenter Projektstatus

---

## 2. Problemstellung

### 2.1 Aktuelle Herausforderungen

**Unstrukturierte Anforderungen**
- Anforderungen kommen als E-Mails, Slack-Nachrichten, Meeting-Notizen
- Wichtige Details gehen verloren oder werden vergessen
- Keine einheitliche Struktur für verschiedene Projekttypen

**Fehlende Traceability**
- Kein Zusammenhang zwischen Anforderung → Implementierung → Dokumentation
- Architekturentscheidungen sind nicht nachvollziehbar
- Status von Anforderungen ist unklar

**Dokumentations-Chaos**
- Dokumente in verschiedenen Formaten und Orten (Confluence, Google Docs, Git)
- Dokumentation veraltet schnell
- Kein automatischer Abgleich mit dem tatsächlichen Stand

**Ineffiziente Erfassung**
- Mehrere Meetings für vollständige Anforderungsklärung
- Wiederholte Rückfragen zu gleichen Themen
- Keine kategoriespezifischen Checklisten

### 2.2 Beispiel: Typischer Anforderungs-Workflow heute

```
Tag 1: E-Mail "Wir brauchen eine neue Kundenverwaltung"
       ↓
Tag 3: Meeting zur Klärung (2h, 5 Personen)
       ↓
Tag 5: Confluence-Seite erstellt (wird nie aktualisiert)
       ↓
Tag 10: Entwicklung beginnt mit unvollständigen Infos
       ↓
Tag 20: "Das war aber anders gemeint!" 
       ↓
Tag 30: Rework, Frustration, Verzögerung
```

---

## 3. Lösungsansatz

### 3.1 Vision

Das DDL-System führt einen **strukturierten, AI-gestützten Prozess** ein, der:

1. **Freitext analysiert** und automatisch kategorisiert
2. **Gezielt nachfragt** basierend auf Kategorie und bereits bekannten Informationen
3. **Strukturierte Dokumente erzeugt** (Business Cases, Use Cases, ADRs)
4. **Dokumentation automatisch generiert** und aktuell hält
5. **Traceability sicherstellt** von Anforderung bis Code

### 3.2 Der DDL-Prozess

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DOMAIN DEVELOPMENT LIFECYCLE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ INCEPTION │ → │ BUSINESS │ → │   USE    │ → │   ADR    │           │
│  │  Dialog   │    │   CASE   │    │  CASES   │    │          │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│       ↑               │               │               │                  │
│       │               ↓               ↓               ↓                  │
│  Freitext        Strukturiert    Detailliert    Dokumentiert            │
│  Eingabe         + Kategorisiert + Priorisiert  + Entschieden           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Kategorie-spezifische Erfassung

Das System erkennt automatisch die **Kategorie** einer Anforderung und stellt entsprechende Fragen:

| Kategorie | Beschreibung | Spezifische Fragen |
|-----------|--------------|-------------------|
| `neue_domain` | Neue Fachdomäne | Domänenexperte, Datenmodell, Migration |
| `integration` | Externe Systeme | API-Dokumentation, Auth, Rate Limits |
| `optimierung` | Verbesserungen | Pain Points, Messbarkeit, Baseline |
| `erweiterung` | Feature-Erweiterung | Breaking Changes, Abhängigkeiten |
| `produktion` | Deployment/Release | Branch, Rollback-Plan, Monitoring |

### 3.4 Beispiel: Neuer Workflow mit DDL

```
Minute 0:  User: "Wir brauchen eine neue Kundenverwaltung"
           ↓
Minute 1:  AI: "Kategorie erkannt: neue_domain. 
                Wer ist der Domänenexperte?"
           ↓
Minute 5:  AI: "Welche Daten sollen erfasst werden?"
           ↓
Minute 10: AI: "Gibt es eine Migration von Altdaten?"
           ↓
Minute 15: Business Case BC-042 erstellt
           4 Use Cases automatisch abgeleitet
           ↓
Minute 20: Review durch Stakeholder
           ↓
Tag 2:     Entwicklung beginnt mit vollständiger Spezifikation
```

**Ergebnis:** 2 Stunden Meeting → 20 Minuten Dialog

---

## 4. Use Cases

### 4.1 Übersicht der System-Use-Cases

```
┌─────────────────────────────────────────────────────────────────┐
│                         DDL SYSTEM                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                          ┌─────────────┐       │
│  │   Product   │                          │  Developer  │       │
│  │    Owner    │                          │             │       │
│  └──────┬──────┘                          └──────┬──────┘       │
│         │                                        │               │
│         │  ┌────────────────────────┐           │               │
│         ├──│ UC-01: Start Inception │           │               │
│         │  └────────────────────────┘           │               │
│         │  ┌────────────────────────┐           │               │
│         ├──│ UC-02: Answer Questions│           │               │
│         │  └────────────────────────┘           │               │
│         │  ┌────────────────────────┐           │               │
│         ├──│ UC-03: Review & Approve│───────────┤               │
│         │  └────────────────────────┘           │               │
│         │                                       │               │
│         │  ┌────────────────────────┐           │               │
│         └──│ UC-04: Track Progress  │───────────┘               │
│            └────────────────────────┘                           │
│                                                                  │
│                          ┌────────────────────────┐             │
│                          │ UC-05: Detail Use Case │─────────────┤
│                          └────────────────────────┘             │
│                          ┌────────────────────────┐             │
│                          │ UC-06: Create ADR      │─────────────┤
│                          └────────────────────────┘             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 UC-01: Inception starten

**Akteur:** Product Owner, Stakeholder

**Beschreibung:** 
Der Benutzer gibt eine unstrukturierte Anforderung ein. Das System analysiert den Text, erkennt die Kategorie und beginnt einen iterativen Dialog.

**Ablauf:**
1. Benutzer gibt Freitext-Anforderung ein
2. System analysiert und extrahiert bekannte Informationen
3. System erkennt Kategorie (oder fragt nach)
4. System erstellt Draft Business Case
5. System stellt erste kategorieabhängige Frage
6. Benutzer erhält Session-ID für Fortsetzung

**Vorbedingungen:**
- Benutzer ist authentifiziert
- MCP-Server oder Web UI verfügbar

**Nachbedingungen:**
- Business Case im Status `draft` erstellt
- Inception Session aktiv
- Erste Conversation gespeichert

### 4.3 UC-02: Fragen beantworten

**Akteur:** Product Owner, Domänenexperte

**Beschreibung:**
Der Benutzer beantwortet iterativ die Fragen des Systems. Jede Antwort wird analysiert und in strukturierte Daten überführt.

**Ablauf:**
1. System zeigt aktuelle Frage mit Kontext
2. Benutzer gibt Antwort
3. System extrahiert Daten aus Antwort
4. System aktualisiert Business Case
5. System prüft ob weitere Fragen nötig
6. Bei ja: nächste Frage; bei nein: Finalisierung anbieten

**Regeln:**
- Benutzer kann Fragen überspringen
- Benutzer kann zu vorherigen Fragen zurück
- System merkt sich bereits beantwortete Fragen

### 4.4 UC-03: Review und Genehmigung

**Akteur:** Technical Lead, Architect

**Beschreibung:**
Ein Reviewer prüft den fertiggestellten Business Case und genehmigt oder fordert Änderungen an.

**Ablauf:**
1. Reviewer öffnet Business Case zur Prüfung
2. Reviewer sieht alle Details inkl. abgeleiteter Use Cases
3. Reviewer trifft Entscheidung (Approve/Reject/Changes)
4. Bei Änderungswunsch: Kommentare hinzufügen
5. System aktualisiert Status
6. Owner wird benachrichtigt

**Status-Übergänge:**
```
draft → submitted → approved
                  → changes_requested → draft
                  → rejected
```

### 4.5 UC-04: Fortschritt verfolgen

**Akteur:** Alle

**Beschreibung:**
Dashboard-Ansicht über alle Business Cases, Use Cases und deren Status.

**Features:**
- Statistiken nach Status
- Meine Business Cases
- Ausstehende Reviews
- Kürzlich aktualisiert

### 4.6 UC-05: Use Case detaillieren

**Akteur:** Developer, Business Analyst

**Beschreibung:**
Ein automatisch abgeleiteter Use Case wird mit Details angereichert: Hauptablauf, Alternativen, Ausnahmen.

**Ablauf:**
1. Developer öffnet Use Case
2. Developer fügt Flow-Steps hinzu
3. Developer definiert Preconditions/Postconditions
4. Developer ergänzt technische Hinweise
5. Status wechselt zu `detailed`

### 4.7 UC-06: ADR erstellen

**Akteur:** Architect, Tech Lead

**Beschreibung:**
Für architekturrelevante Business Cases wird ein ADR erstellt.

**Ablauf:**
1. Architect erstellt ADR mit Kontext
2. Architect dokumentiert Alternativen mit Bewertung
3. Architect trifft und dokumentiert Entscheidung
4. ADR wird mit Business Case und Use Cases verknüpft
5. Review durch weitere Architekten
6. ADR wird akzeptiert

---

## 5. Systemarchitektur

### 5.1 Architektur-Überblick

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
├──────────────────────────────────┬──────────────────────────────────────────┤
│         MCP Server               │              Web UI                       │
│    (Windsurf/Claude Desktop)     │         (Django + HTMX)                  │
│                                  │                                          │
│  ┌────────────────────────┐     │     ┌────────────────────────┐           │
│  │ • start_business_case  │     │     │ • Dashboard            │           │
│  │ • answer_question      │     │     │ • Business Case CRUD   │           │
│  │ • finalize            │     │     │ • Use Case Editor      │           │
│  │ • list/search         │     │     │ • ADR Management       │           │
│  │ • detail_use_case     │     │     │ • Review Workflow      │           │
│  └────────────────────────┘     │     └────────────────────────┘           │
├──────────────────────────────────┴──────────────────────────────────────────┤
│                              SERVICE LAYER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ InceptionService│  │BusinessCaseServ.│  │  UseCaseService │             │
│  │                 │  │                 │  │                 │             │
│  │ • start_session │  │ • create        │  │ • create        │             │
│  │ • answer_quest. │  │ • submit        │  │ • create_bulk   │             │
│  │ • finalize      │  │ • approve       │  │ • update_flow   │             │
│  │ • derive_uc     │  │ • search        │  │ • transition    │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   ADRService    │  │  LookupService  │  │  ExportService  │             │
│  │                 │  │                 │  │                 │             │
│  │ • create        │  │ • get_choices   │  │ • to_rst        │             │
│  │ • accept        │  │ • get_choice    │  │ • to_markdown   │             │
│  │ • supersede     │  │ • validate      │  │ • to_json       │             │
│  │ • link_uc       │  │ • (cached)      │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                               DATA LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         PostgreSQL                                   │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ lkp_domain   │  │ lkp_choice   │  │ dom_business │              │   │
│  │  │              │  │              │  │    _case     │              │   │
│  │  │ • bc_status  │  │ • draft      │  │              │              │   │
│  │  │ • bc_category│  │ • submitted  │  │ • code       │              │   │
│  │  │ • uc_status  │  │ • approved   │  │ • title      │              │   │
│  │  │ • uc_priority│  │ • neue_domain│  │ • status_id  │              │   │
│  │  │ • ...        │  │ • ...        │  │ • ...        │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ dom_use_case │  │   dom_adr    │  │dom_conversat.│              │   │
│  │  │              │  │              │  │              │              │   │
│  │  │ • main_flow  │  │ • context    │  │ • session_id │              │   │
│  │  │ • alt_flows  │  │ • decision   │  │ • turn       │              │   │
│  │  │ • exceptions │  │ • alternativ.│  │ • message    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────┐                                                        │
│  │     Redis       │  Session Storage für Inception Dialoge                 │
│  └─────────────────┘                                                        │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                           EXTERNAL SERVICES                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  LLM Gateway    │  │  GitHub Pages   │  │    Sphinx       │             │
│  │                 │  │                 │  │                 │             │
│  │ • Anthropic     │  │ • Hosting       │  │ • Build         │             │
│  │ • OpenAI        │  │ • CI/CD         │  │ • db_docs ext   │             │
│  │ • Fallback      │  │                 │  │                 │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Architektur-Prinzipien

| Prinzip | Beschreibung |
|---------|--------------|
| **Database-First** | PostgreSQL ist Single Source of Truth |
| **Service Layer** | Geschäftslogik in Services, nicht in Views/Models |
| **Dual Interface** | MCP für AI, Web für Menschen – gleiche Services |
| **Zero Breaking Changes** | Additive Änderungen, keine Löschungen |
| **Soft Delete** | Alle Entitäten mit `deleted_at` statt echtem Delete |

### 5.3 Deployment-Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hetzner Cloud                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Production                            │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │  BF Agent    │  │   MCP Hub    │  │    Docs      │  │   │
│  │  │  (Django)    │  │  (FastAPI)   │  │  (Sphinx)    │  │   │
│  │  │              │  │              │  │              │  │   │
│  │  │  DDL Views   │  │  DDL MCP     │  │  DDL Docs    │  │   │
│  │  │  DDL Service │  │  Server      │  │              │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │   │
│  │         │                 │                             │   │
│  │         └────────┬────────┘                             │   │
│  │                  ↓                                      │   │
│  │         ┌──────────────┐                                │   │
│  │         │  PostgreSQL  │                                │   │
│  │         │   (Primary)  │                                │   │
│  │         └──────────────┘                                │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Datenmodell

### 6.1 Entity-Relationship-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATENMODELL                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐         ┌─────────────────────────────────────────┐       │
│   │ lkp_domain  │         │              dom_business_case           │       │
│   ├─────────────┤    ┌───→├─────────────────────────────────────────┤       │
│   │ code (PK)   │    │    │ id (PK)                                 │       │
│   │ name        │    │    │ code (unique) "BC-001"                  │       │
│   └──────┬──────┘    │    │ title                                   │       │
│          │           │    │ category_id (FK) ─────┐                 │       │
│          │           │    │ status_id (FK) ───────┤                 │       │
│          ↓           │    │ problem_statement     │                 │       │
│   ┌─────────────┐    │    │ target_audience       │                 │       │
│   │ lkp_choice  │    │    │ expected_benefits     │                 │       │
│   ├─────────────┤    │    │ scope                 │                 │       │
│   │ id (PK)     │←───┼────│ success_criteria (JSON)                 │       │
│   │ domain_code │    │    │ assumptions (JSON)    │                 │       │
│   │ code        │    │    │ risks (JSON)          │                 │       │
│   │ name        │    │    │ architecture_basis (JSON)               │       │
│   │ metadata    │    │    │ owner_id (FK User)    │                 │       │
│   │ sort_order  │    │    │ inception_session_id  │                 │       │
│   └─────────────┘    │    │ search_vector         │                 │       │
│                      │    └──────────┬────────────┘                 │       │
│                      │               │                               │       │
│                      │               │ 1:n                           │       │
│                      │               ↓                               │       │
│                      │    ┌─────────────────────────────────────────┐       │
│                      │    │              dom_use_case                │       │
│                      │    ├─────────────────────────────────────────┤       │
│                      │    │ id (PK)                                 │       │
│                      │    │ code (unique) "UC-001"                  │       │
│                      │    │ business_case_id (FK) ──────────────────┘       │
│                      ├───→│ status_id (FK)                                  │
│                      ├───→│ priority_id (FK)                                │
│                      ├───→│ complexity_id (FK)                              │
│                      │    │ title                                           │
│                      │    │ actor                                           │
│                      │    │ preconditions (JSON)                            │
│                      │    │ postconditions (JSON)                           │
│                      │    │ main_flow (JSON)                                │
│                      │    │ alternative_flows (JSON)                        │
│                      │    │ exception_flows (JSON)                          │
│                      │    │ estimated_hours                                 │
│                      │    └──────────┬────────────────────────────────────  │
│                      │               │                                       │
│                      │               │ n:m                                   │
│                      │               ↓                                       │
│                      │    ┌─────────────────────┐                           │
│                      │    │  dom_adr_use_case   │                           │
│                      │    ├─────────────────────┤                           │
│                      │    │ adr_id (FK)         │                           │
│                      │    │ use_case_id (FK)    │                           │
│                      │    │ relationship_type   │                           │
│                      │    └─────────┬───────────┘                           │
│                      │              │                                        │
│                      │              ↓                                        │
│                      │    ┌─────────────────────────────────────────┐       │
│                      │    │                dom_adr                   │       │
│                      │    ├─────────────────────────────────────────┤       │
│                      │    │ id (PK)                                 │       │
│                      │    │ code (unique) "ADR-001"                 │       │
│                      ├───→│ status_id (FK)                          │       │
│                      │    │ business_case_id (FK)                   │       │
│                      │    │ supersedes_id (FK self)                 │       │
│                      │    │ context                                 │       │
│                      │    │ decision                                │       │
│                      │    │ consequences                            │       │
│                      │    │ alternatives (JSON)                     │       │
│                      │    │ decision_drivers (JSON)                 │       │
│                      │    │ affected_components (JSON)              │       │
│                      │    │ decision_date                           │       │
│                      │    └─────────────────────────────────────────┘       │
│                      │                                                       │
│                      │    ┌─────────────────────────────────────────┐       │
│                      │    │            dom_conversation             │       │
│                      │    ├─────────────────────────────────────────┤       │
│                      │    │ id (PK)                                 │       │
│                      │    │ business_case_id (FK)                   │       │
│                      │    │ session_id (UUID)                       │       │
│                      │    │ turn_number                             │       │
│                      └───→│ role_id (FK) user/assistant/system      │       │
│                           │ message                                 │       │
│                           │ extracted_data (JSON)                   │       │
│                           │ next_question                           │       │
│                           │ tokens_used                             │       │
│                           │ model_used                              │       │
│                           └─────────────────────────────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Lookup Domains

| Domain | Zweck | Beispiel-Werte |
|--------|-------|----------------|
| `bc_status` | Business Case Status | draft, submitted, approved, rejected |
| `bc_category` | Business Case Kategorie | neue_domain, integration, optimierung |
| `uc_status` | Use Case Status | draft, detailed, in_progress, done |
| `uc_priority` | Use Case Priorität | must, should, could, wont |
| `uc_complexity` | Komplexität | xs, s, m, l, xl |
| `adr_status` | ADR Status | proposed, accepted, deprecated, superseded |
| `flow_step_type` | Flow Step Typen | user_action, system_action, validation |
| `conversation_role` | Dialog-Rollen | user, assistant, system |

### 6.3 JSONB-Strukturen

**main_flow (Use Case):**
```json
[
  {"step": 1, "type": "user_action", "description": "User öffnet Formular"},
  {"step": 2, "type": "system_action", "description": "System lädt Daten"},
  {"step": 3, "type": "validation", "description": "System prüft Eingaben"},
  {"step": 4, "type": "data_operation", "description": "System speichert Daten"}
]
```

**alternatives (ADR):**
```json
[
  {
    "name": "Option A: PostgreSQL",
    "description": "Relationale Datenbank",
    "pros": ["ACID", "Bekannt", "JSON Support"],
    "cons": ["Skalierung aufwändiger"],
    "score": 8
  },
  {
    "name": "Option B: MongoDB",
    "description": "Document Store",
    "pros": ["Flexibles Schema", "Horizontal skalierbar"],
    "cons": ["Keine Transaktionen", "Konsistenz"],
    "score": 5
  }
]
```

---

## 7. Komponenten

### 7.1 InceptionService

Der Kern des Systems – verantwortlich für den iterativen Dialog.

```python
class InceptionService:
    """
    Steuert den iterativen Dialog zur Anforderungserfassung.
    
    Ablauf:
    1. start_session() - Analysiert Eingabe, erstellt Draft BC
    2. answer_question() - Verarbeitet Antworten iterativ
    3. finalize() - Schließt Session ab, leitet Use Cases ab
    """
    
    # Session Storage (Redis in Production)
    _sessions: Dict[UUID, InceptionSession]
    
    # Kategorie-spezifische Fragen
    CATEGORY_QUESTIONS = {
        'neue_domain': [
            ('domain_expert', 'Wer ist der Domänenexperte?'),
            ('domain_boundaries', 'Was sind die Grenzen der Domäne?'),
            ('data_migration', 'Gibt es zu migrierende Altdaten?'),
            ('database_schema', 'Welche Entitäten werden benötigt?'),
        ],
        'integration': [
            ('external_system', 'Welches System wird integriert?'),
            ('api_documentation', 'Gibt es eine API-Dokumentation?'),
            ('authentication', 'Wie erfolgt die Authentifizierung?'),
        ],
        # ...
    }
```

**Key Methods:**

| Methode | Input | Output | Beschreibung |
|---------|-------|--------|--------------|
| `start_session` | initial_input, user | session_id, bc_code, first_question | Startet neue Inception |
| `answer_question` | session_id, answer | next_question oder ready_to_finalize | Verarbeitet Antwort |
| `finalize` | session_id, derive_uc | business_case, use_cases | Schließt ab |
| `get_session` | session_id | InceptionSession | Session-Status |

### 7.2 MCP Server Tools

Der MCP Server exponiert die Services als AI-Tools:

| Tool | Beschreibung | Parameter |
|------|--------------|-----------|
| `start_business_case` | Startet Inception Dialog | initial_description, category? |
| `answer_question` | Beantwortet aktuelle Frage | session_id, answer |
| `finalize_business_case` | Schließt Dialog ab | session_id, adjustments?, derive_use_cases |
| `get_session_status` | Zeigt Session-Stand | session_id |
| `list_business_cases` | Listet BCs mit Filtern | status?, category?, search? |
| `get_business_case` | Zeigt BC-Details | code |
| `submit_for_review` | Reicht BC ein | code |
| `detail_use_case` | Detailliert UC-Flow | code, main_flow, ... |

### 7.3 Web UI Komponenten

**Views:**

| View | URL | Funktion |
|------|-----|----------|
| DashboardView | `/` | Übersicht, Statistiken |
| BusinessCaseListView | `/business-cases/` | Liste mit Filtern |
| BusinessCaseDetailView | `/business-cases/{code}/` | Detail mit UCs, ADRs |
| UseCaseDetailView | `/use-cases/{code}/` | UC mit Flow-Editor |
| ADRDetailView | `/adrs/{code}/` | ADR-Ansicht |

**HTMX Partials:**

| Partial | Trigger | Funktion |
|---------|---------|----------|
| `_status_badge.html` | Status-Änderung | Badge aktualisieren |
| `_list_table.html` | Filter-Änderung | Tabelle neu laden |
| `_flow_editor.html` | Flow-Edit | Flow-Steps bearbeiten |
| `_review_form.html` | Review-Button | Review-Modal |

### 7.4 Sphinx Extension

Directives für Dokumentation:

```rst
.. Einzelnen Business Case einbinden
.. db-business-case:: BC-001

.. Use Case einbinden
.. db-use-case:: UC-001

.. ADR einbinden
.. db-adr:: ADR-001

.. Liste mit Filtern
.. db-business-case-list::
   :status: approved
   :category: neue_domain
```

---

## 8. Workflows

### 8.1 Inception Workflow (Detailliert)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INCEPTION WORKFLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           START                                       │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  1. User gibt Freitext ein                                            │  │
│  │     "Wir brauchen eine Schnittstelle zu SAP für Rechnungsdaten"       │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  2. System analysiert Input                                           │  │
│  │     • Extrahiert: "SAP", "Schnittstelle", "Rechnungsdaten"            │  │
│  │     • Erkennt Kategorie: "integration"                                 │  │
│  │     • Erstellt Draft BC mit erkannten Infos                           │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  3. System lädt kategorie-spezifische Fragen                          │  │
│  │     • integration: external_system, api_docs, auth, rate_limits, ...  │  │
│  │     • Filtert bereits beantwortete (external_system = SAP)            │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  4. Dialog-Loop                                                        │  │
│  │                                                                        │  │
│  │     ┌─────────────────────────────────────────────────────────────┐   │  │
│  │     │  System: "Gibt es eine API-Dokumentation für SAP?"          │   │  │
│  │     │                                                              │   │  │
│  │     │  User: "Ja, wir haben REST API Docs, Basic Auth"            │   │  │
│  │     │                                                              │   │  │
│  │     │  System extrahiert:                                         │   │  │
│  │     │    api_documentation = "REST API Docs vorhanden"            │   │  │
│  │     │    authentication = "Basic Auth"                            │   │  │
│  │     │                                                              │   │  │
│  │     │  System: "Gibt es Rate Limits oder Quotas?"                 │   │  │
│  │     │                                                              │   │  │
│  │     │  User: "100 Requests/Minute"                                │   │  │
│  │     │                                                              │   │  │
│  │     │  ... (weitere Fragen bis vollständig)                       │   │  │
│  │     └─────────────────────────────────────────────────────────────┘   │  │
│  │                                                                        │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  5. Finalisierung                                                     │  │
│  │     • Alle Pflichtfragen beantwortet                                  │  │
│  │     • System generiert Summary                                        │  │
│  │     • User kann Anpassungen vornehmen                                 │  │
│  │     • BC Status: draft → (bleibt draft bis Submit)                    │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  6. Use Case Ableitung (optional)                                     │  │
│  │     • Kategorie "integration" → 3 Standard-UCs:                       │  │
│  │       - UC-xxx: Verbindung herstellen                                 │  │
│  │       - UC-xxx: Daten synchronisieren                                 │  │
│  │       - UC-xxx: Fehler behandeln                                      │  │
│  │     • UCs im Status "draft", müssen detailliert werden               │  │
│  └────────────────────────────┬─────────────────────────────────────────┘  │
│                               │                                              │
│                               ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           ENDE                                        │  │
│  │     Output: BC-042, UC-087, UC-088, UC-089                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Review & Approval Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      REVIEW & APPROVAL WORKFLOW                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     ┌─────────┐                                                             │
│     │  DRAFT  │ ← Inception abgeschlossen                                   │
│     └────┬────┘                                                             │
│          │                                                                   │
│          │ submit_for_review()                                               │
│          ▼                                                                   │
│     ┌─────────┐                                                             │
│     │SUBMITTED│ ← Wartet auf Review                                         │
│     └────┬────┘                                                             │
│          │                                                                   │
│          ├──────────────────────┬───────────────────┐                       │
│          │                      │                   │                       │
│          ▼                      ▼                   ▼                       │
│     ┌─────────┐          ┌───────────┐       ┌──────────┐                  │
│     │APPROVED │          │ CHANGES   │       │ REJECTED │                  │
│     │         │          │ REQUESTED │       │          │                  │
│     └────┬────┘          └─────┬─────┘       └──────────┘                  │
│          │                     │                                            │
│          │                     │ Überarbeitung                              │
│          │                     ▼                                            │
│          │               ┌─────────┐                                        │
│          │               │  DRAFT  │ ← zurück zum Bearbeiten               │
│          │               └─────────┘                                        │
│          │                                                                   │
│          ▼                                                                   │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │  Use Cases können jetzt detailliert werden                       │    │
│     │  ADRs können erstellt werden (falls Kategorie es erfordert)      │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.3 Documentation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENTATION WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐                                                            │
│  │ PostgreSQL  │                                                            │
│  │   Database  │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                    │
│         │ Scheduled (alle 6h) oder Push-Trigger                             │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GitHub Actions: Export Job                                          │   │
│  │                                                                       │   │
│  │  1. Verbindung zu PostgreSQL                                         │   │
│  │  2. Export aller BC, UC, ADR als RST                                 │   │
│  │  3. Upload als Artifact                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GitHub Actions: Build Job                                           │   │
│  │                                                                       │   │
│  │  1. Download Export-Artifact                                         │   │
│  │  2. Sphinx Build mit db_docs Extension                               │   │
│  │  3. HTML-Output generieren                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GitHub Actions: Deploy Job                                          │   │
│  │                                                                       │   │
│  │  1. Deploy zu GitHub Pages                                           │   │
│  │  2. URL: https://bf-agent.github.io/docs/                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                                                                    │
│         ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Ergebnis: Immer aktuelle Dokumentation                              │   │
│  │                                                                       │   │
│  │  • /business_cases/BC-001.html                                       │   │
│  │  • /use_cases/UC-001.html                                            │   │
│  │  • /adrs/ADR-001.html                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Technologie-Stack

### 9.1 Backend

| Komponente | Technologie | Version | Begründung |
|------------|-------------|---------|------------|
| **Framework** | Django | 5.x | Bewährt, ORM, Admin, Auth |
| **Database** | PostgreSQL | 16 | JSONB, Full-Text Search, GIN |
| **Cache/Session** | Redis | 7.x | Session Storage für Inception |
| **Task Queue** | Celery | 5.x | Async Jobs (optional) |
| **API** | Django REST Framework | 3.x | Nur für externe Integration |

### 9.2 Frontend

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Templates** | Django Templates | Server-side Rendering |
| **Interaktivität** | HTMX | Partials ohne JavaScript |
| **Reaktivität** | Alpine.js | Leichtgewichtig, deklarativ |
| **Styling** | Tailwind CSS | Utility-first, konsistent |

### 9.3 AI/MCP

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **MCP Server** | FastMCP / Python | Standard für Claude/Windsurf |
| **LLM Primary** | Anthropic Claude | Beste Reasoning-Fähigkeiten |
| **LLM Fallback** | OpenAI GPT-4 | Redundanz |
| **Embedding** | OpenAI Ada | Für zukünftige Suche |

### 9.4 Documentation

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Generator** | Sphinx | RST, Extensions, Themes |
| **Theme** | Furo | Modern, responsive |
| **Hosting** | GitHub Pages | Kostenlos, CI/CD integriert |

### 9.5 Infrastructure

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Cloud** | Hetzner | Preis-Leistung, DSGVO |
| **IaC** | Terraform | Deklarativ, versioniert |
| **CI/CD** | GitHub Actions | Native Integration |
| **Monitoring** | (TBD) | Prometheus/Grafana geplant |

---

## 10. Integration

### 10.1 Integration mit BF Agent Platform

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BF AGENT PLATFORM INTEGRATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         SHARED COMPONENTS                              │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │ platform_core│  │ LookupChoice │  │    Auth      │                │  │
│  │  │   Package    │  │    Model     │  │   (Django)   │                │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                              APPS                                      │  │
│  │                                                                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │ BF Agent │  │Travel-Beat│  │  MCP-Hub │  │   DDL    │ ← NEU       │  │
│  │  │          │  │          │  │          │  │          │              │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘              │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         DATABASE (platform schema)                     │  │
│  │                                                                        │  │
│  │  Bestehend:                    │  Neu (DDL):                          │  │
│  │  • lkp_domain                  │  • dom_business_case                 │  │
│  │  • lkp_choice                  │  • dom_use_case                      │  │
│  │  • reg_application             │  • dom_adr                           │  │
│  │  • reg_tenant                  │  • dom_conversation                  │  │
│  │  • ...                         │  • dom_review                        │  │
│  │                                │  • dom_status_history                │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 ADR-015 Governance Integration

Das DDL-System nutzt die bestehende Governance-Infrastruktur:

| Governance-Komponente | DDL-Nutzung |
|-----------------------|-------------|
| `LookupChoice` | Status, Kategorien, Prioritäten, Komplexitäten |
| `LookupService` | Cached Lookups für alle Choices |
| `GovernanceService` | Validierung von Übergängen |
| Platform Schema | Alle DDL-Tabellen im `platform` Schema |

### 10.3 MCP Hub Integration

```python
# MCP Hub Configuration (mcp_hub/servers/ddl.py)

DDL_MCP_SERVER = {
    "name": "ddl-inception",
    "description": "Domain Development Lifecycle - Inception Tools",
    "command": "python",
    "args": ["-m", "platform.governance.mcp.inception_server"],
    "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "REDIS_URL": "${REDIS_URL}",
    },
    "tools": [
        "start_business_case",
        "answer_question", 
        "finalize_business_case",
        "list_business_cases",
        "get_business_case",
        "detail_use_case",
        # ...
    ]
}
```

---

## 11. Roadmap

### 11.1 Phase 1: Foundation (Aktuell)

| Schritt | Status | Beschreibung |
|---------|--------|--------------|
| 1 | ✅ | Database Schema (SQL) |
| 2 | ✅ | Django Models |
| 3 | ✅ | Service Layer |
| 4 | ✅ | MCP Server |
| 5 | ✅ | Web UI + Templates |
| 6 | ✅ | Sphinx Extension |
| 7 | ✅ | GitHub Actions |

**Deliverables Phase 1:**
- Vollständige Code-Basis
- Dokumentierte API
- Deployment-fähig

### 11.2 Phase 2: Enhancement (Q2 2026)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| LLM Integration | Must | Echte AI-Analyse statt Heuristiken |
| Notifications | Should | E-Mail/Slack bei Status-Änderungen |
| Search | Should | Full-Text Search über alle Dokumente |
| Import/Export | Could | BC aus Markdown/Confluence importieren |
| Metrics | Could | Dashboard mit Statistiken |

### 11.3 Phase 3: Advanced (Q3 2026)

| Feature | Priorität | Beschreibung |
|---------|-----------|--------------|
| Template System | Must | Wiederverwendbare BC-Templates |
| Dependency Graph | Should | Visualisierung von UC-Abhängigkeiten |
| Auto-ADR | Could | Automatische ADR-Generierung |
| Versioning | Could | History/Diff für alle Dokumente |
| API | Could | REST/GraphQL für externe Tools |

### 11.4 Meilensteine

```
         Q1 2026              Q2 2026              Q3 2026
            │                    │                    │
  ──────────┼────────────────────┼────────────────────┼──────────
            │                    │                    │
            ▼                    ▼                    ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │   Phase 1    │    │   Phase 2    │    │   Phase 3    │
    │  Foundation  │ → │ Enhancement  │ → │   Advanced   │
    │              │    │              │    │              │
    │ • Schema     │    │ • LLM        │    │ • Templates  │
    │ • Models     │    │ • Notif.     │    │ • Versioning │
    │ • Services   │    │ • Search     │    │ • API        │
    │ • MCP/UI     │    │ • Metrics    │    │ • Graphs     │
    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## Anhang

### A. Glossar

| Begriff | Definition |
|---------|------------|
| **Business Case** | Strukturierte Anforderung mit Problem, Nutzen, Scope |
| **Use Case** | Funktionale Anforderung mit Akteur und Ablauf |
| **ADR** | Architecture Decision Record - dokumentierte Architekturentscheidung |
| **Inception** | AI-gestützter Dialog zur Anforderungserfassung |
| **MCP** | Model Context Protocol - Standard für AI Tool Integration |
| **HTMX** | JavaScript-Library für partielle Updates |
| **DDL** | Domain Development Lifecycle (dieses System) |

### B. Referenzen

- [ADR-015: Platform Governance System](./ADR-015-platform-governance.md)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [HTMX Documentation](https://htmx.org/)

### C. Änderungshistorie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 1.0 | 2026-02-04 | AI/Achim | Initiale Version |

---

**Ende des Concept Papers**
