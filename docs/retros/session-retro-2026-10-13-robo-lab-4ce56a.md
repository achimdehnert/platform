---
retro_schema: 1
date: 2026-10-13
repo_scope: [robo-lab]
session_id: 4ce56a
footprint: full
findings_total: 19
findings_survived: 11
refuted_rate: 0.42
phase3_refuted: 6
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [edit-in-worktree-without-read, run-result-not-anchored]
recurring_findings: [edit-in-worktree-without-read, run-result-not-anchored, deferred-item-no-tracking-issue, worktree-midsession-accumulation, claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m, repo-datei-per-bash-statt-edit]
gates_caught: [claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m]
gates_verwandt: []
over_ask_klassen: []
over_act_klassen: []
widerlegung: "0 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede Phase dieser Retro messbar gewirkt hat: Phase 2.5 löste den Rollen-Konflikt (Befund 14), die Skeptiker kippten sechs Bewertungsbefunde (11–16), die Widerlegungsbahn korrigierte zwei Zahlen und fand Befund 19."
---

# Session-Retro 4ce56a — Dosen kartonieren, Fernlabor TTZ, U13-Gerätangabe, Humanoiden-Recherche (robo-lab)

Sitzung `e9977fad-62ad-428d-9d0e-16308c4ce56a`, 2026-10-13, 05:55–09:51 UTC. Sitzungsgrenze:
Branch-Präfix `session/2026-10-13/achim-dehnert/` mit den Slugs `kartonieren`, `fernlabor-ttz`,
`geraet-u13-rollen-ttz`, `recherche-humanoide-industrie`.

