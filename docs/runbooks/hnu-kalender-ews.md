# HNU-Kalender lesen und schreiben — über EWS statt Graph (#3300)

## Zweck

Der HNU-Kalender (Dienstpostfach an der Hochschule Neu-Ulm) ist seit 2026-07-18 aus dem
Graph-Draht (`ms_calendar.py`) entfernt: „alle Direktzugänge gesperrt". Das stimmte nur für
den Kanal, der damals probiert wurde. Dieses Runbook hält fest, **warum Graph nicht geht**,
**warum EWS geht**, und wie das Werkzeug bedient wird.

Werkzeug: [`tools/calendar_agent/ews_calendar.py`](../../tools/calendar_agent/ews_calendar.py).
Auftrag: platform#3300 (Raum Achim/Lotse, SA-4, Owner-Freigabe 2026-09-17).

## Befund: warum Graph den HNU-Kalender nie sehen wird

| # | Beobachtung | Beleg (2026-09-17, von der Lotsen-Maschine) | Folgerung |
|---|---|---|---|
| 1 | Device-Code-Anmeldung am HNU-Mandanten scheitert mit AADSTS **53003** | Commit `74f12f76` (2026-07-18), Konfig-Kommentar in `~/.claude/calendar.env` | Conditional Access „Gerätestatus Unregistered" — Richtlinie des Mandanten, kein Client-Problem; ein anderer Public Client oder Scope ändert daran nichts |
| 2 | `outlook.hnu.de` antwortet mit `Server: Microsoft-IIS/10.0`, `X-OWA-Version: 15.2.2562.49`, `X-FEServer: EXCH-02/03` | `curl -D - https://outlook.hnu.de/EWS/Exchange.asmx` | **On-Prem Exchange 2019** (15.2 = Exchange 2019). Das Postfach liegt nicht in Exchange Online — Microsoft Graph erreicht On-Prem-Postfächer grundsätzlich nicht (Graph-API ist Cloud-only, Hybrid-REST deckt Kalender nicht ab) |
| 3 | `/EWS/Exchange.asmx` bietet `WWW-Authenticate: Negotiate, NTLM` (kein Basic); `/autodiscover` und `/mapi` zusätzlich `Basic` | dieselben Header-Probes | Passwort-Anmeldung per NTLM ist am EWS-Endpunkt vorgesehen — dieselbe Kennung wie der IMAP-Draht (`outlook.hnu.de:993`, seit 2026-07-21 in Betrieb) |
| 4 | `GetFolder(calendar)` per NTLM → HTTP 200, Kalenderordner mit 2361 Einträgen | `ews_calendar.py --account hnu --status` | Leseweg steht |
| 5 | `CreateItem` → `UpdateItem` → `DeleteItem` je HTTP 200 / `NoError` | Verdrahtungstest 2026-09-17 mit Testtermin „Lotse-Verdrahtungstest #3300", danach wieder gelöscht (0 Treffer) | Schreibweg steht — ohne ICS-Umweg |

Kurz: **Der Kalender war nie „gesperrt", er lag nur hinter einem anderen Server.** Graph
und der HNU-Mandant in Entra ID sind für dieses Postfach die falsche Tür; die richtige ist
der On-Prem-Exchange, den der IMAP-Draht ohnehin schon benutzt.

Was **nicht** geht (geprüft): OWA (`/owa/`) hängt hinter einem Portal-Redirect
(`/cgi/tm?code=…`, Forms-Login) — kein programmatischer Weg. Ein Abo-Link (ICS-Publish)
ist weiterhin nicht freigeschaltet. Beides ist egal, solange EWS offen ist.

## Rechte-Bilanz (Kriterium 4 in #3300)

- Kein neues Credential, kein neuer Scope, keine App-Registrierung: EWS läuft mit der
  IMAP-Kennung aus `~/.secrets/hnu_mail.env` (Zeiger, nie Wert).
- Nur das eigene Postfach: `DistinguishedFolderId Id="calendar"` ohne `Mailbox`-Element —
  fremde Kalender sind im Werkzeug nicht adressierbar.
- Schreiben ist Stufe A wie bei `ms_calendar.py`: nie Teilnehmer, `SendMeetingInvitations=
  SendToNone`; `--update`/`--delete` verweigern Besprechungen, fremde Einladungen und
  Serien hart (Exit 3, kein `--yes` hebt das auf).

## Aufruf

```bash
T=tools/calendar_agent/ews_calendar.py
python3 $T --account hnu --status              # Verdrahtungsprobe
python3 $T --account hnu --today
python3 $T --account hnu --list 14 --ids       # Kennung, besprechung=, organisator=, serie
python3 $T --account hnu --create --subject "…" --start "2026-10-01 10:00" --end "2026-10-01 11:00" [--location …] [--note …]
python3 $T --account hnu --update KENNUNG [--subject …] [--start …] [--end …] [--location …] [--note …]
python3 $T --account hnu --delete KENNUNG
```

Ohne `--yes` fragen `--create`/`--update`/`--delete` zurück. Die Kennung (letzte 12 Zeichen
der EWS-ItemId) wird über ein Listenfenster aufgelöst (`--tage`, Default 60); 0 oder >1
Treffer → Exit 2.

## Konfiguration (Maschinen-Gate)

Das Werkzeug liest **dieselbe** Datei wie der Mail-Draht: `~/.claude/mail-<KONTO>.env` mit
`IMAP_HOST` (→ `https://<host>/EWS/Exchange.asmx`, überschreibbar per `EWS_URL`),
`MAIL_LOGIN`, `MAIL_CREDS_FILE`. Keine zusätzliche Konfig, kein Eintrag in `calendar.env`.
Fehlt die Datei, läuft nichts (Capability-Profil).

NTLM übernimmt `curl --ntlm`; das Passwort geht ausschließlich als curl-Konfiguration
über stdin (`-K -`) — nie auf die Kommandozeile, nie in die Umgebung.

## Abgrenzung zum bestehenden ICS-Import

Der manuelle ICS-Import (`.ics` nach `~/shared/`, Owner importiert in Outlook) bleibt
unangetastet und funktioniert weiter. Er ist ab jetzt der Fallback, nicht mehr der
Standard: `--create` legt den Termin direkt an, `--update` ändert ihn, beides ohne
Handarbeit des Owners.

**Nicht gebaut (bewusst):** Einbindung in die Gesamtsicht `ms_calendar.py --list` (beide
Konten in einer Ausgabe). Das würde `calendar.env` anfassen, die die Owner-Entscheidung
vom 2026-07-18 trägt — Owner-Zug, im PR zu #3300 als Frage gestellt.

## Wenn es bricht

| Symptom | Ursache | Griff |
|---|---|---|
| `✘ Anmeldung abgelehnt (HTTP 401)` | Passwort rotiert oder NTLM am EWS-Endpunkt abgeschaltet | `curl -D - …/EWS/Exchange.asmx` — steht `NTLM` noch im `WWW-Authenticate`? Dann Kennung prüfen (`read_mail.py --account hnu` als Gegenprobe, gleicher Draht) |
| `keine XML-Antwort` | Redirect/Portal vor EWS (wie bei OWA) | `EWS_URL` in `mail-hnu.env` auf den ausgegebenen Endpunkt zeigen lassen |
| `ErrorAccessDenied` | Postfach-Rechte geändert | Owner — keine Rechte-Ausweitung ohne Rücksprache |
