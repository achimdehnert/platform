# ADR-013: Team Organization & MCP Ownership

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Scope** | core |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-012 (MCP Quality Standards), ADR-009 (Deployment Architecture) |

---

## 1. Executive Summary

Dieses ADR definiert die **Team-Organisation** und **Ownership-Struktur** für die BF Agent Platform mit zwei Teams. Wir etablieren ein **Hybrid-Modell** mit produktorientierter Primärverantwortung und einer rotierenden Platform Guild für shared Components.

**Kernprinzip:** *"Produkt-Fokus mit geteilter Platform-Verantwortung"*

---

## 2. Context

### 2.1 Aktuelle Situation

Die BF Agent Platform besteht aus:

**Produkte:**
| Produkt | Beschreibung | Deployment-Frequenz |
|---------|--------------|---------------------|
| BFAgent | AI Agent Application | ~5x/Tag |
| Travel-Beat | Travel Content Platform | ~10x/Tag |
| Risk-Hub | Risk Assessment | ~2x/Tag |
| CAD-Hub | CAD Processing | ~2x/Tag |
| PPTX-Hub | Presentation Generation | ~2x/Tag |

**MCP Server (14+):**
| Server | Status | Abhängigkeiten |
|--------|--------|----------------|
| llm_mcp | Production | Alle Produkte |
| bfagent_mcp | Production | BFAgent |
| bfagent_sqlite_mcp | Production | BFAgent |
| deployment_mcp | Production | Alle Produkte |
| research_mcp | Production | Alle Produkte |
| travel_mcp | Production | Travel-Beat |
| illustration_mcp | Production | Travel-Beat, BFAgent |
| book_writing_mcp | Production | Travel-Beat |
| german_tax_mcp | Beta | BFAgent |
| ifc_mcp | Beta | CAD-Hub |
| cad_mcp | Beta | CAD-Hub |
| dlm_mcp | Beta | Alle |
| physicals_mcp | Beta | CAD-Hub |

**Shared Components:**
- Platform Repository (CI/CD, Shared Packages)
- mcp-core Library (neu, ADR-012)
- Docs Infrastructure
- Monitoring & Observability

### 2.2 Team-Struktur

```
Aktuell: 2 Teams
├── Team A: ? Personen
└── Team B: ? Personen
```

### 2.3 Herausforderungen

| Problem | Impact | Häufigkeit |
|---------|--------|------------|
| **Unklare Ownership** | Shared Components werden vernachlässigt | Hoch |
| **Feature vs. Platform** | Platform-Arbeit blockiert Feature-Entwicklung | Mittel |
| **Wissens-Silos** | Nur eine Person kennt bestimmte MCP Server | Hoch |
| **Koordinationsaufwand** | Unklar wer was macht | Mittel |
| **Quality Gaps** | Unterschiedliche Standards pro Team | Mittel |

### 2.4 Anforderungen

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | Klare Ownership für alle Components | CRITICAL |
| R2 | Hohe Feature-Velocity bei Produkten | HIGH |
| R3 | Konsistente Platform-Qualität | HIGH |
| R4 | Wissensverteilung zwischen Teams | MEDIUM |
| R5 | Flexibilität bei Prioritätsänderungen | MEDIUM |
| R6 | Skalierbarkeit für Team-Wachstum | LOW |

---

## 3. Decision

### 3.1 Hybrid-Modell

Wir führen ein **Hybrid-Modell** ein mit:
1. **Produkt-Teams** (80% Zeit) - Fokus auf Features
2. **Platform Guild** (20% Zeit) - Shared Responsibility

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         TEAM ORGANIZATION                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                    ┌─────────────────────────────┐                       │
│                    │     🏛️ PLATFORM GUILD       │                       │
│                    │                             │                       │
│                    │  Rotating Members (20%)     │                       │
│                    │  • Quality Standards        │                       │
│                    │  • mcp-core Library         │                       │
│                    │  • Shared Infrastructure    │                       │
│                    │  • Cross-Team Coordination  │                       │
│                    │                             │                       │
│                    └──────────────┬──────────────┘                       │
│                                   │                                      │
│            ┌──────────────────────┼──────────────────────┐               │
│            │                      │                      │               │
│            ▼                      ▼                      ▼               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │  🤖 TEAM ALPHA  │    │  ✈️ TEAM BRAVO  │    │  📦 SHARED      │      │
│  │                 │    │                 │    │                 │      │
│  │  80% Product    │    │  80% Product    │    │  Owned by Guild │      │
│  │  20% Platform   │    │  20% Platform   │    │                 │      │
│  │                 │    │                 │    │  • mcp-core     │      │
│  │  Products:      │    │  Products:      │    │  • llm_mcp      │      │
│  │  • BFAgent      │    │  • Travel-Beat  │    │  • research_mcp │      │
│  │  • Risk-Hub     │    │  • PPTX-Hub     │    │  • deploy_mcp   │      │
│  │  • CAD-Hub      │    │                 │    │  • Platform CI  │      │
│  │                 │    │                 │    │                 │      │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Team Alpha: BFAgent & Industrial

