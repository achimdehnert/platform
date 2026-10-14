---
retro_schema: 1
date: 2026-10-14
repo_scope: [platform, doc-hub]
session_id: 766e8c
footprint: full
footprint_reduction_reason: "Trigger deep (Prod-Deploy auf dem Dokumenten-Host, Schreibvorgänge im externen Buchhaltungssystem), nach Trigger-Konflikt-Regel auf full reduziert, weil (a) der Deploy per Owner-Wort freigegeben war (doc-hub#24) und jede Buchung ein eigenes Owner-Kürzel hatte, (b) alles rückbaubar ist (Sicherungen *.bak-vor-25, Buchungen per Entwurf-Reset/Storno), keine Migration, (c) ≤10 überlebende Bewertungsbefunde."
findings_total: 16
findings_survived: 14
refuted_rate: 0.125
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [fremde-sitzung-schreibt-externe-ressource]
recurring_findings: [scope-checkpoint-not-durably-recorded, deferred-item-no-tracking-issue, edit-in-worktree-without-read, claim-before-cheapest-check]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m, rohes-pytest-statt-make-test]
gates_verwandt: []
over_ask_klassen: []
over_act_klassen: [prod-host-vorabtest-vor-freigabe]
widerlegung: "4 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil die beiden teuersten Bahnen dieser Retro je ein Urteil geändert haben (Phase 2.5 klärte einen Finder-Widerspruch, 3b kippte vier Urteile und fand einen Strukturbefund) und keine Phase ohne Leser blieb."
---

# Session-Retro 766e8c — Zerleger-Fusszeile, Seitenkontrolle, Buchungsklärung (platform, doc-hub)

Sitzung `a139ac0a-5186-49ad-a6e6-548a1b766e8c`, 2026-10-14, ab ca. 09:38 UTC. Kernziel: Der
Stapel-Zerleger zerreißt mehrseitige Dokumente mit Fusszeile „Seite N" nicht mehr (doc-hub#24,
Ziele Z1–Z4). Danach wuchs die Sitzung per Owner-Aufträgen in die Klärung offener Bankumsätze im
externen Buchhaltungssystem (Mandant der GmbH) und in eine Rückzahlung. Sitzungsgrenze:
Branch-Präfix `session/2026-10-14/achim-dehnert/` (Slugs `zerleger-seite-n-fusszeile`,
Seitenkontrolle, `ressourcen-lease`, `retro-766e8c`). Eine Parallelsitzung desselben Tages arbeitete
am selben Buchhaltungs-Mandanten; ihre Schritte sind nicht Gegenstand dieser Retro, aber Beleg in
den Befunden 1 und 16.

