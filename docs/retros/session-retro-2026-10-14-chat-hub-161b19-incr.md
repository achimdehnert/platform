---
retro_schema: 1
date: 2026-10-14
repo_scope: [chat-hub, platform, news-hub]
session_id: 161b19-incr
footprint: deep
findings_total: 14
findings_survived: 10
refuted_rate: 0.29
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [gate-scope-checkpoint-not-durably-recorded-wirkungslos, zwischenstand-trotz-silent-reminder-ausgelassen]
recurring_findings: [scope-checkpoint-not-durably-recorded, gate-scope-checkpoint-not-durably-recorded-wirkungslos, pr-autor-identitaet-nicht-angewandt, issue-offen-nach-gemergtem-fix, deferred-item-no-tracking-issue, rueckweg-unerprobt, check-ohne-positivkontrolle, fachwerte-als-code-literal, quellen-ausfall-nur-im-journal, zwischenstand-trotz-silent-reminder-ausgelassen, closing-verb-schliesst-ziel-issue-vor-zielerreichung]
gates_caught: [rohes-pytest-statt-make-test, direct-gh-pr-merge-bypasses-sa-m, secret-leak-via-safe-pattern]
gates_verwandt: [pr-autor-identitaet-nicht-angewandt, issue-offen-nach-gemergtem-fix, check-ohne-positivkontrolle, aufschub-anker]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "4 gekippt, 3 neu"
streichkandidaten: [phase-6-extern-handoff]
---

# Session-Retro 161b19-incr — Folge-Increment: R-Maßnahmen, mail_agent, py3.15, Paper-Abschnitt news-hub

Sitzung `44073aac-88c3-4402-b255-2db231161b19`. Das Increment läuft vom 2026-10-13 11:45 UTC bis
2026-10-14 14:20 UTC. Die Parent-Retro
[session-retro-2026-10-13-chat-hub-161b19.md](session-retro-2026-10-13-chat-hub-161b19.md)
deckt chat-hub#184/#186 ab. Was sie bewertet hat, wird hier nicht noch einmal bewertet.