**Artefakte:**
[robo-lab#269](https://github.com/achimdehnert/robo-lab/pull/269) (Griff- und Traglastprobe Dosen),
[robo-lab#271](https://github.com/achimdehnert/robo-lab/pull/271) (Konzept Fernlabor TTZ),
[robo-lab#272](https://github.com/achimdehnert/robo-lab/pull/272) (U13 statt Boxing, Rollen nach Fernlabor-Konzept),
[robo-lab#273](https://github.com/achimdehnert/robo-lab/pull/273) (Recherche Humanoide und Hände);
[#261](https://github.com/achimdehnert/robo-lab/pull/261) und [#266](https://github.com/achimdehnert/robo-lab/pull/266)
geschlossen, Inhalt über #272 auf main. Issues [#267](https://github.com/achimdehnert/robo-lab/issues/267) (offen),
[#268](https://github.com/achimdehnert/robo-lab/issues/268) (geschlossen), [#270](https://github.com/achimdehnert/robo-lab/issues/270) (offen).
Außenwirkung: ein Mail-Entwurf im HNU-Postfach an zwei TTZ-Partner (nicht gesendet, Versand durch den Owner) und
ein geteiltes Konzeptdokument ohne Repo-Interna.

**Footprint:** 4 gemergte PRs, 2 geschlossene, 1 Repo, kein Prod, keine Migration, kein ADR, Außenwirkung als
Entwurf → `full`. Agenten: 3 Finder, 2 Skeptiker (einer davon mit dem Konflikt aus 2.5), 1 Widerlegungsbahn (Opus),
1 Meta-Agent = 7.

## Phase 0.0 — Wirkungsbilanz

`gate_wirkung.py` meldete vier Gates `RUECKFAELLIG`. Alle vier hat die platform-Retro desselben Tages
([session-retro-2026-10-13-platform-34ae36.md](session-retro-2026-10-13-platform-34ae36.md) §0.0) bereits entschieden;
hier wird nichts doppelt aufgemacht.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 4 | Quelle | nachschärfen ([platform#2666](https://github.com/achimdehnert/platform/issues/2666)) |
| built-but-never-called | 3 | Quelle | nachschärfen durch Ausweitung des Zuschnitts (Owner „187 go“, entschieden in Retro 34ae36 §0.0) |
| check-ohne-positivkontrolle | 2 | Quelle | Rev 2 ([platform#3722](https://github.com/achimdehnert/platform/issues/3722)) |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | Rev 10 ([platform#3600](https://github.com/achimdehnert/platform/issues/3600)) |

In dieser Sitzung hat `claim-before-cheapest-check` dreimal gefangen (Befund 2) und
`direct-gh-pr-merge-bypasses-sa-m` einmal (Befund 3). Beides sind Belege für die Gates, keine Rückfälle; die Tabellenzeilen tragen dafür den Marker `gates_caught`, sonst zählt `gate_wirkung.py` sie als Rückfall (der Meta-Agent sah im Entwurf 5 statt 4).

## 1. Executive Summary

- Alle sechs Owner-Aufträge sind geliefert. Die Dosenaufgabe endet mit Kriterium und Abbruchkriterium in #267, die Recherche mit vier Endeffektor-Optionen.
- Zwei Bewertungen der Messarbeit („1 kg ohne Positivkontrolle“, „0,5 kg als Dosenaussage“) und drei der Steuerung (#272 ohne Review, Schließen statt Mergen, Merge von #269/#271) hielten der Prüfung nicht stand, ebenso der Rollen-Widerspruch aus Phase 2.5 (Befunde 11–16). Die Messkette mit Kontrollen und Werten aus der Datendatei trägt.
- Was bleibt, sind Lücken in der Weitergabe: Ein Annahmewert erscheint in der Recherche ohne Kennzeichen (Befund 6), ein p95-Wert als Grenze (Befund 9), der 90-mm-Wert ohne Messartefakt (Befund 10) und mit falscher Herkunftsangabe in #267 (Befund 19).
- Zwei Verankerungen fehlen: die Liste „Nicht verifiziert“ der Recherche (Befund 7) und die Außenwirkung (Befund 8).
- 18 der 27 echten Fehlerläufe waren Edits ohne vorheriges Lesen (Befund 1). Das Muster stand schon in 8 früheren Retros und hat kein Gate; daraus folgt Gate-Pflicht.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | 18 von 27 echten Fehlerläufen: Edit-Salven ohne vorheriges Lesen im frischen Worktree | Werkzeug | mittel | SURVIVES (kommandobelegt) | Transkript: 4× 06:19, 4× 06:27, 10× 08:31–08:32, „File has not been read yet“; 4 der 31 gezählten Läufe (07:52) sind nur die Fremdinhalt-Kennzeichnung | edit-in-worktree-without-read (8 Retros, ohne Gate) |
| 2 | Zwei Turns mit Aussagen ohne Tool-Beleg; der Stop-Hook fing sie, dazu fing der Bescheinigungs-Guard einen Kommentar | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | Stop-Hook 06:56:13 und 08:36:37, PreToolUse 08:42:22 (#267-Kommentar) | claim-before-cheapest-check (gates_caught) |
| 3 | Direkter `gh pr merge` statt Merge-Werkzeug | Wissenslücke | niedrig | SURVIVES (kommandobelegt) | Merge-Guard 09:30:22; danach `pr_merge_sa.py` | direct-gh-pr-merge-bypasses-sa-m (gates_caught) |
| 4 | Hausskript ohne vorheriges Lesen der Signatur aufgerufen, Traceback | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Transkript 07:57, Entwurfs-Werkzeug | — |
| 5 | Remote-Branches gemergter PRs und Sitzungs-Worktrees bleiben liegen | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `git ls-remote --heads origin 'session/2026-10-13/*'`: `kartonieren` 29c2c01, `fernlabor-ttz` 235dc44 (#269/#271 gemergt 07:08), dazu `session/2026-10-12/…/inbetriebnahme-handouts` e04d6fe und `…/schulungen-aktualisierung` 94d424e der geschlossenen #261/#266; 4 Sitzungs-Worktrees lokal (alles nach der Retro entfernt, M6) | worktree-midsession-accumulation |
| 6 | Recherche nennt die Dosengröße Ø 100 × 118 mm ohne Annahme-Kennzeichen; die Kernaussage hängt daran | Kommunikation | niedrig | SURVIVES | `docs/recherche-humanoide-industrieaufgaben-2026-10.md:6`, Kernaussage :16; `training/kartonieren/szene.json` D1/D2 `"quelle": "annahme"`; mildernd: Kopf :3 verlinkt #267, dessen Text die Annahme nennt | — |
| 7 | Abschnitt „Nicht verifiziert“ der Recherche (5 Punkte) ohne Issue oder Ledger-Zeile | Prozesslücke | mittel | SURVIVES | Recherche :103 ff.; `gh search issues` leer; #267-Kommentar 08:42 nennt nur die Dex1-1-Backen | deferred-item-no-tracking-issue |
| 8 | Außenwirkung (Mail-Entwurf an TTZ-Partner, geteiltes Konzeptdokument, Termin 15.10.) in keinem durablen Artefakt vermerkt | Prozesslücke | mittel | SURVIVES | #270 mit 0 Kommentaren; Handover-Fragment 06:54 entstand vor Konzept und Mail; `git grep -i Fernlabor` in Handover leer | — |
| 9 | „Gelenklast bei 1 kg ≤ 51 %“ ist das Maximum der p95-Werte, kein Maximum der Last | Kommunikation | niedrig | SURVIVES (kommandobelegt) | Recherche Tabelle 1; `docs/versuche/kartonieren/dose-traglast-20261013-062603.json` (`p95_auslastung_mit_last`) | — |
| 10 | „Dex2/5 umschließt bis ~90 mm“ ohne Messartefakt; abgelegt sind nur 30, 70, 100 mm | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `docs/versuche/kartonieren/` drei Griff-JSONs; `docs/kartonieren-erhebungsbogen.md:20`; Recherche :38,:67 | run-result-not-anchored |
| 11 | „Seilzughand hält 1 kg nicht“ ohne Positivkontrolle bei 1 kg | fehlende Validierung | — | REFUTED (Phase 3) | Kette hält 0,5 kg 19/22 (5× Kontrollmasse), Stufenleiter 22→20→19→0; Katalog :62/:109 „im Twin, am Gerät ungemessen“ | — |
| 12 | Katalog und Recherche stellen 0,5 kg als Dosenaussage dar | Kommunikation | — | REFUTED (Phase 3) | Recherche :38–39 nennt „am 30-mm-Zylinder“; Katalog lässt nur die Geometrie weg | — |
| 13 | #272 ohne Review, Umfang intransparent | Prozesslücke | — | REFUTED (Phase 3) | 31 Dateien, nicht ~80; Bündelung im PR-Text; 0 Reviews ist Repo-Norm (#251–#273); Rest: `<n>`→`‹n›` nicht im PR-Text | — |
| 14 | Betriebsanweisung A11 widerspricht den TTZ-Rollen der Handouts, Änderung nicht verankert (Konflikt aus 2.5) | Kommunikation | — | REFUTED (Phase 3) | A11:64 „von ihm benannte Person“ deckt TTZ-Bediener; Änderung als E2/E3 in KONZ-006:55,172–173 und #270 | — |
| 15 | „merge 261 266“ als Schließen ausgeführt, ohne Vorlage | Kommunikation | — | REFUTED (Phase 3) | Schließkommentar im selben Zug, Inhalt auf main, reversibel; Owner-Weisung „berichten statt vorlegen“ | — |
| 16 | #269/#271 ohne Owner-Wort von der Sitzung gemergt | Prozesslücke | — | REFUTED (Phase 3) | kein Merge-Aufruf der Sitzung 06:50–07:10; mergedBy Owner-Konto 07:08 | — |
| 17 | Issues #267/#270 offen trotz gemergter PRs | Prozesslücke | — | REFUTED (vor Phase 3) | beide PRs nur „Refs“, Arbeit an #267/#270 nicht fertig | — |
| 18 | #268 geschlossen trotz Rest-Treffern „Boxing“ | Prozesslücke | — | REFUTED (vor Phase 3) | Resttreffer sind Historie oder Basis-EDU, im PR-Text unter „Bewusst nicht geändert“ | — |
| 19 | #267 schreibt „~90 mm“ dem Repo-Werkzeug (Grenzsuche `DURCHMESSER=…`) zu; der Wert kam aus einem Scratchpad-Skript | Kommunikation | mittel | SURVIVES (Phase 3b, NEU) | #267-Text :24; Transkript 06:37:43 `umschluss.py` „d=90 mm“; `dose_griff.py` lief nur mit 0,03/0,07/0,10 | run-result-not-anchored |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | alle sechs Aufträge geliefert; Mängel nur in der Weitergabe (Befunde 6, 19) |
| architektur_design | 4 | Messkette mit Kontrollen und Werten aus Datendatei hielt (Befund 11 widerlegt); Grenzwert ohne Artefakt (Befund 10) |
| code_konventionstreue | 4 | Commit-Format und Hardcoding-Regel eingehalten; Befund 4 |
| risiko_debt | 3 | offene Prüfpunkte und Außenwirkung ohne Anker (Befunde 7, 8) |
| prozess_effizienz | 3 | 18 vermeidbare Fehlläufe (Befund 1), Belegdisziplin erst durch Hooks (Befund 2) |
| entscheidungsqualitaet | 4 | alle sechs Entscheidungsbewertungen widerlegt (Befunde 11–16); Statistik-Verlust (Befund 9) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Edit-Salven auf ungelesene Dateien im frischen Worktree, danach Wiederholung | erst ein Read-Batch über alle Zieldateien des Worktrees, dann die Edit-Salve | #1 |
| Kraft- und Grenzaussagen im Turn ohne Tool-Lauf, Stop-Hook fängt | Aussage erst nach dem Lauf im selben Turn, sonst als Hypothese kennzeichnen | #2 |
| `gh pr merge` direkt, Guard blockt | Merge immer über `pr_merge_sa.py` mit Dry-Run | #3 |
| Hausskript aufgerufen, Traceback | vor dem ersten Aufruf `--help` oder Kopf des Skripts lesen | #4 |
| Remote-Branches nach Merge liegen | nach jedem Merge Branch löschen und `repo-session.sh reap` im selben Zug | #5 |
| Annahmewert aus `szene.json` in der Recherche ohne Kennzeichen | Annahmen beim Übernehmen in ein Folgedokument mit Quelle `annahme` und Link auf die Datendatei markieren | #6 |
| Liste „Nicht verifiziert“ nur im Dokument | im selben Zug als Checkliste in #267 kommentieren | #7 |
| Mail-Entwurf und geteiltes Dokument ohne Vermerk | Kommentar auf #270: Datum, Empfänger-Rollen, Anhänge, Termin, Stand „Entwurf, Versand Owner“ | #8 |
| p95 als Grenze übernommen | beim Übertragen die Kennzahl (p95/Max) mitnennen | #9 |
| ~90 mm ohne Lauf-Datei | jeder zitierte Messwert verweist auf eine Ergebnisdatei unter `docs/versuche/`; 80- und 90-mm-Lauf ablegen | #10 |
| Scratchpad-Ergebnis einem Repo-Werkzeug zugeschrieben | Herkunft wörtlich nennen; Scratchpad-Rechnung erst ins Repo-Werkzeug überführen und dort nachlaufen lassen, dann zitieren | #19 |

**Top-3-Maßnahmen** (abgeleitet): (1) Gate für Befund 1 bauen (Gate-Pflicht, 8 Retros ohne Gate).
(2) Weitergabe nachziehen: Befunde 6, 9, 10, 19 in Recherche, Erhebungsbogen und #267 korrigieren, `make dose-griff DURCHMESSER=0.09` ablegen und mit dem Scratchpad-Wert vergleichen.
(3) Verankern: Befunde 7 und 8 als Kommentare auf #267 und #270.

## 5. Längsschnitt

`retro_kpis.py` (2026-10-13, vor diesem Report): 66 Slugs ≥2 mit Gate-Pflicht. Für diese Sitzung relevant:

| Slug | Retros (git grep über `docs/retros/`) | Gate | Konsequenz |
|---|---|---|---|
| edit-in-worktree-without-read | 8 | **keins**, kein declined | Gate-Pflicht → Maßnahme M1 ([platform#3906](https://github.com/achimdehnert/platform/issues/3906)) |
| run-result-not-anchored | 2 (mit diesem Report 3) | **keins**, kein declined | Gate-Pflicht → Maßnahme M8 ([platform#3907](https://github.com/achimdehnert/platform/issues/3907)) |
| deferred-item-no-tracking-issue | 69 | declined (Owner-Entscheidung) | kein neues Gate, Einzelfall nachziehen |
| worktree-midsession-accumulation | 39 | gebaut 2026-10-12, `zu-frueh` | erster Fall nach Bau, beobachten |
| claim-before-cheapest-check | 152 | gebaut, RUECKFAELLIG | gefangen, entschieden in 0.0 |
| direct-gh-pr-merge-bypasses-sa-m | 16 | gebaut | gefangen |

Auto-Memory robo-lab: die Drift-Memory „Abnahme braucht Positiv- UND Negativkontrolle“ existiert
(`MEMORY.md`); der zugehörige Verdacht (Befund 11) ist widerlegt, also kein Rückfall.

### 5a. Rückfall-Prüfung

Kein gebautes Gate ist in dieser Sitzung rückfällig geworden. `claim-before-cheapest-check` und
`direct-gh-pr-merge-bypasses-sa-m` haben gefangen (`gates_caught`). Die vier `RUECKFAELLIG`-Gates aus
0.0 sind durch die platform-Retro 34ae36 entschieden.

### 5b. Autonomie-Kalibrierung

Kein over_ask und kein over_act überlebt. Der Kandidat „Schließen statt Mergen“ (Befund 15) ist widerlegt.
Der Mail-Versand blieb Entwurf, wie die Kontoregel verlangt.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates** (robo-lab):

```markdown
---
name: annahme-bleibt-annahme-im-folgedokument
description: Werte mit quelle annahme aus szene.json tragen das Kennzeichen in jedes Folgedokument mit (Recherche, Katalog, Mail)
metadata:
  type: feedback
---
Ein Wert aus einer Datendatei mit `"quelle": "annahme"` behält sein Kennzeichen, wenn er in ein anderes Dokument wandert.
**Why:** Retro 4ce56a Befund 6: Die Recherche nannte die Dosengröße ohne Kennzeichen, die Kernaussage hing daran.
**How to apply:** Beim Übernehmen eines Messwerts oder Parameters Quelle und Kennzahl (Annahme, p95, Max) mitschreiben und auf die Datei verlinken.
```

**adr_candidates:** keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Gate Edit ohne Read im Worktree | platform | [platform#3906](https://github.com/achimdehnert/platform/issues/3906) | 🟢 | Owner: Gate bauen oder declined |
| M2 | Annahme, p95, 90 mm in Recherche und Erhebungsbogen | robo-lab | #267 | 🔵 | Lotse: PR, Merge per Owner-Wort |
| M3 | 80/90-mm-Lauf mit Repo-Werkzeug | robo-lab | #267 | 🔵 | Lotse: Lauf ablegen, #267 korrigieren |
| M4 | Lückenliste der Recherche verankern | robo-lab | [#267 Kommentar](https://github.com/achimdehnert/robo-lab/issues/267#issuecomment-6143131972) | ✅ | erledigt nach der Retro |
| M5 | Außenwirkung auf #270 vermerken | robo-lab | [#270 Kommentar](https://github.com/achimdehnert/robo-lab/issues/270#issuecomment-6143132322) | ✅ | erledigt nach der Retro |
| M6 | Erledigte Remote-Branches löschen | robo-lab | #269, #271, #261, #266 | ✅ | 4 Branches gelöscht, 4 Worktrees entfernt |
| M7 | Kennzahlen-Werkzeug zählt Fremdinhalt-Kennzeichen | platform | [platform#3908](https://github.com/achimdehnert/platform/issues/3908) | 🟢 | Owner: Fix freigeben |
| M8 | Gate Messwert ohne Ergebnisdatei | platform | [platform#3907](https://github.com/achimdehnert/platform/issues/3907) | 🟢 | Owner: Gate bauen oder declined |

## 8. Nicht verifiziert (Restlücken)

- **getan:** 3 Finder, 2 Skeptiker (einer mit dem Konflikt aus 2.5), Widerlegungsbahn, Meta-Review; 0.0 und 5a mit `gate_wirkung.py`; Längsschnitt mit `retro_kpis.py`; Gate-Registry je Slug per `git ls-tree` auf `origin/main`; die Widerlegungsbahn bestätigte im Transkript, dass die 4 Claude-Docs-Läufe (07:52) nur Fremdinhalt-Kennzeichen sind (M7).
- **angenommen:** dass die Retro-Zählung „Retros je Slug“ per `git grep -l` über `docs/retros/` die Gate-Pflicht richtig wiedergibt; `retro_kpis.py` zählt nur Frontmatter-Slugs (billigster Check: `retro_kpis.py | grep edit-in-worktree`).
- **nicht verifizierbar:** Inhalt des Mail-Entwurfs und des geteilten Dokuments (außerhalb des Repos); Werte der externen Herstellerseiten (die Prüfer hatten keinen Web-Zugriff).
- **offen geblieben:** Handover und Journal in robo-lab seit 2026-10-04 bzw. 2026-10-02 ungepflegt (sitzungsübergreifend, kein Befund dieser Sitzung); ob die Skripte `dose_griff`/`dose_traglast` in der CI laufen (Finder-Hinweis, ungeprüft; billigster Check: `ci_deckung.py`); ob die Edit-Salve um 06:27 nach dem Kontextwechsel lag (Hypothese `edit-after-compaction-without-reread`); E3, Hand am Gerät messen (#267), Lauf 20 zweiter Seed ([#248](https://github.com/achimdehnert/robo-lab/issues/248)).

## Widerlegung

Ein Subagent (Opus, frischer Kontext) mit Report-Entwurf, Footprint und Artefaktliste; `fetch origin main`, gh, Transkript per python.

| Punkt | Urteil | Verdikt | Beleg |
|---|---|---|---|
| #1 Edit ohne Read | hält, Zahl korrigiert | BESTAETIGT | 18 statt 17 Fälle; 4 der 31 Läufe sind Fremdinhalt-Kennzeichen → 18 von 27 |
| #5 Branches | hält, größer | BESTAETIGT | zusätzlich die Branches von #261/#266; 4 Worktrees lokal |
| #6 Annahme Ø 100 | hält, Severity niedrig | BESTAETIGT | #267-Text :18 nennt die Annahme, Recherche :3 verlinkt #267 |
| #9 ≤ 51 % | hält | BESTAETIGT | JSON speichert nur `p95_auslastung_mit_last`, kein Lastmaximum |
| #10 ~90 mm | hält, verschärft | BESTAETIGT | Wert aus Scratchpad-Skript 06:37:43, nicht abgelegt; Kategorie Prozesslücke |
| #2–#4, #7, #8 | halten | BESTAETIGT | Guards 08:42:22, 09:30:22; Traceback 07:57:42; #270 ohne Kommentar |
| REFUTED #11–#18 | keiner zu früh verworfen | BESTAETIGT | #16: Beleg trägt allein das Fehlen eines Merge-Aufrufs, nicht `mergedBy` |
| Scorecard/Summary | interne Zählfehler | korrigiert | „vier von vier (11–15)“ → sechs (11–16); Summary trennt Mess- und Steuerungsbewertungen |
| Herkunftsangabe 90 mm | neu | NEU (#19) | #267-Text :24 vs. Transkript 06:37:43 |

Abdeckung ohne Fund: Personennamen auf main (Repo privat, Namen der Partner kommen nicht vor), Annahme-Kennzeichen in der Recherche, ein 80/90-mm-Artefakt in Tests, Handover und PR-Texten.

## Self-Review

- Eigener Regelverstoß während der Retro: Die Einarbeitung der Widerlegungsbahn lief als Python-Ersetzung über die Shell statt per Edit („Repo-Dateien nur per Edit/Write“). Inhaltlich gleich, jede Ersetzung mit Eindeutigkeits-Assertion; Slug `repo-datei-per-bash-statt-edit` (vorher 1×, Retro 3b46a0).
- `refuted_rate` 0,42 liegt im gesunden Band (`retro_kpis.py`: weder 3× > 0,8 noch < 0,2).
- Meta-Agent (sonnet, nur Report und Skill), 7 Befunde am Report, 6 eingearbeitet:
  - Branch-Liste in Befund 5 („die Köpfe von #261/#266 fehlen auf dem Remote“) **widerlegt**: Das Löschen per `git push origin --delete` meldete für beide `[deleted]`. Sie lagen also auf dem Remote, der Meta-Agent hatte nur nach `session/2026-10-13/*` gesucht.
  - Beleg Befund 10 auf Erhebungsbogen :20 gekürzt.
  - §0.0 built-but-never-called als erlaubte Konsequenz „nachschärfen“ gefasst.
  - Die Zahl 5 statt 4 bei claim-before-cheapest-check kam aus meinem Entwurf: Dessen Tabellenzeilen trugen „(gefangen)“ statt des Markers `gates_caught`, deshalb zählte `gate_wirkung.py` sie als Rückfall. Der Marker ist korrigiert.
  - „6 von 9“ ersetzt durch „sechs (11–16)“; die Summary nennt Befund 14 mit.
  - run-result-not-anchored bekommt M8 mit eigenem Issue.
  - M1 und M7 verlinkt.
- Ein zweiter Edit-ohne-Read-Lauf während dieser Retro: Nach der Kontextverdichtung scheiterten 4 Edits am Report, weil der Read-Zustand zurückgesetzt war. Das stützt Befund 1 und die Hypothese `edit-after-compaction-without-reread` aus §8.

## Streichbahn

Keiner, weil jede Phase dieser Retro messbar gewirkt hat: Phase 2.5 löste den Rollen-Konflikt (Befund 14), die Skeptiker kippten sechs Bewertungsbefunde (11–16), die Widerlegungsbahn korrigierte zwei Zahlen und fand Befund 19.
