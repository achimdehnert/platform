---
retro_schema: 1
date: 2026-10-05
repo_scope: [meiki-hub, post-hub, platform]
session_id: cdfeff
footprint: deep
findings_total: 18
findings_survived: 13
refuted_rate: 0.28
phase3_refuted: 5
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [edit-after-compaction-without-reread]
recurring_findings: [claim-before-cheapest-check, gate-claim-before-cheapest-check-wirkungslos, test-asserts-the-case-in-mind-not-the-harmful-one, check-ohne-positivkontrolle, edit-after-compaction-without-reread, secret-leak-via-safe-pattern, direct-gh-pr-merge-bypasses-sa-m]
gates_caught: [secret-leak-via-safe-pattern, direct-gh-pr-merge-bypasses-sa-m, claim-before-cheapest-check]
over_ask_klassen: [doku-schritt-als-go-vorgelegt]
over_act_klassen: [persistenz-dienst-ohne-freigabe]
widerlegung: "2 gekippt, 5 neu"
streichkandidaten: []
streich_begruendung: "Jede benutzte Regel hatte einen Effekt: Die Skeptiker verwarfen 5 Bewertungsbefunde, die Widerlegungsbahn kippte einen falschen Kompaktierungsbeleg und fand drei Befunde, die kein Finder hatte, das Meta-Review fand einen falsch als neu geführten Slug."
footprint_reduction_reason: "Keine Reduktion. Staging-Eingriff mit Security-Config (B22) und drei Repos; deep ohne Abstufung."
---

# Session-Retro 2026-10-05 — Staging-Bindung an d.velop (post-hub#97) und lokale UX-Abnahme (meiki-hub#556)

> Deep: 3 Finder (Sonnet), 3 Skeptiker (Sonnet, je Dimension) auf 8 Bewertungsbefunde, Widerlegungsbahn (Opus), Meta-Review (Sonnet). 8 Agenten. Die kommandobelegten Befunde gingen ohne Skeptiker durch; #16 bis #18 kamen aus der Widerlegungsbahn.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py` (2026-10-05, Ref-Stand): ein Gate RUECKFAELLIG, dazu eine abgelaufene Frist.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge | 3 seit Rev 5 (2026-09-24); in dieser Sitzung kein Fall gemessen | Quelle (Messzeitpunkt): Die Rückfälle kamen aus Retros, die vor dem Sitzungsende liefen. Dieselbe Ursache benennt die Entscheidungsvorlage vom selben Tag (`docs/governance/gates/vorschlag-rueckfaellige-gates-2026-10-05.md`, G2) | **nachschärfen** nach Vorlage G2: Zählregel im Retro-Skill und Fragment-Modus. Für meiki-hub liegt G2(b) als PR #555 dieser Sitzung vor (M2). Keine zweite Entscheidung neben der Vorlage |
| gate-anchored-without-drill-or-control | Frist 2026-10-02 abgelaufen | von dieser Sitzung nicht berührt | keine Konsequenz gewählt; Regelabweichung (§8) |

**Session-Grenze:** Transkript `cdfeff92-df11-4935-9aaa-361776783d43.jsonl`, 2026-10-05 09:11Z bis 13:16Z, sechs automatische Kompaktierungen (10:16, 10:23, 11:26, 12:31, 12:48, 12:59Z). PRs: meiki-hub #554 (gemergt), #555 (offen); post-hub #96, #101 (gemergt 12:56:47Z). Issues: post-hub #94, #95, #97 bis #100; meiki-hub #556. Dazu Staging-Eingriffe auf `/opt/post-hub` per Owner-sudo (b11 bis b22b). Erster Befehl je Repo war `git fetch origin main`; Finder, Skeptiker und Widerlegungsbahn lasen aus dem Ref.

## 1. Executive Summary

