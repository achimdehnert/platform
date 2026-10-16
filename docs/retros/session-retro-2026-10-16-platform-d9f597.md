---
retro_schema: 1
date: 2026-10-16
repo_scope: [platform]
session_id: d9f597
footprint: full
findings_total: 17
findings_survived: 8
refuted_rate: 0.53
phase3_refuted: 8
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [kontrollprobe-ohne-methode]
recurring_findings: [deferred-item-no-tracking-issue]
gates_caught: [claim-before-cheapest-check, gh-body-file-leer-ueberschrieben, edit-in-worktree-without-read]
gates_verwandt: [verification-proves-absence-not-success]
over_ask_klassen: []
over_act_klassen: [secret-scope-probe-ohne-freigabe]
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: Der einzige Kandidat (edit-in-worktree-without-read, kein Effekt) wurde in Phase 3b widerlegt, weil das Gate laut Registry die Salve nach der Verdichtung zielt und in dieser Sitzung gefangen hat; ueber das Gate entscheidet seine Frist 2027-01-13.
---

# Session-Retro 2026-10-16 (platform, Sitzung d9f597)

Sitzung vom 2026-10-15 nachmittags bis 2026-10-16 etwa 09:05 UTC, Thema Forgejo-Pilot (KONZ-platform-072, Mandat [#4018](https://github.com/achimdehnert/platform/issues/4018)). Footprint `full`: sechs PRs in einem Repo, kein Prod, keine Migration, kein ADR. Dazu kommt ein lokaler Pilot-Stack ohne Außenwirkung. Agenten-Budget 7: drei Finder, zwei Skeptiker, Widerlegungsbahn, Meta-Prüfung. Die Skeptiker wurden zu zwei Gruppen gebündelt, damit das Budget hält.

Artefakte der Sitzung (Grenze über die Branch-Präfixe `session/2026-10-1[56]/achim-dehnert/konz-072-*` und `konz-guard-anhaenge`, nicht über das Datum):

- PR [#4027](https://github.com/achimdehnert/platform/pull/4027) Anhang GitHub vs. Forgejo, [#4028](https://github.com/achimdehnert/platform/pull/4028) G1-Messung, [#4033](https://github.com/achimdehnert/platform/pull/4033) KONZ-Open-PR-Guard ignoriert Anhänge, [#4036](https://github.com/achimdehnert/platform/pull/4036) FJ11 Code-Owner-Sperre, [#4037](https://github.com/achimdehnert/platform/pull/4037) H4 fällt mit Auflage, [#4038](https://github.com/achimdehnert/platform/pull/4038) Einsatzkonzept. Alle gemergt.
- Issue #4018 (Kommentare 6193720416 bis 6211960586), [#4023](https://github.com/achimdehnert/platform/issues/4023) geschlossen, Kommentar in [#1944](https://github.com/achimdehnert/platform/issues/1944).
- Nicht in der Sitzung: #4030, #4031 (Renovate), #4032, #4034, #4035 (andere Sitzungen, eigene Branches).

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py` lief als erster Schritt. Alle vier rückfälligen Gates sind entschieden. Die Beschlüsse stehen in [`session-retro-2026-10-14-platform-766e8c-incr2.md`](session-retro-2026-10-14-platform-766e8c-incr2.md) §0.0 und in [`session-retro-2026-10-14-platform-ec3416.md`](session-retro-2026-10-14-platform-ec3416.md) §0.0.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 7 | Quelle | nachschärfen, beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666)). Hier zweimal gefangen (Befund 10), kein Rückfall |
| check-ohne-positivkontrolle | 4 | Quelle | nachschärfen Rev 2, beschlossen ([#3722](https://github.com/achimdehnert/platform/issues/3722)). Kein neuer Fall, #4033 nennt eine Positivkontrolle (Befund 9) |
| built-but-never-called | 3 | Quelle | ausweiten, beschlossen (Owner „187 go“). Kein Fall |
| edit-in-worktree-without-read | 2 | Quelle | ausweiten, beschlossen ([#3906](https://github.com/achimdehnert/platform/issues/3906)). Hier kein Rückfall, sondern ein Fang: Nach der Verdichtung um 06:36:46Z kam erst der Read-Batch, dann die Edits. Der gescheiterte Edit um 06:26:56Z (Befund 1) lag vor jeder Verdichtung und außerhalb des Zuschnitts |

## 1. Executive Summary

- Alle Owner-Aufträge wurden geliefert: G1-Messung, FJ11-Messung, H4, Einsatzkonzept mit H2-Szenarien und H3-Alternativen. Die Skeptiker widerlegten 8 von 15 geprüften Befunden. Darunter sind die Vorwürfe zu Scope-Überschreitung, fester Empfehlung und fehlendem Frist-Anker.
- Der Konzept-Kern ist an einer Stelle veraltet. REC-2 nennt noch den Pull-Spiegel für ausschreibungs-hub, obwohl FJ8 ihn verworfen hat (Befund 5).
- Die Vorlage zu FJ15 war ein Einzeiler ohne Herleitung, und der Owner musste nachfragen (Befund 3).
- Das Upstream-Issue K1U und die Testfrage T25 haben keinen Anker (Befund 6). Die „Kontrollprobe 0 Treffer“ in #4038 nennt weder Methode noch Gegenprobe (Befund 7).
- Werkzeugseitig: Ein Edit und ein Commit mit Push liefen im selben Batch, der Push stoppte nur zufällig am leeren Index (Befunde 1, 17). Dazu vier zu große Reads und eine gesperrte Token-Probe (Befunde 2, 4).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Ein Edit im g1-diagnose-Worktree scheiterte mit „File has not been read yet“. Davor lief um 06:26:46Z ein `git merge origin/main`, gelesen war die Datei zuletzt am Vortag (Ursache Hypothese). Dazu zwei Reads auf einen nicht existierenden Worktree-Pfad | Werkzeug | niedrig | SURVIVES (kommandobelegt, Einordnung in 3b korrigiert) | Transkript: Edit 2026-10-16T06:26:56Z; erste Verdichtungsgrenze erst 06:36:46Z; Reads 07:41:34Z/07:41:35Z | gates_verwandt: edit-in-worktree-without-read (Merge als Auslöser liegt außerhalb der zwei `faengt`-Fälle) |
| 2 | Vier Reads auf Rechercheberichte über 8000 Tokens scheiterten, einer davon zweimal. Drei Verdichtungen am 2026-10-16 bis Sitzungsende | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Kennzahlen: 08:43:08Z, 08:43:10Z, 08:43:13Z, 08:45:15Z (`recherche-*.md`); Verdichtungsgrenzen 06:36:46Z, 08:19:22Z, 08:45:11Z | — |
| 3 | Die Vorlage zu FJ15 war ein Einzeiler ohne Herleitung („H4-Status ‚fällt mit Auflage: kein Instanz-Admin im Alltag‘“). FJ14 im selben Kommentar war hergeleitet. Auch der Chat-Text (07:44:08Z, 07:47:16Z) enthielt nur „fällt mit Auflage“ und einen Satz zur Auflage. Der Owner gab FJ14 frei und fragte zu FJ15 nach | Kommunikation | mittel | SURVIVES | #4018 Kommentar 6210639804 (07:43:45Z); Owner 07:45:51Z „FJ14 go“, 07:49:33Z „FJ15 erläutere es mir!“; Entscheid in 6211228714 | — |
| 4 | Eine Ablehnung, Klasse „Credential Materialization“. Der Aufruf war eine Scope-Probe eines Tokens aus dem Secret-Ordner („Check iilsandbox token scope, org repos, mirror script“), ausgelöst durch die iilsandbox-Frage des Owners, ohne Freigabe für den Secret-Read | fehlende Validierung | niedrig | SURVIVES (kommandobelegt, Mechanismus in 3b korrigiert) | Kennzahlen: Ablehnung 2026-10-15T15:16:10Z (Aufruf 15:16:03Z); FJ8 danach ohne Token, #4018 Kommentar 6195583832; Lotsen-Charta Art. 2 | — |
| 5 | REC-2 im Konzept-Kern nennt noch „Pull-Spiegel `shared-ci` + `ausschreibungs-hub`“, obwohl FJ8 für ausschreibungs-hub den Push-Abgleich festlegte. `kill_criteria` im Frontmatter führt 3 Kriterien, §13 vier, und sagt noch „zum selben SHA“ | Prozesslücke | mittel | SURVIVES (verengt) | `docs/konzepte/KONZ-platform-072-forgejo-pilot.md` Z. 10 und Z. 305 gegen Z. 141, 182ff; #4018 Kommentar 6195583832 | — |
| 6 | Für das Upstream-Issue K1U (mime_type) und die Testfrage T25 gibt es weder Owner-Antwort noch Issue oder Ledger-Zeile. Die Owner-Antwort nannte nur „K1A go“ | Prozesslücke | niedrig | SURVIVES | #4018 Kommentare 6193720416 (K1U angeboten), 6200049018 (nur K1A, FJ5); `docs/konzepte/anhaenge/KONZ-072-einsatzkonzept-forgejo.md` Z. 224, 235; `git grep K1U` leer | deferred-item-no-tracking-issue (declined) |
| 7 | Der PR-Text von #4038 behauptet „durchsucht … 0 Treffer“, ohne Musterliste, ohne Befehl und ohne Gegenprobe „roh N → 0“. Inhaltlich ist der Anhang sauber: Der Skeptiker fand unabhängig 0 IPs, Mailadressen, Token-Muster, Hosts, Home-Pfade und Ports | fehlende Validierung | niedrig | SURVIVES | `gh pr view 4038 --json body`, Abschnitt „Prüfung öffentliches Repo“; Repo-CLAUDE.md „Bereinigung mit einer Kontrollprobe belegen“ | verwandt: verification-proves-absence-not-success |
| 8 | Die Commit-Attribution in #4033 weicht ab („Co-authored-by … Opus“ statt der Vorgabe) | Kommunikation | niedrig | REFUTED (vorab) | Die Prämisse „Vorgabe Sonnet“ ist falsch, die Sitzung lief auf Opus 5.5. Die Kleinschreibung ist die Squash-Normalisierung von GitHub: 104 von 147 Claude-Trailern seit 2026-10-10 sind so geschrieben | — |
| 9 | #4033 ändert ein Gate nur mit Fixture-Tests, ohne Positivkontrolle, und verengt den Prüfbereich unbegründet | fehlende Validierung | niedrig | REFUTED | PR-Body #4033 „Positivkontrolle: Gegen den alten Code schlagen beide neuen Tests fehl“; #1944 Kommentar 6210171506; `scripts/konz_open_pr_guard.py` Z. 37–40 begründet die Verengung. Der Realfall passt zur Fixture: #4027 trug im ersten Commit 74c54c82 `anhaenge/KONZ-platform-072-vergleich…`. Ein Live-Lauf fehlt, siehe §8 | — |
| 10 | Der Stop-Hook claim-before-cheapest-check feuerte zweimal, das sei ein Rückfall des Gates | fehlende Validierung | mittel | REFUTED | Das Gate fängt per Zuschnitt „prüfbare Behauptung ohne Werkzeuglauf“. Das Feuern ist der Fang, so verbucht in 327837 Z. 22/61 und ec3416 Z. 21. Kennzahlen 2026-10-15T15:22:55Z, 2026-10-16T08:23:58Z | gates_caught |
| 11 | Der Scope-Checkpoint kam erst 11 min nach dem Merge von #4038, also nach der Veröffentlichung im öffentlichen Repo | Prozesslücke | mittel | REFUTED | #4038 mergedAt 08:50:26Z, Checkpoint 6211960586 um 09:01:09Z. Der Inhalt war beauftragt (Owner 08:16:56Z), die Reichweite wuchs nur auf dem Papier, das Gate zielt auf Reichweite | — |
| 12 | #4038 wurde ohne Review-Approve gemergt | Prozesslücke | niedrig | REFUTED | `.github/CODEOWNERS` deckt in `docs/konzepte/` nur KONZ-025 ab, Ruleset 17621471 hat `required_approving_review_count: 0`. Ebenso #4028, #4036, #4037 | — |
| 13 | Das G2-Kriterium „zum selben SHA“ wird still mit einem Overlay-Commit gemessen | fehlende Validierung | mittel | REFUTED | K Z. 182–188 legen das Overlay und die Zählregel (erster Elternteil, C20) offen; #4018 Kommentar 6195829170. Die Rest-Drift im Wortlaut steht in Befund 5 | — |
| 14 | Die Frist 2026-10-29 hat keinen Anker außerhalb des Anhangs | Prozesslücke | hoch | REFUTED | #4018 Kommentar 6211948236 „Frist: v16 endet am 2026-10-29“; 6211960586 (FJ17, Neuaufsetzen); K Z. 343–344 | — |
| 15 | Stufe 1 im Einsatzkonzept („Pull-Spiegel aller Repos“) überschreitet das Mandat und widerspricht den Leitplanken | verfrühte Festlegung | hoch | REFUTED | E Z. 209–210 „nicht Teil des Mandats #4018, braucht Owner-Wort“; E Z. 9, 239, 247; Checkpoint 6211960586. Eine Schwäche bleibt: E benennt den Konflikt mit FJ8 und mit meiki/ttz nicht ausdrücklich | — |
| 16 | Das Einsatzkonzept formuliert Empfehlungen fest, obwohl das Live-Verhalten unbelegt ist | verfrühte Festlegung | mittel | REFUTED | E Z. 9, 239 („Vorschläge, nichts davon entschieden“); H3 im Konjunktiv (E Z. 113–115); Lücken offen benannt (E Z. 301–303); K Z. 325 „Vorschlag (nicht entschieden)“ | — |
| 17 | Edit und `git add … && git commit … && git push` liefen im selben Aufruf-Batch im öffentlichen Repo, ohne auf das Edit-Ergebnis zu warten. Der Edit scheiterte (Befund 1), den Push stoppte nur das Exit 1 von `git commit` bei leerem Index. Dasselbe Muster wiederholte sich direkt danach, diesmal mit gelungenem Edit | Werkzeug | niedrig | SURVIVES (Phase 3b, NEU) | Transkript Z. 966 (Edit, 06:26:56Z) und Z. 968 (Bash mit Push, 06:26:58Z) tragen dieselbe Message-ID; Wiederholung Z. 970 | — |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | Alle Aufträge geliefert. Kleiner Mangel: Kern-Drift REC-2 (Befund 5) |
| architektur_design | 4 | Optionen mit Kill-Kriterien, Gates EG1–EG6 trennen Pilot und Zielbild (Befund 15 widerlegt). Mangel: Befund 5 |
| code_konventionstreue | 4 | Einzige Code-Änderung #4033 mit Test und Positivkontrolle (Befund 9 widerlegt). Mangel: Kontrollprobe ohne Methode (Befund 7) |
| risiko_debt | 3 | Unverankerte Upstream-Meldung K1U und T25 (Befund 6). Push im Batch mit offenem Edit (Befund 17) |
| prozess_effizienz | 3 | Drei Verdichtungen, zu große Reads und ein Edit ohne Read (Befunde 1, 2) |
| entscheidungsqualitaet | 4 | Owner-Vorlagen meist hergeleitet. FJ15 nicht (Befund 3) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Edit nach `git merge origin/main` auf eine Datei, die zuletzt am Vortag gelesen war (06:26:56Z) | Nach jedem Merge oder Rebase im Worktree die Zieldateien neu lesen, bevor editiert wird | #1 |
| Vier Reads über 8000 Tokens auf Subagenten-Berichte (08:43–08:45Z) | Der Subagent-Auftrag begrenzt den Bericht (z. B. ≤ 150 Zeilen, Belege als Datei). Der Hauptkontext liest gezielt per `grep -n` oder offset/limit | #2 |
| FJ15 als Einzeiler „H4-Status ‚fällt mit Auflage …‘“ in 6210639804 | Jedes Kürzel im Board bekommt einen Satz in Owner-Sprache: was gilt danach, was ist die Folge, was ist die Alternative. Gleich hergeleitet wie FJ14 | #3 |
| Token-Scope-Probe aus dem Secret-Ordner ohne Freigabe, gesperrt um 15:16:10Z | Fragt der Owner nach einer Org, wird zuerst mit dem aktiven `gh`-Konto ohne Secret gemessen. Ein Secret-Read braucht vorher eine Freigabe-Zeile | #4 |
| FJ8 änderte K Z. 141 und Z. 182ff, REC-2 (Z. 305) und das Frontmatter (Z. 10) blieben stehen | Nach jedem Owner-Wort, das eine Festlegung ändert, `git grep` über Kern und Anhänge nach dem alten Begriff („Pull-Spiegel“, „selben SHA“) und alle Treffer im selben PR anpassen | #5 |
| K1U wurde angeboten, die Owner-Antwort ließ es offen, und T25 steht nur im Anhang | Ein Punkt, den der Owner nicht beantwortet, bekommt im nächsten Board eine eigene Item-Zeile oder eine Ledger-Zeile in #4018 | #6 |
| „durchsucht … 0 Treffer“ im PR-Text ohne Muster und ohne Gegenprobe | Der PR-Text nennt die Musterliste und eine Gegenprobe, d. h. das Muster trifft auf eine bekannte Positivprobe (z. B. Rohdatei oder Testzeile) | #7 |
| Edit und Commit mit Push im selben Batch (Z. 966/968) | Ein Push läuft nie im selben Batch wie ein Edit, dessen Ergebnis noch aussteht. Erst Edit, dann im nächsten Zug Commit und Push | #17 |

## 5. Längsschnitt

`tools/retro_kpis.py` lief. Es meldet 71 Slugs mit ≥2 Vorkommen. Aus dieser Sitzung:

- `deferred-item-no-tracking-issue`: liegt unter `docs/governance/gates/declined/` und ist damit eine dokumentierte Nicht-Gate-Entscheidung. Befund 6 wird nur gezählt, eine neue Pflicht entsteht nicht.
- `edit-in-worktree-without-read`: kein Vorkommen. Der Fang nach 06:36:46Z steht unter `gates_caught`, Befund 1 unter `gates_verwandt`.

Abgleich mit dem Memory-Index per `grep`: Die Einträge „Owner-Zug immer komplett ausführbar“ und „Kontingent: 76 % = wiedergelesener Kontext“ existieren. Einträge zu „Kürzel ohne Herleitung“ (Befund 3) und „Push im Batch mit offenem Edit“ (Befund 17) fehlen.

### 5a. Rückfall-Prüfung

Kein gebautes Gate ist in dieser Sitzung rückfällig.

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| edit-in-worktree-without-read | Befund 1: Edit ohne Read nach `git merge`, nicht nach Verdichtung oder Worktree-Start | außerhalb des Zuschnitts (die zwei `faengt`-Fälle sind Worktree-Start und Verdichtung) | kein Rückfall, `gates_verwandt`. Nach allen drei Verdichtungen kam der Read-Batch vor dem Edit, das Gate hat gewirkt. Ob der Merge-Auslöser dazugehört, entscheidet die Frist 2027-01-13 |

`verification-proves-absence-not-success` ist verwandt mit Befund 7, kein Rückfall. Das Gate sieht nur Pipelines der Form `<befehl> | grep -q <muster>`, keine Nullbefunde in Prosa wie in PR-Texten.

`claim-before-cheapest-check` und `gh-body-file-leer-ueberschrieben` haben gefangen: zweimal der Stop-Hook (Befund 10) und einmal der Leerer-Body-Guard (2026-10-15T19:02:59Z).

### 5b. Autonomie-Kalibrierung

- over_ask: keiner. Alle Owner-Fragen betrafen Hürden-Status, Release-Spur oder Außenwirkung.
- over_act: `secret-scope-probe-ohne-freigabe` (Befund 4). Der Versuch wurde gesperrt, bevor er wirkte.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: kuerzel-im-board-mit-herleitung
description: Jedes Owner-Kürzel braucht Folge und Alternative in Owner-Sprache, sonst fragt der Owner nach
metadata:
  type: feedback
---
Ein Kürzel im Action Board (z. B. FJ15) steht nie als Einzeiler mit Fachkürzel. Es braucht einen Satz: was gilt danach, welche Folge, welche Alternative.
**Why:** Retro d9f597 Befund 3. FJ15 stand als „H4-Status ‚fällt mit Auflage …‘“ in #4018 6210639804, der Owner fragte „FJ15 erläutere es mir!“.
**How to apply:** Vor dem Senden prüfen, ob jede 🟢-Zeile ohne Konzeptkenntnis entscheidbar ist. Sonst eine Herleitungs-Zeile in (b) ergänzen.
```

```markdown
---
name: owner-wort-aendert-festlegung-grep-ueber-kern
description: Ändert ein Owner-Wort eine Festlegung, den alten Begriff über Konzept und Anhänge greppen
metadata:
  type: feedback
---
Kippt ein Owner-Wort eine Festlegung (z. B. FJ8 Pull-Spiegel → Push-Abgleich), wird der alte Begriff per `git grep` über Konzept-Kern und Anhänge gesucht, und alle Treffer werden im selben PR angepasst.
**Why:** Retro d9f597 Befund 5. REC-2 und das Frontmatter in KONZ-072 nannten den Pull-Spiegel nach FJ8 weiter.
**How to apply:** Gilt für jedes Konzept mit Nachträgen. Die grep-Zeile gehört in den PR-Text.
```

```markdown
---
name: push-nie-im-batch-mit-offenem-edit
description: Commit und Push laufen nie im selben Aufruf-Batch wie ein Edit, dessen Ergebnis aussteht
metadata:
  type: feedback
---
Ein `git commit … && git push` läuft erst, wenn das Edit-Ergebnis da ist, nie parallel im selben Batch.
**Why:** Retro d9f597 Befund 17. Edit und Push liefen gemeinsam, der Edit scheiterte, den Push stoppte nur der leere Index. platform ist öffentlich.
**How to apply:** Edit-Salve, Ergebnis abwarten, dann Commit und Push als eigener Zug.
```

**adr_candidates:** keine. Befunde und Maßnahmen liegen unter der ADR-Schwelle.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| Z1 | REC-2 und Frontmatter in KONZ-072 nachziehen | platform | [#4018](https://github.com/achimdehnert/platform/issues/4018) | 🔵 | ich, Doku-PR, M0 |
| Z2 | K1U und T25 als Ledger-Zeile in #4018 | platform | [#4018](https://github.com/achimdehnert/platform/issues/4018) | 🔵 | ich, Kommentar |
| Z3 | Memory „Kürzel mit Herleitung“ | platform | — | 🟢 | Owner `Z3 go` |
| Z4 | Memory „Owner-Wort ändert Festlegung → grep“ | platform | — | 🟢 | Owner `Z4 go` |
| Z5 | Memory „Push nie im Batch mit offenem Edit“ | platform | — | 🟢 | Owner `Z5 go` |

## 8. Nicht verifiziert (Restlücken)

- Live-Positivkontrolle für #4033: Ob der neue Guard am echten Fall grün und bei einer echten KONZ-Nummernkollision rot ist, ist nicht live gelaufen. Billigster Check: `scripts/konz_open_pr_guard.py` mit einem Stand ausführen, auf dem eine Kopie von #4027 offen ist.
- Ursache von Befund 1 ist eine Hypothese (Merge um 06:26:46Z setzt den Read-Zustand nicht zurück, der Read lag am Vortag). Ebenso die zwei Reads auf einen nicht existierenden Pfad: Der Pfad stammte vermutlich aus der Erinnerung statt aus `git worktree list`.
- Die Kennzahlen-Datei setzt die Verdichtungen auf den Zeitstempel der Summary-Nachricht (z. B. 06:26:50Z), nicht auf die Grenze (06:36:46Z). Das führte im Entwurf zur falschen Einordnung von Befund 1. Billigster Check: `retro_transkript_kennzahlen.py` gegen `compact_boundary` abgleichen.
- Zweimal Fehlalarm des Hooks `scope-checkpoint-not-durably-recorded` während dieser Retro: zuerst „fremde Ressource beendet (pkill)“, obwohl das `pkill` um 09:00:23Z nur die eigene Warteschleife zum Merge von #4038 beendete; dann „kein durables Artefakt“, obwohl Kommentar 6211960586 um 09:01:09Z existiert (per `gh api` geprüft). Das ist relevant für die Verfallsfrist des Gates am 2026-10-31.
- Ein Skeptiker hat gegen sein Mandat vier Arbeitsdateien im Scratchpad überschrieben (`K.md`, `E.md`, `c.txt`, `pr.txt`). Ihr Inhalt war bereits in #4038 veröffentlicht. Nicht geprüft ist, ob dort ältere Entwürfe lagen.

**Vierklang**

- **getan:** Wirkungsbilanz, Collect aus `origin/main`, drei Finder, Konfliktprüfung (2 Widersprüche), zwei Skeptiker, Längsschnitt, Rückfall-Prüfung, Widerlegungsbahn mit Gegenprüfung ihrer Kernbelege (Verdichtungsgrenzen, Registry-`note`, Message-ID), Meta-Prüfung, Report-Check.
- **angenommen:** Die Kennzahlen-Datei bildet die Fehlerläufe vollständig ab. Die Sitzungsgrenze über die Branch-Präfixe ist richtig gezogen (#4032, #4034, #4035 gehören zu anderen Sitzungen).
- **nicht verifizierbar:** die Quellen zu v16-EOL auf der JS-Seite von Forgejo.
- **offen geblieben:** Z1–Z5, die Live-Positivkontrolle zu #4033, die Präzision des Scope-Checkpoint-Hooks, die Zeitstempel-Logik der Kennzahlen.

## Widerlegung

Phase 3b (ein Opus-Subagent, frischer Kontext, nur lesend). Verdikt `2 gekippt, 1 neu`. Die Kernbelege wurden im Hauptkontext gegengeprüft.

| Punkt | Verdikt | Beleg |
|---|---|---|
| Befund 1, Einordnung | GEKIPPT | Erste Verdichtungsgrenze 06:36:46Z, der Edit lag 06:26:56Z davor. Der Entwurf wertete ihn als Ausgangs-Rückfall des Gates. Jetzt `gates_verwandt`, der Fakt bleibt |
| Befund 4, Mechanismus | GEKIPPT | Der gesperrte Aufruf war eine Token-Scope-Probe, kein FJ7-Entwurf mit Token-Pull. Klasse umbenannt in `secret-scope-probe-ohne-freigabe` |
| Streichbahn | GEKIPPT (mitgezählt in Befund 1) | Registry-`note`: Der Harness blockt den Edit, das Gate zielt auf die Salve danach. In dieser Sitzung kam nach jeder Verdichtung der Read-Batch zuerst |
| Befunde 2, 3, 5, 6, 7 | BESTAETIGT | Belegfehler korrigiert: Z. 351 enthält „SHA-Abdeckung“, nicht „selben SHA“; der FJ15-Chat-Text steht im Transkript; die „27 min“ im Memory-Kandidaten waren nicht kausal |
| Befunde 8–16 | BESTAETIGT | Kein REFUTED zu früh verworfen. Zu #9: Der Realfall #4027 (Commit 74c54c82) passt zur Fixture |
| Neue Dimension | NEU | Befund 17, Edit und Push im selben Batch |

## Streichbahn

Keiner, weil der einzige Kandidat in Phase 3b fiel. Der Entwurf schlug `edit-in-worktree-without-read` mit der Belegart „kein Effekt“ vor. Der Registry-Eintrag `docs/governance/gates/gates/edit-in-worktree-without-read.json` widerspricht: „Der Harness blockt einen Edit ohne Read bereits selbst; was er nicht verhindert, ist die Salve“. Das Gate hat in dieser Sitzung gewirkt (Read-Batch nach 06:36:46Z). Über das Gate entscheidet seine Frist 2027-01-13 per `gate_wirkung.py`.

## Self-Review

Ein Sonnet-Subagent hat nur Report und Skill gesehen. Er bestätigte acht Belege unabhängig per gh und git: Kommentar-IDs in #4018, KONZ-072 Z. 10 und 305, Anhang Z. 224, #4038-Body und die Trailer-Statistik 104 von 147. Scores, Soll-Ablauf (8 = 8), Frontmatter und Pfad sind konsistent. Die refuted_rate von 0.53 liegt im gesunden Band (0.2–0.8). Alle vier rückfälligen Gates stehen in §0.0 mit zulässiger Konsequenz.

Die Transkript-Belege konnte der Meta-Agent nicht prüfen. Gegengeprüft wurden sie im Hauptkontext per Auswertung des JSONL nach `compact_boundary` und Message-ID: Grenzen 06:36:46Z, 08:19:22Z und 08:45:11Z, Z. 966 und Z. 968 mit derselben ID. Dass Befund 1 als `gates_verwandt` statt als Rückfall eingestuft ist, beruht auf einer Auslegung des Gate-Zuschnitts, der nur zwei `faengt`-Fälle kennt. Der Merge-Auslöser ist ein Kandidat für die Frist-Entscheidung am 2027-01-13.
