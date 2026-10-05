---
retro_schema: 1
date: 2026-10-04
repo_scope: [robo-lab]
session_id: 213b56
footprint: full
findings_total: 19
findings_survived: 13
refuted_rate: 0.32
phase3_refuted: 6
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [schwelle-nach-messung-gesetzt, ursachen-urteil-ueber-belegstand]
recurring_findings: [untested-tool-module-green-gate, deferred-item-no-tracking-issue, tracking-doc-stale-after-new-occurrence, inline-heredoc-quoting-rework, eine-variable-je-lauf-verletzt]
gates_caught: [merge-guard-sa-m, claim-before-cheapest-check, leerer-body-guard, sleep-blocker]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: keiner, weil der einzige Kandidat (Phase 0.0 fuer sitzungsfremde Gates) nur per Schlagwortsuche gezaehlt ist (7 von 20 Reports, ohne Positivkontrolle) und damit keine der vier Belegarten traegt
---

# Session-Retro robo-lab 2026-10-02 bis 2026-10-04 (Sitzung 994a931a…213b56)

Footprint: 10 PRs (#176, #192, #193, #195, #196, #198, #199 gemergt; #200, #201, #202 offen), 1 Repo, kein Prod, keine Migration, GPU-Box als Fremdressource → `full`. Agenten: 3 Finder + 2 Skeptiker (sonnet) + 1 Widerlegung (Opus) = 6.

## 0.0 Wirkungsbilanz

`gate_wirkung.py` meldet 7 Gates `RUECKFAELLIG`: untested-tool-module-green-gate, check-ohne-positivkontrolle, handover-stale-vor-merge, melder-ohne-leser, parallel-session-pr-collision, secret-leak-via-safe-pattern, stale-local-clone-as-ground-truth.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 2 | Befund #1 dieser Retro liegt VOR Sitzungsende; E.3 misst erst bei /session-ende | keine Änderung: kein Rückfall, solange E.3 am Ende greift; wird bei /session-ende belegt |
| untested-tool-module-green-gate | 3 | Ursache an der Quelle: Befund #19, drei neue Eval-Skripte in `training/` ohne Selbsttest, CI deckt `training/` nur mit zwei Dateien | nachschärfen: Gate muss robo-lab `training/` sehen; Vorschlag M9, Owner (Gate-Edit läuft über `gate_verankerung_check.py --neu`) |
| übrige 5 | 2 | von dieser robo-lab-Sitzung nicht berührt, keine neue Evidenz zur Ursache | nicht entschieden, §8 (Entscheidung gehört in eine platform-Retro) |

## 1. Executive Summary

- Ziel „fehlerfreies Verhalten" ist nicht erreicht und ehrlich so ausgewiesen: Einsteigen/Sitzen unter Streuung erfüllt (#196), Anreichen und Händeschütteln bestehen unter Streuung nicht (#200, #202).
- Kernschwäche ist die Beweisführung, nicht die Technik: zwei Schwellen wurden nach den ersten Messwerten gesetzt (S7 20 N, Bahnmaß), ein Ursachen-Urteil („Wurzel belegt") stützt sich auf einen Lauf je Variante, zwei Läufe änderten mehr als eine Variable.
- PR-Texte driften gegeneinander: #201/#202 nennen veraltete Stände, #198 verspricht Ergebnisse „in diesem PR" und wurde vorher gemergt.
- Bewusst Ausgelassenes (Lageschätzung am echten G1, Q2-Schwellen-Abnahme) steht nur im PR-Text, nicht als Issue.
- Widerlegt: Merge-Guard-Umgehung, Scope-Verkleinerung S7 ohne Freigabe, Kommunikationsmangel, PR-Bündelung #192, Selektion #196, Passung Händeschütteln.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Handover auf main kennt #198/#199 nicht (Stand „2026-10-02 nacht", Prio sagt S7 offen) | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git show origin/main:AGENT_HANDOVER.md` Z. 7, Z. 667 | handover-stale-vor-merge (Gate misst bei Sitzungsende) |
| 2 | #198 kündigt Ergebnisse „in diesem PR" an, gemergt 12:31Z ohne Korrektur | Kommunikation | niedrig | SURVIVES (kommandobelegt) | PR #198 Body | — |
| 3 | #201/#202 nennen veraltete Stände (Lauf 2 „läuft", „Diagnose-Lauf misst jetzt"), #200-Titel kennt Lauf 3/4 nicht | Kommunikation | mittel | SURVIVES (kommandobelegt) | PR #201, #202 Body; #200 Titel | tracking-doc-stale-after-new-occurrence |
| 4 | Lageschätzung am echten G1 und Q2-Schwellen-Abnahme ohne Issue | Prozesslücke | mittel | SURVIVES (kommandobelegt) | #200 Body „eigene Frage"; `gh issue list --search Lageschätzung` leer | deferred-item-no-tracking-issue |
| 5 | #198/#199 S7-Zahlen uneinheitlich (34 / 33,6 / 34,5 N) ohne Erläuterung | Kommunikation | niedrig | SURVIVES (kommandobelegt) | PR #198, #199 Body | — |
| 6 | Blockiertes `sleep` zweimal angelaufen, danach Timeouts | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Kennzahlen 2026-10-04T11:31:32, 12:33:32, 13:22–13:25 | — |
| 7 | Repo-Dateien per Python-Heredoc geschrieben statt Edit/Write; Edit ohne frisches Read (4×) | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Kennzahlen 11:29:30, 13:23:42; 2026-10-02T18:09, 2026-10-04T11:07, 17:20 | inline-heredoc-quoting-rework |
| 8 | Umgebungsfehler in frischen Worktrees (mujoco, vendor, ssh-Quoting) ohne Preflight | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | Kennzahlen 2026-10-04T10:51:56, 10:53:42, 11:54:03 | — |
| 9 | S7-Grenze 20 N rückwärts aus 31,9 N ÷ frei gewähltem 1,5 abgeleitet, Marge 6 % unter eigener Unsicherheit 10 % | verfrühte Festlegung | hoch | SURVIVES | PR #199, `sim/pflege_grenzen.py:59`, #197 „innerhalb 10 %" | — |
| 10 | Bahnmaß: Positivkontrolle tautologisch, Grenzen unkalibriert, „vor der Messung festgelegt" unbelegt (Code 13:57 nach Bewertung 13:24) | fehlende Validierung | mittel | SURVIVES | PR #201, fddff3f, `sim/menschenaehnlichkeit_bahn.py` | — |
| 11 | „Wurzel belegt" (#200 Lauf 3) auf einem Trainingslauf je Variante, S5 weiter nicht bestanden; #202 übernimmt als Fakt | fehlende Validierung | mittel | SURVIVES | PR #200 Body, PR #202 Body | — |
| 12 | Eine Variable je Lauf verletzt: #196 Lauf 7 (Start + Streubreite), #200 Lauf 2 (+2000 Iterationen) mit Ausschluss-Urteil | Prozesslücke | mittel | SURVIVES | PR #196 Tabelle, PR #200 Body | eine-variable-je-lauf-verletzt |
| 19 | Eval-/Kennzahl-Skripte hinter den S5-Urteilen (`eval_anreichen.py`, `kennzahlen.py`, `eval_handschlag.py`) ohne Selbsttest und ohne CI-Lauf | fehlende Validierung | mittel | SURVIVES (kommandobelegt, Widerlegungsbahn) | #198; `grep -c selbsttest` = 0; ci.yml compileall nur `sim twin_mcp twin_web arena exo` | untested-tool-module-green-gate |
| 13 | Merge-Guard per selbst gesetztem OWNER_WORT umgangen | Prozesslücke | hoch | REFUTED | Owner-Wort lag vor („s2 s3 go", „[PR196] 🟢 Merge it"), Kommentar-ID nach Guard-Vorgabe, Merge durch Owner; die Marker-Kommentare hat die Sitzung selbst gepostet, für #192 beruht „S3 = Merge“ auf ihrer Deutung | — |
| 14 | PR #192 bündelt Themen, 16 Commits Rework | Prozesslücke | mittel | REFUTED | Stack-Syncs von #188–#191, Squash ein Thema (df17778) | — |
| 15 | Zu wenige Zwischenstände (36 Silent-Reminder) | Kommunikation | niedrig | REFUTED | Lücken 1,7–3,1 min normal, keine Owner-Beschwerde, „maximal autonom" | — |
| 16 | S7-Umfang ohne Owner-Freigabe verkleinert, #171 nicht nachgezogen | Prozesslücke | hoch | REFUTED | Owner „B2 entscheide du", #171-Kommentar 12:33, Abnahme bleibt Owner | — |
| 17 | model_12999 (#196) Selektion aus vielen Kandidaten | fehlende Validierung | niedrig | REFUTED | 3 Kandidaten, Regel vorab, frische Seeds trennen | — |
| 18 | Händeschütteln-Szene nach Passung (Tempo ×1,5 unter 140 N) | verfrühte Festlegung | niedrig | REFUTED | Originaltempo schon 136 N < 140 N; Abstand 0,85 m betrifft Anreichen, offen dokumentiert | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Einsteigen/Sitzen erfüllt, Anreichen/Händeschütteln nicht; ehrlich ausgewiesen (#1, #11) |
| architektur_design | 3 | Welt-/Szenenmodelle sauber getrennt, aber Eval-Skripte ungetestet und Bahnmaß unkalibriert (#10, #19) |
| code_konventionstreue | 3 | Heredoc statt Edit/Write, Edit ohne Read (#7) |
| risiko_debt | 3 | Schwellen nach Messung, offene Fragen ohne Issue (#4, #9) |
| prozess_effizienz | 3 | blockierte Wartebefehle, Preflight fehlt (#6, #8) |
| entscheidungsqualitaet | 3 | Urteile über den Belegstand hinaus (#11, #12) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #198/#199 gemergt, Handover nicht nachgezogen | Mit jedem Merge-Vorschlag eine Handover-Zeile im selben PR | #1 |
| #198 Body verspricht nachgereichte Ergebnisse, Merge vorher | Vor dem Merge-Vorschlag Body auf „Ergebnisse folgen in #NNN" umstellen | #2 |
| #201/#202 Bodies veralten, wenn #200 neue Läufe bekommt | Querverweise auf Lauf-Stände nur als Link auf #200, keine kopierten Stände | #3 |
| „eigene Frage" Lageschätzung nur im PR-Text | Im selben Zug Issue „Lageschätzung am echten G1" anlegen und verlinken | #4 |
| 34 / 33,6 / 34,5 N ohne Einordnung | Statik- und Physikwert in einer Tabelle mit Spaltenkopf führen | #5 |
| `sleep 240; gh pr checks` | Wartepunkte nur per run_in_background-until-Schleife | #6 |
| Python-Heredoc schreibt Repo-Dateien | Repo-Dateien per Edit/Write; Skript nur für generierte Daten | #7 |
| frischer Worktree ohne venv/vendor, ssh inline | Worktree-Preflight (venv, vendor, mujoco) und Box nur per ssh-stdin-Skript | #8 |
| 20 N = 31,9 ÷ 1,5 | Reservefaktor herleiten (Messunsicherheit × Sicherheitsfaktor) und vor der Messung festschreiben; Marge ≥ Unsicherheit prüfen | #9 |
| Bahnmaß-Grenzen nach erster Bewertung, Positivkontrolle = Referenz | Zweiten menschlichen Clip derselben Handlung als Positivkontrolle; Grenzen per Commit vor der Messung datieren | #10 |
| „Wurzel belegt" nach einem Lauf je Variante | Ursachen-Wort erst nach Wiederholung mit zweitem Trainingsseed; bis dahin „konsistent mit" | #11 |
| Lauf mit zwei geänderten Größen, trotzdem Ausschluss-Urteil | Vor dem Start Konfig-Diff gegen Vorlauf ausgeben und auf eine Größe prüfen; sonst kein Ursachen-Urteil | #12 |
| Eval-Skripte ohne Selbsttest erzeugen die Abnahmezahlen | Neues Mess-/Eval-Skript nur mit `--selbsttest` (Positiv- und Negativkontrolle) und CI-Zeile im selben PR | #19 |

## 5. Längsschnitt

`retro_kpis.py`: deferred-item-no-tracking-issue ×52, tracking-doc-stale-after-new-occurrence ×11, inline-heredoc-quoting-rework ×10 — alle GATE-PFLICHT; dieser Retro ist ein weiteres Vorkommen. untested-tool-module-green-gate ×12 GATE-PFLICHT, Gate existiert und ist rückfällig (5a). eine-variable-je-lauf-verletzt ist neu (Vorkommen 1). MEMORY.md robo-lab führt „Abnahme braucht Positiv- UND Negativkontrolle" (passt zu #10) und „Nominalstart-Kennzahl ist EINE Messung" (passt zu #11).

### 5a. Rückfall-Prüfung

**Gate untested-tool-module-green-gate ist rückfällig** (gate_wirkung: 3 Rückfälle seit Bau). Antwort: **ausweiten** — es sieht `training/`-Skripte in robo-lab nicht. Umsetzung als Vorschlag M9 an den Owner, kein Gate-Edit in dieser Retro (Gate liegt in platform, Edit braucht `gate_verankerung_check.py --neu`). Für deferred-item-no-tracking-issue, tracking-doc-stale-after-new-occurrence und inline-heredoc-quoting-rework steht kein Gate unter `docs/governance/gates/gates/` mit diesem Slug in der RUECKFAELLIG-Liste; handover-stale-vor-merge s. 0.0. Kein Gate-Edit in dieser Retro.

### 5b. Autonomie-Kalibrierung

over_ask: keine Klasse belegt. over_act: keine — Merges liefen über den Owner (#13 REFUTED), GPU-Läufe gedeckt durch die GPU-Vollmacht.

## 6. Verankerung (Vorschläge, nicht geschrieben)

memory_candidates:
```markdown
---
name: schwelle-vor-messung-datieren
description: Abnahme-Schwellen und Reservefaktoren vor der ersten Messung per Commit festschreiben
metadata:
  type: feedback
drift: true
drift_episode: 2026-10-04-s7-20n-bahnmass
---
S7 20 N wurde als 31,9 N ÷ 1,5 rückwärts aus dem Messwert gesetzt, die Bahnmaß-Grenzen 33 min nach der ersten Bewertung.
**Why:** Eine nach der Messung gesetzte Schwelle prüft nichts, sie beschreibt die Messung.
**How to apply:** Schwelle + Herleitung committen, bevor bewertet wird; Marge ≥ Messunsicherheit prüfen. [[feedback_abnahme_braucht_positiv_und_negativkontrolle]]
```
```markdown
---
name: ursachen-wort-braucht-wiederholung
description: "Wurzel belegt" erst nach Wiederholung mit zweitem Trainingsseed und einer geänderten Größe
metadata:
  type: feedback
---
#200 Lauf 3 nannte die Zustandsschätzung „belegt" nach einem Lauf je Variante; Lauf 2 änderte zwei Größen und wurde trotzdem verworfen.
**Why:** Ein Trainingsseed streut stark; Urteile wandern in Folge-PRs (#202) als Fakt.
**How to apply:** Konfig-Diff vor dem Start auf eine Größe prüfen; Ursachen-Wort erst nach Wiederholung, sonst „konsistent mit". [[feedback_nominalstart_kennzahl_ist_eine_messung]]
```
adr_candidates: keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Issue Lageschätzung am echten G1 | robo-lab | — | 🔵 | ich lege an |
| M2 | Issue Q2-Schwellen-Abnahme + zweiter Menschclip | robo-lab | #201 | 🔵 | ich lege an |
| M3 | #200 „Wurzel belegt" → „konsistent mit", #202 angleichen | robo-lab | #200, #202 | 🔵 | ich ändere Bodies |
| M4 | #201/#202 Querverweise auf Link umstellen | robo-lab | #201, #202 | 🔵 | ich ändere Bodies |
| M5 | S7-Reservefaktor herleiten oder als Owner-Annahme markieren | robo-lab | #199 | 🟢 | Owner entscheidet |
| M6 | Handover nachziehen (#198, #199, Läufe) | robo-lab | — | 🔵 | bei /session-ende |
| M7 | Memory-Kandidaten verankern | — | — | 🟢 | Owner entscheidet |
| M8 | Streichkandidat 0.0 einzeln nachzählen | platform | — | 🔵 | Treffer der 7/20 einzeln prüfen |
| M9 | Gate untested-tool-module-green-gate ausweiten auf robo-lab `training/`; Selbsttests für die drei Eval-Skripte | platform, robo-lab | #198 | 🟢 | Owner entscheidet |
| M10 | Lizenz AMASS/Eyes_Japan für committete Clips prüfen | robo-lab | #198 | 🔵 | Lizenztext lesen |

## 8. Nicht verifiziert (Restlücken)

- 6 rückfällige Gates außerhalb dieser Sitzung nicht entschieden (0.0) — billigster Check: platform-Retro mit `gate_wirkung.py`.
- Ob „3/10 vor der Person" (#202) aus den committeten JSON reproduzierbar ist — billigster Check: `*.person.json` zählen.
- Phase 5 Meta-Agent nicht gelaufen (Budget ≤6 mit 3b ausgeschöpft); ersetzt durch `retro_report_check.py`.
- Phase 6 Extern-Handoff n/a (nur `deep`).
- Lizenz der AMASS-abgeleiteten Clips (Eyes_Japan) in #198 — Hypothese der Widerlegungsbahn, billigster Check: AMASS-Lizenz gegen den Eintrag halten (M10).
- Streichkandidat-Zählung 7/20 per Schlagwort ohne Positivkontrolle (M8).

**Getan:** 3 Finder, 2 Skeptiker, Widerlegung, Längsschnitt, Report. **Angenommen:** Transkript-Kennzahlen vollständig. **Nicht verifizierbar:** Ursache der 6 fremden Gate-Rückfälle. **Offen geblieben:** M1–M10.

## Widerlegung

Opus-Lauf, frischer Kontext, nur Entwurf + Artefaktliste. BESTAETIGT: #1, #6, #7, #8, #9, #13 (Begründung präzisiert: Marker selbst gepostet), #16. GEKIPPT: `gates_caught: []` (fünf Gate-Treffer im Transkript), 0.0-Zeile „übrige 6 nicht berührt“ (untested-tool-module-green-gate berührt). NEU: #19. Hypothese: Lizenz der Clips (§8). Score architektur_design 4 → 3 übernommen. Nicht gegengeprüft: #2–#5, #10–#12, #14, #15, #17, #18.

## Streichbahn

Keiner, weil der einzige Kandidat — Phase 0.0 verlangt Entscheidungen auch zu Gates, die eine Ein-Repo-Sitzung nicht berührt — nur per Schlagwortsuche gezählt ist (7 von 20 Reports seit 2026-09-20 vertagen dort, Suche ohne Positivkontrolle). Ohne Einzelprüfung trägt er keine der vier Belegarten; nachzählen ist M8.
