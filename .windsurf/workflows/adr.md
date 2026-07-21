---
tool_targets: [windsurf-review]
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
>
> ℹ️ **CC-Fallback:** In Claude-Code-Sessions heißen die Tools `mcp__<orchestrator-prefix>__adr_*`.
> Bindet die Session keinen ADR-MCP-Server, ist der Fallback direkte Reads in `docs/adr/` bzw.
> der `iil-adrfw`-CLI-Weg — der ADR-Flow bricht nicht ab, nur die MCP-Automatik entfällt.

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

### 3.3 Index NEU GENERIEREN — niemals von Hand ergänzen

> ⛔ **`docs/adr/INDEX.md` ist eine generierte Datei** (Zeile 1: `AUTO-GENERATED
> by scripts/gen_adr_index.py — do not edit manually`). Eine Zeile von Hand
> einzutragen ist **kein** gültiger Abschluss — der CI-Gate „ADR index freshness
> (gating)" regeneriert den Index und diffed gegen den Commit.

Nach dem Erstellen der ADR-Datei (Step 4), **nicht davor** — der Generator liest
die fertige Datei:

```bash
python3 scripts/gen_adr_index.py
```

Erzeugt **zwei** Artefakte, beide gehören in den Commit:

| Datei | Inhalt |
|---|---|
| `docs/adr/INDEX.md` | Tabellenzeile, Kopfzeile „Next free ADR number", Datum |
| `docs/adr/index.json` | maschinenlesbar; trägt Rückreferenzen `superseded_by` / `amended_by` automatisch in die *referenzierten* ADRs nach |

**Warum Handarbeit hier zuverlässig fehlschlägt** (Realfall ADR-280, 2026-07-21 —
alle drei Abweichungen in einem einzigen handgepflegten Eintrag):

1. Der Titel in der Index-Zeile wird aus der **H1-Überschrift** des ADR abgeleitet.
   Eine sinngemäß gleiche, aber nicht zeichengleiche Formulierung ⇒ Diff ⇒ rot.
2. `> **Next free ADR number:**` im Index-Kopf wird **nicht** mitgezählt.
3. `docs/adr/index.json` wird komplett vergessen — sie steht in keiner Anleitung,
   die von „INDEX.md ergänzen" spricht.

**Fallback ohne Generator** (Docs-/Fremd-Repos ohne `scripts/gen_adr_index.py`):
dort ist der Index handgepflegt und Handarbeit korrekt. Vorher prüfen:
`ls scripts/gen_adr_index.py` bzw. Zeile 1 von `INDEX.md` auf den
`AUTO-GENERATED`-Marker lesen.

### 3.4 Frontmatter lokal validieren (vor dem Push)

```bash
iil-adrfw validate docs/adr
```

Erwartet: `N/N (100.0%) ✓ All ADRs valid`.

> Der Validator scannt **alle** ADRs, nicht nur den neuen. Ein einziger Alt-Key
> (`date:`, `decision-makers:`, `relates_to:`) in irgendeiner Datei rötet die
> **gesamte** ADR-Pipeline — der Fehler sieht dann so aus, als läge er am neuen
> ADR. Schema aus einer aktuellen Nachbar-ADR abschauen, nicht aus dem Gedächtnis.

**Merge-Konflikt in `INDEX.md`/`index.json`?** Nicht von Hand mergen — auf
`origin/main` rebasen, `gen_adr_index.py` erneut laufen lassen, das Ergebnis
committen. Zwei parallele ADR-PRs kollidieren in diesen generierten Dateien
zwangsläufig; die Auflösung ist immer Neugenerierung, nie Hand-Merge.

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

### Pflicht-Struktur (SSOT: docs/templates/adr-template.md — ADR-271)

Datei-Inhalt = Kopie von `docs/templates/adr-template.md`, Platzhalter ausgefüllt.
NICHT die Struktur neu erfinden oder aus dem Gedächtnis rekonstruieren.

Pflicht-Abschnitte (siehe Template): Metadaten, Repo-Zugehörigkeit, Decision
Drivers, §1 Context and Problem Statement, §2 Considered Options, §3 Decision
Outcome, §4 Implementation Details, §6 Consequences, §8 Confirmation.
Optional (nur wenn zutreffend): §5 Migration Tracking (nur bei Transitions),
§7 Risks, §9 More Information, §10 Changelog.

Sprache (ADR-271 §3.2): Abschnitts-Überschriften kanonisch Englisch (fleet-weit);
Prosa-Sprache frei — Deutsch in LRA-/Behörden-Repos üblich.

Glossar: siehe Template (§Glossar) — Pflicht-Trigger und Kandidatenliste
stehen DORT, nicht hier. Der Skill fügt nichts ein, was das Template
nicht kennt.

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
Index regeneriert: INDEX.md + index.json (gen_adr_index.py)
Frontmatter validiert: N/N gültig (iil-adrfw validate docs/adr)
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

### 8.1 ADR-Datei ändern, Index regenerieren

