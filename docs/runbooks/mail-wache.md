# Mail-Wache — Weckruf bei neuer Mail (chat-hub#48 F4)

## Zweck

Weckt die Raum-Session "Mail" bei neuer Mail — analog zur Chat-Wache
(`chat-hub/deploy/chat_lotse.py watch`), die dieselbe Session bei neuer
Raumnachricht weckt. Bearbeitet nichts, meldet nur: eine JSON-Zeile je neuer
Nachricht auf stdout.

Werkzeug: [`tools/mail_agent/mail_wache.py`](../../tools/mail_agent/mail_wache.py).
Owner-Grant: chat-hub#48, Kommentar „vierter".

## Aufruf

```bash
python3 tools/mail_agent/mail_wache.py                       # Default: hnu,iil,ad
python3 tools/mail_agent/mail_wache.py --konten hnu,iil --ordner INBOX
python3 tools/mail_agent/mail_wache.py --einmal --konten hnu # Selbsttest
```

| Option | Default | Bedeutung |
|---|---|---|
| `--konten` | `hnu,iil,ad` | Komma-Liste der zu beobachtenden Konten |
| `--ordner` | `INBOX` | IMAP-Ordner (alle IMAP-Konten dieses Laufs) |
| `--einmal` | aus | Verbindungsbeleg je Konto, dann beenden |
| `--intervall` | `120` | Poll-Abstand in Sekunden (Graph, IMAP ohne IDLE) |

## Ausgabeformat

Eine JSON-Zeile je neuer Nachricht, `flush=True`:

```json
{"konto": "hnu", "ordner": "INBOX", "uid": "12345", "von": "Max Muster",
 "betreff": "Rückfrage zur Klausur", "ts": "2026-09-05T08:12:00Z",
 "link": "https://mail.iil.pet/m/hnu/posteingang/12345"}
```

`link` fehlt, wenn der Ordner-Slug nicht ableitbar ist (nie geraten) — beim
IIL-Konto (Graph) grundsätzlich, weil ein Link dort erst eine Kurz-ID-
Registrierung braucht (`mail_link_server.py`, `/r/<kurz-id>`). Ein Konto, das
länger als 15 Minuten nicht erreichbar ist, meldet zusätzlich
`{"konto": "...", "fehler": "..."}` — nicht stumm bleiben.

## Als zweiter Monitor der Raum-Session „Mail"

```bash
python3 tools/mail_agent/mail_wache.py 2>&1
```

Persistent laufen lassen (kein `run_in_background`, kein `Monitor`-Poll) —
die Session liest die Zeilen fortlaufend mit; `2>&1`, weil die
Verbindungsbelege (Capability, Start-UID) auf stderr stehen.

## Grenzen

- **Graph (iil) pollt**, kein IDLE im genutzten Scope.
- **`ad` fehlt, solange `~/.claude/mail.env` nicht existiert** — Wache
  überspringt es mit einer stderr-Zeile, statt abzubrechen.
- **Kein Body, keine Anhänge** — Inhalt über `read_mail.py`/`graph_mail.py`.
- **Strikt lesend** — nichts wird markiert, verschoben oder gelöscht.

## Stopp

Nur per `TaskStop` (SIGTERM) — beendet IDLE-Zyklen sauber (Exit 0).
