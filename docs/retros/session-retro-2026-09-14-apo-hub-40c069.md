---
retro_schema: 1
date: 2026-09-14
repo_scope: [apo-hub, platform]
session_id: 40c069
footprint: deep
findings_total: 22
findings_survived: 17
refuted_rate: 0.18
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [parallel-subagents-shared-scratch-state, date-cutoff-utc-statt-localdate, same-file-serial-prs, deferred-item-no-tracking-issue]
recurring_findings: [date-cutoff-utc-statt-localdate, date-cutoff-utc-statt-localdate, temporaere-ausnahme-nach-parallelem-merge-nicht-entfernt, parallel-subagents-shared-scratch-state, parallel-subagents-shared-scratch-state, same-file-serial-prs, pruefwerkzeug-wertet-zaehlwort-als-treffer, inline-heredoc-quoting-rework, check-ohne-positivkontrolle, claim-before-cheapest-check, blocked-sleep-retry, gate-test-race-container-init, klassen-severity-abweichung-vom-katalog, deferred-item-no-tracking-issue, sammel-zaehler-widerspricht-tabelle, gate-test-einzelfall-statt-klassen-gate, permission-vorschlag-ohne-macht-kennzeichnung]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "5 gekippt, 5 neu"
streichkandidaten: [ux-review-falsifikator-spruch]
---

# Session-Retro 2026-09-14 · apo-hub (+ platform) · 40c069

