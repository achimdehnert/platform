# sevdesk-Werkzeuge

Werkzeuge rund um die IIL-Rechnungsstrecke in sevdesk (platform#3102, SA-4). Jedes
Werkzeug ist eigenstaendig lauffaehig; Schreib-Operationen (Entwuerfe, Buchungen,
Versand) sind ausnahmslos hinter einem expliziten Owner-Gate (`--ja` o.ae.).

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

## Kostenabgleich

`tools/sevdesk/kostenabgleich.py` — K7 aus platform#3102 (Owner-Ergaenzung
2026-09-12). Liest die Abgaenge des Geschaeftskontos und ordnet sie offenen
Belegen zu, statt jeden Kontoauszug von Hand gegen die Belegablage zu pruefen.
Erkennt zusaetzlich wiederkehrende Kosten (Miete, Lizenzen, Abos) und schlaegt
je Position ein Buchungskonto vor.

### Kommandos

```bash
python3 tools/sevdesk/kostenabgleich.py                # Standardlauf, 120 Tage, Markdown
python3 tools/sevdesk/kostenabgleich.py --tage 60       # engeres Fenster
python3 tools/sevdesk/kostenabgleich.py --mandant edv   # zweiter Mandant (K8)
python3 tools/sevdesk/kostenabgleich.py --json          # maschinenlesbare Ausgabe
python3 tools/sevdesk/kostenabgleich.py --buchen        # zeigt, was gebucht wuerde — bucht NICHTS
python3 tools/sevdesk/kostenabgleich.py --buchen --ja   # bucht die sicheren Zuordnungen wirklich
```

`make sevdesk-kostenabgleich` ruft den Standardlauf.

### Die drei Listen

1. **Beleg vorhanden (buchbar)** — genau ein offener Beleg (Status 50/100,
   Lieferantenbeleg) trifft den Betrag auf einen Cent genau, teilt ein Wort
   (mindestens 4 Zeichen, ohne Fuellwoerter `gmbh`/`mbh`/`ag`/`kg`) mit dem
   Zahler und liegt maximal 14 Tage vom Abgang entfernt.
2. **Unklar** — der Betrag trifft, aber kein Name passt eindeutig, oder
   mehrere Belege kommen infrage.
3. **Beleg fehlt** — kein offener Beleg trifft den Betrag ueberhaupt
   (Owner/Rechnungsstrecke).

**Wiederkehrend**: Abgaenge mit gleichem normalisiertem Zahler und aehnlichem
Betrag (Toleranz 0,50 EUR) in mindestens zwei aufeinanderfolgenden
Kalendermonaten werden als "wiederkehrend (nx)" markiert. Fehlt bei einer
solchen Serie ausgerechnet in diesem Monat der Beleg, obwohl ein frueherer
Monat der Serie einen hatte, wird zusaetzlich "Beleg fuer diesen Monat fehlt"
vermerkt.

**Kontovorschlag** je Position: zuerst eine Regel aus
`~/.claude/sevdesk-konten.json` (wiederverwendet aus `bankpositionen.py`),
sonst bis zu zwei Treffer aus `GET /ReceiptGuidance/forExpense`; kein Treffer
-> `—`.

### Gates

- Gegen sevdesk wird **nur gelesen**, ausser mit `--buchen --ja`.
- `--buchen` ohne `--ja` zeigt nur eine Vorschau — `bookAmount` wird in
  keinem Fall aufgerufen.
- `--buchen --ja` bucht **ausschliesslich** die Stufe "Beleg vorhanden", und
  dort immer den vollen offenen Betrag (`FULL_PAYMENT`).
- Jede Buchung wird nach dem Schreiben gegen den Beleg geprueft und als Log
  unter `~/.claude/sevdesk-kostenabgleich-<datum>.json` abgelegt.
- Wiederholung bucht nie doppelt: eine bereits verknuepfte/verbuchte
  Bank-Transaktion (Status != 100) taucht bei einem erneuten Lauf nicht mehr
  unter den offenen Abgaengen auf — derselbe Mechanismus wie beim
  Zahlungsabgleich.
- Exit-Codes: `0` alles zugeordnet oder nichts offen, `2` unklare Faelle oder
  fehlende Belege (Owner-Blick noetig), `3` API-Fehler.

## Mandanten

K8 aus platform#3102: der Owner betreibt zwei sevdesk-Mandanten — die IIL GmbH
(Standard `iil`) und die Dehnert EDV-Beratung (`edv`), die der IIL meist
selbst Rechnungen stellt. `tools/sevdesk/mandant.py` ist die einzige Stelle,
die weiss, welche Secret-Datei zu welchem Mandanten gehoert:

```bash
python3 tools/sevdesk/kostenabgleich.py --mandant edv
SEVDESK_MANDANT=edv python3 tools/sevdesk/kostenabgleich.py   # gleichwertig
```

Secret-Dateien (Zeiger, nie der Wert im Repo):

| Mandant | Datei |
|---|---|
| `iil` (Standard) | `~/.secrets/sevdesk_api_token` |
| `edv` | `~/.secrets/sevdesk_dehnert_edv_api_token` |

Fehlt die Datei des gewaehlten Mandanten, bricht das Werkzeug mit einer
Meldung ab, die den erwarteten Pfad nennt (nie einen Wert) — Exit 3, kein
Traceback.

Rechnungen der EDV-Beratung an die IIL erscheinen im IIL-Kostenabgleich
automatisch als "Beleg vorhanden", sobald sie als sevdesk-Beleg in der IIL
vorliegen (Abgleich laeuft ohnehin ueber Betrag + Lieferantenname/Datum,
unabhaengig vom Ursprungsmandanten) — wirksam erst, wenn der Owner den
zweiten Zugang hinterlegt hat.

**Noch nicht umgestellt (Folgeschritt, #3102 K8):** `bankpositionen.py`,
`zahlungsabgleich.py` und `beleg_entwurf.py` lesen ihren Zugang weiterhin
fest verdrahtet auf den IIL-Pfad. Das Umstellen dieser Werkzeuge auf
`mandant.py` ist bewusst nicht Teil dieser Aenderung.
