---
retro_schema: 1
date: 2026-07-12
repo_scope: [dev-hub, iil-voice-agent, mcp-hub]
session_id: 3722b1
footprint: deep
footprint_reduction_reason: "Nicht reduziert — PR #133 (dev-hub) enthält eine DB-Migration (0002_alter_agentrun_agent_type.py), Bedingung (b) 'keine Migration' der Trigger-Konflikt-Regel ist verletzt, daher bleibt es bei deep trotz durchgängig freigegebener/reversibler Prod-Schritte."
findings_total: 10
findings_survived: 6
refuted_rate: 0.4
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, planned-phase-no-issue, scope-checkpoint-not-durably-recorded]
recurring_findings: [claim-before-cheapest-check, planned-phase-no-issue, scope-checkpoint-not-durably-recorded, handover-stale-vor-merge]
---

# Session-Retro 2026-07-12 — dev-hub (primär) + iil-voice-agent + mcp-hub (berührt)

## 1. Executive Summary

- Zwei Hauptstränge liefen parallel zum Ziel: Mail-Agent Stufe 2 (iil-voice-agent, 7 PRs, DSGVO-Amendment ratifiziert) und KONZ-dev-hub-001 Platform Maintenance Agent Phase 0+1 (dev-hub, 5 PRs, erster je erfolgreicher `quality_agent`-Lauf nach 5 unabhängigen Blockern).
- Alle drei unabhängigen Falsifikations-Pässe bestätigen: **kein einziger** der in dieser Session gefundenen Mängel ist eine neue Fehlerart — alle drei überlebenden Kern-Befunde (Budget-Seed ohne Drittrepo-Tracking, rsync-Tech-Debt nur als Prosa, eigene „vermutlich Dependabot"-Fehlzuschreibung) reproduzieren **bereits gate-pflichtige** Muster aus `retro_kpis.py` (`scope-checkpoint-not-durably-recorded`, `planned-phase-no-issue`, `claim-before-cheapest-check`).
- Eine ursprünglich als „kritisch" eingestufte Behauptung (Budget-Seed betrifft 10 Tenants) wurde durch unabhängige Code-Prüfung auf „additiv, 1 Tenant, kein Overwrite-Risiko" korrigiert — die Governance-Lücke (fehlendes Tracking) bleibt real, ihre Tragweite war überzeichnet.
- Ein zweiter, unabhängig entdeckter Fund: PR #128s CI-Rot wurde in einem eigenen Session-Kommentar fälschlich shared-ci v1.0.11 zugeschrieben — echte Ursache ist ein stale `iil-aifw`-Paket im Runner-Image, unabhängig vom CI-Pin.
- `risiko_debt` (2/5) bestätigt den historisch schwächsten Score (Ø 2,70 über 23 Retros) — auch diese Session.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Issue #82 (iil-voice-agent, `mail_search`-Chunk-Crash) nie mit PR #83 verknüpft, obwohl Issue #82 selbst explizit Koordination mit dem Stufe-2-Bau anmahnte | Prozesslücke | hoch | SURVIVES | Issue #82 Body ("⚠️ Koordination … Fix ggf. dort mit anlanden"); 7 PR-Bodies (#76–#84) auf "#82"/"mail_search"/"chunk" geprüft = 0 Treffer; PR #83 eröffnet 6 Min. nach Issue #82 | 1× (neuer Kandidat-Slug, nicht bereits gate-pflichtig) |
| 2 | Budget-Seed (`orchestrator_mcp/headless/seed.py::seed_budgets()`) gegen geteilte Orchestrator-Prod-DB ausgeführt — drittes Repo (mcp-hub) berührt, kein PR/Issue dort | Scope-Checkpoint-Verstoß | mittel *(korrigiert von ursprünglich „hoch/kritisch")* | SURVIVES (Kern), REFUTED (Schwere-Multiplikator „10 Tenants") | `gh issue/pr list -R achimdehnert/mcp-hub --search "budget OR seed"` = 0 Treffer; `seed_budgets()`-Code: reines `INSERT WHERE NOT EXISTS`, hart auf `DEFAULT_TENANT_ID=1` verdrahtet, kein UPDATE/DELETE | ✅ bereits gate-pflichtig: `scope-checkpoint-not-durably-recorded` |
| 3 | Staging-Deploy-Tech-Debt (rsync statt Deploy-Key) nur als Prosa in Issue-#123-Kommentar benannt, nie als eigenes Issue | Hausregel-Verstoß (Tracking-Pflicht) | mittel-hoch | SURVIVES | `gh issue list -R achimdehnert/dev-hub --search "rsync OR deploy-key"` = 0 Treffer; Cross-Repo-`gh search issues "rsync" --owner achimdehnert` ebenfalls nur Issue #123 selbst | ✅ bereits gate-pflichtig: `planned-phase-no-issue` |
| 4 | Selbstverursachte Fehlzuschreibung „vermutlich Dependabot-Bump" auf Issue #127 (17:43:47Z) — mit einem `gh pr list`-Check (PR #128 existierte seit 14:00:15Z, 3h43min vorher) vermeidbar gewesen | Evidenz-Disziplin-Verstoß | mittel | SURVIVES | Kommentartext wörtlich verifiziert; Dependabot-PRs #119/#120 bumpen nachweislich nur auf v1.0.9, können v1.0.11 nicht erklärt haben | ✅ bereits gate-pflichtig: `claim-before-cheapest-check` |
| 5 | Commit-Konvention `[typ](scope):` (literale Klammern) nur in 2 von 13 Session-Commits eingehalten — Ambiguität zwischen Org- und Repo-CLAUDE.md-Formulierung | Konventionsverstoß / Doku-Tech-Debt | niedrig-mittel | SURVIVES *(korrigierte Zahl: Finder behauptete 8/13, real 11/13 abweichend)* | vollständige `git log`-Zählung beider Repos, alle 13 Commit-Subjects einzeln geprüft | wiederkehrend, nicht neu — erstmals in dieser Tiefe quantifiziert |
| 6 | PR #128s CI-Rot fälschlich shared-ci-v1.0.11 zugeschrieben — reale Ursache: stale `iil-aifw`-Paket im Runner-Image (`missing get_action_config/QualityLevel/AIFWError`), Postgres-„database test_user"-Meldung ist bekanntes, auch in grünen Läufen toleriertes Rauschen | fehlende Validierung | niedrig-mittel | SURVIVES *(aus Skeptiker-Refutation abgeleitet)* | Log-Grep auf 3 zufälligen SUCCESS-Läufen: identische Postgres-Meldung 30–37× vorhanden trotz grün; PR-#128-Log zeigt echten `exit 1` an anderer Stelle | 1× (neu entdeckt) |

**Nicht in die Tabelle aufgenommen (REFUTED, kein Survivor):** Issue #127 behaupte fälschlich „main-Pin = v1.0.10" (REFUTED — zwei verschiedene Drift-Dimensionen verwechselt, shared-ci-Repo-Tag vs. dev-hub-Pin, beide Werte gleichzeitig korrekt); Commit `16b08f7` verstoße gegen Commit-Konvention (REFUTED — automatischer Squash-Merge-Titel, darunterliegende Arbeits-Commits folgen der Konvention); PR #128 sei von einer unkoordinierten unbekannten Parallel-Session (REFUTED — nachweislich derselbe Autor/Kontext, KONZ-017-Bump-Welle); „drei komplett unkoordinierte Bump-Versuche, keiner verlinkt" (REFUTED — Issue #127 referenziert #119/#120 explizit im Body).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Beide KONZ-Ziele substanziell geliefert (Mail-Agent Stufe 2 live+getestet, PMA Phase 0 real bewiesen); Befund #1 (Issue #82) verhindert die 5 |
| architektur_design | 4 | Adversarial-reviewte KONZ-Dokumente (3-Agenten-Panel je Konzept), Generalisierung bestehender Muster statt Neubau (`_call_orchestrator_tool`, `move_to`-Regeln) |
| code_konventionstreue | 3 | Befund #5 — reale, nicht-triviale Konventions-Abweichung über beide Repos |
| risiko_debt | 2 | Befunde #2+#3 — zwei Instanzen bereits gate-pflichtiger Tracking-Lücken; deckt sich mit historischem Tiefstwert (Ø 2,70/23 Retros) |
| prozess_effizienz | 4 | 5 execution-ready Issues → Sonnet-Delegation, alle erfolgreich + real CI-verifiziert; Befund #4 als einziger Effizienz-Rückschlag |
| entscheidungsqualitaet | 4 | Migrations-Beweispflicht statt Behauptung eingehalten (`makemigrations --check`), Cloudflare-WAF-Bypass bewusst nicht versucht, Classifier-Grenzen respektiert statt umgangen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Issue #82 wurde 6 Min. vor PR #83 erstellt und enthielt bereits eine Koordinations-Notiz zum selben Modul — PR #83 grepte nicht nach offenen Issues im berührten Verzeichnis vor dem Schreiben des PR-Bodies | Vor jedem PR, der ein Modul ändert: `gh issue list --search "in:body <modulname>"` als Pflicht-Schritt vor dem "Bewusst ausgelassen"-Abschnitt — nicht nur die eigene Erinnerung | #1 |
| Budget-Seed lief gegen mcp-hub-Prod-DB, ohne dass in mcp-hub selbst ein Tracking-Artefakt entstand (das Konzept „drittes Repo berührt" löste keinen Scope-Checkpoint-Stopp aus) | Bei jeder Schreib-Operation auf eine geteilte Infrastruktur eines FREMDEN Repos: sofort (nicht nachträglich) ein Issue in genau diesem Repo anlegen — der Scope-Checkpoint-Trigger "drittes Repo" gilt auch für reine Infra-Aktionen ohne eigenen Code-Commit dort | #2 |
| rsync-Tech-Debt wurde im Abschluss-Kommentar von Issue #123 in Prosa benannt, aber kein neues Issue dafür erstellt | "Bewusst Ausgelassenes bekommt im selben Turn ein Tracking-Artefakt" als Checkliste VOR dem Schreiben eines Abschluss-Kommentars abarbeiten, nicht danach als Fließtext einstreuen | #3 |
| Vor dem Kommentar "vermutlich Dependabot-Bump" lief kein `gh pr list` auf offene PRs im selben Repo | Jede Kausal-Behauptung über eine Zustandsänderung ("X kam vermutlich von Y") braucht den einen billigsten Check (`gh pr list`/`git log`) VOR dem Schreiben, nicht als nachträgliche Vermutung | #4 |
| Commit-Konvention wird in 11 von 13 Fällen nicht im literalen `[typ](scope):`-Format befolgt, ohne dass ein CI-Check das auffängt | Commit-Msg-Format als leichtgewichtigen `commit-msg`-Hook oder CI-Lint-Schritt verankern (schließt die Doku-Ambiguität durch eine einzige durchsetzbare Regel, statt zwei lesbare CLAUDE.md-Ebenen im Widerspruch zu lassen) | #5 |
| PR #128s CI-Rot wurde im Issue-127-Nachtrag ungeprüft dem frischen shared-ci-Bump zugeschrieben, ohne den tatsächlichen Job-Log zu lesen | Bei rotem CI-Gate: IMMER den vollständigen Job-Log nach der tatsächlichen `exit`-Ursache durchsuchen, bevor eine Korrelation (zeitliche Nähe zum letzten Bump) als Kausalität behauptet wird | #6 |

**Invariante erfüllt:** 6 Soll-Schritte == 6 überlebende Befunde.

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (23 vorherige Retros, 2026-07-12 ausgeführt):

- **9 bereits gate-pflichtige Slugs** (≥2 Vorkommen): `always-instruction-without-enforcement`, `ci-gate-maskiert-failure`, **`claim-before-cheapest-check`**, `handover-stale-vor-merge`, `lint-failure-no-local-gate`, **`planned-phase-no-issue`**, `platform-pinned-perma-dirty-loop`, **`scope-checkpoint-not-durably-recorded`**, `stale-local-clone-as-ground-truth`.
- **Diese Session reproduziert drei davon** (fett markiert oben) — Befund #2↔`scope-checkpoint-not-durably-recorded`, Befund #3↔`planned-phase-no-issue`, Befund #4↔`claim-before-cheapest-check`. Kein einziger neuer Fehlertyp, drei bestätigte Wiederholungen bereits eskalierter Muster.
- `handover-stale-vor-merge` wurde in dieser Session selbst als „6. Beleg" dokumentiert (PR #76, iil-voice-agent) — bereits vorher gate-pflichtig, hier nur zur Vollständigkeit im Frontmatter mitgeführt (kein neuer Fund dieses Retros, da bereits im PR-Text selbst korrekt attribuiert).
- `refuted_rate`-Trend (`retro_kpis.py`): 0,29 · 0,00 · 0,36 · 0,50 · 0,20 · 0,14 · 0,00 · 0,40 → **Band gesund** (weder 3× >0,8 noch <0,2). Diese Session: 4/10=0,40 — liegt konsistent im gesunden Band.
- **Score-Mittel je Dimension (n=23, historisch):** zielerreichung 3,87 · architektur_design 3,57 · code_konventionstreue 3,61 · **risiko_debt 2,70** (durchgängig schwächste Dimension) · prozess_effizienz 3,17 · entscheidungsqualitaet 3,39. Diese Session bestätigt das Muster (risiko_debt=2, niedrigster Einzelscore).

### 5b. Autonomie-Kalibrierung

- `over_ask`: **0** — kein Fall gefunden, in dem etwas nachweislich deterministisch/reversibles dem Menschen als „dein Zug" vorgelegt wurde, das autonom hätte laufen können.
- `over_act`: **0** — alle Gate-relevanten Aktionen (Budget-Seed, Secret-Kopien, Prod-Deploys, Merges) liefen erst nach expliziter, zunehmend präzisierter Freigabe; mehrere Classifier-Denials wurden korrekt als Anlass zur Nachfrage behandelt, nie umgangen. Ein Grenzfall (erneutes Ausführen des bereits vom User per `!` gestarteten, idempotenten Budget-Seed-Skripts zur Verifikation) wird als Restlücke in §8 geführt, nicht als klarer Verstoß gewertet.

## 6. Verankerung — kopierfertige Vorschläge (Mensch entscheidet)

**memory_candidates (repo-lokal, `iil-voice-agent`/`dev-hub` CC-Memory):**

```yaml
---
name: mail-search-issue-ignored-in-coordinating-pr
description: "Issue #82 (mail_search-Crash) mahnte Koordination mit dem Stufe-2-Bau an — PR #83 (dasselbe Modul) erwähnte es trotzdem nicht"
metadata:
  type: feedback
---
Vor jedem PR, der ein Modul ändert: gh issue list --search "in:body <modulname>" als
Pflicht-Schritt, bevor der "Bewusst ausgelassen"-Abschnitt geschrieben wird — eine bereits
offene, koordinierende Issue-Notiz zum selben Modul darf nicht unerwähnt bleiben.
Why: Session-Retro 2026-07-12 fand Issue #82 unverknüpft trotz eigener Koordinations-Bitte.
```

**adr_candidates:** keiner — alle Befunde sind Prozess-/Tracking-Lücken, keine Architektur-Entscheidung im Sinne der `adr-threshold`-Policy.

**Gate-Eskalations-Vorschlag (an `~/.claude/policies/` bzw. Hook-Ebene, NICHT session-lokal):**
Die drei bereits ≥2×-bestätigten Slugs (`claim-before-cheapest-check`, `planned-phase-no-issue`, `scope-checkpoint-not-durably-recorded`) haben in dieser Session ihre 3./4. Instanz erreicht (kumulativ über alle Retros). Der `retro_kpis.py`-Output sagt es selbst: "Als Gate (Hook/CI/Skill) verankern, nicht als N-tes Memo." Konkreter Vorschlag: ein PreToolUse-Hook, der bei `gh issue close`/`gh pr merge`-Kommentaren mit Formulierungen wie "sollte nachgezogen werden"/"Betreiber-Entscheidung" ohne begleitenden `gh issue create`-Aufruf im selben Turn warnt (Muster-Erkennung auf Prosa-Tracking-Versprechen).

## 7. Maßnahmen (Action-Board)

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Issue #82 (mail_search-Crash) einplanen | iil-voice-agent | https://github.com/iilgmbh/iil-voice-agent/issues/82 | 🟢 offen | Priorisieren oder bewusst zurückstellen (mit Begründung) |
| 2 | rsync→Deploy-Key für Staging nachziehen | dev-hub | file:///home/devuser/github/dev-hub/AGENT_HANDOVER.md | 🟢 offen | Eigenes Issue anlegen (fehlt noch) |
| 3 | Gate-Eskalation der 3 wiederkehrenden Slugs entscheiden | platform | file:///home/devuser/github/platform/docs/retros/session-retro-2026-07-12-dev-hub-3722b1.md#6-verankerung--kopierfertige-vorschläge-mensch-entscheidet | 🟢 offen | Hook/CI-Vorschlag §6 annehmen oder ablehnen |
| 4 | memory_candidate oben verankern oder verwerfen | iil-voice-agent | file:///home/devuser/github/platform/docs/retros/session-retro-2026-07-12-dev-hub-3722b1.md#6-verankerung--kopierfertige-vorschläge-mensch-entscheidet | 🟢 offen | Ja/Nein |

### 🔵 Ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | Issue in mcp-hub für den Budget-Seed-Präzedenzfall nachtragen | mcp-hub | file:///home/devuser/github/platform/docs/retros/session-retro-2026-07-12-dev-hub-3722b1.md#2-befund-tabelle (Befund #2) | 🔵 ready | Auf Zuruf |
| 6 | PR #128 CI-Root-Cause (stale iil-aifw) als Kommentar nachtragen | dev-hub | https://github.com/achimdehnert/dev-hub/pull/128 | 🔵 ready | Auf Zuruf |

## 8. Nicht verifiziert (Restlücken)

- Ob ein Pre-Merge-Check auf offene PRs (insb. #128) vor den 5 dev-hub-Merges dieser Session stattfand, ist aus den Artefakten nicht rekonstruierbar (kein Tool-Aufruf-Log einsehbar) — billigster Check wäre gewesen, aber jetzt nicht mehr nachholbar.
- Ob das erneute Ausführen des bereits vom User selbst per `!`-Befehl gestarteten Budget-Seed-Skripts (zur Verifikation) einen `over_act`-Grenzfall darstellt, bleibt hier bewusst als Restlücke geführt statt einseitig entschieden — Skript ist nachweislich idempotent, aber die Handlung selbst lief ohne erneute explizite Rückfrage.
- Delegations-Overhead (Hintergrund-Agenten meldeten "warte auf CI" statt Endergebnis) — als Hypothese geführt, kein harter Beleg aus verfügbaren Artefakten, ob das ineffizient oder korrekt getrennte Verantwortung war.
- Phase 6 (Extern-Handoff) wurde nicht ausgelöst — optional bei `deep`, hier nicht angefordert.
