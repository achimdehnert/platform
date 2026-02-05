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
