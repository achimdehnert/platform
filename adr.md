---
description: Create new ADR with automatic scope detection and proper structure
---

# ADR Creation Workflow

## Trigger

User says: "Erstelle ein ADR für: [Thema]" or similar natural language request.

## Step 0: Validate if this is actually an ADR

Before creating an ADR, check if the topic is truly an **Architecture Decision**.

### ADR Criteria (ALL must apply)

1. **Long-term impact**: Will this affect the codebase for months/years?
2. **Technical decision**: Is there a "why" behind choosing option A over B?
3. **Not operational**: Is this NOT a repeatable procedure?

### NOT an ADR - Suggest Alternatives

| Topic Pattern | Reason | Suggest Instead |
|---------------|--------|-----------------|
| "Deployment of...", "How to deploy" | Operational procedure | Workflow: `deploy.md` |
| "Backup process", "How to backup" | Operational procedure | Workflow: `backup.md` |
| "Release process", "How to release" | Operational procedure | Workflow: `release.md` |
| "Setup instructions", "Installation" | Documentation | README or docs/ |
| "Bug fix for...", "Fix issue with" | Code change | GitHub Issue or PR |

### Response if NOT an ADR

```text
🤔 Das klingt nicht nach einem ADR

Thema: "[User's topic]"

❌ Warum kein ADR?
   → [Reason]

✅ Bessere Alternativen:
   1. Workflow erstellen
   2. Dokumentation
   3. Oder meinst du eine Architektur-Entscheidung?

Soll ich stattdessen einen Workflow erstellen? [Ja/ADR trotzdem]
```

## Step 1: Analyze Topic and Detect Scope

Analyze the topic using these keywords:

| Keywords | Scope | Number Range |
|----------|-------|--------------|
| Agent, Handler, Tool, Memory, Conversation, LLM, Prompt | `bfagent` | 050-099 |
| Story, Travel, Trip, Timing, Drifttales, Content | `travel-beat` | 100-149 |
| MCP, Server, Protocol, Registry, Tool-Server | `mcp-hub` | 150-199 |
| Risk, Assessment, Scoring, Compliance | `risk-hub` | 200-249 |
| CAD, IFC, XGF, XKT, Viewer, Model, BIM | `cad-hub` | 250-299 |
| PPTX, PowerPoint, Slide, Template, Presentation | `pptx-hub` | 300-349 |
| CI/CD, Deployment, Docker, DB, Monitoring, Security, Platform | `core` | 001-049 |
| API, Auth, Logging, "alle Apps", "shared", Cross-App | `shared` | 350-399 |

## Step 2: Show Scope Suggestion

```text
📋 ADR-Vorschlag

Thema: "[User's topic]"

🎯 Scope-Erkennung:
   → [scope] ([range])
   
   Begründung: [Why this scope was chosen]

Nächste Nummer: ADR-[NNN]
Datei: docs/adr/ADR-[NNN]-[title-slug].md

Scope korrekt? [Ja/Nein]
```

## Step 3: Create ADR File

After user confirms:

1. Find next available number in scope range
2. Create file using TEMPLATE structure
3. Fill in metadata and content from user's concept (if provided)

## Step 4: Post-ADR Workflow

After ADR is created, show:

```text
📋 ADR-[NNN] erstellt: [Title]

Status: Proposed → Review erforderlich

Nächste Schritte:
1. 👀 Review: "Review ADR-[NNN]" (AI + Team)
2. ✅ Approval: Status → Accepted/Rejected
3. 🚀 Implementation: Gemäß Implementation Plan

Soll ich das ADR jetzt reviewen? [Ja/Nein]
```

## Step 5: ADR Review (if requested)

Review the ADR against these criteria:

| Kategorie | Prüfpunkte |
|-----------|------------|
| **Vollständigkeit** | Context, Decision, Consequences vorhanden? |
| **Klarheit** | Verständlich formuliert? Keine Mehrdeutigkeiten? |
| **Begründung** | Alternativen betrachtet? Entscheidung nachvollziehbar? |
| **Umsetzbarkeit** | Implementation Plan realistisch? Risiken adressiert? |
| **Konsistenz** | Passt zu anderen ADRs? Keine Widersprüche? |

Output format:

```text
## 🔍 ADR Review: ADR-[NNN]

### ✅ Stärken
- [Positive points]

### ⚠️ Verbesserungsvorschläge
- [Suggestions]

### ❌ Kritische Punkte (falls vorhanden)
- [Critical issues that must be addressed]

### 📊 Bewertung
| Kriterium | Score |
|-----------|-------|
| Vollständigkeit | ⭐⭐⭐⭐☆ |
| Klarheit | ⭐⭐⭐⭐⭐ |
| Begründung | ⭐⭐⭐⭐☆ |
| Umsetzbarkeit | ⭐⭐⭐☆☆ |
| Konsistenz | ⭐⭐⭐⭐⭐ |

### 🎯 Empfehlung
[Accept / Accept with changes / Reject]
```
