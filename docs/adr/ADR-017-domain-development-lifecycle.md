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

### 2.6 Systemabgrenzung

> **WICHTIG:** DDL ist ein **Meta-System** für die Entwicklungssteuerung und **unabhängig** von allen Fachdomänen.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PLATFORM ECOSYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              DDL (Domain Development Lifecycle)              │   │
│  │                    Schema: platform                          │   │
│  │                                                              │   │
│  │  • Business Cases    • Use Cases    • ADRs                  │   │
│  │  • Inception         • Reviews      • Status Tracking       │   │
│  │                                                              │   │
│  │  UNABHÄNGIG von Fachdomänen - steuert deren Entwicklung     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              │ beschreibt/steuert                   │
│                              ▼                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ travel-beat │  │  pptx-hub   │  │  weltenhub  │  │    ...    │ │
│  │             │  │             │  │             │  │           │ │
│  │ Eigene DB   │  │ Eigene DB   │  │ Eigene DB   │  │ Eigene DB │ │
│  │ Eigene      │  │ Eigene      │  │ Eigene      │  │ Eigene    │ │
│  │ Lookups     │  │ Lookups     │  │ Lookups     │  │ Lookups   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │
│                                                                     │
│                    FACHDOMÄNEN (unabhängig)                        │
└─────────────────────────────────────────────────────────────────────┘
```

| Aspekt | DDL | Fachdomänen |
|--------|-----|-------------|
| **Zweck** | Entwicklungsprozess steuern | Fachliche Funktionalität |
| **Schema** | `platform` | Eigenes Schema pro Domäne |
| **Lookups** | `platform.lkp_*` (DDL-spezifisch) | Eigene `lkp_*` Tabellen |
| **Deployment** | Zentral (Platform) | Unabhängig pro Domäne |
| **Datenbank** | PostgreSQL (Governance DB) | Kann variieren |

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

> **Hinweis:** DDL verwendet eigene Lookup-Tabellen im `platform` Schema. Diese sind **unabhängig** von Lookups in Fachdomänen (z.B. `weltenhub.lkp_genre`).

| Tabelle | Zweck | Beispiel-Werte |
|---------|-------|----------------|
| `platform.lkp_domain` | Lookup-Domänen | bc_status, uc_priority, adr_status |
| `platform.lkp_choice` | Lookup-Werte | draft, approved, high, critical |

**Wichtig:** Alle Auswahllisten in DDL kommen aus diesen Tabellen - **keine hardcoded Enums** im Code:

```python
# ❌ FALSCH - Hardcoded Enum
RELATIONSHIP_TYPES = [('implements', 'Implementiert'), ...]

# ✅ RICHTIG - FK zu lkp_choice
relationship_type = models.ForeignKey(
    'governance.LookupChoice',
    limit_choices_to={'domain__code': 'adr_uc_relationship'},
)
```

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
| Abhängigkeit von LLM für Inception | Expliziter Fehler + Web-UI Alternative (kein stilles Fallback) |
| Zusätzliche DB-Tabellen | Klare Schema-Trennung (platform.*) |

### 4.3 Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| LLM-Kosten bei hoher Nutzung | Mittel | Mittel | Token-Budgets, Caching |
| Adoption-Widerstand | Niedrig | Hoch | Einfache MCP-Integration |
| Datenqualität bei schlechtem Input | Mittel | Mittel | Validation Rules |
| LLM-Ausfall/Quota erschöpft | Niedrig | Hoch | Expliziter Fehler + Web-UI Fallback |
| Rollback erforderlich | Niedrig | Hoch | Rollback-Scripts pro Phase |

---

## 5. Implementation

### 5.1 Phasen-Roadmap

| Phase | Umfang | Timeline | Status | Rollback |
|-------|--------|----------|--------|----------|
| **P1: Foundation** | Datenmodell, Django Models, Admin | Woche 1-2 | 🔲 Geplant | `DROP SCHEMA platform CASCADE` |
| **P2: Services** | BusinessCaseService, LookupService | Woche 3-4 | 🔲 Geplant | Revert Django App |
| **P3: MCP Server** | inception_mcp mit Inception Dialog | Woche 5-6 | 🔲 Geplant | MCP Config entfernen |
| **P4: Web-UI** | governance_app mit HTMX | Woche 7-8 | 🔲 Geplant | URLs deaktivieren |
| **P5: Sphinx** | db_docs Extension | Woche 9 | 🔲 Geplant | Extension entfernen |
| **P6: GitHub Actions** | Automated Docs Build | Woche 10 | 🔲 Geplant | Workflow deaktivieren |

### 5.1.1 Rollback-Strategie

```bash
#!/usr/bin/env bash
# rollback.sh - DDL Governance Rollback
# Usage: ./rollback.sh <PHASE>
#
# Exit Codes:
#   0 - Success
#   1 - Invalid phase
#   2 - Rollback failed

