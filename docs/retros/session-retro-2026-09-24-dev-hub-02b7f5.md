---
retro_schema: 1
date: 2026-09-24
repo_scope: [dev-hub, platform, chat-hub]
session_id: 02b7f5
footprint: full
footprint_reduction_reason: "deep→full: (a) Prod-Schritt ausdrücklich freigegeben (Owner-Wort „25 go", Merge #383 per Owner-Klick, Kommentar dev-hub#382 16:02Z); (b) voll rollback-fähig, keine DB-Migration; (c) Befund-Schätzung ≤10 (tatsächlich 19)"
findings_total: 19
findings_survived: 15
refuted_rate: 0.21
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [aktionswaechter-kommunikationsklasse, holdout-nach-tuning-neu-deklarieren, retro-kennzahlen-queued-command, deferred-item-no-tracking-issue]
recurring_findings: [scope-checkpoint-not-durably-recorded, inline-heredoc-quoting-rework, deferred-item-no-tracking-issue, worktree-midsession-accumulation, untested-tool-module-green-gate, claim-before-cheapest-check]
gates_caught: []
over_ask_klassen: [memory-index-straffung-vorgelegt]
over_act_klassen: []
widerlegung: "2 gekippt, 4 neu"
streichkandidaten: []
streich_begruendung: "Einziger geprüfter Kandidat war der Meta-Agent (Phase 5); retro_report_check.py deckt nur Form und Pflichtfelder, nicht Beleg je Befund, Ganzzahligkeit der Scores und die Soll-Invariante — keine Dublette, kein Effekt-Ersatz."
---

# Session-Retro 2026-09-24 · dev-hub / platform · 02b7f5

