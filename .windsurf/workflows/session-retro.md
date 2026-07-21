---
description: Geerdete, adversariale Session-Retrospektive — sammelt git/gh/CI als Ground Truth, urteilt in frischem Kontext (Richter≠Angeklagter), falsifiziert jeden Befund, schlägt kopierfertige Verankerung + Scorecard vor. Schreibt Report nach platform/docs/retros/ (git, KONZ-010).
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

**Trigger-Konflikt (Rule B feuert, Dichte-Regel dämpft) — Auflösung (Lehre 2026-06-14):**
Der `deep`-Trigger „Prod-Schritt" und die Dichte-Regel „reversibel+transparent+freigegeben →
kleiner skalieren" widersprechen sich bei einem **sauberen, freigegebenen, reversiblen**
Prod-Deploy. Regel: starte beim Rule-B-Level (`deep`); **eine** Stufe runter (→ `full`) nur wenn
**alle drei** zutreffen — (a) Prod-Schritt war menschlich explizit freigegeben (Artefakt-Beleg:
PR-Body-Warnung oder `AskUserQuestion`), (b) voll rollback-fähig (gleiche Bereitstellung, **keine**
DB-Migration), (c) findings_total-Schätzung ≤10. Bei Prod-Schritt **nie** auf `lean`. Reduktion +
die drei Begründungen im Frontmatter (`footprint_reduction_reason`) festhalten.

**Increment-Retro (Anchor am selben Tag):** Läuft eine zweite Retro auf dem Abarbeiten der
Action-Items der vorigen Retro: (1) `session_id`-Suffix `-incr` (kollisionssicherer Pfad);
(2) **nur die neuen Artefakte** sind in-scope — Vor-Retro NICHT re-litigieren; (3) Parent-Retro-
Slugs zählen als Vorkommen-1 → taucht ein Slug im Increment erneut auf, ist das Vorkommen-2 ⇒
**Gate-Pflicht, auch same-day** (siehe `retro_kpis.py`); (4) Right-Sizing-Minimum mit Prod-Schritt:
`full` (nie `lean`), weil ein Anchor per Definition neue Fixes auf bekannte Muster deployt.

## Modell-Routing je Phase (Kosten-Disziplin)
Die Trennung Richter≠Angeklagter kommt vom **frischen Kontext**, NICHT vom teuren Opus →
Subagenten laufen auf dem **billigsten Modell, das die Phase trägt** (`agent(..., model: …)`):

| Phase | Wer / Modell | Warum |
|---|---|---|
| 0 Right-Sizing | **du** (inline) | trivial |
| 1 Collect (gh/git) | Subagent **haiku** | reines Sammeln, keine Wertung |
| 2 Find · 3 Verify · 5 Meta | Subagent **sonnet** | braucht **frischen Kontext** (Richter≠Angeklagter), aber Sonnet trägt Review-Tiefe — ~5× billiger als Opus (s. `session-routing.md`) |
| 3.5 Soll-Ablauf · 4 Anchor/Report | **du** (Haupt-Session) | nur *Zusammenführen* fremder Befunde + Schreiben = kein Selbst-Urteil → in-context ok |
| 6 Extern-Handoff | **fremder Anbieter** (Mensch holt ein) | stärkster Falsifikator (fremde Blindflecken) |

**Anti-Pattern:** Find/Verify durch **„du" (Haupt-Session)** erledigen = Self-Review aus eigenem
Kontext = Bruch von Regel 1. „Billiger" heißt **Sonnet-Subagent**, nicht **kein** Subagent.
Opus-Subagenten nur, wenn Sonnet nachweislich an Nuance scheitert.

