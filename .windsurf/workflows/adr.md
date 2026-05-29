---
description: Create new ADR with automatic scope detection, proper structure, and pgvector memory storage
mode: write
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

## Step 0.5: Repo-Kontext aus project-facts.md lesen (PFLICHT — kein Hardcoding!)

Vor jedem weiteren Schritt aus project-facts.md (always_on) lesen:

```
Aus project-facts.md entnehmen:
- REPO_OWNER   (z.B. "achimdehnert" oder "meiki-lra")
- REPO_NAME    (z.B. "platform" oder "meiki-docs")
- ADR_PATH     (z.B. "docs/adr" oder "docs/03-technisches-handbuch/architektur")
- GH_PREFIX    (GitHub MCP prefix, z.B. "mcp1_" oder "mcp0_")
- ORC_PREFIX   (Orchestrator MCP prefix; auf Dev Desktop "mcp1_", auf WSL/Prod "mcp2_" — IMMER aus project-facts.md lesen)
```

> **NIEMALS** owner, repo, Pfade oder Prefixe hardcoden.
> project-facts.md ist die einzige Source of Truth für repo-spezifische Werte.

## Step 1: Analyze Topic and Detect Scope

Analyze the topic using these keywords:

| Keywords | Scope / Repo | Number Range |
|----------|-------------|--------------|
| CI/CD, Deployment, Docker, DB, Monitoring, Security, Platform-wide, Work Management, Governance | `platform` | 001–099 |
| Agent, Handler, Tool, Memory, Conversation, LLM, Prompt | `bfagent` | 100–149 |
| Story, Travel, Trip, Timing, Drifttales, Content | `travel-beat` | 150–199 |
| MCP, Server, Protocol, Registry, Tool-Server | `mcp-hub` | 200–249 |
| Risk, Assessment, Scoring, Compliance | `risk-hub` | 250–299 |
| CAD, IFC, XGF, XKT, Viewer, Model, BIM | `cad-hub` | 300–349 |
| PPTX, PowerPoint, Slide, Template, Presentation | `pptx-hub` | 350–399 |
| API, Auth, Logging, "alle Apps", "shared", Cross-App | `shared` | 450–499 |
| Trading, Market, Exchange, Bot, Signal, Order, Portfolio | `trading-hub` | 400–449 |

## Step 1.5: ADR Pre-Validation via iil-adrfw (PFLICHT)

> Nutzt `iil-adrfw` MCP Tools (Prefix aus project-facts.md, aktuell `mcp2_`).

Vor Erstellung prüfen ob der ADR-Vorschlag konsistent ist:

```
MCP: mcp2_adr_propose(
    title="<Decision Statement im Imperativ>",
    domains=["<domain1>", "<domain2>"],
    deciders=["Achim Dehnert"],
    rationale_summary="<Warum diese Entscheidung? Min. 20 Zeichen.>"
)
→ Liefert:
  - proposed_id: nächste freie Nummer
  - conflicts: Duplikate, verpasste Supersessions
  - closes_open_questions: welche bestehenden Open Questions dieser ADR beantwortet
  - blocks_publish: True wenn HIGH-confidence Konflikte existieren
```

**Bei `blocks_publish: True`** → User informieren, Konflikte zuerst lösen.
**Bei `conflicts`** → im ADR-Body unter "Considered Options" referenzieren.
**Bei `closes_open_questions`** → im bestehenden ADR die Frage als "resolved" markieren.

## Step 2: Show Scope Suggestion

```text
ADR-Vorschlag

Thema: "[User's topic]"

Scope-Erkennung:
   → [scope] ([range])

Nächste Nummer: ADR-[NNN] (aus mcp2_adr_propose oder Step 3)
Datei: {ADR_PATH}/ADR-[NNN]-[title-slug].md
Pre-Validation: ✅ keine Konflikte / ⚠️ [N] Konflikte

Scope korrekt? [Ja/Nein]
```

## Step 3: Nächste ADR-Nummer ermitteln (PFLICHT — nie aus Gedächtnis!)