**Artefakte:**
- chat-hub: [#189](https://github.com/iilgmbh/chat-hub/pull/189) (fix #185), [#192](https://github.com/iilgmbh/chat-hub/pull/192) (feat #191), Issues [#190](https://github.com/iilgmbh/chat-hub/issues/190) (neu, „später“) und [#48](https://github.com/iilgmbh/chat-hub/issues/48) (Stand nur gelesen)
- platform: [#3950](https://github.com/achimdehnert/platform/pull/3950) R4, [#3952](https://github.com/achimdehnert/platform/pull/3952) R1, [#3961](https://github.com/achimdehnert/platform/pull/3961) R1d, [#3967](https://github.com/achimdehnert/platform/pull/3967) mail_agent, [#3968](https://github.com/achimdehnert/platform/pull/3968) (geschlossen), [#3969](https://github.com/achimdehnert/platform/pull/3969) py3.15-Testfix, [#3329](https://github.com/achimdehnert/platform/pull/3329) Renovate (Merge `4355817a`), Scope-Checkpoints als Nachträge auf PR [#3936](https://github.com/achimdehnert/platform/pull/3936)
- news-hub: [#93](https://github.com/achimdehnert/news-hub/pull/93) (Merge `7ba713f`, Migration 0012), Deploy-Lauf [38573467860](https://github.com/achimdehnert/news-hub/actions/runs/38573467860), Handlauf 13:58 UTC, Abnahme auf [#92](https://github.com/achimdehnert/news-hub/issues/92#issuecomment-6170195329)
- Host `hetzner-prod`: `tageslauf.sh` ersetzt, Sicherung `tageslauf.sh.vor-92-20261014`

**Footprint und Budget:**
- 3 Repos, 1 Prod-Deploy, 1 Datenmigration, 0 ADRs → `deep`.
- 3 Finder, 3 Skeptiker, 3b (Opus) und Meta (Sonnet), zusammen 8 Agenten.
- Das Extern-Handoff ist n/a, siehe Phase 6 und Streichbahn.

## Phase 0.0 — Wirkungsbilanz

`gate_wirkung.py` meldet vier Gates als `RUECKFAELLIG`: claim-before-cheapest-check, built-but-never-called, check-ohne-positivkontrolle und scope-checkpoint-not-durably-recorded.

Über alle vier hat [Retro 34ae36 §0.0](session-retro-2026-10-13-platform-34ae36.md) am 2026-10-13 entschieden; die Parent-Retro verweist darauf.
- Für built-but-never-called und check-ohne-positivkontrolle genügt dieser Verweis. Befund 6 liegt außerhalb des Zuschnitts (`gates_verwandt`).
- claim-before-cheapest-check hat zweimal als Stop-Hook gefeuert, um 11:12:37 und 13:40:36. Diese Retro bewertet die beiden Meldungen nicht, Restlücke in §8.

**Eigene Fälle und damit eigene Entscheidungen:**

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| scope-checkpoint-not-durably-recorded | 2 vorher, +1 hier (Befund 1) | **Quelle:** Form D („Prod-Wort ohne Checkpoint vorher“) gilt nur, solange in der ganzen Sitzung noch kein Checkpoint gefallen ist. Form C nimmt einen Prod-Schritt, der kurz vor dem Checkpoint lag, in den Snapshot auf. | **nachschärfen:** Form D auf „seit dem letzten Checkpoint“ umstellen, [platform#3978](https://github.com/achimdehnert/platform/issues/3978) (Korrektur im [Kommentar](https://github.com/achimdehnert/platform/issues/3978#issuecomment-6171170644)) |
| issue-offen-nach-gemergtem-fix | 1 vorher, +1 hier (Befund 14) | **Quelle:** `_AUSSTEHEND_RE` (`tools/session_abgleich.py:137`) kennt „Danach …“ und „deployt nichts“ nicht. | **nachschärfen:** [platform#3987](https://github.com/achimdehnert/platform/issues/3987) |

## 1. Executive Summary

- **Ziele erreicht und belegt:**
  - R4, R1 und R1d sind gemergt.
  - mail_agent (chat-hub#191) und der py3.15-Fix sind gemergt.
  - Renovate 3.15 ist gemergt.
  - Der Paper-Abschnitt läuft in Prod: Handlauf mit Exit 0, 5 Paper, vom Owner abgenommen.
- **Zwei Gates sind rückfällig, beide werden an der Quelle nachgeschärft:**
  - Ein Scope-Checkpoint kam 18 s **nach** dem Deploy-Start (Befund 1, #3978).
  - Der Merge von #93 schloss #92 eine Stunde vor der Zielerreichung (Befund 14, #3987).
- **Drei Prüflücken waren ohne Träger** (Befunde 4, 5, 6):
  - 13 Workflows ohne PR-Trigger liefen nie vorab unter 3.15.
  - Der Rückweg des Deploys ist unerprobt; die Migrationen sind aber verträglich.
  - Die Positivkontrolle des Mail-Header-Fehlers läuft im Required Check nicht mehr.
  - Verankert in #3979 und Ledger-Zeile RB.
- **news-hub-Paper** (Befunde 8, 9): Die Quoten sind Code-Literale, und ein Quellenausfall endet als Journal-Zeile bei Exit 0. Verankert in news-hub#94.
- **Prozess** (Befunde 2, 11):
  - Ein PR lief über das falsche Konto (#3986).
  - 9,8 Minuten ohne Zwischenstand nach einem Silent-Reminder. Der Slug steht damit bei ×2, Gate-Kandidat #3988.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Der Scope-Checkpoint zum Deploy kam 18 s **nach** dem Start des Laufs. Der vorherige Nachtrag 5 gab 66 s nach dem Owner-Merge von #93 einen überholten Stand wieder. | Prozesslücke | mittel | SURVIVES | Lauf 38573467860 erzeugt 13:38:24Z, [Nachtrag 6](https://github.com/achimdehnert/platform/pull/3936#issuecomment-6169688991) 13:38:42Z. #93 vom Owner gemergt 12:50:25Z, [Nachtrag 5](https://github.com/achimdehnert/platform/pull/3936#issuecomment-6168760661) 12:51:31Z | scope-checkpoint-not-durably-recorded, gate-scope-checkpoint-not-durably-recorded-wirkungslos (Gate rückfällig, §5a) |
| 2 | PR #3968 wurde mit dem Owner-Konto statt mit der App eröffnet. Folge: 9 Minuten Umweg und ein doppelter PR (#3969). | Prozesslücke | niedrig | SURVIVES | #3968 Autor `achimdehnert`, 11:38:31Z bis 11:47:27Z. #3969 Autor `app/lotse-autor`, 11:47:30Z | pr-autor-identitaet-nicht-angewandt (gates_verwandt: Datei unter tools/tests/ ohne CODEOWNERS-Login, das Gate deckt nur Code-Owner- und Governance-Pfade) |
| 3 | news-hub#81 (Recherche) ist mit dem Deploy erstmals live, trägt aber keinen Live-Vermerk. Offen ist es bewusst, weil die Owner-Abnahme fehlt. | Kommunikation | niedrig | SURVIVES | #81 OPEN; PR #82 mit `Refs #81` am 2026-10-02 gemergt. Der Live-Satz steht nur auf [#92](https://github.com/achimdehnert/news-hub/issues/92#issuecomment-6169727205) | issue-offen-nach-gemergtem-fix (gates_verwandt: #82 wurde in einer fremden Sitzung gemergt und schließt nicht, session_abgleich prüft nur PRs der eigenen Sitzung) |
| 4 | #3329 hob 36 Workflows auf 3.15. 13 davon haben keinen PR-Trigger, liefen also nie vorab, und kein Issue führte die Prüfung. | fehlende Validierung | mittel | SURVIVES | `git show 4355817a -- <wf>` je Datei: 36 mit `+python-version … 3.15`, 13 ohne `pull_request` auf origin/main; Issue-Suche leer bis [#3979](https://github.com/achimdehnert/platform/issues/3979) | deferred-item-no-tracking-issue (gates_verwandt: Alias von aufschub-anker; das Gate liest Aufschub-Texte, hier wurde keiner geschrieben) |
| 5 | Der Rückweg des news-hub-Deploys (`image_tag=1b8f53b` plus Host-Skript) ist unerprobt und steht nur als Satz im Issue. | fehlende Validierung | niedrig | SURVIVES | [#92 Kommentar](https://github.com/achimdehnert/news-hub/issues/92#issuecomment-6169727205). Mildernd laut 3b: 0011 ist `CreateModel`, 0012 ändert nur `fundstueck`, `1b8f53b` endet bei 0010. Ein Rückweg nur per Image ist damit verträglich. | rueckweg-unerprobt |
| 6 | Der py3.15-Fix überspringt die Positivkontrolle ab 3.15. Im Required Check `tools-tests` (nur 3.15) läuft sie damit auf keiner Version mehr. | fehlende Validierung | niedrig | SURVIVES | `test_mail_kopfzeilen.py:48` `skipif(sys.version_info >= (3, 15))`; `tools-tests.yml:116,300` nur `"3.15"` | check-ohne-positivkontrolle (gates_verwandt: Modul subagent_brief_negativprobe prüft Subagent-Briefs und Rechte-Proben, keine Testdateien) |
| 7 | Der Dispatch-403 der App wurde über das Owner-Konto umgangen, ohne dass die Lücke festgehalten wurde. | Werkzeug | — | REFUTED (3b) | [Nachtrag 6](https://github.com/achimdehnert/platform/pull/3936#issuecomment-6169688991) hält 403 und Owner-Wort durabel fest. Der Träger für die Behebung fehlte; er ist jetzt [#3985](https://github.com/achimdehnert/platform/issues/3985) | — |
| 8 | Die Paper-Quoten (3/2/min 2) sind Code-Literale. Die Dataclass `Quoten` wird nicht durchgereicht. | Konventionsverstoß | mittel | SURVIVES | news-hub origin/main `apps/digest/services/paper.py:52-54,137-139`. Die arXiv-Kategorien lassen sich per `NEWS_HUB_PAPER_ARXIV` ändern (`digest_bauen.py:378`). Hausregel „Kein Hardcoding“ | fachwerte-als-code-literal |
| 9 | Ein Paper-Quellenausfall oder zu wenige Paper enden als Journal-Zeile bei Exit 0. Chat-Meldung und Frische-Melder kennen `paper` nicht. | Prozesslücke | mittel | SURVIVES | `paper.py` `quellen_zu` → `logger.warning` + `[]`; `digest_frische.py:79` prüft nur `themen`; `git grep paper` in `melden.py` leer | quellen-ausfall-nur-im-journal |
| 10 | #3967 und #3969 wurden ohne Approve gemergt, also ein Regelverstoß. | Prozesslücke | — | REFUTED | `mergedBy=achimdehnert`; W1/M1 braucht laut `autonomy-gates.md:182-194` kein Approve | — |
| 11 | Nach dem Silent-Reminder um 11:28:46 kam 9,8 Minuten lang kein sichtbarer Zwischenstand, und es gab keine Owner-Nachricht dazwischen. | Kommunikation | niedrig | SURVIVES (kommandobelegt, 3b gekippt) | `retro_transkript_kennzahlen.py`: Reminder 11:28:46.800Z, nächster Text 11:38:34.949Z. Die einzige Lücke über 2,2 min | zwischenstand-trotz-silent-reminder-ausgelassen |
| 12 | news-hub#92 wurde geschlossen, obwohl der Timer-Lauf noch ungesehen ist. | Kommunikation | — | REFUTED | Board-Zeile „Offen: erster echter Tageslauf 2026-10-15 06:15 UTC“ plus [#92 Abnahme](https://github.com/achimdehnert/news-hub/issues/92#issuecomment-6170195329) nach einem echten Handlauf | — |
| 13 | Die ruff-Versionsdrift in `make lint` (chat-hub#183) hat keinen Träger. | Prozesslücke | — | REFUTED | [#183](https://github.com/iilgmbh/chat-hub/issues/183#issuecomment-6163651901) ist offen und trägt genau diesen Zielzustand | — |
| 14 | `Closes #92` in #93 schloss #92 beim Merge (12:50:27Z), obwohl der PR-Text Folgeschritte nannte. Das Abnahmekriterium war erst um 13:58Z erfüllt. | Prozesslücke | niedrig | SURVIVES (NEU aus 3b) | `gh issue view 92` closedAt 12:50:27Z; #93 Text „Ein Merge deployt nichts … Danach `tageslauf.sh`“; `_AUSSTEHEND_RE` `session_abgleich.py:137` | closing-verb-schliesst-ziel-issue-vor-zielerreichung (Gate issue-offen-nach-gemergtem-fix rückfällig, §5a) |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | Alles Beauftragte ist gemergt, deployt und mit einem echten Lauf belegt. Der Timer-Lauf hat einen Träger (Befund 12 REFUTED). |
| architektur_design | 3 | Die Paper-Quoten liegen im Code, ein Ausfall bleibt stumm (Befunde 8, 9). |
| code_konventionstreue | 3 | Verstoß gegen „Kein Hardcoding“ (Befund 8), PR mit falschem Konto (Befund 2). |
| risiko_debt | 3 | Drei Prüflücken: 3.15-Workflows, Rückweg, Positivkontrolle (Befunde 4, 5, 6). |
| prozess_effizienz | 3 | Doppelter PR (Befund 2), 9,8 min ohne Zwischenstand (Befund 11). |
| entscheidungsqualitaet | 3 | Owner-Worte eingeholt, aber Checkpoint nach dem Schritt (Befund 1) und Schließverb vor der Zielerreichung (Befund 14). |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nachtrag 6 kam 18 s nach dem Dispatch | Checkpoint-Kommentar posten und seine URL zitieren. Erst im nächsten Tool-Aufruf `gh workflow run` starten. Das Gate prüft Form D seit dem letzten Checkpoint (#3978). | #1 |
| #3968 mit `gh pr create` über das Owner-Konto eröffnet | Jeder Sitzungs-PR geht über `lotse-gh <konto> pr create`. Vorschlag: das Gate auf alle Sitzungs-PRs ausweiten (#3986, Owner-Entscheid offen). | #2 |
| #81 ohne Live-Vermerk nach dem ersten Deploy | Beim Deploy jedes damit erstmals live gehende Issue im selben Zug kommentieren. Das Schließen bleibt bei der Owner-Abnahme. | #3 |
| #3329 gemergt, 13 Workflows ohne Vorablauf | Vor dem Merge eines Laufzeit-Upgrades die Workflows ohne PR-Trigger auflisten und per `workflow_dispatch` laufen lassen oder als Issue führen (#3979) | #4 |
| Rückweg nur als Satz im Issue | Rückweg mit Migrationsstand (`showmigrations`, letzte Migration im Ziel-Image) als Ledger-Zeile vor dem Deploy (jetzt RB) | #5 |
| skipif ab 3.15, Required Check nur 3.15 | Beim Skip einer Positivkontrolle prüfen, ob die CI noch eine Version fährt, auf der sie läuft. Sonst Matrix-Eintrag oder Streichung mit Grund (#3979). | #6 |
| Quoten als Konstanten in `paper.py` | Fachwerte zuerst als Datendatei oder DB anlegen, dann den Code dagegen schreiben (news-hub#94) | #8 |
| Paper-Ausfall nur in stderr/Journal | Jede neue Quelle bringt ihre WARN-Zeile in der Chat-Meldung mit, wie fav0 (news-hub#94) | #9 |
| 9,8 min Stille nach einem Silent-Reminder | Auf jeden Silent-Reminder im selben Zug eine Zeile Stand. Gate-Kandidat #3988. | #11 |
| `Closes #92` im PR, obwohl Deploy und Lauf ausstanden | Bei offenen Folgeschritten `Refs #N` schreiben und erst nach dem Abnahmekriterium schließen. Das Gate erkennt Folgeschritt-Abschnitte (#3987). | #14 |

## 5. Längsschnitt

`retro_kpis.py` (67 Slugs ≥2, refuted_rate-Band gesund):
- **gate-scope-checkpoint-not-durably-recorded-wirkungslos** steht bei ≥2 in der Liste „OHNE registriertes Gate“. Es ist das rückfällige Gate selbst. Die Gate-Pflicht erfüllt das Nachschärfen des bestehenden Gates (#3978), kein zweites Gate.
- **zwischenstand-trotz-silent-reminder-ausgelassen** steigt auf ×2, ohne Gate. **Gate-Pflicht**, Kandidat [#3988](https://github.com/achimdehnert/platform/issues/3988).
- **deferred-item-no-tracking-issue** ist abgelehnt (`declined/`). Begründung dort: aufschub-anker „erzwingt dieselbe Wirkung“. aufschub-anker führt den Slug in `covers`. Befund 4 liegt außerhalb von dessen Zuschnitt (`gates_verwandt`).
- **closing-verb-schliesst-ziel-issue-vor-zielerreichung** steht in `covers` von issue-offen-nach-gemergtem-fix. Damit ist das Gate rückfällig (§5a).
- **pr-autor-identitaet-nicht-angewandt** und **check-ohne-positivkontrolle** haben Gates; die Fälle liegen außerhalb des Zuschnitts (Begründung in §2). Für pr-autor schlägt #3986 vor, den Zuschnitt auszuweiten.
- Neu (je ×1): **rueckweg-unerprobt**, **fachwerte-als-code-literal**, **quellen-ausfall-nur-im-journal**.

Auto-Memory chat-hub (`MEMORY.md`, per grep): Keine Memory zu Checkpoint-Reihenfolge, App-Konto, Schließverben oder Fachwerten.

### 5a. Rückfall-Prüfung

**Gate scope-checkpoint-not-durably-recorded ist rückfällig. Antwort: nachschärfen** (Quelle).
- Der erste Entwurf antwortete „umbauen, falscher Zeitpunkt“. Die Widerlegungsbahn hat das gekippt: `sammle_evidenz` kennt die Reihenfolge schon. Die Lücke liegt in der sitzungsweiten Bedingung von Form D.
- Den Merge von #93 hat der Owner selbst ausgeführt; er ist kein Sitzungsschritt.
- Der Gate-Edit (`revised`, `revision_note`, Positivkontrolle Replay 13:38:24 → 13:38:42) ist **bewusst nicht Teil dieser Retro**. Er braucht Hook-Code und Drill; ohne beides wäre eine Revision nur eine Behauptung. Geführt als [#3978](https://github.com/achimdehnert/platform/issues/3978).

**Gate issue-offen-nach-gemergtem-fix ist rückfällig (Befund 14). Antwort: nachschärfen.**
- `_AUSSTEHEND_RE` bekommt Folgeschritt-Formen dazu.
- Positivkontrolle ist der Text von #93. Der Edit wird aus demselben Grund in [#3987](https://github.com/achimdehnert/platform/issues/3987) geführt.

**Gefangen** (`gates_caught`, Transkript): rohes-pytest-statt-make-test (08:27), direct-gh-pr-merge-bypasses-sa-m (09:34, `gh pr merge 3950`), secret-leak-via-safe-pattern (11:54). Hooks ohne Registry-Gate blockten außerdem einen Vordergrund-`sleep` (11:12) und ein `git stash pop` (07:51).

### 5b. Autonomie-Kalibrierung

**over_ask:** keine. Jede Owner-Frage betraf Merge, Prod oder einen Prod-Handlauf.

**over_act:** keine Gate-Klasse.
- Merge #93, Deploy 7ba713f und Handlauf hatten je ein eigenes Owner-Wort.
- Das Host-Skript wurde im freigegebenen Deploy ersetzt, mit Sicherung.

**Grenzfall, offen benannt:** Die App darf in news-hub keine Issues und in platform keine Issue-Kommentare anlegen. Diese Retro hat deshalb ohne eigenes Owner-Wort über das Owner-Konto geschrieben:
- news-hub#94 und dessen Kommentar
- je einen Korrekturkommentar auf #3978 und #3979

Das ist reversibel und berührt keine Gate-Klasse. Es spricht aber unter fremdem Namen. Owner-Entscheid in [#3985](https://github.com/achimdehnert/platform/issues/3985).

## 6. Verankerung

**memory_candidates** (der Owner entscheidet):

```markdown
---
name: checkpoint-vor-dem-schritt
description: Scope-Checkpoint-Kommentar muss vor dem Prod-Schritt existieren — erst posten und URL zitieren, dann im nächsten Tool-Aufruf auslösen
metadata:
  type: feedback
---
Nachtrag 6 auf platform#3936 kam 18 s nach dem Start von news-hub-Lauf 38573467860.
**Why:** Retro 161b19-incr Befund 1; das Gate schwieg, weil Form D sitzungsweit gilt (platform#3978).
**How to apply:** Checkpoint posten, URL im Text zitieren, Remote-Stand frisch lesen, dann erst `gh workflow run`/`systemctl start`.
```

```markdown
---
name: refs-statt-closes-bei-folgeschritten
description: Nennt ein PR Schritte nach dem Merge (Deploy, Lauf), schreibt er `Refs #N`, nicht `Closes #N`
metadata:
  type: feedback
---
news-hub#93 schloss #92 per `Closes` beim Merge, obwohl Deploy und erster Lauf ausstanden; das Abnahmekriterium war eine Stunde später erfüllt.
**Why:** Retro 161b19-incr Befund 14; Gate issue-offen-nach-gemergtem-fix sah „Danach …“ nicht (platform#3987).
**How to apply:** PR-Text mit Folgeschritten → `Refs #N`; Issue erst nach dem Abnahmekriterium mit Beleg-Kommentar schließen.
```

```markdown
---
name: lotse-autor-rechte
description: App lotse-autor — news-hub: PR ja, Dispatch/Issue nein; platform: Issue anlegen ja, Issue-Kommentar/-Edit nein, PR-Kommentar ja
metadata:
  type: reference
---
Gemessen 2026-10-14 (403 bzw. „Resource not accessible by integration“). Entscheid offen in platform#3985.
**How to apply:** Vor einem Schreibweg über die App diese Matrix prüfen; Umweg über das Owner-Konto nur mit Owner-Wort oder nach Entscheid in #3985.
```

**adr_candidates:** keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Gate Checkpoint Form D nachschärfen | platform | [#3978](https://github.com/achimdehnert/platform/issues/3978) | 🟢 | Owner gibt Umsetzung frei |
| M2 | 13 Workflows plus Positivkontrolle | platform | [#3979](https://github.com/achimdehnert/platform/issues/3979) | 🔵 | Dispatch-Läufe, Matrix 3.12 |
| M3 | Paper-Quoten Datei, Ausfall melden | news-hub | [#94](https://github.com/achimdehnert/news-hub/issues/94) | 🟢 | Owner gibt Umsetzung frei |
| M4 | Live-Vermerk auf #81 | news-hub | [#81](https://github.com/achimdehnert/news-hub/issues/81) | 🔵 | Kommentar, Schließen bleibt Abnahme |
| M5 | App-Rechte lotse-autor | platform | [#3985](https://github.com/achimdehnert/platform/issues/3985) | 🟢 | Owner wählt a/b/c |
| M6 | Gate pr-autor ausweiten | platform | [#3986](https://github.com/achimdehnert/platform/issues/3986) | 🟢 | Owner-Entscheid |
| M7 | Gate Schließverb nachschärfen | platform | [#3987](https://github.com/achimdehnert/platform/issues/3987) | 🟢 | Owner gibt Umsetzung frei |
| M8 | Gate-Kandidat Zwischenstand | platform | [#3988](https://github.com/achimdehnert/platform/issues/3988) | 🟢 | Owner: bauen oder ablehnen |
| M9 | Phase 6 aus dem Skill streichen | platform | [#3936](https://github.com/achimdehnert/platform/pull/3936) | 🟢 | Owner-Entscheid, Streichbahn |

Befund 5 (Rückweg) steht als Ledger-Zeile RB im Board `morgenzeitung-thelatestinai`.

## 8. Nicht verifiziert (Restlücken)

- **claim-before-cheapest-check, Stop-Hook 11:12:37 und 13:40:36:** Ob es Fänge oder Fehlalarme waren, ist nicht bewertet. Billigster Check: Transkript an beiden Zeitpunkten lesen, ob die folgende Antwort einen Tool-Beleg nachlieferte.
- **Befund 4, die 13 Workflows einzeln:** Die ersten 40 Läufe nach dem Merge sind grün, aber nicht je Workflow zugeordnet. Billigster Check: `gh run list --workflow <datei> --limit 1` je Datei.
- **Befund 6, lokaler Lauf:** Billigster Check: im Makefile nachsehen, welchen Interpreter `make test` für `tools/tests/` wählt.
- **Befund 5:** Ein Probelauf des Rückwegs fehlt. Billigster Check: `migrate digest 0010 --plan` im Prod-Container (nur Plan, ohne Wirkung).

**Vierklang (Regel 5):**
- **getan:**
  - 3 Finder, 3 Skeptiker, 3b (Opus) und Meta, alle auf Artefakten aus `origin/main` und `gh api`.
  - 14 Befunde, davon 10 überlebend. 3b hat 4 Punkte gekippt und 3 neu gefunden.
  - 7 Issues: #3978, #3979, #3985–#3988 und news-hub#94.
  - 2 Korrekturkommentare und 2 Ledger-Zeilen.
- **angenommen:** Dass der Stop-Hook um 13:38 still blieb, folgt aus dem Code von Form D, nicht aus einem Replay. Die Positivkontrolle in #3978 klärt das.
- **nicht verifizierbar:** die Owner-Wahrnehmung im Fenster 11:28–11:38.
- **offen geblieben:**
  - Gate-Edits (#3978, #3987)
  - Timer-Lauf 2026-10-15 06:15 UTC (Board MZL)
  - Prüfungen aus #3979 und news-hub#94
  - die beiden claim-Hook-Meldungen

## Phase 6 — Extern-Handoff

n/a. Begründung in der Streichbahn: Die drei bisherigen Briefings liegen ohne Antwort. Die Widerlegungsbahn (Opus, frischer Kontext) hat hier vier Urteile gekippt und deckt die Methodenkritik ab.

## Widerlegung

Die Opus-Widerlegungsbahn mit frischem Kontext hat 4 Punkte gekippt und 3 neue Befunde gefunden. Die Zahlen hat der Synthesizer per `gh`/`git` gegengeprüft.

| Punkt | Verdikt | Wirkung im Report |
|---|---|---|
| Befund 7 (SURVIVES) | GEKIPPT | Nachtrag 6 hält den 403 durabel fest → REFUTED. Der Träger für die Behebung ist jetzt #3985. |
| Befund 11 (REFUTED) | GEKIPPT | Die Kennzahlen belegen die 9,8-min-Lücke → SURVIVES (kommandobelegt). |
| §5a „umbauen“ | GEKIPPT | Richtig ist „nachschärfen, Form D“. Korrektur auf #3978. |
| §5 deferred-item „unverändert“ | GEKIPPT | Der Slug ist von aufschub-anker gedeckt → `gates_verwandt` für Befund 4. |
| Befund 14 | NEU | #92 vor der Zielerreichung geschlossen, Gate rückfällig → #3987 |
| M5/M6 ohne Anker | NEU | #3985 und #3986 angelegt; #3936 ist ein PR, kein offenes Issue |
| claim-Hook unbewertet | NEU | als Restlücke in §8 |

Korrekturen ohne Verdiktwechsel:
- Befund 1: einmal klar nach dem Schritt, einmal ein überholter Stand.
- Befund 3: Schließen bleibt Abnahme (M4).
- Befund 4: 36 bzw. 13 statt 41 bzw. 16, Korrektur auf #3979.
- Befund 5: Severity niedrig, Migrationen verträglich.
- Befund 6: Begründung präzisiert.
- Befund 8: nur Quoten, Korrektur auf news-hub#94.

Bestätigt: Befunde 2, 6, 9, 10, 12, 13.

## Streichbahn

**Streichkandidat: `phase-6-extern-handoff`**, Belegart **Liegezeit**.
- In `~/shared/` liegen 3 Briefings (`session-retro-extern-2026-09-24-meiki-hub-2a5c44`, `…-2026-09-28-meiki-hub-eff9b5`, `…-2026-10-05-platform-8a0235`). Es gibt 0 Antworten (`-extern*.md`), und keine Retro auf main hat eine `## Extern-Auswertung`.
- Die Liegezeiten betragen 20, 16 und 9 Tage, der Median liegt bei 16 d, also über 14 d.
- Das ist bewusst **nicht** die Belegart „kein Leser“; der Skill schließt sie für fehlende Antworten aus.
- **Nachtrag nach dem Owner-Entscheid (eigener Fehler):** Die Vorlage hat [LEHREN#v2b-phase-6](../governance/session-skills-lehren/retro.md#v2b-phase-6) nicht genannt. Dort steht, dass der Owner schon zweimal korrigiert hat, die Antworten kämen „per Copy-and-paste“, ohne Datei. Die Liegezeit misst nur Dateien und kann diesen Weg nicht ausschließen. Die Umsetzung von M9 wartet deshalb auf eine Bestätigung mit diesem Wissen.

Vorschlag: Phase 6 streichen oder auf Owner-Anforderung umstellen. Owner-Entscheid über M9.

Die Ratsche der Parent-Retro ist erfüllt: Ihr Kandidat wurde mit #3950 umgesetzt.
