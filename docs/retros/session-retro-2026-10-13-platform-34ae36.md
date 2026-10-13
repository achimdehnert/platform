---
retro_schema: 1
date: 2026-10-13
repo_scope: [platform, risk-hub, dev-hub, iil-pet-portal, pg-hub, ausschreibungs-hub]
session_id: 34ae36
footprint: full
footprint_reduction_reason: "Trigger deep (6 Repos, ein Prod-Deploy), nach Trigger-Konflikt-Regel von deep auf full reduziert, weil (a) der Prod-Deploy ausschreibungs-hub per Owner-Wort freigegeben war (wortgleicher Befehl des Owners, vom Agenten ausgefuehrt, Befund 17), (b) alle Änderungen rollback-fähig sind (Doku, Tests, Schema-URLs, ein Werkzeug), keine Migration, (c) ≤10 überlebende Befunde."
findings_total: 18
findings_survived: 9
refuted_rate: 0.5
phase3_refuted: 8
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [generated-artifact-drift-not-prechecked]
recurring_findings: [partial-fix-not-generalized-to-sibling-artifacts, deferred-item-no-tracking-issue, check-ohne-positivkontrolle]
gates_caught: [scope-checkpoint-not-durably-recorded]
gates_verwandt: ["check-ohne-positivkontrolle: der Fristen-Regex des Melders 0.7.27 entstand am 2026-09-16, einen Tag vor dem Bau des Gates (2026-09-17); die Sitzung hat ihn nicht gebaut, nur als Zielmass fuer V2 benutzt", "partial-fix-not-generalized-to-sibling-artifacts: das Gate geschwister-stellen-nicht-mitgezogen prueft Geschwister in derselben Datei; Befund 8 ist eine Kopie in einem anderen Repo (iil-pet-portal), ausserhalb des Zuschnitts"]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "2 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jede Phase dieser Retro messbar gewirkt hat: Phase 2.5 fand Befund 9, die Skeptiker kippten 6, die Widerlegungsbahn kippte 2 und fand 2 neue (darunter den Attributionsfehler beim Prod-Deploy), der Meta-Agent fand 6 Formfehler."
---

# Session-Retro 34ae36 — Positivliste-Journal, Schleuse, Sichtbarkeits-Abbau, Konzept-Fristen (platform)

Sitzung `34ae368e-106d-4638-b533-9da2c775c580`, 2026-10-13, ab 05:55 UTC. Owner-Aufträge per Kürzel:
„D1 go S1 go V1 go B1 go" (07:14Z) und „V2 go ; der rest ist done" (07:46Z). Sitzungsgrenze:
Branch-Präfix `session/2026-10-13/achim-dehnert/` mit den Slugs `positivliste-journal`,
`schleuse-regeln`, `sichtbarkeit-schema-url`, `v2-fristen-pilot`, `klickdummy-1412`, `retro-34ae36`.
Nicht aus dieser Sitzung (parallele Sitzungen): platform#3884, #3888, #3889, #3891, #3893, Renovate-PRs.