**Mission:** Entwicklung und Wartung von BFAgent und industrienahen Produkten.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          TEAM ALPHA                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 PRIMARY RESPONSIBILITY (80% Zeit)                                   │
│  ═══════════════════════════════════                                     │
│                                                                          │
│  Products:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • BFAgent Application     - Features, Bug Fixes, Releases           ││
│  │ • Risk-Hub                - Risk Assessment Features                ││
│  │ • CAD-Hub                 - CAD Processing Features                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  MCP Servers (Primary Owner):                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Server              │ Status     │ Responsibility                   ││
│  ├─────────────────────┼────────────┼──────────────────────────────────┤│
│  │ bfagent_mcp         │ Production │ Full Ownership                   ││
│  │ bfagent_sqlite_mcp  │ Production │ Full Ownership                   ││
│  │ german_tax_mcp      │ Beta       │ Full Ownership, Quality Upgrade  ││
│  │ ifc_mcp             │ Beta       │ Full Ownership, Quality Upgrade  ││
│  │ cad_mcp             │ Beta       │ Full Ownership, Quality Upgrade  ││
│  │ physicals_mcp       │ Beta       │ Full Ownership                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🏗️ PLATFORM DUTY (20% Zeit)                                            │
│  ════════════════════════════                                            │
│                                                                          │
│  Responsibilities:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • mcp-core Library        - Development & Maintenance               ││
│  │ • CI/CD Workflows         - Reusable Workflows (ADR-009)            ││
│  │ • Quality Tooling         - Scorecard Scripts (ADR-012)             ││
│  │ • llm_mcp                 - Shared Server, Secondary Owner          ││
│  │ • deployment_mcp          - Shared Server, Primary Owner            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Key Metrics:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • BFAgent Deployment Success Rate      Target: >99%                 ││
│  │ • MCP Server Quality Score             Target: ≥80 (Grade B)        ││
│  │ • Beta → Production Upgrades           Target: 2/Quarter            ││
│  │ • Platform Contribution                Target: 20% Sprint Capacity  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Team Bravo: Travel-Beat & Content

**Mission:** Entwicklung und Wartung von Travel-Beat und content-orientierten Produkten.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          TEAM BRAVO                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 PRIMARY RESPONSIBILITY (80% Zeit)                                   │
│  ═══════════════════════════════════                                     │
│                                                                          │
│  Products:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Travel-Beat Application - Features, Content, Releases             ││
│  │ • PPTX-Hub                - Presentation Generation                 ││
│  │ • Docs Infrastructure     - Documentation Platform                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  MCP Servers (Primary Owner):                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Server              │ Status     │ Responsibility                   ││
│  ├─────────────────────┼────────────┼──────────────────────────────────┤│
│  │ travel_mcp          │ Production │ Full Ownership                   ││
│  │ illustration_mcp    │ Production │ Full Ownership                   ││
│  │ book_writing_mcp    │ Production │ Full Ownership                   ││
│  │ dlm_mcp             │ Beta       │ Full Ownership, Quality Upgrade  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🏗️ PLATFORM DUTY (20% Zeit)                                            │
│  ════════════════════════════                                            │
│                                                                          │
│  Responsibilities:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • MCP Quality Reviews     - Scorecard Reviews (ADR-012)             ││
│  │ • Documentation           - ADRs, Guides, API Docs                  ││
│  │ • Testing Infrastructure  - Test Fixtures, Mocks                    ││
│  │ • research_mcp            - Shared Server, Primary Owner            ││
│  │ • llm_mcp                 - Shared Server, Secondary Owner          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Key Metrics:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Travel-Beat Deployment Success Rate  Target: >99%                 ││
│  │ • MCP Server Quality Score             Target: ≥80 (Grade B)        ││
│  │ • Documentation Coverage               Target: 100% of MCP Servers  ││
│  │ • Platform Contribution                Target: 20% Sprint Capacity  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Platform Guild