set -euo pipefail

PHASE="${1:-}"

case "$PHASE" in
    p1|foundation)
        log_info "Rolling back P1: Foundation"
        # Daten sichern vor DROP
        pg_dump -h localhost -U governance -d governance \
            --schema=platform -f "backup_platform_$(date +%Y%m%d_%H%M%S).sql"
        # Schema entfernen
        psql -h localhost -U governance -d governance \
            -c "DROP SCHEMA IF EXISTS platform CASCADE;"
        ;;
    p2|services)
        log_info "Rolling back P2: Services"
        # Django App deaktivieren (INSTALLED_APPS)
        sed -i "s/'apps.governance',/#'apps.governance',/" config/settings/base.py
        ;;
    p3|mcp)
        log_info "Rolling back P3: MCP Server"
        # MCP Server aus Config entfernen
        jq 'del(.mcpServers."inception-mcp")' ~/.codeium/windsurf/mcp_config.json > tmp.json
        mv tmp.json ~/.codeium/windsurf/mcp_config.json
        ;;
    p4|webui)
        log_info "Rolling back P4: Web-UI"
        # URLs deaktivieren
        sed -i "s|path('governance/'|#path('governance/'|" config/urls.py
        ;;
    *)
        log_error "Unknown phase: $PHASE"
        echo "Usage: $0 <p1|p2|p3|p4|p5|p6>"
        exit 1
        ;;
esac

log_success "Rollback completed for phase: $PHASE"
```

### 5.1.2 Feature Flags

```sql
-- Feature Flags für graduellen Rollout
-- In platform.lkp_choice mit domain='feature_flag'

INSERT INTO platform.lkp_choice (domain_id, domain, code, name, is_active, metadata)
VALUES
    (1, 'feature_flag', 'ddl_inception_enabled', 'DDL Inception MCP', false, '{"rollout_percentage": 0}'),
    (1, 'feature_flag', 'ddl_webui_enabled', 'DDL Web-UI', false, '{"rollout_percentage": 0}'),
    (1, 'feature_flag', 'ddl_sphinx_enabled', 'DDL Sphinx Docs', false, '{"rollout_percentage": 0}');
```

### 5.2 Technologie-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Backend | Django | 5.x |
| Database | PostgreSQL | 16.x |
| Connection Pool | PgBouncer | 1.22+ |
| Frontend | HTMX + Alpine.js | 2.x |
| MCP Server | Python MCP SDK | Latest |
| LLM | Claude API (via LLM Gateway) | 3.x |
| Documentation | Sphinx | 7.x |
| CI/CD | GitHub Actions | - |
| Container Runtime | Docker + Compose | 24.x / 2.x |
| Reverse Proxy | Traefik | 3.x |
| Target Platform | Hetzner Cloud VMs | - |

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

### 5.4 Infrastructure & Deployment

#### 5.4.1 Docker Compose Stack

```yaml
# docker-compose.prod.yml
# DDL Governance Stack - Hetzner Deployment
#
# Voraussetzungen:
#   - Docker 24.x, Compose 2.x
#   - .env.prod mit DATABASE_URL, ANTHROPIC_API_KEY
#   - Traefik Netzwerk 'web' existiert
#
# Usage:
#   docker compose -f docker-compose.prod.yml up -d
#   docker compose -f docker-compose.prod.yml logs -f governance

version: "3.9"

