---
retro_schema: 1
date: 2026-10-14
repo_scope: [platform, shared-ci, risk-hub, writing-hub, dev-hub, billing-hub]
session_id: ec3416
footprint: deep
findings_total: 24
findings_survived: 18
refuted_rate: 0.25
phase3_refuted: 5
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [tag-ohne-nicht-pr-lauf, issue-ohne-dublettensuche]
recurring_findings: [claim-before-cheapest-check, check-ohne-positivkontrolle, scope-checkpoint-not-durably-recorded, edit-in-worktree-without-read, issue-offen-nach-gemergtem-fix, pr-autor-identitaet-nicht-angewandt]
gates_caught: [rohes-pytest-statt-make-test, direct-gh-pr-merge-bypasses-sa-m, secret-leak-via-safe-pattern, gh-body-file-leer-ueberschrieben, claim-before-cheapest-check]
gates_verwandt: [untested-tool-module-green-gate]
over_ask_klassen: []
over_act_klassen: [shared-ci-tag-ohne-nicht-pr-dry-run, prod-workflow-bump-ohne-dispatch]
widerlegung: "0 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Jede genutzte Phase trug hier einen eigenen Ertrag (Konflikt-Skeptiker kippte das Datei-Muster, 3b fand Befund 24, Meta neun Korrekturen); kein Melder/Gate ohne Leser, Effekt oder Dublette belegt, Liegezeit nicht gemessen."
---

# Session-Retro ec3416 — KONZ-070 Review-System Pilot: Ledger, Liste L, Advocatus (platform, shared-ci, risk-hub, writing-hub)

