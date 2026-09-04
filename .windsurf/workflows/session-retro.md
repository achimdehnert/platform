---
description: Geerdete, adversariale Session-Retrospektive — sammelt git/gh/CI als Ground Truth, urteilt in frischem Kontext (Richter≠Angeklagter), falsifiziert jeden Befund, schlägt kopierfertige Verankerung + Scorecard vor. Schreibt Report nach platform/docs/retros/ (git, KONZ-010).
mode: write
---

# /session-retro — Geerdeter, adversarialer Session-Review

> **Zweck:** Eine Arbeitssession schonungslos reviewen, mit gelösten Konstruktionsfehlern des
> „Paste-Prompt-Retros": Angeklagter≠Richter, Artefakt-Erdung statt Erinnerung, geschlossener
> Lessons-Loop, Falsifikation der eigenen Befunde.
> **Wann:** nach größeren Umbau-/Architektur-Sessions; am Sitzungsende.
> **Wann NICHT:** Trivial-Edits → höchstens `lean`.
> **Das *Warum* jeder Regel** (Realfälle, Messungen, Changelog-Historie): `LEHREN` =
> `docs/governance/session-skills-lehren/retro.md`. Hier steht nur die Anweisung.

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
   (Dimensionen, Artefakte, Zeiträume) — sonst ist „nichts gefunden" nicht von „nicht hingesehen"
   zu unterscheiden. Kein Zwang, etwas zu finden: verlangt ist die *Abdeckungsauskunft*. Jeder
   Report endet auf **getan · angenommen · nicht verifizierbar · offen geblieben**.

## Phase 0 — Right-Sizing (Footprint **und** erwartete Befund-Dichte)

### 0.0 Wirkungsbilanz lesen — ERSTER Schritt, vor allem anderen (PFLICHT — NEU 2026-09-02, platform#2690 K4)

```bash
python3 tools/gate_wirkung.py
```

**Jedes `RUECKFAELLIG`-Gate wird behandelt, BEVOR ein neuer Befund aufgemacht wird.** Eine Zeile
je Gate: `Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz`.

- **Ursache am Ausgang** — das Gate feuert, niemand handelt danach (Melder ohne Leser, Advisory
  ohne Frist) ⇒ **Modus herabstufen** oder **Sunset** (`declined` mit Grund). Ein Melder, der
  nichts auslöst, wird nicht lauter gemacht.
- **Ursache an der Quelle** — das Gate sieht den Fall nicht (falsches Muster/Pfad, zu spät) ⇒
  **nachschärfen** oder **Drill ergänzen**, wenn der namensgebende Fall ungedrillt ist
  (`gate_namensdeckung.py`).

Zulässig sind genau diese vier Konsequenzen; „im Report erwähnt" ist keine. Umgesetzt wird in
Phase 4 (5a) — hier wird **entschieden**, damit die Befund-Suche weiß, was schon als Rückfall
verbucht ist und nicht ein zweites Mal als neuer Befund aufgemacht wird. **Ehrlichkeits-Sperre:**
ein Gate mit `zu-frueh`/`unerprobt` ist nicht wirksam, sondern ungeprüft — kein berichtbarer
Erfolg. (Warum zuerst: Lehren-Doku § Phase 0.0.)

### 0.1 Footprint + Befund-Dichte
Footprint messen (PRs / Repos / Prod-Schritte / Migrationen / ADRs) **und** Befund-Dichte
schätzen: war die Session **reversibel + transparent + freigegeben**, sind harte Survivors
strukturell selten → kleiner skalieren. Stufe + **hartes Agenten-Budget**:

| Stufe | Trigger | Agenten-Budget |
|---|---|---|
| **lean** | ≤2 PRs, 1 Repo, kein Prod/Migration/ADR | **0 Subagenten**, 1 Inline-Pass, 2 Dimensionen |
| **full** | Standard | Collector + 3 Finder + Skeptiker **je Dimension** + 3b — ≤6 |
| **deep** | ≥3 Repos ODER Prod ODER Migration ODER Verdacht auf vertuschte Fehler | volle Pipeline + 3b + Phase-5-Meta; Skeptiker ≤ Anzahl Dimensionen |

