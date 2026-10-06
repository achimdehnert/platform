---
description: Geerdete, adversariale Session-Retrospektive — sammelt git/gh/CI als Ground Truth, urteilt in frischem Kontext (Richter≠Angeklagter), falsifiziert jeden Befund, schlägt kopierfertige Verankerung + Scorecard vor. Schreibt Report nach platform/docs/retros/ (git, KONZ-010).
mode: write
---

# /session-retro — Geerdeter, adversarialer Session-Review

> **Wann:** nach größeren Umbau-/Architektur-Sessions, am Sitzungsende; Trivial-Edits höchstens
> `lean`. **Das *Warum* jeder Regel:** `LEHREN` = `docs/governance/session-skills-lehren/retro.md`
> (Zweck-Satz → LEHREN#v2b-kopf).

## Eiserne Regeln — die 5 Fixes (nicht verhandelbar)

1. **Richter ≠ Angeklagter.** Urteile NIE aus deinem Session-Gedächtnis. Jeden Befund über einen
   **frischen Subagenten** erzeugen, der nur die Artefakte sieht — nicht deine Erzählung.
2. **Evidenz vor Behauptung.** Jeder Befund braucht einen harten Artefakt-Beleg (repo#PR,
   Commit-SHA, Datei:Zeile, CI-Run). Kein Beleg → kein Befund.
3. **Falsifikation.** Jeden Befund einem Widerlegungs-Pass aussetzen (Steelman der
   Original-Entscheidung). Nur Überlebende bleiben — sonst entsteht performative Kritik.
4. **Geschlossener Loop.** Lessons NICHT als Prosa versanden lassen → als **kopierfertige**
   Memory-/ADR-/CLAUDE.md-Vorschläge ausgeben. Verankerung entscheidet der Mensch.
5. **Nullbefund ist rechenschaftspflichtig, kein Haken.** Endet ein Finder- oder
   Falsifikations-Pass mit **null** Befunden, wird dokumentiert, **was erfolglos versucht wurde**
   (Dimensionen, Artefakte, Zeiträume). Kein Zwang, etwas zu finden: verlangt ist die
   *Abdeckungsauskunft*. Jeder Report endet auf **getan · angenommen · nicht verifizierbar ·
   offen geblieben**.

## Phase 0 — Right-Sizing (Footprint **und** erwartete Befund-Dichte)

### 0.0 Wirkungsbilanz lesen — ERSTER Schritt, vor allem anderen (PFLICHT — NEU 2026-09-02, platform#2690 K4)

```bash
python3 tools/gate_wirkung.py
```

**Jedes `RUECKFAELLIG`-Gate wird behandelt, BEVOR ein neuer Befund aufgemacht wird.** Eine Zeile
je Gate: `Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz`.

- **Ursache am Ausgang** (Gate feuert, niemand handelt danach) ⇒ **Modus herabstufen** oder
  **Sunset** (`declined` mit Grund) — ein Melder ohne Wirkung wird nicht lauter gemacht.
- **Ursache an der Quelle** (Gate sieht den Fall nicht) ⇒ **nachschärfen** oder **Drill
  ergänzen**, wenn der namensgebende Fall ungedrillt ist (`gate_namensdeckung.py`).

Nur diese vier Konsequenzen; „im Report erwähnt" ist keine. Hier wird **entschieden**, in
Phase 4 (5a) umgesetzt; ein verbuchter Rückfall wird nicht ein zweites Mal als neuer Befund
aufgemacht. **Ehrlichkeits-Sperre:** `zu-frueh`/`unerprobt` heißt ungeprüft, nicht wirksam —
kein berichtbarer Erfolg. → LEHREN § Phase 0.0

### 0.1 Footprint + Befund-Dichte
Footprint messen (PRs / Repos / Prod-Schritte / Migrationen / ADRs) **und** Befund-Dichte
schätzen: Session **reversibel + transparent + freigegeben** ⇒ harte Survivors selten → kleiner
skalieren. Stufe + **hartes Agenten-Budget**:

| Stufe | Trigger | Agenten-Budget |
|---|---|---|
| **lean** | ≤2 PRs, 1 Repo, kein Prod/Migration/ADR | **0 Subagenten**, 1 Inline-Pass, 2 Dimensionen |
| **full** | Standard | 3 Finder + Skeptiker **je Dimension** + 3b — ≤5 |
| **deep** | ≥3 Repos ODER Prod ODER Migration ODER Verdacht auf vertuschte Fehler | volle Pipeline + 3b + Phase-5-Meta; Skeptiker ≤ Anzahl Dimensionen |

Kein Multi-Agent unter `lean`. Falsifikation gebündelt je Dimension (Ausnahme: Phase 3).

**Skeptiker nur auf Bewertungsbefunde** — das Budget bezahlt **fremden Kontext**, nicht die
Zweitausführung eines Befehls:

| Klasse | Beleg ist … | Skeptiker? |
|---|---|---|
| **kommandobelegt** | reproduzierbares Kommandoergebnis (`grep -c`, Datei-Existenz, CI-Status, Textvergleich) | **nein** — liefert dieselbe Zahl |
| **Bewertungsbefund** | Urteil über eigene Entscheidungen („vermeidbar", „zu spät", „falsch kalibriert") | **ja** — nur hier wirkt Richter≠Angeklagter |

Auftrag **neutral** („widerlege, wenn du kannst"). **~55k Tokens je Skeptiker** (gemessen) —
bei Budget-Freigabe nennen. Ohne Subagenten: inline, Bewertungsbefunde zur Freigabe, Restlücke
in §8. → LEHREN § Phase 0.1

**Trigger-Konflikt:** `deep` → `full` nur bei (a) Prod freigegeben, (b) rollback-fähig, keine
Migration, (c) ≤10 Befunde; mit Prod **nie** `lean`; Grund als `footprint_reduction_reason`.
**Increment-Retro:** Suffix `-incr`, nur neue Artefakte, Parent-Slug wiederholt ⇒ Gate-Pflicht.
Volltext beider Regeln: → LEHREN#v2b-phase-0

## Modell-Routing je Phase (Kosten-Disziplin)
Richter≠Angeklagter kommt vom **frischen Kontext**, nicht vom teuren Modell:

| Phase | Wer / Modell |
|---|---|
| 0 · 1 · 3.5 · 4 · 7 | **du** (inline, 0 Agenten) — Zusammenführen und Artefaktliste, kein Selbst-Urteil |
| 2 Find · 3 Verify · 5 Meta | Subagent **sonnet** — frischer Kontext, ~5× billiger als Opus (`session-routing.md`) |
| **3b Widerlegungsbahn** | Subagent **Tier 4 (Opus)**, frischer Kontext — Owner-Entscheid 2026-09-02 ([#2374](https://github.com/achimdehnert/platform/issues/2374#issuecomment-5510996006)) |
| 6 Extern-Handoff | **fremder Anbieter** (Mensch holt ein) — fremde Blindflecken |

Find/Verify durch **„du"** bricht Regel 1. Opus nur in 3b oder bei Nuance-Fail.

## Phase 1 — Collect (Ground Truth, frischer Ermittler)
**Frisch-Checkout-Pflicht (GATE-PFLICHTIG, 8. Vorkommen):** erster Befehl gegen jedes Scope-Repo
ist `git fetch origin <default-branch>`, **bevor** ein `git log`/`status`/`diff` den lokalen
Checkout liest — auch bei `lean`. **Danach aus dem Ref lesen**
(`git show origin/<default-branch>:<pfad>`), nie die Working-Tree-Datei greppen: Fetch bewegt
den Ref, nicht den Tree. → LEHREN § Phase 1 / Phase 3

**Session-Grenze = die Konversation, NICHT der Kalendertag.** Scope über **Branch-Präfixe/
PR-Nummern der eigenen Sitzung** (bzw. den Transkript-Pfad); das Datum ist nur Vorfilter.
Genannte Repos sind in-scope — nie als „separater Workstream" wegklassifizieren.

**Inline, 0 Agenten:** du erstellst nur die **Artefaktliste** (PR-/Issue-Nummern, Repos,
Host-Dienste) und gibst sie jedem Finder-Prompt mit; bewertet wird nichts (Regel 1). Die
Sammel-Befehle in **EINER Nachricht** (platform#3373); einzige Reihenfolge-Pflicht: `fetch` vor
`log`/`show` **desselben** Repos.
- `gh pr list --repo <owner>/<repo> --state all --search "updated:>=<datum>"` (+ `gh issue list`)
  — danach auf die Sitzung **eingrenzen**
- `git -C ~/github/<repo> fetch origin <default-branch>`, dann
  `log --oneline --since='<YYYY-MM-DD> 00:00'` gegen `origin/<default-branch>` —
  ⚠️ **`--since` immer MIT Uhrzeit**, sonst stille Null trotz existierender Commits
- `python3 tools/retro_transkript_kennzahlen.py <transkript.jsonl> [--von ISO] [--bis ISO]`,
  vorher einmal `--selbsttest`: Ablehnungen, Fehlerläufe (auch ohne `is_error`),
  Silent-Reminder mit Abstand zum nächsten sichtbaren Text, Nutzer-Nachrichten. Ausgabe als
  Datei an die Finder — kein Agent wertet das JSONL selbst aus. → LEHREN#v2b-phase-1

**red_flags (Auftrag an den Finder „Prozess & Kollaboration"):** OPEN-PR überholt von späterem
MERGED-PR zum selben Issue · mehrere PRs „Closes" dasselbe Issue · rote Required-Gates auf
offenen PRs · Migrations-Nummern-Kollision · Issue offen trotz gemergtem Fix.

**Infra-Topologie-Sonde (Pflicht, wenn die Session CI/Deploy/Runner/Hosts berührte):**
`platform/infra/hosts.yaml` gegen die Realität —
`python3 platform/infra/scripts/hosts_audit.py --check all --workflows <repo>/.github/workflows`
+ `gh api repos/<owner>/<repo>/actions/runners` gegen `runs-on:`. Drift → Gate-Kandidat.
→ LEHREN § Phase 1 Infra, LEHREN#v2b-phase-1

## Phase 2 — Find (frischer Kontext, je Dimension)

**Alle Finder in EINER Nachricht starten (PFLICHT — NEU 2026-09-22, platform#3373)**, ebenso
die Skeptiker in Phase 3. Das Budget aus 0.1 zählt Agenten, nicht Runden. → LEHREN#v2b-phase-2

Je Dimension ein **eigener** Subagent (kennt die Session-Erzählung nicht), geerdet im Footprint:
- **Soll-Ist & Scope** — Ziel vs. Geliefertes; Scope Creep; still Weggelassenes; Offenes, das das Ziel verfehlt.
- **Entscheidungen & Fehler** — tragfähig vs. fragwürdig; Anti-Patterns; Konventionsverstöße; Tech-Debt; verfrühte Festlegungen.
- **Prozess & Kollaboration** — Rework, Duplikat-/dangling-PRs, rote Gates, unklare Steuerung, fehlende frühe Checks.

Je Befund: Schweregrad (kritisch/hoch/mittel/niedrig) + Root Cause (5-Why) + Kategorie
(Wissenslücke / Prozesslücke / Kommunikation / verfrühte Festlegung / fehlende Validierung / Werkzeug).

**Finder-Mandat (hart, in JEDEN Finder-/Skeptiker-Prompt):** „Du lieferst NUR Befunde als Text
zurück — du erstellst KEINE Dateien, Branches, Commits, PRs oder Reports und fährst keine eigene
Retro-Pipeline." → LEHREN § Phase 2

## Phase 2.5 — Finder-Konflikt-Erkennung (in-context, 0 Agenten)
Finder-Outputs auf **widersprüchliche Fakt-Behauptungen über dasselbe Artefakt** scannen, je
Widerspruch ein **zusätzlicher Skeptiker-Task** (zieht unabhängig aus `origin/main`, binär) —
**nicht in Phase 4 auflösen**. Nur die verifizierte Version geht in den Report, mit eigener
Befund-Nummer. → LEHREN § Phase 2.5

## Phase 3 — Verify (Falsifikation)
Skeptiker-Subagent **je Dimension**. **Binär: SURVIVES oder REFUTED** — kein
„weakened"/„teilweise"; mildernde Umstände gehören in die Beleg-Spalte. Vorher sortieren:
kommandobelegte Befunde überspringen (Tabelle 0.1). Bei ≤2 Bewertungsbefunden ist ein Skeptiker
**je Befund** günstiger und schärfer; das Budget-Argument greift ab etwa vier. Alle Skeptiker
in EINER Nachricht starten.

**Eiserne Verify-Regel:** Der Skeptiker bekommt **nur die Behauptung, NICHT den Finder-Befehl**
und zieht den Beleg **unabhängig neu**, breiter/rekursiv (`find -name` statt `ls <dir>`,
`grep -r` statt `grep <datei>`) — sonst wandert ein False-Positive ungeprüft durch.
**Längsschnitt-Behauptungen** („wiederholt Drift-Memory X") brauchen den Existenz-Beleg per
`ls`/`grep`, sonst REFUTED.

**Frisch-Checkout-Pflicht (GATE-PFLICHTIG, 3. Vorkommen):** jeder Skeptiker-Prompt beginnt mit
`git fetch origin <default-branch>` und liest aus dem Ref (wie Phase 1).

Nur SURVIVES gehen in den Report.

## Phase 3b — Widerlegungsbahn (PFLICHT ab Footprint `full`; NEU 2026-09-02, platform#2690 K5)
3b widerlegt **das Urteil dieser Retro** (→ LEHREN#v2b-phase-3b). **Ein** Subagent, Tier 4,
frischer Kontext, mit gh/git. Er sieht
**Report-Entwurf + Footprint + Artefaktliste** — NICHT die Session-Erzählung, NICHT die
Finder-Prompts. Auftrag: *„Widerlege das Urteil dieser Retro."* Drei Fragen, je mit Beleg:

1. Ist ein **SURVIVES** falsch stehen geblieben? (Gegenbeleg aus `origin/<default-branch>`)
2. Ist ein **REFUTED** zu früh verworfen worden?
3. Fehlt eine ganze **Dimension**? Nenne EINEN Befund, den keiner der Finder hatte.

Je Befund **widerlegt / hält / unentscheidbar** (letzteres nur mit dem billigsten fehlenden
Check); Verdikt `BESTAETIGT`/`GEKIPPT`/`NEU`. Ausgabe als `## Widerlegung` **und**
Frontmatter `widerlegung: "<n> gekippt, <m> neu"`. Ohne Fund ⇒ Abdeckungsauskunft (Regel 5).
Bei `lean` begründet n/a. Kosten: ein Agent obendrauf (`full` ≤7).

## Phase 3.5 — Soll-Ablauf (konstruktiv, an Überlebende gekoppelt)
Pro **überlebendem** Befund **genau ein** artefakt-verankerter Alternativschritt:

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| … was real geschah | … der konkrete bessere Schritt/Checkpoint | #<Befund> |

**Invariante (hart):** `|Soll-Schritte| == |überlebende Befunde|` — kein Soll-Schritt ohne
Befund-Referenz, kein Überlebender ohne Soll-Schritt. Die Top-3-Maßnahmen (Phase 4) werden
daraus **abgeleitet**, nicht frei erfunden.

## Phase 4 — Anchor (schließen + Längsschnitt)
**Pflicht-Report-Skelett** — feste Reihenfolge, feste Tabellenspalten, maschinenlesbares
YAML-Frontmatter (sonst ist der Längsschnitt nicht auswertbar):

```yaml
---
retro_schema: 1
date: <YYYY-MM-DD>
repo_scope: [<repo>, …]   # bare Repo-Slugs (a-z0-9_-), kein Pfad, kein owner/repo
session_id: <kurz>
footprint: lean|full|deep
findings_total: <n>
findings_survived: <n>
refuted_rate: <(phase3_refuted + pre_refuted)/findings_total, 0–1>   # Skill-KPI, s. Phase 5
phase3_refuted: <n>   # vom UNABHAENGIGEN Phase-3-Skeptiker verworfen
pre_refuted: <n>      # schon VOR Phase 3 trivial-falsch (Finder-Stroh)
scores:               # ganzzahlig 1–5, KEINE Halbwerte
  zielerreichung: <1-5>
  architektur_design: <1-5>
  code_konventionstreue: <1-5>
  risiko_debt: <1-5>
  prozess_effizienz: <1-5>
  entscheidungsqualitaet: <1-5>
gate_candidates: [<slug>, …]
recurring_findings: [<slug>, …]
gates_caught: [<slug>, …]   # Teilmenge: von einem BESTEHENDEN Gate gefangen ⇒ Beleg FUER
                            # das Gate, nicht Rueckfall
gates_verwandt: [<slug>, …]   # Teilmenge: Fall lag ausserhalb des Zuschnitts des Gates ⇒ kein Rueckfall
over_ask_klassen: [<slug>, …]
over_act_klassen: [<slug>, …]
widerlegung: "<n> gekippt, <m> neu"   # Phase 3b, PFLICHT ab full
streichkandidaten: [<slug>, …]        # Phase 7; leer erlaubt, dann streich_begruendung Pflicht
streich_begruendung: <satz>           # nur wenn streichkandidaten leer
---
```
Danach in fester Reihenfolge:
- **1. Executive Summary** (max 5 Bullets).
- **2. Befund-Tabelle**, eingefrorene Spalten: `# | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence`.
  Keine nummernlosen Zeilen.
- **3. Scorecard** — die 6 Frontmatter-Dimensionen, **ganzzahlig 1–5**, je **an einem Befund
  verankert**. Rubrik: `1`=Kernziel verfehlt · `2`=verfehlt mit Rework · `3`=teilweise, Abweichung
  begründet · `4`=erreicht, kleine Mängel · `5`=vorbildlich.
- **4. Soll-Ablauf** (aus 3.5).
- **5. Längsschnitt — PFLICHT** `python3 tools/retro_kpis.py` (zählt `recurring_findings`-Slugs
  über ALLE `docs/retros/session-retro-*.md`). Slug mit Zähler **≥2 ⇒ GATE-PFLICHT**
  (Hook/CI/Skill-Edit), nicht der N-te Notizzettel. Zusätzlich gegen
  `<auto-memory>/MEMORY.md` abgleichen — Existenz per `grep` prüfen, nicht erinnern.
- **5a. Rückfall-Prüfung — hat ein GEBAUTES Gate versagt? (PFLICHT)** `python3 tools/gate_wirkung.py`
  trennt Vorkommen **vor** und **nach** dem Bau. Kehrt ein Slug wieder, für den ein Gate unter
  `docs/governance/gates/gates/` steht, lautet der Befund **„Gate X ist rückfällig"** (Slug
  `gate-<name>-wirkungslos`) mit genau einer Antwort: **ausweiten** (sieht die Familie nicht) ·
  **umbauen** (zu spät/falscher Pfad) · **herabstufen** (begründet in `declined`). „Nochmal
  aufschreiben" ist keine. **Ein Rückfall ändert das BESTEHENDE Gate, nie ein zweites unter
  neuem Namen (PFLICHT):** `revised` + `revision_note`, bei Ausweitung eine neue
  `positivkontrolle`. Der Edit läuft durch `tools/gate_verankerung_check.py --neu`, sonst ist er
  Kandidat, kein Eintrag. **Zuschnitt:** Fall außerhalb des Zuschnitts ⇒ `gates_verwandt:
  <Begründung ≥10 Zeichen>`, zählt nicht als Rückfall. → LEHREN § Phase 4 Punkt 5a,
  LEHREN#v2b-phase-4
- **5b. Autonomie-Kalibrierung:** `over_ask` (vorgelegt, obwohl **deterministisch/reversibel**)
  und `over_act` (autonom getan, obwohl **Gate**: Prod/Publish/Merge-auto-deploy/3.-Repo/
  irreversibel) gegen die Artefakte messen; **Klassen-Slugs Pflicht**, eng benannt. Muster ≥2
  über Retros ⇒ Gate-Liste schärfen; `retro_kpis.py --nominierung` → LEHREN#v2b-phase-4.
- **6. Verankerung:** kopierfertige `memory_candidates` + `adr_candidates` (du schreibst sie NICHT selbst).
- **7. Maßnahmen als Action-Board** (🟢 dein Zug / 🔵 ich sofort / 🟡-⛔ wip / ✅ done; Spalten
  `# | Item | Repo | PR/Issue/ADR | Status | Next Step`), **aus dem Soll-Ablauf abgeleitet**.
- **8. Nicht verifiziert (Restlücken)** — Pflicht-Sektion: was offen blieb + billigster Check.
- **`## Widerlegung`** (Phase 3b) und **`## Streichbahn`** (Phase 7) als eigene Abschnitte.

**Synthesizer-Grenze:** Phase 4 führt **nur zusammen** — **keine** neuen `gh`/`git`-Befehle;
Widerspruch → zurück nach 2.5/3 oder Lücke in §8. Nur-Gedächtnis-Befunde sind **Hypothese**.

**Report-Pfad (KONZ-platform-010):**
`platform/docs/retros/session-retro-<datum>-<repo>-<session-id-kurz>.md` (letzte ~6 Zeichen),
committet. **Existiert der Pfad → NICHT überschreiben**, Suffix anhängen. → LEHREN#v2b-phase-4

## Phase 5 — Self-Review (Meta-Agent, nur OUTPUT-Qualität) — `full`/`deep`
Ein **separater Meta-Agent** prüft AUSSCHLIESSLICH den **Report-Entwurf gegen die Skill-Regeln**
— er sieht nur Report + Skill, NIE die Session-Erzählung:
- Hat **jeder** Befund (inkl. Längsschnitt-Behauptung) einen per `gh/git` **unabhängig
  nachgeprüften** Beleg?
- Scores ganzzahlig 1–5, je an Befund verankert?
- **Invariante** `|Soll-Schritte| == |überlebende Befunde|` erfüllt?
- Frontmatter schema-valide (inkl. `widerlegung` + `streichkandidaten`)? Pfad kollisionsfrei?
- **`gate_wirkung.py` gelaufen (0.0 und 5a)?** Führt der Report ein `RUECKFAELLIG`-Gate nur als
  Slug statt als **„Gate rückfällig"** mit einer der drei Antworten ⇒ **Befund am Report**.
- `refuted_rate` nur numerisch gegen das Band (`retro_kpis.py`) → LEHREN#v2b-phase-5;
  Auffälligkeit als `## Self-Review`.

**Agenten-Budget:** `full` mit 3b und Meta = ≤6 (`≤5` in 0.1 = reine Find/Verify-Pipeline).
`deep` zzgl. Phase-6-Extern. → LEHREN § Phase 5

## Phase 6 — Extern-Handoff (optional, nur `deep`)
Anbieter-**fremde** Zweitmeinung, Muster wie [`adr-handoff-extern`]. Briefing nach
`~/shared/session-retro-extern-<datum>-<repo>-<sid>.md`: (1) Report, (2) die 5 Eisernen Regeln
+ Output-Schema, (3) Auftrag Advocatus Diabolus **ohne Repo-Zugriff** — nur Methode/Struktur/
Blindflecken, **keine** Evidenz-Fakten (Wortlaut → LEHREN#v2b-phase-6).

**Rückweg (manuell über den Owner):** Antwort liegt als
`~/shared/session-retro-extern-<datum>-<repo>-<sid>-extern1.md` (zweiter Anbieter `…-extern2.md`)
und ist **Pflichtlektüre der nächsten Retro desselben Scopes**: je Punkt **hält / widerlegt /
unentscheidbar** mit Beleg, Überlebende in den Changelog, der Rest mit Grund verworfen;
Abschnitt `## Extern-Auswertung`. ⚠️ **Fehlende `-extern*.md` heißt NICHT „keine Antwort" und
NIE „kein Leser".** → LEHREN#v2b-phase-6

## Phase 7 — Streichbahn (PFLICHT, jeder Footprint; NEU 2026-09-02, platform#2690 K5)
Genau **eine** Frage am Ende jeder Retro: *„Welche Phase / welcher Melder / welche
Skill-Sektion / welches Gate gehört WEG?"* → LEHREN#v2b-phase-7. Zulässig sind genau **zwei**
Antworten:

**(a) ≥1 Streichkandidat MIT Beleg** — genau eine der vier Belegarten:

| Belegart | wie belegt |
|---|---|
| **kein Leser** | der Output landet in keinem Artefakt (`gh`-Suche: 0 oder nur Uralt-Treffer) |
| **kein Effekt** | ein Tool/Gate erzwingt dieselbe Wirkung ohnehin (Registry-Eintrag/`record`-Zeile nennen) |
| **Dublette** | dieselbe Aussage steht in einem anderen Skill/Doc (Fundstelle nennen) |
| **Liegezeit** | Artefakte liegen im Median > 14 d ohne Entscheidung (`gate_deckung.py`, `befund_journal.py --bericht`) |

**(b) „keiner, weil <Satz>"** — mit dem Grund, nicht nur dem Wort.

Ergebnis als `streichkandidaten:` (leer ⇒ `streich_begruendung:` Pflicht), `## Streichbahn`
und Action-Board-Zeile. **Ratsche:** Kandidat zwei Retros in Folge ungestrichen = Befund.

## Phase 8 — Report gegen die eigenen Regeln prüfen (PFLICHT, jeder Footprint; NEU 2026-09-16)

```bash
python3 tools/retro_report_check.py docs/retros/<dein-report>.md
```

Exit 0 oder Befund beheben — nicht „im Report erwähnt". Geprüft: Vierklang aus Regel 5, `## 8`,
eingefrorene Spalten, Pflicht-Frontmatter-Felder, Streichbahn (leer nur mit Grund-Satz). §8
vorhanden ist **kein** Beleg für Regel 5. Läuft zusätzlich in der CI. → LEHREN#v2b-phase-8

## Phase 9 — Abschluss: Maßnahmen statt Nacherzählung (PFLICHT, wenn etwas zu entscheiden ist; NEU 2026-10-05, Owner-Wort)

Übergabe = Entscheidungsvorlage, keine Nacherzählung des Reports:

1. **Erster Satz:** ob die Sitzung gefahrlos geschlossen werden kann.
2. **Nummerierte Maßnahmenliste**, je Zeile: stabiles Kürzel · was zu entscheiden ist ·
   Empfehlung · Link auf bestehendes Issue/PR; getrennt nach „dein Wort nötig" und „kann ich
   ohne dich". Quelle: Top-3-Maßnahmen und Verankerungs-Vorschläge aus Phase 4 — keine neuen
   Befunde.
3. **Beispielantwort** am Ende („Z1 Z3 go, Z4 Liste").

Regel 4 bleibt. Nichts zu entscheiden ⇒ Liste entfällt, der erste Satz bleibt.

## Anti-Patterns
Jedes Anti-Pattern steht oben als Regel am Ort der Handlung; der vollständige Katalog zur
Gegenprobe eines Reports: → LEHREN#v2b-anti-patterns.

## Abschluss-Checkliste (muss alles grün oder begründet n/a sein)

| # | Check | Status |
|---|-------|--------|
| 1 | `gate_wirkung.py` als ERSTER Schritt gelaufen (Phase 0.0) | ☐ |
| 2 | Jedes `RUECKFAELLIG`-Gate mit Ursache + einer der vier Konsequenzen behandelt (0.0) | ☐ |
| 3 | Footprint, Befund-Dichte, Agenten-Budget genannt; Reduktion begründet (0.1) | ☐ |
| 4 | Collect nach `git fetch` **aus dem Ref** gelesen, nicht aus dem Tree (Phase 1) | ☐ |
| 5 | Session-Grenze über Branch/PR gezogen, nicht über das Datum (Phase 1) | ☐ |
| 6 | Find je Dimension in frischem Kontext; Finder-Mandat im Prompt (Phase 2) | ☐ |
| 7 | Finder-Widersprüche als Skeptiker-Task aufgelöst, nicht inline (Phase 2.5) | ☐ |
| 8 | Verify binär; Skeptiker nur auf Bewertungsbefunde (Phase 3) | ☐ |
| 9 | **Widerlegungsbahn gelaufen (T4, frischer Kontext), `widerlegung:` gesetzt (3b)** | ☐ |
| 10 | Soll-Ablauf gekoppelt: so viele Soll-Schritte wie Überlebende (Phase 3.5) | ☐ |
| 11 | Report vollständig: Frontmatter + §1–§8, eingefrorene Spalten, §8 gefüllt (Phase 4) | ☐ |
| 12 | `retro_kpis.py` gelaufen; jeder Slug ≥2 als GATE-PFLICHT geführt (Punkt 5) | ☐ |
| 13 | Rückfall-Konsequenz eingetragen: `revised` + `revision_note`, kein zweites Gate (5a) | ☐ |
| 14 | `over_ask`/`over_act` inkl. Klassen-Slugs im Frontmatter geführt (Punkt 5b) | ☐ |
| 15 | **Streichbahn: ≥1 Kandidat mit Beleg ODER „keiner, weil …" (Phase 7)** | ☐ |
| 16 | Report unter `docs/retros/…-<repo>-<id>.md` committet, Pfad nicht überschrieben | ☐ |
| 17 | Self-Review durch separaten Meta-Agenten auf den Report; `lean` begründet n/a (Phase 5) | ☐ |
| 18 | Extern-Handoff geschrieben oder begründet n/a (Phase 6) | ☐ |
| 19 | **Vierklang vorhanden: getan · angenommen · nicht verifizierbar · offen geblieben (Regel 5)** | ☐ |
| 20 | `retro_report_check.py` über den Report gelaufen, Exit 0 (Phase 8) | ☐ |
| 21 | **Finder (2) und Skeptiker (3) je in EINER Nachricht gestartet, Collect-Befehle gebündelt (Phase 1/2/3)** | ☐ |
| 22 | Übergabe-Antwort: erster Satz „schließbar ja/nein", Maßnahmen mit Empfehlung + Link, Beispielantwort — oder nichts zu entscheiden (Phase 9) | ☐ |

> **Pflicht-Selbstcheck (nicht überspringen):** zähle die als PFLICHT/NEU markierten
> `##`/`###`-Überschriften oben gegen diese Tabelle — jede neue Pflicht-Phase braucht hier eine
> Zeile, sonst ist sie strukturell überspringbar. (Warum: LEHREN § Abschluss-Checkliste.)

## Changelog

Letzte drei Einträge; Wortlaut und Historie: LEHREN § Changelog-Historie.

- 2026-10-06: **Kontext-Diät V2b** (platform#3785): Herleitungen wörtlich nach LEHREN, keine
  Phase, Pflicht, Checklisten-Zeile oder Frontmatter-Feld gestrichen.
- 2026-10-05: **Phase 9 Abschluss-Maßnahmen (PFLICHT) + Checklisten-Zeile 22** (platform#3716).
- 2026-09-22: **Nebenläufig starten statt nacheinander warten** (platform#3373), Zeile 21.
