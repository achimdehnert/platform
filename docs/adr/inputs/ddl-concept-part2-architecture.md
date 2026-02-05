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
