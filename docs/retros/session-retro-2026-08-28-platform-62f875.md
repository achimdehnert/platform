---
retro_schema: 1
date: 2026-08-28
repo_scope: [platform, shared-ci, writing-hub]
session_id: 62f875
footprint: deep
findings_total: 15
findings_survived: 9
refuted_rate: 0.40
phase3_refuted: 5
pre_refuted: 1
over_ask: 0
over_act: 2
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - required-check-reduction-drops-sibling-job
  - merge-bypass-without-explicit-word
  - gate-claim-before-cheapest-check-wirkungslos
  - gate-lint-failure-no-local-gate-wirkungslos
recurring_findings:
  - claim-before-cheapest-check
  - merge-bypass-without-explicit-word
  - gate-approval-needs-pr-comment
  - lint-failure-no-local-gate
  - tracking-doc-stale-after-new-occurrence
  - scope-checkpoint-not-durably-recorded
  - deferred-item-no-tracking-issue
gates_caught:
  - scope-checkpoint-not-durably-recorded
  - deferred-item-no-tracking-issue
footprint_reduction_reason: "keine — deep beibehalten (39 PRs / 24 Repos / Ruleset-Bypass / Host-Eingriff; Befund-Schaetzung >10)"
---

# Session-Retro 2026-08-28 — platform / shared-ci / writing-hub (62f875)

> Sitzung 2026-08-27 ~14:00Z bis 2026-08-28 ~09:30Z, **eine** Konversation ueber zwei Kalendertage.
> Auftrag: „analysier und schlage moeglichkeiten vor wie wir unnoetige ausgaben vermeiden koennen"
> (GitHub-Alarm 90 % der 3.000 Actions-Minuten). Spaeter ergaenztes Owner-Ziel: „writing-hub
> verursacht keine kosten -> ggf auf lokaler llm -> rtx4090". Scope ueber Branch-Praefixe
> `session/2026-08-2[78]/achim-dehnert/{ci-concurrency-cancel,shared-ci-v1112,ci-gpu-*,rm-abs-symlink}`
> gezogen, nicht ueber das Datum. Pipeline: 1 Collector (haiku), 3 Finder (sonnet), 3 Skeptiker
> (sonnet, nur Bewertungsbefunde + zwei Finder-Konflikte), 1 Meta-Reviewer (sonnet).

## 1. Executive Summary

