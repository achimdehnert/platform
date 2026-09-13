# Betriebsakte: sevdesk-Rechnungslauf

> K1/K9 aus [#3102](https://github.com/achimdehnert/platform/issues/3102): Einstieg für ein Modell ohne Sitzungsgedächtnis. Stand 2026-09-13.

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

### Belegbeschaffung (K9)

```bash
# Vorschau: was fehlt, woher käme es, was würde angelegt — legt NICHTS an
# (liest Postfach UND Owner-Ablage ~/shared/inbox/invoices/)
python3 tools/sevdesk/belegbeschaffung.py --tage 120

# Reproduzierbar aus einem gespeicherten Kostenabgleich-Lauf
python3 tools/sevdesk/kostenabgleich.py --json > /tmp/kostenabgleich.json
python3 tools/sevdesk/belegbeschaffung.py --eingabe /tmp/kostenabgleich.json

# Beleg-ENTWÜRFE wirklich anlegen (Status 50, nie gebucht)
python3 tools/sevdesk/belegbeschaffung.py --anlegen

# Je Beleg in den Mandanten, auf den er laut PDF lautet (#3112)
python3 tools/sevdesk/belegbeschaffung.py --mandant beide --anlegen
```

`make sevdesk-belegbeschaffung` fährt die Vorschau. Voraussetzung ist das
Bezugswege-Register `~/.claude/sevdesk-bezugswege.json` (Vorlage:
`tools/sevdesk/sevdesk-bezugswege.example.json`) — fehlt es, bricht das
Werkzeug mit Exit 3 ab statt still nichts zu tun.

## Zeitplan

Der Monatslauf startet am **10. jeden Monats um 07:30** als Benutzer-Timer (`sevdesk-rechnungslauf.timer`, Dateien unter `tools/sevdesk/systemd/`, installiert nach `~/.config/systemd/user/`). Er ruft `tools/sevdesk/rechnungslauf_monatlich.sh` auf: Entwürfe für den Vormonat anlegen, Prüfliste nach `~/.claude/boards/sevdesk-rechnungslauf-<Monat>.md`, Meldung in den Auftragsraum. **Versendet wird nichts**; der Versand folgt auf Owner-Wort mit `--senden --ja`. Warum der 10.: Owner-Wort 2026-09-12 („statt 1. den 10. jeden Monats"). Prüfen: `systemctl --user list-timers sevdesk-rechnungslauf.timer`.

## Datenwege

| Was | Woher | Anmerkung |
|---|---|---|
| Rechnungsbestand, Positionen, Kontakte | sevdesk-API (`/Invoice`, `/InvoicePos`, `/Contact`, `/CommunicationWay`, `/TextTemplate`) | Token `~/.secrets/sevdesk_api_token`, geteilter Client aus `beleg_entwurf.py` |
| Dauerkunden-Datei | `~/.claude/sevdesk-dauerkunden.json`, geschrieben von `--kunden-ermitteln`, Modus 0600 | NIE im Repo, NIE mit echten Namen in Tests/Doku (platform ist öffentlich). Je Kunde zusätzlich `zustand` (`"aktiv"`/`"beendet"`, automatisch) und `aktiv` (Owner-Override, bleibt über Läufe hinweg erhalten) |
| Versandlog | `~/.claude/sevdesk-versand-<von>.json` je Zeitraum-Start | macht `--senden --ja` über Tage hinweg idempotent (Mail-ID im Log oder Status ≠ 100 → überspringen) |
| Lauf-Journal (K2) | `~/.claude/sevdesk-rechnungslauf-journal.jsonl`, vom Werkzeug selbst je Lauf angehängt | `messjournal.py --anwendung sevdesk` liest davon nur die jüngste Zeile |
| Bezugswege-Register (K9) | `~/.claude/sevdesk-bezugswege.json`, vom Owner gepflegt | Vorlage im Repo; die echte Datei darf Ordnernamen, Portallinks und Muster mit Personennamen enthalten und bleibt deshalb lokal. `"ohne_abgang": true` sucht einen Lieferanten auch dann ab, wenn kein Abgang zu ihm passt (Rechnung liegt im Postfach, bezahlt wird über ein anderes Konto) |
| Rechnungs-PDFs (K9) | IIL-Postfach über Microsoft Graph (read-only), abgelegt unter `~/.claude/sevdesk-belege/<Lieferant>/` | nur `.pdf`-Anhänge; das Postfach wird nicht verändert (kein Verschieben, Markieren, Löschen) |
| Owner-Ablage (K9) | `~/shared/inbox/invoices/` (`--ablage-inbox`), vom Owner per Hand befüllt | zweite Quelle für Rechnungen ohne Mailversand (Owner-Entscheid B 2026-08-07); Dateien werden gelesen, nie verschoben oder gelöscht — fehlender Ordner ist kein Fehler |
| Postfach-Index (K9) | `~/.claude/sevdesk-belegbeschaffung-index.json` | bereits geholte Nachrichten-IDs — verhindert den zweiten Download derselben Mail |
| Belegbeschaffungs-Journal (K9) | `~/.claude/sevdesk-belegbeschaffung-journal.jsonl`, je Lauf eine Zeile | nur Kennzahlen, keine Beträge Dritter |

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

### Kennzahlen je Belegbeschaffungs-Lauf (K9)

`belegbeschaffung.py` schreibt je Lauf eine Zeile nach
`~/.claude/sevdesk-belegbeschaffung-journal.jsonl`:

| Kennzahl | Bedeutung |
|---|---|
| `lieferanten_abgaenge` | Abgänge ohne Beleg, für die das Register einen Lieferantenweg (`mail`) kennt |
| `pdf_gefunden` | Rechnungs-PDFs, die einem Register-Eintrag zugeordnet wurden |
| `ablage_pdf` | aus der Owner-Ablage `~/shared/inbox/invoices/` gelesene Dateien — auch die ohne Zuordnung, die als Owner-Zug erscheinen |
| `bereits_im_lauf` | Rechnungen, die im selben Lauf ein zweites Mal auftauchten (Rechnungsmail + Zahlungsbeleg + Ablage) |
| `entwuerfe_je_mandant` | Entwürfe je sevdesk-Mandant (`iil`, `edv`) |
| `entwuerfe_angelegt` | neu angelegte Beleg-Entwürfe (nur mit `--anlegen`) |
| `duplikate` | Belege, die es unter derselben Beschreibung schon gab |
| `vorschau` | Entwürfe, die im Trockenlauf nur vorgemerkt wurden |
| `owner_zug` | Zeilen, die einen Owner-Blick brauchen (Portal, fehlender Beleg, anderer Mandant, kein Bezugsweg) |
| `intern` | Abgänge ohne Lieferantenbeleg (Lohn, Steuern, Kontoführung) |
| `dauer_s` | Laufzeit |
| `anlegen` | ob der Lauf wirklich angelegt hat |

## Verfallsignale (K3)

`python3 tools/mail_agent/verfallsmelder.py --anwendung sevdesk` — ein
Signal, derselbe generische Journal-Alter-Mechanismus wie bei
`mailcheck`/`todo`:

| Signal | Schwelle | Zustand bei Überschreitung |
|---|---|---|
| Journal-Alter (kein Rechnungslauf) | > 35 Tage seit der jüngsten `sevdesk`-Zeile im Mailcheck-Journal | `WARNUNG` (kein `HINWEIS` — anders als bei `auftragsraum`: ein ausbleibender Rechnungslauf ist ein Fehler, kein gewolltes Schweigen) |

### Verfallsignale der Belegbeschaffung (K9)

Diese drei Signale liest man am Journal bzw. am Board ab — sie zeigen an, dass
das Werkzeug die Wirklichkeit nicht mehr trifft:

| Signal | Schwelle | Bedeutung |
|---|---|---|
| PDF-Parser findet bei einem Lieferanten 0 Beträge | eine `FEHLER`-Zeile "Datum oder Betrag im PDF nicht gefunden" in Liste 1/4 | Das Rechnungslayout hat sich geändert — Summen-/Datumswörter in `belegbeschaffung.py` nachziehen, nicht den Beleg von Hand abtippen |
| `owner_zug` wächst über mehrere Läufe, `pdf_gefunden` bleibt 0 | zwei Läufe in Folge | Postfach-Ordner umbenannt oder Absender/Betreff geändert — Register korrigieren |
| "kein Bezugsweg"-Zeilen bei jedem Lauf dieselben | ein Lauf | Das Register ist unvollständig; jeder solche Abgang bleibt sonst dauerhaft unbelegt |

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
  neu — außer einem manuell gesetzten `"aktiv": false`, das erhalten bleibt.
  Abweichungen (neu/entfallen) werden gemeldet, aber der Owner muss sie
  lesen, bevor der nächste Lauf sie überschreibt.
- Ohne `--ja` sendet `--senden` NIE etwas — das ist Absicht, keine Falle,
  aber leicht zu übersehen, wenn die Ausgabe wie ein Versand aussieht.
- **Beendete Kunden (K1-Nachtrag #3102)**: Ein Kunde, dessen letzter
  Leistungszeitraum mehr als zwei Rhythmusperioden vor dem angeforderten
  Zeitraum endet, gilt als `beendet` und bekommt GARANTIERT keinen Entwurf —
  auch nicht mit `--senden`. Das `zustand`-Feld in der Kundendatei ist nur
  ein Schnappschuss vom letzten `--kunden-ermitteln`-Lauf; die eigentliche
  Sperre prüft bei jedem Lauf live gegen den tatsächlich angeforderten
  Zeitraum (`ist_beendet()`) und bleibt deshalb auch dann korrekt, wenn
  `--kunden-ermitteln` seit einer Weile nicht mehr gelaufen ist. Ein Kunde
  mit manuell gesetztem `"aktiv": false` wird ebenso übersprungen, unabhängig
  vom `zustand`.

### Bekannte Fallen der Belegbeschaffung (K9)

- **Empfänger ≠ Postfach**: Eine Rechnung im IIL-Postfach kann an den zweiten
  Mandanten adressiert sein (real gesehen 2026-09-13). Der Empfänger wird
  ausschließlich aus dem PDF-Text gelesen. Mit `--mandant edv` bzw. `beide`
  entsteht der Beleg im richtigen Mandanten ([#3112](https://github.com/achimdehnert/platform/issues/3112)); mit dem
  Standard `iil` bleibt er Owner-Zug.
- **Steuerregel aus dem Register kann falsch sein**: Weist das PDF deutsche
  Umsatzsteuer aus, ist Reverse Charge ausgeschlossen — dann gilt Regel 9 und
  das Board nennt die Abweichung ([#3118](https://github.com/achimdehnert/platform/issues/3118)).
- **Dieselbe Rechnung mehrfach**: Rechnungsmail, Zahlungsbeleg und
  Ablage-Datei tragen dieselbe Nummer; je Lauf gewinnt die erste Fundstelle
  (`bereits_im_lauf`). Gegenüber dem Bestand greift zusätzlich der Dedup in
  `beleg_entwurf.py`, der die Nummer jetzt auch als Teil einer gewachsenen
  Beschreibung findet ([#3118](https://github.com/achimdehnert/platform/issues/3118)).
- **Zahlungsbeleg statt Rechnung**: Manche Anbieter schicken nur ein Receipt
  ohne Empfängerzeile, dafür mit `Account billed <login>`. Welcher Mandant
  hinter einem Konto steht, sagt das Register-Feld `logins`
  (`{"<org-login>": "iil", "<privat-login>": "edv"}`) — die Belege des
  persönlichen Kontos gehören zur EDV-Beratung (Owner-Wort 2026-09-13). Ein
  Login ohne Zuordnung bleibt "Empfänger unklar" beim Owner, auch wenn
  daneben eine IIL-Mailadresse steht. Rechnungen ohne Kontozeile erkennt das
  Werkzeug dagegen an `iil.gmbh` / `iil-institut` / `IIL`.
- **Fremdwährung**: EUR-Abgang gegen USD-Receipt wird nur im Kursband
  0,80–1,00 und innerhalb von 40 Tagen zusammengeführt, und nie als "sicher".
  Den Stichtagskurs setzt sevdesk selbst.
- **Zahler `—`**: Lastschriften ohne geparsten Namen tragen den Lieferanten
  nur im Verwendungszweck. Deshalb prüft das Register gegen
  `"<zahler> <zweck>"`, und `kostenabgleich.py --json` gibt den Zweck mit aus.
- **Fehlendes Register**: Exit 3 mit Zeiger auf die Vorlage — ein leeres
  Register sähe sonst aus wie "nichts zu tun".

## Verbesserungs-Backlog (K4)

Prüfung: `make betrieb-check` — ein Vorschlag ohne Gegenrede und Alternative wird abgewiesen.

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Rhythmus-Feld je Journalzeile ergänzen, damit das 35-Tage-Signal spezifisch „seit letztem Monatslauf" statt „seit letztem Lauf jeder Art" misst | Ein zusätzliches Feld im aggregierten Journal, das nur dieses eine Signal genauer macht — Pflegeaufwand für eine Feinheit, die in der Praxis selten den Unterschied macht (Monat/Quartal/Senden liegen meist eng beieinander) | Statt eines neuen Felds: eigenes Signal je Rhythmus direkt aus dem rohen `sevdesk-rechnungslauf-journal.jsonl` lesen (wie `auftragsraum` es für sein Rohjournal tut), am aggregierten Journal vorbei | [#3102](https://github.com/achimdehnert/platform/issues/3102) |
| 2 | `--kunden-ermitteln` als wöchentlicher Cron statt manuell | Ein Cron, der niemand beobachtet, überschreibt die Kundendatei still — eine Owner-Auffälligkeit (Kunde fällt raus) bliebe unbemerkt, bis die nächste Rechnung fehlt | Diff-Meldung (`neu`/`entfallen`) zusätzlich als Signal im Verfallsmelder ausgeben, damit ein stiller Cron trotzdem auffällt | offen (nach erster Betriebserfahrung) |
| 3 | Positionen mit Preisänderung automatisch aus der Vorlage übernehmen (z. B. jährliche Indexierung) | Eine automatische Preisänderung ohne Owner-Blick ist genau der Fehler, den die ganze ENTWURF-Kette vermeiden soll — Beträge bleiben Owner-Sache | Preisänderungen bleiben manuell in sevdesk an der Vorlage-Rechnung selbst, der Lauf kopiert nur, was dort steht — keine eigene Logik nötig | offen |
| 4 | Beschaffte Rechnungs-PDFs zusätzlich nach Paperless übertragen (`--paperless`), statt sie nur unter `~/.claude/sevdesk-belege/` abzulegen | Zwei Ablagen für dasselbe Dokument heißen zwei Wahrheiten: sevdesk trägt das PDF ohnehin am Beleg, und eine zweite Kopie in Paperless kann still auseinanderlaufen, sobald ein Beleg in sevdesk korrigiert oder ersetzt wird | Statt einer eigenen Übertragung den bestehenden Weg nehmen: die Rechnungsmail wie in `rechnungsstrecke` nach Paperless geben und in sevdesk nur den Beleg führen — dann gibt es genau einen Einspeisepunkt statt zweier | [#3102](https://github.com/achimdehnert/platform/issues/3102) |
| 5 | Portal-Abruf für die drei Abo-Lieferanten mit hinterlegtem Zugang automatisieren, statt sie jeden Monat als Owner-Zug zu listen | Ein Werkzeug, das sich mit gespeicherten Zugangsdaten in fremde Kundenkonten einloggt, ist genau die Klasse von Automatik, die bei einer Layout- oder MFA-Änderung stumm scheitert — und es bräuchte Passwörter außerhalb von `~/.secrets` im Zugriff eines Automaten | Beim Anbieter den Rechnungsversand per Mail einschalten (viele Abos können das) und den Lieferanten im Register von `portal` auf `mail` umstellen — dann trägt die bestehende Postfach-Strecke den Fall ohne neue Zugangsdaten | [#3102](https://github.com/achimdehnert/platform/issues/3102) |
| 6 | `beleg_entwurf.py` auf `--mandant` umstellen, damit Belege an die EDV-Beratung im richtigen Mandanten angelegt werden statt als Owner-Zug zu enden | Ein zweiter schreibender Zugang verdoppelt die Fläche, auf der ein falsch gesetzter Mandant einen Beleg im falschen Buchungskreis erzeugt — und ein solcher Fehlgriff fällt erst beim Jahresabschluss auf | Den Mandanten gar nicht im Werkzeug wählen, sondern den EDV-Beleg als Ausgangsrechnung der EDV-Beratung an die IIL führen (er ist meist genau das) — dann bleibt die Belegstrecke einmandantig | [#3112](https://github.com/achimdehnert/platform/issues/3112) |

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
| 6 | `python3 tools/sevdesk/belegbeschaffung.py --tage 120` — Vorschau läuft, vier Listen plausibel, nichts angelegt (K9) | ☐ |
| 7 | `python3 -m pytest tools/tests/test_belegbeschaffung.py -q` grün (K9) | ☐ |
| 8 | `make betrieb-check` grün (K4) | ☐ |
