---
description: Geerdete, adversariale Session-Retrospektive — sammelt git/gh/CI als Ground Truth, urteilt in frischem Kontext (Richter≠Angeklagter), falsifiziert jeden Befund, schlägt kopierfertige Verankerung + Scorecard vor. Schreibt Report nach ~/shared/.
mode: write
---

# /session-retro — Geerdeter, adversarialer Session-Review

> **Zweck:** Eine zurückliegende Arbeitssession schonungslos reviewen — aber so, dass die
> vier Konstruktionsfehler des klassischen „Paste-Prompt-Retros" gelöst sind: Angeklagter≠
> Richter, Artefakt-Erdung statt Erinnerung, geschlossener Lessons-Loop, Falsifikation der
> eigenen Befunde.
>
> **Wann:** Nach größeren Umbau-/Architektur-Sessions; am Sitzungsende.
> **Wann NICHT:** Trivial-Edits (ein Tippfehler-Fix braucht keinen Retro) → höchstens `lean`.
> **Deterministische Engine (optional):** Für schwere Läufe den JS-Workflow
> `~/shared/session-retro.workflow.js` via Workflow-Tool starten (parallele Finder +
> pipeline-erzwungene Falsifikation). Dieser Command ist die portable Prosa-Variante mit
> identischer Methode.

## Eiserne Regeln — die 4 Fixes (nicht verhandelbar)

1. **Richter ≠ Angeklagter.** Urteile NIE aus deinem Session-Gedächtnis. Jeden Befund über
   einen **frischen Subagenten** (Agent-Tool) erzeugen, der nur die Artefakte sieht — nicht
   deine Erzählung. (Self-Review verbucht eigene Fehler als Erfolge.)
