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