### 3.1 Primär: adr_next_number.py (falls im Repo vorhanden)

```bash
python3 scripts/adr_next_number.py
```

Ausgabe: `ADR-NNN` — diese Nummer direkt verwenden.

**Konflikt-Check:**
```bash
python3 scripts/adr_next_number.py --check
```

### 3.2 Fallback: GitHub API (wenn Script nicht vorhanden — ERLAUBT)

Wenn `scripts/adr_next_number.py` nicht existiert (z.B. Docs-Repos, externe Repos):

```
{GH_PREFIX}_get_file_contents(
  owner: "{REPO_OWNER}",   ← aus project-facts.md
  repo:  "{REPO_NAME}",    ← aus project-facts.md
  path:  "{ADR_PATH}"      ← aus project-facts.md
)
→ Alle Einträge mit Pattern ADR-NNN-*.md auflisten
→ Höchste Zahl bestimmen
→ Nächste Nummer = max + 1 (dreistellig: 009, 010, ...)
```

> **NIEMALS** manuelle Zählung oder Schätzung aus Gedächtnis.
> Script-Fallback auf GitHub API ist explizit erlaubt wenn Script fehlt.

### 3.3 INDEX.md sofort aktualisieren

Nach dem Erstellen der ADR-Datei **sofort** INDEX.md ergänzen (falls vorhanden).

## Step 4: Create ADR File

Nach Nummern-Bestimmung:

**Option A — lokal (wenn Git-Checkout vorhanden):**
Datei `{ADR_PATH}/ADR-NNN-[title-slug].md` erstellen.

**Option B — via GitHub MCP (wenn kein lokaler Checkout):**
```
{GH_PREFIX}_create_or_update_file(
  owner:   "{REPO_OWNER}",
  repo:    "{REPO_NAME}",
  path:    "{ADR_PATH}/ADR-[NNN]-[slug].md",
  content: "<Template unten>",
  message: "docs(ADR-[NNN]): create [Titel]",
  branch:  "main"
)
```

### Pflicht-Metadaten-Template (IMMER verwenden)

```markdown
| Attribut       | Wert                        |
|----------------|------------------------------|
| **Status**     | Proposed                    |
| **Scope**      | [scope aus Step 1]          |
| **Repo**       | [repo aus Step 1]           |
| **Erstellt**   | [YYYY-MM-DD]                |
| **Autor**      | Achim Dehnert               |
| **Reviewer**   | –                           |
| **Supersedes** | –                           |
| **Relates to** | [ADR-NNN (Titel), ...]      |
```

**Pflicht-Abschnitte (Reihenfolge einhalten):**

```
1. Kontext (1.1 Ausgangslage, 1.2 Problem/Lücken, 1.3 Constraints)
2. Entscheidung
3. Betrachtete Alternativen
4. Begründung im Detail
5. Implementation Plan
6. Risiken
7. Konsequenzen (7.1 Positiv, 7.2 Trade-offs, 7.3 Nicht in Scope)
8. Validation Criteria
9. Glossar
10. Referenzen
11. Changelog
```

**Glossar-Abschnitt (Pflicht — LRA-Lesbarkeit):**

Jede Abkürzung und jeder Fachbegriff, der für LRA-Mitarbeiter ohne IT-Hintergrund
nicht selbsterklärend ist, MUSS im Glossar erläutert werden.

```markdown
## Glossar

| Abkürzung | Bedeutung |
|-----------|-----------|
| **XYZ** | Ausgeschriebener Name — kurze Erklärung in einem Satz |
```

Typische Kandidaten: ADR, KI, ML, LLM, HITL, OCR, API, DSGVO, DMS, QR, HMAC, CI/CD, etc.

## Step 5: pgvector Memory sichern (PFLICHT — jede neue ADR, alle Repos)

Nach dem Erstellen der ADR-Datei **sofort** in pgvector speichern:

