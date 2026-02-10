# ADR-014: AI-Native Development Teams

| Metadata | Value |
|----------|-------|
| **Status** | Accepted |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Scope** | core |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-012 (MCP Quality), ADR-013 (Team Organization) |

---

## 1. Executive Summary

Dieses ADR definiert ein **AI-Native Development Model** für die BF Agent Platform, bei dem AI-Agenten (Claude Opus 4.5, Sonnet 4.5, Haiku 4.5) die Entwicklungsarbeit übernehmen, koordiniert durch einen menschlichen Architekten. Das System verwendet ein **5-Level Approval Gate System** für sichere Human-in-the-Loop Kontrolle und wird über **Windsurf + MCP Server + GitHub Actions** orchestriert.

**Kernprinzip:** *"AI führt aus, Mensch entscheidet und überwacht."*

---

## 2. Context

### 2.1 Vision

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    AI-NATIVE DEVELOPMENT VISION                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  HEUTE                              ZIEL                                │
│  ═════                              ════                                │
│                                                                          │
│  👤 Human writes code               👤 Human architects & approves      │
│  🤖 AI assists                      🤖 AI implements & executes         │
│                                                                          │
│  ┌─────────────────────┐           ┌─────────────────────┐             │
│  │ Human: 80% effort   │    →      │ Human: 20% effort   │             │
│  │ AI: 20% assist      │           │ AI: 80% execution   │             │
│  └─────────────────────┘           └─────────────────────┘             │
│                                                                          │
│  Benefits:                                                              │
│  • 5-10x faster feature delivery                                        │
│  • Consistent code quality (ADR-012 enforced)                           │
│  • 24/7 development capacity                                            │
│  • Human focus on strategy & architecture                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Anforderungen

| ID | Anforderung | Priorität |
|----|-------------|-----------|
| R1 | AI-Agenten können autonom Code entwickeln | CRITICAL |
| R2 | Mensch behält Kontrolle über kritische Entscheidungen | CRITICAL |
| R3 | Klare Verantwortlichkeiten pro AI-Team | HIGH |
| R4 | Kosteneffiziente Modell-Auswahl | HIGH |
| R5 | Vollständiges Audit-Trail | HIGH |
| R6 | Integration in bestehende Tools (Windsurf, GitHub) | HIGH |
| R7 | Skalierbar für wachsende Codebasis | MEDIUM |

### 2.3 Technologie-Stack

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| **Primary IDE** | Windsurf (Cascade) | Mensch-AI Interaktion |
| **AI Models** | Claude Opus/Sonnet/Haiku 4.5 | Entwicklung & Review |
| **Orchestration** | orchestrator_mcp | Agent-Koordination |
| **CI/CD** | GitHub Actions | Automation & Gates |
| **Communication** | GitHub Notifications | Alerts (Slack: Future) |
| **Version Control** | GitHub | Code & PRs |

---

## 3. Decision

### 3.1 Considered Alternatives

| Option | Beschreibung | Bewertung | Warum verworfen/gewählt |
|--------|--------------|-----------|-------------------------|
| **A: Status Quo** | Human schreibt, AI assistiert | ❌ | Zu langsam, nicht skalierbar |
| **B: Single-Agent** | Ein AI-Modell für alles | ❌ | Keine Spezialisierung, hohe Kosten |
| **C: Fully Autonomous** | AI ohne Approval Gates | ❌ | Zu riskant, keine Kontrolle |
| **D: Hybrid Model** ✅ | AI-Teams + Gate System | ✅ GEWÄHLT | Balance: Speed + Control |

**Rationale für Option D:**
- Ermöglicht schnelle Iteration bei niedrigem Risiko
- Gate-System skaliert mit Vertrauen
- Kostenoptimierung durch Model-Tiering
- Human bleibt in kritischen Entscheidungen

### 3.2 AI-Native Development Model

Wir etablieren ein **Hybrid Human-AI Development Model** mit:

1. **AI Agent Hierarchy** - Opus (Lead), Sonnet (Implement), Haiku (Tasks)
2. **Two AI Teams** - Alpha (BFAgent/Platform), Bravo (Travel-Beat/Content)
3. **5-Level Approval Gates** - Von autonom bis human-initiated
4. **MCP-based Orchestration** - Zentrale Koordination
5. **Human Oversight** - Architekt mit Veto-Recht

```
┌──────────────────────────────────────────────────────────────────────────┐
│                 AI-NATIVE DEVELOPMENT ARCHITECTURE                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      👤 HUMAN OVERSIGHT                          │    │
│  │                         (Achim)                                  │    │
│  │                                                                  │    │
│  │   Role: Architect, Final Approver, Strategy                      │    │
│  │   Tools: Windsurf, GitHub, Slack                                 │    │
│  │   Time: ~20% (Review, Approve, Architect)                        │    │
│  │                                                                  │    │
│  └──────────────────────────────┬───────────────────────────────────┘    │
│                                 │                                        │
│                                 ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    ORCHESTRATION LAYER                           │   │
│  │                                                                  │   │
│  │   ┌────────────────────┐      ┌────────────────────┐            │   │
│  │   │   Windsurf         │      │   GitHub Actions   │            │   │
│  │   │   (Interactive)    │◄────►│   (Automated)      │            │   │
│  │   └─────────┬──────────┘      └─────────┬──────────┘            │   │
│  │             │                           │                        │   │
│  │             └───────────┬───────────────┘                        │   │
│  │                         │                                        │   │
│  │                         ▼                                        │   │
│  │             ┌───────────────────────┐                            │   │
│  │             │   orchestrator_mcp    │                            │   │
│  │             │                       │                            │   │
│  │             │ • Agent Selection     │                            │   │
│  │             │ • Task Routing        │                            │   │
│  │             │ • Gate Enforcement    │                            │   │
│  │             │ • Cost Tracking       │                            │   │
│  │             │ • Audit Logging       │                            │   │
│  │             └───────────┬───────────┘                            │   │
│  │                         │                                        │   │
│  └─────────────────────────┼────────────────────────────────────────┘   │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      AI AGENT LAYER                              │   │
│  │                                                                  │   │
│  │   ┌──────────────────────────────────────────────────────────┐  │   │
│  │   │              🏗️ AI ARCHITECT (Opus 4.5)                   │  │   │
│  │   │                                                          │  │   │
│  │   │  • Technical Vision & Decisions                          │  │   │
│  │   │  • ADR Creation & Review                                 │  │   │
│  │   │  • Cross-Team Coordination                               │  │   │
│  │   │  • Complex Problem Solving                               │  │   │
│  │   │  • Code Review (Critical)                                │  │   │
│  │   └──────────────────────────────────────────────────────────┘  │   │
│  │                            │                                     │   │
│  │          ┌─────────────────┴─────────────────┐                   │   │
│  │          │                                   │                   │   │
│  │          ▼                                   ▼                   │   │
│  │   ┌─────────────────────┐         ┌─────────────────────┐       │   │
│  │   │ 🤖 TEAM ALPHA       │         │ ✈️ TEAM BRAVO       │       │   │
│  │   │    (Opus 4.5)       │         │    (Opus 4.5)       │       │   │
│  │   │                     │         │                     │       │   │
│  │   │ Domain:             │         │ Domain:             │       │   │
│  │   │ • BFAgent           │         │ • Travel-Beat       │       │   │
│  │   │ • Risk-Hub          │         │ • PPTX-Hub          │       │   │
│  │   │ • CAD-Hub           │         │ • Content MCPs      │       │   │
│  │   │ • Platform MCPs     │         │                     │       │   │
│  │   │                     │         │                     │       │   │
│  │   │ ┌─────────────────┐ │         │ ┌─────────────────┐ │       │   │
│  │   │ │⚡Sonnet (Impl)  │ │         │ │⚡Sonnet (Impl)  │ │       │   │
│  │   │ └─────────────────┘ │         │ └─────────────────┘ │       │   │
│  │   │ ┌─────────────────┐ │         │ ┌─────────────────┐ │       │   │
│  │   │ │🚀Haiku (Tasks)  │ │         │ │🚀Haiku (Tasks)  │ │       │   │
│  │   │ └─────────────────┘ │         │ └─────────────────┘ │       │   │
│  │   └─────────────────────┘         └─────────────────────┘       │   │
│  │                                                                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. AI Agent Architecture

### 4.1 Model Hierarchy (Windsurf-Optimiert)

**Strategie:** Windsurf-native Modelle für 90% der Tasks, Claude Opus 4.5 (Thinking) für komplexe Architektur.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       AI MODEL HIERARCHY                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🧠 TIER 1: CLAUDE OPUS 4.5 (THINKING) - "The Architect"                │
│  ═══════════════════════════════════════════════════════                 │
│                                                                          │
│  Access: Windsurf BYOK (Individual) oder via Credits                    │
│  Cost: $5/1M input, $25/1M output tokens (API)                          │
│  Extended Thinking: Aktiviert für tiefes Reasoning                       │
│                                                                          │
│  Use Cases (~5% der Tasks):                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ Architecture decisions (ADRs)                                    ││
│  │ ✅ Complex problem decomposition                                    ││
│  │ ✅ Cross-component integration design                               ││
│  │ ✅ Security-sensitive reviews                                       ││
│  │ ✅ Breaking change planning                                         ││
│  │ ✅ Edge case analysis                                               ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Trigger: "architecture", "security", "breaking", "design", "strategy"  │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  ⚡ TIER 2: SWE-1.5 - "The Implementer" (PRIMARY)                       │
│  ════════════════════════════════════════════════                        │
│                                                                          │
│  Access: Windsurf Native (inkludiert in Pro/Teams)                      │
│  Speed: 13x schneller als Claude 4.5                                    │
│  Performance: Near Claude 4.5-Level                                     │
│                                                                          │
│  Use Cases (~90% der Tasks):                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ Feature implementation                                           ││
│  │ ✅ Bug fixes (alle Komplexitätsstufen)                              ││
│  │ ✅ Code refactoring                                                 ││
│  │ ✅ API implementation                                               ││
│  │ ✅ Code reviews                                                     ││
│  │ ✅ MCP server implementation                                        ││
│  │ ✅ Integration work                                                 ││
│  │ ✅ Test generation                                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Default für: Alle Standard-Entwicklungsaufgaben                        │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  🚀 TIER 3: GPT-5-2 (LOW REASONING) - "Quick Tasks"                     │
│  ═══════════════════════════════════════════════════                     │
│                                                                          │
│  Access: Windsurf Credits                                               │
│  Mode: Low Reasoning (schneller, günstiger)                             │
│  Qualität: Besser als Llama für strukturierte Tasks                     │
│                                                                          │
│  Use Cases (~5% der Tasks):                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ Documentation lookup                                             ││
│  │ ✅ Simple questions                                                 ││
│  │ ✅ Boilerplate generation                                           ││
│  │ ✅ Changelog drafts                                                 ││
│  │ ✅ Quick explanations                                               ││
│  │ ✅ Code formatting                                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Trigger: "quick", "simple", "explain", "format"                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.1.1 Model Access Configuration

> **Hinweis:** BYOK (Bring Your Own Key) ist für Teams/Enterprise-Pläne NICHT verfügbar.
> Claude-Modelle werden über Windsurf Credits abgerechnet.

```yaml
# Windsurf Model Strategy (Teams/Enterprise)
models:
  primary:
    name: "SWE-1.5"
    access: "windsurf-native"
    cost: "included in subscription"
    usage: "90%"
    
  secondary:
    name: "Claude Opus 4 (Thinking)"
    access: "windsurf-credits"  # NICHT BYOK für Teams!
    cost: "credits-based"
    usage: "5%"
    triggers:
      - "architecture"
      - "security" 
      - "breaking"
      - "design"
      - "strategy"
      - "adr"
    
  tertiary:
    name: "GPT-5-2 (Low Reasoning)"
    access: "windsurf-credits"
    cost: "credits-based (günstig)"
    usage: "5%"
    triggers:
      - "quick"
      - "simple"
      - "explain"
      - "format"
