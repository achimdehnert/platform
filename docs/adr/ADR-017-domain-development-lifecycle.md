# ADR-017: Domain Development Lifecycle (DDL)

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-04 |
| **Author** | Platform Architecture Team |
| **Scope** | core, governance |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-015 (Governance), ADR-012 (MCP Quality), ADR-014 (AI-Native Teams) |

---

## 1. Executive Summary

Das **Domain Development Lifecycle (DDL)** System ist eine integrierte Lösung zur strukturierten Erfassung, Verwaltung und Dokumentation von Geschäftsanforderungen innerhalb der BF Agent Platform.

### Kernidee

```
Freitext-Idee → Strukturierter Business Case → Use Cases → ADRs → Code
```

Ein Entwickler oder Product Owner beschreibt eine Anforderung in natürlicher Sprache. Das System führt einen AI-gestützten Dialog (Inception), um alle relevanten Informationen zu extrahieren und strukturiert zu speichern. Daraus werden automatisch Use Cases abgeleitet und bei Bedarf Architecture Decision Records (ADRs) erstellt.

### Hauptvorteile

| Vorteil | Beschreibung |
|---------|--------------|
| **Konsistenz** | Einheitliche Struktur für alle Anforderungen |
| **Nachvollziehbarkeit** | Vollständige Historie von Idee bis Code |
| **Effizienz** | AI-gestützte Extraktion reduziert manuellen Aufwand |
| **Integration** | Nahtlose Einbindung in bestehende Entwicklungsprozesse |
| **Dokumentation** | Automatische Sphinx-Dokumentation aus der Datenbank |

### Zielgruppen

| Rolle | Kanal | Hauptaktivitäten |
|-------|-------|------------------|
| **Entwickler** | MCP (Windsurf/Claude) | Business Cases über IDE erstellen |
| **Product Owner** | Web-UI | Review und Approval |
| **Architekten** | Web-UI + MCP | ADR-Erstellung und -Verwaltung |
| **Stakeholder** | Web-UI | Dashboard und Reporting |

---

## 2. Context

### 2.1 Problem Statement

| Problem | Impact | Häufigkeit |
|---------|--------|------------|
| Anforderungen in Slack/Chat verloren | Wissen geht verloren, keine Rückverfolgung | Täglich |
| Unstrukturierte Dokumentation | Jedes Projekt dokumentiert anders | Ständig |
| Manuelle Überführung (Slack → Ticket → Code) | Informationsverlust bei jeder Übergabe | Täglich |
| Fehlende Governance | Keine standardisierten Approval-Workflows | Häufig |
| Architekturentscheidungen nicht dokumentiert | Entscheidungsgründe nicht nachvollziehbar | Wöchentlich |
| README-Dateien veralten schnell | Dokumentation weicht von Code ab | Ständig |

### 2.2 Auswirkungen (IST-Zustand)

```
Zeit für Anforderungserfassung:     ████████████░░░░  ~3-5 Std/Feature
Informationsverlust:                ████████░░░░░░░░  ~40%
Dokumentationsaufwand:              ██████████████░░  ~6 Std/Feature
Nachvollziehbarkeit:                ████░░░░░░░░░░░░  ~25%
```

### 2.3 Vision

> **"Von der Idee zum Code – strukturiert, nachvollziehbar, automatisiert."**

### 2.4 Strategische Ziele

| # | Ziel | Messung | Target |
|---|------|---------|--------|
| Z1 | Strukturierte Erfassung aller Anforderungen | % Anforderungen im System | 100% |
| Z2 | Reduzierter Dokumentationsaufwand | Stunden pro Feature | -60% |
| Z3 | Vollständige Nachvollziehbarkeit | BC → Code Traceability | 100% |
| Z4 | Automatisierte Dokumentation | Manueller Doku-Aufwand | -80% |
| Z5 | Standardisierte Governance | % mit Approval-Workflow | 100% |

