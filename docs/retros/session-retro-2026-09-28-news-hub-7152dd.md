---
retro_schema: 1
date: 2026-09-28
repo_scope: [news-hub, dev-hub, chat-hub, platform]
session_id: 7152dd
footprint: full
footprint_reduction_reason: "deep→full: (a) Prod-Schritte je mit Owner-Freigabe vermerkt (news-hub#84, #86, dev-hub#404); (b) voll rollback-fähig, keine DB-Migration, Deploy per Image-Tag, Skript mit Sicherung; (c) Befund-Schätzung ≤10"
findings_total: 11
findings_survived: 7
refuted_rate: 0.36
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [deploy-input-format-undokumentiert]
recurring_findings: [parallel-session-pr-collision, claim-before-cheapest-check, test-asserts-the-case-in-mind-not-the-harmful-one, gate-scope-checkpoint-not-durably-recorded-wirkungslos]
gates_caught: []
over_ask_klassen: []
over_act_klassen: []
widerlegung: "0 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "Keiner, weil der einzige Kandidat (Silent-Reminder-Kennzahl, Fehlbefund F7) ein erstes Vorkommen ohne eine der vier Belegarten ist."
---

# Session-Retro 2026-09-28 · Zeitung aus dem Raum, gh-Last, Websuche news-hub (7152dd)

**Footprint `full`** (Reduktion von `deep`, Gründe im Frontmatter). Vier Repos, drei Prod-Schritte
(Skript-Tausch `vertiefen-chat.sh`, Deploys `895d5ce` und `1b8f53b`), keine Migration, kein ADR.
Budget: 3 Finder + 3 Skeptiker (Sonnet), 1 Widerlegung (Opus), 1 Meta (Sonnet); gemessen
72k–89k Tokens je Finder, 62k–74k je Skeptiker. **Budget überschritten:** Find/Verify 6 statt ≤5,
gesamt 8 statt ≤6. Ursache: je Dimension ein Skeptiker ohne vorheriges Aussortieren der
kommandobelegten Befunde (F3, F9 hätten keinen gebraucht). Beim nächsten `full` zuerst sortieren.

## 0.0 Wirkungsbilanz

`tools/gate_wirkung.py`: 7 Gates `RUECKFAELLIG`, dieselben wie in Retro d332fc am selben Tag.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 5 (+1 hier, F2) | Quelle — Statusangaben über PR-Zustände in eigenen Zwischenständen werden nicht gegen `gh` geprüft | **ausweiten**, auf bestehendem Issue platform#2666 (Familie: Zeitangabe → Zustandsangabe) |
| untested-tool-module-green-gate | 3 | kein Vorkommen hier | nicht entschieden (§8) |
| worktree-midsession-accumulation | 3 | kein Vorkommen hier | nicht entschieden (§8) |
| check-ohne-positivkontrolle | 2 | kein Vorkommen hier | nicht entschieden (§8) |
| melder-ohne-leser | 2 | kein Vorkommen hier | nicht entschieden (§8) |
| secret-leak-via-safe-pattern | 2 | kein Vorkommen hier (F4 ist latent, kein Leck) | nicht entschieden (§8) |
| stale-local-clone-as-ground-truth | 2 | kein Vorkommen hier | nicht entschieden (§8) |

## 1. Executive Summary

