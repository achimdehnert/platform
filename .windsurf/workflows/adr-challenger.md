---
description: Adversarial review of a proposed ADR — find conflicts, right-size, surface 1-2 strong counter-arguments. Read-only. Does NOT write or modify ADRs.
mode: read-only
---

# /adr-challenger — Adversarial ADR Stress-Test

> **Wann:** Bevor ein Draft als Accepted markiert wird, oder wenn ein bestehender ADR auf "ist das noch tragfähig?" geprüft werden soll.
> **Wann NICHT:** Disambiguation existierender ADRs → `/adr-curator`. Schema/Format-Check → `/adr-review`. Vollständigen Audit → `/adr-health`.

## Verwendung

```
/adr-challenger <ADR-NNN | path/to/draft.md>
```

Beispiele:
- `/adr-challenger ADR-204`
- `/adr-challenger ~/github/platform/docs/adr/ADR-DRAFT-routing.md`

---

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT)

```
Aus project-facts.md entnehmen:
- ADR_PATH
- ORC_PREFIX
- ADRFW_PREFIX
```

> NIEMALS Pfade/Prefixe hardcoden.

---

## Step 1: Draft laden + Threshold-Reality-Check

Read den Draft komplett.

Gegen `~/.claude/policies/adr-threshold.md` prüfen:
- Folgt das einem bestehenden Pattern (z.B. "noch ein Platform Agent")? → kein ADR nötig
- Reversibel durch Entfernen einer App / eines Tasks? → kein ADR nötig
- Lokal in einem Repo ohne Cross-Cutting-Impact? → kein ADR nötig
- Code-Style oder Refactor? → kein ADR nötig

**Wenn Threshold nicht überschritten:** Report endet hier mit "CHANGELOG + PR-Beschreibung reicht, kein ADR".

---

## Step 2: Drift-Memory laden (operationalisiert 🌀-Lehren)

```
MCP: {ORC_PREFIX}agent_memory_search(query="drift:adr OR iteration_count", limit=5)
MCP: {ORC_PREFIX}agent_memory_search(query="feedback:adr smallest-viable", limit=3)
```

Zitiere relevante Lehren im Report. Insbesondere:
- "3+ Architektur-Iterationen ohne Konvergenz = falsches Framing" (🌀 ADR-199 → ADR-201)
- Smallest-viable-ADR ~120 Zeilen Pattern

---

## Step 3: Schema-Validation (deterministisch)

```
MCP: {ADRFW_PREFIX}adr_validate(req={"adr_dir": "<ADR_PATH absolute>"})
→ erwartet: passed=true für ALLE ADRs im Korpus (kein per-file Modus)
```

**Achtung:** `adr_validate` validiert das **gesamte Verzeichnis**, nicht einen einzelnen Draft. Filtere im Output auf den Draft-Namen. Wenn Draft noch nicht im Verzeichnis liegt: Draft temporär dorthin kopieren ODER Frontmatter manuell gegen Schema v3 prüfen (lieber zweites — keine Side-Effects).

Bei Schema-Fehlern: hart abbrechen mit Liste der Verstöße. Adversarial Review macht nur Sinn auf strukturell gültigen Drafts.

---

## Step 4: Conflict-Detection gegen Korpus

```
MCP: {ADRFW_PREFIX}adr_query(req={"question": "<draft.decision_summary as natural question>"})
→ liefert: {primary_answer, citations[], open_questions[], confidence, routing}
```

Für Top-3-5 Citations: **direkten File-Read** der zitierten ADRs + manuell vergleichen (Decision-Verb, Scope, Status). `adr_diff` ist **nicht** das richtige Tool dafür — es vergleicht Constitution-Sets (temporal oder zwischen Repos), keine ADR-Paare.

Identifiziere:
- **Hard conflict:** beide accepted, widersprüchliche Decision-Verbs
- **Soft conflict:** überlappender Scope, aber andere Concerns
- **Implicit supersession:** Draft macht ADR-X obsolet, nennt es aber nicht in `supersedes:`

---

## Step 5: Cross-Repo-Impact

⚠️ **Direction-Note:** `adr_impact(file_path=...)` gibt zurück welche ADRs für eine Datei gelten — **Gegenteil** von "welche Files referenzieren diesen ADR".

Für letzteres direkter Grep auf Draft-ID:
```bash
grep -rn "<DRAFT-ID>" ~/github/ --include="*.py" --include="*.md" --include="*.toml" -l 2>/dev/null | wc -l
```

Bei neuen Drafts ohne ID gibt es noch keine Refs — stattdessen Scope-Abschätzung über `scope.repos` im Frontmatter. Wenn Impact > 3 Repos und Draft hat keinen Migrations-Plan im Body → Challenge raisen.

---

## Step 6: Right-Sizing-Check (🌀 ADR-201-Lehre)