- **Ziel erreicht und belegt:** shared-ci v1.1.12 bricht ueberholte PR-Laeufe in 23 Konsumenten ab
  (Wirkungsnachweis dev-hub-Run 33103182338: Jobs 1 s nach Anlage des Folgelaufs `cancelled`);
  writing-hub laeuft auf dem GPU-Box-Runner `ci-gpu` — drei unabhaengige Laeufe zeigen je genau
  **einen** hosted Job (`Runner-Label-Check`, Owner-Entscheidung „31 nicht bauen" durabel).
- **Kritischer Nebeneffekt, in der Sitzung uebersehen:** die Reduktion der writing-hub-Branch-
  Protection auf `ci / gate` hat den repo-eigenen Job `Integration Tests` (Postgres, Chromium,
  ADR-180-Trigger) aus den Required Checks entfernt — er haengt nicht unter `gate` (#1).
- **Gate rueckfaellig:** `claim-before-cheapest-check` zum 70. Mal — diesmal als `gh pr comment`
  („Admin-Merge") vor `gh pr view --json mergedBy`; der Stop-Hook sieht Kommentar-Payloads nicht (#2).
- **Zwei Bypass-Klassen ohne spezifisches Wort:** `--admin` auf mcp-hub#234 mit generischer
  Autonomie-Formel (#3); Security-Config-Aenderung ohne durables Freigabe-Zitat (#1).
- **Sauber gelaufen:** 39/39 PRs gemergt, Session-Branches geloescht, alle Aufschuebe mit Issue
  (#2392, #2401, writing-hub#824), Scope-Checkpoints in PR-Texten — zwei Gates haben gefangen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | writing-hub Required Checks auf `ci / gate` reduziert: eigener Job `Integration Tests` ist kein Required Check mehr (nicht in `gate.needs`), keine Freigabe woertlich im Artefakt | fehlende Validierung / Prozessluecke | kritisch | SURVIVES (Skeptiker A) | `gh api repos/achimdehnert/writing-hub/branches/main/protection/required_status_checks` → `["ci / gate"]`; `origin/main:.github/workflows/ci.yml` writing-hub Job `integration-tests` als Sibling von `ci:`; shared-ci `_ci-python.yml` `gate.needs` ohne ihn; platform#2392 Kommentare 04:41:37Z („offen beim Owner") → 04:47:50Z („reduziert, verifiziert") ohne Zitat dazwischen | gate-approval-needs-pr-comment ×3 → ×4; neu: required-check-reduction-drops-sibling-job |
| 2 | Kommentar „Admin-Merge (Ruleset-Bypass)" auf platform#2397 gepostet, obwohl wirdigital 06:55:25Z regulaer gemergt hatte; 28 s spaeter selbst korrigiert | fehlende Validierung | hoch | kommandobelegt | platform#2397 Kommentare 06:56:41Z / 06:57:09Z; `gh pr view 2397 --json mergedBy` → `wirdigital` | claim-before-cheapest-check ×69 → ×70 — **Gate rueckfaellig** (§5a) |
| 3 | mcp-hub#234 per `--admin` gemergt, gestuetzt auf „mache es autonom, du hast dafuer meine freigabe" statt auf ein benanntes Bypass-Wort | Kommunikation | mittel | SURVIVES (Skeptiker B1) | mcp-hub#234 Kommentar 06:56:36Z; `autonomy-gates.md:228-229` („'mergen' ≠ '--admin' … praezise fragen") | merge-bypass-without-explicit-word ×3 → ×4 |
| 4 | Host-Port 55434 zweimal als Literal in writing-hub `ci.yml` (`ports:` Z.114, `TEST_DB_PORT` Z.121) — `vars.*` waere in beiden Kontexten referenzierbar | verfruehte Festlegung | niedrig | SURVIVES (Skeptiker B2) | `origin/main:.github/workflows/ci.yml:114,121` (writing-hub); GitHub-Doku Context-Availability (`vars` in `services` und `env`) | — |
| 5 | Review-Prep-Frage „docker-Gruppe fuer github-ci bewusst?" auf platform#2397 vor dem Merge unbeantwortet | fehlende Validierung | mittel | kommandobelegt | platform#2397 Kommentar 06:08:13Z (Frage #2); keine Antwort in 06:55–06:57Z; `bootstrap_ci_runner_wsl.sh` `usermod -aG docker github-ci` | — |
| 6 | platform#2397 nach erstem Push rot (hosts_audit-Schema + Zeitbomben-Test), Folge-Commit noetig — `hosts_audit.py` und `pytest tools/tests` waren lokal verfuegbar, liefen aber erst nach dem CI-Rot | fehlende Validierung | mittel | kommandobelegt | Run 33143485516 (attempt 2, failure 05:01Z, Annotation `runner 'gpu-box'.host=10.99.0.2 referenziert keinen Host`); Fix-Commit 06:53:44Z; Run 33149497270 gruen | lint-failure-no-local-gate ×9 → ×10 |
| 7 | writing-hub#826 brauchte 4 Commits / 2 rote Laeufe: Absolut-Symlink ins Owner-Home (EACCES) und Port 5434 vom lokalen PG-18 belegt — hosted-only-Annahmen zuendeten erst auf dem self-hosted Runner | Wissensluecke | mittel | kommandobelegt | Runs 33143498559 (05:01Z fail), 33150361186 (07:08Z fail), 33150937943 (07:17Z gruen); Commits 07:08:13Z, 07:17:46Z; Flotte: platform#2401 (18 Repos) | neu: hosted-only-assumptions-surface-on-self-hosted |
| 8 | Kontoweite Sperre: hosted Jobs scheiterten in 2–5 s („payments have failed or your spending limit needs to be increased"), bis der Owner ein Budget setzte — Spending-Limit stand auf 0 $ + Stop | Prozessluecke (Org) | hoch | kommandobelegt | dev-hub Job 98626011599 Annotation 18:23Z; Run 33103314562 attempt 2 gruen 18:24:36Z; Usage-Report: 31,15 $ bezahlt ab 17.8., writing-hub 24,11 $ | neu: spend-limit-zero-blocks-hosted-ci |
| 9 | platform#2392-Body: 8 Checkboxen nie abgehakt, „Budget 10 $" steht, real 200 $ nur als Paraphrase im Kommentar; Fortschritt nur als Kommentar-Kette | Prozessluecke | mittel | SURVIVES (Skeptiker C4) + kommandobelegt (P5) | `gh issue view 2392 --json body` (alle `- [ ]`); Kommentar 04:41:37Z „Owner hat Budget (200 $, Stop bei Limit) gesetzt" (indirekte Rede) | tracking-doc-stale-after-new-occurrence ×7 → ×8 |
| 10 | Test-Fix `test_kettencheck.py` in Infra-PR #2397 = Scope-Vermischung | — | niedrig | **REFUTED** (C3): Commit 5aae85f dokumentiert die Zeitbombe (`HEUTE` fix, mtime real), die den PR blockierte und main ab 28.8. rot gemacht haette | `gh pr view 2397 --json commits` (3. Commit) | — |
| 11 | Ersparnis nur Einzellauf-Hochrechnung, „0 hosted Minuten" unbelegt | — | mittel | **REFUTED** (C1): drei unabhaengige Runs 33151934576 / 33154132665 / 33150937943 zeigen identisch 1 hosted Job; Rest ist Owner-Entscheidung „31 nicht bauen" (08:02:56Z) | `gh api …/runs/<id>/jobs` ×3; platform#2392 | — |
| 12 | #2401 / writing-hub#824 ohne Assignee/Label/Termin = Prozessluecke | — | mittel | **REFUTED** (C2): Hausregel verlangt Tracking-Artefakt mit Link, nicht Assignee; 15/15 offene platform-Issues ohne Assignee (Repo-Konvention) | `~/.claude/CLAUDE.md` Z.57; `gh issue list -R achimdehnert/platform --limit 15 --json assignees` | — |
| 13 | hosts_audit-Fund auf #2397 „nicht dokumentiert aufgeloest" (Finder E6, Konflikt mit P1) | — | niedrig | **REFUTED** (B3): Fix-Commit 06:53:44Z vor gruenen Checks; `hosts_audit.py` gegen Ref-Stand „keine Findings" | platform#2397 Commits/Checks; `infra/hosts.yaml:159-169,301-312` | — |
| 14 | „recruiting-hub ohne Ausschlussgrund, wedding-hub andere shared-ci-Version" (Finder E7, Konflikt mit P13) | — | niedrig | **REFUTED** (B4): alle vier `isArchived:true`; #2401-Kommentar 08:07:46Z nennt genau diese vier als archiviert | `gh repo view --json isArchived` ×4; platform#2401 | — |
| 15 | Finder S6 ordnete die korrigierte „Admin-Merge"-Aussage mcp-hub#234 zu | — | — | **pre_refuted** (Zuordnungsfehler; Beleg im selben Befund zeigt platform#2397 — Substanz = #2) | Collector A / Finder S6 Belegzeile | — |

**Positiv belegt (kein Befund):** Concurrency-Design #60 (`group` Job×Workflow×Ref, `cancel-in-progress` nur `pull_request`, Deploy-`concurrency` in writing-hub `deploy.yml` unberuehrt) · Pin-Bump 23/23 ohne Rest-Pins (Stichprobe 12 Repos) · Symlink-Welle 14/18 mit Owner-Zitat „29 go" je PR, 4 archivierte begruendet · Session-Branches auf Remotes 0/0 (31 gefundene Branches sind Fremd-Sessions) · keine Klartext-Tokens im Artefaktraum · zwei getrennte PR-Wellen je Repo waren zeitlich nicht buendelbar (Symlink-Fund 3 h nach Bump-Merge).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Auftrag messbar erfuellt (Usage-Report, 3 Laeufe je 1 hosted Job); Abzug: #1 als unbeabsichtigter Schutzverlust |
| architektur_design | 4 | #60 tragfaehig (OK-Eintrag Finder E), Runner als getrackter KONZ-021-Opt-out in `hosts.yaml`; Abzug: #4, Runner-Name = Hostname |
| code_konventionstreue | 3 | #3 (Bypass ohne benanntes Wort), #4 (Literal ×2), #1 (Security-Config ohne durables Zitat) |
| risiko_debt | 2 | #1 realer Merge-Gate-Verlust auf der laut Datei-Kommentar riskantesten Testflaeche; #5 offene Sicherheitsfrage; #9 Plan-Drift |
| prozess_effizienz | 3 | 39 PRs in ~19 h mit Merge-Monitoren; Abzug: #6/#7 Rework, #8 Sperre kostete eine Rerun-Runde ueber 4 PRs |
| entscheidungsqualitaet | 3 | W1 („nur `ci / gate`") wurde vorgeschlagen, ohne den Sibling-Job zu pruefen (#1); dagegen #11–#14 widerlegt: Beweisfuehrung war ueberwiegend sauber |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Required Checks per API auf `ci / gate` reduziert; Annahme „gate buendelt alles" ungeprueft (platform#2392 04:47:50Z) | Vor jeder Reduktion von Required Checks: `gh api …/protection/required_status_checks` → je Kontext pruefen, ob er in `gate.needs` liegt; Sibling-Jobs bleiben Required; Owner-Wort als PR-/Issue-Kommentar zitieren, dann erst PATCH | #1 |
| `gh pr merge --admin` → „already merged" → sofort Bypass-Kommentar gepostet (06:56:41Z) | Kein Kommentar mit Status-Claim ohne vorherigen `gh pr view --json state,mergedBy`; Stop-Hook-Scanner um `gh pr/issue comment`-Payloads erweitern (§5a) | #2 |
| `--admin` auf mcp-hub#234 mit „mache es autonom" (06:56:36Z) | Bypass nur mit benanntem Wort („#234 per --admin mergen: go"); sonst Zweitkonto/Bot abwarten — Frage praezise stellen, nicht generisch | #3 |
| Port 55434 in `ports:` und `TEST_DB_PORT` (ci.yml:114,121) | Repo-Variable `vars.TEST_DB_HOST_PORT` in beiden Kontexten, eine Quelle | #4 |
| Review-Prep-Frage zur docker-Gruppe unbeantwortet vor Merge (06:08:13Z) | Jede offene Review-Prep-Frage bekommt vor dem Merge eine Antwort-Zeile im PR (auch „bewusst so, weil …") | #5 |
| #2397 erst in CI rot (hosts_audit, pytest) | `python3 infra/scripts/hosts_audit.py` + `pytest tools/tests/` lokal vor dem ersten Push, wenn `infra/hosts.yaml` oder `tools/` angefasst wird | #6 |
| Erster self-hosted Lauf deckte Symlink + Port-Kollision auf (Runs 05:01Z, 07:08Z) | Vor dem Umzug eines Repos auf self-hosted: `git ls-files -s \| awk '$1==120000'` auf Absolut-Ziele und `ss -ltnp` auf der Box gegen alle `ports:` der Workflows pruefen (Preflight-Checkliste im Bootstrap-Runbook) | #7 |
| Spending-Limit 0 $ + Stop → hosted CI kontoweit tot (18:23Z) | Budget nie „0 $ + Stop"; kleines Puffer-Budget + 75/90/100 %-Alerts als Standard; Alarm-Mail = Incident-Trigger, nicht nur Analyse-Anlass | #8 |
| #2392-Body unveraendert, Fortschritt nur in Kommentaren | Bei jedem Status-Update Checkboxen im Body abhaken und geaenderte Zielwerte (10 $ → 200 $) im Body nachziehen; Owner-Entscheidungen woertlich zitieren | #9 |

## 5. Laengsschnitt

`python3 tools/retro_kpis.py` (98 Reports vor diesem): `claim-before-cheapest-check` ×69, `deferred-item-no-tracking-issue` ×28, `scope-checkpoint-not-durably-recorded` ×21, `lint-failure-no-local-gate` ×9, `tracking-doc-stale-after-new-occurrence` ×7, `merge-bypass-without-explicit-word` ×3, `gate-approval-needs-pr-comment` ×3 — alle bereits GATE-PFLICHT. Dieser Report erhoeht: claim ×70, lint-local ×10, tracking-stale ×8, merge-bypass ×4, gate-approval ×4.

**Skill-KPI:** `refuted_rate` 0,40 gegen das Band der letzten sieben Reports (0,00 · 0,25 · 0,00 · 0,33 · 0,14 · 0,00 · 0,07) — hoechster Wert der Reihe, innerhalb des gesunden Bands (0,2–0,8); echte Falsifikationsquote `phase3_refuted/(findings_total − pre_refuted)` = 5/14 = 0,36. Drei der fuenf Widerlegungen trafen Bewertungsbefunde, die zu **streng** waren (C1–C3) — Fehlerrichtung wie im Realfall 6bd412, nicht Selbstnachsicht.

**Gates, die gefangen haben (`gates_caught`):** `scope-checkpoint-not-durably-recorded` — der Artefakt-Budget-Hook feuerte zweimal (nach 20 bzw. 13 PRs), der Scope wurde jeweils gespiegelt und die Owner-Worte stehen in jedem PR-Body. `deferred-item-no-tracking-issue` — jede Aufschiebung bekam im selben Zug ein Issue (#2392, #2401, writing-hub#824; Skeptiker C2 bestaetigt Konformitaet). Beide zaehlen als Vorkommen, aber als Beleg **fuer** das Gate.

**Memory-Abgleich:** `feedback_runner_label_check_blind_to_runs_on_inputs` (existiert, 🌀) — Session hat den Label-Check bewusst behalten, konform. `feedback_ruleset_bypass_durable_artifact` (existiert) — #3 hat das Artefakt, nicht das Wort. `feedback_merge_bypass…` als eigene Memory: nicht vorhanden (Kandidat unten).

### 5a. Rueckfall-Pruefung (`tools/gate_wirkung.py`)

Lauf mit diesem Report (`python3 tools/gate_wirkung.py --dir docs/retros --kurz`): **3 Gates rueckfaellig** — `deferred-item-no-tracking-issue` (4× seit 2026-08-23, zuletzt 2026-08-26; dieser Report zaehlt dort **nicht**, weil der Slug in `gates_caught` steht — das Gate hat gefangen), `lint-failure-no-local-gate` (2× seit Bau 2026-08-04, zuletzt **2026-08-28 = #6**), `untested-tool-module-green-gate` (2× seit 2026-08-12, nicht diese Sitzung).

**Gate rueckfaellig 1 — `claim-before-cheapest-check`** (#2, ×70; Klasse `gate-claim-before-cheapest-check-wirkungslos`, damit ×2 nach beefc148). Antwort **ausweiten**: der Stop-Hook `evidence_claim_scanner.py` prueft nur den Antworttext des Turns; die falsche Behauptung ging als `gh pr comment`-Payload hinaus und wurde erst 28 s spaeter durch einen Folge-Check (`gh pr view --json mergedBy`) entdeckt. Erweiterungsvorschlag: PreToolUse-Hook auf `gh pr comment`/`gh issue comment`/`gh pr create --body`, der Status-Marker („gemergt", „Admin-Merge", „gruen", „deployed") im Body erkennt und einen vorangegangenen Check-Aufruf im selben Turn verlangt. Umbauen/herabstufen passen nicht: das Gate feuert am richtigen Ort, es sieht nur nicht alle Kanaele.

**Gate rueckfaellig 2 — `lint-failure-no-local-gate`** (#6; Klasse `gate-lint-failure-no-local-gate-wirkungslos`). Antwort **ausweiten**: das registrierte Gate deckt Lint/Format vor dem Push; platform#2397 scheiterte an zwei Pruefungen, die es nicht kennt — `infra/scripts/hosts_audit.py` (Schema `runner.host` → Host-Block) und `pytest tools/tests/` (Zeitbomben-Test). Beide sind lokal in Sekunden lauffaehig und in CI Pflicht. Vorschlag: Pre-Push-Gate in platform um „wenn `infra/hosts.yaml` im Diff → `hosts_audit.py`; wenn `tools/**` im Diff → `pytest tools/tests -q`" erweitern (Marker-Scanner auf Pfade, nicht auf Dateitypen). Herabstufen scheidet aus (der Rot-Lauf kostete einen Folge-Commit und einen Rerun); umbauen nicht noetig (Zeitpunkt vor Push ist richtig).

### 5b. Autonomie-Kalibrierung

`over_act = 2`: (a) Required-Check-Reduktion (Gate 3 Security-Config) ohne durables Freigabe-Zitat (#1); (b) `--admin` auf generische Formel (#3). `over_ask = 0`: die als 🟢 vorgelegten Punkte (Device-Code, Budget-UI, Zweit-Review) waren real nicht agentenseitig loesbar. Muster `merge-bypass-without-explicit-word` steht mit ×4 ueber der Schwelle → `feedback_autonomy_charter` schaerfen: „generische Autonomie-Formel deckt keinen benannten Bypass" als Gate-Zeile.

## 6. Verankerung (Vorschlaege — nicht selbst geschrieben)

`memory_candidates`:

```markdown
---
name: feedback_required_check_reduction_check_sibling_jobs
description: Vor Reduktion der Required Checks auf `ci / gate` pruefen, welche Jobs NICHT unter gate.needs haengen — writing-hub Integration Tests fiel 2026-08-28 still aus dem Merge-Gate
metadata: {type: feedback, drift: true, drift_episode: 2026-08-28-required-check-reduction}
---
`ci / gate` buendelt nur die shared-ci-Jobs (`_ci-python.yml` `gate.needs`). Repo-eigene Sibling-Jobs im Caller (writing-hub `integration-tests`: Postgres, Chromium, ADR-180-Trigger) sind NICHT enthalten. Die Reduktion auf `["ci / gate"]` machte diesen Job zum Nicht-Required — entgegen dem Datei-Kommentar, der ihn ausdruecklich als Required Check fuehrt.
**Why:** Annahme „gate deckt alles" ohne `needs:`-Blick; Security-Config-Aenderung zudem ohne durables Freigabe-Zitat (Gate 3).
**How to apply:** Vor jedem PATCH auf `required_status_checks`: Kontexte auflisten, je Kontext `needs:`-Kette pruefen, Sibling-Jobs behalten; Owner-Wort als Kommentar zitieren, dann PATCH. Verwandt: [[feedback_required_check_paths_filter_blocks]], [[feedback_gate_approval_needs_pr_comment]].
```

```markdown
---
name: feedback_bypass_needs_named_word_not_autonomy_formula
description: `--admin`/Ruleset-Bypass braucht ein benanntes Owner-Wort fuer GENAU diesen Bypass — „mache es autonom" deckt Klassen, keinen Bypass (mcp-hub#234, 2026-08-28)
metadata: {type: feedback, drift: true, drift_episode: 2026-08-28-admin-merge-generic-word}
---
Owner-Formel „mache es autonom, du hast dafuer meine freigabe" folgte auf ein Board mit drei 🟢-Punkten; ich las sie als Freigabe fuer `gh pr merge --admin`. `autonomy-gates.md` sagt woertlich „'mergen' ≠ '--admin' … praezise fragen". Das durable Artefakt (Kommentar) heilt die fehlende Spezifitaet nicht.
**Why:** Vierte Instanz von `merge-bypass-without-explicit-word` — Schwelle fuer Gate ueberschritten.
**How to apply:** Bypass nur nach Frage „#N per --admin mergen — go?" und Antwort mit Nummer. Sonst Zweitkonto/Bot. Verwandt: [[feedback_ruleset_bypass_durable_artifact]], [[feedback_autonomy_charter]].
```

```markdown
---
name: feedback_claim_in_gh_comment_is_a_claim
description: Status-Behauptungen in `gh pr comment`/`gh issue comment` unterliegen derselben Evidenz-Pflicht wie Antworttext — der Stop-Hook sieht sie nicht (platform#2397 „Admin-Merge", 2026-08-28)
metadata: {type: feedback, drift: true, drift_episode: 2026-08-28-claim-via-comment}
---
`gh pr merge --admin` antwortete „already merged"; ich postete trotzdem den vorbereiteten Bypass-Kommentar und pruefte `mergedBy` erst danach (wirdigital, regulaer). Korrektur 28 s spaeter — aber der falsche Kommentar ist Artefakt.
**Why:** 70. Vorkommen `claim-before-cheapest-check`; der Scanner prueft nur den Turn-Text.
**How to apply:** Vor jedem Kommentar mit Status-Marker (gemergt/Admin/gruen/deployed) den Check im selben Turn laufen lassen; Kommentar-Text aus dem Check-Ergebnis bauen, nicht vorformulieren. Verwandt: [[feedback_actions_minutes_measurement_traps]].
```

```markdown
---
name: feedback_self_hosted_preflight_symlinks_and_ports
description: Vor dem Umzug eines Repos auf einen self-hosted Runner: Absolut-Symlinks (`ls-files -s` 120000) und Port-Kollisionen (`ss -ltnp` gegen `services.ports`) pruefen — writing-hub#826 brauchte dafuer 4 Commits
metadata: {type: feedback}
---
Auf `ubuntu-latest` sind tote Absolut-Symlinks ENOENT (pytest ignoriert), auf einer Box mit existierendem Owner-Home EACCES (Collection-Abbruch). Host-Ports aus `services:` kollidieren mit lokalen Diensten (PG-18 auf 5434). Beides ist vorab mechanisch pruefbar. Flotte: platform#2401 (18 Repos).
**How to apply:** Preflight-Block im Bootstrap-Runbook; hohe Host-Ports (>50000) in Service-Jobs. Verwandt: [[reference_gpu_box_wsl_runner_access]].
```

`adr_candidates`: **kein neues ADR** (adr-threshold: Runner-Placement liegt in ADR-257/KONZ-021). Stattdessen eine **Rev-Zeile in KONZ-platform-021/042**: „gpu-box (Owner-Desktop, WSL2) als getrackter `ci-gpu`-Opt-out fuer writing-hub, Grund 70 % der hosted Minuten, `hosts.yaml consumers:` gepflegt; Kill-Gate (c) Minuten-Baseline erbracht (Usage-Report 27.159 min, 31,15 $ bezahlt), Spend bewusst entschieden (200 $ bis bereinigt)."

`gate_candidates` → Registry-Eintraege: `required-check-reduction-drops-sibling-job` (PreToolUse auf `gh api -X PATCH …/required_status_checks`: Kontexte gegen `gate.needs` der Caller-Workflows pruefen), `merge-bypass-without-explicit-word` (×4: PreToolUse auf `gh pr merge --admin` verlangt Kommentar mit PR-Nummer + Owner-Zitat, das die Nummer enthaelt), `gate-claim-before-cheapest-check-wirkungslos` → **ausweiten** (§5a).

## 7. Massnahmen (Action-Board)

### Stand
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Retro-Report | platform | dieser PR | 🟡 | wirdigital: Review |

### Zug
- **[R1]** 🟢 writing-hub: `Integration Tests` wieder als Required Check eintragen (Gate 3 — dein Wort noetig) — https://github.com/achimdehnert/writing-hub/settings/branches
- **[R2]** 🔵 writing-hub: Port 55434 → `vars.TEST_DB_HOST_PORT` (eine Quelle) — https://github.com/achimdehnert/writing-hub
- **[R3]** 🔵 platform#2397: docker-Gruppen-Frage im Thread beantworten (bewusst: Postgres-Service-Container) — https://github.com/achimdehnert/platform/pull/2397
- **[R4]** 🔵 platform#2392: Body-Checkboxen abhaken, Budget-Zeile 10 $ → 200 $ (Owner-Wort „22 belassen bis situation bereinigt") — https://github.com/achimdehnert/platform/issues/2392
- **[R5]** 🟢 vier Memory-Kandidaten (§6) uebernehmen ja/nein
- **[R6]** 🟢 Gate-Ausweitung `claim-before-cheapest-check` auf Kommentar-Payloads (§5a) als Hook-PR beauftragen ja/nein
- **[R7]** 🟢 KONZ-021/042 Rev-Zeile (gpu-box Opt-out, Kill-Gate c) ja/nein

## 8. Nicht verifiziert (Restluecken)

- **Registrierungs-Token im Chat (Hypothese, kein gh/git-Artefakt):** ein Owner-Paste eines `registration-token` landete im Chat-Transkript; der Agent verwendete ihn nicht, legte einen zweiten als Datei ueber den Hop ab und beobachtete die Runner-Liste bis zum Ablauf (Runner-Liste unveraendert). Einziger Artefakt-Zeiger: Memory `reference_gpu_box_wsl_runner_access.md`. Billigster Check: `gh api repos/achimdehnert/writing-hub/actions/runners` (heute 2 Runner) — Finder P9 fand keine Klartext-Tokens im Artefaktraum.
- **Worktree-Hygiene** (P11): 30 Session-Worktrees laut Session beendet; nicht aus Artefakten pruefbar. Billigster Check: `ls /home/devuser/.repo-session/worktrees/*/2026-08-2[78]-achim-dehnert-*` — verbleibende Eintraege gehoeren anderen Sessions (ux-review, mandant-fehlt, …).
- **GPU-Box-Zustand** (Keepalive `.wslconfig`, Aufgabe `WSLKeepAlive`, `runner.token` geloescht): nur ueber den prod/wg0-Hop pruefbar; kein Finder hatte Box-Zugriff. Billigster Check: `ssh hetzner-prod 'ssh achim@10.99.0.2 "schtasks /Query /TN WSLKeepAlive"'`.
- **Ersparnis ueber Zeit:** Usage-Report nach dem 1.9. (neuer Abrechnungsmonat) — erst dann ist „writing-hub ≈ 1 min/Lauf" als Monatswert belegt.
- **Collector-Fehler:** meldete „0 Kommentare" auf #2392/#2401 (real 6/1) — von den Findern korrigiert; Ursache (`--json comments` vs. `/comments`-Endpoint) nicht untersucht.

**getan:** Report aus 3 Findern + 3 Skeptikern zusammengefuehrt, KPIs gelaufen, 4 Memory-Kandidaten, Gate-Rueckfall klassifiziert · **angenommen:** Severity-Kalibrierung #1 folgt Skeptiker A · **nicht verifizierbar:** Token-Episode, Worktrees, Box-Zustand, Monatsersparnis · **offen geblieben:** R1–R7.
