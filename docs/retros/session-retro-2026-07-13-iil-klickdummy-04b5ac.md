---
retro_schema: 1
date: 2026-07-13
repo_scope: [iil-klickdummy, frist-hub, trading-hub, bahn-sqf/pg-hub]
session_id: 04b5ac
footprint: deep
footprint_reduction_reason: "Kein Downscale angewendet — Rule B (≥3 Repos mit realen Merges: iil-klickdummy, frist-hub, trading-hub) UND ein echter Prod-Schritt (Auto-Deploy-on-Merge in trading-hub, ausgelöst durch PR #139) feuerten unabhängig voneinander. Die 3-Kriterien-Downscale-Prüfung (a: Prod-Schritt explizit freigegeben / b: voll rollback-fähig / c: findings_total≤10) scheitert an Kriterium (a) — der Prod-Deploy wurde dem User vor dem Merge nicht als solcher benannt, nur generisch 'PR 139 mergen' bestätigt. Deep bleibt bestehen."
findings_total: 14
findings_survived: 8
refuted_rate: 0.43
phase3_refuted: 0
pre_refuted: 6
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [prod-deploy-merge-not-preflighted, new-repo-adoption-without-ci-gate]
recurring_findings: [scope-checkpoint-not-durably-recorded]
---

# Session-Retro 2026-07-13 — iil-klickdummy / frist-hub / trading-hub (Klickdummy-Rollout-Pilot)

## 1. Executive Summary