## Phase 1 — Collect (Ground Truth, frischer Ermittler)
**Frisch-Checkout-Pflicht (GATE-PFLICHTIG, 8. Vorkommen — Lehre 2026-07-16, geschärft 2026-07-21):** der
allererste Befehl gegen jedes Scope-Repo ist `git fetch origin <default-branch>`,
**bevor** irgendein `git log`/`git status`/`git diff` gegen den lokalen Checkout liest —
auch bei `lean`-Footprint und auch wenn Phase 1 inline (ohne Subagent) läuft. **`fetch` ALLEIN
reicht NICHT: es aktualisiert `origin/<default-branch>`, NICHT den Working-Tree — wer danach die
Working-Tree-Datei grept/liest (`grep pattern <datei>`, `cat`), liest weiter stale. Verifikations-Reads
MÜSSEN aus dem Ref kommen: `git show origin/<default-branch>:<pfad>` bzw. `git diff origin/<default-branch>
-- <pfad>`, NIE die lokale Datei nach dem Fetch.** Diese
Pflicht galt bisher nur explizit für Phase 3 (Skeptiker); `stale-local-clone-as-ground-truth`
trat trotz „fetch first" ein 7. Mal (Phase 1, `session-retro-2026-07-16-iil-klickdummy-d80d23`:
4 gemergte PRs übersehen) und ein 8. Mal (`8d663b-incr` I2: `grep` auf lokalem mcp-hub-Tree HEAD
`c092cb8` zeigte alte Check-Zeilen, obwohl origin/main `15a1fc7` sie verankert hatte — nur durch
Content-Smell gefangen) auf — beide belegen: die Lücke ist die **Lesequelle**, nicht der Fetch.
Diese Zeile ersetzt das bloße Hoffen auf Einzelfall-Disziplin — exakt wie die Phase-3-Zeile es bereits für Skeptiker tut.

Ein Subagent sammelt **ausschließlich aus Artefakten** (kein Self-Report):
- `gh pr list --repo <owner>/<repo> --state all --search "updated:>=<datum>"` (+ `gh issue list`)
- `git -C ~/github/<repo> fetch origin <default-branch>` **zuerst**, dann `log --oneline --since=<…>`
  gegen `origin/<default-branch>` (nicht den lokalen Branch) + `git diff --stat` wo sinnvoll
- CI/main-Status der betroffenen Repos (`gh run list --branch main`)

**Aktiv nach red_flags suchen, die ein Self-Review systematisch übersieht:**
OPEN-PR überholt von späterem MERGED-PR zum selben Issue (Duplikat/dangling) · mehrere PRs
„Closes" dasselbe Issue · rote Required-Gates auf offenen PRs · Migrations-Nummern-Kollision ·
Issue offen geblieben trotz gemergtem Fix.

**Infra-Topologie-Sonde (Pflicht, wenn die Session CI/Deploy/Runner/Hosts berührte —
Lehre 2026-06-17: fehlende Infra-Transparenz war wiederholt Outage- und Merge-Blocker-
Quelle):** die SoT `platform/infra/hosts.yaml` gegen die Realität abgleichen, nicht raten:
`python3 platform/infra/scripts/hosts_audit.py --check all --workflows <repo>/.github/workflows`
(Schema + Frische der SoT + tote Runner-Label-Pins). Zusätzlich: `gh api repos/<owner>/<repo>/
actions/runners` (online vs. verwaist) und `runs-on:`-Labels der Workflows gegen lebende
Runner — ein Workflow auf einem Label, das kein Online-Runner trägt, hängt unbegrenzt und
blockiert Merges. Drift hier → Längsschnitt-Gate-Kandidat (Phase 4/5), kein Einzelfix.

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

**Finder-Mandat (hart, in JEDEN Finder-/Skeptiker-Prompt — Lehre 2026-07-04):** „Du lieferst
NUR Befunde als Text zurück — du erstellst KEINE Dateien, Branches, Commits, PRs oder
Reports und fährst keine eigene Retro-Pipeline." (Realfall e17299-incr: ein Finder fuhr
eigenmächtig Collector+Skeptiker+Report und eröffnete PR #924 auf dem Report-Zielpfad des
Orchestrators — Partial-Report ohne die anderen Dimensionen, musste mit Coverage-Nachweis
geschlossen werden; zusätzlich hatte er die Datei im geteilten Haupt-Tree gestaged.)

## Phase 2.5 — Finder-Konflikt-Erkennung (in-context, 0 Agenten — Lehre 2026-06-14)
Bevor Phase 3 startet: die Finder-Outputs auf **zwei Finder mit widersprüchlichen Fakt-Behauptungen
über dasselbe Artefakt** (gleiche Datei/PR/Status) scannen. Jeden Widerspruch explizit als Paar
markieren. **NICHT in Phase 4 selbst auflösen** — das wäre verstecktes Verify aus dem Haupt-Kontext
(Regel-1-Bruch). Stattdessen den Widerspruch als **zusätzlichen Skeptiker-Task** routen: der Phase-3-
Skeptiker zieht das umstrittene Artefakt **unabhängig aus `origin/main`** (nicht aus dem lokalen
Working-Tree) und entscheidet binär. Nur die skeptiker-verifizierte Version geht in den Report — mit
eigener Befund-Nummer + Kategorie/Severity (keine nummernlosen Tabellenzeilen). (Realfall: zwei Finder
widersprachen sich über `pptx-hub origin/main`; **ein Finder verfiel selbst in den stale-local-Fehler,
den er anklagte** — genau dafür existiert Richter≠Angeklagter.)

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