Heuristiken:
- **Line-Count:** Body > 180 Zeilen → "smallest-viable cut nötig"
- **Decision-Verb-Count:** mehr als 1 Verb im Title ("introduce X **and** standardize Y") → Split in 2 ADRs
- **Concern-Count:** mehr als 1 abgegrenzte Problem-Domain im Body → Split-Vorschlag
- **Iteration-History:** Wenn Draft Version v3+ oder mehrfach rejected in Memory → "falsches Framing"-Verdacht zitieren

---

## Step 7: Adversarial-Counter-Arguments (LLM-Judgment)

Generiere **1-2 stärkste Gegenargumente** als Steel-Man, nicht Stroh-Mann:
- Welcher rational Stakeholder könnte begründet widersprechen?
- Welche Annahme im Draft ist unausgesprochen und falsifizierbar?
- Welche Alternative im "Considered Options"-Abschnitt verdient mehr Gewicht?

Format pro Counter:
```
**Challenger #N (Confidence: 0-100):**
Argument: <1-2 Sätze>
Konsequenz wenn ignoriert: <1 Satz>
Was würde diesen Counter widerlegen: <1 Satz>
```

---

## Step 8: Open-Question-Aging

```
MCP: {ADRFW_PREFIX}adr_audit(req={"auditors": ["open_question_aging"]})
→ liefert: aggregierte Findings über ALLE ADRs (kein per-draft Filter)
```

Output post-process: filtere `findings[]` auf `adr_id == "<DRAFT-ID>"`. Wenn Draft Open Questions > 7 Tage alt enthält ohne Update → Challenge: "Decide or close before merging Accepted".

---

## Output-Format

```
## ADR Challenger Report — <ADR-ID or Draft-Filename>

### Threshold Verdict
✅ ADR-worthy / ❌ CHANGELOG reicht / ⚠️ borderline (Grund)

### Schema
✅ Passed / ❌ <list violations>

### Conflict-Map
- ADR-XXX: hard conflict on <verb> — Draft muss `supersedes: ADR-XXX` setzen oder Scope abgrenzen
- ADR-YYY: soft conflict on <scope> — Erwähnung im "Considered Options" erwartet

### Right-Sizing
- Line count: NNN (Ziel: ≤180)
- Decision verbs: N
- Concerns: N
- Iteration history: <count> prior versions (Memory)
- Verdict: ✅ smallest-viable / ⚠️ split-candidate / ❌ smallest-viable cut required

### Cross-Repo Impact
N repos touched. Migration plan: present / **missing — challenge raised**.

### Steel-Man Challengers
**#1 (Confidence 75):** <Argument>
   Folge: <…>
   Falsifizierbar durch: <…>

**#2 (Confidence 60):** <Argument>
   ...

### Drift-Memory Citations
- 🌀 ADR-199 → ADR-201: "3+ Iterationen = falsches Framing"
- [andere relevante Memories]

### Recommendation
- [ ] Adress Challenger #1 in Decision rationale
- [ ] Split into ADR-A (verb-1) + ADR-B (verb-2)
- [ ] Add `supersedes: ADR-XXX`
- [ ] Trim to ~120 lines before merging Accepted
```

---

## Action-Output (statt nur Report)

Pro Finding **executable Artefakte** vorschlagen, nicht nur Text:

| Finding | Action-Output |
|---|---|
| Split-Vorschlag (z.B. 7 Concerns → 4 ADRs) | Frontmatter-Stubs für jeden Sub-ADR (status: draft, supersedes: <parent>, scope, decision_summary-Stub) — ready für `/adr` |
| Hard-Conflict ohne `supersedes:` | Diff-Block: `--- supersedes: []` `+++ supersedes: [ADR-XXX]` für PR-Amendment |
| Cross-Repo-Impact ohne Migrations-Plan | `gh issue create` Snippet mit Migration-Phasen-Template |
| Open Questions > 7 Tage alt | TODO-Liste mit ADR-Section-Verweis + Decide-or-Close-Snippet |
| Memory-Drift (File-Status ≠ Orchestrator-Memory) | `agent_memory_upsert`-Call ready zum Aufruf |

Format: pro Finding 1 Code-Block (`bash` / `yaml` / `python`), copy-paste-ready. User entscheidet was angewandt wird — Skill bleibt read-only.

---

## Anti-Patterns

- ❌ Stroh-Mann-Argumente (immer Steel-Man)
- ❌ Niedrige Confidence-Counter aufblähen — wenn unter 50, weglassen
- ❌ ADR-Text **schreiben** oder **editieren** — read-only Workflow
- ❌ Threshold-Check überspringen, wenn User "ich will einen ADR" sagt
- ❌ Path/Repo hardcoden — alles via project-facts.md
- ❌ Mehr als 2 Counter generieren — Signal-to-Noise ruinieren

---

## Changelog

- 2026-05-15: Initial. Adressiert 🌀-Drift-Klassen ADR-199 (Iteration-Count) und ADR-201 (Smallest-Viable). Read-only, SSoT in platform-workflows.
