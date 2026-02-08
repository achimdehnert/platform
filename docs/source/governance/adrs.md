# ADR Registry

```{note}
Diese Seite wird zukünftig automatisch aus `platform.dom_adr` generiert
via `python manage.py sync_adrs --direction db-to-rst`.
```

## Übersicht

| ADR | Titel | Status | Scope |
|-----|-------|--------|-------|
| ADR-007 | Final Production Architecture | Accepted | Infrastructure |
| ADR-008 | Infrastructure & Deployment | Accepted | Hetzner, Docker |
| ADR-009 | IFC/DXF Processing | Accepted | CAD services |
| ADR-010 | 3D Viewer Strategy | Accepted | CAD frontend |
| ADR-012 | MCP Quality Standards | Accepted | MCP servers |
| ADR-013 | Team Organization & MCP Ownership | Accepted | Organization |
| ADR-014 | AI-Native Development Teams | Accepted | AI workflows |
| ADR-015 | Platform Governance System | Accepted | Lookup pattern |
| ADR-016 | Trip Plan Import | Accepted | Travel-beat |
| ADR-017 | Domain Development Lifecycle | Accepted | DDL system |
| ADR-018 | Weltenhub Architecture | Accepted | Story platform |
| ADR-019 | Weltenhub UI, Templates, APIs | Accepted | Frontend |
| ADR-020 | Dokumentationsstrategie | Proposed | Sphinx + DB |

### Travel-Beat ADRs

| ADR | Titel | Status | Scope |
|-----|-------|--------|-------|
| TB-019 | Story Review & Optimization | **Implemented** | Review pipeline |
| TB-020 | Stop-Enrichment & Weltenhub Pipeline | **Implemented** | Enrichment |

## ADR-Template

Alle ADRs folgen diesem Schema:

1. **Executive Summary** — Kurzzusammenfassung
2. **Context** — Problem Statement, Anforderungen
3. **Decision** — Gewählte Lösung mit Begründung
4. **Consequences** — Positive und negative Auswirkungen
5. **Implementation** — Technische Umsetzung