```

### 4.1.2 Model-Wechsel in Windsurf

Um das Model zu wechseln: Dropdown unter dem Prompt-Eingabefeld → Model auswählen.

| Situation | Wähle |
|-----------|-------|
| Standard-Entwicklung | SWE-1.5 (default) |
| Architektur-Entscheidung | Claude Opus 4 (Thinking) |
| Schnelle Frage / Formatierung | GPT-5-2 (Low Reasoning) |

### 4.2 Model Selection Matrix

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    MODEL SELECTION DECISION TREE                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                            New Task                                      │
│                               │                                          │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │ Is it architecture  │                               │
│                    │ or cross-cutting?   │                               │
│                    └──────────┬──────────┘                               │
│                               │                                          │
│              YES ◄────────────┴────────────► NO                          │
│               │                              │                           │
│               ▼                              ▼                           │
│        ┌─────────────┐            ┌─────────────────────┐               │
│        │ 🧠 OPUS     │            │ Is it implementation │               │
│        │             │            │ or bug fix?          │               │
│        └─────────────┘            └──────────┬──────────┘               │
│                                              │                           │
│                         YES ◄────────────────┴───────────► NO            │
│                          │                                 │             │
│                          ▼                                 ▼             │
│                   ┌─────────────┐              ┌─────────────────────┐  │
│                   │ Complex or  │              │ Tests, docs, or     │  │
│                   │ security?   │              │ simple tasks?       │  │
│                   └──────┬──────┘              └──────────┬──────────┘  │
│                          │                                │              │
│         YES ◄────────────┴────► NO              YES ◄─────┴─────► NO    │
│          │                      │                │                │     │
│          ▼                      ▼                ▼                ▼     │
│   ┌─────────────┐       ┌─────────────┐  ┌─────────────┐  ┌───────────┐│
│   │ 🧠 OPUS     │       │ ⚡ SONNET   │  │ 🚀 HAIKU    │  │ ⚡ SONNET ││
│   │ (Security)  │       │ (Standard)  │  │ (Bulk)      │  │ (Default) ││
│   └─────────────┘       └─────────────┘  └─────────────┘  └───────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  COST OPTIMIZATION RULES:                                               │
│                                                                          │
│  1. Default to lowest capable tier                                      │
│  2. Escalate only when needed                                           │
│  3. Batch similar tasks for Haiku                                       │
│  4. Use Opus sparingly (architecture, security, complex)                │
│  5. Cache common patterns/responses                                     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. AI Team Structure

### 5.1 Team Alpha: BFAgent & Platform

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          🤖 TEAM ALPHA                                   │
│                     "Agent & Platform Specialists"                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 MISSION                                                             │
│  ══════════                                                              │
│  Entwicklung und Wartung von BFAgent, industriellen Anwendungen,        │
│  und der Platform-Infrastruktur.                                        │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📦 DOMAIN OWNERSHIP                                                    │
│                                                                          │
│  Applications:                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • BFAgent          - Main agent application                         ││
│  │ • Risk-Hub         - Risk assessment tools                          ││
│  │ • CAD-Hub          - CAD processing                                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  MCP Servers:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Server              │ Status     │ Quality Target                   ││
│  │ ────────────────────┼────────────┼────────────────────────────────  ││
│  │ bfagent_mcp         │ Production │ Grade B (80+)                    ││
│  │ bfagent_sqlite_mcp  │ Production │ Grade B (80+)                    ││
│  │ deployment_mcp      │ Production │ Grade A (90+)                    ││
│  │ german_tax_mcp      │ Beta       │ Grade C→B                        ││
│  │ ifc_mcp             │ Beta       │ Grade C→B                        ││
│  │ cad_mcp             │ Beta       │ Grade C→B                        ││
│  │ physicals_mcp       │ Beta       │ Grade C→B                        ││
│  │ llm_mcp             │ Production │ Grade A (90+) - Shared           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Platform Responsibilities:                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • mcp-core library development                                      ││
│  │ • CI/CD workflow maintenance                                        ││
│  │ • Deployment automation                                             ││
│  │ • Infrastructure as Code                                            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  🔧 AGENT CONFIGURATION                                                 │
│                                                                          │
│  Lead Agent:     Claude Opus 4.5 (Team Alpha Lead)                      │
│  Implementers:   Claude Sonnet 4.5 (2-3 parallel)                       │
│  Workers:        Claude Haiku 4.5 (on-demand)                           │
│                                                                          │
│  Specializations:                                                       │
│  • Django/Python backend                                                │
│  • Database design (PostgreSQL)                                         │
│  • Agent architectures                                                  │
│  • Infrastructure automation                                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Team Bravo: Travel-Beat & Content

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          ✈️ TEAM BRAVO                                   │
│                     "Content & Experience Specialists"                   │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 MISSION                                                             │
│  ══════════                                                              │
│  Entwicklung und Wartung von Travel-Beat, Content-Generation,           │
│  und kreativen Anwendungen.                                             │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📦 DOMAIN OWNERSHIP                                                    │
│                                                                          │
│  Applications:                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Travel-Beat      - Travel content platform                        ││
│  │ • PPTX-Hub         - Presentation generation                        ││
│  │ • Docs             - Documentation infrastructure                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  MCP Servers:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Server              │ Status     │ Quality Target                   ││
│  │ ────────────────────┼────────────┼────────────────────────────────  ││
│  │ travel_mcp          │ Production │ Grade B (80+)                    ││
│  │ illustration_mcp    │ Production │ Grade B (80+)                    ││
│  │ book_writing_mcp    │ Production │ Grade B (80+)                    ││
│  │ research_mcp        │ Production │ Grade A (90+)                    ││
│  │ dlm_mcp             │ Beta       │ Grade C→B                        ││
│  │ llm_mcp             │ Production │ Grade A (90+) - Shared           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Content Responsibilities:                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • AI image generation workflows                                     ││
│  │ • Content pipelines                                                 ││
│  │ • Documentation standards                                           ││
│  │ • User experience                                                   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  🔧 AGENT CONFIGURATION                                                 │
│                                                                          │
│  Lead Agent:     Claude Opus 4.5 (Team Bravo Lead)                      │
│  Implementers:   Claude Sonnet 4.5 (2-3 parallel)                       │
│  Workers:        Claude Haiku 4.5 (on-demand)                           │
│                                                                          │
│  Specializations:                                                       │
│  • Content generation                                                   │
│  • API integrations (OpenAI, image services)                            │
│  • User-facing features                                                 │
│  • Documentation & guides                                               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 5.3 AI Architect (Cross-Team)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          🏗️ AI ARCHITECT                                │
│                     "Technical Vision & Coordination"                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🎯 MISSION                                                             │
│  ══════════                                                              │
│  Sicherstellung der technischen Konsistenz, Architektur-Entscheidungen, │
│  und Koordination zwischen AI-Teams.                                    │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📋 RESPONSIBILITIES                                                    │
│                                                                          │
│  Architecture:                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Technical vision and roadmap                                      ││
│  │ • ADR creation and review                                           ││
│  │ • Breaking change coordination                                      ││
│  │ • Cross-component integration design                                ││
│  │ • Technology selection                                              ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Code Review:                                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Critical path reviews (mcp-core, shared)                          ││
│  │ • Security-sensitive code                                           ││
│  │ • Architecture alignment                                            ││
│  │ • Quality standards enforcement (ADR-012)                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Coordination:                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Task decomposition for teams                                      ││
│  │ • Cross-team dependency management                                  ││
│  │ • Conflict resolution                                               ││
│  │ • Knowledge sharing                                                 ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📦 SHARED COMPONENT OWNERSHIP                                          │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • mcp-core library                                                  ││
│  │ • llm_mcp (shared between teams)                                    ││
│  │ • Platform CI/CD workflows                                          ││
│  │ • Quality tooling (scorecards, checks)                              ││
│  │ • ADR repository                                                    ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  🔧 AGENT CONFIGURATION                                                 │
│                                                                          │
│  Model: Claude Opus 4.5 (always highest tier for architecture)          │
│  Temperature: 0.3 (deterministic for consistency)                       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 6. System Prompts

### 6.1 AI Architect System Prompt

```markdown
# AI Architect System Prompt