## 1. Executive Summary
- Ziel erreicht: /ux-review über drei Rollen ergab 15 Befund-Issues (#98–#112), alle über 8 Fix-PRs plus #83 geschlossen und nach Prod deployt; zusätzlich ein 12/12 still fehlschlagendes Pre-Deploy-Backup gefunden und kanonisch gefixt (apo-hub#122, platform#3161, Prod-Beleg 1,1 MB).
- Zwei Code-Restmängel dieser Session auf `main`: Datums-Cutoff in UTC statt Ortszeit an zwei Stellen (#1, #21), veraltete Test-Ausnahme (#3, niedrig — ein anderer Test deckt die Route).
- Die Gate-Tests prüfen überwiegend den Einzelfall statt des im Issue vorgeschlagenen Klassen-Gates; dadurch bleibt `Search` ohne Bedienweg unentdeckt (#20). Bewusst Ausgelassenes aus PR #119 und die Nicht-verifiziert-Liste stehen nur im geschlossenen Sammel-Issue (#18).
- Die Parallelisierung von 8 Fix-Subagenten erzeugte drei Kollisionsarten: geteilter Stash (#4), geteilte Scratchpad-Datei (#5), Import-Konflikte (#6). Kein Datenverlust.
- 5 von 22 Befunden widerlegt (4 in Phase 3, 1 in Phase 3b: die N+1-Abfragen sind Altlast). Keine over_ask/over_act.

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `dashboard()` vergleicht `DateField`s mit `timezone.now().date()` (UTC) bei `TIME_ZONE=Europe/Berlin`; dieselbe Datei nutzt in `bookings_list` `timezone.localdate()` — zwischen 00:00 und 02:00 Ortszeit zählen am Vortag beendete Einträge noch als offen | fehlende Validierung | niedrig (3b: Fenster max. 2 h) | SURVIVES | `origin/main:apps/web/views.py:133` vs `:279`; `apps/requests/models.py:75,131`; `config/settings/base.py:98,100`; blame 01a5a61 (PR #118) | date-cutoff-utc-statt-localdate ×2 (mit #21) |
| 2 | N+1-Abfragen auf `requests_list`/`bookings_list` durch `.profile.display_name` | fehlende Validierung | — | REFUTED (3b) | Altlast: `git show 01a5a61^:templates/web/requests_list.html:9` rendert seit 8f521df `{{ r.substitute }}`, `SubstituteProfile.__str__` lädt `profile` je Zeile; `bookings_list` hatte N+1 schon vorher | — |
| 3 | `tests/test_ux_verfuegbarkeit.py` führt `Pharmacy` weiter als Ausnahme („#98, paralleler PR"), obwohl PR #119 `pharmacy_edit` geliefert hat | Prozesslücke | niedrig (3b: `tests/test_ux_apotheke.py:58` fängt ein Entfernen der Route über `reverse`) | SURVIVES | `origin/main:tests/test_ux_verfuegbarkeit.py:12-17`; PR #119 diff | temporaere-ausnahme-nach-parallelem-merge-nicht-entfernt ×1 |
| 4 | Ein paralleler Fix-Subagent (PR #119) poppte beim Rot/Grün-Messen einen fremden Stash aus dem geteilten `.git`; keiner der 8 Briefs warnte vor `git stash`; selbst zurückgesetzt | Prozesslücke | mittel | SURVIVES | Agent-Report 07:23:04 (Transkript); `git stash list` unverändert 2 Einträge; 8 Brief-Texte ohne „stash" | parallel-subagents-shared-scratch-state ×2 (mit #5) |
| 5 | PR-Body-Dateien zweier paralleler Subagenten kollidierten im gemeinsamen Scratchpad; falscher Body auf PR #117, per `gh pr edit` korrigiert; Briefs nannten nur `--body-file <datei>` | Prozesslücke | mittel | SURVIVES | Agent-Report 07:21:20 (Transkript); `gh pr view 117 --json body` aktuell korrekt | parallel-subagents-shared-scratch-state |
| 6 | Drei Merge-Konflikte zwischen parallelen PRs (Importblock `apps/web/views.py` #115/#116, `apps/web/forms.py` #119/#120); Briefs scopten Funktionen, nicht Importzeilen | Prozesslücke | mittel | SURVIVES | Transkript 07:27:46, 07:28:06, 07:50:35; Nachzieh-Commits 5766665c, 506dafe4 | same-file-serial-prs ×14 |
| 7 | `ux_falsifikator.py` sprach für #110 (reproduzierter Datenverlust) „widerlegt": Regel 2 wertet „Absenz + Gegenprobe meldet Treffer"; das Gegenprobe-Feld begann mit „8 DateInput…" statt mit der Absenz-Zahl (G13/E18 „Zahl zuerst") — erneutes Eintreten von Risiko R7 aus KONZ-platform-051 (erstmals 2026-08-30) | Werkzeug | mittel | SURVIVES | `origin/main:tools/ux_falsifikator.py:77-78`; Issue #110 Body (R7-Vermerk); Transkript 07:12:04 | pruefwerkzeug-wertet-zaehlwort-als-treffer ×1 |
| 8 | Zwei Body-/Messskripte scheiterten mit `SyntaxError: unterminated string literal` (deutsche „…" in Inline-Python-Heredocs); danach Umstieg auf Write-Datei | Werkzeug | mittel | SURVIVES | Transkript 07:08:12, 07:33:50 | inline-heredoc-quoting-rework ×1 |
| 9 | Reseed scheiterte 3× mit `KeyError`; der Vorab-Check 07:30:18 (`grep -oE "environ\[['\"][A-Z_]+…"`) kannte keine Ziffern und fand `UXR_SUB2_PW`/`UXR_OWNER2_PW` nicht — blinder Check ohne Positivkontrolle | fehlende Validierung | niedrig | SURVIVES (Ursache per 3b korrigiert) | Transkript 07:29:47, 07:30:18, 07:30:46, 07:31:04 | check-ohne-positivkontrolle ×1 |
| 10 | Der Evidenz-Stop-Hook fing 2× eine im Turn unbelegte Behauptung; Reaktion jeweils sofort mit billigstem Check | Kommunikation | niedrig | SURVIVES | Transkript 07:18:29→07:18:34, 10:21:17→10:21:23 | claim-before-cheapest-check (gates_caught) |
| 11 | Merge-Retry für PR #116 als `sleep 30; …`, von der Harness geblockt | Werkzeug | niedrig | SURVIVES | Transkript 07:51:01, 07:51:04 | blocked-sleep-retry ×1 |
| 12 | Gate-Test für den Backup-Fix hatte eine Postgres-Init-Race; erste Rot-Messung nicht belastbar; gefixt, lief danach in CI | fehlende Validierung | niedrig | SURVIVES | Transkript 09:22:34; CI-Run 34828562528 (5278 passed, Test nicht unter SKIPPED) | gate-test-race-container-init ×1 |
| 13 | Issue #111 führt Klasse `formular-verliert-eingabe` mit Severity `optimierung` (Katalog I6: `fehler`); der eigene Body sagt „Eingaben bleiben erhalten" — die Klasse passt nicht, Titel ohne Klassen-Präfix | Wissenslücke | niedrig | SURVIVES | Issue #111 Body/Titel; `origin/main:.windsurf/workflows/ux-review.md` I6 | klassen-severity-abweichung-vom-katalog ×1 |
| 14 | Alle 5 `optimierung`-Befunde gefixt trotz Skill-Step-8-„Diff-Bremse" | Prozesslücke | — | REFUTED | Harte Gates verlangen nur Referenz (A3/G15/G22), alle 5 Issues tragen eine; Step 8 unter `## Referenzpfad (nicht bindend)`; Nutzerauftrag 06:44:53 | — |
| 15 | `AGENT_HANDOVER.md` nach 10 Merges nicht aktualisiert | Prozesslücke | — | REFUTED | Pflege in `/session-ende` 0b, noch nicht gelaufen; Gate `handover-stale-vor-merge` Rev 3 misst am Sitzungsende, PR-Schwelle 12 Commits | — |
| 16 | Remote-Branch `…/deploy-backup-postgres-user` blieb stehen | Prozesslücke | — | REFUTED | `git ls-remote` exakt auf den Branchnamen in apo-hub und platform: 0 (Muster `session/2026-09-14/*` trifft in platform nur eine Fremdsitzung, PR #3166) | — |
| 17 | `renovate.json` aus #83 unbegründet entfernt | Prozesslücke | — | REFUTED | Begründung im PR-#83-Kommentar; `renovate.json` nie auf `origin/main` | — |
| 18 | PR #119 nennt „Bewusst weggelassen (Sammel-Issue #113): weitere Pharmacy-Felder …, Löschen einer Apotheke"; #113 enthält davon nichts und ist geschlossen; auch die Nicht-verifiziert-Liste (DEBUG=False-Fehlerseiten, POST-Aktionen, Django-Admin) steht nur im geschlossenen Issue — kein offenes Tracking | Prozesslücke | mittel | NEU (3b), SURVIVES | `gh pr view 119` Body Z.43-44; `gh issue list -R achimdehnert/apo-hub --state open` → nur #11–#13, #50 | deferred-item-no-tracking-issue ×41 |
| 19 | Zähler im Sammel-Issue #113 („befund 28 · ok 10") widersprechen der eigenen Stationstabelle (30 befund / 8 ok) | Kommunikation | niedrig | NEU (3b), SURVIVES | `gh issue view 113` Stationszeilen gezählt | sammel-zaehler-widerspricht-tabelle ×1 |
| 20 | Gate-Tests setzen den Klassen-Gate-Vorschlag ihrer Issues nicht um: #99 verlangt „jedes nutzerangelegte Modell mit Listen-View", der Test führt ein festes Dict mit 2 Modellen; `Search` (angelegt über SearchForm, gelistet in Dashboard und /bedarfe/) hat weder Bearbeiten- noch Löschen-Route und wird nicht erfasst; dashboard/bewerten/abo/stammdaten/apotheke-Tests prüfen nur den Einzelfall | fehlende Validierung | mittel | NEU (3b), SURVIVES | Issue #99 „Klassen-Gate-Vorschlag"; `origin/main:tests/test_ux_verfuegbarkeit.py:11-17`; `apps/web/urls.py` ohne Search-Edit/Delete | gate-test-einzelfall-statt-klassen-gate ×1 |
| 21 | Zweite Stelle derselben Klasse wie #1: PR #115 führt `ends_at__gte=date.today()` in `apps/web/views.py:552` ein (Container-Zeit; dass der Container UTC läuft, ist **Hypothese**) | fehlende Validierung | niedrig | NEU (3b), SURVIVES | `git show 0a6385f -- apps/web/views.py`; `git grep -i "TZ="` → 1 Treffer (Docstring `USE_TZ=True` in `etl_apocenna.py:50`, kein TZ-Env) | date-cutoff-utc-statt-localdate (s. #1) |
| 22 | Die erste Permission-Empfehlung (08:56:35) war nicht als „erweitert meine Macht" gekennzeichnet (Charta Art. 3) und nannte ein breites Glob, das Schreiben erlaubt; Kennzeichnung und Einengung erst 09:39:38, nach der Nutzerfreigabe 09:10:32 | Kommunikation | niedrig | NEU (3b), SURVIVES | Transkript 08:56:35, 09:10:32, 09:39:38 | permission-vorschlag-ohne-macht-kennzeichnung ×1 |

## 3. Scorecard
| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | Ziel „keine Finding offen" erreicht und deployt; Restmängel #1/#21, #18 |
| architektur_design | 4 | Fixes korrekt gescoped (IDOR/CSRF ohne Befund, 3b); Gate-Tests auf Einzelfall-Ebene #20 |
| code_konventionstreue | 4 | #1 folgt dem Muster der eigenen Datei nicht, #21 derselbe Fehler an zweiter Stelle |
| risiko_debt | 3 | Ausgelassenes ohne offenes Tracking #18; `Search` ohne Bedienweg unerkannt #20 |
| prozess_effizienz | 3 | Kollisionen #4–#6 plus Rework #8, #9, #11 |
| entscheidungsqualitaet | 4 | #7 korrekt übersteuert, Backup-Eingrenzung belegt, 0 over_act; aber #12 Rot-Messung zunächst nicht belastbar, #22 Macht-Kennzeichnung verspätet |

## 4. Soll-Ablauf
| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Cutoff mit `timezone.now().date()` (views.py:133) | Datumsvergleich gegen `DateField` immer mit `timezone.localdate()`; Gate-Test mit gefrorener Zeit **00:30 Europe/Berlin** (= 22:30Z Vortag) | #1 |
| Temporäre Ausnahme „#98, paralleler PR" blieb nach Merge von #119 | Nach dem letzten Merge einer Parallelwelle `grep -rn 'paralleler PR' tests/` und jede Ausnahme gegen `main` auflösen | #3 |
| Brief erlaubte Rot/Grün per `git stash` im geteilten `.git` | Brief-Vorlage für parallele Subagenten: kein `git stash`, Rot messen per `git show HEAD:<datei>` | #4 |
| Briefs nannten generisch `--body-file <datei>` im gemeinsamen Scratchpad | Brief-Vorlage: jeder Subagent schreibt nur unter `$SP/<agent-slug>/` | #5 |
| 8 Briefs scopten Funktionen, Importblöcke kollidierten | Vor Parallelstart Datei-Overlap der Briefs prüfen; gemeinsame Dateien: Importzeilen einem Brief zuordnen oder seriell mergen | #6 |
| Gegenprobe-Feld begann mit „8 DateInput…" statt der Absenz-Zahl; Regel 2 wertete Treffer | Gegenprobe bei Absenz immer mit der Absenz-Zahl beginnen („0 von 8 DateInput mit format"); Regel 2 nur bei Nullzählung als Widerlegung | #7 |
| Bodies per Inline-Python-Heredoc mit „…" | Texte mit typografischen Anführungszeichen per Write-Datei | #8 |
| Vorab-Regex ohne Ziffern fand die fehlenden Variablen nicht | Jeder Vorab-Check erst gegen einen bekannten Treffer laufen lassen (Positivkontrolle), dann gegen die Frage | #9 |
| Board-Aussage mit Zahl ohne Beleg im selben Turn | Pre-Send-Selbstcheck: jede Zahl/jeder Artefakt-Claim braucht einen Tool-Lauf im selben Turn | #10 |
| Retry als `sleep 30; cmd` | Warten auf Zustand mit `until <check>; do sleep 5; done` bzw. Monitor | #11 |
| Gate-Test wartete nur auf `pg_isready` | Postgres-Readiness: Log „init process complete" UND `pg_isready`; Rot-Messung erst nach stabilem Grün als belastbar werten | #12 |
| Klasse mit abweichender Severity und unpassendem Symptom geführt | Klasse und Severity aus der Katalog-Tabelle übernehmen; passt keine Klasse, neue Klasse per G24 vorschlagen | #13 |
| Ausgelassenes nur im PR-Text bzw. im geschlossenen Sammel-Issue | Vor dem Schließen des Sammel-Issues je Auslassung und je Nicht-verifiziert-Punkt ein offenes Issue anlegen und verlinken | #18 |
| Zähler von Hand geschrieben | Zähler aus der Stationstabelle per Skript ableiten, nicht tippen | #19 |
| Gate-Test mit festem Dict statt Enumeration | Gate-Test enumeriert die Klasse (alle ModelForms/Listen-Views per Introspektion) und führt Ausnahmen mit Grund | #20 |
| Zweiter Cutoff mit `date.today()` in derselben Session | Nach Fix einer Klasse `git grep -nE 'date\.today\(\)|now\(\)\.date\(\)' apps/` und alle Stellen mitziehen | #21 |
| Permission-Empfehlung ohne Macht-Kennzeichnung, breites Glob zuerst | Jede Permission-Empfehlung sofort als „erweitert meine Macht" kennzeichnen und die engste Variante zuerst nennen | #22 |

## 5. Längsschnitt
`python3 tools/retro_kpis.py` (platform, 2026-09-14): 43 Slugs ≥2 mit GATE-PFLICHT. Für diese Retro:
- `date-cutoff-utc-statt-localdate` neu, ×2 in dieser Retro (#1, #21) → **GATE-PFLICHT** (Test/Lint gegen `timezone.now().date()` und `date.today()` in `apps/`).
- `parallel-subagents-shared-scratch-state` neu, ×2 (#4, #5) → **GATE-PFLICHT** (Brief-Vorlage/Delegations-Hook).
- `same-file-serial-prs` ×13 → ×14 (#6); Gate `serielle-prs-auf-derselben-datei` → §5a.
- `deferred-item-no-tracking-issue` ×40 → ×41 (#18); gedeckt durch Gate `aufschub-anker` (blocking) → §5a.
- `claim-before-cheapest-check` ×82: #10 vom bestehenden Hook gefangen → `gates_caught`.
- `pruefwerkzeug-wertet-zaehlwort-als-treffer` (#7) bewusst nicht auf `gate-matches-spelling-not-substance` gemappt: `grep -i falsifikator` in `gate-registry.json` → 0; der Scope des Gates umfasst das Werkzeug nicht (3b bestätigt).
- `temporaere-ausnahme-nach-parallelem-merge-nicht-entfernt` (#3): Nähe zu `workaround-without-tracking-anchor` (Anker #98 vorhanden, inzwischen geschlossen); eigener Slug, weil der Anker existiert (3b bestätigt).

### 5a. Rückfall-Prüfung
`gate_wirkung.py` (Phase 0.0): kein Gate `RUECKFAELLIG`. Kein Rückfall durch diese Retro gebucht:
| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| `serielle-prs-auf-derselben-datei` | 0 gebucht (#6 außerhalb der Reichweite) | Reichweite: Melder `serielle-prs-advisory.yml` liegt nur in `platform/.github/workflows`; apo-hub hat 5 Workflows ohne `session_abgleich` (3b); Transkript 0 Treffer `session_abgleich` | Kandidat **ausweiten** (Aufruf in shared-ci bzw. Ziel-Repos) — Owner-Entscheid, Registry-Edit über `gate_verankerung_check.py --neu` |
| `aufschub-anker` | 0 gebucht (#18 außerhalb der Reichweite) | Reichweite: Gate läuft nur in platform (3b), apo-hub-Workflows ohne Aufruf | Kandidat **ausweiten** — Owner-Entscheid |

### 5b. Autonomie-Kalibrierung
over_ask: 0 (einzige Frage im Transkript vom Nutzer; Merge-Freigabe vor jedem Prod-Schritt). over_act: 0 (0 `gh pr merge`/Push nach main vor Freigabe 07:37:10; 3 Classifier-Blocks ohne Umgehungsversuch; Settings-Regel vom Nutzer eingetragen; platform#3161 mit Code-Owner-Freigabe, ohne Admin-Bypass). Keine Klassen-Slugs.

## 6. Verankerung (Vorschläge, nicht geschrieben)
memory_candidates:
```markdown
---
name: parallel-subagents-isolation
description: Parallele Fix-Subagenten teilen .git-Stash und Scratchpad — Brief muss Stash verbieten, je Agent ein Unterverzeichnis vorgeben und Datei-Overlap vorab prüfen
metadata:
  type: feedback
---
Bei ≥2 parallelen Umsetzungs-Subagenten im selben Repo: kein `git stash` (Stash-Liste über alle Worktrees geteilt), Rot-Messung per `git show HEAD:<datei>`; Schreiben nur unter `$SCRATCHPAD/<agent-slug>/`; Datei-Overlap der Briefs vorab prüfen, Importblöcke einem Brief zuordnen.
**Why:** Retro 2026-09-14 apo-hub 40c069 (#4 fremder Stash gepoppt, #5 PR-Body überschrieben, #6 drei Import-Konflikte).
**How to apply:** Beim Schreiben jedes Parallel-Briefs die drei Zeilen übernehmen.
```
```markdown
---
name: django-date-cutoff-localdate
description: Datumsvergleiche gegen DateField in apo-hub mit timezone.localdate(), nie timezone.now().date() oder date.today(); Test auf 00:30 Ortszeit
metadata:
  type: feedback
---
`USE_TZ=True`, `TIME_ZONE=Europe/Berlin`: `timezone.now()` ist UTC, `date.today()` Container-Zeit. Zwischen 00:00 und 02:00 Ortszeit liegt das UTC-Datum einen Tag zurück.
**Why:** Retro 2026-09-14 40c069 #1/#21 — zwei neue Cutoffs in derselben Session falsch; ein vorgeschlagener Test auf 23:30 wäre mit dem Bug grün gewesen.
**How to apply:** Gefrorene Zeit 00:30 Europe/Berlin als Rot-Fall.
```
adr_candidates: keine.

## 7. Maßnahmen
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Cutoffs auf localdate | apo-hub | [#123](https://github.com/achimdehnert/apo-hub/issues/123) | 🔵 offen | ich: Fix-PR, du: Merge |
| M2 | Gate-Tests Klassen-Ebene | apo-hub | [#124](https://github.com/achimdehnert/apo-hub/issues/124) | 🔵 offen | ich: PR, du: Merge |
| M3 | Ausgelassenes nachholen | apo-hub | [#125](https://github.com/achimdehnert/apo-hub/issues/125) | 🟢 offen | du: priorisieren |
| M4 | Parallel-Brief-Isolation | platform | [#3167](https://github.com/achimdehnert/platform/issues/3167) | 🟢 Gate-Pflicht | du: Vorlage/Hook freigeben |
| M5 | Falsifikator Regel 2 | platform | [#3168](https://github.com/achimdehnert/platform/issues/3168) | 🔵 offen | ich: Drill + Fix |
| M6 | Gate-Reichweite Ziel-Repos | platform | [#3169](https://github.com/achimdehnert/platform/issues/3169) | 🟢 Entscheid | du: ausweiten ja/nein |
| M7 | Sammel-Zähler korrigiert | apo-hub | [#113 Kommentar](https://github.com/achimdehnert/apo-hub/issues/113#issuecomment-5663139670) | ✅ done | — |
| M8 | Memory-Kandidaten §6 | lokal | [Report §6](file:///home/devuser/github/platform/docs/retros/session-retro-2026-09-14-apo-hub-40c069.md) | 🟢 Vorschlag | du: übernehmen ja/nein |
| M9 | Streichkandidat Falsifikator-Spruch | platform | [KONZ-051 K9](https://github.com/achimdehnert/platform/blob/main/docs/konzepte/KONZ-platform-051-ux-review-agent.md) | 🟢 Frist 30.09. | du: im K9-Entscheid |

Ableitung: M1 aus Soll #1/#21; M2 aus #3/#20; M3 aus #18; M4 aus #4/#5/#6; M5 aus #7; M6 aus §5a; M7 aus #19; M8 aus #8/#9/#10/#11/#12/#13/#22 (Prozess-Lehren ohne eigene Artefakte, als Memory-/Skill-Hinweis); M9 aus der Streichbahn.

## 8. Nicht verifiziert (Restlücken)
- Container-Zeitzone von `apo_hub_web` (#21 Hypothese UTC) — billigster Check: `docker exec apo_hub_web date +%Z` auf prod-b.
- Ob `aufschub-anker` eine Ausnahme mit geschlossenem Anker (#3) melden würde — billigster Check: `tools/deferral_anchor_check.py` gegen `tests/test_ux_verfuegbarkeit.py`.
- G26 „Zweiter Fall derselben Klasse → Gate-Test zuerst" bei den `daten-invariante`-Issues (#100, #101, #103, #104, #112) nicht geprüft — billigster Check: Commit-Reihenfolge Test vor Fix in PR #118 und #120.
- #8, #10, #11 von 3b nicht unabhängig nachgeprüft (Phase-3-Skeptiker C bestätigte sie) — billigster Check: Transkript an 07:08:12, 07:33:50, 07:51:01.
- MEMORY.md-Abgleich auf die neuen Slugs nicht durchgeführt — billigster Check: `grep -iE 'stash|scratchpad|parallel|localdate' ~/.claude/projects/-home-devuser-github-apo-hub/memory/MEMORY.md`.
- Collector-Phase: §7 der Sammlung meldete 0 Tool-Fehler/0 Agent-Aufrufe (Parser auf falschem JSON-Pfad) und ordnete einen fremden Container (`uxr-kette-pg`, Up 4 days) der Session zu; beides im Haupt-Kontext mechanisch neu gezählt (§7b/§8b) — Regel-1-Restlücke, kein Urteil.

## Widerlegung
Phase 3b (Opus, frischer Kontext) — `5 gekippt, 5 neu`:
| Ziel | Verdikt | Ergebnis | Beleg |
|---|---|---|---|
| #1 Fehlerfenster/Testvorschlag (22–24 Uhr, Test 23:30) | GEKIPPT | widerlegt | 23:30+02:00 = 21:30Z, gleiches Datum; richtig 00:00–02:00, Test 00:30 |
| #2 N+1 als Session-Mangel | GEKIPPT | widerlegt | `git show 01a5a61^:templates/web/requests_list.html:9`, `SubstituteProfile.__str__` lud `profile` schon vorher |
| #3 „Entfernen der Route wird nicht gefangen" | GEKIPPT | widerlegt (Severity → niedrig) | `tests/test_ux_apotheke.py:58` `reverse("pharmacy_edit")` |
| §5a Rückfall `serielle-prs` „zu spät" | GEKIPPT | widerlegt | Melder nur in `platform/.github/workflows`; apo-hub ohne `session_abgleich` |
| Scorecard-Anker #2/#3 | GEKIPPT | widerlegt | Anker auf #18/#20 getauscht |
| #4–#7, #9, #12, #13 | BESTAETIGT | hält | #9 Ursache präzisiert (Regex ohne Ziffern) |
| #14–#17 (REFUTED) | BESTAETIGT | hält | #16 Beleg präzisiert |
| #18–#22 | NEU | — | s. Befund-Tabelle |
Nicht nachgeprüft durch 3b: #8, #10, #11 (→ §8).

## Streichbahn
Kandidat `ux-review-falsifikator-spruch` — Belegart **kein Effekt**: /ux-review G19/E16 legt fest, dass der Spruch kein Issue unterdrückt; in dieser Session wurden alle 15 Befund-Issues unabhängig vom Spruch angelegt (#98–#112), 4 der 15 Sprüche waren falsch oder unklar (#102, #107, #108 „unklar", #110 „widerlegt"), 5 uneinig. Entscheidung gehört zum Kill-Gate K9 von KONZ-platform-051 (Frist 2026-09-30).

## Self-Review
Meta-Agent (Phase 5, Sonnet, nur Report gegen Skill): `refuted_rate` stand im Entwurf auf 0,23, weil die 3b-Widerlegung von #2 eingerechnet war; schemakonform (`(phase3_refuted+pre_refuted)/findings_total`) sind es 4/22 = 0,18 — korrigiert, die 3b-Widerlegung bleibt im Abschnitt Widerlegung. 0,18 liegt knapp unter der 0,2-Marke; `retro_kpis.py` führt frühere Werte von 0,10/0,12/0,14 bei „Band gesund". §7 war im Entwurf noch offen und ist jetzt aus dem Soll-Ablauf abgeleitet. Der Beleg zu #21 (`git grep -i "TZ="`) nannte 0 Treffer, tatsächlich 1 irrelevanter Docstring — korrigiert. Stichprobe von 8 Befund-Belegen, 2 Längsschnitt-Claims und 2 Transkript-Zeitstempeln: sonst exakt. Die Korrektur der Sammel-Zähler (#19) wurde vor dem Posten mit einer Summenprüfung nachgezählt (38 Zeilen: 30 befund, 8 ok); ein erster awk-Zähler lieferte nur 29 Zeilen und wurde verworfen.