### 2.5 Nicht-Ziele (Out of Scope)

- Ersatz für Projektmanagement-Tools (Jira, Linear)
- Vollautomatische Code-Generierung
- Ersatz für direkte Kommunikation im Team
- Micromanagement von Entwicklungsaufgaben

---

## 3. Decision

### 3.1 Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOMAIN DEVELOPMENT LIFECYCLE                          │
│                           SYSTEM ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        PRESENTATION LAYER                            │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐   │   │
│  │   │  MCP Server │    │   Web UI    │    │   Sphinx Docs       │   │   │
│  │   │  (Windsurf) │    │  (Django +  │    │  (GitHub Pages)     │   │   │
│  │   │             │    │   HTMX)     │    │                     │   │   │
│  │   │ • inception │    │ • Dashboard │    │ • Business Cases    │   │   │
│  │   │ • registry  │    │ • BC/UC/ADR │    │ • Use Cases         │   │   │
│  │   │             │    │ • Review    │    │ • ADRs              │   │   │
│  │   └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘   │   │
│  │          │                  │                      │              │   │
│  └──────────┼──────────────────┼──────────────────────┼──────────────┘   │
│             │                  │                      │                  │
│  ┌──────────┼──────────────────┼──────────────────────┼──────────────┐   │
│  │          │      SERVICE LAYER                      │              │   │
│  ├──────────┼──────────────────┼──────────────────────┼──────────────┤   │
│  │          ▼                  ▼                      ▼              │   │
│  │   ┌─────────────────────────────────────────────────────────┐    │   │
│  │   │                     SHARED SERVICES                      │    │   │
│  │   ├─────────────────────────────────────────────────────────┤    │   │
│  │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │   │
│  │   │  │ Inception    │  │ Business     │  │ Lookup       │  │    │   │
│  │   │  │ Service      │  │ CaseService  │  │ Service      │  │    │   │
│  │   │  │ • Dialog     │  │ • CRUD       │  │ • Categories │  │    │   │
│  │   │  │ • Extraction │  │ • Search     │  │ • Status     │  │    │   │
│  │   │  │ • Derivation │  │ • Transition │  │ • Priorities │  │    │   │
│  │   │  └──────────────┘  └──────────────┘  └──────────────┘  │    │   │
│  │   │                                                         │    │   │
│  │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │   │
│  │   │  │ UseCase      │  │ ADR          │  │ Export       │  │    │   │
│  │   │  │ Service      │  │ Service      │  │ Service      │  │    │   │
│  │   │  │ • Flows      │  │ • Accept     │  │ • RST Gen    │  │    │   │
│  │   │  │ • Dependencies│ │ • Supersede  │  │ • Sphinx     │  │    │   │
│  │   │  │ • Estimation │  │ • Link UC    │  │ • PDF        │  │    │   │
│  │   │  └──────────────┘  └──────────────┘  └──────────────┘  │    │   │
│  │   └─────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                           DATA LAYER                              │   │
│  │                     PostgreSQL (schema: platform)                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Datenmodell

#### 3.2.1 Lookup-Tabellen (lkp_*)

| Tabelle | Zweck | Beispiel-Werte |
|---------|-------|----------------|
| `lkp_domain` | Lookup-Domänen | bc_status, uc_priority, adr_status |
| `lkp_choice` | Lookup-Werte | draft, approved, high, critical |

#### 3.2.2 Domain-Tabellen (dom_*)

| Tabelle | Zweck | Kardinalität |
|---------|-------|--------------|
| `dom_business_case` | Business Cases | ~100/Jahr |
| `dom_use_case` | Use Cases | ~5 pro BC |
| `dom_adr` | Architecture Decision Records | ~20/Jahr |
| `dom_conversation` | Inception Dialog | ~10 pro BC |
| `dom_adr_use_case` | ADR ↔ UC Verknüpfung | N:M |
| `dom_review` | Reviews/Approvals | ~2 pro BC |
| `dom_status_history` | Audit Trail | Unbegrenzt |