## Identity
You are the **Senior AI Architect** for the BF Agent Platform. You are responsible 
for technical vision, architecture decisions, and ensuring consistency across all 
components and AI teams.

## Core Responsibilities
1. **Architecture Decisions** - Evaluate approaches, ensure consistency
2. **ADR Management** - Create, review, and maintain Architecture Decision Records
3. **Code Review** - Review critical paths, security-sensitive code
4. **Team Coordination** - Decompose tasks, resolve conflicts
5. **Quality Oversight** - Enforce ADR-012 standards

## Platform Context
<platform_knowledge>
- **Stack**: Python 3.12, Django 5.x, PostgreSQL, Redis
- **Products**: BFAgent, Travel-Beat, Risk-Hub, CAD-Hub, PPTX-Hub
- **MCP Servers**: 14+ servers in mcp-hub repository
- **Infrastructure**: Hetzner Cloud, GitHub Actions, Docker
- **Key Standards**: ADR-009 (Deployment), ADR-012 (Quality), ADR-013 (Teams)
</platform_knowledge>

## Decision Framework
When making architectural decisions:
1. Check existing ADRs for precedent
2. Evaluate: Maintainability > Security > Performance > Simplicity
3. Consider backward compatibility (zero breaking changes policy)
4. Document rationale
5. Identify approval gate level

## Approval Gates
- **Gate 0**: Autonomous (triage, comments, reports)
- **Gate 1**: Async approval (docs, tests, minor PRs)
- **Gate 2**: Explicit approval (merges, API changes)
- **Gate 3**: Synchronous (production deploy, breaking changes)
- **Gate 4**: Human-initiated (delete, permissions, billing)

## Output Formats

### For Architecture Decisions:
```
## Decision: [Title]

### Context
[Why is this decision needed?]

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| A      | ...  | ...  |
| B      | ...  | ...  |

### Recommendation
[Your recommendation with rationale]

### Approval Gate: [0-4]
### Human Approval Required: [Yes/No]
```

### For Code Reviews:
```
## Code Review: [PR/File]

### Architecture Alignment
[✅/⚠️/❌] [Assessment]

### Quality Check (ADR-012)
- [ ] Tool docstrings complete
- [ ] Error handling structured
- [ ] Test coverage adequate
- [ ] Security considerations

### Recommendation
[APPROVE / REQUEST_CHANGES / COMMENT]

### Specific Feedback
[Line-by-line comments]
```

## Constraints
- Never approve production deployments without human confirmation
- Always create ADR for decisions affecting >1 component
- Escalate security concerns immediately to human
- Delegate implementation to Sonnet, routine tasks to Haiku
- Track and report token costs

## Collaboration
- **With Human (Achim)**: Seek approval for Gate 2+ decisions
- **With Team Alpha**: Coordinate on BFAgent/Platform tasks
- **With Team Bravo**: Coordinate on Travel-Beat/Content tasks
- **With Implementers**: Provide clear specifications
```

### 6.2 Team Alpha Lead System Prompt

```markdown
# Team Alpha Lead System Prompt

## Identity
You are the **AI Lead for Team Alpha**, specializing in BFAgent, industrial 
applications (Risk-Hub, CAD-Hub), and platform infrastructure.

## Domain Expertise
<expertise>
- BFAgent Django application architecture
- Industrial MCP servers: bfagent_mcp, ifc_mcp, cad_mcp
- Platform infrastructure: CI/CD, deployment_mcp
- Database design and migrations (PostgreSQL)
- Agent architectures and workflows
- Python packaging and distribution
</expertise>

## MCP Server Ownership
| Server | Role | Quality Target | Priority |
|--------|------|----------------|----------|
| bfagent_mcp | Primary | Grade B (80+) | High |
| bfagent_sqlite_mcp | Primary | Grade B (80+) | High |
| deployment_mcp | Primary | Grade A (90+) | Critical |
| german_tax_mcp | Primary | Grade C→B | Medium |
| ifc_mcp | Primary | Grade C→B | Medium |
| cad_mcp | Primary | Grade C→B | Medium |
| physicals_mcp | Primary | Grade C→B | Low |
| llm_mcp | Secondary | Grade A (90+) | Critical |

## Quality Standards (ADR-012)
All code must meet:
```python
@app.tool()
async def tool_name(
    param: str,
    optional: int = 10,
) -> str:
    """
    Brief description of what the tool does.
    
    Args:
        param: Description of parameter
        optional: Description with default noted
    
    Returns:
        JSON string describing the return value
    
    Raises:
        ValidationError: When input validation fails
    """
    try:
        # Validate input
        if not param:
            raise ValidationError("param cannot be empty")
        
        # Implementation
        result = await do_work(param, optional)
        
        return json.dumps({"success": True, "data": result})
    except ValidationError as e:
        return json.dumps({"success": False, "error": str(e), "code": "VALIDATION_ERROR"})
    except Exception as e:
        logger.exception(f"Error in tool_name: {e}")
        return json.dumps({"success": False, "error": str(e), "code": "INTERNAL_ERROR"})
```

## Task Routing
Route tasks to appropriate model tier:
- **Keep (Opus)**: Architecture decisions, complex bugs, security issues
- **Delegate to Sonnet**: Feature implementation, standard bugs, refactoring
- **Delegate to Haiku**: Tests, docs, linting, boilerplate

## Collaboration Rules
- **With AI Architect**: Escalate cross-cutting concerns
- **With Team Bravo**: Coordinate on shared components (llm_mcp)
- **With Human**: Get approval for Gate 2+ actions
- **With Implementers**: Provide clear, actionable specifications

## Output Format for Task Assignment
```
## Task Assignment

### Task: [Description]
### Assigned To: [Sonnet/Haiku]
### Priority: [High/Medium/Low]

### Specification
[Detailed requirements]

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Files to Modify
- path/to/file1.py
- path/to/file2.py

### Tests Required
- [ ] Unit tests for [X]
- [ ] Integration tests for [Y]
```
```

### 6.3 Team Bravo Lead System Prompt

```markdown
# Team Bravo Lead System Prompt

## Identity
You are the **AI Lead for Team Bravo**, specializing in Travel-Beat, content 
generation, and user experience applications.

## Domain Expertise
<expertise>
- Travel-Beat Django application
- Content generation MCP servers: travel_mcp, illustration_mcp, book_writing_mcp
- AI image generation workflows (DALL-E, Stable Diffusion)
- Documentation and user guides
- Creative content pipelines
- API integrations (external services)
</expertise>

## MCP Server Ownership
| Server | Role | Quality Target | Priority |
|--------|------|----------------|----------|
| travel_mcp | Primary | Grade B (80+) | High |
| illustration_mcp | Primary | Grade B (80+) | High |
| book_writing_mcp | Primary | Grade B (80+) | High |
| research_mcp | Primary | Grade A (90+) | Critical |
| dlm_mcp | Primary | Grade C→B | Medium |
| llm_mcp | Secondary | Grade A (90+) | Critical |

## Content Quality Standards
For content-related features:
- Clear, user-friendly error messages
- Proper handling of external API failures
- Graceful degradation when services unavailable
- Comprehensive logging for debugging

## Documentation Focus
As content specialists, ensure:
- All MCP servers have excellent README files
- API documentation is complete and accurate
- User guides are clear and helpful
- Examples are provided for common use cases

## Task Routing
Route tasks to appropriate model tier:
- **Keep (Opus)**: Content strategy, complex integrations, UX decisions
- **Delegate to Sonnet**: Feature implementation, API integrations
- **Delegate to Haiku**: Tests, docs, content templates

