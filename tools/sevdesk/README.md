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

## Belegbeschaffung

`tools/sevdesk/belegbeschaffung.py` — K9 aus platform#3102. Nimmt die Abgaenge
ohne Beleg aus dem Kostenabgleich und beschafft die fehlenden Rechnungen,
statt sie Monat fuer Monat von Hand aus dem Postfach zu fischen.

### Zweck

Der Kostenabgleich sagt, **wo** ein Beleg fehlt — nicht, **woher** er kommt.
Ein lokales Bezugswege-Register (`~/.claude/sevdesk-bezugswege.json`, Vorlage
`tools/sevdesk/sevdesk-bezugswege.example.json`) beantwortet je Lieferant
genau das: `intern` (es gibt keinen Lieferantenbeleg), `mail` (Rechnung liegt
im IIL-Postfach) oder `portal` (nur ueber das Kundenportal abrufbar). Fuer den
`mail`-Weg holt das Werkzeug die PDFs ueber Microsoft Graph (read-only), liest
Betrag/Datum/Nummer/Empfaenger aus dem PDF, ordnet PDF und Abgang zu und legt
sevdesk-Beleg-**ENTWUERFE** an (Status 50 aus `beleg_entwurf.py`).

### Kommandos

```bash
python3 tools/sevdesk/belegbeschaffung.py                       # Vorschau, legt NICHTS an
python3 tools/sevdesk/belegbeschaffung.py --tage 60             # engeres Fenster
python3 tools/sevdesk/belegbeschaffung.py --eingabe lauf.json   # Kostenabgleich-JSON statt Live-Lauf
python3 tools/sevdesk/belegbeschaffung.py --anlegen             # Entwuerfe wirklich anlegen
python3 tools/sevdesk/belegbeschaffung.py --json                # maschinenlesbar
python3 tools/sevdesk/belegbeschaffung.py --ablage-inbox PFAD   # andere Owner-Ablage
```

`make sevdesk-belegbeschaffung` ruft die Vorschau. Das Board liegt unter
`~/.claude/boards/sevdesk-belegbeschaffung.md`, die PDFs unter
`~/.claude/sevdesk-belege/<Lieferant>/`.

**Zweite Quelle: die Owner-Ablage** `~/shared/inbox/invoices/`
(`--ablage-inbox`, fehlender Ordner ist kein Fehler). Rechnungen, die der
Owner von Hand aus einem Kundenportal laedt und dort einstellt, gehen denselben
Weg wie Postfach-PDFs; der Lieferant wird ueber den Dateinamen, sonst ueber
den PDF-Text gegen das Register bestimmt, ohne Treffer ist es ein Owner-Zug.
Die Dateien werden nie verschoben oder geloescht — ein angelegter Beleg wird
im Index vermerkt, damit der naechste Lauf ihn nicht erneut anlegt.
`intern`-Eintraege zaehlen dabei nicht als Treffer, damit ein Kontoauszug in
der Ablage keinen Lieferantenbeleg ausloest.

### Die vier Listen

1. **Entwuerfe angelegt / Vorschau** — PDF und Abgang passen zusammen
   (`sicher` bei EUR-Gleichstand, `fremdwaehrung` im Kursband). Zeigt
   Beleg-ID bzw. `VORSCHAU`/`DUPLIKAT` und den Kontovorschlag.
2. **Owner-Zug** — Portal-Abruf (mit Link), Beleg nicht im Postfach, anderer
   Mandant (`edv`, mit lokalem PDF-Pfad), Empfaenger unklar, kein Bezugsweg
   im Register, Ordner nicht gefunden.
3. **intern (kein Lieferantenbeleg)** — Lohn, Steuern, Kontofuehrung,
   Eigenuebertraege, jeweils mit Kontovorschlag aus dem Kostenabgleich.
4. **PDF ohne Abgang** — Rechnung gefunden, kein passender Abgang im Fenster.
   Fuer den eigenen Mandanten wird trotzdem ein Entwurf angelegt; der Abgang
   kommt spaeter oder lief ueber ein anderes Konto. Lieferanten, die **nie**
   ueber dieses Konto bezahlt werden (andere Zahlungsart), tragen im Register
   `"ohne_abgang": true` und werden auch ohne Abgang abgesucht — Fenster ist
   dann `--tage`.

### Gates

- Ohne `--anlegen` ist der Lauf eine Vorschau: sevdesk wird nur gelesen, es
  wird **kein PDF hochgeladen** (`beleg_entwurf.anlegen` kehrt im Trockenlauf
  vor dem Upload zurueck).
