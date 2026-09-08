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
  - proposed_id: informativ nur (Nummer faellt erst beim Merge, ADR-228 — siehe Step 3)
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

Entwurfs-Slug: <kebab-slug> (Nummer faellt beim Merge — ADR-228, siehe Step 3)
Datei: {ADR_PATH}/ADR-DRAFT-<kebab-slug>.md
Pre-Validation: ✅ keine Konflikte / ⚠️ [N] Konflikte

Scope korrekt? [Ja/Nein]
```

## Step 3: Entwurfsdatei statt Nummer (ADR-228 — Nummer faellt erst beim Merge)

> Seit 2026-09-08 vergibt der Autor **keine** Nummer mehr beim Anlegen
> (platform#2931 setzt ADR-228 um). Ein neues ADR startet als Entwurf:
> `id: ADR-000` im Frontmatter (reservierter Platzhalter, validiert sauber),
> Dateiname `ADR-DRAFT-<kebab-slug>.md`. Kurz vor dem Merge vergibt
> `tools/adr_allocate.py --apply` die echte Nummer — siehe Step 6.

### 3.1 Slug bilden

Kebab-Case aus dem Titel ableiten (z.B. "Adopt X for Y" → `adopt-x-for-y`).
Keine Nummer wählen, `scripts/adr_next_number.py` NICHT für die eigene Datei
aufrufen — das Skript liefert nur die Sicht auf `main` zum jetzigen Zeitpunkt,
die beim Merge längst veraltet sein kann (genau die Race Condition, die
ADR-228 beseitigt).

### 3.2 Index NICHT anfassen — auch nicht generieren

> ⛔ **`docs/adr/INDEX.md` ist eine generierte Datei.** Eine Entwurfsdatei
> (`ADR-DRAFT-*.md`) wird von `scripts/gen_adr_index.py` **bewusst
> übersprungen** (Dateiname matcht nicht `ADR-\d{3}`) — ein Lauf beim Anlegen
> des Entwurfs wäre ein No-Op und ändert nichts am Commit. Die Index-Zeile
> entsteht automatisch, wenn `tools/adr_allocate.py --apply` beim Merge
> läuft (Step 6). Nichts von Hand in `INDEX.md` eintragen.

### 3.4 Frontmatter lokal validieren (vor dem Push)

```bash
iil-adrfw validate docs/adr
```

Erwartet: `N/N (100.0%) ✓ All ADRs valid` — die Entwurfsdatei mit `id: ADR-000`
validiert sauber (reservierter Platzhalter, ADR-228).

> Der Validator scannt **alle** ADRs, nicht nur den neuen. Ein einziger Alt-Key
> (`date:`, `decision-makers:`, `relates_to:`) in irgendeiner Datei rötet die
> **gesamte** ADR-Pipeline — der Fehler sieht dann so aus, als läge er am neuen
> ADR. Schema aus einer aktuellen Nachbar-ADR abschauen, nicht aus dem Gedächtnis.

## Step 4: Create ADR File

Nach Slug-Bestimmung (Step 3.1) — **keine Nummer**, siehe ADR-228:

**Option A — lokal (wenn Git-Checkout vorhanden):**
Datei `{ADR_PATH}/ADR-DRAFT-[kebab-slug].md` erstellen.

**Option B — via GitHub MCP (wenn kein lokaler Checkout):**
```
{GH_PREFIX}_create_or_update_file(
  owner:   "{REPO_OWNER}",
  repo:    "{REPO_NAME}",
  path:    "{ADR_PATH}/ADR-DRAFT-[slug].md",
  content: "<Template unten>",
  message: "docs(adr): draft [Titel]",
  branch:  "<Feature-Branch, NICHT main>"
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

Nach dem Erstellen der Entwurfsdatei **sofort** in pgvector speichern — die
Nummer existiert noch nicht (ADR-228), daher ein **Entwurfs-entry_id** mit dem
Slug statt der Nummer:

```
{ORC_PREFIX}agent_memory(
  operation: "upsert",
  agent: "cascade",
  entry: {
    entry_id:   "ADR-{REPO-UPPERCASE}-DRAFT-[slug]",  // muss [A-Z][A-Z0-9\-]+ matchen
    entry_type: "agent_decision",                     // enum: solved_problem|repo_context|open_task|agent_decision|error_pattern
    agent:      "cascade",
    title:      "ADR-DRAFT: [Titel] — {REPO_NAME} (Status: Proposed)",
    content:    "Repo: {REPO_NAME}\nPfad: {ADR_PATH}/ADR-DRAFT-[slug].md\nThema: [Thema]\nScope: [scope]\nStatus: Proposed (Entwurf, Nummer faellt beim Merge)\nErstellt: [YYYY-MM-DD]\nKern-Entscheidung: [1-2 Sätze]\nAlternativen verworfen: [kurz]",
    tags:       ["adr", "{REPO_NAME}", "proposed", "draft", "[scope]"]
  }
)
```

> **Warum Pflicht?** pgvector ist der zentrale Memory-Store für ALLE Repos.
> Jede ADR die hier gespeichert ist, kann jede künftige Session überall finden
> via `{ORC_PREFIX}agent_memory(operation: "query", filter_type: "agent_decision", filter_tag: "adr")` — repobergreifend.
>
> **Nach der Nummernvergabe (Step 6) nachziehen:** einen zweiten Eintrag mit
> `entry_id: "ADR-{REPO-UPPERCASE}-[NNN]"` (echte Nummer) upserten und den
> `DRAFT`-Eintrag als erledigt markieren (Tag `draft` entfernen oder Eintrag
> löschen) — sonst bleiben zwei parallele Erinnerungen an dieselbe Entscheidung
> stehen.

## Step 6: Vor dem Merge — Nummer vergeben (ADR-228, PFLICHT)

> Es gibt keine Merge-Queue im Repo (`main-required-checks` kennt nur
> `required_status_checks` + `pull_request`) — die Vergabe läuft deshalb als
> **letzter Schritt vor dem Merge**, ausgelöst vom Autor. Das Gate
> `tools/adr_draft_guard.py` (gating auf dem `push`-Lauf gegen `main`)
> erzwingt, dass sie passiert ist — ein Entwurf, der `main` erreicht, macht
> den nächsten Lauf rot.

```bash
python3 tools/adr_allocate.py --apply
```

Das Werkzeug (Trockenlauf ohne `--apply` zeigt die geplante Nummer vorab):

* benennt `ADR-DRAFT-[slug].md` per `git mv` in `ADR-NNN-[slug].md` um
  (Historie bleibt erhalten),
* ersetzt `id: ADR-000` → `id: ADR-NNN`, die H1 und übrige `ADR-DRAFT`-Selbstverweise,
* regeneriert `docs/adr/INDEX.md` + `docs/adr/index.json`
  (`scripts/gen_adr_index.py`) — **beide** gehören in den Commit.

**Warum Handarbeit hier zuverlässig fehlschlägt** (Realfall ADR-280, 2026-07-21
— drei Abweichungen in einem einzigen handgepflegten Eintrag): Index-Titel muss
zeichengleich zur H1 sein, die Kopfzeile „Next free ADR number" wird beim
Zählen leicht vergessen, `index.json` wird komplett übersehen. Deshalb: nie von
Hand, immer über `tools/adr_allocate.py --apply`.

**Merge-Konflikt in `INDEX.md`/`index.json`?** Nicht von Hand mergen — auf
`origin/main` rebasen, `tools/adr_allocate.py --apply` erneut laufen lassen
(idempotent, siehe REC-4/ADR-228), das Ergebnis committen.

Danach `iil-adrfw validate docs/adr` erneut grün bestätigen (Step 3.4), Step 5
mit der echten Nummer nachziehen, dann erst mergen:

```text
ADR-[NNN] vergeben: [Title]
Index regeneriert: INDEX.md + index.json (tools/adr_allocate.py --apply)
Frontmatter validiert: N/N gültig (iil-adrfw validate docs/adr)
pgvector Memory: nachgezogen unter adr:{REPO_NAME}:ADR-[NNN]

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

> ⛔ **`INDEX.md` nicht von Hand anfassen** — siehe Step 3.2/6. Die Status-Spalte
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

- [ ] Entwurfsdatei `ADR-DRAFT-<slug>.md` mit `id: ADR-000` angelegt (Step 3/4) — **keine** Nummer selbst gewählt
- [ ] ADR-Datei aus `docs/templates/adr-template.md` (Step 4), Struktur nicht neu erfunden
- [ ] `iil-adrfw validate docs/adr` grün, `N/N (100.0%)` (Step 3.4) — auch für die Entwurfsdatei
- [ ] pgvector-Entwurfs-Upsert abgesetzt (Step 5, `entry_id` mit `-DRAFT-<slug>`)
- [ ] Vor dem Merge: `python3 tools/adr_allocate.py --apply` gelaufen — **`INDEX.md` UND `index.json`** im Commit (Step 6)
- [ ] Alle im ADR referenzierten `ADR-NNN` existieren wirklich (`ls docs/adr/ADR-NNN-*`)
- [ ] Bei `supersedes:`/`amends:` — Statuswechsel des Vorgängers bewusst **jetzt oder aufgeschoben**, und wenn aufgeschoben: als Zeile im Migration Tracking (Step 8.1)
- [ ] §8 Confirmation hat mindestens 2 **prüfbare** Mechanismen, kein „wird beachtet"
- [ ] pgvector-Eintrag mit der echten Nummer nachgezogen, Entwurfs-Eintrag aufgeräumt (Step 5/6)
- [ ] `tools/adr_draft_guard.py --adr-dir docs/adr` lokal grün, bevor der PR auf `main` gemerged wird (kein `ADR-DRAFT-*` mehr, kein `id: ADR-000`)

---

## Anti-Patterns

- ❌ Selbst eine Nummer wählen statt `ADR-DRAFT-<slug>.md` + `id: ADR-000` (ADR-228)
- ❌ Einen Entwurf ohne `id: ADR-000` anlegen — Schema lehnt jede andere Platzhalterform ab
- ❌ Einen Entwurf ungewandelt mergen (`ADR-DRAFT-*` oder `id: ADR-000` auf `main`) — `tools/adr_draft_guard.py` rötet den nächsten Lauf
- ❌ `INDEX.md` von Hand ergänzen — sie ist generiert, der CI-Gate diffed dagegen
- ❌ `index.json` vergessen — sie ist Teil desselben `tools/adr_allocate.py --apply`-Laufs
- ❌ Vorgänger-ADR auf `superseded` setzen, während der Nachfolger noch `proposed` ist
- ❌ Merge-Konflikt in `INDEX.md`/`index.json` von Hand auflösen statt `tools/adr_allocate.py --apply` neu laufen zu lassen
- ❌ §8 Confirmation mit unprüfbaren Zusagen füllen („wird im Review beachtet")

---

## Changelog

- 2026-09-08: **ADR-228 umgesetzt (platform#2931)** — Schritte 2–6 auf die
  Entwurfsform umgestellt: neue ADRs starten als `ADR-DRAFT-<slug>.md` mit
  `id: ADR-000`, die Nummer fällt erst kurz vor dem Merge über
  `tools/adr_allocate.py --apply` (Step 6, ersetzt das alte `scripts/adr_next_number.py`-Vorgehen
  am Autorenzeitpunkt); `tools/adr_draft_guard.py` verhindert, dass ein Entwurf
  `main` erreicht. pgvector-Entry-ID nutzt bis zur Vergabe einen `-DRAFT-<slug>`-Platzhalter.
- 2026-07-21: **Step 3.3 korrigiert** — „INDEX.md ergänzen" war irreführend und
  führte direkt in den roten Gate „ADR index freshness (gating)". Jetzt:
  `gen_adr_index.py` als Pflichtschritt, mit den drei konkreten Fehlerarten aus
  dem Realfall ADR-280. Neu: Step 3.4 (lokales `iil-adrfw validate`),
  Supersession-Regel in 8.1, Abschluss-Checkliste, Anti-Patterns, dieser
  Changelog. Auslöser: platform#1291 — die Anleitung selbst war die Fehlerquelle.
