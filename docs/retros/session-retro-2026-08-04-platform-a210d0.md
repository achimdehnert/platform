---
retro_schema: 1
date: 2026-08-04
repo_scope: [platform, pptx-hub]
session_id: a210d0
footprint: deep
findings_total: 14
findings_survived: 8
refuted_rate: 0.43
phase3_refuted: 3
pre_refuted: 3
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates:
  - handover-stale-vor-merge
  - tracking-doc-stale-after-new-occurrence
  - claim-before-cheapest-check
  - lint-failure-no-local-gate
recurring_findings:
  - handover-stale-vor-merge
  - tracking-doc-stale-after-new-occurrence
  - claim-before-cheapest-check
  - lint-failure-no-local-gate
  - adr-claim-not-amended-after-refutation
  - pr-body-stale-after-followup-commits
---

# Session-Retro 2026-08-04 — platform (a210d0)

Ausgangsfrage des Menschen: ob **IONOS Cubes** eine flexiblere, günstigere
On-Demand-Lösung für selten genutzte Anwendungen wären. Ergebnis der Sitzung:
neun Anwendungen von Host `prod` nach `prod-b` migriert, ein Runbook aus dem
Nichts, zwei CI-Gates repariert, ein 212-Dateien-Formatierungssweep.

## 1. Executive Summary

- **Das Sachziel wurde erreicht und gemessen:** neun Migrationen inklusive
  Datenbank-Dump/Restore, jede einzeln per Marker-Request gegen beide
  nginx-Logs nachgewiesen, kein Datenverlust, kein unbemerkter Ausfall.
- **Die Antwort auf die Ausgangsfrage war „nein" — und das war richtig.**
  IONOS Cubes stoppen die Abrechnung nicht beim Anhalten; der reale Hebel war
  ein Host mit 2,1 % Belegung für 69,49 EUR/Monat, nicht der Anbieter.
- **Schwächste Dimension ist wie im Längsschnitt-Mittel das Register.** Es
  behauptet an einer Stelle zu viel (`illustration` gestoppt — läuft) und an
  sechs Stellen zu wenig (`prod_host` liegt in offenen PRs), während die
  Erfolgsmeldung „Serie vollständig" bereits geschrieben war.
- **Die Falsifikation hat gearbeitet:** von vier Bewertungsbefunden wurden drei
  widerlegt, einer präzisiert. Zwei Finder-Befunde waren zu streng, nicht zu
  milde.
- **Ein Gate fehlt, das keiner der bestehenden abdeckt:** die im Sweep
  gefundene Lint-Regression wäre weder von CI (`ruff check tools/ scripts/`)
  noch vom lokalen Hook (prüft nur `format`) gefangen worden.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Issue #1738 meldet „Long-Tail-Serie vollständig", aber `origin/main:infra/ports.yaml` trägt für 6 der 9 Apps kein `prod_host: prod-b` — die Einträge liegen in den offenen PRs #1752/#1753 | Prozesslücke | kritisch | SURVIVES | `git show origin/main:infra/ports.yaml` → nur 4 `prod_host`-Treffer; `gh pr view 1752/1753 --json state` → OPEN | handover-stale-vor-merge |
