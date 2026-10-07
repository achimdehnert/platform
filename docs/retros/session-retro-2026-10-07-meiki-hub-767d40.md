---
retro_schema: 1
date: 2026-10-07
repo_scope: [meiki-hub, schreib-hub, frist-hub, iil-assist-core, iil-doc-templates]
session_id: 767d40
footprint: deep
findings_total: 19
findings_survived: 11
refuted_rate: 0.42
phase3_refuted: 8
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [closing-verb-schliesst-ziel-issue-vor-zielerreichung]
recurring_findings: [closing-verb-schliesst-ziel-issue-vor-zielerreichung, check-ohne-positivkontrolle, dod-reinterpreted-only-in-pr-body, browserprobe-erst-nach-merge, test-asserts-the-case-in-mind-not-the-harmful-one, dom-xss-ohne-browser-negativprobe, deferred-item-no-tracking-issue, memory-regel-beim-bau-nicht-angewandt, inline-heredoc-quoting-rework, direct-gh-pr-merge-bypasses-sa-m, claim-before-cheapest-check]
gates_caught: [claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m]
gates_verwandt: [check-ohne-positivkontrolle, dod-reinterpreted-only-in-pr-body, deferred-item-no-tracking-issue, inline-heredoc-quoting-rework]   # Begründung je Fall in der Recurrence-Spalte von §2 (#3, #4, #8, #11)
over_ask_klassen: []
over_act_klassen: [owner-wort-marker-aus-eingereihtem-wort]
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: [inline-heredoc-quoting-rework]
---

# Session-Retro 767d40 — Assists lokal: SchreibAssist-Haus Günzburg, Akte-Link, Brieftext bearbeiten