Der Status steht an **zwei** Stellen in der ADR-Datei — beide ändern:

```yaml
---
status: accepted        # ← Frontmatter: DAS liest der Generator
---
```

```markdown
| **Status**     | Accepted    |   ← Metadaten-Tabelle: das liest der Mensch
```

Changelog-Eintrag ergänzen, dann:

```bash
python3 scripts/gen_adr_index.py     # INDEX.md + index.json ziehen den Status nach
```

> ⛔ **`INDEX.md` nicht von Hand anfassen** — siehe Step 3.3. Die Status-Spalte
> im Index ist abgeleitet, keine eigene Wahrheit.

**Regel für Supersession/Amendment — Relation ≠ Statuswechsel:**
Trägt das neue ADR `supersedes: [ADR-X]`, wird der Status von ADR-X **erst dann**
auf `superseded` gesetzt, wenn das **neue** ADR selbst `accepted` ist. Ein
„superseded by" auf einen erst *vorgeschlagenen* Nachfolger behauptet eine
Ablösung, die niemand beschlossen hat. Die Relation ist trotzdem sofort
festgehalten: `gen_adr_index.py` trägt `superseded_by`/`amended_by` automatisch
in `index.json` nach. Der aufgeschobene Statuswechsel gehört als Zeile ins
Migration Tracking des neuen ADR — sonst geht er verloren.
(Realfall ADR-280 → ADR-229, 2026-07-21.)

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
- {ADR_PATH}/ADR-[NNN]-[slug].md  (Frontmatter status: + Metadaten-Tabelle + Changelog)
- INDEX.md + index.json           (regeneriert via gen_adr_index.py)
- pgvector Memory                 (entry_id: ADR-{REPO-UPPERCASE}-[NNN])
```

### Gültige Status-Übergänge

```
Proposed --> Accepted     (nach positivem Review)
Proposed --> Draft        (nach Review mit Änderungsbedarf)
Proposed --> Superseded   (nie beschlossen, aber vom Nachfolger mit abgeräumt —
                           NUR wenn der Nachfolger selbst accepted ist, s. 8.1)
Draft    --> Proposed     (nach Überarbeitung)
Accepted --> Deprecated   (veraltet, kein direkter Nachfolger)
Accepted --> Superseded   (abgelöst durch ADR-NNN)
```

---

## Abschluss-Checkliste (PFLICHT — vor „fertig")

Diese Liste existiert, weil ein langes Schritt-für-Schritt-Dokument beim Lesen
überflogen statt abgearbeitet wird. Jede Zeile einmal aktiv gegenprüfen; ein
bewusstes „übersprungen, weil X" ist in Ordnung, ein stilles Auslassen nicht.

- [ ] Nummer aus `scripts/adr_next_number.py` (Step 3.1) — **nicht** geschätzt
- [ ] ADR-Datei aus `docs/templates/adr-template.md` (Step 4), Struktur nicht neu erfunden
- [ ] `python3 scripts/gen_adr_index.py` gelaufen — **`INDEX.md` UND `index.json`** im Commit (Step 3.3)
- [ ] `iil-adrfw validate docs/adr` grün, `N/N (100.0%)` (Step 3.4)
- [ ] Alle im ADR referenzierten `ADR-NNN` existieren wirklich (`ls docs/adr/ADR-NNN-*`)
- [ ] Bei `supersedes:`/`amends:` — Statuswechsel des Vorgängers bewusst **jetzt oder aufgeschoben**, und wenn aufgeschoben: als Zeile im Migration Tracking (Step 8.1)
- [ ] §8 Confirmation hat mindestens 2 **prüfbare** Mechanismen, kein „wird beachtet"
- [ ] pgvector-Upsert abgesetzt (Step 5)

---

## Anti-Patterns

- ❌ `INDEX.md` von Hand ergänzen — sie ist generiert, der CI-Gate diffed dagegen
- ❌ `index.json` vergessen — sie ist Teil desselben Generator-Laufs
- ❌ ADR-Nummer aus dem Gedächtnis oder aus einem älteren Branch übernehmen
- ❌ Vorgänger-ADR auf `superseded` setzen, während der Nachfolger noch `proposed` ist
- ❌ Merge-Konflikt in `INDEX.md`/`index.json` von Hand auflösen statt neu generieren
- ❌ §8 Confirmation mit unprüfbaren Zusagen füllen („wird im Review beachtet")

---

## Changelog

- 2026-07-21: **Step 3.3 korrigiert** — „INDEX.md ergänzen" war irreführend und
  führte direkt in den roten Gate „ADR index freshness (gating)". Jetzt:
  `gen_adr_index.py` als Pflichtschritt, mit den drei konkreten Fehlerarten aus
  dem Realfall ADR-280. Neu: Step 3.4 (lokales `iil-adrfw validate`),
  Supersession-Regel in 8.1, Abschluss-Checkliste, Anti-Patterns, dieser
  Changelog. Auslöser: platform#1291 — die Anleitung selbst war die Fehlerquelle.