## Collaboration Rules
- **With AI Architect**: Escalate cross-cutting concerns
- **With Team Alpha**: Coordinate on shared components (llm_mcp)
- **With Human**: Get approval for user-facing changes
- **With Implementers**: Provide clear specifications with examples
```

### 6.4 Implementer System Prompt (Sonnet)

```markdown
# Implementer Agent System Prompt

## Identity
You are an **AI Implementer** for the BF Agent Platform. You write production-quality 
code based on specifications from Team Leads.

## Core Responsibilities
1. Implement features according to specifications
2. Fix bugs with proper test coverage
3. Refactor code following best practices
4. Create PRs with clear descriptions

## Code Standards
<standards>
- Python 3.12+
- Django 5.x patterns
- Type hints required for all functions
- Docstrings for all public functions (Google style)
- pytest for testing
- Ruff for linting (must pass)
- Follow existing patterns in codebase
</standards>

## MCP Server Template (ADR-012)
```python
"""
MCP Server: [name]_mcp

[Brief description of what this server does]
"""

import json
import logging
from typing import Optional

from mcp.server import Server
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)
app = Server("[name]-mcp")

class ToolInput(BaseModel):
    """Input validation model."""
    param: str
    optional: int = 10

@app.tool()
async def tool_name(
    param: str,
    optional: int = 10,
) -> str:
    """
    Brief description.
    
    Args:
        param: Description
        optional: Description (default: 10)
    
    Returns:
        JSON string with result
    """
    try:
        # Validate
        validated = ToolInput(param=param, optional=optional)
        
        # Implement
        result = await process(validated)
        
        return json.dumps({"success": True, "data": result})
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return json.dumps({"success": False, "error": str(e), "code": "VALIDATION"})
    except Exception as e:
        logger.exception(f"Error in tool_name")
        return json.dumps({"success": False, "error": str(e), "code": "INTERNAL"})
```

## PR Requirements
Every PR must include:
- [ ] Clear description of changes
- [ ] Tests for new functionality
- [ ] Updated documentation if needed
- [ ] No linting errors (ruff check passes)
- [ ] Type hints for all new code
- [ ] Linked to issue/task ID

## Constraints
- Do NOT make architecture decisions (escalate to Lead)
- Do NOT change public APIs without explicit approval
- Do NOT skip tests for "simple" changes
- Do NOT introduce new dependencies without approval

## Escalation Triggers
Escalate to Team Lead (Opus) when:
- Architecture decision needed
- Breaking change required
- Security concern found
- Specification unclear or incomplete
- External API behavior unexpected
```

### 6.5 Worker System Prompt (Haiku)

```markdown
# Worker Agent System Prompt

## Identity
You are an **AI Worker** for the BF Agent Platform. You handle routine tasks 
efficiently: test generation, documentation, simple fixes.

## Core Tasks

### 1. Test Generation
```python
import pytest
from unittest.mock import AsyncMock, patch
from module import function_to_test

class TestFunctionName:
    """Tests for function_name."""
    
    @pytest.fixture
    def mock_dependency(self):
        """Mock external dependency."""
        return AsyncMock(return_value={"success": True})
    
    def test_success_case(self, mock_dependency):
        """Test normal operation."""
        result = function_to_test("valid")
        assert result["success"] is True
    
    def test_invalid_input(self):
        """Test error handling."""
        result = function_to_test("")
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async operation."""
        result = await async_function("input")
        assert result is not None
    
    @pytest.mark.parametrize("input,expected", [
        ("a", "result_a"),
        ("b", "result_b"),
    ])
    def test_parametrized(self, input, expected):
        """Test multiple inputs."""
        assert function(input) == expected
```

### 2. Documentation
```markdown
# Tool Name

Brief description of what this tool does.

## Usage

\`\`\`python
result = await tool_name(param="value")
\`\`\`

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| param | str | Yes | - | Description |
| optional | int | No | 10 | Description |

## Returns

JSON object with:
- `success`: boolean indicating success
- `data`: result data (on success)
- `error`: error message (on failure)

## Examples

### Basic Usage
\`\`\`python
result = await tool_name(param="example")
# {"success": true, "data": {...}}
\`\`\`

### Error Handling
\`\`\`python
result = await tool_name(param="")
# {"success": false, "error": "param cannot be empty"}
\`\`\`
```

### 3. Simple Fixes
- Linting errors (ruff)
- Type hint additions
- Import organization
- Typo corrections
- Docstring formatting

## Constraints
- Do NOT make architecture decisions
- Do NOT change public APIs
- Do NOT modify business logic
- Escalate anything unclear to Implementer (Sonnet)

## Output Format
Always provide complete, copy-paste ready code or documentation.
```

---

## 7. Approval Gate System

### 7.1 Gate Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     5-LEVEL APPROVAL GATE SYSTEM                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GATE 0: AUTONOMOUS                                                     │
│  ═══════════════════                                                     │
│  AI executes without human involvement.                                 │
│                                                                          │
│  Actions:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ Issue triage & labeling                                          ││
│  │ ✅ PR comments & suggestions                                        ││
│  │ ✅ Test generation (existing code)                                  ││
│  │ ✅ Documentation updates (minor)                                    ││
│  │ ✅ Linting & formatting fixes                                       ││
│  │ ✅ Code quality reports & scorecards                                ││
│  │ ✅ Dependency vulnerability alerts                                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Notification: None required                                            │
│  Timeout: N/A                                                           │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  GATE 1: ASYNC APPROVAL                                                 │
│  ═══════════════════════                                                 │
│  AI executes after async approval (👍 reaction or "approve" comment).   │
│                                                                          │
│  Actions:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 🟡 PR ready for merge (feature branches)                            ││
│  │ 🟡 Non-breaking dependency updates                                  ││
│  │ 🟡 New test files                                                   ││
│  │ 🟡 README/documentation changes                                     ││
│  │ 🟡 Configuration changes (non-production)                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Notification: Slack + GitHub                                           │
│  Timeout: 24h → Reminder, 48h → Escalate                                │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  GATE 2: EXPLICIT APPROVAL                                              │
│  ═════════════════════════                                               │
│  AI executes only after explicit click/command approval.                │
│                                                                          │
│  Actions:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 🟠 Merge to main/production branch                                  ││
│  │ 🟠 New MCP server creation                                          ││
│  │ 🟠 API changes (even non-breaking)                                  ││
│  │ 🟠 New external dependencies                                        ││
│  │ 🟠 ADR drafts for review                                            ││
│  │ 🟠 Database schema changes (staging)                                ││
│  │ 🟠 CI/CD workflow changes                                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Notification: Slack + GitHub + Windsurf                                │
│  Timeout: Blocks indefinitely until approved                            │
│  Approval: /approve <action-id> or GitHub PR approval                   │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  GATE 3: SYNCHRONOUS REVIEW                                             │
│  ═══════════════════════════                                             │
│  AI executes only when human is online and confirms in real-time.       │
│                                                                          │
│  Actions:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ 🔴 Production deployments                                           ││
│  │ 🔴 Breaking API changes                                             ││
│  │ 🔴 Security-sensitive code                                          ││
│  │ 🔴 Database migrations (production)                                 ││
│  │ 🔴 ADR acceptance (final)                                           ││
│  │ 🔴 Cost-impacting decisions (>$100/month)                           ││
│  │ 🔴 External service integrations                                    ││
│  │ 🔴 User data handling changes                                       ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Notification: Urgent Slack + requires online presence                  │
│  Timeout: 4h then fails (human must be present)                         │
│  Approval: Real-time confirmation in Windsurf or Slack                  │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  GATE 4: HUMAN-INITIATED (AI Prepared Execution)                        │
│  ═══════════════════════════════════════════════                         │
│  Human must initiate. AI prepares and executes when granted.            │
│                                                                          │
│  Actions:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ⛔ Delete operations (repos, branches, data)                        ││
│  │ ⛔ Access/permission changes                                        ││
│  │ ⛔ Billing/subscription changes                                     ││
│  │ ⛔ Team member additions/removals                                   ││
│  │ ⛔ Repository settings changes                                      ││
│  │ ⛔ Secret/credential rotation                                       ││
│  │ ⛔ Rollback decisions                                               ││
│  │ ⛔ Infrastructure scaling                                           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  AI Capabilities:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ ✅ Suggest action based on human request                            ││
│  │ ✅ Prepare execution plan                                           ││
│  │ ✅ Create scripts/commands                                          ││
│  │ ✅ Perform impact analysis                                          ││
│  │ ✅ Execute dry-run                                                  ││
│  │ ✅ Create backup                                                    ││
│  │ ✅ EXECUTE when human grants with "/execute <action-id>"            ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Human Requirements:                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Must initiate the request                                         ││
│  │ • Must review AI preparation                                        ││
│  │ • Must explicitly grant execution permission                        ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Timeout: None - waits for human grant indefinitely                     │
│  Approval: /execute <action-id> (explicit command)                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Gate Comparison Matrix

| Aspect | Gate 0 | Gate 1 | Gate 2 | Gate 3 | Gate 4 |
|--------|--------|--------|--------|--------|--------|
| **AI can suggest** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AI can execute** | ✅ Auto | ✅ After 👍 | ✅ After ✓ | ✅ After ✓ | ✅ After grant |
| **Human initiates** | ❌ | ❌ | ❌ | ❌ | ✅ Required |
| **Approval type** | None | Async | Explicit | Sync | Grant |
| **Timeout** | N/A | 48h | ∞ | 4h | ∞ |
| **Notification** | None | Slack | Slack+GH | Urgent | On request |

### 7.3 Gate Assignment Rules

```python
# Gate assignment logic
def determine_gate(action_type: str, component: str, context: dict) -> int:
    """Determine approval gate level for an action."""
    
    # Gate 4: Human-initiated only
    GATE_4_ACTIONS = [
        "delete", "permission_change", "billing", 
        "team_change", "repo_settings", "secret_rotation",
        "rollback", "infrastructure_scale"
    ]
    if action_type in GATE_4_ACTIONS:
        return 4
    
    # Gate 3: Synchronous review required
    GATE_3_ACTIONS = [
        "production_deploy", "breaking_change", "security_change",
        "production_migration", "adr_accept", "cost_decision",
        "external_integration", "user_data_change"
    ]
    if action_type in GATE_3_ACTIONS:
        return 3
    
    # Gate 2: Explicit approval required
    GATE_2_ACTIONS = [
        "merge_main", "new_mcp_server", "api_change",
        "new_dependency", "adr_draft", "staging_migration",
        "workflow_change"
    ]
    if action_type in GATE_2_ACTIONS:
        return 2
    
    # Critical components elevate to at least Gate 2
    CRITICAL_COMPONENTS = ["llm_mcp", "deployment_mcp", "mcp-core", "platform"]
    if component in CRITICAL_COMPONENTS and action_type not in ["triage", "comment"]:
        return 2  # Force minimum Gate 2 for critical components
    
    # Gate 1: Async approval
    GATE_1_ACTIONS = [
        "feature_pr", "dependency_update", "new_tests",
        "docs_change", "staging_config"
    ]
    if action_type in GATE_1_ACTIONS:
        return 1
    
    # Gate 0: Autonomous
    return 0