```
{ORC_PREFIX}agent_memory(
  operation: "upsert",
  agent: "cascade",
  entry: {
    entry_id:   "ADR-{REPO-UPPERCASE}-[NNN]",       // muss [A-Z][A-Z0-9\-]+ matchen
    entry_type: "agent_decision",                   // enum: solved_problem|repo_context|open_task|agent_decision|error_pattern
    agent:      "cascade",
    title:      "ADR-[NNN]: [Titel] — {REPO_NAME} (Status: Proposed)",
    content:    "Repo: {REPO_NAME}\nPfad: {ADR_PATH}/ADR-[NNN]-[slug].md\nThema: [Thema]\nScope: [scope]\nStatus: Proposed\nErstellt: [YYYY-MM-DD]\nKern-Entscheidung: [1-2 Sätze]\nAlternativen verworfen: [kurz]",
    tags:       ["adr", "{REPO_NAME}", "proposed", "[scope]"]
  }
)
```

> **Warum Pflicht?** pgvector ist der zentrale Memory-Store für ALLE Repos.
> Jede ADR die hier gespeichert ist, kann jede künftige Session überall finden
> via `{ORC_PREFIX}agent_memory(operation: "query", filter_type: "agent_decision", filter_tag: "adr")` — repobergreifend.

## Step 6: Post-ADR Workflow

```text
ADR-[NNN] erstellt: [Title]
INDEX.md aktualisiert
pgvector Memory: gespeichert unter adr:{REPO_NAME}:ADR-[NNN]

Status: Proposed → Review erforderlich

Nächste Schritte:
1. Review: "/adr-review ADR-[NNN]"
2. Approval: Status → Accepted
3. Implementation: Gemäß Implementation Plan

Soll ich das ADR jetzt reviewen? [Ja/Nein]
```

## Step 7: ADR Review (if requested)

Review gegen diese Kriterien:

| Kategorie | Prüfpunkte |
|-----------|------------|
| **Vollständigkeit** | Context, Decision, Consequences vorhanden? |
| **Klarheit** | Verständlich formuliert? Keine Mehrdeutigkeiten? |
| **Begründung** | Alternativen betrachtet? Entscheidung nachvollziehbar? |
| **Umsetzbarkeit** | Implementation Plan realistisch? Risiken adressiert? |
| **Konsistenz** | Passt zu anderen ADRs? Keine Widersprüche? |

## Step 8: Status-Wechsel-Prozedur

Wenn ein ADR seinen Status ändert (z.B. `Proposed` → `Accepted`):

### 8.1 ADR-Datei + INDEX.md aktualisieren

```markdown
| **Status**     | Accepted    |
```

Changelog-Eintrag ergänzen.

### 8.2 pgvector Memory aktualisieren (gleicher entry_id = Update)

```
{ORC_PREFIX}agent_memory(
  operation: "upsert",
  agent: "cascade",
  entry: {
    entry_id:   "ADR-{REPO-UPPERCASE}-[NNN]",       ← gleicher entry_id = Überschreiben
    entry_type: "agent_decision",
    agent:      "cascade",
    title:      "ADR-[NNN]: [Titel] — {REPO_NAME} (Status: Accepted)",
    content:    "[Aktualisierter Inhalt mit Accepted-Status]",
    tags:       ["adr", "{REPO_NAME}", "accepted", "[scope]"]
  }
)
```

### 8.3 Ausgabe nach Status-Wechsel

```text
ADR-[NNN] Status aktualisiert: [Alt] → [Neu]

Geändert in:
- {ADR_PATH}/ADR-[NNN]-[slug].md  (Status-Feld + Changelog)
- INDEX.md                        (Status-Spalte + Datum)
- pgvector Memory                 (entry_id: ADR-{REPO-UPPERCASE}-[NNN])
```

### Gültige Status-Übergänge

```
Proposed --> Accepted     (nach positivem Review)
Proposed --> Draft        (nach Review mit Änderungsbedarf)
Draft    --> Proposed     (nach Überarbeitung)
Accepted --> Deprecated   (veraltet, kein direkter Nachfolger)
Accepted --> Superseded   (abgelöst durch ADR-NNN)
```