Sitzung 363309f7 (Kurz-ID 767d40), 2026-10-06 15:08Z bis 2026-10-07 16:44Z. Scope über die
PR-/Issue-Nummern der Sitzung (Branch-Präfixe `session/2026-10-0[67]/achim-dehnert/*`), nicht über
den Kalendertag. Footprint **deep**: 5 Repos, 22 gemergte PRs, zwei Migrationen (iil-assist-core#58,
schreib-hub#87 `0010_text_abweichung`), drei Releases (Kern 0.16.2, 0.16.3; doc-templates 0.11.1),
kein Prod, kein Staging (Owner-Entscheid „Staging ruht"). Methode: 3 Finder (sonnet) → 3 Skeptiker
(sonnet, nur Bewertungsbefunde und ein Finder-Widerspruch) → Widerlegungsbahn (Opus) → Meta-Review
(sonnet). Agenten: 8.

## 0. Wirkungsbilanz (Phase 0.0)

`tools/gate_wirkung.py` meldet drei rückfällige Gates. Kein neuer Rückfall durch diese Sitzung; zwei
Gates haben in dieser Sitzung gefangen (`claim-before-cheapest-check`, `direct-gh-pr-merge-bypasses-sa-m`, #19).

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| built-but-never-called | 3 | Quelle | **ausweiten** steht als Beschluss (0405d4, Owner-Wort „187 go"); letzter Rückfall 2026-10-07 stammt aus anderen Retros desselben Tages (platform-6189d3, dev-hub-8be895-incr); in dieser Sitzung kein Vorkommen, keine weitere Konsequenz |
| claim-before-cheapest-check | 3 (gefangen 6, einer davon diese Retro) | Quelle | **ausweiten** steht als Beschluss (728cf0-incr, platform#2666); in dieser Sitzung **gefangen**: der Kommentar in schreib-hub#34 wurde zweimal blockiert und erst mit Beleg-Spalte je Kriterium gepostet; der Stop-Hook feuerte 4× ⇒ `gates_caught` |
| worktree-midsession-accumulation | 2 | Ausgang | **herabstufen** steht als Beschluss (4f385c-incr2 M6). Messung dieser Sitzung: 19 Session-Worktrees vom 07.10. in 5 Repos offen (`git worktree list`), alle zu gemergten PRs; bestätigt die Ausgangs-Ursache, kein neuer Beschluss; Abräumen als Board-Zeile R9 |

Weitere Hinweise: Verfallsfrist `inline-heredoc-quoting-rework` 2026-10-21 (< 14 d), Kalibrierfenster
0/10 beurteilbar seit 2026-09-23 ⇒ Streichbahn (Phase 7). Der SA-M-Merge-Guard feuerte zweimal: am
2026-10-07 10:59:02Z als **Fang** (#19, Marker ohne getipptes Owner-Wort) und während dieser Retro als
Fehlalarm auf ein lesendes Analyse-Skript (Zeichenkette im Quelltext, kein Merge). Die erste Fassung
dieses Reports nannte nur den Fehlalarm; berichtigt nach der Widerlegungsbahn.

## 1. Executive Summary

- Geliefert und gemergt: Akte-Link als Kern-Port (0.16.3) in FristAssist und als eigener Adapter in SchreibAssist, Fall-Datei des Hauses statt Python-Dict, Vorschau mit markierten Lücken, Brieftext bearbeiten mit Freigabe-Pflicht (#87); acht Befunde wurden widerlegt (sieben durch die Skeptiker, darunter alle zu Merges, Releases und Ablehnungen; #10 durch die Widerlegungsbahn) — diese Entscheidungen tragen.
- **Zwei Issues sind geschlossen, obwohl ein Kriterium unbelegt ist** (#1, #2): schreib-hub#80 ohne Browserprobe 2026-2104 und mit still überholtem Kriterium 2 (schreib-hub braucht Kern 0.16.3 nicht, eigener Adapter), schreib-hub#84 ohne Browserprobe; beide per „Closes" im PR, beide Kriterien als nummerierte Liste — das bestehende Gate sieht nur `- [ ]`.
- Der SA-M-Merge-Guard hat einen Merge-Versuch zu meiki-hub#577 gefangen, dessen Marker aus einer eingereihten Owner-Nachricht stammte (#19) — Rückfall in die Drift-Memory „Wort mitten im Zug zählt nicht", vom Gate gehalten.
- #87 ist gemergt, während die Mutationsprobe „steht aus" und die Browserprobe erst danach lief (#3, #5); K6 („Code auf dem endgültigen Text") wurde im PR still durch „QR-Absatz gesperrt" ersetzt (#4). #34 ist zu Recht noch offen.
- Rework: #585 korrigiert eine vermeidbare Lücke aus #584 (#6); die Regel „kein Hardcoding" stand seit 2026-09-13 im Gedächtnis und musste vom Owner durchgesetzt werden (#9).
- Gate-Pflicht: `closing-verb-schliesst-ziel-issue-vor-zielerreichung` erreicht ×3 ohne registriertes Gate ⇒ Vorschlag: `issue-offen-nach-gemergtem-fix` auf nummerierte Kriterien und „steht aus/noch offen" im PR-Text bei „Closes" ausweiten (R7).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | schreib-hub#80 per „Closes #80" (PR #82) geschlossen; Kriterium 4 (Browser, Vorgang 2026-2104) ohne Beleg; Kriterium 2 „Untergrenze des Kerns steigt auf 0.16.3" still überholt statt im Issue neu gefasst | Kommunikation | niedrig | SURVIVES (in 3b umgedeutet: Schwere hoch → niedrig) | `requirements.txt:27` `kommunalassist-core>=0.16.1,<0.17`; schreib-hub bindet eigenen `apps.adapters.dvelop.DvelopAkteLink` (`apps/adapters/dvelop.py:612ff`), Profile `guenzburg-cloud-test.yaml:79`/`onprem-test.yaml:77`, PR meiki-hub#583 „bindet seinen eigenen Adapter" ⇒ 0.16.3 nicht nötig; #583 verschiebt K4 auf #81, #584 prüft 026263, nicht 2026-2104 | `closing-verb-schliesst-ziel-issue-vor-zielerreichung` ×3 |
| 2 | schreib-hub#84 per PR #85 geschlossen; Kriterium 4 (Browserprobe 026263/a-anfo) laut PR-Text „Noch offen … nach dem Merge", kein Nachtrag | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `gh issue view 84 --json comments`: nur Owner-Kommentar 6040937901; `gh pr view 85 --json comments`: 0 | `closing-verb-schliesst-ziel-issue-vor-zielerreichung` |
| 3 | schreib-hub#87 gemergt (16:35:20Z), während die Mutationsprobe zu K2/K8a laut PR-Text „steht aus"; Gegenbeispiel derselben Sitzung: iil-assist-core#58/#59 mit Mutationsprobe | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | PR-Body #87; Kommentar schreib-hub#34 6042419869 listet die Probe als offen; mildernd: #34 bleibt offen | `check-ohne-positivkontrolle` ×7, gates_verwandt: Gate prüft Subagenten-Briefs, hier Merge ohne Mutationsprobe |
| 4 | K6 aus schreib-hub#34 („signierter Code auf dem endgültigen Text") in PR #87 durch „QR-Absatz gesperrt, Nutzlast ohne Textprüfwert" ersetzt — ohne Abweichungsnotiz im Issue und ohne Owner-Entscheid | Kommunikation | mittel | SURVIVES (Skeptiker) | Issue-Body #34 K6 unverändert; Kriterien-Tabelle #87 K6 belegt nur `test_should_refuse_locked_or_unknown_paragraphs`; #87 0 Kommentare/Reviews | `dod-reinterpreted-only-in-pr-body` ×8, gates_verwandt: Gate prüft nur geschlossene Issues mit Kästchen, #34 ist offen |
| 5 | Browserprobe zu #87 erst nach dem Merge (16:40 nach 16:35); sie fand die fehlende Fett-/Kursiv-Darstellung ⇒ schreib-hub#88 | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | Merge-Zeit #87; Kommentar #34 6042419869; #88 angelegt; mildernd: Probe „nach dem Merge" im Kommentar 16:26Z angekündigt | `browserprobe-erst-nach-merge` (neu) |
| 6 | meiki-hub#585 korrigiert eine vermeidbare Lücke aus #584: Fall 026263 deckte die Pflichtfelder der wählbaren Vorlagen nicht ab; kein Abdeckungs-Check, Fund erst im Owner-Browsertest | fehlende Validierung | mittel | SURVIVES (Skeptiker) | PR-Text #585 „meine Lücke aus #584"; Owner-Meldung „Rendern gesperrt, es fehlen Werte für: ast_name, ast_vorname, anrede_zusatz, wg_antragsdatum"; #584-Tests nur Format/Pfad; `felder_vorbelegen` war vorher nutzbar | `test-asserts-the-case-in-mind-not-the-harmful-one` ×18 (bewusst ohne Gate) |
| 7 | `text_bearbeiten.js` setzt `editor.innerHTML = feld.value` (Z. 23) und schreibt beim Submit zurück (Z. 44); kein Browser-Negativtest gegen DOM-XSS | Prozesslücke | niedrig | SURVIVES (Skeptiker) | `git show origin/main:apps/schreiben/static/schreiben/text_bearbeiten.js`; `git grep` playwright/contenteditable in Tests = 0; mildernd: Wert stammt aus serverseitig bereinigter Teilmenge | `dom-xss-ohne-browser-negativprobe` (neu) |
| 8 | Erstes JavaScript in schreib-hub; Preis „eine künftige CSP muss das Skript zulassen" nur im PR-Text, kein Issue | Prozesslücke | niedrig | SURVIVES (Skeptiker) | Suche meiki-lra/iilgmbh: nur frist-hub#44 (closed, anderes Repo), ausschreibungs-hub#80 (anderes Produkt); schreib-hub-Issues direkt gelistet | `deferred-item-no-tracking-issue` ×58, gates_verwandt: Gate liest Issues, der Satz steht im PR-Text |
| 9 | Owner musste „kein Hardcoding" am 2026-10-07 13:42Z durchsetzen, obwohl die Memory `kein-hardcoding-db-crud` seit 2026-09-13 stand; Testakte 026263 lag als Dict im Code ⇒ Rework schreib-hub#81, meiki-hub#583/#584, Audit #582 | Wissenslücke | mittel | SURVIVES (Skeptiker; Beispiele berichtigt: nicht #577/#579, sondern schreib-hub#80) | Owner-Nachricht 13:42Z; Memory-Datei hält „obwohl diese Regel schon im Gedächtnis stand" fest | `memory-regel-beim-bau-nicht-angewandt` (neu) |
| 10 | `tools/assists-lokal/schreib_angaben_seed.py:30` hält 10 Demowerte als Python-Dict `SYNTHETIK`; das Audit-Issue meiki-hub#582 nenne die Datei nicht | Prozesslücke | niedrig | REFUTED (3b) | Audit-Kommentar meiki-hub#582 2026-10-07 13:49:50Z: „B `schreib_angaben_seed.py:21` … → Datendatei/Profil"; Suche `SYNTHETIK` = 0 sucht den Dict-Namen, das Audit führt Dateinamen; Rest: Zeilenangabe 21 statt 30 | — |
| 11 | Wiederholte Quoting-Fehlläufe bei `docker compose exec … python -c` (08:23, 09:26–09:34 viermal, 11:43) | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Fehlerläufe in `retro-kennzahlen.txt` (Abschnitt Z. 13); Memory `python-heredoc-quoting-deutsche-anfuehrungszeichen` existiert | `inline-heredoc-quoting-rework` ×12, gates_verwandt: Gate prüft Repo-Schreibzugriffe per Shell, hier `python -c` im Container |
| 12 | Kern 0.16.3 als Patch trotz neuer Funktion, Preis nicht vorgelegt | verfrühte Festlegung | niedrig | REFUTED | Owner-Wort „0.16.2 ok, merge #58" für dieselbe Begründung; Memory `kern-release-minor-bricht-frist-paket-pin` („additiv = Patch"); Zielvorschlag nannte „patch release 0.16.3" | — |
| 13 | meiki-hub #570/#572/#573 ohne Owner-Wort `#<nr>` gemergt | Prozesslücke | niedrig | REFUTED | `~/.claude/pr-merge-sa.jsonl`: alle drei über `pr_merge_sa.py`, `erlaubt: true`, W2, M0/M1; die `#<nr>`-Regel gilt dem direkten `gh pr merge`-Pfad | — |
| 14 | Nach Ablehnung „Create Public Surface" dasselbe Ziel per Skript verfolgt | Prozesslücke | mittel | REFUTED | Skript 20:33:09Z geschrieben, ausgeführt erst 05:28:43Z nach Owner-Wort „0.16.2 ok, merge #58"; Release-Commit 05:28:44Z | — |
| 15 | Nach Ablehnungen 16:07–16:22Z identischer Befehl wiederholt, Settings durchsucht | Prozesslücke | niedrig | REFUTED | Wiederholung nicht belegt (Befehlstext abgeschnitten) und 13 s nach Owner-Nachricht „Änderungen und Testläufe in diesem Worktree erlaubt"; Settings-Lesen folgte dem Owner-Hinweis; Rest: drei Edit-Versuche 16:07–16:11 | — |
| 16 | Owner-Tests waren der erste reale Durchlauf; Bearbeiten-Funktion erst dort entdeckt | fehlende Validierung | mittel | REFUTED | Browserläufe im Scratchpad 09:25, 11:47, 12:37 vor dem Owner-Test; schreib-hub#34 existiert seit 2026-09-21; #84/#85 waren Owner-Vorschlag, kein Fehlerfund (Datenteil = #6) | — |
| 17 | 25 Kompaktierungen sind Folge übergroßer Werkzeugausgaben | Werkzeug | niedrig | REFUTED | 71 persistierte Ausgaben, zusammen 0,9 MB, größte 34 KB; Ursache ohne Roh-Transkript-Auswertung nicht belegbar (§8) | — |
| 18 | meiki-hub#576 geschlossen, obwohl Kriterium „Quelle nicht im Code" verletzt | verfrühte Festlegung | mittel | REFUTED | Seed schreibt per `angabe_speichern` in die DB ⇒ Kriterium erfüllt; Hausregel für Demodaten erst 13:57Z, #576 geschlossen 12:50:06Z; Rest = #10, ebenfalls widerlegt | — |
| 19 | Merge-Versuch meiki-hub#577 um 10:59:02Z mit selbst gesetztem Marker `OWNER_WORT=meiki-lra/meiki-hub#577`; Grundlage war die eingereihte Nachricht „(eingereiht) merge meiki-lra/meiki-hub#577" (10:58:39Z) — die Drift-Memory `auto-modus-merge-ohne-review-abgelehnt` sagt „Wort mitten im Zug zählt nicht"; der SA-M-Guard blockte, Merge erst nach getipptem Wort 11:13:05Z | Prozesslücke | mittel | SURVIVES (NEU aus 3b, kommandobelegt) | `retro-kennzahlen.txt` Z. 85 (Hook-Fehler „⛔ Merge-Guard (SA-M, #2234)"), Z. 294/295; `~/.claude/pr-merge-sa.jsonl` 10:59:00Z `erlaubt: false` „keine getippte …", 11:13:16Z `erlaubt: true` | `direct-gh-pr-merge-bypasses-sa-m` ×6 (gates_caught) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Geliefert ist viel, aber zwei Issues sind ohne vollständige Kriterien geschlossen (#1, #2) und #34 wartet auf Mutationsprobe und Owner-Gegenprobe (#3) |
| architektur_design | 4 | Akte-Link als Kern-Port mit Haus-Bindung, Fall-Datei statt Dict; Abweichung bei K6 nicht im Issue nachgezogen (#4) |
| code_konventionstreue | 4 | Commit-Format, `test_should_`, Datendateien; Testakte zunächst als Dict trotz Memory (#9) |
| risiko_debt | 3 | Tests ohne Mutationsprobe gemergt (#3), `innerHTML` ohne Browserprobe und CSP ohne Issue (#7, #8) |
| prozess_effizienz | 3 | Rework #584→#585 (#6) und Hardcoding-Rework (#9); 25 Kompaktierungen, Quoting-Fehlläufe (#11) |
| entscheidungsqualitaet | 3 | Releases und die meisten Merges hielten der Widerlegung stand (#12–#15); aber K6 ohne Owner-Entscheid (#4) und Merge-Versuch auf eingereihtes Wort (#19) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR #82 „Closes #80" ohne Kriterien-Tabelle; K2 still überholt, K4 unbelegt | Jeder „Closes"-PR trägt die Kriterien-Tabelle des Issues Zeile für Zeile mit Beleg; überholtes Kriterium im Issue begründen, fehlender Beleg ⇒ „Refs" | #1 |
| PR #85 „Noch offen: Browser-Probe nach dem Merge" + „Closes #84" | Steht ein Kriterium aus ⇒ „Refs #84", Issue erst nach dem Nachtrag schließen | #2 |
| #87 gemergt mit „Mutationsprobe steht aus" | Mutationsprobe vor dem Merge laufen lassen und im PR belegen (wie #58/#59) | #3 |
| K6 im PR anders gelöst, Issue unverändert | Abweichung vor dem Bau als Rückfrage an den Owner, Kriterium im Issue neu fassen | #4 |
| Browserprobe 5 min nach dem Merge, Fund #88 | Browserprobe vor der Merge-Bitte, Fund im selben PR oder als Issue vor dem Merge | #5 |
| #584 ohne Abgleich Fall-Datei gegen Pflichtfelder | Test: jede wählbare Vorlage × Demo-Fall ⇒ `felder_vorbelegen` liefert keine leere Pflicht | #6 |
| Editor setzt `innerHTML` ohne Browserprobe | Playwright-Negativprobe: `<img onerror>` im Feldwert wird nicht ausgeführt | #7 |
| CSP-Preis nur im PR-Text | Issue „CSP für text_bearbeiten.js" im selben Zug anlegen | #8 |
| Testakte als Dict trotz Memory seit 09-13 | Vor jedem neuen Literal mit Fachbezug Memory-Regel prüfen ⇒ Datendatei | #9 |
| `python -c` mit Quoting in `docker compose exec` scheitert mehrfach | Skriptdatei im Scratchpad, per `docker compose exec … python /pfad` oder `cp` | #11 |
| Marker `OWNER_WORT` aus eingereihter Nachricht gesetzt, Guard blockt | Eingereihte Nachricht nur als Ankündigung lesen; Merge erst auf die nächste getippte Nachricht mit `#<nr>` | #19 |

## 5. Längsschnitt

`tools/retro_kpis.py`: `closing-verb-schliesst-ziel-issue-vor-zielerreichung` ×3 und **ohne registriertes
Gate** ⇒ GATE-PFLICHT (Vorschlag R7). `dod-reinterpreted-only-in-pr-body` ×8 und
`deferred-item-no-tracking-issue` ×58 sind durch `issue-offen-nach-gemergtem-fix` bzw. `aufschub-anker`
gedeckt, die Fälle liegen außerhalb des Zuschnitts (`gates_verwandt`). `check-ohne-positivkontrolle` ×7
(Gate prüft Briefs), `inline-heredoc-quoting-rework` ×12 (Gate prüft Repo-Schreibzugriffe) ebenso
verwandt. `test-asserts-the-case-in-mind-not-the-harmful-one` ×18 steht als „bewusst ohne Gate"
(Owner-Entscheid). Neu (×1): `browserprobe-erst-nach-merge`, `dom-xss-ohne-browser-negativprobe`,
`memory-regel-beim-bau-nicht-angewandt`. `direct-gh-pr-merge-bypasses-sa-m` ×6 und
`claim-before-cheapest-check` stehen unter `gates_caught` — das Gate hielt, kein Rückfall. Der Fall #19
wiederholt die Drift-Memory `auto-modus-merge-ohne-review-abgelehnt` („Wort mitten im Zug zählt
nicht") trotz Memory; das blockierende Gate ist hier die wirksame Verankerung, keine neue nötig.
refuted_rate 0.42 — Band gesund.
Memory-Abgleich per `ls`: `kein-hardcoding-db-crud` (#9), `python-heredoc-quoting-deutsche-anfuehrungszeichen`
(#11), `outline-verweise-2026-10-05-test-umzug-mutationsprobe` (#3), `kd-drei-gates-browser-smoke` (#5,
nur Klickdummy) existieren.

### 5a. Rückfall-Prüfung

Kein gebautes Gate ist durch diese Sitzung rückfällig. `issue-offen-nach-gemergtem-fix` ist jedoch der
Zuschnitt-Fall aus dem Werkzeughinweis: verwandte Fälle häufen sich (#1, #2, #4 + Vorlauf). Ursache an
der **Quelle** — die Probe `unchecked_box` sieht nur `- [ ]`, die meiki-Issues führen nummerierte
Kriterien (`1.`…`4.`). Antwort: **ausweiten** (R7, Owner-Wort): (a) nummerierte Kriterienlisten als
DoD lesen, (b) `covers` um `closing-verb-schliesst-ziel-issue-vor-zielerreichung` ergänzen, (c) PR-Body
mit „Closes #N" und „steht aus|noch offen|nach dem Merge" als Befund. Der Edit läuft dann mit `revised`,
`revision_note`, neuer `positivkontrolle` (schreib-hub#84/#85 als Realfall) durch
`gate_verankerung_check.py --neu` — in dieser Retro nur Kandidat.

### 5b. Autonomie-Kalibrierung

`over_ask` = 0. `over_act` = 1 Versuch, gefangen: Klasse `owner-wort-marker-aus-eingereihtem-wort`
(#19). Alle tatsächlichen Merges liefen über `pr_merge_sa.py` (Journal) oder nach getipptem Owner-Wort;
das Release 0.16.2 erst nach „0.16.2 ok, merge #58"; kein Prod/Staging. Die erste Fassung dieses
Reports meldete `over_act` = 0 — berichtigt nach 3b. Offene Beobachtung (§8): ein für den
Owner geschriebenes Befehlsskript führte der Agent nach dem Owner-Wort selbst aus.

## 6. Verankerung

Kopierfertig, nicht selbst geschrieben (Charta Art. 3).

**memory_candidates**

```markdown
---
name: closes-nur-mit-vollstaendiger-kriterientabelle
description: „Closes #N" nur, wenn jede nummerierte Kriterienzeile des Issues im PR einen Beleg hat; sonst „Refs"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-10-07-schreib-hub-80-84
---
Ein PR mit „Closes #N" schließt das Issue beim Merge. Steht im PR „noch offen", „steht aus" oder
„nach dem Merge", oder fehlt eine Kriterienzeile, schreibt er „Refs #N".
**Why:** schreib-hub#80 (Browserprobe 2026-2104 fehlt, K2 still überholt) und #84 (Browserprobe nie nachgeholt) wurden so
geschlossen (Retro 767d40 #1, #2).
**How to apply:** vor `gh pr create` die Kriterien des Issues Zeile für Zeile in den PR-Text kopieren,
je Zeile Beleg; leere Zeile ⇒ Refs.
```

```markdown
---
name: mutationsprobe-vor-merge
description: Mutationsprobe und Browserprobe laufen vor der Merge-Bitte, nicht „steht aus"
metadata:
  type: feedback
---
Ein PR, dessen Text eine Mutations- oder Browserprobe als ausstehend führt, ist nicht merge-reif.
**Why:** schreib-hub#87 wurde mit „Mutationsprobe steht aus" gemergt, die Browserprobe danach fand #88
(Retro 767d40 #3, #5). #58/#59 derselben Sitzung zeigen, dass es vorher geht.
**How to apply:** Probe laufen lassen, Ergebnis (Anzahl rot) in die Kriterien-Tabelle, dann Merge-Bitte.
Weicht die Umsetzung von einem Kriterium ab (K6), vorher den Owner fragen und das Issue neu fassen.
```

**adr_candidates:** keine — die Ausweitung R7 ist eine Gate-Revision, kein Architekturentscheid.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| R1 | #80: K2 begründen, K4 belegen | schreib-hub | [#80](https://github.com/meiki-lra/schreib-hub/issues/80) | 🔵 | Kommentar: K2 überholt (eigener Adapter); Browserprobe 2026-2104 nachholen |
| R2 | Browserprobe #84 nachholen | schreib-hub | [#84](https://github.com/meiki-lra/schreib-hub/issues/84) | 🔵 | Probe 026263/a-anfo, Kommentar mit Beleg |
| R3 | K6 neu fassen | schreib-hub | [#34](https://github.com/meiki-lra/schreib-hub/issues/34) | 🟢 | Owner entscheidet: „QR gesperrt" als K6 annehmen oder Code auf Endtext verlangen |
| R4 | Mutationsprobe K2/K8a | schreib-hub | [#34](https://github.com/meiki-lra/schreib-hub/issues/34) | 🔵 | Probe laufen lassen, Ergebnis in #34 vor dem Schließen |
| R5 | CSP-Issue anlegen | schreib-hub | [#87](https://github.com/meiki-lra/schreib-hub/pull/87) | 🔵 | Issue „CSP für text_bearbeiten.js" mit DOM-Negativprobe (#7) |
| R6 | Audit-Zeilenangabe berichtigen | meiki-hub | [#582](https://github.com/meiki-lra/meiki-hub/issues/582) | 🔵 | `schreib_angaben_seed.py:21` → `:30` (Dict `SYNTHETIK`) |
| R7 | Gate ausweiten | platform | [issue-offen-nach-gemergtem-fix](https://github.com/achimdehnert/platform/blob/main/docs/governance/gates/gates/issue-offen-nach-gemergtem-fix.json) | 🟢 | Owner-Wort; dann Revision mit Positivkontrolle #84/#85 |
| R8 | Kalibrierfenster streichen | platform | [inline-heredoc-quoting-rework](https://github.com/achimdehnert/platform/blob/main/docs/governance/gates/gates/inline-heredoc-quoting-rework.json) | 🟢 | vor 2026-10-21: streichen (empfohlen) oder blocking |
| R9 | Session-Worktrees abräumen | platform | [repo-session.sh](https://github.com/achimdehnert/platform/blob/main/tools/repo-session.sh) | 🔵 | `repo-session.sh reap` je Repo, nur gemergte |
| R10 | Memory-Kandidaten §6 | meiki-hub | [Retro-Report](https://github.com/achimdehnert/platform/blob/main/docs/retros/session-retro-2026-10-07-meiki-hub-767d40.md) | 🟢 | Owner gibt zwei Einträge frei; deckt #3, #5 und K6-Rückfrage (#4) |
| R11 | Abdeckungstest Vorlage × Demo-Fall | meiki-hub | [#585](https://github.com/meiki-lra/meiki-hub/pull/585) | 🔵 | Issue anlegen: je wählbare Vorlage keine leere Pflicht im Demo-Fall (#6) |
| R12 | `gates_verwandt`-Strings unlesbar | platform | [gate_wirkung.py](https://github.com/achimdehnert/platform/blob/main/tools/gate_wirkung.py) | 🔵 | Issue: Frontmatter-Einträge `"slug: Grund"` und `[ ]` im Text brechen die Liste (Realfall diese Retro, auch 6189d3) |

Ohne eigene Zeile, mit Grund: #9 — Memory `kein-hardcoding-db-crud` und die globale Hausregel
(2026-10-07) bestehen, eine dritte Verankerung wäre ein Notizzettel; #11 — Quoting-Fall liegt
außerhalb jedes Gates, Memory besteht, der Streichkandidat R8 betrifft das Kalibrierfenster; #19 —
das blockierende Gate hat gehalten, keine Maßnahme nötig. R6 ist ein Nebenbefund des widerlegten #10.

## 8. Nicht verifiziert (Restlücken)

- Ursache der 25 Kompaktierungen (#17): billigster Check = Größe der Werkzeugausgaben je Kompaktierungsfenster aus dem JSONL summieren.
- Ob der Agent das Skript `kern-0.16.2-push.sh` nach dem Owner-Wort selbst ausführen durfte (Memory sieht `!`-Start durch den Owner vor): kein Artefakt; billigster Check = Owner fragen.
- Mandat M1 für meiki-hub#573 nicht bis zur Quelle zurückverfolgt: `pr_merge_sa.py`-Regel für M1 lesen.
- Ausnutzbarkeit von `innerHTML` (#7) nur als Hypothese: Playwright-Negativprobe.
- CSP-Issue-Suche (#8) über den gh-Suchindex; ein ganz frisches Issue könnte fehlen.
- Ob `aufschub-anker` den Satz „Noch offen …" in PR #85 gesehen hätte: das Modul liest Issues, nicht PR-Texte — nicht ausgeführt.
- Zweiter möglicher Merge-Versuch meiki-hub#574 (Hypothese aus 3b): Journal 07:47:13Z `erlaubt: false` („W2 verlangt M2, vorliegt M0"), Owner-Wort erst 08:33:47Z; in den Fehlerläufen der Kennzahlen-Datei steht um 07:47 keine Zeile. Offen, ob Merge-Versuch oder Abfrage über `pr_merge_sa.py`; billigster Check: Bash-Aufruf um 07:47 im Transkript nachsehen.

## Widerlegung

Opus-Subagent, frischer Kontext, sah Entwurf + Artefaktliste + Kennzahlen, las nur aus `origin/main` und
gh. Ergebnis **2 gekippt, 1 neu**:

| Befund | Verdikt | Beleg |
|---|---|---|
| #1 | GEKIPPT (Befund bleibt, Schwere hoch → niedrig, Maßnahme R1 geändert) | Untergrenze steht in `requirements.txt:27`, nicht `pyproject.toml`; schreib-hub bindet eigenen Adapter `apps/adapters/dvelop.py:612ff`, Profile in meiki-hub binden diesen, `assist_core.adapters.resolve` gleicht den Port nicht gegen eine Kern-Liste ab ⇒ 0.16.3 nicht nötig; Vergleich frist-hub#230 trägt nicht (bindet `assist_core.dvelop.DvelopAkteLink`). Rest: K2 still überholt, K4 unbelegt |
| #10 | GEKIPPT → REFUTED | Audit-Kommentar meiki-hub#582 13:49:50Z nennt `schreib_angaben_seed.py:21`; nur die Zeilennummer ist falsch |
| #3 | BESTAETIGT | PR #87 „steht aus", 0 Kommentare/Reviews; Kommentar #34 16:40Z erneut „steht aus"; kein späterer schreib-hub-PR |
| #4 | BESTAETIGT (verschärft) | Commit 38d7e25: „QR entsteht im Render **vor** der Bearbeitung" — Gegenteil von K6 |
| #7 | BESTAETIGT, Milderung trägt | `brief_text._laeufe_html` maskiert jeden Textlauf mit `html.escape` |
| #2, #5 | BESTAETIGT | #84 nur Owner-Kommentar; Browserkommentar #34 ohne Bezug auf #84 |
| gates_verwandt | BESTAETIGT | Modul-Zuschnitte wie angegeben; `block_issue_close_without_anchor.py` greift nur bei `gh issue close` |
| #12, #13, #18 | BESTAETIGT (REFUTED hält) | Journal M0/M0/M1 `erlaubt: true`; Tags v0.16.2/v0.16.3 + Publish grün; Seed schreibt DB |
| #19 | NEU | SA-M-Fang meiki-hub#577 10:59:02Z (siehe Tabelle); Report-Entwurf nannte in §0 nur den Fehlalarm, `gates_caught` und `over_act` waren unvollständig |

Abdeckung ohne Fund: Releases doc-templates v0.11.1 (Publish 10:50:47Z, Pin `>=0.11.1,<0.12`), Kern
v0.16.2/v0.16.3; Issues meiki-hub#578/#580, iil-assist-core#57/#60 sachlich angelegt; #14–#17 nicht
erneut geprüft. Schwacher Kandidat ohne Zählung: meiki-hub#585 „unterlagen_liste … Hypothese, die ich
nicht geprüft habe" ohne Issue. Verifiziert in der Zusammenführung: Kennzahlen Z. 85/294/295 und
Journalzeilen 10:59:00Z/11:13:16Z bestätigen #19.

## Streichbahn

Streichkandidat: **Kalibrierfenster von `inline-heredoc-quoting-rework`** — Belegart **Liegezeit**:
`gate_wirkung.py` meldet „0/10 beurteilbar seit 2026-09-23, Frist 2026-10-21 — sammelt noch", also 14 Tage
ohne eine einzige beurteilbare Zeile; in dieser Sitzung 0 Treffer des Moduls bei 1203 Bash-Aufrufen
(Transkript-grep). Ein Fenster, das nichts beurteilen kann, kann nichts scharfschalten. Empfehlung:
streichen und in `declined` begründen (R8); die Quoting-Fehlläufe dieser Sitzung (#11) liegen ohnehin
außerhalb seines Zuschnitts.

## Self-Review

Meta-Agent (sonnet), sah nur Report + Skill, prüfte 3 Belege unabhängig gegen `origin/main`/gh
(`requirements.txt:27`, `text_bearbeiten.js` Z. 23/44, #87 Merge-Zeit und 0 Reviews, #84/#85
Kommentare) — alle stimmen. Invariante 11 = 11 = 11 erfüllt; Frontmatter-Rechnung 19 = 11 + 8,
refuted_rate 8/19 = 0.42, Band gesund; Scores ganzzahlig und verankert. Sechs Auffälligkeiten,
alle eingearbeitet:

1. Self-Review war Platzhalter — dieser Abschnitt.
2. `gate_wirkung.py` meldete vier statt drei rückfällige Gates; das vierte (`inline-heredoc-quoting-rework`)
   erzeugte **dieser Report selbst**: die Frontmatter-Form `["slug: Grund"]` und ein `[ ]` im Text
   wurden nicht als `gates_verwandt` gelesen, und die Tabellenzeilen trugen den Marker ohne
   Begründung. Behoben (nackte Slugs in der Frontmatter, Begründung in der Recurrence-Spalte); danach
   wieder drei. Werkzeug-Befund als R12.
3. `built-but-never-called` mit Rückfall 2026-10-07: stammt aus anderen Retros desselben Tages, in §0 benannt.
4. Gefangen-Zahl `claim-before-cheapest-check` 5 → 6 angeglichen.
5. §1 zählte sieben statt acht Widerlegte — Quelle je Widerlegung jetzt genannt; #14–#17 sind von den
   Skeptikern widerlegt, 3b hat sie nicht erneut geprüft.
6. Board deckte #5, #6, #9, #11, #19 nicht — R10 erweitert, R11 neu, Rest mit Grund unter §7.

Nicht geprüft vom Meta-Agenten: Kennzahlen- und Journalzeilen (Transkript-Auswertung), Links per HTTP.

Phase 6 (Extern-Handoff): n/a — kein Prod, keine irreversiblen Schritte; die Widerlegungsbahn hat
zwei Befunde gekippt und einen gefunden, die Methode trägt für diesen Footprint ohne fremden Anbieter.

## Vierklang

- **getan:** 3 Finder, 3 Skeptiker (inkl. Finder-Widerspruch K1), Widerlegungsbahn (2 gekippt, 1 neu), 19 Befunde, 11 überleben; Wirkungsbilanz, Längsschnitt, Rückfall-Prüfung, Soll-Ablauf, Streichbahn.
- **angenommen:** Zeitstempel aus dem Transkript sind UTC; die Session-Grenze über PR-/Issue-Nummern erfasst alle Artefakte der Sitzung.
- **nicht verifizierbar:** Ursache der Kompaktierungen, Deckung des Skript-Selbststarts, Ausnutzbarkeit `innerHTML`, zweiter Merge-Versuch #574 (§8).
- **offen geblieben:** R1–R10; schreib-hub#34 bleibt bis Mutationsprobe, K6-Entscheid und Owner-Gegenprobe offen.