```

---

## 8. Orchestrator MCP Server

### 8.1 Server Structure

```
mcp-hub/orchestrator_mcp/
├── __init__.py
├── server.py              # Main MCP server
├── agents.py              # Agent calling logic
├── gates.py               # Approval gate system
├── tasks.py               # Task management
├── costs.py               # Cost tracking
├── audit.py               # Audit logging
├── prompts/
│   ├── ai-architect.md
│   ├── team-alpha.md
│   ├── team-bravo.md
│   ├── implementer.md
│   └── worker.md
└── tests/
    ├── test_agents.py
    ├── test_gates.py
    └── test_tasks.py
```

### 8.2 Core Implementation

```python
# mcp-hub/orchestrator_mcp/server.py
"""
AI Team Orchestrator MCP Server

Coordinates AI agents, manages tasks, enforces approval gates,
and tracks costs for the BF Agent Platform.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from mcp.server import Server
from anthropic import Anthropic

from .agents import AgentConfig, call_agent, AGENT_CONFIGS
from .gates import ApprovalGate, determine_gate, Gate4Action, gate4_actions
from .tasks import Task, TaskType, TaskStatus, tasks_db
from .costs import track_cost, get_cost_report
from .audit import log_action

logger = logging.getLogger(__name__)
app = Server("orchestrator-mcp")
client = Anthropic()

# Component ownership mapping
COMPONENT_OWNERSHIP = {
    # Team Alpha
    "bfagent": "alpha",
    "bfagent_mcp": "alpha",
    "bfagent_sqlite_mcp": "alpha",
    "risk-hub": "alpha",
    "cad-hub": "alpha",
    "deployment_mcp": "alpha",
    "german_tax_mcp": "alpha",
    "ifc_mcp": "alpha",
    "cad_mcp": "alpha",
    "physicals_mcp": "alpha",
    # Team Bravo
    "travel-beat": "bravo",
    "travel_mcp": "bravo",
    "illustration_mcp": "bravo",
    "book_writing_mcp": "bravo",
    "pptx-hub": "bravo",
    "dlm_mcp": "bravo",
    "research_mcp": "bravo",
    # Shared (Architect)
    "llm_mcp": "architect",
    "mcp-core": "architect",
    "platform": "architect",
}

# ═══════════════════════════════════════════════════════════════════════════
# Task Management Tools
# ═══════════════════════════════════════════════════════════════════════════

@app.tool()
async def assign_task(
    description: str,
    component: str,
    task_type: str = "feature",
    priority: str = "medium",
) -> str:
    """
    Assign a development task to the appropriate AI team.
    
    Args:
        description: What needs to be done
        component: Which component is affected (e.g., "travel_mcp", "bfagent")
        task_type: Type (triage, architecture, feature, bug, test, docs, deploy)
        priority: Priority level (low, medium, high, critical)
    
    Returns:
        Task assignment with plan and approval requirements
    """
    # Determine ownership and gate
    team = COMPONENT_OWNERSHIP.get(component, "architect")
    task_type_enum = TaskType(task_type)
    gate = determine_gate(task_type, component, {})
    
    # Create task
    task = Task(
        id=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        description=description,
        component=component,
        task_type=task_type_enum,
        team=team,
        gate=ApprovalGate(gate),
        priority=priority,
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
    )
    
    # Get execution plan from architect
    plan_prompt = f"""
    Create an execution plan for this task:
    
    Task: {description}
    Component: {component}
    Type: {task_type}
    Team: {team}
    Priority: {priority}
    Approval Gate: {gate}
    
    Provide:
    1. Step-by-step plan with model assignment (Opus/Sonnet/Haiku)
    2. Estimated token cost
    3. Estimated time in minutes
    4. Files that will be modified
    5. Tests required
    6. Any risks or concerns
    
    Format as structured JSON.
    """
    
    plan_response = await call_agent("architect", plan_prompt)
    task.plan = plan_response
    
    # Store task
    tasks_db[task.id] = task
    
    # Log action
    log_action("task_created", task.id, {"team": team, "gate": gate})
    
    return json.dumps({
        "task_id": task.id,
        "team": team,
        "gate": gate,
        "gate_name": ApprovalGate(gate).name,
        "requires_approval": gate >= 2,
        "plan": plan_response,
        "next_steps": _get_next_steps(task),
    }, indent=2)


@app.tool()
async def execute_task(
    task_id: str,
    approved: bool = False,
) -> str:
    """
    Execute a task. Requires approval for Gate 2+.
    
    Args:
        task_id: ID of the task to execute
        approved: Whether human has approved (required for Gate 2+)
    
    Returns:
        Execution result or approval request
    """
    task = tasks_db.get(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})
    
    # Check gate requirements
    if task.gate.value >= 2 and not approved:
        task.status = TaskStatus.AWAITING_APPROVAL
        return json.dumps({
            "status": "awaiting_approval",
            "task_id": task_id,
            "gate": task.gate.name,
            "description": task.description,
            "message": f"Gate {task.gate.value}: Use '/approve {task_id}' to proceed.",
        })
    
    # Execute
    task.status = TaskStatus.EXECUTING
    if approved:
        task.approved_at = datetime.now()
        task.approved_by = "human"
    
    try:
        # Select agent based on team
        agent = f"{task.team}_lead" if task.team != "architect" else "architect"
        
        execution_prompt = f"""
        Execute this task:
        
        Task ID: {task_id}
        Description: {task.description}
        Component: {task.component}
        Plan: {task.plan}
        
        Implement the solution following ADR-012 quality standards.
        Provide the complete implementation.
        """
        
        result = await call_agent(agent, execution_prompt)
        
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.result = result
        
        log_action("task_completed", task_id, {"result": "success"})
        
        return json.dumps({
            "status": "completed",
            "task_id": task_id,
            "result": result,
        }, indent=2)
        
    except Exception as e:
        task.status = TaskStatus.FAILED
        task.error = str(e)
        log_action("task_failed", task_id, {"error": str(e)})
        
        return json.dumps({
            "status": "failed",
            "task_id": task_id,
            "error": str(e),
        })


@app.tool()
async def approve(action_id: str) -> str:
    """
    Approve a pending action (task or Gate 4 action).
    
    Args:
        action_id: ID of the task or action to approve
    
    Returns:
        Approval confirmation and execution result
    """
    # Check if it's a task
    if action_id in tasks_db:
        task = tasks_db[action_id]
        if task.status != TaskStatus.AWAITING_APPROVAL:
            return json.dumps({"error": f"Task {action_id} is not awaiting approval"})
        
        log_action("task_approved", action_id, {"by": "human"})
        return await execute_task(action_id, approved=True)
    
    # Check if it's a Gate 4 action
    if action_id in gate4_actions:
        return await execute_gate4(action_id, confirmed=True)
    
    return json.dumps({"error": f"Action {action_id} not found"})


@app.tool()
async def list_pending() -> str:
    """
    List all pending tasks and actions awaiting approval.
    
    Returns:
        List of pending items with details
    """
    pending_tasks = [
        {
            "id": t.id,
            "type": "task",
            "description": t.description,
            "gate": t.gate.name,
            "team": t.team,
            "created_at": t.created_at.isoformat(),
        }
        for t in tasks_db.values()
        if t.status == TaskStatus.AWAITING_APPROVAL
    ]
    
    pending_gate4 = [
        {
            "id": a.id,
            "type": "gate4",
            "description": a.description,
            "action_type": a.action_type,
            "prepared_at": a.prepared_at.isoformat(),
        }
        for a in gate4_actions.values()
        if a.status.value == "ready"
    ]
    
    return json.dumps({
        "pending_count": len(pending_tasks) + len(pending_gate4),
        "tasks": pending_tasks,
        "gate4_actions": pending_gate4,
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Direct Agent Access Tools
# ═══════════════════════════════════════════════════════════════════════════

@app.tool()
async def architect(question: str, context: str = "") -> str:
    """
    Consult the AI Architect for architecture decisions or complex questions.
    
    Args:
        question: The question or problem to address
        context: Optional additional context
    
    Returns:
        Architect's analysis and recommendation
    """
    log_action("architect_consulted", None, {"question": question[:100]})
    return await call_agent("architect", question, context)


@app.tool()
async def team_alpha(task: str, context: str = "") -> str:
    """
    Assign a task to Team Alpha (BFAgent, Platform, Industrial).
    
    Args:
        task: Task description
        context: Optional additional context
    
    Returns:
        Team Alpha's response
    """
    log_action("team_alpha_task", None, {"task": task[:100]})
    return await call_agent("alpha_lead", task, context)


@app.tool()
async def team_bravo(task: str, context: str = "") -> str:
    """
    Assign a task to Team Bravo (Travel-Beat, Content).
    
    Args:
        task: Task description
        context: Optional additional context
    
    Returns:
        Team Bravo's response
    """
    log_action("team_bravo_task", None, {"task": task[:100]})
    return await call_agent("bravo_lead", task, context)


@app.tool()
async def implement(
    specification: str,
    model_tier: str = "sonnet",
) -> str:
    """
    Delegate implementation to Sonnet or Haiku.
    
    Args:
        specification: What to implement
        model_tier: "sonnet" for features/bugs, "haiku" for tests/docs
    
    Returns:
        Implementation result
    """
    agent = "implementer" if model_tier == "sonnet" else "worker"
    log_action("implementation", None, {"tier": model_tier})
    return await call_agent(agent, specification)


# ═══════════════════════════════════════════════════════════════════════════
# Gate 4: Human-Initiated Actions
# ═══════════════════════════════════════════════════════════════════════════

@app.tool()
async def prepare_destructive_action(
    action_type: str,
    description: str,
    target_resources: list[str],
) -> str:
    """
    Prepare a Gate 4 (human-initiated) action for review and execution.
    
    Args:
        action_type: Type (delete, permission_change, rollback, etc.)
        description: Human-readable description
        target_resources: List of resources that will be affected
    
    Returns:
        Prepared action with ID for grant/execute
    """
    from .gates import prepare_gate4_action
    return await prepare_gate4_action(action_type, description, target_resources)


@app.tool()
async def execute_gate4(action_id: str, confirmed: bool = False) -> str:
    """
    Execute a prepared Gate 4 action after human grant.
    
    Args:
        action_id: ID of the prepared action
        confirmed: Must be True to execute
    
    Returns:
        Execution result
    """
    from .gates import execute_gate4_action
    log_action("gate4_executed", action_id, {"confirmed": confirmed})
    return await execute_gate4_action(action_id, confirmed)


@app.tool()
async def cancel_gate4(action_id: str) -> str:
    """
    Cancel a prepared Gate 4 action.
    
    Args:
        action_id: ID of the action to cancel
    
    Returns:
        Cancellation confirmation
    """
    from .gates import cancel_gate4_action
    log_action("gate4_cancelled", action_id, {})
    return await cancel_gate4_action(action_id)


# ═══════════════════════════════════════════════════════════════════════════
# Review & Quality Tools
# ═══════════════════════════════════════════════════════════════════════════

@app.tool()
async def review_pr(
    pr_number: int,
    repository: str = "mcp-hub",
) -> str:
    """
    Request AI review of a pull request.
    
    Args:
        pr_number: GitHub PR number
        repository: Repository name
    
    Returns:
        Review with approval recommendation
    """
    review_prompt = f"""
    Review PR #{pr_number} in {repository}.
    
    Check for:
    1. Architecture alignment with ADRs
    2. Code quality (ADR-012 standards)
    3. Security issues
    4. Test coverage
    5. Documentation completeness
    
    Provide specific feedback and approval recommendation.
    Format: APPROVE / REQUEST_CHANGES / COMMENT
    """
    
    log_action("pr_review", None, {"pr": pr_number, "repo": repository})
    return await call_agent("architect", review_prompt)


@app.tool()
async def quality_check(mcp_server: str) -> str:
    """
    Run quality scorecard check on an MCP server.
    
    Args:
        mcp_server: Name of the MCP server to check
    
    Returns:
        Quality scorecard with score and recommendations
    """
    check_prompt = f"""
    Run ADR-012 quality check on {mcp_server}.
    
    Evaluate:
    1. Tool Design (20%): Naming, parameters, types, docstrings
    2. Error Handling (15%): Try/catch, error classification
    3. Documentation (15%): README, tool docs, examples
    4. Test Coverage (20%): Unit tests, integration tests
    5. Security (15%): Input validation, secrets handling
    6. Observability (10%): Logging, metrics
    7. Architecture (5%): Code organization
    
    Provide:
    - Score per category
    - Overall score and grade
    - Specific recommendations
    """
    
    log_action("quality_check", None, {"server": mcp_server})
    return await call_agent("architect", check_prompt)


# ═══════════════════════════════════════════════════════════════════════════
# Cost & Monitoring Tools
# ═══════════════════════════════════════════════════════════════════════════

@app.tool()
async def get_costs(period: str = "today") -> str:
    """
    Get AI token costs for a period.
    
    Args:
        period: "today", "week", "month", or specific date
    
    Returns:
        Cost breakdown by model and team
    """
    return json.dumps(get_cost_report(period), indent=2)


@app.tool()
async def get_task_status(task_id: str) -> str:
    """
    Get detailed status of a task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Task details including status, plan, and result
    """
    task = tasks_db.get(task_id)
    if not task:
        return json.dumps({"error": f"Task {task_id} not found"})
    
    return json.dumps({
        "id": task.id,
        "description": task.description,
        "component": task.component,
        "team": task.team,
        "status": task.status.value,
        "gate": task.gate.name,
        "priority": task.priority,
        "created_at": task.created_at.isoformat(),
        "approved_at": task.approved_at.isoformat() if task.approved_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "plan": task.plan,
        "result": task.result,
        "error": task.error,
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

def _get_next_steps(task: Task) -> list[str]:
    """Get next steps based on task state and gate."""
    if task.gate.value >= 2:
        return [
            f"Review the execution plan above",
            f"Use '/approve {task.id}' to approve and execute",
            f"Use '/cancel {task.id}' to cancel",
        ]
    elif task.gate.value == 1:
        return [
            f"Task will execute after async approval",
            f"React with 👍 or comment 'approve' on the notification",
        ]
    else:
        return [
            f"Task is executing autonomously",
            f"Use '/status {task.id}' to check progress",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream)
    
    asyncio.run(main())
```

---

## 9. GitHub Actions Integration

### 9.1 AI Orchestration Workflow

```yaml
# .github/workflows/ai-orchestration.yml
name: "🤖 AI Team Orchestration"

on:
  issues:
    types: [opened, labeled]
  pull_request:
    types: [opened, synchronize, ready_for_review]
  issue_comment:
    types: [created]
  workflow_dispatch:
    inputs:
      task:
        description: 'Task for AI team'
        required: true

env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

jobs:
  # ═══════════════════════════════════════════════════════════════════════
  # Issue Triage (Gate 0: Autonomous)
  # ═══════════════════════════════════════════════════════════════════════
  triage:
    name: "🏷️ AI Issue Triage"
    if: github.event_name == 'issues' && github.event.action == 'opened'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: AI Triage Analysis
        id: triage
        uses: anthropics/claude-code-action@v1
        with:
          model: claude-haiku-4-5-20250514
          max_tokens: 1024
          prompt: |
            Analyze this GitHub issue:
            
            Title: ${{ github.event.issue.title }}
            Body: ${{ github.event.issue.body }}
            
            Component ownership:
            - Team Alpha: bfagent, risk-hub, cad-hub, deployment_mcp, *_mcp (industrial)
            - Team Bravo: travel-beat, pptx-hub, travel_mcp, illustration_mcp, book_writing_mcp
            - Architect: llm_mcp, mcp-core, platform, cross-cutting
            
            Respond with JSON only:
            {
              "team": "alpha|bravo|architect",
              "task_type": "bug|feature|docs|architecture|question",
              "gate": 0-4,
              "priority": "low|medium|high|critical",
              "labels": ["label1", "label2"],
              "summary": "One sentence summary"
            }
      
      - name: Apply Labels
        uses: actions/github-script@v7
        with:
          script: |
            const result = JSON.parse(`${{ steps.triage.outputs.response }}`);
            
            const labels = [
              `team:${result.team}`,
              `type:${result.task_type}`,
              `priority:${result.priority}`,
              ...result.labels
            ];
            
            await github.rest.issues.addLabels({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              labels: labels
            });
            
            const body = `## 🤖 AI Triage
            
            **Summary:** ${result.summary}
            
            | Attribute | Value |
            |-----------|-------|
            | Team | ${result.team} |
            | Type | ${result.task_type} |
            | Priority | ${result.priority} |
            | Gate | ${result.gate} |
            
            ---
            *Automated triage by AI Orchestrator*`;
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });

  # ═══════════════════════════════════════════════════════════════════════
  # PR Review (Gate 0-2 depending on changes)
  # ═══════════════════════════════════════════════════════════════════════
  pr-review:
    name: "🔍 AI Code Review"
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Get Changed Files
        id: changes
        run: |
          FILES=$(git diff --name-only origin/${{ github.base_ref }}...HEAD)
          echo "files<<EOF" >> $GITHUB_OUTPUT
          echo "$FILES" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT
          
          # Determine if critical files changed
          CRITICAL="mcp-core|llm_mcp|deployment_mcp|platform"
          if echo "$FILES" | grep -qE "$CRITICAL"; then
            echo "critical=true" >> $GITHUB_OUTPUT
            echo "model=claude-opus-4-5-20250514" >> $GITHUB_OUTPUT
          else
            echo "critical=false" >> $GITHUB_OUTPUT
            echo "model=claude-sonnet-4-5-20250514" >> $GITHUB_OUTPUT
          fi
      
      - name: Get Diff
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > diff.txt
          head -c 100000 diff.txt > diff_truncated.txt
      
      - name: AI Code Review
        id: review
        uses: anthropics/claude-code-action@v1
        with:
          model: ${{ steps.changes.outputs.model }}
          max_tokens: 4096
          system_prompt_file: .github/prompts/code-reviewer.md
          prompt: |
            Review this PR:
            
            Title: ${{ github.event.pull_request.title }}
            Description: ${{ github.event.pull_request.body }}
            Critical: ${{ steps.changes.outputs.critical }}
            
            Changed files:
            ${{ steps.changes.outputs.files }}
            
            Diff:
            $(cat diff_truncated.txt)
      
      - name: Post Review
        uses: actions/github-script@v7
        with:
          script: |
            const review = `${{ steps.review.outputs.response }}`;
            const critical = '${{ steps.changes.outputs.critical }}' === 'true';
            
            await github.rest.pulls.createReview({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.payload.pull_request.number,
              body: `## 🤖 AI Code Review\n\n${critical ? '⚠️ **Critical path changes detected**\n\n' : ''}${review}`,
              event: 'COMMENT'
            });

  # ═══════════════════════════════════════════════════════════════════════
  # Approval Command Handler
  # ═══════════════════════════════════════════════════════════════════════
  handle-approval:
    name: "✅ Handle Approval Command"
    if: |
      github.event_name == 'issue_comment' && 
      startsWith(github.event.comment.body, '/approve')
    runs-on: ubuntu-latest
    
    steps:
      - name: Parse Command
        id: parse
        run: |
          COMMENT="${{ github.event.comment.body }}"
          ACTION_ID=$(echo "$COMMENT" | grep -oP '/approve \K\S+')
          echo "action_id=$ACTION_ID" >> $GITHUB_OUTPUT
      
      - name: Execute Approval
        run: |
          echo "Approving action: ${{ steps.parse.outputs.action_id }}"
          # In production: call orchestrator_mcp approve tool
      
      - name: Confirm
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `✅ Approved: \`${{ steps.parse.outputs.action_id }}\`\n\nExecuting...`
            });

  # ═══════════════════════════════════════════════════════════════════════
  # Deployment Gates (Gate 3)
  # ═══════════════════════════════════════════════════════════════════════
  deploy-staging:
    name: "🚀 Deploy to Staging"
    if: |
      github.event_name == 'pull_request' && 
      github.event.action == 'closed' && 
      github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: echo "Deploying to staging..."
      
      - name: Notify
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_CHANNEL }}
          slack-message: |
            🚀 *Staging Deployment*
            PR: ${{ github.event.pull_request.title }}
            
            Production deployment requires manual approval.

  deploy-production:
    name: "🚀 Deploy to Production"
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # Requires explicit approval
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: echo "Deploying to production..."
      
      - name: Notify
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: ${{ secrets.SLACK_CHANNEL }}
          slack-message: "✅ Production deployment complete!"
```

---

## 10. Windsurf Integration

### 10.1 MCP Server Configuration

```json
// windsurf.json or .cascade/mcp.json
{
  "mcpServers": {
    "orchestrator": {
      "command": "python",
      "args": ["-m", "orchestrator_mcp.server"],
      "cwd": "/path/to/mcp-hub",
      "env": {
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    },
    "github": {
      "command": "npx",
      "args": ["@anthropic/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "deployment": {
      "command": "python",
      "args": ["-m", "deployment_mcp.server"],
      "cwd": "/path/to/mcp-hub"
    }
  }
}
```

### 10.2 Windsurf Command Reference

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    WINDSURF COMMAND REFERENCE                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  📋 TASK MANAGEMENT                                                     │
│  ═══════════════════                                                     │
│                                                                          │
│  "Assign task to fix bug in travel_mcp"                                 │
│  → Calls: assign_task(description, component="travel_mcp", type="bug")  │
│                                                                          │
│  "What's the status of task-20260203-143022?"                           │
│  → Calls: get_task_status(task_id)                                      │
│                                                                          │
│  "Show me all pending approvals"                                        │
│  → Calls: list_pending()                                                │
│                                                                          │
│  "Approve task-20260203-143022"                                         │
│  → Calls: approve(action_id)                                            │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🤖 DIRECT AGENT ACCESS                                                 │
│  ════════════════════════                                                │
│                                                                          │
│  "Ask the architect about database design for X"                        │
│  → Calls: architect(question)                                           │
│                                                                          │
│  "Team Alpha: implement rate limiting for bfagent_mcp"                  │
│  → Calls: team_alpha(task)                                              │
│                                                                          │
│  "Team Bravo: add new illustration style option"                        │
│  → Calls: team_bravo(task)                                              │
│                                                                          │
│  "Implement this feature specification using Sonnet"                    │
│  → Calls: implement(specification, model_tier="sonnet")                 │
│                                                                          │
│  "Generate tests for this function using Haiku"                         │
│  → Calls: implement(specification, model_tier="haiku")                  │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🔴 GATE 4: DESTRUCTIVE ACTIONS                                         │
│  ═══════════════════════════════                                         │
│                                                                          │
│  "Clean up old branches merged more than 30 days ago"                   │
│  → Calls: prepare_destructive_action(type="delete", ...)                │
│  → Returns: Action ID for review                                        │
│  → You: "Execute gate4-cleanup-20260203-143022"                         │
│  → Calls: execute_gate4(action_id, confirmed=True)                      │
│                                                                          │
│  "Cancel the branch cleanup"                                            │
│  → Calls: cancel_gate4(action_id)                                       │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  🔍 REVIEW & QUALITY                                                    │
│  ═══════════════════                                                     │
│                                                                          │
│  "Review PR #234"                                                       │
│  → Calls: review_pr(pr_number=234)                                      │
│                                                                          │
│  "Run quality check on travel_mcp"                                      │
│  → Calls: quality_check(mcp_server="travel_mcp")                        │
│                                                                          │
│  ────────────────────────────────────────────────────────────────────── │
│                                                                          │
│  💰 MONITORING                                                          │
│  ═════════════                                                           │
│                                                                          │
│  "What are today's AI costs?"                                           │
│  → Calls: get_costs(period="today")                                     │
│                                                                          │
│  "Show this week's cost breakdown"                                      │
│  → Calls: get_costs(period="week")                                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Cost Management

### 11.1 Cost Tracking

```python
# orchestrator_mcp/costs.py
"""
AI Token Cost Tracking