**Mission:** Qualität und Konsistenz der shared Platform Components sicherstellen.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PLATFORM GUILD                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 MISSION                                                             │
│  ══════════                                                              │
│  Sicherstellung von Qualität, Konsistenz und Wartbarkeit der            │
│  shared Platform Components durch cross-funktionale Zusammenarbeit.     │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  👥 MEMBERSHIP                                                          │
│  ══════════════                                                          │
│                                                                          │
│  Struktur:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • 1 Person aus Team Alpha (rotierend)                               ││
│  │ • 1 Person aus Team Bravo (rotierend)                               ││
│  │ • Rotation: Alle 4 Wochen                                           ││
│  │ • Mindestens 1 Sprint Kontinuität                                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Zeitbudget:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • 20% der Arbeitszeit (~1 Tag/Woche)                                ││
│  │ • Feste Slots: Mittwoch für Guild-Arbeit                            ││
│  │ • Weekly Sync: 30min jeden Mittwoch                                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  📦 OWNED COMPONENTS                                                    │
│  ════════════════════                                                    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Component           │ Type        │ Responsibility                  ││
│  ├─────────────────────┼─────────────┼─────────────────────────────────┤│
│  │ mcp-core            │ Library     │ Development, Releases           ││
│  │ llm_mcp             │ MCP Server  │ Quality, Maintenance            ││
│  │ research_mcp        │ MCP Server  │ Quality, Maintenance            ││
│  │ deployment_mcp      │ MCP Server  │ Quality, Maintenance            ││
│  │ Platform CI/CD      │ Workflows   │ Reusable Workflows              ││
│  │ Quality Tooling     │ Scripts     │ Scorecard, Checks               ││
│  │ ADR Process         │ Governance  │ Reviews, Standards              ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  📋 RESPONSIBILITIES                                                    │
│  ════════════════════                                                    │
│                                                                          │
│  Weekly:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Guild Sync Meeting (30min)                                        ││
│  │ • Review offener Platform PRs                                       ││
│  │ • Triage Platform Issues                                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Monthly:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • MCP Quality Review (alle Server scannen)                          ││
│  │ • Dependency Updates (shared packages)                              ││
│  │ • Platform Health Report                                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Quarterly:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Platform Roadmap Planning                                         ││
│  │ • ADR Review & Cleanup                                              ││
│  │ • Quality Standards Update                                          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🚦 DECISION AUTHORITY                                                  │
│  ══════════════════════                                                  │
│                                                                          │
│  Guild entscheidet:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ mcp-core API Design                                              ││
│  │ ✅ Shared MCP Server Changes                                        ││
│  │ ✅ Quality Standards (ADR-012)                                      ││
│  │ ✅ CI/CD Workflow Changes                                           ││
│  │ ✅ Breaking Changes in Shared Components                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Guild berät, Team entscheidet:                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ⚠️ Team-owned MCP Server Architecture                               ││
│  │ ⚠️ Product-specific Technical Decisions                             ││
│  │ ⚠️ Team-internal Tooling                                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. MCP Server Ownership Matrix

### 4.1 Vollständige Ownership-Tabelle

| MCP Server | Primary Owner | Secondary | Guild | Status | Quality Target |
|------------|---------------|-----------|-------|--------|----------------|
| **llm_mcp** | Guild | Alpha, Bravo | ✅ | Production | A (90+) |
| **research_mcp** | Guild (Bravo Lead) | Alpha | ✅ | Production | A (90+) |
| **deployment_mcp** | Guild (Alpha Lead) | Bravo | ✅ | Production | A (90+) |
| **bfagent_mcp** | Alpha | — | — | Production | B (80+) |
| **bfagent_sqlite_mcp** | Alpha | — | — | Production | B (80+) |
| **travel_mcp** | Bravo | — | — | Production | B (80+) |
| **illustration_mcp** | Bravo | Alpha | — | Production | B (80+) |
| **book_writing_mcp** | Bravo | — | — | Production | B (80+) |
| **german_tax_mcp** | Alpha | — | — | Beta | C→B (70→80) |
| **ifc_mcp** | Alpha | — | — | Beta | C→B (70→80) |
| **cad_mcp** | Alpha | — | — | Beta | C→B (70→80) |
| **dlm_mcp** | Bravo | Alpha | — | Beta | C→B (70→80) |
| **physicals_mcp** | Alpha | — | — | Beta | C→B (70→80) |
| **mcp-core** | Guild | Alpha, Bravo | ✅ | New | A (90+) |

