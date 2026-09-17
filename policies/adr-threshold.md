# Policy: ADR Threshold
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

**Trigger words:** ADR, architecture decision, adr-record, adr nötig

## Rule

Do **not** propose writing an ADR for work that is purely an *addition*
following an existing pattern. ADRs are reserved for genuine architecture
decisions.

## ADR is required when *any* of these is true

- New external dependency or service boundary (new DB, new API, new MCP, new SaaS)
- Reverses or replaces an existing architectural decision
- Cross-cutting impact across multiple apps/teams/repos
- Non-trivial trade-off worth recording for a future challenger
- Anything that touches data sovereignty, security perimeter, or licensing

## ADR is NOT required when

- A new app/feature **follows an existing pattern** (e.g. "another Platform
  Agent in dev-hub like Drift Detector / TechDocs")
- Reversible by removing one app or one Celery task
- Local to one repo with no public surface
- Dependency bump within the same major version
- Code-style or refactor work

For these → **CHANGELOG entry + PR description** is enough.

## Where ADRs live

`~/github/platform/docs/adr/ADR-NNN-*.md`. **Keine Nummer am Autorenzeitpunkt wählen**
(ADR-228, seit 2026-09-08): ein neuer ADR startet als `docs/adr/ADR-DRAFT-<slug>.md` mit
`id: ADR-000`; die Nummer vergibt `tools/adr_allocate.py --apply` kurz vor dem Merge.
Wer die voraussichtlich nächste Nummer trotzdem sehen will (z. B. für einen Split wie
ADR-188 → ADR-303…306), fragt **alle** Quellen, nicht nur `main`:

```bash
P="${GITHUB_DIR:-$HOME/github}/platform"
python3 "$P/scripts/naechste_nummer.py" --art adr    # Remote-Refs + offene PRs + Reservierungen
python3 "$P/scripts/naechste_nummer.py" --art konz   # dasselbe für KONZ-platform-NNN
```

`scripts/adr_next_number.py` sieht nur `main` — genau die Race, die am 2026-08-12 zwei
KONZ-043 erzeugte (#1944 K1). Nicht mehr verwenden.

> Absolute Pfade mit Absicht: diese Policy wird in **jeder** Session geladen,
> auch wenn das Arbeitsverzeichnis ein anderes Repo ist. Ein relatives
> `scripts/naechste_nummer.py` schlägt dort fehl — und die alte Zeile, die es
> ersetzt, war absolut.

> ⚠️ Die früher hier dokumentierte Zeile `ls ~/github/platform/docs/adr/ | sort |
> tail -1` ist **kaputt**, nicht bloß umständlich. `docs/adr/` enthält neben den
> ADRs auch `index.json`, `INDEX.md` sowie die Unterverzeichnisse `inputs/`,
> `mockups/`, `reviews/` — die sortieren alle **nach** `ADR-*`. Gemessen am
> 2026-07-21 lieferte der Befehl `reviews`; korrekt gewesen wäre `ADR-281`.
> Er liefert zudem einen Dateinamen, nie die **nächste** Nummer.

**Index nach dem Anlegen regenerieren, nicht von Hand pflegen:**

```bash
# --adr-dir/--root sind cwd-relativ vorbelegt — aus einem anderen Repo heraus
# beide setzen, sonst schreibt der Generator ins falsche Verzeichnis:
python3 "$P/scripts/gen_adr_index.py" --adr-dir "$P/docs/adr" --root "$P"
iil-adrfw validate "$P/docs/adr"        # Frontmatter-Schema, erwartet N/N (100.0%)
```

`INDEX.md` trägt in Zeile 1 `AUTO-GENERATED … do not edit manually`; der CI-Gate
„ADR index freshness (gating)" regeneriert sie und diffed gegen den Commit.
Vollständiger Ablauf inklusive Abschluss-Checkliste: Skill `/adr`.

## Changelog

- 2026-07-21: **Nummern-Ermittlung korrigiert.** Die dokumentierte `ls | sort |
  tail -1`-Zeile lieferte real `reviews` (Unterverzeichnis) statt einer ADR-Nummer
  — falsifiziert am 2026-07-21. Ersetzt durch `scripts/adr_next_number.py`.
  Ergänzt: Index-Regenerierung + Frontmatter-Validierung, weil beide Schritte
  bisher in keiner Policy standen und der CI-Gate sie erzwingt (Realfall
  platform#1291, Skill-Fix platform#1292).
- 2026-05-11: Initial. Promoted after user feedback ("Ergänzung keine
  Architektur-Entscheidung") on repo_health agent.
