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

## Kennzahlen je Lauf (K2, Soll)

Das Messjournal existiert noch nicht. Bis es existiert, sind dies die Zahlen, die jeder Lauf ohnehin erzeugt und die ein Journal aufnehmen soll (nur Zahlen und Bezeichner, keine Adressen, keine Betreffs):

| Kennzahl | Quelle | Heute (2026-09-10) |
|---|---|---|
| Vorgänge gesamt / offen / geschlossen im 14-Tage-Fenster | `board.py --pruefe` | 87 gesamt |
| Offene Vorgänge ohne Frist und ohne `frist_grund` | `board.py --pruefe` | 0 |
| Referenzen ohne Ordner ab Stichtag | `referenzen.py --pruefe-ordner` | 0 (70 Altbestand) |
| Unverankerte Referenzen | `eintrag_anker.py --nur-zaehlen` | nicht erhoben |
| Tote Links auf Vorgangsseiten | `link_pruefen.py --vorgangsseiten` | 5 von 184 |
| Posteingangs-Mails zu geschlossenen Vorgängen | `ablage_erledigt.py --pruefe` | nicht erhoben |
| Index-Alter zum Laufzeitpunkt | `suche.py --nur-deckung` | Index bis 2026-09-09 |

Journal-Pfad (Soll): `~/.claude/mail-messjournal.jsonl`, eine Zeile je Lauf mit Datum, Modellkennung und den sieben Zahlen; `board.py --trend` zeigt die letzten sieben Läufe. Beides ist Backlog (unten).

## Verfallsignale (K3, Soll)

| Signal | Schwelle | Vorlauf | Heute |
|---|---|---|---|
| Index älter als | 36 h | ein Tag vor dem sichtbaren Ausfall | nicht als Melder verdrahtet |
| Offener Vorgang ohne Frist | 1 | sofort | gedeckt durch `board.py --pruefe` |
| Tote Links auf Vorgangsseiten | > 3 | bevor der Owner klickt | Kandidat [#3051](https://github.com/achimdehnert/platform/issues/3051) |
| Verteilte Skill-Kopie älter als Quelle | 1 Commit | Sitzungsstart | Kandidat [#3052](https://github.com/achimdehnert/platform/issues/3052) |
| Dienst läuft mit altem Code (Unit älter als letzter Code-Commit) | 1 Commit | nach jedem Merge | nicht verdrahtet |

## Bekannte Fallen

- Der Index ist gestern: Antworten nach 03:30 sieht nur der Live-Fallback. Frage „nicht erkannt oder zu neu?" (Owner, 2026-09-10) ist ohne Blick auf das Index-Alter nicht beantwortbar.
- Verlaufseinträge sind die Akte des Vorgangs, nicht das Arbeitsprotokoll des Agenten (Regel 0 im Skill seit #3037). Eingegangene Mails werden gelesen und eingetragen, nicht als „noch nicht ausgewertet" vermerkt.
- Vorgang schließen geht nur per Hand im JSON (`bucket: erledigt`, `erledigt_am`); Kommando fehlt → [#3049](https://github.com/achimdehnert/platform/issues/3049).
- Das Ledger enthält Personendaten. Nichts daraus in Repo, Issue, PR-Text oder Test-Fixture — auch keine Betreffs (Realfall #3042, korrigiert).
- IIL hat keine IMAP-UIDs; Referenzen dort per Betreff in Anführungszeichen plus Datum.
- `graph_mail.py --find` schließt `--all` und `--from` gegenseitig aus; `--login` und `--find` ebenfalls.

## Verbesserungs-Backlog (K4: jeder Vorschlag mit Gegenrede und Alternative, bevor er gebaut wird)

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Messjournal + `board.py --trend` | Sieben Zahlen, die niemand liest, sind ein Melder ohne Leser; erst der Trend macht sie lesbar, und den schaut sich der Owner nur an, wenn das Board ihn zeigt | Kennzahlen nicht in eine Datei, sondern als Kopfzeile auf die Arbeitsliste, die der Owner ohnehin öffnet | offen, K2 |
| 2 | Index-Alter auf die Arbeitsliste | Eine Zahl mehr im Kopf; sie erklärt nur, was fehlt, nicht was da ist | Statt Alter anzeigen: Post-Ingest-Fenster automatisch live nachziehen, wenn die Liste geöffnet wird | offen, K3 |
| 3 | `board.py --erledigt` | Ein Kommando mehr, das der Owner nicht tippt; er sagt „#206 erledigt" im Chat | Schließen direkt aus der Arbeitsliste per Klick, mit Charta-Grenze (kein Senden) | [#3049](https://github.com/achimdehnert/platform/issues/3049) |
| 4 | Melder „tote Links" | Tote Links entstehen durch Ablage; der Melder meldet die Folge, nicht die Ursache | Anker beim Ablegen mitziehen (`ablage_erledigt.py` kennt die Bewegung) | [#3051](https://github.com/achimdehnert/platform/issues/3051) |

## Modellfest-Drill (K5, Soll)

Eine frische Sitzung bekommt nur diese Akte, führt die drei Einstiegskommandos aus, nennt die sieben Kennzahlen und einen Backlog-Vorschlag mit Gegenrede. Protokoll nach der Drill-Vorlage (`tools/session_skill_drill.py --vorlage`, Trockenlauf-Regel seit #3016). Noch nicht gefahren.
