---
retro_schema: 1
date: 2026-10-08
repo_scope: [platform, billing-hub, pptx-hub, travel-beat, mcp-hub, odoo-hub, risk-hub, shared-ci, tax-hub, illustration-hub, dms-hub, learn-hub, cad-hub, weltenhub, trading-hub, writing-hub]
session_id: 3b46a0
footprint: deep
findings_total: 17
findings_survived: 10
refuted_rate: 0.41
phase3_refuted: 7
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [deploy-job-skipped-als-erfolg, betriebsstatus-vor-repo-arbeit, bot-konfig-pilot-vor-flotte]
recurring_findings: [deploy-green-not-prod-healthy, repo-betriebsstatus-vor-arbeit-ungeprueft, bot-konfig-ohne-verhaltensprobe-ausgerollt, hausdaten-hardcoded-org-liste, commit-praefix-gemischt, repo-datei-per-bash-statt-edit, edit-in-worktree-without-read, hook-block-wiederholt-gleiches-muster, zweitziel-ohne-messung, ledger-zaehlung-veraltet-durch-bot-zufluss, gleichartige-bot-prs-einzeln-gemergt]
gates_caught: [claim-before-cheapest-check, gh-body-file-leer-ueberschrieben]
gates_verwandt: ["inline-heredoc-quoting-rework: Gate faengt Quoting-Rework in gh-Argumenten; hier wurde eine Repo-Datei per Python-Heredoc geaendert, ohne Quoting-Fehler und ohne Rework, ausserhalb des Zuschnitts"]
over_ask_klassen: []
over_act_klassen: [repo-einstellung-patch-ohne-owner-zug]
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: [retro-0.0-wiederholt-bestehenden-beschluss]
---

# Session-Retro 3b46a0 — PR-Bestand auf das notwendige Maß (#3812)

Sitzung 2026-10-06 12:40 UTC → 2026-10-08 03:40 UTC. Scope über die 14 Leases mit
`claude_session` 3b46a028 (Branches `session/2026-10-0[67]/achim-dehnert/*`), die Merges und
Schließungen fremder PRs laut Ledger in #3812 und das Transkript, nicht über den Kalendertag.
Methode: 3 Finder (sonnet, frischer Kontext) → 3 Skeptiker (sonnet, gebündelt je Dimension, nur
Bewertungsbefunde) → Widerlegungsbahn (Opus) → Meta-Review (sonnet). Agenten: 8. Footprint
`deep` (16 Repos, Prod-Deploys u. a. in billing-hub, pptx-hub, trading-hub, writing-hub), keine
Reduktion.

