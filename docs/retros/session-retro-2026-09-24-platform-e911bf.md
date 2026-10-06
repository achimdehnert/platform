---
retro_schema: 1
date: 2026-09-24
repo_scope: [platform, cad-hub, mcp-hub, news-hub, risk-hub, iil-adrfw, ttz-hub]
session_id: e911bf
footprint: deep
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [push-to-merged-branch-silently-lost, infra-detail-in-public-repo]
recurring_findings: [push-to-merged-branch-silently-lost, issue-offen-nach-gemergtem-fix, handover-stale-vor-merge, inline-heredoc-quoting-rework, scope-checkpoint-not-durably-recorded, claim-before-cheapest-check]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: [neues-repo-nach-checkpoint-ohne-spiegelung]
widerlegung: "0 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: Jede Phase trug heute einen eigenen Befund bei — Finder 10, Skeptiker 3 Widerlegungen, Widerlegungsbahn den einzigen Befund zum öffentlichen Repo; keine lief ohne Wirkung.
---

# Session-Retro 2026-09-24 — platform (Sitzung e911bf49)

Sitzung von 04:51 bis ~16:45 UTC, erst Fable 5.1, ab ~14:40 Opus 5.5. Auftrag
[#3475](https://github.com/achimdehnert/platform/issues/3475) (Items 9–18 des Session-Start-Boards
autonom, Backup-Strategie nach netcup-Kündigung), danach auf Owner-Zuruf Hetzner-Inference-Pilot
([#3500](https://github.com/achimdehnert/platform/issues/3500)), Klickdummy Bauantrag
(cad-hub#81–#84, ADR-036 Rev 2–6), Screenshot-PDF, PDF-Auslieferung im Link-Dienst (#3540).
Sieben Repos, vier Prod-/Host-Eingriffe (Zertifikat, news-hub-Deploy + Env, Offsite-Umstellung
prod und prod-b, Link-Dienst). Footprint `deep` (≥3 Repos, Prod), keine Reduktion.

**Agenten:** 3 Finder (sonnet) · 2 Skeptiker (sonnet, gebündelt je Dimension, nur
Bewertungsbefunde und Finder-Widersprüche) · 1 Widerlegungsbahn (opus) · 1 Meta (sonnet) = 7.
Kosten nach Budget-Richtwert ~55k je Skeptiker; laut Nutzungsmeldung der Agent-Läufe je Finder/Skeptiker 108k–131k Token, Widerlegungsbahn 87k (Finder und
Skeptiker haben das 15-MB-Transkript gezielt durchsucht).

## 1. Executive Summary

- Das Kernziel stand am Abend: beide Prod-Hosts sichern nach 17 Nächten ohne Offsite wieder in
  die vorhandene Storage Box, der Melder zeigt 0 ungedeckte Volumes. Offen ist nur K5
  (Restore-Drill), sauber verankert.
- Der teuerste Fehler war ein **bekannter**: Push auf einen bereits gemergten PR-Branch, heute
  zweimal (#3488→#3514, cad-hub#81→#82) — obwohl die Lehre vom Vortag geladen und mittags
  selbst ergänzt war. Zweites Vorkommen des Gate-Kandidaten ⇒ **GATE-PFLICHT**.
- Vier weitere Befunde sind Rückfälle **bestehender** Gates: Issue offen trotz Fix (#3469),
  Handover veraltet nach späterer Arbeit (#3531), Heredoc-Patch auf eine Repo-Datei,
  Scope-Checkpoint beim 7. Repo nicht gespiegelt.
- Zwei Prod-Fehler ohne Schaden, aber mit Lernwert: Vhost-Sicherung im Include-Ordner (nginx
  Reload scheiterte), `compose up` ohne Image-Tag (news-hub-DB ~4 min nicht verfügbar).
- Die Widerlegungsbahn fand eine Dimension, die kein Finder sah: Adresse und Unterkonten des
  Offsite-Ziels stehen jetzt im öffentlichen Repo (#14, kein Secret, Owner-Entscheid #3542).
- Drei Bewertungsbefunde hielten der Falsifikation nicht stand (ADR-289 Rev 2 war aus dem
  Repo-Stand nicht vermeidbar; Restore-Lücke offen verankert; PR-Dublette war ein Wettlauf).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Folge-Commits auf bereits gemergte PR-Branches gepusht, erreichten `main` nicht | fehlende Validierung | hoch | SURVIVES | platform#3488 mergedAt 07:23:54Z vs. Commit `99e658a7` 11:38 → Cherry-pick #3514; cad-hub#81 gemergt → v0.3-Commit `40cfeaee` nicht in `main` (`merge-base --is-ancestor` exit 1) → #82 | 2. und 3. Vorkommen (`push-to-merged-branch-silently-lost`, Kandidat aus Retro 4ed2e5) ⇒ GATE-PFLICHT |
| 2 | Issue #3469 offen, obwohl beide Fix-PRs gemergt und die eigene Schließbedingung erfüllt | Prozesslücke | mittel | SURVIVES | `gh issue view 3469` → OPEN; #3473 merged 06:55Z, #3489 merged 07:07Z; Issue-Kommentar 06:28Z „schließt, sobald beide gemergt sind" | Gate `issue-offen-nach-gemergtem-fix` rückfällig |
| 3 | K4 im Abnahme-Kommentar als ✅ verbucht, obwohl der selbst geforderte Nachweis (nächster Sitzungsstart-Lauf 0.7.17) nicht gelaufen war | verfrühte Festlegung | mittel | SURVIVES | #3475-Kommentar 12:43Z „K4 nach dem nächsten Sitzungsstart-Lauf" vs. 13:07Z „K4 ✅ … folgt beim nächsten Start" | neu |
| 4 | Handover-Fragment #3531 deckt die letzten ~3 h nicht ab (Klickdummy v0.2–v0.6, PDF, #3539/#3540); kein zweiter `/session-ende` | Prozesslücke | hoch | SURVIVES | #3531 mergedAt 13:31Z, nur `docs/handover.d/2026-09-24T13-01-28Z-e911bf49.md`; #3540 mergedAt 16:08Z; keine Handover-PR danach | Gate `handover-stale-vor-merge` rückfällig |
| 5 | Beim 7. Repo (cad-hub, ab 13:44Z) kein erneuter Scope-Checkpoint, obwohl der eigene Checkpoint „weitere Repos" unter neues Wort stellte | Kommunikation | niedrig | SURVIVES | #3475-Kommentar 07:49Z „Nicht freigegeben … ohne neues Wort: … weitere Repos"; cad-hub#81 created 13:44:41Z; letzter „Scope-Checkpoint" im Transkript 13:04Z | Gate `scope-checkpoint-not-durably-recorded` (×32) — sieht „neues Repo nach Checkpoint" nicht |
| 6 | ADR-289 Rev 2 ignorierte die in ADR-241 festgelegte Storage Box | verfrühte Festlegung | mittel | REFUTED | ADR-241 sagte „nicht bestellen, bevor ADR-289 entschieden"; Box-ID erstmals im Repo ab 11:38Z; Existenz kam per Owner-Zuruf; Rev 2 schrieb Owner-Entscheid vom 2026-09-08 fort | — |
| 7 | Vhost-Sicherung auf prod im `sites-enabled`-Ordner abgelegt → `nginx -t` rot, Reload fehlgeschlagen | fehlende Validierung | mittel | SURVIVES | risk-hub#770-Kommentar „Eigener Fehler"; Memory `feedback_sicherungskopie_nie_ins_include_verzeichnis.md` (originSessionId e911bf49) | neu (Memory angelegt) |
| 8 | `docker compose up -d` auf prod ohne `IMAGE_TAG` → `news_hub_db` neu erzeugt, ~4 min nicht verfügbar | Wissenslücke | mittel | SURVIVES | #3500-Kommentar 08:15Z „Eigener Fehler, sofort behoben"; Memory `feedback_compose_up_ohne_image_tag_reisst_datenbank_mit.md` | neu (Memory angelegt) |
| 9 | Offsite-Umstellung ohne Restore-Nachweis als erledigt behandelt | fehlende Validierung | mittel | REFUTED | #3475 13:07Z „K5 verschoben … Issue bleibt offen"; ADR-289 §5 E6/E7 „⬜ Ausstehend"; Finder-Detail „5 Prod-Hosts" falsch, hosts.yaml führt 2 | — |
| 10 | `pr_merge_sa.py` stufte iil-adrfw#82 als W3 (Publish auf main) ein, obwohl `publish.yml` nur `workflow_dispatch` hat; Merge blieb beim Owner | Werkzeug | niedrig | SURVIVES | Ablehnung 06:54Z „Merge Without Review"; Issue #3493; iil-adrfw#82 `mergedBy: achimdehnert`, `reviews: []` | neu (Issue #3493) |
| 11 | PR #3465 ohne Vorab-Prüfung auf Parallelsitzungen angelegt → Dublette #3466 | Prozesslücke | mittel | REFUTED | `repo-session.sh start` 04:53Z listete 14 offene PRs; #3465 04:55:11Z, #3466 04:55:17Z aus Parallelsitzung — Wettlauf, #3466 existierte vorher nicht | — |
| 12 | Evidenz-Hook feuerte dreimal in 35 min; jedes Mal war die Aussage im Turn unbelegt und wurde erst danach belegt | fehlende Validierung | niedrig | SURVIVES | Kennzahlen 12:34:02Z, 12:35:23Z, 13:09:52Z; Transkript-Zeilen 2109→2115/2126, →2156, 2568→2574/2582 | Gate `claim-before-cheapest-check` hat gefangen |
| 13 | Repo-Datei per Bash-Heredoc geändert (`python3 - <<'PY'` mit `s.replace` auf cad-hub `shell.html`), entgegen Hausregel | Prozesslücke | niedrig | SURVIVES | Transkript-Zeile 3506 (Pfad `…/worktrees/cad-hub/…/klickdummy/bauantrag-vorpruefung/shell.html`, Ergebnis `ok`); Finder 2 hatte „kein Heredoc-Patch" gemeldet → als Skeptiker-Task aufgelöst | Gate `inline-heredoc-quoting-rework` (Kalibrierfenster) |
| 14 | Hostname, Unterkonto-Namen, Box-ID und Projekt-ID des Offsite-Ziels in vier Dateien des **öffentlichen** Repos veröffentlicht; Skript und Runbook derselben Sitzung nutzten Platzhalter | fehlende Validierung | mittel | SURVIVES (3b NEU) | `git grep -l <unterkonto-host> origin/main` → ADR-289, `infra/hosts.yaml`, `infra/secrets-inventory.yaml`, Fragment e911bf49; vor #3530 0 Treffer; `gh repo view` → PUBLIC; kein Secret betroffen | neu; verwandt mit Drift-Memory „platform PUBLIC" → [#3542](https://github.com/achimdehnert/platform/issues/3542) |

## 3. Scorecard

| Dimension | Score | Verankert an |
|---|---|---|
| zielerreichung | 4 | K1–K3 erfüllt, K4 vorzeitig verbucht (#3), K5 offen verankert (#9 REFUTED) |
| architektur_design | 4 | Storage-Box-Entscheidung tragfähig und aus Repo-Stand nicht früher möglich (#6 REFUTED); Melder je Host korrigiert |
| code_konventionstreue | 3 | Heredoc-Patch (#13), Push auf gemergten Branch (#1) |
| risiko_debt | 3 | Prod-DB ~4 min down (#8), nginx-Reload gescheitert (#7), Infra-Details öffentlich (#14); kein Datenverlust, kein Secret |
| prozess_effizienz | 3 | Handover veraltet (#4), Issue nicht geschlossen (#2), zweifacher Cherry-pick-Rework (#1) |
| entscheidungsqualitaet | 4 | W3-Fehlklassifikation nicht umgangen, sondern als #3493 verankert (#10); drei Bewertungsvorwürfe widerlegt |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Folge-Commit in einen langlebigen Worktree gepusht, dessen PR der Owner zwischenzeitlich gemergt hatte | **Vor** jedem `git push` auf einen PR-Branch `gh pr view <n> --json state`; bei `MERGED` neuer Branch + Cherry-pick — als PreToolUse-Hook, nicht als Memory | #1 |
| #3469 blieb offen, weil beide PRs nur `Refs` trugen und nach dem zweiten Merge niemand schloss | Der PR, der die Schließbedingung vollendet, trägt `Closes #N`; `/session-ende` E.10 prüft alle von eigenen PRs referenzierten Issues | #2 |
| K4 als ✅ verbucht mit „folgt beim nächsten Start" im selben Satz | Kriterium, dessen Nachweis in der Zukunft liegt, als 🟡 „Nachweis ausstehend: <Lauf>" führen, nie ✅ | #3 |
| Nach `/session-ende` 3 h weitergearbeitet, Fragment blieb beim Mittagsstand | Neue substanzielle Arbeit nach einem Sitzungsende ⇒ eigenes Nachtrags-Fragment im letzten PR des Blocks; Stop-Hook meldet Commits nach dem letzten Fragment | #4 |
| cad-hub als 7. Repo begonnen, ohne den Checkpoint aus #3475 zu erneuern | Beim ersten Edit in einem Repo außerhalb der gespiegelten Liste: ein Satz Scope-Spiegelung + Kommentar im Auftrag | #5 |
| Vhost-Kopie in `sites-enabled/` angelegt | Sicherungen immer nach `/root/<dienst>-backups/`, danach `nginx -t` vor Reload | #7 |
| `compose up -d` auf prod ohne Image-Tag | Env-Änderung per Deploy-Dispatch; Handgriff nur mit `IMAGE_TAG=<laufender Tag> --pull never -p <projekt>` | #8 |
| Merge-Werkzeug stufte dispatch-only Publish als W3 ein | `pr_merge_sa.py` wertet den `on:`-Block aus (#3493) | #10 |
| Aussage „läuft/steht" vor dem belegenden Tool-Lauf geschrieben | Erst Log/`gh`-Ausgabe lesen, dann den Satz schreiben — auch in Zwischenständen | #12 |
| Textersetzung in `shell.html` per `python3 - <<'PY'` | Jede Repo-Datei per Edit-Tool, auch bei mehreren Stellen (mehrere Edit-Aufrufe) | #13 |
| Echte Box-Adresse und Unterkonten in ADR, `hosts.yaml` und Inventar geschrieben, obwohl das Skript Platzhalter nutzte | Vor jedem Commit nach platform: Diff auf Hostnamen, Konto-Namen und Console-IDs prüfen, die vor der Sitzung 0× im Repo standen; echte Werte nur in `~/.secrets` bzw. privaten Repos | #14 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand 2026-09-24, nach `git fetch`, einschließlich dieses Reports):

| Slug | Zähler | Status |
|---|---|---|
| `claim-before-cheapest-check` | ×93 | GATE-PFLICHT, Gate existiert, hat heute dreimal gefangen (#12) |
| `scope-checkpoint-not-durably-recorded` | ×33 | GATE-PFLICHT, Gate existiert (advisory) |
| `handover-stale-vor-merge` | ×24 | GATE-PFLICHT, Gate existiert, `gate_wirkung.py`: RUECKFAELLIG |
| `inline-heredoc-quoting-rework` | ×9 | GATE-PFLICHT, Gate existiert (Kalibrierfenster bis 2026-10-21) |
| `issue-offen-nach-gemergtem-fix` | ×5 | GATE-PFLICHT, Gate existiert |
| `push-to-merged-branch-silently-lost` | ×1 im Zähler; in Retro 4ed2e5 als `gate_candidates` geführt (Befund #1 dort), heute zweimal | **GATE-PFLICHT** — kein Gate unter `docs/governance/gates/gates/` |
| `infra-detail-in-public-repo` | neu | Kandidat, Owner-Entscheid in #3542 |

Memory-Abgleich (per `grep` in `~/.claude/projects/-home-devuser-github-platform/memory/`):
`feedback_push_auf_gemergten_branch_geht_verloren.md` existiert (drift, 2026-09-23) und wurde
heute zweimal ergänzt — Beleg, dass Memory allein nicht wirkt.

### 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` (Phase 0.0, erster Schritt) meldete 6 Gates RUECKFAELLIG:
`check-ohne-positivkontrolle`, `handover-stale-vor-merge`, `melder-ohne-leser`,
`secret-leak-via-safe-pattern`, `stale-local-clone-as-ground-truth`,
`untested-tool-module-green-gate`. Entscheidung je Gate (Umsetzung als eigener PR durch
`gate_verankerung_check.py --neu`, **in dieser Retro nicht ausgeführt**, siehe §7/§8):

| Gate | Rückfälle | Ursache | Konsequenz |
|---|---|---|---|
| `handover-stale-vor-merge` | heute +1 (#4) | Quelle: E.3 prüft nur beim `/session-ende`; Arbeit danach fällt durch | **umbauen**: Stop-Hook meldet Commits/PRs nach dem letzten eigenen Fragment |
| `issue-offen-nach-gemergtem-fix` | heute +1 (#2) | Quelle: E.10 sah #3475, nicht #3469 (nur `Refs` im PR) | **ausweiten**: E.10 prüft alle in eigenen PR-Bodies referenzierten Issues |
| `scope-checkpoint-not-durably-recorded` | heute +1 (#5) | Quelle: Hook zählt Prod-Schritte nach dem Checkpoint, nicht neue Repos | **ausweiten**: neues Repo nach Checkpoint = Checkpoint überholt |
| `inline-heredoc-quoting-rework` | heute +1 (#13) | Kalibrierfenster sammelt | keine neue Entscheidung — Vorkommen zählt ins Fenster (Frist 2026-10-21) |
| `check-ohne-positivkontrolle`, `melder-ohne-leser`, `secret-leak-via-safe-pattern`, `stale-local-clone-as-ground-truth`, `untested-tool-module-green-gate` | 0 heute | Rückfälle aus Retros bis 2026-09-23 | **Entscheidung offen** — kein Vorkommen in dieser Sitzung; gehören in die Retro, die sie gefunden hat bzw. an den Owner (§7) |

### 5b. Autonomie-Kalibrierung

- `over_act`: **`neues-repo-nach-checkpoint-ohne-spiegelung`** (#5) — Arbeit in cad-hub war per
  Owner-Auftrag gedeckt, die Scope-Spiegelung fehlte. Erstes Vorkommen dieser engen Klasse.
- `over_ask`: keins belegt. Die Rückfragen an den Owner betrafen Console-Schritte (API ohne
  Zugang), Code-Owner-Reviews (Ruleset) und Prod-Worte — alle gate-pflichtig.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates** — keine neuen; die drei Lehren sind heute als Memory angelegt bzw.
ergänzt. Vorschlag: `feedback_push_auf_gemergten_branch_geht_verloren.md` bekommt einen
Verweis auf das Gate, sobald es gebaut ist, und wird dann `rule_class: A`.

**adr_candidates** — keine. Gate-Vorschlag (kopierfertig, `docs/governance/gates/gates/push-to-merged-branch-silently-lost.json`):

```json
{
  "slug": "push-to-merged-branch-silently-lost",
  "mode": "blocking",
  "module": "tools/claude-hooks/block_push_to_merged_branch.py",
  "trigger": "PreToolUse(Bash) auf `git push` in einem Worktree unter ~/.repo-session/worktrees/",
  "check": "gh pr list --head <branch> --state all --json state → MERGED ⇒ deny mit Hinweis 'neuer Branch + git cherry-pick'",
  "fail_mode": "fail-open bei fehlendem gh/Netz (Push ist reversibel), Journalzeile",
  "drill": "tools/claude-hooks/tests/test_block_push_to_merged_branch.py",
  "positivkontrolle": {"ref": "platform#3488→#3514, cad-hub#81→#82", "datum": "2026-09-24"},
  "built": null
}
```

## 7. Maßnahmen

- **[R1]** 🔵 Gate `push-to-merged-branch-silently-lost` als PreToolUse-Hook bauen · platform · Umsetzung, Brief an Sonnet — https://github.com/achimdehnert/platform/issues/2234
- **[R2]** ✅ #3469 geschlossen (Fix belegt, 2026-09-24) · platform — https://github.com/achimdehnert/platform/issues/3469
- **[R9]** 🟢 Offsite-Ziel-Details: Platzhalter oder akzeptieren · platform · du — https://github.com/achimdehnert/platform/issues/3542
- **[R3]** 🔵 Nachtrags-Fragment für den Nachmittag (Klickdummy, PDF, #3540) · platform · ich — https://github.com/achimdehnert/platform/pull/3531
- **[R4]** 🔵 K4 in #3475 auf „Nachweis ausstehend" korrigieren · platform · ich — https://github.com/achimdehnert/platform/issues/3475
- **[R5]** 🔵 Gate-Revisionen `handover-stale-vor-merge` (umbauen), `issue-offen-nach-gemergtem-fix` und `scope-checkpoint-not-durably-recorded` (ausweiten) · platform · eigener PR — https://github.com/achimdehnert/platform/issues/2234
- **[R6]** 🟢 Entscheidung zu den fünf übrigen rückfälligen Gates (aus Vor-Retros) · platform · du — https://github.com/achimdehnert/platform/issues/2234
- **[R7]** 🔵 `pr_merge_sa.py` W-Einstufung aus `on:`-Block · platform · Umsetzung — https://github.com/achimdehnert/platform/issues/3493
- **[R8]** 🟢 Streichbahn-Kandidat entscheiden (siehe unten) · platform · du — https://github.com/achimdehnert/platform/issues/2234

## 8. Nicht verifiziert (Restlücken)

- **Getan:** Wirkungsbilanz zuerst, Collect nach `git fetch` aus dem Ref, 3 Finder parallel,
  2 Skeptiker parallel (nur Bewertungsbefunde + Finder-Widerspruch), Längsschnitt, Widerlegungsbahn, Meta-Prüfung.
- **Angenommen:** Die drei Hook-Meldungen (#12) sind über die Transkript-Zeilen richtig
  zugeordnet; die cad-hub-Commit-Reihenfolge (#1, zweites Vorkommen) stützt sich auf
  `merge-base` und die Memory-Chronik, nicht auf einen eigenen `gh`-Zeitstempelvergleich.
- **Nicht verifizierbar:** Die Aussage des 0e-Prüfers beim Sitzungsende („k1.md wortgleich mit
  dem Issue-Kommentar") — mein Gegencheck lief gegen eine Rate-Limit-Fehlerantwort der API und
  ist wertlos. Billigster Check: den K1-Kommentar in #3475 per `gh api repos/achimdehnert/platform/issues/3475/comments --jq '.[].body'` bei freiem Limit holen und gegen die k1-Kopie `diff`en.
- **Nicht verifizierbar in dieser Retro (3b-Kandidaten ohne Lauf):** `.env.prod`-Handänderung auf news-hub gegen den
  nächsten Deploy; Konsumenten der ersetzten Hetzner-Token-Datei (mindestens
  mcp-hub `scripts/start-deployment-mcp.sh` liest sie, ob das Lese-Schreib-Token dort mehr
  Rechte gibt als nötig, ist offen); fehlendes Review der Subagent-PRs. Billigster Check fürs
  Token: Scope in der Hetzner-Console gegen den Bedarf des Deployment-MCP halten.
- **Offen geblieben:** Umsetzung der Gate-Entscheidungen aus 5a (R1, R5), Entscheidung zu fünf
  rückfälligen Gates ohne Vorkommen heute (R6), K5-Restore-Drill (#3475), Nachtrags-Fragment (R3),
  Owner-Entscheid zu #3542 (R9).

## Widerlegung

Ein Opus-Subagent mit frischem Kontext, nur Report-Entwurf und Artefaktliste, `git fetch` vor
jedem Lesen. Ergebnis `0 gekippt, 1 neu`.

| Befund | Verdikt | Beleg |
|---|---|---|
| #1 | BESTAETIGT | `merge-base --is-ancestor 40cfeaee origin/main` exit 1 (cad-hub); `99e658a7` nur auf dem Session-Branch |
| #2 | BESTAETIGT | `gh issue view 3469` → OPEN, `closedAt: null` (inzwischen geschlossen, R2) |
| #3 | BESTAETIGT | #3475-Kommentar wörtlich „K4 ✅ … folgt beim nächsten Start" |
| #4 | BESTAETIGT | `git log origin/main --since=13:30Z -- docs/handover.d` leer |
| #5, #7, #8, #12, #13 | BESTAETIGT | Belegkette stimmig, kein Gegenbeleg — nicht eigenständig nachgezogen |
| #10 | BESTAETIGT | `publish.yml` in iil-adrfw: `on:` nur `workflow_dispatch` |
| #6 (REFUTED) | BESTAETIGT | ADR-241 Z. 39–46 „nie bestellt … nicht bestellen"; Box-ID vor der Sitzung 0× im Repo |
| #9 (REFUTED) | BESTAETIGT | #3475 OPEN, K5 als „verschoben" geführt |
| #11 (REFUTED) | BESTAETIGT | #3465 04:55:11Z vs. #3466 04:55:17Z, anderer Branch — Wettlauf |
| — | **NEU #14** | Offsite-Ziel-Details im öffentlichen Repo, eigene Prüfung per `git grep -l` bestätigt 4 Dateien |

## Streichbahn

Kein Streichkandidat. Die Widerlegungsbahn lieferte den einzigen Befund zur Veröffentlichungs-
Dimension, die Skeptiker verwarfen drei Bewertungsbefunde, die Finder trugen die übrigen zehn.
Die Skeptiker-Kosten lagen mit 108k–131k je Agent über dem Richtwert von ~55k, weil sie das
15-MB-Transkript selbst durchsuchten; eine engere Führung (Zeilenbereiche mitgeben) ist ein
Kostenhebel, kein Streichgrund.