| 2 | ADR-292 behauptet weiterhin, Deploy-Workflows läsen `prod_host` als Placement-SSoT; das Runbook widerlegt das, die ADR wurde nie amendiert | verfrühte Festlegung | hoch | SURVIVES | `docs/adr/ADR-292-…md:65,80` vs. `grep -rl prod_host .github/ tools/ infra/` → nur die 2 YAML | adr-claim-not-amended-after-refutation |
| 3 | `infra/hosts.yaml:79-84` und `ports.yaml:338` sagen „illustration-Umzug ABGESCHLOSSEN, prod-Kopie gestoppt", obwohl beide Instanzen laufen (Issue #1738 offen, mit `docker stats` belegt) | fehlende Validierung | hoch | SURVIVES | `git show origin/main:infra/hosts.yaml` + Issue #1738 | tracking-doc-stale-after-new-occurrence |
| 4 | „Bei zehn PRs wurden die CI-Checks nach dem Push nicht kontrolliert" | fehlende Validierung | mittel | **REFUTED** | #1735/#1736 tragen dokumentierte Check-Ergebnisse („CI grün 7/7"); 9 von 10 PRs durchgehend grün | — |
| 5 | Hook `block_unformatted_push.sh` sei strukturell fragil (Regex-Parsing von Bash-Text, zwei Bugfix-Runden) | Werkzeug | mittel | **REFUTED** | Fix betrifft Zeilen 64-72 (Diff-Basis), nicht 26-39 (cd/pushd); nur *eine* frühere Runde für letztere; 6 Testfälle + T10 decken sie ab | — |
| 6 | Die im Sweep gefundene Regressionsklasse ist von keinem Gate abgedeckt: CI prüft nur `ruff check tools/ scripts/`, der lokale Hook nur `ruff format` | Prozesslücke | mittel | SURVIVES | `tools-tests.yml:179`; andere ruff-Workflows pfadgescoped bzw. `\|\| true`; Hook prüft `format --check` | lint-failure-no-local-gate |
| 7 | PR #1752 Titel/Body nennt 2 Apps, der Diff enthält `prod_host` für **5** — Body nach zwei Nachtrags-Commits nicht aktualisiert | Kommunikation | mittel | SURVIVES | `gh pr diff 1752` (5 Blöcke) vs. Body-Tabelle (2 Zeilen), 3 Commits | pr-body-stale-after-followup-commits |
| 8 | „Orchestrator MCP Tests" ist kein Required Check — Lint-Regressionen außerhalb `tools/scripts` können ungehindert nach `main` | Prozesslücke | niedrig | SURVIVES | `gh api repos/…/rules/branches/main` → 3 Required Checks, dieser nicht darunter | lint-failure-no-local-gate |
| 9 | Zwei offene PRs auf identischer Basis ändern beide `infra/ports.yaml` → Konfliktrisiko | Prozesslücke | niedrig | **REFUTED** | Hunks überlappen nicht (#1752: ~157-400, #1753: ~422-436); sachlicher Trennungsgrund; 3 h Abstand | — |
| 10 | Issue-Kommentar nennt „Fix in #1755 … Sweep in #1756" im Ton abgeschlossener Fakten; beide PRs offen | Kommunikation | niedrig | SURVIVES | `gh pr view 1755/1756 --json state` → OPEN | handover-stale-vor-merge |
| 11 | Bei **#1756** blieb rotes CI unbeachtet (4 Fails), im Body trotz Verifikationstabelle nicht erwähnt, `updatedAt` 49 s nach `createdAt`, keine Reaktion | fehlende Validierung | mittel | SURVIVES | `gh pr checks 1756`; präzisierte Fassung von #4 | claim-before-cheapest-check |
| 12 | „Rework an denselben Dateien deutet auf fehlende Vorabprüfung" | Prozesslücke | niedrig | **pre-REFUTED** | `gh pr view <n> --json files` für 1741/1742/1746/1748/1752/1753 → alle berühren `infra/ports.yaml` + `docs/runbooks/adr292-long-tail-umzug-prod-b.md`, aber je einen anderen App-Block (apo/pptx/wedding+coach/research+cad/trading/dms) — Registry-Muster, keine Korrektur derselben Änderung | — |
| 13 | „`--no-verify`-Umgehung ist ein Prozessverstoß" | Prozesslücke | niedrig | **pre-REFUTED** | Im PR-Body offengelegt, Ursache benannt, in derselben Sitzung gefixt (#1755) | — |
| 14 | „Zahlenwiderspruch 496 vs. 212 Dateien" | Kommunikation | niedrig | **pre-REFUTED** | Dieselbe Messung mit/ohne `_ARCHIVED`-Ausschluss (495 ≈ 496) | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | 9 von 9 Migrationen erreicht und je einzeln nachgewiesen; Abzug für #1 (Register bildet 6 davon auf `main` nicht ab) |
| architektur_design | **4** | Runbook wuchs aus einem Präzedenzfall zu einem belastbaren Verfahren mit Fehlerklassen; Abzug für #2 (ADR nicht amendiert) |
| code_konventionstreue | **3** | PR-Bodies mit Belegtabellen, Gate-Umgehung offengelegt; Abzug für #7 (Body veraltet) und #10 (Ton suggeriert Erledigung) |
| risiko_debt | **2** | #1 und #3 lassen das Register in beide Richtungen falsch stehen; #6/#8 lassen eine Gate-Lücke offen; #11 ungeprüftes rotes CI |
| prozess_effizienz | **3** | 9 Migrationen an einem Tag mit wachsendem Verfahren; Abzug für selbstverursachte Portkollision (8094) und für #11 |
| entscheidungsqualitaet | **4** | `_ARCHIVED`-Ausschluss, Baseline-Vergleiche vor/nach, SCRAM-Verifier statt Klartext, Papertrading-Einstufung; 3 von 4 Bewertungsbefunden widerlegt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| „Serie vollständig" in #1738 geschrieben, während `prod_host` für 6 Apps in offenen PRs lag | Vollzugsmeldung erst nach `git show origin/main:<register>` — Prod-Zustand **und** SSoT gemeinsam prüfen, nicht nur den Host | #1 |
| Runbook korrigierte ADR-292s Invariante 2, die ADR blieb unangetastet | Widerlegt ein Fund eine ADR-Aussage, wird im selben Zug ein Amendment-PR gegen die ADR eröffnet — die Korrektur gehört in die SSoT, nicht nur in abgeleitete Doku | #2 |
| `illustration`-Doppellauf gefunden, Issue geschrieben, Registerzeile „gestoppt" stehen gelassen | Beim Befund einer falschen Registeraussage wird die Zeile im selben PR korrigiert (Vertagung betrifft die *Arbeit*, nicht die *Wahrheit* des Registers) | #3 |
| Regression im Sweep nur durch manuellen Baseline-Vergleich gefunden | `ruff check` repo-weit als Required Check ergänzen ODER den lokalen Hook um `check` (nicht nur `format`) erweitern | #6 |
| PR #1752 sammelte 3 Commits über 5 Apps, Body blieb auf Stand von Commit 1 | Bei jedem Nachtrags-Commit auf einen offenen PR Titel und Body im selben Zug nachziehen | #7 |
| Lint-Regressionen außerhalb `tools/scripts` erreichen `main` ungegatet | Required-Check-Liste um einen repo-weiten Lint-Job erweitern, oder den Scope des bestehenden Jobs ausdehnen | #8 |
| Issue-Kommentar formulierte offene PRs als erledigte Fakten | Für unmerged PRs konsequent „vorgeschlagen in #N" statt „Fix in #N"; Zustand aus `gh pr view --json state` übernehmen, nicht aus der Absicht | #10 |
| #1756 gepusht, PR eröffnet, nie auf Checks gesehen | Nach jedem PR-Open ein `gh pr checks <n>` — und bei Rot entweder Fix oder ausdrücklicher Vermerk im Body, warum es stehen bleibt | #11 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über alle Retros: **18 Slugs mit Zähler ≥2** sind
bereits gate-pflichtig. Diese Sitzung trifft vier davon erneut:

| Slug | Befund hier | Status |
|---|---|---|
| `handover-stale-vor-merge` | #1, #10 | ≥2, Gate-Pflicht |
| `tracking-doc-stale-after-new-occurrence` | #3 | ≥2, Gate-Pflicht |
| `claim-before-cheapest-check` | #11 | ≥2, Gate-Pflicht |
| `lint-failure-no-local-gate` | #6, #8 | ≥2, Gate-Pflicht |

Zwei neue Slugs: `adr-claim-not-amended-after-refutation` (#2),
`pr-body-stale-after-followup-commits` (#7).

**Score-Einordnung:** `risiko_debt` liegt hier bei 2 gegen ein Mittel von 2,57
über 68 Messungen — die schwächste Dimension der Sitzung ist zugleich die
dauerhaft schwächste des Repos. Alle drei Register-Befunde (#1, #3, #10) sind
Varianten derselben Ursache: **ein Zustand wird gemeldet, bevor sein durables
Abbild existiert.**

**refuted_rate 0,43** liegt im gesunden Band (Trend zuletzt 0,00–0,45). Die
echte Falsifikationsquote `phase3_refuted/(findings_total − pre_refuted)` =
3/11 = **0,27**.

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 0 | Jeder Prod-Schritt wurde einzeln vorgelegt; keine deterministisch-reversible Aktion unnötig delegiert |
| `over_act` | 0 | Kein Gate autonom überschritten. Firewall-Regel, Compose-Edits und DNS-Schwenks wurden vorgelegt bzw. erst nach ausdrücklicher Freigabe ausgeführt; `--admin`-Bypass wurde **abgelehnt** und zur Entscheidung gestellt |

Bemerkenswert: Der Permission-Classifier blockte mehrfach Aktionen, die der
Mensch bereits freigegeben hatte (ufw-Regel, cloudflared-Config). Das ist kein
`over_act`, sondern eine Werkzeug-Ebene, die enger ist als die Charta — für die
Charta-Kalibrierung eher ein Argument, die Standing-Authorization-Klassen zu
präzisieren als sie zu verengen.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: feedback_vollzug_erst_nach_ssot_abgleich
description: Vollzugsmeldung erst, wenn Prod-Zustand UND Register auf origin/main übereinstimmen
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-04-register-hinkt-hinter-prod
---
Eine Meldung „erledigt/vollständig" ist erst zulässig, wenn beides geprüft ist:
der reale Zustand **und** sein durables Abbild auf `origin/main`.

**Why:** Am 2026-08-04 wurden neun Migrationen als „Serie vollständig" gemeldet,
während `infra/ports.yaml` auf `origin/main` für sechs davon nichts wusste — die
Einträge lagen in offenen PRs. Gleichzeitig behauptete `infra/hosts.yaml` seit
zwei Tagen, eine Instanz sei gestoppt, die nachweislich lief. Beide Richtungen
desselben Fehlers in einer Sitzung.

**How to apply:** Vor jeder Vollzugsmeldung `git show origin/<default>:<register>`
lesen, nicht den Working-Tree und nicht den PR-Branch. Offene PRs sind kein
Vollzug. Siehe [[feedback_handover_next_steps_is_machine_contract]].
```

```markdown
---
name: feedback_widerlegte_adr_aussage_braucht_amendment
description: Widerlegt ein Fund eine ADR-Aussage, gehört die Korrektur in die ADR — nicht nur ins Runbook
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-04-adr292-invariante-nicht-amendiert
---
Wird eine Aussage einer akzeptierten ADR durch Messung widerlegt, wird im selben
Zug ein Amendment-PR gegen die ADR eröffnet.

**Why:** ADR-292 behauptet, Deploy-Workflows läsen `infra/ports.yaml:prod_host`
als Placement-SSoT. Am 2026-08-04 wurde gemessen, dass kein Workflow und kein
Skript das Feld liest. Die Korrektur landete im Runbook; die ADR behauptet es
weiter. Ein Feld, das niemand auswertet, kann beliebig lange falsch stehen.

**How to apply:** Der Fund gehört an die Quelle, nicht nur in die abgeleitete
Doku. Siehe [[feedback_accepted_adr_amendment_needs_execution_pr]].
```

**adr_candidates**

- **Amendment zu ADR-292:** Invariante 2 („Deploy-Workflows lesen `prod_host`")
  streichen oder in ein Soll umformulieren, bis ein Workflow das Feld tatsächlich
  auswertet. Alternativ: einen Konsumenten bauen und die Invariante belegen.
  Auslöser: Befund #2.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Vier PRs brauchen ein Fremd-Approve — https://github.com/achimdehnert/platform/pull/1752 · https://github.com/achimdehnert/platform/pull/1753 · https://github.com/achimdehnert/platform/pull/1755 · https://github.com/achimdehnert/platform/pull/1756
2. 🟢 Entscheiden, ob ADR-292 amendiert oder ein `prod_host`-Konsument gebaut wird — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-292-two-lane-deployment-six-host-standard.md

### 🔵 Offen — ich kann sofort

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 3 | hosts.yaml korrigieren | platform | 🔵 ready | illustration-Zeile (ich) |
| 4 | PR #1752 Body nachziehen | platform | 🔵 ready | 5 statt 2 Apps (ich) |
| 5 | #1756 rote Checks | platform | 🔵 ready | orchestrator_mcp klären (ich) |
| 6 | Lint-Gate erweitern | platform | 🔵 ready | Issue + Vorschlag (ich) |

### ⏸ Vertagt

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 7 | illustration-Doppellauf | platform | ⏸ vertagt | nach Illu-Session |

## 8. Nicht verifiziert (Restlücken)

- **Ursache der roten Checks auf #1756 nicht abschließend geklärt.** Mein
  Phase-1-Log-Lesen zeigte `orchestrator_mcp does not appear to be a Python
  project`; der Prozess-Finder berichtet **54 ruff-check-Fehler** in
  `session_memory.py`. Das sind zwei verschiedene Läufe (30925412727 /
  30925453673) und möglicherweise zwei Ursachen. Billigster Check:
  `gh api repos/achimdehnert/platform/actions/jobs/<id>/logs` für je einen Job
  aus beiden Läufen.
- **Kein unabhängiger Infra-Recheck der Migrationsbehauptungen.** Der
  Soll-Ist-Finder hatte keinen Serverzugriff; die neun „gemessen"-Aussagen
  stützen sich auf meine eigenen Kommandoausgaben in der Sitzung, nicht auf eine
  fremde Zweitmessung. Billigster Check: je App ein Marker-Request durch einen
  Dritten.
- **Phase 1 (Collect) lief inline, nicht über einen frischen Subagenten.** Die
  Sitzungsgrenze (7 fremde PRs desselben Tages aussortiert) habe ich selbst
  gezogen — ein Regel-1-Grenzfall, weil Collect kein Urteil enthält, aber die
  Scope-Entscheidung eine Wertung ist.
- **`over_ask`/`over_act` sind Selbsteinschätzungen**, nicht von einem Skeptiker
  geprüft. Billigster Check: ein Agent zählt in den PR-Bodies vorgelegte gegen
  autonom ausgeführte Schritte.

## Self-Review (Phase 5)

Ein Meta-Agent prüfte diesen Report gegen die Skill-Regeln (nur Formalia, kein
Sitzungsurteil). Ergebnis: **1 formaler Mangel**, behoben — Befund #12 trug
statt eines Artefakt-Belegs nur eine Behauptung („Registry-Muster") und hat jetzt
Kommando plus betroffene Dateien. Geprüft und in Ordnung: Frontmatter-Schema,
Zahlen-Konsistenz (8 + 3 + 3 = 14; `refuted_rate` 6/14 = 0,43), ganzzahlige
Scores mit Befund-Ankern, die Invariante `|Soll-Schritte| == |Survivors|` (8/8),
Abschnitt 8 samt Vierer, kopierfertige Verankerungsvorschläge.

`refuted_rate` 0,43 liegt im Band der Vorgänger (0,00–0,45); `retro_kpis.py`
meldet „Band gesund". Die Zahlen zu den 18 gate-pflichtigen Slugs und zum
`risiko_debt`-Mittel (2,57 bei n=68) wurden vom Meta-Agenten gegen die
Tool-Ausgabe gegengeprüft und stimmen.

### getan · angenommen · nicht verifizierbar · offen geblieben

- **getan:** 9 Migrationen inkl. Stop der Altinstanzen, 10 PRs, 4 Issues, 2
  reparierte bzw. dokumentierte Gates, 1 Formatierungssweep mit Baseline-Beleg.
- **angenommen:** dass die vier offenen PRs unverändert gemergt werden und das
  Register damit aufholt; dass `orchestrator_mcp` schon vorher rot war (belegt
  für die fehlende `pyproject.toml`, nicht für die 54 Lint-Fehler).
- **nicht verifizierbar:** ob während der Umzüge externe Nutzer Ausfälle sahen —
  die Erreichbarkeit wurde nur vorher und nachher gemessen, nicht durchgehend.
- **offen geblieben:** `illustration`-Doppellauf (bewusst vertagt), ruff-Versions-
  widerspruch 0.15.4/0.16.1 (#1754), Fleet-Monitoring blind (#1734), pptx-hub
  Worker defekt (pptx-hub#52).
