# Betriebsakte: To-do-Liste (todo.iil.pet)

> K1 aus [#3015](https://github.com/achimdehnert/platform/issues/3015): Einstieg für ein Modell ohne Sitzungsgedächtnis. Stand 2026-09-10.

## Zweck

Die Arbeitsliste zeigt dem Owner die offenen Mail-Vorgänge aus dem Ledger als Seite: Liste nach Buckets, je Vorgang eine Vorgangsseite mit Verlauf (Akte), Fristen, nächstem Schritt und Links in die Mails. Sie ist rein anzeigend, kein Knopf löst etwas aus (Lotsen-Charta Art. 1). Öffentlich nur hinter Cloudflare Access.

## Einstiegskommando

```bash
# Seite einmal bauen (reproduzierbar, --stichtag für gleiche Ausgabe)
python3 tools/todo_board/todo_board.py build
# Dienst lokal
python3 tools/todo_board/todo_board.py serve --port 8789 --bind 127.0.0.1
# Kettenprobe: alle Mail-Links aller Vorgangsseiten
python3 tools/mail_agent/link_pruefen.py --vorgangsseiten
```

Prod: `systemd --user todo-board.service` auf dev-desktop (Port 8789), Tunnel `cloudflared-mail-links` leitet `todo.iil.pet` dorthin; deklariert in `infra/ports.yaml` als `todo-board`, Betriebsstatus `blockiert` (läuft ohne Deploy-Recht, #2507). Neuer Code wirkt erst nach `systemctl --user restart todo-board.service` (Owner).

## Datenwege

| Was | Woher | Anmerkung |
|---|---|---|
| Vorgänge | `~/.claude/mail-vorgaenge.json` (live gelesen bei jedem Abruf) | Personendaten, nie ins Repo |
| Archivierte Vorgänge | `archivierte_vorgaenge()` in `todo_board.py` | Verlaufseinträge werden durchnummeriert (`#116-23`) |
| Mail-Links im Verlauf | Textanalyse der Notiz (`Ordner #uid`) gegen `~/.claude/mail-anker.json`; nur verankerte Nummern werden Links | Kopf-Aktion fällt seit #3034 auf dieselben Anker zurück |
| Kopf-Aktion „Erste/Letzte Mail des Strangs" | Nummern-Anker oder Verlaufs-Anker | seit #3034 |
| Rückweg | Vorgangsseite → „← Arbeitsliste"; Mail-Seiten auf mail.iil.pet → „Arbeitsliste · Vorgang #N" | seit #3042 |
| Suche | `?q=` auf der Liste | seit #2874 |

## Kennzahlen je Lauf (K2)

`tools/mail_agent/messjournal.py --schreiben --anwendung todo` erhebt fünf Kennzahlen und haengt sie als JSON-Zeile ans Journal an:

| Kennzahl | Quelle |
|---|---|
| `vorgangsseiten` | `link_pruefen.py --vorgangsseiten` (Netz, kann fehlen) |
| `mail_links` / `mail_links_tot` | dito |
| `ohne_kopf_aktion` (Vorgänge ohne Kopf-Aktion, „keine Mail verknuepft") | Zählung über `todo_board.aktionen()` je Vorgang (Direktimport, kein eigenes Kommando) |
| `geschlossen_7_tage` | Ledger `erledigt_am`, Zählung über die letzten 7 Tage |

„Öffnungen der Liste je Tag" (Cloudflare-Access-Log oder Dienst-Log) ist weiterhin Backlog — kein Quellkommando, nicht Teil dieses Baus.

Journal-Pfad: gemeinsam mit dem Mailcheck (`~/.claude/mail-messjournal.jsonl`), Feld `anwendung: "todo"`. Trend über die letzten sieben Läufe:

```bash
python3 tools/mail_agent/messjournal.py --trend --anwendung todo --n 7
```

## Verfallsignale (K3, Ist)

`python3 tools/mail_agent/verfallsmelder.py --anwendung todo` (angeschlossen an
`make boards` und als Glied „Verfall" in `kettencheck.py`). Fünf Signale, je eine
Zeile `todo | Signal | Ist | Schwelle | Zustand | Vorlauf/Konsequenz`:

| Signal | Schwelle | Ist |
|---|---|---|
| Tote Mail-Links (`mail_links_tot`) | > 3 | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064), Closes [#3051](https://github.com/achimdehnert/platform/issues/3051) |
| Ohne Kopf-Aktion (`ohne_kopf_aktion`) | > 5 | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) (neu, kein Soll-Eintrag vorher) |
| Dienst läuft mit altem Code (`todo-board.service` vs. `todo_board.py`) | Unit-Start < letzter Code-Commit | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) |
| Dienst läuft mit altem Code (`mail-links.service` vs. `mail_link_server.py`) | Unit-Start < letzter Code-Commit | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) (neu, kein Soll-Eintrag vorher) |
| Journal-Alter (kein Lauf) | > 2 Tage seit der jüngsten Journalzeile | gebaut, PR [#3064](https://github.com/achimdehnert/platform/pull/3064) (neu, kein Soll-Eintrag vorher) |
| Dienst nicht in `ports.yaml` | 1 | behoben mit #3039 (unverändert, kein Melder-Signal) |
| Waisen-Zuordnung je Repo kippt | 2 Hosts je Repo | [#3050](https://github.com/achimdehnert/platform/issues/3050) (unverändert, außerhalb dieses Auftrags) |

## Bekannte Fallen

- Die Liste zeigt kein Index-Alter: „zu neu" und „nicht erkannt" sehen gleich aus (Owner-Frage 2026-09-10, Vorgang 116).
- Verlaufstexte werden gerendert, wie sie im Ledger stehen: Arbeitsprotokolle des Agenten machen die Akte unlesbar (Regel 0 im Mailcheck-Skill, #3037).
- Mail-Links tragen nur, wenn die Nummer im Ledger MIT Ordner steht und verankert ist; unverankerte Nummern bleiben Text mit Hinweis.
- `mail.iil.pet` und `todo.iil.pet` sind zwei Dienste (8787 / 8789); Messungen gegen den falschen Port sehen eine andere Seite (eigener Fehler 2026-09-10, zurückgenommen).

## Verbesserungs-Backlog (K4)

Prüfung: `make betrieb-check` — ein Vorschlag ohne Gegenrede und Alternative wird abgewiesen (K4).

| # | Vorschlag | Advocatus Diaboli | Out of the Box | Anker |
|---|---|---|---|---|
| 1 | Index-Alter in der Kopfzeile | Erklärt nur das Fehlen; der Owner will die Mail, nicht das Alter | Liste zieht das Post-Ingest-Fenster beim Öffnen selbst live nach | offen |
| 2 | „Geschlossen in 7 Tagen" als Kopfzahl | Eine Motivationszahl ohne Handlung; sie zeigt Tempo, aber der Owner kann daraus nichts anklicken oder öffnen | Geschlossene Vorgänge als eigenen, eingeklappten Abschnitt zeigen | offen |
| 3 | Melder „Dienst läuft mit altem Code" | Ein Melder mehr, der den Owner zum Neustart auffordert, den er ohnehin nach jedem Merge macht | Neustart durch den Merge-Workflow (braucht Deploy-Recht, das der Dienst bewusst nicht hat) | gebaut (Melder), PR [#3064](https://github.com/achimdehnert/platform/pull/3064) — Auto-Neustart bleibt Owner-Entscheid #2507 |

## Modellfest-Drill (K5, Soll)

Frische Sitzung, nur diese Akte: Seite bauen, Linkprüfer laufen lassen, fünf Kennzahlen nennen, einen Backlog-Vorschlag mit Gegenrede. Noch nicht gefahren.
