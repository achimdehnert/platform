# Domain Development Lifecycle (DDL)

## Konzeptpapier v1.0

**Projekt:** BF Agent Platform - Governance Extension  
**Datum:** Februar 2025  
**Status:** Konzept / In Entwicklung  
**Autor:** Platform Architecture Team

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Problemstellung](#2-problemstellung)
3. [Vision & Ziele](#3-vision--ziele)
4. [Use Cases](#4-use-cases)
5. [Systemarchitektur](#5-systemarchitektur)
6. [Datenmodell](#6-datenmodell)
7. [Komponenten](#7-komponenten)
8. [Prozess-Workflow](#8-prozess-workflow)
9. [Technologie-Stack](#9-technologie-stack)
10. [Implementierungs-Roadmap](#10-implementierungs-roadmap)
11. [Beispiel-Szenario](#11-beispiel-szenario)

---

## 1. Executive Summary

Das **Domain Development Lifecycle (DDL)** System ist eine integrierte Lösung zur strukturierten Erfassung, Verwaltung und Dokumentation von Geschäftsanforderungen innerhalb der BF Agent Platform.

### Kernidee

```
Freitext-Idee → Strukturierter Business Case → Use Cases → ADRs → Code
```

Ein Entwickler oder Product Owner beschreibt eine Anforderung in natürlicher Sprache. Das System führt einen AI-gestützten Dialog, um alle relevanten Informationen zu extrahieren und strukturiert zu speichern. Daraus werden automatisch Use Cases abgeleitet und bei Bedarf Architecture Decision Records (ADRs) erstellt.

### Hauptvorteile

| Vorteil | Beschreibung |
|---------|--------------|
| **Konsistenz** | Einheitliche Struktur für alle Anforderungen |
| **Nachvollziehbarkeit** | Vollständige Historie von Idee bis Code |
| **Effizienz** | AI-gestützte Extraktion reduziert manuellen Aufwand |
| **Integration** | Nahtlose Einbindung in bestehende Entwicklungsprozesse |
| **Dokumentation** | Automatische Sphinx-Dokumentation aus der Datenbank |

### Zielgruppen

- **Entwickler**: Business Cases über IDE/MCP erstellen
- **Product Owner**: Review und Approval über Web-UI
- **Architekten**: ADR-Erstellung und -Verwaltung
- **Stakeholder**: Dashboard und Reporting

---

## 2. Problemstellung

### 2.1 Aktuelle Situation

In der aktuellen Entwicklungspraxis existieren mehrere Herausforderungen:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AKTUELLE PROBLEME                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📝 Anforderungen        │  🔀 Prozess           │  📚 Doku    │
│  ─────────────────       │  ──────────           │  ────────   │
│  • In Slack verloren     │  • Kein Standard      │  • Veraltet │
│  • Unstrukturiert        │  • Wissen in Köpfen   │  • Verteilt │
│  • Keine Rückverfolgung  │  • Manuelle Übergaben │  • Inkonsist│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Konkrete Schmerzpunkte

1. **Verlorenes Wissen**
   - Anforderungen werden in Chats besprochen und nie dokumentiert
   - Entscheidungsgründe sind nicht nachvollziehbar
   - Bei Personalwechsel geht Kontext verloren

2. **Inkonsistente Dokumentation**
   - Jedes Projekt dokumentiert anders
   - README-Dateien veralten schnell
   - Keine Verbindung zwischen Anforderung und Code

3. **Manuelle Überführung**
   - Von Slack zu Ticket zu Code: mehrfache manuelle Übertragung
   - Informationsverlust bei jeder Übergabe
   - Zeitaufwändig und fehleranfällig

4. **Fehlende Governance**
   - Keine standardisierten Approval-Workflows
   - Architekturentscheidungen nicht dokumentiert
   - Keine Übersicht über laufende Vorhaben

### 2.3 Auswirkungen

```
Zeit für Anforderungserfassung:     ████████████░░░░  ~3-5 Std/Feature
Informationsverlust:                ████████░░░░░░░░  ~40%
Dokumentationsaufwand:              ██████████████░░  ~6 Std/Feature
Nachvollziehbarkeit:                ████░░░░░░░░░░░░  ~25%
```

---

## 3. Vision & Ziele

### 3.1 Vision

> **"Von der Idee zum Code – strukturiert, nachvollziehbar, automatisiert."**

Das DDL-System transformiert unstrukturierte Anforderungen in verwaltbare, dokumentierte und nachvollziehbare Entwicklungsartefakte.

### 3.2 Zielbild

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ZIELBILD DDL                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   Entwickler                    Product Owner           Stakeholder     │
│       │                              │                       │          │
│       ▼                              ▼                       ▼          │
│   ┌───────────┐               ┌───────────┐           ┌───────────┐    │
│   │ Windsurf  │               │  Web-UI   │           │ Dashboard │    │
│   │ + MCP     │               │  Review   │           │ Reports   │    │
│   └─────┬─────┘               └─────┬─────┘           └─────┬─────┘    │
│         │                           │                       │          │
│         └───────────────┬───────────┴───────────────────────┘          │
│                         │                                               │
│                         ▼                                               │
│              ┌─────────────────────┐                                   │
│              │    PostgreSQL       │                                   │
│              │  ┌───────────────┐  │                                   │
│              │  │ Business Cases│  │                                   │
│              │  │ Use Cases     │  │                                   │
│              │  │ ADRs          │  │                                   │
│              │  │ Conversations │  │                                   │
│              │  └───────────────┘  │                                   │
│              └──────────┬──────────┘                                   │
│                         │                                               │
│                         ▼                                               │
│              ┌─────────────────────┐                                   │
│              │  Sphinx + GitHub    │                                   │
│              │  Pages Dokumentation│                                   │
│              └─────────────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Strategische Ziele

| # | Ziel | Messung | Target |
|---|------|---------|--------|
| Z1 | Strukturierte Erfassung aller Anforderungen | % Anforderungen im System | 100% |
| Z2 | Reduzierter Dokumentationsaufwand | Stunden pro Feature | -60% |
| Z3 | Vollständige Nachvollziehbarkeit | BC → Code Traceability | 100% |
| Z4 | Automatisierte Dokumentation | Manueller Doku-Aufwand | -80% |
| Z5 | Standardisierte Governance | % mit Approval-Workflow | 100% |

### 3.4 Nicht-Ziele (Out of Scope)

- Ersatz für Projektmanagement-Tools (Jira, Linear)
- Vollautomatische Code-Generierung
- Ersatz für direkte Kommunikation im Team
- Micromanagement von Entwicklungsaufgaben

---

## 4. Use Cases

### 4.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USE CASE ÜBERSICHT                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   INCEPTION     │    │   MANAGEMENT    │    │  DOCUMENTATION  │     │
│  ├─────────────────┤    ├─────────────────┤    ├─────────────────┤     │
│  │ UC-01: BC       │    │ UC-04: Review   │    │ UC-07: Export   │     │
│  │       erstellen │    │       & Approve │    │       Sphinx    │     │
│  │ UC-02: UC       │    │ UC-05: Status   │    │ UC-08: API      │     │
│  │       ableiten  │    │       Tracking  │    │       Doku      │     │
│  │ UC-03: ADR      │    │ UC-06: Dashboard│    │ UC-09: Search   │     │
│  │       erstellen │    │       & Reports │    │       & Query   │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 UC-01: Business Case erstellen (Inception)

**Akteur:** Entwickler, Product Owner  
**Trigger:** Neue Anforderung / Idee  
**Kanal:** MCP Server (Windsurf/Claude) oder Web-UI

**Hauptablauf:**

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
│  🤖 Agent: ✓ Gespeichert.                                        │
│           Frage 2/8: Was sind die messbaren Erfolgskriterien?   │
│                                                                  │
│  👤 User: "80% Zeitersparnis bei der Abrechnung,                │
│           Fehlerquote unter 5%"                                  │
│                                                                  │
│  🤖 Agent: ✓ Gespeichert.                                        │
│           Frage 3/8: ...                                         │
│                                                                  │
│  [... weitere Fragen ...]                                        │
│                                                                  │
│  🤖 Agent: ✅ Business Case BC-042 erstellt.                     │
│           4 Use Cases wurden automatisch abgeleitet:            │
│           • UC-087: Beleg hochladen                             │
│           • UC-088: OCR-Erkennung durchführen                   │
│           • UC-089: Abrechnung erstellen                        │
│           • UC-090: Abrechnung genehmigen                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Nachbedingungen:**
- Business Case in DB gespeichert (Status: Draft)
- Conversation History vollständig protokolliert
- Use Cases automatisch abgeleitet
- Notification an Reviewer (optional)

### 4.3 UC-02: Use Cases detaillieren

**Akteur:** Entwickler, Architekt  
**Vorbedingung:** Business Case existiert mit abgeleiteten Use Cases

**Hauptablauf:**

1. Entwickler öffnet Use Case im Flow-Editor
2. Definiert Hauptablauf (Schritt für Schritt)
3. Fügt alternative Abläufe hinzu
4. Definiert Vor- und Nachbedingungen
5. Ergänzt technische Hinweise und API-Endpoints
6. Speichert → Status wechselt zu "Detailliert"

### 4.4 UC-03: ADR erstellen

**Akteur:** Architekt  
**Trigger:** Business Case erfordert Architekturentscheidung

**Hauptablauf:**

1. System erkennt: Kategorie "Neue Domain" → ADR erforderlich
2. Architekt erstellt ADR mit:
   - Kontext (warum diese Entscheidung?)
   - Betrachtete Alternativen (mit Pros/Cons)
   - Entscheidung (was wurde gewählt?)
   - Konsequenzen (Auswirkungen)
3. ADR wird zur Review eingereicht
4. Nach Approval: Status "Accepted"

### 4.5 UC-04: Review & Approval

**Akteur:** Product Owner, Tech Lead  
**Kanal:** Web-UI

```
┌──────────────────────────────────────────────────────────────────┐
│  APPROVAL WORKFLOW                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│     Draft ──────► Submitted ──────► In Review ──────► Approved  │
│       │              │                  │                │       │
│       │              │                  ▼                │       │
│       │              │           ┌──────────┐            │       │
│       │              └──────────►│ Rejected │            │       │
│       │                          └────┬─────┘            │       │
│       │                               │                  │       │
│       ◄───────────────────────────────┘                  │       │
│                    (Überarbeitung)                       │       │
│                                                          │       │
│                                                          ▼       │
│                                                    In Progress   │
│                                                          │       │
│                                                          ▼       │
│                                                     Completed    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 4.6 UC-05: Dashboard & Reporting

**Akteur:** Stakeholder, Management  
**Kanal:** Web-UI

**Verfügbare Ansichten:**

| Ansicht | Inhalt |
|---------|--------|
| Status-Übersicht | Anzahl BC nach Status (Draft, Submitted, Approved, ...) |
| Pending Reviews | Liste der zu prüfenden Business Cases |
| Team-Fortschritt | Use Cases pro Team und Status |
| Timeline | Zeitlicher Verlauf der Fertigstellung |
| Metriken | Durchlaufzeiten, Completion Rate |

### 4.7 UC-06: Dokumentation generieren

**Akteur:** System (automatisch)  
**Trigger:** Scheduled (alle 6h) oder Push auf main

**Ablauf:**

1. GitHub Action wird getriggert
2. Export-Script lädt alle BC, UC, ADR aus DB
3. Generiert RST-Dateien
4. Sphinx baut HTML-Dokumentation
5. Deploy auf GitHub Pages

**Ergebnis:** Aktuelle, konsistente Dokumentation unter `docs.platform.example.com`

---

*[Fortsetzung in Teil 2: Architektur und Datenmodell]*
---

## 5. Systemarchitektur

### 5.1 Architektur-Übersicht

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
│  │   │             │    │ • Reports   │    │ • API Reference     │   │   │
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
│  │   │                                                         │    │   │
│  │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │   │
│  │   │  │ Inception    │  │ Business     │  │ Lookup       │  │    │   │
│  │   │  │ Service      │  │ CaseService  │  │ Service      │  │    │   │
│  │   │  │              │  │              │  │              │  │    │   │
│  │   │  │ • Dialog     │  │ • CRUD       │  │ • Categories │  │    │   │
│  │   │  │ • Extraction │  │ • Search     │  │ • Status     │  │    │   │
│  │   │  │ • Derivation │  │ • Transition │  │ • Priorities │  │    │   │
│  │   │  └──────────────┘  └──────────────┘  └──────────────┘  │    │   │
│  │   │                                                         │    │   │
│  │   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │   │
│  │   │  │ UseCase      │  │ ADR          │  │ Export       │  │    │   │
│  │   │  │ Service      │  │ Service      │  │ Service      │  │    │   │
│  │   │  │              │  │              │  │              │  │    │   │
│  │   │  │ • Flows      │  │ • Accept     │  │ • RST Gen    │  │    │   │
│  │   │  │ • Dependencies│  │ • Supersede │  │ • Sphinx     │  │    │   │
│  │   │  │ • Estimation │  │ • Link UC    │  │ • PDF        │  │    │   │
│  │   │  └──────────────┘  └──────────────┘  └──────────────┘  │    │   │
│  │   │                                                         │    │   │
│  │   └─────────────────────────────────────────────────────────┘    │   │
│  │                              │                                    │   │
│  └──────────────────────────────┼────────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────┼────────────────────────────────────┐   │
│  │                    DATA LAYER│                                    │   │
│  ├──────────────────────────────┼────────────────────────────────────┤   │
│  │                              ▼                                    │   │
│  │   ┌───────────────────────────────────────────────────────────┐  │   │
│  │   │                    PostgreSQL                              │  │   │
│  │   │                   Schema: platform                         │  │   │
│  │   ├───────────────────────────────────────────────────────────┤  │   │
│  │   │                                                           │  │   │
│  │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │   │
│  │   │  │ lkp_domain  │  │ lkp_choice  │  │ dom_business│       │  │   │
│  │   │  │             │◄─┤             │◄─┤ _case       │       │  │   │
│  │   │  └─────────────┘  └─────────────┘  └──────┬──────┘       │  │   │
│  │   │                                           │              │  │   │
│  │   │                          ┌────────────────┼───────────┐  │  │   │
│  │   │                          │                │           │  │  │   │
│  │   │                          ▼                ▼           ▼  │  │   │
│  │   │                   ┌───────────┐    ┌───────────┐  ┌──────┴┐│  │   │
│  │   │                   │dom_use    │    │ dom_adr   │  │dom_   ││  │   │
│  │   │                   │_case      │◄───┤           │  │conver-││  │   │
│  │   │                   └───────────┘    └───────────┘  │sation ││  │   │
│  │   │                                                   └───────┘│  │   │
│  │   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │   │
│  │   │  │ dom_review  │  │dom_status   │  │dom_adr     │       │  │   │
│  │   │  │             │  │_history     │  │_use_case   │       │  │   │
│  │   │  └─────────────┘  └─────────────┘  └─────────────┘       │  │   │
│  │   │                                                           │  │   │
│  │   └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Komponenten-Interaktion

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     KOMPONENTEN-INTERAKTION                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                          ┌─────────────────┐                           │
│                          │   LLM Gateway   │                           │
│                          │  (Claude API)   │                           │
│                          └────────┬────────┘                           │
│                                   │                                    │
│                                   │ Extraction                         │
│                                   │ Derivation                         │
│                                   ▼                                    │
│  ┌──────────────┐         ┌─────────────────┐         ┌────────────┐  │
│  │              │  MCP    │                 │  HTTP   │            │  │
│  │   Windsurf   │◄───────►│ Inception MCP   │◄───────►│  Web UI    │  │
│  │   Claude     │  Tools  │    Server       │  API    │  (Django)  │  │
│  │              │         │                 │         │            │  │
│  └──────────────┘         └────────┬────────┘         └─────┬──────┘  │
│                                    │                        │         │
│                                    │ Service Calls          │         │
│                                    ▼                        ▼         │
│                           ┌─────────────────────────────────────┐     │
│                           │          SERVICE LAYER              │     │
│                           │                                     │     │
│                           │  InceptionService                   │     │
│                           │  BusinessCaseService                │     │
│                           │  UseCaseService                     │     │
│                           │  ADRService                         │     │
│                           │  LookupService                      │     │
│                           │  ExportService                      │     │
│                           │                                     │     │
│                           └─────────────────┬───────────────────┘     │
│                                             │                         │
│                                             │ ORM                     │
│                                             ▼                         │
│                           ┌─────────────────────────────────────┐     │
│                           │           PostgreSQL                │     │
│                           │                                     │     │
│                           │  dom_business_case                  │     │
│                           │  dom_use_case                       │     │
│                           │  dom_adr                            │     │
│                           │  dom_conversation                   │     │
│                           │  dom_review                         │     │
│                           │  dom_status_history                 │     │
│                           │  lkp_domain / lkp_choice            │     │
│                           │                                     │     │
│                           └─────────────────────────────────────┘     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Deployment-Architektur

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      HETZNER CLOUD                               │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │   │
│  │   │   Traefik   │    │   Django    │    │ PostgreSQL  │        │   │
│  │   │   Reverse   │───►│   App +     │───►│   15+       │        │   │
│  │   │   Proxy     │    │   Gunicorn  │    │             │        │   │
│  │   └─────────────┘    └─────────────┘    └─────────────┘        │   │
│  │                             │                   ▲               │   │
│  │                             │                   │               │   │
│  │   ┌─────────────┐           │                   │               │   │
│  │   │ Inception   │───────────┴───────────────────┘               │   │
│  │   │ MCP Server  │                                               │   │
│  │   └─────────────┘                                               │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      GITHUB                                      │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │   │
│  │   │  Repository │───►│   Actions   │───►│   Pages     │        │   │
│  │   │  (Code)     │    │  (CI/CD)    │    │   (Docs)    │        │   │
│  │   └─────────────┘    └─────────────┘    └─────────────┘        │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      DEVELOPER WORKSTATION                       │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │                                                                 │   │
│  │   ┌─────────────┐                                               │   │
│  │   │  Windsurf   │                                               │   │
│  │   │  + Claude   │◄──── MCP Protocol ────► Inception MCP         │   │
│  │   │  Desktop    │                                               │   │
│  │   └─────────────┘                                               │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Datenmodell

### 6.1 Entity-Relationship-Diagramm

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY RELATIONSHIP DIAGRAM                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────┐                                                       │
│   │   lkp_domain    │                                                       │
│   ├─────────────────┤                                                       │
│   │ PK id           │                                                       │
│   │    code         │◄─────────────────────────────────────────┐           │
│   │    name         │                                          │           │
│   │    description  │                                          │           │
│   └────────┬────────┘                                          │           │
│            │ 1:N                                               │           │
│            ▼                                                   │           │
│   ┌─────────────────┐         ┌─────────────────────────────┐ │           │
│   │   lkp_choice    │         │      dom_business_case      │ │           │
│   ├─────────────────┤         ├─────────────────────────────┤ │           │
│   │ PK id           │◄────────┤ PK id                       │ │           │
│   │ FK domain_id    │         │    code (unique)            │ │           │
│   │    code         │    ┌───►│ FK category_id              │ │           │
│   │    name         │    │    │ FK status_id                │─┘           │
│   │    description  │    │    │    title                    │             │
│   │    metadata     │────┘    │    problem_statement        │             │
│   │    sort_order   │         │    target_audience          │             │
│   │    parent_id    │         │    expected_benefits        │             │
│   └─────────────────┘         │    scope                    │             │
│            ▲                  │    out_of_scope             │             │
│            │                  │    success_criteria (JSON)  │             │
│            │                  │    assumptions (JSON)       │             │
│            │                  │    risks (JSON)             │             │
│            │                  │    architecture_basis (JSON)│             │
│            │                  │ FK owner_id                 │             │
│            │                  │    inception_session_id     │             │
│            │                  │    created_at               │             │
│            │                  │    updated_at               │             │
│            │                  │    deleted_at               │             │
│            │                  └──────────────┬──────────────┘             │
│            │                                 │                            │
│            │                    ┌────────────┼────────────┐               │
│            │                    │            │            │               │
│            │                    ▼            ▼            ▼               │
│            │         ┌──────────────┐ ┌──────────┐ ┌────────────────┐    │
│            │         │dom_use_case  │ │ dom_adr  │ │dom_conversation│    │
│            │         ├──────────────┤ ├──────────┤ ├────────────────┤    │
│            │         │PK id         │ │PK id     │ │PK id           │    │
│            │         │   code       │ │   code   │ │FK business_    │    │
│            └────────►│FK status_id  │ │FK status │ │   case_id      │    │
│                      │FK priority_id│ │FK bc_id  │ │   session_id   │    │
│                      │FK complexity │ │FK super- │ │   turn_number  │    │
│                      │FK bc_id      │ │   sedes  │ │FK role_id      │    │
│                      │   title      │ │   title  │ │   message      │    │
│                      │   actor      │ │   context│ │   extracted_   │    │
│                      │   main_flow  │ │   decision│ │   data (JSON) │    │
│                      │   (JSON)     │ │   conseq.│ │   next_question│    │
│                      │   alt_flows  │ │   altern.│ │   created_at   │    │
│                      │   (JSON)     │ │   (JSON) │ └────────────────┘    │
│                      │   sort_order │ │   affected│                      │
│                      │   created_at │ │   _comps │                       │
│                      │   deleted_at │ │   (JSON) │                       │
│                      └───────┬──────┘ └────┬─────┘                       │
│                              │             │                              │
│                              │             │                              │
│                              └──────┬──────┘                              │
│                                     │                                     │
│                                     ▼                                     │
│                          ┌─────────────────────┐                          │
│                          │  dom_adr_use_case   │                          │
│                          ├─────────────────────┤                          │
│                          │ PK id               │                          │
│                          │ FK adr_id           │                          │
│                          │ FK use_case_id      │                          │
│                          │    relationship_type│                          │
│                          │    notes            │                          │
│                          └─────────────────────┘                          │
│                                                                           │
│   ┌─────────────────┐                     ┌─────────────────┐            │
│   │   dom_review    │                     │dom_status_history│            │
│   ├─────────────────┤                     ├─────────────────┤            │
│   │ PK id           │                     │ PK id           │            │
│   │    entity_type  │                     │    entity_type  │            │
│   │    entity_id    │                     │    entity_id    │            │
│   │ FK reviewer_id  │                     │ FK old_status_id│            │
│   │    decision     │                     │ FK new_status_id│            │
│   │    comments     │                     │ FK changed_by_id│            │
│   │    requested_   │                     │    reason       │            │
│   │    changes(JSON)│                     │    created_at   │            │
│   │    created_at   │                     └─────────────────┘            │
│   └─────────────────┘                                                    │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Tabellen-Übersicht

| Tabelle | Zweck | Kardinalität |
|---------|-------|--------------|
| `lkp_domain` | Lookup-Domänen (bc_status, uc_priority, ...) | ~10 Einträge |
| `lkp_choice` | Lookup-Werte (draft, approved, high, ...) | ~50 Einträge |
| `dom_business_case` | Business Cases | Wachsend (~100/Jahr) |
| `dom_use_case` | Use Cases | ~5 pro BC |
| `dom_adr` | Architecture Decision Records | ~20/Jahr |
| `dom_conversation` | Inception Dialog | ~10 pro BC |
| `dom_adr_use_case` | ADR ↔ UC Verknüpfung | N:M |
| `dom_review` | Reviews/Approvals | ~2 pro BC |
| `dom_status_history` | Audit Trail | Unbegrenzt |

### 6.3 Lookup-Domänen

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOOKUP DOMAINS                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  bc_category                    bc_status                               │
│  ────────────                   ─────────                               │
│  • neue_domain                  • draft                                 │
│  • integration                  • submitted                             │
│  • optimierung                  • in_review                             │
│  • erweiterung                  • approved                              │
│  • produktion                   • rejected                              │
│  • bugfix                       • in_progress                           │
│                                 • completed                             │
│                                 • archived                              │
│                                                                         │
│  uc_status                      uc_priority                             │
│  ─────────                      ───────────                             │
│  • draft                        • critical                              │
│  • detailed                     • high                                  │
│  • ready                        • medium                                │
│  • in_progress                  • low                                   │
│  • blocked                      • backlog                               │
│  • testing                                                              │
│  • done                         uc_complexity                           │
│                                 ─────────────                           │
│  adr_status                     • trivial (1 SP)                        │
│  ──────────                     • simple (2 SP)                         │
│  • proposed                     • moderate (3 SP)                       │
│  • accepted                     • complex (5 SP)                        │
│  • rejected                     • very_complex (8 SP)                   │
│  • deprecated                   • epic (13 SP)                          │
│  • superseded                                                           │
│                                                                         │
│  conversation_role              flow_step_type                          │
│  ─────────────────              ──────────────                          │
│  • user                         • user_action                           │
│  • agent                        • system_action                         │
│  • system                       • validation                            │
│                                 • decision                              │
│                                 • external_call                         │
│                                 • data_operation                        │
│                                 • notification                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.4 JSONB-Strukturen

#### Business Case: `success_criteria`
```json
[
  "80% Zeitersparnis bei der Abrechnung",
  "Fehlerquote unter 5%",
  "Durchlaufzeit unter 2 Tagen"
]
```

#### Business Case: `risks`
```json
[
  {
    "risk": "OCR-Erkennung ungenau",
    "probability": "medium",
    "impact": "high",
    "mitigation": "Manuelle Korrekturmöglichkeit"
  }
]
```

#### Business Case: `architecture_basis`
```json
{
  "database": "postgresql",
  "backend": "django",
  "frontend": "htmx",
  "extends_app": "bfagent",
  "external_apis": ["ocr-service"]
}
```

#### Use Case: `main_flow`
```json
[
  {"step": 1, "type": "user_action", "description": "Benutzer öffnet Upload-Dialog"},
  {"step": 2, "type": "system_action", "description": "System zeigt Dateiauswahl"},
  {"step": 3, "type": "user_action", "description": "Benutzer wählt Beleg-Foto"},
  {"step": 4, "type": "validation", "description": "System prüft Dateityp und -größe"},
  {"step": 5, "type": "external_call", "description": "System sendet an OCR-Service"},
  {"step": 6, "type": "system_action", "description": "System zeigt extrahierte Daten"},
  {"step": 7, "type": "user_action", "description": "Benutzer bestätigt oder korrigiert"},
  {"step": 8, "type": "data_operation", "description": "System speichert Beleg"}
]
```

#### Use Case: `alternative_flows`
```json
[
  {
    "name": "Ungültiges Dateiformat",
    "branch_from_step": 4,
    "condition": "Dateityp nicht unterstützt",
    "steps": [
      {"step": "4a", "description": "System zeigt Fehlermeldung"},
      {"step": "4b", "description": "Benutzer wählt andere Datei"}
    ],
    "return_to_step": 3
  }
]
```

#### ADR: `alternatives`
```json
[
  {
    "name": "Eigene OCR-Implementierung",
    "description": "Tesseract lokal installieren",
    "pros": ["Keine externen Abhängigkeiten", "Kostenlos"],
    "cons": ["Wartungsaufwand", "Geringere Genauigkeit"],
    "score": 4
  },
  {
    "name": "Google Vision API",
    "description": "Cloud-basierte OCR",
    "pros": ["Hohe Genauigkeit", "Skalierbar"],
    "cons": ["Kosten", "Datenschutz-Bedenken"],
    "score": 7
  },
  {
    "name": "Azure Computer Vision",
    "description": "Microsoft Cloud OCR",
    "pros": ["DSGVO-konform", "Gute Genauigkeit"],
    "cons": ["Vendor Lock-in"],
    "score": 8
  }
]
```

---

*[Fortsetzung in Teil 3: Komponenten, Workflow und Roadmap]*
---

## 7. Komponenten

### 7.1 Komponenten-Übersicht

| Komponente | Typ | Beschreibung | Technologie |
|------------|-----|--------------|-------------|
| **inception_mcp** | MCP Server | AI-gestützte BC-Erstellung | Python, MCP SDK |
| **governance_app** | Django App | Web-UI und API | Django 5, HTMX |
| **db_docs** | Sphinx Extension | DB → Dokumentation | Sphinx, psycopg2 |
| **export_script** | CLI Tool | DB Export für CI/CD | Python |
| **LookupService** | Service | Cached Lookup-Zugriff | Django ORM |
| **InceptionService** | Service | Dialog-Management | Django, LLM API |
| **BusinessCaseService** | Service | BC CRUD & Workflow | Django ORM |

### 7.2 MCP Server: inception_mcp

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INCEPTION MCP SERVER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TOOLS                                                                  │
│  ─────                                                                  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ start_business_case(initial_description, category?)             │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ • Analysiert Freitext                                           │   │
│  │ • Erstellt BC-Draft in DB                                       │   │
│  │ • Gibt erste Frage zurück                                       │   │
│  │ • Returns: session_id, bc_code, question, questions_remaining   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ answer_question(session_id, answer)                             │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ • Extrahiert Daten aus Antwort                                  │   │
│  │ • Aktualisiert BC-Draft                                         │   │
│  │ • Gibt nächste Frage oder Summary zurück                        │   │
│  │ • Returns: question | summary + ready_for_finalization          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ finalize_business_case(session_id, adjustments?)                │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │ • Finalisiert BC                                                │   │
│  │ • Leitet Use Cases ab                                           │   │
│  │ • Returns: bc_code, derived_use_cases[], next_steps[]           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ list_business_cases(status?, category?, search?, limit?)        │   │
│  │ get_business_case(code)                                         │   │
│  │ get_categories()                                                │   │
│  │ submit_for_review(code)                                         │   │
│  │ detail_use_case(code, main_flow, ...)                           │   │
│  │ get_session_status(session_id)                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Web-UI: governance_app

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WEB UI STRUKTUR                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  URLS                                                                   │
│  ────                                                                   │
│  /governance/                          Dashboard                        │
│  /governance/business-cases/           BC Liste                         │
│  /governance/business-cases/create/    BC Erstellen (Simple Form)       │
│  /governance/business-cases/{code}/    BC Detail                        │
│  /governance/use-cases/                UC Liste                         │
│  /governance/use-cases/{code}/         UC Detail                        │
│  /governance/adrs/                     ADR Liste                        │
│  /governance/adrs/{code}/              ADR Detail                       │
│                                                                         │
│  HTMX ENDPOINTS (Partials)                                              │
│  ─────────────────────────                                              │
│  /governance/business-cases/{code}/status/     Status ändern            │
│  /governance/business-cases/list-partial/      Gefilterte Liste         │
│  /governance/use-cases/{code}/flow-editor/     Flow Editor              │
│  /governance/review/{type}/{id}/               Review Form              │
│                                                                         │
│  VIEWS                                                                  │
│  ─────                                                                  │
│  • DashboardView          - Statistiken, Pending Reviews               │
│  • BusinessCaseListView   - Filterbare Liste mit HTMX                  │
│  • BusinessCaseDetailView - Detail mit Use Cases, ADRs, History        │
│  • BusinessCaseCreateView - Simple Form (nicht Inception)              │
│  • UseCaseListView        - Filterbar nach BC, Status, Priorität       │
│  • UseCaseDetailView      - Detail mit Flow-Editor                     │
│  • ADRListView            - Liste mit Status-Badges                    │
│  • ADRDetailView          - Vollständiger ADR mit Alternativen         │
│                                                                         │
│  TEMPLATES                                                              │
│  ─────────                                                              │
│  governance/                                                            │
│  ├── base.html                 - Layout mit Navigation                 │
│  ├── dashboard.html            - Stats, Recent, Pending                │
│  ├── business_case/                                                    │
│  │   ├── list.html             - Filter + Tabelle                      │
│  │   ├── detail.html           - Vollständige Ansicht                  │
│  │   ├── form.html             - Create/Edit Form                      │
│  │   ├── _list_table.html      - HTMX Partial                          │
│  │   └── _status_badge.html    - HTMX Partial                          │
│  ├── use_case/                                                         │
│  │   ├── list.html                                                     │
│  │   ├── detail.html                                                   │
│  │   ├── _flow_display.html    - Read-only Flow                        │
│  │   └── _flow_editor.html     - Interaktiver Editor                   │
│  ├── adr/                                                              │
│  │   ├── list.html                                                     │
│  │   └── detail.html                                                   │
│  ├── _review_form.html         - Modal für Approvals                   │
│  └── _review_success.html      - Bestätigung                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Sphinx Extension: db_docs

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SPHINX EXTENSION                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DIRECTIVES                                                             │
│  ──────────                                                             │
│                                                                         │
│  .. db-business-case:: BC-001                                          │
│     Lädt BC aus DB und generiert RST                                   │
│                                                                         │
│  .. db-use-case:: UC-001                                               │
│     Lädt UC aus DB und generiert RST mit Flows                         │
│                                                                         │
│  .. db-adr:: ADR-001                                                   │
│     Lädt ADR aus DB mit Alternativen-Tabelle                           │
│                                                                         │
│  .. db-business-case-list::                                            │
│     :status: approved                                                   │
│     :category: neue_domain                                             │
│     Generiert Tabelle mit Links                                        │
│                                                                         │
│  KONFIGURATION (conf.py)                                               │
│  ────────────────────────                                              │
│                                                                         │
│  extensions = ['_extensions.db_docs']                                  │
│  db_docs_database_url = os.environ.get('DATABASE_URL')                 │
│                                                                         │
│  USAGE EXAMPLE                                                         │
│  ─────────────                                                         │
│                                                                         │
│  Business Cases                                                        │
│  ==============                                                        │
│                                                                         │
│  Übersicht aller genehmigten Business Cases:                           │
│                                                                         │
│  .. db-business-case-list::                                            │
│     :status: approved                                                   │
│                                                                         │
│  Details                                                               │
│  -------                                                               │
│                                                                         │
│  .. db-business-case:: BC-042                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Prozess-Workflow

### 8.1 End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         END-TO-END WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: INCEPTION                                                         │
│  ──────────────────                                                         │
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  Idee    │───►│ Start BC │───►│ Dialog   │───►│ Finalize │             │
│  │          │    │          │    │ Q&A      │    │          │             │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘             │
│                                                       │                    │
│                        Entwickler (MCP)               │                    │
│  ─────────────────────────────────────────────────────┼────────────────── │
│                                                       │                    │
│  PHASE 2: DERIVATION                                  │                    │
│  ───────────────────                                  │                    │
│                                                       ▼                    │
│                                                  ┌──────────┐             │
│                                                  │ Auto UC  │             │
│                                                  │ Derive   │             │
│                                                  └────┬─────┘             │
│                                                       │                    │
│                        System (automatisch)           │                    │
│  ─────────────────────────────────────────────────────┼────────────────── │
│                                                       │                    │
│  PHASE 3: ELABORATION                                 │                    │
│  ────────────────────                                 │                    │
│                                                       ▼                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Detail   │───►│ Define   │───►│ Create   │───►│ Link UC  │             │
│  │ UC Flows │    │ Pre/Post │    │ ADR      │    │ to ADR   │             │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘             │
│                                                       │                    │
│                        Entwickler/Architekt           │                    │
│  ─────────────────────────────────────────────────────┼────────────────── │
│                                                       │                    │
│  PHASE 4: REVIEW                                      │                    │
│  ──────────────                                       │                    │
│                                                       ▼                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Submit   │───►│ Review   │───►│ Approve/ │───►│ Ready    │             │
│  │ for Rev  │    │          │    │ Reject   │    │          │             │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘             │
│                                                       │                    │
│                        Product Owner (Web-UI)         │                    │
│  ─────────────────────────────────────────────────────┼────────────────── │
│                                                       │                    │
│  PHASE 5: IMPLEMENTATION                              │                    │
│  ──────────────────────                               │                    │
│                                                       ▼                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │ Code     │───►│ Test     │───►│ Deploy   │───►│ Complete │             │
│  │          │    │          │    │          │    │          │             │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘             │
│                                                       │                    │
│                        Entwickler                     │                    │
│  ─────────────────────────────────────────────────────┼────────────────── │
│                                                       │                    │
│  PHASE 6: DOCUMENTATION                               │                    │
│  ──────────────────────                               │                    │
│                                                       ▼                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                             │
│  │ Export   │───►│ Build    │───►│ Deploy   │                             │
│  │ from DB  │    │ Sphinx   │    │ Pages    │                             │
│  └──────────┘    └──────────┘    └──────────┘                             │
│                                                                            │
│                        GitHub Actions (automatisch)                        │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Status-Workflow Business Case

```
                                  ┌─────────────┐
                                  │             │
                         ┌───────►│  ARCHIVED   │
                         │        │             │
                         │        └─────────────┘
                         │              ▲
                         │              │
┌─────────┐        ┌─────┴─────┐  ┌─────┴─────┐  ┌───────────┐
│         │        │           │  │           │  │           │
│  DRAFT  │───────►│ SUBMITTED │─►│ IN_REVIEW │─►│ APPROVED  │
│         │        │           │  │           │  │           │
└────┬────┘        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
     │                   │              │              │
     │                   │              │              │
     │                   │              ▼              ▼
     │                   │        ┌───────────┐  ┌───────────┐
     │                   │        │           │  │           │
     │◄──────────────────┼────────│ REJECTED  │  │IN_PROGRESS│
     │                   │        │           │  │           │
     │                   │        └───────────┘  └─────┬─────┘
     │                   │                             │
     │                   │                             ▼
     │                   │                       ┌───────────┐
     │                   │        ┌──────────────│           │
     │                   │        │              │ ON_HOLD   │
     │                   │        │              │           │
     │                   │        │              └───────────┘
     │                   │        │
     │                   │        ▼
     │                   │  ┌───────────┐
     │                   │  │           │
     │                   └─►│ COMPLETED │
     │                      │           │
     │                      └───────────┘
     │
     ▼
  (Bearbeitung)
```

### 8.3 Kategorie-spezifische Fragen

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    KATEGORIE-SPEZIFISCHE FRAGEN                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ALLE KATEGORIEN (Default)                                              │
│  ─────────────────────────                                              │
│  1. Wer ist die primäre Zielgruppe?                                    │
│  2. Was sind die messbaren Erfolgskriterien?                           │
│  3. Was ist explizit NICHT Teil des Projekts?                          │
│  4. Welche Annahmen liegen zugrunde?                                   │
│  5. Gibt es bekannte Risiken?                                          │
│  6. Wer ist der fachliche Ansprechpartner?                             │
│                                                                         │
│  NEUE_DOMAIN (zusätzlich)                                              │
│  ────────────────────────                                              │
│  • Gibt es einen Domänenexperten?                                      │
│  • Wie grenzt sich die Domain ab?                                      │
│  • Müssen Daten migriert werden?                                       │
│  • Welche Datenbank-Technologie? (Architecture)                        │
│  • Welches Backend-Framework? (Architecture)                           │
│  • Welche Frontend-Technologie? (Architecture)                         │
│                                                                         │
│  INTEGRATION (zusätzlich)                                              │
│  ────────────────────────                                              │
│  • Welches externe System?                                             │
│  • Ist eine API dokumentiert?                                          │
│  • Welche Authentifizierung wird benötigt?                             │
│                                                                         │
│  OPTIMIERUNG (zusätzlich)                                              │
│  ────────────────────────                                              │
│  • Was sind die aktuellen Pain Points?                                 │
│  • Wie lässt sich die Verbesserung messen?                             │
│                                                                         │
│  ERWEITERUNG (zusätzlich)                                              │
│  ────────────────────────                                              │
│  • Welche bestehende Domain wird erweitert?                            │
│  • Gibt es Breaking Changes?                                           │
│                                                                         │
│  PRODUKTION (zusätzlich)                                               │
│  ────────────────────────                                              │
│  • Welcher Branch/Version?                                             │
│  • Was ist der Rollback-Plan?                                          │
│  • Welches Monitoring ist eingerichtet?                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Technologie-Stack

### 9.1 Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TECHNOLOGIE-STACK                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  LAYER              TECHNOLOGIE           VERSION                       │
│  ─────              ───────────           ───────                       │
│                                                                         │
│  Database           PostgreSQL            15+                           │
│                     └─ JSONB für flexible Strukturen                   │
│                     └─ Full-Text Search (german)                       │
│                     └─ Row-Level Security (Mandanten)                  │
│                                                                         │
│  Backend            Django                5.0+                          │
│                     └─ Django REST Framework                           │
│                     └─ psycopg2                                        │
│                     └─ Gunicorn                                        │
│                                                                         │
│  Frontend           HTMX                  1.9+                          │
│                     └─ Alpine.js          3.x                          │
│                     └─ Tailwind CSS       3.x                          │
│                                                                         │
│  MCP Server         Python                3.11+                         │
│                     └─ mcp SDK                                         │
│                     └─ Django ORM (shared)                             │
│                                                                         │
│  LLM Integration    Anthropic Claude      claude-3-5-sonnet            │
│                     └─ API für Extraction                              │
│                     └─ API für Use Case Derivation                     │
│                                                                         │
│  Documentation      Sphinx                7.x                           │
│                     └─ Custom db_docs Extension                        │
│                     └─ Read the Docs Theme                             │
│                                                                         │
│  CI/CD              GitHub Actions                                      │
│                     └─ Export Job                                      │
│                     └─ Build Job                                       │
│                     └─ Deploy to Pages                                 │
│                                                                         │
│  Hosting            Hetzner Cloud                                       │
│                     └─ Docker Container                                │
│                     └─ Traefik Reverse Proxy                           │
│                     └─ Let's Encrypt SSL                               │
│                                                                         │
│  Observability      (existing platform)                                 │
│                     └─ Logging                                         │
│                     └─ Metrics                                         │
│                     └─ Alerts                                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Abhängigkeiten

```
# requirements.txt (governance_app)

Django>=5.0
psycopg2-binary>=2.9
django-htmx>=1.17
whitenoise>=6.6

# requirements.txt (inception_mcp)

mcp>=0.9
anthropic>=0.18
psycopg2-binary>=2.9

# requirements.txt (docs)

Sphinx>=7.2
sphinx-rtd-theme>=2.0
psycopg2-binary>=2.9
```

---

## 10. Implementierungs-Roadmap

### 10.1 Phasen-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      IMPLEMENTIERUNGS-ROADMAP                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PHASE 1: FOUNDATION (2 Wochen)                                        │
│  ══════════════════════════════                                        │
│  □ Database Schema implementieren                                      │
│  □ Django Models erstellen                                             │
│  □ LookupService implementieren                                        │
│  □ Basis-Migrationen ausführen                                         │
│  □ Lookup-Daten laden                                                  │
│                                                                         │
│  PHASE 2: SERVICES (2 Wochen)                                          │
│  ════════════════════════════                                          │
│  □ BusinessCaseService implementieren                                  │
│  □ UseCaseService implementieren                                       │
│  □ ADRService implementieren                                           │
│  □ InceptionService (ohne LLM) implementieren                          │
│  □ Unit Tests für Services                                             │
│                                                                         │
│  PHASE 3: MCP SERVER (2 Wochen)                                        │
│  ══════════════════════════════                                        │
│  □ MCP Server Grundstruktur                                            │
│  □ start_business_case Tool                                            │
│  □ answer_question Tool                                                │
│  □ finalize_business_case Tool                                         │
│  □ LLM-Integration für Extraction                                      │
│  □ Use Case Derivation mit LLM                                         │
│  □ Integration Tests                                                   │
│                                                                         │
│  PHASE 4: WEB UI (2 Wochen)                                            │
│  ══════════════════════════                                            │
│  □ Base Template + Navigation                                          │
│  □ Dashboard View                                                      │
│  □ Business Case List + Detail                                         │
│  □ Use Case List + Detail + Flow Editor                                │
│  □ ADR List + Detail                                                   │
│  □ Review/Approval Workflow                                            │
│  □ HTMX Interaktionen                                                  │
│                                                                         │
│  PHASE 5: DOCUMENTATION (1 Woche)                                      │
│  ════════════════════════════════                                      │
│  □ Sphinx Extension implementieren                                     │
│  □ Export Script erstellen                                             │
│  □ GitHub Actions Workflow                                             │
│  □ Initial Documentation Build                                         │
│                                                                         │
│  PHASE 6: INTEGRATION & POLISH (1 Woche)                               │
│  ═══════════════════════════════════════                               │
│  □ E2E Tests                                                           │
│  □ Performance Optimierung                                             │
│  □ Dokumentation vervollständigen                                      │
│  □ Deployment auf Staging                                              │
│  □ User Acceptance Testing                                             │
│                                                                         │
│  PHASE 7: PRODUCTION (1 Woche)                                         │
│  ════════════════════════════                                          │
│  □ Production Deployment                                               │
│  □ Monitoring einrichten                                               │
│  □ Team-Schulung                                                       │
│  □ Feedback sammeln                                                    │
│                                                                         │
│  ═══════════════════════════════════════════════════════════════════   │
│  GESAMT: ~11 Wochen                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Gantt-Diagramm (vereinfacht)

```
Woche:        1    2    3    4    5    6    7    8    9   10   11
              ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
              │                                                  │
Foundation    ████████                                           │
              │    │                                             │
Services      │    ████████                                      │
              │         │                                        │
MCP Server    │         ████████                                 │
              │              │                                   │
Web UI        │              ████████                            │
              │                   │                              │
Documentation │                   ██████                         │
              │                        │                         │
Integration   │                        ██████                    │
              │                             │                    │
Production    │                             ██████               │
              │                                  │               │
              └──────────────────────────────────┼───────────────┘
                                                 │
                                           GO LIVE
```

### 10.3 Meilensteine

| Meilenstein | Woche | Kriterium |
|-------------|-------|-----------|
| M1: Schema Ready | 2 | Alle Tabellen erstellt, Lookups geladen |
| M2: Services Complete | 4 | Alle Services mit Tests |
| M3: MCP Functional | 6 | End-to-End BC-Erstellung via MCP |
| M4: UI Complete | 8 | Alle Views funktional |
| M5: Docs Automated | 9 | Automatischer Build + Deploy |
| M6: Production Ready | 11 | Alle Tests grün, Performance OK |

---

## 11. Beispiel-Szenario

### 11.1 Kompletter Durchlauf: Reisekostenabrechnung

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BEISPIEL: REISEKOSTENABRECHNUNG                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SCHRITT 1: Inception starten (Windsurf)                               │
│  ───────────────────────────────────────                               │
│                                                                         │
│  👤 Entwickler ruft MCP Tool auf:                                       │
│                                                                         │
│  > start_business_case(                                                │
│  >   initial_description="Wir brauchen eine digitale Reisekosten-      │
│  >     abrechnung. Mitarbeiter sollen Belege fotografieren können,     │
│  >     die dann per OCR ausgelesen werden. Am Ende soll ein PDF        │
│  >     für die Buchhaltung erstellt werden.",                          │
│  >   category="neue_domain"                                            │
│  > )                                                                   │
│                                                                         │
│  🤖 Agent Response:                                                     │
│  {                                                                      │
│    "session_id": "a1b2c3d4-...",                                       │
│    "business_case_code": "BC-042",                                     │
│    "status": "in_progress",                                            │
│    "detected_category": "neue_domain",                                 │
│    "understood": {                                                     │
│      "title": "Digitale Reisekostenabrechnung",                        │
│      "keywords": ["OCR", "Belege", "PDF", "Buchhaltung"]               │
│    },                                                                  │
│    "question": "Wer ist die primäre Zielgruppe für diese Lösung?",    │
│    "questions_remaining": 8                                            │
│  }                                                                     │
│                                                                         │
│  SCHRITT 2: Fragen beantworten (iterativ)                              │
│  ─────────────────────────────────────────                             │
│                                                                         │
│  👤 > answer_question(session_id, "Außendienstmitarbeiter und          │
│  >    Vorgesetzte für die Genehmigung")                                │
│                                                                         │
│  🤖 {                                                                   │
│    "question": "Was sind die messbaren Erfolgskriterien?",             │
│    "questions_remaining": 7                                            │
│  }                                                                     │
│                                                                         │
│  👤 > answer_question(session_id, "80% Zeitersparnis gegenüber         │
│  >    manueller Abrechnung, Fehlerquote unter 5%")                     │
│                                                                         │
│  🤖 {                                                                   │
│    "question": "Gibt es einen Domänenexperten, der das Projekt         │
│                 begleiten kann?",                                      │
│    "questions_remaining": 6                                            │
│  }                                                                     │
│                                                                         │
│  [...weitere Fragen...]                                                │
│                                                                         │
│  🤖 Nach letzter Frage:                                                 │
│  {                                                                      │
│    "status": "ready_for_finalization",                                 │
│    "summary": "**BC-042: Digitale Reisekostenabrechnung**\n..."        │
│  }                                                                     │
│                                                                         │
│  SCHRITT 3: Finalisieren                                               │
│  ───────────────────────                                               │
│                                                                         │
│  👤 > finalize_business_case(session_id)                               │
│                                                                         │
│  🤖 {                                                                   │
│    "status": "finalized",                                              │
│    "business_case": {                                                  │
│      "code": "BC-042",                                                 │
│      "title": "Digitale Reisekostenabrechnung",                        │
│      "status": "draft"                                                 │
│    },                                                                  │
│    "derived_use_cases": [                                              │
│      {"code": "UC-087", "title": "Beleg fotografieren und hochladen"}, │
│      {"code": "UC-088", "title": "OCR-Erkennung durchführen"},         │
│      {"code": "UC-089", "title": "Abrechnung erstellen"},              │
│      {"code": "UC-090", "title": "Abrechnung zur Genehmigung senden"}, │
│      {"code": "UC-091", "title": "Abrechnung genehmigen/ablehnen"},    │
│      {"code": "UC-092", "title": "PDF für Buchhaltung exportieren"}    │
│    ],                                                                  │
│    "next_steps": [                                                     │
│      "Use Cases detaillieren",                                         │
│      "ADR für OCR-Service erstellen",                                  │
│      "Zur Review einreichen"                                           │
│    ]                                                                   │
│  }                                                                     │
│                                                                         │
│  SCHRITT 4: Use Case detaillieren (Entwickler)                         │
│  ─────────────────────────────────────────────                         │
│                                                                         │
│  👤 > detail_use_case(                                                 │
│  >   code="UC-087",                                                    │
│  >   main_flow=[                                                       │
│  >     {"step": 1, "type": "user_action",                              │
│  >      "description": "Benutzer öffnet Kamera-Dialog"},               │
│  >     {"step": 2, "type": "system_action",                            │
│  >      "description": "System aktiviert Kamera"},                     │
│  >     {"step": 3, "type": "user_action",                              │
│  >      "description": "Benutzer fotografiert Beleg"},                 │
│  >     ...                                                             │
│  >   ],                                                                │
│  >   preconditions=["Benutzer ist angemeldet", "Offene Abrechnung"],   │
│  >   postconditions=["Beleg ist im System gespeichert"]                │
│  > )                                                                   │
│                                                                         │
│  SCHRITT 5: Review (Product Owner in Web-UI)                           │
│  ───────────────────────────────────────────                           │
│                                                                         │
│  PO öffnet /governance/business-cases/BC-042/                          │
│  PO prüft Problem, Zielgruppe, Use Cases                               │
│  PO klickt "Genehmigen" mit Kommentar                                  │
│                                                                         │
│  → Status wechselt zu "approved"                                       │
│  → Use Cases sind "ready" für Implementierung                          │
│                                                                         │
│  SCHRITT 6: Dokumentation (automatisch)                                │
│  ──────────────────────────────────────                                │
│                                                                         │
│  GitHub Action wird ausgelöst:                                         │
│  1. Export: BC-042, UC-087..UC-092 → RST-Dateien                       │
│  2. Build: Sphinx generiert HTML                                       │
│  3. Deploy: docs.platform.example.com/business_cases/BC-042.html      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Anhang

### A. Glossar

| Begriff | Beschreibung |
|---------|--------------|
| **BC** | Business Case - Geschäftsanforderung |
| **UC** | Use Case - Funktionale Anforderung |
| **ADR** | Architecture Decision Record |
| **DDL** | Domain Development Lifecycle |
| **MCP** | Model Context Protocol |
| **Inception** | AI-gestützter Dialog zur BC-Erstellung |

### B. Referenzen

- ADR-015: Platform Governance System
- PLATFORM_ARCHITECTURE_MASTER.md
- MCP Specification: https://modelcontextprotocol.io/

### C. Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2025-02 | Initiale Version |

---

**Ende des Konzeptpapiers**