### 4.2 Ownership-Regeln

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       OWNERSHIP RULES                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📌 PRIMARY OWNER                                                       │
│  ══════════════════                                                      │
│  • Verantwortlich für: Features, Bugs, Quality, Releases                │
│  • Entscheidet über: Architektur, Roadmap, Breaking Changes             │
│  • Pflicht: Mindestens 1 Review pro Woche                               │
│  • Eskalation bei: Blocker, Security Issues                             │
│                                                                          │
│  📌 SECONDARY OWNER                                                     │
│  ════════════════════                                                    │
│  • Verantwortlich für: Review-Backup, Knowledge Sharing                 │
│  • Kann: PRs reviewen, kleine Fixes machen                              │
│  • Pflicht: Wissen aktuell halten (min. 1x/Monat Code Review)           │
│  • Springt ein bei: Urlaub, Krankheit des Primary                       │
│                                                                          │
│  📌 GUILD OWNERSHIP                                                     │
│  ════════════════════                                                    │
│  • Verantwortlich für: Shared Components, Cross-Team Concerns           │
│  • Entscheidet über: API Design, Breaking Changes, Standards            │
│  • Pflicht: Weekly Sync, Monthly Quality Review                         │
│  • Alle Changes: Require 1 Approval aus jedem Team                      │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🔄 OWNERSHIP TRANSFER                                                  │
│  ══════════════════════                                                  │
│                                                                          │
│  Wann Transfer?                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Produkt-Zuordnung ändert sich                                     ││
│  │ • Team-Mitglied verlässt Team                                       ││
│  │ • Bessere Expertise in anderem Team                                 ││
│  │ • Quarterly Review ergibt Rebalancing-Bedarf                        ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Transfer-Prozess:                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 1. Antrag in Guild Meeting                                          ││
│  │ 2. Knowledge Transfer Session (min. 2h)                             ││
│  │ 3. Pair Programming Phase (1-2 Wochen)                              ││
│  │ 4. Shadowing Phase (1 Woche)                                        ││
│  │ 5. Formaler Ownership-Wechsel (Update dieser ADR)                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Sprint-Rhythmus