Sitzung `ec3416d8-abff-49d6-b425-b55635dc2aed`, 2026-10-13 07:22Z bis 2026-10-14 15:32Z, 1397
Nutzer-Nachrichten, 805 Bash-Aufrufe. Kernziel: Mandat [platform#3903](https://github.com/achimdehnert/platform/issues/3903)
(KONZ-platform-070 „Review-System org-weit", O1 Ledger in dev-hub, O2 Pilot auf Liste L, O3 Advocatus
als Cloud-Routine; WP0–WP6; Kill-Gate 2026-12-15). Sitzungsgrenze: Branch-Präfixe
`session/2026-10-13/achim-dehnert/` und `session/2026-10-14/achim-dehnert/` dieser Konversation
(Transkript-Pfad); das Datum ist nur Vorfilter. Eine Parallelsitzung desselben Tages (Retro 766e8c,
PRs #3990–#4003) ist nicht Gegenstand, aber Beleg in Befund 18 (§5a).

**Artefakte:** platform [#3889](https://github.com/achimdehnert/platform/pull/3889), [#3892](https://github.com/achimdehnert/platform/pull/3892),
[#3893](https://github.com/achimdehnert/platform/pull/3893), [#3899](https://github.com/achimdehnert/platform/pull/3899),
[#3902](https://github.com/achimdehnert/platform/pull/3902), [#3904](https://github.com/achimdehnert/platform/pull/3904),
[#3928](https://github.com/achimdehnert/platform/pull/3928)→[#3937](https://github.com/achimdehnert/platform/pull/3937),
[#3929](https://github.com/achimdehnert/platform/pull/3929), [#3938](https://github.com/achimdehnert/platform/pull/3938),
[#3940](https://github.com/achimdehnert/platform/pull/3940), [#3941](https://github.com/achimdehnert/platform/pull/3941),
[#3942](https://github.com/achimdehnert/platform/pull/3942), [#3951](https://github.com/achimdehnert/platform/pull/3951),
[#3955](https://github.com/achimdehnert/platform/pull/3955), [#3956](https://github.com/achimdehnert/platform/pull/3956)→[#3958](https://github.com/achimdehnert/platform/pull/3958),
[#3957](https://github.com/achimdehnert/platform/pull/3957), [#3964](https://github.com/achimdehnert/platform/pull/3964),
[#3965](https://github.com/achimdehnert/platform/pull/3965), [#3966](https://github.com/achimdehnert/platform/pull/3966),
[#3973](https://github.com/achimdehnert/platform/pull/3973), [#3974](https://github.com/achimdehnert/platform/pull/3974),
[#3975](https://github.com/achimdehnert/platform/pull/3975), [#3989](https://github.com/achimdehnert/platform/pull/3989);
Issues [#3900](https://github.com/achimdehnert/platform/issues/3900) (offen), [#3903](https://github.com/achimdehnert/platform/issues/3903) (Mandat);
dev-hub [#506](https://github.com/achimdehnert/dev-hub/pull/506), [#508](https://github.com/achimdehnert/dev-hub/pull/508), [#510](https://github.com/achimdehnert/dev-hub/pull/510);
billing-hub [#84](https://github.com/achimdehnert/billing-hub/pull/84);
shared-ci [#110](https://github.com/iilgmbh/shared-ci/pull/110)→[#111](https://github.com/iilgmbh/shared-ci/pull/111) (Tag `v1.1.27` = `bf98df86`, von Hand),
[#112](https://github.com/iilgmbh/shared-ci/issues/112), [#113](https://github.com/iilgmbh/shared-ci/issues/113);
writing-hub [#1362](https://github.com/achimdehnert/writing-hub/pull/1362)→[#1363](https://github.com/achimdehnert/writing-hub/pull/1363) (Rollback nach 17 min, ein Prod-Deploy Run 38534842332);
risk-hub [#836](https://github.com/iilgmbh/risk-hub/pull/836), Staging-Dispatch Run 38587124635 (AD8);
Folgewirkung meiki-lra [meiki-hub#630](https://github.com/meiki-lra/meiki-hub/issues/630) (vier Repos, Rückpin v1.1.26).

**Datenschutz:** Dieses Repo ist öffentlich. Der Report nennt keine Personen außer GitHub-Logins, die
in den verlinkten Artefakten ohnehin stehen, keine Zugangsdaten und keine Hostnamen. Kontrollprobe §8.

## Phase 0.0 — Wirkungsbilanz

`tools/gate_wirkung.py` meldet vier `RUECKFAELLIG`-Gates. Alle vier sind in den Retros desselben
Scopes vom Vortag und von heute entschieden, Link statt Neuverhandlung:
[e50644 §0.0](session-retro-2026-10-13-platform-e50644.md#phase-00--wirkungsbilanz),
[34ae36 §0.0](session-retro-2026-10-13-platform-34ae36.md#phase-00--wirkungsbilanz),
[766e8c §5a](session-retro-2026-10-14-platform-766e8c.md#5a-rückfall-prüfung).

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check (blocking) | 96 / 5 Retros | Quelle | nachschärfen, beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666), 766e8c §5a ausweiten); eigener Fall: PR-Text writing-hub#1362 „Deploy bleibt wie bisher" ohne Lauf, Teil von Befund 1 (§5a) |
| built-but-never-called | 4 / 3 | Quelle | ausweiten, beschlossen (Owner „187 go", 34ae36); kein eigener Fall |
| scope-checkpoint-not-durably-recorded (advisory) | 35 / 3 | Quelle | ausweiten Rev 11, beschlossen (766e8c §5a); eigener Fall Befund 15 (§5a) |
| check-ohne-positivkontrolle (advisory) | 5 / 2 | Quelle | nachschärfen Rev 2, beschlossen ([#3722](https://github.com/achimdehnert/platform/issues/3722)); eigener Fall Befund 2 (§5a) |

Ehrlichkeits-Sperre: `untested-tool-module-green-gate` und `gate-anchored-without-drill-or-control` stehen
auf `zu-frueh`/`unerprobt` und zählen hier nicht als wirksam; `gate-matches-spelling-not-substance` ist
widerrufen, `hook-block-wiederholt-gleiches-muster` declined. Kein Gate existiert für
`dod-reinterpreted-only-in-pr-body`, `tag-ohne-nicht-pr-lauf`, `issue-ohne-dublettensuche`,
`freigabe-vor-erstem-anlauf` (geprüft per `ls docs/governance/gates/{gates,widerrufen,declined}`).

## 1. Executive Summary

- Kernziel teilweise erreicht: O1 Ledger-Endpunkt, O2 Liste L und O3 Routine sind gebaut und gemergt (WP0–WP5), aber im Mandats-Issue ist kein Kriterium K1–K8 abgehakt, K3–K8 und WP6 sind offen, und für den Ledger gibt es noch keinen Leser (13, 14).
- Schwerster Befund (1, nach Konflikt-Skeptiker neu gefasst): Der von Hand gesetzte shared-ci-Tag `v1.1.27` bricht jeden Nicht-PR-Lauf seiner Aufrufer mit 0 Jobs, belegt 13 von 13 (push und dispatch, `ci.yml` und `deploy.yml`, sechs Repos). Nur PR-Läufe waren je grün. Vier meiki-lra-Repos, die eine andere Sitzung gezielt auf den Tag pinnte, liefen rund zwei Stunden rot (meiki-hub#630).
- Die Ursache wurde zweimal falsch festgeschrieben (2, 11): erst „gemischte Refs" im Mandats-Issue und im Memory, dann „deploy.yml-vs-ci.yml" in shared-ci#113, das weder das 34 Minuten ältere #112 noch meiki-hub#630 (2 h älter, Event-Muster schon benannt) nennt. Memory und #113 sind korrigiert; die falsche Lehre steht weiter als Kommentar in writing-hub `deploy.yml` und risk-hub `ci.yml` (24, aus der Widerlegungsbahn); die eigentliche Ursache bleibt offen.
- Dreimal ging ein Governance-PR unter dem Owner-Konto auf und wurde als App-PR neu angelegt (4). Beim dritten Fall war der Hinweis-Hook aktiv, schwieg aber, weil das Kommando erst nach Variablenzuweisungen per `cd "$wt"` in den Worktree wechselte. Das Gate ist in diesem PR an der Quelle ausgeweitet (§5a).
- Fünf Bewertungsbefunde fielen in der Falsifikation (5, 6, 16, 17, 23); unter anderem gab es nur einen Prod-Deploy statt zwei, und die ersten App-PR-Anläufe lagen nach, nicht vor dem Owner-Wort.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Tag `v1.1.27` (`_ci-python.yml`) bricht jeden Nicht-PR-Lauf: 13/13 push- und dispatch-Läufe mit 0 Jobs (`failure`/`startup_failure`), 33/33 PR-Läufe starteten; Selbsttest und writing-hub-PR-Run waren nur `pull_request`; meiki-lra vier Repos rot bis Rückpin v1.1.26; Tag steht weiter auf `bf98df86`, kein v1.1.28 | fehlende Validierung | kritisch | kommandobelegt; Konflikt-Skeptiker 2.5: Event-Muster SURVIVES, Datei-Muster REFUTED | Runs 38532968320 (writing-hub deploy.yml push), 38587124635 (risk-hub deploy.yml dispatch), 38563676513 / 38568356663 (post-hub ci.yml push/dispatch), 38563634273, 38555399460, 38563699017; shared-ci#112, #113; meiki-hub#630 | claim-before-cheapest-check (§5a); Kandidat `tag-ohne-nicht-pr-lauf` |
| 2 | Ursache „gemischte Refs" um 08:41Z als „Hypothese bestätigt" gemeldet und um 15:18Z ins Memory geschrieben; Beleg war nur der grüne Rückbau auf v1.1.20 (jeder Pin auf v1.1.20 wäre grün); Gegenprobe AD8 mit beiden Refs auf v1.1.27 fiel ebenso | fehlende Validierung | hoch | kommandobelegt | #3903 Kommentar 6164417991; Memory `feedback_shared_ci_refs_gleich_je_datei` (15:18:07Z, korrigiert in dieser Retro); Run 38587124635 | check-ohne-positivkontrolle (§5a) |
| 3 | Ledger-Poster mit 15 Mock-Tests gemergt, nie gegen den echten Endpunkt gelaufen; 403 durch Cloudflare-Filter auf den Python-urllib-User-Agent fiel erst in Routine-Läufen am Folgetag auf | fehlende Validierung | hoch | kommandobelegt | #3937 (`tools/advocatus_ledger_post.py`, Tests mocken `urlopen`); #3975 (`5fe30a85`); #3989 (`6a0dd751`) | gates_verwandt `untested-tool-module-green-gate` (Modul hatte Tests, nur ohne Netzstrecke) |
| 4 | Governance-PR dreimal unter dem Owner-Konto statt als App-PR: #3928 (10-13 11:15Z) → #3937, shared-ci#110 → #111 (18 h offen), #3956 (10-14 09:47Z) → #3958; beim dritten Fall war der Hinweis-Hook seit 08:11Z installiert und schwieg | Prozesslücke | hoch | kommandobelegt | PR-Paare; #3930 (RA1, 11:32Z); Hook-Commit `83e496d7` (#3943, 08:05Z); Transkript 0 Treffer „Hinweis (pr-autor-identitaet" | pr-autor-identitaet-nicht-angewandt, Rückfall bei #3956 (§5a) |
| 5 | Selbstfreigabe-Pfad (Autor App, Approve und Merge Owner-Konto) verfrüht aktiviert | verfrühte Festlegung | – | REFUTED (Phase 3) | Owner-Zitate in #3937/#3940 („SA go", „LL go"); `policies/autonomy-gates.md` „Owner-Wort als Approval" mit Ratsche und Kalibrierfenster bis 2026-10-26 | – |
| 6 | Review-Engine im Reusable ungepinnt (`platform_ref` Default `main`) | verfrühte Festlegung | – | REFUTED (Phase 3) | Input `platform_ref` erlaubt Pin; `enable_review`/`review_blockieren` Default false; Job `review` nicht in `gate.needs`; Stufe 2 erst nach ADR | – |
| 7 | Literal `PROFIL: deployed` im Workflow mit Kommentar „vorerst", eine Stunde später per Registry ersetzt | Prozesslücke | niedrig | kommandobelegt | #3957 (`ae37ac0`), #3964 (`6caa342`) | Hausregel „kein Hardcoding" (Owner 2026-10-07) |
| 8 | Öffentlich auflösbarer Dienst-Hostname in `registry/review-risiko.yaml` | Einordnung | niedrig | pre_refuted (Finder selbst: kein Verstoß, Endpunkt tokengeschützt, vergleichbare Einträge bestehen) | #3937, dev-hub#508 | – |
| 9 | `BOT_REVIEW_REPOS = ("achimdehnert/platform",)` als Literal neben der YAML-Positivliste, in #3938 (+202 Zeilen derselben Datei) nicht bereinigt | Prozesslücke | niedrig | kommandobelegt | `tools/pr_merge_sa.py:81` (vorbestehend `f7998296`, 2026-10-06); #3938 | Hausregel „kein Hardcoding" |
| 10 | Zwei Quellwege für dieselbe Engine: `review-check.yml` nimmt den PR-Checkout, `_review.yml` platform/main | Werkzeug | niedrig | kommandobelegt | #3957 (`ae37ac0`); shared-ci `.github/workflows/_review.yml:31,59` (`platform_ref` → `ref:`) | – |
| 11 | shared-ci#113 (15:17Z) zum selben Symptom wie das 34 min ältere #112 aus einer anderen Sitzung (gleiches Konto, meiki-Kontext), ohne Querverweis; #113 nennt ein Datei-Muster, dessen „grüne" Fälle alle PR-Läufe sind (Event-Confound), #112 und meiki-hub#630 (13:04Z, mit Hypothese `./_review.yml`) das Event-Muster, das die Daten tragen; Querverweis am 16:07Z nachgetragen | Kommunikation | hoch | kommandobelegt; Konflikt-Skeptiker 2.5; 3b: hält | #112 Body (14:43:16Z), #113 Body (`grep 112`: 0), meiki-hub#630; Laufdaten Befund 1; Kommentar 6172717525 | Kandidat `issue-ohne-dublettensuche` |
| 12 | K2 „Repo erhält Review-Check ohne eigene Workflow-Zeile" als erfüllt gemeldet, geliefert ist ein Schalter (`enable_review: true` in writing-hub#1362 = eigene Zeile); Sandbox-Nachweis aus KONZ-070 §4 fehlt | verfrühte Festlegung | mittel | SURVIVES (Phase 3) | #3903 Body K2; KONZ-070 §4 Z.153; Kommentar 07:42:15Z „K2 Nachweis erbracht"; writing-hub#1362 Diff | `dod-reinterpreted-only-in-pr-body` (kein Gate) |
| 13 | Mandatsstand nicht konsolidiert: K1–K8 im Issue-Body alle `- [ ]`, obwohl K1 und WP0–WP5 belegt gemergt sind | Kommunikation | mittel | kommandobelegt | `gh issue view 3903` Body 8× `- [ ]` (Stand 15:18Z) | – |
| 14 | K3–K8 und WP6 offen; kein Leser des Ledgers (Session-Start liest nur Routine-Berichte; `git grep review-ledger` ohne Leser); Advocatus wirkt nur per Kommentar, „Ledger schreibt" bleibt Hypothese | Prozesslücke | mittel | kommandobelegt | #3903 Kommentare 10-13 10:07:59Z, 10-14 13:36:59Z, 15:07:46Z; `governance/melder-register.yaml`, `tools/session_start_checks.sh` | – |
| 15 | Schreiben in writing-hub (drittes Repo, Prod-Pfad) nur mit Chat-Checkpoint; #1362 um 07:40:05Z erstellt, durables „K2 go" erst 08:03Z; keine `scope +`-Zeile für writing-hub, risk-hub, shared-ci, dev-hub, billing-hub | Prozesslücke | mittel | SURVIVES eng (Phase 3): Mandat O2 deckt Liste L, Owner-Worte in PR-Texten zitiert, Regel „Business-Start-Repo" greift formal nicht | #3903 Kommentare 07:33Z, 07:36Z, 07:42:15Z, 08:03:16Z; #1362 Body; billing-hub#84, dev-hub#506/#510 je mit Owner-Zitat | scope-checkpoint-not-durably-recorded (§5a) |
| 16 | Owner-Worte im Mandats-Issue nicht vom Agenten unterscheidbar (39/39 Kommentare unter einem Konto) | Kommunikation | – | REFUTED (Phase 3) als Prozesslücke: benannter Preis der Regel „Owner-Wort als Zitat" (Memory, Owner „MC beide ja" 2026-10-07) | `policies/autonomy-gates.md:296` („Owner-Wort als Approval"); shared-ci#111 zwei Approvals mit Zitat | – |
| 17 | Zwei Prod-Deploys auf Verdacht in 17 min | verfrühte Festlegung | – | REFUTED (Phase 3): Run 38532968320 hatte 0 Jobs und deployte nichts; ein Prod-Deploy (38534842332), gedeckt durch „K2 go … inkl. möglichem Rollout" 08:03Z; der Wächter nutzte dasselbe Zitat für #1363 wieder | writing-hub Runs; #3903 Kommentar 08:03:16Z | Bump unnötig und PR-Text ungetestet gehen in Befund 1 |
| 18 | platform#3900 (M1) 31 h nach Merge von #3892 offen; der PR schreibt `Refs #3900` statt `Closes`; der Hinweis-Check „Schließ-Bezug" wurde an #3928/#3937 wiederholt nicht umgesetzt | Prozesslücke | mittel | kommandobelegt | #3892 Body Z. 21; `gh issue view 3900` OPEN; PR-Kommentare #3928/#3937 | issue-offen-nach-gemergtem-fix (§5a: Messpunkt `/session-ende` noch nicht erreicht; Parallelsitzung revidiert in #3993) |
| 19 | 33 „File has not been read"-Fehler in mindestens sechs Salven in frischen Worktrees (10-13 08:28, 11:02 ×6, 12:27, 13:24 ×3; 10-14 12:48 ×4) | Werkzeug | mittel | kommandobelegt | Transkript-Auswertung `tools/retro_transkript_kennzahlen.py` (`retro-kennzahlen.txt` Z. 30–51; Quelle ist das Sitzungs-Transkript, nicht im Repo); `docs/governance/gates/gates/edit-in-worktree-without-read.json` (schranke seit 10-13) | edit-in-worktree-without-read (§5a) |
| 20 | Hooks fingen wiederholt dasselbe Muster: rohes pytest 12×, Push-Blocks pytest/ruff 3×, claim-before 6×, leerer `--body-file` 4×, Merge-Guard 8×; Verhalten wechselte nicht auf `make test` | Prozesslücke | mittel | kommandobelegt | Transkript-Auswertung (`retro-kennzahlen.txt` Z. 29, 43, 47, 52–55); `tools/gate_wirkung.py` (`gate-wirkung.txt`); Hook-Quellen unter `tools/claude-hooks/` | gates_caught: rohes-pytest-statt-make-test, direct-gh-pr-merge-bypasses-sa-m, gh-body-file-leer-ueberschrieben, claim-before-cheapest-check, secret-leak-via-safe-pattern |
| 21 | Merge-Guard-Fehlalarm: `gh pr comment` und ein `printf`-Vorspann wurden geblockt, weil der Merge-Befehl im Kommentartext stand; dazu ein falsches OWNER_WORT-Marker-Format | Werkzeug | niedrig | kommandobelegt | Transkript-Auswertung (`retro-kennzahlen.txt` Z. 25, 27, 56; 10-13 07:44Z, 13:54Z); Guard `tools/claude-hooks/block_direct_pr_merge.py` | direct-gh-pr-merge-bypasses-sa-m (Guard matcht Text, nicht Befehlsposition) |
| 22 | Owner-Worte in #3903 nicht durchgängig als Zitat: AD8-Kommentar ohne Zitat, AD5-Kommentar nur Status ohne „erledigt"-Zitat | Kommunikation | niedrig | kommandobelegt | #3903 Kommentare 6171735545, 6171515462 | Memory `feedback_owner_wort_als_zitat_im_artefakt` |
| 23 | App-PR-Anläufe ohne vorher eingeholte Freigabe (vier Auto-Mode-Bypass-Ablehnungen 10-13 11:47–11:53) | Prozesslücke | – | REFUTED (Phase 3): Owner-Wort „APP go autonom" 11:46:40Z lag 30 s vor dem ersten Anlauf; Owner legte 11:50:04Z eine Allow-Regel an; Rest: zweimal dieselbe Aktion nach Ablehnung statt sofort Owner-Zug | Transkript-Nutzerzeile 11:46:40Z; Kennzahlen Z. 4–21; Owner-Zug `konz070-app-pr.sh` 12:07:16Z → #3937 | Kandidat `freigabe-vor-erstem-anlauf` entfällt |
| 24 | Die widerlegte Ursache „gemischte Refs" steht als Lehre in zwei Konsumenten-Workflows auf `main` (writing-hub `deploy.yml:123` aus #1363, risk-hub `ci.yml:13` aus #836); writing-hub `ci.yml:165` steht weiter auf `_ci-python.yml@v1.1.27` und hat einen `workflow_dispatch`-Trigger (`ci.yml:32`), jeder manuelle Lauf fiele nach Befund 1 mit 0 Jobs | fehlende Validierung | mittel | NEU aus 3b, kommandobelegt (nachgezogen per `git show origin/main`) | writing-hub `6a5f522d`-Gegenstück #1363 Diff; risk-hub #836 (`6a5f522d`); kein Nicht-PR-Lauf von writing-hub `ci.yml` seit 07:30Z | Folge von Befund 2; Soll-Schritt #24 |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 3 | O1–O3 gebaut und gemergt, aber K3–K8/WP6 offen und kein Ledger-Leser (Befund 14); K2 nur als Schalter (12) |
| Architektur/Design | 3 | Regeln als Daten und Engine ausgelagert tragen; zwei Quellwege für dieselbe Engine (10), Positivliste doppelt als Literal und YAML (9) |
| Code-/Konventionstreue | 3 | 33 Edit-ohne-Read, 12 rohe pytest-Aufrufe trotz Hook (19, 20); Literal „vorerst" (7) |
| Risiko/Debt | 2 | Tag v1.1.27 bricht Nicht-PR-Läufe in sechs Repos, davon vier außerhalb der Autonomie-Freigabe, Ursache offen (1); Ledger-Poster ohne echten Lauf gemergt (3) |
| Prozess-Effizienz | 2 | Dreimal Owner-PR → App-PR (4), Rollback writing-hub nach 17 min (1), Dubletten-Issue mit falschem Muster (11) |
| Entscheidungsqualität | 3 | Falsche Ursache festgeschrieben, aber am selben Tag mit Gegenprobe (AD8) widerlegt (2); K2-Deutung ohne Rückfrage (12); Prod-Weg und Freigaben hielten der Falsifikation stand (5, 17, 23) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Tag v1.1.27 von Hand gesetzt, nur PR-Selbsttest grün (shared-ci#111, Runs Befund 1) | Vor dem Tag ein `workflow_dispatch`- oder push-Lauf eines Aufrufers gegen den Kandidaten-SHA; Tag erst nach grünem Nicht-PR-Lauf, sonst Issue in shared-ci mit Konsumentenliste | #1 |
| Ursache „gemischte Refs" aus grünem Rückbau abgeleitet (#3903 08:41Z, Memory 15:18Z) | Kontrollfall vor der Festschreibung: ein Lauf mit unverändertem Tag und gleichen Refs; Memory erst nach Kontrollfall, bis dahin „Hypothese" im Kommentar | #2 |
| Ledger-Poster mit Mocks gemergt, 403 am Folgetag (#3937 → #3989) | Vor dem Merge ein echter GET mit Token gegen den Endpunkt aus der CI-Umgebung des Konsumenten (Cloud-Routine), Ergebnis im PR | #3 |
| Governance-PR unter Owner-Konto, Hook schwieg bei `cd "$wt"` nach Zuweisung (#3956) | Hook löst das letzte `cd`-Segment vor `gh pr create` samt Variablen auf (dieser PR); Agent prüft vor `gh pr create` auf Tabu-Pfad die CODEOWNERS und nimmt direkt `lotse-gh` | #4 |
| `PROFIL: deployed` „vorerst" im Workflow (#3957), eine Stunde später Registry (#3964) | Fachliteral erst als Registry-/Datendatei-Eintrag, dann Workflow; „vorerst" ist ein Befund, kein Kommentar | #7 |
| `BOT_REVIEW_REPOS`-Literal in der Datei, die #3938 um 202 Zeilen erweiterte | Beim Anfassen einer Datei vorbestehende Fachliterale in die bestehende YAML-Positivliste ziehen oder Issue anlegen | #9 |
| Engine aus PR-Checkout in `review-check.yml`, aus platform/main in `_review.yml` (#3957) | Ein Quellweg: `review-check.yml` ruft dasselbe Reusable mit `platform_ref: ${{ github.sha }}` statt eigener Kopie der Schritte | #10 |
| #113 ohne Suche nach #112 im selben Repo, Muster aus PR-Läufen abgeleitet | Vor `gh issue create` eine Suche `gh issue list --search "<Symptom>"` im Zielrepo; Laufdaten nach Event aufschlüsseln, bevor ein Muster behauptet wird | #11 |
| K2 als erfüllt gemeldet mit Schalter statt OOTB (#3903 07:42Z) | Kriterium im Wortlaut aus Issue/KONZ zitieren und gegen den Beleg stellen; Abweichung als „K2 teilerfüllt, Rest: Sandbox-Nachweis" | #12 |
| K1–K8 alle ungetickt trotz gemergter WP0–WP5 | Nach jedem WP-Merge Issue-Body redigieren: Kästchen setzen oder Statusblock „K | Beleg | Stand" anhängen | #13 |
| Schreibweg Ledger vor Leser gebaut, K3–K8 ohne Zeitplan | WP-Reihenfolge am Kill-Gate ausrichten: erster Leser (Session-Start-Melder) im selben WP wie der Schreibweg; K3–K8 je mit Datum im Issue | #14 |
| writing-hub-PR vor durablem Checkpoint (07:40Z vs 08:03Z) | Vor dem ersten Schreibvorgang in ein drittes Repo ein Kommentar im Mandats-Issue „Scope + <repo>, Grund, Prod-Wirkung ja/nein", dann PR | #15 |
| #3900 offen nach Merge des Fixes mit `Refs` | Hinweis-Check „Schließ-Bezug" am PR umsetzen (`Closes #N`), sonst Issue im selben Zug schließen; `/session-ende` als Messpunkt laufen lassen | #18 |
| 33 Edit-ohne-Read in sechs Salven nach Worktree-Start | Nach jedem Worktree-Start und jeder Verdichtung alle Zieldateien in einem Read-Batch, dann erst Edit (766e8c §5a Ausweitung) | #19 |
| Rohes pytest 12× trotz Hook | Vor dem ersten Test im Repo `Makefile` lesen und `make test` als einzigen Testbefehl notieren; Hook-Block = Befehl wechseln, nicht umformulieren | #20 |
| Merge-Guard blockt Kommentartext mit „gh pr merge" | Guard auf Befehlsposition umstellen (Segmentanfang nach `;`/`&&`/Newline), Kommentar-Texte per `--body-file` | #21 |
| AD5/AD8 ohne Owner-Zitat in #3903 | Jede Statusmeldung zu einem Kürzel beginnt mit dem Owner-Zitat samt Zeitstempel, auch wenn kein Merge folgt | #22 |
| Fehldiagnose als Workflow-Kommentar in writing-hub und risk-hub committet, writing-hub `ci.yml` latent auf v1.1.27 | Beim Widerruf einer Ursache alle Stellen suchen, die sie zitieren (`git grep -l "gemischte Refs"` in allen Konsumenten), und im selben Zug korrigieren; Pin erst mit v1.1.28 nach grünem Nicht-PR-Lauf | #24 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand vor dieser Retro, `retro-kpis.txt`): `claim-before-cheapest-check`
×108, `scope-checkpoint-not-durably-recorded` ×36, `edit-in-worktree-without-read` ×10,
`check-ohne-positivkontrolle` ×9, `secret-leak-via-safe-pattern` ×8, `direct-gh-pr-merge-bypasses-sa-m`
×8, `issue-offen-nach-gemergtem-fix` ×6, `pr-autor-identitaet-nicht-angewandt` ×2 (e50644, 327837).
Alle sechs `recurring_findings` liegen ≥2 und sind gedeckt (Gate existiert); die Gate-Pflicht löst
sich in §5a, nicht in neuen Notizen. `refuted_rate` 0.25 liegt im gesunden Band des KPI-Berichts.
Memory-Abgleich per `grep` in `MEMORY.md`: `feedback_shared_ci_refs_gleich_je_datei` (korrigiert),
`feedback_closes_statt_schliesst` (Befund 18 verletzt sie), `feedback_owner_wort_als_zitat_im_artefakt`
(Befund 22 verletzt sie) existieren; für Tag-Validierung und Issue-Dublettensuche gibt es keinen Eintrag.

### 5a. Rückfall-Prüfung

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| pr-autor-identitaet-nicht-angewandt (advisory, gebaut 2026-10-13, installiert 10-14 08:11Z) | Befund 4: #3956 um 09:47Z auf `registry/review-regeln.yaml` unter dem Owner-Konto, kein Hinweis im Transkript | Quelle: `_arbeitsverzeichnis()` in `tools/claude-hooks/pr_anlegen_kollision_hinweis.py` sah nur `cd` am Kommandoanfang ohne Variablen; das Kommando begann mit `d=…; wt=…; cd "$wt" && …`, der Hook las das Haupt-Tree auf `main`, fand keinen Diff und schwieg. #3928 und shared-ci#110 liegen vor dem Bau und zählen nicht | **ausweiten, in diesem PR:** letztes `cd`-Segment vor `gh pr create`, `$VAR`/`${VAR}` aus Zuweisungen desselben Kommandos aufgelöst, offene Variable → cwd; Positivkontrolle `test_should_hinweis_zeigen_wenn_cd_nach_zuweisungen_in_variable_steht` (rot gegen alten Stand, grün mit Fix) plus Gegenprobe; Gate-JSON `revised: 2026-10-14`, neuer `faengt`-Eintrag; `gate_verankerung_check.py --neu` grün |
| claim-before-cheapest-check (blocking) | PR-Text writing-hub#1362 „auf main/Deploy bleibt alles wie bisher" ohne Nicht-PR-Lauf (Teil von Befund 1) | Quelle: Behauptung über einen Workflow-Lauf, den der Hook nicht als prüfbare Aussage erkennt; derselbe Hook fing 6 andere Aussagen (`gates_caught`), der Fall aus Befund 1 lag außerhalb seines Musters | beschlossen in [766e8c §5a](session-retro-2026-10-14-platform-766e8c.md#5a-rückfall-prüfung) (ausweiten) und [#2666](https://github.com/achimdehnert/platform/issues/2666); Fall dort verbucht, kein zweiter Beschluss |
| check-ohne-positivkontrolle (advisory) | Befund 2: Rückbau-grün als Kausalbeleg | Quelle: Gate kennt Abwesenheitsprüfungen, nicht Kausalschlüsse aus einem Rückbau | beschlossen Rev 2 ([#3722](https://github.com/achimdehnert/platform/issues/3722)); Fall verbucht; Soll-Schritt #2 nennt den Kontrollfall |
| scope-checkpoint-not-durably-recorded (advisory) | Befund 15: writing-hub-PR 23 min vor dem durablen „K2 go" | Quelle: Hook misst Repo-Wechsel, nicht den Prod-Pfad des dritten Repos | beschlossen [766e8c §5a](session-retro-2026-10-14-platform-766e8c.md#5a-rückfall-prüfung) (ausweiten Rev 11); Fall verbucht |
| edit-in-worktree-without-read (schranke seit 10-13) | Befund 19: 33 Fehler, Salven in frischen Worktrees derselben Bau-Sitzung des Gates | Quelle: Start-Hinweis nennt nur bekannte Zieldateien, Salve entsteht bei neu hinzukommenden | Antwort ausweiten, beschlossen in [766e8c §5a](session-retro-2026-10-14-platform-766e8c.md#5a-rückfall-prüfung); die Umsetzung wartet dort auf das Owner-Wort; Fall verbucht |
| issue-offen-nach-gemergtem-fix | Befund 18: #3900 offen nach #3892 | Messpunkt des Gates ist `/session-ende`, das noch nicht lief → kein Rückfall; Parallelsitzung revidiert das Gate in [#3993](https://github.com/achimdehnert/platform/pull/3993) (`_FOLGESCHRITT_RE`) | kein zweiter Edit; Lösung des Falls = Issue schließen (Owner-Zug R4, Classifier verweigerte den Agenten-Close) |
| untested-tool-module-green-gate (zu-frueh) | Befund 3 | außerhalb des Zuschnitts: das Gate prüft Module ohne Tests, der Poster hatte 15 Tests, nur ohne Netzstrecke | `gates_verwandt`; kein Rückfall, Soll-Schritt #3 |

### 5b. Autonomie-Kalibrierung

- **over_act** `shared-ci-tag-ohne-nicht-pr-dry-run`: Tag `v1.1.27` von Hand gesetzt (Publish für alle Konsumenten) ohne push- oder dispatch-Lauf; das Owner-Wort „WP2 go" deckte den Merge, nicht den Tag als Publish. Die vier meiki-lra-Repos pinnte eine andere Sitzung gezielt (3b: post-hub #127, 11:07Z), der Tag war dafür nur die Voraussetzung (Befund 1).
- **over_act** `prod-workflow-bump-ohne-dispatch`: `deploy.yml`-Bump in writing-hub#1362 autonom nach „RH WP2 du go autonom", obwohl der Review-Job `deploy.yml` nicht braucht und `main` dort Prod ist; der Prod-Lauf selbst war durch „K2 go" gedeckt (Befund 17 REFUTED), der Bump nicht nötig (Befund 1).
- **over_ask**: keine Klasse. Geprüft: alle 🟢-Owner-Schritte der Sitzung (Issue-Close #3900 nach Classifier-Verweigerung, roter Fehlertext aus der UI, `scope +risk-hub`, App-PR-Erzeugung) betrafen Rechte, die der Agent nicht hat, oder Prod/Publish; kein deterministisch-reversibler Schritt wurde vorgelegt.
- Muster ≥2 über Retros: `prod-host-vorabtest-vor-freigabe` (766e8c) und `prod-workflow-bump-ohne-dispatch` (hier) sind dieselbe Familie „Prod-Pfad vor dem Gate berührt" → Nominierung in `retro_kpis.py --nominierung` beim nächsten Lauf prüfen.

## 6. Verankerung

Memory korrigiert (eigene Memory, im selben Zug): `feedback_shared_ci_refs_gleich_je_datei` trägt jetzt
Ursache offen, Event-Muster, Fehldiagnose und Regel „vor dem Pin einen Nicht-PR-Lauf sehen".

**memory_candidates**

```markdown
---
name: feedback_issue_vor_anlage_dublettensuche_im_zielrepo
description: Vor `gh issue create` im Zielrepo nach dem Symptom suchen; Parallelsitzungen und der Owner legen zum selben Lauf eigene Issues an (shared-ci#112 vs #113, 34 min, 2026-10-14)
metadata:
  type: feedback
---
Retro ec3416 Befund 11: shared-ci#113 (15:17Z) nannte #112 (14:43Z, andere Sitzung, gleiches Symptom) nicht
und behauptete ein Muster, das nur aus PR-Läufen stammte.
**Why:** Zwei Issues zu einem Lauf tragen konkurrierende Hypothesen, niemand löst den Widerspruch.
**How to apply:** `gh issue list -R <repo> --search "<Run-ID oder Symptom>" --state all` vor dem
Anlegen; Treffer → Kommentar dort mit Querverweis statt neues Issue; Laufdaten vor einer
Muster-Behauptung nach Event (`pull_request` vs push/dispatch) aufschlüsseln.
```

```markdown
---
name: feedback_mandats_kriterium_im_wortlaut_pruefen
description: Ein Kriterium aus Mandat/KONZ gilt als erfüllt, wenn der Beleg den Wortlaut trifft; ein Schalter ist kein „ohne eigene Zeile" (K2 KONZ-070, 2026-10-14)
metadata:
  type: feedback
---
Retro ec3416 Befund 12: K2 „Review-Check ohne eigene Workflow-Zeile" wurde mit `enable_review: true`
(eine eigene Zeile) als erbracht gemeldet; der Sandbox-Nachweis aus KONZ-070 §4 fehlt.
**Why:** Umgedeutete Kriterien lassen das Kill-Gate grün aussehen, obwohl das Ziel offen ist.
**How to apply:** Kriterium wörtlich zitieren, Beleg daneben, Abweichung als „teilerfüllt, Rest: …"
im Mandats-Issue; Kästchen erst dann setzen.
```

**adr_candidates:** keiner. Die Engine-Auslagerung (Regeln als Daten, `platform_ref`) ist in KONZ-070
Stufe 1 gedeckt; Stufe 2 (Default in shared-ci, blockierend) fordert laut KONZ selbst ein ADR nach dem
Kill-Gate, nicht jetzt (`adr-threshold`).

## 7. Maßnahmen

Aus dem Soll-Ablauf abgeleitet; IDs stabil zum Board der Sitzung (AD8, AD10, SC1–SC3).

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| R1 | Gate pr-autor-identitaet ausgeweitet (cd nach Zuweisung) | platform | dieser PR | 🔵 | Merge per SA-Pfad, dann Hook-Kopie verteilen (0.7.5) |
| R2 | Memory shared-ci-Ursache korrigiert | platform | `feedback_shared_ci_refs_gleich_je_datei` | ✅ | – |
| R3 | #113 mit #112 verknüpfen, Datei-Muster zurücknehmen | shared-ci | [#113 Kommentar](https://github.com/iilgmbh/shared-ci/issues/113#issuecomment-6172717525) | ✅ | – |
| R10 | Fehldiagnose-Kommentare in writing-hub `deploy.yml` und risk-hub `ci.yml` korrigieren, writing-hub `ci.yml` erst mit v1.1.28 | writing-hub, risk-hub | Befund 24 | 🟢 | Owner-Wort `R10 go` (writing-hub Prod-Pfad, risk-hub `scope +risk-hub`); Text liegt bereit |
| R4 | #3900 schließen (M1 gemergt in #3892) | platform | [#3900](https://github.com/achimdehnert/platform/issues/3900) | 🟢 | Owner: `~/zug/i3900.sh` (Classifier verweigerte dem Agenten den Close) |
| SC1 | Ursache startup_failure v1.1.27 | shared-ci | [#112](https://github.com/iilgmbh/shared-ci/issues/112) | ⛔ | hängt an SC2; danach v1.1.28 nur nach push/dispatch-Lauf |
| SC2 | Roten Fehlertext aus der Run-Seite liefern | risk-hub | Run 38587124635 | 🟢 | Owner: Run-Seite öffnen, roten Kasten hier einfügen |
| SC3 | AD8-Ergebnis auf #828 kommentieren | risk-hub | [#828](https://github.com/iilgmbh/risk-hub/pull/828) | 🟢 | Owner: `scope +risk-hub` |
| R5 | K-Status in #3903 redigieren, K2 als teilerfüllt | platform | [#3903](https://github.com/achimdehnert/platform/issues/3903) | 🔵 | Statusblock K1–K8 mit Beleg; Sandbox-Nachweis als WP-Zeile |
| R6 | Gate-Kandidaten bauen: tag-ohne-nicht-pr-lauf, issue-ohne-dublettensuche | platform | §6 | 🟢 | Owner-Wort `R6 go`, dann je ein Gate-PR mit Drill |
| R7 | `BOT_REVIEW_REPOS`-Literal in YAML-Positivliste | platform | `tools/pr_merge_sa.py:81` | 🟢 | Owner-Wort `R7 go` (Tabu-nahe Datei, App-PR) |
| AD10 | Ersten echten Bulk-POST des Ledgers nachlesen | platform | [#3903](https://github.com/achimdehnert/platform/issues/3903) | 🟢 | nächster Routine-Lauf zeigt Statuscode; ich lese nach |
| AD8 | Staging-Dispatch bestätigt Warnung | risk-hub | Run 38587124635 | ✅ | – |

## 8. Nicht verifiziert (Restlücken)

- **getan:** Laufdaten von 404 Runs in sechs Repos per `gh api` nach Event und Job-Anzahl ausgewertet (Konflikt-Skeptiker); 39 Kommentare in #3903 gelesen; PR-Paare, Issue-Bodies, Hook-Commit-Zeiten und Transkript-Kennzahlen geprüft; Hook-Ausweitung mit Positivkontrolle gedrillt; `make test` im Worktree grün (7250 passed, Hook-Tests im Makefile-Ziel enthalten); Memory korrigiert; die meiki-Kausalität ist gemessen (meiki-hub#630: v1.1.26-dispatch 16 Jobs gegen v1.1.27 `startup_failure`). Datenschutz-Kontrollprobe vor dem Commit: `grep -c` auf E-Mail-Muster, Hostnamen der eigenen Domain und Token-Präfixe im Report → 0 Treffer.
- **angenommen:** Der Fehlertext „workflow file issue" ist für alle 13 Läufe gleich (nur für zwei in der UI gesehen).
- **nicht verifizierbar:** Der rote Fehlertext steht nur in der Run-Seite, nicht in der API (SC2); der Mechanismus (nested `./_review.yml`, `if:` mit `github.event_name`) bleibt Hypothese; ob die Cloud-Routine `advocatus-diaboli` nach #3989 real ins Ledger schreibt (AD10); Owner-Klicks hinter den App-PRs; `schedule`/`release`-Events mit v1.1.27.
- **offen geblieben:** Gegenfall `deploy.yml@v1.1.27` bei `pull_request`, billigster Check: ein PR im Sandbox-Spiegel von writing-hub mit `deploy.yml` auf v1.1.27; Sandbox-Nachweis für K2 (R5), billigster Check: Sandbox-Repo mit nur `_ci-python.yml@<sha>` ohne `enable_review`; Scharfschaltung des pr-autor-Gates per `expires_note`, billigster Check: `gate_wirkung.py` nach der nächsten Sitzung; Streichbahn-Ratsche siehe `## Streichbahn`.

## Widerlegung

Phase 3b, frischer Opus-Agent mit Report-Entwurf, Footprint und Artefaktliste; 15 lesende Aufrufe
gegen `origin/main` (platform, shared-ci-Tags) und GitHub (shared-ci, writing-hub, risk-hub, meiki-hub,
post-hub). Verdikt `widerlegung: "0 gekippt, 1 neu"`.

**Frage 1 (SURVIVES/kommandobelegt): BESTAETIGT, mit Korrekturen**

- Befund 1 hält im Kern (Run 38532968320 `jobs=0`, 38534842332 18 Jobs; meiki-hub#630 misst v1.1.26-dispatch 16 Jobs gegen v1.1.27 `startup_failure`). Nebensatz korrigiert: die meiki-lra-Repos kamen nicht durch den Publish, eine andere Sitzung pinnte sie gezielt (post-hub #127, 11:07Z); §1 und §5b entsprechend umformuliert, meiki-Kausalität in §8 von „angenommen" nach „getan".
- Befund 11 hält und ist schärfer: meiki-hub#630 (13:04Z) nannte Event-Muster und `./_review.yml`-Hypothese 2 h vor #113; „Owner-Issue" für #112 war nicht belegbar (gleiches Konto) → umformuliert. R3 war zum Prüfzeitpunkt erledigt (Kommentar 16:07Z) → ✅.
- Befund 2 hält und wird stärker: die Memory-Zeile 15:18Z entstand 2 h nach dem Gegenbeleg in meiki-hub#630.
- Befunde 3, 4, 9, 12, 13, 18 halten (je unabhängig nachgezogen: `urlopen` 13× in den Tests, Hook-Commit 08:05Z vor #3956 09:47Z, `pr_merge_sa.py:81` genutzt in Z. 369/387/887, K2-Wortlaut in KONZ-070, 8× `- [ ]`, #3900 OPEN mit `Refs` in #3892 Z. 22).

**Frage 2 (REFUTED/pre_refuted): BESTAETIGT**

- 6 hält: `platform_ref` Default `main`, Job `review` advisory und nicht in `gate.needs` (`_ci-python.yml` Z. 902–923 am Tag). 17 hält: einziger Deploy-Lauf 38534842332, kein weiterer im Fenster 07:30–09:00Z. 8 hält: der Host steht schon in vier Dateien auf `origin/main`.
- 5, 16, 23 unentscheidbar für den Agenten (Belege sind Transkript-Zeitstempel und eine Policy außerhalb des Repos); billigster Check: `grep` auf die Nutzerzeile 11:40–11:55Z im Sitzungs-Transkript und auf „Owner-Wort als Approval" in `policies/autonomy-gates.md:296`. Beides ist in dieser Retro inline geprüft; die Verdikte bleiben.

**Frage 3 (fehlende Dimension): NEU → Befund 24**

- Die widerlegte Ursache steht als Lehre in writing-hub `deploy.yml:123` (#1363) und risk-hub `ci.yml:13` (#836); writing-hub `ci.yml:165` bleibt auf v1.1.27 mit `workflow_dispatch`-Trigger, latent kaputt. Aufgenommen als Befund 24, Soll-Schritt #24, Maßnahme R10.

Nicht prüfbar (3b): Transkript-Belege für 5, 16, 23; ob die Cloud-Routine nach #3989 real ins Ledger schreibt (AD10); Mechanismus des `startup_failure` ohne roten Fehlertext (SC2).

## Streichbahn

**keiner, weil** jede genutzte Phase in dieser Retro einen eigenen, nicht anders erreichbaren Ertrag
hatte: der Konflikt-Skeptiker (2.5) kippte das Datei-Muster, das sonst als Befund in den Report
gegangen wäre; 3b fand Befund 24 und korrigierte zwei Nebensätze; der Meta-Agent lieferte neun
Formkorrekturen (Belege ohne Zeile, Platzhalter, fehlende Links in §5a). Für „kein Leser", „kein
Effekt" oder „Dublette" wurde kein Melder oder Gate geprüft; „Liegezeit" ist ohne Lauf von
`gate_deckung.py` nicht messbar. Beobachtung ohne Belegart, als Kandidat für die nächste Retro:
der Hygiene-Melder nennt beim Start 32 abgelaufene Leases (älteste 118 Tage) in jeder Sitzung,
ohne dass eine Lease verschwindet; Belegart wäre „kein Effekt" oder „Liegezeit", beides hier
ungemessen. Ratsche: zweite Retro in Folge ohne Kandidat zählt als Befund.

## Self-Review

Phase 5, Sonnet-Agent mit Report-Entwurf und Skill, acht lesende Aufrufe. Alle Punkte vor dem Commit
eingearbeitet:

- **Belege:** fünf Stichproben per `gh` bestätigt (Run 38532968320 `failure`/`push`, Run 38587124635 `startup_failure`/`dispatch`, #3956 Owner-Login 09:47Z, #3892 gemergt mit `Refs #3900` und #3900 OPEN, #112/#113 34 min). Korrigiert: #16 Zeile `autonomy-gates.md:296` statt „~297–305"; #10 `_review.yml:31,59`; #19–21 nennen jetzt die Transkript-Auswertung als Quelle plus Repo-Dateien; §5-Zähler bleiben Ausgabe von `retro_kpis.py` (nicht unabhängig geprüft, in §8 benannt).
- **Scores:** ganzzahlig, je an Befund verankert. OK.
- **Invariante:** 18 Soll-Zeilen = 18 Überlebende (1–4, 7, 9–15, 18–22, 24). OK nach Aufnahme von 24.
- **Frontmatter:** Platzhalter `widerlegung`/`streich_begruendung` ersetzt; Pfad kollisionsfrei (`ls-tree origin/main docs/retros/ | grep ec3416` leer).
- **0.0/5a:** fehlende Links auf 766e8c §5a nachgetragen; „Owner-Wort offen" als „Antwort beschlossen, Umsetzung wartet" präzisiert; `claim-before-cheapest-check` zugleich in `gates_caught` (6 Treffer) und §5a (ein Fall außerhalb des Musters) mit Satz aufgelöst.
- **Rechnung:** (5 + 1) / 24 = 0.25; 24 − 5 − 1 = 18. OK.
- **Vierklang §8:** „offen geblieben" trägt jetzt je einen billigsten Check.
- **Datenschutz:** Kontrollprobe vor dem Commit → 0 Treffer; der Satz in §8 nennt das Muster nicht mehr aus.
- **Form:** Spalten exakt; keine nummernlose Zeile; R1 ohne Link, weil der PR erst nach dem Commit existiert.

Nicht prüfbar (Meta): Transkript-Kennzahlen, Owner-Zitate mit Zeitstempel, `gate_wirkung.py`-Ausgabe, die Zählung 13/13 und 33/33.