**Frisch-Checkout-Pflicht (Lehre 2026-07-06 — GATE-PFLICHTIG, 3. Vorkommen):** Jeder
Skeptiker-Prompt beginnt zwingend mit `git fetch origin <default-branch>` und prüft gegen
`origin/<default-branch>`, NICHT den lokalen Checkout. **Konkret heißt „gegen origin prüfen":
aus dem Ref LESEN (`git show origin/<default-branch>:<pfad>`), nicht die Working-Tree-Datei nach
dem Fetch greppen — Fetch bewegt `origin/<default-branch>`, nicht den Tree (Schärfung 2026-07-21, s. Phase 1).** `stale-local-clone-as-ground-truth`
war bereits ×2 gate-pflichtig (`e17299`, `a2c373`); beim Retro `3b123e` trat es ein drittes
Mal auf — diesmal INNERHALB der eigenen Skeptiker-Verifikation dieser Skill (ein Skeptiker
prüfte zunächst gegen einen veralteten lokalen `main`, in dem ein PR-Merge fehlte, und musste
nachträglich fetchen). Diese Zeile ersetzt das bloße Hoffen auf Einzelfall-Disziplin.

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
refuted_rate: <(phase3_refuted + pre_refuted)/findings_total, 0–1>  # Skill-KPI, s. Phase 5
phase3_refuted: <n>   # vom UNABHÄNGIGEN Phase-3-Skeptiker mit frischem Artefakt-Check verworfen
pre_refuted: <n>      # schon VOR Phase 3 als trivial-falsch erkannt (Finder-Stroh); NICHT die Skeptiker-Schärfe
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
- **5. Längsschnitt — der eigentliche Hebel:** **PFLICHT** `python3 tools/retro_kpis.py` laufen lassen
  (zählt `recurring_findings`-Slugs maschinell über ALLE `platform/docs/retros/session-retro-*.md`). Jeder Slug mit
  Zähler **≥2 ⇒ GATE-PFLICHT** (Hook/CI/Skill-Edit), nicht der N-te Notizzettel. Zusätzlich gegen
  `<auto-memory>/MEMORY.md` abgleichen (gleiche Kategorie mehrfach in dieser Session ODER schon als
  Drift-Memory **belegt vorhanden** — Existenz per `grep` prüfen). Der maschinelle Zähler ersetzt das
  manuelle Erinnern (Realfall 2026-06-14: `worktree-orphan-accumulation` ×2 erst vom Tool gefangen).
- **5b. Autonomie-Kalibrierung (integriert, gegen statische Charter):** zusätzlich zwei KPIs gegen die
  Artefakte messen und im Frontmatter führen — `over_ask` (etwas dem Menschen als „dein Zug" vorgelegt,
  das nachweislich **deterministisch/reversibel** war → hätte autonom laufen sollen) und `over_act`
  (etwas autonom getan, das ein **Gate** war — Prod/Publish/Merge-auto-deploy/3.-Repo/irreversibel).
  Muster **≥2 über Retros** (via `retro_kpis.py`) ⇒ die Gate-Liste in `feedback_autonomy_charter`
  **schärfen** (Grenze verschieben), nicht neu raten. So kalibriert sich die Autonomie-Grenze aus
  gemessenen Fehlern statt aus einem Einmal-Entwurf (Realfall 2026-07-03: 3 Secrets + ein grüner
  Nicht-Deploy-Merge als `over_ask` geparkt → Charter daraus entstanden).
- **6. Verankerung:** kopierfertige `memory_candidates` + `adr_candidates` (du schreibst sie NICHT selbst).
- **7. Maßnahmen als Action-Board** (Org-Standard: Buckets 🟢 dein Zug / 🔵 ich sofort / 🟡-⛔ wip / ✅ done;
  Lean-Spalten `# | Item | Repo | PR/Issue/ADR | Status | Next Step`), **abgeleitet aus dem Soll-Ablauf**.
- **8. Nicht verifiziert (Restlücken)** — Pflicht-Sektion: was offen blieb + billigster Check.

