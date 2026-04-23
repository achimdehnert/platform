# Übersicht

BF Agent ist ein Django-basiertes System für AI-gestütztes kreatives Schreiben.

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        BF Agent                                  │
├─────────────────────────────────────────────────────────────────┤
│  Writing Hub     │  CAD Hub      │  MCP Hub      │  Control     │
│  - Books         │  - Projects   │  - Servers    │  - Dashboard │
│  - Chapters      │  - Documents  │  - Tools      │  - Analytics │
│  - Characters    │  - Exports    │  - Profiles   │  - Settings  │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Workflow System                               │
│  Handlers (DB I/O) ←→ Agents (Pure AI) ←→ LLM Gateway           │
└─────────────────────────────────────────────────────────────────┘
```

## Hauptkomponenten

### Writing Hub
- **BookProject** - Buchprojekte mit Metadaten
- **Chapter** - Kapitel mit Status-Workflow
- **Character** - Charaktere mit Backstory
- **Scene** - Szenen innerhalb von Kapiteln

### Workflow System
- **Handlers** - Orchestrieren DB-Operationen
- **Agents** - Pure AI-Funktionen (kein DB-Zugriff!)
- **Context** - Immutable State zwischen Schritten

### n8n Integration
- Visual Workflow Builder
- REST API für externe Aufrufe
- 400+ Integrationen (Email, Slack, etc.)
