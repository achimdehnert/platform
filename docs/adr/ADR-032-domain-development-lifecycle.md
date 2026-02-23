---
status: "deprecated"
date: 2026-02-21
decision-makers: Achim Dehnert
---

> **Deprecated**: duplicate of ADR-017 (already superseded) — DDL concept not adopted

# ADR-032: Domain Development Lifecycle (DDL)

| Metadata    | Value |
| ----------- | ----- |
| **Status** | Deprecated |
| **Date**    | 2026-02-13 |
| **Author**  | Achim Dehnert |
| **Related** | ADR-010 (MCP Tool Governance), ADR-022 (Platform Consistency) |
| **Input**   | `docs/adr/inputs/ddl-concept-paper.md`, `ddl-concept-part1-overview.md`, `ddl-concept-part2-architecture.md`, `ddl-concept-part3-workflow.md` |

---

## 1. Context

### 1.1 Problem

Anforderungen in der Platform kommen als E-Mails, Chat-Nachrichten, Meeting-Notizen
oder mündliche Beschreibungen. Es gibt keinen strukturierten Prozess von der Idee
bis zum Code:

```text
Freitext → Meeting (2h) → Confluence-Seite (veraltet) → Entwicklung (unvollständig)
         → "Das war aber anders gemeint!" → Rework → Verzögerung
```

**Konkrete Probleme:**

- **Verlorenes Wissen:** Anforderungen in Chats besprochen, nie dokumentiert
- **Keine Traceability:** Kein Zusammenhang Anforderung → Implementierung → Doku
- **Inkonsistente Dokumentation:** Jedes Projekt dokumentiert anders
- **Ineffiziente Erfassung:** Mehrere Meetings für vollständige Klärung

### 1.2 Vision

```text
Freitext-Idee → Strukturierter Business Case → Use Cases → ADRs → Code
```

Ein AI-gestützter, iterativer Dialog ersetzt mehrstündige Meetings durch einen
15-20 Minuten Inception-Prozess mit vollständiger Spezifikation.

---

## 2. Decision

### 2.1 DDL als Platform-Service

Das DDL-System wird als **eigener Service** mit Dual-Interface implementiert:

| Interface | Zielgruppe | Technologie |
| --------- | ---------- | ----------- |
| MCP Server (`inception_mcp`) | Entwickler via IDE | FastMCP (ADR-010 konform) |
| Web UI | Product Owner, Stakeholder | Django (HTMX + Tailwind) |

**Kein eigenständiges Repo** — DDL wird als App innerhalb eines bestehenden
Django-Projekts implementiert (z.B. `platform` oder eigene Django-App).

### 2.2 DDL-Prozess (4 Phasen)

```text
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ INCEPTION │ → │ BUSINESS │ → │   USE    │ → │   ADR    │
│  Dialog   │    │   CASE   │    │  CASES   │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     ↑               │               │               │
     │               ↓               ↓               ↓
  Freitext       Strukturiert    Detailliert    Dokumentiert
  Eingabe        + Kategorisiert + Priorisiert  + Entschieden
```

**Phase 1: Inception**
- User gibt Freitext-Anforderung ein
- AI analysiert, kategorisiert, startet iterativen Dialog
- Kategorie-spezifische Fragen (neue_domain, integration, optimierung, etc.)

**Phase 2: Business Case**
- Strukturierter BC mit allen relevanten Feldern
- Status-Workflow: `draft → submitted → approved | changes_requested | rejected`
- Automatische Kategorisierung und Priorisierung

**Phase 3: Use Cases**
- Automatisch aus Business Case abgeleitet
- Manuell detaillierbar (Flow-Steps, Pre/Postconditions)
- Verknüpft mit Business Case und ADRs

**Phase 4: ADR-Erstellung**
- Für architekturrelevante Business Cases
- Template-basiert, automatisch vorausgefüllt
- Integration in `platform/docs/adr/` Struktur

### 2.3 Datenmodell (Kern)

| Entity | Zweck | Beziehung |
| ------ | ----- | --------- |
| `BusinessCase` | Strukturierte Anforderung | 1:N UseCase, 1:N ADR |
| `UseCase` | Detaillierter Anwendungsfall | N:1 BusinessCase |
| `InceptionSession` | AI-Dialog-Verlauf | 1:1 BusinessCase |
| `Conversation` | Einzelne Frage-Antwort | N:1 InceptionSession |
| `ADRRecord` | Architecture Decision | N:1 BusinessCase |

**Database-First:** PostgreSQL als Single Source of Truth.
Alle Artefakte (BC, UC, ADR) leben in der Datenbank, nicht als Dateien.

### 2.4 Kategorie-spezifische Erfassung

| Kategorie | Beschreibung | Spezifische Fragen |
| --------- | ------------ | ------------------ |
| `neue_domain` | Neue Fachdomäne | Domänenexperte, Datenmodell, Migration |
| `integration` | Externe Systeme | API-Dokumentation, Auth, Rate Limits |
| `optimierung` | Verbesserungen | Pain Points, Messbarkeit, Baseline |
| `erweiterung` | Feature-Erweiterung | Breaking Changes, Abhängigkeiten |
| `produktion` | Deployment/Release | Branch, Rollback-Plan, Monitoring |

