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

## Schritt 1: Interaktives Menü starten (empfohlen)

// turbo
Run: `ssh -t hetzner-dev 'bash ~/fix-windsurf-remote.sh --menu'`

Das Menü zeigt:
```
═══ Windsurf Cleanup Menü ═══

  1) Sanft      — Nur stale Prozesse (>1h), aktive Sessions bleiben
  2) Workspace  — Nur einen bestimmten Workspace bereinigen  
  3) Force      — ALLE Windsurf-Prozesse killen (Notfall)
  4) Status     — Aktive Windsurf-Sessions anzeigen
  q) Abbrechen

Auswahl [1-4, q]:
```

### Alternative: Direkte Befehle

```bash
# Sanft (nur stale Prozesse)
ssh hetzner-dev 'bash ~/fix-windsurf-remote.sh --clean'

# Force (Notfall - killt ALLE Sessions)
ssh hetzner-dev 'bash ~/fix-windsurf-remote.sh --force'
```

Erwartete Ausgabe:
```
═══ Windsurf Remote-SSH Fix — ECONNREFUSED 44341 ═══
[INFO]  User: root (Target: deploy)
[INFO]  Sanfter Modus: Nur stale Prozesse (>1h) werden bereinigt.
✅ Cleanup abgeschlossen. Windsurf neu verbinden.
```

## Schritt 2: Windsurf reconnecten

In Windsurf: `F1` → `Remote-SSH: Connect to Host` → `dev-server`

Oder unten links auf `SSH: dev-server` klicken → Reconnect.

## Schritt 3: Verify

// turbo
Run: `ssh hetzner-dev 'pgrep -u deploy -f windsurf-server | wc -l && echo processes running'`

Nach erfolgreichem Reconnect sollten 3-5 Prozesse laufen (normal).

## Bei häufigen Problemen: Vollständiger Fix

Wenn das Problem wiederholt auftritt, einmalig den vollen Fix ausführen:

```bash
scp ${GITHUB_DIR:-$HOME/github}/platform/docs/adr/inputs/fix-windsurf-remote.sh hetzner-dev:~/
ssh hetzner-dev 'bash ~/fix-windsurf-remote.sh'
```

Das installiert:
- SSH-Server Keepalive (30s/4)
- Systemd Cleanup-Timer (alle 4h)
- Node.js Memory-Limit (2GB)
