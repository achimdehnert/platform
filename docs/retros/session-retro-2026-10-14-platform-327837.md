---
retro_schema: 1
date: 2026-10-14
repo_scope: [platform, iil-pet-portal]
session_id: "327837"
footprint: full
footprint_reduction_reason: "deep wegen externer Schreibschritte in sevdesk; reduziert auf full, weil jede Buchung vom Owner freigegeben, per resetToOpen rückholbar und ohne Migration war"
findings_total: 17
findings_survived: 12
refuted_rate: 0.29
phase3_refuted: 4
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [abgleich-fehlt-gegenrichtung-eindeutigkeit, parallel-session-shared-external-target]
recurring_findings: [abgleich-fehlt-gegenrichtung-eindeutigkeit, deferred-item-no-tracking-issue, geteiltes-board-vor-schreibschritt-ungelesen, parallel-session-shared-external-target, zweiter-schreibpfad-ohne-strikt, gleichbetraege-zuordnung-per-reihenfolge, buchungsdatum-systemdatum-statt-valuta, sevdesk-regel-erst-in-prod-sichtbar, tool-api-unverified-before-call, pr-autor-identitaet-nicht-angewandt, zweiter-zahlweg-ohne-stilllegung]
gates_caught: [claim-before-cheapest-check, aufschub-anker]
gates_verwandt: ["aufschub-anker: Befund 2 ist ein Aufschub auf einer lokalen Board-Seite und im Scratchpad, das Gate prüft PR-Texte und Issue-Kommentare", "parallel-session-pr-collision: Befunde 4 und 17 betreffen externe Schreibziele (sevdesk-Mandant, Board-Datei, Memory-Ordner), das Gate prüft nur Worktrees und offene PRs"]
over_ask_klassen: []
over_act_klassen: [externe-buchung-ohne-eigenes-kuerzel]
widerlegung: "2 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil beide teuren Bahnen hier gewirkt haben: der Skeptiker kippte 5 Bewertungsbefunde, die nachweislich die Parallelsitzung ausgeführt hatte, und die Widerlegungsbahn holte einen davon mit Tool-Aufruf-Beleg zurück und fand den Datenschutzfehler im eigenen Entwurf."
---

# Session-Retro 327837 — sevdesk-Buchungen EDV und IIL, Mail-Ablage (platform)

Sitzung `84c8e20e…327837`, 2026-10-14, 06:55–14:31 UTC. Owner-Aufträge unter anderem
„verbuche nun für edv und iil alle offensichtlich klaren positionen", „SC go", „S2 go", dazu
Mail-Ablage und Beleg-Nachträge. Sitzungsgrenze: Branch-Präfix `session/2026-10-14/achim-dehnert/`
dieser Konversation und die unten genannten Artefakte. **Parallelsitzung** `a139ac0a` arbeitete
zeitgleich am selben sevdesk-Mandanten und an derselben Board-Seite; ihre Handlungen sind nicht
Gegenstand dieser Retro (Befunde 12–15 deshalb gekippt).

Lieferanten, Kunden, Beträge und Beleg-IDs stehen hier nur als Platzhalter (Repo öffentlich).

