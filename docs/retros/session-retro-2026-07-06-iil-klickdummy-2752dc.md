---
retro_schema: 1
date: 2026-07-06
repo_scope: [iil-klickdummy, platform]
session_id: 2752dc
footprint: full
findings_total: 16
findings_survived: 14
refuted_rate: 0.125
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [main-tree-guard-recurring-incident, pythonpath-worktree-mismatch-cross-repo-known, pr-collision-check-bypassed-by-direct-branch, genesor-validation-fix-incomplete-propagation]
recurring_findings: [main-tree-guard-recurring-incident, pythonpath-worktree-mismatch-cross-repo-known, pr-collision-check-bypassed-by-direct-branch, genesor-validation-fix-incomplete-propagation, changelog-frozen-section-retroactive-edit]
---

# Session-Retro — iil-klickdummy (+ platform) · 2026-07-05/06

_Full-Footprint (2 Repos, 3 gemergte PRs + 1 offener PR, keine Prod-Migration, kein ADR). 1 Collector
(haiku) + 3 Finder + 4 Skeptiker (sonnet, davon 1 dedizierter Konflikt-Skeptiker), Richter≠Angeklagter.
16 Befunde, 14 SURVIVES, 2 REFUTED._

## 1. Executive Summary

- **Alle drei iil-klickdummy-PRs (#129 Dependabot, #135 EF-5/EF-7, #136 AD-6/#103) lieferten ihr
  genanntes Ziel nachweisbar** — Escape-Fix, Code-Verschiebung, weiche Schema-Validierung wurden
  unabhängig gegen den echten Diff verifiziert (SURVIVES). CI durchgehend grün, Issue #103 korrekt
  automatisch geschlossen. Der platform-PR #965 (KD-Referenz-Schema) ist ebenfalls sauber (rein
  additiv, Drift-Score 0, Dogfood-Beleg gegen echte risk-hub-Daten gegenverifiziert) — blieb aber ohne
  dokumentierten Grund offen statt automatisiert gemergt zu werden.
- **Ein echter Finder-Widerspruch wurde aufgelöst:** verwaiste Remote-Branches nach `--delete-branch`
  liegen NICHT am Repo-Setting `delete_branch_on_merge=false` (das betrifft nur automatische Löschungen
  ohne expliziten Flag) — der reale Grund ist, dass der Merge-Befehl aus dem Worktree heraus lief, in
  dem der Branch selbst noch ausgecheckt war, wodurch `gh`s lokaler Cleanup-Pfad in einem
  Partial-Failure-Zustand abbrach (per unabhängig gefundenem `cli/cli`-Issue-Muster erhärtet).
- **AD-6/#103 (PR #136) ist wieder nur teilweise gefixt — dasselbe Muster wie beim ursprünglichen
  Fund selbst.** Der Fix deckt `genesor/scan.py`, aber zwei weitere reale Konsumenten desselben
  Spec-Formats (`klickdummy_sync.py`, `registry.py._load_spec`) bleiben unvalidiert — exakt die
  Lücke, die die bestehende Drift-Memory `genesor-security-unvalidated-path` schon einmal benannt
  hatte. Zusätzlich führt die Code-Verschiebung einen vorher nicht existenten, ungeschützten
  `jsonschema`-Import in einen Pfad ein, der laut Memory `genesor-deploy-simple` real ohne
  pip-Install direkt aus dem Source-Checkout aufgerufen wird.
- **Prozess-Reibung wiederholt sich, aber verringert sich innerhalb der Session:** ein
  main-tree-guard-Vorfall (direkter `git checkout -b` im Haupt-Checkout, von ADR-233 geblockt) plus
  eine PYTHONPATH-Verwechslung (Test lief gegen falschen Worktree-Code) — beide Muster sind in einem
  SCHWESTER-Repo (`iil-adrfw`) bereits dokumentiert, aber nie repo-übergreifend gezogen worden. Der
  direkte Vergleich "Worktree-Zeitstempel #135/#136 vs. #965" scheiterte an fehlenden Artefakten
  (Worktrees bereits entfernt) — aber der spätere platform-PR #965 lief nachweislich sauber über
  `repo-session.sh start` inkl. PR-Kollisionscheck.