Tracks token usage and costs per model, team, and task.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import json

# Model pricing (per 1M tokens)
MODEL_COSTS = {
    "claude-opus-4-5-20250514": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20250514": {"input": 0.25, "output": 1.25},
}

@dataclass
class TokenUsage:
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    team: str
    task_id: Optional[str]
    cost: float

# Storage
usage_log: list[TokenUsage] = []

def track_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    team: str,
    task_id: Optional[str] = None,
) -> float:
    """Track token usage and calculate cost."""
    costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
    
    cost = (
        (input_tokens / 1_000_000) * costs["input"] +
        (output_tokens / 1_000_000) * costs["output"]
    )
    
    usage = TokenUsage(
        timestamp=datetime.now(),
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        team=team,
        task_id=task_id,
        cost=cost,
    )
    
    usage_log.append(usage)
    return cost

def get_cost_report(period: str = "today") -> dict:
    """Generate cost report for a period."""
    now = datetime.now()
    
    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=7)
    elif period == "month":
        start = now - timedelta(days=30)
    else:
        start = datetime.min
    
    filtered = [u for u in usage_log if u.timestamp >= start]
    
    # Aggregate by model
    by_model = {}
    for u in filtered:
        model_name = u.model.split("-")[1]  # opus, sonnet, haiku
        if model_name not in by_model:
            by_model[model_name] = {"tokens": 0, "cost": 0.0}
        by_model[model_name]["tokens"] += u.input_tokens + u.output_tokens
        by_model[model_name]["cost"] += u.cost
    
    # Aggregate by team
    by_team = {}
    for u in filtered:
        if u.team not in by_team:
            by_team[u.team] = 0.0
        by_team[u.team] += u.cost
    
    total_cost = sum(u.cost for u in filtered)
    
    return {
        "period": period,
        "start": start.isoformat(),
        "end": now.isoformat(),
        "total_cost": f"${total_cost:.2f}",
        "total_tokens": sum(u.input_tokens + u.output_tokens for u in filtered),
        "by_model": {
            k: {"tokens": v["tokens"], "cost": f"${v['cost']:.2f}"}
            for k, v in by_model.items()
        },
        "by_team": {k: f"${v:.2f}" for k, v in by_team.items()},
        "request_count": len(filtered),
    }
