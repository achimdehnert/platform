---
retro_schema: 1
date: 2026-09-03
repo_scope: [platform, dev-hub, aifw, writing-hub, travel-beat, illustration-hub, shared-ci]
session_id: 0f59ce
footprint: deep
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 2
pre_refuted: 1
over_ask: 1
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [same-file-serial-prs, gate-step-only-on-pr-path-undrilled, report-dir-default-public-repo, bot-taboo-path-not-prechecked, api-quota-exhausted-before-pr-verify, adr-status-not-updated-after-execution, shared-egress-to-external-llm-ui, runner-offline-pr-never-green, docs-merge-triggers-prod-sync]
recurring_findings: [deferred-item-no-tracking-issue, handover-stale-vor-merge, worktree-midsession-accumulation, same-file-serial-prs]
gates_caught: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, untested-tool-module-green-gate, deferred-item-no-tracking-issue]
over_ask_klassen: [docs-pr-anlage-freigabe]
over_act_klassen: []
widerlegung: "2 gekippt, 1 neu"
streichkandidaten: [retro-phase-6-extern-handoff]
---

# Session-Retro 2026-09-03 — platform (+6 Repos) — Future-Readiness-Audit (0f59ce)

Reviewte Sitzung (2026-09-02 bis 2026-09-03): Owner-Frage „ist dieser Master-Prompt zukunftstauglich,
adaptiere ihn". Ergebnis: Prompt v2.1→v2.3 ([#2727](https://github.com/achimdehnert/platform/pull/2727),
[#2729](https://github.com/achimdehnert/platform/pull/2729), [#2756](https://github.com/achimdehnert/platform/pull/2756)),
Rubrik-Generator, Evidenz-Generator + deterministischer Bewerter ([#2767](https://github.com/achimdehnert/platform/pull/2767), offen),
drei Canaries + Inventur über 56 Repos (dev-hub [#317](https://github.com/achimdehnert/dev-hub/pull/317)),
CI-Fixes ([#2731](https://github.com/achimdehnert/platform/pull/2731)), Pinning-Welle 1 in 7 Repos
([#2728](https://github.com/achimdehnert/platform/pull/2728), [#2734](https://github.com/achimdehnert/platform/pull/2734),
[shared-ci#67](https://github.com/iilgmbh/shared-ci/pull/67), [dev-hub#318](https://github.com/achimdehnert/dev-hub/pull/318),
[aifw#63](https://github.com/achimdehnert/aifw/pull/63), [writing-hub#1001](https://github.com/achimdehnert/writing-hub/pull/1001),
[illustration-hub#321](https://github.com/achimdehnert/illustration-hub/pull/321), [travel-beat#94](https://github.com/achimdehnert/travel-beat/pull/94) offen),
Tracking [#2736](https://github.com/achimdehnert/platform/issues/2736), [#2737](https://github.com/achimdehnert/platform/issues/2737).

**Methode:** Footprint `deep` (13 PRs, 7 Repos, Prod-relevant über Deploy-Reusables von shared-ci;
Reduktion auf `full` nicht zulässig: Befundschätzung > 10). 1 Collector (haiku, 557 Zeilen
Artefakt-Sammlung) + 3 Finder (sonnet, je Dimension) + 1 gebündelter Skeptiker (sonnet, 4 Punkte:
ein Finder-Widerspruch, drei Bewertungsbefunde) + Widerlegungsbahn (Opus, 3b: 2 REFUTED gekippt, 1 neue Dimension) + Meta (sonnet) +
Extern-Briefing. Kommandobelegte Befunde gingen nicht durch den Skeptiker (Klassentabelle 0.1).

## Phase 0.0 — Wirkungsbilanz (`gate_wirkung.py`, zuerst gelaufen)

| Gate (RUECKFAELLIG lt. Registry) | Diese Sitzung | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 8× gefeuert, jedes Mal Check, 3 Korrekturen (Zählungen, Bot-Annahme) | gefangen | keine — Wirksamkeitsbeleg (`gates_caught`) |
| untested-tool-module-green-gate | Trigger-Deckungstest schlug bei #2767 lokal an, vor Push behoben | gefangen | keine |
| scope-checkpoint-not-durably-recorded | 3× gefeuert, 2 Checkpoints + Owner-Antworten auf #2728/#2737 | gefangen | keine |
| melder-ohne-leser | kein Melder gebaut | nicht berührt | n/a |
| worktree-midsession-accumulation | 12 Worktrees angelegt, 6 nach Merge nicht geschlossen (erst in Phase 0 dieser Retro) | Ausgang: Reaper greift erst am SessionEnd | Rückfall verbucht (§5a), keine zweite Gate-Kopie |

## 1. Executive Summary

- Ziel erreicht und übertroffen: Prompt in drei Canaries messbar stabilisiert (Δ Readiness 4 bei zwei
  unabhängigen Läufen), Bewerter ersetzt Modell-Worker (150–190k Token → Sekunden), Welle 1 Pinning in
  6 von 7 Repos gemergt.
- Der schwerste Befund ist eine **Zusage ohne Artefakt**: die Regel „Berichte nie ins öffentliche
  platform" steht nur in einem Issue-Kommentar; Prompt (`REPORT_DIR`) und Werkzeug prüfen nichts (#1).
- Zwei **Wirkungslücken**: shared-ci-Pinning ohne Folge-Tag wirkt für `@v1`-Konsumenten nicht (#2);
  ADR-262 steht nach flottenweiter Umsetzung noch auf `not-started` (#3).
- Rework-Kette #2728→#2731→#2734: ein PR-only-Gate ohne Drill, ein Bot-Tabu-Pfad ohne Vorabcheck —
  Kosten ~31 Min + ~6h50 Wartezeit (#5, #6).
- Die Widerlegungsbahn hat zwei Skeptiker-Urteile gekippt: der Scope-Checkpoint kam 58 Min NACH einem
  Prod-relevanten Push-Sync (#9), und travel-beat hängt nicht an einem Backlog, sondern an zwei offline
  Runnern — der PR wird von allein nie grün (#11). Neu: die Schleuse `~/shared` ist ein Ausleitungspfad
  zum externen LLM-Anbieter, nicht nur ein Ablageort (#14).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | REPORT_DIR-Default zeigt auf das öffentliche platform; Sichtbarkeits-Regel nur als Issue-Kommentar, weder Prompt-Zeile noch Werkzeug prüfen sie (Prompt kennt nur eine Secret-/Personendaten-Kontrollprobe, Z.153) | fehlende Validierung | hoch (präventiv, nicht eingetreten: 0 Dateien in platform, Berichte in dev-hub PRIVATE) | SURVIVES (Skeptiker K1; 3b: Kern hält, Teilsatz „prüft nichts" präzisiert) | `git show origin/main:docs/prompts/future-readiness-audit.md` Z.66 `REPORT_DIR: platform/docs/audits/…`; `gh pr diff 2756` 0× REPORT_DIR; `gh pr diff 2767` 0× visibility; #2737 Kommentar 07:02Z „Regelkandidat 11 … v2.3-PR #2756" | neu: report-dir-default-public-repo |
| 2 | shared-ci#67 gemergt ohne Folge-Tag; Tag-Schritt nur im PR-Body, kein Issue. 3b: es gibt kein `v1`-Band-Tag und keinen `@v1`-Konsumenten — Konsumenten pinnen exakt v1.1.11–13; Dependabot bietet gerade Bumps auf v1.1.14 (VOR der Härtung) an | Prozesslücke | mittel | SURVIVES (kommandobelegt; Wirkungsaussage durch 3b präzisiert) | `git -C shared-ci tag --sort=-v:refname` v1.1.14 (2026-08-30) < mergedAt 2026-09-03T08:40:14Z; `gh issue list` shared-ci/platform ohne Issue für diesen Tag | deferred-item-no-tracking-issue ×36 → **Gate rückfällig** (§5a) |
| 3 | ADR-262 `implementation_status: not-started` trotz 7-Repo-Umsetzung | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git show origin/main:docs/adr/ADR-262-sha-pin-github-actions.md` → status proposed / not-started; PR-Filelisten #2728/#2734 ohne ADR | neu: adr-status-not-updated-after-execution |
| 4 | PRs #2728/#2727 angelegt, CI bei Anlage ungeprüft — REST-Kontingent erschöpft (Inventur + Canaries) | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | #2728 createdAt 16:26:16Z, eigener Anker-Kommentar 16:27:04Z „CI … nicht geprüft … Kontingent bis 17:23 UTC erschöpft" | neu: api-quota-exhausted-before-pr-verify |
| 5 | #2731 ist Rework: deploy-sh-gate-Schritt lief nur auf `pull_request`, nie gedrillt, brach mit „no merge base" | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | #2731 Body; #2728 Re-Run nach Merge von main, mergedAt 21:33:20Z (+31 Min); Konflikt in derselben Datei `.github/workflows/deploy-sh-gate.yml` | same-file-serial-prs ×8 (OHNE Gate); neu: gate-step-only-on-pr-path-undrilled |
| 6 | #2734 als Rest aus #2728: Bot-Tabu-Pfad `bot-review.yml` nicht vorab abgeglichen | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | #2734 Titel „(Rest aus #2728)", createdAt 21:29:56Z → mergedAt 04:20:25Z (~6h50); `tools/bot_review_kandidaten.py` TABU-Liste | neu: bot-taboo-path-not-prechecked |
| 7 | AGENT_HANDOVER.md bildet die Sitzung nicht ab (Stand 7902c652, 2026-09-02) | Kommunikation | mittel | SURVIVES (kommandobelegt) | `git show origin/main:AGENT_HANDOVER.md \| head -80` ohne #2727–#2767, #2736/#2737 | handover-stale-vor-merge ×19 → **Gate rückfällig** (§5a) |
| 8 | 6 Worktrees gemergter PRs blieben bis zur Retro offen | Prozesslücke | niedrig | SURVIVES (kommandobelegt, Phase 0) | `ls -d ~/.repo-session/worktrees/*/2026-09-0[23]-achim-dehnert-*` vor/nach `repo-session.sh end` | worktree-midsession-accumulation ×5 → **Gate rückfällig** (§5a) |
| 9 | Scope-Checkpoint 58 Min nach dem ersten Prod-relevanten Schritt: Merge #2727 löste `opt-platform-sync.yml` (push main, bewusst ohne paths-Filter, self-hosted root, Prod-Werkzeugklon) aus | Kommunikation | mittel | SURVIVES (3b GEKIPPT: Skeptiker K2 nahm „Doku-Merge = keine Prod-Wirkung" an) | Lauf 2026-09-02T16:30:20Z push success „Merge pull request #2727"; Checkpoint-Kommentar 17:28:45Z; Klon inhaltlich unberührt (nur docs/prompts) | neu: docs-merge-triggers-prod-sync |
| 10 | #2767 verletzt Größen-Guardrail (1976 > 600 Zeilen), Regel ignoriert | fehlende Validierung | niedrig | REFUTED (Skeptiker K3) | `agents/guardian.py` G-004 = `Gate.AUTO_WARN`, guardian-Check SUCCESS; Split hätte Halb-Feature erzeugt | — |
| 11 | travel-beat#94 wird nie grün: beide self-hosted Runner offline, Run seit 08:26:29Z queued; der billigste Check stand in §8 und wurde nicht gezogen | fehlende Validierung | mittel | SURVIVES (3b GEKIPPT: Skeptiker K4 nahm „Runner-Backlog" an) | `gh api …/actions/runners` → 2 Runner, beide `offline`; dieselbe prod-server-Rolle in 4 anderen Repos online; Tracking-Teil hält (#2737) | neu: runner-offline-pr-never-green |
| 12 | „REPORT_DIR-Regel mit #2756 nachgezogen" (Finder E3) | Wissenslücke | — | REFUTED (Skeptiker K1) | s. #1 | — |
| 13 | travel-beat#94 „FAIL:3" (Collector) | fehlende Validierung (Phase 1) | — | pre_refuted (drei Finder unabhängig: QUEUED/PENDING) | `gh pr view 94 --json statusCheckRollup` conclusion leer | — |
| 14 | Ausleitung der Sicherheitsposture (secret_scanning/private-Flags, Org-Namen) über `~/shared` (777) an die externe LLM-Oberfläche des Owners; T0-Inventur privater Repos lag dort (131× secret_scanning, 32× private) | Prozesslücke | mittel | SURVIVES (3b NEU) | #2088 Kommentar 2026-09-02T15:04:38Z (Flatrate-Oberfläche); ~/shared 15 Dateien/~800 KB; v2.2-Briefing 7× secret_scanning, 2× private; Prompt Z.155 „Inhalte dieser Orgs verlassen die Sitzung nicht"; Secret-Muster 0 Treffer mit Positivkontrolle | neu: shared-egress-to-external-llm-ui |

Entlastungen (geprüft, kein Befund): Prompt-Iteration v2.1→v2.3 an einem Tag ist evidenzgestützt
(#2737 Messwerte je Canary); kein Duplikat #2736-Skript ↔ `tools/future_readiness_evidence.py`;
SHA-Auflösung korrekt (ls-remote peeled, Stichprobe actions/checkout v7 = 3d3c42e5…), Dependabot
nachgezogen; Commit-Konventionen eingehalten; Berichtsablage tatsächlich in dev-hub (privat);
Scope-Erweiterung owner-gegated (#2737 „146 mergen").

## 3. Scorecard

| Dimension | Score | Verankerung |
|---|---|---|
| zielerreichung | 4 | Auftrag erfüllt (Prompt + Messung + Werkzeug); Welle 1 für `@v1`-Konsumenten noch unwirksam (#2), #2767 offen |
| architektur_design | 4 | Rubrik/Schema/Prompt aus einer Quelle mit `check`; Bewerter statt Modell-Worker; REPORT_DIR-Default aber ungeschützt (#1) |
| code_konventionstreue | 4 | Commit-Format, Attribution, `test_should_*`, Ruff eingehalten; Guardian-Hinweis G-004 (#10, refuted) |
| risiko_debt | 2 | Offene Reste: #1, #2, #3; dazu Ausleitungspfad #14 und ein Repo ohne Runner #11 |
| prozess_effizienz | 3 | Rework-Kette #2731/#2734 (#5, #6), API-Kontingent (#4), Worktrees (#8) |
| entscheidungsqualitaet | 3 | Iteration evidenzgestützt, Ad-hoc-Skript → Werkzeug mit Tests; aber Checkpoint 58 Min nach Prod-Sync (#9) und §8-Check nicht gezogen (#11) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Regel „nicht ins öffentliche Repo" als Kommentar auf #2737 (07:02Z), Prompt-Zeile unverändert | Regel im selben Zug in die `REPORT_DIR`-Zeile UND als Sichtbarkeits-Check in `future_readiness_evidence.py` (`gh repo view --json visibility`, Abbruch bei public) | #1 |
| shared-ci#67 gemergt, Tag-Schritt im PR-Body „bleibt beim Owner" | Provider-Merge ohne Tag ist unvollständig: Issue in shared-ci mit Tag-Vorschlag im selben Zug anlegen (Anker), Handover-Zeile | #2 |
| Pinning in 7 Repos gemergt, ADR-262 auf `not-started` | Umsetzungs-PR eines ADR-Themas ändert das ADR-Frontmatter mit (`implementation_status`, Repo-Liste) oder legt das Issue dazu an | #3 |
| PR angelegt, CI ungeprüft, Kontingent leer (16:26Z) | Vor Inventur-/Canary-Läufen `gh api rate_limit` lesen; PR-Anlage erst mit ≥ 500 verbleibenden Calls, sonst warten statt „ungeprüft" | #4 |
| deploy-sh-gate-Schritt nur `if: pull_request`, nie auf einem PR gelaufen, Fehlalarm bei #2728 | Ein Gate-Schritt mit Event-Bedingung bekommt einen Drill-PR, bevor er als Gate zählt (`gate_namensdeckung.py`); Fix #2731 hätte VOR #2728 laufen müssen, Same-file-Konflikt vermieden | #5 |
| bot-review.yml im 63-Dateien-PR, Bot verweigert, Rest-PR #2734 wartet 6h50 | Vor einem Sammel-PR `tools/bot_review_kandidaten.py` TABU-Liste gegen die Dateiliste prüfen; Tabu-Dateien von Anfang an getrennt | #6 |
| AGENT_HANDOVER.md Stand 2026-09-02 abends, 13 Merges danach | Handover-Block bei jedem Scope-Checkpoint mitziehen (nicht erst am Session-Ende) — der Checkpoint ist der natürliche Schreibmoment | #7 |
| Worktrees nach Merge stehen gelassen | `repo-session.sh end` gehört in denselben Zug wie der Merge (Merge-Funktion ruft `end`), nicht in den Reaper | #8 |
| Merge #2727 (nur docs/) löste `opt-platform-sync.yml` auf dem Prod-Werkzeugklon aus; Checkpoint 58 Min später | „Prod-Schritt" = jeder Merge nach main in einem Repo mit push-Sync ohne paths-Filter; Checkpoint VOR dem ersten Merge, nicht vor dem ersten Deploy-Workflow-Edit | #9 |
| §8 nannte den billigsten Check (Runner-Liste), niemand zog ihn; PR wartete auf einen Runner, den es nicht gab | Ein QUEUED-Check > 15 Min löst den Runner-Check aus (`gh api …/actions/runners`), bevor „wartet" berichtet wird | #11 |
| Briefings mit Sicherheitsposture nach `~/shared` (777), Owner kopiert sie in die externe Oberfläche | Vor jedem Extern-Briefing Egress-Klasse prüfen: Org (ttz-lif/meiki-lra nie), Datenklasse (private Repo-Posture nur nach Owner-Wort), Rest der Schleuse nach Übergabe löschen | #14 |

## 5. Längsschnitt (`retro_kpis.py`, 112 Reports)

| Slug | Zähler vorher | Status | Konsequenz |
|---|---|---|---|
| deferred-item-no-tracking-issue | ×36 | Gate advisory, revised 2026-09-03 | **rückfällig** (#2) → §5a |
| handover-stale-vor-merge | ×19 | Gate process, revised 2026-08-20 | **rückfällig** (#7) → §5a |
| worktree-midsession-accumulation | ×5 | Gate process, revised 2026-08-23 | **rückfällig** (#8) → §5a |
| same-file-serial-prs | ×8 | **OHNE registriertes Gate** | Gate-PR-Pflicht (Kandidat, Owner-Zug) |
| scope-checkpoint-not-durably-recorded | ×25 | Gate advisory | gefangen 3× → `gates_caught` |
| claim-before-cheapest-check | ×… | Gate blocking | gefangen 8× → `gates_caught` |

Memory-Abgleich (`grep` in `MEMORY.md`): „accepted ≠ umgesetzt" (`feedback_accepted_adr_amendment_needs_execution_pr`) existiert → #3 ist ein Rückfall auf ein bestehendes Memory, kein neues; „Bewusst Ausgelassenes → Tracking" steht in CLAUDE.md → #2 ebenfalls. Neue Slugs (×1): report-dir-default-public-repo, gate-step-only-on-pr-path-undrilled, bot-taboo-path-not-prechecked, api-quota-exhausted-before-pr-verify, adr-status-not-updated-after-execution.

### 5a. Rückfall-Prüfung (`gate_wirkung.py`)

| Gate | Rückfall | Ursache | Antwort | Registry-Edit |
|---|---|---|---|---|
| deferred-item-no-tracking-issue | #2 (Tag-Schritt nur im PR-Body) | **Quelle**: der Hook liest den Chat-Turn; ein „🟢 dein Zug"-Item mit Prod-Gate (Tag) gilt ihm als Owner-Aktion, nicht als Auslassung | **ausweiten**: Zug-Items mit Prod-/Publish-Gate brauchen ein Artefakt (Issue) im selben Turn | kein `revised` ohne neue Positivkontrolle (`gate_verankerung_check.py --neu` weist das ab); stattdessen Kandidat `deferred-item-owner-zug-prod-gate` in der Registry-`kandidaten`-Liste (#2234), in diesem PR |
| handover-stale-vor-merge | #7 (13 Merges ohne Handover-Update) | **Quelle**: Modul `scripts/checks/agent_handover_freshness_check.py` prüft die Überschrift gegen den letzten Datei-Commit; Merges per `gh pr merge` in 6 anderen Repos sieht es nicht | **ausweiten** auf Cross-Repo-Merges der Sitzung (Scope-Checkpoint als Schreibmoment) | `--neu`-Check meldet „keine positivkontrolle", nicht verankerungsfähig; Kandidat `handover-stale-cross-repo-merge` in `kandidaten` (#2234), in diesem PR; Gate-PR mit Drill = Owner-Zug |
| worktree-midsession-accumulation | #8 | **Ausgang**: Reaper wirkt erst am SessionEnd; mid-session kein Signal | **umbauen**: `repo-session.sh end` in den Merge-Zug (Skill `pr-merge`) statt in den SessionEnd-Reaper | Kandidat `worktree-end-on-merge` in `kandidaten` (#2234), in diesem PR; Umbau-PR = Owner-Zug (A8) |

### 5b. Autonomie-Kalibrierung

- `over_ask: 1` — Klasse `docs-pr-anlage-freigabe`: Freigabe für Commit/PR einer reinen Prompt-Doku
  ([#2727](https://github.com/achimdehnert/platform/pull/2727), Owner-Wort „39 ok go") eingeholt, obwohl
  deterministisch und reversibel. Nominierung: `retro_kpis.py --nominierung` (Klasse ≥2 ⇒ NOMINIERT).
- `over_act: 0` — jeder Prod-/Merge-Schritt hatte ein dokumentiertes Owner-Wort (#2728 Kommentar
  „62 go", #2737 „146 mergen"); Issues #2736/#2737 autonom angelegt (Tracking, kein Gate).

## 6. Verankerung (Vorschläge — der Mensch entscheidet)

`memory_candidates`:

```markdown
---
name: feedback_report_dir_default_must_not_be_public_repo
description: Audit-Berichte mit privaten Repo-Metadaten nie in ein öffentliches Repo — Regel gehört in die Konfig-Zeile und ins Werkzeug (visibility-Check), nicht in einen Issue-Kommentar
metadata: {type: feedback}
drift: true
drift_episode: 2026-09-03-report-dir-public
---
Future-Readiness v2.x setzte REPORT_DIR auf platform (PUBLIC); die Inventur nennt private Repos samt
Sicherheits-Einstellungen. Die Korrektur landete als "Regelkandidat 11" in platform#2737 — Prompt-Zeile
und Werkzeug blieben unverändert (Retro 0f59ce #1).
**Why:** Eine Regel, die nur ein Kommentar kennt, gilt für die nächste Sitzung nicht.
**How to apply:** Regel im selben Zug in die Zeile schreiben, die sie betrifft, und im Werkzeug
prüfen (`gh repo view --json visibility` → Abbruch bei public). [[feedback_deferred_item_needs_tracking_artifact]]
```

```markdown
---
name: feedback_gate_step_with_event_condition_needs_drill_pr
description: Ein CI-Gate-Schritt mit `if: github.event_name == 'pull_request'` zählt erst als Gate, wenn er einmal auf einem PR gelaufen ist — sonst Fehlalarm beim ersten echten PR
metadata: {type: feedback}
drift: true
drift_episode: 2026-09-03-deploy-sh-gate-merge-base
---
deploy-sh-gate.yml: Versionscheck nur auf pull_request, fetch-depth 1, Dreipunkt-Diff → "no merge base"
→ `if ! git diff --quiet` las den Abbruch als "geändert" (platform#2731, Fehlalarm auf #2728).
**Why:** push-Läufe testen den Schritt nie; die Kombination Event-Bedingung + shallow checkout ist unsichtbar.
**How to apply:** Merge-Base explizit (`git merge-base`), fetch-depth 0, und ein Drill-PR vor dem
Gate-Status (`gate_namensdeckung.py`). Fix-PR VOR dem Sammel-PR, sonst Same-file-Konflikt.
```

```markdown
---
name: feedback_bot_taboo_paths_before_bulk_pr
description: Vor einem Sammel-PR über .github/ die TABU-Liste von tools/bot_review_kandidaten.py gegen die Dateiliste prüfen — bot-review.yml gibt der Bot nie frei
metadata: {type: feedback}
---
platform#2728 (63 Workflow-Dateien) blieb 20 Min ohne Freigabe: "Tabu-Pfad — bleibt Mensch", weil
bot-review.yml dabei war; Rest-PR #2734 wartete 6h50 auf einen zweiten Menschen.
**How to apply:** `python3 -c 'import tools.bot_review_kandidaten as b; print(b.TABU)'` gegen `git diff --name-only`;
Tabu-Dateien von Anfang an in einen eigenen PR.
```

`adr_candidates`: keiner — ADR-262 existiert; Befund #3 ist Pflege (`implementation_status`, Repo-Liste), kein neues ADR.

`gate-registry` (in diesem Retro-PR, `kandidaten`-Liste): `deferred-item-owner-zug-prod-gate`, `handover-stale-cross-repo-merge`, `worktree-end-on-merge`. Beide Ausweitungen sind ohne neue Positivkontrolle laut `gate_verankerung_check.py --neu` nicht verankerungsfähig, daher Kandidat statt `revised`. `same-file-serial-prs` steht bereits in `kandidaten` (×8, ohne Gate): Owner-Entscheid Gate-PR oder `declined`.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| A1 | REPORT_DIR-Regel in Prompt-Zeile + visibility-Check im Werkzeug | platform | [#2737](https://github.com/achimdehnert/platform/issues/2737) | 🔵 | ich: Folge-PR nach Merge #2767 |
| A2 | shared-ci Tag v1.1.15 UND Dependabot-Bumps (writing-hub#1002/#1004, illustration-hub#322/#324/#325) nicht auf v1.1.14 mergen, sondern auf v1.1.15 neu anstoßen | shared-ci | [shared-ci#73](https://github.com/iilgmbh/shared-ci/issues/73) | 🟢 | du: Tag setzen (Prod-Gate), Bumps schließen |
| A3 | ADR-262 Frontmatter `implementation_status` + Repo-Liste | platform | [#2770](https://github.com/achimdehnert/platform/issues/2770) | 🔵 | ich: Doku-PR |
| A4 | Rate-Limit-Vorabcheck in `future_readiness_evidence.py` | platform | [#2736](https://github.com/achimdehnert/platform/issues/2736) | 🔵 | ich: mit A1 |
| A5 | Drill-PR-Pflicht für Event-bedingte Gate-Schritte | platform | [gate-registry.json](file:///home/devuser/github/platform/docs/governance/gate-registry.json) | 🟢 | du: Gate-Kandidat annehmen |
| A6 | TABU-Vorabcheck als Zeile im Skill `pr-merge`/Sammel-PR | platform | [bot_review_kandidaten.py](file:///home/devuser/github/platform/tools/bot_review_kandidaten.py) | 🟢 | du: Skill-Zeile freigeben |
| A7 | Handover-Block mit Session-Stand (Future-Readiness) | platform | [AGENT_HANDOVER.md](file:///home/devuser/github/platform/AGENT_HANDOVER.md) | 🔵 | ich: in `/session-ende` |
| A8 | `repo-session.sh end` im Merge-Zug | platform | [repo-session.sh](file:///home/devuser/github/platform/tools/repo-session.sh) | 🟢 | du: Skill-Zeile freigeben |
| A9 | `same-file-serial-prs` (Kandidat, ×8) als Gate bauen oder declinen; dazu die zwei neuen Kandidaten | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 | du: Entscheid |
| A10 | Streichbahn: Retro-Phase 6 (Extern-Handoff) streichen | platform | [session-retro.md](file:///home/devuser/github/platform/.windsurf/workflows/session-retro.md) | 🟢 | du: Entscheid, s. §Streichbahn |
| A11 | travel-beat: beide self-hosted Runner offline, #94 blockiert | travel-beat | [travel-beat#95](https://github.com/achimdehnert/travel-beat/issues/95) | 🟢 | du: Runner-Host prüfen |
| A12 | Egress-Regel für `~/shared`-Briefings (Org, Datenklasse, Löschung nach Übergabe) | platform | [data-sovereignty.md](file:///home/devuser/.claude/policies/data-sovereignty.md) | 🟢 | du: Policy-Zeile freigeben |
| A13 | T0-Inventur (private Posture) aus `~/shared` entfernt; Kopie liegt in dev-hub#317 | – | – | ✅ | – |
| A14 | Guardian-Docstring „> 400 Zeilen" vs. Code `threshold=600` | platform | [agents/guardian.py](file:///home/devuser/github/platform/agents/guardian.py) | 🔵 | ich: Einzeiler |

## 8. Nicht verifiziert (Restlücken)

| Lücke | billigster Check |
|---|---|
| ~~travel-beat#94 Ursache~~ — 3b hat den Check gezogen: beide Runner offline (jetzt Befund #11, Anker travel-beat#95) | – |
| Welche der 25 shared-ci-Konsumenten exakt v1.1.x pinnen und welche `@main` (3b: platform 0 echte `@v1`-Referenzen; 6 Konsumenten auf v1.1.11–13 gezählt, Rest offen) | `gh search code "iilgmbh/shared-ci/.github/workflows" --owner … --json textMatches` |
| ~~`make test` 4111 grün / Ruff nur laut PR-Text #2767~~ — 3b: `gh pr checks 2767` pytest pass (1m44s), gitleaks pass, guardian pass → geschlossen | – |
| Unabhängigkeit der externen Reviewer A/B/C (Canaries) — nur aus Dateinamen in ~/shared | Owner-Auskunft, welche Modelle/Anbieter |
| Orchestrator-MCP (403 AUTH_HEADER_REJECTED) — kein Zugriff auf dortiges Checkpoint-Protokoll | Token prüfen (`orchestrator.iil.pet`), Handover |
| Bewerter vs. Modell-Worker: Δ ≤ 5 in drei Fällen, aber n=3 | Phase C über 56 Repos mit Stichprobe von 5 Modell-Läufen |

## Widerlegung

Phase 3b (Opus, frischer Kontext, sah nur Report-Entwurf + Artefakt-Sammlung + Footprint). Verdikt:
Frage 1 SURVIVES **BESTAETIGT** (kein Befund gekippt, zwei Teilbehauptungen präzisiert) · Frage 2 REFUTED
**GEKIPPT** (#9, #11) · Frage 3 Dimension **NEU** (#14).

| Befund | Verdikt | Beleg |
|---|---|---|
| #1 | hält im Kern, Teilsatz widerlegt | Z.66 zeigt weiter auf platform (PUBLIC); aber Z.153–154 kennt eine Secret-/Personendaten-Kontrollprobe (bec7849f, vor dem Kommentar 07:02Z). Schaden nie eingetreten: `git ls-tree -r origin/main docs/audits/ \| grep -c future-readiness` = 0 |
| #2 | hält, Wirkungsaussage widerlegt | `git ls-remote --tags origin` → v1.1.14 neuestes; kein `v1`-Tag, kein `@v1`-Konsument (`git grep uses:.*iilgmbh/shared-ci origin/main` in platform = 0 echte Treffer); Konsumenten pinnen v1.1.11/12/13 |
| #3 | hält | ADR-262 status proposed / not-started |
| #7 | hält, verschärft | `git log origin/main -1 -- AGENT_HANDOVER.md` → e0018fbe 2026-09-03 11:32 (Parallelsitzung), nennt die Welle nur als „drei fremde PRs ungeprüft (#2763 #2764 #2767)" |
| #9 | **GEKIPPT → SURVIVES** | `opt-platform-sync.yml`: `on: push main`, „BEWUSST OHNE paths-Filter", self-hosted root, Prod-Klon; Lauf 2026-09-02T16:30:20Z push success „Merge #2727"; Checkpoint 17:28:45Z = 58 Min später |
| #10 | hält (REFUTED) | `agents/guardian.py` G-004 `Gate.AUTO_WARN`, `threshold=600`; Docstring sagt „> 400" (Doku-Drift → A14) |
| #11 | **GEKIPPT → SURVIVES** | `gh api repos/achimdehnert/travel-beat/actions/runners` → 2 Runner, beide offline; Run 33733359397 seit 08:26:29Z queued (68 Min); prod-server-Rolle in 4 anderen Repos online; kein Deploy seit 2026-08-29 |
| #13 | hält (pre_refuted) | `gh pr checks 94`: skipping/pending/pass, kein failure |
| **#14 NEU** | Ausleitung privater Sicherheitsposture über ~/shared an externe LLM-Oberfläche | #2088 Kommentar 15:04:38Z; ~/shared 777, 15 Dateien; v2.2-Briefing 7× secret_scanning; T0-Inventur 131× secret_scanning, 32× private; Prompt Z.155 „verlassen die Sitzung nicht"; Secrets 0 (Positivkontrolle 1) |

Erfolglos geprüft (kein Befund): Deploy-Zustand der 5 gemergten Konsumenten nach dem Merge (dev-hub, writing-hub,
aifw, shared-ci: alle Läufe ab 08:40Z success); Testabdeckung #2767 (pytest/gitleaks/guardian pass, §8-Zeile
geschlossen); Secrets in ~/shared (0 mit Positivkontrolle). Nicht nachgeprüft (kommandobelegt übernommen): #4, #5, #6, #8.

Zwei Folgerungen für die Maßnahmen: A2 ist notwendig, aber nicht hinreichend — die offenen Dependabot-Bumps
zielen auf v1.1.14 (vor der Härtung). Und #1 hat einen Zwilling: die REPORT_DIR-Regel schützt vor dem öffentlichen
Repo, nicht vor dem Modellanbieter; der „sichere" Ausweichort ~/shared ist der Ausleitungspfad (A12).

## Streichbahn

**Kandidat: Phase 6 „Extern-Handoff" der Retro-Skill** — Belegart **kein Leser**: `ls ~/shared | grep session-retro-extern`
→ 1 Briefing, 0 Antwortdateien; `ls docs/retros | grep session-retro-extern` → genau 1 Datei (2026-06-30, writing-hub).
Seit zwei Monaten hat kein Retro-Extern-Briefing eine Antwort erzeugt, die in ein Artefakt zurückfloss; die
Methoden-Kritik, die Phase 6 liefern soll, kam in dieser Sitzung stattdessen aus den Canary-Reviews (#2737) —
dort mit Rückfluss. Vorschlag: Phase 6 streichen oder auf „nur bei explizitem Owner-Wunsch" setzen; das
Briefing dieser Retro wird trotzdem geschrieben (Pflicht `deep`), damit die Ratsche beim nächsten Mal greift,
falls es wieder ohne Leser bleibt.

## Self-Review

Meta-Agent (sonnet, sah nur Report + Skill): 8/10 Checks grün; drei Belege unabhängig nachgezogen (REPORT_DIR
Z.66, ADR-262 `not-started`, travel-beat-Runner offline — alle halten). Zwei Korrekturen eingearbeitet:
(a) §5a `worktree-midsession-accumulation` stand auf „beobachten" — keine der drei zulässigen Antworten; jetzt
**umbauen** mit Kandidat `worktree-end-on-merge`. (b) Action-Board-Zellen ohne Link (A1, A4–A8, A10, A12, A14)
→ echte bzw. `file://`-Links. `refuted_rate` 0,21 im Band (Trend 0,17/0,11/0,10/0,00/0,11/0,29/0,20).
Pfad kollisionsfrei (`git ls-tree origin/main` 0 Treffer).

---
getan: Collect (haiku), 3 Finder (sonnet), Skeptiker (sonnet, 4 Punkte), Widerlegungsbahn (Opus), Längsschnitt (`retro_kpis.py`, `gate_wirkung.py`), Anker shared-ci#73 / platform#2770 / travel-beat#95, Registry-Kandidaten.
angenommen: Kommandobelegte Befunde ohne Skeptiker (Klassentabelle 0.1).
nicht verifizierbar: s. §8.
offen geblieben: A2, A5, A6, A8, A9, A10, A11, A12 (Owner-Zug); A1, A3, A4, A7, A14 (ich, nächste Sitzung).