Sitzung: Vor-Router-Prototyp vor Claude (Auftrag SA-4), danach Scope-Zuwachs auf Kontingent-Messung,
CLAUDE.md-/Memory-Straffung und Policy-Hook. Artefakte: dev-hub#383, #384, #382; platform#3541;
lokale Dateien (`~/.claude/bin/kontingent-woche`, systemd-Timer, Memory-Index).

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py` meldete 6 Gates RUECKFAELLIG. Deren Rückfälle stammen aus anderen Retros (letzte Vorkommen
2026-09-23/24); die Konsequenz bleibt bei den Retros, die sie gezählt haben.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| check-ohne-positivkontrolle | 2 | nicht aus dieser Sitzung | Entscheidung bei der zählenden Retro |
| handover-stale-vor-merge | 2 | nicht aus dieser Sitzung | dito |
| melder-ohne-leser | 2 | nicht aus dieser Sitzung | dito |
| secret-leak-via-safe-pattern | 2 | nicht aus dieser Sitzung | dito |
| stale-local-clone-as-ground-truth | 2 | Finder „Soll-Ist": Architekturbefund stützte sich auf Live-Checks, nicht auf ungefetchten Clone | kein Beitrag dieser Sitzung |
| untested-tool-module-green-gate | 2 | Befund #14 trägt bei | s. 5a |

## 1. Executive Summary

- Auftrag erfüllt: Architekturbericht, Prototyp mit 2 Vorstufen, Fail-open 54/54 bitgleich, GX10-Nachweis,
  Kosten-/Tokenbericht; keine produktive Migration der Claude-Code-Anbindung.
- Schwächen der Messung: Holdout-Leck beim Aktions-Wächter (#10), 57-%-Szenario auf einer Einzelmessung (#9),
  GX10-Abbruch nur clientseitig belegt (#8), Wächter ohne Kommunikations-Klasse (#11).
- Prozess: Scope-Checkpoint erst nach dem Prod-Deploy (#3), vor dem dritten Repo nicht wiederholt (#6);
  eine falsche Aussage an den Owner („Merge durch Claude gesperrt", #17); zwei Quoting-Fehler (#4).
- Werkzeug: `retro_transkript_kennzahlen.py` übersieht eingereihte Nachrichten (#19) — führte die
  Widerlegungsbahn zu einer falschen Freigabe-Anklage (#16, per Befehl widerlegt).
- Kosten der Retro: Sonnet-Agenten 106k–139k Token je Agent, Opus-3b 108k — rund doppelt so viel wie der
  Skill-Richtwert (~55k).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | PR-Text #383 nennt `GX10_NOT_SAFE_YET`, REPORT.md im selben Merge `GX10_SAFE_FOR_PRE_ROUTER_TESTS` | Kommunikation | mittel | SURVIVES | dev-hub#383 Body; REPORT.md §F in `919c834`; Korrektur-Commit `1896c19` 15:01Z vor Merge 16:11Z | neu |
| 2 | Worktree + Remote-Branch `deploy-ignore-experiments` nach Merge #384 nicht aufgeräumt | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `repo-session.sh list`; `gh api …/branches/session%2F2026-09-24%2Fachim-dehnert%2Fdeploy-ignore-experiments` | worktree-midsession-accumulation |
| 3 | Scope-Checkpoint erst nach dem Prod-Deploy von #383 | Prozesslücke | hoch | SURVIVES (kommandobelegt) | Merge #383 16:11:54Z; Checkpoint dev-hub#382 16:36:08Z (issuecomment-5818172166) | scope-checkpoint-not-durably-recorded |
| 4 | Zwei Inline-Texte mit „…"-Quotes brachen (Issue-Kommentar abgeschnitten, Commit gescheitert) | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript 16:02:35Z Exit 2 (issuecomment-5817644664 zunächst verkürzt); Commit-Fehlschlag 16:12:43Z | inline-heredoc-quoting-rework |
| 5 | Dockerfile kopiert `experiments/` ins Prod-Image — nur als Nebensatz im Issue-Kommentar, kein Tracking-Item | Prozesslücke | mittel | SURVIVES | dev-hub `origin/main:.dockerignore`, `Dockerfile`; dev-hub#382 Kommentar 16:02Z | deferred-item-no-tracking-issue |
| 6 | Vor platform#3541 (drittes Repo, globaler Hook, Live-Verteilung) kein erneuter Scope-Checkpoint | Prozesslücke | hoch | SURVIVES | Checkpoint 16:36Z nennt platform nicht; #3541 Commit 16:56Z, Merge 17:03Z | scope-checkpoint-not-durably-recorded |
| 7 | REPORT.md-Kopfzeile „nichts an globalen Einstellungen geändert" durch #3541 falsch geworden | Kommunikation | mittel | REFUTED | Kopfzeile war zum Merge-Zeitpunkt wahr; keine Nachtragspflicht für gemergte Artefakte | — |
| 8 | Akzeptanzkriterium 4 (GX10) nur clientseitig belegt; serverseitiger Abbruch nicht beobachtet | fehlende Validierung | mittel | SURVIVES | `gx10_probe.py` (P2 = `asyncio.wait_for` 1 s); `results/gx10_probe.json`; REPORT.md §F eigener Vorbehalt | neu |
| 9 | 57-%-Ersparnis (Szenario b) auf einer einzigen Messung des Sitzungs-Grundaufwands | fehlende Validierung | niedrig | SURVIVES | REPORT.md §D „eine Messung" | neu |
| 10 | Holdout-Leck: Wächter an h-08/h-12 aus Holdout 1 („nicht zum Tunen") motiviert; „0 FP" in Lauf 3 enthält diese Fälle | fehlende Validierung | hoch | SURVIVES | `testset.py:261`, `:277`; REPORT.md §C | neu |
| 11 | Aktions-Wächter ohne Kommunikations-Klasse (senden/schicken/Mail/Issue), kein Testfall | verfrühte Festlegung | mittel | SURVIVES | `prerouter.py:85-95`; `testset.py` (nur h2-11, Lesefrage) | neu |
| 12 | `inject_policies.py`: Lesen→Rechnen→Schreiben der Merkliste nicht atomar, ungetestet; ob parallele Läufe je Sitzung vorkommen, unbelegt | fehlende Validierung | niedrig | SURVIVES | platform `tools/claude-hooks/inject_policies.py`, `test_inject_policies.py` ohne Race-Test | neu |
| 13 | `kontingent-woche`: unbeaufsichtigter Issue-Post verstößt gegen die Automatismus-Regel | fehlende Validierung | mittel | REFUTED | Regel zielt auf gemergte Cross-Repo-Automatismen; lokales Einmal-Skript, offengelegt, Owner-Wort 16:31:33Z. Technisch bestätigt: `check=True` ohne Fehlerpfad, Temp-Datei bleibt; `Persistent=true` verschiebt Fenster | — |
| 14 | Die 30 Prototyp-Tests laufen nicht in der Repo-CI, nur lokal | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | `experiments/prerouter/pytest.ini:1-2`; `gh pr checks 383` | untested-tool-module-green-gate |
| 15 | Finder-Behauptung „alle drei Merges vom Owner geklickt" | Kommunikation | niedrig | REFUTED | platform#3541 Kommentar 17:03:02Z „Merge durch Claude mit Marker OWNER_WORT=60" | — |
| 16 | (3b-N1) Timer und Checkpoint dokumentierten „47 go" vor dem Owner-Wort | Kommunikation | hoch | REFUTED (kommandobelegt) | Transkript `queued_command` „47 go" 16:31:33Z; Unit-Datei mtime 16:33:12Z | — |
| 17 | (3b-N2) Aussage an Owner „Den Merge durch Claude hat der Klassifizierer gesperrt" — kein Merge-Aufruf für #383, gesperrt war der Freigabe-Vermerk | Kommunikation | mittel | SURVIVES (kommandobelegt) | dev-hub#382 issuecomment-5817644664; Ablehnung 16:02:22Z [Production Deploy] betrifft `gh issue edit` | claim-before-cheapest-check |
| 18 | (3b-N4) Action-Board-Entwurf verlinkte platform#3541 für nicht zugehörige Items, Tabelle statt Link-Liste | Kommunikation | niedrig | SURVIVES (kommandobelegt) | Report-Entwurf §7 (vor Korrektur) | neu |
| 19 | `retro_transkript_kennzahlen.py` erfasst eingereihte Nachrichten (`attachment.type=queued_command`) nicht als Nutzer-Nachrichten | Werkzeug | mittel | SURVIVES (kommandobelegt) | Transkript: `queued_command` „47 go" 16:31:33Z fehlt in kennzahlen.txt, dort erst 17:04:58Z | neu |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | alle 7 Akzeptanzkriterien belegt, AC4 nur clientseitig (#8) |
| architektur_design | 4 | Fail-open-Kaskade trägt; Merkliste nicht atomar (#12) |
| code_konventionstreue | 3 | Quoting-Rework (#4), Tests außerhalb CI (#14) |
| risiko_debt | 3 | Dockerfile-Befund ungetrackt (#5), Wächter-Lücke Kommunikation (#11) |
| prozess_effizienz | 3 | Checkpoint zu spät/nicht wiederholt (#3, #6), Aufräumen unvollständig (#2) |
| entscheidungsqualitaet | 3 | Holdout-Leck (#10), Hochrechnung auf n=1 (#9), falsche Aussage an Owner (#17) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR-Text #383 blieb auf Stand 14:44Z, Report wurde 15:01Z korrigiert | Nach jedem Commit, der einen im PR-Text genannten Status ändert: `gh pr edit --body-file` im selben Zug | #1 |
| Worktree `deploy-ignore-experiments` blieb nach Merge liegen | Nach jedem Merge einer Sitzungs-PR: `repo-session.sh end <wt>` + Remote-Branch löschen, im selben Zug | #2 |
| Owner-Frage „25 go" (Merge mit Deploy) kam vor dem Scope-Checkpoint | Checkpoint-Satz VOR der Frage nach einem Prod-Wort, im selben Board | #3 |
| `gh issue comment --body "…„…"…"` und `git commit -m` mit „" | Jeder Text mit Sonderzeichen über Datei (`--body-file`, `-F`) — auch Einzeiler | #4 |
| Dockerfile-Hinweis nur im Kommentar | Eigener Checklistenpunkt in #382 mit `.dockerignore`-Zeile als Next Step | #5 |
| platform#3541 ohne zweiten Checkpoint | Bei jeder neuen Schwelle (neues Repo, globaler Hook) Checkpoint wiederholen, als Issue-Kommentar | #6 |
| GX10-Status SAFE bei nur clientseitigem Abbruch-Beleg | Status mit Zusatz „clientseitig" führen, bis das Ollama-Journal den Abbruch zeigt | #8 |
| 57 % aus einer Messung | ≥3 Messungen des Grundaufwands, Spanne angeben, bevor eine Prozentzahl in die Schlagzeile geht | #9 |
| Holdout 1 half beim Tuning, blieb als „nicht zum Tunen" deklariert | Nach Tuning an Holdout-Fällen deren Label umstellen, FP-Zahl nur über den unberührten Holdout ausweisen | #10 |
| Wächter-Muster induktiv aus 2 Fehlfällen | Muster aus einer Risikoklassen-Liste (Infra, Kommunikation, Geld, Daten), je Klasse ≥1 Testfall | #11 |
| Merkliste Read-Modify-Write ohne Sperre | Beim Schreiben erneut lesen und vereinigen oder `fcntl`-Lock; ein Nebenläufigkeitstest | #12 |
| Fail-open-Tests laufen nur lokal | Tracking-Punkt „vor Weiterverwendung in CI aufnehmen" in #382 | #14 |
| „Merge durch Claude gesperrt" ohne Merge-Versuch geschrieben | Sperrgrund wörtlich aus der Ablehnung zitieren (welcher Befehl, welche Klasse), nicht umdeuten | #17 |
| Board-Zeilen mit fremdem PR-Link als Platzhalter | Ohne eigenes GitHub-Objekt Board-Link oder Bericht-PR verlinken; Link-Items als Liste | #18 |
| Kennzahlen-Skript zählt nur `type=user`-Nachrichten | `queued_command`-Anhänge als Nutzer-Nachricht mitzählen + Selbsttest-Fall ergänzen | #19 |