**Synthesizer-Grenze (Lehre 2026-06-14):** Phase 4 ist **nur Zusammenführen** — der Haupt-Kontext führt
hier **keine** neuen `gh`/`git`-Befehle aus. Stellt er einen Finder-Widerspruch oder ein ungedecktes
Faktum fest → zurück nach Phase 2.5/3 (Skeptiker) ODER als Lücke in §8 (Nicht verifiziert), **nicht**
still selbst-verifizieren. Befunde, die nur durch Session-Gedächtnis gedeckt sind (kein per `gh run
view` erreichbares Artefakt), werden als **Hypothese** geführt, nicht als SURVIVES mit „Beleg=Session-Log".

**Report-Pfad — durable + kollisionsfrei (Pflicht, KONZ-platform-010):**
**Durable Heimat = git `platform/docs/retros/session-retro-<datum>-<repo>-<session-id-kurz>.md`**
(zentral, versioniert, gebackupt — `retro_kpis.py` liest den Längsschnitt von dort). **NICHT mehr
`~/shared/`** (ungetrackt/ungebackupt → war für diese benötigte Funktion nicht wegwerfbar; KONZ-010).
Schreibe den Report in einen platform-Worktree unter `docs/retros/` und committe ihn (auch wenn die
reviewte Session ein anderes Repo betraf — der Cross-Repo-Längsschnitt lebt zentral in platform).
**Jede Session schreibt ihre eigene Datei;** `<repo>` = primäres Scope-Repo, `<session-id-kurz>` =
letzte ~6 Zeichen der Session-ID. **Existiert der Pfad → NICHT überschreiben**, Suffix anhängen. Der
bloße `…-<datum>.md`-Default ist verboten (Realfall 2026-06-04: Parallel-Session-Kollision).

## Phase 5 — Self-Review (Meta-Agent, nur OUTPUT-Qualität) — `full`/`deep`
Selbstverbesserung der Skill **ohne Richter≠Angeklagter zu brechen:** ein **separater Meta-Agent**
prüft AUSSCHLIESSLICH den **Report-Entwurf gegen die Skill-Regeln** — NIE die Session-Erzählung.
Er sieht nur den Report + diese Skill. Checkliste:
- Hat **jeder** Befund (inkl. Längsschnitt-Behauptung) einen per `gh/git` **unabhängig nachgeprüften** Beleg?
- Scores ganzzahlig 1–5, je an Befund verankert? (fängt erfundene Halbwerte wie `2.5`)
- **Invariante** `|Soll-Schritte| == |überlebende Befunde|` erfüllt?
- Frontmatter schema-valide (alle Pflichtfelder)? Report-Pfad kollisionsfrei (repo+session-id)?
- `refuted_rate` plausibel? Der Meta-Reviewer kommentiert sie **ausschließlich numerisch** als
  Band-Vergleich (aktueller Wert vs. die vorangehenden Retros via `retro_kpis.py`) — er beurteilt
  **NICHT**, ob einzelne SURVIVES/REFUTED-Entscheide inhaltlich korrekt sind (das wäre Session-Urteil).
  Band-KPI: dauerhaft **>0,8** → Finder zu lasch (widerlegbares Stroh); **<0,2** → Falsifikation ist
  Theater. **Nur `phase3_refuted/(findings_total − pre_refuted)` ist die echte Falsifikations-Quote**
  (hohes `pre_refuted` = schwache Finder, nicht scharfer Skeptiker). Auffälligkeit als `## Self-Review`.

> **Längsschnitt der Skill selbst (PFLICHT in Phase 4, nicht optional):** `python3 tools/retro_kpis.py`
> liest die Frontmatter aller `platform/docs/retros/session-retro-*.md`, trendet `refuted_rate`/Scores und eskaliert
> jeden `recurring_finding` mit Zähler **≥2 über Retros** zum Gate-PR-Pflicht-Item. Stdlib-only, kein Setup.

**Agenten-Budget-Hinweis:** ein `full`-Lauf mit Phase 5 braucht den 6. Subagenten (Meta) — das `≤5` in der
Phase-0-Tabelle gilt für die Find/Verify-Pipeline; der Meta-Reviewer kommt **obendrauf** (also `full` ≤6,
`deep` zzgl. Phase-6-Extern).

## Phase 6 — Extern-Handoff (optional, nur `deep`)
Stärkste Stufe der Selbstverbesserung: eine **anbieter-fremde** Zweitmeinung (nicht nur frischer
Kontext, sondern fremde Trainings-Blindflecken). Muster wie [`adr-handoff-extern`].