#### 3.2.3 Entity-Relationship

```
┌─────────────────┐         ┌─────────────────────────────┐
│   lkp_domain    │         │      dom_business_case      │
├─────────────────┤         ├─────────────────────────────┤
│ PK id           │◄────────┤ PK id                       │
│    code         │         │    code (unique, BC-XXX)    │
│    name         │         │ FK category_id              │
└────────┬────────┘         │ FK status_id                │
         │ 1:N              │    title                    │
         ▼                  │    problem_statement        │
┌─────────────────┐         │    success_criteria (JSON)  │
│   lkp_choice    │         │    risks (JSON)             │
├─────────────────┤         └──────────────┬──────────────┘
│ PK id           │                        │
│ FK domain_id    │           ┌────────────┼────────────┐
│    code         │           │            │            │
│    name         │           ▼            ▼            ▼
│    metadata     │    ┌──────────┐  ┌──────────┐  ┌────────────┐
└─────────────────┘    │dom_use   │  │ dom_adr  │  │dom_conver- │
                       │_case     │  │          │  │sation      │
                       └──────────┘  └──────────┘  └────────────┘
```

### 3.3 Komponenten

#### 3.3.1 MCP Server: inception_mcp

**Tools:**

| Tool | Beschreibung | Returns |
|------|--------------|---------|
| `start_business_case` | Analysiert Freitext, erstellt BC-Draft | session_id, bc_code, first_question |
| `answer_question` | Extrahiert Daten, aktualisiert BC | next_question \| summary |
| `finalize_business_case` | Finalisiert BC, leitet Use Cases ab | bc_code, derived_use_cases[] |
| `list_business_cases` | Filterbare BC-Liste | business_cases[] |
| `get_business_case` | BC-Details abrufen | business_case |
| `submit_for_review` | BC zur Review einreichen | success, message |
| `detail_use_case` | UC-Details erweitern | use_case |

#### 3.3.2 Web-UI: governance_app

**URL-Struktur:**

```
/governance/                          Dashboard
/governance/business-cases/           BC Liste
/governance/business-cases/create/    BC Erstellen
/governance/business-cases/{code}/    BC Detail
/governance/use-cases/                UC Liste
/governance/use-cases/{code}/         UC Detail + Flow-Editor
/governance/adrs/                     ADR Liste
/governance/adrs/{code}/              ADR Detail
```

#### 3.3.3 Sphinx Extension: db_docs

**Directives:**

```rst
.. db-business-case:: BC-001
   Lädt BC aus DB und generiert RST

.. db-use-case:: UC-001
   Lädt UC aus DB mit Flows

.. db-adr:: ADR-001
   Lädt ADR mit Alternativen-Tabelle

.. db-business-case-list::
   :status: approved
   Generiert Tabelle mit Links
```

### 3.4 Workflow

#### 3.4.1 Inception Dialog (Phase 1)

```
┌──────────────────────────────────────────────────────────────────┐
│  INCEPTION DIALOG                                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  👤 User: "Ich brauche eine Reisekostenabrechnung mit           │
│           Beleg-Upload und automatischer OCR-Erkennung"          │
│                                                                  │
│  🤖 Agent: Ich habe verstanden:                                  │
│           • Titel: Reisekostenabrechnung                        │
│           • Kategorie: Neue Domain                               │
│           • Keywords: Beleg-Upload, OCR                          │
│                                                                  │
│           Frage 1/8: Wer ist die primäre Zielgruppe?            │
│                                                                  │
│  👤 User: "Außendienstmitarbeiter und deren Vorgesetzte"        │
│                                                                  │
│  🤖 Agent: ✓ Gespeichert. Frage 2/8: ...                        │
│                                                                  │
│  [... weitere Fragen ...]                                        │
│                                                                  │
│  🤖 Agent: ✅ Business Case BC-042 erstellt.                     │
│           4 Use Cases wurden automatisch abgeleitet.            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.4.2 Approval Workflow (Phase 2)

```
Draft ──────► Submitted ──────► In Review ──────► Approved
  │              │                  │                │
  │              │                  ▼                │
  │              │           ┌──────────┐            │
  │              └──────────►│ Rejected │            │
  │                          └────┬─────┘            │
  │                               │                  │
  ◄───────────────────────────────┘                  │
             (Überarbeitung)                         ▼
                                               In Progress
                                                    │
                                                    ▼
                                               Completed