Kein Multi-Agent unter `lean`. Falsifikation **nie** 1 Agent pro Befund — gebündelt je Dimension.

**Skeptiker-Auswahl: nur Bewertungsbefunde (GEMESSEN 2026-07-31).** Das Budget bezahlt den
**fremden Kontext**, nicht die Zweitausführung eines Befehls:

| Klasse | Beleg ist … | Skeptiker? |
|---|---|---|
| **kommandobelegt** | reproduzierbares Kommandoergebnis (`grep -c`, Datei-Existenz, CI-Status, Textvergleich) | **nein** — liefert dieselbe Zahl |
| **Bewertungsbefund** | Urteil über eigene Entscheidungen („vermeidbar", „zu spät", „falsch kalibriert") | **ja** — nur hier wirkt Richter≠Angeklagter |

**Skeptiker-Auftrag neutral formulieren** („widerlege, wenn du kannst"), nie „prüfe, ob ich zu
milde war" — die Fehlerrichtung ist nicht vorhersagbar. **Kosten (gemessen): ~55k Tokens je eng
geführtem Skeptiker** — bei einer Budget-Freigabe diese Zahl nennen, nicht schätzen.
**Untersagt die Umgebung Subagenten:** inline finden, nach obiger Tabelle sortieren, die
Bewertungsbefunde mit ihrer Zahl zur Freigabe vorlegen — statt ohne Falsifikation zu fahren oder
an der Budgetfrage zu scheitern; der Regel-1-Bruch bleibt in §8 als Restlücke.

**Trigger-Konflikt (`deep` „Prod-Schritt" vs. Dichte-Downscale):** beim Rule-B-Level (`deep`)
starten; **eine** Stufe runter (→ `full`) nur wenn **alle drei** zutreffen — (a) Prod-Schritt
explizit freigegeben (Artefakt-Beleg: PR-Body-Warnung oder `AskUserQuestion`), (b) voll
rollback-fähig (**keine** DB-Migration), (c) findings_total-Schätzung ≤10. Bei Prod-Schritt
**nie** `lean`. Reduktion + die drei Begründungen als `footprint_reduction_reason` ins Frontmatter.

**Increment-Retro (Anchor am selben Tag):** (1) `session_id`-Suffix `-incr`; (2) **nur die neuen
Artefakte** sind in-scope, Vor-Retro NICHT re-litigieren; (3) Parent-Retro-Slugs zählen als
Vorkommen-1 → derselbe Slug im Increment ist Vorkommen-2 ⇒ **Gate-Pflicht, auch same-day**;
(4) Minimum mit Prod-Schritt: `full`, nie `lean`.

## Modell-Routing je Phase (Kosten-Disziplin)
Richter≠Angeklagter kommt vom **frischen Kontext**, nicht vom teuren Opus → Subagenten auf dem
**billigsten Modell, das die Phase trägt**:

| Phase | Wer / Modell |
|---|---|
| 0 · 3.5 · 4 · 7 | **du** (inline) — Zusammenführen, kein Selbst-Urteil |
| 1 Collect | Subagent **haiku** — reines Sammeln |
| 2 Find · 3 Verify · 5 Meta | Subagent **sonnet** — frischer Kontext, ~5× billiger als Opus (`session-routing.md`) |
| **3b Widerlegungsbahn** | Subagent **Tier 4 (Opus)**, frischer Kontext — Owner-Entscheid 2026-09-02 ([#2374](https://github.com/achimdehnert/platform/issues/2374#issuecomment-5510996006)) |
| 6 Extern-Handoff | **fremder Anbieter** (Mensch holt ein) — fremde Blindflecken |

**Anti-Pattern:** Find/Verify durch **„du"** = Self-Review = Bruch von Regel 1. „Billiger" heißt
**Sonnet-Subagent**, nicht **kein** Subagent. Opus nur in 3b oder bei Nuance-Fail.

## Phase 1 — Collect (Ground Truth, frischer Ermittler)
**Frisch-Checkout-Pflicht (GATE-PFLICHTIG, 8. Vorkommen):** erster Befehl gegen jedes Scope-Repo
ist `git fetch origin <default-branch>`, **bevor** irgendein `git log`/`status`/`diff` den
lokalen Checkout liest — auch bei `lean`, auch inline ohne Subagent.

> **Nach `git fetch`: aus dem Ref lesen** (`git show origin/<default-branch>:<pfad>`), nie die
> Working-Tree-Datei greppen. Fetch bewegt den Ref, nicht den Tree.

**Session-Grenze = die Konversation, NICHT der Kalendertag.** Ein Datumsfilter sammelt an einem
geteilten Arbeitstag fremde Sitzungen ein. Scope über **Branch-Präfixe/PR-Nummern der eigenen
Sitzung** ziehen (bzw. den Transkript-Pfad); das Datum ist nur Vorfilter.

Ein Subagent sammelt **ausschließlich aus Artefakten** (kein Self-Report):
- `gh pr list --repo <owner>/<repo> --state all --search "updated:>=<datum>"` (+ `gh issue list`)
  — danach auf die Sitzung **eingrenzen**, nicht alles übernehmen
- `git -C ~/github/<repo> fetch origin <default-branch>` **zuerst**, dann
  `log --oneline --since='<YYYY-MM-DD> 00:00'` gegen `origin/<default-branch>` + `diff --stat`
- CI/main-Status der Repos (`gh run list --branch main`)

⚠️ **`--since` immer MIT Uhrzeit** (`'<datum> 00:00'`) — sonst **null Treffer** trotz
existierender Commits, und die stille Null wird als Faktum gemeldet.

**Aktiv nach red_flags suchen, die ein Self-Review übersieht:** OPEN-PR überholt von späterem
MERGED-PR zum selben Issue · mehrere PRs „Closes" dasselbe Issue · rote Required-Gates auf
offenen PRs · Migrations-Nummern-Kollision · Issue offen trotz gemergtem Fix.

**Infra-Topologie-Sonde (Pflicht, wenn die Session CI/Deploy/Runner/Hosts berührte):** SoT
`platform/infra/hosts.yaml` gegen die Realität abgleichen, nicht raten —
`python3 platform/infra/scripts/hosts_audit.py --check all --workflows <repo>/.github/workflows`,
plus `gh api repos/<owner>/<repo>/actions/runners` und `runs-on:` gegen lebende Runner: ein
Workflow auf einem Label ohne Online-Runner hängt unbegrenzt und blockiert Merges. Drift →
Längsschnitt-Gate-Kandidat, kein Einzelfix.

> **Repos verbindlich halten:** genannte Repos sind in-scope — nie als „separater Workstream"
> wegklassifizieren. Ein gegebener Transkript-Pfad erdet die Session-Grenze.

## Phase 2 — Find (frischer Kontext, je Dimension)
Je Dimension ein **eigener** Subagent (kennt die Session-Erzählung nicht), geerdet im Footprint:
- **Soll-Ist & Scope** — Ziel vs. Geliefertes; Scope Creep; still Weggelassenes; Offenes, das das Ziel verfehlt.
- **Entscheidungen & Fehler** — tragfähig vs. fragwürdig; Anti-Patterns; Konventionsverstöße; Tech-Debt; verfrühte Festlegungen.
- **Prozess & Kollaboration** — Rework, Duplikat-/dangling-PRs, rote Gates, unklare Steuerung, fehlende frühe Checks.

Je Befund: Schweregrad (kritisch/hoch/mittel/niedrig) + Root Cause (5-Why) + Kategorie
(Wissenslücke / Prozesslücke / Kommunikation / verfrühte Festlegung / fehlende Validierung / Werkzeug).

**Finder-Mandat (hart, in JEDEN Finder-/Skeptiker-Prompt):** „Du lieferst NUR Befunde als Text
zurück — du erstellst KEINE Dateien, Branches, Commits, PRs oder Reports und fährst keine eigene
Retro-Pipeline." (Realfall: Lehren-Doku § Phase 2.)

## Phase 2.5 — Finder-Konflikt-Erkennung (in-context, 0 Agenten)
Vor Phase 3: Finder-Outputs auf **zwei Finder mit widersprüchlichen Fakt-Behauptungen über
dasselbe Artefakt** scannen, jeden Widerspruch als Paar markieren. **NICHT in Phase 4 auflösen** —
das wäre verstecktes Verify aus dem Haupt-Kontext (Regel-1-Bruch). Stattdessen als **zusätzlichen
Skeptiker-Task** routen: der Phase-3-Skeptiker zieht das umstrittene Artefakt **unabhängig aus
`origin/main`** und entscheidet binär. Nur die verifizierte Version geht in den Report — mit
eigener Befund-Nummer + Kategorie/Severity (keine nummernlosen Zeilen).

## Phase 3 — Verify (Falsifikation)
Skeptiker-Subagent **je Dimension** (nicht je Befund — Budget, 0.1). **Binär: SURVIVES oder
REFUTED** — kein „weakened"/„teilweise" (das ist Verhandlung; mildernde Umstände gehören in die
Beleg-Spalte, nicht in ein drittes Verdikt).

**Vorher sortieren:** kommandobelegte Befunde überspringen, Skeptiker nur auf Bewertungsbefunde
(Klassentabelle 0.1). Bei ≤2 Bewertungsbefunden ist ein Skeptiker **je Befund** günstiger und
schärfer; das Budget-Argument greift erst ab etwa vier.

**Eiserne Verify-Regel:** Der Skeptiker bekommt **nur die Behauptung, NICHT den Finder-Befehl** —
und muss den Beleg **unabhängig neu ziehen**, breiter/rekursiv (`find -name` statt `ls <dir>`,
`grep -r` statt `grep <datei>`). Wiederholt er den Finder-Glob, wandert dessen False-Positive
ungeprüft durch.

**Belegpflicht gilt AUCH für Längsschnitt-Behauptungen:** „wiederholt Drift-Memory X" ist ein
Befund → X muss per `ls`/`grep` existieren, sonst REFUTED.

**Frisch-Checkout-Pflicht (GATE-PFLICHTIG, 3. Vorkommen):** jeder Skeptiker-Prompt beginnt
zwingend mit `git fetch origin <default-branch>` und prüft gegen `origin/<default-branch>`.

> **Nach `git fetch`: aus dem Ref lesen** (`git show origin/<default-branch>:<pfad>`), nie die
> Working-Tree-Datei greppen. Fetch bewegt den Ref, nicht den Tree.

Nur SURVIVES gehen in den Report.

## Phase 3b — Widerlegungsbahn (PFLICHT ab Footprint `full`; NEU 2026-09-02, platform#2690 K5)
Phase 3 widerlegt **einzelne Befunde**, Phase 5 prüft die **Form des Reports**. Keine der beiden
widerlegt **das Urteil dieser Retro** — genau das ist der Auftrag hier.

**Ein** Subagent, **Tier 4 (Opus), frischer Kontext** (Owner-Entscheid 2026-09-02,
[#2374](https://github.com/achimdehnert/platform/issues/2374#issuecomment-5510996006)), mit
gh/git-Zugriff. Er sieht **Report-Entwurf + Footprint + Artefaktliste aus Phase 1** — NICHT die
Session-Erzählung, NICHT die Finder-Prompts. Auftrag: *„Widerlege das Urteil dieser Retro."*
Drei Fragen, jede mit Artefakt-Beleg:

1. Ist ein **SURVIVES** falsch stehen geblieben? (Gegenbeleg aus `origin/<default-branch>`)
2. Ist ein **REFUTED** zu früh verworfen worden?
3. Fehlt eine ganze **Dimension**? Nenne EINEN Befund, den keiner der Finder hatte.

Ergebnis je Befund: **widerlegt / hält / unentscheidbar** mit Beleg — „unentscheidbar" nur mit dem
billigsten fehlenden Check. Verdikt je Punkt `BESTAETIGT`/`GEKIPPT`/`NEU`. Ausgabe als Abschnitt
`## Widerlegung` **und** als Frontmatter-Feld `widerlegung: "<n> gekippt, <m> neu"`. Lauf ohne
Fund ⇒ Abdeckungsauskunft (Eiserne Regel 5). Bei `lean` begründet n/a. Kosten: ein Agent
obendrauf (`full` ≤7).

## Phase 3.5 — Soll-Ablauf (konstruktiv, an Überlebende gekoppelt)
Diagnose allein lehrt „war schlecht", nicht „so geht's richtig". Pro **überlebendem** Befund
**genau ein** artefakt-verankerter Alternativschritt, Format **Ist → Soll → eliminiert #**:

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| … was real geschah | … der konkrete bessere Schritt/Checkpoint | #<Befund> |

**Invariante (hart):** `|Soll-Schritte| == |überlebende Befunde|`. Kein Soll-Schritt ohne
Befund-Referenz (verhindert Plattitüden), kein Überlebender ohne Soll-Schritt (verhindert reine
Anklage). Die Top-3-Maßnahmen (Phase 4) werden daraus **abgeleitet**, nicht frei erfunden.

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
- **3. Scorecard** — die 6 Frontmatter-Dimensionen, **ganzzahlig 1–5**, je **an einem Befund
  verankert**. Rubrik: `1`=Kernziel verfehlt · `2`=verfehlt mit Rework · `3`=teilweise, Abweichung
  begründet · `4`=erreicht, kleine Mängel · `5`=vorbildlich.
- **4. Soll-Ablauf** (aus 3.5, Ist→Soll→eliminiert-#).
- **5. Längsschnitt — der eigentliche Hebel: PFLICHT** `python3 tools/retro_kpis.py` (zählt
  `recurring_findings`-Slugs über ALLE `docs/retros/session-retro-*.md`). Slug mit Zähler **≥2 ⇒
  GATE-PFLICHT** (Hook/CI/Skill-Edit), nicht der N-te Notizzettel. Zusätzlich gegen
  `<auto-memory>/MEMORY.md` abgleichen — Existenz per `grep` prüfen, nicht erinnern.
- **5a. Rückfall-Prüfung — hat ein GEBAUTES Gate versagt? (PFLICHT)** `python3 tools/gate_wirkung.py`
  trennt Vorkommen **vor** dem Bau eines Gates von denen **danach**. **Regel:** Kehrt ein Slug
  wieder, für den bereits ein Gate in `docs/governance/gate-registry.json` steht, ist der Befund
  **nicht** „Slug X zum N-ten Mal", sondern **„Gate X ist rückfällig"** — eigene Klasse, eigener
  Slug (`gate-<name>-wirkungslos`), drei zulässige Antworten: **ausweiten** (sieht die Familie
  nicht) · **umbauen** (zu spät/falscher Pfad) · **herabstufen** (begründet in `declined`). Ein
  vierter Weg („nochmal aufschreiben") ist **keiner**. **Ein Rückfall ändert das BESTEHENDE Gate,
  nie ein zweites unter neuem Namen (PFLICHT):** derselbe Eintrag bekommt `revised` +
  `revision_note`, bei Ausweitung zusätzlich eine neue `positivkontrolle` (`gate_wirkung.py` liest
  `revised or built`). Die Entscheidung aus 0.0 wird hier eingetragen; der Edit läuft durch
  `tools/gate_verankerung_check.py --neu` (session-ende 0f), sonst ist er ein Kandidat, kein
  Eintrag (#2234). (Warum: Lehren-Doku § Phase 4 Punkt 5a.)
- **5b. Autonomie-Kalibrierung:** zwei KPIs gegen die Artefakte messen und im Frontmatter führen —
  `over_ask` (vorgelegt, obwohl nachweislich **deterministisch/reversibel**) und `over_act`
  (autonom getan, obwohl **Gate**: Prod/Publish/Merge-auto-deploy/3.-Repo/irreversibel). Muster
  **≥2 über Retros** ⇒ die Gate-Liste in `feedback_autonomy_charter` **schärfen**, nicht neu raten.
  **Klassen-Slugs Pflicht (KONZ-025 Art. 2.1a):** Klasse **eng** benennen
  (`pr-merge-nicht-deploy-repo`, nicht `merge`). `retro_kpis.py --nominierung` zählt sie: Klasse ≥2
  ⇒ **NOMINIERT** (Vorschlag im Registry-Format, eine Stufe, als „erweitert meine Macht"
  gekennzeichnet — Ratifikation bleibt Kapitäns-Zug); `over_act` derselben Klasse im Fenster
  **sperrt** sie (Art. 2.2). Ohne Slug ist der Beleg für den Sensor unsichtbar.
- **6. Verankerung:** kopierfertige `memory_candidates` + `adr_candidates` (du schreibst sie NICHT selbst).
- **7. Maßnahmen als Action-Board** (🟢 dein Zug / 🔵 ich sofort / 🟡-⛔ wip / ✅ done; Lean-Spalten
  `# | Item | Repo | PR/Issue/ADR | Status | Next Step`), **aus dem Soll-Ablauf abgeleitet**.
- **8. Nicht verifiziert (Restlücken)** — Pflicht-Sektion: was offen blieb + billigster Check.
- **`## Widerlegung`** (Phase 3b) und **`## Streichbahn`** (Phase 7) als eigene Abschnitte.

**Synthesizer-Grenze:** Phase 4 ist **nur Zusammenführen** — hier **keine** neuen `gh`/`git`-Befehle.
Widerspruch oder ungedecktes Faktum → zurück nach 2.5/3 ODER als Lücke in §8, **nicht** still
selbst-verifizieren. Nur durch Session-Gedächtnis gedeckte Befunde sind **Hypothese**, nicht
SURVIVES mit „Beleg=Session-Log".

**Report-Pfad — durable + kollisionsfrei (KONZ-platform-010):**
`platform/docs/retros/session-retro-<datum>-<repo>-<session-id-kurz>.md`, committet — auch wenn die
reviewte Session ein anderes Repo betraf (der Cross-Repo-Längsschnitt lebt zentral in platform).
`<session-id-kurz>` = letzte ~6 Zeichen. **Existiert der Pfad → NICHT überschreiben**, Suffix
anhängen; der bloße `…-<datum>.md`-Default ist verboten.

## Phase 5 — Self-Review (Meta-Agent, nur OUTPUT-Qualität) — `full`/`deep`
Ein **separater Meta-Agent** prüft AUSSCHLIESSLICH den **Report-Entwurf gegen die Skill-Regeln** —
NIE die Session-Erzählung. Er sieht nur den Report + diese Skill. Checkliste:
- Hat **jeder** Befund (inkl. Längsschnitt-Behauptung) einen per `gh/git` **unabhängig
  nachgeprüften** Beleg?
- Scores ganzzahlig 1–5, je an Befund verankert? (fängt Halbwerte wie `2.5`)
- **Invariante** `|Soll-Schritte| == |überlebende Befunde|` erfüllt?
- Frontmatter schema-valide (inkl. `widerlegung` + `streichkandidaten`)? Pfad kollisionsfrei?
- **Wurde `gate_wirkung.py` gelaufen (0.0 und 5a)?** Falls es ein Gate als `RUECKFAELLIG` meldet,
  das der Report als `recurring_finding` führt: steht dort die Klasse **„Gate rückfällig"** mit
  einer der drei Antworten — oder nur der Slug ein weiteres Mal? Nur der Slug ⇒ **Befund am
  Report**, nicht am Gate.
- `refuted_rate` plausibel? Kommentar **ausschließlich numerisch** als Band-Vergleich
  (`retro_kpis.py`) — er beurteilt **NICHT**, ob einzelne SURVIVES/REFUTED inhaltlich korrekt sind
  (das wäre Session-Urteil; das Kippen ist Phase 3b). Band: dauerhaft **>0,8** → Finder zu lasch;
  **<0,2** → Falsifikation ist Theater. **Nur `phase3_refuted/(findings_total − pre_refuted)`** ist
  die echte Falsifikations-Quote. Auffälligkeit als `## Self-Review`.

**Agenten-Budget:** `full` mit 3b und Meta = ≤7; das `≤5` in 0.1 gilt für die reine
Find/Verify-Pipeline. `deep` zzgl. Phase-6-Extern. (Warum zwei Längsschnitt-Werkzeuge nötig sind:
Lehren-Doku § Phase 5.)

## Phase 6 — Extern-Handoff (optional, nur `deep`)
Anbieter-**fremde** Zweitmeinung (fremde Trainings-Blindflecken, nicht nur frischer Kontext).
Muster wie [`adr-handoff-extern`]. Briefing nach
`~/shared/session-retro-extern-<datum>-<repo>-<sid>.md`: (1) den fertigen Report, (2) die 5
Eisernen Regeln + das Output-Schema dieser Skill, (3) Auftrag: *„**Advocatus Diabolus +
Out-of-the-Box:** finde, was dieser Retro übersehen oder falsch bewertet hat. Du hast **KEIN
Repo-Zugriff** → kritisiere **Methode/Struktur/Blindflecken/Score-Logik/Soll-Ablauf**, behaupte
**keine** Evidenz-Fakten."*

**Harte Grenze:** extern challengt **Methode**, prüft **keine Evidenz** (kein gh/git) — der
Evidenz-Recheck bleibt Phase 3/3b/5. **Loop:** wiederkehrende Methoden-Kritik fließt als
Verbesserung in **diese Skill** (Changelog).

## Phase 7 — Streichbahn (PFLICHT, jeder Footprint; NEU 2026-09-02, platform#2690 K5)
Genau **eine** Frage, am Ende jeder Retro: *„Welche Phase / welcher Melder / welche Skill-Sektion
/ welches Gate gehört WEG?"* Ohne sie wächst der Loop monoton — jede Retro darf anbauen, keine
muss abtragen. Zulässig sind genau **zwei** Antworten:

**(a) ≥1 Streichkandidat MIT Beleg** — genau eine der vier Belegarten:

| Belegart | wie belegt |
|---|---|
| **kein Leser** | der Output landet in keinem Artefakt (`gh`-Suche: 0 oder nur Uralt-Treffer) |
| **kein Effekt** | ein Tool/Gate erzwingt dieselbe Wirkung ohnehin (Registry-Eintrag/`record`-Zeile nennen) |
| **Dublette** | dieselbe Aussage steht in einem anderen Skill/Doc (Fundstelle nennen) |
| **Liegezeit** | Artefakte liegen im Median > 14 d ohne Entscheidung (`gate_deckung.py`, `befund_journal.py --bericht`) |

**(b) „keiner, weil <Satz>"** — mit dem Grund, nicht nur dem Wort.

Ergebnis als `streichkandidaten: [<slug>, …]` (leer erlaubt, dann ist `streich_begruendung:`
Pflicht), als Abschnitt `## Streichbahn` und als Zeile im Action-Board (Phase 4, Punkt 7).
**Ratsche:** ein Kandidat, der zwei Retros hintereinander auftaucht und nicht gestrichen wurde,
ist selbst ein Befund — dieselbe Regel wie GATE-PFLICHT ≥2.

## Anti-Patterns
- ❌ Aus dem eigenen Session-Kontext urteilen (in-context self-review).
- ❌ Befund ohne harten Artefakt-Beleg.
- ❌ Befunde nicht falsifizieren — performative Kritik durchlassen.
- ❌ Memory/ADR/CLAUDE.md selbst schreiben statt nur vorschlagen.
- ❌ Wiederkehrendes Muster als „noch ein Memo" abtun statt als Gate-Kandidat eskalieren.
- ❌ Genannte Repos als „separaten Workstream" aus dem Scope kippen.
- ❌ **Verify wiederholt den Finder-Befehl** statt den Beleg breiter neu zu ziehen.
- ❌ **Drittes Verdikt „weakened/teilweise"** — Falsifikation ist binär.
- ❌ **Längsschnitt-Behauptung ohne Existenz-Check** des Artefakts (Phantom-Referenz).
- ❌ **Soll-Schritt ohne Befund-Referenz** ODER Überlebender ohne Soll-Schritt.
- ❌ **Default-Dateiname `…-<datum>.md`** → Kollision bei Parallel-Sessions.
- ❌ **Halbscores** (2.5) — brechen die Längsschnitt-Vergleichbarkeit.
- ❌ **Multi-Agent für `lean`** / Skeptiker je Befund statt je Dimension ab ~4 Befunden.
- ❌ **Skeptiker auf einen kommandobelegten Befund** — bezahlt wird eine Zweitausführung.
- ❌ **Agenten-Budget schätzen statt beziffern** (~55k je Skeptiker ist gemessen).
- ❌ Meta-Self-Review (Phase 5), der die **Session** statt den **Report** beurteilt.
- ❌ **3b aus dem Haupt-Kontext oder mit Session-Erzählung** — der Angeklagte widerlegt sich selbst.
- ❌ **3b „nichts gefunden" ohne Abdeckungsauskunft** (Eiserne Regel 5).
- ❌ **Phase 7 „keiner" ohne Grund-Satz** oder Kandidat ohne eine der vier Belegarten.
- ❌ Find/Verify durch **„du"** „zum Sparen" — Kosten-Fix ist Sonnet-Subagent, nicht **kein** Subagent.
- ❌ **Opus als Default** — Sonnet trägt Find/Verify/Meta; Opus nur in 3b.
- ❌ Extern-Handoff **Evidenz-Fakten** behaupten lassen — extern hat kein gh/git.
- ❌ **Finder-Widerspruch in Phase 4 per neuem git/gh auflösen** — verstecktes Verify.
- ❌ **Nummernlose Befund-Zeile** — bricht eingefrorene Spalten + `findings_total`.
- ❌ **`recurring_finding` ohne `retro_kpis.py`-Zähler-Check** — Längsschnitt als Dekoration.
- ❌ **`refuted_rate` ohne `pre_refuted`-Trennung** — Finder-Stroh bläht die Quote.
- ❌ **Collect ohne vorheriges `git fetch`** — gilt für JEDEN Collect-Schritt, auch `lean`.
- ❌ **Nach dem Fetch die Working-Tree-Datei greppen** statt aus dem Ref zu lesen.

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

> **Pflicht-Selbstcheck (nicht überspringen):** zähle die als PFLICHT/NEU markierten
> `##`/`###`-Überschriften oben gegen diese Tabelle — jede neue Pflicht-Phase braucht hier eine
> Zeile, sonst ist sie strukturell überspringbar. (Warum: Lehren-Doku § Abschluss-Checkliste.)

## Changelog

Vollständige Historie: `docs/governance/session-skills-lehren/retro.md` § Changelog-Historie.

- 2026-09-02: **Kontext-Diät + zwei neue Bahnen** (platform#2690 K5). Lehren, Realfälle und
  Changelog-Historie wörtlich in die Begleitdoku, je ein Verweis im Skill. **Neu:** Phase 3b
  Widerlegungsbahn (T4, PFLICHT ab `full`) + Phase 7 Streichbahn (PFLICHT, jeder Footprint).
- 2026-09-02: **Phase 0.0 Wirkungsbilanz zuerst + `revised`-Regel in 5a + Abschluss-Checkliste**
  (platform#2690 K4). `gate_wirkung.py` läuft als erster statt vorletzter Schritt (14/33 Gates
  rückfällig); ein Rückfall ändert den bestehenden Eintrag statt ein zweites Gate zu bauen.
- 2026-08-20: **Phase 4 Punkt 5a — Rückfall-Prüfung** (`tools/gate_wirkung.py`) als PFLICHT plus
  Abfrage in der Meta-Agent-Checkliste. Kehrt ein Slug wieder, für den ein Gate registriert ist,
  lautet der Befund **Gate rückfällig** — drei zulässige Antworten statt des Slugs zum N-ten Mal.
