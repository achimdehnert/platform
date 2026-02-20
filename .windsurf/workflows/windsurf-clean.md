---
description: Kill stale Windsurf remote server processes on dev-server to fix ECONNREFUSED reconnect errors
---

# Windsurf Remote Cleanup

Verwende diesen Workflow wenn Windsurf beim SSH Remote Connect folgende Fehler zeigt:
- `windsurf client: couldn't create connection to server`
- `ECONNREFUSED 127.0.0.1:4XXXX`
- `Restarting server failed`

## Ursache

Alte Windsurf-Server-Prozesse vom letzten Session-Abbruch laufen noch auf dem dev-server
und blockieren den Neustart.

## Schritt 1: Stale Prozesse killen

// turbo
Run: `ssh deploy@46.225.113.1 "bash ~/windsurf-clean.sh"`

Erwartete Ausgabe:
```
[windsurf-clean] Killing ALL stale windsurf-server processes...
[windsurf-clean] Done. Remaining windsurf processes: 0
You can now reconnect Windsurf.
```

## Schritt 2: Windsurf reconnecten

In Windsurf: `F1` → `Remote-SSH: Connect to Host` → `dev-server`

Oder unten links auf `SSH: dev-server` klicken → Reconnect.

## Schritt 3: Verify

// turbo
Run: `ssh deploy@46.225.113.1 "pgrep -u deploy -f windsurf-server | wc -l && echo processes running"`

Nach erfolgreichem Reconnect sollten 3-5 Prozesse laufen (normal).
