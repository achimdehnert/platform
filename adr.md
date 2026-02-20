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

| Keywords | Scope / Repo | Number Range |
|----------|-------------|--------------|
| CI/CD, Deployment, Docker, DB, Monitoring, Security, Platform-wide | `platform` | 001–049 |
| Agent, Handler, Tool, Memory, Conversation, LLM, Prompt | `bfagent` | 050–099 |
| Story, Travel, Trip, Timing, Drifttales, Content | `travel-beat` | 100–149 |
| MCP, Server, Protocol, Registry, Tool-Server | `mcp-hub` | 150–199 |
| Risk, Assessment, Scoring, Compliance | `risk-hub` | 200–249 |
| CAD, IFC, XGF, XKT, Viewer, Model, BIM | `cad-hub` | 250–299 |
| PPTX, PowerPoint, Slide, Template, Presentation | `pptx-hub` | 300–349 |
| API, Auth, Logging, "alle Apps", "shared", Cross-App | `shared` | 350–399 |
| Trading, Market, Exchange, Bot, Signal, Order, Portfolio | `trading-hub` | 400–449 |

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
2. Create file using TEMPLATE structure below
3. Fill in metadata and content from user's concept (if provided)

### Pflicht-Metadaten-Template (IMMER verwenden)

```markdown
| Attribut       | Wert                        |
|----------------|-----------------------------|
| **Status**     | Proposed                    |
| **Scope**      | [scope aus Step 1]          |
| **Repo**       | [repo aus Step 1]           |
| **Erstellt**   | [YYYY-MM-DD]                |
| **Autor**      | Achim Dehnert               |
| **Reviewer**   | –                           |
| **Supersedes** | –                           |
| **Relates to** | [ADR-NNN (Titel), ...]      |
```

**Pflichtfelder**: `Status`, `Scope`, `Repo`, `Erstellt` — niemals weglassen.

**Gültige Status-Werte**: `Proposed` | `Accepted` | `Deprecated` | `Superseded` | `Draft`

**Gültige Repo-Werte**: `platform` | `bfagent` | `travel-beat` | `mcp-hub` | `risk-hub` | `cad-hub` | `pptx-hub` | `shared` | `trading-hub`

### Pflicht-Abschnitte (Reihenfolge einhalten)

```
1. Kontext (1.1 Ausgangslage, 1.2 Problem/Lücken, 1.3 Constraints)
2. Entscheidung
3. Betrachtete Alternativen
4. Begründung im Detail
5. Implementation Plan (phasenweise wenn sinnvoll)
6. Risiken
7. Konsequenzen (7.1 Positiv, 7.2 Trade-offs, 7.3 Nicht in Scope)
8. Validation Criteria (pro Phase wenn mehrphasig)
9. Referenzen
10. Changelog
```

## Step 4: INDEX.md aktualisieren (Pflicht nach jedem ADR)

Nach dem Erstellen der ADR-Datei **immer** `docs/adr/INDEX.md` aktualisieren:

1. Neue Zeile in der passenden Sektion eintragen:
   ```
   | [NNN] | [Titel] | `Proposed` | `[repo]` | [ADR-NNN-slug.md](ADR-NNN-slug.md) |
   ```
2. "Letzte Aktualisierung"-Datum oben in INDEX.md aktualisieren

## Step 5: Post-ADR Workflow

After ADR is created and INDEX.md updated, show:

```text
📋 ADR-[NNN] erstellt: [Title]
📋 INDEX.md aktualisiert

Status: Proposed → Review erforderlich
Repo: [repo]

Nächste Schritte:
1. 👀 Review: "Review ADR-[NNN]" (AI + Team)
2. ✅ Approval: Status → Accepted  (dann INDEX.md + ADR-Datei + Changelog aktualisieren)
3. 🚀 Implementation: Gemäß Implementation Plan

Soll ich das ADR jetzt reviewen? [Ja/Nein]
```

## Step 6: ADR Review (if requested)

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

## Step 7: Status-Wechsel-Prozedur

Wenn ein ADR seinen Status ändert (z.B. `Proposed` → `Accepted`), immer **drei Stellen** aktualisieren:

### 7.1 ADR-Datei selbst

```markdown
| **Status**     | Accepted    |   ← ändern
```

Changelog-Eintrag ergänzen:
```markdown
| [YYYY-MM-DD] | Achim Dehnert | Status: Proposed → Accepted |
```

### 7.2 INDEX.md aktualisieren

In `docs/adr/INDEX.md`:
- Status-Spalte der entsprechenden Zeile ändern
- "Letzte Aktualisierung"-Datum oben aktualisieren

### 7.3 Ausgabe nach Status-Wechsel

```text
✅ ADR-[NNN] Status aktualisiert: [Alt] → [Neu]

Geändert in:
- docs/adr/ADR-[NNN]-[slug].md  (Status-Feld + Changelog)
- docs/adr/INDEX.md             (Status-Spalte + Datum)
```

### Gültige Status-Übergänge

```
Proposed ──▶ Accepted     (nach positivem Review)
Proposed ──▶ Draft        (nach Review mit Änderungsbedarf)
Draft    ──▶ Proposed     (nach Überarbeitung)
Accepted ──▶ Deprecated   (veraltet, kein direkter Nachfolger)
Accepted ──▶ Superseded   (abgelöst durch ADR-NNN)
```
