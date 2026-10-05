# Vorschlag: sieben rückfällige Gates (Stand 2026-10-05)

> **Status: Entscheidungsvorlage, nichts umgesetzt.** Dieser PR ändert keinen Registry-Eintrag
> und kein Werkzeug. Der Owner entscheidet je Zeile (G1–G7); jede angenommene Zeile wird ein
> eigener Umsetzungs-PR, der durch `tools/gate_verankerung_check.py --neu` läuft.
> Anlass: Retro 2026-10-05 ([#3717](https://github.com/achimdehnert/platform/pull/3717)),
> Prozess-Befunde in [#3716](https://github.com/achimdehnert/platform/issues/3716).

## Messung

`python3 tools/gate_wirkung.py` über 151 Retros meldet sieben Gates als `RUECKFAELLIG`.
Die Zahlen „vor/nach" stammen aus diesem Lauf; die Fälle dahinter sind aus den
Befund-Tabellen der Retros seit dem jeweiligen Bau- oder Umbaudatum gelesen.

| ID | Gate | Modus | seit | vor | nach | gefangen | Frist |
|---|---|---|---|---|---|---|---|
| G1 | `untested-tool-module-green-gate` | advisory | 2026-09-07 | 11 | 4 | 0 | 2026-10-31 |
| G2 | `handover-stale-vor-merge` | process | 2026-09-24 | 24 | 3 | 0 | — |
| G3 | `check-ohne-positivkontrolle` | advisory | 2026-09-17 | 2 | 2 | 2 | 2026-10-31 |
| G4 | `melder-ohne-leser` | advisory | 2026-09-07 | 2 | 2 | 0 | 2026-10-31 |
| G5 | `parallel-session-pr-collision` | process | 2026-09-10 | 9 | 2 | 0 | — |
| G6 | `secret-leak-via-safe-pattern` | blocking | 2026-09-14 | 4 | 2 | 2 | — |
| G7 | `stale-local-clone-as-ground-truth` | advisory | 2026-09-03 | 10 | 2 | 2 | 2026-10-31 |

„Frist" ist das Feld `expires` der Registry: bis dahin „blocking oder gestrichen"
(Owner-Entscheid E4, [#2606](https://github.com/achimdehnert/platform/issues/2606)).

## Gemeinsamer Befund

Bei fünf der sieben Gates liegt die Ursache an der **Quelle**: Das Gate prüft eine Instanz,
der Name zählt eine ganze Familie. Die Rückfälle sind fast durchweg Fälle, die das Gate nach
seinem eigenen Zuschnitt gar nicht sehen kann (anderes Repo, anderer Zeitpunkt, andere Form).
Ein Fall, den das Gate nach seinem Zuschnitt hätte fangen müssen, ist nur bei G6 belegt und
bei G7 möglich. Das Urteil „rückfällig" misst hier also vor allem den Zuschnitt der Namen,
nicht das Versagen der Prüfungen.

## Vorschläge

### G1 `untested-tool-module-green-gate` — nachschärfen und scharf stellen

- **Fälle seit Umbau:** ein Modul mit Testdatei, dessen eigentlicher Transportweg in jedem
  Test ersetzt wird (2026-09-23); Tests eines Prototyps, die nur lokal laufen (dev-hub,
  2026-09-24); drei Auswertungs-Skripte ohne Selbsttest (robo-lab, 2026-10-04).
- **Ursache (Quelle):** Das Gate prüft nur neu hinzugefügte Module unter `tools/` und
  `scripts/` in diesem Repo. Keiner der Fälle ist ein solches Modul.
- **Vorschlag:** (a) Im eigenen Geltungsbereich von advisory auf blocking stellen — die
  Frist verlangt die Entscheidung ohnehin. Vorher die Fehlalarm-Zahl aus den letzten
  30 PR-Läufen ablesen; sie ist bisher **nicht gemessen**. (b) Die Fremd-Repo-Fälle als
  eigenen Kandidaten „Tests laufen nicht in der CI des Repos" führen, statt sie diesem Gate
  anzulasten. (c) „Testdatei vorhanden, Kernpfad ungetestet" nicht als Gate bauen — das
  wäre eine Abdeckungs-Schwelle und damit eine eigene Entscheidung.

### G2 `handover-stale-vor-merge` — Gate unverändert, Zählung und Geltung nachziehen

- **Fälle seit Umbau:** zwei Retros fanden einen veralteten Stand, **bevor** die Sitzung
  beendet war (2026-10-01, 2026-10-04); die Prüfung am Sitzungsende meldete den ersten
  davon selbst als veraltet. Ein echter Fall: Stand in einem Repo ohne Fragment-Modus war
  schon beim Schreiben inhaltlich überholt (meiki-hub, 2026-09-28).
- **Ursache:** zweimal Messzeitpunkt (Retro läuft vor dem Sitzungsende), einmal Quelle
  (inhaltliche Überholung ist am Zeitstempel nicht zu erkennen).
- **Vorschlag:** (a) Zählregel: ein Handover-Befund vor dem Sitzungsende gilt nur dann als
  Rückfall, wenn die Prüfung am Ende trotzdem grün war; sonst als gefangen. Das ist eine
  Änderung am Retro-Skill und wird nur vorgeschlagen. (b) Fragment-Modus in meiki-hub und
  robo-lab einführen: dort trägt jeder offene Punkt einen Issue-Link, und Erledigtes fällt
  von selbst heraus.

### G3 `check-ohne-positivkontrolle` — scharf stellen, Familie beim Nachbar-Gate ergänzen

- **Fälle seit Bau:** eine Zählung aus einer Suche ohne Gegenprobe in einer
  Entscheidungsvorlage (2026-09-23); ungeprüfte Annahmen über eine Staging-Umgebung und ein
  öffentlich geposteter Messfehler (meiki-hub, 2026-09-24). Zweimal gefangen.
- **Ursache (Quelle):** Das Gate liest nur Aufträge an Unter-Agenten. Die Rückfälle sind
  eigene Messungen der Sitzung.
- **Vorschlag:** (a) Den Auftrags-Prüfer auf blocking stellen: Die Bedingung ist mit einer
  Zeile im Auftrag erfüllbar. (b) „Zahl oder Null-Treffer aus einer Suche ohne Gegenprobe"
  beim bestehenden Gate `claim-before-cheapest-check` ergänzen, zusammen mit der dort
  offenen Ausweitung ([#2666](https://github.com/achimdehnert/platform/issues/2666)), statt
  ein drittes Gate zu bauen.

### G4 `melder-ohne-leser` — scharf stellen, Fremdfälle nicht mitzählen

- **Fälle seit Umbau:** ein Zeitplan-Dienst ohne Ausfallmeldung (2026-09-21) und eine
  Prüfliste ohne Leser in einem Nachbar-Repo (2026-09-23). Beide stehen nur in den
  Befund-Tabellen, beide außerhalb des Registers.
- **Messung heute:** `python3 tools/melder_register_check.py --kurz` meldet nichts, Exit 0.
  Beim Umbau am 2026-09-07 waren es 18 Melder ohne Leser. Am eigenen Prüfpunkt wirkt das
  Gate.
- **Vorschlag:** (a) Register-Prüfung auf blocking stellen — der Bestand ist sauber, ab
  jetzt hält sie nur den Zustand. (b) Die beiden Fremdfälle als „verwandt" führen und nicht
  als Rückfall dieses Gates zählen.

### G5 `parallel-session-pr-collision` — Prüfzeitpunkt ergänzen

- **Fälle seit Umbau:** zwei PR-Serien berührten dieselbe Datei (2026-09-14); zwei PRs
  lösten dasselbe Issue ohne Querverweis (dev-hub, 2026-09-28). Vor dem Umbau neun Fälle.
- **Ursache (Quelle, Zeitpunkt):** Die Liste offener PRs erscheint beim Start der Sitzung.
  Beide Kollisionen entstanden danach.
- **Vorschlag:** Dieselbe Liste zusätzlich beim Anlegen eines PR zeigen, beschränkt auf
  „gleiches Issue genannt" oder „gleiche Datei berührt". Weiter als Hinweis, nicht als
  Sperre: Parallele Arbeit an einer Datei ist oft gewollt.

### G6 `secret-leak-via-safe-pattern` — nachschärfen, bleibt blocking

- **Fälle seit Umbau:** ein echter Fall (2026-09-23, Ablaufverfolgung eines Kommandos, das
  Umgebungswerte ausgibt) und ein Fehlalarm (2026-09-24, ein Pfad stand nur im Text einer
  Notiz). Zweimal gefangen.
- **Ursache (Quelle):** Der Guard prüft Argumente bekannter Lese-Kommandos und erkennt
  Ablaufverfolgung nur beim Aufruf eines lokalen Skripts. Der Rückfall lief laut Retro über
  einen entfernten Aufruf; der Kopf des Guards nennt weitere unerkannte Formen.
- **Vorschlag:** (a) Ablaufverfolgung zusammen mit Kommandos sperren, die Umgebungswerte
  ausgeben; der Fall vom 2026-09-23 wird Positivkontrolle. (b) Text in eingebetteten
  Notizen von der Prüfung ausnehmen; der Fehlalarm vom 2026-09-24 wird Gegenprobe.

### G7 `stale-local-clone-as-ground-truth` — Drill ergänzen, dann über die Frist entscheiden

- **Fälle seit Umbau:** ein Werkzeuglauf maß den lokalen Arbeitsbaum statt des gemeinsamen
  Stands und berichtete „wirksam" (2026-09-23); eine Suche in fremden lokalen Klonen fand
  nichts, der gemeinsame Stand hatte die Stelle (meiki-hub, 2026-09-24). Einer der beiden
  gezählten Rückfälle stützt sich auf einen Befund, den die Retro selbst verworfen hat.
  Zweimal gefangen.
- **Ursache:** offen. Die Prüfung für fremde Klone ist seit 2026-09-03 verdrahtet; warum
  sie am 2026-09-24 nicht meldete, ist **nicht geprüft**.
- **Vorschlag:** (a) Den Fall vom 2026-09-24 als Drill nachbauen. Meldet die Prüfung ihn,
  liegt die Ursache am Ausgang (Hinweis überlesen) und das Gate wird blocking; meldet sie
  ihn nicht, wird das Muster erweitert. (b) Werkzeuge, die Bilanzen berichten, lesen in der
  Voreinstellung den gemeinsamen Stand, nicht den Arbeitsbaum.

## Zählweise — eigener Punkt (G8)

`gate_wirkung.py` zählt einen Slug als Rückfall, sobald eine Retro ihn führt. Drei Arten
von Einträgen verzerren das Urteil: Fälle außerhalb des Geltungsbereichs des Gates, Befunde
vor dem Messzeitpunkt des Gates und verworfene Befunde. **Vorschlag:** In der Befund-Tabelle
der Retro je Rückfall-Zeile festhalten, ob das Gate den Fall nach seinem Zuschnitt sehen
konnte; nur diese Fälle zählen als Rückfall, die übrigen als „verwandt". Ohne diese
Trennung kommen dieselben sieben Zeilen in jeder Retro wieder.

## Nicht geprüft

- Fehlalarm-Zahlen der vier Advisory-Gates vor einer Umstellung auf blocking.
- Die vierte gezählte Stelle bei G1 und die dritte bei G2: belegt sind hier nur die oben
  genannten Fälle.
- Ob die Prüfung für fremde Klone am 2026-09-24 lief (G7).
