# ADR-Fleet-Audit — 2026-07-10 (Fokus: Struktur-Konformität + MADR-Frage)

**Abdeckung:** 34 lokale Repo-Clones mit ADR-Bestand (692 Dateien, `find`+`adr_inventory.py`-verifiziert) ·
Org-Scope aus Clone-Remotes: achimdehnert, bahn-sqf, iilgmbh, meiki-lra, ttz-lif · **Remote-Diff (Phase 0.2,
`gh repo list` je Org) für diesen fokussierten Lauf NICHT gefahren** — Scope war Struktur-Konformität, nicht
Vollständigkeitsbeweis; siehe „Nicht verifiziert". `platform` (217) und `platform-pinned` (211) sind derselbe
Remote als Worktree (bekannt, [[platform-pinned-is-worktree]]) — pinned liegt 6 Dateien hinter platform zurück.

## Kernbefund

**Das ist kein organisches Cross-Repo-Drift-Problem — es ist ein ungelöster Selbst-Widerspruch von `platform`.**
`docs/templates/adr-template.md` erklärt sich selbst explizit als „Basis: MADR 4.0" (Kopfkommentar, Z. 10,
verweist auf ADR-021/046/059 — ADR-054 im Verweis existiert nicht mehr, toter Link im Template selbst). Der
aktive `/adr`-Skill (`.windsurf/workflows/adr.md` Step 4, „Pflicht-Abschnitte — Reihenfolge einhalten") scaffoldet
aber eine **andere, nicht MADR-benannte** 11-Abschnitt-Struktur (Kontext/Entscheidung/Betrachtete
Alternativen/Begründung im Detail/Implementation Plan/Risiken/Konsequenzen/Validation Criteria/Glossar/
Referenzen/Changelog). Da `/adr` bei jeder Neuanlage — repo-übergreifend — feuert, hat sich diese zweite,
nie mit dem Template abgeglichene Struktur über die Flotte verteilt.

**Beleg im eigenen Korpus:** Selbst innerhalb von `platform` ist der Bestand fast hälftig gespalten —
von den 217 Dateien matchen 80 primär das Skill-Gerüst und 58 primär das Template-Gerüst (H2-Überschriften-
Klassifikation, s. u.). `platform` widerspricht sich selbst, bevor überhaupt ein Sub-Repo etwas nachbaut.

## Frontmatter: näher an einheitlich, als es aussieht

`iil-adrfw validate` (autoritativ, Exit-Code-basiert — nicht meine eigene Heuristik) normalisiert veraltete
Feldnamen automatisch und **blockiert dabei nicht**:

| Alias (gefunden) | Kanonisch | Blockierend? |
|---|---|---|
| `date` (296/692 Dateien) | `decision_date` | nein — DEPRECATION, Exit 0 |
| `decision-makers` (Bindestrich) | `deciders` | nein — DEPRECATION |
| `adr_id` | `id` | nein — DEPRECATION |
| `relates_to`/`relates-to` | `related` | nein — DEPRECATION |

**Echte harte Verstöße (Exit 1, `additionalProperties: false`): 85/692 (12 %)** — davon der überwiegende Teil
(≈80) auf **eine einzige, bereits bekannte Lücke** zurückzuführen: die ADR-211-Klickdummy-Felder (`class`,
`conforms_to`, `sunset_after`, `extension_review_required`, …) fehlen im Schema
(`iil-adrfw/schemas/adr_frontmatter.schema.json`, `additionalProperties: false`, `properties`-Liste geprüft).
Betroffen: `meiki-hub` (21), `writing-hub` (13), `risk-hub` (11), `ausschreibungs-hub` (9), `design-hub` (6),
`apo-hub`/`pg-hub` (4 je), `ttz-hub`/`iil-voice-agent` (3 je), Rest 1–2. Das ist Schema-Backlog, keine
Repo-Schuld (Skill-eigene Vorwarnung bestätigt).

**Drei echte Ausreißer außerhalb der bekannten Lücke:**
- `bfagent`: 14/16 Dateien **ganz ohne Frontmatter** — Repo ist **archiviert** (`gh api repos/achimdehnert/bfagent
  --jq .archived` → `true`, live geprüft), also eingefroren; aus jeder Fix-Welle ausklammern.
- `trading-hub/ADR-408-scalping-bot.md`: `review_status` trägt Freitext statt Enum-Wert.
- `weltenhub/ADR-031-graphql-strategie-iil-content-universum.md`: `title: 'MOVED'` — Stub/verwaister Eintrag.

## Body-Struktur: keine Werkzeug-Abdeckung existiert (Root-Cause geprüft)

Vor dem Vorschlag eines neuen Checks geprüft, ob schon einer existiert: `iil-adrfw/src/iil_adrfw/cli.py`
validiert ausschließlich Frontmatter (`_cmd_validate`, kein H2-/Abschnitts-Code); `platform`-CI
(`adr-validate.yml`, `adr-guard.yml`) ruft nur `iil-adrfw validate`, `staleness`, `adr_cross_repo_refs.sh`,
`adr_next_number.py --check`, `adr_open_pr_guard.py`; `scripts/adr_audit.py` prüft ausschließlich
Nummern-Konflikte/-Lücken. **Kein Mechanismus prüft je Abschnittsüberschriften — Body-Struktur ist der
tatsächlich unregulierte Freiraum.**

1673 verschiedene H2-Überschriften über 692 Dateien. Klassifikation nach Überschriften-Familie
(Kandidaten-Vokabular gegen `.windsurf/workflows/adr.md` Step 4 vs. `docs/templates/adr-template.md` vs.
reines MADR-4.0-Englisch vs. Alt-Minimalform):

| Familie | Dateien | Anteil |
|---|---|---|
| Skill-Gerüst (DE, nummeriert — aktiv per `/adr`) | 341 | 49 % |
| Template-Gerüst (EN, nummeriert, MADR-Vokabular) | 125 | 18 % |
| reines MADR-4.0-Englisch (unnummeriert) | 71 | 10 % |
| sonstige/gemischt | 100 | 14 % |
| keine H2 (Stubs/Kurzform) | 55 | 8 % |

*(Buckets nicht überschneidungsfrei, da Vokabular teils gemeinsam — Größenordnung, nicht Nachkommastelle.)*

**Fundort MADR-4.0-Vokabular außerhalb von platform:** `risk-hub`, `coach-hub`, `bfagent`, `trading-hub`,
`mcp-hub`, `pptx-hub`, `137-hub` — organisch entstanden, nicht durch eine zentrale Vorgabe.

## Nebenbefunde (nicht vertieft, Scope war Struktur)

- `dup_nums` (Nummern-Doppelvergabe innerhalb eines Repos): `bfagent` ADR-79/81/85 (archiviert, kein Fix nötig),
  `nl2cad` ADR-1 (3×), `odoo-hub` ADR-1 (2×), `pptx-hub` ADR-2 (2×), `risk-hub` ADR-39 (2×).
- `supersession_broken`: 6 Ketten mit fehlendem oder falsch-status'tem Ziel (`adr_analyze.py`).
- `cross_repo_title_dups`: 211 Titel-Überschneidungen zwischen Repos — größtenteils erwartbar (gleiches Thema,
  unabhängig entschieden), Einzelfall-Bewertung gehört zu `/adr-curator`, nicht in diesen Report.

## MADR-Empfehlung

**Ja — aber nicht als Einführung eines neuen Standards, sondern als Vollzug einer bereits getroffenen
Entscheidung.** `docs/templates/adr-template.md` sagt selbst „Basis: MADR 4.0" seit Version 2.0 (2026-02-21).
Die Flotte ist nicht von einem Standard abgedriftet — sie folgt zu fast gleichen Teilen zwei offiziellen,
nie abgeglichenen Quellen. Der MADR-Anteil ist außerdem schon jetzt der größere, sobald man Template- und
reine MADR-Familie zusammenzählt (196 von 692 vs. 341 Skill-Gerüst) — kein Fremdkörper, sondern die
Mehrheitsrichtung, die nie zu Ende gebracht wurde.

**Was MADR NICHT verlangt, wegzulassen:** Die Platform-Erweiterungen sind begründet und sollten bleiben —
Glossar (Pflicht für LRA-/Nicht-IT-Leser, MADR kennt das nicht), Implementation Details/Migration Tracking
(für ein Repo mit echten Deployments sinnvoll), Risks, sowie die ADR-211-Klickdummy-Frontmatter-Erweiterung
(anderer Artefakt-Typ). MADR 4.0 ist als Kern-Gerüst + optionale Erweiterungen spezifiziert — genau dafür gedacht.

**Was NICHT sinnvoll ist:** 692 bestehende ADR-Bodies rückwirkend umformatieren. Kosten hoch, Nutzen ~0 —
akzeptierte historische Entscheidungen ändern sich durch Überschriften-Kosmetik nicht, und die ADR-Praxis
selbst rät von retroaktivem Umschreiben ab (Historie bleibt lesbar wichtiger als einheitliche Optik).

## Backlog

| Klasse | Bedeutung |
|---|---|
| A | mechanisch, gate-frei — nur in platform |
| B | inhaltlich, braucht Review |
| C | Architektur-Entscheidung nötig |

| # | Item | Repo | Klasse | Evidenz | Status | Next Step |
|---|---|---|---|---|---|---|
| F-1 | `.windsurf/workflows/adr.md` Step 4 auf MADR-4.0-Sektionen (aus `docs/templates/adr-template.md`) umstellen — behält Glossar/Risks/Implementation Details als Erweiterung | platform | C | `.windsurf/workflows/adr.md:166-190` vs. `docs/templates/adr-template.md:21-` | 🟡 Empfehlung | ADR schreiben (adr-threshold: cross-cutting, alle Repos betroffen) — du entscheidest, ich ziehe den Skill nach |
| F-2 | ADR-211-Klickdummy-Felder ins Schema aufnehmen (`class`,`conforms_to`,`sunset_after`,`extension_review_required`,…) — behebt ≈80 der 85 Hard-Fails | platform (iil-adrfw) | A | `iil-adrfw/schemas/adr_frontmatter.schema.json` `additionalProperties:false` | 🔵 ready | Schema-PR (ich, nach Go) |
| F-3 | Leichter Struktur-Lint (H2-Set gegen kanonische MADR-Liste, WARN nicht BLOCK, nur `created > Cutover-Datum`) — kein retroaktiver Zwang | platform (iil-adrfw oder `scripts/`) | B | Root-Cause bestätigt: existiert nirgends (s. o.) | 🔵 ready | Nach F-1-Entscheid bauen (ich) |
| F-4 | `docs/templates/adr-template.md` Kopfkommentar: toter Verweis „ADR-054" entfernen/korrigieren | platform | A | `docs/templates/adr-template.md:11` — `ls docs/adr/ADR-054-*` → kein Treffer | 🔵 ready | 1-Zeilen-Fix (ich) |
| F-5 | `trading-hub/ADR-408` `review_status`-Freitext → Enum-Wert (`approved` + Freitext in Body) | trading-hub | B | `iil-adrfw validate` Exit 1 | 🔵 ready | PR (ich, nach Go) |
| F-6 | `weltenhub/ADR-031` Stub mit `title: MOVED` klären (löschen/vervollständigen) | weltenhub | B | `iil-adrfw validate` Exit 1 | 🟢 offen | Owner-Entscheid: löschen oder Ziel benennen (du) |
| F-7 | `bfagent` 14 frontmatter-lose Dateien — **NICHT anfassen**, Repo archiviert | bfagent | — | `gh api repos/achimdehnert/bfagent --jq .archived` = `true` | ✅ dokumentiert | keiner — bewusst ausgeklammert |
| F-8 | `platform-pinned` 6 Dateien hinter `platform` | platform-pinned | A | Dateizahl-Diff 217 vs. 211 | 🔵 ready | Worktree-Sync (ich, mechanisch) |

**Verifiziert:** Frontmatter-Schema-Status per `iil-adrfw validate` über alle 34 Repos (Exit-Codes, nicht
Heuristik) · Body-Struktur-Werkzeug-Lücke per Quellcode-Lektüre (cli.py, CI-Workflows, adr_audit.py) ·
Archiv-Status bfagent per Live-API-Call · MADR-4.0-Selbstbezug per Template-Kopfkommentar gelesen.
**Nicht verifiziert:** vollständiger Remote-Abgleich (Phase 0.2) für alle 5 Orgs — billigster Nachtrag:
`gh repo list <org> --json name,isArchived` je Org gegen `ls ~/github` diffen, falls ein Vollständigkeitsbeweis
gebraucht wird · inhaltliche Bewertung der 211 `cross_repo_title_dups` (Themenkollision vs. Zufall) — gehört
zu `/adr-curator`, hier nur gezählt.

## Freigabe-Block

- [ ] F-1: ADR schreiben „`/adr`-Skill-Scaffold auf MADR 4.0 vereinheitlichen" (du entscheidest ADR ja/nein
      und Cutover-Verhalten — retroaktiv NICHTS umschreiben)
- [ ] F-2: Schema-Erweiterung um ADR-211-Felder
- [ ] F-3: Struktur-Lint bauen (abhängig von F-1)
- [ ] F-4: toter Verweis im Template fixen
- [ ] F-5: trading-hub Enum-Fix
- [ ] F-6: weltenhub-Stub — Owner-Entscheid nötig
- [ ] F-8: platform-pinned nachziehen