services:
  # ============================================
  # PostgreSQL 16 - Persistente Datenbank
  # ============================================
  postgres:
    image: postgres:16-alpine
    container_name: ddl_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-governance}
      POSTGRES_USER: ${POSTGRES_USER:-governance}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD required}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-governance} -d ${POSTGRES_DB:-governance}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - internal

  # ============================================
  # PgBouncer - Connection Pooling
  # ============================================
  pgbouncer:
    image: edoburu/pgbouncer:1.22.1
    container_name: ddl_pgbouncer
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgres://${POSTGRES_USER:-governance}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-governance}
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
    networks:
      - internal

  # ============================================
  # Django Governance App
  # ============================================
  governance:
    image: ghcr.io/achimdehnert/platform/governance:${IMAGE_TAG:-latest}
    container_name: ddl_governance
    restart: unless-stopped
    depends_on:
      pgbouncer:
        condition: service_started
      postgres:
        condition: service_healthy
    environment:
      # Database (via pgbouncer)
      DATABASE_URL: postgres://${POSTGRES_USER:-governance}:${POSTGRES_PASSWORD}@pgbouncer:6432/${POSTGRES_DB:-governance}
      # Django
      DJANGO_SETTINGS_MODULE: config.settings.production
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY required}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-governance.iil.pet}
      # LLM Gateway
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY required}
      LLM_GATEWAY_URL: ${LLM_GATEWAY_URL:-http://llm-gateway:8080}
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.governance.rule=Host(`${TRAEFIK_HOST:-governance.iil.pet}`)"
      - "traefik.http.routers.governance.tls=true"
      - "traefik.http.routers.governance.tls.certresolver=letsencrypt"
      - "traefik.http.services.governance.loadbalancer.server.port=8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - internal
      - web

volumes:
  postgres_data:
    name: ddl_postgres_data

networks:
  internal:
    name: ddl_internal
  web:
    external: true
```

#### 5.4.2 Deployment Script

```bash
#!/usr/bin/env bash
# deploy.sh - DDL Governance Deployment
#
# Usage:
#   ./deploy.sh [IMAGE_TAG]
#
# Exit Codes:
#   0 - Success
#   1 - Missing dependencies
#   2 - Missing environment variables
#   3 - Docker compose failed
#   4 - Health check failed
#
# Idempotent: Safe to run multiple times

set -euo pipefail

# ============================================
# Configuration
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.prod.yml"
ENV_FILE="${SCRIPT_DIR}/.env.prod"
IMAGE_TAG="${1:-latest}"
HEALTH_CHECK_URL="http://localhost:8000/health/"
HEALTH_CHECK_RETRIES=30
HEALTH_CHECK_INTERVAL=2

# ============================================
# Functions
# ============================================
log_info() { echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*"; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
log_success() { echo "[OK] $(date '+%Y-%m-%d %H:%M:%S') $*"; }

check_dependencies() {
    local missing=0
    for cmd in docker curl; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Missing required command: $cmd"
            missing=1
        fi
    done
    return $missing
}

check_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Validate required variables
    local required_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "ANTHROPIC_API_KEY")
    local missing=0
    
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Missing required environment variable: $var"
            missing=1
        fi
    done
    
    return $missing
}

wait_for_health() {
    local retries=$HEALTH_CHECK_RETRIES
    log_info "Waiting for service health..."
    
    while [[ $retries -gt 0 ]]; do
        if curl -sf "$HEALTH_CHECK_URL" &>/dev/null; then
            log_success "Service is healthy"
            return 0
        fi
        retries=$((retries - 1))
        sleep $HEALTH_CHECK_INTERVAL
    done
    
    log_error "Health check failed after $HEALTH_CHECK_RETRIES attempts"
    return 1
}