`|Soll-Schritte| = 15 = |überlebende Befunde|`.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (vor diesem Bericht): `claim-before-cheapest-check` ×92,
`deferred-item-no-tracking-issue` ×49, `scope-checkpoint-not-durably-recorded` ×32,
`untested-tool-module-green-gate` ×11, `inline-heredoc-quoting-rework` ×8,
`worktree-midsession-accumulation` ×8 — alle ≥2 ⇒ GATE-PFLICHT. Für fünf der sechs existiert ein Gate unter
`docs/governance/gates/gates/` (per `ls`: fünf Treffer), daher 5a. **Kein Gate** hat `deferred-item-no-tracking-issue`
(×49) — geführt als `gate_candidate`, nicht unter 5a. (Die Erstfassung behauptete „alle sechs"; vom Meta-Prüfer korrigiert.)

> **Nachtrag 2026-09-24 (Umsetzung von 5a, Owner-Wort „9 10 go"):** Die Korrektur war selbst falsch.
> `deferred-item-no-tracking-issue` ist gedeckt — über `covers` im Gate `aufschub-anker` (blocking,
> `tools/deferral_anchor_check.py`); der eigene Scanner wurde am 2026-09-14 bewusst stillgelegt
> (`docs/governance/gates/declined/deferred-item-no-tracking-issue.json`, Belegart „kein Effekt").
> Der Existenz-Check per Dateiname übersah das `covers`-Feld. Kein neues Gate. Befund #5 (Dockerfile-Hinweis
> als Kommentarnotiz) war keine Vertagungsformulierung, die `aufschub-anker` sehen könnte — kein Rückfall
> dieses Gates. Der `gate_candidate`-Eintrag oben ist damit gegenstandslos. Umgesetzt aus 5a:
> `inline-heredoc-quoting-rework` ausgeweitet (dieser PR).

### 5a. Rückfall-Prüfung

| Gate | Stand `gate_wirkung.py` vor diesem Bericht | diese Sitzung | Entscheidung |
|---|---|---|---|
| scope-checkpoint-not-durably-recorded | advisory, 0 Rückfälle | +2 (#3, #6); Stop-Hook feuerte 16:33:30Z und 16:35:55Z, erst nach der Handlung | **umbauen** (zu spät): Hinweis vor der Owner-Frage nach einem Prod-Wort statt nach der Handlung — Kandidat, Edit über `gate_verankerung_check.py --neu` (Owner-Zug) |
| inline-heredoc-quoting-rework | advisory, 1 Rückfall | +1 (#4) ⇒ rückfällig | **ausweiten**: sieht Heredoc, nicht Inline-`--body "…"`/`-m "…"` mit typografischen Quotes — Kandidat (Owner-Zug) |
| claim-before-cheapest-check | blocking, 1 Rückfall | +1 (#17) | Scanner feuerte in dieser Sitzung zweimal (Stop-Hook); #17 lag in einem Issue-Kommentar, den er nicht sieht — **ausweiten** auf `gh issue comment`-Texte, Kandidat |
| worktree-midsession-accumulation | process, 1 Rückfall, beobachten | +1 (#2) ⇒ rückfällig | **ausweiten**: auch Sitzungs-Worktrees nach Merge ihres PRs erfassen (nicht nur mitten in der Sitzung) — Kandidat (Owner-Zug) |
| untested-tool-module-green-gate | RUECKFAELLIG | +1 (#14) | **ausweiten**: `experiments/**` mit eigener `pytest.ini` als nicht-blockierenden CI-Lauf erfassen — Kandidat (Owner-Zug) |

`gates_caught` leer: 3b kippte „gefangen" — der Hook feuerte erst nach der Handlung, #6 blieb ungefangen.

### 5b. Autonomie-Kalibrierung

- `over_ask`: `memory-index-straffung-vorgelegt` — reversible Memory-Umstrukturierung wurde als „58 go" vorgelegt.
- `over_act`: keiner. Timer nach Owner-Wort 16:31:33Z (#16 widerlegt); Deploy-Merges #383/#384 ohne eigenen
  Merge-Aufruf im Transkript; #3541 per `OWNER_WORT=60` nach Owner-Nachricht 17:02:20Z (Deutung s. §8).

## 6. Verankerung (Vorschläge, nicht angewendet)

**memory_candidates**
- `feedback_holdout_nach_tuning_umlabeln` — „Wird ein Holdout-Fall zum Anlass einer Regel, ist er kein Holdout mehr: Label umstellen, FP nur über unberührte Fälle ausweisen." (#10)
- `feedback_pr_body_nach_statuswechsel_nachziehen` — „Ändert ein Commit einen im PR-Text genannten Status, wird der PR-Text im selben Zug nachgezogen." (#1)
- `feedback_sperrgrund_woertlich_zitieren` — „Eine Klassifizierer-Sperre wird mit dem gesperrten Befehl und der Klasse zitiert, nicht umgedeutet." (#17)

**adr_candidates / Skill- und Werkzeug-Edits**
- `tools/retro_transkript_kennzahlen.py`: `queued_command`-Anhänge als Nutzer-Nachricht zählen, Selbsttest-Fall ergänzen (#19).
- session-retro Skill §0.1: Kostenrichtwert „~55k je Skeptiker" ersetzen — gemessen 2026-09-24: Finder 106k/117k/139k, Skeptiker 136k (Sonnet), 3b 108k (Opus).
- Gates `scope-checkpoint-not-durably-recorded` (umbauen), `inline-heredoc-quoting-rework` und `claim-before-cheapest-check` (ausweiten) — s. 5a.

## 7. Maßnahmen (Action-Board)

- **[1]** 🔵 PR-Text #383 korrigieren · dev-hub · ich — https://github.com/achimdehnert/dev-hub/pull/383
- **[2]** 🔵 Worktree/Branch #384 aufräumen · dev-hub · ich — https://github.com/achimdehnert/dev-hub/pull/384
- **[3]** 🔵 Punkte #5/#11/#14 in #382 tracken · dev-hub · ich — https://github.com/achimdehnert/dev-hub/issues/382
- **[4]** 🟢 Fünf Gate-Edits aus 5a + neues Gate `deferred-item-no-tracking-issue` entscheiden · platform · du — https://github.com/achimdehnert/platform/pull/3545
- **[5]** 🟢 Kennzahlen-Skript + Skill-Kostenrichtwert · platform · du — https://github.com/achimdehnert/platform/pull/3545
- **[6]** ✅ Streichbahn: kein Kandidat · platform — https://github.com/achimdehnert/platform/pull/3545

## 8. Nicht verifiziert (Restlücken)

- **getan:** Phase 0.0, Collect (3 Repos gefetcht, Transkript-Kennzahlen), 3 Finder + 1 Skeptiker in frischem Kontext, 3b (Opus), Meta, `retro_report_check.py`; N1 per Transkript-Befehl widerlegt. Phase 6 (Extern-Handoff) n/a: nur bei `deep`, Footprint auf `full` reduziert.
- **angenommen:** Gewichtung der Kostenarten folgt API-Preisverhältnissen (Abo-Gewichtung unbelegt); Owner-Klick bei #383/#384 belegt nur durch fehlenden eigenen Merge-Aufruf im Transkript.
- **nicht verifizierbar:** serverseitiger GX10-Abbruch (#8) — billigster Check: `journalctl --user -u ollama` auf der GX10 während einer Probe; parallele `UserPromptSubmit`-Läufe je Sitzung (#12) — billigster Check: zwei Prompts in schneller Folge + Zeitstempel. **Hypothese (3b-N3, nicht falsifiziert, kein Skeptiker-Budget):** Die Owner-Nachricht 17:02:20Z („PR #3541 mergen), [61] …") ist ein zurückkopiertes Board-Fragment; `pr_merge_sa.py` meldete M0, gemergt wurde mit `OWNER_WORT=60`. Die Deutung als Merge-Auftrag ist vertretbar, im PR-Kommentar ist der M0-Befund nicht erwähnt — billigster Check: Owner fragen.
- **offen geblieben:** Schattenbetrieb (Klassifizierer-Sperre, Owner-Regel ausstehend); Gate-Edits aus 5a; Board-Punkte 1–5.

## Widerlegung

Phase 3b (Opus, frischer Kontext), Ergebnis `2 gekippt, 4 neu`:

- **GEKIPPT:** `gates_caught: [scope-checkpoint-not-durably-recorded]` — #6 blieb ungefangen, der Hook feuerte 22 min nach dem Prod-Merge. Übernommen: `gates_caught` leer, 5a „umbauen".
- **GEKIPPT:** #13 (REFUTED) wegen N1. Nicht übernommen: N1 selbst wurde per Transkript widerlegt (`queued_command` „47 go" 16:31:33Z vor Unit 16:33:12Z), #13 bleibt REFUTED.
- **NEU N1** → #16 REFUTED. Ursache der Fehlanklage: Kennzahlen-Skript übersieht eingereihte Nachrichten → #19.
- **NEU N2** → #17 SURVIVES. **NEU N3** → §8 als Hypothese. **NEU N4** → #18 SURVIVES, Board auf Link-Liste umgestellt.
- BESTAETIGT: #1–#5, #7, #15.

## Self-Review

Meta-Prüfer (Sonnet, frischer Kontext, nur Report + Skill): Invariante 15 = 15, Scores ganzzahlig und verankert,
Frontmatter valide, Pfad kollisionsfrei, 4 Belege unabhängig bestätigt. Zwei Mängel gefunden und behoben:
§5 „alle sechs haben ein Gate" (falsch, fünf) und drei 5a-Zeilen ohne eine der drei zulässigen Antworten.
`refuted_rate` = 4/19 = 0,21 — im neutralen Band (0,2–0,8), knapp über der Theater-Schwelle.

## Streichbahn

Keiner, weil der einzige geprüfte Kandidat — der Meta-Agent (Phase 5) — keine Dublette von
`retro_report_check.py` ist: der Prüfer deckt Frontmatter-Felder, Spalten, Vierklang, §8 und Streichbahn ab
(`tools/retro_report_check.py:27-28, 99-104`), nicht aber Beleg je Befund, Ganzzahligkeit der Scores und die
Soll-Invariante.