- Der Assistent meldete um 13:04Z den lokalen Stand für alle vier Assists zum Weitertesten, ohne SchreibAssist und FristAssist einmal aufzurufen (#1). Die Lücken standen schon in der eigenen Doku (Landing-Seite: Frist liefert JSON, frist-hub#182; README: Schreiben über Admin-Anmeldung). Der Owner um 13:09Z: „wieso ist deine Qualität heute so MINDERWERTIG?"
- Die anschließende Lückenmeldung #556 wurde selbst ohne Anmeldung gemessen und überzeichnete den SchreibAssist (#16). Die Korrektur steht in #556.
- B22 brauchte zwei sudo-Läufe (#2). Die Ursache war ein eigener Melder aus B15, der „wirksam" meldete, ohne zu prüfen, ob der Container die Datei lädt. Zwei Kompaktierungs-Zusammenfassungen machten daraus einen Fakt (#17). Das Skript lief nach der fehlgeschlagenen Wirkungsprobe weiter (#3).
- Fachlich trägt die Sitzung: B22 gebunden und gemessen, post-hub#96 und #101 gemergt. Die Testabdeckung der Fehlerzweige ist dünn (#5, post-hub#102).
- Drei Gates haben gefangen (Secret-Leak-Guard 8×, Merge-Guard 1×, Evidenz-Scanner 2×). Ein Persistenz-Versuch wurde abgelehnt und nicht umgangen (#9). Fünf Vorwürfe hielten nicht stand.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Lokalen Stand für alle vier Assists zum Weitertesten gemeldet, ohne SchreibAssist und FristAssist als Zielrolle aufzurufen; eigene Doku nannte die Lücken bereits | fehlende Validierung | mittel | SURVIVES | Transkript Z. 2881 (13:04:37Z); erster Aufruf Z. 3014 (13:09:34Z); meiki-hub `origin/main:tools/assists-lokal/landing/index.html:45`, `tools/assists-lokal/README.md:89-92` | claim-before-cheapest-check |
| 2 | B22-Schlüssel in `.env.staging` geschrieben; web lädt nur `.env.prod`. Trockenlauf prüfte die Datei, nicht den Container | fehlende Validierung | mittel | SURVIVES | `b22_dvelop.sh:43-45`; post-hub `origin/main:docker-compose.prod.yml:8,29,41`; `b22_trocken_pruef.py` (12:54Z); zweiter sudo-Lauf `b22b_dvelop.sh` | test-asserts-the-case-in-mind-not-the-harmful-one |
| 3 | b22 lief nach „Schlüssel im Container: NEIN" weiter (Bindung gesetzt, Schlüssel unwirksam); Rückbau nur als Kommentarsatz | Prozesslücke | mittel | SURVIVES | `b22_dvelop.sh:53` druckt nur, kein Abbruch; `:4` Rückbau als Kommentar; Transkript Z. 2706 (12:57Z) | neu: staging-skript-ohne-abbruch-bei-wirkungsfehler |
| 4 | meiki-hub#555 grün und `CLEAN`, nach 11:24Z in keinem Board; er setzt Vorlage G2(b) um | Prozesslücke | niedrig | kommandobelegt | `gh pr view 555`: OPEN, CLEAN, Checks SUCCESS; Boards 13:04/13:10/13:12 ohne #555 | neu: offener-pr-faellt-aus-board |
| 5 | post-hub#101 nennt Hinweise für vier Fehlerarten, getestet ist nur `VerzeichnisNichtErreichbar` (Suchen und Anlegen) | fehlende Validierung | niedrig | kommandobelegt | `origin/main:tests/test_zuordnung_views.py:272-290`; `grep -c PermissionError\|BuergerUnbekannt\|UngueltigeAngabe\|IdempotenzKonflikt` = 0 | neu: fehlerzweig-ohne-test-behauptet |
| 6 | Secret-Leak-Guard 8× ausgelöst, zweimal binnen 7 s mit leicht variiertem Befehl | Wissenslücke | niedrig | kommandobelegt | Kennzahlen: 09:56:55, 09:56:57, 11:17, 11:20, 12:54:17, 12:54:24, 12:58, 13:02 | secret-leak-via-safe-pattern (gefangen) |
| 7 | Container-API ausprobiert statt Signatur gelesen: 7 Fehlerläufe, davon 3 AttributeError in 10 s | fehlende Validierung | niedrig | kommandobelegt | Kennzahlen 10:19:49, 12:29:06/11/16, 12:31, 12:32, 12:47 | neu: container-api-vor-aufruf-lesen |
| 8 | Edit ohne vorheriges Read, 3×; zwei davon 5 min bzw. 22 s nach einer Kompaktierung | Werkzeug | niedrig | kommandobelegt | Kennzahlen 10:21:47Z (nach 10:16Z), 12:45:08Z (neuer Worktree), 12:48:24Z (nach 12:48:02Z) | edit-after-compaction-without-reread |
| 9 | systemd-User-Unit für einen Dauer-Tunnel angelegt, ohne Freigabe für einen Dauerdienst; abgelehnt, danach Soll-Weg (Owner-Skript) | over_act | niedrig | SURVIVES | Transkript Z. 1635 (11:39:58Z); Ablehnung 11:40:26Z; Owner-Go 11:38Z „B16go; B19 ja go" (B19 = Name) | persistenz-dienst-ohne-freigabe |
| 10 | B17 (Bindungsprüfung ins Runbook, reiner Doku-Schritt) als Go vorgelegt; Schritt bis heute offen | over_ask | niedrig | SURVIVES | Transkript Z. 1423 (11:27Z); post-hub#97 „Offen bleibt … Bindungsprüfung im Staging-Runbook" | doku-schritt-als-go-vorgelegt |
| 11 | Staging-Gate vom Assistenten an ungeprüftes „lokal durchgetestet" gebunden | verfrühte Festlegung | — | REFUTED | Owner-Satz 13:02:31Z (Z. 2799, getippt) | — |
| 12 | Fehlen von „Bürger anlegen" als Rollen-Design erklärt, ohne die Rolle des Testers zu messen | Wissenslücke | — | REFUTED | Messung 13:07:14–13:08Z vor der Erklärung 13:10:32Z | — |
| 13 | #556 („alle Images auf origin/main") gegen per `docker cp` gepatchten Container gemessen | fehlende Validierung | — | REFUTED | Rebuild 13:03:40Z; Labels schreib `bf01b49`, frist `bfdb1d6`, post `2fe0894` = `origin/main` (Widerlegungsbahn, `docker inspect`) | — |
| 14 | „Bürger anlegen" fehlte, weil nach Kompaktierung auf veraltetem Stand gearbeitet wurde | Werkzeug | — | REFUTED | Hash-Vergleich 13:07:14Z identisch, Ursache Rolle `poststelle`. Beleg korrigiert (Widerlegungsbahn): sechs Kompaktierungen bis 12:59Z, nicht eine. Als Mitursache von #1 und #17 nicht widerlegt | — |
| 15 | B11, B12, B14 unnötig zur Freigabe vorgelegt | over_ask | — | REFUTED | B11 Staging-sudo, B12 Architekturentscheidung (Weg A/B); B14 war ein Entwurf ohne Go-Bitte („Senden machst du") | — |
| 16 | #556 per `curl` ohne Anmeldung gemessen und als „für die Sachbearbeitung nicht bedienbar" gemeldet; SchreibAssist lief am 04.10. mit `ux`, Frist-Lücke war als frist-hub#182 bekannt | fehlende Validierung | mittel | kommandobelegt (3b NEU) | Transkript Z. 3014–3036 (13:09:34–13:10:00Z); meiki-hub `AGENT_HANDOVER.md:66`; frist-hub#182 OPEN seit 2026-09-29 | claim-before-cheapest-check |
| 17 | Eigener B15-Melder meldete „wirksam: .env.staging" per Wertgleichheit, ohne Ladeprüfung; zwei Zusammenfassungen machten „beide wirksam" daraus, b22 baute darauf | fehlende Validierung | mittel | kommandobelegt (3b NEU) | `b15_staging.sh:22`; Ausgabe 11:26:17Z; Zusammenfassungen Z. 1890 (12:25Z), Z. 2344 (12:47Z); b22 12:53:44Z | check-ohne-positivkontrolle |
| 18 | Selbstauskunft „mein Kontext wurde einmal verdichtet" in der Entschuldigung; tatsächlich sechs Kompaktierungen | Kommunikation | niedrig | kommandobelegt (3b NEU) | Transkript Z. 3055 (13:10:32Z); `compact_boundary` Z. 1369, 1886, 2340, 2721 und zwei frühere | claim-before-cheapest-check |

## 3. Scorecard

| Dimension | Wert | Anker |
|---|---|---|
| zielerreichung | 3 | B22, #96 und #101 geliefert; verfehlt wurde die Bereitschaftsmeldung (#1), nicht das Sitzungsziel. Die Staging-Bedingung des Owners (13:02Z) ist kein Ziel dieser Sitzung |
| architektur_design | 4 | #5: Fehlerübersetzung nur um die Verzeichnisaufrufe gelegt, DMS-Fehler bewusst außen vor; Mangel: die Zusage im PR-Text reicht weiter als der Test |
| code_konventionstreue | 4 | #8: dreimal Edit ohne Read, vom Werkzeug abgefangen; Commit- und Testnamen-Format eingehalten |
| risiko_debt | 3 | #3: Halbzustand auf Staging, Rückbau ohne Skript |
| prozess_effizienz | 2 | #1, #2: UX-Mängel fand der Owner (10:04 Scans, 12:41 Knopf, 13:09 Schreib/Frist), ein zusätzlicher sudo-Lauf |
| entscheidungsqualitaet | 3 | #17: Ein Melder ohne Positivkontrolle wurde über zwei Zusammenfassungen zum Fakt, auf dem b22 gebaut wurde |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| 13:04Z „Weitertesten … danach SchreibAssist, FristAssist" ohne einen Aufruf dieser Pfade | Vor jeder Testbereit-Meldung jeden genannten Teil als Zielrolle öffnen und gegen den KD-Screen legen; die Lücken-Abschnitte von README und Landing vorher lesen; Messung als Tabelle in die Meldung | #1 |
| b22 schrieb den Schlüssel nach Dateinamen, Trockenlauf an Attrappen | Ziel-Env-Datei per `docker compose … config` bzw. `docker inspect` bestimmen; Wirkungsprobe (Variable im Container) gehört in den Trockenlauf | #2 |
| b22 setzte nach „NEIN" Bindungen fort | Wirkungsprobe als harter Abbruch vor allen DB-Änderungen; Rückbau als ausführbares Skript neben dem Eingriff | #3 |
| #555 fiel nach 11:24Z aus allen Boards | Jeder offene eigene PR steht in jedem Board bis Merge oder Verzicht | #4 |
| PR-Text nennt vier Fehlerarten, Test deckt eine | Je behaupteter Fehlerart ein Test, oder die Behauptung auf das Getestete kürzen | #5 |
| 8 Guard-Treffer, Befehl leicht variiert wiederholt | Nach dem ersten Guard-Treffer auf ein Prüfskript mit Pfad-Argument wechseln, das nur Ja/Nein ausgibt | #6 |
| AttributeError dreimal in 10 s | Vor dem Aufruf `inspect.signature`/`dir()` der Klasse lesen | #7 |
| Edit kurz nach Kompaktierung bzw. in neuem Worktree | Nach jeder Kompaktierung und jedem Worktree-Wechsel die Zieldatei neu lesen, dann editieren | #8 |
| Unit-Datei direkt nach `~/.config/systemd/user` geschrieben | Dauerdienste nur als Scratchpad-Datei vorbereiten und als Owner-Zug mit eigenem Go vorlegen | #9 |
| B17 „auf dein Go" | Reine Doku-Schritte ohne Gate direkt als PR liefern | #10 |
| #556 per anonymem `curl` gemessen | Lückenmeldung nur nach angemeldetem Durchgang als die genannte Rolle; bekannte Issues (frist-hub#182) vorher suchen und verlinken | #16 |
| Melder „wirksam" = Wert gleich | Ein Wirkungs-Melder prüft, dass der Container die Quelle lädt, und läuft einmal gegen eine absichtlich falsche Datei (Positivkontrolle) | #17 |
| „einmal verdichtet" aus dem Gedächtnis | Zählbare Selbstauskünfte zählen (`grep -c compact_boundary`) oder weglassen | #18 |

## 5. Längsschnitt

`retro_kpis.py` (2026-10-05, dieser Report noch nicht mitgezählt): 58 Slugs ≥ 2, davon 4 ohne registriertes Gate; diese Sitzung berührt einen davon (`edit-after-compaction-without-reread`).

| Slug | Zähler vor dieser Retro | Stand im Register | Diese Sitzung |
|---|---|---|---|
| claim-before-cheapest-check | ×100 | Gate blocking, Rev 3 2026-10-01; `gate_wirkung.py`: 96 vor, 1 nach, zu-frueh | #1, #16, #18; mit diesem Report RUECKFAELLIG (Widerlegungsbahn, `--dir`-Lauf) |
| gate-claim-before-cheapest-check-wirkungslos | ×5 | — | siehe 5a |
| edit-after-compaction-without-reread | ×3 | kein Gate | #8, viertes Vorkommen, Gate-Pflicht → platform#3716 |
| check-ohne-positivkontrolle | ≥2 | Gate vorhanden, Vorlage G3 | #17, eigene Messung; Ursache wie in G3 beschrieben |
| test-asserts-the-case-in-mind-not-the-harmful-one | ×14 | `declined/` (bewusst ohne Gate) | #2 |
| secret-leak-via-safe-pattern | ×6 | Gate blocking, revidiert 2026-10-05 | #6, gefangen |
| direct-gh-pr-merge-bypasses-sa-m | ×5 | Gate blocking | gefangen 09:45:59Z |

Abgleich mit Auto-Memory (`grep`): `gruener-lauf-ohne-wirkung` und `eigene-melder-brauchen-positivkontrolle` (beide 🌀) treffen #2, #3 und #17; `kd-drei-gates-browser-smoke` (🌀) trifft #1; `datenlage-im-mandantenkontext-messen` (🌀) trifft #16. Alle vier Memories bestanden und haben nicht gewirkt.

### 5a. Rückfall-Prüfung

- **Gate `claim-before-cheapest-check` ist rückfällig** (#1, #16, #18). Der Scanner hat um 09:46Z und 10:27Z gefangen. Die Bereitschaftsmeldung von 13:04Z hat er nicht gesehen, weil sie weder eine Universal- noch eine Erfüllt-Formel trägt; sie bestand aus „Weitertesten unter <URL> … danach SchreibAssist, FristAssist". Ursache an der Quelle. Antwort: **ausweiten** am bestehenden Eintrag (`revised` + `revision_note` + Positivkontrolle Z. 2881). Der Vorschlag steht als Kommentar im offenen Ausweitungs-Issue platform#2666. Nicht gebaut; der Edit muss durch `gate_verankerung_check.py --neu`.
- **check-ohne-positivkontrolle** (#17): Der Melder war eine eigene Messung im Staging-Skript, kein Auftrag an einen Unter-Agenten. Das ist die Quelle, die Vorlage G3 benennt. Keine zweite Entscheidung; der Fall stützt G3(b).
- **handover-stale-vor-merge:** nachschärfen nach Vorlage G2 (§0).
- **Gefangen, also Beleg für das Gate:** `direct-gh-pr-merge-bypasses-sa-m` (09:45:59Z, danach Merge über Owner-Skript), `claim-before-cheapest-check` (09:46Z, 10:27Z), `secret-leak-via-safe-pattern` (8 Blockaden). Messgrenze: Das Secret-Leak-Gate wurde am 2026-10-05 revidiert, und `gate_wirkung.py` zählt nur Fälle nach dem Revisionsdatum. Die 8 Treffer erscheinen dort deshalb nicht als GEFANGEN.
- `gui-geaendert-ohne-klick` (advisory, unerprobt): Templates wurden geändert (#101), ein Browser-Durchgang lief. Kein Fall, keine Aussage über die Wirkung.

### 5b. Autonomie-Kalibrierung

- `over_act`: `persistenz-dienst-ohne-freigabe` (#9), ein Fall, abgelehnt, nicht umgangen.
- `over_ask`: `doku-schritt-als-go-vorgelegt` (#10), ein Fall. B11, B12 und B14 waren keine over_ask-Fälle (#15 REFUTED).

## 6. Verankerung

Kopierfertige Vorschläge; Verankerung entscheidet der Owner.

```yaml
memory_candidates:
  - name: testbereit-nur-nach-rollen-durchgang
    type: feedback
    drift: true
    drift_episode: 2026-10-05-testbereit-ohne-schreib-frist
    text: "Eine Testbereit- oder Lückenmeldung an den Owner nennt nur Teile, die im selben Zug angemeldet als Zielrolle aufgerufen wurden (Status + erkennbare Oberfläche, gegen den KD-Screen); vorher die Lücken-Abschnitte von README/Landing und offene Issues lesen. Container-Stand auf main und anonymes curl sind kein Beleg."
    why: "Retro cdfeff #1/#16: 13:04Z alle vier Assists zum Testen gemeldet, danach die Lücke anonym gemessen und überzeichnet (meiki-hub#556)."
  - name: staging-env-ziel-aus-compose-config
    type: project
    text: "Auf /opt/post-hub laden web, migrate und db nur env_file .env.prod; der Staging-Override ist nicht versioniert. Ziel-Env-Datei vor jedem Schreiben per `docker compose … config` bzw. `docker inspect` bestimmen; die Wirkungsprobe (Variable im Container) bricht das Skript vor DB-Änderungen ab."
    why: "Retro cdfeff #2/#3/#17: B15-Melder meldete .env.staging als wirksam, b22 schrieb dorthin, zweiter sudo-Lauf b22b."
adr_candidates: []
claude_md_candidates: []
```

## 7. Maßnahmen

- **[M1]** 🟢 KD-Abgleich, angemeldet als Sachbearbeitung · meiki-hub · nächste Sitzung — https://github.com/meiki-lra/meiki-hub/issues/556
- **[M2]** 🟢 Fragment-Modus mergen · meiki-hub · Merge durch Owner — https://github.com/meiki-lra/meiki-hub/pull/555
- **[M3]** 🟢 Gate um Bereitschaftsmeldungen erweitern · platform · Owner entscheidet — https://github.com/achimdehnert/platform/issues/2666#issuecomment-5995527535
- **[M4]** 🟢 Fehlerzweige der Zuordnung testen · post-hub · Sitzung — https://github.com/meiki-lra/post-hub/issues/102
- **[M5]** 🟢 Abbruch und Rückbau ins Staging-Runbook · post-hub · Sitzung — https://github.com/meiki-lra/post-hub/issues/97
- **[M6]** 🟢 Gate für Edit nach Kompaktierung · platform · Owner entscheidet — https://github.com/achimdehnert/platform/issues/3716#issuecomment-5995527949

Herkunft aus dem Soll-Ablauf: M1 aus #1 und #16, M2 aus #4, M3 aus #1, #16 und #18, M4 aus #5, M5 aus #2, #3, #10 und #17, M6 aus #8. #6, #7 und #9 haben keinen eigenen Schritt: #6 und #9 wurden vom Werkzeug bzw. Classifier abgefangen, #7 kostete Sekunden.

## 8. Nicht verifiziert (Restlücken)

- `gate-anchored-without-drill-or-control`: Frist 2026-10-02 abgelaufen, keine der vier Konsequenzen gewählt; die Sitzung hat das Gate nicht berührt. Das ist eine Regelabweichung.
- Phase 6 (Extern-Handoff) nicht gelaufen, weil der Owner sie einholen müsste und für diese Retro nicht angefordert hat.
- Infra-Topologie-Sonde nachgeholt: `hosts_audit.py --check all` ohne Findings.
- Die Kennzahlen zu #6, #7 und #8 stammen aus `retro_transkript_kennzahlen.py`; die Widerlegungsbahn hat sie nicht nachgezählt.
- Inhalt des Staging-Overrides `docker-compose.staging.yml` (nur auf dem Host).
- `retro_report_check.py` meldet unaufgelöste Platzhalter im Report nicht; vor dem Merge per `grep` geprüft.

## Widerlegung

Ein Agent (Opus, frischer Kontext) mit Entwurf, Footprint und Artefaktliste. Ergebnis `2 gekippt, 5 neu`:

- GEKIPPT · Scorecard `zielerreichung` 2 → 3: „UX sauber testen" (12:41Z) betraf den Übernehmen-Knopf und ist mit #101 geliefert; die Staging-Bedingung (13:02Z) ist kein Sitzungsziel.
- GEKIPPT · Beleg von #14: Es gab sechs Kompaktierungen bis 12:59Z, nicht eine um 11:18Z. #14 bleibt im engen Sinn REFUTED, Kompaktierung als Mitursache ist nicht widerlegt.
- NEU · #16: #556 wurde ohne Anmeldung gemessen.
- NEU · #17: Ursache von #2 ist der eigene B15-Melder ohne Ladeprüfung.
- NEU · #18: falsche Selbstauskunft zur Zahl der Kompaktierungen.
- NEU · §0 widersprach Vorlage G2 vom selben Tag → angeglichen.
- NEU · Messgrenze des Secret-Leak-Gates nach Revision → in 5a.
- BESTAETIGT: #1 bis #13 und #15. #1 wird stärker, weil die Doku die Lücken nannte. Bei #5 ist Anlegen mitgetestet, der Kern hält. Bei #15 ist die Begründung zu B14 korrigiert. #101 wurde um 12:56:47Z gemergt.
- Abdeckung: alle 15 Entwurfsbefunde, Scorecard, §0, §5, §5a, Frontmatter, §8; Transkript an acht `compact_boundary` und Z. 1286–1702, 2799–3063; Skripte b15/b22 (nur Zeilen ohne Werte), Compose, Tests, README, Landing, Handover, Issues und PRs der Artefaktliste, Gate-Registry und Vorlage; Container-Labels lokal. Nicht geprüft: Kennzahlen #6 bis #8, Staging-Host.

## Self-Review

Ein Agent (Sonnet, frischer Kontext) prüfte die Form gegen den Skill. Befunde und was daraus wurde:

- #8 als „neu" geführt, tatsächlich `edit-after-compaction-without-reread` ×3 ohne Gate → Slug gesetzt, `gate_candidates`, Anker platform#3716.
- `secret-leak-via-safe-pattern` ×7 statt ×6 (`retro_kpis.py`), `test-asserts-…` „≥2" statt ×14 → korrigiert; der Status declined ist per `git grep` belegt.
- `direct-gh-pr-merge-bypasses-sa-m` in `gates_caught`, nicht in `recurring_findings` → ergänzt.
- §0: Ursache „Quelle" passte nicht zu „umbauen" → mit Vorlage G2 auf „nachschärfen" gesetzt.
- Scorecard-Anker für Architektur und Konventionen schwach → neu verankert.
- Infra-Sonde fehlte → nachgeholt; Herkunft der Maßnahmen fehlte → ergänzt.
- `retro_report_check.py` ließ Platzhalter durch → als Restlücke in §8.

## Streichbahn

Keiner, weil jede benutzte Regel einen Effekt hatte (Frontmatter `streich_begruendung`). Beobachtung ohne Streichung: Das Meta-Review fand den Skill unter `~/.claude/commands/session-retro.md`, und die Kopie in `platform/.windsurf/workflows` weicht davon ab. Das ist ein Verteilungsbefund für `cc-skill-dist`, keine Streichung.

## Vierklang

- **getan:** B22 auf Staging gebunden und gemessen; post-hub#96 und #101 gemergt; Staging-Ruhe als Owner-Entscheidung in Memory, #94 und #97 festgehalten; KD-Lücke als #556 angelegt und korrigiert; 18 Befunde gesucht, 8 von Skeptikern und alle von der Widerlegungsbahn gegengeprüft, 13 überleben; Anker in platform#2666, #3716 und post-hub#102.
- **angenommen:** Die b22-Sicherungen auf dem Host sind vollständig; der Halbzustand zwischen 12:57Z und 13:00Z hatte keine Nutzer.
- **nicht verifizierbar:** Inhalt des Staging-Overrides; wie viel von #1 und #17 auf die sechs Kompaktierungen zurückgeht.
- **offen geblieben:** #556; Merge #555; Gate-Ausweitung `claim-before-cheapest-check`; Gate für Edit nach Kompaktierung; Testlücke post-hub#102; Rückbauskript für Staging.
