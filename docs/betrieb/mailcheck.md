# Betriebsakte: Mailcheck

> K1 aus [#3015](https://github.com/achimdehnert/platform/issues/3015): Diese Akte ist der Einstieg für ein Modell ohne Sitzungsgedächtnis. Wer sie liest, kann den Mailcheck betreiben, messen und verbessern. Stand 2026-09-10.

## Zweck

Der Mailcheck ist der Fortschritts-Check über die offenen Mail-Vorgänge des Owners in drei Postfächern (HNU per IMAP, IIL per Microsoft Graph, AD per IMAP). Er stellt fest, ob Antworten eingegangen sind, was der Owner selbst gesendet hat, und leitet je Vorgang den nächsten Schritt ab. Er sendet nie; Entwürfe bleiben Entwürfe, der Owner sendet selbst.

Der Skill-Text ist die vollständige Anweisung: `.windsurf/workflows/mailcheck.md` (verteilte Kopie `~/.claude/commands/mailcheck.md`, Kopf-Kommentar nennt `source_commit`).

## Einstiegskommando

```bash
# 1) Stand und Frische des Index (Schritt 0 des Skills)
python3 tools/mail_agent/suche.py --nur-deckung
# 2) Kette prüfen: Anker, Fristen, Ordner-Pflicht, Ablage, Links — ein Lauf
python3 tools/mail_agent/kettencheck.py
# 3) Beide Boards bauen (Action-Board + Arbeitsliste), reproduzierbar
make boards
make boards-check      # zweimal mit festem Stichtag, byteweise gleich
```

Der interaktive Lauf ist `/mailcheck` in der Kapitäns-Sitzung; die drei Kommandos oben sind das, was er am Anfang und am Ende ausführt.

## Datenwege

| Quelle | Weg | Frische |
|---|---|---|
| Index (alle drei Konten, alle Ordner) | `suche.py` → per SSH Management-Befehl `mail_suche` in der dev-hub-Datenbank | täglich 03:30 (Ingest); alles danach kennt der Index nicht |
| Live-Fallback IIL | `graph_mail.py --find …` (Graph, read-only) | sofort; nur für das Post-Ingest-Fenster |
| Live-Fallback HNU/AD | `read_mail.py` (IMAP, read-only) | sofort; nur für das Post-Ingest-Fenster |
| Vorgangs-Speicher | `~/.claude/mail-vorgaenge.json` (lokal, nie im Repo: enthält Adressen und Betreffs) | wird vom Skill fortgeschrieben |
| Anker (Mail ↔ Vorgang) | `~/.claude/mail-anker.json` (Message-ID-Schlüssel `konto-ordner-uid`), `eintrag_anker.py` schreibt | am Ende jedes Laufs und täglich über `make boards` |
| Ausgaben | Action-Board (Markdown), Arbeitsliste `todo.iil.pet` (Dienst `todo-board`, 8789), Mail-Ansicht `mail.iil.pet` (Dienst `mail-links`, 8787) | beide Dienste lesen das Ledger live; Code laden sie erst nach `systemctl --user restart` |

## Kennzahlen je Lauf (K2)

`tools/mail_agent/messjournal.py --schreiben --anwendung mailcheck` erhebt acht Kennzahlen (nur Zahlen und Bezeichner, keine Adressen, keine Betreffs) und haengt sie als JSON-Zeile ans Journal an:

| Kennzahl | Quelle |
|---|---|
| `vorgaenge_gesamt` | `board.py --pruefe` |
| `ohne_frist` | `board.py --pruefe` (Zeilen "keine Frist und kein frist_grund") |
| `referenzen_ohne_ordner` | `referenzen.py --pruefe-ordner --json` (`ab_stichtag`) |
| `unverankert` | `eintrag_anker.py --nur-zaehlen` |
| `vorgangsseiten_geprueft` / `vorgangsseiten_tot` | `link_pruefen.py --vorgangsseiten` (Netz, kann fehlen) |
| `posteingang_geschlossene_vorgaenge` | `ablage_erledigt.py --pruefe` |
| `index_alter_tage` | `suche.py --nur-deckung`, Alter in Tagen ab Laufzeitpunkt |

Schlaegt ein Quellkommando fehl oder liefert unlesbare Ausgabe (Timeout 120 s), wird die Kennzahl `null` und landet im Feld `fehler` — der Lauf bricht nie ab.

## Journal-Pfad

`~/.claude/mail-messjournal.jsonl` (Default, überschreibbar per `--journal`), eine JSON-Zeile je Lauf mit `zeit`, `anwendung`, `modell`, `kennzahlen`, `fehler`, `quelle_version`. `make boards` ruft `messjournal.py --schreiben --anwendung alle` einmal auf und haengt je eine Zeile für `mailcheck` und `todo` an — die geteilte Quelle `link_pruefen.py --vorgangsseiten` laeuft dabei nur einmal (#3067). `ablage_erledigt.py --pruefe` (75 Index-Abfragen, gemessen 253 s) ruft `make boards` ebenfalls nur einmal auf: die Textausgabe des eigenen Melder-Schritts geht per `--ablage-ausgabe DATEI` ins Messjournal, statt dort ein zweites Mal zu laufen (#3069). Trend über die letzten sieben Läufe:

```bash
python3 tools/mail_agent/messjournal.py --trend --anwendung mailcheck --n 7
```

## Verfallsignale (K3, Ist)

`python3 tools/mail_agent/verfallsmelder.py --anwendung mailcheck` (angeschlossen an
`make boards` und als Glied „Verfall" in `kettencheck.py`). Fünf Signale, je eine
Zeile `mailcheck | Signal | Ist | Schwelle | Zustand | Vorlauf/Konsequenz`:

| Signal | Schwelle | Vorlauf | Ist |
|---|---|---|---|
| Index älter als (`index_alter_tage`) | > 1,5 Tage (36 h) | ein Tag vor dem sichtbaren Ausfall | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) |
| Offener Vorgang ohne Frist (`ohne_frist`) | ≥ 1 | sofort | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) |
| Tote Links auf Vorgangsseiten (`vorgangsseiten_tot`) | > 3 | bevor der Owner klickt | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064), Closes [#3051](https://github.com/achimdehnert/platform/issues/3051) |
| Verteilte Skill-Kopie älter als Quelle | `source_commit` aus der MANAGED-BY-Kopfzeile ≠ `git log` auf `origin/main` | Sitzungsstart | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064), Closes [#3052](https://github.com/achimdehnert/platform/issues/3052) |
| Journal-Alter (kein Lauf) | > 2 Tage seit der jüngsten Journalzeile | vor dem nächsten erwarteten Lauf | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) (neu, kein Soll-Eintrag vorher) |