- F11: Websuche-Fix (news-hub#85, danach Lauf 39 nur 1 von 5 Themen) und Hetzner-Fix (news-hub#87) sind ausgerollt, aber nur per Einzelaufruf geprüft — Wirkung offen bis Morgenlauf 2026-09-29; D2 folgte ohne neuen Checkpoint. Außerdem gemergt: platform#3595, dev-hub#407.
- F10: Zwei Probe-Ausgaben auf Prod haben den Tagesdeckel verbraucht; der End-to-End-Nachweis im Raum ist frühestens am 2026-09-29 möglich.
- F1: dev-hub#407 behob denselben Fehler wie das vorher angelegte dev-hub#406 samt parallelem PR #408 — ohne Querverweis; #406 und #408 sind weiter offen.
- F2: Das Kernziel von dev-hub#403 (Zuruf im Raum löst Ausgabe aus) ist nicht End-to-End belegt, und der Scope-Checkpoint nannte chat-hub#148 als offen, obwohl er 24 Minuten vorher gemergt war.
- F4: Der `gh`-Mitschreiber loggt die Eltern-Kommandozeile ungefiltert; kein aktueller Aufrufer trägt dort ein Secret, der Pfad ist aber ungetestet.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | dev-hub#407 behebt denselben `.venv`-Link-Fehler wie das zuvor angelegte #406 und der parallele PR #408; keine Querverweise, #406/#408 weiter offen | Prozesslücke | mittel | SURVIVES | dev-hub#406 13:30:29Z, #407 13:46:01Z (merged 14:19:43Z, Body ohne #406), #408 13:49:23Z „Closes #406" OPEN; Cross-Reference-Query auf #406 ohne #407 | parallel-session-pr-collision |
| F2 | #403-Ziel ohne End-to-End-Beleg; Scope-Checkpoint 2 nennt chat-hub#148 als offen, obwohl gemergt | fehlende Validierung | mittel | SURVIVES | dev-hub#403 letzter Kommentar 14:11:50Z; chat-hub#148 mergedAt 14:16:14Z; Checkpoint-Kommentar dev-hub#404 14:40:01Z | claim-before-cheapest-check |
| F3 | Sechs Edit-Aufrufe in frischen Worktrees ohne vorheriges Read, je Serie im selben Zug behoben | Werkzeug | niedrig | SURVIVES | `retro_transkript_kennzahlen.py`: Fehlerläufe 13:45:05Z, 14:24:40–43Z, 15:05:46–49Z | — |
| F4 | `tools/gh_abrufe/gh` schreibt bis 120 Zeichen der Eltern-Kommandozeile ungefiltert ins Log; Test deckt nur `gh`-eigene Argumente | fehlende Validierung | mittel | SURVIVES | platform#3595, `tools/gh_abrufe/gh` (`/proc/$PPID/cmdline`), `tools/tests/test_gh_abrufe.py::test_should_never_log_free_text_arguments`; Ökosystem-Grep: kein Aufrufer mit Secret im Argv | test-asserts-the-case-in-mind-not-the-harmful-one |
| F5 | Websuche ohne Gesamt-Zeitgrenze, Lauf kann unkontrolliert lang werden | verfrühte Festlegung | niedrig | REFUTED | Worst Case fest ≈ 3×120 s + 60 s je Thema, `--max-themen` 5 ⇒ ≈ 35 min, getestet (`test_should_give_up_the_search_after_the_last_retry`) | — |
| F6 | Deploy-Run 36437298152 scheiterte, weil das Image noch nicht gebaut war | fehlende Validierung | mittel | REFUTED | Build-Job endete 14:36:10Z, Dispatch 14:36:49Z; tatsächliche Ursache siehe F9 | — |
| F7 | 3,9 min ohne sichtbare Rückmeldung nach Classifier-Fehler 14:04:18Z | Kommunikation | niedrig | REFUTED | Transkript 14:04–14:08: acht sichtbare Werkzeugaufrufe, keine Nutzer-Nachricht wartend (letzte 14:03:12Z) | — |
| F8 | Self-Approval-Ablehnung betraf einen direkten PR-Merge-Versuch | Prozesslücke | niedrig | REFUTED | abgelehnter Aufruf 13:51:07Z war `tools/pr_merge_sa.py 3595`, kein `gh pr merge` | — |
| F9 | Erster Deploy mit vollem SHA als `image_tag`; Build pusht nur Kurz-SHA, `deploy.yml` nennt das Format nicht | Wissenslücke | niedrig | SURVIVES | Run 36437298152 `image_tag` 40 Zeichen, Folge-Run 36437515448 7 Zeichen; shared-ci `_build-docker.yml` `type=sha,prefix=`; `deploy.yml`-Input „Image-Tag aus GHCR (leer = Commit-SHA dieses Laufs)" | — |
| F10 | Zwei Probe-Ausgaben auf Prod (Lauf 38: 0 Themen + Alarm, Lauf 39: 1 Thema) verbrauchen den Deckel 2/Tag; Report und Board nannten das nicht, M2 ist heute nicht ausführbar | Kommunikation | niedrig | SURVIVES (3b NEU) | dev-hub#403 Kommentar 14:11:50Z („Zusatzausgabe 1/2"), dev-hub#404 Checkpoint 14:40:01Z („2/2 läuft"), news-hub#83 Deckel | — |
| F11 | Zielerreichung überzeichnet: #87 nur per Einzelaufruf geprüft, Kontrollergebnis nicht in #86; D2-Deploy nach Checkpoint „keine weiteren Prod-Schritte" ohne neuen Checkpoint | fehlende Validierung | mittel | SURVIVES (3b NEU) | news-hub#86 ohne Kommentar nach 15:34:48Z; dev-hub#404 Checkpoint 2 14:40:01Z; Deploy-Run 36444702762 | gate-scope-checkpoint-not-durably-recorded-wirkungslos |

F9 ist die in Phase 2.5 aus dem Finder-Konflikt (P2) verifizierte Fassung; F6 bleibt als widerlegte Ursprungsbehauptung stehen.

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 3 | F2, F11 — #403-Kernziel ohne End-to-End-Beleg; R1/R2 ausgerollt, Wirkung offen |
| architektur_design | 4 | F4 — zentraler Fix je Anbieter statt je Aufrufer, Mitschreiber mit Filterlücke |
| code_konventionstreue | 4 | F3 — Werkzeugreibung, Konventionen (Commit, Testnamen) eingehalten |
| risiko_debt | 3 | F1 — offene Doppelung #406/#408; F4 latentes Log-Risiko |
| prozess_effizienz | 3 | F1, F9 — Doppelarbeit, ein vermeidbarer Fehl-Deploy |
| entscheidungsqualitaet | 4 | F9 — Tag-Format geraten statt aus Workflow gelesen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #407 ohne Suche nach offenen Issues/PRs zum selben Pfad angelegt (dev-hub#406 lag 16 min vorher vor) | Vor Fix-PR `gh issue list/pr list --search "<pfad> in:title,body"` im Ziel-Repo; Treffer ⇒ verlinken bzw. „Closes #406" | F1 |
| Checkpoint 14:40 meldet #148 offen, Stand nicht geprüft; E2E-Test nicht als offenes Kriterium geführt | Statuszeile je PR aus `gh pr view --json state` erzeugen; Akzeptanztest als eigene offene Zeile im Ziel-Issue | F2 |
| Edit in frischem Worktree ohne Read | Nach `repo-session.sh start` die Zieldateien einmal lesen, bevor Edits gebündelt werden | F3 |
| Eltern-Cmdline roh geloggt, Test nur für `gh`-Argumente | Nur `argv[0]` + Skriptpfad der Eltern loggen, Test mit Secret-artigem Eltern-Argument | F4 |
| `image_tag` als voller SHA geraten | Tag-Format aus Build-Workflow lesen; `deploy.yml`-Beschreibung um „Kurz-SHA, 7 Zeichen" ergänzen | F9 |
| Probe-Läufe verbrauchten den Deckel, ohne dass Board/Plan das festhielt | Vor einer Probe-Ausgabe den Deckelstand und die Folge („E2E-Test dann erst morgen") ins Board schreiben | F10 |
| Deploy-Kontrolle nur im Chat, #86 ohne Ergebnis; D2 nach „keine weiteren Prod-Schritte" | Kontrollergebnis nach jedem Deploy als Kommentar im Ziel-Issue; neuer Prod-Schritt ⇒ Checkpoint-Nachtrag | F11 |

## 5. Längsschnitt

`tools/retro_kpis.py`: `parallel-session-pr-collision`, `claim-before-cheapest-check` und
`test-asserts-the-case-in-mind-not-the-harmful-one` stehen jeweils ≥2 ⇒ Gate-Pflicht; der
Registry-Abgleich meldet für alle drei ein registriertes Gate oder eine dokumentierte
Owner-Entscheidung (`test-asserts-…` bewusst ohne Gate). `refuted_rate`-Band gesund.

### 5a. Rückfall

`claim-before-cheapest-check` ist **Gate rückfällig** (F2, `gate-claim-before-cheapest-check-wirkungslos`).
Antwort: **ausweiten** — das Gate prüft Zeitangaben, F2 ist eine Zustandsangabe über einen PR.
Umsetzung auf dem bestehenden Issue platform#2666, kein zweites Gate; Edit am Registry-Eintrag
(`revised` + `revision_note` + neue `positivkontrolle`) ist Kandidat, bis er durch
`gate_verankerung_check.py --neu` läuft.

`scope-checkpoint-not-durably-recorded` ist **Gate rückfällig** (F11, erst durch 3b sichtbar,
deshalb nicht in 0.0). Das Gate ist advisory, Rev 9 vom 2026-09-25. Hier lag das Owner-Wort
„D2 go" vor dem Deploy, nur der Checkpoint-Nachtrag fehlte.
**Korrigiert 2026-09-28 (Nachtrag nach Merge):** Die ursprüngliche Diagnose „am Ausgang, herabstufen" war
falsch. Die Ursache liegt **an der Quelle**: Im Transkript meldete sich der Scanner zuletzt um 14:39:52Z,
also vor dem D2-Deploy. Zwischen 15:30 und 16:00Z kam keine Meldung, obwohl `gh workflow run deploy.yml`
nachweislich als Prod-Schritt erkannt wird (`_PROD` in `artefakt_budget.py`).
Hypothese: Fehlerform C sieht Prod schon seit dem ersten Deploy (14:36Z) als berührt an, deshalb zählt ein
zweiter Prod-Schritt nicht als Wachstum.
Antwort: **nachschärfen**. Mit Rev 10 zählt jeder weitere Prod-Schritt nach einem Checkpoint als Wachstum.
Das Owner-Go vom 2026-09-28 galt für „herabstufen", deshalb braucht M8 ein neues Wort.

### 5b. Autonomie-Kalibrierung

over_ask 0, over_act 0. Alle Prod-Schritte mit Owner-Wort vorab (news-hub#84 „R1 Groq + Prod ok",
news-hub#86 „D2 go", dev-hub#404 „Z1 go + Prod ok"); Merges über `pr_merge_sa.py` mit Mandat.

## 6. Verankerung

memory_candidates (kopierfertig, nicht geschrieben):

```markdown
---
name: news-hub-deploy-image-tag-kurz-sha
description: news-hub deploy.yml braucht image_tag als Kurz-SHA (7 Zeichen); voller SHA existiert im GHCR nicht
metadata:
  type: reference
---
Der Build (shared-ci _build-docker.yml, metadata-action type=sha) pusht nur `:<kurzsha>`, `:latest`, `:main`.
Ein Dispatch mit vollem SHA scheitert mit "failed to resolve reference" (Run 36437298152, 2026-09-28).
```

adr_candidates: keine (reine Fixes nach bestehendem Muster).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | #406/#408 gegen #407 auflösen | dev-hub | dev-hub#406 | 🔵 | #406 mit Verweis auf #407 schließen, #408 schließen |
| M2 | #403 End-to-End-Nachweis | dev-hub | dev-hub#403 | 🟢 | Owner: „Lotse neu laden", ab 2026-09-29 „zeitung" im Raum |
| M3 | Gate ausweiten auf Zustandsangaben | platform | platform#2666 | 🔵 | F2 als Fall an #2666 |
| M4 | Mitschreiber: Eltern-Cmdline kürzen + Test | platform | platform#3595 | 🔵 | Folge-Issue, Fix nach Owner-Wort |
| M5 | `deploy.yml`-Input dokumentieren | news-hub | news-hub#87 | 🔵 | Beschreibung „Kurz-SHA" ergänzen |
| M7 | Deploy-Kontrolle in #86 nachtragen | news-hub | news-hub#86 | ✅ | [Kommentar](https://github.com/achimdehnert/news-hub/issues/86#issuecomment-5873744745) |
| M8 | Checkpoint-Gate nachschärfen | platform | platform#3598 | 🟢 | neues Owner-Wort, §5a korrigiert |
| M6 | Streichbahn | platform | — | ✅ | siehe `## Streichbahn` |

## 8. Nicht verifiziert (Restlücken)

- **getan:** R1 (news-hub#85) und R2 (news-hub#87) gemergt und ausgerollt, Prod-Kontrollen grün (Schlüsselprüfung, Hetzner auf Stufe 0); platform#3595 und dev-hub#407 gemergt; alle Prod-Schritte mit Owner-Freigabe vermerkt.
- **angenommen:** Dass der Morgenlauf 2026-09-29 mit ≥3 Themen läuft; Qwen ohne Denken verdrehte im Testsatz den Sinn („einstellen" → „vorgestellt") — Qualitätsfolge für Überschriften offen.
- **nicht verifizierbar:** ob Lauf 38/39 an Leser zugestellt wurden (billigster Check: Zustellstatus in der Prod-DB); wann der Freigabe-Vermerk im Body von news-hub#84 entstand (GraphQL `userContentEdits`); Host-seitiges `DefaultTimeoutStartSec` für den Tageslauf (nicht im Repo); ob #406 aus dieser oder einer parallelen Sitzung stammt (Autor identisch). Billigster Check: Transkripte des Tages nach „issue create" + „venv" greppen.
- **offen geblieben:** M1–M5, M8 (M7 im Retro-Lauf erledigt); #404 Bausteine A, C2, D (D bis 2026-10-05); die sechs rückfälligen Gates ohne Vorkommen hier wurden nicht entschieden.

## Widerlegung

Opus-Subagent, frischer Kontext, sah Entwurf + Artefaktliste + Kennzahlen. Alle fünf SURVIVES und
alle vier REFUTED **BESTAETIGT** (Zeitstempel und Dateistellen neu gezogen); Footprint-Reduktion
deep→full **BESTAETIGT** — Freigabe-Vermerke liegen vor den Prod-Schritten (Z1 13:44 vs. 14:11,
D2 15:34:48 vs. Deploy 15:35:11). **NEU:** F10 (Probe-Ausgaben verbrauchen Deckel) und F11
(Zielerreichung überzeichnet). Ergebnis: 0 gekippt, 2 neu.

## Self-Review

Meta-Prüfung durch einen Sonnet-Subagenten, der nur den Report gegen die Skill-Regeln prüfte. Drei Formbefunde, alle übernommen:
(1) Executive Summary hatte 6 Bullets, jetzt 5.
(2) F11 fehlte in der Summary, jetzt drin, F9 dafür gestrichen.
(3) Budgetüberschreitung, jetzt oben ausgewiesen.
Ohne Befund: Frontmatter, `refuted_rate` 4/11, Zählung 11/7, Invariante 7 = 7, Scorecard-Anker, Tabellenkopf, Vierklang, keine Secrets und keine Personendaten.

## Streichbahn

Keiner. Die Silent-Reminder-Kennzahl des Transkript-Skripts erzeugte hier einen Fehlbefund (F7:
sichtbare Werkzeugaufrufe zählen nicht als Text); das ist ein Kalibrierungsfall, keine der vier
Belegarten — erstes Vorkommen, bei Wiederholung als Streichkandidat „kein Effekt" prüfen.