- Gebucht wird **nie** — `beleg_entwurf.py` legt ausschliesslich Status 50 an.
- Ein Buchungskonto wird **nie** gesetzt; der Vorschlag steht nur im Board.
- `--mandant iil|edv|beide` (Standard `iil`) entscheidet, welche Belege
  entstehen: nur eigene, nur die der zweiten Firma, oder je Beleg der
  Mandant, auf den er laut PDF lautet (#3112). Ein Beleg mit unklarem
  Empfaenger bleibt in jedem Fall Owner-Zug — geraten wird nie. Fehlt der
  Zugang eines Mandanten, ist das eine Board-Zeile, kein Abbruch.
- Dieselbe Rechnung kommt mehrfach an (Rechnungsmail, Zahlungsbeleg,
  Ablage-Datei): innerhalb eines Laufs gewinnt die erste Fundstelle, weitere
  zaehlen als `bereits_im_lauf` (#3118).
- Weist das PDF deutsche Umsatzsteuer aus, gilt Steuerregel 9 statt des
  Register-Werts; die Abweichung steht als Hinweis unter der Liste (#3118).
- Das Postfach wird nur gelesen — nichts verschoben, markiert oder geloescht.
- Idempotenz: bereits geholte Nachrichten stehen in
  `~/.claude/sevdesk-belegbeschaffung-index.json` und werden nicht erneut
  heruntergeladen; doppelte Entwuerfe faengt der description-Dedup in
  `beleg_entwurf.py` als `DUPLIKAT` ab.
- Exit-Codes: `0` keine Owner-Zug-Zeile, `2` Owner-Zug noetig, `3`
  Register/Zugang/API.

### Bekannte Fallen

- **Empfaenger != Postfach**: Eine Rechnung im IIL-Postfach kann an den
  zweiten Mandanten adressiert sein (real gesehen 2026-09-13). Der Empfaenger
  wird deshalb aus dem PDF-Text gelesen, nie aus dem Postfach geschlossen.
  Zahlungsbelege ohne Empfaengerzeile (nur `Account billed <login>`) ordnet
  das Register ueber `logins` (Login -> Mandant) zu — ein persoenliches Konto
  kann so zur zweiten Firma gehoeren, ohne dass geraten wird. Ein Login ohne
  Zuordnung bleibt "Empfaenger unklar", auch wenn daneben eine eigene
  Rechnungsmailadresse steht: welches Konto belastet wurde, sagt die
  Kontozeile, nicht die Adresse. Die aeltere Listenform `eigene_logins` gilt
  weiter (alle Logins = eigener Mandant). Rechnungen **ohne** Kontozeile erkennt das
  Werkzeug an `iil.gmbh`, `iil-institut` oder `IIL` als eigenem Wort.
- **Fremdwaehrung**: Der Abgang steht in EUR, das Receipt in USD. Eine solche
  Zuordnung ist nie "sicher", sondern `fremdwaehrung` — den Stichtagskurs
  setzt sevdesk selbst (`propertyForeignCurrencyDeadline`).
- **Zahler `—`**: Bei Lastschriften ohne geparsten Namen traegt nur der
  Verwendungszweck den Lieferanten; das Register wird deshalb gegen
  `"<zahler> <zweck>"` geprueft. Dafuer gibt `kostenabgleich.py --json` den
  Zweck je Position mit aus.
- **Fehlendes Register**: bricht mit Exit 3 ab und nennt die Vorlage — ein
  leeres Register saehe sonst aus wie "nichts zu tun".

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

**Umgestellt (#3112):** `beleg_entwurf.py` nimmt `--mandant iil|edv` und holt
seinen Zugang ueber `mandant.py`; der Standard bleibt `iil`, die
Schwesterwerkzeuge rufen `_client()` weiterhin ohne Argument. Der
Kontenhilfe-Cache liegt je Mandant getrennt
(`~/.claude/sevdesk-receipt-guidance-<mandant>.json`, `iil` behaelt den alten
Pfad) — der Kontenrahmen der zweiten Firma ist ein anderer.

```bash
python3 tools/sevdesk/beleg_entwurf.py --mandant edv --pdf r.pdf ...
```

**Noch nicht umgestellt (Folgeschritt, #3102 K8):** `bankpositionen.py` und
`zahlungsabgleich.py` lesen ihren Zugang weiterhin fest verdrahtet auf den
IIL-Pfad.