# ============================================
# Main
# ============================================
main() {
    log_info "Starting DDL Governance deployment (tag: $IMAGE_TAG)"
    
    # Pre-flight checks
    if ! check_dependencies; then
        exit 1
    fi
    
    if ! check_env_file; then
        exit 2
    fi
    
    # Export for docker compose
    export IMAGE_TAG
    
    # Pull latest images (idempotent)
    log_info "Pulling images..."
    if ! docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull; then
        log_error "Failed to pull images"
        exit 3
    fi
    
    # Deploy (idempotent - recreates only if changed)
    log_info "Deploying services..."
    if ! docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans; then
        log_error "Failed to deploy services"
        exit 3
    fi
    
    # Run migrations (idempotent)
    log_info "Running database migrations..."
    if ! docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T governance \
        python manage.py migrate --no-input; then
        log_error "Failed to run migrations"
        exit 3
    fi
    
    # Health check
    if ! wait_for_health; then
        log_error "Deployment failed health check"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50 governance
        exit 4
    fi
    
    log_success "Deployment completed successfully"
    exit 0
}

main "$@"
```

#### 5.4.3 Database Initialization

```sql
-- scripts/init-db.sql
-- DDL Governance - Database Initialization
--
-- Idempotent: Uses IF NOT EXISTS
-- Run by: docker-entrypoint-initdb.d

-- Create schema (idempotent)
CREATE SCHEMA IF NOT EXISTS platform;

-- Set search path
ALTER DATABASE governance SET search_path TO platform, public;

-- Grant permissions
GRANT ALL ON SCHEMA platform TO governance;
GRANT ALL ON ALL TABLES IN SCHEMA platform TO governance;
GRANT ALL ON ALL SEQUENCES IN SCHEMA platform TO governance;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For search

-- Audit function (idempotent via OR REPLACE)
CREATE OR REPLACE FUNCTION platform.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON SCHEMA platform IS 'Domain Development Lifecycle tables';

-- ============================================
-- Lookup Seed Data (ADR-015 konform)
-- ============================================

-- Domain: adr_uc_relationship (für ADRUseCaseLink)
INSERT INTO platform.lkp_domain (code, name, description)
VALUES ('adr_uc_relationship', 'ADR-UseCase Beziehungstyp', 'Typen der Beziehung zwischen ADR und Use Case')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order
FROM platform.lkp_domain d,
     (VALUES
         ('implements', 'Implements', 'Implementiert', 1),
         ('affects', 'Affects', 'Beeinflusst', 2),
         ('references', 'References', 'Referenziert', 3)
     ) AS v(code, name, name_de, sort_order)
WHERE d.code = 'adr_uc_relationship'
ON CONFLICT DO NOTHING;

-- Domain: review_entity_type (für Review und StatusHistory)
INSERT INTO platform.lkp_domain (code, name, description)
VALUES ('review_entity_type', 'Review Entity-Typ', 'Typen von Entities die reviewed werden können')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order
FROM platform.lkp_domain d,
     (VALUES
         ('business_case', 'Business Case', 'Business Case', 1),
         ('use_case', 'Use Case', 'Use Case', 2),
         ('adr', 'ADR', 'ADR', 3)
     ) AS v(code, name, name_de, sort_order)
WHERE d.code = 'review_entity_type'
ON CONFLICT DO NOTHING;

-- Domain: review_decision (für Review)
INSERT INTO platform.lkp_domain (code, name, description)
VALUES ('review_decision', 'Review Entscheidung', 'Mögliche Entscheidungen bei einem Review')
ON CONFLICT (code) DO NOTHING;

INSERT INTO platform.lkp_choice (domain_id, code, name, name_de, sort_order)
SELECT d.id, v.code, v.name, v.name_de, v.sort_order
FROM platform.lkp_domain d,
     (VALUES
         ('approved', 'Approved', 'Genehmigt', 1),
         ('rejected', 'Rejected', 'Abgelehnt', 2),
         ('changes_requested', 'Changes Requested', 'Änderungen erforderlich', 3)
     ) AS v(code, name, name_de, sort_order)