„Dienst läuft mit altem Code" (Unit-Start vs. letzter Code-Commit) ist NICHT Teil
dieses Signalsatzes — der Melder deckt ihn für `todo-board.service` und
`mail-links.service` unter der To-do-Anwendung ab, siehe `todo-liste.md`.

## Bekannte Fallen

- Der Index ist gestern: Antworten nach 03:30 sieht nur der Live-Fallback. Frage „nicht erkannt oder zu neu?" (Owner, 2026-09-10) ist ohne Blick auf das Index-Alter nicht beantwortbar.
- Verlaufseinträge sind die Akte des Vorgangs, nicht das Arbeitsprotokoll des Agenten (Regel 0 im Skill seit #3037). Eingegangene Mails werden gelesen und eingetragen, nicht als „noch nicht ausgewertet" vermerkt.
- Vorgang schließen geht nur per Hand im JSON (`bucket: erledigt`, `erledigt_am`); Kommando fehlt → [#3049](https://github.com/achimdehnert/platform/issues/3049).
- Das Ledger enthält Personendaten. Nichts daraus in Repo, Issue, PR-Text oder Test-Fixture — auch keine Betreffs (Realfall #3042, korrigiert).
- IIL hat keine IMAP-UIDs; Referenzen dort per Betreff in Anführungszeichen plus Datum.
- `graph_mail.py --find` schließt `--all` und `--from` gegenseitig aus; `--login` und `--find` ebenfalls.
- Seit [#3072](https://github.com/achimdehnert/platform/pull/3072) verankert `draft_mail.py` jeden Entwurf beim Anlegen per Message-ID; Outlook-Umzug ändert die UID, der Link hält.

## Verbesserungs-Backlog (K4: jeder Vorschlag mit Gegenrede und Alternative, bevor er gebaut wird)

Prüfung: `make betrieb-check` — ein Vorschlag ohne Gegenrede und Alternative wird abgewiesen (K4). Die Zeitungs-Akte in news-hub prüft man mit `python3 tools/betrieb_backlog_check.py ~/github/news-hub/docs/betrieb/morgen-zeitung.md`.

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Messjournal + `messjournal.py --trend` | Acht Zahlen, die niemand liest, sind ein Melder ohne Leser; erst der Trend macht sie lesbar, und den schaut sich der Owner nur an, wenn das Board ihn zeigt | Kennzahlen nicht in eine Datei, sondern als Kopfzeile auf die Arbeitsliste, die der Owner ohnehin öffnet | gebaut, [PR #3061](https://github.com/achimdehnert/platform/pull/3061) |
| 2 | Index-Alter auf die Arbeitsliste | Eine Zahl mehr im Kopf; sie erklärt nur, was fehlt, nicht was da ist | Statt Alter anzeigen: Post-Ingest-Fenster automatisch live nachziehen, wenn die Liste geöffnet wird | offen, K3 (Melder-Signal `index_alter_tage` ist gebaut, Anzeige auf der Arbeitsliste selbst nicht) |
| 3 | `board.py --erledigt` | Ein Kommando mehr, das der Owner nicht tippt; er sagt „#206 erledigt" im Chat | Schließen direkt aus der Arbeitsliste per Klick, mit Charta-Grenze (kein Senden) | [#3049](https://github.com/achimdehnert/platform/issues/3049) |
| 4 | Melder „tote Links" | Tote Links entstehen durch Ablage; der Melder meldet die Folge, nicht die Ursache | Anker beim Ablegen mitziehen (`ablage_erledigt.py` kennt die Bewegung) | gebaut, PR #3064 (#3051 zu) — Ursache (Anker beim Ablegen) bleibt offen |
## Modellfest-Drill (K5)

Gefahren am 2026-09-10 mit zwei frischen Sitzungen (Sonnet), Vorlage aus dieser Akte (`python3 tools/session_skill_drill.py --vorlage --datei docs/betrieb/mailcheck.md`): beide Läufe 9/9 erfüllt, 0 Abweichungen im Vergleich (`--vergleich`), Kennzahlen in beiden Läufen identisch (87 Vorgänge, 0 ohne Frist, 116 unverankert, 185 Links / 5 tot, Index 1 Tag alt). Beide Läufe schlugen dasselbe vor (Index-Alter auf die Arbeitsliste, Backlog 2). Protokolle liegen im Sitzungs-Scratchpad; die Zahlen stehen im Messjournal.

## Betriebs-Checkliste

| # | Check | Status |
|---|---|---|
| 1 | `python3 tools/mail_agent/kettencheck.py` gelaufen, gebrochene Glieder genannt | ☐ |
| 2 | `make boards` gelaufen, Messjournal hat eine neue Zeile (`messjournal.py --trend --n 1`) | ☐ |
| 3 | `python3 tools/mail_agent/verfallsmelder.py` — Warnungen genannt, auch bei 0 | ☐ |
| 4 | `make betrieb-check` grün (K4) | ☐ |
| 5 | Jeder neue Verlaufseintrag ist Akte, nicht Arbeitsprotokoll (Regel 0 im Mailcheck-Skill) | ☐ |