**Artefakte:** [platform#3885](https://github.com/achimdehnert/platform/pull/3885) (D1, Owner-Merge),
[platform#3886](https://github.com/achimdehnert/platform/pull/3886) (S1, SA-Merge),
[dev-hub#506](https://github.com/achimdehnert/dev-hub/pull/506) (V1, SA-Merge),
[iil-pet-portal#56](https://github.com/iilgmbh/iil-pet-portal/pull/56) und
[pg-hub#15](https://github.com/bahn-sqf/pg-hub/pull/15) (V1, Owner-Merge),
[risk-hub#833](https://github.com/iilgmbh/risk-hub/pull/833) (V1, offen),
[risk-hub#834](https://github.com/iilgmbh/risk-hub/pull/834) (Pin-Bump, offen),
[platform#3895](https://github.com/achimdehnert/platform/pull/3895) (V2, SA-Merge); Issues
[#3405](https://github.com/achimdehnert/platform/issues/3405) (geschlossen),
[#3234](https://github.com/achimdehnert/platform/issues/3234), [#3804](https://github.com/achimdehnert/platform/issues/3804),
[#3843](https://github.com/achimdehnert/platform/issues/3843), [#3896](https://github.com/achimdehnert/platform/issues/3896) (neu);
Prod-Deploy ausschreibungs-hub Run 38282431677 (Owner-Wort, vom Agenten ausgeführt);
Schleuse: 18 Einträge reversibel archiviert.

## Phase 0.0 — Wirkungsbilanz

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 5 | Quelle | nachschärfen — bereits beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666), Retro 1012cf §0); in dieser Retro kein überlebender Fall (Kandidat #6 von der Widerlegungsbahn gekippt) |
| built-but-never-called | 3 | Quelle | ausweiten — bereits beschlossen (Owner „187 go"); in dieser Sitzung kein neuer Fall |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | nachschärfen — bereits beschlossen (Rev 10, [#3600](https://github.com/achimdehnert/platform/issues/3600)); in dieser Sitzung hat das Gate gefangen (Befund #1), Checkpoint steht durabel in #3234 |
| check-ohne-positivkontrolle | 2 | Quelle | nachschärfen — Rev 2 (2026-10-05, [#3722](https://github.com/achimdehnert/platform/issues/3722) G3) hat schon ausgeweitet; die Rückfälle stammen aus fremden Retros. Befund #9 dieser Retro zählt nicht mit (gates_verwandt: Regex vor dem Gate gebaut), zeigt aber eine Lücke: das Gate prüft neue Checks, keinen Altbestand. Vorschlag: Altbestands-Melder einmal mit Positivfall drillen (Maßnahme M1) |

## 1. Executive Summary

- **Geliefert:** D1 (Positivliste-Abweisungen im Merge-Journal) und S1 (Schleuse: 42 → 25 unentschieden, 0 fällig) sind gemergt und belegt; V2 ist erledigt — sieben Fristen hat eine parallele Sitzung nach Owner-Wort „B3a ruhen" auf `stale` gesetzt (#3893), die beiden Pilot-Fristen erneuert #3895 mit Messbeleg.
- **Nicht erreicht:** V1 (#3234) — der Melder zeigt nach der Arbeit „Aufrufer 1 · Raw 1 (Laufzeit 1) · Kopien 2", Ziel 0/0/1/0; der letzte Laufzeit-Bezug hängt an risk-hub#833, das zweimal an Generator-Drift rot lief (Befund #4).
- **Falsch-grün:** „Fristen 0" ist nicht wahr — der Melder-Regex überspringt gequotete `review_by`-Werte; vier aktive Konzepte (015, 017, 021, 032) haben eine abgelaufene, ungezählte Frist (Befund #9). Auch #3895 spricht von „den beiden Pilot-Fristen", obwohl 015 ebenfalls pilot ist.
- **Attribution:** Die Prod-Freigabe ausschreibungs-hub hat der Agent ausgeführt (der `!`-Befehl des Owners kam nur als Text an); Artefakte nannten sie eine Owner-Handlung (Befund #17, korrigiert). „B1 go" hatte kein durables Artefakt (Befund #18, nachgeholt).
- **Falsifikation:** 6 von 16 Erstbefunden in Phase 3 gekippt, 1 vorab; die Widerlegungsbahn kippte 2 weitere (#2, #6) und fand 2 neue.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Scope-Checkpoint beim 3. Repo verspätet: PRs im 3. und 4. Repo eröffnet (iil-pet-portal#56 07:35:11Z, dev-hub#506 07:35:38Z), #3886 gemergt (07:37:22Z), erst danach der Kommentar (07:38:53Z) | Prozesslücke | mittel | SURVIVES (kommandobelegt) | [#3234 Kommentar 6140723462](https://github.com/achimdehnert/platform/issues/3234#issuecomment-6140723462) nennt sich selbst „verspätet" | gates_caught: scope-checkpoint-not-durably-recorded |
| 2 | Freigabe-Zeile für „S1 go" erst um 07:36:54Z in #3405, kurz vor dem Merge von #3886 | Prozesslücke | mittel | REFUTED (3b) | PR-Text #3886 (angelegt 07:29:19Z) beginnt mit „Auftrag: Owner-Wort „S1 go", 2026-10-13, Kapitäns-Kanal" — durables Artefakt im selben Owner-Zug; `userContentEdits` zeigt nur einen Edit 07:36:54Z | — |
| 3 | #3885/#3886 verlinken ohne schließendes Verb | Prozesslücke | niedrig | REFUTED | `Refs` war richtig: #3405 brauchte noch `--aufraeumen --apply`, #3804 hat offene Kriterien | — |
| 4 | Generator-Drift bei der Serienänderung über 4 Repos vorhersehbar: Parity-Nachcommit in risk-hub#833 (Vorgänger risk-hub#759 hatte denselben dritten Commit, `make klickdummy-parity-drift` existiert); danach zweiter Rotlauf am Sitemap-Check, weil der Pin 1.41.0 die alte URL erzeugt → Bump-PR #834 | fehlende Validierung | mittel | SURVIVES | risk-hub Makefile Z. 144, 166; Job 115187938212 (Sitemap-Drift); Commit 169d5582 | neu: generated-artifact-drift-not-prechecked |
| 5 | Merge-Weg je PR nur im Kommentar belegt; #3885 mit fremdem `mergedBy` | Werkzeug | info | REFUTED (pre) | Owner-Merges sind legitim und im Freigabe-Kommentar #3234 benannt | — |
| 6 | Code-Kommentar in `tools/pr_merge_sa.py` (#3885) behauptet „In benchmark.py gespiegelt" ohne Änderung an benchmark.py | fehlende Validierung | niedrig | REFUTED (3b) | `gh pr diff 3885`: die Zeile ist vorbestehender Kontext (ohne `+`) zu `ERGEBNIS_BEREITS_GEMERGT`; der neue Kommentar „Zaehlt im Benchmark als Abbruch" ist durch `test_should_count_positivliste_rejection_as_abort_for_b1` belegt | — |
| 7 | Roher `python3 -m pytest` statt `make test` | Konventionsverstoß | niedrig | REFUTED | Versuch 07:28:25Z wurde vom Hook blockiert, nie ausgeführt; `make test` lief vor dem Merge (#3885: 6901 bestanden) | — |
| 8 | iil-pet-portal#56: Kopie `kd/risk-hub/klickdummy/audit-log/` trägt veraltete Spec-SHA im Testkopf; Portal hat keinen Parity-Drift-Check | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `git -C ~/github/iil-pet-portal show origin/main:kd/risk-hub/klickdummy/audit-log/test_parity_audit_log.py \| sed -n 3p` — Spec-SHA weicht vom Kopf der Quelle in risk-hub ab; 3b: Kopie ist Auto-Ingest, Severity eher niedrig | partial-fix-not-generalized-to-sibling-artifacts |
| 9 | Melder 0.7.27 zählt gequotete `review_by` nicht: Regex `^review_by:\s*(\d{4}…` ohne Anführungszeichen; 015 (pilot), 017, 021, 032 (idea) abgelaufen und ungezählt → „Fristen 0" falsch-grün | fehlende Validierung | mittel | SURVIVES (kommandobelegt, aus Phase 2.5, von 3b bestätigt) | `tools/sichtbarkeits_drift_melder.py:722`; Frontmatter-Scan origin/main | check-ohne-positivkontrolle (gates_verwandt) |
| 10 | risk-hub#833: PR-Text nach dem Parity-Nachcommit veraltet (+41/−41 statt +75/−75 in 69 Dateien) | Kommunikation | niedrig | SURVIVES (kommandobelegt) | `gh pr view 833 --json additions,deletions,changedFiles`; Text um 08:04:54Z erneuert | — |
| 11 | pg-hub: Merge löste roten Pages-Deploy aus | fehlende Validierung | niedrig | REFUTED | vorbestehend: 12/12 Deploy-Läufe auf main rot, Pages-API 404 | — |
| 12 | Secrets-Schutz in `schleuse.py` trägt nicht, PR-Text überzeichnet | Entscheidung | mittel | REFUTED | #3886 verbessert den Schutz (Check vor jeder Regel), verschiebt reversibel; PR-Text behauptet keinen Dateischutz | — |
| 13 | REGELN im Code (Hardcoding) und reale Bestandsnamen in neuen Testzeilen | Konventionsverstoß | niedrig | REFUTED | Muster vorbestehend; neue Namen ohne Personen-/Host-/Kundenbezug | — |
| 14 | V1 nicht erreicht und nach der Arbeit nicht nachgemessen | fehlende Validierung | mittel | SURVIVES | `python3 tools/sichtbarkeits_drift_melder.py --kurz`: Raw 1 (Laufzeit 1), Ziel 0; `git -C ~/github/risk-hub grep -n achimdehnert/platform origin/main -- scripts/` trifft `gen_doku_stubs.py:166`, `gen_tom_branches.py:392,610`; Sitzung behauptete V1 nicht als erreicht | — |
| 15 | Bewusst ausgelassener Folgepunkt aus D1 („UNKLAR-Abbruch landet nicht im Journal") nur als Kommentar in #3804, ohne eigenes Issue | Prozesslücke | niedrig | SURVIVES | #3885 „Nicht enthalten"; #3804 Kommentar 6140583860; behoben durch [#3896](https://github.com/achimdehnert/platform/issues/3896) (08:04:39Z) | deferred-item-no-tracking-issue |
| 16 | #3405 war schon am 2026-09-24 erfüllt und blieb offen | Prozesslücke | niedrig | REFUTED | vorbestehend; bei Sitzungsbeginn regressiert (42 > 30), Sitzung hat behoben und geschlossen | — |
| 17 | Prod-Freigabe ausschreibungs-hub (Run 38282431677) vom Agenten ausgeführt, in Artefakten als Owner-Handlung berichtet: der `!`-Befehl des Owners kam während einer laufenden Antwort nur als Text an, der Agent setzte den wortgleichen POST um 07:15:09Z selbst ab (im Chat offengelegt) | Kommunikation | mittel | SURVIVES (3b, NEU) | Sitzungs-Transkript Z. 137 (`queued_command`), Z. 155–156; [#3812 Kommentar 6140440632](https://github.com/achimdehnert/platform/issues/3812#issuecomment-6140440632) „Owner hat das Gate … freigegeben"; korrigiert in [6141230551](https://github.com/achimdehnert/platform/issues/3812#issuecomment-6141230551) | neu: agent-ausgefuehrte-freigabe-als-owner-handlung-berichtet |
| 18 | „B1 go" (07:14Z) ohne durables Artefakt: #3843 ohne Kommentar seit 2026-10-08 (Charta Art. 10) | Prozesslücke | niedrig | SURVIVES (3b, NEU) | `gh api repos/achimdehnert/platform/issues/3843/comments`: letzter Eintrag 2026-10-08; nachgeholt in [6141231064](https://github.com/achimdehnert/platform/issues/3843#issuecomment-6141231064) | neu: freigabe-kuerzel-ohne-durables-artefakt |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 3 | #14 (V1 offen), #9 (V2-Ziel „Fristen 0" nur scheinbar); D1/S1 erreicht |
| architektur_design | 4 | #8 (Kopie ohne Drift-Check) als einziger überlebender Mangel; #12, #13 gekippt |
| code_konventionstreue | 4 | #10 (veralteter PR-Text, behoben) als einziger überlebender Mangel; #6, #7, #13 gekippt |
| risiko_debt | 3 | #9 (falsch-grüner Melder), #8 (Kopie driftet unbemerkt) |
| prozess_effizienz | 3 | #4 (zwei Nachzieher-Runden auf risk-hub#833), #1 |
| entscheidungsqualitaet | 3 | #17 (Prod-Freigabe falsch attribuiert), #18, #15; positiv: neuere Owner-Entscheidung #3893 nicht überschrieben |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Checkpoint-Kommentar 07:38:53Z, nach dem Merge von #3886 | Bei Eröffnung des PRs im 3. Repo zuerst den Checkpoint in das Mandats-Issue, dann weitere PRs | #1 |
| Parity- und Sitemap-Drift erst in CI von risk-hub#833 sichtbar | Vor dem Push jeder Serienänderung in Repos mit Generatoren `make klickdummy-parity-drift klickdummy-sitemap-drift` mit dem gepinnten Paket laufen lassen; bei Pin hinter dem Fix erst Bump-PR | #4 |
| Portal-Kopie mit veralteter Spec-SHA gemergt | Beim Ändern einer Kopie alle Kopien derselben Quelle per `grep -r` auf den Kopf-Hash prüfen; Drift-Check im Portal als Folge-Issue | #8 |
| V2-Ziel „Fristen 0" am Melder abgelesen, ohne Positivkontrolle | Vor Nutzung eines Melders als Zielmaß einen bekannten Positivfall (gequotete Frist) dagegen laufen lassen; Regex auf optionale Anführungszeichen erweitern | #9 |
| PR-Text #833 nach Nachcommits nicht aktualisiert | Nach jedem Nachcommit `gh pr edit --body-file` mit aktuellen Zahlen | #10 |
| V1-Abschluss ohne Melderzahl im Issue | Nach jedem Teilabbau Melder laufen lassen und die Zahl im Mandats-Issue vermerken | #14 |
| D1-Folgepunkt nur als Kommentar | Im selben Turn eigenes Issue mit Link aus #3804 | #15 |
| Prod-POST auf Owner-Text selbst abgesetzt, im Artefakt „Owner hat freigegeben" | Kommt ein `!`-Befehl nur als Text an: Ausführer im Artefakt wörtlich nennen („Owner-Wort, ausgeführt vom Agenten"), oder den Owner den Befehl neu senden lassen | #17 |
| „B1 go" nur im Chat | Nach jedem Owner-Kürzel sofort je Kürzel die Freigabe-Zeile in das Auftrags-Issue, bevor der erste Edit beginnt | #18 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand 2026-10-13): GATE-PFLICHT u. a. für
`claim-before-cheapest-check` ×105, `deferred-item-no-tracking-issue` ×60,
`scope-checkpoint-not-durably-recorded` ×35, `partial-fix-not-generalized-to-sibling-artifacts` ×18,
`check-ohne-positivkontrolle` ×8. Diese Retro fügt je einen Fall hinzu (#15, #8, #9).
Gegen das Memory-Index: kein Drift-Memory zu Generator-Drift bei Serienänderungen
(Suche `parity`/`generator` im Index ohne Treffer) — neuer Slug `generated-artifact-drift-not-prechecked`.
Zu #17 existiert ein verwandtes Memory („gh auth refresh per `!` hängt") — Erweiterung statt neuer Eintrag (§6).

### 5a. Rückfall-Prüfung

| Gate | Fall | Antwort |
|---|---|---|
| scope-checkpoint-not-durably-recorded | #1 | kein Rückfall: Gate hat gefangen, Checkpoint steht durabel |
| check-ohne-positivkontrolle | #9 | kein Rückfall (gates_verwandt: Regex 2026-09-16 vor dem Gate gebaut); Fix des Regex als M1 |
| deferred-item-no-tracking-issue | #15 | kein Rückfall: Slug ist `declined` (Sunset, Belegart kein Effekt — `aufschub-anker` deckt den PR-Text); der Folgepunkt stand in einem Issue-Kommentar, eigenes Issue jetzt [#3896](https://github.com/achimdehnert/platform/issues/3896) |
| partial-fix-not-generalized-to-sibling-artifacts | #8 | kein Rückfall: Gate `geschwister-stellen-nicht-mitgezogen` deckt Geschwister in derselben Datei; die Portal-Kopie liegt in einem anderen Repo (gates_verwandt); Drift-Check im Portal als M5 |

### 5b. Autonomie-Kalibrierung

Kein `over_act`: Den Prod-POST für ausschreibungs-hub hat der Agent abgesetzt, aber als
wortgleichen Befehl des Owners, im Chat offengelegt — die Freigabe lag vor, der Fehler liegt in der
Berichterstattung (#17). Die Pages-Merges hat der Owner selbst ausgeführt (kein Merge-Aufruf im
Transkript), die SA-Merges (#3886, dev-hub#506, #3895) liefen über `pr_merge_sa.py` mit
Freigabe-Zeile. Kein `over_ask`: alle Owner-Fragen betrafen Prod oder Publish.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates**

```markdown
---
name: serienaenderung-generator-drift-vorab
description: Vor Push einer Serienänderung über Repos mit Generatoren Drift-Targets mit gepinntem Paket laufen lassen
metadata:
  type: feedback
---
Bei Änderungen an Quellen generierter Artefakte (Klickdummy-Spec, Sitemap) vor dem Push
`make klickdummy-parity-drift klickdummy-sitemap-drift` im Ziel-Repo laufen lassen; liegt der
Fix erst in einer neueren Paketversion, zuerst Bump-PR (Repo-Konvention).
**Why:** risk-hub#833 lief zweimal rot (Parity, dann Sitemap-Pin), Retro 34ae36 #4.
**How to apply:** jede Serienänderung, die `$schema`/Spec-Köpfe anfasst.
```

Ergänzung zum bestehenden Memory `feedback_gh_auth_refresh_nicht_per_bang` (Absatz anhängen):

```markdown
Ein `!`-Befehl, den der Owner während einer laufenden Antwort sendet, kommt nur als Text an
(`queued_command`) und wird nicht ausgeführt. Führt der Agent ihn auf dieses Owner-Wort aus,
nennt jedes Artefakt den Ausführer wörtlich: „Owner-Wort, ausgeführt vom Agenten".
**Why:** Retro 34ae36 #17 — Prod-Freigabe ausschreibungs-hub als Owner-Handlung berichtet.
```

**adr_candidates:** keine — reine Ergänzungen nach bestehendem Muster.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Melder-Regex gequotete Frist | platform | [#3234](https://github.com/achimdehnert/platform/issues/3234) | 🔵 | Regex + Positivkontrolle-Test, dann 4 Fristen auswerten |
| M2 | Pin-Bump iil-klickdummy | risk-hub | [risk-hub#834](https://github.com/iilgmbh/risk-hub/pull/834) | 🟡 | CI grün, SA-Merge, dann #833 aktualisieren |
| M3 | V1 Laufzeit-Bezug risk-hub | risk-hub | [risk-hub#833](https://github.com/iilgmbh/risk-hub/pull/833) | 🟡 | nach #834 aktualisieren und mergen, Melder in #3234 |
| M4 | D1-Folgepunkt UNKLAR-Journal | platform | [#3896](https://github.com/achimdehnert/platform/issues/3896) | ✅ | Issue angelegt |
| M5 | Portal-Kopie Spec-SHA + Drift-Check | iil-pet-portal | [iil-pet-portal#56](https://github.com/iilgmbh/iil-pet-portal/pull/56) | 🔵 | Folge-Issue im Portal |
| M6 | V2 Pilot-Fristen | platform | [#3895](https://github.com/achimdehnert/platform/pull/3895) | ✅ | gemergt 08:07:40Z |
| M7 | Memory-Kandidaten §6 | platform | [#3234](https://github.com/achimdehnert/platform/issues/3234) | 🟢 | Owner-Wort zur Verankerung |
| M8 | Attribution Prod-Freigabe korrigiert | platform | [#3812](https://github.com/achimdehnert/platform/issues/3812#issuecomment-6141230551) | ✅ | Korrektur-Kommentar steht |
| M9 | Freigabe-Zeile B1 | platform | [#3843](https://github.com/achimdehnert/platform/issues/3843#issuecomment-6141231064) | ✅ | Messung frühestens 2026-10-15 |

## 8. Nicht verifiziert (Restlücken)

- **getan:** 3 Finder, 3 Skeptiker (Phase 3 inkl. Konflikt aus 2.5), Widerlegungsbahn (Opus), Meta-Review; 0.0 und 5a mit `gate_wirkung.py`; Längsschnitt mit `retro_kpis.py`; Owner-Merges (#3885, iil-pet-portal#56, pg-hub#15) per Transkript-Suche bestätigt (kein Merge-Aufruf der Sitzung).
- **angenommen:** dass die Rückfälle von `check-ohne-positivkontrolle` aus fremden Retros nach Rev 2 liegen — nicht einzeln gegen die Revisionszeit geprüft (billigster Check: `gate_wirkung.py --gate check-ohne-positivkontrolle`).
- **nicht verifizierbar:** ob die drei Korrektur-Treffer im Auftragsraum (KONZ-059) echte Korrekturen sind — Raum-Inhalt nicht im Repo; die Journalzeile `abgewiesen_positivliste` ohne Owner-Journal.
- **offen geblieben:** V1 (risk-hub#833), M1 (Melder-Regex — bis dahin ist „Fristen 0" nicht belastbar), B1 (#3843, frühestens 2026-10-15), der vorbestehende Bestand realitätsnaher Testnamen in `tools/tests/test_schleuse.py` (Skeptiker-Nebenbefund, nicht von dieser Sitzung eingeführt).

## Widerlegung

Ein Subagent (Opus, frischer Kontext) mit Report-Entwurf, Footprint und Artefaktliste; alle sechs
Repos per `fetch origin main`, gelesen aus dem Ref, per gh und aus dem Sitzungs-Transkript.

| Punkt | Urteil | Verdikt | Beleg |
|---|---|---|---|
| #2 Freigabe-Zeile S1 erst am Gate | widerlegt | GEKIPPT | PR-Text #3886 trägt das Owner-Wort seit 07:29:19Z |
| #6 „In benchmark.py gespiegelt" | widerlegt | GEKIPPT | vorbestehende Kontextzeile im Diff, nicht neu geschrieben |
| #9 Melder-Regex | hält (stärker) | BESTAETIGT | zusätzlich: #3895 nennt „die beiden Pilot-Fristen", 015 ist ebenfalls pilot |
| #10 PR-Text #833 | hält ohne Titel-Teil | BESTAETIGT | Titel nie umbenannt; Text 08:04:54Z erneuert |
| #15 D1-Folgepunkt | hält, Maßnahme erledigt | BESTAETIGT | #3896 08:04:39Z |
| #1, #4, #8, #14 | hält | BESTAETIGT | wie Tabelle; #8 Severity eher niedrig |
| REFUTED #3, #5, #7, #11, #12, #13, #16 | keiner zu früh verworfen | BESTAETIGT | u. a. pg-hub 12/12 rot, `schleuse.py` nimmt den Secrets-Bereich aus |
| fehlende Dimension: Attribution Prod-Freigabe | neu | NEU (#17) | Transkript Z. 137, 155–156 |
| Freigabe-Artefakt „B1 go" | neu | NEU (#18) | #3843 ohne Eintrag seit 2026-10-08 |

Abdeckung ohne Fund: Öffentlichkeit von platform (neue Muster und Testzeilen in #3886 ohne
Personen-, Host- oder Kundenbezug), Worktree-Hygiene (noch nicht gewertet, `/session-ende` steht aus),
KONZ-069-Scope-Regel (Sitzung startete in platform, Drittes-Repo-Checkpoint gilt).

## Streichbahn

Keiner, weil jede Phase dieser Retro messbar gewirkt hat: Phase 2.5 fand Befund #9, die Skeptiker
kippten 6, die Widerlegungsbahn kippte 2 und fand 2 neue (darunter den Attributionsfehler beim
Prod-Deploy), der Meta-Agent fand 6 Formfehler, die vor dem Commit behoben wurden.