```

### 3.5 Lookup-Domänen

```
bc_category                    bc_status
────────────                   ─────────
• neue_domain                  • draft
• integration                  • submitted
• optimierung                  • in_review
• erweiterung                  • approved
• produktion                   • rejected
• bugfix                       • in_progress
                               • completed
                               • archived

uc_status                      uc_priority
─────────                      ───────────
• draft                        • critical
• detailed                     • high
• ready                        • medium
• in_progress                  • low
• blocked                      • backlog
• testing
• done                         uc_complexity
                               ─────────────
adr_status                     • trivial (1 SP)
──────────                     • simple (2 SP)
• proposed                     • moderate (3 SP)
• accepted                     • complex (5 SP)
• rejected                     • very_complex (8 SP)
• deprecated                   • epic (13 SP)
• superseded
```

---

## 4. Consequences

### 4.1 Positive

| Bereich | Auswirkung |
|---------|------------|
| **Konsistenz** | Alle Anforderungen folgen einheitlicher Struktur |
| **Nachvollziehbarkeit** | Vollständiger Audit Trail von Idee bis Code |
| **Effizienz** | -60% Dokumentationsaufwand durch AI-gestützte Extraktion |
| **Qualität** | Standardisierte Review-Prozesse |
| **Integration** | Nahtlose Einbindung in Governance-System (ADR-015) |

### 4.2 Negative / Trade-offs

| Trade-off | Mitigation |
|-----------|------------|
| Initialer Implementierungsaufwand | Modularer Rollout in Phasen |
| Lernkurve für Entwickler | MCP-Integration macht Adoption einfach |
| Abhängigkeit von LLM für Inception | Fallback auf manuelle Erfassung |
| Zusätzliche DB-Tabellen | Klare Schema-Trennung (platform.*) |

### 4.3 Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LLM-Kosten bei hoher Nutzung | Mittel | Mittel | Token-Budgets, Caching |
| Adoption-Widerstand | Niedrig | Hoch | Einfache MCP-Integration |
| Datenqualität bei schlechtem Input | Mittel | Mittel | Validation Rules |

---

## 5. Implementation

### 5.1 Phasen-Roadmap

| Phase | Umfang | Timeline | Status |
|-------|--------|----------|--------|
| **P1: Foundation** | Datenmodell, Django Models, Admin | Woche 1-2 | 🔲 Geplant |
| **P2: Services** | BusinessCaseService, LookupService | Woche 3-4 | 🔲 Geplant |
| **P3: MCP Server** | inception_mcp mit Inception Dialog | Woche 5-6 | 🔲 Geplant |
| **P4: Web-UI** | governance_app mit HTMX | Woche 7-8 | 🔲 Geplant |
| **P5: Sphinx** | db_docs Extension | Woche 9 | 🔲 Geplant |
| **P6: GitHub Actions** | Automated Docs Build | Woche 10 | 🔲 Geplant |

### 5.2 Technologie-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Backend | Django | 5.x |
| Database | PostgreSQL | 15+ |
| Frontend | HTMX + Alpine.js | 2.x |
| MCP Server | Python MCP SDK | Latest |
| LLM | Claude API (via LLM Gateway) | 3.x |
| Documentation | Sphinx | 7.x |
| CI/CD | GitHub Actions | - |

### 5.3 Dateien/Module

```
apps/
├── governance/                    # Django App
│   ├── models/
│   │   ├── lookups.py            # lkp_domain, lkp_choice
│   │   ├── business_case.py      # dom_business_case
│   │   ├── use_case.py           # dom_use_case
│   │   ├── adr.py                # dom_adr
│   │   └── conversation.py       # dom_conversation
│   ├── services/
│   │   ├── inception_service.py  # AI Dialog
│   │   ├── business_case_service.py
│   │   ├── use_case_service.py
│   │   ├── adr_service.py
│   │   └── lookup_service.py
│   ├── views/
│   │   ├── dashboard.py
│   │   ├── business_case.py
│   │   ├── use_case.py
│   │   └── adr.py
│   ├── templates/governance/
│   └── urls.py
│
mcp-servers/
├── inception-mcp/                # MCP Server
│   ├── server.py
│   ├── tools/
│   │   ├── business_case.py
│   │   ├── use_case.py
│   │   └── inception.py
│   └── pyproject.toml
│
docs/
├── _extensions/
│   └── db_docs.py               # Sphinx Extension
└── governance/
    ├── business_cases.rst
    ├── use_cases.rst
    └── adrs.rst