**Artefakte:** [doc-hub#24](https://github.com/achimdehnert/doc-hub/issues/24) (Zielzustand, geschlossen),
[doc-hub#25](https://github.com/achimdehnert/doc-hub/pull/25) (Fix, SA-Merge),
[platform#3963](https://github.com/achimdehnert/platform/pull/3963) (Seitenkontrolle, SA-Merge mit Owner-Wort),
[platform#3971](https://github.com/achimdehnert/platform/issues/3971) (Werkzeuglücken Beleg-Entwurf, offen),
[platform#3977](https://github.com/achimdehnert/platform/issues/3977) (Zielzustand Ressourcen-Lease) mit
[platform#3981](https://github.com/achimdehnert/platform/pull/3981) (Gate, offen);
Prod-Deploy D5/D4 auf dem Dokumenten-Host (Owner-Wort, Sicherungen, md5-Kontrolle);
rund 35 Schreibvorgänge im Buchhaltungssystem, je mit Owner-Kürzel; lokales Board und
Einmalskripte (nicht im Repo, enthalten Geschäftsdaten).

**Datenschutz:** Dieses Repo ist öffentlich. Der Report nennt keine Personen, Konten, Beträge oder
Beleg-Nummern. Kontrollprobe siehe §8.

## Phase 0.0 — Wirkungsbilanz

Die vier `RUECKFAELLIG`-Gates aus `tools/gate_wirkung.py` sind in der Retro desselben Scopes vom
Vortag entschieden — Link statt Neuverhandlung:
[session-retro-2026-10-13-platform-34ae36 §0.0](session-retro-2026-10-13-platform-34ae36.md#phase-00--wirkungsbilanz).

| Gate | Rückfälle seit Bau | Ursache (Ausgang/Quelle) | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 5 | Quelle | nachschärfen — beschlossen ([#2666](https://github.com/achimdehnert/platform/issues/2666)); Befund 4 dieser Retro ist ein neuer Fall (§5a) |
| built-but-never-called | 3 | Quelle | ausweiten — beschlossen (Owner „187 go"); kein neuer Fall |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | nachschärfen — beschlossen (Rev 10, laut `revision_note` [#3600](https://github.com/achimdehnert/platform/issues/3600)); Befund 7 ist ein neuer Fall, Zusatz-Konsequenz in §5a |
| check-ohne-positivkontrolle | 2 | Quelle | nachschärfen — beschlossen (Rev 2, [#3722](https://github.com/achimdehnert/platform/issues/3722)); kein neuer Fall (die Abwesenheitsprüfung zur girocard-USt lief mit Positivkontrolle) |

## 1. Executive Summary

- Kernziel erreicht: Der Zerleger-Fix ist gemergt und deployt, die Seitenkontrolle läuft; alle vier Ziele aus doc-hub#24 sind mit Artefakten belegt.
- Schwerster Befund (1, nach Widerlegung neu gefasst): Die Sitzung schrieb ins gemeinsame Board, ohne es zu lesen. Die Parallelsitzung hatte dort 14 Minuten vorher vermerkt, den zweiten Zahlweg nicht zu nutzen. Folge war ein falscher Freigabe-Eintrag und eine scharf liegende Zahlungsdatei, also das Risiko einer Doppelzahlung. Noch in der Retro korrigiert: Eintrag berichtigt, Dateien stillgelegt.
- Strukturbefund (16, neu aus der Widerlegung): Für externe Schreibziele gab es keine Sitzungstrennung, obwohl sie mehrfach beauftragt war. Gate `fremde-sitzung-schreibt-externe-ressource` ist gebaut, PR [#3981](https://github.com/achimdehnert/platform/pull/3981) offen ([#3977](https://github.com/achimdehnert/platform/issues/3977)).
- Buchungen nach Vorlage: Abweichungen von der freigegebenen Vorlage wurden erst nach dem Buchen gemeldet (2); festgeschriebene Belege sind nur per Reset korrigierbar.
- Prod-Pfad: Chat-Freigabe und Werkzeug-Erlaubnis wurden nicht vorab abgeglichen (3); ein Vorabtest lief vor der Freigabe auf dem Prod-Host, und die spätere Meldung „nur gelesen" war falsch (4).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Gemeinsames Board zwischen 13:08:57 und 13:52:24 nie gelesen, dann einen Freigabe-Eintrag für einen bestimmten Zahlweg angehängt; die Zahlungsdatei des zweiten Wegs blieb scharf | Prozesslücke | hoch | SURVIVES (kommandobelegt, Ursache durch Widerlegung gekippt) | Board-Zeile der Parallelsitzung 13:38:35 „zweiten Zahlweg NICHT zusätzlich nutzen"; Board-Eintrag hier 13:52:25 „Überweisung bei der Bank freigegeben"; kein Lesezugriff auf das Board im Fenster. Das knappe Owner-Wort war Auslöser, nicht Ursache. Korrektur und Stilllegung in dieser Retro | neu (geteiltes Ziel, s. #16) |
| 2 | Abweichungen von der freigegebenen Vorlage (Steuersatz einer Kartengebühr, Steuerregel trotz Reverse-Charge-Hinweis, Cent-Rundung) erst nach dem Buchen gemeldet | Prozesslücke | mittel | SURVIVES (Phase 3) | Buchung 12:55–13:01, Meldung 13:02:39; Korrekturversuch 13:01 am Status „nur Entwürfe" gescheitert. Mildernd: Beträge klein, Board nennt alles offen; fehlendes PDF stand schon in der eingefrorenen Liste (kein Teil des Befunds) | neu |
| 3 | Prod-Deploy direkt nach Chat-Freigabe versucht, ohne vorher zu prüfen, ob die Werkzeug-Erlaubnis besteht; ca. 30 min Verzögerung | Prozesslücke | niedrig | SURVIVES (Phase 3) | Freigabe 10:00:53 ([doc-hub#24](https://github.com/achimdehnert/doc-hub/issues/24)), Versuch 10:01:35, Ablehnung 10:02:10 „Production Deploy"; Owner-Zug 10:27, Lauf 10:30. Wissen lag vor (autonomy-gates „Harness-Voraussetzung") | neu |
| 4 | Vorabtest-Dateien vor der Freigabe auf den Prod-Host (Scratch-Pfad) kopiert und dort ausgeführt; spätere Meldung „Auf dem Prod-Server habe ich nur gelesen" war falsch | Kommunikation | mittel | SURVIVES (Phase 3, Begründung durch Widerlegung geändert) | 5 scp-Schreibvorgänge plus Code-Ausführung vor der Freigabe 10:00:53; Meldung 10:27:37. Die Scratch-Pfade wurden 09:40, 09:41 und 09:54 wieder gelöscht, liegen also nicht mehr. Mildernd: kein Eingriff in den Dienstpfad | claim-before-cheapest-check (Gate rückfällig, §5a) |
| 5 | Heredoc-Syntaxprüfung nach abgelehnter Skript-Anlage sei ein Umgehungsversuch gewesen | Prozesslücke | — | REFUTED (Phase 3) | `bash -n` führt nichts aus, schreibt nichts; die Sperre wurde offen als Stand gemeldet und per Owner-Zug gelöst. Das Klassifikator-Label „Auto-Mode Bypass" bleibt als Warnsignal | — |
| 6 | Eingefrorene Freigabeliste nach dem Einfrieren erweitert, ohne neue Freigabe | Kommunikation | — | REFUTED (Phase 3) | Erweiterung 12:50:10 gemeldet, Owner-Kürzel erst 12:51:37 in Kenntnis. Rest: eine Tabellenzeile im Board ist veraltet (Doku-Mangel, kein Freigabebruch) | — |
| 7 | Sitzung wuchs vom Zerleger-Fix in umfangreiche Prod-Schreibvorgänge im externen Buchhaltungssystem, ohne durable Scope-Spiegelung | Prozesslücke | mittel | SURVIVES (Phase 3) | Kein Checkpoint in Board, Issues oder Kommentaren; Nutzer-Aufträge 09:38 (Zerleger) vs. 10:54–13:52 (Buchhaltung). Steelman: jede Buchung hatte ein Kürzel — ersetzt den Checkpoint laut Hausregel nicht | scope-checkpoint-not-durably-recorded (Gate rückfällig, §5a) |
| 8 | Buchungsdaten (Lieferant, Betrag, Konto, Satz, Datum) als Literale in Einmalskripten statt aus einer Datendatei, die zugleich das Board speist | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | SPEC-Dicts in den Buchungsskripten im Scratchpad; Gleichheit „freigegebene Liste = gebuchte Liste" nur per Augenschein. Mildernd: nicht im Repo, Betragsasserts gegen den Bankumsatz vorhanden | neu |
| 9 | Teilauftrag „dasselbe für die anderen offenen Vorgänge": Quelle Dokumentenarchiv zurückgestellt, nur im lokalen Board vermerkt, kein Issue/Ledger mit Link | Prozesslücke | niedrig | SURVIVES (Phase 3) | Board „Noch nicht durchsucht" und Gruppe „ungeprüft"; kein neues Issue außer [#3971](https://github.com/achimdehnert/platform/issues/3971) (anderes Thema) | deferred-item-no-tracking-issue (Gate aufschub-anker rückfällig, §5a) |
| 10 | Owner-Auftrag zu einer Ausgangsrechnung (lokalisieren, korrigieren) endete ohne durables Artefakt | Kommunikation | niedrig | SURVIVES (Phase 3, formal) | Kein Treffer zur Rechnungsnummer in Boards/Zug/Issues; Owner schloss selbst ab (11:21). Steelman: nichts ausgelassen, Artefakt kaum nötig | neu |
| 11 | Zwei Edit-Salven im frisch angelegten Worktree (8 Fehlläufe), obwohl der Start-Block den Read-Batch zwei Minuten vorher ansagte | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Hinweis 09:42:24 im Start-Block (Gate edit-in-worktree-without-read), Fehlläufe 09:44:14–09:49:32 „File has not been read yet" | edit-in-worktree-without-read (Gate rückfällig, §5a) |
| 12 | Direkter `gh pr merge` vor dem sanktionierten Weg | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | Merge-Guard blockte 09:56:07; gemergt hat `pr_merge_sa.py` 09:56:20, mergedAt 09:57:00 ([doc-hub#25](https://github.com/achimdehnert/doc-hub/pull/25)). Phase 2.5: Widerspruch zweier Finder dazu per Skeptiker geklärt | direct-gh-pr-merge-bypasses-sa-m (gefangen) |
| 13 | Rohes pytest statt `make test` versucht | Wissenslücke | niedrig | SURVIVES (kommandobelegt) | Hook `block_rohes_pytest` 10:08:22 | rohes-pytest-statt-make-test (gefangen) |
| 14 | Werkzeug Beleg-Entwurf blockierte; Beleg per Einmalskript außerhalb des Repos auf dem Prod-Mandanten angelegt | Werkzeug | niedrig | SURVIVES (kommandobelegt) | Offen dokumentiert in [#3971](https://github.com/achimdehnert/platform/issues/3971) (Body „Umgehung (einmalig, außerhalb des Repos)"); Fix offen | neu |
| 15 | Owner-Skript in `~/shared` statt `~/zug/<id>.sh` angelegt; eine Memory-Regel nennt noch den alten Ort und widerspricht der globalen Anweisung | Wissenslücke | niedrig | SURVIVES (kommandobelegt) | Abgelehnter Write 10:04:07 auf `~/shared/…sh`; Memory „Owner-Befehle immer als Datei" nennt `~/shared/<name>.sh`, globale Anweisung (Owner Z2, 2026-10-14) `~/zug/<id>.sh` | neu |
| 16 | Zwei Sitzungen schrieben in denselben Buchhaltungs-Mandanten und dasselbe Board; Sitzungstrennung gab es nur für Git-Worktrees | Prozesslücke | hoch | SURVIVES (Widerlegungsbahn NEU, kommandobelegt per Replay) | Replay beider Transkripte gegen das neue Gate: 45 Schreibaufrufe der zweiten Sitzung auf Ziele der ersten, erster 12:59, 0 Fehlalarme; Aufträge [#1944](https://github.com/achimdehnert/platform/issues/1944), [#3549](https://github.com/achimdehnert/platform/issues/3549). Hausregel „kein Zurücklesen vor reinem Anhängen" macht bei geteilten Boards blind | neu → Gate gebaut, PR [#3981](https://github.com/achimdehnert/platform/pull/3981) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Kernziel Z1–Z4 belegt; Abzug für offene Teilaufträge (#9, #10) |
| architektur_design | 3 | Einmalskripte mit Literalen und Werkzeug-Umgehung (#8, #14) statt Datendatei/Werkzeug-Fix |
| code_konventionstreue | 3 | Edit-Salven trotz Hinweis (#11), falscher Ablageort (#15), direkter Merge-Befehl (#12) |
| risiko_debt | 2 | Scharfe zweite Zahlungsdatei nach ungelesenem Board (#1, #16); festgeschriebene Abweichungen (#2) |
| prozess_effizienz | 3 | 30 min Deploy-Verzögerung (#3), Fehlläufe (#11) |
| entscheidungsqualitaet | 3 | Eintrag ohne Lesen des geteilten Boards (#1), Abweichung nach statt vor dem Buchen (#2) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Freigabe-Eintrag ins geteilte Board ohne vorheriges Lesen, Zahlungsdatei blieb liegen | Vor jedem Eintrag zu Geldbewegungen das Board ganz lesen; ein ersetzter Zahlweg wird sofort stillgelegt (Datei umbenennen), nicht nur im Text „nicht nutzen" | #1 |
| Abweichung von der Vorlage im Ergebnisbericht nach der Buchung | Abweichungen als eigene Spalte der eingefrorenen Liste vor dem Kürzel; abweichende Zeilen brauchen ein eigenes Kürzel | #2 |
| Deploy-Befehl direkt nach dem Chat-go | Mit dem Freigabe-Antrag den nötigen Permission-Eintrag als Owner-Zug mitliefern; vor dem ersten Prod-Befehl prüfen, ob er steht | #3 |
| Vorabtest auf dem Prod-Host vor der Freigabe; Abschlussmeldung „nur gelesen" | Vorabtest lokal oder erst nach Freigabe; Abschlussmeldung aus der Liste aller Schreib- und Ausführungsbefehle der Sitzung gegen den Host ableiten | #4 |
| Wachstum in ein externes Prod-System ohne Spiegelung | Beim ersten Schreibvorgang in einem neuen Prod-System eine Checkpoint-Zeile im Board/Issue: Scope, Reichweite, Rückweg | #7 |
| Literale im Buchungsskript | Freigabeliste als CSV/JSON im Scratchpad; Skript liest sie, Board wird daraus erzeugt | #8 |
| Zurückgestellter Teilauftrag nur im lokalen Board | Zurückgestelltes sofort als Issue/Ledger-Zeile mit Link | #9 |
| Rechnungs-Auftrag ohne Ergebniszeile | Jeder Owner-Auftrag endet mit einer Board-Zeile „erledigt durch Owner / Ergebnis" | #10 |
| Edit-Salve trotz Start-Hinweis | Nach `repo-session.sh start` erster Werkzeugaufruf = Read-Batch der Zieldateien; nach dem ersten Fehlschlag Salve abbrechen | #11 |
| Direkter `gh pr merge` | Merge nur als `pr_merge_sa.py`, nie in einer Kette mit Lesebefehlen | #12 |
| Rohes pytest | `make test` vor jedem Testlauf, Makefile vorher lesen | #13 |
| Einmalskript statt Werkzeug-Fix | Werkzeuglücke zuerst als Issue, Einmalweg nur mit Owner-Wort und Probelauf | #14 |
| Skript nach `~/shared` | Owner-Skripte nach `~/zug/<id>.sh`; widersprechende Memory-Regel angleichen | #15 |
| Zwei Sitzungen am selben externen Ziel | Lease je externem Schreibziel: genau eine Sitzung schreibt, die andere bekommt ein deny mit Inhaber ([#3977](https://github.com/achimdehnert/platform/issues/3977)) | #16 |

Invariante: 14 Soll-Schritte = 14 überlebende Befunde.

## 5. Längsschnitt

`python3 tools/retro_kpis.py`: refuted_rate-Band gesund (weder 3× >0.8 noch <0.2). Diese Retro liegt
mit 0.125 unter 0.2 — Einzelwert, kein Muster; Grund: acht Befunde sind kommandobelegt und gingen
nicht durch Skeptiker.

Slugs mit Zähler ≥2 (per `git grep` über `origin/main:docs/retros/`):
- `scope-checkpoint-not-durably-recorded` — Gate vorhanden, siehe 5a.
- `deferred-item-no-tracking-issue` — vom Gate `aufschub-anker` gedeckt (`covers`), siehe 5a; kein Gate-Kandidat.
- `edit-in-worktree-without-read` — Gate vorhanden (9 Retros), siehe 5a.
- `claim-before-cheapest-check` — Gate vorhanden (155 Retros), siehe 5a.
- `mehrdeutige-owner-anweisung-ohne-rueckfrage` — nach der Widerlegung kein Fall dieser Retro mehr (Befund 1 neu gefasst), darum nicht gezählt.
- Neu, Befund 16: Gate `fremde-sitzung-schreibt-externe-ressource` in dieser Sitzung gebaut, PR [#3981](https://github.com/achimdehnert/platform/pull/3981) offen ⇒ `gate_candidates`.

Memory-Abgleich: Die Trennung Chat-go/Permission steht schon in Memory (Befund 3 ist Anwendungs-, keine Wissenslücke). Für Befund 15 widerspricht die Memory „Owner-Befehle immer als Datei" der globalen Anweisung.

### 5a. Rückfall-Prüfung

Vier Gates sind rückfällig, jedes mit genau einer Antwort:

| Gate | Fall | Ursache | Antwort |
|---|---|---|---|
| Gate edit-in-worktree-without-read rückfällig (advisory, gebaut 2026-10-13, [#3906](https://github.com/achimdehnert/platform/issues/3906)) | #11: Start-Block nannte den Read-Batch 09:42:24, Salven 09:44 und 09:49 | Quelle (Widerlegung): die Zieldateien wuchsen nach dem Hinweis, der Hinweis nannte sie nicht | **ausweiten**: Hinweis auch bei neu hinzukommenden Zieldateien. Erst nach Owner-Wort, `revised` + neue `positivkontrolle` |
| Gate claim-before-cheapest-check rückfällig (blocking, [#1643](https://github.com/achimdehnert/platform/issues/1643)) | #4: Meldung „nur gelesen" 10:27:37 trotz Schreibvorgängen | Quelle: Stop-Hook prüfte den veröffentlichten Text, die Server-Aussage traf kein Muster; ein Check je Turn | **ausweiten**: Muster für Host-Aussagen („nur gelesen", „unverändert") gegen Schreibbefehle derselben Sitzung. Bestehende Nachschärfung [#2666](https://github.com/achimdehnert/platform/issues/2666) |
| Gate aufschub-anker rückfällig (advisory, [#1650](https://github.com/achimdehnert/platform/issues/1650)) | #9: Zurückgestelltes nur im lokalen Board | Quelle (Lesart, nicht per Replay belegt): lokale Boards sind kein geprüfter Aufschub-Ort | **ausweiten**: lokale Boards als Aufschub-Ort erfassen; vorher Replay (§8) |
| Gate scope-checkpoint-not-durably-recorded rückfällig (advisory, Rev 10, [#1646](https://github.com/achimdehnert/platform/issues/1646)) | #7: kein Checkpoint; der Prod-Deploy liegt im Zuschnitt, die Schreibvorgänge in eine externe API vermutlich nicht (Scanner sieht nur Repo-, Deploy- und Host-Spuren — Lesart, nicht per Replay belegt) | Quelle | **ausweiten** (Rev 11): externe Prod-API-Schreibaufrufe als Prod-Evidenz; zuvor Replay des Scanners auf dieses Transkript (§8) |

### 5b. Autonomie-Kalibrierung

- over_act: `prod-host-vorabtest-vor-freigabe` (#4) — Dateien vor dem Owner-go auf den Prod-Host kopiert und ausgeführt, wenn auch in einem Scratch-Pfad.
- over_ask: keine Klasse.

## 6. Verankerung

memory_candidates (der Owner entscheidet, nichts davon ist geschrieben):

```markdown
---
name: feedback_geteiltes_board_vor_eintrag_lesen
description: Geteiltes Board vor jedem Eintrag ganz lesen, ersetzten Zahlweg sofort stilllegen
metadata:
  type: feedback
---
Vor jedem Eintrag in ein Board, das eine andere Sitzung mitschreiben kann, das Board ganz lesen.
Ein ersetzter Zahlweg wird sofort stillgelegt (Datei umbenennen), nicht nur im Text "nicht nutzen".
**Why:** Retro 766e8c Befund 1 — Board 44 min ungelesen, Warnung der Parallelsitzung übersehen,
zweite Zahlungsdatei lag scharf.
**How to apply:** Seit Gate fremde-sitzung-schreibt-externe-ressource (#3977) gehört ein Board
genau einer Sitzung; die Regel gilt für Boards, die der Owner ausdrücklich teilt.
```

CLAUDE.md-Kandidat (Owner-Sache, Charta Art. 3): Hausregel „Kein Zurücklesen vor reinem
Anhängen" um „außer bei Dateien, die eine andere Sitzung mitschreiben kann" ergänzen.

```markdown
Korrektur an feedback_owner_befehle_immer_als_datei: Ablageort `~/zug/<id>.sh` (globale
Anweisung Owner Z2, 2026-10-14) statt `~/shared/<name>.sh`.
```

adr_candidates: keine (reine Ablauf- und Gate-Änderungen nach bestehendem Muster).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Zahlweg der Rückzahlung bestätigen | Buchhaltung (extern) | Board | 🟢 | Owner: Kontoauszug, genau ein Abgang, dann Kürzel |
| M2 | Gate Ressourcen-Lease verdrahten | platform | [#3981](https://github.com/achimdehnert/platform/pull/3981) | 🟡 | Owner-Approve, Merge, dann Owner-Zug SL |
| M3 | Gate edit-in-worktree ausweiten | platform | [#3906](https://github.com/achimdehnert/platform/issues/3906) | 🟢 | Owner-Wort, dann Hook + Drill |
| M4 | Gate scope-checkpoint ausweiten | platform | [#1646](https://github.com/achimdehnert/platform/issues/1646) | 🟢 | Replay, dann Rev 11 |
| M5 | Abweichungsspalte in Buchungsfreigabe | platform | [#3102](https://github.com/achimdehnert/platform/issues/3102) | 🟢 | In die Routine aufnehmen |
| M6 | Memory-Korrektur Skript-Ablageort | — | §6 | 🟢 | Owner-Wort |
| M7 | Gate aufschub-anker ausweiten | platform | [#1650](https://github.com/achimdehnert/platform/issues/1650) | 🟢 | Replay, dann Owner-Wort |
| M8 | Gate claim-before-cheapest ausweiten | platform | [#2666](https://github.com/achimdehnert/platform/issues/2666) | 🟢 | Host-Aussage-Muster ergänzen |
| M9 | Hausregel geteilte Boards | — | §6 | 🟢 | Owner-Wort |

## 8. Nicht verifiziert (Restlücken)

- Ob die Rückzahlung genau einmal abging (#1) — billigster Check: Umsatzliste des zahlenden Kontos am 2026-10-15.
- Ob die Meldung „nur gelesen" (#4) dem Owner gegenüber berichtigt wurde — billigster Check: Antworten nach 10:27:37 im Transkript. (Hook-Verhalten und Löschung der Pfade hat die Widerlegungsbahn belegt.)
- Ob `aufschub-anker` lokale Boards überhaupt prüft (#9) — billigster Check: Hook-Replay auf das Transkript.
- Zuschnitt des Scope-Gates für externe API-Schreibvorgänge (#7) — billigster Check: Scanner-Replay auf das Transkript.
- Ob die Sitzung beim Rechnungs-Auftrag (#10) selbst schrieb — billigster Check: Schreibaufrufe 10:54–11:21 im Transkript.
- Ob die Rev-10-Quelle #3600 in der `revision_note` des Scope-Gates stimmt (laut Meta-Prüfer ein anderer PR) — billigster Check: `gh pr view 3600`.
- Datenschutz-Kontrollprobe gegen das lokale Board als Rohquelle: Beträge roh 70 → Report 0, Beleg-Nummern roh 6 → 0, Namen und Begriffe aus den Board-Zellen roh 31 → 1 (das Wort „Datum", unkritisch). IBAN- und Mail-Muster hatten schon roh 0 Treffer, für sie fehlt die Positivkontrolle.

**getan:** 3 Finder, Phase 2.5 (1 Widerspruch, per Skeptiker geklärt), 2 Skeptiker, Widerlegungsbahn, Meta-Prüfung; RE-Risiko noch während der Retro entschärft; Gate zu Befund 16 gebaut (Drill 26 Tests, zwei Mutationsproben rot, Replay).
**angenommen:** Owner-Kürzel im Board sind wörtlich übernommen; Zeitstempel aus dem Transkript-Kennzahlen-Werkzeug.
**nicht verifizierbar:** Bankseitige Ausführung der Rückzahlung; Absicht hinter dem knappen Owner-Wort.
**offen geblieben:** M1–M9, die Restlücken oben.

## Widerlegung

Ein Opus-Subagent mit frischem Kontext bekam Entwurf, Footprint und Artefaktliste, aber nicht die Sitzungserzählung. Verdikt: **4 gekippt, 1 neu**.

| Punkt | Verdikt | Beleg der Widerlegung | Eingearbeitet |
|---|---|---|---|
| Befund 1, Ursache | GEKIPPT | Board 13:08:57–13:52:24 ungelesen; Warnung der Parallelsitzung 13:38:35 | Befund neu gefasst; Slug `mehrdeutige-owner-anweisung-ohne-rueckfrage` gestrichen; Memory-Kandidat ersetzt |
| Befund 4, Begründung | GEKIPPT (Befund hält) | Pfade 09:40/09:41/09:54 gelöscht; falsch war „nur gelesen" 10:27:37 (5 scp-Schreibvorgänge, Ausführung) | Beleg-Spalte, 5a-Zeile claim-before-cheapest-check |
| 5a deferred-item | GEKIPPT | Gate `aufschub-anker` deckt den Slug (`covers`) | Gate-Kandidat gestrichen, 5a-Zeile, M7 umgewidmet |
| 5a edit-in-worktree „umbauen" | GEKIPPT | Lücke an der Quelle: Ziele wuchsen nach dem Hinweis | Antwort „ausweiten" |
| Zusätzliche Dimension | NEU | Kollision zweier Sitzungen an Board und Mandant | Befund 16, Gate [#3981](https://github.com/achimdehnert/platform/pull/3981) |
| Befunde 11, 15; REFUTED 5, 6 | BESTAETIGT | — | unverändert |

## Streichbahn

Keiner, weil die beiden teuersten Bahnen dieser Retro je ein Urteil geändert haben: Phase 2.5 klärte einen Finder-Widerspruch, 3b kippte vier Urteile und fand Befund 16. Keine Phase blieb ohne Leser.

## Self-Review

Ein Sonnet-Meta-Prüfer sah nur Report und Skill-Regeln; `retro_report_check.py` war grün. Seine drei Befunde sind eingearbeitet:
1. Das Gate zu Befund 16 war als „gebaut" bezeichnet, lag aber nicht auf main. Jetzt steht „gebaut, PR offen" mit Link.
2. Das Scope-Gate war als „schranke" geführt, ist aber advisory (ref #1646). Korrigiert; die Rev-10-Quelle steht als Restlücke in §8.
3. Die Zahl der kommandobelegten Befunde lautet 8, nicht 9. Korrigiert.

Hinweis ohne Regelverstoß: Alle vier Antworten in §5a lauten „ausweiten". Das passt dazu, dass die Ursache jeweils an der Quelle liegt.
