# sevdesk-Werkzeuge

Werkzeuge rund um die IIL-Rechnungsstrecke in sevdesk (platform#3102, SA-4). Jedes
Werkzeug ist eigenstaendig lauffaehig; Schreib-Operationen (Entwuerfe, Buchungen,
Versand) sind ausnahmslos hinter einem expliziten Owner-Gate (`--ja` o.ae.).

## Rechnungslauf

`tools/sevdesk/rechnungslauf.py` — K1/K2/K3/K5 aus platform#3102. Legt
Dauerkunden (monatlicher oder quartalsweiser Rhythmus, aus dem Bestand
erkannt) je Zeitraum einen Rechnungs-ENTWURF an, indem es die letzte
Rechnung als Vorlage kopiert. Versand ist ein separater, gegateter Schritt.

```bash
python3 tools/sevdesk/rechnungslauf.py --kunden-ermitteln
python3 tools/sevdesk/rechnungslauf.py --monat 2026-09 --dry-run
python3 tools/sevdesk/rechnungslauf.py --senden --monat 2026-09 --ja
```

`make sevdesk-rechnungslauf` ruft den Dry-Run des Vormonats. Volle
Betriebsakte (Datenwege, Kennzahlen, Verfallsignale, bekannte Fallen):
[`docs/betrieb/sevdesk-rechnungslauf.md`](../../docs/betrieb/sevdesk-rechnungslauf.md).

## Zahlungsabgleich

`tools/sevdesk/zahlungsabgleich.py` — K4 aus platform#3102 (Vorschlag 228). Liest
offene Bankeingaenge und offene Rechnungen aus sevdesk und ordnet sie zu, statt
den Abgleich von Hand in der sevdesk-Oberflaeche zu machen.

### Zweck

Jeder Zahlungseingang muss gegen eine offene Rechnung gebucht werden — sonst
bleibt sie faelschlich "offen" und irgendwann faellig fuer eine Mahnung, obwohl
sie laengst bezahlt ist. Von Hand ist das Abtippen von Verwendungszwecken
fehleranfaellig und bei Sammelueberweisungen (mehrere Rechnungen in einer
Ueberweisung) leicht zu uebersehen. Das Werkzeug macht die Zuordnung nachvollziehbar
und trennt das, was sich automatisch sicher entscheiden laesst, von dem, was einen
Owner-Blick braucht.

### Kommandos

```bash
python3 tools/sevdesk/zahlungsabgleich.py                # Standardlauf, 120 Tage, Markdown
python3 tools/sevdesk/zahlungsabgleich.py --tage 60       # engeres Fenster
python3 tools/sevdesk/zahlungsabgleich.py --json          # maschinenlesbare Ausgabe
python3 tools/sevdesk/zahlungsabgleich.py --buchen        # zeigt, was gebucht wuerde — bucht NICHTS
python3 tools/sevdesk/zahlungsabgleich.py --buchen --ja   # bucht die sicheren Zuordnungen wirklich
```

`make sevdesk-zahlungsabgleich` ruft den Standardlauf.

### Die drei Listen

1. **Sicher zugeordnet** — eine oder mehrere Rechnungsnummern (Muster
   `YYYYMMDD-NNN`) stehen im Verwendungszweck, und die Summe der genannten
   offenen Rechnungen trifft den eingegangenen Betrag auf einen Cent genau.
2. **Unsicher — Owner-Blick noetig** — entweder passt der Betrag zu genau EINER
   offenen Rechnung, deren Kontaktname ein gemeinsames Wort mit dem
   Zahlungsempfaenger im Umsatz teilt, ohne dass eine Nummer im Zweck steht;
   oder eine Nummer steht im Zweck, aber die Summe weicht ab (Skonto,
   Teilzahlung, Rundung).
3. **Ohne Zuordnung** — der Rest: Fremdeingang, unbekannter Zahler, keine
   passende offene Rechnung.

Zusaetzlich: **Mahnkandidaten** — offene Rechnungen, deren Zahlungsziel
(`invoiceDate` + `timeToPay` Tage) am Stichtag ueberschritten ist und die in
keiner der beiden Trefferlisten vorkommen, absteigend nach Tagen ueberfaellig.
Es wird **nichts versendet** — reine Anzeige, Mahnungen sind ein eigener Auftrag.

### Gates

- Gegen sevdesk wird **nur gelesen**, ausser mit `--buchen --ja`.
- `--buchen` ohne `--ja` zeigt nur eine Vorschau — `bookAmount` wird in keinem
  Fall aufgerufen.
- `--buchen --ja` bucht **ausschliesslich** die Stufe "sicher", und dort immer
  den vollen offenen Betrag je Rechnung (`FULL_PAYMENT`) — nie Teilbetraege ohne
  Owner-Wort.
- Jede Buchung wird nach dem Schreiben gegen die Rechnung geprueft (`paidAmount`)
  und als Log unter `~/.claude/sevdesk-zahlungsabgleich-<datum>.json` abgelegt.
- Wiederholung bucht nie doppelt: eine bereits verknuepfte Bank-Transaktion
  (Status 200) taucht bei einem erneuten Lauf nicht mehr unter den offenen
  Eingaengen (Status 100) auf.
- Exit-Codes: `0` alles sicher oder nichts offen, `2` unsichere Faelle vorhanden
  (Owner-Blick noetig), `3` API-Fehler.

### Bekannte Fallen

- **Rechnungsnummern-Muster**: `YYYYMMDD-NNN` ist die Konvention aus dem
  Rechnungslauf. Eine Nummer im Zweck ist fuer sich kein Beweis — erst die
  Summenprobe macht die Zuordnung sicher. Genannt, aber falscher Betrag ->
  unsicher, nie sicher.
- **Sammelueberweisungen**: nennen mehrere Rechnungsnummern in einem
  Verwendungszweck. Alle genannten Nummern muessen zu bekannten offenen
  Rechnungen gehoeren UND deren Summe muss exakt passen — fehlt eine oder
  passt die Summe nicht, faellt der ganze Eingang auf "unsicher" zurueck statt
  einen Teil davon stillschweigend zu akzeptieren.
- **Skonto/Teilzahlung**: sehen im ersten Blick wie eine falsch abgetippte
  Rechnungsnummer aus, sind aber eine gewollte Abweichung vom Rechnungsbetrag.
  Deshalb landen sie in der unsicheren Liste statt automatisch als sicher
  durchzugehen.