2. **Evidenz vor Behauptung.** Jeder Befund braucht einen harten Artefakt-Beleg
   (repo#PR, Commit-SHA, Datei:Zeile, CI-Run). Kein Beleg → kein Befund. „Eindruck" zählt nicht.
3. **Falsifikation.** Jeden Befund einem Widerlegungs-Pass aussetzen (Steelman der
   Original-Entscheidung). Nur Überlebende bleiben — sonst entsteht performative Kritik.
4. **Geschlossener Loop.** Lessons NICHT als Prosa versanden lassen → als **kopierfertige**
   Memory-/ADR-/CLAUDE.md-Vorschläge ausgeben. Verankerung entscheidet der Mensch.

## Phase 0 — Right-Sizing (Footprint **und** erwartete Befund-Dichte)
Footprint messen (PRs / Repos / Prod-Schritte / Migrationen / ADRs) **und** Befund-Dichte
schätzen: war die Session **reversibel + transparent + vom-Menschen-freigegeben**, sind harte
Survivors strukturell selten → kleiner skalieren (sonst verbrennt die Falsifikation Agenten für
0–1 Survivor). Stufe + **hartes Agenten-Budget**:

| Stufe | Trigger | Agenten-Budget |
|---|---|---|
| **lean** | ≤2 PRs, 1 Repo, kein Prod/Migration/ADR | **0 Subagenten** — 1 Inline-Pass, 2 Dimensionen, knappe Scorecard |
| **full** | Standard | 1 Collector + 3 Finder + Falsifikation **gebündelt** (1 Skeptiker je Dimension, nicht je Befund) — ≤5 Subagenten |
| **deep** | ≥3 Repos ODER Prod-Schritt ODER Migration ODER Verdacht auf vertuschte Fehler | volle Pipeline + Phase-5 Meta-Reviewer; Skeptiker-Spawns **hart gecappt** (≤ Anzahl Dimensionen) |

Kein Multi-Agent unter `lean`. Falsifikation **nie** 1 Agent pro Befund (explodiert linear) —
gebündelt je Dimension.

## Phase 1 — Collect (Ground Truth, frischer Ermittler)
Ein Subagent sammelt **ausschließlich aus Artefakten** (kein Self-Report):
- `gh pr list --repo <owner>/<repo> --state all --search "updated:>=<datum>"` (+ `gh issue list`)
- `git -C ~/github/<repo> log --oneline --since=<…>` + `git diff --stat` wo sinnvoll
- CI/main-Status der betroffenen Repos (`gh run list --branch main`)

**Aktiv nach red_flags suchen, die ein Self-Review systematisch übersieht:**
OPEN-PR überholt von späterem MERGED-PR zum selben Issue (Duplikat/dangling) · mehrere PRs
„Closes" dasselbe Issue · rote Required-Gates auf offenen PRs · Migrations-Nummern-Kollision ·
Issue offen geblieben trotz gemergtem Fix.

> **Repos verbindlich halten:** vom Menschen genannte Repos sind in-scope — niemals als
> „separater Workstream" wegklassifizieren. Falls ein Transkript-Pfad gegeben ist, erdet er
> die Session-Grenze (gewinnt bei Konflikt gegen die Artefakt-Heuristik).

## Phase 2 — Find (frischer Kontext, je Dimension)
Je Dimension ein **eigener** Subagent (kennt die Session-Erzählung nicht), geerdet im Footprint:
- **Soll-Ist & Scope** — Ziel vs. real Geliefertes; Scope Creep; still Weggelassenes; Offenes,
  das das Ziel verfehlt.
- **Entscheidungen & Fehler** — tragfähig vs. fragwürdig; Anti-Patterns; Konventionsverstöße;
  neue Tech-Debt; verfrühte/zu enge Festlegungen.
- **Prozess & Kollaboration** — Rework, Duplikat-/dangling-PRs, rote Gates, unklare Steuerung,
  fehlende frühe Checks (Stand von main / parallele Arbeit nicht geprüft).

Je Befund: Schweregrad (kritisch/hoch/mittel/niedrig) + Root Cause (5-Why) + Kategorie
(Wissenslücke / Prozesslücke / Kommunikation / verfrühte Festlegung / fehlende Validierung / Werkzeug).

## Phase 3 — Verify (Falsifikation)
Skeptiker-Subagent **je Dimension** (nicht je Befund — Budget, s. Phase 0). **Binär: SURVIVES
oder REFUTED** — kein „weakened"/„teilweise" (das ist Verhandlung, nicht Falsifikation; mildernde
Umstände gehören in die Beleg-Spalte, nicht in ein drittes Verdikt).

**Eiserne Verify-Regel (Lehre 2026-06-04):** Der Skeptiker bekommt **nur die Behauptung, NICHT
den Finder-Befehl** — und muss den Beleg **unabhängig neu ziehen**, breiter/rekursiv (`find -name`,
nicht `ls <dir>`; `grep -r`, nicht `grep <einzelne Datei>`). Wiederholt er den Finder-Glob, wandert
dessen False-Positive ungeprüft durch. (Realfall: Finder grepte `tools/`, übersah `tools/tests/`,
Verify wiederholte es → ein falscher Befund „kein Testfile" überlebte.)

**Belegpflicht gilt AUCH für Längsschnitt-/Wiederholungs-Behauptungen** (Phase 4): „wiederholt
Drift-Memory X" ist ein Befund → X muss per `ls`/`grep` existieren, sonst REFUTED. (Realfall:
Verweis auf nicht-existente Memory `claim-confidence-vs-cheapest-check`.)

Nur SURVIVES gehen in den Report.

## Phase 3.5 — Soll-Ablauf (konstruktiv, an Überlebende gekoppelt)
Diagnose allein lehrt „war schlecht", nicht „so geht's richtig". Pro **überlebendem** Befund
**genau ein** artefakt-verankerter Alternativschritt, Format **Ist → Soll → eliminiert #**:

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| … was real geschah | … der konkrete bessere Schritt/Checkpoint | #<Befund> |

**Invariante (hart):** `|Soll-Schritte| == |überlebende Befunde|`. Kein Soll-Schritt ohne
Befund-Referenz (verhindert generische Plattitüden „besser planen/kommunizieren"); kein
überlebender Befund ohne Soll-Schritt (verhindert reine Anklage). Die Top-3-Maßnahmen (Phase 4)
werden aus dem Soll-Ablauf **abgeleitet**, nicht frei erfunden.

## Phase 4 — Anchor (schließen + Längsschnitt)
**Pflicht-Report-Skelett** (erzwungen — feste Reihenfolge + feste Tabellenspalten, damit
Längsschnitt maschinell auswertbar ist). Beginnt mit maschinenlesbarem YAML-Frontmatter:

```yaml
---
retro_schema: 1
date: <YYYY-MM-DD>
repo_scope: [<repo>, …]
session_id: <kurz>
footprint: lean|full|deep
findings_total: <n>
findings_survived: <n>
refuted_rate: <(refuted)/total, 0–1>     # Skill-KPI, s. Phase 5
scores:                                   # ganzzahlig 1–5, KEINE Halbwerte
  zielerreichung: <1-5>
  architektur_design: <1-5>
  code_konventionstreue: <1-5>
  risiko_debt: <1-5>
  prozess_effizienz: <1-5>
  entscheidungsqualitaet: <1-5>
gate_candidates: [<slug>, …]
recurring_findings: [<slug>, …]
---
```
Danach in fester Reihenfolge:
- **1. Executive Summary** (max 5 Bullets).
- **2. Befund-Tabelle** mit **eingefrorenen Spalten:** `# | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence`.
- **3. Scorecard** — 6 feste Dimensionen (`zielerreichung · architektur_design · code_konventionstreue ·
  risiko_debt · prozess_effizienz · entscheidungsqualitaet`), **ganzzahlig 1–5, KEINE Halbwerte**,
  je **Anker aus Befunden** (nicht Bauch). Rubrik: `1`=Kernziel verfehlt/hoher Schaden · `2`=verfehlt
  mit Rework · `3`=teilweise erreicht, signifikante Abweichung begründet · `4`=erreicht, kleine Mängel ·
  `5`=erreicht, vorbildlich.
- **4. Soll-Ablauf** (aus Phase 3.5, Ist→Soll→eliminiert-#).
- **5. Längsschnitt — der eigentliche Hebel:** gegen `<auto-memory>/MEMORY.md` abgleichen.
  Wiederholung (gleiche Kategorie mehrfach in dieser Session ODER schon als Drift-Memory **belegt
  vorhanden** — Existenz per `grep` prüfen, Phase 3) → **HARTES GATE** (Hook/CI), nicht der N-te Notizzettel.
- **6. Verankerung:** kopierfertige `memory_candidates` + `adr_candidates` (du schreibst sie NICHT selbst).
- **7. Maßnahmen als Action-Board** (Org-Standard: Buckets 🟢 dein Zug / 🔵 ich sofort / 🟡-⛔ wip / ✅ done;
  Lean-Spalten `# | Item | Repo | PR/Issue/ADR | Status | Next Step`), **abgeleitet aus dem Soll-Ablauf**.
- **8. Nicht verifiziert (Restlücken)** — Pflicht-Sektion: was offen blieb + billigster Check.

**Report-Pfad — kollisionsfrei bei Parallel-Sessions (Pflicht):**
`~/shared/session-retro-<datum>-<repo>-<session-id-kurz>.md`. **Jede Session schreibt ihre eigene Datei.**
`<repo>` = primäres Scope-Repo, `<session-id-kurz>` = die letzten ~6 Zeichen der Session-ID (oder ein
eindeutiger Suffix). **Existiert der Pfad bereits → NICHT überschreiben**, zusätzlichen Suffix anhängen.
Der bloße `…-<datum>.md`-Default ist verboten (Realfall 2026-06-04: 2 Parallel-Sessions kollidierten am
selben Pfad → Überschreib-Gefahr).

## Phase 5 — Self-Review (Meta-Agent, nur OUTPUT-Qualität) — `full`/`deep`
Selbstverbesserung der Skill **ohne Richter≠Angeklagter zu brechen:** ein **separater Meta-Agent**
prüft AUSSCHLIESSLICH den **Report-Entwurf gegen die Skill-Regeln** — NIE die Session-Erzählung.
Er sieht nur den Report + diese Skill. Checkliste:
- Hat **jeder** Befund (inkl. Längsschnitt-Behauptung) einen per `gh/git` **unabhängig nachgeprüften** Beleg?
- Scores ganzzahlig 1–5, je an Befund verankert? (fängt erfundene Halbwerte wie `2.5`)
- **Invariante** `|Soll-Schritte| == |überlebende Befunde|` erfüllt?
- Frontmatter schema-valide (alle Pflichtfelder)? Report-Pfad kollisionsfrei (repo+session-id)?
- `refuted_rate` plausibel? **Interpretation als Skill-KPI** (kein Session-Urteil): dauerhaft
  **>0,8** über mehrere Retros → Finder zu lasch (produzieren widerlegbares Stroh); **<0,2** →
  Falsifikation ist Theater (widerlegt nie). Auffälligkeit als `## Self-Review`-Block im Report notieren.

> **Längsschnitt der Skill selbst (optional):** `retro-kpis.py` (falls vorhanden) liest die Frontmatter
> aller `~/shared/session-retro-*.md`, trendet `refuted_rate`/Scores und eskaliert jeden
> `recurring_finding` mit Zähler **≥2 über Retros** automatisch zum Gate-PR-Pflicht-Item.

## Anti-Patterns
- ❌ Aus dem eigenen Session-Kontext urteilen (in-context self-review).
- ❌ Befund ohne harten Artefakt-Beleg.
- ❌ Befunde nicht falsifizieren — performative Kritik durchlassen.
- ❌ Memory/ADR/CLAUDE.md selbst schreiben statt nur vorschlagen.
- ❌ Ein wiederkehrendes Muster als „noch ein Memo" abtun statt als Gate-Kandidat zu eskalieren.
- ❌ Vom Menschen genannte Repos als „separaten Workstream" aus dem Scope kippen.
- ❌ **Verify wiederholt den Finder-Befehl** statt den Beleg unabhängig/breiter neu zu ziehen → False-Positive überlebt.
- ❌ **Drittes Verdikt „weakened/teilweise"** — Falsifikation ist binär (SURVIVES/REFUTED).
- ❌ **Längsschnitt-Behauptung („wiederholt Memory X") ohne Existenz-Check** von X (Phantom-Referenz).
- ❌ **Soll-Schritt ohne Befund-Referenz** (= Plattitüde) ODER überlebender Befund ohne Soll-Schritt.
- ❌ **Default-Dateiname `…-<datum>.md`** → Kollision/Overwrite bei Parallel-Sessions; repo+session-id ist Pflicht.
- ❌ **Halbscores** (2.5) — brechen Längsschnitt-Vergleichbarkeit.
- ❌ **Multi-Agent für `lean`-Footprint** / Skeptiker je Befund statt je Dimension (Spend-Falle).
- ❌ Meta-Self-Review (Phase 5), der die **Session** statt den **Report** beurteilt (Richter≠Angeklagter auf Meta-Ebene).

## Changelog
- 2026-06-04: Initial. Aus einem Advocatus-Diabolus-Review des Paste-Prompt-Retros
  (`iil-prompts-retrospective`) hervorgegangen; die 4 Fixes + der Längsschnitt-Hebel sind die
  Lehren daraus. Deterministische Engine: `~/shared/session-retro.workflow.js`.
- 2026-06-04 (v2): Adversarialer Selbst-Review der Skill (Richter≠Angeklagter, geerdet am realen
  Output `session-retro-2026-06-04-platform.md`). **Fixes:** (1) **erzwungenes Report-Skelett** +
  YAML-Frontmatter + feste Spalten + Score-Rubrik (ganzzahlig, keine Halbwerte) + Action-Board →
  Längsschnitt maschinell auswertbar. (2) **Phase 3.5 Soll-Ablauf** (Ist→Soll→eliminiert-#, Invariante
  |Soll|==|Survivors|) → konstruktiv statt nur Anklage, plattitüdenfrei by construction. (3) **Phase 5
  Meta-Self-Review** (separater Agent, nur Output-Qualität) + `refuted_rate`-KPI → Selbstverbesserung
  ohne Meta-Richter≠Angeklagter-Bruch. (4) **kollisionsfreier Report-Pfad** `…-<datum>-<repo>-<session-id>.md`
  (Parallel-Sessions schreiben eigene Dateien; Default-Pfad verboten). **Methodenfixe:** Verify zieht
  Beleg unabhängig neu (nicht Finder-Befehl wiederholen — sonst überlebt False-Positive); binär
  SURVIVES/REFUTED (kein „weakened"); Belegpflicht auch für Längsschnitt-Behauptungen; Right-Sizing
  nach Befund-Dichte + harte Agenten-Budgets (lean=0 Subagenten, Skeptiker je Dimension).