Schreibe ein Briefing nach `~/shared/session-retro-extern-<datum>-<repo>-<sid>.md`:
1. den fertigen Report (Phase 4),
2. die 4 Eisernen Regeln + das Output-Schema dieser Skill,
3. Auftrag: *„**Advocatus Diabolus + Out-of-the-Box:** finde, was dieser Retro übersehen oder
   falsch bewertet hat. Du hast **KEIN Repo-Zugriff** → kritisiere **Methode/Struktur/Blindflecken/
   Score-Logik/Soll-Ablauf**, behaupte **keine** Evidenz-Fakten (die prüft Phase 3 mit gh/git)."*

Mensch holt die Zweitmeinung extern, faltet sie zurück. **Harte Grenze:** extern kann **Methode**
challengen, **nicht Evidenz nachprüfen** (kein gh/git) — Evidenz-Recheck bleibt Phase 3/5.
**Loop:** wiederkehrende Methoden-Kritik fließt als Verbesserung in **diese Skill** (Changelog) —
genau wie die Skill ursprünglich aus einem Diabolus-Review entstand.

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
- ❌ Find/Verify durch **„du"/Haupt-Session** „zum Sparen" — das ist Self-Review (Regel-1-Bruch). Kosten-Fix = **Sonnet-Subagent**, nicht **kein** Subagent.
- ❌ **Opus-Subagenten** als Default — Sonnet trägt Find/Verify/Meta; Opus nur bei nachgewiesenem Nuance-Fail.
- ❌ Extern-Handoff (Phase 6) **Evidenz-Fakten** behaupten lassen — extern hat kein gh/git, nur Methoden-Kritik.
- ❌ **Finder-vs-Finder-Widerspruch durch die Haupt-Session (Phase 4) per neuem git/gh auflösen** — verstecktes Verify (Regel-1-Bruch); Widersprüche gehören als Skeptiker-Task nach Phase 2.5/3.
- ❌ **Nummernlose Befund-Zeile** (Finder-Konflikt-Funde ohne `#`/Kategorie/Severity) — bricht die eingefrorenen Spalten + den `findings_total`-Zähler.
- ❌ **`recurring_finding` im Frontmatter ohne `retro_kpis.py`-Zähler-Check** — Längsschnitt ist dann Dekoration, kein Hebel (genau das Anti-Pattern, das die Skill predigt, auf sich selbst angewandt).
- ❌ **`refuted_rate` ohne `pre_refuted`-Trennung** — trivial-falsche Finder-Behauptungen (vom Haupt-Kontext vor-widerlegt) blähen die Quote und verfälschen das Skill-KPI.
- ❌ **Phase-1-Collect liest lokalen `git log` ohne vorheriges `git fetch`** — die Frisch-Checkout-Pflicht gilt nicht nur für Phase-3-Skeptiker, sondern für JEDEN Collect-Schritt, auch inline bei `lean`.

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
- 2026-06-04 (v2.1): **Modell-Routing je Phase** (Kosten) — Subagenten auf billigstem tragenden
  Modell: Collect=haiku, Find/Verify/Meta=**sonnet** (frischer Kontext ≠ teures Opus → ~5× günstiger),
  Synthese/Report inline bei der Haupt-Session; „billiger" heißt Sonnet-Subagent, NICHT Self-Review.
  **Phase 6 Extern-Handoff** (optional, deep) — anbieter-fremde Methoden-Zweitmeinung (Muster
  `adr-handoff-extern`); harte Grenze: extern kritisiert Methode, prüft KEINE Evidenz (kein gh/git);
  wiederkehrende Kritik fließt zurück in die Skill (Self-Improvement-Loop mit externem Falsifikator).