WHERE d.code = 'review_decision'
ON CONFLICT DO NOTHING;
```

### 5.5 Error Handling & Idempotenz

#### 5.5.1 Service Error Handling

| Komponente | Error Handling | Kein stilles Fallback |
|------------|----------------|----------------------|
| **InceptionService** | Explizite `InceptionError` Exception | LLM-Fehler → `raise`, kein Mock |
| **BusinessCaseService** | `ValidationError` mit Felddetails | Ungültiger Status → `raise` |
| **LookupService** | `LookupNotFoundError` | Fehlender Lookup → `raise`, kein Default |
| **MCP Tools** | JSON-RPC Error Codes | `-32602` für ungültige Parameter |

#### 5.5.2 Idempotenz-Garantien

| Operation | Idempotenz-Strategie |
|-----------|---------------------|
| `start_business_case` | Eindeutiger `session_id`, Duplikat-Check |
| `finalize_business_case` | Status-Check vor Transition |
| `docker compose up` | `--remove-orphans`, Container-Hash |
| `migrate` | Django Migrations sind idempotent |
| `init-db.sql` | `IF NOT EXISTS`, `OR REPLACE` |

#### 5.5.3 Python Service Pattern

```python
# services/business_case_service.py
"""
BusinessCaseService - CRUD und Workflow für Business Cases.

Error Handling:
- ValidationError: Ungültige Eingabedaten
- TransitionError: Ungültiger Status-Übergang
- NotFoundError: BC nicht gefunden

Idempotenz:
- create(): Prüft auf Duplikate via title+category
- transition(): Prüft aktuellen Status vor Änderung
"""
from dataclasses import dataclass
from typing import Optional
import logging

from django.db import transaction
from django.core.exceptions import ValidationError

from .exceptions import TransitionError, NotFoundError
from ..models import BusinessCase, StatusHistory

logger = logging.getLogger(__name__)


@dataclass
class OperationResult:
    """Standardisiertes Ergebnis für Service-Operationen."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class BusinessCaseService:
    """Service für Business Case Operationen."""
    
    # Explizite Status-Übergänge (kein "magisches" Verhalten)
    VALID_TRANSITIONS = {
        'draft': ['submitted'],
        'submitted': ['in_review', 'rejected'],
        'in_review': ['approved', 'rejected'],
        'rejected': ['draft'],  # Zurück zur Überarbeitung
        'approved': ['in_progress'],
        'in_progress': ['completed'],
        'completed': ['archived'],
    }
    
    @transaction.atomic
    def transition_status(
        self,
        bc_code: str,
        new_status: str,
        user_id: int,
        comment: Optional[str] = None
    ) -> OperationResult:
        """
        Führt Status-Übergang durch.
        
        Args:
            bc_code: Business Case Code (z.B. "BC-042")
            new_status: Ziel-Status
            user_id: User der die Transition durchführt
            comment: Optionaler Kommentar
            
        Returns:
            OperationResult mit success/error
            
        Raises:
            NotFoundError: BC existiert nicht
            TransitionError: Ungültiger Übergang
        """
        # 1. BC laden (expliziter Fehler wenn nicht gefunden)
        try:
            bc = BusinessCase.objects.select_for_update().get(code=bc_code)
        except BusinessCase.DoesNotExist:
            logger.error(f"BusinessCase not found: {bc_code}")
            raise NotFoundError(f"BusinessCase {bc_code} nicht gefunden")
        
        current_status = bc.status.code
        
        # 2. Transition validieren (kein stilles Fallback)
        valid_targets = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_targets:
            logger.warning(
                f"Invalid transition: {bc_code} {current_status} -> {new_status}"
            )
            raise TransitionError(
                f"Ungültiger Übergang: {current_status} → {new_status}. "
                f"Erlaubt: {valid_targets}"
            )
        
        # 3. Idempotenz: Bereits im Ziel-Status?
        if current_status == new_status:
            logger.info(f"BC {bc_code} already in status {new_status}")
            return OperationResult(
                success=True,
                data={'code': bc_code, 'status': new_status, 'changed': False}
            )
        
        # 4. Transition durchführen
        old_status = bc.status
        bc.status = self._get_status_choice(new_status)
        bc.save(update_fields=['status', 'updated_at'])
        
        # 5. Audit Trail
        StatusHistory.objects.create(
            content_object=bc,
            old_status=old_status,
            new_status=bc.status,
            changed_by_id=user_id,
            comment=comment or ''
        )
        
        logger.info(f"BC {bc_code} transitioned: {current_status} -> {new_status}")
        
        return OperationResult(
            success=True,
            data={'code': bc_code, 'status': new_status, 'changed': True}
        )
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