```

---

## 6. References

### 6.1 Related ADRs

- **ADR-015**: Platform Governance System (Registry, Enforcement)
- **ADR-012**: MCP Quality Standards
- **ADR-014**: AI-Native Development Teams

### 6.2 Input Documents

- `docs/adr/inputs/ddl-concept-part1-overview.md`
- `docs/adr/inputs/ddl-concept-part2-architecture.md`
- `docs/adr/inputs/ddl-concept-part3-workflow.md`
- `docs/adr/inputs/ddl-step-02-django-models.py`
- `docs/adr/inputs/ddl-step-03-services.py`
- `docs/adr/inputs/ddl-step-04-inception-mcp.py`
- `docs/adr/inputs/ddl-step-05-web-views.py`
- `docs/adr/inputs/ddl-step-06-sphinx-extension.py`
- `docs/adr/inputs/ddl-step-07-github-actions.yml`

### 6.3 External References

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [HTMX](https://htmx.org/)

---

## 7. Appendix

### A. Inception Questions Template

Die Standard-Fragen für den Inception-Dialog:

1. **Zielgruppe**: Wer ist die primäre Zielgruppe?
2. **Erfolgskriterien**: Was sind die messbaren Erfolgskriterien?
3. **Scope**: Was gehört explizit NICHT dazu (Out of Scope)?
4. **Abhängigkeiten**: Welche bestehenden Systeme sind betroffen?
5. **Risiken**: Welche Risiken siehst du?
6. **Timeline**: Gibt es zeitliche Constraints?
7. **Architektur**: Sind Architekturentscheidungen erforderlich?
8. **Priorität**: Wie kritisch ist dieses Feature?

### B. Business Case Template (JSON)

```json
{
  "code": "BC-042",
  "title": "Reisekostenabrechnung",
  "category": "neue_domain",
  "status": "draft",
  "problem_statement": "...",
  "target_audience": "Außendienstmitarbeiter",
  "expected_benefits": ["80% Zeitersparnis", "< 5% Fehlerquote"],
  "scope": "...",
  "out_of_scope": ["Integration mit SAP"],
  "success_criteria": [
    {"metric": "Bearbeitungszeit", "target": "< 5 Min", "unit": "Minuten"}
  ],
  "assumptions": ["OCR-API verfügbar"],
  "risks": [
    {"description": "OCR-Qualität", "probability": "medium", "impact": "high"}
  ],
  "architecture_basis": {
    "requires_adr": true,
    "reason": "Neue Domain"
  }
}
```

---

*Erstellt: 2026-02-04 | Letzte Änderung: 2026-02-04*