- 2026-06-14 (v2.2): **Self-Improvement aus zwei realen Läufen am selben Tag** (Richter≠Angeklagter:
  frischer Skill-Kritiker gegen die zwei erzeugten Reports). **Fixes:** (1) **`tools/retro_kpis.py`
  gebaut** (war nur „falls vorhanden" referenziert → Längsschnitt-Hebel war fiktiv; 15 Reports lagen
  ungelesen). Stdlib-only, zählt `recurring_findings` über Retros, eskaliert ≥2 → GATE-PFLICHT; fing
  beim ersten Lauf `worktree-orphan-accumulation ×2`. Phase-4-Pflichtaufruf, „falls vorhanden"-Hedge
  entfernt. (2) **Phase 2.5 Finder-Konflikt-Erkennung** — widersprechen sich zwei Finder über einen
  Fakt, war die Auflösung still in Phase 4 (Haupt-Session zieht neues git/gh = Regel-1-Bruch; Realfall:
  ein Finder verfiel selbst in den stale-local-Fehler, den er anklagte). Jetzt: als Skeptiker-Task nach
  Phase 3, Synthesizer führt KEINE neuen Befehle aus. (3) **`refuted_rate` 3-Feld-Split** (`phase3_refuted`
  + `pre_refuted`) — Vor-Widerlegungen durch den Haupt-Kontext verfälschten das KPI. (4) **Trigger-Konflikt-
  Auflösung** (deep „Prod-Schritt" vs. Dichte-Downscale) + **Increment-Retro-Regeln** (same-day Anchor).
  (5) **Phase-5-Budget** geklärt (`full` ≤6 mit Meta) + Meta-Reviewer nur **numerisch** (kein Einzel-Befund-
  Urteil). Quelle: `~/shared/session-retro-2026-06-14-coach-hub-2d7cd9*.md` + adversarialer Skill-Kritiker.
- 2026-07-04 (v2.3): **Finder-Mandat-Satz** (Phase 2, hart): Finder/Skeptiker liefern NUR
  Befunde als Text — keine Dateien/Branches/Commits/PRs/eigene Pipelines. Realfall e17299-incr:
  ein Entscheidungs-Finder fuhr eigenmächtig Collector+Skeptiker+Report, eröffnete PR #924 auf
  dem Report-Zielpfad des Orchestrators (Partial ohne die anderen Dimensionen; mit Coverage-
  Nachweis geschlossen) und stagede die Datei im geteilten Haupt-Tree. Quelle:
  `docs/retros/session-retro-2026-07-04-platform-e17299-incr.md` §6.2/Self-Review.
- 2026-07-06 (v2.4): **Frisch-Checkout-Pflichtzeile** (Phase 3): jeder Skeptiker-Prompt beginnt
  jetzt zwingend mit `git fetch origin <default-branch>` + Prüfung gegen `origin/<branch>`.
  `stale-local-clone-as-ground-truth` war bereits ×2 gate-pflichtig (`e17299`, `a2c373`); im
  Retro `3b123e` trat es ein 3. Mal auf — diesmal innerhalb der eigenen Skeptiker-Verifikation
  dieser Skill. Quelle: `docs/retros/session-retro-2026-07-06-frist-hub-3b123e.md` Befund #8/§6.
- 2026-07-16 (v2.5): **Frisch-Checkout-Pflicht auf Phase 1 (Collect) ausgeweitet** — bisher galt
  die Zeile nur explizit für Phase-3-Skeptiker; ein lean-Footprint-Retro (kein Subagent, Inline-
  Collect) las `git log` gegen einen ungefetchten lokalen `main`, übersah 4 gemergte PRs und
  produzierte einen Befund, der beim späteren Merge-Versuch als REFUTED aufflog — 7. Instanz von
  `stale-local-clone-as-ground-truth`, diesmal in Phase 1 statt Phase 3. Quelle:
  `docs/retros/session-retro-2026-07-16-iil-klickdummy-d80d23.md` Befund #2.
- 2026-07-21 (v2.6): **Frisch-Checkout-Pflicht präzisiert (Phase 1 + Phase 3): „fetch first" reicht
  NICHT — nach dem Fetch aus dem REF lesen** (`git show origin/<branch>:<pfad>`), nicht die
  Working-Tree-Datei greppen. Fetch bewegt `origin/<branch>`, nicht den Tree; ein grep auf die lokale
  Datei liest danach weiter stale. 8. Instanz von `stale-local-clone-as-ground-truth`, diesmal INNERHALB
  eines lean-Increment-Retros dieser Skill (`8d663b-incr` I2): `grep` auf lokalem mcp-hub-Tree (HEAD
  `c092cb8`) zeigte alte Check-Zeilen trotz vorherigem `fetch`, weil origin/main (`15a1fc7`) nur den Ref
  bewegte — nur durch Content-Smell gefangen. Die bestehende Zeile („fetch first") war unvollständig:
  die Lücke ist die Lesequelle, nicht der Fetch. Memory `feedback_stale_clone_read_from_ref_not_tree_after_fetch`.
  Quelle: `docs/retros/session-retro-2026-07-21-platform-8d663b-incr.md` Befund I2.
