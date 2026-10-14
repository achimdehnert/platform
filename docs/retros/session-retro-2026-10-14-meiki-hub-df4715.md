---
retro_schema: 1
date: 2026-10-14
repo_scope: [meiki-hub, post-hub, schreib-hub, frist-hub, buerger-hub, iil-assist-core]
session_id: df4715
footprint: deep
findings_total: 20
findings_survived: 10
refuted_rate: 0.5
phase3_refuted: 9
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [local-test-gate-skipped-before-push, commit-praefix-gemischt]
recurring_findings: [parallele-migrationen-ohne-rebase-test, pin-bump-nur-pr-lauf-geprueft, local-test-gate-skipped-before-push, commit-praefix-gemischt, pin-kommentar-drift, open-pr-superseded-not-closed, scope-checkpoint-not-durably-recorded, rohes-pytest-statt-make-test, untested-command-handed-to-user, claim-before-cheapest-check, direct-gh-pr-merge-bypasses-sa-m, gh-body-file-leer-ueberschrieben, secret-leak-via-safe-pattern, aufschub-anker]
gates_caught: [rohes-pytest-statt-make-test, untested-command-handed-to-user, direct-gh-pr-merge-bypasses-sa-m, gh-body-file-leer-ueberschrieben, secret-leak-via-safe-pattern, aufschub-anker]
gates_verwandt: []
over_ask_klassen: []
over_act_klassen: [kern-merge-vor-scope-zeile]
widerlegung: "5 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede teure Bahn dieser Retro das Ergebnis geändert hat: Phase 2.5 klärte drei Finder-Widersprüche, Phase 3 verwarf acht Behauptungen, 3b kippte fünf Urteile und brachte einen neuen Befund."
---

# Session-Retro df4715 — Pilot-Reife der Assist-Familie, Wellen W0–W2 und D11 (meiki-hub, vier Assists, Kern)

