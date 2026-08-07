---
description: IIL-Rechnungsstrecke — Rechnungs-Mails erkennen (DB-first), Empfänger prüfen, PDF nach Paperless (Tags) übertragen, sevdesk-Beleg-ENTWURF anlegen, Mail einsortieren; nie buchen, nie senden, nie löschen
mode: write
---

# /rechnungsstrecke — Postfach → docs (Paperless) → sevdesk-Beleg-Entwurf

> **Wann:** Auf Zuruf („Rechnungen übertragen") oder nach /mailcheck, wenn Rechnungs-Mails
> aufgelaufen sind. **Wann NICHT:** Verbuchen/Bezahlen (immer Owner, ⛔-Gate) · Postfächer
> HNU/AD (eigenes Go nötig) · EDV-Beratungs-Belege (Owner bucht manuell, s. Empfänger-Regel).
> **Auftrag + Akzeptanzkriterien:** platform#1827 (Zielzustand akzeptiert 2026-08-07;
> Probelauf bestanden am selben Tag, Belege 152103230/152105495/152105500).

**SSoT-Werkzeuge:** `tools/mail_agent/suche.py` (Erkennung, DB) · `tools/mail_agent/graph_mail.py`
(PDF-Abruf, Move) · `tools/sevdesk/beleg_entwurf.py` (Entwurf, status 50 fest) — kein neues Tooling.

## Step 0: Erkennung mit Deckung `[db]`

```bash
python3 tools/mail_agent/suche.py --nur-deckung
for b in Rechnung Invoice receipt Beleg Quittung; do
  python3 tools/mail_agent/suche.py --begriff "$b" --seit <fenster> --json; done
```

**Begriffsliste ist gemessen, nicht geraten:** `receipt` kam am 2026-08-07 dazu, weil
Stripe-Quittungen (Railway, Cerebras) von Rechnung+Invoice NICHT gefunden wurden.
Neue Lücke gefunden → Begriff HIER ergänzen, nicht nur im Lauf. Zweitquelle:
**`~/shared/inbox/invoices/`** (Owner-Ablage für Link-only-Rechnungen wie Heroku —
Owner-Entscheid B, 2026-08-07; Option „Mail-Körper als PDF" wurde verworfen).
Vorschau-Liste bauen; ohne Owner-Zuruf für das Fenster nichts übertragen.

## Step 1: Empfänger prüfen — VOR jedem Übertrag (Pflicht, zwei Realfälle am ersten Tag)

Das PDF öffnen und den **Rechnungsempfänger** lesen — die Mailadresse täuscht:

| Empfänger laut PDF | Weg |
|---|---|
| IIL GmbH (auch „IIL - Priv. Institut …") | Strecke fährt (Step 2–4) |
| „Achim Dehnert EDV Beratung" / „Dehnert EDV" | **STOPP** — eigenes sevdesk (ad@dehnert.team), Owner bucht manuell (zu wenige Buchungen für API, Owner-Entscheid 2026-08-07). Ledger-Todo `todo-edv-beratung` anlegen. Realfälle: Placetel, Cerebras (Letzterer TROTZ iil.gmbh-Mailadresse). |
| Privatperson | **STOPP** — Ledger-Todo `todo-privat`. Realfall: Kronen-Apotheke (Empfängerin Ottilie). |

## Step 2: Paperless mit Kontrollprobe

Consume: `/opt/paperless-consume/iil/rechnung/` auf hetzner-prod (Unterordner = Tags
iil+rechnung). **Rechte VOR der Ablage:** Ordner `runner-wh:runner-wh` + `chmod 2775`
(root-Ordner → PermissionError, Dokument kommt NIE an); liegengebliebene Datei braucht
`touch`. Vorher `max(id)` aus `documents_document` merken, nachher: **N rein = N drin**,
je Dokument Tags per DB prüfen (Container `iil_dochub_web`). Differenz = Abbruchbefund.

## Step 3: sevdesk-Entwurf (nie buchen)

```bash
python3 tools/sevdesk/beleg_entwurf.py --pdf <pdf> --lieferant "<Name laut PDF>" \
  --datum <YYYY-MM-DD> --brutto <x.yy> --steuer <x.yy> --beschreibung "<RechnungsNr>" \
  --taxrule <9|12|14> [--konto <nr>] [--waehrung USD]
```

- Beträge aus dem PDF, nie aus der Mail; Plausibilitätsprobe netto+steuer==brutto macht das Werkzeug.
- taxRule: DE-Lieferant 9 · Drittland-RC 12 · EU-RC 14 (Reverse-Charge-Hinweis steht im PDF).
  Sonderfall gemessen: US-Lieferant MIT deutscher USt (Railway) → 9.
- **Konto nur aus der Owner-Zuordnung** (project_sevdesk_invoice_pipeline) — nicht zugeordnet
  = leer lassen + im Board nennen. Nie raten (🌀 6310-statt-6837-Realfall).
- Fremdwährung: `--waehrung` reicht — das Werkzeug setzt `propertyForeignCurrencyDeadline`
  aufs Rechnungsdatum, sevdesk zieht den Stichtagskurs selbst (Feld heißt NICHT
  propExchangeRate — der 500-Fehler des Probelaufs).
- Idempotenz macht das Werkzeug (Dedup über description = Rechnungsnummer).

## Step 4: Mail einsortieren (reversibel)

Ziel `IIL.Finanzen/Rechnungen/01-in-sevdesk`. **Vor jedem Absender-Move die Zählprobe:**
`suche.py --von <absender>` — wie viele Mails dieses Absenders liegen im Posteingang, und
gehören ALLE dorthin? Stripe-Absender brauchen die VOLLE Adresse
(`invoice+statements+acct_…@stripe.com`) — der Präfix allein riss im Probelauf fast eine
fremde Quittung mit. Kein Löschen, kein Senden.

## Step 5: Bericht

Board an den Owner (Kapitäns-Kanal: Beträge/Lieferanten ja; ins Issue nur Zahlen/Struktur):
je Rechnung Paperless-Dok-ID + Beleg-ID + Mail-Status; Ausschlüsse mit Grund;
Deckungsblock; Ledger-Todos für STOPP-Fälle.

## Verboten

- Buchen, Bezahlen, Status >50 — ausnahmslos Owner (⛔-Gate)
- Senden, Hard-Delete, HNU/AD-Postfächer ohne eigenes Go
- Konto oder Entität raten; Kurs raten (Deadline-Feld nutzen)
- Übertrag ohne Empfänger-Prüfung (Step 1)

## Abschluss-Checkliste (PFLICHT — jede Zeile explizit abhaken)

- [ ] Step 0: Deckung + alle 5 Begriffe + Ablage-Ordner geprüft, Vorschau gezeigt
- [ ] Step 1: Empfänger JEDES PDFs gelesen, STOPP-Fälle ins Ledger
- [ ] Step 2: N rein = N drin, Tags per DB verifiziert
- [ ] Step 3: alle Belege status 50, Konto nur aus Owner-Zuordnung
- [ ] Step 4: Moves nur nach Zählprobe mit voller Absenderadresse
- [ ] Step 5: Board geliefert, Issue-Kommentar ohne Personendaten/Beträge Dritter
- [ ] Nichts gebucht, gesendet oder gelöscht

## Changelog

- 2026-08-07: Initial (v1) — kodifiziert den bestandenen Probelauf aus platform#1827
  (3 Belege Ende-zu-Ende, 2 Entitäts-Ausschlüsse, USD-Lösung, Cerebras-Erkennungslücke).
