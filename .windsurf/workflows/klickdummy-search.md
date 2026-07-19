---
description: Semantische Cross-Repo-Suche über alle Klickdummies, Iterationen, ADRs via Orchestrator-pgvector (read-only, ADR-211 Rev 14 Stufe 2 Konsument)
mode: read-only
---

# /klickdummy-search — Cross-Repo-Suche über die Klickdummy-Welt

> **Wann:** Drift-Schutz vor neuem Bau („existiert das schon?"), Cross-Repo-Konsistenz-Check, Pattern-Mining für Workshops, Adoption-Status-Übersicht.
> **Wann NICHT:** Suche **innerhalb** eines einzelnen Klickdummys → das ist eine normale Spec-Lese-Operation, kein Cross-Repo-Lookup. Wenn nur 1 Repo betroffen ist: `grep` in dem Repo reicht.

## Verwendung

```
/klickdummy-search <freitext-query> [--org <org>] [--class <pattern>] [--type <kind>] [--repo <repo>] [--limit <n>]
```

**Argumente:**

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<query>` | **ja** | — | Freitext, semantisch indexiert (pgvector + temporal decay) |
| `--org` | nein | (alle) | Filter `klickdummy:org:<org>` (iilgmbh, ttz-lif, meiki-lra, achimdehnert) |
| `--class` | nein | (alle) | Filter `klickdummy:class:<pattern>` (mock/stub-demo/story/spec-demo) |
| `--type` | nein | (alle) | `repo_context` (Spec) \| `lesson_learned` (Iter.) \| `decision` (ADR) |
| `--repo` | nein | (alle) | Filter `klickdummy:repo:<repo>` |
| `--limit` | nein | `5` | Max Treffer |

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` (always_on) im aktuellen Repo lesen:

```
- REPO_OWNER     (z.B. "iilgmbh", "achimdehnert", "meiki-lra", "ttz-lif")
- REPO_NAME      (z.B. "platform", "iil-klickdummy", "meiki-hub")
```

Wenn der User `--org` nicht setzt, wird der aktuelle Repo-Org als implizit-bevorzugter Filter angeboten („nur in eigener Org suchen oder cross-org?").

## Step 0.5: Orchestrator-Verfügbarkeit prüfen

```
orchestrator MCP available? → check tool list
  ja: nutze `orchestrator__agent_memory_search`
  nein: STOP mit Hinweis „Session bindet Orchestrator nicht; öffne /klickdummy-search aus dev-hub/mcp-hub/bfagent-Workspace."
```

Per `~/.claude/policies/orchestrator.md`: meiki-hub/ttz-hub/risk-hub-Workspaces binden i.d.R. nicht. Default-Empfehlung an User: aus dev-hub-Session aufrufen.

## Step 1: Query-Konstruktion

Aus User-Argumenten:

```
base_query = "<freitext-query>"
filter_tags = []
if --org:    filter_tags.append(f"klickdummy:org:{org}")
if --class:  filter_tags.append(f"klickdummy:class:{class}")
if --repo:   filter_tags.append(f"klickdummy:repo:{repo}")
```

Default-Constraint: alle Treffer haben den `klickdummy`-Tag (Pre-Filter zur Trennung von ADR-211-irrelevanten Memory-Entries).

## Step 2: Memory-Suche

```
results = orchestrator__agent_memory_search(
    query=base_query,
    entry_type=<--type filter | none>,
    limit=<limit>
)
```

**MCP-Signatur verifiziert (siehe `claude-skills.md` Pflicht):** `agent_memory_search` nimmt `query`, optional `entry_type` (Enum), `limit`. Schema unter `mcp__orchestrator__agent_memory_search`-Tool-Description. Keine `tags`-Pre-Filter in der Search-API → manuelle Tag-Filterung in Step 3.

## Step 3: Tag-Filter + Output-Aggregation

Aus den Memory-Hits:
- Filter nach `filter_tags` (alle müssen in `tags` sein)
- Sortiere nach Relevanz (Memory-Search liefert bereits ranked)
- Begrenze auf `--limit`

Aggregiere zu Output-Format (siehe unten). Bei 0 Treffern: hilfreiche „nichts gefunden — versuche andere Tags / weiteren Query"-Antwort.

## Step 4: Drift-Hinweis (out-of-the-box)

Wenn `--type=repo_context` (Spec-Search) und ≥2 Treffer mit ähnlichem Inhalt aus **verschiedenen** Repos: **Drift-Warning** ausgeben.

Beispiel:
```
⚠ Mögliche Cross-Repo-Drift:
  meiki-hub:fristenmanagement-klickdummy (v0.1) und
  writing-hub:lecture-outline-wizard (v0.1)
  ähneln sich semantisch — ggf. Pattern-Sharing prüfen.
```

Schützt vor versehentlicher Re-Implementation existierender Konzepte.

## Output-Format

```
== /klickdummy-search "<query>" ==
  Filter: <none|filters>
  Treffer: <N> (limit=<L>)

[1] <entry_key>
    Type:     <repo_context|lesson_learned|decision>
    Title:    <title>
    Tags:     <gefilterte tag-liste>
    Snippet:  <erste 200 Zeichen content>
    Stand:    <Sync-Zeit aus Content-Zeile "Sync-Zeit:"; fehlt sie: "unbekannt">
    Score:    <relevance, falls verfügbar>

[2] ...

⚠ Freshness (KONZ-risk-hub-008 R1/K2): Treffer sind ein abgeleiteter Cache — SoR ist
  die Spec im Repo. Ist der älteste "Stand" >7 Tage alt, Hinweis ausgeben:
  „Cache ggf. stale — /klickdummy-pgvector-sync laufen lassen"; Treffer IMMER mit
  Repo+Spec-Pfad zitieren (Verweis, nie Kopie als Wahrheit).

⚠ Drift-Hinweise (falls vorhanden):
  - <repo_a> + <repo_b> ähneln sich semantisch

== Empfehlungen ==
  - Engerer Filter: --type=repo_context, --class=mock
  - Cross-Org-Suche: füge --org alle hinzu
  - Drift-Detail: /klickdummy-search "<topic>" --type=repo_context --limit=10
```

## Anti-Patterns

- ❌ **Hardcoded Org-Liste** im Skill — Tags werden zur Laufzeit gefiltert; neue Orgs (z. B. ein zukünftiges 4. Repo) brauchen keine Skill-Änderung.
- ❌ **Search ohne `klickdummy`-Tag-Pre-Filter** — Memory enthält auch ADRs/Tasks anderer Themen; ohne Pre-Filter Output verrauscht.
- ❌ **Schreibender Zugriff** (`agent_memory_upsert` etc.) — Skill ist `mode: read-only`. Schreibender Sync = `/klickdummy-pgvector-sync` (Konsument der `iil-klickdummy` `klickdummy-sync`-CLI).
- ❌ **Drift-Hinweis ohne Schwellwert** — nur bei ≥2 cross-repo-Hits ausgeben, sonst False-Positive-Rauschen.
- ❌ **Limit ohne Cap** — UI-Outputs >20 sind unlesbar; Default 5, Cap 20.
- ❌ **Gov-Daten leaken** — wenn Treffer das Tag `gov-data` haben (ttz-lif, meiki-lra), Output nur an autorisierte User; Hinweis im Output-Footer („enthält Gov-Workload-Daten, vertraulich").

## 🌀-Memory-Discovery-Pfad

Drift-Lehren leben in CC-Memory (`~/.claude/projects/.../memory/MEMORY.md`) lokal pro Repo. Suche dort zuerst bei Konflikt-Verdacht, dann Orchestrator. Echte Memory-IDs aus meiki-hub-MEMORY.md (Beispiele):
- `klickdummy-adr180-collision` (Drift-Episode 2026-05-19)
- `klickdummy-platform-heimat-iil-klickdummy` (Reference 2026-05-20)
- `klickdummy-rev12-pivot-adr214-rejected` (Drift 2026-05-20)

## Dogfood-Tests (Pflicht-Review-Gate per `claude-skills.md`)

### Test 1 — Drift-Schutz für Iter. 8

```
/klickdummy-search "klickdummy versions listbox cross-repo browser"
```

**Erwartung:** Treffer auf `klickdummy-iter:meiki-lra:meiki-hub:fristenmanagement-klickdummy:8` (Iter. 8 die genau dieses Pattern triggerte) + ADR-211-Rev-14-Body. **Konsequenz:** „Existiert schon als Iter.8 → v1.1.0 (Multi-Klickdummy-Browser)". Spart Re-Bau.

### Test 2 — Cross-Org-Konsistenz

```
/klickdummy-search "schwester mock klickdummy workshop" --class=mock
```

**Erwartung:** meiki:ADR-021, risk-hub:ADR-046, ttz-hub:ADR-100 (alle als `class:mock` deklariert).

### Test 3 — Repo-spezifisch

```
/klickdummy-search "fristen" --repo=meiki-hub --type=repo_context
```

**Erwartung:** meiki:fristenmanagement-klickdummy v0.1 (Top-1).

## Bezug

- `platform:ADR-211` Rev 14 §Multi-Klickdummy-Browser Stufe 2 (Orchestrator-pgvector)
- `iilgmbh/iil-klickdummy` v1.2.0 — `klickdummy-sync` produziert die Memory-Entries
- `~/.claude/policies/orchestrator.md` — MCP-Mechanik
- `~/.claude/policies/claude-skills.md` — Pflicht-Strukturelemente

## Changelog

- 2026-05-21: Initial. Konsument-Seite zu `iil-klickdummy` v1.2.0 `klickdummy-sync` (Schreib-Seite, NDJSON → Orchestrator). Read-only-Skill für Cross-Repo-Suche. Konformt zu `claude-skills.md` (Frontmatter, Anti-Patterns, Dogfood, MCP-Signatur verifiziert).
