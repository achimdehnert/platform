---
description: Disambiguate which ADR is canonical for a topic — supersession chains, naming collisions, conflict warnings. Read-only.
mode: read-only
---

# /adr-curator — ADR Disambiguation Specialist

> **Wann:** Bevor du auf ADR-X verweist, eine bestehende Decision in Frage stellst, oder bei Verdacht auf canonical-number-drift (Lehre aus 🌀 ADR-141 vs 179).
> **Wann NICHT:** Neuen ADR schreiben → `/adr`. Draft adversarial reviewen → `/adr-challenger`. Vollständigen Audit → `/adr-health`.

## Verwendung

```
/adr-curator <topic-or-keyword>
```

Beispiele:
- `/adr-curator SQLite Verbot`
- `/adr-curator multi-tenancy strategy`
- `/adr-curator ADR-141`

---

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT)

```
Aus project-facts.md (always_on rule) entnehmen:
- ADR_PATH (z.B. "docs/adr")
- ORC_PREFIX (orchestrator MCP prefix, aktuell "mcp2_")
- ADRFW_PREFIX (iil-adrfw MCP prefix, aktuell "mcp2_")
```

> **NIEMALS** Pfade/Prefixe hardcoden. SSoT ist project-facts.md.

---

## Step 1: Drift-Memory query (operationalisiert 🌀-Lehren)

```
MCP: {ORC_PREFIX}agent_memory_search(query="drift:adr <topic>", limit=5)
MCP: {ORC_PREFIX}agent_memory_search(query="policy:adr-canonical-numbers", limit=3)
```

Wenn Drift-Memory existiert für das Topic → Output **zuerst** zitieren ("Vorsicht: diese Frage hatte bereits einen Drift-Fall bei ADR-X — siehe Memory").

---

## Step 2: Constitution-Query auf ADR-Korpus

```
MCP: {ADRFW_PREFIX}adr_query(req={"question": "<topic>"})
→ liefert: {primary_answer, citations[], open_questions[], confidence, routing}
```

**Wichtig:** `adr_query` ist deterministisch (regel-basiert, kein Vektor). Bei `confidence=0` und leeren `citations` → MCP kennt das Topic nicht. **Nicht** als "Topic existiert nicht" interpretieren — fallback auf Grep in Step 4 ist Pflicht.

Re-rank der `citations`-Liste (LLM-Judgment):
1. **Status-Priority:** Accepted > Proposed > Superseded > Deprecated
2. **Recency-Bias:** bei identischem Score jüngeres `decision_date`
3. **Title-Match:** exakter Keyword-Match im Titel schlägt nur-Body-Match

---

## Step 3: Supersession-Kette + Detail-Read

Für jeden Top-3-Hit aus Citations:

```
MCP: {ADRFW_PREFIX}adr_explain(req={"rule_id": "<rule_id_from_citation>", "audience": "senior"})
```

**Achtung Format:** `rule_id` ist nicht `"ADR-179"` allein, sondern `"ADR-NNN/<rule-slug>"` (z.B. `"ADR-099/tenant-id-bigint"`). Plain ADR-Nummern liefern "Rule not found". Wenn `citations` keine vollständigen rule_ids enthalten → **Fallback auf direkten File-Read** des ADR-Files für Supersession-Fields aus Frontmatter (`supersedes`, `superseded_by`, `amends`).

Folge `superseded_by` rekursiv bis zum aktuell gültigen ADR.

---

## Step 4: Naming-Collision-Check (Anti-141/179-Drift)

```
Grep über ADR_PATH nach allen Titeln mit Top-Topic-Keyword:
  grep -l "<keyword>" $ADR_PATH/ADR-*.md
```

Wenn mehrere ADRs **denselben Topic-Claim** machen → explizit als "Konflikt-Kandidat" markieren. Lehre: ADR-141 (=Discord-Bridge) wurde monatelang als "SQLite-Verbot" zitiert, kanonisch war 179.

---

## Step 5: Cross-Repo-Referenzen (optional, bei "wird das woanders zitiert?")

⚠️ **Direction-Note:** `adr_impact` macht das **Gegenteil**: gegeben einen `file_path`, sagt es welche ADRs für die Datei gelten. Für "welche Files referenzieren ADR-X" → direkter Grep:

```bash
grep -rn "ADR-NNN" ~/github/ --include="*.py" --include="*.md" --include="*.toml" --include="*.yml" -l 2>/dev/null
```

Output gruppieren nach Repo. Bei >20 Hits: nur Counts pro Repo zeigen, keine vollständige File-Liste.

---

## Output-Format

```
## ADR Curator Report — "<topic>"

### Canonical ADR
**ADR-NNN — <Title>** (Status: Accepted, last touched: YYYY-MM-DD)

### Supersession Chain
ADR-AAA (deprecated) → ADR-BBB (superseded) → **ADR-NNN** (current)

### Conflict Candidates (manuelle Verifikation empfohlen)
- ADR-XXX touches similar topic — different decision verb
- ADR-YYY claims topic in title but status=Proposed

### Drift Warning
[falls Memory-Hit] Diese Frage hatte bereits Drift bei ADR-Z — siehe `drift:adr-canonical-numbers`.

### Cross-Repo Impact (optional)
- repo-a: 3 references
- repo-b: 1 reference

### Recommendation
Verwende **ADR-NNN** als Referenz. Bei "<conflict-claim>" prüfe ob ADR-XXX/YYY denselben Decision-Scope haben oder nur überlappendes Vokabular.
```

---

## Action-Output (statt nur Report)

Pro Finding **executable Artefakte** vorschlagen, nicht nur Text:

| Finding | Action-Output |
|---|---|
| Body-Heading-Drift (z.B. ADR-179 file zeigt "ADR-141" im H1) | `sed -i 's\|^# ADR-141:\|# ADR-179:\|' <file>` (User reviewt + applied) |
| Stale Orchestrator-Memory | Code-Block mit `agent_memory_upsert(entry_key="adr:platform:ADR-NNN", ...)` aufruf-fertig |
| Cross-Repo-Reference-Audit | `grep -rln "ADR-NNN" ~/github/ --include="*.py"` + Pipe-Snippet für Repo-Aggregation |
| Constitution-Load-Gap (adr_explain "Rule not found") | `gh issue create` Snippet im iil-adrfw-Repo mit Reproduce-Steps |

Format: pro Finding 1 `bash`-Code-Block ODER 1 MCP-Call-Block, klar abgegrenzt. User entscheidet was angewandt wird — Skill bleibt read-only, aber Output ist copy-paste-ready.

---

## Anti-Patterns (was dieser Workflow NICHT tut)

- ❌ Neue ADRs schreiben — das macht `/adr`
- ❌ Drafts reviewen — das macht `/adr-challenger`
- ❌ Cross-ADR-Audit — das macht `/adr-health`
- ❌ Path/Repo hardcoden — alles via project-facts.md
- ❌ Annahme "vector-search-top-1 = canonical" — Status + Supersession + Naming-Collision müssen mitgeprüft werden

---

## Changelog

- 2026-05-15: Initial. Adressiert 🌀-Drift-Klasse ADR-141/179. SSoT in platform-workflows, verfügbar in Claude Code (via Symlink) und Windsurf-Cascade.
