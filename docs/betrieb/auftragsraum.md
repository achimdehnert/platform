# Betriebsakte: Auftragsraum

> K1 aus [#3015](https://github.com/achimdehnert/platform/issues/3015), Stufe 1 aus [KONZ-platform-059](../konzepte/KONZ-platform-059-auftragsraum-lernschleife-chat.md) ([#3079](https://github.com/achimdehnert/platform/issues/3079)): Einstieg für ein Modell ohne Sitzungsgedächtnis. Stand 2026-09-11 — Journal leer (Raum und Morgen-Meldung entstehen in anderen Aufträgen).

## Zweck

Der Auftragsraum ist ein Chat-Raum (Matrix/Element, `chat-hub`), in den der Owner Zurufe schreibt, die sonst nur in einer offenen Kapitäns-Sitzung ankommen. Der Raum ist kein zweiter Befehlskanal (Lotsen-Charta Art. 1): `chat_lotse.py sync` liefert Raumnachrichten als reine Daten, `tools/chat_agent/auftragsraum.py` klassifiziert sie ohne Modell in vier Klassen und schreibt ein Journal. Kurzbefehle werden erst per `anwenden` (Kapitäns-Sitzung) ins Ledger übernommen, Korrekturen werden per `regel` zum Memory-Kandidaten, Aufträge bekommen ein Issue. Zustand hat immer genau eine Heimat außerhalb des Journals — Ledger, Issue oder Regel-Datei (D8).

## Einstiegskommando

```bash
# Sortieren (im echten Betrieb: chat_lotse.py sync | auftragsraum.py sortieren)
python3 tools/chat_agent/auftragsraum.py sortieren --eingabe sync.jsonl
# Offene Vorschlaege/Auftraege/Korrekturen zeigen
python3 tools/chat_agent/auftragsraum.py offen
# Kurzbefehl-Vorschlaege uebernehmen (Kapitaens-Sitzung)
python3 tools/chat_agent/auftragsraum.py anwenden
# Regel-Artefakt aus einer Korrektur anlegen
python3 tools/chat_agent/auftragsraum.py regel <nachricht_id> --why '…'
```

Der Raum selbst (`chat_lotse.py room-create`) und die Morgen-Meldung (`digest_taeglich` → `chat_lotse.py send`) sind eigene Aufträge (KONZ-platform-059 MVC) — diese Akte beschreibt nur die platform-Seite: Sortierer, Journal, Regel-Artefakt, Kennzahlen, Verfallsignale.

## Datenwege

| Was | Woher | Anmerkung |
|---|---|---|
| Raumnachrichten | `chat_lotse.py sync` (iilgmbh/chat-hub), JSON-Zeilen: `room_id, room_name, sender, ts, event_id, body[, undecryptable, audio]` | führt nichts aus (Charta Art. 1) |
| Owner-Konto | `~/.claude/auftragsraum.env`, Zeile `OWNER_MXID=@…` | Owner-gepflegt, nicht im Repo; fehlt sie, gilt jede Nachricht als `fremd` |
| Journal | `~/.claude/auftragsraum-journal.jsonl` | eine Zeile je Nachricht: `zeit, klasse, konto_hash, nachricht_id, vorschlag, artefakt, korrektur, bearbeitet_am, tokens` — nie `sender` oder `body` |
| Kurzbefehl-Übernahme | `board.py --frist` (existiert) bzw. `board.py --erledigt` (folgt mit [#3049](https://github.com/achimdehnert/platform/issues/3049)) | `anwenden` protokolliert einen unbekannten Aufruf als „nicht angewendet", bricht nicht ab |
| Auftrag-Zustand | GitHub-Issue, live per `gh issue view --json state` gelesen | Journal spiegelt den Zustand nie (D8) |
| Regel-Artefakt | `~/.claude/auftragsraum-regeln/<datum>-<id>.md` | lokal, NICHT im Repo — Nachrichtentext darf dort stehen |

## Kennzahlen je Lauf (K2)

`tools/mail_agent/messjournal.py --schreiben --anwendung auftragsraum` liest das rohe Ereignis-Journal (nicht ein eigenes Kommando) und erhebt vier Kennzahlen:

| Kennzahl | Bedeutung |
|---|---|
| `nachrichten_je_klasse` | Objekt, Anzahl je Klasse, letzte 7 Tage |
| `korrekturen_ohne_artefakt_24h` | Korrekturen ohne Regel-Artefakt, älter als 24 h |
| `mittlere_stunden_bis_bearbeitung` | Mittelwert über alle Nachrichten mit `bearbeitet_am` |
| `anteil_angewendete_kurzbefehle` | angewendete / gesamte Kurzbefehl-Vorschläge |

`tokens` bleibt in Stufe 1 immer `null` (Feld der Journalzeile selbst — Aufwachkosten kommen erst mit Stufe 2, gemessen statt geschätzt, Kill-Gate). `--anwendung alle` erhebt `mailcheck`, `todo` UND `auftragsraum` in einem Lauf.

Heutiger Stand (2026-09-11): **Journal leer** — der Raum ist noch nicht angelegt (eigener Auftrag). Erste echte Zahlen entstehen mit der ersten Owner-Nachricht im Raum.

## Verfallsignale (K3, Soll)

`python3 tools/mail_agent/verfallsmelder.py --anwendung auftragsraum` liest das rohe Journal direkt (nicht den Umweg über das aggregierte Mailcheck-Journal) — drei Signale:

| Signal | Schwelle | Zustand bei Überschreitung |
|---|---|---|
| Nachricht ohne Bearbeitung | > 24 h | `WARNUNG` |
| Korrektur ohne Artefakt | > 24 h | `WARNUNG` |
| Journal-Alter (kein Eintrag) | > 7 Tage | `HINWEIS` (nie `WARNUNG`, blockt `--block` nie — ein stiller Raum ist laut Konzept-Befund B3 kein Fehler) |

Ein leeres Journal (Datei fehlt oder ohne Zeilen) macht alle drei Signale `nicht prüfbar`, nie eine Warnung. Schwellen per `--schwellen '{"auftragsraum.nachricht_ohne_bearbeitung_stunden": …}'` überschreibbar.

## Bekannte Fallen

- `board.py --erledigt` existiert erst mit [#3049](https://github.com/achimdehnert/platform/issues/3049) — bis dahin bleiben `erledigt`-Kurzbefehle nach `anwenden` unbearbeitet (`bearbeitet_am` bleibt `null`), das ist erwartetes Verhalten, kein Fehler.
- `regel` kennt den Nachrichtentext nicht aus dem Journal (das Journal speichert ihn nie, D7) — ohne `--zitat` bleibt ein TODO-Platzhalter im Regel-Artefakt stehen; die Kapitäns-Sitzung, die die Sync-Zeile gesehen hat, muss ihn nachtragen.
- `offen` fragt den Issue-Zustand live per `gh` ab; ohne Netz oder in Tests immer mit `--ohne-gh` aufrufen, sonst hängt der Lauf am Netzwerk-Timeout.
- Ein Owner-Konto ohne `~/.claude/auftragsraum.env` heißt: JEDE Nachricht (auch die eigene) wird als `fremd` protokolliert — kein Fehler, aber leicht zu übersehen, wenn der Raum scheinbar nichts tut.

## Verbesserungs-Backlog (K4)

Prüfung: `make betrieb-check` — ein Vorschlag ohne Gegenrede und Alternative wird abgewiesen.

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | `board.py --erledigt` bauen, damit Kurzbefehle wirklich schließen | Ein zweiter Schreibpfad neben `--frist` verdoppelt die Angriffsfläche für Ledger-Korruption, wenn beide gleichzeitig laufen | Kurzbefehl `erledigt` auf eine Reaktion (Emoji) statt Text umstellen — `chat_lotse.py react` existiert schon, kein Grammatik-Gate nötig | [#3049](https://github.com/achimdehnert/platform/issues/3049) |
| 2 | K4-Prüfwerkzeug: nacktes „offen" nicht mehr als Anker zulassen | Strenger heißt mehr Fehlalarme bei ehrlich offenen Punkten; eine Datumsangabe wäre reine Pflege ohne Erkenntnisgewinn | Anker-Prüfung ins bestehende Aufschub-Anker-Gate verlagern, das Prosa schon prüft, statt ein zweites Werkzeug zu pflegen | [#3080](https://github.com/achimdehnert/platform/issues/3080) |
| 3 | Raum, Sortierer, Journal ohne Modell als Stufe 1 | Ohne Live-Antwort fühlt sich der Raum nicht wie Chat an — nur eine teurere Notiz-App, die der Owner am Ende doch nicht nutzt | Statt eines neuen Raums eine Mail an sich selbst, die `/mailcheck` ohnehin schon abholt — dieselbe Lernschleife ohne neuen Kanal | [#3079](https://github.com/achimdehnert/platform/issues/3079) |
| 4 | Kennzahlen und Verfallsignale wöchentlich als Nachricht in den Raum zurückspiegeln | Ein Melder, der niemand liest, weil der Owner nur schreibt, nicht das Journal öffnet | Wochenzahlen als Teil der Morgen-Meldung (`digest_taeglich`) mitschicken statt eines eigenen Laufs | offen (Stufe 2, nach Kill-Gate-Auswertung 2026-10-08) |
| 5 | Stufe 2 (Auftrag → Issue → Lauf in schlanker Chat-Rolle) direkt mitbauen | Der Lauf startet trotzdem erst aus einer Kapitäns-Sitzung — für den Owner ändert sich gegenüber Stufe 1 nur die Automatik hinter dem Issue, kein Zugewinn ohne Kill-Gate-Nachweis | Aufträge als Ledger-Vorgang statt als Issue führen — der Mailcheck kennt das Vorgangsmuster (Frist, Zustand, Verlauf) bereits | offen (Stufe 2, Entscheid nach [#3079](https://github.com/achimdehnert/platform/issues/3079) Kill-Gate) |

## Modellfest-Drill (K5, Soll)

Noch nicht gefahren — Raum und Journal existieren noch nicht produktiv. Sobald die erste Owner-Nachricht im Raum steht: zwei frische Sitzungen führen `sortieren → offen → anwenden → regel` gegen dieselbe Fixture aus und vergleichen Journal-Bytes sowie Kennzahlen.

## Betriebs-Checkliste

| # | Check | Status |
|---|---|---|
| 1 | `python3 tools/chat_agent/auftragsraum.py sortieren --eingabe <Fixture> --journal /tmp/x.jsonl` idempotent (zweimal: 0 neue Zeilen im zweiten Lauf) | ☐ |
| 2 | `python3 tools/chat_agent/auftragsraum.py offen --ohne-gh --block` — Exit 0 ohne überfällige Korrektur | ☐ |
| 3 | `python3 tools/mail_agent/messjournal.py --schreiben --anwendung auftragsraum` — 0 Fehler bei vorhandenem Journal, `null`-Kennzahlen bei leerem | ☐ |
| 4 | `python3 tools/mail_agent/verfallsmelder.py --anwendung auftragsraum` — leeres Journal meldet „nicht prüfbar", nie eine Warnung | ☐ |
| 5 | `make betrieb-check` grün (K4) | ☐ |