- **Kernziel teilweise erreicht:** Prozess-Bestandsaufnahme + Pilot auf frist-hub liefen sauber und vollständig (alle 3 Pipeline-Stufen `kd-scout→klickdummy→kd-review`, PR #41/#42 gemergt, CI grün). Der Rollout-Schritt auf ein zweites Repo (trading-hub) kam voran, aber mit echten Prozessbrüchen.
- **Kritisch:** Der Merge von PR #139 (trading-hub) hat einen echten Production-Deploy eines Live-Trading-Systems ausgelöst (Auto-Deploy-on-Merge, `deploy.yml`) — ohne dass dies vor dem Merge als Prod-Schritt erkannt/kommuniziert wurde. Diesmal folgenlos (Deploy erfolgreich), aber strukturell ungeschützt.
- **trading-hub-Adoption unvollständig:** `/kd-review` (dritte Pipeline-Stufe, in frist-hub sauber durchgeführt) wurde übersprungen, UND es gibt kein CI-Gate für die neu eingeführten Klickdummy-Invarianten (I1-I3) — anders als frist-hub, wo genau das nach einer früheren Retro-Lehre bereits automatisiert ist.
- **Scope Creep:** vor dem eigentlichen Rollout-Pilot liefen 9 PRs zu einem Alt-Issue-Backlog in iil-klickdummy — inhaltlich sinnvoll, aber deren zentrales Ergebnis (`gates.mk`-Parity-Gate) wurde im Rollout-Ziel (trading-hub) nicht verwendet.
- **`scope-checkpoint-not-durably-recorded`** ist bereits seit mehreren Retros gate-pflichtig (≥7 Vorkommen) — der heutige Prod-Deploy-Befund ist eine weitere Instanz desselben, strukturell ungelösten Musters.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Merge von PR #139 (trading-hub) löste echten Production-Deploy aus — vor dem Merge nicht als Prod-Schritt erkannt/kommuniziert | fehlende Validierung / Prozesslücke | kritisch | SURVIVES | `deploy.yml` paths-ignore deckt `Makefile`/`klickdummy/*` nicht ab; Deploy-Run `29264533397` (event=push, headSha=460af7a2=Merge-Commit #139) startete 15:59:18Z, 3s nach `mergedAt: 15:59:15Z`, `conclusion: success` (Jobs Resolve/Build/Production) | scope-checkpoint-not-durably-recorded (≥7×, bereits gate-pflichtig) |
| 2 | ADR-409 behauptet "Kein Prod-Deploy-Bezug (I2 mock)" — durch Befund #1 widerlegt | Wissenslücke (Konvention als Gate fehlinterpretiert) | hoch | SURVIVES | `docs/adr/ADR-409-klickdummy-kill-switch-risk.md` Abschnitt "Konsequenzen", wörtlich zitiert | — |
| 3 | trading-hub hat keinen CI-Job, der `make klickdummy`/I1-I3 bei PRs automatisch ausführt — anders als frist-hub (`.github/workflows/ci.yml:56-68`, dort explizit aus einer früheren Retro-Lehre eingeführt) | Prozesslücke / Werkzeug | hoch | SURVIVES | Alle 5 Workflow-Dateien in `achimdehnert/trading-hub/.github/workflows/` grep "klickdummy" → 0 Treffer; PR #139 `statusCheckRollup`: Unit/Integration/Coverage/Contract/Architecture-Guardian alle SKIPPED, kein Klickdummy-Check | — |
| 4 | `/kd-review` (3. Pipeline-Stufe, Playwright+UX-Subagent) wurde für trading-hub PR #139 nicht durchgeführt — in frist-hub PR #42 explizit dokumentiert | Prozesslücke | hoch | SURVIVES | `gh pr view 139 --json comments,reviews` → leer; kein Folge-PR mit UX-Fixes; Gegenprobe frist-hub PR #42 Body zitiert wörtlich einen kd-review-Fund | — |
| 5 | Kein Tracking-Artefakt (Issue/Queue) für die verbleibenden unadoptierten Repos nach trading-hub — Rollout-Ziel "org-weit" kam nur 1 Repo voran | Prozesslücke / Kommunikation | hoch | SURVIVES | `gh issue list --repo iilgmbh/iil-klickdummy --state open` → leer; keine Rollout-Queue in trading-hub-Issues; AGENT_HANDOVER.md ohne Folge-Kandidaten-Liste | — |
| 6 | 9-PR-Backlog-Sweep (iil-klickdummy #166-175) lief vor dem eigentlichen Rollout-Pilot; zentrales Ergebnis (`gates.mk`-Parity-Gate, PR #169/Issue #162) wurde in trading-hub PR #139 nicht verwendet | verfrühte Festlegung / Scope | mittel | SURVIVES | PRs #166-175 gemergt 05:25-08:54 Uhr, vor Pilot-Start; `gh pr diff 139 \| grep gates.mk` → 0 Treffer | — |
| 7 | ADR-409-Frontmatter weicht vom lokalen trading-hub-ADR-Schema ab (kein `decision-makers`/`implementation_status`/Drift-Detector-Kommentar, die ADR-405/406/407/408 alle haben) | fehlende Validierung (Repo-Konvention nicht abgeglichen) | mittel | SURVIVES | Frontmatter-Diff ADR-409 vs. ADR-405/406/407/408 (4 unabhängige Vergleichsfälle) | — |
| 8 | Handover-PR #173 (iil-klickdummy) gemergt, während #171/#172 noch offen waren — 9 Min. später Korrektur-PR #174 auf derselben Datei nötig | Prozesslücke (Reihenfolge Session-Ende vs. offene Merges) | mittel | SURVIVES | #173 mergedAt 08:41:38Z; #171/#172 mergedAt 08:45:20Z/22Z (danach); #174 (Korrektur) mergedAt 08:50:57Z | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Prozess-Check + frist-hub-Pilot vollständig (Ziel 1+2); Rollout (Ziel 3) nur 1 Repo, mit Befund #1/#3/#4/#5 |
| architektur_design | 4 | KD-Erweiterungen strukturell sauber (bestehende Muster wiederverwendet, kein Komplexitätsmonster); Abzug für Befund #7 |
| code_konventionstreue | 3 | I1-I3 grün + Playwright-verifiziert, aber Befund #3 (kein CI-Gate in trading-hub) lässt Drift künftig unentdeckt |
| risiko_debt | 2 | Befund #1+#2 (unentdeckter Prod-Deploy-Pfad, live-money-System) + #3 (kein Schutz-Gate) — kein Incident, aber die Schutzstruktur fehlte komplett |
| prozess_effizienz | 3 | Session insgesamt flüssig (parallele Subagenten, saubere Selbstkorrektur bei der 899-Zeilen-Spec-Erkenntnis), aber Befund #6 (Scope Creep) + #8 (Rework) real |
| entscheidungsqualitaet | 3 | Einzelentscheidungen (Klasse mock, Toggle-Pattern, schlanke Screens) gut begründet und transparent; zentraler Fehler: kein Pre-Flight-Check auf Auto-Deploy vor Merge #139 (Befund #1) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR #139 wurde nach generischer "1 merge"-Freigabe gemergt, ohne vorher `deploy.yml`/`paths-ignore` des Ziel-Repos zu prüfen | Vor JEDEM ersten Merge in ein neues Repo: `gh api repos/<owner>/<repo>/contents/.github/workflows` auflisten + auf Deploy-Trigger prüfen, Ergebnis explizit im Freigabe-Text nennen ("dieser Merge löst einen Prod-Deploy aus") | #1 |
| ADR-409 behauptet pauschal "kein Prod-Deploy-Bezug" allein aus der I2-Klasse `mock` abgeleitet, ohne die CI-Realität des Ziel-Repos zu prüfen | I2-Klassenwahl UND die tatsächliche CI/Deploy-Topologie getrennt dokumentieren — eine `mock`-Klasse ist eine Inhalts-Aussage, keine CI-Garantie | #2 |
| trading-hub bekam die Makefile-Targets (`klickdummy-i1..i3`) ohne CI-Verdrahtung — identisch zum Zustand, den frist-hub laut eigener Commit-Historie (PR #20) bereits einmal als Bug-Quelle identifiziert hatte | Bei Erstadoption von iil-klickdummy in einem neuen Repo: CI-Job-Verdrahtung ist Teil des Adoptions-Schritts, nicht optional — analog frist-hub `ci.yml:56-68` als Kopiervorlage nutzen | #3 |
| `/kd-review` wurde nach dem `klickdummy`-Build für trading-hub nicht mehr aufgerufen, obwohl die 3-Stufen-Pipeline in derselben Session für frist-hub durchlaufen wurde | Pipeline-Stufen als Checkliste führen (`kd-scout ☐ klickdummy ☐ kd-review ☐`) — kein Merge, solange nicht alle 3 Stufen für DIESES Repo abgehakt sind | #4 |
| Nach dem trading-hub-Merge gab es keine Notiz/Issue für die verbleibenden ~14 Repos ohne KD | Bei jedem Rollout-Schritt: ein GitHub-Issue oder ein Abschnitt in AGENT_HANDOVER.md mit der Restliste aktualisieren — im selben Turn, nicht nachträglich | #5 |
| 9 PRs zu einem Alt-Backlog liefen vor dem eigentlichen Rollout-Ask, ihr Ergebnis (`gates.mk`) blieb im Rollout-Ziel ungenutzt | Vor Backlog-Arbeit parallel zu einem neuen Ask kurz prüfen, ob das Backlog-Ergebnis für den Ask selbst gebraucht wird — wenn nicht, zeitlich klar trennen oder das Ergebnis aktiv ins Rollout-Ziel einziehen | #6 |
| ADR-409 nutzt das cross-repo-Template statt das lokal etablierte trading-hub-Schema | Vor dem Schreiben eines neuen ADRs in einem fremden Repo: 1 bestehendes ADR im Zielrepo als Frontmatter-Vorlage lesen, nicht das generische Skill-Template blind kopieren | #7 |
| Session-Ende-Handover-PR (#173) lief, bevor die zugehörigen Fach-PRs (#171/#172) tatsächlich gemergt waren | Handover-/Abschluss-PRs erst NACH Bestätigung aller referenzierten Merges erstellen, nicht parallel/vorgezogen | #8 |

## 5. Längsschnitt (`tools/retro_kpis.py`)

**Tool-Output (verbatim, Auszug):**
```
🚨 GATE-PFLICHT (10 Slugs ≥2): always-instruction-without-enforcement, ci-gate-maskiert-failure,
ci-replace-requires-job-catalog-diff, claim-before-cheapest-check, handover-stale-vor-merge,
lint-failure-no-local-gate, planned-phase-no-issue, platform-pinned-perma-dirty-loop,
scope-checkpoint-not-durably-recorded, stale-local-clone-as-ground-truth
refuted_rate-Band: 589606:0.36 · 42bfe0:0.50 · d2522c:0.20 · f4a546-incr:0.14 · f4a546:0.00 ·
d2522c-incr:0.40 · d2b425-incr:0.60 · d2b425:0.33 → Band gesund (weder 3× >0.8 noch <0.2)
Score-Mittel (n=25): zielerreichung 3.92 · architektur_design 3.60 · code_konventionstreue 3.60 ·
risiko_debt 2.76 · prozess_effizienz 3.16 · entscheidungsqualitaet 3.48
```

- **`scope-checkpoint-not-durably-recorded` — bestätigte Rekurrenz.** Bereits ≥7× gate-pflichtig
  (u. a. `e17299`, `0181a7-incr`, `2752dc`, `d2b425`, `42bfe0`, `17c08c`, `7f7fbd`). Ein Vorgänger-
  Fund (`0181a7-incr`, F7) beschreibt wörtlich denselben Mechanismus wie Befund #1 heute: *"#762
  (Prod-Deploy, 2. Repo) ohne dokumentierten Scope-Checkpoint im PR-Body."* Heute: PR #139
  (Prod-Deploy, 2. Repo dieser Session mit Merge-Rechten) — gleiches Muster, anderes Repo, anderer
  Tag. Der Slug ist seit Wochen gate-pflichtig und wurde bisher **nicht** hart verankert (kein Hook/CI
  gefunden, das einen Auto-Deploy-Trigger vor Merge-Freigabe prüft und meldet).
- **`ci-gate-maskiert-failure` (×3, bereits gate-pflichtig)** ist NICHT dasselbe Muster wie Befund #3
  (dort maskiert ein bestehendes Gate einen echten Fehler; hier fehlt das Gate komplett) — bewusst
  NICHT als Rekurrenz gezählt, sondern als neuer, verwandter `gate_candidate` geführt
  (`new-repo-adoption-without-ci-gate`).
- Kein Beleg für eine Verbindung zwischen Befund #4/#5/#6/#8 und einem bestehenden gate-pflichtigen
  Slug gefunden (`workaround-without-tracking-anchor` wurde geprüft, deckt inhaltlich einen anderen
  Fall ab) — als neue Einzelfunde geführt, nicht als Rekurrenz behauptet.

## 5b. Autonomie-Kalibrierung

- **`over_act` (autonom getan, das ein Gate war):** Befund #1 — PR #139 gemergt (Prod-Deploy-
  auslösend) auf Basis der generischen Wort-Freigabe "1 merge", ohne die Deploy-Konsequenz vorher
  zu benennen. Die Freigabe selbst war zwar spezifisch ("PR 139 mergen" nach separater Nennung),
  aber ohne die *materielle* Information, dass dies einen Live-Trading-Prod-Deploy auslöst — die
  Zustimmung war damit nicht auf derselben Informationsbasis wie bei den anderen (deploy-losen)
  Merges dieser Session. Das ist ein `over_act` nach der 5-Gates-Definition (Gate 2, Prod-
  Zustandsänderung), auch wenn eine PR-Nummer explizit genannt wurde.
- **`over_ask`:** keiner identifiziert — alle Rückfragen dieser Session (pg-hub-Scope, KD-Zuschnitt-
  Strategie, D+mock-Klassenwahl) betrafen echte, nicht-deterministische Entscheidungen (Fach-/
  Strategie-Wahl), keine reversiblen/deterministischen Routine-Schritte.
- Da `scope-checkpoint-not-durably-recorded` bereits ≥7× gate-pflichtig ist und genau diesen
  `over_act`-Typ (Prod-Schritt ohne durchgehaltenen Scope-Checkpoint) beschreibt, verstärkt dieser
  Fund die bestehende Empfehlung: **die Charter/Policy sollte einen Pre-Flight-Check auf
  Auto-Deploy-Workflows zur Pflicht vor JEDER Merge-Freigabe machen**, nicht nur zur Empfehlung.

## 6. Verankerung (Kandidaten — Mensch entscheidet)

**memory_candidate `trading-hub-deploy-on-merge` (feedback/project, repo iil-klickdummy oder
achimdehnert-global):**
```markdown
---
name: trading-hub-auto-deploy-on-merge
description: trading-hub deployed automatisch bei jedem Merge nach main (außer reine .md/docs) — Merge dorthin ist immer ein Prod-Schritt
metadata:
  type: project
---

trading-hub hat `.github/workflows/deploy.yml` mit Auto-Deploy bei Push auf
main. `paths-ignore` deckt nur `**.md`, `docs/**`, `AGENT_HANDOVER.md`,
`NEXT.md` ab — Makefile/Code/klickdummy-Änderungen lösen IMMER einen echten
Production-Deploy des Live-Trading-Systems aus.

**Warum:** Session-Retro 2026-07-13 (`04b5ac`) — PR #139 (Klickdummy-Merge,
inhaltlich harmlos) löste unbemerkt einen echten Prod-Deploy aus, weil vor
dem Merge nicht geprüft wurde, ob das Repo Auto-Deploy hat.

**Wie anwenden:** Vor JEDEM Merge in trading-hub explizit benennen, dass ein
Prod-Deploy folgt — auch bei rein doku-/mock-artigen Änderungen wie
Klickdummies, sobald sie Nicht-.md-Dateien berühren.
```

**gate_candidate `prod-deploy-merge-not-preflighted` (höchster Hebel, verstärkt bestehendes
`scope-checkpoint-not-durably-recorded`):**
> Vor jeder Merge-Freigabe-Anfrage an den User: `gh api repos/<owner>/<repo>/contents/.github/workflows`
> auflisten, auf Push-zu-main-Deploy-Trigger prüfen. Trifft das zu → im Freigabe-Text explizit
> "Dieser Merge löst einen Production-Deploy aus" ergänzen, nicht nur "PR mergen?". Mechanisch
> gateable als Pre-Merge-Checkliste im `/issues-offen`/allgemeinen Merge-Workflow.

**gate_candidate `new-repo-adoption-without-ci-gate`:**
> Bei Erstadoption eines Tools/einer Konvention (hier: iil-klickdummy) in einem neuen Repo: CI-
> Job-Verdrahtung ist verpflichtender Teil des Adoptions-PRs, nicht optional — Checkliste im
> `/klickdummy`-Skill ergänzen (Schritt 8 Makefile-Erweiterung um "+ CI-Workflow-Job" erweitern).

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Rollout-Queue-Issue für verbleibende ~14 Repos anlegen | iil-klickdummy | — | offen | Issue mit Repo-Liste + Priorisierung anlegen |
| 2 | CI-Gate für Klickdummy-Invarianten in trading-hub nachziehen | trading-hub | — | offen | `ci.yml`-Job analog frist-hub ergänzen |
| 3 | `/kd-review` nachträglich für trading-hub-KD fahren | trading-hub | — | offen | Playwright+UX-Subagent-Review nachholen |
| 4 | memory_candidate + gate_candidates oben verankern (ja/nein je Kandidat) | — | — | offen | Entscheidung + ggf. `/klickdummy`-Skill-Edit |

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | ADR-409-Frontmatter an lokales trading-hub-Schema angleichen | trading-hub | ADR-409 | bereit | kleiner Folge-PR |

### ✅ Erledigt

- Retro-Report geschrieben, Phase 1-4 vollständig mit unabhängigen Sonnet-Subagenten (3 Finder + 3 Skeptiker), alle 8 verifizierten Befunde SURVIVES.

## 8. Nicht verifiziert (Restlücken)

- **2 Low-Severity-Beobachtungen nicht durch Phase-3-Skeptiker geprüft** (Zeitbudget-Priorisierung
  auf die 8 höchstrangigen Befunde): ADR-409 fehlt im `docs/adr/INDEX.md` von trading-hub (Finder-
  Befund, größtenteils vorbestehend — ADR-405-408 fehlen dort ebenfalls) und die kurzen Merge-
  Review-Fenster (9-42s) bei den reinen Doku-PRs #173/#174/#175 in iil-klickdummy (Finder-Befund,
  niedrig, da keine Code-/Prod-Wirkung). Billigster Nachweis: beide sind mit den bereits gezogenen
  Finder-Belegen (`gh pr view ... --json createdAt,mergedAt` bzw. `cat docs/adr/INDEX.md`) in <2 Min.
  nachprüfbar, falls gewünscht.
- **Inhalt von `screens-spec.yaml`/`shell.html` in trading-hub nicht line-by-line von einem
  Skeptiker geprüft** — nur strukturell (Playwright-Coverage, I1-I3) während der Session selbst
  verifiziert, nicht in einem frischen Retro-Kontext gegengelesen.
- **Phase 6 (Extern-Handoff)** nicht durchgeführt — optional bei `deep`, hier aus Zeit-/Kosten-
  Gründen ausgelassen; könnte bei Bedarf nachgeholt werden (Methoden-Zweitmeinung zur Scoring-
  Logik/Soll-Ablauf).
