---
retro_schema: 1
date: 2026-07-09
repo_scope: [frist-hub, platform]
session_id: 934b53
footprint: full
findings_total: 13
findings_survived: 10
refuted_rate: 0.077
phase3_refuted: 1
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [handover-stale-vor-merge, ci-gate-maskiert-failure, post-merge-ci-divergence-uncaught]
recurring_findings: [handover-stale-vor-merge, ci-gate-maskiert-failure, parallel-session-pr-collision]
over_ask: 0
over_act: 0
---

# Session-Retro · frist-hub · 2026-07-09 (PR #33: Szenario-Konsistenz + KONZ-frist-hub-003)

**Tier: full** — 1 Repo primär (frist-hub), 1 PR gemergt, aber mit echtem Prod-adjacent-Schritt
(SSH-Push nach kd.iil.pet, zweifach) + Git-Chirurgie auf einem geteilten Zweit-Repo (platform,
Hard-Reset). Trigger-Konflikt-Regel angewendet: alle drei Downscale-Bedingungen erfüllt
(User-Freigabe für den Hard-Reset per AskUserQuestion belegt; voll rollback-fähig, keine
DB-Migration; findings_total-Schätzung ≤10 vor Start) → `full` statt `deep`, nicht `lean`
(Auto-Eskalation "Prod-Schritt" verbietet lean kategorisch).

Pipeline: 1 Collector (haiku) → 3 Finder (sonnet, je Dimension) → 3 Skeptiker (sonnet, je
Dimension, unabhängiger Beleg-Zug). 7 Subagenten, 454k Tokens, 150 Tool-Calls, ~11,5 Min Laufzeit.

## 1. Executive Summary

- PR #33 (Szenario-Konsistenz Cockpit/Fristdetail + Cross-KD-Link + Eskalation-Anchor +
  KONZ-frist-hub-003) ist sauber gemerged, Fachlich korrekt umgesetzt und per Playwright
  verifiziert — das eigentliche Feature-Ziel wurde erreicht.
- **Main steht seit dem Merge mit rotem required Check `ci / gate`** (Post-Merge-Run divergiert
  vom PR-Zeit-Run: `Coverage Gate` + `Contract Tests` hingen 15 Min und wurden `cancelled`) —
  **unentdeckt/unadressiert bis zu diesem Retro**, Root Cause im verfügbaren Rohmaterial nicht
  ermittelbar (Logs bereits abgelaufen).
- Zwei bereits gate-pflichtige Wiederholungsmuster (`handover-stale-vor-merge` ×4→5,
  `ci-gate-maskiert-failure` ×2→3) traten erneut auf — beide waren schon vor dieser Session als
  strukturell bekannt, keiner der beiden Fixes ist verankert.