### 5.1 Sprint-Struktur (2 Wochen)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       SPRINT RHYTHM (2 Weeks)                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  WEEK 1                                                                 │
│  ══════                                                                  │
│                                                                          │
│  Mo │ Tu │ We │ Th │ Fr                                                 │
│  ───┼────┼────┼────┼────                                                 │
│  SP │ 🚀 │ 🏗️ │ 🚀 │ 🚀    SP = Sprint Planning                        │
│     │    │    │    │       🚀 = Product Work (80%)                       │
│     │    │    │    │       🏗️ = Platform Day (20%)                       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Mittwoch (Platform Day):                                            ││
│  │ • 09:00 - 09:30  Guild Sync Meeting                                 ││
│  │ • 09:30 - 12:00  Platform Work (mcp-core, CI/CD, Quality)           ││
│  │ • 13:00 - 17:00  Platform Work / Cross-Team Collaboration           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  WEEK 2                                                                 │
│  ══════                                                                  │
│                                                                          │
│  Mo │ Tu │ We │ Th │ Fr                                                 │
│  ───┼────┼────┼────┼────                                                 │
│  🚀 │ 🚀 │ 🏗️ │ 🚀 │ RE    RE = Retro, Review, Release                 │
│     │    │    │    │                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Freitag (Release Day):                                              ││
│  │ • 09:00 - 10:00  Sprint Review (Demo)                               ││
│  │ • 10:00 - 11:00  Retrospective                                      ││
│  │ • 11:00 - 12:00  Release Preparation                                ││
│  │ • 14:00          Production Release (wenn bereit)                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  ZEITVERTEILUNG PRO SPRINT                                              │
│                                                                          │
│  Team Alpha:                    Team Bravo:                             │
│  ┌──────────────────────┐      ┌──────────────────────┐                 │
│  │ Product Work: 64h    │      │ Product Work: 64h    │                 │
│  │ Platform Work: 16h   │      │ Platform Work: 16h   │                 │
│  │ ────────────────     │      │ ────────────────     │                 │
│  │ Total: 80h (2 Weeks) │      │ Total: 80h (2 Weeks) │                 │
│  └──────────────────────┘      └──────────────────────┘                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Platform Day Aktivitäten

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    PLATFORM DAY ACTIVITIES                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🔵 TEAM ALPHA FOCUS                                                    │
│  ════════════════════                                                    │
│                                                                          │
│  Primary:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • mcp-core Development                                              ││
│  │   - New features, bug fixes, releases                               ││
│  │   - API design discussions                                          ││
│  │                                                                     ││
│  │ • CI/CD Workflows                                                   ││
│  │   - Reusable workflow improvements                                  ││
│  │   - Build optimization                                              ││
│  │                                                                     ││
│  │ • deployment_mcp Maintenance                                        ││
│  │   - Quality improvements                                            ││
│  │   - New deployment features                                         ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Secondary:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Review PRs from Team Bravo                                        ││
│  │ • llm_mcp quality improvements                                      ││
│  │ • Platform issue triage                                             ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🟢 TEAM BRAVO FOCUS                                                    │
│  ════════════════════                                                    │
│                                                                          │
│  Primary:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • MCP Quality Reviews                                               ││
│  │   - Run scorecard on owned servers                                  ││
│  │   - Fix quality issues                                              ││
│  │                                                                     ││
│  │ • Documentation                                                     ││
│  │   - Update MCP server docs                                          ││
│  │   - Write/review ADRs                                               ││
│  │                                                                     ││
│  │ • research_mcp Maintenance                                          ││
│  │   - Quality improvements                                            ││
│  │   - New research features                                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Secondary:                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Review PRs from Team Alpha                                        ││
│  │ • Testing infrastructure                                            ││
│  │ • llm_mcp quality improvements                                      ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Communication & Coordination

### 6.1 Meeting-Struktur

| Meeting | Frequenz | Dauer | Teilnehmer | Zweck |
|---------|----------|-------|------------|-------|
| **Guild Sync** | Wöchentlich (Mi) | 30min | Guild Members | Platform Coordination |
| **Team Standup** | Täglich | 15min | Team | Daily Sync |
| **Sprint Planning** | Bi-Weekly (Mo) | 2h | Team | Sprint Planning |
| **Sprint Review** | Bi-Weekly (Fr) | 1h | Alle | Demo |
| **Retro** | Bi-Weekly (Fr) | 1h | Team | Improvement |
| **Cross-Team Sync** | Monatlich | 1h | Alle | Alignment |
| **Platform Review** | Monatlich | 1h | Guild + Leads | Quality Review |

### 6.2 Kommunikationskanäle

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION CHANNELS                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Slack Channels:                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ #team-alpha          - Team Alpha internal                          ││
│  │ #team-bravo          - Team Bravo internal                          ││
│  │ #platform-guild      - Guild discussions, cross-team                ││
│  │ #mcp-hub             - MCP Server updates, issues                   ││
│  │ #deployments         - Deployment notifications                     ││
│  │ #incidents           - Production incidents                         ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  GitHub:                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • PRs: Tag relevant team (@team-alpha, @team-bravo)                 ││
│  │ • Issues: Use labels (team:alpha, team:bravo, guild)                ││
│  │ • Discussions: For RFCs, ADRs, Design Decisions                     ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Escalation Path:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 1. Team-internal                                                    ││
│  │ 2. Cross-team (Guild oder direkt)                                   ││
│  │ 3. Tech Lead                                                        ││
│  │ 4. Management                                                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Quality & Performance Metrics

### 7.1 Team Metrics

| Metric | Alpha Target | Bravo Target | Messung |
|--------|--------------|--------------|---------|
| **Deployment Success** | >99% | >99% | GitHub Actions |
| **MCP Quality Score** | Avg ≥80 | Avg ≥80 | Scorecard |
| **Platform Contribution** | 20% Zeit | 20% Zeit | Sprint Tracking |
| **PR Review Time** | <24h | <24h | GitHub |
| **Test Coverage** | ≥80% | ≥80% | Codecov |

### 7.2 Guild Metrics