```

### 11.2 Cost Optimization Rules

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    COST OPTIMIZATION RULES                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  RULE 1: Default to Lowest Capable Tier                                 │
│  ═══════════════════════════════════════                                 │
│  • Use Haiku for tests, docs, simple fixes                              │
│  • Use Sonnet for standard implementation                               │
│  • Use Opus only for architecture, security, complex                    │
│                                                                          │
│  RULE 2: Batch Similar Tasks                                            │
│  ════════════════════════════                                            │
│  • Group test generation requests                                       │
│  • Combine documentation updates                                        │
│  • Batch linting fixes                                                  │
│                                                                          │
│  RULE 3: Cache Common Patterns                                          │
│  ═════════════════════════════                                           │
│  • Cache boilerplate templates                                          │
│  • Reuse common code patterns                                           │
│  • Store and reuse test fixtures                                        │
│                                                                          │
│  RULE 4: Truncate Large Inputs                                          │
│  ═════════════════════════════                                           │
│  • Limit diff size for reviews                                          │
│  • Summarize long context                                               │
│  • Use focused file excerpts                                            │
│                                                                          │
│  RULE 5: Monitor and Alert                                              │
│  ═════════════════════════                                               │
│  • Daily cost report                                                    │
│  • Alert on unusual spending                                            │
│  • Weekly trend analysis                                                │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  ESTIMATED MONTHLY COSTS (Active Development):                          │
│                                                                          │
│  Model      │ Tasks/Month │ Avg Cost │ Monthly    │ % of Total          │
│  ───────────┼─────────────┼──────────┼────────────┼─────────────        │
│  Opus       │ 50          │ $0.75    │ $37.50     │ 60%                 │
│  Sonnet     │ 200         │ $0.10    │ $20.00     │ 32%                 │
│  Haiku      │ 500         │ $0.01    │ $5.00      │ 8%                  │
│  ───────────┼─────────────┼──────────┼────────────┼─────────────        │
│  Total      │ 750         │ —        │ $62.50     │ 100%                │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Implementation Plan

**Gesamtdauer: 12-16 Wochen** (realistisch für Production-Ready System)

### Phase 1: MVP Foundation (Week 1-4)

| Task | Owner | Deliverable | Status |
|------|-------|-------------|--------|
| Create orchestrator_mcp server | AI Architect | Working MCP server | — |
| Write system prompts | AI Architect | 5 prompt files | — |
| Setup Windsurf integration | Human | mcp.json config | — |
| Implement Gate 0-2 | AI Sonnet | Basic gate logic | — |
| Test basic task flow | Human + AI | Working demo | — |

**Milestone 1:** AI kann einfache Tasks (Gate 0-1) ausführen

### Phase 2: Gate System (Week 5-8)

| Task | Owner | Deliverable | Status |
|------|-------|-------------|--------|
| Implement Gate 3-4 | AI Sonnet | Advanced gates | — |
| Add cost tracking | AI Haiku | Cost module | — |
| Create audit logging | AI Haiku | Audit system | — |
| GitHub Actions workflows | AI | 2 workflow files | — |
| Security hardening | AI Sonnet | Input validation | — |

**Milestone 2:** Vollständiges Gate-System mit Audit

### Phase 3: Team Integration (Week 9-12)

| Task | Owner | Deliverable | Status |
|------|-------|-------------|--------|
| Train Team Alpha prompt | AI Architect | Specialized prompt | — |
| Train Team Bravo prompt | AI Architect | Specialized prompt | — |
| Create MCP server tests | AI Haiku | Test suite | — |
| Documentation | AI Haiku | User guide | — |
| Pilot mit echten Tasks | Human + AI | 10+ Tasks | — |

**Milestone 3:** Beide Teams operativ

### Phase 4: Optimization (Week 13-16)

| Task | Owner | Deliverable | Status |
|------|-------|-------------|--------|
| Analyze cost patterns | AI Architect | Cost report | — |
| Optimize model selection | AI Architect | Updated rules | — |
| Add caching layer | AI Sonnet | Cache system | — |
| Performance tuning | AI Sonnet | Faster responses | — |
| Full production rollout | Human | Complete system | — |

**Milestone 4:** Production-Ready, Metrics validiert

---

## 13. Success Metrics

| Metric | Baseline | Target (3M) | Target (6M) | Target (12M) |
|--------|----------|-------------|-------------|--------------|
| **Tasks completed by AI** | 0% | 30% | 50% | 70% |
| **Human review time** | 100% | 60% | 40% | 25% |
| **Code quality score** | ~60 | 70 | 80 | 85 |
| **Deployment frequency** | 20/day | 25/day | 35/day | 50/day |
| **Mean time to resolve** | Days | 12h | 4h | 1h |
| **AI cost per feature** | — | <$10 | <$5 | <$3 |
| **Gate 4 incidents** | — | 0 | 0 | 0 |

> **Note:** Metriken sind konservativ geschätzt. Anpassung nach Phase 1 basierend auf realen Daten.

---

## 14. Consequences

### 14.1 Positive

| Benefit | Impact |
|---------|--------|
| **Faster development** | 5-10x feature velocity |
| **Consistent quality** | ADR-012 always enforced |
| **24/7 capacity** | AI works while human sleeps |
| **Human focus** | Strategy instead of coding |
| **Lower costs** | Optimized model selection |
| **Full audit trail** | Every action logged |

### 14.2 Negative

| Drawback | Mitigation |
|----------|------------|
| AI token costs | Cost tracking, optimization (keine Token-Limits) |
| Learning curve | Good documentation, examples |
| AI mistakes | Human approval gates |
| Complexity | Start simple, iterate |
| **Task Failures** | AI erinnert Human, gemeinsam Lösung finden |

### 14.3 Rollback Strategy

Bei fehlgeschlagenen AI-Aufgaben:

1. **AI meldet Fehler** an Human mit Kontext und Logs
2. **Human und AI analysieren** gemeinsam die Ursache
3. **Gemeinsame Lösungsfindung** - AI schlägt Alternativen vor
4. **Human entscheidet** über nächsten Schritt
5. **Fallback**: Manuelle Ausführung wenn AI nicht weiterkommt

> *"Bei Problemen: AI erinnert dich, und wir finden gemeinsam eine Lösung."*

### 14.4 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| AI makes wrong decision | Medium | High | Gate system, human review |
| Cost overrun | Low | Medium | Budget alerts, caps |
| Security issue | Low | Critical | Gate 3-4 for sensitive |
| System failure | Low | High | Fallback to manual |

### 14.5 Security Considerations

| Risiko | Mitigation |
|--------|------------|
| **Prompt Injection** | Input Sanitization, Output Validation vor Code-Ausführung |
| **Credential Exposure** | Secrets nie in Prompts, nur über Vault/Environment |
| **Malicious Code** | Gate 2+ für alle Code-Änderungen, Automated Security Scans |
| **Audit Tampering** | Immutable Audit Log, External Backup |
| **AI Impersonation** | Alle AI-Commits signiert, klare Kennzeichnung |

### 14.6 Continuity & Delegation

| Situation | Verhalten |
|-----------|-----------|
| **Human unavailable <4h** | Gate 0-1 läuft weiter, Gate 2+ queued |
| **Human unavailable 4-24h** | AI pausiert neue Tasks, nur laufende abschließen |
| **Extended absence >24h** | System in "Read-Only Mode", nur Gate 0 |
| **Emergency** | Designated Backup via GitHub Team erhält Notifications |

> **Backup-Kontakt:** GitHub Team `@platform-admins` für Notfälle konfigurieren.

### 14.7 Exit Criteria

Rückkehr zu traditionellem Modell wenn nach **6 Monaten**:

| Kriterium | Schwellwert |
|-----------|-------------|
| AI Task Completion | < 20% |
| Bug-Rate durch AI | > Bugs gelöst |
| Monatliche Kosten | > $500 ohne proportionalen Nutzen |
| Gate 4 Incidents | > 2 |
| Human Zufriedenheit | < 3/5 |

---

## 15. References

- [ADR-012: MCP Server Quality Standards](./ADR-012-mcp-quality-standards.md)
- [ADR-013: Team Organization & MCP Ownership](./ADR-013-team-organization-mcp-ownership.md)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [Windsurf Documentation](https://docs.windsurf.ai/)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-03 | Achim Dehnert | Initial version |
| 2026-02-03 | AI Review | Added: Alternatives (3.1), Security (14.5), Continuity (14.6), Exit Criteria (14.7) |
| 2026-02-03 | AI Review | Updated: Realistic metrics, 12-16 week timeline, fixed code issues |
| 2026-02-03 | Achim Dehnert | Model Strategy: SWE-1.5 primary, Claude Opus 4.5 (Thinking) for architecture |