- **Testabdeckung bei beiden Sicherheits-PRs bleibt unter dem Umfang des Fixes:** #136 testet nur 1
  von 3 Aufrufstellen end-to-end, #135 nur 1 von 2 gehärteten Funktionen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | PR #136 bündelt Code-Motion (`validate_spec`/`_load_schema` gen_e2e.py→read_model.py) mit dem AD-6-Security-Fix in einem PR, obwohl der minimale Fix ohne Verschiebung ausgekommen wäre | verfrühte Festlegung | mittel | SURVIVES | `gh pr diff 136`: `gen_e2e.py` −38/+3, `read_model.py` +48; PR-Body begründet die Verschiebung als Design-Entscheidung, nicht als Fix-Notwendigkeit | — |
| 2 | Verwaiste Remote-Branches (#135/#136) nach `gh pr merge --delete-branch` — echter Root Cause: Merge-Befehl lief aus dem Feature-Worktree heraus, in dem der Branch ausgecheckt war → `gh`s lokaler Cleanup brach vor dem Remote-Delete ab (nicht das Repo-Setting `delete_branch_on_merge=false`, das nur automatische Löschungen ohne Flag betrifft) | Werkzeug | mittel | SURVIVES | Lease-Close-Timestamps `04:45:18Z` (13s/10s NACH den Merges `04:45:05Z`/`04:45:08Z`) beweisen aktive Worktree-Auschecks zum Merge-Zeitpunkt; `git ls-remote` bestätigt beide Branches noch live; passendes `cli/cli`-Issue-Muster unabhängig gefunden | pr-collision-check-bypassed-by-direct-branch (verwandt) |
| 3 | platform-PR #965 blieb offen (nicht automatisiert gemergt) ohne dokumentierten Grund — kein Label/Review-Kommentar/CI-Gate-Name erklärt die Freigabe-Schwelle ggü. #135/#136 | Wissenslücke | niedrig | SURVIVES | `gh pr view 965`: state OPEN, 11/11 Checks grün, `labels: []`, `reviews: []`; nur automatisierte Bot-Kommentare | — |
| 4 | PR-#965-Herkunftsbehauptung ("entstanden aus einer iil-klickdummy-Session") ist nur im Fließtext dokumentiert, kein verlinktes Issue/Trailer/Session-ID macht sie cross-repo nachprüfbar | Kommunikation | niedrig | SURVIVES | `gh pr view 965 --json closingIssuesReferences` → `[]`; kein Trailer in Commit-Message | — |
| 5 | Kein Scope-Checkpoint-Artefakt für den Repo-Übergang iil-klickdummy→platform (schwache Form — 2 Repos, unter der 3-Repo-Schwelle der Hausregel) | Prozesslücke (Grenzfall) | niedrig | SURVIVES (schwach) | Volltextsuche PR-Body/Kommentare auf Scope-Vokabular → 0 Treffer | scope-checkpoint-not-durably-recorded (bestehender Gate-Slug, ×3 vor dieser Session) |
| 6 | `read_model.py` importiert `jsonschema` jetzt UNGESCHÜTZT (kein try/except mit Setup-Meldung, wie vorher in `gen_e2e.py`); `genesor/scan.py` hat dadurch über `lineage.py` einen NEUEN harten jsonschema-Pfad, wo vorher keiner existierte — riskant für den dokumentierten Direkt-Source-Checkout-Aufruf (`iil-pet-portal/scripts/regen-genesor-main.sh` → `python -m iil_klickdummy.lineage` ohne pip-Install) | fehlende Validierung | mittel | SURVIVES | `read_model.py:22` kein try/except; `check_i1.py`/`check_stories.py` guarden denselben Import weiterhin; `git show <vor-#136>:genesor/scan.py` hatte gar keinen jsonschema-Import | — |
| 7 | `gen_e2e.py` importiert `_load_schema` ungenutzt, nur per `# noqa: E402,F401` unterdrückt statt weggelassen | Werkzeug | niedrig | SURVIVES | `grep -c "_load_schema" gen_e2e.py` → nur Import+Kommentar, keine Nutzung | — |
| 8 | AD-6-Fix (PR #136) unvollständig propagiert: `klickdummy_sync.py` (eigenes `find_specs()`+`yaml.safe_load`) und `registry.py._load_spec` (genutzt von `discover_klickdummies`) bleiben unvalidiert — derselbe Fehlerklassen-Fund, den Drift-Memory `genesor-security-unvalidated-path` bereits einmal benannt hatte | fehlende Validierung | mittel | SURVIVES | `grep -rn "validate_spec\|_warn_schema" klickdummy_sync.py registry.py` → 0 Treffer; PR-#136-Scope (`git show 4268935 --stat`) umfasst nur `genesor/scan.py` | genesor-validation-fix-incomplete-propagation (2. Vorkommen dieser Fehlerklasse in diesem Repo) |
| 9 | Testabdeckung PR #136: nur 1 von 3 `_warn_schema_violations`-Aufrufstellen (`find_all_repos_specs` Standard-Konvention) ist end-to-end getestet; `find_specs()` und die meiki-Konvention-Branch nur indirekt über den Helper-Unit-Test | fehlende Validierung | niedrig-mittel | SURVIVES | `test_should_include_non_conforming_spec_in_fleet_scan_but_warn` nutzt nur `klickdummy/*/screens-spec.yaml`-Pfad | — |
| 10 | Testabdeckung PR #135: nur 1 von 2 gehärteten Funktionen (`render_browser_html`) hat Regressionstest; `render_cross_repo_browser_html` (ebenfalls gepatcht) hat keinen bösartigen `base_label`-Test | fehlende Validierung | niedrig-mittel | SURVIVES | `git show 02b4a70 -- tests/test_smoke.py`: 1 neuer Test; `test_v13_cross_repo_render` nutzt `base_label="test"` (harmlos) | — |
| 11 | PR #135 editiert `CHANGELOG.md` rückwirkend in den bereits released `[1.30.0]`-Abschnitt statt unter `[Unreleased]`, obwohl `v1.31.0`/`v1.31.1` seither getaggt sind | Prozesskonvention | niedrig | SURVIVES (schwach — Repo hat Präzedenz für transparente rückwirkende Notizen in Altsektionen) | `git show 02b4a70 -- CHANGELOG.md`: Diff-Hunk unter `## [1.30.0]`; `git tag` bestätigt v1.30.0/v1.31.0/v1.31.1 existieren | changelog-frozen-section-retroactive-edit |
| 12 | main-tree-guard-Vorfall (direkter `git checkout -b` im Haupt-Checkout von iil-klickdummy, per ADR-233-Hook geblockt, HEAD zurückgesetzt) trat in dieser Session real auf — Teil eines wiederkehrenden, aber bisher nur in einem SCHWESTER-Repo (`iil-adrfw`) als Memory dokumentierten Musters. **Präzisierung:** `.git/iil-guard-events.log` enthält 3 Einträge insgesamt über mehrere Sessions (2026-06-24, 2026-07-02, 2026-07-05) — nur der letzte gehört zu dieser Session; "4. Vorfall in dieser Session" (Erst-Formulierung eines Finders) wäre eine Überziehung der Evidenz | Prozesslücke / Wissenslücke | mittel-hoch | SURVIVES (mit Korrektur) | `.git/iil-guard-events.log` (3 Zeilen, Zeitstempel wie oben); Reflog bestätigt Checkout im Haupt-Tree 2 Min vor Lease-Erstellung | main-tree-guard-recurring-incident (3× repo-lokal über Zeit, 0× bisher als Retro-Slug erfasst) |
| 13 | PYTHONPATH-Verwechslung (erster Testlauf im neuen Worktree griff auf den Haupt-Checkout-Code statt Worktree-Code zu) — derselbe Pitfall ist in `iil-adrfw`s Memory `adr233-main-tree-guard-workflow.md` bereits seit 2026-07-02 dokumentiert, aber nie repo-übergreifend auf iil-klickdummy angewendet worden | Wissenslücke (Cross-Repo-Transfer) | mittel | SURVIVES (mit Scope-Einschränkung — Dokumentation existiert in anderem Repo, nicht demselben) | `~/.claude/projects/-home-devuser-github-iil-adrfw/memory/adr233-main-tree-guard-workflow.md`: identischer Pitfall-Text, Datum 2026-07-02 | pythonpath-worktree-mismatch-cross-repo-known |
| 14 | `repo-session.sh start`s PR-Kollisions-Check existiert unbedingt im Code, lief aber nachweislich NICHT vor dem ersten (dann geblockten) Direktversuch bei PR #135 — der fehlerhafte Erstversuch umging damit auch den eingebauten Sicherheitsschritt, nicht nur Zeit | Prozesslücke | niedrig-mittel | SURVIVES (Code-Fakt git-verifiziert; Nichtausführung für #135 verifiziert über das Tool-Aufruf-Protokoll dieser Session, nicht über ein Repo-Artefakt) | `check_pr_collision()` in `repo-session.sh` als fester `cmd_start()`-Bestandteil; kein Log-Artefakt für Nicht-Ausführung, nur Session-Transkript | — |

**REFUTED (nicht in der Tabelle, nur gezählt):** (a) "Root Cause der verwaisten Branches = `delete_branch_on_merge=false`" — widerlegt durch Konflikt-Skeptiker (s. Befund 2). (b) "Worktree-Pfad-Zeitstempel-Vergleich zeigt In-Session-Lerneffekt #135/#136→#965" — die geforderte Vergleichsmethode scheiterte, weil die iil-klickdummy-Worktrees bereits entfernt waren (nur Lease-Dateien übrig); die schwächere Ersatzevidenz (Lease-Timestamps) ist bereits in Befund 2 verwertet.

## 3. Scorecard (1–5, an Befunden verankert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Alle 3 iil-klickdummy-PR-Ziele nachweisbar erreicht (Befunde SURVIVES ohne Diskrepanz), Issue #103 korrekt geschlossen, CI durchgehend grün; Abzug: unvollständige Test-Abdeckung (#9/#10) |
| architektur_design | **3** | Soft-Validierungs-Design in `scan.py` durchdacht (vermeidet bewusst M28-2-Regressionsklasse); aber unvollständige Fix-Propagation (#8) wiederholt eine bereits bekannte Fehlerklasse, plus neuer ungeschützter jsonschema-Pfad (#6) |
| code_konventionstreue | **4** | `ruff check` clean, 205 Tests grün; Abzug: unbenutzter Import mit `noqa` (#7), rückwirkender Changelog-Edit in Altsektion (#11) |
| risiko_debt | **3** | Neue Fragilität im Direkt-Source-Checkout-Pfad (#6) + wiederholte unvollständige Validierungsabdeckung (#8) + zwei Testlücken (#9/#10) — reale, aber nicht akut brennende neue Schuld |
| prozess_effizienz | **3** | Zwei separate Reibungspunkte im selben PR-Paar (#12 main-tree-guard, #13 PYTHONPATH) plus verwaiste Branches (#2) — aber sichtbar sauberer Ablauf beim nachfolgenden platform-PR #965 (Dry-Run vor Push, PR-Kollisionscheck lief) |
| entscheidungsqualitaet | **4** | KD-Referenz-Design ging über 2 `AskUserQuestion`-Runden mit dem Nutzer, Dogfood-Beleg gegen echte Daten unabhängig doppelt gegenverifiziert (SURVIVES); Abzug: Bündelung Refactor+Security-Fix (#1) ohne Split-Erwägung |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| PR #136 bündelt Code-Motion (`gen_e2e.py`→`read_model.py`) mit dem AD-6-Fix in einem PR | Bei einem Security-/Bugfix, der eine Code-Verschiebung "ermöglicht" statt "erzwingt": Refactor und Fix in **getrennte PRs** (Refactor zuerst, isoliert reviewbar/zurückrollbar; Fix danach, minimal) | #1 |
| Merge-Befehl (`gh pr merge --delete-branch`) lief aus dem Feature-Worktree heraus, in dem der Branch ausgecheckt war → lokaler Cleanup brach ab, Remote-Branch blieb verwaist | Merge-Schritt in der Session-Routine **immer aus dem Haupt-Checkout** absetzen (nach `git fetch`), nie aus dem Feature-Worktree selbst — oder Worktree per `repo-session.sh end` schließen, BEVOR gemergt wird | #2 |
| platform-PR #965 blieb offen ohne dokumentierten Freigabe-Grund | Bei bewusst zurückgehaltenen PRs (Skill-/Prozessänderungen) einen kurzen PR-Kommentar/Label hinterlassen, der die Freigabe-Schwelle benennt ("wartet auf menschliche Sichtung, weil X") | #3 |
| PR-#965-Herkunft nur im Fließtext, keine verlinkte Quelle | Cross-Repo-Herkunftsbehauptungen als strukturierten Trailer (`Source-Session:`/`Refs:`) statt nur Prosa führen | #4 |
| Kein Scope-Checkpoint-Artefakt beim Übergang iil-klickdummy→platform | Bei jedem Repo-Wechsel (auch unter der 3-Repo-Schwelle) einen 1-Satz-Spiegel im ersten PR-Body des neuen Repos ("Fortsetzung aus Repo X, Grund Y") | #5 |
| `read_model.py` importiert `jsonschema` ungeschützt, neuer harter Pfad über `scan.py`/`lineage.py` in einen Direkt-Source-Checkout-Aufruf | Bei Code-Motion einer Funktion mit externer Dependency in ein neues Modul: den bestehenden Guard (`try/except ImportError` + freundliche FAIL-Meldung) mitverschieben, nicht stillschweigend fallen lassen | #6 |
| `gen_e2e.py` importiert `_load_schema` ungenutzt, per `noqa` unterdrückt | Nach einer Re-Export-Verschiebung: `ruff check --select F401` gezielt lesen statt die Warnung pauschal zu unterdrücken — ungenutzte Importe weglassen | #7 |
| AD-6-Fix deckt nur `genesor/scan.py`, nicht `klickdummy_sync.py`/`registry.py._load_spec` | Vor "Issue X gefixt" eine **sink-/consumer-Inventur** (`grep -rn "yaml.safe_load"` über den ganzen Consumer-Kreis) fahren, wie es die bestehende Memory `genesor-security-unvalidated-path` bereits vorschreibt — und diese Memory in der PR-Beschreibung explizit gegenlesen | #8 |
| Test deckt nur 1 von 3 `_warn_schema_violations`-Aufrufstellen end-to-end ab | Bei einer Funktion mit N Aufrufstellen: mindestens 1 End-to-End-Test **pro Aufrufstelle**, nicht nur 1 E2E-Test + Helper-Unit-Tests für den Rest | #9 |
| Test deckt nur 1 von 2 gehärteten Funktionen (`render_browser_html`/`render_cross_repo_browser_html`) ab | Wenn ein Fix 2 Funktionen mit identischem Muster patcht: **2 Regressionstests**, nicht 1 (auch wenn die zweite Stelle "offensichtlich analog" wirkt) | #10 |
| CHANGELOG-Ergänzung landet rückwirkend in einer bereits released Sektion | Ergänzende Migrationshinweise zu bereits released Versionen als eigene, klar markierte Nachtrags-Zeile ("Nachtrag YYYY-MM-DD") statt unmarkiert in den historischen Abschnitt einzufügen | #11 |
| main-tree-guard blockte einen direkten `git checkout -b` im Haupt-Checkout — Wissen dazu liegt nur in `iil-adrfw`s Memory | Vor JEDER editierenden Session in JEDEM Repo mit main-tree-guard-Hook (`.git/hooks/post-checkout` prüfen) **zuerst** `repo-session.sh start` — als globale Regel/Reminder, nicht als repo-lokale Einzel-Memory | #12 |
| PYTHONPATH zeigte nach Worktree-Wechsel auf den falschen (Haupt-Checkout-)Code | Vor dem ersten Testlauf in einem neuen Worktree: 1 Zeile `python3 -c "import <pkg>; print(<pkg>.__file__)"` als Billigst-Check, ODER den bekannten Fix (`PYTHONPATH=$WT/src`) direkt in die `repo-session.sh`-Ausgabe/den Onboarding-Hinweis aufnehmen | #13 |
| Der PR-Kollisions-Check aus `repo-session.sh start` lief nicht vor dem ersten (fehlgeschlagenen) Direktversuch bei PR #135 | Direkter `git checkout -b`/`git commit` im Haupt-Tree sollte gar nicht erst versucht werden — s. Soll-Schritt #12; sobald der Einstieg über `repo-session.sh start` läuft, ist der Kollisionscheck automatisch mit dabei | #14 |

## 5. Längsschnitt (`tools/retro_kpis.py`, 14 Reports)

- **8 bestehende Slugs bereits ≥2 → Gate-Pflicht** (unverändert durch diese Session):
  `claim-before-cheapest-check` ×14, `scope-checkpoint-not-durably-recorded` ×3, `planned-phase-no-issue` ×3,
  `handover-stale-vor-merge` ×3, `lint-failure-no-local-gate` ×2, `parallel-session-pr-collision` ×2,
  `critical-alert-no-ticket` ×2, `worktree-midsession-accumulation` ×2.
- Diese Session trägt zu `scope-checkpoint-not-durably-recorded` **ein weiteres (schwaches) Vorkommen** bei
  (Befund 5) — bleibt unter der harten Form (nur 2, nicht 3 Repos), aber Muster wiederholt sich erneut.
- **5 NEUE Slugs** aus dieser Session (0× vorher als Retro-Slug erfasst, aber teils bereits real
  wiederkehrend am Repo selbst — s. unten): `main-tree-guard-recurring-incident`,
  `pythonpath-worktree-mismatch-cross-repo-known`, `pr-collision-check-bypassed-by-direct-branch`,
  `genesor-validation-fix-incomplete-propagation`, `changelog-frozen-section-retroactive-edit`.
- ⚠ **Vorgriff auf Gate-Pflicht bei `main-tree-guard-recurring-incident`:** obwohl dies der 1. Retro-
  Auftritt dieses Slugs ist (`retro_kpis.py` zählt ihn also mit 1), belegt `.git/iil-guard-events.log`
  in iil-klickdummy bereits **3 reale Vorfälle über die Zeit** (2026-06-24, 2026-07-02, 2026-07-05).
  Der Längsschnitt-Zähler unterschätzt hier die reale Wiederholungsrate, weil frühere Vorfälle nie in
  einem Retro benannt wurden. Empfehlung: dieses Muster nicht auf die übliche "≥2-Retros"-Schwelle
  warten lassen, sondern direkt als Gate-Kandidat einstufen (s. `gate_candidates` im Frontmatter).
- `genesor-validation-fix-incomplete-propagation` (Befund 8) ist inhaltlich das **zweite** Auftreten
  derselben Fehlerklasse in DIESEM Repo — die erste war der Ursprungsfund selbst (Session-Retro
  2026-07-03, dokumentiert in der bestehenden Drift-Memory `genesor-security-unvalidated-path`,
  per `ls ~/.claude/projects/-home-devuser-github-iil-klickdummy/memory/` verifiziert vorhanden).
  Auch das ist trotz `retro_kpis.py`-Zähler=1 real bereits eine Wiederholung.
- `pythonpath-worktree-mismatch-cross-repo-known` (Befund 13) ist **kein** Erst-Auftreten der
  zugrundeliegenden Lektion — sie steht bereits seit 2026-07-02 in `iil-adrfw`s Memory
  `adr233-main-tree-guard-workflow.md` (Datei-Existenz per `ls` verifiziert) —, nur der erste Retro-
  Auftritt *dieses Slug-Namens* in `platform/docs/retros`. Der Zähler=1 unterschätzt die reale
  Wiederholungsrate strukturell, weil Cross-Repo-Memory keine gemeinsame Slug-Historie hat.
- `pr-collision-check-bypassed-by-direct-branch` (Befund 14) ist inhaltlich mit dem bestehenden
  Gate-Slug `parallel-session-pr-collision` (×2, bereits gate-pflichtig laut `retro_kpis.py`)
  verwandt, aber ein anderer Mechanismus: dort kollidieren zwei parallele Sessions am selben Issue,
  hier umging ein einzelner fehlerhafter Erstversuch (main-tree-guard-Blockade → Direktversuch statt
  `repo-session.sh start`) denselben eingebauten Kollisions-Check strukturell, nicht durch Parallelität.
  Bewusst als eigener Slug geführt, nicht unter `parallel-session-pr-collision` subsumiert, da die
  Ursache (Bypass durch falschen Einstiegspunkt) eine andere ist als die dort gegatete (fehlender
  Vorab-Check bei zwei echten Parallel-Sessions).
- `changelog-frozen-section-retroactive-edit` (Befund 11) ist ein Erst-Auftreten dieses konkreten
  Slugs; verwandt, aber nicht identisch mit der bereits bestehenden `retro_kpis.py`-Lektion `SI-5`
  aus dem 2026-07-03-Report (dort: Versions-Tag fehlte zu einer CHANGELOG-Sektion; hier: eine bereits
  getaggte Sektion wird nachträglich erweitert) — beide Male ist die Wurzel dieselbe Konvention
  ("CHANGELOG-Sektionen sind nach Tag-Erstellung eingefroren"), aber der konkrete Verstoß ist
  spiegelverkehrt, daher als eigener Slug geführt statt als Wiederholung von SI-5 gezählt.
- **refuted_rate dieser Session: 0,125** — liegt im gesunden Band (weder >0,8 "Stroh" noch dauerhaft
  <0,2 "Theater"; Referenz-Trend der letzten 8 Reports laut `python3 tools/retro_kpis.py`-Lauf dieser
  Session: `54a76c:0.20 · e17299-incr:0.57 · e17299:0.33 · f5e1d:0.20 · 16fd96:0.33 · 35c665:0.33 ·
  44240f:0.38 · 0b46ee:0.50`).

## 5b. Autonomie-Kalibrierung

- **Kein `over_ask` erkennbar:** #129/#135/#136 (iil-klickdummy) wurden nach Freigabe direkt gemergt;
  #965 (platform) blieb bewusst offen zur menschlichen Sichtung (Befund 3 benennt nur das FEHLENDE
  Dokumentieren des Grundes, nicht dass das Offenlassen selbst falsch wäre — ein Skill-/Prozess-Fix
  im geteilten platform-Repo unter menschliche Freigabe zu stellen ist im Rahmen der bestehenden
  Scope-Eskalations-Gates plausibel richtig).
- **Kein `over_act` erkennbar:** kein Prod-Schritt, kein Merge-auto-deploy, keine Security-/Governance-
  Config wurde in dieser Session autonom verändert. Der einzige potenzielle Kandidat (direkter
  `git checkout -b` im Haupt-Checkout) wurde vom main-tree-guard-Hook selbst verhindert, bevor ein
  echter Schaden entstand — kein Bypass, kein `--no-verify`.

## 6. Verankerung (Vorschläge — Mensch entscheidet)

**memory_candidates:**
1. `feedback` `main-tree-guard-cross-repo-lesson` — "Der `iil-adrfw`-Pitfall (main-tree-guard blockt
   direkten Checkout im Haupt-Tree; danach PYTHONPATH zeigt bei Worktree-Tests auf falschen Code) ist
   generisch für JEDES Repo mit main-tree-guard-Hook, nicht `iil-adrfw`-spezifisch. **Why:** dieselben
   zwei Fehler traten in `iil-klickdummy` erneut auf, obwohl die Lösung in einem Schwester-Repo bereits
   dokumentiert war. **How:** vor der ersten editierenden Aktion in JEDEM Repo `.git/hooks/post-checkout`
   auf main-tree-guard prüfen → sofort `repo-session.sh start` nutzen, nie direkten Checkout versuchen."
2. `feedback` `genesor-fix-scope-check-against-known-memory` — "Vor Abschluss eines Security-Fixes im
   genesor-Pfad die Memory `genesor-security-unvalidated-path` explizit gegenlesen und im PR-Body
   bestätigen, welche der dort genannten Consumer (scan.py/ucs.py/render_uc.py/lineage.py **UND**
   klickdummy_sync.py/registry.py) abgedeckt sind bzw. bewusst offen bleiben. **Why:** PR #136 deckte
   nur einen Teil des in dieser Memory bereits benannten Consumer-Kreises ab, ohne das explizit zu machen."

**adr_candidates:** keiner (alle Befunde sind Repo-lokal/Prozess bzw. Test-Abdeckungslücken — keine
Architektur-Reversal, ADR-Schwelle nicht erreicht laut `adr-threshold.md`).

**Gate-Verankerung (Vorgriff, s. §5):**
- `main-tree-guard-recurring-incident` → globaler Reminder/Hook-Text (nicht repo-lokale Memory):
  main-tree-guard-Fehlermeldung selbst um einen Verweis auf `repo-session.sh start` als EINZIGEN
  korrekten Einstieg erweitern (statt nur den Commit abzulehnen).
- `genesor-validation-fix-incomplete-propagation` → bei der nächsten Session zu diesem Thema:
  entweder den Consumer-Kreis vollständig schließen (`klickdummy_sync.py`, `registry.py._load_spec`)
  oder in der Memory explizit als "bewusst zurückgestellt, Grund X" markieren — analog zur bereits
  gelebten Praxis bei AD-6/#103 selbst.

## 7. Maßnahmen (Action-Board)

🟢 **Dein Zug**

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | PR #965 mergen (oder Grund fürs Offenhalten dokumentieren) | platform | #965 | 🟢 offen | Freigabe/Entscheidung |
| 2 | 2 memory_candidates freigeben | — | — | 🟢 offen | ja/nein je Vorschlag |

🔵 **Ich sofort (gate-frei, auf dein Wort)**

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 3 | Test-Lücken schließen (#9/#10: je 1 weiterer Regressionstest) | iil-klickdummy | 🔵 ready | 1 kleiner PR |
| 4 | `read_model.py`-jsonschema-Import wieder guarden (#6) + unbenutzten `_load_schema`-Import entfernen (#7) | iil-klickdummy | 🔵 ready | 1 kleiner PR |
| 5 | Consumer-Inventur `klickdummy_sync.py`/`registry.py._load_spec` gegen AD-6 (#8) | iil-klickdummy | 🔵 ready, größer | Design-Sichtung erst (ähnlich AD-6 selbst) |

## 8. Nicht verifiziert (Restlücken)

- **Befund 14 (PR-Kollisions-Check nicht gelaufen für #135):** nur über das Tool-Aufruf-Protokoll
  dieser Session verifizierbar, nicht über ein unabhängiges Repo-Artefakt (`repo-session.sh` persistiert
  seine PR-Listen-Ausgabe nirgends). Billigster zusätzlicher Check: `repo-session.sh` um ein Log-File
  erweitern, das jeden `start`-Aufruf inkl. Kollisions-Check-Ergebnis persistiert — dann wäre dieser
  Befund-Typ zukünftig rein artefaktbasiert prüfbar.
- **Ob der main-tree-guard-Vorfall (#12) und der PYTHONPATH-Fehler (#13) tatsächlich ursächlich
  zusammenhängen** (derselbe fehlerhafte Erstversuch löste beides aus) oder zwei unabhängige Fehler
  waren, ist aus den Artefakten nicht scharf zu trennen — beide Skeptiker bestätigten die Einzelfakten,
  aber keiner prüfte die Kausalkette zwischen ihnen explizit.
- **Ob die 2 AskUserQuestion-Runden zum KD-Referenz-Design (Grundlage für PR #965) irgendwo als
  Artefakt festgehalten sind** (außer im Chat-Verlauf dieser Session) — nicht geprüft; falls nicht,
  ist die Design-Begründung für zukünftige Leser des PR nur im PR-Body, nicht in der Konversation
  selbst nachvollziehbar.