### 2.5 MCP-Integration (inception_mcp)

Der `inception_mcp` Server bietet Tools für den AI-Dialog:

| Tool | Beschreibung | Kategorie |
| ---- | ------------ | --------- |
| `start_inception` | Freitext analysieren, Session starten | DATA_MUTATION |
| `answer_question` | Antwort verarbeiten, nächste Frage | DATA_MUTATION |
| `get_business_case` | BC-Details abrufen | DATA_READ |
| `list_business_cases` | Übersicht aller BCs | DATA_READ |
| `finalize_business_case` | BC abschließen | DATA_MUTATION |
| `create_adr_from_bc` | ADR aus BC generieren | DATA_MUTATION |

Alle Tools folgen ADR-010 Governance (ToolSpec, Response Contract, Validator).

### 2.6 Technologie-Stack

| Komponente | Technologie |
| ---------- | ----------- |
| Backend | Django 5.x (Service Layer Pattern) |
| Frontend | HTMX + Tailwind (ADR-022 konform) |
| AI | LLM via `llm_mcp` oder direkter API-Call |
| MCP Server | FastMCP (`inception_mcp`) |
| Database | PostgreSQL 16 |
| Dokumentation | Sphinx-Integration (automatisch aus DB) |
| Tests | pytest + Factory Boy |

---

## 3. Implementation Roadmap

### Phase 1: Foundation (MVP)

| Task | Aufwand |
| ---- | ------- |
| Django-App `ddl` mit Models (BusinessCase, UseCase, Session, Conversation) | 2 Tage |
| Admin-UI für manuelle BC-Erstellung und -Verwaltung | 0.5 Tage |
| `inception_mcp` Server mit `start_inception` + `answer_question` | 2 Tage |
| AI-Prompt-Templates für Kategorisierung und Frage-Generierung | 1 Tag |
| Tests (Models, Services, MCP Tools) | 1 Tag |

### Phase 2: Web UI

| Task | Aufwand |
| ---- | ------- |
| Dashboard (alle BCs, Status-Statistiken, meine BCs) | 1 Tag |
| BC-Detail-View mit Use-Case-Liste | 1 Tag |
| Inception-Dialog als Chat-UI (HTMX) | 2 Tage |
| Review/Approval-Workflow | 1 Tag |

### Phase 3: ADR-Integration

| Task | Aufwand |
| ---- | ------- |
| ADR-Template-Generator aus Business Case | 1 Tag |
| Sphinx-Export (automatische Dokumentation) | 1 Tag |
| Traceability-Links (BC → UC → ADR → Code) | 1 Tag |

---

## 4. Rejected Alternatives

### A: Jira / Linear / Notion

- Externe Tools schaffen Medienbrüche
- Keine MCP-Integration
- Keine AI-gestützte Kategorisierung
- Vendor Lock-in

### B: Reines Datei-basiertes System (Markdown in Git)

- Keine strukturierte Suche und Filterung
- Kein Status-Workflow
- Keine AI-Interaktion
- Merge-Konflikte bei gleichzeitiger Bearbeitung

### C: Eigenständiges Repo für DDL

- Overhead für kleines System
- Besser als App in bestehendem Django-Projekt
- Kann bei Bedarf später extrahiert werden

### D: Revival von registry_mcp (ADR-015)

- Dead Code, nie deployed
- Zu eng auf Tool-Registry fokussiert
- DDL hat breiteren Scope (Anforderungen → Code)
- ADR-010 superseded ADR-015 bereits

---

## 5. Consequences

### Positive

- **Strukturierte Anforderungserfassung** statt Ad-hoc-Meetings
- **AI-Unterstützung** reduziert Erfassungszeit von Stunden auf Minuten
- **Vollständige Traceability** von Idee bis Code
- **MCP-First**: Entwickler können BCs direkt aus der IDE erstellen
- **Platform-konform**: Django + HTMX + ADR-010 ToolSpecs

### Negative

- **Initialer Entwicklungsaufwand**: ~10 Tage für MVP
- **AI-Abhängigkeit**: Qualität der Fragen hängt von LLM ab
- **Adoption**: Team muss neuen Prozess annehmen
- **Maintenance**: Prompt-Templates müssen gepflegt werden

### Neutral

- Bestehende ADRs in `platform/docs/adr/` bleiben als Dateien
- DDL-generierte ADRs können in Dateien exportiert werden
- System ist optional — kein Zwang, alle BCs über DDL zu erstellen

---

## 6. Open Questions

| Nr | Frage | Priorität |
| -- | ----- | --------- |
| Q1 | In welchem Django-Projekt wird DDL implementiert? | Hoch |
| Q2 | Welches LLM (llm_mcp, direkt Anthropic/OpenAI)? | Hoch |
| Q3 | Multi-Tenancy für DDL nötig? | Mittel |
| Q4 | Brauchen BCs eine Versions-History? | Mittel |
| Q5 | Integration mit GitHub Issues/PRs? | Niedrig |

---

## 7. Changelog

| Datum | Änderung |
| ----- | -------- |
| 2026-02-13 | Initial: ADR-032 proposed based on DDL Concept Papers |