| Metric | Target | Messung |
|--------|--------|---------|
| **Shared MCP Quality** | ≥90 (Grade A) | Scorecard |
| **mcp-core Adoption** | 100% Server | Code Analysis |
| **Documentation Coverage** | 100% | Doc Check |
| **Platform Incidents** | <2/Month | Incident Tracking |
| **ADR Compliance** | 100% | ADR Review |

---

## 8. Implementation Plan

### Phase 1: Foundation (Woche 1)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Teams formieren | Management | Team-Listen |
| Slack Channels erstellen | Admin | Channels |
| GitHub Teams einrichten | Admin | @team-alpha, @team-bravo |
| CODEOWNERS aktualisieren | Guild | CODEOWNERS Files |
| Kickoff Meeting | Alle | Alignment |

### Phase 2: Ownership Transfer (Woche 2-3)

| Task | Owner | Deliverable |
|------|-------|-------------|
| MCP Server Ownership zuweisen | Guild | Ownership Matrix |
| Knowledge Transfer Sessions | Teams | Dokumentation |
| Handover Checklist pro Server | Teams | Checklists |
| Secondary Owner Briefings | Teams | Cross-Training |

### Phase 3: Rhythm Etablieren (Woche 4-6)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Erster Platform Day | Guild | Platform Work |
| Guild Sync etablieren | Guild | Weekly Meeting |
| Sprint Rhythm starten | Teams | Sprints |
| Metrics Dashboard | Guild | Monitoring |

### Phase 4: Optimize (Ongoing)

| Task | Owner | Frequency |
|------|-------|-----------|
| Retrospektive zur Teamstruktur | Alle | Monatlich |
| Ownership Review | Guild | Quarterly |
| Process Improvements | Guild | Continuous |

---

## 9. Consequences

### 9.1 Positive

| Benefit | Impact |
|---------|--------|
| **Klare Ownership** | Jeder weiß wer verantwortlich ist |
| **Feature Velocity** | 80% fokussierte Produktarbeit |
| **Platform Quality** | 20% dedizierte Platform-Zeit |
| **Wissensverteilung** | Secondary Owners, Guild Rotation |
| **Skalierbarkeit** | Modell funktioniert mit mehr Teams |
| **Flexibilität** | Platform Day kann verschoben werden |

### 9.2 Negative

| Drawback | Mitigation |
|----------|------------|
| Context Switching | Fester Platform Day (Mittwoch) |
| 20% "Overhead" | Investition zahlt sich aus durch Qualität |
| Koordinationsaufwand | Klare Regeln, feste Meetings |
| Guild kann Bottleneck werden | Zwei-Team Approval Regel |

### 9.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Platform Day wird gestrichen | Medium | High | Commitment in Sprint Planning |
| Teams ignorieren Guild | Low | Medium | Management Support |
| Ownership unklar bei Edge Cases | Medium | Low | Entscheidung durch Guild |
| Rotation funktioniert nicht | Low | Medium | Mindestens 1 Sprint Kontinuität |

---

## 10. Success Metrics (6 Monate)

| Metric | Current | Target |
|--------|---------|--------|
| MCP Server Avg Quality Score | ~60? | ≥80 |
| Platform Incidents/Month | Unknown | <2 |
| Cross-Team PRs | Unknown | ≥10/Sprint |
| Knowledge Bus Factor | 1? | ≥2 |
| Feature Delivery | Baseline | +20% |
| Developer Satisfaction | Baseline | Improved |

---

## 11. Open Questions

| # | Question | Decision Needed By |
|---|----------|-------------------|
| 1 | Wie groß sind die Teams genau? | Sofort |
| 2 | Wer sind die initialen Guild Members? | Woche 1 |
| 3 | Wie wird Platform-Arbeit im Sprint geplant? | Woche 1 |
| 4 | Welcher Tag ist Platform Day? (Vorschlag: Mi) | Woche 1 |
| 5 | Wie werden Konflikte zwischen Teams gelöst? | Woche 2 |

---

## 12. References

- [ADR-012: MCP Server Quality Standards](./ADR-012-mcp-quality-standards.md)
- [ADR-009: Deployment Architecture](./ADR-009-deployment-architecture.md)
- [Team Topologies (Book)](https://teamtopologies.com/)
- [Spotify Squad Model](https://www.atlassian.com/agile/agile-at-scale/spotify)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-03 | Achim Dehnert | Initial version |
