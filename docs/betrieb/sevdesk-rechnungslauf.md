# Betriebsakte: sevdesk-Rechnungslauf

> K1 aus [#3102](https://github.com/achimdehnert/platform/issues/3102): Einstieg für ein Modell ohne Sitzungsgedächtnis. Stand 2026-09-12.

## Zweck

`tools/sevdesk/rechnungslauf.py` erspart das manuelle Anlegen wiederkehrender
Ausgangsrechnungen (Dauerkunden mit monatlichem oder quartalsweisem
Leistungszeitraum). Es erkennt den Rhythmus aus dem Bestand, kopiert die
letzte Rechnung als Vorlage (Positionen, Texte, Zahlungsziel, Adresse) und
legt je Zeitraum einen neuen Rechnungs-**ENTWURF** an — Status 100, nie
höher. Versand ist ein separater, gegateter Schritt (`--senden --ja`); ohne
`--ja` zeigt er nur, was gesendet würde. Gegen sevdesk ist NUR Lesen und
`--dry-run` erlaubt; Anlegen/Senden mit echten Effekten laufen ausschließlich
über die dedizierten Kommandos unten, nie automatisch.

Schwesterwerkzeuge: `beleg_entwurf.py` (Eingangsrechnungen als Voucher-
Entwurf), `rechnung_entwurf.py` (eine Ausgangsrechnung von Hand). Dieses hier
ist der Lauf über den ganzen Dauerkunden-Bestand.

## Einstiegskommando

```bash
# Bestand lesen, Rhythmus erkennen, ~/.claude/sevdesk-dauerkunden.json schreiben (0600)
python3 tools/sevdesk/rechnungslauf.py --kunden-ermitteln

# Prüfliste für einen Monat (ohne Angabe: Vormonat), nichts wird geschrieben
python3 tools/sevdesk/rechnungslauf.py --monat 2026-09 --dry-run

# Entwürfe wirklich anlegen
python3 tools/sevdesk/rechnungslauf.py --monat 2026-09

# Quartalslauf analog
python3 tools/sevdesk/rechnungslauf.py --quartal 2026-Q3 --dry-run

# Versand-Vorschau (ohne --ja wird NICHTS gesendet)
python3 tools/sevdesk/rechnungslauf.py --senden --monat 2026-09
# Versand mit Gate
python3 tools/sevdesk/rechnungslauf.py --senden --monat 2026-09 --ja
```

`make sevdesk-rechnungslauf` fährt den Dry-Run des Vormonats (siehe Makefile).

## Datenwege

| Was | Woher | Anmerkung |
|---|---|---|
| Rechnungsbestand, Positionen, Kontakte | sevdesk-API (`/Invoice`, `/InvoicePos`, `/Contact`, `/CommunicationWay`, `/TextTemplate`) | Token `~/.secrets/sevdesk_api_token`, geteilter Client aus `beleg_entwurf.py` |
| Dauerkunden-Datei | `~/.claude/sevdesk-dauerkunden.json`, geschrieben von `--kunden-ermitteln`, Modus 0600 | NIE im Repo, NIE mit echten Namen in Tests/Doku (platform ist öffentlich) |
| Versandlog | `~/.claude/sevdesk-versand-<von>.json` je Zeitraum-Start | macht `--senden --ja` über Tage hinweg idempotent (Mail-ID im Log oder Status ≠ 100 → überspringen) |
| Lauf-Journal (K2) | `~/.claude/sevdesk-rechnungslauf-journal.jsonl`, vom Werkzeug selbst je Lauf angehängt | `messjournal.py --anwendung sevdesk` liest davon nur die jüngste Zeile |

## Kennzahlen je Lauf (K2)

`rechnungslauf.py` schreibt nach jedem Lauf (Prüflauf, Dry-Run, Anlegen ODER
Senden) selbst eine Zeile ins Lauf-Journal — kein separates Erhebungskommando
nötig. `tools/mail_agent/messjournal.py --schreiben --anwendung sevdesk`
liest NUR die jüngste Zeile und übernimmt fünf Kennzahlen:

| Kennzahl | Bedeutung |
|---|---|
| `entwuerfe_angelegt` | neu angelegte Rechnungs-Entwürfe in diesem Lauf |
| `uebersprungen` | Duplikate (Anlegen) bzw. bereits gesendet/falscher Status (Senden) |
| `gesendet` | tatsächlich verschickte Rechnungen (`--senden --ja`) |
| `wiederholungen_429` | HTTP-429-Wiederholungen während des Versands |
| `dauer_sekunden` | Laufzeit des gesamten Kommandos |

`--anwendung alle` schließt `sevdesk` mit ein (zusammen mit `mailcheck`,
`todo`, `auftragsraum`).

## Verfallsignale (K3)

`python3 tools/mail_agent/verfallsmelder.py --anwendung sevdesk` — ein
Signal, derselbe generische Journal-Alter-Mechanismus wie bei
`mailcheck`/`todo`:

| Signal | Schwelle | Zustand bei Überschreitung |
|---|---|---|
| Journal-Alter (kein Rechnungslauf) | > 35 Tage seit der jüngsten `sevdesk`-Zeile im Mailcheck-Journal | `WARNUNG` (kein `HINWEIS` — anders als bei `auftragsraum`: ein ausbleibender Rechnungslauf ist ein Fehler, kein gewolltes Schweigen) |

Einschränkung: Das Signal misst die Zeit seit dem letzten Lauf **jeder Art**
(Monat, Quartal oder `--senden`) — nicht spezifisch seit dem letzten
Monatslauf. Genauer geht nur mit einem eigenen Rhythmus-Feld im aggregierten
Journal; als Vereinfachung dokumentiert, nicht stillschweigend gelassen
(Anker [#3102](https://github.com/achimdehnert/platform/issues/3102)).

## Bekannte Fallen

- **HTTP 429**: sevdesk drosselt den Versand nach wenigen Sendungen in kurzer
  Folge. `versenden()` pausiert deshalb 15 s zwischen zwei Sendungen und
  wiederholt bei 429 mit `Retry-After` (falls gesetzt) oder der Folge
  30/60/90/120 s, maximal 6 Versuche — danach bleibt die Rechnung im Status
  „fehler" im Versandlog stehen und wird beim nächsten Lauf erneut versucht.
- **Layout-Cache**: Ändert sich eine sevdesk-PDF-Vorlage, zeigt die
  Rechnungsvorschau mitunter noch das alte Layout — ein `render`-Aufruf mit
  `forceReload` erzwingt die Neuberechnung. Betrifft nur die Anzeige, nicht
  die gespeicherten Daten; für den Entwurf selbst ohne Wirkung, aber relevant
  vor dem manuellen Owner-Review eines frisch angelegten Entwurfs.
- **Kopien landen im IIL-Ordner „sevdesk"**: Der Versand setzt `copy: true` —
  jede gesendete Rechnung landet zusätzlich im IIL-Postfach im Ordner
  „sevdesk". Das ist gewollt (Owner-Kontrolle), aber beim Aufräumen des
  Postfachs zu beachten — dieser Ordner ist kein offener Vorgang.
- Die Rhythmus-Erkennung braucht **mindestens zwei** Rechnungen mit
  übereinstimmender Zeitraumlänge (27–31 Tage = Monat, 89–93 Tage = Quartal);
  ein einzelner Treffer reicht nicht und der Kunde bleibt „unregelmäßig".
- `--kunden-ermitteln` überschreibt die Kundendatei bei jedem Lauf komplett
  neu (keine Merge-Logik) — Abweichungen (neu/entfallen) werden gemeldet,
  aber der Owner muss sie lesen, bevor der nächste Lauf sie überschreibt.
- Ohne `--ja` sendet `--senden` NIE etwas — das ist Absicht, keine Falle,
  aber leicht zu übersehen, wenn die Ausgabe wie ein Versand aussieht.

## Verbesserungs-Backlog (K4)

Prüfung: `make betrieb-check` — ein Vorschlag ohne Gegenrede und Alternative wird abgewiesen.

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Rhythmus-Feld je Journalzeile ergänzen, damit das 35-Tage-Signal spezifisch „seit letztem Monatslauf" statt „seit letztem Lauf jeder Art" misst | Ein zusätzliches Feld im aggregierten Journal, das nur dieses eine Signal genauer macht — Pflegeaufwand für eine Feinheit, die in der Praxis selten den Unterschied macht (Monat/Quartal/Senden liegen meist eng beieinander) | Statt eines neuen Felds: eigenes Signal je Rhythmus direkt aus dem rohen `sevdesk-rechnungslauf-journal.jsonl` lesen (wie `auftragsraum` es für sein Rohjournal tut), am aggregierten Journal vorbei | [#3102](https://github.com/achimdehnert/platform/issues/3102) |
| 2 | `--kunden-ermitteln` als wöchentlicher Cron statt manuell | Ein Cron, der niemand beobachtet, überschreibt die Kundendatei still — eine Owner-Auffälligkeit (Kunde fällt raus) bliebe unbemerkt, bis die nächste Rechnung fehlt | Diff-Meldung (`neu`/`entfallen`) zusätzlich als Signal im Verfallsmelder ausgeben, damit ein stiller Cron trotzdem auffällt | offen (nach erster Betriebserfahrung) |
| 3 | Positionen mit Preisänderung automatisch aus der Vorlage übernehmen (z. B. jährliche Indexierung) | Eine automatische Preisänderung ohne Owner-Blick ist genau der Fehler, den die ganze ENTWURF-Kette vermeiden soll — Beträge bleiben Owner-Sache | Preisänderungen bleiben manuell in sevdesk an der Vorlage-Rechnung selbst, der Lauf kopiert nur, was dort steht — keine eigene Logik nötig | offen |

## Modellfest-Drill (K5, Soll)

Noch nicht gefahren — das Werkzeug ist mit diesem PR neu. Sobald ein echter
Monatslauf produktiv gelaufen ist: zwei frische Sitzungen führen
`--kunden-ermitteln → --monat <M> --dry-run → --monat <M>` gegen denselben
synthetischen Fixture-Bestand aus und vergleichen Prüflisten-Bytes sowie
Kennzahlen (`test_rechnungslauf.py` deckt die Einzelfunktionen bereits
deterministisch ab — der Drill prüft den CLI-Pfad end-to-end).

## Betriebs-Checkliste

| # | Check | Status |
|---|---|---|
| 1 | `python3 tools/sevdesk/rechnungslauf.py --kunden-ermitteln` — Anzahl je Rhythmus plausibel, keine Namen im Terminal-Output kopieren | ☐ |
| 2 | `python3 tools/sevdesk/rechnungslauf.py --monat <Vormonat> --dry-run` zweimal — byteweise identische Ausgabe | ☐ |
| 3 | `python3 -m pytest tools/tests/test_rechnungslauf.py -q` grün | ☐ |
| 4 | `python3 tools/mail_agent/messjournal.py --schreiben --anwendung sevdesk` — 0 Fehler bei vorhandenem Lauf-Journal | ☐ |
| 5 | `python3 tools/mail_agent/verfallsmelder.py --anwendung sevdesk` — Zustand plausibel (WARNUNG nur bei echtem Rückstand) | ☐ |
| 6 | `make betrieb-check` grün (K4) | ☐ |