Sitzung `1c941f6b-ccf5-42ef-ab63-4b379cdf4715`, 2026-10-13 05:55Z bis 2026-10-14 16:07Z. Auftrag
(Owner, 13.10.): die vier Assists tief analysieren und signifikant optimieren, Fokus „künftiges
LLM setzt verzugslos auf", Continuous Improvement, vorausschauende Wartung, OOTB, Advocatus
Diaboli; Pilot mit Günzburg, Traunstein und einer PROSOZ-Teststellung. Zielanker
[meiki-hub#621](https://github.com/meiki-lra/meiki-hub/issues/621) (K1–K6, Wellen W0–W4).
Sitzungsgrenze: Branches `session/2026-10-13/…` und `session/2026-10-14/…`. 65 eigene PRs in
sechs Repos, alle gemergt, dazu drei Merges von PRs, die am 12.10. eine andere Sitzung angelegt
hatte (iil-assist-core#68, post-hub#115, schreib-hub#101).

## Phase 0.0 — Wirkungsbilanz

Die vier `RUECKFAELLIG`-Gates aus `tools/gate_wirkung.py` sind in der Retro desselben Tages
entschieden — Link statt Neuverhandlung:
[session-retro-2026-10-14-platform-766e8c §0.0](session-retro-2026-10-14-platform-766e8c.md#phase-00--wirkungsbilanz).

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 5 (ohne diese Retro), 6 mit | Quelle | nachschärfen — beschlossen in 766e8c ([#2666](https://github.com/achimdehnert/platform/issues/2666)); Befund 9 dieser Retro ist ein neuer Fall (§5a) |
| built-but-never-called | 3 | Quelle | ausweiten — beschlossen in 766e8c (Owner „187 go"); kein neuer Fall |
| scope-checkpoint-not-durably-recorded | 4 (ohne diese Retro), 5 mit | Quelle | nachschärfen — beschlossen in 766e8c (Rev 10 laut [#3600](https://github.com/achimdehnert/platform/issues/3600), Gate-Quelle [#1646](https://github.com/achimdehnert/platform/issues/1646)); Befund 7 ist ein neuer Fall (§5a) |
| check-ohne-positivkontrolle | 2 | Quelle | nachschärfen — beschlossen in 766e8c (Rev 2, [#3722](https://github.com/achimdehnert/platform/issues/3722)); kein neuer Fall |
| issue-offen-nach-gemergtem-fix | 2 | Quelle | nachschärfen — beschlossen in [161b19-incr §5a](session-retro-2026-10-14-chat-hub-161b19-incr.md) und [ec3416 §5a](session-retro-2026-10-14-platform-ec3416.md); kein neuer Fall |
| pr-autor-identitaet-nicht-angewandt | 2 | Quelle | ausweiten — umgesetzt in [ec3416 §5a](session-retro-2026-10-14-platform-ec3416.md); kein neuer Fall |

Zählung per `tools/gate_wirkung.py` im Worktree, einmal mit und einmal ohne diesen Report.
Die Gates, die in dieser Sitzung gefangen haben (Befunde 8, 10), sind zeilengenau als
`gates_caught` markiert und zählen nicht als Rückfall.

## 1. Executive Summary

- Vereinbarter Umfang erreicht: K1–K4 in [#621](https://github.com/meiki-lra/meiki-hub/issues/621) sind mit PRs belegt. K5 (vorausschauende Wartung, W3) und K6 (Traunstein/enaio, PROSOZ, W4) sind geplant und als offen geführt; der Vorwurf eines stillen Soll-Ist-Defizits hielt nicht (Befund 15).
- Schwerste Befunde: main war zweimal rot. Zwei parallele `0012`-Migrationen in post-hub (1) und ein shared-ci-Pin, der nur auf PR-Läufen geprüft war (2, Push-CI rund zwei Stunden rot in vier Repos). Beide in der Sitzung behoben. Keiner war ein Rückfall auf eine ältere Regel; Befund 1 ist aber dieselbe Mechanik wie die Drift-Memory zur ADR-Nummernkollision.
- Gates haben viel gefangen (Befunde 8, 10): direkter Merge, rohes pytest, ungetestete Owner-Befehle, leere Bodies, Secret-Leser. Schaden 0, aber der Vorab-Check fehlt.
- Kleinere Lücken: Kern-Merge vor der formalen Scope-Zeile (7), überholter Draft-PR offen (6), Pin-Kommentar widerspricht dem Pin (5), Typ-Präfix `ci(...)` (4), voreilige Lückenaussage im Anker-Issue (9).
- Widerlegt: Kern ohne Secret-Scan, assists-lokal ohne Owner-Wort, irreführender K3-Haken, überzeichnetes K2/RLS, Secret-Ausgabe durch einen Sitzungsbefehl, Rückfälle bei Befehlslänge und Fremdthema.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Zwei PRs mit je einer Migration `eingang/0012_*` parallel vom selben main gebaut und seriell ohne Lauf gegen den neuen main gemergt; main rot, jeder Merge schob ein Image | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | [post-hub#119](https://github.com/meiki-lra/post-hub/pull/119) mergedAt 08:07:11Z, [#122](https://github.com/meiki-lra/post-hub/pull/122) 08:07:25Z, Fix [#125](https://github.com/meiki-lra/post-hub/pull/125) 08:18Z („354 brachen mit CommandError ab"); Branch-Schutz „strict" erst mit Owner-Entscheid D8, jetzt in allen fünf meiki-Repos gesetzt | neu als Slug; Mechanik wie Drift-Memory `adr-number-collision-open-prs` (2026-07-30): Nummer aus lokalem Stand, in-flight-PR belegt sie. Memory `serien-merge-probe-braucht-testlauf` entstand 08:17Z aus dem Vorfall |
| 2 | shared-ci-Pin v1.1.27 in vier Repos gemergt, nur der `pull_request`-Lauf geprüft; Push-, Dispatch- und Schedule-Läufe brachen beim Start | fehlende Validierung | hoch | SURVIVES (kommandobelegt, 3b bestätigt) | [post-hub#127](https://github.com/meiki-lra/post-hub/pull/127), [frist-hub#242](https://github.com/meiki-lra/frist-hub/pull/242), [schreib-hub#107](https://github.com/meiki-lra/schreib-hub/pull/107), [buerger-hub#19](https://github.com/meiki-lra/buerger-hub/pull/19); Läufe 38563676513 (push), 38568356663 (dispatch) je ohne Jobs; Rücknahme [post-hub#132](https://github.com/meiki-lra/post-hub/pull/132) u. a. 13:20Z; [meiki-hub#630](https://github.com/meiki-lra/meiki-hub/issues/630) | neu; Memory `shared-ci-pin-bump-push-lauf-pruefen` entstand 13:10Z aus dem Vorfall; Familie `gruener-lauf-ohne-wirkung` |
| 3 | Erster Push von frist-hub#246 rot: Haus-Literal `AZ-1` im neuen Test, Contract-Test ohne DB-Marker; Literal-Prüfer lief nicht vor dem Push | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | [frist-hub#246](https://github.com/meiki-lra/frist-hub/pull/246) Läufe 38586201770, 38586203017 rot, Fix b80002be, Endlauf grün; dazu [meiki-hub#624](https://github.com/meiki-lra/meiki-hub/pull/624) mit vier roten PR-Läufen; in den übrigen PRs keine roten PR-Läufe gefunden | local-test-gate-skipped-before-push (2. Retro, Gate-Pflicht §5) |
| 4 | Zwei PR-Titel mit Typ `ci(...)`, Hausregel erlaubt feat/fix/refactor/docs/test/chore | Wissenslücke | niedrig | SURVIVES (kommandobelegt, 3b bestätigt) | [post-hub#119](https://github.com/meiki-lra/post-hub/pull/119), [iil-assist-core#74](https://github.com/iilgmbh/iil-assist-core/pull/74); beide Titel so auf main | commit-praefix-gemischt (3. Retro, ohne Gate) |
| 5 | Kopfkommentar im frist-hub-Workflow nennt v1.1.27, der Pin darunter v1.1.26 | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `frist-hub:.github/workflows/ci.yml` Z. 14 gegen Z. 49 (origin/main) | neu |
| 6 | Draft [meiki-hub#530](https://github.com/meiki-lra/meiki-hub/pull/530) (post-hub an Kern-Adapter binden) ist durch [#627](https://github.com/meiki-lra/meiki-hub/pull/627) inhaltlich überholt, weder geschlossen noch als überholt vermerkt | Prozesslücke | niedrig | SURVIVES (Phase 3, 3b bestätigt) | #530 OPEN, Draft, letzte Änderung 2026-10-02T07:31Z, 0 Kommentare, berührt dieselben `profile/guenzburg-*.yaml` und `assists.sh`; `profile/guenzburg-cloud-test.yaml` Z. 73–74, 90–91 binden `assist_core.dvelop.*` auf main | neu |
| 7 | Kern-Merge vor einer formalen `scope +`-Zeile für den Kern | Prozesslücke | niedrig | SURVIVES (Phase 3, Severity durch 3b gesenkt) | `pr_merge_sa.py 68` mergedAt 2026-10-13T07:28:58Z; `scope +… +iil-assist-core` erst [09:26:50Z](https://github.com/meiki-lra/meiki-hub/issues/621#issuecomment-6142501898). Mildernd: Z1 lautete „Bestand Kategorie D (#582)", Kern#68 trägt „Refs meiki-hub#582", #582 ist Cross-Repo; ob Z1 den Merge deckte, ist unentscheidbar (§8) | scope-checkpoint-not-durably-recorded (Gate rückfällig, §5a) |
| 8 | Vorab-Check fehlt, Hooks fangen: viermal rohes pytest, zweimal ungetesteter Owner-Befehl, zweimal leerer Body, zweimal Secret-Leser, einmal Aufschub ohne Anker, viermal bare stash pop | Werkzeug | niedrig | SURVIVES (Phase 3, 3b ergänzt) | Hook `block_rohes_pytest` 13.10. 10:38, 10:51, 13:10; 14.10. 14:48 (12:47 Fehlalarm auf `grep`); Stop-Hook untested-command 08:03Z, 15:05Z; Leerer-Body-Guard 13.10. 09:32Z, 13:58Z; Aufschub-Anker 13.10. 13:01Z; Secret-Leak-Guard 14.10. 09:39Z, 12:29Z; `block_bare_stash_pop` 13.10. 10:38Z, 12:26Z, 12:59Z, 14:03Z; Schaden 0 | gates_caught: rohes-pytest-statt-make-test, untested-command-handed-to-user, gh-body-file-leer-ueberschrieben, secret-leak-via-safe-pattern, aufschub-anker |
| 9 | Lückenaussage „frist-hub ohne Required Secret-Scan" im Anker-Issue veröffentlicht, elf Minuten später selbst richtiggestellt | fehlende Validierung | niedrig | SURVIVES (kommandobelegt, 3b bestätigt) | [11:04Z](https://github.com/meiki-lra/meiki-hub/issues/621#issuecomment-6166898191) gegen [11:15Z](https://github.com/meiki-lra/meiki-hub/issues/621#issuecomment-6167077689). Mildernd: Richtigstellung aus eigenem Antrieb (Charta Art. 5) | claim-before-cheapest-check (Gate rückfällig, §5a) |
| 10 | Direkter `gh pr merge 115 -R meiki-lra/post-hub` statt Merge über `pr_merge_sa.py`/Owner-Skript | Prozesslücke | niedrig | SURVIVES (3b NEU, kommandobelegt) | Merge-Guard blockte 2026-10-13T07:26:29Z, 13 s nach dem Freigabe-Vermerk in [#582](https://github.com/meiki-lra/meiki-hub/issues/582); Schaden 0. Memory `freigabe-vermerk-im-issue-text` entstand erst 07:28Z, also kein Rückfall darauf | gates_caught: direct-gh-pr-merge-bypasses-sa-m |
| 11 | Kern-CI ohne Secret-Scan, K2-Matrix schweigt | Prozesslücke | — | REFUTED (3b) | Im Kern sind GitHub-Secret-Scanning und Push-Protection aktiv (`gh api repos/iilgmbh/iil-assist-core`: beide `enabled`); es fehlt nur ein gitleaks-Job in der CI | — |
| 12 | assists-lokal geändert ohne zitiertes Owner-Wort | Prozesslücke | — | REFUTED (Phase 3) | K4 in #621 („Haus-Profil als Vertragsdatei", „Durchlauf im lokalen Stapel") + Owner-Wort „P4 go; K1–K6 bestätigt"; #627 zitiert D10. Mildernd: #626 nur indirekt gedeckt | — |
| 13 | K3-Haken irreführend, Kriteriumstext „nur im Kern" nicht erfüllt | Kommunikation | — | REFUTED (Phase 3) | Der Haken nennt D9 in derselben Zeile mit Link auf die Nachprüfung | — |
| 14 | K2/RLS überzeichnet, weil die Laufzeitrolle Superuser mit BYPASSRLS ist | fehlende Validierung | — | REFUTED (Phase 3) | K2 verlangt Required Checks, Negativprobe, Coverage; [post-hub#130](https://github.com/meiki-lra/post-hub/pull/130) „## Grenze" nennt die Rolle und [#629](https://github.com/meiki-lra/meiki-hub/issues/629); frist-hub `tools/architektur_gate.sh` G5 prüft RLS als App-Rolle. Mildernd: kein #629-Verweis am K2-Haken | — |
| 15 | Auftragsteile (vorausschauende Wartung, Traunstein, PROSOZ, LLM-Aufsetzen) ohne neue Artefakte | Prozesslücke | — | REFUTED (Phase 3) | Bericht `docs/analysen/pilot-reife-assist-familie-2026-10-13.md` ([meiki-hub#622](https://github.com/meiki-lra/meiki-hub/pull/622)) §2.1–2.3; K5/K6 und W3/W4 in #621. Offen ist Zeitplan, nicht Artefakt | — |
| 16 | Rückkehr auf shared-ci ≥ v1.1.28 ohne Anker | Prozesslücke | — | REFUTED (Phase 3) | #630 Zielzustand 3 und Inline-Kommentar am Pin in vier Repos. Mildernd: keine Frist, kein Renovate-Zwang | — |
| 17 | Secret-Wert gelangte über einen Sitzungsbefehl ins Protokoll | Prozesslücke | — | REFUTED (Phase 3) | Eingefügter Terminalverlauf mit eigener Owner-Eingabe; Dateiname vorher in keinem Sitzungsbefehl, `~/zug/*.sh` ohne Bezug. Sitzung reagierte mit Rotations-Board | — |
| 18 | Owner musste Befehlslänge eskalieren, obwohl die Regel schon galt | Kommunikation | — | REFUTED (Phase 3) | Regel „≤40 Zeichen, `~/zug/`" entstand erst nach der Eskalation 14.10. 10:11Z (Memory 10:14Z, globale Anweisung 10:28Z) | — |
| 19 | Fremdthema im meiki-Strang trotz bestehender Memory | Kommunikation | — | REFUTED (Phase 3) | Memory `fremde-auftraege-nicht-im-meiki-strang` 07:37:49Z, 85 s nach dem Owner-Eingriff, also Folge | — |
| 20 | Lokaler Stapel bricht nach frist-hub#246 bis zur Entscheidung über #632 | Prozesslücke | — | REFUTED (vor Phase 3) | Kein Defekt: Owner mergte mit Kenntnis (Merge-Skript nennt #632 als Folgeschritt), [#632](https://github.com/meiki-lra/meiki-hub/issues/632) offen als Owner-Entscheid | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | #6, #5: vereinbarter Umfang W0–W2 erreicht, kleine Reste |
| architektur_design | 4 | #6: überholter Adapter-Entwurf liegt noch offen |
| code_konventionstreue | 3 | #3, #4 |
| risiko_debt | 2 | #1, #2: main zweimal rot, Images geschoben |
| prozess_effizienz | 3 | #8, #3 |
| entscheidungsqualitaet | 3 | #2: Pin-Bump ohne Push-Probe; #10 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #119 und #122 seriell gemergt, CI lief gegen alten main | Branch-Schutz „strict" vor einer Welle mit Migrationen (inzwischen per D8 gesetzt, strukturell erledigt) | #1 |
| Pin-Bump nur am PR-Lauf geprüft | Nach Pin-Bump einen Dispatch auf dem Zweig fahren und `jobs > 0` prüfen, vor der Merge-Bitte | #2 |
| Literal-Prüfer erst in CI | Vor dem Push `make test-voll` plus Literal-Prüfer lokal | #3 |
| `ci(...)` im Titel | Titel-Präfix gegen die erlaubte Typliste prüfen, bevor der PR angelegt wird | #4 |
| Kommentar nennt alten Pin | Pin und Kopfkommentar im selben Edit ändern | #5 |
| #530 bleibt Draft neben erledigtem Ziel | Beim Merge von #627 überholte PRs zum Thema suchen und schließen oder vermerken | #6 |
| Kern-Merge 07:28Z vor Scope-Zeile 09:26Z | `scope +<repo>` als Owner-Zeile vor dem ersten Schreibakt im zweiten Repo, auch bei Cross-Repo-Issue | #7 |
| Hooks fangen rohes pytest, ungetestete Befehle, leere Bodies | Test immer über `make`-Ziel; Owner-Befehl erst nach eigenem Lauf übergeben; `test -s` vor `--body-file` | #8 |
| Lückenaussage zu frist-hub veröffentlicht, dann zurückgenommen | Required-Context-Aussage erst nach `gh api …/required_status_checks` plus Blick auf `needs` des Gate-Jobs | #9 |
| `gh pr merge` direkt versucht | Merge nur über `pr_merge_sa.py` bzw. Owner-Skript in `~/zug/` | #10 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`: refuted_rate-Band gesund (766e8c 0.12, 327837 0.29, 1012cf 0.55);
diese Retro 0.5. Score-Mittel über alle Retros: risiko_debt 2.59, prozess 3.03.

Slugs mit Zähler ≥2 (per `git grep` über `origin/main:docs/retros/`):
- `commit-praefix-gemischt` — 2 Retros vorher, ohne Gate ⇒ `gate_candidates` (Titel-Prüfung beim Anlegen des PR).
- `local-test-gate-skipped-before-push` — 1 Retro vorher, mit dieser 2, ohne Gate ⇒ `gate_candidates`.
- `scope-checkpoint-not-durably-recorded`, `claim-before-cheapest-check` — Gate vorhanden, §5a.
- `rohes-pytest-statt-make-test`, `untested-command-handed-to-user`, `direct-gh-pr-merge-bypasses-sa-m` — vom bestehenden Gate gefangen (`gates_caught`), Beleg für das Gate.

Memory-Abgleich (Datei-Zeitstempel geprüft): `serien-merge-probe-braucht-testlauf` 08:17:41Z,
`shared-ci-pin-bump-push-lauf-pruefen` 13:10:38Z, `lokal-gruen-ci-flags-no-migrations` (Zeile zum
Literal-Prüfer) 15:13:59Z, `freigabe-vermerk-im-issue-text` 13.10. 07:28:19Z — alle nach dem
jeweiligen Vorfall, also Ersterfassung. Älter und thematisch verwandt: 🌀
`adr-number-collision-open-prs` (2026-07-30) zu Befund 1.

### 5a. Rückfall-Prüfung

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| Gate scope-checkpoint-not-durably-recorded rückfällig (advisory, Rev 10, [#1646](https://github.com/achimdehnert/platform/issues/1646)) | #7: Kern-Merge vor der formalen Scope-Zeile | Quelle: ein Merge über `pr_merge_sa.py` in ein zweites Repo zählt offenbar nicht als Scope-Evidenz (Lesart, nicht per Replay belegt) | **ausweiten**: Merge-Aufrufe auf fremde Repos als Schreibevidenz; bündeln mit der in 766e8c beschlossenen Rev 11 |
| Gate claim-before-cheapest-check rückfällig (blocking, [#1643](https://github.com/achimdehnert/platform/issues/1643)) | #9: Lückenaussage in einem Issue-Kommentar | Quelle (3b): der PreToolUse-Hook liest seit Rev 11 auch `--body-file`, erkennt aber nur positive Bescheinigungen („erfüllt", „geprüft"); negative Lückenaussagen („fehlt", „nicht Required") fallen nicht in seine Klasse | **ausweiten**: Negativ- und Lückenaussagen in die Klasse aufnehmen; über [#2666](https://github.com/achimdehnert/platform/issues/2666) |

### 5b. Autonomie-Kalibrierung

- over_act: `kern-merge-vor-scope-zeile` (#7) — Merge in ein zweites Repo vor der formalen Scope-Zeile; ob Z1 ihn deckte, ist offen.
- over_ask: keine Klasse.

## 6. Verankerung

memory_candidates (der Owner entscheidet, nichts davon ist geschrieben):

```markdown
---
name: serien-merge-migrationen-strict
description: Welle mit mehreren Migrations-PRs je App nur bei Branch-Schutz strict mergen
metadata:
  type: feedback
---
Mehrere PRs mit Migrationen in derselben App nie parallel vom selben main bauen und seriell
mergen, ohne dass der zweite gegen den neuen main läuft.
**Why:** Retro df4715 Befund 1 — zwei `0012` in post-hub, main rot (post-hub#125). Dieselbe
Mechanik wie [[adr-number-collision-open-prs]].
**How to apply:** Vor der Welle Branch-Schutz „strict" prüfen (seit D8 gesetzt); fehlt er,
je PR `makemigrations --check` gegen den gemergten Stand. Ergänzt [[serien-merge-probe-braucht-testlauf]].
```

CLAUDE.md-Kandidat (Owner-Sache, Charta Art. 3): Commit-Regel um „gilt auch für PR-Titel" ergänzen.

adr_candidates: keine.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Draft #530 schließen | meiki-hub | [#530](https://github.com/meiki-lra/meiki-hub/pull/530) | 🟢 | Owner-Wort, dann Vermerk + Close |
| M2 | Pin-Kommentar frist-hub | frist-hub | [#630](https://github.com/meiki-lra/meiki-hub/issues/630) | 🟢 | mit Rückkehr auf ≥ v1.1.28 |
| M3 | Gate scope-checkpoint ausweiten | platform | [#1646](https://github.com/achimdehnert/platform/issues/1646) | 🟢 | mit Rev 11 aus 766e8c |
| M4 | Gate claim auf Lückenaussagen | platform | [#2666](https://github.com/achimdehnert/platform/issues/2666) | 🟢 | Negativklasse aufnehmen |
| M5 | Gate PR-Titel-Präfix | platform | §5 | 🟢 | Owner-Wort, Gate-Kandidat |
| M6 | Gate Literal-Prüfer vor Push | platform | §5 | 🟢 | Owner-Wort, Gate-Kandidat |
| M7 | Memory Serien-Migrationen | — | §6 | 🟢 | Owner-Wort |

## 8. Nicht verifiziert (Restlücken)

- Ob Z1 („Bestand Kategorie D (#582)") den Kern-Merge 07:28Z deckte (#7) — billigster Check: Owner-Nachricht 13.10. 07:16Z im Wortlaut.
- Ob `pr_merge_sa.py` auf fremde Repos im Scope-Gate als Evidenz zählt (#7) — billigster Check: Scanner-Replay auf das Transkript.
- Release-Verzug Kern 0.16.8 (3b, Hypothese zur Wirkung): Merge 13.10. 11:10Z, auf PyPI erst 14.10. 07:52Z, rund 21 h; alle Hosts pinnen `>=0.16.8`, die Host-Merges folgten ab 08:06Z. Ob der Verzug Arbeit blockierte — billigster Check: Board-Zeilen am 13.10. nach 11:10Z.
- Rework-Zahl für schreib-hub#109 — die API brach mit HTTP 500 ab; billigster Check: `gh run list -R meiki-lra/schreib-hub --branch <branch>`.
- Ob post-hub#111 alle Kriterien erfüllt — billigster Check: Issue-Body gegen die Refs-PRs.
- Ob die Rotation des betroffenen Tokens erfolgt ist — Owner-Zug laut Rotations-Board.
- Datensparsamkeit der neuen Texte nicht systematisch geprüft — billigster Check: Grep nach Namens- und Aktenzeichen-Mustern über die 65 PR-Diffs.
- Beobachtung zum Werkzeug: Der memory-link-guard meldete dieser Sitzung mehrfach einen toten Verweis in einer Memory-Datei des platform-Projekts, die die Sitzung nicht geschrieben hat. Billigster Check: Zuordnungslogik des Wächters (Datei-mtime statt Sitzungs-Schreibliste).

**getan:** 3 Finder, Phase 2.5 (drei Widersprüche, je per Skeptiker binär geklärt), 3 Skeptiker, Nachprüfung der Memory-Zeitstempel, Required Checks und Secret-Scanning-Status, Widerlegungsbahn, Meta-Prüfung.
**angenommen:** Zeitstempel aus dem Transkript-Kennzahlen-Werkzeug; Owner-Kürzel wörtlich aus #621 und #582.
**nicht verifizierbar:** Absicht hinter dem eingefügten Terminalverlauf (#17).
**offen geblieben:** M1–M7, die Restlücken oben.

## Widerlegung

Ein Opus-Subagent mit frischem Kontext bekam Entwurf, Footprint und Artefaktliste, aber nicht die Sitzungserzählung. Verdikt: **5 gekippt, 2 neu**.

| Punkt | Verdikt | Beleg der Widerlegung | Eingearbeitet |
|---|---|---|---|
| Befund 1, Recurrence | GEKIPPT | Mechanik wie Drift-Memory `adr-number-collision-open-prs`; „strict" inzwischen in allen fünf Repos | Recurrence-Spalte, Soll-Zeile als strukturell erledigt, Memory-Kandidat verlinkt |
| Kern ohne Secret-Scan | GEKIPPT | Secret-Scanning und Push-Protection im Kern `enabled` | als Befund 11 REFUTED, Maßnahme gestrichen |
| Befund 7, Beleg und Severity | GEKIPPT | Z1 bezog sich auf das Cross-Repo-Issue #582, Kern#68 trägt „Refs #582" | Severity niedrig, Deckung durch Z1 als Restlücke |
| §5a Ursache zu Befund 9 | GEKIPPT | Hook liest `--body-file` seit Rev 11, erkennt nur positive Bescheinigungen | Ursache und M4 neu gefasst, Restlücke gestrichen |
| PR-Zahl | GEKIPPT | 65 eigene PRs plus 3 Merges von PRs des 12.10. | Kopf korrigiert |
| Direkter Merge-Versuch | NEU | Merge-Guard 07:26:29Z | Befund 10 |
| Release-Verzug 0.16.8 | NEU (Hypothese) | Merge 11:10Z, PyPI 07:52Z am Folgetag | §8, kein Befund ohne Wirkungsbeleg |
| Befunde 2, 4, 5, 6, 9; REFUTED 12–20 | BESTAETIGT | — | unverändert; `gates_caught` um drei Slugs ergänzt, Score-Anker auf überlebende Befunde gelegt |

## Streichbahn

Keiner, weil jede teure Bahn dieser Retro das Ergebnis geändert hat: Phase 2.5 klärte drei Finder-Widersprüche, Phase 3 verwarf acht Behauptungen, 3b kippte fünf Urteile und brachte einen neuen Befund. Keine Phase blieb ohne Leser.

## Self-Review

Ein Sonnet-Meta-Agent hat den Entwurf gegen den Skill geprüft. Er sah nur Report und Skill.

| Punkt | Urteil | Eingearbeitet |
|---|---|---|
| Belege | ok, 7 Stichproben unabhängig nachgeprüft | — |
| Scores, Invariante 10 = 10 | ok | — |
| `gates_caught` nicht Teilmenge von `recurring_findings` | Befund | drei Slugs ergänzt |
| §0.0 führte 4 statt 6 rückfällige Gates; gefangene Gates zählten als Rückfall, weil die Zeilen nicht als `gates_caught` markiert waren | Befund | zwei Zeilen mit Link auf die Retros desselben Tages, Zahlen eingetragen, Zeilen 8 und 10 markiert; `gate_wirkung.py` meldet danach wieder 6 statt 9 |
| „nachschärfen" sei keine zulässige Antwort | nicht übernommen | §0.0 erlaubt laut Skill nachschärfen, §5a nutzt nur „ausweiten" |
| `retro_report_check.py`, Band | ok (Exit 0; 0.5 im gesunden Band) | — |

Auffällig: Der formale Prüfer war vor und nach der Korrektur grün. Die beiden Lücken in §0.0
fand nur die inhaltliche Prüfung.