Sitzungsziel (Owner-Wortlaut): „PR sind alle gemerged oder gelöscht wenn nicht mehr notwendig
(überflüssig wegen "Alters"); unnötige merges und approves sind beseitigt, merges / approves sind
auf das tatsächlich notwendige Maß (keine redaktion, keine erneuten Läufe wegen commit hinter
main, ....) reduziert“. Zielzustand: [#3812](https://github.com/achimdehnert/platform/issues/3812)
K1–K4.

## 0. Wirkungsbilanz (Phase 0.0)

`tools/gate_wirkung.py` meldet drei rückfällige Gates. Für alle drei liegt ein Beschluss aus
früheren Retros vor. Diese Sitzung bringt bei keinem einen neuen Rückfall. Der letzte Rückfall von
built-but-never-called am 2026-10-07 stammt aus den Retros anderer Sitzungen (8be895-incr, 767d40,
6189d3).

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| built-but-never-called | 3 | Quelle | **ausweiten**, Beschluss Owner-Wort „187 go“ (Retro `0405d4`); hier kein Vorkommen |
| claim-before-cheapest-check | 3 | Quelle | **nachschärfen**, Beschluss [#2666](https://github.com/achimdehnert/platform/issues/2666) (Retro `728cf0-incr`); hier zweimal **gefangen** (Bash-Hook 2026-10-07T14:21Z, Stop-Hook 2026-10-08) |
| worktree-midsession-accumulation | 2 | Ausgang | **herabstufen**, Beschluss Retro `4f385c-incr2` M6; hier kein Vorkommen: kein Worktree der 14 Sitzungs-Branches besteht noch (`git worktree list` in 7 Repos) |

⏰ Verfallsfrist `inline-heredoc-quoting-rework`: Die Gate-Datei führt `expires: 2026-10-21` und
`mode: advisory` (Zeilen 3 und 13). R8 ([#3841](https://github.com/achimdehnert/platform/pull/3841))
hat nur das Kalibrierfenster aufgegeben, nicht die Frist. Bis 2026-10-21 muss der Eintrag also
blocking geschaltet oder gestrichen werden. „Advisory ohne Frist“ ist kein zulässiger Endzustand.
Owner-Entscheid, Maßnahme M6.

## 1. Executive Summary

- K1 ist nahezu erreicht: 32 offene PRs ohne archivierte Repos, alle bis auf einen mit Gate-Grund im Ledger. Die Ausnahme ist risk-hub#827 (Renovate, 01:36Z). Der PR bestand schon vor der letzten Ledger-Zählung um 03:25Z und wurde dort nicht erfasst (#13).
- Größter Fehler: PR-Arbeit an travel-beat, das seit 2026-08-30 stillgelegt war. Dazu kam eine öffentliche Meldung „Deploy success“ für einen Lauf, in dem der Deploy-Job übersprungen wurde (#1).
- Größter Rework: Eine Dependabot-Konfiguration ging ohne Pilot-Ergebnis binnen einer Minute in drei Repos und musste zweimal nachgebessert werden (#2). Die Ursache behoben erst die Lock-Dateien in billing-hub#78.
- Zweitziel „keine erneuten Läufe“: Für Renovate ist es adressiert, aber nicht gemessen (#12). Fünf gleichartige Security-Bumps in risk-hub liefen einzeln mit je einem Deploy-Lauf (#17).
- Prod blieb unbeschädigt. Die Security-Bumps #760–#764 erreichen Prod aber nicht, weil Staging seit [risk-hub#468](https://github.com/iilgmbh/risk-hub/issues/468) im Crashloop hängt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | PR-Arbeit am stillgelegten travel-beat: Merges #114, #122 und #129, dabei #129 um 13:55:50Z, also nach der Korrektur. Dazu die öffentliche Meldung „Deploy success“, obwohl der Deploy-Job übersprungen war. Ein Hinweis auf die Stilllegung wurde abgetan. Der Versuch, dort `allow_auto_merge` zu setzen, kostete eine Owner-Ablehnung | fehlende Validierung | hoch | SURVIVES | Lauf 37628198087: Conclusion success, Job `deploy` skipped; Meldung in #3812, Korrektur dort 2026-10-07T13:53Z; Stilllegung [#2480](https://github.com/achimdehnert/platform/issues/2480) (2026-08-30), travel-beat#98 (`vars.DEPLOY_ENABLED`); Transkript 2026-10-06T13:28Z „NICHT stillgelegt“; Ablehnung 2026-10-07T08:31Z | deploy-green-not-prod-healthy (4.), repo-betriebsstatus-vor-arbeit-ungeprueft (1.) |
| 2 | Dependabot-Gruppe mit `update-types` bei Bereichsangaben ohne Pins: billing-hub#68, pptx-hub#95 und travel-beat#122 wurden binnen einer Minute gemergt, ohne Pilot-Ergebnis. Folgen: 15 Einzel-PRs, Django-Major trotz Sperre, Korrektur in #75/#98/#129, danach erneute Umstellung in billing-hub#78 | verfrühte Festlegung | mittel | SURVIVES | mergedAt 13:23:10Z, 13:23:39Z, 13:24:08Z (2026-10-07); #95-Text „Ob die Gruppen wirken, zeigt erst der nächste Lauf (Hypothese)“; billing-hub#70–#74, pptx-hub#99–#103 (#100 Django), travel-beat#124–#128 | bot-konfig-ohne-verhaltensprobe-ausgerollt (1.) |
| 3 | pptx-hub#95 setzte den Docker-Pfad falsch | fehlende Validierung | mittel | REFUTED | `git show 7e5deab^:.github/dependabot.yml` hat `/docker` schon vor #95 (Zeile 35); #98 korrigiert einen Altfehler | — |
| 4 | pptx-hub inkonsistent zu billing-hub, gunicorn-Sperre fehlt | verfrühte Festlegung | mittel | REFUTED | gunicorn steht in pptx-hub in keinem Manifest (nur ungepinnt im Dockerfile), eine Sperre wirkte nicht; Abweichung in der Datei begründet | — |
| 5 | Obergrenzen in billing-hub `requirements.in` deckeln Majors still | verfrühte Festlegung | niedrig | REFUTED | Dependabot hob `<`-Grenzen vor #78 an (billing-hub#72, #74 „update celery requirement from <6.0,>=5.4“); für den Modus nach #78 kein Lauf, PR-Text führt es als Hypothese | — |
| 6 | Org-Liste fest im Code (`ORGS = (…)`) statt Datendatei | Prozesslücke | niedrig | SURVIVES | `tools/pr_bestand.py:45` (platform#3824); `--org` als Überschreibung vorhanden | hausdaten-hardcoded-org-liste (1.) |
| 7 | PR-/Commit-Titel überwiegend `type(scope):` statt Hausregel `[type](scope):` | Kommunikation | niedrig | SURVIVES | #3824, #3825, #3830, #3831, billing-hub#68, #75, mcp-hub#311 vs. billing-hub#78; Regel in der globalen Nutzer-Anweisung, Repo-Praxis 129 von 200 Commits `type(`, 9 `[type](` | commit-praefix-gemischt (2.) |
| 8 | Repo-Datei (billing-hub `Makefile`) per Python-Heredoc in Bash geändert statt per Edit | Prozesslücke | niedrig | SURVIVES | Transkript 2026-10-07T16:15:58Z, Worktree `billing-hub/…pip-lock-161513`; in der Sitzung selbst gemeldet | repo-datei-per-bash-statt-edit (1.) |
| 9 | 10 Edit/Write-Aufrufe ohne vorheriges Read: Tool-Fehler, je ein Wiederholungsaufruf. Beim Schreiben dieses Reports kamen drei weitere dazu | Werkzeug | niedrig | SURVIVES | `retro_kennzahlen`: „File has not been read yet“ 10×, z. B. 2026-10-06T13:39Z, 2026-10-07T09:41Z (2×); Report-Edits 2026-10-08 nach Kontext-Kürzung (3×) | edit-in-worktree-without-read (6.) |
| 10 | Hook-Blockaden wiederholten sich mit demselben Muster (sleep-Block 09:18Z und 14:09Z, Leerer-Body-Guard 2026-10-06T13:43Z und 2026-10-07T11:17Z) | Werkzeug | niedrig | SURVIVES | `retro_kennzahlen` Fehlerläufe; Hook fing jedes Mal, Kosten je ein Wiederholungsaufruf | hook-block-wiederholt-gleiches-muster (2.) |
| 11 | „Deploy nach Merge prüfen“ hat eine allgemeine Werkzeuglücke (Conclusion statt Job) | Werkzeug | mittel | REFUTED | `tools/deploy_wirkung.py` misst Prod-Stand gegen `origin/main`; declined-Eintrag `deploy-green-not-prod-healthy` (Phase 0.7.12); die Lücke lag im Vorgehen der Sitzung, nicht im Werkzeug (→ #1) | — |
| 12 | Zweitziel „keine erneuten Läufe wegen hinter main“ wurde nicht gemessen. Renovate `rebaseWhen: conflicted` (#3825) wirkt nur in 15 von 74 Repos, die Dependabot-Dateien haben keine `rebase-strategy` | fehlende Validierung | mittel | SURVIVES | `rebase-strategy` in 32 `dependabot.yml` auf main: 0; Ledger #3812/#3817 ohne Nachlauf-Messung; mildernd: strict required checks in 5 geprüften Repos aus, Dependabot rebased per Default nur bei Konflikt | zweitziel-ohne-messung (1.) |
| 13 | K1-Ledger unvollständig: risk-hub#827 fehlt, Ledger-Zahl 33 gegen Messung 32 | Prozesslücke | mittel | SURVIVES | `gh pr view 827 -R iilgmbh/risk-hub`: OPEN, Renovate, createdAt 2026-10-08T01:36:53Z; letzter Ledger-Kommentar #3812 03:25:39Z; `grep -c 827` in #3812/#3817: 0 | ledger-zaehlung-veraltet-durch-bot-zufluss (1.) |
| 14 | K1 still auf zwei Orgs verengt, meiki-lra/ttz-lif ungezählt | verfrühte Festlegung | mittel | REFUTED | #3812 schließt in meiki/ttz nur Merges aus, nicht das Zählen; alle 13 offenen PRs dort stehen namentlich im Ledger (G5, G7, G8, G9) | — |
| 15 | 17 Schließungen tragen nur den Bot-Kommentar (Dependabot „superseded“), keinen Grund-Kommentar der Sitzung | Kommunikation | niedrig | REFUTED | Phase 3b: K2 verlangt „einen Kommentar mit Grund“, nicht vom Sitzungskonto. Die Bot-Kommentare nennen ihn: billing-hub#70 „Superseded by #77“, travel-beat#124 „Superseded by #130“, billing-hub#63/#64 „group … removed from your configuration“, pptx-hub#100 „django is no longer being updated“ | — |
| 16 | K3 „Merge nur bei grüner CI“ nicht streng belegt (Rollup zeigt Endstand) | fehlende Validierung | niedrig | REFUTED | `tools/pr_merge_sa.py:285/292` lehnt rote Checks und `checks_total == 0` ab, Zeile 929 Head-SHA-Bindung per `--match-head-commit`; Owner-Skript prüft Fail-Rollup | — |
| 17 | Fünf gleichartige Security-Bumps in risk-hub einzeln gemergt, jeder mit eigenem Deploy-Lauf: vier cancelled, einer am Staging gescheitert. Das widerspricht dem Zweitziel „Merges auf das notwendige Maß“ | verfrühte Festlegung | mittel | SURVIVES | Phase 3b NEU; iilgmbh/risk-hub#760–#764, mergedAt 2026-10-06T15:11:22Z bis 15:59:29Z (achimdehnert); Lauf 37492108884 Staging rot; Ledger #3812 Bilanz 17:00 UTC | gleichartige-bot-prs-einzeln-gemergt (1.) |

Root Causes (5-Why, Kurzform):
- **#1:** Die Workflow-Conclusion galt als Deploy-Beleg. Den Job-Status hat niemand geprüft. Ein Frühcheck „Betriebsstatus“ vor der Arbeit an einem Repo fehlt. Den Hinweis aus dem Deploy-Scan habe ich widerlegt, statt ihn zu prüfen.
- **#2:** Die Konfiguration wurde nur gegen das Schema validiert, nicht gegen das Verhalten. Den Pin-Zustand der requirements habe ich nicht angesehen. Das Muster aus #3817 ging in Repos mit anderen Dateien, bevor der Pilot ein Ergebnis hatte.
- **#12, #17:** Das Zweitziel stand nur im Zieltext und bekam kein eigenes K-Kriterium mit Messung. Deshalb gab es auch keinen Anlass, gleichartige PRs zu bündeln.
- **#13:** Das Ledger wird am Sitzungsende nicht gegen die Messung abgeglichen.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | K1 bis auf #13 erfüllt, Zweitziel ungemessen (#12) |
| architektur_design | 3 | Dependabot-Design dreimal geändert (#2), Org-Liste im Code (#6) |
| code_konventionstreue | 3 | #6, #7, #8 |
| risiko_debt | 3 | Rework reversibel, Falschmeldung korrigiert (#1); Security-Bumps in risk-hub ohne Prod-Wirkung, Anker risk-hub#468 (#17) |
| prozess_effizienz | 3 | Arbeit an totem Repo (#1), Rework in drei Repos (#2), fünf Einzel-Deploys (#17) |
| entscheidungsqualitaet | 3 | Stilllegungs-Hinweis abgetan (#1), Rollout vor Pilot-Ergebnis (#2) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| travel-beat bearbeitet, „Deploy success“ aus Conclusion gemeldet (Lauf 37628198087) | Vor der ersten PR-Arbeit je Repo `isArchived`, Stillgelegt-Liste aus `infra/ports.yaml` und `vars.DEPLOY_ENABLED` prüfen; Deploy-Meldung nur aus `gh run view --json jobs` mit Job `deploy` = success | #1 |
| Gleiche Dependabot-Konfig in drei Repos binnen einer Minute gemergt | Erst die requirements ansehen (Pins oder Bereiche), dann ein Pilot-Repo, den nächsten Dependabot-Lauf abwarten, erst danach die anderen Repos | #2 |
| `ORGS = (…)` in `tools/pr_bestand.py:45` | Org-Liste in eine Datendatei unter `registry/` und von dort lesen | #6 |
| Titel `type(scope):` | Vor `gh pr create` die Titelform gegen die Hausregel prüfen, bis der Owner eine Form festlegt | #7 |
| Makefile per Heredoc geändert | Repo-Dateien immer per Edit, auch bei mehrzeiligen Ersetzungen | #8 |
| Edit ohne Read | Vor dem ersten Edit einer Datei ein Read, auch nach Worktree-Wechsel und nach Kontext-Kürzung | #9 |
| `sleep N; cmd` nach erster Blockade erneut | Warten nur per `gh … --watch` oder Monitor-Schleife | #10 |
| Zweitziel nur im Zieltext | Je Zweitziel ein K-Kriterium mit Messbefehl ins Zielzustand-Issue | #12 |
| Ledger-Zählung 03:25Z ohne risk-hub#827 | Letzte Ledger-Zählung unmittelbar vor Sitzungsende per Messbefehl, jeder offene PR als Zeile | #13 |
| risk-hub#760–#764 einzeln gemergt, fünf Deploy-Läufe | Gleichartige Bot-PRs eines Repos zuerst gruppieren (Renovate/Dependabot-Gruppe oder ein Sammel-PR), dann ein Merge und ein Deploy-Lauf | #17 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`: Slugs mit Zähler ≥ 2 nach dieser Retro sind GATE-PFLICHT.

| Slug | Zähler | Antwort |
|---|---|---|
| deploy-green-not-prod-healthy | 4 | Declined seit 2026-08-23, weil 0.7.12 laufende Container misst. Ein stillgelegtes Repo hat keinen Container, deshalb greift der Grund hier nicht. Kandidat `deploy-job-skipped-als-erfolg`: Die Deploy-Meldung nach dem Merge liest den Job-Status (M1) |
| edit-in-worktree-without-read | 6 | Das Werkzeug erzwingt das Read selbst, Kosten je ein Wiederholungsaufruf. Gate „Lesen vor Edit“ ist beschlossen ([#2234](https://github.com/achimdehnert/platform/issues/2234) M6), kein zweites |
| commit-praefix-gemischt | 2 | Die Regel kollidiert mit der Repo-Praxis. Zuerst entscheidet der Owner die Form, danach kommt ein Titel-Check (M5) |
| hook-block-wiederholt-gleiches-muster | 2 | Der Hook fängt jedes Mal, also kein Gate-Versagen. Vorschlag: declined mit Grund „Kosten ein Aufruf, kein Schaden“ (M7) |

Abgleich mit dem Memory-Index: Eine Memory zu Dependabot und pip-Bereichen fehlt. `grep -il "update-types"`
im Memory-Verzeichnis findet 0 Treffer, deshalb steht ein Memory-Kandidat in §6.

### 5a. Rückfall-Prüfung

Kein gebautes Gate hat in dieser Sitzung versagt. `claim-before-cheapest-check` und
`gh-body-file-leer-ueberschrieben` (Leerer-Body-Guard) haben gefangen und stehen deshalb in
`gates_caught`. `deploy-green-not-prod-healthy` ist declined, nicht gebaut. Sein vierter Zähler ist
damit keine Rückfall-Antwort, sondern die Frage, ob der declined-Grund noch trägt (M1).

### 5b. Autonomie-Kalibrierung

- **over_act** `repo-einstellung-patch-ohne-owner-zug`: Versuch, `allow_auto_merge` in travel-beat per `gh api -X PATCH` zu setzen (2026-10-07T08:31Z). Die Permission-Schranke hat abgelehnt. Repo-Einstellungen sind Owner-Zug (Security-Config-Gate). In pptx-hub und odoo-hub lief es danach korrekt als Owner-Befehl.
- **over_ask:** kein Fall belegt. Die Owner-Züge (P2/P3, P5, P6, P8, P8 lock, W1) waren Merges an Governance-Pfaden oder Prod-nahe Schritte.

## 6. Verankerung

**memory_candidates** (kopierfertig, Owner entscheidet):

```markdown
---
name: dependabot-pip-bereiche-update-types
description: Dependabot-Gruppen mit update-types greifen bei pip-Bereichsangaben nicht — erst Lock-Dateien
metadata:
  type: feedback
---
Bei requirements mit Bereichen (`>=5.4,<6.0`) kennt Dependabot keine aktuelle Version
("Updating celery from  to 5.6.3"), deshalb filtert `update-types` die Updates aus der Gruppe.
Es entstehen Einzel-PRs, die Major-Sperre wirkt nicht.
**Why:** platform#3812/#3817, Rework billing-hub#68→#75→#78, pptx-hub#95→#98 (2026-10-07).
**How to apply:** Vor jeder Dependabot-Konfig die requirements ansehen. Bei Bereichen entweder
Gruppe ohne update-types plus `ignore versions`, oder Lock-Dateien per pip-tools (Muster
billing-hub#78) und dann update-types. Ein Pilot-Repo zuerst, die übrigen erst nach seinem
nächsten Lauf. Bot-PRs nicht von Hand schließen: Dependabot meldet die Version dann nie wieder.
```

```markdown
---
name: betriebsstatus-vor-repo-arbeit
description: Vor PR-Arbeit Archiv-/Stilllegungsstatus prüfen; grüner Deploy-Lauf mit skipped Job ist kein Deploy
metadata:
  type: feedback
---
Vor der ersten PR-Arbeit in einem Repo `gh repo view --json isArchived`, die Stillgelegt-Liste in
`infra/ports.yaml` und `vars.DEPLOY_ENABLED` prüfen. Eine Deploy-Meldung nur aus dem Job-Status
(`gh run view <id> --json jobs`) ableiten, nie aus der Workflow-Conclusion.
**Why:** travel-beat war seit platform#2480 stillgelegt. Die Sitzung 2026-10-06/07 mergte dort
trotzdem und meldete "Deploy success" für Lauf 37628198087 (Job deploy skipped).
**How to apply:** einmal je Repo, bevor ein PR angefasst wird.
```

**adr_candidates:** keine. Beide Lehren ergänzen bestehende Muster (`policies/adr-threshold.md`).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Deploy-Meldung aus Job-Status, declined-Grund prüfen | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812) | 🟢 | Owner: Kandidat `deploy-job-skipped-als-erfolg` annehmen oder declined erweitern |
| M2 | Betriebsstatus-Check vor Repo-Arbeit | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812) | 🟢 | Owner: Memory-Kandidat 2 verankern |
| M3 | Dependabot-Lehre als Memory | platform | [#3817](https://github.com/achimdehnert/platform/issues/3817) | 🟢 | Owner: Memory-Kandidat 1 verankern |
| M4 | Zweitziel messen, Ledger vor Ende nachzählen | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812) | 🔵 | Agent: K5-Vorschlag „Nachläufe und Einzel-Deploys“ mit Messbefehl, risk-hub#827 als Ledger-Zeile |
| M5 | Titelform festlegen | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812) | 🟢 | Owner: `[type](scope)` oder `type(scope)` |
| M6 | Verfallsfrist inline-heredoc-quoting-rework | platform | [#3841](https://github.com/achimdehnert/platform/pull/3841) | ⛔ fällig ab 2026-10-21 | Owner: blocking oder streichen |
| M7 | hook-block-wiederholt als declined | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812) | 🟢 | Owner: declined-Eintrag ja/nein |
| M8 | Org-Liste aus Datendatei | platform | [#3824](https://github.com/achimdehnert/platform/pull/3824) | 🟢 | Agent auf Owner-Wort: Folge-PR |
| M9 | Gleichartige Bot-PRs gebündelt mergen | platform | [#3817](https://github.com/achimdehnert/platform/issues/3817) | 🔵 | Agent: Gruppierungsregel als K4-Vorschlag ergänzen |

## 8. Nicht verifiziert (Restlücken)

- **Dependabot-Verhalten nach billing-hub#78:** Ob der pip-compile-Modus Majors als Einzel-PRs liefert, ist offen, bisher gab es keinen Lauf. Billigster Check am 2026-10-12: `gh pr list -R achimdehnert/billing-hub --author app/dependabot`.
- **Auto-Merge bei Gruppen-PRs:** Belegt ist nur, dass er aktiviert wird. pptx-hub#105 ist OPEN, `mergeStateStatus` BLOCKED. Ob der Merge tatsächlich durchläuft, ist zur selben Frist zu prüfen.
- **Versionssperren durch Schließen von Hand:** Elf Schließungen in billing-hub und pptx-hub lösten „won't notify you again about this release“ aus. Unkritisch ist das nur, solange neuere Versionen folgen. Für billing-hub#66 (gunicorn 26, für eine Owner-Welle vorgesehen) ist die Lage ungeprüft. Billigster Check: `@dependabot recreate` oder die Major-Welle über `requirements.in`.
- **Zahlenabweichung im Ledger:** 33 gegen 32 ist nicht aufgelöst. Billigster Check: die PR-Nummern im Ledger gegen `gh search prs --state open --owner achimdehnert --owner iilgmbh --json repository,number` diffen.
- **mcp-hub#311:** Die doppelte Label-Liste (Workflow-Eingabe und `ALLOWED_EXTRA`) gilt als Drift-Risiko, wurde aber nicht gegengeprüft. Billigster Check: `grep -rn ALLOWED_EXTRA` in shared-ci gegen den Aufruf in mcp-hub.
- **Strict required checks:** nur in 5 Repos geprüft, nicht flottenweit.
- **Befunde #8–#11:** Die Widerlegungsbahn hat sie nicht in der Tiefe geprüft. Belegt sind sie durch Transkript-Kennzahlen und Kommandos.
- **Phase 6 (Extern-Handoff):** bewusst ausgelassen. Die Befunde sind kommandobelegt und klein, eine fremde Zweitmeinung bringt hier wenig. Bei Bedarf kann der Owner sie anstoßen.

Vierklang: **getan:** 3 Finder, 3 Skeptiker, Widerlegungsbahn, Meta-Review, Längsschnitt, Rückfall-Prüfung.
**angenommen:** Dependabot rebased per Default nur bei Konflikt (Doku-Wissen, nicht live geprüft).
**nicht verifizierbar:** die Wirkung von billing-hub#78 vor dem nächsten Dependabot-Lauf.
**offen geblieben:** M1–M9.

## Widerlegung

Phase 3b (Opus, frischer Kontext, nur Report, Footprint und Artefaktliste): **2 gekippt, 1 neu.**

- **BESTAETIGT:** #1 (dazu: #129 wurde erst nach der Korrektur gemergt), #2, #3, #6, #7, #12, #13, #14, #16 und die Worktree-Aussage in §0.
- **GEKIPPT #15:** K2 verlangt einen Kommentar mit Grund, nicht vom Sitzungskonto. Die Dependabot-Kommentare nennen den Grund. Jetzt REFUTED.
- **GEKIPPT §0/M6:** Der Entwurf hielt die ⏰-Mahnung zu `inline-heredoc-quoting-rework` für einen Fehlalarm des Werkzeugs. `gate_wirkung.py` liest aber `expires` (2026-10-21), nicht das Kalibrierfenster. R8 hat nur das Fenster aufgegeben. Die Mahnung ist berechtigt, M6 ist wieder Owner-Entscheid.
- **NEU #17:** Fremde Merges fehlten im Scope des Entwurfs. Belegt sind 16 statt 6 Repos und fünf Einzel-Merges in risk-hub mit fünf Deploy-Läufen. Nachgeprüft per `gh pr view` (mergedAt, mergedBy) und Ledger-Bilanz #3812.
- Nebenfunde übernommen: Zähler `rebase-strategy` 32 statt 30, Commit-Zählung 129/9, §8 Auto-Merge abgeschwächt, Versionssperren als Restlücke, risiko_debt 4 → 3.

## Streichbahn

Streichkandidat `retro-0.0-wiederholt-bestehenden-beschluss`, Belegart **Dublette**: Die
0.0-Tabelle wiederholt für die drei rückfälligen Gates Beschlüsse, die schon in den Retros
`8be895-incr` (Zeilen 49–51) und `767d40` (Zeilen 46–48) stehen. Diese Retro trägt nur bei
claim-before-cheapest-check Neues bei, nämlich zwei Fänge. Vorschlag: `gate_wirkung.py` markiert
ein Gate mit gefasstem, noch nicht umgesetztem Beschluss als `BESCHLOSSEN (<Ref>)`. Die Retro führt
dann nur Gates ohne Beschluss oder mit neuem Vorkommen. Die Zeile aus 6189d3, die der Entwurf
anführte, enthält keinen wiederholten Beschluss und ist gestrichen.

## Self-Review

Phase 5 (Meta-Agent sonnet, nur Report und Skill) hat sechs Mängel gemeldet, alle sind eingearbeitet:

1. Zähler deploy-green-not-prod-healthy 3 → 4.
2. Zeitleiste zu risk-hub#827: Der PR entstand vor der Ledger-Zählung. Die Erklärung „Zeitversatz“ ist gestrichen.
3. „in derselben Minute“ → „binnen einer Minute“.
4. Bei M6 war der falsche PR verlinkt. Ersetzt durch #3841, M6 wieder Owner-Entscheid (siehe Widerlegung).
5. Die Platzhalter in Widerlegung und Self-Review sind gefüllt.
6. Die Fehlalarm-Aussage in §0 war unbelegt. Die Gate-Datei ist nachgeprüft (Zeilen 3 und 13), die Aussage korrigiert.

Sauber: Stichproben-Belege (risk-hub#827, `pr_bestand.py:45`, Lauf 37628198087, Merge-Zeiten,
travel-beat archiviert), Scores ganzzahlig und verankert, Invariante 10 = 10, Frontmatter
vollständig, 0.0 und 5a behandelt, Pfad kollisionsfrei, `retro_report_check.py` Exit 0,
refuted_rate im Band (0.00–0.54). `phase3_refuted: 7` zählt die Kippung von #15 durch die
Widerlegungsbahn mit.