**Artefakte:** platform [#3972](https://github.com/achimdehnert/platform/pull/3972),
[#3953](https://github.com/achimdehnert/platform/pull/3953),
[#3954](https://github.com/achimdehnert/platform/pull/3954),
[#3949](https://github.com/achimdehnert/platform/pull/3949),
[#3948](https://github.com/achimdehnert/platform/pull/3948) (geschlossen); Issues
[#3970](https://github.com/achimdehnert/platform/issues/3970) (geschlossen durch #3972),
[#3976](https://github.com/achimdehnert/platform/issues/3976),
[#3982](https://github.com/achimdehnert/platform/issues/3982) (aus dieser Retro). iilgmbh/iil-pet-portal#58.
sevdesk-Schreibschritte (Mandanten EDV und IIL) protokolliert auf den Board-Seiten
`buchungen-2026-10-14` und `sevdesk-eingaenge-2026-10-14` (lokal, über `/d/`-Link erreichbar).

## Phase 0.0 — Wirkungsbilanz

`gate_wirkung.py` meldet vier `RUECKFAELLIG`-Gates; alle vier sind in
[Retro e50644 §Phase 0.0](session-retro-2026-10-13-platform-e50644.md) vom Vortag entschieden und
hier kein eigener Fall.

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 4 | Quelle | nachschärfen, beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666)); hier hat das Gate gefangen (Kommentar an #3970, 12:40Z) |
| built-but-never-called | 3 | Quelle | ausweiten, beschlossen (Owner „187 go"); hier kein Fall |
| check-ohne-positivkontrolle | 2 | Quelle | nachschärfen, Rev 2 ([#3722](https://github.com/achimdehnert/platform/issues/3722)); hier kein Fall |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | nachschärfen, Rev 10 ([#3600](https://github.com/achimdehnert/platform/issues/3600)); hier kein Fall |

## 1. Executive Summary

- **Geliefert:** Die Ausgleichsbuchungen der Sitzung sind auf Status 1000/400 nachgeprüft: ein Sammeleingang über fünf Ausgangsrechnungen (EDV), ein Altbeleg und vier Eigenbelege Dezember–März. Nach „SC go" sind drei falsch zugeordnete Eigenbelege Juni–August umgehängt. Der Rückzahlungsbeleg (EDV) wurde auf Owner-Wort angelegt und steht bewusst offen bis zur Zahlung. Der Mail-Ablage-Lauf ist gemergt und lief im Zielkontext (#3972). Die Typ-N-Lücke ist als #3976 verankert, die Zuordnungslücke als #3982.
- **Schwerster Befund:** `kostenabgleich` prüft Eindeutigkeit nur vom Umsatz zum Beleg. Ein Abo mit zwei gleich hohen Abbuchungen im Monat hat deshalb am 13.09. drei Belege der falschen Abbuchung zugeordnet. Die Kontrolle „1000/400" kann das nicht sehen (#1).
- **Über der Linie:** Zwei Gutschriften wurden auf ein Owner-Wort gebucht, das nur die PDFs nannte. Das Kürzel, das die Parallelsitzung auf dem geteilten Board dafür verlangt hatte, war ungelesen (#3, #4).
- **Zwei Zahlwege:** Die Sitzung legte für eine Kundenrückzahlung den sevdesk-Beleg an, während die Zahldateien der Parallelsitzung rund 18 min weiter ausführbar blieben (#11).
- **Entlastet:** SEPA-Datei, GiroCode, die Deutung von „erledigt" und die Buchungen mit Abweichung von der Vorlage stammen nachweislich aus der Parallelsitzung (#12–#14). Den Zuschnitt „offensichtlich klar" hatte der Owner delegiert (#15).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `kostenabgleich.zuordnen_position` prüft nur, ob je Umsatz genau ein Beleg im 14-Tage-Fenster passt, und nimmt den Beleg dann aus dem Pool; die Gegenrichtung (passt der Beleg zu einem näheren Umsatz?) fehlt. Ein Abo mit zwei gleich hohen Abbuchungen je Monat (um den 11. und den 23.) bekam am 13.09. drei Eigenbelege Juni–August auf die 11er-Abbuchung statt die 23er (10 statt 2 Tage Abstand). Die Nachprüfung „Beleg 1000 / Umsatz 400" belegt Konsistenz, nicht Richtigkeit | fehlende Validierung | hoch | SURVIVES (Skeptiker 7, 3b bestätigt) | `git show origin/main:tools/sevdesk/kostenabgleich.py` (`TAGE_TOLERANZ = 14`, 1:1-Entnahme); Lauf-Protokoll `~/.claude/sevdesk-kostenabgleich-2026-09-13.json`; nach „SC go" Altumsätze Status 100, neue 400; verankert in [#3982](https://github.com/achimdehnert/platform/issues/3982) | neu: abgleich-fehlt-gegenrichtung-eindeutigkeit |
| 2 | Die Korrektur zu #1 (Paarung nach kleinstem Datumsabstand, beidseitig eindeutig, Gleichstand ausgeschlossen) lag nur im Scratchpad (`klar_abgleich.py`); weder PR noch Issue. Die seit 12/2025 offenen 11er-Abbuchungen ohne Beleg (Board „S1") standen nur auf der lokalen Board-Seite. #3976 deckt nur Typ N und Valuta | Prozesslücke | mittel | SURVIVES (Skeptiker 5 Rest, 8; 3b bestätigt) | `git log origin/main --since='2026-10-14 00:00' -- tools/sevdesk` leer; Body #3976 ohne Treffer für Zuordnung/Gegenrichtung; Anker erst in der Retro ([#3982](https://github.com/achimdehnert/platform/issues/3982)) | deferred-item-no-tracking-issue |
| 3 | Zwei Gutschriften (IIL) wurden gebucht, ohne dass ein eigenes „go" fiel. Das Owner-Wort lautete „<Lieferant> habe ich auch <zwei PDFs>". Die Parallelsitzung hatte auf dem geteilten Board für genau diesen Fall „K3m go" als eigenes Gate verlangt; die Sitzung las das Board vor der Buchung nicht | verfrühte Festlegung | mittel | SURVIVES (Skeptiker 3, 3b nachgeprüft; schwach: das Wort folgt auf „verbuche", das Gate stammte aus der anderen Sitzung) | 0 Owner-Treffer „K3m go" in beiden Transkripten; 0 Tool-Aufrufe der Sitzung auf die Board-Seite vor 13:19Z; Board-Zeile 63 verlangt „K3m go" | neu: geteiltes-board-vor-schreibschritt-ungelesen |
| 4 | Zwei Sitzungen schrieben ohne Eigentümer-Regel an denselben sevdesk-Mandanten und in dieselbe Board-Seite; die eine kannte die Gates der anderen nicht (#3). Der Owner hatte die Trennung laut #3977 „bereits mehrfach in Auftrag gegeben"; bestehende Regeln (#1944, #3549) decken nur Git | Prozesslücke | mittel | SURVIVES (Skeptiker 11, 3b verstärkt) | Board-Seite: 20 Schreibzugriffe der Parallelsitzung, 1 Anhang dieser Sitzung (13:38Z); [#3977](https://github.com/achimdehnert/platform/issues/3977) mit Owner-Zitat | neu: parallel-session-shared-external-target |
| 5 | Die Gutschriften wurden per Roh-`saveVoucher` und `bookAmount` angelegt; `beleg_entwurf.py --strikt` kennt nur `creditDebit C`, ein Gutschrift-Pfad fehlt. Damit gibt es zwei Schreibpfade für Belege, die Striktprüfungen greifen nur auf einem | Werkzeug | niedrig | SURVIVES (Skeptiker 10) | `git show origin/main:tools/sevdesk/beleg_entwurf.py` Z. 668 `"voucher[creditDebit]": "C"`; Scratchpad-Skript `<lieferant>_gutschrift.py` | neu: zweiter-schreibpfad-ohne-strikt |
| 6 | Drei gleich hohe Abbuchungen wurden drei Belegen per Reihenfolgeannahme zugeordnet (aufsteigende Rechnungsnr. ↔ aufsteigende Bankreferenz); kein Datenfeld verbindet beide. Das Board legt die Annahme offen, die Wirkung beschränkt sich auf die Verknüpfung | verfrühte Festlegung | niedrig | SURVIVES (Skeptiker 9) | GET Mandant IIL: Bankreferenzen und Beleg-Transaktionscodes ohne gemeinsames Feld; Docstring des Nachtrags-Skripts | neu: gleichbetraege-zuordnung-per-reihenfolge |
| 7 | `zahlungsabgleich.buchen` und `kostenabgleich.buchen` schreiben als Zahlungsdatum den Parameter `heute` (Systemdatum), nicht die Valuta; die Sitzung umging das per Hand-Datum in den Skripten | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `git show origin/main:tools/sevdesk/zahlungsabgleich.py` / `kostenabgleich.py` (`"date": _dd_mm_yyyy(heute)`); verankert in [#3976](https://github.com/achimdehnert/platform/issues/3976) | neu: buchungsdatum-systemdatum-statt-valuta |
| 8 | Erste Sammelbuchung mit `FULL_PAYMENT` → 422; die Regel „Sammeleingang = Typ N" stand nicht im Werkzeug. Die Probe an einer Rechnung fing es ab, geschrieben wurde nichts | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Transkript-Kennzahlen 13:55Z (422); Board `buchungen` Zeile Sammeleingang; verankert in #3976 | neu: sevdesk-regel-erst-in-prod-sichtbar |
| 9 | Vermeidbare Fehlläufe: Tracebacks bei Werkzeug-Aufrufen (`FileNotFoundError` 08:10Z, `TypeError: 'Response'` 13:00Z), `--help` erst nach dem Fehler (10:34Z), `sleep` trotz Hook-Verbot (08:22Z) | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `scratchpad/retro_kennzahlen.txt`: 15 Fehlerläufe, 5 Ablehnungen | neu: tool-api-unverified-before-call |
| 10 | Docs-PR #3948 unter dem Owner-Konto eröffnet statt über die App `lotse-autor`; der Owner-Approve scheiterte (07:28:40Z, „Owner kann eigenen PR nicht approven"), PR geschlossen und als #3949 neu eröffnet. Kostete einen Owner-Klick. Rückfall auf die 🌀-Memory „Code-Owner-Review über App lotse-autor"; der Hinweis-Hook dazu war noch nicht gemergt (#3943, 08:05Z) | Wissenslücke | mittel | SURVIVES (kommandobelegt; Ursache per 3b korrigiert, vorher „Grund nicht ableitbar") | #3948 created 07:21:14Z, Schließkommentar 07:28:51Z, Selbstaussage 07:29:05Z; #3949 merged 07:33:09Z; `gh pr view 3943 --json mergedAt` = 08:05:10Z | pr-autor-identitaet-nicht-angewandt |
| 11 | Für eine Kundenrückzahlung legte die Sitzung auf Owner-Wort den bezahlbaren sevdesk-Beleg an (13:38Z), ohne die vorhandenen Zahldateien (SEPA, GiroCode) der Parallelsitzung stillzulegen; einzige Absicherung war ein Chat-Satz. Rund 18 min lagen zwei ausführbare Zahlwege für denselben Betrag vor, die Umbenennung auf `*.NICHT-NUTZEN` machte die Parallelsitzung (13:56:45Z) | Kommunikation | mittel | SURVIVES (3b: vom Skeptiker zu früh verworfen, die Zahldateien stammen von der Parallelsitzung, der zweite Weg von dieser) | Transkript 13:30:28Z, 13:36:29Z (Owner-Wort), 13:37:50Z, 13:38:09Z (Beleg angelegt), 13:38:44Z (Board-Item); Tool-Aufruf der Parallelsitzung 13:56:45Z; GET Beleg: Status 150, `paidAmount` 0 | neu: zweiter-zahlweg-ohne-stilllegung |
| 12 | Sitzung deutete „erledigt" als Bank-Freigabe und trug es als Fakt ins Board | Kommunikation | mittel | REFUTED (Skeptiker 2: Board-Eintrag 13:52:24Z und Korrektur 13:56:45Z von der Parallelsitzung; 3b bestätigt) | — | — |
| 13 | Buchungen mit Abweichung von Vorlage bzw. Rechnung (0 % statt 19 %, Cent-Rundung, Reverse Charge, ohne PDF) ohne erneute Vorlage | fehlende Validierung | mittel | REFUTED (Skeptiker 4: Belege von der Parallelsitzung angelegt, 12:54–13:01Z; 3b bestätigt) | — | — |
| 14 | Offene Owner-Gates („RE go", Reverse-Charge-Frage, netcup) nur auf lokalem Board ohne Issue | Prozesslücke | mittel | REFUTED (Skeptiker 5: diese Punkte gehören der Parallelsitzung; der eigene Rest steht in #2) | — | — |
| 15 | „Offensichtlich klar" selbst definiert und ohne Vorschau gebucht | verfrühte Festlegung | niedrig | REFUTED (Skeptiker 6: Owner delegierte die Auswahl; Kriterium angekündigt, Analyse zuerst lesend, Probe vor dem Rest) | — | — |
| 16 | IDs, Beträge, Daten hartkodiert in den Buchungsskripten | Werkzeug | niedrig | REFUTED (vor Phase 3: die Regel „Kein Hardcoding" gilt für Repo-Code; einmalige Buchungsskripte im Scratchpad tragen Falldaten, kein Fachwissen; der Bedarf an einer Eingabedatei ist in #2 enthalten) | — | — |
| 17 | Die Sitzung erklärte eine Memory-Notiz der Parallelsitzung als „nicht angelegt … deshalb nicht angefasst" (12:48:07Z) und änderte sie 10 s später per `sed -i` (12:48:17Z); die Parallelsitzung hatte dieselbe Stelle schon ersetzt. Zweiter Fall zu #4, diesmal im geteilten Memory-Ordner | Prozesslücke | niedrig | SURVIVES (3b NEU, kommandobelegt) | Transkript 12:48:07Z, 12:48:17Z (`sed -i` auf die Notiz), 12:48:21Z (Kollision gemeldet) | parallel-session-shared-external-target |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Aufträge erledigt und nachgeprüft; offen bleiben die 11er-Abbuchungen ohne Beleg (#2) und die Zahlung der Rückzahlung (#11) |
| architektur_design | 3 | Korrekturlogik und Gutschrift-Pfad als Ad-hoc-Skripte neben dem Werkzeug (#2, #5) |
| code_konventionstreue | 4 | PR-Titel und Commits im Format, `make test`; ein PR unter falscher Identität (#10) |
| risiko_debt | 3 | Zuordnungs- und Datumslücke im Werkzeug bestehen fort, beide jetzt verankert (#1, #7) |
| prozess_effizienz | 3 | Zwei Sitzungen an denselben Zielen ohne Eigentümer, vermeidbare Fehlläufe (#4, #17, #9) |
| entscheidungsqualitaet | 3 | Probe-zuerst und Summenprobe tragfähig; Gutschrift ohne eigenes go, zweiter Zahlweg ohne Stilllegung (#3, #11) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Zuordnung prüft nur Umsatz→Beleg, Nachprüfung nur Status | `zuordnen_position` paart beidseitig eindeutig nach kleinstem Datumsabstand, Gleichstand → „unsicher"; Test mit Doppel-Abo (#3982) | #1 |
| Korrekturlogik nur im Scratchpad, offene Abbuchungen nur auf dem Board | Im selben Turn ein Issue mit Soll (Logik aus `klar_abgleich.py`) und der Liste offener Abbuchungen | #2 |
| Gutschrift auf „habe ich auch <PDFs>" gebucht | Neuer Schreibpfad oder neue Belegart: Vorschau + eigenes Kürzel abwarten, auch wenn ein früheres „verbuche" vorliegt | #3 |
| Zwei Sitzungen schreiben ohne Eigentümer in Mandant und Board | Vor dem ersten Schreibschritt auf ein externes Ziel die Tages-Board-Seite lesen und Eigentümer eintragen; Mechanik nach #3977 | #4 |
| Gutschrift per Roh-`saveVoucher` | `beleg_entwurf.py` um `creditDebit D` erweitern, Gutschriften nur mit `--strikt` | #5 |
| Gleiche Beträge nach Reihenfolge verknüpft | Bei austauschbaren Positionen das Merkmal suchen (Transaktions-ID in Zweck/Referenz); ohne Merkmal im Beleg „Zuordnung austauschbar" vermerken | #6 |
| Zahlungsdatum = Systemdatum | `buchen` übernimmt `valueDate` des Umsatzes; Test „Zahlungsdatum = Valuta" (#3976) | #7 |
| 422 erst an der echten Buchung | Typwahl im Werkzeug aus der Zahl der Rechnungen je Eingang ableiten; Fake wirft 422 bei `FULL_PAYMENT` mit Differenz (#3976) | #8 |
| Werkzeug-Aufruf vor `--help` | Vor dem ersten Aufruf eines Moduls Signatur bzw. `--help` lesen | #9 |
| PR unter Owner-Konto, Approve scheitert, Neueröffnung | Governance-/Skill-PRs per `gh_app_token` als `lotse-autor` eröffnen; seit #3943 warnt der Hinweis-Hook davor | #10 |
| Zweiter Zahlweg angelegt, erster nur per Chat-Satz entwertet | Wer einen Zahlweg anlegt, legt im selben Schritt die übrigen still (Umbenennen oder Board-Zeile „ungültig") und prüft danach, dass genau einer ausführbar ist | #11 |
| Fremde Memory-Notiz per `sed -i` geändert | Fremde Memory-Dateien nur lesen; Änderungswunsch als Board-Zeile an die Eigentümer-Sitzung bzw. nach #3977 | #17 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py`: 67 Slugs mit Zähler ≥2, davon 8 ohne Gate. Aus dieser Retro sind
zwei Slugs wiederkehrend:

- `deferred-item-no-tracking-issue` steht unter `docs/governance/gates/declined/` (bewusst ohne Gate). Das verwandte Gate `aufschub-anker` prüft PR-Texte und Issue-Kommentare, nicht Board-Seiten (siehe `gates_verwandt`).
- `pr-autor-identitaet-nicht-angewandt` (zuerst Retro e50644) hat ein gebautes Gate, siehe 5a.

Alle übrigen Slugs sind neu (Zähler 1). `refuted_rate` 0,29 liegt im gesunden Band (zuletzt
0,16–0,55).

MEMORY-Abgleich: `grep -i "board" MEMORY.md` zeigt keine Regel zum Lesen geteilter Board-Seiten vor
einem Schreibschritt; die sevdesk-Regeln (Unterindex Finanzen) decken Freigabe und
Erstbuchungs-Probe, nicht die Zuordnungsrichtung. Die 🌀-Memory zum Code-Owner-Review über
`lotse-autor` existiert (Index-Zeile „platform-Ruleset: Code-Owner-Review") und wurde in #10 nicht
angewandt.

### 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` mit diesem Report: Die vier rückfälligen Gates sind dieselben wie in §0.0 und
bereits entschieden. Aus dieser Sitzung zählen `claim-before-cheapest-check` und `aufschub-anker` als
**gefangen**. `aufschub-anker` bleibt `wirksam` (0 Rückfälle), ebenso `parallel-session-pr-collision`.
Die Befunde #2, #4 und #17 liegen außerhalb des Zuschnitts dieser beiden Gates (`gates_verwandt`) und sind
kein Rückfall. Häufen sich solche Fälle, ist #3977 der Ort für den erweiterten Zuschnitt (externe Schreibziele).

`pr-autor-identitaet-nicht-angewandt` (Hinweis-Hook, `built` 2026-10-13) zählt mit #10 einen Rückfall
nach Bau. Das Vorkommen (#3948, 07:21Z) lag aber vor dem Merge des Hooks (#3943, 08:05Z). Das Gate hat
also nicht versagt, es war noch nicht in Betrieb. `gate_wirkung.py` führt es als `zu-frueh`. Das heißt ungeprüft, nicht wirksam. Mit einem Vorkommen ist das Gate nicht `RUECKFAELLIG`, eine Konsequenz folgt daraus nicht.
Ein zweites Vorkommen nach 08:05Z wäre der Befund „Gate rückfällig". Ein zweites Gate unter neuem Namen gibt es nicht.

### 5b. Autonomie-Kalibrierung

- **over_act** `externe-buchung-ohne-eigenes-kuerzel` (#3): Buchung in sevdesk auf ein Owner-Wort ohne „go".
- **kein over_act** bei #11: Den Rückzahlungsbeleg hatte der Owner ausdrücklich beauftragt; der Mangel ist die fehlende Stilllegung, nicht die Handlung.
- **over_ask:** keiner. Die Umhängung der Juni–August-Belege wurde vorgelegt („SC go"). Das war richtig, denn sie hob Buchungen einer früheren Sitzung auf.

## 6. Verankerung (Vorschläge, nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: geteiltes-board-vor-schreibschritt-lesen
description: Vor dem ersten Schreibschritt auf ein externes Ziel (sevdesk, Postfach, Zahldatei) die Tages-Board-Seite ganz lesen
metadata:
  type: feedback
---
Vor dem ersten Schreibschritt in sevdesk, ein Postfach oder eine Zahldatei die Board-Seite des Tages zum selben Ziel ganz lesen; Gates einer anderen Sitzung (Kürzel) gelten mit. Fremde Memory-Dateien nur lesen.
**Why:** Retro 327837 #3/#4/#17 — Gutschrift gebucht, deren Kürzel die Parallelsitzung verlangt hatte; fremde Memory-Notiz überschrieben.
**How to apply:** `ls ~/.claude/boards/*<datum>*` → passende Seite lesen, bevor gebucht wird; bis #3977 gebaut ist.
```

```markdown
---
name: zweiter-zahlweg-erst-stilllegen
description: Wer einen Zahlweg anlegt, legt die übrigen für denselben Betrag im selben Schritt still
metadata:
  type: feedback
---
Beim Anlegen eines Zahlwegs (sevdesk-Beleg, SEPA-Datei, GiroCode) alle anderen Wege für denselben Betrag im selben Schritt stilllegen (Umbenennen, Board-Zeile „ungültig") und prüfen, dass genau einer ausführbar ist. Ein Chat-Satz reicht nicht.
**Why:** Retro 327837 #11 — 18 min zwei ausführbare Wege für eine Kundenrückzahlung.
**How to apply:** `ls ~/zug/` und Board nach dem Betrag durchsuchen, bevor der neue Weg gemeldet wird.
```

**adr_candidates:** keiner. Die Eigentümer-Regel für externe Schreibziele ist als Zielzustand
[#3977](https://github.com/achimdehnert/platform/issues/3977) gefasst; ob daraus ein ADR wird,
entscheidet sich dort.

## 7. Maßnahmen

- **[R1]** ✅ Issue Abgleich beidseitig · platform · angelegt — https://github.com/achimdehnert/platform/issues/3982
- **[R2]** 🟢 Memory Board und Zahlweg · platform · Owner „R2 go" — https://github.com/achimdehnert/platform/issues/3977
- **[R3]** 🟢 Gutschriften nachträglich bestätigen · platform · Owner „R3 go" — https://github.com/achimdehnert/platform/issues/3977
- **[R4]** ✅ #3977 um Memory-Ordner ergänzt · platform · kommentiert — https://github.com/achimdehnert/platform/issues/3977#issuecomment-6171130694
- **[R5]** 🔵 #3976 umsetzen · platform · nach „S2b go" — https://github.com/achimdehnert/platform/issues/3976

## 8. Nicht verifiziert (Restlücken)

- Offen ist, ob auf dem EDV-Konto genau ein Abgang für die Kundenrückzahlung ankommt. Weil bis 13:56Z eine SEPA-Datei ausführbar war, wäre ein zweiter Abgang eine Doppelzahlung. Der Beleg steht auf Status 150. Billigster Check: ab 15.10. `GET /CheckAccountTransaction` auf dem EDV-Konto mit dem Rückzahlungsbetrag.
- Ungemessen ist, ob die Läufe vom 13.09. das Zahlungsdatum auf das Systemdatum gesetzt haben. Billigster Check: die Felder `payDate` der Belege vom 13.09. gegen `valueDate` vergleichen.
- Unklar ist, ob die Secret-Leak-Guard-Treffer (12:38Z, 13:00Z) vom Gate `secret-leak-via-safe-pattern` kamen. Sie stehen deshalb nicht in `gates_caught`. Billigster Check: Hook-Name im Transkript-Treffer.
- Die Diffs von #3953, #3954 und iil-pet-portal#58 hat kein Finder inhaltlich bewertet. 3b hat sie nur auf Personendaten durchsucht, ohne Treffer.

**getan:** 3 Finder, 1 Skeptiker über 11 Bewertungsbefunde, Phase 2.5 (Zuordnung zur Parallelsitzung per Transkript-Tool-Aufrufen), Widerlegungsbahn (Opus), Längsschnitt, Wirkungsbilanz, Anker-Issue #3982.
**angenommen:** Board-Einträge der Sitzung spiegeln die Buchungen. Die Status 1000/400 wurden je Ausgleichsbuchung in der Sitzung per GET geprüft.
**nicht verifizierbar:** ob „habe ich auch <PDFs>" vom Owner als Buchungsauftrag gemeint war (#3).
**offen geblieben:** Abgang der Kundenrückzahlung, Altbuchungen vom 13.09. auf Datum, 11er-Abbuchungen ohne Beleg (#3982).

## Widerlegung

Widerlegungsbahn (Opus, frischer Kontext, Report-Entwurf + Artefaktliste): **2 gekippt, 2 neu.**

| Punkt | Verdikt | Beleg |
|---|---|---|
| #1–#3, #5–#9 | BESTAETIGT | #3 nachgeprüft: 0 Tool-Aufrufe auf die Board-Seite und 0 Treffer „K3m" vor 13:19Z |
| #4 | BESTAETIGT, verstärkt | die Sitzung schrieb selbst in geteilte Ziele (#11, #17) |
| #10 | GEKIPPT | Ursache stand im Transkript (Schließkommentar 07:28:51Z): falsche PR-Identität, Rückfall auf 🌀-Memory; neu gefasst |
| #11 | GEKIPPT | den zweiten Zahlweg hat diese Sitzung angelegt (13:38:09Z), die Stilllegung machte die Parallelsitzung; jetzt SURVIVES |
| §1 „alle Buchungen 1000/400", „Entlastet" | Folge von #11, kein eigener Punkt | der Rückzahlungsbeleg steht auf 150; §1 neu gefasst |
| #12–#16 | BESTAETIGT | Board-Korrektur und Stilllegung per Tool-Aufruf bei der Parallelsitzung |
| Datenschutz im Report-Entwurf | NEU | der Entwurf nannte einen Lieferanten des Mandanten und Abo-Beträge. Ersetzt durch Platzhalter, Kontrollprobe siehe unten. PR-Texte, Diffs und Issues der Sitzung sind ohne Treffer. |
| Memory-Notiz der Parallelsitzung überschrieben | NEU | als #17 aufgenommen |
| Mail-Ablage im Zielkontext (#3972) | BESTAETIGT, kein Befund | echter Lauf 12:47:03Z nach Merge, Posteingang 51→40, offene Mails geschützt |

**Kontrollprobe Datenschutz:** Gesucht wurde nach Lieferantennamen, Abo-Beträgen, Rechnungsnummer und Beleg-ID des Mandanten. Roh 6 Zeilen mit Treffer, bereinigt 0 (`grep -ciE` vor dem Commit).

## Self-Review

Meta-Agent (sonnet, Report + Skill): Belege #1, #5, #7, #10 und die Issues unabhängig bestätigt. Invariante 12 = 12, Frontmatter rechnerisch konsistent, `refuted_rate` im Band, Datenschutz ohne Treffer. Zwei Befunde am Report:

- **(a)** Die Widerlegungs-Tabelle führte die §1-Korrektur als eigenes GEKIPPT. Das stand im Widerspruch zu „2 gekippt", die Zeile ist jetzt als Folge von #11 gekennzeichnet.
- **(b)** „`aufschub-anker` ist `zu-frueh`, nicht `wirksam`" ist widerlegt: `gate_wirkung.py` im Worktree, also mit diesem Report, führt das Gate als `wirksam` (4 Fänge, 0 Rückfälle). Der Meta-Agent las vermutlich den Stand ohne diesen Report.

Die Transkript-Belege der Befunde #10, #11 und #17 hat nur die Widerlegungsbahn gezogen, nicht der Meta-Agent.

## Streichbahn

Kein Streichkandidat. Beide teuren Bahnen haben hier gewirkt. Der Skeptiker kippte 5 Bewertungsbefunde, die nachweislich die Parallelsitzung ausgeführt hatte. Die Widerlegungsbahn holte einen davon mit Tool-Aufruf-Beleg zurück und fand den Datenschutzfehler im eigenen Entwurf.