- Ein PR (#33) bündelte einen reinen UI-Fix mit einem eigenständigen T2-Architektur-Konzept unter
  einem `fix(...)`-Titel; das Konzept-Doc selbst hält fest, dass der Fix unabhängig mergefähig
  gewesen wäre — und es fehlt das sonst übliche `external_sparring_by`-Feld.
- Nebenbefund: paralleles Arbeiten in mehreren Worktrees führte zu einem echten Merge-Konflikt in
  `AGENT_HANDOVER.md`, der PR #32 (offen seit 2026-07-08) jetzt blockiert.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Scope-Bündelung: reiner UI-Fix + eigenständiges T2-Konzept (Cross-Repo-SSoT-Risiko) unter einem `fix(...)`-Titel gemergt; einzige Review ("getestet und akzeptiert") ohne inhaltliche Auseinandersetzung mit den Konzept-Tradeoffs | Prozesslücke/Kommunikation | mittel | SURVIVES | PR #33 Commits `b6f1fcf`+`d3f2395`; KONZ-003 Ledger A3 ("unabhängig mergefähig"); `gh pr view 33 --json reviews` | neu |
| 2 | `external_sparring_by`-Feld fehlt bei KONZ-frist-hub-003 (im Gegensatz zu KONZ-001/002 im selben Repo); zentraler Diabolus-Einwand D2 (Cross-Repo-SSoT-Divergenz) bleibt explizit "offen" markiert, kein Gate erzwingt das Feld | Konventionsverstoß/Prozesslücke | mittel | SURVIVES | KONZ-001/002 Frontmatter vs. KONZ-003 (Zeilen 1-24, Feld fehlt) | neu |
| 3 | Handoff-Banner-Gate prüft Handover-Rezenz nur, wenn `AGENT_HANDOVER.md` selbst im PR-Diff ist — bei reinen `docs/klickdummy*`/`docs/konzepte`-PRs läuft der Rezenz-Check komplett `skipped`; `AGENT_HANDOVER.md` blieb auf Iter. 23 (PR #31) stehen, PR #33/Iter. 24 fehlt dort weiterhin | Werkzeug (Gate-Design-Blindspot) | hoch | SURVIVES | `gh run view 29014280487 --json jobs`: Step "Rezenz prüfen" = `skipped`; `origin/main:AGENT_HANDOVER.md` ohne PR-#33-Erwähnung | **×5 (Memory `handover-stale-vor-merge`, bereits ×4 vor dieser Session)** |
| 4 | Keine dokumentierte Pre-Existing-Verifikation für den `ci / Integration Tests`-Failure bei PR #33 — im Gegensatz zum expliziten Vermerk bei PR #30 in `AGENT_HANDOVER.md` ("vor Merge gegen main-Baseline verifiziert"); die Prüfung fand in der Session zwar statt, wurde aber in keinem PR-Artefakt (Body/Commits/feedback-log) festgehalten | fehlende Validierung/Evidenzdisziplin | mittel | SURVIVES | `AGENT_HANDOVER.md:22-24` (PR-#30-Vermerk) vs. PR #33 Body/Commits/feedback-log ohne Äquivalent | neu |
| 5 | `ci / gate` maskiert strukturell Integration-Test-Failures (`continue-on-error: true` überschreibt `needs`-Result hart auf `success`) — bekannter Bug, Fix seit Tagen als Draft (`platform` PR #963) hängen geblieben, kein Owner treibt ihn in den Merge | Werkzeug + Prozesslücke (Governance) | kritisch | SURVIVES | `_ci-python.yml@b9d932f` Z. 313-317/586/592-599; Run `29014280600` Job `ci/gate`; `gh api .../pulls/963` (state=open, draft=true, verifiziert: PR ist noch offen im aktuellen `gh pr list`) | **×3 (Memory `ci-gate-maskiert-failure`, bereits ×2 vor dieser Session)** |
| 6 | Echte Rework-Schleife: PR #30 (Iter. 23) lieferte 3 Klickdummy-Inkonsistenzen aus (Szenario-Gating fehlte auf Cockpit/Fristdetail, Akte-DMS-Link war nur Info-Toast, Eskalation-Link ohne Anchor), die ausschließlich durch manuelles Nutzer-Klicken auf dem publizierten kd.iil.pet-Preview gefangen wurden — keine der 4 Klickdummy-Invarianten (I1-I4) deckt Cross-Screen-Verhaltenskonsistenz ab | fehlende Validierung | hoch | SURVIVES | `feedback-log.md` Iter.-24-Auslöser-Absatz; `Makefile` Z. 64-74 (`klickdummy-i1..i4`, kein Szenario-Konsistenz-Check) | neu |
| 7 | **Main steht seit dem PR-#33-Merge mit rotem required Check** — Post-Merge-Run auf identischem Commit (`4c9f7c5`) divergiert vom grünen PR-Zeit-Run: `Coverage Gate` + `Contract Tests` beide nach exakt 15 Min `cancelled` (11:32:20Z→11:47:22Z); kein Concurrency-Cancel durch neueren Push nachweisbar, Root Cause im verfügbaren Rohmaterial nicht ermittelbar (Job-Logs bereits abgelaufen); kein Re-Run, kein Fix-Commit bis Retro-Zeitpunkt | Werkzeug (CI-Infra-Flakiness) + fehlende Validierung (kein Post-Merge-Monitoring) | hoch | SURVIVES | Run `29015097161`; Gate-Log `Failed or cancelled jobs: ['coverage-report','test-contract']`; `gh api .../commits/4c9f7c5/check-runs` weiterhin rot zum Retro-Zeitpunkt | neu — **AKTIV, UNGELÖST** |
| 8 | Hard-Reset (`git reset --hard origin/main`) auf dem geteilten `platform`-Repo erfolgte nach expliziter User-Freigabe, aber ohne ein *persistiertes* Artefakt, das vor dem Reset die vollständige Inhaltsgleichheit aller 7 betroffenen Dateien belegt (nur 1 von 7 Dateien wurde im Chat gezeigt, plus Gits eigenes "bereits upstream"-Signal aus `rebase --skip`) — im Ergebnis ging inhaltlich nichts verloren (`967056d` war Subset von `9c945ce`/PR #1022), aber das war zum Reset-Zeitpunkt nicht vollständig dokumentiert | fehlende Validierung/verfrühte Festlegung | mittel | SURVIVES (Ergebnis unschädlich, Prozess unvollständig belegt) | Reflog `~/github/platform`; `.git/iil-guard-events.log`; `git diff 967056d 9c945ce --stat` (Superset bestätigt) | neu |
| 9 | Echter Merge-Konflikt in `AGENT_HANDOVER.md` blockiert PR #32 (offen seit 2026-07-08) — verursacht durch parallele Worktrees, die unabhängig denselben "Aktueller Stand"-Abschnitt überschreiben; kein Sync-Schritt hob PR #32 vor Weiterarbeiten auf den zwischenzeitlichen main-Stand | Prozesslücke/unklare Steuerung bei parallelen Sessions | mittel | SURVIVES | `gh pr view 32 --json mergeable` = `CONFLICTING` (nach PR-#33-Merge); `git merge-tree`-Konfliktblock in `AGENT_HANDOVER.md` | **×3 (Memory/Muster `parallel-session-pr-collision`, bereits ×2)** — **AKTIV, blockiert PR #32** |
| 10 | Lokales `frist-hub`-main nach Session nicht mit `origin/main` synchronisiert (1 Commit hinter, reines Fast-Forward-Delta, kein Risiko) | Prozesslücke (Routine-Sync) | niedrig | SURVIVES | `git rev-parse HEAD` (`67ba03c`) vs. `origin/main` (`4c9f7c5`) | neu |

**Nicht übernommen (REFUTED):** "PR #28 blieb bewusst als Draft" (ursprünglicher Präzedenzfall-Vergleich
für Befund 1 der Dimension Soll-Ist-Scope) — `gh pr view 28 --json isDraft` zeigt `draft: false`
über die gesamte Lebensdauer, gemergt 5 Min nach Erstellung trotz offenem Team-204-Feedback. Der
Vergleich war falsch herum: PR #28 zeigt dasselbe Muster wie PR #33, kein abweichender Präzedenzfall.

**Korrigierter Collector-Fehler (kein Befund):** Die ursprüngliche Rohfakten-Angabe "KD-Serve
akte-dms-Dateien liegen zeitlich nach dem Merge" war eine Zeitrichtungs-Verwechslung des Collectors
— die Mtimes (10:10–11:09Z) liegen alle vor dem Merge (11:30:54Z), konsistent mit dem normalen
Publish-vor-Merge-Workflow. Von zwei Findern unabhängig korrigiert, nicht in die Tabelle übernommen.

**Rechenweg 13 → 10 (Nachvollziehbarkeit des Deltas):** 13 Rohbefunde aus den 3 Dimensionen
(Soll-Ist-Scope 3, Entscheidungen-Fehler 5, Prozess-Kollaboration 5) minus 1 REFUTED = 12
Überlebende. Davon wurden 2 Paare als **dieselbe Tatsache, unabhängig von zwei Dimensionen
gefunden** zu je einer Tabellenzeile zusammengeführt (kein Doppel-Count, sondern Cross-Validation):
"main rot nach Merge" (Entscheidungen-Fehler #3 + Prozess-Kollaboration #3 → Zeile #7) und "lokales
main nicht synchronisiert" (Entscheidungen-Fehler #5 + Prozess-Kollaboration #5 → Zeile #10).
12 − 2 (gemergte Duplikate) = 10 distinkte Zeilen in §2.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Feature-Ziel (3 KD-Fixes) erreicht + verifiziert, aber Session endet mit rotem main und blockiertem PR #32 — signifikante offene Folgen |
| architektur_design | 4 | KONZ-003 solide, evidenzbasiert, richtig als T2 eingestuft; einziger Mangel: fehlendes `external_sparring_by` (#2) |
| code_konventionstreue | 4 | Klickdummy-Fix reuste bestehende Muster (sc-hybrid-plus/sc-c-only aus Iter. 22) korrekt; I4-Verstöße vor Merge selbst gefangen+gefixt |
| risiko_debt | 2 | Main aktuell rot (#7), PR #32 blockiert (#9), bekannter Gate-Masking-Bug 3. Vorkommen ohne Fix-Merge (#5) — spürbarer, teils neuer Risiko-Zuwachs |
| prozess_effizienz | 3 | Rework nötig (PR #30 → PR #33 Nachbesserung, #6), Rebase-Dance auf platform, aber am Ende sauber gelandet |
| entscheidungsqualitaet | 3 | Gute Einzelentscheidungen (Freigabe vor Hard-Reset, SSH-Verifikation vor Publish-Behauptung), aber Lücke bei Post-Merge-Monitoring (#7) und Pre-Existing-Dokumentation (#4) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| PR #33 bündelte UI-Fix + T2-Konzept unter einem Titel; einzige Review war oberflächlich (#1) | Konzept-Docs mit Cross-Repo-SSoT-Risiko (Auto-Eskalations-Trigger) als eigenen PR führen, damit ein Reviewer explizit die Architektur-Tradeoffs freigibt, nicht nur den KD-Klick nachvollzieht | #1 |
| KONZ-003 ohne `external_sparring_by`, kein Gate erzwingt es (#2) | `/konzept`-Skill-Selbstcheck (Step 5) um eine explizite Ja/Nein-Frage "braucht dieses Konzept `external_sparring_by`?" ergänzen, wenn Vorgänger-Konzepte im selben Repo das Feld führen | #2 |
| Handoff-Banner-Gate lief `skipped`, weil `AGENT_HANDOVER.md` nicht im Diff war (#3) | `paths:`-Filter des Gates um eine "und trotzdem prüfen, ob AGENT_HANDOVER.md seit dem letzten Merge aktualisiert wurde"-Bedingung erweitern — Rezenz unabhängig vom eigenen Diff prüfen, nicht nur bei Selbstbetroffenheit | #3 |
| PR #33 ohne dokumentierte Pre-Existing-Verifikation für den bekannten CI-Failure (#4) | Vor jedem Merge mit rotem Non-Required-Check einen Einzeiler im PR-Body/Commit ergänzen ("main-Baseline verifiziert: Run <ID>"), analog zum PR-#30-Vorbild — macht die Prüfung selbst artefaktfähig statt nur im Chat zu passieren | #4 |
| `continue-on-error` maskiert Integration-Test-Failures strukturell, Fix seit Tagen im Draft (#5) | `platform` PR #963 aktiv priorisieren (Review anfordern oder selbst finalisieren) statt als Dauer-Draft laufen zu lassen — das 3. Vorkommen ist der Beleg, dass "später" nicht funktioniert | #5 |
| 3 Klickdummy-Inkonsistenzen aus PR #30 nur durch manuelles Klicken gefangen (#6) | `klickdummy-i1..i4` um eine 5. (opt-in) Prüfung ergänzen, die pro Szenario-/Persona-Kombination die Sichtbarkeits-Konsistenz zwischen den in `personas.sieht` gelisteten Screens prüft — KONZ-frist-hub-003 (bereits erstellt) liefert den Ansatz dafür | #6 |
| Main seit Merge rot, keiner hat es bemerkt (#7) | Nach jedem Merge auf ein Repo mit bekanntermaßen instabilem `Integration Tests`-Job einen zweiten Check nach ~15-20 Min ansetzen (`gh run list --branch main`), bevor die Session als abgeschlossen gilt | #7 |
| Hard-Reset auf `platform` ohne persistiertes Vollständigkeits-Artefakt (#8) | Vor einem Hard-Reset auf einem geteilten Repo ALLE betroffenen Dateien (nicht nur eine Stichprobe) per `git diff --stat`+Volltext gegen die Zielreferenz zeigen, bevor gefragt wird — die Freigabe-Frage selbst braucht den vollständigen Beleg als Anhang | #8 |
| Paralleler Worktree-Konflikt in `AGENT_HANDOVER.md` blockiert PR #32 (#9) | Vor dem Öffnen eines neuen Session-Worktrees prüfen, ob andere offene Worktrees denselben "Aktueller Stand"-Abschnitt planen zu ändern (`git worktree list` + Diff-Vorschau); wenn ja, den älteren PR zuerst rebasen oder den neuen Abschnitt als Anhang statt Ersetzung schreiben | #9 |
| Lokales `frist-hub` nach Merge nicht gepullt (#10) | Nach jedem PR-Merge, den man selbst durchgeführt hat, den lokalen Checkout (falls einer offen ist) direkt mitziehen (`git pull --ff-only`) als letzten Schritt der Merge-Routine | #10 |

## 5. Längsschnitt

`tools/retro_kpis.py` über 20 Reports (`platform/docs/retros/` + `~/shared`, Stand dieser Session):

- **10 Slugs bereits ≥2 ⇒ gate-pflichtig** (unverändert von vor dieser Session, keine neuen
  Fleet-weiten Slugs durch diesen Retro hinzugekommen — aber 2 bestehende Slugs erneut bestätigt):
  `ci-gate-maskiert-failure` (jetzt ×3), `claim-before-cheapest-check` (×16), `critical-alert-no-ticket`
  (×2), `handover-stale-vor-merge` (jetzt ×5), `lint-failure-no-local-gate` (×3),
  `parallel-session-pr-collision` (jetzt ×3), `planned-phase-no-issue` (×3),
  `scope-checkpoint-not-durably-recorded` (×3), `stale-local-clone-as-ground-truth` (×3),
  `worktree-midsession-accumulation` (×2).
- `refuted_rate`-Band über die letzten 8 vergleichbaren Reports: 0.00–0.50, gesund (weder
  durchgängig >0.8 noch <0.2). Dieser Report: 0.077 (1/13) — am unteren Ende, konsistent mit
  disziplinierten Findern (wenig Stroh), nicht mit lascher Falsifikation (die Skeptiker haben den
  einen REFUTED-Fall aktiv per GitHub-API widerlegt, nicht nur durchgewinkt).
- Score-Mittel über 20 Reports zum Vergleich: `risiko_debt` 2.80 (dieser Report: 2, unter Schnitt —
  main ist aktuell rot, das zieht runter), `zielerreichung` 3.95 (dieser Report: 3, unter Schnitt).

**Handover-stale-vor-merge und ci-gate-maskiert-failure sind jetzt beide beim 3.-5. Vorkommen ohne
verankerten Fix — das ist der eigentliche Hebel dieses Retros, nicht die Einzel-Befunde.**

## 5b. Autonomie-Kalibrierung

- `over_ask`: 0 — kein Fall in dieser Session, in dem etwas Deterministisches/Reversibles unnötig
  dem User vorgelegt wurde (der Hard-Reset-Freigabe-Fall war wegen unvollständiger Vorab-Prüfung
  (#8) korrekt eine Frage wert, nicht over_ask).
- `over_act`: 0 — die zwei Kandidaten (kd.iil.pet-Republish ohne erneute Rückfrage, PR-Merge nach
  Nutzer-Freigabe "1") liefen beide innerhalb bereits erteilter, expliziter Autorisierung
  (Standing-Preference "immer kd.iil.pet"; Nutzer-Auswahl "warte auf CI, dann mergen").

## 6. Verankerung (Vorschläge — Mensch entscheidet)

**memory_candidate 1** (Update, nicht neu — bestehende Memory `ci-gate-maskiert-failure.md` bereits
vorhanden, dieser Fund bestätigt sie ×3):
```yaml
---
name: ci-gate-maskiert-failure
description: ci/gate maskiert continue-on-error-Failures via needs-Result-Override — 3. Vorkommen, Fix (platform PR #963) seit Tagen Draft
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-09-frist-hub-pr33-gate-mask-3rd
---
3. bestätigtes Vorkommen (nach a50bc6, 7f7fbd) — frist-hub PR #33 mergte mit rotem
`ci / Integration Tests`, weil `ci / gate` den Job-Status via `continue-on-error: true` hart
auf "success" liest. Fix existiert (platform PR #963), ist aber seit Tagen im Draft-Status
liegen geblieben. **Neu diesmal:** kein Owner-Mechanismus treibt bekannte Fleet-Fixes aus dem
Draft — das ist jetzt der eigentliche Hebel, nicht ein 4. Memo über dasselbe Symptom.
```

**memory_candidate 2** (neu):
```yaml
---
name: post-merge-ci-divergence-uncaught
description: PR-Zeit-CI grün, Post-Merge-Run auf identischem Commit rot (gecancelte Jobs) — kein Monitoring-Schritt fängt das
metadata:
  type: feedback
---
frist-hub PR #33: Required Check "ci / gate" war beim Merge grün (Run A), der automatische
Push-Run auf demselben Merge-Commit (Run B, ~1 Sek später getriggert) zeigte "gate" rot, weil
Coverage-Gate + Contract-Tests nach 15 Min hingen und gecancelt wurden. Root Cause nicht
ermittelbar (Logs verfallen). Bis zu diesem Retro (21 Min später) hat niemand nachgeschaut.
Why: PR-Zeit-Grün gilt als hinreichend: Post-Merge-Run wird nicht routinemäßig noch einmal
geprüft. How to apply: nach jedem eigenen Merge ~15-20 Min später `gh run list --branch main`
prüfen, bevor die Session/Aufgabe als abgeschlossen gilt.
```

**adr_candidate:** keiner — nichts in dieser Session berührt einen der `adr-threshold.md`-Trigger
(kein neuer Dependency/Service, keine Cross-Repo-Architektur-Umkehr; KONZ-frist-hub-003 selbst
adressiert das bereits richtig als Konzept-Vorstufe, nicht als ADR).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Main auf frist-hub ist seit PR #33-Merge rot (`ci / gate` failure, Run [29015097161](https://github.com/meiki-lra/frist-hub/actions/runs/29015097161)) | frist-hub | — | 🟢 offen | du: entscheiden ob Re-Run angestoßen werden soll (ich kann das sofort ausführen) |
| 2 | PR #32 (DAP-Austauschschicht) ist durch Merge-Konflikt in `AGENT_HANDOVER.md` blockiert | frist-hub | [#32](https://github.com/meiki-lra/frist-hub/pull/32) | 🟢 offen | du: Konflikt lösen (Rebase) oder mir die Freigabe dafür geben |
| 3 | `platform` PR #963 (Coverage-Gate-Fix, behebt `ci-gate-maskiert-failure` strukturell) seit Tagen Draft, jetzt 3. bestätigtes Symptom-Vorkommen | platform | [#963](https://github.com/achimdehnert/platform/pull/963) | 🟢 offen | du: priorisieren (Review/Merge) oder Owner benennen |
| 4 | Handoff-Banner-Gate-Blindspot (prüft Rezenz nur bei Selbstbetroffenheit) — 5. Vorkommen | platform | — | 🔵 ich kann | ich: Fix-Vorschlag für `.github/workflows/handoff-banner-gate.yml`-Trigger-Logik ausarbeiten, wenn gewünscht |
| 5 | `external_sparring_by` bei KONZ-frist-hub-003 nachtragen (2 Reviewer, analog KONZ-001/002) oder bewusst als "T2, kein externes Sparring nötig" begründen | frist-hub | [KONZ-frist-hub-003](https://github.com/meiki-lra/frist-hub/blob/main/docs/konzepte/KONZ-frist-hub-003-customer-journey-spec-first-klickdummy.md) | 🟢 offen | du: entscheiden ob externes Sparring nachgeholt wird |
| 6 | Lokales `frist-hub`-Checkout auf `origin/main` vorspulen | frist-hub | — | 🔵 ich kann | ich: `git pull --ff-only`, trivial |

## 8. Nicht verifiziert (Restlücken)

- **Root Cause der 15-Min-Hänger bei Coverage Gate/Contract Tests (Befund #7):** Job-Logs waren zum
  Prüfzeitpunkt bereits nicht mehr abrufbar (`gh api .../logs` → 404 BlobNotFound). Billigster
  nächster Check: einen manuellen Re-Run auf demselben Commit anstoßen und live beobachten, ob der
  Hänger reproduzierbar ist (transientes Infra-Flake vs. deterministischer Fehler).
- **Ob `parallel-session-pr-collision` (Befund #9) inhaltlich zum selben Muster gehört wie die 2
  Vorkommen in `17c08c`/`44240f`:** nur der Slug-Name wurde abgeglichen (per `retro_kpis.py`), nicht
  der volle Text jener beiden Reports gelesen. Billigster Check: `platform/docs/retros/session-retro-*17c08c*.md`
  und `*44240f*.md` öffnen und den exakten Mechanismus vergleichen.
- **Ob die externe Zweitmeinung (Phase 6) für diesen Report nötig ist:** nicht ausgeführt (nur bei
  `deep`, dieser Report ist `full`) — falls gewünscht, wäre `session-retro-extern-2026-07-09-frist-hub-934b53.md`
  der nächste Schritt.
